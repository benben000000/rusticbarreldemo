"""Render each card-art source with a labelled percentage grid.

Picking a crop by eye off a remembered image does not work - the tap room
frame came back as nothing but ceiling because the focal fraction was guessed
against the wrong reading of the photo. This draws the grid so the focal point
can be read off the actual pixels and written into build_card_art.py.

Usage: .venv\\Scripts\\python.exe scripts\\grid_sources.py [slug ...]
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from PIL import Image, ImageDraw, ImageFont

import brandlib as bl
from build_card_art import CARDS

OUT = bl.RESEARCH / "screens"


def font(px: int):
    for name in ("segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, px)
        except Exception:  # noqa: BLE001
            continue
    return ImageFont.load_default()


def main() -> int:
    slugs = sys.argv[1:] or list(CARDS)
    OUT.mkdir(parents=True, exist_ok=True)
    f = font(22)

    for slug in slugs:
        spec = CARDS[slug]
        src = bl.MEDIA / "photos" / f"orig-{spec['photo']}.jpg"
        im = Image.open(src).convert("RGB")
        w, h = im.size
        d = ImageDraw.Draw(im, "RGBA")

        for pct in range(10, 100, 10):
            x = int(w * pct / 100)
            d.line([(x, 0), (x, h)], fill=(255, 214, 10, 150), width=2)
            d.text((x + 3, 4), str(pct), font=f, fill=(255, 240, 170, 255))
            y = int(h * pct / 100)
            d.line([(0, y), (w, y)], fill=(255, 214, 10, 150), width=2)
            d.text((4, y + 3), str(pct), font=f, fill=(255, 240, 170, 255))

        # the square the current focal point produces, so a wrong one is obvious
        s = int(round(min(w, h) * spec["side"]))
        cx, cy = int(w * spec["fx"]), int(h * spec["fy"])
        x0 = min(max(cx - s // 2, 0), w - s)
        y0 = min(max(cy - s // 2, 0), h - s)
        d.rectangle([x0, y0, x0 + s, y0 + s], outline=(255, 60, 60, 255), width=5)

        out = OUT / f"grid-{slug}.png"
        im.save(out)
        print(f"  {slug:<12} {w}x{h}  current crop y {y0}..{y0+s} "
              f"({y0/h:.0%}..{(y0+s)/h:.0%})  -> {out.name}")

    print("\n  red box = what build_card_art.py crops today")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
