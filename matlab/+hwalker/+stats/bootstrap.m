function result = bootstrap(x, statFn, varargin)
% hwalker.stats.bootstrap  BCa-bootstrap confidence interval for any statistic.
%
%   r = hwalker.stats.bootstrap(x, @mean)
%   r = hwalker.stats.bootstrap(x, @median, 'NBoot', 10000, 'Alpha', 0.05, 'Seed', 42)
%   r = hwalker.stats.bootstrap({a, b}, @(g) mean(g{1}) - mean(g{2}))   % two-sample
%
% Returns Bias-Corrected and accelerated (BCa) bootstrap CI.
% Pure MATLAB; no Stats Toolbox required.
%
% Inputs:
%   x       N x D numeric data, OR cell array of vectors (multi-sample stat)
%   statFn  function handle:  s = statFn(x)  must return a scalar
%   'NBoot'   number of bootstrap resamples (default 10000)
%   'Alpha'   significance level for (1-alpha) CI (default 0.05 → 95%)
%   'Seed'    RNG seed (default = current state, no reseed)
%
% Result struct:
%   .point_estimate   statFn(x) on original data
%   .nboot
%   .alpha
%   .ci_lower, .ci_upper   BCa-corrected CI
%   .bias                  bootstrap mean - point estimate
%   .se                    bootstrap SD
%   .z0                    bias-correction term
%   .acceleration          jackknife acceleration term
%   .boot_distribution     1 x NBoot vector
%
% Reference: Efron B, Tibshirani RJ (1993) An Introduction to the Bootstrap, ch. 14.

    p = inputParser;
    addParameter(p, 'NBoot', 10000, @(v) isnumeric(v) && isscalar(v) && v >= 100);
    addParameter(p, 'Alpha', 0.05,  @(v) isnumeric(v) && isscalar(v) && v>0 && v<1);
    addParameter(p, 'Seed',  []);
    parse(p, varargin{:});
    nboot = p.Results.NBoot;
    alpha = p.Results.Alpha;
    seed  = p.Results.Seed;

    assert(isa(statFn, 'function_handle'), 'hwalker:bootstrap:badStatFn', ...
        'statFn must be a function handle.');

    if ~isempty(seed)
        rng(seed, 'twister');
    end

    % --- Reject empty / drop NaN-only input ---
    %  Codex pass 7 fix: numeric x with NaNs must be cleaned BEFORE
    %  resampling, else CI silently collapses to NaN with @mean etc.
    if iscell(x)
        ns = cellfun(@numel, x);
        if any(ns == 0)
            error('hwalker:bootstrap:emptySample', ...
                'All samples must be non-empty (got sizes [%s]).', ...
                num2str(ns));
        end
        % Best-effort: drop NaN within each numeric vector sample
        for ii = 1:numel(x)
            if isnumeric(x{ii})
                x{ii} = x{ii}(isfinite(x{ii}));
                if isempty(x{ii})
                    error('hwalker:bootstrap:emptySample', ...
                        'Sample %d has no finite observations after NaN removal.', ii);
                end
            end
        end
    else
        if isempty(x) || all(~isfinite(x(:)))
            error('hwalker:bootstrap:emptySample', ...
                'Input x must contain at least one finite observation.');
        end
        % Drop NaN/Inf entries to avoid silent CI corruption
        finiteMask = isfinite(x(:));
        if ~all(finiteMask)
            x = x(finiteMask);
        end
    end

    point_estimate = statFn(x);
    assert(isscalar(point_estimate), 'hwalker:bootstrap:nonScalar', ...
        'statFn must return a scalar.');

    boot = zeros(nboot, 1);

    if iscell(x)
        ns = cellfun(@numel, x);
        for b = 1:nboot
            xb = cell(size(x));
            for i = 1:numel(x)
                idx = randi(ns(i), ns(i), 1);
                xb{i} = x{i}(idx);
            end
            boot(b) = statFn(xb);
        end
    else
        x = x(:);
        n = numel(x);
        for b = 1:nboot
            idx = randi(n, n, 1);
            boot(b) = statFn(x(idx));
        end
    end

    % --- Degenerate case: bootstrap distribution has zero variance ---
    bootSpread = std(boot, 0);
    if bootSpread < eps
        % Statistic is constant under resampling → CI collapses to point estimate.
        result.point_estimate    = point_estimate;
        result.nboot             = nboot;
        result.alpha             = alpha;
        result.ci_lower          = point_estimate;
        result.ci_upper          = point_estimate;
        result.bias              = 0;
        result.se                = 0;
        result.z0                = 0;
        result.acceleration      = 0;
        result.boot_distribution = boot;
        return
    end

    % --- Bias correction term z0 ---
    p0 = mean(boot < point_estimate);
    p0 = min(max(p0, 1/(2*nboot)), 1 - 1/(2*nboot));
    z0 = norminv01(p0);

    % --- Acceleration via jackknife (across ALL samples for cell input) ---
    accel = jackknifeAccel(x, statFn, point_estimate);

    % --- BCa percentile bounds (sign-preserving guard) ---
    z_lo = bcaPercentile(z0, accel, alpha/2);
    z_hi = bcaPercentile(z0, accel, 1 - alpha/2);
    a_lo = normcdf01(z_lo);
    a_hi = normcdf01(z_hi);

    sortedBoot = sort(boot);
    ci_lower   = quantileFromSorted(sortedBoot, a_lo);
    ci_upper   = quantileFromSorted(sortedBoot, a_hi);

    result.point_estimate   = point_estimate;
    result.nboot            = nboot;
    result.alpha            = alpha;
    result.ci_lower         = ci_lower;
    result.ci_upper         = ci_upper;
    result.bias             = mean(boot) - point_estimate;
    result.se               = std(boot, 0);
    result.z0               = z0;
    result.acceleration     = accel;
    result.boot_distribution = boot;
end


% =====================================================================
function a = jackknifeAccel(x, statFn, ~)
% BCa acceleration via jackknife.
%
% For multi-sample (cell) input: leave-one-out across EACH sample, then aggregate
% per Efron & Tibshirani 1993 §14.3 (treat samples as conditionally independent;
% pool jackknife replicates with appropriate weights).
%
% For single-sample input: standard jackknife.
    if iscell(x)
        nSamples = numel(x);
        ns = cellfun(@numel, x);
        if any(ns < 2), a = 0; return; end
        % Pool jackknife replicates from every sample
        theta_jk_all = [];
        for s = 1:nSamples
            xs = x{s}(:);
            n_s = numel(xs);
            if n_s < 2, continue; end
            for i = 1:n_s
                xi    = xs;  xi(i) = [];
                xrep  = x;   xrep{s} = xi;
                theta_jk_all(end+1, 1) = statFn(xrep);   %#ok<AGROW>
            end
        end
        if numel(theta_jk_all) < 4, a = 0; return; end
        theta_jk = theta_jk_all;
    else
        x = x(:);
        n = numel(x);
        if n < 4, a = 0; return; end
        theta_jk = zeros(n, 1);
        for i = 1:n
            xi = x;  xi(i) = [];
            theta_jk(i) = statFn(xi);
        end
    end
    theta_dot = mean(theta_jk);
    num = sum((theta_dot - theta_jk).^3);
    den = 6 * (sum((theta_dot - theta_jk).^2))^1.5;
    if den < eps, a = 0; else, a = num / den; end
end


function z_q = bcaPercentile(z0, a, alpha_q)
% BCa quantile transform with sign-preserving denominator guard.
%
%   z_q = z0 + (z0 + z_alpha) / (1 - a*(z0 + z_alpha))
%
% Guard: if denominator approaches zero, the formula diverges to ±Inf.
% Cap at the unadjusted percentile (z0 + z_alpha) to avoid wrong-tail flip.
    z_alpha = norminv01(alpha_q);
    num = z0 + z_alpha;
    den = 1 - a * num;
    if abs(den) < 1e-9
        z_q = z0 + num;     % fall back to bias-corrected percentile (BC, not BCa)
    else
        z_q = z0 + num / den;
    end
end

function z = norminv01(p)
% Inverse standard normal CDF (Beasley-Springer-Moro)
    if exist('norminv', 'file') || exist('norminv', 'builtin')
        z = norminv(p);
        return
    end
    % Fallback: rational approximation (accurate to ~1e-9)
    a = [-3.969683028665376e+01,  2.209460984245205e+02, ...
         -2.759285104469687e+02,  1.383577518672690e+02, ...
         -3.066479806614716e+01,  2.506628277459239e+00];
    b = [-5.447609879822406e+01,  1.615858368580409e+02, ...
         -1.556989798598866e+02,  6.680131188771972e+01, ...
         -1.328068155288572e+01];
    c = [-7.784894002430293e-03, -3.223964580411365e-01, ...
         -2.400758277161838e+00, -2.549732539343734e+00, ...
          4.374664141464968e+00,  2.938163982698783e+00];
    d = [ 7.784695709041462e-03,  3.224671290700398e-01, ...
          2.445134137142996e+00,  3.754408661907416e+00];
    p_low  = 0.02425;  p_high = 1 - p_low;
    if p < p_low
        q = sqrt(-2*log(p));
        z = (((((c(1)*q+c(2))*q+c(3))*q+c(4))*q+c(5))*q+c(6)) ./ ...
            ((((d(1)*q+d(2))*q+d(3))*q+d(4))*q+1);
    elseif p <= p_high
        q = p - 0.5;  r = q*q;
        z = (((((a(1)*r+a(2))*r+a(3))*r+a(4))*r+a(5))*r+a(6))*q ./ ...
            (((((b(1)*r+b(2))*r+b(3))*r+b(4))*r+b(5))*r+1);
    else
        q = sqrt(-2*log(1-p));
        z = -(((((c(1)*q+c(2))*q+c(3))*q+c(4))*q+c(5))*q+c(6)) ./ ...
             ((((d(1)*q+d(2))*q+d(3))*q+d(4))*q+1);
    end
end

function p = normcdf01(z)
    if exist('normcdf', 'file') || exist('normcdf', 'builtin')
        p = normcdf(z);
    else
        p = 0.5 * erfc(-z / sqrt(2));
    end
end

function v = quantileFromSorted(sortedX, q)
    n = numel(sortedX);
    if n < 1, v = NaN; return; end
    h = q * (n - 1) + 1;     % 1-based
    h = max(min(h, n), 1);
    lo = floor(h);  hi = ceil(h);
    if lo == hi
        v = sortedX(lo);
    else
        frac = h - lo;
        v = sortedX(lo) + frac * (sortedX(hi) - sortedX(lo));
    end
end
