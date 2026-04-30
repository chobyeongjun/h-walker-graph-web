classdef SyncTest < matlab.unittest.TestCase
% Unit tests for hwalker.sync.findWindows and extractWindow.

    methods (TestClassSetup)
        function addToolboxPath(tc) %#ok<MANU>
            addpath(fullfile(fileparts(mfilename('fullpath')), '..'));
        end
    end

    methods (Test)

        function testBasicOneCycle(tc)
            % One falling→rising→falling = one cycle
            % Use realistic durations: 500ms HIGH, 200ms LOW at 100 Hz
            s = [zeros(1,20) ones(1,50) zeros(1,20) ones(1,50) zeros(1,20)];
            T = makeSyncTable(s, 100);
            cycles = hwalker.sync.findWindows(T, 0);
            tc.verifyEqual(size(cycles,1), 1);
        end

        function testTwoCycles(tc)
            % Two complete cycles with realistic durations
            s = [zeros(1,20) ones(1,50) zeros(1,20) ones(1,50) zeros(1,20) ones(1,50) zeros(1,20)];
            T = makeSyncTable(s, 100);
            cycles = hwalker.sync.findWindows(T, 0);
            tc.verifyGreaterThanOrEqual(size(cycles,1), 2);
        end

        function testPhantomFilter(tc)
            % Cycles shorter than minDuration_s (0.5 s) are excluded
            % At 100 Hz, 0.5 s = 50 samples. Make a short 5-sample cycle.
            short = [zeros(1,5) 1 1 zeros(1,5)];       % 5 samples → 0.05 s at 100 Hz
            long  = [zeros(1,10) ones(1,60) zeros(1,10)]; % 80 samples → 0.8 s
            s     = [short long];
            T     = makeSyncTable(s, 100);
            cycles = hwalker.sync.findWindows(T, 0.5);
            if size(cycles,1) > 0
                durations = cycles(:,2) - cycles(:,1);
                tc.verifyTrue(all(durations >= 0.5));
            end
        end

        function testConstantSignal(tc)
            T = makeSyncTable(ones(1,200), 100);
            cycles = hwalker.sync.findWindows(T, 0);
            tc.verifyEmpty(cycles);
        end

        function testNoSyncColumn(tc)
            T = table((0:9)', rand(10,1), 'VariableNames', {'Time_s','Value'});
            cycles = hwalker.sync.findWindows(T, 0);
            tc.verifyEmpty(cycles);
        end

        function testHalfOpenInterval(tc)
            % Each cycle [t_start, t_end] must have positive duration
            s = [1 1 0 0 1 1 0 0 1 1 0 0];
            T = makeSyncTable(s, 100);
            cycles = hwalker.sync.findWindows(T, 0);
            if size(cycles,1) > 0
                tc.verifyTrue(all(cycles(:,2) > cycles(:,1)));
            end
        end

        function testExtractWindowRebased(tc)
            n = 300;
            t = (0:n-1)' / 100;
            T = table(t, rand(n,1), ...
                'VariableNames', {'Time_s','Value'});
            T.Sync = double(t >= 1.0 & t < 2.0);
            Tw = hwalker.sync.extractWindow(T, 1.0, 2.0);
            tc.verifyGreaterThan(height(Tw), 0);
            % Time should be rebased to start at 0
            tc.verifyLessThan(abs(Tw.Time_s(1)), 0.02);
        end

        function testExtractWindowRowCount(tc)
            n = 500;
            t = (0:n-1)' / 100;
            T = table(t, ones(n,1), 'VariableNames', {'Time_s','Val'});
            Tw = hwalker.sync.extractWindow(T, 1.0, 3.0);
            % Expect ~201 rows for 2 s at 100 Hz
            tc.verifyGreaterThan(height(Tw), 190);
            tc.verifyLessThan(height(Tw), 215);
        end

    end
end

% ---- Helper ----
function T = makeSyncTable(syncVec, fs)
    n = numel(syncVec);
    T = table((0:n-1)' / fs, syncVec(:), ...
        'VariableNames', {'Time_s','Sync'});
end
