function cmp = compareConditions(conditions, varargin)
% hwalker.experiment.compareConditions  Statistical comparison across conditions for one subject.
%
%   cmp = hwalker.experiment.compareConditions(conditions)
%   cmp = hwalker.experiment.compareConditions(conditions, ...
%             'Design','within', 'Alpha',0.05, 'Planned',false)
%
% Input:
%   conditions  N x 1 struct array of sessions (from loadAllConditions)
%
% Returns struct cmp where each field corresponds to a metric:
%   cmp.<metric>.condition_names
%   cmp.<metric>.means(1:K), .sds(1:K), .ns(1:K)
%   cmp.<metric>.recommended_test     ('paired t' | 'RM-ANOVA + GG' | 'Friedman' | 'one-way ANOVA' | ...)
%   cmp.<metric>.test_struct          (full result from hwalker.stats.* call)
%   cmp.<metric>.post_hoc             (only when K >= 3 and significant)
%   cmp.<metric>.effect_size          (omega2 / partial eta2 / d_av)
%   cmp.<metric>.normality_p_min      (Lilliefors)
%   cmp.<metric>.assumption_notes
%
% The metric set is the union of feature names across all conditions
% (per hwalker.experiment.extractFeatures).

    p = inputParser;
    addParameter(p, 'Design',  'within', @(x) any(strcmpi(x, {'within','between','mixed'})));
    addParameter(p, 'Alpha',   0.05);
    addParameter(p, 'Planned', false, @islogical);
    parse(p, varargin{:});
    design  = lower(p.Results.Design);
    alpha   = p.Results.Alpha;
    planned = p.Results.Planned;

    K = numel(conditions);
    if K < 2
        error('hwalker:compareConditions:tooFew', ...
            'Need >= 2 conditions, got %d.', K);
    end

    condNames = arrayfun(@(s) s.condition, conditions, 'UniformOutput', false);

    % Extract features for each condition
    features = cell(K, 1);
    for k = 1:K
        features{k} = hwalker.experiment.extractFeatures(conditions(k));
    end

    % Union of metric names across conditions
    allFields = {};
    for k = 1:K
        if isstruct(features{k})
            allFields = union(allFields, fieldnames(features{k}));
        end
    end

    cmp = struct();
    skipFields = {'stride_idx','side'};

    for fi = 1:numel(allFields)
        nm = allFields{fi};
        if ismember(nm, skipFields), continue; end

        % Collect per-condition vectors
        groups = cell(1, K);
        for k = 1:K
            if isfield(features{k}, nm)
                v = features{k}.(nm);
                if isnumeric(v)
                    v = v(isfinite(v));
                    groups{k} = v;
                else
                    groups{k} = [];
                end
            else
                groups{k} = [];
            end
        end

        % Skip if any group has no data
        if any(cellfun(@isempty, groups)), continue; end

        means = cellfun(@mean, groups);
        sds   = cellfun(@(v) std(v,0), groups);
        ns    = cellfun(@numel, groups);

        % --- Test selection — HONORS decisionTree recommendation ---
        % Codex pass 10 fix: previously ignored decisionTree's
        % non-parametric recommendation and always ran ANOVA.
        rec = '';  testStruct = []; ph = []; effectSize = NaN; normPMin = NaN;
        try
            decision = hwalker.stats.decisionTree(groups, ...
                'Design', design, 'Planned', planned, 'Alpha', alpha);
            normPMin = decision.normality_p_min;
            useNonparam = isequal(decision.normality_ok, false);
            % decision.recommended_test contains string like 'Friedman test',
            % 'Mann-Whitney U test', 'Kruskal-Wallis test', etc.

            if K == 2
                if strcmp(design, 'within') && numel(groups{1}) == numel(groups{2})
                    if useNonparam && (exist('signrank','file') || exist('signrank','builtin'))
                        [pv, h, st] = signrank(groups{1}, groups{2}, 'Alpha', alpha);
                        rec = 'Wilcoxon signed-rank';
                        testStruct = struct('p', pv, 'p_ttest', pv, 'h', h, ...
                            'signedrank', getfieldOr(st,'signedrank',NaN));
                        % Effect size r = Z / sqrt(N)
                        if isstruct(st) && isfield(st,'zval')
                            effectSize = st.zval / sqrt(numel(groups{1}));
                        end
                    else
                        r = hwalker.stats.pairedTest(groups{1}, groups{2}, 'Alpha', alpha);
                        rec = 'paired t (+ Wilcoxon)';
                        testStruct = r;
                        effectSize = r.cohens_d_variants.d_av;
                    end
                else
                    if useNonparam && (exist('ranksum','file') || exist('ranksum','builtin'))
                        [pv, h, st] = ranksum(groups{1}, groups{2}, 'Alpha', alpha);
                        rec = 'Mann-Whitney U';
                        testStruct = struct('p', pv, 'p_ttest', pv, 'h', h, ...
                            'ranksum', getfieldOr(st,'ranksum',NaN));
                        if isstruct(st) && isfield(st,'zval')
                            effectSize = st.zval / sqrt(numel(groups{1}) + numel(groups{2}));
                        end
                    elseif exist('ttest2','file') || exist('ttest2','builtin')
                        [h, pv, ci, stats] = ttest2(groups{1}, groups{2}, ...
                            'Vartype', 'unequal');
                        rec = 'Welch t';
                        testStruct = struct('p',pv,'p_ttest',pv,'t',stats.tstat, ...
                            'df',stats.df, 'h',h,'ci',ci);
                    end
                end
            else
                if strcmp(design, 'within')
                    nMin = min(ns);
                    Y = zeros(nMin, K);
                    for k = 1:K, Y(:, k) = groups{k}(1:nMin); end
                    if useNonparam && (exist('friedman','file') || exist('friedman','builtin'))
                        pv = friedman(Y, 1, 'off');
                        rec = 'Friedman';
                        testStruct = struct('p', pv, 'recommended_p', pv, ...
                            'recommended_label', 'Friedman p', 'F', NaN);
                        if pv < alpha
                            ph = pseudoPostHocRM(groups, condNames, alpha, planned);
                        end
                    else
                        r = hwalker.stats.anovaRM(Y, 'ConditionNames', condNames, ...
                            'Alpha', alpha);
                        rec = sprintf('RM-ANOVA (%s)', r.recommended_label);
                        testStruct = r;
                        effectSize = r.eta2_partial;
                        if r.recommended_p < alpha
                            ph = pseudoPostHocRM(groups, condNames, alpha, planned);
                        end
                    end
                else
                    if useNonparam && (exist('kruskalwallis','file') || exist('kruskalwallis','builtin'))
                        allD = []; grpIdx = [];
                        for k = 1:K
                            allD = [allD; groups{k}(:)];                          %#ok<AGROW>
                            grpIdx = [grpIdx; repmat(k, numel(groups{k}), 1)];    %#ok<AGROW>
                        end
                        pv = kruskalwallis(allD, grpIdx, 'off');
                        rec = 'Kruskal-Wallis';
                        testStruct = struct('p', pv, 'recommended_p', pv, ...
                            'recommended_label','Kruskal-Wallis p','F',NaN);
                        if pv < alpha
                            ph = hwalker.stats.postHoc(groups, ...
                                'Method', 'fdr', 'GroupNames', condNames, 'Alpha', alpha);
                        end
                    else
                        a = hwalker.stats.anova1(groups, 'GroupNames', condNames, 'Alpha', alpha);
                        rec = 'one-way ANOVA';
                        testStruct = a;
                        effectSize = a.omega2;
                        if a.h
                            ph = hwalker.stats.postHoc(groups, ...
                                'Method', ternary(planned, 'holm', 'tukey'), ...
                                'GroupNames', condNames, 'Alpha', alpha);
                        end
                    end
                end
            end
        catch ME
            warning('hwalker:compareConditions:testFail', ...
                '[%s] test failed: %s', nm, ME.message);
        end

        cmp.(nm).condition_names = condNames;
        cmp.(nm).means           = means;
        cmp.(nm).sds             = sds;
        cmp.(nm).ns              = ns;
        cmp.(nm).recommended_test = rec;
        cmp.(nm).test_struct     = testStruct;
        cmp.(nm).post_hoc        = ph;
        cmp.(nm).effect_size     = effectSize;
        cmp.(nm).normality_p_min = normPMin;
    end
end


function ph = pseudoPostHocRM(groups, condNames, alpha, planned)
% Pairwise paired t-tests with Holm/Tukey adjustment, for RM context.
    pairs = nchoosek(1:numel(groups), 2);
    raw = zeros(size(pairs,1), 1);
    md  = zeros(size(pairs,1), 1);
    labels = cell(size(pairs,1), 1);
    nMin = min(cellfun(@numel, groups));
    for ii = 1:size(pairs,1)
        i = pairs(ii,1); j = pairs(ii,2);
        a = groups{i}(1:nMin);
        b = groups{j}(1:nMin);
        r = hwalker.stats.pairedTest(a, b, 'Alpha', alpha);
        raw(ii) = r.p_ttest;
        md(ii)  = r.diff_mean;
        labels{ii} = sprintf('%s vs %s', condNames{i}, condNames{j});
    end
    if planned, method = 'bonferroni'; else, method = 'holm'; end
    p_adj = applyMC(raw, method);
    ph.method      = method;
    ph.pair_labels = labels;
    ph.mean_diff   = md;
    ph.p_raw       = raw;
    ph.p_adj       = p_adj;
    ph.reject      = p_adj < alpha;
end

function p_adj = applyMC(p_raw, method)
    m = numel(p_raw);
    switch method
        case 'bonferroni'
            p_adj = min(p_raw * m, 1);
        case {'holm','holm-bonferroni'}
            [p_sort, ord] = sort(p_raw);
            factors = (m:-1:1)';
            p_step = p_sort .* factors;
            p_step = cummax(p_step);
            p_step = min(p_step, 1);
            p_adj  = zeros(m, 1);
            p_adj(ord) = p_step;
        case {'fdr','bh'}
            [p_sort, ord] = sort(p_raw);
            ranks = (1:m)';
            p_step = p_sort * m ./ ranks;
            p_step = flipud(cummin(flipud(p_step)));
            p_step = min(p_step, 1);
            p_adj = zeros(m,1);
            p_adj(ord) = p_step;
        otherwise
            p_adj = p_raw;
    end
end

function v = ternary(cond, a, b)
    if isequal(cond, true), v = a; else, v = b; end
end

function v = getfieldOr(s, name, default)
    if isstruct(s) && isfield(s, name), v = s.(name); else, v = default; end
end
