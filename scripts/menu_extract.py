"""
Phase 2c - Extract the full DoorDash menu as structured data.

The JSON-LD carries 150 MenuItems with names, descriptions and prices. That is
the single richest piece of brand-language the business publishes anywhere -
it tells us exactly how they name things, how they write, and what they sell.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import brandlib as bl

STOP = set("""the a an and or of with to for on in our is are at from by your you
this that it as be we all one two three four & more than then out up about
select choice side served topped our most popular""".split())


def walk(node, items, sections):
    if isinstance(node, dict):
        t = node.get("@type")
        if t == "MenuItem":
            price = ""
            off = node.get("offers")
            if isinstance(off, dict):
                price = off.get("price", "") or ""
            elif isinstance(off, list) and off:
                price = off[0].get("price", "") or ""
            items.append({
                "name": (node.get("name") or "").strip(),
                "description": re.sub(r"\s+", " ", (node.get("description") or "").strip()),
                "price": price,
            })
        if t == "MenuSection":
            sections.append(node.get("name", ""))
        for v in node.values():
            walk(v, items, sections)
    elif isinstance(node, list):
        for v in node:
            walk(v, items, sections)


def main() -> None:
    dd = json.loads((bl.RAW / "doordash.json").read_text(encoding="utf-8"))
    items: list[dict] = []
    sections: list[str] = []

    for raw in dd.get("dom", {}).get("jsonld", []):
        try:
            walk(json.loads(raw), items, sections)
        except Exception:  # noqa: BLE001
            pass

    # de-dupe by name, keep first
    seen = set()
    clean = []
    for it in items:
        k = it["name"].lower()
        if k and k not in seen:
            seen.add(k)
            clean.append(it)

    prices = []
    for it in clean:
        m = re.search(r"([\d.]+)", it["price"])
        if m:
            prices.append(float(m.group(1)))
    prices.sort()

    descs = [it["description"] for it in clean if it["description"]]
    words = Counter()
    for d in descs:
        for w in re.findall(r"[A-Za-z']+", d.lower()):
            if w not in STOP and len(w) > 2:
                words[w] += 1

    avg_desc = round(sum(len(d.split()) for d in descs) / max(len(descs), 1), 1)

    bl.dump_json(bl.BRAND / "menu.json", {
        "sections": sections,
        "items": clean,
        "stats": {
            "item_count": len(clean),
            "price_min": prices[0] if prices else None,
            "price_max": prices[-1] if prices else None,
            "price_median": prices[len(prices) // 2] if prices else None,
            "avg_description_words": avg_desc,
            "top_words": words.most_common(30),
        },
    })

    print(f"menu items      : {len(clean)}")
    print(f"sections        : {sections}")
    print(f"price range     : ${prices[0]:.2f} - ${prices[-1]:.2f}"
          if prices else "price range: n/a")
    print(f"median price    : ${prices[len(prices)//2]:.2f}" if prices else "")
    print(f"avg desc length : {avg_desc} words")
    print()
    print("top brand words :")
    print("   " + ", ".join(w for w, _ in words.most_common(25)))
    print()
    print("--- sample items ---")
    for it in clean[:8]:
        p = f"  {it['price']}" if it["price"] else ""
        print(f"  {it['name'][:40]:<40} {p}")
        if it["description"]:
            print(f"      {it['description'][:100]}")


if __name__ == "__main__":
    main()
