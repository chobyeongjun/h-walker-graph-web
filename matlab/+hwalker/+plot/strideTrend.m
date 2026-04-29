function fig = strideTrend(result, metric, preset, nCols)
% hwalker.plot.strideTrend  Stride-by-stride trend with mean line.
%
%   fig = hwalker.plot.strideTrend(result, 'strideTime')
%   fig = hwalker.plot.strideTrend(result, 'strideLength', preset, 2)
%
% metric: 'strideTime' | 'strideLength'
% Returns figure handle (Visible='off').

    if nargin < 3, preset = hwalker.plot.journalPreset('IEEE'); end
    if nargin < 4, nCols  = 1; end

    fig = figure('Visible', 'off');
    ax  = axes(fig);
    hold(ax, 'on');

    sides  = {'left', 'right'};
    labels = {'Left',  'Right'};

    for si = 1:2
        sf = sides{si};
        if ~isfield(result, sf), continue; end
        sr = result.(sf);

        switch metric
            case 'strideTime'
                y      = sr.strideTimes(:);
                yLabel = 'Stride Time (s)';
            case 'strideLength'
                if isfield(sr, 'strideLengths')
                    y = sr.strideLengths(:);
                    y = y(isfinite(y));
                else
                    continue
                end
                yLabel = 'Stride Length (m)';
            otherwise
                y      = sr.strideTimes(:);
                yLabel = 'Value';
        end

        if isempty(y), continue; end
        c = preset.colors(si, :);
        x = (1:numel(y))';

        plot(ax, x, y, 'o-', 'Color', c, ...
            'LineWidth', preset.strokePt, ...
            'MarkerSize', 3, ...
            'DisplayName', labels{si});
        yline(ax, mean(y), '--', 'Color', c, ...
            'LineWidth', preset.strokePt * 0.8, ...
            'HandleVisibility', 'off');
    end

    xlabel(ax, 'Stride Index');
    ylabel(ax, yLabel);
    title(ax, 'Stride Trend');
    legend(ax, 'Location', 'best');
    grid(ax, 'on');

    hwalker.plot.applyPreset(fig, ax, preset, nCols);
end
