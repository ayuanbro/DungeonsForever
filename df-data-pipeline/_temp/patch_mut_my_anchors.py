# -*- coding: utf-8 -*-
"""重锚两条「属我」的变异：MUT_PROF_READ_BACK / MUT_PROF_MATCOL_BACK。

背景：
  · PD.SourceText 被拆成 PD.SourceParts（返回 {text=...} 数组）后，
    MUT_PROF_READ_BACK 的 old（`t[#t + 1] = ...`）在源码里消失。
  · RecipeSpec 的 mats 被惰性化到 PD.FitRecipeCols（2026-10-09 并发改动）后，
    MUT_PROF_MATCOL_BACK 的 old（`mats = mcol,`）在源码里消失。

本脚本同时改：
  ① 成品 df_mut_check.py（立即生效）
  ② 生成器 mk_df_mut.py 中对应的字面量（保持重跑一致）
"""
import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# ─────────────────────────── df_mut_check.py（成品）─────────────────────────
DFF = os.path.join(HERE, 'df_mut_check.py')
t = io.open(DFF, encoding='utf-8', newline='').read()

OLD1 = '''MUT_PROF_READ_BACK = ('Core/ProfessionUI.lua', (
    b'    if s.drops and #s.drops > 0 then t[#t + 1] = format(L["\\xe6\\x8e\\x89\\xe8\\x90\\xbd %d \\xe5\\xa4\\x84"], #s.drops) end\\n',
    b'    if s.read then t[#t + 1] = format(L["\\xe8\\xaf\\xbb\\xe7\\x89\\xa9\\xef\\xbc\\x9a%s"], tostring(s.read)) end -- MUT: read back\\n    if s.drops and #s.drops > 0 then t[#t + 1] = format(L["\\xe6\\x8e\\x89\\xe8\\x90\\xbd %d \\xe5\\xa4\\x84"], #s.drops) end\\n'))
'''

NEW1 = '''MUT_PROF_READ_BACK = ('Core/ProfessionUI.lua', (
    b'    if s.drops and #s.drops > 0 then\\n        out[#out + 1] = { text = format(L["\\xe6\\x8e\\x89\\xe8\\x90\\xbd %d \\xe5\\xa4\\x84"], #s.drops) }\\n    end\\n',
    b'    if s.read then out[#out + 1] = { text = format(L["\\xe8\\xaf\\xbb\\xe7\\x89\\xa9\\xef\\xbc\\x9a%s"], tostring(s.read)) } end -- MUT: read back\\n    if s.drops and #s.drops > 0 then\\n        out[#out + 1] = { text = format(L["\\xe6\\x8e\\x89\\xe8\\x90\\xbd %d \\xe5\\xa4\\x84"], #s.drops) }\\n    end\\n'))
'''

OLD2 = '''MUT_PROF_MATCOL_BACK = ('Core/ProfessionUI.lua', (
    b'        sub = tostring(r[5] or ""),\\n        mats = mcol,\\n        matSegs = msegs,\\n',
    b'        sub = table.concat({ tostring(r[5] or ""), PD.MatText(r[12], 4) }, "   "), -- MUT: mats back into sub\\n        mats = "",\\n        matSegs = nil,\\n'))
'''

NEW2 = '''MUT_PROF_MATCOL_BACK = ('Core/ProfessionUI.lua', (
    b'            local sg\\n            s.mats, _, _, sg = PD.MatCol(s._mats, PD.MAT_FS, PD.MAT_W)\\n            s.matSegs = sg\\n',
    b'            s.sub = s.sub .. "   " .. PD.MatText(s._mats, 4) -- MUT: mats back into sub\\n            s.mats = ""\\n            s.matSegs = nil\\n'))
'''

assert t.count(OLD1) == 1, 'df_mut_check OLD1 命中 %d' % t.count(OLD1)
assert t.count(OLD2) == 1, 'df_mut_check OLD2 命中 %d' % t.count(OLD2)
t = t.replace(OLD1, NEW1, 1).replace(OLD2, NEW2, 1)
io.open(DFF, 'w', encoding='utf-8', newline='').write(t)
print('[ok] df_mut_check.py 两条变异已重锚')

# ─────────────────────────── mk_df_mut.py（生成器字面量）─────────────────────
MKF = os.path.join(HERE, 'mk_df_mut.py')
m = io.open(MKF, encoding='utf-8', newline='').read()

# 文件内文本：每行形如  `    "    b'...',\n"`（" 里含 \\n 与 \" 的转义）
MK_PAIRS = [
    # READ_BACK old 段（',\n" 收尾）
    ('''    "    b'    if s.drops and #s.drops > 0 then t[#t + 1] = format(L[\\"\\\\xe6\\\\x8e\\\\x89\\\\xe8\\\\x90\\\\xbd %d \\\\xe5\\\\xa4\\\\x84\\"], #s.drops) end\\\\n',\\n"\n''',
     '''    "    b'    if s.drops and #s.drops > 0 then\\\\n        out[#out + 1] = { text = format(L[\\"\\\\xe6\\\\x8e\\\\x89\\\\xe8\\\\x90\\\\xbd %d \\\\xe5\\\\xa4\\\\x84\\"], #s.drops) }\\\\n    end\\\\n',\\n"\n'''),
    # READ_BACK new 段（第一段，读 read）
    ('''    "    b'    if s.read then t[#t + 1] = format(L[\\"\\\\xe8\\\\xaf\\\\xbb\\\\xe7\\\\x89\\\\xa9\\\\xef\\\\xbc\\\\x9a%s\\"], tostring(s.read)) end -- MUT: read back\\\\n"\n''',
     '''    "    b'    if s.read then out[#out + 1] = { text = format(L[\\"\\\\xe8\\\\xaf\\\\xbb\\\\xe7\\\\x89\\\\xa9\\\\xef\\\\xbc\\\\x9a%s\\"], tostring(s.read)) } end -- MUT: read back\\\\n"\n'''),
    # READ_BACK new 段（第二段，drops 复述，'))\n 收尾）
    ('''    "    if s.drops and #s.drops > 0 then t[#t + 1] = format(L[\\"\\\\xe6\\\\x8e\\\\x89\\\\xe8\\\\x90\\\\xbd %d \\\\xe5\\\\xa4\\\\x84\\"], #s.drops) end\\\\n'))\\n"\n''',
     '''    "    if s.drops and #s.drops > 0 then\\\\n        out[#out + 1] = { text = format(L[\\"\\\\xe6\\\\x8e\\\\x89\\\\xe8\\\\x90\\\\xbd %d \\\\xe5\\\\xa4\\\\x84\\"], #s.drops) }\\\\n    end\\\\n'))\\n"\n'''),
    # MATCOL_BACK old（两行，',\n" 收尾）
    ('''    "    b'        sub = tostring(r[5] or \\"\\"),\\\\n        mats = mcol,\\\\n',\\n"\n''',
     '''    "    b'            local sg\\\\n            s.mats, _, _, sg = PD.MatCol(s._mats, PD.MAT_FS, PD.MAT_W)\\\\n            s.matSegs = sg\\\\n',\\n"\n'''),
    # MATCOL_BACK new（'))\n 收尾）
    ('''    "    b'        sub = table.concat({ tostring(r[5] or \\"\\"), PD.MatText(r[12], 4) }, \\"   \\"), -- MUT: mats back into sub\\\\n        mats = \\"\\",\\\\n        matSegs = nil,\\\\n'))\\n"\n''',
     '''    "    b'            s.sub = s.sub .. \\"   \\" .. PD.MatText(s._mats, 4) -- MUT: mats back into sub\\\\n            s.mats = \\"\\"\\\\n            s.matSegs = nil\\\\n'))\\n"\n'''),
]

for i, (o, n) in enumerate(MK_PAIRS, 1):
    c = m.count(o)
    if c != 1:
        print('[!!] mk_df_mut 第 %d 对命中 %d 次，跳过（不影响成品）' % (i, c))
        continue
    m = m.replace(o, n, 1)
    print('[ok] mk_df_mut 第 %d 对已同步' % i)

io.open(MKF, 'w', encoding='utf-8', newline='').write(m)
print('done')
