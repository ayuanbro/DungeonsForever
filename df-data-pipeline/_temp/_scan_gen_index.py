#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""按脚本头部 docstring 建立「生成器 -> 读写对象」索引。

只用 docstring，不猜代码，所以准确。
"""
import io
import json
import os
import re
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
RE_READ = re.compile(r"^\s*(?:读|输入|读取|来源|Source|Read)\s*[:：]\s*(.+)$", re.M)
RE_WRITE = re.compile(r"^\s*(?:写|输出|生成|Output|Write)\s*[:：]\s*(.+)$", re.M)
RE_USAGE = re.compile(r"^\s*(?:用法|用法示例|Usage)\s*[:：]?\s*(.+)$", re.M)
RE_DATA = re.compile(r"Data_(\w+)\.lua")
RE_URL = re.compile(r"(?:https?://)?([a-z0-9.-]+\.(?:com|pro|io|net|tools))", re.I)

GEN_PAT = re.compile(r"^(gen_|fc_|_fc_|_cq_|_route_|_wh_|_df_wh|build_|_build_|make_|explore_gen|clean_comments|prof_|patch_)")

rows = []
for name in sorted(os.listdir(HERE)):
    if not name.endswith(".py") or not GEN_PAT.match(name):
        continue
    try:
        src = io.open(os.path.join(HERE, name), encoding="utf-8", errors="ignore").read()
    except Exception:
        continue
    head = src[:4000]
    doc = ""
    m = re.search(r'^\s*(?:"""|\'\'\')(.*?)(?:"""|\'\'\')', head, re.S)
    if m:
        doc = m.group(1)
    reads = [x.strip() for x in RE_READ.findall(doc)]
    writes = [x.strip() for x in RE_WRITE.findall(doc)]
    usage = [x.strip() for x in RE_USAGE.findall(doc)]
    tables = sorted(set(RE_DATA.findall(src)))
    urls = sorted({u.lower() for u in RE_URL.findall(head)})
    if not (reads or writes or tables or urls):
        continue
    rows.append({
        "file": name,
        "reads": reads,
        "writes": writes,
        "usage": usage[:2],
        "tables": tables,
        "urls": urls,
        "has_doc": bool(doc),
    })

with_doc = [r for r in rows if r["has_doc"]]
print("候选脚本 %d，其中有 docstring %d\n" % (len(rows), len(with_doc)))

by_table = defaultdict(list)
for r in rows:
    for t in r["tables"]:
        by_table[t].append(r["file"])

print("=== 每张表被哪些生成器脚本提到 ===")
for t in sorted(by_table):
    print("%-30s %s" % (t, ", ".join(sorted(by_table[t])[:6])))

print("\n=== 有 docstring 且声明了读/写的脚本 ===")
for r in with_doc:
    if r["reads"] or r["writes"]:
        print(r["file"])
        for x in r["reads"]:
            print("   读:", x[:110])
        for x in r["writes"]:
            print("   写:", x[:110])

json.dump(rows, io.open(os.path.join(HERE, "_gen_index.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\nwrote _gen_index.json  (%d 条)" % len(rows))
