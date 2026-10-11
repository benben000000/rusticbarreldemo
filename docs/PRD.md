# PRD — The Rustic Barrel Taphouse Website

**Version:** 1.0 · **Date:** 11 Oct 2026 · **Owner:** Client / Agency
**Status:** Build complete, pending deployment (blocked on domain ownership — see §9)

---

## 1. Problem

The Rustic Barrel has a genuinely strong, hand-made visual identity and **no
home to put it in.**

| Finding | Evidence |
|---|---|
| No owned website | `therusticbarrel.com` is a parked domain (151-byte JS lander). `rusticbarrel.com` is listed for sale on a broker. |
| No brand-owned assets | No vector logo, no brand fonts, no brand colours anywhere. Computed styles return only platform defaults (DD Norms, UberMoveText, Times New Roman, Segoe UI). |
| Every channel is rented | Instagram, Facebook, TikTok, Yelp, DoorDash, Uber Eats, Linktree — all of which can change fonts, colours and layout without notice. |
| Identity trapped in pixels | The barrel badge, wood-type, cream-on-navy palette exist only as baked-in JPEGs on social posts. |
| Brand error live in market | "King City, **GA**" on the comedy flyer. King City is in **California**. |
| Dead conversion path | The Linktree "Contact Us" block is configured but **completely empty**. |
| The best product is invisible | A venue categorised *Beer Bar · Sports Bar* with 17 craft beers on Untappd sells **nine soft drinks and no beer** on its menu. |

**Cost of doing nothing:** the restaurant keeps paying commission on every order
it could have taken directly, keeps a brand identity nobody can reuse, and
remains unfindable by anyone searching for it by name.

## 2. Goals

| # | Goal | Measure |
|---|---|---|
| G1 | Own a canonical domain and identity | `www.therusticbarrel.com` serving 200 over HTTPS, `therusticbarrel.com` 301-redirecting to it |
| G2 | Be findable for local intent | Indexed for "King City beer bar", "King City BBQ", "Canal St bar" within 60 days |
| G3 | Convert visitors to orders | ≥ 1 order-intent click per 50 sessions; deep-link CTA on every page |
| G4 | Codify the identity | `tokens.json` + guidelines shipped; every new surface generated from tokens |
| G5 | Beat the platform tax | Menu prices visible without clicking through to a marketplace |
| G6 | Ship fast and stay fast | Core Web Vitals in the green on 4G mobile |
| G7 | Be maintainable by non-engineers | Content edits are a JSON edit + one command |

## 3. Non-goals

- **Not** a CMS, an ordering system, or a POS replacement.
- **Not** a loyalty club, bookings engine or job board in v1.
- **Not** a directory listing replacement — Google Business Profile stays and is
  kept in sync (it outranks the site for local pack results).
- **Not** a framework application. Static HTML by design (§TRD 1.1).
- **Not** a rebuild of the delivery marketplaces. We link out, never embed.

## 4. Users

| Persona | Need | Where they come from |
|---|---|---|
| **Local, 25–55** — "going to the Rustic" | Confirm hours, find the door, order food | Google, Instagram bio |
| **Sports-night group** | Confirm screens + which app to order on | TikTok, Instagram, word of mouth |
| **Passing-through / new** | "Is it worth stopping?" | Google Maps, Yelp, Drive-by |
| **Craving delivery** | Reorder a known dish, fast | Direct URL, Linktree, a saved app |
| **Owner/manager** | Change a price or an event | Phone to the agency — **not** an editor |

**Deliberate exclusion:** there is no customer account, no login, and no cookie
banner. A neighbourhood bar does not need identity infrastructure, and a cookie
banner is a tax on the one thing that matters — the order button.

## 5. Requirements

### 5.1 Must-have (v1 — built)

| ID | Requirement | Where |
|---|---|---|
| R1 | 5-page static site: home, menu, beer, events, visit | `site/*.html` |
| R2 | One canonical host, www, with 301 from the bare domain and force-HTTPS | `_redirects`, `vercel.json` |
| R3 | Valid `robots.txt` — public pages allowed, sitemap referenced, no blanket disallow | `site/robots.txt` |
| R4 | `sitemap.xml` covering every indexable page with priority + changefreq | `site/sitemap.xml` |
| R5 | Unique title ≤60ch and meta description ≤155ch per page, self-referencing canonical | enforced by `validate_seo.py` |
| R6 | Exactly one `<h1>` per page | enforced by `validate_seo.py` |
| R7 | Mobile-first, responsive 320px → 1440px, 48px tap targets | `site.css` |
| R8 | **Order CTA opening the delivery apps directly** | `site.css`, `deeplink.js` |
| R9 | Restaurant JSON-LD: address, geo, hours, rating, price range, menu link | `<script type="application/ld+json">` |
| R10 | `OrderAction` structured data for both delivery providers | homepage JSON-LD |
| R11 | Design tokens as the single source of truth | `assets/tokens.json` |
| R12 | Generated CSS custom properties from tokens | `assets/tokens.css` |
| R13 | Real menu content, 32 dishes, sourced from the official Canva menu | `official_menu.json` |
| R14 | Real tap list with ABV and brewery | `beer_list_parsed.json` |
| R15 | Breadcrumb-free, fully cross-linked internal navigation | every page |
| R16 | 404 page with recovery routes | `site/404.html` |
| R17 | Accessible: skip link, focus rings, live regions, AA contrast | `site.css` |
| R18 | `prefers-reduced-motion` honoured | `site.css` |
| R19 | Print stylesheet (menus get printed at a bar) | `site.css` |
| R20 | Automated SEO validation gate in the build | `validate_seo.py` |

### 5.2 Should-have (v1.1)

| ID | Requirement | Note |
|---|---|---|
| R21 | Events CMS-fed from a `events.json` | Patterns already proven by the menu generator |
| R22 | Beer "what's on now" board with tap numbers | Needs a data source the client can update |
| R23 | Real photography replacing the flyer-derived hero | Blocked on a photo shoot |
| R24 | Commissioned vector logo replacing the DRAFT SVGs | Blocked on artwork |
| R25 | Spanish-language menu | ~9% Hispanic population in the service area; worth scoping |

### 5.3 Won't-have (v1)

Booking engine · loyalty programme · live order tracking · user accounts ·
comment forms · third-party analytics · cookie consent UI.

## 6. The deep-link CTA — the signature feature

> *"A button that hands off to the DoorDash or Uber Eats app and lands the
> customer on this restaurant's store page — not the app homepage."*

### 6.1 What the research changed

The naive build is two custom-scheme links: `doordash://…` and `ubereats://…`.
Investigation showed that is **the wrong approach**, because both platforms
already publish an `apple-app-site-association` file claiming their own HTTPS
store URLs:

| Domain | Claims | Path |
|---|---|---|
| `doordash.com` | `com.doordash.DoorDashConsumer`, `…RedApp`, `com.trycaviar.consumer` | `*/store/*` |
| `ubereats.com` | `com.ubercab.UberEats.Dev` | `/store/*/*` |

So **a plain `https://` link to the store page is already an App Link / Universal
Link.** The OS resolves it to the app when installed and to the browser when not.

### 6.2 Design consequence

**The primary CTA is a plain `<a href="https://…">` with no JavaScript at all.**
That is deliberate and it is the correct engineering:

| Property | Why it matters |
|---|---|
| Works with JS disabled | Nothing to break |
| Works in email clients | Most clients strip `<script>` |
| Works from Google results | The App Link path is the strongest signal |
| No timer race | The classic `setTimeout` fallback pattern misfires on slow devices and strands users on a blank screen |
| Crawlable | Search engines follow it |
| Zero maintenance | Platform changes to their AASA file propagate automatically |

### 6.3 What the JS *does* add (`deeplink.js`, ~2 KB)

Only the two cases the universal link cannot cover:

1. **In-app browsers.** Instagram and Facebook's embedded webviews block app
   switching. Attempting a hand-off there drops the user on a dead screen, so we
   detect `FBAN|FBAV|Instagram|Line|MicroMessenger|Twitter` and skip the attempt,
   leaving the plain web link to do its job.
2. **Desktop.** We never attempt a scheme on a pointer-fine viewport — it cannot
   succeed and only produces a console error.

Plus: if a custom scheme *is* attempted (opt-in only), a 1.4s
`visibilitychange` check detects that the app did **not** take over and routes
to the web store instead of stranding the user.

### 6.4 Known limitation — stated, not hidden

The `ubereats://` custom scheme needs a real **`storeUUID`**, which Uber issues
per merchant. It is **not derivable from any public URL** and is deliberately
`null` in `tokens.json`. Until the client copies it from the Uber Eats Merchant
Portal, the Uber CTA runs on the universal link alone — which works, and is the
primary path anyway.

**This is a configuration task, not an engineering one.**

## 7. Success metrics

| Metric | Baseline | 90-day target | How measured |
|---|---|---|---|
| Organic sessions | 0 (no site) | 400+ | Search Console |
| Indexed pages | 0 | 5 | Search Console URL Inspection |
| Order-CTA click-through | — | ≥ 2% of sessions | Plausible (privacy-first) analytics or manual |
| Domain authority | 0 | ≥ 5 backlinks | Search Console / Ahrefs |
| LCP (4G mobile) | — | < 2.0s | PageSpeed Insights |
| CLS | — | < 0.05 | PageSpeed Insights |
| INP | — | < 150ms | PageSpeed Insights |

> **Analytics caveat:** the site ships **zero** trackers and no cookie banner.
> Measuring click-through therefore means either a privacy-first, cookieless
> tool (Plausible/Umami/Fathom) or accepting the number is not measured. This is
> a deliberate trade and should be confirmed with the client, not assumed.

## 8. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **Domain is squatted before launch** | Low | Critical | Register `therusticbarrel.com` **and** `rusticbarrel.com` today, before anything else. Auto-renew + registry lock. |
| Domain registrar / DNS misconfiguration | Medium | High | `_redirects` and `vercel.json` both ship; verify the 301 on day one |
| Client has no Google account | Medium | Medium | We cannot submit to Search Console without one — see §9 |
| Client cannot supply the Uber `storeUUID` | Medium | Low | Universal link still works; CTA degrades gracefully |
| Photos are of poor quality (they are marketplace shots) | High | Medium | R23 — photo shoot is the highest-value non-code spend |
| Logo never gets commissioned | Medium | Medium | DRAFT SVGs shipped so the site is not blocked |
| Menus drift out of date | High | Medium | Menu is generated from one JSON; a re-run updates every page |
| Review aggregator markup confusion | — | Low | The 4% disclosure is stated plainly on the page |

## 9. Blockers — what I cannot do

These require the client, and no engineering substitutes for them:

1. **Register the domain.** `therusticbarrel.com` is parked and purchasable by
   anyone. Until it is yours, every URL in this build is aspirational.
2. **Create / access a Google account** for Search Console verification and
   sitemap submission. I cannot verify domain ownership on the client's behalf.
3. **Supply the Uber Eats `storeUUID`** from the Merchant Portal.
4. **Commission the vector logo.** The shipped SVGs are DRAFT reconstructions.
5. **Authorize hosting** (Netlify / Cloudflare Pages — both free at this scale).

## 10. Definition of done

- [x] All 20 v1 requirements implemented
- [x] `validate_seo.py` exits 0 — 8 passes, 0 warnings, 0 failures
- [x] All 5 pages + 404 + robots + sitemap + manifest return 200
- [x] No broken internal links; no orphan pages
- [x] Contrast measured ≥ 4.5:1 for body, ≥ 14:1 for hero
- [x] `tokens.json` is the single source of truth for colour, type, space, motion
- [ ] Domain registered *(client)*
- [ ] Deployed to a live HTTPS host *(client)*
- [ ] 301 + force-HTTPS verified in production *(post-deploy)*
- [ ] Search Console verified, sitemap submitted *(client)*
- [ ] Key URLs submitted for indexing *(client)*
- [ ] Backlinks acquired *(ongoing)*

**Related documents:** `TRD.md` · `ARCHITECTURE.md` · `SYSTEM_FLOW.md` ·
`IMPLEMENTATION_PLAN.md` · `SEO_LAUNCH_CHECKLIST.md`
