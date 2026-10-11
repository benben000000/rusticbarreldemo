"""
Phase 1b - Instagram deep crawl.

Instagram's grid is lazy-loaded and each post's full-resolution media only exists
inside the lightbox. So we can't just grab the profile page - we have to open the
grid and step through every post, harvesting the real assets at each stop.

Strategy:
  1. Load the profile, scroll to materialise the grid
  2. Click the first tile to open the lightbox
  3. Step with ArrowRight / clicking "next", capturing at every stop
  4. Also pull the reels + tagged tab if present

Outputs: research/raw/instagram_posts.json and downloaded media.
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

PROFILE = "https://www.instagram.com/the_rustic_barrel_/"
MAX_POSTS = 60

JS_COLLECT = r"""
() => {
  const abs = (u) => { try { return new URL(u, location.href).href; } catch { return u; } };
  const imgs = [];
  document.querySelectorAll('img').forEach(el => {
    const src = el.currentSrc || el.src || '';
    if (src && !src.startsWith('data:')) {
      imgs.push({ src: abs(src), w: el.naturalWidth, h: el.naturalHeight, alt: (el.alt||'').slice(0,200) });
    }
  });
  const vids = [];
  document.querySelectorAll('video').forEach(el => {
    vids.push({ src: abs(el.currentSrc || el.src || ''), poster: abs(el.poster || '') });
  });
  const caption = '';
  const cap = document.querySelector('h1');
  return { imgs, vids, caption: cap ? (cap.innerText || '').slice(0, 3000) : caption,
           url: location.href, title: document.title };
}
"""


def wire_for(store: list):
    """Returns the page_setup callback Scrapling expects."""
    def setup(page):
        def on_response(resp):
            try:
                rtype = resp.request.resource_type
                if rtype in ("image", "media"):
                    ct = ""
                    try:
                        ct = (resp.headers or {}).get("content-type", "")
                    except Exception:  # noqa: BLE001
                        pass
                    store.append({"url": resp.url, "rtype": rtype, "ct": ct})
            except Exception:  # noqa: BLE001
                pass

        page.on("response", on_response)

    return setup


def make_post_action():
    """Scroll a single post then read its DOM - Response has no .evaluate,
    so everything has to happen inside page_action."""

    def action(page):
        try:
            page.evaluate(bl.JS_AUTOSCROLL, 8)
        except Exception:  # noqa: BLE001
            pass
        try:
            page.wait_for_timeout(1200)
        except Exception:  # noqa: BLE001
            pass

    return action


def main() -> None:
    posts: list[dict] = []
    seen_assets: set[str] = set()
    saved: list[dict] = []

    profile_store: list[dict] = []
    harvested: dict = {}
    page = StealthyFetcher.fetch(
        PROFILE,
        headless=True,
        network_idle=True,
        timeout=120_000,
        page_setup=wire_for(profile_store),
        page_action=lambda p: p.evaluate(bl.JS_AUTOSCROLL, 45),
    )
    titles = page.css("title::text")
    bl.log(f"profile loaded: {str(titles[0])[:80] if titles else '?'}")

    # --- count the grid tiles -------------------------------------------- #
    tiles = page.css("a[href*='/p/'], a[href*='/reel/'], a[href*='/reels/']")
    bl.log(f"grid tiles found: {len(tiles)}")
    tile_hrefs = []
    seen_href = set()
    for t in tiles:
        h = t.attrib.get("href", "")
        if h and h not in seen_href:
            seen_href.add(h)
            tile_hrefs.append(h)
    bl.dump_json(bl.RAW / "instagram_tiles.json", tile_hrefs[:200])

    # Visit each post directly - far more reliable than lightbox clicking.
    from urllib.parse import urljoin

    for i, href in enumerate(tile_hrefs[:MAX_POSTS], 1):
        post_url = urljoin(PROFILE, href)
        store: list[dict] = []
        got_dom: dict = {}

        def post_action(pg, _d=got_dom):
            make_post_action()(pg)
            try:
                _d.update(pg.evaluate(JS_COLLECT) or {})
            except Exception as e:  # noqa: BLE001
                bl.log(f"     [collect failed] {type(e).__name__}: {str(e)[:100]}")

        bl.log(f"  [{i}/{min(len(tile_hrefs), MAX_POSTS)}] {href}")
        try:
            sub = StealthyFetcher.fetch(
                post_url,
                headless=True,
                network_idle=True,
                timeout=60_000,
                page_setup=wire_for(store),
                page_action=post_action,
            )
        except Exception as e:  # noqa: BLE001
            bl.log(f"     failed: {type(e).__name__}")
            continue

        data = got_dom or {}
        entry = {
            "index": i,
            "url": str(getattr(sub, "url", post_url)),
            "title": data.get("title"),
            "caption": data.get("caption", ""),
            "imgs": data.get("imgs", []),
            "vids": data.get("vids", []),
            "wire": store,
        }

        # Persist the post HTML - captions and engagement live here.
        (bl.RAW / f"ig_post_{i:03d}.html").write_text(sub.html_content, encoding="utf-8")

        # Download the biggest image on the page (that is the full-res media).
        cands = []
        for im in data.get("imgs", []):
            if im["w"] >= 400 and "profile_pic" not in im["src"]:
                cands.append(im)
        cands.sort(key=lambda x: -(x["w"] * x["h"]))
        picked = []
        for im in cands[:3]:
            if im["src"] in seen_assets:
                continue
            seen_assets.add(im["src"])
            got = bl.save_asset(im["src"], "photo", referer=post_url)
            if got:
                saved.append(got)
                picked.append(got["file"])
        for v in data.get("vids", []):
            for src in (v.get("src"), v.get("poster")):
                if src and src not in seen_assets:
                    seen_assets.add(src)
                    got = bl.save_asset(src, "photo", referer=post_url)
                    if got:
                        saved.append(got)
                        picked.append(got["file"])
        entry["saved"] = picked
        posts.append(entry)
        bl.log(f"     imgs={len(data.get('imgs', []))} saved={len(picked)} "
               f"wire={len(store)}")
        time.sleep(2.5)

    bl.dump_json(bl.RAW / "instagram_posts.json", posts)
    bl.dump_json(bl.BRAND / "instagram_assets.json", saved)
    bl.log(f"\nposts captured: {len(posts)}  files saved: {len(saved)}")

    # Merge into the global asset manifest so analyze.py picks them up.
    mpath = bl.BRAND / "asset_manifest.json"
    manifest = json.loads(mpath.read_text(encoding="utf-8")) if mpath.exists() else []
    manifest = [r for r in manifest if r.get("key") != "instagram"]
    manifest.append({
        "key": "instagram",
        "url": PROFILE,
        "final_url": PROFILE,
        "title": "Instagram posts (deep crawl)",
        "dom": {"imgs": [], "metas": [], "jsonld": [], "links": []},
        "computed": {"fonts": [], "colors": [], "headings": []},
        "css": {"font_faces": [], "font_families": [], "color_tokens": {},
                "stylesheets_saved": []},
        "assets": saved,
    })
    bl.dump_json(mpath, manifest)
    bl.log("manifest updated")


if __name__ == "__main__":
    main()
