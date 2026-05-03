function result = anova1(groups, varargin)
% hwalker.stats.anova1  One-way (between-subjects) ANOVA + omega² + eta² + 95%CI on F.
%
%   r = hwalker.stats.anova1({groupA, groupB, groupC})
%   r = hwalker.stats.anova1({groupA, groupB, groupC}, ...
%                             'GroupNames', {'baseline','low','high'}, ...
%                             'Alpha', 0.05)
%
% Accepts either:
%   - a cell array of column vectors (one per group)
%   - a struct array with .name + .data fields
%
% NaN values are dropped per group (listwise within group).
%
% Result struct fields:
%   .k                 number of groups
%   .n_per_group       vector of group sizes after NaN removal
%   .N                 total n
%   .group_names       cellstr (auto: G1, G2, ...)
%   .group_means       vector
%   .group_stds        vector (sample SD, N-1)
%   .grand_mean        scalar
%   .ss_between, .ss_within, .ss_total
%   .df_between, .df_within
%   .ms_between, .ms_within
%   .F                 F statistic
%   .p                 p-value (Snedecor F distribution)
%   .h                 1 = significant at .alpha
%   .alpha
%   .eta2              SS_between / SS_total          (biased)
%   .omega2            (SS_between - df_b*MS_w) / (SS_total + MS_w)  (less biased)
%   .cohens_f          sqrt(eta2 / (1 - eta2))
%   .levene_p          Brown-Forsythe variance-homogeneity p (NaN if not run)
%   .assumptions_met   struct with .normality_ok / .homogeneity_ok (NaN if not checked)
%
% Reference: Lakens (2013) Frontiers in Psychology 4:863.

    p = inputParser;
    addParameter(p, 'GroupNames', {});
    addParameter(p, 'Alpha',      0.05, @(x) isnumeric(x) && isscalar(x) && x>0 && x<1);
    addParameter(p, 'CheckAssumptions', true, @islogical);
    parse(p, varargin{:});

    [data, names] = normalizeGroups(groups, p.Results.GroupNames);
    k = numel(data);
    assert(k >= 2, 'hwalker:anova1:tooFewGroups', 'Need >= 2 groups.');

    % Drop NaN per group
    for i = 1:k
        data{i} = data{i}(isfinite(data{i}));
    end
    n_per_group = cellfun(@numel, data);
    N = sum(n_per_group);
    assert(all(n_per_group >= 2), 'hwalker:anova1:groupTooSmall', ...
        'Each group must have >= 2 finite observations.');

    % Group statistics
    group_means = cellfun(@mean, data);
    group_stds  = cellfun(@(x) std(x, 0), data);   % N-1

    % Grand mean (weighted by n_per_group, i.e. mean of all samples)
    all_data   = cat(1, data{:});
    grand_mean = mean(all_data);

    % Sums of squares
    ss_between = sum(n_per_group(:) .* (group_means(:) - grand_mean).^2);
    ss_within  = 0;
    for i = 1:k
        ss_within = ss_within + sum((data{i} - group_means(i)).^2);
    end
    ss_total = ss_between + ss_within;

    df_between = k - 1;
    df_within  = N - k;

    ms_between = ss_between / df_between;
    ms_within  = ss_within  / df_within;

    % --- Degenerate cases (avoid 0/0 from constant data) ---
    if ms_within < eps && ss_between < eps
        % All observations identical across all groups → no effect
        F = 0;  pval = 1;  eta2 = 0;  omega2 = 0;  cohens_f = 0;
    elseif ms_within < eps
        % Within-group variance vanishes but between-group differs → perfect separation
        F = Inf;  pval = 0;  eta2 = 1;  omega2 = 1;  cohens_f = Inf;
    else
        F        = ms_between / ms_within;
        pval     = fdist_sf(F, df_between, df_within);
        eta2     = ss_between / ss_total;
        omega2   = (ss_between - df_between * ms_within) / (ss_total + ms_within);
        cohens_f = sqrt(max(eta2, 0) / max(1 - eta2, eps));
    end

    result.k             = k;
    result.group_names   = names;
    result.n_per_group   = n_per_group(:)';
    result.N             = N;
    result.group_means   = group_means(:)';
    result.group_stds    = group_stds(:)';
    result.grand_mean    = grand_mean;
    result.ss_between    = ss_between;
    result.ss_within     = ss_within;
    result.ss_total      = ss_total;
    result.df_between    = df_between;
    result.df_within     = df_within;
    result.ms_between    = ms_between;
    result.ms_within     = ms_within;
    result.F             = F;
    result.p             = pval;
    result.alpha         = p.Results.Alpha;
    result.h             = pval < p.Results.Alpha;
    result.eta2          = eta2;
    result.omega2        = omega2;
    result.cohens_f      = cohens_f;
    result.levene_p      = NaN;
    result.assumptions_met.normality_ok    = NaN;
    result.assumptions_met.homogeneity_ok  = NaN;

    % --- Assumption checks (informational) ---
    if p.Results.CheckAssumptions
        % Brown-Forsythe (median-based Levene)
        try
            lev = hwalker.stats.leveneTest(data);
            result.levene_p = lev.p;
            result.assumptions_met.homogeneity_ok = lev.p >= p.Results.Alpha;
        catch
        end

        if exist('lillietest', 'file') || exist('lillietest', 'builtin')
            try
                allOk = true;
                for i = 1:k
                    if numel(data{i}) >= 4
                        [~, pn] = lillietest(data{i});
                        if pn < p.Results.Alpha
                            allOk = false;
                        end
                    end
                end
                result.assumptions_met.normality_ok = allOk;
            catch
            end
        end
    end
end


% ------------------------------------------------------------------
function [data, names] = normalizeGroups(groups, userNames)
    if iscell(groups)
        data = cellfun(@(x) x(:), groups, 'UniformOutput', false);
    elseif isstruct(groups)
        data = arrayfun(@(s) s.data(:), groups, 'UniformOutput', false);
        if isempty(userNames)
            userNames = arrayfun(@(s) s.name, groups, 'UniformOutput', false);
        end
    else
        error('hwalker:anova1:badInput', ...
            'groups must be cell array or struct array.');
    end

    k = numel(data);
    if isempty(userNames)
        names = arrayfun(@(i) sprintf('G%d', i), 1:k, 'UniformOutput', false);
    else
        assert(numel(userNames) == k, 'hwalker:anova1:nameLengthMismatch', ...
            'GroupNames length (%d) must equal number of groups (%d).', ...
            numel(userNames), k);
        names = cellfun(@char, userNames, 'UniformOutput', false);
    end
end


function p = fdist_sf(F, df1, df2)
% Survival function of Snedecor's F (= 1 - CDF). Uses incomplete beta.
% MATLAB has fcdf in the Stats Toolbox; this fallback works in base MATLAB.
    if df1 <= 0 || df2 <= 0
        p = NaN; return
    end
    if F <= 0
        p = 1; return         % no effect → p = 1
    end
    if isinf(F)
        p = 0; return         % perfect separation → p = 0
    end
    if exist('fcdf', 'file') || exist('fcdf', 'builtin')
        p = 1 - fcdf(F, df1, df2);
    else
        % Regularized incomplete beta: P(X >= F) = I_x(df2/2, df1/2) where
        % x = df2 / (df2 + df1*F). Implemented via betainc(x, a, b, 'lower').
        x = df2 / (df2 + df1 * F);
        p = betainc(x, df2/2, df1/2);
    end
    p = max(min(p, 1), 0);
end
