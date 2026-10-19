# -*- coding: utf-8 -*-
# 2026-10-09 给 df_mut_check.py 补「配方搜索 + 名称列现算」4 条变异 + 登记
import sys

P = r'D:\workspace\DungeonsForever\_temp\df_mut_check.py'
s = open(P, 'rb').read().decode('utf-8')

if 'MUT_SEARCH_FILTER_GONE' in s:
    print('SKIP: 已插入过'); sys.exit(0)

def rep(old, new, tag):
    global s
    n = s.count(old)
    if n != 1:
        print('FATAL[%s]: 锚点命中 %d 次' % (tag, n)); sys.exit(1)
    s = s.replace(old, new, 1)
    print('OK %s' % tag)

rep("""MUTATIONS = [
""",
"""# ㉘ 配方搜索 + 名称列现算（2026-10-09：配方页加搜索框 / 名称列按本页现算）
MUT_SEARCH_FILTER_GONE = ('Core/ProfessionUI.lua', (
    b'    local list = PD.SearchFilter(PD.RecipeList())\n',
    b'    local list = PD.RecipeList()\n'))
MUT_RECIPE_COLS_STATIC = ('Core/ProfessionUI.lua', (
    '    PD.MAT_X = nameW + PD.RECIPE_NAME_PAD\n'.encode('utf-8'),
    '    PD.MAT_X = math.floor(PD.MAT_ROW_W * 0.40)\n'.encode('utf-8')))
MUT_SEARCH_HIDE = ('Core/ProfessionUI.lua', (
    b'        if PD.tab == "recipe" and not PD.setOpen then\n'
    b'            PD.searchBox:ClearAllPoints()',
    b'        if false and PD.tab == "recipe" and not PD.setOpen then\n'
    b'            PD.searchBox:ClearAllPoints()'))
MUT_SEARCH_NORENDER = ('Core/ProfessionUI.lua', (
    b'        PD.searchQ = t\n        PD.Render()\n',
    b'        PD.searchQ = t\n'))

MUTATIONS = [
""", 'mut-defs')

rep("""    ('前导链备注：备注行不再渲染', MUT_QPRENOTE_OFF),
    ('前导链备注：备注挂到了别的任务上（界面读不到）', MUT_QPRENOTE_WRONGKEY),
]
""",
"""    ('前导链备注：备注行不再渲染', MUT_QPRENOTE_OFF),
    ('前导链备注：备注挂到了别的任务上（界面读不到）', MUT_QPRENOTE_WRONGKEY),

    # ㉘ 配方搜索 + 名称列现算（2026-10-09）
    ('搜索：列表过滤被绕过（搜索框形同虚设）', MUT_SEARCH_FILTER_GONE),
    ('搜索：名称列退回固定分割（材料列变窄）', MUT_RECIPE_COLS_STATIC),
    ('搜索：切离配方页搜索框不隐藏', MUT_SEARCH_HIDE),
    ('搜索：输入后不重渲染（要按回车才滤）', MUT_SEARCH_NORENDER),
]
""", 'mut-register')

open(P, 'wb').write(s.encode('utf-8'))
print('写入完成')
