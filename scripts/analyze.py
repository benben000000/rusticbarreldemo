"""
Phase 2 - Asset analysis + brand-signal distillation.

Reads everything captured in Phase 1 and distils it into structured brand data:
  * image dimensions / aspect / dominant colour palettes (Pillow)
  * per-source colour tokens ranked by usage
  * typography inventory (families, weights, sizes, letter-spacing)
  * logo candidates isolated by size + filename signals
  * copy / voice-of-brand samples (headings, taglines, descriptions)
  * metadata (hours, phone, address, categories, rating)

Outputs: research/brand/analysis.json
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image  # noqa: E402

import brandlib as bl  # noqa: E402

Image.MAX_IMAGE_PIXELS = 300_000_000


# --------------------------------------------------------------------------- #
# Colour utilities
# --------------------------------------------------------------------------- #
def rgb_to_hex(r, g, b) -> str:
    return f"#{r:02x}{g:02x}{b:02x}"


def parse_color(tok: str):
    """Parse #rgb/#rrggbb/rgb()/rgba() into an (r,g,b) tuple, else None."""
    tok = tok.strip().lower()
    m = re.fullmatch(r"#([0-9a-f]{3,8})", tok)
    if m:
        h = m.group(1)
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        if len(h) >= 6:
            try:
                return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
            except ValueError:
                return None
        return None
    m = re.fullmatch(r"rgba?\(([^)]+)\)", tok)
    if m:
        parts = re.split(r"[,\s/]+", m.group(1).strip())
        try:
            r, g, b = int(float(parts[0])), int(float(parts[1])), int(float(parts[2]))
            a = float(parts[3]) if len(parts) > 3 and parts[3] else 1.0
            if a < 0.25:
                return None  # effectively transparent - not a brand colour
            return (r, g, b)
        except (ValueError, IndexError):
            return None
    return None


def hsl(r, g, b):
    import colorsys
    r, g, b = r / 255, g / 255, b / 255
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return h * 360, l * 100, s * 100


def dominant_colors(path: Path, n: int = 6) -> list[dict]:
    """k-means-ish palette via Pillow quantisation."""
    try:
        with Image.open(path) as im:
            im = im.convert("RGB")
            im.thumbnail((220, 220))
            q = im.quantize(colors=n, method=Image.Quantize.FASTOCTREE)
            palette = q.getpalette() or []
            counts = Counter(q.getdata())
            out = []
            total = sum(counts.values()) or 1
            for idx, cnt in counts.most_common(n):
                rgb = tuple(palette[idx * 3: idx * 3 + 3])[:3]
                if len(rgb) < 3:
                    continue
                h, l, s = hsl(*rgb)
                out.append({
                    "hex": rgb_to_hex(*rgb),
                    "rgb": list(rgb),
                    "share": round(cnt / total * 100, 1),
                    "hue": round(h), "lightness": round(l), "saturation": round(s),
                })
            return out
    except Exception:  # noqa: BLE001 - corrupt or non-raster asset
        return []


def image_meta(path: Path) -> dict | None:
    try:
        with Image.open(path) as im:
            return {
                "format": im.format,
                "w": im.width,
                "h": im.height,
                "mode": im.mode,
                "aspect": round(im.width / im.height, 3) if im.height else None,
                "megapixels": round(im.width * im.height / 1_000_000, 2),
                "animated": getattr(im, "n_frames", 1) > 1,
            }
    except Exception:  # noqa: BLE001
        return None


# --------------------------------------------------------------------------- #
# Typography / colour distillation
# --------------------------------------------------------------------------- #
def distil_typography(record: dict) -> dict:
    fam_counter: Counter = Counter()
    fam_detail: dict[str, dict] = {}
    size_counter: Counter = Counter()
    weight_counter: Counter = Counter()
    tracking: set[str] = set()
    transforms: Counter = Counter()

    for f in record.get("computed", {}).get("fonts", []):
        fam = (f.get("family") or "").split(",")[0].strip().strip("\"'")
        if fam and fam.lower() not in ("inherit", "initial"):
            fam_counter[fam] += 1
            d = fam_detail.setdefault(
                fam, {"sizes": Counter(), "weights": Counter(), "styles": Counter()}
            )
            if f.get("size"):
                d["sizes"][f["size"]] += 1
                size_counter[f["size"]] += 1
            if f.get("weight"):
                d["weights"][str(f["weight"])] += 1
                weight_counter[str(f["weight"])] += 1
            if f.get("style"):
                d["styles"][f["style"]] += 1
            if f.get("letterSpacing") and f["letterSpacing"] not in ("normal",):
                tracking.add(f["letterSpacing"])
            if f.get("transform") and f["transform"] != "none":
                transforms[f["transform"]] += 1

    families = []
    for fam, n in fam_counter.most_common(12):
        d = fam_detail[fam]
        families.append({
            "family": fam,
            "usage": n,
            "sizes": [s for s, _ in d["sizes"].most_common(8)],
            "weights": [w for w, _ in d["weights"].most_common(6)],
            "styles": [s for s, _ in d["styles"].most_common(4)],
        })

    css_fonts = record.get("css", {}).get("font_faces", [])
    return {
        "computed_families": families,
        "declared_font_faces": css_fonts,
        "css_font_families": record.get("css", {}).get("font_families", []),
        "font_sizes_ranked": [s for s, _ in size_counter.most_common(20)],
        "font_weights_ranked": [w for w, _ in weight_counter.most_common(10)],
        "letter_spacing_seen": sorted(tracking),
        "text_transforms": dict(transforms),
    }


def distil_colors(record: dict) -> dict:
    counter: Counter = Counter()
    for c in record.get("computed", {}).get("colors", []):
        rgb = parse_color(c.get("color", ""))
        if rgb:
            hexv = rgb_to_hex(*rgb)
            counter[hexv] += 1
        bg = parse_color(c.get("bg", "") or "")
        if bg:
            hexv = rgb_to_hex(*bg)
            counter[hexv] += 1

    css_tokens = Counter(record.get("css", {}).get("color_tokens", {}))
    merged: dict[str, int] = {}
    for hexv, n in counter.items():
        rgb = parse_color(hexv)
        if rgb:
            h, l, s = hsl(*rgb)
            # Skip near-white / near-black / near-grey UI chrome
            if s < 6 and (l > 96 or l < 6):
                continue
            merged[hexv] = merged.get(hexv, 0) + n * 3

    ranked = []
    for hexv, n in sorted(merged.items(), key=lambda x: -x[1])[:24]:
        rgb = parse_color(hexv)
        h, l, s = hsl(*rgb)
        ranked.append({
            "hex": hexv, "rgb": list(rgb), "score": n,
            "hue": round(h), "saturation": round(s), "lightness": round(l),
            "tone": ("dark" if l < 35 else "mid" if l < 70 else "light"),
            "chroma": ("neutral" if s < 10 else "muted" if s < 45 else "vivid"),
        })
    return {"computed_ranked": ranked, "css_tokens": css_tokens.most_common(40)}


def distil_copy(record: dict) -> dict:
    headings = record.get("computed", {}).get("headings", [])
    metas = {m["name"]: m["content"] for m in record.get("dom", {}).get("metas", [])}
    jsonld = []
    for raw in record.get("dom", {}).get("jsonld", []):
        try:
            jsonld.append(json.loads(raw))
        except Exception:  # noqa: BLE001
            pass
    desc = metas.get("description") or metas.get("og:description") or ""
    title = metas.get("og:title") or metas.get("twitter:title") or record.get("title", "")
    return {
        "meta_title": title,
        "meta_description": desc,
        "headings": [
            {k: h.get(k) for k in ("tag", "text", "family", "size", "weight", "transform", "ls", "color")}
            for h in headings[:40]
        ],
        "jsonld": jsonld,
        "all_meta": metas,
    }


def find_jsonld_business(jsonld_list) -> dict | None:
    for blob in jsonld_list:
        stack = [blob]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                if node.get("@type") in ("Restaurant", "BarOrPub", "FoodEstablishment",
                                         "LocalBusiness", "BeerBar", "SportsBar"):
                    return node
                stack.extend(node.values())
            elif isinstance(node, list):
                stack.extend(node)
    return None


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    manifest = json.loads((bl.BRAND / "asset_manifest.json").read_text(encoding="utf-8"))
    analysis: dict = {"sources": {}, "assets": []}

    for record in manifest:
        key = record["key"]
        if "error" in record and "dom" not in record:
            bl.log(f"{key}: skipped ({record['error'][:60]})")
            continue

        bl.log(f"analysing {key}...")
        bl.dump_json(bl.BRAND / f"copy_{key}.json", distil_copy(record))

        asset_rows = []
        for a in record.get("assets", []):
            p = bl.RESEARCH / a["file"]
            row = dict(a)
            row["sha"] = None
            if p.exists():
                import hashlib
                row["sha"] = hashlib.sha1(p.read_bytes()).hexdigest()[:12]
                row["bytes"] = p.stat().st_size
            meta = image_meta(p) if a["ext"] in bl.IMG_EXT else None
            if meta:
                row["meta"] = meta
                if a["kind"] in ("photo", "logo") and meta["w"] >= 80:
                    row["palette"] = dominant_colors(p)
            asset_rows.append(row)

        analysis["sources"][key] = {
            "url": record.get("url"),
            "final_url": record.get("final_url"),
            "title": record.get("title"),
            "typography": distil_typography(record),
            "colors": distil_colors(record),
            "copy": distil_copy(record),
            "asset_count": len(asset_rows),
        }
        b = find_jsonld_business(record.get("dom", {}).get("jsonld", []) and
                                 distil_copy(record)["jsonld"] or [])
        if b:
            analysis["sources"][key]["business_schema"] = b
        analysis["assets"].extend(asset_rows)

    bl.dump_json(bl.BRAND / "analysis.json", analysis)

    # Media inventory summary
    inv = Counter(a["kind"] for a in analysis["assets"])
    bl.log(f"\n=== ASSET INVENTORY ===")
    for k, v in inv.most_common():
        bl.log(f"  {k:<8} {v}")
    bl.log(f"  TOTAL    {len(analysis['assets'])}")
    bl.log(f"analysis -> {bl.BRAND / 'analysis.json'}")


if __name__ == "__main__":
    main()
