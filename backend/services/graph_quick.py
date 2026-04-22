"""Quick (interactive) graph service — returns Plotly-compatible JSON."""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from backend.models.schema import AnalysisRequest
from backend.services.analysis_engine import (
    load_csv,
    resolve_gcp,
    detect_heel_strikes,
    normalize_to_gcp,
)


SERIES_COLORS: list[str] = [
    "#1f77b4",  # muted blue
    "#ff7f0e",  # safety orange
    "#2ca02c",  # cooked asparagus green
    "#d62728",  # brick red
    "#9467bd",  # muted purple
    "#8c564b",  # chestnut brown
    "#e377c2",  # raspberry yogurt pink
    "#7f7f7f",  # middle gray
    "#bcbd22",  # curry yellow-green
    "#17becf",  # blue-teal
]


def guess_ylabel(columns: list[str]) -> str:
    """Infer a y-axis label from column names."""
    combined = " ".join(columns).lower()
    if "force" in combined or "_n" in combined:
        return "Force (N)"
    if "gcp" in combined:
        return "GCP (%)"
    if any(k in combined for k in ("pitch", "roll", "yaw")):
        return "Angle (°)"
    if "vel" in combined:
        return "Velocity (m/s)"
    if "pos" in combined:
        return "Position (m)"
    if "current" in combined:
        return "Current (A)"
    if "gyro" in combined:
        return "Angular Rate (°/s)"
    if "acc" in combined:
        return "Acceleration (m/s²)"
    if "phase" in combined or "event" in combined:
        return "Phase / Event"
    return "Value"


def _is_desired_column(col: str) -> bool:
    """Check if a column represents a desired/reference value."""
    return "Des" in col or "des" in col


def _color_key(col: str) -> str:
    """Group columns by side+type for shared color assignment.

    e.g., L_DesForce_N and L_ActForce_N → "L_Force_N" (same color, different dash)
    """
    return col.replace("Des", "").replace("Act", "").replace("Err", "")


def build_traces(
    dfs: list[tuple[str, pd.DataFrame]],
    request: AnalysisRequest,
) -> list[dict]:
    """Build a list of Plotly trace dicts.

    Desired columns are rendered as dashed lines, Actual as solid.
    Same side+type pairs share the same color for easy comparison.
    """
    columns = request.resolve_columns()
    traces: list[dict] = []

    # Assign colors: group by side+type, so Des/Act share color
    color_map: dict[str, str] = {}
    color_idx = 0

    for fname, df in dfs:
        for col in columns:
            if col not in df.columns:
                continue

            # Determine color — shared for Des/Act of same signal
            file_key = os.path.basename(fname)
            group = f"{file_key}/{_color_key(col)}"
            if group not in color_map:
                color_map[group] = SERIES_COLORS[color_idx % len(SERIES_COLORS)]
                color_idx += 1
            color = color_map[group]

            # Determine line style
            dash = "dash" if _is_desired_column(col) else "solid"
            width = 1.2 if _is_desired_column(col) else 1.8

            signal = df[col].to_numpy(dtype=float)

            if request.normalize_gcp:
                side = "L" if col.startswith("L_") else "R"
                gcp = resolve_gcp(df, side)
                hs = detect_heel_strikes(gcp)
                mean_101, _ = normalize_to_gcp(signal, hs, gcp=gcp)
                x_vals = np.linspace(0, 100, 101).tolist()
                y_vals = mean_101.tolist()
            else:
                x_vals = list(range(len(signal)))
                y_vals = signal.tolist()

            # Clean legend label — prioritize readability
            short_name = os.path.basename(fname)
            # Strip temp filename prefix/suffix (e.g., Force_50N_CSV_abc123.csv → Force_50N)
            short_name = short_name.replace(".csv", "").replace(".CSV", "")
            # Remove common tmp suffix patterns
            import re
            short_name = re.sub(r'_[a-z0-9]{8,}$', '', short_name)

            # Legend: if multiple files, show "file/col"; else just col
            if len(dfs) > 1:
                label = f"{short_name}/{col}"
            else:
                label = col  # Just the column name for single-file

            trace = {
                "x": x_vals,
                "y": y_vals,
                "name": label,
                "mode": "lines",
                "line": {"color": color, "width": width, "dash": dash},
            }
            traces.append(trace)

    return traces


def build_layout(request: AnalysisRequest, ylabel: str) -> dict:
    """Build a Plotly layout dict."""
    xaxis_title = "GCP (%)" if request.normalize_gcp else "Sample"
    title_text = request.analysis_type.value.replace("_", " ").title()

    return {
        "title": {"text": title_text, "x": 0.5, "xanchor": "center"},
        "xaxis": {
            "title": {"text": xaxis_title},
            "gridcolor": "#e5e7eb",
            "showgrid": True,
            "zeroline": False,
        },
        "yaxis": {
            "title": {"text": ylabel},
            "gridcolor": "#e5e7eb",
            "showgrid": True,
            "zeroline": False,
        },
        "legend": {
            "orientation": "v",
            "x": 1.02,
            "y": 1,
            "xanchor": "left",
            "yanchor": "top",
            "bgcolor": "rgba(255,255,255,0.8)",
            "bordercolor": "#d1d5db",
            "borderwidth": 1,
            "font": {"size": 11},
        },
        "showlegend": True,
        "plot_bgcolor": "white",
        "paper_bgcolor": "white",
        "font": {"size": 12, "family": "Inter, sans-serif"},
        "margin": {"l": 60, "r": 150, "t": 60, "b": 60},
        "hovermode": "x unified",
    }


def build_quick_response(
    request: AnalysisRequest,
    csv_paths: list[str],
) -> dict:
    """Load CSVs, build traces and layout, return Plotly-compatible dict."""
    dfs: list[tuple[str, pd.DataFrame]] = []
    for path in csv_paths:
        df = load_csv(path)  # raises FileNotFoundError if missing
        dfs.append((path, df))

    if not dfs:
        raise ValueError("No valid CSV files provided.")

    columns = request.resolve_columns()
    traces = build_traces(dfs, request)
    ylabel = guess_ylabel(columns)
    layout = build_layout(request, ylabel)

    return {"data": traces, "layout": layout}
