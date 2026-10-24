# -*- coding: utf-8 -*-
"""交叉比对 MageBookTracker（SoD 法师找书，任务ID口径）与 Data_Explore.lua（物品ID口径）。
按坐标最近邻配对，报告距离、区域对，人工判读哪些本子两源一致、哪些有出入。"""
import re, json, math, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

TITAN = r"D:/workspace/DungeonsForever"
MBT = r"D:/Game/World of Warcraft/_classic_era_/Interface/AddOns/MageBookTracker/magebooktracker.lua"

# ---- 解析我们的 Data_Explore.lua ----
src = open(TITAN + "/Core/Data/Data_Explore.lua", encoding="utf-8").read()
ours = []
for m in re.finditer(r"\[(\d+)\] = \{ (\d+), (\d+), ([\d.]+), ([\d.]+),", src):
    idx, item, area, x, y = int(m.group(1)), int(m.group(2)), int(m.group(3)), float(m.group(4)), float(m.group(5))
    ours.append((idx, item, area, x, y))

# ---- 解析 MBT ----
mbt_src = open(MBT, encoding="utf-8").read()
mbt = []
for tbl in re.finditer(r"(?m)^(\w+) = \{(.*?)^\}", mbt_src, re.S):
    phase, body = tbl.group(1), tbl.group(2)
    for e in re.finditer(r"\[(\d+)\]=\{ \[\"x\"\] = ([\d.]+), \[\"y\"\] = ([\d.]+), (?:\[\"x2\"\] = ([\d.]+), \[\"y2\"\] = ([\d.]+), )?\[\"location\"\] = \"([^\"]*)\", \[\"name\"\] = \"([^\"]*)\" \}", body):
        qid, x, y, x2, y2, loc, name = (int(e.group(1)), float(e.group(2)), float(e.group(3)),
                                        e.group(4), e.group(5), e.group(6), e.group(7))
        mbt.append((qid, x, y, loc, name, phase))

print(f"我们的数据 {len(ours)} 本；MBT {len(mbt)} 本\n")

# ---- 最近邻配对（对每个 MBT 条目找我们最近的一条）----
report = []
for qid, x, y, loc, name, phase in mbt:
    best = min(ours, key=lambda o: (o[3]-x)**2 + (o[4]-y)**2)
    dist = math.hypot(best[3]-x, best[4]-y)
    report.append((dist, qid, name, loc, phase, best))

report.sort(reverse=True)  # 最可疑的排前面
print("=== 按距离降序（最可疑在前）===")
for dist, qid, name, loc, phase, best in report:
    flag = "OK " if dist < 1.0 else ("近 " if dist < 3.0 else "!! ")
    print(f"{flag} d={dist:5.2f}  MBT [{qid}] {name[:42]:<42} @ {loc:<24}"
          f"  <-> 我们#{best[0]:>2} item={best[1]} area={best[2]} ({best[3]},{best[4]})")
