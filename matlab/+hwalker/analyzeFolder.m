function results = analyzeFolder(folderPath)
% hwalker.analyzeFolder  Analyze all Robot-type CSVs in a folder.
%
%   results = hwalker.analyzeFolder()             % UI folder picker
%   results = hwalker.analyzeFolder('/path')      % direct path
%
% Auto-discovery:
%   1. Finds all .csv files recursively under folderPath
%   2. Filters to 'Robot' kind (has L_GCP / L_DesForce_N columns)
%   3. Runs hwalker.analyzeFile on each
%   4. Saves per-stride CSV + .mat result to <folder>/analysis_output/
%
% Returns cell array of result structs (failed files silently skipped).
%
% Quick start:
%   addpath('matlab');                         % once per session
%   results = hwalker.analyzeFolder();         % pick folder in UI
%   r1 = results{1};
%   fig = hwalker.plot.forceTracking(hwalker.io.loadCSV(r1.filepath), 'L', ...
%           r1.left.hsIndices, r1.left.validMask);
%   hwalker.plot.exportFigure(fig, 'Fig1_force.pdf', ...
%           hwalker.plot.journalPreset('IEEE'));

    if nargin < 1 || isempty(folderPath)
        folderPath = uigetdir(pwd, 'Select H-Walker data folder');
        if isequal(folderPath, 0)
            results = {};
            return
        end
    end

    % --- Discover CSVs ---
    csvFiles = dir(fullfile(folderPath, '**', '*.csv'));
    if isempty(csvFiles)
        fprintf('No CSV files found in: %s\n', folderPath);
        results = {};
        return
    end

    % --- Filter to Robot-type ---
    robotFiles = {};
    for i = 1:numel(csvFiles)
        fp   = fullfile(csvFiles(i).folder, csvFiles(i).name);
        kind = hwalker.io.detectSourceKind(fp);
        if strcmp(kind, 'Robot')
            robotFiles{end+1} = fp; %#ok<AGROW>
        end
    end

    if isempty(robotFiles)
        fprintf(['No Robot-type CSVs found (need L_GCP or L_DesForce_N).\n' ...
                 'All %d file(s) were: %s\n'], numel(csvFiles), folderPath);
        results = {};
        return
    end

    fprintf('Found %d Robot CSV(s) in %s\n', numel(robotFiles), folderPath);

    % --- Output directory ---
    outDir = fullfile(folderPath, 'analysis_output');
    if ~exist(outDir, 'dir'), mkdir(outDir); end

    % --- Analyze ---
    nFiles  = numel(robotFiles);
    buf     = cell(nFiles, 1);
    nOk     = 0;
    for i = 1:nFiles
        fp = robotFiles{i};
        fprintf('\n[%d/%d] %s\n', i, nFiles, fp);
        try
            r = hwalker.analyzeFile(fp);
            buf{i} = r;
            nOk = nOk + 1;

            % Per-stride table → CSV
            tbl = hwalker.io.resultToTable(r);
            [~, fname] = fileparts(fp);
            if ~isempty(tbl)
                writetable(tbl, fullfile(outDir, [fname '_strides.csv']));
            end
            % Full result → .mat
            save(fullfile(outDir, [fname '_result.mat']), 'r'); %#ok<USENS>
        catch ME
            fprintf('  ERROR: %s\n', ME.message);
        end
    end

    results = buf(~cellfun('isempty', buf));
    fprintf('\n=== Done: %d/%d succeeded. Output → %s ===\n', nOk, nFiles, outDir);
end
