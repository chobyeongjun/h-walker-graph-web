function meta = writeMeta(targetDir, varargin)
% hwalker.experiment.writeMeta  Build and write meta.json for a session folder.
%
%   meta = hwalker.experiment.writeMeta(targetDir, ...
%       'Subject',  'LKM', ...
%       'Date',     '260504', ...
%       'Speed',    '1_0', ...
%       'Group',    '', ...
%       'WeightKg', 80, ...
%       'Existing', '');         % path to existing meta.json to merge in
%
% targetDir is a session folder with modality-folder layout, e.g.:
%
%   targetDir/
%     ├── Robot/    high_0.csv  high_30.csv  ...
%     ├── Loadcell/ high_0.csv  ...  noassist_wb_01.csv  noassist_wb_02.csv
%     ├── Motion/   high_0.qtm  ...  noassist_nwb.qtm
%     └── Reference/ MVC_BF.qtm  ...  Static.qtm
%
% Auto-enumerates conditions (union of file basenames across modality
% folders), each condition's modality coverage, and Reference/ contents.
% Writes meta.json to targetDir/meta.json.
%
% meta.json is the single source of truth — analysis functions read this
% rather than parsing the long upload-form filenames.

    p = inputParser;
    addParameter(p, 'Subject',       '',  @(x)ischar(x)||isstring(x));
    addParameter(p, 'Date',          '',  @(x)ischar(x)||isstring(x));
    addParameter(p, 'Speed',         '',  @(x)ischar(x)||isstring(x));
    addParameter(p, 'Group',         '',  @(x)ischar(x)||isstring(x));
    addParameter(p, 'WeightKg',      NaN, @(x)isnumeric(x)&&isscalar(x));
    addParameter(p, 'NamingVersion', 'v2_2026-05-05', @(x)ischar(x)||isstring(x));
    addParameter(p, 'Existing',      '',  @(x)ischar(x)||isstring(x));
    addParameter(p, 'Cuts',          [],  @(x)isstruct(x)||isempty(x));
    addParameter(p, 'RenameMap',     [],  @(x)isstruct(x)||istable(x)||isempty(x));
    parse(p, varargin{:});

    if ~exist(targetDir, 'dir')
        error('hwalker:writeMeta:noTarget', 'targetDir not found: %s', targetDir);
    end

    meta = struct();
    meta.naming_version = char(p.Results.NamingVersion);

    % --- Merge with existing meta.json if provided ---
    existing = char(p.Results.Existing);
    if ~isempty(existing) && exist(existing, 'file')
        try
            old = jsondecode(fileread(existing));
            fns = fieldnames(old);
            for k = 1:numel(fns), meta.(fns{k}) = old.(fns{k}); end
        catch ME
            warning('hwalker:writeMeta:mergeFail', ...
                'Could not parse existing meta.json (%s): %s', existing, ME.message);
        end
    end

    % --- Override with arguments (only if non-empty) ---
    sub = char(p.Results.Subject);
    dt  = char(p.Results.Date);
    sp  = char(p.Results.Speed);
    gr  = char(p.Results.Group);
    wk  = p.Results.WeightKg;
    if ~isempty(sub), meta.subject = sub; end
    if ~isempty(dt),  meta.date    = dt;  end
    if ~isempty(sp)
        meta.speed_token = sp;
        spnum = str2double(strrep(sp, '_', '.'));
        if ~isnan(spnum), meta.speed_ms = spnum; end
    end
    if ~isempty(gr) || ~isfield(meta, 'group'), meta.group = gr; end
    if ~isnan(wk),    meta.weight_kg = wk; end

    % --- Force-profile defaults (H-Walker fixed protocol) ---
    if ~isfield(meta, 'force_profile') || isempty(meta.force_profile)
        meta.force_profile = struct( ...
            'onset_pct',       55, ...
            'peak_pct',        70, ...
            'release_pct',     85, ...
            'target_N',        50, ...
            'rmse_window_pct', [55, 85]);
    end

    % --- Auto-enumerate condition + reference folders ---
    [conds, modPer, refFiles] = enumerateFolders(targetDir);
    meta.conditions               = conds;
    meta.modalities_per_condition = modPer;
    meta.reference_files          = refFiles;

    % --- Optional sync-cut info (absorbs old _trial_index.csv) ---
    if ~isempty(p.Results.Cuts)
        meta.cuts = p.Results.Cuts;
    end

    % --- Optional rename map (absorbs old _rename_map.csv) ---
    if ~isempty(p.Results.RenameMap)
        rm = p.Results.RenameMap;
        if istable(rm), rm = table2struct(rm); end
        meta.rename_map = rm;
    end

    % --- Write ---
    outFile = fullfile(targetDir, 'meta.json');
    txt = jsonencode(meta, 'PrettyPrint', true);
    fid = fopen(outFile, 'w');
    if fid < 0, error('hwalker:writeMeta:writeFail', 'cannot write %s', outFile); end
    fwrite(fid, txt, 'char');
    fclose(fid);

    fprintf('  ✓ meta.json (%s): %d conditions, %d MVC, %d ref-static\n', ...
        outFile, numel(conds), numel(refFiles.mvc), ...
        ~isempty(refFiles.static));
end


% ====================================================================
function [conds, modPer, refFiles] = enumerateFolders(rootDir)
% Layout: modality-folder. Each condition appears as a file basename
% inside one or more of {Robot/, Loadcell/, Motion/, EMG/}.
    modPer   = struct();
    refFiles = struct('mvc', {{}}, 'static', '');

    modDirs = {'Robot', 'Loadcell', 'Motion', 'EMG'};
    seen    = containers.Map('KeyType','char','ValueType','any');

    for k = 1:numel(modDirs)
        modName = modDirs{k};
        prefix  = [lower(modName) '_'];     % 'robot_' / 'loadcell_' / ...
        mDir = fullfile(rootDir, modName);
        if ~exist(mDir, 'dir'), continue; end
        files = dir(mDir);
        for j = 1:numel(files)
            if files(j).isdir, continue; end
            if startsWith(files(j).name, '.'), continue; end
            [~, base, ~] = fileparts(files(j).name);
            if isempty(base), continue; end
            % Strip modality prefix → bare condition key
            if startsWith(lower(base), prefix)
                cond = base(numel(prefix)+1:end);
            else
                cond = base;
            end
            if ~isKey(seen, cond), seen(cond) = {}; end
            arr = seen(cond);
            arr{end+1} = modName;                                       %#ok<AGROW>
            seen(cond) = arr;
        end
    end

    conds = sort(keys(seen));
    for i = 1:numel(conds)
        c = conds{i};
        modPer.(matlab.lang.makeValidName(c)) = sort(seen(c));
    end

    refDir = fullfile(rootDir, 'Reference');
    if exist(refDir, 'dir')
        refFiles = enumReference(refDir);
    end
end


function refFiles = enumReference(refDir)
    refFiles = struct('mvc', {{}}, 'static', '');
    rf = dir(refDir);
    for j = 1:numel(rf)
        if rf(j).isdir, continue; end
        [~, base, ~] = fileparts(rf(j).name);
        if startsWith(lower(base), 'mvc')
            refFiles.mvc{end+1} = base;                                 %#ok<AGROW>
        elseif strcmpi(base, 'static') || contains(lower(base), 'static')
            refFiles.static = base;
        end
    end
    refFiles.mvc = sort(refFiles.mvc);
end
