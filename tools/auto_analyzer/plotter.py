"""
H-Walker Auto Analyzer — Publication-quality graph generation.
All graphs use matplotlib with Agg backend (headless).
"""

import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

from .styles import apply_style, FILE_COLORS, SIDE_COLORS, TRACK_COLORS
from .analyzer import AnalysisResult, ForceProfileResult


def _save(fig, output_dir: str, name: str, dpi: int = 300):
    """Save figure and close."""
    path = os.path.join(output_dir, name)
    fig.savefig(path, dpi=dpi, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return path


# ================================================================
# FORCE PLOTS
# ================================================================

def plot_force_mean_sd(result: AnalysisResult, style: dict,
                       output_dir: str) -> list[str]:
    """Plot mean +/- SD force profiles (Des vs Act) for L and R."""
    saved = []
    gcp_x = np.linspace(0, 100, 101)

    for side, fp_attr, label in [
        ('L', 'left_force_profile', 'Left'),
        ('R', 'right_force_profile', 'Right'),
    ]:
        fp: ForceProfileResult = getattr(result, fp_attr)
        if fp.mean is None:
            continue

        fig, ax = plt.subplots(figsize=style['figsize'])

        # Desired force
        if fp.des_mean is not None:
            ax.plot(gcp_x, fp.des_mean, color=TRACK_COLORS['des'],
                    linewidth=style['line_width'], label='Desired', linestyle='--')
            if fp.des_std is not None:
                ax.fill_between(gcp_x,
                                fp.des_mean - fp.des_std,
                                fp.des_mean + fp.des_std,
                                color=TRACK_COLORS['des'], alpha=style['fill_alpha'])

        # Actual force
        ax.plot(gcp_x, fp.mean, color=SIDE_COLORS[side],
                linewidth=style['line_width'], label='Actual')
        if fp.std is not None:
            ax.fill_between(gcp_x,
                            fp.mean - fp.std,
                            fp.mean + fp.std,
                            color=SIDE_COLORS[side], alpha=style['fill_alpha'])

        ax.set_xlabel('Gait Cycle (%)')
        ax.set_ylabel('Force (N)')
        ax.set_title(f'{label} Cable Force — Mean ± SD')
        ax.legend(loc='upper right')
        ax.set_xlim(0, 100)

        saved.append(_save(fig, output_dir, f'force_mean_sd_{side}.png', style['dpi']))

    return saved


def plot_force_individual_strides(result: AnalysisResult, style: dict,
                                   output_dir: str, max_strides: int = 50) -> list[str]:
    """Plot individual stride force overlays."""
    saved = []
    gcp_x = np.linspace(0, 100, 101)

    for side, fp_attr, label in [
        ('L', 'left_force_profile', 'Left'),
        ('R', 'right_force_profile', 'Right'),
    ]:
        fp: ForceProfileResult = getattr(result, fp_attr)
        if fp.individual is None:
            continue

        fig, ax = plt.subplots(figsize=style['figsize'])
        n = min(len(fp.individual), max_strides)

        for i in range(n):
            ax.plot(gcp_x, fp.individual[i], color=SIDE_COLORS[side],
                    alpha=0.15, linewidth=0.5)

        # Mean on top
        if fp.mean is not None:
            ax.plot(gcp_x, fp.mean, color='black',
                    linewidth=style['line_width'] * 1.2, label=f'Mean (n={len(fp.individual)})')

        ax.set_xlabel('Gait Cycle (%)')
        ax.set_ylabel('Force (N)')
        ax.set_title(f'{label} Cable Force — Individual Strides')
        ax.legend(loc='upper right')
        ax.set_xlim(0, 100)

        saved.append(_save(fig, output_dir, f'force_individual_{side}.png', style['dpi']))

    return saved


def plot_force_tracking_error(result: AnalysisResult, style: dict,
                               output_dir: str) -> list[str]:
    """Plot force tracking RMSE per stride."""
    saved = []

    for side, ft_attr, label in [
        ('L', 'left_force_tracking', 'Left'),
        ('R', 'right_force_tracking', 'Right'),
    ]:
        ft = getattr(result, ft_attr)
        if len(ft.rmse_per_stride) == 0:
            continue

        fig, ax = plt.subplots(figsize=style['figsize'])
        x = np.arange(1, len(ft.rmse_per_stride) + 1)

        ax.scatter(x, ft.rmse_per_stride, s=style['marker_size']**2,
                   color=SIDE_COLORS[side], alpha=0.6, label='RMSE')
        ax.axhline(y=ft.rmse, color='red', linestyle='--',
                   linewidth=0.8, label=f'Overall RMSE={ft.rmse:.2f} N')

        # Trend line
        if len(x) > 3:
            z = np.polyfit(x, ft.rmse_per_stride, 1)
            ax.plot(x, np.polyval(z, x), color='gray', linestyle=':',
                    linewidth=0.8, label='Trend')

        ax.set_xlabel('Stride Number')
        ax.set_ylabel('RMSE (N)')
        ax.set_title(f'{label} Force Tracking Error')
        ax.legend(loc='upper right')
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))

        saved.append(_save(fig, output_dir, f'force_tracking_{side}.png', style['dpi']))

    return saved


def plot_force_lr_comparison(result: AnalysisResult, style: dict,
                              output_dir: str) -> list[str]:
    """Plot L vs R mean force profiles on same axes."""
    lfp = result.left_force_profile
    rfp = result.right_force_profile
    if lfp.mean is None and rfp.mean is None:
        return []

    gcp_x = np.linspace(0, 100, 101)
    fig, ax = plt.subplots(figsize=style['figsize'])

    if lfp.mean is not None:
        ax.plot(gcp_x, lfp.mean, color=SIDE_COLORS['L'],
                linewidth=style['line_width'], label='Left')
        if lfp.std is not None:
            ax.fill_between(gcp_x, lfp.mean - lfp.std, lfp.mean + lfp.std,
                            color=SIDE_COLORS['L'], alpha=style['fill_alpha'])

    if rfp.mean is not None:
        ax.plot(gcp_x, rfp.mean, color=SIDE_COLORS['R'],
                linewidth=style['line_width'], label='Right')
        if rfp.std is not None:
            ax.fill_between(gcp_x, rfp.mean - rfp.std, rfp.mean + rfp.std,
                            color=SIDE_COLORS['R'], alpha=style['fill_alpha'])

    ax.set_xlabel('Gait Cycle (%)')
    ax.set_ylabel('Force (N)')
    ax.set_title('Left vs Right Cable Force')
    ax.legend(loc='upper right')
    ax.set_xlim(0, 100)

    return [_save(fig, output_dir, 'force_lr_comparison.png', style['dpi'])]


# ================================================================
# GAIT PARAMETER PLOTS
# ================================================================

def plot_stride_time_trend(result: AnalysisResult, style: dict,
                            output_dir: str) -> list[str]:
    """Plot stride time over stride number with trend line."""
    fig, ax = plt.subplots(figsize=style['figsize'])
    has_data = False

    for side, sr_attr, label in [
        ('L', 'left_stride', 'Left'),
        ('R', 'right_stride', 'Right'),
    ]:
        sr = getattr(result, sr_attr)
        if len(sr.stride_times) == 0:
            continue
        has_data = True

        x = np.arange(1, len(sr.stride_times) + 1)
        ax.scatter(x, sr.stride_times, s=style['marker_size']**2,
                   color=SIDE_COLORS[side], alpha=0.5, label=f'{label} ({sr.stride_time_mean:.3f}±{sr.stride_time_std:.3f}s)')

        # Trend line
        if len(x) > 3:
            z = np.polyfit(x, sr.stride_times, 1)
            ax.plot(x, np.polyval(z, x), color=SIDE_COLORS[side],
                    linestyle='--', linewidth=0.8)

    if not has_data:
        plt.close(fig)
        return []

    ax.set_xlabel('Stride Number')
    ax.set_ylabel('Stride Time (s)')
    ax.set_title('Stride Time Trend')
    ax.legend(loc='upper right')
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))

    return [_save(fig, output_dir, 'stride_time_trend.png', style['dpi'])]


def plot_stride_length_trend(result: AnalysisResult, style: dict,
                              output_dir: str) -> list[str]:
    """Plot stride length over stride number."""
    fig, ax = plt.subplots(figsize=style['figsize'])
    has_data = False

    for side, sr_attr, label in [
        ('L', 'left_stride', 'Left'),
        ('R', 'right_stride', 'Right'),
    ]:
        sr = getattr(result, sr_attr)
        valid = sr.stride_lengths[np.isfinite(sr.stride_lengths)] if len(sr.stride_lengths) > 0 else np.array([])
        if len(valid) == 0:
            continue
        has_data = True

        x = np.arange(1, len(valid) + 1)
        ax.scatter(x, valid, s=style['marker_size']**2,
                   color=SIDE_COLORS[side], alpha=0.5,
                   label=f'{label} ({sr.stride_length_mean:.3f}±{sr.stride_length_std:.3f}m)')

        if len(x) > 3:
            z = np.polyfit(x, valid, 1)
            ax.plot(x, np.polyval(z, x), color=SIDE_COLORS[side],
                    linestyle='--', linewidth=0.8)

    if not has_data:
        plt.close(fig)
        return []

    ax.set_xlabel('Stride Number')
    ax.set_ylabel('Stride Length (m)')
    ax.set_title('Stride Length Trend (ZUPT)')
    ax.legend(loc='upper right')
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))

    return [_save(fig, output_dir, 'stride_length_trend.png', style['dpi'])]


def plot_gait_summary(result: AnalysisResult, style: dict,
                       output_dir: str) -> list[str]:
    """Bar chart summarizing key gait parameters (L vs R)."""
    ls, rs = result.left_stride, result.right_stride

    labels = ['Stride Time (s)', 'Cadence (steps/min)', 'Stance (%)', 'Stride Length (m)']
    left_vals = [ls.stride_time_mean, ls.cadence, ls.stance_pct_mean, ls.stride_length_mean]
    right_vals = [rs.stride_time_mean, rs.cadence, rs.stance_pct_mean, rs.stride_length_mean]
    left_err = [ls.stride_time_std, 0, ls.stance_pct_std, ls.stride_length_std]
    right_err = [rs.stride_time_std, 0, rs.stance_pct_std, rs.stride_length_std]

    # Filter out zero-only pairs
    keep = [i for i in range(len(labels)) if left_vals[i] > 0 or right_vals[i] > 0]
    if not keep:
        return []

    labels = [labels[i] for i in keep]
    left_vals = [left_vals[i] for i in keep]
    right_vals = [right_vals[i] for i in keep]
    left_err = [left_err[i] for i in keep]
    right_err = [right_err[i] for i in keep]

    fig, axes = plt.subplots(1, len(labels), figsize=(style['figsize'][0] * 1.5,
                                                       style['figsize'][1]))
    if len(labels) == 1:
        axes = [axes]

    for ax, label, lv, rv, le, re in zip(axes, labels, left_vals, right_vals, left_err, right_err):
        x = np.array([0, 1])
        bars = ax.bar(x, [lv, rv], yerr=[le, re], width=0.5,
                      color=[SIDE_COLORS['L'], SIDE_COLORS['R']],
                      capsize=4, error_kw={'linewidth': 0.8})
        ax.set_xticks(x)
        ax.set_xticklabels(['Left', 'Right'])
        ax.set_title(label, fontsize=style['label_size'])

        # Value labels on bars
        for bar, val in zip(bars, [lv, rv]):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                        f'{val:.2f}', ha='center', va='bottom',
                        fontsize=style['tick_size'])

    fig.suptitle('Gait Parameters Summary', fontsize=style['title_size'])
    fig.tight_layout()

    return [_save(fig, output_dir, 'gait_summary.png', style['dpi'])]


def plot_stride_time_histogram(result: AnalysisResult, style: dict,
                                output_dir: str) -> list[str]:
    """Histogram of stride times."""
    fig, ax = plt.subplots(figsize=style['figsize'])
    has_data = False

    for side, sr_attr, label in [
        ('L', 'left_stride', 'Left'),
        ('R', 'right_stride', 'Right'),
    ]:
        sr = getattr(result, sr_attr)
        if len(sr.stride_times) == 0:
            continue
        has_data = True

        ax.hist(sr.stride_times, bins='auto', color=SIDE_COLORS[side],
                alpha=0.5, label=f'{label} (n={sr.n_strides})', edgecolor='black',
                linewidth=0.3)

    if not has_data:
        plt.close(fig)
        return []

    ax.set_xlabel('Stride Time (s)')
    ax.set_ylabel('Count')
    ax.set_title('Stride Time Distribution')
    ax.legend(loc='upper right')

    return [_save(fig, output_dir, 'stride_time_histogram.png', style['dpi'])]


def plot_symmetry(result: AnalysisResult, style: dict,
                   output_dir: str) -> list[str]:
    """Bar chart of symmetry indices."""
    labels = []
    values = []

    for name, val in [
        ('Stride Time', result.stride_time_symmetry),
        ('Stride Length', result.stride_length_symmetry),
        ('Force (RMSE)', result.force_symmetry),
        ('Stance %', result.stance_symmetry),
    ]:
        if val > 0 or name == 'Stride Time':
            labels.append(name)
            values.append(val)

    if not labels:
        return []

    fig, ax = plt.subplots(figsize=style['figsize'])
    x = np.arange(len(labels))
    colors = ['#4C9EFF' if v < 10 else '#FB923C' if v < 20 else '#F87171' for v in values]
    bars = ax.bar(x, values, color=colors, width=0.5, edgecolor='black', linewidth=0.3)

    # Reference lines
    ax.axhline(y=10, color='orange', linestyle='--', linewidth=0.8, alpha=0.7, label='Mild asymmetry (10%)')
    ax.axhline(y=20, color='red', linestyle='--', linewidth=0.8, alpha=0.7, label='Significant asymmetry (20%)')

    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                f'{val:.1f}%', ha='center', va='bottom', fontsize=style['tick_size'])

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel('Symmetry Index (%)')
    ax.set_title('Gait Symmetry (0% = perfect)')
    ax.legend(loc='upper right', fontsize=style['legend_size'])

    return [_save(fig, output_dir, 'symmetry_index.png', style['dpi'])]


# ================================================================
# COMPARISON PLOTS (multi-file)
# ================================================================

def plot_force_comparison(results: list[AnalysisResult], style: dict,
                           output_dir: str) -> list[str]:
    """Subplots comparing mean force profiles across files."""
    saved = []

    for side, fp_attr, label in [
        ('L', 'left_force_profile', 'Left'),
        ('R', 'right_force_profile', 'Right'),
    ]:
        profiles = [(r.filename, getattr(r, fp_attr)) for r in results
                     if getattr(r, fp_attr).mean is not None]
        if not profiles:
            continue

        gcp_x = np.linspace(0, 100, 101)
        n = len(profiles)
        fig, axes = plt.subplots(1, n, figsize=(style['figsize'][0] * n * 0.6,
                                                  style['figsize'][1]),
                                  sharey=True)
        if n == 1:
            axes = [axes]

        for ax, (fname, fp), color in zip(axes, profiles, FILE_COLORS):
            ax.plot(gcp_x, fp.mean, color=color, linewidth=style['line_width'])
            if fp.std is not None:
                ax.fill_between(gcp_x, fp.mean - fp.std, fp.mean + fp.std,
                                color=color, alpha=style['fill_alpha'])
            ax.set_title(fname, fontsize=style['tick_size'])
            ax.set_xlabel('GC (%)')
            ax.set_xlim(0, 100)

        axes[0].set_ylabel('Force (N)')
        fig.suptitle(f'{label} Force Comparison', fontsize=style['title_size'])
        fig.tight_layout()
        saved.append(_save(fig, output_dir, f'force_comparison_{side}.png', style['dpi']))

    return saved


def plot_force_comparison_overlay(results: list[AnalysisResult], style: dict,
                                   output_dir: str) -> list[str]:
    """Overlay mean force profiles from all files on same axes."""
    saved = []
    gcp_x = np.linspace(0, 100, 101)

    for side, fp_attr, label in [
        ('L', 'left_force_profile', 'Left'),
        ('R', 'right_force_profile', 'Right'),
    ]:
        profiles = [(r.filename, getattr(r, fp_attr)) for r in results
                     if getattr(r, fp_attr).mean is not None]
        if not profiles:
            continue

        fig, ax = plt.subplots(figsize=style['figsize'])

        for (fname, fp), color in zip(profiles, FILE_COLORS):
            ax.plot(gcp_x, fp.mean, color=color, linewidth=style['line_width'], label=fname)
            if fp.std is not None:
                ax.fill_between(gcp_x, fp.mean - fp.std, fp.mean + fp.std,
                                color=color, alpha=style['fill_alpha'] * 0.5)

        ax.set_xlabel('Gait Cycle (%)')
        ax.set_ylabel('Force (N)')
        ax.set_title(f'{label} Force — Multi-File Overlay')
        ax.legend(loc='upper right')
        ax.set_xlim(0, 100)
        saved.append(_save(fig, output_dir, f'force_overlay_{side}.png', style['dpi']))

    return saved


def plot_stats_comparison(results: list[AnalysisResult], style: dict,
                           output_dir: str) -> list[str]:
    """Bar chart comparing key stats across files."""
    if len(results) < 2:
        return []

    metrics = [
        ('L Stride Time (s)', lambda r: r.left_stride.stride_time_mean),
        ('R Stride Time (s)', lambda r: r.right_stride.stride_time_mean),
        ('L Cadence', lambda r: r.left_stride.cadence),
        ('R Cadence', lambda r: r.right_stride.cadence),
        ('L Force RMSE (N)', lambda r: r.left_force_tracking.rmse),
        ('R Force RMSE (N)', lambda r: r.right_force_tracking.rmse),
    ]

    # Filter to metrics that have non-zero values
    metrics = [(name, fn) for name, fn in metrics
               if any(fn(r) > 0 for r in results)]

    if not metrics:
        return []

    fig, ax = plt.subplots(figsize=style['figsize_wide'])
    n_metrics = len(metrics)
    n_files = len(results)
    width = 0.8 / n_files
    x = np.arange(n_metrics)

    for i, r in enumerate(results):
        vals = [fn(r) for _, fn in metrics]
        offset = (i - n_files / 2 + 0.5) * width
        ax.bar(x + offset, vals, width=width, label=r.filename,
               color=FILE_COLORS[i % len(FILE_COLORS)])

    ax.set_xticks(x)
    ax.set_xticklabels([name for name, _ in metrics], rotation=30, ha='right')
    ax.set_title('Cross-File Comparison')
    ax.legend(loc='upper right')
    fig.tight_layout()

    return [_save(fig, output_dir, 'stats_comparison.png', style['dpi'])]


# ================================================================
# MAIN ENTRY
# ================================================================

def generate_all_plots(results: list[AnalysisResult], style_name: str,
                        output_dir: str) -> list[str]:
    """Generate all applicable plots. Returns list of saved file paths."""
    plots_dir = os.path.join(output_dir, 'plots')
    os.makedirs(plots_dir, exist_ok=True)

    style = apply_style(style_name)
    saved = []

    # Single-file plots for each result
    for r in results:
        prefix = os.path.splitext(r.filename)[0]
        file_dir = plots_dir if len(results) == 1 else os.path.join(plots_dir, prefix)
        os.makedirs(file_dir, exist_ok=True)

        saved.extend(plot_force_mean_sd(r, style, file_dir))
        saved.extend(plot_force_individual_strides(r, style, file_dir))
        saved.extend(plot_force_tracking_error(r, style, file_dir))
        saved.extend(plot_force_lr_comparison(r, style, file_dir))
        saved.extend(plot_stride_time_trend(r, style, file_dir))
        saved.extend(plot_stride_length_trend(r, style, file_dir))
        saved.extend(plot_gait_summary(r, style, file_dir))
        saved.extend(plot_stride_time_histogram(r, style, file_dir))
        saved.extend(plot_symmetry(r, style, file_dir))

    # Multi-file comparison plots
    if len(results) >= 2:
        comp_dir = os.path.join(plots_dir, '_comparison')
        os.makedirs(comp_dir, exist_ok=True)
        saved.extend(plot_force_comparison(results, style, comp_dir))
        saved.extend(plot_force_comparison_overlay(results, style, comp_dir))
        saved.extend(plot_stats_comparison(results, style, comp_dir))

    return saved
