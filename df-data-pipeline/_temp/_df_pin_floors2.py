# -*- coding: utf-8 -*-
"""从新版 foreverchanges 副本页（_ref/dg_<slug>.html）提取**全部楼层**钉点并对齐我方掉落表。

2026-10-05：fc 改版页重新内嵌 floors JSON（此前改版一度没有 ⇒ 钉点 9/35）。
目前（重抓实锤）只有前 8 本低级副本带 floors：ragefire / wailing / deadmines /
shadowfang / blackfathom / stockade / gnomeregan / razorfen-kraul。

流程：extract_floors 抠转义 JSON → 每层钉点 label（zh/en）对齐 Data_DungeonLoot
来源名（by_en/by_zh + MANUAL 别名）→ 输出
_temp/_bosspos_floors_all.json = { 副本id: { 层号: [ {en, zh, x, y}, … ] } }
（含第 1 层——与旧 _df_pin_floors.py 的差别：旧脚本第 1 层跳过、由 draft 供）。

用法：python _df_pin_floors2.py
"""
import html
import io
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOOT = os.path.join(DF, "Core", "Data", "Data_DungeonLoot.lua")

SLUG = {
    "ragefire_chasm": "ragefire-chasm",
    "wailing_caverns": "wailing-caverns",
    "the_deadmines": "the-deadmines",
    "shadowfang_keep": "shadowfang-keep",
    "blackfathom_deeps": "blackfathom-deeps",
    "the_stockade": "the-stockade",
    "gnomeregan": "gnomeregan",
    "razorfen_kraul": "razorfen-kraul",
    "hall_of_thanes": "hall-of-thanes",
    "ruins_of_lordaeron": "ruins-of-lordaeron",
    # 2026-10-09：达拉然之城（fc 双层图，层名→客户端层号见 FLOOR_NAME）
    "city_of_dalaran": "city-of-dalaran",
}

# fc 图文件名无数字层号、改用图内标题的副本：图名 → 我方**客户端层号**
# （达拉然城客户端 2 层：第 1 层 = 城、第 2 层 = 下水道；fc 页顺序相反）
FLOOR_NAME = {
    ("city_of_dalaran", "下水道"): 2,
    ("city_of_dalaran", "城市"): 1,
}

# 站点名 → 我方英文名（沿用 _df_pin_floors.py 的人工别名表）
MANUAL = {
    ("the_stockade", "巴吉尔·特雷德"): "Bazil Thredd",
    ("blackfathom_deeps", "暮光领主克尔里斯"): "Twilight Lord Kelris",
    ("hall_of_thanes", "法德林·安威玛尔"): "Faldrim Anvilmar",
    ("hall_of_thanes", "劫掠者"): "Plunder",
    ("hall_of_thanes", "杜根·挽锤"): "Durgen Dirgehammer",
    ("ruins_of_lordaeron", "邪恶的维克多"): "Viktor the Vile",
    # 达拉然城：fc 译名与我方自译名不同（wowhead 无官方 zhCN，保留我方）
    ("city_of_dalaran", "墓穴骑士阿特雷克斯"): "Atrexis the Grave Knight",
    ("city_of_dalaran", "被无视的琳恩"): "Lyn the Ignored",
    ("city_of_dalaran", "奥术畸体"): "Arcane Anomaly",
}

# 坐标人工覆盖（键 = (副本, 我方 en 名) → (x, y)）：fc 原钉点位置不佳，
# 2026-10-10 用户在游戏截图上逐钉标注定稿。应用于 fc 坐标之后（覆盖优先）。
PIN_OVERRIDE = {
    # 达拉然之城 · 下水道层（层 2）
    ("city_of_dalaran", "Atrexis the Grave Knight"): (54.8, 52.3),
    ("city_of_dalaran", "Lyn the Ignored"): (64.1, 13.0),
    # 达拉然之城 · 城市层（层 1）：大法师1/哨兵2/谜团3/古树4/吞噬者5/异常体6
    ("city_of_dalaran", "Shade of the Archmage"): (49.2, 25.4),
    ("city_of_dalaran", "Unstable Sentinel"): (56.6, 36.2),
    ("city_of_dalaran", "Arcanic Enigma"): (65.3, 38.9),
    ("city_of_dalaran", "Fel Ancient"): (53.2, 51.4),
    ("city_of_dalaran", "Mana Devourer"): (49.2, 68.5),
    ("city_of_dalaran", "Arcane Anomaly"): (60.9, 74.9),
}


def loot_rows():
    src = io.open(LOOT, encoding="utf-8", errors="replace").read()
    BLOCK = re.compile(r'^\s*\["([a-z_0-9]+)"\]\s*=\s*\{')
    SRC = re.compile(r'^\s*\{ "((?:[^"\\]|\\.)*)", "((?:[^"\\]|\\.)*)", "((?:[^"\\]|\\.)*)", "((?:[^"\\]|\\.)*)",')
    blocks, cur = {}, None
    for line in src.splitlines():
        m = BLOCK.match(line)
        if m:
            cur = m.group(1)
            blocks[cur] = []
            continue
        if cur:
            m2 = SRC.match(line)
            if m2:
                blocks[cur].append({"en": m2.group(1).replace("\\'", "'"),
                                    "zh": m2.group(2), "npc": m2.group(4)})
    return blocks


def extract_floors(txt):
    """→ [ {src, name, pins:[…]} ]（从转义 JSON 抠出并解析）。"""
    i = txt.find('floors\\":')
    if i < 0:
        return []
    j = i + len('floors\\":')
    assert txt[j] == "[", "floors 后不是数组"
    depth, k = 0, j
    while k < len(txt):
        c = txt[k]
        if c == "\\":
            k += 2
            continue
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                break
        k += 1
    blob = txt[j:k + 1].replace('\\"', '"')
    return json.loads(blob)


def main():
    blocks = loot_rows()
    out = {}
    total = 0
    for did, slug in SLUG.items():
        p = os.path.join(HERE, "_ref", "dg_%s.html" % slug)
        txt = io.open(p, encoding="utf-8").read()
        floors = extract_floors(txt)
        ours = blocks.get(did) or []
        by_en = {s["en"]: s for s in ours}
        by_zh = {s["zh"]: s for s in ours}
        d = {}
        for fl in floors:
            m = re.search(r"-([0-9]+)\.webp", fl.get("src") or "")
            # src 无层号后缀 = 单层图 ⇒ 第 1 层；FLOOR_NAME 副本按图名映射客户端层号
            flnum = FLOOR_NAME.get((did, fl.get("name"))) if FLOOR_NAME.get((did, fl.get("name"))) \
                else (int(m.group(1)) if m else 1)
            rows, skip = [], []
            for pin in fl.get("pins") or []:
                if (pin.get("faceKind") or "") == "object":
                    skip.append(pin.get("label"))
                    continue  # 物件点不是首领
                nm = html.unescape(pin.get("label") or "").strip()
                forced = MANUAL.get((did, nm))
                s = by_en.get(forced) if forced else (by_en.get(nm) or by_zh.get(nm))
                if not s:
                    skip.append(nm)
                    continue
                ov = PIN_OVERRIDE.get((did, s["en"]))
                rows.append({"en": s["en"], "zh": s["zh"],
                             "x": ov[0] if ov else pin["x"],
                             "y": ov[1] if ov else pin["y"]})
            total += len(rows)
            print("%-20s 层 %-3s %-10s 对齐 %d / 跳过 %s"
                  % (did, flnum, fl.get("name"), len(rows),
                     ",".join(skip) or "-"))
            if rows:
                d[str(flnum)] = rows
        if d:
            out[did] = d
    with open(os.path.join(HERE, "_bosspos_floors_all.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("写出 _bosspos_floors_all.json：副本", len(out), "钉点", total)


if __name__ == "__main__":
    main()
