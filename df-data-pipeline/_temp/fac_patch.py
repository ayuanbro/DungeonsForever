# -*- coding: utf-8 -*-
"""按 DBC + wowhead 扫描结果修补 Data_DungeonQuests.lua 阵营字段（CRLF 保留）。"""
import json
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

QF = "D:/workspace/DungeonsForever/Core/Data/Data_DungeonQuests.lua"
QJ = "D:/workspace/DungeonsForever/_temp/questie/questie_forever.json"
SW = "D:/workspace/DungeonsForever/_temp/fac_wowhead_sweep.json"

KEEP_MASKS = {5, 162}


def target_fac(qid, races, sweep):
    v = races.get(str(qid))
    if v is not None:
        low = v & 0xFFFFFFFF
        if low == 77:
            return "A", "DBC"
        if low == 178:
            return "H", "DBC"
        if low in KEEP_MASKS or low not in (0,):
            return None, f"DBC-mask={low}(keep)"
        return None, "DBC-0"
    s = sweep.get(str(qid), {})
    side = s.get("side")
    if side == "Alliance":
        return "A", "wowhead"
    if side == "Horde":
        return "H", "wowhead"
    if side in ("Both", "None"):
        return None, "wowhead-" + side
    return None, "UNRESOLVED"


def main(apply=False):
    src = open(QF, encoding="utf-8", newline="").read()
    assert "\r\n" in src and src.count("\n") == src.count("\r\n"), "行尾异常"
    races = json.load(open(QJ, encoding="utf-8"))["quest_races"]
    sweep = json.load(open(SW, encoding="utf-8"))

    row_re = re.compile(r'^(\s*\{\s*(\d+),\s*)("(?:A|H)"|nil)(\s*,.*)$')
    changes, unresolved, kept = [], [], []
    out_lines = []
    for line in src.split("\r\n"):
        m = row_re.match(line)
        if not m:
            out_lines.append(line)
            continue
        qid = int(m.group(2))
        cur = m.group(3).strip('"') if m.group(3) != "nil" else None
        tgt, src_note = target_fac(qid, races, sweep)
        if src_note == "UNRESOLVED":
            unresolved.append((qid, cur))
            out_lines.append(line)
            continue
        if src_note.startswith("DBC-mask") or src_note == "DBC-0":
            kept.append((qid, cur, src_note))
            out_lines.append(line)
            continue
        if tgt != cur:
            new = m.group(1) + ('"A"' if tgt == "A" else '"H"' if tgt == "H" else "nil") + m.group(4)
            out_lines.append(new)
            changes.append((qid, cur, tgt, src_note))
        else:
            out_lines.append(line)

    print(f"计划修改 {len(changes)} 行：")
    for qid, cur, tgt, note in changes:
        print(f"  {qid:6d} {cur or 'nil':4s} -> {tgt or 'nil':4s}  ({note})")
    print(f"特殊掩码/零掩码保留 {len(kept)} 行；未裁决 {len(unresolved)} 行:")
    for qid, cur in unresolved:
        print(f"  {qid} 我={cur or 'nil'}")
    if apply and changes:
        data = "\r\n".join(out_lines)
        open(QF, "w", encoding="utf-8", newline="").write(data)
        b = open(QF, "rb").read()
        assert b.count(b"\r\n") == b.count(b"\n"), "写后行尾翻转!"
        print(f"[OK] 已写入，CRLF {b.count(b'CRLF'[:0])}")
    elif apply:
        print("[SAME] 无改动")


if __name__ == "__main__":
    main(apply="--apply" in sys.argv)
