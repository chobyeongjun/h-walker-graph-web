"""
Compare Tab - Stride-normalized multi-file comparison with mean±SD bands
"""

import os
import numpy as np
import pyqtgraph as pg
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QCheckBox, QComboBox, QScrollArea,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from styles import C, SERIES_COLORS
from widgets import CrosshairPlotWidget, ZoomToolbar, LabelEditors
from data_manager import DataManager, COLUMN_GROUPS

PEN_STYLES = [Qt.SolidLine, Qt.DashLine, Qt.DotLine, Qt.DashDotLine]


class CompareTab(QWidget):
    """Compare columns across multiple files with optional stride normalization."""

    def __init__(self, data_mgr: DataManager, parent=None):
        super().__init__(parent)
        self._dm = data_mgr
        self._line_width = 2.0
        self._cmp_checkboxes: dict[str, QCheckBox] = {}
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(6, 6, 6, 6)

        # Controls
        ctrl = QFrame()
        ctrl.setObjectName("GlassCard")
        ctrl.setFixedHeight(44)
        ctrl.setStyleSheet(
            "QFrame#GlassCard { border-left: 2px solid rgba(76,158,255,0.30); }")
        cl = QHBoxLayout(ctrl)
        cl.setContentsMargins(12, 0, 12, 0)

        cl.addWidget(QLabel("X:"))
        self._x_combo = QComboBox()
        self._x_combo.addItems(["Sample Index", "GCP (%)"])
        self._x_combo.setFixedWidth(120)
        self._x_combo.currentIndexChanged.connect(lambda: self.refresh())
        cl.addWidget(self._x_combo)

        cl.addSpacing(8)

        self._normalize_cb = QCheckBox("Normalize by stride")
        self._normalize_cb.setStyleSheet(f"color:{C['text2']}; background:transparent;")
        self._normalize_cb.toggled.connect(lambda: self.refresh())
        cl.addWidget(self._normalize_cb)

        cl.addStretch()

        hint = QLabel("Select columns below to compare across files")
        hint.setStyleSheet(f"color:{C['muted']}; font-size:10px; background:transparent; border:none;")
        cl.addWidget(hint)
        layout.addWidget(ctrl)

        # Column checkboxes (grouped)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(120)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("border:none; background:transparent;")

        inner = QWidget()
        inner.setStyleSheet("background:transparent;")
        grid = QVBoxLayout(inner)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(2)

        # Use a subset of groups that are most useful for comparison
        cmp_groups = [
            ("Force", ["L_ActForce_N", "R_ActForce_N", "L_DesForce_N", "R_DesForce_N"]),
            ("GCP", ["L_GCP", "R_GCP"]),
            ("IMU", ["L_Pitch", "R_Pitch", "L_Roll", "R_Roll"]),
            ("Gyro", ["L_Gy", "R_Gy", "L_Gx", "R_Gx"]),
            ("Vel", ["L_ActVel_mps", "R_ActVel_mps", "L_DesVel_mps", "R_DesVel_mps"]),
            ("Pos", ["L_ActPos_deg", "R_ActPos_deg", "L_DesPos_deg", "R_DesPos_deg"]),
            ("Curr", ["L_ActCurr_A", "R_ActCurr_A"]),
            ("Gait", ["L_Event", "R_Event", "L_Phase", "R_Phase", "L_StepTime", "R_StepTime"]),
            ("FF", ["L_MotionFF_mps", "R_MotionFF_mps", "L_TreadmillFF_mps", "R_TreadmillFF_mps"]),
        ]

        # Readable short names for compare checkboxes
        _SHORT = {
            "L_ActForce_N": "L Act", "R_ActForce_N": "R Act",
            "L_DesForce_N": "L Des", "R_DesForce_N": "R Des",
            "L_GCP": "L GCP", "R_GCP": "R GCP",
            "L_Pitch": "L Pitch", "R_Pitch": "R Pitch",
            "L_Roll": "L Roll", "R_Roll": "R Roll",
            "L_Gy": "L Gy", "R_Gy": "R Gy", "L_Gx": "L Gx", "R_Gx": "R Gx",
            "L_ActVel_mps": "L Act", "R_ActVel_mps": "R Act",
            "L_DesVel_mps": "L Des", "R_DesVel_mps": "R Des",
            "L_ActPos_deg": "L Act", "R_ActPos_deg": "R Act",
            "L_DesPos_deg": "L Des", "R_DesPos_deg": "R Des",
            "L_ActCurr_A": "L Act", "R_ActCurr_A": "R Act",
            "L_Event": "L Evt", "R_Event": "R Evt",
            "L_Phase": "L Phase", "R_Phase": "R Phase",
            "L_StepTime": "L Step", "R_StepTime": "R Step",
            "L_MotionFF_mps": "L Mot", "R_MotionFF_mps": "R Mot",
            "L_TreadmillFF_mps": "L Trdml", "R_TreadmillFF_mps": "R Trdml",
        }

        for group_name, cols in cmp_groups:
            row = QHBoxLayout()
            row.setSpacing(8)
            glbl = QLabel(f"{group_name}:")
            glbl.setFixedWidth(42)
            glbl.setStyleSheet(
                f"color:{C['blue']}; font-size:10px; font-weight:700; "
                f"background:transparent; border:none;")
            row.addWidget(glbl)
            for col in cols:
                short = _SHORT.get(col, col.replace("_", " "))
                cb = QCheckBox(short)
                cb.setToolTip(col)
                cb.setStyleSheet(f"color:{C['text2']}; font-size:11px; background:transparent;")
                cb.toggled.connect(lambda _: self.refresh())
                row.addWidget(cb)
                self._cmp_checkboxes[col] = cb
            row.addStretch()
            grid.addLayout(row)

        scroll.setWidget(inner)
        layout.addWidget(scroll)

        # File legend
        self._file_bar = QFrame()
        self._file_bar.setObjectName("GlassCard")
        self._file_bar.setFixedHeight(36)
        self._file_bar.setStyleSheet(
            "QFrame#GlassCard { border-left: 2px solid rgba(76,158,255,0.15); }")
        self._file_layout = QHBoxLayout(self._file_bar)
        self._file_layout.setContentsMargins(12, 0, 12, 0)
        self._file_layout.addStretch()
        layout.addWidget(self._file_bar)

        # Plot
        self._plot = CrosshairPlotWidget()
        self._plot.addLegend(offset=(10, 10))

        layout.addWidget(ZoomToolbar(self._plot))
        layout.addWidget(self._plot, 1)
        layout.addWidget(LabelEditors(self._plot))

    def refresh(self):
        self._plot.clear()
        self._update_file_legend()

        if not self._dm.files:
            return

        selected = [name for name, cb in self._cmp_checkboxes.items() if cb.isChecked()]
        if not selected:
            return

        normalize = self._normalize_cb.isChecked()
        use_gcp = self._x_combo.currentIndex() == 1

        single_file = len(self._dm.files) == 1

        for lf in self._dm.files:
            pen_style = PEN_STYLES[lf.style_idx]
            if normalize:
                self._plot_normalized(lf, selected, pen_style, single_file)
            else:
                for ci, col in enumerate(selected):
                    if col not in lf.df.columns:
                        continue
                    y = lf.df[col].values.astype(np.float64)
                    if use_gcp and 'L_GCP' in lf.df.columns:
                        x = lf.df['L_GCP'].values.astype(np.float64) * 100
                    else:
                        x = np.arange(len(y), dtype=np.float64)
                    color = SERIES_COLORS[ci % len(SERIES_COLORS)] if single_file else lf.color
                    pen = pg.mkPen(color, width=self._line_width, style=pen_style)
                    self._plot.plot(x, y, pen=pen, name=f"{lf.name}: {col}")

        self._plot.enableAutoRange()

    def _plot_normalized(self, lf, selected_cols, pen_style, single_file=False):
        gcp_col = 'L_GCP' if 'L_GCP' in lf.df.columns else (
            'R_GCP' if 'R_GCP' in lf.df.columns else None)
        if gcp_col is None:
            return

        gcp = lf.df[gcp_col].values.astype(np.float64)
        gcp_max = np.nanmax(gcp)
        if gcp_max > 10:
            gcp = gcp / 100.0
        elif gcp_max > 1.5:
            gcp = gcp / gcp_max

        diffs = np.diff(gcp)
        drop_threshold = -max(0.3, np.ptp(gcp[np.isfinite(gcp)]) * 0.4)
        boundaries = np.where(diffs < drop_threshold)[0] + 1
        x_pct = np.linspace(0, 100, 101)

        for ci, col in enumerate(selected_cols):
            if col not in lf.df.columns:
                continue
            color = SERIES_COLORS[ci % len(SERIES_COLORS)] if single_file else lf.color
            y = lf.df[col].values.astype(np.float64)

            profiles = []
            for i in range(len(boundaries) - 1):
                s, e = boundaries[i], boundaries[i + 1]
                if e - s < 10:
                    continue
                stride_y = y[s:e]
                x_orig = np.linspace(0, 100, len(stride_y))
                interp = np.interp(x_pct, x_orig, stride_y)
                profiles.append(interp)

                # Individual stride (thin, transparent)
                c = QColor(color)
                c.setAlpha(60)
                thin_pen = pg.mkPen(c, width=1, style=pen_style)
                self._plot.plot(x_pct, interp, pen=thin_pen)

            if len(profiles) >= 2:
                arr = np.array(profiles)
                mean = np.mean(arr, axis=0)
                std = np.std(arr, axis=0)

                fill_c = QColor(color)
                fill_c.setAlpha(35)
                upper = pg.PlotDataItem(x_pct, mean + std, pen=pg.mkPen(None))
                lower = pg.PlotDataItem(x_pct, mean - std, pen=pg.mkPen(None))
                fill = pg.FillBetweenItem(upper, lower, brush=fill_c)
                self._plot.addItem(upper)
                self._plot.addItem(lower)
                self._plot.addItem(fill)

                self._plot.plot(x_pct, mean,
                    pen=pg.mkPen(color, width=3, style=pen_style),
                    name=f"{lf.name}: {col} (n={len(profiles)})")

    def _update_file_legend(self):
        while self._file_layout.count() > 1:
            item = self._file_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        style_chars = ["───", "- - -", "· · ·", "─·─"]
        for lf in self._dm.files:
            d = QLabel(f"● {lf.name}")
            d.setStyleSheet(
                f"color:{lf.color}; font-size:11px; font-weight:600; "
                f"background:transparent; border:none;")
            self._file_layout.insertWidget(self._file_layout.count() - 1, d)
