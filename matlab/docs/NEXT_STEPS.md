# 다음에 내가 뭘 해야 해? — H-Walker MATLAB Toolbox 적용 가이드

> 도구 만들었으니 이제 **본인 데이터로 실제 논문 figure + 통계** 만드는 절차.
> 처음부터 끝까지 따라하는 5-step.

---

## STEP 1 — MATLAB.app 켜고 도구 등록 (1회만, 30초)

1. macOS 응용프로그램 → **MATLAB_R2025b** 더블클릭
2. MATLAB 창 안의 `>>` 프롬프트 보이는 **Command Window** 클릭
3. 입력:
   ```matlab
   cd /Users/chobyeongjun/h-walker-graph-web/matlab
   install
   ```
4. `Toolbox added to startup.m` 비슷한 메시지 나오면 끝. **MATLAB 재시작** 한 번 하면 영구 적용.

→ 이제 어느 working directory 에서든 `hwalker.*` 함수가 호출 가능.

---

## STEP 2 — 데모 한 번 돌려서 도구 작동 확인 (2분)

Command Window 에:
```matlab
cd /Users/chobyeongjun/h-walker-graph-web/matlab/examples
demo
```

→ 끝나면 Finder 가 자동으로 결과 폴더 (`./out/`) 열어줌.
→ `figures/Fig1_force_*.pdf` 12개 더블클릭해서 같은 figure 가 저널마다 다른 사이즈/폰트인 걸 눈으로 확인.
→ 콘솔에 통계 결과 (paired t, ANOVA, RM-ANOVA, post-hoc 4가지, bootstrap CI) 출력.

여기서 **에러 없이 통과** = 도구는 100% 작동.

---

## STEP 3 — 본인 실제 CSV 1개로 분석 (5분)

본인 H-Walker 실험 CSV 1개 위치 확인 (예: `~/h-walker-data/2026-04-30/Robot_CBJ_TD_level_0_5_walker_high_0.csv`).

```matlab
% 분석 (sync 신호 자동 분할됨)
results = hwalker.analyzeFile('/Users/chobyeongjun/h-walker-data/2026-04-30/your_file.csv');

% 핵심 결과 빠르게 확인
results(1).right.cadence              % 분당 걸음
results(1).right.strideTimeMean       % 평균 stride 시간
results(1).right.strideTimeStd
results(1).rightForce.rmse            % force 추적 오차
results(1).strideTimeSymmetry         % 좌우 비대칭 (%)
results(1).right.qcReasons            % stride 제외 통계 (Methods 섹션 보고용)
```

콘솔에 자동 출력:
```
[sync1] sample_data  (3000 samples, 30.0 s, 100.0 Hz)
  L strideQC: kept 24/26 (excluded: 1 IQR-outlier, 0 < 0.30s, 1 > 5.00s)
  L: 24 strides, T=1.180±0.087 s, cadence=101.7 steps/min
  L force: RMSE=18.32 N, MAE=14.71 N, peak=42.18 N
```

이 한 줄 그대로 Methods 섹션에 인용 가능.

---

## STEP 4 — 논문 Figure 한 번에 출력 (30초)

```matlab
hwalker.plot.exportAllJournals( ...
    @hwalker.plot.forceQC, {results(1), 'R'}, '~/Desktop/paper_fig1', ...
    'Journals', {'TRO','RAL','TNSRE','ICRA','JNER','SciRobotics'}, ...
    'Formats',  {'PDF','PNG'}, ...
    'NCols',    2);
```

→ `~/Desktop/paper_fig1/Fig1_force_TRO.pdf`, `Fig1_force_RAL.pdf`, ... 12개 파일.

본인이 노리는 저널 (예: T-RO 1순위, JNER 2순위) 에 맞춰 `'Journals'` 배열 변경.

**사용 가능한 저널 목록 보기**:
```matlab
hwalker.plot.listJournals
```

---

## STEP 5 — 통계 검정 + 재현성 패키지 (논문 작성 단계)

### 5a. 어떤 검정 써야 하나?

```matlab
groups = {baseline.right.strideTimes, low.right.strideTimes, high.right.strideTimes};
rec = hwalker.stats.decisionTree(groups, 'Design', 'between');
disp(rec.rationale);
% → 자동 추천: One-way ANOVA + Tukey HSD (정규성 OK, 분산 OK)
```

### 5b. 권장된 검정 실행

| Design | 함수 | 보고할 것 |
|---|---|---|
| 2 within (pre/post 같은 사람) | `hwalker.stats.pairedTest(a, b)` | t, p, Cohen's d_av, 95% CI |
| 2 between (다른 그룹) | `[h,p,ci,stats] = ttest2(a, b, 'Vartype','unequal')` | Welch t |
| 3+ between | `hwalker.stats.anova1({a,b,c}) + postHoc(...)` | F, p, ω², 사후검정 |
| 3+ within (같은 사람 K 조건) | `hwalker.stats.anovaRM(Y_NxK)` | F, GG-corrected p, partial η² |

### 5c. 재현성 패키지 (supplementary 첨부)

```matlab
hwalker.meta.reproPackage(results, '~/Desktop/paper_repro', ...
    'InputCSV', '/path/to/your.csv');
% → ~/Desktop/paper_repro/<timestamp>/
%     ├── result.mat / result.json    (전체 분석 결과)
%     ├── parameters.json             (사용 파라미터)
%     ├── environment.json            (MATLAB 버전 + git commit)
%     ├── input_hash.txt              (input CSV SHA-256)
%     └── README.txt
```

이 폴더 통째로 zip 떠서 supplementary 로 첨부.

---

## STEP 6 — 막혔을 때 / 새로운 시나리오

### 6a. 시나리오별 example 스크립트 (복사해서 그대로 사용)

```matlab
edit example_01_paired_t_test          % pre/post 비교
edit example_02_anova_3conditions      % 3+ 조건 비교
edit example_03_force_figure_export    % 6+ 저널 figure 출력
edit example_04_significance_brackets  % bar + ** asterisk
edit example_05_multipanel_with_labels % 4-panel + a/b/c/d
edit example_06_repro_for_supplementary % 재현성 패키지
```

각 스크립트 위에 본인 CSV 경로만 바꾸면 그대로 동작.

### 6b. MATLAB Copilot 한테 물어볼 때

MATLAB R2024b+ Copilot 이 깔려 있으면 (Editor 우측 패널), 자연어로 물어보면 알아서 우리 함수 사용한 답을 줌:

| Copilot prompt 예시 | Copilot 이 제안할 함수 |
|---|---|
| "stride time pre/post 비교" | `hwalker.stats.pairedTest(...)` |
| "3 조건 비교 + 사후검정" | `hwalker.stats.anova1 + postHoc` |
| "T-RO 사이즈로 figure" | `hwalker.plot.journalPreset('TRO') + exportFigure` |
| "재현성 패키지" | `hwalker.meta.reproPackage(...)` |
| "어떤 검정 써야해?" | `hwalker.stats.decisionTree(...)` |

→ Copilot 이 우리 함수를 정확히 호출하도록 `examples/` 의 6개 스크립트가 컨텍스트 학습 자료 역할을 함.

### 6c. 본인 저널이 목록에 없을 때 (Custom preset)

```matlab
mySpec = struct( ...
    'name',       'MyTargetJournal', ...
    'col1mm',     88,  'col1h_mm', 70, ...
    'col2mm',     180, 'col2h_mm', 90, ...
    'font',       'Arial', ...
    'bodyPt',     9, ...
    'strokePt',   0.75, ...
    'dpi',        600, ...
    'paletteName','wong');     % wong | grayscale | default | elsevier

p = hwalker.plot.journalPreset('Custom', mySpec);
fig = hwalker.plot.forceQC(results(1), 'R');
hwalker.plot.applyPreset(fig, gca, p, 2);
hwalker.plot.exportFigure(fig, 'Fig1_MyJournal.pdf', p);
```

---

## STEP 7 — Phase F (논문 제출 후)

지금 도구는 H-Walker 도메인 전용 (`+hwalker/` 패키지). 논문 제출 후 시간 나면:

- `+robolab/` generic 패키지로 분리 → 다른 로봇 (외골격, IMU 기반 보행, manipulator) 에도 그대로 재사용
- `+stats/` 와 `+plot/` 는 도메인 무관이라 그대로 이식
- `+hwalker/` 는 thin wrapper 만 남기고 GCP heel-strike 등 H-Walker-specific 만 보유
- `examples/cable_robot/`, `examples/exoskeleton/` 같은 도메인 wrapper 예시 추가

---

## 자주 막히는 곳

### "Stats Toolbox 없다고 NaN"
```matlab
ver('stats')                           % 라이선스 확인
% 핵심 검정 (anova1, anovaRM, postHoc, bootstrap, leveneTest) 은
% 자체 fallback 이라 toolbox 없어도 정확하게 작동.
% ttest/signrank/lillietest 는 Stats Toolbox 가 있어야 함.
```

### "Sync 가 잘못 잡힘"
```matlab
% 신호 노이즈 → debounce 늘리기
cycles = hwalker.sync.findWindows(T, 'DebounceMs', 100);

% 임계값 수동
cycles = hwalker.sync.findWindows(T, 'Threshold', 0.5);
```

### "Stride 너무 많이 제외됨 (clinical 데이터)"
```matlab
[ft, mask, why] = hwalker.stride.filterIQR(rawTimes, ...
    'Multiplier', 3.0, 'Bounds', [0.2, 8.0]);
disp(why);    % 어떤 이유로 몇 개 제외인지
```

### "PDF 가 저널 사이즈와 안 맞음"
```matlab
% 출력된 PDF 직접 검증 (macOS):
!pdfinfo Fig1_TRO.pdf | grep "Page size"
% → 252.4 x 199.1 pts = 89.2 x 70.3 mm  (TRO 1col 88.9 x 70 ±0.3mm 이내)
```

### "Demo 가 에러"
```matlab
% MATLAB 버전 확인 (R2020a 이상 필요)
ver
% R2025b 면 OK
```

---

## 한 페이지 명령어 치트시트

```matlab
%%% 분석
r = hwalker.analyzeFile('/path/to/your.csv');

%%% 검정 자동 추천
hwalker.stats.decisionTree({a, b, c}, 'Design', 'between');

%%% 검정 실행
pt  = hwalker.stats.pairedTest(a, b);
av  = hwalker.stats.anova1({a, b, c});
arm = hwalker.stats.anovaRM(Y_NxK);
ph  = hwalker.stats.postHoc({a, b, c}, 'Method', 'tukey');
bs  = hwalker.stats.bootstrap(a, @median, 'NBoot', 5000, 'Seed', 42);

%%% Figure (단일 저널)
fig = hwalker.plot.forceQC(r, 'R', 'TRO');
hwalker.plot.exportFigure(fig, 'Fig1.pdf', hwalker.plot.journalPreset('TRO'));

%%% Figure (여러 저널 일괄)
hwalker.plot.exportAllJournals(@hwalker.plot.forceQC, {r,'R'}, '~/Desktop/figs', ...
    'Journals', {'TRO','RAL','JNER'});

%%% 저널 목록 / preset 상세
hwalker.plot.listJournals
disp(hwalker.plot.journalPreset('TRO'))

%%% 재현성
hwalker.meta.reproPackage(r, '~/Desktop/repro', 'InputCSV', '/path/to/your.csv');

%%% 사전 검증 (Copilot-style 경고)
hwalker.plot.preflightCheck(@hwalker.plot.forceQC, {r,'R'}, ...
    hwalker.plot.journalPreset('Nature'), 2);

%%% 도움말
help hwalker.stats.anovaRM
help hwalker.plot.journalPreset
edit example_01_paired_t_test
```
