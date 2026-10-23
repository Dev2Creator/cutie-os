#!/usr/bin/env python3
"""CUTIE OS / GShop personal search helper.

Output contract: friendly text first, compact JSON array on the LAST stdout line.
Requires: requests, beautifulsoup4

This script reads search-engine result pages, then may inspect at most two
recognizable product-detail URLs per query for explicit structured price metadata.
It checks robots.txt, follows redirects only after checking each destination's
robots policy, observes per-host cooldowns, caches successful queries locally,
and never retries a 401/403/429/503 or CAPTCHA/bot-check response.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
import logging
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs, unquote
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

VERSION = "2.1.1"
MAX_RESULTS = 8
MAX_PRICE_ENRICH = 2          # at most two direct product pages per search
PRODUCT_TIMEOUT = (2.5, 4)   # keep background capture responsive
TIMEOUT = (4, 9)                 # connect timeout, read timeout
CACHE_TTL = 15 * 60              # successful search results: 15 minutes
ROBOTS_TTL = 6 * 60 * 60         # robots policy cache: 6 hours
MIN_HOST_INTERVAL = 8            # minimum between requests to the same host

HOME = Path.home()
CACHE_DIR = HOME / ".cache" / "cutie-os"
CACHE_FILE = CACHE_DIR / "momo-web-cache.json"
ROBOTS_FILE = CACHE_DIR / "momo-web-robots.json"
HOSTS_FILE = CACHE_DIR / "momo-web-hosts.json"
LOG_FILE = Path("/tmp/gshop-debug.log")

# Identifies this personal client honestly; it does not pretend to be a browser.
USER_AGENT = "CutieOS-GShop/2.0 (personal low-volume search; local TUI client)"
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.5",
    "Accept-Language": "en-IN,en;q=0.8",
    "Cache-Control": "no-cache",
}

# Override from shell if an instance goes offline:
# MOMO_SEARXNG_INSTANCES='https://your-instance.example,https://another.example'
DEFAULT_SEARXNG = [
    "https://searx.ononoki.org",
    "https://searx.oloke.xyz",
]

PRICE_RE = re.compile(
    r"(?:₹\s*[\d][\d,]*(?:\.\d{1,2})?|"
    r"Rs\.?\s*[\d][\d,]*(?:\.\d{1,2})?|"
    r"INR\s*[\d][\d,]*(?:\.\d{1,2})?|"
    r"US\$\s*[\d][\d,]*(?:\.\d{1,2})?|"
    r"[$€£]\s*[\d][\d,]*(?:\.\d{1,2})?)",
    re.IGNORECASE,
)
CHALLENGE_RE = re.compile(
    r"captcha|verify you are human|verify you're human|unusual traffic|"
    r"automated quer(?:y|ies)|bot.?check|robot check|access denied|"
    r"security challenge|cf-chl-|challenge-platform",
    re.IGNORECASE,
)

class EngineBlocked(Exception):
    """An endpoint explicitly denied the request or returned a challenge."""

class RobotsDenied(Exception):
    """robots.txt does not allow this request URL for this client."""

class EngineEmpty(Exception):
    """A page loaded but no usable search result rows were found."""


def log(message: str) -> None:
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}\n")
    except OSError:
        pass


def load_json(path: Path, default):
    try:
        with path.open("r", encoding="utf-8") as fh:
            value = json.load(fh)
        return value if isinstance(value, type(default)) else default
    except (OSError, ValueError, TypeError):
        return default


def save_json(path: Path, value) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(value, fh, ensure_ascii=False, separators=(",", ":"))
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
        tmp.replace(path)
    except (OSError, TypeError, ValueError) as exc:
        log(f"CACHE write failed path={path.name} error={exc!r}")


def normalized_host(url: str) -> str:
    return (urlparse(url).hostname or "").lower().removeprefix("www.")


def origin(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def read_robots(base_url: str) -> tuple[bool, int | None, str]:
    """Return (allowed-to-read-robots, crawl_delay, reason); fail closed on errors."""
    host = normalized_host(base_url)
    robots_cache = load_json(ROBOTS_FILE, {})
    cached = robots_cache.get(host)
    now = time.time()
    if isinstance(cached, dict) and now - float(cached.get("ts", 0)) < ROBOTS_TTL:
        return bool(cached.get("allowed", False)), cached.get("delay"), str(cached.get("reason", "cached"))

    robots_url = origin(base_url) + "/robots.txt"
    try:
        response = requests.get(robots_url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        if response.status_code in (404, 410):
            result = (True, None, f"robots.txt absent ({response.status_code})")
        elif response.status_code != 200:
            result = (False, None, f"robots.txt HTTP {response.status_code}; fail-closed")
        else:
            parser = RobotFileParser()
            parser.set_url(robots_url)
            parser.parse(response.text.splitlines())
            allowed = parser.can_fetch(USER_AGENT, base_url)
            delay = parser.crawl_delay(USER_AGENT)
            if delay is None:
                delay = parser.crawl_delay("*")
            result = (bool(allowed), int(delay) if delay is not None else None,
                      "robots allows URL" if allowed else "robots disallows URL")
    except requests.RequestException as exc:
        result = (False, None, f"robots.txt unavailable; fail-closed ({type(exc).__name__})")

    robots_cache[host] = {"ts": now, "allowed": result[0], "delay": result[1], "reason": result[2]}
    save_json(ROBOTS_FILE, robots_cache)
    return result


def respect_robots(url: str) -> None:
    allowed, delay, reason = read_robots(url)
    log(f"ROBOTS host={normalized_host(url)} allowed={allowed} reason={reason}")
    if not allowed:
        raise RobotsDenied(reason)
    # Avoid unexpectedly freezing the TUI if an operator publishes a large delay.
    if delay:
        if delay > 10:
            raise RobotsDenied(f"robots Crawl-delay={delay}s; skipped to keep TUI responsive")
        time.sleep(max(0, delay))


def host_is_cooling_down(url: str) -> bool:
    host = normalized_host(url)
    host_state = load_json(HOSTS_FILE, {})
    last = host_state.get(host)
    return isinstance(last, (int, float)) and time.time() - last < MIN_HOST_INTERVAL


def mark_host_used(url: str) -> None:
    host = normalized_host(url)
    host_state = load_json(HOSTS_FILE, {})
    host_state[host] = time.time()
    # Keep the state file bounded.
    if len(host_state) > 100:
        host_state = dict(list(host_state.items())[-80:])
    save_json(HOSTS_FILE, host_state)


def get_page(engine: str, url: str, *, method: str = "GET", params=None, data=None) -> str:
    """Fetch one search page while respecting robots and a per-host cooldown."""
    respect_robots(url)
    if host_is_cooling_down(url):
        raise EngineEmpty(f"per-host cooldown ({MIN_HOST_INTERVAL}s)")
    log(f"REQUEST engine={engine} method={method} url={url}")
    mark_host_used(url)
    try:
        if method.upper() == "POST":
            response = requests.post(url, headers=HEADERS, data=data, timeout=TIMEOUT, allow_redirects=True)
        else:
            response = requests.get(url, headers=HEADERS, params=params, timeout=TIMEOUT, allow_redirects=True)
    except requests.RequestException as exc:
        log(f"FAIL engine={engine} network={type(exc).__name__}: {exc}")
        raise EngineEmpty(f"network error: {type(exc).__name__}") from exc

    if response.status_code in (401, 403, 429, 503):
        log(f"BLOCK engine={engine} status={response.status_code}")
        raise EngineBlocked(f"HTTP {response.status_code}")
    if response.status_code >= 400:
        log(f"FAIL engine={engine} status={response.status_code}")
        raise EngineEmpty(f"HTTP {response.status_code}")

    body_start = response.text[:9000]
    if CHALLENGE_RE.search(body_start) and not BeautifulSoup(body_start, "html.parser").select(
        "article.result, div.result, .w-gl__result, .result__a"
    ):
        log(f"BLOCK engine={engine} challenge-page=true")
        raise EngineBlocked("CAPTCHA/bot-check/challenge page")
    return response.text


def clean_text(node) -> str:
    if node is None:
        return ""
    return re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip()


def unwrap_result_url(href: str, base_url: str) -> str:
    href = (href or "").strip()
    if not href or href.startswith(("#", "javascript:", "mailto:")):
        return ""
    candidate = urljoin(base_url, href)
    parsed = urlparse(candidate)
    # Unwrap common query-parameter redirect links when the link points back
    # to the search frontend itself.
    if normalized_host(candidate) == normalized_host(base_url):
        qs = parse_qs(parsed.query)
        for key in ("url", "uddg", "target", "u", "r"):
            value = qs.get(key, [""])[0]
            if value.startswith(("http://", "https://")):
                candidate = unquote(value)
                parsed = urlparse(candidate)
                break
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return ""
    if normalized_host(candidate) == normalized_host(base_url):
        return ""
    # Remove URL fragment; keep query params because they may be product variants.
    return parsed._replace(fragment="").geturl()


def first_anchor(block, base_url: str):
    selectors = (
        "h3 a[href]", "a.result_header[href]", "a.result__a[href]",
        "a.w-gl__result-title[href]", "a.result-title[href]",
        "a.title[href]", ".title a[href]", "a[href]",
    )
    for selector in selectors:
        for anchor in block.select(selector):
            title = clean_text(anchor)
            url = unwrap_result_url(anchor.get("href", ""), base_url)
            if title and url and len(title) > 2:
                return anchor, title, url
    return None, "", ""


def get_snippet(block, title_anchor) -> str:
    selectors = (
        ".result__snippet", ".result__body", ".w-gl__description",
        ".content", ".result-content", ".result-snippet", ".snippet",
        "[class*='snippet']", "[class*='description']", "p",
    )
    for selector in selectors:
        for node in block.select(selector):
            text = clean_text(node)
            if text and text != clean_text(title_anchor) and len(text) >= 20:
                return text[:550]
    text = clean_text(block)
    title = clean_text(title_anchor)
    if title and text.startswith(title):
        text = text[len(title):].strip(" :-–|")
    return text[:550]


def price_info(text: str) -> tuple[str, str]:
    """Return the first plausible item price, ignoring obvious promo/savings amounts.

    Search snippets can contain "₹4,500 - ₹81,500 off" or "save ₹5,000";
    those are not the product's selling price. Leave the price empty rather than
    presenting a discount/trade-in value as the item price.
    """
    text = text or ""
    matches = list(PRICE_RE.finditer(text))
    if not matches:
        return "", ""

    for index, match in enumerate(matches):
        start, end = match.span()
        before = text[max(0, start - 45):start]
        after = text[end:min(len(text), end + 65)]

        # A price immediately introduced as a saving/exchange amount is not a
        # selling price. A number followed by "off" is a discount, not a price.
        if re.search(r"\b(?:save|saves|saving|savings|discount|cashback|trade[- ]?in value|exchange value)\s*[:=\-]?\s*$", before, re.I):
            continue
        if re.match(r"\s*(?:[-–—:]\s*)?(?:off\b|discount\b|cashback\b|in savings\b)", after, re.I):
            continue

        # Reject both amounts in common promotional ranges such as
        # "₹4,500 - ₹81,500 off". Do not reject prices merely because a later
        # sentence mentions a discount.
        next_match = matches[index + 1] if index + 1 < len(matches) else None
        if next_match and next_match.start() - end < 30:
            between_and_after = text[end:min(len(text), next_match.end() + 30)]
            if re.search(r"\b(?:off|discount|savings?)\b", between_and_after, re.I):
                continue

        price = re.sub(r"\s+", " ", match.group(0)).strip()
        if price.startswith("Rs") or price.upper().startswith("INR"):
            currency = "₹"
        else:
            currency = next((symbol for symbol in ("₹", "US$", "$", "€", "£") if price.startswith(symbol)), "")
        return price, currency
    return "", ""


def country_from_host(host: str, url: str = "") -> str:
    """Best-effort storefront country; generic .com is not automatically US."""
    host = (host or "").lower().removeprefix("www.")
    path = urlparse(url).path.lower() if url else ""

    # Well-known India-oriented retailers/publishers that use .com/.app domains.
    if host.endswith(".in") or host in {
        "flipkart.com", "myntra.com", "meesho.com", "jiomart.com",
        "croma.com", "pricehistory.app", "gadgets360.com", "vijaysales.com",
        "reliancedigital.in",
    }:
        return "in"
    if host == "apple.com":
        if path.startswith("/in/") or path == "/in":
            return "in"
        if path.startswith(("/uk/", "/gb/")):
            return "gb"
        if path.startswith("/ca/"):
            return "ca"
        if path.startswith("/au/"):
            return "au"
        if path.startswith("/us/") or path == "/us":
            return "us"
    if host.endswith(".uk") or host.endswith(".co.uk"):
        return "gb"
    if host.endswith(".ca"):
        return "ca"
    if host.endswith(".au") or host.endswith(".com.au"):
        return "au"
    if host in {"amazon.com", "bestbuy.com", "walmart.com", "target.com"} or host.endswith(".us"):
        return "us"
    # A bare .com gives no reliable country evidence.
    return ""


def parse_blocks(html: str, base_url: str, engine: str, selectors: tuple[str, ...]) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    blocks = []
    for selector in selectors:
        found = soup.select(selector)
        if found:
            # Prefer specific block selectors; don't merge overlapping selectors.
            blocks = found
            break
    output = []
    seen = set()
    for block in blocks:
        anchor, title, url = first_anchor(block, base_url)
        if not anchor:
            continue
        url = url[:1800]
        if url in seen:
            continue
        seen.add(url)
        snippet = get_snippet(block, anchor)
        full_text = clean_text(block)
        price, currency = price_info(full_text + " " + snippet + " " + title)
        host = normalized_host(url)
        country = country_from_host(host, url)
        output.append({
            "t": title[:240],
            "u": url,
            "s": snippet,
            "p": price,
            "r": country,
            "c": currency,
            "h": host,
        })
        if len(output) >= MAX_RESULTS:
            break
    log(f"PARSE engine={engine} blocks={len(blocks)} results={len(output)}")
    return output


def parse_searxng(html: str, base_url: str) -> list[dict]:
    # article.result is used by the current SearXNG simple HTML theme; the
    # alternatives support older/custom themes without depending on JSON API.
    return parse_blocks(html, base_url, "SearXNG", (
        "#urls article.result", "article.result", "#urls .result", "div.result",
    ))


def parse_startpage(html: str, base_url: str) -> list[dict]:
    return parse_blocks(html, base_url, "Startpage", (
        ".w-gl__result", "div.w-gl__result", "main article", "div.result", "article",
    ))


def parse_duckduckgo(html: str, base_url: str) -> list[dict]:
    return parse_blocks(html, base_url, "DuckDuckGo", (
        "div.result", "div.web-result", "article.result",
    ))



# Only attempt enrichment on known merchant domains. Search-result pages are
# deliberately excluded; we must never attach one item's price to a generic
# store/search landing page.
SHOP_DOMAINS = (
    "amazon.in", "amazon.com", "amazon.co.uk", "amazon.ca", "amazon.com.au",
    "flipkart.com", "ebay.com", "ebay.in", "ebay.co.uk", "walmart.com",
    "bestbuy.com", "target.com", "croma.com", "reliancedigital.in",
    "vijaysales.com", "myntra.com", "meesho.com", "jiomart.com",
)

CURRENCY_SYMBOLS = {
    "INR": "₹", "USD": "$", "GBP": "£", "EUR": "€", "CAD": "C$",
    "AUD": "A$", "JPY": "¥", "CNY": "¥", "SGD": "S$",
}


def is_shop_host(host: str) -> bool:
    host = (host or "").lower().removeprefix("www.")
    return any(host == domain or host.endswith("." + domain) for domain in SHOP_DOMAINS)


def is_likely_product_url(url: str) -> bool:
    """Recognize common product-detail URL patterns; reject store/search pages."""
    parsed = urlparse(url)
    host = normalized_host(url)
    path = (parsed.path or "").lower()
    if not is_shop_host(host):
        return False
    if host.endswith(("amazon.in", "amazon.com", "amazon.co.uk", "amazon.ca", "amazon.com.au")):
        return bool(re.search(r"/(?:dp|gp/product|gp/aw/d)/[a-z0-9]{8,}(?:/|$)", path, re.I))
    if host.endswith("flipkart.com"):
        return bool(re.search(r"/p/[a-z0-9]{6,}", path, re.I))
    if host.endswith(("ebay.com", "ebay.in", "ebay.co.uk")):
        return bool(re.search(r"/itm/(?:[^/]+/)?\d{8,}", path, re.I))
    if host.endswith("walmart.com"):
        return bool(re.search(r"/ip/.+/\d{6,}", path, re.I))
    if host.endswith("bestbuy.com"):
        return bool(re.search(r"/site/.+\.p/\d{6,}", path, re.I))
    if host.endswith("target.com"):
        return bool(re.search(r"/p/.+/-/A-\d+", path, re.I))
    # Other shop sites have inconsistent URL styles. Reject known search/cart paths,
    # and require a product-like path rather than their root or listing page.
    if any(token in path for token in ("/search", "/category", "/cart", "/checkout", "/collections")):
        return False
    segments = [part for part in path.split("/") if part]
    return len(segments) >= 2 and len(path) >= 12


def _money_from_value(value, currency: str = "") -> tuple[str, str]:
    """Normalize a structured price value; return (display price, symbol)."""
    if value is None:
        return "", ""
    raw = str(value).strip()
    if not raw or len(raw) > 40:
        return "", ""
    found, found_currency = price_info(raw)
    if found:
        return found, found_currency
    # Accept only a numeric structured-data price, never arbitrary nearby numbers.
    numeric = re.fullmatch(r"\s*(\d+(?:[.,]\d{1,2})?)\s*", raw)
    if not numeric:
        return "", ""
    number = numeric.group(1).replace(",", "")
    try:
        amount = Decimal(number)
    except InvalidOperation:
        return "", ""
    if amount < 0 or amount > Decimal("100000000000"):
        return "", ""
    code = (currency or "").upper().strip()
    symbol = CURRENCY_SYMBOLS.get(code, code if len(code) == 1 else "")
    if not symbol:
        return "", ""
    # Format from ungrouped digits to avoid duplicate commas. INR uses the
    # Indian 3-2-2 grouping; other currencies use conventional 3-digit groups.
    is_integer = amount == amount.to_integral_value()
    raw_number = str(int(amount)) if is_integer else f"{amount:.2f}"
    whole, dot, fraction = raw_number.partition(".")
    if code == "INR":
        tail = whole[-3:]
        head = whole[:-3]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        whole = ",".join(groups + [tail]) if groups else tail
    else:
        whole = f"{int(whole):,}"
    value_text = whole + (dot + fraction if dot else "")
    return f"{symbol}{value_text}", symbol


def _iter_product_nodes(value):
    """Yield Product/ProductGroup dicts from JSON-LD, including @graph nesting."""
    if isinstance(value, dict):
        kind = value.get("@type", "")
        types = kind if isinstance(kind, list) else [kind]
        if any(str(t).lower() in {"product", "productgroup"} for t in types):
            yield value
        for child in value.values():
            yield from _iter_product_nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_product_nodes(child)


def _extract_jsonld_price(soup: BeautifulSoup) -> tuple[str, str]:
    for script in soup.select('script[type*="ld+json"]'):
        raw = script.string or script.get_text("", strip=True)
        if not raw or len(raw) > 1_500_000:
            continue
        try:
            parsed = json.loads(raw.strip().lstrip("\ufeff"))
        except (ValueError, TypeError):
            continue
        for product in _iter_product_nodes(parsed):
            offers = product.get("offers", [])
            if isinstance(offers, dict):
                offers = [offers]
            if not isinstance(offers, list):
                continue
            for offer in offers:
                if not isinstance(offer, dict):
                    continue
                # Do not report out-of-stock offers as a live buy price.
                availability = str(offer.get("availability", "")).lower()
                if availability and any(word in availability for word in ("outofstock", "discontinued", "soldout")):
                    continue
                currency = offer.get("priceCurrency", "")
                price = offer.get("price")
                if price is None:
                    spec = offer.get("priceSpecification")
                    if isinstance(spec, dict):
                        price = spec.get("price") or spec.get("minPrice")
                        currency = spec.get("priceCurrency", currency)
                if price is None:
                    price = offer.get("lowPrice")
                formatted, symbol = _money_from_value(price, str(currency or ""))
                if formatted:
                    return formatted, symbol
    return "", ""


def extract_product_page_price(html: str) -> tuple[str, str]:
    """Extract price from explicit product metadata, not arbitrary page numbers."""
    soup = BeautifulSoup(html, "html.parser")

    # Structured Product offers are the most reliable source.
    price, currency = _extract_jsonld_price(soup)
    if price:
        return price, currency

    # Common Open Graph / microdata price fields.
    amount = ""
    code = ""
    amount_selectors = (
        'meta[property="product:price:amount"]',
        'meta[property="og:price:amount"]',
        'meta[itemprop="price"]',
        '[itemprop="price"][content]',
        'meta[name="twitter:data1"]',
    )
    for selector in amount_selectors:
        node = soup.select_one(selector)
        if node:
            amount = node.get("content") or node.get_text(" ", strip=True)
            if amount:
                break
    currency_selectors = (
        'meta[property="product:price:currency"]',
        'meta[property="og:price:currency"]',
        'meta[itemprop="priceCurrency"]',
        '[itemprop="priceCurrency"][content]',
    )
    for selector in currency_selectors:
        node = soup.select_one(selector)
        if node:
            code = node.get("content") or node.get_text(" ", strip=True)
            if code:
                break
    price, symbol = _money_from_value(amount, code)
    if price:
        return price, symbol

    # Product page-specific UI fragments. We do not scan the entire page text,
    # as dates, review counts, and unrelated prices can be mistaken for a price.
    selectors = (
        "[itemprop='price']", "[data-testid*='price']", "[data-test*='price']",
        ".a-price .a-offscreen", ".priceToPay .a-offscreen", ".product-price",
        ".selling-price", ".price-box .price", ".price-current",
    )
    for selector in selectors:
        for node in soup.select(selector)[:4]:
            text = clean_text(node) or str(node.get("content", ""))
            price, symbol = price_info(text)
            if price:
                return price, symbol
    return "", ""


def fetch_product_page(url: str) -> str:
    """Read a permitted product page, respecting robots and redirects at each hop."""
    current = url
    for redirect_count in range(5):
        if not is_shop_host(normalized_host(current)):
            raise EngineEmpty("redirect left supported merchant domains")
        respect_robots(current)
        if host_is_cooling_down(current):
            raise EngineEmpty(f"merchant cooldown ({MIN_HOST_INTERVAL}s)")
        mark_host_used(current)
        try:
            response = requests.get(
                current, headers=HEADERS, timeout=PRODUCT_TIMEOUT,
                allow_redirects=False,
            )
        except requests.RequestException as exc:
            log(f"PRICE_FAIL host={normalized_host(current)} network={type(exc).__name__}")
            raise EngineEmpty(f"product page network error: {type(exc).__name__}") from exc
        if response.status_code in (301, 302, 303, 307, 308):
            location = response.headers.get("Location", "")
            if not location:
                raise EngineEmpty("redirect without Location")
            current = urljoin(current, location)
            continue
        if response.status_code in (401, 403, 429, 503):
            log(f"PRICE_BLOCK host={normalized_host(current)} status={response.status_code}")
            raise EngineBlocked(f"merchant HTTP {response.status_code}")
        if response.status_code != 200:
            raise EngineEmpty(f"merchant HTTP {response.status_code}")
        html = response.text
        if CHALLENGE_RE.search(html[:9000]) and not BeautifulSoup(html[:9000], "html.parser").select(
            'script[type*="ld+json"], [itemprop="price"], meta[property*="price"]'
        ):
            log(f"PRICE_BLOCK host={normalized_host(current)} challenge-page=true")
            raise EngineBlocked("merchant challenge page")
        return html
    raise EngineEmpty("too many merchant redirects")


def enrich_missing_prices(results: list[dict]) -> list[dict]:
    """Try a small, polite number of explicit product pages for structured prices."""
    attempted_hosts = set()
    attempts = 0
    for row in results:
        if row.get("p") or not is_likely_product_url(row.get("u", "")):
            continue
        host = normalized_host(row.get("u", ""))
        if host in attempted_hosts:
            continue
        attempted_hosts.add(host)
        if attempts >= MAX_PRICE_ENRICH:
            break
        attempts += 1
        try:
            log(f"PRICE_TRY host={host} url={row.get('u', '')[:220]}")
            html = fetch_product_page(row["u"])
            price, symbol = extract_product_page_price(html)
            if price:
                row["p"] = price
                row["c"] = symbol or row.get("c", "")
                log(f"PRICE_FOUND host={host} price={price}")
            else:
                log(f"PRICE_MISSING host={host} metadata=no-price")
        except (RobotsDenied, EngineBlocked, EngineEmpty) as exc:
            log(f"PRICE_SKIP host={host} reason={exc}")
        except Exception as exc:
            log(f"PRICE_FAIL host={host} error={type(exc).__name__}: {exc}")
    return results


def sort_for_shopping(results: list[dict]) -> list[dict]:
    """Bring exact prices and merchant links forward without fabricating prices."""
    def key(row):
        url = row.get("u", "")
        host = normalized_host(url)
        return (
            bool(row.get("p")),
            is_likely_product_url(url),
            is_shop_host(host),
        )
    return sorted(results, key=key, reverse=True)

def query_cache_key(query: str) -> str:
    # Include the parser version so an upgrade cannot reuse stale prices from
    # an older build (for example, a trade-in offer mistaken for item price).
    material = f"{VERSION}\0{query.casefold().strip()}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def cached_results(query: str):
    cache = load_json(CACHE_FILE, {})
    row = cache.get(query_cache_key(query))
    if not isinstance(row, dict) or time.time() - float(row.get("ts", 0)) > CACHE_TTL:
        return None
    results = row.get("results")
    return results if isinstance(results, list) and results else None


def cache_results(query: str, engine: str, results: list[dict]) -> None:
    if not results:
        return
    cache = load_json(CACHE_FILE, {})
    cache[query_cache_key(query)] = {"ts": time.time(), "engine": engine, "results": results}
    if len(cache) > 120:
        cache = dict(sorted(cache.items(), key=lambda item: item[1].get("ts", 0))[-100:])
    save_json(CACHE_FILE, cache)


def searxng_bases() -> list[str]:
    configured = os.environ.get("MOMO_SEARXNG_INSTANCES", "").strip()
    raw = configured.split(",") if configured else DEFAULT_SEARXNG
    bases = []
    for item in raw:
        item = item.strip().rstrip("/")
        parsed = urlparse(item)
        if parsed.scheme == "https" and parsed.netloc and parsed.path in ("", "/"):
            if item not in bases:
                bases.append(item)
    return bases


def search_all(query: str) -> tuple[list[dict], str, list[str]]:
    failures = []
    # SearXNG first: HTML only, no JSON API assumption. If one public instance
    # is down/empty, try the next. A 403/429/challenge stops attempts against
    # the rest of the SearXNG instances for this invocation.
    for base in searxng_bases():
        url = base + "/search"
        name = f"SearXNG {normalized_host(base)}"
        try:
            html = get_page(name, url, params={"q": query, "language": "en", "categories": "general", "safesearch": 1})
            results = parse_searxng(html, base)
            if results:
                return results, name, failures
            failures.append(f"{name}: HTML returned but no result cards parsed")
            log(f"EMPTY engine={name} no-usable-result-cards")
        except EngineBlocked as exc:
            failures.append(f"{name}: blocked/challenge ({exc})")
            log(f"SKIP remaining SearXNG instances after blocked host={normalized_host(base)}")
            break
        except (RobotsDenied, EngineEmpty) as exc:
            failures.append(f"{name}: {exc}")
            log(f"FAIL engine={name} reason={exc}")
        except Exception as exc:
            failures.append(f"{name}: {type(exc).__name__}")
            log(f"FAIL engine={name} unexpected={type(exc).__name__}: {exc}")

    # Startpage's documented GET form, parsed as HTML. No API key involved.
    try:
        base = "https://www.startpage.com"
        url = base + "/do/dsearch"
        html = get_page("Startpage", url, params={"q": query, "cat": "web", "language": "english"})
        results = parse_startpage(html, base)
        if results:
            return results, "Startpage", failures
        failures.append("Startpage: HTML returned but no result cards parsed")
        log("EMPTY engine=Startpage no-usable-result-cards")
    except (EngineBlocked, RobotsDenied, EngineEmpty) as exc:
        failures.append(f"Startpage: {exc}")
        log(f"FAIL engine=Startpage reason={exc}")
    except Exception as exc:
        failures.append(f"Startpage: {type(exc).__name__}")
        log(f"FAIL engine=Startpage unexpected={type(exc).__name__}: {exc}")

    # Last resort: the legacy DDG HTML POST endpoint. A block is recorded and
    # not retried; it won't loop or switch DuckDuckGo hosts to evade the block.
    try:
        base = "https://html.duckduckgo.com"
        url = base + "/html/"
        html = get_page("DuckDuckGo", url, method="POST", data={"q": query})
        results = parse_duckduckgo(html, base)
        if results:
            return results, "DuckDuckGo", failures
        failures.append("DuckDuckGo: HTML returned but no result cards parsed")
        log("EMPTY engine=DuckDuckGo no-usable-result-cards")
    except (EngineBlocked, RobotsDenied, EngineEmpty) as exc:
        failures.append(f"DuckDuckGo: {exc}")
        log(f"FAIL engine=DuckDuckGo reason={exc}")
    except Exception as exc:
        failures.append(f"DuckDuckGo: {type(exc).__name__}")
        log(f"FAIL engine=DuckDuckGo unexpected={type(exc).__name__}: {exc}")

    return [], "", failures


def emit(query: str, results: list[dict], engine: str = "", failures=None, cached=False) -> None:
    failures = failures or []
    print("🛍️  CUTIE OS • GShop search")
    print(f"🔎 Query: {query}")
    if cached:
        print("🧊 Cache hit — internet ko dobara poke nahi kiya.")
    elif engine:
        print(f"🌐 Engine: {engine}")
    if results:
        print(f"✨ {len(results)} result(s) mile — price snippet ya permitted product metadata mein mile toh dikhega.")
        for index, row in enumerate(results, 1):
            price = f"  {row.get('p')}" if row.get("p") else ""
            print(f"{index:02d}. {row.get('t', '(untitled)')[:120]}{price}")
            print(f"    {row.get('h', '')}  •  {row.get('u', '')}")
            if row.get("s"):
                print(f"    {row['s'][:180]}")
    else:
        print("😿 Is baar usable results nahi mile. Ye zaroori nahi ki query ka result zero ho:")
        for reason in failures[:5]:
            print(f"   • {reason}")
        print("🧪 Debug: /tmp/gshop-debug.log")
    # CRITICAL CUTIE CONTRACT: exactly one compact JSON-array line at EOF.
    print(json.dumps(results, ensure_ascii=False, separators=(",", ":")))


def main() -> int:
    query = " ".join(arg for arg in sys.argv[1:] if arg.strip()).strip()
    if not query:
        print("Usage: python3 ~/momo-web.py <search words>")
        print("[]")
        return 2

    log(f"START version={VERSION} query={query!r}")
    cached = cached_results(query)
    if cached:
        emit(query, cached, cached=True)
        log(f"CACHE_HIT count={len(cached)}")
        return 0

    results, engine, failures = search_all(query)
    if results:
        # Search snippets often omit prices. Try a tiny number of direct product
        # pages only when the URL is a recognizable product page and robots permits it.
        results = enrich_missing_prices(results)
        results = sort_for_shopping(results)[:MAX_RESULTS]
        cache_results(query, engine, results)
        priced = sum(bool(row.get("p")) for row in results)
        log(f"SUCCESS engine={engine} count={len(results)} priced={priced}")
    else:
        log("NO_RESULTS failures=" + repr(failures))
    emit(query, results, engine=engine, failures=failures)
    return 0 if results else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        # Keep the last line machine-readable if interrupted before search starts.
        print("😿 Search cancelled.")
        print("[]")
        raise SystemExit(130)
    except Exception as exc:
        log(f"FATAL {type(exc).__name__}: {exc}")
        print(f"😿 Internal search error: {type(exc).__name__}")
        print("[]")
        raise SystemExit(1)
