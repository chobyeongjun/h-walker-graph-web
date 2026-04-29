classdef StrideTest < matlab.unittest.TestCase
% Unit tests for hwalker.stride.* functions.

    methods (TestClassSetup)
        function addToolboxPath(tc) %#ok<MANU>
            addpath(fullfile(fileparts(mfilename('fullpath')), '..'));
        end
    end

    methods (Test)

        % ---------- detectHS ----------

        function testDetectHS_GCP_3Strides(tc)
            % GCP: 3 strides of 100 samples each at 100 Hz → stride time = 1.0 s
            fs  = 100;
            n   = 400;
            gcp = zeros(n, 1);
            for s = [1, 101, 201, 301]
                gcp(s:s+59) = 1.0;      % 60 samples stance, 40 swing
            end
            T = makeGCPTable(gcp, fs);
            hsIdx = hwalker.stride.detectHS(T, 'L', fs);
            tc.verifyGreaterThanOrEqual(numel(hsIdx), 3);
            % Stride durations should be ~1.0 s
            dt = double(diff(hsIdx)) / fs;
            tc.verifyLessThan(max(abs(dt - 1.0)), 0.05);
        end

        function testDetectHS_EventFallback(tc)
            % No GCP → Event rising edges at 100-sample intervals
            fs = 100;
            n  = 600;
            ev = zeros(n, 1);
            for s = [50, 150, 250, 350, 450]
                ev(s:s+5) = 1;
            end
            T = table((0:n-1)'/fs, ev, ...
                'VariableNames', {'Time_s','L_Event'});
            hsIdx = hwalker.stride.detectHS(T, 'L', fs);
            tc.verifyGreaterThanOrEqual(numel(hsIdx), 3);
        end

        function testDetectHS_EmptyWhenFlat(tc)
            % Constant GCP → no strides
            fs  = 100;
            n   = 200;
            gcp = zeros(n, 1);
            T   = makeGCPTable(gcp, fs);
            hsIdx = hwalker.stride.detectHS(T, 'L', fs);
            tc.verifyEmpty(hsIdx);
        end

        % ---------- filterIQR ----------

        function testFilterIQR_RemovesOutlier(tc)
            times = [1.0; 1.1; 0.9; 1.05; 5.0; 1.0; 1.1];
            [filtered, mask] = hwalker.stride.filterIQR(times);
            tc.verifyFalse(any(filtered > 3.0));
            tc.verifyFalse(mask(5));   % 5.0 s flagged
        end

        function testFilterIQR_TooFew(tc)
            times = [1.0; 1.1; 1.0];
            [filtered, mask] = hwalker.stride.filterIQR(times);
            tc.verifyEqual(numel(filtered), 3);
            tc.verifyTrue(all(mask));
        end

        function testFilterIQR_AbsoluteLower(tc)
            % 0.1 s strides are below the 0.3 s floor → removed
            times = repmat(0.1, 10, 1);
            [filtered, ~] = hwalker.stride.filterIQR(times);
            tc.verifyEmpty(filtered);
        end

        % ---------- lengthZUPT ----------

        function testZUPT_ConstantVelocity_1ms(tc)
            % 1 m/s constant forward velocity → stride length ≈ 1.0 m at 1 s/stride
            fs = 100;
            n  = 400;
            vx  = ones(n, 1);      % L_Ax = global vel X (m/s)
            vy  = zeros(n, 1);     % L_Ay = global vel Y
            gcp = zeros(n, 1);
            for s = [1, 101, 201, 301]
                gcp(s:s+59) = 1.0;
            end
            T = table((0:n-1)'/fs, vx, vy, gcp, ...
                'VariableNames', {'Time_s','L_Ax','L_Ay','L_GCP'});
            hsIdx    = int32([1; 101; 201; 301]);
            validMask = logical([1; 1; 1]);
            lengths  = hwalker.stride.lengthZUPT(T, 'L', hsIdx, validMask, fs);
            valid    = lengths(isfinite(lengths));
            tc.verifyNotEmpty(valid);
            tc.verifyEqual(mean(valid), 1.0, 'AbsTol', 0.05);
        end

        % ---------- cadence formula ----------

        function testCadenceFormula(tc)
            % stride time 1.0 s → cadence = 120 steps/min (2 steps per stride)
            strideTime = 1.0;
            cadence    = 60.0 / strideTime * 2;
            tc.verifyEqual(cadence, 120.0);
        end

        % ---------- stanceSwing ----------

        function testStanceSwing_60pct(tc)
            fs  = 100;
            n   = 200;
            gcp = zeros(n, 1);
            gcp(1:60) = 1.0;   gcp(101:160) = 1.0;   % 60% stance
            T = table((0:n-1)'/fs, gcp, 'VariableNames', {'Time_s','L_GCP'});
            hsIdx     = int32([1; 101]);
            validMask = true(1, 1);
            [stance, swing] = hwalker.stride.stanceSwing(T, 'L', hsIdx, validMask);
            tc.verifyEqual(stance(1), 60.0, 'AbsTol', 1.0);
            tc.verifyEqual(swing(1),  40.0, 'AbsTol', 1.0);
        end

        function testStanceSwing_NoGCP(tc)
            T = table((0:99)'/100, rand(100,1), ...
                'VariableNames', {'Time_s','L_ActForce_N'});
            hsIdx = int32([1; 50]);
            [stance, swing] = hwalker.stride.stanceSwing(T, 'L', hsIdx, true);
            tc.verifyTrue(all(isnan(stance)));
            tc.verifyTrue(all(isnan(swing)));
        end

    end
end

% ---- Helper ----
function T = makeGCPTable(gcp, fs)
    n = numel(gcp);
    T = table((0:n-1)'/fs, gcp, 'VariableNames', {'Time_s','L_GCP'});
end
