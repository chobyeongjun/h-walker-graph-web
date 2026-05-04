# H-Walker MATLAB Toolbox — 사용자 가이드

> H-Walker (케이블 드리븐 보행 재활 로봇) CSV → 보행 분석 → 통계 → **저널 사이즈 그대로** 의 Figure 까지 한 번에.
> ARLAB · 조병준 · 최종 업데이트 2026-05-04

---

## 0. 5분 Quickstart

```matlab
%% 1) 한 번만: 경로 추가
cd /path/to/h-walker-graph-web/matlab
install      % startup.m 에 영구 등록

%% 2) 분석
results = hwalker.analyzeFile('260430_Robot_CBJ_TD_level_0_5_walker_high_0.csv');

%% 3) 가장 자주 쓰는 결과
results(1).right.nStrides           % 우측 stride 수
results(1).right.strideTimeMean     % 평균 stride time (s)
results(1).right.cadence            % cadence (steps/min)
results(1).rightForce.rmse          % force tracking RMSE (N)
results(1).strideTimeSymmetry       % 좌우 비대칭 지수 (%)
results(1).right.qcReasons          % stride 제외 통계  ← Methods 섹션에 보고

%% 4) 통계 (2 조건 비교)
r = hwalker.stats.pairedTest(pre.left.strideTimes, post.left.strideTimes);
fprintf('p = %.3g, Cohen''s d_av = %.2f\n', r.p_ttest, r.cohens_d);

%% 5) 통계 (3+ 조건 비교)
groups = {baseline.right.strideTimes, low.right.strideTimes, high.right.strideTimes};
a = hwalker.stats.anova1(groups, 'GroupNames', {'baseline','low','high'});
ph = hwalker.stats.postHoc(groups, 'Method', 'tukey', ...
                                   'GroupNames', {'baseline','low','high'});

%% 6) 논문 Figure — 6 저널 한번에 export
hwalker.plot.exportAllJournals( ...
    @hwalker.plot.forceQC, {results(1), 'R'}, '~/paper/figures', ...
    'BaseName', 'Fig1_force', 'Formats', {'PDF','PNG'});
```

---

## 1. 설치 & 첫 실행

```bash
git clone https://github.com/arlab-hwalker/h-walker-graph-web
```

MATLAB 에서:
```matlab
cd /path/to/h-walker-graph-web/matlab
install
```

`install.m` 가 자동으로 `startup.m` 에 경로를 추가합니다. **MATLAB 재시작 후 영구 적용**.

**필요 툴박스**:
- Statistics and Machine Learning Toolbox — `ttest`, `signrank`, `lillietest`, `fcdf`, `tcdf`
  → 없으면 핵심 검정 fallback 으로 동작 (정확도 동일, 속도만 약간 느려짐)

---

## 2. 데이터 로드 → 분석

### 2.1 CSV 컬럼 규칙

H-Walker 펌웨어 출력 그대로 사용. 핵심 컬럼:

| 컬럼 | 내용 | 단위 |
|---|---|---|
| `Time_ms` 또는 `Time_s` | 타임스탬프 | ms / s |
| `L_GCP` / `R_GCP` | 케이블 변위 (heel-strike 검출 sawtooth) | rad |
| `L_ActForce_N` / `R_ActForce_N` | 실제 케이블 장력 | N |
| `L_DesForce_N` / `R_DesForce_N` | 목표 케이블 장력 | N |
| `L_Ax` / `L_Ay` | Global Velocity X/Y (ZUPT 보폭 적분용) | m/s |
| `Sync` 또는 `A7` | 동기화 신호 (0/1 bool) | - |

### 2.2 분석 한 줄

```matlab
results = hwalker.analyzeFile('260430_..._walker_high_0.csv');
```

**자동 동작:**
1. CSV 로드 (`hwalker.io.loadCSV` — 헤더/타입 자동 검출)
2. Sync 신호 검출 (`hwalker.sync.findWindows` — 50 ms debounce 기본)
3. 0개 → 전체 파일 분석, 1개 → 단일 윈도우, N 개 → struct array (각 sync 별)
4. 좌/우 각 side 마다:
   - GCP heel-strike 검출 → stride time
   - **Stride QC**: IQR 2× + [0.3, 5.0] s bound — 제외된 stride 콘솔 출력
   - Stance/Swing % (GCP duty cycle)
   - ZUPT 보폭 (속도 적분)
   - Force tracking RMSE/MAE
   - Normalized force profile (0-100% gait cycle)
5. 좌우 대칭 지수 (4가지)
6. 피로 지수 (stride time linear trend)

### 2.3 콘솔 출력 예시

```
  [sync1] 260430_..._sync1  (2842 samples, 28.4 s, 100.0 Hz)
    L: 24 strides, T=1.180±0.087 s, cadence=101.7 steps/min
    L strideQC: kept 24/26 (excluded: 1 IQR-outlier, 0 < 0.30s, 1 > 5.00s)
    L force: RMSE=18.32 N, MAE=14.71 N, peak=42.18 N
    R: 24 strides, T=1.181±0.085 s, cadence=101.6 steps/min
    R strideQC: kept 24/26 (excluded: 2 IQR-outlier, 0 < 0.30s, 0 > 5.00s)
    R force: RMSE=17.04 N, MAE=13.92 N, peak=40.81 N
```

→ Methods 섹션에 그대로 인용 가능: *"Strides outside [0.3, 5.0] s or beyond 2× IQR
were excluded (mean 2.0/26 = 7.7 % per side)."*

---

## 3. 통계 — 어떤 검정을 쓸까?

### 3.1 빠른 결정

`hwalker.stats.decisionTree` 가 자동으로 추천해 줍니다:

```matlab
groups = {baseline.right.strideTimes, low.right.strideTimes, high.right.strideTimes};
rec    = hwalker.stats.decisionTree(groups, 'Design', 'between', 'Planned', false);
disp(rec.rationale);
```

→
```
Design = between, k = 3 groups/conditions.
Normality (Lilliefors): min p across groups = 0.241 → OK.
Homogeneity (Brown-Forsythe Levene): p = 0.418 → OK.
→ Recommended: One-way ANOVA
→ Post-hoc (k>2): tukey (planned=0)
```

### 3.2 결정 트리 (시각)

`docs/STATS_DECISION_TREE.md` 참고. 요약:

```
  데이터 형태?
    ├─ 같은 피험자 N 명, 다른 조건 K 개 (within)
    │   ├─ K=2 → paired t-test (정규성) / Wilcoxon (비정규)
    │   └─ K≥3 → RM-ANOVA + GG correction / Friedman
    └─ 다른 피험자 그룹 K 개 (between)
        ├─ K=2 → Welch t-test / Mann-Whitney U
        └─ K≥3 → One-way ANOVA + post-hoc / Kruskal-Wallis
```

### 3.3 모듈별 사용법

| 함수 | 언제 |
|---|---|
| `hwalker.stats.pairedTest(a, b)` | 2 조건 within-subject (정규성 자동 체크) |
| `hwalker.stats.anova1(groups)` | 3+ between-subject |
| `hwalker.stats.anovaRM(Y_NxK)` | 3+ within-subject (Greenhouse-Geisser 자동) |
| `hwalker.stats.postHoc(groups, 'Method', M)` | ANOVA 유의 후 사후검정 (tukey/bonferroni/holm/fdr) |
| `hwalker.stats.bootstrap(x, @mean)` | BCa-bootstrap CI (분포 가정 없음) |
| `hwalker.stats.leveneTest(groups)` | 분산 동질성 (Brown-Forsythe) |
| `hwalker.stats.symmetryIndex(L, R)` | 좌우 비대칭 % |
| `hwalker.stats.fatigueIndex(stride_times)` | 시간에 따른 stride time 변화 (linear trend) |

### 3.4 효과 크기 (Effect Size) — 논문 필수

| 검정 | 효과 크기 | 어디 |
|---|---|---|
| paired t-test | Cohen's `d_av`, `d_z`, `d_rm` | `r.cohens_d_variants` |
| One-way ANOVA | `η²`, `ω²`, Cohen's `f` | `a.eta2`, `a.omega2`, `a.cohens_f` |
| RM-ANOVA | partial η², generalized η² | `a.eta2_partial`, `a.eta2_generalized` |

**기본 보고 권장**: paired → `d_av` (Cumming 2012), ANOVA → `ω²` (less biased than η²).

---

## 4. 논문 Figure — 6 저널 한 번에

### 4.1 단일 Figure, 단일 저널

```matlab
preset = hwalker.plot.journalPreset('Nature');
fig    = hwalker.plot.forceQC(results(1), 'R', 'Nature');
hwalker.plot.exportFigure(fig, 'Fig1_force_Nature.pdf', preset);
```

### 4.2 한 Figure, 6 저널 일괄

```matlab
hwalker.plot.exportAllJournals( ...
    @hwalker.plot.forceQC, {results(1), 'R'}, '~/paper/figures', ...
    'BaseName', 'Fig1_force', ...
    'Formats',  {'PDF','PNG'}, ...
    'NCols',    2);
```

→ `Fig1_force_IEEE.pdf`, `Fig1_force_Nature.pdf`, ..., `Fig1_force_JNER.pdf` (×2 formats = 12 files).

자동 동작:
1. 각 저널 preset 로드
2. `preflightCheck` 자동 실행 (폰트 설치 여부 / 결과 struct 비어있는지 / 사이즈 비현실적인지 등 경고)
3. plot 함수 호출 + applyPreset 적용
4. 저널별 mm × mm 정확한 PDF/PNG 출력
5. 콘솔에 `12/12 files written` 같이 매니페스트 요약

### 4.3 통계 annotation

```matlab
preset = hwalker.plot.journalPreset('JNER');
fig = hwalker.plot.metricBar([m1; m2], [s1; s2], {'Pre','Post'}, {'L','R'}, ...
                              'Stride Time (s)', preset);
ax = gca;
% bar 1, bar 2 사이에 ** 표시
hwalker.plot.drawSignificance(ax, 1, 2, max(ylim)*0.95, 0.003, ...
                               'Style', 'asterisk', 'Preset', preset);
```

### 4.4 Multi-panel a/b/c 라벨

```matlab
fig = figure;
subplot(2,2,1); plot(...); title('Force');
subplot(2,2,2); plot(...); title('Stride Time');
subplot(2,2,3); plot(...); title('Symmetry');
subplot(2,2,4); plot(...); title('Cadence');
preset = hwalker.plot.journalPreset('Nature');
hwalker.plot.labelPanels(fig, 'Style', 'lowercase-bold', 'Preset', preset);
```

---

## 5. Pre-flight 검증 (Copilot-style 경고)

`hwalker.plot.preflightCheck` 가 plot 호출 **전에** 다음을 체크:

| 체크 | 출력 |
|---|---|
| plotFn 이 함수 핸들이 아님 | `[CRITICAL]` |
| preset 에 필수 필드 누락 | `[CRITICAL]` |
| nCols=1.5 인데 Elsevier 가 아님 | `[CRITICAL]` |
| 폰트가 시스템에 설치 안 됨 | `[WARN]` (substitute 됨) |
| bodyPt < 6 (비현실적으로 작음) | `[WARN]` |
| DPI ≥ 1000 인데 raster 출력 (파일 너무 큼) | `[INFO]` |
| `result.<side>.nStrides == 0` (빈 데이터로 plot) | `[CRITICAL]` |
| Aspect ratio > 2:1 (가로로 매우 넓음) | `[INFO]` |

**자동 호출**: `exportAllJournals` 가 매번 실행. **수동 호출**:

```matlab
hwalker.plot.preflightCheck(@hwalker.plot.forceQC, {results(1),'R'}, ...
                             hwalker.plot.journalPreset('Nature'), 2);
```

---

## 6. 재현성 패키지 (Supplementary 첨부용)

```matlab
results = hwalker.analyzeFile('mydata.csv');
info = hwalker.meta.reproPackage(results, '~/paper/repro', ...
           'InputCSV', 'mydata.csv', ...
           'Parameters', struct('alpha', 0.05, 'iqrK', 2.0));
```

`~/paper/repro/<timestamp>/` 에 다음을 저장:

| 파일 | 내용 |
|---|---|
| `result.mat` | 전체 result struct (binary) |
| `result.json` | 동일 (human-readable) |
| `parameters.json` | 사용된 분석 파라미터 |
| `environment.json` | MATLAB 버전, OS, hostname, toolbox 목록, **git commit** |
| `input_hash.txt` | input CSV 의 SHA-256 |
| `journal_presets.json` | 6 저널 preset snapshot |
| `README.txt` | 모든 파일 설명 |

**다시 로드** + 무결성 검증:

```matlab
pkg = hwalker.meta.loadRepro('~/paper/repro/20260504T120000');
% 콘솔에:
%   Original commit : 82a06f3...   (current: 82a06f3...)  [MATCH]
%   MATLAB version  : ...           (current: ...)         [MATCH]
%   Input CSV hash  : ab12cd34...   [MATCH]
```

이 패키지를 paper 의 supplementary 에 통째로 첨부하면 누구나 비트 단위 동일한 분석을 재현할 수 있습니다.

---

## 7. 자주 막히는 곳 / Troubleshooting

### "Stats Toolbox 없다고 NaN 만 나와요"

```matlab
% 핵심 검정은 fallback 구현이 있어 정상 동작합니다 (anova1, anovaRM, postHoc, bootstrap, leveneTest).
% 단 ttest/signrank/lillietest 는 native MATLAB 에 없으므로 t/signrank p-value 는 NaN 됨.
% → Stats Toolbox 라이선스 필요.
ver('stats')   % 라이선스 확인
```

### "PDF 가 저널 사이즈가 안 맞아요"

```matlab
% 이전 버그 (heightIn = widthIn * 0.75) 는 이미 수정됨.
% 확인:
preset = hwalker.plot.journalPreset('Nature');
fprintf('1col: %.1f x %.1f mm\n', preset.col1mm, preset.col1h_mm);
fprintf('2col: %.1f x %.1f mm\n', preset.col2mm, preset.col2h_mm);

% 출력된 PDF 직접 검증 (macOS):
% !sips -g pixelWidth -g pixelHeight Fig1_*.pdf
% 또는 ImageMagick:
% !identify -format '%[fx:w/2.835] x %[fx:h/2.835] mm\n' Fig1_*.pdf
```

### "Sync 가 잘못 잡혀요"

```matlab
% 신호가 노이지 → debounce 늘리기
cycles = hwalker.sync.findWindows(T, 'DebounceMs', 100);

% 임계값 수동 지정
cycles = hwalker.sync.findWindows(T, 'Threshold', 0.5);

% 다른 컬럼 사용
cycles = hwalker.sync.findWindows(T, 'SyncColumn', 'A7');
```

### "Stride time bound 가 너무 좁아요 (clinical 데이터)"

```matlab
% IQR + bound 수동 조정
[ft, mask, why] = hwalker.stride.filterIQR(rawTimes, ...
    'Multiplier', 3.0, 'Bounds', [0.2, 8.0]);
disp(why);    % 어떤 이유로 몇 개 제외됐는지
```

### "Demo 어떻게 돌려요?"

```matlab
cd matlab/examples
demo
% → 합성 데이터 → 분석 → 통계 → 6 저널 export → ./out/ 폴더 자동 열림
```

---

## 8. 더 알고 싶으면

- 통계 결정 트리 (시각): [STATS_DECISION_TREE.md](STATS_DECISION_TREE.md)
- 인터랙티브 결정 트리 (HTML): `matlab/docs/decision_tree.html` (브라우저로 직접 열기)
- 알고리즘 디테일: 각 함수의 `help <function>` (모든 함수에 doc block 있음)
- 코드 베이스 구조: `../README.md`
- 검증 로그: `docs/verification/codex_pass_*.md` (codex 검증 라운드별)

---

## 9. 한 줄 명령어 치트시트

```matlab
% 분석
r = hwalker.analyzeFile('data.csv');

% 검정 자동 추천
hwalker.stats.decisionTree({a, b, c}, 'Design', 'between');

% 검정 실행
pt  = hwalker.stats.pairedTest(a, b);
av  = hwalker.stats.anova1({a,b,c});
arm = hwalker.stats.anovaRM(Y_NxK);
ph  = hwalker.stats.postHoc({a,b,c}, 'Method', 'tukey');
bs  = hwalker.stats.bootstrap(a, @median, 'NBoot', 5000);

% Figure
fig = hwalker.plot.forceQC(r, 'R', 'JNER');
hwalker.plot.exportFigure(fig, 'Fig1.pdf', hwalker.plot.journalPreset('JNER'));

% 6 저널 일괄
hwalker.plot.exportAllJournals(@hwalker.plot.forceQC, {r,'R'}, './out');

% 재현성
hwalker.meta.reproPackage(r, './repro', 'InputCSV', 'data.csv');

% 검증
hwalker.plot.preflightCheck(@hwalker.plot.forceQC, {r,'R'}, ...
    hwalker.plot.journalPreset('Nature'), 2);
```
