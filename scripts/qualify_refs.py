"""
Phase 4b - Qualify the Dribbble references against the Rustic Barrel brief.

We are not inventing a look, we are selecting one. Each of the 267 captured
shots is scored against the eight criteria defined in BRAND_VIBE.md, half from
pixel analysis of the artwork itself and half from its own title/tags.

  C1 dark warm ground      C2 cream/bone type      C3 western/slab display type
  C4 hand-made texture     C5 Americana motifs     C6 bar/beverage context
  C7 warm accent colour    C8 contemporary execution

Threshold: 4+ qualifies. Ranked output feeds the shortlist in the guidelines.

Outputs: research/reference/qualified.json, shortlist.html
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image

import brandlib as bl
from analyze import hsl

REF = bl.RESEARCH / "reference"

# --- text signals ----------------------------------------------------------- #
WESTERN = re.compile(
    r"\b(western|saloon|cowboy|outlaw|sheriff|wild ?west|old ?west|western|"
    r"slab|wood ?type|woodtype|typewriter|franklin|spur|frontier|"
    r"wester(n)?|saddle|rodeo|cactus|horse|sheriff)\b", re.I)
TEXTURE = re.compile(
    r"\b(texture|grain|letterpress|hand ?drawn|hand ?made|handmade|craft|"
    r"kraft|distressed|grunge|rough|paper|parchment|analog|organic|"
    r"imperfect|artisanal|material)\b", re.I)
AMERICANA = re.compile(
    r"\b(american|america|usa|stars|star|heritage|vintage|retro|badge|"
    r"emblem|crest|shield|patch|nostalgic|establish|est\.?\s*\d{4}|"
    r"since \d{4}|classic|old ?school)\b", re.I)
BAR = re.compile(
    r"\b(bar|beer|brew|tap|pub|tavern|saloon|bottle|glass|stout|ale|ipa|"
    r"lager|pilsner|whisk(e)y|bourbon|cocktail|drink|beverage|pour|"
    r"bartend|nightlife|pub|restaurant|bbq|grill|steak|smoke)\b", re.I)
MODERN = re.compile(
    r"\b(modern|contemporary|clean|minimal|geometric|editorial|grid|"
    r"system|identity|brand ?guidelines|visual ?identity)\b", re.I)

NEGATIVE = re.compile(
    r"\b(neon|synthwave|vaporwave|cyberpunk|gradient mesh|glassmorphism)\b", re.I)


def pixel_scores(path: Path) -> dict | None:
    """Analyse the artwork itself: ground, cream, warm accent."""
    try:
        with Image.open(path) as im:
            im = im.convert("RGB")
            im.thumbnail((160, 160))
            q = im.quantize(colors=8, method=Image.Quantize.FASTOCTREE)
            pal = q.getpalette() or []
            counts = Counter(q.getdata())
    except Exception:  # noqa: BLE001
        return None

    total = sum(counts.values()) or 1
    dark_warm = cream = warm_accent = 0.0
    hues, sats, lights = [], [], []

    for idx, cnt in counts.items():
        rgb = tuple(pal[idx * 3: idx * 3 + 3])[:3]
        if len(rgb) < 3:
            continue
        share = cnt / total
        h, l, s = hsl(*rgb)
        hues.append(h); sats.append(s); lights.append(l)

        # C1 dark warm ground: dark AND warm-leaning (hue 0-60 or neutral brown)
        if l < 45 and (h <= 62 or s < 18):
            dark_warm += share
        # C2 cream / bone: light, low-sat, warm
        if l > 72 and s < 42 and 18 <= h <= 62:
            cream += share
        # C7 warm accent: saturated amber/oxblood/rust
        if s > 45 and 8 <= h <= 52 and 28 <= l <= 78:
            warm_accent += share

    mean_l = sum(lights) / len(lights) if lights else 50
    return {
        "mean_light": round(mean_l, 1),
        "dark_warm_share": round(dark_warm * 100, 1),
        "cream_share": round(cream * 100, 1),
        "warm_accent_share": round(warm_accent * 100, 1),
        "mean_sat": round(sum(sats) / len(sats), 1) if sats else 0,
        "mean_hue": round(sum(hues) / len(hues), 1) if hues else 0,
    }


def score_shot(meta: dict, px: dict | None) -> dict:
    blob = " ".join(filter(None, [
        meta.get("title", ""), meta.get("description", ""),
        " ".join(meta.get("tags") or []), meta.get("query", ""),
    ]))

    reasons: list[str] = []
    pts = 0

    # C1 - dark warm ground
    c1 = bool(px and px["mean_light"] < 58 and px["dark_warm_share"] > 22)
    pts += c1
    if c1:
        reasons.append(f"dark warm ground ({px['mean_light']:.0f}% L, "
                       f"{px['dark_warm_share']:.0f}% dark-warm)")

    # C2 - cream / bone type
    c2 = bool(px and px["cream_share"] > 4)
    pts += c2
    if c2:
        reasons.append(f"cream/bone present ({px['cream_share']:.0f}%)")

    # C3 - western / slab display type
    c3 = bool(WESTERN.search(blob))
    pts += c3
    if c3:
        reasons.append("western/slab language")

    # C4 - hand-made texture
    c4 = bool(TEXTURE.search(blob))
    pts += c4
    if c4:
        reasons.append("hand-made texture language")

    # C5 - Americana motifs
    c5 = bool(AMERICANA.search(blob))
    pts += c5
    if c5:
        reasons.append("Americana motifs")

    # C6 - bar / beverage context
    c6 = bool(BAR.search(blob))
    pts += c6
    if c6:
        reasons.append("bar/beverage context")

    # C7 - warm accent colour
    c7 = bool(px and px["warm_accent_share"] > 1.2)
    pts += c7
    if c7:
        reasons.append(f"warm accent ({px['warm_accent_share']:.1f}%)")

    # C8 - contemporary execution
    c8 = bool(MODERN.search(blob)) and not NEGATIVE.search(blob)
    pts += c8
    if c8:
        reasons.append("contemporary system work")

    # Penalty for the wrong side of the fence
    penalty = 1 if NEGATIVE.search(blob) else 0

    return {
        "score": pts - penalty,
        "raw": pts,
        "penalty": penalty,
        "criteria": {
            "C1_dark_warm": c1, "C2_cream": c2, "C3_western": c3,
            "C4_texture": c4, "C5_americana": c5, "C6_bar": c6,
            "C7_warm_accent": c7, "C8_modern": c8,
        },
        "reasons": reasons,
        "pixels": px,
    }


def main() -> None:
    shots = json.loads((REF / "dribbble_shots.json").read_text(encoding="utf-8"))
    bl.log(f"scoring {len(shots)} shots...\n")

    rows = []
    for s in shots:
        f = s.get("file")
        px = None
        if f:
            p = bl.RESEARCH / f
            if p.exists():
                px = pixel_scores(p)
        if px is None:
            continue
        sc = score_shot(s, px)
        rows.append({**s, **sc})

    rows.sort(key=lambda r: (-r["score"], -r["raw"]))

    qualified = [r for r in rows if r["score"] >= 4]
    strong = [r for r in rows if r["score"] >= 5]

    bl.dump_json(REF / "qualified.json", {
        "threshold": 4,
        "total_scored": len(rows),
        "qualified": len(qualified),
        "strong": len(strong),
        "shots": rows,
    })

    bl.log(f"scored           : {len(rows)}")
    bl.log(f"score >= 4        : {len(qualified)}")
    bl.log(f"score >= 5 (top) : {len(strong)}")
    bl.log("")
    bl.log("score distribution:")
    for k, v in sorted(Counter(r["score"] for r in rows).items(), reverse=True):
        bl.log(f"  {k:>2} pts : {v:>3}")

    bl.log("")
    bl.log("=== TOP REFERENCES ===")
    for r in rows[:30]:
        bl.log(f"  [{r['score']}] {(r.get('title') or 'untitled')[:52]}")
        bl.log(f"        {'; '.join(r['reasons'][:4])}")

    # ---- browsable shortlist ---------------------------------------------- #
    def esc(t: str) -> str:
        return (t or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def card(r: dict) -> str:
        img = f"../{r['file']}" if r.get("file") else ""
        link = r.get("url") or ""
        crits = "".join(
            f'<span class="c {"on" if v else ""}">{k.split("_")[0]}</span>'
            for k, v in r["criteria"].items())
        return (
            f'<figure><a href="{esc(link)}" target="_blank">'
            f'<img loading="lazy" src="{img}" alt="{esc(r.get("title",""))}"></a>'
            f'<figcaption><b>{r["score"]}</b> {esc((r.get("title") or "untitled")[:54])}'
            f'<br><span class="d">{esc(r.get("designer",""))} · '
            f'{esc((r.get("query") or ""))}</span>'
            f'<br><span class="r">{esc("; ".join(r["reasons"][:3]))}</span>'
            f'<br><span class="crits">{crits}</span></figcaption></figure>'
        )

    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>The Rustic Barrel - qualified Dribbble references</title><style>
 body{{font-family:ui-sans-serif,system-ui,sans-serif;margin:0;padding:26px;
      background:#17130f;color:#f0e6d6}}
 h1{{font-size:22px;margin:0 0 4px}}
 p.sub{{color:#a4938a;margin:0 0 22px;font-size:13px;max-width:760px}}
 h2{{font-size:15px;margin:28px 0 10px;color:#ed9f0f}}
 .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(215px,1fr));gap:11px}}
 figure{{margin:0;background:#241d17;border-radius:8px;overflow:hidden;
         border:1px solid #3a2c20}}
 figure img{{width:100%;height:200px;object-fit:cover;display:block}}
 figcaption{{font-size:10.5px;padding:8px;line-height:1.45;color:#c9b8a6}}
 figcaption b{{color:#ed9f0f;font-size:13px}}
 .d{{color:#8d7d70}} .r{{color:#9fb3a0;font-size:10px}}
 .crits{{margin-top:4px}}
 .c{{display:inline-block;background:#3a2c20;color:#7d6d61;border-radius:3px;
     padding:1px 4px;margin:1px 1px 0 0;font-size:9px;font-family:ui-monospace,monospace}}
 .c.on{{background:#6b1f1f;color:#f0e6d6}}
</style></head><body>
<h1>Qualified references — The Rustic Barrel Taphouse</h1>
<p class="sub">267 Dribbble shots scored against the eight criteria in
BRAND_VIBE.md: dark warm ground, cream/bone type, western or slab display type,
hand-made texture, Americana motifs, bar/beverage context, warm accent,
contemporary execution. Threshold for qualification: 4+. C1–C8 markers show
which criteria each shot hits.</p>
<h2>Top matches (5+)</h2>
<div class="grid">{''.join(card(r) for r in rows if r['score'] >= 5)}</div>
<h2>Qualified (4+)</h2>
<div class="grid">{''.join(card(r) for r in rows if r['score'] == 4)}</div>
</body></html>"""
    (REF / "shortlist.html").write_text(html, encoding="utf-8")
    bl.log("")
    bl.log(f"shortlist -> {REF / 'shortlist.html'}")


if __name__ == "__main__":
    main()
