function kind = detectSourceKind(filepath)
% hwalker.io.detectSourceKind  Classify CSV by column signature.
%
%   kind = hwalker.io.detectSourceKind('/path/to/file.csv')
%
% Returns:
%   'Robot'     — has L_GCP / R_GCP (main control + IMU CSV)
%   'Loadcell'  — has L_DesForce_N but NO GCP column
%   'Motion'    — has motion-capture position columns
%   'Unknown'   — none of the above (or unreadable)

    try
        opts = detectImportOptions(filepath, 'Delimiter', ',');
        cols = opts.VariableNames;
    catch
        kind = 'Unknown';
        return
    end

    hasGCP    = any(ismember({'L_GCP','R_GCP'}, cols));
    hasForce  = any(ismember({'L_DesForce_N','R_DesForce_N','L_ActForce_N'}, cols));
    hasMotion = any(contains(cols, 'Marker')) || ...
                any(ismember(cols, {'PelvisX','PelvisY','PelvisZ'}));

    if hasGCP
        kind = 'Robot';
    elseif hasForce
        kind = 'Loadcell';
    elseif hasMotion
        kind = 'Motion';
    else
        kind = 'Unknown';
    end
end
