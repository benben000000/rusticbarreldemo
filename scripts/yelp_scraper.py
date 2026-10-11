"""
Phase 1j - Scrape Yelp using the authenticated profile.

Prerequisite: run scripts/yelp_login.py first and complete the sign-in. That
writes a persistent Chromium profile to .browsers/yelp_profile. This script
reopens the same profile, so the session cookie travels with it and Yelp serves
the page normally instead of 403.

Captures:
  * rating, review count, price range, categories, hours, amenities
  * the full review feed (author, date, rating, text, photos)
  * reviewer photos and owner/business photos

Outputs: research/raw/yelp.html, yelp.json, media/photos/yelp_*
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from scrapling.fetchers import StealthyFetcher

import brandlib as bl

BUSINESS = "https://www.yelp.com/biz/the-rustic-barrel-king-city-2"
PROFILE = Path(__file__).resolve().parent.parent / ".browsers" / "yelp_profile"

MAX_REVIEW_PAGES = 8


def make_setup(store: list):
    def setup(page):
        def on_response(resp):
            try:
                if resp.request.resource_type == "image":
                    ct = ""
                    try:
                        ct = (resp.headers or {}).get("content-type", "")
                    except Exception:  # noqa: BLE001
                        pass
                    if ct.startswith("image/"):
                        store.append({"url": resp.url, "ct": ct})
            except Exception:  # noqa: BLE001
                pass

        page.on("response", on_response)

    return setup


JS_HARVEST = r"""
() => {
  const abs = (u) => { try { return new URL(u, location.href).href; } catch { return u; } };
  const out = { review_count: null, rating: null, price: null, categories: [],
                address: null, phone: null, hours: [], amenities: [],
                reviews: [], imgs: [], title: document.title, url: location.href };
  const txt = document.body ? (document.body.innerText || '') : '';

  const rate = txt.match(/([\d.]+)\s*star/i) || txt.match(/([\d.]+)\s*out of 5/i);
  if (rate) out.rating = rate[1];
  const rc = txt.match(/([\d,]+)\s*reviews?/i);
  if (rc) out.review_count = rc[1];
  const pr = txt.match(/\$\$?/);
  if (pr) out.price = pr[0];

  document.querySelectorAll('a[href*="/categories/"], a[href*="?find_desc="]').forEach(a => {
    const t = (a.innerText || '').trim();
    if (t && t.length < 28 && !out.categories.includes(t)) out.categories.push(t);
  });
  const h = txt.match(/\d{3,5} [A-Z][A-Za-z]+ (St|Ave|Rd|Blvd|Dr|Way|Ct|Ln)\b[^\n]*/);
  if (h) out.address = h[0].trim();
  const ph = txt.match(/\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}/);
  if (ph) out.phone = ph[0];
  (txt.match(/(\d{1,2}:\d{2}\s?[ap]m\s?-\s?\d{1,2}:\d{2}\s?[ap]m)/gi) || [])
    .forEach(x => { if (!out.hours.includes(x)) out.hours.push(x); });

  document.querySelectorAll('li[data-test-target="amenity_text__list_item"], .amenity_description')
    .forEach(e => { const t = (e.innerText||'').trim(); if (t) out.amenities.push(t); });

  document.querySelectorAll('div[data-testid="serp-ia-card"]').forEach(c => {
    const who = (c.querySelector('a[href*="/user_details/"], .user-name a, .display-name')||{}).innerText || '';
    const date = (c.querySelector('.date, time')||{}).innerText || '';
    const stars = (c.querySelector('[data-test-target="review-rating"], .ftr-gallery .stars')||{}).innerText || '';
    const body = (c.querySelector('[data-test-target="review-text"], .review-text, .comment')||{}).innerText || '';
    const rimg = Array.from(c.querySelectorAll('img')).map(i => abs(i.currentSrc || i.src)).filter(Boolean);
    if (who || body) {
      out.reviews.push({ author: (who||'').trim(), date: (date||'').trim(),
                         stars: (stars||'').trim(), text: (body||'').trim().slice(0,2500),
                         images: rimg });
    }
  });

  document.querySelectorAll('img').forEach(i => {
    const s = i.currentSrc || i.src || '';
    if (s && !s.startsWith('data:') && (i.naturalWidth >= 300)) {
      out.imgs.push({ src: abs(s), w: i.naturalWidth, h: i.naturalHeight, alt: i.alt || '' });
    }
  });
  return out;
}
"""


def main() -> None:
    if not PROFILE.exists():
        bl.log("!! No saved Yelp profile found.")
        bl.log("   Run:  .venv\\Scripts\\python.exe scripts\\yelp_login.py")
        bl.log("   and complete the sign-in first.")
        return

    bl.log(f"using saved session: {PROFILE}")
    store: list[dict] = []
    state: dict = {}

    def action(page):
        try:
            page.wait_for_timeout(4000)
        except Exception:  # noqa: BLE001
            pass
        for i in range(MAX_REVIEW_PAGES):
            try:
                page.evaluate("() => window.scrollBy(0, 1400)")
                page.wait_for_timeout(1600)
            except Exception:  # noqa: BLE001
                break
        try:
            state.update(page.evaluate(JS_HARVEST) or {})
        except Exception as e:  # noqa: BLE001
            bl.log(f"  [harvest] {type(e).__name__}: {str(e)[:120]}")

    page = StealthyFetcher.fetch(
        BUSINESS,
        headless=True,
        network_idle=True,
        timeout=180_000,
        user_data_dir=str(PROFILE),
        disable_resources=False,
        page_setup=make_setup(store),
        page_action=action,
    )

    html = page.html_content
    (bl.RAW / "yelp.html").write_text(html, encoding="utf-8")
    bl.log(f"status: {getattr(page, 'status', None)}  bytes: {len(html)}")

    if "unusual traffic" in html.lower() or "are you a robot" in html.lower():
        bl.log("!! Yelp served a bot challenge - the session did not take.")
        bl.dump_json(bl.BRAND / "yelp.json", {"error": "bot challenge", "status":
                                              getattr(page, "status", None)})
        return

    dom = state or {}
    bl.log(f"rating      : {dom.get('rating')}")
    bl.log(f"reviews     : {dom.get('review_count')}")
    bl.log(f"price       : {dom.get('price')}")
    bl.log(f"categories  : {dom.get('categories', [])[:6]}")
    bl.log(f"hours       : {len(dom.get('hours', []))} slots")
    bl.log(f"amenities   : {len(dom.get('amenities', []))}")
    bl.log(f"reviews read: {len(dom.get('reviews', []))}")

    saved = []
    seen = set()
    for img in dom.get("imgs", [])[:160]:
        u = img["src"]
        if u in seen or "yelp-assets" in u and "photo" not in u:
            continue
        seen.add(u)
        got = bl.save_asset(u, "photo", referer=BUSINESS)
        if got:
            saved.append(got)

    bl.dump_json(bl.BRAND / "yelp.json", {
        "url": str(getattr(page, "url", BUSINESS)),
        "status": getattr(page, "status", None),
        "rating": dom.get("rating"),
        "review_count": dom.get("review_count"),
        "price": dom.get("price"),
        "categories": dom.get("categories"),
        "address": dom.get("address"),
        "phone": dom.get("phone"),
        "hours": dom.get("hours"),
        "amenities": dom.get("amenities"),
        "reviews": dom.get("reviews"),
        "images_saved": saved,
    })

    bl.log("")
    bl.log(f"images saved: {len(saved)}")
    bl.log("yelp data -> research/brand/yelp.json")

    revs = dom.get("reviews", [])
    if revs:
        bl.log("")
        bl.log("--- recent reviews ---")
        for r in revs[:8]:
            txt = re.sub(r"\s+", " ", r.get("text", ""))[:110]
            bl.log(f"  {r.get('author','')[:18]:<18} {r.get('stars','')[:22]:<22} {txt}")


if __name__ == "__main__":
    main()
