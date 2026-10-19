#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""从游戏客户端批量取职业任务的中文名，写 _temp/_cq_names.json。

用法: python _cq_fetch_names.py
"""
import io
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WX = "D:/workspace/project-024-wuxian-workshop/.venv/Scripts/wuxian.exe"
sys.path.insert(0, os.path.join(ROOT, "_temp"))
from gen_class_quest import load, dump_quests, dump_chains  # noqa: E402

BATCH = 90


def run(code, timeout=30):
    p = subprocess.run([WX, "run", code, "--timeout", str(timeout)],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return (p.stdout or "").strip()


def main():
    cqf = load()
    quests = dump_quests(cqf)
    ids = sorted(quests)
    print("quests", len(ids))
    names = {}

    for start in range(0, len(ids), BATCH):
        part = ids[start:start + BATCH]
        body = ", ".join(str(x) for x in part)
        run("local ids={%s}; for i=1,#ids do C_QuestLog.RequestLoadQuestByID(ids[i]) end; return #ids" % body)
        time.sleep(1.2)
        out = run("local ids={%s}; local o={}; for i=1,#ids do local n=C_QuestLog.GetTitleForQuestID(ids[i]); if n and n~='' then o[#o+1]=ids[i]..'\\t'..n end end; return table.concat(o,'\\n')" % body)
        got = 0
        for line in out.splitlines():
            if "\t" not in line:
                continue
            a, b = line.split("\t", 1)
            a = a.strip()
            if a.isdigit():
                names[a] = b.strip()
                got += 1
        print("  batch %3d-%3d  got %d/%d" % (start, start + len(part) - 1, got, len(part)))

    path = os.path.join(ROOT, "_temp", "_cq_names.json")
    with io.open(path, "w", encoding="utf-8") as fh:
        json.dump(names, fh, ensure_ascii=False, indent=0, sort_keys=True)
    print("wrote", path, len(names), "/", len(ids))


if __name__ == "__main__":
    main()
