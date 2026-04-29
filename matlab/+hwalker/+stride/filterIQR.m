function [filtered, validMask] = filterIQR(strideTimes, multiplier)
% hwalker.stride.filterIQR  Remove outlier strides using IQR method.
%
%   [filtered, mask] = hwalker.stride.filterIQR(strideTimes)
%   [filtered, mask] = hwalker.stride.filterIQR(strideTimes, 2.0)
%
% Absolute bounds enforced: [0.3 s, 5.0 s] (physiological walking range).
% Returns original array unchanged when n < 4.

    if nargin < 2, multiplier = 2.0; end
    strideTimes = strideTimes(:);
    n = numel(strideTimes);

    if n < 4
        filtered  = strideTimes;
        validMask = true(n, 1);
        return
    end

    q1 = prctile(strideTimes, 25);
    q3 = prctile(strideTimes, 75);
    iqr = q3 - q1;
    lower = max(q1 - multiplier * iqr, 0.3);
    upper = min(q3 + multiplier * iqr, 5.0);

    validMask = strideTimes >= lower & strideTimes <= upper;
    filtered  = strideTimes(validMask);
end
