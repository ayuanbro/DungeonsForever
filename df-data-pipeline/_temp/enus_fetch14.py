# -*- coding: utf-8 -*-
import re, sys
sys.stdout.reconfigure(encoding="utf-8")
from curl_cffi import requests
HDRS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0.0.0 Safari/537.36"}

def ttl(url):
    r = requests.get(url, headers=HDRS, proxy="http://127.0.0.1:7897",
                     impersonate="chrome", timeout=20)
    m = re.search(r"<title>(.*?)</title>", r.text, re.S)
    print(url, "->", m.group(1).strip() if m else r.status_code)
    return r

ttl("https://www.wowhead.com/classic/cn/npc=1344")
ttl("https://www.wowhead.com/npc=1344")
r = ttl("https://www.wowhead.com/quest=739")
hits = sorted(set(re.findall(r"[A-Za-z'\\]*(?:[Cc]arcass|[Rr]emains|[Cc]orpse|keleton)[A-Za-z'\\]*", r.text)))
print("remains-ish:", hits[:10])
