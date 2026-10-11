"""
Accessibility gate - rendered contrast audit.

Why this exists as a separate check:

The ORDER button shipped with cream text on an amber background. The cause was
not a colour choice, it was CSS specificity - `.nav a` (0,1,1) silently outranks
`.btn--primary` (0,1,0), so the nav colour won. Every static check passed:
valid CSS, correct hex values in tokens.json, valid markup, HTTP 200.

Only a real browser sees that. So this audit renders every page, walks every
interactive element plus the custom text components, composites the actual
foreground over its real painted background, and fails on WCAG AA.

Run:  .venv\\Scripts\\python.exe scripts\\audit_contrast.py
Exit code 1 on any failure.
"""

from __future__ import annotations

import http.server
import socketserver
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
PORT = 8898

PAGES = ["/", "/menu.html", "/beer.html", "/events.html", "/visit.html", "/404.html"]

# What to audit: everything a human has to read.
SELECTORS = (
    "a, button, summary, "
    ".menu-item__price, .menu-item__variants, .menu-note, "
    ".beer-table td, .beer-table th, .hero-fact span, .footer-base span, "
    ".cta-disclosure, .card p, .lede, .label"
)

AUDIT_JS = """
(sel) => {
  const lum = c => { const f = x => { x/=255; return x<=0.03928 ? x/12.92
      : Math.pow((x+0.055)/1.055, 2.4); };
    return 0.2126*f(c[0]) + 0.7152*f(c[1]) + 0.0722*f(c[2]); };
  const parse = s => { const m = (s||'').match(/rgba?\\(([^)]+)\\)/); if(!m) return null;
    const p = m[1].split(',').map(parseFloat);
    return [p[0], p[1], p[2], p[3] === undefined ? 1 : p[3]]; };
  const comp = (f, b) => [ f[0]*f[3] + b[0]*(1-f[3]), f[1]*f[3] + b[1]*(1-f[3]),
                           f[2]*f[3] + b[2]*(1-f[3]) ];
  const ratio = (a, b) => { const L1 = Math.max(a,b), L2 = Math.min(a,b);
    return (L1+0.05)/(L2+0.05); };
  // Walk up for the nearest painted background - that is what the text
  // actually sits on, not the page default.
  const bgOf = el => { let n = el;
    while (n && n !== document.documentElement) {
      const c = parse(getComputedStyle(n).backgroundColor);
      if (c && c[3] > 0.05) return c;
      n = n.parentElement; }
    return parse(getComputedStyle(document.body).backgroundColor); };

  const out = [], seen = new Set();
  document.querySelectorAll(sel).forEach(el => {
    const txt = (el.innerText || '').trim().slice(0, 26);
    if (!txt) return;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none') return;
    const key = el.tagName + '|' + txt + '|' + cs.color;
    if (seen.has(key)) return;
    seen.add(key);
    const fg = parse(cs.color); if (!fg) return;
    const bg = bgOf(el); if (!bg) return;
    const c = comp(fg, bg);
    const size = parseFloat(cs.fontSize);
    const weight = parseInt(cs.fontWeight, 10) || 400;
    const large = size >= 24 || (size >= 18.66 && weight >= 700);
    const need = large ? 3 : 4.5;
    const r = ratio(lum(c), lum(bg));
    if (r < need) out.push({ text: txt, cls: String(el.className).slice(0, 34),
      color: cs.color, size: +size.toFixed(1), ratio: +r.toFixed(2), needs: need });
  });
  return { page: location.pathname, checked: seen.size, failing: out };
}
"""


def serve() -> socketserver.TCPServer:
    class H(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(SITE), **kw)

        def log_message(self, *a):  # silence
            pass

    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("127.0.0.1", PORT), H)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def main() -> int:
    from patchright.sync_api import sync_playwright

    httpd = serve()
    total_checked = 0
    all_failures: list[dict] = []

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            pg = browser.new_context(viewport={"width": 1280, "height": 900}).new_page()
            for path in PAGES:
                pg.goto(f"http://127.0.0.1:{PORT}{path}",
                        wait_until="networkidle", timeout=45_000)
                res = pg.evaluate(AUDIT_JS, SELECTORS)
                total_checked += res["checked"]
                status = "FAIL" if res["failing"] else "pass"
                print(f"  {status}  {path:<14} {res['checked']:>4} elements")
                for f in res["failing"]:
                    all_failures.append(f)
            browser.close()
    finally:
        httpd.shutdown()

    print()
    if all_failures:
        print("  WCAG AA FAILURES")
        print("  " + "-" * 60)
        for f in all_failures:
            print(f"   {f['ratio']:>5}:1 (needs {f['needs']})  "
                  f"{f['page']}  '{f['text']}'  .{f['cls']}")
        print()
        print(f"  {len(all_failures)} failures across {total_checked} elements")
        return 1

    print(f"  All {total_checked} text elements meet WCAG AA.")
    print("  Rendered-contrast gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
