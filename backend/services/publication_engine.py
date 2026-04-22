"""
Phase 2 publication engine — HANDOFF §2.4 implementation.

Given a GRAPH_TPLS key + JOURNAL preset + width variant + format + dpi,
produces a journal-ready figure (SVG / PDF / EPS / PNG / TIFF) at EXACT
submission size with correct fonts, point sizes, stroke widths, palettes.

Single source of truth for presets lives here (Python), mirrored in
frontend/src/data/journalPresets.ts — the mirror is intentionally verbatim
so that the pub-bar preview (CSS) matches the exported binary bit-perfect.

Design notes
------------
* Mockup GRAPH_TPLS path data (cubic Bezier SVG strings) is imported from
  the mirrored GRAPH_SPECS dict below and sampled to polylines in pure
  Python. No extra deps.
* Matplotlib renders on the Agg / SVG / PS backends directly; TIFF goes
  via PIL from the PNG path.
* rcParams are applied inside a `with mpl.rc_context()` block so request
  handlers are thread-safe.

Future (Phase B): replace the hand-coded GRAPH_SPECS with numeric data
pulled from the registered dataset CSV (`backend.routers.datasets`).
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field

import matplotlib
matplotlib.use("Agg")  # headless
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

# ============================================================
# JOURNAL_PRESETS — Python mirror of frontend/src/data/journalPresets.ts
# ============================================================

@dataclass
class Preset:
    name: str
    full: str
    col1: tuple[float, float]          # (width_mm, height_mm)
    col2: tuple[float, float]
    onehalf: tuple[float, float] | None  # Elsevier only
    max_h_mm: float
    font: str
    font_fallback: list[str]
    body_pt: float
    axis_pt: float
    legend_pt: float
    title_pt: float
    stroke_pt: float
    grid_pt: float
    palette: list[str]            # grayscale / minimal
    palette_color: list[str]      # full color
    colorblind_safe: bool
    bg: str
    axis_color: str
    grid_color: str
    formats: list[str]
    dpi: int
    notes: str


JOURNAL_PRESETS: dict[str, Preset] = {
    "ieee": Preset(
        name="IEEE", full="IEEE Transactions / Journals",
        col1=(88.9, 70.0), col2=(181.0, 90.0), onehalf=None, max_h_mm=216.0,
        font="Times New Roman",
        font_fallback=["Times New Roman", "Times", "serif"],
        body_pt=8, axis_pt=8, legend_pt=7, title_pt=10, stroke_pt=1.0, grid_pt=0.4,
        palette=["#000000", "#555555", "#888888", "#BBBBBB"],
        palette_color=["#1f77b4", "#d62728", "#2ca02c", "#ff7f0e", "#9467bd"],
        colorblind_safe=False, bg="#ffffff", axis_color="#000000", grid_color="#CCCCCC",
        formats=["PDF", "EPS", "TIFF", "SVG", "PNG"], dpi=600,
        notes="1 col 88.9mm / 2 col 181mm · 8–10pt Times · grayscale preferred",
    ),
    "nature": Preset(
        name="Nature", full="Nature · Nature journals",
        col1=(89.0, 60.0), col2=(183.0, 90.0), onehalf=None, max_h_mm=247.0,
        font="Helvetica",
        font_fallback=["Helvetica", "Arial", "sans-serif"],
        body_pt=7, axis_pt=7, legend_pt=6, title_pt=8, stroke_pt=0.5, grid_pt=0.25,
        palette=["#000000", "#E69F00", "#56B4E9", "#009E73", "#F0E442",
                 "#0072B2", "#D55E00", "#CC79A7"],
        palette_color=["#000000", "#E69F00", "#56B4E9", "#009E73", "#F0E442",
                       "#0072B2", "#D55E00", "#CC79A7"],
        colorblind_safe=True, bg="#ffffff", axis_color="#000000", grid_color="#E5E5E5",
        formats=["PDF", "EPS", "AI", "TIFF"], dpi=300,
        notes="Single 89mm / double 183mm · Helvetica 5–7pt · Wong colorblind-safe palette",
    ),
    "apa": Preset(
        name="APA", full="APA 7th edition",
        col1=(85.0, 65.0), col2=(174.0, 100.0), onehalf=None, max_h_mm=235.0,
        font="Arial",
        font_fallback=["Arial", "Helvetica", "sans-serif"],
        body_pt=10, axis_pt=10, legend_pt=9, title_pt=11, stroke_pt=0.75, grid_pt=0.3,
        palette=["#000000", "#555555", "#888888", "#BBBBBB"],
        palette_color=["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"],
        colorblind_safe=False, bg="#ffffff", axis_color="#000000", grid_color="#DDDDDD",
        formats=["PDF", "SVG", "PNG", "TIFF"], dpi=300,
        notes="Sans-serif 8–14pt · grayscale preferred · figure note below",
    ),
    "elsevier": Preset(
        name="Elsevier", full="Elsevier journals",
        col1=(90.0, 60.0), col2=(190.0, 90.0), onehalf=(140.0, 80.0), max_h_mm=240.0,
        font="Arial",
        font_fallback=["Arial", "Helvetica", "sans-serif"],
        body_pt=8, axis_pt=8, legend_pt=7, title_pt=9, stroke_pt=0.5, grid_pt=0.25,
        palette=["#000000", "#E41A1C", "#377EB8", "#4DAF4A", "#984EA3", "#FF7F00"],
        palette_color=["#E41A1C", "#377EB8", "#4DAF4A", "#984EA3", "#FF7F00", "#FFFF33", "#A65628"],
        colorblind_safe=False, bg="#ffffff", axis_color="#000000", grid_color="#DDDDDD",
        formats=["EPS", "PDF", "TIFF", "JPEG"], dpi=300,
        notes="Single 90mm / 1.5 col 140mm / double 190mm · Arial · EPS preferred",
    ),
    "mdpi": Preset(
        name="MDPI", full="MDPI (Applied Sciences, Sensors, etc.)",
        col1=(85.0, 65.0), col2=(170.0, 90.0), onehalf=None, max_h_mm=225.0,
        font="Palatino",
        font_fallback=["Palatino", "Palatino Linotype", "Book Antiqua", "serif"],
        body_pt=8, axis_pt=8, legend_pt=7, title_pt=10, stroke_pt=0.75, grid_pt=0.3,
        palette=["#000000", "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"],
        palette_color=["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"],
        colorblind_safe=False, bg="#ffffff", axis_color="#000000", grid_color="#E0E0E0",
        formats=["PDF", "TIFF", "PNG", "EPS"], dpi=1000,
        notes="Single 85mm / double 170mm · Palatino 8pt · 1000 dpi line art",
    ),
    "jner": Preset(
        name="JNER", full="J. NeuroEngineering & Rehabilitation (BMC)",
        col1=(85.0, 65.0), col2=(170.0, 90.0), onehalf=None, max_h_mm=225.0,
        font="Arial",
        font_fallback=["Arial", "Helvetica", "sans-serif"],
        body_pt=8, axis_pt=8, legend_pt=7, title_pt=10, stroke_pt=0.75, grid_pt=0.3,
        palette=["#000000", "#0072B2", "#D55E00", "#009E73", "#CC79A7", "#F0E442"],
        palette_color=["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#F0E442", "#56B4E9"],
        colorblind_safe=True, bg="#ffffff", axis_color="#000000", grid_color="#E0E0E0",
        formats=["PDF", "EPS", "PNG", "TIFF"], dpi=300,
        notes="Springer/BMC · Arial 8pt · colorblind-safe · 300 dpi",
    ),
}


# ============================================================
# GRAPH_SPECS — server-side mirror of GRAPH_TPLS
#   The SVG path strings are identical to those in
#   frontend/src/data/graphTemplates.ts, so sampling produces the
#   same visual as the browser preview.
# ============================================================

@dataclass
class PathSpec:
    color: str
    width: float            # mockup line width (relative)
    label: str
    d: str                  # SVG path commands (M/L/C only)
    dash: str | None = None


@dataclass
class BandSpec:
    color: str
    opacity: float
    upper: str
    lower: str


@dataclass
class HLineSpec:
    y: float
    color: str
    dash: str
    label: str


@dataclass
class BoxSpec:
    x: float
    label: str
    color: str
    min: float
    q1: float
    med: float
    q3: float
    max: float


@dataclass
class BarSpec:
    x: float
    w: float
    h: float
    color: str
    label: str


@dataclass
class GraphSpec:
    eyebrow: str
    title: str
    ds: str
    y_unit: str
    x_unit: str
    y_ticks: list[str]
    x_ticks: list[str]
    paths: list[PathSpec] = field(default_factory=list)
    bands: list[BandSpec] = field(default_factory=list)
    hlines: list[HLineSpec] = field(default_factory=list)
    boxes: list[BoxSpec] = field(default_factory=list)
    bars: list[BarSpec] = field(default_factory=list)
    summary: list[tuple[str, str]] = field(default_factory=list)


_LA, _LD = "#3B82C4", "#7FB5E4"
_RA, _RD = "#D35454", "#E89B9B"
_ACC = "#F09708"


GRAPH_SPECS: dict[str, GraphSpec] = {
    "force": GraphSpec(
        eyebrow="Force · L vs R", title="Ground reaction force", ds="ds1",
        y_unit="Force (N)", x_unit="Gait cycle (%)",
        y_ticks=["60", "45", "30", "15", "0"],
        x_ticks=["0", "25", "50", "75", "100"],
        paths=[
            PathSpec(_LA, 2.0, "L Actual",  "M48,160 C70,155 92,120 114,72 C138,38 158,28 180,42 C202,58 224,80 246,110 C270,140 290,152 312,150 C332,148 354,134 376,122 C394,114 402,122 408,138"),
            PathSpec(_LD, 1.3, "L Desired", "M48,164 C70,160 92,126 114,78 C138,42 158,34 180,48 C204,62 224,82 246,112 C270,140 292,154 312,152 C332,148 354,134 376,124 C394,116 402,124 408,140", dash="4 3"),
            PathSpec(_RA, 2.0, "R Actual",  "M48,165 C70,160 92,150 114,108 C138,62 160,48 180,64 C202,82 224,100 246,130 C270,150 292,156 312,152 C332,150 354,138 376,124 C394,114 402,122 408,136"),
            PathSpec(_RD, 1.3, "R Desired", "M48,167 C70,162 92,154 114,114 C138,68 160,54 180,70 C202,88 224,104 246,132 C270,150 292,156 312,154 C332,150 354,138 376,126 C394,114 402,124 408,138", dash="4 3"),
        ],
        summary=[("n strides", "14"), ("peak ΔL", "48.2 N"), ("peak ΔR", "46.7 N"), ("asym", "3.2%")],
    ),
    "imu": GraphSpec(
        eyebrow="IMU · Pitch", title="Shank vs thigh pitch", ds="ds2",
        y_unit="Pitch (°)", x_unit="Time (s)",
        y_ticks=["+20", "+10", "0", "−10", "−20"],
        x_ticks=["0", "2", "4", "6", "8"],
        paths=[
            PathSpec(_LA, 1.8, "Shank", "M48,100 C70,70 92,40 114,50 C136,60 158,130 180,140 C202,150 224,90 246,60 C268,50 290,110 312,140 C332,150 354,100 376,70 C394,55 402,80 408,100"),
            PathSpec(_RA, 1.8, "Thigh", "M48,110 C70,90 92,70 114,78 C138,88 158,120 180,126 C204,132 224,100 246,82 C268,75 290,108 312,128 C332,136 354,108 376,88 C394,78 402,90 408,102"),
        ],
        summary=[("strides", "3"), ("cadence", "112 spm"), ("stride T", "1.08 s")],
    ),
    "force_avg": GraphSpec(
        eyebrow="Force · mean ± SD", title="GRF stride-averaged (n=14)", ds="ds1",
        y_unit="Vertical GRF (N)", x_unit="Gait cycle (%)",
        y_ticks=["60", "45", "30", "15", "0"],
        x_ticks=["0", "25", "50", "75", "100"],
        bands=[
            BandSpec("#3B82C4", 0.18,
                "M48,148 C70,144 92,108 114,58 C138,24 158,14 180,28 C202,44 224,66 246,96 C270,126 290,138 312,136 C332,134 354,120 376,108 C394,100 402,108 408,124",
                "M48,172 C70,167 92,132 114,86 C138,52 158,42 180,56 C202,72 224,94 246,124 C270,154 290,166 312,164 C332,162 354,148 376,136 C394,128 402,136 408,152"),
            BandSpec("#D35454", 0.18,
                "M48,153 C70,148 92,138 114,94 C138,48 160,34 180,50 C202,68 224,86 246,116 C270,136 292,142 312,138 C332,136 354,124 376,110 C394,100 402,108 408,122",
                "M48,177 C70,172 92,162 114,122 C138,76 160,62 180,78 C202,96 224,114 246,144 C270,164 292,170 312,166 C332,164 354,152 376,138 C394,128 402,136 408,150"),
        ],
        paths=[
            PathSpec("#1E5F9E", 2.0, "L mean", "M48,160 C70,155 92,120 114,72 C138,38 158,28 180,42 C202,58 224,80 246,110 C270,140 290,152 312,150 C332,148 354,134 376,122 C394,114 402,122 408,138"),
            PathSpec("#9E3838", 2.0, "R mean", "M48,165 C70,160 92,150 114,108 C138,62 160,48 180,64 C202,82 224,100 246,130 C270,150 292,156 312,152 C332,150 354,138 376,124 C394,114 402,122 408,136"),
        ],
        summary=[("n strides", "14"), ("mean peak L", "48.2 ± 0.6 N"), ("mean peak R", "46.7 ± 0.7 N"), ("CV", "1.3%")],
    ),
    "asymmetry": GraphSpec(
        eyebrow="Asymmetry · per stride", title="Asymmetry index across strides", ds="ds1",
        y_unit="Asymmetry (%)", x_unit="Stride #",
        y_ticks=["10", "7.5", "5", "2.5", "0"],
        x_ticks=["1", "4", "7", "10", "14"],
        paths=[
            PathSpec(_ACC, 1.8, "asym_idx", "M48,120 L76,98 L102,115 L128,105 L156,90 L184,110 L210,95 L238,118 L264,100 L292,85 L318,112 L348,102 L376,92 L408,106"),
        ],
        hlines=[HLineSpec(140, "#6B7280", "3 3", "5% threshold")],
        summary=[("mean", "2.1 ± 0.8%"), ("max", "3.6%"), ("≥5%", "0 strides")],
    ),
    "peak_box": GraphSpec(
        eyebrow="Peak force · L vs R", title="Peak vertical GRF — boxplot", ds="ds1",
        y_unit="Peak GRF (N)", x_unit="",
        y_ticks=["50", "48", "46", "44", "42"], x_ticks=[],
        boxes=[
            BoxSpec(140, "L", "#3B82C4", 170, 162, 158, 155, 148),
            BoxSpec(280, "R", "#D35454", 175, 167, 163, 160, 152),
        ],
        summary=[("n=14", "paired"), ("Δ mean", "+1.5 N"), ("p", ".006")],
    ),
    "cop": GraphSpec(
        eyebrow="CoP · trajectory", title="Center of pressure path", ds="ds1",
        y_unit="AP (mm)", x_unit="ML (mm)",
        y_ticks=["+50", "+25", "0", "−25", "−50"],
        x_ticks=["−40", "−20", "0", "+20", "+40"],
        paths=[
            PathSpec("#3B82C4", 1.6, "L CoP", "M100,160 C110,140 115,120 120,100 C125,80 130,60 140,40 C145,35 150,35 155,40"),
            PathSpec("#D35454", 1.6, "R CoP", "M300,160 C295,140 290,120 285,100 C280,80 275,60 268,40 C263,35 258,35 255,40"),
        ],
        summary=[("L path", "142 mm"), ("R path", "138 mm"), ("Δ", "+2.9%")],
    ),
    "cv_bar": GraphSpec(
        eyebrow="Variability · CV", title="Coefficient of variation per trial", ds="ds3",
        y_unit="CV (%)", x_unit="Trial",
        y_ticks=["8", "6", "4", "2", "0"],
        x_ticks=["T1", "T2", "T3", "T4", "T5"],
        bars=[
            BarSpec(80, 40, 60, "#7FB5E4", "T1"),
            BarSpec(150, 40, 48, "#3B82C4", "T2"),
            BarSpec(220, 40, 36, "#E89B9B", "T3"),
            BarSpec(290, 40, 22, "#D35454", "T4"),
            BarSpec(360, 40, 14, "#F09708", "T5"),
        ],
        summary=[("trials", "5"), ("improving", "T1→T5"), ("final CV", "0.7%")],
    ),
    "trials": GraphSpec(
        eyebrow="Trials · N=5", title="Trial overlay", ds="ds3",
        y_unit="Normalized force", x_unit="Gait cycle (%)",
        y_ticks=["1.0", "0.75", "0.5", "0.25", "0"],
        x_ticks=["0", "25", "50", "75", "100"],
        paths=[
            PathSpec("#7FB5E4", 1.4, "Trial 1", "M48,170 C82,150 112,100 150,60 C188,40 222,32 258,52 C292,78 326,130 360,160 C384,172 398,168 408,164"),
            PathSpec("#3B82C4", 1.4, "Trial 2", "M48,172 C82,154 112,104 150,66 C188,46 222,38 258,58 C292,82 326,132 360,160 C384,170 398,168 408,166"),
            PathSpec("#E89B9B", 1.4, "Trial 3", "M48,168 C82,148 112,98 150,58 C188,38 222,30 258,50 C292,76 326,128 360,158 C384,170 398,166 408,162"),
            PathSpec("#D35454", 1.4, "Trial 4", "M48,174 C82,156 112,108 150,70 C188,50 222,42 258,60 C292,84 326,134 360,162 C384,172 398,170 408,168"),
            PathSpec(_ACC, 2.2, "Trial 5 · target", "M48,166 C82,146 112,94 150,54 C188,34 222,26 258,46 C292,72 326,124 360,154 C384,168 398,164 408,160"),
        ],
        summary=[("trials", "5"), ("CV", "4.1%"), ("target Δ", "+2.3%")],
    ),
    # =====================================================
    # Phase 2I · Debug raw time-series (full duration + HS markers)
    # =====================================================
    "debug_ts": GraphSpec(
        eyebrow="Debug · raw time-series", title="Raw signals with heel-strike markers", ds="ds1",
        y_unit="", x_unit="Time (s)",
        y_ticks=["", "", "", "", ""],
        x_ticks=["0", "5", "10", "15", "20"],
        paths=[
            PathSpec(_LA, 1.2, "L_ActForce_N", "M48,100 C80,60 120,150 160,80 C200,40 240,140 280,90 C320,50 360,150 408,100"),
            PathSpec(_RA, 1.2, "R_ActForce_N", "M48,110 C80,70 120,160 160,90 C200,50 240,150 280,100 C320,60 360,160 408,110"),
        ],
        summary=[("hint", "dotted = heel-strikes"), ("purpose", "find where signal went weird")],
    ),

    # =====================================================
    # Phase 2H · L/R side-by-side GCP subplot — top-requested kinetic figure
    # =====================================================
    "force_lr_subplot": GraphSpec(
        eyebrow="Force · L / R subplots", title="GCP-normalized force per leg", ds="ds1",
        y_unit="Force (N)", x_unit="Gait cycle (%)",
        y_ticks=["60", "45", "30", "15", "0"],
        x_ticks=["0", "25", "50", "75", "100"],
        paths=[
            PathSpec(_LA, 2.0, "L actual",  "M48,160 C70,155 92,120 114,72 C138,38 158,28 180,42 C202,58 224,80 246,110 C270,140 290,152 312,150 C332,148 354,134 376,122 C394,114 402,122 408,138"),
            PathSpec(_LD, 1.3, "L desired", "M48,164 C70,160 92,126 114,78 C138,42 158,34 180,48 C204,62 224,82 246,112 C270,140 292,154 312,152 C332,148 354,134 376,124 C394,116 402,124 408,140", dash="4 3"),
        ],
        summary=[("L mean peak", "48.2 N"), ("R mean peak", "46.7 N"), ("asym", "3.2%")],
    ),

    # =====================================================
    # Phase 0 · Motion / kinematic templates (fallback specs
    # for when no dataset_id — frontend uses these for the
    # empty-state preview).
    # =====================================================
    "imu_avg": GraphSpec(
        eyebrow="Kinematics · mean ± SD", title="Joint angle over gait cycle", ds="ds2",
        y_unit="Pitch (°)", x_unit="Gait cycle (%)",
        y_ticks=["+20", "+10", "0", "−10", "−20"],
        x_ticks=["0", "25", "50", "75", "100"],
        paths=[
            PathSpec(_LA, 1.8, "L shank", "M48,100 C70,70 92,40 114,60 C138,80 158,130 180,140 C202,140 224,90 246,60 C268,50 290,110 312,140 C332,140 354,100 376,70 C394,55 402,80 408,100"),
            PathSpec(_RA, 1.8, "R shank", "M48,110 C70,90 92,70 114,78 C138,88 158,120 180,126 C204,132 224,100 246,82 C268,75 290,108 312,128 C332,136 354,108 376,88 C394,78 402,90 408,102"),
        ],
        summary=[("ROM L", "38.4°"), ("ROM R", "37.1°"), ("asym", "3.4%")],
    ),
    "cyclogram": GraphSpec(
        eyebrow="Phase portrait", title="Shank vs thigh cyclogram", ds="ds2",
        y_unit="Thigh pitch (°)", x_unit="Shank pitch (°)",
        y_ticks=["+30", "+15", "0", "−15", "−30"],
        x_ticks=["−20", "−10", "0", "+10", "+20"],
        paths=[
            PathSpec(_ACC, 1.8, "Cycle avg", "M150,100 C120,60 140,30 200,40 C260,50 300,80 340,110 C340,140 280,160 220,150 C160,140 180,120 150,100"),
        ],
        summary=[("cycle", "closed"), ("phase lag", "12°")],
    ),
    "stride_time_trend": GraphSpec(
        eyebrow="Temporal · fatigue", title="Stride time over strides", ds="ds1",
        y_unit="Stride T (s)", x_unit="Stride #",
        y_ticks=["1.20", "1.10", "1.00", "0.90", "0.80"],
        x_ticks=["1", "5", "10", "15", "20"],
        paths=[
            PathSpec(_LA, 1.6, "L", "M48,100 L80,96 L120,104 L160,100 L200,108 L240,104 L280,112 L320,108 L360,116 L408,112"),
            PathSpec(_RA, 1.6, "R", "M48,104 L80,100 L120,108 L160,104 L200,112 L240,108 L280,116 L320,112 L360,120 L408,116"),
        ],
        summary=[("slope L", "+0.3 ms/str"), ("slope R", "+0.4 ms/str")],
    ),
    "stance_swing_bar": GraphSpec(
        eyebrow="Temporal phases", title="Stance / swing percentages", ds="ds1",
        y_unit="% gait cycle", x_unit="",
        y_ticks=["100", "75", "50", "25", "0"],
        x_ticks=["L stance", "L swing", "R stance", "R swing"],
        bars=[
            BarSpec(80, 40, 62, "#3B82C4", "L stance"),
            BarSpec(170, 40, 26, "#7FB5E4", "L swing"),
            BarSpec(260, 40, 60, "#D35454", "R stance"),
            BarSpec(350, 40, 28, "#E89B9B", "R swing"),
        ],
        summary=[("L stance", "62%"), ("R stance", "60%"), ("asym", "3.3%")],
    ),
    "rom_bar": GraphSpec(
        eyebrow="Kinematics · ROM", title="Range of motion by joint/plane", ds="ds2",
        y_unit="ROM (°)", x_unit="",
        y_ticks=["60", "45", "30", "15", "0"],
        x_ticks=["L sag", "L fro", "R sag", "R fro"],
        bars=[
            BarSpec(80, 40, 110, "#3B82C4", "L sag"),
            BarSpec(170, 40, 35, "#7FB5E4", "L fro"),
            BarSpec(260, 40, 105, "#D35454", "R sag"),
            BarSpec(350, 40, 32, "#E89B9B", "R fro"),
        ],
        summary=[("L sagittal", "38.4°"), ("R sagittal", "36.8°")],
    ),
    "symmetry_radar": GraphSpec(
        eyebrow="Symmetry", title="Symmetry summary (0 = perfect)", ds="ds1",
        y_unit="Asymmetry (%)", x_unit="",
        y_ticks=["10", "7.5", "5", "2.5", "0"],
        x_ticks=["T", "L", "St", "F", "Pk"],
        bars=[
            BarSpec(70, 44, 30, "#F09708", "stride T"),
            BarSpec(150, 44, 56, "#F09708", "stride L"),
            BarSpec(230, 44, 28, "#F09708", "stance"),
            BarSpec(310, 44, 44, "#F09708", "force"),
            BarSpec(385, 44, 36, "#F09708", "peak"),
        ],
        summary=[("avg", "3.9%"), ("max", "stride L · 5.6%")],
    ),
}


# ============================================================
# SVG path → polyline sampler (pure Python, no deps)
# ============================================================

_PATH_TOKENIZER = re.compile(r'[MLCZmlcz]|-?[\d.]+')


def _sample_path(d: str, steps_per_cubic: int = 24) -> np.ndarray:
    """Sample an SVG path (subset: M/L/C, absolute) to an Nx2 ndarray of points."""
    tokens = _PATH_TOKENIZER.findall(d)
    pts: list[tuple[float, float]] = []
    cmd = None
    i = 0
    cx = cy = 0.0

    while i < len(tokens):
        t = tokens[i]
        if t in "MLCZmlcz":
            cmd = t.upper()
            i += 1
            continue

        if cmd == "M":
            x = float(tokens[i]); y = float(tokens[i + 1]); i += 2
            pts.append((x, y)); cx, cy = x, y
            cmd = "L"  # subsequent pairs treated as L per SVG spec
        elif cmd == "L":
            x = float(tokens[i]); y = float(tokens[i + 1]); i += 2
            pts.append((x, y)); cx, cy = x, y
        elif cmd == "C":
            x1 = float(tokens[i]); y1 = float(tokens[i + 1])
            x2 = float(tokens[i + 2]); y2 = float(tokens[i + 3])
            x = float(tokens[i + 4]); y = float(tokens[i + 5])
            i += 6
            for s in range(1, steps_per_cubic + 1):
                u = s / steps_per_cubic
                v = 1 - u
                bx = v**3 * cx + 3*v*v*u * x1 + 3*v*u*u * x2 + u**3 * x
                by = v**3 * cy + 3*v*v*u * y1 + 3*v*u*u * y2 + u**3 * y
                pts.append((bx, by))
            cx, cy = x, y
        elif cmd == "Z":
            # close path — ignored for polyline
            pass
        else:
            i += 1  # unknown token; skip defensively

    return np.asarray(pts, dtype=float) if pts else np.zeros((0, 2))


# ============================================================
# Render core
# ============================================================

# Mockup viewBox convention: 0,0 → 456,210 with plot area x∈[44,448], y∈[20,180].
_VB_X_LO, _VB_X_HI = 44.0, 448.0
_VB_Y_LO, _VB_Y_HI = 20.0, 180.0


def _svg_to_data(xy: np.ndarray, spec: GraphSpec) -> np.ndarray:
    """Map SVG-coord points to data-coord points using first/last ticks as anchors."""
    if xy.size == 0 or not spec.x_ticks or not spec.y_ticks:
        return xy
    try:
        x_data_lo = float(spec.x_ticks[0].replace("−", "-").replace("+", "").replace("T", ""))
    except ValueError:
        x_data_lo = 0.0
    try:
        x_data_hi = float(spec.x_ticks[-1].replace("−", "-").replace("+", "").replace("T", ""))
    except ValueError:
        x_data_hi = 1.0
    try:
        y_data_top = float(spec.y_ticks[0].replace("−", "-").replace("+", ""))
    except ValueError:
        y_data_top = 1.0
    try:
        y_data_bot = float(spec.y_ticks[-1].replace("−", "-").replace("+", ""))
    except ValueError:
        y_data_bot = 0.0

    x_new = x_data_lo + (xy[:, 0] - _VB_X_LO) / (_VB_X_HI - _VB_X_LO) * (x_data_hi - x_data_lo)
    # SVG y grows down, data y grows up → invert
    y_new = y_data_top - (xy[:, 1] - _VB_Y_LO) / (_VB_Y_HI - _VB_Y_LO) * (y_data_top - y_data_bot)
    return np.column_stack([x_new, y_new])


def _compose_rc(preset: Preset) -> dict:
    """Build matplotlib rcParams from a preset."""
    return {
        "font.family": [preset.font] + preset.font_fallback,
        "font.size": preset.body_pt,
        "axes.titlesize": preset.title_pt,
        "axes.labelsize": preset.axis_pt,
        "xtick.labelsize": preset.axis_pt,
        "ytick.labelsize": preset.axis_pt,
        "legend.fontsize": preset.legend_pt,
        "axes.linewidth": 0.6,
        "axes.edgecolor": preset.axis_color,
        "axes.facecolor": preset.bg,
        "figure.facecolor": preset.bg,
        "savefig.facecolor": preset.bg,
        "xtick.color": preset.axis_color,
        "ytick.color": preset.axis_color,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "grid.color": preset.grid_color,
        "grid.linewidth": preset.grid_pt,
        "grid.alpha": 0.7,
        "lines.linewidth": preset.stroke_pt,
        "lines.solid_capstyle": "round",
        "svg.fonttype": "none",        # keep text editable in vector output
        "pdf.fonttype": 42,              # TrueType embedding
        "ps.fonttype": 42,
        "path.simplify": False,
    }


def _remap_color(c: str, preset: Preset, index: int) -> str:
    """When rendering in pub mode, remap mockup palette to preset palette for
    pure-line (non-band, non-box) traces.
    We only swap if mockup color is in our known H-Walker accent map.
    """
    accent_map = {"#3B82C4", "#7FB5E4", "#1E5F9E", "#D35454", "#E89B9B", "#9E3838", "#F09708", "#7FB5E4"}
    if c in accent_map:
        pal = preset.palette_color if len(preset.palette_color) >= 2 else preset.palette
        return pal[index % len(pal)]
    return c


def render(
    template: str,
    preset: str = "ieee",
    variant: str = "col2",       # col1 | col2 | onehalf
    format: str = "svg",         # svg | pdf | eps | png | tiff
    dpi: int | None = None,
    stride_avg: bool = False,
    colorblind_safe: bool | None = None,
    keep_palette: bool = False,  # if True, do not remap to preset palette
    title_override: str | None = None,
) -> tuple[bytes, str]:
    """Render a publication-ready figure for a GRAPH_TPLS key.

    Returns (binary_data, mime_type).
    """
    if preset not in JOURNAL_PRESETS:
        raise ValueError(f"Unknown preset: {preset}")
    P = JOURNAL_PRESETS[preset]

    # stride_avg flips force → force_avg when available
    key = "force_avg" if (stride_avg and template == "force" and "force_avg" in GRAPH_SPECS) else template
    if key not in GRAPH_SPECS:
        raise ValueError(f"Unknown template: {template}")
    spec = GRAPH_SPECS[key]

    if variant == "col1":
        w_mm, h_mm = P.col1
    elif variant == "col2":
        w_mm, h_mm = P.col2
    elif variant == "onehalf" and P.onehalf is not None:
        w_mm, h_mm = P.onehalf
    else:
        w_mm, h_mm = P.col2

    dpi = dpi or P.dpi
    inch_w, inch_h = w_mm / 25.4, h_mm / 25.4

    rc = _compose_rc(P)
    # Colorblind-safe override: swap to Wong palette if requested and not already.
    if colorblind_safe and not P.colorblind_safe:
        wong = ["#000000", "#E69F00", "#56B4E9", "#009E73", "#F0E442",
                "#0072B2", "#D55E00", "#CC79A7"]
        palette = wong
    else:
        palette = P.palette_color if P.palette_color else P.palette

    with mpl.rc_context(rc):
        fig, ax = plt.subplots(figsize=(inch_w, inch_h))

        # Bands (filled mean±SD)
        for i, band in enumerate(spec.bands):
            up = _svg_to_data(_sample_path(band.upper), spec)
            lo = _svg_to_data(_sample_path(band.lower), spec)
            if up.size and lo.size:
                # Align on x
                xs = up[:, 0]
                # Simple interpolation to common x if lengths differ
                if lo.shape[0] != up.shape[0]:
                    lo_y = np.interp(xs, lo[:, 0], lo[:, 1])
                else:
                    lo_y = lo[:, 1]
                color = band.color if keep_palette else palette[i % len(palette)]
                ax.fill_between(xs, up[:, 1], lo_y, color=color, alpha=band.opacity, linewidth=0)

        # H-lines (thresholds)
        for hl in spec.hlines:
            # y is in SVG coords → convert
            data_y = _svg_to_data(np.array([[0, hl.y]]), spec)[0, 1]
            ax.axhline(y=data_y, color=hl.color, linestyle=(0, (3, 3)) if hl.dash else "-",
                       linewidth=P.grid_pt * 2, label=hl.label)

        # Paths (line traces)
        line_idx = 0
        for p in spec.paths:
            xy = _svg_to_data(_sample_path(p.d), spec)
            if xy.size == 0:
                continue
            color = p.color if keep_palette else _remap_color(p.color, P, line_idx)
            kwargs = dict(
                color=color,
                linewidth=P.stroke_pt * (p.width / 1.8),
                label=p.label,
                solid_capstyle="round",
            )
            if p.dash:
                kwargs["linestyle"] = "--"
                kwargs["dashes"] = (2, 1.5)
            else:
                kwargs["linestyle"] = "-"
            ax.plot(xy[:, 0], xy[:, 1], **kwargs)
            line_idx += 1

        # Boxplots
        for i, b in enumerate(spec.boxes):
            # Convert every box coord (x fixed SVG, y→data)
            x_data = float(spec.x_ticks[i]) if i < len(spec.x_ticks) else float(b.x)
            def ymap(yv):
                return _svg_to_data(np.array([[0, yv]]), spec)[0, 1]
            ys = {k: ymap(v) for k, v in [("min", b.min), ("q1", b.q1), ("med", b.med), ("q3", b.q3), ("max", b.max)]}
            color = b.color if keep_palette else palette[i % len(palette)]
            ax.vlines(x=x_data, ymin=min(ys["min"], ys["max"]), ymax=max(ys["min"], ys["max"]),
                      color=color, linewidth=P.stroke_pt)
            lo, hi = sorted([ys["q1"], ys["q3"]])
            ax.add_patch(plt.Rectangle((x_data - 0.35, lo), 0.7, hi - lo,
                                        fill=True, facecolor=color, alpha=0.25,
                                        edgecolor=color, linewidth=P.stroke_pt))
            ax.hlines(y=ys["med"], xmin=x_data - 0.35, xmax=x_data + 0.35,
                      color=color, linewidth=P.stroke_pt * 1.4)

        # Bars
        for i, bar in enumerate(spec.bars):
            x_label = spec.x_ticks[i] if i < len(spec.x_ticks) else str(i)
            # Bar height in mockup is in SVG px from bottom (180)
            # Map h (SVG units, from bottom) to data h
            h_data = _svg_to_data(np.array([[0, 180 - bar.h]]), spec)[0, 1]
            color = bar.color if keep_palette else palette[i % len(palette)]
            ax.bar(x_label, h_data, width=0.6, color=color,
                   edgecolor=P.axis_color, linewidth=P.stroke_pt * 0.5)

        # Axes + grid
        ax.grid(True, which="major", linestyle="-", linewidth=P.grid_pt, color=P.grid_color, alpha=0.7)
        ax.set_axisbelow(True)
        ax.set_xlabel(spec.x_unit)
        ax.set_ylabel(spec.y_unit)
        # Journal convention: figure has NO in-plot title; the caption lives
        # below the figure in the manuscript. Only draw a title when the
        # caller explicitly supplies title_override (non-empty).
        if title_override:
            ax.set_title(title_override, fontsize=P.title_pt)

        # Tick handling: for categorical (e.g., T1…T5), let matplotlib keep categories.
        if spec.x_ticks and not spec.bars:
            try:
                xticks_num = [float(t.replace("−", "-").replace("+", "")) for t in spec.x_ticks]
                ax.set_xticks(xticks_num)
                ax.set_xticklabels(spec.x_ticks)
            except ValueError:
                ax.set_xticks(range(len(spec.x_ticks)))
                ax.set_xticklabels(spec.x_ticks)
        if spec.y_ticks:
            try:
                yticks_num = [float(t.replace("−", "-").replace("+", "")) for t in spec.y_ticks]
                ax.set_yticks(yticks_num)
                ax.set_yticklabels(spec.y_ticks)
            except ValueError:
                pass

        # Ensure exact figure size (no bbox_inches='tight' — would change size)
        fig.set_size_inches(inch_w, inch_h)
        if spec.paths and not spec.bars:
            ax.legend(loc="best", frameon=False, fontsize=P.legend_pt)

        # Export in the requested format.
        return _emit(fig, format, dpi, preset_name=P.name)


def _emit(fig: plt.Figure, fmt: str, dpi: int, preset_name: str = "") -> tuple[bytes, str]:
    buf = io.BytesIO()
    fmt_l = fmt.lower()
    try:
        if fmt_l == "svg":
            fig.savefig(buf, format="svg", dpi=dpi, pad_inches=0.04)
            return buf.getvalue(), "image/svg+xml"
        if fmt_l == "pdf":
            fig.savefig(buf, format="pdf", dpi=dpi, pad_inches=0.04)
            return buf.getvalue(), "application/pdf"
        if fmt_l == "eps":
            fig.savefig(buf, format="eps", dpi=dpi, pad_inches=0.04)
            return buf.getvalue(), "application/postscript"
        if fmt_l == "png":
            fig.savefig(buf, format="png", dpi=dpi, pad_inches=0.04)
            return buf.getvalue(), "image/png"
        if fmt_l == "tiff":
            png_buf = io.BytesIO()
            fig.savefig(png_buf, format="png", dpi=dpi, pad_inches=0.04)
            png_buf.seek(0)
            img = Image.open(png_buf)
            out = io.BytesIO()
            img.save(out, format="TIFF", compression="tiff_lzw", dpi=(dpi, dpi))
            return out.getvalue(), "image/tiff"
        raise ValueError(f"Unsupported format: {fmt}")
    finally:
        plt.close(fig)


@dataclass
class Trace:
    """Numeric trace for real-data publication rendering.

    `kind`:
        "line"        — simple line plot (color, width, dash)
        "band"        — filled mean±SD; needs `y_upper` + `y_lower`
        "bar"         — categorical bar (x is list of labels, y is heights)
        "box"         — single boxplot (x is label, y is list of raw values)
        "scatter"     — points only (color, size)
    """
    kind: str
    name: str
    x: list[float] | list[str]
    y: list[float]
    color: str = "#1f77b4"
    width: float = 1.0
    dash: bool = False
    y_upper: list[float] | None = None
    y_lower: list[float] | None = None
    opacity: float = 1.0


def render_from_traces(
    traces: list[Trace],
    title: str = "",
    x_label: str = "",
    y_label: str = "",
    preset: str = "ieee",
    variant: str = "col2",
    format: str = "svg",
    dpi: int | None = None,
    colorblind_safe: bool | None = None,
    x_range: tuple[float, float] | None = None,
    y_range: tuple[float, float] | None = None,
    legend: bool = True,
) -> tuple[bytes, str]:
    """Render a figure from real numeric traces at exact journal size.

    Uses the same preset machinery (font/stroke/dpi/palette) as `render()`
    but skips the SVG-mockup sampling — traces are already in data coords.
    """
    if preset not in JOURNAL_PRESETS:
        raise ValueError(f"Unknown preset: {preset}")
    P = JOURNAL_PRESETS[preset]

    if variant == "col1":
        w_mm, h_mm = P.col1
    elif variant == "onehalf" and P.onehalf is not None:
        w_mm, h_mm = P.onehalf
    else:
        w_mm, h_mm = P.col2

    dpi_val = dpi or P.dpi
    inch_w, inch_h = w_mm / 25.4, h_mm / 25.4

    rc = _compose_rc(P)
    if colorblind_safe and not P.colorblind_safe:
        palette = ["#000000", "#E69F00", "#56B4E9", "#009E73", "#F0E442",
                   "#0072B2", "#D55E00", "#CC79A7"]
    else:
        palette = P.palette_color if P.palette_color else P.palette

    with mpl.rc_context(rc):
        fig, ax = plt.subplots(figsize=(inch_w, inch_h))

        line_idx = 0
        for tr in traces:
            color = tr.color if tr.color else palette[line_idx % len(palette)]
            if tr.kind == "band":
                if tr.y_upper is None or tr.y_lower is None:
                    continue
                ax.fill_between(
                    tr.x, tr.y_upper, tr.y_lower,
                    color=color, alpha=tr.opacity or 0.2, linewidth=0,
                    label=tr.name if legend else None,
                )
            elif tr.kind == "line":
                kwargs = dict(
                    color=color,
                    linewidth=P.stroke_pt * (tr.width or 1.0),
                    label=tr.name,
                    solid_capstyle="round",
                )
                if tr.dash:
                    kwargs["linestyle"] = "--"
                    kwargs["dashes"] = (3, 2)
                ax.plot(tr.x, tr.y, **kwargs)
                line_idx += 1
            elif tr.kind == "bar":
                ax.bar(
                    tr.x, tr.y, width=0.6, color=color,
                    edgecolor=P.axis_color, linewidth=P.stroke_pt * 0.5,
                    label=tr.name if legend else None,
                )
            elif tr.kind == "box":
                vals = [v for v in tr.y if np.isfinite(v)]
                if vals:
                    ax.boxplot(
                        [vals], positions=[line_idx], widths=0.5,
                        patch_artist=True,
                        boxprops=dict(facecolor=color, alpha=0.25, edgecolor=color,
                                      linewidth=P.stroke_pt),
                        medianprops=dict(color=color, linewidth=P.stroke_pt * 1.4),
                        whiskerprops=dict(color=color, linewidth=P.stroke_pt),
                        capprops=dict(color=color, linewidth=P.stroke_pt),
                        flierprops=dict(marker="o", markersize=2, markerfacecolor=color,
                                        markeredgecolor=color, alpha=0.6),
                    )
                    line_idx += 1
            elif tr.kind == "scatter":
                ax.scatter(tr.x, tr.y, color=color,
                           s=(tr.width or 1.0) * 4, alpha=tr.opacity or 0.8,
                           label=tr.name, edgecolors="none")

        ax.grid(True, which="major", linestyle="-",
                linewidth=P.grid_pt, color=P.grid_color, alpha=0.7)
        ax.set_axisbelow(True)
        if x_label:
            ax.set_xlabel(x_label)
        if y_label:
            ax.set_ylabel(y_label)
        if title:
            ax.set_title(title, fontsize=P.title_pt)
        if x_range is not None:
            ax.set_xlim(*x_range)
        if y_range is not None:
            ax.set_ylim(*y_range)
        if legend and any(tr.kind in ("line", "band", "scatter", "bar") and tr.name
                          for tr in traces):
            ax.legend(loc="best", frameon=False, fontsize=P.legend_pt)

        fig.set_size_inches(inch_w, inch_h)
        return _emit(fig, format, dpi_val, preset_name=P.name)


def list_templates() -> list[str]:
    return sorted(GRAPH_SPECS.keys())


def list_presets() -> list[dict]:
    return [
        {
            "key": k,
            "name": p.name,
            "full": p.full,
            "col1_mm": list(p.col1),
            "col2_mm": list(p.col2),
            "onehalf_mm": list(p.onehalf) if p.onehalf else None,
            "font": p.font,
            "body_pt": p.body_pt,
            "dpi": p.dpi,
            "formats": p.formats,
            "colorblind_safe": p.colorblind_safe,
            "notes": p.notes,
        }
        for k, p in JOURNAL_PRESETS.items()
    ]
