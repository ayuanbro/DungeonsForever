# -*- coding: utf-8 -*-
"""抓 wowhead classic 7 个副本攻略页的 BBCode 真源。

输出：_temp/_ref_wowhead/wh_<slug>.html（整页，BBCode 藏在 WH.markup.printHtml 里或正文脚本中）。
"""
from curl_cffi import requests
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "_ref_wowhead")
PROXIES = {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}

# 副本 id → wowhead 攻略页 slug
WH = {
    "ragefire_chasm": "ragefire-chasm-dungeon-strategy-wow-classic",
    "wailing_caverns": "wailing-caverns-dungeon-strategy-wow-classic",
    "the_deadmines": "deadmines-dungeon-strategy-wow-classic",
    "shadowfang_keep": "shadowfang-keep-dungeon-strategy-wow-classic",
    "blackfathom_deeps": "blackfathom-deeps-dungeon-strategy-wow-classic",
    "the_stockade": "stockade-dungeon-strategy-wow-classic",
    "gnomeregan": "gnomeregan-dungeon-strategy-wow-classic",
}

for did, slug in WH.items():
    out = os.path.join(OUT, "wh_%s.html" % did)
    if os.path.exists(out) and os.path.getsize(out) > 20000:
        print("%-20s 缓存命中" % did)
        continue
    url = "https://www.wowhead.com/classic/cn/guide/%s" % slug
    try:
        r = requests.get(url, proxies=PROXIES, impersonate="chrome110", timeout=30)
        open(out, "w", encoding="utf-8").write(r.text)
        print("%-20s %s len=%d" % (did, r.status_code, len(r.text)))
    except Exception as e:
        print("%-20s FAIL %s" % (did, e))
    time.sleep(1.2)
print("done")
