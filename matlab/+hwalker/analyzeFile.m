function result = analyzeFile(filepath)
% hwalker.analyzeFile  Full analysis pipeline for one H-Walker CSV.
%
%   result = hwalker.analyzeFile('/path/to/Robot_S01_T01.csv')
%
% Computes per-side:
%   stride times, GCP-based heel strikes, ZUPT stride lengths,
%   stance/swing %, force tracking RMSE/MAE, GCP-normalized force profiles,
%   cadence, symmetry indices, fatigue index.
%
% Result struct fields:
%   filename, filepath, nSamples, durationS, sampleRate
%   left / right       (stride metrics struct, see below)
%   leftForce / rightForce   (force tracking struct)
%   leftProfile / rightProfile   (normalized force profiles)
%   strideTimeSymmetry, strideLengthSymmetry, stanceSymmetry, forceSymmetry
%   leftFatigue, rightFatigue
%
% Stride metrics struct fields:
%   nStrides, strideTimes, strideTimesRaw, hsIndices, validMask
%   strideTimeMean, strideTimeStd, strideTimeCV, cadence
%   stancePct, swingPct, stancePctMean, stancePctStd, swingPctMean, swingPctStd
%   strideLengths, strideLengthMean, strideLengthStd

    T  = hwalker.io.loadCSV(filepath);
    fs = hwalker.io.estimateSampleRate(T);
    if fs <= 0
        error('hwalker:badSampleRate', ...
            'Cannot estimate sample rate for: %s', filepath);
    end

    [~, fname, ext] = fileparts(filepath);
    result.filename   = [fname ext];
    result.filepath   = filepath;
    result.nSamples   = height(T);
    result.durationS  = height(T) / fs;
    result.sampleRate = fs;

    fprintf('  Loaded: %s  (%d samples, %.1f s, %.1f Hz)\n', ...
        result.filename, result.nSamples, result.durationS, fs);

    sides      = {'L', 'R'};
    sideFields = {'left', 'right'};

    for si = 1:2
        side = sides{si};
        sf   = sideFields{si};

        hsIdx = hwalker.stride.detectHS(T, side, fs);

        if numel(hsIdx) < 2
            fprintf('    %s: no strides detected\n', side);
            result.(sf)           = emptyStride();
            result.([sf 'Force']) = emptyForce();
            result.([sf 'Profile']) = emptyProfile();
            continue
        end

        % --- Stride times ---
        strideTimes_raw = double(diff(hsIdx)) / fs;
        [strideTimes_valid, validMask] = hwalker.stride.filterIQR(strideTimes_raw);

        % NaN-aligned stride times: same length as strideTimes_raw so all
        % per-stride arrays (stancePct, strideLengths, forceRMSE) share index i.
        strideTimes_aligned = nan(numel(strideTimes_raw), 1);
        strideTimes_aligned(validMask) = strideTimes_valid;

        sr.nStrides       = numel(strideTimes_valid);   % valid stride count
        sr.strideTimesRaw = strideTimes_raw;
        sr.strideTimes    = strideTimes_aligned;         % NaN-aligned
        sr.hsIndices      = hsIdx;
        sr.validMask      = validMask;

        if ~isempty(strideTimes_valid)
            sr.strideTimeMean = mean(strideTimes_valid);
            sr.strideTimeStd  = std(strideTimes_valid);
            sr.strideTimeCV   = sr.strideTimeStd / sr.strideTimeMean * 100;
            % cadence [steps/min]: one stride = 2 steps (L + R)
            % cadence = 60/T * 2  — do NOT drop the *2
            sr.cadence = 60.0 / sr.strideTimeMean * 2;
        else
            sr.strideTimeMean = 0; sr.strideTimeStd = 0;
            sr.strideTimeCV   = 0; sr.cadence = 0;
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
            sr.stancePctMean = 0; sr.stancePctStd  = 0;
            sr.swingPctMean  = 0; sr.swingPctStd   = 0;
        end

        % --- Stride length (ZUPT) ---
        sr.strideLengths = hwalker.stride.lengthZUPT(T, side, hsIdx, validMask, fs);
        validLen = sr.strideLengths(isfinite(sr.strideLengths));
        if ~isempty(validLen)
            sr.strideLengthMean = mean(validLen);
            sr.strideLengthStd  = std(validLen);
        else
            sr.strideLengthMean = 0; sr.strideLengthStd = 0;
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
    l = result.left; r = result.right;
    result.strideTimeSymmetry   = hwalker.stats.symmetryIndex( ...
        l.strideTimeMean, r.strideTimeMean);
    result.strideLengthSymmetry = hwalker.stats.symmetryIndex( ...
        l.strideLengthMean, r.strideLengthMean);
    result.stanceSymmetry       = hwalker.stats.symmetryIndex( ...
        l.stancePctMean, r.stancePctMean);
    lft = result.leftForce; rft = result.rightForce;
    if lft.rmse > 0 && rft.rmse > 0
        result.forceSymmetry = hwalker.stats.symmetryIndex(lft.rmse, rft.rmse);
    else
        result.forceSymmetry = -1;
    end

    % --- Fatigue (strip NaN from aligned arrays before computing) ---
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
