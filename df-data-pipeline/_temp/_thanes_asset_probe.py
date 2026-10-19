#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""独立核查：客户端 listfile 里到底有没有「领主大厅 / Thanes」的副本内地图瓦片。
不依赖任何我们自己写的别名表 —— 纯看客户端全历史文件名清单。"""
import collections

P = r"D:/workspace/DungeonsForever/_temp/_community-listfile.csv"

dirs = collections.Counter()
wm_thanes = []
all_thanes = []

with open(P, "r", encoding="utf-8", errors="replace") as f:
    f.readline()
    for line in f:
        raw = line.strip().strip('"').lower()
        # 行格式： <filedataid>;<path>
        path = raw.split(";", 1)[1] if ";" in raw else raw
        if path.startswith("interface/worldmap/"):
            rest = path[len("interface/worldmap/"):]
            top = rest.split("/", 1)[0]
            if top:
                dirs[top] += 1
            if "thane" in path or "hallof" in path:
                wm_thanes.append(path)
        if "thane" in path:
            all_thanes.append(path)

print("== interface/worldmap 下目录总数:", len(dirs))
print()
print("== [重点] worldmap 里含 thane/hallof 的条目 ==")
for t in sorted(set(wm_thanes)):
    print("  ", t)
print("   命中条数:", len(wm_thanes))
print()
print("== 全清单里含 thane 的条目，按二级目录归类 ==")
cat = collections.Counter()
for t in all_thanes:
    parts = t.split("/")
    cat["/".join(parts[:2])] += 1
for k, v in sorted(cat.items()):
    print("   %-40s %4d" % (k, v))
print()
print("== 目录名全清单 ==")
for d in sorted(dirs):
    print("   %-36s %3d" % (d, dirs[d]))
