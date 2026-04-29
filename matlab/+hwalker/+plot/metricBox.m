function fig = metricBox(data, labels, metricName, preset, figNum)
% hwalker.plot.metricBox  Boxplot comparison of gait metrics across conditions.
%
%   fig = hwalker.plot.metricBox(data, labels, metricName, preset, figNum)
%
% INPUT
%   data        : cell array of vectors, one per group/condition
%                 e.g., {preStrideTimes, postStrideTimes}
%   labels      : cell of strings matching data length, e.g., {'Pre','Post'}
%   metricName  : y-axis label, e.g., 'Stride Time (s)'
%   preset      : journalPreset struct
%   figNum      : figure number (default 1)
%
% EXAMPLE — compare stride times before/after training:
%   preT  = r_pre.left.strideTimes;
%   postT = r_post.left.strideTimes;
%   preset = hwalker.plot.journalPreset('Nature');
%   fig = hwalker.plot.metricBox({preT(isfinite(preT)), postT(isfinite(postT))}, ...
%       {'Pre','Post'}, 'Stride Time (s)', preset, 2);

    if nargin < 5, figNum = 1; end

    fig = figure(figNum);
    clf(fig);
    ax = axes(fig);

    nGroups = numel(data);
    colors  = preset.colors;

    % Build combined vector + group index for boxplot
    allVals = [];
    grpIdx  = [];
    for g = 1:nGroups
        v = data{g}(:);
        v = v(isfinite(v));
        allVals = [allVals; v];           %#ok<AGROW>
        grpIdx  = [grpIdx;  repmat(g, numel(v), 1)]; %#ok<AGROW>
    end

    % Use boxchart (R2020b+) with fallback to boxplot
    if exist('boxchart', 'file') || exist('boxchart', 'builtin')
        bc = boxchart(ax, grpIdx, allVals);
        bc.BoxFaceColor  = colors{1};
        bc.MarkerColor   = colors{1};
        bc.LineWidth     = preset.strokePt;
        ax.XTick      = 1:nGroups;
        ax.XTickLabel = labels;
    else
        boxplot(allVals, grpIdx, 'Labels', labels, ...
            'Parent', ax, 'Widths', 0.5);
    end

    ylabel(ax, metricName, 'FontName', preset.font, 'FontSize', preset.bodyPt);

    hwalker.plot.applyPreset(fig, preset);
end
