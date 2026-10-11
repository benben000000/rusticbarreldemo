# Implementation Plan — The Rustic Barrel Taphouse Website

**Version:** 1.0 · **Date:** 11 Oct 2026

---

## 0. Status

| Phase | State |
|---|---|
| Research & brand identity | ✅ Complete |
| Design tokens & reference qualification | ✅ Complete |
| Site build (5 pages + 404) | ✅ Complete |
| Deep-link CTA | ✅ Complete (Uber scheme pending one config value) |
| SEO automation & validation | ✅ Complete — 8 pass, 0 warn, 0 fail |
| **Domain registration** | 🔴 **BLOCKED — client action, do this first** |
| Deployment | ⬜ Blocked on domain |
| Search Console & indexing | ⬜ Blocked on domain + Google account |
| Backlinks | ⬜ Ongoing |

---

## 1. Critical path — the ordering that matters

**Phase 1 is not optional and not parallelisable. Do it today.**

```
DAY 0  ──▶  Register therusticbarrel.com          ← RISK: squattable TODAY
           Register rusticbarrel.com               ← defensive
           Enable auto-renew + registry lock
           Enable WHOIS privacy
                                    │
                                    ▼
DAY 1-2 ─▶  DNS: A/AAAA → Netlify (or CF Pages)
           Verify HTTPS certificate issues
           Verify 301 from bare domain → www
                                    │
                                    ▼
DAY 2   ──▶  Deploy site/
           Run the launch checklist (SEO_LAUNCH_CHECKLIST.md)
                                    │
                                    ▼
DAY 3   ──▶  Google: create account, verify domain property
           Submit sitemap.xml
           Request indexing on 5 URLs
                                    │
                                    ▼
WEEK 2-4 ─▶ First crawl + index. Watch Search Console → Pages.
                                    │
                                    ▼
WEEK 4+ ──▶ GBP sync, backlinks, content cadence
```

**Why Phase 1 is urgent:** `therusticbarrel.com` is a parked domain with a live
lander. It is purchasable. Every day it is unclaimed is a day someone else can
take the name a customer is about to type into a search bar.

---

## 2. Phase detail

### Phase 1 — Domain & DNS *(client, day 0)*

| # | Task | Owner | Done when |
|---|---|---|---|
| 1.1 | Register `therusticbarrel.com` (10 yr if possible) | Client | WHOIS shows client ownership |
| 1.2 | Register `rusticbarrel.com` defensively | Client | Redirects to primary |
| 1.3 | Auto-renew ON, registry lock ON, WHOIS privacy ON | Client | Confirmed in registrar UI |
| 1.4 | Netlify or Cloudflare Pages account | Client | Site can deploy |
| 1.5 | A/AAAA → edge; CNAME `www` → apex | Client | Both resolve |
| 1.6 | Confirm `_redirects` deployed (301 + force HTTPS) | Agency | `curl -I http://therusticbarrel.com` → 301 |

**Acceptance:** `curl -I https://therusticbarrel.com` → `301` →
`https://www.therusticbarrel.com`.

---

### Phase 2 — Deploy *(agency + client, day 2)*

| # | Task | Owner |
|---|---|---|
| 2.1 | Drag `site/` to Netlify, or `npx vercel deploy --prod` | Agency |
| 2.2 | Confirm all 6 HTML + robots + sitemap return **200** | Agency |
| 2.3 | Confirm unknown URL returns the styled 404, not the default | Agency |
| 2.4 | Confirm security headers (see §6) | Agency |
| 2.5 | Confirm canonical host 301 + force HTTPS in production | Agency |

**Smoke test (run in this order):**

```
curl -sI https://www.therusticbarrel.com/            | Select-String "HTTP/|location"
curl -sI http://therusticbarrel.com/                 → expect 301 to https://www…
curl -s  https://www.therusticbarrel.com/robots.txt
curl -s  https://www.therusticbarrel.com/sitemap.xml
curl -sI https://www.therusticbarrel.com/assets/tokens.css | Select-String "cache-control"
```

---

### Phase 3 — Search Console & indexing *(client, day 3)*

Full detail in `SEO_LAUNCH_CHECKLIST.md`. Summary:

| # | Task | Done when |
|---|---|---|
| 3.1 | Google account for the business | Account exists |
| 3.2 | Add property, **Domain** type | Verified |
| 3.3 | Submit `sitemap.xml` | Status "Success" |
| 3.4 | URL Inspection → Request Index × 5 | All 5 queued |
| 3.5 | Google Business Profile: claim + verify | Live listing |
| 3.6 | GBP: hours, phone, categories, photos, menu link | Matches site |

> GBP will outrank the website in the local pack for most queries. **Sync it
> weekly.** The site is the durable asset; GBP is the shop window.

---

### Phase 4 — Content operations *(ongoing)*

The pipeline exists so content stays accurate. It needs a human to run it.

| Cadence | Task | Script | Owner |
|---|---|---|---|
| **Bi-weekly** | Re-crawl the Canva menu; redeploy if prices changed | `canva_menu_pages.py` → `build_pages.py` | Agency |
| **Monthly** | Check for broken external links | `link-check` | Agency |
| **Quarterly** | Re-parse Yelp (rating/review count change) | `parse_yelp.py` | Agency |
| **Quarterly** | **Manually tap both CTAs** on a real phone — platforms rotate URLs | — | Client |
| **Quarterly** | Confirm Uber `storeUUID` still valid | Merchant Portal | Client |
| **Annually** | Domain + hosting renewal | Registrar | Client |

**The quarterly manual CTA test is not optional.** Delivery platforms change
store URLs without notice; nothing in a static build will notice for you.

---

## 3. Resource & effort estimate

| Workstream | Effort | Notes |
|---|---|---|
| Research, crawl, brand identity | **Done** | ~40 scripts, 9 channels, 700+ assets |
| Design tokens + references | **Done** | 267 shots captured, 50 qualified |
| Site build | **Done** | 5 pages + 404, ~2s build |
| SEO automation | **Done** | 12-check gate |
| Client domain acquisition | ~30 min | Their call, their card |
| Hosting setup + DNS | ~1 h | Netlify walkthrough |
| Deployment + smoke test | ~1 h | Agency |
| Search Console + GBP | ~2 h | Client, with a call |
| **Vector logo commission** | **$400–1,200** | Freelancer; highest-value non-code spend |
| **Photography shoot** | **$500–1,500** | Replaces marketplace images (R23) |
| Backlink outreach | ~4 h/mo | Ongoing |

**Cheapest, highest-impact remaining spend: the photography shoot.** The hero
image is currently a marketplace shot. A real shoot of the bar at 9pm on a
game night would outperform any further code.

---

## 4. Content refresh plan (first 90 days)

| Window | Action | Purpose |
|---|---|---|
| Day 0–7 | Deploy, index, GBP sync | Get discovered |
| Week 2–4 | Add 4–6 real photos (bar, taps, tri-tip, a game night) | Replace marketplace imagery |
| Week 4–6 | Publish the first 3 events on `/events.html` | Give Google fresh local content; give customers a reason |
| Week 6–10 | Commission + ship the vector logo | Remove the DRAFT SVG caveat |
| Week 8–12 | Add "what's on tap today" with real tap numbers | Converts the #1 customer question |
| Ongoing | 2 social posts/week → link to the matching site page | Drive the Linktree audience to an owned destination |

> The Linktree is currently the only place the business publishes its own links.
> Every social post should now point at the site, not Linktree. **That is the
> whole point of building it.**

---

## 5. Risk register

| # | Risk | Severity | Trigger | Response |
|---|---|---|---|---|
| R1 | **Domain squatted before registration** | 🔴 Critical | Registrar reports taken | Register both domains immediately; use a .com alternative if needed |
| R2 | No Google account / GBP access | 🟠 High | 7 days post-launch, no access | Create one at kickoff, not day 3 |
| R3 | Uber `storeUUID` never supplied | 🟡 Medium | 30 days | CTA degrades to universal link; still works |
| R4 | Vector logo never commissioned | 🟡 Medium | 90 days | DRAFT SVGs remain; low visual impact |
| R5 | Menu prices drift | 🟠 High | >14 days without re-crawl | Bi-weekly cadence + a monthly reminder |
| R6 | Delivery platform changes URLs | 🟠 High | Quarterly test fails | Update `tokens.json`, rebuild, redeploy — 10 minutes |
| R7 | Photography never reshoots | 🟡 Medium | 6 months | Marketable; the current images work |
| R8 | Host misconfiguration (no 301) | 🔴 Critical | Smoke test fails | Blocked by Phase 2 acceptance test |

---

## 6. Production hardening *(set at the host — a static site cannot send headers)*

```nginx
# Netlify _headers (add to site/_headers before deploy)
# or Cloudflare Pages _headers, or Netlify Edge Functions

/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: geolocation=(), microphone=(), camera=(), interest-cohort=()
  X-Frame-Options: SAMEORIGIN
  Strict-Transport-Security: max-age=63072000; includeSubDomains; preload

/assets/*
  Cache-Control: public, max-age=31536000, immutable

/*.html
  Cache-Control: public, max-age=0, must-revalidate
```

---

## 7. Handover

| Deliverable | Path |
|---|---|
| Site source | `site/` |
| Design tokens | `site/assets/tokens.json` |
| Brand guidelines | `BRAND_IDENTITY_GUIDELINES.md` |
| Vibe & direction | `BRAND_VIBE.md` |
| Qualified references | `research/reference/shortlist.html` |
| Media library | `research/media/brand_marks/` (119 files) |
| Media contact sheet | `research/brand/contact_sheet.html` |
| Scraper source | `scripts/` |
| Crawl + analysis output | `research/` |
| Build command | `python scripts/build_logo.py && build_site.py && build_pages.py && validate_seo.py` |

**The client can never break the site by editing it**, because they would have to
edit a generated file — and the validator would catch the consequences on the
next build. That is the intended safety property.
