# -*- coding: utf-8 -*-
"""确定性取证：Data_PvPHonor.lua 每周上限字段（禁凭回显猜）"""
import io, re, sys, json, os

PATH = r"D:/workspace/DungeonsForever/Core/Data/Data_PvPHonor.lua"
out = io.StringIO()

def p(*a):
    print(*a, file=out)

if not os.path.isfile(PATH):
    p("MISSING_FILE", PATH)
    sys.stdout.write(out.getvalue())
    sys.exit(2)

src = open(PATH, encoding="utf-8", errors="replace").read()
p("FILE_LEN", len(src))

# 1) 锚点断言：文件确实包含每周上限表
assert "ns.PvPHonorData" in src or "ns.PvPRankData" in src, "no honor data table"
p("HAS_NS_TABLE", True)

# 2) 抓 weekly/caps 相关行（限 40 行，防刷屏）
hits = []
for i, line in enumerate(src.splitlines(), 1):
    if re.search(r"weekly|weekCap|cap\b|上限|honor", line, re.I):
        hits.append((i, line.strip()[:120]))
p("HIT_LINES", len(hits))
for i, l in hits[:40]:
    p(f"L{i}", l)

res = out.getvalue()
sys.stdout.write(res)
with open(r"D:/workspace/DungeonsForever/_temp/probe_honor_out.txt", "w", encoding="utf-8") as f:
    f.write(res)
