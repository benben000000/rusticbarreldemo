"""Print the real geometry of the widest offending menu row, so the cause is
read off the layout instead of guessed at.

Usage: .venv\\Scripts\\python.exe scripts\\probe_menu_row.py [width]
"""

from __future__ import annotations

import http.server
import socketserver
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
PORT = 8894
WIDTH = int(sys.argv[1]) if len(sys.argv) > 1 else 360

JS = r"""
() => {
  const list = document.querySelector('.menu-list');
  const box = list.getBoundingClientRect();
  const chain = [];
  let el = list;
  while (el && el !== document.documentElement) {
    const r = el.getBoundingClientRect();
    chain.push(`${el.tagName}.${(el.className || '').split(' ')[0]}  `
      + `box=${Math.round(r.left)}..${Math.round(r.right)} w=${Math.round(r.width)} `
      + `client=${el.clientWidth} scroll=${el.scrollWidth} `
      + `pad=${getComputedStyle(el).paddingLeft}/${getComputedStyle(el).paddingRight} `
      + `disp=${getComputedStyle(el).display}`);
    el = el.parentElement;
  }
  let worst = null;
  const w = document.createTreeWalker(list, NodeFilter.SHOW_TEXT);
  let n;
  while ((n = w.nextNode())) {
    if (!n.textContent.trim()) continue;
    const rg = document.createRange();
    rg.selectNodeContents(n);
    for (const rr of rg.getClientRects()) {
      if (rr.width && rr.right > box.right + 1 && (!worst || rr.right > worst.right)) {
        worst = { right: Math.round(rr.right), t: n.textContent.trim().slice(0, 40),
                  p: n.parentElement.tagName + '.' + (n.parentElement.className || '') };
      }
    }
  }
  return { box: `menu-list ${Math.round(box.left)}..${Math.round(box.right)}`,
           chain, worst };
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
            ctx = b.new_context(viewport={"width": WIDTH, "height": 900})
            pg = ctx.new_page()
            pg.goto(f"http://127.0.0.1:{PORT}/menu.html", wait_until="networkidle",
                    timeout=45_000)
            pg.wait_for_timeout(600)
            data = pg.evaluate(JS)
            print(f"  @ {WIDTH}px   {data['box']}")
            for row in data["chain"]:
                print("    " + row)
            w = data["worst"]
            print("    worst text: " + (f"{w['p']}  right={w['right']}  \"{w['t']}\""
                                         if w else "none past the menu-list box"))
            ctx.close()
            b.close()
    finally:
        httpd.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
