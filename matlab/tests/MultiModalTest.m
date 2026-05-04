classdef MultiModalTest < matlab.unittest.TestCase
% Tests for hwalker.io.{loadEMG,loadLoadcell}, +experiment, +kinetics, +emg.
% Synthesizes minimal CSVs in temp dir to drive the loaders.

    properties
        tmpDir
    end

    methods (TestClassSetup)
        function addToolboxPath(tc) %#ok<MANU>
            addpath(fullfile(fileparts(mfilename('fullpath')), '..'));
        end
    end

    methods (TestMethodSetup)
        function makeTempDir(tc)
            tc.tmpDir = fullfile(tempdir, sprintf('hwalker_mm_%s', ...
                datestr(now,'yyyymmddHHMMSSFFF'))); %#ok<DATST>
            mkdir(tc.tmpDir);
        end
    end

    methods (TestMethodTeardown)
        function rmTempDir(tc)
            if exist(tc.tmpDir, 'dir'), rmdir(tc.tmpDir, 's'); end
        end
    end

    methods (Test)

        % ==============================================================
        %  loadEMG
        % ==============================================================
        function testLoadEMG_BasicPipeline(tc)
            csv = fullfile(tc.tmpDir, 'emg.csv');
            fs = 2000; dur = 5;
            t = (0:1/fs:dur)';
            % 2-channel synthetic EMG: noise + bursts
            ch1 = 0.1 * randn(numel(t), 1);
            ch1(t > 1 & t < 2) = ch1(t > 1 & t < 2) + 0.5 * randn(sum(t>1 & t<2), 1);
            ch2 = 0.1 * randn(numel(t), 1);
            ch2(t > 3 & t < 4) = ch2(t > 3 & t < 4) + 0.4 * randn(sum(t>3 & t<4), 1);
            T = table(t, ch1, ch2, 'VariableNames', {'Time_s','R_TibAnt','R_GastrocLat'});
            writetable(T, csv);

            emg = hwalker.io.loadEMG(csv);
            tc.verifyEqual(emg.fs, fs, 'AbsTol', 1);
            tc.verifyEqual(numel(emg.channel_names), 2);
            tc.verifyEqual(size(emg.envelope), [numel(t), 2]);
            tc.verifyTrue(all(isfinite(emg.envelope(:))));
        end

        function testLoadEMG_OnsetDetected(tc)
            csv = fullfile(tc.tmpDir, 'emg2.csv');
            fs = 2000; dur = 4;
            t = (0:1/fs:dur)';
            % Strong contrast: low baseline, high-amplitude burst from t=1 to t=2
            x = 0.01 * randn(numel(t), 1);                          % very quiet baseline
            burst = t > 1 & t < 2;
            x(burst) = x(burst) + 2.0 * randn(sum(burst), 1);       % >100x baseline
            writetable(table(t, x, 'VariableNames', {'Time','EMG_Test'}), csv);
            emg = hwalker.io.loadEMG(csv, 'OnsetSDMult', 3.0);
            tc.verifyTrue(numel(emg.onset{1}) >= 1);
        end

        % ==============================================================
        %  loadLoadcell
        % ==============================================================
        function testLoadLoadcell_BasicTareAndBWS(tc)
            csv = fullfile(tc.tmpDir, 'loadcell.csv');
            fs = 1000; dur = 5;
            t = (0:1/fs:dur)';
            F = 200 + 5 * randn(numel(t), 1);   % ~200 N steady BWS
            writetable(table(t, F, 'VariableNames', {'Time_s','Force_N'}), csv);

            lc = hwalker.io.loadLoadcell(csv, 'BodyMassKg', 70);
            tc.verifyEqual(lc.fs, fs, 'AbsTol', 1);
            % After tare, mean of bws_pct should be near 0 (since baseline subtracted)
            tc.verifyEqual(lc.bws_pct_mean, 0, 'AbsTol', 1.0);
        end

        function testLoadLoadcell_RejectsMissingForce(tc)
            csv = fullfile(tc.tmpDir, 'badload.csv');
            T = table((0:99)', 'VariableNames', {'Time_s'});
            writetable(T, csv);
            tc.verifyError(@() hwalker.io.loadLoadcell(csv), ...
                'hwalker:loadLoadcell:noForce');
        end

        % ==============================================================
        %  emg.coContractionIndex
        % ==============================================================
        function testCCI_PerfectCoContraction(tc)
            % Identical envelopes → CCI = 100
            x = [1; 2; 3; 4; 5];
            cci = hwalker.emg.coContractionIndex(x, x);
            tc.verifyEqual(cci, 100, 'AbsTol', 1e-10);
        end

        function testCCI_PureReciprocal(tc)
            % Disjoint activation → CCI ≈ 0
            a = [1; 1; 0; 0; 0];
            b = [0; 0; 0; 1; 1];
            cci = hwalker.emg.coContractionIndex(a, b);
            tc.verifyEqual(cci, 0, 'AbsTol', 1e-10);
        end

        function testCCI_LengthMismatchErrors(tc)
            tc.verifyError(@() hwalker.emg.coContractionIndex([1;2], [1;2;3]), ...
                'hwalker:coContractionIndex:lengthMismatch');
        end

        % ==============================================================
        %  kinetics.grfFeatures
        % ==============================================================
        function testGrfFeatures_StanceDetection(tc)
            % Synthetic GRF: 3 stance phases
            fs = 1000; dur = 3;
            t = (0:1/fs:dur)';
            Fz = zeros(size(t));
            for s = [0.5, 1.5, 2.5]
                in = t > s & t < s + 0.7;
                Fz(in) = 700 * sin(pi * (t(in) - s) / 0.7);
            end
            grf.Fx = zeros(size(t));
            grf.Fy = 50 * ones(size(t));
            grf.Fz = Fz;
            grf.t  = t;
            feats = hwalker.kinetics.grfFeatures(grf);
            tc.verifyEqual(numel(feats.stance_start_s), 3);
            tc.verifyTrue(all(feats.peak_vertical_N > 600));
        end

        % ==============================================================
        %  experiment.loadSession (minimal smoke — robot only)
        % ==============================================================
        function testLoadSession_RobotOnly(tc)
            condDir = fullfile(tc.tmpDir, 'sub-01', 'cond-baseline');
            mkdir(condDir);
            % minimal robot.csv: H-Walker firmware-style
            fs = 100; dur = 3;
            t  = (0:1/fs:dur)';
            n  = numel(t);
            T = table(t * 1000, ...
                       zeros(n,1), zeros(n,1), ...
                       ones(n,1), zeros(n,1), ones(n,1), zeros(n,1), ...
                       25 * sin(2*pi*1*t), 25*sin(2*pi*1*t)+1, ...
                       25 * sin(2*pi*1*t), 25*sin(2*pi*1*t)+1, ...
                       double(t>1 & t<2), ...
                'VariableNames', {'Time_ms','L_GCP','R_GCP','L_Ax','L_Ay','R_Ax','R_Ay', ...
                                  'L_DesForce_N','L_ActForce_N','R_DesForce_N','R_ActForce_N','Sync'});
            writetable(T, fullfile(condDir, 'robot.csv'));

            session = hwalker.experiment.loadSession(condDir);
            tc.verifyEqual(session.subject_id, 'sub-01');
            tc.verifyEqual(session.condition,  'baseline');
            tc.verifyTrue(isstruct(session.robot));
            tc.verifyEmpty(session.motion);
            tc.verifyEmpty(session.emg);
            tc.verifyEmpty(session.loadcell);
        end

        function testLoadSession_RejectsMissingRobot(tc)
            condDir = fullfile(tc.tmpDir, 'sub-01', 'cond-baseline');
            mkdir(condDir);
            tc.verifyError(@() hwalker.experiment.loadSession(condDir), ...
                'hwalker:loadSession:noRobot');
        end

        function testLoadSession_LegacyFilenamePattern(tc)
            % Legacy H-Walker filename: 260430_Robot_CBJ_TD_level_0_5_walker_high_0.csv
            % loadSession should auto-detect via parseFilename when standard names absent.
            condDir = fullfile(tc.tmpDir, 'sub-01', 'cond-baseline');
            mkdir(condDir);
            fs = 100; dur = 3;
            t  = (0:1/fs:dur)';
            n  = numel(t);
            T = table(t * 1000, ...
                       zeros(n,1), zeros(n,1), ...
                       ones(n,1), zeros(n,1), ones(n,1), zeros(n,1), ...
                       25 * sin(2*pi*1*t), 25*sin(2*pi*1*t)+1, ...
                       25 * sin(2*pi*1*t), 25*sin(2*pi*1*t)+1, ...
                       double(t>1 & t<2), ...
                'VariableNames', {'Time_ms','L_GCP','R_GCP','L_Ax','L_Ay','R_Ax','R_Ay', ...
                                  'L_DesForce_N','L_ActForce_N','R_DesForce_N','R_ActForce_N','Sync'});
            % Save with LEGACY filename — NOT robot.csv
            legacyName = '260430_Robot_CBJ_TD_level_0_5_walker_high_0.csv';
            writetable(T, fullfile(condDir, legacyName));

            % Should still auto-detect this as the robot file
            session = hwalker.experiment.loadSession(condDir);
            tc.verifyTrue(contains(session.qc.files_present.robot, 'Robot'));
            tc.verifyTrue(isstruct(session.robot));
        end

        function testOnsetReleaseRMSE_BasicSegments(tc)
            % Build synthetic robot table with 3 active segments
            fs = 100; dur = 6;
            t = (0:1/fs:dur)';
            n = numel(t);
            des = zeros(n, 1);
            % 3 trapezoidal pulses: peak 50N
            for s = [1.0, 3.0, 5.0]
                in = (t >= s & t < s + 0.5);
                des(in) = 50;
            end
            act = des + 2*randn(n, 1);   % small noise
            T = table(t * 1000, des, act, 'VariableNames', ...
                {'Time_ms', 'R_DesForce_N', 'R_ActForce_N'});
            r = hwalker.force.onsetReleaseRMSE(T, 'R', 'Threshold', 1, 'SegMinDurMs', 50);
            tc.verifyEqual(r.nSegments, 3);
            tc.verifyTrue(all(r.peak_des_per_seg_N == 50));
            tc.verifyTrue(all(r.rmse_per_seg_N < 4));    % small-noise RMSE
            tc.verifyTrue(isfinite(r.rmse_overall_N));
        end

        function testOnsetReleaseRMSE_NoSegmentsBelowThreshold(tc)
            fs = 100; t = (0:1/fs:2)';
            T = table(t*1000, 0.1*ones(size(t)), zeros(size(t)), ...
                'VariableNames', {'Time_ms','R_DesForce_N','R_ActForce_N'});
            r = hwalker.force.onsetReleaseRMSE(T, 'R', 'Threshold', 1.0);
            tc.verifyEqual(r.nSegments, 0);
            tc.verifyTrue(isnan(r.rmse_overall_N));
        end

        function testLoadMotion_QualisysMatStub(tc)
            % Build a minimal Qualisys-style .mat and verify loadMotion reads it
            matFile = fullfile(tc.tmpDir, 'trial.mat');
            fs = 200;  nFr = 600;
            xyz = randn(3, 4, nFr);            % 4 markers × 3 coords × N frames
            trial.Trajectories.Labeled.Data      = xyz;
            trial.Trajectories.Labeled.Labels    = {'RKNE','RANK','LKNE','LANK'};
            trial.Trajectories.Labeled.Frequency = fs;
            trial.FrameRate = fs;
            save(matFile, '-struct', 'trial', '-v7.3');                  %#ok<NASGU>
            % Wrap in trial-name field as Qualisys does
            S = struct(); S.LKM_High_0 = trial;
            save(matFile, '-struct', 'S');

            motion = hwalker.io.loadMotion(matFile);
            tc.verifyEqual(motion.fs_marker, fs);
            tc.verifyEqual(numel(motion.marker_names), 4);
            tc.verifyTrue(isfield(motion.markers, 'RKNE'));
        end

        function testExtractFeatures_SideRightOnly(tc)
            % Robot result with both sides should yield only R rows when Side='R'
            condDir = fullfile(tc.tmpDir, 'sub-01', 'cond-baseline');
            mkdir(condDir);
            fs = 100; t = (0:1/fs:3)'; n = numel(t);
            T = table(t * 1000, ...
                       zeros(n,1), zeros(n,1), ...
                       ones(n,1), zeros(n,1), ones(n,1), zeros(n,1), ...
                       25*sin(2*pi*t), 25*sin(2*pi*t)+1, ...
                       25*sin(2*pi*t), 25*sin(2*pi*t)+1, ...
                       double(t>1 & t<2), ...
                'VariableNames', {'Time_ms','L_GCP','R_GCP','L_Ax','L_Ay','R_Ax','R_Ay', ...
                                  'L_DesForce_N','L_ActForce_N','R_DesForce_N','R_ActForce_N','Sync'});
            writetable(T, fullfile(condDir, 'robot.csv'));
            session = hwalker.experiment.loadSession(condDir);

            % both sides (default)
            f_both = hwalker.experiment.extractFeatures(session, 'Side', 'both');
            % R only
            f_r = hwalker.experiment.extractFeatures(session, 'Side', 'R');
            if ~isempty(f_r) && isfield(f_r, 'side')
                tc.verifyTrue(all(strcmp(f_r.side, 'R')));
                tc.verifyLessThanOrEqual(numel(f_r.side), numel(f_both.side));
            end
            % L only
            f_l = hwalker.experiment.extractFeatures(session, 'Side', 'L');
            if ~isempty(f_l) && isfield(f_l, 'side')
                tc.verifyTrue(all(strcmp(f_l.side, 'L')));
            end
        end

        function testLoadSession_LoadcellLegacyName(tc)
            condDir = fullfile(tc.tmpDir, 'sub-01', 'cond-baseline');
            mkdir(condDir);
            % Standard robot.csv
            fs = 100; t = (0:1/fs:3)'; n = numel(t);
            Trobot = table(t * 1000, zeros(n,1), zeros(n,1), ...
                ones(n,1), zeros(n,1), ones(n,1), zeros(n,1), ...
                25*sin(2*pi*t), 25*sin(2*pi*t)+1, 25*sin(2*pi*t), 25*sin(2*pi*t)+1, ...
                double(t>1 & t<2), ...
                'VariableNames', {'Time_ms','L_GCP','R_GCP','L_Ax','L_Ay','R_Ax','R_Ay', ...
                                  'L_DesForce_N','L_ActForce_N','R_DesForce_N','R_ActForce_N','Sync'});
            writetable(Trobot, fullfile(condDir, 'robot.csv'));

            % Loadcell with LEGACY name
            legacyName = '260430_Loadcell_CBJ_TD_level_0_5_walker_high_0.csv';
            Tlc = table((0:0.001:5)', 200 + 5*randn(5001,1), ...
                'VariableNames', {'Time_s','Force_N'});
            writetable(Tlc, fullfile(condDir, legacyName));

            session = hwalker.experiment.loadSession(condDir, 'BodyMassKg', 70);
            tc.verifyTrue(contains(session.qc.files_present.loadcell, 'Loadcell'));
            tc.verifyTrue(isstruct(session.loadcell));
        end

    end
end
