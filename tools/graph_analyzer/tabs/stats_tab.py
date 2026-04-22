"""
Statistics Tab - Enhanced
Per-column stats (skewness, kurtosis, CV), normality test, histogram + CDF,
box plot comparison, region crop
"""

import os
import numpy as np
import pyqtgraph as pg
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QComboBox, QSplitter, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QSpinBox, QCheckBox,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from styles import C, SERIES_COLORS
from widgets import CrosshairPlotWidget, ZoomToolbar
from data_manager import DataManager


class StatsTab(QWidget):
    """Comprehensive statistics with histogram, CDF, box plot, normality."""

    def __init__(self, data_mgr: DataManager, parent=None):
        super().__init__(parent)
        self._dm = data_mgr
        self._selected_columns: set = set()
        self._crop_start = 0
        self._crop_end = -1
        self._rows_data = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(6, 6, 6, 6)

        # Region crop controls
        crop_bar = QFrame()
        crop_bar.setObjectName("GlassCard")
        crop_bar.setFixedHeight(40)
        crop_bar.setStyleSheet(
            "QFrame#GlassCard { border-left: 2px solid rgba(76,158,255,0.30); }")
        cl = QHBoxLayout(crop_bar)
        cl.setContentsMargins(12, 0, 12, 0)
        cl.setSpacing(8)

        cl.addWidget(QLabel("Region:"))
        cl.addWidget(QLabel("Start:"))
        self._start_spin = QSpinBox()
        self._start_spin.setRange(0, 999999)
        self._start_spin.setValue(0)
        self._start_spin.setFixedWidth(80)
        self._start_spin.valueChanged.connect(lambda v: self._set_crop(v, None))
        cl.addWidget(self._start_spin)

        cl.addWidget(QLabel("End:"))
        self._end_spin = QSpinBox()
        self._end_spin.setRange(-1, 999999)
        self._end_spin.setValue(-1)
        self._end_spin.setFixedWidth(80)
        self._end_spin.setSpecialValueText("End")
        self._end_spin.valueChanged.connect(lambda v: self._set_crop(None, v))
        cl.addWidget(self._end_spin)

        reset_btn = QPushButton("Full Range")
        reset_btn.setObjectName("SmallBtn")
        reset_btn.clicked.connect(self._reset_crop)
        cl.addWidget(reset_btn)

        cl.addStretch()

        self._outlier_cb = QCheckBox("Remove outliers")
        self._outlier_cb.setStyleSheet(f"color:{C['text2']}; background:transparent;")
        self._outlier_cb.setToolTip("Remove outliers (IQR method) before computing stats")
        cl.addWidget(self._outlier_cb)

        refresh_btn = QPushButton("Refresh Stats")
        refresh_btn.setObjectName("AccentBtn")
        refresh_btn.clicked.connect(self.refresh)
        cl.addWidget(refresh_btn)

        layout.addWidget(crop_bar)

        splitter = QSplitter(Qt.Vertical)

        # --- Stats table ---
        table_w = QWidget()
        tl = QVBoxLayout(table_w)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(4)

        title = QLabel("COLUMN STATISTICS")
        title.setStyleSheet(
            f"color:{C['text2']}; font-size:11px; font-weight:700; "
            f"letter-spacing:1.5px; background:transparent; "
            f"border:none; border-bottom:2px solid rgba(76,158,255,0.30); "
            f"padding-bottom:4px; margin-bottom:2px;")
        tl.addWidget(title)

        self._table = QTableWidget()
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.itemSelectionChanged.connect(self._on_row_selected)
        tl.addWidget(self._table)
        splitter.addWidget(table_w)

        # --- Visualization sub-tabs ---
        self._viz_tabs = QTabWidget()

        # Histogram + CDF
        hist_w = QWidget()
        hl = QVBoxLayout(hist_w)
        hl.setContentsMargins(4, 6, 4, 4)
        hl.setSpacing(4)
        self._hist_plot = CrosshairPlotWidget()
        self._hist_plot.setTitle("Distribution", color=C['text1'], size='10pt')
        self._hist_plot.setLabel('bottom', 'Value')
        self._hist_plot.setLabel('left', 'Count')
        hl.addWidget(ZoomToolbar(self._hist_plot, with_y_lock=False))
        hl.addWidget(self._hist_plot, 1)

        # Normality info
        self._norm_label = QLabel("")
        self._norm_label.setStyleSheet(
            f"color:{C['text1']}; font-size:10px; font-family:monospace; "
            f"background:rgba(30,34,55,0.95); "
            f"border:1px solid rgba(255,255,255,0.10); "
            f"border-left:2px solid {C['teal']}; "
            f"border-radius:4px; padding:6px 10px;")
        hl.addWidget(self._norm_label)
        self._viz_tabs.addTab(hist_w, "Histogram")

        # Box plot comparison
        box_w = QWidget()
        bl = QVBoxLayout(box_w)
        bl.setContentsMargins(4, 6, 4, 4)
        bl.setSpacing(4)
        self._box_plot = CrosshairPlotWidget()
        self._box_plot.setTitle("Box Plot Comparison", color=C['text1'], size='10pt')
        self._box_plot.setLabel('bottom', 'Column')
        self._box_plot.setLabel('left', 'Value')
        bl.addWidget(ZoomToolbar(self._box_plot, with_y_lock=False))
        bl.addWidget(self._box_plot, 1)
        self._viz_tabs.addTab(box_w, "Box Plot")

        # Q-Q plot
        qq_w = QWidget()
        ql = QVBoxLayout(qq_w)
        ql.setContentsMargins(4, 6, 4, 4)
        ql.setSpacing(4)
        self._qq_plot = CrosshairPlotWidget()
        self._qq_plot.setTitle("Q-Q Plot (Normal)", color=C['text1'], size='10pt')
        self._qq_plot.setLabel('bottom', 'Theoretical Quantiles')
        self._qq_plot.setLabel('left', 'Sample Quantiles')
        ql.addWidget(self._qq_plot, 1)
        self._viz_tabs.addTab(qq_w, "Q-Q Plot")

        splitter.addWidget(self._viz_tabs)
        splitter.setSizes([320, 330])
        layout.addWidget(splitter, 1)

    def set_columns(self, columns: set):
        self._selected_columns = columns

    def _set_crop(self, start, end):
        if start is not None:
            self._crop_start = start
        if end is not None:
            self._crop_end = end

    def _reset_crop(self):
        self._start_spin.setValue(0)
        self._end_spin.setValue(-1)
        self._crop_start = 0
        self._crop_end = -1
        self.refresh()

    def refresh(self):
        self._table.clear()
        self._hist_plot.clear()
        self._box_plot.clear()
        self._qq_plot.clear()
        self._norm_label.setText("")

        if not self._dm.files or not self._selected_columns:
            self._table.setRowCount(0)
            return

        remove_outliers = self._outlier_cb.isChecked()

        stat_keys = ['count', 'mean', 'std', 'min', 'q1', 'median', 'q3', 'max',
                     'rms', 'p2p', 'iqr', 'cv', 'skewness', 'kurtosis']
        headers = ["File", "Column"] + [k.upper() for k in stat_keys]
        self._table.setColumnCount(len(headers))
        self._table.setHorizontalHeaderLabels(headers)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)

        rows_data = []
        for lf in self._dm.files:
            for col in sorted(self._selected_columns):
                if col not in lf.df.columns:
                    continue
                y = lf.df[col].values.astype(np.float64)
                s = self._crop_start
                e = self._crop_end if self._crop_end > 0 else len(y)
                e = min(e, len(y))
                y_crop = y[s:e]

                if remove_outliers:
                    y_crop = DataManager.remove_outliers(y_crop, method='iqr')
                    y_crop = y_crop[np.isfinite(y_crop)]

                stats = DataManager.compute_stats(y_crop)
                norm = DataManager.normality_test(y_crop)
                rows_data.append((lf.name, lf.color, col, stats, y_crop, norm))

        self._table.setRowCount(len(rows_data))
        self._rows_data = rows_data

        for ri, (fname, color, col, stats, _, norm) in enumerate(rows_data):
            self._table.setItem(ri, 0, QTableWidgetItem(fname))
            self._table.setItem(ri, 1, QTableWidgetItem(col))
            for ci, key in enumerate(stat_keys):
                val = stats.get(key, 0)
                fmt = f"{val:.4f}" if key != 'count' else f"{int(val)}"
                item = QTableWidgetItem(fmt)
                item.setTextAlignment(Qt.AlignCenter)

                # Color-code skewness/kurtosis
                if key == 'skewness' and abs(val) > 1.0:
                    item.setForeground(pg.mkColor(C['amber']))
                elif key == 'kurtosis' and abs(val) > 2.0:
                    item.setForeground(pg.mkColor(C['amber']))

                self._table.setItem(ri, ci + 2, item)

        # Show first row by default
        if rows_data:
            self._show_histogram(0)
            self._show_box_plots()

    def _on_row_selected(self):
        rows = self._table.selectionModel().selectedRows()
        if rows:
            self._show_histogram(rows[0].row())

    def _show_histogram(self, row_idx: int):
        self._hist_plot.clear()
        self._qq_plot.clear()
        self._norm_label.setText("")

        if row_idx >= len(self._rows_data):
            return

        fname, color, col, stats, y_crop, norm = self._rows_data[row_idx]
        valid = y_crop[np.isfinite(y_crop)]
        if len(valid) < 2:
            return

        # Histogram - use Sturges' rule for bin count
        n_bins = min(100, max(10, int(np.ceil(np.log2(len(valid)) + 1)) * 2))
        hist, edges = np.histogram(valid, bins=n_bins)
        centers = (edges[:-1] + edges[1:]) / 2
        width = (edges[1] - edges[0]) * 0.85

        bg = pg.BarGraphItem(x=centers, height=hist, width=width,
                             brush=QColor(color), pen=pg.mkPen(None))
        self._hist_plot.addItem(bg)

        # Overlay: Gaussian fit
        x_fit = np.linspace(edges[0], edges[-1], 200)
        gaussian = (len(valid) * (edges[1] - edges[0]) /
                    (stats['std'] * np.sqrt(2 * np.pi)) *
                    np.exp(-0.5 * ((x_fit - stats['mean']) / stats['std']) ** 2))
        self._hist_plot.plot(x_fit, gaussian,
            pen=pg.mkPen(C['amber'], width=2, style=Qt.DashLine), name="Normal fit")

        # CDF overlay (secondary axis via scaling)
        sorted_v = np.sort(valid)
        cdf = np.arange(1, len(sorted_v) + 1) / len(sorted_v)
        cdf_scaled = cdf * np.max(hist)
        self._hist_plot.plot(sorted_v, cdf_scaled,
            pen=pg.mkPen(C['teal'], width=2), name="CDF")

        # Reference lines
        for val, label, lcolor, style in [
            (stats['mean'], f"μ={stats['mean']:.2f}", C['red'], Qt.DashLine),
            (stats['median'], f"Med={stats['median']:.2f}", C['purple'], Qt.DotLine),
            (stats['q1'], "Q1", C['muted'], Qt.DotLine),
            (stats['q3'], "Q3", C['muted'], Qt.DotLine),
        ]:
            line = pg.InfiniteLine(pos=val, angle=90,
                pen=pg.mkPen(lcolor, width=1.5, style=style),
                label=label,
                labelOpts={'color': lcolor, 'position': 0.9, 'anchors': [(0, 0), (0, 0)]})
            self._hist_plot.addItem(line)

        self._hist_plot.setTitle(f"{fname}: {col}", color=C['text1'], size='10pt')
        self._hist_plot.enableAutoRange()

        # Normality info
        is_normal = norm.get('is_normal', False)
        test_name = norm.get('test', 'unknown')
        p_val = norm.get('shapiro_p', 0)
        norm_str = "NORMAL" if is_normal else "NON-NORMAL"
        norm_color = C['green'] if is_normal else C['amber']

        info = (f"  n={stats['count']}  |  μ={stats['mean']:.3f}  σ={stats['std']:.3f}  |  "
                f"Skew={stats['skewness']:.3f}  Kurt={stats['kurtosis']:.3f}  |  "
                f"CV={stats['cv']:.1f}%  |  ")
        if test_name == 'shapiro':
            info += f"Shapiro p={p_val:.4f}  "
        info += f"[{norm_str}]"
        self._norm_label.setText(info)
        self._norm_label.setStyleSheet(
            f"color:{norm_color}; font-size:10px; font-family:monospace; "
            f"background:rgba(30,34,55,0.95); "
            f"border:1px solid rgba(255,255,255,0.10); "
            f"border-left:2px solid {norm_color}; "
            f"border-radius:4px; padding:6px 10px;")

        # Q-Q plot
        self._show_qq(valid, color, col)

    def _show_qq(self, data, color, col):
        """Normal Q-Q plot."""
        self._qq_plot.clear()
        n = len(data)
        if n < 4:
            return

        sorted_data = np.sort(data)
        # Theoretical quantiles
        probs = (np.arange(1, n + 1) - 0.5) / n
        # Inverse normal CDF approximation (Beasley-Springer-Moro)
        z = np.zeros(n)
        for i, p in enumerate(probs):
            z[i] = self._inv_norm(p)

        self._qq_plot.plot(z, sorted_data, pen=pg.mkPen(None),
            symbol='o', symbolSize=3, symbolBrush=pg.mkBrush(color),
            symbolPen=pg.mkPen(None))

        # Reference line (if data were perfectly normal)
        mean, std = np.mean(data), np.std(data)
        z_range = np.array([z[0], z[-1]])
        ref_line = mean + std * z_range
        self._qq_plot.plot(z_range, ref_line,
            pen=pg.mkPen(C['red'], width=2, style=Qt.DashLine), name="Normal reference")

        self._qq_plot.setTitle(f"Q-Q Plot: {col}", color=C['text1'], size='10pt')
        self._qq_plot.enableAutoRange()

    @staticmethod
    def _inv_norm(p):
        """Approximate inverse normal CDF (rational approx)."""
        if p <= 0:
            return -4.0
        if p >= 1:
            return 4.0
        if p < 0.5:
            t = np.sqrt(-2.0 * np.log(p))
            return -(2.515517 + t * (0.802853 + t * 0.010328)) / \
                    (1.0 + t * (1.432788 + t * (0.189269 + t * 0.001308)))
        else:
            t = np.sqrt(-2.0 * np.log(1 - p))
            return (2.515517 + t * (0.802853 + t * 0.010328)) / \
                   (1.0 + t * (1.432788 + t * (0.189269 + t * 0.001308)))

    def _show_box_plots(self):
        """Draw box plots for all selected columns across all files."""
        self._box_plot.clear()

        if not self._rows_data:
            return

        x_labels = []
        x_pos = 0
        tick_positions = []

        for ri, (fname, color, col, stats, y_crop, _) in enumerate(self._rows_data):
            valid = y_crop[np.isfinite(y_crop)]
            if len(valid) < 4:
                continue

            q1 = stats['q1']
            q3 = stats['q3']
            med = stats['median']
            iqr = stats['iqr']
            whisker_lo = max(stats['min'], q1 - 1.5 * iqr)
            whisker_hi = min(stats['max'], q3 + 1.5 * iqr)

            w = 0.35

            # Box (Q1 to Q3)
            box = pg.BarGraphItem(x=[x_pos], height=[q3 - q1], y0=[q1], width=w * 2,
                                   brush=QColor(color), pen=pg.mkPen(C['text2'], width=1))
            self._box_plot.addItem(box)

            # Median line
            self._box_plot.plot([x_pos - w, x_pos + w], [med, med],
                pen=pg.mkPen(C['text1'], width=2))

            # Whiskers
            self._box_plot.plot([x_pos, x_pos], [whisker_lo, q1],
                pen=pg.mkPen(C['text2'], width=1))
            self._box_plot.plot([x_pos, x_pos], [q3, whisker_hi],
                pen=pg.mkPen(C['text2'], width=1))
            # Whisker caps
            cap_w = w * 0.6
            self._box_plot.plot([x_pos - cap_w, x_pos + cap_w], [whisker_lo, whisker_lo],
                pen=pg.mkPen(C['text2'], width=1))
            self._box_plot.plot([x_pos - cap_w, x_pos + cap_w], [whisker_hi, whisker_hi],
                pen=pg.mkPen(C['text2'], width=1))

            # Outliers
            outliers = valid[(valid < whisker_lo) | (valid > whisker_hi)]
            if len(outliers) > 0 and len(outliers) < 200:
                self._box_plot.plot(
                    np.full(len(outliers), x_pos), outliers,
                    pen=pg.mkPen(None), symbol='o', symbolSize=3,
                    symbolBrush=pg.mkBrush(C['red']), symbolPen=pg.mkPen(None))

            short_name = f"{col[:12]}\n({fname[:8]})"
            tick_positions.append((x_pos, short_name))
            x_pos += 1

        if tick_positions:
            ax = self._box_plot.getAxis('bottom')
            ax.setTicks([tick_positions])

        self._box_plot.enableAutoRange()
