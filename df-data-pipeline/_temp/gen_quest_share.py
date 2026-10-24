# -*- coding: utf-8 -*-
"""生成 ns.DungeonQuestShare（副本任务「可共享」标志表）→ 追加进
Core/Data/Data_DungeonQuests.lua（纯 ID，无本地化文案，覆盖层不受影响）。

数据源：QuestieDB-Forever.toc 的 Quest 标量行（字段 23 = questFlags），
        bit 0x08 = QUEST_FLAGS_SHARABLE。字段缺失记 0（不可共享）。
输出：只列本插件任务表里出现过的、且带该标志的任务 ID。
用法：python gen_quest_share.py
"""
import base64
import io
import os
import re
import sys

import cbor2

HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(HERE)
TOC = os.path.join(HERE, "questie", "forever", "QuestieDB", "QuestieDB_Forever.toc")
DATA = os.path.join(DF, "Core", "Data", "Data_DungeonQuests.lua")

SHARABLE = 0x08
LINE = re.compile(r"^## X-Quest-(\d+)-S:\s*(\S+)\s*$", re.M)
ROWID = re.compile(r"^        \{ (\d+), ", re.M)
BLOCK = re.compile(r"\n\nns\.DungeonQuestShare = \{.*?\n\}\n?$", re.S)


def quest_flags():
    txt = io.open(TOC, encoding="utf-8", errors="replace").read()
    out = {}
    for m in LINE.finditer(txt):
        qid = int(m.group(1))
        try:
            row = cbor2.loads(base64.b64decode(m.group(2)))
        except Exception:
            continue
        if not isinstance(row, dict):
            continue
        v = None
        for k, val in row.items():
            kk = int(k) if isinstance(k, bytes) and k.isdigit() else k
            if kk == 23 and isinstance(val, int):
                v = val
                break
        out[qid] = v or 0
    return out


def main():
    raw = io.open(DATA, "rb").read()
    txt = raw.decode("utf-8")
    assert "\r\n" in txt, "主数据文件应为 CRLF"

    ids = sorted(set(int(x) for x in ROWID.findall(txt)))
    flags = quest_flags()
    sharable = [i for i in ids if flags.get(i, 0) & SHARABLE]

    lines = ["ns.DungeonQuestShare = {"]
    row = []
    for i, qid in enumerate(sharable, 1):
        row.append("[%d] = true," % qid)
        if len(row) == 8:
            lines.append("    " + " ".join(row))
            row = []
    if row:
        lines.append("    " + " ".join(row))
    lines.append("}")
    block = "\r\n".join(lines)

    m = BLOCK.search(txt)
    if m:
        txt = txt[:m.start()]
    txt = txt.rstrip("\r\n") + "\r\n\r\n" + block + "\r\n"

    io.open(DATA, "wb").write(txt.encode("utf-8"))
    print("任务行 %d，可共享 %d（%.0f%%）" % (len(ids), len(sharable), 100.0 * len(sharable) / max(1, len(ids))))
    print("缺失数据（不可共享）%d" % (len(ids) - len(sharable)))


if __name__ == "__main__":
    sys.exit(main())
