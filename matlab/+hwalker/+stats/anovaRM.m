function result = anovaRM(Y, varargin)
% hwalker.stats.anovaRM  One-way Repeated-Measures ANOVA + sphericity corrections.
%
%   r = hwalker.stats.anovaRM(Y)
%   r = hwalker.stats.anovaRM(Y, 'ConditionNames', {'baseline','low','high'})
%
% Y : N x K matrix where rows are subjects, columns are conditions.
%     Subjects with ANY missing condition are dropped (listwise deletion);
%     RM-ANOVA requires balanced data per subject.
%
% Computes:
%   - SS_subjects, SS_conditions, SS_error  (Type-III, balanced design)
%   - F_uncorrected with df1=K-1, df2=(N-1)(K-1)
%   - Greenhouse-Geisser epsilon (eps_GG) — sphericity correction
%   - Huynh-Feldt epsilon          (eps_HF) — less conservative variant
%   - Mauchly's test for sphericity (chi-square approximation)
%   - Three p-values: uncorrected, GG-corrected, HF-corrected
%   - Effect sizes:
%       eta2_partial      = SS_cond / (SS_cond + SS_error)
%       eta2_generalized  = SS_cond / (SS_cond + SS_subj + SS_error)
%       cohens_f          = sqrt(eta2_partial / (1 - eta2_partial))
%
% Use the GG-corrected p when sphericity is rejected (Mauchly p < 0.05).
% Use HF correction if Mauchly's eps_GG > 0.75 (less conservative).
%
% References:
%   Greenhouse SW, Geisser S (1959) Psychometrika 24:95-112.
%   Huynh H, Feldt LS (1976) J Educ Stat 1:69-82.
%   Olejnik S, Algina J (2003) Psychol Methods 8:434-447 — generalized eta².

    p = inputParser;
    addParameter(p, 'ConditionNames', {});
    addParameter(p, 'Alpha',          0.05, @(x) isnumeric(x) && isscalar(x) && x>0 && x<1);
    parse(p, varargin{:});
    alpha = p.Results.Alpha;

    assert(ismatrix(Y) && size(Y,2) >= 2, 'hwalker:anovaRM:badShape', ...
        'Y must be N x K matrix with K >= 2 conditions.');

    % Listwise deletion across conditions
    rowOk = all(isfinite(Y), 2);
    Y = Y(rowOk, :);
    [N, K] = size(Y);
    assert(N >= 3, 'hwalker:anovaRM:tooFewSubjects', ...
        'Need >= 3 subjects with complete data; got %d.', N);

    condNames = p.Results.ConditionNames;
    if isempty(condNames)
        condNames = arrayfun(@(j) sprintf('C%d', j), 1:K, 'UniformOutput', false);
    end
    assert(numel(condNames) == K, 'hwalker:anovaRM:nameLengthMismatch', ...
        'ConditionNames length (%d) must equal K (%d).', numel(condNames), K);

    % --- Means ---
    M_subj  = mean(Y, 2);          % N x 1
    M_cond  = mean(Y, 1);          % 1 x K
    M_grand = mean(Y(:));

    % --- Sums of squares (balanced design, Type III == Type I) ---
    SS_total = sum((Y(:) - M_grand).^2);
    SS_subj  = K * sum((M_subj - M_grand).^2);
    SS_cond  = N * sum((M_cond - M_grand).^2);
    SS_error = SS_total - SS_subj - SS_cond;

    df_cond  = K - 1;
    df_error = (N - 1) * (K - 1);
    MS_cond  = SS_cond  / df_cond;
    MS_error = SS_error / df_error;

    % --- Degenerate cases (avoid 0/0 from constant data) ---
    if MS_error < eps && SS_cond < eps
        % All identical → no effect
        F = 0;
    elseif MS_error < eps
        % Perfect separation
        F = Inf;
    else
        F = MS_cond / MS_error;
    end

    % --- Sphericity diagnostics ---
    % Build N x (K-1) "difference contrast" matrix and look at its covariance
    %   Sphericity holds iff the variance of all pairwise differences equals 2*sigma^2.
    % We use an orthonormal contrast (Helmert) to compute eps directly from
    % eigenvalues of the contrast covariance matrix.
    C = orthHelmert(K);                   % K x (K-1)
    Yc = Y - mean(Y, 2);                  % subject-centered (Helmert ignores mean)
    Z  = Yc * C;                          % N x (K-1)
    S  = cov(Z);                          % (K-1) x (K-1)
    lam = eig(S);
    lam = lam(lam > 1e-12);
    if isempty(lam)
        eps_GG = 1; eps_HF = 1; mauchly_p = NaN; W_mauchly = NaN;
    else
        eps_GG = (sum(lam))^2 / ((K-1) * sum(lam.^2));
        eps_GG = max(min(eps_GG, 1), 1/(K-1));   % clamp [1/(K-1), 1]

        % Huynh-Feldt
        num = N * (K-1) * eps_GG - 2;
        den = (K-1) * ((N-1) - (K-1) * eps_GG);
        if den > 0
            eps_HF = min(num / den, 1);
        else
            eps_HF = 1;
        end

        % Mauchly's W and chi-square test
        % W = det(S) / (trace(S)/(K-1))^(K-1)
        try
            W_mauchly = det(S) / (trace(S)/(K-1))^(K-1);
            d = 1 - (2*(K-1)^2 + (K-1) + 2) / (6*(K-1)*(N-1));
            chi2 = -(N-1) * d * log(max(W_mauchly, eps));
            df_chi = (K-1)*K/2 - 1;
            if df_chi > 0
                if exist('chi2cdf', 'file') || exist('chi2cdf', 'builtin')
                    mauchly_p = 1 - chi2cdf(chi2, df_chi);
                else
                    % Fallback via incomplete gamma:  P(X^2 >= x) = gammainc(x/2, df/2, 'upper')
                    mauchly_p = gammainc(chi2/2, df_chi/2, 'upper');
                end
            else
                mauchly_p = NaN;
            end
        catch
            W_mauchly = NaN;  mauchly_p = NaN;
        end
    end

    % --- Three p-values ---
    p_uncorr = fdist_sf(F, df_cond, df_error);
    p_GG     = fdist_sf(F, df_cond * eps_GG, df_error * eps_GG);
    p_HF     = fdist_sf(F, df_cond * eps_HF, df_error * eps_HF);

    % --- Effect sizes (guard against 0/0) ---
    if (SS_cond + SS_error) < eps
        eta2_partial = 0;
    else
        eta2_partial = SS_cond / (SS_cond + SS_error);
    end
    if (SS_cond + SS_subj + SS_error) < eps
        eta2_generalized = 0;
    else
        eta2_generalized = SS_cond / (SS_cond + SS_subj + SS_error);
    end
    cohens_f = sqrt(max(eta2_partial, 0) / max(1 - eta2_partial, eps));

    % --- Pack ---
    result.N                = N;
    result.K                = K;
    result.condition_names  = condNames;
    result.cond_means       = M_cond;
    result.cond_stds        = std(Y, 0, 1);
    result.SS_subjects      = SS_subj;
    result.SS_conditions    = SS_cond;
    result.SS_error         = SS_error;
    result.SS_total         = SS_total;
    result.df_conditions    = df_cond;
    result.df_error         = df_error;
    result.MS_conditions    = MS_cond;
    result.MS_error         = MS_error;
    result.F                = F;
    result.eps_GG           = eps_GG;
    result.eps_HF           = eps_HF;
    result.mauchly_W        = W_mauchly;
    result.mauchly_p        = mauchly_p;
    result.p_uncorrected    = p_uncorr;
    result.p_GG             = p_GG;
    result.p_HF             = p_HF;
    result.alpha            = alpha;
    result.h_uncorrected    = p_uncorr < alpha;
    result.h_GG             = p_GG < alpha;
    result.h_HF             = p_HF < alpha;
    result.eta2_partial     = eta2_partial;
    result.eta2_generalized = eta2_generalized;
    result.cohens_f         = cohens_f;

    % Reporting recommendation
    if isfinite(mauchly_p) && mauchly_p < alpha
        if eps_GG > 0.75
            result.recommended_p    = p_HF;
            result.recommended_label = 'p_HF (Huynh-Feldt)';
        else
            result.recommended_p    = p_GG;
            result.recommended_label = 'p_GG (Greenhouse-Geisser)';
        end
    else
        result.recommended_p    = p_uncorr;
        result.recommended_label = 'p_uncorrected (sphericity OK)';
    end
end


% =====================================================================
%  Helpers
% =====================================================================
function C = orthHelmert(K)
% Orthonormal Helmert-style contrast matrix, K x (K-1)
    C = zeros(K, K-1);
    for j = 1:K-1
        v = zeros(K, 1);
        v(1:j) = 1/j;
        v(j+1) = -1;
        C(:, j) = v / norm(v);
    end
end


function p = fdist_sf(F, df1, df2)
    if ~isfinite(F) || F <= 0 || df1 <= 0 || df2 <= 0
        p = NaN; return
    end
    if exist('fcdf', 'file') || exist('fcdf', 'builtin')
        p = 1 - fcdf(F, df1, df2);
    else
        x = df2 / (df2 + df1 * F);
        p = betainc(x, df2/2, df1/2);
    end
    p = max(min(p, 1), 0);
end
