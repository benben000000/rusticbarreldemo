"""
Phase 2d - Parse the Untappd venue page into a structured tap list.

Untappd renders "The List" as repeated blocks:

    (4.12)
    Bring Back Brewers Gold IPA - New England / Hazy
    6.5% ABV - 40 IBU - Russian River Brewing Company

Markup is stable enough to parse from the browser-rendered innerText, which is
more reliable than chasing class names.

IMPORTANT CAVEAT: Untappd lists beers that *patrons have logged*, not the venue's
official tap list. It is excellent evidence of style/brewery positioning, but it
is not a substitute for the bar's own pour list.

Outputs: research/brand/beer_list_parsed.json + beer_list.md
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import brandlib as bl

ENTRY = re.compile(
    r"^(?P<name>.+?)\s+-\s+(?P<style>[^-]+?)\s*$"
)
DETAIL = re.compile(
    r"(?P<abv>[\d.]+)%\s*ABV\s*[•\-]\s*(?:(?P<ibu>[\d.]+|N/A)\s*IBU)?\s*[•\-]?\s*(?P<brewery>.+?)\s*$",
    re.I,
)
RATING = re.compile(r"^\(([\d.]+)\)$")


def main() -> None:
    d = json.loads((bl.BRAND / "beer_list.json").read_text(encoding="utf-8"))
    text = d.get("page_text", "")
    if not text:
        html = (bl.RAW / "untappd.html").read_text(encoding="utf-8", errors="ignore")
        text = re.sub(r"<[^>]+>", "\n", html)

    lines = [l.strip() for l in text.splitlines()]
    lines = [l for l in lines if l and l != "•"]

    beers: list[dict] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = ENTRY.match(line)
        if m and i + 1 < len(lines):
            det = DETAIL.match(lines[i + 1])
            if det:
                rating = None
                if i >= 2:
                    r = RATING.match(lines[i - 1])
                    if r:
                        rating = float(r.group(1))
                beers.append({
                    "beer": m.group("name").strip(),
                    "style": m.group("style").strip(),
                    "abv": float(det.group("abv")) if det.group("abv") else None,
                    "ibu": (float(det.group("ibu"))
                            if det.group("ibu") and det.group("ibu") != "N/A" else None),
                    "brewery": det.group("brewery").strip().rstrip("• ").strip(),
                    "untappd_rating": rating,
                })
                i += 2
                continue
        i += 1

    # de-dupe
    seen, clean = set(), []
    for b in beers:
        k = b["beer"].lower()
        if k not in seen:
            seen.add(k)
            clean.append(b)

    styles = Counter(b["style"] for b in clean)
    breweries = Counter(b["brewery"] for b in clean)
    abvs = sorted(b["abv"] for b in clean if b["abv"])

    out = {
        "venue_url": d.get("final_url"),
        "venue_name": "The Rustic Barrel",
        "venue_category": "BBQ Joint",
        "count": len(clean),
        "abv_range": [min(abvs), max(abvs)] if abvs else None,
        "abv_median": abvs[len(abvs) // 2] if abvs else None,
        "styles": styles.most_common(),
        "breweries": breweries.most_common(),
        "beers": clean,
        "caveat": ("Untappd lists patron-logged beers, not the venue's official "
                   "tap list."),
    }
    bl.dump_json(bl.BRAND / "beer_list_parsed.json", out)

    L = ["# Untappd tap evidence - The Rustic Barrel\n",
         f"Venue: <{d.get('final_url')}>  ·  Category: BBQ Joint  ·  "
         f"{len(clean)} beers listed\n",
         "> Untappd lists beers patrons have *logged*, not the bar's official "
         "pour list. Treat as style/brewery positioning evidence.\n",
         "| Beer | Style | ABV | IBU | Brewery |",
         "|---|---|---:|---:|---|"]
    for b in clean:
        ibu = b["ibu"] if b["ibu"] is not None else "—"
        L.append(f"| {b['beer']} | {b['style']} | {b['abv']}% | {ibu} | {b['brewery']} |")

    if abvs:
        L.append(f"\n**ABV range:** {min(abvs)}% – {max(abvs)}%  ·  "
                 f"**median:** {abvs[len(abvs)//2]}%\n")
    L.append("\n**Style mix:**\n")
    for s, n in styles.most_common():
        L.append(f"- {s} — {n}")
    L.append("\n**Breweries:**\n")
    for b_, n in breweries.most_common():
        L.append(f"- {b_} — {n}")

    (bl.BRAND / "beer_list.md").write_text("\n".join(L), encoding="utf-8")

    bl.log(f"beers parsed : {len(clean)}")
    bl.log(f"abv range    : {out['abv_range']}  median {out['abv_median']}%")
    bl.log(f"styles       : {len(styles)} distinct")
    bl.log("top styles   : " + ", ".join(f"{s} ({n})" for s, n in styles.most_common(8)))
    bl.log("breweries    : " + ", ".join(f"{b} ({n})" for b, n in breweries.most_common(6)))
    bl.log("")
    for b in clean[:12]:
        bl.log(f"  {b['beer'][:42]:<42} {b['style'][:22]:<22} {b['abv']}%  {b['brewery'][:26]}")


if __name__ == "__main__":
    main()
