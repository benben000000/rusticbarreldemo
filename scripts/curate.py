"""
Phase 2b - Curate the raw haul into a clean brand library.

The wire captures deliberately over-collect: marketplaces serve their own
marketing creative (DoorDash's CVS/grocery banners, Facebook's icon sprites)
alongside the restaurant's real assets. Left in, that noise would poison the
palette and mood analysis.

This pass:
  1. Reclassifies every file as BRAND CONTENT vs PLATFORM CHROME by origin rules
  2. Moves chrome into _platform_chrome/ (kept, but out of the brand library)
  3. Drops low-resolution thumbnails and duplicates
  4. Renames surviving files to a clean, human-readable scheme
  5. Writes research/brand/curated_library.json

Outputs:
  research/media/brand_library/     <- the actual deliverable media
  research/media/_platform_chrome/  <- marketplace/UI artwork, quarantined
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image

import brandlib as bl

LIBRARY = bl.MEDIA / "brand_library"
CHROME = bl.MEDIA / "_platform_chrome"

MIN_WIDTH = 500          # below this it is a thumbnail / icon, not usable
MIN_POST_PX = 1000       # Meta real post photos are >=1350px; sidebars are <=640
MIN_BYTES = 6_000


# --------------------------------------------------------------------------- #
# Origin rules: is this the restaurant's asset, or the platform's?
# --------------------------------------------------------------------------- #
OWN_HANDLES = ("the_rustic_barrel_", "therusticbarreltaphouse")


def is_own_content(source: str, referer: str) -> bool:
    """Instagram surfaces collab/partner posts from OTHER accounts in the same
    grid. Their photography is not the client's - drop it.

    Only meaningful for Instagram: a DoorDash referer will never contain an
    Instagram handle, so this must not be applied there."""
    if source != "instagram" or not referer:
        return True
    return any(h in referer for h in OWN_HANDLES)


def classify(source: str, url: str, ext: str = "", kind: str = "", w: int = 0) -> str:
    """Return 'brand' or 'chrome'."""
    low = url.lower()
    host = urlparse(low).netloc
    path = urlparse(low).path
    is_video = ext.lower() in (".mp4", ".mov", ".webm", ".m4v") or kind == "video"

    # --- Instagram reels (captured separately) ----------------------------- #
    if source == "instagram-reels" and is_video:
        return "brand"

    # --- DoorDash ---------------------------------------------------------- #
    if "cdn4dd.com" in host or "doordash" in low:
        # catex/ = DoorDash's own category + homepage advertising art
        if "/managed/catex/" in path or "catex" in low:
            return "chrome"
        # Store photography lives under /media/photosV..., /media/restaurant/,
        # /media/store/ on the S3 origin - note it is wrapped in a /cdn-cgi/ URL
        if any(seg in low for seg in (
            "/media/photosv", "/media/photos", "/media/restaurant/", "/media/store/",
        )):
            return "brand"
        return "chrome"

    # --- Uber Eats --------------------------------------------------------- #
    if "ubereats.com" in host or "uber.com" in host or "eatsfeed" in low:
        return "chrome"

    # --- Facebook / Instagram --------------------------------------------- #
    # Yelp hosts customer shots of the venue on yelpcdn.com.
    if "yelpcdn.com" in host:
        return "brand"

    # Meta serves TWO different classes of image from these post pages:
    #   * the real post/photo  -> {scontent,instagram}.fcrk1-*.fbcdn.net, >=1000px
    #   * sidebar "suggested"  -> scontent.cdninstagram.com at 507-640px, and
    #                              static.*/rsrc.php UI chrome
    # The fcrk1 hosts were missed by an earlier host-prefix rule, which threw
    # away every genuine brand photo and kept the sidebar thumbs. Keying on
    # resolution + the fcrk1 hosts is what actually separates them.
    if "facebook.com" in host or "fbcdn.net" in host:
        return "brand" if ("fcrk1" in host and w >= MIN_POST_PX) else "chrome"

    if "instagram.com" in host or "cdninstagram" in host:
        if host.startswith("static"):
            return "chrome"
        if "fcrk1" in host:
            return "brand" if w >= MIN_POST_PX else "chrome"
        return "brand" if (is_video or w >= MIN_POST_PX) else "chrome"

    return "chrome"


def is_meaningful_name(name: str) -> bool:
    """Human-readable marketing filenames are a strong platform-chrome tell."""
    return bool(re.search(r"(Desktop|Mobile|Tablet|Hero|splash|landingpage|catex)", name, re.I))


def perceptual_key(path: Path) -> str | None:
    """Cheap near-duplicate key: size + a 4x4 thumbnail hash."""
    try:
        with Image.open(path) as im:
            im = im.convert("RGB")
            im.thumbnail((4, 4))
            return hashlib.sha1(im.tobytes()).hexdigest()
    except Exception:  # noqa: BLE001
        return None


def nice_name(url: str, ext: str, idx: int, source: str) -> str:
    stem = Path(urlparse(url).path).stem
    stem = re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "", stem)
    stem = re.sub(r"[^A-Za-z0-9]+", "-", stem).strip("-")[:48]
    if not stem or len(stem) < 3:
        stem = f"{source}-{idx:03d}"
    return f"{source}_{idx:03d}_{stem}{ext}"


def main() -> None:
    manifest = json.loads((bl.BRAND / "asset_manifest.json").read_text(encoding="utf-8"))

    # Fold the separately-captured reel videos in as their own source.
    reel_path = bl.BRAND / "reel_assets.json"
    if reel_path.exists():
        reel_assets = json.loads(reel_path.read_text(encoding="utf-8"))
        manifest = [r for r in manifest if r.get("key") != "instagram-reels"]
        manifest.append({
            "key": "instagram-reels",
            "url": "https://www.instagram.com/the_rustic_barrel_/ (reels)",
            "title": "Instagram reels",
            "dom": {"imgs": [], "metas": [], "jsonld": [], "links": []},
            "computed": {"fonts": [], "colors": [], "headings": []},
            "css": {"font_faces": [], "font_families": [], "color_tokens": {},
                    "stylesheets_saved": []},
            "assets": reel_assets,
        })
        print(f"merged {len(reel_assets)} reel video assets")

    if LIBRARY.exists():
        shutil.rmtree(LIBRARY)
    if CHROME.exists():
        shutil.rmtree(CHROME)
    LIBRARY.mkdir(parents=True, exist_ok=True)
    CHROME.mkdir(parents=True, exist_ok=True)

    # Fold in the Yelp user photos captured through the authenticated session.
    yelp_path = bl.BRAND / "yelp_parsed.json"
    if yelp_path.exists():
        yp = json.loads(yelp_path.read_text(encoding="utf-8"))
        yassets = [{
            "url": p["url"], "file": p["file"], "kind": "photo", "ext": ".jpg",
            "bytes": p.get("bytes", 0), "referer": "https://www.yelp.com/",
            "caption": p.get("caption", ""),
        } for p in yp.get("user_photos_downloaded", [])]
        if yassets:
            manifest = [r for r in manifest if r.get("key") != "yelp"]
            manifest.append({
                "key": "yelp", "url": "https://www.yelp.com/biz/the-rustic-barrel-king-city-2",
                "title": "Yelp user photos", "dom": {"imgs": [], "metas": [], "jsonld": [], "links": []},
                "computed": {"fonts": [], "colors": [], "headings": []},
                "css": {"font_faces": [], "font_families": [], "color_tokens": {},
                        "stylesheets_saved": []},
                "assets": yassets,
            })
            print(f"merged {len(yassets)} yelp user photos")

    kept: list[dict] = []
    chrome_count = 0
    thin_count = 0
    dup_count = 0
    reasons: Counter = Counter()
    per_source: dict[str, int] = defaultdict(int)
    seen_hashes: dict[str, str] = {}

    for record in manifest:
        source = record["key"]
        for a in record.get("assets", []):
            src = bl.RESEARCH / a["file"]
            if not src.exists():
                continue

            # --- read dimensions first --------------------------------------- #
            is_video = a["kind"] == "video" or src.suffix.lower() in (".mp4", ".mov", ".webm")
            w = h = 0
            if not is_video:
                try:
                    with Image.open(src) as im:
                        w, h = im.width, im.height
                except Exception:  # noqa: BLE001
                    shutil.copy2(src, CHROME / src.name)
                    chrome_count += 1
                    reasons["unreadable"] += 1
                    continue

            verdict = classify(source, a["url"], a.get("ext", ""), a.get("kind", ""), w)
            if verdict == "chrome":
                shutil.copy2(src, CHROME / src.name)
                chrome_count += 1
                reasons[f"chrome:{source}"] += 1
                continue

            # Photos pulled from a partner/collaborator's Instagram post
            if not is_own_content(source, a.get("referer", "")):
                shutil.copy2(src, CHROME / src.name)
                chrome_count += 1
                reasons["other_account_collab"] += 1
                continue

            # --- quality gates ---------------------------------------------- #
            # Reel streams emit dozens of init/keyframe segments; anything under
            # ~120 KB is a fragment, not a watchable video.
            floor = 120_000 if is_video else MIN_BYTES
            if src.stat().st_size < floor:
                thin_count += 1
                reasons["video_fragment" if is_video else "too_small_file"] += 1
                shutil.copy2(src, CHROME / src.name)
                chrome_count += 1
                continue

            # --- image-only checks ------------------------------------------ #
            # Videos have no Pillow frame, so the dimension gates are skipped.
            if is_video:
                per_source[source] += 1
                idx = per_source[source]
                ext = a["ext"] if a["ext"] != ".bin" else src.suffix
                vdir = LIBRARY / "videos"
                vdir.mkdir(parents=True, exist_ok=True)
                vname = f"{source}_{idx:03d}_reel{ext}"
                shutil.copy2(src, vdir / vname)
                row = dict(a)
                row["library_file"] = f"brand_library/videos/{vname}"
                row["width"] = row["height"] = row["mp"] = None
                kept.append(row)
                continue

            try:
                with Image.open(src) as im:
                    w, h = im.width, im.height
            except Exception:  # noqa: BLE001
                shutil.copy2(src, CHROME / src.name)
                chrome_count += 1
                reasons["unreadable"] += 1
                continue

            if w < MIN_WIDTH:
                thin_count += 1
                reasons["too_low_res"] += 1
                shutil.copy2(src, CHROME / src.name)
                chrome_count += 1
                continue

            # --- dedupe ------------------------------------------------------ #
            pkey = perceptual_key(src)
            if pkey and pkey in seen_hashes:
                dup_count += 1
                reasons["duplicate"] += 1
                continue
            if pkey:
                seen_hashes[pkey] = a["url"]

            per_source[source] += 1
            idx = per_source[source]
            ext = a["ext"] if a["ext"] != ".bin" else src.suffix
            sub = "videos" if a["kind"] == "video" else "photos"
            folder = LIBRARY / sub
            folder.mkdir(parents=True, exist_ok=True)
            name = nice_name(a["url"], ext, idx, source)
            shutil.copy2(src, folder / name)

            row = dict(a)
            row["library_file"] = f"brand_library/{sub}/{name}"
            row["width"], row["height"] = w, h
            row["mp"] = round(w * h / 1_000_000, 2)
            kept.append(row)

    bl.dump_json(bl.BRAND / "curated_library.json", kept)

    bl.log("=" * 58)
    bl.log("CURATED BRAND LIBRARY")
    bl.log("=" * 58)
    bl.log(f"  brand photos kept : {sum(1 for k in kept if k['kind'] != 'video')}")
    bl.log(f"  brand videos kept : {sum(1 for k in kept if k['kind'] == 'video')}")
    bl.log(f"  platform chrome   : {chrome_count}  (quarantined)")
    bl.log(f"  dropped low-res   : {thin_count}")
    bl.log(f"  dropped duplicates: {dup_count}")
    bl.log("\n  per source:")
    for s, n in sorted(per_source.items(), key=lambda x: -x[1]):
        bl.log(f"    {s:<14} {n}")
    bl.log("\n  drop reasons:")
    for r, n in reasons.most_common(12):
        bl.log(f"    {r:<24} {n}")
    bl.log(f"\n  -> {LIBRARY}")


if __name__ == "__main__":
    main()
