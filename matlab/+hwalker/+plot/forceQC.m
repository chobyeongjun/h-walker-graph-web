function fig = forceQC(result, side, journal)
% hwalker.plot.forceQC  Normalized force profile — Desired vs Actual ±1 SD.
%
%   hwalker.plot.forceQC(result, 'R')
%   hwalker.plot.forceQC(result, 'R', 'JNER')   % default: JNER
%   % journal: 'IEEE' | 'Nature' | 'APA' | 'Elsevier' | 'MDPI' | 'JNER'
%
% result = one element from hwalker.analyzeFile output

    if nargin < 3, journal = 'JNER'; end
    preset = hwalker.plot.journalPreset(journal);

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

    % Wong palette: blue = desired, orange = actual
    cDes = preset.colors(1,:);
    cAct = preset.colors(2,:);

    fig = figure('Color', 'w', 'Visible', 'on');
    ax  = axes(fig);
    hold(ax, 'on');

    x = linspace(0, 100, 101);

    % ---- Desired ±1 SD ----
    if ~isempty(fp.des.mean)
        fill(ax, [x, fliplr(x)], ...
            [fp.des.mean + fp.des.std, fliplr(fp.des.mean - fp.des.std)], ...
            cDes, 'FaceAlpha', 0.20, 'EdgeColor', 'none');
        plot(ax, x, fp.des.mean, '-', 'Color', cDes, ...
            'LineWidth', preset.strokePt, 'DisplayName', 'Desired');
    end

    % ---- Actual ±1 SD ----
    if ~isempty(fp.act.mean)
        fill(ax, [x, fliplr(x)], ...
            [fp.act.mean + fp.act.std, fliplr(fp.act.mean - fp.act.std)], ...
            cAct, 'FaceAlpha', 0.20, 'EdgeColor', 'none');
        plot(ax, x, fp.act.mean, '-', 'Color', cAct, ...
            'LineWidth', preset.strokePt, 'DisplayName', 'Actual');
    end

    % ---- Axes labels ----
    xlabel(ax, 'Gait Cycle (%)');
    ylabel(ax, 'Force (N)');
    title(ax, sprintf('%s-side Force Tracking  (n=%d strides,  RMSE=%.1f N)', ...
        side, sf.nStrides, ft.rmse));
    legend(ax, 'show', 'Location', 'northeast');
    grid(ax, 'on');
    box(ax, 'off');
    xlim(ax, [0 100]);

    hwalker.plot.applyPreset(fig, ax, preset, 1);
end
