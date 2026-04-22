"""
Correlation/Scatter Tab - Enhanced
X-Y scatter, regression with 95% CI bands, residual plot,
R²/Pearson/Spearman, p-values, density coloring, Bland-Altman
"""

import os
import numpy as np
import pyqtgraph as pg
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QComboBox, QCheckBox, QSplitter, QTabWidget,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from styles import C, SERIES_COLORS
from widgets import CrosshairPlotWidget, ZoomToolbar
from data_manager import DataManager


class CorrelationTab(QWidget):
    """X-Y scatter plot with regression analysis, residuals, Bland-Altman."""

    def __init__(self, data_mgr: DataManager, parent=None):
        super().__init__(parent)
        self._dm = data_mgr
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(6, 6, 6, 6)

        # Controls
        ctrl = QFrame()
        ctrl.setObjectName("GlassCard")
        ctrl.setFixedHeight(48)
        ctrl.setStyleSheet(
            "QFrame#GlassCard { border-left: 2px solid rgba(76,158,255,0.30); }")
        cl = QHBoxLayout(ctrl)
        cl.setContentsMargins(10, 0, 10, 0)
        cl.setSpacing(6)

        cl.addWidget(QLabel("X:"))
        self._x_combo = QComboBox()
        self._x_combo.setMinimumWidth(140)
        self._x_combo.currentIndexChanged.connect(lambda: self.refresh())
        cl.addWidget(self._x_combo)

        cl.addWidget(QLabel("Y:"))
        self._y_combo = QComboBox()
        self._y_combo.setMinimumWidth(140)
        self._y_combo.currentIndexChanged.connect(lambda: self.refresh())
        cl.addWidget(self._y_combo)

        cl.addSpacing(6)

        self._regress_cb = QCheckBox("Reg")
        self._regress_cb.setChecked(True)
        self._regress_cb.setToolTip("Regression line")
        self._regress_cb.setStyleSheet(f"color:{C['text2']}; background:transparent;")
        self._regress_cb.toggled.connect(lambda: self.refresh())
        cl.addWidget(self._regress_cb)

        self._ci_cb = QCheckBox("CI")
        self._ci_cb.setChecked(True)
        self._ci_cb.setToolTip("95% Confidence Interval band")
        self._ci_cb.setStyleSheet(f"color:{C['text2']}; background:transparent;")
        self._ci_cb.toggled.connect(lambda: self.refresh())
        cl.addWidget(self._ci_cb)

        self._density_cb = QCheckBox("Den")
        self._density_cb.setToolTip("Density coloring")
        self._density_cb.setStyleSheet(f"color:{C['text2']}; background:transparent;")
        self._density_cb.toggled.connect(lambda: self.refresh())
        cl.addWidget(self._density_cb)

        cl.addSpacing(4)

        # Stats display
        self._stats_label = QLabel("")
        self._stats_label.setStyleSheet(
            f"color:{C['teal']}; font-size:10px; font-family:monospace; "
            f"background:rgba(30,34,55,0.90); "
            f"border:1px solid rgba(255,255,255,0.08); "
            f"border-left:2px solid {C['teal']}; "
            f"border-radius:4px; padding:3px 8px;")
        cl.addWidget(self._stats_label)
        layout.addWidget(ctrl)

        # Preset buttons
        preset_bar = QFrame()
        preset_bar.setObjectName("GlassCard")
        preset_bar.setFixedHeight(38)
        preset_bar.setStyleSheet(
            "QFrame#GlassCard { border-left: 2px solid rgba(76,158,255,0.15); }")
        pl = QHBoxLayout(preset_bar)
        pl.setContentsMargins(12, 0, 12, 0)
        pl.setSpacing(8)

        presets_label = QLabel("Presets:")
        presets_label.setStyleSheet(
            f"color:{C['text2']}; font-size:10px; font-weight:700; "
            f"letter-spacing:1px; background:transparent; border:none; "
            f"padding-right:4px;")
        pl.addWidget(presets_label)

        presets = [
            ("Force: Des vs Act L", "L_DesForce_N", "L_ActForce_N"),
            ("Force: Des vs Act R", "R_DesForce_N", "R_ActForce_N"),
            ("Force L vs R", "L_ActForce_N", "R_ActForce_N"),
            ("GCP vs Force L", "L_GCP", "L_ActForce_N"),
            ("Pitch L vs R", "L_Pitch", "R_Pitch"),
            ("Vel: Des vs Act L", "L_DesVel_mps", "L_ActVel_mps"),
        ]
        for label, xc, yc in presets:
            btn = QPushButton(label)
            btn.setObjectName("SmallBtn")
            btn.setFixedHeight(28)
            btn.clicked.connect(lambda _, x=xc, y=yc: self._set_preset(x, y))
            pl.addWidget(btn)
        pl.addStretch()
        layout.addWidget(preset_bar)

        # Sub-tabs: Scatter | Residual | Bland-Altman
        self._sub_tabs = QTabWidget()

        # Scatter plot
        scatter_w = QWidget()
        sl = QVBoxLayout(scatter_w)
        sl.setContentsMargins(4, 6, 4, 4)
        sl.setSpacing(4)
        self._plot = CrosshairPlotWidget()
        self._plot.setLabel('bottom', 'X')
        self._plot.setLabel('left', 'Y')
        sl.addWidget(ZoomToolbar(self._plot, with_y_lock=False))
        sl.addWidget(self._plot, 1)
        self._sub_tabs.addTab(scatter_w, "Scatter")

        # Residual plot
        resid_w = QWidget()
        rl = QVBoxLayout(resid_w)
        rl.setContentsMargins(4, 6, 4, 4)
        rl.setSpacing(4)
        self._resid_plot = CrosshairPlotWidget()
        self._resid_plot.setTitle("Residuals", color=C['text1'], size='10pt')
        self._resid_plot.setLabel('bottom', 'Predicted')
        self._resid_plot.setLabel('left', 'Residual')
        rl.addWidget(self._resid_plot, 1)
        self._sub_tabs.addTab(resid_w, "Residuals")

        # Bland-Altman
        ba_w = QWidget()
        bl = QVBoxLayout(ba_w)
        bl.setContentsMargins(4, 6, 4, 4)
        bl.setSpacing(4)
        self._ba_plot = CrosshairPlotWidget()
        self._ba_plot.setTitle("Bland-Altman Plot", color=C['text1'], size='10pt')
        self._ba_plot.setLabel('bottom', 'Mean of X and Y')
        self._ba_plot.setLabel('left', 'Difference (X - Y)')
        bl.addWidget(self._ba_plot, 1)

        self._ba_label = QLabel("")
        self._ba_label.setStyleSheet(
            f"color:{C['text1']}; font-size:10px; font-family:monospace; "
            f"background:rgba(30,34,55,0.95); "
            f"border:1px solid rgba(255,255,255,0.10); "
            f"border-left:2px solid {C['blue']}; "
            f"border-radius:4px; padding:6px 10px;")
        bl.addWidget(self._ba_label)
        self._sub_tabs.addTab(ba_w, "Bland-Altman")

        layout.addWidget(self._sub_tabs, 1)

    def update_columns(self):
        cols = self._dm.get_available_columns()
        prev_x = self._x_combo.currentText()
        prev_y = self._y_combo.currentText()

        self._x_combo.blockSignals(True)
        self._y_combo.blockSignals(True)
        self._x_combo.clear()
        self._y_combo.clear()
        self._x_combo.addItems(cols)
        self._y_combo.addItems(cols)

        if prev_x in cols:
            self._x_combo.setCurrentText(prev_x)
        elif "L_DesForce_N" in cols:
            self._x_combo.setCurrentText("L_DesForce_N")

        if prev_y in cols:
            self._y_combo.setCurrentText(prev_y)
        elif "L_ActForce_N" in cols:
            self._y_combo.setCurrentText("L_ActForce_N")

        self._x_combo.blockSignals(False)
        self._y_combo.blockSignals(False)

    def _set_preset(self, x_col, y_col):
        if self._x_combo.findText(x_col) >= 0:
            self._x_combo.setCurrentText(x_col)
        if self._y_combo.findText(y_col) >= 0:
            self._y_combo.setCurrentText(y_col)
        self.refresh()

    def refresh(self):
        self._plot.clear()
        self._resid_plot.clear()
        self._ba_plot.clear()
        self._stats_label.setText("")
        self._ba_label.setText("")

        if not self._dm.files:
            return

        x_col = self._x_combo.currentText()
        y_col = self._y_combo.currentText()
        if not x_col or not y_col:
            return

        for fi, lf in enumerate(self._dm.files):
            if x_col not in lf.df.columns or y_col not in lf.df.columns:
                continue

            x = lf.df[x_col].values.astype(np.float64)
            y = lf.df[y_col].values.astype(np.float64)
            mask = np.isfinite(x) & np.isfinite(y)
            x, y = x[mask], y[mask]
            if len(x) < 3:
                continue

            # Scatter
            if self._density_cb.isChecked():
                brushes = self._density_brushes(x, y, lf.color)
                scatter = pg.ScatterPlotItem(
                    x=x, y=y, size=4, pen=pg.mkPen(None), brush=brushes, name=lf.name)
            else:
                c = QColor(lf.color)
                c.setAlpha(120)
                scatter = pg.ScatterPlotItem(
                    x=x, y=y, size=4, pen=pg.mkPen(None), brush=pg.mkBrush(c), name=lf.name)
            self._plot.addItem(scatter)

            # Regression + stats
            if self._regress_cb.isChecked():
                coeffs = np.polyfit(x, y, 1)
                slope, intercept = coeffs
                y_pred = slope * x + intercept

                # R²
                ss_res = np.sum((y - y_pred) ** 2)
                ss_tot = np.sum((y - np.mean(y)) ** 2)
                r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
                pearson = np.corrcoef(x, y)[0, 1]

                # Spearman (rank correlation)
                rank_x = np.argsort(np.argsort(x)).astype(float)
                rank_y = np.argsort(np.argsort(y)).astype(float)
                spearman = np.corrcoef(rank_x, rank_y)[0, 1]

                # p-value approximation (t-test for correlation)
                n = len(x)
                if abs(pearson) < 1.0 and n > 2:
                    t_stat = pearson * np.sqrt((n - 2) / (1 - pearson**2))
                    # Approximate p-value using normal distribution for large n
                    p_val = 2 * (1 - self._norm_cdf(abs(t_stat)))
                else:
                    p_val = 0.0

                # Standard error of regression
                se = np.sqrt(ss_res / (n - 2)) if n > 2 else 0

                # Regression line
                x_fit = np.linspace(np.min(x), np.max(x), 200)
                y_fit = slope * x_fit + intercept
                self._plot.plot(x_fit, y_fit,
                    pen=pg.mkPen(lf.color, width=2, style=Qt.DashLine))

                # 95% confidence interval band
                if self._ci_cb.isChecked() and se > 0 and n > 2:
                    x_mean = np.mean(x)
                    ss_xx = np.sum((x - x_mean) ** 2)
                    t_crit = 1.96  # ~95% for large n
                    ci = t_crit * se * np.sqrt(1.0 / n + (x_fit - x_mean)**2 / ss_xx)

                    upper = pg.PlotDataItem(x_fit, y_fit + ci, pen=pg.mkPen(None))
                    lower = pg.PlotDataItem(x_fit, y_fit - ci, pen=pg.mkPen(None))
                    fill_c = QColor(lf.color)
                    fill_c.setAlpha(25)
                    fill = pg.FillBetweenItem(upper, lower, brush=fill_c)
                    self._plot.addItem(upper)
                    self._plot.addItem(lower)
                    self._plot.addItem(fill)

                # Stats text
                sig = "***" if p_val < 0.001 else "**" if p_val < 0.01 else "*" if p_val < 0.05 else "ns"
                self._stats_label.setText(
                    f"y={slope:.3f}x{intercept:+.2f}  R²={r2:.4f}  "
                    f"r={pearson:.4f}  ρ={spearman:.4f}  "
                    f"p={p_val:.4f}{sig}  SE={se:.3f}  n={n}")

                # Residual plot
                residuals = y - y_pred
                c_resid = QColor(lf.color)
                c_resid.setAlpha(150)
                self._resid_plot.plot(y_pred, residuals,
                    pen=pg.mkPen(None), symbol='o', symbolSize=3,
                    symbolBrush=pg.mkBrush(c_resid), symbolPen=pg.mkPen(None))
                self._resid_plot.addItem(pg.InfiniteLine(
                    pos=0, angle=0, pen=pg.mkPen(C['red'], width=1, style=Qt.DashLine)))

                # ±2σ bands on residual
                resid_std = np.std(residuals)
                for mult, ls in [(2, Qt.DotLine), (-2, Qt.DotLine)]:
                    self._resid_plot.addItem(pg.InfiniteLine(
                        pos=mult * resid_std, angle=0,
                        pen=pg.mkPen(C['muted'], width=1, style=ls),
                        label=f"{mult}σ", labelOpts={'color': C['muted']}))

            # Bland-Altman
            mean_xy = (x + y) / 2
            diff_xy = x - y
            bias = np.mean(diff_xy)
            sd_diff = np.std(diff_xy)

            c_ba = QColor(lf.color)
            c_ba.setAlpha(150)
            self._ba_plot.plot(mean_xy, diff_xy,
                pen=pg.mkPen(None), symbol='o', symbolSize=3,
                symbolBrush=pg.mkBrush(c_ba), symbolPen=pg.mkPen(None))

            # Bias line
            self._ba_plot.addItem(pg.InfiniteLine(
                pos=bias, angle=0, pen=pg.mkPen(C['blue'], width=2),
                label=f"Bias={bias:.3f}", labelOpts={'color': C['blue']}))

            # Limits of agreement (±1.96 SD)
            for mult, label_text in [(1.96, "+1.96SD"), (-1.96, "-1.96SD")]:
                val = bias + mult * sd_diff
                self._ba_plot.addItem(pg.InfiniteLine(
                    pos=val, angle=0,
                    pen=pg.mkPen(C['red'], width=1, style=Qt.DashLine),
                    label=f"{label_text}={val:.3f}",
                    labelOpts={'color': C['red']}))

            self._ba_label.setText(
                f"Bland-Altman: Bias={bias:.4f}  SD={sd_diff:.4f}  "
                f"LoA=[{bias - 1.96*sd_diff:.3f}, {bias + 1.96*sd_diff:.3f}]  n={len(x)}")

        self._plot.setLabel('bottom', x_col)
        self._plot.setLabel('left', y_col)
        self._plot.enableAutoRange()
        self._resid_plot.enableAutoRange()
        self._ba_plot.enableAutoRange()

    @staticmethod
    def _norm_cdf(x):
        """Approximate standard normal CDF."""
        return 0.5 * (1 + np.tanh(np.sqrt(2 / np.pi) * (x + 0.044715 * x**3)))

    @staticmethod
    def _density_brushes(x, y, base_color, n_bins=30):
        hist, xedges, yedges = np.histogram2d(x, y, bins=n_bins)
        xi = np.clip(np.digitize(x, xedges) - 1, 0, n_bins - 1)
        yi = np.clip(np.digitize(y, yedges) - 1, 0, n_bins - 1)
        densities = hist[xi, yi]
        if np.max(densities) > 0:
            densities = densities / np.max(densities)
        base = QColor(base_color)
        brushes = []
        for d in densities:
            c = QColor(base)
            c.setAlpha(int(40 + d * 200))
            brushes.append(pg.mkBrush(c))
        return brushes
