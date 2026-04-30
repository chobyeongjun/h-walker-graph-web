function info = parseFilename(filename)
% hwalker.io.parseFilename  Parse H-Walker CSV filename into metadata.
%
% Canonical formats:
%
%   Treadmill:
%     20260430_Robot_CBJ_TD_level_3_0.csv
%     → date=20260430, source=Robot, subject=CBJ,
%       modality=TD, incline=level, speed=3.0
%
%   Overground:
%     20260430_Robot_CBJ_OG.csv
%     → date=20260430, source=Robot, subject=CBJ, modality=OG
%
% Result struct fields:
%   .date      'YYYYMMDD' string  ('' if absent)
%   .source    'Robot' / 'Loadcell' / 'Motion'  ('' if absent)
%   .subject   e.g. 'CBJ', 'S01'
%   .modality  'TD' (treadmill) | 'OG' (overground) | ''
%   .incline   'level' | 'incline' | '' (TD only)
%   .speed     numeric km/h, e.g. 3.0  (NaN if absent)
%   .raw       full stem without extension

    [~, stem] = fileparts(filename);
    info.raw      = stem;
    info.date     = '';
    info.source   = '';
    info.subject  = '';
    info.modality = '';
    info.incline  = '';
    info.speed    = NaN;

    parts = strsplit(stem, '_');
    if isempty(parts), return; end

    idx = 1;

    % --- Date token: 8-digit YYYYMMDD ---
    if idx <= numel(parts) && ~isempty(regexp(parts{idx}, '^\d{8}$', 'once'))
        info.date = parts{idx};
        idx = idx + 1;
    end

    % --- Source token ---
    knownSources = {'Robot','Motion','Loadcell','IMU','GRF'};
    if idx <= numel(parts) && ismember(parts{idx}, knownSources)
        info.source = parts{idx};
        idx = idx + 1;
    end

    % --- Subject token: any alphanumeric (CBJ, S01, P02, …) ---
    if idx <= numel(parts)
        tok = parts{idx};
        if ~isempty(regexp(tok, '^[A-Za-z][A-Za-z0-9]*$', 'once')) && ...
           ~ismember(tok, {'TD','OG'})
            info.subject = tok;
            idx = idx + 1;
        end
    end

    % --- Modality: TD or OG ---
    if idx <= numel(parts) && ismember(parts{idx}, {'TD','OG'})
        info.modality = parts{idx};
        idx = idx + 1;
    end

    % --- TD-specific tokens: incline + speed ---
    if strcmp(info.modality, 'TD')
        % Incline: non-numeric word (level, incline, decline, …)
        if idx <= numel(parts) && isempty(regexp(parts{idx}, '^\d', 'once'))
            info.incline = parts{idx};
            idx = idx + 1;
        end

        % Speed: two consecutive tokens "X" "_" "Y" → X.Y km/h
        % e.g. parts = {..., '3', '0', ...} → speed = 3.0
        if idx + 1 <= numel(parts) && ...
           ~isempty(regexp(parts{idx},   '^\d+$', 'once')) && ...
           ~isempty(regexp(parts{idx+1}, '^\d+$', 'once'))
            info.speed = str2double(parts{idx}) + ...
                         str2double(parts{idx+1}) * 10^(-numel(parts{idx+1}));
            % idx not advanced — remaining tokens ignored
        end
    end
end
