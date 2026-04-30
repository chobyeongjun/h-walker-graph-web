classdef IOTest < matlab.unittest.TestCase
% Unit tests for hwalker.io.* and hwalker.stats.* utilities.

    methods (TestClassSetup)
        function addToolboxPath(tc) %#ok<MANU>
            addpath(fullfile(fileparts(mfilename('fullpath')), '..'));
        end
    end

    methods (Test)

        % ---------- estimateSampleRate ----------

        function testSampleRate_TimeMs(tc)
            T = table((0:999)' * 9, rand(1000,1), ...
                'VariableNames', {'Time_ms','Val'});
            fs = hwalker.io.estimateSampleRate(T);
            tc.verifyEqual(fs, 1000/9, 'RelTol', 0.01);
        end

        function testSampleRate_TimeS(tc)
            T = table((0:999)' / 200, rand(1000,1), ...
                'VariableNames', {'Time_s','Val'});
            fs = hwalker.io.estimateSampleRate(T);
            tc.verifyEqual(fs, 200.0, 'RelTol', 0.01);
        end

        function testSampleRate_Fallback111(tc)
            T = table(rand(100,1), 'VariableNames', {'Val'});
            fs = hwalker.io.estimateSampleRate(T);
            tc.verifyEqual(fs, 111.0);
        end

        % ---------- parseFilename ----------

        function testParse_Walker(tc)
            info = hwalker.io.parseFilename( ...
                '260430_Robot_CBJ_TD_level_3_0_walker_high_30.csv');
            tc.verifyEqual(info.date,          '260430');
            tc.verifyEqual(info.modality,      'TD');
            tc.verifyEqual(info.speed,         3.0, 'AbsTol', 1e-9);
            tc.verifyEqual(info.device,        'walker');
            tc.verifyEqual(info.attachment,    'high');
            tc.verifyEqual(info.angle,         30);
            tc.verifyEmpty(info.weightbearing);
        end

        function testParse_NoassistWB(tc)
            info = hwalker.io.parseFilename( ...
                '260430_Robot_CBJ_TD_level_3_0_noassist_wb.csv');
            tc.verifyEqual(info.device,        'noassist');
            tc.verifyEqual(info.weightbearing, 'wb');
            tc.verifyEmpty(info.attachment);
            tc.verifyTrue(isnan(info.angle));
        end

        function testParse_NoassistNWB(tc)
            info = hwalker.io.parseFilename( ...
                '260430_Robot_CBJ_OG_noassist_nwb.csv');
            tc.verifyEqual(info.modality,      'OG');
            tc.verifyEqual(info.device,        'noassist');
            tc.verifyEqual(info.weightbearing, 'nwb');
        end

        function testParse_AllAttachments(tc)
            for att = {'high','middle','low'}
                for ang = {0, 30}
                    fname = sprintf('260430_Robot_CBJ_TD_level_3_0_walker_%s_%d.csv', att{1}, ang{1});
                    info  = hwalker.io.parseFilename(fname);
                    tc.verifyEqual(info.attachment, att{1});
                    tc.verifyEqual(info.angle, ang{1});
                end
            end
        end

        function testParse_InvalidAngleIgnored(tc)
            % angle 45 is not a valid condition → angle stays NaN
            info = hwalker.io.parseFilename( ...
                '260430_Robot_CBJ_TD_level_3_0_walker_high_45.csv');
            tc.verifyTrue(isnan(info.angle));
        end

        function testParse_TrialPresent(tc)
            info = hwalker.io.parseFilename( ...
                '260430_Robot_CBJ_TD_level_3_0_walker_high_30_T02.csv');
            tc.verifyEqual(info.trial, 2);
            tc.verifyEqual(info.attachment, 'high');
        end

        function testParse_TrialAbsent(tc)
            info = hwalker.io.parseFilename( ...
                '260430_Robot_CBJ_TD_level_3_0_walker_high_30.csv');
            tc.verifyTrue(isnan(info.trial));
        end

        function testParse_EmptyFilename(tc)
            info = hwalker.io.parseFilename('data.csv');
            tc.verifyEmpty(info.source);
            tc.verifyEmpty(info.subject);
        end

        % ---------- detectSourceKind ----------

        function testDetectSourceKind_MissingFile(tc)
            kind = hwalker.io.detectSourceKind('/nonexistent/path.csv');
            tc.verifyEqual(kind, 'Unknown');
        end

        % ---------- symmetryIndex ----------

        function testSymmetry_Perfect(tc)
            tc.verifyEqual(hwalker.stats.symmetryIndex(1.0, 1.0), 0.0);
        end

        function testSymmetry_MissingSide(tc)
            tc.verifyEqual(hwalker.stats.symmetryIndex(0.0, 1.0), -1.0);
            tc.verifyEqual(hwalker.stats.symmetryIndex(1.0, 0.0), -1.0);
        end

        function testSymmetry_KnownValue(tc)
            % |1-2| / ((1+2)/2) * 100 = 1/1.5*100 = 66.667
            si = hwalker.stats.symmetryIndex(1.0, 2.0);
            tc.verifyEqual(si, 66.6667, 'AbsTol', 0.001);
        end

        % ---------- fatigueIndex ----------

        function testFatigue_NoChange(tc)
            fi = hwalker.stats.fatigueIndex(ones(100,1));
            tc.verifyEqual(fi, 0.0, 'AbsTol', 1e-10);
        end

        function testFatigue_TooShort(tc)
            tc.verifyEqual(hwalker.stats.fatigueIndex([1;2;3]), 0.0);
        end

        function testFatigue_PositiveTrend(tc)
            v = linspace(1.0, 2.0, 100)';
            fi = hwalker.stats.fatigueIndex(v);
            tc.verifyGreaterThan(fi, 0);
        end

        function testFatigue_NegativeTrend(tc)
            v = linspace(2.0, 1.0, 100)';
            fi = hwalker.stats.fatigueIndex(v);
            tc.verifyLessThan(fi, 0);
        end

        % ---------- pairedTest ----------

        function testPairedTest_Identical(tc)
            a = (1:20)';
            r = hwalker.stats.pairedTest(a, a);
            tc.verifyEqual(r.diff_mean, 0.0, 'AbsTol', 1e-10);
            tc.verifyEqual(r.cohens_d,  0.0, 'AbsTol', 1e-10);
        end

        function testPairedTest_KnownDiff(tc)
            % b = a + 2 → diff_mean = 2, d = 2/0 = Inf handled → just check mean
            a = ones(20, 1);
            b = ones(20, 1) * 3;
            r = hwalker.stats.pairedTest(a, b);
            tc.verifyEqual(r.diff_mean, 2.0, 'AbsTol', 1e-10);
            tc.verifyEqual(r.n, 20);
        end

        function testPairedTest_NaNDropped(tc)
            a = [1; 2; NaN; 4];
            b = [2; 3; 4;   5];
            r = hwalker.stats.pairedTest(a, b);
            tc.verifyEqual(r.n, 3);   % NaN pair dropped
        end

        % ---------- effectSize ----------

        function testEffectSize_SameGroups(tc)
            a = randn(30,1);
            tc.verifyEqual(hwalker.stats.effectSize(a, a), 0.0, 'AbsTol', 1e-10);
        end

        function testEffectSize_TooFew(tc)
            tc.verifyTrue(isnan(hwalker.stats.effectSize(1, 2)));
        end

    end
end
