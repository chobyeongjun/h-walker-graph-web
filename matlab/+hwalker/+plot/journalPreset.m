function p = journalPreset(name)
% hwalker.plot.journalPreset  Return journal figure specification struct.
%
%   p = hwalker.plot.journalPreset('IEEE')
%   p = hwalker.plot.journalPreset('Nature')
%   % Also: 'APA', 'Elsevier', 'MDPI', 'JNER'
%
% Verified specs (CLAUDE.md):
%   IEEE:     88.9/181 mm, Times, 8pt, 1.0pt, 600dpi, grayscale
%   Nature:   89/183 mm, Helvetica, 7pt, 0.5pt, 300dpi, Wong
%   APA:      85/174 mm, Arial, 10pt, 0.75pt, 300dpi, grayscale
%   Elsevier: 90/190 mm, Arial, 8pt, 0.5pt, 300dpi, default
%   MDPI:     85/170 mm, Palatino, 8pt, 0.75pt, 1000dpi, default
%   JNER:     85/170 mm, Arial, 8pt, 0.75pt, 300dpi, colorblind-safe

    % Wong color-blind-safe palette (Nature/JNER recommended)
    wongColors = [
          0  114  178;   % blue
        230  159    0;   % orange
         86  180  233;   % sky blue
          0  158  115;   % bluish green
        240  228   66;   % yellow
        213   94    0;   % vermillion
        204  121  167    % reddish purple
    ] / 255;

    grayscale = [
        0    0    0   ;
        0.40 0.40 0.40;
        0.65 0.65 0.65;
        0.20 0.20 0.20;
        0.50 0.50 0.50;
        0.75 0.75 0.75;
        0.15 0.15 0.15
    ];

    defaultColors = [
        0      0.447  0.741;
        0.850  0.325  0.098;
        0.929  0.694  0.125;
        0.494  0.184  0.556;
        0.466  0.674  0.188;
        0.301  0.745  0.933;
        0.635  0.078  0.184
    ];

    presets.IEEE     = struct('col1mm',88.9,'col2mm',181,  'font','Times New Roman',    'bodyPt',8,  'strokePt',1.00,'dpi',600,  'palette','grayscale');
    presets.Nature   = struct('col1mm',89,  'col2mm',183,  'font','Helvetica',           'bodyPt',7,  'strokePt',0.50,'dpi',300,  'palette','wong');
    presets.APA      = struct('col1mm',85,  'col2mm',174,  'font','Arial',               'bodyPt',10, 'strokePt',0.75,'dpi',300,  'palette','grayscale');
    presets.Elsevier = struct('col1mm',90,  'col2mm',190,  'font','Arial',               'bodyPt',8,  'strokePt',0.50,'dpi',300,  'palette','default');
    presets.MDPI     = struct('col1mm',85,  'col2mm',170,  'font','Palatino Linotype',   'bodyPt',8,  'strokePt',0.75,'dpi',1000, 'palette','default');
    presets.JNER     = struct('col1mm',85,  'col2mm',170,  'font','Arial',               'bodyPt',8,  'strokePt',0.75,'dpi',300,  'palette','wong');

    if ~isfield(presets, name)
        validNames = strjoin(fieldnames(presets), ', ');
        error('hwalker:plot:unknownJournal', ...
            'Unknown journal ''%s''. Valid: %s', name, validNames);
    end

    p = presets.(name);

    switch p.palette
        case 'wong',      p.colors = wongColors;
        case 'grayscale', p.colors = grayscale;
        otherwise,        p.colors = defaultColors;
    end

    % Inches for MATLAB figure size  (1 inch = 25.4 mm)
    p.col1in = p.col1mm / 25.4;
    p.col2in = p.col2mm / 25.4;
end
