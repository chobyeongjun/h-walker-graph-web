# Multi-Modal H-Walker Experiment Pipeline

> 한 실험에서 **3종 데이터 (Robot + Motion/Force/EMG + Loadcell)** 를 받아서, 보조 방식 (assistance condition) 별로 비교하고, 논문 figure + 통계 까지 끝내는 전 과정.

**배경:** 사용자 연구 — 보조 방식에 따른 사람의 kinematic + multi-modal 변화.
**Setup:** H-Walker (cable robot) + treadmill + force plate + EMG + motion capture + loadcell BWS.

---

## 1. 폴더 구조 (강제 표준)

이 구조 그대로 따라야 toolbox 가 자동으로 매칭함.

```
~/h-walker-experiments/                    ← root (사용자가 정함, 어디든 OK)
├── studies/
│   └── 2026-05-04_assistance-comparison/  ← 한 실험 (study)
│       ├── README.md                       ← 실험 설계 메모 (손으로 작성)
│       ├── subjects.csv                    ← 피험자 목록 + 메타
│       │
│       ├── sub-01/                         ← 피험자 1
│       │   ├── meta.json                   ← 키, 몸무게, 나이, 우세발 등
│       │   │
│       │   ├── cond-baseline/              ← 보조 OFF
│       │   │   ├── robot.csv               ← H-Walker 펌웨어 출력
│       │   │   ├── motion.c3d              ← (또는 motion.csv) MoCap+Force
│       │   │   ├── emg.csv                 ← EMG 다채널
│       │   │   ├── force.csv               ← (motion.c3d 에 포함되면 생략 가능)
│       │   │   ├── loadcell.csv            ← BWS 로드셀
│       │   │   └── notes.md                ← 손으로 적은 trial 메모
│       │   │
│       │   ├── cond-low_assist/            ← 보조 LOW
│       │   │   └── (같은 5개 파일)
│       │   │
│       │   └── cond-high_assist/           ← 보조 HIGH
│       │       └── (같은 5개 파일)
│       │
│       ├── sub-02/  ...
│       ├── sub-03/  ...
│       │
│       └── analysis/                       ← toolbox 가 자동 생성
│           ├── per_subject/
│           │   ├── sub-01_results.mat
│           │   └── ...
│           ├── group_comparison.mat        ← 조건 간 통계
│           ├── figures/
│           │   ├── Fig1_kinematics_TRO.pdf
│           │   ├── Fig2_emg_TRO.pdf
│           │   ├── Fig3_robot_force_TRO.pdf
│           │   └── ... (저널별 6개)
│           └── repro/                      ← 재현성 패키지
```

### 명명 규약 (절대 변경 금지)

| 항목 | 규칙 | 예 |
|---|---|---|
| 피험자 | `sub-NN` (zero-padded) | `sub-01`, `sub-12` |
| 조건 폴더 | `cond-<name>` (소문자, 언더스코어) | `cond-baseline`, `cond-high_assist` |
| 파일명 | 고정된 5개: `robot.csv`, `motion.c3d` (or `.csv`), `emg.csv`, `force.csv`, `loadcell.csv` | |
| 메타 | `meta.json` per subject, `notes.md` per condition | |

### `meta.json` 형식

```json
{
  "subject_id": "sub-01",
  "age_years": 28,
  "height_cm": 175,
  "mass_kg": 72.0,
  "sex": "M",
  "dominant_leg": "R",
  "condition_order": ["baseline", "low_assist", "high_assist"],
  "wash_in_min": 3,
  "trial_min": 5,
  "BWS_pct": 30
}
```

### `subjects.csv` 형식

```
subject_id,age,sex,height_cm,mass_kg,group
sub-01,28,M,175,72.0,healthy
sub-02,31,F,162,55.5,healthy
...
```

---

## 2. 동기화 (sync) 전략

모든 modality 가 같은 trigger pulse 를 받아야 함. H-Walker firmware 의 `Sync` 또는 `A7` 컬럼이 마스터 신호.

```
              ┌─────────────────────────────────────┐
Trigger (TTL) │  ____|‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾|____ │
              │      ↑ Robot.Sync rising             │
              │      ↑ Motion.Channel-Sync rising    │
              │      ↑ EMG.AnalogIn-Sync rising      │
              │      ↑ Loadcell.DigitalIn rising     │
              └─────────────────────────────────────┘
```

`hwalker.experiment.loadSession` 이 각 modality 를 native sample rate 로 로드하고,
duration mismatch 가 1초 이상이면 콘솔에 경고를 출력. **각 modality 의 시간축은
독립으로 보존**되며, sync 정렬은 stride detection 시점에 robot side 의 GCP/sync
신호 기준으로 수행.

**Roadmap:** 단일 `hwalker.experiment.syncModalities` (모든 modality 를 공통
1000 Hz 시간축으로 리샘플) 는 다음 릴리스 예정. 현재는 robot 시간축을 master
로 사용.

---

## 3. 처리 파이프라인 (전 단계)

### Step 1: Session 로드
```matlab
session = hwalker.experiment.loadSession( ...
    '~/h-walker-experiments/studies/2026-05-04_assistance-comparison/sub-01/cond-baseline');
```

→ struct:
```
session.subject_id    = 'sub-01'
session.condition     = 'baseline'
session.fs_common     = 1000      % Hz (resampled common rate)
session.t             = [0 ... T] % sec, common time axis
session.robot         = (struct from analyzeFile)
session.motion        = (markers, joint angles)
session.force         = (GRF L/R, COP)
session.emg           = (channels, envelope, onset)
session.loadcell      = (BWS Newton, % body weight)
session.meta          = (loaded from meta.json)
session.qc            = (sample loss, sync accuracy, NaN counts)
```

### Step 2: Per-modality processing

| Modality | 처리 | 출력 metric |
|---|---|---|
| **Robot** | 이미 `analyzeFile` 으로 처리됨 | force RMSE/MAE, stride time, cadence, ZUPT length, symmetry |
| **Motion** | C3D parse → marker fill (gap < 100 ms) → 6 Hz Butterworth zero-phase low-pass → joint angle (Vicon plug-in-gait or IK) | hip/knee/ankle angle (sagittal/frontal), pelvic tilt, ROM |
| **Force plate** | 20 Hz low-pass → threshold detect heel-strike/toe-off → COP excursion | peak GRF (vertical/AP/ML), impulse, COP path, propulsion impulse |
| **EMG** | DC remove → 20-450 Hz Butterworth bandpass → full-wave rectify → 50 ms RMS → MVC normalize | onset/offset (Teager-Kaiser), amplitude % MVC, co-contraction (Falconer-Winter) |
| **Loadcell** | 10 Hz low-pass → calibration apply → mass divide | mean BWS (% body weight), variability |

### Step 3: Gait segmentation

Heel-strike events come from the H-Walker robot data (`hwalker.stride.detectHS`,
already invoked inside `analyzeFile`). Force-plate-based detection is exposed
via `hwalker.kinetics.grfFeatures` for the GRF channels separately. Per-stride
stitching across modalities (motion/EMG/loadcell aligned to robot strides)
is currently **simplified**: per-stride feature values for motion and GRF are
populated via the side-specific TRIAL summary (codex pass 9), not yet via
true per-stride re-windowing of the marker / EMG time-series.

**Roadmap:** `hwalker.experiment.detectStrides`, `normalizeStrides`,
`ensembleAverage` are planned for a follow-up release. Until then,
`hwalker.experiment.extractFeatures` returns per-stride robot features
combined with trial-level summary features for the optional modalities.

### Step 6: Feature extraction (per stride)

Stride 별 scalar metric (통계 검정용):

```matlab
features = hwalker.experiment.extractFeatures(norm, strides);
% → features struct:
%   .stride_time(1:N)      .cadence(1:N)
%   .step_length(1:N)
%   .knee_peak_flex(1:N)   .knee_ROM(1:N)
%   .hip_peak_flex(1:N)    .hip_ROM(1:N)
%   .ankle_peak_dorsi(1:N) .ankle_ROM(1:N)
%   .grf_peak_vert(1:N)    .grf_impulse_AP(1:N)
%   .emg_<muscle>_avg(1:N) .emg_<muscle>_peak(1:N)
%   .cocontraction_<pair>(1:N)
%   .robot_force_rmse(1:N) .robot_assistance_work(1:N)
%   .bws_pct(1:N)
%   ... (50+ scalar features)
```

---

## 4. 조건 간 비교 (statistical analysis)

```matlab
% 한 피험자의 3 조건 비교
conditions = hwalker.experiment.loadAllConditions( ...
    '~/h-walker-experiments/studies/2026-05-04_assistance-comparison/sub-01');
% → conditions(1) = baseline, (2) = low, (3) = high (cond-* 폴더 알파벳 순)

cmp = hwalker.experiment.compareConditions(conditions);
% → cmp.<feature>: struct with
%       .means(1:K)       .sds(1:K)
%       .anova_p          .anova_F
%       .post_hoc.pair_labels{}, .p_adj{}
%       .effect_size_omega2
%       .recommended_test  ('RM-ANOVA'|'Friedman'|...)
```

**자동 결정**:
- Within-subject (같은 피험자, 다른 조건) → RM-ANOVA + Greenhouse-Geisser
- 정규성 위반 (Lilliefors p < .05) → Friedman test
- ≥ 3 조건 → 사후검정 자동 (Tukey planned=false, Holm planned=true)

### 그룹 분석 (여러 피험자)

여러 피험자 그룹 분석은 직접 loop 으로 처리:

```matlab
studyRoot = '~/h-walker-experiments/studies/2026-05-04_assistance-comparison';
subDirs   = dir(fullfile(studyRoot, 'sub-*'));
all_cmp   = cell(numel(subDirs), 1);
for i = 1:numel(subDirs)
    cond_i = hwalker.experiment.loadAllConditions( ...
        fullfile(subDirs(i).folder, subDirs(i).name));
    all_cmp{i} = hwalker.experiment.compareConditions(cond_i, 'Design','within');
end
% group-level synthesis is left to the user; planned wrapper:
% hwalker.experiment.compareGroup() — coming in next release.
```

---

## 5. Figure 출력

논문 figure 는 `hwalker.plot.exportAllJournals` 를 직접 호출해서 만듬. `examples/example_07_multimodal_session.m` 의 STEP 5 참고.

```matlab
% Figure 1 — 로봇 force tracking, 5 robotics 저널 일괄
hwalker.plot.exportAllJournals( ...
    @hwalker.plot.forceQC, {conditions(1).robot(1), 'R'}, '~/Desktop/figs', ...
    'BaseName', 'Fig1_force', ...
    'Journals', {'TRO','RAL','TNSRE','JNER','SciRobotics'}, ...
    'Formats',  {'PDF','PNG'}, 'NCols', 2);

% Figure 2 — 조건별 metric bar + significance bracket
preset = hwalker.plot.journalPreset('TRO');
fig = hwalker.plot.metricBar(c.means(:)', c.sds(:)', ...
    c.condition_names, {'value'}, 'Knee Peak Flexion (°)', preset);
% post-hoc 별표 추가는 example_07 STEP 5 참고
hwalker.plot.exportFigure(fig, '~/Desktop/figs/Fig2_kneeFlex_TRO.pdf', preset);
```

권장 paper figure 세트 (수동 조립):
| Fig | 내용 |
|---|---|
| **1** | 실험 셋업 다이어그램 (사진 + 도식, 수동 작성) |
| **2** | Joint angle ensembles (hip/knee/ankle × condition) |
| **3** | GRF / COP × condition |
| **4** | EMG amplitude bar + co-contraction index |
| **5** | Robot force tracking — `hwalker.plot.forceQC` |
| **6** | BWS distribution + symmetry — `hwalker.plot.metricBar` |
| **7** | Multi-panel summary — `subplot` + `hwalker.plot.labelPanels` |

**Roadmap:** `hwalker.experiment.makeAllPaperFigures` 단일 호출 wrapper 는 다음 릴리스 예정.

---

## 6. Methods 섹션 자동 생성

```matlab
methods_text = hwalker.experiment.generateMethods(cmp);   % returns string
hwalker.experiment.generateMethods(cmp, 'OutFile', 'methods.md');  % also writes
% → 'methods.md' 자동 작성:
%
%   ## Data Acquisition
%   Three modalities were recorded at synchronized timestamps...
%   - Robot: H-Walker firmware (sample rate 100 Hz)
%   - Motion: Vicon Nexus C3D format (200 Hz markers, 1000 Hz GRF)
%   - EMG: Delsys Trigno (2000 Hz raw, processed to 1000 Hz envelope)
%
%   ## Signal Processing
%   Marker trajectories were low-pass filtered at 6 Hz (Butterworth, 4th order, zero-phase).
%   GRF was low-pass filtered at 20 Hz. EMG was bandpass-filtered (20-450 Hz),
%   full-wave rectified, RMS-windowed (50 ms), and MVC-normalized.
%
%   ## Statistical Analysis
%   Repeated-measures ANOVA with Greenhouse-Geisser correction was used to
%   compare the three assistance conditions. ...
```

→ 이걸 그대로 paper Methods 에 붙여넣음.

---

## 7. 재현성 패키지 (supplementary)

```matlab
hwalker.meta.reproPackage(conditions, ...
    '~/Desktop/paper_repro', ...
    'InputCSV', '~/h-walker-experiments/studies/2026-05-04_assistance-comparison');
```

→ supplementary 에 zip 으로 첨부.

---

## 8. 한 페이지 워크플로우 (실험 직후 → 논문)

```matlab
%%% Day 1 — 실험 직후
% 1. 데이터 폴더 정리 (sub-01/cond-baseline/robot.csv 형식)
% 2. meta.json 작성 (각 subject 폴더에)
% 3. subjects.csv 한 번 작성

%%% Day 2 — 분석
study = hwalker.experiment.loadGroup( ...
    '~/h-walker-experiments/studies/2026-05-04_assistance-comparison');
%   → 콘솔에 자동으로 QC 출력:
%     [sub-01/baseline] sync OK, robot 5832 samples, motion 11664, emg 116648
%     [sub-01/baseline] strides: L=24, R=24
%     [sub-01/low_assist] strides: L=23, R=24
%     ...

groupCmp = hwalker.experiment.compareGroup(study, 'Design', 'within');
%   → 콘솔:
%     stride_time: F(1.97, 21.69) = 9.51, p_GG = 0.0011, eta²p = 0.464
%     knee_peak_flex: F(2,30) = 5.21, p = 0.012, eta²p = 0.258
%     ...

%%% Day 3 — Figure
hwalker.experiment.makeAllPaperFigures(groupCmp, '~/Desktop/paper/figs', ...
    'Journals', {'TRO','RAL','TNSRE','JNER'});
%   → 28 PDF (7 fig × 4 journal) 생성

%%% Day 4 — Methods + Supplementary
hwalker.experiment.generateMethods(groupCmp, '~/Desktop/paper/methods.md');
hwalker.meta.reproPackage(groupCmp, '~/Desktop/paper/repro', ...
    'InputCSV', '~/h-walker-experiments/studies/2026-05-04_assistance-comparison');

%%% 그대로 paper 에 paste.
```

---

## 9. 시스템별 데이터 로더 호환성

이 toolbox 는 가장 흔한 system 들을 지원:

### Motion Capture
| 시스템 | 형식 | 자동 인식 |
|---|---|---|
| Vicon Nexus | `.c3d` (binary) | ✅ 자동 |
| Qualisys QTM | `.c3d` 또는 `.tsv` | ✅ 자동 |
| OptiTrack | `.csv` (export from Motive) | ✅ marker name 매핑 |
| Generic CSV | columns: `Time, Marker1_X, Marker1_Y, Marker1_Z, ...` | ✅ |

### Force Plate
| 시스템 | 형식 |
|---|---|
| Bertec instrumented treadmill | `.c3d` 내장 또는 `.csv` |
| AMTI | `.c3d` 또는 `.csv` |
| Kistler | `.txt` (탭 구분) 또는 `.c3d` |

### EMG
| 시스템 | 형식 |
|---|---|
| Delsys Trigno (16-ch) | `.csv` (sample rate 2000 Hz typical) |
| Noraxon Ultium | `.csv` |
| Generic | columns: `Time, EMG_RTibAnt, EMG_RGastrocLat, ...` |

### Loadcell (BWS)
| 시스템 | 형식 |
|---|---|
| Generic CSV | columns: `Time, Force_N` (또는 `BWS_pct`) |

→ 본인 시스템이 위에 없으면 `hwalker.experiment.loadSession` 의 `'CustomLoaders'` 옵션으로 plug-in 가능.

---

## 10. 흔한 함정

| 함정 | 증상 | 해결 |
|---|---|---|
| Sync 신호 어긋남 | 동기화 후 raw plot 에서 trial 시작이 modality 마다 다름 | Vicon trigger box 사용; 또는 모든 시스템에 동일 TTL 분배 |
| Marker dropout | C3D 에 NaN 다수 | `loadMotion('FillGaps', true)` 자동 spline 보간 (gap < 100 ms) |
| EMG cross-talk | 인접 근육 신호 섞임 | 6th-order Butterworth bandpass + ICA decomposition (수동) |
| BWS calibration drift | 연속 trial 간 mean BWS 가 슬금슬금 바뀜 | Trial 시작마다 zero-tare; `loadcell.csv` 첫 1초 mean 을 baseline 으로 차감 |
| Heel-strike 누락 | 첫/마지막 stride 미검출 | Force plate 임계치 `'HSThreshold', 30 → 20 N` 로 낮춤 |

---

## 11. 다음 스텝

- 실제 본인 데이터 1세션 로드 → 콘솔 QC 출력 보고 sync 정확성 확인
- `examples/example_07_multimodal_session.m` 참고하여 본인 폴더 구조에 맞춤
- 막히면 `hwalker.plot.preflightCheck` 가 자동으로 가이드 메시지

자세한 함수별 사용: `help hwalker.experiment.loadSession` 등.
