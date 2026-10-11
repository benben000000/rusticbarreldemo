"""
Phase 1c - Reel video capture.

Instagram reels stream from blob: URLs and only start fetching the real MP4 once
playback begins. A passive page load therefore never puts video on the wire -
you get the poster frame and nothing else.

So: load each reel, unmute-mute it, call .play(), wait for the media request to
land on the listener, then pull the resulting .mp4 off the CDN.

Outputs: research/media/videos/ and research/raw/reels.json
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from scrapling.fetchers import StealthyFetcher

import brandlib as bl

PROFILE = "https://www.instagram.com/the_rustic_barrel_/"

JS_PLAY = r"""
async () => {
  const sleep = (ms) => new Promise(r => setTimeout(r, ms));
  for (let i = 0; i < 6; i++) {
    const v = document.querySelector('video');
    if (v) {
      v.muted = true;
      try { await v.play(); } catch (e) {}
      // force it into view so the pipeline engages
      v.scrollIntoView({block: 'center'});
      await sleep(2500);
      return { src: v.currentSrc || v.src || '', dur: v.duration || 0,
               w: v.videoWidth || 0, h: v.videoHeight || 0 };
    }
    await sleep(800);
  }
  return { src: '', dur: 0, w: 0, h: 0 };
}
"""


def make_setup(store: list):
    def setup(page):
        def on_response(resp):
            try:
                rtype = resp.request.resource_type
                if rtype in ("media", "image", "xhr", "fetch"):
                    url = resp.url
                    if ".mp4" in url or rtype == "media":
                        ct = ""
                        try:
                            ct = (resp.headers or {}).get("content-type", "")
                        except Exception:  # noqa: BLE001
                            pass
                        store.append({"url": url, "rtype": rtype, "ct": ct})
            except Exception:  # noqa: BLE001
                pass

        page.on("response", on_response)

    return setup


def make_action(state: dict):
    def action(page):
        try:
            state.update(page.evaluate(JS_PLAY) or {})
        except Exception as e:  # noqa: BLE001
            print(f"     [play failed] {type(e).__name__}: {str(e)[:120]}", flush=True)
        try:
            page.wait_for_timeout(6000)  # let the stream buffer
        except Exception:  # noqa: BLE001
            pass

    return action


def find_reels() -> list[str]:
    p = bl.RAW / "instagram_tiles.json"
    hrefs = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
    reels = [h for h in hrefs if "/reel/" in h]
    from urllib.parse import urljoin
    return [urljoin(PROFILE, h) for h in reels]


def main() -> None:
    reels = find_reels()
    print(f"reels to capture: {len(reels)}", flush=True)

    results: list[dict] = []
    saved: list[dict] = []

    for i, url in enumerate(reels, 1):
        store: list[dict] = []
        state: dict = {}
        print(f"  [{i}/{len(reels)}] {url.split('/')[-3]}", flush=True)
        try:
            page = StealthyFetcher.fetch(
                url,
                headless=True,
                network_idle=True,
                timeout=90_000,
                page_setup=make_setup(store),
                page_action=make_action(state),
            )
        except Exception as e:  # noqa: BLE001
            print(f"     failed: {type(e).__name__}: {str(e)[:100]}", flush=True)
            continue

        (bl.RAW / f"reel_{i:02d}.html").write_text(page.html_content, encoding="utf-8")

        # Collect every mp4 that showed up on the wire.
        mp4s = []
        for w in store:
            u = w["url"]
            if ".mp4" in u and u not in [m["url"] for m in mp4s]:
                mp4s.append(w)

        # Fall back to the element's currentSrc if it is a real CDN URL.
        src = state.get("src", "")
        if src and src.startswith("http") and ".mp4" in src:
            if src not in [m["url"] for m in mp4s]:
                mp4s.append({"url": src, "rtype": "media", "ct": "video/mp4"})

        got = []
        for m in mp4s:
            got_asset = bl.save_asset(m["url"], "video", referer=url)
            if got_asset:
                got.append(got_asset)
                saved.append(got_asset)
                print(f"     video -> {got_asset['file']} "
                      f"({got_asset['bytes']/1e6:.2f} MB)", flush=True)

        results.append({
            "index": i, "url": url, "element_src": src,
            "duration": state.get("dur"), "dims": [state.get("w"), state.get("h")],
            "wire_media": len(store), "mp4_found": len(mp4s), "saved": got,
        })
        time.sleep(3)

    bl.dump_json(bl.RAW / "reels.json", results)
    bl.dump_json(bl.BRAND / "reel_assets.json", saved)
    print(f"\nreels processed: {len(results)}  videos saved: {len(saved)}", flush=True)


if __name__ == "__main__":
    main()
