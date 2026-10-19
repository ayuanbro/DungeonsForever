# -*- coding: utf-8 -*-
# boss 钉图标恢复身份色（与文字同色）——静态断言 + 一条变异
import io


def rd(p):
    return io.open(p, encoding='utf-8', newline='').read()


def wr(p, s):
    io.open(p, 'w', encoding='utf-8', newline='').write(s)


def rep1(src, old, new, tag):
    n = src.count(old)
    assert n == 1, '%s: hit %d' % (tag, n)
    return src.replace(old, new, 1)


# ---------- 1) harness 静态断言 ----------
p = 'df_dungeon_check.py'
s = rd(p)
anchor = """ck('★★ ㊲b 贴图分派：任务 PIN_QUEST_TEX / 入口 PIN_DOOR_TEX / 物品 DG.ItemIcon(p.id) / 稀有银染色',"""
assert s.count(anchor) == 1
add = """ck('★★ ㊲b boss 钉图标 = 身份色（BossColor 先算、dot 与文字同色；2026-10-04 用户定——恒定金回退）',
   'local nm, cr, cg, cb' in _mui3_src
   and 'cr, cg, cb = M.BossColor(M.curId, p.en)' in _mui3_src
   and 'bt.dot:SetVertexColor(cr, cg, cb)' in _mui3_src
   and _mui3_src.find('cr, cg, cb = M.BossColor') < _mui3_src.find('bt.dot:SetVertexColor(cr, cg, cb)'))
"""
s = rep1(s, anchor, add + anchor, 'static boss color')
wr(p, s)
print('df_dungeon_check.py 静态断言已加')

# ---------- 2) 变异：dot 恒定金（身份色回退） ----------
p = 'df_mut_check.py'
s = rd(p)
i = s.find('\nMUTATIONS = [')
assert i > 0
end = s.find('\n]', i)
assert end > 0
mut = """    ('图钉扩展：boss 钉图标回退恒定金（身份色不再上 dot，图标与文字脱钩）',
     ('Core/MapUI.lua', (
         u8('                bt.dot:SetVertexColor(cr, cg, cb)\\n'),
         u8('                bt.dot:SetVertexColor(1, 0.82, 0) -- MUT: identity color wiped from dot\\n')))),
"""
s = s[:end] + mut + s[end:]
wr(p, s)
print('df_mut_check.py 变异已加')
