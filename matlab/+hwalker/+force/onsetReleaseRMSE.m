function result = onsetReleaseRMSE(T, side, varargin)
% hwalker.force.onsetReleaseRMSE  Force-tracking RMSE within onset→release windows only.
%
%   r = hwalker.force.onsetReleaseRMSE(T, 'R')
%   r = hwalker.force.onsetReleaseRMSE(T, 'L', 'Threshold', 1.0)
%   r = hwalker.force.onsetReleaseRMSE(T, 'R', 'Restrict', 'sync')
%   r = hwalker.force.onsetReleaseRMSE(T, 'R', 'SegMinDurMs', 100)
%
% Definition:
%   Onset  = sample where DesForce crosses Threshold upward
%   Release = sample where DesForce crosses Threshold downward
%   Each [onset, release] pair is one "active segment".
%   RMSE_seg(k)  = sqrt(mean((Act - Des)^2))   over segment k
%   RMSE_overall = sqrt(mean(RMSE_seg.^2))     pooled across segments
%
% Name-value:
%   'Threshold'    desired-force threshold defining active (default 1.0 N)
%   'Restrict'     'all' | 'sync' (default 'all')
%                  'sync' restricts to within the sync cycle (uses
%                  hwalker.sync.findWindows on T)
%   'SegMinDurMs'  drop segments shorter than this (default 100 ms)
%
% Returns struct:
%   .nSegments
%   .segments              N x 2 [onset_s, release_s]
%   .duration_per_seg_s
%   .peak_des_per_seg_N    desired-force peak in each segment (should ~= 50N)
%   .peak_act_per_seg_N    actual-force peak in each segment
%   .rmse_per_seg_N        per-segment RMSE
%   .mae_per_seg_N         per-segment MAE
%   .latency_onset_ms      lag between desired onset and first |actual| > 0.5*peak
%                          (positive = actual lags behind)
%   .rmse_overall_N        pooled RMSE across segments
%   .mae_overall_N         pooled MAE
%   .threshold_used        copy of Threshold

    p = inputParser;
    addParameter(p, 'Threshold',   1.0,    @(x) isnumeric(x) && isscalar(x) && x >= 0);
    addParameter(p, 'Restrict',    'all',  @(x) any(strcmpi(x, {'all','sync'})));
    addParameter(p, 'SegMinDurMs', 100,    @(x) isnumeric(x) && isscalar(x) && x >= 0);
    parse(p, varargin{:});
    thresh   = p.Results.Threshold;
    restrict = lower(p.Results.Restrict);
    minDurMs = p.Results.SegMinDurMs;

    side = upper(side(1));
    desCol = sprintf('%s_DesForce_N', side);
    actCol = sprintf('%s_ActForce_N', side);
    if ~all(ismember({desCol, actCol}, T.Properties.VariableNames))
        error('hwalker:onsetReleaseRMSE:missingCol', ...
            'Columns %s / %s not in table.', desCol, actCol);
    end

    t   = hwalker.io.timeAxis(T);
    des = T.(desCol);
    act = T.(actCol);
    fs  = 1 / median(diff(t(isfinite(t))));
    minDurSamples = max(round(minDurMs / 1000 * fs), 1);

    % --- Restrict to sync window if requested ---
    keepMask = true(numel(t), 1);
    if strcmp(restrict, 'sync')
        cycles = hwalker.sync.findWindows(T);
        if ~isempty(cycles)
            keepMask = false(numel(t), 1);
            for k = 1:size(cycles, 1)
                keepMask(t >= cycles(k, 1) & t < cycles(k, 2)) = true;
            end
        end
    end

    % --- Detect active segments (DesForce > threshold) ---
    active = des > thresh & keepMask;
    d = diff([0; active(:); 0]);
    starts = find(d == 1);
    stops  = find(d == -1) - 1;
    keep   = (stops - starts + 1) >= minDurSamples;
    starts = starts(keep);
    stops  = stops(keep);

    nSeg = numel(starts);
    segments        = zeros(nSeg, 2);
    duration        = zeros(nSeg, 1);
    peak_des        = zeros(nSeg, 1);
    peak_act        = zeros(nSeg, 1);
    rmse_per        = zeros(nSeg, 1);
    mae_per         = zeros(nSeg, 1);
    latency_per     = zeros(nSeg, 1);

    for k = 1:nSeg
        idx = starts(k):stops(k);
        seg_t   = t(idx);
        seg_des = des(idx);
        seg_act = act(idx);
        err = seg_act - seg_des;
        ok = isfinite(err);
        if any(ok)
            rmse_per(k) = sqrt(mean(err(ok).^2));
            mae_per(k)  = mean(abs(err(ok)));
        else
            rmse_per(k) = NaN;  mae_per(k) = NaN;
        end
        peak_des(k) = max(seg_des, [], 'omitnan');
        peak_act(k) = max(seg_act, [], 'omitnan');
        segments(k, :) = [seg_t(1), seg_t(end)];
        duration(k)    = seg_t(end) - seg_t(1);

        % Latency: time from desired-onset to actual ≥ 0.5 * peak_des
        target = 0.5 * peak_des(k);
        crossIdx = find(seg_act >= target, 1, 'first');
        if ~isempty(crossIdx)
            latency_per(k) = (seg_t(crossIdx) - seg_t(1)) * 1000;   % ms
        else
            latency_per(k) = NaN;
        end
    end

    result = struct();
    result.nSegments         = nSeg;
    result.segments          = segments;
    result.duration_per_seg_s= duration;
    result.peak_des_per_seg_N= peak_des;
    result.peak_act_per_seg_N= peak_act;
    result.rmse_per_seg_N    = rmse_per;
    result.mae_per_seg_N     = mae_per;
    result.latency_onset_ms  = latency_per;
    result.threshold_used    = thresh;
    result.restrict          = restrict;

    if nSeg == 0
        result.rmse_overall_N = NaN;
        result.mae_overall_N  = NaN;
    else
        % Pool RMSE in quadrature mean (RMS of per-segment RMSE)
        % Equivalent to sqrt of mean error^2 over all samples in active segments
        result.rmse_overall_N = sqrt(mean(rmse_per.^2, 'omitnan'));
        result.mae_overall_N  = mean(mae_per, 'omitnan');
    end
end
