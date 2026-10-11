"""Header layout probe - prints the real boxes so the overlap rule can be
written against what the browser actually does, not what it looks like.

Run with the fix in place, then again with the @media block removed, to see
which of the two states the check in check_overflow.py can tell apart.
"""

from __future__ import annotations

import http.server
import socketserver
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
PORT = 8895
WIDTH = int(sys.argv[1]) if len(sys.argv) > 1 else 390

JS = r"""
() => {
  const wrap = document.querySelector('.site-header .wrap');
  const out = [];
  const box = el => {
    const r = el.getBoundingClientRect();
    return `${Math.round(r.left)},${Math.round(r.top)} ${Math.round(r.right)},${Math.round(r.bottom)}`;
  };
  out.push(['viewport', `${document.documentElement.clientWidth}`]);
  for (const el of wrap.children) {
    const cs = getComputedStyle(el);
    out.push([el.className || el.tagName, box(el),
              `w=${Math.round(el.getBoundingClientRect().width)}`,
              `flexBasis=${cs.flexBasis}`, `minW=${cs.minWidth}`]);
  }
  // does the brandmark's own content spill past its box?
  const bm = wrap.querySelector('.brandmark');
  const span = bm.querySelector('span');
  out.push(['brandmark span', box(span)]);
  out.push(['brandmark scrollW', `${bm.scrollWidth} clientW=${bm.clientWidth}`]);
  out.push(['wrap scrollW', `${wrap.scrollWidth} clientW=${wrap.clientWidth}`]);
  return out;
}
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


def main() -> int:
    from patchright.sync_api import sync_playwright

    httpd = serve()
    try:
        with sync_playwright() as pw:
            b = pw.chromium.launch(headless=True)
            ctx = b.new_context(viewport={"width": WIDTH, "height": 844})
            pg = ctx.new_page()
            pg.goto(f"http://127.0.0.1:{PORT}/", wait_until="networkidle", timeout=45_000)
            pg.wait_for_timeout(600)
            print(f"  @ {WIDTH}px")
            for row in pg.evaluate(JS):
                print("    " + "  ".join(str(c) for c in row))
            ctx.close()
            b.close()
    finally:
        httpd.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
