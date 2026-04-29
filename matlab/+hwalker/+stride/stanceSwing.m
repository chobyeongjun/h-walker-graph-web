function [stancePct, swingPct] = stanceSwing(T, side, hsIdx, validMask)
% hwalker.stride.stanceSwing  Compute stance/swing % per stride from GCP.
%
%   [stance, swing] = hwalker.stride.stanceSwing(T, 'L', hsIdx, validMask)
%
% Uses {side}_GCP active fraction (GCP > 0.01) per stride.
% GCP sawtooth ramps during stance, flat during swing.
% Returns NaN for strides with missing or insufficient GCP data.

    gcpCol    = [side '_GCP'];
    nStrides  = numel(validMask);
    stancePct = nan(nStrides, 1);
    swingPct  = nan(nStrides, 1);

    if ~ismember(gcpCol, T.Properties.VariableNames), return; end

    gcp = double(T.(gcpCol)(:));

    for i = 1:nStrides
        if ~validMask(i), continue; end
        s = double(hsIdx(i));
        e = double(hsIdx(i+1));
        if e - s < 5, continue; end

        strideGCP = gcp(s:e-1);
        finiteIdx = isfinite(strideGCP);
        if sum(finiteIdx) < 5, continue; end

        active   = strideGCP(finiteIdx) > 0.01;
        nStance  = sum(active);
        total    = sum(finiteIdx);
        stancePct(i) = nStance / total * 100;
        swingPct(i)  = (total - nStance) / total * 100;
    end
end
