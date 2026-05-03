classdef PreflightTest < matlab.unittest.TestCase
% Tests for the Copilot-style hwalker.plot.preflightCheck.

    methods (TestClassSetup)
        function addToolboxPath(tc) %#ok<MANU>
            addpath(fullfile(fileparts(mfilename('fullpath')), '..'));
        end
    end

    methods (Test)

        function testPassesValidInput(tc)
            preset = hwalker.plot.journalPreset('Nature');
            r = hwalker.plot.preflightCheck(@hwalker.plot.forceQC, ...
                {dummyResult(), 'R'}, preset, 1);
            tc.verifyTrue(r.ok);
        end

        function testCriticalOnNonHandle(tc)
            preset = hwalker.plot.journalPreset('Nature');
            r = hwalker.plot.preflightCheck('not a handle', {}, preset, 1);
            tc.verifyFalse(r.ok);
            tc.verifyTrue(any(contains(r.critical, 'not a function handle')));
        end

        function testCriticalOnBadNCols(tc)
            preset = hwalker.plot.journalPreset('Nature');
            r = hwalker.plot.preflightCheck(@hwalker.plot.forceQC, ...
                {dummyResult(), 'R'}, preset, 1.5);   % Nature has no 1.5
            tc.verifyFalse(r.ok);
            tc.verifyTrue(any(contains(r.critical, '1.5-column')));
        end

        function testElsevierAccepts1_5(tc)
            preset = hwalker.plot.journalPreset('Elsevier');
            r = hwalker.plot.preflightCheck(@hwalker.plot.forceQC, ...
                {dummyResult(), 'R'}, preset, 1.5);
            tc.verifyTrue(r.ok);
        end

        function testCriticalOnMissingPresetFields(tc)
            badPreset = struct('name', 'Bad');
            r = hwalker.plot.preflightCheck(@hwalker.plot.forceQC, ...
                {dummyResult(), 'R'}, badPreset, 1);
            tc.verifyFalse(r.ok);
            tc.verifyTrue(numel(r.critical) >= 5);  % many missing fields
        end

        function testCriticalOnEmptyStrideSide(tc)
            % Codex pass 7: empty result side must surface as CRITICAL,
            % not silent warning.
            r = dummyResult();
            r.right.nStrides = 0;
            preset = hwalker.plot.journalPreset('Nature');
            report = hwalker.plot.preflightCheck(@hwalker.plot.forceQC, ...
                {r, 'R'}, preset, 1);
            tc.verifyFalse(report.ok);
            tc.verifyTrue(any(contains(report.critical, 'nStrides == 0')));
        end

    end
end


function r = dummyResult()
    n = 24;
    sr.nStrides       = n;
    sr.strideTimes    = 1.0 + 0.05 * randn(n, 1);
    sr.strideTimesRaw = sr.strideTimes;
    sr.hsIndices      = int32((1:n+1)' * 100);
    sr.validMask      = true(n, 1);
    sr.qcReasons      = struct('nTotal', n, 'nKept', n, 'nOutlierIQR', 0, ...
                               'nBelowBound', 0, 'nAboveBound', 0, ...
                               'multiplier', 2.0, ...
                               'boundsRequested', [0.3 5.0], ...
                               'boundsEffective', [0.3 5.0]);
    sr.strideTimeMean = 1.0; sr.strideTimeStd = 0.05; sr.strideTimeCV = 5;
    sr.cadence        = 120;
    sr.stancePct      = 60 * ones(n,1);  sr.swingPct = 40 * ones(n,1);
    sr.stancePctMean  = 60;  sr.stancePctStd = 1;
    sr.swingPctMean   = 40;  sr.swingPctStd  = 1;
    sr.strideLengths  = ones(n,1);  sr.strideLengthMean = 1; sr.strideLengthStd = 0.05;

    profile.act.individual = randn(n, 101);
    profile.act.mean       = mean(profile.act.individual, 1);
    profile.act.std        = std(profile.act.individual, 0, 1);
    profile.des.individual = profile.act.individual;
    profile.des.mean       = profile.act.mean;
    profile.des.std        = profile.act.std;

    ft.rmse = 5;  ft.mae = 4;  ft.peakError = 8;
    ft.rmsePerStride = 5*ones(n,1); ft.maePerStride = 4*ones(n,1);

    r.left  = sr;     r.right = sr;
    r.leftForce  = ft; r.rightForce = ft;
    r.leftProfile  = profile; r.rightProfile = profile;
    r.strideTimeSymmetry   = 0.5;
    r.strideLengthSymmetry = 0.3;
    r.stanceSymmetry       = 1.2;
    r.forceSymmetry        = 0.8;
    r.leftFatigue          = 0.0;
    r.rightFatigue         = 0.0;
end
