# -*- coding: utf-8 -*-
"""盘点：worldmap 目录 -> 瓦片组（base, 编号集合, 代表 fid），并对副本关键词输出候选。"""
import io, re, json, collections

LF = r"D:/workspace/DungeonsForever/_temp/_community-listfile.csv"
out = collections.defaultdict(lambda: collections.defaultdict(dict))  # 目录 -> base -> {n: fid}
with io.open(LF, "r", encoding="utf-8", errors="replace") as f:
    for line in f:
        i = line.find(";")
        if i < 0: continue
        fid, path = line[:i], line[i+1:].strip().lower()
        if not path.startswith("interface/worldmap/"): continue
        rest = path[len("interface/worldmap/"):]
        parts = rest.split("/")
        if len(parts) < 2: continue
        m = re.match(r"^(.*?)(\d+)\.blp$", parts[-1])
        if not m: continue
        out[parts[0]][m.group(1)][int(m.group(2))] = int(fid)

KEY = {
    "hall_of_thanes":     ["oldironforge", "ironforge"],
    "ragefire_chasm":     ["ragefire"],
    "ruins_of_lordaeron": ["lordaeron", "tirisfal", "undercity"],
    "wailing_caverns":    ["wailingcaverns"],
    "the_deadmines":      ["thedeadmines", "deadmineswestfall"],
    "shadowfang_keep":    ["shadowfangkeep"],
    "excavation_wetlands":["excavation", "wetlands"],
    "blackfathom_deeps":  ["blackfathom"],
    "the_stockade":       ["thestockade", "stockadescenario"],
    "city_of_dalaran":    ["dalaran"],
    "gnomeregan":         ["gnomeregan"],
    "razorfen_kraul":     ["razorfenkraul"],
    "sm_graveyard":       ["scarletmonastery", "scarlethalls", "scarletcathedral"],
    "sm_library":         ["scarletmonastery", "scarlethalls"],
    "the_drowned_city":   ["drowned"],
    "sm_armory":          ["scarletmonastery", "scarlethalls"],
    "razorfen_downs":     ["razorfendowns"],
    "sm_cathedral":       ["scarletmonastery", "scarletcathedral"],
    "kroldok_stronghold": ["kroldok"],
    "uldaman":            ["uldaman"],
    "zul_farrak":         ["zulfarrak"],
    "maraudon":           ["maraudon"],
    "alcaz_prison":       ["alcaz"],
    "sunken_temple":      ["sunkentemple", "templeofatul", "atalhakkar"],
    "blackrock_depths":   ["blackrockdepths"],
    "dire_maul_east":     ["diremaul"],
    "blackmaw_hold":      ["blackmaw"],
    "lower_blackrock_spire":["blackrockspire"],
    "dire_maul_north":    ["diremaul"],
    "dire_maul_west":     ["diremaul"],
    "scholomance":        ["scholomance"],
    "shapers_terrace":    ["shapers"],
    "stratholme_main":    ["stratholme"],
    "stratholme_service": ["stratholme"],
    "upper_blackrock_spire":["blackrockspire"],
}

res = {}
for did, keys in KEY.items():
    cands = []
    for d in sorted(out):
        if not any(k in d for k in keys): continue
        for base, ns in out[d].items():
            if len(ns) < 6: continue
            cands.append({
                "dir": d, "base": base, "n": len(ns),
                "min": min(ns), "max": max(ns),
                "firstFid": ns[min(ns)],
                "path": "Interface\WorldMap\%s\%s" % (d, base),
                "fids": {str(k): ns[k] for k in sorted(ns)},
            })
    cands.sort(key=lambda c: -c["n"])
    res[did] = cands

json.dump(res, open("_map_inv.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for did, c in res.items():
    print("== %-24s %d 个候选" % (did, len(c)))
    for x in c[:3]:
        print("     %-38s n=%-3d %d..%d  first=%d" % (x["dir"], x["n"], x["min"], x["max"], x["firstFid"]))
