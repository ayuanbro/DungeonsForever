# -*- coding-utf-8 -*-
# 修复 PROF_PITFALLS.md 第 11/12 条（bash 反引号吞了标识符）
import io

P = r'D:\workspace\DungeonsForever\.workbuddy\memory\PROF_PITFALLS.md'
s = io.open(P, 'r', encoding='utf-8', newline='').read()
i = s.index('11. **配方页列宽')
good = (
    '11. **配方页列宽是「每渲染现算」不是常量（2026-10-09）**：PD.FitRecipeCols(list) 每次渲染量本页\n'
    '    最宽名称/副行/「新」角标 → RECIPE_NAME_W（钳在 118~38% 行宽）→ MAT_X = nameW+44、\n'
    '    MAT_W = 行宽-132-起点-8，再用新预算重排 s.mats，名称超宽 PD.Fit 截断显示。\n'
    '    改列宽别去动常量区那两行 0.40 兜底（旧静态断言钉着它当加载期缺省）；\n'
    '    名称列截断只截显示、搜索匹配用的是 RecipeList() 时的全名（顺序：先 SearchFilter 再 FitRecipeCols）。\n'
    '    非恒真证明/独立验证走 _prof_search_probe.py / _prof_search_smoke.py（支持 DF_ADDON_ROOT 重定向）。\n'
    '12. **打字节锚点前先看文件当前换行**：ProfessionUI.lua 2026-10-09 被并行会话整文件转成 CRLF\n'
    '    （此前恒 LF）→ _temp/_chk_eol.py 一眼体检；注入类探针按「文件自身换行」写入还原。\n'
)
io.open(P, 'w', encoding='utf-8', newline='').write(s[:i] + good)
print('FIXED')
