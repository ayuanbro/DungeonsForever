# -*- coding: utf-8 -*-
# 2026-10-04 图层断言升级：旧断言查 'bt.nm = MakeFS(bt, …)' 已不在源码里（find=-1 假绿）。
#   换新口径：pinText 低层文字容器先建 + nm 挂 pinText + 隐藏循环清文字；变异 +1（挂回按钮本体）。
import io


def rd(p):
    return io.open(p, encoding='utf-8', newline='').read()


def wr(p, s):
    io.open(p, 'w', encoding='utf-8', newline='').write(s)


def rep1(src, old, new, tag):
    n = src.count(old)
    assert n == 1, '%s: anchor hit %d' % (tag, n)
    return src.replace(old, new, 1)


# ---------- ① 静态断言换新口径 ----------
p1 = 'df_dungeon_check.py'
s = rd(p1)
old_ck = """ck('★★ ㊲b 图钉图层：图标必须盖过文字（dot 提 OVERLAY + 文字先建，否则 14px 名字糊掉任务「!」等小材质）',
   'bt.dot = bt:CreateTexture(nil, "OVERLAY")' in _mui3_src
   and _mui3_src.find('bt.nm = MakeFS(bt, 14, C_GOLD, "CENTER")') < _mui3_src.find('bt.dot = bt:CreateTexture(nil, "OVERLAY")'))"""
assert s.count(old_ck) == 1, s.count(old_ck)
new_ck = """ck('★★ ㊲b 图钉图层（第二轮）：全部钉文字挂先建的低层容器 pinText + dot 提 OVERLAY —— 图标压过全部文字（含跨钉）',
   'local pinText = CreateFrame("Frame", nil, pins)' in _mui3_src
   and 'bt.nm = MakeFS(pinText, 14, C_GOLD, "CENTER")' in _mui3_src
   and _mui3_src.find('local pinText = CreateFrame') < _mui3_src.find('for i = 1, M.MAX_PINS do')
   and 'bt.dot = bt:CreateTexture(nil, "OVERLAY")' in _mui3_src
   and 'nm:SetText("")' in _mui3_src)"""
s = rep1(s, old_ck, new_ck, 'layer ck v2')
wr(p1, s)
print('df_dungeon_check.py: 图层断言换新口径')

# ---------- ② 变异 +1 ----------
p2 = 'df_mut_check.py'
m = rd(p2)
tail = """    ('图钉扩展：钉点图标图层回退（dot 回 ARTWORK，文字又糊到图标上）',
     ('Core/MapUI.lua', (
         u8('        bt.dot = bt:CreateTexture(nil, "OVERLAY")\\n'),
         u8('        bt.dot = bt:CreateTexture(nil, "ARTWORK") -- MUT: icon below text\\n')))),
]"""
assert m.count(tail) == 1, m.count(tail)
new_tail = """    ('图钉扩展：钉点图标图层回退（dot 回 ARTWORK，文字又糊到图标上）',
     ('Core/MapUI.lua', (
         u8('        bt.dot = bt:CreateTexture(nil, "OVERLAY")\\n'),
         u8('        bt.dot = bt:CreateTexture(nil, "ARTWORK") -- MUT: icon below text\\n')))),
    ('图钉扩展：名字挂回按钮本体（弃文字层，跨钉文字又压过隔壁钉图标）',
     ('Core/MapUI.lua', (
         u8('        bt.nm = MakeFS(pinText, 14, C_GOLD, "CENTER") -- 挂文字层：图标永远盖得住（跨钉也是）\\n'),
         u8('        bt.nm = MakeFS(bt, 14, C_GOLD, "CENTER") -- MUT: name back on button\\n')))),
]"""
m = rep1(m, tail, new_tail, 'mutation name layer')
wr(p2, m)
print('df_mut_check.py: 挂回按钮变异 +1')
