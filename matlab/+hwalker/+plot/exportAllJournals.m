function manifest = exportAllJournals(plotFn, plotArgs, outputDir, varargin)
% hwalker.plot.exportAllJournals  Export the same figure across all 6 journal presets.
%
%   manifest = hwalker.plot.exportAllJournals( ...
%       @hwalker.plot.forceQC, {result, 'R'}, '~/paper/figures');
%
%   manifest = hwalker.plot.exportAllJournals(plotFn, plotArgs, outputDir, ...
%                  'BaseName', 'Fig1_force', ...
%                  'Journals', {'IEEE','Nature','JNER'}, ...
%                  'Formats',  {'PDF','PNG'}, ...
%                  'NCols',    1, ...
%                  'CloseAfter', true);
%
% Inputs:
%   plotFn     function handle returning a figure handle.
%              Last arg of plotFn is the journal name string.
%              e.g. @(r, s, j) hwalker.plot.forceQC(r, s, j)
%   plotArgs   cell array of arguments to pass to plotFn BEFORE the journal name.
%              Journal name will be appended automatically as the last arg.
%   outputDir  string. Created if it does not exist.
%
% Name-value parameters:
%   'BaseName'    file name prefix (default 'Fig')
%   'Journals'    cellstr of journal keys (default all 6)
%   'Formats'     cellstr of output formats (default {'PDF'})
%   'NCols'       1, 1.5, or 2 (default 1)
%   'CloseAfter'  close each fig after export (default true)
%
% Returns manifest struct array, one row per (journal, format) combo:
%   .journal  .format  .filename  .widthMm  .heightMm  .dpi  .ok  .error

    p = inputParser;
    addParameter(p, 'BaseName',   'Fig',   @(x) ischar(x) || isstring(x));
    addParameter(p, 'Journals',   {'IEEE','Nature','APA','Elsevier','MDPI','JNER'});
    addParameter(p, 'Formats',    {'PDF'}, @iscell);
    addParameter(p, 'NCols',      1);
    addParameter(p, 'CloseAfter', true,    @islogical);
    parse(p, varargin{:});
    base    = char(p.Results.BaseName);
    jlist   = p.Results.Journals;
    flist   = p.Results.Formats;
    nCols   = p.Results.NCols;
    closeAf = p.Results.CloseAfter;

    if ~exist(outputDir, 'dir')
        mkdir(outputDir);
    end

    nRows = numel(jlist) * numel(flist);
    manifest = repmat(struct( ...
        'journal', '', 'format', '', 'filename', '', ...
        'widthMm', NaN, 'heightMm', NaN, 'dpi', NaN, ...
        'ok', false, 'error', ''), nRows, 1);

    row = 0;
    for ji = 1:numel(jlist)
        journal = jlist{ji};
        try
            preset = hwalker.plot.journalPreset(journal);
        catch ME
            row = row + 1;
            manifest(row).journal = journal;
            manifest(row).error   = ME.message;
            continue
        end

        % Run preflight check (auto-warning) on the inputs
        try
            hwalker.plot.preflightCheck(plotFn, plotArgs, preset, nCols);
        catch ME
            warning('hwalker:exportAllJournals:preflight', ...
                '[%s] preflight: %s', journal, ME.message);
        end

        % Build the figure with this preset
        try
            argsPlus = [plotArgs(:)' {journal}];
            fig = plotFn(argsPlus{:});
        catch ME
            for fi = 1:numel(flist)
                row = row + 1;
                manifest(row).journal = journal;
                manifest(row).format  = flist{fi};
                manifest(row).error   = sprintf('plotFn failed: %s', ME.message);
            end
            continue
        end

        % Export each requested format
        for fi = 1:numel(flist)
            fmt = upper(flist{fi});
            row = row + 1;
            ext = lower(fmt);
            if strcmp(ext, 'jpeg'), ext = 'jpg'; end
            fname = fullfile(outputDir, ...
                sprintf('%s_%s.%s', base, journal, ext));
            try
                hwalker.plot.exportFigure(fig, fname, preset);
                manifest(row).journal  = journal;
                manifest(row).format   = fmt;
                manifest(row).filename = fname;
                manifest(row).widthMm  = pickWidth(preset, nCols);
                manifest(row).heightMm = pickHeight(preset, nCols);
                manifest(row).dpi      = preset.dpi;
                manifest(row).ok       = true;
            catch ME
                manifest(row).journal = journal;
                manifest(row).format  = fmt;
                manifest(row).error   = ME.message;
            end
        end

        if closeAf && ishandle(fig)
            close(fig);
        end
    end

    % Console summary
    nOk = sum([manifest.ok]);
    fprintf('exportAllJournals: %d/%d files written → %s\n', ...
        nOk, numel(manifest), outputDir);
end


function w = pickWidth(preset, nCols)
    if abs(nCols - 1) < 1e-9,    w = preset.col1mm;
    elseif abs(nCols - 2) < 1e-9, w = preset.col2mm;
    elseif abs(nCols - 1.5) < 1e-9, w = preset.col15mm;
    else, w = NaN;
    end
end

function hh = pickHeight(preset, nCols)
    if abs(nCols - 1) < 1e-9,    hh = preset.col1h_mm;
    elseif abs(nCols - 2) < 1e-9, hh = preset.col2h_mm;
    elseif abs(nCols - 1.5) < 1e-9, hh = preset.col15h_mm;
    else, hh = NaN;
    end
end
