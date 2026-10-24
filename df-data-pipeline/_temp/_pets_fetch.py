# -*- coding: utf-8 -*-
"""抓 wowhead forever 小动物新闻页（en + cn）。"""
from curl_cffi import requests
import os, time, re

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "_ref_pets")
os.makedirs(OUT, exist_ok=True)
PROXIES = {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}

PAGES = {
    "capitals": "earn-two-new-pets-in-capital-cities-in-wow-forever-383170",
    "gustjumper": "how-to-get-the-new-musical-gustjumper-pet-in-wow-forever-383087",
}

for k, slug in PAGES.items():
    for loc in ("cn", "us"):
        out = os.path.join(OUT, "wh_%s_%s.html" % (k, loc))
        if os.path.exists(out) and os.path.getsize(out) > 20000:
            print("%-12s %s 缓存" % (k, loc)); continue
        url = "https://www.wowhead.com/forever/%s/news/%s" % (loc, slug)
        try:
            r = requests.get(url, proxies=PROXIES, impersonate="chrome110", timeout=40)
            open(out, "w", encoding="utf-8").write(r.text)
            print("%-12s %-3s %s len=%d" % (k, loc, r.status_code, len(r.text)))
        except Exception as e:
            print("%-12s %-3s FAIL %s" % (k, loc, e))
        time.sleep(1.5)
print("done")
