function d = effectSize(a, b)
% hwalker.stats.effectSize  Cohen's d for two independent or paired samples.
%
%   d = hwalker.stats.effectSize(groupA, groupB)
%
% Uses pooled SD (independent-samples formula).
% For paired comparisons use pairedTest which computes paired Cohen's d.
%
% Returns NaN when either group has < 2 valid values or zero pooled SD.

    a = a(isfinite(a(:)));
    b = b(isfinite(b(:)));

    if numel(a) < 2 || numel(b) < 2
        d = NaN;
        return
    end

    nA = numel(a);  nB = numel(b);
    sA = std(a);    sB = std(b);

    % Pooled SD
    sp = sqrt(((nA - 1)*sA^2 + (nB - 1)*sB^2) / (nA + nB - 2));
    if sp < 1e-12
        d = 0;
        return
    end

    d = (mean(a) - mean(b)) / sp;
end
