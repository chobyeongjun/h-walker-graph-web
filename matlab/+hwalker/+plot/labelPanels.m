function h = labelPanels(fig, varargin)
% hwalker.plot.labelPanels  Add a / b / c / d labels to a multi-panel figure.
%
%   hwalker.plot.labelPanels(fig)
%   hwalker.plot.labelPanels(fig, 'Style', 'lowercase-bold')
%   hwalker.plot.labelPanels(fig, 'Preset', preset, 'Style', 'uppercase')
%   hwalker.plot.labelPanels(fig, 'Position', 'topleft', 'OffsetX', -0.08)
%
% Style:
%   'lowercase-bold'  → 'a', 'b', 'c' bold (Nature default)
%   'uppercase'       → 'A', 'B', 'C'      (IEEE default)
%   'lowercase-paren' → '(a)', '(b)', '(c)' (APA convention)
%
% Position:
%   'topleft' (default) | 'topright' | 'bottomleft' | 'bottomright'
%
% Auto-detects all child axes of the figure that contain plotted data
% (skips legend/colorbar panels). Labels are placed in normalized axes
% coordinates, with a small offset so they sit just outside the axes box.

    p = inputParser;
    addParameter(p, 'Style',    'lowercase-bold');
    addParameter(p, 'Position', 'topleft');
    addParameter(p, 'Preset',   []);
    addParameter(p, 'OffsetX',  -0.10);
    addParameter(p, 'OffsetY',   1.06);
    addParameter(p, 'FontSize',  []);
    parse(p, varargin{:});
    style    = lower(p.Results.Style);
    posname  = lower(p.Results.Position);
    preset   = p.Results.Preset;

    % Find axes (skip legends, colorbars)
    axList = findall(fig, 'Type', 'axes');
    keep = false(numel(axList), 1);
    for i = 1:numel(axList)
        tag = get(axList(i), 'Tag');
        if ~ismember(tag, {'legend','Colorbar'})
            keep(i) = true;
        end
    end
    axList = axList(keep);
    if isempty(axList)
        h = [];
        return
    end

    % Sort axes by position (top-to-bottom, then left-to-right)
    pos = zeros(numel(axList), 4);
    for i = 1:numel(axList)
        pos(i, :) = get(axList(i), 'Position');
    end
    % MATLAB's findall returns axes in reverse creation order; sort by row then col
    [~, ord] = sortrows([-pos(:,2), pos(:,1)], [1 2]);
    axList = axList(ord);

    fontName = 'Helvetica';
    fontSize = 10;
    if ~isempty(preset)
        if isfield(preset, 'font'),    fontName = preset.font;    end
        if isfield(preset, 'titlePt'), fontSize = preset.titlePt; end
    end
    if ~isempty(p.Results.FontSize), fontSize = p.Results.FontSize; end

    % Position offset
    switch posname
        case 'topleft',     xN = 0 + p.Results.OffsetX; yN = p.Results.OffsetY;
        case 'topright',    xN = 1 - p.Results.OffsetX; yN = p.Results.OffsetY;
        case 'bottomleft',  xN = 0 + p.Results.OffsetX; yN = -0.12;
        case 'bottomright', xN = 1 - p.Results.OffsetX; yN = -0.12;
        otherwise
            error('hwalker:labelPanels:badPosition', ...
                'Position must be topleft/topright/bottomleft/bottomright.');
    end

    h = gobjects(numel(axList), 1);
    for i = 1:numel(axList)
        letter = labelFor(i, style);
        weight = 'normal';
        if contains(style, 'bold'), weight = 'bold'; end
        h(i) = text(axList(i), xN, yN, letter, ...
            'Units',               'normalized', ...
            'FontName',            fontName, ...
            'FontSize',            fontSize, ...
            'FontWeight',          weight, ...
            'HorizontalAlignment', 'left', ...
            'VerticalAlignment',   'bottom', ...
            'Interpreter',         'tex');
    end
end


function s = labelFor(idx, style)
    base = char('a' + idx - 1);
    switch style
        case {'uppercase','uppercase-bold','uppercase-paren'}
            base = upper(base);
    end
    if contains(style, 'paren')
        s = sprintf('(%s)', base);
    else
        s = base;
    end
end
