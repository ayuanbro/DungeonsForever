# -*- coding: utf-8 -*-
"""检查 Data_DungeonQuests.lua 里 prev 链引用是否都存在（孤儿引用检查）。"""
import re
import sys

SRC = "Core/Data/Data_DungeonQuests.lua"


def main():
    src = open(SRC, encoding="utf-8").read()
    cur = None
    ids = set()
    refs = []  # (source_id, source_key, target_id)
    dkg = re.compile(r'^\s*\["([a-z_0-9]+)"\]\s*=\s*\{')
    # { id, side, .. , bool, prevList, ...
    row = re.compile(
        r'^\s*\{\s*(\d+),\s*(?:nil|"[AH]"),\s*(\d+),\s*(?:nil|\d+),'
        r'\s*(?:"(?:[^"\\]|\\.)*"|nil),\s*(?:"(?:[^"\\]|\\.)*"|nil),'
        r'\s*(?:"(?:[^"\\]|\\.)*"|nil),\s*(true|false),\s*'
        r'(\{[0-9,\s]*\}|nil)')
    for line in src.splitlines():
        m = dkg.match(line)
        if m and 'ns.DungeonQuests' not in line:
            cur = m.group(1)
            continue
        if cur is None:
            continue
        mr = row.match(line)
        if not mr:
            continue
        qid = int(mr.group(1))
        ids.add(qid)
        prev = mr.group(4)
        if prev != 'nil':
            for t in re.findall(r'\d+', prev):
                refs.append((qid, cur, int(t)))

    orphans = {}
    for qid, key, t in refs:
        if t not in ids:
            orphans.setdefault(t, []).append((qid, key))

    print(f"任务总数 {len(ids)}，prev 引用 {len(refs)} 条")
    print(f"\n===== 孤儿引用（被引用但表内不存在）: {len(orphans)} =====")
    for t in sorted(orphans):
        users = orphans[t]
        print(f"  {t:7d}  <- 被 {', '.join(f'{u[0]}({u[1]})' for u in users)} 引用")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
