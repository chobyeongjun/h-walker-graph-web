function p = journalPreset(name)
% hwalker.plot.journalPreset  Return journal figure specification struct.
%
%   p = hwalker.plot.journalPreset('IEEE')
%   p = hwalker.plot.journalPreset('Nature')
%   % Also: 'APA', 'Elsevier', 'MDPI', 'JNER'
%
% Verified specs (CLAUDE.md + backend/services/publication_engine.py).
% Python-side `Preset` dataclass is the single source of truth; this file
% is a verbatim mirror so MATLAB and the web-app render identical figures.
%
% Returned struct fields:
%   name, full           string identifiers
%   col1mm, col1h_mm     1-column width / height (mm)
%   col2mm, col2h_mm     2-column width / height (mm)
%   col15mm, col15h_mm   1.5-column (Elsevier only) — NaN otherwise
%   maxHmm               maximum allowed figure height (page constraint)
%   col1in, col2in, col15in        same widths in inches (1 in = 25.4 mm)
%   col1h_in, col2h_in, col15h_in  same heights in inches
%   font, fontFallback   primary font + cellstr fallback chain
%   bodyPt, axisPt       body / axis tick label size (pt)
%   legendPt, titlePt    legend / title text size (pt)
%   strokePt             plotted line width (pt)
%   axesPt               axes spine line width (pt) — fixed across journals
%   gridPt               grid line width (pt)
%   palette              Nx3 RGB matrix used for line / marker colors
%   paletteName          'wong' | 'grayscale' | 'default' | 'elsevier'
%   colorblindSafe       logical flag
%   bg, axisColor, gridColor   hex strings
%   formats              cellstr of accepted export formats (informational)
%   dpi                  raster export DPI
%   interpreter          'tex' | 'latex' | 'none' — text interpreter for labels
%   notes                string for documentation

    % ---------- Color palettes ----------
    % Wong color-blind safe palette — Wong B (2011) Nature Methods 8:441
    wongColors = [
          0  114  178;   % blue
        230  159    0;   % orange
         86  180  233;   % sky blue
          0  158  115;   % bluish green
        240  228   66;   % yellow
        213   94    0;   % vermillion
        204  121  167    % reddish purple
    ] / 255;

    grayscaleColors = [
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

    elsevierColors = [
        228   26   28;
         55  126  184;
         77  175   74;
        152   78  163;
        255  127    0;
        255  255   51;
        166   86   40
    ] / 255;

    % ---------- Preset table (verbatim from publication_engine.py) ----------
    presets.IEEE = makePreset( ...
        'IEEE', 'IEEE Transactions / Journals', ...
        88.9, 70.0,  181.0, 90.0,  NaN, NaN,  216.0, ...
        'Times New Roman', {'Times New Roman','Times','serif'}, ...
        8, 8, 7, 10,  1.0, 0.6, 0.4, ...
        'grayscale', false, '#ffffff', '#000000', '#CCCCCC', ...
        {'PDF','EPS','TIFF','SVG','PNG'}, 600, 'tex', ...
        '1col 88.9mm / 2col 181mm · 8-10pt Times · grayscale preferred');

    presets.Nature = makePreset( ...
        'Nature', 'Nature · Nature journals', ...
        89.0, 60.0,  183.0, 90.0,  NaN, NaN,  247.0, ...
        'Helvetica', {'Helvetica','Arial','sans-serif'}, ...
        7, 7, 6, 8,   0.5, 0.6, 0.25, ...
        'wong', true, '#ffffff', '#000000', '#E5E5E5', ...
        {'PDF','EPS','AI','TIFF'}, 300, 'tex', ...
        'Single 89mm / double 183mm · Helvetica 5-7pt · Wong colorblind-safe');

    presets.APA = makePreset( ...
        'APA', 'APA 7th edition', ...
        85.0, 65.0,  174.0, 100.0, NaN, NaN,  235.0, ...
        'Arial', {'Arial','Helvetica','sans-serif'}, ...
        10, 10, 9, 11, 0.75, 0.6, 0.3, ...
        'grayscale', false, '#ffffff', '#000000', '#DDDDDD', ...
        {'PDF','SVG','PNG','TIFF'}, 300, 'tex', ...
        'Sans-serif 8-14pt · grayscale preferred · figure note below');

    presets.Elsevier = makePreset( ...
        'Elsevier', 'Elsevier journals', ...
        90.0, 60.0,  190.0, 90.0,  140.0, 80.0,  240.0, ...
        'Arial', {'Arial','Helvetica','sans-serif'}, ...
        8, 8, 7, 9,   0.5, 0.6, 0.25, ...
        'elsevier', false, '#ffffff', '#000000', '#DDDDDD', ...
        {'EPS','PDF','TIFF','JPEG'}, 300, 'tex', ...
        'Single 90mm / 1.5 col 140mm / double 190mm · Arial · EPS preferred');

    presets.MDPI = makePreset( ...
        'MDPI', 'MDPI (Applied Sciences, Sensors, etc.)', ...
        85.0, 65.0,  170.0, 90.0,  NaN, NaN,  225.0, ...
        'Palatino Linotype', {'Palatino Linotype','Palatino','Book Antiqua','serif'}, ...
        8, 8, 7, 10,  0.75, 0.6, 0.3, ...
        'default', false, '#ffffff', '#000000', '#E0E0E0', ...
        {'PDF','TIFF','PNG','EPS'}, 1000, 'tex', ...
        'Single 85mm / double 170mm · Palatino 8pt · 1000 dpi line art');

    presets.JNER = makePreset( ...
        'JNER', 'J. NeuroEngineering & Rehabilitation (BMC)', ...
        85.0, 65.0,  170.0, 90.0,  NaN, NaN,  225.0, ...
        'Arial', {'Arial','Helvetica','sans-serif'}, ...
        8, 8, 7, 10,  0.75, 0.6, 0.3, ...
        'wong', true, '#ffffff', '#000000', '#E0E0E0', ...
        {'PDF','EPS','PNG','TIFF'}, 300, 'tex', ...
        'Springer/BMC · Arial 8pt · colorblind-safe · 300 dpi');

    if ~isfield(presets, name)
        validNames = strjoin(fieldnames(presets), ', ');
        error('hwalker:plot:unknownJournal', ...
            'Unknown journal ''%s''. Valid: %s', name, validNames);
    end

    p = presets.(name);

    switch p.paletteName
        case 'wong',      p.palette = wongColors;
        case 'grayscale', p.palette = grayscaleColors;
        case 'elsevier',  p.palette = elsevierColors;
        otherwise,        p.palette = defaultColors;
    end
    % Backward compatibility: legacy code expected `colors`
    p.colors = p.palette;

    % Inches conversions  (1 inch = 25.4 mm)
    p.col1in   = p.col1mm   / 25.4;
    p.col2in   = p.col2mm   / 25.4;
    p.col1h_in = p.col1h_mm / 25.4;
    p.col2h_in = p.col2h_mm / 25.4;
    if isfinite(p.col15mm)
        p.col15in   = p.col15mm   / 25.4;
        p.col15h_in = p.col15h_mm / 25.4;
    else
        p.col15in   = NaN;
        p.col15h_in = NaN;
    end
end


function s = makePreset(name, fullName, ...
        col1mm, col1h_mm, col2mm, col2h_mm, col15mm, col15h_mm, maxHmm, ...
        font, fontFallback, ...
        bodyPt, axisPt, legendPt, titlePt, ...
        strokePt, axesPt, gridPt, ...
        paletteName, colorblindSafe, bg, axisColor, gridColor, ...
        formats, dpi, interpreter, notes)
    s.name           = name;
    s.full           = fullName;
    s.col1mm         = col1mm;
    s.col1h_mm       = col1h_mm;
    s.col2mm         = col2mm;
    s.col2h_mm       = col2h_mm;
    s.col15mm        = col15mm;
    s.col15h_mm      = col15h_mm;
    s.maxHmm         = maxHmm;
    s.font           = font;
    s.fontFallback   = fontFallback;
    s.bodyPt         = bodyPt;
    s.axisPt         = axisPt;
    s.legendPt       = legendPt;
    s.titlePt        = titlePt;
    s.strokePt       = strokePt;
    s.axesPt         = axesPt;
    s.gridPt         = gridPt;
    s.paletteName    = paletteName;
    s.colorblindSafe = colorblindSafe;
    s.bg             = bg;
    s.axisColor      = axisColor;
    s.gridColor      = gridColor;
    s.formats        = formats;
    s.dpi            = dpi;
    s.interpreter    = interpreter;
    s.notes          = notes;
end
