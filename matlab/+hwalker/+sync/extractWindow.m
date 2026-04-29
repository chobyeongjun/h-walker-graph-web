function Tw = extractWindow(T, t_start, t_end)
% hwalker.sync.extractWindow  Slice table to [t_start, t_end] and rebase time to 0.
%
%   cycles = hwalker.sync.findWindows(T);
%   Tw = hwalker.sync.extractWindow(T, cycles(1,1), cycles(1,2));
%
% All time columns in the sliced table are rebased so t_start → 0.

    t    = hwalker.io.timeAxis(T);
    % Half-open interval: include t_start, exclude t_end (prevents overlap between cycles)
    mask = t >= t_start & t < t_end;
    Tw   = T(mask, :);

    if isempty(Tw), return; end

    % Rebase millisecond columns
    for col = {'Time_ms','time_ms'}
        if ismember(col{1}, Tw.Properties.VariableNames)
            Tw.(col{1}) = Tw.(col{1}) - Tw.(col{1})(1);
        end
    end
    % Rebase second columns
    for col = {'Time_s','Time','time','Timestamp'}
        if ismember(col{1}, Tw.Properties.VariableNames)
            Tw.(col{1}) = Tw.(col{1}) - Tw.(col{1})(1);
        end
    end
end
