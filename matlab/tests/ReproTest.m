classdef ReproTest < matlab.unittest.TestCase
% Tests for hwalker.meta.reproPackage / loadRepro round-trip.

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
            tc.tmpDir = fullfile(tempdir, ...
                sprintf('hwalker_repro_%s', datestr(now,'yyyymmddHHMMSSFFF'))); %#ok<DATST>
            mkdir(tc.tmpDir);
        end
    end

    methods (TestMethodTeardown)
        function rmTempDir(tc)
            if exist(tc.tmpDir, 'dir')
                rmdir(tc.tmpDir, 's');
            end
        end
    end

    methods (Test)

        function testReproPackageWritesAllFiles(tc)
            r = makeFakeResult();
            info = hwalker.meta.reproPackage(r, tc.tmpDir, ...
                'Parameters', struct('alpha', 0.05));

            tc.verifyTrue(exist(info.dir, 'dir') == 7);
            for f = {'mat','json','params','env','presets','readme'}
                tc.verifyTrue(isfield(info.files, f{1}), ...
                    sprintf('files.%s missing', f{1}));
                tc.verifyTrue(exist(info.files.(f{1}), 'file') == 2);
            end
        end

        function testReproPackageWritesInputHash(tc)
            % Create a temp CSV
            csvPath = fullfile(tc.tmpDir, 'data.csv');
            T = table((0:99)', randn(100,1), 'VariableNames', {'t','x'});
            writetable(T, csvPath);

            r = makeFakeResult();
            info = hwalker.meta.reproPackage(r, tc.tmpDir, 'InputCSV', csvPath);

            tc.verifyTrue(exist(info.files.hash, 'file') == 2);
            line = strtrim(fileread(info.files.hash));
            parts = strsplit(line);
            tc.verifyEqual(numel(parts{1}), 64);   % SHA-256 = 64 hex chars
        end

        function testLoadReproRoundTrip(tc)
            r = makeFakeResult();
            info = hwalker.meta.reproPackage(r, tc.tmpDir, ...
                'Parameters', struct('alpha', 0.05, 'iqr_k', 2.0));

            pkg = hwalker.meta.loadRepro(info.dir);
            tc.verifyEqual(pkg.result.left.nStrides, r.left.nStrides);
            tc.verifyEqual(pkg.result.right.nStrides, r.right.nStrides);
            tc.verifyEqual(pkg.params.alpha, 0.05);
            tc.verifyEqual(pkg.params.iqr_k, 2.0);
        end

        function testCurrentMatchFlagsExist(tc)
            r = makeFakeResult();
            info = hwalker.meta.reproPackage(r, tc.tmpDir);
            pkg  = hwalker.meta.loadRepro(info.dir);
            tc.verifyTrue(isfield(pkg, 'currentMatch'));
            tc.verifyTrue(isfield(pkg.currentMatch, 'matlab'));
            tc.verifyTrue(isfield(pkg.currentMatch, 'git_commit'));
            % MATLAB version should match (we just saved with current version)
            tc.verifyTrue(pkg.currentMatch.matlab);
        end

        function testParallelCallsDontCollide(tc)
            % Codex pass 7: ms-resolution timestamp + collision suffix.
            % Call reproPackage twice within the same ms; both must succeed.
            r = makeFakeResult();
            info1 = hwalker.meta.reproPackage(r, tc.tmpDir);
            info2 = hwalker.meta.reproPackage(r, tc.tmpDir);
            tc.verifyNotEqual(info1.dir, info2.dir);
            tc.verifyTrue(exist(info1.dir, 'dir') == 7);
            tc.verifyTrue(exist(info2.dir, 'dir') == 7);
        end

        function testGitCommitNotEmpty(tc)
            % Codex pass 5: reproPackage MUST capture a non-empty git commit
            % when run inside a git repo.  Bug was: walked up wrong number
            % of fileparts() calls and looked for .git in matlab/ instead
            % of repo root.
            r = makeFakeResult();
            info = hwalker.meta.reproPackage(r, tc.tmpDir);
            tc.verifyNotEmpty(info.git_commit, ...
                'git_commit field must be non-empty when in a git repo');
            tc.verifyEqual(numel(info.git_commit), 40, ...
                'git_commit should be a 40-char SHA-1');
        end

    end
end


function r = makeFakeResult()
    r.filename = 'test.csv';  r.filepath = '';
    r.label    = 'test';      r.syncId   = 0;  r.syncWindow = [];
    r.nSamples = 1000;        r.durationS = 10; r.sampleRate = 100;
    r.left.nStrides       = 10;
    r.left.strideTimes    = ones(10,1);
    r.left.strideTimesRaw = ones(10,1);
    r.left.hsIndices      = int32((1:11)' * 100);
    r.left.validMask      = true(10,1);
    r.left.qcReasons      = struct('nTotal', 10, 'nKept', 10, ...
                                   'nOutlierIQR', 0, 'nBelowBound', 0, 'nAboveBound', 0);
    r.left.strideTimeMean = 1; r.left.strideTimeStd = 0.05; r.left.strideTimeCV = 5;
    r.left.cadence        = 120;
    r.left.stancePct      = 60*ones(10,1); r.left.swingPct = 40*ones(10,1);
    r.left.stancePctMean  = 60; r.left.stancePctStd = 1;
    r.left.swingPctMean   = 40; r.left.swingPctStd  = 1;
    r.left.strideLengths  = ones(10,1);  r.left.strideLengthMean = 1;
    r.left.strideLengthStd = 0.05;

    r.right = r.left;

    r.leftForce.rmse = 5; r.leftForce.mae = 4; r.leftForce.peakError = 8;
    r.leftForce.rmsePerStride = 5*ones(10,1); r.leftForce.maePerStride = 4*ones(10,1);
    r.rightForce = r.leftForce;

    pf.act.individual = []; pf.act.mean = []; pf.act.std = [];
    pf.des.individual = []; pf.des.mean = []; pf.des.std = [];
    r.leftProfile  = pf;  r.rightProfile = pf;

    r.strideTimeSymmetry = 0.5;
    r.strideLengthSymmetry = 0.3;
    r.stanceSymmetry = 1.2;
    r.forceSymmetry  = 0.8;
    r.leftFatigue    = 0;
    r.rightFatigue   = 0;
end
