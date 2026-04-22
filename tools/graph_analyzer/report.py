"""
H-Walker Graph Analyzer - HTML Report Generator
Auto-generate comprehensive analysis report with embedded charts
"""

import os
import io
import base64
import datetime
import numpy as np

from data_manager import DataManager


def _fig_to_base64(plot_widget) -> str:
    """Convert a pyqtgraph PlotWidget to base64 PNG string."""
    try:
        from pyqtgraph.exporters import ImageExporter
        exporter = ImageExporter(plot_widget.plotItem)
        exporter.parameters()['width'] = 1200
        # Export to bytes
        buf = io.BytesIO()
        exporter.export(buf)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode('utf-8')
    except Exception:
        # Fallback: grab widget as pixmap
        from PyQt5.QtCore import QBuffer, QIODevice
        pixmap = plot_widget.grab()
        buf = QBuffer()
        buf.open(QIODevice.WriteOnly)
        pixmap.save(buf, "PNG")
        return base64.b64encode(buf.data().data()).decode('utf-8')


def _stats_table_html(dm: DataManager, columns: list) -> str:
    """Generate HTML stats table for selected columns."""
    rows = []
    for lf in dm.files:
        for col in columns:
            if col not in lf.df.columns:
                continue
            y = lf.df[col].values.astype(np.float64)
            s = DataManager.compute_stats(y)
            rows.append(f"""
                <tr>
                    <td>{lf.name}</td>
                    <td>{col}</td>
                    <td>{s['count']}</td>
                    <td>{s['mean']:.4f}</td>
                    <td>{s['std']:.4f}</td>
                    <td>{s['min']:.4f}</td>
                    <td>{s['max']:.4f}</td>
                    <td>{s['median']:.4f}</td>
                    <td>{s['rms']:.4f}</td>
                    <td>{s['p2p']:.4f}</td>
                    <td>{s['cv']:.2f}</td>
                    <td>{s['iqr']:.4f}</td>
                    <td>{s['q1']:.4f}</td>
                    <td>{s['q3']:.4f}</td>
                    <td>{s['p5']:.4f}</td>
                    <td>{s['p95']:.4f}</td>
                    <td>{s['skewness']:.4f}</td>
                    <td>{s['kurtosis']:.4f}</td>
                </tr>""")

    return f"""
    <table>
        <thead>
            <tr>
                <th>File</th><th>Column</th><th>Count</th>
                <th>Mean</th><th>Std</th><th>Min</th><th>Max</th>
                <th>Median</th><th>RMS</th><th>P2P</th>
                <th>CV(%)</th><th>IQR</th><th>Q1</th><th>Q3</th>
                <th>P5</th><th>P95</th><th>Skew</th><th>Kurt</th>
            </tr>
        </thead>
        <tbody>{"".join(rows)}</tbody>
    </table>"""


def _detailed_column_html(dm: DataManager, columns: list) -> str:
    """Generate detailed per-column analysis cards with distribution info."""
    if not columns:
        return "<p class='muted'>No columns selected for detailed analysis.</p>"
    cards = []
    for lf in dm.files:
        for col in columns:
            if col not in lf.df.columns:
                continue
            y = lf.df[col].values.astype(np.float64)
            s = DataManager.compute_stats(y)
            # Histogram-like distribution summary
            valid = y[np.isfinite(y)]
            if len(valid) > 0:
                pcts = [0, 10, 25, 50, 75, 90, 100]
                pct_vals = np.percentile(valid, pcts)
                pct_rows = "".join(
                    f"<td>{v:.4f}</td>" for v in pct_vals
                )
                pct_header = "".join(f"<th>P{p}</th>" for p in pcts)
            else:
                pct_rows = "<td colspan='7'>No valid data</td>"
                pct_header = ""

            cards.append(f"""
            <div class="chart-section">
                <h3>{lf.name} &mdash; {col}</h3>
                <div class="summary-grid">
                    <div class="summary-card">
                        <div class="value">{s['mean']:.4f}</div>
                        <div class="label">Mean</div>
                    </div>
                    <div class="summary-card">
                        <div class="value">{s['std']:.4f}</div>
                        <div class="label">Std Dev</div>
                    </div>
                    <div class="summary-card">
                        <div class="value">{s['rms']:.4f}</div>
                        <div class="label">RMS</div>
                    </div>
                    <div class="summary-card">
                        <div class="value">{s['p2p']:.4f}</div>
                        <div class="label">Peak-to-Peak</div>
                    </div>
                    <div class="summary-card">
                        <div class="value">{s['cv']:.2f}%</div>
                        <div class="label">CV</div>
                    </div>
                    <div class="summary-card">
                        <div class="value">{s['skewness']:.4f}</div>
                        <div class="label">Skewness</div>
                    </div>
                    <div class="summary-card">
                        <div class="value">{s['kurtosis']:.4f}</div>
                        <div class="label">Kurtosis</div>
                    </div>
                    <div class="summary-card">
                        <div class="value">{s['nan_count']}</div>
                        <div class="label">NaN Count ({s['nan_pct']:.1f}%)</div>
                    </div>
                </div>
                <table>
                    <thead><tr><th>Percentile</th>{pct_header}</tr></thead>
                    <tbody><tr><td>Value</td>{pct_rows}</tr></tbody>
                </table>
            </div>""")
    return "".join(cards) if cards else "<p class='muted'>No matching columns found.</p>"


def _gait_table_html(dm: DataManager) -> str:
    """Generate gait parameters table as HTML."""
    if not dm.files:
        return "<p>No files loaded</p>"

    all_params = []
    for lf in dm.files:
        params = DataManager.compute_gait_params(lf.df)
        params['_fname'] = lf.name
        all_params.append(params)

    def _fmt(p, key):
        prefix = key.split('_')[0]
        if p.get(f'{prefix}_no_data'):
            return "No GCP"
        m = p.get(f'{key}_mean', 0)
        s = p.get(f'{key}_std', 0)
        if m == 0 and s == 0:
            return "0 strides"
        return f"{m:.2f} &plusmn; {s:.2f}"

    param_rows = [
        ("Total Strides", lambda p: f"{p.get('l_stride_count',0) + p.get('r_stride_count',0)}"),
        ("Total Samples", lambda p: f"{p.get('total_samples',0):,}"),
        ("Duration (s)", lambda p: f"{p.get('duration_s',0):.1f}"),
        ("Sample Rate (Hz)", lambda p: f"{p.get('sample_rate',0):.1f}"),
        ("HS Count (L / R)", lambda p: f"{p.get('l_hs_count',0)} / {p.get('r_hs_count',0)}"),
        ("HO Count (L / R)", lambda p: f"{p.get('l_ho_count',0)} / {p.get('r_ho_count',0)}"),
        ("Stride Time L (s)", lambda p: _fmt(p, 'l_stride_time')),
        ("Stride Time R (s)", lambda p: _fmt(p, 'r_stride_time')),
        ("Step Time L (s)", lambda p: _fmt(p, 'l_step_time')),
        ("Step Time R (s)", lambda p: _fmt(p, 'r_step_time')),
        ("Cadence L (steps/min)", lambda p: f"{p.get('l_cadence',0):.1f}"),
        ("Cadence R (steps/min)", lambda p: f"{p.get('r_cadence',0):.1f}"),
        ("Avg Cadence", lambda p: f"{p.get('avg_cadence',0):.1f}"),
        ("Stride CV L (%)", lambda p: f"{p.get('l_stride_cv',0):.2f}"),
        ("Stride CV R (%)", lambda p: f"{p.get('r_stride_cv',0):.2f}"),
        ("Stance Phase L (%)", lambda p: _fmt(p, 'l_stance')),
        ("Stance Phase R (%)", lambda p: _fmt(p, 'r_stance')),
        ("Swing Phase L (%)", lambda p: _fmt(p, 'l_swing')),
        ("Swing Phase R (%)", lambda p: _fmt(p, 'r_swing')),
        ("Peak Force L (N)", lambda p: _fmt(p, 'l_peak_force')),
        ("Peak Force R (N)", lambda p: _fmt(p, 'r_peak_force')),
        ("Mean Force L (N)", lambda p: _fmt(p, 'l_mean_force')),
        ("Mean Force R (N)", lambda p: _fmt(p, 'r_mean_force')),
        ("Symmetry Index (%)", lambda p: f"{p.get('symmetry_index',0):.1f}"),
        ("Force Symmetry (%)", lambda p: f"{p.get('force_symmetry',0):.1f}"),
        ("Stance Symmetry (%)", lambda p: f"{p.get('stance_symmetry',0):.1f}"),
        ("Cadence Symmetry (%)", lambda p: f"{p.get('cadence_symmetry',0):.1f}"),
        ("Fatigue Ratio L (%)", lambda p: f"{p.get('l_fatigue_ratio',0):.2f}"),
        ("Fatigue Ratio R (%)", lambda p: f"{p.get('r_fatigue_ratio',0):.2f}"),
    ]

    # Build table
    header = "<th>Parameter</th>" + "".join(f"<th>{p['_fname']}</th>" for p in all_params)
    rows = []
    for name, getter in param_rows:
        cells = f"<td><strong>{name}</strong></td>"
        for p in all_params:
            try:
                cells += f"<td>{getter(p)}</td>"
            except Exception:
                cells += "<td>—</td>"
        rows.append(f"<tr>{cells}</tr>")

    return f"""
    <table>
        <thead><tr>{header}</tr></thead>
        <tbody>{"".join(rows)}</tbody>
    </table>"""


def generate_report(dm: DataManager, columns: list,
                    plots: dict = None, output_path: str = None) -> str:
    """Generate a complete HTML analysis report.

    Args:
        dm: DataManager with loaded files
        columns: List of selected column names
        plots: Optional dict of {name: PlotWidget} to embed as images
        output_path: If provided, save to file

    Returns:
        HTML string
    """
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # File info
    file_rows = ""
    for lf in dm.files:
        duration_s = len(lf.df) / DataManager.estimate_sample_rate(lf.df)
        file_rows += f"""
            <tr>
                <td>{lf.name}</td>
                <td>{len(lf.df):,} rows</td>
                <td>{len(lf.df.columns)} cols</td>
                <td>{duration_s:.1f} s</td>
                <td>{DataManager.estimate_sample_rate(lf.df):.1f} Hz</td>
                <td>{lf.path}</td>
                <td style="color:{lf.color}">&#9632; {lf.color}</td>
            </tr>"""

    # Per-file column listing for reference
    column_listing = ""
    for lf in dm.files:
        cols_str = ", ".join(lf.df.columns.tolist())
        column_listing += f"""
        <div class="summary-card">
            <div class="label"><strong>{lf.name}</strong> &mdash; {len(lf.df.columns)} columns</div>
            <div style="font-size:10px; color:var(--text2); margin-top:6px; word-wrap:break-word;">
                {cols_str}
            </div>
        </div>"""

    # Embedded chart images
    chart_sections = ""
    if plots:
        for name, plot in plots.items():
            try:
                b64 = _fig_to_base64(plot)
                chart_sections += f"""
                <div class="chart-section">
                    <h3>{name}</h3>
                    <img src="data:image/png;base64,{b64}" alt="{name}">
                </div>"""
            except Exception:
                chart_sections += f"""
                <div class="chart-section">
                    <h3>{name}</h3>
                    <p class="muted">Chart export failed</p>
                </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>H-Walker Analysis Report - {now}</title>
<style>
    :root {{
        --bg: #0D0D0F; --card: #1A1A24; --text1: #E2E8F0;
        --text2: #94A3B8; --muted: #64748B; --blue: #4C9EFF;
        --border: rgba(255,255,255,0.06);
    }}
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    body {{
        font-family: "Inter","SF Pro Display","Segoe UI",sans-serif;
        background: var(--bg); color: var(--text1); padding: 32px;
        line-height: 1.6;
    }}
    .container {{ max-width: 1200px; margin: 0 auto; }}
    h1 {{ color: var(--blue); font-size: 24px; margin-bottom: 4px; }}
    h2 {{
        color: var(--text2); font-size: 16px; margin: 32px 0 12px;
        padding-bottom: 8px; border-bottom: 1px solid var(--border);
    }}
    h3 {{ color: var(--text2); font-size: 14px; margin: 16px 0 8px; }}
    .meta {{ color: var(--muted); font-size: 12px; margin-bottom: 24px; }}
    .muted {{ color: var(--muted); }}
    table {{
        width: 100%; border-collapse: collapse; margin: 12px 0;
        background: var(--card); border-radius: 8px; overflow: hidden;
    }}
    th {{
        background: rgba(255,255,255,0.04); color: var(--text2);
        font-size: 11px; font-weight: 700; text-align: left;
        padding: 8px 12px; border-bottom: 1px solid var(--border);
    }}
    td {{
        padding: 6px 12px; font-size: 12px;
        border-bottom: 1px solid rgba(255,255,255,0.02);
    }}
    tr:hover td {{ background: rgba(255,255,255,0.02); }}
    .chart-section {{
        background: var(--card); border-radius: 12px; padding: 16px;
        margin: 16px 0; border: 1px solid var(--border);
    }}
    .chart-section img {{
        width: 100%; border-radius: 8px; margin-top: 8px;
    }}
    .summary-grid {{
        display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 12px; margin: 16px 0;
    }}
    .summary-card {{
        background: var(--card); border-radius: 10px; padding: 16px;
        border: 1px solid var(--border);
    }}
    .summary-card .value {{
        font-size: 24px; font-weight: 700; color: var(--blue);
    }}
    .summary-card .label {{ font-size: 11px; color: var(--muted); margin-top: 4px; }}
    footer {{
        margin-top: 48px; padding-top: 16px;
        border-top: 1px solid var(--border);
        color: var(--muted); font-size: 10px; text-align: center;
    }}
</style>
</head>
<body>
<div class="container">

<h1>H-Walker Analysis Report</h1>
<p class="meta">Generated: {now}</p>

<!-- Summary Cards -->
<div class="summary-grid">
    <div class="summary-card">
        <div class="value">{len(dm.files)}</div>
        <div class="label">Files Loaded</div>
    </div>
    <div class="summary-card">
        <div class="value">{sum(len(f.df) for f in dm.files):,}</div>
        <div class="label">Total Samples</div>
    </div>
    <div class="summary-card">
        <div class="value">{len(columns)}</div>
        <div class="label">Columns Analyzed</div>
    </div>
    <div class="summary-card">
        <div class="value">{len(dm.get_available_columns())}</div>
        <div class="label">Available Columns</div>
    </div>
</div>

<h2>Loaded Files</h2>
<table>
    <thead><tr><th>File</th><th>Rows</th><th>Columns</th><th>Duration</th><th>Sample Rate</th><th>Path</th><th>Color</th></tr></thead>
    <tbody>{file_rows}</tbody>
</table>

<h2>Available Columns</h2>
<div class="summary-grid">
{column_listing}
</div>

<h2>Column Statistics</h2>
{_stats_table_html(dm, columns)}

<h2>Detailed Column Analysis</h2>
{_detailed_column_html(dm, columns)}

<h2>Gait Parameters</h2>
{_gait_table_html(dm)}

{f'<h2>Charts</h2>{chart_sections}' if chart_sections else ''}

<footer>
    H-Walker Graph Analyzer &mdash; Cable-Driven Walker Rehabilitation Robot<br>
    Report generated automatically
</footer>

</div>
</body>
</html>"""

    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

    return html
