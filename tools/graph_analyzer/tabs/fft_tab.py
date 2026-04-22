"""
FFT / Frequency Analysis Tab
Enhanced: Spectrogram heatmap, Welch PSD, phase display, frequency band power
"""

import os
import numpy as np
import pyqtgraph as pg
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QComboBox, QCheckBox, QSplitter, QSpinBox, QTabWidget,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from styles import C, SERIES_COLORS
from widgets import CrosshairPlotWidget, ZoomToolbar
from data_manager import DataManager

PEN_STYLES = [Qt.SolidLine, Qt.DashLine, Qt.DotLine, Qt.DashDotLine]

WINDOW_FUNCS = {
    "Hanning": np.hanning,
    "Hamming": np.hamming,
    "Blackman": np.blackman,
    "Rectangle": np.ones,
}


class FFTTab(QWidget):
    """Frequency domain analysis: FFT, Welch PSD, Spectrogram, phase."""

    def __init__(self, data_mgr: DataManager, parent=None):
        super().__init__(parent)
        self._dm = data_mgr
        self._selected_columns: set = set()
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
        cl.setSpacing(4)

        cl.addWidget(QLabel("Win:"))
        self._window_combo = QComboBox()
        self._window_combo.addItems(list(WINDOW_FUNCS.keys()))
        self._window_combo.setFixedWidth(85)
        self._window_combo.currentIndexChanged.connect(lambda: self.refresh())
        cl.addWidget(self._window_combo)

        cl.addWidget(QLabel("Scl:"))
        self._scale_combo = QComboBox()
        self._scale_combo.addItems(["Linear", "dB"])
        self._scale_combo.setFixedWidth(65)
        self._scale_combo.currentIndexChanged.connect(lambda: self.refresh())
        cl.addWidget(self._scale_combo)

        self._method_combo = QComboBox()
        self._method_combo.addItems(["FFT", "Welch"])
        self._method_combo.setFixedWidth(65)
        self._method_combo.setToolTip("Welch: averaged periodogram for smoother PSD estimate")
        self._method_combo.currentIndexChanged.connect(lambda: self.refresh())
        cl.addWidget(self._method_combo)

        cl.addSpacing(4)

        self._detrend_cb = QCheckBox("Det")
        self._detrend_cb.setChecked(True)
        self._detrend_cb.setToolTip("Detrend (remove DC offset)")
        self._detrend_cb.setStyleSheet(f"color:{C['text2']}; background:transparent;")
        self._detrend_cb.toggled.connect(lambda: self.refresh())
        cl.addWidget(self._detrend_cb)

        self._peaks_cb = QCheckBox("Pk")
        self._peaks_cb.setChecked(True)
        self._peaks_cb.setToolTip("Show peak markers")
        self._peaks_cb.setStyleSheet(f"color:{C['text2']}; background:transparent;")
        self._peaks_cb.toggled.connect(lambda: self.refresh())
        cl.addWidget(self._peaks_cb)

        self._phase_cb = QCheckBox("Ph")
        self._phase_cb.setToolTip("Show phase spectrum")
        self._phase_cb.setStyleSheet(f"color:{C['text2']}; background:transparent;")
        self._phase_cb.toggled.connect(lambda: self.refresh())
        cl.addWidget(self._phase_cb)

        cl.addSpacing(2)

        cl.addWidget(QLabel("Hz:"))
        self._max_freq_spin = QSpinBox()
        self._max_freq_spin.setRange(1, 500)
        self._max_freq_spin.setValue(55)
        self._max_freq_spin.setFixedWidth(55)
        self._max_freq_spin.setToolTip("Maximum frequency to display")
        self._max_freq_spin.valueChanged.connect(lambda: self.refresh())
        cl.addWidget(self._max_freq_spin)

        cl.addStretch()

        # Peak info
        self._peak_label = QLabel("")
        self._peak_label.setStyleSheet(
            f"color:{C['amber']}; font-size:10px; font-family:monospace; "
            f"background:rgba(255,255,255,0.03); "
            f"border:1px solid rgba(255,255,255,0.06); "
            f"border-left:2px solid {C['amber']}; "
            f"border-radius:4px; padding:2px 8px;")
        cl.addWidget(self._peak_label)

        layout.addWidget(ctrl)

        # Sub-tabs: Spectrum | Spectrogram | Band Power
        self._sub_tabs = QTabWidget()

        # --- Spectrum tab ---
        spec_tab = QWidget()
        stl = QVBoxLayout(spec_tab)
        stl.setContentsMargins(4, 6, 4, 4)
        stl.setSpacing(4)

        splitter = QSplitter(Qt.Vertical)

        # Magnitude plot
        mag_w = QWidget()
        ml = QVBoxLayout(mag_w)
        ml.setContentsMargins(0, 0, 0, 0)
        ml.setSpacing(2)
        self._spec_plot = CrosshairPlotWidget()
        self._spec_plot.setTitle("Power Spectrum", color=C['text1'], size='10pt')
        self._spec_plot.setLabel('bottom', 'Frequency (Hz)')
        self._spec_plot.setLabel('left', 'Magnitude')
        self._spec_plot.addLegend(offset=(10, 10), labelTextSize='9pt')
        ml.addWidget(ZoomToolbar(self._spec_plot))
        ml.addWidget(self._spec_plot, 1)
        splitter.addWidget(mag_w)

        # Phase plot (hidden by default, shown with phase checkbox)
        phase_w = QWidget()
        phl = QVBoxLayout(phase_w)
        phl.setContentsMargins(0, 0, 0, 0)
        phl.setSpacing(2)
        self._phase_plot = CrosshairPlotWidget()
        self._phase_plot.setTitle("Phase Spectrum", color=C['text1'], size='10pt')
        self._phase_plot.setLabel('bottom', 'Frequency (Hz)')
        self._phase_plot.setLabel('left', 'Phase (deg)')
        self._phase_plot.addLegend(offset=(10, 10), labelTextSize='9pt')
        phl.addWidget(self._phase_plot, 1)
        self._phase_widget = phase_w
        phase_w.hide()
        splitter.addWidget(phase_w)

        # Time domain
        time_w = QWidget()
        tl = QVBoxLayout(time_w)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(2)
        self._time_plot = CrosshairPlotWidget()
        self._time_plot.setTitle("Time Domain", color=C['text1'], size='10pt')
        self._time_plot.setLabel('bottom', 'Sample')
        self._time_plot.setLabel('left', 'Value')
        self._time_plot.addLegend(offset=(10, 10), labelTextSize='9pt')
        tl.addWidget(ZoomToolbar(self._time_plot, with_y_lock=False))
        tl.addWidget(self._time_plot, 1)
        splitter.addWidget(time_w)

        splitter.setSizes([400, 200, 200])
        stl.addWidget(splitter)
        self._sub_tabs.addTab(spec_tab, "Spectrum")

        # --- Spectrogram tab ---
        sgram_tab = QWidget()
        sgl = QVBoxLayout(sgram_tab)
        sgl.setContentsMargins(4, 4, 4, 4)
        sgl.setSpacing(4)

        sgram_ctrl = QFrame()
        sgram_ctrl.setObjectName("GlassCard")
        sgram_ctrl.setFixedHeight(36)
        sgram_ctrl.setStyleSheet(
            "QFrame#GlassCard { border-left: 2px solid rgba(76,158,255,0.15); }")
        scl = QHBoxLayout(sgram_ctrl)
        scl.setContentsMargins(12, 0, 12, 0)
        scl.setSpacing(8)

        scl.addWidget(QLabel("Segment:"))
        self._sgram_seg = QSpinBox()
        self._sgram_seg.setRange(32, 2048)
        self._sgram_seg.setValue(256)
        self._sgram_seg.setFixedWidth(70)
        scl.addWidget(self._sgram_seg)

        scl.addWidget(QLabel("Overlap:"))
        self._sgram_overlap = QSpinBox()
        self._sgram_overlap.setRange(0, 95)
        self._sgram_overlap.setValue(50)
        self._sgram_overlap.setSuffix("%")
        self._sgram_overlap.setFixedWidth(60)
        scl.addWidget(self._sgram_overlap)

        scl.addWidget(QLabel("Column:"))
        self._sgram_col_combo = QComboBox()
        self._sgram_col_combo.setMinimumWidth(140)
        scl.addWidget(self._sgram_col_combo)

        sgram_refresh = QPushButton("Compute")
        sgram_refresh.setObjectName("AccentBtn")
        sgram_refresh.clicked.connect(self._refresh_spectrogram)
        scl.addWidget(sgram_refresh)

        scl.addStretch()
        sgl.addWidget(sgram_ctrl)

        # Spectrogram image
        self._sgram_widget = pg.PlotWidget()
        self._sgram_widget.setBackground(C['bg'])
        self._sgram_widget.setLabel('bottom', 'Time (samples)')
        self._sgram_widget.setLabel('left', 'Frequency (Hz)')
        self._sgram_img = pg.ImageItem()
        self._sgram_widget.addItem(self._sgram_img)

        # Colorbar
        colormap = pg.colormap.get('viridis')
        self._sgram_img.setLookupTable(colormap.getLookupTable())

        sgl.addWidget(self._sgram_widget, 1)
        self._sub_tabs.addTab(sgram_tab, "Spectrogram")

        # --- Band Power tab ---
        band_tab = QWidget()
        bl = QVBoxLayout(band_tab)
        bl.setContentsMargins(4, 4, 4, 4)
        bl.setSpacing(4)

        self._band_plot = CrosshairPlotWidget()
        self._band_plot.setTitle("Frequency Band Power Distribution", color=C['text1'], size='10pt')
        self._band_plot.setLabel('bottom', 'Band')
        self._band_plot.setLabel('left', 'Power (%)')
        bl.addWidget(ZoomToolbar(self._band_plot, with_y_lock=False))
        bl.addWidget(self._band_plot, 1)

        self._band_table_label = QLabel("")
        self._band_table_label.setStyleSheet(
            f"color:{C['text2']}; font-size:10px; font-family:monospace; "
            f"background:rgba(24,24,37,0.95); "
            f"border:1px solid rgba(255,255,255,0.08); "
            f"border-left:2px solid {C['blue']}; "
            f"border-radius:4px; padding:6px 10px;")
        bl.addWidget(self._band_table_label)
        self._sub_tabs.addTab(band_tab, "Band Power")

        layout.addWidget(self._sub_tabs, 1)

    def set_columns(self, columns: set):
        self._selected_columns = columns
        # Update spectrogram column combo
        self._sgram_col_combo.clear()
        for col in sorted(columns):
            self._sgram_col_combo.addItem(col)
        self.refresh()

    def refresh(self):
        self._spec_plot.clear()
        self._spec_plot.addLegend(offset=(10, 10), labelTextSize='9pt')
        self._phase_plot.clear()
        self._phase_plot.addLegend(offset=(10, 10), labelTextSize='9pt')
        self._time_plot.clear()
        self._time_plot.addLegend(offset=(10, 10), labelTextSize='9pt')
        self._peak_label.setText("")

        # Toggle phase plot visibility
        self._phase_widget.setVisible(self._phase_cb.isChecked())

        if not self._dm.files or not self._selected_columns:
            return

        window_name = self._window_combo.currentText()
        win_func = WINDOW_FUNCS.get(window_name, np.hanning)
        use_db = self._scale_combo.currentIndex() == 1
        use_welch = self._method_combo.currentIndex() == 1
        detrend = self._detrend_cb.isChecked()
        show_peaks = self._peaks_cb.isChecked()
        show_phase = self._phase_cb.isChecked()
        max_freq = self._max_freq_spin.value()

        peak_texts = []

        for lf in self._dm.files:
            fs = DataManager.estimate_sample_rate(lf.df)
            pen_style = PEN_STYLES[lf.style_idx]

            for col in sorted(self._selected_columns):
                if col not in lf.df.columns:
                    continue

                y = lf.df[col].values.astype(np.float64)
                valid = y[np.isfinite(y)]
                if len(valid) < 16:
                    continue

                if detrend:
                    valid = valid - np.mean(valid)

                name = f"{lf.name}: {col}"

                # Time domain plot
                self._time_plot.plot(np.arange(len(valid)), valid,
                    pen=pg.mkPen(lf.color, width=1.5, style=pen_style), name=name)

                # Compute spectrum
                if use_welch:
                    freqs, magnitude, phase = self._welch_psd(valid, fs, win_func)
                else:
                    freqs, magnitude, phase = self._fft_spectrum(valid, fs, win_func)

                # Limit to max freq
                mask = freqs <= max_freq
                freqs = freqs[mask]
                magnitude = magnitude[mask]
                phase = phase[mask] if phase is not None else None

                if use_db:
                    magnitude = 20 * np.log10(np.maximum(magnitude, 1e-12))
                    self._spec_plot.setLabel('left', 'Magnitude (dB)')
                else:
                    self._spec_plot.setLabel('left', 'Magnitude')

                # Magnitude plot
                pen = pg.mkPen(lf.color, width=1.5, style=pen_style)
                self._spec_plot.plot(freqs, magnitude, pen=pen, name=name)

                # Phase plot
                if show_phase and phase is not None:
                    phase_deg = np.degrees(phase)
                    self._phase_plot.plot(freqs, phase_deg,
                        pen=pg.mkPen(lf.color, width=1, style=pen_style), name=name)

                # Peak detection
                if show_peaks and len(magnitude) > 5:
                    peaks = self._detect_peaks(magnitude, n_peaks=5)
                    for pi in peaks:
                        if pi < len(freqs):
                            f_peak = freqs[pi]
                            m_peak = magnitude[pi]
                            self._spec_plot.plot(
                                [f_peak], [m_peak], pen=pg.mkPen(None),
                                symbol='o', symbolSize=10,
                                symbolBrush=pg.mkBrush(C['amber']),
                                symbolPen=pg.mkPen(C['amber'], width=1))
                            text = pg.TextItem(
                                f"{f_peak:.1f}Hz", anchor=(0.5, 1.3), color=C['amber'])
                            text.setFont(pg.QtGui.QFont("monospace", 8))
                            text.setPos(f_peak, m_peak)
                            self._spec_plot.addItem(text)
                            peak_texts.append(f"{col}:{f_peak:.1f}Hz")

        if peak_texts:
            self._peak_label.setText("Peaks: " + " | ".join(peak_texts[:8]))

        self._spec_plot.enableAutoRange()
        self._time_plot.enableAutoRange()
        if show_phase:
            self._phase_plot.enableAutoRange()

        # Refresh band power
        self._refresh_band_power()

    @staticmethod
    def _fft_spectrum(y, fs, win_func):
        n = len(y)
        win = win_func(n)
        windowed = y * win
        fft_vals = np.fft.rfft(windowed)
        freqs = np.fft.rfftfreq(n, d=1.0 / fs)
        magnitude = np.abs(fft_vals) * 2.0 / n
        phase = np.angle(fft_vals)
        return freqs, magnitude, phase

    @staticmethod
    def _welch_psd(y, fs, win_func, nperseg=256):
        """Welch method: averaged periodogram."""
        nperseg = min(nperseg, len(y))
        noverlap = nperseg // 2
        step = nperseg - noverlap

        segments = []
        for start in range(0, len(y) - nperseg + 1, step):
            seg = y[start:start + nperseg]
            win = win_func(len(seg))
            windowed = seg * win
            fft_vals = np.fft.rfft(windowed)
            psd = np.abs(fft_vals) ** 2
            segments.append(psd)

        if not segments:
            return np.array([]), np.array([]), None

        avg_psd = np.mean(segments, axis=0)
        magnitude = np.sqrt(avg_psd) * 2.0 / nperseg
        freqs = np.fft.rfftfreq(nperseg, d=1.0 / fs)
        return freqs, magnitude, None

    @staticmethod
    def _detect_peaks(data, n_peaks=5):
        if len(data) < 3:
            return []
        d = data[1:]  # skip DC
        threshold = np.mean(d) + 1.5 * np.std(d)
        peaks = []
        for i in range(1, len(d) - 1):
            if d[i] > d[i-1] and d[i] > d[i+1] and d[i] > threshold:
                peaks.append(i + 1)
        peaks.sort(key=lambda i: data[i], reverse=True)
        return peaks[:n_peaks]

    def _refresh_spectrogram(self):
        """Compute and display spectrogram for selected column."""
        if not self._dm.files:
            return

        col = self._sgram_col_combo.currentText()
        if not col:
            return

        lf = self._dm.files[0]  # Use first file
        if col not in lf.df.columns:
            return

        y = lf.df[col].values.astype(np.float64)
        valid = y[np.isfinite(y)]
        if len(valid) < 64:
            return

        fs = DataManager.estimate_sample_rate(lf.df)
        nperseg = self._sgram_seg.value()
        overlap_pct = self._sgram_overlap.value() / 100.0
        noverlap = int(nperseg * overlap_pct)
        step = max(1, nperseg - noverlap)

        win_name = self._window_combo.currentText()
        win_func = WINDOW_FUNCS.get(win_name, np.hanning)
        win = win_func(nperseg)

        # Compute STFT
        segments = []
        times = []
        for start in range(0, len(valid) - nperseg + 1, step):
            seg = valid[start:start + nperseg] * win
            fft_vals = np.fft.rfft(seg)
            psd = np.abs(fft_vals) ** 2
            segments.append(psd)
            times.append(start)

        if not segments:
            return

        sgram = np.array(segments).T  # shape: (freq_bins, time_steps)
        freqs = np.fft.rfftfreq(nperseg, d=1.0 / fs)

        # Limit to max freq
        max_freq = self._max_freq_spin.value()
        freq_mask = freqs <= max_freq
        sgram = sgram[freq_mask, :]
        freqs = freqs[freq_mask]

        # Log scale
        sgram = 10 * np.log10(np.maximum(sgram, 1e-12))

        # Display
        self._sgram_img.setImage(sgram.T, autoLevels=True)

        # Set axes
        tr = pg.QtGui.QTransform()
        if len(times) > 1 and len(freqs) > 1:
            t_scale = (times[-1] - times[0]) / sgram.shape[1] if sgram.shape[1] > 1 else 1
            f_scale = (freqs[-1] - freqs[0]) / sgram.shape[0] if sgram.shape[0] > 1 else 1
            tr.scale(t_scale, f_scale)
            tr.translate(times[0] / t_scale if t_scale else 0, freqs[0] / f_scale if f_scale else 0)
        self._sgram_img.setTransform(tr)
        self._sgram_widget.autoRange()

    def _refresh_band_power(self):
        """Compute power in frequency bands and show as bar chart."""
        self._band_plot.clear()

        if not self._dm.files or not self._selected_columns:
            self._band_table_label.setText("")
            return

        # Define frequency bands (Hz)
        bands = [
            ("0-2", 0, 2),
            ("2-5", 2, 5),
            ("5-10", 5, 10),
            ("10-20", 10, 20),
            ("20-40", 20, 40),
            ("40+", 40, 999),
        ]

        band_data = {}
        for lf in self._dm.files:
            fs = DataManager.estimate_sample_rate(lf.df)
            for col in sorted(self._selected_columns):
                if col not in lf.df.columns:
                    continue
                y = lf.df[col].values.astype(np.float64)
                valid = y[np.isfinite(y)]
                if len(valid) < 16:
                    continue

                valid = valid - np.mean(valid)
                n = len(valid)
                fft_vals = np.fft.rfft(valid)
                freqs = np.fft.rfftfreq(n, d=1.0 / fs)
                power = np.abs(fft_vals) ** 2
                total_power = np.sum(power)
                if total_power < 1e-12:
                    continue

                key = f"{lf.name}: {col}"
                band_data[key] = []
                for bname, f_lo, f_hi in bands:
                    mask = (freqs >= f_lo) & (freqs < f_hi)
                    bp = np.sum(power[mask]) / total_power * 100
                    band_data[key].append(bp)

        if not band_data:
            self._band_table_label.setText("")
            return

        # Bar chart
        x_labels = [b[0] for b in bands]
        x_pos = np.arange(len(bands))
        bar_width = 0.8 / max(1, len(band_data))

        table_lines = ["Band Power Distribution (%):", ""]
        color_idx = 0
        for key, powers in band_data.items():
            offset = (color_idx - len(band_data) / 2 + 0.5) * bar_width
            color = SERIES_COLORS[color_idx % len(SERIES_COLORS)]
            bg = pg.BarGraphItem(
                x=x_pos + offset, height=powers, width=bar_width * 0.9,
                brush=QColor(color), pen=pg.mkPen(None), name=key)
            self._band_plot.addItem(bg)

            line = f"  {key}: " + " | ".join(f"{x_labels[i]}={powers[i]:.1f}%" for i in range(len(bands)))
            table_lines.append(line)
            color_idx += 1

        # X-axis labels
        ax = self._band_plot.getAxis('bottom')
        ax.setTicks([[(i, label) for i, label in enumerate(x_labels)]])
        self._band_plot.enableAutoRange()
        self._band_table_label.setText("\n".join(table_lines))
