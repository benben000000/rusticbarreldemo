"""List the captured Yelp originals with size and caption, so card art can be
chosen from what the room actually looks like rather than at random.

Usage: .venv\\Scripts\\python.exe scripts\\list_shots.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from PIL import Image

import brandlib as bl


def main() -> int:
    parsed = json.loads((bl.BRAND / "yelp_parsed.json").read_text(encoding="utf-8"))
    by_id: dict[str, dict] = {}
    for key in ("user_photos", "user_photos_downloaded"):
        for p in parsed.get(key, []) or []:
            pid = (p.get("url") or "").split("/bphoto/")[-1].split("/")[0]
            if pid:
                by_id[pid] = p

    rows = []
    for f in sorted((bl.MEDIA / "photos").glob("orig-*.jpg")):
        pid = f.stem.replace("orig-", "")
        with Image.open(f) as im:
            w, h = im.size
        info = by_id.get(pid, {})
        rows.append((pid, w, h, info.get("caption") or "", info.get("keywords") or []))

    print(f"  {'photo id':<26}{'size':>10}  caption / keywords")
    print("  " + "-" * 104)
    for pid, w, h, cap, kw in rows:
        tag = ",".join(kw) if kw else ""
        line = (cap + ("  [" + tag + "]" if tag else "")).strip()
        print(f"  {pid:<26}{f'{w}x{h}':>10}  {line[:62]}")

    print(f"\n  {len(rows)} originals")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
