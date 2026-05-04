function example_05_multipanel_with_labels()
% example_05_multipanel_with_labels  4-panel figure with auto a/b/c/d labels.
%
% MATLAB Copilot prompt examples:
%   "4개 panel 에 a, b, c, d 자동으로 붙이고 싶어"
%   "subplot 마다 lowercase bold label"
%   "Nature 스타일 multi-panel figure"
%
% CANONICAL Copilot prompt:
%   "Use subplot then loop applyPreset over each axes, then call
%    hwalker.plot.labelPanels(fig, 'Style', 'lowercase-bold', 'Preset', preset)."

    % --- Step 1: load your data ---
    r = hwalker.analyzeFile('~/data/your_subject.csv');
    r = r(1);

    preset = hwalker.plot.journalPreset('Nature');

    % --- Step 2: 4-panel figure (2 x 2) ---
    fig = figure('Color','w','Visible','on');

    subplot(2,2,1);
    plot(r.right.strideTimes, '-o');
    xlabel('Stride #'); ylabel('Stride time (s)');
    title('Stride Time Trend');

    subplot(2,2,2);
    bar([r.left.strideTimeMean, r.right.strideTimeMean]);
    set(gca,'XTickLabel',{'L','R'});
    ylabel('Stride time (s)');
    title('Left vs Right');

    subplot(2,2,3);
    x = linspace(0,100,101);
    plot(x, r.rightProfile.act.mean, '-', ...
         x, r.rightProfile.des.mean, '--');
    xlabel('Gait cycle (%)'); ylabel('Force (N)');
    title('Force Tracking (R)');

    subplot(2,2,4);
    bar([r.left.stancePctMean,  r.right.stancePctMean ;
         r.left.swingPctMean,   r.right.swingPctMean]);
    set(gca,'XTickLabel',{'Stance','Swing'});
    legend({'L','R'}, 'Location','best');
    ylabel('% gait cycle');

    % --- Step 3: apply Nature preset to ALL axes (manual loop) ---
    for ax = findobj(fig,'Type','axes')'
        hwalker.plot.applyPreset(fig, ax, preset, 2);
    end

    % --- Step 4: auto-label panels a, b, c, d (Nature bold lowercase) ---
    hwalker.plot.labelPanels(fig, ...
        'Style', 'lowercase-bold', ...
        'Preset', preset);

    % --- Step 5: export 2-col Nature ---
    hwalker.plot.exportFigure(fig, ...
        '~/Desktop/Fig3_overview_Nature.pdf', preset);
end
