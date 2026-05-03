classdef StatsAnovaTest < matlab.unittest.TestCase
% Unit tests for hwalker.stats.{anova1, anovaRM, leveneTest, postHoc}.
% Verifies formulas against known-answer datasets and Stats Toolbox results.

    methods (TestClassSetup)
        function addToolboxPath(tc) %#ok<MANU>
            addpath(fullfile(fileparts(mfilename('fullpath')), '..'));
            rng(42);   % reproducible synthetic data
        end
    end

    methods (Test)

        % ============================================================
        %  anova1
        % ============================================================
        function testAnova1_KnownF(tc)
            % Three groups with mean 1, 2, 3 and SD 0.5 (large effect)
            g1 = 1.0 + 0.5 * randn(20, 1);
            g2 = 2.0 + 0.5 * randn(20, 1);
            g3 = 3.0 + 0.5 * randn(20, 1);
            r = hwalker.stats.anova1({g1, g2, g3});
            tc.verifyGreaterThan(r.F, 30, 'F should be very large for 3 distinct means');
            tc.verifyLessThan(r.p, 1e-6);
            tc.verifyEqual(r.df_between, 2);
            tc.verifyEqual(r.df_within,  57);
            tc.verifyGreaterThan(r.eta2, 0.5);
            tc.verifyGreaterThan(r.omega2, 0.5);
            tc.verifyTrue(r.h);
        end

        function testAnova1_NullEffect(tc)
            % Three groups from identical distribution → F should hover near 1, large p
            g1 = randn(30, 1);
            g2 = randn(30, 1);
            g3 = randn(30, 1);
            r = hwalker.stats.anova1({g1, g2, g3});
            tc.verifyLessThan(r.F, 5);     % can fluctuate but not huge
            tc.verifyGreaterThan(r.p, 0.01);
            tc.verifyLessThan(abs(r.eta2), 0.20);
        end

        function testAnova1_MatchesToolbox(tc)
            % Cross-check our formula vs MATLAB's `anova1` if available
            if ~exist('anova1', 'file'), return; end
            g1 = 1.0 + 0.5 * randn(15, 1);
            g2 = 1.5 + 0.5 * randn(15, 1);
            g3 = 2.0 + 0.5 * randn(15, 1);
            mine = hwalker.stats.anova1({g1, g2, g3});
            allD = [g1; g2; g3];
            grp  = [repmat(1,15,1); repmat(2,15,1); repmat(3,15,1)];
            theirP = anova1(allD, grp, 'off');
            tc.verifyEqual(mine.p, theirP, 'AbsTol', 1e-6);
        end

        function testAnova1_GroupNamesPropagate(tc)
            r = hwalker.stats.anova1({1+randn(10,1), 2+randn(10,1)}, ...
                'GroupNames', {'pre','post'});
            tc.verifyEqual(r.group_names, {'pre','post'});
        end

        function testAnova1_RejectsTooFewGroups(tc)
            tc.verifyError(@() hwalker.stats.anova1({1:10}), ...
                'hwalker:anova1:tooFewGroups');
        end

        function testAnova1_AllIdentical(tc)
            % All groups exactly identical → F=0, p=1, eta2=0 (no NaN)
            r = hwalker.stats.anova1({ones(10,1), ones(10,1), ones(10,1)});
            tc.verifyEqual(r.F, 0);
            tc.verifyEqual(r.p, 1);
            tc.verifyEqual(r.eta2, 0);
            tc.verifyFalse(r.h);
        end

        function testAnova1_PerfectSeparation(tc)
            % Zero within-group variance, different group means → F=Inf, p=0
            r = hwalker.stats.anova1({ones(10,1)*1, ones(10,1)*2, ones(10,1)*3});
            tc.verifyTrue(isinf(r.F));
            tc.verifyEqual(r.p, 0);
            tc.verifyEqual(r.eta2, 1);
            tc.verifyTrue(r.h);
        end

        % ============================================================
        %  anovaRM
        % ============================================================
        function testAnovaRM_DistinctConditions(tc)
            n = 12;
            Y = [1.20 + 0.1*randn(n,1), ...
                 1.10 + 0.1*randn(n,1), ...
                 1.00 + 0.1*randn(n,1)];
            r = hwalker.stats.anovaRM(Y);
            tc.verifyEqual(r.K, 3);
            tc.verifyEqual(r.N, n);
            tc.verifyGreaterThan(r.F, 5);
            tc.verifyLessThan(r.p_uncorrected, 0.05);
            tc.verifyGreaterThan(r.eta2_partial, 0.20);
        end

        function testAnovaRM_SphericityClamped(tc)
            % eps_GG must be in [1/(K-1), 1]
            Y = randn(20, 4);
            r = hwalker.stats.anovaRM(Y);
            tc.verifyGreaterThanOrEqual(r.eps_GG, 1/(4-1) - 1e-9);
            tc.verifyLessThanOrEqual(   r.eps_GG, 1 + 1e-9);
        end

        function testAnovaRM_ListwiseDeletion(tc)
            n = 10;
            Y = randn(n, 3);
            Y(3, 2) = NaN;          % subject 3 missing condition 2
            r = hwalker.stats.anovaRM(Y);
            tc.verifyEqual(r.N, n-1);
        end

        function testAnovaRM_RecommendedPSelection(tc)
            % When sphericity OK → use uncorrected; otherwise GG/HF
            Y = randn(20, 3);
            r = hwalker.stats.anovaRM(Y);
            tc.verifyTrue(any(strcmp(r.recommended_label, ...
                {'p_uncorrected (sphericity OK)', ...
                 'p_GG (Greenhouse-Geisser)', ...
                 'p_HF (Huynh-Feldt)'})));
        end

        % ============================================================
        %  leveneTest (Brown-Forsythe)
        % ============================================================
        function testLevene_EqualVariance(tc)
            g1 = randn(50, 1);
            g2 = randn(50, 1);
            g3 = randn(50, 1);
            r = hwalker.stats.leveneTest({g1, g2, g3});
            tc.verifyGreaterThan(r.p, 0.05);
            tc.verifyFalse(r.h);
        end

        function testLevene_UnequalVariance(tc)
            g1 = 0.5 * randn(80, 1);
            g2 = 1.0 * randn(80, 1);
            g3 = 3.0 * randn(80, 1);    % much larger spread
            r = hwalker.stats.leveneTest({g1, g2, g3});
            tc.verifyLessThan(r.p, 0.05);
            tc.verifyTrue(r.h);
        end

        % ============================================================
        %  postHoc
        % ============================================================
        function testPostHoc_PairCount(tc)
            % k=4 groups → 6 pairs
            r = hwalker.stats.postHoc({randn(20,1), randn(20,1), ...
                                       randn(20,1), randn(20,1)});
            tc.verifyEqual(size(r.pairs, 1), 6);
            tc.verifyEqual(numel(r.p_adj), 6);
        end

        function testPostHoc_BonferroniBound(tc)
            % p_adj_Bonf >= p_raw and <= p_raw * m (clamped to 1)
            g1 = 1.0 + 0.5 * randn(20, 1);
            g2 = 2.0 + 0.5 * randn(20, 1);
            g3 = 3.0 + 0.5 * randn(20, 1);
            r = hwalker.stats.postHoc({g1, g2, g3}, 'Method', 'bonferroni');
            m = numel(r.p_adj);
            tc.verifyTrue(all(r.p_adj >= r.p_raw - 1e-12));
            tc.verifyTrue(all(r.p_adj <= min(r.p_raw * m, 1) + 1e-12));
        end

        function testPostHoc_HolmMonotonic(tc)
            % Holm-corrected p-values should be monotone non-decreasing in raw p order
            g1 = 1.0 + 0.5 * randn(20, 1);
            g2 = 1.5 + 0.5 * randn(20, 1);
            g3 = 2.0 + 0.5 * randn(20, 1);
            g4 = 2.5 + 0.5 * randn(20, 1);
            r = hwalker.stats.postHoc({g1,g2,g3,g4}, 'Method', 'holm');
            [~, ord] = sort(r.p_raw);
            sortedAdj = r.p_adj(ord);
            tc.verifyTrue(all(diff(sortedAdj) >= -1e-12));
        end

        function testPostHoc_FDRGivesSmallerThanBonf(tc)
            % BH-FDR p_adj should be <= Bonferroni p_adj
            g1 = randn(20,1); g2 = randn(20,1); g3 = randn(20,1);
            rB = hwalker.stats.postHoc({g1,g2,g3}, 'Method', 'bonferroni');
            rF = hwalker.stats.postHoc({g1,g2,g3}, 'Method', 'fdr');
            tc.verifyTrue(all(rF.p_adj <= rB.p_adj + 1e-12));
        end

    end
end
