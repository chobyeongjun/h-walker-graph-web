function f = extractFeatures(session)
% hwalker.experiment.extractFeatures  Compute per-stride scalar features for one session.
%
%   f = hwalker.experiment.extractFeatures(session)
%
% Returns struct with column-vector fields, one row per stride:
%   .stride_idx           1..N
%   .side                 'L'|'R'
%   --- Robot ---
%   .stride_time_s        diff of HS indices / fs
%   .cadence_steps_min    60/T * 2
%   .stride_length_m      ZUPT-integrated
%   .force_rmse_N         per-stride force tracking RMSE
%   .force_mae_N          per-stride MAE
%   .stance_pct
%   .swing_pct
%   --- Motion (if present) ---
%   .knee_peak_flex_deg   max knee flexion within stride
%   .knee_ROM_deg
%   .hip_peak_flex_deg
%   .hip_ROM_deg
%   .ankle_peak_dorsi_deg
%   .ankle_ROM_deg
%   --- Force plate (if present) ---
%   .grf_peak_vert_N
%   .grf_peak_propulsion_N
%   .grf_impulse_AP_Ns
%   --- EMG (if present) ---
%   .emg_<channel>_avg_pctMVC
%   .emg_<channel>_peak_pctMVC
%   --- BWS (if loadcell present) ---
%   .bws_pct_per_stride

    f = struct();

    % --- Robot per-side features ---
    if isstruct(session.robot)
        rPrime = session.robot(1);
    else
        rPrime = session.robot;
    end

    sideLR = {'L', 'R'};
    rows = [];

    for si = 1:2
        side = sideLR{si};
        sideField = lower(side); if strcmp(sideField,'l'), sideField = 'left'; else, sideField = 'right'; end
        sf = rPrime.(sideField);

        nStr = sf.nStrides;
        if nStr == 0, continue; end

        ft = rPrime.([sideField 'Force']);
        for k = 1:nStr
            row = struct();
            row.stride_idx        = numel(rows) + 1;
            row.side              = side;
            row.stride_time_s     = sf.strideTimes(k);
            row.cadence_steps_min = (60.0 / max(row.stride_time_s, eps)) * 2;
            if k <= numel(sf.strideLengths)
                row.stride_length_m = sf.strideLengths(k);
            else
                row.stride_length_m = NaN;
            end
            if k <= numel(ft.rmsePerStride)
                row.force_rmse_N = ft.rmsePerStride(k);
                row.force_mae_N  = ft.maePerStride(k);
            else
                row.force_rmse_N = NaN;  row.force_mae_N = NaN;
            end
            if k <= numel(sf.stancePct)
                row.stance_pct = sf.stancePct(k);
                row.swing_pct  = sf.swingPct(k);
            else
                row.stance_pct = NaN;  row.swing_pct = NaN;
            end

            % Placeholder NaNs for optional modalities (fill below)
            row.knee_peak_flex_deg     = NaN;
            row.knee_ROM_deg           = NaN;
            row.hip_peak_flex_deg      = NaN;
            row.hip_ROM_deg            = NaN;
            row.ankle_peak_dorsi_deg   = NaN;
            row.ankle_ROM_deg          = NaN;
            row.grf_peak_vert_N        = NaN;
            row.grf_peak_propulsion_N  = NaN;
            row.grf_impulse_AP_Ns      = NaN;
            row.bws_pct_per_stride     = NaN;

            rows = [rows; row];                                          %#ok<AGROW>
        end
    end

    % --- Motion features (if available) ---
    if ~isempty(session.motion) && isfield(session.motion, 'markers')
        try
            angles = hwalker.kinematics.computeJointAngles(session.motion);
            for k = 1:numel(rows)
                rows(k) = augmentMotionRow(rows(k), angles, session, k);
            end
        catch ME
            warning('hwalker:extractFeatures:motionFail', ...
                'Joint-angle extraction failed: %s', ME.message);
        end
    end

    % --- Force plate features ---
    if ~isempty(session.motion) && isfield(session.motion,'grf') && ~isempty(session.motion.grf)
        try
            grfFeats = hwalker.kinetics.grfFeatures(session.motion.grf);
            for k = 1:numel(rows)
                rows(k) = augmentGRFRow(rows(k), grfFeats, k);
            end
        catch ME
            warning('hwalker:extractFeatures:grfFail', ...
                'GRF feature extraction failed: %s', ME.message);
        end
    end

    % --- EMG features ---
    if ~isempty(session.emg)
        for ch = 1:numel(session.emg.channel_names)
            chName = matlab.lang.makeValidName(session.emg.channel_names{ch});
            avgFld  = sprintf('emg_%s_avg_pctMVC',  chName);
            peakFld = sprintf('emg_%s_peak_pctMVC', chName);
            for k = 1:numel(rows)
                if ~isnan(session.emg.normalized(:, ch))
                    v = session.emg.normalized(:, ch);
                else
                    v = session.emg.envelope(:, ch);
                end
                if isempty(v) || all(isnan(v))
                    rows(k).(avgFld)  = NaN;
                    rows(k).(peakFld) = NaN;
                else
                    rows(k).(avgFld)  = mean(v, 'omitnan');
                    rows(k).(peakFld) = max(v, [], 'omitnan');
                end
            end
        end
    end

    % --- BWS per stride ---
    if ~isempty(session.loadcell) && isfinite(session.loadcell.bws_pct_mean)
        for k = 1:numel(rows)
            rows(k).bws_pct_per_stride = session.loadcell.bws_pct_mean;
        end
    end

    % Convert struct array → struct of column vectors
    if isempty(rows)
        f = struct();
        return
    end
    fnames = fieldnames(rows);
    for i = 1:numel(fnames)
        vals = {rows.(fnames{i})};
        if all(cellfun(@(x) ischar(x) || isstring(x), vals))
            f.(fnames{i}) = vals(:);
        else
            f.(fnames{i}) = cell2mat(vals(:));
        end
    end
end


function row = augmentMotionRow(row, angles, ~, ~)
% Aggregate joint-angle features by side.
% Codex pass 9 fix: previously global means were copied to every stride —
% now we use the side-specific TRIAL-LEVEL summary (still constant across
% strides until per-stride detection is wired through). This is honest:
% same value across strides reflects that we don't yet have a per-stride
% breakdown of the marker time-series.
    sideLetter = upper(row.side);   % 'L' or 'R'
    knFld = ['knee_peak_flex_'  sideLetter];
    knROM = ['knee_ROM_'        sideLetter];
    hpFld = ['hip_peak_flex_'   sideLetter];
    hpROM = ['hip_ROM_'         sideLetter];
    anFld = ['ankle_peak_dorsi_' sideLetter];
    anROM = ['ankle_ROM_'        sideLetter];

    if isfield(angles, knFld), row.knee_peak_flex_deg   = double(angles.(knFld)); end
    if isfield(angles, knROM), row.knee_ROM_deg         = double(angles.(knROM)); end
    if isfield(angles, hpFld), row.hip_peak_flex_deg    = double(angles.(hpFld)); end
    if isfield(angles, hpROM), row.hip_ROM_deg          = double(angles.(hpROM)); end
    if isfield(angles, anFld), row.ankle_peak_dorsi_deg = double(angles.(anFld)); end
    if isfield(angles, anROM), row.ankle_ROM_deg        = double(angles.(anROM)); end
end

function row = augmentGRFRow(row, grfFeats, k)
% Per-stride GRF features.  Codex pass 9 fix: previously took mean across
% all stance phases (global summary copied to every stride). Now indexes
% the k-th stance phase if available; falls back to NaN otherwise.
    if isfield(grfFeats, 'peak_vertical_N') && k <= numel(grfFeats.peak_vertical_N)
        row.grf_peak_vert_N = grfFeats.peak_vertical_N(k);
    end
    if isfield(grfFeats, 'peak_propulsion_N') && k <= numel(grfFeats.peak_propulsion_N)
        row.grf_peak_propulsion_N = grfFeats.peak_propulsion_N(k);
    end
    if isfield(grfFeats, 'impulse_AP_Ns') && k <= numel(grfFeats.impulse_AP_Ns)
        row.grf_impulse_AP_Ns = grfFeats.impulse_AP_Ns(k);
    end
end

function m = nanmean1(x)
    if isempty(x), m = NaN; return; end
    x = x(isfinite(x));
    if isempty(x), m = NaN; else, m = mean(x); end
end
