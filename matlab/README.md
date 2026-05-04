# H-Walker MATLAB Toolbox

> H-Walker 케이블 드리븐 보행 재활 로봇 — CSV → 보행 분석 → 통계 → **저널 사이즈 그대로** Figure Export 까지 한 번에.

---

## 5분 Quickstart

```matlab
%% 1) 한 번만
cd /path/to/h-walker-graph-web/matlab
install                       % startup.m 자동 등록

%% 2) 데모 돌려보기 (합성 데이터로 전 기능 시연)
cd examples
demo

%% 3) 실제 데이터
results = hwalker.analyzeFile('260430_..._walker_high_0.csv');
results(1).right.cadence
results(1).rightForce.rmse

%% 4) 6 저널 한번에 export
hwalker.plot.exportAllJournals( ...
    @hwalker.plot.forceQC, {results(1), 'R'}, '~/paper/figures');
```

---

## 설치

```bash
git clone https://github.com/arlab-hwalker/h-walker-graph-web
```

MATLAB 에서:
```matlab
cd /path/to/h-walker-graph-web/matlab
install
```

`install.m` 가 `startup.m` 에 영구 경로 등록.

**필요 toolbox:** Statistics and Machine Learning Toolbox (없어도 fallback 동작 — 정확도 동일).

---

## 한 페이지 요약

### 데이터
| 컬럼 | 내용 |
|---|---|
| `Time_ms` | 타임스탬프 (ms) |
| `L_GCP` / `R_GCP` | 케이블 변위 (heel-strike sawtooth) |
| `L_ActForce_N` / `R_ActForce_N` | 실제 케이블 장력 (N) |
| `L_DesForce_N` / `R_DesForce_N` | 목표 케이블 장력 (N) |
| `L_Ax` / `L_Ay` | Global Velocity X/Y (ZUPT 보폭용) |
| `Sync` 또는 `A7` | 동기화 신호 (0/1) |

### 분석
| 함수 | 용도 |
|---|---|
| `hwalker.analyzeFile(path)` | 1-shot: CSV → struct (sync 자동 분할) |
| `hwalker.analyzeFolder(dir)` | 폴더 내 모든 CSV batch |

### 통계 — 어느 검정?
| 함수 | 언제 | 보고 항목 |
|---|---|---|
| `hwalker.stats.decisionTree(g, ...)` | **자동 추천** | 검정 + 사후검정 method + rationale |
| `hwalker.stats.pairedTest(a, b)` | 2 within | t, p, d_av/d_z/d_rm, Wilcoxon |
| `hwalker.stats.anova1(groups)` | 3+ between | F, p, ω², η², Cohen's f, Levene |
| `hwalker.stats.anovaRM(Y_NxK)` | 3+ within | F, GG/HF p, Mauchly W, partial η² |
| `hwalker.stats.postHoc(g, 'Method', M)` | 사후검정 | Tukey / Bonferroni / Holm / FDR |
| `hwalker.stats.bootstrap(x, fn)` | 분포-free CI | BCa-bootstrap |
| `hwalker.stats.leveneTest(g)` | 분산 동질성 | Brown-Forsythe |
| `hwalker.stats.symmetryIndex(L,R)` | 좌우 대칭 % | |
| `hwalker.stats.fatigueIndex(t)` | 피로 지수 (선형 추세) | |

### 시각화 (저널 사이즈 정확)
| 함수 | 용도 |
|---|---|
| `hwalker.plot.journalPreset(name)` | IEEE/Nature/APA/Elsevier/MDPI/JNER preset |
| `hwalker.plot.forceQC(r, side, j)` | Desired vs Actual force ±SD |
| `hwalker.plot.forceTracking(...)` | Force tracking aligned across strides |
| `hwalker.plot.strideTrend(r, m)` | 시간에 따른 stride metric 변화 |
| `hwalker.plot.metricBar(...)` | 조건 비교 bar + error bar |
| `hwalker.plot.metricBox(...)` | 조건 비교 boxplot |
| `hwalker.plot.multiConditionForce(...)` | 여러 조건 force overlay |
| `hwalker.plot.applyPreset(fig, ax, p)` | 저널 mm/font/stroke 적용 |
| `hwalker.plot.drawSignificance(ax,x1,x2,y,p)` | 통계 bracket + asterisk |
| `hwalker.plot.labelPanels(fig)` | 멀티패널 a/b/c 자동 라벨 |
| `hwalker.plot.exportFigure(fig, path, p)` | PDF/PNG/TIFF/EPS 저장 |
| `hwalker.plot.exportAllJournals(fn, args, dir)` | **6 저널 일괄** |
| `hwalker.plot.preflightCheck(fn, args, p)` | **Copilot-style** 사전 검증 |

### 재현성
| 함수 | 용도 |
|---|---|
| `hwalker.meta.reproPackage(r, dir, ...)` | input hash + git commit + result snapshot |
| `hwalker.meta.loadRepro(dir)` | 저장된 패키지 로드 + 무결성 검증 |

---

## 저널 Preset (verified spec)

| 저널 | 1-col mm | 2-col mm | 폰트 | Body pt | Stroke pt | DPI | 팔레트 |
|---|---|---|---|---|---|---|---|
| IEEE | 88.9 × 70 | 181 × 90 | Times | 8 | 1.0 | 600 | grayscale |
| Nature | 89 × 60 | 183 × 90 | Helvetica | 7 | 0.5 | 300 | Wong (CB-safe) |
| APA | 85 × 65 | 174 × 100 | Arial | 10 | 0.75 | 300 | grayscale |
| Elsevier | 90 × 60 | 190 × 90 (1.5col 140×80) | Arial | 8 | 0.5 | 300 | default |
| MDPI | 85 × 65 | 170 × 90 | Palatino | 8 | 0.75 | 1000 | default |
| JNER | 85 × 65 | 170 × 90 | Arial | 8 | 0.75 | 300 | Wong (CB-safe) |

CLAUDE.md authoritative table 과 일치 — `tests/PresetParityTest.m` 가 회귀 보호.

---

## 알고리즘 요약

- **Heel strike**: GCP sawtooth rising edge
- **Stride QC**: IQR 2× + [0.3, 5.0] s bound — 제외 stride 카운트 콘솔 출력 + `result.right.qcReasons` 보고
- **Stride length**: ZUPT 속도 적분 (`L_Ax`/`L_Ay` = Global Velocity)
- **Stance/Swing**: GCP duty cycle
- **Sync**: falling→rising→falling = 1 cycle, debounce 파라미터화 (`'DebounceMs', 50`)
- **Cadence**: `60 / strideTime × 2` (1 stride = 2 steps)
- **Force tracking**: stride 정렬 후 RMSE / MAE / peak error
- **Symmetry**: `2|L−R| / (|L|+|R|) × 100` (Robinson)
- **Fatigue**: linear regression slope of stride time

---

## 문서

- 사용자 가이드 (한국어, step-by-step): [docs/USER_GUIDE.md](docs/USER_GUIDE.md)
- 통계 결정 트리 (시각): [docs/STATS_DECISION_TREE.md](docs/STATS_DECISION_TREE.md)
- 인터랙티브 결정 트리 (HTML): `docs/decision_tree.html` (브라우저로 직접 열기)
- 데모 스크립트: [examples/demo.m](examples/demo.m)
- 함수별 상세: 각 `.m` 파일 doc block (`help hwalker.stats.anova1` 등)

---

## 테스트

```matlab
cd matlab
runAllTests
% === 70+/70+ passed ===   (44 기존 + 신규 stats/plot/meta)
```

테스트 클래스:
- `IOTest`, `SyncTest`, `StrideTest`, `ForceTest` (기존)
- `StatsAnovaTest`, `StatsBootstrapTest`, `PairedTestVariantsTest` (신규)
- `PresetParityTest`, `PreflightTest` (신규)
- `ReproTest` (신규)

---

## Roadmap

- [ ] Phase F: `+robolab/` 일반화 — 다른 로봇 도메인 재사용
- [ ] `+stats/anovaMixed.m` — between × within 혼합 디자인
- [ ] `+stats/lmm.m` — linear mixed-effects model
- [ ] `+stats/power.m` — sample size / power 계산 wrapper
- [ ] `examples/cable_robot/`, `examples/exoskeleton/` 도메인 wrapper 예시

기여: `docs/verification/` 의 codex 검증 라운드 통과 후 PR.
