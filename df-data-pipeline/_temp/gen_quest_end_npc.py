import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.path.join(HERE, "_wh_qend_raw.json")
CACHE = os.path.join(HERE, "_wh_qend")
AREAMAP = os.path.join(ROOT, "Core/Data/Data_AreaMap.lua")
NPCLOC = os.path.join(ROOT, "Core/Data/Data_NPCLoc.lua")
QUESTS = os.path.join(ROOT, "Core/Data/Data_DungeonQuests.lua")
DST = os.path.join(ROOT, "Core/Data/Data_QuestEndNpc.lua")

SW_MAP = 1453


def read_area_map():
    src = io.open(AREAMAP, encoding="utf-8").read()
    return {int(a): int(b) for a, b in re.findall(r"\[(\d+)\] = (\d+)", src)}


def read_npcloc():
    src = io.open(NPCLOC, encoding="utf-8").read()
    return {int(m.group(1)): (int(m.group(2)), float(m.group(3)), float(m.group(4)))
            for m in re.finditer(r'\[(\d+)\] = \{ (\d+), ([\d.]+), ([\d.]+), ', src)}


MANUAL_NAMES = {252085: "大法师塞林德拉"}


def read_names():
    src = io.open(QUESTS, encoding="utf-8").read()
    names = {}
    for m in re.finditer(r', (\d{3,7}), "([^"]+)", \{ (?:xp|money|rep)', src):
        names.setdefault(int(m.group(1)), m.group(2))
    for m in re.finditer(r'npc = "([^"]+)", npcid = (\d+)', src):
        names.setdefault(int(m.group(2)), m.group(1))
    for m in re.finditer(r'npcid = (\d+), npc = "([^"]+)"', src):
        names.setdefault(int(m.group(1)), m.group(2))
    names.update(MANUAL_NAMES)
    return names


ROW_RE = re.compile(r'\{ (\d{3,7}), "[AH]", \d+, \d+, "([^"]*)", "([^"]*)",')
TAIL_RE = re.compile(r', (\d{3,7}), "([^"]+)", \{ (?:xp|money|rep)')
COORD_RE = re.compile(r'\d+[,.]\d+')


def read_loctext():
    src = io.open(QUESTS, encoding="utf-8").read()
    out = {}
    for line in src.splitlines():
        m = ROW_RE.search(line)
        if not m:
            continue
        loc = m.group(3)
        if not COORD_RE.search(loc):
            continue
        t = TAIL_RE.search(line)
        if not t:
            continue
        out.setdefault(int(t.group(1)), loc)
    return out


def sw_fix(x, y):
    return round(0.760476 * x + 21.0335, 1), round(0.781010 * y + 23.7064, 1)


def load_rows():
    rows = {}
    if os.path.isdir(CACHE):
        for fn in os.listdir(CACHE):
            if fn.endswith(".json"):
                rows[fn[:-5]] = json.load(io.open(os.path.join(CACHE, fn), encoding="utf-8"))
        return rows
    return json.load(io.open(RAW, encoding="utf-8"))


def is_ascii(s):
    return bool(s) and all(ord(c) < 128 for c in s)


def main():
    areas = read_area_map()
    npcloc = read_npcloc()
    cn_names = read_names()
    loctext = read_loctext()
    rows = load_rows()
    out, no_end, renamed = {}, 0, 0
    stat = {"full": 0, "name-only": 0, "sw-fit": 0, "loc-pref": 0}
    for qid, rec in rows.items():
        ends = (rec or {}).get("end") or []
        if not ends:
            no_end += 1
            continue
        e = ends[0]
        npcid = e.get("npcid")
        x, y = e.get("x"), e.get("y")
        name = (e.get("name") or "").strip()
        zone = (e.get("zone") or "").strip()
        area = e.get("area")
        if npcid and is_ascii(name):
            cn = cn_names.get(int(npcid))
            if cn:
                name = cn
                renamed += 1
        if name.startswith("[") and name.endswith("]"):
            name = name[1:-1]
        mapid = None
        if x is not None and y is not None:
            mapid = areas.get(int(area)) if area else None
            if not mapid and npcid:
                loc = npcloc.get(int(npcid))
                mapid = loc[0] if loc else None
            loc = npcloc.get(int(npcid)) if npcid else None
            if loc and (mapid is None or loc[0] == mapid):
                mapid = loc[0]
                x, y = loc[1], loc[2]
                stat["loc-pref"] += 1
            elif mapid == SW_MAP:
                x, y = sw_fix(x, y)
                stat["sw-fit"] += 1
            if mapid:
                stat["full"] += 1
            else:
                stat["name-only"] += 1
        else:
            x = y = None
            stat["name-only"] += 1
        lt = loctext.get(int(npcid)) if npcid else None
        out[int(qid)] = (npcid, name, mapid, x, y, zone, lt)
    lines = ["local _, ns = ...", "", "ns.DungeonQuestEndNpc = {"]
    for qid in sorted(out):
        npcid, name, mapid, x, y, zone, lt = out[qid]
        nm = '"%s"' % name if name else "nil"
        mp = str(mapid) if mapid else "nil"
        xs = "%.1f" % x if x is not None else "nil"
        ys = "%.1f" % y if y is not None else "nil"
        zn = '"%s"' % zone if zone else "nil"
        lts = ', "%s"' % lt if lt else ""
        lines.append("    [%d] = { %s, %s, %s, %s, %s, %s%s },"
                     % (qid, npcid if npcid else "nil", nm, mp, xs, ys, zn, lts))
    lines.append("}")
    lines.append("")
    io.open(DST, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
    print("wrote", len(out), "->", DST)
    print("no-end", no_end, "| full", stat["full"], "name-only", stat["name-only"],
          "| loc-pref", stat["loc-pref"], "sw-fit", stat["sw-fit"], "| renamed", renamed,
          "| loctext", sum(1 for v in out.values() if v[6]))


if __name__ == "__main__":
    main()
