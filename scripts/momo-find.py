#!/usr/bin/env python3
# momo-find — Momo Amazon.in pe dhoondhti hai 🐱
import sys

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("💔 pehle ye chalao: sudo pacman -S python-requests python-beautifulsoup4")
    sys.exit(1)

H = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept-Language": "en-IN,en;q=0.9",
}

MOMO_LINES = (
    "momo: sabse sasta wala 3rd number pe hai 👀",
    "momo: rating 4+ wale safe hain ⭐",
    "momo: haan ye maine khud order nahi kiya, tu kar lena 😼",
    "momo: stealth tip — 'buy' command se list bana ke mangwa 👑",
)


def search(query, limit=5):
    url = "https://www.amazon.in/s?k=" + requests.utils.quote(query)
    try:
        r = requests.get(url, headers=H, timeout=15)
    except Exception as e:
        print("😿 momo internet tak nahi pahunchi:", str(e)[:50])
        return
    soup = BeautifulSoup(r.content, "html.parser")
    items = soup.select("div[data-component-type='s-search-result']")[:limit]
    if not items:
        print("😿 momo ko Amazon ne block kar diya (bot-check page aaya)")
        print("   thodi der baad try karna, ya browser me dekh lena 🙏")
        return
    print("✨ Momo ne ye nikale:\n")
    for i, item in enumerate(items, 1):
        h2 = item.select_one("h2 span")
        name = h2.get_text(strip=True)[:64] if h2 else "(naam nahi mila)"
        price = item.select_one("span.a-price-whole")
        rating = item.select_one("span.a-icon-alt")
        ptxt = "₹" + price.get_text(strip=True) if price else "Out of stock"
        rtxt = rating.get_text(strip=True)[:14] if rating else "—"
        print("%d. %s" % (i, name))
        print("   💰 %s   ⭐ %s" % (ptxt, rtxt))
    import random
    print()
    print("🐾 " + random.choice(MOMO_LINES))


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]).strip()
    if not q:
        print("usage: momo-find whisper ultra large   ya: find sofy panty")
        sys.exit(1)
    search(q)
