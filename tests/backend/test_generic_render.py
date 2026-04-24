"""Test generic-CSV fallback renderer.

Ensures a CSV that fails the H-Walker schema check still produces a real-data
plot (time-series of actual columns) instead of a mock bezier.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pandas as pd


def _make_req(template: str = "force", preset: str = "ieee") -> MagicMock:
    req = MagicMock()
    req.template = template
    req.preset = preset
    req.variant = "col2"
    req.dpi = None
    req.format = "svg"
    req.title = None
    req.dataset_id = "ds_test"
    req.colorblind_safe = False
    return req


def test_generic_force_template_renders():
    from backend.routers.graphs import _render_generic_csv
    from backend.routers import datasets as _ds_mod
    _ds_mod._REGISTRY["ds_test"] = {"hz": "100Hz"}

    t = np.arange(0, 5, 0.01)
    df = pd.DataFrame({
        "time_s": t,
        "L_ActForce_N": np.sin(t * 5) * 100 + 200,
        "R_ActForce_N": np.cos(t * 5) * 100 + 200,
    })
    result = _render_generic_csv(_make_req("force"), df)
    assert result is not None
    data, mime = result
    assert mime == "image/svg+xml"
    assert len(data) > 1000  # produced a real SVG, not an empty stub


def test_generic_debug_ts_renders():
    from backend.routers.graphs import _render_generic_csv
    from backend.routers import datasets as _ds_mod
    _ds_mod._REGISTRY["ds_test"] = {"hz": "100Hz"}

    t = np.arange(0, 3, 0.01)
    df = pd.DataFrame({
        "time": t,
        "ch1": np.sin(t),
        "ch2": np.cos(t),
        "ch3": t,
    })
    result = _render_generic_csv(_make_req("debug_ts"), df)
    assert result is not None
    data, mime = result
    assert mime == "image/svg+xml"
    assert len(data) > 1000


def test_generic_only_time_column_returns_none():
    from backend.routers.graphs import _render_generic_csv
    from backend.routers import datasets as _ds_mod
    _ds_mod._REGISTRY["ds_test"] = {"hz": "100Hz"}

    # Only a time-like column → nothing plottable
    df = pd.DataFrame({"time_s": [0, 0.01, 0.02]})
    result = _render_generic_csv(_make_req("force"), df)
    assert result is None


def test_generic_unsupported_template_returns_none():
    from backend.routers.graphs import _render_generic_csv
    from backend.routers import datasets as _ds_mod
    _ds_mod._REGISTRY["ds_test"] = {"hz": "100Hz"}

    df = pd.DataFrame({"time": [0, 1, 2], "force": [1, 2, 3]})
    # "cyclogram" needs analyzer output; generic fallback skips it
    result = _render_generic_csv(_make_req("cyclogram"), df)
    assert result is None
