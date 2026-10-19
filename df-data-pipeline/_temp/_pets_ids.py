# -*- coding: utf-8 -*-
"""抓 3 个物品图标 slug + 相关 NPC 坐标。"""
from curl_cffi import requests
import os, re, time, json

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "_ref_pets")
os.makedirs(OUT, exist_ok=True)
PROXIES = {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}
HDR = {"Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"}

TARGETS = [
    ("item", 282047), ("item", 275682), ("item", 268109), ("item", 278265),
    ("npc", 3581), ("npc", 269452), ("npc", 259006), ("npc", 259842), ("npc", 4612),
]

def get(url):
    return requests.get(url, proxies=PROXIES, impersonate="chrome110",
                        timeout=40, headers=HDR)

out = {}
for kind, i in TARGETS:
    p = os.path.join(OUT, "%s_%d.html" % (kind, i))
    if os.path.exists(p) and os.path.getsize(p) > 20000:
        raw = open(p, encoding="utf-8").read()
    else:
        raw = get("https://www.wowhead.com/forever/cn/%s=%d" % (kind, i)).text
        open(p, "w", encoding="utf-8").write(raw)
        time.sleep(1.3)
    icons = re.findall(r"inv_[a-z0-9_]+|spell_[a-z0-9_]+|ability_[a-z0-9_]+|achievement_[a-z0-9_]+", raw)
    icons = [x for x in icons if "icon" not in x or True]
    # 图标 slug 一般在 Icon.create 或 "icon":"..."
    ic = re.findall(r'"icon":"([a-z0-9_]+)"', raw) + re.findall(r"Icon\.create\([^)]*'([a-z0-9_]+)'", raw)
    ic = [x for x in ic if re.match(r"^(inv_|spell_|ability_|achievement_)", x)]
    coords = re.findall(r'"coords":\[\[([0-9.]+),([0-9.]+)', raw)
    out["%s%d" % (kind, i)] = {"icon": sorted(set(ic))[:4], "coords": coords[:6]}
    print("%-12s icon=%s coords=%s" % ("%s=%d" % (kind, i), sorted(set(ic))[:3], coords[:4]))

open(os.path.join(OUT, "_pets_ids.json"), "w", encoding="utf-8").write(
    json.dumps(out, ensure_ascii=False, indent=1))
print("done")
