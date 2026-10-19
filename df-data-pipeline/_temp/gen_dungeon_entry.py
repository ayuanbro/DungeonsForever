# -*- coding: utf-8 -*-
"""生成 Core/Data/Data_DungeonEntry.lua —— 副本入口在世界地图上的坐标（仅无限服可用）。

为什么需要单独一张表：
    「点副本名 → 在地图上标记入口」与「点 NPC 名 → 标记 NPC」走同一条航点链路
    （UiMapPoint.CreateFromCoordinates → C_Map.SetUserWaypoint → C_Map.OpenWorldMap），
    后者读 ns.NPCLoc。副本入口不属于任何 NPC，客户端 Lua 也没有按副本 ID 查入口的口，
    故在此单独落一张同形表：{ uiMapID, x%, y%, 地图名 }。

坐标来源（本脚本为内部工具、不进包）：
    本机 AddOns/Leatrix_Maps/Leatrix_Maps_Icons.lua 的 {"Dungeon", x, y, 名} 条目。
    该文件按区域块组织，**块的 key 就是 uiMapID**，条目坐标即「画在客户端世界地图上的
    百分比位置」——与客户端地图同基准，不需要换算。
    ⚠️ 必须用 Leatrix_Maps_Icons.lua（Wrath 基准），**不能**用 _Icons_Cata.lua：
       Cata 重画过地图（贫瘠之地一分为二），两套数值不可混用
       （实测 Razorfen Downs：Wrath 49.1,93.4 / Cata 41.5,29.4）。
    ⚠️ 黑石山（Blackrock Depths / Lower+Upper Blackrock Spire）在源数据里是**一个
       Dunraid 共享点**（灼热峡谷 34.8,85.3 / 燃烧平原 29.9,47.9），无法区分具体副本门
       → 刻意不落键，等实测值。

自检（任一条不过就中止，不产出半成品）：
    ① 每个副本 slug 只出现一次；
    ② 坐标必须落在 (0,100) 开区间；
    ③ uiMapID 必须在 Data_NPCLoc.lua 的地图名表里（拿不到中文图名就说明图号错了）；
    ④ 落键数 == 预期数；未收录清单必须与预期清单一致（防静默漏改）。
"""

import io
import os
import re
import sys

DF = r"D:/workspace/DungeonsForever"
LEATRIX = r"D:/Game/World of Warcraft/_classic_titan_/Interface/AddOns/Leatrix_Maps/Leatrix_Maps_Icons.lua"
DST = os.path.join(DF, "Core", "Data", "Data_DungeonEntry.lua")

CRLF = "\r\n"


def die(msg):
    sys.exit("gen_dungeon_entry: " + msg)


# ── 源条目名 → 本插件副本 slug ────────────────────────────────────────────────
# 名字以 Leatrix 源数据里的写法为准（区分左右，如三类厄运之槌、两道斯坦索姆门）。
SLUG = {
    "Ragefire Chasm": ["ragefire_chasm"],
    "Wailing Caverns": ["wailing_caverns"],
    "The Deadmines": ["the_deadmines"],
    "Shadowfang Keep": ["shadowfang_keep"],
    "Blackfathom Deeps": ["blackfathom_deeps"],
    "The Stockade": ["the_stockade"],
    "Gnomeregan": ["gnomeregan"],
    "Razorfen Kraul": ["razorfen_kraul"],
    "Razorfen Downs": ["razorfen_downs"],
    # 血色修道院四个区共用一个建筑入口 → 四条同值
    "Scarlet Monastery": ["sm_graveyard", "sm_library", "sm_armory", "sm_cathedral"],
    "Uldaman": ["uldaman"],
    "Zul'Farrak": ["zul_farrak"],
    "Maraudon": ["maraudon"],
    "Temple of Atal'Hakkar": ["sunken_temple"],
    "Dire Maul (East)": ["dire_maul_east"],
    "Dire Maul (North)": ["dire_maul_north"],
    "Dire Maul (West)": ["dire_maul_west"],
    "Scholomance": ["scholomance"],
    "Stratholme (Main Gate)": ["stratholme_main"],
    "Stratholme (Service Gate)": ["stratholme_service"],
}

# 刻意不落键的副本（点了 UI 会明说「未收录」，不假装成功）
#   · 黑石山三兄弟：源数据只有共享点，无法区分具体副本门 → 等实测
#   · 其余为本服自制副本（经典版不存在，公开坐标库没有；领主大厅 / 洛丹伦废墟已由
#     用户给值落入 MANUAL，见 ③-b）→ 等实测
MISSING = [
    "blackrock_depths", "lower_blackrock_spire", "upper_blackrock_spire",
    "the_drowned_city", "kroldok_stronghold", "alcaz_prison", "blackmaw_hold",
    "shapers_terrace",
]

# 全部副本（从 Data_Dungeons.lua 现读，不硬编码）——用于 ④ 的集合自检


def rd(p):
    return io.open(p, encoding="utf-8", errors="replace").read()


# ── ① 抽源数据 ──────────────────────────────────────────────────────────────
src = rd(LEATRIX)
blocks = {}
cur = None
ENTRY = re.compile(r'\{"(Dungeon|Dunraid)",\s*([\d.]+),\s*([\d.]+),\s*(.+?),\s*L\["')
for line in src.split("\n"):
    m = re.search(r"--\[\[([^\]]+)\]\]\s*\[(\d+)\]\s*=\s*\{", line)
    if m:
        cur = int(m.group(2))
        blocks.setdefault(cur, [])
        continue
    if cur is None:
        continue
    if '"Dunraid"' in line:
        continue  # 共享点（黑石山），不用
    for m in ENTRY.finditer(line):
        if m.group(1) != "Dungeon":
            continue
        names = re.findall(r'L\["([^"]+)"\]', m.group(4))
        nm = " + ".join(names) if names else m.group(4).strip()
        blocks[cur].append((float(m.group(2)), float(m.group(3)), nm))

# ── ② 地图中文名（从 Data_NPCLoc.lua 现取，避免自造图名）────────────────────
maploc = {}
for mm in re.finditer(r'\[\s*\d+\s*\]\s*=\s*\{\s*(\d+)\s*,\s*[\d.]+\s*,\s*[\d.]+\s*,\s*"([^"]*)"\s*\}',
                      rd(os.path.join(DF, "Core", "Data", "Data_NPCLoc.lua"))):
    maploc[int(mm.group(1))] = mm.group(2)
if not maploc:
    die("Data_NPCLoc.lua 里读不到地图名表（结构变了？）")

# ── ③ 映射 ─────────────────────────────────────────────────────────────────
rows = {}
used = {}
for mid in sorted(blocks):
    for x, y, nm in blocks[mid]:
        if nm not in SLUG:
            continue
        if nm in used:
            die("源条目名重复命中：%s" % nm)
        used[nm] = mid
        if not (0 < x < 100 and 0 < y < 100):
            die("%s 坐标越界：%s, %s" % (nm, x, y))
        if mid not in maploc:
            die("%s 的 uiMapID %d 在 Data_NPCLoc.lua 里没有中文图名（图号可能不对）" % (nm, mid))
        for slug in SLUG[nm]:
            if slug in rows:
                die("副本 slug 重复落键：%s" % slug)
            rows[slug] = (mid, x, y, maploc[mid])

unmapped = [k for k in SLUG if k not in used]
if unmapped:
    die("以下源条目名在 Leatrix 数据里没找到（源改名了？）：%s" % "、".join(unmapped))

# ── ③-b 手工落键（用户给值 / 窝窝头攻略页钉点，仅自制副本）─────────────────────
#   hall_of_thanes 领主大厅：用户实测两个点——副本入口（铁炉堡 28.2,47.7）是航点落点；
#     楼梯入口（铁炉堡 44.2,52）进 ROUTE 指引表，悬停提示框里逐行列出。
#     ★ uiMapID 以 Data_NPCLoc.lua 的地图名表为准：铁炉堡 = 1455（1454 是奥格瑞玛，别抄错）。
#   ruins_of_lordaeron 洛丹伦废墟：窝窝头攻略页 Dungeon Entrance 钉点 = 提瑞斯法林地
#     65.0,70.0（地上废墟入口）。旧口径 61.9,65.0 是幽暗城正门，2026-10-03 修正
#     （曾按用户「就用幽暗城入口」取 Leatrix Arrow→幽暗城条目，实机指向错误）。
#   excavation_wetlands / city_of_dalaran：窝窝头攻略页 Location 地图钉点
#     （wowhead /forever guide，2026-10-03/05 用户确认）。
MANUAL = {
    "hall_of_thanes": (1455, 28.2, 47.7),
    "ruins_of_lordaeron": (1420, 65.0, 70.0),
    "excavation_wetlands": (1437, 47.8, 56.3),
    "city_of_dalaran": (1416, 8.0, 61.2),
    # 奥妮克希亚的巢穴：尘泥沼泽 52.3,76.1（wowhead /forever 诸源一致，kami-labs 同值）
    "onyxias_lair": (1445, 52.3, 76.1),
}
# 多段指引：航点仍落 MANUAL 主点，本表只供提示框逐行展示。{uiMapID, x, y, 标签}
ROUTE = {
    "hall_of_thanes": [(1455, 44.2, 52.0, "楼梯入口")],
    # 挖掘场：窝窝头同图第二枚钉点「Meeting Stone and Entry」——本副本有两个入口坐标
    "excavation_wetlands": [(1437, 53.4, 65.3, "集合石入口")],
}
for _slug, (_mid, _x, _y) in MANUAL.items():
    if not (0 < _x < 100 and 0 < _y < 100):
        die("MANUAL %s 坐标越界：%s, %s" % (_slug, _x, _y))
    if _mid not in maploc:
        die("MANUAL %s 的 uiMapID %d 在 Data_NPCLoc.lua 里没有中文图名（图号可能不对）" % (_slug, _mid))
    if _slug in rows:
        die("MANUAL %s 与 Leatrix 落键撞了（自制副本出现在源数据里？）" % _slug)
    rows[_slug] = (_mid, _x, _y, maploc[_mid])
for _slug, _pts in ROUTE.items():
    if _slug not in MANUAL:
        die("指引点指向没有手工落键的副本：%s（主点必须同时存在）" % _slug)
    for (_m2, _x2, _y2, _lbl) in _pts:
        if not (0 < _x2 < 100 and 0 < _y2 < 100):
            die("指引点 %s 坐标越界：%s, %s" % (_slug, _x2, _y2))
        if _m2 not in maploc:
            die("指引点 %s 的 uiMapID %d 没有中文图名" % (_slug, _m2))

# 全量副本（含未收录）——用来做集合自检
allslugs = re.findall(r'\{ id = "([a-z_0-9]+)"', rd(os.path.join(DF, "Core", "Data", "Data_Dungeons.lua")))
if not allslugs:
    die("Data_Dungeons.lua 里读不到副本清单（结构变了？）")
# MANUAL_ONLY：不在 Data_Dungeons 副本表里的手工落键（团本走 RaidUI 自己的数据）
MANUAL_ONLY = {"onyxias_lair"}
expect_hit = len(allslugs) - len(MISSING) + len(MANUAL_ONLY)
if len(rows) != expect_hit:
    die("落键数 %d != 预期 %d（副本表 %d 个 − 未收录 %d 个 + 团本手工 %d 个）"
        % (len(rows), expect_hit, len(allslugs), len(MISSING), len(MANUAL_ONLY)))
if sorted(set(allslugs) - set(rows)) != sorted(set(MISSING)):
    die("未收录清单与预期不一致：\n  实际 = %s\n  预期 = %s"
        % (sorted(set(allslugs) - set(rows)), sorted(MISSING)))
if not MANUAL_ONLY <= set(rows):
    die("团本手工落键缺失：%s" % sorted(MANUAL_ONLY - set(rows)))

# ── ④ 产出 ─────────────────────────────────────────────────────────────────
HEAD = [
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    "",
    "local _, ns = ...",
    "",
    "ns.DungeonEntry = {",
]
lines = list(HEAD)
order = sorted(rows, key=lambda s: (rows[s][0], rows[s][1], s))
for slug in order:
    mid, x, y, zone = rows[slug]
    lines.append('    ["%s"] = { %d, %.1f, %.1f, "%s" },' % (slug, mid, x, y, zone))
lines += ["}", ""]
if ROUTE:
    lines += [
        "-- 多段指引点：航点仍落 ns.DungeonEntry 的主点（副本入口），本表只供提示框逐行展示。",
        "ns.DungeonEntryRoute = {",
    ]
    for slug in sorted(ROUTE):
        pts = ", ".join('{ %d, %.1f, %.1f, "%s", "%s" }' % (m2, x2, y2, lbl, maploc[m2])
                        for m2, x2, y2, lbl in ROUTE[slug])
        lines.append('    ["%s"] = { %s },' % (slug, pts))
    lines += ["}", ""]

out = CRLF.join(lines)
if "\n" in out.replace(CRLF, ""):
    die("输出里出现了裸 LF —— 本文件必须全 CRLF")

open(DST, "wb").write(out.encode("utf-8"))
print("已生成 %s" % DST)
print("  落键 %d 条 / 全部 %d 个副本；未收录 %d 个：%s"
      % (len(rows), len(allslugs), len(MISSING), "、".join(sorted(MISSING))))
if ROUTE:
    print("  指引点 %d 条：%s" % (sum(len(v) for v in ROUTE.values()),
                                 "、".join(sorted(ROUTE))))
for slug in order:
    mid, x, y, zone = rows[slug]
    print("    %-22s [%d] %-8s %6.1f, %-6.1f" % (slug, mid, zone, x, y))
