function results = analyzeFile(filepath_or_table, varargin)
% hwalker.analyzeFile  Full analysis pipeline for one H-Walker CSV.
%
%   results = hwalker.analyzeFile('/path/to/20260430_Robot_CBJ_TD_level_0_5_walker_high_0.csv')
%   results = hwalker.analyzeFile(T)                      % pre-loaded table
%   results = hwalker.analyzeFile(T, 'label','sync1_run') % table + custom label
%
% When called with a file path and a Sync column is present:
%   - 0 sync windows → analyzes the full file (result.syncId = 0)
%   - 1 sync window  → analyzes that window  (result.syncId = 1)
%   - N sync windows → returns 1×N struct array, each labeled basename_syncK
%
% Optional parameters:
%   'label'           string  override filename in result struct
%   'syncId'          int     sync window index when passing pre-sliced table
%   'syncWindow'      1×2     [t_start, t_end] of pre-sliced window (seconds)
%   'minSyncDuration' double  minimum valid sync cycle length in seconds (default 0.5)
%
% Result struct fields:
%   filename, filepath, label, syncId, syncWindow
%   nSamples, durationS, sampleRate
%   left / right             (stride metrics struct)
%   leftForce / rightForce   (force tracking struct)
%   leftProfile / rightProfile (normalized force profiles)
%   strideTimeSymmetry, strideLengthSymmetry, stanceSymmetry, forceSymmetry
%   leftFatigue, rightFatigue
%
% Stride metrics struct fields:
%   nStrides, strideTimes, strideTimesRaw, hsIndices, validMask
%   strideTimeMean, strideTimeStd, strideTimeCV, cadence
%   stancePct, swingPct, stancePctMean, stancePctStd, swingPctMean, swingPctStd
%   strideLengths, strideLengthMean, strideLengthStd

    p = inputParser;
    addParameter(p, 'label',           '');
    addParameter(p, 'syncId',          0);
    addParameter(p, 'syncWindow',      []);
    addParameter(p, 'minSyncDuration', 0.5);
    parse(p, varargin{:});

    % --- Handle table vs. file path input ---
    if istable(filepath_or_table)
        T        = filepath_or_table;
        filepath = '';
        baseName = p.Results.label;
        results  = coreAnalysis(T, baseName, filepath, ...
                       p.Results.syncId, p.Results.syncWindow);
        return
    end

    % --- File path: load, detect sync, branch ---
    filepath = filepath_or_table;
    T_full   = hwalker.io.loadCSV(filepath);
    [~, baseName, ~] = fileparts(filepath);
    if ~isempty(p.Results.label)
        baseName = p.Results.label;
    end

    cycles  = hwalker.sync.findWindows(T_full, p.Results.minSyncDuration);
    nCycles = size(cycles, 1);

    if nCycles == 0
        % No sync signal → analyze full file
        results = coreAnalysis(T_full, baseName, filepath, 0, []);

    elseif nCycles == 1
        % Single sync window
        Tw      = hwalker.sync.extractWindow(T_full, cycles(1,1), cycles(1,2));
        results = coreAnalysis(Tw, baseName, filepath, 1, cycles(1,:));

    else
        % Multiple sync windows → labeled struct array  (basename_sync1, _sync2 ...)
        for k = nCycles:-1:1  % reverse to pre-allocate struct array
            Tw        = hwalker.sync.extractWindow(T_full, cycles(k,1), cycles(k,2));
            label_k   = sprintf('%s_sync%d', baseName, k);
            results(k) = coreAnalysis(Tw, label_k, filepath, k, cycles(k,:));
        end
    end
end


% =========================================================================
%  Core analysis (operates on an already-sliced table)
% =========================================================================
function result = coreAnalysis(T, label, filepath, syncId, syncWindow)

    fs = hwalker.io.estimateSampleRate(T);
    if fs <= 0
        error('hwalker:badSampleRate', 'Cannot estimate sample rate.');
    end

    result.filename   = label;
    result.filepath   = filepath;
    result.label      = label;
    result.syncId     = syncId;
    result.syncWindow = syncWindow;   % [] when no sync, [t_start t_end] otherwise
    result.nSamples   = height(T);
    result.durationS  = height(T) / fs;
    result.sampleRate = fs;

    if syncId > 0
        fprintf('  [sync%d] %s  (%d samples, %.1f s, %.1f Hz)\n', ...
            syncId, label, result.nSamples, result.durationS, fs);
    else
        fprintf('  Loaded: %s  (%d samples, %.1f s, %.1f Hz)\n', ...
            label, result.nSamples, result.durationS, fs);
    end

    sides      = {'L', 'R'};
    sideFields = {'left', 'right'};

    for si = 1:2
        side = sides{si};
        sf   = sideFields{si};

        hsIdx = hwalker.stride.detectHS(T, side, fs);

        if numel(hsIdx) < 2
            fprintf('    %s: no strides detected\n', side);
            result.(sf)             = emptyStride();
            result.([sf 'Force'])   = emptyForce();
            result.([sf 'Profile']) = emptyProfile();
            continue
        end

        % --- Stride times ---
        strideTimes_raw = double(diff(hsIdx)) / fs;
        [strideTimes_valid, validMask] = hwalker.stride.filterIQR(strideTimes_raw);

        % NaN-aligned: all per-stride arrays share the same length
        strideTimes_aligned = nan(numel(strideTimes_raw), 1);
        strideTimes_aligned(validMask) = strideTimes_valid;

        sr.nStrides       = numel(strideTimes_valid);
        sr.strideTimesRaw = strideTimes_raw;
        sr.strideTimes    = strideTimes_aligned;
        sr.hsIndices      = hsIdx;
        sr.validMask      = validMask;

        if ~isempty(strideTimes_valid)
            sr.strideTimeMean = mean(strideTimes_valid);
            sr.strideTimeStd  = std(strideTimes_valid);
            sr.strideTimeCV   = sr.strideTimeStd / sr.strideTimeMean * 100;
            sr.cadence = 60.0 / sr.strideTimeMean * 2;  % one stride = 2 steps
        else
            sr.strideTimeMean = 0;  sr.strideTimeStd = 0;
            sr.strideTimeCV   = 0;  sr.cadence = 0;
        end

        % --- Stance / Swing ---
        [stancePct, swingPct] = hwalker.stride.stanceSwing(T, side, hsIdx, validMask);
        sr.stancePct = stancePct;
        sr.swingPct  = swingPct;
        finiteS = isfinite(stancePct);
        if any(finiteS)
            sr.stancePctMean = mean(stancePct(finiteS));
            sr.stancePctStd  = std(stancePct(finiteS));
            sr.swingPctMean  = mean(swingPct(finiteS));
            sr.swingPctStd   = std(swingPct(finiteS));
        else
            sr.stancePctMean = 0;  sr.stancePctStd = 0;
            sr.swingPctMean  = 0;  sr.swingPctStd  = 0;
        end

        % --- Stride length (ZUPT) ---
        sr.strideLengths = hwalker.stride.lengthZUPT(T, side, hsIdx, validMask, fs);
        validLen = sr.strideLengths(isfinite(sr.strideLengths));
        if ~isempty(validLen)
            sr.strideLengthMean = mean(validLen);
            sr.strideLengthStd  = std(validLen);
        else
            sr.strideLengthMean = 0;  sr.strideLengthStd = 0;
        end

        result.(sf) = sr;
        fprintf('    %s: %d strides, T=%.3f±%.3f s, cadence=%.1f steps/min\n', ...
            side, sr.nStrides, sr.strideTimeMean, sr.strideTimeStd, sr.cadence);

        % --- Force tracking ---
        ft = hwalker.force.trackingError(T, side, hsIdx, validMask);
        result.([sf 'Force']) = ft;
        if ft.rmse > 0
            fprintf('    %s force: RMSE=%.2f N, MAE=%.2f N, peak=%.2f N\n', ...
                side, ft.rmse, ft.mae, ft.peakError);
        end

        % --- Normalized force profiles ---
        result.([sf 'Profile']) = hwalker.force.normalizedProfile( ...
            T, side, hsIdx, validMask);
    end

    % --- Symmetry indices ---
    l = result.left;  r = result.right;
    result.strideTimeSymmetry   = hwalker.stats.symmetryIndex( ...
        l.strideTimeMean, r.strideTimeMean);
    result.strideLengthSymmetry = hwalker.stats.symmetryIndex( ...
        l.strideLengthMean, r.strideLengthMean);
    result.stanceSymmetry       = hwalker.stats.symmetryIndex( ...
        l.stancePctMean, r.stancePctMean);
    lft = result.leftForce;  rft = result.rightForce;
    if lft.rmse > 0 && rft.rmse > 0
        result.forceSymmetry = hwalker.stats.symmetryIndex(lft.rmse, rft.rmse);
    else
        result.forceSymmetry = -1;
    end

    % --- Fatigue ---
    lTimes = l.strideTimes(isfinite(l.strideTimes));
    rTimes = r.strideTimes(isfinite(r.strideTimes));
    result.leftFatigue  = hwalker.stats.fatigueIndex(lTimes);
    result.rightFatigue = hwalker.stats.fatigueIndex(rTimes);
end


% ---- Local helpers ----

function sr = emptyStride()
    sr.nStrides       = 0;   sr.strideTimesRaw = [];  sr.strideTimes = [];
    sr.hsIndices      = [];   sr.validMask       = [];
    sr.strideTimeMean = 0;    sr.strideTimeStd   = 0;
    sr.strideTimeCV   = 0;    sr.cadence         = 0;
    sr.stancePct      = [];   sr.swingPct        = [];
    sr.stancePctMean  = 0;    sr.stancePctStd    = 0;
    sr.swingPctMean   = 0;    sr.swingPctStd     = 0;
    sr.strideLengths  = [];   sr.strideLengthMean = 0; sr.strideLengthStd = 0;
end

function ft = emptyForce()
    ft.rmse = 0; ft.mae = 0; ft.peakError = 0;
    ft.rmsePerStride = []; ft.maePerStride = [];
end

function fp = emptyProfile()
    fp.act.individual = []; fp.act.mean = []; fp.act.std = [];
    fp.des.individual = []; fp.des.mean = []; fp.des.std = [];
end
