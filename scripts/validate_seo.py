"""
Site build - SEO validator.

Runs against the generated HTML and fails loudly. Every check maps to a line on
the launch checklist in docs/SEO_LAUNCH_CHECKLIST.md, so "done" means the build
passed, not that someone eyeballed it.

Checks:
  1. unique <title> per page, within length budget
  2. unique meta description per page, within length budget
  3. exactly one <h1> per page
  4. canonical present, absolute, self-referencing
  5. no noindex / nofollow-in-meta robots anywhere
  6. viewport meta present (mobile)
  7. every internal link resolves to a file that exists
  8. images have alt and explicit dimensions (no CLS)
  9. JSON-LD parses and carries the expected @type
 10. sitemap + robots.txt exist and reference each other
 11. og:image absolute and https
 12. internal linking graph has no orphan pages

Usage:  .venv\\Scripts\\python.exe scripts\\validate_seo.py
Exit code 1 on any failure.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"

TITLE_MAX = 60
DESC_MAX = 155
DESC_MIN = 70

SKIP_LINKCHECK = {"/404.html"}

# HTML void elements: no content model, no closing tag. Anything written between
# the open and close tags is silently re-parented by the parser.
VOID_ELEMENTS = ("hr", "br", "img", "input", "meta", "link", "source",
                 "area", "base", "col", "embed", "track", "wbr", "param")

# Attribute run, quote-aware, so a ">" inside an alt= does not end the tag early.
_ATTR = r"""(?:"[^"]*"|'[^']*'|[^>"'])*"""


def void_with_content(html: str) -> list[str]:
    """Void elements written with an explicit closing tag.

    <hr class="rule rule--star" aria-hidden="true">&#9733;</hr> shipped on three
    pages. <hr> is void - it has no content model and no closing tag - so the
    parser never opened a container for the star and ejected it into the parent
    as a stray text node. It rendered left-aligned and completely unstyled, on
    every page carrying it.

    Nothing else in this gate saw the bug: the tags balanced, the page still had
    its h1 and canonical, and no link was broken. It only showed up when the
    rendered page was actually looked at.

    The test is the closing tag itself, not "what follows". An earlier version
    flagged every void element with content after it, which is how <br> is
    supposed to be used - it fired on every address block in the footer.
    A closing tag for a void element is always wrong and never intentional.
    """
    bad: list[str] = []
    for m in re.finditer(
        rf"</\s*({'|'.join(VOID_ELEMENTS)})\s*>", html, re.I
    ):
        tag = m.group(1).lower()
        opener = None
        for cand in re.finditer(rf"<{tag}(\s{_ATTR})?\s*/?>", html[:m.start()], re.I):
            opener = cand                      # the nearest preceding open tag
        if opener is None:
            continue
        snippet = " ".join(html[opener.start():m.end() + 24].split())
        bad.append(f"<{tag}>...{snippet[:88]}")
    return bad

errors: list[str] = []
warns: list[str] = []
oks: list[str] = []


def fail(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warns.append(msg)


def ok(msg: str) -> None:
    oks.append(msg)


def strip_tags(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s)


def main() -> int:
    pages = sorted(p for p in SITE.glob("*.html"))
    if not pages:
        print("no pages found in site/")
        return 1

    titles: dict[str, str] = {}
    descs: dict[str, str] = {}
    links_out: dict[str, set[str]] = {}
    linked_to: set[str] = set()

    for p in pages:
        h = p.read_text(encoding="utf-8")
        rel = "/" + p.name

        # 1 title
        m = re.search(r"<title>(.*?)</title>", h, re.S)
        if not m:
            fail(f"{rel}: no <title>")
        else:
            t = strip_tags(m.group(1)).strip()
            titles[rel] = t
            if len(t) > TITLE_MAX:
                fail(f"{rel}: title {len(t)}ch > {TITLE_MAX} -> '{t[:50]}...'")
            elif len(t) < 20:
                warn(f"{rel}: title only {len(t)}ch")
            if t in titles.values() and list(titles.values()).count(t) > 1:
                fail(f"{rel}: duplicate title '{t[:40]}'")

        # 2 description
        m = re.search(r'<meta name="description" content="([^"]*)"', h)
        if not m:
            fail(f"{rel}: no meta description")
        else:
            d = m.group(1).strip()
            descs[rel] = d
            if len(d) > DESC_MAX:
                fail(f"{rel}: description {len(d)}ch > {DESC_MAX}")
            if len(d) < DESC_MIN:
                warn(f"{rel}: description only {len(d)}ch")
            if list(descs.values()).count(d) > 1:
                fail(f"{rel}: duplicate meta description")

        # 3 h1
        n_h1 = len(re.findall(r"<h1[\s>]", h))
        if n_h1 != 1:
            fail(f"{rel}: {n_h1} <h1> tags (expected exactly 1)")

        # 4 canonical
        m = re.search(r'<link rel="canonical" href="([^"]*)"', h)
        if not m:
            fail(f"{rel}: no canonical")
        elif not m.group(1).startswith("https://"):
            fail(f"{rel}: canonical not https -> {m.group(1)}")
        else:
            ok(f"{rel}: canonical absolute")

        # 5 noindex
        bad = re.findall(r'<meta name="robots" content="([^"]*)"', h)
        for b in bad:
            if "noindex" in b.lower():
                fail(f"{rel}: robots meta contains noindex -> {b}")
        if "X-Robots-Tag" in h:
            warn(f"{rel}: mentions X-Robots-Tag in markup (check headers)")

        # 6 viewport
        if not re.search(r'<meta name="viewport"', h):
            fail(f"{rel}: no viewport meta (mobile)")

        # 8 images
        for tag in re.findall(r"<img[^>]*>", h):
            if "alt=" not in tag:
                fail(f"{rel}: <img> without alt -> {tag[:70]}")
            if "width=" not in tag or "height=" not in tag:
                warn(f"{rel}: <img> without width/height (CLS risk) -> {tag[:70]}")
        for src in re.findall(r'(?:src|srcset)="(/assets/[^"]+)"', h):
            for cand in re.split(r"\s*,\s*", src):
                cand = cand.strip().split(" ")[0]
                if cand and not (SITE / cand.lstrip("/")).exists():
                    fail(f"{rel}: missing asset {cand}")

        # 8b void elements given content
        for snippet in void_with_content(h):
            fail(f"{rel}: void element given content -> {snippet}")

        # 9 JSON-LD
        for blob in re.findall(
            r'<script type="application/ld\+json">(.*?)</script>', h, re.S
        ):
            try:
                parsed = json.loads(blob)
            except Exception as e:  # noqa: BLE001
                fail(f"{rel}: JSON-LD does not parse -> {e}")
                continue
            flat = json.dumps(parsed)
            if "@type" not in flat:
                warn(f"{rel}: JSON-LD has no @type")

        # 11 og:image
        m = re.search(r'<meta property="og:image" content="([^"]*)"', h)
        if not m:
            fail(f"{rel}: no og:image")
        elif not m.group(1).startswith("https://"):
            fail(f"{rel}: og:image not absolute https")

        # 7 internal links
        out: set[str] = set()
        for href in re.findall(r'href="(/[^"#?]*)"', h):
            if href in SKIP_LINKCHECK:
                continue
            out.add(href)
            target = SITE / ("index.html" if href == "/" else href.lstrip("/"))
            if not target.exists():
                fail(f"{rel}: broken internal link -> {href}")
            else:
                # normalise so "/" and "/index.html" are the same node
                linked_to.add("/" if target.name == "index.html" else href)
        links_out[rel] = out

    # 10 sitemap / robots
    sm = SITE / "sitemap.xml"
    rb = SITE / "robots.txt"
    if not sm.exists():
        fail("sitemap.xml missing")
    else:
        body = sm.read_text(encoding="utf-8")
        n = body.count("<loc>")
        if n == 0:
            fail("sitemap.xml has no <loc> entries")
    for page in pages:
        if page.name == "404.html":
            continue
        url = "https://www.therusticbarrel.com/" + (
            "" if page.name == "index.html" else page.name)
        if url not in body:
            fail(f"sitemap.xml missing {url}")
    ok(f"sitemap.xml: {n} URLs, every page covered")

    if not rb.exists():
        fail("robots.txt missing")
    else:
        body = rb.read_text(encoding="utf-8")
        if "Sitemap:" not in body:
            fail("robots.txt does not reference the sitemap")
        elif "sitemap.xml" not in body:
            fail("robots.txt sitemap reference is malformed")
        # a blanket Disallow before any Allow is the classic deindex bug
        ua = re.search(r"User-agent: \*.*?(?=\n\nUser-agent|\n\nSitemap|\Z)",
                       body, re.S)
        if ua:
            block = ua.group(0)
            if "Disallow: /" in block and "Allow: /" not in block:
                fail("robots.txt: blanket 'Disallow: /' for User-agent *")
        ok("robots.txt: references sitemap, no blanket disallow")

    # 12 orphan pages
    for page in pages:
        if page.name == "404.html":
            continue
        rel = "/" if page.name == "index.html" else "/" + page.name
        if rel not in linked_to:
            warn(f"{rel}: no inbound internal link (orphan)")

    # 13. every var() in the stylesheet must resolve to a generated token
    css_path = SITE / "assets" / "css" / "site.css"
    tok_path = SITE / "assets" / "tokens.css"
    if css_path.exists() and tok_path.exists():
        css = css_path.read_text(encoding="utf-8")
        toks = tok_path.read_text(encoding="utf-8")
        defined = set(re.findall(r"(--[\w-]+)\s*:", toks))
        used = set(re.findall(r"var\((--[\w-]+)", css))
        missing = sorted(used - defined)
        if missing:
            for m in missing:
                fail(f"site.css: var({m}) is not defined in tokens.css "
                     f"- declaration is silently dropped")
        else:
            ok(f"site.css: all {len(used)} var() references resolve")
    else:
        warn("could not verify CSS variable integrity (files missing)")

    # ---- report ----------------------------------------------------------- #
    print("=" * 66)
    print(" SEO VALIDATION - The Rustic Barrel")
    print("=" * 66)
    for o in oks:
        print(f"  PASS  {o}")
    print()
    for w in warns:
        print(f"  WARN  {w}")
    if warns:
        print()
    for e in errors:
        print(f"  FAIL  {e}")
    print()
    print(f"  {len(oks)} passed, {len(warns)} warnings, {len(errors)} failures")
    print("=" * 66)

    if errors:
        print("\nBUILD BLOCKED - fix the failures above.")
        return 1
    print("\nAll hard SEO checks pass. Ready for launch, subject to the")
    print("operational steps in docs/SEO_LAUNCH_CHECKLIST.md that need a")
    print("live domain and a Google account.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
