# The Rustic Barrel — Research Notes

**Client:** The Rustic Barrel — Beer Bar / Sports Bar / Sandwiches
**Address:** 611 Canal St, King City, CA 93930 (Monterey County, Central Coast)
**Phone:** (831) 601-1397
**Email:** therusticbarrel831@gmail.com
**Tooling:** Scrapling 0.4.15 (`StealthyFetcher` = stealth Chromium, `Fetcher` = curl-cffi impersonation)

---

## 1. Digital presence audit

| Channel | URL | Status |
|---|---|---|
| Yelp | `yelp.com/biz/the-rustic-barrel-king-city-2` | **HTTP 403 — hard bot block** |
| DoorDash | `doordash.com/store/34689489` | 200 (via Cloudflare Turnstile solve) |
| Uber Eats | `ubereats.com/store/the-rustic-barrel/j50H6Tr2W-qha1Ep9ys4Ag` | 200 (via Cloudflare Turnstile solve) |
| Facebook | `facebook.com/therusticbarreltaphouse` | 200 |
| Instagram | `instagram.com/the_rustic_barrel_` | 200 |
| **Linktree** | `linktr.ee/therusticbarrel_831` | 200 — **the hub; found 4 new sources** |
| **Canva menu** | `canva.link/jn02vj7qvspjnja` → design `DAHAU38TVeA` | 200 — **official 2-page menu** |
| **Untappd** | `untp.beer/450efae094` → `/v/the-rustic-barrel/13736755` | 200 (Cloudflare solved) — **17-beer list** |
| **TikTok** | `tiktok.com/@therusticbarrel831` | Profile login-walled; **70 video URLs leaked**, 1 downloadable |

### The Linktree is the real index

The Instagram bio points at Linktree, and it is the **only place the business
publishes its own links**. Everything found there was invisible from the other
channels:

| Link | Type | What it gave us |
|---|---|---|
| The Rustic Barrel Menu | Canva | The **actual 2-page menu** — 32 dishes with descriptions + prices |
| Untappd | Beer | 17 beers, ABV/IBU/brewery — "BBQ Joint" category |
| Follow us on TikTok | Social/video | 70 posts, captions recovered |
| Order Here | DoorDash | (already captured) |
| Leave Us a Yelp Review | Review | (already captured) |
| Leave Us a Google Review | Review | Google search-based listing |
| **Contact Us** | `CONTACT_DETAILS` | **⚠ Configured but EMPTY — no email or phone set** |

### Owned-domain check — all negative

| Domain | Result |
|---|---|
| `therusticbarrel.com` | **Parked.** 151-byte JS lander redirecting to `/lander?oref=...` |
| `rusticbarrel.com` | **For sale.** Redirects to `thebrandable.com/buy-domain/rusticbarrel.com` |
| `therusticbarrel831.com` | NXDOMAIN |
| `rusticbarrelkingcity.com` | NXDOMAIN |

> **Key finding:** The Rustic Barrel has **no owned website**. 100% of their brand
> presence is rented — social + delivery marketplaces. The `.com` they appear to
> own is not theirs. This is the single most important input to the guidelines:
> there is no existing brand system to codify, only raw material to build from.

---

## 2. Blocked / unreachable

- **Yelp** returns `403` to every request including stealth Chromium. Yelp blocks
  at the edge (datacenter IP reputation), not by challenge. Captured data will
  have to come from the other four channels plus secondary sources.
- `therusticbarrel.com` is a parking page — nothing to scrape.

---

## 3. Scrape pipeline

| Script | Phase |
|---|---|
| `scripts/recon.py` | Probe every channel for reachability |
| `scripts/brandlib.py` | Shared helpers: URL classification, downloads, in-page JS harvesters |
| `scripts/capture.py` | Load page in stealth Chromium, record wire traffic, harvest DOM, download assets |
| `scripts/instagram_deep.py` | Step through every IG post for full-res media |
| `scripts/analyze.py` | Pillow palette extraction, typography + colour distillation, JSON-LD parsing |
| `scripts/render_tables.py` | Emit `research/brand/data_tables.md` |

### Output layout

```
research/
  raw/          <source>.html, <source>.json, instagram_posts.json
  media/
    photos/     brand photography
    videos/     reels / video
    logos/      logo + icon assets
    fonts/      font files
  brand/        analysis.json, data_tables.md, asset_manifest.json, stylesheets
```

### Scrapling notes / gotchas learned

- `network_idle` is a **bool**, not an int (`network_idle=2` → `TypeError`).
- The `Response` object **is** a Selector. It has `.css()` / `.xpath()` / `.find()`;
  there is **no** `.css_first()`. Use `page.css("title::text")[0]`.
- `Response` has **no `.evaluate()`** — all DOM reads must happen inside
  `page_action`, where the live Playwright page still exists, and be handed back
  through a closure dict.
- `solve_cloudflare=True` costs ~90 s per protected page but does defeat
  DoorDash, Uber Eats and Untappd.
- `page_setup` runs **before** navigation (register the wire listener there);
  `page_action` runs after load (scroll + interact + harvest there).
- Set `disable_resources=False` when capturing media, or images/video are dropped —
  and Canva's document viewer will render nothing at all.
- "Execution context was destroyed, most likely because of a navigation" means the
  page redirected mid-harvest. Settle with `wait_for_load_state` and retry in a loop.
- Windows consoles default to cp1252 and crash on `\u2060` scraped from menus —
  `brandlib.log()` now degrades to `replace`.
- Instagram/Facebook real post images live on **`*.fcrk1-*.fbcdn.net` at ≥1350 px**;
  the `scontent.cdninstagram.com` 507–640 px images are repeating sidebar
  "suggested posts". A naive `host.startswith("scontent")` test keeps the wrong ones.
- Instagram/TikTok video streams are `blob:` URLs until playback starts — call
  `.play()` on the element and capture the wire, or you get posters only.
- TikTok: direct HTTP on a video page returns a 1.5 KB stub. Stealth Chromium
  renders ~670 KB with a signed `playAddr`. TikTok then **rate-limits hard** —
  only the first request succeeds.

---

## 4. Official menu (Canva, design DAHAU38TVeA)

Captured as rendered viewer text across both pages → `research/brand/official_menu.json`

**Sections:** Barrel Bites · Meat Combos · Rustic Favorites · Side Selections ·
Rustic Sandwiches · Fresh Greens · Little Barrels · Cold Beverages · Freestyle Picks

### ⚠ The menu sells no beer

The Cold Beverages list is **Coca-Cola, Diet Coke, Dr Pepper, Sprite, Squirt,
Lemonade, La Croix, Apple Juice, Root Beer** — every one $3 (La Croix $2).
There is **not a single beer on the menu**, at a venue whose own categories are
"Beer Bar · Sports Bar" and whose Untappd page lists 17 craft beers.

This is the single biggest commercial/brand inconsistency found.

### Price integrity vs DoorDash

`research/brand/price_diff.json` — 22 matched items, average **+3.3%** on
DoorDash (a standard commission pass-through, consistent at ~4.2% on nearly
everything). Outlier: **Garden Wrap is +19.1%** ($14 → $16.67). Apple Juice is
-30.7% ($3 → $2.08), likely a different size.

### Other menu notes

- Prices are **cash prices**: *"Listed prices reflect cash amount. Card
  transactions will include applicable processing fees."*
- Two Instagram handles printed on the menu: `@The_Rustic_Barrel_` and
  `@TheRusticBarrel831`.
- Typos to correct: *"Pepperoncini's"*, *"juicy bite."* (orphan fragment),
  *"and"* for *"n"*, *"complimented"* (should be *complemented*).
- Address here is correct — **CA**, unlike the comedy flyer.

---

## 5. Untappd — beer evidence

`research/brand/beer_list.md` · venue `/v/the-rustic-barrel/13736755` · category **BBQ Joint**

- **17 beers** logged, ABV **4.5–10.5%**, median **6.2%**
- Breweries are heavily **Northern/Central California craft**:
  Russian River (5), Firestone Walker (3), Alvarado Street (3), Altamont (2),
  2 Towns Ciderhouse (2), Fieldwork, Dust Bowl
- Styles: American (8), Fruited (3), New England/Hazy IPA (2), Vienna,
  Apfelwein, Mexican, Other Fruit
- **Two ciders present** — notable for a venue branded as a beer bar

> Caveat: Untappd lists patron-*logged* beers, not the official tap list. It is
> strong evidence of positioning, not an authoritative pour list.
