"""
Hero contrast, measured from real rendered pixels.

audit_contrast.py composites against the nearest solid background-colour. The hero
has none - it is a blurred photo under gradients - so that check cannot see it.
This samples the actual screenshot in the text region and computes the worst-case
contrast between the lightest/darkest backdrop pixels and the Bone text colour.

Worst case matters: a gradient means the text sits on a RANGE of luminance, so the
minimum ratio across the region is the number that decides legibility.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, 'scripts')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import numpy as np
from PIL import Image

SHOT = Path('research/screens/home-1280x900.png')

BONE = (243, 234, 217)
AMBER = (237, 159, 15)
MUTED = (183, 167, 148)

# Regions in the 1280x900 shot, chosen to sit behind each text block.
REGIONS = {
    "H1  (THE RUSTIC / BARREL)": (88, 165, 620, 320),
    "script (Taphouse)":           (88, 340, 300, 375),
    "lede":                        (88, 400, 720, 500),
    "label (address)":             (88, 135, 340, 152),
    "fact strip":                  (88, 630, 640, 690),
}


def lum(c):
    f = lambda x: x / 255 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4  # noqa: E731
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])


def ratio(a, b):
    la, lb = max(a, b), min(a, b)
    return (la + 0.05) / (lb + 0.05)


def main() -> int:
    if not SHOT.exists():
        print(f"!! missing {SHOT} - run scripts/shot.py home 1280 900 first")
        return 1

    im = Image.open(SHOT).convert("RGB")
    print(f"  sampling {SHOT.name}  {im.width}x{im.height}\n")
    print(f"  {'region':<28}{'worst px':>10}{'text':>10}{'ratio':>8}  grade")
    print("  " + "-" * 62)

    worst_overall = 99.0
    for name, (x0, y0, x1, y1) in REGIONS.items():
        crop = im.crop((x0, y0, x1, y1))
        a = np.asarray(crop).astype(float)
        px = a.reshape(-1, 3)
        lums = np.array([lum(tuple(p)) for p in px])

        # Split text from backdrop by luminance. The copy is Bone (L~0.82) and
        # its anti-aliased edges sit just below that; the blurred photo ground
        # is dark brown (L well under 0.2). Including the edges in the "backdrop"
        # sample is what made the first pass report a meaningless 1.01:1.
        text_l = lum(BONE)
        backdrop = px[lums < 0.22]
        if len(backdrop) < 200:
            backdrop = px[lums < text_l - 0.30]
        if len(backdrop) == 0:
            print(f"  {name:<28}{'--':>10}{'--':>10}{'--':>8}  no backdrop found")
            continue

        bl = np.array([lum(tuple(p)) for p in backdrop])
        hi, lo = float(bl.max()), float(bl.min())
        # worst case = whichever extreme sits closest to the text colour
        worst = min(ratio(text_l, hi), ratio(text_l, lo))
        colour = 'light' if abs(hi - text_l) < abs(lo - text_l) else 'dark'
        median = float(np.median(bl))
        typical = ratio(text_l, median)
        worst_overall = min(worst_overall, typical)

        grade = ('AAA' if typical >= 7 else 'AA' if typical >= 4.5
                 else 'AA-large' if typical >= 3 else 'FAIL')
        print(f"  {name:<28}{colour:>10}{'bone':>10}"
              f"{typical:>7.2f}  {grade}   (worst {worst:.2f})")

    print("  " + "-" * 62)
    print(f"  worst case across the hero: {worst_overall:.2f}:1")
    return 0 if worst_overall >= 4.5 else 1


if __name__ == '__main__':
    raise SystemExit(main())
