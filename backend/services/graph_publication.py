"""Publication-quality graph service — renders matplotlib SVG strings.

Uses Agg backend (headless) and per-journal rcParams presets.
Always closes figures after rendering to prevent memory leaks.
Integrates auto_analyzer for rich gait analysis graphs.
"""
from __future__ import annotations

import base64
import io
import os
import sys
import tempfile

import matplotlib
matplotlib.use("Agg")  # must be before pyplot import
import matplotlib.pyplot as plt
import numpy as np

# Add project root for auto_analyzer imports
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from backend.models.schema import AnalysisRequest
from backend.services.analysis_engine import (
    load_csv,
    resolve_gcp,
    detect_heel_strikes,
    normalize_to_gcp,
    run_full_analysis,
    AnalysisResult,
)
from backend.services.graph_quick import SERIES_COLORS, _is_desired_column, _color_key
from backend.services.journal_resolver import resolve_journal as _resolve_journal, apply_to_figure

from tools.auto_analyzer.plotter import (
    plot_force_mean_sd,
    plot_force_individual_strides,
    plot_force_tracking_error,
    plot_force_lr_comparison,
    plot_stride_time_trend,
    plot_stride_length_trend,
    plot_gait_summary,
    plot_stride_time_histogram,
    plot_symmetry,
    plot_force_comparison_overlay,
    plot_stats_comparison,
)
from tools.auto_analyzer.styles import apply_style, STYLES


JOURNAL_RCPARAMS: dict[str, dict] = {
    "ieee_tnsre": {
        "figsize": (3.5, 2.6),
        "font_size": 8,
        "line_width": 1.0,
        "font_family": "Times New Roman",
    },
    "jner": {
        "figsize": (4.5, 3.4),
        "font_size": 9,
        "line_width": 1.2,
        "font_family": "Arial",
    },
    "ieee_ral": {
        "figsize": (3.5, 2.6),
        "font_size": 8,
        "line_width": 1.0,
        "font_family": "Times New Roman",
    },
    "science_robotics": {
        "figsize": (3.5, 2.6),
        "font_size": 7,
        "line_width": 0.8,
        "font_family": "Helvetica",
    },
    "biomechanics": {
        "figsize": (4.0, 3.0),
        "font_size": 10,
        "line_width": 1.5,
        "font_family": "Arial",
    },
    "gait_posture": {
        "figsize": (4.0, 3.0),
        "font_size": 10,
        "line_width": 1.5,
        "font_family": "Arial",
    },
    "plos_one": {
        "figsize": (5.2, 3.9),
        "font_size": 10,
        "line_width": 1.5,
        "font_family": "Arial",
    },
    "nature": {
        "figsize": (3.5, 2.6),
        "font_size": 7,
        "line_width": 0.75,
        "font_family": "Helvetica",
    },
    "icra_iros": {
        "figsize": (3.5, 2.6),
        "font_size": 8,
        "line_width": 1.0,
        "font_family": "Times New Roman",
    },
    "default": {
        "figsize": (6.0, 4.0),
        "font_size": 10,
        "line_width": 1.5,
        "font_family": "Arial",
    },
}


def _apply_rcparams(params: dict) -> None:
    """Apply journal rcParams to the current matplotlib context."""
    # NOTE: global rcParams mutation — safe only under single-process uvicorn.
    # For multi-worker deployments, use matplotlib.rc_context() instead.
    plt.rcParams.update({
        "font.size": params["font_size"],
        "font.family": "sans-serif",
        "font.sans-serif": [params["font_family"], "DejaVu Sans"],
        "axes.linewidth": 0.8,
        "xtick.major.width": 0.8,
        "ytick.major.width": 0.8,
        "legend.fontsize": max(6, params["font_size"] - 1),
    })


def _figure_to_svg(fig: plt.Figure) -> str:
    """Serialize a matplotlib Figure to an SVG string."""
    try:
        buf = io.BytesIO()
        fig.savefig(buf, format="svg", bbox_inches="tight")
        buf.seek(0)
        return buf.getvalue().decode("utf-8")
    finally:
        plt.close(fig)


def render_svg(
    request: AnalysisRequest,
    csv_paths: list[str],
    journal: str = "default",
) -> str:
    """Render a publication-quality matplotlib figure and return SVG string.

    Parameters
    ----------
    request:
        Analysis parameters.
    csv_paths:
        Paths to H-Walker CSV log files.
    journal:
        Key into JOURNAL_RCPARAMS. Unknown journals fall back to "default".
    """
    if not csv_paths:
        raise ValueError("csv_paths must not be empty")

    MM_TO_INCH = 1 / 25.4

    if journal == "default":
        params = JOURNAL_RCPARAMS.get("default", JOURNAL_RCPARAMS["default"])
        rc_params_dict = {
            "font.size": params["font_size"],
            "font.family": "sans-serif",
            "font.sans-serif": [params["font_family"], "DejaVu Sans"],
            "axes.linewidth": 0.8,
            "xtick.major.width": 0.8,
            "ytick.major.width": 0.8,
            "legend.fontsize": max(6, params["font_size"] - 1),
        }
    else:
        try:
            style = _resolve_journal(journal)
            params = {
                "figsize": (
                    style["figure_width_mm"] * MM_TO_INCH,
                    style["figure_height_mm"] * MM_TO_INCH,
                ),
                "font_size": style["font_size"],
                "line_width": style["line_width"],
                "font_family": style["font_family"],
            }
            rc_params_dict = {
                "font.size": style["font_size"],
                "font.family": "sans-serif",
                "font.sans-serif": [style["font_family"], "DejaVu Sans"],
                "axes.linewidth": 0.8,
                "xtick.major.width": 0.8,
                "ytick.major.width": 0.8,
                "legend.fontsize": max(6, style["font_size"] - 1),
                "figure.figsize": [
                    style["figure_width_mm"] * MM_TO_INCH,
                    style["figure_height_mm"] * MM_TO_INCH,
                ],
            }
        except Exception:
            params = JOURNAL_RCPARAMS.get(journal, JOURNAL_RCPARAMS["default"])
            rc_params_dict = {
                "font.size": params["font_size"],
                "font.family": "sans-serif",
                "font.sans-serif": [params["font_family"], "DejaVu Sans"],
                "axes.linewidth": 0.8,
                "xtick.major.width": 0.8,
                "ytick.major.width": 0.8,
                "legend.fontsize": max(6, params["font_size"] - 1),
            }

    with matplotlib.rc_context(rc_params_dict):
        columns = request.resolve_columns()
        lw = params["line_width"]

        # Load all files
        dfs = [(os.path.basename(p), load_csv(p)) for p in csv_paths]

        if request.compare_mode and len(dfs) > 1:
            # One subplot per file, shared x-axis
            n_files = len(dfs)
            fig, axes = plt.subplots(
                n_files, 1,
                figsize=params["figsize"],
                sharex=True,
                squeeze=False,
            )
            for ax_idx, (fname, df) in enumerate(dfs):
                ax = axes[ax_idx][0]
                color_map_pub: dict[str, str] = {}
                color_idx = 0
                for col in columns:
                    if col not in df.columns:
                        continue
                    signal = df[col].to_numpy(dtype=float)
                    # Shared color for Des/Act of same signal
                    group = _color_key(col)
                    if group not in color_map_pub:
                        color_map_pub[group] = SERIES_COLORS[color_idx % len(SERIES_COLORS)]
                        color_idx += 1
                    color = color_map_pub[group]
                    ls = '--' if _is_desired_column(col) else '-'
                    line_w = lw * 0.8 if _is_desired_column(col) else lw

                    if request.normalize_gcp:
                        side = "L" if col.startswith("L_") else "R"
                        gcp = resolve_gcp(df, side)
                        hs = detect_heel_strikes(gcp)
                        mean_101, std_101 = normalize_to_gcp(signal, hs, gcp=gcp)
                        x_vals = np.linspace(0, 100, 101)
                        ax.plot(x_vals, mean_101, color=color, linewidth=line_w, linestyle=ls, label=col)
                        ax.fill_between(
                            x_vals,
                            mean_101 - std_101,
                            mean_101 + std_101,
                            alpha=0.2,
                            color=color,
                        )
                    else:
                        ax.plot(signal, color=color, linewidth=line_w, linestyle=ls, label=col)

                ax.set_title(fname, fontsize=params["font_size"])
                ax.legend(loc="upper right")

            axes[-1][0].set_xlabel(
                "GCP (%)" if request.normalize_gcp else "Sample"
            )
        else:
            # Check if L/R columns both exist → split into subplots
            has_left = any(c.startswith("L_") for c in columns)
            has_right = any(c.startswith("R_") for c in columns)
            split_lr = has_left and has_right and "both" in request.sides

            if split_lr:
                # L/R side-by-side subplots
                fig_w, fig_h = params["figsize"]
                fig, axes_lr = plt.subplots(
                    1, 2, figsize=(fig_w * 1.8, fig_h), sharey=True,
                )
                side_map = {"L": (axes_lr[0], "Left"), "R": (axes_lr[1], "Right")}

                for fname, df in dfs:
                    for side_prefix, (ax_side, side_title) in side_map.items():
                        color_map_pub: dict[str, str] = {}
                        color_idx = 0
                        for col in columns:
                            if not col.startswith(f"{side_prefix}_"):
                                continue
                            if col not in df.columns:
                                continue
                            signal = df[col].to_numpy(dtype=float)
                            group = _color_key(col)
                            if group not in color_map_pub:
                                color_map_pub[group] = SERIES_COLORS[color_idx % len(SERIES_COLORS)]
                                color_idx += 1
                            color = color_map_pub[group]
                            ls = '--' if _is_desired_column(col) else '-'
                            line_w = lw * 0.8 if _is_desired_column(col) else lw
                            # Shorter label: strip side prefix for clarity
                            short_label = col[2:]  # Remove "L_" or "R_"
                            if _is_desired_column(col):
                                short_label = "Desired"
                            elif "Act" in col:
                                short_label = "Actual"
                            elif "Err" in col:
                                short_label = "Error"

                            if request.normalize_gcp:
                                gcp = resolve_gcp(df, side_prefix)
                                hs = detect_heel_strikes(gcp)
                                mean_101, std_101 = normalize_to_gcp(signal, hs, gcp=gcp)
                                x_vals = np.linspace(0, 100, 101)
                                ax_side.plot(x_vals, mean_101, color=color, linewidth=line_w, linestyle=ls, label=short_label)
                                ax_side.fill_between(
                                    x_vals,
                                    mean_101 - std_101,
                                    mean_101 + std_101,
                                    alpha=0.15,
                                    color=color,
                                )
                            else:
                                ax_side.plot(signal, color=color, linewidth=line_w, linestyle=ls, label=short_label)

                        ax_side.set_title(side_title, fontsize=params["font_size"])
                        ax_side.set_xlabel("GCP (%)" if request.normalize_gcp else "Sample")
                        ax_side.legend(loc="upper right", fontsize=max(5, params["font_size"] - 2))
                        ax_side.grid(True, alpha=0.2)

                axes_lr[0].set_ylabel(
                    request.analysis_type.value.replace("_", " ").title() + " (N)"
                    if "force" in request.analysis_type.value
                    else request.analysis_type.value.replace("_", " ").title()
                )
            else:
                # Single axes (one side only, or non-sided columns)
                fig, ax = plt.subplots(figsize=params["figsize"])
                color_map_pub: dict[str, str] = {}
                color_idx = 0

                for fname, df in dfs:
                    for col in columns:
                        if col not in df.columns:
                            continue
                        signal = df[col].to_numpy(dtype=float)
                        file_key = fname if len(dfs) > 1 else ""
                        group = f"{file_key}/{_color_key(col)}"
                        if group not in color_map_pub:
                            color_map_pub[group] = SERIES_COLORS[color_idx % len(SERIES_COLORS)]
                            color_idx += 1
                        color = color_map_pub[group]
                        ls = '--' if _is_desired_column(col) else '-'
                        line_w = lw * 0.8 if _is_desired_column(col) else lw
                        label = f"{fname}/{col}" if len(dfs) > 1 else col

                        if request.normalize_gcp:
                            side = "L" if col.startswith("L_") else "R"
                            gcp = resolve_gcp(df, side)
                            hs = detect_heel_strikes(gcp)
                            mean_101, std_101 = normalize_to_gcp(signal, hs, gcp=gcp)
                            x_vals = np.linspace(0, 100, 101)
                            ax.plot(x_vals, mean_101, color=color, linewidth=line_w, linestyle=ls, label=label)
                            ax.fill_between(
                                x_vals,
                                mean_101 - std_101,
                                mean_101 + std_101,
                                alpha=0.2,
                                color=color,
                            )
                        else:
                            ax.plot(signal, color=color, linewidth=line_w, linestyle=ls, label=label)

                ax.set_xlabel("GCP (%)" if request.normalize_gcp else "Sample")
                ax.legend(loc="upper right")

        title_text = request.analysis_type.value.replace("_", " ").title()
        fig.suptitle(title_text, fontsize=params["font_size"] + 1)
        fig.tight_layout()

        return _figure_to_svg(fig)


# ================================================================
# AUTO_ANALYZER INTEGRATION — Rich analysis graphs
# ================================================================

def render_full_analysis_svgs(
    csv_paths: list[str],
    journal: str = "default",
    graph_types: list[str] | None = None,
) -> dict[str, str]:
    """Run full auto_analyzer pipeline and return {name: svg_string} dict.

    graph_types: optional filter, e.g. ['force_mean_sd', 'gait_summary'].
    If None, generates all available graphs.
    """
    # Map journal name to auto_analyzer style key
    style_map = {
        'ieee_tnsre': 'ieee', 'ieee_ral': 'ieee', 'icra_iros': 'ieee',
        'nature': 'nature', 'science_robotics': 'nature',
        'jner': 'elsevier', 'gait_posture': 'elsevier',
        'biomechanics': 'elsevier', 'plos_one': 'elsevier',
        'medical_eng_physics': 'elsevier',
        'default': 'default',
    }
    style_key = style_map.get(journal, 'default')
    style = apply_style(style_key)

    # Analyze all files
    results = []
    for path in csv_paths:
        results.append(run_full_analysis(path))

    # Render to temp directory then convert to SVG
    with tempfile.TemporaryDirectory() as tmpdir:
        svgs = {}

        # Available graph generators (single-file)
        all_generators = {
            'force_mean_sd': plot_force_mean_sd,
            'force_individual': plot_force_individual_strides,
            'force_tracking': plot_force_tracking_error,
            'force_lr': plot_force_lr_comparison,
            'stride_time_trend': plot_stride_time_trend,
            'stride_length_trend': plot_stride_length_trend,
            'gait_summary': plot_gait_summary,
            'stride_time_histogram': plot_stride_time_histogram,
            'symmetry': plot_symmetry,
        }

        # Multi-file generators
        multi_generators = {
            'force_overlay': plot_force_comparison_overlay,
            'stats_comparison': plot_stats_comparison,
        }

        active = graph_types or list(all_generators.keys()) + (
            list(multi_generators.keys()) if len(results) >= 2 else []
        )

        for r in results:
            prefix = os.path.splitext(r.filename)[0]
            for name, fn in all_generators.items():
                if name not in active:
                    continue
                saved = fn(r, style, tmpdir)
                for png_path in saved:
                    key = f"{prefix}/{os.path.basename(png_path).replace('.png', '')}"
                    svgs[key] = _png_to_base64(png_path)

        if len(results) >= 2:
            for name, fn in multi_generators.items():
                if name not in active:
                    continue
                saved = fn(results, style, tmpdir)
                for png_path in saved:
                    key = f"comparison/{os.path.basename(png_path).replace('.png', '')}"
                    svgs[key] = _png_to_base64(png_path)

    return svgs


def _png_to_base64(path: str) -> str:
    """Read PNG file and return data URI."""
    with open(path, 'rb') as f:
        data = f.read()
    return f"data:image/png;base64,{base64.b64encode(data).decode()}"
