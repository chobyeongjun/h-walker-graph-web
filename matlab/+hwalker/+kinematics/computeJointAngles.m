function angles = computeJointAngles(motion)
% hwalker.kinematics.computeJointAngles  Sagittal hip/knee/ankle angles from markers.
%
%   angles = hwalker.kinematics.computeJointAngles(motion)
%
% Input:
%   motion  struct from hwalker.io.loadMotion with .markers and .marker_names
%
% Returns struct (each field is N-frame vector or per-stride summary):
%   .t                  time axis
%   .hip_flex_R, .hip_flex_L     hip flexion angle (deg, sagittal)
%   .knee_flex_R, .knee_flex_L   knee flexion (deg, positive = flexion)
%   .ankle_dorsi_R, .ankle_dorsi_L  ankle dorsiflexion (deg)
%   .knee_peak_flex      stride-peak knee flex (vector, populated by ensemble step)
%   .knee_ROM            stride ROM
%   ... etc
%
% Marker convention (Plug-in-Gait or Helen Hayes — auto-tries multiple aliases):
%   Hip:    RASIS, LASIS, RPSIS, LPSIS  (or 'RHIP','LHIP')
%   Knee:   RKNE, LKNE                  (lateral knee marker)
%   Ankle:  RANK, LANK                  (lateral malleolus)
%   Toe:    RTOE, LTOE                  (or 2nd metatarsal head)
%   Heel:   RHEE, LHEE                  (calcaneus)
%
% NOTE: This is a SIMPLIFIED 2D sagittal joint-angle calculation using
% vector geometry between adjacent markers.  For full 3D kinematics
% (e.g., Cardan / Grood-Suntay angles), use OpenSim or Vicon Polygon.
% Sagittal angles here are sufficient for paper-grade gait reporting.

    angles = struct();
    angles.t = motion.t_marker;

    sides = {'R', 'L'};
    for si = 1:2
        side = sides{si};
        % Marker names — try Plug-in-Gait first, fall back to common aliases
        hipName   = pickMarker(motion, {[side 'ASI'], [side 'ASIS'], [side 'HIP']});
        kneeName  = pickMarker(motion, {[side 'KNE'], [side 'KNEE']});
        ankleName = pickMarker(motion, {[side 'ANK'], [side 'ANKLE'], [side 'MAL']});
        toeName   = pickMarker(motion, {[side 'TOE'], [side 'MET2']});
        heelName  = pickMarker(motion, {[side 'HEE'], [side 'HEEL'], [side 'CAL']});

        % Hip flexion: angle between trunk-vertical and thigh (hip→knee) in sagittal plane
        if ~isempty(hipName) && ~isempty(kneeName)
            P_hip = motion.markers.(hipName);
            P_knee = motion.markers.(kneeName);
            % Use Y (anterior) and Z (vertical) — standard biomech axes
            thigh = P_knee(:, [2 3]) - P_hip(:, [2 3]);
            angles.(['hip_flex_' side]) = atan2d(thigh(:,1), -thigh(:,2));
        end

        % Knee flexion: angle between thigh (hip→knee) and shank (knee→ankle)
        if ~isempty(hipName) && ~isempty(kneeName) && ~isempty(ankleName)
            P_hip = motion.markers.(hipName);
            P_knee = motion.markers.(kneeName);
            P_ank = motion.markers.(ankleName);
            thigh_v = P_hip(:, [2 3]) - P_knee(:, [2 3]);
            shank_v = P_ank(:, [2 3]) - P_knee(:, [2 3]);
            cosA = dot(thigh_v, shank_v, 2) ./ ...
                (vecnorm(thigh_v, 2, 2) .* vecnorm(shank_v, 2, 2) + eps);
            angles.(['knee_flex_' side]) = 180 - acosd(max(min(cosA, 1), -1));
        end

        % Ankle dorsiflexion: between shank (knee→ankle) and foot (ankle→toe)
        if ~isempty(kneeName) && ~isempty(ankleName) && ~isempty(toeName)
            P_knee = motion.markers.(kneeName);
            P_ank = motion.markers.(ankleName);
            P_toe = motion.markers.(toeName);
            shank_v = P_knee(:, [2 3]) - P_ank(:, [2 3]);
            foot_v  = P_toe(:, [2 3])  - P_ank(:, [2 3]);
            cosA = dot(shank_v, foot_v, 2) ./ ...
                (vecnorm(shank_v, 2, 2) .* vecnorm(foot_v, 2, 2) + eps);
            angles.(['ankle_dorsi_' side]) = 90 - acosd(max(min(cosA, 1), -1));
        end
    end

    % --- Whole-trial summaries (per-side, no overwrite) ---
    %  Codex pass 9 fix: previously knee_peak_flex etc. were single fields
    %  so the L computation overwrote R.  Now keyed by side.
    %  These are TRIAL-LEVEL summaries.  For TRUE per-stride values pass
    %  stride boundaries to hwalker.experiment.extractStrideFeatures (TODO).
    for side = {'R', 'L'}
        knFld = ['knee_flex_' side{1}];
        hpFld = ['hip_flex_'  side{1}];
        anFld = ['ankle_dorsi_' side{1}];
        if isfield(angles, knFld)
            angles.(['knee_peak_flex_' side{1}]) = max(angles.(knFld), [], 'omitnan');
            angles.(['knee_ROM_'       side{1}]) = max(angles.(knFld), [], 'omitnan') - ...
                                                   min(angles.(knFld), [], 'omitnan');
        end
        if isfield(angles, hpFld)
            angles.(['hip_peak_flex_'  side{1}]) = max(angles.(hpFld), [], 'omitnan');
            angles.(['hip_ROM_'        side{1}]) = max(angles.(hpFld), [], 'omitnan') - ...
                                                   min(angles.(hpFld), [], 'omitnan');
        end
        if isfield(angles, anFld)
            angles.(['ankle_peak_dorsi_' side{1}]) = max(angles.(anFld), [], 'omitnan');
            angles.(['ankle_ROM_'        side{1}]) = max(angles.(anFld), [], 'omitnan') - ...
                                                     min(angles.(anFld), [], 'omitnan');
        end
    end
end


function nm = pickMarker(motion, candidates)
% Find first matching marker in motion.markers struct.
    nm = '';
    fnames = fieldnames(motion.markers);
    for i = 1:numel(candidates)
        cand = matlab.lang.makeValidName(candidates{i});
        idx = find(strcmpi(fnames, cand), 1);
        if ~isempty(idx)
            nm = fnames{idx};
            return
        end
    end
end
