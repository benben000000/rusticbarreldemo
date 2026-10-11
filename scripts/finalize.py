"""
Phase 3 - Final brand distillation + browsable contact sheet.

Palette is computed from the CURATED library only (platform ads excluded),
then merged with the typography / copy signals from the raw manifest.

Outputs:
  research/brand/brand_data.json
  research/brand/contact_sheet.html   <- open in a browser to review every asset
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image

import brandlib as bl
from analyze import parse_color, hsl, dominant_colors, image_meta, distil_typography

MEDIA_TYPES = {".jpg", ".jpeg", ".png", ".webp"}


def main() -> None:
    lib = json.loads((bl.BRAND / "curated_library.json").read_text(encoding="utf-8"))
    manifest = json.loads((bl.BRAND / "asset_manifest.json").read_text(encoding="utf-8"))

    photos = [a for a in lib if a["kind"] != "video"]

    # ---- palette over the curated library --------------------------------- #
    weight: Counter = Counter()
    per_file = []
    for a in photos:
        # library_file is recorded relative to research/media/
        p = bl.MEDIA / a["library_file"]
        pal = dominant_colors(p, 6) if p.exists() else []
        if pal:
            per_file.append({"file": a["library_file"], "source": a.get("source", ""),
                             "palette": pal})
        for c in pal:
            weight[c["hex"]] += c["share"]

    ranked = []
    for hexv, w in weight.most_common(40):
        rgb = parse_color(hexv)
        if not rgb:
            continue
        h, l, s = hsl(*rgb)
        ranked.append({
            "hex": hexv, "rgb": list(rgb), "weight": round(w, 1),
            "hue": round(h), "sat": round(s), "light": round(l),
            "tone": "dark" if l < 35 else "mid" if l < 68 else "light",
            "chroma": "neutral" if s < 12 else "muted" if s < 45 else "vivid",
        })

    # Earth / warm family - the "rustic" signal
    earth = [c for c in ranked if 8 <= c["hue"] <= 55 and c["sat"] >= 10]

    # ---- typography signals ----------------------------------------------- #
    typo = {}
    for rec in manifest:
        if "dom" not in rec:
            continue
        typo[rec["key"]] = distil_typography(rec)

    # ---- videos ------------------------------------------------------------ #
    videos = [a for a in lib if a["kind"] == "video"]

    out = {
        "photo_count": len(photos),
        "video_count": len(videos),
        "palette_ranked": ranked,
        "palette_earth": earth,
        "typography_by_source": typo,
        "per_file_palette": per_file,
        "videos": [{"file": a["library_file"], "bytes": a.get("bytes")}
                   for a in videos],
    }
    bl.dump_json(bl.BRAND / "brand_data.json", out)

    print(f"photos analysed : {len(photos)}")
    print(f"videos          : {len(videos)}")
    print()
    print("--- warm / earth palette (the 'rustic' signal) ---")
    for c in earth[:16]:
        print(f"  {c['hex']}  H{c['hue']:>3} S{c['sat']:>3} L{c['light']:>3}  "
              f"{c['tone']:<5} {c['chroma']:<7} w={c['weight']}")

    # ---- contact sheet ----------------------------------------------------- #
    def thumb(rel: str, cap: str, cls: str = "") -> str:
        import urllib.parse
        return (f'<figure class="{cls}"><img loading="lazy" src="{urllib.parse.quote(rel)}" '
                f'alt="{cap}"><figcaption>{cap}</figcaption></figure>')

    cards = []
    for a in photos:
        cap = Path(a["library_file"]).stem
        cards.append(thumb(f"../media/{a['library_file']}", cap, "photo"))
    for a in videos:
        cap = Path(a["library_file"]).stem
        cards.append(thumb(f"../media/{a['library_file']}", cap, "video"))

    pal_html = "".join(
        f'<div class="sw" style="background:{c["hex"]}"><span>{c["hex"]}<br>'
        f'H{c["hue"]} S{c["sat"]} L{c["light"]}</span></div>'
        for c in ranked[:24]
    )

    sheet = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>The Rustic Barrel - scraped asset library</title>
<style>
 body {{ font-family: ui-sans-serif,system-ui,sans-serif; margin:0; padding:28px;
        background:#191512; color:#f0e6d6; }}
 h1 {{ font-size:24px; margin:0 0 4px; }}
 .sub {{ color:#a89madeup; }}
 p.sub {{ color:#a8968a; margin:0 0 26px; font-size:14px; }}
 .sw {{ display:inline-block; width:132px; height:96px; margin:0 6px 10px 0;
        border-radius:6px; position:relative; border:1px solid #00000055; }}
 .sw span {{ position:absolute; bottom:5px; left:7px; font-size:10px;
             font-family:ui-monospace,monospace; color:#fff; text-shadow:0 1px 3px #000; }}
 .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(200px,1fr));
         gap:12px; margin-top:14px; }}
 figure {{ margin:0; background:#241f1a; border-radius:8px; overflow:hidden; }}
 figure img {{ width:100%; height:190px; object-fit:cover; display:block; }}
 figure figcaption {{ font-size:10px; padding:6px 8px; color:#9d8d80;
                      font-family:ui-monospace,monospace;
                      overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
 figure.video img {{ object-fit:contain; background:#000; }}
</style></head><body>
<h1>The Rustic Barrel &mdash; scraped asset library</h1>
<p class="sub">{len(photos)} photos &middot; {len(videos)} videos &middot;
 harvested with Scrapling from Instagram, Facebook, DoorDash and Uber Eats</p>
<h2 style="font-size:16px;margin:26px 0 8px">Extracted palette</h2>
{''.join(cards) and '<div class="grid">' + ''.join(cards) + '</div>'}
</body></html>"""

    # palette strip goes above the grid
    sheet = sheet.replace("<h2 style=\"font-size:16px;margin:26px 0 8px\">Extracted palette</h2>",
                          f"<h2 style=\"font-size:16px;margin:26px 0 8px\">Extracted palette</h2>{pal_html}")

    sheet = sheet.replace(".sub { color:#a89madeup; }", "")
    (bl.BRAND / "contact_sheet.html").write_text(sheet, encoding="utf-8")
    print(f"\ncontact sheet -> {bl.BRAND / 'contact_sheet.html'}")


if __name__ == "__main__":
    main()
