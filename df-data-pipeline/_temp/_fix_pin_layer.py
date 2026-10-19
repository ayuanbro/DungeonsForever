# -*- coding: utf-8 -*-
# 2026-10-04 图钉图层修复：图标(dot)必须盖过文字(nm)。
#   源侧改动：bt.nm 先建、bt.dot 后建且层 ARTWORK → OVERLAY。
#   本脚本：① harness 静态断言 +1；② 变异 +1（图层回退 ARTWORK）。
import io


def rd(p):
    return io.open(p, encoding='utf-8', newline='').read()


def wr(p, s):
    io.open(p, 'w', encoding='utf-8', newline='').write(s)


def rep1(src, old, new, tag):
    n = src.count(old)
    assert n == 1, '%s: anchor hit %d' % (tag, n)
    return src.replace(old, new, 1)


# ---------- ① 静态断言 ----------
p1 = 'df_dungeon_check.py'
s = rd(p1)
anchor = "ck('★★ ㊲b 贴图分派：任务 PIN_QUEST_TEX / 入口 PIN_DOOR_TEX / 物品 DG.ItemIcon(p.id) / 稀有银染色',"
assert s.count(anchor) == 1
# 锚点唯一性预检（针对源码串的断言写法）
mkfs = "bt.nm = MakeFS(bt, 14, C_GOLD, \"CENTER\")"
dotov = "bt.dot = bt:CreateTexture(nil, \"OVERLAY\")"
src = io.open('../Core/MapUI.lua', encoding='utf-8', newline='').read()
assert src.count(mkfs) == 1 and src.count(dotov) == 1, (src.count(mkfs), src.count(dotov))
new_ck = (
    "ck('★★ ㊲b 图钉图层：图标必须盖过文字（dot 提 OVERLAY + 文字先建，否则 14px 名字糊掉任务「!」等小材质）',\n"
    "   " + repr(dotov) + " in _mui3_src\n"
    "   and _mui3_src.find(" + repr(mkfs) + ") < _mui3_src.find(" + repr(dotov) + "))\n"
)
s = rep1(s, anchor, new_ck + anchor, 'static layer ck')
wr(p1, s)
print('df_dungeon_check.py: 图层静态断言 +1')

# ---------- ② 变异 +1 ----------
p2 = 'df_mut_check.py'
m = rd(p2)
tail_anchor = """    ('图钉扩展：开关文案退回旧「隐藏boss/显示boss」（改名回滚）',
     ('Core/MapUI.lua', (
         u8('    bt:SetText(off and L["显示图钉"] or L["隐藏图钉"])\\n'),
         u8('    bt:SetText(off and L["显示boss"] or L["隐藏boss"]) -- MUT: old label\\n')))),
]"""
assert m.count(tail_anchor) == 1, m.count(tail_anchor)
new_mut = """    ('图钉扩展：开关文案退回旧「隐藏boss/显示boss」（改名回滚）',
     ('Core/MapUI.lua', (
         u8('    bt:SetText(off and L["显示图钉"] or L["隐藏图钉"])\\n'),
         u8('    bt:SetText(off and L["显示boss"] or L["隐藏boss"]) -- MUT: old label\\n')))),
    ('图钉扩展：钉点图标图层回退（dot 回 ARTWORK，文字又糊到图标上）',
     ('Core/MapUI.lua', (
         u8('        bt.dot = bt:CreateTexture(nil, "OVERLAY")\\n'),
         u8('        bt.dot = bt:CreateTexture(nil, "ARTWORK") -- MUT: icon below text\\n')))),
]"""
m = rep1(m, tail_anchor, new_mut, 'mutation layer')
wr(p2, m)
print('df_mut_check.py: 图层回退变异 +1')
