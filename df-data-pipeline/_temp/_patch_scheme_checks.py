# -*- coding: utf-8 -*-
# 2026-10-10：自动路线方案化 check/mut 补丁（自适应行尾）
def load(p):
    return open(p, "rb").read()

def save(p, b):
    open(p, "wb").write(b)

def rep1(data, old, new, tag):
    for o in (old.encode("utf-8"), old.encode("utf-8").replace(b"\n", b"\r\n")):
        n = new.encode("utf-8")
        if o != old.encode("utf-8"):
            n = new.encode("utf-8").replace(b"\n", b"\r\n")
        c = data.count(o)
        if c == 1:
            return data.replace(o, n)
    raise AssertionError("%s: anchor not found: %r" % (tag, old[:70]))


# ---- df_dungeon_check.py：4 条静态断言 ----
p1 = r"D:/workspace/DungeonsForever/_temp/df_dungeon_check.py"
d = load(p1)
anchor1 = """    ck('★ 名字到货打 __named 标记（重扫只扫没标记的卡，否则每轮白刷）',
       _dui.count('c.__named = hasName') == 4)
"""
assert d.count(anchor1.encode("utf-8")) + d.count(anchor1.replace("\n", "\r\n").encode("utf-8")) == 1
add1 = """    # ---- ★★ 2026-10-10 自动路线方案化（用户：默认最省钱；方案卡第二位）----
    ck('★★ 自动路线方案化：四方案/标签/Compute 兜底最省钱/缓存键含 scheme/结果带 scheme',
       "'cheapest', 'matcost', 'crafts', 'optim'" in profra
       and 'function RA.SchemeOrder' in profra
       and 'if scheme == nil or not SCHEME_LABEL[scheme] then scheme = "cheapest" end' in profra
       and 'tostring(opts.scheme)' in profra
       and profra.count('        scheme = scheme,\\n') >= 1)
    ck('★★ 最省钱指标计入图纸价（已学免费/取不到按 0）；乐观计数提前学习线+收益恒 1+排冷却/未公开',
       'local fcost = MatPrice(f[1], soldSet) or 0' in profra
       and 'if scheme == "cheapest" then return (c.cost + (c.fcost or 0)) / g end' in profra
       and 'if scheme == "optim" then return 1 end' in profra
       and 'math.max(1, math.min(learn, cY - 25))' in profra
       and profra.count('c.cd or c.unknown') >= 2
       and profra.count('(c.learnO or c.learn)') >= 3
       and 'if c then st.cost = (c.base or 0) * (st[4] or 0) end' in profra)
    ck('★★ 升级页方案卡第二位 + 五卡均分 + 点击循环切换',
       profui.count('{ key = "scheme", w = 150 },') == 1
       and '"mode", "scheme", "cost", "target", "snap"' in profui
       and '4 * PD.LV_TILE_GAP' in profui
       and 'math.floor(usable / 5)' in profui
       and 'ProfDB().autoScheme = order[ni]' in profui)
    ck('★ 方案默认最省钱 + 乐观计数不依赖价格插件（页面与 HUD 门槛都放宽）',
       'PD.SETTING_DEF.autoScheme = "cheapest"' in profui
       and 'scheme ~= "optim"' in profui
       and '(scheme == "optim" or RA.Available())' in profui
       and pfhud.count('scheme == "optim"') >= 2
       and 'PD.Setting("autoScheme")' in pfhud)
"""
d = rep1(d, anchor1, anchor1 + add1, "harness")
save(p1, d)

# ---- df_mut_check.py：4 条变异 + 注册 ----
p2 = r"D:/workspace/DungeonsForever/_temp/df_mut_check.py"
d = load(p2)
anchor2 = """MUT_PROF_QSEG_GONE = ('Core/ProfessionUI.lua', (
    '            if q then scol = { DG.QColor(q) } end'.encode('utf-8'),
    '            scol = col -- MUT: material quality color gone'.encode('utf-8')))
"""
add2 = anchor2 + """
# 2026-10-10 自动路线方案化（默认最省钱 + 方案卡）
MUT_PROF_SCHEME_DEF_GONE = ('Core/ProfessionUI.lua', (
    'PD.SETTING_DEF.autoScheme = "cheapest"'.encode('utf-8'),
    'PD.SETTING_DEF.autoScheme = "matcost" -- MUT: scheme default regressed'.encode('utf-8')))
MUT_PROF_SCHEME_TILE_GONE = ('Core/ProfessionUI.lua', (
    '{ key = "scheme", w = 150 },'.encode('utf-8'),
    '{ }, -- MUT: scheme tile gone'.encode('utf-8')))
MUT_PROF_FCHEAP_GONE = ('Core/ProfRouteAuto.lua', (
    'if scheme == "cheapest" then return (c.cost + (c.fcost or 0)) / g end'.encode('utf-8'),
    'if scheme == "cheapest" then return c.cost / g end -- MUT: formula price dropped'.encode('utf-8')))
MUT_PROF_OPTIM_GAIN_GONE = ('Core/ProfRouteAuto.lua', (
    'if scheme == "optim" then return 1 end'.encode('utf-8'),
    'if false then return 1 end -- MUT: optimistic gain gone'.encode('utf-8')))
"""
d = rep1(d, anchor2, add2, "mut defs")
anchor3 = "    ('专业页：材料段品质色断开', MUT_PROF_QSEG_GONE),\n"
add3 = anchor3 + """    ('专业页：路线方案默认回潮材料成本', MUT_PROF_SCHEME_DEF_GONE),
    ('专业页：路线方案卡消失', MUT_PROF_SCHEME_TILE_GONE),
    ('自动路线：最省钱指标丢图纸价', MUT_PROF_FCHEAP_GONE),
    ('自动路线：乐观计数收益回潮概率口径', MUT_PROF_OPTIM_GAIN_GONE),
"""
d = rep1(d, anchor3, add3, "mut reg")
save(p2, d)
print("check/mut scheme patch OK")
