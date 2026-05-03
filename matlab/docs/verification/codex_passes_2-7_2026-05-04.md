# Codex Verification Passes 2-7 — Follow-up & Adversarial

**Date**: 2026-05-04
**Reviewer**: OpenAI Codex CLI (codex-cli 0.128.0)
**Branch**: `claude/improve-validation-agent-v3bWQ`
**Predecessor pass**: see [codex_pass_1_2026-05-04.md](codex_pass_1_2026-05-04.md) — Pass 1 found 4 critical bugs (all fixed there).

This document covers passes 2 through 7 — verification of the Pass 1 fixes, then targeted reviews of figure presets, color palette, reproducibility, documentation, and a final adversarial sweep.

---

## Pass 2 — verify the 4 critical fixes from Pass 1

| Fix | Question | Codex answer |
|---|---|---|
| #1 Tukey HSD numerical integration | "Is `stud_range_sf_integrated` a correct numerical integration of the studentized-range survival function?" | **CORRECT** ✅ |
| #2 BCa cell-array jackknife | "Does `jackknifeAccel` pool jackknife replicates from ALL samples or only from x{1}?" | **ALL** ✅ |
| #3 BCa sign-preserving denominator | implicit (covered by combined ANOVA edge-case sweep) | ✅ |
| #4 Perfect-correlation constant shift | "When diff_std=0 and diff_mean≠0, do d_z and d_rm fall back to d_av?" | **YES** ✅ |
| Edge cases (zero variance handling across anova1 / leveneTest / anovaRM / postHoc) | "Do all four return F=0,p=1 or F=Inf,p=0 instead of NaN?" | **PARTIAL** — anovaRM and postHoc still had gaps |

### Pass 2 follow-up bugs found and fixed

| File | Bug | Fix |
|---|---|---|
| `anovaRM.m`, `anova1.m` (`fdist_sf` helpers) | When F=0 returned NaN; when F=Inf returned NaN | Now return p=1 for F≤0, p=0 for F=Inf |
| `postHoc.m` Tukey branch | When `se_diff=0` produced `q=0/0=NaN` → `p_adj=NaN` | Branch on se_diff≈0: equal means → p_adj=1; differing means → p_adj=0 |

Tests added: `testAnovaRM_AllIdenticalGivesP1`, `testAnovaRM_PerfectSeparationGivesP0`,
`testPostHocTukey_AllIdenticalNoNaN`, `testPostHocTukey_PerfectSeparationP0`.

---

## Pass 3 — Journal preset accuracy vs current author guidelines

Codex web-searched current IEEE / Nature / APA / Elsevier / MDPI / JNER author guidelines and compared to `journalPreset.m`.

**Verdict**: All values fall within currently published tolerances. Discrepancies (≤ 1 mm width, font-size choices within published ranges, DPI at the upper end of recommended) reflect either rounding (181 mm = 7.16 in rounded) or conservative within-range choices for legibility at print size.

**Action taken**: Added a documentation block to `journalPreset.m` explaining that the preset values are the LAB STANDARD — a single concrete choice within each journal's allowed range — and recording the verification date and sources.

---

## Pass 4 — Wong colorblind palette accuracy

Verified `wongColors` matrix against Wong B (2011) Nature Methods 8:441 reference RGB values:

```
blue       (0,   114, 178)
orange     (230, 159,   0)
sky blue   (86,  180, 233)
bluish green (0, 158, 115)
yellow     (240, 228,  66)
vermillion (213,  94,   0)
reddish purple (204, 121, 167)
```

**Codex verdict**: **MATCH** ✅

---

## Pass 5 — Reproducibility round-trip

Asked codex to verify that `reproPackage` + `loadRepro` capture and verify everything needed to bit-replicate an analysis.

**Initial verdict**: `MISSING:git_commit`

### Bug found and fixed

**`reproPackage.m` and `loadRepro.m`**: walked up the wrong number of `fileparts()` calls when looking for the `.git` directory:
- `mfilename('fullpath')` for `matlab/+hwalker/+meta/reproPackage.m` returns `.../matlab/+hwalker/+meta/reproPackage`
- Original code did `fileparts(fileparts(...))` which gives `.../matlab/+hwalker` (NOT the repo root)
- `.git` lives at `.../h-walker-graph-web/.git`, so the lookup always failed silently → `commit = ''`

**Fix**: New `findRepoRoot()` helper walks UP from the .m file's directory looking for a `.git` entry (file or dir, to handle git worktrees). Up to 8 levels.

Test added: `testGitCommitNotEmpty` — asserts `info.git_commit` is a 40-char SHA-1 when run inside a git repo.

Verified end-to-end: `environment.json` from a fresh demo run now contains
`"git_commit": "2bad73654210ffd9e208f654b3b8c30daca2ef2d"`.

---

## Pass 6 — Documentation completeness

Codex pretended to be a new researcher and answered five questions using only `USER_GUIDE.md` + `STATS_DECISION_TREE.md`:

| Q | Answer |
|---|---|
| (a) Can you install the toolbox? | YES |
| (b) Can you load a CSV? | YES |
| (c) Can you run paired t-test reporting Cohen's d_av? | YES |
| (d) Can you export a Nature 2-col PDF? | YES |
| (e) Can you find which test to use for 3 conditions within-subject? | YES |

**Missing topics noted (low priority)**: location of example CSV file, exact Nature 2-column dimensions inline, troubleshooting install path issues, complete `anovaRM` input shape example. None of these are blockers — all are answerable from the function help blocks (`help hwalker.stats.anovaRM`).

---

## Pass 7 — Adversarial challenge

> "Try to find ANY remaining critical bug. Be brutal."

Codex found **5 more bugs**. All fixed:

| # | File:line | Bug | Fix |
|---|---|---|---|
| 1 | `bootstrap.m:56-83` | Numeric input with NaN values silently produced NaN CIs (resampled `x` including NaN, so `@mean` returned NaN every iteration) | Drop `~isfinite` entries from numeric x before resampling; same for cell elements |
| 2 | `fatigueIndex.m:17-23` | `mean(values(1:k))` did not skip NaN — one NaN in the first or last window silently returned `fi = NaN` | Drop `~isfinite` entries before windowing |
| 3 | `symmetryIndex.m:8-12` | `if leftVal <= 0 || rightVal <= 0 → si = -1` doc says "missing → -1", but `NaN <= 0` is false → returned `NaN` instead | Add explicit `~isfinite` check |
| 4 | `reproPackage.m:36-39` | Second-resolution timestamp + unguarded `mkdir` → two calls in same second collide | Switch to ms-resolution `yyyymmddTHHMMSSFFF`; if `runDir` exists, append `_N` counter |
| 5 | `preflightCheck.m:115, 184-205` | `checkResultStruct` declared `~report` (discard) → empty-stride CRITICAL was logged via `warning()` but NEVER added to `report.critical`, so `report.ok` stayed true | Pass `report` in/out, push to `report.critical` |

Tests added: `testBootstrap_DropsNaNFromNumericInput`, `testCriticalOnEmptyStrideSide`,
`testParallelCallsDontCollide`.

---

## Cumulative Result

| Codex pass | Bugs found | All fixed? | Test status after |
|---|---|---|---|
| Pass 1 (full stat review) | 4 critical | ✅ | 113 → 119 passing |
| Pass 2 (verify + edge cases) | 2 partial-fixes | ✅ | 119 → 123 passing |
| Pass 3 (preset web-check) | 0 (within tolerance) | n/a | 123 |
| Pass 4 (Wong palette) | 0 | n/a | 123 |
| Pass 5 (repro git_commit) | 1 (path bug) | ✅ | 123 → 124 passing |
| Pass 6 (docs) | 0 critical | n/a | 124 |
| Pass 7 (adversarial) | 5 (silent NaN, race, dropped report) | ✅ | 124 → 127 passing |
| **Total** | **12 bugs** | **✅ 12/12 fixed** | **127/127** |

## Final State (after all 7 passes)
- MATLAB tests: **127/127 passing** (44 pre-existing + 83 new across 9 test classes)
- Python parity tests: **23/23 passing**
- Demo end-to-end: ✅ all 12 PDFs at correct mm × mm; git commit captured in repro
- Outstanding critical findings: **0**

## Costs
- Total tokens across all 7 passes: ~480,000
- Estimated total cost: ~$2.40 (gpt-5 codex pricing, mix of high/medium/low reasoning)

## Outcome
✅ **PAPER-READY** — comprehensive multi-axis verification complete. No remaining critical bugs in the statistical formulas, figure pipeline, reproducibility metadata, or documentation flow.
