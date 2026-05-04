function result = onsetReleaseRMSE_GCP(T, side, hsIdx, validMask, varargin)
% hwalker.force.onsetReleaseRMSE_GCP  Force RMSE within GCP [onset, release] window per stride.
%
%   r = hwalker.force.onsetReleaseRMSE_GCP(T, 'R', hsIdx, validMask)
%   r = hwalker.force.onsetReleaseRMSE_GCP(T, 'R', hsIdx, validMask, ...
%             'OnsetPct', 55, 'ReleasePct', 85)
%
% Definition (paper-grade, per-stride):
%   Each stride is time-normalized to 101 points (0-100 % gait cycle)
%   via hwalker.force.normalizedProfile.  RMSE is computed only on the
%   slice [OnsetPct, ReleasePct] of that 101-point profile.
%
% Default window 55-85 %  matches the H-Walker assist profile spec
% (onset 55 % GC, peak 70 % GC, release 85 % GC, 50 N target).
%
% Returns struct:
%   .window_pct           [onset, release]
%   .nStrides
%   .rmse_per_stride_N    K x 1
%   .mae_per_stride_N     K x 1
%   .peak_des_per_stride_N
%   .peak_act_per_stride_N
%   .latency_onset_ms     time from window-start to actual ≥ 0.5*peak_des,
%                          per stride (positive = actual lags)
%   .rmse_overall_N       quadratic-mean of per-stride RMSE
%   .mae_overall_N        mean of per-stride MAE
%
% Use this as the paper-reportable RMSE (specific to the cable assist
% pulse window).  For the threshold-based variant (segments where
% DesForce > threshold, ignoring stride structure) see onsetReleaseRMSE.m.

    p = inputParser;
    addParameter(p, 'OnsetPct',   55, @(x) isnumeric(x) && isscalar(x) && x >= 0 && x <= 100);
    addParameter(p, 'ReleasePct', 85, @(x) isnumeric(x) && isscalar(x) && x > 0 && x <= 100);
    parse(p, varargin{:});
    onsetPct   = p.Results.OnsetPct;
    releasePct = p.Results.ReleasePct;
    if releasePct <= onsetPct
        error('hwalker:onsetReleaseRMSE_GCP:badWindow', ...
            'ReleasePct (%g) must exceed OnsetPct (%g).', releasePct, onsetPct);
    end

    % stride-aligned 0-100% normalized force profiles (101 points each)
    fp = hwalker.force.normalizedProfile(T, side, hsIdx, validMask);

    result = struct( ...
        'window_pct',             [onsetPct, releasePct], ...
        'nStrides',               0, ...
        'rmse_per_stride_N',      [], ...
        'mae_per_stride_N',       [], ...
        'peak_des_per_stride_N',  [], ...
        'peak_act_per_stride_N',  [], ...
        'latency_onset_ms',       [], ...
        'rmse_overall_N',         NaN, ...
        'mae_overall_N',          NaN);

    if ~isfield(fp, 'des') || ~isfield(fp.des, 'individual') || isempty(fp.des.individual)
        return
    end

    desAll = fp.des.individual;     % K x 101
    actAll = fp.act.individual;     % K x 101
    K = size(desAll, 1);

    % Map percentage to 1-based column indices in a 101-point profile
    onsetIdx   = max(round(onsetPct)   + 1, 1);
    releaseIdx = min(round(releasePct) + 1, 101);

    rmse_per    = nan(K, 1);
    mae_per     = nan(K, 1);
    peak_des    = nan(K, 1);
    peak_act    = nan(K, 1);
    latency_per = nan(K, 1);

    % Time per percent of stride: per-stride duration / 100
    %  (we don't have absolute stride times here without hsIdx → derive ms)
    %  Fallback: average from hsIdx if available
    fs = NaN;
    try
        fs = hwalker.io.estimateSampleRate(T);
    catch
    end

    for k = 1:K
        des = desAll(k, onsetIdx:releaseIdx);
        act = actAll(k, onsetIdx:releaseIdx);
        err = act - des;
        ok  = isfinite(err);
        if any(ok)
            rmse_per(k) = sqrt(mean(err(ok).^2));
            mae_per(k)  = mean(abs(err(ok)));
        end
        peak_des(k) = max(des, [], 'omitnan');
        peak_act(k) = max(act, [], 'omitnan');

        % Latency: first sample (within window) where actual ≥ 0.5*peak_des
        target = 0.5 * peak_des(k);
        crossLocal = find(act >= target, 1, 'first');
        if ~isempty(crossLocal) && isfinite(fs) && k <= numel(hsIdx) - 1
            % sec per percent ≈ stride_duration / 100
            stride_dur_s = double(hsIdx(k+1) - hsIdx(k)) / fs;
            sec_per_pct  = stride_dur_s / 100;
            latency_per(k) = (crossLocal - 1) * sec_per_pct * 1000;   % ms
        end
    end

    result.nStrides              = K;
    result.rmse_per_stride_N     = rmse_per;
    result.mae_per_stride_N      = mae_per;
    result.peak_des_per_stride_N = peak_des;
    result.peak_act_per_stride_N = peak_act;
    result.latency_onset_ms      = latency_per;
    if any(isfinite(rmse_per))
        result.rmse_overall_N = sqrt(mean(rmse_per(isfinite(rmse_per)).^2));
        result.mae_overall_N  = mean(mae_per(isfinite(mae_per)));
    end
end
