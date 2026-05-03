function result = leveneTest(groups, varargin)
% hwalker.stats.leveneTest  Brown-Forsythe (median-based Levene) homogeneity-of-variance test.
%
%   r = hwalker.stats.leveneTest({groupA, groupB, groupC})
%
% More robust to non-normality than the original (mean-based) Levene test.
% NaNs are dropped per group.
%
% Result struct:
%   .k          number of groups
%   .N          total n
%   .W          test statistic (F-distributed under H0)
%   .df1, .df2  degrees of freedom
%   .p          p-value (H0 = equal variances)
%   .h          1 = reject H0 at .alpha (default 0.05)
%   .alpha
%   .group_medians, .mean_abs_dev_per_group
%
% Reference: Brown & Forsythe (1974) JASA 69:364-367.

    p = inputParser;
    addParameter(p, 'Alpha', 0.05, @(x) isnumeric(x) && isscalar(x) && x>0 && x<1);
    parse(p, varargin{:});
    alpha = p.Results.Alpha;

    if iscell(groups)
        data = cellfun(@(x) x(isfinite(x(:))), groups, 'UniformOutput', false);
    elseif isstruct(groups)
        data = arrayfun(@(s) s.data(isfinite(s.data(:))), groups, 'UniformOutput', false);
    else
        error('hwalker:leveneTest:badInput', 'groups must be cell or struct array.');
    end

    k = numel(data);
    assert(k >= 2, 'hwalker:leveneTest:tooFewGroups', 'Need >= 2 groups.');

    n_per_group = cellfun(@numel, data);
    assert(all(n_per_group >= 2), 'hwalker:leveneTest:tooSmall', ...
        'Each group needs >= 2 finite observations.');

    N = sum(n_per_group);

    % --- Step 1: replace each value with |x - median(group)| ---
    z = cell(k, 1);
    medians = zeros(k, 1);
    for i = 1:k
        medians(i) = median(data{i});
        z{i}       = abs(data{i} - medians(i));
    end

    % --- Step 2: one-way ANOVA on z ---
    z_means = cellfun(@mean, z);
    z_grand = mean(cat(1, z{:}));

    ss_between = sum(n_per_group(:) .* (z_means(:) - z_grand).^2);
    ss_within  = 0;
    for i = 1:k
        ss_within = ss_within + sum((z{i} - z_means(i)).^2);
    end

    df1 = k - 1;
    df2 = N - k;
    ms_between = ss_between / df1;
    ms_within  = ss_within  / df2;

    % --- Degenerate: perfectly equal variances → no test, p = 1 ---
    if ms_within < eps && ss_between < eps
        W = 0;  pval = 1;
    elseif ms_within < eps
        W = Inf;  pval = 0;
    else
        W = ms_between / ms_within;
        if exist('fcdf', 'file') || exist('fcdf', 'builtin')
            pval = 1 - fcdf(W, df1, df2);
        else
            xc = df2 / (df2 + df1 * W);
            pval = betainc(xc, df2/2, df1/2);
        end
        pval = max(min(pval, 1), 0);
    end

    result.k                      = k;
    result.N                      = N;
    result.W                      = W;
    result.df1                    = df1;
    result.df2                    = df2;
    result.p                      = pval;
    result.alpha                  = alpha;
    result.h                      = pval < alpha;
    result.group_medians          = medians(:)';
    result.mean_abs_dev_per_group = z_means(:)';
end
