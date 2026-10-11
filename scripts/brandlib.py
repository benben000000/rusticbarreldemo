"""
Shared helpers for The Rustic Barrel brand-intelligence scrape.

Everything is built on Scrapling:
  * StealthyFetcher  - Chromium with anti-detection for JS-heavy / bot-protected pages
  * Fetcher          - curl-cffi impersonation for fast asset downloads
"""

from __future__ import annotations

import hashlib
import json
import mimetypes
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

from scrapling.fetchers import Fetcher

ROOT = Path(__file__).resolve().parent.parent
RESEARCH = ROOT / "research"
RAW = RESEARCH / "raw"
MEDIA = RESEARCH / "media"
PHOTOS = MEDIA / "photos"
VIDEOS = MEDIA / "videos"
LOGOS = MEDIA / "logos"
FONTS = MEDIA / "fonts"
BRAND = RESEARCH / "brand"
LOGS = RESEARCH / "logs"

for _d in (RAW, MEDIA, PHOTOS, VIDEOS, LOGOS, FONTS, BRAND, LOGS):
    _d.mkdir(parents=True, exist_ok=True)

# Extensions that are never a brand asset - trackers, sprites, junk.
JUNK_EXT = {
    ".gif", ".ico", ".svgz", ".map", ".woff2", ".woff", ".ttf", ".otf", ".eot",
    ".js", ".mjs", ".css", ".json", ".xml", ".txt", ".html", ".htm", ".php",
    ".swf", ".mp4.webm",
}

IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".bmp", ".tif", ".tiff"}
VID_EXT = {".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv", ".m3u8"}

CT_EXT = {
    "image/jpeg": ".jpg", "image/jpg": ".jpg", "image/png": ".png",
    "image/webp": ".webp", "image/avif": ".avif", "image/gif": ".gif",
    "image/bmp": ".bmp", "image/tiff": ".tiff", "image/x-icon": ".ico",
    "video/mp4": ".mp4", "video/quicktime": ".mov", "video/webm": ".webm",
    "video/x-m4v": ".m4v", "application/vnd.apple.mpegurl": ".m3u8",
    "application/x-mpegurl": ".m3u8", "font/woff2": ".woff2",
    "font/woff": ".woff", "font/ttf": ".ttf", "font/otf": ".otf",
    "application/font-woff2": ".woff2", "application/font-woff": ".woff",
}

# Domains that only ever serve analytics/pixel/spacer assets.
TRACKER_HOSTS = (
    "google-analytics", "googletagmanager", "doubleclick", "facebook.net/tr",
    "connect.facebook", "hotjar", "segment", "sentry", "mixpanel", "amplitude",
    "clarity.ms", "gstatic.com/generate_204", "bat.bing", "scorecardresearch",
    "quantserve", "optimizely", "fullstory", "branch.io", "app.link",
)


# --------------------------------------------------------------------------- #
# URL helpers
# --------------------------------------------------------------------------- #
def is_junk(url: str) -> bool:
    if not url or not url.startswith("http"):
        return True
    low = url.lower()
    if any(t in low for t in TRACKER_HOSTS):
        return True
    ext = Path(urlparse(url).path).suffix.lower()
    return ext in JUNK_EXT


def ext_of(url: str, content_type: str = "") -> str:
    ext = Path(urlparse(url).path).suffix.lower()
    if ext in IMG_EXT or ext in VID_EXT or ext in {".svg", ".woff2", ".woff", ".ttf", ".otf"}:
        return ext
    ct = (content_type or "").split(";")[0].strip().lower()
    return CT_EXT.get(ct, ext or ".bin")


def kind_of(url: str, content_type: str = "", hint: str = "") -> str:
    """Classify an asset as photo / video / logo / font / other."""
    low = url.lower()
    ext = ext_of(url, content_type)
    if hint == "font" or ext in {".woff2", ".woff", ".ttf", ".otf", ".eot"}:
        return "font"
    if ext in VID_EXT or "video" in (content_type or "").lower():
        return "video"
    if any(k in low for k in ("logo", "wordmark", "brandmark", "mark_", "/mark.")):
        return "logo"
    if ext == ".svg":
        return "logo" if any(k in low for k in ("logo", "icon", "mark")) else "other"
    if ext in IMG_EXT or "image" in (content_type or "").lower():
        return "photo"
    return "other"


def safe_name(url: str, ext: str) -> str:
    """Deterministic, readable filename derived from the URL."""
    p = urlparse(url)
    base = Path(p.path).stem or "asset"
    base = re.sub(r"[^A-Za-z0-9._-]+", "-", base)[:60].strip("-.")
    tail = hashlib.sha1(url.encode()).hexdigest()[:8]
    return f"{base}-{tail}{ext}"


# --------------------------------------------------------------------------- #
# Download
# --------------------------------------------------------------------------- #
def download(url: str, referer: str = "", timeout: int = 45) -> dict | None:
    """Download a single asset using browser impersonation. Returns file info."""
    headers = {"Referer": referer, "Accept": "*/*"} if referer else {"Accept": "*/*"}
    for attempt in range(2):
        try:
            resp = Fetcher.get(
                url,
                impersonate="chrome",
                stealthy_headers=True,
                follow_redirects=True,
                timeout=timeout,
                headers=headers,
            )
            if resp.status != 200:
                if attempt == 0:
                    time.sleep(1.5)
                    continue
                return None
            body = resp.body
            if not body or len(body) < 120:
                return None
            ct = resp.headers.get("content-type", "")
            ext = ext_of(url, ct)
            return {"body": body, "ext": ext, "content_type": ct, "bytes": len(body)}
        except Exception:  # noqa: BLE001 - a dead asset must not kill the run
            if attempt == 0:
                time.sleep(1.5)
    return None


def save_asset(url: str, bucket: str, referer: str = "") -> dict | None:
    """Download + write an asset into its bucket folder, skipping duplicates."""
    info = download(url, referer=referer)
    if not info:
        return None
    folder = {"photo": PHOTOS, "video": VIDEOS, "logo": LOGOS, "font": FONTS}.get(
        bucket, PHOTOS
    )
    name = safe_name(url, info["ext"])
    path = folder / name
    path.write_bytes(info["body"])
    return {
        "url": url,
        "file": str(path.relative_to(RESEARCH)).replace("\\", "/"),
        "kind": bucket,
        "ext": info["ext"],
        "content_type": info["content_type"],
        "bytes": info["bytes"],
        "referer": referer,
    }


# --------------------------------------------------------------------------- #
# DOM harvesting JS (runs inside the page)
# --------------------------------------------------------------------------- #
JS_HARVEST = r"""
() => {
  const out = { imgs: [], videos: [], srcsets: [], links: [], metas: [],
                backgrounds: [], fonts: [], svgs: [], jsonld: [], classes: [] };
  const abs = (u) => { try { return new URL(u, location.href).href; } catch { return u; } };

  document.querySelectorAll('img').forEach(el => {
    const rec = { src: el.currentSrc || el.src || '',
                  alt: el.alt || '', width: el.naturalWidth, height: el.naturalHeight,
                  cls: (el.className && el.className.baseVal !== undefined ? el.className.baseVal : el.className || '').toString().slice(0,120) };
    if (rec.src) out.imgs.push(rec);
    if (el.srcset) out.srcsets.push(el.srcset);
  });

  document.querySelectorAll('video, video source, audio source').forEach(el => {
    out.videos.push({ src: el.currentSrc || el.src || '', poster: el.poster || '',
                      type: el.getAttribute('type') || '', cls: (el.className||'').toString().slice(0,120) });
  });

  document.querySelectorAll('link[rel]').forEach(el => {
    const rel = (el.rel || '').toLowerCase();
    const href = el.href || '';
    if (!href) return;
    if (rel.includes('icon') || rel.includes('apple-touch') || rel.includes('mask-icon') || rel.includes('manifest'))
      out.links.push({ rel, href: abs(href) });
    if (rel.includes('stylesheet') || rel.includes('preload'))
      out.links.push({ rel, href: abs(href) });
  });

  document.querySelectorAll('meta').forEach(el => {
    const n = el.getAttribute('name') || el.getAttribute('property') || '';
    const c = el.getAttribute('content') || '';
    if (n && c) out.metas.push({ name: n.toLowerCase(), content: c });
  });

  // CSS background-images incl. inline styles + stylesheets
  document.querySelectorAll('*').forEach(el => {
    const bg = getComputedStyle(el).backgroundImage;
    if (bg && bg !== 'none') {
      const m = bg.match(/url\(["']?(.*?)["']?\)/g);
      if (m) m.forEach(x => out.backgrounds.push(abs(x.replace(/url\(["']?/,'').replace(/["']?\)/,''))));
    }
  });

  // Fonts actually in use
  const fams = new Set();
  document.querySelectorAll('body *').forEach(el => {
    const ff = getComputedStyle(el).fontFamily;
    if (ff && ff !== 'inherit') fams.add(ff);
  });
  out.fonts = Array.from(fams).slice(0, 60);

  document.querySelectorAll('svg').forEach(el => {
    const cls = (el.getAttribute('class') || '');
    const aria = el.getAttribute('aria-label') || '';
    if (cls || aria) out.svgs.push({ cls: cls.slice(0,120), label: aria.slice(0,120) });
  });

  document.querySelectorAll('script[type="application/ld+json"]').forEach(el => {
    if (el.textContent) out.jsonld.push(el.textContent.slice(0, 40000));
  });

  return out;
}
"""

JS_COMPUTED_STYLE = r"""
() => {
  const pick = (el, name) => { try { return getComputedStyle(el)[name]; } catch { return null; } };
  const res = { fonts: [], colors: [], backgrounds: [], headings: [] };
  const seen = new Set();
  document.querySelectorAll('h1,h2,h3,h4,p,a,span,button,li,div').forEach(el => {
    if (!el.textContent || !el.textContent.trim()) return;
    if (el.children.length > 2) return;
    const key = el.tagName + '|' + (el.textContent.trim().slice(0,40));
    if (seen.has(key)) return;
    seen.add(key);
    const f = pick(el, 'fontFamily'), s = pick(el, 'fontSize'),
          w = pick(el, 'fontWeight'), st = pick(el, 'fontStyle'),
          lh = pick(el, 'lineHeight'), ls = pick(el, 'letterSpacing'),
          c = pick(el, 'color'), bg = pick(el, 'backgroundColor'),
          tr = pick(el, 'textTransform'), ff = pick(el, 'fontFamily');
    if (f && w) res.fonts.push({ tag: el.tagName, sample: el.textContent.trim().slice(0,50),
        family: f, size: s, weight: w, style: st, lineHeight: lh, letterSpacing: ls, transform: tr });
    if (c) res.colors.push({ tag: el.tagName, color: c, bg: bg,
        sample: el.textContent.trim().slice(0,40) });
    if (/^H[1-4]$/.test(el.tagName)) res.headings.push({ tag: el.tagName,
        text: el.textContent.trim().slice(0,120), family: f, size: s, weight: w,
        transform: tr, ls: ls, color: c });
  });
  return res;
}
"""

JS_AUTOSCROLL = r"""
async (maxSteps) => {
  await new Promise(resolve => {
    let steps = 0;
    const tick = () => {
      window.scrollBy(0, 700);
      steps++;
      if (steps < maxSteps) setTimeout(tick, 90);
      else { window.scrollTo(0, document.body.scrollHeight); setTimeout(resolve, 400); }
    };
    tick();
  });
  return { height: document.body.scrollHeight, steps: maxSteps };
}
"""


def dump_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def log(msg: str) -> None:
    # Windows consoles default to cp1252 and explode on typographic characters
    # scraped straight out of menus (U+2060 word joiner etc). Force UTF-8.
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        enc = (getattr(sys.stdout, "encoding", None) or "ascii")
        print(msg.encode(enc, "replace").decode(enc, "replace"), flush=True)
