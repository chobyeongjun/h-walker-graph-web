function exportFigure(fig, filepath, preset, format)
% hwalker.plot.exportFigure  Export figure at publication quality.
%
%   hwalker.plot.exportFigure(fig, 'Fig1.pdf', preset)
%   hwalker.plot.exportFigure(fig, 'Fig1.tif', preset, 'tiff')
%   hwalker.plot.exportFigure(fig, 'Fig1.eps', preset, 'eps')
%
% Honors EXACT figure size set by applyPreset (mm × mm per journal preset),
% NOT the auto-cropped axes-only bounding box.
%
% Vector formats (pdf/eps/svg): full PaperSize honored; uses `print -dpdf`
%   (or exportgraphics with 'Padding','figure' on R2022a+).
% Raster formats (png/tif/tiff): uses preset.dpi.

    if nargin < 4
        [~, ~, ext] = fileparts(filepath);
        format = lower(strrep(ext, '.', ''));
    end

    fmt = lower(format);

    switch fmt
        case 'pdf'
            % `print -dpdf` honors PaperSize/PaperPosition set by applyPreset
            % (this is critical for exact journal-mm dimensions).
            set(fig, 'PaperPositionMode', 'manual');
            print(fig, filepath, '-dpdf', '-vector', '-loose');
        case 'eps'
            set(fig, 'PaperPositionMode', 'manual');
            print(fig, filepath, '-depsc', '-vector', '-loose');
        case 'svg'
            % exportgraphics SVG with 'Padding','figure' if supported
            if exportgraphicsHasPadding()
                exportgraphics(fig, filepath, ...
                    'ContentType', 'vector', 'Padding', 'figure', ...
                    'BackgroundColor', 'none');
            else
                set(fig, 'PaperPositionMode', 'manual');
                print(fig, filepath, '-dsvg', '-loose');
            end
        case {'png', 'tif', 'tiff'}
            if exportgraphicsHasPadding()
                exportgraphics(fig, filepath, ...
                    'Resolution', preset.dpi, ...
                    'Padding', 'figure', ...
                    'BackgroundColor', 'white');
            else
                % Fallback: print with explicit DPI
                set(fig, 'PaperPositionMode', 'manual');
                resArg = sprintf('-r%d', preset.dpi);
                if strcmp(fmt, 'png')
                    print(fig, filepath, '-dpng', resArg, '-loose');
                else
                    print(fig, filepath, '-dtiff', resArg, '-loose');
                end
            end
        otherwise
            exportgraphics(fig, filepath, 'Resolution', preset.dpi);
    end
    fprintf('Saved: %s\n', filepath);
end


function tf = exportgraphicsHasPadding()
% True on R2022a+ when exportgraphics gained the 'Padding' name-value.
    persistent cached
    if isempty(cached)
        try
            % Test by parsing the function signature
            cached = ~verLessThan('matlab', '9.12');   % R2022a = 9.12
        catch
            cached = false;
        end
    end
    tf = cached;
end
