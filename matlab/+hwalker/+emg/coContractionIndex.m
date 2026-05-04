function CCI = coContractionIndex(envAgonist, envAntagonist, varargin)
% hwalker.emg.coContractionIndex  Falconer-Winter co-contraction index.
%
%   CCI = hwalker.emg.coContractionIndex(envAgonist, envAntagonist)
%
% Formula (Falconer & Winter 1985, J Electromyogr Kinesiol):
%
%   CCI = 2 * sum_i  min(EMG_ag(i), EMG_ant(i))   /
%             sum_i (EMG_ag(i) + EMG_ant(i))         * 100   (%)
%
% Both inputs should be ENVELOPES (rectified + smoothed), ideally MVC-normalized.
% Returns scalar 0-100 %.  100 = perfect co-contraction; 0 = pure reciprocal.
%
% Example:
%   ta_env = emg.envelope(:, find(strcmp(emg.channel_names,'R_TibAnt')));
%   gl_env = emg.envelope(:, find(strcmp(emg.channel_names,'R_GastrocLat')));
%   cci = hwalker.emg.coContractionIndex(ta_env, gl_env);

    p = inputParser;
    addParameter(p, 'IndexRange', []);
    parse(p, varargin{:});
    rng = p.Results.IndexRange;

    a = envAgonist(:);
    b = envAntagonist(:);
    if numel(a) ~= numel(b)
        error('hwalker:coContractionIndex:lengthMismatch', ...
            'Agonist and antagonist envelopes must be same length.');
    end
    if ~isempty(rng)
        a = a(rng);
        b = b(rng);
    end

    ok = isfinite(a) & isfinite(b);
    a = a(ok);  b = b(ok);
    if isempty(a)
        CCI = NaN;
        return
    end

    num = 2 * sum(min(a, b));
    den = sum(a + b);
    if den < eps
        CCI = 0;
    else
        CCI = num / den * 100;
    end
end
