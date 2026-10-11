"""
Phase 1e - Linktree hub scrape.

The Instagram bio points at linktr.ee/therusticbarrel_831, which is the only
place the business publishes its *owned* links - a Canva menu, an Untappd
beer list, a TikTok account and review links that never appear on any other
channel.

Linktree renders its links from an embedded __NEXT_DATA__ blob; the visible
<a> tags on the page belong to Linktree's "other creators" carousel, so we read
the JSON, not the DOM.

Outputs: research/raw/linktree.json  (+ links.json for the crawl queue)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

from scrapling.fetchers import Fetcher

import brandlib as bl

URL = "https://linktr.ee/therusticbarrel_831?utm_source=ig&utm_medium=social&utm_content=link_in_bio"


def classify(url: str, title: str) -> str:
    u = (url or "").lower()
    t = (title or "").lower()
    if not u:
        return "contact"
    if "canva.link" in u or u.endswith(".pdf") or "menu" in t:
        return "menu"
    if "untappd" in u or "untp.beer" in u:
        return "beer"
    if "tiktok" in u:
        return "social-video"
    if "instagram" in u:
        return "social-image"
    if "facebook" in u:
        return "social-image"
    if "yelp" in u:
        return "review"
    if "google.com" in u:
        return "review"
    if "order.online" in u or "doordash" in u or "ubereats" in u:
        return "ordering"
    return "other"


def main() -> None:
    r = Fetcher.get(URL, impersonate="chrome", stealthy_headers=True,
                    timeout=45, follow_redirects=True)
    html = r.body.decode("utf-8", "ignore")
    (bl.RAW / "linktree.html").write_text(html, encoding="utf-8")

    m = re.search(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        print("no __NEXT_DATA__ found")
        return
    data = json.loads(m.group(1))
    pp = data.get("props", {}).get("pageProps", {})
    account = pp.get("account", {}) or {}
    user = pp.get("user", {}) or account.get("user", {}) or {}
    links = account.get("links") or pp.get("links") or []

    # Linktree splits some links into sub-links (e.g. Contact Us -> email + phone)
    flattened: list[dict] = []
    for l in links:
        children = l.get("children") or []
        if children:
            for c in children:
                flattened.append({
                    "title": f"{l.get('title')} - {c.get('title')}",
                    "url": c.get("url"),
                    "type": l.get("type"),
                    "thumbnail": (c.get("thumbnail") or {}).get("url"),
                })
        else:
            flattened.append({
                "title": l.get("title"),
                "url": l.get("url"),
                "type": l.get("type"),
                "thumbnail": (l.get("thumbnail") or {}).get("url"),
                "raw_keys": [k for k in l.keys() if k in
                             ("email", "phone", "address", "note", "url", "title")],
            })

    out = {
        "profile_url": URL,
        "username": user.get("username"),
        "display_name": user.get("name"),
        "bio": user.get("bio"),
        "follower_count": user.get("followerCount"),
        "links": flattened,
        "unmapped_keys": {
            k: v for k, v in account.items()
            if k in ("bio", "followerCount", "isVerified", "plan", "city", "country")
        },
    }
    bl.dump_json(bl.RAW / "linktree.json", out)

    # Crawl queue, de-duplicated.
    queue, seen = [], set()
    for l in flattened:
        u = (l.get("url") or "").strip()
        if not u or u in seen:
            continue
        seen.add(u)
        queue.append({
            "title": l.get("title"),
            "url": u,
            "kind": classify(u, l.get("title") or ""),
            "host": urlparse(u).netloc,
        })
    bl.dump_json(bl.RAW / "links.json", queue)

    print(f"profile : {out['display_name']} (@{out['username']})")
    if out.get("bio"):
        print(f"bio     : {out['bio']}")
    print(f"links   : {len(flattened)}  (crawl queue: {len(queue)})")
    print()
    for q in queue:
        print(f"  [{q['kind']:<12}] {str(q['title'])[:34]:<34} {q['url'][:78]}")


if __name__ == "__main__":
    main()
