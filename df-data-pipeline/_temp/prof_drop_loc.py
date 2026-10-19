import base64
import glob
import json
import os
import re
import sys

import cbor2

HERE = os.path.dirname(os.path.abspath(__file__))
TOC = os.path.join(HERE, "questie", "forever", "QuestieDB", "QuestieDB_Forever.toc")
DATA = os.path.join(HERE, "_fc", "data")
SPAWNS = os.path.join(HERE, "questie", "questie_forever.json")

pat = re.compile(r"^## X-Npc-(\d+)-S:\s*(\S+)\s*$", re.M)


def decode_b64(b64):
    return cbor2.loads(base64.b64decode(b64))


def as_text(v):
    if isinstance(v, bytes):
        return v.decode("utf-8", "replace")
    if isinstance(v, str):
        return v
    return None


def load_npc_names():
    txt = open(TOC, encoding="utf-8", errors="replace").read()
    names = {}
    for m in pat.finditer(txt):
        eid, val = int(m.group(1)), m.group(2)
        try:
            row = decode_b64(val)
        except Exception:
            continue
        if isinstance(row, dict):
            nm = as_text(row.get(1))
            if nm:
                names[eid] = nm
    return names


def load_drop_names():
    names = set()
    for f in glob.glob(os.path.join(DATA, "prof_*.json")):
        d = json.load(open(f, encoding="utf-8"))
        for coll in ("rows", "enchants", "crafted"):
            for r in d.get(coll) or []:
                src = r.get("source")
                if not isinstance(src, dict):
                    continue
                for dd in src.get("drops") or []:
                    if isinstance(dd, dict) and dd.get("npc"):
                        names.add(dd["npc"])
    return names


def main():
    names = load_npc_names()
    spawns = json.load(open(SPAWNS, encoding="utf-8")).get("npc_spawns") or {}
    by_name = {}
    by_name_ci = {}
    for eid, nm in names.items():
        by_name.setdefault(nm, eid)
        by_name_ci.setdefault(nm.lower(), eid)
    drop_names = load_drop_names()
    out = {}
    miss = []
    for nm in sorted(drop_names):
        eid = by_name.get(nm) or by_name_ci.get(nm.lower())
        if not eid:
            miss.append(nm)
            continue
        sp = spawns.get(str(eid)) or spawns.get(eid) or {}
        if not sp:
            miss.append(nm)
            continue
        pts = []
        for z, xy in sorted(sp.items(), key=lambda kv: int(kv[0])):
            if isinstance(xy, (list, tuple)) and len(xy) >= 2:
                pts.append([int(z), round(float(xy[0]), 1), round(float(xy[1]), 1)])
        if pts:
            out[nm] = {"id": int(eid), "spawns": pts}
    dst = os.path.join(DATA, "drop_loc.json")
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("drop npc names: %d, resolved: %d, missing: %d" % (len(drop_names), len(out), len(miss)))
    for nm in miss[:20]:
        print("  miss:", nm)
    return 0


if __name__ == "__main__":
    sys.exit(main())
