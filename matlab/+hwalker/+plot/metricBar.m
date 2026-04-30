function fig = metricBar(means, stds, groupLabels, seriesLabels, metricName, preset, figNum)
% hwalker.plot.metricBar  Grouped bar chart with error bars for gait metrics.
%
%   fig = hwalker.plot.metricBar(means, stds, groupLabels, seriesLabels, ...
%             metricName, preset, figNum)
%
% INPUT
%   means       : [nGroups × nSeries] matrix, e.g., [L_pre R_pre; L_post R_post]
%   stds        : same shape as means (SD or SE; pass zeros(size(means)) if none)
%   groupLabels : cell of nGroups strings, e.g., {'Pre-training','Post-training'}
%   seriesLabels: cell of nSeries strings, e.g., {'L','R'}
%   metricName  : y-axis label string, e.g., 'Stride Time (s)'
%   preset      : journalPreset struct (from hwalker.plot.journalPreset)
%   figNum      : figure number (default 1)
%
% EXAMPLE — compare L vs R stride times pre/post:
%   preMeans  = [r_pre.left.strideTimeMean,  r_pre.right.strideTimeMean];
%   postMeans = [r_post.left.strideTimeMean, r_post.right.strideTimeMean];
%   preStds   = [r_pre.left.strideTimeStd,   r_pre.right.strideTimeStd];
%   postStds  = [r_post.left.strideTimeStd,  r_post.right.strideTimeStd];
%   preset = hwalker.plot.journalPreset('IEEE');
%   fig = hwalker.plot.metricBar( ...
%       [preMeans; postMeans], [preStds; postStds], ...
%       {'Pre','Post'}, {'L','R'}, 'Stride Time (s)', preset, 1);

    if nargin < 7, figNum = 1; end
    means = double(means);
    stds  = double(stds);

    fig = figure(figNum);
    clf(fig);

    ax = axes(fig);
    b  = bar(ax, means, 'grouped');

    % Apply series colors from preset (colors is Nx3 matrix, not cell)
    nSeries = size(means, 2);
    colors  = preset.colors;
    for si = 1:min(nSeries, size(colors, 1))
        b(si).FaceColor = colors(si, :);
        b(si).EdgeColor = 'none';
    end

    % Error bars
    hold(ax, 'on');
    nGroups = size(means, 1);
    groupW  = 0.8;  % bar group width (MATLAB default)
    seriesW = groupW / nSeries;
    offsets = seriesW * ((1:nSeries) - (nSeries+1)/2);

    for si = 1:nSeries
        xPos = (1:nGroups) + offsets(si);
        errorbar(ax, xPos, means(:,si), stds(:,si), ...
            'k', 'LineStyle', 'none', ...
            'LineWidth', preset.strokePt, ...
            'CapSize', 4);
    end
    hold(ax, 'off');

    % Labels
    ax.XTick      = 1:nGroups;
    ax.XTickLabel = groupLabels;
    ylabel(ax, metricName, 'FontName', preset.font, 'FontSize', preset.bodyPt);

    % Legend
    if numel(seriesLabels) == nSeries
        legend(ax, seriesLabels, 'Location', 'best', ...
            'FontName', preset.font, 'FontSize', preset.bodyPt - 1);
    end

    hwalker.plot.applyPreset(fig, ax, preset);
end
