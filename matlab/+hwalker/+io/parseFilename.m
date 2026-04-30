function info = parseFilename(filename)
% hwalker.io.parseFilename  Parse H-Walker CSV filename into metadata.
%
% Canonical formats:
%
%   Treadmill:
%     20260430_Robot_CBJ_TD_level_3_0_walker_high_30.csv
%     → date=20260430, source=Robot, subject=CBJ,
%       modality=TD, incline=level, speed=3.0,
%       device=walker, attachment=high, angle=30
%
%   Overground:
%     20260430_Robot_CBJ_OG_walker_low_0.csv
%     → modality=OG, device=walker, attachment=low, angle=0
%
% Result struct fields:
%   .date        'YYYYMMDD' string  ('' if absent)
%   .source      'Robot' / 'Loadcell' / 'Motion'
%   .subject     e.g. 'CBJ'
%   .modality    'TD' (treadmill) | 'OG' (overground) | ''
%   .incline     'level' | 'incline' | '' (TD only)
%   .speed       numeric km/h, e.g. 3.0  (NaN if absent)
%   .device        'walker' | 'noassist' | ''
%   .attachment    'high' | 'middle' | 'low' | ''
%   .angle         numeric degrees, 0 or 30  (NaN if absent)
%   .weightbearing 'wb' | 'nwb' | ''
%   .trial         numeric (NaN if absent) — optional, T01 appended at end
%   .raw           full stem without extension

    [~, stem] = fileparts(filename);
    info.raw           = stem;
    info.date          = '';
    info.source        = '';
    info.subject       = '';
    info.modality      = '';
    info.incline       = '';
    info.speed         = NaN;
    info.device        = '';    % 'walker' | 'noassist'
    info.attachment    = '';    % 'high' | 'middle' | 'low'  (walker only)
    info.angle         = NaN;   % 0 | 30  (walker only)
    info.weightbearing = '';    % 'wb' | 'nwb'  (noassist only)
    info.trial         = NaN;   % numeric, e.g. 1 from T01 (optional)

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

    % --- Subject token: only when date or source was already found ---
    % Guards against 'data.csv' being parsed as subject='data'
    if idx <= numel(parts) && (~isempty(info.date) || ~isempty(info.source))
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
        % Incline condition
        knownInclines = {'level','incline','decline','stair_up','stair_down'};
        % stair_up / stair_down span two underscore tokens → rejoin
        if idx + 1 <= numel(parts) && ...
           ismember([parts{idx} '_' parts{idx+1}], knownInclines)
            info.incline = [parts{idx} '_' parts{idx+1}];
            idx = idx + 2;
        elseif idx <= numel(parts) && ismember(parts{idx}, knownInclines)
            info.incline = parts{idx};
            idx = idx + 1;
        end

        % Speed: two consecutive numeric tokens X_Y → X.Y km/h
        if idx + 1 <= numel(parts) && ...
           ~isempty(regexp(parts{idx},   '^\d+$', 'once')) && ...
           ~isempty(regexp(parts{idx+1}, '^\d+$', 'once'))
            info.speed = str2double(parts{idx}) + ...
                         str2double(parts{idx+1}) * 10^(-numel(parts{idx+1}));
            idx = idx + 2;
        end
    end

    % --- Experimental condition tokens (TD and OG) ---
    %
    % walker conditions (weight bearing implicit):
    %   walker_high_0 / walker_high_30
    %   walker_middle_0 / walker_middle_30
    %   walker_low_0  / walker_low_30
    %
    % noassist conditions:
    %   noassist_wb / noassist_nwb

    if idx <= numel(parts) && strcmp(parts{idx}, 'walker')
        info.device = 'walker';
        idx = idx + 1;

        % attachment: high / middle / low
        if idx <= numel(parts) && ismember(parts{idx}, {'high','middle','low'})
            info.attachment = parts{idx};
            idx = idx + 1;
        end

        % angle: 0 or 30 (only accept known values)
        if idx <= numel(parts) && ismember(parts{idx}, {'0','30'})
            info.angle = str2double(parts{idx});
            idx = idx + 1;  % consume the token
        end

    elseif idx <= numel(parts) && strcmp(parts{idx}, 'noassist')
        info.device = 'noassist';
        idx = idx + 1;

        % weight bearing: wb / nwb
        if idx <= numel(parts) && ismember(parts{idx}, {'wb','nwb'})
            info.weightbearing = parts{idx};
            idx = idx + 1;
        end
    end

    % --- Trial number: optional T## at the end ---
    % Works whether or not it appears: _T01 present → trial=1, absent → trial=NaN
    if idx <= numel(parts)
        trialTok = regexp(parts{end}, '^[Tt](\d+)$', 'tokens', 'once');
        if ~isempty(trialTok)
            info.trial = str2double(trialTok{1});
        end
    end
end
