function applyPreset(fig, ax, preset, nCols)
% hwalker.plot.applyPreset  Apply journal preset to figure and axes.
%
%   hwalker.plot.applyPreset(gcf, gca, preset, 1)   % 1-column
%   hwalker.plot.applyPreset(gcf, gca, preset, 2)   % 2-column

    if nargin < 4, nCols = 1; end

    widthIn  = preset.(['col' num2str(nCols) 'in']);
    heightIn = widthIn * 0.75;   % 4:3 default aspect ratio

    % Figure dimensions
    set(fig, 'Units', 'inches', ...
        'Position',      [1 1 widthIn heightIn], ...
        'PaperUnits',    'inches', ...
        'PaperSize',     [widthIn heightIn], ...
        'PaperPosition', [0 0 widthIn heightIn]);

    % Axes typography and tick style
    set(ax, 'FontName', preset.font, ...
        'FontSize',  preset.bodyPt, ...
        'LineWidth', preset.strokePt * 0.5, ...
        'TickDir',   'out', ...
        'Box',       'off');

    % Apply line widths to all existing lines
    lines = findobj(ax, 'Type', 'line');
    if ~isempty(lines)
        set(lines, 'LineWidth', preset.strokePt);
    end

    % Labels / title font
    for hObj = {get(ax,'Title'), get(ax,'XLabel'), get(ax,'YLabel')}
        if ~isempty(hObj{1})
            set(hObj{1}, 'FontName', preset.font, 'FontSize', preset.bodyPt);
        end
    end

    % Color order for new plot commands
    set(ax, 'ColorOrder',  preset.colors, ...
        'NextPlot', 'replacechildren');
end
