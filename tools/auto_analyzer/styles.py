"""
Journal style presets for publication-quality graphs.
"""

import matplotlib as mpl

STYLES = {
    'default': {
        'figsize': (8, 5),
        'figsize_wide': (12, 5),
        'figsize_multi': (12, 8),
        'dpi': 300,
        'font_family': 'Arial',
        'font_size': 11,
        'title_size': 13,
        'label_size': 11,
        'tick_size': 9,
        'legend_size': 9,
        'line_width': 1.5,
        'marker_size': 4,
        'grid': True,
        'grid_alpha': 0.3,
        'fill_alpha': 0.25,
        'spine_width': 1.0,
    },
    'ieee': {
        'figsize': (3.5, 2.5),
        'figsize_wide': (7.16, 2.5),
        'figsize_multi': (7.16, 5.0),
        'dpi': 600,
        'font_family': 'Times New Roman',
        'font_size': 8,
        'title_size': 9,
        'label_size': 8,
        'tick_size': 7,
        'legend_size': 7,
        'line_width': 1.0,
        'marker_size': 3,
        'grid': True,
        'grid_alpha': 0.2,
        'fill_alpha': 0.2,
        'spine_width': 0.5,
    },
    'nature': {
        'figsize': (89 / 25.4, 60 / 25.4),
        'figsize_wide': (183 / 25.4, 60 / 25.4),
        'figsize_multi': (183 / 25.4, 120 / 25.4),
        'dpi': 300,
        'font_family': 'Arial',
        'font_size': 7,
        'title_size': 8,
        'label_size': 7,
        'tick_size': 6,
        'legend_size': 6,
        'line_width': 1.0,
        'marker_size': 2.5,
        'grid': False,
        'grid_alpha': 0.15,
        'fill_alpha': 0.2,
        'spine_width': 0.5,
    },
    'elsevier': {
        'figsize': (90 / 25.4, 65 / 25.4),
        'figsize_wide': (190 / 25.4, 65 / 25.4),
        'figsize_multi': (190 / 25.4, 130 / 25.4),
        'dpi': 300,
        'font_family': 'Arial',
        'font_size': 8,
        'title_size': 9,
        'label_size': 8,
        'tick_size': 7,
        'legend_size': 7,
        'line_width': 1.2,
        'marker_size': 3,
        'grid': True,
        'grid_alpha': 0.2,
        'fill_alpha': 0.2,
        'spine_width': 0.5,
    },
}

# Colors for multi-file comparison
FILE_COLORS = ['#1f77b4', '#d62728', '#2ca02c', '#ff7f0e']
# Colors for L/R within same file
SIDE_COLORS = {'L': '#1f77b4', 'R': '#d62728'}
# Des vs Act
TRACK_COLORS = {'des': '#888888', 'act': '#1f77b4'}


def _resolve_font(font_name: str) -> str:
    """Check if font exists, fallback to sans-serif default."""
    from matplotlib.font_manager import fontManager
    available = {f.name for f in fontManager.ttflist}
    if font_name in available:
        return font_name
    return 'DejaVu Sans'


def apply_style(style_name: str) -> dict:
    """Apply a journal style preset to matplotlib rcParams. Returns the style dict."""
    s = STYLES.get(style_name, STYLES['default'])
    resolved_font = _resolve_font(s['font_family'])
    mpl.rcParams.update({
        'font.family': resolved_font,
        'font.size': s['font_size'],
        'axes.titlesize': s['title_size'],
        'axes.labelsize': s['label_size'],
        'xtick.labelsize': s['tick_size'],
        'ytick.labelsize': s['tick_size'],
        'legend.fontsize': s['legend_size'],
        'lines.linewidth': s['line_width'],
        'lines.markersize': s['marker_size'],
        'axes.grid': s['grid'],
        'grid.alpha': s['grid_alpha'],
        'axes.linewidth': s['spine_width'],
        'figure.dpi': s['dpi'],
        'savefig.dpi': s['dpi'],
        'figure.facecolor': 'white',
        'axes.facecolor': 'white',
        'savefig.facecolor': 'white',
    })
    return s
