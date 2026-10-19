# -*- coding: utf-8 -*-
import io, re, sys, time
sys.stdout.reconfigure(encoding="utf-8")
from curl_cffi import requests
HDRS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"}

def _get(url):
    for a in range(4):
        try:
            r = requests.get(url, headers=HDRS, proxy="http://127.0.0.1:7897",
                             impersonate="chrome", timeout=20)
        except Exception as e:
            print(" ERR", e); time.sleep(5); continue
        if r.status_code == 403:
            time.sleep((15, 25, 35, 45)[a]); continue
        return r
    return None

for url in ("https://www.wowhead.com/npc=9037",
            "https://www.wowhead.com/npc=9156",
            "https://www.wowhead.com/object=131474",
            "https://www.wowhead.com/object=164869",
            "https://www.wowhead.com/classic/cn/npc=9037",
            "https://www.wowhead.com/classic/cn/npc=9156"):
    r = _get(url)
    t = None
    if r is not None and r.status_code == 200:
        m = re.search(r"<title>(.*?)</title>", r.text, re.S)
        t = m.group(1).strip() if m else None
    print(url, "->", t)
    time.sleep(1)
