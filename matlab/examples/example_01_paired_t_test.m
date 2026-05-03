function example_01_paired_t_test()
% example_01_paired_t_test  Paired t-test (within-subject, 2 conditions).
%
% Use this when: same subjects measured BEFORE and AFTER an intervention
%   (e.g., baseline vs after rehab training).
%
% MATLAB Copilot prompt examples this answers:
%   "내 데이터에서 pre/post 조건의 stride time 차이가 유의한지 검정하고 싶어"
%   "paired t-test 어떻게 해? Cohen's d 까지 보고 싶어"
%   "before-after 비교 통계 + 95% CI 출력"

    % --- Step 1: load YOUR pre/post CSVs (replace these paths) ---
    pre_results  = hwalker.analyzeFile('~/data/subject01_pre.csv');
    post_results = hwalker.analyzeFile('~/data/subject01_post.csv');

    pre_strideTime  = pre_results(1).right.strideTimes;
    post_strideTime = post_results(1).right.strideTimes;
    %  (or use any other metric: strideLengths, cadence per-stride, force tracking error...)

    % --- Step 2: paired t-test + Wilcoxon + 3 Cohen's d variants ---
    r = hwalker.stats.pairedTest(pre_strideTime, post_strideTime, 'Alpha', 0.05);

    % --- Step 3: report exactly what reviewers want ---
    fprintf('\n=== Paired t-test (%s) ===\n', 'stride time pre vs post');
    fprintf('n              = %d valid pairs\n', r.n);
    fprintf('Pre  mean ± SD = %.3f ± %.3f s\n', r.pre_mean,  r.pre_std);
    fprintf('Post mean ± SD = %.3f ± %.3f s\n', r.post_mean, r.post_std);
    fprintf('Diff mean      = %.3f s, 95%% CI [%.3f, %.3f]\n', ...
        r.diff_mean, r.ci_diff(1), r.ci_diff(2));
    fprintf('t(%d) = %.2f, p = %.4f\n', r.df_ttest, r.t_stat, r.p_ttest);
    fprintf('Wilcoxon signed-rank p = %.4f\n', r.p_wilcoxon);
    fprintf('Cohen''s d_av = %.2f (default; Cumming 2012)\n', r.cohens_d_variants.d_av);
    fprintf('Cohen''s d_z  = %.2f (Cohen 1988)\n', r.cohens_d_variants.d_z);
    fprintf('Cohen''s d_rm = %.2f (corrected for r=%.2f)\n', ...
        r.cohens_d_variants.d_rm, r.corr);

    % --- Step 4: paper sentence, ready to paste ---
    fprintf('\n>>> Paper-ready sentence:\n');
    fprintf('"Stride time differed significantly between conditions ');
    fprintf('(M_pre = %.2f ± %.2f s, M_post = %.2f ± %.2f s; ', ...
        r.pre_mean, r.pre_std, r.post_mean, r.post_std);
    fprintf('t(%d) = %.2f, p = %.3f, Cohen''s d_av = %.2f, ', ...
        r.df_ttest, r.t_stat, r.p_ttest, r.cohens_d_variants.d_av);
    fprintf('95%% CI of difference [%.3f, %.3f])."\n\n', ...
        r.ci_diff(1), r.ci_diff(2));
end
