"""
Phase 4 - Package the client-facing asset folder.

Copies the highest-signal brand assets (logo lockups, hero flyers, store
photography, reels) into research/media/brand_marks/ with descriptive names,
so the client receives usable files rather than a pile of CDN hashes.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import brandlib as bl

DEST = bl.MEDIA / "brand_marks"

# The designed Instagram flyers, in the order they were posted.
FLYERS = [
    ("instagram_001", "chili-cheese-fry-special"),
    ("instagram_002", "special-offer-poster"),
    ("instagram_003", "labor-day-closure-notice"),
    ("instagram_004", "chili-cheese-fry-special-dark"),
    ("instagram_005", "private-event-hours-notice"),
    ("instagram_006", "hours-change-notice-parchment"),
]


def main() -> None:
    lib = json.loads((bl.BRAND / "curated_library.json").read_text(encoding="utf-8"))
    by_stem = {}
    for a in lib:
        stem = Path(a["library_file"]).stem
        by_stem[stem] = a

    if DEST.exists():
        shutil.rmtree(DEST)
    DEST.mkdir(parents=True, exist_ok=True)

    copied = []
    for prefix, nice in FLYERS:
        for stem, a in by_stem.items():
            if stem.startswith(prefix):
                src = bl.MEDIA / a["library_file"]
                ext = src.suffix
                shutil.copy2(src, DEST / f"brand-{nice}{ext}")
                copied.append(f"brand-{nice}{ext}")
                break

    # Store photography
    photos = [a for a in lib if "doordash_" in a["library_file"]]
    for i, a in enumerate(photos, 1):
        src = bl.MEDIA / a["library_file"]
        shutil.copy2(src, DEST / f"photo-{i:03d}{src.suffix}")
        copied.append(f"photo-{i:03d}{src.suffix}")

    # Reels
    vids = [a for a in lib if a["kind"] == "video"]
    for i, a in enumerate(vids, 1):
        src = bl.MEDIA / a["library_file"]
        shutil.copy2(src, DEST / f"reel-{i:02d}{src.suffix}")
        copied.append(f"reel-{i:02d}{src.suffix}")

    readme = f"""# The Rustic Barrel Taphouse - asset pack

Extracted with Scrapling on {__import__('datetime').date.today().isoformat()}.

| File group | What it is |
|---|---|
| `brand-*.jpg/.png` | The designed marketing flyers - these carry the full identity (logo, type, colour) |
| `photo-NNN.*` | Store photography from the DoorDash album |
| `reel-NN.mp4` | Instagram reels |

**Sources:** instagram.com/the_rustic_barrel_ , facebook.com/therusticbarreltaphouse ,
doordash.com/store/the-rustic-barrel-king-city-34689489 , ubereats.com

**Note:** The originals are flat images baked into social posts. There is no vector
logo file and no source artwork available anywhere in their digital presence - see
BRAND_IDENTITY_GUIDELINES.md for the remediation plan.
"""
    (DEST / "README.md").write_text(readme, encoding="utf-8")

    print(f"packaged {len(copied)} files -> {DEST}")
    for c in copied[:10]:
        print(f"  {c}")
    print("  ...")


if __name__ == "__main__":
    main()
