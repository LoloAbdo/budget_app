"""
services/shopping_service.py
Fetch Amazon product prices for the Shopping price tracker.

Plain Python (no Qt) so it runs on a worker thread and unit-tests offline: the
parse functions take an HTML string, and only ``fetch_item`` / ``fetch_wishlist``
touch the network. Network helpers use stdlib urllib with short timeouts and
never raise — failures surface as ``ItemInfo.ok = False`` or ``FetchBlocked``.

CAVEAT: scraping Amazon violates its Terms of Service and its anti-bot systems
(CAPTCHA / "Robot Check") will block requests intermittently. This is best-effort
for personal use only; a blocked fetch keeps the last known price and flags the
row stale rather than storing garbage.
"""

from __future__ import annotations

import re
import urllib.request
import urllib.parse
from dataclasses import dataclass, field
from typing import Optional

from bs4 import BeautifulSoup

_TIMEOUT = 8  # seconds per request
# A realistic desktop-browser UA + headers; the terse market UA gets 503'd here.
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-CA,en;q=0.9,fr-CA;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Markers Amazon returns on its bot wall / CAPTCHA interstitial.
_BLOCK_MARKERS = (
    "Robot Check",
    "Enter the characters you see below",
    "api-services-support@amazon",
    "To discuss automated access",
    "/errors/validateCaptcha",
    "Type the characters you see in this image",
)

# Amazon domain -> currency. '$' is ambiguous, so currency comes from the domain
# rather than the price symbol.
_DOMAIN_CURRENCY = {
    "amazon.ca": "CAD", "amazon.com": "USD", "amazon.co.uk": "GBP",
    "amazon.com.mx": "MXN", "amazon.com.au": "AUD", "amazon.fr": "EUR",
    "amazon.de": "EUR", "amazon.es": "EUR", "amazon.it": "EUR",
    "amazon.nl": "EUR", "amazon.co.jp": "JPY", "amazon.in": "INR",
}

_ASIN_RE = re.compile(r"/(?:dp|gp/product|gp/aw/d|d|product)/([A-Z0-9]{10})", re.I)


class FetchBlocked(Exception):
    """Raised (internally) when Amazon returns a bot-check page."""


@dataclass
class ItemInfo:
    url: str
    asin: Optional[str] = None
    domain: str = "amazon.ca"
    title: Optional[str] = None
    price: Optional[float] = None
    currency: str = "CAD"
    ok: bool = False
    blocked: bool = False
    error: str = ""


# ── URL / parsing helpers (pure, offline-testable) ───────────────────────────

def asin_from_url(url: str) -> Optional[str]:
    """Extract the 10-char ASIN from a product URL, or None."""
    m = _ASIN_RE.search(url or "")
    return m.group(1).upper() if m else None


def domain_from_url(url: str) -> str:
    """Bare Amazon host (no www.), defaulting to amazon.ca for junk input."""
    try:
        netloc = urllib.parse.urlparse(url).netloc.lower()
    except Exception:
        netloc = ""
    netloc = netloc.split("@")[-1].split(":")[0]
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc or "amazon.ca"


def currency_for_domain(domain: str) -> str:
    return _DOMAIN_CURRENCY.get(domain, "CAD")


def canonical_url(asin: Optional[str], domain: str) -> Optional[str]:
    """Clean ``https://{domain}/dp/{ASIN}`` — strips tracking query junk."""
    if not asin:
        return None
    return f"https://{domain}/dp/{asin}"


def parse_price_text(text):
    """Parse a localized price string to a float.

    Handles US ('CDN$ 1,299.99'), EU ('1.299,00 EUR', '19,99 EUR'), French
    space-thousands ('1 299,99'), and whole numbers ('1,299' -> 1299). The
    decimal separator is decided by the *trailing group length*: a final
    separator followed by exactly two digits is the decimal point; a group of
    three digits is a thousands separator, so the value is an integer."""
    if not text:
        return None
    # Drop whitespace (incl. non-breaking / narrow spaces) between digits, so a
    # French '1 299,99' collapses to '1299,99'.
    t = re.sub(r"(?<=\d)[\s  ]+(?=\d)", "", text)
    m = re.search(r"\d[\d.,]*\d|\d", t)
    if not m:
        return None
    raw = m.group(0)
    seps = [i for i, ch in enumerate(raw) if ch in ".,"]
    if not seps:
        cleaned = raw
    else:
        last = seps[-1]
        trailing = len(raw) - last - 1
        if trailing == 2:
            int_part = raw[:last].replace(".", "").replace(",", "")
            cleaned = int_part + "." + raw[last + 1:]
        else:
            cleaned = raw.replace(".", "").replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None



# Product-page price selectors, most-specific first.
_PRICE_SELECTORS = (
    "#corePrice_feature_div span.a-price span.a-offscreen",
    "#corePriceDisplay_desktop_feature_div span.a-price span.a-offscreen",
    "#tp_price_block_total_price_ww span.a-offscreen",
    "span.a-price span.a-offscreen",
    "#priceblock_ourprice",
    "#priceblock_dealprice",
    "#price_inside_buybox",
)


def is_blocked_html(html: str) -> bool:
    return any(marker in html for marker in _BLOCK_MARKERS)


def parse_product(html: str, domain: str = "amazon.ca") -> ItemInfo:
    """Parse a product page's title + price out of its HTML."""
    info = ItemInfo(url="", domain=domain, currency=currency_for_domain(domain))
    soup = BeautifulSoup(html, "html.parser")

    title_el = soup.select_one("#productTitle")
    if title_el:
        info.title = title_el.get_text(strip=True) or None

    for sel in _PRICE_SELECTORS:
        el = soup.select_one(sel)
        if el:
            price = parse_price_text(el.get_text(" ", strip=True))
            if price is not None:
                info.price = price
                break

    info.ok = info.price is not None
    if not info.ok:
        info.error = "price not found"
    return info


def parse_wishlist(html: str, domain: str = "amazon.ca") -> list[dict]:
    """Best-effort scrape of a public wishlist page into seed dicts
    ``{asin, domain, url, title, price}``. Skips items with no resolvable ASIN.

    Wishlist markup changes often and lazy-loads extra pages, so this returns
    whatever it can find on the first page — callers treat it as a seed, not a
    guaranteed-complete list."""
    soup = BeautifulSoup(html, "html.parser")
    seeds: list[dict] = []
    seen: set[str] = set()

    for li in soup.select("li[data-itemid], li[data-id]"):
        link = None
        for a in li.select("a[href]"):
            if asin_from_url(a.get("href", "")):
                link = a
                break
        if link is None:
            continue
        asin = asin_from_url(link.get("href", ""))
        if not asin or asin in seen:
            continue
        seen.add(asin)
        title = (link.get("title") or link.get_text(strip=True) or "").strip() or None
        price_el = li.select_one("span.a-price span.a-offscreen, .a-price .a-offscreen")
        price = parse_price_text(price_el.get_text(" ", strip=True)) if price_el else None
        seeds.append({
            "asin": asin,
            "domain": domain,
            "url": canonical_url(asin, domain),
            "title": title,
            "price": price,
        })
    return seeds


# ── Network (not exercised by unit tests) ────────────────────────────────────

def _get(url: str) -> Optional[str]:
    """GET a URL, returning the body text or None on any failure."""
    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception:
        return None


def fetch_item(url: str) -> ItemInfo:
    """Fetch + parse a single product URL. Never raises."""
    domain = domain_from_url(url)
    asin = asin_from_url(url)
    canon = canonical_url(asin, domain) or url
    info = ItemInfo(url=canon, asin=asin, domain=domain,
                    currency=currency_for_domain(domain))

    html = _get(canon)
    if html is None:
        info.error = "network error"
        return info
    if is_blocked_html(html):
        info.blocked = True
        info.error = "blocked (captcha)"
        return info

    parsed = parse_product(html, domain)
    info.title = parsed.title
    info.price = parsed.price
    info.ok = parsed.ok
    info.error = parsed.error
    return info


def fetch_wishlist(url: str) -> list[dict]:
    """Fetch + parse a public wishlist page into seed dicts. [] on failure/block."""
    domain = domain_from_url(url)
    html = _get(url)
    if html is None or is_blocked_html(html):
        return []
    return parse_wishlist(html, domain)
