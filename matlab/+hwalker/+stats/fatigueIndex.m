function fi = fatigueIndex(values, pct)
% hwalker.stats.fatigueIndex  % change: first pct vs last pct of values.
%
%   fi = hwalker.stats.fatigueIndex(strideTimes)        % default pct=0.1
%   fi = hwalker.stats.fatigueIndex(strideTimes, 0.15)
%
% Returns 0 when n < 10 or baseline ≈ 0.

    if nargin < 2, pct = 0.1; end
    values = values(:);
    values = values(isfinite(values));   % drop NaN/Inf — codex pass 7 fix
    n = numel(values);
    if n < 10
        fi = 0;
        return
    end
    k     = max(2, round(n * pct));
    first = mean(values(1:k));
    last  = mean(values(end-k+1:end));
    if abs(first) < 1e-12
        fi = 0;
        return
    end
    fi = (last - first) / abs(first) * 100;
end
