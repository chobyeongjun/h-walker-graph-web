"""
H-Walker Graph Analyzer - Main Application Window
Standalone CSV data analysis tool with advanced graphing features.

Features:
- Drag & Drop CSV loading (up to 20 files)
- Chart tab: overlay / subplot mode, crosshair cursor, math ops, MATLAB commands
- Gait Analysis tab: HS detection, stride params, GCP-normalized force profiles
- Compare tab: stride-normalized multi-file comparison (mean±SD)
- Statistics tab: per-column stats, region crop, histogram
- Correlation tab: X-Y scatter plot with regression, R², density coloring
- FFT tab: frequency analysis, peak detection, windowing
- Data Table tab: raw CSV viewer with filtering and clipboard copy
- Column Calculator: create derived columns (L-R diff, ratios, etc.)
- ROI region selection: drag to select region, compute stats
- Annotations: click to add text markers on plots
- HTML Report generation: auto-generate comprehensive analysis report
- Export: PNG / SVG / PDF
- Session save / load
"""

import os
import sys

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QScrollArea, QCheckBox, QRadioButton, QFileDialog,
    QTabWidget, QLineEdit, QApplication, QStatusBar, QMessageBox,
    QAction, QMenuBar, QSplitter, QInputDialog,
)
from PyQt5.QtCore import Qt, QMimeData
from PyQt5.QtGui import QDragEnterEvent, QDropEvent
import pyqtgraph as pg

from styles import C, get_stylesheet
from data_manager import DataManager, ALL_COLUMNS, COLUMN_GROUPS
from widgets import ROISelector, AnnotationManager, ColumnCalculator
from tabs.chart_tab import ChartTab
from tabs.gait_tab import GaitTab
from tabs.compare_tab import CompareTab
from tabs.stats_tab import StatsTab
from tabs.correlation_tab import CorrelationTab
from tabs.fft_tab import FFTTab
from tabs.table_tab import TableTab
from report import generate_report


_SECTION_ICONS = {
    "FILES": "\u25C8",       # ◈
    "PLOT COLUMNS": "\u25A6", # ▦
    "X AXIS": "\u25CE",       # ◎
    "EXPORT": "\u25A3",       # ▣
}


def _section_label(text: str) -> QLabel:
    upper = text.upper()
    icon = _SECTION_ICONS.get(upper, "\u25B8")
    lbl = QLabel(f"{icon}  {upper}")
    lbl.setStyleSheet(
        f"color:{C['muted']}; font-size:9px; font-weight:700; "
        f"letter-spacing:1.5px; background:transparent; "
        f"border:none; border-left:2px solid rgba(76,158,255,0.40); "
        f"padding-left:7px; margin-top:4px; margin-bottom:2px;")
    return lbl


class MainWindow(QMainWindow):
    """H-Walker Graph Analyzer main window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("H-Walker Graph Analyzer")
        self.resize(1440, 900)
        self.setAcceptDrops(True)

        self._dm = DataManager()
        self._selected_columns: set = set()
        self._column_checkboxes: dict[str, QCheckBox] = {}
        self._active_filter: str | None = None
        self._group_buttons: dict[str, QPushButton] = {}
        self._section_headers: dict[str, QLabel] = {}

        self._init_menubar()
        self._init_ui()
        self._init_statusbar()

    # ================================================================
    # MENU BAR
    # ================================================================

    def _init_menubar(self):
        mb = self.menuBar()
        mb.setStyleSheet(
            f"QMenuBar {{ background:{C['sidebar']}; color:{C['text2']}; "
            f"border-bottom:1px solid {C['border']}; font-size:12px; }}"
            f"QMenuBar::item:selected {{ background:{C['hover']}; }}"
            f"QMenu {{ background:{C['card']}; color:{C['text1']}; border:1px solid {C['border']}; }}"
            f"QMenu::item:selected {{ background:{C['hover']}; }}")

        # File menu
        file_menu = mb.addMenu("File")

        open_act = QAction("Open CSV...", self)
        open_act.setShortcut("Ctrl+O")
        open_act.triggered.connect(self._open_csv)
        file_menu.addAction(open_act)

        file_menu.addSeparator()

        save_sess = QAction("Save Session...", self)
        save_sess.setShortcut("Ctrl+S")
        save_sess.triggered.connect(self._save_session)
        file_menu.addAction(save_sess)

        load_sess = QAction("Load Session...", self)
        load_sess.setShortcut("Ctrl+L")
        load_sess.triggered.connect(self._load_session)
        file_menu.addAction(load_sess)

        file_menu.addSeparator()

        quit_act = QAction("Quit", self)
        quit_act.setShortcut("Ctrl+Q")
        quit_act.triggered.connect(self.close)
        file_menu.addAction(quit_act)

        # Tools menu
        tools_menu = mb.addMenu("Tools")

        calc_act = QAction("Column Calculator...", self)
        calc_act.setShortcut("Ctrl+K")
        calc_act.triggered.connect(self._open_calculator)
        tools_menu.addAction(calc_act)

        # Calculator presets submenu
        preset_menu = tools_menu.addMenu("Calculator Presets")
        for name, expr in ColumnCalculator.PRESETS:
            act = QAction(f"{name}  ({expr})", self)
            act.triggered.connect(lambda _, n=name, e=expr: self._apply_calc_preset(n, e))
            preset_menu.addAction(act)

        tools_menu.addSeparator()

        roi_act = QAction("Toggle ROI Selection", self)
        roi_act.setShortcut("Ctrl+R")
        roi_act.triggered.connect(self._toggle_roi)
        tools_menu.addAction(roi_act)

        annot_act = QAction("Toggle Annotation Mode", self)
        annot_act.setShortcut("Ctrl+M")
        annot_act.triggered.connect(self._toggle_annotation)
        tools_menu.addAction(annot_act)

        clear_annot_act = QAction("Clear All Annotations", self)
        clear_annot_act.triggered.connect(self._clear_annotations)
        tools_menu.addAction(clear_annot_act)

        # Export menu
        export_menu = mb.addMenu("Export")
        for fmt in ["PNG", "SVG", "PDF"]:
            act = QAction(f"Export {fmt}...", self)
            act.triggered.connect(lambda _, f=fmt: self._export(f))
            export_menu.addAction(act)

        export_menu.addSeparator()
        batch_act = QAction("Batch Export All Tabs (PNG)...", self)
        batch_act.triggered.connect(self._batch_export)
        export_menu.addAction(batch_act)

        export_menu.addSeparator()
        report_act = QAction("Generate HTML Report...", self)
        report_act.setShortcut("Ctrl+Shift+R")
        report_act.triggered.connect(self._generate_report)
        export_menu.addAction(report_act)

    # ================================================================
    # UI LAYOUT
    # ================================================================

    def _init_ui(self):
        central = QWidget()
        central.setObjectName("Central")
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        # === Left Sidebar ===
        left = QScrollArea()
        left.setFixedWidth(280)
        left.setWidgetResizable(True)
        left.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        left.setObjectName("Sidebar")

        sidebar = QWidget()
        sidebar.setObjectName("SidebarInner")
        sidebar.setStyleSheet(f"#SidebarInner {{ background:{C['sidebar']}; }}")
        sl = QVBoxLayout(sidebar)
        sl.setSpacing(6)
        sl.setContentsMargins(6, 6, 6, 6)

        # --- Branded Header ---
        header_frame = QFrame()
        header_frame.setStyleSheet(
            f"background:transparent; border:none; padding:0; margin:0;")
        hl = QVBoxLayout(header_frame)
        hl.setContentsMargins(10, 8, 10, 4)
        hl.setSpacing(1)

        title_lbl = QLabel("\u25C8  H-Walker")
        title_lbl.setStyleSheet(
            f"color:{C['text1']}; font-size:17px; font-weight:800; "
            f"letter-spacing:1.5px; background:transparent; border:none; "
            f"padding-bottom:0px;")
        hl.addWidget(title_lbl)

        subtitle_lbl = QLabel("Graph Analyzer")
        subtitle_lbl.setStyleSheet(
            f"color:{C['muted']}; font-size:9px; font-weight:600; "
            f"letter-spacing:3px; text-transform:uppercase; "
            f"background:transparent; border:none; "
            f"padding-left:20px; padding-top:0px;")
        hl.addWidget(subtitle_lbl)

        # Version tag
        ver_lbl = QLabel("v2.0")
        ver_lbl.setStyleSheet(
            f"color:rgba(76,158,255,0.45); font-size:8px; font-weight:700; "
            f"letter-spacing:1px; background:transparent; border:none; "
            f"padding-left:20px;")
        hl.addWidget(ver_lbl)

        sl.addWidget(header_frame)

        header_sep = QFrame()
        header_sep.setFrameShape(QFrame.HLine)
        header_sep.setFixedHeight(2)
        header_sep.setStyleSheet(
            f"background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 rgba(76,158,255,0.5), stop:0.4 rgba(45,212,191,0.30), "
            f"stop:0.8 rgba(167,139,250,0.15), stop:1 transparent); "
            f"max-height:2px; border:none; margin:2px 6px 6px 6px;")
        sl.addWidget(header_sep)

        # --- FILES card ---
        files_card = QFrame()
        files_card.setObjectName("GlassCard")
        fl = QVBoxLayout(files_card)
        fl.setContentsMargins(10, 10, 10, 10)
        fl.setSpacing(6)

        fl.addWidget(_section_label("Files"))

        open_btn = QPushButton("\u25B6  Open CSV")
        open_btn.setObjectName("AccentBtn")
        open_btn.clicked.connect(self._open_csv)
        fl.addWidget(open_btn)

        self._file_list_layout = QVBoxLayout()
        fl.addLayout(self._file_list_layout)

        drop_hint = QLabel("\u2507\n\u25CB  Drag & Drop CSV files here\nUp to 20 files supported")
        drop_hint.setStyleSheet(
            f"color:{C['muted']}; font-size:9px; background:rgba(255,255,255,0.015); "
            f"border:1px dashed rgba(255,255,255,0.08); border-radius:6px; "
            f"padding:8px 4px;")
        drop_hint.setAlignment(Qt.AlignCenter)
        fl.addWidget(drop_hint)

        clear_btn = QPushButton("Clear All")
        clear_btn.setObjectName("SecondaryBtn")
        clear_btn.clicked.connect(self._clear_all_files)
        fl.addWidget(clear_btn)
        sl.addWidget(files_card)

        # --- COLUMNS card ---
        cols_card = QFrame()
        cols_card.setObjectName("GlassCard")
        col_l = QVBoxLayout(cols_card)
        col_l.setContentsMargins(10, 10, 10, 10)
        col_l.setSpacing(4)

        col_l.addWidget(_section_label("Plot Columns"))

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("\u2315  Search columns...")
        self._search_input.setObjectName("SearchInput")
        self._search_input.textChanged.connect(self._filter_columns)
        col_l.addWidget(self._search_input)

        # Quick group buttons — segmented pill control
        grp_frame = QFrame()
        grp_frame.setStyleSheet(
            f"background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            f"stop:0 rgba(255,255,255,0.05), stop:1 rgba(255,255,255,0.02)); "
            f"border:1px solid rgba(255,255,255,0.08); "
            f"border-top:1px solid rgba(255,255,255,0.12); "
            f"border-radius:8px; padding:3px;")
        grp_layout = QHBoxLayout(grp_frame)
        grp_layout.setContentsMargins(3, 3, 3, 3)
        grp_layout.setSpacing(1)
        _grp_short = {
            "Force": "Frc", "GCP": "GCP", "IMU Angle": "IMU",
            "Velocity": "Vel", "Position": "Pos", "Current": "Cur",
        }
        _grp_keys = list(_grp_short.keys())
        for idx, (grp_name, short) in enumerate(_grp_short.items()):
            btn = QPushButton(short)
            btn.setFixedHeight(22)
            btn.setToolTip(f"Filter to {grp_name} columns")
            # Determine border-radius for pill ends
            if idx == 0:
                radius = "border-radius:4px 0 0 4px;"
            elif idx == len(_grp_keys) - 1:
                radius = "border-radius:0 4px 4px 0;"
            else:
                radius = "border-radius:0;"
            btn.setProperty("_radius", radius)
            btn.setStyleSheet(
                f"QPushButton {{ background:rgba(255,255,255,0.02); color:{C['muted']}; "
                f"border:none; border-right:1px solid rgba(255,255,255,0.06); "
                f"padding:3px 7px; font-size:10px; font-weight:600; "
                f"{radius} }}"
                f"QPushButton:hover {{ background:rgba(76,158,255,0.15); color:{C['text1']}; }}"
                f"QPushButton:pressed {{ background:rgba(76,158,255,0.25); }}")
            btn.clicked.connect(lambda _, g=grp_name: self._toggle_group(g))
            self._group_buttons[grp_name] = btn
            grp_layout.addWidget(btn)
        col_l.addWidget(grp_frame)

        # Column checkboxes
        col_scroll = QScrollArea()
        col_scroll.setMaximumHeight(350)
        col_scroll.setWidgetResizable(True)
        col_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        col_scroll.setStyleSheet("border:none; background:transparent;")

        self._col_container = QWidget()
        self._col_container.setStyleSheet("background:transparent;")
        self._col_layout = QVBoxLayout(self._col_container)
        self._col_layout.setSpacing(1)
        self._col_layout.setContentsMargins(0, 0, 0, 0)

        # Build categorized column list from COLUMN_GROUPS
        grouped_cols = set()
        for grp_name, cols in COLUMN_GROUPS.items():
            grouped_cols.update(cols)
        for grp_name, cols in COLUMN_GROUPS.items():
            # Section header
            hdr = QLabel(f"\u2500\u2500 {grp_name} \u2500\u2500")
            hdr.setStyleSheet(
                f"color:{C['muted']}; font-size:9px; font-weight:700; "
                f"background:transparent; border:none; "
                f"padding:4px 0 1px 2px; letter-spacing:0.5px;")
            self._col_layout.addWidget(hdr)
            self._section_headers[grp_name] = hdr
            for col_name in cols:
                if col_name in ALL_COLUMNS:
                    cb = QCheckBox(col_name)
                    cb.toggled.connect(lambda checked, n=col_name: self._on_col_toggled(n, checked))
                    self._col_layout.addWidget(cb)
                    self._column_checkboxes[col_name] = cb
        # "Other" section for columns not in any group
        other_cols = [c for c in ALL_COLUMNS if c not in grouped_cols]
        if other_cols:
            hdr = QLabel("\u2500\u2500 Other \u2500\u2500")
            hdr.setStyleSheet(
                f"color:{C['muted']}; font-size:9px; font-weight:700; "
                f"background:transparent; border:none; "
                f"padding:4px 0 1px 2px; letter-spacing:0.5px;")
            self._col_layout.addWidget(hdr)
            self._section_headers["Other"] = hdr
            for col_name in other_cols:
                cb = QCheckBox(col_name)
                cb.toggled.connect(lambda checked, n=col_name: self._on_col_toggled(n, checked))
                self._col_layout.addWidget(cb)
                self._column_checkboxes[col_name] = cb

        col_scroll.setWidget(self._col_container)
        col_l.addWidget(col_scroll)

        # Select all / none
        sel_row = QHBoxLayout()
        sel_all = QPushButton("All")
        sel_all.setObjectName("SmallBtn")
        sel_all.setFixedHeight(20)
        sel_all.clicked.connect(self._select_all_columns)
        sel_row.addWidget(sel_all)
        sel_none = QPushButton("None")
        sel_none.setObjectName("SmallBtn")
        sel_none.setFixedHeight(20)
        sel_none.clicked.connect(self._select_no_columns)
        sel_row.addWidget(sel_none)
        sel_row.addStretch()
        col_l.addLayout(sel_row)

        sl.addWidget(cols_card)

        # --- X AXIS card ---
        x_card = QFrame()
        x_card.setObjectName("GlassCard")
        xl = QVBoxLayout(x_card)
        xl.setContentsMargins(10, 8, 10, 10)
        xl.setSpacing(2)
        xl.addWidget(_section_label("X Axis"))

        radio_container = QFrame()
        radio_container.setStyleSheet(
            f"background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            f"stop:0 rgba(255,255,255,0.035), stop:1 rgba(255,255,255,0.015)); "
            f"border:1px solid rgba(255,255,255,0.06); "
            f"border-top:1px solid rgba(255,255,255,0.10); "
            f"border-radius:8px; padding:4px;")
        rc_layout = QVBoxLayout(radio_container)
        rc_layout.setContentsMargins(10, 8, 10, 8)
        rc_layout.setSpacing(8)

        self._x_index = QRadioButton("\u25B9  Sample Index")
        self._x_index.setChecked(True)
        self._x_index.toggled.connect(lambda: self._set_x_axis('index'))
        rc_layout.addWidget(self._x_index)

        self._x_gcp = QRadioButton("\u25B9  GCP (%)")
        self._x_gcp.toggled.connect(lambda c: self._set_x_axis('gcp') if c else None)
        rc_layout.addWidget(self._x_gcp)

        xl.addWidget(radio_container)
        sl.addWidget(x_card)

        # --- EXPORT card ---
        exp_card = QFrame()
        exp_card.setObjectName("GlassCard")
        el = QVBoxLayout(exp_card)
        el.setContentsMargins(10, 8, 10, 8)
        el.setSpacing(6)
        el.addWidget(_section_label("Export"))
        exp_btn_row = QHBoxLayout()
        exp_btn_row.setSpacing(4)
        _fmt_icons = {"PNG": "\u25A3", "SVG": "\u25C7", "PDF": "\u25A0"}
        for fmt in ["PNG", "SVG", "PDF"]:
            b = QPushButton(f"{_fmt_icons[fmt]}  {fmt}")
            b.setObjectName("ExportBtn")
            b.setToolTip(f"Export current view as {fmt}")
            b.clicked.connect(lambda _, f=fmt: self._export(f))
            exp_btn_row.addWidget(b)
        el.addLayout(exp_btn_row)
        sl.addWidget(exp_card)

        sl.addStretch()

        left.setWidget(sidebar)
        splitter.addWidget(left)

        # === Right: Tabs ===
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)

        self._tabs = QTabWidget()

        self._chart_tab = ChartTab(self._dm)
        self._gait_tab = GaitTab(self._dm)
        self._compare_tab = CompareTab(self._dm)
        self._stats_tab = StatsTab(self._dm)
        self._corr_tab = CorrelationTab(self._dm)
        self._fft_tab = FFTTab(self._dm)
        self._table_tab = TableTab(self._dm)

        self._tabs.addTab(self._chart_tab, "Chart")
        self._tabs.addTab(self._gait_tab, "Gait Analysis")
        self._tabs.addTab(self._compare_tab, "Compare")
        self._tabs.addTab(self._stats_tab, "Statistics")
        self._tabs.addTab(self._corr_tab, "Correlation")
        self._tabs.addTab(self._fft_tab, "FFT")
        self._tabs.addTab(self._table_tab, "Data Table")

        self._tabs.setTabToolTip(0, "\uc2dc\uacc4\uc5f4 \uadf8\ub798\ud504 \u2014 \uc120\ud0dd\ud55c \ucee8\ub7fc\uc758 \ub370\uc774\ud130\ub97c \uc2dc\uac04\ucd95\uc73c\ub85c \ud45c\uc2dc")
        self._tabs.setTabToolTip(1, "\ubcf4\ud589 \ubd84\uc11d \u2014 HS \uac80\ucd9c, \uc2a4\ud2b8\ub77c\uc774\ub4dc \ud30c\ub77c\ubbf8\ud130, \ud798 \ud504\ub85c\ud30c\uc77c")
        self._tabs.setTabToolTip(2, "\ube44\uad50 \u2014 \uc5ec\ub7ec \ud30c\uc77c\uc758 \ub3d9\uc77c \ucee8\ub7fc\uc744 \uacb9\uccd0\uc11c \ube44\uad50")
        self._tabs.setTabToolTip(3, "\ud1b5\uacc4 \u2014 \ud788\uc2a4\ud1a0\uadf8\ub7a8, \ubc15\uc2a4\ud50c\ub86f, Q-Q\ud50c\ub86f, \uc815\uaddc\uc131 \uac80\uc815")
        self._tabs.setTabToolTip(4, "\uc0c1\uad00\ubd84\uc11d \u2014 X-Y \uc0b0\uc810\ub3c4, \ud68c\uadc0\ubd84\uc11d, Bland-Altman")
        self._tabs.setTabToolTip(5, "\uc8fc\ud30c\uc218 \ubd84\uc11d \u2014 FFT, Welch PSD, \uc2a4\ud399\ud2b8\ub85c\uadf8\ub7a8")
        self._tabs.setTabToolTip(6, "\ub370\uc774\ud130 \ud14c\uc774\ube14 \u2014 \uc6d0\ubcf8 CSV \ub370\uc774\ud130 \ubdf0\uc5b4")

        # ROI and Annotation on chart plot
        self._roi = ROISelector(self._chart_tab._overlay_plot)
        self._roi.on_region_changed(self._on_roi_changed)
        self._annot = AnnotationManager(self._chart_tab._overlay_plot)
        self._roi_active = False
        self._annot_active = False

        rl.addWidget(self._tabs)
        splitter.addWidget(right)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        main_layout.addWidget(splitter)

    def _init_statusbar(self):
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status_label = QLabel("\u25C8  Ready \u2500 Drag & drop CSV files to begin")
        self._status_label.setStyleSheet(
            f"color:{C['muted']}; font-size:10px; padding-left:4px; "
            f"background:transparent; border:none;")
        self._status.addPermanentWidget(self._status_label)

    # ================================================================
    # DRAG & DROP
    # ================================================================

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith('.csv'):
                    event.acceptProposedAction()
                    return

    def dropEvent(self, event: QDropEvent):
        count = 0
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith('.csv'):
                lf = self._dm.load_csv(path)
                if lf:
                    count += 1
                    if len(self._dm.files) == 1:
                        self._auto_select_columns(lf.df)
        if count:
            self._on_files_changed()
            self._status_label.setText(f"Loaded {count} file(s) — Total: {len(self._dm.files)}")

    # ================================================================
    # FILE OPERATIONS
    # ================================================================

    def _open_csv(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Open CSV Files", "",
            "CSV Files (*.csv *.CSV);;All Files (*)")
        count = 0
        for path in paths:
            lf = self._dm.load_csv(path)
            if lf:
                count += 1
                if len(self._dm.files) == 1:
                    self._auto_select_columns(lf.df)
        if count:
            self._on_files_changed()
            self._status_label.setText(f"Loaded {count} file(s) — Total: {len(self._dm.files)}")

    def _remove_file(self, path: str):
        self._dm.remove_file(path)
        self._on_files_changed()

    def _clear_all_files(self):
        self._dm.files.clear()
        self._on_files_changed()
        self._status_label.setText("All files cleared")

    def _on_files_changed(self):
        self._update_file_list_ui()
        self._refresh_all()

    def _auto_select_columns(self, df):
        auto = ["L_ActForce_N", "R_ActForce_N", "L_GCP", "R_GCP"]
        for col in auto:
            if col in df.columns and col in self._column_checkboxes:
                self._column_checkboxes[col].setChecked(True)

    def _update_file_list_ui(self):
        while self._file_list_layout.count():
            item = self._file_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    child = item.layout().takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()

        style_chars = ["\u2500\u2500\u2500", "- - -", "\u00B7 \u00B7 \u00B7", "\u2500\u00B7\u2500"]
        for lf in self._dm.files:
            # Mini-card container
            file_card = QFrame()
            file_card.setStyleSheet(
                f"background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                f"stop:0 rgba(255,255,255,0.04), stop:1 rgba(255,255,255,0.015)); "
                f"border:1px solid rgba(255,255,255,0.06); "
                f"border-left:3px solid {lf.color}; "
                f"border-radius:6px; margin:2px 0;")
            card_layout = QHBoxLayout(file_card)
            card_layout.setContentsMargins(6, 4, 4, 4)
            card_layout.setSpacing(5)

            dot = QLabel(f"\u25CF  {style_chars[lf.style_idx]}")
            dot.setStyleSheet(
                f"color:{lf.color}; font-size:10px; font-family:monospace; "
                f"background:transparent; border:none;")
            card_layout.addWidget(dot)

            # Name and size in a vertical mini-layout
            info_layout = QVBoxLayout()
            info_layout.setSpacing(0)
            info_layout.setContentsMargins(0, 0, 0, 0)
            name = QLabel(lf.name)
            name.setStyleSheet(
                f"color:{C['text1']}; font-size:11px; background:transparent; border:none;")
            name.setToolTip(lf.path)
            info_layout.addWidget(name)
            # File size
            try:
                fsize = os.path.getsize(lf.path)
                if fsize >= 1_048_576:
                    size_str = f"{fsize / 1_048_576:.1f} MB"
                else:
                    size_str = f"{fsize / 1024:.0f} KB"
            except OSError:
                size_str = ""
            if size_str:
                size_lbl = QLabel(size_str)
                size_lbl.setStyleSheet(
                    f"color:{C['muted']}; font-size:8px; background:transparent; border:none;")
                info_layout.addWidget(size_lbl)
            card_layout.addLayout(info_layout)

            card_layout.addStretch()
            x_btn = QPushButton("\u00D7")
            x_btn.setFixedSize(18, 18)
            x_btn.setStyleSheet(
                f"background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05); "
                f"color:{C['muted']}; font-size:10px; font-weight:600; border-radius:9px;"
                f"QPushButton:hover {{ background:rgba(248,113,113,0.15); color:{C['red']}; "
                f"border:1px solid rgba(248,113,113,0.25); }}")
            x_btn.clicked.connect(lambda _, p=lf.path: self._remove_file(p))
            card_layout.addWidget(x_btn)
            self._file_list_layout.addWidget(file_card)

    # ================================================================
    # COLUMN OPERATIONS
    # ================================================================

    def _filter_columns(self, text: str):
        text = text.lower()
        group_cols = set(COLUMN_GROUPS.get(self._active_filter, [])) if self._active_filter else None
        for name, cb in self._column_checkboxes.items():
            in_group = (name in group_cols) if group_cols else True
            matches_text = (text in name.lower()) if text else True
            cb.setVisible(in_group and matches_text)
        # Also hide/show section headers based on search text
        for hdr_name, hdr in self._section_headers.items():
            if self._active_filter:
                hdr.setVisible(hdr_name == self._active_filter)
            elif text:
                # Show header if any column in its group matches
                grp_cols = COLUMN_GROUPS.get(hdr_name, [])
                hdr.setVisible(any(text in c.lower() for c in grp_cols))
            else:
                hdr.setVisible(True)

    def _on_col_toggled(self, col_name: str, checked: bool):
        if checked:
            self._selected_columns.add(col_name)
        else:
            self._selected_columns.discard(col_name)
        self._push_columns()
        self._chart_tab.refresh()

    def _toggle_group(self, group_name: str):
        """Filter column list to show only columns in the clicked group.
        Clicking the same group again shows all columns (toggle off)."""
        if self._active_filter == group_name:
            # Deactivate filter — show all
            self._active_filter = None
            for name, cb in self._column_checkboxes.items():
                cb.setVisible(True)
            for hdr in self._section_headers.values():
                hdr.setVisible(True)
        else:
            # Activate filter for this group
            self._active_filter = group_name
            group_cols = set(COLUMN_GROUPS.get(group_name, []))
            for name, cb in self._column_checkboxes.items():
                cb.setVisible(name in group_cols)
            for hdr_name, hdr in self._section_headers.items():
                hdr.setVisible(hdr_name == group_name)

        # Update button styles to highlight active filter
        for gname, btn in self._group_buttons.items():
            radius = btn.property("_radius") or "border-radius:0;"
            if gname == self._active_filter:
                btn.setStyleSheet(
                    f"QPushButton {{ background:rgba(76,158,255,0.25); color:{C['text1']}; "
                    f"border:none; border-right:1px solid rgba(76,158,255,0.30); "
                    f"padding:3px 7px; font-size:10px; font-weight:700; "
                    f"{radius} }}"
                    f"QPushButton:hover {{ background:rgba(76,158,255,0.35); }}"
                    f"QPushButton:pressed {{ background:rgba(76,158,255,0.40); }}")
            else:
                btn.setStyleSheet(
                    f"QPushButton {{ background:rgba(255,255,255,0.02); color:{C['muted']}; "
                    f"border:none; border-right:1px solid rgba(255,255,255,0.06); "
                    f"padding:3px 7px; font-size:10px; font-weight:600; "
                    f"{radius} }}"
                    f"QPushButton:hover {{ background:rgba(76,158,255,0.15); color:{C['text1']}; }}"
                    f"QPushButton:pressed {{ background:rgba(76,158,255,0.25); }}")

    def _select_all_columns(self):
        avail = self._dm.get_available_columns()
        for c in avail:
            if c in self._column_checkboxes:
                self._column_checkboxes[c].setChecked(True)

    def _select_no_columns(self):
        for cb in self._column_checkboxes.values():
            cb.setChecked(False)

    def _push_columns(self):
        self._chart_tab.set_columns(self._selected_columns.copy())
        self._stats_tab.set_columns(self._selected_columns.copy())
        self._fft_tab.set_columns(self._selected_columns.copy())

    def _set_x_axis(self, mode: str):
        self._chart_tab.set_x_axis(mode)

    # ================================================================
    # REFRESH ALL TABS
    # ================================================================

    def _refresh_all(self):
        self._push_columns()
        self._chart_tab.refresh()
        self._gait_tab.refresh()
        self._compare_tab.refresh()
        self._stats_tab.refresh()
        self._corr_tab.update_columns()
        self._corr_tab.refresh()
        self._fft_tab.refresh()
        self._table_tab.refresh()

    # ================================================================
    # SESSION
    # ================================================================

    def _save_session(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Session", "session.json",
            "JSON Files (*.json);;All Files (*)")
        if not path:
            return
        extra = {
            'columns': list(self._selected_columns),
            'x_axis': 'gcp' if self._x_gcp.isChecked() else 'index',
        }
        self._dm.save_session(path, extra)
        self._status_label.setText(f"Session saved: {os.path.basename(path)}")

    def _load_session(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Session", "",
            "JSON Files (*.json);;All Files (*)")
        if not path:
            return
        extra = self._dm.load_session(path)

        # Restore columns
        self._select_no_columns()
        for col in extra.get('columns', []):
            if col in self._column_checkboxes:
                self._column_checkboxes[col].setChecked(True)

        # Restore X axis
        if extra.get('x_axis') == 'gcp':
            self._x_gcp.setChecked(True)

        self._on_files_changed()
        self._status_label.setText(
            f"Session loaded: {os.path.basename(path)} — {len(self._dm.files)} file(s)")

    # ================================================================
    # EXPORT
    # ================================================================

    def _export(self, fmt: str):
        tab_idx = self._tabs.currentIndex()
        tab_name = self._tabs.tabText(tab_idx).replace(" ", "_")

        tab_plots = {
            0: self._chart_tab.get_current_plot(),
            1: self._gait_tab._plot,
            2: self._compare_tab._plot,
            3: self._stats_tab._hist_plot,
            4: self._corr_tab._plot,
            5: self._fft_tab._spec_plot,
        }
        plot = tab_plots.get(tab_idx, self._chart_tab.get_current_plot())

        default_name = f"{tab_name}.{fmt.lower()}"
        path, _ = QFileDialog.getSaveFileName(
            self, f"Export as {fmt}", default_name,
            f"{fmt} Files (*.{fmt.lower()});;All Files (*)")
        if not path:
            return

        self._export_plot(plot, path, fmt)

    def _export_plot(self, plot, path: str, fmt: str):
        try:
            if fmt.upper() == 'PDF':
                from PyQt5.QtGui import QPainter
                from PyQt5.QtPrintSupport import QPrinter
                printer = QPrinter(QPrinter.HighResolution)
                printer.setOutputFormat(QPrinter.PdfFormat)
                printer.setOutputFileName(path)
                painter = QPainter(printer)
                plot.render(painter)
                painter.end()
            elif fmt.upper() == 'SVG':
                from pyqtgraph.exporters import SVGExporter
                exporter = SVGExporter(plot.plotItem)
                exporter.export(path)
            else:
                from pyqtgraph.exporters import ImageExporter
                exporter = ImageExporter(plot.plotItem)
                exporter.parameters()['width'] = 1920
                exporter.export(path)
        except Exception:
            pixmap = plot.grab()
            if not path.lower().endswith(f'.{fmt.lower()}'):
                path += f'.{fmt.lower()}'
            pixmap.save(path)

        if os.path.exists(path) and os.path.getsize(path) > 0:
            self._status_label.setText(
                f"Exported: {os.path.basename(path)} ({os.path.getsize(path) // 1024} KB)")
        else:
            self._status_label.setText(f"Export failed: {path}")

    def _batch_export(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Export Directory")
        if not dir_path:
            return

        tabs_plots = [
            ("Chart", self._chart_tab.get_all_plots()),
            ("Gait", [self._gait_tab._plot]),
            ("Compare", [self._compare_tab._plot]),
            ("Stats", [self._stats_tab._hist_plot]),
            ("Correlation", [self._corr_tab._plot]),
            ("FFT_Spectrum", [self._fft_tab._spec_plot]),
            ("FFT_Time", [self._fft_tab._time_plot]),
        ]

        count = 0
        for tab_name, plots in tabs_plots:
            for i, plot in enumerate(plots):
                suffix = f"_{i}" if len(plots) > 1 else ""
                path = os.path.join(dir_path, f"{tab_name}{suffix}.png")
                self._export_plot(plot, path, "PNG")
                count += 1

        self._status_label.setText(f"Batch export: {count} files to {dir_path}")

    # ================================================================
    # COLUMN CALCULATOR
    # ================================================================

    def _open_calculator(self):
        """Open dialog to create a derived column."""
        if not self._dm.files:
            self._status_label.setText("Load files first to use calculator")
            return

        expr, ok = QInputDialog.getText(
            self, "Column Calculator",
            "Expression (use column names, +, -, *, /, np.abs, etc.):\n"
            "Examples: L_ActForce_N - R_ActForce_N\n"
            "         np.abs(L_Pitch - R_Pitch)\n"
            "         L_ActForce_N / (R_ActForce_N + 0.001)",
            QLineEdit.Normal, "L_ActForce_N - R_ActForce_N")
        if not ok or not expr:
            return

        name, ok2 = QInputDialog.getText(
            self, "Column Name",
            "Name for the new column:", QLineEdit.Normal,
            f"calc_{expr[:25].replace(' ', '_')}")
        if not ok2 or not name:
            return

        self._apply_calculator(name, expr)

    def _apply_calc_preset(self, name: str, expr: str):
        self._apply_calculator(name.replace(' ', '_'), expr)

    def _apply_calculator(self, name: str, expr: str):
        errors = []
        for lf in self._dm.files:
            result, err = ColumnCalculator.evaluate(lf.df, expr, name)
            if err:
                errors.append(f"{lf.name}: {err}")
            else:
                lf.df[name] = result

        if errors:
            self._status_label.setText(f"Calc errors: {'; '.join(errors)}")
        else:
            # Add checkbox for the new column
            if name not in self._column_checkboxes:
                cb = QCheckBox(name)
                cb.setStyleSheet(f"color:{C['teal']}; font-size:11px; background:transparent;")
                cb.toggled.connect(lambda checked, n=name: self._on_col_toggled(n, checked))
                self._col_layout.addWidget(cb)
                self._column_checkboxes[name] = cb
                cb.setChecked(True)

            self._status_label.setText(f"Column '{name}' created: {expr}")
            self._corr_tab.update_columns()
            self._table_tab.refresh()

    # ================================================================
    # ROI SELECTION
    # ================================================================

    def _toggle_roi(self):
        self._roi_active = not self._roi_active
        self._roi.toggle(self._roi_active)
        state = "ON" if self._roi_active else "OFF"
        self._status_label.setText(
            f"ROI selection: {state}" +
            ("  — Drag the blue region to select data range" if self._roi_active else ""))

    def _on_roi_changed(self, region):
        start, end = region
        self._status_label.setText(
            f"ROI: [{start:.0f} ~ {end:.0f}]  "
            f"({int(end - start)} samples)")
        # Update stats tab crop range
        self._stats_tab._start_spin.setValue(int(max(0, start)))
        self._stats_tab._end_spin.setValue(int(end))

    # ================================================================
    # ANNOTATIONS
    # ================================================================

    def _toggle_annotation(self):
        self._annot_active = not self._annot_active
        self._annot.set_enabled(self._annot_active)
        state = "ON" if self._annot_active else "OFF"
        self._status_label.setText(
            f"Annotation mode: {state}" +
            ("  — Click on chart to add markers" if self._annot_active else ""))

    def _clear_annotations(self):
        self._annot.clear_annotations()
        self._status_label.setText("All annotations cleared")

    # ================================================================
    # HTML REPORT
    # ================================================================

    def _generate_report(self):
        if not self._dm.files:
            self._status_label.setText("Load files first to generate report")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Save HTML Report", "analysis_report.html",
            "HTML Files (*.html);;All Files (*)")
        if not path:
            return

        plots = {
            "Chart": self._chart_tab.get_current_plot(),
            "Gait Analysis": self._gait_tab._plot,
            "Compare": self._compare_tab._plot,
            "Correlation": self._corr_tab._plot,
            "FFT Spectrum": self._fft_tab._spec_plot,
        }

        generate_report(
            self._dm,
            columns=list(self._selected_columns),
            plots=plots,
            output_path=path,
        )

        self._status_label.setText(f"Report saved: {os.path.basename(path)}")
        # Try to open in browser
        import webbrowser
        webbrowser.open(f"file://{os.path.abspath(path)}")


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(get_stylesheet())

    # pyqtgraph global config
    pg.setConfigOptions(
        background=C['bg'],
        foreground=C['text2'],
        antialias=True,
    )

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
