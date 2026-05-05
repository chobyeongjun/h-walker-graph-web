function example_08_manual_sync_cut()
% example_08_manual_sync_cut  Manually sync-cut one trial in MATLAB.
%
% MATLAB Copilot prompt examples this answers:
%   "한 robot CSV 파일을 sync 신호 기준으로 자르고 싶어"
%   "low_0 trial 만 따로 자르고 plot 으로 확인"
%   "multi-segment 파일에서 sync-complete segment 만 추출"
%
% CANONICAL Copilot prompt:
%   "Use hwalker.experiment.cutBySync(file, 'Plot', true) to load,
%    detect segments, pick sync-complete one, slice the longest cycle,
%    and visualize before/after."

    % ============================================================
    %  USAGE 1 — single command, plot result
    % ============================================================
    file = '/Users/chobyeongjun/assistive-vector-treadmill/data/260504_Sub01/Robot/robot_lkm_low_0.CSV';
    [Tcut, info] = hwalker.experiment.cutBySync(file, 'Plot', true);

    fprintf('\nSegments found: %d (picked seg %d, dur %.1fs)\n', ...
        info.nSegmentsFound, info.pickedSegment, info.segmentDur_s);
    fprintf('Cycles found in segment: %d (picked %d)\n', ...
        info.nCyclesFound, info.pickedCycle);
    fprintf('Cycle window: %.3f - %.3f s (%.3fs)\n', ...
        info.cycleStart_s, info.cycleEnd_s, info.cycleEnd_s - info.cycleStart_s);
    fprintf('Rows: %d → %d\n', info.nSamplesIn, info.nSamplesOut);

    % ============================================================
    %  USAGE 2 — choose explicit segment / cycle
    % ============================================================
    %  Default 'sync-complete' picks the segment that has a real
    %  rising→falling cycle. To override:
    %    'WhichSegment', 1            % first segment of the file
    %    'WhichSegment', 'last'       % last segment (record-stop+start)
    %    'WhichSegment', 'longest'    % longest by duration (ignores sync)
    %    'WhichCycle', 'first'        % first cycle within picked segment
    %    'WhichCycle', 2              % cycle index 2

    [Tcut2, ~] = hwalker.experiment.cutBySync(file, ...
        'WhichSegment', 'longest', ...     % seg 1 (1427 s) of low_0
        'WhichCycle',   'first');

    % ============================================================
    %  USAGE 3 — save the cut directly to a CSV
    % ============================================================
    [~, ~] = hwalker.experiment.cutBySync(file, ...
        'Save', '/tmp/low_0_manually_cut.csv');

    % ============================================================
    %  USAGE 4 — sanity check: feed the cut table to analyzeFile
    % ============================================================
    r = hwalker.analyzeFile(Tcut, 'label', 'low_0_R_only');
    fprintf('\nR strides: %d, R force RMSE (full): %.2f N\n', ...
        r.right.nStrides, r.rightForce.rmse);
    if isfield(r.rightForce, 'onsetReleaseGCP') && r.rightForce.onsetReleaseGCP.nStrides > 0
        g = r.rightForce.onsetReleaseGCP;
        fprintf('R GCP[55-85%%] RMSE: %.2f N (n=%d)\n', g.rmse_overall_N, g.nStrides);
    end

    % ============================================================
    %  USAGE 5 — multi-segment detection only (no sync cut yet)
    % ============================================================
    T_full = hwalker.io.loadCSV(file);
    [T_seg, segInfo] = hwalker.experiment.pickSegment(T_full, 'sync-complete');
    fprintf('\nSegment detection: %d segs, durations = %s s, syncOK = %s\n', ...
        segInfo.nSegments, mat2str(round(segInfo.durs_s')), mat2str(segInfo.syncOK'));
end
