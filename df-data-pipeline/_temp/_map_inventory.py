# -*- coding: utf-8 -*-
"""对 34 个副本做「有没有地图美术」盘点：读 listfile 的 worldmap 目录集合，按关键词匹配。"""
import io, json, re, sys

LF = r"D:/workspace/DungeonsForever/_temp/_community-listfile.csv"
DUNS = [
    ("hall_of_thanes",     "领主大厅",              "Hall of Thanes"),
    ("ragefire_chasm",     "怒焰裂谷",              "Ragefire Chasm"),
    ("ruins_of_lordaeron", "洛丹伦废墟",            "Ruins of Lordaeron"),
    ("wailing_caverns",    "哀嚎洞穴",              "Wailing Caverns"),
    ("the_deadmines",      "死亡矿井",              "The Deadmines"),
    ("shadowfang_keep",    "影牙城堡",              "Shadowfang Keep"),
    ("excavation_wetlands","挖掘场：湿地",          "Excavation Site: Wetlands"),
    ("blackfathom_deeps",  "黑暗深渊",              "Blackfathom Deeps"),
    ("the_stockade",       "监狱",                  "The Stockade"),
    ("city_of_dalaran",    "达拉然城",              "City of Dalaran"),
    ("gnomeregan",         "诺莫瑞根",              "Gnomeregan"),
    ("razorfen_kraul",     "剃刀沼泽",              "Razorfen Kraul"),
    ("sm_graveyard",       "血色修道院：墓地",       "Scarlet Monastery Graveyard"),
    ("sm_library",         "血色修道院：图书馆",     "Scarlet Monastery Library"),
    ("the_drowned_city",   "沉没之城",              "The Drowned City"),
    ("sm_armory",          "血色修道院：军械库",     "Scarlet Monastery Armory"),
    ("razorfen_downs",     "剃刀高地",              "Razorfen Downs"),
    ("sm_cathedral",       "血色修道院：大教堂",     "Scarlet Monastery Cathedral"),
    ("kroldok_stronghold", "克罗多克要塞",          "Kroldok Stronghold"),
    ("uldaman",            "奥达曼",                "Uldaman"),
    ("zul_farrak",         "祖尔法拉克",            "Zul'Farrak"),
    ("maraudon",           "玛拉顿",                "Maraudon"),
    ("alcaz_prison",       "奥卡兹监狱",            "Alcaz Prison"),
    ("sunken_temple",      "沉没的神庙",            "Sunken Temple"),
    ("blackrock_depths",   "黑石深渊",              "Blackrock Depths"),
    ("dire_maul_east",     "厄运之槌：东",          "Dire Maul East"),
    ("blackmaw_hold",      "黑喉要塞",              "Blackmaw Hold"),
    ("lower_blackrock_spire","黑石塔下层",          "Lower Blackrock Spire"),
    ("dire_maul_north",    "厄运之槌：北",          "Dire Maul North"),
    ("dire_maul_west",     "厄运之槌：西",          "Dire Maul West"),
    ("scholomance",        "通灵学院",              "Scholomance"),
    ("shapers_terrace",    "塑造者平台",            "Shaper's Terrace"),
    ("stratholme_main",    "斯坦索姆：正门",        "Stratholme Main Gate"),
    ("stratholme_service", "斯坦索姆：侧门",        "Stratholme Service Gate"),
    ("upper_blackrock_spire","黑石塔上层",          "Upper Blackrock Spire"),
]

# 手工关键词（比自动拆词准）；值 = 在目录名里要找的子串（任一命中即候选）
KEY = {
    "hall_of_thanes":     ["oldironforge", "ironforge"],
    "ragefire_chasm":     ["ragefire"],
    "ruins_of_lordaeron": ["lordaeron", "ruinsoflordaeron", "undercity", "tirisfal"],
    "wailing_caverns":    ["wailing"],
    "the_deadmines":      ["deadmine"],
    "shadowfang_keep":    ["shadowfang"],
    "excavation_wetlands":["excavation", "wetlands"],
    "blackfathom_deeps":  ["blackfathom"],
    "the_stockade":       ["stockade"],
    "city_of_dalaran":    ["dalaran"],
    "gnomeregan":         ["gnomeregan"],
    "razorfen_kraul":     ["razorfen"],
    "sm_graveyard":       ["scarlet", "monastery"],
    "sm_library":         ["scarlet", "monastery"],
    "the_drowned_city":   ["drowned", "drownedcity"],
    "sm_armory":          ["scarlet", "monastery"],
    "razorfen_downs":     ["razorfen"],
    "sm_cathedral":       ["scarlet", "monastery"],
    "kroldok_stronghold": ["kroldok", "stronghold"],
    "uldaman":            ["uldaman"],
    "zul_farrak":         ["zulfarrak"],
    "maraudon":           ["maraudon"],
    "alcaz_prison":       ["alcaz"],
    "sunken_temple":      ["sunkentemple", "templeofatul"],
    "blackrock_depths":   ["blackrockdepths", "blackrock"],
    "dire_maul_east":     ["diremaul"],
    "blackmaw_hold":      ["blackmaw"],
    "lower_blackrock_spire":["blackrockspire", "blackrock"],
    "dire_maul_north":    ["diremaul"],
    "dire_maul_west":     ["diremaul"],
    "scholomance":        ["scholomance"],
    "shapers_terrace":    ["shapers", "terrace"],
    "stratholme_main":    ["stratholme"],
    "stratholme_service": ["stratholme"],
    "upper_blackrock_spire":["blackrockspire", "blackrock"],
}

dirs = {}
with io.open(LF, "r", encoding="utf-8", errors="replace") as f:
    for line in f:
        i = line.find(";")
        if i < 0: continue
        path = line[i+1:].strip().lower()
        if not path.startswith("interface/worldmap/"): continue
        rest = path[len("interface/worldmap/"):]
        parts = rest.split("/")
        d = parts[0] if len(parts) > 1 else "<root>"
        dirs.setdefault(d, []).append(parts[-1])

def tiles(files):
    """数出 <base>N.blp 组成的整套瓦片数量（N 从 1 起连续）"""
    best = {}
    for fn in files:
        m = re.match(r"^(.*?)(\d+)\.blp$", fn)
        if not m: continue
        base, n = m.group(1), int(m.group(2))
        best.setdefault(base, set()).add(n)
    out = []
    for base, ns in best.items():
        if len(ns) >= 6:
            out.append((base, min(ns), max(ns), len(ns)))
    return sorted(out, key=lambda x: -x[3])

print("%-24s %-14s %s" % ("副本", "目录候选", "瓦片组"))
print("-" * 100)
for did, zh, en in DUNS:
    keys = KEY.get(did, [])
    hit = [d for d in sorted(dirs) if any(k in d for k in keys)]
    # 只保留「瓦片组」看起来完整的
    lines = []
    for d in hit[:6]:
        ts = tiles(dirs[d])
        lines.append("%s(%d 文件)" % (d, len(set(dirs[d]))))
    print("%-24s %-14s %s" % (zh, "", " | ".join(lines) if lines else "—— 无候选 ——"))
