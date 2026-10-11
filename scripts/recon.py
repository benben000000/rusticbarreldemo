"""
Phase 0 - Reconnaissance.

Probes every known touchpoint for The Rustic Barrel with Scrapling's StealthyFetcher
and reports whether the content is actually reachable, so we know what we're working
with before building the real scrapers.

Outputs: research/raw/recon.json
"""

import json
import re
import time
from pathlib import Path

from scrapling.fetchers import StealthyFetcher

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "research" / "raw"

TARGETS = [
    ("yelp", "https://www.yelp.com/biz/the-rustic-barrel-king-city-2"),
    ("doordash", "https://doordash.com/store/34689489?src=yp&pickup=true"),
    ("ubereats", "https://www.ubereats.com/store/the-rustic-barrel/j50H6Tr2W-qha1Ep9ys4Ag"),
    ("facebook", "https://www.facebook.com/therusticbarreltaphouse"),
    ("instagram", "https://www.instagram.com/the_rustic_barrel_/"),
    # Likely-owned domains worth probing
    ("site_therusticbarrel_com", "https://www.therusticbarrel.com"),
    ("site_therusticbarrel831_com", "https://www.therusticbarrel831.com"),
    ("site_rusticbarrel_com", "https://www.rusticbarrel.com"),
]

BLOCK_MARKERS = [
    "unusual traffic",
    "are you a robot",
    "verify you are human",
    "access denied",
    "enable javascript and cookies",
    "just a moment",
    "checking your browser",
    "captcha",
    "security check",
    "page not available",
    "this content isn't available",
    "you must log in",
    "log in to continue",
    "sorry, this page",
    "request blocked",
]


def classify(html: str) -> str:
    low = html[:40000].lower()
    for m in BLOCK_MARKERS:
        if m in low:
            return f"BLOCKED ({m})"
    if len(html) < 3000:
        return "THIN / SUSPECT"
    return "OK"


def title_of(page, html: str) -> str:
    """Scrapling's Response is itself a Selector - it exposes .css(), not .css_first()."""
    try:
        nodes = page.css("title::text")
        if nodes:
            return str(nodes[0]).strip()[:200]
    except Exception:  # noqa: BLE001
        pass
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    return (m.group(1).strip()[:200] if m else "")


def probe(key: str, url: str) -> dict:
    entry = {"key": key, "url": url}
    t0 = time.time()
    try:
        page = StealthyFetcher.fetch(
            url,
            headless=True,
            network_idle=True,
            timeout=90_000,
            solve_cloudflare=True,
            disable_resources=True,
        )
        html = page.html_content
        entry.update(
            {
                "status": getattr(page, "status", None),
                "final_url": str(getattr(page, "url", url)),
                "bytes": len(html),
                "title": title_of(page, html),
                "verdict": classify(html),
                "elapsed": round(time.time() - t0, 1),
            }
        )
        # Save the raw HTML so later phases can parse it offline if we want to.
        (RAW / f"recon_{key}.html").write_text(html, encoding="utf-8")
    except Exception as e:  # noqa: BLE001 - recon must never die on one target
        import traceback
        entry.update({
            "verdict": f"ERROR: {type(e).__name__}",
            "error": str(e)[:300],
            "traceback": traceback.format_exc()[-800:],
        })
    return entry


def main() -> None:
    results = []
    for key, url in TARGETS:
        print(f"--> probing {key}: {url}", flush=True)
        entry = probe(key, url)
        results.append(entry)
        print(f"    {entry.get('verdict')}  {entry.get('bytes', 0)} bytes", flush=True)
        time.sleep(3)  # be polite between browser launches

    (RAW / "recon.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("\n=== RECON SUMMARY ===")
    for r in results:
        print(f"{r['key']:<32} {r.get('verdict','?')}")


if __name__ == "__main__":
    main()
