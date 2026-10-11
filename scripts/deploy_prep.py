"""Regenerate the site, run every gate, mirror to the root. One command.

The order matters and is the whole point of this file:

    1. assets    logo, hero, card art   (these write into site/assets/img)
    2. tokens    tokens.json -> tokens.css, sitemap, robots, _redirects
    3. pages     menu / beer / events / visit / 404
    4. gates     anything wrong should stop the line before the mirror
    5. mirror    site/ -> repo root, which is what Vercel actually serves

Mirroring before gating would publish a broken build. Gating before mirroring
means a failed gate leaves the root untouched, so the last good deploy is still
the last good deploy.

    python scripts/deploy_prep.py            full run
    python scripts/deploy_prep.py --gates    gates and mirror only, no rebuild
    python scripts/deploy_prep.py --no-mirror rebuild and gate, do not mirror
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable

BUILD = [
    ("logo",     "extract_logo.py"),
    ("hero",     "build_hero.py"),
    ("card art", "build_card_art.py"),
    ("tokens",   "build_site.py"),
    ("pages",    "build_pages.py"),
]

# (label, script, extra args)
GATES = [
    ("seo",          "validate_seo.py",        []),
    ("void markup",  "test_void_elements.py",  []),
    ("contrast",     "audit_contrast.py",      []),
    ("images",       "check_images.py",        ["/"]),
    ("dead space",   "find_dead_space.py",     ["/", "250"]),
    ("overflow",     "check_overflow.py",      ["1280"]),
    ("overflow sm",  "check_overflow.py",      ["390"]),
    ("root mirror",  "sync_root.py",           ["--check"]),
]

# hero contrast reads a screenshot, so it can only run once one exists.
AFTER_SHOTS = [
    ("hero contrast", "audit_hero_contrast.py", []),
]


def run(label: str, script: str, args: list[str] | None = None) -> tuple[bool, float]:
    cmd = [PY, str(ROOT / "scripts" / script), *(args or [])]
    start = time.perf_counter()
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    took = time.perf_counter() - start

    tail = [ln for ln in (proc.stdout or "").splitlines() if ln.strip()][-3:]
    status = "pass" if proc.returncode == 0 else "FAIL"
    print(f"  {status}  {label:<16} {took:5.1f}s")
    for ln in tail:
        print(f"          {ln}")
    if proc.returncode != 0:
        err = [ln for ln in (proc.stderr or "").splitlines() if ln.strip()][-6:]
        for ln in err:
            print(f"        ! {ln}")
    return proc.returncode == 0, took


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gates", action="store_true", help="skip the rebuild")
    ap.add_argument("--no-mirror", action="store_true", help="do not write the root")
    args = ap.parse_args()

    print(f"\n  Rustic Barrel — deploy prep\n  {'-' * 58}")

    if not args.gates:
        print("\n  BUILD")
        for label, script in BUILD:
            ok, _ = run(label, script)
            if not ok:
                print(f"\n  {script} failed. Nothing was mirrored.")
                return 1

    print("\n  GATES")
    failed: list[str] = []
    total = 0.0
    for label, script, extra in GATES:
        ok, took = run(label, script, extra)
        total += took
        if not ok:
            failed.append(label)

    print("\n  SCREENSHOT-DEPENDENT")
    if (ROOT / "research" / "screens" / "home-1280x900.png").exists():
        for label, script, extra in AFTER_SHOTS:
            ok, _ = run(label, script, extra)
            if not ok:
                failed.append(label)
    else:
        print("  skip   hero contrast    no screenshot yet - run scripts/shot.py home 1280 900")

    if failed:
        print(f"\n  {len(failed)} gate(s) failed: {', '.join(failed)}")
        print("  The root mirror was NOT updated, so a failed run cannot publish a")
        print("  broken build. Fix and re-run.\n")
        return 1

    if args.no_mirror:
        print("\n  Mirroring skipped (--no-mirror).\n")
        return 0

    print("\n  MIRROR")
    ok, _ = run("root", "sync_root.py")
    if not ok:
        return 1
    ok, _ = run("root verify", "sync_root.py", ["--check"])
    if not ok:
        return 1

    print(f"\n  All gates green in {total:.1f}s. "
          f"The repo root now matches site/ and is ready to push.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
