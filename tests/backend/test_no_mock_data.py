"""Anti-regression test: NO mock data in any frontend data file.

User directive (CLAUDE.md):
    "🚫 절대 mock / placeholder 데이터를 UI 에 띄우지 마라."

This test scans the frontend `data/` schema files and asserts that no
literal placeholder rows / fake SVG paths / sample stat results sneak
back in. It complements the explicit removal commits — anyone editing
these files in the future must keep them metadata-only.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DATA = ROOT / "frontend" / "src" / "data"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


# ----------------------------------------------------------------
# computeMetrics.ts — schema only, no rows[] fake numbers
# ----------------------------------------------------------------

def test_compute_metrics_has_no_mock_rows():
    src = _read(FRONTEND_DATA / "computeMetrics.ts")
    # The earlier mock had `rows: [['1', '47.8', '45.1', ...]]` etc.
    # Match the literal payload start, not bare substrings (the metric
    # key `symmetry_summary:` is fine — that's a category name).
    assert not re.search(r"\brows\s*:\s*\[", src), (
        "computeMetrics.ts must be schema-only (label + cols). A mock "
        "`rows: [...]` payload was found — placeholder numbers will "
        "leak onto the canvas before any CSV is bound. Move test data "
        "to fixtures."
    )
    assert not re.search(r"\bsummary\s*:\s*\{", src), (
        "computeMetrics.ts must not carry mock `summary: { ... }` "
        "payloads (a metric key like `symmetry_summary:` is fine)."
    )


# ----------------------------------------------------------------
# graphTemplates.ts — schema only, no SVG mock paths
# ----------------------------------------------------------------

def test_graph_templates_has_no_svg_paths():
    src = _read(FRONTEND_DATA / "graphTemplates.ts")
    # Old templates carried `paths: [{ d: 'M48,160 C70,...' }]` and
    # similar bezier mockups; renderers used them as fallback figures.
    # Match payload-start (`name: [`) so we don't trip on substrings
    # inside identifiers / docstrings.
    for forbidden in ("paths", "bands", "boxes", "bars", "hlines"):
        if re.search(rf"\b{forbidden}\s*:\s*\[", src):
            raise AssertionError(
                f"graphTemplates.ts contains a `{forbidden}: [...]` "
                "payload — that's mock render data and would put fake "
                "bezier curves on the canvas. Keep it metadata-only."
            )


# ----------------------------------------------------------------
# statOps.ts — schema only, no run() that returns fake stats
# ----------------------------------------------------------------

def test_stat_ops_has_no_run_function():
    src = _read(FRONTEND_DATA / "statOps.ts")
    # Old shape: `run: ({ a, b }) => ({ test: 'Paired t-test', t: '3.27' })`
    forbidden = re.search(r"\brun\s*:\s*\(", src)
    assert forbidden is None, (
        "statOps.ts must not carry client-side mock `run()` functions — "
        "real stats come from /api/stats only. Found: "
        f"{forbidden.group(0) if forbidden else None}"
    )


# ----------------------------------------------------------------
# StatCell — no MockKV / mockResult component lingering
# ----------------------------------------------------------------

def test_stat_cell_has_no_mock_kv_component():
    cell = ROOT / "frontend" / "src" / "components" / "cells" / "StatCell.tsx"
    src = _read(cell)
    for sym in ("MockKV", "mockResult", "formatMockReport", "mockOp"):
        assert sym not in src, (
            f"StatCell.tsx still references `{sym}`. The mock stat "
            "result path was removed — re-introducing it would put "
            "fake t/F/p numbers in front of the user."
        )


# ----------------------------------------------------------------
# GraphCell — no PlotSvg fallback that draws fake curves
# ----------------------------------------------------------------

def test_graph_cell_has_no_plot_svg_fallback():
    cell = ROOT / "frontend" / "src" / "components" / "cells" / "GraphCell.tsx"
    src = _read(cell)
    assert "PlotSvg" not in src, (
        "GraphCell.tsx still references `PlotSvg`. That component drew "
        "the mock bezier fallback when no dataset was bound. The "
        "replacement is `EmptyPlot` — axes only, no fake data."
    )
    assert "EmptyPlot" in src, (
        "GraphCell.tsx must use `EmptyPlot` for the no-dataset state."
    )


# ----------------------------------------------------------------
# Removed templates stay removed
# ----------------------------------------------------------------

@pytest.mark.parametrize("name", ["peak_box", "debug_ts"])
def test_removed_templates_not_referenced_in_data(name: str):
    """User explicitly asked to remove peak_box and debug_ts. They must
    not reappear as a key in the data files."""
    for fname in ("graphTemplates.ts", "canonicalRecipes.ts"):
        src = _read(FRONTEND_DATA / fname)
        # Allow comments / removal-history mentions, but not as object keys.
        # Keys in a TS object look like `name:` or `'name':` at the start
        # of a line (after indent).
        if re.search(rf"^\s*['\"]?{name}['\"]?\s*:", src, re.MULTILINE):
            raise AssertionError(
                f"`{name}` reappeared as a key in {fname}. It was removed "
                "per a user directive — re-adding requires deleting this "
                "guard and explaining why in the commit message."
            )
