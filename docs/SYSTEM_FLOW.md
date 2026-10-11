# System Flow — The Rustic Barrel Taphouse Website

**Version:** 1.0 · **Date:** 11 Oct 2026

---

## 1. Authoring flow — data to deployed page

```
┌─────────────────────────────────────────────────────────────────────┐
│  LIVE WEB                                                           │
│  Instagram · Facebook · TikTok · DoorDash · Uber Eats                │
│  Linktree → Canva menu · Untappd · Yelp                             │
└────────────────────────────┬────────────────────────────────────────┘
                             │  Scrapling
                             │  · StealthyFetcher (anti-detection)
                             │  · Fetcher (TLS impersonation)
                             │  · solve_cloudflare
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  RAW CAPTURE                                                        │
│  research/raw/*.html   ·  wire manifests  ·  post HTML               │
└────────────────────────────┬────────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  PARSE                                                               │
│  official_menu.json    32 dishes, prices, descriptions               │
│  beer_list_parsed.json 17 beers, ABV, IBU, brewery                  │
│  yelp_parsed.json      4.6★ / 59 reviews, hours, 31 photos          │
│  price_diff.json       menu vs DoorDash (+3.3% avg)                  │
└────────────────────────────┬────────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  CURATE + ANALYSE                                                   │
│  108 brand frames · platform chrome quarantined (356 files)         │
│  palette by pixel quantisation · typography from computed styles    │
│  50 qualified design references                                    │
└────────────────────────────┬────────────────────────────────────────┘
                             ▼
                    ┌────────────────┐
                    │  tokens.json   │  ← human judgment, written ONCE
                    │  colour·type·  │     every value traceable to
                    │  space·motion· │     the evidence above
                    │  content facts │
                    └────────┬───────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
┌───────────────┐   ┌────────────────┐   ┌──────────────────┐
│ build_logo.py │   │ build_site.py  │   │  build_pages.py  │
│ DRAFT SVGs    │   │ tokens.css     │   │ menu·beer·       │
│ + PNG icons   │   │ responsive     │   │ events·visit·404 │
│               │   │ WebP + fallback│   │ (from crawl data)│
│               │   │ sitemap.xml    │   │                  │
│               │   │ robots.txt     │   │                  │
│               │   │ _redirects     │   │                  │
└───────┬───────┘   └────────┬───────┘   └─────────┬────────┘
        └────────────────────┼─────────────────────┘
                             ▼
                    ┌─────────────────┐
                    │   site/**       │  static output
                    └────────┬────────┘
                             ▼
                    ┌─────────────────┐      ┌──────────────────┐
                    │ validate_seo.py │─────▶│  exit 0 only     │
                    │ 12 checks       │ fail │  may deploy      │
                    └─────────────────┘      └────────┬─────────┘
                                                     ▼
                                             ┌───────────────┐
                                             │   CDN EDGE    │
                                             │ TLS·301·cache │
                                             └───────────────┘
```

---

## 2. Deep-link CTA flow — full decision tree

```
                    CUSTOMER TAPS THE ORDER CARD
                                 │
                                 ▼
                  ┌──────────────────────────┐
                  │ href = https://…/store/… │  always. always HTTPS.
                  └────────────┬─────────────┘
                               │
                               ▼
                  ┌──────────────────────────┐
                  │      OS APP LINK         │
                  │ doordash.com claims      │
                  │   */store/*  (AASA)      │
                  │ ubereats.com claims      │
                  │   /store/*/*  (AASA)     │
                  └────────────┬─────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
        APP INSTALLED    APP MISSING      APP BLOCKED
              │                │            (in-app webview)
              ▼                ▼                ▼
     ┌────────────────┐  ┌────────────┐  ┌──────────────────┐
     │ Native app      │  │ Browser    │  │ Webview cannot   │
     │ correct store   │  │ store page │  │ hand off         │
     │ page            │  │ ordering   │  │                  │
     └────────────────┘  └────────────┘  └────────┬─────────┘
              │                │                   │
              │                │           ┌───────▼────────┐
              │                │           │ SKIP the scheme│
              │                │           │ plain web link │
              │                │           │ handles it     │
              │                │           └───────┬────────┘
              ▼                ▼                   ▼
        ═══════════════════════════════════════════════
                        ORDER PLACED
        ═══════════════════════════════════════════════
```

### Enhancement layer — only for the edge cases

```
             deeplink.js runs (4.7 KB, defer, no deps)
                                 │
                                 ▼
                  ┌──────────────────────────┐
                  │  Is this a real gesture? │  yes, click handler
                  └────────────┬─────────────┘
                               │
                               ▼
                  ┌──────────────────────────┐
                  │  Desktop?                │──yes──▶ remove data-scheme
                  │  hover+pointer ≥1024px   │         plain link only
                  └────────────┬─────────────┘
                               │ no
                               ▼
                  ┌──────────────────────────┐
                  │  In-app webview?         │──yes──▶ SKIP
                  │  FBAN·FBAV·Instagram·    │         (blocked anyway)
                  │  Line·WeChat·Twitter     │
                  └────────────┬─────────────┘
                               │ no
                               ▼
                  ┌──────────────────────────┐
                  │  data-scheme contains    │──yes──▶ ANNOUNCE via
                  │  "{STORE_UUID}"?         │         aria-live
                  └────────────┬─────────────┘         (Uber, until configured)
                               │ no
                               ▼
                  ┌──────────────────────────┐
                  │  window.location = scheme│
                  │  start visibility watch  │
                  └────────────┬─────────────┘
                               │
                  ┌────────────┴────────────┐
                  │  1400ms elapsed          │
                  ▼                         ▼
        ┌────────────────┐        ┌────────────────────┐
        │ document.hidden │──yes──│ App took over.     │
        │ (app opened)    │        │ DO NOTHING.        │
        └───────┬────────┘        └────────────────────┘
                │ no
                ▼
        ┌────────────────────┐
        │ App not installed. │
        │ → web store URL    │
        └────────────────────┘
```

**Invariant: every branch ends at a working store page.** No blank screens.

---

## 3. Crawl flow — why it needed the workarounds it did

```
                    TARGET
                      │
      ┌───────────────┴───────────────┐
      ▼                               ▼
┌─────────────┐              ┌────────────────────┐
│ Plain HTML  │              │ JS / bot-protected  │
│ (Linktree,  │              │ (Yelp, TikTok,      │
│  Untappd)   │              │  Canva, Dribbble)   │
└──────┬──────┘              └─────────┬──────────┘
       │                               │
       ▼                               ▼
┌──────────────┐            ┌───────────────────────┐
│ Fetcher      │            │ StealthyFetcher      │
│ curl-cffi    │            │ stealth Chromium     │
│ TLS          │            │ + solve_cloudflare   │
│ impersonate  │            │ + persistent profile │
└──────┬───────┘            └──────────┬────────────┘
       │                               │
       │            ┌──────────────────┴─────────────────┐
       │            │  page_setup  → BEFORE navigation   │
       │            │  register the response listener,  │
       │            │  so the FIRST image is captured    │
       │            │                                    │
       │            │  page_action  → AFTER load         │
       │            │  scroll · click · .play() · harvest│
       └────────────┴──────────────────┬─────────────────┘
                                       │
                                       ▼
                            ┌─────────────────────┐
                            │ Classify every asset│
                            └──────────┬──────────┘
                                       │
          ┌────────────────┬───────────┴──────────┬────────────────┐
          ▼                ▼                      ▼                ▼
   ┌────────────┐  ┌─────────────┐        ┌──────────────┐  ┌───────────┐
   │ BRAND      │  │ PLATFORM    │        │ too small /  │  │ duplicate │
   │ (library)  │  │ CHROME      │        │ fragment     │  │ (4×4 hash)│
   │            │  │ quarantine  │        │ drop         │  │ drop      │
   └─────┬──────┘  └─────────────┘        └──────────────┘  └───────────┘
         │
         ▼
  ┌─────────────┐
  │ palette by  │──▶ tokens.json
  │ quantisation│
  └─────────────┘
```

### Three traps the pipeline hit, and the fixes

| Trap | Symptom | Fix |
|---|---|---|
| `Response` has no `.evaluate()` | `AttributeError` after a successful fetch | All DOM reads move **into** `page_action`, handed back via a closure dict |
| Real post images on `fcrk1` hosts, not `scontent` | Curation kept 640px sidebar thumbs, discarded every genuine photo | Classify on **host + resolution**, not host prefix alone |
| DoorDash serves ads through the store's own album path | Michelob Ultra creative survived URL filtering | No URL rule is sufficient; sponsorships require **human review** |

> The third is the honest limit of automated curation. It is documented as a
> required manual pass rather than papered over.

---

## 4. Content lifecycle — menu accuracy

```
  Day 0   Owner updates the Canva menu (their real workflow today)
     │
     ▼
  Day 14  ── scheduled re-crawl ──▶ canva_menu_pages.py
     │                              └─▶ official_menu.json
     ▼
  build_pages.py  ──▶ menu.html regenerated
     │
     ▼
  validate_seo.py  ──▶ exit 0
     │
     ▼
  Deploy. Live menu matches the counter within minutes.
```

**Today that gap is 14 days of wrong prices.** The pipeline closes it, but only
if someone runs it. Cadence is set in `IMPLEMENTATION_PLAN.md` §4.

---

## 5. SEO lifecycle — index → rank → maintain

```
  DEPLOY ──▶ verify 301 + HTTPS ──▶ Search Console verify domain
                                        │
                                        ▼
                                  submit sitemap.xml
                                        │
                                        ▼
                                  URL Inspection: Request Index
                                  for all 5 URLs
                                        │
                                        ▼
                              ┌─────────────────────┐
                              │  Local Pack ranking │◀── Google Business
                              │  (GBP outranks us)  │    Profile, synced
                              └─────────┬───────────┘
                                        │
                              ┌─────────▼───────────┐
                              │  Organic: menu,     │
                              │  beer, location     │
                              └─────────┬───────────┘
                                        │
                              ┌─────────▼───────────┐
                              │  Backlinks: chamber,│
                              │  city events, press │──▶ authority
                              └─────────────────────┘
```

First 8 weeks are crawl → index. Nothing ranks meaningfully until Google has
re-crawled. The plan accounts for that rather than promising traffic in week two.
