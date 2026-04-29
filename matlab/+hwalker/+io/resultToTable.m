function T = resultToTable(result)
% hwalker.io.resultToTable  Convert analyzeFile result to per-stride table.
%
%   T = hwalker.io.resultToTable(result)
%
% Each row = one valid stride. Columns:
%   filename, side, strideIdx, strideTimeS, strideLengthM,
%   stancePct, swingPct, forceRMSE_N

    sides  = {'left','right'};
    labels = {'L','R'};

    rows = cell(0);
    for si = 1:2
        sf  = sides{si};
        slb = labels{si};
        if ~isfield(result, sf), continue; end
        sr = result.(sf);
        if sr.nStrides == 0, continue; end

        % strideTimes is NaN-aligned (length = nStrides_raw); only export valid rows
        n = numel(sr.strideTimes);
        for i = 1:n
            if ~sr.validMask(i), continue; end
            row.filename      = result.filename;
            row.side          = slb;
            row.strideIdx     = i;   % raw index (preserves original stride numbering)
            row.strideTimeS   = sr.strideTimes(i);

            if isfield(sr,'strideLengths') && i <= numel(sr.strideLengths)
                row.strideLengthM = sr.strideLengths(i);
            else
                row.strideLengthM = NaN;
            end

            if isfield(sr,'stancePct') && i <= numel(sr.stancePct)
                row.stancePct = sr.stancePct(i);
                row.swingPct  = sr.swingPct(i);
            else
                row.stancePct = NaN;
                row.swingPct  = NaN;
            end

            % Per-stride force RMSE
            ftField = [sf 'Force'];
            if isfield(result, ftField) && ...
               ~isempty(result.(ftField).rmsePerStride) && ...
               i <= numel(result.(ftField).rmsePerStride)
                row.forceRMSE_N = result.(ftField).rmsePerStride(i);
            else
                row.forceRMSE_N = NaN;
            end

            rows{end+1} = row; %#ok<AGROW>
        end
    end

    if isempty(rows)
        T = table();
        return
    end
    T = struct2table([rows{:}]);
end
