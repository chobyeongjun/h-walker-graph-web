function sessionQC(folderOrFile, varargin)
% sessionQC  End-of-session data quality check.
%
%   sessionQC('/path/to/session/folder')
%   sessionQC('/path/to/260430_Robot_CBJ_TD_level_0_5_walker_high_0.csv')
%   sessionQC(folder, 'syncIdx', 1)      % check specific sync window only
%   sessionQC(folder, 'save', true)      % save PNG to folder
%
% Finds Robot / Loadcell / Motion CSVs in the same folder,
% detects sync windows in each file, and plots aligned timeseries.
%
% Console output:
%   ✓ / ✗  Sync detected, sample rate, row count, NaN fraction per file
%   Sync window count + time span
%
% Figure layout (3 rows, shared x-axis per sync window):
%   Row 1  Robot:    R_GCP  +  R_ActForce_N
%   Row 2  Loadcell: R_DesForce_N  +  R_ActForce_N  (L side if R absent)
%   Row 3  Motion:   PelvisX/Y  or first Marker column

    p = inputParser;
    addParameter(p, 'syncIdx',  0);    % 0 = show all (overlay), N = show sync N only
    addParameter(p, 'save',     false);
    addParameter(p, 'minSync',  0.5);  % minimum sync duration (s)
    parse(p, varargin{:});

    % ---- Resolve folder ---------------------------------------------------
    if isfile(folderOrFile)
        folder = fileparts(folderOrFile);
    elseif isfolder(folderOrFile)
        folder = folderOrFile;
    else
        error('sessionQC:notFound', 'Path not found: %s', folderOrFile);
    end

    % ---- Find CSVs in folder ----------------------------------------------
    files = dir(fullfile(folder, '*.csv'));
    if isempty(files)
        error('sessionQC:noCSV', 'No CSV files found in: %s', folder);
    end

    sources = struct('kind',{},'path',{},'T',{},'cycles',{},'fs',{});
    for fi = 1:numel(files)
        fp   = fullfile(folder, files(fi).name);
        kind = hwalker.io.detectSourceKind(fp);
        if strcmp(kind, 'Unknown'), continue; end
        % Keep only the first file of each kind (same session = same condition)
        already = strcmp({sources.kind}, kind);
        if any(already), continue; end
        T  = hwalker.io.loadCSV(fp);
        fs = hwalker.io.estimateSampleRate(T);
        cy = hwalker.sync.findWindows(T, p.Results.minSync);
        idx = numel(sources) + 1;
        sources(idx).kind   = kind;
        sources(idx).path   = fp;
        sources(idx).T      = T;
        sources(idx).cycles = cy;
        sources(idx).fs     = fs;
    end

    if isempty(sources)
        error('sessionQC:noKnown', 'No Robot/Loadcell/Motion CSV recognised in: %s', folder);
    end

    % ---- Console QC report ------------------------------------------------
    fprintf('\n=== Session QC: %s ===\n', folder);
    for si = 1:numel(sources)
        src  = sources(si);
        T    = src.T;
        nRow = height(T);
        nanFrac = sum(sum(ismissing(T))) / (nRow * width(T)) * 100;
        nCy  = size(src.cycles, 1);
        hasSyncCol = hasSyncSignal(T);

        syncMark = ternary(nCy > 0, '✓', '✗');
        fprintf('[%s] %s\n', syncMark, src.kind);
        fprintf('  File    : %s\n', src.path);
        fprintf('  Rows    : %d  |  %.1f Hz  |  %.1f s\n', nRow, src.fs, nRow/src.fs);
        fprintf('  NaN     : %.1f%%\n', nanFrac);
        if hasSyncCol
            fprintf('  Sync    : %d windows detected (min %.1f s)\n', nCy, p.Results.minSync);
            for ci = 1:nCy
                fprintf('    sync%d: %.2f – %.2f s  (%.2f s)\n', ci, ...
                    src.cycles(ci,1), src.cycles(ci,2), ...
                    src.cycles(ci,2) - src.cycles(ci,1));
            end
        else
            fprintf('  Sync    : no sync column found\n');
        end
        fprintf('\n');
    end

    % ---- Figure -----------------------------------------------------------
    nSrc = numel(sources);
    fig  = figure('Name', 'Session QC', 'Color', [0.12 0.12 0.16], ...
                  'Position', [100 100 1200 200+280*nSrc]);

    [~, folderName] = fileparts(folder);
    sgtitle(fig, sprintf('Session QC — %s', strrep(folderName,'_','\_')), ...
        'Color','w', 'FontSize',12, 'FontWeight','bold');

    allAx = gobjects(nSrc, 1);
    for si = 1:nSrc
        src = sources(si);
        ax  = subplot(nSrc, 1, si, 'Parent', fig);
        allAx(si) = ax;
        plotSource(ax, src, p.Results.syncIdx, si);
    end

    % Link x-axes only when all share same absolute timeline
    % (they may differ if files start at different times — don't link)

    % ---- Save -------------------------------------------------------------
    if p.Results.save
        ts  = datestr(now, 'yyyymmdd_HHMMSS');
        out = fullfile(folder, sprintf('qc_%s.png', ts));
        exportgraphics(fig, out, 'Resolution', 150);
        fprintf('QC figure saved: %s\n', out);
    end
end


% =========================================================================
%  Per-source subplot
% =========================================================================
function plotSource(ax, src, syncIdx, rowIdx)
    T     = src.T;
    t     = hwalker.io.timeAxis(T);
    cy    = src.cycles;
    kind  = src.kind;

    % Dark background
    set(ax, 'Color', [0.08 0.10 0.18], 'XColor','w', 'YColor','w', ...
        'GridColor', [0.4 0.4 0.5], 'GridAlpha', 0.3);
    grid(ax, 'on'); hold(ax, 'on');

    % Shade sync windows
    for ci = 1:size(cy, 1)
        if syncIdx > 0 && ci ~= syncIdx, continue; end
        yLim = [0 1];  % placeholder; will stretch after data is plotted
        xpatch = [cy(ci,1) cy(ci,2) cy(ci,2) cy(ci,1)];
        ypatch = [-1e6 -1e6 1e6 1e6];
        patch(ax, xpatch, ypatch, [0.0 0.5 0.3], ...
            'FaceAlpha', 0.12, 'EdgeColor', 'none');
        % Sync boundary lines
        xline(ax, cy(ci,1), '--', 'Color', [0 1 0.7 0.6], 'LineWidth', 0.8);
        xline(ax, cy(ci,2), '--', 'Color', [1 0.4 0.4 0.6], 'LineWidth', 0.8);
    end

    % Plot signals depending on source kind
    switch kind
        case 'Robot'
            plotRobot(ax, T, t);
        case 'Loadcell'
            plotLoadcell(ax, T, t);
        case 'Motion'
            plotMotion(ax, T, t);
    end

    xlabel(ax, 'Time (s)', 'Color', 'w', 'FontSize', 9);
    ylabel(ax, kind, 'Color', 'w', 'FontSize', 9);

    % Sync count badge
    nCy = size(cy, 1);
    badgeColor = ternary(nCy > 0, [0 0.85 0.6], [1 0.35 0.35]);
    syncStr = sprintf('sync: %d', nCy);
    text(ax, 0.01, 0.95, syncStr, 'Units','normalized', ...
        'Color', badgeColor, 'FontSize', 9, 'FontWeight','bold', ...
        'VerticalAlignment','top');

    % Sample rate badge
    fsStr = sprintf('%.0f Hz | %.0f s', src.fs, height(T)/src.fs);
    text(ax, 0.99, 0.95, fsStr, 'Units','normalized', ...
        'Color', [0.7 0.7 0.9], 'FontSize', 8, ...
        'HorizontalAlignment','right', 'VerticalAlignment','top');

    hold(ax, 'off');
    xlim(ax, [t(1) t(end)]);
end


% =========================================================================
%  Signal-specific plot helpers
% =========================================================================
function plotRobot(ax, T, t)
    cols = T.Properties.VariableNames;

    % GCP (heel strike sawtooth)
    for side = {'L','R'}
        gcpCol = [side{1} '_GCP'];
        if ismember(gcpCol, cols)
            sig = normalise01(double(T.(gcpCol)(:)));
            lc  = sideColor(side{1});
            plot(ax, t, sig, 'Color', [lc 0.7], 'LineWidth', 0.8, ...
                'DisplayName', gcpCol);
        end
    end

    % Actual cable force
    for side = {'L','R'}
        fCol = [side{1} '_ActForce_N'];
        if ismember(fCol, cols)
            sig = double(T.(fCol)(:));
            lc  = sideColor(side{1});
            yyaxis(ax, 'right');
            plot(ax, t, sig, 'Color', [lc 0.9], 'LineWidth', 1.2, ...
                'DisplayName', fCol);
            set(ax, 'YColor', 'w');
            yyaxis(ax, 'left');
        end
    end

    % Sync signal on top
    syncCol = getSyncCol(T);
    if ~isempty(syncCol)
        sig = normalise01(double(T.(syncCol)(:)));
        plot(ax, t, sig * 0.15, 'Color', [0 1 0.7 0.5], 'LineWidth', 1.5, ...
            'DisplayName', 'Sync');
    end

    legend(ax, 'show', 'Location','best', 'TextColor','w', ...
        'FontSize',7, 'Color',[0.1 0.1 0.2]);
end


function plotLoadcell(ax, T, t)
    cols = T.Properties.VariableNames;
    forceCols = {'L_DesForce_N','R_DesForce_N','L_ActForce_N','R_ActForce_N', ...
                 'L_Force','R_Force','Force_L','Force_R'};
    % Also accept any column containing 'force' or 'Force'
    extraF = cols(contains(lower(cols), 'force'));
    forceCols = union(forceCols, extraF, 'stable');

    plotted = 0;
    for k = 1:numel(forceCols)
        fc = forceCols{k};
        if ~ismember(fc, cols), continue; end
        sig  = double(T.(fc)(:));
        side = 'n';
        if startsWith(lower(fc),'l'), side = 'L'; end
        if startsWith(lower(fc),'r'), side = 'R'; end
        lc   = sideColor(side);
        ls   = ternary(contains(fc,'Des'), '--', '-');
        plot(ax, t, sig, 'Color', [lc 0.85], 'LineStyle', ls, ...
            'LineWidth', 1.0, 'DisplayName', fc);
        plotted = plotted + 1;
    end

    if plotted == 0
        text(ax, 0.5, 0.5, 'No force columns detected', ...
            'Units','normalized', 'Color',[0.7 0.5 0.5], ...
            'HorizontalAlignment','center');
    end

    syncCol = getSyncCol(T);
    if ~isempty(syncCol)
        sig = normalise01(double(T.(syncCol)(:)));
        yRng = ylim(ax);
        h = (yRng(2)-yRng(1)) * 0.12;
        plot(ax, t, yRng(1) + sig*h, 'Color', [0 1 0.7 0.5], ...
            'LineWidth', 1.5, 'DisplayName', 'Sync');
    end

    ylabel(ax, 'Force (N)', 'Color','w', 'FontSize',9);
    legend(ax, 'show', 'Location','best', 'TextColor','w', ...
        'FontSize',7, 'Color',[0.1 0.1 0.2]);
end


function plotMotion(ax, T, t)
    cols = T.Properties.VariableNames;

    % Prefer PelvisX/Y/Z, then any *X column, then any Marker column
    preferred = {'PelvisX','PelvisY','PelvisZ', ...
                 'RAnkleX','LAnkleX','RKneeX','LKneeX'};
    markerCols = cols(contains(cols,'Marker') | contains(cols,'marker'));
    xCols      = cols(endsWith(cols,'X') | endsWith(cols,'_x'));

    candidates = [preferred, markerCols, xCols];
    plotted    = 0;
    palette    = lines(6);
    for k = 1:numel(candidates)
        mc = candidates{k};
        if ~ismember(mc, cols), continue; end
        if plotted >= 5, break; end
        sig = double(T.(mc)(:));
        plot(ax, t, sig, 'Color', [palette(mod(plotted,6)+1,:) 0.85], ...
            'LineWidth', 0.9, 'DisplayName', strrep(mc,'_','\_'));
        plotted = plotted + 1;
    end

    if plotted == 0
        text(ax, 0.5, 0.5, 'No position columns detected', ...
            'Units','normalized', 'Color',[0.7 0.5 0.5], ...
            'HorizontalAlignment','center');
    end

    syncCol = getSyncCol(T);
    if ~isempty(syncCol)
        sig = normalise01(double(T.(syncCol)(:)));
        yRng = ylim(ax);
        h = (yRng(2)-yRng(1)) * 0.12;
        plot(ax, t, yRng(1) + sig*h, 'Color', [0 1 0.7 0.5], ...
            'LineWidth', 1.5, 'DisplayName', 'Sync');
    end

    ylabel(ax, 'Position (m)', 'Color','w', 'FontSize',9);
    legend(ax, 'show', 'Location','best', 'TextColor','w', ...
        'FontSize',7, 'Color',[0.1 0.1 0.2]);
end


% =========================================================================
%  Utilities
% =========================================================================
function col = getSyncCol(T)
    col = '';
    for c = {'Sync','A7'}
        if ismember(c{1}, T.Properties.VariableNames)
            col = c{1};
            return;
        end
    end
    for c = T.Properties.VariableNames
        lc = lower(c{1});
        if contains(lc,'sync') || contains(lc,'ttl')
            col = c{1};
            return;
        end
    end
end

function tf = hasSyncSignal(T)
    tf = ~isempty(getSyncCol(T));
end

function sig = normalise01(sig)
    lo = min(sig(isfinite(sig)));
    hi = max(sig(isfinite(sig)));
    if hi - lo < 1e-9, sig(:) = 0; return; end
    sig = (sig - lo) / (hi - lo);
end

function c = sideColor(side)
    if strcmp(side,'L')
        c = [0.48 0.75 1.0];   % cool blue
    elseif strcmp(side,'R')
        c = [1.0 0.55 0.2];    % warm orange
    else
        c = [0.7 0.7 0.7];
    end
end

function out = ternary(cond, a, b)
    if cond, out = a; else, out = b; end
end
