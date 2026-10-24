import io
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CACHE = os.path.join(HERE, "_wh_qend")
AREAMAP = os.path.join(ROOT, "Core/Data/Data_AreaMap.lua")
NPCLOC = os.path.join(ROOT, "Core/Data/Data_NPCLoc.lua")
QUESTS = os.path.join(ROOT, "Core/Data/Data_DungeonQuests.lua")
DST = os.path.join(ROOT, "Core/Data/Data_QuestStartLoc.lua")

SW_MAP = 1453


def read_area_map():
    src = io.open(AREAMAP, encoding="utf-8").read()
    return {int(a): int(b) for a, b in re.findall(r"\[(\d+)\] = (\d+)", src)}


def read_npcloc():
    src = io.open(NPCLOC, encoding="utf-8").read()
    return {int(m.group(1)): (int(m.group(2)), float(m.group(3)), float(m.group(4)))
            for m in re.finditer(r'\[(\d+)\] = \{ (\d+), ([\d.]+), ([\d.]+), ', src)}


def quest_rows():
    src = io.open(QUESTS, encoding="utf-8").read()
    out = {}
    for m in re.finditer(r'\{ (\d{3,7}), "[AH]", ', src):
        s = m.start()
        depth = 0
        i = s
        instr = False
        while i < len(src):
            c = src[i]
            if c == '"' and src[i - 1] != "\\":
                instr = not instr
            elif not instr:
                if c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        break
            i += 1
        blk = src[s:i + 1]
        t = re.search(r', (\d{3,7}), "([^"]*)", \{ (?:xp|money|rep)', blk)
        if t:
            out[int(m.group(1))] = (int(t.group(1)), t.group(2))
        else:
            out.setdefault(int(m.group(1)), (None, None))
    return out


def sw_fix(x, y):
    return round(0.760476 * x + 21.0335, 1), round(0.781010 * y + 23.7064, 1)


def main():
    areas = read_area_map()
    npcloc = read_npcloc()
    rows = quest_rows()
    out = {}
    stat = {"row-npc": 0, "nl": 0, "wh": 0, "sw-fit": 0, "none": 0, "mismatch": 0}
    files = [f for f in os.listdir(CACHE) if f.endswith(".json")]
    for fn in files:
        qid = int(fn[:-5])
        rec = json.load(io.open(os.path.join(CACHE, fn), encoding="utf-8"))
        starts = rec.get("start") or []
        qnpc, qname = rows.get(qid, (None, None))
        npcid, name, mapid, x, y, zone = qnpc, qname, None, None, None, None
        if qnpc and qnpc in npcloc:
            mapid, x, y = npcloc[qnpc]
            stat["nl"] += 1
        elif starts:
            e = starts[0]
            snpc = e.get("npcid")
            if qnpc and snpc and int(snpc) != int(qnpc):
                stat["mismatch"] += 1
            npcid = qnpc or snpc
            name = name or (e.get("name") or "").strip()
            zone = (e.get("zone") or "").strip() or None
            sx, sy = e.get("x"), e.get("y")
            area = e.get("area")
            if sx is not None and sy is not None:
                mapid = areas.get(int(area)) if area else None
                if not mapid and snpc:
                    loc = npcloc.get(int(snpc))
                    mapid = loc[0] if loc else None
                loc = npcloc.get(int(snpc)) if snpc else None
                if loc and (mapid is None or loc[0] == mapid):
                    mapid, x, y = loc[0], loc[1], loc[2]
                    stat["nl"] += 1
                    stat["wh"] += 1
                elif mapid == SW_MAP:
                    x, y = sw_fix(sx, sy)
                    stat["sw-fit"] += 1
                    stat["wh"] += 1
                elif mapid:
                    x, y = round(float(sx), 1), round(float(sy), 1)
                    stat["wh"] += 1
        if not mapid:
            stat["none"] += 1
        if name:
            name = name.strip()
        out[qid] = (npcid, name, mapid, x, y, zone)
    lines = ["local _, ns = ...", "", "ns.DungeonQuestStartLoc = {"]
    for qid in sorted(out):
        npcid, name, mapid, x, y, zone = out[qid]
        nm = '"%s"' % name if name else "nil"
        mp = str(mapid) if mapid else "nil"
        xs = "%.1f" % x if x is not None else "nil"
        ys = "%.1f" % y if y is not None else "nil"
        zn = '"%s"' % zone if zone else "nil"
        lines.append("    [%d] = { %s, %s, %s, %s, %s, %s },"
                     % (qid, npcid if npcid else "nil", nm, mp, xs, ys, zn))
    lines.append("}")
    lines.append("")
    io.open(DST, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
    print("wrote", len(out), "->", DST)
    print("stat", stat)


if __name__ == "__main__":
    main()
