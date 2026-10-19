# -*- coding: utf-8 -*-
# 修复 patch_mut_search.py 写坏的变异定义（\n 被解析成真实换行 → Python 字面量断裂）
import sys

P = r'D:\workspace\DungeonsForever\_temp\df_mut_check.py'
s = open(P, 'rb').read().decode('utf-8')

start = s.index('# ㉘ 配方搜索 + 名称列现算（2026-10-09：配方页加搜索框 / 名称列按本页现算）')
end = s.index('MUTATIONS = [', start)
broken = s[start:end]

good = (
    "# ㉘ 配方搜索 + 名称列现算（2026-10-09：配方页加搜索框 / 名称列按本页现算）\n"
    "MUT_SEARCH_FILTER_GONE = ('Core/ProfessionUI.lua', (\n"
    "    b'    local list = PD.SearchFilter(PD.RecipeList())\\n',\n"
    "    b'    local list = PD.RecipeList()\\n'))\n"
    "MUT_RECIPE_COLS_STATIC = ('Core/ProfessionUI.lua', (\n"
    "    '    PD.MAT_X = nameW + PD.RECIPE_NAME_PAD\\n'.encode('utf-8'),\n"
    "    '    PD.MAT_X = math.floor(PD.MAT_ROW_W * 0.40)\\n'.encode('utf-8')))\n"
    "MUT_SEARCH_HIDE = ('Core/ProfessionUI.lua', (\n"
    "    b'        if PD.tab == \"recipe\" and not PD.setOpen then\\n'\n"
    "    b'            PD.searchBox:ClearAllPoints()',\n"
    "    b'        if false and PD.tab == \"recipe\" and not PD.setOpen then\\n'\n"
    "    b'            PD.searchBox:ClearAllPoints()'))\n"
    "MUT_SEARCH_NORENDER = ('Core/ProfessionUI.lua', (\n"
    "    b'        PD.searchQ = t\\n        PD.Render()\\n',\n"
    "    b'        PD.searchQ = t\\n'))\n\n"
)

s = s[:start] + good + s[end:]
open(P, 'wb').write(s.encode('utf-8'))
print('已重写变异定义块（原 %d 字节 → 新 %d 字节）' % (len(broken), len(good)))
