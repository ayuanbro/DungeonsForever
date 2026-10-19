# -*- coding: utf-8 -*-
"""两条旧钉点变异重锚到 R5 新代码（SyncPins 渲染段被 2026-10-04 图钉扩展改写）。"""
import io

def rd(p):
    return io.open(p, encoding='utf-8', newline='').read()

def wr(p, s):
    io.open(p, 'w', encoding='utf-8', newline='').write(s)

def rep1(src, old, new, tag):
    n = src.count(old)
    assert n == 1, '%s: anchor hit %d' % (tag, n)
    return src.replace(old, new, 1)

p2 = 'df_mut_check.py'
m = rd(p2)

old1 = (
    "MUT_PIN_ALL_LAYERS = ('Core/MapUI.lua', (\n"
    "    b'        list = M.PinsFor(M.curId, M.FloorNumAt(M.curId, M.curLayer or 1))\\n',\n"
    "    b'        list = M.PinsFor(M.curId) -- MUT: every floor\\'s pins on this layer\\n'))"
)
new1 = (
    "MUT_PIN_ALL_LAYERS = ('Core/MapUI.lua', (\n"
    "    b'        list = M.PinsFor(M.curId, floor)\\n',\n"
    "    b'        list = M.PinsFor(M.curId) -- MUT: every floor\\'s pins on this layer\\n'))"
)
m = rep1(m, old1, new1, 'MUT_PIN_ALL_LAYERS')

old2 = (
    "MUT_PIN_COLOR_SAME = ('Core/MapUI.lua', (\n"
    "    b'            local cr, cg, cb = M.BossColor(M.curId, p.en)\\n'\n"
    "    b'            bt.dot:SetVertexColor(cr, cg, cb)\\n'\n"
    "    b'            bt.nm:SetTextColor(cr, cg, cb)\\n',\n"
    "    b'            local cr, cg, cb = 1, 1, 1 -- MUT: identity colors wiped\\n'\n"
    "    b'            bt.dot:SetVertexColor(cr, cg, cb)\\n'\n"
    "    b'            bt.nm:SetTextColor(cr, cg, cb)\\n'))"
)
new2 = (
    "MUT_PIN_COLOR_SAME = ('Core/MapUI.lua', (\n"
    "    b'                cr, cg, cb = M.BossColor(M.curId, p.en)\\n',\n"
    "    b'                cr, cg, cb = 1, 1, 1 -- MUT: identity colors wiped\\n'))"
)
m = rep1(m, old2, new2, 'MUT_PIN_COLOR_SAME')

wr(p2, m)
print('两条旧变异重锚完成')
