classdef ForceTest < matlab.unittest.TestCase
% Unit tests for hwalker.force.* functions.

    methods (TestClassSetup)
        function addToolboxPath(tc) %#ok<MANU>
            addpath(fullfile(fileparts(mfilename('fullpath')), '..'));
        end
    end

    methods (Test)

        % ---------- trackingError ----------

        function testTracking_PerfectTracking(tc)
            % Des == Act → RMSE = 0
            n   = 200;
            des = sin(linspace(0, 2*pi, n))';
            T   = makeForceTable(n, des, des);
            hsIdx = int32([1; 101]);
            ft = hwalker.force.trackingError(T, 'L', hsIdx, true(1,1));
            tc.verifyEqual(ft.rmse, 0.0, 'AbsTol', 1e-10);
            tc.verifyEqual(ft.mae,  0.0, 'AbsTol', 1e-10);
        end

        function testTracking_ConstantOffset5N(tc)
            % Act = Des + 5 → RMSE = MAE = 5
            n   = 200;
            des = zeros(n, 1);
            act = ones(n, 1) * 5;
            T   = makeForceTable(n, des, act);
            hsIdx = int32([1; 101]);
            ft = hwalker.force.trackingError(T, 'L', hsIdx, true(1,1));
            tc.verifyEqual(ft.rmse, 5.0, 'AbsTol', 0.01);
            tc.verifyEqual(ft.mae,  5.0, 'AbsTol', 0.01);
            tc.verifyEqual(ft.peakError, 5.0, 'AbsTol', 0.01);
        end

        function testTracking_MissingColumns(tc)
            T = table((0:99)'/100, 'VariableNames', {'Time_s'});
            hsIdx = int32([1; 50]);
            ft = hwalker.force.trackingError(T, 'L', hsIdx, true(1,1));
            tc.verifyEqual(ft.rmse,      0.0);
            tc.verifyEqual(ft.mae,       0.0);
            tc.verifyEqual(ft.peakError, 0.0);
        end

        function testTracking_PerStrideRMSE(tc)
            % Two strides with different offsets → perStride RMSE differs
            n   = 200;
            des = zeros(n, 1);
            act = [ones(100,1)*3; ones(100,1)*7];
            T   = makeForceTable(n, des, act);
            hsIdx = int32([1; 101; 201]);
            ft = hwalker.force.trackingError(T, 'L', hsIdx, logical([1;1]));
            tc.verifyEqual(numel(ft.rmsePerStride), 2);
            tc.verifyEqual(ft.rmsePerStride(1), 3.0, 'AbsTol', 0.01);
            tc.verifyEqual(ft.rmsePerStride(2), 7.0, 'AbsTol', 0.01);
        end

        % ---------- normalizedProfile ----------

        function testProfile_OutputShape(tc)
            n   = 300;
            des = ones(n, 1) * 10;
            act = ones(n, 1) * 12;
            T   = makeForceTable(n, des, act);
            hsIdx = int32([1; 101; 201]);
            fp = hwalker.force.normalizedProfile(T, 'L', hsIdx, logical([1;1]));
            tc.verifyEqual(size(fp.act.individual, 2), 101);
            tc.verifyEqual(size(fp.act.individual, 1), 2);
        end

        function testProfile_MeanConstant(tc)
            % Constant force → mean profile = constant
            n   = 200;
            des = zeros(n, 1);
            act = ones(n, 1) * 8;
            T   = makeForceTable(n, des, act);
            hsIdx = int32([1; 101]);
            fp = hwalker.force.normalizedProfile(T, 'L', hsIdx, true(1,1));
            tc.verifyEqual(mean(fp.act.mean), 8.0, 'AbsTol', 0.1);
        end

        function testProfile_MissingColumns(tc)
            T = table((0:99)'/100, 'VariableNames', {'Time_s'});
            hsIdx = int32([1; 50]);
            fp = hwalker.force.normalizedProfile(T, 'L', hsIdx, true(1,1));
            tc.verifyEmpty(fp.act.individual);
            tc.verifyEmpty(fp.des.individual);
        end

    end
end

% ---- Helper ----
function T = makeForceTable(n, des, act)
    T = table((0:n-1)'/100, des, act, ...
        'VariableNames', {'Time_s','L_DesForce_N','L_ActForce_N'});
end
