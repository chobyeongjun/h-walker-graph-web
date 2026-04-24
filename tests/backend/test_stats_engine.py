"""Regression tests for stats_engine — pin APA 7 contract bits.

The frontend relies on the backend to produce:
  - a `label` ("small"/"medium"/…/"large") on every Cohen's d
    effect_size dict, so StatCell can print "d = 0.42 (small)".
  - a `warning` string when paired t-test silently trimmed unequal-
    length inputs, so the user sees data was dropped.
These are shape contracts. A future refactor that drops either field
must flip this test red.
"""
from __future__ import annotations

import pytest

from backend.services import stats_engine


# ---------------------------------------------------------------
# Effect-size label coverage
# ---------------------------------------------------------------

def test_paired_ttest_includes_cohen_magnitude_label():
    # Two clearly different means → d should be large.
    a = [10.0, 11.0, 12.0, 10.5, 11.5, 9.5]
    b = [5.0, 6.0, 7.0, 5.5, 6.5, 4.5]
    r = stats_engine.ttest_paired(a, b)
    es = r["effect_size"]
    assert es["name"] == "Cohen's d"
    assert "label" in es, (
        "paired t-test effect_size is missing the 'label' field. "
        "Frontend StatCell renders 'd = X.XX (label)' and falls back "
        "to 'd = X.XX' without this — user loses the magnitude cue."
    )
    assert es["label"] in ("negligible", "small", "medium", "large")


def test_welch_ttest_includes_cohen_magnitude_label():
    a = [10.0, 11.0, 12.0, 10.5, 11.5]
    b = [5.0, 6.0, 7.0, 5.5, 6.5, 4.5, 7.0]
    r = stats_engine.ttest_welch(a, b)
    es = r["effect_size"]
    assert es["name"] == "Cohen's d"
    assert "label" in es
    assert es["label"] in ("negligible", "small", "medium", "large")


def test_cohen_magnitude_thresholds():
    """Cohen (1988) boundaries: .2 / .5 / .8."""
    assert stats_engine._cohen_magnitude(0.0) == "negligible"
    assert stats_engine._cohen_magnitude(0.19) == "negligible"
    assert stats_engine._cohen_magnitude(0.3) == "small"
    assert stats_engine._cohen_magnitude(0.6) == "medium"
    assert stats_engine._cohen_magnitude(0.9) == "large"
    # Sign doesn't change magnitude
    assert stats_engine._cohen_magnitude(-0.9) == "large"


# ---------------------------------------------------------------
# Paired t-test trim transparency
# ---------------------------------------------------------------

def test_paired_ttest_warns_on_unequal_length_inputs():
    """If the user passes arrays of different length, the paired t-test
    silently trims to min(len) — but must surface a warning so the user
    knows data was dropped."""
    a = [10.0, 11.0, 12.0, 10.5, 11.5]       # 5 values
    b = [5.0, 6.0, 7.0, 5.5, 6.5, 4.5, 7.0]  # 7 values → 2 dropped
    r = stats_engine.ttest_paired(a, b)
    assert r.get("warning"), (
        "paired t-test silently trimmed unequal-length inputs — the "
        "frontend has no breadcrumb that data was dropped."
    )
    assert "2" in r["warning"], f"warning should mention count: {r['warning']}"


def test_paired_ttest_no_warning_when_equal_length():
    a = [10.0, 11.0, 12.0, 10.5, 11.5]
    b = [5.0, 6.0, 7.0, 5.5, 6.5]
    r = stats_engine.ttest_paired(a, b)
    # warning should be None / absent when no trim happened
    assert not r.get("warning")


def test_paired_ttest_still_rejects_too_few_pairs():
    with pytest.raises(ValueError, match=r"≥3 pairs"):
        stats_engine.ttest_paired([1.0, 2.0], [1.0, 2.0])
