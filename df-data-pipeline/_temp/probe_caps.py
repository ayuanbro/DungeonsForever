# -*- coding: utf-8 -*-
"""每周上限 + 军衔阶梯 确定性取证（锚点 count 断言，结果落盘 JSON）"""
import re, json, sys

SRC = r"D:/workspace/DungeonsForever/Core/Data/Data_PvPRanks.lua"
OUT = r"D:/workspace/DungeonsForever/_temp/probe_caps.json"

src = open(SRC, encoding="utf-8", errors="replace").read()

report = {"file": SRC, "len": len(src), "errors": []}

# --- 锚点 1：caps 表唯一 ---
n_caps_block = src.count("caps = {")
report["caps_block_count"] = n_caps_block
if n_caps_block != 1:
    report["errors"].append("caps block count != 1")

# --- 锚点 2：ranks 表唯一 ---
n_ranks_block = src.count("ranks = {")
report["ranks_block_count"] = n_ranks_block
if n_ranks_block != 1:
    report["errors"].append("ranks block count != 1")

# --- caps 逐条：[n] = { rank = X, cum = Y, inc = Z } ---
cap_pat = re.compile(r"\[(\d+)\]\s*=\s*\{\s*rank\s*=\s*(\d+),\s*cum\s*=\s*(\d+),\s*inc\s*=\s*(\d+)\s*\}")
caps = [{"week": int(a), "rank": int(b), "cum": int(c), "inc": int(d)}
        for a, b, c, d in cap_pat.findall(src)]
report["caps_entry_count"] = len(caps)
if len(caps) != 10:
    report["errors"].append("caps entries != 10")
if [c["week"] for c in caps] != list(range(1, 11)):
    report["errors"].append("caps weeks not 1..10")
if [c["rank"] for c in caps] != [3, 5, 6, 7, 8, 9, 11, 12, 13, 14]:
    report["errors"].append("caps rank sequence mismatch")
cums = [c["cum"] for c in caps]
if any(cums[i] >= cums[i + 1] for i in range(len(cums) - 1)):
    report["errors"].append("caps cum not strictly increasing")
report["caps"] = caps

# --- ranks 14 条：pts / cum / week ---
rank_pat = re.compile(
    r"\[(\d+)\]\s*=\s*\{\s*pts\s*=\s*(\d+),\s*cum\s*=\s*(\d+),\s*week\s*=\s*(\d+),"
    r".*?a\s*=\s*\{([^}]*)\},\s*h\s*=\s*\{([^}]*)\}", re.S)
ranks = []
for m in rank_pat.finditer(src[src.find("ranks = {"):]):
    ranks.append({
        "rank": int(m.group(1)), "pts": int(m.group(2)), "cum": int(m.group(3)),
        "week": int(m.group(4)),
        "a_n": len([x for x in m.group(5).split(",") if x.strip()]),
        "h_n": len([x for x in m.group(6).split(",") if x.strip()]),
    })
report["ranks_entry_count"] = len(ranks)
if len(ranks) != 14:
    report["errors"].append("ranks entries != 14")
rc = [r["cum"] for r in ranks]
if any(rc[i] >= rc[i + 1] for i in range(len(rc) - 1)):
    report["errors"].append("ranks cum not increasing")
report["ranks"] = ranks

report["OK"] = not report["errors"]
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=1)
print("WROTE", OUT, "OK=", report["OK"], "errors=", report["errors"])
