# -*- coding: utf-8 -*-
"""导出待汉化的 wowhead 攻略正文（仅掉落表里匹配上的 boss）。"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(HERE)
LOOT = os.path.join(DF, "Core", "Data", "Data_DungeonLoot.lua")

DUN = re.compile(r'\["([a-z0-9_]+)"\]\s*=\s*\{')
BOSS = re.compile(r'\{\s*"([^"]+)",\s*"([^"]+)"')


def norm(s):
    s = (s or "").replace("\u2019", "'").replace("\u2018", "'")
    return re.sub(r"\s+", " ", s).strip().lower()


def strip_title(s):
    s = re.sub(r"\s*\(Rare\)\s*$", "", s or "").strip()
    s = re.sub(r"^Naralax Event\s+", "", s, flags=re.I)
    return s.strip()


ALIAS = {
    "lady anacondra": "lady andacondra",
    "fel steed / shadow charger": "fel steeds / shadow charger",
    "sneed": "sneed's shredder",
}

DUN7 = ["ragefire_chasm", "wailing_caverns", "the_deadmines", "shadowfang_keep",
        "blackfathom_deeps", "the_stockade", "gnomeregan"]

src = open(LOOT, encoding="utf-8", errors="replace").read()
marks = [(m.start(), m.group(1)) for m in DUN.finditer(src)]
loot = {}
for i, (pos, did) in enumerate(marks):
    end = marks[i + 1][0] if i + 1 < len(marks) else len(src)
    loot[did] = [m.group(1) for m in BOSS.finditer(src[pos:end])]

wh = json.load(open(os.path.join(HERE, "_wh_guide_raw.json"), encoding="utf-8"))
out = {}
for did in DUN7:
    widx = {norm(strip_title(k)): k for k in wh.get(did, {})}
    for en in loot.get(did, []):
        key = norm(en)
        wkey = widx.get(ALIAS.get(key, key))
        if not wkey:
            continue
        v = wh[did][wkey]
        if v["text"]:
            out.setdefault(did, {})[en] = v["text"]

json.dump(out, open(os.path.join(HERE, "_wh_translate_src.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
n = sum(len(v) for v in out.values())
print("待汉化 %d 条" % n)
for did, m in out.items():
    print("%-20s %d 条" % (did, len(m)))
