"""
Phase 1f - Pull the official Canva menu.

The Linktree menu link resolves to a public Canva design (DAHAU38TVeA). Canva's
viewer renders through canvas/WebGL and exposes the source pages and a download
endpoint only after the document loads, so this runs in stealth Chromium and
picks the PDF/asset URLs off the wire.

Outputs: research/media/menus/  +  research/brand/menu_pdf.json
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from scrapling.fetchers import StealthyFetcher, Fetcher

import brandlib as bl

CANVA = "https://www.canva.com/design/DAHAU38TVeA/VT2V1I86CxNFujvjBKbSXg/view"
OUT = bl.MEDIA / "menus"

# Canva's document viewer lives inside an iframe and streams page assets from
# several CDN hosts, so match broadly on the wire and filter afterwards.
INTEREST = re.compile(r"(\.pdf|export|document|/pages?/|media\.canva|cdn\.canva)", re.I)

SKIP_HOSTS = ("gravatar", "google-analytics", "googletagmanager", "doubleclick",
              "facebook.net/tr", "hotjar", "segment.io", "sentry.io", "mixpanel")


def make_setup(store: list):
    def setup(page):
        def on_response(resp):
            try:
                u = resp.url
                if u.startswith("data:"):
                    return
                if any(h in u for h in SKIP_HOSTS):
                    return
                if not INTEREST.search(u):
                    return
                ct = ""
                try:
                    ct = (resp.headers or {}).get("content-type", "")
                except Exception:  # noqa: BLE001
                    pass
                store.append({"url": u, "ct": ct, "status": resp.status})
            except Exception:  # noqa: BLE001
                pass

        page.on("response", on_response)

    return setup


def make_action(state: dict):
    def action(page):
        # The document renders in an iframe; wait long enough for Canva to
        # hydrate the viewer and fetch the page bitmaps.
        try:
            page.wait_for_timeout(9000)
        except Exception:  # noqa: BLE001
            pass
        # Step through the paginator so later pages load as well.
        for _ in range(4):
            try:
                moved = page.evaluate("""() => {
                    const frames = Array.from(document.querySelectorAll('iframe'));
                    const scope = document;
                    const btns = Array.from(scope.querySelectorAll('button,[role="button"]'));
                    const next = btns.find(b => {
                        const l = (b.getAttribute('aria-label') || b.innerText || '').trim();
                        return /^(next|right|›|→)$/i.test(l);
                    });
                    if (next) { next.click(); return true; }
                    return false;
                }""")
            except Exception:  # noqa: BLE001
                moved = False
            try:
                page.wait_for_timeout(3000)
            except Exception:  # noqa: BLE001
                pass
            if not moved:
                break
        try:
            state["title"] = page.evaluate("() => document.title")
            state["url"] = page.evaluate("() => location.href")
            state["frames"] = page.evaluate(
                "() => Array.from(document.querySelectorAll('iframe')).map(f => f.src)"
            )
            # Read text from the top document AND every same-origin frame.
            state["body_text"] = page.evaluate("""() => {
                let out = document.body ? (document.body.innerText || '') : '';
                document.querySelectorAll('iframe').forEach(f => {
                    try {
                        const d = f.contentDocument;
                        if (d && d.body) out += '\\n' + (d.body.innerText || '');
                    } catch (e) {}
                });
                return out.slice(0, 20000);
            }""")
        except Exception:  # noqa: BLE001
            pass

    return action


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    store: list[dict] = []
    state: dict = {}

    print("loading Canva design in stealth Chromium...", flush=True)
    page = StealthyFetcher.fetch(
        CANVA, headless=True, network_idle=True, timeout=120_000,
        disable_resources=False, page_setup=make_setup(store),
        page_action=make_action(state),
    )
    html = page.html_content
    (bl.RAW / "canva_menu.html").write_text(html, encoding="utf-8")
    print(f"title : {state.get('title')}")
    print(f"final : {state.get('url', '')[:120]}")
    print(f"wire  : {len(store)} candidate asset requests")
    print()

    # 1. Direct PDF links seen on the wire
    pdfs = [s for s in store if ".pdf" in s["url"].lower() and s["status"] == 200]
    # 2. Canva export endpoint discovered in the page source
    m = re.search(r'"(?:downloadUrl|exportUrl)":"([^"]+)"', html)
    if m:
        pdfs.append({"url": m.group(1).encode().decode("unicode_escape"),
                     "ct": "application/pdf", "status": 200})

    saved = []
    for i, p in enumerate(dict.fromkeys([x["url"] for x in pdfs]), 1):
        try:
            r = Fetcher.get(p, impersonate="chrome", stealthy_headers=True,
                            timeout=90, follow_redirects=True,
                            headers={"Referer": CANVA})
            if r.status == 200 and r.body[:4] == b"%PDF":
                f = OUT / f"rustic-barrel-menu-{i:02d}.pdf"
                f.write_bytes(r.body)
                saved.append({"url": p, "file": f"menus/{f.name}",
                              "bytes": len(r.body)})
                print(f"  saved PDF: {f.name} ({len(r.body)/1e6:.2f} MB)")
            else:
                print(f"  not a pdf (status={r.status}, "
                      f"magic={r.body[:4]!r}): {p[:90]}")
        except Exception as e:  # noqa: BLE001
            print(f"  download failed: {type(e).__name__}: {str(e)[:90]}")

    # 3. Page images - a Canva menu is often readable page by page
    imgs = [s for s in store if s["ct"].startswith("image/") and s["status"] == 200
            and "profile" not in s["url"]]
    uniq = list(dict.fromkeys(s["url"] for s in imgs))
    print(f"\nimage assets on wire: {len(uniq)}")
    got_imgs = []
    for i, u in enumerate(uniq[:60], 1):
        got = bl.save_asset(u, "photo", referer=CANVA)
        if got:
            got_imgs.append(got)

    # Move anything menu-ish out of the flat photo bucket
    pagen = 0
    for g in got_imgs:
        if any(k in g["url"].lower() for k in ("page", "document", "design")):
            src = bl.MEDIA / "photos" / Path(g["file"]).name
            if src.exists():
                dest = OUT / f"menu-page-{pagen+1:02d}{src.suffix}"
                src.replace(dest)
                g["file"] = f"menus/{dest.name}"
                pagen += 1

    bl.dump_json(bl.BRAND / "menu_pdf.json", {
        "canva_url": CANVA,
        "title": state.get("title"),
        "iframes": state.get("frames", []),
        "pdfs": saved,
        "image_assets": got_imgs,
        "wire_sample": store[:80],
        "body_text": state.get("body_text", "")[:20000],
    })

    print(f"\npdfs saved : {len(saved)}")
    print(f"images saved: {len(got_imgs)}  (menu pages relabelled: {pagen})")
    print(f"-> {OUT}")

    txt = state.get("body_text", "")
    if txt.strip():
        safe = txt[:2500].encode("ascii", "replace").decode("ascii")
        print("\n--- rendered text (first 2500 chars, non-ASCII stripped) ---")
        print(safe)


if __name__ == "__main__":
    main()
