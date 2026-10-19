#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把客户端 ClassQuestsForever 的职业任务数据转成 DungeonsForever 的数据文件。

用法:
    python gen_class_quest.py --stats
    python gen_class_quest.py [--apply]

读:  D:/Game/World of Warcraft/_cn_beta_/Interface/AddOns/ClassQuestsForever/Data/{Quests,Chains}.lua
写:  Core/Data/Data_ClassQuest.lua
可选: _temp/_cq_names.json   ({ "1638": "战士的训练", ... })
      _temp/_cq_zone_zh.json ({ "Elwynn Forest": "艾尔文森林", ... })
"""
import io
import json
import os
import sys

from lupa import lua51

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = "D:/Game/World of Warcraft/_cn_beta_/Interface/AddOns/ClassQuestsForever/Data"
OUT = os.path.join(ROOT, "Core", "Data", "Data_ClassQuest.lua")

CLASSES = ["WARRIOR", "PALADIN", "HUNTER", "ROGUE", "PRIEST",
           "SHAMAN", "MAGE", "WARLOCK", "DRUID"]

MAP_FIX = {2665: 2521}


def dec(v):
    if isinstance(v, bytes):
        return v.decode("utf-8", "replace")
    return v


def load():
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    env = L.eval("""
        function()
            local ns = {}
            local CQF = {}
            local files = {"Quests", "Chains"}
            for _, f in ipairs(files) do
                local path = "%s/" .. f .. ".lua"
                local fh = assert(io.open(path, "rb"))
                local src = fh:read("*a")
                fh:close()
                local chunk, err = loadstring(src)
                if not chunk then error(path .. ": " .. tostring(err)) end
                chunk(nil, CQF)
            end
            return CQF
        end
    """ % SRC.replace("\\", "/"))
    return env()


def dump_quests(cqf):
    out = {}
    q = cqf.Quests
    for k, v in q.items():
        qid = int(k)
        rec = {}
        rec["n"] = dec(v["n"])
        rec["l"] = int(v["l"] or 0)
        rec["r"] = int(v["r"] or 0)
        f = dec(v["f"])
        if f:
            rec["f"] = f
        races = v["races"]
        if races is not None:
            rec["races"] = [int(x) for x in races.values()]
        for key in ("s", "e"):
            t = v[key]
            if t is None:
                continue
            arr = list(t.values())
            if not arr:
                continue

            def point(vals):
                if len(vals) < 2:
                    return None
                nid = int(vals[0])
                nm = dec(vals[1]) if len(vals) > 1 and vals[1] else ""
                if NpcZh.get(str(nid)):
                    nm = NpcZh[str(nid)]
                out = [nid]
                out.append(nm)
                out.append(dec(vals[2]) if len(vals) > 2 and vals[2] else "")
                out.append(float(vals[3]) if len(vals) > 3 and vals[3] else 0.0)
                out.append(float(vals[4]) if len(vals) > 4 and vals[4] else 0.0)
                return out

            if hasattr(arr[0], "values"):
                pts = [p for p in (point(list(x.values())) for x in arr) if p]
                if pts:
                    rec[key] = pts
            else:
                p = point(arr)
                if p:
                    rec[key] = p
        for key in ("items", "spells"):
            t = v[key]
            if t is not None:
                lst = [int(x) for x in t.values()]
                if lst:
                    rec[key] = lst
        out[qid] = rec
    return out


CHAIN_FIELDS = ["key", "title", "steps", "group", "races", "faction", "shared",
                "after", "afterAny", "reward", "minLevel", "cat", "extra",
                "note", "section", "anyOrder", "choice", "art", "artTitle"]


def plain(v):
    if v is None:
        return None
    if isinstance(v, (bool, int, float)):
        return v
    if isinstance(v, bytes):
        return dec(v)
    if hasattr(v, "values"):
        vals = list(v.values())
        if vals and isinstance(vals[0], (bytes, int, float)):
            return [plain(x) for x in vals]
        out = {}
        for k, x in v.items():
            out[dec(k)] = plain(x)
        return out
    return v


def dump_chains(cqf):
    out = {}
    for cls in CLASSES:
        lst = cqf.Chains[cls]
        if lst is None:
            continue
        rows = []
        for c in lst.values():
            rec = {}
            for f in CHAIN_FIELDS:
                val = c[f]
                if val is None:
                    continue
                rec[f] = plain(val)
            rows.append(rec)
        out[cls] = rows
    return out


def lua_val(v, ind=0):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, str):
        return '"%s"' % v.replace("\\", "\\\\").replace('"', '\\"')
    if isinstance(v, (int, float)):
        if isinstance(v, float) and v == int(v):
            return "%d" % int(v)
        return ("%g" % v) if isinstance(v, float) else str(v)
    if isinstance(v, list):
        return "{ " + ", ".join(lua_val(x) for x in v) + " }"
    if isinstance(v, dict):
        parts = []
        for k, x in v.items():
            if isinstance(k, str) and not k.isdigit():
                parts.append("%s = %s" % (k, lua_val(x)))
            else:
                parts.append("[%s] = %s" % (k, lua_val(x)))
        return "{ " + ", ".join(parts) + " }"
    return "nil"


NpcZh = {}
_npc_path = os.path.join(ROOT, "_temp", "_cq_npc_zh.json")
if os.path.exists(_npc_path):
    with io.open(_npc_path, encoding="utf-8") as fh:
        NpcZh = json.load(fh)

_manual_path = os.path.join(ROOT, "_temp", "_cq_npc_manual.json")
if os.path.exists(_manual_path):
    with io.open(_manual_path, encoding="utf-8") as fh:
        NpcZh.update(json.load(fh))


ItemZh = {}
_item_path = os.path.join(ROOT, "_temp", "_cq_item_zh.json")
if os.path.exists(_item_path):
    with io.open(_item_path, encoding="utf-8") as fh:
        ItemZh = json.load(fh)

_note_path = os.path.join(ROOT, "_temp", "_cq_notes.json")
QuestNotes = {}
if os.path.exists(_note_path):
    with io.open(_note_path, encoding="utf-8") as fh:
        QuestNotes = json.load(fh)


def main():
    cqf = load()
    quests = dump_quests(cqf)
    chains = dump_chains(cqf)

    names = {}

    npath = os.path.join(ROOT, "_temp", "_cq_names.json")
    if os.path.exists(npath):
        with io.open(npath, encoding="utf-8") as fh:
            names = json.load(fh)

    zpath = os.path.join(ROOT, "_temp", "_cq_zone_zh.json")
    zones = {}
    if os.path.exists(zpath):
        with io.open(zpath, encoding="utf-8") as fh:
            zones = json.load(fh)

    tpath = os.path.join(ROOT, "_temp", "_cq_title_zh.json")
    zh_text = {}
    if os.path.exists(tpath):
        with io.open(tpath, encoding="utf-8") as fh:
            zh_text = json.load(fh)

    mpath = os.path.join(ROOT, "_temp", "_cq_zone_map.json")
    zonemap = {}
    if os.path.exists(mpath):
        with io.open(mpath, encoding="utf-8") as fh:
            zonemap = json.load(fh)
    zonemap = {k: MAP_FIX.get(int(v), int(v)) for k, v in zonemap.items()}

    byname = {}
    for qid, q in quests.items():
        cn = names.get(str(qid))
        if cn:
            byname.setdefault(q["n"], cn)

    def chain_title(t):
        if t in zh_text:
            return zh_text[t]
        if t in byname:
            return byname[t]
        return t

    if "--stats" in sys.argv:
        print("quests", len(quests), "classes", len(chains))
        for cls in CLASSES:
            rows = chains.get(cls) or []
            ids = set()
            for c in rows:
                def walk(s):
                    if isinstance(s, list):
                        for x in s:
                            walk(x)
                    elif isinstance(s, (int, float)):
                        ids.add(int(s))
                walk(c.get("steps"))
            print("%-9s chains=%-3d quests=%-4d" % (cls, len(rows), len(ids)))
        zs = {}
        for q in quests.values():
            for key in ("s", "e"):
                t = q.get(key)
                if not t:
                    continue
                pts = t if isinstance(t[0], list) else [t]
                for p in pts:
                    zs[p[2]] = zs.get(p[2], 0) + 1
        print("\nzones", len(zs))
        for z, n in sorted(zs.items(), key=lambda x: -x[1]):
            print("  %-32s %3d  %s" % (z, n, zones.get(z, "")))
        print("\nnames loaded", len(names))
        return

    if "--apply" not in sys.argv:
        print("dry-run: 加 --apply 才写文件")
        return

    buf = io.StringIO()
    buf.write("local _, ns = ...\n\n")
    buf.write("ns.ClassQuestChains = {\n")
    for cls in CLASSES:
        rows = chains.get(cls)
        if not rows:
            continue
        buf.write("    %s = {\n" % cls)
        for c in rows:
            parts = []
            parts.append('t = %s' % lua_val(chain_title(c["title"])))
            for k in ("key", "steps", "group", "races", "faction",
                      "after", "afterAny", "note", "cat", "extra", "anyOrder",
                      "choice", "minLevel"):
                if k not in c:
                    continue
                v = c[k]
                if k == "note":
                    v = zh_text.get(v, v)
                parts.append("%s = %s" % (k, lua_val(v)))
            rew = c.get("reward")
            if isinstance(rew, dict) and "spell" in rew:
                parts.append("spell = %s" % lua_val(rew["spell"]))
            buf.write("        { %s },\n" % ", ".join(parts))
        buf.write("    },\n")
    buf.write("}\n\n")

    buf.write("ns.ClassQuestInfo = {\n")
    for qid in sorted(quests):
        q = quests[qid]
        parts = []
        nm = q["n"]
        zh = names.get(str(qid))
        parts.append('n = "%s"' % nm.replace("\\", "\\\\").replace('"', '\\"'))
        if zh and zh != nm:
            parts.append('cn = "%s"' % zh.replace("\\", "\\\\").replace('"', '\\"'))
        parts.append("l = %d" % q["l"])
        parts.append("r = %d" % q["r"])
        if q.get("f"):
            parts.append('f = "%s"' % q["f"])
        if q.get("races"):
            parts.append("races = %s" % lua_val(q["races"]))
        for key in ("s", "e"):
            t = q.get(key)
            if not t:
                continue
            def fix(p):
                p = list(p)
                p[2] = zones.get(p[2], p[2])
                mid = zonemap.get(p[2])
                while len(p) < 5:
                    p.append(0.0)
                if mid:
                    p = p[:5] + [int(MAP_FIX.get(int(mid), int(mid)))]
                return lua_val(p)

            if isinstance(t[0], list):
                pts = [fix(p) for p in t]
                parts.append("%s = { %s }" % (key, ", ".join(pts)))
            else:
                parts.append("%s = %s" % (key, fix(t)))
        for key in ("items", "spells"):
            if q.get(key):
                parts.append("%s = %s" % (key, lua_val(q[key])))
        note = QuestNotes.get(str(qid))
        if note:
            esc = str(note).replace("\\", "\\\\").replace('"', '\\"')
            parts.append('note = "%s"' % esc)
        buf.write("    [%d] = { %s },\n" % (qid, ", ".join(parts)))
    buf.write("}\n\n")

    used = set()
    for qid in sorted(quests):
        for iid in quests[qid].get("items", []):
            used.add(int(iid))
    if used:
        buf.write("ns.ClassQuestItemName = {\n")
        for iid in sorted(used):
            nm = ItemZh.get(str(iid))
            if nm:
                esc = nm.replace("\\", "\\\\").replace('"', '\\"')
                buf.write('    [%d] = "%s",\n' % (iid, esc))
        buf.write("}\n")

    text = buf.getvalue()
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print("wrote", OUT, len(text), "bytes")


if __name__ == "__main__":
    main()
