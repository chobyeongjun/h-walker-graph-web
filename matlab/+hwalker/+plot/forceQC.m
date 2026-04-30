function fig = forceQC(result, side, preset)
% hwalker.plot.forceQC  Force tracking quick-look: profile + per-stride error.
%
%   hwalker.plot.forceQC(result, 'R')
%   hwalker.plot.forceQC(result, 'L', hwalker.plot.journalPreset('IEEE'))
%
% Two-panel figure:
%   Top    : Normalized force profile (Desired vs Actual ±1 SD)
%   Bottom : Per-stride RMSE and MAE bar chart
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
                 'Color', [0.08 0.10 0.18], 'Position', [100 100 860 560]);

    % ---- Palette -----------------------------------------------------------
    cDes = [0.48 0.75 1.0];   % blue  = desired
    cAct = [1.0  0.55 0.2];   % orange = actual
    cErr = [0.95 0.35 0.35];  % red   = error

    % ========================================================================
    % Panel 1: Normalized force profile
    % ========================================================================
    ax1 = subplot(2, 1, 1);
    styleAx(ax1);
    hold(ax1, 'on');

    x = linspace(0, 100, 101);

    % Desired ±1 SD band
    if ~isempty(fp.des.mean)
        fill(ax1, [x, fliplr(x)], ...
            [fp.des.mean + fp.des.std, fliplr(fp.des.mean - fp.des.std)], ...
            cDes, 'FaceAlpha', 0.15, 'EdgeColor', 'none');
        plot(ax1, x, fp.des.mean, '-', 'Color', cDes, 'LineWidth', 1.5, ...
            'DisplayName', 'Desired');
    end

    % Actual ±1 SD band
    if ~isempty(fp.act.mean)
        fill(ax1, [x, fliplr(x)], ...
            [fp.act.mean + fp.act.std, fliplr(fp.act.mean - fp.act.std)], ...
            cAct, 'FaceAlpha', 0.15, 'EdgeColor', 'none');
        plot(ax1, x, fp.act.mean, '-', 'Color', cAct, 'LineWidth', 1.5, ...
            'DisplayName', 'Actual');
    end

    % RMSE / MAE annotation
    infoStr = sprintf('RMSE=%.1f N  MAE=%.1f N  Peak=%.1f N', ...
        ft.rmse, ft.mae, ft.peakError);
    text(ax1, 0.02, 0.95, infoStr, 'Units','normalized', ...
        'Color', [0.9 0.9 0.9], 'FontSize', 9, 'VerticalAlignment','top');

    xlabel(ax1, 'Gait Cycle (%)', 'Color','w');
    ylabel(ax1, 'Force (N)', 'Color','w');
    title(ax1, sprintf('%s-side: Desired vs Actual (n=%d strides)', side, sf.nStrides), ...
        'Color','w', 'FontWeight','bold');
    legend(ax1, 'show', 'Location','northeast', 'TextColor','w', ...
        'Color',[0.1 0.1 0.2], 'FontSize',8);
    hold(ax1, 'off');

    % ========================================================================
    % Panel 2: Per-stride RMSE + MAE
    % ========================================================================
    ax2 = subplot(2, 1, 2);
    styleAx(ax2);
    hold(ax2, 'on');

    nS = numel(ft.rmsePerStride);
    if nS == 0
        text(ax2, 0.5, 0.5, 'No per-stride data', 'Units','normalized', ...
            'Color',[0.6 0.6 0.6], 'HorizontalAlignment','center');
    else
        strides = (1:nS)';

        % MAE as filled area below, RMSE as line on top
        fill(ax2, [strides; flipud(strides)], ...
            [ft.maePerStride; zeros(nS,1)], ...
            cAct, 'FaceAlpha', 0.25, 'EdgeColor', 'none', 'DisplayName','MAE');
        plot(ax2, strides, ft.maePerStride, '-', 'Color', [cAct 0.8], 'LineWidth', 1.0);

        plot(ax2, strides, ft.rmsePerStride, '-o', 'Color', cErr, ...
            'LineWidth', 1.4, 'MarkerSize', 4, 'MarkerFaceColor', cErr, ...
            'DisplayName','RMSE');

        % Overall mean lines
        yline(ax2, ft.rmse, '--', 'Color', [cErr 0.6], 'LineWidth', 0.8, ...
            'Label', sprintf('Mean RMSE %.1f N', ft.rmse), ...
            'LabelHorizontalAlignment','right', 'FontSize',8);
        yline(ax2, ft.mae,  '--', 'Color', [cAct 0.6], 'LineWidth', 0.8, ...
            'Label', sprintf('Mean MAE %.1f N', ft.mae), ...
            'LabelHorizontalAlignment','right', 'FontSize',8);

        xlim(ax2, [0.5, nS + 0.5]);
    end

    xlabel(ax2, 'Stride #', 'Color','w');
    ylabel(ax2, 'Error (N)', 'Color','w');
    title(ax2, 'Per-stride Force Error', 'Color','w', 'FontWeight','bold');
    legend(ax2, 'show', 'Location','northwest', 'TextColor','w', ...
        'Color',[0.1 0.1 0.2], 'FontSize',8);
    hold(ax2, 'off');

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
