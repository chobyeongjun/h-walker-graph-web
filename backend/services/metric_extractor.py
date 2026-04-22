"""
Phase 3 · Metric extractor.

Maps a metric key (e.g. "peak_force_L", "cadence", "stride_time_cv")
to a list of float values extracted from a dataset's analysis result.

Used by /api/stats to support cross-file statistical tests:
  - For paired / Welch t-tests: one value per dataset per side (→ arrays
    aligned for pairing).
  - For ANOVA / Kruskal: multiple datasets per group, each contributing
    one value; groups are lists of dataset ids.
  - For `per_stride` style metrics, the extractor can return full per-
    stride arrays so within-subject variability can be compared.

New metrics are added to METRIC_EXTRACTORS — keep the keys stable
because frontend StatCell + Claude tool schema reference them.
"""
from __future__ import annotations

from typing import Any, Callable

import numpy as np

from tools.auto_analyzer.analyzer import AnalysisResult


MetricFn = Callable[[AnalysisResult], list[float]]


# ============================================================
# Scalar (one value per dataset — for between-subject comparisons)
# ============================================================


def _scalar_or_empty(v: float) -> list[float]:
    return [float(v)] if np.isfinite(v) else []


def peak_force_L(res: AnalysisResult) -> list[float]:
    lfp = res.left_force_profile
    if lfp.mean is None:
        return []
    return _scalar_or_empty(float(np.max(lfp.mean)))


def peak_force_R(res: AnalysisResult) -> list[float]:
    rfp = res.right_force_profile
    if rfp.mean is None:
        return []
    return _scalar_or_empty(float(np.max(rfp.mean)))


def cadence_L(res: AnalysisResult) -> list[float]:
    return _scalar_or_empty(res.left_stride.cadence)


def cadence_R(res: AnalysisResult) -> list[float]:
    return _scalar_or_empty(res.right_stride.cadence)


def stride_time_mean_L(res: AnalysisResult) -> list[float]:
    return _scalar_or_empty(res.left_stride.stride_time_mean)


def stride_time_mean_R(res: AnalysisResult) -> list[float]:
    return _scalar_or_empty(res.right_stride.stride_time_mean)


def stride_time_cv_L(res: AnalysisResult) -> list[float]:
    return _scalar_or_empty(res.left_stride.stride_time_cv)


def stride_time_cv_R(res: AnalysisResult) -> list[float]:
    return _scalar_or_empty(res.right_stride.stride_time_cv)


def stride_length_mean_L(res: AnalysisResult) -> list[float]:
    return _scalar_or_empty(res.left_stride.stride_length_mean)


def stride_length_mean_R(res: AnalysisResult) -> list[float]:
    return _scalar_or_empty(res.right_stride.stride_length_mean)


def stance_pct_L(res: AnalysisResult) -> list[float]:
    return _scalar_or_empty(res.left_stride.stance_pct_mean)


def stance_pct_R(res: AnalysisResult) -> list[float]:
    return _scalar_or_empty(res.right_stride.stance_pct_mean)


def force_rmse_L(res: AnalysisResult) -> list[float]:
    return _scalar_or_empty(res.left_force_tracking.rmse)


def force_rmse_R(res: AnalysisResult) -> list[float]:
    return _scalar_or_empty(res.right_force_tracking.rmse)


def symmetry_stride_time(res: AnalysisResult) -> list[float]:
    return _scalar_or_empty(res.stride_time_symmetry)


def symmetry_stride_length(res: AnalysisResult) -> list[float]:
    return _scalar_or_empty(res.stride_length_symmetry)


def symmetry_force(res: AnalysisResult) -> list[float]:
    return _scalar_or_empty(res.force_symmetry)


def symmetry_stance(res: AnalysisResult) -> list[float]:
    return _scalar_or_empty(res.stance_symmetry)


def fatigue_L(res: AnalysisResult) -> list[float]:
    return _scalar_or_empty(res.left_fatigue)


def fatigue_R(res: AnalysisResult) -> list[float]:
    return _scalar_or_empty(res.right_fatigue)


def foot_pitch_rom_L(res: AnalysisResult) -> list[float]:
    return _scalar_or_empty(res.left_kinematics.rom)


def foot_pitch_rom_R(res: AnalysisResult) -> list[float]:
    return _scalar_or_empty(res.right_kinematics.rom)


def foot_pitch_max_L(res: AnalysisResult) -> list[float]:
    return _scalar_or_empty(res.left_kinematics.peak_max)


def foot_pitch_max_R(res: AnalysisResult) -> list[float]:
    return _scalar_or_empty(res.right_kinematics.peak_max)


def foot_pitch_min_L(res: AnalysisResult) -> list[float]:
    return _scalar_or_empty(res.left_kinematics.peak_min)


def foot_pitch_min_R(res: AnalysisResult) -> list[float]:
    return _scalar_or_empty(res.right_kinematics.peak_min)


def force_bias_L(res: AnalysisResult) -> list[float]:
    return _scalar_or_empty(res.left_force_tracking.bias)


def force_bias_R(res: AnalysisResult) -> list[float]:
    return _scalar_or_empty(res.right_force_tracking.bias)


# ============================================================
# Array (full per-stride vector — for within-subject variability tests)
# ============================================================


def stride_times_L(res: AnalysisResult) -> list[float]:
    return [float(v) for v in res.left_stride.stride_times if np.isfinite(v)]


def stride_times_R(res: AnalysisResult) -> list[float]:
    return [float(v) for v in res.right_stride.stride_times if np.isfinite(v)]


def stride_lengths_L(res: AnalysisResult) -> list[float]:
    return [float(v) for v in res.left_stride.stride_lengths if np.isfinite(v)]


def stride_lengths_R(res: AnalysisResult) -> list[float]:
    return [float(v) for v in res.right_stride.stride_lengths if np.isfinite(v)]


def peaks_per_stride_L(res: AnalysisResult) -> list[float]:
    lfp = res.left_force_profile
    if lfp.individual is None:
        return []
    return [float(v) for v in lfp.individual.max(axis=1) if np.isfinite(v)]


def peaks_per_stride_R(res: AnalysisResult) -> list[float]:
    rfp = res.right_force_profile
    if rfp.individual is None:
        return []
    return [float(v) for v in rfp.individual.max(axis=1) if np.isfinite(v)]


def force_rmse_per_stride_L(res: AnalysisResult) -> list[float]:
    arr = res.left_force_tracking.rmse_per_stride
    return [float(v) for v in arr if np.isfinite(v)]


def force_rmse_per_stride_R(res: AnalysisResult) -> list[float]:
    arr = res.right_force_tracking.rmse_per_stride
    return [float(v) for v in arr if np.isfinite(v)]


# ============================================================
# Registry
# ============================================================


METRIC_EXTRACTORS: dict[str, MetricFn] = {
    # Scalar — one value per dataset
    "peak_force_L":        peak_force_L,
    "peak_force_R":        peak_force_R,
    "cadence_L":           cadence_L,
    "cadence_R":           cadence_R,
    "stride_time_mean_L":  stride_time_mean_L,
    "stride_time_mean_R":  stride_time_mean_R,
    "stride_time_cv_L":    stride_time_cv_L,
    "stride_time_cv_R":    stride_time_cv_R,
    "stride_length_mean_L": stride_length_mean_L,
    "stride_length_mean_R": stride_length_mean_R,
    "stance_pct_L":        stance_pct_L,
    "stance_pct_R":        stance_pct_R,
    "force_rmse_L":        force_rmse_L,
    "force_rmse_R":        force_rmse_R,
    "symmetry_stride_time":   symmetry_stride_time,
    "symmetry_stride_length": symmetry_stride_length,
    "symmetry_force":         symmetry_force,
    "symmetry_stance":        symmetry_stance,
    "fatigue_L":           fatigue_L,
    "fatigue_R":           fatigue_R,
    "foot_pitch_rom_L":    foot_pitch_rom_L,
    "foot_pitch_rom_R":    foot_pitch_rom_R,
    "foot_pitch_max_L":    foot_pitch_max_L,
    "foot_pitch_max_R":    foot_pitch_max_R,
    "foot_pitch_min_L":    foot_pitch_min_L,
    "foot_pitch_min_R":    foot_pitch_min_R,
    "force_bias_L":        force_bias_L,
    "force_bias_R":        force_bias_R,
    # Array — per-stride vectors
    "stride_times_L":           stride_times_L,
    "stride_times_R":           stride_times_R,
    "stride_lengths_L":         stride_lengths_L,
    "stride_lengths_R":         stride_lengths_R,
    "peaks_per_stride_L":       peaks_per_stride_L,
    "peaks_per_stride_R":       peaks_per_stride_R,
    "force_rmse_per_stride_L":  force_rmse_per_stride_L,
    "force_rmse_per_stride_R":  force_rmse_per_stride_R,
}


def describe_metric(key: str) -> dict[str, Any]:
    """Return metadata for a metric key — used by the frontend to
    render the picker dropdown with human-readable labels."""
    labels = {
        "peak_force_L":            {"label": "Peak force · L",           "unit": "N",  "side": "L", "kind": "kinetic"},
        "peak_force_R":            {"label": "Peak force · R",           "unit": "N",  "side": "R", "kind": "kinetic"},
        "cadence_L":               {"label": "Cadence · L",              "unit": "spm", "side": "L", "kind": "temporal"},
        "cadence_R":               {"label": "Cadence · R",              "unit": "spm", "side": "R", "kind": "temporal"},
        "stride_time_mean_L":      {"label": "Stride time mean · L",     "unit": "s",   "side": "L", "kind": "temporal"},
        "stride_time_mean_R":      {"label": "Stride time mean · R",     "unit": "s",   "side": "R", "kind": "temporal"},
        "stride_time_cv_L":        {"label": "Stride time CV · L",       "unit": "%",   "side": "L", "kind": "temporal"},
        "stride_time_cv_R":        {"label": "Stride time CV · R",       "unit": "%",   "side": "R", "kind": "temporal"},
        "stride_length_mean_L":    {"label": "Stride length · L",        "unit": "m",   "side": "L", "kind": "spatial"},
        "stride_length_mean_R":    {"label": "Stride length · R",        "unit": "m",   "side": "R", "kind": "spatial"},
        "stance_pct_L":            {"label": "Stance % · L",             "unit": "%",   "side": "L", "kind": "temporal"},
        "stance_pct_R":            {"label": "Stance % · R",             "unit": "%",   "side": "R", "kind": "temporal"},
        "force_rmse_L":            {"label": "Force tracking RMSE · L",  "unit": "N",   "side": "L", "kind": "control"},
        "force_rmse_R":            {"label": "Force tracking RMSE · R",  "unit": "N",   "side": "R", "kind": "control"},
        "symmetry_stride_time":    {"label": "Symmetry · stride time",   "unit": "%",   "side": "-", "kind": "symmetry"},
        "symmetry_stride_length":  {"label": "Symmetry · stride length", "unit": "%",   "side": "-", "kind": "symmetry"},
        "symmetry_force":          {"label": "Symmetry · force",         "unit": "%",   "side": "-", "kind": "symmetry"},
        "symmetry_stance":         {"label": "Symmetry · stance",        "unit": "%",   "side": "-", "kind": "symmetry"},
        "fatigue_L":               {"label": "Fatigue · L",              "unit": "%",   "side": "L", "kind": "temporal"},
        "fatigue_R":               {"label": "Fatigue · R",              "unit": "%",   "side": "R", "kind": "temporal"},
        "foot_pitch_rom_L":        {"label": "Foot Pitch ROM · L",       "unit": "°",   "side": "L", "kind": "kinematic"},
        "foot_pitch_rom_R":        {"label": "Foot Pitch ROM · R",       "unit": "°",   "side": "R", "kind": "kinematic"},
        "foot_pitch_max_L":        {"label": "Foot Pitch Max · L",       "unit": "°",   "side": "L", "kind": "kinematic"},
        "foot_pitch_max_R":        {"label": "Foot Pitch Max · R",       "unit": "°",   "side": "R", "kind": "kinematic"},
        "foot_pitch_min_L":        {"label": "Foot Pitch Min · L",       "unit": "°",   "side": "L", "kind": "kinematic"},
        "foot_pitch_min_R":        {"label": "Foot Pitch Min · R",       "unit": "°",   "side": "R", "kind": "kinematic"},
        "force_bias_L":            {"label": "Force Bias · L",           "unit": "N",   "side": "L", "kind": "control"},
        "force_bias_R":            {"label": "Force Bias · R",           "unit": "N",   "side": "R", "kind": "control"},
        "stride_times_L":          {"label": "Stride times (all) · L",   "unit": "s",   "side": "L", "kind": "array"},
        "stride_times_R":          {"label": "Stride times (all) · R",   "unit": "s",   "side": "R", "kind": "array"},
        "stride_lengths_L":        {"label": "Stride lengths (all) · L", "unit": "m",   "side": "L", "kind": "array"},
        "stride_lengths_R":        {"label": "Stride lengths (all) · R", "unit": "m",   "side": "R", "kind": "array"},
        "peaks_per_stride_L":      {"label": "Peak force per stride · L", "unit": "N",  "side": "L", "kind": "array"},
        "peaks_per_stride_R":      {"label": "Peak force per stride · R", "unit": "N",  "side": "R", "kind": "array"},
        "force_rmse_per_stride_L": {"label": "Force RMSE per stride · L", "unit": "N",  "side": "L", "kind": "array"},
        "force_rmse_per_stride_R": {"label": "Force RMSE per stride · R", "unit": "N",  "side": "R", "kind": "array"},
    }
    meta = labels.get(key)
    if not meta:
        return {"label": key, "unit": "?", "side": "-", "kind": "unknown"}
    return {"key": key, **meta}


def extract(key: str, res: AnalysisResult) -> list[float]:
    if key not in METRIC_EXTRACTORS:
        raise ValueError(f"unknown metric '{key}'")
    return METRIC_EXTRACTORS[key](res)
