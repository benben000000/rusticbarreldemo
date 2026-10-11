"""
Phase 1d - Verified menu photography.

DoorDash serves sponsored ads (Michelob Ultra, etc.) through the SAME
/media/photosV2/ album path as the restaurant's real photography, so URL
patterns cannot tell them apart - we proved that the hard way.

The trustworthy link is the menu itself: each dish photo renders with an
`alt` attribute equal to the item name. So we expand the full menu in the
browser, harvest (alt -> image) pairs, and only keep images whose alt matches
a real item from the JSON-LD menu.

Outputs: research/raw/menu_photos.json  + photos written to
         research/media/menu_photos/
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

sys.path.insert(0, str(Path(__file__).resolve().parent))

from scrapling.fetchers import StealthyFetcher

import brandlib as bl

STORE = "https://www.doordash.com/store/the-rustic-barrel-king-city-34689489/90022148/?pickup=true&src=yp"
OUT = bl.MEDIA / "menu_photos"

# Expand every collapsed menu section, then walk the whole list.
JS_EXPAND = r"""
async () => {
  const sleep = (ms) => new Promise(r => setTimeout(r, ms));
  const words = ['expand','more','show more','see all','view all'];
  let clicked = 0;
  for (let pass = 0; pass < 6; pass++) {
    const btns = Array.from(document.querySelectorAll('button, [role="button"], a'));
    let n = 0;
    for (const b of btns) {
      const t = (b.innerText || b.textContent || '').trim().toLowerCase();
      if (t.length < 22 && words.some(w => t.includes(w))) {
        try { b.scrollIntoView({block:'center'}); b.click(); n++; clicked++; await sleep(180); }
        catch (e) {}
      }
    }
    if (!n) break;
    await sleep(400);
  }
  return clicked;
}
"""

JS_WALK = r"""
async () => {
  const sleep = (ms) => new Promise(r => setTimeout(r, ms));
  const seen = new Map();
  const grab = () => {
    document.querySelectorAll('img').forEach(el => {
      const src = el.currentSrc || el.src || '';
      if (!src || src.startsWith('data:')) return;
      const alt = (el.alt || '').trim();
      const w = el.naturalWidth, h = el.naturalHeight;
      if (!alt) return;
      if (w < 300) return;
      const key = src.split('?')[0];
      if (!seen.has(key) || seen.get(key).w < w) {
        seen.set(key, { src, alt, w, h });
      }
    });
  };
  grab();
  for (let i = 0; i < 70; i++) {
    window.scrollBy(0, 800);
    await sleep(140);
    grab();
  }
  window.scrollTo(0, document.body.scrollHeight);
  await sleep(600);
  grab();
  return { count: seen.size, items: Array.from(seen.values()) };
}
"""


def main() -> None:
    # Authoritative item list from the JSON-LD we already captured.
    menu_items: list[str] = []
    dd = json.loads((bl.RAW / "doordash.json").read_text(encoding="utf-8"))

    def walk(node):
        if isinstance(node, dict):
            if node.get("@type") == "MenuItem" and node.get("name"):
                menu_items.append(node["name"])
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    for raw in dd.get("dom", {}).get("jsonld", []):
        try:
            walk(json.loads(raw))
        except Exception:  # noqa: BLE001
            pass
    menu_items = list(dict.fromkeys(menu_items))
    print(f"menu items from JSON-LD: {len(menu_items)}", flush=True)

    def norm(s: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()

    norm_items = {norm(n): n for n in menu_items}

    state: dict = {}

    def action(page):
        # DoorDash redirects to a canonical store URL and may fire a location
        # prompt mid-load, which destroys the JS execution context. Settle the
        # page first, then retry the harvest until it actually returns data.
        for attempt in range(1, 5):
            try:
                try:
                    page.wait_for_load_state("domcontentloaded")
                    page.wait_for_timeout(2500)
                except Exception:  # noqa: BLE001
                    pass
                try:
                    print(f"  expand pass {attempt}", flush=True)
                    page.evaluate(JS_EXPAND)
                except Exception as e:  # noqa: BLE001
                    print(f"  [expand failed] {type(e).__name__}", flush=True)
                got = page.evaluate(JS_WALK) or {}
                if got.get("items"):
                    state.update(got)
                    print(f"  walk OK on pass {attempt}: {got['count']} alt-tagged images",
                          flush=True)
                    return
                state.update(got)
            except Exception as e:  # noqa: BLE001
                print(f"  [walk attempt {attempt} failed] {type(e).__name__}: "
                      f"{str(e)[:90]}", flush=True)
                try:
                    page.wait_for_timeout(3000)
                except Exception:  # noqa: BLE001
                    pass

    page = StealthyFetcher.fetch(
        STORE, headless=True, network_idle=True, timeout=120_000,
        solve_cloudflare=True, disable_resources=False,
        additional_args={"geolocation": None, "permissions": []},
        page_action=action,
    )
    (bl.RAW / "doordash_menu.html").write_text(page.html_content, encoding="utf-8")

    found = state.get("items", [])
    print(f"images with alt text: {len(found)}", flush=True)

    if OUT.exists():
        for f in OUT.iterdir():
            f.unlink()
    OUT.mkdir(parents=True, exist_ok=True)

    kept: list[dict] = []
    unmatched: list[dict] = []
    for im in found:
        alt = im["alt"]
        key = norm(alt)
        matched = norm_items.get(key)
        if not matched:
            # try prefix/substring match - alts are often truncated
            for nk, orig in norm_items.items():
                if nk and (nk.startswith(key) or key.startswith(nk)):
                    matched = orig
                    break
        row = {
            "url": im["src"], "alt": alt, "w": im["w"], "h": im["h"],
            "item": matched,
        }
        if matched:
            got = bl.save_asset(im["src"], "photo", referer=STORE)
            if got:
                slug = re.sub(r"[^A-Za-z0-9]+", "-", matched).strip("-")[:44]
                ext = got["ext"] if got["ext"] != ".bin" else ".jpg"
                dest = OUT / f"{slug}{ext}"
                src_path = bl.RESEARCH / got["file"]
                src_path.replace(dest)
                row["file"] = f"menu_photos/{dest.name}"
                kept.append(row)
        else:
            unmatched.append(row)

    bl.dump_json(bl.RAW / "menu_photos.json", {"kept": kept, "unmatched": unmatched})

    print()
    print(f"MENU PHOTOS MATCHED : {len(kept)}")
    print(f"unmatched (ads etc.): {len(unmatched)}")
    print()
    for r in kept[:15]:
        print(f"  {r['item'][:46]:<46} {r['w']}x{r['h']}")
    print(f"\n-> {OUT}")


if __name__ == "__main__":
    main()
