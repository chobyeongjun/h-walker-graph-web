% install.m  —  H-Walker Toolbox 설치 (한 번만 실행)
%
% 이 파일이 있는 폴더에서 실행하세요:
%   >> cd /path/to/matlab
%   >> install

thisDir = fileparts(mfilename('fullpath'));

% startup.m 위치 확인
startupFile = fullfile(userpath, 'startup.m');

% 이미 경로가 등록돼 있으면 skip
existingPath = path;
if contains(existingPath, thisDir)
    fprintf('✓ 이미 등록됨: %s\n', thisDir);
else
    % startup.m에 addpath 추가
    fid = fopen(startupFile, 'a');
    if fid == -1
        error('startup.m 을 열 수 없습니다: %s\n일시적으로 추가합니다.', startupFile);
    end
    fprintf(fid, "\naddpath('%s');  %% hwalker toolbox\n", thisDir);
    fclose(fid);
    addpath(thisDir);
    fprintf('✓ 등록 완료: %s\n', thisDir);
    fprintf('  startup.m: %s\n', startupFile);
end

% 동작 확인
try
    hwalker.io.estimateSampleRate(table((0:9)'/100, ones(10,1), ...
        'VariableNames', {'Time_s','Val'}));
    fprintf('✓ hwalker 패키지 로드 확인\n');
catch ME
    fprintf('✗ 오류: %s\n', ME.message);
    return
end

fprintf('\n사용법:\n');
fprintf('  results = hwalker.analyzeFile(''경로/파일.csv'');\n');
fprintf('  hwalker.plot.forceQC(results(1), ''R'')\n');
