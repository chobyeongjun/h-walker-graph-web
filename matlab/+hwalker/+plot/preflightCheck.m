function report = preflightCheck(plotFnOrFig, argsOrEmpty, preset, nCols)
% hwalker.plot.preflightCheck  Copilot-style pre-render validation.
%
% Validates inputs BEFORE a plot/export call and prints actionable
% warnings to the console so users can fix issues before wasting time.
%
% Two calling conventions:
%
%   % (1) Pre-flight before calling a plot function:
%   report = hwalker.plot.preflightCheck(@hwalker.plot.forceQC, ...
%                {result, 'R'}, preset, 1);
%
%   % (2) Post-render check on an existing figure (font/size sanity):
%   report = hwalker.plot.preflightCheck(fig, [], preset, 1);
%
% Returns struct:
%   .ok          true if no CRITICAL issues (warnings still allowed)
%   .critical    cellstr of CRITICAL messages (will likely break export)
%   .warnings    cellstr of WARNING messages (cosmetic / suboptimal)
%   .info        cellstr of INFO messages (good-to-know)
%
% Console emits with severity prefix:  [CRITICAL] / [WARN] / [INFO]
%
% This function is automatically invoked by exportAllJournals; users can
% also run it manually:
%   hwalker.plot.preflightCheck(@hwalker.plot.forceQC, {results(1),'R'}, ...
%       hwalker.plot.journalPreset('Nature'), 2);

    if nargin < 4, nCols = 1; end
    report = struct('ok', true, 'critical', {{}}, ...
                    'warnings', {{}}, 'info', {{}});

    % ====================================================================
    % Branch 1: figure handle passed → post-render checks only
    % ====================================================================
    if isgraphics(plotFnOrFig, 'figure')
        report = checkRenderedFigure(plotFnOrFig, preset, nCols, report);
        report = emit(report);
        return
    end

    % ====================================================================
    % Branch 2: function handle + args → pre-flight checks
    % ====================================================================
    plotFn = plotFnOrFig;
    args   = argsOrEmpty;
    if isempty(args), args = {}; end

    % --- 1. Function handle exists ---
    if ~isa(plotFn, 'function_handle')
        report.critical{end+1} = 'plotFn is not a function handle.';
        report = emit(report);  return
    end
    fnInfo = functions(plotFn);
    if isempty(fnInfo.function)
        report.critical{end+1} = 'plotFn could not be resolved.';
    end

    % --- 2. Preset shape ---
    requiredFields = {'name','col1mm','col2mm','col1h_mm','col2h_mm', ...
                      'font','bodyPt','axisPt','strokePt','axesPt', ...
                      'dpi','interpreter','palette'};
    presetMissing = false;
    for f = requiredFields
        if ~isfield(preset, f{1})
            report.critical{end+1} = sprintf( ...
                'preset is missing field ''%s'' — re-call hwalker.plot.journalPreset(name).', f{1});
            presetMissing = true;
        end
    end
    if presetMissing
        % Stop further checks that read those fields — they would crash.
        report.ok = false;
        report = emit(report);
        return
    end

    % --- 3. nCols validity ---
    if abs(nCols - 1.5) < 1e-9
        if ~isfield(preset, 'col15mm') || ~isfinite(preset.col15mm)
            report.critical{end+1} = sprintf( ...
                'Preset ''%s'' has no 1.5-column variant — only Elsevier supports nCols=1.5. Use 1 or 2.', ...
                getfieldOrEmpty(preset,'name'));
        end
    elseif ~ismember(nCols, [1 2])
        report.critical{end+1} = sprintf('nCols must be 1, 1.5, or 2; got %g', nCols);
    end

    % --- 4. Font installed on this system ---
    fontIssue = checkFontInstalled(preset.font);
    if ~isempty(fontIssue)
        report.warnings{end+1} = fontIssue;
    end

    % --- 5. Body / axis font readability at small sizes ---
    if isfield(preset, 'bodyPt')
        if preset.bodyPt < 6
            report.warnings{end+1} = sprintf( ...
                'bodyPt=%.1f may be unreadable when printed; reviewers usually want >= 6pt.', ...
                preset.bodyPt);
        end
    end

    % --- 6. DPI vs format guidance ---
    if isfield(preset, 'dpi') && preset.dpi >= 1000
        report.info{end+1} = sprintf( ...
            'DPI=%d is large — vector formats (PDF/EPS/SVG) ignore DPI; rasters (PNG/TIFF) will be heavy.', ...
            preset.dpi);
    end

    % --- 7. Inspect first arg for typical "result" struct issues ---
    if ~isempty(args)
        first = args{1};
        if isstruct(first) && numel(first) == 1
            checkResultStruct(first, args, report);
        elseif isstruct(first) && numel(first) > 1
            report.info{end+1} = sprintf( ...
                'plotFn given a %d-element result struct array — only the first will be plotted unless plotFn iterates.', ...
                numel(first));
        end
    end

    % --- 8. Figure aspect-ratio warning if extreme ---
    if isfield(preset, 'col1mm') && isfield(preset, 'col1h_mm') && nCols == 1
        ar = preset.col1mm / preset.col1h_mm;
        if ar > 2.0
            report.info{end+1} = sprintf( ...
                'Aspect ratio %.2f:1 (%s 1-col) is wide — long x-axis works best.', ...
                ar, getfieldOrEmpty(preset,'name'));
        end
    end

    report.ok = isempty(report.critical);
    report = emit(report);
end


% =====================================================================
%  Sub-checkers
% =====================================================================

function report = checkRenderedFigure(fig, preset, nCols, report)
    % Find primary axes
    axList = findall(fig, 'Type', 'axes');
    keep   = ~ismember(get(axList, 'Tag'), {'legend','Colorbar'});
    if iscell(keep), keep = cell2mat(keep); end
    if isempty(keep), keep = true(size(axList)); end
    axList = axList(keep);
    if isempty(axList)
        report.critical{end+1} = 'No data axes found in figure.';
        return
    end

    % Check that figure size matches preset
    units = get(fig, 'Units');
    set(fig, 'Units', 'inches');
    pos = get(fig, 'Position');
    set(fig, 'Units', units);
    expectedW = pickIn(preset, nCols, 'w');
    expectedH = pickIn(preset, nCols, 'h');
    if isfinite(expectedW)
        if abs(pos(3) - expectedW) > 0.01
            report.warnings{end+1} = sprintf( ...
                'Figure width %.3f in differs from preset %s %d-col target %.3f in. Did you forget applyPreset()?', ...
                pos(3), getfieldOrEmpty(preset,'name'), nCols, expectedW);
        end
        if abs(pos(4) - expectedH) > 0.01
            report.warnings{end+1} = sprintf( ...
                'Figure height %.3f in differs from preset target %.3f in.', ...
                pos(4), expectedH);
        end
    end

    % Check that axes have data
    for i = 1:numel(axList)
        c = get(axList(i), 'Children');
        if isempty(c)
            report.warnings{end+1} = sprintf('Axes #%d is empty (no plotted data).', i);
        end
    end
end


function checkResultStruct(s, args, ~)
    % Common fields we expect from analyzeFile output
    % This is informational — we don't fail; just hint at empty data.
    if isfield(s, 'left') && isfield(s, 'right')
        sideHint = '';
        if numel(args) >= 2 && (ischar(args{2}) || isstring(args{2}))
            sideHint = upper(char(args{2}));
        end
        if ~isempty(sideHint)
            switch sideHint(1)
                case 'L', subKey = 'left';
                case 'R', subKey = 'right';
                otherwise, subKey = '';
            end
            if ~isempty(subKey)
                if isfield(s.(subKey), 'nStrides') && s.(subKey).nStrides == 0
                    warning('hwalker:preflight:noStrides', ...
                        '[CRITICAL] result.%s.nStrides == 0 — plot will be empty. Pick the other side or check sync window.', subKey);
                end
            end
        end
    end
end


function msg = checkFontInstalled(fontName)
    msg = '';
    try
        installed = listfonts;       % returns sorted cellstr (MATLAB built-in)
        if ~ismember(fontName, installed)
            % Some platforms list 'Helvetica' as 'Helvetica Neue' etc — try contains
            hit = any(contains(installed, fontName));
            if ~hit
                msg = sprintf( ...
                    'Font ''%s'' is not installed on this system. MATLAB will substitute. Install or pick a different journal.', ...
                    fontName);
            end
        end
    catch
        % listfonts not available in batch headless mode → skip silently
    end
end


function v = getfieldOrEmpty(s, f)
    if isstruct(s) && isfield(s, f), v = s.(f); else, v = '<unknown>'; end
end


function v = pickIn(preset, nCols, dim)
    if abs(nCols - 1) < 1e-9
        if dim == 'w', f = 'col1in';   else, f = 'col1h_in'; end
    elseif abs(nCols - 2) < 1e-9
        if dim == 'w', f = 'col2in';   else, f = 'col2h_in'; end
    elseif abs(nCols - 1.5) < 1e-9
        if dim == 'w', f = 'col15in';  else, f = 'col15h_in'; end
    else
        v = NaN; return
    end
    if isfield(preset, f), v = preset.(f); else, v = NaN; end
end


function report = emit(report)
    for i = 1:numel(report.critical)
        fprintf(2, '[CRITICAL] %s\n', report.critical{i});  %#ok<PRTCAL>
    end
    for i = 1:numel(report.warnings)
        fprintf('[WARN]     %s\n', report.warnings{i});
    end
    for i = 1:numel(report.info)
        fprintf('[INFO]     %s\n', report.info{i});
    end
    report.ok = isempty(report.critical);
end
