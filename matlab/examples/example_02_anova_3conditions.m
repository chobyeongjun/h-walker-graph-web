function example_02_anova_3conditions()
% example_02_anova_3conditions  3+ condition comparison (between OR within subjects).
%
% Use this when: comparing baseline vs assist-low vs assist-high (3 levels).
% Auto-recommends parametric vs non-parametric, with assumption checks.
%
% MATLAB Copilot prompt examples:
%   "3개 조건 (baseline, low, high) 평균 비교 + 사후검정"
%   "one-way ANOVA + Tukey HSD 어떻게 해?"
%   "RM-ANOVA 구형성 보정 (Greenhouse-Geisser)"
%   "어떤 검정을 써야할지 자동 추천 받고 싶어"
%
% CANONICAL Copilot prompt:
%   "Call hwalker.stats.decisionTree(groups, 'Design', 'between') first
%    for the recommendation, then hwalker.stats.anova1(groups) and
%    hwalker.stats.postHoc(groups, 'Method', 'tukey')."

    % --- Step 1: load YOUR data per condition ---
    %   Pattern: one cell per group, each cell is a column vector of metric values
    baseline = hwalker.analyzeFile('~/data/baseline.csv');
    low      = hwalker.analyzeFile('~/data/low_assist.csv');
    high     = hwalker.analyzeFile('~/data/high_assist.csv');

    % Extract one metric per condition (here: stride times of right side)
    g_baseline = baseline(1).right.strideTimes;
    g_low      = low(1).right.strideTimes;
    g_high     = high(1).right.strideTimes;
    groups = {g_baseline, g_low, g_high};
    names  = {'baseline','low','high'};

    % --- Step 2: ask the toolbox which test to use ---
    rec = hwalker.stats.decisionTree(groups, ...
        'Design', 'between', ...        % use 'within' if SAME subjects across conditions
        'Planned', false);
    fprintf('\n=== Test recommendation ===\n%s\n', rec.rationale);

    % --- Step 3a: BETWEEN-subject design → one-way ANOVA ---
    a = hwalker.stats.anova1(groups, 'GroupNames', names);
    fprintf('\n=== One-way ANOVA ===\n');
    fprintf('F(%d, %d) = %.2f, p = %.4f\n', a.df_between, a.df_within, a.F, a.p);
    fprintf('eta² = %.3f, omega² = %.3f, Cohen''s f = %.2f\n', a.eta2, a.omega2, a.cohens_f);
    fprintf('Levene p = %.3f → variance %s\n', a.levene_p, ...
        ternary(a.assumptions_met.homogeneity_ok, 'homogeneous', 'heterogeneous'));

    % --- Step 4: post-hoc (when ANOVA is significant) ---
    if a.h
        ph = hwalker.stats.postHoc(groups, 'Method', 'tukey', 'GroupNames', names);
        fprintf('\n=== Tukey HSD post-hoc ===\n');
        fprintf('%-25s  %8s  %8s  %s\n', 'pair', 'diff', 'p_adj', 'sig');
        for i = 1:numel(ph.pair_labels)
            fprintf('%-25s  %+8.3f  %8.4f  %s\n', ...
                ph.pair_labels{i}, ph.mean_diff(i), ph.p_adj(i), ...
                ternary(ph.reject(i), '*', 'ns'));
        end
    end

    % --- Step 3b: WITHIN-subject design → use anovaRM instead ---
    %   (uncomment if same subjects across all conditions)
    %
    %   Y = [baseline.right.strideTimes(1:N), ...
    %        low.right.strideTimes(1:N), ...
    %        high.right.strideTimes(1:N)];   % N x K matrix
    %   rm = hwalker.stats.anovaRM(Y, 'ConditionNames', names);
    %   fprintf('F(%.2f, %.2f) = %.2f, %s = %.4f, partial η² = %.3f\n', ...
    %       rm.df_conditions * rm.eps_GG, rm.df_error * rm.eps_GG, ...
    %       rm.F, rm.recommended_label, rm.recommended_p, rm.eta2_partial);
end


function v = ternary(cond, a, b)
    if isequal(cond, true), v = a; else, v = b; end
end
