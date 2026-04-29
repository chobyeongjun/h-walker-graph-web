function mask = detectZUPT(T, side, gyroThreshold)
% hwalker.stride.detectZUPT  Detect mid-stance (ZUPT) frames.
%
%   mask = hwalker.stride.detectZUPT(T, 'L')
%   mask = hwalker.stride.detectZUPT(T, 'L', 50)  % threshold in deg/s
%
% During mid-stance the foot is flat; gyro magnitude drops below threshold.
% Fallback: {side}_Phase < 0.5 (0 = stance in H-Walker firmware).
% Returns logical mask length N (same as height(T)).

    if nargin < 3, gyroThreshold = 50.0; end  % deg/s

    n = height(T);
    gxCol = [side '_Gx'];
    gyCol = [side '_Gy'];
    gzCol = [side '_Gz'];

    if all(ismember({gxCol, gyCol, gzCol}, T.Properties.VariableNames))
        gx = double(T.(gxCol)(:));
        gy = double(T.(gyCol)(:));
        gz = double(T.(gzCol)(:));
        gyroMag = sqrt(gx.^2 + gy.^2 + gz.^2);
        mask = gyroMag < gyroThreshold;
        return
    end

    phaseCol = [side '_Phase'];
    if ismember(phaseCol, T.Properties.VariableNames)
        phase = double(T.(phaseCol)(:));
        mask = phase < 0.5;
        return
    end

    mask = false(n, 1);
end
