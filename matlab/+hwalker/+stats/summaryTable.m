function T = summaryTable(results, field, varargin)
% hwalker.stats.summaryTable  Per-file summary table with stats for one metric.
%
%   T = hwalker.stats.summaryTable(results, 'left.strideTimeMean')
%   T = hwalker.stats.summaryTable(results, 'left.strideTimeMean', ...
%           'alpha', 0.05, 'ci', 0.95)
%
% INPUT
%   results  : array of analyzeFile result structs (1 per trial/file)
%   field    : dot-path into the result struct, e.g.
%              'left.strideTimeMean'  → result(i).left.strideTimeMean
%              'strideTimeSymmetry'  → result(i).strideTimeSymmetry
%              'leftForce.rmse'      → result(i).leftForce.rmse
%
% OUTPUT table columns:
%   filename, value, mean_all, sd_all, ci_lo, ci_hi, cv_pct, n
%
% The last row is a summary row (filename = 'SUMMARY').
%
% Example for comparing two conditions:
%   preResults  = arrayfun(@hwalker.analyzeFile, preFiles,  'Uni', 0);
%   postResults = arrayfun(@hwalker.analyzeFile, postFiles, 'Uni', 0);
%   Tpre  = hwalker.stats.summaryTable([preResults{:}],  'left.strideTimeMean');
%   Tpost = hwalker.stats.summaryTable([postResults{:}], 'left.strideTimeMean');
%   r = hwalker.stats.pairedTest(Tpre.value(1:end-1), Tpost.value(1:end-1));

    p = inputParser;
    addParameter(p, 'alpha', 0.05);
    addParameter(p, 'ci',    0.95);
    parse(p, varargin{:});
    alpha = p.Results.alpha;
    ci    = p.Results.ci;

    n = numel(results);
    filenames = cell(n, 1);
    values    = nan(n, 1);

    parts = strsplit(field, '.');

    for i = 1:n
        r = results(i);
        try
            for pj = 1:numel(parts)
                r = r.(parts{pj});
            end
            values(i) = double(r);
        catch
            values(i) = NaN;
        end
        if isfield(results(i), 'filename')
            filenames{i} = results(i).filename;
        else
            filenames{i} = sprintf('trial_%02d', i);
        end
    end

    valid = isfinite(values);
    m     = mean(values(valid));
    s     = std(values(valid));
    nv    = sum(valid);
    cv    = NaN;
    if m ~= 0 && nv > 0
        cv = s / abs(m) * 100;
    end

    % Confidence interval (t-distribution): use ci level directly
    ci_lo = NaN;  ci_hi = NaN;
    if nv >= 2 && exist('tinv', 'file')
        t_crit = tinv((1 + ci) / 2, nv - 1);  % ci=0.95 → tinv(0.975, df)
        se     = s / sqrt(nv);
        ci_lo  = m - t_crit * se;
        ci_hi  = m + t_crit * se;
    end

    % Per-file rows + summary row
    allNames = [filenames; {'SUMMARY'}];
    allVals  = [values;    m];
    T = table(allNames, allVals, ...
        'VariableNames', {'filename', 'value'});
    T.mean_all(:) = m;
    T.sd_all(:)   = s;
    T.ci_lo(:)    = ci_lo;
    T.ci_hi(:)    = ci_hi;
    T.cv_pct(:)   = cv;
    T.n(:)        = nv;
    T.metric(:)   = {field};
end
