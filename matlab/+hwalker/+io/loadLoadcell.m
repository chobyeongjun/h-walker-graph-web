function lc = loadLoadcell(filepath, varargin)
% hwalker.io.loadLoadcell  Load body-weight-support (BWS) loadcell CSV.
%
%   lc = hwalker.io.loadLoadcell('loadcell.csv')
%   lc = hwalker.io.loadLoadcell('loadcell.csv', 'BodyMassKg', 72.0)
%   lc = hwalker.io.loadLoadcell(file, 'CutoffHz', 10, 'TareSeconds', 1.0)
%
% Pipeline:
%   1. Read CSV (columns: Time, Force_N or Force, plus optional Sync)
%   2. Tare baseline (mean of first TareSeconds)
%   3. 4th-order Butterworth low-pass at CutoffHz (default 10 Hz, zero-phase)
%   4. If BodyMassKg given → compute % BWS  =  100 * F / (m * 9.81)
%
% Returns struct:
%   .source_file
%   .fs
%   .t                 time axis (s)
%   .force_N           raw force (calibrated)
%   .force_filt_N      filtered force
%   .bws_pct           % body weight support (NaN if no BodyMassKg)
%   .bws_pct_mean
%   .bws_pct_std
%   .body_mass_kg
%   .sync              digital sync if present
%   .qc                struct .baseline_drift, .saturation_count

    p = inputParser;
    addParameter(p, 'BodyMassKg',  NaN, @(x) isnumeric(x) && isscalar(x));
    addParameter(p, 'CutoffHz',    10,  @(x) isnumeric(x) && isscalar(x) && x > 0);
    addParameter(p, 'TareSeconds', 1.0, @(x) isnumeric(x) && isscalar(x) && x >= 0);
    parse(p, varargin{:});
    bodyMass = p.Results.BodyMassKg;
    cutoff   = p.Results.CutoffHz;
    tareSec  = p.Results.TareSeconds;

    if ~exist(filepath, 'file')
        error('hwalker:loadLoadcell:notFound', 'File not found: %s', filepath);
    end

    T = readtable(filepath, 'VariableNamingRule', 'preserve');
    cols = T.Properties.VariableNames;

    % Time
    timeIdx = find(contains(lower(cols), {'time','t_s','timestamp'}), 1);
    if isempty(timeIdx)
        error('hwalker:loadLoadcell:noTime', 'No time column found.');
    end
    t = T{:, timeIdx};
    if max(t) > 1000
        t = t / 1000;
    end
    dt = diff(t);
    fs = 1 / median(dt(dt > 0));

    % Force column
    forceIdx = find(contains(lower(cols), {'force','load','newton','f_n','bws'}), 1);
    if isempty(forceIdx)
        error('hwalker:loadLoadcell:noForce', 'No force column found.');
    end
    F = T{:, forceIdx};

    % Sync (optional)
    syncSig = [];
    syncIdx = find(contains(lower(cols), {'sync','ttl','trigger'}), 1);
    if ~isempty(syncIdx)
        syncSig = T{:, syncIdx};
    end

    % --- Tare ---
    nTare = max(round(tareSec * fs), 1);
    if numel(F) > nTare
        F0 = mean(F(1:nTare), 'omitnan');
        F  = F - F0;
    end

    % --- Filter ---
    F_filt = F;
    if fs > 2 * cutoff
        [b, a] = butter(4, cutoff / (fs/2));
        ok = isfinite(F);
        if sum(ok) > 12
            F_filt(ok) = filtfilt(b, a, F(ok));
        end
    end

    % --- BWS % ---
    bws_pct = nan(size(F));
    bws_mean = NaN; bws_std = NaN;
    if isfinite(bodyMass) && bodyMass > 0
        bws_pct = 100 * F_filt / (bodyMass * 9.81);
        bws_mean = mean(bws_pct, 'omitnan');
        bws_std  = std(bws_pct,  0, 'omitnan');
    end

    % QC
    sat = sum(abs(F) >= 0.99 * max(abs(F)));
    drift = abs(mean(F(end-min(end,nTare):end), 'omitnan') - 0);

    lc.source_file   = filepath;
    lc.fs            = fs;
    lc.t             = t;
    lc.force_N       = F;
    lc.force_filt_N  = F_filt;
    lc.bws_pct       = bws_pct;
    lc.bws_pct_mean  = bws_mean;
    lc.bws_pct_std   = bws_std;
    lc.body_mass_kg  = bodyMass;
    lc.sync          = syncSig;
    lc.qc            = struct('baseline_drift', drift, 'saturation_count', sat);

    fprintf('[loadLoadcell] %s — fs=%.0f Hz, mean F=%.1f N (%.1f %% BW)\n', ...
        filepath, fs, mean(F_filt, 'omitnan'), bws_mean);
end
