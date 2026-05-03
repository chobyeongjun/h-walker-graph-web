function [filtered, validMask, reasons] = filterIQR(strideTimes, varargin)
% hwalker.stride.filterIQR  Remove outlier strides using IQR method + absolute bounds.
%
%   [filtered, mask]          = hwalker.stride.filterIQR(strideTimes)
%   [filtered, mask]          = hwalker.stride.filterIQR(strideTimes, 2.0)        % legacy positional
%   [filtered, mask, reasons] = hwalker.stride.filterIQR(strideTimes, ...)
%   [filtered, mask, reasons] = hwalker.stride.filterIQR(strideTimes, ...
%                                   'Multiplier', 2.0, 'Bounds', [0.3 5.0])
%
% Outlier rule:  exclude any stride outside  [max(Q1 - k*IQR, lower),  min(Q3 + k*IQR, upper)]
%
% Default bounds [0.3, 5.0] s reflect the physiological walking range —
% bounds should be widened (or relaxed) for clinical populations with severe
% spasticity / very slow gait. Always report the bounds used in the Methods
% section.
%
% Returns:
%   filtered   N_kept x 1  surviving stride times
%   validMask  N x 1 logical  (true = kept)
%   reasons    struct with counts:
%       .nTotal           input length
%       .nKept            count where validMask is true
%       .nOutlierIQR      excluded by IQR rule (within absolute bounds)
%       .nBelowBound      excluded for being < lower absolute bound
%       .nAboveBound      excluded for being > upper absolute bound
%       .multiplier       k value used
%       .boundsRequested  [lower, upper] absolute bounds the caller passed
%       .boundsEffective  [effLower, effEffective] after IQR intersection
%
% n < 4 returns the input unchanged with mask all-true.

    p = inputParser;
    p.KeepUnmatched = false;

    % Backward compat: filterIQR(times, 2.0) → 'Multiplier', 2.0
    if numel(varargin) == 1 && isnumeric(varargin{1}) && isscalar(varargin{1})
        varargin = {'Multiplier', varargin{1}};
    end

    addParameter(p, 'Multiplier', 2.0, @(x) isnumeric(x) && isscalar(x) && x > 0);
    addParameter(p, 'Bounds',     [0.3, 5.0], @(x) isnumeric(x) && numel(x) == 2 && x(2) > x(1));
    parse(p, varargin{:});
    multiplier = p.Results.Multiplier;
    bounds     = p.Results.Bounds;

    strideTimes = strideTimes(:);
    n = numel(strideTimes);

    reasons = struct( ...
        'nTotal',          n, ...
        'nKept',           n, ...
        'nOutlierIQR',     0, ...
        'nBelowBound',     0, ...
        'nAboveBound',     0, ...
        'multiplier',      multiplier, ...
        'boundsRequested', bounds(:)', ...
        'boundsEffective', bounds(:)');

    if n < 4
        filtered  = strideTimes;
        validMask = true(n, 1);
        return
    end

    finiteIdx = isfinite(strideTimes);
    if sum(finiteIdx) < 4
        filtered  = strideTimes(finiteIdx);
        validMask = finiteIdx;
        reasons.nKept = sum(finiteIdx);
        return
    end

    q1  = prctile(strideTimes(finiteIdx), 25);
    q3  = prctile(strideTimes(finiteIdx), 75);
    iqr = q3 - q1;

    iqrLower = q1 - multiplier * iqr;
    iqrUpper = q3 + multiplier * iqr;

    effLower = max(iqrLower, bounds(1));
    effUpper = min(iqrUpper, bounds(2));
    reasons.boundsEffective = [effLower, effUpper];

    validMask = finiteIdx & strideTimes >= effLower & strideTimes <= effUpper;
    filtered  = strideTimes(validMask);

    % --- Categorize exclusions for reporting ---
    excluded   = finiteIdx & ~validMask;
    belowAbs   = excluded & strideTimes < bounds(1);
    aboveAbs   = excluded & strideTimes > bounds(2);
    outlierIQR = excluded & ~belowAbs & ~aboveAbs;

    reasons.nKept        = sum(validMask);
    reasons.nOutlierIQR  = sum(outlierIQR);
    reasons.nBelowBound  = sum(belowAbs);
    reasons.nAboveBound  = sum(aboveAbs);
end
