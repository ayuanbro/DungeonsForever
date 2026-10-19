#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""精确扫描：谁真正以写模式打开某张 Data_*.lua。

判据（三者任一）：
  A. 同一行里出现 Data_X.lua 且出现 'w' / "w" / newline=  / .write(
  B. OUT/DST/TARGET/PATH 变量 = 含 Data_X.lua
  C. 文件里 Data_X.lua 出现后 300 字符内出现 open( 或 io.open( 且带写模式
"""
import io
import json
import os
import re
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "Core", "Data")
TABLES = sorted(f for f in os.listdir(DATA) if f.startswith("Data_") and f.endswith(".lua"))

OUTVAR = re.compile(r"^(?:OUT|DST|TARGET|DEST|PATH|LUA|OUTFILE|FILE)\s*=\s*.{0,200}?Data_(\w+)\.lua", re.M)
LINE_WRITE = re.compile(r"Data_(\w+)\.lua[^\n]{0,200}?(?:['\"]w['\"]|newline=|\.write\()|(?:['\"]w['\"]|newline=|\.write\()[^\n]{0,200}?Data_(\w+)\.lua")

writers = defaultdict(list)
for name in sorted(os.listdir(HERE)):
    if not name.endswith(".py"):
        continue
    try:
        s = io.open(os.path.join(HERE, name), encoding="utf-8", errors="ignore").read()
    except Exception:
        continue
    hit = set(OUTVAR.findall(s))
    for a, b in LINE_WRITE.findall(s):
        if a:
            hit.add(a)
        if b:
            hit.add(b)
    for t in hit:
        writers[t].append(name)

print("%-32s %-4s %s" % ("数据表", "脚本", "生成脚本"))
print("-" * 110)
for f in TABLES:
    t = f[len("Data_"):-len(".lua")]
    w = writers.get(t, [])
    print("%-32s %-4d %s" % (f, len(w), ", ".join(w[:5]) + (" ..." if len(w) > 5 else "")))

missing = [f for f in TABLES if not writers.get(f[len("Data_"):-len(".lua")])]
print("\n无精确写入者: %d" % len(missing))
for m in missing:
    print("  " + m)

json.dump({k: v for k, v in writers.items()},
          io.open(os.path.join(HERE, "_data_writers.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\nwrote _data_writers.json")
