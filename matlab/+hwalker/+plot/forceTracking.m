function fig = forceTracking(T, side, hsIdx, validMask, preset, nCols)
% hwalker.plot.forceTracking  Desired vs actual force with ±1SD envelope.
%
%   fig = hwalker.plot.forceTracking(T, 'L', hsIdx, validMask)
%   fig = hwalker.plot.forceTracking(T, 'L', hsIdx, validMask, preset, 2)
%
% Returns figure handle (Visible='off'). Call exportFigure to save.

    if nargin < 5, preset = hwalker.plot.journalPreset('IEEE'); end
    if nargin < 6, nCols  = 1; end

    fig = figure('Visible', 'off');
    ax  = axes(fig);
    hold(ax, 'on');

    fp = hwalker.force.normalizedProfile(T, side, hsIdx, validMask);
    x  = linspace(0, 100, 101);

    c1 = preset.colors(1,:);
    c2 = preset.colors(2,:);

    if ~isempty(fp.des.mean)
        patch(ax, [x, fliplr(x)], ...
            [fp.des.mean + fp.des.std, fliplr(fp.des.mean - fp.des.std)], ...
            c1, 'FaceAlpha', 0.15, 'EdgeColor', 'none');
        plot(ax, x, fp.des.mean, '-', 'Color', c1, ...
            'LineWidth', preset.strokePt, 'DisplayName', 'Desired');
    end

    if ~isempty(fp.act.mean)
        patch(ax, [x, fliplr(x)], ...
            [fp.act.mean + fp.act.std, fliplr(fp.act.mean - fp.act.std)], ...
            c2, 'FaceAlpha', 0.15, 'EdgeColor', 'none');
        plot(ax, x, fp.act.mean, '-', 'Color', c2, ...
            'LineWidth', preset.strokePt, 'DisplayName', 'Actual');
    end

    xlabel(ax, 'Gait Cycle (%)');
    ylabel(ax, 'Force (N)');
    title(ax, sprintf('%s Force Tracking', side));
    legend(ax, 'Location', 'best');
    grid(ax, 'on');

    hwalker.plot.applyPreset(fig, ax, preset, nCols);
end
