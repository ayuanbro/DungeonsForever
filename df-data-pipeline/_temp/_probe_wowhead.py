# -*- coding: utf-8 -*-
"""探测 wowhead classic 攻略页的 boss 技能结构（临时脚本）。"""
from curl_cffi import requests

URL = "https://www.wowhead.com/classic/cn/guide/ragefire-chasm-dungeon-strategy-wow-classic"
PROXIES = {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}

r = requests.get(URL, proxies=PROXIES, impersonate="chrome110", timeout=30)
h = r.text
print("status", r.status_code, "len", len(h))
open("_temp/_ref_wowhead/dg_ragefire-chasm.html", "w", encoding="utf-8").write(h)

import re
print("spell links:", len(re.findall(r'/spell=(\d+)', h)))
print("npc links:", len(re.findall(r'/npc=(\d+)', h)))
# boss 小节标题
for m in re.finditer(r'<h[23][^>]*id="([^"]*)"[^>]*>(.*?)</h[23]>', h):
    t = re.sub(r'<[^>]+>', '', m.group(2))
    if t.strip():
        print("H:", m.group(1)[:40], "|", t.strip()[:50])
