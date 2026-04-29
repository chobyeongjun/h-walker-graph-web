function results = runAllTests()
% runAllTests  Run all H-Walker toolbox unit tests.
%
%   runAllTests()           % print results
%   r = runAllTests();      % also return TestResult array

    testFolder    = fileparts(mfilename('fullpath'));
    toolboxFolder = fullfile(testFolder, '..');
    addpath(toolboxFolder);

    suite = testsuite({'SyncTest','IOTest','StrideTest','ForceTest'}, ...
        'BaseFolder', testFolder);

    runner  = matlab.unittest.TestRunner.withTextOutput('Verbosity', 2);
    results = runner.run(suite);

    nTotal  = numel(results);
    nFailed = sum([results.Failed]);
    fprintf('\n=== %d/%d passed ===\n', nTotal - nFailed, nTotal);
end
