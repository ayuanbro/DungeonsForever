# -*- coding: utf-8 -*-
"""从 foreverchanges 缓存页提取**每层**的首领钉点（按名字对齐，同 _df_pin_align 口径）。

页面内嵌一段转义 JSON：floors\\":[{\\"src\\":\\"/dungeons/maps/<slug>-<层号>.webp\\",
\\"name\\":\\"庭院\\",\\"pins\\":[{\\"x\\":66.1,\\"y\\":71.1,\\"label\\":\\"雷希戈尔\\",...},...]}]
—— src 的数字后缀 = 客户端层号（ShadowfangKeep7_ ↔ -7.webp；Gnomeregan10_ ↔ -10.webp，
均与 MapUI ART 前缀一致）。

对齐：pin.label（en 优先、其次 zh）→ 我方 Data_DungeonLoot 的来源名；
faceKind = object 的物件点不收（label 是物品名、不在 boss 名单）。第 1 层跳过
（_bosspos_draft.json 已有，同一份站点数据）。

输出：_temp/_bosspos_floors.json = { 副本id: { 层号: [ {en, zh, x, y}, … ] } }
"""
import html
import io
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOOT = os.path.join(DF, "Core", "Data", "Data_DungeonLoot.lua")

DUN7 = ["ragefire_chasm", "wailing_caverns", "the_deadmines", "shadowfang_keep",
        "blackfathom_deeps", "the_stockade", "gnomeregan",
        # 2026-09-30 晚：两个自制副本也补钉点（用户手绘 TGA 图 + 站点单层 floors JSON）
        "hall_of_thanes", "ruins_of_lordaeron"]
SLUG = {
    "ragefire_chasm": "ragefire-chasm",
    "wailing_caverns": "wailing-caverns",
    "the_deadmines": "the-deadmines",
    "shadowfang_keep": "shadowfang-keep",
    "blackfathom_deeps": "blackfathom-deeps",
    "the_stockade": "the-stockade",
    "gnomeregan": "gnomeregan",
    "hall_of_thanes": "hall-of-thanes",
    "ruins_of_lordaeron": "ruins-of-lordaeron",
}

# 站点名 → 我方英文名（与 _df_pin_align.py 同一张人工别名表）
MANUAL = {
    ("the_stockade", "巴吉尔·特雷德"): "Bazil Thredd",
    ("blackfathom_deeps", "暮光领主克尔里斯"): "Twilight Lord Kelris",  # 我方表译「梦游者克尔里斯」
    # 自制副本：站点的 zh 译名与我方掉落表不一致（2026-09-30 对齐实锤）
    ("hall_of_thanes", "法德林·安威玛尔"): "Faldrim Anvilmar",      # 我方「法尔德里姆·安威玛尔」
    ("hall_of_thanes", "劫掠者"): "Plunder",                        # 我方「普兰德」
    ("hall_of_thanes", "杜根·挽锤"): "Durgen Dirgehammer",          # 我方「杜尔根·挽歌之锤」
    ("ruins_of_lordaeron", "邪恶的维克多"): "Viktor the Vile",      # 我方「邪恶的维克托」（多/托之差）
}
# 这两本的钉点**只在站点第 1 层**（src 无层号后缀），且 draft 里没有 —— 第 1 层也要收
INCLUDE_L1 = {"hall_of_thanes", "ruins_of_lordaeron"}


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
    for did in DUN7:
        p = os.path.join(HERE, "_ref", "dg_%s.html" % SLUG[did])
        txt = io.open(p, encoding="utf-8").read()
        floors = extract_floors(txt)
        ours = blocks.get(did) or []
        by_en = {s["en"]: s for s in ours}
        by_zh = {s["zh"]: s for s in ours}
        d = {}
        for fl in floors:
            m = re.search(r"-([0-9]+)\.webp", fl.get("src") or "")
            # src 无层号后缀 = 单层图（自制副本 hall-of-thanes.webp）⇒ 第 1 层
            flnum = int(m.group(1)) if m else 1
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
                rows.append({"en": s["en"], "zh": s["zh"], "x": pin["x"], "y": pin["y"]})
            print("%-20s 层 %-3s %-10s 对齐 %d / 跳过 %s"
                  % (did, flnum, fl.get("name"), len(rows),
                     ",".join(skip) or "-"))
            if (flnum > 1 or did in INCLUDE_L1) and rows:
                d[str(flnum)] = rows
        if d:
            out[did] = d
    with open(os.path.join(HERE, "_bosspos_floors.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("写出 _bosspos_floors.json：副本", len(out))


if __name__ == "__main__":
    main()
