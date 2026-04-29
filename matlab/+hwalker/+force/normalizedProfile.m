function result = normalizedProfile(T, side, hsIdx, validMask, nPoints)
% hwalker.force.normalizedProfile  GCP-normalized force profiles.
%
%   fp = hwalker.force.normalizedProfile(T, 'L', hsIdx, validMask)
%   fp = hwalker.force.normalizedProfile(T, 'L', hsIdx, validMask, 101)
%
% Resamples each stride's force to nPoints (default 101) spanning 0–100% GCP.
%
% Fields returned (for each source 'act' and 'des'):
%   fp.act.individual  (K × nPoints) individual stride profiles
%   fp.act.mean        (1 × nPoints) mean across strides
%   fp.act.std         (1 × nPoints) std  across strides
%   fp.des.*           same for desired force

    if nargin < 5, nPoints = 101; end

    actCol = [side '_ActForce_N'];
    desCol = [side '_DesForce_N'];

    % Initialize output
    result.act.individual = [];
    result.act.mean       = [];
    result.act.std        = [];
    result.des.individual = [];
    result.des.mean       = [];
    result.des.std        = [];

    cols   = {actCol,  desCol};
    fields = {'act',   'des'};
    xNew   = linspace(0, 100, nPoints);
    nStrides = numel(validMask);

    for k = 1:2
        if ~ismember(cols{k}, T.Properties.VariableNames), continue; end
        force    = double(T.(cols{k})(:));
        profiles = zeros(0, nPoints);

        for i = 1:nStrides
            if ~validMask(i), continue; end
            s = double(hsIdx(i));
            e = double(hsIdx(i + 1));
            if e - s < 10, continue; end

            sf = force(s:e-1);
            if all(isnan(sf)), continue; end

            % Fill NaN by linear interpolation
            nanMask = isnan(sf);
            if any(nanMask)
                xOk = find(~nanMask);
                if numel(xOk) >= 2
                    sf(nanMask) = interp1(xOk, sf(~nanMask), find(nanMask), ...
                        'linear', 'extrap');
                else
                    sf(nanMask) = 0;
                end
            end

            xOrig = linspace(0, 100, numel(sf));
            profiles(end+1, :) = interp1(xOrig, sf, xNew, 'linear'); %#ok<AGROW>
        end

        if ~isempty(profiles)
            tmp            = result.(fields{k});
            tmp.individual = profiles;
            tmp.mean       = mean(profiles, 1);
            tmp.std        = std(profiles, 0, 1);
            result.(fields{k}) = tmp;
        end
    end
end
