"""
Gait Analysis Tab - Enhanced
HS detection, stride parameters, GCP-normalized force profiles,
fatigue trend, symmetry summary, stride-level overlay
"""

import os
import numpy as np
import pyqtgraph as pg
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QSplitter,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QTabWidget,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from styles import C, SERIES_COLORS
from widgets import CrosshairPlotWidget, ZoomToolbar
from data_manager import DataManager


class GaitTab(QWidget):
    """Gait analysis: parameter table + force profiles + fatigue + symmetry."""

    def __init__(self, data_mgr: DataManager, parent=None):
        super().__init__(parent)
        self._dm = data_mgr
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(6, 6, 6, 6)

        splitter = QSplitter(Qt.Vertical)

        # --- TOP: Parameter Table ---
        table_w = QWidget()
        tl = QVBoxLayout(table_w)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(4)

        title = QLabel("GAIT PARAMETERS")
        title.setStyleSheet(
            f"color:{C['text2']}; font-size:11px; font-weight:700; "
            f"letter-spacing:1.5px; background:transparent; "
            f"border:none; border-bottom:2px solid rgba(76,158,255,0.30); "
            f"padding-bottom:4px; margin-bottom:2px;")
        tl.addWidget(title)

        self._table = QTableWidget()
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionMode(QAbstractItemView.NoSelection)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(True)
        tl.addWidget(self._table)
        splitter.addWidget(table_w)

        # --- BOTTOM: Sub-tabs for different plots ---
        self._plot_tabs = QTabWidget()

        # Force profile
        force_w = QWidget()
        fl = QVBoxLayout(force_w)
        fl.setContentsMargins(4, 6, 4, 4)
        fl.setSpacing(4)
        self._plot = CrosshairPlotWidget()
        self._plot.setTitle("GCP-Normalized Force Profile", color=C['text1'], size='10pt')
        self._plot.setLabel('bottom', 'GCP (%)')
        self._plot.setLabel('left', 'Force (N)')
        self._plot.addLegend(offset=(10, 10))
        fl.addWidget(ZoomToolbar(self._plot))
        fl.addWidget(self._plot, 1)
        self._plot_tabs.addTab(force_w, "Force Profile")

        # Fatigue trend
        fatigue_w = QWidget()
        ftl = QVBoxLayout(fatigue_w)
        ftl.setContentsMargins(4, 6, 4, 4)
        ftl.setSpacing(4)
        self._fatigue_plot = CrosshairPlotWidget()
        self._fatigue_plot.setTitle("Stride Time Trend (Fatigue Indicator)", color=C['text1'], size='10pt')
        self._fatigue_plot.setLabel('bottom', 'Stride #')
        self._fatigue_plot.setLabel('left', 'Stride Time (s)')
        self._fatigue_plot.addLegend(offset=(10, 10))
        ftl.addWidget(ZoomToolbar(self._fatigue_plot, with_y_lock=False))
        ftl.addWidget(self._fatigue_plot, 1)
        self._plot_tabs.addTab(fatigue_w, "Fatigue Trend")

        # Symmetry overview
        symm_w = QWidget()
        sml = QVBoxLayout(symm_w)
        sml.setContentsMargins(4, 6, 4, 4)
        sml.setSpacing(4)
        self._symm_plot = CrosshairPlotWidget()
        self._symm_plot.setTitle("L/R Symmetry Comparison", color=C['text1'], size='10pt')
        self._symm_plot.setLabel('bottom', 'Metric')
        self._symm_plot.setLabel('left', 'Value')
        sml.addWidget(ZoomToolbar(self._symm_plot, with_y_lock=False))
        sml.addWidget(self._symm_plot, 1)
        self._plot_tabs.addTab(symm_w, "Symmetry")

        splitter.addWidget(self._plot_tabs)
        splitter.setSizes([280, 420])
        layout.addWidget(splitter, 1)

    def refresh(self):
        self._plot.clear()
        self._fatigue_plot.clear()
        self._fatigue_plot.addLegend(offset=(10, 10))
        self._symm_plot.clear()

        if not self._dm.files:
            self._table.setRowCount(0)
            self._table.setColumnCount(0)
            return

        all_params = []
        x_pct = np.linspace(0, 100, 101)

        for fi, lf in enumerate(self._dm.files):
            params = DataManager.compute_gait_params(lf.df)
            params['_fname'] = lf.name
            params['_color'] = lf.color
            all_params.append(params)

            # Force profile plot
            if params.get('l_force_strides') is not None:
                self._plot_band(params['l_force_strides'], x_pct,
                                lf.color, f"L ({lf.name})", 40)
            r_color = SERIES_COLORS[(fi * 2 + 1) % len(SERIES_COLORS)]
            if params.get('r_force_strides') is not None:
                self._plot_band(params['r_force_strides'], x_pct,
                                r_color, f"R ({lf.name})", 30)

            # Fatigue trend: stride time over stride number
            for side, prefix, s_color in [
                ('L', 'l', lf.color),
                ('R', 'r', SERIES_COLORS[(fi * 2 + 1) % len(SERIES_COLORS)])
            ]:
                stride_times = params.get(f'{prefix}_stride_times', np.array([]))
                if len(stride_times) >= 3:
                    x_strides = np.arange(1, len(stride_times) + 1)
                    self._fatigue_plot.plot(x_strides, stride_times,
                        pen=pg.mkPen(s_color, width=1.5),
                        name=f"{side} ({lf.name})")

                    # Trend line (linear fit)
                    if len(stride_times) >= 5:
                        coeffs = np.polyfit(x_strides, stride_times, 1)
                        trend = np.polyval(coeffs, x_strides)
                        self._fatigue_plot.plot(x_strides, trend,
                            pen=pg.mkPen(s_color, width=2, style=Qt.DashLine))
                        # Slope annotation
                        slope_ms = coeffs[0] * 1000  # ms per stride
                        trend_label = pg.TextItem(
                            f"{slope_ms:+.2f} ms/stride",
                            anchor=(0, 1), color=s_color)
                        trend_label.setFont(pg.QtGui.QFont("monospace", 8))
                        trend_label.setPos(x_strides[-1], trend[-1])
                        self._fatigue_plot.addItem(trend_label)

        self._plot.enableAutoRange()
        self._fatigue_plot.enableAutoRange()
        self._build_table(all_params)
        self._build_symmetry_chart(all_params)

    def _plot_band(self, strides, x_pct, color, name, alpha):
        mean = np.mean(strides, axis=0)
        std = np.std(strides, axis=0)

        upper = pg.PlotDataItem(x_pct, mean + std, pen=pg.mkPen(None))
        lower = pg.PlotDataItem(x_pct, mean - std, pen=pg.mkPen(None))
        fill_c = QColor(color)
        fill_c.setAlpha(alpha)
        fill = pg.FillBetweenItem(upper, lower, brush=fill_c)
        self._plot.addItem(upper)
        self._plot.addItem(lower)
        self._plot.addItem(fill)

        # Individual strides (thin, semi-transparent)
        if len(strides) <= 30:
            for stride in strides:
                c = QColor(color)
                c.setAlpha(40)
                self._plot.plot(x_pct, stride, pen=pg.mkPen(c, width=0.5))

        self._plot.plot(x_pct, mean, pen=pg.mkPen(color, width=2),
                       name=f"{name} (n={len(strides)})")

    def _build_symmetry_chart(self, all_params):
        """Bar chart comparing L vs R metrics."""
        if not all_params:
            return

        # Use first file for symmetry chart
        p = all_params[0]
        metrics = [
            ("Stride\nTime", p.get('l_stride_time_mean', 0), p.get('r_stride_time_mean', 0), "s"),
            ("Stance\n(%)", p.get('l_stance_mean', 0), p.get('r_stance_mean', 0), "%"),
            ("Swing\n(%)", p.get('l_swing_mean', 0), p.get('r_swing_mean', 0), "%"),
            ("Peak\nForce", p.get('l_peak_force_mean', 0), p.get('r_peak_force_mean', 0), "N"),
            ("Mean\nForce", p.get('l_mean_force_mean', 0), p.get('r_mean_force_mean', 0), "N"),
            ("Cadence", p.get('l_cadence', 0), p.get('r_cadence', 0), "st/m"),
        ]

        x = np.arange(len(metrics))
        bar_w = 0.35

        l_vals = [m[1] for m in metrics]
        r_vals = [m[2] for m in metrics]

        if any(v > 0 for v in l_vals + r_vals):
            l_bars = pg.BarGraphItem(x=x - bar_w/2, height=l_vals, width=bar_w,
                                      brush=QColor(C['blue']), pen=pg.mkPen(None), name="Left")
            r_bars = pg.BarGraphItem(x=x + bar_w/2, height=r_vals, width=bar_w,
                                      brush=QColor(C['orange']), pen=pg.mkPen(None), name="Right")
            self._symm_plot.addItem(l_bars)
            self._symm_plot.addItem(r_bars)
            self._symm_plot.addLegend(offset=(10, 10))

            # Labels
            ax = self._symm_plot.getAxis('bottom')
            ax.setTicks([[(i, m[0]) for i, m in enumerate(metrics)]])

            # Value labels on bars
            for i, (_, lv, rv, unit) in enumerate(metrics):
                for val, xpos, color in [(lv, i - bar_w/2, C['blue']), (rv, i + bar_w/2, C['orange'])]:
                    if val > 0:
                        txt = pg.TextItem(f"{val:.1f}", anchor=(0.5, 1.1), color=color)
                        txt.setFont(pg.QtGui.QFont("monospace", 7))
                        txt.setPos(xpos, val)
                        self._symm_plot.addItem(txt)

        self._symm_plot.enableAutoRange()

    def _build_table(self, all_params):
        if not all_params:
            self._table.setRowCount(0)
            return

        rows = [
            ("Recording", None),
            ("  Duration (s)", lambda p: f"{p.get('duration_s', 0):.1f}"),
            ("  Sample Rate (Hz)", lambda p: f"{p.get('sample_rate', 0):.0f}"),
            ("  Total Samples", lambda p: f"{p.get('total_samples', 0)}"),
            ("", None),
            ("Stride Count", None),
            ("  Total Strides", lambda p: f"{p.get('l_stride_count',0) + p.get('r_stride_count',0)}"),
            ("  HS Count (L / R)", lambda p: f"{p.get('l_hs_count',0)} / {p.get('r_hs_count',0)}"),
            ("  HO Count (L / R)", lambda p: f"{p.get('l_ho_count',0)} / {p.get('r_ho_count',0)}"),
            ("", None),
            ("Temporal Parameters", None),
            ("  Stride Time L (s)", lambda p: _fmt(p, 'l_stride_time')),
            ("  Stride Time R (s)", lambda p: _fmt(p, 'r_stride_time')),
            ("  Step Time L (s)", lambda p: _fmt(p, 'l_step_time')),
            ("  Step Time R (s)", lambda p: _fmt(p, 'r_step_time')),
            ("  Cadence L (steps/min)", lambda p: f"{p.get('l_cadence',0):.1f}"),
            ("  Cadence R (steps/min)", lambda p: f"{p.get('r_cadence',0):.1f}"),
            ("  Avg Cadence", lambda p: f"{p.get('avg_cadence',0):.1f}"),
            ("", None),
            ("Phase Distribution", None),
            ("  Stance Phase L (%)", lambda p: _fmt(p, 'l_stance')),
            ("  Stance Phase R (%)", lambda p: _fmt(p, 'r_stance')),
            ("  Swing Phase L (%)", lambda p: _fmt(p, 'l_swing')),
            ("  Swing Phase R (%)", lambda p: _fmt(p, 'r_swing')),
            ("", None),
            ("Force", None),
            ("  Peak Force L (N)", lambda p: _fmt(p, 'l_peak_force')),
            ("  Peak Force R (N)", lambda p: _fmt(p, 'r_peak_force')),
            ("  Mean Force L (N)", lambda p: _fmt(p, 'l_mean_force')),
            ("  Mean Force R (N)", lambda p: _fmt(p, 'r_mean_force')),
            ("", None),
            ("Symmetry & Variability", None),
            ("  Stride Time SI (%)", lambda p: f"{p.get('symmetry_index',0):.1f}"),
            ("  Force SI (%)", lambda p: f"{p.get('force_symmetry',0):.1f}"),
            ("  Stance SI (%)", lambda p: f"{p.get('stance_symmetry',0):.1f}"),
            ("  Cadence SI (%)", lambda p: f"{p.get('cadence_symmetry',0):.1f}"),
            ("  Stride CV L (%)", lambda p: f"{p.get('l_stride_cv',0):.1f}"),
            ("  Stride CV R (%)", lambda p: f"{p.get('r_stride_cv',0):.1f}"),
            ("", None),
            ("Fatigue Indicators", None),
            ("  L Fatigue Ratio (%)", lambda p: f"{p.get('l_fatigue_ratio',0):+.1f}"),
            ("  R Fatigue Ratio (%)", lambda p: f"{p.get('r_fatigue_ratio',0):+.1f}"),
        ]

        headers = ["Parameter"] + [p['_fname'] for p in all_params]
        self._table.setColumnCount(len(headers))
        self._table.setRowCount(len(rows))
        self._table.setHorizontalHeaderLabels(headers)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, len(headers)):
            self._table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)

        for ri, (name, getter) in enumerate(rows):
            if getter is None:
                if name == "":
                    # Separator
                    item = QTableWidgetItem("")
                    item.setFlags(Qt.NoItemFlags)
                    self._table.setItem(ri, 0, item)
                    self._table.setRowHeight(ri, 6)
                    for c in range(1, len(headers)):
                        self._table.setItem(ri, c, QTableWidgetItem(""))
                else:
                    # Section header
                    item = QTableWidgetItem(name)
                    item.setForeground(pg.mkColor(C['blue']))
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                    self._table.setItem(ri, 0, item)
                    for c in range(1, len(headers)):
                        self._table.setItem(ri, c, QTableWidgetItem(""))
                continue

            self._table.setItem(ri, 0, QTableWidgetItem(name))
            for fi, params in enumerate(all_params):
                try:
                    val = getter(params)
                except Exception:
                    val = "—"
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                self._table.setItem(ri, fi + 1, item)


def _fmt(p: dict, key: str) -> str:
    prefix = key.split('_')[0]
    if p.get(f'{prefix}_no_data'):
        return "No GCP"
    m = p.get(f'{key}_mean', 0)
    s = p.get(f'{key}_std', 0)
    if m == 0 and s == 0:
        return "0 strides"
    return f"{m:.2f} ± {s:.2f}"
