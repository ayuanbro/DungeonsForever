#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""扫描 _temp/*.py，建立「数据表 -> 脚本 -> 数据源」的对应关系。

判定规则：
  写入型：文件里出现 Data_Xxx.lua 且同文件有写操作（open(...,'w') / .write( )
  读取型：只出现 Data_Xxx.lua，没有写操作
  URL 源：抓取域名
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
RE_TABLE = re.compile(r"Data_([A-Za-z0-9]+)\.lua")
RE_WRITE = re.compile(r"""open\([^)]*['"][wa]b?['"]|\.write\(|dump\(|--apply|argparse""")
DOMAINS = {
    "wowhead": re.compile(r"wowhead\.com"),
    "wuxianwow": re.compile(r"wuxianwow\.com"),
    "foreverchanges": re.compile(r"foreverchanges\.pro"),
    "wago": re.compile(r"wago\.tools|wago\.io"),
    "questie": re.compile(r"questie", re.I),
    "wuxian-cli": re.compile(r"wuxian\.exe|wuxian\"|'wuxian'"),
    "local-client": re.compile(r"Interface/AddOns|_cn_beta_|_classic_beta_|ClassQuestsForever"),
}

writers = defaultdict(list)
readers = defaultdict(list)
sources = defaultdict(set)

for name in sorted(os.listdir(HERE)):
    if not name.endswith(".py"):
        continue
    path = os.path.join(HERE, name)
    try:
        s = io.open(path, encoding="utf-8", errors="ignore").read()
    except Exception:
        continue
    tabs = sorted(set(RE_TABLE.findall(s)))
    if not tabs:
        continue
    writes = bool(RE_WRITE.search(s))
    for d, rx in DOMAINS.items():
        if rx.search(s):
            sources[d].add(name)
    for t in tabs:
        (writers if writes else readers)[t].append(name)

rows = []
for f in TABLES:
    t = f[len("Data_"):-len(".lua")]
    rows.append({
        "table": f,
        "writers": writers.get(t, []),
        "readers": len(readers.get(t, [])),
    })

print("=== 数据表 <-> 脚本 ===")
no_writer = []
for r in rows:
    w = r["writers"]
    tag = "%d" % len(w) if w else "—"
    print("%-32s 写入脚本 %-3s %s" % (r["table"], tag, ", ".join(w[:4]) + (" ..." if len(w) > 4 else "")))
    if not w:
        no_writer.append(r["table"])

print("\n无写入脚本引用的表:", len(no_writer))
for t in no_writer:
    print("  " + t)

print("\n=== 数据源出现频次 ===")
for d in sorted(sources, key=lambda x: -len(sources[x])):
    print("%-16s %4d 个脚本" % (d, len(sources[d])))

out = os.path.join(HERE, "_data_source_index.json")
json.dump({"tables": rows, "sources": {k: sorted(v) for k, v in sources.items()}},
          io.open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\nwrote", out)
