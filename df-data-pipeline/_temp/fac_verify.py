# -*- coding: utf-8 -*-
"""核对 Data_DungeonQuests.lua 的阵营字段 vs QuestieDB requiredRaces（客户端 DBC）。"""
import json
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

QF = "D:/workspace/DungeonsForever/Core/Data/Data_DungeonQuests.lua"
QJ = "D:/workspace/DungeonsForever/_temp/questie/questie_forever.json"


def parse_ours():
    src = open(QF, encoding="utf-8").read()
    rows = []
    cur = None
    for line in src.splitlines():
        m = re.match(r'^\s*\["([a-z_0-9]+)"\]\s*=\s*\{', line)
        if m:
            cur = m.group(1)
            continue
        if cur is None or not line.strip().startswith("{ "):
            continue
        m2 = re.match(r'^\s*\{\s*(\d+),\s*("(?:A|H)"|nil)\s*,', line)
        if m2:
            fac = m2.group(2)
            rows.append({"dg": cur, "id": int(m2.group(1)),
                         "fac": fac.strip('"') if fac != "nil" else None,
                         "line": line.strip()[:80]})
        else:
            rows.append({"dg": cur, "id": None, "fac": "?", "line": line.strip()[:80]})
    return rows


def main():
    rows = parse_ours()
    qj = json.load(open(QJ, encoding="utf-8"))
    races = qj["quest_races"]

    def qfac(qid):
        v = races.get(str(qid), races.get(qid))
        if v is None:
            return None, "missing"
        v = v & 0xFFFFFFFF
        if v == 77:
            return "A", None
        if v == 178:
            return "H", None
        return None, f"mask={v}"

    ids = [r["id"] for r in rows if r["id"]]
    print(f"我方任务行: {len(rows)}，有效 id: {len(ids)}")
    stats = {"match": 0, "fixable": [], "conflict": [], "unparsed": 0,
             "dbc_missing": [], "dbc_other": []}
    for r in rows:
        if r["id"] is None:
            stats["unparsed"] += 1
            continue
        f, note = qfac(r["id"])
        if note == "missing":
            stats["dbc_missing"].append(r)
            continue
        if note and note.startswith("mask"):
            stats["dbc_other"].append((r, note))
            if r["fac"] is None:
                stats["match"] += 1
            else:
                stats["fixable"].append((r, None, note))
            continue
        if f == r["fac"]:
            stats["match"] += 1
        else:
            stats["fixable"].append((r, f, note))

    print(f"\n一致: {stats['match']}")
    print(f"\n=== 我方标了 A/H 但 DBC 说另一阵营/双阵营（需改或复查）===")
    for r, f, note in stats["fixable"]:
        print(f"  {r['dg']:26s} {r['id']:6d} 我={r['fac'] or 'nil'} DBC={f or note}")
    print(f"\n=== DBC 缺失（{len(stats['dbc_missing'])}）===")
    for r in stats["dbc_missing"]:
        print(f"  {r['dg']:26s} {r['id']:6d} 我={r['fac'] or 'nil'}")
    print(f"\n=== DBC 其他掩码（{len(stats['dbc_other'])}）===")
    for r, note in stats["dbc_other"]:
        print(f"  {r['dg']:26s} {r['id']:6d} 我={r['fac'] or 'nil'} {note}")
    print(f"未解析行: {stats['unparsed']}")


if __name__ == "__main__":
    main()
