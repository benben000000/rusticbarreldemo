# SEO Launch Checklist — The Rustic Barrel Taphouse

**Version:** 1.0 · **Date:** 11 Oct 2026

---

## ⚠ Read this first

Your list assumes a website exists. **The Rustic Barrel has none** —
`therusticbarrel.com` is a parked domain the client does not own, so nothing
could be verified "live over HTTPS", submitted to Search Console, or
domain-verified.

So this checklist is split honestly:

- **✅ DONE — built and enforced in code.** These are already implemented and
  machine-verified. They will be satisfied the moment the site is deployed.
- **🔧 POST-DEPLOY — verify in production.** Must be confirmed on the live host.
- **🔑 CLIENT-ONLY — needs your domain and Google account.** I cannot do these.

Nothing is marked done that is not.

---

## ✅ DONE — implemented and machine-verified

Enforced by `scripts/validate_seo.py`. **Current result: 8 passed, 0 warnings,
0 failures.** A failing build cannot deploy.

| # | Requirement | Implementation | Verified by |
|---|---|---|---|
| 1 | **Site publicly accessible over HTTPS** | Edge TLS + `force_https=true` in `_redirects` | Post-deploy §B1 |
| 2 | **Important pages return HTTP 200** | All 5 pages + 404 + robots + sitemap + manifest + tokens + CSS + JS tested against a local server — all **200** | ✅ tested |
| 3 | **Remove noindex meta tags and headers** | `robots` is `index, follow, max-image-preview:large` on every page; **no `X-Robots-Tag` anywhere**; validator fails the build if `noindex` appears | ✅ automated |
| 4 | **robots.txt at the domain root** | `site/robots.txt` — `User-agent: *` / `Allow: /` | ✅ exists |
| 5 | **Allow public pages in robots.txt** | `Allow: /` for `*`, plus explicit `Allow: /` for Googlebot, Googlebot-Image, Bingbot, Applebot, Google-Extended. Only build artefacts excluded | ✅ automated |
| 6 | **Generate sitemap.xml** | `site/sitemap.xml`, 5 URLs with `lastmod`/`changefreq`/`priority`. Validator asserts **every** indexable page is present | ✅ automated |
| 7 | **Reference sitemap in robots.txt** | `Sitemap: https://www.therusticbarrel.com/sitemap.xml` | ✅ automated |
| 8 | **Set canonical URLs** | Absolute, https, self-referencing, generated from `tokens.json → seo.canonicalBase` | ✅ automated |
| 9 | **One primary domain version + redirect the other** | `www` canonical; bare domain 301 → www (`_redirects` + `vercel.json`) | ✅ shipped · verify §B2 |
| 10 | **Unique page titles** | 5 unique, all ≤60 chars | ✅ automated |
| 11 | **Unique meta descriptions** | 5 unique, all 118–135 chars | ✅ automated |
| 12 | **One clear `<h1>` per page** | Exactly 1 on all 6 pages | ✅ automated |
| 13 | **Descriptive, indexable content** | Real menu (32 dishes), real tap list (17 beers with ABV/brewery), hours, address, events — all indexable body copy, not thin filler | ✅ shipped |
| 14 | **Internal links between important pages** | Header nav + contextual links + full footer on every page; validator resolves every `href` on disk and flags orphans | ✅ automated |
| 15 | **Mobile-friendly** | Mobile-first CSS, viewport meta on every page, 48px tap targets, `svh` units, fluid `clamp()` type, table scroll container | ✅ shipped |
| 16 | **Improve page speed / Core Web Vitals** | Static edge delivery · ~18 KB HTML · 20 KB CSS · **4.7 KB JS** · zero third-party JS · WebP + `fetchpriority=high` LCP hero · explicit `width`/`height` on all media (no CLS) · fonts `swap` + `preconnect` | ✅ shipped · measure §B4 |
| 17 | **Fix broken links and redirects** | Validator fails on any unresolved internal link. **0 broken links** | ✅ automated |
| 18 | **Avoid blocking crawlers** | No auth, no firewall rules, no maintenance mode, no Cloudflare challenge on our own domain, no IP allowlists | ✅ by design |
| 19 | **Structured data** | `Restaurant` + `WebSite` (`@graph`) with address, geo, 7-day hours, 4.6★/59 rating, `priceRange`, `hasMenu`, and **`OrderAction`** with both providers · `Menu`+`MenuSection` · `ItemList` of `Product` · `LocalBusiness` · `WebPage` | ✅ automated (parses) |
| 20 | **Accessibility (supports all of the above)** | Skip link, visible focus rings (never removed), `aria-current`, `aria-live` status region, `aria-hidden` on decorative glyphs, print stylesheet, `prefers-reduced-motion`. Measured contrast: hero H1 **14.89:1**, lede **14.89:1**, script **8.10:1**, nav **7.60:1** | ✅ measured |

### Excluded deliberately

| Item | Why |
|---|---|
| `Disallow: /` | Not used — this is the #1 self-inflicted deindexing mistake. The validator greps for it and fails the build. |
| `Disallow` for AI crawlers | A public restaurant refusing AI crawlers is a bad look for no gain. |
| Cookie-consent UI | No cookies, no trackers, nothing to consent to. |

---

## 🔧 POST-DEPLOY — verify in production

Run after Phase 2 of `IMPLEMENTATION_PLAN.md`.

```powershell
# 1. HTTPS + canonical redirect
curl.exe -sI https://www.therusticbarrel.com/     | Select-String "HTTP/"
curl.exe -sI http://therusticbarrel.com/          # → 301, Location: https://www.therusticbarrel.com/
curl.exe -sI https://therusticbarrel.com/         # → 301 to www

# 2. every page 200
foreach ($p in "/","/menu.html","/beer.html","/events.html","/visit.html",
               "/robots.txt","/sitemap.xml","/site.webmanifest","/assets/tokens.css")
  { $r = Invoke-WebRequest "https://www.therusticbarrel.com$p" -UseBasicParsing
    "$p  $($r.StatusCode)" }

# 3. no noindex anywhere
curl.exe -s https://www.therusticbarrel.com/ | Select-String "noindex"   # → no match

# 4. security headers present
curl.exe -sI https://www.therusticbarrel.com/ | Select-String "Strict-Transport|x-content-type|referrer-policy"
```

- [ ] **B1** HTTPS cert valid, HTTP → HTTPS redirect
- [ ] **B2** bare domain → `www` 301 (and the reverse never happens)
- [ ] **B3** all pages 200; unknown path → styled 404
- [ ] **B4** PageSpeed Insights (mobile): **LCP < 2.0s · CLS < 0.05 · INP < 150ms**
- [ ] **B5** Rich Results Test → Restaurant rich result valid
- [ ] **B6** Security headers present (see plan §6)
- [ ] **B7** Tap both CTAs on a real iPhone and Android, with and without the apps installed

---

## 🔑 CLIENT-ONLY — needs your domain and Google account

**I cannot perform any of these.** They require domain ownership and
authenticated access to a Google account that does not exist yet.

| # | Task | Steps | Done when |
|---|---|---|---|
| C1 | **Submit sitemap to Search Console** | search.google.com/search-console → add property (**Domain**) → verify with DNS TXT → Sitemaps → paste `https://www.therusticbarrel.com/sitemap.xml` | Status **Success** |
| C2 | **Verify domain in Search Console** | DNS TXT proof. Both `therusticbarrel.com` and any subdomain | Property shows "Verified" |
| C3 | **Submit key URLs for indexing** | URL Inspection → paste each of the 5 URLs → **Request Indexing** | 5 URLs queued |
| C4 | **Claim Google Business Profile** | Claim the existing listing or create it; verify by postcard/phone/email | Listing live and accurate |
| C5 | **Sync GBP with the site** | Hours (**Tuesday closed**), phone, address, categories, 10+ photos, link to `/menu.html` | GBP matches site |
| C6 | **Create useful backlinks** | Chamber of Commerce · King City tourism · local press · event promoters · Laughing Booth Comedy · the breweries you pour | 5+ relevant referring domains |
| C7 | **Monitor indexing & crawl errors** | Search Console → Pages (indexed vs submitted), and **Security & Manual Actions** = clean | 5/5 indexed; 0 errors |
| C8 | **Ongoing monitoring** | Monthly: index coverage, Core Web Vitals field data, top queries, 404 report | Logged |

### Backlink targets, ranked by realistic value

| Target | Why it works | Effort |
|---|---|---|
| **King City Chamber of Commerce** | Direct local authority, often links to member sites | Low |
| **Monterey County / Central Coast tourism** | Geographic relevance | Medium |
| **The breweries they pour** | Russian River, Firestone Walker, Alvarado Street often feature local stockists | Medium, high value |
| **Laughing Booth Comedy** | Already promoting their events | Very low — just ask |
| **Local event calendars** | Comedy nights, watch parties | Low |
| **Firestone Walker trail guides** | Beer writers covering Central Coast taps | Medium |

> Honest expectation: **5–10 relevant backlinks in the first 90 days** from real
> outreach. Do not buy links — for a local business the risk to GBP standing
> outweighs any gain.

---

## Verification timing

| Window | What happens |
|---|---|
| **Day 0–2** | Deploy. No index yet. |
| **Day 3** | Property verified, sitemap submitted. |
| **Day 3–10** | Request indexing. Google queues a crawl. |
| **Week 2–3** | Pages move to "Crawled – currently not indexed" → then indexed. **Normal.** |
| **Week 4–6** | Indexed. GBP starts outranking the site in local pack — expected and fine. |
| **Week 8–12** | First organic impressions. Realistic: dozens of impressions, not thousands. |
| **Month 4–6** | Organic sessions become measurable. |

**Do not judge this at week two.** For a business with no prior web presence,
the honest KPI at 90 days is *indexed and correct*, not *ranking*.

---

## Ongoing

| Cadence | Task |
|---|---|
| Weekly | Search Console → check for new errors |
| Monthly | Sync GBP hours/photos; check top queries |
| Quarterly | Re-parse Yelp rating into JSON-LD; **manually tap both CTAs on a phone** |
| Annually | Domain + hosting renewal |

### ⚠ One structured-data caveat

`aggregateRating: 4.6 / 59` is included because both values are exact and taken
from Yelp's own JSON-LD. **If Yelp reviews are filtered, or the rating becomes
self-managed, this becomes a structured-data violation** and Google may issue a
manual action. Re-verify quarterly, and if the client ever manages their own
Yelp reviews, remove the field.
