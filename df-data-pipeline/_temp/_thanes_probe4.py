# -*- coding: utf-8 -*-
import re
from curl_cffi import requests
PX = {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
     "Accept": "text/html,*/*;q=0.8", "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
     "Referer": "https://www.wowhead.com/"}
u = "https://www.wowhead.com/forever/cn/zone=16919/hall-of-thanes"
r = requests.get(u, headers=H, proxies=PX, impersonate="chrome110", timeout=45)
t = r.text
print("status", r.status_code, "len", len(t))
pats = {
    "mapX-系列": r"(mapX?-\d+|MapCanvas|maps/[\w\-/\.]+)",
    "WH.markup 地图": r"printHtml\((['\"]).{0,200}?map.{0,300}?\1\)",
    "data-map": r"data-map[a-z]*=\"[^\"]*\"",
    "标题": r"<title>(.*?)</title>",
}
for k, p in pats.items():
    hits = re.findall(p, t, re.S)
    print("--", k, len(hits))
    for h in hits[:12]:
        print("   ", re.sub(r"\s+", " ", str(h))[:300])
