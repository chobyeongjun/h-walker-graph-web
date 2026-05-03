function h = drawSignificance(ax, x1, x2, yTop, pVal, varargin)
% hwalker.plot.drawSignificance  Draw a significance bracket above two groups.
%
%   hwalker.plot.drawSignificance(ax, 1, 2, yTop, p)
%   hwalker.plot.drawSignificance(ax, x1, x2, yTop, p, 'Style', 'asterisk')
%   hwalker.plot.drawSignificance(ax, x1, x2, yTop, p, 'Style', 'pvalue', ...
%                                  'Preset', preset, 'Color', 'k')
%
% Draws a bracket --|---|-- between two x positions at height yTop, then
% places a label above. Style 'asterisk' uses *, **, ***, or ns (default).
% Style 'pvalue' prints the literal p-value (e.g. "p=0.034").
%
% Optional name-value parameters:
%   'Style'     'asterisk' (default) | 'pvalue'
%   'Preset'    journal preset struct → uses preset.font / fontPt / strokePt
%   'Color'     line + text color (default 'k' or preset.axisColor)
%   'TextOffsetFrac'  vertical offset of label above bracket, as fraction of
%                     axes y-range (default 0.02)
%   'StemFrac'        bracket stem (downward tick) length fraction (default 0.015)
%   'AlphaThresholds' [a3 a2 a1] cutoffs for ***/**/* (default [.001 .01 .05])
%
% Returns struct h with handles: .bracket (line), .label (text).
%
% Reference: standard biomechanics figure annotation convention.

    p = inputParser;
    addParameter(p, 'Style',           'asterisk');
    addParameter(p, 'Preset',          []);
    addParameter(p, 'Color',           []);
    addParameter(p, 'TextOffsetFrac',  0.02);
    addParameter(p, 'StemFrac',        0.015);
    addParameter(p, 'AlphaThresholds', [0.001, 0.01, 0.05]);
    parse(p, varargin{:});

    style    = lower(p.Results.Style);
    preset   = p.Results.Preset;
    color    = p.Results.Color;
    textFrac = p.Results.TextOffsetFrac;
    stemFrac = p.Results.StemFrac;
    cuts     = sort(p.Results.AlphaThresholds);     % [a3 a2 a1]

    if isempty(color)
        if ~isempty(preset) && isfield(preset, 'axisColor')
            color = preset.axisColor;
            if ischar(color) && color(1) == '#'
                color = hex2rgb01(color);
            end
        else
            color = [0 0 0];
        end
    end

    yLim = ylim(ax);
    yRange = diff(yLim);
    stem  = stemFrac * yRange;
    yLab  = yTop + textFrac * yRange;

    % Bracket: horizontal line + two short stems pointing DOWN
    holdState = ishold(ax);
    hold(ax, 'on');
    bx = [x1, x1, x2, x2];
    by = [yTop - stem, yTop, yTop, yTop - stem];

    lineW = 0.6;
    fontPt = 8;
    fontName = 'Helvetica';
    if ~isempty(preset)
        if isfield(preset, 'strokePt'), lineW   = preset.strokePt; end
        if isfield(preset, 'bodyPt'),   fontPt  = preset.bodyPt;   end
        if isfield(preset, 'font'),     fontName = preset.font;    end
    end

    h.bracket = plot(ax, bx, by, '-', 'Color', color, ...
        'LineWidth', lineW, 'HandleVisibility', 'off');

    label = formatLabel(pVal, style, cuts);
    h.label = text(ax, (x1 + x2)/2, yLab, label, ...
        'HorizontalAlignment', 'center', ...
        'VerticalAlignment',   'bottom', ...
        'Color',               color, ...
        'FontName',            fontName, ...
        'FontSize',            fontPt, ...
        'Interpreter',         'tex');

    if ~holdState, hold(ax, 'off'); end

    % Auto-extend y-axis if the label would overflow
    if yLab + 0.04 * yRange > yLim(2)
        ylim(ax, [yLim(1), yLab + 0.06 * yRange]);
    end
end


% ====================================================================
function s = formatLabel(p, style, cuts)
    if ~isfinite(p)
        s = '';
        return
    end
    if strcmp(style, 'pvalue')
        if p < 0.001
            s = 'p<0.001';
        else
            s = sprintf('p=%.3f', p);
        end
        return
    end
    % asterisk style
    if p < cuts(1)
        s = '***';
    elseif p < cuts(2)
        s = '**';
    elseif p < cuts(3)
        s = '*';
    else
        s = 'ns';
    end
end

function rgb = hex2rgb01(hex)
    hex = char(hex);
    if hex(1) == '#', hex = hex(2:end); end
    if numel(hex) ~= 6, rgb = [0 0 0]; return; end
    rgb = [sscanf(hex(1:2), '%x'), sscanf(hex(3:4), '%x'), ...
           sscanf(hex(5:6), '%x')] / 255;
end
