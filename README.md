# The Rustic Barrel Taphouse

Brand identity and website for The Rustic Barrel, 611 Canal St, King City, California.

Static site, no framework, no build step on deploy, no third-party JavaScript,
no analytics. 5 pages, 10.9 MB of assets, ~57 KB of first-party CSS and JS.

## Repo layout — read this first

```
index.html  menu.html  beer.html  events.html  visit.html  404.html   <- Vercel serves these
assets/                                                            <- generated
robots.txt  sitemap.xml  site.webmanifest  _redirects  vercel.json
site/          <- CANONICAL SOURCE. Every generator writes here.
scripts/       <- the generators and the gates
docs/          <- PRD, TRD, architecture, system flow, plan, SEO checklist
research/      <- parsed source data (JSON only; media is gitignored)
README.md .gitignore .sync-manifest.json                            <- hand-written
```

**The site exists twice on purpose, and that is policed.**

Vercel serves the repo root. The generators write to `site/`. So `site/` is the
source of truth and the root is a mirror produced by:

```bash
python scripts/sync_root.py          # copy site/ to the root
python scripts/sync_root.py --check  # exit 1 if they have drifted
```

Run `--check` before every commit. Without it the arrangement rots quietly: you
regenerate, push without re-mirroring, and the live site serves last month's
markup while the repo's own `site/` says otherwise. `scripts/deploy_prep.py`
runs the generators, the mirror and every gate in the right order.

## Build

Needs Python 3.11+ and the packages in `requirements.txt`.

```bash
python -m venv .venv && .venv\Scripts\activate     # Windows
pip install -r requirements.txt
python scripts/deploy_prep.py                      # regenerate + gate + mirror
```

Individual steps, in dependency order:

| Script | Does |
| --- | --- |
| `extract_logo.py` | crops the real logo out of the marketplace cover, emits light and Charred-Oak variants |
| `build_hero.py` | picks the hero room shot, builds responsive WebP + the blurred base layer |
| `build_card_art.py` | square-crops the three feature-badge photos |
| `build_site.py` | `tokens.json` → `tokens.css`, image variants, sitemap, robots, `_redirects` |
| `build_pages.py` | generates menu / beer / events / visit / 404 from the shared shell |
| `sync_root.py` | mirrors `site/` to the repo root for Vercel |

Some of these need the scraped originals in `research/media/`, which is
gitignored at ~1 GB. A fresh clone can rebuild the *pages* from
`research/brand/*.json`; rebuilding the *images* needs the originals re-fetched.

## Gates

All exit non-zero on failure. `deploy_prep.py` runs all of them.

| Script | Checks | Currently |
| --- | --- | --- |
| `validate_seo.py` | titles, descriptions, h1s, canonicals, OG, JSON-LD, sitemap, robots, internal links, asset existence, CSS `var()` resolution, void-element misuse | 9 passed, 0 warnings, 0 failures |
| `audit_contrast.py` | rendered WCAG AA contrast, in a real browser | 244 elements pass |
| `audit_hero_contrast.py` | hero text contrast sampled from actual screenshot pixels | worst case 59.66:1 |
| `check_overflow.py` | horizontal overflow and header collision at 9 widths | 0 at 1440/1280/1024/768/414/390/375/360/320 |
| `check_images.py` | every image actually decodes, before and after scroll | 8/8 |
| `find_dead_space.py` | tall empty containers that hold a page open | 0 on all 6 pages |
| `test_void_elements.py` | self-test for the void-element rule | 14/14 |
| `sync_root.py --check` | root mirror matches `site/` | in sync |

`shot.py` captures screenshots, with `--full` and `--scroll <px>`. `--full`
walks the page before capturing: a `full_page` screenshot goes through CDP
`captureBeyondViewport`, which resizes the surface without scrolling and so
never paints `loading="lazy"` art — the result looks like a hole in the layout
that isn't there.

## Deploying to Vercel

Live at **https://rusticbarreldemo.vercel.app**.

Import the repo. No build command, no output directory, no framework preset —
the root *is* the static site, so Vercel's zero-config serves it as-is.

URLs are extensionless: `/menu`, not `/menu.html`. `site/vercel.json` sets
`cleanUrls`, which serves `/menu` from `menu.html` and 308s `/menu.html` to
`/menu`. Canonicals, the sitemap and every internal link use the clean form, so
the site never advertises two URLs for one page.

The canonical origin is the demo host, set once in
`site/assets/tokens.json` → `seo.canonicalBase`. **When the real domain is
registered**, change `canonicalBase` and `primaryDomain`, set
`redirectNonWwwToWww` back to `true`, and rebuild — `build_host_config()`
restores the www 301 in both `vercel.json` and `_redirects` automatically.
Do not hand-edit a canonical; `validate_seo.py` now fails the build if any
page's canonical does not match the configured origin and clean path, which is
how the home page's hand-written head was caught pointing at the old domain
after five generated pages had already moved.

## Known issues, in the client's court

- **Domain not owned.** `therusticbarrel.com` is still parked and purchasable,
  and `rusticbarrel.com` is on a broker. Everything in
  `docs/SEO_LAUNCH_CHECKLIST.md` that needs a live host or a Google account is
  blocked until it is registered.
- **The Chili Cheese Fries artwork is a dated flyer** — it reads "THURSDAY
  OCTOBER 1ST" and that date has passed. It sits on a permanent page whose
  copy says the dish rotates weekly. Needs an undated replacement or removal.
- **Uber Eats `storeUUID` is a `{STORE_UUID}` literal** in the order CTA. It is
  not publicly derivable; the client fills it from the Merchant Portal.
  `deeplink.js` detects the placeholder and declines with an `aria-live`
  message rather than navigating somewhere broken.
- **The logo exists only at 440×230.** It was extracted from the DoorDash store
  cover — real artwork, cropped, never redrawn — but it is not a vector. A
  commission would fix the small-size legibility in the header.
- **The menu sells no beer** at a venue branded as a Beer Bar with 17 craft
  taps.

## Attribution

Photography is the venue's own, captured from its public listings. DoorDash and
Uber Eats wordmarks are the partners' trademarks, used to link to their stores.
Beer names belong to their brewers.
