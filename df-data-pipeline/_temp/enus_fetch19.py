# -*- coding: utf-8 -*-
import re, sys, time
sys.stdout.reconfigure(encoding="utf-8")
from curl_cffi import requests
HDRS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0.0.0 Safari/537.36"}

def _get(url):
    for a in range(3):
        try:
            r = requests.get(url, headers=HDRS, proxy="http://127.0.0.1:7897",
                             impersonate="chrome", timeout=20)
        except Exception as e:
            print(" ERR", e); time.sleep(5); continue
        if r.status_code == 403:
            time.sleep(15); continue
        return r
    return None

def ttl(url, greps=()):
    r = _get(url)
    if r is None or r.status_code != 200:
        print(url, "->", r.status_code if r else None); return
    m = re.search(r"<title>(.*?)</title>", r.text, re.S)
    print(url.split("wowhead.com/")[-1], "->", m.group(1).strip() if m else None)
    for pat in greps:
        hits = sorted(set(x.strip() for x in re.findall(pat, r.text)))[:6]
        if hits:
            print("   ", pat[:28], hits)

ttl("https://www.wowhead.com/item=13174")
ttl("https://www.wowhead.com/quest=5125",
    (r"[A-Za-z' ]*[Mm]edallion[A-Za-z' ]*", r"[A-Za-z' ]*Martyr[A-Za-z' ]*"))
ttl("https://www.wowhead.com/quest=5466",
    (r"[A-Za-z' ]*[Rr]elic[A-Za-z' ]*", r"[A-Za-z' ]*[Ss]oul[A-Za-z'-]*[A-Za-z' ]*"))
