function manifest = renameRawToStandard(rawDir, outputDir, varargin)
% hwalker.experiment.renameRawToStandard  Copy raw files into standard-named tree.
%
%   manifest = hwalker.experiment.renameRawToStandard(rawDir, outputDir, ...
%       'Date',    '260504', ...
%       'Subject', 'LKM', ...
%       'Speed',   '1_0', ...    % 1.0 m/s
%       'Group',   '');           % '' (healthy) or 'Parkinson'
%
% Pattern (per user spec, 2026-05-05):
%
%   <YYMMDD>_<Source>_<Subject>_TD_level_<speed_int>_<speed_dec>_H-Walker[_<Group>]_<cond>_<TrialNum>.<ext>
%
% e.g.
%   260504_Robot_LKM_TD_level_1_0_H-Walker_high_0_01.csv
%   260504_Loadcell_LKM_TD_level_1_0_H-Walker_noassist_wb_02.csv
%   260512_Robot_PSM_TD_level_1_0_H-Walker_Parkinson_high_0_01.csv
%
% Behavior:
%   - rawDir/ stays untouched (read-only).
%   - outputDir/Robot, /Loadcell, /Motion are created (mkdir if absent).
%   - Each raw file is COPIED to outputDir/<modality>/<new_name>.<ext>.
%   - meta.json from rawDir is also copied.
%   - MVC_*.qtm and *Static*.qtm are copied to outputDir/Motion/ unchanged
%     (reference trials, not subject to the H-Walker naming).
%   - A `_rename_map.csv` is written so the user can audit raw → renamed
%     mapping.
%
% Returns manifest table: Source modality | raw filename | new filename | trial | cond.

    p = inputParser;
    addParameter(p, 'Date',    '');
    addParameter(p, 'Subject', '');
    addParameter(p, 'Speed',   '1_0');
    addParameter(p, 'Group',   '');
    addParameter(p, 'DryRun',  false, @islogical);
    parse(p, varargin{:});

    if ~exist(rawDir, 'dir')
        error('hwalker:renameRawToStandard:noRaw', 'rawDir not found: %s', rawDir);
    end

    % Auto-derive Date and Subject from rawDir foldername if not given
    [~, rawBase] = fileparts(rawDir);
    if isempty(p.Results.Date)
        tok = regexp(rawBase, '^(\d{6})', 'tokens', 'once');
        if ~isempty(tok), Date = tok{1}; else, Date = ''; end
    else
        Date = char(p.Results.Date);
    end
    Subject = char(p.Results.Subject);
    if isempty(Subject)
        % Try meta.json
        metaFile = fullfile(rawDir, 'meta.json');
        if exist(metaFile, 'file')
            try
                m = jsondecode(fileread(metaFile));
                if isfield(m, 'name_initials'), Subject = m.name_initials; end
            catch
            end
        end
    end
    if isempty(Date) || isempty(Subject)
        error('hwalker:renameRawToStandard:missingMeta', ...
            'Cannot determine Date or Subject. Pass them explicitly.');
    end
    Speed = char(p.Results.Speed);
    Group = char(p.Results.Group);
    groupTok = '';
    if ~isempty(Group), groupTok = ['_' Group]; end

    fprintf('\n========================================\n');
    fprintf(' renameRawToStandard\n');
    fprintf('   raw : %s\n', rawDir);
    fprintf('   out : %s\n', outputDir);
    fprintf('   date=%s  subject=%s  speed=%s  group=%s\n', Date, Subject, Speed, Group);
    fprintf('========================================\n');

    % Output dirs
    if ~p.Results.DryRun
        for d = {outputDir, fullfile(outputDir,'Robot'), ...
                 fullfile(outputDir,'Loadcell'), fullfile(outputDir,'Motion')}
            if ~exist(d{1}, 'dir'), mkdir(d{1}); end
        end
    end

    rows = {};
    rows = processModality(rows, fullfile(rawDir,'Robot'),    'Robot',    'csv', ...
        Date, Subject, Speed, groupTok, fullfile(outputDir,'Robot'), p.Results.DryRun);
    rows = processModality(rows, fullfile(rawDir,'Loadcell'), 'Loadcell', 'csv', ...
        Date, Subject, Speed, groupTok, fullfile(outputDir,'Loadcell'), p.Results.DryRun);
    rows = processModality(rows, fullfile(rawDir,'Motion'),   'Motion',   '',    ...
        Date, Subject, Speed, groupTok, fullfile(outputDir,'Motion'), p.Results.DryRun);

    % Copy meta.json if exists
    metaSrc = fullfile(rawDir, 'meta.json');
    if exist(metaSrc, 'file') && ~p.Results.DryRun
        copyfile(metaSrc, fullfile(outputDir, 'meta.json'));
    end

    % Build manifest table
    if isempty(rows)
        manifest = table();
    else
        manifest = cell2table(rows, ...
            'VariableNames', {'modality','raw_name','new_name','condition','trial_num'});
    end
    if ~p.Results.DryRun && height(manifest) > 0
        writetable(manifest, fullfile(outputDir, '_rename_map.csv'));
    end

    fprintf('\n=== Done ===\n');
    fprintf('  files: %d\n', height(manifest));
    fprintf('  map: %s/_rename_map.csv\n', outputDir);
    if p.Results.DryRun
        fprintf('  ⚠ DryRun mode — nothing actually copied.\n');
    end
end


% ====================================================================
function rows = processModality(rows, srcDir, modality, requiredExt, ...
    Date, Subject, Speed, groupTok, dstDir, dryRun)
    if ~exist(srcDir, 'dir'), return; end

    if ~isempty(requiredExt)
        listing = dir(fullfile(srcDir, ['*.' upper(requiredExt)]));
    else
        % Motion: any of qtm / mat / c3d / tsv
        listing = [dir(fullfile(srcDir, '*.qtm')); ...
                   dir(fullfile(srcDir, '*.mat')); ...
                   dir(fullfile(srcDir, '*.c3d')); ...
                   dir(fullfile(srcDir, '*.tsv'))];
    end

    % Group condition→trial counts so trial_num auto-increments per condition
    seen = containers.Map('KeyType','char','ValueType','double');

    for i = 1:numel(listing)
        fn = listing(i).name;
        [~, base, ext] = fileparts(fn);

        % Reference files (MVC, Static): copy as-is, no rename
        if startsWith(lower(base), 'mvc') || contains(lower(base), 'static')
            if ~dryRun
                copyfile(fullfile(srcDir, fn), fullfile(dstDir, fn));
            end
            fprintf(' [%s]    %-50s → (reference, kept)\n', modality, fn);
            rows(end+1, :) = {modality, fn, fn, '<reference>', NaN};               %#ok<AGROW>
            continue
        end

        % Extract condition + raw trial-num suffix from the existing name
        [cond, rawTrial] = extractCondition(base);

        % Determine trial number
        if ~isnan(rawTrial)
            trialNum = rawTrial;
        else
            if isKey(seen, cond), seen(cond) = seen(cond) + 1; else, seen(cond) = 1; end
            trialNum = seen(cond);
        end

        newBase = sprintf('%s_%s_%s_TD_level_%s_H-Walker%s_%s_%02d', ...
            Date, modality, Subject, Speed, groupTok, cond, trialNum);
        newName = [newBase lower(ext)];

        if ~dryRun
            copyfile(fullfile(srcDir, fn), fullfile(dstDir, newName));
        end
        fprintf(' [%s]    %-50s → %s\n', modality, fn, newName);
        rows(end+1, :) = {modality, fn, newName, cond, trialNum};                  %#ok<AGROW>
    end
end


function [cond, trialNum] = extractCondition(base)
% Map raw stem to (condition, trial_number).
%
% Rules (priority):
%   1. noassist_wb_<N>           → cond='noassist_wb',  trial=N
%   2. noassist_wb (no number)   → cond='noassist_wb',  trial=NaN (auto-increment)
%   3. noassist_nwb_<N>          → cond='noassist_nwb', trial=N
%   4. noassist_nwb              → cond='noassist_nwb', trial=NaN
%   5. <mount>_<angle> e.g. high_0 / Mid_30 / low_45 → cond=lowercase, trial=NaN
%   6. fallback                   → cond=lowercased base, trial=NaN

    s = lower(base);
    % strip prefixes (robot_lkm_, Loadcell_LKM_, LKM_)
    s = regexprep(s, '^robot_lkm_', '');
    s = regexprep(s, '^loadcell_lkm_', '');
    s = regexprep(s, '^lkm_', '');

    % noassist with explicit trial number
    tk = regexp(s, '^noassist_(wb|nwb)_(\d+)$', 'tokens', 'once');
    if ~isempty(tk)
        cond = ['noassist_' tk{1}];
        trialNum = str2double(tk{2});
        return
    end
    % noassist without number
    tk = regexp(s, '^noassist_(wb|nwb)$', 'tokens', 'once');
    if ~isempty(tk)
        cond = ['noassist_' tk{1}];
        trialNum = NaN;
        return
    end
    % shank mount + angle (high_0, mid_30, low_45)
    tk = regexp(s, '^(high|mid|low)_(\d+)$', 'tokens', 'once');
    if ~isempty(tk)
        cond = sprintf('%s_%s', tk{1}, tk{2});
        trialNum = NaN;
        return
    end
    cond = s;
    trialNum = NaN;
end
