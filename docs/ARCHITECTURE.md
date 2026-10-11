# System Architecture — The Rustic Barrel Taphouse Website

**Version:** 1.0 · **Date:** 11 Oct 2026

---

## 1. Shape of the system

Two planes that never touch at runtime.

```
╔═══════════════════════════════════════════════════════════════════════╗
║  BUILD TIME  (Python · runs on the agency's machine)                   ║
║                                                                       ║
║   ┌──────────┐   ┌──────────┐   ┌───────────┐   ┌─────────────────┐  ║
║   │  CRAWL   │──▶│  CURATE  │──▶│  ANALYSE  │──▶│     TOKENS      │  ║
║   │ scrapling│   │ dedupe + │   │ palette + │   │ hand-authored   │  ║
║   │ stealth  │   │ classify │   │ typography│   │ from evidence   │  ║
║   └────┬─────┘   └──────────┘   └───────────┘   └────────┬────────┘  ║
║        │                                               │           ║
║        ▼                                               ▼           ║
║   research/media/                          ┌──────────────────────┐  ║
║   research/brand/*.json                    │  BUILD  (Python)     │  ║
║                                            │  logo → tokens.css   │  ║
║                                            │  → images → pages    │  ║
║                                            │  → sitemap/robots    │  ║
║                                            └──────────┬───────────┘  ║
║                                            ┌──────────▼───────────┐  ║
║                                            │  VALIDATE (gate)     │  ║
║                                            │  12 checks · exit≠0  │  ║
║                                            │  = do not deploy     │  ║
║                                            └──────────┬───────────┘  ║
╚════════════════════════════════│╤══════════════════╤════════════════╝
                                 │                  │
                                 ▼                  ▼
                        ┌────────────────────────────────────┐
                        │   site/   (static output)           │
                        │   HTML · CSS · 4.7KB JS · WebP     │
                        └──────────────────┬─────────────────┘
                                           │  git push / drag-drop
                                           ▼
╔══════════════════════════════════════╤═══════════════════════════════╗
║  RUNTIME  (edge, globally distributed)                                ║
║                                       │                               ║
║                         ┌─────────────▼──────────────┐                ║
║                         │  CDN EDGE  (Netlify / CF)  │                ║
║                         │  · TLS termination         │                ║
║                         │  · force_https             │                ║
║                         │  · www 301 canonical       │                ║
║                         │  · immutable cache headers │                ║
║                         └─────────────┬──────────────┘                ║
║                                       │                               ║
║                     ┌─────────────────┼─────────────────┐             ║
║                     ▼                 ▼                 ▼             ║
║              ┌────────────┐    ┌────────────┐    ┌────────────┐        ║
║              │  Crawler   │    │   Human    │    │  Delivery  │        ║
║              │  (Google)  │    │  visitor   │    │    apps    │        ║
║              └─────┬──────┘    └─────┬──────┘    └─────┬──────┘        ║
║                    │                │                 │               ║
║                    ▼                ▼                 ▼               ║
║              indexable        reads page,      App Link /             ║
║              HTML, JSON-LD    taps Order CTA   Universal Link        ║
║                                                  ▼                   ║
║                                          ┌──────────────┐            ║
║                                          │  DoorDash    │            ║
║                                          │  Uber Eats   │            ║
║                                          └──────────────┘            ║
╚═══════════════════════════════════════════════════════════════════════╝
```

**The defining property:** there is no server. No API, no database, no runtime
that can 500, no patch cycle, no origin to be down. The "backend" is a folder of
files and a validation gate that refuses to let a broken build ship.

---

## 2. Component map

```
site/
├── index.html            Hero, order CTA, value props, proof, hours
├── menu.html             GENERATED · 32 dishes from official_menu.json
├── beer.html             GENERATED · 17 beers from beer_list_parsed.json
├── events.html           Comedy, watch parties, private hire
├── visit.html            Address, hours, "before you come"
├── 404.html              Recovery routes, no dead end
├── robots.txt            GENERATED · allow-all public pages
├── sitemap.xml           GENERATED · 5 URLs
├── site.webmanifest      PWA metadata
├── _redirects            Netlify canonical-host 301 + force_https
├── vercel.json           Drop-in alternative host config
└── assets/
    ├── tokens.json       ★ SINGLE SOURCE OF TRUTH (design system)
    ├── tokens.css        GENERATED · 79 custom properties
    ├── css/site.css      Handwritten component layer
    ├── js/deeplink.js    Deep-link enhancement, ~2 KB, no deps
    └── img/
        ├── logo-badge.svg    DRAFT reconstruction
        ├── logo-icon.svg     DRAFT reconstruction
        ├── logo-wordmark.svg DRAFT reconstruction
        ├── logo-icon-{192,512}.png
        ├── hero-*.webp/.jpg  GENERATED responsive
        └── og-default.jpg    GENERATED 1200×630
```

---

## 3. Layer responsibilities

| Layer | Owns | Never touches |
|---|---|---|
| **tokens.json** | Colour, type, space, radius, border, shadow, motion, layout, content facts, SEO config | Markup, build logic |
| **tokens.css** | Flattened custom properties | Any hand-authored style |
| **site.css** | Layout, components, responsive, a11y, print | Colour values *(always via `var()`)* |
| **deeplink.js** | App hand-off + fallback only | Content, layout, routing |
| **build_pages.py** | Page markup from data | Design values *(emits `var()` refs)* |
| **validate_seo.py** | The deploy gate | — |

**The one-way dependency** (`site.css` → `tokens.css` → `tokens.json`) is what
makes a palette change a one-line JSON edit rather than a find-and-replace
across every stylesheet.

---

## 4. Data flow — a price change

```
1.  Owner phones: "tri-tip sandwich is $24 now"
2.  Update tokens.json → content, or re-crawl the Canva menu
3.  python scripts/build_pages.py
       └─▶ reads official_menu.json
       └─▶ regenerates menu.html with $24
4.  python scripts/validate_seo.py
       └─▶ title/desc/h1/links assertions
       └─▶ exit 0
5.  Deploy. menu.html changes. Nothing else does.
```

No template to open, no CMS login, no chance of touching the production site
with a broken edit. The crawl output stays the source of truth.

---

## 5. Request lifecycle — one page view

```
Customer taps "ORDER"
        │
        ▼
┌─────────────────────────────────────────┐
│ href is ALWAYS https://…/store/…        │  ← no JS required
└────────────────────┬────────────────────┘
                     ▼
              OS App Link check
        ┌────────────┴────────────┐
        │ app installed?          │
        ├── yes ──▶ app opens,    │
        │          correct store  │
        └── no  ──▶ browser opens, │
                   store page      │
                     │              │
                     ▼              │
        deeplink.js (enhancement)   │
                     │              │
        ┌────────────┴───────────┐  │
        │ in-app webview?        │  │
        ├── yes ──▶ skip scheme  │  │
        │          (web link)    │  │
        └── no ──▶ optional:     │  │
                   custom scheme │  │
                     │          │  │
                     ▼          │  │
          {STORE_UUID} set?     │  │
          ├── no ─▶ announce,   │  │
          │        use web link │  │
          └── yes ─▶ fire scheme│  │
                     │          │  │
                     ▼          │  │
        ┌───────────────────────┴──┐│
        │ 1400ms visibilitychange  ││
        │ app took over?          ││
        ├── yes ─▶ done (native)   ││
        └── no  ─▶ web store URL   ││
        └──────────────────────────┘│
                     │              │
                     ▼              ▼
              Customer is ordering.
```

**Every branch terminates in a working store page.** There is no path where the
user sees a blank screen.

---

## 6. Trust boundaries

| Boundary | Controls |
|---|---|
| Internet → edge | TLS 1.3, `force_https`, HSTS recommended |
| Edge → filesystem | Read-only; no origin process |
| Browser → third party | **Only** `fonts.googleapis.com` / `fonts.gstatic.com`. No analytics, no pixels, no CDN-hosted JS. |
| Browser → delivery platforms | `nofollow noopener`, `target=_blank` |
| Build → deploy | `validate_seo.py` must exit 0 |

The single-external-resource policy is deliberate: for a business whose entire
current problem is that its identity lives on other people's servers, shipping a
site with third-party trackers would be self-parody.

---

## 7. Scaling envelope

| Dimension | Capacity | Headroom |
|---|---|---|
| Concurrent visitors | ~100k/s (static CDN) | Effectively unlimited |
| Origin load | Zero after first request | — |
| Build time | < 2 s for 5 pages | ~500 pages |
| Content pages | 5 today | Hundreds, same pipeline |
| Monthly cost | $0 (Netlify/Cloudflare free tier) | — |

**This architecture has no scaling trigger.** That is the point of choosing it.

---

## 8. Failure modes

| Failure | Behaviour | Detection |
|---|---|---|
| Host down | 5xx from edge | External uptime monitor |
| Bad deploy | Validator blocks it pre-push | `validate_seo.py` exit code |
| Domain lapses | NXDOMAIN | Uptime monitor + registrar auto-renew |
| Delivery platform changes their URL | CTA breaks | Quarterly manual click-test |
| Menu goes stale | Wrong prices published | Re-crawl cadence (plan §4) |
| Yelp rating changes | `aggregateRating` stale | Quarterly re-run of `parse_yelp.py` |
| Uber rotates store token | CTA 404s at destination | Quarterly manual click-test |

Six of the seven are **content staleness**, not infrastructure. Infrastructure
on a static host is the easy part.
