"""
H-Walker Graph Analyzer - Design System
Glassmorphism dark theme (standalone version)
"""

# === Color Palette ===
C = {
    'bg':      '#0C0C16',
    'sidebar': '#0F1020',
    'card':    '#161928',
    'hover':   '#1E2245',
    'border':  'rgba(255,255,255,0.07)',
    'text1':   '#E2E8F0',
    'text2':   '#94A3B8',
    'muted':   '#64748B',
    'blue':    '#4C9EFF',
    'teal':    '#2DD4BF',
    'purple':  '#A78BFA',
    'amber':   '#FCD34D',
    'red':     '#F87171',
    'green':   '#4ADE80',
    'orange':  '#FB923C',
    'pink':    '#F472B6',
}

SERIES_COLORS = [
    '#4C9EFF', '#2DD4BF', '#A78BFA', '#FB923C', '#F472B6',
    '#FCD34D', '#4ADE80', '#F87171', '#818CF8', '#22D3EE',
    '#38BDF8', '#34D399', '#C084FC', '#FBBF24', '#E879F9',
    '#6EE7B7', '#7DD3FC', '#FCA5A5', '#A5B4FC', '#67E8F9',
]

PEN_STYLES_QT = None  # Set after Qt import

PLOT_BG = '#10101E'
GRID_ALPHA = 0.15


def get_stylesheet() -> str:
    return f"""
        * {{ font-family: "Inter","SF Pro Display","Segoe UI",sans-serif; }}
        QMainWindow, #Central {{ background:{C['bg']}; color:{C['text1']}; }}

        /* Sidebar */
        #Sidebar {{
            background:qlineargradient(x1:0,y1:0,x2:0.3,y2:1,
                stop:0 #141528, stop:0.3 {C['sidebar']}, stop:0.7 #0D0E1E, stop:1 {C['sidebar']});
            border-right:1px solid rgba(76,158,255,0.08);
            border-left:3px solid qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 rgba(76,158,255,0.50), stop:0.5 rgba(76,158,255,0.20), stop:1 rgba(76,158,255,0.50));
        }}
        #Sidebar QScrollBar:vertical {{ width:6px; background:transparent; }}
        #Sidebar QScrollBar::handle:vertical {{ background:rgba(255,255,255,0.12); border-radius:3px; }}
        #Sidebar QScrollBar::add-line, #Sidebar QScrollBar::sub-line {{ height:0; }}

        /* Glass Cards */
        #GlassCard {{
            background:qlineargradient(x1:0,y1:0,x2:0.2,y2:1,
                stop:0 rgba(36,40,64,0.97), stop:0.02 rgba(30,34,56,0.95),
                stop:0.08 rgba(26,28,48,0.93),
                stop:0.5 rgba(22,24,40,0.90), stop:1 rgba(18,20,35,0.85));
            border:1px solid rgba(100,140,255,0.06);
            border-top:1px solid rgba(140,180,255,0.22);
            border-left:1px solid rgba(100,140,255,0.10);
            border-radius:10px; padding:6px;
        }}

        /* Buttons */
        #AccentBtn {{
            background:qlineargradient(x1:0,y1:0,x2:1,y2:1,
                stop:0 #3D8EF0, stop:0.5 {C['blue']}, stop:1 #6CB4FF);
            color:#000; font-weight:700; font-size:12px;
            border:1px solid rgba(108,180,255,0.3); border-radius:8px; padding:7px 14px;
        }}
        #AccentBtn:hover {{
            background:qlineargradient(x1:0,y1:0,x2:1,y2:1,
                stop:0 #5AABFF, stop:0.5 #6CB8FF, stop:1 #7EC4FF);
            border:2px solid rgba(108,180,255,0.70);
        }}
        #AccentBtn:pressed {{
            background:qlineargradient(x1:0,y1:0,x2:1,y2:1,
                stop:0 #2A72D0, stop:1 {C['blue']});
            border:2px solid rgba(76,158,255,0.50);
        }}

        #SecondaryBtn {{
            background:rgba(255,255,255,0.04); color:{C['text2']};
            border:1px solid rgba(255,255,255,0.08); border-radius:6px;
            padding:5px 10px; font-size:11px;
        }}
        #SecondaryBtn:hover {{
            background:rgba(76,158,255,0.10); color:{C['text1']};
            border:1px solid rgba(76,158,255,0.25);
        }}
        #SecondaryBtn:pressed {{ background:rgba(76,158,255,0.06); border:1px solid rgba(76,158,255,0.15); }}

        #ExportBtn {{
            background:qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 rgba(255,255,255,0.07), stop:1 rgba(255,255,255,0.02));
            color:{C['text2']}; font-weight:600;
            border:1px solid rgba(255,255,255,0.10);
            border-top:1px solid rgba(255,255,255,0.15);
            border-radius:7px; padding:6px 10px; font-size:11px;
        }}
        #ExportBtn:hover {{
            background:qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 rgba(76,158,255,0.20), stop:1 rgba(76,158,255,0.08));
            color:{C['text1']};
            border:1px solid rgba(76,158,255,0.35);
            border-top:1px solid rgba(76,158,255,0.45);
        }}
        #ExportBtn:pressed {{
            background:rgba(76,158,255,0.12);
            border:1px solid rgba(76,158,255,0.25);
        }}

        #ToolbarBtn {{
            background:rgba(255,255,255,0.04); color:{C['text2']};
            border:1px solid rgba(255,255,255,0.06); border-radius:4px;
            padding:3px 8px; font-size:11px; font-weight:600;
        }}
        #ToolbarBtn:checked {{
            background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 #3D8EF0, stop:0.5 {C['blue']}, stop:1 #5AAAFF);
            color:#000; border:1px solid rgba(76,158,255,0.55);
            border-bottom:2px solid rgba(76,158,255,0.70);
        }}
        #ToolbarBtn:hover {{ background:rgba(76,158,255,0.12); border:1px solid rgba(76,158,255,0.20); color:{C['text1']}; }}

        #SmallBtn {{
            background:transparent; color:{C['muted']};
            border:1px solid rgba(255,255,255,0.06); border-radius:4px;
            padding:3px 8px; font-size:11px;
        }}
        #SmallBtn:hover {{ color:{C['text1']}; background:rgba(255,255,255,0.04); }}

        #DangerBtn {{
            background:rgba(248,113,113,0.1); color:{C['red']};
            border:1px solid rgba(248,113,113,0.2); border-radius:4px;
            padding:3px 8px; font-size:11px;
        }}
        #DangerBtn:hover {{ background:rgba(248,113,113,0.2); }}

        #CloseBtn {{
            background:transparent; border:none; color:{C['muted']};
            font-size:12px; font-weight:700;
        }}
        #CloseBtn:hover {{ color:{C['red']}; }}

        /* Inputs */
        #SearchInput {{
            background:rgba(255,255,255,0.06); color:{C['text1']};
            border:1px solid rgba(255,255,255,0.10); border-radius:7px;
            padding:6px 10px; font-size:11px;
        }}
        #SearchInput:focus {{ border:2px solid rgba(76,158,255,0.55); background:rgba(76,158,255,0.05); }}

        QDoubleSpinBox, QSpinBox {{
            background:rgba(255,255,255,0.05); color:{C['text1']};
            border:1px solid rgba(255,255,255,0.10); border-radius:5px;
            padding:3px 5px; font-size:10px;
        }}
        QDoubleSpinBox:focus, QSpinBox:focus {{
            border:2px solid rgba(76,158,255,0.60);
            background:rgba(76,158,255,0.06);
        }}
        QDoubleSpinBox::up-button, QSpinBox::up-button,
        QDoubleSpinBox::down-button, QSpinBox::down-button {{
            background:rgba(76,158,255,0.08); border:none; width:16px;
        }}
        QDoubleSpinBox::up-button:hover, QSpinBox::up-button:hover,
        QDoubleSpinBox::down-button:hover, QSpinBox::down-button:hover {{
            background:rgba(76,158,255,0.20);
        }}

        QComboBox {{
            background:rgba(255,255,255,0.05); color:{C['text1']};
            border:1px solid rgba(255,255,255,0.10); border-radius:5px;
            padding:3px 6px; font-size:10px;
        }}
        QComboBox:focus {{ border:2px solid rgba(76,158,255,0.60); background:rgba(76,158,255,0.06); }}
        QComboBox::drop-down {{
            border:none; width:22px;
            background:rgba(76,158,255,0.10); border-top-right-radius:5px; border-bottom-right-radius:5px;
            border-left:1px solid rgba(255,255,255,0.06);
        }}
        QComboBox::down-arrow {{ image:none; border-left:4px solid transparent; border-right:4px solid transparent;
            border-top:6px solid {C['blue']}; width:0; height:0; }}
        QComboBox::drop-down:hover {{ background:rgba(76,158,255,0.22); }}
        QComboBox QAbstractItemView {{
            background:{C['card']}; color:{C['text1']};
            border:1px solid rgba(76,158,255,0.15); selection-background-color:rgba(76,158,255,0.18);
            outline:none; padding:3px;
            border-radius:6px;
        }}
        QComboBox QAbstractItemView::item {{ padding:5px 8px; border-radius:4px; margin:1px; }}
        QComboBox QAbstractItemView::item:hover {{ background:rgba(76,158,255,0.12); }}

        /* Tabs */
        QTabWidget::pane {{ border:none; }}
        QTabBar {{ background:transparent; }}
        QTabBar::tab {{
            background:transparent; color:{C['muted']};
            padding:6px 10px; font-size:12px; font-weight:700;
            border-bottom:2px solid transparent; margin-right:2px;
            border-top-left-radius:6px; border-top-right-radius:6px;
        }}
        QTabBar::tab:selected {{
            color:{C['blue']}; border-bottom:2px solid {C['blue']};
            background:qlineargradient(x1:0,y1:1,x2:0,y2:0,
                stop:0 rgba(76,158,255,0.14), stop:0.4 rgba(76,158,255,0.06), stop:1 transparent);
        }}
        QTabBar::tab:hover {{
            color:{C['text1']}; background:rgba(76,158,255,0.06);
            border-bottom:2px solid rgba(76,158,255,0.30);
        }}

        /* Table */
        QTableWidget {{
            background:{C['card']}; border:1px solid rgba(100,140,255,0.06);
            border-radius:8px; gridline-color:rgba(255,255,255,0.04);
            color:{C['text1']}; font-size:11px;
            alternate-background-color:rgba(76,158,255,0.03);
        }}
        QTableWidget::item {{ padding:4px 6px; }}
        QTableWidget::item:selected {{
            background:rgba(76,158,255,0.18); color:{C['text1']};
        }}
        QTableWidget::item:hover {{
            background:rgba(76,158,255,0.08);
        }}
        QHeaderView::section {{
            background:qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 rgba(76,120,200,0.14), stop:1 rgba(76,120,200,0.04));
            color:{C['text1']};
            border:none; border-bottom:2px solid rgba(76,158,255,0.15);
            border-right:1px solid rgba(255,255,255,0.05);
            padding:6px 8px; font-size:10px; font-weight:700;
            text-transform:uppercase;
        }}

        /* Splitter */
        QSplitter::handle {{
            background:qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0.00 rgba(76,158,255,0.02), stop:0.10 rgba(76,158,255,0.10),
                stop:0.15 rgba(76,158,255,0.02), stop:0.25 rgba(76,158,255,0.10),
                stop:0.30 rgba(76,158,255,0.02), stop:0.40 rgba(76,158,255,0.10),
                stop:0.45 rgba(76,158,255,0.02), stop:0.55 rgba(76,158,255,0.10),
                stop:0.60 rgba(76,158,255,0.02), stop:0.70 rgba(76,158,255,0.10),
                stop:0.75 rgba(76,158,255,0.02), stop:0.85 rgba(76,158,255,0.10),
                stop:0.90 rgba(76,158,255,0.02), stop:1.00 rgba(76,158,255,0.10));
        }}
        QSplitter::handle:hover {{ background:rgba(76,158,255,0.28); }}
        QSplitter::handle:horizontal {{ width:5px; }}
        QSplitter::handle:vertical {{ height:5px; }}

        /* Scrollbars */
        QScrollBar:vertical {{ width:6px; background:transparent; }}
        QScrollBar::handle:vertical {{ background:rgba(76,158,255,0.15); border-radius:3px; min-height:24px; }}
        QScrollBar::handle:vertical:hover {{ background:rgba(76,158,255,0.28); }}
        QScrollBar::add-line, QScrollBar::sub-line {{ height:0; }}
        QScrollBar:horizontal {{ height:6px; background:transparent; }}
        QScrollBar::handle:horizontal {{ background:rgba(76,158,255,0.15); border-radius:3px; min-width:24px; }}
        QScrollBar::handle:horizontal:hover {{ background:rgba(76,158,255,0.28); }}

        /* CheckBox */
        QCheckBox {{ color:{C['text2']}; font-size:12px; background:transparent; min-height:20px; }}
        QCheckBox::indicator {{ width:14px; height:14px; border-radius:3px;
            border:1px solid rgba(255,255,255,0.15); background:rgba(255,255,255,0.04); }}
        QCheckBox::indicator:hover {{ border:1px solid rgba(76,158,255,0.40); background:rgba(76,158,255,0.08); }}
        QCheckBox::indicator:checked {{ background:{C['blue']}; border-color:{C['blue']}; }}

        /* RadioButton */
        QRadioButton {{ color:{C['text2']}; font-size:12px; background:transparent; min-height:22px; padding:2px 0; }}
        QRadioButton::indicator {{ width:14px; height:14px; border-radius:7px;
            border:1px solid rgba(255,255,255,0.18); background:rgba(255,255,255,0.04); }}
        QRadioButton::indicator:hover {{ border:1px solid rgba(76,158,255,0.45); background:rgba(76,158,255,0.08); }}
        QRadioButton::indicator:checked {{ background:{C['blue']}; border:2px solid rgba(76,158,255,0.6); }}

        /* Tooltip */
        QToolTip {{
            background:rgba(22,24,42,0.98); color:{C['text1']};
            border:1px solid rgba(76,158,255,0.35);
            border-top:1px solid rgba(140,180,255,0.30);
            border-radius:8px; padding:7px 12px; font-size:10px;
            font-weight:500;
        }}

        /* StatusBar */
        QStatusBar {{
            background:qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 rgba(20,22,38,0.98), stop:1 rgba(12,12,22,0.98));
            color:{C['text2']}; font-size:10px; font-weight:600;
            border-top:1px solid rgba(76,158,255,0.10);
            padding:3px 10px; min-height:24px;
        }}
        QStatusBar::item {{ border:none; }}
    """
