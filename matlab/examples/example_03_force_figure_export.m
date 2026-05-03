function example_03_force_figure_export()
% example_03_force_figure_export  Export force-tracking figure across many journals.
%
% Use this when: you want the SAME figure rendered at 6+ different journal
% sizes/fonts/palettes, ready to paste into the manuscript.
%
% MATLAB Copilot prompt examples:
%   "force tracking 그래프를 모든 robotics 저널 사이즈로 내보내고 싶어"
%   "IEEE T-RO + RA-L + ICRA + JNER 한번에 PDF 출력"
%   "이 figure 를 Nature 2-col 사이즈로 만들어줘"

    % --- Step 1: load + analyze YOUR data ---
    results = hwalker.analyzeFile('~/data/your_subject.csv');
    r = results(1);    % first sync window (use results(2) etc. if multiple)

    outDir = '~/Desktop/paper_figures';

    % --- Step 2a: ONE figure, ONE journal ---
    preset = hwalker.plot.journalPreset('TRO');           % IEEE Trans on Robotics
    fig    = hwalker.plot.forceQC(r, 'R', 'TRO');
    hwalker.plot.exportFigure(fig, fullfile(outDir,'Fig1_TRO.pdf'), preset);
    close(fig);

    % --- Step 2b: ONE figure, ALL robotics journals at once ---
    %   (writes Fig1_force_TRO.pdf, Fig1_force_RAL.pdf, etc.)
    hwalker.plot.exportAllJournals( ...
        @hwalker.plot.forceQC, ...                        % plot function
        {r, 'R'}, ...                                      % args before journal name
        outDir, ...
        'BaseName', 'Fig1_force', ...
        'Journals', {'TRO','RAL','TNSRE','TMECH','ICRA','IJRR', ...
                     'SciRobotics','SoftRobotics','FrontNeurorobot','AuRo'}, ...
        'Formats',  {'PDF','PNG'}, ...
        'NCols',    2);                                    % use 2-col width

    % --- Step 3: 1.5-col variant (Elsevier only supports this) ---
    presetEls = hwalker.plot.journalPreset('Elsevier');
    fig2 = hwalker.plot.forceQC(r, 'R', 'Elsevier');
    hwalker.plot.applyPreset(fig2, gca, presetEls, 1.5);
    hwalker.plot.exportFigure(fig2, fullfile(outDir,'Fig1_Elsevier_15col.pdf'), presetEls);
    close(fig2);

    % --- Step 4: list available journals (handy reminder) ---
    hwalker.plot.listJournals();

    % --- Step 5: register a CUSTOM journal (yours not in the list?) ---
    %   p_custom = hwalker.plot.journalPreset('Custom', struct( ...
    %       'name',    'MyTargetJournal', ...
    %       'col1mm',  88, 'col1h_mm', 70, ...
    %       'col2mm',  180, 'col2h_mm', 90, ...
    %       'font',    'Arial', ...
    %       'bodyPt',  9, ...
    %       'strokePt',0.75, ...
    %       'dpi',     600, ...
    %       'paletteName','wong'));
    %   fig3 = hwalker.plot.forceQC(r, 'R');     % renders with default first
    %   hwalker.plot.applyPreset(fig3, gca, p_custom, 2);
    %   hwalker.plot.exportFigure(fig3, fullfile(outDir,'Fig1_MyJournal.pdf'), p_custom);
end
