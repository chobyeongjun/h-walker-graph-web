# H-Walker 실험 데이터 업로드 가이드

피험자 한 명 측정 끝나면 → **한 줄 명령** 으로 표준화 + sync cut + ARLAB 공유 드라이브 자동 push.

---

## 0. 사전 준비 (한 번만)

```matlab
cd ~/h-walker-graph-web/matlab
install                  % addpath + runAllTests
```

ARLAB Google Drive Desktop 동기화 켜둘 것 (`admin@arlabcau.com`). 한국어 mac 이든 영어 mac 이든 helper 가 알아서 path 찾음.

---

## 1. raw 데이터 위치 — `~/assistive-vector-treadmill/data/`

피험자마다 한 폴더, 안에 modality 별 sub-folder.

```
~/assistive-vector-treadmill/data/
└── 260504_Sub01/                   ← 피험자 폴더 (YYMMDD_Sub<NN>)
    ├── Robot/                      ← H-Walker 펌웨어 CSV
    │   ├── high_0.csv  high_30.csv  low_0.csv  low_30.csv
    │   ├── low_45.csv  mid_0.csv   mid_30.csv
    ├── Loadcell/                   ← Loadcell CSV
    │   ├── high_0.csv  ...  noassist_wb_01.csv  noassist_wb_02.csv
    └── Motion/                     ← Qualisys .qtm
        ├── high_0.qtm  ...  noassist_nwb.qtm
        └── MVC_BF.qtm  MVC_GM.qtm  MVC_MG.qtm  MVC_RF.qtm  MVC_TA.qtm  Static.qtm
```

**파일명은 자유** (`high_0`, `High_0_01`, `robot_lkm_high_0` 등 모두 OK). helper 가 알아서 condition 추출.

**condition 표준 토큰:**
- 보조 trial: `high_0`, `high_30`, `mid_0`, `mid_30`, `low_0`, `low_30`, `low_45` (앞=shank mount, 뒤=각도 deg)
- 무보조: `noassist_wb` (with body weight), `noassist_nwb` (no body weight)
- 같은 condition multi-trial: `_01`, `_02` 접미사 (`noassist_wb_01`, `noassist_wb_02`)

---

## 2. 한 줄 명령 — 처리 + 푸시

피험자 측정 완료 직후 MATLAB Command Window:

```matlab
hwalker.experiment.uploadToARLAB( ...
    '~/assistive-vector-treadmill/data/260504_Sub01', ...
    'Subject',  'LKM', ...           % 피험자 이니셜
    'Speed',    '1_0', ...            % m/s (소수점 → 언더스코어, 1.0 → '1_0')
    'WeightKg', 80, ...               % 체중
    'Group',    '');                  % healthy=빈 문자열, 환자=Parkinson|Stroke|SCI
```

**자동 처리 단계:**
1. 표준 파일명으로 rename → `260504_Sub01_LKM/Raw/`
2. sync window 자동 검출 + cut → `260504_Sub01_LKM/Organized/`
3. ARLAB 3 위치 자동 push (Google Drive 동기화 자동)

---

## 3. 결과 layout — `~/assistive-vector-treadmill/data/260504_Sub01_LKM/`

```
260504_Sub01_LKM/                    ← 통합 subject root (자동 생성)
├── meta.json                        ← 모든 metadata (single source of truth)
├── Raw/                             ← 긴 파일명 (공유용, .qtm 보존)
│   ├── Robot/      260504_Robot_LKM_TD_level_1_0_H-Walker_high_0_01.csv  (긴 이름)
│   ├── Loadcell/   같은 패턴
│   ├── Motion/     같은 패턴 (.qtm)
│   └── Reference/  MVC_*.qtm  Static.qtm
└── Organized/                       ← 짧은 파일명, sync cut, 분석용
    ├── Robot/      robot_high_0.csv  robot_high_30.csv  ...
    ├── Loadcell/   loadcell_high_0.csv  ...  loadcell_noassist_wb_01.csv
    ├── Motion/     (Qualisys .mat export 시 자동 채워짐)
    └── Reference/  (.mat 시 자동)
```

**meta.json 안:** subject/date/speed/weight/group, conditions list, modalities-per-condition, force_profile (55-70-85% GCP, 50N, RMSE window), cuts (sync window per file), rename_map (raw → 표준 매핑).

---

## 4. ARLAB 푸시 위치 (Google Drive 자동 동기화)

| 위치 | 내용 |
|---|---|
| `06_MotionData_(데이터)/01.Normal_Gait/H-Walker/Robot/260504_Sub01_LKM/` | Raw/ 통째로 (긴 파일명, 공유 archive) |
| `02_Research_(연구)/[H-Walker]/03_Data/Paper_Works/00_Raw/260504_Sub01_LKM/` | Raw/ (paper raw 보존) |
| `02_Research_(연구)/[H-Walker]/03_Data/Paper_Works/Organized_Data/260504_Sub01_LKM/` | Organized/ (분석용) |

각 위치에 `meta.json` 동봉됨 → 단독으로 받아도 metadata 추적 가능.

---

## 5. 새 피험자 추가 (Sub02, Sub03, ...)

raw 폴더 만들고 **같은 명령에 path/Subject 만 바꿔 호출:**

```matlab
% 건강인
hwalker.experiment.uploadToARLAB( ...
    '~/assistive-vector-treadmill/data/260512_Sub02', ...
    'Subject', 'KCH', 'Speed', '1_0', 'WeightKg', 72);

% Parkinson 환자
hwalker.experiment.uploadToARLAB( ...
    '~/assistive-vector-treadmill/data/260520_Sub03', ...
    'Subject', 'PSM', 'Speed', '1_0', 'WeightKg', 75, ...
    'Group',   'Parkinson');
```

→ ARLAB 3 위치에 sibling 폴더 (`260512_Sub02_KCH/`, `260520_Sub03_PSM/`) 자동 추가. 기존 피험자는 그대로 유지.

---

## 6. Qualisys QTM 에서 .mat export 후

`Organized/Motion/` 와 `Organized/Reference/` 는 처음에는 비어있음 (Qualisys 원본 .qtm 은 binary 라 분석 불가). QTM 에서 .mat 으로 export 한 뒤:

1. .mat 파일을 raw `Motion/` 폴더에 추가 (또는 덮어쓰기)
2. 같은 `uploadToARLAB(...)` 명령 재실행
3. `Organized/Motion/motion_high_0.mat` 등 자동 생성 + ARLAB 동기화

---

## 7. 옵션

```matlab
hwalker.experiment.uploadToARLAB(rawDir, ...
    'Subject',     'LKM', ...
    'Speed',       '1_0', ...
    'Group',       '', ...
    'WeightKg',    80, ...
    'SubjectDir',  '', ...                  % default '<rawDir>_<Subject>'
    'WhichSegment','sync-complete', ...     % multi-segment CSV 처리법
    'PushArchive', true, ...                % 06_MotionData/Robot 으로 push
    'PushPaper',   true, ...                % Paper_Works/00_Raw + Organized_Data 로 push
    'DryRun',      false);                  % 미리보기만 (복사 안 함)
```

`'PushArchive', false, 'PushPaper', false` → 로컬에만 처리 (ARLAB 안 건드림).

---

## 8. 분석 시작 (push 안 끝나도 로컬 바로 가능)

```matlab
% 한 condition 다중 모달리티 통합
session = hwalker.experiment.loadSession( ...
    '~/assistive-vector-treadmill/data/260504_Sub01_LKM/Organized/Robot/robot_high_0.csv');

% 모든 condition 자동 비교 + 통계 검정 추천
conds = hwalker.experiment.loadAllConditions( ...
    '~/assistive-vector-treadmill/data/260504_Sub01_LKM/Organized');
cmp = hwalker.experiment.compareConditions(conds, 'Design','within');

% 17 저널 figure 일괄 출력
hwalker.plot.exportAllJournals(@hwalker.plot.forceQC, ...
    {session.robot, 'R'}, '~/figs', ...
    'Journals', {'TRO','RAL','TNSRE','JNER','SciRobotics'});
```

---

## 트러블슈팅

| 증상 | 원인 / 해결 |
|---|---|
| `ARLAB shared drive not mounted` | macOS 환경설정 → Google Drive Desktop → ARLAB 공유 드라이브 동기화 켜기 |
| `Subject is required` | `'Subject', 'LKM'` 인자 누락 |
| `rawDir not found` | path 오타. `ls ~/assistive-vector-treadmill/data/` 로 확인 |
| sync cut 결과 너무 짧음 (< 0.5s) | A7/Sync 신호가 trial 안에 한 cycle 안 됨. raw 직접 확인 |
| Robot CSV 안에 multi-trial 합쳐짐 (Teensy reset) | `'WhichSegment', 'sync-complete'` (default) — 자동 sync-OK 세그먼트 픽 |
| `_upload`/`_organized` 옛 폴더 남음 | v1 layout 잔존. 수동 삭제 OK |

---

## 핵심 함수 요약

| 함수 | 역할 |
|---|---|
| `hwalker.experiment.uploadToARLAB` | 한 줄 end-to-end (rename + organize + push) |
| `hwalker.experiment.renameRawToStandard` | 긴 표준 파일명만 (rename 만) |
| `hwalker.experiment.organizeStudy` | sync cut + meta.json 만 (organize 만) |
| `hwalker.experiment.writeMeta` | meta.json 만 작성/갱신 |
| `hwalker.experiment.loadSession` | 한 condition 다중 모달리티 로드 |
| `hwalker.experiment.compareConditions` | 모든 condition 통계 비교 |

상세는 각 함수의 `help hwalker.experiment.<함수명>` 또는 `matlab/docs/SESSION_HANDOFF.md`.
