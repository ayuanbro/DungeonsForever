# -*- coding: utf-8 -*-
import re, json
from curl_cffi import requests
PX = {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
     "Accept": "text/html,*/*;q=0.8", "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
     "Referer": "https://www.wowhead.com/"}
r = requests.get("https://www.wowhead.com/forever/cn/zone=16919/hall-of-thanes", headers=H, proxies=PX, impersonate="chrome110", timeout=45)
t = r.text
print("len", len(t))
for m in re.finditer(r"printHtml\(", t):
    a = m.end(); seg = t[a:a+700]
    print("---- printHtml @%d: %s" % (a, re.sub(r"\s+", " ", seg)[:420]))
print("=== 所有含 map 的行 ===")
for i, ln in enumerate(t.splitlines(), 1):
    if re.search(r"map", ln, re.I):
        s = re.sub(r"\s+", " ", ln.strip())[:260]
        if s: print(i, s)
