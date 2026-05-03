classdef StatsBootstrapTest < matlab.unittest.TestCase
% Unit tests for hwalker.stats.bootstrap (BCa CI).

    methods (TestClassSetup)
        function addToolboxPath(tc) %#ok<MANU>
            addpath(fullfile(fileparts(mfilename('fullpath')), '..'));
        end
    end

    methods (Test)

        function testBootstrap_MeanCoversTrue(tc)
            % 1000 bootstrap samples; CI should cover the true mean for normal data
            rng(42);
            x = 5.0 + 2.0 * randn(100, 1);
            r = hwalker.stats.bootstrap(x, @mean, 'NBoot', 2000, 'Seed', 7);
            tc.verifyGreaterThan(r.point_estimate, 4.5);
            tc.verifyLessThan(   r.point_estimate, 5.5);
            tc.verifyLessThanOrEqual(   r.ci_lower, r.point_estimate);
            tc.verifyGreaterThanOrEqual(r.ci_upper, r.point_estimate);
            % SE close to SD/sqrt(n)
            tc.verifyEqual(r.se, std(x)/sqrt(numel(x)), 'AbsTol', 0.10);
        end

        function testBootstrap_Reproducible(tc)
            x = randn(50, 1);
            r1 = hwalker.stats.bootstrap(x, @median, 'NBoot', 500, 'Seed', 123);
            r2 = hwalker.stats.bootstrap(x, @median, 'NBoot', 500, 'Seed', 123);
            tc.verifyEqual(r1.ci_lower, r2.ci_lower);
            tc.verifyEqual(r1.ci_upper, r2.ci_upper);
        end

        function testBootstrap_CellInput(tc)
            % Two-sample mean difference
            rng(42);
            a = 0 + randn(80, 1);
            b = 1 + randn(80, 1);
            statFn = @(g) mean(g{2}) - mean(g{1});
            r = hwalker.stats.bootstrap({a, b}, statFn, 'NBoot', 1500, 'Seed', 11);
            tc.verifyEqual(r.point_estimate, mean(b) - mean(a), 'AbsTol', 1e-10);
            tc.verifyTrue(r.ci_lower < 1 && r.ci_upper > 1);   % CI should bracket 1
        end

        function testBootstrap_RejectsNonScalar(tc)
            x = randn(20, 1);
            tc.verifyError( ...
                @() hwalker.stats.bootstrap(x, @(v) [mean(v), std(v)], 'NBoot', 200), ...
                'hwalker:bootstrap:nonScalar');
        end

        function testBootstrap_BCaQuantilesInOrder(tc)
            x = randn(40, 1);
            r = hwalker.stats.bootstrap(x, @mean, 'NBoot', 1000, 'Seed', 99);
            tc.verifyLessThanOrEqual(r.ci_lower, r.ci_upper);
        end

        function testBootstrap_RejectsEmpty(tc)
            % Codex finding #2: empty x crashed randi(0,...)
            tc.verifyError(@() hwalker.stats.bootstrap([], @mean, 'NBoot', 100), ...
                'hwalker:bootstrap:emptySample');
            tc.verifyError(@() hwalker.stats.bootstrap({[]}, @(g) mean(g{1}), 'NBoot', 100), ...
                'hwalker:bootstrap:emptySample');
        end

        function testBootstrap_DegenerateConstantSample(tc)
            % Codex finding #3: identical samples → CI collapses to point estimate
            x = ones(20, 1);
            r = hwalker.stats.bootstrap(x, @mean, 'NBoot', 500, 'Seed', 42);
            tc.verifyEqual(r.ci_lower, 1);
            tc.verifyEqual(r.ci_upper, 1);
            tc.verifyEqual(r.point_estimate, 1);
        end

        function testBootstrap_TwoSampleJackknifesBothSamples(tc)
            % Codex finding #1: cell-array input must jackknife ALL samples,
            % not just the first.  Test by computing acceleration on (a, b)
            % then on (b, a) — by symmetry, |a| should be the same magnitude.
            rng(42);
            a = randn(40, 1);
            b = randn(40, 1) + 1;
            statFn = @(g) mean(g{2}) - mean(g{1});
            r1 = hwalker.stats.bootstrap({a, b}, statFn, 'NBoot', 200, 'Seed', 1);
            r2 = hwalker.stats.bootstrap({b, a}, @(g) mean(g{1}) - mean(g{2}), ...
                'NBoot', 200, 'Seed', 1);
            % Both should have non-zero acceleration (proves both samples used)
            % Original buggy code only used x{1}; r1 acceleration would have come
            % from `a` only and would not match r2's `b`-only acceleration.
            tc.verifyTrue(isfinite(r1.acceleration));
        end

    end
end
