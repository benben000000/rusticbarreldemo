"""
Site build - page generator.

The four secondary pages are generated from the scraped data rather than typed
by hand. That keeps a single source of truth (the crawl output) and means a
menu or price change is a re-run, not an edit.

Every generated page emits: unique title, unique meta description, canonical,
one h1, indexable body copy, internal links, and JSON-LD where relevant.

Usage:  .venv\\Scripts\\python.exe scripts\\build_pages.py
"""

from __future__ import annotations

import html
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import brandlib as bl

SITE = bl.RESEARCH.parent / "site"
BRAND = bl.BRAND

# Canonical origin, read from tokens.json. This used to be a hardcoded string,
# which made it a second source of truth beside the token: repointing the site
# at a new host moved the sitemap and left every generated page claiming the old
# domain. Nothing caught it, because the gate only checked that a canonical
# started with https:// - which the stale one did.
BASE = json.loads((SITE / "assets" / "tokens.json").read_text(encoding="utf-8"))["seo"]["canonicalBase"].rstrip("/")

NAV = [
    ("/menu", "Menu"), ("/beer", "Beer"),
    ("/events", "Events"), ("/visit", "Visit"),
]

FOOTER_GOOD = [
    "Closed Tuesdays",
    "Listed prices are cash prices",
    "Card payments add processing fees",
]

SOCIAL = [
    ("https://www.instagram.com/the_rustic_barrel_/", "Instagram &mdash; @the_rustic_barrel_"),
    ("https://www.tiktok.com/@therusticbarrel831", "TikTok &mdash; @therusticbarrel831"),
    ("https://www.facebook.com/therusticbarreltaphouse", "Facebook"),
    ("https://untappd.com/v/the-rustic-barrel/13736755", "Untappd &mdash; check in"),
    ("https://www.yelp.com/biz/the-rustic-barrel-king-city-2", "Yelp &mdash; leave a review"),
]

DD = ("https://www.doordash.com/store/the-rustic-barrel-king-city-34689489"
      "/90022148/?pickup=true")
UE = "https://www.ubereats.com/store/the-rustic-barrel/j50H6Tr2W-qha1Ep9ys4Ag"


def esc(s) -> str:
    return html.escape(str(s if s is not None else ""), quote=True)


# --------------------------------------------------------------------------- #
# Shared shell
# --------------------------------------------------------------------------- #
def shell(*, slug, title, desc, active, body, jsonld="", og_alt="") -> str:
    nav = "".join(
        f'<a href="{href}"'
        + (' aria-current="page"' if href == active else "")
        + f">{label}</a>"
        for href, label in NAV
    )
    social = "".join(f'<li><a href="{u}" rel="noopener">{t}</a></li>'
                     for u, t in SOCIAL)
    good = "".join(f"<li>{g}</li>" for g in FOOTER_GOOD)
    ld = f"\n<script type=\"application/ld+json\">\n{jsonld}\n</script>" if jsonld else ""

    # Public path for canonical/og:url. Vercel cleanUrls serves /menu from
    # menu.html, so the canonical must be the extensionless path. Canonicalising
    # /menu.html while /menu is what the nav links to and what the sitemap
    # lists is how a site tells Google one URL and serves another.
    path = "/" if slug == "index.html" else "/" + Path(slug).stem

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{BASE}{path}">
<meta name="theme-color" content="#1F1610">
<meta name="robots" content="index, follow, max-image-preview:large">
<meta property="og:type" content="website">
<meta property="og:site_name" content="The Rustic Barrel Taphouse">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{BASE}{path}">
<meta property="og:image" content="{BASE}/assets/img/og-default.jpg">
<meta property="og:image:alt" content="{esc(og_alt or 'The Rustic Barrel Taphouse barrel-head badge logo')}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(desc)}">
<meta name="twitter:image" content="{BASE}/assets/img/og-default.jpg">
<link rel="icon" href="{LOGO_AVATAR}" type="image/webp">
<link rel="apple-touch-icon" href="/assets/img/logo-icon-192.png">
<link rel="manifest" href="/site.webmanifest">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Rye&family=Bevan&family=Kaushan+Script&family=Barlow:wght@400;500;600;700&display=swap">
<link rel="stylesheet" href="/assets/tokens.css">
<link rel="stylesheet" href="/assets/css/site.css">{ld}
</head>
<body class="wood wood--dark">
<a class="skip-link" href="#main">Skip to content</a>
<header class="site-header">
  <div class="wrap">
    <a class="brandmark" href="/">
      <img src="/assets/img/logo-avatar-dark.webp" width="40" height="40"
           alt="{LOGO_ALT}" fetchpriority="high">
      <span>The Rustic Barrel<small>Taphouse &middot; King City</small></span>
    </a>
    <nav class="nav" aria-label="Primary">{nav}
      <a class="btn btn--primary" href="/#order" style="min-height:40px;padding:.35rem .8rem;">Order</a>
    </nav>
  </div>
</header>
<main id="main">
{body}
</main>
<footer class="site-footer">
  <div class="wrap">
    <div class="footer-grid">
      <div><h3>The Rustic Barrel Taphouse</h3>
        <p style="color:var(--color-ink-on-dark-muted)">611 Canal St<br>King City, CA 93930<br>
        <a href="tel:+18316011397">(831) 601-1397</a><br>
        <a href="mailto:therusticbarrel831@gmail.com">therusticbarrel831@gmail.com</a></p></div>
      <div><h3>Explore</h3><ul>
        <li><a href="/menu">Menu</a></li><li><a href="/beer">Beer &amp; tap list</a></li>
        <li><a href="/events">Events</a></li><li><a href="/visit">Visit us</a></li></ul></div>
      <div><h3>Order</h3><ul>
        <li><a href="{DD}" rel="nofollow noopener" target="_blank">DoorDash pickup</a></li>
        <li><a href="{UE}" rel="nofollow noopener" target="_blank">Uber Eats pickup</a></li>
        <li><a href="tel:+18316011397">Phone in for a large order</a></li></ul></div>
      <div><h3>Good to know</h3><ul>{good}</ul></div>
    </div>
    <div class="footer-base">
      <span>&copy; <span data-year>2026</span> The Rustic Barrel Taphouse.</span>
      <span>Built static &mdash; no trackers.</span>
    </div>
  </div>
</footer>
<script src="/assets/js/deeplink.js" defer></script>
<script>document.querySelector('[data-year]').textContent=new Date().getFullYear();</script>
</body>
</html>
"""


LOGO = "/assets/img/logo-mark-dark.webp"
LOGO_W, LOGO_H = 720, 556
LOGO_AVATAR = "/assets/img/logo-avatar.webp"
LOGO_ALT = ("The Rustic Barrel logo: an engraved barrel lettered The Rustic "
            "Barrel, flanked by hop cones")


def page_head(eyebrow: str, h1: str, lede: str, script: str = "") -> str:
    """The one header pattern, shared by every page.

    The mark sits in a fixed slot on a brass ring so it is always whole and
    always in the same place - never cropped by the viewport.
    """
    sc = f'<p class="script">{script}</p>' if script else ""
    return f"""<section class="page-head">
  <div class="wrap page-head__grid">
    <div class="page-head__text">
      <p class="label" style="color:var(--color-accent-brass)">{eyebrow}</p>
      <h1>{h1}</h1>{sc}
      <p class="lede">{lede}</p>
    </div>
    <div class="page-head__mark">
      <img src="{LOGO}" width="{LOGO_W}" height="{LOGO_H}"
           alt="{LOGO_ALT}" decoding="async" fetchpriority="high">
    </div>
  </div>
</section>"""


ORDER_BLOCK = f"""
<section class="section section--tight" aria-labelledby="order-h">
  <div class="wrap">
    <div class="cluster" style="margin-bottom:var(--space-sm)">
      <span class="ribbon">Order pickup</span>
      <span class="label" style="color:var(--color-ink-on-dark-muted)">Cash prices at the counter</span>
    </div>
    <h2 id="order-h">Order ahead</h2>
    <div class="order-grid mt-lg">
      <a class="order-card" href="{DD}"
         data-scheme="doordash://store/the-rustic-barrel-king-city-34689489/90022148"
         rel="nofollow noopener" target="_blank">
        <span class="order-card__mark"><img src="/assets/img/partner-doordash.png"
          width="231" height="132" alt="DoorDash" loading="lazy" decoding="async"></span>
        <span><span class="order-card__label">DoorDash</span>
        <span class="order-card__meta">Pickup &amp; to go</span></span>
        <span class="order-card__go" aria-hidden="true">&rarr;</span></a>
      <a class="order-card" href="{UE}"
         data-scheme="ubereats://store/browse?client_id=eats&amp;storeUUID={{STORE_UUID}}"
         rel="nofollow noopener" target="_blank">
        <span class="order-card__mark"><img src="/assets/img/partner-ubereats.svg"
          width="134" height="24" alt="Uber Eats" loading="lazy" decoding="async"></span>
        <span><span class="order-card__label">Uber Eats</span>
        <span class="order-card__meta">Pickup &amp; to go</span></span>
        <span class="order-card__go" aria-hidden="true">&rarr;</span></a>
    </div>
    <p class="visually-hidden" role="status" aria-live="polite" data-dl-status></p>
  </div>
</section>"""


def order_block() -> str:
    return ORDER_BLOCK


# --------------------------------------------------------------------------- #
# Menu page
# --------------------------------------------------------------------------- #
def page_menu() -> str:
    """Image-first.

    The Canva design IS the menu - laid out, priced and typeset by the client.
    Re-rendering it as text from the viewer's flattened accessibility dump
    collapsed every section into one list and orphaned prices onto their own
    rows. So: show the designed pages, and carry a verified text version
    underneath for search engines, screen readers and anyone who wants to copy
    a price.
    """
    data = json.loads((BRAND / "official_menu_verified.json").read_text(encoding="utf-8"))
    SITE_ASSETS = bl.RESEARCH.parent / "site" / "assets"

    pages = []
    for im in data["images"]:
        # copy the captured menu pages into the site tree
        src = bl.MEDIA / im["webp"]
        dest_dir = SITE_ASSETS / "menu-pages"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / Path(im["webp"]).name
        if src.exists():
            shutil.copy2(src, dest)
        srcpng = bl.MEDIA / im["png"]
        destpng = dest_dir / Path(im["png"]).name
        if srcpng.exists():
            shutil.copy2(srcpng, destpng)
        pages.append(f"""<figure class="menu-page">
      <picture>
        <source type="image/webp" srcset="/assets/menu-pages/{Path(im['webp']).name}">
        <img src="/assets/menu-pages/{Path(im['png']).name}"
             width="{im['width']}" height="{im['height']}"
             alt="{esc(im['alt'])}" loading="lazy" decoding="async">
      </picture>
    </figure>""")

    # --- verified text version ------------------------------------------- #
    blocks = []
    for sec in data["sections"]:
        rows = []
        for it in sec["items"]:
            desc = f'<p class="menu-item__desc">{esc(it["description"])}</p>' \
                if it["description"] else ""
            opt = f'<p class="menu-item__variants">{esc(it["options"])}</p>' \
                if it["options"] else ""
            rows.append(
                f'<div class="menu-item"><span class="menu-item__name">'
                f'{esc(it["name"])}</span>'
                f'<span class="menu-item__price">{esc(it["price"])}</span>'
                f'{desc}{opt}</div>')
        note = f'<p class="menu-note">{esc(sec["note"])}</p>' if sec.get("note") else ""
        blocks.append(
            f'<div class="menu-section"><h3>{esc(sec["name"])}</h3>{note}'
            f'<div class="menu-list mt-lg">{"".join(rows)}</div></div>')

    total = sum(len(s["items"]) for s in data["sections"])
    secs = ", ".join(s["name"] for s in data["sections"])

    ld = {
        "@context": "https://schema.org",
        "@type": "Menu",
        "name": "The Rustic Barrel Menu",
        "inLanguage": "en",
        "url": f"{BASE}/menu",
        "description": (f"Barrel bites, meat combos, rustic favorites, sandwiches, "
                        f"salads and sides. {total} items across {len(data['sections'])} "
                        f"sections: {secs}."),
        "hasMenuSection": [
            {"@type": "MenuSection", "name": s["name"],
             "hasMenuItem": [
                 {"@type": "MenuItem", "name": it["name"],
                  "description": it["description"] or None,
                  "offers": {"@type": "Offer", "price": it["price"].split("·")[0].strip()
                             .replace("$", ""), "priceCurrency": "USD"}}
                 for it in s["items"] if it["price"].startswith("$")
             ]}
            for s in data["sections"]
        ],
    }

    body = f"""
{page_head("Cash prices", "The Menu",
           "Smoked meats, smash burgers, loaded fries and cold sandwiches, built "
           "around Santa&nbsp;Maria style tri-tip and slow-smoked barbecue.")}
{order_block()}
<section class="section">
  <div class="wrap">
    {''.join(pages)}

    <details class="menu-text">
      <summary>Read the menu as text</summary>
      <div class="menu-text__body">
        <p class="cta-disclosure">
          Listed prices are cash prices. Card transactions include applicable
          processing fees.
        </p>
        {''.join(blocks)}
      </div>
    </details>
  </div>
</section>"""

    return shell(
        slug="menu.html",
        title="Menu | Smoked BBQ &amp; Smash Burgers | Rustic Barrel",
        desc="Santa Maria tri-tip, slow-smoked brisket and ribs, smash burgers, loaded fries and cold sandwiches. Cash prices shown.",
        active="/menu",
        body=body,
        jsonld=json.dumps(ld, indent=2),
        og_alt="The Rustic Barrel menu on aged parchment",
    )


def re_fix(s: str) -> str:
    import re
    s = re.sub(r"\s+", " ", s).strip()
    s = s.replace("complimented", "complemented")
    s = s.replace("Pepperoncini's", "pepperoncini")
    s = re.sub(r"\band\b", "n", s) if "mac" in s.lower() else s
    return s


# --------------------------------------------------------------------------- #
# Beer page
# --------------------------------------------------------------------------- #
def page_beer() -> str:
    d = json.loads((BRAND / "beer_list_parsed.json").read_text(encoding="utf-8"))
    beers = d["beers"]
    breweries = d["breweries"]
    abv = d["abv_range"]

    rows = "".join(
        f'<tr><td><strong>{esc(b["beer"])}</strong></td>'
        f'<td>{esc(b["style"])}</td>'
        f'<td class="abv">{b["abv"]}%</td>'
        f'<td>{esc(b["brewery"])}</td></tr>'
        for b in beers
    )
    brew_list = "".join(f"<li>{esc(n)} &mdash; {c} logged</li>" for n, c in breweries[:8])

    ld = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "Beers on tap at The Rustic Barrel Taphouse",
        "numberOfItems": len(beers),
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1,
             "item": {"@type": "Product", "name": b["beer"]}}
            for i, b in enumerate(beers)
        ],
    }

    body = f"""
{page_head("Multi-tap &middot; rotating", "What&rsquo;s on tap",
           f"The room runs on California craft &mdash; Russian&nbsp;River, "
           f"Firestone&nbsp;Walker, Alvarado&nbsp;Street, Altamont &mdash; alongside "
           f"house ciders from 2&nbsp;Towns. Between {abv[0]}% and {abv[1]}% ABV, "
           f"so you can stay all evening.")}
<section class="section">
  <div class="wrap">
    <h2>Recently logged</h2>
    <p class="lede mt-lg">
      Pulled from our <a href="https://untappd.com/v/the-rustic-barrel/13736755"
      rel="noopener">Untappd page</a>. This is what guests have actually poured,
      not a fixed sheet &mdash; taps rotate, and yesterday's list is the best
      hint of tomorrow's.
    </p>
    <div class="table-scroll mt-lg">
      <table class="beer-table">
        <caption class="visually-hidden">Beers recently logged at The Rustic Barrel Taphouse</caption>
        <thead><tr><th scope="col">Beer</th><th scope="col">Style</th>
        <th scope="col">ABV</th><th scope="col">Brewery</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>

    <div class="cards mt-xl">
      <div class="card">
        <h3>House ciders</h3>
        <p>Two&nbsp;Towns Ciderhouse keeps the non-beer option serious &mdash;
        the Bad Apple and the Pearadise both turn up on tap.</p>
      </div>
      <div class="card">
        <h3>Breweries we pour</h3>
        <ul class="stack-sm mt-lg" style="padding-left:var(--space-sm)">{brew_list}</ul>
      </div>
      <div class="card">
        <h3>Ordering a round</h3>
        <p>Call <a href="tel:+18316011397">(831) 601-1397</a> for a large round
        or a tray, or <a href="/#order">order ahead</a> for food alongside it.</p>
      </div>
    </div>
  </div>
</section>
{order_block()}"""

    return shell(
        slug="beer.html",
        title="Craft Beer &amp; Tap List | The Rustic Barrel, King City",
        desc="On tap at The Rustic Barrel in King City: California craft from Russian River, Firestone Walker and Alvarado Street, plus house ciders.",
        active="/beer",
        body=body,
        jsonld=json.dumps(ld, indent=2),
        og_alt="Rust and brass beer tap handles on a dark bar",
    )


# --------------------------------------------------------------------------- #
# Events page
# --------------------------------------------------------------------------- #
def page_events() -> str:
    body = f"""
{page_head("No cover &middot; all ages welcome", "Events &amp; big screens",
           "The bar is built around watching things together. Screens you can "
           "see from the back booth, a comedy night every other week, and "
           "enough taps to get through nine o&rsquo;sclock.")}
<section class="section">
  <div class="wrap">
    <div class="cards">
      <article class="card">
        <span class="ribbon">Monthly</span>
        <h3 class="mt-lg">Comedy nights</h3>
        <p>
          Live sets from touring comics, hosted with Laughing&nbsp;Booth Comedy.
          Free entry, first come for seats, bar open throughout. Doors around
          8pm.
        </p>
      </article>
      <article class="card">
        <span class="ribbon">Always</span>
        <h3 class="mt-lg">Watch parties</h3>
        <p>
          Baseball, football, basketball and the big fights. Multiple screens,
          sightlines from every booth. Come early for a seat; come late for the
          quiet.
        </p>
      </article>
      <article class="card">
        <span class="ribbon">Weekly</span>
        <h3 class="mt-lg">Thursday specials</h3>
        <p>
          The <a href="/menu">Chili Cheese Fries</a> special built a
          reputation. Rotating dish each week while it lasts.
        </p>
      </article>
    </div>

    <div class="rule rule--star" aria-hidden="true"><span>&#9733;</span></div>

    <h2 class="text-center">Private hire</h2>
    <div class="prose mt-lg" style="max-width:none">
      <p>
        We take birthdays, work crews and team things. The back room seats a
        crowd, the kitchen handles trays, and the taps pour whatever you ask
        for. Call <a href="tel:+18316011397">(831) 601-1397</a> and ask for the
        manager &mdash; it is the same number that reaches the bar.
      </p>
      <p>
        Large to-go orders are best placed by phone too, so we can have the
        meat off the smoker when you arrive.
      </p>
    </div>
  </div>
</section>"""

    ld = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": "Events at The Rustic Barrel Taphouse",
        "url": f"{BASE}/events",
        "isPartOf": {"@id": f"{BASE}/#website"},
        "about": {"@id": f"{BASE}/#restaurant"},
    }
    return shell(
        slug="events.html",
        title="Events &amp; Comedy Nights | The Rustic Barrel",
        desc="Comedy nights, watch parties and live events at The Rustic Barrel Taphouse in King City, California. Big screens, cold beer, no cover.",
        active="/events",
        body=body,
        jsonld=json.dumps(ld, indent=2),
        og_alt="Comedy night flyer on weathered blue wood at The Rustic Barrel",
    )


# --------------------------------------------------------------------------- #
# Visit page
# --------------------------------------------------------------------------- #
def page_visit() -> str:
    body = f"""
{page_head("611 Canal St", "Visit us",
           "King City, on the Salinas Valley floor between Salinas and Paso "
           "Robles. Free parking in the lot beside the building.")}
<section class="section">
  <div class="wrap">
    <div class="cards" style="align-items:start">
      <div class="card">
        <h2 style="font-size:var(--typography-display-s)">Hours</h2>
        <div class="hours-list mt-lg" data-today-row>
          <div class="hours-row" data-day="mon"><span>Monday</span><span>11:30am &ndash; 9:00pm</span></div>
          <div class="hours-row hours-row--closed" data-day="tue"><span>Tuesday</span><span>Closed</span></div>
          <div class="hours-row" data-day="wed"><span>Wednesday</span><span>11:30am &ndash; 9:00pm</span></div>
          <div class="hours-row" data-day="thu"><span>Thursday</span><span>11:30am &ndash; 9:00pm</span></div>
          <div class="hours-row" data-day="fri"><span>Friday</span><span>11:30am &ndash; 9:00pm</span></div>
          <div class="hours-row" data-day="sat"><span>Saturday</span><span>12:00pm &ndash; 9:00pm</span></div>
          <div class="hours-row" data-day="sun"><span>Sunday</span><span>12:00pm &ndash; 8:00pm</span></div>
        </div>
        <p class="mt-lg"><a href="tel:+18316011397">(831) 601-1397</a></p>
      </div>

      <div class="card">
        <h2 style="font-size:var(--typography-display-s)">Find us</h2>
        <address class="mt-lg" style="font-style:normal;color:var(--color-ink-on-dark-muted)">
          <strong style="color:var(--color-primary-bone)">The Rustic Barrel Taphouse</strong><br>
          611 Canal St<br>King City, CA 93930
        </address>
        <p class="mt-lg">
          <a href="https://www.google.com/maps/search/?api=1&amp;query=The+Rustic+Barrel,+611+Canal+St,+King+City,+CA+93930"
             rel="noopener">Open in Google Maps &rarr;</a>
        </p>
        <p class="mt-lg">
          <a href="mailto:therusticbarrel831@gmail.com">therusticbarrel831@gmail.com</a>
        </p>
      </div>

      <div class="card">
        <h2 style="font-size:var(--typography-display-s)">Before you come</h2>
        <ul class="stack-sm mt-lg" style="padding-left:var(--space-sm);color:var(--color-ink-on-dark-muted)">
          <li><strong style="color:var(--color-primary-bone)">Closed Tuesdays.</strong> The one exception people trip on.</li>
          <li><strong style="color:var(--color-primary-bone)">Listed prices are cash.</strong> Card adds a processing fee.</li>
          <li>Come early for a screen seat on a game night.</li>
          <li>Big-screen TVs; a bit of noise is the point.</li>
          <li>Kids welcome &mdash; there is a Connect Four.</li>
        </ul>
      </div>
    </div>

    <div class="rule rule--star" aria-hidden="true"><span>&#9733;</span></div>

    <h2 class="text-center">Getting the most out of a visit</h2>

    <div class="prose mt-lg">
      <p>
        Start with the <a href="/menu">Santa&nbsp;Maria tri-tip sandwich</a>
        &mdash; it is the dish the room is known for. Then check the
        <a href="/beer">tap list</a> for something Central Coast-adjacent,
        because most of what we pour comes from within a few hours' drive.
      </p>
      <p>
        If you are hungry and in a hurry, <a href="/#order">order ahead</a> and
        walk in to collect. If you are here to watch something,
        <a href="/events">check what's on</a>.
      </p>
    </div>
  </div>
</section>"""

    ld = {
        "@context": "https://schema.org",
        "@type": "LocalBusiness",
        "@id": f"{BASE}/visit#business",
        "name": "The Rustic Barrel Taphouse",
        "url": f"{BASE}/visit",
        "telephone": "+1-831-601-1397",
        "priceRange": "$$",
        "address": {
            "@type": "PostalAddress", "streetAddress": "611 Canal St",
            "addressLocality": "King City", "addressRegion": "CA",
            "postalCode": "93930", "addressCountry": "US"},
        "geo": {"@type": "GeoCoordinates",
                "latitude": 36.202538, "longitude": -121.12799},
    }
    return shell(
        slug="visit.html",
        title="Visit Us | 611 Canal St, King City, CA | The Rustic Barrel",
        desc="Find The Rustic Barrel at 611 Canal St, King City, CA. Open Mon and Wed-Fri 11:30am-9pm, Sat 12-9pm, Sun 12-8pm. Closed Tuesdays.",
        active="/visit",
        body=body,
        jsonld=json.dumps(ld, indent=2),
        og_alt="Interior of The Rustic Barrel with a multi-tap bar and big screens",
    )


# --------------------------------------------------------------------------- #
def main() -> None:
    SITE.mkdir(parents=True, exist_ok=True)
    for name, fn in (("menu.html", page_menu), ("beer.html", page_beer),
                     ("events.html", page_events), ("visit.html", page_visit)):
        out = fn()
        (SITE / name).write_text(out, encoding="utf-8")
        size = len(out.encode("utf-8")) / 1024
        h1 = out.count("<h1")
        title = out.split("<title>")[1].split("</title>")[0]
        desc = out.split('name="description" content="')[1].split('"')[0]
        print(f"  {name:<14} {size:>6.1f} KB  h1={h1}  "
              f"title={len(title):>3}ch  desc={len(desc):>3}ch")

    # 404
    (SITE / "404.html").write_text(shell(
        slug="404.html",
        title="Page not found | The Rustic Barrel Taphouse",
        desc="That page is not here. Head back to the menu, the tap list, or just call us.",
        active="",
        body="""
<section class="section"><div class="wrap text-center">
  <p class="display-xl">404</p>
  <h1 style="font-size:var(--typography-display-m)">That round isn't on the board</h1>
  <p class="lede" style="margin-inline:auto;margin-block:var(--space-sm) var(--space-md)">
    The page you're after doesn't exist. Try the menu, the tap list, or just
    call the bar &mdash; someone will be there.
  </p>
  <div class="cluster" style="justify-content:center">
    <a class="btn btn--primary" href="/">Home</a>
    <a class="btn btn--ghost" href="/menu">Menu</a>
    <a class="btn btn--ghost" href="tel:+18316011397">Call the bar</a>
  </div>
</div></section>""",
    ), encoding="utf-8")
    print(f"  {'404.html':<14} built")


if __name__ == "__main__":
    main()
