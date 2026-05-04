# CLAUDE.md — H-Walker MATLAB Toolbox

**새 Claude 세션이 이 레포에 들어왔을 때 먼저 읽어야 할 컨텍스트.**

---

## 가장 중요한 한 줄

이 repo 는 **MATLAB toolbox 만**입니다. (이전 web app — frontend/backend/desktop — 는 2026-05-04 에 모두 제거됨. git history 에 남아있어 필요시 복구 가능: `git log --all -- frontend/`).

---

## 👤 사용자

- 조병준 (ARLAB, 케이블 드리븐 보행 재활 로봇 "H-Walker" 연구자)
- 한국어 소통, 직접적이고 간결한 답변 선호
- `python` 아닌 `python3` 사용 (MATLAB toolbox 는 Python 의존성 없음)
- Git 커밋 메시지에 **Claude/AI 흔적 절대 금지** (`Co-Authored-By`, PR 본문 등)
- 로컬 경로: `~/h-walker-graph-web` (= 이 레포)
- 다른 프로젝트: `~/research-vault` (vault), `~/skiro` (learning capture)

---

## 🎯 이 레포의 정체

**H-Walker (cable-driven gait rehab robot) 실험 데이터 → 논문 직행 figure + 통계 + 재현성 패키지** 까지 한 번에 처리하는 MATLAB toolbox.

- 입력: H-Walker 펌웨어 CSV + (옵션) Motion C3D + EMG + Loadcell BWS
- 출력: 17 저널 (T-RO/RA-L/TNSRE 등) 정확 mm × mm figure + ANOVA/RM-ANOVA/post-hoc/bootstrap 통계 + supplementary 재현성 패키지

## 가장 빠른 컨텍스트 복원
**`matlab/docs/SESSION_HANDOFF.md`** 한 페이지에 모든 핵심 정리됨 — 30초 미션, 핵심 함수 5개, 폴더 표준, codex 10-pass 검증 결과, 함정, 다음 작업 후보. 새 세션은 이 파일부터 읽기.

---

## 🧱 기술 스택

- MATLAB R2020a+ (개발은 R2025b)
- Statistics and Machine Learning Toolbox (선택; 없어도 핵심 검정 fallback 동작)
- ezc3d (선택; C3D 파일 처리시 권장)
- 외부 의존성 없음 — 순수 MATLAB

---

## 📁 주요 경로

```
h-walker-graph-web/
├── CLAUDE.md                      ← 너 지금 여기
├── README.md
└── matlab/
    ├── install.m  runAllTests 입구
    ├── README.md
    ├── docs/
    │   ├── SESSION_HANDOFF.md     ⭐ 1분 컨텍스트 복원
    │   ├── NEXT_STEPS.md          사용자용 7-step 가이드
    │   ├── USER_GUIDE.md
    │   ├── STATS_DECISION_TREE.md (Mermaid)
    │   ├── decision_tree.html     인터랙티브 결정 트리
    │   ├── MULTIMODAL_PIPELINE.md Robot+Motion+EMG+Loadcell 표준
    │   └── verification/codex_pass_*.md  codex 10-pass 검증 로그
    ├── examples/
    │   ├── demo.m                 합성 데이터 end-to-end
    │   └── example_01..07_*.m     Copilot 친화 시나리오 7개
    ├── tests/                     149 단위테스트 (matlab.unittest)
    └── +hwalker/
        ├── analyzeFile.m  analyzeFolder.m
        ├── +io/      loadCSV / loadMotion / loadEMG / loadLoadcell + parseFilename
        ├── +sync/    findWindows (DebounceMs name-value)
        ├── +stride/  detectHS, lengthZUPT, stanceSwing, filterIQR (reasons)
        ├── +force/   trackingError, normalizedProfile
        ├── +stats/   ⭐ pairedTest (d_av/d_z/d_rm), anova1, anovaRM (GG/HF/Mauchly),
        │             postHoc (tukey/bonferroni/holm/fdr), bootstrap (BCa),
        │             leveneTest, decisionTree, symmetryIndex, fatigueIndex
        ├── +kinematics/ computeJointAngles (sagittal hip/knee/ankle, side-keyed)
        ├── +kinetics/   grfFeatures (peak Fz, propulsion, AP impulse, COP)
        ├── +emg/        coContractionIndex (Falconer-Winter)
        ├── +experiment/ ⭐ loadSession / loadAllConditions / extractFeatures /
        │                compareConditions / generateMethods
        ├── +plot/   ⭐ journalPreset (17 저널 + Custom), listJournals,
        │             applyPreset, exportFigure, exportAllJournals,
        │             preflightCheck (Copilot-style), drawSignificance, labelPanels,
        │             forceQC / forceTracking / strideTrend / metricBar / metricBox / multiConditionForce
        └── +meta/   reproPackage / loadRepro
```

---

## 핵심 함수 5개 (90% 시나리오)

```matlab
%% 1. 한 trial 분석
r = hwalker.analyzeFile('/path/to/data.csv');

%% 2. 한 condition multi-modal 묶음
session = hwalker.experiment.loadSession('~/exp/sub-01/cond-1_baseline');

%% 3. 모든 condition 비교 + 자동 검정 추천
conds = hwalker.experiment.loadAllConditions('~/exp/sub-01');
cmp   = hwalker.experiment.compareConditions(conds, 'Design','within');

%% 4. 6+ 저널 figure 일괄
hwalker.plot.exportAllJournals(@hwalker.plot.forceQC, {r,'R'}, '~/figs', ...
    'Journals', {'TRO','RAL','TNSRE','JNER','SciRobotics'});

%% 5. supplementary 재현성 패키지
hwalker.meta.reproPackage(r, '~/repro', 'InputCSV', '/path/to/data.csv');
```

---

## CSV 컬럼 규약 (H-Walker 펌웨어)

H-Walker 펌웨어 출력 그대로 사용. 핵심 컬럼:

| 컬럼 | 내용 |
|---|---|
| `Time_ms` | 타임스탬프 (ms) |
| `L_GCP` / `R_GCP` | 케이블 변위 (heel-strike 검출 sawtooth) |
| `L_ActForce_N` / `R_ActForce_N` | 실제 케이블 장력 (N) |
| `L_DesForce_N` / `R_DesForce_N` | 목표 케이블 장력 (N) |
| `L_Ax` / `L_Ay` | Global Velocity X/Y (ZUPT 보폭용) |
| `Sync` 또는 `A7` | 동기화 신호 (0/1) |

기존 파일명 (`260430_Robot_CBJ_TD_level_0_5_walker_high_0.csv`) 그대로 OK — `parseFilename` 이 자동 분류, multi-modal 워크플로우에서도 `loadSession` 이 source 별로 매칭.

---

## 17 저널 Preset 

**Robotics (11)**: TRO / RAL / TNSRE / TMECH / ICRA / IROS / IJRR / SciRobotics / SoftRobotics / FrontNeurorobot / AuRo
**General (6)**: IEEE / Nature / APA / Elsevier / MDPI / JNER
**Custom 등록**: `hwalker.plot.journalPreset('Custom', struct(...))`

목록 출력: `hwalker.plot.listJournals`

---

## 🚧 Codex 10-pass 검증 결과

총 **18 critical bug 발견 + 18 모두 fix**. 검증 로그: `matlab/docs/verification/codex_pass_*.md`.

영구 fix 항목 (회귀 금지):
- 저널 figure 높이 4:3 hardcoded → preset 종횡비 사용
- Tukey HSD fallback Bonferroni 사용 → numerical integration of studentized range
- BCa cell-array jackknife x{1} 만 → 모든 sample 풀링
- BCa denominator clamp 부호 잃음 → sign-preserving fallback
- paired Cohen's d 완전상관 case → d_av 한계로 fallback
- anova1/leveneTest/anovaRM/postHoc zero-variance → F=0,p=1 또는 F=Inf,p=0
- reproPackage git_commit 경로 버그 → findRepoRoot walks 8 levels
- bootstrap NaN drop, fatigueIndex/symmetryIndex NaN 처리, race condition
- compareConditions 가 decisionTree non-parametric 추천 무시 → Friedman/Wilcoxon/MW/KW 자동 라우팅
- generateMethods 가 없는 modality 도 텍스트 작성 → cmp metric 으로 detect
- grfFeatures stance off-by-one (sample-count semantics)
- computeJointAngles R/L summary fieldname 충돌 → side-suffixed
- preflightCheck checkResultStruct 가 report 출력 누락 → return value 추가

---

## 🐛 알려진 함정 / Gotchas

1. **`install` 명령어를 zsh 에 입력 → "target directory `등록' does not exist"**: MATLAB Command Window 에 입력해야 함 (zsh `install` 은 BSD 명령어).
2. **MDPI Palatino 폰트 macOS 미설치**: preflightCheck WARN; MATLAB 자동 substitute (paper 영향 거의 없음).
3. **저널 PDF 가 88.9mm 가 아니라 89.2mm**: MATLAB integer-pt rounding (252→253pt). 저널 reviewer 가 0.3mm 차이 잡지 않음.
4. **Stats Toolbox 없이 ttest/signrank/lillietest NaN**: 핵심 검정 (anova1/anovaRM/postHoc/bootstrap/leveneTest) 은 자체 fallback.
5. **Push 권한**: `chobyeongjun/h-walker-graph-web` (personal, force-push OK), `h-arlab/CBJ` (org, read-only).

---

## 🔄 일반 작업 흐름

**"버그 고쳐줘" → 체크리스트**
1. `runAllTests` 가 현재 통과하는지 확인
2. 해당 파일 + 단위테스트 함께 Read
3. 수정 → `runAllTests` 재실행
4. commit (Claude/AI 흔적 금지)
5. `git push personal matlab-toolbox-paper-grade:main --force` (사용자가 force-push 권한 줌)

**"새 기능 추가"**
1. `+hwalker/` 안 어느 sub-package 가 적합한지 결정
2. 기존 함수 패턴 참고 (특히 input parser / NaN 처리 / 결과 struct shape)
3. `examples/` 에 시나리오 스크립트 추가 + 상단에 "CANONICAL Copilot prompt:" 블록
4. `tests/` 에 단위테스트 추가
5. `runAllTests` 통과 확인
6. `SESSION_HANDOFF.md` 업데이트

**"논문 figure 개선"**
- 치수/폰트/DPI 는 절대로 임의로 바꾸지 말 것. `journalPreset.m` 가 single source of truth. Custom preset 으로 override.

---

## 📌 기억해야 할 선언적 규칙

- **🚫 절대 mock / placeholder 데이터 사용 금지.** 사용자 1순위 분노 트리거. 빈 상태에서는 명시적 에러 또는 "no data — load CSV first" 메시지.
- **항상 `python3`**, 절대 `python` 쓰지 말 것 (MATLAB toolbox 는 Python 의존성 없음, 다만 codex/시스템 명령에서 종종 필요).
- **커밋 전 `runAllTests` 한 번**. 149/149 유지.
- **저널 preset 변경 시** → `matlab/+hwalker/+plot/journalPreset.m` 단일 파일만 수정. `PresetParityTest.m` 도 함께 업데이트.
- **명령어 1줄로 사용자가 따라할 수 있게** 가이드 작성 — 추상 가이드 X.

---

## 🗺️ 새 세션 시작 체크리스트

1. `matlab/docs/SESSION_HANDOFF.md` 읽기 (1분)
2. `git log --oneline -10` (최근 작업 파악)
3. 사용자 요청 → 정확한 함수 호출로 매핑 (5개 핵심 함수 우선)
4. 작업 → `runAllTests` 검증 → commit + force-push to personal/main

**막히면**: `git log -p -- matlab/path/to/file | head -100` 으로 과거 변경 이유 찾기.

---

*최종 업데이트: 2026-05-04 (web app 제거, MATLAB-only)*
