function fs = estimateSampleRate(T)
% hwalker.io.estimateSampleRate  Estimate sample rate from table time column.
%
%   fs = hwalker.io.estimateSampleRate(T)
%
% Priority: Time_ms median diff → Time_s median diff → 111 Hz (Teensy default).

    for col = {'Time_ms','time_ms'}
        if ismember(col{1}, T.Properties.VariableNames)
            t = double(T.(col{1})(:));
            t = t(isfinite(t));
            if numel(t) > 1
                dt_ms = median(diff(t));
                if dt_ms > 0
                    fs = 1000.0 / dt_ms;
                    return
                end
            end
        end
    end
    for col = {'Time_s','Time','time','Timestamp'}
        if ismember(col{1}, T.Properties.VariableNames)
            t = double(T.(col{1})(:));
            t = t(isfinite(t));
            if numel(t) > 1
                dt = median(diff(t));
                if dt > 0
                    fs = 1.0 / dt;
                    return
                end
            end
        end
    end
    fs = 111.0;
end
