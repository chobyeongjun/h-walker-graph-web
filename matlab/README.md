# H-Walker MATLAB Toolbox

H-Walker 실험 CSV → 보행 지표 분석 → 저널 Figure Export 원툴 패키지.

## 설치 (한 번만)

```matlab
addpath('/path/to/h-walker-graph-web/matlab');
```

또는 MATLAB 시작 시 자동 실행되도록 `startup.m`에 추가.

---

## 빠른 시작

### 1. 폴더 하나로 전체 분석

```matlab
% UI에서 데이터 폴더 선택 → Robot-type CSV 자동 발견 → 분석 → 저장
results = hwalker.analyzeFolder();

% 또는 경로 직접 지정
results = hwalker.analyzeFolder('/data/Pilot03');
```

출력: `<folder>/analysis_output/` 에 `*_strides.csv` + `*_result.mat`

### 2. 단일 파일 분석

```matlab
r = hwalker.analyzeFile('/data/Robot_S01_walk_T01.csv');

r.left.nStrides          % 왼쪽 보행 수
r.left.strideTimeMean    % 평균 보행 주기 (s)
r.left.cadence           % 케이던스 (steps/min)
r.left.stancePctMean     % 평균 stance % (GCP 기반)
r.leftForce.rmse         % force tracking RMSE (N)
r.strideTimeSymmetry     % 좌우 비대칭 지수 (%)
```

### 3. 저널 Figure 생성 + 저장

```matlab
T      = hwalker.io.loadCSV(r.filepath);
preset = hwalker.plot.journalPreset('IEEE');    % IEEE 1열: 88.9mm, 600dpi

% Force tracking figure
fig = hwalker.plot.forceTracking(T, 'L', ...
    r.left.hsIndices, r.left.validMask, preset, 1);
hwalker.plot.exportFigure(fig, 'Fig1_force.pdf', preset);  % vector PDF

% Stride trend figure (PNG, Nature 2열)
preset2 = hwalker.plot.journalPreset('Nature');
fig2 = hwalker.plot.strideTrend(r, 'strideTime', preset2, 2);
hwalker.plot.exportFigure(fig2, 'Fig2_trend.png', preset2);
```

### 4. Sync window 추출 (per-sync inspector)

```matlab
cycles = hwalker.sync.findWindows(T);       % Nx2 [t_start, t_end] seconds
Tw1    = hwalker.sync.extractWindow(T, cycles(1,1), cycles(1,2));
% Tw1 = sync #1 구간만 잘라낸 table, 시간축 0부터 rebase됨
```

---

## 패키지 구조

```
matlab/
├── +hwalker/
│   ├── analyzeFolder.m      ← 진입점: 폴더 → 전체 분석
│   ├── analyzeFile.m        ← 단일 파일 분석
│   ├── +io/
│   │   ├── loadCSV.m           BOM/중복헤더/units행 자동 처리
│   │   ├── timeAxis.m          초 단위 시간축 반환
│   │   ├── estimateSampleRate.m Time_ms→Hz, fallback 111Hz
│   │   ├── detectSourceKind.m  Robot/Loadcell/Motion/Unknown
│   │   ├── parseFilename.m     9-token 파싱 (source/subject/cond/trial)
│   │   └── resultToTable.m     결과 struct → per-stride table
│   ├── +sync/
│   │   ├── findWindows.m       sync 사이클 검출 [t_start, t_end]
│   │   └── extractWindow.m     시간 구간 슬라이싱 + rebase
│   ├── +stride/
│   │   ├── detectHS.m          GCP rising edge (primary) / Event fallback
│   │   ├── filterIQR.m         IQR 이상치 필터 [0.3s, 5.0s]
│   │   ├── detectZUPT.m        자이로 크기 < 50 deg/s → ZUPT mask
│   │   ├── lengthZUPT.m        ZUPT 속도 적분 → 보폭 (m)
│   │   └── stanceSwing.m       GCP active fraction → stance/swing %
│   ├── +force/
│   │   ├── trackingError.m     Des vs Act → RMSE/MAE/peak per stride
│   │   └── normalizedProfile.m 101포인트 GCP-정규화 force profile
│   ├── +stats/
│   │   ├── symmetryIndex.m     |L-R| / mean(L,R) × 100
│   │   └── fatigueIndex.m      first 10% vs last 10% % change
│   └── +plot/
│       ├── journalPreset.m     IEEE/Nature/APA/Elsevier/MDPI/JNER 스펙
│       ├── applyPreset.m       figure 크기/폰트/선굵기 적용
│       ├── exportFigure.m      exportgraphics 래퍼 (PDF/PNG/TIFF/EPS)
│       ├── forceTracking.m     Des vs Act + ±1SD envelope
│       └── strideTrend.m       stride-by-stride 추이 + mean line
└── tests/
    ├── runAllTests.m        ← `runAllTests()` 한 줄로 전체 실행
    ├── SyncTest.m           sync 검출 7개 회귀
    ├── IOTest.m             IO + stats 14개 회귀
    ├── StrideTest.m         stride 검출/ZUPT/stance 10개 회귀
    └── ForceTest.m          force tracking/profile 7개 회귀
```

---

## 저널 스펙 (검증 완료)

| 저널     | 1열 mm | 2열 mm | 폰트              | pt | 선굵기 | DPI  | 팔레트   |
|----------|--------|--------|-------------------|----|--------|------|----------|
| IEEE     | 88.9   | 181    | Times New Roman   | 8  | 1.0    | 600  | grayscale|
| Nature   | 89     | 183    | Helvetica         | 7  | 0.5    | 300  | Wong     |
| APA      | 85     | 174    | Arial             | 10 | 0.75   | 300  | grayscale|
| Elsevier | 90     | 190    | Arial             | 8  | 0.5    | 300  | default  |
| MDPI     | 85     | 170    | Palatino Linotype | 8  | 0.75   | 1000 | default  |
| JNER     | 85     | 170    | Arial             | 8  | 0.75   | 300  | Wong     |

---

## 테스트 실행

```matlab
addpath('matlab');
runAllTests()
% === 38/38 passed ===
```

---

## 알고리즘 노트

### GCP 기반 Heel Strike 검출
GCP 컬럼 sawtooth가 0→1+ 로 올라가는 순간(rising edge) = heel strike.
`Event` 컬럼 fallback: median gap < 0.7 s (step signal) 이면 every-other edge만 취함.

### ZUPT 속도 적분
`L_Ax`/`L_Ay` = EBIMU soa5 Global Velocity (m/s) — 가속도 아님.  
자이로 크기 < 50 deg/s 구간 = mid-stance (ZUPT).  
offset 누적 방식 (hard-zero 아님): 마지막 ZUPT frame의 raw velocity를 offset으로 저장, 이후 모든 frame에서 뺌.

### Cadence
`cadence = 60 / strideTime * 2`  
한 stride = 같은 쪽 발의 연속 heel strike 사이 = 2 steps (L + R).  
`* 2` 빼면 값이 절반이 됨 — 절대 생략하지 말 것.

### Sync 사이클
"falling edge 후 rising edge 부터 다시 falling edge 까지가 1 sync."  
`findWindows` 반환값: `[t_falling_i, t_falling_{i+1}]`.
