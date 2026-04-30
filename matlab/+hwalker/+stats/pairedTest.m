function result = pairedTest(a, b)
% hwalker.stats.pairedTest  Paired comparisons: t-test + Wilcoxon signed-rank.
%
%   r = hwalker.stats.pairedTest(preValues, postValues)
%
% Both vectors must be equal length. NaN pairs are dropped automatically.
%
% Result struct:
%   .n            number of valid pairs after NaN removal
%   .diff_mean    mean(b - a)
%   .diff_std     std(b - a)
%   .t_stat       t-statistic (NaN when Stats Toolbox unavailable)
%   .p_ttest      two-tailed p-value from paired t-test
%   .h_ttest      1 = significant at α=0.05
%   .p_wilcoxon   two-tailed p-value from Wilcoxon signed-rank test
%   .h_wilcoxon   1 = significant at α=0.05
%   .cohens_d     Cohen's d for paired samples (effect size)
%
% Requires Statistics and Machine Learning Toolbox for ttest / signrank.

    a = a(:);  b = b(:);
    assert(numel(a) == numel(b), 'hwalker:pairedTest:unequalLength', ...
        'a and b must have equal length.');

    valid = isfinite(a) & isfinite(b);
    a = a(valid);  b = b(valid);
    d = b - a;

    result.n          = numel(d);
    result.diff_mean  = mean(d);
    result.diff_std   = std(d);

    % Defaults for when toolbox is unavailable
    result.t_stat      = NaN;
    result.p_ttest     = NaN;
    result.h_ttest     = false;
    result.p_wilcoxon  = NaN;
    result.h_wilcoxon  = false;
    result.cohens_d    = NaN;

    if result.n < 3
        warning('hwalker:pairedTest:tooFew', 'Need ≥3 pairs; returning NaN.');
        return
    end

    % Cohen's d (paired): mean diff / SD of differences
    if result.diff_std > 1e-12
        result.cohens_d = result.diff_mean / result.diff_std;
    else
        result.cohens_d = 0;
    end

    % Paired t-test: ttest(b, a) tests b-a, consistent with diff_mean = mean(b-a)
    if exist('ttest', 'file') || exist('ttest', 'builtin')
        [h, p, ~, stats] = ttest(b, a);
        result.h_ttest = h;
        result.p_ttest = p;
        if isstruct(stats) && isfield(stats, 'tstat')
            result.t_stat = stats.tstat;
        end
    end

    % Wilcoxon signed-rank test: signrank(b, a) tests b-a
    if exist('signrank', 'file') || exist('signrank', 'builtin')
        [p, h] = signrank(b, a);
        result.p_wilcoxon = p;
        result.h_wilcoxon = h;
    end
end
