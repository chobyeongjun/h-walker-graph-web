function info = parseFilename(filename)
% hwalker.io.parseFilename  Parse H-Walker CSV filename into metadata.
%
%   info = hwalker.io.parseFilename('Robot_S01_walk_fast_T03.csv')
%   info.source    = 'Robot'
%   info.subject   = 'S01'
%   info.condition = 'walk_fast'
%   info.trial     = 3
%   info.raw       = 'Robot_S01_walk_fast_T03'
%
% Canonical format: {Source}_{Subject}_{Condition...}_{Trial}.csv
% Heuristic fallback for non-canonical filenames.

    [~, stem] = fileparts(filename);
    info.raw       = stem;
    info.source    = '';
    info.subject   = '';
    info.condition = '';
    info.trial     = NaN;

    parts = strsplit(stem, '_');
    if isempty(parts), return; end

    i = 1;
    % Source token
    knownSources = {'Robot','Motion','Loadcell','IMU','GRF'};
    if ismember(parts{i}, knownSources)
        info.source = parts{i};
        i = i + 1;
    end

    % Subject token: S##, P##, B##, sub## (case-insensitive)
    if i <= numel(parts)
        tok = regexp(parts{i}, '^([SsPpBb])(\d+)$', 'tokens', 'once');
        if ~isempty(tok)
            info.subject = [upper(tok{1}) tok{2}];
            i = i + 1;
        end
    end

    % Trial token: last part matching T## or trial##
    if numel(parts) >= i
        last = parts{end};
        trialTok = regexp(last, '^[Tt](\d+)$', 'tokens', 'once');
        if ~isempty(trialTok)
            info.trial = str2double(trialTok{1});
            condParts = parts(i:end-1);
        else
            condParts = parts(i:end);
        end
        info.condition = strjoin(condParts, '_');
    end
end
