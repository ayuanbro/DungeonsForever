# -*- coding: utf-8 -*-
"""对齐三份 boss 名单：wowhead 攻略页 / 掉落表 / foreverchanges 技能数据。"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(HERE)
LOOT = os.path.join(DF, "Core", "Data", "Data_DungeonLoot.lua")

DUN = re.compile(r'\["([a-z0-9_]+)"\]\s*=\s*\{')
BOSS = re.compile(r'\{\s*"([^"]+)",\s*"([^"]+)",\s*"([^"]*)",\s*"([^"]*)",\s*\{')


def norm(s):
    s = (s or "").replace("\u2019", "'").replace("\u2018", "'")
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


def strip_title(s):
    """去 (Rare) / 前缀修饰。"""
    s = re.sub(r"\s*\(Rare\)\s*$", "", s or "").strip()
    s = re.sub(r"^Naralax Event\s+", "", s, flags=re.I)
    return s.strip()


def loot_bosses():
    src = open(LOOT, encoding="utf-8", errors="replace").read()
    marks = [(m.start(), m.group(1)) for m in DUN.finditer(src)]
    out = {}
    for i, (pos, did) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(src)
        out[did] = [(m.group(1), m.group(2)) for m in BOSS.finditer(src[pos:end])]
    return out


def main():
    loot = loot_bosses()
    wh = json.load(open(os.path.join(HERE, "_wh_guide_raw.json"), encoding="utf-8"))
    sk = json.load(open(os.path.join(HERE, "_boss_skills_raw.json"), encoding="utf-8"))

    for did in ["ragefire_chasm", "wailing_caverns", "the_deadmines", "shadowfang_keep",
                "blackfathom_deeps", "the_stockade", "gnomeregan"]:
        print("=== %s ===" % did)
        widx = {norm(strip_title(k)): k for k in wh.get(did, {})}
        sidx = {norm(k): k for k in sk.get(did, {})}
        for en, zh in loot.get(did, []):
            w = widx.get(norm(en))
            s = sidx.get(norm(en))
            winfo = ""
            if w:
                v = wh[did][w]
                winfo = "WH[%d 法术, 正文 %d]" % (len(v["spells"]), len(v["text"]))
            print("  %-30s %s %s" % (en, "WH✓ " + winfo if w else "WH✗",
                                     "SK✓" if s else "SK✗"))


if __name__ == "__main__":
    main()
