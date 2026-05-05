function [Tout, info] = pickSegment(T, which)
% hwalker.experiment.pickSegment  Multi-segment detection and selection.
%
%   [Tout, info] = hwalker.experiment.pickSegment(T)
%   [Tout, info] = hwalker.experiment.pickSegment(T, 'sync-complete')
%   [Tout, info] = hwalker.experiment.pickSegment(T, 'last' | 'first' | 'longest' | N)
%
% Detects backward jumps in `Time_ms` (or `timestamp_ms`) — these
% indicate Teensy reset or record stop+start that concatenated several
% trials into a single CSV — and returns only one segment.
%
% Selection rules:
%   'sync-complete' (default) — longest segment whose A7 column has at
%                                 least one rising edge followed by a
%                                 falling edge (i.e. a real assist cycle)
%   'last'    — last segment in the file
%   'first'   — first segment
%   'longest' — longest by duration
%   integer N — that segment index (1-based)
%
% Info struct:
%   .nSegments     total segments found
%   .picked        index used (1..nSegments)
%   .dur_s         duration of picked segment
%   .durs_s        all segment durations
%   .syncOK        per-segment vector of complete-sync flags
%   .startRow / .endRow   rows in original T that bound the picked segment

    if nargin < 2 || isempty(which), which = 'sync-complete'; end

    % Find time column
    timeCol = '';
    for c = {'Time_ms', 'timestamp_ms', 'time_ms'}
        if ismember(c{1}, T.Properties.VariableNames), timeCol = c{1}; break; end
    end

    info = struct('nSegments', 1, 'picked', 1, 'dur_s', NaN, 'durs_s', NaN, ...
                  'syncOK', false, 'startRow', 1, 'endRow', height(T));

    if isempty(timeCol)
        Tout = T;  return
    end

    tm = double(T.(timeCol));
    dt = diff(tm);
    backJump = find(dt < -1000);
    if isempty(backJump)
        info.dur_s = (tm(end) - tm(1)) / 1000;
        info.durs_s = info.dur_s;
        info.syncOK = checkSync(T, 1, height(T));
        Tout = T;  return
    end

    bounds = [0; backJump; height(T)];
    nSeg = numel(bounds) - 1;
    durs = zeros(nSeg, 1);
    syncOK = false(nSeg, 1);
    sIdx = zeros(nSeg, 1);  eIdx = zeros(nSeg, 1);
    for i = 1:nSeg
        sIdx(i) = bounds(i) + 1;
        eIdx(i) = bounds(i+1);
        durs(i) = (tm(eIdx(i)) - tm(sIdx(i))) / 1000;
        syncOK(i) = checkSync(T, sIdx(i), eIdx(i));
    end

    if isnumeric(which)
        pick = max(min(round(which), nSeg), 1);
    else
        switch lower(which)
            case 'sync-complete'
                if any(syncOK)
                    cand = find(syncOK);
                    [~, j] = max(durs(cand));
                    pick = cand(j);
                else
                    [~, pick] = max(durs);
                end
            case 'last',     pick = nSeg;
            case 'first',    pick = 1;
            case 'longest',  [~, pick] = max(durs);
            otherwise,       pick = nSeg;
        end
    end

    Tout = T(sIdx(pick):eIdx(pick), :);
    info.nSegments = nSeg;
    info.picked    = pick;
    info.dur_s     = durs(pick);
    info.durs_s    = durs;
    info.syncOK    = syncOK;
    info.startRow  = sIdx(pick);
    info.endRow    = eIdx(pick);

    % Console summary
    syncMark = arrayfun(@(b) ternary(b,'✓','×'), syncOK, 'UniformOutput', false);
    durStr = strjoin(arrayfun(@(i) sprintf('%ds%s', round(durs(i)), syncMark{i}), ...
        1:nSeg, 'UniformOutput', false), ', ');
    fprintf('  pickSegment: %d segs [%s] → seg %d (%.1fs)\n', nSeg, durStr, pick, durs(pick));
end


function ok = checkSync(T, s, e)
    ok = false;
    if ~ismember('A7', T.Properties.VariableNames), return; end
    seg = double(T.A7(s:e));
    fin = isfinite(seg);
    if ~any(fin) || max(seg(fin)) - min(seg(fin)) < 1, return; end
    thr = (min(seg(fin)) + max(seg(fin))) / 2;
    hi = seg > thr;
    d = diff(int8(hi));
    rs = find(d == 1);  fl = find(d == -1);
    if ~isempty(rs) && ~isempty(fl) && any(fl > rs(1))
        ok = true;
    end
end


function v = ternary(cond, a, b)
    if cond, v = a; else, v = b; end
end
