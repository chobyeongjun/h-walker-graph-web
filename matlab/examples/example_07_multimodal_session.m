function example_07_multimodal_session()
% example_07_multimodal_session  END-TO-END multi-modal H-Walker analysis.
%
% Use this when: you have one experiment with multiple subjects, each
% measured in multiple assistance conditions, with data from H-Walker
% robot + motion capture + force plate + EMG + BWS loadcell.
%
% MATLAB Copilot prompt examples this answers:
%   "한 피험자의 baseline / low_assist / high_assist 3 조건 비교"
%   "robot + motion + emg + loadcell 데이터 한 번에 처리"
%   "보조 방식별 kinematic / kinetic 변화 통계 검정 + 논문 figure"
%   "여러 피험자 group 분석 + RM-ANOVA 자동"
%
% CANONICAL Copilot prompts (paste these EXACT phrases):
%   "Use hwalker.experiment.loadAllConditions on a sub-XX folder, then
%    compareConditions(...,'Design','within') and exportAllJournals."
%   "Generate Methods text from the comparison via
%    hwalker.experiment.generateMethods(cmp, 'OutFile', 'methods.md')."
%
% PREREQ — folder structure (see matlab/docs/MULTIMODAL_PIPELINE.md):
%
%   ~/h-walker-experiments/studies/2026-05-04_assistance-comparison/
%   ├── sub-01/
%   │   ├── meta.json
%   │   ├── cond-1_baseline/
%   │   │   ├── robot.csv     ← H-Walker firmware
%   │   │   ├── motion.c3d    ← Vicon/Qualisys (markers + GRF)
%   │   │   ├── emg.csv       ← Delsys/Noraxon
%   │   │   └── loadcell.csv  ← BWS load
%   │   ├── cond-2_low_assist/
%   │   └── cond-3_high_assist/
%   └── sub-02/ ...

    % ======================================================================
    % STEP 1 — point at one condition, sanity-check loading
    % ======================================================================
    studyRoot = '~/h-walker-experiments/studies/2026-05-04_assistance-comparison';
    condDir   = fullfile(studyRoot, 'sub-01', 'cond-1_baseline');

    session = hwalker.experiment.loadSession(condDir);
    %   Console output (look for these to confirm):
    %     === Loading session sub-01/baseline ===
    %     [robot]    1 sync windows; using first ...
    %     [loadMotion] motion.c3d — 32 markers @ 200 Hz, 2 plate(s) @ 1000 Hz, 30.0s
    %     [loadEMG]    emg.csv — 16 channels @ 2000 Hz, 30.0s
    %     [loadLoadcell] loadcell.csv — fs=1000 Hz, mean F=216.7 N (30.6 % BW)

    % Quick QC
    disp(session.qc.files_present)
    disp(session.qc.durations_s)         % all modality durations should match (±1 s)

    % ======================================================================
    % STEP 2 — extract per-stride scalar features from this single session
    % ======================================================================
    feats_one = hwalker.experiment.extractFeatures(session, 'Side', 'R');
    fprintf('Stride count: %d\n', numel(feats_one.stride_idx));
    fprintf('Mean stride time: %.3f ± %.3f s\n', ...
        mean(feats_one.stride_time_s), std(feats_one.stride_time_s));
    if isfield(feats_one, 'knee_peak_flex_deg')
        fprintf('Knee peak flex: %.1f deg\n', mean(feats_one.knee_peak_flex_deg, 'omitnan'));
    end

    % ======================================================================
    % STEP 3 — load ALL conditions for this subject + statistical comparison
    % ======================================================================
    subjectDir = fullfile(studyRoot, 'sub-01');
    conditions = hwalker.experiment.loadAllConditions(subjectDir);
    fprintf('\nLoaded %d conditions: %s\n', numel(conditions), ...
        strjoin(arrayfun(@(s) s.condition, conditions, 'UniformOutput',false), ' / '));

    cmp = hwalker.experiment.compareConditions(conditions, ...
        'Design',  'within', ...   % same subject across conditions
        'Alpha',   0.05, ...
        'Planned', false, ...
        'Side',    'R');           % R-only analysis (force/EMG/motion all filtered to R)
    %  Use 'Side','both' (default) to keep L+R separate rows;
    %  use 'Side','L' for left-only.

    % ======================================================================
    % STEP 4 — print key results table for the paper Results section
    % ======================================================================
    fprintf('\n=== Results summary (sub-01) ===\n');
    keyMetrics = {'stride_time_s','cadence_steps_min','stride_length_m', ...
                  'force_rmse_N','knee_peak_flex_deg','knee_ROM_deg', ...
                  'grf_peak_vert_N','bws_pct_per_stride'};
    for i = 1:numel(keyMetrics)
        nm = keyMetrics{i};
        if ~isfield(cmp, nm), continue; end
        c = cmp.(nm);
        means = c.means;  sds = c.sds;
        fprintf('  %s\n', nm);
        for k = 1:numel(c.condition_names)
            fprintf('    %-15s  %8.3f ± %.3f\n', c.condition_names{k}, means(k), sds(k));
        end
        ts = c.test_struct;
        if isstruct(ts) && isfield(ts, 'recommended_p')
            fprintf('    [test=%s, %s p=%.4f, effect=%.3f]\n\n', ...
                c.recommended_test, ts.recommended_label, ts.recommended_p, c.effect_size);
        elseif isstruct(ts) && isfield(ts, 'p_ttest')
            fprintf('    [test=%s, p=%.4f, d=%.2f]\n\n', ...
                c.recommended_test, ts.p_ttest, c.effect_size);
        end
    end

    % ======================================================================
    % STEP 5 — make all paper figures across robotics journals
    % ======================================================================
    figDir = fullfile(studyRoot, 'analysis', 'figures');
    if ~exist(figDir, 'dir'), mkdir(figDir); end

    % Figure 1 — force-tracking QC (robot)
    hwalker.plot.exportAllJournals( ...
        @hwalker.plot.forceQC, {conditions(1).robot(1), 'R'}, figDir, ...
        'BaseName', 'Fig1_forceQC_baseline', ...
        'Journals', {'TRO','RAL','TNSRE','JNER','SciRobotics'}, ...
        'Formats',  {'PDF','PNG'}, 'NCols', 2);

    % Figure 2 — bar chart: knee_peak_flex across conditions, with significance
    if isfield(cmp, 'knee_peak_flex_deg')
        c = cmp.knee_peak_flex_deg;
        preset = hwalker.plot.journalPreset('TRO');
        fig = hwalker.plot.metricBar( ...
            c.means(:)', c.sds(:)', c.condition_names, {'value'}, ...
            'Knee Peak Flexion (°)', preset, 2);
        if isstruct(c.post_hoc) && ~isempty(c.post_hoc)
            ax = gca; yMax = max(c.means + c.sds);
            for ii = 1:numel(c.post_hoc.pair_labels)
                if c.post_hoc.reject(ii)
                    pair = c.post_hoc.pairs(ii, :);
                    hwalker.plot.drawSignificance(ax, pair(1), pair(2), ...
                        yMax * (1.05 + 0.10*ii), c.post_hoc.p_adj(ii), ...
                        'Style','asterisk', 'Preset', preset);
                end
            end
        end
        hwalker.plot.exportFigure(fig, ...
            fullfile(figDir, 'Fig2_kneeFlex_TRO.pdf'), preset);
    end

    % ======================================================================
    % STEP 6 — auto-generate Methods + reproducibility package
    % ======================================================================
    methodsTxt = hwalker.experiment.generateMethods(cmp, ...
        'OutFile', fullfile(studyRoot, 'analysis', 'methods.md'));
    fprintf('\n=== Methods text written to analysis/methods.md (%d chars) ===\n', ...
        numel(methodsTxt));

    hwalker.meta.reproPackage(conditions, ...
        fullfile(studyRoot, 'analysis', 'repro'), ...
        'InputCSV',   condDir, ...
        'Parameters', struct( ...
            'design',          'within', ...
            'alpha',           0.05, ...
            'planned',         false, ...
            'common_fs_hz',    1000, ...
            'marker_cutoff_hz', 6, ...
            'grf_cutoff_hz',   20, ...
            'emg_bandpass_hz', [20 450], ...
            'rms_window_ms',   50));

    fprintf('\n========================================\n');
    fprintf(' Multi-modal pipeline complete.\n');
    fprintf(' Outputs in: %s/analysis/\n', studyRoot);
    fprintf('========================================\n\n');
end
