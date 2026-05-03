classdef FilterIQRReasonsTest < matlab.unittest.TestCase
% Tests for the new third return value (reasons struct) of filterIQR.

    methods (TestClassSetup)
        function addToolboxPath(tc) %#ok<MANU>
            addpath(fullfile(fileparts(mfilename('fullpath')), '..'));
        end
    end

    methods (Test)

        function testReasonsStructShape(tc)
            times = [1.0; 1.1; 0.9; 1.05; 5.0; 1.0; 1.1];
            [~, ~, why] = hwalker.stride.filterIQR(times);
            for f = {'nTotal','nKept','nOutlierIQR','nBelowBound','nAboveBound', ...
                     'multiplier','boundsRequested','boundsEffective'}
                tc.verifyTrue(isfield(why, f{1}), ...
                    sprintf('reasons missing field %s', f{1}));
            end
            tc.verifyEqual(why.nTotal, 7);
        end

        function testCountsAddUp(tc)
            times = [0.1; 0.2; 1.0; 1.1; 1.05; 0.95; 1.2; 7.0; 8.0; 1.1];
            [~, ~, why] = hwalker.stride.filterIQR(times);
            tc.verifyEqual(why.nKept + why.nOutlierIQR + why.nBelowBound + why.nAboveBound, ...
                why.nTotal);
        end

        function testBelowBoundCategorized(tc)
            times = [0.1; 0.15; 1.0; 1.05; 1.1; 0.98; 1.02];   % 2 below 0.3
            [~, ~, why] = hwalker.stride.filterIQR(times);
            tc.verifyEqual(why.nBelowBound, 2);
        end

        function testAboveBoundCategorized(tc)
            times = [1.0; 1.1; 1.05; 0.95; 1.02; 6.0; 7.0];     % 2 above 5.0
            [~, ~, why] = hwalker.stride.filterIQR(times);
            tc.verifyEqual(why.nAboveBound, 2);
        end

        function testCustomBounds(tc)
            % With wider bounds [0.1, 10.0], the previously-excluded 7.0 is kept
            times = [1.0; 1.1; 1.05; 0.95; 1.02; 6.0; 7.0];
            [filt, ~, why] = hwalker.stride.filterIQR(times, ...
                'Bounds', [0.1, 10.0]);
            tc.verifyEqual(why.nAboveBound, 0);
            tc.verifyEqual(why.boundsRequested, [0.1, 10.0]);
            tc.verifyTrue(any(filt > 5.0));   % 6 or 7 should survive (subject to IQR)
        end

        function testLegacyPositionalMultiplier(tc)
            % filterIQR(times, 2.0) still works via backward-compat shim
            times = [1.0; 1.1; 0.9; 1.05; 1.0; 1.1];
            [filt, ~, why] = hwalker.stride.filterIQR(times, 2.0);
            tc.verifyEqual(why.multiplier, 2.0);
            tc.verifyEqual(numel(filt), 6);
        end

        function testCustomMultiplier(tc)
            times = [1.0; 1.1; 0.9; 1.05; 5.0; 1.0; 1.1];
            % With smaller multiplier (e.g. 0.5), the 5.0 outlier is more aggressively excluded
            [~, ~, why] = hwalker.stride.filterIQR(times, 'Multiplier', 0.5);
            tc.verifyEqual(why.multiplier, 0.5);
        end

        function testRejectsBadBounds(tc)
            tc.verifyError( ...
                @() hwalker.stride.filterIQR([1;2;3;4], 'Bounds', [5, 1]), ...
                'MATLAB:InputParser:ArgumentFailedValidation');
        end

        function testNFewerThan4Untouched(tc)
            times = [1.0; 1.1; 0.9];
            [filt, mask, why] = hwalker.stride.filterIQR(times);
            tc.verifyEqual(numel(filt), 3);
            tc.verifyTrue(all(mask));
            tc.verifyEqual(why.nKept, 3);
        end

    end
end
