"""Card art for the three home-page feature badges.

The badges were typographic only - a circle with TAP ROOM / SANTA MARIA /
BIG SCREEN set inside - which left three large empty discs above the copy. They
now carry a photograph of the thing each card is about.

Source frames are the customer's own Yelp shots, pulled at the original tier
rather than the "large" tier the crawl captured. All three are real photos of
the real room; nothing here is stock or generated.

Crops are square and the circle is done in CSS, so there is no alpha channel to
carry and no seam to hide. Focal points are given as a fraction of the frame so
the crop is explicit and reviewable rather than a blind centre crop - the
sources are 3:4 portraits full of ceiling and floor, and a centred square would
have framed the light fittings.

Output: site/assets/img/card-<slug>-{160,320}.webp
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from PIL import Image, ImageEnhance

import brandlib as bl

OUT = bl.RESEARCH.parent / "site" / "assets" / "img"

# slug -> (yelp photo id, focal x, focal y, square side as a fraction of the
# shorter edge, alt text)
#
# Focal points read off the sources with scripts/grid_sources.py, which draws a
# labelled percentage grid plus the box the current values produce. Guessing
# them from memory is what put the first tap room crop on nothing but ceiling:
#   taproom    chalkboard of craft names sits at 66-76%h, tap handles 76-84%h.
#              Centre on 75% and keep the square tight, so the crop is the chalk
#              board and the taps rather than the light fittings above them.
#   santamaria the tray is already centred; a wide square keeps the tri-tip, the
#              ribs and the salad in one frame.
#   bigscreen  screens at 18-32%h, chalkboard 35-40%h, taps 40-48%h. A square
#              spanning 17-46%h holds all three; the first pass started at 6%h
#              and spent a third of the frame on ceiling.
CARDS = {
    "taproom": dict(
        photo="Bu5XawbtCnVdAWeQjSAdFg",
        fx=0.40, fy=0.75, side=0.34,
        alt="The multi-tap bar: a hand-lettered chalkboard listing California "
            "craft above a row of tap handles",
    ),
    "santamaria": dict(
        photo="C-B1y7xOqceF6bAzQtQKgA",
        fx=0.50, fy=0.52, side=0.86,
        alt="A three-meat plate: sliced Santa Maria tri-tip, slow-smoked ribs, "
            "house fries and a side salad",
    ),
    "bigscreen": dict(
        photo="-vh3S4SYXHDF4mBMqwow2w",
        fx=0.45, fy=0.35, side=0.38,
        alt="A row of four wall-mounted screens showing live sport above the "
            "bar's chalkboard beer list",
    ),
}

WIDTHS = (160, 320)


def square(im: Image.Image, fx: float, fy: float, side: float) -> Image.Image:
    """Square crop of `side` x the shorter edge, centred on a focal fraction."""
    w, h = im.size
    s = max(1, int(round(min(w, h) * side)))
    s = min(s, w, h)
    cx, cy = w * fx, h * fy
    x0 = int(round(min(max(cx - s / 2, 0), w - s)))
    y0 = int(round(min(max(cy - s / 2, 0), h - s)))
    return im.crop((x0, y0, x0 + s, y0 + s))


def grade(im: Image.Image) -> Image.Image:
    """Pull the photos a little toward the site so they do not read as pasted on.

    Light touch only: a touch more contrast, a touch less saturation, and a
    faint warm bias matching Charred Oak. Heavier grading would start inventing
    a room that does not exist.
    """
    im = ImageEnhance.Contrast(im).enhance(1.06)
    im = ImageEnhance.Color(im).enhance(0.94)
    warm = Image.new("RGB", im.size, (196, 138, 74))
    return Image.blend(im, warm, 0.06)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    provenance = []

    for slug, spec in CARDS.items():
        src_path = bl.MEDIA / "photos" / f"orig-{spec['photo']}.jpg"
        if not src_path.exists():
            print(f"  !! missing source for {slug}: {src_path.name}")
            return 1

        with Image.open(src_path) as raw:
            im = raw.convert("RGB")
        cropped = grade(square(im, spec["fx"], spec["fy"], spec["side"]))

        made = []
        for w in WIDTHS:
            out = OUT / f"card-{slug}-{w}.webp"
            cropped.resize((w, w), Image.LANCZOS).save(
                out, "WEBP", quality=82, method=6)
            made.append(out.name)

        provenance.append({
            "slug": slug,
            "source": f"yelp bphoto {spec['photo']}",
            "source_file": src_path.name,
            "source_size": f"{im.width}x{im.height}",
            "crop": f"square, focal ({spec['fx']}, {spec['fy']}), "
                    f"side {spec['side']}",
            "alt": spec["alt"],
            "variants": made,
        })
        print(f"  {slug:<12} <- {src_path.name:<34} {im.width}x{im.height}  "
              f"-> {', '.join(made)}")

    (bl.BRAND / "card_art.json").write_text(
        json.dumps(provenance, indent=2), encoding="utf-8")

    print()
    for p in provenance:
        for n in p["variants"]:
            f = OUT / n
            print(f"  {n:<26} {f.stat().st_size:>8,}B")
    print("\n  provenance -> research/brand/card_art.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
