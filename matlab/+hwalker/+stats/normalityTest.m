function result = normalityTest(x)
% hwalker.stats.normalityTest  Lilliefors normality test (n ≥ 4).
%
%   r = hwalker.stats.normalityTest(strideTimes)
%
% Result struct:
%   .n          number of valid values
%   .h          1 = reject normality at α=0.05
%   .p          p-value (NaN when toolbox unavailable)
%   .is_normal  true when p > 0.05
%
% Uses lillietest (Statistics Toolbox). Returns h=0 (assume normal) when
% the toolbox is unavailable or n < 4.

    x = x(isfinite(x(:)));
    result.n         = numel(x);
    result.h         = false;
    result.p         = NaN;
    result.is_normal = true;

    if numel(x) < 4
        return
    end

    if exist('lillietest', 'file') || exist('lillietest', 'builtin')
        [h, p] = lillietest(x);
        result.h         = h;
        result.p         = p;
        result.is_normal = ~h;
    end
end
