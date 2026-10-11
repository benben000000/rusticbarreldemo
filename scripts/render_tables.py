"""
Phase 3 - Render the scraped data into reference tables (Markdown).

Produces research/brand/data_tables.md - the factual backbone of the guidelines.
The narrative/strategic document is authored separately on top of this.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import brandlib as bl  # noqa: E402
from analyze import parse_color, hsl  # noqa: E402

SOURCE_LABEL = {
    "yelp": "Yelp",
    "doordash": "DoorDash",
    "ubereats": "Uber Eats",
    "facebook": "Facebook",
    "instagram": "Instagram",
}


def swatch(hexv: str) -> str:
    return f"`{hexv}`"


def render(analysis: dict) -> str:
    L: list[str] = []
    a = L.append

    a("# The Rustic Barrel - Extracted Brand Data\n")
    a("_Auto-generated from the Scrapling crawl. See the narrative guidelines document "
      "for interpretation._\n")

    # ---------------------------------------------------------------- sources
    a("\n## 1. Source coverage\n")
    a("| Source | Page title | Assets | Typography families | Colour tokens |")
    a("|---|---|---:|---:|---:|")
    for key, s in analysis.get("sources", {}).items():
        label = SOURCE_LABEL.get(key, key)
        fams = len(s["typography"]["computed_families"])
        cols = len(s["colors"]["computed_ranked"])
        a(f"| {label} | {(s.get('title') or '-')[:60]} | {s['asset_count']} | {fams} | {cols} |")

    failed = [r for r in json.loads((bl.BRAND / "asset_manifest.json").read_text(encoding="utf-8"))
              if "error" in r and "dom" not in r]
    if failed:
        a("\n**Not captured:** " + ", ".join(f"`{r['key']}`" for r in failed) + "\n")

    # ------------------------------------------------------------- typography
    a("\n## 2. Typography\n")
    seen_fams: dict[str, dict] = {}
    for key, s in analysis.get("sources", {}).items():
        for f in s["typography"]["computed_families"]:
            slug = f["family"].lower().replace(" ", "")
            if slug not in seen_fams:
                seen_fams[slug] = {**f, "source": SOURCE_LABEL.get(key, key)}
            else:
                seen_fams[slug]["usage"] += f["usage"]

    a("### Computed font families (ranked by usage)\n")
    a("| Family | Usage | Weights | Sizes seen | First seen on |")
    a("|---|---:|---|---|---|")
    for f in sorted(seen_fams.values(), key=lambda x: -x["usage"])[:25]:
        w = ", ".join(f["weights"][:4]) or "-"
        sz = ", ".join(f["sizes"][:4]) or "-"
        a(f"| {f['family']} | {f['usage']} | {w} | {sz} | {f['source']} |")

    ff: dict[str, dict] = {}
    for key, s in analysis.get("sources", {}).items():
        for face in s["typography"]["declared_font_faces"]:
            name = face.get("family") or "?"
            if name not in ff:
                ff[name] = {"face": face, "source": SOURCE_LABEL.get(key, key)}
    if ff:
        a("\n### `@font-face` declarations found in stylesheets\n")
        a("| Family | Weight | Style | Source file | Found on |")
        a("|---|---|---|---|---|")
        for name, v in ff.items():
            f = v["face"]
            a(f"| {name} | {f.get('weight') or '-'} | {f.get('style') or '-'} | "
              f"`{f.get('stylesheet')}` | {v['source']} |")

    # ----------------------------------------------------------------- colour
    a("\n## 3. Colour\n")
    merged: Counter = Counter()
    for key, s in analysis.get("sources", {}).items():
        for c in s["colors"]["computed_ranked"]:
            merged[c["hex"]] += c["score"]
    for key, s in analysis.get("sources", {}).items():
        for hexv, n in s["colors"]["css_tokens"]:
            if parse_color(hexv):
                merged[hexv] += n

    a("### Ranked palette\n")
    a("| Hex | H | S | L | Tone | Chroma | Score |")
    a("|---|---:|---:|---:|---|---|---:|")
    for hexv, score in merged.most_common(32):
        rgb = parse_color(hexv)
        if not rgb:
            continue
        h, l, s = hsl(*rgb)
        tone = "dark" if l < 35 else "mid" if l < 70 else "light"
        chroma = "neutral" if s < 10 else "muted" if s < 45 else "vivid"
        a(f"| {swatch(hexv)} | {round(h)} | {round(s)} | {round(l)} | {tone} | {chroma} | {score} |")

    # Warm / earth-tone check - is the palette actually rustic?
    earth = []
    for hexv, score in merged.most_common(80):
        rgb = parse_color(hexv)
        if not rgb:
            continue
        h, l, s = hsl(*rgb)
        if 12 <= h <= 55 and 8 <= s <= 85 and 10 <= l <= 80:
            earth.append((hexv, score))
    if earth:
        a("\n### Earth-tone subset (hue 12-55 deg = wood, leather, amber, brass)\n")
        a("| Hex | Score |")
        a("|---|---:|")
        for hexv, score in earth[:20]:
            a(f"| {swatch(hexv)} | {score} |")

    # ------------------------------------------------------------------ logos
    a("\n## 4. Logo candidates\n")
    logos = [x for x in analysis["assets"] if x["kind"] == "logo"]
    a(f"{len(logos)} asset(s) matched logo heuristics.\n")
    if logos:
        a("| File | Px | Format | Source URL |")
        a("|---|---|---|---|")
        for x in logos[:40]:
            m = x.get("meta", {})
            px = f"{m.get('w')}x{m.get('h')}" if m else "-"
            a(f"| `{x['file']}` | {px} | {x['ext']} | `{x['url'][:90]}` |")

    # ------------------------------------------------------------ media index
    a("\n## 5. Media inventory\n")
    inv = Counter(x["kind"] for x in analysis["assets"])
    a("| Type | Count |")
    a("|---|---:|")
    for k in ("photo", "video", "logo", "font"):
        a(f"| {k} | {inv.get(k, 0)} |")

    photos = [x for x in analysis["assets"] if x["kind"] == "photo" and x.get("meta")]
    if photos:
        res = Counter(f"{x['meta']['w']}x{x['meta']['h']}" for x in photos)
        a("\n### Most common photo resolutions\n")
        a("| Resolution | Count |")
        a("|---|---:|")
        for r, c in res.most_common(12):
            a(f"| {r} | {c} |")

        # Aggregate palette across the photo library - the real "mood" signal.
        agg: Counter = Counter()
        for x in photos:
            for p in x.get("palette", []):
                agg[p["hex"]] += p["share"]
        if agg:
            a("\n### Aggregate photo palette (mean presence across library)\n")
            a("| Hex | Weight |")
            a("|---|---:|")
            for hexv, w in agg.most_common(24):
                a(f"| {swatch(hexv)} | {w} |")

    # -------------------------------------------------------------------- copy
    a("\n## 6. Copy & messaging\n")
    for key, s in analysis.get("sources", {}).items():
        c = s["copy"]
        a(f"\n### {SOURCE_LABEL.get(key, key)}\n")
        if c.get("meta_title"):
            a(f"- **Title:** {c['meta_title']}")
        if c.get("meta_description"):
            a(f"- **Description:** {c['meta_description']}")
        heads = [h for h in c.get("headings", []) if h.get("text")]
        if heads:
            a("\n**Headings (with their styling):**\n")
            a("| Text | Tag | Family | Size | Weight | Transform | Tracking | Colour |")
            a("|---|---|---|---|---|---|---|---|")
            for h in heads[:20]:
                a(f"| {h['text'][:48]} | {h['tag']} | {h.get('family','')[:22]} | "
                  f"{h.get('size','')} | {h.get('weight','')} | {h.get('transform','')} | "
                  f"{h.get('ls','')} | `{h.get('color','')}` |")

        bs = s.get("business_schema")
        if bs:
            a("\n**Schema.org business data:**\n")
            for k in ("name", "description", "servesCuisine", "priceRange",
                      "telephone", "address", "openingHours", "aggregateRating", "url"):
                if k in bs:
                    a(f"- `{k}`: {json.dumps(bs[k], ensure_ascii=False)[:300]}")

    return "\n".join(L)


def main() -> None:
    analysis = json.loads((bl.BRAND / "analysis.json").read_text(encoding="utf-8"))
    out = bl.BRAND / "data_tables.md"
    out.write_text(render(analysis), encoding="utf-8")
    bl.log(f"tables -> {out}")


if __name__ == "__main__":
    main()
