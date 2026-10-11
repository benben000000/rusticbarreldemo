"""
Phase 1g - Yelp via a logged-in browser session.

Yelp returns 403 to anonymous requests, including stealth Chromium - it blocks at
the edge on IP/visitor reputation, not on a challenge we can solve. The supported
way through is a real, authenticated session.

This script does NOT attempt to bypass anything. It:
  1. Launches a visible Chromium using a PERSISTENT profile directory
  2. Opens Yelp's login page and waits for YOU to sign in
  3. Persists the resulting cookies/session to the profile on disk
  4. Closes cleanly

After that, `yelp_scraper.py` reopens the same profile headlessly and the session
cookie travels with it, so the business page renders normally.

Run:  .venv\\Scripts\\python.exe scripts\\yelp_login.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from scrapling.fetchers import StealthyFetcher

PROFILE = Path(__file__).resolve().parent.parent / ".browsers" / "yelp_profile"
LOGIN_URL = "https://www.yelp.com/login?return_to=%2Fbiz%2Fthe-rustic-barrel-king-city-2"

PROFILE.mkdir(parents=True, exist_ok=True)


def check(page) -> str:
    """Are we authenticated? Look for signals only a logged-in visitor gets."""
    try:
        return page.evaluate("""() => {
            const t = document.body.innerText || '';
            const links = Array.from(document.querySelectorAll('a'))
              .map(a => (a.innerText || '').trim()).join('|');
            if (/log in|sign in/i.test(links) && !/log out|sign out|account/i.test(links)) {
                return 'anonymous';
            }
            return 'signed-in';
        }""")
    except Exception as e:  # noqa: BLE001
        return f"unknown ({type(e).__name__})"


def main() -> None:
    print("=" * 66)
    print("  YELP LOGIN - a browser window is about to open.")
    print("=" * 66)
    print("  1. Sign in to Yelp in that window (any account you own).")
    print("  2. Wait until you can see your own account menu top-right.")
    print("  3. Come back here - this script closes the window automatically.")
    print()
    print(f"  Session is stored at: {PROFILE}")
    print("  Nothing is typed or submitted on your behalf.")
    print("=" * 66)

    # A long wait so the human has time to authenticate.
    page = StealthyFetcher.fetch(
        LOGIN_URL,
        headless=False,          # visible window - this is the whole point
        network_idle=True,
        timeout=300_000,
        user_data_dir=str(PROFILE),
        page_action=lambda p: (
            print("  waiting for sign-in..."),
            p.wait_for_timeout(240_000),
        ),
    )

    state = check(page)
    print()
    print(f"  session state: {state}")
    print(f"  final url    : {str(page.url)[:120]}")

    cookies = page.cookies
    print(f"  cookies held : {len(cookies) if hasattr(cookies, '__len__') else '?'}")

    ok = "signed-in" in state
    print()
    if ok:
        print("  SUCCESS - profile saved. You can now run yelp_scraper.py")
    else:
        print("  NOT SIGNED IN - the session may not have persisted.")
        print("  Re-run and complete the login before the window closes.")
    print()
    print("  closing browser...")
    time.sleep(3)


if __name__ == "__main__":
    main()
