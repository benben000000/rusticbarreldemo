"""
Screenshot helper.

Used to review rendered output during development - the browser MCP tool loses
window visibility intermittently, and patchright headless is deterministic.

Usage:
  .venv\\Scripts\\python.exe scripts\\shot.py <page> [width] [height] [outname]
  .venv\\Scripts\\python.exe scripts\\shot.py all 1280 900
"""

from __future__ import annotations

import http.server
import socketserver
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
SHOTS = ROOT / "research" / "screens"
PORT = 8897

PAGES = {
    "home": "/",
    "menu": "/menu.html",
    "beer": "/beer.html",
    "events": "/events.html",
    "visit": "/visit.html",
    "404": "/404.html",
}


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

    # Pull flags out first, then take the rest positionally. Relying on a fixed
    # argv index meant `shot.py home 1280 900 "" full` silently captured a
    # viewport-height image named "-full", because PowerShell drops the empty
    # argument and every index shifted.
    argv = [a for a in sys.argv[1:] if not a.startswith("--")]
    full = "--full" in sys.argv[1:]
    scroll = None
    if "--scroll" in sys.argv[1:]:
        i = sys.argv.index("--scroll")
        scroll = int(sys.argv[i + 1])
        argv = [a for a in argv if a != sys.argv[i + 1]]

    arg = argv[0] if len(argv) > 0 else "all"
    width = int(argv[1]) if len(argv) > 1 else 1280
    height = int(argv[2]) if len(argv) > 2 else 900
    label = argv[3] if len(argv) > 3 else ""
    # "full" captures the whole scrollable page. Sections below the fold - the
    # feature cards in particular - are otherwise never actually looked at.

    targets = PAGES if arg in ("all", "a") else {arg: PAGES.get(arg, "/")}
    if arg not in PAGES and arg not in ("all", "a"):
        targets = {arg: arg if arg.startswith("/") else "/" + arg}

    SHOTS.mkdir(parents=True, exist_ok=True)
    httpd = serve()

    try:
        with sync_playwright() as pw:
            b = pw.chromium.launch(headless=True, args=["--force-color-profile=srgb"])
            for name, path in targets.items():
                ctx = b.new_context(viewport={"width": width, "height": height},
                                    device_scale_factor=1)
                pg = ctx.new_page()
                pg.goto(f"http://127.0.0.1:{PORT}{path}", wait_until="networkidle",
                        timeout=45_000)
                pg.wait_for_timeout(1200)

                if full:
                    # Walk the page before capturing. A full_page screenshot
                    # goes through CDP captureBeyondViewport, which resizes the
                    # surface without ever scrolling - so loading="lazy" art
                    # below the fold is never painted and photographs as a hole
                    # in the layout. Scrolling first makes the full-page shot
                    # trustworthy; without this it reports dead space that is
                    # not there.
                    h = pg.evaluate("document.documentElement.scrollHeight")
                    for y in range(0, int(h) + 800, 600):
                        pg.evaluate(f"window.scrollTo(0, {y})")
                        pg.wait_for_timeout(160)
                    pg.wait_for_timeout(1200)
                    pg.evaluate("window.scrollTo(0, 0)")
                    pg.wait_for_timeout(400)

                if scroll is not None:
                    # Scroll for real rather than cropping the full-page shot,
                    # for the same reason.
                    pg.evaluate(f"window.scrollTo(0, {scroll})")
                    pg.wait_for_timeout(1500)
                suffix = f"-{label}" if label else ""
                stem = f"{name}{suffix}-{width}x{height}"
                if full:
                    stem += "-full"
                out = SHOTS / f"{stem}.png"
                pg.screenshot(path=str(out), full_page=full)
                print(f"  {out.relative_to(ROOT)}  {out.stat().st_size:,}B")
                ctx.close()
            b.close()
    finally:
        httpd.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
