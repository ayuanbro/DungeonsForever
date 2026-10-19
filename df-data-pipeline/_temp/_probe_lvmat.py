# -*- coding: utf-8 -*-
"""探针：升级分段行的「配方法术ID → 材料」到底能对上几条？

背景：升级页分段行要显示本段材料（走 `spells[st[3]] = r[12]`，法术 ID → reagents）。
若某些分段的法术 ID 在配方表里查不到（法术没对上 / 该配方没抓），行内材料就会是空的 ——
这时断言写「每段都有材料」就是**恒假**（每条变异都能让它红，等于白测），必须先量清楚真值。
"""
import os
import sys

import lupa

DF = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
L = lupa.LuaRuntime(unpack_returned_tuples=True)
L.execute("""
function load_data(path, ns)
    local f = assert(loadfile(path))
    f("DungeonsForever", ns)
end
""")
loader = L.globals().load_data

LV, REC = L.table(), L.table()
loader(os.path.join(DF, "Core", "Data", "Data_ProfLeveling.lua"), LV)
loader(os.path.join(DF, "Core", "Data", "Data_ProfRecipes.lua"), REC)

lv_all = LV["ProfLeveling"]
rec_all = REC["ProfRecipes"]
if not lv_all or not rec_all:
    sys.exit("数据表没加载上（ns 里的键名变了？）")

for slug in sorted(lv_all.keys()):
    lv = lv_all[slug]
    steps = lv["steps"]
    if steps is None or len(steps) == 0:
        continue
    rec = rec_all[slug]
    have = {}
    if rec is not None and rec["rows"] is not None:
        for r in rec["rows"].values():
            if r is not None and r[12] is not None:
                have[r[1]] = r[12]
    miss = []
    for st in steps.values():
        if st[3] not in have:
            miss.append((st[1], st[2], st[3]))
    print("%-16s 分段 %2d 条 / 有材料 %2d 条 / 缺 %2d 条  %s"
          % (slug, len(steps), len(steps) - len(miss), len(miss),
             "" if not miss else "缺:" + ",".join(str(m[2]) for m in miss[:8])))
