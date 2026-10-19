import json
import sys
import time

from playwright.sync_api import sync_playwright

PROXY = {"server": "http://127.0.0.1:7897"}
EXE = (r"C:/Users/Administrator/AppData/Local/ms-playwright/"
       r"chromium-1247/chrome-win64/chrome.exe")


def search_kinds(pw, name):
    br = pw.chromium.launch(headless=True, executable_path=EXE,
                            proxy=PROXY)
    pg = br.new_page(user_agent=(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0"))
    url = ("https://www.wowhead.com/forever/search?q="
           + requests_quote(name))
    pg.goto(url, wait_until="domcontentloaded", timeout=45000)
    pg.wait_for_timeout(4000)
    html = pg.content()
    import re
    npcs = re.findall(r'href="[^"]*/forever/npc=(\d+)[^"]*"', html)
    quests = re.findall(r'href="[^"]*/forever/quest=(\d+)[^"]*"', html)
    # 标题文本对照
    titles = re.findall(r'<a[^>]*href="[^"]*/forever/(npc|quest)=(\d+)[^"]*"[^>]*>([^<]+)<', html)
    br.close()
    return npcs[:5], quests[:5], titles[:6]


def requests_quote(s):
    import urllib.parse
    return urllib.parse.quote(s)


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "Anub'Rekhan"
    with sync_playwright() as pw:
        n, q, t = search_kinds(pw, name)
    print("npcs:", n)
    print("quests:", q)
    for k, i, txt in t:
        print("  ", k, i, txt.strip()[:50])
