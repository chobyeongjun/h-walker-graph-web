# Session Handoff — H-Walker MATLAB Toolbox

> **다음 Claude 세션이 이 파일 먼저 읽으면 1분 안에 컨텍스트 복원.**
> 마지막 큰 작업: 2026-05-04 (multi-modal pipeline + 11 robotics journals + codex 10-pass).

---

## 30초 미션

H-Walker (cable-driven gait rehab robot) 실험 데이터를 **논문에 바로 쓸** figure (저널 정확 mm) + 통계 (paper-grade) + 재현성 패키지까지 한 번에 처리하는 MATLAB toolbox.
사용자: 조병준 (ARLAB). 현재 cable robot + assistance condition 비교 연구 중.

---

## 현재 상태 (2026-05-04 기준)

- **Tests**: 149/149 passing (`runAllTests`)
- **Codex 10-pass**: 18 critical bug 발견 → 모두 수정
- **Repo scope**: MATLAB ONLY. 이전 web app (frontend/backend/desktop) 는 2026-05-04 에 제거됨 (git history 에 보존).
- **Branch**: `matlab-toolbox-paper-grade` on `chobyeongjun/h-walker-graph-web`

---

## 한 쪽만 분석하기 (R-only / L-only)

```matlab
%% 한 session 의 R 만
f = hwalker.experiment.extractFeatures(session, 'Side', 'R');

%% 모든 condition 비교 — 모두 R 기준
cmp = hwalker.experiment.compareConditions(conds, 'Design','within', 'Side','R');

%% 그래프도 R 만
fig = hwalker.plot.forceQC(r, 'R', 'TRO');
```

`'Side'` option 동작:
- 로봇/스트라이드 metric: R 행만 통과
- EMG: 채널명이 `L_*` / `Left*` 인 것 자동 제외 (prefix 없는 trunk 등은 유지)
- Motion: side-keyed 필드 (`knee_peak_flex_R`) 만 사용
- GRF: `grf(1)` (사용자 setup 에서 R plate 가 1번이라 가정)

---

## 핵심 함수 5개 (90% 의 사용 시나리오)

```matlab
%% 1. 한 trial 분석 (가장 자주)
r = hwalker.analyzeFile('/path/to/data.csv');

%% 2. 한 condition 의 multi-modal 묶음 (Robot+Motion+EMG+Loadcell)
session = hwalker.experiment.loadSession('~/exp/sub-01/cond-1_baseline');

%% 3. 한 피험자의 모든 condition 비교 + 자동 검정 추천
conds = hwalker.experiment.loadAllConditions('~/exp/sub-01');
cmp   = hwalker.experiment.compareConditions(conds, 'Design','within');

%% 4. 6+ 저널 figure 일괄 출력 (T-RO/RA-L/TNSRE/JNER/SciRobotics 등)
hwalker.plot.exportAllJournals(@hwalker.plot.forceQC, {r,'R'}, '~/figs', ...
    'Journals', {'TRO','RAL','TNSRE','JNER','SciRobotics'});

%% 5. supplementary 용 재현성 패키지
hwalker.meta.reproPackage(r, '~/repro', 'InputCSV', '/path/to/data.csv');
```

---

## 폴더 구조 (multi-modal 워크플로우)

```
~/h-walker-experiments/studies/<study_name>/
├── sub-01/
│   ├── meta.json   {"subject_id":"sub-01","mass_kg":72.0,...}
│   ├── cond-1_baseline/
│   │   ├── robot.csv          (또는 *_Robot_*.csv 같은 legacy 명도 자동 인식)
│   │   ├── motion.c3d         (또는 motion.csv/tsv)
│   │   ├── emg.csv            (옵션, EMG 가 motion 시스템과 별도일 때)
│   │   └── loadcell.csv       (옵션)
│   ├── cond-2_low_assist/
│   └── cond-3_high_assist/
└── sub-02/ ...
```

→ 표준 4 파일 (robot/motion/emg/loadcell). EMG 가 motion.c3d 안에 embed 되면 emg.csv 생략.
→ 사용자 기존 파일명 (`260430_Robot_CBJ_TD_level_0_5_walker_high_0.csv` 등) 그대로 둬도 OK — `loadSession` 이 `parseFilename` 으로 자동 분류.

---

## 패키지 맵

```
matlab/+hwalker/
├── analyzeFile.m            single CSV → result struct (sync 자동 분할)
├── analyzeFolder.m          batch
├── +io/                     loadCSV / loadMotion / loadEMG / loadLoadcell + parseFilename
├── +sync/                   findWindows (DebounceMs name-value)
├── +stride/                 detectHS, lengthZUPT, stanceSwing, filterIQR (reasons)
├── +force/                  trackingError, normalizedProfile
├── +stats/                  pairedTest (d_av/d_z/d_rm), anova1, anovaRM (GG/HF/Mauchly),
│                            postHoc (tukey/bonferroni/holm/fdr), bootstrap (BCa),
│                            leveneTest, decisionTree, symmetryIndex, fatigueIndex
├── +kinematics/             computeJointAngles (sagittal hip/knee/ankle, side-keyed)
├── +kinetics/               grfFeatures (peak Fz, propulsion, AP impulse, COP excursion)
├── +emg/                    coContractionIndex (Falconer-Winter)
├── +experiment/             loadSession / loadAllConditions / extractFeatures /
│                            compareConditions (decisionTree non-parametric routing) /
│                            generateMethods (modality-aware Methods text)
├── +plot/                   journalPreset (17 저널 + Custom), listJournals,
│                            applyPreset (저널 종횡비), exportFigure (print -dpdf -loose),
│                            exportAllJournals, preflightCheck (Copilot-style),
│                            drawSignificance, labelPanels, forceQC, etc.
└── +meta/                   reproPackage / loadRepro
```

---

## Codex 10-pass 검증 — 발견 + fix 18건

Round 1 (pass 1-7): single-trial 분석
- height 4:3 hardcoded, Tukey HSD fallback 잘못, BCa cell-array x{1} 만, BCa sign clamp,
  paired d 완전상관, anova1/leveneTest/anovaRM/postHoc zero-variance NaN, repro git_commit
  경로, bootstrap NaN drop, fatigue/symmetry NaN, race condition, preflight dropped report.

Round 2 (pass 8-9): multi-modal pipeline
- extractFeatures 가 global mean 을 모든 stride 에 복사 → per-stride GRF 인덱싱 + side-keyed
- computeJointAngles R/L summary fieldname 충돌 → side-suffixed
- grfFeatures 100ms stance off-by-one → sample-count semantics

Round 3 (pass 10): final + Copilot
- compareConditions 가 decisionTree non-parametric 추천 무시 → Friedman/Wilcoxon/MW/KW 자동
- generateMethods 가 없는 modality 도 텍스트 작성 → cmp metric 으로 detect
- MULTIMODAL_PIPELINE.md 가 미구현 함수 documenting → 실제 API 만 + Roadmap 명시
- example_*.m 7개 모두 CANONICAL Copilot prompt 추가

상세: `matlab/docs/verification/codex_pass_*.md`, `codex_passes_*.md`

---

## 알려진 함정

| 함정 | 해결 |
|---|---|
| `install` 명령어를 zsh terminal 에 입력 → "target directory `등록' does not exist" | MATLAB 내부 `>>` 프롬프트에 입력해야 함 |
| MDPI Palatino 폰트 macOS 미설치 | preflightCheck WARN; MATLAB 자동 substitute (paper 영향 거의 없음) |
| 저널 PDF 가 정확히 88.9mm 가 아니라 89.2mm 정도 | MATLAB integer-pt rounding (252→253pt). 저널 reviewer 가 0.3mm 차이 잡지 않음. |
| Stats Toolbox 없이 ttest/signrank/lillietest NaN | 핵심 검정 (anova1/anovaRM/postHoc/bootstrap/leveneTest) 은 자체 fallback |
| MATLAB Copilot 한테 물었는데 우리 함수 안 부르고 generic MATLAB 코드 | 사용자가 example_*.m 한 번 열어두면 컨텍스트 학습 → 다음부터 정확 |

---

## 사용자 (조병준) preference 요약

- 한국어 소통, 직접적, 짧은 답변
- python 아닌 python3
- Git 에 Claude/AI 흔적 절대 금지 (Co-Authored-By, claude/ 브랜치명, PR 본문 언급)
- 도구가 정확히 작동해야 함 (논문 직행 quality)
- "추상 가이드" 보다 "정확한 명령어" 선호 (NEXT_STEPS.md 가 그 응답)
- robotics 분야 — T-RO / RA-L / TNSRE / ICRA / IROS 가 main target

---

## 다음 작업 후보 (사용자 우선순위 순)

1. **본인 실제 데이터로 example_07 돌려보기** — 막히는 지점 디버깅
2. **per-stride motion features** — 현재 trial 평균이라, 진짜 stride 분할 (motion 시간축 stride 인덱싱) 추가
3. **`hwalker.experiment.compareGroup`** — 여러 피험자 통합 (현재는 subject loop 으로 user 가 직접)
4. **`hwalker.experiment.makeAllPaperFigures`** — 7-figure 일괄 wrapper
5. **`+robolab/` 일반화** — 다른 로봇 (외골격, manipulator) 재사용 (Phase F, 논문 후)

---

## 주의 사항

- **CLAUDE.md** (project root) 와 **~/.claude/CLAUDE.md** (global universal harness rules) 둘 다 읽기
- 사용자가 `/codex --xhigh` 호출하면 시간 매우 오래 걸림 (xhigh 는 high 의 23배 토큰). `medium` 또는 `low` 가 보통 충분
- 사용자가 commit 하라고 명시 안 했어도 CLAUDE.md 에 "작업 완료 시 커밋 + 푸시 자동" 룰 있음 → AI 흔적 금지로 commit 메시지 작성
- Push 권한: `chobyeongjun/h-walker-graph-web` (personal, force-push OK), `h-arlab/CBJ` (org, read-only — collaborator 권한 없음)

---

## 빠른 참조 (사용자 요청별)

| 사용자 질문 | 가이드 |
|---|---|
| "어떻게 시작?" | `matlab/docs/NEXT_STEPS.md` |
| "어떤 통계 검정?" | `matlab/docs/STATS_DECISION_TREE.md` 또는 `hwalker.stats.decisionTree(...)` 자동 추천 |
| "Robot+Motion+EMG+Loadcell 한 번에" | `matlab/docs/MULTIMODAL_PIPELINE.md` + `examples/example_07_*.m` |
| "내 저널이 목록에 없어" | `hwalker.plot.journalPreset('Custom', struct(...))` |
| "사용 가능한 저널 목록" | `hwalker.plot.listJournals` |
| "함수별 detail 도움말" | `help hwalker.stats.anovaRM` 등 (모든 함수 풍부한 doc block) |
| "MATLAB Copilot 이 우리 함수 사용?" | example 파일 한 번 열기 → CANONICAL prompt 가 컨텍스트 |
| "재현성 패키지" | `hwalker.meta.reproPackage(...)` |

---

*마지막 업데이트: 2026-05-04 · maintainer: 사용자 본인 + Claude session-by-session*
