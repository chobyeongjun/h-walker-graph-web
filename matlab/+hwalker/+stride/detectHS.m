function hsIdx = detectHS(T, side, fs)
% hwalker.stride.detectHS  Detect heel-strike indices (1-based) for one side.
%
%   hsIdx = hwalker.stride.detectHS(T, 'L')
%   hsIdx = hwalker.stride.detectHS(T, 'R', fs)
%
% Priority:
%   1. {side}_GCP rising edges (active-segment starts) — primary.
%      GCP sawtooth ramps 0→1+ during stance; rising edge = heel strike.
%   2. {side}_Event rising edges — fallback with stride-plausibility filter.
%      If consecutive edges are tighter than 0.7 s median (step signal,
%      not stride), every other edge is dropped.
%
% Refractory period: 0.3 s (debounce GCP noise at lift-off).

    if nargin < 3, fs = hwalker.io.estimateSampleRate(T); end

    hsIdx    = zeros(0, 1, 'int32');
    gcpCol   = [side '_GCP'];
    eventCol = [side '_Event'];

    % ---- Primary: GCP rising edges ----
    if ismember(gcpCol, T.Properties.VariableNames)
        gcp    = double(T.(gcpCol)(:));
        finite = isfinite(gcp);
        if sum(finite) >= 10
            gcpRange = max(gcp(finite)) - min(gcp(finite));
            if gcpRange >= 0.3
                % Normalize to 0-1 range
                gcpMax = max(gcp(finite));
                if gcpMax > 10
                    gcp = gcp / 100.0;
                elseif gcpMax > 1.5
                    gcp = gcp / gcpMax;
                end

                active = gcp > 0.01;
                d      = diff(int8(active));
                rising = find(d == 1) + 1;  % 1-based: first active sample

                % Refractory: drop a start within 0.3 s of the previous one
                if numel(rising) > 1
                    minGap = max(20, round(fs * 0.3));
                    keep   = [true; diff(rising) > minGap];
                    rising = rising(keep);
                end

                if numel(rising) >= 2
                    hsIdx = int32(rising);
                    return
                end
            end
        end
    end

    % ---- Fallback: Event rising edges ----
    if ismember(eventCol, T.Properties.VariableNames)
        ev  = double(T.(eventCol)(:));
        raw = find(diff(ev) > 0.5) + 1;  % 1-based rising edges
        if numel(raw) >= 2
            % If median gap < 0.7 s → step signal, not stride → keep every 2nd
            minStride = max(round(fs * 0.7), 10);
            if median(diff(raw)) < minStride
                raw = raw(1:2:end);
            end
            hsIdx = int32(raw);
        end
    end
end
