"""
Phase 1 - Media + brand-signal capture.

For every reachable touchpoint this script:
  1. Loads the page in Scrapling's StealthyFetcher (Chromium + anti-detection)
  2. Records EVERY image / video / font response off the wire (page_setup hook)
  3. Runs source-specific interactions (click into galleries, open menus, scroll)
  4. Harvests the DOM: images, srcsets, videos, icons, meta tags, JSON-LD,
     computed fonts, computed colours
  5. Writes raw HTML + a JSON manifest
  6. Downloads every unique asset to disk, bucketed photo / video / logo / font

Outputs:
  research/raw/<source>.html
  research/raw/<source>.json
  research/media/{photos,videos,logos,fonts}/
  research/brand/asset_manifest.json
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from scrapling.fetchers import StealthyFetcher  # noqa: E402

import brandlib as bl  # noqa: E402

# --------------------------------------------------------------------------- #
# Source configuration
# --------------------------------------------------------------------------- #
# `interact` runs inside the page after load, before harvesting. It is where we
# coax galleries open and lazy-loaded content into the DOM.
SOURCES: dict[str, dict] = {
    "yelp": {
        "url": "https://www.yelp.com/biz/the-rustic-barrel-king-city-2",
        "scroll": 40,
        "interact": None,
    },
    "doordash": {
        "url": "https://www.doordash.com/store/the-rustic-barrel-king-city-34689489/90022148/?pickup=true&src=yp",
        "scroll": 25,
        "interact": None,
    },
    "ubereats": {
        "url": "https://www.ubereats.com/store/the-rustic-barrel/j50H6Tr2W-qha1Ep9ys4Ag",
        "scroll": 25,
        "interact": None,
    },
    "facebook": {
        "url": "https://www.facebook.com/therusticbarreltaphouse",
        "scroll": 60,
        "interact": None,
    },
    "instagram": {
        "url": "https://www.instagram.com/the_rustic_barrel_/",
        "scroll": 50,
        "interact": None,
    },
}


# --------------------------------------------------------------------------- #
# Hooks
# --------------------------------------------------------------------------- #
def title_of(page, html: str) -> str:
    """Scrapling's Response is itself a Selector - it exposes .css(), not .css_first()."""
    try:
        nodes = page.css("title::text")
        if nodes:
            return str(nodes[0]).strip()[:200]
    except Exception:  # noqa: BLE001
        pass
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    return m.group(1).strip()[:200] if m else ""


def make_setup(store: list):
    """Runs BEFORE navigation - registers the wire listener so we catch the
    very first image/font/media requests too."""

    def setup(page):
        def on_response(resp):
            try:
                rtype = resp.request.resource_type
                if rtype in ("image", "media", "font"):
                    ct = ""
                    try:
                        ct = (resp.headers or {}).get("content-type", "")
                    except Exception:  # noqa: BLE001
                        ct = ""
                    store.append({"url": resp.url, "rtype": rtype, "ct": ct})
            except Exception:  # noqa: BLE001
                pass

        page.on("response", on_response)

    return setup


def make_action(scroll_steps: int, interact: str | None, harvested: dict):
    """Runs AFTER load, while the Playwright page is still alive.

    Scrapling's Response is not a live browser handle (it has no .evaluate), so
    every DOM read has to happen in here and be handed back through `harvested`.
    """

    def action(page):
        if interact:
            try:
                page.evaluate(interact)
            except Exception as e:  # noqa: BLE001
                bl.log(f"    [interact failed] {type(e).__name__}: {str(e)[:120]}")
        try:
            page.evaluate(bl.JS_AUTOSCROLL, scroll_steps)
        except Exception as e:  # noqa: BLE001
            bl.log(f"    [scroll failed] {type(e).__name__}")
        try:
            page.wait_for_timeout(1500)
        except Exception:  # noqa: BLE001
            pass
        for key, js in (("dom", bl.JS_HARVEST), ("computed", bl.JS_COMPUTED_STYLE)):
            try:
                harvested[key] = page.evaluate(js) or {}
            except Exception as e:  # noqa: BLE001
                bl.log(f"    [{key} harvest failed] {type(e).__name__}: {str(e)[:160]}")
                harvested[key] = {}

    return action


# --------------------------------------------------------------------------- #
# Asset URL collection
# --------------------------------------------------------------------------- #
def collect_urls(html: str, dom: dict, network: list, base_url: str) -> list[dict]:
    """Merge every asset reference we can find into one deduplicated list."""
    from urllib.parse import urljoin

    found: dict[str, dict] = {}

    def add(url: str, ct: str = "", rtype: str = "", hint: str = ""):
        if not url:
            return
        url = url.strip().strip('"\'')
        if not url or url.startswith("data:"):
            return
        url = urljoin(base_url, url)
        if bl.is_junk(url):
            return
        if url not in found:
            found[url] = {"url": url, "ct": ct, "rtype": rtype, "hint": hint}

    # 1. Anything that came over the wire during load
    for n in network:
        add(n["url"], n.get("ct", ""), n.get("rtype", ""))

    # 2. DOM images / srcsets
    for img in dom.get("imgs", []):
        add(img.get("src", ""), "image/auto", "image")
    for ss in dom.get("srcsets", []):
        for part in ss.split(","):
            cand = part.strip().split(" ")[0]
            add(cand, "image/auto", "image")

    # 3. Videos
    for v in dom.get("videos", []):
        add(v.get("src", ""), "video/auto", "media")
        add(v.get("poster", ""), "image/auto", "image")

    # 4. Icon / manifest links
    for l in dom.get("links", []):
        if any(k in l["rel"] for k in ("icon", "apple-touch", "manifest", "mask-icon")):
            add(l["href"], "", "", hint="icon")

    # 5. og:image / twitter:image
    for m in dom.get("metas", []):
        if m["name"] in ("og:image", "og:image:url", "twitter:image",
                         "twitter:image:src", "og:logo"):
            add(m["content"], "image/auto", "image", hint="logo")

    # 6. CSS backgrounds
    for b in dom.get("backgrounds", []):
        add(b, "image/auto", "image")

    # 7. Last resort: regex sweep of the raw HTML for absolute media URLs
    for m in re.finditer(
        r'https?://[^\s"\'<>\\)]+?\.(?:jpe?g|png|webp|avif|gif|mp4|mov|webm|svg)(?:\?[^\s"\'<>\\)]*)?',
        html, re.I,
    ):
        add(m.group(0), "", "image")

    # 8. Stylesheet URLs - we download these separately for @font-face + colour mining
    return list(found.values())


def mine_stylesheets(base_url: str, stylesheet_urls: list[str]) -> dict:
    """Fetch linked CSS and mine @font-face declarations + raw colour tokens."""
    from scrapling.fetchers import Fetcher

    fonts: list[dict] = []
    color_tokens: dict[str, int] = {}
    font_families: set[str] = set()
    sheets_saved: list[str] = []

    for href in stylesheet_urls[:40]:
        if bl.is_junk(href) or not href.endswith(".css"):
            continue
        try:
            r = Fetcher.get(href, impersonate="chrome", stealthy_headers=True,
                            timeout=25, headers={"Referer": base_url})
            if r.status != 200:
                continue
            css = r.body.decode("utf-8", "ignore")
            name = bl.safe_name(href, ".css")
            (bl.BRAND / name).write_text(css, encoding="utf-8")
            sheets_saved.append(name)

            for m in re.finditer(
                r"@font-face\s*\{[^}]*\}", css, re.I | re.S
            ):
                block = m.group(0)
                fam = re.search(r"font-family\s*:\s*([^;]+)", block, re.I)
                src = re.search(r"url\(([^)]+)\)", block)
                wgt = re.search(r"font-weight\s*:\s*([^;]+)", block, re.I)
                sty = re.search(r"font-style\s*:\s*([^;]+)", block, re.I)
                if fam:
                    font_families.add(fam.group(1).strip().strip("\"'"))
                fonts.append({
                    "family": (fam.group(1).strip().strip("\"'") if fam else ""),
                    "weight": (wgt.group(1).strip() if wgt else ""),
                    "style": (sty.group(1).strip() if sty else ""),
                    "src": (src.group(1).strip().strip("\"'") if src else ""),
                    "stylesheet": name,
                })

            for tok in re.findall(r"#[0-9a-fA-F]{3,8}\b", css):
                color_tokens[tok.lower()] = color_tokens.get(tok.lower(), 0) + 1
            for tok in re.findall(r"rgba?\([^)]+\)", css, re.I):
                color_tokens[tok.lower()] = color_tokens.get(tok.lower(), 0) + 1
        except Exception:  # noqa: BLE001
            continue

    return {
        "font_faces": fonts,
        "font_families": sorted(font_families),
        "color_tokens": dict(sorted(color_tokens.items(), key=lambda x: -x[1])[:60]),
        "stylesheets_saved": sheets_saved,
    }


# --------------------------------------------------------------------------- #
# Main capture
# --------------------------------------------------------------------------- #
def fallback_dom_from_html(html: str, base_url: str) -> dict:
    """If the in-page harvest came back empty (SPA, or JS errored), recover the
    basics straight out of the saved HTML so we still get assets."""
    from urllib.parse import urljoin

    dom = {"imgs": [], "metas": [], "links": [], "jsonld": [], "videos": [],
           "srcsets": [], "backgrounds": [], "fonts": [], "svgs": []}

    for m in re.finditer(r"<img[^>]+>", html, re.I):
        tag = m.group(0)
        src = re.search(r'(?:src|data-src)="([^"]+)"', tag, re.I)
        if src:
            dom["imgs"].append({"src": urljoin(base_url, src.group(1)), "alt": "",
                                "width": 0, "height": 0, "cls": ""})

    for m in re.finditer(r"<meta[^>]+>", html, re.I):
        tag = m.group(0)
        n = re.search(r'(?:name|property)="([^"]+)"', tag, re.I)
        c = re.search(r'content="([^"]*)"', tag, re.I)
        if n and c:
            dom["metas"].append({"name": n.group(1).lower(), "content": c.group(1)})

    for m in re.finditer(r"<link[^>]+>", html, re.I):
        tag = m.group(0)
        rel = re.search(r'rel="([^"]+)"', tag, re.I)
        href = re.search(r'href="([^"]+)"', tag, re.I)
        if rel and href:
            dom["links"].append({"rel": rel.group(1).lower(),
                                 "href": urljoin(base_url, href.group(1))})

    for m in re.finditer(
        r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S | re.I
    ):
        dom["jsonld"].append(m.group(1)[:40000])

    return dom


def capture_source(key: str, cfg: dict) -> dict:
    url = cfg["url"]
    bl.log(f"\n=== {key} ===")
    network: list[dict] = []
    harvested: dict = {}
    record: dict = {"key": key, "url": url}

    try:
        page = StealthyFetcher.fetch(
            url,
            headless=True,
            network_idle=True,
            timeout=120_000,
            solve_cloudflare=True,
            block_ads=False,
            disable_resources=False,  # media capture needs images/video to load
            page_setup=make_setup(network),
            page_action=make_action(cfg.get("scroll", 30), cfg.get("interact"), harvested),
        )
    except Exception as e:  # noqa: BLE001
        record["error"] = f"{type(e).__name__}: {str(e)[:300]}"
        bl.log(f"  FAILED: {record['error']}")
        return record

    html = page.html_content
    final_url = str(getattr(page, "url", url))
    record["status"] = getattr(page, "status", None)
    record["final_url"] = final_url
    record["title"] = title_of(page, html)

    (bl.RAW / f"{key}.html").write_text(html, encoding="utf-8")

    # Harvest results come back through the page_action closure.
    dom = harvested.get("dom") or {}
    styles = harvested.get("computed") or {}
    if not dom.get("imgs"):
        bl.log("  [live DOM empty - falling back to raw HTML parse]")
        dom = fallback_dom_from_html(html, final_url)
    record["dom"] = dom
    record["computed"] = styles

    bl.log(f"  html={len(html):,}B  dom_imgs={len(dom.get('imgs', []))}  "
           f"wire={len(network)}  jsonld={len(dom.get('jsonld', []))}")

    # Fonts declared in stylesheets.
    css_urls = [
        l["href"] for l in dom.get("links", [])
        if "stylesheet" in l["rel"]
    ]
    record["css"] = mine_stylesheets(final_url, css_urls)
    bl.log(f"  stylesheets={len(record['css']['stylesheets_saved'])}  "
           f"@font-face={len(record['css']['font_faces'])}")

    # Build the asset list and download.
    candidates = collect_urls(html, dom, network, final_url)
    bl.log(f"  candidate assets: {len(candidates)}")

    assets = []
    seen_files: set[str] = set()
    for i, c in enumerate(candidates, 1):
        bucket = bl.kind_of(c["url"], c.get("ct", ""), c.get("hint", ""))
        if bucket == "other" and c.get("rtype") == "font":
            bucket = "font"
        if bucket == "other":
            continue
        got = bl.save_asset(c["url"], bucket, referer=final_url)
        if got and got["file"] not in seen_files:
            seen_files.add(got["file"])
            assets.append(got)
        if i % 40 == 0:
            bl.log(f"    ...{i}/{len(candidates)} downloaded={len(assets)}")

    record["assets"] = assets
    bl.log(f"  SAVED {len(assets)} assets "
           f"(photos={sum(1 for a in assets if a['kind']=='photo')}, "
           f"videos={sum(1 for a in assets if a['kind']=='video')}, "
           f"logos={sum(1 for a in assets if a['kind']=='logo')}, "
           f"fonts={sum(1 for a in assets if a['kind']=='font')})")
    return record


def main() -> None:
    only = sys.argv[1:] or list(SOURCES)
    all_records = []
    for key in only:
        cfg = SOURCES.get(key)
        if not cfg:
            bl.log(f"skip unknown source {key}")
            continue
        rec = capture_source(key, cfg)
        all_records.append(rec)
        bl.dump_json(bl.RAW / f"{key}.json", rec)
        time.sleep(4)  # polite pacing between browser sessions

    manifest_path = bl.BRAND / "asset_manifest.json"
    existing = []
    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
    by_source = {r["key"]: r for r in existing if r.get("key") in {x["key"] for x in all_records}}
    for r in all_records:
        by_source[r["key"]] = r
    bl.dump_json(manifest_path, list(by_source.values()))
    bl.log(f"\nmanifest -> {manifest_path}")


if __name__ == "__main__":
    main()
