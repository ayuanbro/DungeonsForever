# -*- coding: utf-8 -*-
"""探针：升级页每段的「来源」到底能不能查出来？能查出来的有哪几类？

背景（用户 2026-09-24 十二轮）：用户要求分段行改成**两行**，第二行要显示
「这个配方是向训练师学的、还是要买图纸」。但界面上现在**根本没有**这类文案
（grep「训练师」= 0 命中），所以先得确认数据层给不给得出。

配方行字段（见 Data_ProfRecipes.lua 头注释）：
  r[1] spell / r[7] learn / r[12] reagents / r[13] formula={图纸ID,品质} / r[14] source={skill,read,drops,vendors}
判定口径（本探针与将要落地的 UI 一致）：
  · formula == nil 且 source 无 drops/vendors  → 训练师直学（技能 N 可学）
  · formula ~= nil 且有 drops                   → 图纸来自掉落
  · formula ~= nil 且有 vendors                 → 图纸来自商人
  · formula ~= nil 但 source 空                 → 只知道「需要图纸」，出处不可读
  · steps 里的 spell 在配方表里查不到            → 无法判定（附魔就是这一类）
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


def is_empty(t):
    if not t:
        return True
    try:
        return len(list(t.values())) == 0
    except Exception:
        return True


def kind_of(row, has_row):
    if not has_row:
        return "查不到"
    formula = row[13]
    src = row[14]
    drops = (src and src["drops"]) if src else None
    vendors = (src and src["vendors"]) if src else None
    has_drop = not is_empty(drops)
    has_vend = not is_empty(vendors)
    if not formula:
        return "训练师直学" if not (has_drop or has_vend) else "无图纸但有出处?"
    if has_drop and has_vend:
        return "图纸=掉落+商人"
    if has_drop:
        return "图纸=掉落"
    if has_vend:
        return "图纸=商人"
    return "图纸(出处不可读)"


print("prof            段   来源分类")
tally_all = {}
for slug in sorted(lv_all.keys()):
    lv = lv_all[slug]
    steps = lv["steps"]
    if not steps or len(steps) == 0:
        continue
    rec = rec_all[slug]
    by_spell = {}
    if rec is not None and rec["rows"] is not None:
        for r in rec["rows"].values():
            if r is not None:
                by_spell[r[1]] = r
    tally = {}
    for st in steps.values():
        row = by_spell.get(st[3])
        k = kind_of(row, row is not None)
        tally[k] = tally.get(k, 0) + 1
        tally_all[k] = tally_all.get(k, 0) + 1
    print("%-14s %3d   %s" % (slug, len(steps),
                              "  ".join("%s×%d" % (k, v) for k, v in sorted(tally.items()))))

print("\n=== 合计 ===")
for k, v in sorted(tally_all.items(), key=lambda kv: -kv[1]):
    print("  %-18s %d" % (k, v))

# ── 抽几个「训练师直学」与「图纸=掉落」的样本看看源文本会长什么样 ──
print("\n=== 样本（用于预估第二行宽度）===")
shown = {"训练师直学": 0, "图纸=掉落": 0, "图纸=商人": 0, "图纸(出处不可读)": 0}
for slug in sorted(lv_all.keys()):
    lv = lv_all[slug]
    steps = lv["steps"]
    if not steps:
        continue
    rec = rec_all[slug]
    by_spell = {}
    if rec is not None and rec["rows"] is not None:
        for r in rec["rows"].values():
            if r is not None:
                by_spell[r[1]] = r
    for st in steps.values():
        row = by_spell.get(st[3])
        k = kind_of(row, row is not None)
        if k in shown and shown[k] < 3:
            shown[k] += 1
            f = row[13] if row else None
            s = row[14] if row else None
            dr = []
            if s and s["drops"]:
                for d in s["drops"].values():
                    dr.append("%s@%s" % (d["npc"], d["zone"]))
            ve = []
            if s and s["vendors"]:
                for v in s["vendors"].values():
                    ve.append("%s@%s" % (v["name"], v["zone"]))
            print("[%s] %s spell=%s learn=%s 图纸=%s 掉落=%s 商人=%s"
                  % (k, slug, st[3], row[7] if row else "-",
                     ("%s(品质%s)" % (f[1], f[2])) if f else "-",
                     "; ".join(dr) or "-", "; ".join(ve) or "-"))
