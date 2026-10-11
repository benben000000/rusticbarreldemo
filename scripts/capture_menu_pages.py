"""
Phase 6 - Capture the official menu as designed pages.

The text re-render of the Canva menu is unreadable because the viewer's
innerText is a flattened accessibility dump: sections collapse, descriptions
bleed into the next item, and prices orphan onto their own rows.

But the Canva design IS the real menu - laid out, priced and typeset by the
client. So capture it as rendered pages instead, and keep the text underneath
for search engines and screen readers.

This drives patchright directly: Scrapling has no screenshot primitive, and we
need the viewer chrome stripped before the capture.

Usage:  .venv\\Scripts\\python.exe scripts\\capture_menu_pages.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image

import brandlib as bl
from patchright.sync_api import sync_playwright

BASE = "https://www.canva.com/design/DAHAU38TVeA/VT2V1I86CxNFujvjBKbSXg/view"
OUT = bl.MEDIA / "menu_pages"

# Hide the Canva viewer chrome so only the designed page is captured.
HIDE_CHROME = """
(() => {
  const kill = [
    '[aria-label*="Toolbar" i]', '[data-testid*="toolbar" i]',
    'nav[aria-label*="tool" i]', '[class*="Toolbar"]',
    '[class*="BottomBar"]', '[class*="TopBar"]', '[class*="NavBar"]',
    '[class*="PageNav"]', '[class*="ZoomControls"]', '[class*="pagination" i]',
    '[role="toolbar"]', 'footer'
  ];
  kill.forEach(s => document.querySelectorAll(s).forEach(n => n.style.display = 'none'));
  // collapse any full-screen overlays that pad the page
  document.querySelectorAll('[class*="Overlay"], [class*="Modal"], [class*="Dialog"]')
    .forEach(n => { if (!n.querySelector('svg')) n.style.display = 'none'; });
  document.documentElement.style.background = '#ffffff';
  document.body && (document.body.style.background = '#ffffff',
                     document.body.style.margin = '0',
                     document.body.style.overflow = 'hidden');
  return true;
})()
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for f in OUT.glob("*"):
        f.unlink()

    captured: list[dict] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--force-color-profile=srgb"])
        for page_no in (1, 2):
            ctx = browser.new_context(
                viewport={"width": 1400, "height": 1800},
                device_scale_factor=2,          # 2x for a crisp retina capture
            )
            pg = ctx.new_page()
            url = BASE if page_no == 1 else f"{BASE}#{page_no}"
            print(f"[page {page_no}] loading {url}")
            pg.goto(url, wait_until="domcontentloaded", timeout=90_000)
            pg.wait_for_timeout(9000)          # viewer hydrate

            try:
                pg.evaluate(HIDE_CHROME)
                pg.wait_for_timeout(1200)
            except Exception as e:  # noqa: BLE001
                print(f"  chrome-strip failed: {type(e).__name__}")

            raw = OUT / f"menu-page-{page_no}-raw.png"
            try:
                pg.screenshot(path=str(raw), full_page=True)
            except Exception as e:  # noqa: BLE001
                print(f"  screenshot failed: {type(e).__name__}: {str(e)[:80]}")
                ctx.close()
                continue

            with Image.open(raw) as im:
                # trim the viewer chrome that survived
                box = im.convert("RGB").getbbox()
                im = im.convert("RGB")
                # crop to the widest non-uniform band (the page itself)
                cropped = trim_to_content(im)
                cropped.save(OUT / f"menu-page-{page_no}.png", "PNG", optimize=True)
                cropped.save(OUT / f"menu-page-{page_no}.webp", "WEBP",
                             quality=88, method=6)
                captured.append({
                    "page": page_no,
                    "png": f"menu_pages/menu-page-{page_no}.png",
                    "webp": f"menu_pages/menu-page-{page_no}.webp",
                    "width": cropped.width, "height": cropped.height,
                    "aspect": round(cropped.width / cropped.height, 3),
                    "bytes_png": (OUT / f"menu-page-{page_no}.png").stat().st_size,
                    "bytes_webp": (OUT / f"menu-page-{page_no}.webp").stat().st_size,
                })
                print(f"  captured {cropped.width}x{cropped.height} "
                      f"png={(OUT / f'menu-page-{page_no}.png').stat().st_size:,}B "
                      f"webp={(OUT / f'menu-page-{page_no}.webp').stat().st_size:,}B")
            raw.unlink(missing_ok=True)
            ctx.close()
        browser.close()

    bl.dump_json(bl.BRAND / "menu_pages.json", captured)
    print(f"\ncaptured {len(captured)} designed menu pages -> {OUT}")


def trim_to_content(im: Image.Image) -> Image.Image:
    """Crop to the designed page.

    Canva's viewer chrome (dark app header, Share / Create-with-Canva buttons)
    survives the CSS strip and lands as a black band at the top. The designed
    page sits on aged parchment - warm, light, low saturation - so we find the
    largest contiguous warm-light band and crop to it.
    """
    import numpy as np
    a = np.asarray(im.convert("RGB")).astype(int)
    h, w, _ = a.shape

    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    mx = a.max(axis=2)
    mn = a.min(axis=2)
    # parchment: light, and warmer than cool (r >= b)
    parchment = (mx > 150) & ((mx - mn) < 78) & (r >= b - 6)

    row_frac = parchment.mean(axis=1)
    thresh = 0.35
    rows = np.where(row_frac > thresh)[0]
    if len(rows) < 50:
        return im
    y0, y1 = int(rows[0]), int(rows[-1]) + 1

    band = parchment[y0:y1]
    col_frac = band.mean(axis=0) if band.size else np.zeros(w)
    cols = np.where(col_frac > max(0.25, col_frac.max() * 0.45))[0]
    if len(cols) < 20:
        return im.crop((0, y0, w, y1))
    x0, x1 = int(cols[0]), int(cols[-1]) + 1

    return im.crop((x0, y0, x1, y1))


if __name__ == "__main__":
    main()
