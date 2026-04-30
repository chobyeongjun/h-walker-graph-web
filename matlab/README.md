# H-Walker MATLAB Toolbox

H-Walker 로봇 실험 CSV → 보행 지표 분석 → 저널 Figure 출력.

---

## 설치

**1. 이 폴더를 받는다**

```
git clone https://github.com/arlab-hwalker/h-walker-graph-web
```

또는 `matlab/` 폴더만 복사해도 됩니다.

**2. MATLAB에서 install.m 실행 (한 번만)**

```matlab
cd /path/to/matlab
install
```

startup.m에 경로를 자동 추가합니다. MATLAB 재시작 후 영구 적용됩니다.

**필요 툴박스**: Statistics and Machine Learning Toolbox

---

## 빠른 시작

```matlab
% 분석
results = hwalker.analyzeFile('260430_Robot_CBJ_TD_level_0_5_walker_high_0.csv');

% 기본 지표 확인
results(1).right.nStrides        % 오른쪽 stride 수
results(1).right.strideTimeMean  % 평균 stride time (s)
results(1).right.cadence         % cadence (steps/min)
results(1).rightForce.rmse       % force tracking RMSE (N)
results(1).strideTimeSymmetry    % 좌우 대칭 지수 (%)

% Force profile 시각화
hwalker.plot.forceQC(results(1), 'R')

% 논문 Figure 저장
preset = hwalker.plot.journalPreset('JNER');
fig = hwalker.plot.forceQC(results(1), 'R', 'JNER');
hwalker.plot.exportFigure(fig, 'Fig1_force.pdf', preset);
```

Sync 신호가 있는 파일은 자동으로 sync 구간마다 분석합니다.  
결과가 여러 개면 `results(1)`, `results(2)` ... 로 접근합니다.

---

## CSV 컬럼 규칙

H-Walker 펌웨어 출력 그대로 사용합니다.

| 컬럼 | 내용 |
|---|---|
| `Time_ms` | 타임스탬프 (ms) |
| `L_GCP` / `R_GCP` | 케이블 변위 (heel strike 검출용) |
| `L_ActForce_N` / `R_ActForce_N` | 실제 케이블 장력 (N) |
| `L_DesForce_N` / `R_DesForce_N` | 목표 케이블 장력 (N) |
| `L_Ax` / `L_Ay` | Global Velocity X/Y (m/s) — ZUPT 보폭 계산용 |
| `Sync` 또는 `A7` | 동기화 신호 (0/1) |

---

## 주요 함수

| 함수 | 용도 |
|---|---|
| `hwalker.analyzeFile(path)` | 파일 분석, sync 자동 분할 |
| `hwalker.plot.forceQC(result, side)` | Desired vs Actual force profile |
| `hwalker.plot.forceTracking(T, side, hs, mask, preset)` | Force tracking figure |
| `hwalker.plot.strideTrend(result, metric, preset)` | Stride-by-stride 추이 |
| `hwalker.plot.metricBar(means, stds, conds, sides, label, preset)` | 조건 비교 bar |
| `hwalker.plot.metricBox(data, conds, label, preset)` | 조건 비교 boxplot |
| `hwalker.plot.exportFigure(fig, filename, preset)` | PDF/PNG/TIFF 저장 |
| `hwalker.stats.pairedTest(a, b)` | paired t-test + Wilcoxon + Cohen's d |
| `hwalker.stats.symmetryIndex(l, r)` | 좌우 대칭 지수 |
| `hwalker.stats.fatigueIndex(times)` | 피로 지수 |
| `hwalker.sync.findWindows(T)` | Sync 구간 검출 |

저널 프리셋: `'IEEE'` `'Nature'` `'APA'` `'Elsevier'` `'MDPI'` `'JNER'`

---

## 테스트

```matlab
cd matlab
runAllTests
% === 44/44 passed ===
```

---

## 알고리즘 요약

- **Heel strike**: GCP sawtooth rising edge
- **Stride length**: ZUPT 속도 적분 (`L_Ax`/`L_Ay` = Global Velocity, 가속도 아님)
- **Sync**: falling→rising→falling = 1 cycle, 50ms 디바운스 적용
- **Cadence**: `60 / strideTime × 2` (1 stride = 2 steps)
