"""Find tall empty regions on a page.

The viewport screenshot showed a clean home page. The full-page screenshot
showed ~1500px of nothing between the stat cards and the footer, which no
viewport-height capture could reveal. This walks the DOM and reports any
element that is tall but holds no visible content of its own, so the thing
holding the page open can be named instead of guessed at.

Usage: .venv\\Scripts\\python.exe scripts\\find_dead_space.py [page] [minheight]
"""

from __future__ import annotations

import http.server
import socketserver
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
PORT = 8893

JS = r"""
(minH) => {
  const out = [];
  // A decoded image IS content. Without this every <img> reads as an empty
  // region - it has no text and no children - and the report fills with the
  // page's photographs instead of its holes.
  const LEAF = ['IMG', 'SVG', 'VIDEO', 'CANVAS', 'PICTURE', 'SOURCE', 'HR', 'BR'];
  const path = (el) => {
    const parts = [];
    for (let p = el; p && p !== document.body && parts.length < 4; p = p.parentElement) {
      parts.unshift(p.tagName.toLowerCase() +
        (p.className && typeof p.className === 'string'
          ? '.' + p.className.trim().split(/\s+/).join('.') : ''));
    }
    return parts.join('>');
  };
  for (const el of document.querySelectorAll('body *')) {
    if (LEAF.includes(el.tagName)) continue;
    // Decorative layers are allowed to be big and empty - the hero scrim is a
    // 673px gradient with no content in it by design.
    if (el.getAttribute('aria-hidden') === 'true') continue;
    const r = el.getBoundingClientRect();
    if (r.height < minH) continue;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || cs.opacity === '0') continue;

    let painted = 0;
    for (const d of el.querySelectorAll('img, svg, video, canvas')) {
      const dr = d.getBoundingClientRect();
      const decoded = d.tagName !== 'IMG' || d.naturalWidth > 0;
      if (dr.height > 0 && dr.width > 0 && decoded) painted++;
    }
    const hasText = Array.from(el.childNodes).some(
      n => n.nodeType === 3 && n.textContent.trim().length > 0);
    let childContent = 0;
    for (const c of el.children) {
      const cr = c.getBoundingClientRect();
      const ccs = getComputedStyle(c);
      if (cr.height > 8 && ccs.display !== 'none'
          && (c.tagName !== 'SCRIPT' && c.tagName !== 'STYLE')) childContent++;
    }

    if (painted === 0 && !hasText && childContent === 0) {
      out.push({ path: path(el), h: Math.round(r.height),
                 top: Math.round(r.top + window.scrollY),
                 minH: cs.minHeight, pad: cs.paddingTop + '/' + cs.paddingBottom,
                 mar: cs.marginTop + '/' + cs.marginBottom });
    }
  }
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

    page = sys.argv[1] if len(sys.argv) > 1 else "/"
    min_h = int(sys.argv[2]) if len(sys.argv) > 2 else 200

    httpd = serve()
    total = 0
    try:
        with sync_playwright() as pw:
            b = pw.chromium.launch(headless=True)
            ctx = b.new_context(viewport={"width": 1280, "height": 900})
            pg = ctx.new_page()
            pg.goto(f"http://127.0.0.1:{PORT}{page}", wait_until="networkidle",
                    timeout=45_000)
            pg.wait_for_timeout(900)
            h = pg.evaluate("document.documentElement.scrollHeight")
            rows = pg.evaluate(JS, min_h)
            print(f"  {page}   page height {h}px")
            if not rows:
                print(f"  no empty element taller than {min_h}px")
            for r in rows:
                total += r["h"]
                print(f"    {r['h']:>5}px @ {r['top']:>5}  {r['path']}")
                print(f"           min-height:{r['minH']}  padding:{r['pad']}  margin:{r['mar']}")
            ctx.close()
            b.close()
    finally:
        httpd.shutdown()
    print(f"\n  {len(rows)} empty region(s), {total}px combined")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
