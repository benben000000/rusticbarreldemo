"""Self-test for the void-element check in validate_seo.py.

A gate that has never been shown to fail is not a gate. This feeds the check
the exact markup that shipped (the stray-star <hr>) plus controls it must NOT
flag, so a future edit to the regex that silently neuters it is visible.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from validate_seo import void_with_content  # noqa: E402

# (markup, should_be_flagged)
CASES = [
    # the markup that actually shipped, on three pages
    ('<hr class="rule rule--star" aria-hidden="true">&#9733;</hr>', True),
    ('<br>oops</br>', True),
    ('<hr><span>&#9733;</span></hr>', True),
    ('<img src="a.png" alt="x" width="1" height="1">stray</img>', True),
    # controls it must NOT flag
    ('<img src="a.png" alt="x" width="1" height="1">', False),
    ('<meta name="viewport" content="width=device-width">', False),
    ('<link rel="stylesheet" href="/assets/css/site.css">', False),
    ('<hr>', False),
    ('<hr class="rule" />', False),
    ('<hr class="rule"><span>&#9733;</span>', False),   # not void any more
    ('<img alt="a > b" src="c.png">', False),           # ">" inside an attr
    # <br> is void but is SUPPOSED to be followed by content. An earlier
    # version of this check flagged these and broke the build on every
    # address block in the footer.
    ('<address>\n  611 Canal St<br>\n  King City, CA 93930<br>\n</address>', False),
    ('<hr class="rule">\n  <p>next</p>', False),        # element follows
    ('</div>', False),
]


def main() -> int:
    bad = 0
    print(f"  {'markup':<56}{'expect':>8}{'got':>8}   result")
    print("  " + "-" * 80)
    for markup, expect in CASES:
        flagged = bool(void_with_content(markup))
        ok = flagged == expect
        bad += not ok
        flat = " ".join(markup.split())
        label = flat if len(flat) <= 54 else flat[:51] + "..."
        print(f"  {label:<56}{'flag' if expect else 'pass':>8}"
              f"{'flag' if flagged else 'pass':>8}   {'ok' if ok else 'WRONG'}")

    print("  " + "-" * 80)
    print(f"  {len(CASES) - bad}/{len(CASES)} correct")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
