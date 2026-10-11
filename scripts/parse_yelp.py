"""
Phase 2e - Parse the captured Yelp page.

Yelp's React markup is hostile to selectors, but every page ships a
schema.org JSON-LD block carrying the authoritative business facts, and the
review feed is present as JSON in the hydration payload.

Extracts: rating, review count, price, categories, full opening hours,
phone, address, geo, amenities, and every review we can recover.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import brandlib as bl

WD = {"monday": "Mon", "tuesday": "Tue", "wednesday": "Wed", "thursday": "Thu",
      "friday": "Fri", "saturday": "Sat", "sunday": "Sun"}


def fmt_hour(h: str) -> str:
    m = re.match(r"(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})", h)
    if not m:
        return h
    a, b = int(m.group(1)), int(m.group(3))
    ap = "am" if a < 12 else "pm"
    bp = "am" if b < 12 else "pm"
    a12 = a if a <= 12 else a - 12
    b12 = b if b <= 12 else b - 12
    return f"{a12}:{m.group(2)} {ap} – {b12}:{m.group(4)} {bp}"


def all_ld_blocks(html: str) -> list[dict]:
    out = []
    for m in re.finditer(
        r'<script type="application/ld\+json">(.*?)</script>', html, re.S
    ):
        try:
            out.append(json.loads(m.group(1)))
        except Exception:  # noqa: BLE001
            pass
    return out


def find_image_objects(html: str) -> list[dict]:
    """Yelp's JSON-LD includes user-uploaded photos as ImageObject with a
    caption, author, rating and keyword tags - free sentiment + photo data."""
    photos = []
    seen = set()
    for m in re.finditer(
        r'"@type"\s*:\s*"ImageObject".{0,1800}?"contentUrl"\s*:\s*"(https?://[^"]+)"',
        html, re.S,
    ):
        seg = html[max(0, m.start() - 400): m.end() + 900]
        url = m.group(1)
        if url in seen:
            continue
        seen.add(url)
        cap = re.search(r'"caption"\s*:\s*"([^"]{3,300})"', seg)
        auth = re.search(r'"review"\s*:\s*\{.*?"name"\s*:\s*"([^"]{2,40})"', seg, re.S)
        rate = re.search(r'"ratingValue"\s*:\s*"?([\d.]+)', seg)
        date = re.search(r'"uploadDate"\s*:\s*"([^"]+)"', seg)
        kw = re.findall(r'"keywords"\s*:\s*\[([^\]]*)\]', seg)
        photos.append({
            "url": url,
            "caption": cap.group(1) if cap else "",
            "author": auth.group(1) if auth else "",
            "rating": rate.group(1) if rate else None,
            "date": (date.group(1)[:10] if date else ""),
            "keywords": [k.strip('" ') for k in kw[-1].split(",")] if kw else [],
        })
    return photos


def find_business_ld(html: str) -> dict | None:
    for m in re.finditer(
        r'<script type="application/ld\+json">(.*?)</script>', html, re.S
    ):
        try:
            o = json.loads(m.group(1))
        except Exception:  # noqa: BLE001
            continue
        stack = [o]
        while stack:
            n = stack.pop()
            if isinstance(n, dict):
                if n.get("@type") in ("Restaurant", "BarOrPub", "FoodEstablishment",
                                      "LocalBusiness"):
                    return n
                stack.extend(n.values())
            elif isinstance(n, list):
                stack.extend(n)
    return None


def find_reviews(html: str) -> list[dict]:
    """Reviews live in the hydration payload as review objects."""
    out: list[dict] = []
    seen: set[str] = set()

    # schema.org subjectOf reviews
    for m in re.finditer(r'"subjectOf"\s*:\s*(\[.*?\])\s*[,}]', html, re.S):
        try:
            arr = json.loads(m.group(1))
        except Exception:  # noqa: BLE001
            continue
        if isinstance(arr, list):
            for r in arr:
                if isinstance(r, dict) and (r.get("reviewBody") or r.get("name")):
                    txt = r.get("reviewBody") or r.get("description") or ""
                    if txt[:80] in seen:
                        continue
                    seen.add(txt[:80])
                    out.append({
                        "author": (r.get("author") or {}).get("name", "")
                                  if isinstance(r.get("author"), dict)
                                  else str(r.get("author") or ""),
                        "date": r.get("datePublished", ""),
                        "rating": (r.get("reviewRating") or {}).get("ratingValue")
                                  if isinstance(r.get("reviewRating"), dict) else None,
                        "text": txt.strip()[:3000],
                    })

    # Fallback: reviewRating objects scattered through the payload
    if not out:
        for m in re.finditer(r'"reviewRating"\s*:\s*\{[^}]*"ratingValue"\s*:\s*"?([\d.]+)', html):
            out.append({"rating": m.group(1), "text": ""})
    return out


def main() -> None:
    html = (bl.RAW / "yelp.html").read_text(encoding="utf-8", errors="ignore")

    ld = find_business_ld(html) or {}
    agg = ld.get("aggregateRating", {}) or {}
    addr = ld.get("address", {}) or {}

    rating = agg.get("ratingValue")
    review_count = agg.get("reviewCount")

    # Price range: Yelp renders it as a run of $ glyphs inside a hashed class
    pr = re.search(r'"priceRange"\s*:\s*"(\$+)"', html)
    price = pr.group(1) if pr else None
    if not price:
        m = re.search(r'priceRange[^>]*>(?:\s*<[^>]+>)*\s*(\$+)', html, re.I)
        price = m.group(1) if m else None
    if not price:
        m = re.search(r'>\s*(\${1,4})\s*<', html)
        price = m.group(1) if m else None

    # Categories
    cats = list(dict.fromkeys(
        re.findall(r'"name"\s*:\s*"(Beer Bar|Sports Bars?|Sandwiches|'
                   r'Restaurants Open Late|Sports Bar|Grills?|Steakhouse)"', html)))
    if not cats:
        cats = list(dict.fromkeys(re.findall(
            r'href="/biz/[^"]*\?[^"]*find_desc=([^"&]+)', html)))[:8]
        cats = [c.replace("+", " ") for c in cats]

    # Hours
    hours_raw = ld.get("openingHours", []) or []
    hours = {}
    for h in hours_raw:
        m = re.match(r"(\w+)\s+(.+)", h)
        if m:
            day = WD.get(m.group(1).lower(), m.group(1)[:3])
            hours[day] = fmt_hour(m.group(2))
    all_days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    hours_out = {d: hours.get(d, "Closed") for d in all_days}

    # Geo
    geo = {}
    m = re.search(r'"geo"\s*:\s*\{[^}]*"latitude"\s*:\s*"?([\d.-]+)[^}]*'
                  r'"longitude"\s*:\s*"?([\d.-]+)', html)
    if m:
        geo = {"lat": m.group(1), "lon": m.group(2)}

    reviews = find_reviews(html)
    yelp_photos = find_image_objects(html)

    # Amenities / attributes
    amenities = list(dict.fromkeys(re.findall(
        r'"amenity"\s*:\s*"([^"]{3,30})"', html)))[:20]
    if not amenities:
        amenities = list(dict.fromkeys(re.findall(
            r'/biz/[^"]*\?[^"]*attributes=([^"&]+)', html)))[:12]
        amenities = [a.replace("+", " ") for a in amenities]

    out = {
        "source": "Yelp (authenticated session)",
        "url": "https://www.yelp.com/biz/the-rustic-barrel-king-city-2",
        "name": ld.get("name"),
        "image": ld.get("image"),
        "telephone": ld.get("telephone"),
        "address": addr,
        "address_formatted": (f"{addr.get('streetAddress')}, {addr.get('addressLocality')}, "
                              f"{addr.get('addressRegion')} {addr.get('postalCode')}"
                              if addr else None),
        "rating": rating,
        "review_count": review_count,
        "price_range": price,
        "categories": cats,
        "hours": hours_out,
        "geo": geo,
        "amenities": amenities,
        "reviews_recovered": reviews,
        "review_count_in_page": html.count('"reviewRating"'),
        "user_photos": yelp_photos,
    }
    bl.dump_json(bl.BRAND / "yelp_parsed.json", out)

    # Download the large originals of every user-uploaded photo
    saved = []
    for p in yelp_photos:
        got = bl.save_asset(p["url"], "photo",
                            referer="https://www.yelp.com/biz/the-rustic-barrel-king-city-2")
        if got:
            saved.append({**p, "file": got["file"], "bytes": got["bytes"]})
    out["user_photos_downloaded"] = saved
    bl.dump_json(bl.BRAND / "yelp_parsed.json", out)

    bl.log("=" * 58)
    bl.log("YELP - The Rustic Barrel")
    bl.log("=" * 58)
    bl.log(f"  name      : {out['name']}")
    bl.log(f"  rating    : {rating}  ({review_count} reviews)")
    bl.log(f"  price     : {price}")
    bl.log(f"  phone     : {out['telephone']}")
    bl.log(f"  address   : {out['address_formatted']}")
    bl.log(f"  categories: {', '.join(cats[:6])}")
    bl.log("")
    bl.log("  hours:")
    for d in all_days:
        mark = "  " if hours_out[d] != "Closed" else "x "
        bl.log(f"    {mark}{d}  {hours_out[d]}")
    bl.log("")
    bl.log(f"  amenities : {len(amenities)}")
    for a in amenities[:10]:
        bl.log(f"    - {a}")
    bl.log("")
    bl.log(f"  review objects in page : {out['review_count_in_page']}")
    bl.log(f"  reviews recovered      : {len(reviews)}")
    for r in reviews[:10]:
        txt = re.sub(r"\s+", " ", r.get("text", ""))[:100]
        bl.log(f"    {str(r.get('rating','')):<5} {txt}")
    bl.log("")
    bl.log(f"  user photos found      : {len(yelp_photos)}")
    bl.log(f"  user photos downloaded : {len(saved)}")
    for p in yelp_photos[:10]:
        bl.log(f"    {str(p.get('rating','')):<5} {p['date']}  {p['caption'][:62]}")


if __name__ == "__main__":
    main()
