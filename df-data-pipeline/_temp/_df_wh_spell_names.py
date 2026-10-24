# -*- coding: utf-8 -*-
"""抓取 wowhead 能力法术的中英文名。

输入：_temp/_wh_guide_raw.json 的 spells 并集
输出：_temp/_wh_spell_names.json = { str(id): {"zh": …, "en": …} }
"""
from curl_cffi import requests
import json
import os
import re
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROXIES = {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}

g = json.load(open(os.path.join(HERE, "_wh_guide_raw.json"), encoding="utf-8"))
ids = sorted({sid for v in g.values() for b in v.values() for sid in b["spells"]})
print("唯一法术 %d 个" % len(ids))

out = {}
if os.path.exists(os.path.join(HERE, "_wh_spell_names.json")):
    out = json.load(open(os.path.join(HERE, "_wh_spell_names.json"), encoding="utf-8"))


def fetch(url):
    r = requests.get(url, proxies=PROXIES, impersonate="chrome110", timeout=30)
    return r.text if r.status_code == 200 else ""


def name_of(h, tag):
    if not h:
        return ""
    if tag == "zh":
        m = re.search(r"<h1[^>]*>(.*?)</h1>", h, re.S)
        return re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else ""
    m = re.search(r"<title>(.*?)</title>", h)
    if not m:
        return ""
    t = m.group(1)
    return t.split("—")[0].strip() if "—" in t else t.split("\u2014")[0].strip()


todo = [i for i in ids if str(i) not in out]
print("待抓 %d 个" % len(todo))
for i in todo:
    zh = name_of(fetch("https://www.wowhead.com/classic/cn/spell=%d" % i), "zh")
    time.sleep(0.5)
    en = name_of(fetch("https://www.wowhead.com/classic/spell=%d" % i), "en") if zh else ""
    time.sleep(0.5)
    out[str(i)] = {"zh": zh, "en": en}
    print("%6d  zh=%-14s en=%s" % (i, zh, en))

json.dump(out, open(os.path.join(HERE, "_wh_spell_names.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("— 落盘 _temp/_wh_spell_names.json")
