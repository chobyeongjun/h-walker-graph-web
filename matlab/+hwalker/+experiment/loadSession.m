function session = loadSession(condDir, varargin)
% hwalker.experiment.loadSession  Load all modalities from one condition folder.
%
%   session = hwalker.experiment.loadSession( ...
%       '~/h-walker-experiments/studies/2026-05-04/sub-01/cond-baseline')
%
%   session = hwalker.experiment.loadSession(condDir, ...
%       'CommonFs', 1000, 'BodyMassKg', 72.0, 'MVCFile', '...')
%
% Expects (per MULTIMODAL_PIPELINE.md, hard standard):
%
%   condDir/
%     ├── robot.csv         (REQUIRED — H-Walker firmware)
%     ├── motion.c3d|csv|tsv (optional — MoCap + force plate)
%     ├── force.csv          (optional — separate force plate file)
%     ├── emg.csv            (optional)
%     └── loadcell.csv       (optional — BWS)
%
% Subject metadata read from `condDir/../meta.json` if present.
%
% Returns struct:
%   .subject_id .condition .source_dir
%   .meta              (from meta.json)
%   .fs_common         common sample rate after sync (default 1000 Hz)
%   .t                 common time axis
%   .robot             from analyzeFile (sync-windowed if applicable)
%   .motion            from loadMotion (or [] if missing)
%   .emg               from loadEMG    (or [] if missing)
%   .loadcell          from loadLoadcell (or [] if missing)
%   .qc                struct .files_present, .sync_lock_ok, .durations_s

    p = inputParser;
    addParameter(p, 'CommonFs',   1000, @(x) isnumeric(x) && isscalar(x) && x >= 100);
    addParameter(p, 'BodyMassKg', NaN,  @(x) isnumeric(x) && isscalar(x));
    addParameter(p, 'MVCFile',    '',   @(x) ischar(x) || isstring(x));
    parse(p, varargin{:});
    commonFs = p.Results.CommonFs;
    bodyMass = p.Results.BodyMassKg;
    mvcFile  = char(p.Results.MVCFile);

    if ~exist(condDir, 'dir')
        error('hwalker:experiment:loadSession:notDir', ...
            'Condition directory not found: %s', condDir);
    end

    [parentDir, condName] = fileparts(condDir);
    [~, subjId] = fileparts(parentDir);

    session = struct();
    session.subject_id = subjId;
    session.condition  = strrep(condName, 'cond-', '');
    session.source_dir = condDir;

    % --- Subject meta from sub-XX/meta.json ---
    metaPath = fullfile(parentDir, 'meta.json');
    if exist(metaPath, 'file')
        try
            session.meta = jsondecode(fileread(metaPath));
            if isnan(bodyMass) && isfield(session.meta, 'mass_kg')
                bodyMass = session.meta.mass_kg;
            end
        catch ME
            warning('hwalker:loadSession:metaParseFail', ...
                'Could not parse %s: %s', metaPath, ME.message);
            session.meta = struct();
        end
    else
        session.meta = struct();
    end

    % ============================================================
    %  File presence check — supports BOTH naming conventions:
    %    1. Standard fixed names (recommended):
    %         robot.csv / motion.c3d / emg.csv / loadcell.csv
    %    2. Legacy H-Walker filename pattern (auto-detected):
    %         260430_Robot_CBJ_TD_level_0_5_walker_high_0.csv
    %         260430_Loadcell_CBJ_TD_...csv
    %         260430_Motion_CBJ_TD_...csv  (or .c3d / .tsv)
    %  Either works — pick whichever you already have.
    % ============================================================
    files = struct('robot','', 'motion','', 'force','', 'emg','', 'loadcell','');

    % First: try standard names
    files.robot    = pickFirst(condDir, {'robot.csv'});
    files.motion   = pickFirst(condDir, {'motion.c3d','motion.tsv','motion.csv'});
    files.force    = pickFirst(condDir, {'force.csv','grf.csv'});
    files.emg      = pickFirst(condDir, {'emg.csv'});
    files.loadcell = pickFirst(condDir, {'loadcell.csv','bws.csv'});

    % Fallback: scan every csv / c3d / tsv and classify by parseFilename source
    if isempty(files.robot) || isempty(files.loadcell) || isempty(files.motion)
        files = scanByLegacyPattern(condDir, files);
    end

    session.qc.files_present = files;

    if isempty(files.robot)
        error('hwalker:loadSession:noRobot', ...
            'robot.csv is REQUIRED in %s.', condDir);
    end

    % ============================================================
    %  Robot (always)
    % ============================================================
    fprintf('\n=== Loading session %s/%s ===\n', subjId, session.condition);
    session.robot = hwalker.analyzeFile(files.robot, 'label', ...
        sprintf('%s_%s', subjId, session.condition));
    if numel(session.robot) > 1
        fprintf('  [robot] %d sync windows; using first for session-level analysis\n', ...
            numel(session.robot));
        sessionRobotPrimary = session.robot(1);
    else
        sessionRobotPrimary = session.robot;
    end

    % ============================================================
    %  Motion (optional)
    % ============================================================
    if ~isempty(files.motion)
        try
            session.motion = hwalker.io.loadMotion(files.motion);
        catch ME
            warning('hwalker:loadSession:motionFail', '%s', ME.message);
            session.motion = [];
        end
    else
        session.motion = [];
    end

    % ============================================================
    %  EMG (optional)
    % ============================================================
    if ~isempty(files.emg)
        try
            if ~isempty(mvcFile)
                session.emg = hwalker.io.loadEMG(files.emg, 'MVCFile', mvcFile);
            else
                session.emg = hwalker.io.loadEMG(files.emg);
            end
        catch ME
            warning('hwalker:loadSession:emgFail', '%s', ME.message);
            session.emg = [];
        end
    else
        session.emg = [];
    end

    % ============================================================
    %  Loadcell (optional)
    % ============================================================
    if ~isempty(files.loadcell)
        try
            session.loadcell = hwalker.io.loadLoadcell(files.loadcell, ...
                'BodyMassKg', bodyMass);
        catch ME
            warning('hwalker:loadSession:loadcellFail', '%s', ME.message);
            session.loadcell = [];
        end
    else
        session.loadcell = [];
    end

    % ============================================================
    %  Sync + common time base (informational; per-modality time
    %  retained, but session.t shows the union duration)
    % ============================================================
    session.fs_common = commonFs;
    durations = [sessionRobotPrimary.durationS];
    if ~isempty(session.motion) && ~isempty(session.motion.t_marker)
        durations(end+1) = session.motion.t_marker(end) - session.motion.t_marker(1);
    end
    if ~isempty(session.emg)
        durations(end+1) = session.emg.t(end) - session.emg.t(1);
    end
    if ~isempty(session.loadcell)
        durations(end+1) = session.loadcell.t(end) - session.loadcell.t(1);
    end
    Tend = min(durations);                                 % shortest = aligned trim
    session.t = (0:1/commonFs:Tend)';
    session.qc.durations_s = durations;
    session.qc.sync_lock_ok = (max(durations) - min(durations)) < 1.0;
    if ~session.qc.sync_lock_ok
        fprintf('  ⚠ modality durations differ by >1s: %s\n', mat2str(durations, 4));
    end

    fprintf('=== %s/%s ready (%.1fs aligned, %d modalities) ===\n', ...
        subjId, session.condition, Tend, ...
        sum([~isempty(session.motion) ~isempty(session.emg) ~isempty(session.loadcell)]) + 1);
end


function f = pickFirst(dir_, candidates)
% Return the first existing file from candidates list, or '' if none.
    f = '';
    for i = 1:numel(candidates)
        cand = fullfile(dir_, candidates{i});
        if exist(cand, 'file')
            f = cand;
            return
        end
    end
end


function files = scanByLegacyPattern(dir_, files)
% Auto-classify files in `dir_` using hwalker.io.parseFilename.
% Recognises legacy H-Walker filenames such as
%   260430_Robot_CBJ_TD_level_0_5_walker_high_0.csv
%   260430_Loadcell_CBJ_TD_level_0_5_walker_high_0.csv
%   260430_Motion_CBJ_TD_level_0_5_walker_high_0.csv  (or .c3d/.tsv)
% Whichever side (Robot/Motion/Loadcell) is filled in by the legacy
% scan only when the standard-named slot is still empty.
    % Scan CSV
    listing = dir(fullfile(dir_, '*.csv'));
    for i = 1:numel(listing)
        full = fullfile(dir_, listing(i).name);
        try
            info = hwalker.io.parseFilename(listing(i).name);
        catch
            info = struct('source','');
        end
        switch lower(getfieldOr(info, 'source', ''))
            case 'robot'
                if isempty(files.robot),    files.robot    = full; end
            case 'loadcell'
                if isempty(files.loadcell), files.loadcell = full; end
            case 'motion'
                if isempty(files.motion),   files.motion   = full; end
        end
        % Heuristic: filenames containing 'emg' (case-insensitive)
        if isempty(files.emg) && ~isempty(regexpi(listing(i).name, '(^|[_-])emg([_-]|\.)', 'once'))
            files.emg = full;
        end
        % Heuristic: 'force' or 'grf'
        if isempty(files.force) && ~isempty(regexpi(listing(i).name, '(^|[_-])(force|grf)([_-]|\.)', 'once'))
            files.force = full;
        end
        % Heuristic: 'loadcell' or 'bws'
        if isempty(files.loadcell) && ~isempty(regexpi(listing(i).name, '(^|[_-])(loadcell|bws)([_-]|\.)', 'once'))
            files.loadcell = full;
        end
    end
    % Scan C3D / TSV for motion (these formats unambiguously identify motion data)
    if isempty(files.motion)
        for ext = {'*.c3d','*.tsv'}
            listing = dir(fullfile(dir_, ext{1}));
            if ~isempty(listing)
                files.motion = fullfile(dir_, listing(1).name);
                return
            end
        end
    end
end


function v = getfieldOr(s, name, default)
    if isstruct(s) && isfield(s, name) && ~isempty(s.(name))
        v = s.(name);
    else
        v = default;
    end
end
