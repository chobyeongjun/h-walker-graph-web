function manifest = organizeStudy(rawDir, organizedDir, varargin)
% hwalker.experiment.organizeStudy  Sync-cut raw data into a paper-ready Organized/ tree.
%
%   manifest = hwalker.experiment.organizeStudy(rawDir, organizedDir)
%   manifest = hwalker.experiment.organizeStudy(rawDir, organizedDir, ...
%                'WhichCycle', 'longest',  ...   % 'longest' (default) | 1 | 2 | 'all'
%                'CopyMotion', true,       ...   % copy .qtm/.mat as-is
%                'CopyReference', true)
%
% Inputs:
%   rawDir         folder containing Robot/ Loadcell/ Motion/ subfolders
%                  (each with raw modality files — H-Walker convention)
%   organizedDir   destination root.  Creates organizedDir/Organized/
%                  with sub-folders Motion/ Robot/ Loadcell/ Reference/
%
% Pipeline:
%   1. Scan Robot/*.CSV → trial keys (filename minus prefix/extension).
%   2. For each robot trial:
%        a. Detect sync cycles via hwalker.sync.findWindows on its A7
%        b. Pick the cycle per WhichCycle setting (longest = paper window)
%        c. Slice the table to [t_start, t_end], rebase Time_ms to start=0
%        d. Save Organized/Robot/<trial>.csv
%   3. For each loadcell file matching the trial key (Loadcell/*<key>*.CSV):
%        a. Detect sync cycles on its `a7` column
%        b. Slice the same way (own clock, own rising edge → 0)
%        c. Save Organized/Loadcell/<trial>.csv
%   4. Motion: matching <trial>.{qtm,mat,c3d} copied as-is
%      (.qtm is binary — pre-cut not possible without QTM; toolbox loads
%       full file later via loadMotion when user has exported to .mat).
%   5. MVC_*.{qtm,mat} and Static.{qtm,mat} → Reference/ as-is.
%   6. Write _trial_index.csv (trial → original samples → cut samples →
%      cycle duration → modality file paths).
%   7. Write README.md (one-page summary).
%
% Returns manifest struct array with one row per (trial × modality):
%   .trial .modality .src .dst .cycleStart_s .cycleEnd_s .cycleDur_s
%   .nSamplesIn .nSamplesOut .syncOK .note

    p = inputParser;
    addParameter(p, 'WhichCycle',    'longest', ...
        @(x) (ischar(x) && any(strcmpi(x, {'longest','all','first'}))) || isnumeric(x));
    addParameter(p, 'WhichSegment',  'sync-complete', ...
        @(x) (ischar(x) && any(strcmpi(x, ...
            {'sync-complete','last','longest','first'}))) || isnumeric(x));
    addParameter(p, 'CopyMotion',    true,  @islogical);
    addParameter(p, 'CopyReference', true,  @islogical);
    addParameter(p, 'MinDurationS',  0.5,   @(x) isnumeric(x) && isscalar(x));
    parse(p, varargin{:});
    whichCycle   = p.Results.WhichCycle;
    whichSeg     = p.Results.WhichSegment;

    if ~exist(rawDir, 'dir')
        error('hwalker:organizeStudy:badRaw', 'rawDir not found: %s', rawDir);
    end

    outRoot = fullfile(organizedDir, 'Organized');
    out_M = fullfile(outRoot, 'Motion');
    out_R = fullfile(outRoot, 'Robot');
    out_L = fullfile(outRoot, 'Loadcell');
    out_F = fullfile(outRoot, 'Reference');
    for d = {outRoot, out_M, out_R, out_L, out_F}
        if ~exist(d{1}, 'dir'), mkdir(d{1}); end
    end

    manifest = struct('trial',{},'modality',{},'src',{},'dst',{}, ...
        'cycleStart_s',{},'cycleEnd_s',{},'cycleDur_s',{}, ...
        'nSamplesIn',{},'nSamplesOut',{},'syncOK',{},'note',{});

    fprintf('\n========================================\n');
    fprintf(' organizeStudy\n');
    fprintf('   raw : %s\n   out : %s\n', rawDir, outRoot);
    fprintf('========================================\n');

    % ---------- Robot ----------
    rawRobotDir = fullfile(rawDir, 'Robot');
    robotFiles = dir(fullfile(rawRobotDir, '*.CSV'));   % macOS case-insensitive — single glob
    trialKeys = {};
    for i = 1:numel(robotFiles)
        fn = robotFiles(i).name;
        key = extractTrialKey(fn);
        trialKeys{end+1} = key;                                          %#ok<AGROW>
        src = fullfile(rawRobotDir, fn);
        try
            T = hwalker.io.loadCSV(src);
            [T, ~] = hwalker.experiment.pickSegment(T, whichSeg);
            t  = hwalker.io.timeAxis(T);
            cycles = hwalker.sync.findWindows(T, 'MinDurationS', p.Results.MinDurationS);
            row = pickCycle(cycles, whichCycle);
            if isempty(row)
                fprintf(' [Robot]    %-20s NO CYCLE — copy as-is\n', key);
                Tcut = T;  cs = NaN; ce = NaN;
            else
                cs = row(1); ce = row(2);
                mask = t >= cs & t < ce;
                Tcut = T(mask, :);
                if ismember('Time_ms', T.Properties.VariableNames)
                    Tcut.Time_ms = Tcut.Time_ms - Tcut.Time_ms(1);
                end
                fprintf(' [Robot]    %-20s cycle %.2f-%.2f s (%.2fs) → %d samples\n', ...
                    key, cs, ce, ce-cs, sum(mask));
            end
            dst = fullfile(out_R, [key '.csv']);
            writetable(Tcut, dst);
            manifest(end+1) = mkrow(key,'Robot',src,dst,cs,ce, ...
                height(T), height(Tcut), ~isempty(row), '');     %#ok<AGROW>
        catch ME
            fprintf(' [Robot]    %-20s ERROR: %s\n', key, ME.message);
            manifest(end+1) = mkrow(key,'Robot',src,'',NaN,NaN,NaN,NaN,false,ME.message); %#ok<AGROW>
        end
    end

    % ---------- Loadcell ----------
    rawLCDir = fullfile(rawDir, 'Loadcell');
    if exist(rawLCDir, 'dir')
        lcFiles = dir(fullfile(rawLCDir, '*.CSV'));    % macOS case-insensitive
        for i = 1:numel(lcFiles)
            fn = lcFiles(i).name;
            % Use unified trial-key extractor (handles both legacy + new naming)
            matched = extractTrialKey(fn);
            % If extracted key already in robot trialKeys, reuse for matching;
            % otherwise add it (e.g. loadcell-only noassist trials)
            if ~ismember(matched, trialKeys)
                trialKeys{end+1} = matched;                             %#ok<AGROW>
            end
            src = fullfile(rawLCDir, fn);
            try
                Tl = readtable(src, 'VariableNamingRule', 'preserve');
                % Multi-segment detect on loadcell timestamp_ms too
                if ismember('timestamp_ms', Tl.Properties.VariableNames)
                    tsRaw = double(Tl.timestamp_ms);
                    dtL = diff(tsRaw);
                    bj = find(dtL < -1000);
                    if ~isempty(bj)
                        bounds = [0; bj; height(Tl)];
                        nSeg = numel(bounds)-1;
                        dursL = arrayfun(@(i) (tsRaw(bounds(i+1)) - tsRaw(bounds(i)+1))/1000, 1:nSeg);
                        if isnumeric(whichSeg)
                            pick = max(min(round(whichSeg), nSeg), 1);
                        else
                            switch lower(whichSeg)
                                case 'last', pick = nSeg;
                                case 'first', pick = 1;
                                case 'longest', [~, pick] = max(dursL);
                                otherwise, pick = nSeg;
                            end
                        end
                        fprintf('   ⚠ %s loadcell: %d segments (durs=%s s); using seg %d\n', ...
                            matched, nSeg, mat2str(round(dursL)), pick);
                        Tl = Tl(bounds(pick)+1:bounds(pick+1), :);
                    end
                end
                ts = double(Tl.timestamp_ms);
                tl = (ts - ts(1)) / 1000;     % seconds, t=0 at file start
                if ismember('a7', Tl.Properties.VariableNames)
                    syncCol = 'a7';
                elseif ismember('A7', Tl.Properties.VariableNames)
                    syncCol = 'A7';
                else
                    syncCol = '';
                end
                cs = NaN; ce = NaN; cycleOK = false;
                if ~isempty(syncCol)
                    s = double(Tl.(syncCol));
                    finite = isfinite(s);
                    if any(finite) && (max(s)-min(s) > 1e-9)
                        thr = (min(s(finite))+max(s(finite)))/2;
                        hi = s > thr;
                        d = diff(int8(hi));
                        rs = find(d == 1) + 1;
                        fl = find(d == -1) + 1;
                        % Build cycles per spec: rising[i] → next falling
                        cycLC = [];
                        for r = 1:numel(rs)
                            f = fl(fl > rs(r));
                            if ~isempty(f)
                                cycLC = [cycLC; tl(rs(r)), tl(f(1))];   %#ok<AGROW>
                            end
                        end
                        % Filter min duration
                        cycLC = cycLC((cycLC(:,2)-cycLC(:,1)) >= p.Results.MinDurationS, :);
                        row = pickCycle(cycLC, whichCycle);
                        if ~isempty(row)
                            cs = row(1); ce = row(2);
                            mask = tl >= cs & tl < ce;
                            Tl = Tl(mask, :);
                            Tl.timestamp_ms = Tl.timestamp_ms - Tl.timestamp_ms(1);
                            cycleOK = true;
                            fprintf(' [Loadcell] %-20s cycle %.2f-%.2f s (%.2fs) → %d samples\n', ...
                                matched, cs, ce, ce-cs, sum(mask));
                        end
                    end
                end
                if ~cycleOK
                    fprintf(' [Loadcell] %-20s no sync cycle, copying full\n', matched);
                end
                dst = fullfile(out_L, [matched '.csv']);
                writetable(Tl, dst);
                manifest(end+1) = mkrow(matched,'Loadcell',src,dst,cs,ce, ...
                    NaN, height(Tl), cycleOK, '');                       %#ok<AGROW>
            catch ME
                fprintf(' [Loadcell] %-20s ERROR: %s\n', matched, ME.message);
            end
        end
    end

    % ---------- Motion (and Reference: MVC_*, Static) ----------
    rawMDir = fullfile(rawDir, 'Motion');
    if exist(rawMDir, 'dir') && p.Results.CopyMotion
        mFiles = [dir(fullfile(rawMDir, '*.qtm')); ...
                  dir(fullfile(rawMDir, '*.mat')); ...
                  dir(fullfile(rawMDir, '*.c3d')); ...
                  dir(fullfile(rawMDir, '*.tsv'))];
        for i = 1:numel(mFiles)
            fn = mFiles(i).name;
            isMVC    = startsWith(lower(fn), 'mvc');
            isStatic = contains(lower(fn), 'static');
            isRef    = isMVC || isStatic;
            src = fullfile(rawMDir, fn);
            if isRef
                if p.Results.CopyReference
                    dst = fullfile(out_F, fn);
                    copyfile(src, dst);
                    manifest(end+1) = mkrow(fn,'Reference',src,dst,NaN,NaN,NaN,NaN,false,'reference (raw)'); %#ok<AGROW>
                end
            else
                % Unified extractor — handles legacy LKM_* and new H-Walker_* naming
                key = extractTrialKey(fn);
                [~, ~, ext] = fileparts(fn);
                dst = fullfile(out_M, [key, lower(ext)]);
                copyfile(src, dst);
                fprintf(' [Motion]   %-20s copy (%s)\n', key, ext);
                manifest(end+1) = mkrow(key,'Motion',src,dst,NaN,NaN,NaN,NaN,false, ...
                    'copy as-is — toolbox cuts during loadMotion'); %#ok<AGROW>
            end
        end
    end

    % ---------- Trial index CSV + README ----------
    Tm = struct2table(manifest);
    writetable(Tm, fullfile(organizedDir, '_trial_index.csv'));

    fid = fopen(fullfile(organizedDir, 'README.md'), 'w');
    if fid > 0
        fprintf(fid, '# Organized Data — %s\n\n', date);
        fprintf(fid, 'Generated by `hwalker.experiment.organizeStudy`\n\n');
        fprintf(fid, 'Source raw: `%s`\n\n', rawDir);
        fprintf(fid, '## Folders\n');
        fprintf(fid, '- `Organized/Robot/<trial>.csv`     sync-cut, t=0 at first rising edge\n');
        fprintf(fid, '- `Organized/Loadcell/<trial>.csv`  sync-cut on own clock, t=0\n');
        fprintf(fid, '- `Organized/Motion/<trial>.qtm`    raw copy (toolbox cuts on load if .mat)\n');
        fprintf(fid, '- `Organized/Reference/`            MVC_*.qtm + Static.qtm (no sync cut)\n\n');
        fprintf(fid, '## Trial index\n\n');
        fprintf(fid, 'See `_trial_index.csv` for trial → modality → cycle window mapping.\n\n');
        fprintf(fid, '## Next step\n');
        fprintf(fid, '```matlab\n');
        fprintf(fid, 'cd ~/h-walker-graph-web/matlab; install\n');
        fprintf(fid, '%% loadSession on Organized/  (treats it like a single condition folder)\n');
        fprintf(fid, '%% Per-trial: hwalker.analyzeFile(''Organized/Robot/high_0.csv'')\n');
        fprintf(fid, '```\n');
        fclose(fid);
    end

    fprintf('\n=== Done ===\n');
    fprintf('  trials processed: %d\n', numel(unique({manifest.trial})));
    fprintf('  manifest entries: %d\n', numel(manifest));
    fprintf('  index: %s/_trial_index.csv\n', organizedDir);
end


% ====================================================================
function T = pickContiguousSegment(T, which, label)
% Detect Time_ms backward jumps (Teensy reset / record stop+start) and
% return only the chosen contiguous segment.
%
% 'which' selection rules:
%   'sync-complete' (default) — pick the segment that contains a complete
%                                 sync cycle (≥1 rising followed by ≥1
%                                 falling on the A7 column). If multiple
%                                 segments qualify, the longest among them
%                                 wins. Rationale: only segments where the
%                                 user actually toggled sync OFF after
%                                 toggling it ON are paper trials.
%   'last'    — last segment in the file
%   'longest' — longest by duration
%   'first'   — first segment
%   integer N — that index
    if ~ismember('Time_ms', T.Properties.VariableNames), return; end
    tm = double(T.Time_ms);
    dt = diff(tm);
    backJump = find(dt < -1000);
    if isempty(backJump), return; end

    bounds = [0; backJump; height(T)];
    nSeg = numel(bounds) - 1;
    durs = zeros(nSeg, 1);
    syncOK = false(nSeg, 1);
    sIdx = zeros(nSeg, 1);
    eIdx = zeros(nSeg, 1);
    for i = 1:nSeg
        sIdx(i) = bounds(i) + 1;
        eIdx(i) = bounds(i+1);
        durs(i) = (tm(eIdx(i)) - tm(sIdx(i))) / 1000;
        % Test if this segment has at least one rising followed by a falling
        if ismember('A7', T.Properties.VariableNames)
            seg = double(T.A7(sIdx(i):eIdx(i)));
            ok = isfinite(seg);
            if any(ok) && (max(seg(ok)) - min(seg(ok))) > 1e-6
                thr = (min(seg(ok)) + max(seg(ok))) / 2;
                hi = seg > thr;
                d = diff(int8(hi));
                rs = find(d == 1);
                fl = find(d == -1);
                % Need at least one falling that comes AFTER a rising
                if ~isempty(rs) && ~isempty(fl) && any(fl > rs(1))
                    syncOK(i) = true;
                end
            end
        end
    end

    if isnumeric(which)
        pick = max(min(round(which), nSeg), 1);
        method = sprintf('seg %d (manual index)', pick);
    else
        switch lower(which)
            case 'sync-complete'
                if any(syncOK)
                    cand = find(syncOK);
                    [~, j] = max(durs(cand));
                    pick = cand(j);
                    method = sprintf('seg %d (longest with complete sync cycle)', pick);
                else
                    [~, pick] = max(durs);
                    method = sprintf('seg %d (NO sync-complete seg → fallback longest)', pick);
                end
            case 'last',    pick = nSeg;          method = 'seg last';
            case 'first',   pick = 1;             method = 'seg first';
            case 'longest', [~, pick] = max(durs); method = sprintf('seg %d (longest)', pick);
            otherwise,      pick = nSeg;          method = 'seg last';
        end
    end
    syncMark = arrayfun(@(b) ternary(b,'✓','×'), syncOK, 'UniformOutput', false);
    durStr = strjoin(arrayfun(@(i) sprintf('%ds%s', round(durs(i)), syncMark{i}), ...
        1:nSeg, 'UniformOutput', false), ', ');
    fprintf('   ⚠ %s: %d segments [%s] → %s\n', label, nSeg, durStr, method);
    T = T(sIdx(pick):eIdx(pick), :);
end

function v = ternary(cond, a, b)
    if cond, v = a; else, v = b; end
end


function key = extractTrialKey(fn)
% Map a raw filename to a stable trial key (e.g., 'high_0', 'noassist_wb_02').
% Recognizes:
%   robot_lkm_high_0.CSV                         → 'high_0'
%   Loadcell_LKM_High_30.CSV                     → 'high_30'
%   LKM_low_45.qtm                               → 'low_45'
%   LKM_noassist_wb_2.qtm                        → 'noassist_wb_02'
%   260504_Robot_LKM_TD_level_1_0_H-Walker_high_0_01.csv  → 'high_0_01'
    base = regexprep(fn, '\.[^.]*$', '');     % strip extension
    s = lower(base);
    s = regexprep(s, '^\d{6}_(robot|loadcell|motion|emg)_[a-z]+_td_level_\d+_\d+_h-walker_(.*)$', '$2');
    if contains(s, 'parkinson_')
        s = regexprep(s, '^parkinson_', '');
    end
    s = regexprep(s, '^robot_lkm_', '');
    s = regexprep(s, '^loadcell_lkm_', '');
    s = regexprep(s, '^lkm_', '');
    key = s;
end


function row = pickCycle(cycles, whichCycle)
    if isempty(cycles), row = []; return; end
    if isnumeric(whichCycle)
        idx = whichCycle;
        if idx > size(cycles, 1), row = []; else, row = cycles(idx, :); end
    else
        switch lower(whichCycle)
            case 'longest'
                durs = cycles(:,2) - cycles(:,1);
                [~, i] = max(durs);
                row = cycles(i, :);
            case 'first'
                row = cycles(1, :);
            case 'all'
                row = cycles;     % caller iterates if needed
            otherwise
                row = cycles(1, :);
        end
    end
end

function r = mkrow(trial, modality, src, dst, cs, ce, nIn, nOut, syncOK, note)
    r.trial         = char(trial);
    r.modality      = char(modality);
    r.src           = char(src);
    r.dst           = char(dst);
    r.cycleStart_s  = cs;
    r.cycleEnd_s    = ce;
    r.cycleDur_s    = ce - cs;
    r.nSamplesIn    = nIn;
    r.nSamplesOut   = nOut;
    r.syncOK        = logical(syncOK);
    r.note          = char(note);
end
