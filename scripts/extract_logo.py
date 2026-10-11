"""
Extract the client's REAL logo from the crawled assets.

build_logo.py drew a DRAFT reconstruction when the actual mark was already in the
crawl. That was the wrong instinct. The genuine engraved barrel - black line art
with hop cones, "The Rustic Barrel" lettered on the barrel head - was sitting in
DoorDash's own store cover at
  media/restaurant/cover/4344682f-ee49-4e45-b109-6b0ce6abf3a8.png

This script only EXTRACTS and prepares it. Nothing is redrawn:
  logo-mark.png        faithful, white ground, cropped to the subject
  logo-mark.webp       same, WebP
  logo-mark-dark.png   same artwork, ground swapped to Charred Oak so it sits on
                       the site without a white box - a ground treatment, not a
                       redesign
  logo-mark.png        avatar/favicon square crop

Run:  .venv\\Scripts\\python.exe scripts\\extract_logo.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "research" / "media" / "logo_candidates" / "restaurant-cover.png"
OUT = ROOT / "site" / "assets" / "img"

CHARRED = (31, 22, 16)
BONE = (243, 234, 217)

PROVENANCE = {
    "asset": "The Rustic Barrel engraved barrel logo",
    "found_at": "DoorDash store cover image",
    "source_url": ("https://doordash-static.s3.amazonaws.com/media/restaurant/"
                   "cover/4344682f-ee49-4e45-b109-6b0ce6abf3a8.png"),
    "local_source": "research/media/logo_candidates/restaurant-cover.png",
    "treatment": ("Extracted only. The subject is cropped from its white ground "
                  "using the alpha-safe bounding box of non-white pixels. Two "
                  "ground variants are produced (white / Charred Oak) because the "
                  "artwork is black line art and would be invisible on the dark "
                  "site. No lettering, shape or proportion was altered."),
}


def subject_bbox(im: Image.Image, thresh: int = 244) -> tuple[int, int, int, int]:
    a = np.asarray(im.convert("L"))
    mask = a < thresh
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return (0, 0, im.width, im.height)
    return (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)


def pad(box, w, h, p):
    x0, y0, x1, y1 = box
    return (max(0, x0 - p), max(0, y0 - p),
            min(w, x1 + p), min(h, y1 + p))


def main() -> None:
    if not SRC.exists():
        print(f"!! source missing: {SRC}")
        return
    OUT.mkdir(parents=True, exist_ok=True)

    with Image.open(SRC) as im:
        base = im.convert("RGB")

    box = subject_bbox(base)
    box = pad(box, base.width, base.height, 6)
    mark = base.crop(box)
    print(f"  source        {base.width}x{base.height}")
    print(f"  subject bbox  {box}")
    print(f"  cropped mark  {mark.width}x{mark.height}")

    # The source is small (the store cover is the only place this artwork
    # exists). Upscale to a comfortable display size - this adds no detail but
    # avoids browser-side resampling artefacts at the sizes we actually render.
    target_w = 720
    scale = target_w / mark.width
    if scale > 1:
        mark = mark.resize((target_w, round(mark.height * scale)), Image.LANCZOS)
    print(f"  prepared      {mark.width}x{mark.height}")

    mark.save(OUT / "logo-mark.png", "PNG", optimize=True)
    mark.save(OUT / "logo-mark.webp", "WEBP", quality=92, method=6)

    # Charred-Oak ground variant so it drops onto the dark site cleanly.
    # Only the GROUND is recoloured - the black line art is preserved. Simply
    # pasting the mark onto a dark canvas replaces every pixel and leaves an
    # identical file, which is what the first attempt did.
    a = np.asarray(mark.convert("RGB")).astype(float)
    lum = a.mean(axis=2)
    soft = np.clip((lum - 196) / 36.0, 0, 1)   # 0 = ink, 1 = paper ground
    w3 = soft[..., None]
    # paper -> Charred Oak, ink -> untouched. (Weighting the ORIGINAL by
    # (1 - soft) is what keeps the black line art black.)
    mixed = a * (1 - w3) + np.array(CHARRED, float) * w3
    dark_arr = np.clip(mixed, 0, 255).astype("uint8")
    dark = Image.fromarray(dark_arr, "RGB")
    dark.save(OUT / "logo-mark-dark.webp", "WEBP", quality=92, method=6)
    dark.save(OUT / "logo-mark-dark.png", "PNG", optimize=True)

    # Square avatar crop - centre the barrel, fill the frame.
    side = max(mark.size)
    sq = Image.new("RGB", (side, side), CHARRED)
    sq.paste(mark, ((side - mark.width) // 2, (side - mark.height) // 2))
    sq = sq.resize((512, 512), Image.LANCZOS)
    sq.save(OUT / "logo-avatar.png", "PNG", optimize=True)
    sq.save(OUT / "logo-avatar.webp", "WEBP", quality=92, method=6)

    # Favicon sizes
    for s in (192, 512):
        sq.resize((s, s), Image.LANCZOS).save(OUT / f"logo-icon-{s}.png", "PNG")

    # White-ground square, for anywhere a light plate is used.
    light = Image.new("RGB", (side, side), (255, 255, 255))
    light.paste(mark, ((side - mark.width) // 2, (side - mark.height) // 2))
    light.resize((512, 512), Image.LANCZOS).save(OUT / "logo-avatar-light.png", "PNG")

    # Charred-Oak-ground square, for the dark header.
    # This has to be built from `dark`, not from `mark`. side == mark.width and
    # the mark is wider than it is tall, so pasting the ORIGINAL covers the
    # charcoal square edge to edge - the header was showing the bare white
    # paper rectangle. Recolouring the ground first is what leaves the bands
    # above and below the barrel actually charred.
    sq_dark = Image.new("RGB", (side, side), CHARRED)
    sq_dark.paste(dark, ((side - dark.width) // 2, (side - dark.height) // 2))
    # 160px, not 512. This file is only ever displayed at 40px in the header, so
    # a 512px copy cost 67KB on every page load to render the same mark. 160 is
    # still 4x the display size for any density.
    sq_dark = sq_dark.resize((160, 160), Image.LANCZOS)
    sq_dark.save(OUT / "logo-avatar-dark.png", "PNG", optimize=True)
    sq_dark.save(OUT / "logo-avatar-dark.webp", "WEBP", quality=92, method=6)

    (ROOT / "research" / "brand" / "logo_provenance.json").write_text(
        json.dumps({**PROVENANCE,
                    "outputs": ["logo-mark.png", "logo-mark.webp",
                                "logo-mark-dark.png", "logo-mark-dark.webp",
                                "logo-avatar.png", "logo-avatar-dark.png",
                                "logo-avatar-dark.webp",
                                "logo-icon-192.png",
                                "logo-icon-512.png"]}, indent=2),
        encoding="utf-8")

    print()
    for n in ("logo-mark.png", "logo-mark.webp", "logo-mark-dark.png",
              "logo-mark-dark.webp", "logo-avatar.png", "logo-avatar-dark.webp"):
        p = OUT / n
        print(f"  {n:<26} {p.stat().st_size:>8,}B")
    print("\n  provenance -> research/brand/logo_provenance.json")


if __name__ == "__main__":
    main()
