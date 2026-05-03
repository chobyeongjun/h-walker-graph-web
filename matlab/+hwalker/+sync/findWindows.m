function cycles = findWindows(T, varargin)
% hwalker.sync.findWindows  Find sync cycles in an H-Walker data table.
%
%   cycles = hwalker.sync.findWindows(T)
%   cycles = hwalker.sync.findWindows(T, 0.5)                          % legacy positional
%   cycles = hwalker.sync.findWindows(T, 'MinDurationS', 0.5, ...
%                                       'DebounceMs',  50, ...
%                                       'SyncColumn',  'A7')
%
% Sync cycle definition (per declarative spec in CLAUDE.md):
%   "falling edge 후 rising edge 부터 다시 falling edge 까지가 1 sync"
%   → t_start = first high sample after falling(i)
%     t_end   = t(falling(i+1))                  (half-open interval)
%
% Column search order: 'Sync' → 'A7' → any column matching /sync|ttl/ (case-insensitive).
%
% Name-value parameters:
%   'MinDurationS'  minimum valid cycle length (s).         Default 0.5
%   'DebounceMs'    boxcar debounce window (ms).            Default 50
%                   ASSUMPTION: sampling rate >= 1000/DebounceMs Hz.
%                   At 50 ms, this requires fs >= 20 Hz to resolve glitches
%                   and fs >= ~60 Hz to be effective; at lower fs, raise
%                   DebounceMs or pre-filter the signal.
%   'SyncColumn'    name of column to use (override auto-detection).
%   'Threshold'     midpoint threshold (default = (min+max)/2).
%
% Returns:
%   cycles  M x 2  [t_start, t_end] per cycle (seconds). 0x2 if none.

    cycles = zeros(0, 2);

    p = inputParser;

    % Backward compat: findWindows(T, 0.5) where 0.5 is min duration
    if numel(varargin) == 1 && isnumeric(varargin{1}) && isscalar(varargin{1})
        varargin = {'MinDurationS', varargin{1}};
    end

    addParameter(p, 'MinDurationS', 0.5,  @(x) isnumeric(x) && isscalar(x) && x >= 0);
    addParameter(p, 'DebounceMs',   50,   @(x) isnumeric(x) && isscalar(x) && x >= 0);
    addParameter(p, 'SyncColumn',   '',   @(x) ischar(x) || isstring(x));
    addParameter(p, 'Threshold',    [],   @(x) isempty(x) || (isnumeric(x) && isscalar(x)));
    parse(p, varargin{:});
    minDuration_s = p.Results.MinDurationS;
    debounceMs    = p.Results.DebounceMs;
    syncColUser   = char(p.Results.SyncColumn);
    threshUser    = p.Results.Threshold;

    % --- Find sync column ---
    syncCol = '';
    if ~isempty(syncColUser) && ismember(syncColUser, T.Properties.VariableNames)
        syncCol = syncColUser;
    else
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

    % Replace NaN with LOW to avoid phantom edges from missing samples
    sync(~isfinite(sync)) = lo;

    if isempty(threshUser)
        threshold = (lo + hi) / 2.0;
    else
        threshold = threshUser;
    end
    high = sync > threshold;

    % --- Debounce: boxcar smooth to suppress sub-DebounceMs glitches ---
    dt_t = diff(t(isfinite(t)));
    dt_t = dt_t(dt_t > 0);
    if isempty(dt_t)
        return  % cannot estimate fs
    end
    fs_est = 1 / median(dt_t);
    debounceN = max(3, round(fs_est * debounceMs / 1000));
    if debounceN > 1
        kern     = ones(debounceN, 1) / debounceN;
        smoothed = conv(double(high), kern, 'same');
        high     = smoothed > 0.5;
    end

    % --- Falling edges: diff(h)==-1 at index i means h(i+1) < h(i) ---
    h = int8(high);
    d = diff(h);
    falling = find(d == -1) + 1;  % 1-based index of the first low sample

    if numel(falling) < 2, return; end

    % --- Build cycle list ---
    n   = numel(falling) - 1;
    buf = zeros(n, 2);
    k   = 0;
    for i = 1:n
        s = falling(i);
        e = falling(i + 1);
        if e > numel(t), break; end
        % First rising edge (first high sample) in [s, e-1]
        riseSearch = find(high(s:e-1), 1, 'first');
        if isempty(riseSearch), continue; end
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
