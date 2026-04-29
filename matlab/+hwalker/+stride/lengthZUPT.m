function lengths = lengthZUPT(T, side, hsIdx, validMask, fs)
% hwalker.stride.lengthZUPT  Per-stride length via ZUPT velocity integration.
%
%   lengths = hwalker.stride.lengthZUPT(T, 'L', hsIdx, validMask)
%   lengths = hwalker.stride.lengthZUPT(T, 'L', hsIdx, validMask, fs)
%
% EBIMU soa5 column mapping:
%   {side}_Ax = Global Velocity X (m/s)   ← NOT acceleration
%   {side}_Ay = Global Velocity Y (m/s)
%
% ZUPT error-offset accumulation (not hard-zeroing):
%   During mid-stance (gyro < threshold) the measured velocity IS the
%   accumulated drift error. Record it as offset; subtract on every frame.
%   Single integration: corrected velocity → horizontal displacement.
%
% Warns when median stride length is outside [0.05, 3.0] m.

    if nargin < 5, fs = hwalker.io.estimateSampleRate(T); end

    vxCol = [side '_Ax'];
    vyCol = [side '_Ay'];

    nStrides = numel(validMask);
    lengths  = nan(nStrides, 1);

    if ~ismember(vxCol, T.Properties.VariableNames) || ...
       ~ismember(vyCol, T.Properties.VariableNames)
        return
    end

    vx = double(T.(vxCol)(:));
    vy = double(T.(vyCol)(:));
    n  = numel(vx);

    % ZUPT mask (mid-stance = foot flat on ground)
    isZUPT = hwalker.stride.detectZUPT(T, side);

    % Frame-by-frame ZUPT error-offset correction
    % offset = last raw velocity seen during a ZUPT frame
    vxC = zeros(n, 1);
    vyC = zeros(n, 1);
    ox = 0; oy = 0;
    for j = 1:n
        vxC(j) = vx(j) - ox;
        vyC(j) = vy(j) - oy;
        if isZUPT(j)
            ox = vx(j);
            oy = vy(j);
        end
    end

    % Integrate corrected velocity → position
    dt = 1.0 / fs;
    px = cumsum(vxC) * dt;
    py = cumsum(vyC) * dt;

    % Stride length = Euclidean displacement between consecutive heel strikes
    for i = 1:nStrides
        if ~validMask(i), continue; end
        s = double(hsIdx(i));
        e = double(hsIdx(i + 1));
        if e - s < 10, continue; end
        dx = px(e) - px(s);
        dy = py(e) - py(s);
        lengths(i) = sqrt(dx^2 + dy^2);
    end

    % Sanity check
    valid = lengths(isfinite(lengths));
    if ~isempty(valid)
        med = median(valid);
        if med < 0.05 || med > 3.0
            warning('hwalker:stride:suspiciousLength', ...
                '%s median stride length = %.3f m (expected 0.3-2.0 m). Check IMU columns.', ...
                side, med);
        end
    end
end
