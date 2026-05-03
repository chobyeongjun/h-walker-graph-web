function result = pairedTest(a, b, varargin)
% hwalker.stats.pairedTest  Paired comparisons: t-test + Wilcoxon + 3 Cohen's d variants.
%
%   r = hwalker.stats.pairedTest(preValues, postValues)
%   r = hwalker.stats.pairedTest(pre, post, 'Alpha', 0.05, 'Tail', 'both')
%
% Both vectors must be equal length. NaN pairs are dropped automatically
% before any computation (listwise deletion).
%
% Name-value parameters:
%   'Alpha'  significance threshold (default 0.05) — affects h_ttest/h_wilcoxon
%   'Tail'   'both' (default) | 'right' | 'left'
%
% Result struct fields:
%   .n                 valid pairs after NaN removal
%   .alpha, .tail      copies of inputs for self-documentation
%   .pre_mean, .pre_std, .post_mean, .post_std
%   .diff_mean         mean(b - a)
%   .diff_std          std(b - a, 0)  — sample SD (denominator N-1)
%   .corr              Pearson correlation between pre and post pairs
%   .t_stat            t-statistic (NaN when Stats Toolbox absent)
%   .df_ttest          n - 1
%   .p_ttest           paired t-test p-value
%   .h_ttest           1 = significant at alpha
%   .ci_diff           [lower upper] 95% CI of mean difference (t-distribution)
%   .p_wilcoxon        Wilcoxon signed-rank p-value
%   .h_wilcoxon        1 = significant at alpha
%   .cohens_d          alias of cohens_d_av (recommended default)
%   .cohens_d_type     descriptive label for the default 'd_av (Cumming 2012)'
%   .cohens_d_variants struct with all three paired-d variants:
%       .d_z   = mean(diff) / SD(diff)              -- Cohen 1988, Lakens 2013
%       .d_av  = mean(diff) / mean(SD_pre, SD_post) -- Cumming 2012 (default)
%       .d_rm  = d_z * sqrt(2*(1-r))                -- Lakens 2013 corrected
%   .normality         struct with .p_pre / .p_post (Lilliefors p-values; NaN if absent)
%
% References:
%   Lakens, D. (2013). Calculating and reporting effect sizes to facilitate
%       cumulative science. Frontiers in Psychology, 4:863.
%   Cumming, G. (2012). Understanding the New Statistics. Routledge.

    p = inputParser;
    addParameter(p, 'Alpha', 0.05, @(x) isnumeric(x) && isscalar(x) && x>0 && x<1);
    addParameter(p, 'Tail',  'both', ...
        @(x) ischar(x) && any(strcmpi(x, {'both','right','left'})));
    parse(p, varargin{:});
    alpha = p.Results.Alpha;
    tail  = lower(p.Results.Tail);

    a = a(:);  b = b(:);
    assert(numel(a) == numel(b), 'hwalker:pairedTest:unequalLength', ...
        'a and b must have equal length.');

    valid = isfinite(a) & isfinite(b);
    a = a(valid);  b = b(valid);
    d = b - a;

    result = defaultResult(alpha, tail);
    result.n         = numel(d);
    result.pre_mean  = nanmean1(a);
    result.pre_std   = nanstd1(a);
    result.post_mean = nanmean1(b);
    result.post_std  = nanstd1(b);
    result.diff_mean = nanmean1(d);
    result.diff_std  = nanstd1(d);

    if result.n < 3
        warning('hwalker:pairedTest:tooFew', ...
            'Need >=3 valid pairs (got %d); returning NaN.', result.n);
        return
    end

    % --- Pearson correlation (needed for d_rm) ---
    if result.pre_std > 1e-12 && result.post_std > 1e-12
        c = corrcoef(a, b);
        result.corr = c(1,2);
    else
        result.corr = NaN;
    end

    % --- Three paired Cohen's d variants (Lakens 2013) ---
    avgSD = mean([result.pre_std, result.post_std]);

    % d_av  = M_diff / mean(SD_pre, SD_post)
    if isfinite(avgSD) && avgSD > 1e-12
        result.cohens_d_variants.d_av = result.diff_mean / avgSD;
    elseif abs(result.diff_mean) < 1e-12
        result.cohens_d_variants.d_av = 0;     % no shift, no spread → effect 0
    end

    % d_z   = M_diff / SD_diff
    if abs(result.diff_mean) < 1e-12
        result.cohens_d_variants.d_z = 0;
    elseif result.diff_std > 1e-12
        result.cohens_d_variants.d_z = result.diff_mean / result.diff_std;
    elseif isfinite(result.cohens_d_variants.d_av)
        % Degenerate: zero spread of differences but nonzero mean shift
        % (e.g., b = a + c constant).  d_z is mathematically infinite;
        % use d_av as the well-defined limit (Lakens 2013, eq. 9 footnote).
        result.cohens_d_variants.d_z = result.cohens_d_variants.d_av;
    end

    % d_rm  = d_z * sqrt(2*(1 - r))
    if abs(result.diff_mean) < 1e-12
        result.cohens_d_variants.d_rm = 0;
    elseif isfinite(result.cohens_d_variants.d_z) && isfinite(result.corr)
        if result.diff_std > 1e-12
            result.cohens_d_variants.d_rm = ...
                result.cohens_d_variants.d_z * sqrt(2 * (1 - result.corr));
        else
            % Degenerate (constant shift): r=1 → 2(1-r)=0 → indeterminate Inf*0.
            % Use d_av as the finite limit since pre/post SDs are equal.
            result.cohens_d_variants.d_rm = result.cohens_d_variants.d_av;
        end
    end

    % Default reported d for backward compatibility — d_av is most commonly
    % recommended for paper reporting (Lakens 2013 §"Recommendations").
    if isfinite(result.cohens_d_variants.d_av)
        result.cohens_d      = result.cohens_d_variants.d_av;
        result.cohens_d_type = 'd_av (Cumming 2012)';
    elseif isfinite(result.cohens_d_variants.d_z)
        result.cohens_d      = result.cohens_d_variants.d_z;
        result.cohens_d_type = 'd_z (Cohen 1988)';
    end

    % --- Paired t-test ---
    if exist('ttest', 'file') || exist('ttest', 'builtin')
        try
            [h, pval, ci, stats] = ttest(b, a, 'Alpha', alpha, 'Tail', tail);
            % ttest can return h=NaN when there is no variance (a == b exactly)
            if isnumeric(h) && ~isnan(h)
                result.h_ttest = logical(h);
            else
                result.h_ttest = false;
            end
            result.p_ttest  = pval;
            if numel(ci) == 2, result.ci_diff = ci(:)'; end
            if isstruct(stats)
                if isfield(stats, 'tstat'), result.t_stat   = stats.tstat;   end
                if isfield(stats, 'df'),    result.df_ttest = stats.df;      end
            end
        catch
            % toolbox call failed for some reason — keep defaults
        end
    end

    % --- Wilcoxon signed-rank ---
    if exist('signrank', 'file') || exist('signrank', 'builtin')
        try
            [pval, h] = signrank(b, a, 'Alpha', alpha, 'Tail', tail);
            result.p_wilcoxon = pval;
            if isnumeric(h) && ~isnan(h)
                result.h_wilcoxon = logical(h);
            else
                result.h_wilcoxon = false;
            end
        catch
        end
    end

    % --- Normality screen (informational) ---
    if exist('lillietest', 'file') || exist('lillietest', 'builtin')
        try
            [~, pPre]  = lillietest(a);
            [~, pPost] = lillietest(b);
            result.normality.p_pre  = pPre;
            result.normality.p_post = pPost;
        catch
            % lillietest needs n >= 4 and unique values; swallow
        end
    end
end


% --- Helpers ---
function s = defaultResult(alpha, tail)
    s.n          = 0;
    s.alpha      = alpha;
    s.tail       = tail;
    s.pre_mean   = NaN;  s.pre_std  = NaN;
    s.post_mean  = NaN;  s.post_std = NaN;
    s.diff_mean  = NaN;  s.diff_std = NaN;
    s.corr       = NaN;
    s.t_stat     = NaN;  s.df_ttest = NaN;
    s.p_ttest    = NaN;  s.h_ttest  = false;
    s.ci_diff    = [NaN, NaN];
    s.p_wilcoxon = NaN;  s.h_wilcoxon = false;
    s.cohens_d                  = NaN;
    s.cohens_d_type             = '';
    s.cohens_d_variants.d_z     = NaN;
    s.cohens_d_variants.d_av    = NaN;
    s.cohens_d_variants.d_rm    = NaN;
    s.normality.p_pre  = NaN;
    s.normality.p_post = NaN;
end

function m = nanmean1(x)
    x = x(isfinite(x));
    if isempty(x), m = NaN; else, m = mean(x); end
end

function s = nanstd1(x)
    x = x(isfinite(x));
    if numel(x) < 2, s = NaN; else, s = std(x, 0); end  % N-1 denominator
end
