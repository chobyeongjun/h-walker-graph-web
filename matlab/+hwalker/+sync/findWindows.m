function cycles = findWindows(T, minDuration_s)
% hwalker.sync.findWindows  Find sync cycles in an H-Walker data table.
%
%   cycles = hwalker.sync.findWindows(T)
%   cycles = hwalker.sync.findWindows(T, 0.5)  % ignore cycles < 0.5 s
%
% Sync cycle definition (per declarative spec in CLAUDE.md):
%   "falling edge 후 rising edge 부터 다시 falling edge 까지가 1 sync"
%   → [first-low-sample, next-falling-edge) in time.
%
% Column search order: 'Sync' → 'A7' → any column containing 'sync'/'ttl'.
%
% Returns Mx2 array of [t_start, t_end] in seconds.
% Returns 0×2 empty when no Sync column or no complete cycles found.

    if nargin < 2, minDuration_s = 0.5; end

    cycles = zeros(0, 2);

    % --- Find sync column ---
    syncCol = '';
    for candidate = {'Sync','A7'}
        if ismember(candidate{1}, T.Properties.VariableNames)
            syncCol = candidate{1};
            break
        end
    end
    if isempty(syncCol)
        colNames = T.Properties.VariableNames;
        for k = 1:numel(colNames)
            lc = lower(colNames{k});
            if contains(lc,'sync') || contains(lc,'ttl')
                syncCol = colNames{k};
                break
            end
        end
    end
    if isempty(syncCol), return; end

    % --- Time axis and signal ---
    t    = hwalker.io.timeAxis(T);
    sync = double(T.(syncCol)(:));

    valid = isfinite(sync);
    if sum(valid) < 4, return; end

    lo = min(sync(valid));
    hi = max(sync(valid));
    if hi - lo < 1e-9, return; end  % constant signal → no cycles

    threshold = (lo + hi) / 2.0;
    high = sync > threshold;

    % Falling edges: diff(h)==-1 at index i means h(i+1) < h(i)
    % → first low sample is at index i+1 (1-based)
    h = int8(high);
    d = diff(h);
    falling = find(d == -1) + 1;  % 1-based index of the first low sample

    if numel(falling) < 2, return; end

    % Build cycle list
    % Spec: "falling edge 후 rising edge 부터 다시 falling edge 까지가 1 sync"
    % → t_start = first high sample after falling(i), t_end = t(falling(i+1))
    n = numel(falling) - 1;
    buf = zeros(n, 2);
    k = 0;
    for i = 1:n
        s = falling(i);
        e = falling(i + 1);
        % Find the first rising edge (first high sample) in [s, e-1]
        riseSearch = find(high(s:e-1), 1, 'first');
        if isempty(riseSearch), continue; end  % no rising edge → skip
        riseIdx = s + riseSearch - 1;
        t_start = t(riseIdx);
        dur = t(e) - t_start;
        if dur >= minDuration_s
            k = k + 1;
            buf(k, :) = [t_start, t(e)];
        end
    end
    cycles = buf(1:k, :);
end
