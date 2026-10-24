# -*- coding: utf-8 -*-
"""生成 DungeonsForever/Core/Data/Data_BossPos.lua（首领钉点坐标）。

链路（2026-10-05 v2，fc 改版页重采）：
  _df_pin_refetch.py 抓 fc 改版页（floors JSON 内嵌，26-10 起逐步回铺）
  → _df_pin_floors2.py 提取**全部楼层**钉点并按名字对齐我方掉落表
    （_bosspos_floors_all.json，含第 1 层；faceKind=object 的物件点不收）
  → 本脚本渲染 Lua。

  另有一份手工层 _bosspos_manual.json：excavation_wetlands 的 4 颗钉点**不是**
  站点采集，是 2026-10-03 用户在游戏地图页亲手标注（配准反解），永远以它为准。

坐标 = 相对客户端原图 1002×668 的百分比（fc 站同口径）。键 = 首领英文名（与
DungeonLoot 的来源名 / DungeonGuide 的 bosses[].en 同口径）。多刷点保留为数组。

用法：python gen_boss_pos.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(HERE)
FLOORS = os.path.join(HERE, "_bosspos_floors_all.json")
MANUAL = os.path.join(HERE, "_bosspos_manual.json")
# Lootified 补缺（2026-10-10）：_temp/lootified_bosspos.py 从客户端 Lootified 插件提取，
# 只含「我们没有的」——17 个未收录副本 + 已收录副本里缺钉点的首领（现有钉点一律不碰）
LOOTIFIED = os.path.join(HERE, "_bosspos_lootified.json")
# 我方 Data_DungeonLoot 里的副本先后（razorfen_kraul 2026-10-05 新采，插在 gnomeregan 后，
# 与掉落表顺序一致）
ORDER = ["ragefire_chasm", "wailing_caverns", "the_deadmines", "shadowfang_keep",
         "blackfathom_deeps", "the_stockade", "gnomeregan",
         "razorfen_kraul",
         # 两个自制副本（用户手绘 TGA 图，钉点坐标 = fc 站单层图同口径）
         "hall_of_thanes", "ruins_of_lordaeron",
         # 达拉然城（2026-10-09：fc 双层图回铺；第 1 层 = 用户重绘成品图、第 2 层 = 客户端瓦片）
         "city_of_dalaran",
         # 挖掘场湿地（自制图 + 用户在游戏地图页手工标注，_bosspos_manual.json）
         "excavation_wetlands",
         # Lootified 补缺（2026-10-10，按 Data_Dungeons 顺序插队）
         "sm_graveyard", "sm_library", "sm_armory", "razorfen_downs", "sm_cathedral",
         "uldaman", "zul_farrak", "maraudon", "sunken_temple", "blackrock_depths",
         "dire_maul_east", "lower_blackrock_spire", "dire_maul_north", "dire_maul_west",
         "scholomance", "stratholme_main", "stratholme_service",
         # 奥妮克希亚的巢穴（2026-10-11，客户端地图标注换算，_bosspos_manual.json）
         "onyxias_lair"]

HEADER = '''local _, ns = ...
ns.BossPos = {'''

FOOTER = "}\n"

# ★ 2026-10-05 用户拍板：fc 改版页对这些点做了坐标「校准」，**不收** —— 旧坐标为准
#   （只有这 10 颗回退；剃刀沼泽 9 颗 / 德克斯伦·沃德 3 颗 / 洛丹伦卫兵等新增钉照收）
REVERT = {
    ("shadowfang_keep", "Commander Springvale"): (27.9, 59.3),
    ("shadowfang_keep", "Fel Steed / Shadow Charger"): (36, 62.9),
    ("hall_of_thanes", "Durgen Dirgehammer"): (50.5, 23.1),
    ("hall_of_thanes", "Faldrim Anvilmar"): (50.4, 63.6),
    ("hall_of_thanes", "Magmatus"): (62, 50.1),
    ("hall_of_thanes", "Plunder"): (50.5, 50.6),
    ("ruins_of_lordaeron", "Bjork"): (34.7, 42.5),
    ("ruins_of_lordaeron", "Rath'mael"): (41.3, 62.7),
    ("ruins_of_lordaeron", "The Abandoned"): (36.5, 53.3),
    ("ruins_of_lordaeron", "Viktor the Vile"): (33.2, 64.8),
}


def revert(did, en, pts):
    old = REVERT.get((did, en))
    if not old:
        return pts
    # 旧口径：这些点都是单点、第 1 层
    return [[old[0], old[1]]]


def fmt(v):
    return "%g" % v


def lua_str(s):
    """首领名转 Lua 字符串体（Eric \"The Swift\" 这类带引号的名字要转义）"""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def main():
    data = {}
    if os.path.exists(MANUAL):
        data.update(json.load(open(MANUAL, encoding="utf-8")))
    floors = json.load(open(FLOORS, encoding="utf-8"))
    # 楼层钉点：第 1 层保持两位（缺省层号），2+ 层带第 3 位 = 客户端层号
    for did, fls in floors.items():
        dst = data.setdefault(did, {})
        for flnum, rows in fls.items():
            for r in rows:
                if int(flnum) == 1:
                    dst.setdefault(r["en"], []).append([r["x"], r["y"]])
                else:
                    dst.setdefault(r["en"], []).append([r["x"], r["y"], int(flnum)])
    # Lootified 补缺（只含我们没有的；现有键 setdefault 不覆盖、已有点不追加）
    if os.path.exists(LOOTIFIED):
        for did, fls in json.load(open(LOOTIFIED, encoding="utf-8")).items():
            dst = data.setdefault(did, {})
            for flnum, rows in fls.items():
                for r in rows:
                    if int(flnum) == 1:
                        dst.setdefault(r["en"], []).append([r["x"], r["y"]])
                    else:
                        dst.setdefault(r["en"], []).append([r["x"], r["y"], int(flnum)])
    lines = [HEADER]
    npin = 0
    nboss = 0
    present = [d for d in ORDER if data.get(d)]
    for did in present:
        pos = data[did]
        lines.append('    ["%s"] = {\n' % did)
        for en in sorted(pos.keys()):
            pts = revert(did, en, pos[en])
            npin += len(pts)
            nboss += 1
            body = ", ".join("{ %s }" % ", ".join(fmt(v) for v in p) for p in pts)
            lines.append('        ["%s"] = { %s },\n' % (lua_str(en), body))
        lines.append("    },\n")
    lines.append(FOOTER)
    out = os.path.join(DF, "Core", "Data", "Data_BossPos.lua")
    open(out, "w", encoding="utf-8", newline="\n").write("".join(lines))
    print("写出", out)
    print("副本 = %d  首领 = %d  钉点 = %d" % (len(present), nboss, npin))
    for did in present:
        pos = data[did]
        print("  %-22s 首领 %2d  钉点 %2d" % (did, len(pos), sum(len(v) for v in pos.values())))


if __name__ == "__main__":
    main()
