function motion = loadMotion(filepath, varargin)
% hwalker.io.loadMotion  Load motion-capture data (markers + GRF) from C3D / TSV / CSV.
%
%   motion = hwalker.io.loadMotion('motion.c3d')
%   motion = hwalker.io.loadMotion('motion.csv')
%   motion = hwalker.io.loadMotion('qualisys.tsv', 'FillGaps', true)
%   motion = hwalker.io.loadMotion(file, 'MarkerSet', 'plug-in-gait', ...
%                                       'GRFInside', true, ...
%                                       'CutoffMarker', 6, 'CutoffGRF', 20)
%
% Auto-detects format:
%   .c3d  → uses ezc3d MATLAB binding if available (recommended); falls back
%           to a minimal native parser sufficient for marker + GRF channels.
%   .tsv  → Qualisys QTM export (header + ROW data).
%   .csv  → Generic table; columns matching marker name conventions auto-grouped.
%
% Returns struct:
%   .source_file
%   .fs_marker          marker sample rate (Hz)
%   .fs_grf             force-plate sample rate (Hz, can differ from marker)
%   .t_marker           marker time axis (s)
%   .t_grf              GRF time axis (s)
%   .markers            struct: each field = marker name → N x 3 array (X,Y,Z mm)
%   .marker_names       cellstr
%   .grf                struct array, one per plate:
%                         .Fx .Fy .Fz   (N)
%                         .COPx .COPy   (m)
%                         .Mz           (Nm)
%   .events             cellstr or struct (HS / TO if exported)
%   .units              struct .marker = 'mm'|'m', .grf = 'N'
%   .sync_signal        if a digital sync channel detected
%   .qc                 struct .marker_dropouts, .gap_max_ms, .nan_pct
%
% Filtering applied (zero-phase Butterworth, 4th order):
%   markers: 6 Hz low-pass (Winter 2009 default)
%   GRF:     20 Hz low-pass
%
% Customize via name-value:
%   'FillGaps'      true (default) — spline interpolate gaps < GapMaxMs
%   'GapMaxMs'      100 ms (default)
%   'CutoffMarker'  6 Hz (default)
%   'CutoffGRF'     20 Hz (default)
%   'MarkerSet'     'plug-in-gait' | 'helen-hayes' | 'generic' (informational)
%   'GRFInside'     true if GRF embedded in C3D (default true for c3d)

    p = inputParser;
    addParameter(p, 'FillGaps',     true,   @islogical);
    addParameter(p, 'GapMaxMs',     100,    @(x) isnumeric(x) && isscalar(x) && x > 0);
    addParameter(p, 'CutoffMarker', 6.0,    @(x) isnumeric(x) && isscalar(x) && x > 0);
    addParameter(p, 'CutoffGRF',    20.0,   @(x) isnumeric(x) && isscalar(x) && x > 0);
    addParameter(p, 'MarkerSet',    'generic');
    addParameter(p, 'GRFInside',    true,   @islogical);
    parse(p, varargin{:});

    motion = struct( ...
        'source_file',  filepath, ...
        'fs_marker',    NaN, ...
        'fs_grf',       NaN, ...
        't_marker',     [], ...
        't_grf',        [], ...
        'markers',      struct(), ...
        'marker_names', {{}}, ...
        'grf',          struct([]), ...
        'events',       {{}}, ...
        'units',        struct('marker','mm','grf','N'), ...
        'sync_signal',  [], ...
        'qc',           struct('marker_dropouts',0,'gap_max_ms',0,'nan_pct',0));

    if ~exist(filepath, 'file')
        error('hwalker:loadMotion:notFound', 'File not found: %s', filepath);
    end

    [~, ~, ext] = fileparts(filepath);
    switch lower(ext)
        case '.c3d', motion = loadC3D(filepath, motion, p.Results);
        case '.tsv', motion = loadQualisysTSV(filepath, motion, p.Results);
        case '.csv', motion = loadGenericCSV(filepath, motion, p.Results);
        otherwise
            error('hwalker:loadMotion:badExt', ...
                'Unsupported extension ''%s''. Use .c3d, .tsv, or .csv.', ext);
    end

    % Filter + fill gaps + QC
    motion = postProcess(motion, p.Results);

    fprintf('[loadMotion] %s — %d markers @ %g Hz, %d plate(s) @ %g Hz, %.2fs\n', ...
        filepath, numel(motion.marker_names), motion.fs_marker, ...
        numel(motion.grf), motion.fs_grf, ...
        motion.t_marker(end) - motion.t_marker(1));
end


% =====================================================================
%  Format-specific loaders
% =====================================================================

function motion = loadC3D(filepath, motion, opts)
% C3D loader.  Tries ezc3d binding first (fast, complete); falls back to
% a minimal native parser that reads marker + analog channels only.
    if exist('ezc3dRead', 'file')
        try
            c = ezc3dRead(filepath);
            motion.fs_marker = c.parameters.POINT.RATE.DATA;
            nFr = size(c.data.points, 3);
            motion.t_marker = (0:nFr-1)' / motion.fs_marker;

            labels = c.parameters.POINT.LABELS.DATA;
            for i = 1:numel(labels)
                pts = squeeze(c.data.points(1:3, i, :));   % 3 x N
                motion.markers.(makeFieldName(labels{i})) = pts';
                motion.marker_names{end+1} = labels{i};
            end

            if isfield(c.data, 'analogs') && opts.GRFInside
                motion.fs_grf = c.parameters.ANALOG.RATE.DATA;
                nFrA = size(c.data.analogs, 3);
                motion.t_grf = (0:nFrA-1)' / motion.fs_grf;
                motion.grf = parseGRFAnalogs(c, motion.t_grf);
            end
            return
        catch ME
            warning('hwalker:loadMotion:ezc3dFail', ...
                'ezc3dRead failed (%s); trying native parser.', ME.message);
        end
    end
    % Native fallback parser
    motion = loadC3DNative(filepath, motion);
end


function motion = loadC3DNative(filepath, motion)
% Minimal native C3D parser (Vicon C3D format spec, integer-frame data).
% Sufficient for marker positions + analog channels; NOT a full implementation.
    fid = fopen(filepath, 'rb', 'l');
    if fid < 0
        error('hwalker:loadMotion:openFail', 'Cannot open %s', filepath);
    end
    cleanup = onCleanup(@() fclose(fid));

    parameterStartBlock = fread(fid, 1, 'uint8');
    fread(fid, 1, 'uint8');                              %#ok<NASGU>  % 0x50
    nMarkers = fread(fid, 1, 'uint16=>double');
    nAnalog  = fread(fid, 1, 'uint16=>double');
    firstFrame = fread(fid, 1, 'uint16=>double');
    lastFrame  = fread(fid, 1, 'uint16=>double');
    fread(fid, 1, 'uint16');                              %#ok<NASGU>  % max gap
    scaleFactor = fread(fid, 1, 'single=>double');
    fread(fid, 1, 'uint16');                              %#ok<NASGU>  % data start block
    nAnalogPerFrame = fread(fid, 1, 'uint16=>double');
    fs_marker = fread(fid, 1, 'single=>double');

    nFrames = lastFrame - firstFrame + 1;

    motion.fs_marker = fs_marker;
    if nAnalogPerFrame > 0
        motion.fs_grf = fs_marker * nAnalogPerFrame;
    else
        motion.fs_grf = NaN;
    end
    motion.t_marker = (0:nFrames-1)' / fs_marker;

    if nAnalogPerFrame > 0 && ~isnan(motion.fs_grf)
        nA = nFrames * nAnalogPerFrame;
        motion.t_grf = (0:nA-1)' / motion.fs_grf;
    end

    % Names from parameter section (block 2)
    fseek(fid, (parameterStartBlock - 1) * 512, 'bof');
    fread(fid, 4, 'uint8');                               %#ok<NASGU>
    paramBlock = fread(fid, 512 - 4, 'uint8=>uint8');
    labels = extractLabels(paramBlock, nMarkers);

    if numel(labels) < nMarkers
        % Fallback names
        labels = arrayfun(@(i) sprintf('M%02d', i), 1:nMarkers, 'UniformOutput', false);
    end

    % Marker data block
    dataStartByte = (parameterStartBlock - 1) * 512 + 512;   % approximate
    fseek(fid, dataStartByte, 'bof');
    dataBytesPerFrame = (nMarkers * 4 + nAnalogPerFrame) * 4;   % integer or float
    rawAll = fread(fid, dataBytesPerFrame * nFrames / 4, 'single=>double');
    if numel(rawAll) < nMarkers * 4 * nFrames
        warning('hwalker:loadMotion:c3dShort', 'C3D data block shorter than expected.');
        motion.markers = struct();
        return
    end
    rawAll = reshape(rawAll, [4 + nAnalogPerFrame/4, nMarkers, nFrames]);
    if scaleFactor > 0
        coords = squeeze(rawAll(1:3, :, :)) * scaleFactor;
    else
        coords = squeeze(rawAll(1:3, :, :));
    end

    for i = 1:nMarkers
        nm  = makeFieldName(labels{i});
        pts = squeeze(coords(:, i, :))';                  % N x 3
        motion.markers.(nm) = pts;
        motion.marker_names{end+1} = labels{i};
    end
    % NOTE: This native parser is BEST-EFFORT.  For production, install ezc3d.
end


function motion = loadQualisysTSV(filepath, motion, ~)
% Qualisys QTM standard TSV export.
% Header lines (key-value), then column header row, then data.
    fid = fopen(filepath, 'r');
    if fid < 0, error('hwalker:loadMotion:openFail', 'Cannot open %s', filepath); end
    cleanup = onCleanup(@() fclose(fid));

    nMarkers = 0;
    fs = 200;
    while true
        line = fgetl(fid);
        if ~ischar(line), break; end
        if isempty(strtrim(line)), continue; end
        parts = strsplit(line, '\t');
        if numel(parts) >= 2
            switch lower(parts{1})
                case 'frequency',    fs = str2double(parts{2});
                case 'no_of_markers',nMarkers = str2double(parts{2});
                case 'marker_names'
                    motion.marker_names = parts(2:end);
            end
        end
        if startsWith(line, 'Frame')   % column header row
            break
        end
    end

    motion.fs_marker = fs;
    raw = fscanf(fid, '%f', [2 + nMarkers*3, Inf])';
    motion.t_marker = raw(:, 2);
    if isempty(motion.t_marker)
        motion.t_marker = (0:size(raw,1)-1)' / fs;
    end

    coords = raw(:, 3:end);   % N x (nMarkers*3)
    if isempty(motion.marker_names)
        motion.marker_names = arrayfun(@(i) sprintf('M%02d', i), 1:nMarkers, 'UniformOutput', false);
    end
    for i = 1:nMarkers
        cs = (i-1)*3 + (1:3);
        motion.markers.(makeFieldName(motion.marker_names{i})) = coords(:, cs);
    end
end


function motion = loadGenericCSV(filepath, motion, ~)
% Generic CSV: column 'Time' + 'Marker_X', 'Marker_Y', 'Marker_Z' triplets.
    T = readtable(filepath, 'VariableNamingRule', 'preserve');
    cols = T.Properties.VariableNames;

    % Time
    timeColIdx = find(contains(lower(cols), {'time','t_s','timestamp'}), 1);
    if isempty(timeColIdx)
        warning('hwalker:loadMotion:noTime', 'No time column; assuming 200 Hz.');
        motion.fs_marker = 200;
        motion.t_marker  = (0:height(T)-1)' / 200;
    else
        motion.t_marker = T{:, timeColIdx};
        if max(motion.t_marker) > 1000
            motion.t_marker = motion.t_marker / 1000;     % ms → s heuristic
        end
        dt = diff(motion.t_marker);
        motion.fs_marker = 1 / median(dt(dt > 0));
    end

    % Find triplets *_X *_Y *_Z
    xCols = find(endsWith(cols, '_X'));
    for ci = xCols(:)'
        baseName = cols{ci}(1:end-2);
        yCol = find(strcmp(cols, [baseName '_Y']), 1);
        zCol = find(strcmp(cols, [baseName '_Z']), 1);
        if ~isempty(yCol) && ~isempty(zCol)
            pts = [T{:, ci}, T{:, yCol}, T{:, zCol}];
            motion.markers.(makeFieldName(baseName)) = pts;
            motion.marker_names{end+1} = baseName;
        end
    end
end


% =====================================================================
function grf = parseGRFAnalogs(c, t_grf)
% Try to parse standard GRF channel naming from a C3D's analog block.
% Looks for groups Fx1/Fy1/Fz1/COPx1/COPy1/Mz1 (plate 1), Fx2... (plate 2).
    grf = struct([]);
    if ~isfield(c.parameters,'ANALOG') || ~isfield(c.parameters.ANALOG,'LABELS')
        return
    end
    labels = c.parameters.ANALOG.LABELS.DATA;
    data   = squeeze(c.data.analogs(1, :, :))';   % N x nChannels
    nPlates = sum(startsWith(labels, 'Fz'));
    for k = 1:nPlates
        sk = num2str(k);
        plate.Fx = data(:, find(strcmpi(labels, ['Fx' sk]), 1));
        plate.Fy = data(:, find(strcmpi(labels, ['Fy' sk]), 1));
        plate.Fz = data(:, find(strcmpi(labels, ['Fz' sk]), 1));
        copxIdx = find(strcmpi(labels, ['COPx' sk]) | strcmpi(labels, ['Cx' sk]), 1);
        copyIdx = find(strcmpi(labels, ['COPy' sk]) | strcmpi(labels, ['Cy' sk]), 1);
        mzIdx   = find(strcmpi(labels, ['Mz' sk]), 1);
        if ~isempty(copxIdx), plate.COPx = data(:, copxIdx); end
        if ~isempty(copyIdx), plate.COPy = data(:, copyIdx); end
        if ~isempty(mzIdx),   plate.Mz   = data(:, mzIdx);   end
        plate.t = t_grf;
        if k == 1, grf = plate; else, grf(k) = plate; end       %#ok<AGROW>
    end
end


function motion = postProcess(motion, opts)
    % --- Marker filter + gap fill + QC ---
    fnames = fieldnames(motion.markers);
    nFr = numel(motion.t_marker);
    totalNaN = 0;  maxGap = 0;
    fc = opts.CutoffMarker;
    fs = motion.fs_marker;
    if isfinite(fs) && fs > 2 * fc
        [b, a] = butter(4, fc / (fs/2));
    else
        b = []; a = [];
    end

    for i = 1:numel(fnames)
        m = motion.markers.(fnames{i});
        nan_mask = any(isnan(m), 2);
        gaps = findGaps(nan_mask);
        if ~isempty(gaps)
            gapMaxMs = max(gaps) / fs * 1000;
            maxGap = max(maxGap, gapMaxMs);
            if opts.FillGaps && gapMaxMs <= opts.GapMaxMs
                for c = 1:3
                    v = m(:, c);
                    okIdx = ~isnan(v);
                    if sum(okIdx) > 3
                        m(:, c) = interp1(find(okIdx), v(okIdx), (1:nFr)', 'spline', NaN);
                    end
                end
            end
        end
        totalNaN = totalNaN + sum(any(isnan(m), 2));
        if ~isempty(b)
            for c = 1:3
                v = m(:, c);
                ok = isfinite(v);
                if sum(ok) > 12
                    m(ok, c) = filtfilt(b, a, v(ok));
                end
            end
        end
        motion.markers.(fnames{i}) = m;
    end
    motion.qc.marker_dropouts = totalNaN;
    motion.qc.gap_max_ms      = maxGap;
    motion.qc.nan_pct = 100 * totalNaN / max(nFr * numel(fnames), 1);

    % --- GRF filter ---
    if ~isempty(motion.grf) && isfinite(motion.fs_grf)
        fcG = opts.CutoffGRF;
        if motion.fs_grf > 2 * fcG
            [bg, ag] = butter(4, fcG / (motion.fs_grf/2));
            for k = 1:numel(motion.grf)
                for fld = {'Fx','Fy','Fz','COPx','COPy','Mz'}
                    if isfield(motion.grf(k), fld{1}) && ~isempty(motion.grf(k).(fld{1}))
                        v = motion.grf(k).(fld{1});
                        ok = isfinite(v);
                        if sum(ok) > 12
                            v(ok) = filtfilt(bg, ag, v(ok));
                            motion.grf(k).(fld{1}) = v;
                        end
                    end
                end
            end
        end
    end
end


function gaps = findGaps(mask)
% Lengths of contiguous runs of `true` in mask.
    d = diff([0; mask(:); 0]);
    starts = find(d == 1);
    ends   = find(d == -1) - 1;
    gaps = ends - starts + 1;
end


function nm = makeFieldName(s)
% Convert any string to a valid MATLAB struct fieldname.
    nm = matlab.lang.makeValidName(s);
end


function labels = extractLabels(paramBlock, nMarkers)
% Best-effort string scan from C3D parameter block.
    labels = {};
    raw = char(paramBlock(:)');
    tokens = regexp(raw, '[A-Za-z][A-Za-z0-9_]{2,15}', 'match');
    for i = 1:min(nMarkers, numel(tokens))
        labels{end+1} = tokens{i};                                 %#ok<AGROW>
    end
end
