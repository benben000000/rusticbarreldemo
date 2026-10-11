"""
Phase 5 - Official delivery-platform logos.

The order CTA currently uses "DD" / "UE" text placeholders. Both DoorDash and
Uber Eats run merchant co-marketing programs and supply official artwork to
partners for exactly this purpose, so this pulls the real marks rather than
drawing an approximation - an approximation would be both wrong-looking and a
trademark problem.

Sources tried, in order:
  1. the platform's own brand/press asset pages
  2. logo references inside the storefront HTML we already captured
  3. their public CDN hosts observed on the storefront pages

Output: site/assets/img/partner-{doordash,ubereats}.svg|.png + provenance JSON
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

sys.path.insert(0, str(Path(__file__).resolve().parent))

from scrapling.fetchers import Fetcher

import brandlib as bl

OUT = bl.RESEARCH.parent / "site" / "assets" / "img"

TARGETS = {
    "doordash": {
        "brand_pages": [
            "https://www.doordash.com/brand",
            "https://about.doordash.com/en-us/brand",
            "https://partners.doordash.com/en-US/brand",
        ],
        # observed while crawling the storefront
        "html": [bl.RAW / "doordash.html", bl.RAW / "doordash_menu.html"],
        "host_hints": ("doordash-static.s3.amazonaws.com", "img.cdn4dd.com"),
        "name_hints": ("doordash-logo", "dd-logo", "logo-doordash",
                       "doordash_wordmark", "dd_wordmark", "wordmark"),
    },
    "ubereats": {
        "brand_pages": [
            "https://www.ubereats.com/brand",
            "https://www.uber.com/brand",
            "https://brand.uber.com/",
        ],
        "html": [bl.RAW / "ubereats.html"],
        "host_hints": ("d4p17acsd5wyj.cloudfront.net", "tb-static.uber.com"),
        "name_hints": ("ubereats-logo", "ue-logo", "logo-ubereats",
                       "ubereats_wordmark", "ue_wordmark", "wordmark"),
    },
}

# A wordmark is what a merchant order button needs - not the app icon.
BAD_NAME = re.compile(r"(icon|avatar|favicon|apple-touch|badge|1x1|pixel|spacer)", re.I)


def from_html(paths: list[Path], hints: tuple[str, ...]) -> list[dict]:
    found: list[dict] = []
    seen: set[str] = set()
    for p in paths:
        if not p.exists():
            continue
        html = p.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r'https://[^"\'\\\s)]+?\.(?:svg|png)', html):
            u = m.group(0)
            if u in seen:
                continue
            seen.add(u)
            low = u.lower()
            if BAD_NAME.search(low):
                continue
            if any(h in low for h in hints):
                found.append({"url": u, "source": p.name, "via": "html-sweep"})
        # <img> tags carrying an accessible name are a stronger signal
        for m in re.finditer(r'<img[^>]+>', html):
            tag = m.group(0)
            src = re.search(r'(?:src|data-src)="([^"]+)"', tag)
            alt = re.search(r'alt="([^"]*)"', tag)
            if not src:
                continue
            low = (alt.group(1) if alt else "").lower()
            if "doordash" in low or "uber eats" in low or "ubereats" in low:
                if not BAD_NAME.search(src.group(1)):
                    found.append({"url": src.group(1), "source": p.name,
                                  "via": f"img-alt:{alt.group(1)[:40]}"})
    return found


def from_brand_pages(cfg: dict) -> list[dict]:
    found: list[dict] = []
    for page in cfg["brand_pages"]:
        try:
            r = Fetcher.get(page, impersonate="chrome", stealthy_headers=True,
                            timeout=30, follow_redirects=True)
        except Exception as e:  # noqa: BLE001
            print(f"    {page} -> {type(e).__name__}")
            continue
        if r.status != 200:
            print(f"    {page} -> HTTP {r.status}")
            continue
        html = r.body.decode("utf-8", "ignore")
        hits = 0
        for m in re.finditer(r'https://[^"\'\\\s)]+?\.(?:svg|png)', html):
            u = m.group(0)
            low = u.lower()
            if BAD_NAME.search(low):
                continue
            if any(h in low for h in cfg["name_hints"]) or "logo" in low:
                if any(h in low for h in cfg["host_hints"]) or "logo" in low:
                    found.append({"url": u, "source": page, "via": "brand-page"})
                    hits += 1
        print(f"    {page} -> HTTP 200, {hits} candidates")
    return found


def score(u: str) -> int:
    """Prefer a wide wordmark SVG over an icon or a raster."""
    s = 0
    low = u.lower()
    if low.endswith(".svg"):
        s += 6
    if BAD_NAME.search(low):
        s -= 8
    if any(k in low for k in ("wordmark", "logo-full", "logo_horizontal",
                              "full-color", "fullcolor", "horizontal")):
        s += 5
    if "white" in low or "inverse" in low:
        s += 3          # we render on a dark card
    if "black" in low or "dark" in low:
        s -= 2
    if re.search(r"\d{3,4}x\d{2,3}", low):   # raster size in the filename
        s -= 2
    return s


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    provenance: dict = {}

    for key, cfg in TARGETS.items():
        print(f"\n=== {key} ===")
        cands: list[dict] = []

        print("  brand pages:")
        cands += from_brand_pages(cfg)
        print("  captured storefront HTML:")
        cands += from_html(cfg["html"], cfg["name_hints"])

        # de-dupe, then rank
        uniq: dict[str, dict] = {}
        for c in cands:
            u = c["url"].split("?")[0]
            if u not in uniq or score(u) > score(uniq[u]["url"].split("?")[0]):
                uniq[u] = c

        ranked = sorted(uniq.values(),
                        key=lambda c: -score(c["url"].split("?")[0]))
        print(f"  candidates: {len(ranked)}")
        for c in ranked[:8]:
            print(f"    [{score(c['url']):>3}] {c['url'][:100]}")

        chosen = ranked[0] if ranked else None
        if chosen:
            dest_stem = f"partner-{key}"
            info = bl.download(chosen["url"])
            if info:
                ext = info["ext"] if info["ext"] != ".bin" else ".svg"
                dest = OUT / f"{dest_stem}{ext}"
                dest.write_bytes(info["body"])
                print(f"  SAVED {dest.name}  ({info['bytes']:,} bytes)")
                provenance[key] = {
                    "file": dest.name,
                    "source_url": chosen["url"],
                    "discovered_via": chosen["via"],
                    "page": chosen["source"],
                    "bytes": info["bytes"],
                    "content_type": info["content_type"],
                }
            else:
                print("  download failed")
        else:
            print("  !! no asset found")

    bl.dump_json(bl.BRAND / "partner_logos.json", provenance)
    print("\nprovenance -> research/brand/partner_logos.json")


if __name__ == "__main__":
    main()
