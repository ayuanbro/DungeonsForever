# -*- coding: utf-8 -*-
"""探针：升级分段行的「区间 / 配方名 / 材料 / 次数」四列到底需要多宽？

背景（用户 2026-09-24）：升级页左栏材料列显示不全（末尾「…」），同时名称与材料之间留白过多。
要定列宽就得先知道**真实需要多少**：
  · 区间宽（决定 PD.LV_NAME_X）
  · 配方名宽（决定 PD.LV_NAME_W —— 本次要改成「按本页最长名现算」，故需确认最长名有多长）
  · 材料串宽（决定 PD.LV_MAT_W —— 用 PD.MatCol 的**分块**口径算：数量 + 图标 16px + 物品名）
  · 次数宽（决定 PD.LV_CNT_W）

口径与插件一致：PD.TextW = 每个 CJK 记 1 * fs、每个 ASCII 记 0.55 * fs。
★ 离线拿不到真实客户端物品名 → 用桩里的占位名「暂时没有客户端数据」（8 个 CJK = 104px）
   当**上界**来量：真实中文物品名极少超过 8 字，所以离线量出来的是保守值。
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

FS = 13          # PD.LV_FS
ICON = 16        # PD.MAT_ICON_PX
GAP = 10         # PD.MatCol 块间距
STUB = "暂时没有客户端数据"      # 桩里的占位物品名（保守上界）


def textw(s):
    w = 0
    for ch in s:
        w += FS if ord(ch) > 0x7F else FS * 0.55
    return w


def matw(mats):
    """PD.MatCol 的分块口径：块 = 「N×」+ 图标 + 名字。"""
    w = 0
    for i, m in enumerate(mats):
        w += (0 if i == 0 else GAP)
        w += textw("%d×" % (m[1] or 1)) + ICON + textw(STUB)
    return w


print("prof            段  区间W  最长名W  次数W  材料串宽(最大/中位)  材料种数分布")
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
    rngw, namew, cntw = 0, 0, 0
    mw, dist = [], {}
    for st in steps.values():
        w = textw("%s → %s" % (st[1], st[2]))
        rngw = max(rngw, w)
        nw = textw("法术 #%d" % st[3])      # 离线拿不到法术名 → 用它上界
        namew = max(namew, nw)
        cntw = max(cntw, textw("~%s 次制作" % st[4]))
        mats = have.get(st[3]) or []
        mw.append(matw(list(mats.values()) if hasattr(mats, "values") else mats))
        k = len(mats)
        dist[k] = dist.get(k, 0) + 1
    mw.sort()
    n = len(mw)
    print("%-14s %3d %6.1f %8.1f %6.1f %10.1f /%9.1f  %s"
          % (slug, n, rngw, namew, cntw, mw[-1], mw[n // 2],
             ",".join("%d种×%d" % (k, dist[k]) for k in sorted(dist))))
