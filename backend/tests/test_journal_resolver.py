"""Tests for journal_resolver: preset loading, fuzzy match, Gemma 4 fallback."""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


def test_normalize_key_ieee():
    from services.journal_resolver import _normalize_key
    assert _normalize_key("IEEE RA-L") == "ieee_ra_l"
    assert _normalize_key("Gait & Posture") == "gait_posture"
    assert _normalize_key("PLOS ONE") == "plos_one"


def test_load_preset_ieee_tnsre():
    from services.journal_resolver import load_preset
    style = load_preset("ieee_tnsre")
    assert style is not None
    assert style["key"] == "ieee_tnsre"
    assert style["font_family"] == "Times New Roman"
    assert style["figure_width_mm"] == 88


def test_load_preset_returns_none_for_unknown():
    from services.journal_resolver import load_preset
    result = load_preset("nonexistent_journal_xyz")
    assert result is None


def test_load_all_10_presets():
    from services.journal_resolver import load_preset
    keys = [
        "ieee_tnsre", "jner", "ieee_ral", "science_robotics",
        "biomechanics", "gait_posture", "medical_eng_physics",
        "plos_one", "nature", "icra_iros",
    ]
    for key in keys:
        style = load_preset(key)
        assert style is not None, f"Missing preset: {key}"
        assert "font_family" in style
        assert "figure_width_mm" in style


def test_fuzzy_match_ieee_transactions():
    from services.journal_resolver import _fuzzy_match
    result = _fuzzy_match("IEEE Transactions Neural Systems")
    assert result is not None
    assert "ieee" in result["key"]


def test_resolve_journal_exact_match():
    from services.journal_resolver import resolve_journal
    style = resolve_journal("ieee_tnsre")
    assert style["key"] == "ieee_tnsre"


def test_resolve_journal_human_name():
    from services.journal_resolver import resolve_journal
    style = resolve_journal("IEEE TNSRE")
    assert style is not None
    assert style["key"] == "ieee_tnsre"


def test_resolve_journal_gemma4_fallback(tmp_path, monkeypatch):
    """Unknown journal triggers Gemma 4 call and caches result."""
    from services import journal_resolver

    monkeypatch.setattr(journal_resolver, "STYLES_DIR", tmp_path)
    monkeypatch.setattr(journal_resolver, "CACHE_DIR", tmp_path / "cached")
    (tmp_path / "cached").mkdir()

    fake_style = {
        "name": "Fake Journal", "key": "fake_journal",
        "font_family": "Arial", "font_size": 9.0, "line_width": 1.0,
        "figure_width_mm": 85.0, "figure_height_mm": 64.0, "dpi": 300,
        "legend_frameon": False, "color_cycle": ["#000000"],
        "spine_linewidth": 0.8, "tick_direction": "out",
        "tick_labelsize": 8.0, "axes_labelsize": 9.0, "title_size": 9.0,
        "pad_inches": 0.05,
    }

    mock_response = MagicMock()
    mock_response.json.return_value = {"response": json.dumps(fake_style)}
    mock_response.raise_for_status = MagicMock()

    with patch("services.journal_resolver.httpx.post", return_value=mock_response):
        result = journal_resolver.resolve_journal("Fake Journal 2026")

    assert result["font_family"] == "Arial"
    # Second call should use cache, not call Gemma 4 again
    with patch("services.journal_resolver.httpx.post", side_effect=Exception("Should not call")):
        result2 = journal_resolver.resolve_journal("Fake Journal 2026")
    assert result2["font_family"] == "Arial"


def test_apply_to_figure_sets_size():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from services.journal_resolver import apply_to_figure, load_preset

    style = load_preset("ieee_tnsre")
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [1, 2, 3])
    apply_to_figure(fig, style)

    MM_TO_INCH = 1 / 25.4
    w, h = fig.get_size_inches()
    assert abs(w - style["figure_width_mm"] * MM_TO_INCH) < 0.01
    plt.close(fig)
