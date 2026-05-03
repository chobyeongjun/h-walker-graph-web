function info = reproPackage(result, outputDir, varargin)
% hwalker.meta.reproPackage  Save a reproducibility package next to results.
%
%   info = hwalker.meta.reproPackage(result, '~/paper/repro')
%   info = hwalker.meta.reproPackage(result, outputDir, ...
%                'InputCSV', '/path/to/data.csv', ...
%                'Parameters', struct('alpha', 0.05))
%
% Writes everything needed to bit-replicate the analysis run that produced
% `result` (single struct OR struct array from hwalker.analyzeFile):
%
%   <outputDir>/<timestamp>/
%       result.mat                — full result struct (binary)
%       result.json               — same, JSON-encoded (human readable)
%       parameters.json           — analysis parameters used (caller-supplied)
%       environment.json          — MATLAB version, OS, hostname, toolboxes, git commit
%       input_hash.txt            — SHA-256 of input CSV file (if provided)
%       journal_presets.json      — snapshot of all 6 presets used to render
%       README.txt                — auto-generated summary of contents
%
% Returns info struct: .timestamp .dir .files .git_commit .matlab_version
%
% Use hwalker.meta.loadRepro(<dir>) to re-load and verify a saved package.

    p = inputParser;
    addParameter(p, 'InputCSV',   '', @(x) ischar(x) || isstring(x));
    addParameter(p, 'Parameters', struct(), @isstruct);
    addParameter(p, 'JournalsUsed', {'IEEE','Nature','APA','Elsevier','MDPI','JNER'});
    parse(p, varargin{:});

    inputCSV   = char(p.Results.InputCSV);
    params     = p.Results.Parameters;
    journals   = p.Results.JournalsUsed;

    % --- Output directory ---
    ts = datestr(now, 'yyyymmddTHHMMSS');               %#ok<DATST>
    if ~exist(outputDir, 'dir'), mkdir(outputDir); end
    runDir = fullfile(outputDir, ts);
    mkdir(runDir);

    files = struct();

    % --- result.mat ---
    files.mat = fullfile(runDir, 'result.mat');
    save(files.mat, 'result', '-v7');   % v7 = portable across MATLAB versions

    % --- result.json ---
    files.json = fullfile(runDir, 'result.json');
    writeJSON(files.json, struct2safe(result));

    % --- parameters.json ---
    files.params = fullfile(runDir, 'parameters.json');
    writeJSON(files.params, params);

    % --- environment.json ---
    env.matlab_version = version;
    env.matlab_release = ['R' version('-release')];
    env.os             = computer;
    try, env.hostname = char(java.net.InetAddress.getLocalHost.getHostName); ...
        catch, env.hostname = 'unknown'; end
    try, env.toolboxes = ver; ...
        env.toolboxes = {env.toolboxes.Name}; ...
        catch, env.toolboxes = {}; end
    env.git_commit = gitCommit();
    env.git_status = gitStatus();
    env.timestamp_iso = strrep(strrep(datestr(now,'yyyy-mm-ddTHH:MM:SS'),' ','T'), '/', '-'); %#ok<DATST>

    files.env = fullfile(runDir, 'environment.json');
    writeJSON(files.env, env);

    % --- input_hash.txt ---
    if ~isempty(inputCSV) && exist(inputCSV, 'file')
        h = sha256OfFile(inputCSV);
        files.hash = fullfile(runDir, 'input_hash.txt');
        fid = fopen(files.hash, 'w');
        if fid > 0
            fprintf(fid, '%s  %s\n', h, inputCSV);
            fclose(fid);
        end
    end

    % --- journal_presets.json ---
    presetSnap = struct();
    for j = 1:numel(journals)
        try
            p = hwalker.plot.journalPreset(journals{j});
            % Drop the colors matrix from JSON (huge & numeric; keep as palette name)
            if isfield(p, 'colors'),  p = rmfield(p, 'colors');  end
            if isfield(p, 'palette'), p = rmfield(p, 'palette'); end
            presetSnap.(journals{j}) = p;
        catch
            presetSnap.(journals{j}) = 'preset_load_failed';
        end
    end
    files.presets = fullfile(runDir, 'journal_presets.json');
    writeJSON(files.presets, presetSnap);

    % --- README.txt ---
    files.readme = fullfile(runDir, 'README.txt');
    writeREADME(files.readme, runDir, env, inputCSV, journals);

    info.timestamp       = ts;
    info.dir             = runDir;
    info.files           = files;
    info.git_commit      = env.git_commit;
    info.matlab_version  = env.matlab_version;

    fprintf('reproPackage: saved %d files to %s\n', ...
        numel(fieldnames(files)), runDir);
end


% =====================================================================
%  Helpers
% =====================================================================

function commit = gitCommit()
    commit = '';
    try
        toolboxRoot = fileparts(fileparts(mfilename('fullpath')));    % .../matlab/+hwalker/+meta -> .../matlab
        repoRoot    = fileparts(toolboxRoot);
        if exist(fullfile(repoRoot, '.git'), 'dir')
            [s, out] = system(sprintf('cd "%s" && git rev-parse HEAD', repoRoot));
            if s == 0
                commit = strtrim(out);
            end
        end
    catch
    end
end

function st = gitStatus()
    st = '';
    try
        toolboxRoot = fileparts(fileparts(mfilename('fullpath')));
        repoRoot    = fileparts(toolboxRoot);
        if exist(fullfile(repoRoot, '.git'), 'dir')
            [s, out] = system(sprintf('cd "%s" && git status --porcelain', repoRoot));
            if s == 0
                st = strtrim(out);
                if isempty(st), st = 'clean'; end
            end
        end
    catch
    end
end

function h = sha256OfFile(filepath)
    h = '';
    try
        md = java.security.MessageDigest.getInstance('SHA-256');
        f  = java.io.FileInputStream(filepath);
        bs = java.io.BufferedInputStream(f);
        buf = zeros(8192, 1, 'int8');
        n = bs.read(buf);
        while n > 0
            md.update(buf(1:n));
            n = bs.read(buf);
        end
        bs.close();  f.close();
        d = typecast(md.digest, 'uint8');
        h = lower(reshape(dec2hex(d, 2)', 1, []));
    catch
    end
end

function writeJSON(path, data)
    try
        s = jsonencode(data, 'PrettyPrint', true);
    catch
        s = jsonencode(data);
    end
    fid = fopen(path, 'w');
    if fid > 0
        fwrite(fid, s, 'char');
        fclose(fid);
    end
end

function writeREADME(path, dir, env, inputCSV, journals)
    fid = fopen(path, 'w');
    if fid <= 0, return; end
    fprintf(fid, 'H-Walker Reproducibility Package\n');
    fprintf(fid, '================================\n\n');
    fprintf(fid, 'Created  : %s\n', env.timestamp_iso);
    fprintf(fid, 'Run dir  : %s\n', dir);
    fprintf(fid, 'MATLAB   : %s (%s)\n', env.matlab_release, env.matlab_version);
    fprintf(fid, 'OS       : %s\n', env.os);
    fprintf(fid, 'Hostname : %s\n', env.hostname);
    fprintf(fid, 'Git HEAD : %s\n', env.git_commit);
    fprintf(fid, 'Git diff : %s\n', env.git_status);
    if ~isempty(inputCSV)
        fprintf(fid, 'Input CSV: %s\n', inputCSV);
    end
    fprintf(fid, '\nJournal presets snapshot: %s\n', strjoin(journals, ', '));
    fprintf(fid, '\nFiles in this directory:\n');
    fprintf(fid, '  result.mat            — full analysis result (MATLAB binary)\n');
    fprintf(fid, '  result.json           — same, human-readable\n');
    fprintf(fid, '  parameters.json       — analysis parameters used\n');
    fprintf(fid, '  environment.json      — MATLAB version, OS, toolboxes, git commit\n');
    fprintf(fid, '  input_hash.txt        — SHA-256 of input CSV (if provided)\n');
    fprintf(fid, '  journal_presets.json  — snapshot of all journal presets\n\n');
    fprintf(fid, 'To reproduce: hwalker.meta.loadRepro(''<this-dir>'')\n');
    fclose(fid);
end


function s = struct2safe(s)
% Recursively convert non-JSON-serializable fields (function handles,
% complex doubles, etc.) to strings so jsonencode never fails.
    if isstruct(s)
        if numel(s) > 1
            s = arrayfun(@struct2safe, s);
            return
        end
        f = fieldnames(s);
        for i = 1:numel(f)
            v = s.(f{i});
            if isa(v, 'function_handle')
                s.(f{i}) = func2str(v);
            elseif iscomplex(v)
                s.(f{i}) = struct('real', real(v), 'imag', imag(v));
            elseif isstruct(v)
                s.(f{i}) = struct2safe(v);
            elseif iscell(v)
                s.(f{i}) = cellfun(@struct2safe, v, 'UniformOutput', false);
            end
        end
    end
end

function tf = iscomplex(v)
    tf = isnumeric(v) && ~isreal(v);
end
