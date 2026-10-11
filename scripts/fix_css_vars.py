"""
Fix: reconcile site.css variable references with the names build_site.py emits.

The token flattener joins every path segment, so `typography.scale.display-xl`
becomes `--typography-scale-display-xl`. The stylesheet was hand-written
against `--typography-display-xl`. Every mismatched var() resolves to nothing,
the declaration is dropped by the CSS parser, and the element silently falls
back to the UA default - which is how every headline ended up at 16px
Times New Roman while every static check passed.

`subhead` is a genuine collision in the token shape: it names both a font
family (typography.family.subhead) and a size (typography.scale.subhead). The
size is renamed to `subhead-size` in tokens.json so each reference is
unambiguous.

Run once:  .venv\\Scripts\\python.exe scripts\\fix_css_vars.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSS = ROOT / "site" / "assets" / "css" / "site.css"
TOKENS = ROOT / "site" / "assets" / "tokens.json"

# longest first, so --typography-body-l is not eaten by --typography-body
MAP = [
    ("--typography-display-xl", "--typography-scale-display-xl"),
    ("--typography-display-l",  "--typography-scale-display-l"),
    ("--typography-display-m",  "--typography-scale-display-m"),
    ("--typography-display-s",  "--typography-scale-display-s"),
    ("--typography-body-l",     "--typography-scale-body-l"),
    ("--typography-body-s",     "--typography-scale-body-s"),
    ("--typography-label",      "--typography-scale-label"),
    ("--typography-display",    "--typography-family-display"),
    ("--typography-script",     "--typography-family-script"),
    ("--typography-subhead",    "--typography-family-subhead"),
    ("--typography-body",       "--typography-family-body"),
]

# font-family declarations must point at the *family* token
FAMILY_RE = re.compile(
    r"(font-family\s*:\s*var\()--typography-scale-([a-z-]+)(\))")


def main() -> int:
    css = CSS.read_text(encoding="utf-8")
    original = css

    # 1. rename the colliding size token
    tk = TOKENS.read_text(encoding="utf-8")
    if '"subhead"' in tk:
        tk = tk.replace('"subhead": { "$value": "clamp(1.125rem, 2.4vw, 1.5rem)"',
                        '"subhead-size": { "$value": "clamp(1.125rem, 2.4vw, 1.5rem)"')
        TOKENS.write_text(tk, encoding="utf-8")
        print("  tokens.json: scale.subhead -> scale.subhead-size (de-collide)")

    # 2. rewrite every mismatched reference
    changed = 0
    for old, new in MAP:
        # negative lookbehind so --typography-display-l does not match
        # inside --typography-display-xl (already handled by ordering, but this
        # guards the substring families)
        pat = re.compile(re.escape(old) + r"(?![\w-])")
        css, n = pat.subn(new, css)
        changed += n

    # 3. font-family uses must resolve to the family token, never the scale one
    css, n = FAMILY_RE.subn(r"\1--typography-family-\2\3", css)
    changed += n

    # 4. size uses of the subhead scale token
    css, n = re.subn(
        r"(font-size\s*:\s*var\()--typography-family-subhead(\))",
        r"\1--typography-scale-subhead-size\2", css)
    changed += n

    CSS.write_text(css, encoding="utf-8")
    print(f"  site.css: {changed} variable references rewritten")

    # 5. verify nothing references an undefined var any more.
    # Definitions live in the GENERATED tokens.css, not in tokens.json.
    gen = ROOT / "site" / "assets" / "tokens.css"
    defined = set(re.findall(r"(--[\w-]+)\s*:", gen.read_text(encoding="utf-8")))
    used = set(re.findall(r"var\((--[\w-]+)", css))
    missing = sorted(used - defined)
    if missing:
        print(f"\n  STILL UNDEFINED ({len(missing)}):")
        for m in missing:
            print(f"    {m}")
        return 1
    print(f"  all {len(used)} var() references resolve against tokens.css")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
