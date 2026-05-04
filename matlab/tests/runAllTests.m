function results = runAllTests()
% runAllTests  Run all H-Walker toolbox unit tests.
%
%   runAllTests()           % print results
%   r = runAllTests();      % also return TestResult array

    testFolder    = fileparts(mfilename('fullpath'));
    toolboxFolder = fullfile(testFolder, '..');
    addpath(toolboxFolder);

    suite = testsuite({ ...
        'SyncTest', 'IOTest', 'StrideTest', 'ForceTest', ...
        'StatsAnovaTest', 'StatsBootstrapTest', 'PairedTestVariantsTest', ...
        'PresetParityTest', 'FilterIQRReasonsTest', ...
        'SyncDebounceTest', 'PreflightTest', 'ReproTest', ...
        'MultiModalTest'}, ...
        'BaseFolder', testFolder);

    runner  = matlab.unittest.TestRunner.withTextOutput('Verbosity', 2);
    results = runner.run(suite);

    nTotal  = numel(results);
    nFailed = sum([results.Failed]);
    fprintf('\n=== %d/%d passed ===\n', nTotal - nFailed, nTotal);

    if nFailed > 0
        fprintf('\n--- Failed tests ---\n');
        for i = 1:nTotal
            if results(i).Failed
                fprintf('  %s\n', results(i).Name);
            end
        end
    end
end
