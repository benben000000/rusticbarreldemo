"""
Phase 4 - Dribbble reference scrape.

Purpose: we are NOT inventing a look. We are qualifying existing, proven
design directions that already fit The Rustic Barrel's vibe, so the brand work
starts from work designers have validated rather than from scratch.

The vibe we're matching, established from the crawl:
  * Western / Americana rustic - barrel, hops, wheat, wood type
  * Craft-beer bar identity, dark and warm, high-contrast cream typography
  * Modern execution, not country-kitchen kitsch
  * Sports-bar energy: TV wall, multi-tap, events, comedy nights

Dribbble is a React app, so search pages are harvested in stealth Chromium.
Individual shot pages are then fetched over plain HTTP (far faster) for the
metadata + cover art.

Outputs: research/reference/dribbble_shots.json + reference/dribbble/*.jpg
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

sys.path.insert(0, str(Path(__file__).resolve().parent))

from scrapling.fetchers import Fetcher, StealthyFetcher

import brandlib as bl

DEST = bl.RESEARCH / "reference"
SHOTS = DEST / "dribbble"

QUERIES = [
    "western bar branding",
    "rustic bar identity",
    "craft beer branding",
    "bbq restaurant branding",
    "saloon branding",
    "tavern brand identity",
    "western typography poster",
    "bar menu design",
    "sports bar branding",
    "whiskey bar branding",
    "rustic logo design",
    "beer label design",
]

MAX_PER_QUERY = 24


def collect_shots(query: str) -> list[dict]:
    """Dribbble's search page is client-rendered; scroll to pull in more shots.

    The page embeds a schema.org ItemList of CreativeWork (name / url / image /
    creator), which is far cleaner than scraping the React markup - and a
    permalink regex fallback for shots that arrive after the JSON is built.
    """
    url = f"https://dribbble.com/search/{query.replace(' ', '-')}"
    shots: list[dict] = []
    seen: set[str] = set()

    def action(page):
        try:
            page.wait_for_timeout(3500)
        except Exception:  # noqa: BLE001
            pass
        for _ in range(8):
            try:
                page.evaluate("() => window.scrollBy(0, 1800)")
                page.wait_for_timeout(1300)
            except Exception:  # noqa: BLE001
                break

    try:
        page = StealthyFetcher.fetch(
            url, headless=True, network_idle=True, timeout=90_000,
            page_action=action,
        )
        html = page.html_content
    except Exception as e:  # noqa: BLE001
        bl.log(f"  [{query}] search failed: {type(e).__name__}")
        return []

    # 1. JSON-LD ItemList - name + image + creator, all in one pass
    for m in re.finditer(
        r'<script type="application/ld\+json">(.*?)</script>', html, re.S
    ):
        try:
            blob = json.loads(m.group(1))
        except Exception:  # noqa: BLE001
            continue
        stack = [blob]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                if node.get("@type") == "CreativeWork" and node.get("url"):
                    u = node["url"].split("?")[0]
                    if u not in seen:
                        seen.add(u)
                        shots.append({
                            "url": u,
                            "title": node.get("name", ""),
                            "image": node.get("image", ""),
                            "designer": (node.get("creator") or {}).get("name", "")
                            if isinstance(node.get("creator"), dict) else "",
                            "query": query,
                        })
                stack.extend(v for v in node.values() if isinstance(v, (dict, list)))
            elif isinstance(node, list):
                stack.extend(v for v in node if isinstance(v, (dict, list)))

    # 2. Fallback for shots only present in the DOM: /shots/<id>-<Slug>
    dom_urls = set(re.findall(
        r'href="(https://dribbble\.com/shots/\d{6,}-[A-Za-z0-9._-]+)"', html))
    for u in dom_urls:
        if u not in seen:
            seen.add(u)
            shots.append({"url": u, "title": "", "image": "", "designer": "",
                          "query": query})

    # 3. Last resort: orphan CDN images on the page
    if len(shots) < 4:
        for u in re.findall(r'https://cdn\.dribbble\.com/userupload/[^"\'\\ ]+?'
                            r'\.(?:png|jpe?g|webp)', html):
            k = f"cdn::{u}"
            if k not in seen:
                seen.add(k)
                shots.append({"url": "", "title": "", "image": u, "designer": "",
                              "query": query, "cdn_only": True})

    bl.log(f"  [{query}] -> {len(shots)} shots")
    return shots[:MAX_PER_QUERY]


SHOT_META = {
    "title": (r'<meta\s+property="og:title"\s+content="([^"]+)"', r'"title":"([^"]{3,90})"'),
    "description": (r'<meta\s+name="description"\s+content="([^"]+)"',
                    r'"description":"([^"]{5,400})"'),
    "image": (r'<meta\s+property="og:image"\s+content="([^"]+)"',
              r'"(?:ogImage|coverImage)":"([^"]+)"'),
    "tags": (r'<meta\s+name="keywords"\s+content="([^"]+)"', r'"tags":\[([^\]]*)\]'),
    "designer": (r'"user":\{"[^}]*"name":"([^"]+)"', r'"username":"([^"]+)"'),
}


def fetch_shot(url: str) -> dict | None:
    try:
        r = Fetcher.get(url, impersonate="chrome", stealthy_headers=True,
                        timeout=30, follow_redirects=True)
        if r.status != 200:
            return None
        html = r.body.decode("utf-8", "ignore")
    except Exception:  # noqa: BLE001
        return None

    out: dict = {"url": url}

    def grab(key: str) -> str:
        for pat in SHOT_META[key]:
            m = re.search(pat, html)
            if m:
                return m.group(1)
        return ""

    out["title"] = grab("title")
    out["description"] = grab("description")
    out["designer"] = grab("designer")
    out["image"] = grab("image").replace("\\u002F", "/").replace("\\/", "/")

    tags = grab("tags")
    out["tags"] = [t.strip().strip('" ') for t in tags.split(",") if t.strip()][:12]
    if not out["tags"] and tags.startswith("["):
        out["tags"] = [t.strip('" ') for t in tags.strip("[]").split(",") if t.strip()][:12]

    out["likes"] = int(m.group(1)) if (m := re.search(r'"likes":\s*(\d+)', html)) else None
    out["views"] = int(m.group(1)) if (m := re.search(r'"views":\s*(\d+)', html)) else None

    # strip the "_-<user>-<slug>-<id>-<hash>.png" tail Dribbble puts on the CDN
    if out["image"]:
        out["image"] = re.sub(r"\?.*$", "", out["image"])
        out["image"] = re.sub(r"-[0-9a-f]{32}\.(png|jpg|jpeg)$",
                              r"-original.\1", out["image"])
    if out["title"].startswith("Dribbble - "):
        out["title"] = out["title"][11:].split(" by ")[0]
    return out


def main() -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    all_shots: dict[str, dict] = {}

    for q in QUERIES:
        bl.log(f"[search] {q}")
        for s in collect_shots(q):
            key = s.get("url") or f"cdn::{s.get('image','')}"
            if key not in all_shots:
                all_shots[key] = s
            elif s.get("title") and not all_shots[key].get("title"):
                all_shots[key].update(s)

    bl.log("")
    bl.log(f"unique shots discovered: {len(all_shots)}")

    saved = 0
    items = list(all_shots.values())
    results: list[dict] = []
    for i, base in enumerate(items, 1):
        meta = dict(base)
        # Fill gaps from the shot's own page when we have a permalink
        if meta.get("url") and not (meta.get("tags") or meta.get("likes") is not None):
            extra = fetch_shot(meta["url"])
            if extra:
                for k, v in extra.items():
                    if v and not meta.get(k):
                        meta[k] = v

        img = meta.get("image") or ""
        if img:
            got = bl.save_asset(img, "photo", referer="https://dribbble.com")
            if got:
                ext = got["ext"] if got["ext"] != ".bin" else ".jpg"
                slug = re.sub(r"[^a-z0-9]+", "-",
                              (meta.get("title") or "shot").lower())[:44]
                dest = SHOTS / f"{i:03d}_{slug}{ext}"
                srcf = bl.MEDIA / "photos" / Path(got["file"]).name
                if srcf.exists():
                    srcf.replace(dest)
                    meta["file"] = str(dest.relative_to(bl.RESEARCH)).replace("\\", "/")
                    meta["bytes"] = got["bytes"]
                    saved += 1
        results.append(meta)
        if i % 25 == 0:
            bl.log(f"   ...{i}/{len(items)} saved={saved}")
        time.sleep(0.3)

    shots = [m for m in results if m.get("image") or m.get("title")]
    bl.dump_json(DEST / "dribbble_shots.json", shots)

    bl.log("")
    bl.log(f"shots captured  : {len(shots)}")
    bl.log(f"cover images    : {saved}")
    bl.log(f"-> {DEST}")


if __name__ == "__main__":
    main()
