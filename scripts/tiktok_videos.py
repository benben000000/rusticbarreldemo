"""
Phase 1i - TikTok video library.

The TikTok profile page itself is login-walled, but the DOM still leaks every
video permalink - 70 of them for @therusticbarrel831. That is a second, entirely
separate video library the Instagram crawl never touched.

Two-stage retrieval per post:
  1. Static: fetch the permalink and look for playAddr / downloadAddr in the
     embedded JSON (fast, no browser)
  2. Dynamic: fall back to stealth Chromium + forced .play() to pull the real
     bitstream off the wire, the same trick the Instagram reels needed.

Outputs: research/media/videos/ + research/brand/tiktok_videos.json
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from scrapling.fetchers import Fetcher, StealthyFetcher

import brandlib as bl

MAX_VIDEOS = 45

# playAddr / downloadAddr appear JSON-escaped in TikTok's bootstrap payload.
PLAY_PATTERNS = [
    r'"playAddr"\s*:\s*"(https?://[^"]+)"',
    r'"downloadAddr"\s*:\s*"(https?://[^"]+)"',
    r'"playApi":"([^"]+)"',
]


def unescape(u: str) -> str:
    return (u.replace("\\u002F", "/").replace("\\/", "/")
             .replace("\\u0026", "&").replace("\\u003D", "=")
             .replace("\\u0025", "%").replace("\\/", "/"))


def try_static(url: str) -> tuple[str, str]:
    """TikTok's video pages are login-walled to plain HTTP (1.5 KB stub), but
    stealth Chromium renders the full document and the real playAddr appears in
    the hydrated HTML. Returns (playAddr, title/caption)."""
    state: dict = {}

    def action(page):
        try:
            page.wait_for_timeout(4500)
        except Exception:  # noqa: BLE001
            pass
        try:
            state["title"] = page.evaluate("() => document.title")
        except Exception:  # noqa: BLE001
            pass

    try:
        page = StealthyFetcher.fetch(
            url, headless=True, network_idle=True, timeout=90_000,
            disable_resources=True, page_action=action,
        )
        html = page.html_content
    except Exception:  # noqa: BLE001
        return "", ""

    for pat in (r'"playAddr":"([^"]+)"', r'"downloadAddr":"([^"]+)"'):
        m = re.search(pat, html)
        if m:
            return unescape(m.group(1)), state.get("title", "")
    return "", state.get("title", "")


JS_PLAY = r"""
async () => {
  const sleep = (ms) => new Promise(r => setTimeout(r, ms));
  for (let i = 0; i < 6; i++) {
    const v = document.querySelector('video');
    if (v) {
      v.muted = true;
      try { await v.play(); } catch (e) {}
      v.scrollIntoView({block: 'center'});
      await sleep(3500);
      return { src: v.currentSrc || v.src || '', w: v.videoWidth, h: v.videoHeight };
    }
    await sleep(900);
  }
  return { src: '' };
}
"""


def try_dynamic(url: str) -> tuple[str, list[dict]]:
    wire: list[dict] = []

    def setup(page):
        def on_response(resp):
            try:
                if resp.request.resource_type in ("media", "xhr", "fetch"):
                    u = resp.url
                    if ".mp4" in u or resp.request.resource_type == "media":
                        ct = ""
                        try:
                            ct = (resp.headers or {}).get("content-type", "")
                        except Exception:  # noqa: BLE001
                            pass
                        wire.append({"url": u, "ct": ct, "status": resp.status})
            except Exception:  # noqa: BLE001
                pass

        page.on("response", on_response)

    state: dict = {}

    def action(page):
        try:
            state.update(page.evaluate(JS_PLAY) or {})
        except Exception:  # noqa: BLE001
            pass
        try:
            page.wait_for_timeout(4000)
        except Exception:  # noqa: BLE001
            pass

    try:
        StealthyFetcher.fetch(
            url, headless=True, network_idle=True, timeout=60_000,
            disable_resources=False, page_setup=setup, page_action=action,
        )
    except Exception:  # noqa: BLE001
        return "", wire
    return state.get("src", ""), wire


def main() -> None:
    meta = json.loads((bl.BRAND / "tiktok.json").read_text(encoding="utf-8"))
    links = meta.get("post_links", [])[:MAX_VIDEOS]
    bl.log(f"tiktok videos queued: {len(links)}")

    saved: list[dict] = []
    seen: set[str] = set()
    stats = {"static_ok": 0, "dynamic_ok": 0, "failed": 0}

    for i, url in enumerate(links, 1):
        vid = url.rstrip("/").split("/")[-1]
        bl.log(f"  [{i}/{len(links)}] {vid}")

        src, title = try_static(url)
        got = None
        if src and src not in seen:
            seen.add(src)
            got = bl.save_asset(src, "video", referer=url)

        if got and got["bytes"] < 60_000:
            # TikTok serves a tiny preview at the default quality
            if "&quality=" not in src:
                hi = src + "&quality=1080p"
                better = bl.save_asset(hi, "video", referer=url)
                if better and better["bytes"] > got["bytes"]:
                    got = better

        if got:
            stats["static_ok"] += 1
            saved.append({"video_id": vid, "url": url, "title": title, **got})
            bl.log(f"     -> {got['file']} ({got['bytes']/1e6:.2f} MB)  {title[:56]}")
        else:
            dyn, wire = try_dynamic(url)
            cands = [dyn] if dyn else []
            cands += [w["url"] for w in wire if w.get("status") in (200, 206)]
            for c in cands:
                if not c or c in seen:
                    continue
                seen.add(c)
                got = bl.save_asset(c, "video", referer=url)
                if got and got["bytes"] > 120_000:
                    stats["dynamic_ok"] += 1
                    break
                got = None
            if got:
                saved.append({"video_id": vid, "url": url, "title": title, **got})
                bl.log(f"     -> {got['file']} ({got['bytes']/1e6:.2f} MB)")
            else:
                stats["failed"] += 1
                bl.log("     -> no video retrieved")
        time.sleep(1.5)

    bl.dump_json(bl.BRAND / "tiktok_videos.json",
                 {"stats": stats, "videos": saved})
    bl.log("")
    bl.log(f"tiktok videos saved: {len(saved)}")
    bl.log(f"  static: {stats['static_ok']}  dynamic: {stats['dynamic_ok']}  "
           f"failed: {stats['failed']}")


if __name__ == "__main__":
    main()
