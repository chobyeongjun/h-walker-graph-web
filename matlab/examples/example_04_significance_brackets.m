function example_04_significance_brackets()
% example_04_significance_brackets  Bar chart with * / ** / *** brackets.
%
% MATLAB Copilot prompt examples:
%   "bar chart 위에 유의도 표시 (asterisks) 추가"
%   "L vs R 차이 위에 ** 별표 그리고 싶어"
%   "metric bar + p-value bracket"
%
% CANONICAL Copilot prompt:
%   "Use hwalker.plot.metricBar then hwalker.plot.drawSignificance(ax, x1, x2, yTop, p, 'Style', 'asterisk', 'Preset', preset)."

    % --- Step 1: load + analyze your data ---
    pre  = hwalker.analyzeFile('~/data/pre.csv');
    post = hwalker.analyzeFile('~/data/post.csv');

    % --- Step 2: build the bar inputs ---
    means = [pre(1).left.strideTimeMean,  pre(1).right.strideTimeMean ;
             post(1).left.strideTimeMean, post(1).right.strideTimeMean];
    stds  = [pre(1).left.strideTimeStd,   pre(1).right.strideTimeStd ;
             post(1).left.strideTimeStd,  post(1).right.strideTimeStd];

    preset = hwalker.plot.journalPreset('TRO');
    fig    = hwalker.plot.metricBar(means, stds, ...
                {'Pre','Post'}, {'L','R'}, ...
                'Stride Time (s)', preset, 1);

    % --- Step 3: compute p-value for each comparison ---
    r_left  = hwalker.stats.pairedTest( ...
                pre(1).left.strideTimes, post(1).left.strideTimes);
    r_right = hwalker.stats.pairedTest( ...
                pre(1).right.strideTimes, post(1).right.strideTimes);

    % --- Step 4: draw brackets ---
    ax = gca;
    yMax = max(means(:) + stds(:));
    %   Left bar: Pre-L (x=1-0.2) vs Post-L (x=2-0.2)
    hwalker.plot.drawSignificance(ax, 0.8, 1.8, yMax * 1.05, ...
        r_left.p_ttest, 'Style','asterisk', 'Preset', preset);
    %   Right bar: Pre-R (x=1+0.2) vs Post-R (x=2+0.2)
    hwalker.plot.drawSignificance(ax, 1.2, 2.2, yMax * 1.15, ...
        r_right.p_ttest, 'Style','asterisk', 'Preset', preset);

    % --- Step 5: export ---
    hwalker.plot.exportFigure(fig, ...
        '~/Desktop/Fig2_strideTime_pre_post_TRO.pdf', preset);
end
