function info = listJournals()
% hwalker.plot.listJournals  Print all available journal presets.
%
%   hwalker.plot.listJournals             % print to console
%   info = hwalker.plot.listJournals();   % also return as table
%
% Use the 'name' column with hwalker.plot.journalPreset(name).
% For a journal not in the list, register a one-off:
%   p = hwalker.plot.journalPreset('Custom', struct('col1mm',88, ...))

    keys = {
        % --- Robotics-domain (added for H-Walker) ---
        'TRO',             'IEEE Trans on Robotics',                  'robotics flagship'
        'RAL',             'IEEE RA-L',                                'most active venue'
        'TNSRE',           'IEEE Trans Neural Sys & Rehab Eng',       'rehab robotics — closest match for H-Walker'
        'TMECH',           'IEEE/ASME Trans on Mechatronics',         'cable + actuator design'
        'ICRA',            'IEEE ICRA conference',                     'IROS uses same template'
        'IROS',            'IEEE/RSJ IROS conference',                 'alias for ICRA'
        'IJRR',            'Int J Robotics Research (SAGE)',          'higher-tier journal'
        'SciRobotics',     'Science Robotics (AAAS)',                  'top-tier'
        'SoftRobotics',    'Soft Robotics (Liebert)',                  'compliant / cable-driven'
        'FrontNeurorobot', 'Frontiers in Neurorobotics',               'open-access neuro-robotics'
        'AuRo',            'Autonomous Robots (Springer)',             'classical robotics'
        % --- General-purpose (kept from original) ---
        'IEEE',            'IEEE Trans / Journals',                    'general IEEE Trans (uses Times)'
        'Nature',          'Nature / Nature subjournals',              'Helvetica Wong palette'
        'APA',             'APA 7th edition',                          'sans-serif grayscale'
        'Elsevier',        'Elsevier journals',                        'has 1.5-col variant'
        'MDPI',            'MDPI (Sensors / Applied Sciences)',        'open-access'
        'JNER',            'J. NeuroEngineering & Rehabilitation',     'rehab Springer/BMC'
    };

    if nargout == 0
        fprintf('\n=== Available journal presets (use with hwalker.plot.journalPreset(NAME)) ===\n\n');
        fprintf('  %-18s %-42s %s\n', 'NAME', 'JOURNAL', 'NOTES');
        fprintf('  %-18s %-42s %s\n', repmat('-',1,18), repmat('-',1,42), repmat('-',1,40));
        for i = 1:size(keys,1)
            fprintf('  %-18s %-42s %s\n', keys{i,1}, keys{i,2}, keys{i,3});
        end
        fprintf('\n  Custom: hwalker.plot.journalPreset(''Custom'', struct(''col1mm'',88, ...))\n');
        fprintf('\n  Detailed spec: p = hwalker.plot.journalPreset(''TRO''); disp(p)\n\n');
    else
        info = cell2table(keys, 'VariableNames', {'name','journal','notes'});
    end
end
