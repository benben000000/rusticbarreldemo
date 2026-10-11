"""Report whether every image actually decoded, before and after a scroll.

A full-page screenshot uses CDP captureBeyondViewport, which does not trigger
loading="lazy". A lazy image below the fold can therefore photograph as an empty
box that is 1393px tall and looks exactly like dead space - without being dead
space at all. This separates "the image is broken" from "the screenshot missed
it" before anyone edits CSS to chase a ghost.

Usage: .venv\\Scripts\\python.exe scripts\\check_images.py [page]
"""

from __future__ import annotations

import http.server
import socketserver
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
PORT = 8892

JS_SCAN = r"""
() => [...document.images].map((im, i) => ({
  i,
  src: (im.currentSrc || im.src || '').split('/').pop().slice(0, 46),
  complete: im.complete,
  natural: im.naturalWidth + 'x' + im.naturalHeight,
  rendered: Math.round(im.getBoundingClientRect().width) + 'x' +
             Math.round(im.getBoundingClientRect().height),
  loading: im.getAttribute('loading') || 'eager',
  top: Math.round(im.getBoundingClientRect().top + window.scrollY),
}))
"""


def serve():
    class H(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(SITE), **kw)

        def log_message(self, *a):
            pass

    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("127.0.0.1", PORT), H)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def report(rows, when):
    bad = [r for r in rows if not r["complete"] or r["natural"].startswith("0")]
    print(f"\n  after {when}: {len(rows)} images, {len(bad)} not decoded")
    for r in bad:
        print(f"      #{r['i']:<3} {r['src']:<46} natural={r['natural']:<10} "
              f"box={r['rendered']:<12} loading={r['loading']}")
    return len(bad)


def main() -> int:
    from patchright.sync_api import sync_playwright

    page = sys.argv[1] if len(sys.argv) > 1 else "/"
    httpd = serve()
    bad = 0
    try:
        with sync_playwright() as pw:
            b = pw.chromium.launch(headless=True)
            ctx = b.new_context(viewport={"width": 1280, "height": 900})
            pg = ctx.new_page()
            pg.goto(f"http://127.0.0.1:{PORT}{page}", wait_until="networkidle",
                    timeout=45_000)
            pg.wait_for_timeout(800)
            bad += report(pg.evaluate(JS_SCAN), "load, no scroll")

            # walk the page the way a person would
            h = pg.evaluate("document.documentElement.scrollHeight")
            for y in range(0, h, 700):
                pg.evaluate(f"window.scrollTo(0, {y})")
                pg.wait_for_timeout(180)
            pg.wait_for_timeout(1200)
            bad += report(pg.evaluate(JS_SCAN), "scrolled to the bottom")
            ctx.close()
            b.close()
    finally:
        httpd.shutdown()
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
