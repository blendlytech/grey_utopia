"""crop_scenes.py -- Cut the painted scene originals down to the UI's scene band.

Downstream of copy_assets.py. The originals in data/assets/originals/ are 1024x1024
paintings that all put a person in the middle of the frame; the UI wants places, not
portraits, so each scene takes a full-width horizontal band that misses the figures.
Output goes to data/assets/*.jpg, which is what server.py serves and grey_utopia.spec
bundles (originals/ is excluded from both).

Band geometry: .scene-header is 200px tall and its width swings with the layout --
~330px at 1101px viewport (3-column, narrow centre), ~670px at the 1440px desktop
default, ~1045px at 1100px (single column). So the stage runs anywhere from 1.65:1 to
5.2:1 and no single crop is exact. These are cut at 4:1, which sits between the common
cases; CSS `background-size: cover` absorbs the rest.

Re-running is idempotent. To retune one band without editing the table:

    python pipeline/crop_scenes.py steward_sanctuary=230

Run: python pipeline/crop_scenes.py
"""
from __future__ import annotations
import os
import sys

from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(ROOT, "data", "assets", "originals")
OUT_DIR = os.path.join(ROOT, "data", "assets")

WIDTH = 1024
HEIGHT = 256          # 4:1 at full source width
QUALITY = 90          # dark painted art; keeps every band well under 400 KB

# scene name -> (source painting, top y of the band, band height)
#
# The y offsets are load-bearing: each one is the lowest band that still misses
# the painting's figures. Verify visually after changing any of them.
CROPS = {
    # Workbench below the fixer's hands: cases, tools, cables, ACCESS GRANTED.
    "fixer_hideout":      ("fixer_hideout.png", 700, HEIGHT),
    # Ceiling pipes and signage above the booths; everyone is seated lower.
    "vice_lounge":        ("vice_lounge.png", 55, HEIGHT),
    # Ends at y=468 -- the reclining figure's hair starts at y=470.
    "steward_sanctuary":  ("steward_sanctuary.png", 212, HEIGHT),
    # Skyline, storm and fence line; the walker enters at y=555.
    "offgrid_wilderness": ("offgrid_wilderness.png", 235, HEIGHT),
    # Despite the filename, overdose_collapse.png is a rain-slick neon street,
    # so it supplies two scenes. Upper band = the street itself, which is the
    # only art the "street" scene key has.
    "street":             ("overdose_collapse.png", 150, HEIGHT),
    # Lower band = empty wet asphalt, behind terminal endings. Starts at y=810
    # because the walker's legs are in frame down to ~808, which leaves it
    # short of a full 256 -- 4.8:1 rather than 4:1.
    "overdose_collapse":  ("overdose_collapse.png", 810, 214),
}


def main(argv: list[str]) -> int:
    crops = dict(CROPS)
    for arg in argv:
        name, _, y = arg.partition("=")
        if name not in crops or not y.isdigit():
            print(f"crop_scenes: expected <scene>=<y> from {sorted(crops)}, got {arg!r}")
            return 2
        src, _old_y, height = crops[name]
        crops[name] = (src, int(y), height)

    if not os.path.isdir(SRC_DIR):
        print(f"crop_scenes: no source art at {SRC_DIR}")
        return 1
    os.makedirs(OUT_DIR, exist_ok=True)

    for name, (src, y, height) in crops.items():
        src_path = os.path.join(SRC_DIR, src)
        if not os.path.isfile(src_path):
            print(f"  MISSING {src}")
            return 1
        image = Image.open(src_path).convert("RGB")
        y = max(0, min(y, image.height - height))
        band = image.crop((0, y, WIDTH, y + height))
        dest = os.path.join(OUT_DIR, name + ".jpg")
        band.save(dest, "JPEG", quality=QUALITY, optimize=True, progressive=True)
        print(f"  {name:20s} <- {src:24s} y={y:4d} h={height:3d}  "
              f"{os.path.getsize(dest) / 1024:6.1f} KB")

    print(f"Wrote {len(crops)} scene crops to data/assets/")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
