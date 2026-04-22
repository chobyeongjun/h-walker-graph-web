"""
Chart Tab - Multi-file overlay + subplot mode + crosshair + MATLAB commands
Enhanced: data cursor snap, peak/valley markers, dual Y-axis, cmd history, more math ops
"""

import os
import numpy as np
import pyqtgraph as pg
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QCheckBox, QLineEdit, QComboBox, QCompleter,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from styles import C, SERIES_COLORS
from widgets import (
    CrosshairPlotWidget, LinkedPlotContainer,
    ZoomToolbar, LabelEditors, MathOpSelector,
)
from data_manager import DataManager

PEN_STYLES = [Qt.SolidLine, Qt.DashLine, Qt.DotLine, Qt.DashDotLine]


class ChartTab(QWidget):
    """Main charting tab with overlay and subplot modes."""

    def __init__(self, data_mgr: DataManager, parent=None):
        super().__init__(parent)
        self._dm = data_mgr
        self._line_width = 2.0
        self._legend_size = '11pt'
        self._subplot_mode = False
        self._selected_columns: set = set()
        self._right_axis_columns: set = set()  # columns assigned to right Y-axis
        self._x_axis_mode = 'index'
        self._math_op = ("None", {})
        self._show_peaks = False
        self._show_valleys = False
        self._cmd_history: list[str] = []
        self._cmd_history_idx = -1
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(4, 4, 4, 4)

        # Top controls bar
        ctrl = QFrame()
        ctrl.setObjectName("GlassCard")
        ctrl.setFixedHeight(44)
        ctrl.setStyleSheet(
            "QFrame#GlassCard { border-left: 2px solid rgba(76,158,255,0.30); }")
        cl = QHBoxLayout(ctrl)
        cl.setContentsMargins(10, 0, 10, 0)
        cl.setSpacing(4)

        # View mode selector
        self._view_combo = QComboBox()
        self._view_combo.addItems(["Overlay", "Subplot", "Mean\u00b1SD Band", "Mean\u00b1SD Bar"])
        self._view_combo.setFixedWidth(120)
        self._view_combo.setToolTip(
            "Overlay: 원본 데이터 겹쳐 그리기\n"
            "Subplot: 컬럼별 분리 그래프\n"
            "Mean\u00b1SD Band: 평균선 + 표준편차 영역\n"
            "Mean\u00b1SD Bar: 평균 막대 + 표준편차 에러바")
        self._view_combo.currentIndexChanged.connect(self._on_view_changed)
        cl.addWidget(self._view_combo)

        cl.addSpacing(6)

        # Crosshair toggle
        self._crosshair_btn = QPushButton("\u253c Crosshair")
        self._crosshair_btn.setCheckable(True)
        self._crosshair_btn.setChecked(True)
        self._crosshair_btn.setObjectName("ToolbarBtn")
        self._crosshair_btn.setToolTip("십자선 커서 On/Off")
        self._crosshair_btn.toggled.connect(self._toggle_crosshair)
        cl.addWidget(self._crosshair_btn)

        # Peak/Valley markers
        self._peaks_btn = QPushButton("\u25b2 Peaks")
        self._peaks_btn.setCheckable(True)
        self._peaks_btn.setChecked(False)
        self._peaks_btn.setObjectName("ToolbarBtn")
        self._peaks_btn.setToolTip("피크(최대값) 마커 표시")
        self._peaks_btn.toggled.connect(self._toggle_peaks)
        cl.addWidget(self._peaks_btn)

        self._valleys_btn = QPushButton("\u25bc Valleys")
        self._valleys_btn.setCheckable(True)
        self._valleys_btn.setChecked(False)
        self._valleys_btn.setObjectName("ToolbarBtn")
        self._valleys_btn.setToolTip("밸리(최소값) 마커 표시")
        self._valleys_btn.toggled.connect(self._toggle_valleys)
        cl.addWidget(self._valleys_btn)

        cl.addSpacing(4)

        # Right Y-axis toggle
        self._raxis_btn = QPushButton("Right Y")
        self._raxis_btn.setCheckable(True)
        self._raxis_btn.setObjectName("ToolbarBtn")
        self._raxis_btn.setToolTip("선택된 컬럼을 오른쪽 Y축에 배치 (스케일 다른 데이터 비교)")
        self._raxis_btn.toggled.connect(self._toggle_right_axis)
        cl.addWidget(self._raxis_btn)

        cl.addSpacing(4)

        # Math operation
        self._math_sel = MathOpSelector()
        self._math_sel.op_changed.connect(self._on_math_changed)
        cl.addWidget(self._math_sel)

        cl.addStretch()

        # Cursor value display (snap to data)
        self._cursor_info = QLabel("")
        self._cursor_info.setStyleSheet(
            f"color:{C['teal']}; font-size:10px; font-family:monospace; "
            f"background:rgba(255,255,255,0.03); "
            f"border:1px solid rgba(255,255,255,0.06); "
            f"border-left:2px solid {C['teal']}; "
            f"border-radius:4px; padding:2px 8px;")
        self._cursor_info.setMinimumWidth(0)
        self._cursor_info.setVisible(False)
        cl.addWidget(self._cursor_info)

        cl.addSpacing(8)

        # Legend bar
        self._legend_frame = QFrame()
        ll = QHBoxLayout(self._legend_frame)
        ll.setContentsMargins(4, 0, 4, 0)
        ll.setSpacing(8)
        self._legend_layout = ll
        cl.addWidget(self._legend_frame)

        layout.addWidget(ctrl)

        # Overlay plot (single plot mode)
        self._overlay_plot = CrosshairPlotWidget()
        self._overlay_plot.addLegend(offset=(10, 10), labelTextSize=self._legend_size)
        self._overlay_plot.cursor_moved.connect(self._on_cursor_snap)
        self._overlay_toolbar = ZoomToolbar(
            self._overlay_plot, with_line_controls=True)
        self._overlay_toolbar.linewidth_changed.connect(self._on_lw)
        self._overlay_toolbar.legend_size_changed.connect(self._on_lg)
        self._overlay_labels = LabelEditors(self._overlay_plot)

        # Subplot container (multi-plot mode)
        self._subplot_container = LinkedPlotContainer()

        # Stack: show one at a time
        self._plot_stack = QWidget()
        self._stack_layout = QVBoxLayout(self._plot_stack)
        self._stack_layout.setContentsMargins(0, 0, 0, 0)
        self._stack_layout.setSpacing(2)
        self._stack_layout.addWidget(self._overlay_toolbar)
        self._stack_layout.addWidget(self._overlay_plot, 1)
        self._stack_layout.addWidget(self._overlay_labels)
        self._stack_layout.addWidget(self._subplot_container)
        self._subplot_container.hide()

        layout.addWidget(self._plot_stack, 1)

        # MATLAB command bar with history
        cmd_bar = QFrame()
        cmd_bar.setObjectName("GlassCard")
        cmd_bar.setFixedHeight(36)
        cmd_bar.setStyleSheet(
            "QFrame#GlassCard { border-left: 2px solid rgba(76,158,255,0.30); }")
        cmd_l = QHBoxLayout(cmd_bar)
        cmd_l.setContentsMargins(10, 0, 10, 0)
        prompt = QLabel(">>")
        prompt.setStyleSheet(
            f"color:{C['blue']}; font-size:12px; font-weight:700; "
            f"font-family:monospace; background:transparent; border:none;")
        cmd_l.addWidget(prompt)
        self._cmd_input = QLineEdit()
        self._cmd_input.setPlaceholderText(
            "ylim [-10 120] | xlim [0 5000] | grid on | title \"text\" | peaks on | "
            "butter 5 | savgol 21 | normalize zscore")
        self._cmd_input.setStyleSheet(
            f"background:transparent; border:none; color:{C['text1']}; "
            f"font-family:monospace; font-size:11px;")
        self._cmd_input.returnPressed.connect(self._exec_cmd)

        # Command autocomplete
        cmds = ["ylim", "xlim", "grid", "title", "ylabel", "xlabel",
                "linewidth", "legend", "auto", "autorange", "subplot",
                "peaks", "valleys", "butter", "savgol", "normalize",
                "clear", "help", "copy", "snap"]
        completer = QCompleter(cmds)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._cmd_input.setCompleter(completer)

        cmd_l.addWidget(self._cmd_input, 1)

        # History count
        self._hist_label = QLabel("")
        self._hist_label.setStyleSheet(
            f"color:{C['muted']}; font-size:9px; background:transparent; border:none;")
        cmd_l.addWidget(self._hist_label)

        layout.addWidget(cmd_bar)

        # Store plotted data for cursor snap
        self._plotted_data: list[tuple] = []  # [(x, y, name, color), ...]
        self._right_vb = None
        self._right_axis = None

    # ---- public API ----

    def set_columns(self, columns: set):
        self._selected_columns = columns
        self.refresh()

    def set_x_axis(self, mode: str):
        self._x_axis_mode = mode
        self.refresh()

    def refresh(self):
        view = self._view_combo.currentIndex()
        if view == 1:  # Subplot
            self._subplot_mode = True
            self._refresh_subplot()
        elif view == 2:  # Mean±SD Band
            self._subplot_mode = False
            self._refresh_mean_sd_band()
        elif view == 3:  # Mean±SD Bar
            self._subplot_mode = False
            self._refresh_mean_sd_bar()
        else:  # Overlay
            self._subplot_mode = False
            self._refresh_overlay()
        self._update_legend()

    # ---- overlay mode ----

    def _refresh_overlay(self):
        self._overlay_plot.clear()
        self._overlay_plot.addLegend(offset=(10, 10), labelTextSize=self._legend_size)
        self._plotted_data.clear()

        # Remove old right-axis viewbox if exists
        if hasattr(self, '_right_vb') and self._right_vb is not None:
            self._overlay_plot.scene().removeItem(self._right_vb)
            self._right_vb = None
        if hasattr(self, '_right_axis') and self._right_axis is not None:
            self._overlay_plot.plotItem.layout.removeItem(self._right_axis)
            self._right_axis = None

        if not self._dm.files or not self._selected_columns:
            return

        lw = self._line_width
        single_file = len(self._dm.files) == 1
        sorted_cols = sorted(self._selected_columns)
        has_right = bool(self._right_axis_columns & self._selected_columns)

        # Setup right Y-axis if needed
        right_vb = None
        if has_right:
            right_vb = pg.ViewBox()
            self._right_vb = right_vb
            ax = pg.AxisItem('right')
            ax.setLabel('Right Axis', color=C['purple'])
            ax.setPen(pg.mkPen(C['purple'], width=1))
            self._right_axis = ax
            self._overlay_plot.plotItem.layout.addItem(ax, 2, 3)
            self._overlay_plot.scene().addItem(right_vb)
            ax.linkToView(right_vb)
            right_vb.setXLink(self._overlay_plot)

            # Sync geometry on resize
            def update_views():
                right_vb.setGeometry(self._overlay_plot.getViewBox().sceneBoundingRect())
            self._overlay_plot.getViewBox().sigResized.connect(update_views)
            update_views()

        for lf in self._dm.files:
            pen_style = PEN_STYLES[lf.style_idx]
            for ci, col in enumerate(sorted_cols):
                if col not in lf.df.columns:
                    continue
                y = lf.df[col].values.astype(np.float64)
                y = self._apply_math(y, lf.df)
                x = self._get_x(lf.df, len(y))

                # When only one file loaded, use different colors per column
                if single_file:
                    color = SERIES_COLORS[ci % len(SERIES_COLORS)]
                else:
                    color = lf.color

                pen = pg.mkPen(color, width=lw, style=pen_style)
                name = f"{lf.name}: {col}"

                # Plot on right axis or left axis
                if col in self._right_axis_columns and right_vb is not None:
                    curve = pg.PlotCurveItem(x, y, pen=pen, name=name + " [R]")
                    right_vb.addItem(curve)
                else:
                    self._overlay_plot.plot(x, y, pen=pen, name=name)

                # Store for cursor snap
                self._plotted_data.append((x, y, name, color))

                # Peak/valley markers
                if self._show_peaks:
                    self._add_peak_markers(x, y, color)
                if self._show_valleys:
                    self._add_valley_markers(x, y, color)

        self._overlay_plot.enableAutoRange()
        if right_vb is not None:
            right_vb.enableAutoRange()

    # ---- subplot mode ----

    def _refresh_subplot(self):
        self._subplot_container.clear_plots()
        self._plotted_data.clear()

        if not self._dm.files or not self._selected_columns:
            return

        lw = self._line_width
        for col in sorted(self._selected_columns):
            plot = self._subplot_container.add_plot(col)
            for lf in self._dm.files:
                if col not in lf.df.columns:
                    continue
                y = lf.df[col].values.astype(np.float64)
                y = self._apply_math(y, lf.df)
                x = self._get_x(lf.df, len(y))
                pen = pg.mkPen(lf.color, width=lw, style=PEN_STYLES[lf.style_idx])
                plot.plot(x, y, pen=pen, name=lf.name)

                if self._show_peaks:
                    self._add_peak_markers(x, y, lf.color, plot=plot)
                if self._show_valleys:
                    self._add_valley_markers(x, y, lf.color, plot=plot)

            plot.enableAutoRange()

    # ---- Mean±SD Band mode ----

    def _refresh_mean_sd_band(self):
        """Mean line (solid dark) + ±SD shaded band (lighter) per column."""
        self._overlay_plot.clear()
        self._overlay_plot.addLegend(offset=(10, 10), labelTextSize=self._legend_size)
        self._plotted_data.clear()

        if not self._dm.files or not self._selected_columns:
            return

        sorted_cols = sorted(self._selected_columns)

        for ci, col in enumerate(sorted_cols):
            # Collect data from all files for this column
            all_arrays = []
            for lf in self._dm.files:
                if col not in lf.df.columns:
                    continue
                y = lf.df[col].values.astype(np.float64)
                y = self._apply_math(y, lf.df)
                all_arrays.append(y)

            if not all_arrays:
                continue

            color = SERIES_COLORS[ci % len(SERIES_COLORS)]

            if len(all_arrays) == 1:
                # Single file: compute rolling mean±SD with window
                y = all_arrays[0]
                x = np.arange(len(y), dtype=np.float64)
                win = max(5, len(y) // 50)
                mean = np.convolve(y, np.ones(win) / win, mode='same')
                std = np.array([np.std(y[max(0, i - win // 2):i + win // 2 + 1])
                               for i in range(len(y))])
            else:
                # Multi-file: truncate to shortest, compute point-wise mean±SD
                min_len = min(len(a) for a in all_arrays)
                stacked = np.array([a[:min_len] for a in all_arrays])
                x = np.arange(min_len, dtype=np.float64)
                mean = np.mean(stacked, axis=0)
                std = np.std(stacked, axis=0)

            upper = mean + std
            lower = mean - std

            # Shaded ±SD band
            fill_color = QColor(color)
            fill_color.setAlpha(40)
            upper_curve = pg.PlotDataItem(x, upper, pen=pg.mkPen(None))
            lower_curve = pg.PlotDataItem(x, lower, pen=pg.mkPen(None))
            fill = pg.FillBetweenItem(upper_curve, lower_curve, brush=pg.mkBrush(fill_color))
            self._overlay_plot.addItem(upper_curve)
            self._overlay_plot.addItem(lower_curve)
            self._overlay_plot.addItem(fill)

            # Mean line (solid, thicker)
            n_label = f" (n={len(all_arrays)})" if len(all_arrays) > 1 else ""
            self._overlay_plot.plot(x, mean,
                pen=pg.mkPen(color, width=2.5),
                name=f"{col} mean{n_label}")

            # ±SD boundary lines (thin, dashed)
            sd_pen = pg.mkPen(color, width=1, style=Qt.DashLine)
            self._overlay_plot.plot(x, upper, pen=sd_pen)
            self._overlay_plot.plot(x, lower, pen=sd_pen)

            self._plotted_data.append((x, mean, f"{col} mean", color))

        self._overlay_plot.enableAutoRange()

    # ---- Mean±SD Bar mode ----

    def _refresh_mean_sd_bar(self):
        """Bar chart: mean as solid bar + SD as error bar range."""
        self._overlay_plot.clear()
        self._overlay_plot.addLegend(offset=(10, 10), labelTextSize=self._legend_size)
        self._plotted_data.clear()

        if not self._dm.files or not self._selected_columns:
            return

        sorted_cols = sorted(self._selected_columns)
        n_cols = len(sorted_cols)
        bar_width = 0.6

        x_ticks = []
        means = []
        stds = []
        colors = []

        for ci, col in enumerate(sorted_cols):
            all_vals = []
            for lf in self._dm.files:
                if col not in lf.df.columns:
                    continue
                y = lf.df[col].values.astype(np.float64)
                y = self._apply_math(y, lf.df)
                y = y[~np.isnan(y)]
                all_vals.extend(y.tolist())

            if not all_vals:
                continue

            arr = np.array(all_vals)
            m = np.mean(arr)
            s = np.std(arr)
            color = SERIES_COLORS[ci % len(SERIES_COLORS)]

            means.append(m)
            stds.append(s)
            colors.append(color)
            x_ticks.append((ci, col))

        if not means:
            return

        # Draw bars
        for i, (m, s, color) in enumerate(zip(means, stds, colors)):
            # Main bar (mean)
            bar_color = QColor(color)
            bar_color.setAlpha(180)
            bar = pg.BarGraphItem(
                x=[i], height=[m], width=bar_width,
                brush=pg.mkBrush(bar_color),
                pen=pg.mkPen(color, width=1.5))
            self._overlay_plot.addItem(bar)

            # SD range as error bar (lighter color box)
            sd_color = QColor(color)
            sd_color.setAlpha(60)
            sd_bar = pg.BarGraphItem(
                x=[i], y0=[m - s], height=[2 * s], width=bar_width * 0.5,
                brush=pg.mkBrush(sd_color),
                pen=pg.mkPen(color, width=1, style=Qt.DashLine))
            self._overlay_plot.addItem(sd_bar)

            # Error bar lines (whiskers)
            err_pen = pg.mkPen(color, width=2)
            self._overlay_plot.plot([i, i], [m - s, m + s], pen=err_pen)
            # Whisker caps
            cap_w = bar_width * 0.3
            self._overlay_plot.plot([i - cap_w, i + cap_w], [m + s, m + s], pen=err_pen)
            self._overlay_plot.plot([i - cap_w, i + cap_w], [m - s, m - s], pen=err_pen)

        # Set x-axis tick labels
        ax = self._overlay_plot.getAxis('bottom')
        ax.setTicks([x_ticks])
        self._overlay_plot.setLabel('bottom', 'Columns')
        self._overlay_plot.setLabel('left', 'Value')
        self._overlay_plot.setTitle('Mean \u00b1 SD', color=C['text1'], size='11pt')
        self._overlay_plot.enableAutoRange()

    # ---- peak/valley markers ----

    def _add_peak_markers(self, x, y, color, plot=None):
        p = plot or self._overlay_plot
        try:
            idx, vals = DataManager.find_peaks(y, distance=max(5, len(y) // 100))
            if len(idx) > 0:
                p.plot(x[idx], vals, pen=pg.mkPen(None),
                       symbol='t', symbolSize=8,
                       symbolBrush=pg.mkBrush(C['amber']),
                       symbolPen=pg.mkPen(C['amber'], width=1))
        except Exception:
            pass

    def _add_valley_markers(self, x, y, color, plot=None):
        p = plot or self._overlay_plot
        try:
            idx, vals = DataManager.find_valleys(y, distance=max(5, len(y) // 100))
            if len(idx) > 0:
                p.plot(x[idx], vals, pen=pg.mkPen(None),
                       symbol='t1', symbolSize=8,
                       symbolBrush=pg.mkBrush(C['teal']),
                       symbolPen=pg.mkPen(C['teal'], width=1))
        except Exception:
            pass

    # ---- data cursor snap ----

    def _on_cursor_snap(self, cx, cy):
        """Find nearest data point to cursor and display values."""
        if not self._plotted_data:
            return

        best_name = ""
        best_dist = float('inf')
        best_x, best_y = 0, 0
        best_color = C['text2']

        for x_data, y_data, name, color in self._plotted_data:
            if len(x_data) == 0:
                continue
            # Find nearest x index
            idx = np.searchsorted(x_data, cx)
            idx = np.clip(idx, 0, len(x_data) - 1)
            # Check neighbors
            for di in [-1, 0, 1]:
                i = idx + di
                if 0 <= i < len(x_data):
                    dist = abs(x_data[i] - cx)
                    if dist < best_dist:
                        best_dist = dist
                        best_x = x_data[i]
                        best_y = y_data[i]
                        best_name = name
                        best_color = color

        if best_name:
            self._cursor_info.setVisible(True)
            self._cursor_info.setText(
                f"[{best_name}]  x={best_x:.1f}  y={best_y:.4f}")
            self._cursor_info.setStyleSheet(
                f"color:{best_color}; font-size:10px; font-family:monospace; "
                f"background:rgba(255,255,255,0.03); "
                f"border:1px solid rgba(255,255,255,0.06); "
                f"border-left:2px solid {best_color}; "
                f"border-radius:4px; padding:2px 8px;")

    # ---- helpers ----

    def _get_x(self, df, length: int) -> np.ndarray:
        if self._x_axis_mode == 'gcp' and 'L_GCP' in df.columns:
            x = df['L_GCP'].values.astype(np.float64) * 100
            return x[:length]
        return np.arange(length, dtype=np.float64)

    def _apply_math(self, y: np.ndarray, df) -> np.ndarray:
        name, params = self._math_op
        if name == "None":
            return y
        elif name == "Derivative":
            dt = 1.0 / DataManager.estimate_sample_rate(df)
            return DataManager.derivative(y, dt)
        elif name.startswith("Moving Average"):
            return DataManager.moving_average(y, params.get("window", 10))
        elif name.startswith("Lowpass"):
            return DataManager.lowpass_filter(y, params.get("cutoff", 0.1))
        elif name == "Integrate":
            dt = 1.0 / DataManager.estimate_sample_rate(df)
            return DataManager.integrate(y, dt)
        elif name.startswith("Butterworth"):
            fs = DataManager.estimate_sample_rate(df)
            return DataManager.butterworth_filter(y, params.get("cutoff_hz", 10), fs)
        elif name.startswith("Savgol"):
            return DataManager.savgol_filter(y, params.get("window", 21), params.get("order", 3))
        elif name.startswith("Normalize"):
            return DataManager.normalize(y, params.get("method", "zscore"))
        return y

    def _update_legend(self):
        while self._legend_layout.count():
            item = self._legend_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        style_chars = ["───", "- - -", "· · ·", "─·─"]
        single_file = len(self._dm.files) == 1

        if single_file and self._selected_columns:
            # Show per-column legend with distinct colors
            sorted_cols = sorted(self._selected_columns)
            lf = self._dm.files[0]
            for ci, col in enumerate(sorted_cols):
                if col not in lf.df.columns:
                    continue
                color = SERIES_COLORS[ci % len(SERIES_COLORS)]
                lbl = QLabel(f"{style_chars[lf.style_idx]} {col}")
                lbl.setStyleSheet(
                    f"color:{color}; font-size:10px; font-weight:600; "
                    f"background:transparent; border:none;")
                self._legend_layout.addWidget(lbl)
        else:
            for lf in self._dm.files:
                lbl = QLabel(f"{style_chars[lf.style_idx]} {lf.name}")
                lbl.setStyleSheet(
                    f"color:{lf.color}; font-size:10px; font-weight:600; "
                    f"background:transparent; border:none;")
                self._legend_layout.addWidget(lbl)

    def _on_view_changed(self, idx):
        """Switch between Overlay / Subplot / Mean±SD modes."""
        is_subplot = (idx == 1)
        self._overlay_plot.setVisible(not is_subplot)
        self._overlay_toolbar.setVisible(not is_subplot)
        self._overlay_labels.setVisible(not is_subplot)
        self._subplot_container.setVisible(is_subplot)
        self.refresh()

    def _toggle_crosshair(self, on: bool):
        self._overlay_plot.set_crosshair(on)
        for p in self._subplot_container.get_plots():
            p.set_crosshair(on)

    def _toggle_right_axis(self, on: bool):
        """When R-Axis is active, currently selected columns are assigned to right Y-axis."""
        if on:
            self._right_axis_columns = self._selected_columns.copy()
        else:
            self._right_axis_columns.clear()
        self.refresh()

    def _toggle_peaks(self, on: bool):
        self._show_peaks = on
        self.refresh()

    def _toggle_valleys(self, on: bool):
        self._show_valleys = on
        self.refresh()

    def _on_lw(self, val):
        self._line_width = val
        self.refresh()

    def _on_lg(self, size):
        self._legend_size = size
        self.refresh()

    def _on_math_changed(self, name, params):
        self._math_op = (name, params)
        self.refresh()

    # ---- MATLAB commands (enhanced) ----

    def _exec_cmd(self):
        cmd = self._cmd_input.text().strip()
        self._cmd_input.clear()
        if not cmd:
            return

        # Store history
        self._cmd_history.append(cmd)
        self._cmd_history_idx = len(self._cmd_history)
        self._hist_label.setText(f"[{len(self._cmd_history)}]")

        plot = self._overlay_plot
        parts = cmd.split()
        verb = parts[0].lower()

        try:
            if verb == 'ylim' and len(parts) >= 3:
                vals = [float(x.strip('[](),')) for x in parts[1:] if x.strip('[](),')]
                if len(vals) >= 2:
                    plot.setYRange(vals[0], vals[1], padding=0)
            elif verb == 'xlim' and len(parts) >= 3:
                vals = [float(x.strip('[](),')) for x in parts[1:] if x.strip('[](),')]
                if len(vals) >= 2:
                    plot.setXRange(vals[0], vals[1], padding=0)
            elif verb == 'grid':
                on = len(parts) < 2 or parts[1].lower() in ('on', 'true', '1')
                plot.showGrid(x=on, y=on, alpha=0.15 if on else 0)
            elif verb == 'title' and len(parts) >= 2:
                plot.setTitle(' '.join(parts[1:]).strip('"\''), color=C['text1'], size='11pt')
            elif verb == 'ylabel' and len(parts) >= 2:
                plot.setLabel('left', ' '.join(parts[1:]).strip('"\''))
            elif verb == 'xlabel' and len(parts) >= 2:
                plot.setLabel('bottom', ' '.join(parts[1:]).strip('"\''))
            elif verb == 'linewidth' and len(parts) >= 2:
                self._line_width = float(parts[1])
                self.refresh()
            elif verb == 'legend' and len(parts) >= 2:
                self._legend_size = parts[1] if 'pt' in parts[1] else f'{parts[1]}pt'
                self.refresh()
            elif verb in ('auto', 'autorange'):
                plot.enableAutoRange()
            elif verb == 'subplot':
                on = len(parts) >= 2 and parts[1].lower() in ('on', 'true', '1')
                self._view_combo.setCurrentIndex(1 if on else 0)
            elif verb == 'peaks':
                on = len(parts) < 2 or parts[1].lower() in ('on', 'true', '1')
                self._peaks_btn.setChecked(on)
            elif verb == 'valleys':
                on = len(parts) < 2 or parts[1].lower() in ('on', 'true', '1')
                self._valleys_btn.setChecked(on)
            elif verb == 'butter' and len(parts) >= 2:
                hz = float(parts[1])
                self._math_op = ("Butterworth", {"cutoff_hz": hz})
                self.refresh()
            elif verb == 'savgol' and len(parts) >= 2:
                win = int(parts[1])
                order = int(parts[2]) if len(parts) >= 3 else 3
                self._math_op = ("Savgol", {"window": win, "order": order})
                self.refresh()
            elif verb == 'normalize' and len(parts) >= 2:
                method = parts[1].lower()
                self._math_op = ("Normalize", {"method": method})
                self.refresh()
            elif verb == 'raw' or verb == 'reset_math':
                self._math_op = ("None", {})
                self.refresh()
            elif verb == 'clear':
                plot.clear()
                self._plotted_data.clear()
            elif verb == 'copy':
                # Copy plot to clipboard
                from PyQt5.QtWidgets import QApplication
                pixmap = plot.grab()
                QApplication.clipboard().setPixmap(pixmap)
            elif verb == 'snap':
                on = len(parts) < 2 or parts[1].lower() in ('on', 'true', '1')
                self._crosshair_btn.setChecked(on)
            elif verb == 'help':
                self._cmd_input.setPlaceholderText(
                    "ylim/xlim [min max] | grid on/off | title/ylabel/xlabel \"text\" | "
                    "linewidth N | peaks/valleys on/off | butter Hz | savgol win [order] | "
                    "normalize zscore/minmax/percent | raw | clear | copy | snap")
        except (ValueError, IndexError):
            pass

    def keyPressEvent(self, event):
        """Handle Up/Down arrow for command history."""
        if event.key() == Qt.Key_Up and self._cmd_history:
            self._cmd_history_idx = max(0, self._cmd_history_idx - 1)
            self._cmd_input.setText(self._cmd_history[self._cmd_history_idx])
        elif event.key() == Qt.Key_Down and self._cmd_history:
            self._cmd_history_idx = min(len(self._cmd_history), self._cmd_history_idx + 1)
            if self._cmd_history_idx < len(self._cmd_history):
                self._cmd_input.setText(self._cmd_history[self._cmd_history_idx])
            else:
                self._cmd_input.clear()
        else:
            super().keyPressEvent(event)

    # ---- export ----

    def get_current_plot(self) -> pg.PlotWidget:
        if self._subplot_mode:
            plots = self._subplot_container.get_plots()
            return plots[0] if plots else self._overlay_plot
        return self._overlay_plot

    def get_all_plots(self) -> list:
        if self._subplot_mode:
            return self._subplot_container.get_plots()
        return [self._overlay_plot]
