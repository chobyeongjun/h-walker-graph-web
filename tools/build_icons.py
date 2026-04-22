#!/usr/bin/env python3
"""
Regenerate H-Walker CORE app icons from the master SVG.

Input  : frontend/public/logo-hwalker.svg
Outputs:
    AppIcon.icns                         — macOS .app bundle
    frontend/public/AppIcon.ico          — Windows / pyinstaller
    frontend/public/icons/icon-<size>.png — individual rasters (for
                                             web + Linux .desktop files)
    frontend/public/favicon.png          — 48×48 favicon
    desktop/icon.png                     — 512×512 copy for pywebview

Run:
    python3 tools/build_icons.py
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

import cairosvg
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
# Full-detail master — used for large sizes (≥64) where every tick / grid
# line / cue-circle is legible.
SRC_FULL = ROOT / "frontend" / "public" / "logo-hwalker.svg"
# Simplified master — grid + horizontal baseline + H-ticks dropped, stroke
# thickened. Used for tiny tab/favicon sizes where the full mark would
# render as an indistinct blob (the "purple lightning" artifact).
SRC_TINY = ROOT / "frontend" / "public" / "favicon.svg"

OUT_ICNS = ROOT / "AppIcon.icns"
OUT_ICO = ROOT / "frontend" / "public" / "AppIcon.ico"
OUT_FAVICON = ROOT / "frontend" / "public" / "favicon.png"
OUT_PNG_DIR = ROOT / "frontend" / "public" / "icons"
OUT_DESKTOP_PNG = ROOT / "desktop" / "icon.png"

ICNS_SIZES = (16, 32, 64, 128, 256, 512, 1024)
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)

PNG_SIZES = sorted(set(ICNS_SIZES) | set(ICO_SIZES) | {192, 384})

# Sizes below this use the simplified SRC_TINY source.
TINY_CUTOFF = 48


def rasterize(size: int) -> Image.Image:
    """Rasterize the right master SVG at `size`×`size` px.

    Below TINY_CUTOFF we use the simplified mark so the stride curve
    stays legible; at larger sizes we use the full mark with grid +
    H-ticks.
    """
    src = SRC_TINY if size < TINY_CUTOFF else SRC_FULL
    png_bytes = cairosvg.svg2png(
        url=str(src),
        output_width=size,
        output_height=size,
    )
    from io import BytesIO
    return Image.open(BytesIO(png_bytes)).convert("RGBA")


def main() -> None:
    if not SRC_FULL.exists():
        raise SystemExit(f"master SVG missing: {SRC_FULL}")
    if not SRC_TINY.exists():
        raise SystemExit(f"simplified favicon SVG missing: {SRC_TINY}")

    # 1. Individual PNGs
    OUT_PNG_DIR.mkdir(parents=True, exist_ok=True)
    rasters: dict[int, Image.Image] = {}
    for size in PNG_SIZES:
        img = rasterize(size)
        rasters[size] = img
        img.save(OUT_PNG_DIR / f"icon-{size}.png", optimize=True)
        print(f"  png @ {size:4d} → {OUT_PNG_DIR / f'icon-{size}.png'}")

    # 2. Favicon (48×48)
    rasters[48].save(OUT_FAVICON, optimize=True)
    print(f"  favicon → {OUT_FAVICON}")

    # 3. Desktop copy
    OUT_DESKTOP_PNG.parent.mkdir(parents=True, exist_ok=True)
    rasters[512].save(OUT_DESKTOP_PNG, optimize=True)
    print(f"  desktop → {OUT_DESKTOP_PNG}")

    # 4. Windows .ico (multi-size embedded)
    base = rasters[max(ICO_SIZES)].copy()
    base.save(
        OUT_ICO,
        format="ICO",
        sizes=[(s, s) for s in ICO_SIZES],
    )
    print(f"  ico     → {OUT_ICO}  ({OUT_ICO.stat().st_size:,} bytes)")

    # 5. macOS .icns
    # Pillow's ICNS writer picks up the available sizes from the
    # "sizes" kwarg; only certain sizes are allowed by the format:
    # 16, 32, 64, 128, 256, 512, 1024. The 1024 slot is the retina
    # variant of 512.
    base_big = rasters[1024].copy()
    base_big.save(
        OUT_ICNS,
        format="ICNS",
        sizes=[(s, s) for s in ICNS_SIZES],
    )
    print(f"  icns    → {OUT_ICNS}  ({OUT_ICNS.stat().st_size:,} bytes)")

    # 6. Sanity summary
    print()
    print("Icon generation complete.")
    print(f"  full SVG    : {SRC_FULL.relative_to(ROOT)}  ({SRC_FULL.stat().st_size} bytes)")
    print(f"  tiny SVG    : {SRC_TINY.relative_to(ROOT)}  ({SRC_TINY.stat().st_size} bytes)")
    print(f"  .icns       : {OUT_ICNS.relative_to(ROOT)}  "
          f"({OUT_ICNS.stat().st_size:,} bytes)")
    print(f"  .ico        : {OUT_ICO.relative_to(ROOT)}  "
          f"({OUT_ICO.stat().st_size:,} bytes)")
    print(f"  png rasters : {len(PNG_SIZES)} sizes in "
          f"{OUT_PNG_DIR.relative_to(ROOT)}")
    shutil_unused = shutil  # kept imported for future cleanup ops
    _ = shutil_unused


if __name__ == "__main__":
    main()
