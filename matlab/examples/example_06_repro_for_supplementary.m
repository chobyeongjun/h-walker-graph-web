function example_06_repro_for_supplementary()
% example_06_repro_for_supplementary  Save reproducibility package for paper supplementary.
%
% MATLAB Copilot prompt examples:
%   "논문 supplementary 에 첨부할 재현성 패키지 만들고 싶어"
%   "input CSV hash + git commit + 결과 보존"
%   "이 분석을 1년 뒤에도 그대로 재현하려면"

    csvPath = '~/data/your_subject.csv';

    % --- Step 1: analyze ---
    results = hwalker.analyzeFile(csvPath);

    % --- Step 2: save reproducibility package ---
    info = hwalker.meta.reproPackage(results, ...
        '~/Desktop/paper_repro', ...
        'InputCSV',   csvPath, ...
        'Parameters', struct( ...
            'iqr_multiplier',   2.0, ...
            'stride_bounds_s',  [0.3 5.0], ...
            'sync_debounce_ms', 50, ...
            'alpha',            0.05));

    fprintf('Saved to: %s\n', info.dir);
    fprintf('Git commit captured: %s\n', info.git_commit);
    fprintf('MATLAB version:      %s\n', info.matlab_version);

    % --- Step 3: later, verify integrity ---
    pkg = hwalker.meta.loadRepro(info.dir);
    if pkg.currentMatch.git_commit && pkg.currentMatch.matlab && ...
       (~isnan(pkg.currentMatch.input_hash) && pkg.currentMatch.input_hash)
        fprintf('✓ Round-trip OK — analysis is bit-reproducible.\n');
    end

    % --- Submission tip ---
    %   Zip the entire timestamp folder under repro/ and upload as
    %   "supplementary_reproducibility.zip" to the journal.
    %   Reviewer can open result.json + journal_presets.json directly,
    %   or load result.mat in MATLAB to interact.
end
