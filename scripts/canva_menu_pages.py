"""
Phase 1f (cont) - Canva menu page 2 + structured parse.

The Canva viewer paginates by URL fragment (…/view#2), and the first pass only
ever hydrates page 1. Page 2 is where the drinks/beer live, so we fetch each
page fragment directly and merge the text.

Then parse the flat viewer text into structured items, and diff the restaurant's
own prices against what DoorDash is charging.

Outputs: research/brand/official_menu.json, official_menu.md, price_diff.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from scrapling.fetchers import StealthyFetcher

import brandlib as bl

BASE = "https://www.canva.com/design/DAHAU38TVeA/VT2V1I86CxNFujvjBKbSXg/view"

JS_TEXT = r"""
() => {
  let out = document.body ? (document.body.innerText || '') : '';
  document.querySelectorAll('iframe').forEach(f => {
    try {
      const d = f.contentDocument;
      if (d && d.body) out += '\n' + (d.body.innerText || '');
    } catch (e) {}
  });
  return out;
}
"""

CHROME_WORDS = re.compile(
    r"^(canva|toolbar|previous page|next page|go to page|zoom in and out|more|"
    r"enter full screen|create with canva|share|\(opens in a new tab.*|"
    r"group elements are not yet.*|\d+\s*/\s*\d+|aaaaaaaaaa|order online|"
    r"order doordash|order pick-up)$", re.I
)


def clean(text: str) -> list[str]:
    text = text.replace("\u2060", "")
    text = re.sub(r"[ \t]+", " ", text)
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if CHROME_WORDS.match(line):
            continue
        if line.isupper() and len(line) > 2 and not line.startswith("$"):
            out.append(line)
            continue
        out.append(line)
    return out


def fetch_page(n: int) -> list[str]:
    url = BASE if n == 1 else f"{BASE}#{n}"
    state: dict = {}

    def action(page):
        # Canva's document viewer hydrates slowly and re-fetches on layout.
        # The first successful pass used 9s + paginator nudges + 3s settles,
        # with resources enabled - disable_resources starves the viewer.
        for _ in range(3):
            try:
                page.wait_for_timeout(5000)
            except Exception:  # noqa: BLE001
                pass
        try:
            state["text"] = page.evaluate(JS_TEXT) or ""
        except Exception as e:  # noqa: BLE001
            bl.log(f"  [page {n}] evaluate failed: {type(e).__name__}")

    bl.log(f"fetching menu page {n} ...")
    try:
        page = StealthyFetcher.fetch(
            url, headless=True, network_idle=True, timeout=180_000,
            disable_resources=False, page_action=action,
        )
        (bl.RAW / f"canva_menu_p{n}.html").write_text(page.html_content, encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        bl.log(f"  page {n} failed: {type(e).__name__}: {str(e)[:140]}")
        return []
    lines = clean(state.get("text", ""))
    if not lines:
        bl.log(f"  page {n}: viewer text empty (login wall or slow hydrate)")
    return lines


PRICE_RE = re.compile(r"^(?:full\s+|half\s+)?(?P<prices>(?:\$?\d[\d,.]*\s*)+)$", re.I)
FULL_PRICE = re.compile(r"\$?(\d[\d,.]*)")


def parse_items(lines: list[str]) -> list[dict]:
    """Walk the flat text: a name line, optional price line, optional blurb."""
    items = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        price = ""
        # name followed by a pure price line
        if i + 1 < n and PRICE_RE.match(lines[i + 1]):
            price = lines[i + 1]
            body = []
            j = i + 2
            while j < n and not PRICE_RE.match(lines[j]) and j - i < 9:
                # stop if this looks like the next item heading
                body.append(lines[j])
                j += 1
            desc = " ".join(body).strip()
            items.append({"name": line, "price": price, "description": desc})
            i = j
            continue
        items.append({"name": line, "price": "", "description": ""})
        i += 1
    return items


def to_numbers(price: str) -> list[float]:
    return [float(x) for x in FULL_PRICE.findall(price or "")]


def main() -> None:
    all_lines: list[str] = []
    for pg in (1, 2, 3):
        lines = fetch_page(pg)
        if not lines:
            break
        # stop when a page repeats the previous one
        if all_lines and lines[:12] == all_lines[:12]:
            bl.log(f"  page {pg} duplicates page {pg-1}; stopping")
            break
        all_lines.extend(lines)
        bl.log(f"  page {pg}: {len(lines)} lines")

    (bl.BRAND / "official_menu_lines.txt").write_text(
        "\n".join(all_lines), encoding="utf-8")

    items = parse_items(all_lines)
    real = [it for it in items if it["description"] and not it["name"].isupper()]
    bl.dump_json(bl.BRAND / "official_menu.json",
                 {"lines": all_lines, "items": items, "dishes": real})

    bl.log("")
    bl.log(f"total lines : {len(all_lines)}")
    bl.log(f"parsed rows : {len(items)}  (with descriptions: {len(real)})")
    bl.log("")
    for it in real:
        bl.log(f"  {it['name'][:38]:<38} {it['price'][:26]}")

    # ---- price comparison vs DoorDash ------------------------------------- #
    dd = json.loads((bl.BRAND / "menu.json").read_text(encoding="utf-8"))
    dd_by_name = {i["name"].lower(): i for i in dd["items"]}

    def norm(s: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()

    dd_by_norm = {norm(k): v for k, v in dd_by_name.items()}

    diffs = []
    for it in real:
        k = norm(it["name"])
        match = dd_by_norm.get(k)
        if not match:
            # try prefix matching (DoorDash appends " - Half Order" etc.)
            for dk, dv in dd_by_norm.items():
                if dk.startswith(k) or k.startswith(dk):
                    match = dv
                    break
        if not match:
            continue
        menu_nums = to_numbers(it["price"])
        dd_num = to_numbers(match.get("price", ""))
        if not menu_nums or not dd_num:
            continue
        m = min(menu_nums)
        d = dd_num[0]
        diffs.append({
            "item": it["name"],
            "menu_price": m,
            "doordash_price": round(d, 2),
            "delta": round(d - m, 2),
            "pct": round((d - m) / m * 100, 1) if m else None,
        })

    diffs.sort(key=lambda x: -(x["pct"] or 0))
    bl.dump_json(bl.BRAND / "price_diff.json", diffs)

    bl.log("")
    bl.log("=== RESTAURANT MENU vs DOORDASH ===")
    bl.log(f"{'item':<34}{'menu':>8}{'doordash':>10}{'delta':>8}{'%':>7}")
    for d_ in diffs:
        bl.log(f"  {d_['item'][:32]:<34}{d_['menu_price']:>7.0f}"
               f"{d_['doordash_price']:>10.2f}{d_['delta']:>8.2f}{d_['pct']:>6.1f}%")
    if diffs:
        avg = sum(d_["pct"] for d_ in diffs if d_["pct"]) / max(len(diffs), 1)
        bl.log("")
        bl.log(f"  matched items: {len(diffs)}   average markup: {avg:.1f}%")


if __name__ == "__main__":
    main()
