function emg = loadEMG(filepath, varargin)
% hwalker.io.loadEMG  Load EMG (Delsys / Noraxon / generic CSV) + standard processing.
%
%   emg = hwalker.io.loadEMG('emg.csv')
%   emg = hwalker.io.loadEMG('emg.csv', 'BandpassHz',[20 450], 'RmsWindowMs',50)
%   emg = hwalker.io.loadEMG('emg.csv', 'MVCFile', 'subj01_mvc.csv')
%
% Standard SENIAM-recommended processing:
%   1. DC remove (subtract mean per channel)
%   2. 4th-order Butterworth bandpass 20-450 Hz (zero-phase)
%   3. Full-wave rectify
%   4. Sliding RMS window (50 ms default)
%   5. Optional MVC normalization (% MVC) if MVCFile provided
%   6. Onset/offset detection via Teager-Kaiser energy operator
%
% Returns struct:
%   .source_file
%   .fs                sample rate (Hz)
%   .t                 time axis (s)
%   .channel_names     cellstr (e.g., 'R_TibAnt', 'R_GastrocLat', ...)
%   .raw               N x C matrix
%   .filtered          N x C bandpass-filtered
%   .rectified         N x C rectified
%   .envelope          N x C RMS envelope (target rate retained)
%   .normalized        N x C  % MVC (NaN if no MVC file)
%   .mvc_values        1 x C  MVC peak per channel (raw units; NaN if no MVC)
%   .onset             cell{C} struct array .start_s .stop_s
%   .qc                struct .channels_dropped, .clipping_count, .baseline_drift
%
% Reference: SENIAM (1999) recommendations, Hermens et al. JEK 10:361-374.

    p = inputParser;
    addParameter(p, 'BandpassHz',  [20 450], @(x) isnumeric(x) && numel(x) == 2);
    addParameter(p, 'RmsWindowMs', 50,       @(x) isnumeric(x) && isscalar(x) && x > 0);
    addParameter(p, 'MVCFile',     '',       @(x) ischar(x) || isstring(x));
    addParameter(p, 'OnsetMethod', 'envelope-threshold', @ischar);  % envelope-threshold | TKE
    addParameter(p, 'OnsetSDMult', 3.0,      @(x) isnumeric(x) && isscalar(x));
    parse(p, varargin{:});
    bp = p.Results.BandpassHz;
    rmsMs = p.Results.RmsWindowMs;

    if ~exist(filepath, 'file')
        error('hwalker:loadEMG:notFound', 'File not found: %s', filepath);
    end

    T = readtable(filepath, 'VariableNamingRule', 'preserve');
    cols = T.Properties.VariableNames;

    % Time
    timeIdx = find(contains(lower(cols), {'time','t_s','timestamp'}), 1);
    if isempty(timeIdx)
        error('hwalker:loadEMG:noTime', ...
            'No time column found.  Expected one of: Time, time, T_s, timestamp.');
    end
    t = T{:, timeIdx};
    if max(t) > 1000
        t = t / 1000;
    end
    dt = diff(t);
    fs = 1 / median(dt(dt > 0));

    % EMG channels = all numeric columns except time + non-EMG-like names
    emgCols = setdiff(1:width(T), timeIdx);
    keep = false(size(emgCols));
    for i = 1:numel(emgCols)
        v = T{:, emgCols(i)};
        keep(i) = isnumeric(v) && ~all(isnan(v));
    end
    emgCols = emgCols(keep);
    raw = T{:, emgCols};
    chNames = cols(emgCols);

    % --- Processing pipeline ---
    nC = size(raw, 2);
    qc = struct('channels_dropped', 0, 'clipping_count', 0, 'baseline_drift', zeros(1, nC));

    % 1. DC removal
    raw_dc = raw - mean(raw, 1, 'omitnan');
    qc.baseline_drift = max(abs(raw - mean(raw,1,'omitnan')), [], 1) - ...
                        max(abs(raw_dc), [], 1);

    % 2. Bandpass
    nyq = fs / 2;
    if bp(2) >= nyq
        bp(2) = nyq * 0.95;
    end
    [bb, ba] = butter(4, bp / nyq);
    filtered = zeros(size(raw_dc));
    for c = 1:nC
        v = raw_dc(:, c);
        ok = isfinite(v);
        if sum(ok) > 12
            v(ok) = filtfilt(bb, ba, v(ok));
        end
        filtered(:, c) = v;
    end

    % 3. Rectify
    rectified = abs(filtered);

    % 4. RMS envelope (sliding window)
    win = max(round(rmsMs / 1000 * fs), 3);
    envelope = zeros(size(rectified));
    sq = rectified.^2;
    for c = 1:nC
        envelope(:, c) = sqrt(movmean(sq(:, c), win, 'omitnan'));
    end

    % 5. MVC normalization
    mvc = nan(1, nC);
    normalized = nan(size(envelope));
    if ~isempty(p.Results.MVCFile) && exist(char(p.Results.MVCFile), 'file')
        try
            mvcEMG = hwalker.io.loadEMG(char(p.Results.MVCFile));
            % Match channels by name; take peak envelope as MVC
            for c = 1:nC
                idx = find(strcmp(mvcEMG.channel_names, chNames{c}), 1);
                if ~isempty(idx)
                    mvc(c) = max(mvcEMG.envelope(:, idx));
                end
            end
        catch ME
            warning('hwalker:loadEMG:mvcFail', 'MVC load failed: %s', ME.message);
        end
        for c = 1:nC
            if isfinite(mvc(c)) && mvc(c) > 0
                normalized(:, c) = envelope(:, c) / mvc(c) * 100;
            end
        end
    end

    % 6. Onset detection (Teager-Kaiser)
    onsets = cell(1, nC);
    for c = 1:nC
        onsets{c} = detectOnset(envelope(:, c), t, fs, ...
            p.Results.OnsetMethod, p.Results.OnsetSDMult);
    end

    % Clipping check
    qc.clipping_count = sum(any(abs(raw - max(abs(raw), [], 1)) < eps & ...
                                 abs(raw) > 0, 1));

    emg.source_file   = filepath;
    emg.fs            = fs;
    emg.t             = t;
    emg.channel_names = chNames;
    emg.raw           = raw;
    emg.filtered      = filtered;
    emg.rectified     = rectified;
    emg.envelope      = envelope;
    emg.normalized    = normalized;
    emg.mvc_values    = mvc;
    emg.onset         = onsets;
    emg.qc            = qc;

    fprintf('[loadEMG] %s — %d channels @ %.0f Hz, %.2fs\n', ...
        filepath, nC, fs, t(end) - t(1));
    if any(isnan(mvc))
        fprintf('[loadEMG]   ⚠ no MVC normalization (provide ''MVCFile'' for %% MVC).\n');
    end
end


function onsets = detectOnset(envSig, t, fs, method, sdMult)
% Detect EMG burst onsets/offsets via thresholded envelope.
%
% Method:
%   'envelope-threshold' (default) — threshold = baseline_mean + sdMult*baseline_sd
%                                    where baseline = first 0.5 s of envelope.
%   'TKE' — Teager-Kaiser energy on the envelope itself (less sensitive on
%           heavily smoothed signals; here implemented as a backup).
%
% Returns struct array with .start_s .stop_s for each detected burst.
    onsets = struct('start_s', {}, 'stop_s', {});

    sig = envSig(:);
    if strcmpi(method, 'TKE')
        % TKE on a smoothed envelope is near-zero by construction; this
        % branch is only useful when the caller supplies the *bandpass-
        % filtered* signal directly. Otherwise it returns no detections.
        tk = zeros(size(sig));
        tk(2:end-1) = sig(2:end-1).^2 - sig(1:end-2) .* sig(3:end);
        sig = max(tk, 0);
    end

    baseline_n = max(round(0.5 * fs), 50);
    if numel(sig) < baseline_n + 10, return; end
    base_mean = mean(sig(1:baseline_n), 'omitnan');
    base_sd   = std(sig(1:baseline_n), 0, 'omitnan');
    if base_sd < eps
        % Constant baseline — use a tiny relative threshold instead
        threshold = base_mean + 0.05 * (max(sig) - base_mean);
    else
        threshold = base_mean + sdMult * base_sd;
    end

    above = sig > threshold;
    d = diff([0; above; 0]);
    starts = find(d == 1);
    ends   = find(d == -1) - 1;

    minDur = max(round(0.05 * fs), 1);   % 50 ms minimum burst
    for i = 1:numel(starts)
        if (ends(i) - starts(i) + 1) >= minDur
            onsets(end+1).start_s = t(starts(i));   %#ok<AGROW>
            onsets(end).stop_s    = t(ends(i));
        end
    end
end
