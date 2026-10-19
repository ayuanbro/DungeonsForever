#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""盘点：我们要用的那些 worldmap 目录，每个到底有几『层』。

判据：目录内文件名去掉尾部数字后的「前缀」= 一层。
  例 ragefire1_1..12  ⇒ 前缀 ragefire1_  = 1 层
     scholomance1_1..12 + scholomance2_1..12 ⇒ 2 层
"""
import collections
import re

P = r"D:/workspace/DungeonsForever/_temp/_community-listfile.csv"

# 看哪些目录（小写）
WANT = [
    "ragefire", "wailingcaverns", "thedeadmines", "shadowfangkeep", "blackfathomdeeps",
    "thestockade", "gnomeregan", "razorfenkraul", "razorfendowns", "scarlethalls",
    "scarletmonasteryold", "scarletmonastery", "uldaman", "uldaman_upres", "zulfarrak",
    "maraudon", "thetempleofatalhakkar", "blackrockdepths", "diremaul", "blackrockspire",
    "upperblackrockspire", "scholomanceold", "scholomance", "stratholme", "dalaran",
    "oldironforge", "ironforge", "ironforge_c60", "wetlands", "wetlands_c60",
    "tirisfal_c60", "ruinsoflordaeronscenario", "lordaerongarrison",
]

tbl = collections.defaultdict(set)   # dir -> set(文件名)

with open(P, "r", encoding="utf-8", errors="replace") as f:
    f.readline()
    for line in f:
        raw = line.strip().strip('"').lower()
        path = raw.split(";", 1)[1] if ";" in raw else raw
        if not path.startswith("interface/worldmap/"):
            continue
        rest = path[len("interface/worldmap/"):]
        parts = rest.split("/")
        if len(parts) < 2:
            continue
        top, fname = parts[0], parts[-1]
        if top in WANT:
            tbl[top].add(fname)

for top in WANT:
    files = tbl.get(top)
    if not files:
        print("== %-28s  (无)" % top)
        continue
    groups = collections.defaultdict(list)
    other = []
    for fn in files:
        m = re.match(r"^(.*?)(\d+)\.blp$", fn)
        if m:
            groups[m.group(1)].append(int(m.group(2)))
        else:
            other.append(fn)
    print("== %-28s 文件 %d 个 · 层前缀 %d 个" % (top, len(files), len(groups)))
    for pref, nums in sorted(groups.items()):
        nums.sort()
        rng = "%d..%d" % (nums[0], nums[-1]) if len(nums) > 1 else str(nums[0])
        flag = "   <== 层" if len(nums) >= 8 else ""
        print("     %-38s %2d 块  (%s)%s" % (pref, len(nums), rng, flag))
    if other:
        print("     其他:", " ".join(sorted(other))[:120])
