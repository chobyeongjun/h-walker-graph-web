function t = timeAxis(T)
% hwalker.io.timeAxis  Return a seconds-axis from table T.
%
% Priority: Time_s / Timestamp / Time → Time_ms / time_ms → synthetic 111 Hz.

    for col = {'Time_s','Timestamp','Time','time'}
        if ismember(col{1}, T.Properties.VariableNames)
            t = double(T.(col{1})(:));
            if sum(isfinite(t)) >= 2, return; end
        end
    end
    for col = {'Time_ms','time_ms'}
        if ismember(col{1}, T.Properties.VariableNames)
            t = double(T.(col{1})(:)) / 1000.0;
            if sum(isfinite(t)) >= 2, return; end
        end
    end
    t = (0:height(T)-1)' / 111.0;
end
