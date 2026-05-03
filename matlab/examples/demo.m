function demo(outputDir)
% demo  End-to-end H-Walker toolbox demonstration with synthetic data.
%
%   demo                           % output to ./out/
%   demo('~/Desktop/hwalker_demo') % custom output dir
%
% Produces:
%   - synthetic CSV (sample_data.csv)
%   - analyzeFile run with console QC output
%   - all 4 statistical test demonstrations (paired/anova1/anovaRM/postHoc)
%   - Fig1 force_QC across all 6 journals × {PDF, PNG}
%   - reproPackage with input hash + git commit + result snapshot
%   - opens the output folder in Finder/Explorer when done

    if nargin < 1, outputDir = fullfile(pwd, 'out'); end
    if ~exist(outputDir, 'dir'), mkdir(outputDir); end

    fprintf('\n========================================\n');
    fprintf(' H-Walker MATLAB Toolbox · Demo\n');
    fprintf('========================================\n\n');

    % ----------------------------------------------------------------
    % 1) Synthesize a realistic H-Walker CSV
    % ----------------------------------------------------------------
    fprintf('[1/5] Synthesizing sample CSV...\n');
    csvPath = fullfile(outputDir, 'sample_data.csv');
    makeSyntheticCSV(csvPath);
    fprintf('   → %s\n', csvPath);

    % ----------------------------------------------------------------
    % 2) Analyze
    % ----------------------------------------------------------------
    fprintf('\n[2/5] Running analyzeFile...\n');
    results = hwalker.analyzeFile(csvPath);
    fprintf('   → %d sync window(s) analyzed\n', numel(results));
    r = results(1);

    % ----------------------------------------------------------------
    % 3) Statistics — demonstrate all major test types
    % ----------------------------------------------------------------
    fprintf('\n[3/5] Statistics demonstrations\n');

    % Synthetic 3-condition data for ANOVA demos
    rng(42);
    baseline = 1.20 + 0.08 * randn(12, 1);
    low      = 1.15 + 0.07 * randn(12, 1);
    high     = 1.08 + 0.06 * randn(12, 1);

    fprintf('\n  (a) decisionTree auto-recommendation:\n');
    rec = hwalker.stats.decisionTree({baseline, low, high}, ...
        'Design', 'between', 'Planned', false);
    fprintf('%s\n', indent(rec.rationale, '      '));

    fprintf('\n  (b) Paired t-test (baseline vs high):\n');
    pt = hwalker.stats.pairedTest(baseline, high);
    fprintf('      t(%d) = %.2f, p = %.4f, d_av = %.2f, 95%% CI [%.3f, %.3f]\n', ...
        pt.df_ttest, pt.t_stat, pt.p_ttest, ...
        pt.cohens_d_variants.d_av, pt.ci_diff(1), pt.ci_diff(2));

    fprintf('\n  (c) One-way ANOVA across 3 conditions:\n');
    a = hwalker.stats.anova1({baseline, low, high}, ...
        'GroupNames', {'baseline','low','high'});
    fprintf('      F(%d, %d) = %.2f, p = %.4f\n', ...
        a.df_between, a.df_within, a.F, a.p);
    fprintf('      ω² = %.3f, η² = %.3f, Cohen''s f = %.2f\n', ...
        a.omega2, a.eta2, a.cohens_f);
    fprintf('      Levene p = %.3f → %s\n', a.levene_p, ...
        ternary(a.assumptions_met.homogeneity_ok, 'homogeneous', 'heterogeneous'));

    fprintf('\n  (d) RM-ANOVA (within-subject 3 conditions):\n');
    Y = [baseline, low, high];     % treat as same 12 subjects across 3 conditions
    rm = hwalker.stats.anovaRM(Y, 'ConditionNames', {'baseline','low','high'});
    fprintf('      F(%.2f, %.2f) = %.2f, %s = %.4f, partial η² = %.3f\n', ...
        rm.df_conditions * rm.eps_GG, rm.df_error * rm.eps_GG, ...
        rm.F, rm.recommended_label, rm.recommended_p, rm.eta2_partial);
    fprintf('      Mauchly W = %.3f, p = %.3f, GG ε = %.2f, HF ε = %.2f\n', ...
        rm.mauchly_W, rm.mauchly_p, rm.eps_GG, rm.eps_HF);

    fprintf('\n  (e) Post-hoc with 4 correction methods:\n');
    for method = {'tukey','bonferroni','holm','fdr'}
        ph = hwalker.stats.postHoc({baseline, low, high}, ...
            'Method', method{1}, ...
            'GroupNames', {'baseline','low','high'});
        fprintf('      [%s]\n', method{1});
        for ii = 1:numel(ph.pair_labels)
            fprintf('         %s: diff=%+.3f, p_adj=%.4f, %s\n', ...
                ph.pair_labels{ii}, ph.mean_diff(ii), ph.p_adj(ii), ...
                ternary(ph.reject(ii), '*', 'ns'));
        end
    end

    fprintf('\n  (f) BCa-bootstrap CI on stride time median:\n');
    bs = hwalker.stats.bootstrap(r.right.strideTimes(isfinite(r.right.strideTimes)), ...
        @median, 'NBoot', 5000, 'Seed', 42);
    fprintf('      median = %.3f, 95%% BCa CI [%.3f, %.3f]\n', ...
        bs.point_estimate, bs.ci_lower, bs.ci_upper);

    % ----------------------------------------------------------------
    % 4) Publication figures — all 6 journals
    % ----------------------------------------------------------------
    fprintf('\n[4/5] Exporting Fig1 across 6 journals × 2 formats...\n');
    figDir = fullfile(outputDir, 'figures');
    if ~exist(figDir, 'dir'), mkdir(figDir); end
    manifest = hwalker.plot.exportAllJournals( ...
        @hwalker.plot.forceQC, {r, 'R'}, figDir, ...
        'BaseName', 'Fig1_force', ...
        'Formats',  {'PDF','PNG'}, ...
        'NCols',    1);
    nOk = sum([manifest.ok]);
    fprintf('   → %d/%d files written\n', nOk, numel(manifest));

    % ----------------------------------------------------------------
    % 5) Reproducibility package
    % ----------------------------------------------------------------
    fprintf('\n[5/5] Saving reproducibility package...\n');
    info = hwalker.meta.reproPackage(results, fullfile(outputDir, 'repro'), ...
        'InputCSV', csvPath, ...
        'Parameters', struct('iqr_multiplier', 2.0, ...
                             'stride_bounds_s', [0.3 5.0], ...
                             'sync_debounce_ms', 50, ...
                             'alpha', 0.05));
    fprintf('   → %s\n', info.dir);

    fprintf('\n========================================\n');
    fprintf(' Demo complete!\n');
    fprintf(' Output: %s\n', outputDir);
    fprintf('========================================\n\n');

    % Open output folder in OS file browser
    if ispc,    system(sprintf('explorer "%s"', outputDir));
    elseif ismac,system(sprintf('open "%s"', outputDir));
    else,       system(sprintf('xdg-open "%s"', outputDir));
    end
end


% =====================================================================
%  Synthetic CSV generator
% =====================================================================
function makeSyntheticCSV(csvPath)
% Generates a 30-second @ 100 Hz CSV with:
%   - 1 sync cycle (3-26 s of high)
%   - 22 strides per side (~1.18 s each)
%   - GCP sawtooth, force tracking with realistic noise

    rng(42);
    fs = 100;
    T_total = 30.0;
    N = round(fs * T_total);
    t_s = (0:N-1)' / fs;

    % --- Sync: low → high at 3 s → low at 26 s ---
    syncSig = zeros(N, 1);
    syncSig((t_s >= 3) & (t_s < 26)) = 1;

    % --- GCP sawtooth (heel-strike pattern), ~1.18 s stride ---
    function gcp = makeGCP(strideT)
        gcp = zeros(N, 1);
        period = round(fs * strideT);
        stancePeriod = round(period * 0.6);
        starts = 1:period:N;
        for s = starts
            ed = min(s + stancePeriod - 1, N);
            gcp(s:ed) = linspace(0, 1, ed - s + 1)';
        end
    end
    L_GCP = makeGCP(1.18);
    R_GCP = makeGCP(1.20);

    % --- Velocity: ~1.0 m/s forward (for ZUPT length) ---
    L_Ax = ones(N, 1) + 0.05 * randn(N, 1);
    L_Ay = 0.05 * randn(N, 1);
    R_Ax = ones(N, 1) + 0.05 * randn(N, 1);
    R_Ay = 0.05 * randn(N, 1);

    % --- Force tracking: desired = sinusoid 0-50 N at stride freq, actual ≈ desired + noise ---
    omegaL = 2*pi / 1.18;
    omegaR = 2*pi / 1.20;
    L_DesForce_N = 25 + 25 * sin(omegaL * t_s);
    R_DesForce_N = 25 + 25 * sin(omegaR * t_s);
    L_ActForce_N = L_DesForce_N + 4.0 * randn(N, 1);
    R_ActForce_N = R_DesForce_N + 3.5 * randn(N, 1);

    % --- Time in ms (firmware native format) ---
    Time_ms = (0:N-1)' * (1000/fs);

    T = table(Time_ms, L_GCP, R_GCP, L_Ax, L_Ay, R_Ax, R_Ay, ...
              L_DesForce_N, L_ActForce_N, R_DesForce_N, R_ActForce_N, syncSig, ...
              'VariableNames', {'Time_ms','L_GCP','R_GCP','L_Ax','L_Ay','R_Ax','R_Ay', ...
                                'L_DesForce_N','L_ActForce_N','R_DesForce_N','R_ActForce_N','Sync'});
    writetable(T, csvPath);
end


function s = indent(str, prefix)
    lines = splitlines(str);
    for i = 1:numel(lines)
        lines{i} = [prefix, lines{i}];
    end
    s = strjoin(lines, sprintf('\n'));
end


function v = ternary(cond, a, b)
    if isequal(cond, true), v = a; else, v = b; end
end
