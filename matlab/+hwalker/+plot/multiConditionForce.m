function fig = multiConditionForce(profiles, condLabels, side, preset, figNum)
% hwalker.plot.multiConditionForce  Overlaid GCP-normalized force profiles.
%
%   fig = hwalker.plot.multiConditionForce(profiles, condLabels, 'L', preset, 3)
%
% INPUT
%   profiles   : cell array of profile structs from hwalker.force.normalizedProfile
%                e.g., {r_pre.leftProfile, r_post.leftProfile, r_walk.leftProfile}
%   condLabels : cell of condition name strings, same length as profiles
%   side       : 'L' or 'R' (for axis label only)
%   preset     : journalPreset struct
%   figNum     : figure number (default 1)
%
% Plots mean ±1 SD envelope for each condition with distinct colors.
%
% EXAMPLE:
%   preset = hwalker.plot.journalPreset('JNER');
%   fig = hwalker.plot.multiConditionForce( ...
%       {r1.leftProfile, r2.leftProfile}, {'Slow', 'Fast'}, 'L', preset, 3);
%   hwalker.plot.exportFigure(fig, 'Fig3_force_conditions.pdf', preset);

    if nargin < 5, figNum = 1; end

    x = linspace(0, 100, 101);  % GCP-normalized 0–100%

    fig = figure(figNum);
    clf(fig);
    ax = axes(fig);
    hold(ax, 'on');

    colors = preset.colors;
    nCond  = numel(profiles);

    for ci = 1:nCond
        fp  = profiles{ci};
        clr = colors{mod(ci-1, numel(colors)) + 1};

        if isempty(fp.act.mean), continue; end

        m = fp.act.mean(:)';
        s = fp.act.std(:)';

        % ±1 SD shaded envelope
        patch(ax, [x, fliplr(x)], [m+s, fliplr(m-s)], clr, ...
            'FaceAlpha', 0.18, 'EdgeColor', 'none');

        % Mean line
        plot(ax, x, m, '-', 'Color', clr, ...
            'LineWidth', preset.strokePt * 1.5, ...
            'DisplayName', condLabels{ci});
    end

    hold(ax, 'off');

    xlabel(ax, 'Gait Cycle (%)', 'FontName', preset.font, 'FontSize', preset.bodyPt);
    ylabel(ax, sprintf('%s Force (N)', side), ...
        'FontName', preset.font, 'FontSize', preset.bodyPt);
    legend(ax, 'Location', 'best', 'FontName', preset.font, 'FontSize', preset.bodyPt - 1);

    hwalker.plot.applyPreset(fig, preset);
end
