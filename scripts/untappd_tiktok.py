"""
Phase 1h - Untappd + TikTok.

Two brand sources the Linktree exposed that no other channel revealed:

  * Untappd (untp.beer/450efae094) - their beer list. Untappd is server-rendered
    and exposes a clean JSON API on the venue slug, which gives the actual tap
    list with ABVs and styles.
  * TikTok (@therusticbarrel831) - a second video channel. Like Instagram reels,
    the video only reaches the wire once playback starts.

Outputs: research/brand/beer_list.json, research/brand/tiktok.json + media
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

UNTAPPD = "https://untp.beer/450efae094"
TIKTOK = "https://www.tiktok.com/@therusticbarrel831"


# --------------------------------------------------------------------------- #
# Untappd
# --------------------------------------------------------------------------- #
def scrape_untappd() -> dict:
    out: dict = {"source": UNTAPPD, "venue": None, "beers": []}
    html = ""

    # Untappd returns 403 to plain HTTP impersonation - it needs the browser.
    state: dict = {}

    def action(page):
        try:
            page.wait_for_timeout(4500)
        except Exception:  # noqa: BLE001
            pass
        try:
            state["text"] = page.evaluate(
                "() => document.body ? document.body.innerText : ''")
        except Exception:  # noqa: BLE001
            pass

    try:
        page = StealthyFetcher.fetch(
            UNTAPPD, headless=True, network_idle=True, timeout=120_000,
            solve_cloudflare=True,
            page_action=action,
        )
        html = page.html_content
        (bl.RAW / "untappd.html").write_text(html, encoding="utf-8")
        out["status"] = getattr(page, "status", None)
        out["final_url"] = str(getattr(page, "url", UNTAPPD))
        out["page_text"] = (state.get("text") or "")[:9000]
        bl.log(f"untappd status: {out['status']}  bytes={len(html)}")
    except Exception as e:  # noqa: BLE001
        out["error"] = f"{type(e).__name__}: {str(e)[:200]}"
        bl.log(f"  untappd fetch failed: {out['error']}")
        return out

    # Venue identity
    for pat, key in ((r'<meta property="og:title" content="([^"]+)"', "og_title"),
                     (r'<meta property="og:description" content="([^"]+)"', "og_description"),
                     (r'<meta property="og:image" content="([^"]+)"', "og_image")):
        m = re.search(pat, html)
        if m:
            out[key] = m.group(1)

    # The tap list is embedded as JSON in the page
    m = re.search(r'window\.__NUXT__\s*=\s*(\{.*?\});?\s*</script>', html, re.S)
    if not m:
        m = re.search(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if m:
        try:
            out["_embedded"] = json.loads(m.group(1))
        except Exception:  # noqa: BLE001
            out["_embedded_raw"] = m.group(1)[:5000]

    # Flat regex sweep as a fallback - beer name / style / abv triples
    for mm in re.finditer(
        r'<div class="beer-name[^"]*"[^>]*>(.*?)</div>.*?'
        r'(?:abv|ABV)["\s:>]*([\d.]+)%?', html, re.S | re.I
    ):
        out["beers"].append({"name": re.sub(r"<[^>]+>", "", mm.group(1)).strip(),
                             "abv": mm.group(2)})
    if not out["beers"]:
        for mm in re.finditer(r'"name"\s*:\s*"([^"]{3,60})".{0,200}?"abv"\s*:\s*"?([\d.]+)', html):
            out["beers"].append({"name": mm.group(1), "abv": mm.group(2)})

    bl.log(f"  beers found: {len(out['beers'])}")
    for b in out["beers"][:15]:
        bl.log(f"    {b.get('name','')[:46]:<46} {b.get('abv','')}%")
    return out


# --------------------------------------------------------------------------- #
# TikTok
# --------------------------------------------------------------------------- #
JS_TIKTOK = r"""
async () => {
  const sleep = (ms) => new Promise(r => setTimeout(r, ms));
  for (let i = 0; i < 12; i++) {
    window.scrollBy(0, 900);
    await sleep(900);
  }
  const vids = Array.from(document.querySelectorAll('video')).map(v => ({
    src: v.currentSrc || v.src || '', poster: v.poster || '',
    w: v.videoWidth, h: v.videoHeight, dur: v.duration || 0
  }));
  const thumbs = Array.from(document.querySelectorAll('img'))
    .filter(i => i.naturalWidth > 200)
    .map(i => ({ src: i.currentSrc || i.src, w: i.naturalWidth, h: i.naturalHeight }));
  const descs = Array.from(document.querySelectorAll('[data-e2e="video-desc"], [data-e2e="browse-video-desc"]'))
    .map(e => (e.innerText || '').trim()).filter(Boolean);
  const links = Array.from(document.querySelectorAll('a[href*="/video/"]'))
    .map(a => a.getAttribute('href')).filter((v, i, s) => s.indexOf(v) === i);
  return { vids, thumbs, descs, links, title: document.title, url: location.href };
}
"""

JS_TIKTOK_PLAY = r"""
async () => {
  const sleep = (ms) => new Promise(r => setTimeout(r, ms));
  const v = document.querySelector('video');
  if (!v) return { ok: false };
  v.muted = true;
  try { await v.play(); } catch (e) {}
  v.scrollIntoView({block: 'center'});
  await sleep(4000);
  return { ok: true, src: v.currentSrc || v.src, w: v.videoWidth, h: v.videoHeight };
}
"""


def scrape_tiktok() -> dict:
    out: dict = {"source": TIKTOK, "posts": [], "videos": []}
    wire: list[dict] = []
    state: dict = {}

    def setup(page):
        def on_response(resp):
            try:
                if resp.request.resource_type in ("media", "image"):
                    ct = ""
                    try:
                        ct = (resp.headers or {}).get("content-type", "")
                    except Exception:  # noqa: BLE001
                        pass
                    wire.append({"url": resp.url, "ct": ct, "status": resp.status})
            except Exception:  # noqa: BLE001
                pass

        page.on("response", on_response)

    def action(page):
        try:
            state.update(page.evaluate(JS_TIKTOK) or {})
        except Exception as e:  # noqa: BLE001
            bl.log(f"  [tiktok harvest] {type(e).__name__}: {str(e)[:100]}")
        try:
            state.update(page.evaluate(JS_TIKTOK_PLAY) or {})
        except Exception:  # noqa: BLE001
            pass

    try:
        page = StealthyFetcher.fetch(
            TIKTOK, headless=True, network_idle=True, timeout=120_000,
            disable_resources=False, page_setup=setup, page_action=action,
        )
        (bl.RAW / "tiktok.html").write_text(page.html_content, encoding="utf-8")
        out["title"] = state.get("title")
        out["url"] = state.get("url", TIKTOK)
    except Exception as e:  # noqa: BLE001
        out["error"] = f"{type(e).__name__}: {str(e)[:200]}"
        bl.log(f"  tiktok fetch failed: {out['error']}")
        return out

    bl.log(f"  tiktok title : {state.get('title')}")
    bl.log(f"  video links  : {len(state.get('links', []))}")
    bl.log(f"  wire entries : {len(wire)}")

    out["descriptions"] = state.get("descs", [])[:60]
    out["post_links"] = state.get("links", [])[:80]

    # Download whatever video bitstreams actually reached the wire
    seen = set()
    for w in wire:
        u = w["url"].split("?")[0]
        if not u.endswith((".mp4", ".webm", ".mov")) or u in seen:
            continue
        if w.get("status") != 200:
            continue
        seen.add(u)
        got = bl.save_asset(u, "video", referer=TIKTOK)
        if got:
            out["videos"].append(got)
            bl.log(f"    video -> {got['file']} ({got['bytes']/1e6:.2f} MB)")
    out["video_count"] = len(out["videos"])
    return out


def main() -> None:
    bl.log("=== UNTAPPD (beer list) ===")
    beer = scrape_untappd()
    bl.dump_json(bl.BRAND / "beer_list.json", beer)
    bl.log("")
    bl.log("=== TIKTOK ===")
    tt = scrape_tiktok()
    bl.dump_json(bl.BRAND / "tiktok.json", tt)
    bl.log("")
    bl.log(f"beers : {len(beer.get('beers', []))}")
    bl.log(f"tiktok videos downloaded: {tt.get('video_count', 0)}")


if __name__ == "__main__":
    main()
