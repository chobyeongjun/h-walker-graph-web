function applyPreset(fig, ax, preset, nCols)
% hwalker.plot.applyPreset  Apply journal preset to a figure + axes pair.
%
%   hwalker.plot.applyPreset(gcf, gca, preset)         % default 1-col
%   hwalker.plot.applyPreset(gcf, gca, preset, 1)      % 1-column
%   hwalker.plot.applyPreset(gcf, gca, preset, 2)      % 2-column
%   hwalker.plot.applyPreset(gcf, gca, preset, 1.5)    % 1.5-col (Elsevier)
%
% Sets exact journal width × height (mm), font family, body / axis / legend
% / title sizes (pt), stroke width, axes-spine width, grid width, color order,
% text interpreter, and tick style.
%
% Throws hwalker:plot:noOneHalf if nCols=1.5 is requested for a journal
% without a 1.5-column variant (only Elsevier supports it).

    if nargin < 4, nCols = 1; end

    [widthIn, heightIn] = pickSize(preset, nCols);

    % --- Figure dimensions (exact journal mm × mm) ---
    set(fig, ...
        'Color',         hex2rgb01(preset.bg), ...
        'Units',         'inches', ...
        'Position',      [1 1 widthIn heightIn], ...
        'PaperUnits',    'inches', ...
        'PaperSize',     [widthIn heightIn], ...
        'PaperPosition', [0 0 widthIn heightIn], ...
        'InvertHardcopy', 'off');

    % --- Axes typography + spines + ticks ---
    set(ax, ...
        'FontName',     preset.font, ...
        'FontSize',     preset.axisPt, ...
        'LineWidth',    preset.axesPt, ...    % spine width (fixed across journals)
        'TickDir',      'out', ...
        'TickLength',   [0.012, 0.025], ...   % conservative for small figures
        'Box',          'off', ...
        'XColor',       hex2rgb01(preset.axisColor), ...
        'YColor',       hex2rgb01(preset.axisColor), ...
        'GridLineStyle','-', ...
        'GridColor',    hex2rgb01(preset.gridColor), ...
        'GridAlpha',    1.0, ...
        'MinorGridAlpha', 0.0, ...
        'Layer',        'top');

    % MATLAB has no public "grid line width" property prior to R2023a;
    % we set the axes line width to a journal-uniform 0.6pt and rely on
    % `preset.gridPt` for downstream consumers (e.g. metricBar's helper grid).

    % --- Apply line width to all existing line objects ---
    lines = findobj(ax, 'Type', 'line');
    if ~isempty(lines)
        set(lines, 'LineWidth', preset.strokePt);
    end

    % --- Labels / title font + body size + interpreter ---
    interp = preset.interpreter;
    if ~isempty(get(ax,'Title'))
        set(get(ax,'Title'), ...
            'FontName',    preset.font, ...
            'FontSize',    preset.titlePt, ...
            'Interpreter', interp);
    end
    if ~isempty(get(ax,'XLabel'))
        set(get(ax,'XLabel'), ...
            'FontName',    preset.font, ...
            'FontSize',    preset.bodyPt, ...
            'Interpreter', interp);
    end
    if ~isempty(get(ax,'YLabel'))
        set(get(ax,'YLabel'), ...
            'FontName',    preset.font, ...
            'FontSize',    preset.bodyPt, ...
            'Interpreter', interp);
    end

    % --- Legend (if attached) ---
    lg = findobj(fig, 'Type', 'Legend');
    if ~isempty(lg)
        set(lg, ...
            'FontName',    preset.font, ...
            'FontSize',    preset.legendPt, ...
            'Box',         'off', ...
            'Interpreter', interp);
    end

    % --- All text objects in the axes use the journal font + interpreter ---
    txt = findobj(ax, 'Type', 'text');
    if ~isempty(txt)
        set(txt, 'FontName', preset.font, 'Interpreter', interp);
    end

    % --- Color order for new plot commands ---
    set(ax, 'ColorOrder', preset.palette, 'NextPlot', 'replacechildren');
end


% ====================================================================
%  Helpers
% ====================================================================
function [widthIn, heightIn] = pickSize(preset, nCols)
    if abs(nCols - 1) < 1e-9
        widthIn  = preset.col1in;
        heightIn = preset.col1h_in;
    elseif abs(nCols - 2) < 1e-9
        widthIn  = preset.col2in;
        heightIn = preset.col2h_in;
    elseif abs(nCols - 1.5) < 1e-9
        if ~isfinite(preset.col15in)
            error('hwalker:plot:noOneHalf', ...
                'Preset ''%s'' has no 1.5-column variant. Use 1 or 2.', ...
                preset.name);
        end
        widthIn  = preset.col15in;
        heightIn = preset.col15h_in;
    else
        error('hwalker:plot:badColumnCount', ...
            'nCols must be 1, 1.5, or 2; got %g', nCols);
    end
end


function rgb = hex2rgb01(hex)
% Convert '#RRGGBB' string to a 1×3 RGB vector in [0,1].
    hex = char(hex);
    if hex(1) == '#', hex = hex(2:end); end
    if numel(hex) ~= 6
        rgb = [1 1 1];
        return
    end
    r = sscanf(hex(1:2), '%x') / 255;
    g = sscanf(hex(3:4), '%x') / 255;
    b = sscanf(hex(5:6), '%x') / 255;
    rgb = [r, g, b];
end
