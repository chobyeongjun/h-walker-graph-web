function exportFigure(fig, filepath, preset, format)
% hwalker.plot.exportFigure  Export figure at publication quality.
%
%   hwalker.plot.exportFigure(fig, 'Fig1.pdf', preset)
%   hwalker.plot.exportFigure(fig, 'Fig1.tif', preset, 'tiff')
%   hwalker.plot.exportFigure(fig, 'Fig1.eps', preset, 'eps')
%
% Vector formats (pdf/eps/svg): ContentType='vector', no DPI rounding.
% Raster formats (png/tif/tiff): uses preset.dpi.
%
% Requires MATLAB R2020a+ (exportgraphics).

    if nargin < 4
        [~, ~, ext] = fileparts(filepath);
        format = lower(strrep(ext, '.', ''));
    end

    switch lower(format)
        case {'pdf', 'eps', 'svg'}
            exportgraphics(fig, filepath, ...
                'ContentType',    'vector', ...
                'BackgroundColor','none');
        case {'png', 'tif', 'tiff'}
            exportgraphics(fig, filepath, ...
                'Resolution',     preset.dpi, ...
                'BackgroundColor','white');
        otherwise
            exportgraphics(fig, filepath, 'Resolution', preset.dpi);
    end
    fprintf('Saved: %s\n', filepath);
end
