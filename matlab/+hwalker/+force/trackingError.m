function result = trackingError(T, side, hsIdx, validMask)
% hwalker.force.trackingError  Force tracking error metrics (Des vs Act).
%
%   ft = hwalker.force.trackingError(T, 'L', hsIdx, validMask)
%
% Fields returned:
%   ft.rmse          overall RMSE across all valid strides (N)
%   ft.mae           overall MAE  (N)
%   ft.peakError     max |error|  (N)
%   ft.rmsePerStride Kx1 vector of per-stride RMSE
%   ft.maePerStride  Kx1 vector of per-stride MAE
%
% Returns zero-filled struct when force columns are missing.

    desCol = [side '_DesForce_N'];
    actCol = [side '_ActForce_N'];

    result.rmse          = 0;
    result.mae           = 0;
    result.peakError     = 0;
    result.rmsePerStride = [];
    result.maePerStride  = [];

    if ~ismember(desCol, T.Properties.VariableNames) || ...
       ~ismember(actCol, T.Properties.VariableNames)
        return
    end

    des      = double(T.(desCol)(:));
    act      = double(T.(actCol)(:));
    nStrides = numel(validMask);

    rmseList  = nan(nStrides, 1);
    maeList   = nan(nStrides, 1);
    allErrors = [];

    for i = 1:nStrides
        if ~validMask(i), continue; end
        s = double(hsIdx(i));
        e = double(hsIdx(i + 1));
        if e - s < 10, continue; end

        err      = act(s:e-1) - des(s:e-1);
        validErr = err(isfinite(err));
        if isempty(validErr), continue; end

        rmseList(i) = sqrt(mean(validErr .^ 2));
        maeList(i)  = mean(abs(validErr));
        allErrors   = [allErrors; validErr]; %#ok<AGROW>
    end

    if ~isempty(allErrors)
        result.rmse      = sqrt(mean(allErrors .^ 2));
        result.mae       = mean(abs(allErrors));
        result.peakError = max(abs(allErrors));
    end
    result.rmsePerStride = rmseList(~isnan(rmseList));
    result.maePerStride  = maeList(~isnan(maeList));
end
