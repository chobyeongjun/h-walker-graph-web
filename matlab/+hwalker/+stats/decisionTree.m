function rec = decisionTree(groups, varargin)
% hwalker.stats.decisionTree  Recommend a statistical test for the given data + design.
%
%   rec = hwalker.stats.decisionTree({A, B})
%   rec = hwalker.stats.decisionTree({A, B}, 'Design', 'within')
%   rec = hwalker.stats.decisionTree({A, B, C}, 'Design', 'between', 'Planned', false)
%   rec = hwalker.stats.decisionTree(Y_NxK,    'Design', 'within')   % matrix for RM
%
% Inputs:
%   groups   cell array of vectors (between)  OR  N x K matrix (within)
%   'Design'      'between' (default) | 'within' | 'mixed'
%   'Alpha'       0.05 default
%   'Planned'     true if comparisons are pre-registered (default true);
%                 affects post-hoc method choice (Tukey if exploratory,
%                 Bonferroni/Holm if planned)
%
% Returns struct:
%   .design                copy
%   .k                     number of groups / conditions
%   .normality_p_min       minimum Lilliefors p across groups (NaN if absent)
%   .normality_ok          logical; true if all groups p >= alpha
%   .homogeneity_p         Brown-Forsythe Levene p (NaN for within designs)
%   .homogeneity_ok        logical; true if Levene p >= alpha
%   .recommended_test      string identifier
%   .recommended_function  '+hwalker/+stats/...' module name to call
%   .post_hoc_method       e.g. 'tukey', 'holm', 'fdr' (for k > 2)
%   .rationale             multi-line string explaining the choice

    p = inputParser;
    addParameter(p, 'Design',  'between', @(x) any(strcmpi(x, {'between','within','mixed'})));
    addParameter(p, 'Alpha',   0.05);
    addParameter(p, 'Planned', true, @islogical);
    parse(p, varargin{:});
    design  = lower(p.Results.Design);
    alpha   = p.Results.Alpha;
    planned = p.Results.Planned;

    rec = struct( ...
        'design', design, 'alpha', alpha, ...
        'k', NaN, 'normality_p_min', NaN, 'normality_ok', NaN, ...
        'homogeneity_p', NaN, 'homogeneity_ok', NaN, ...
        'recommended_test', '', 'recommended_function', '', ...
        'post_hoc_method', '', 'rationale', '');

    % --- Normalize input shape per design ---
    if isnumeric(groups) && strcmp(design, 'within')
        Y = groups(all(isfinite(groups), 2), :);
        rec.k = size(Y, 2);
        cellGroups = num2cell(Y, 1);
    elseif iscell(groups)
        cellGroups = cellfun(@(x) x(isfinite(x(:))), groups, 'UniformOutput', false);
        rec.k = numel(cellGroups);
    else
        error('hwalker:decisionTree:badInput', ...
            'groups must be cell array (between/mixed) or matrix (within).');
    end

    % --- Normality (Lilliefors) ---
    if exist('lillietest', 'file') || exist('lillietest', 'builtin')
        ps = NaN(rec.k, 1);
        for i = 1:rec.k
            xi = cellGroups{i};
            if numel(xi) >= 4
                try, [~, ps(i)] = lillietest(xi); catch, end
            end
        end
        if any(isfinite(ps))
            rec.normality_p_min = min(ps(isfinite(ps)));
            rec.normality_ok    = rec.normality_p_min >= alpha;
        end
    end

    % --- Homogeneity of variance (between only) ---
    if strcmp(design, 'between') && rec.k >= 2
        try
            lev = hwalker.stats.leveneTest(cellGroups);
            rec.homogeneity_p  = lev.p;
            rec.homogeneity_ok = lev.p >= alpha;
        catch
        end
    end

    % --- Decision logic ---
    parametric_ok = ~isequal(rec.normality_ok, false);  % NaN treated as 'unknown→ok'
    if strcmp(design, 'between')
        homog_ok = ~isequal(rec.homogeneity_ok, false);
    else
        homog_ok = true;
    end
    use_parametric = parametric_ok && homog_ok;

    rationale_lines = {};
    rationale_lines{end+1} = sprintf('Design = %s, k = %d groups/conditions.', design, rec.k);
    if isfinite(rec.normality_p_min)
        rationale_lines{end+1} = sprintf( ...
            'Normality (Lilliefors): min p across groups = %.3f → %s.', ...
            rec.normality_p_min, ...
            ternary(rec.normality_ok, 'OK', 'violated'));
    else
        rationale_lines{end+1} = 'Normality: no Stats Toolbox; assumed OK (silent).';
    end
    if isfinite(rec.homogeneity_p)
        rationale_lines{end+1} = sprintf( ...
            'Homogeneity (Brown-Forsythe Levene): p = %.3f → %s.', ...
            rec.homogeneity_p, ...
            ternary(rec.homogeneity_ok, 'OK', 'violated'));
    end

    switch design
    % ----------------------------------------------------------------
    case 'between'
        if rec.k == 2
            if use_parametric
                rec.recommended_test     = 'Welch two-sample t-test';
                rec.recommended_function = 'ttest2(a, b, ''Vartype'', ''unequal'')';
            else
                rec.recommended_test     = 'Mann-Whitney U test';
                rec.recommended_function = 'ranksum(a, b)';
            end
        else
            if use_parametric
                rec.recommended_test     = 'One-way ANOVA';
                rec.recommended_function = 'hwalker.stats.anova1(groups)';
                if planned
                    rec.post_hoc_method = 'holm';
                else
                    rec.post_hoc_method = 'tukey';
                end
            else
                rec.recommended_test     = 'Kruskal-Wallis test';
                rec.recommended_function = 'kruskalwallis(allData, groupIdx)';
                rec.post_hoc_method      = 'fdr';   % Dunn's test ~ approximated by BH-FDR
            end
        end

    % ----------------------------------------------------------------
    case 'within'
        if rec.k == 2
            if parametric_ok
                rec.recommended_test     = 'Paired t-test';
                rec.recommended_function = 'hwalker.stats.pairedTest(pre, post)';
            else
                rec.recommended_test     = 'Wilcoxon signed-rank test';
                rec.recommended_function = 'signrank(pre, post)  [or pairedTest, which reports both]';
            end
        else
            if parametric_ok
                rec.recommended_test     = 'Repeated-measures ANOVA + Greenhouse-Geisser';
                rec.recommended_function = 'hwalker.stats.anovaRM(Y_NxK)';
                if planned
                    rec.post_hoc_method = 'holm';
                else
                    rec.post_hoc_method = 'tukey';
                end
            else
                rec.recommended_test     = 'Friedman test';
                rec.recommended_function = 'friedman(Y_NxK)';
                rec.post_hoc_method      = 'fdr';
            end
        end

    % ----------------------------------------------------------------
    case 'mixed'
        rec.recommended_test = 'Mixed-design ANOVA (between x within)';
        rec.recommended_function = 'fitrm() + ranova() with WithinModel';
        rec.post_hoc_method      = 'holm';
        rationale_lines{end+1}   = 'Mixed designs require the Stats Toolbox (fitrm/ranova).';
    end

    rationale_lines{end+1} = sprintf('→ Recommended: %s', rec.recommended_test);
    if ~isempty(rec.post_hoc_method)
        rationale_lines{end+1} = sprintf( ...
            '→ Post-hoc (k>2): %s (planned=%d)', rec.post_hoc_method, planned);
    end
    rec.rationale = strjoin(rationale_lines, sprintf('\n'));
end


function v = ternary(cond, a, b)
    if isequal(cond, true), v = a; else, v = b; end
end
