function manifest = uploadToARLAB(rawDir, varargin)
% hwalker.experiment.uploadToARLAB  End-to-end pipeline: rename → sync-cut → push.
%
%   manifest = hwalker.experiment.uploadToARLAB(rawDir, ...
%       'Subject', 'LKM', 'Speed', '1_0', 'Group', '');
%
% Layout produced (one consolidated subject root):
%
%   <SubjectDir>/                           (default <rawDir>_<Subject>)
%   ├── meta.json                           (root source-of-truth)
%   ├── Raw/
%   │   ├── meta.json                       (copy)
%   │   ├── _rename_map.csv
%   │   ├── Robot/    260504_Robot_<Subject>_TD_level_<Speed>_H-Walker_*.csv
%   │   ├── Loadcell/ ...
%   │   └── Motion/   ...
%   └── Organized/
%       ├── meta.json                       (auto-enumerated)
%       ├── _trial_index.csv
%       ├── high_0/      robot.csv  loadcell.csv  motion.qtm
%       ├── high_30/     robot.csv  loadcell.csv  motion.qtm
%       ├── ...
%       ├── noassist_wb_01/  loadcell.csv  motion.qtm
%       ├── noassist_wb_02/  loadcell.csv  motion.qtm
%       ├── noassist_nwb/    motion.qtm
%       └── Reference/       MVC_*.qtm  Static.qtm
%
% Then pushes to the ARLAB shared drive (admin@arlabcau.com), three
% locations, each carrying a copy of meta.json:
%   06_MotionData_(데이터)/01.Normal_Gait/H-Walker/Robot/<SubjectDirName>/  ← Raw/
%   02_Research_(연구)/[H-Walker]/03_Data/Paper_Works/00_Raw/<SubjectDirName>/  ← Raw/
%   02_Research_(연구)/[H-Walker]/03_Data/Paper_Works/Organized_Data/<SubjectDirName>/  ← Organized/
%
% Locale auto-detect: works on Korean ("공유 드라이브") and English
% ("Shared drives") macOS without code changes.
%
% Required:
%   'Subject'   subject initials (e.g. 'LKM')
%
% Optional:
%   'SubjectDir'    path to put consolidated subject root.
%                   default: '<rawDir>_<Subject>' (e.g. '260504_Sub01_LKM')
%   'Speed'         '1_0'  (= 1.0 m/s)
%   'Group'         ''     (or 'Parkinson' / 'Stroke' / 'SCI')
%   'Date'          ''     (auto-derived from rawDir basename if YYMMDD prefix)
%   'WeightKg'      NaN
%   'WhichSegment'  'sync-complete'
%   'PushArchive'   true   (push Raw/ to 06_MotionData/Robot archive)
%   'PushPaper'     true   (push Raw/ + Organized/ to Paper_Works)
%   'DryRun'        false

    p = inputParser;
    addParameter(p, 'Subject',      '',           @(x)ischar(x)||isstring(x));
    addParameter(p, 'SubjectDir',   '',           @(x)ischar(x)||isstring(x));
    addParameter(p, 'Speed',        '1_0',        @(x)ischar(x)||isstring(x));
    addParameter(p, 'Group',        '',           @(x)ischar(x)||isstring(x));
    addParameter(p, 'Date',         '',           @(x)ischar(x)||isstring(x));
    addParameter(p, 'WeightKg',     NaN,          @(x)isnumeric(x)&&isscalar(x));
    addParameter(p, 'WhichSegment', 'sync-complete');
    addParameter(p, 'PushArchive',  true,         @islogical);
    addParameter(p, 'PushPaper',    true,         @islogical);
    addParameter(p, 'DryRun',       false,        @islogical);
    parse(p, varargin{:});

    sub = char(p.Results.Subject);
    if isempty(sub)
        error('hwalker:uploadToARLAB:noSubject', 'Subject is required.');
    end

    if endsWith(rawDir, filesep), rawDir = rawDir(1:end-1); end
    if ~exist(rawDir, 'dir')
        error('hwalker:uploadToARLAB:noRaw', 'rawDir not found: %s', rawDir);
    end

    % --- Resolve consolidated subject root path ---
    subjectDir = char(p.Results.SubjectDir);
    if isempty(subjectDir)
        subjectDir = sprintf('%s_%s', rawDir, sub);   % e.g. 260504_Sub01_LKM
    end
    [~, subjectDirName] = fileparts(subjectDir);

    fprintf('\n========================================\n');
    fprintf(' uploadToARLAB\n');
    fprintf('   raw    : %s\n', rawDir);
    fprintf('   subj   : %s   (Subject=%s, Speed=%s, Group=%s)\n', ...
        subjectDir, sub, char(p.Results.Speed), char(p.Results.Group));
    fprintf('========================================\n');

    % --- Locate ARLAB shared drive ---
    SD = locateARLABRoot();
    if isempty(SD) && (p.Results.PushArchive || p.Results.PushPaper)
        warning('hwalker:uploadToARLAB:noSharedDrive', ...
            'ARLAB shared drive not mounted; push steps will be skipped.');
    end
    T_ARCHIVE = ''; T_RAW = ''; T_ORG = '';
    if ~isempty(SD)
        T_ARCHIVE = fullfile(SD, '06_MotionData_(데이터)', '01.Normal_Gait', ...
                                 'H-Walker', 'Robot');
        T_PAPER   = fullfile(SD, '02_Research_(연구)', '[H-Walker]', '03_Data', ...
                                 'Paper_Works');
        T_RAW     = fullfile(T_PAPER, '00_Raw');
        T_ORG     = fullfile(T_PAPER, 'Organized_Data');
    end

    rawOut    = fullfile(subjectDir, 'Raw');
    orgOut    = subjectDir;   % organizeStudy creates orgOut/Organized/ inside
    rootMeta  = fullfile(subjectDir, 'meta.json');

    % ---- Step 1: rename into <SubjectDir>/Raw/ ----
    fprintf('\n=== [1/3] rename → %s ===\n', rawOut);
    manifest = hwalker.experiment.renameRawToStandard(rawDir, rawOut, ...
        'Date',    char(p.Results.Date), ...
        'Subject', sub, ...
        'Speed',   char(p.Results.Speed), ...
        'Group',   char(p.Results.Group), ...
        'DryRun',  p.Results.DryRun);

    % ---- Step 2: organize → <SubjectDir>/Organized/ ----
    fprintf('\n=== [2/3] sync-cut → %s/Organized/ ===\n', subjectDir);
    if ~p.Results.DryRun
        % Pass the rename manifest into organize → writeMeta absorbs it
        % as `rename_map` inside meta.json (no separate CSV file).
        rmStruct = [];
        if istable(manifest) && height(manifest) > 0
            rmStruct = table2struct(manifest);
        end
        hwalker.experiment.organizeStudy(rawOut, orgOut, ...
            'WhichSegment', p.Results.WhichSegment, ...
            'Subject',  sub, ...
            'Date',     char(p.Results.Date), ...
            'Speed',    char(p.Results.Speed), ...
            'Group',    char(p.Results.Group), ...
            'WeightKg', p.Results.WeightKg, ...
            'RenameMap', rmStruct);
        % organizeStudy writes meta.json directly to subjectDir root.
        % No duplicates inside Raw/ or Organized/.
    else
        fprintf('  ⚠ DryRun — skipped\n');
    end

    % ---- Step 3: push to ARLAB ----
    fprintf('\n=== [3/3] push to ARLAB ===\n');
    srcRaw = rawOut;
    srcOrg = fullfile(subjectDir, 'Organized');
    if p.Results.DryRun || isempty(SD)
        fprintf('  ⚠ skipping push (DryRun=%d, ARLAB-mounted=%d)\n', ...
            p.Results.DryRun, ~isempty(SD));
    else
        if p.Results.PushArchive && ~isempty(T_ARCHIVE)
            pushFolder(srcRaw, fullfile(T_ARCHIVE, subjectDirName), ...
                'archive (06_MotionData/Robot)', rootMeta);
        end
        if p.Results.PushPaper
            if ~isempty(T_RAW)
                pushFolder(srcRaw, fullfile(T_RAW, subjectDirName), ...
                    'Paper_Works/00_Raw', rootMeta);
            end
            if ~isempty(T_ORG) && exist(srcOrg, 'dir')
                pushFolder(srcOrg, fullfile(T_ORG, subjectDirName), ...
                    'Paper_Works/Organized_Data', rootMeta);
            end
        end
    end

    fprintf('\n=== Done ===\n');
    fprintf('  local subject root : %s\n', subjectDir);
    fprintf('         ├ Raw/      : %s\n', rawOut);
    fprintf('         └ Organized/: %s/Organized\n', subjectDir);
    if ~isempty(T_ARCHIVE)
        fprintf('  ARLAB archive       : %s\n', fullfile(T_ARCHIVE, subjectDirName));
    end
    if ~isempty(T_RAW)
        fprintf('  ARLAB Paper/00_Raw  : %s\n', fullfile(T_RAW, subjectDirName));
    end
    if ~isempty(T_ORG)
        fprintf('  ARLAB Paper/Organized: %s\n', fullfile(T_ORG, subjectDirName));
    end
end


% ============================================================
function root = locateARLABRoot()
% Find the ARLAB shared-drive root, locale-agnostic.
    home = getenv('HOME');
    base = fullfile(home, 'Library', 'CloudStorage', ...
        'GoogleDrive-admin@arlabcau.com');
    candidates = {
        fullfile(base, '공유 드라이브', 'ARLAB'),  ... % Korean macOS
        fullfile(base, 'Shared drives', 'ARLAB'),   ... % English macOS
        fullfile(base, 'Shared Drives', 'ARLAB'),   ... % capitalized variant
    };
    root = '';
    for i = 1:numel(candidates)
        if exist(candidates{i}, 'dir')
            root = candidates{i};  return
        end
    end
end


function pushFolder(src, dst, label, rootMeta)
% Copy src/* into dst, then drop a copy of rootMeta (the subject-root
% meta.json) into dst as well so the split-archive folder is self-describing.
    if nargin < 4, rootMeta = ''; end
    fprintf('\n→ push [%s]\n', label);
    fprintf('   src: %s\n', src);
    fprintf('   dst: %s\n', dst);
    if ~exist(src, 'dir')
        warning('hwalker:uploadToARLAB:noSrc', 'src missing — skipping');
        return
    end
    [parentDst, ~] = fileparts(dst);
    if ~exist(parentDst, 'dir')
        warning('hwalker:uploadToARLAB:noDst', ...
            'destination parent missing: %s — skipping', parentDst);
        return
    end
    if ~exist(dst, 'dir'), mkdir(dst); end
    copyfile(fullfile(src, '*'), dst);
    if ~isempty(rootMeta) && exist(rootMeta, 'file')
        copyfile(rootMeta, fullfile(dst, 'meta.json'));
    end
    n = numel(dir(dst)) - 2;   % minus . and ..
    fprintf('   ✓ pushed (%d entries)\n', max(n,0));
end
