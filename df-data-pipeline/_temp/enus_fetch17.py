# -*- coding: utf-8 -*-
import re, sys, time
sys.stdout.reconfigure(encoding="utf-8")
from curl_cffi import requests
HDRS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0.0.0 Safari/537.36"}
r = requests.get("https://www.wowhead.com/quest=4771", headers=HDRS,
                 proxy="http://127.0.0.1:7897", impersonate="chrome", timeout=20)
body = r.text
for pat in (r"[A-Za-z' ]*[Vv]ectus[A-Za-z' ]*", r"[A-Za-z' ]*Victus[A-Za-z' ]*",
            r"[A-Za-z' ]*Dawn's Gambit[A-Za-z' ]*",
            r"[A-Za-z' ]*[Cc]hamber of the Watcher[A-Za-z' ]*",
            r"[A-Za-z' ]*[Ww]atcher[A-Za-z' ]*"):
    hits = sorted(set(x.strip() for x in re.findall(pat, body)))[:5]
    if hits:
        print(pat, "->", hits)
