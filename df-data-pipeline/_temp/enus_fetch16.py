# -*- coding: utf-8 -*-
import re, sys, time
sys.stdout.reconfigure(encoding="utf-8")
from curl_cffi import requests
HDRS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0.0.0 Safari/537.36"}

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

for qid, pat in ((4771, r"[A-Za-z' ]*Vanguard[A-Za-z' ]*"),
                 (5384, r"[A-Za-z' ]*[Bb]lood[A-Za-z' ]*")):
    r = _get("https://www.wowhead.com/quest=%d" % qid)
    if r is None or r.status_code != 200:
        print("q%d no page" % qid); continue
    m = re.search(r"<title>(.*?)</title>", r.text, re.S)
    print("q%d title:" % qid, m.group(1).strip() if m else None)
    print("  grep:", sorted(set(x.strip() for x in re.findall(pat, r.text)))[:8])
    time.sleep(1)
