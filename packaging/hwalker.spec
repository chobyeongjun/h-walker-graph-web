# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec — Windows / Linux single-file bundle.

Usage (from repo root):
    pip install pyinstaller
    cd frontend && npm install && npm run build && cd ..
    python3 tools/build_icons.py
    pyinstaller packaging/hwalker.spec --noconfirm

Output:
    dist/H-Walker CORE/H-Walker CORE(.exe)   — folder bundle
"""
from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent   # packaging/ → repo root
FRONTEND_DIST = ROOT / "frontend" / "dist"
TOOLS_DIR = ROOT / "tools"

# Collect every frontend artifact as a data file
datas = []
if FRONTEND_DIST.is_dir():
    for p in FRONTEND_DIST.rglob("*"):
        if p.is_file():
            datas.append((str(p), str(p.relative_to(ROOT).parent)))

# Ship the vendored analyzer tools
for p in TOOLS_DIR.rglob("*.py"):
    datas.append((str(p), str(p.relative_to(ROOT).parent)))

# Ship icons
if (ROOT / "AppIcon.icns").is_file():
    datas.append((str(ROOT / "AppIcon.icns"), "."))
if (ROOT / "frontend" / "public" / "AppIcon.ico").is_file():
    datas.append((str(ROOT / "frontend" / "public" / "AppIcon.ico"), "."))

block_cipher = None

a = Analysis(
    [str(ROOT / "desktop.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "backend.routers.analyze",
        "backend.routers.compute",
        "backend.routers.stats",
        "backend.routers.graphs",
        "backend.routers.datasets",
        "backend.routers.claude",
        "backend.services.publication_engine",
        "backend.services.compute_engine",
        "backend.services.stats_engine",
        "backend.services.analysis_engine",
        "tools.auto_analyzer.analyzer",
        "tools.graph_analyzer.data_manager",
        "anthropic",
        "webview",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "PyQt5", "PyQt6", "pytest"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="H-Walker CORE",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "frontend" / "public" / "AppIcon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="H-Walker CORE",
)
