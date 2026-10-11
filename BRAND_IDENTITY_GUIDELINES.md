# The Rustic Barrel Taphouse
## Brand Identity Guidelines

**Prepared:** 11 October 2026
**Method:** Full crawl of every public touchpoint using Scrapling (stealth Chromium + TLS impersonation), including wire-level asset capture, DOM/computed-style analysis, per-pixel palette extraction, and an **authenticated Yelp session**.
**Asset library:** `research/media/brand_marks/` (118 files) · `research/media/brand_library/` · review via `research/brand/contact_sheet.html`

---

## 0. Executive summary

### The vibe, in one line

> **A modern sports bar with a Western soul.**

Their *room* is a contemporary, family-friendly sports bar — TV wall, multi-tap,
Connect Four, grey vinyl plank, charcoal drop ceiling. Their *marketing* is 1890s
Western Americana — charred oak, barrel hoops, wood-type, bone lettering. **That
gap is the opportunity, not the problem.** Every neighbouring sports bar looks
like the room. The rustic brand is the only reason anyone remembers this one.

Full assessment, including the five vibe words and the anti-vibes:
**`BRAND_VIBE.md`**

The Rustic Barrel has a **genuinely strong, coherent visual identity** — and almost none of it is usable, owned, or consistent.

Every design decision that matters lives inside flat images the team makes by hand: a barrel-head logo with a wheat laurel, Western wood-type lettering, cream on midnight navy, oxblood and amber, parchment nailed to charred oak. It is warm, hand-made, unmistakably American, and it works.

The problem is that **none of it exists outside those images**. Our computed-style analysis across all channels returned:

- **Typography:** Times New Roman, DD Norms, Segoe UI Historic, UberMoveText, Arial. Every one is a platform default. **The brand owns no typeface.**
- **Colour:** `#191919`, `#606060`, `#1c1e21`, Facebook link blue `#0866ff`, DoorDash blue `#0064d1`. Every one belongs to somebody else. **The brand owns no colour.**
- **Logo:** no vector, no SVG, no favicon, no brand page. **The brand owns no logo file.**
- **Website:** none. `therusticbarrel.com` is a parked domain (a 151-byte JS lander); `rusticbarrel.com` is for sale on a domain broker.

So the identity is real but **entirely rented and entirely un-tokenised**.

### The Linktree is the real index

The Instagram bio points to `linktr.ee/therusticbarrel_831`, and it is the **only place the business publishes its own links**. Following it was the highest-value move of this project — it exposed four channels invisible from everywhere else:

| Link | What it revealed |
|---|---|
| **Canva menu** | The **actual two-page menu** — 32 dishes, descriptions, cash pricing |
| **Untappd** | A **17-beer** California craft programme that appears nowhere else |
| **TikTok** | A **second, separate video channel** — 70 posts we had never seen |
| **Google Review** | The listing customers actually rate |
| **Contact Us** | ⚠ **Configured but completely empty — no email, no phone** |

### Five things the crawl found that need fixing

1. **The menu sells no beer.** Cold Beverages is Coke, Sprite, Dr Pepper, Squirt, Lemonade, La Croix, Apple Juice, Root Beer — all $3. Not one beer, at a venue whose own categories are *Beer Bar · Sports Bar* and whose Untappd lists 17 craft beers.
2. **"King City, GA"** on the comedy flyer. King City is in **California**.
3. **DoorDash marks up ~4.2%** on nearly everything, and **Garden Wrap by 19.1%** ($14 → $16.67).
4. **Closed Tuesdays** on Yelp — the one day the menu and socials never mention.
5. **Two Instagram handles in circulation** — `@the_rustic_barrel_` and `@the_rustic_barrel831`, both printed on the menu.

**The single highest-value action:** secure the domain, get a vector logo, and adopt one typeface and one colour system. Everything else in these guidelines is secondary to that.

---

## 1. Business facts (scraped, not assumed)

| Field | Value | Source |
|---|---|---|
| Trading name | The Rustic Barrel | Yelp JSON-LD |
| Full name used on logo | **The Rustic Barrel Taphouse** | Logo lockup, Instagram |
| Categories | Beer Bar · Sports Bars · Sandwiches · Restaurants Open Late | Yelp |
| Address | 611 Canal St, King City, CA 93930 | Yelp + DoorDash JSON-LD |
| Coordinates | 36.202538, −121.12799 | DoorDash JSON-LD |
| Phone | (831) 601-1397 | Yelp + menu |
| Email | therusticbarrel831@gmail.com | Client brief |
| **Rating** | **4.6 / 5** | Yelp JSON-LD |
| **Reviews** | **59** | Yelp JSON-LD |
| **Price range** | **$$** | Yelp |
| Instagram | /the_rustic_barrel_ — 12 posts, 4 reels | — |
| TikTok | /therusticbarrel831 — **70 posts** | Linktree |
| Facebook | /therusticbarreltaphouse | — |
| Untappd | /v/the-rustic-barrel/13736755 — "BBQ Joint" | Linktree |
| DoorDash | /store/the-rustic-barrel-king-city-34689489 | — |
| Uber Eats | /store/the-rustic-barrel/j50H6Tr2W… | — |
| Linktree | /therusticbarrel_831 | Instagram bio |
| Yelp | /biz/the-rustic-barrel-king-city-2 | **403 anonymous — via logged-in session** |
| Owned website | **none** | Domain probe |

### Opening hours (Yelp, authoritative)

| Day | Hours |
|---|---|
| Monday | 11:30 am – 9:00 pm |
| **Tuesday** | **Closed** |
| Wednesday | 11:30 am – 9:00 pm |
| Thursday | 11:30 am – 9:00 pm |
| Friday | 11:30 am – 9:00 pm |
| Saturday | 12:00 pm – 9:00 pm |
| Sunday | 12:00 pm – 8:00 pm |

> A 9 pm close, five days a week, is a genuinely late venue — but **"closed Tuesdays" appears nowhere** on the menu, the flyers or the socials. Customers arriving on a Tuesday will find nothing.

### ⚠ Live brand errors to fix

| # | Error | Where |
|---|---|---|
| 1 | **"611 Canal St. King City, GA"** — it's California | Comedy Night flyer |
| 2 | **"Contact Us" block is empty** | Linktree |
| 3 | **Two different Instagram handles** printed together | Official menu |
| 4 | *"Pepperoncini's"*, *"and"* for *n*, *"complimented"* for *complemented* | Official menu |
| 5 | Orphan fragment *"juicy bite."* rendered as its own line | Official menu |
| 6 | Comic flyer advertises **@laughingboothcomedy**, not the venue | Comedy flyer |
| 7 | **Garden Wrap listed 19.1% above menu price** | DoorDash |

> The menu itself states: *"Listed prices reflect cash amount. Card transactions will include applicable processing fees."* — a cash-pricing practice worth keeping in writing on the menu board.

---

## 2. Brand character

### The one-line position

> **A King City taphouse where Central Coast barbecue, cold beer and neighbourly chaos meet.**

### Personality axes

| Axis | They are | They are not |
|---|---|---|
| Warmth | Welcoming, hand-made, neighbourly | Corporate, scalable, franchisable |
| Energy | Loud, late, festive | Minimal, curated, precious |
| Craft | Smoked, seared, made in-house | Sourced, plated, chef-driven |
| Heritage | Rustic, Americana, Western | Minimal, Nordic, urban-chic |
| Price posture | Accessible ($15.63 median) | Premium, tasting-menu |

### Voice

Their menu copy is their best-written brand asset and it is consistent. Analysed across **63 items, ~21.5 words per description**, the dominant vocabulary is:

> cheese, fries, sauce, golden, onions, layered, bread, made, bun, crispy, house, beef, american, burger, bbq, drizzled, chicken, grilled, brioche, pulled, tri-tip, toasted, meat, fresh

Four rules fall out of it:

1. **Texture first, provenance second.** "Golden crisscut fries", "melted cheese", "crispy". The food is described by how it *feels*.
2. **Process words carry the craft.** "smashed & seared to perfection", "slow smoked", "house-made", "fresh chopped". Method is the value claim.
3. **Regional specificity is a feature.** "Santa Maria Style Tri-Tip" is the single most localising phrase on the menu and should be a brand asset, not an accident.
4. **Punctuation is loose, voice is confident.** "&" for "and", missing apostrophes ("complimented"), capitalised adjectives ("American cheese", "BBQ"). House style — keep it, but fix the apostrophes.

**Voice rules:** write in the present tense, lead with texture, name the method, use "&", never say "premium" or "elevated", never use food-blog minimalism.

---

## 2b. The menu (official Canva menu, design `DAHAU38TVeA`)

Recovered in full — both pages, 383 lines, 32 dishes.

**Sections:** Barrel Bites · Meat Combos · Rustic Favorites · Side Selections · **Rustic Sandwiches** · **Fresh Greens** · **Little Barrels** · Cold Beverages · Freestyle Picks

| Section | Items | Price band |
|---|---|---|
| Meat Combos | One / Two / Three Meat Combo | $25 · $30 · $40 |
| Rustic Favorites | O.G. Smash Burger, Rustic Burger, Smash Burger Deluxe, Barrel Fries, Loaded Barrel Fries, Hot Daddy Fries, Mac Daddy Fries | $14–$30 |
| Barrel Bites | Chicken Wings (5 sauces), Cowboy Candy | $10 · $16 |
| Rustic Sandwiches | Tri-Tip, Pulled Pork, BBQ Chicken, Chopped Brisket, **Chimi Tri-Tip** | $22 · $24 |
| Fresh Greens | Fresh Chopped Salad, Garden Wrap | $14 · $20 |
| Little Barrels | Lil' Grilled Cheese, Lil' Smash Burger | $16 · $17 |
| Sides | Fries, Onion Rings, Small Salad, Side of Meat, Mac n' Cheese | $7–$12 |

Proteins: **Brisket · Pulled Pork · Pork Ribs · Tri-Tip · Chicken.** Wings sauces: **Buffalo · BBQ · Sweet Chili · Garlic Parmesan.**

### ⚠ The menu sells no beer

Cold Beverages is *Coca-Cola, Diet Coca-Cola, Dr Pepper, Sprite, Squirt, Lemonade, La Croix, Apple Juice, Root Beer* — nine items, all $3 (La Croix $2). **There is not a single beer on the menu.**

Set against a venue categorised as **Beer Bar**, an Untappd page listing 17 craft beers, and a customer photo captioned *"Lots of tap beers!!"* — this is the brand's defining asset being left off its own menu.

### Price integrity vs DoorDash

`price_diff.json` — 22 matched items, average **+3.3%** on DoorDash. That is a standard commission pass-through and is consistent at ~4.2% on nearly every line. Two outliers look like data-entry errors:

| Item | Menu | DoorDash | Delta |
|---|---:|---:|---:|
| **Garden Wrap** | $14 | $16.67 | **+19.1%** |
| Apple Juice | $3 | $2.08 | **−30.7%** |

---

## 2c. The beer programme (Untappd)

Venue `/v/the-rustic-barrel/13736755` — categorised by Untappd as **BBQ Joint**. 17 beers logged.

- **ABV 4.5 – 10.5%, median 6.2%**
- Breweries are overwhelmingly **Northern/Central California craft**:
  **Russian River (5)** · **Firestone Walker (3)** · **Alvarado Street (3)** · Altamont (2) · 2 Towns Ciderhouse (2) · Fieldwork · Dust Bowl
- Styles: American (8), Fruited (3), New England/Hazy IPA (2), Vienna, Apfelwein, Mexican, Other Fruit
- **Two ciders** — notable for a venue branded as a beer bar

Firestone Walker (Paso Robles) and Russian River (Sonoma) are genuinely premium CA craft houses. **This is a sophisticated pour programme being marketed as a generic beer bar.** Nothing in the current branding communicates it.

> Caveat: Untappd lists patron-*logged* beers, not the official tap list. Treat as positioning evidence, not a pour sheet.

---

## 2d. Customer voice (Yelp, authenticated session)

**4.6 / 5 from 59 reviews**, price range **$$**. Thirty-one customer photographs were recovered at original resolution with their captions — the closest thing to unsolicited brand research that exists.

Captions confirm the positioning customers actually hold:

> *"Lots of tap beers!!"* — Mike W., ★5
> *"Sneak peek of our Santa Maria Styled Tri-Tip"* — ★5
> *"Sweet chili chicken wings"* · *"The Rustic Burger, two angus beef patties"*
> *"Come in and enjoy sum run"*

Three things customers say that the brand never says itself: **the beer**, **the Santa Maria tri-tip**, and **the wings**. All three belong in the brand line.

---

## 3. Logo system

### The mark

A **circular barrel-head badge**:

- Charred oak stave disc with two hoop bands
- Arched Western wood-type lettering — **THE** / **RUSTIC BARREL** / **TAPHOUSE**
- **Wheat-and-barley laurel** rising on both lower sides
- Bone/cream letterforms on the dark barrel

It appears in at least three treatments, all of which should be formalised:

| Treatment | Where it's used | Status |
|---|---|---|
| Full badge on dark barrel | Primary flyers, barrel prop | **Primary** |
| Barrel badge burned onto a 3D barrel | Private-event flyer | Accent / environmental |
| Circular badge with wheat laurel, arched type | Labor Day closure flyer | **Primary (simplified)** |

### The mark as icon

The wheat laurel alone, or the barrel hoop ring, works as an avatar/favicon. **No such asset currently exists** — their social avatars are generic platform defaults.

### The barrel wordmark

A second, looser lockup — "RUSTIC BARREL" arched over a barrel hoop with a hop cone and barley sprigs, on wood grain — appears on the Chili Cheese Flyer. It is *not* the same as the badge and is missing the "Taphouse" line. **Pick one primary and retire the other.**

### Clear space & minimum size

Not currently defined. Specified:

- **Clear space** = the height of the word "RUSTIC" on all four sides. Nothing enters it.
- **Minimum width** = 120 px digital / 30 mm print. Below that the wheat laurel fills in — drop to the laurel-only icon.
- **Never** recolour, add effects, outline, or place the badge on a busy photo without a solid panel behind it.

---

## 4. Colour

Extracted by pixel-quantising the six designed flyers, not by eyeballing.

### Primary palette

| Role | Name | Hex | Where |
|---|---|---|---|
| **Core dark** | Charred Oak | `#1F1610` | Dominant ground — 33–56% of every flyer |
| **Primary light** | Bone | `#F3EAD9` | All type on dark; parchment surface |
| **Secondary dark** | Barrel Navy | `#151B25` | Panels, ribbons, secondary headlines |
| **Warm mid** | Weathered Wood | `#8B5633` | Plank grounds, rules, texture |

### Accent palette

| Role | Name | Hex | Where |
|---|---|---|---|
| **Accent 1** | Amber Gold | `#ED9F0F` | Chili-cheese focal, availability, price |
| **Accent 2** | Oxblood | `#6B1F1F` | "OPEN", urgency, sold-out, closures |
| **Accent 3** | Burnt Amber | `#A25713` | Deep warm, secondary fills |
| **Accent 4** | Brass | `#B08B54` | Rules, badge borders, small metal cues |
| **Support** | Barley | `#D3B48D` | Parchment mid-tone, dividers |
| **Support** | Hop Green | `#4A6B2A` | Beer/lager references only |

> **Brass `#B08B54` is an addition, not an invention.** It is the colour that
> recurs most in both their own photography and every top-scoring reference —
> it reads as the metal of the barrel hoops and the tap handles, and it gives
> the cream-on-charcoal pairing something warm to land on without going neon.

### Rules

- **Bone on Charred Oak** is the house pairing and must always clear **7:1** contrast.
- **Amber Gold is an accent only** — never a background behind body text (`#ED9F0F` on `#F3EAD9` fails WCAG AA).
- **Oxblood and Amber never sit adjacent** at full saturation; separate with Bone or Navy.
- Photography may shift these freely — the palette governs **designed surfaces**, not plates of food.
- **Print:** use the Pantone bridge below, and specify **no metallic ink**. The rust reads through texture, not shine.

| Hex | Closest Pantone | Closest CMYK |
|---|---|---|
| `#1F1610` | Black 6 C | 60 / 65 / 70 / 70 |
| `#F3EAD9` | 9223 C | 4 / 6 / 14 / 0 |
| `#151B25` | 432 C | 78 / 62 / 45 / 35 |
| `#8B5633` | 7533 C | 52 / 68 / 78 / 30 |
| `#ED9F0F` | 1375 C | 10 / 35 / 92 / 0 |
| `#6B1F1F` | 504 C | 45 / 95 / 92 / 45 |

---

## 5. Typography

### The problem

**There is no brand typeface.** Computed styles across all channels returned only platform defaults:

| Family | Where | Verdict |
|---|---|---|
| Times New Roman | DoorDash | Platform default |
| DD Norms | DoorDash | *DoorDash's* brand font |
| Segoe UI Historic | Facebook | OS system font |
| UberMoveText | Uber Eats | *Uber's* brand font |
| Arial | DoorDash | Fallback |

The identity's type lives only inside the flyer images. It is a **Western wood-type / saloon** system. Below is the hierarchy read off those flyers, with free equivalents.

### Type hierarchy

| # | Role | Style observed | Free equivalent | Use for |
|---|---|---|---|---|
| 1 | **Wood-type display** | Arched Western slab with spur serifs, distressed | **Rye** (Google Fonts) | "OPEN", "CLOSED", dish names, event titles |
| 2 | **Condensed slab caps** | Tall, slightly western, letterspaced | **Bevan** or **Alfa Slab One** | "WE WILL BE", "AUGUST 15TH", subtitles |
| 3 | **Brush script** | Loose hand-brush, casual | **Kaushan Script** | "Saturday,", "Thank you", one-line asides |
| 4 | **Plain sans** | *Does not exist yet* | **Barlow** | Body, menus, legal, web UI |

### Hierarchy rules

- **Display only.** Roles 1–3 are for posters, social, menus, signage. **Never** in body copy or UI.
- Rye is a display face — set it **large**, all caps, with generous tracking. It is illegible below ~24 px.
- Script is a seasoning, not a voice: **one line per composition**, never two.
- Body copy is Barlow Regular 400/600. This is the face that has to exist, because nothing plays that role today.
- **Letter-spacing** on caps: +2 to +4 %. The flyers read as hand-spaced and that is deliberate.
- **Distress is texture, not a filter.** Reproduce it with real texture overlays or a worn-ink font variant — never a drop-shadow or bevel.

### Recommended stack

```
Display:   Rye, 'Rye Fallback', serif
Subhead:   Bevan, Georgia, serif
Script:    'Kaushan Script', cursive
Body:      Barlow, -apple-system, 'Segoe UI', sans-serif
```

> This stack is now validated against the qualified references in §6b — every
> top-scoring shot uses the same three-role western type mix (slab display +
> condensed caps + script accent) on a dark ground.

---

## 6b. Design direction — qualified references

**We did not invent this look. We selected it.** 267 shots across 12 Dribbble
searches were captured and scored against the eight criteria in `BRAND_VIBE.md`.
**50 qualified (4+), 8 top-tier (5+).**

Open `research/reference/shortlist.html` to review all 50 with their criteria
marked. Full scoring in `research/reference/qualified.json`.

### Score distribution

| Score | Shots | |
|---|---:|---|
| 5 (top) | 8 | strongest alignment |
| 4 | 42 | qualified |
| 3 | 70 | adjacent — partial hits |
| 2 | 86 | generic |
| 1 | 48 | off-brief |
| 0 | 9 | wrong entirely |

### The five that define the direction

**1. Diamond Ridge Provisions — Modern Western Branding** *(score 4)*
**The single best match, and effectively a ready-made answer to this brief.**
Charcoal ground with a subtle topographic-contour texture; cream type with a
single **brass/gold** accent; western script wordmark paired with condensed
western caps; rope-and-star border; circular **monogram badge**; shield lockup;
ribbon banner. Contemporary, warm, unmistakably Western — and nothing like
country-kitchen kitsch.
→ *Adopt this structure: one dark ground + one cream + one brass accent + one script + one condensed slab + badge-and-ribbon devices.*

**2. The Wild — Brand Identity, Vinyl Sign & Space** *(score 4)*
An **arched western serif** "THE WILD" over an arched subline, with line-art
beverage icons between, applied as vinyl on glass. Structurally this is
**the same idea as the Rustic Barrel barrel badge** — arched type, circular
composition, centred icon, cream on dark — executed with far more restraint.
→ *Confirms the barrel badge is correct. Keep the structure; strip the distress and the barrel-photo texture.*

**3. The Wild — Brand Identity System & Brand Elements** *(score 5)*
The full system: wordmark, monogram, collateral, menu. Confirms a Western brand
can run a complete, disciplined identity system rather than a single logo.
→ *The model for §7 — one system, six applications.*

**4. Betty's Bar and Grill Signage** *(score 4)*
Cream ground, heavy condensed type, western register. Useful as the **light-side
inverse** of the palette for menus and daylight signage.

**5. Rustic Brand Identity Set** *(score 4)*
The literal reading of "rustic" — confirms what we are *not* choosing, and why.

### Also worth holding

| Shot | Use it for |
|---|---|
| **High Spirits Milano — 360° branding** *(5)* | Dark ground + warm accent at 85% coverage — proof the dark end works at scale |
| **Shaddok — American IPA** *(4)* | Beer label architecture for the Untappd pour programme |
| **Hõlu — craft beer packaging** *(4)* | Craft-beer hierarchy without going precious |
| **Tennis Club — sports branding** *(5)* | The sports-bar half of the venue, done with taste |
| **Sunlitora / Vineyard wine bar** *(4)* | Bar identity with a tighter, more premium palette |

### What the shortlist says, in one line

> **Dark ground. Cream type. One metal or warm accent. Western slab caps, one
> script, nothing else. Badge and ribbon as the only structural devices.**

That is a *simpler* system than what the team makes by hand today — and it is
the same idea, cleaned up.

---

## 6. Visual language & art direction

### Materials

The identity is **material-first**: charred oak, barrel staves and hoops, aged parchment, rusted steel, rope, wheat and hops. Every hero surface should read as a photographed object, not a drawn background.

### Recurring devices (all already in use — codify them)

| Device | Description |
|---|---|
| Ribbons & banners | Navy or oxblood swallowtail banners behind a line of type |
| Stars | Five-point, cream or navy — used as bullets, dividers, corner marks |
| Laurel / wheat | Always paired with hop cones |
| Sunburst rays | Radiating tick marks for emphasis and "available until" |
| Rope rules | Barbed-rope-with-centre-star dividers |
| Hanging sign | Script on a plank with visible nail holes |
| Barrel hoop arcs | Curved baselines for wordmarks |

### Photography

Current direction (from the DoorDash album, 97 frames):

- **Warm, dim, tungsten-warm.** The strongest frames are lit warm against dark wood.
- **Overhead or 45° hero shots**, shallow-ish depth, food filling 60–80% of frame.
- **Visible texture** — checkered deli paper, wood grain, metal trays.
- **Hands and beer in frame** create the "bar" read; pure plate shots don't.
- Patented colours cluster in the amber/wood band (`#B08B54`, `#9B5E1F`, `#6C4F29`, `#DC7320`) — this is the *photographic* palette and it should sit beside, not replace, §4.

**Gaps to fix:** the album mixes in DoorDash-sponsored creative (Michelob Ultra and similar), so some frames currently on their storefront are **not their photography**. Establish a clean, owned library.

### Graphic texture

- Wood grain at 8–15% opacity behind flat colour fields
- Parchment at 4% over dark grounds for warmth
- Never use both textures in one composition
- Always keep type ≥ 60% of the frame's visual mass

---

## 7. Applications

### Social

| Platform | Format | Type |
|---|---|---|
| Instagram feed | 1080×1350 (4:5) | Rye hero + Bevan subhead + Kaushan accent |
| Instagram story | 1080×1920 | Single message, huge display type |
| Instagram reel cover | 1080×1920 | High-contrast Bone-on-Navy, legible at thumbnail |
| Facebook cover | 820×312 | Barrel mark left, Bone type on Charred Oak |
| Event poster | 18×24 in | Full system; Bone ground, oxblood hero word |

Feed posts run 1350–2069 px in their existing archive — **keep posting at ≥1350 px**; the current library is genuinely usable.

### Print / signage

- Bone text on Charred Oak, or Charred Oak on Bone — never Bone on Wood *photography*
- Minimum 24 pt for Rye; 14 pt for Bevan; 9 pt for Barlow
- Weather-proof stock for exterior; the palette is already outdoor-legible at distance

### Digital (to be built)

- Bone `#F3EAD9` on Charred Oak `#1F1610` as the default surface — it passes AA at body sizes
- Amber Gold strictly for CTAs and active states
- Barlow throughout
- Rye only ≥ 32 px with tracking

---

## 8. What has to be built

Ordered by impact. Items 1–3 are the ones that actually protect the brand.

### 1. Secure and build a domain *(critical)*

`therusticbarrel.com` is **parked and available to a third party** — anyone can register it and impersonate the venue. `rusticbarrel.com` is listed for sale. Register both defensively, redirect to whatever you build, and enable auto-renew + registry lock.

### 2. Produce a real logo kit

There is no vector logo anywhere in their digital presence — only baked-in pixels. Commission from the existing mark:

- `logo-primary.svg` — barrel badge, full colour
- `logo-primary-mono.svg` — Bone on transparent
- `logo-badge.svg` — simplified, no "Taphouse"
- `laurel-icon.svg` — avatar / favicon
- `logo-1-colour.svg` — single-ink for stamps, embroidery, receipts

Resolve the **barrel-badge vs barrel-wordmark** conflict first; pick one primary.

### 3. License and formalise the type

Rye / Bevan / Kaushan Script / Barlow are all free — ship them as a documented kit and ban Times New Roman, DD Norms and UberMove from anything client-facing.

### 4. Put beer on the menu *(commercial, not cosmetic)*

A venue whose categories are *Beer Bar · Sports Bar*, whose Untappd lists 17 California craft beers, and whose customers post *"Lots of tap beers!!"* — sells **nine soft drinks and no beer** on its menu. The beer programme is the brand's single strongest differentiator and it is invisible to anyone reading the menu.

This is the highest-margin, lowest-effort change in this document. Add a pours page: house taps, guest taps, ciders, and a rotating seasonal line — in the brand palette, on the brand layout.

### 5. Build the token file

A single `tokens.json` + CSS custom-properties file carrying §4 and §5, so every future surface is generated from one source rather than rebuilt by hand each time.

### 6. Produce the social template set

Six post templates (dish, event, hours, closure, sports-night, offer) in Canva **or** Figma with locked type and palette. The hand-made flyer look is a strength — but it currently costs hours per post and produces the "GA" error.

### 7. Correct the errors in market

The seven-item error list in §1. The "GA" spelling, the empty Contact Us block and the dual Instagram handles are the three that cost trust fastest.

### 8. Reconcile platform pricing

DoorDash carries ~4.2% over cash menu price on nearly every line, which is normal commission pass-through — but **Garden Wrap is +19.1%** and Apple Juice is −30.7%. Audit the whole catalogue; those two look like data-entry errors rather than deliberate margin.

### 9. Own an owned channel

Every current touchpoint is a rented one — and a marketplace page can change its fonts, colours and layout without notice (this document caught exactly that happening). A simple one-page site or a well-maintained Google Business Profile breaks that dependency. Fill the empty Contact Us block today.

---

## 9. Evidence & limitations

**Fully captured:** Instagram (12 posts, 4 reels, 40 images, 15 video files) · Facebook (27 assets) · DoorDash (322 assets + 63-item marketplace menu) · Uber Eats (8 assets) · **Linktree (7 links → 4 new channels)** · **Canva official menu (both pages, 383 lines, 32 dishes)** · **Untappd (17 beers)** · **Yelp via authenticated session (4.6★/59 reviews, hours, 31 customer photos)** · **TikTok (70 post URLs + captions)**. Palette extracted per-pixel via Pillow quantisation over 108 curated brand frames.

**Partial / not captured:**

- **Yelp review *text*** — Yelp lazy-loads the review feed; 17 review objects are present but only the structured facts and photo captions were recovered. The 4.6 rating and 59 count are exact. Review bodies need one paginated pass or a manual pull.
- **TikTok video files** — all 70 post URLs and captions were recovered, but TikTok rate-limited after the **first** download. Only 1 video file was retrieved. A slower, paced run (or authenticated session) would finish this.
- **Menu item photography** — DoorDash gates its menu behind a delivery-address check, so item→image mapping never rendered. Menu *content* came from the official Canva menu and JSON-LD; menu *imagery* is from the store album and still needs a human pass to separate genuinely-shot dishes from DoorDash-sponsored creative.
- **Untappd** lists patron-*logged* beers, not the official tap list — strong positioning evidence, not an authoritative pour list.
- Reel audio was not retained; video files are as delivered by each platform's CDN.
- 26 of the 31 Yelp photos were below the 500 px curation floor; 5 were retained in the library.

**Data tables:** `research/brand/data_tables.md` · `beer_list.md` · `official_menu_lines.txt`
**Analysis:** `analysis.json`, `brand_data.json`, `curated_library.json`, `official_menu.json`, `price_diff.json`, `yelp_parsed.json`, `tiktok.json`
**Contact sheet:** `research/brand/contact_sheet.html`
**Pipeline notes & Scrapling gotchas:** `RESEARCH_NOTES.md`
