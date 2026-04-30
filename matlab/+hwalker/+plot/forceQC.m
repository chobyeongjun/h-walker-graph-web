function fig = forceQC(result, side, preset)
% hwalker.plot.forceQC  Normalized force profile: Desired vs Actual ±1 SD.
%
%   hwalker.plot.forceQC(result, 'R')
%   hwalker.plot.forceQC(result, 'L', hwalker.plot.journalPreset('IEEE'))
%
% result = output of hwalker.analyzeFile (one element of struct array)

    if nargin < 3
        preset = hwalker.plot.journalPreset('IEEE');
    end

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

    fig = figure('Name', sprintf('%s Force QC — %s', side, result.label), ...
                 'Color', [0.08 0.10 0.18], 'Position', [100 100 760 420]);

    cDes = [0.48 0.75 1.0];
    cAct = [1.0  0.55 0.2];

    ax = axes(fig);
    styleAx(ax);
    hold(ax, 'on');

    x = linspace(0, 100, 101);

    if ~isempty(fp.des.mean)
        fill(ax, [x, fliplr(x)], ...
            [fp.des.mean + fp.des.std, fliplr(fp.des.mean - fp.des.std)], ...
            cDes, 'FaceAlpha', 0.15, 'EdgeColor', 'none');
        plot(ax, x, fp.des.mean, '-', 'Color', cDes, 'LineWidth', 1.8, ...
            'DisplayName', 'Desired');
    end

    if ~isempty(fp.act.mean)
        fill(ax, [x, fliplr(x)], ...
            [fp.act.mean + fp.act.std, fliplr(fp.act.mean - fp.act.std)], ...
            cAct, 'FaceAlpha', 0.15, 'EdgeColor', 'none');
        plot(ax, x, fp.act.mean, '-', 'Color', cAct, 'LineWidth', 1.8, ...
            'DisplayName', 'Actual');
    end

    infoStr = sprintf('RMSE=%.1f N  MAE=%.1f N  Peak=%.1f N', ...
        ft.rmse, ft.mae, ft.peakError);
    text(ax, 0.02, 0.97, infoStr, 'Units','normalized', ...
        'Color', [0.85 0.85 0.85], 'FontSize', 9, 'VerticalAlignment','top');

    xlabel(ax, 'Gait Cycle (%)', 'Color','w');
    ylabel(ax, 'Force (N)', 'Color','w');
    title(ax, sprintf('%s-side: Desired vs Actual  (n=%d strides)', side, sf.nStrides), ...
        'Color','w', 'FontWeight','bold');
    legend(ax, 'show', 'Location','northeast', 'TextColor','w', ...
        'Color',[0.1 0.1 0.2], 'FontSize',9);
    hold(ax, 'off');

    sgtitle(fig, strrep(result.label, '_', '\_'), ...
        'Color','w', 'FontSize',11, 'FontWeight','bold');
end

function styleAx(ax)
    set(ax, 'Color',      [0.08 0.10 0.18], ...
            'XColor',     'w', ...
            'YColor',     'w', ...
            'GridColor',  [0.35 0.35 0.45], ...
            'GridAlpha',  0.4);
    grid(ax, 'on');
end
