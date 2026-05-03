classdef PairedTestVariantsTest < matlab.unittest.TestCase
% Unit tests for the extended hwalker.stats.pairedTest (Cohen's d variants).

    methods (TestClassSetup)
        function addToolboxPath(tc) %#ok<MANU>
            addpath(fullfile(fileparts(mfilename('fullpath')), '..'));
            rng(42);
        end
    end

    methods (Test)

        function testReturnsAllThreeDVariants(tc)
            n = 25;
            pre  = 1.20 + 0.10 * randn(n,1);
            post = 1.10 + 0.10 * randn(n,1);
            r = hwalker.stats.pairedTest(pre, post);

            tc.verifyTrue(isfield(r.cohens_d_variants, 'd_z'));
            tc.verifyTrue(isfield(r.cohens_d_variants, 'd_av'));
            tc.verifyTrue(isfield(r.cohens_d_variants, 'd_rm'));

            tc.verifyTrue(isfinite(r.cohens_d_variants.d_z));
            tc.verifyTrue(isfinite(r.cohens_d_variants.d_av));
            tc.verifyTrue(isfinite(r.cohens_d_variants.d_rm));
        end

        function testCohensD_Default_IsAv(tc)
            n = 20;
            pre  = randn(n,1);
            post = pre + 1.0 + 0.1*randn(n,1);
            r = hwalker.stats.pairedTest(pre, post);
            tc.verifyEqual(r.cohens_d, r.cohens_d_variants.d_av, 'AbsTol', 1e-12);
            tc.verifyMatches(r.cohens_d_type, 'd_av.*');
        end

        function testCohensDz_Formula(tc)
            % d_z = mean(diff) / SD(diff) — direct check
            pre  = [1; 2; 3; 4; 5];
            post = [2; 4; 5; 7; 8];
            d = post - pre;
            expected_dz = mean(d) / std(d);
            r = hwalker.stats.pairedTest(pre, post);
            tc.verifyEqual(r.cohens_d_variants.d_z, expected_dz, 'AbsTol', 1e-12);
        end

        function testCohensDav_Formula(tc)
            % d_av = mean(diff) / mean(SD_pre, SD_post)
            pre  = [10; 11; 12; 13; 14; 15];
            post = [12; 14; 14; 16; 17; 18];
            expected_dav = (mean(post)-mean(pre)) / mean([std(pre), std(post)]);
            r = hwalker.stats.pairedTest(pre, post);
            tc.verifyEqual(r.cohens_d_variants.d_av, expected_dav, 'AbsTol', 1e-12);
        end

        function testCohensDrm_FormulaEquivalence(tc)
            % d_rm = d_z * sqrt(2(1-r))  — when r=0.5 → d_rm == d_z exactly
            % Construct data where corr(pre, post) ≈ 0.5
            n = 100; rng(42);
            pre  = randn(n,1);
            post = 0.5 * pre + sqrt(0.75) * randn(n,1);    % theoretical r ≈ 0.5
            r = hwalker.stats.pairedTest(pre, post);
            expected_drm = r.cohens_d_variants.d_z * sqrt(2*(1 - r.corr));
            tc.verifyEqual(r.cohens_d_variants.d_rm, expected_drm, 'AbsTol', 1e-12);
        end

        function testCIDifferenceBracketsMean(tc)
            n = 30;
            pre  = randn(n,1);
            post = pre + 0.5 + 0.5*randn(n,1);
            r = hwalker.stats.pairedTest(pre, post);
            if isfinite(r.ci_diff(1))
                tc.verifyLessThanOrEqual(   r.ci_diff(1), r.diff_mean);
                tc.verifyGreaterThanOrEqual(r.ci_diff(2), r.diff_mean);
            end
        end

        function testNaNDropping(tc)
            pre  = [1; 2; NaN; 4; 5];
            post = [2; NaN; 5; 6; 7];
            r = hwalker.stats.pairedTest(pre, post);
            tc.verifyEqual(r.n, 3);   % only complete pairs (1,2),(4,6),(5,7)
        end

        function testWarnsOnTooFew(tc)
            tc.verifyWarning(@() hwalker.stats.pairedTest([1; 2], [2; 3]), ...
                'hwalker:pairedTest:tooFew');
        end

        function testRejectsUnequalLength(tc)
            tc.verifyError(@() hwalker.stats.pairedTest([1;2;3], [1;2]), ...
                'hwalker:pairedTest:unequalLength');
        end

        function testPerfectCorrelationConstantShift(tc)
            % Codex finding #4: when b = a + c (constant shift), r=1, diff_std=0
            % but diff_mean ≠ 0.  d_z and d_rm must use d_av as the finite limit.
            n = 30;
            a = randn(n, 1);
            shift = 0.5;
            b = a + shift;            % perfect correlation, constant difference
            r = hwalker.stats.pairedTest(a, b);
            tc.verifyEqual(r.diff_mean, shift, 'AbsTol', 1e-10);
            tc.verifyEqual(r.diff_std, 0,     'AbsTol', 1e-10);
            tc.verifyTrue(isfinite(r.cohens_d_variants.d_av), 'd_av should be finite');
            tc.verifyTrue(isfinite(r.cohens_d_variants.d_z),  'd_z should fall back to d_av (finite)');
            tc.verifyTrue(isfinite(r.cohens_d_variants.d_rm), 'd_rm should fall back to d_av (finite)');
            tc.verifyEqual(r.cohens_d_variants.d_z,  r.cohens_d_variants.d_av, 'AbsTol', 1e-10);
            tc.verifyEqual(r.cohens_d_variants.d_rm, r.cohens_d_variants.d_av, 'AbsTol', 1e-10);
        end

    end
end
