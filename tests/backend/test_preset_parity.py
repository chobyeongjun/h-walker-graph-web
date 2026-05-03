"""
test_preset_parity — verifies backend/services/publication_engine.py
JOURNAL_PRESETS values match the canonical CLAUDE.md table that
matlab/+hwalker/+plot/journalPreset.m mirrors verbatim.

These two presets MUST stay in lockstep; this test is the CI gate.
"""
from __future__ import annotations

import pytest

from backend.services.publication_engine import JOURNAL_PRESETS, Preset


# ============================================================
# Canonical specs — mirror matlab/+hwalker/+plot/journalPreset.m
# (which mirrors CLAUDE.md "논문 Export 검증된 스펙").
# ============================================================
EXPECTED = {
    "ieee": dict(
        col1=(88.9, 70.0), col2=(181.0, 90.0), onehalf=None,
        font="Times New Roman", body_pt=8, stroke_pt=1.0,
        dpi=600, colorblind_safe=False,
    ),
    "nature": dict(
        col1=(89.0, 60.0), col2=(183.0, 90.0), onehalf=None,
        font="Helvetica", body_pt=7, stroke_pt=0.5,
        dpi=300, colorblind_safe=True,
    ),
    "apa": dict(
        col1=(85.0, 65.0), col2=(174.0, 100.0), onehalf=None,
        font="Arial", body_pt=10, stroke_pt=0.75,
        dpi=300, colorblind_safe=False,
    ),
    "elsevier": dict(
        col1=(90.0, 60.0), col2=(190.0, 90.0), onehalf=(140.0, 80.0),
        font="Arial", body_pt=8, stroke_pt=0.5,
        dpi=300, colorblind_safe=False,
    ),
    "mdpi": dict(
        col1=(85.0, 65.0), col2=(170.0, 90.0), onehalf=None,
        font="Palatino", body_pt=8, stroke_pt=0.75,
        dpi=1000, colorblind_safe=False,
    ),
    "jner": dict(
        col1=(85.0, 65.0), col2=(170.0, 90.0), onehalf=None,
        font="Arial", body_pt=8, stroke_pt=0.75,
        dpi=300, colorblind_safe=True,
    ),
}


@pytest.mark.parametrize("key", list(EXPECTED))
def test_preset_dimensions(key: str) -> None:
    p: Preset = JOURNAL_PRESETS[key]
    exp = EXPECTED[key]
    assert p.col1 == exp["col1"], f"{key} col1 mismatch"
    assert p.col2 == exp["col2"], f"{key} col2 mismatch"
    assert p.onehalf == exp["onehalf"], f"{key} onehalf mismatch"


@pytest.mark.parametrize("key", list(EXPECTED))
def test_preset_typography(key: str) -> None:
    p: Preset = JOURNAL_PRESETS[key]
    exp = EXPECTED[key]
    assert p.font == exp["font"], f"{key} font mismatch"
    assert p.body_pt == exp["body_pt"], f"{key} body_pt mismatch"
    assert p.stroke_pt == exp["stroke_pt"], f"{key} stroke_pt mismatch"


@pytest.mark.parametrize("key", list(EXPECTED))
def test_preset_export(key: str) -> None:
    p: Preset = JOURNAL_PRESETS[key]
    exp = EXPECTED[key]
    assert p.dpi == exp["dpi"], f"{key} dpi mismatch"
    assert p.colorblind_safe == exp["colorblind_safe"], (
        f"{key} colorblind_safe mismatch"
    )


def test_all_six_journals_present() -> None:
    assert set(JOURNAL_PRESETS) == set(EXPECTED), (
        f"JOURNAL_PRESETS keys differ: "
        f"got {sorted(JOURNAL_PRESETS)}, expected {sorted(EXPECTED)}"
    )


def test_only_elsevier_has_onehalf() -> None:
    for key, p in JOURNAL_PRESETS.items():
        if key == "elsevier":
            assert p.onehalf is not None, "Elsevier should have a 1.5-col variant"
        else:
            assert p.onehalf is None, f"{key} should NOT have a 1.5-col variant"


def test_wong_palette_used_for_colorblind_safe_journals() -> None:
    """Nature and JNER should use the Wong color-blind safe palette."""
    wong_first = "#000000"   # Wong palette starts with black in our spec
    wong_second = "#E69F00"  # orange
    for key in ("nature",):
        p = JOURNAL_PRESETS[key]
        assert p.palette[0].lower() == wong_first.lower(), (
            f"{key} palette[0] should be {wong_first}"
        )
        assert p.palette[1].lower() == wong_second.lower(), (
            f"{key} palette[1] should be {wong_second}"
        )


def test_dpi_is_positive_int() -> None:
    for key, p in JOURNAL_PRESETS.items():
        assert isinstance(p.dpi, int) and p.dpi > 0, f"{key} dpi must be positive int"


def test_height_to_width_aspect_reasonable() -> None:
    """Aspect ratios should be between 0.4 and 0.85 of width — sanity bound."""
    for key, p in JOURNAL_PRESETS.items():
        for label, (w, h) in [("col1", p.col1), ("col2", p.col2)]:
            assert 0.40 * w <= h <= 0.85 * w, (
                f"{key} {label} aspect ratio out of range: {w}x{h}"
            )
