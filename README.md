# H-Walker MATLAB Toolbox

> H-Walker (cable-driven gait rehab robot) 실험 데이터 → 논문 직행 figure (저널 정확 mm) + 통계 (paper-grade) + 재현성 패키지까지 한 toolbox.

```matlab
%% 한 번만 (MATLAB 안에서)
cd matlab; install

%% 데모
cd examples; demo

%% 본인 데이터
results = hwalker.analyzeFile('/path/to/data.csv');
hwalker.plot.exportAllJournals(@hwalker.plot.forceQC, {results(1),'R'}, '~/figs', ...
    'Journals', {'TRO','RAL','TNSRE','JNER'});
```

---

## 핵심

| 항목 | |
|---|---|
| MATLAB 버전 | R2020a 이상 (개발 R2025b) |
| 단위 테스트 | 149/149 통과 (`matlab/tests/runAllTests.m`) |
| 저널 preset | 17 종 (11 robotics + 6 general) + Custom 등록 |
| 통계 | paired t / Wilcoxon / one-way ANOVA / RM-ANOVA / Friedman / post-hoc 4가지 / BCa bootstrap / Levene |
| Multi-modal | Robot CSV + Motion C3D + EMG + Loadcell BWS 한 번에 처리 |
| Codex 검증 | 10-pass, 18 critical bug 발견 + 모두 수정 |
| 재현성 | input SHA-256 + git commit + MATLAB 버전 + JSON+MAT 패키지 |

---

## 문서

- **`matlab/docs/SESSION_HANDOFF.md`** — 새 Claude 세션이 1분 안에 컨텍스트 복원
- **`matlab/docs/NEXT_STEPS.md`** — 사용자용 7-step 적용 가이드
- **`matlab/docs/MULTIMODAL_PIPELINE.md`** — Robot+Motion+EMG+Loadcell 폴더 표준 + 처리
- **`matlab/docs/STATS_DECISION_TREE.md`** — 통계 검정 결정 트리
- **`matlab/docs/decision_tree.html`** — 인터랙티브 결정 트리 (브라우저)
- **`matlab/README.md`** — 함수 매트릭스
- **`matlab/docs/verification/`** — codex 10-pass 검증 로그

---

## 사용 가능한 저널

```matlab
hwalker.plot.listJournals
% Robotics (11): TRO RAL TNSRE TMECH ICRA IROS IJRR SciRobotics SoftRobotics FrontNeurorobot AuRo
% General  (6): IEEE Nature APA Elsevier MDPI JNER
% + Custom: hwalker.plot.journalPreset('Custom', struct('col1mm',88, ...))
```

---

## 이전 web app 코드는?

2026-05-04 에 제거됨. git history 에 보존:
```bash
git log --all --oneline -- frontend/         # 마지막 커밋 보기
git checkout <commit> -- frontend/ backend/  # 필요시 복구
```

## 라이선스
Internal research tool — ARLAB.
