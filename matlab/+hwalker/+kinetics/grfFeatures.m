function feats = grfFeatures(grf, varargin)
% hwalker.kinetics.grfFeatures  Stride-level ground-reaction-force features.
%
%   feats = hwalker.kinetics.grfFeatures(grf)
%   feats = hwalker.kinetics.grfFeatures(grf, 'Threshold', 30)
%
% Input:
%   grf  struct array (one per plate) with .Fx .Fy .Fz .COPx .COPy .Mz .t
%
% Output struct (each field is a vector — one entry per detected stance phase):
%   .stance_start_s       contact onset
%   .stance_stop_s        toe-off
%   .stance_duration_s
%   .peak_vertical_N      Fz peak during stance (1st peak, weight acceptance)
%   .peak_propulsion_N    AP positive peak (Fy or Fx, depending on convention)
%   .impulse_AP_Ns        anteroposterior impulse (integral over stance)
%   .COP_AP_excursion_m   AP COP travel
%   .COP_ML_excursion_m   ML COP travel
%
% Reference: Winter (2009) Biomechanics and Motor Control of Human Movement.

    p = inputParser;
    addParameter(p, 'Threshold', 30, @(x) isnumeric(x) && isscalar(x) && x > 0);
    parse(p, varargin{:});
    thresh = p.Results.Threshold;

    feats = struct();
    feats.stance_start_s     = [];
    feats.stance_stop_s      = [];
    feats.stance_duration_s  = [];
    feats.peak_vertical_N    = [];
    feats.peak_propulsion_N  = [];
    feats.impulse_AP_Ns      = [];
    feats.COP_AP_excursion_m = [];
    feats.COP_ML_excursion_m = [];

    if isempty(grf), return; end

    % Use first plate as primary; (TODO: extend to multi-plate concatenation)
    g = grf(1);
    if ~isfield(g, 'Fz') || isempty(g.Fz), return; end

    Fz = g.Fz(:);
    t  = g.t(:);

    % --- Stance detection (Fz > threshold) ---
    contact = Fz > thresh;
    d = diff([0; contact; 0]);
    starts = find(d == 1);
    stops  = find(d == -1) - 1;

    % Filter: minimum stance duration 100 ms (inclusive — fixes off-by-one
    % flagged by codex pass 9: previously '(stops - starts) >= minDur'
    % dropped contacts of exactly 100 ms because indices count differences
    % between samples, not sample counts).
    fs = 1 / median(diff(t));
    minDurSamples = max(round(0.1 * fs), 1);
    keep = (stops - starts + 1) >= minDurSamples;
    starts = starts(keep);
    stops  = stops(keep);

    nStance = numel(starts);
    if nStance == 0, return; end

    feats.stance_start_s    = t(starts);
    feats.stance_stop_s     = t(stops);
    feats.stance_duration_s = feats.stance_stop_s - feats.stance_start_s;

    feats.peak_vertical_N   = arrayfun(@(s,e) max(Fz(s:e)),  starts, stops);

    % AP propulsion: positive peak of Fy (or Fx if biomech convention swapped)
    if isfield(g, 'Fy') && ~isempty(g.Fy)
        Fap = g.Fy(:);
    elseif isfield(g, 'Fx') && ~isempty(g.Fx)
        Fap = g.Fx(:);
    else
        Fap = [];
    end
    if ~isempty(Fap)
        feats.peak_propulsion_N = arrayfun(@(s,e) max(Fap(s:e)), starts, stops);
        feats.impulse_AP_Ns     = arrayfun(@(s,e) trapz(t(s:e), Fap(s:e)), starts, stops);
    end

    % COP excursion
    if isfield(g, 'COPx') && ~isempty(g.COPx)
        feats.COP_ML_excursion_m = arrayfun(@(s,e) ...
            max(g.COPx(s:e)) - min(g.COPx(s:e)), starts, stops);
    end
    if isfield(g, 'COPy') && ~isempty(g.COPy)
        feats.COP_AP_excursion_m = arrayfun(@(s,e) ...
            max(g.COPy(s:e)) - min(g.COPy(s:e)), starts, stops);
    end
end
