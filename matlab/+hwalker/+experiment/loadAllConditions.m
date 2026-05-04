function conditions = loadAllConditions(subjectDir, varargin)
% hwalker.experiment.loadAllConditions  Load all cond-* sessions for one subject.
%
%   conditions = hwalker.experiment.loadAllConditions( ...
%       '~/h-walker-experiments/studies/2026-05-04/sub-01')
%
% Returns N x 1 struct array of sessions (sorted by cond-* alphabetically).
%
% NOTE: condition order in the returned array follows folder name sort.
% To enforce a particular order (e.g., baseline → low → high), name the
% folders alphabetically: cond-1_baseline, cond-2_low, cond-3_high.

    if ~exist(subjectDir, 'dir')
        error('hwalker:loadAllConditions:notDir', ...
            'Subject directory not found: %s', subjectDir);
    end

    d = dir(fullfile(subjectDir, 'cond-*'));
    d = d([d.isdir]);
    if isempty(d)
        error('hwalker:loadAllConditions:noCond', ...
            'No cond-* subdirectories found in %s.', subjectDir);
    end

    [~, ord] = sort({d.name});
    d = d(ord);

    fprintf('\n=== Loading %d condition(s) for subject %s ===\n', ...
        numel(d), strrep(d(1).folder, fileparts(d(1).folder), ''));

    for k = numel(d):-1:1
        s = hwalker.experiment.loadSession( ...
            fullfile(d(k).folder, d(k).name), varargin{:});
        conditions(k, 1) = s;
    end
end
