# TRD — The Rustic Barrel Taphouse Website

**Version:** 1.0 · **Date:** 11 Oct 2026
Companion to `PRD.md`. This document specifies *how it is built* and *why each
choice was made*, with the alternatives that were rejected.

---

## 1. Stack decisions

### 1.1 Static HTML, no framework — **chosen**

| Option | Verdict |
|---|---|
| **Static HTML + CSS + 2 KB vanilla JS** | ✅ **Chosen** |
| Astro / Eleventy / Hugo | ❌ Build tooling for a 5-page site |
| Next.js / Nuxt | ❌ A runtime and a client bundle for content that never changes |
| WordPress | ❌ Plugin surface, update burden, and a hosting bill for a bar |
| Squarespace / Wix | ❌ Template look; the whole point is a *distinctive* identity |

**Why.** The content is five pages that change monthly. The performance budget is
the competitive advantage. A framework would add 40–90 KB of JavaScript, a
runtime to keep patched, and a build step to keep green — in exchange for
routing and templating we do not need.

The measured result: **~18 KB HTML, ~20 KB CSS, ~4.7 KB JS** per page, zero
third-party JavaScript, no cookie banner required.

### 1.2 Python build pipeline, not Node

The content is already in Python (`menu.json`, `beer_list_parsed.json`,
`tokens.json`) because the crawl pipeline is Python. Generating pages from Python
means **one language across crawl → curate → tokens → pages**, and the menu page
regenerates from scraped source with no data re-entry.

Build cost: **< 2 seconds.** The tooling already exists.

### 1.3 Hosting: Netlify (or Cloudflare Pages) — static tier

Free at this scale, global edge, automatic HTTPS, and `_redirects` support for
the canonical-host 301. `vercel.json` is shipped as a drop-in alternative.

**Not** a VPS, and **not** Cloudflare Workers — no server code exists to run.

### 1.4 Fonts: Google Fonts, four families, one request

Rye (display), Bevan (subhead), Kaushan Script (accent), Barlow (body) — a single
combined request with `display=swap`, preconnected.

Rejected: self-hosting (adds a build step for no gain at this scale) and system
fonts (Barlow is doing real work — it is the face the brand currently lacks
entirely, per §5 of the guidelines).

### 1.5 Images: WebP + JPEG fallback, generated at build

Pillow resizes the scraped flyers to 640/1280/1920 WebP (q82) plus a progressive
JPEG fallback for older Safari. Every `<img>` carries explicit `width`/`height`
to eliminate CLS.

The LCP hero is `<picture>` + `fetchpriority="high"`; everything else is
`loading="lazy"`.

---

## 2. Deep-link CTA — technical specification

### 2.1 Link resolution matrix

| Context | OS behaviour of a plain HTTPS store URL | Result |
|---|---|---|
| Android 12+, app installed | App Link verified via `assetlinks.json` on doordash.com | Opens app, correct store ✅ |
| iOS, app installed | Universal Link via AASA | Opens app, correct store ✅ |
| App not installed | No handler claims the link | Opens browser ✅ |
| Desktop | No handler | Opens browser ✅ |
| Instagram/Facebook in-app browser | **App switching blocked by the webview** | Opens in-app browser; must be handled |
| Search result / email | App Link | Opens app ✅ |

### 2.2 Implementation contract

**Rule 1 — the `href` is always the HTTPS store URL.** Never the scheme. This is
what makes the CTA work with JS off, in email, and for crawlers.

**Rule 2 — the scheme lives in `data-scheme`, never in `href`.** A custom scheme
in `href` renders as a broken link when the app is missing.

**Rule 3 — enhancement only, never replacement.** `deeplink.js` adds an
attribute; it never rewrites `href`.

**Rule 4 — never attempt a scheme on desktop.** Detect via
`(hover: hover) and (pointer: fine)` and `innerWidth >= 1024`.

**Rule 5 — never attempt a scheme inside an in-app webview.** Detect via UA.
Attempting strands the user on a dead screen.

**Rule 6 — fire schemes only from a user gesture.** iOS blocks programmatic
`location.href = scheme` outside a click handler.

**Rule 7 — the fallback timeout must confirm the app did not take over.** Use
`visibilitychange` → `document.hidden`. If still visible after 1.4 s, the app is
not installed → route to the web URL. A naive timer fires even on a successful
hand-off on slow devices.

### 2.3 Config surface

All of it lives in `tokens.json` → `content.delivery.providers[]`:

```json
{
  "id": "ubereats",
  "web": "https://www.ubereats.com/store/the-rustic-barrel/j50H6Tr2W-qha1Ep9ys4Ag",
  "scheme": "ubereats://store/browse?client_id=eats&storeUUID={STORE_UUID}",
  "storeUUID": null
}
```

`deeplink.js` detects the literal `{STORE_UUID}` placeholder and **declines the
attempt with a live-region announcement** rather than firing a malformed URI.
Swapping in the real UUID is a one-line JSON edit — no code change.

### 2.4 Accessibility

The CTA is an `<a>` with visible text; the arrow is `aria-hidden`. Status
changes go to a `role="status" aria-live="polite"` region. Tap targets are
≥48px (WCAG 2.5.5). Focus rings are never removed.

---

## 3. SEO technical specification

### 3.1 Canonical host

`www.therusticbarrel.com` is primary. `therusticbarrel.com` → 301.

Both host configs ship so the rule survives a host change:

```
# _redirects (Netlify)
www.therusticbarrel.com/*   https://www.therusticbarrel.com/:splat  301!  force_https=true
therusticbarrel.com/*       https://www.therusticbarrel.com/:splat  301!
```

`tokens.json → seo.canonicalBase` is the **single** source for every canonical,
og:url and sitemap `<loc>`. Hand-editing a page canonical is a bug; the validator
catches drift.

### 3.2 robots.txt

```
User-agent: *
Allow: /
Disallow: /assets/tokens.json
Disallow: /assets/images.json
Disallow: /*.map$
Disallow: /404.html
Allow: /.well-known/
Allow: /sitemap.xml
Sitemap: https://www.therusticbarrel.com/sitemap.xml
```

Design notes:
- **No blanket `Disallow: /`.** This is the single most common self-inflicted
  deindexing error. The validator explicitly greps for it.
- Named agents (`Googlebot`, `Googlebot-Image`, `Bingbot`, `Applebot`,
  `Google-Extended`) each get an explicit `Allow: /` so a future blanket rule
  cannot silently strip them.
- Build artefacts are excluded by path, not by wildcarding the whole site.
- `/.well-known/` is allowed because `assetlinks.json` must be reachable.

### 3.3 sitemap.xml

Five URLs, `lastmod`, `changefreq`, `priority`. `404.html` deliberately excluded.
The validator asserts **every** indexable page appears — sitemap drift is a build
failure, not a monthly chore.

### 3.4 Per-page metadata

| Element | Rule | Enforced |
|---|---|---|
| `<title>` | unique, ≤60 chars | ✅ `validate_seo.py` |
| meta description | unique, 70–155 chars | ✅ |
| `<link rel=canonical>` | absolute, https, self | ✅ |
| `<meta name=robots>` | `index, follow, max-image-preview:large` | ✅ (noindex = fail) |
| `<h1>` | exactly one per page | ✅ |
| `og:*` / `twitter:*` | absolute https image, 1200×630 | ✅ |
| internal links | every `href="/..."` resolves on disk | ✅ |
| images | `alt` present, `width`+`height` present | ✅ |
| JSON-LD | parses, carries `@type` | ✅ |

### 3.5 Structured data

| Page | Schema |
|---|---|
| Home | `Restaurant` + `WebSite` in an `@graph`, incl. `aggregateRating` 4.6/59, full `openingHoursSpecification` (Tuesday absent = closed), `geo`, `hasMenu`, and **`OrderAction` with two `EntryPoint`s** |
| Menu | `Menu` with `hasMenuSection` |
| Beer | `ItemList` of `Product` |
| Events | `WebPage` |
| Visit | `LocalBusiness` |

`aggregateRating` is included because the value (4.6) and count (59) are exact
and sourced from Yelp's own JSON-LD. **If Yelp reviews are ever filtered or the
rating is self-inflated, this becomes a structured-data violation — re-verify
quarterly.**

### 3.6 Core Web Vitals strategy

| Metric | Technique |
|---|---|
| **LCP** | hero `<picture>` WebP, `fetchpriority="high"`, no blocking JS, fonts `swap` + `preconnect`, image `brightness(.48)` filter so the dark scrim stays cheap |
| **CLS** | every media has explicit dimensions; no injected banners; fonts swap into a metric-similar fallback stack |
| **INP** | 4.7 KB of JS that only touches attributes; no layout thrash, no long tasks |
| **TTFB** | static edge cache — effectively 0 at the origin |

### 3.7 The build gate

`validate_seo.py` exits non-zero on any hard failure. **The site cannot be
deployed from a build that fails.** This converts "we checked SEO" from a claim
into a fact.

Current state: **8 passed, 0 warnings, 0 failures.**

---

## 4. Design token system

### 4.1 Format

`tokens.json` follows the W3C Design Tokens Community Group shape (`$value`,
`$type`, `$description`). Values carry provenance — e.g. Charred Oak is annotated
*"33–56% of every designed flyer"*, Brass is annotated as an addition derived
from reference analysis. **The reasoning travels with the token.**

### 4.2 Generation

`build_site.py` flattens tokens → `tokens.css` custom properties. The flattening
had a real bug worth recording:

```python
# WRONG - produced --colorprimary-bone
name = f"--{prefix}{prefix and '-'}{k}"
emit(f"{prefix}{k}", v)

# RIGHT - produces --color-primary-bone
name = "--" + "-".join([prefix, k] if prefix else [k])
emit(f"{prefix}-{k}" if prefix else k, v)
```

The symptom was silent and total: every `var(--color-*)` fell back to
`initial`, so **all text rendered black on black** while the page still passed
HTTP and markup checks. Caught by measuring computed contrast in a real browser
rather than reading the CSS.

**Lesson: validate rendered output, not source.**

### 4.3 Contrast contract

Measured in-browser against the composited ground, not assumed:

| Element | Ratio | Grade |
|---|---|---|
| Hero H1 | 14.89:1 | AAA |
| Hero lede | 14.89:1 | AAA |
| Script accent | 8.10:1 | AAA |
| Nav links | 7.60:1 | AAA |
| Brass label | 5.65:1 | AA |

---

## 5. Content pipeline

| Stage | Script | Input | Output |
|---|---|---|---|
| Crawl | `capture.py`, `instagram_deep.py`, `reels.py`, `linktree.py`, `canva_menu_pages.py`, `untappd_tiktok.py` | live web | `research/raw/*`, `research/media/*` |
| Authenticated | `yelp_login.py` → `yelp_scraper.py` → `parse_yelp.py` | Yelp session | `yelp_parsed.json` |
| Parse | `menu_extract.py`, `menu_pdf_pages.py`, `parse_beers.py` | raw HTML | `official_menu.json`, `beer_list_parsed.json` |
| Curate | `curate.py` | raw assets + manifest | `brand_library/`, `curated_library.json` |
| Analyse | `analyze.py`, `finalize.py` | curated | `analysis.json`, `brand_data.json` |
| Tokens | `assets/tokens.json` (hand-authored) | analysis + guidelines | the design system |
| Build | `build_logo.py` → `build_site.py` → `build_pages.py` | tokens + crawled content | `site/**` |
| Validate | `validate_seo.py` | `site/**` | exit code |

**The menu page and beer page have no hand-typed content.** They are generated
from crawl output, so a price change is a re-run.

---

## 6. Security & privacy

| Concern | Position |
|---|---|
| Third-party JS | **None.** Google Fonts is the only external resource. |
| Cookies / tracking | **None.** No banner needed because there is nothing to consent to. |
| Data collected | Nothing. No forms, no accounts, no PII. |
| External links | `rel="nofollow noopener"` + `target="_blank"` on delivery CTAs |
| Supply chain | 1 Python dependency for the build (Pillow). Runtime: zero. |
| HTTPS | Enforced at the edge via `force_https=true` |
| Security headers | To set at the host: `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy`. Documented in `IMPLEMENTATION_PLAN.md` §6 — set at the host, not in markup, because a static site cannot send headers. |

---

## 7. Known limitations

| # | Limitation | Impact | Status |
|---|---|---|---|
| L1 | Uber `storeUUID` is `null` | `ubereats://` scheme inert; universal link still works | Client action |
| L2 | Logo SVGs are DRAFT reconstructions | Not the commissioned mark | Client action |
| L3 | Hero photo is a marketplace shot, not a commissioned shoot | Acceptable now, should not ship long-term | R23 |
| L4 | No analytics | Click-through cannot be measured | Deliberate; needs client decision |
| L5 | Menu can drift out of date | Accuracy risk | Needs a re-run cadence (see plan) |
| L6 | `aggregateRating` will go stale or become wrong if reviews change | Structured-data violation | Re-verify quarterly |
| L7 | Menu imagery per dish is not verified | DoorDash gates it behind an address check | Human pass needed |
