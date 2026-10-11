"""Overflow probe.

Finds any element whose text is wider than the box that clips it. Cheap way to
catch "looks fine until you look closely" problems that a static check and a
contrast audit both miss.

Usage: .venv\\Scripts\\python.exe scripts\\check_overflow.py [width] [height]
"""

from __future__ import annotations

import http.server
import socketserver
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
PORT = 8896

PAGES = ["/", "/menu.html", "/beer.html", "/events.html", "/visit.html", "/404.html"]

JS = r"""
() => {
  const bad = [];
  const docW = document.documentElement.clientWidth;
  const CLIPS = ['hidden', 'clip', 'auto', 'scroll'];

  // Standard screen-reader hide: clipped to 1px on purpose.
  const visHidden = el =>
    /(^|\s)(visually-hidden|sr-only|screen-reader-text|hidden-text)(\s|$)/
      .test(el.className || '');

  // The element clips its own overflow - a bleed image or a fixed-ratio box
  // doing exactly what it was built to do.
  const selfClips = el => CLIPS.includes(getComputedStyle(el).overflowX);

  // An ancestor clips it. The classic hero pattern is
  // section{overflow:hidden} > div{position:absolute} > img{transform:scale(1.05)}:
  // the scaled image is deliberately wider than the section so the blur has no
  // edge bleed.
  //
  // body and html are deliberately NOT counted. This site sets
  // overflow-x:hidden on body, so letting root clipping excuse everything made
  // the check report "clean" on the exact 390px bug it was written for - the
  // nav ran to x=460 on a 390px screen, body swallowed it, nothing was flagged.
  // Root-level clipping hides content from the user; it does not excuse it.
  const clippedByBox = el => {
    for (let p = el.parentElement; p; p = p.parentElement) {
      if (p === document.body || p === document.documentElement) continue;
      if (CLIPS.includes(getComputedStyle(p).overflowX)) return true;
    }
    return false;
  };

  // Is it laid out in the normal flow, or is it a positioned decoration?
  // Decorative layers are allowed to be oversized on purpose; content is not.
  const inFlow = el => {
    for (let p = el.parentElement; p; p = p.parentElement) {
      const ps = getComputedStyle(p).position;
      if (ps === 'absolute' || ps === 'fixed') return false;
      // sticky is still in flow - .site-header is sticky and its nav is content
    }
    return true;
  };

  for (const el of document.querySelectorAll('body *')) {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) continue;
    if (visHidden(el)) continue;

    // 1. content sticks out past the viewport and nothing contains it
    if ((r.right > docW + 1 || r.left < -1)
        && inFlow(el) && !clippedByBox(el)) {
      bad.push({ kind: 'viewport', sel: el.className || el.tagName,
                 got: Math.round(r.left) + '..' + Math.round(r.right),
                 want: 'within 0..' + docW });
      continue;
    }
    // 2. text wider than a box that does not clip it - i.e. actually lost
    if (el.scrollWidth > el.clientWidth + 1
        && cs.overflowX === 'visible' && !selfClips(el) && !clippedByBox(el)) {
      // Report what actually sticks out, not the ancestor that noticed.
      // "menu-list is 273px in a 230px box" is not actionable; the offending
      // text run is. Elements alone are not enough here: a long word can
      // overflow its inline box without its *element* box growing, so walk
      // text nodes with Ranges and compare their client rects.
      const box = el.getBoundingClientRect();
      let worst = null;
      const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
      let node;
      while ((node = walker.nextNode())) {
        if (!node.textContent.trim()) continue;
        const range = document.createRange();
        range.selectNodeContents(node);
        for (const rect of range.getClientRects()) {
          if (rect.width === 0) continue;
          if (rect.right > box.right + 1
              && (!worst || rect.right > worst.right)) {
            const p = node.parentElement;
            worst = {
              right: rect.right,
              sel: p.tagName + '.' + (p.className || ''),
              txt: node.textContent.trim().replace(/\s+/g, ' ').slice(0, 46),
            };
          }
        }
      }
      const sel = worst
        ? worst.sel.slice(0, 26) + ' "' + worst.txt + '"'
        : (el.className || el.tagName) + ' "' +
          (el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 40) + '"';
      bad.push({ kind: 'clipped', sel,
                 got: el.scrollWidth + 'px', want: '<= ' + el.clientWidth + 'px' });
    }
  }

  // 3. header rows must not collide with each other.
  // Overlap is not overflow: at 390px the nav drew straight over the wordmark
  // and the Order button ran off the edge, and every viewport check above still
  // passed because nothing exceeded the document width.
  for (const wrap of document.querySelectorAll('.site-header .wrap, .site-footer .wrap')) {
    const kids = [...wrap.children]
      .filter(el => getComputedStyle(el).display !== 'none')
      .filter(el => { const r = el.getBoundingClientRect();
                      return r.width > 0 && r.height > 0; });
    for (let i = 0; i < kids.length; i++) {
      for (let j = i + 1; j < kids.length; j++) {
        const a = kids[i].getBoundingClientRect();
        const b = kids[j].getBoundingClientRect();
        const ox = Math.min(a.right, b.right) - Math.max(a.left, b.left);
        const oy = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
        if (ox > 1 && oy > 1) {
          bad.push({ kind: 'overlap',
                     sel: (kids[i].className || kids[i].tagName) + ' / '
                          + (kids[j].className || kids[j].tagName),
                     got: Math.round(ox) + 'x' + Math.round(oy) + 'px',
                     want: 'no shared area' });
        }
      }
    }
  }
  return bad;
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

    width = int(sys.argv[1]) if len(sys.argv) > 1 else 1280
    httpd = serve()
    total = 0
    try:
        with sync_playwright() as pw:
            b = pw.chromium.launch(headless=True)
            ctx = b.new_context(viewport={"width": width, "height": 900})
            pg = ctx.new_page()
            for path in PAGES:
                pg.goto(f"http://127.0.0.1:{PORT}{path}", wait_until="networkidle",
                        timeout=45_000)
                pg.wait_for_timeout(700)
                rows = pg.evaluate(JS)
                if rows:
                    total += len(rows)
                    print(f"  {path}")
                    for r in rows[:12]:
                        print(f"      {r['kind']:<9} {str(r['sel'])[:34]:<34} "
                              f"{r['got']:<18} want {r['want']}")
                else:
                    print(f"  pass  {path}")
            ctx.close()
            b.close()
    finally:
        httpd.shutdown()
    print(f"\n  {total} overflowing element(s) at {width}px")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
