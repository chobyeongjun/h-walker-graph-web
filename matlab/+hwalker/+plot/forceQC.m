function fig = forceQC(result, side, journal)
% hwalker.plot.forceQC  Normalized force profile — Desired vs Actual ±1 SD.
%
%   hwalker.plot.forceQC(result, 'R')
%   hwalker.plot.forceQC(result, 'R', 'TRO')        % IEEE Trans on Robotics
%   hwalker.plot.forceQC(result, 'L', 'JNER')       % rehab journal
%   % journal: 'TRO'|'RAL'|'TNSRE'|'TMECH'|'ICRA'|'IROS'|'IJRR'|
%   %          'SciRobotics'|'SoftRobotics'|'FrontNeurorobot'|'AuRo'|
%   %          'IEEE'|'Nature'|'APA'|'Elsevier'|'MDPI'|'JNER'
%
% Inputs:
%   result : single element from hwalker.analyzeFile output (e.g., results(1))
%   side   : 'L' | 'R' (case-insensitive, only first letter matters)
%   journal: any preset name (default 'JNER')
%
% Returns:
%   fig    : figure handle (Visible='on'). Pass to hwalker.plot.exportFigure.
%
% Example — full pipeline:
%   results = hwalker.analyzeFile('mydata.csv');
%   fig     = hwalker.plot.forceQC(results(1), 'R', 'TRO');
%   preset  = hwalker.plot.journalPreset('TRO');
%   hwalker.plot.exportFigure(fig, 'Fig1.pdf', preset);

    if nargin < 3, journal = 'JNER'; end
    preset = hwalker.plot.journalPreset(journal);

    side = upper(side(1));
    if strcmp(side, 'L')
        fp = result.leftProfile;
        ft = result.leftForce;
        sf = result.left;
    else
        fp = result.rightProfile;
        ft = result.rightForce;
        sf = result.right;
    end

    % Wong palette: blue = desired, orange = actual
    cDes = preset.colors(1,:);
    cAct = preset.colors(2,:);

    fig = figure('Color', 'w', 'Visible', 'on');
    ax  = axes(fig);
    hold(ax, 'on');

    x = linspace(0, 100, 101);

    % ---- Desired ±1 SD ----
    if ~isempty(fp.des.mean)
        fill(ax, [x, fliplr(x)], ...
            [fp.des.mean + fp.des.std, fliplr(fp.des.mean - fp.des.std)], ...
            cDes, 'FaceAlpha', 0.20, 'EdgeColor', 'none', 'HandleVisibility', 'off');
        plot(ax, x, fp.des.mean, '-', 'Color', cDes, ...
            'LineWidth', preset.strokePt, 'DisplayName', 'Desired Force');
    end

    % ---- Actual ±1 SD ----
    if ~isempty(fp.act.mean)
        fill(ax, [x, fliplr(x)], ...
            [fp.act.mean + fp.act.std, fliplr(fp.act.mean - fp.act.std)], ...
            cAct, 'FaceAlpha', 0.20, 'EdgeColor', 'none', 'HandleVisibility', 'off');
        plot(ax, x, fp.act.mean, '-', 'Color', cAct, ...
            'LineWidth', preset.strokePt, 'DisplayName', 'Actual Force');
    end

    % ---- Axes labels ----
    xlabel(ax, 'Gait Cycle (%)');
    ylabel(ax, 'Force (N)');
    title(ax, sprintf('%s-side Force Tracking  (n=%d strides,  RMSE=%.1f N)', ...
        side, sf.nStrides, ft.rmse));
    legend(ax, 'show', 'Location', 'northeast');
    grid(ax, 'on');
    box(ax, 'off');
    xlim(ax, [0 100]);

    hwalker.plot.applyPreset(fig, ax, preset, 1);
end
