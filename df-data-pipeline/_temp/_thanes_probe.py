# -*- coding: utf-8 -*-
"""查 wowhead forever 是否收录 Hall of Thanes（领主大厅）的地图/区域页。"""
import re, sys
from curl_cffi import requests
PX = {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}
H = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.wowhead.com/",
}
URLS = [
    "https://www.wowhead.com/forever/cn/search?q=Hall+of+Thanes",
    "https://www.wowhead.com/forever/cn/zones?q=thanes",
    "https://www.wowhead.com/forever/zone=10000/hall-of-thanes",
]
for u in URLS:
    try:
        r = requests.get(u, headers=H, proxies=PX, impersonate="chrome110", timeout=40)
        print("=== %s -> %s  len=%d" % (u, r.status_code, len(r.text)))
        t = r.text
        for pat in (r'href="(/forever/[^"]*zone=\d+[^"]*)"', r'zone=(\d+)', r'(hall-of-thanes)', r'(Hall of Thanes)'):
            hits = sorted(set(re.findall(pat, t)))[:6]
            if hits:
                print("   %-14s %s" % (pat[:14], hits))
    except Exception as e:
        print("=== %s -> ERR %s" % (u, e))
