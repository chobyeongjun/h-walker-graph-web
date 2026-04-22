"""
py2app build config — macOS .app bundle.

Usage (from repo root):
    python3 -m pip install py2app
    cd frontend && npm install && npm run build && cd ..
    python3 tools/build_icons.py
    python3 packaging/setup_py2app.py py2app

Output:
    dist/H-Walker CORE.app/

To release:
    Sign + notarize separately via codesign + notarytool.
    (Unsigned .app requires right-click → Open on first launch.)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from setuptools import setup   # type: ignore

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

APP = ["desktop.py"]
DATA_FILES = [
    ("", ["AppIcon.icns"]),
    ("frontend/dist", _glob_root := []),  # type: ignore
]
# Flatten the frontend dist as nested resources
for rel in (ROOT / "frontend" / "dist").rglob("*"):
    if rel.is_file():
        target_dir = str(rel.parent.relative_to(ROOT))
        DATA_FILES.append((target_dir, [str(rel.relative_to(ROOT))]))

# Keep tools/ (auto_analyzer, graph_analyzer) shipped
for rel in (ROOT / "tools").rglob("*.py"):
    target_dir = str(rel.parent.relative_to(ROOT))
    DATA_FILES.append((target_dir, [str(rel.relative_to(ROOT))]))

OPTIONS = {
    "iconfile": "AppIcon.icns",
    "argv_emulation": False,
    "plist": {
        "CFBundleName": "H-Walker CORE",
        "CFBundleDisplayName": "H-Walker CORE",
        "CFBundleIdentifier": "com.arlab.hwalker.core",
        "CFBundleShortVersionString": "2.0.0",
        "CFBundleVersion": "2.0.0",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "11.0",
        "NSRequiresAquaSystemAppearance": False,   # support dark mode
        "NSHumanReadableCopyright": "© 2026 ARLAB / H-Walker Project",
    },
    "packages": [
        "backend",
        "tools",
        "fastapi",
        "starlette",
        "uvicorn",
        "pydantic",
        "pandas",
        "numpy",
        "scipy",
        "matplotlib",
        "PIL",
        "anthropic",
    ],
    "includes": [
        "webview",
        "pkg_resources.py2_warn",
    ],
    "excludes": [
        "tkinter",
        "PyQt5",
        "PyQt6",
        "pytest",
    ],
    "strip": True,
    "optimize": 1,
}

setup(
    app=APP,
    name="H-Walker CORE",
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
