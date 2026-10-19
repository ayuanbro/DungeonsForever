# -*- coding: utf-8 -*-
"""对比 wowhead forever 区域页：有地图的区域 vs 领主大厅。"""
import re
from curl_cffi import requests
PX = {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
     "Accept": "text/html,*/*;q=0.8", "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
     "Referer": "https://www.wowhead.com/"}
PAGES = {
    "领主大厅 16919": "https://www.wowhead.com/forever/cn/zone=16919/hall-of-thanes",
    "怒焰裂谷 2437": "https://www.wowhead.com/forever/cn/zone=2437/ragefire-chasm",
    "湿地 11": "https://www.wowhead.com/forever/cn/zone=11/wetlands",
}
for name, u in PAGES.items():
    r = requests.get(u, headers=H, proxies=PX, impersonate="chrome110", timeout=45)
    t = r.text
    maps = re.findall(r'(maps?/[A-Za-z0-9_\-\/]+\.(?:jpg|png|webp))', t)
    mapper = re.findall(r'(mapid|mapId|map_id|"map":|data-map)', t)
    print("%-16s %s len=%d  图文件=%d %s  地图标记=%d %s" % (
        name, r.status_code, len(t), len(set(maps)), sorted(set(maps))[:3], len(mapper), sorted(set(mapper))[:4]))
