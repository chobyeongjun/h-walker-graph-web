"""
H-Walker Graph Analyzer - Custom Widgets
Crosshair, LinkedPlotContainer, ZoomToolbar, etc.
"""

import numpy as np
import pyqtgraph as pg
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QDoubleSpinBox, QComboBox, QLineEdit,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor

from styles import C


class CrosshairPlotWidget(pg.PlotWidget):
    """PlotWidget with crosshair cursor and value readout."""

    cursor_moved = pyqtSignal(float, float)  # x, y

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setBackground(C['bg'])
        self.showGrid(x=True, y=True, alpha=0.15)
        self.enableAutoRange()

        # Crosshair lines
        self._vline = pg.InfiniteLine(angle=90, movable=False,
                                       pen=pg.mkPen(C['muted'], width=1, style=Qt.DotLine))
        self._hline = pg.InfiniteLine(angle=0, movable=False,
                                       pen=pg.mkPen(C['muted'], width=1, style=Qt.DotLine))
        self.addItem(self._vline, ignoreBounds=True)
        self.addItem(self._hline, ignoreBounds=True)

        # Value label
        self._cursor_label = pg.TextItem(anchor=(0, 1), color=C['text2'])
        self._cursor_label.setFont(pg.QtGui.QFont("monospace", 9))
        self.addItem(self._cursor_label, ignoreBounds=True)

        self._crosshair_enabled = True
        self.scene().sigMouseMoved.connect(self._on_mouse_moved)

    def mouseDoubleClickEvent(self, event):
        """Double-click to reset zoom (auto-range)."""
        self.enableAutoRange()
        event.accept()

    def set_crosshair(self, enabled: bool):
        self._crosshair_enabled = enabled
        self._vline.setVisible(enabled)
        self._hline.setVisible(enabled)
        self._cursor_label.setVisible(enabled)

    def _on_mouse_moved(self, pos):
        if not self._crosshair_enabled:
            return
        vb = self.getViewBox()
        if not vb.sceneBoundingRect().contains(pos):
            return
        mouse_point = vb.mapSceneToView(pos)
        x, y = mouse_point.x(), mouse_point.y()
        self._vline.setPos(x)
        self._hline.setPos(y)
        self._cursor_label.setText(f"x={x:.1f}  y={y:.3f}")
        self._cursor_label.setPos(x, y)
        self.cursor_moved.emit(x, y)


class LinkedPlotContainer(QWidget):
    """Container for multiple vertically stacked plots with linked X-axes."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(2)
        self._plots: list[CrosshairPlotWidget] = []
        self._master_plot: CrosshairPlotWidget = None

    def add_plot(self, title: str = "") -> CrosshairPlotWidget:
        plot = CrosshairPlotWidget()
        if title:
            plot.setTitle(title, color=C['text1'], size='10pt')
        plot.addLegend(offset=(10, 5), labelTextSize='9pt')

        # Link X-axis to master
        if self._master_plot is not None:
            plot.setXLink(self._master_plot)
        else:
            self._master_plot = plot

        self._plots.append(plot)
        self._layout.addWidget(plot, 1)
        return plot

    def clear_plots(self):
        for p in self._plots:
            self._layout.removeWidget(p)
            p.deleteLater()
        self._plots.clear()
        self._master_plot = None

    def get_plots(self) -> list[CrosshairPlotWidget]:
        return self._plots

    def get_master(self) -> CrosshairPlotWidget:
        return self._master_plot


class ZoomToolbar(QFrame):
    """MATLAB-style zoom/pan toolbar with Y-lock and line width controls."""

    linewidth_changed = pyqtSignal(float)
    legend_size_changed = pyqtSignal(str)

    def __init__(self, plot_widget: pg.PlotWidget, with_y_lock=True,
                 with_line_controls=False, parent=None):
        super().__init__(parent)
        self.setObjectName("GlassCard")
        self.setFixedHeight(34)
        self._plot = plot_widget

        bl = QHBoxLayout(self)
        bl.setContentsMargins(8, 0, 8, 0)
        bl.setSpacing(4)

        zoom_btn = QPushButton("Zoom")
        zoom_btn.setCheckable(True)
        zoom_btn.setChecked(True)
        zoom_btn.setObjectName("ToolbarBtn")

        pan_btn = QPushButton("Pan")
        pan_btn.setCheckable(True)
        pan_btn.setObjectName("ToolbarBtn")

        reset_btn = QPushButton("Reset")
        reset_btn.setObjectName("SmallBtn")

        vb = plot_widget.getViewBox()
        vb.setMouseMode(pg.ViewBox.RectMode)

        def set_zoom():
            zoom_btn.setChecked(True)
            pan_btn.setChecked(False)
            vb.setMouseMode(pg.ViewBox.RectMode)

        def set_pan():
            pan_btn.setChecked(True)
            zoom_btn.setChecked(False)
            vb.setMouseMode(pg.ViewBox.PanMode)

        zoom_btn.clicked.connect(set_zoom)
        pan_btn.clicked.connect(set_pan)
        reset_btn.clicked.connect(lambda: plot_widget.enableAutoRange())

        bl.addWidget(zoom_btn)
        bl.addWidget(pan_btn)
        bl.addWidget(reset_btn)

        if with_y_lock:
            bl.addSpacing(8)
            bl.addWidget(QLabel("Y:"))

            self._y_min = QDoubleSpinBox()
            self._y_min.setRange(-100000, 100000)
            self._y_min.setValue(-100)
            self._y_min.setFixedWidth(65)
            bl.addWidget(self._y_min)
            bl.addWidget(QLabel("~"))

            self._y_max = QDoubleSpinBox()
            self._y_max.setRange(-100000, 100000)
            self._y_max.setValue(100)
            self._y_max.setFixedWidth(65)
            bl.addWidget(self._y_max)

            lock_btn = QPushButton("Lock Y")
            lock_btn.setCheckable(True)
            lock_btn.setObjectName("ToolbarBtn")

            def toggle_y(checked):
                if checked:
                    y0, y1 = self._y_min.value(), self._y_max.value()
                    if y0 < y1:
                        plot_widget.setYRange(y0, y1, padding=0)
                        vb.setMouseEnabled(x=True, y=False)
                        lock_btn.setText("Y Locked")
                else:
                    vb.setMouseEnabled(x=True, y=True)
                    plot_widget.enableAutoRange(axis='y')
                    lock_btn.setText("Lock Y")

            lock_btn.clicked.connect(toggle_y)
            bl.addWidget(lock_btn)

        if with_line_controls:
            bl.addSpacing(8)
            lw_label = QLabel("W:")
            lw_label.setStyleSheet(f"color:{C['muted']}; font-size:9px; background:transparent; border:none;")
            bl.addWidget(lw_label)

            lw_spin = QDoubleSpinBox()
            lw_spin.setRange(0.5, 6.0)
            lw_spin.setSingleStep(0.5)
            lw_spin.setValue(2.0)
            lw_spin.setFixedWidth(55)
            lw_spin.valueChanged.connect(self.linewidth_changed.emit)
            bl.addWidget(lw_spin)

            lg_label = QLabel("Lg:")
            lg_label.setStyleSheet(f"color:{C['muted']}; font-size:9px; background:transparent; border:none;")
            bl.addWidget(lg_label)

            lg_combo = QComboBox()
            lg_combo.addItems(["8pt", "10pt", "11pt", "13pt", "15pt"])
            lg_combo.setCurrentText("11pt")
            lg_combo.setFixedWidth(60)
            lg_combo.currentTextChanged.connect(self.legend_size_changed.emit)
            bl.addWidget(lg_combo)

        bl.addStretch()


class LabelEditors(QFrame):
    """Editable title, xlabel, ylabel for a chart."""

    def __init__(self, plot_widget: pg.PlotWidget, parent=None):
        super().__init__(parent)
        bl = QHBoxLayout(self)
        bl.setContentsMargins(4, 2, 4, 2)
        bl.setSpacing(8)

        yl = QLineEdit()
        yl.setPlaceholderText("Y label")
        yl.setObjectName("SearchInput")
        yl.setFixedWidth(80)
        yl.textChanged.connect(lambda t: plot_widget.setLabel('left', t))
        bl.addWidget(yl)

        tl = QLineEdit()
        tl.setPlaceholderText("Chart Title")
        tl.setObjectName("SearchInput")
        tl.setAlignment(Qt.AlignCenter)
        tl.textChanged.connect(lambda t: plot_widget.setTitle(t, color=C['text1'], size='11pt'))
        bl.addWidget(tl, 1)

        xl = QLineEdit()
        xl.setPlaceholderText("X label")
        xl.setObjectName("SearchInput")
        xl.setFixedWidth(80)
        xl.textChanged.connect(lambda t: plot_widget.setLabel('bottom', t))
        bl.addWidget(xl)


class MathOpSelector(QFrame):
    """Dropdown for selecting math operations to apply to data."""

    op_changed = pyqtSignal(str, dict)  # operation name, params

    OPERATIONS = [
        ("None", {}),
        ("Derivative", {}),
        ("Moving Average (10)", {"window": 10}),
        ("Moving Average (25)", {"window": 25}),
        ("Moving Average (50)", {"window": 50}),
        ("Lowpass 10%", {"cutoff": 0.1}),
        ("Lowpass 5%", {"cutoff": 0.05}),
        ("Lowpass 2%", {"cutoff": 0.02}),
        ("Butterworth 5Hz", {"cutoff_hz": 5}),
        ("Butterworth 10Hz", {"cutoff_hz": 10}),
        ("Butterworth 20Hz", {"cutoff_hz": 20}),
        ("Savgol (21, 3)", {"window": 21, "order": 3}),
        ("Savgol (51, 3)", {"window": 51, "order": 3}),
        ("Integrate", {}),
        ("Normalize (Z-score)", {"method": "zscore"}),
        ("Normalize (Min-Max)", {"method": "minmax"}),
        ("Normalize (% baseline)", {"method": "percent"}),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        lbl = QLabel("Math:")
        lbl.setStyleSheet(f"color:{C['text2']}; font-size:10px; font-weight:600; background:transparent; border:none;")
        layout.addWidget(lbl)

        self._combo = QComboBox()
        self._combo.setFixedWidth(140)
        for name, _ in self.OPERATIONS:
            self._combo.addItem(name)
        self._combo.currentIndexChanged.connect(self._on_changed)
        layout.addWidget(self._combo)

    def _on_changed(self, idx):
        name, params = self.OPERATIONS[idx]
        self.op_changed.emit(name, params)

    def current_op(self) -> tuple:
        idx = self._combo.currentIndex()
        return self.OPERATIONS[idx]


class ROISelector:
    """Add a draggable LinearRegionItem to a plot for region-of-interest selection."""

    region_changed = None  # Set by caller

    def __init__(self, plot_widget: pg.PlotWidget):
        self._plot = plot_widget
        self._region = pg.LinearRegionItem(
            values=[0, 100],
            brush=pg.mkBrush(76, 158, 255, 30),
            pen=pg.mkPen(C['blue'], width=1),
            movable=True,
        )
        self._region.setZValue(10)
        self._visible = False
        self._callbacks = []

    def toggle(self, visible: bool):
        self._visible = visible
        if visible:
            self._plot.addItem(self._region)
            # Set to center 50% of current view
            vr = self._plot.viewRange()
            x_range = vr[0]
            span = x_range[1] - x_range[0]
            mid = (x_range[0] + x_range[1]) / 2
            self._region.setRegion([mid - span * 0.25, mid + span * 0.25])
        else:
            self._plot.removeItem(self._region)

    def is_visible(self) -> bool:
        return self._visible

    def get_region(self) -> tuple:
        """Return (start, end) of selected region."""
        return tuple(self._region.getRegion())

    def on_region_changed(self, callback):
        """Register callback for region change events."""
        self._region.sigRegionChanged.connect(lambda: callback(self.get_region()))
        self._callbacks.append(callback)


class AnnotationManager:
    """Manage text annotations on a plot. Click to add, right-click to remove."""

    def __init__(self, plot_widget: pg.PlotWidget):
        self._plot = plot_widget
        self._annotations: list[pg.TextItem] = []
        self._enabled = False
        self._next_id = 0

    def set_enabled(self, enabled: bool):
        self._enabled = enabled
        if enabled:
            self._plot.scene().sigMouseClicked.connect(self._on_click)
        else:
            try:
                self._plot.scene().sigMouseClicked.disconnect(self._on_click)
            except TypeError:
                pass

    def _on_click(self, event):
        if not self._enabled:
            return
        # Only left-click to add
        if event.button() != Qt.LeftButton:
            return
        pos = event.scenePos()
        vb = self._plot.getViewBox()
        if not vb.sceneBoundingRect().contains(pos):
            return
        mp = vb.mapSceneToView(pos)

        self._next_id += 1
        text = pg.TextItem(
            f"#{self._next_id} ({mp.x():.1f}, {mp.y():.2f})",
            anchor=(0.5, 1.2),
            color=C['amber'],
            border=pg.mkPen(C['amber'], width=1),
            fill=pg.mkBrush(26, 26, 36, 200),
        )
        text.setFont(pg.QtGui.QFont("Inter", 9))
        text.setPos(mp.x(), mp.y())
        self._plot.addItem(text)
        self._annotations.append(text)

        # Marker dot
        dot = pg.ScatterPlotItem(
            [mp.x()], [mp.y()], size=8,
            pen=pg.mkPen(C['amber'], width=1),
            brush=pg.mkBrush(C['amber']),
        )
        self._plot.addItem(dot)

    def add_annotation(self, x: float, y: float, label: str):
        """Programmatically add annotation."""
        text = pg.TextItem(
            label, anchor=(0.5, 1.2), color=C['amber'],
            border=pg.mkPen(C['amber'], width=1),
            fill=pg.mkBrush(26, 26, 36, 200),
        )
        text.setFont(pg.QtGui.QFont("Inter", 9))
        text.setPos(x, y)
        self._plot.addItem(text)
        self._annotations.append(text)

    def clear_annotations(self):
        for item in self._annotations:
            self._plot.removeItem(item)
        self._annotations.clear()
        self._next_id = 0

    def get_annotations(self) -> list:
        return [(a.pos().x(), a.pos().y(), a.toPlainText()) for a in self._annotations]


class ColumnCalculator:
    """Create derived columns from existing data using simple expressions."""

    PRESETS = [
        ("L-R Force Diff", "L_ActForce_N - R_ActForce_N"),
        ("L-R Force Sum", "L_ActForce_N + R_ActForce_N"),
        ("Force Ratio L/R", "L_ActForce_N / (R_ActForce_N + 0.001)"),
        ("L-R Pitch Diff", "L_Pitch - R_Pitch"),
        ("L Vel Error", "L_DesVel_mps - L_ActVel_mps"),
        ("R Vel Error", "R_DesVel_mps - R_ActVel_mps"),
        ("L Pos Error", "L_DesPos_deg - L_ActPos_deg"),
        ("R Pos Error", "R_DesPos_deg - R_ActPos_deg"),
        ("L Force Error %", "(L_ErrForce_N / (L_DesForce_N + 0.001)) * 100"),
    ]

    @staticmethod
    def evaluate(df, expression: str, col_name: str = None):
        """Evaluate a column expression safely on a DataFrame.
        Returns (result_series, error_string).
        Only allows column names, basic math ops, and numpy functions.
        """
        import pandas as pd
        import numpy as np

        if col_name is None:
            col_name = f"calc_{expression[:20]}"

        # Build safe namespace with only column data and math
        safe_ns = {
            'np': np,
            'abs': np.abs,
            'sqrt': np.sqrt,
            'sin': np.sin,
            'cos': np.cos,
            'log': np.log,
            'exp': np.exp,
            'clip': np.clip,
            'maximum': np.maximum,
            'minimum': np.minimum,
        }
        # Add DataFrame columns
        for col in df.columns:
            safe_ns[col] = df[col].values.astype(np.float64)

        try:
            result = eval(expression, {"__builtins__": {}}, safe_ns)
            if isinstance(result, np.ndarray):
                return pd.Series(result, name=col_name), None
            return pd.Series(np.full(len(df), result), name=col_name), None
        except Exception as e:
            return None, str(e)
