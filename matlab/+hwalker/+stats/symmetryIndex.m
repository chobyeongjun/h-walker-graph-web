function si = symmetryIndex(leftVal, rightVal)
% hwalker.stats.symmetryIndex  |L-R| / mean(L,R) × 100.
%
%   si = hwalker.stats.symmetryIndex(1.0, 2.0)  % → 66.67
%
% Returns -1 when either side is missing (≤ 0).

    if leftVal <= 0 || rightVal <= 0
        si = -1;
        return
    end
    si = abs(leftVal - rightVal) / ((leftVal + rightVal) / 2) * 100;
end
