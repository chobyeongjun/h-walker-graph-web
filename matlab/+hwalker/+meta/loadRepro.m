function pkg = loadRepro(dir)
% hwalker.meta.loadRepro  Load a reproducibility package and verify integrity.
%
%   pkg = hwalker.meta.loadRepro('~/paper/repro/20260504T120000')
%
% Returns struct:
%   .result       loaded result struct
%   .params       parameters used in original run
%   .env          environment metadata
%   .input_hash   SHA-256 of original input CSV (if present)
%   .input_path   path of original input CSV
%   .git_commit   git commit at time of original run
%   .currentMatch struct .matlab .git_commit .input_hash (true/false/N/A)
%
% Prints a console summary of what matches the current environment.

    if ~exist(dir, 'dir')
        error('hwalker:loadRepro:notFound', 'Directory not found: %s', dir);
    end

    matFile = fullfile(dir, 'result.mat');
    assert(exist(matFile, 'file') == 2, ...
        'hwalker:loadRepro:noResult', 'result.mat not found in %s', dir);

    pkg.dir = dir;

    s = load(matFile, 'result');
    pkg.result = s.result;

    pkg.params = readJSON(fullfile(dir, 'parameters.json'));
    pkg.env    = readJSON(fullfile(dir, 'environment.json'));

    hashFile = fullfile(dir, 'input_hash.txt');
    if exist(hashFile, 'file')
        line = fileread(hashFile);
        parts = strsplit(strtrim(line));
        pkg.input_hash = parts{1};
        if numel(parts) >= 2, pkg.input_path = parts{2}; else, pkg.input_path = ''; end
    else
        pkg.input_hash = '';
        pkg.input_path = '';
    end

    if isstruct(pkg.env) && isfield(pkg.env, 'git_commit')
        pkg.git_commit = pkg.env.git_commit;
    else
        pkg.git_commit = '';
    end

    % --- Integrity check vs. current environment ---
    currentCommit = getCurrentGitCommit();
    pkg.currentMatch.git_commit = strcmp(currentCommit, pkg.git_commit);
    pkg.currentMatch.matlab     = strcmp(version, pkg.env.matlab_version);
    if ~isempty(pkg.input_path) && exist(pkg.input_path, 'file')
        currHash = sha256OfFile(pkg.input_path);
        pkg.currentMatch.input_hash = strcmp(currHash, pkg.input_hash);
    else
        pkg.currentMatch.input_hash = NaN;
    end

    % --- Console report ---
    fprintf('\n=== reproPackage loaded from %s ===\n', dir);
    fprintf('  Result          : %d-element struct array\n', numel(pkg.result));
    fprintf('  Original commit : %s   (current: %s)  [%s]\n', ...
        firstN(pkg.git_commit, 12), firstN(currentCommit, 12), ...
        ternary(pkg.currentMatch.git_commit, 'MATCH', 'DIFFER'));
    fprintf('  MATLAB version  : %s   (current: %s)  [%s]\n', ...
        pkg.env.matlab_version, version, ...
        ternary(pkg.currentMatch.matlab, 'MATCH', 'DIFFER'));
    if ~isnan(pkg.currentMatch.input_hash)
        fprintf('  Input CSV hash  : %s  [%s]\n', firstN(pkg.input_hash, 16), ...
            ternary(pkg.currentMatch.input_hash, 'MATCH', 'DIFFER'));
    elseif ~isempty(pkg.input_path)
        fprintf('  Input CSV       : %s  [original file not at recorded path]\n', pkg.input_path);
    end
    fprintf('===\n\n');
end


% =====================================================================
function v = readJSON(path)
    if ~exist(path, 'file'), v = struct(); return; end
    try
        txt = fileread(path);
        v   = jsondecode(txt);
    catch
        v = struct();
    end
end

function commit = getCurrentGitCommit()
    commit = '';
    try
        toolboxRoot = fileparts(fileparts(mfilename('fullpath')));
        repoRoot    = fileparts(toolboxRoot);
        if exist(fullfile(repoRoot, '.git'), 'dir')
            [s, out] = system(sprintf('cd "%s" && git rev-parse HEAD', repoRoot));
            if s == 0, commit = strtrim(out); end
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

function s = firstN(str, n)
    if numel(str) <= n, s = str; else, s = str(1:n); end
end

function v = ternary(cond, a, b)
    if cond, v = a; else, v = b; end
end
