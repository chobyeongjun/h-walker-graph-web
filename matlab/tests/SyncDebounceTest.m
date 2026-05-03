classdef SyncDebounceTest < matlab.unittest.TestCase
% Tests for the parameterized sync window detection.

    methods (TestClassSetup)
        function addToolboxPath(tc) %#ok<MANU>
            addpath(fullfile(fileparts(mfilename('fullpath')), '..'));
        end
    end

    methods (Test)

        function testNameValueDebounce(tc)
            T = makeSyncTable(0.05);   % 50 ms cycle (would be filtered by debounce=50ms)
            cycles = hwalker.sync.findWindows(T, 'DebounceMs', 50, ...
                'MinDurationS', 0.0);
            % With aggressive debounce, very short pulses should be filtered
            tc.verifyTrue(size(cycles, 1) <= 1);
        end

        function testLegacyPositionalMinDuration(tc)
            T = makeSyncTable(0.5);
            cycles = hwalker.sync.findWindows(T, 0.3);  % positional minDuration
            tc.verifyEqual(class(cycles), 'double');
        end

        function testSyncColumnOverride(tc)
            % Force a specific column name even if 'Sync' is also present
            t  = (0:999)' / 100;
            on = double(t > 1 & t < 5);
            T  = table(t*1000, on, on, 'VariableNames', {'Time_ms','Sync','A7'});
            % Override to A7 explicitly
            cycles1 = hwalker.sync.findWindows(T, 'SyncColumn', 'A7');
            cycles2 = hwalker.sync.findWindows(T, 'SyncColumn', 'Sync');
            tc.verifyEqual(size(cycles1), size(cycles2));
        end

        function testCustomThreshold(tc)
            t  = (0:999)' / 100;
            sig = 2 + 3 * (t > 2 & t < 8);   % ranges 2 to 5
            T  = table(t*1000, sig, 'VariableNames', {'Time_ms','Sync'});
            % Default threshold (2+5)/2 = 3.5; using 4 should also detect
            cy1 = hwalker.sync.findWindows(T);
            cy2 = hwalker.sync.findWindows(T, 'Threshold', 4);
            tc.verifyEqual(size(cy1, 1), size(cy2, 1));
        end

        function testReturnsZeroByTwoOnNoSync(tc)
            t = (0:99)' / 100;
            T = table(t*1000, randn(100,1), 'VariableNames', {'Time_ms','Foo'});
            cy = hwalker.sync.findWindows(T);
            tc.verifyEqual(size(cy), [0 2]);
        end

        function testReturnsZeroByTwoOnConstantSignal(tc)
            t = (0:99)' / 100;
            T = table(t*1000, ones(100,1), 'VariableNames', {'Time_ms','Sync'});
            cy = hwalker.sync.findWindows(T);
            tc.verifyEqual(size(cy), [0 2]);
        end

    end
end


function T = makeSyncTable(highDuration)
    fs = 1000;
    n  = 5 * fs;
    t  = (0:n-1)' / fs;
    sig = zeros(n, 1);
    sig(t > 1 & t < 1+highDuration) = 1;
    T = table(t*1000, sig, 'VariableNames', {'Time_ms','Sync'});
end
