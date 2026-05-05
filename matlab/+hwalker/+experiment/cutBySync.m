function [Tcut, info] = cutBySync(input, varargin)
% hwalker.experiment.cutBySync  Sync-cut a single robot/loadcell file (manual).
%
%   [Tcut, info] = hwalker.experiment.cutBySync('robot_lkm_high_0.CSV')
%   [Tcut, info] = hwalker.experiment.cutBySync(T)                   % already-loaded table
%   [Tcut, info] = hwalker.experiment.cutBySync(file, 'WhichSegment', 'sync-complete', ...
%                                                       'WhichCycle', 'longest', ...
%                                                       'Plot', true, ...
%                                                       'Save', 'cut.csv')
%
% Pipeline (per CLAUDE.md sync definition: falling → rising → falling = 1 cycle):
%   1. Load CSV (or use given table)
%   2. Detect Time_ms backward jumps → contiguous segments
%   3. Pick the segment per WhichSegment (default 'sync-complete')
%   4. Detect sync cycles within that segment via hwalker.sync.findWindows
%   5. Pick the cycle per WhichCycle (default 'longest')
%   6. Slice + rebase Time_ms to start = 0
%   7. Optional: plot before/after / save to .csv
%
% Returns:
%   Tcut    table — sync-cut, time-rebased
%   info    struct .nSegmentsFound .pickedSegment .segmentDur_s
%                  .nCyclesFound   .pickedCycle    .cycleStart_s .cycleEnd_s
%                  .nSamplesIn .nSamplesOut .syncOK

    p = inputParser;
    addParameter(p, 'WhichSegment', 'sync-complete');
    addParameter(p, 'WhichCycle',   'longest');
    addParameter(p, 'MinDurationS', 0.5);
    addParameter(p, 'Plot',         false, @islogical);
    addParameter(p, 'Save',         '',    @(x) ischar(x)||isstring(x));
    parse(p, varargin{:});

    info = struct('nSegmentsFound',1,'pickedSegment',1,'segmentDur_s',NaN, ...
                  'nCyclesFound',0,'pickedCycle',[],'cycleStart_s',NaN, ...
                  'cycleEnd_s',NaN,'nSamplesIn',NaN,'nSamplesOut',0, 'syncOK',false);

    % ---- 1. Load ----
    if istable(input)
        T = input;  src = '<table>';
    else
        src = char(input);
        T = hwalker.io.loadCSV(src);
    end
    info.nSamplesIn = height(T);
    fprintf('=== cutBySync: %s ===\n', src);
    fprintf('  rows in: %d\n', info.nSamplesIn);

    % ---- 2-3. Multi-segment ----
    [T, segInfo] = hwalker.experiment.pickSegment(T, p.Results.WhichSegment);
    info.nSegmentsFound = segInfo.nSegments;
    info.pickedSegment  = segInfo.picked;
    info.segmentDur_s   = segInfo.dur_s;

    % ---- 4-5. Sync cycle within picked segment ----
    cycles = hwalker.sync.findWindows(T, 'MinDurationS', p.Results.MinDurationS);
    info.nCyclesFound = size(cycles, 1);
    if info.nCyclesFound == 0
        warning('hwalker:cutBySync:noCycle', 'No sync cycle found in selected segment.');
        Tcut = T;
        info.nSamplesOut = height(Tcut);
        return
    end

    % Pick cycle
    if isnumeric(p.Results.WhichCycle)
        idx = max(min(round(p.Results.WhichCycle), info.nCyclesFound), 1);
    else
        durs = cycles(:,2) - cycles(:,1);
        switch lower(p.Results.WhichCycle)
            case 'longest', [~, idx] = max(durs);
            case 'first',   idx = 1;
            otherwise,      idx = 1;
        end
    end
    cs = cycles(idx, 1);  ce = cycles(idx, 2);
    info.pickedCycle  = idx;
    info.cycleStart_s = cs;
    info.cycleEnd_s   = ce;
    fprintf('  cycle picked: %.3f-%.3f s (%.3f s) [%d/%d]\n', cs, ce, ce-cs, idx, info.nCyclesFound);

    % ---- 6. Slice + rebase ----
    t = hwalker.io.timeAxis(T);
    mask = t >= cs & t < ce;
    Tcut = T(mask, :);
    if ismember('Time_ms', Tcut.Properties.VariableNames) && ~isempty(Tcut.Time_ms)
        Tcut.Time_ms = Tcut.Time_ms - Tcut.Time_ms(1);
    elseif ismember('timestamp_ms', Tcut.Properties.VariableNames) && ~isempty(Tcut.timestamp_ms)
        Tcut.timestamp_ms = Tcut.timestamp_ms - Tcut.timestamp_ms(1);
    end
    info.nSamplesOut = height(Tcut);
    info.syncOK      = info.nSamplesOut > 0;
    fprintf('  rows out: %d  (%.3f s @ ~%.1f Hz)\n', ...
        info.nSamplesOut, (ce-cs), info.nSamplesOut/(ce-cs));

    % ---- 7. Optional plot ----
    if p.Results.Plot
        plotCutPreview(T, Tcut, cs, ce, src);
    end

    % ---- 7b. Optional save ----
    if ~isempty(char(p.Results.Save))
        out = char(p.Results.Save);
        writetable(Tcut, out);
        fprintf('  saved → %s\n', out);
    end
end


% =====================================================================
function plotCutPreview(Traw, Tcut, cs, ce, label)
    t = hwalker.io.timeAxis(Traw);
    figure('Color','w','Name', sprintf('cutBySync — %s', label));
    syncCol = '';
    for c = {'A7','Sync','a7','sync'}
        if ismember(c{1}, Traw.Properties.VariableNames), syncCol = c{1}; break; end
    end

    nRow = 2 + double(any(ismember({'L_DesForce_N','R_DesForce_N'}, Traw.Properties.VariableNames)));

    % Sync signal
    if ~isempty(syncCol)
        ax = subplot(nRow, 1, 1);
        plot(t, double(Traw.(syncCol)), 'Color', [0.4 0.4 0.4]);
        hold on;
        ylim_ = ylim;
        patch([cs ce ce cs], [ylim_(1) ylim_(1) ylim_(2) ylim_(2)], ...
            [0 0.8 0.4], 'FaceAlpha', 0.15, 'EdgeColor','none');
        xline(cs, 'g-', 'LineWidth', 1.2, 'Label', 'rising');
        xline(ce, 'r-', 'LineWidth', 1.2, 'Label', 'falling');
        ylabel(syncCol);
        title(sprintf('Sync signal — cut window [%.2f, %.2f] s (dur %.2fs)', cs, ce, ce-cs));
        grid on
    end

    % Force tracking (raw)
    if any(ismember({'R_DesForce_N','L_DesForce_N'}, Traw.Properties.VariableNames))
        subplot(nRow, 1, 2);
        if ismember('R_DesForce_N', Traw.Properties.VariableNames)
            plot(t, Traw.R_DesForce_N, 'Color', [0 0.45 0.74], 'LineStyle','--'); hold on
            plot(t, Traw.R_ActForce_N, 'Color', [0 0.45 0.74]);
        end
        if ismember('L_DesForce_N', Traw.Properties.VariableNames)
            plot(t, Traw.L_DesForce_N, 'Color', [0.85 0.32 0.10], 'LineStyle','--');
            plot(t, Traw.L_ActForce_N, 'Color', [0.85 0.32 0.10]);
        end
        ylim_ = ylim;
        patch([cs ce ce cs], [ylim_(1) ylim_(1) ylim_(2) ylim_(2)], ...
            [0 0.8 0.4], 'FaceAlpha', 0.10, 'EdgeColor','none');
        ylabel('Force (N)'); legend({'R_des','R_act','L_des','L_act'}, 'Location','best');
        title('Raw timeline (cut region shaded green)');
        grid on
    end

    % Cut result
    ax = subplot(nRow, 1, nRow);
    if ismember('Time_ms', Tcut.Properties.VariableNames)
        tc = double(Tcut.Time_ms) / 1000;
    else
        tc = (0:height(Tcut)-1)' / 111;
    end
    if ismember('R_ActForce_N', Tcut.Properties.VariableNames)
        plot(tc, Tcut.R_ActForce_N, 'Color', [0 0.45 0.74]); hold on
        plot(tc, Tcut.R_DesForce_N, '--', 'Color', [0 0.45 0.74]);
    end
    xlabel('time (s, rebased)'); ylabel('R Force (N)');
    title(sprintf('Cut result — %d samples', height(Tcut)));
    grid on
end
