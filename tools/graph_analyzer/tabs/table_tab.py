"""
Data Table Tab - Raw CSV data viewer
Click-to-sync with plot cursor, column sorting, search
"""

import os
import numpy as np
import pyqtgraph as pg
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QComboBox, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from styles import C
from data_manager import DataManager


class TableTab(QWidget):
    """Raw data table viewer with column filtering and row highlighting."""

    MAX_DISPLAY_ROWS = 5000  # Performance limit

    def __init__(self, data_mgr: DataManager, parent=None):
        super().__init__(parent)
        self._dm = data_mgr
        self._current_file_idx = 0
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(6, 6, 6, 6)

        # Controls
        ctrl = QFrame()
        ctrl.setObjectName("GlassCard")
        ctrl.setFixedHeight(38)
        cl = QHBoxLayout(ctrl)
        cl.setContentsMargins(10, 0, 10, 0)
        cl.setSpacing(8)

        cl.addWidget(QLabel("File:"))
        self._file_combo = QComboBox()
        self._file_combo.setMinimumWidth(200)
        self._file_combo.currentIndexChanged.connect(self._on_file_changed)
        cl.addWidget(self._file_combo)

        cl.addSpacing(8)

        cl.addWidget(QLabel("Filter:"))
        self._filter_input = QLineEdit()
        self._filter_input.setPlaceholderText("Filter columns (comma-separated)...")
        self._filter_input.setObjectName("SearchInput")
        self._filter_input.setFixedWidth(250)
        self._filter_input.returnPressed.connect(self._apply_filter)
        cl.addWidget(self._filter_input)

        apply_btn = QPushButton("Apply")
        apply_btn.setObjectName("SmallBtn")
        apply_btn.clicked.connect(self._apply_filter)
        cl.addWidget(apply_btn)

        show_all_btn = QPushButton("Show All")
        show_all_btn.setObjectName("SmallBtn")
        show_all_btn.clicked.connect(self._show_all_columns)
        cl.addWidget(show_all_btn)

        cl.addStretch()

        # Info label
        self._info_label = QLabel("")
        self._info_label.setStyleSheet(
            f"color:{C['muted']}; font-size:10px; background:transparent; border:none;")
        cl.addWidget(self._info_label)

        # Export to clipboard
        copy_btn = QPushButton("Copy Table")
        copy_btn.setObjectName("SecondaryBtn")
        copy_btn.setToolTip("Copy visible table to clipboard (TSV)")
        copy_btn.clicked.connect(self._copy_to_clipboard)
        cl.addWidget(copy_btn)

        layout.addWidget(ctrl)

        # Table
        self._table = QTableWidget()
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._table.verticalHeader().setVisible(True)
        self._table.horizontalHeader().setStretchLastSection(False)
        self._table.horizontalHeader().setSectionsClickable(True)
        self._table.horizontalHeader().sectionClicked.connect(self._on_header_clicked)
        self._table.setSortingEnabled(False)  # Manual sort via header click
        layout.addWidget(self._table, 1)

        # Bottom status
        self._status = QLabel("")
        self._status.setStyleSheet(
            f"color:{C['muted']}; font-size:10px; background:transparent; border:none;")
        layout.addWidget(self._status)

    def refresh(self):
        """Reload file list and table."""
        self._file_combo.blockSignals(True)
        prev = self._file_combo.currentIndex()
        self._file_combo.clear()
        for lf in self._dm.files:
            self._file_combo.addItem(f"{lf.name} ({len(lf.df)} rows)")
        if prev >= 0 and prev < len(self._dm.files):
            self._file_combo.setCurrentIndex(prev)
        elif self._dm.files:
            self._file_combo.setCurrentIndex(0)
        self._file_combo.blockSignals(False)
        self._load_table()

    def _on_file_changed(self, idx):
        self._current_file_idx = idx
        self._load_table()

    def _load_table(self, columns=None):
        """Load data into table widget."""
        self._table.clear()
        self._table.setRowCount(0)
        self._table.setColumnCount(0)

        if not self._dm.files or self._current_file_idx >= len(self._dm.files):
            return

        df = self._dm.files[self._current_file_idx].df

        if columns:
            cols = [c for c in columns if c in df.columns]
        else:
            cols = df.columns.tolist()

        n_rows = min(len(df), self.MAX_DISPLAY_ROWS)
        n_cols = len(cols)

        self._table.setColumnCount(n_cols)
        self._table.setRowCount(n_rows)
        self._table.setHorizontalHeaderLabels(cols)

        for ci, col in enumerate(cols):
            values = df[col].values[:n_rows]
            for ri in range(n_rows):
                val = values[ri]
                if isinstance(val, (float, np.floating)):
                    text = f"{val:.4f}" if abs(val) < 1000 else f"{val:.1f}"
                else:
                    text = str(val)
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                self._table.setItem(ri, ci, item)

        # Auto-resize columns (up to limit)
        for ci in range(min(n_cols, 15)):
            self._table.horizontalHeader().setSectionResizeMode(ci, QHeaderView.ResizeToContents)
        if n_cols > 15:
            for ci in range(15, n_cols):
                self._table.horizontalHeader().setSectionResizeMode(ci, QHeaderView.Interactive)

        truncated = " (truncated)" if len(df) > self.MAX_DISPLAY_ROWS else ""
        self._info_label.setText(f"{n_rows} rows × {n_cols} cols{truncated}")
        self._status.setText(
            f"Total: {len(df)} rows × {len(df.columns)} cols  |  "
            f"Showing: {n_rows} rows × {n_cols} cols  |  "
            f"Click column header to sort")

    def _apply_filter(self):
        text = self._filter_input.text().strip()
        if not text:
            self._load_table()
            return

        keywords = [k.strip().lower() for k in text.split(',') if k.strip()]
        if not self._dm.files or self._current_file_idx >= len(self._dm.files):
            return

        df = self._dm.files[self._current_file_idx].df
        matched = []
        for col in df.columns:
            for kw in keywords:
                if kw in col.lower():
                    matched.append(col)
                    break
        self._load_table(columns=matched if matched else None)

    def _show_all_columns(self):
        self._filter_input.clear()
        self._load_table()

    def _on_header_clicked(self, col_idx):
        """Sort table by clicked column."""
        if not self._dm.files or self._current_file_idx >= len(self._dm.files):
            return
        self._table.sortItems(col_idx)

    def _copy_to_clipboard(self):
        """Copy visible table contents to clipboard as TSV."""
        from PyQt5.QtWidgets import QApplication

        rows = self._table.rowCount()
        cols = self._table.columnCount()
        if rows == 0 or cols == 0:
            return

        # Header
        headers = []
        for c in range(cols):
            item = self._table.horizontalHeaderItem(c)
            headers.append(item.text() if item else f"Col{c}")

        lines = ["\t".join(headers)]
        for r in range(rows):
            row_data = []
            for c in range(cols):
                item = self._table.item(r, c)
                row_data.append(item.text() if item else "")
            lines.append("\t".join(row_data))

        QApplication.clipboard().setText("\n".join(lines))
        self._status.setText(f"Copied {rows} rows × {cols} cols to clipboard")
