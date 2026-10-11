"""
Site build - static generator.

Turns site/assets/tokens.json into CSS custom properties, produces responsive
WebP imagery from the scraped brand library, and emits robots.txt + sitemap.xml.

Deliberately no framework and no runtime dependency: the output is plain HTML,
one CSS file and ~2 KB of vanilla JS. That is the fastest thing we can ship,
which is the point - Core Web Vitals are won here, not fought for later.

Usage:  .venv\\Scripts\\python.exe scripts\\build_site.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image

import brandlib as bl

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
ASSETS = SITE / "assets"
IMG_OUT = ASSETS / "img"

# Pages, in sitemap priority order. src/rel are relative to site/.
PAGES = [
    {"file": "index.html",  "priority": "1.0", "changefreq": "weekly",
     "url": "/",              "title": "The Rustic Barrel Taphouse | Craft Beer, BBQ & Sports Bar in King City, CA",
     "desc": "King City's taphouse on Canal St. Multi-tap California craft beer, Santa Maria style tri-tip and slow-smoked barbecue, and big-screen sports. Order pickup on DoorDash or Uber Eats."},
    {"file": "menu.html",    "priority": "0.9", "changefreq": "weekly",
     "url": "/menu.html",    "title": "Menu | Smoked BBQ, Smash Burgers & Sandwiches | The Rustic Barrel",
     "desc": "The full Rustic Barrel menu: Santa Maria style tri-tip, slow-smoked brisket and pork ribs, smash burgers, loaded fries and cold sandwiches. Cash prices shown."},
    {"file": "beer.html",    "priority": "0.9", "changefreq": "weekly",
     "url": "/beer.html",    "title": "Craft Beer & Tap List | Russian River, Firestone Walker | The Rustic Barrel",
     "desc": "What is on tap at The Rustic Barrel in King City: California craft from Russian River, Firestone Walker, Alvarado Street and more, plus house ciders."},
    {"file": "events.html",  "priority": "0.7", "changefreq": "weekly",
     "url": "/events.html",  "title": "Events & Comedy Nights | The Rustic Barrel Taphouse, King City",
     "desc": "Comedy nights, watch parties and live events at The Rustic Barrel Taphouse in King City, California. Big screens, cold beer, no cover."},
    {"file": "visit.html",   "priority": "0.6", "changefreq": "monthly",
     "url": "/visit.html",   "title": "Visit Us | 611 Canal St, King City, CA | The Rustic Barrel",
     "desc": "Find The Rustic Barrel at 611 Canal St, King City, CA. Open Mon and Wed-Fri 11:30am-9pm, Sat 12-9pm, Sun 12-8pm. Closed Tuesdays. (831) 601-1397."},
]

BRAND_SRC = ROOT / "research" / "media" / "brand_marks"

# Hero / gallery imagery: (source filename stem, output basename, alt text)
GALLERY = [
    ("brand-private-event-hours-notice", "hero-hours", "Rustic Barrel barrel-head badge logo with the hours-change notice"),
    ("brand-chili-cheese-fry-special", "chili-cheese-fries", "Chili cheese fries with shredded cheddar, red onion and chili, on a wood backdrop"),
    ("brand-labor-day-closure-notice", "labor-day", "Labor Day closure notice on a weathered wood background with stars and stripes"),
    ("brand-hours-change-notice-parchment", "private-event", "Private event notice printed on aged parchment with the Rustic Barrel Taphouse badge"),
]


def load_tokens() -> dict:
    return json.loads((ASSETS / "tokens.json").read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# tokens.json -> CSS custom properties
# --------------------------------------------------------------------------- #
def to_css(tk: dict) -> str:
    out: list[str] = []
    used: set[str] = set()

    def emit(prefix: str, group) -> None:
        if not isinstance(group, dict):
            return
        for k, v in group.items():
            if k.startswith("$"):
                continue
            if isinstance(v, dict) and "$value" in v:
                # join every path segment with a hyphen: color + primary + bone
                # -> --color-primary-bone
                name = "--" + "-".join([prefix, k] if prefix else [k])
                used.add(k)
                out.append(f"  {name}: {v['$value']};")
            elif isinstance(v, dict):
                emit(f"{prefix}-{k}" if prefix else k, v)

    for section in ("color", "typography", "space", "radius", "border",
                    "shadow", "motion", "breakpoint", "layout"):
        emit(section, tk.get(section, {}))

    # asset + content values that the site actually reads
    c = tk.get("content", {})
    b = c.get("business", {})
    out.append(f"  --brand-phone: '{b.get('phoneDisplay', '')}';")
    out.append(f"  --brand-phone-href: '{b.get('phone', '')}';")
    out.append(f"  --brand-email: '{b.get('email', '')}';")
    out.append(f"  --brand-address: '{b.get('address', {}).get('full', '')}';")
    out.append(f"  --brand-geo: '{b.get('geo', {}).get('lat')},{b.get('geo', {}).get('lng')}';")

    return "\n".join(out)


# --------------------------------------------------------------------------- #
# Imagery
# --------------------------------------------------------------------------- #
def build_images() -> dict:
    IMG_OUT.mkdir(parents=True, exist_ok=True)
    made: dict[str, list[str]] = {}
    widths = (640, 1280, 1920)

    for stem, name, alt in GALLERY:
        src = None
        for ext in (".jpg", ".png", ".jpeg", ".webp"):
            cand = BRAND_SRC / f"{stem}{ext}"
            if cand.exists():
                src = cand
                break
        if not src:
            print(f"  ! missing source for {stem}")
            continue

        variants = []
        with Image.open(src) as im:
            im = im.convert("RGB")
            base_w = im.width
            for w in widths:
                if w > base_w * 1.15:
                    continue
                h = round(im.height * (w / base_w))
                out = IMG_OUT / f"{name}-{w}.webp"
                im.resize((w, h), Image.LANCZOS).save(
                    out, "WEBP", quality=82, method=6)
                variants.append(out.name)

            # LCP hero wants a sharp JPEG fallback for older Safari
            fb = IMG_OUT / f"{name}-1280.jpg"
            im.resize((1280, round(im.height * (1280 / base_w))),
                      Image.LANCZOS).save(fb, "JPEG", quality=80, optimize=True,
                                          progressive=True)
            made[name] = variants
            print(f"  {name:<22} {len(variants)} webp + jpg fallback  alt=\"{alt[:40]}\"")

    # Default Open Graph card
    og = IMG_OUT / "og-default.jpg"
    with Image.open(IMG_OUT / (made["hero-hours"][0])) as im:
        card = Image.new("RGB", (1200, 630), "#1F1610")
        ratio = min(1200 / im.width, 630 / im.height)
        card.paste(im.resize((round(im.width * ratio),
                              round(im.height * ratio)), Image.LANCZOS),
                   ((1200 - round(im.width * ratio)) // 2,
                    (630 - round(im.height * ratio)) // 2))
        card.save(og, "JPEG", quality=82, optimize=True)
    made["og-default"] = ["og-default.jpg"]
    print(f"  og-default.jpg         1200x630")

    (SITE / "assets" / "images.json").write_text(
        json.dumps(made, indent=2), encoding="utf-8")
    return made


# --------------------------------------------------------------------------- #
# SEO files
# --------------------------------------------------------------------------- #
def build_seo(tk: dict, imgs: dict) -> None:
    seo = tk["seo"]
    base = seo["canonicalBase"].rstrip("/")
    today = "2026-10-11"

    # ---- sitemap.xml ------------------------------------------------------ #
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for p in PAGES:
        # "/" must not produce a double slash in the sitemap
        loc = f"{base}/" if p["url"] == "/" else f"{base}{p['url']}"
        sm += ["  <url>",
               f"    <loc>{loc}</loc>",
               f"    <lastmod>{today}</lastmod>",
               f"    <changefreq>{p['changefreq']}</changefreq>",
               f"    <priority>{p['priority']}</priority>",
               "  </url>"]
    sm.append("</urlset>")
    (SITE / "sitemap.xml").write_text("\n".join(sm), encoding="utf-8")

    # ---- robots.txt ------------------------------------------------------- #
    rb = [
        "# robots.txt - The Rustic Barrel Taphouse",
        f"# Canonical host: {base}",
        "#",
        "# IMPORTANT: every public page is crawlable and indexable.",
        "# There are NO Disallow rules against content pages, and no noindex",
        "# anywhere in the markup. Only build artefacts and the offline",
        "# reference/audit directories are excluded.",
        "",
        "User-agent: *",
        "Allow: /",
        "",
        "# Build artefacts - not content, no search value",
        "Disallow: /assets/tokens.json",
        "Disallow: /assets/images.json",
        "Disallow: /*.map$",
        "Disallow: /404.html",
        "",
        "# Google explicitly requires these to be reachable",
        "Allow: /.well-known/",
        "Allow: /sitemap.xml",
        "",
        "# Allow the major crawlers explicitly, so a future blanket Disallow",
        "# can never silently deindex the site.",
        "User-agent: Googlebot",
        "Allow: /",
        "",
        "User-agent: Googlebot-Image",
        "Allow: /",
        "",
        "User-agent: Bingbot",
        "Allow: /",
        "",
        "User-agent: Applebot",
        "Allow: /",
        "",
        "# AI/search crawlers are welcome too - this is a public business",
        "User-agent: Google-Extended",
        "Allow: /",
        "",
        f"Sitemap: {base}/sitemap.xml",
        "",
    ]
    (SITE / "robots.txt").write_text("\n".join(rb), encoding="utf-8")

    # ---- manifest --------------------------------------------------------- #
    mf = json.dumps({
        "name": tk["content"]["business"]["name"],
        "short_name": tk["content"]["business"]["shortName"],
        "start_url": "/",
        "display": "standalone",
        "background_color": "#1F1610",
        "theme_color": "#1F1610",
        "icons": [
            {"src": "/assets/img/logo-icon-192.png", "sizes": "192x192",
             "type": "image/png"},
            {"src": "/assets/img/logo-icon-512.png", "sizes": "512x512",
             "type": "image/png"},
        ],
    }, indent=2)
    (SITE / "site.webmanifest").write_text(mf, encoding="utf-8")

    print(f"  sitemap.xml   {len(PAGES)} urls")
    print(f"  robots.txt    allow-all public pages, sitemap referenced")
    print(f"  webmanifest")


# --------------------------------------------------------------------------- #
# Host config - canonical host + redirect
# --------------------------------------------------------------------------- #
def build_host_config() -> None:
    """Netlify: force www/non-www to ONE version with a 301, force HTTPS."""
    netlify = """# _redirects - host canonicalisation and permanent HTTPS
# Exactly ONE of these two www lines must be uncommented.
# PRIMARY VERSION: www  (set here, and canonicalBase must match)
www.therusticbarrel.com/*   https://www.therusticbarrel.com/:splat  301!  force_https=true
therusticbarrel.com/*       https://www.therusticbarrel.com/:splat  301!

# Legacy/typo protection - the parked domain must never be an index duplicate
www.rusticbarrel.com/*      https://www.therusticbarrel.com/:splat  301!
"""
    (SITE / "_redirects").write_text(netlify, encoding="utf-8")

    vercel = {
        "redirects": [
            {"source": "/therusticbarrel.com/:path*",
             "destination": "https://www.therusticbarrel.com/:path*",
             "permanent": True},
        ]
    }
    (SITE / "vercel.json").write_text(json.dumps(vercel, indent=2), encoding="utf-8")
    print("  _redirects    canonical host 301 + force HTTPS")
    print("  vercel.json")


def main() -> None:
    print("BUILD - The Rustic Barrel")
    print("=" * 58)
    tk = load_tokens()

    print("\n[css]")
    css = to_css(tk)
    (ASSETS / "tokens.css").write_text(
        f"/* GENERATED FROM tokens.json - do not edit by hand.\n"
        f"   Regenerate with: .venv\\Scripts\\python.exe scripts\\build_site.py */\n"
        f":root {{\n{css}\n}}\n", encoding="utf-8")
    print(f"  tokens.css    {len(css.splitlines())} custom properties")

    print("\n[images]")
    imgs = build_images()

    print("\n[seo]")
    build_seo(tk, imgs)

    print("\n[host]")
    build_host_config()

    print("\n" + "=" * 58)
    print("build complete")


if __name__ == "__main__":
    main()
