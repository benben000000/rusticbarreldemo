"""
Hero image selection.

The hero ground should be the room, not the logo. The strongest frame in the
whole crawl is a customer shot of the actual bar: TV wall, chalkboard craft
list, dollar-bill wall. It was captured at Yelp's "large" tier (l.jpg); the
originals sit one tier up at o.jpg, so we try to upgrade before settling.

Emits responsive WebP, a JPEG fallback, and a heavily blurred base layer used
as the frosted ground behind the copy panel.

Output: site/assets/img/hero-room-*
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image, ImageFilter

import brandlib as bl
from scrapling.fetchers import Fetcher

OUT = bl.RESEARCH.parent / "site" / "assets" / "img"


def candidates() -> list[dict]:
    """Every Yelp frame we captured. yelp_parsed.json already records the local
    path for each one, so no filename guessing is needed."""
    parsed = json.loads((bl.BRAND / "yelp_parsed.json").read_text(encoding="utf-8"))
    rows = parsed.get("user_photos_downloaded") or parsed.get("user_photos") or []
    found: list[dict] = []
    for p in rows:
        rel = p.get("file")
        if not rel:
            continue
        f = bl.RESEARCH / rel
        if not f.exists():
            alt = bl.RESEARCH / "media" / "brand_library" / "photos" / Path(rel).name
            f = alt if alt.exists() else None
            if not f:
                continue
        try:
            with Image.open(f) as im:
                w, h = im.size
        except Exception:  # noqa: BLE001
            continue
        found.append({
            "file": f, "url": p.get("url", ""), "w": w, "h": h, "pixels": w * h,
            "caption": (p.get("caption") or "")[:70],
            "kw": p.get("keywords") or [],
        })
    return found


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    found = candidates()
    print(f"  captured frames: {len(found)}")
    for f in found:
        print(f"    {f['w']:>4}x{f['h']:<4} {f['file'].name:<24} {f['caption'][:46]}")

    upgraded: list[dict] = []
    for f in found:
        src, url = f["file"], f["url"]
        if "/l.jpg" in url:
            orig = url.replace("/l.jpg", "/o.jpg")
            # url.rsplit("/", 2)[-1] is just "l.jpg" for a bphoto URL, which
            # made every temp file collide on orig-l.jpg and silently overwrite
            # each other. Key the temp name on the bphoto id instead.
            pid = url.split("/bphoto/")[-1].split("/")[0]
            tmp = bl.MEDIA / "photos" / f"orig-{pid}.jpg"

            # Already have the original on disk? Use it. Re-fetching on every
            # run made the pipeline non-idempotent: one rate-limited request
            # and the hero silently fell back to the 533x400 capture, which
            # looks fine at 1024 and terrible at 1440. Nothing here changes
            # between runs, so the network is only worth touching once.
            have = False
            if tmp.exists():
                try:
                    with Image.open(tmp) as im:
                        have = im.width > f["w"]
                except Exception:  # noqa: BLE001
                    have = False

            if not have:
                try:
                    r = Fetcher.get(orig, impersonate="chrome", timeout=45)
                    if r.status == 200 and len(r.body) > 40000:
                        tmp.write_bytes(r.body)
                        with Image.open(tmp) as im:
                            w, h = im.size
                        if w > f["w"]:
                            print(f"    upgraded {f['w']}x{f['h']} -> {w}x{h}  {tmp.name}")
                            f = {**f, "file": tmp, "w": w, "h": h, "pixels": w * h}
                except Exception:  # noqa: BLE001
                    print(f"    ! fetch failed for {pid}, keeping {f['file'].name}")
            else:
                with Image.open(tmp) as im:
                    w, h = im.size
                f = {**f, "file": tmp, "w": w, "h": h, "pixels": w * h}
                print(f"    cached  {w}x{h}  {tmp.name}")
        upgraded.append(f)

    if not upgraded:
        print("!! no hero candidate")
        return

    # A landscape frame suits a wide hero; prefer it, then resolution.
    upgraded.sort(key=lambda x: (0 if x["w"] >= x["h"] else 1, -x["pixels"]))
    pick = upgraded[0]
    print(f"\n  picked: {pick['file'].name}  {pick['w']}x{pick['h']}")

    with Image.open(pick["file"]) as im:
        src = im.convert("RGB")

    made: list[str] = []
    for w in (640, 1024, 1440, 1920):
        if w > src.width * 1.15:
            continue
        h = round(src.height * (w / src.width))
        out = OUT / f"hero-room-{w}.webp"
        src.resize((w, h), Image.LANCZOS).save(out, "WEBP", quality=78, method=6)
        made.append(out.name)

    fb_w = min(1440, src.width)
    fb_h = round(src.height * (fb_w / src.width))
    src.resize((fb_w, fb_h), Image.LANCZOS).save(
        OUT / "hero-room-1440.jpg", "JPEG", quality=76, optimize=True, progressive=True)

    # Frosted base layer: a tiny blurred blow-up. Cheap to decode, and because
    # it is blurred, the source resolution barely matters.
    blur = src.copy()
    blur.thumbnail((72, 72), Image.LANCZOS)
    blur = blur.filter(ImageFilter.GaussianBlur(radius=2.2))
    blur = blur.resize((fb_w, fb_h), Image.BICUBIC)
    blur.save(OUT / "hero-room-blur.webp", "WEBP", quality=40, method=5)

    (bl.BRAND / "hero_source.json").write_text(json.dumps({
        "chosen": str(pick["file"].name),
        "source_pixels": f'{pick["w"]}x{pick["h"]}',
        "caption": pick["caption"],
        "variants": made + ["hero-room-1440.jpg", "hero-room-blur.webp"],
    }, indent=2), encoding="utf-8")

    for n in made + ["hero-room-1440.jpg", "hero-room-blur.webp"]:
        p = OUT / n
        print(f"  {n:<26} {p.stat().st_size:>9,}B")


if __name__ == "__main__":
    main()
