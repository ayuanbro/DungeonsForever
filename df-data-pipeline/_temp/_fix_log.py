# -*- coding: utf-8 -*-
# 补日志：上一条层判据代码片段被 shell 吃掉
import io

p = r'D:/workspace/DungeonsForever/.workbuddy/memory/2026-10-04.md'
s = io.open(p, encoding='utf-8', newline='').read()
old = '- **MapUI ExtraPinsFor**：层判据  → （entrance/quest/object 第 4 位、rare 第 5 位，缺省 1）。\n'
new = ('- **MapUI ExtraPinsFor**：层判据改为「local pf = p[(kind == "rare") and 5 or 4] or 1; pf == floor」'
       '（entrance/quest/object 第 4 位、rare 第 5 位，缺省 1）。\n')
assert s.count(old) == 1, s.count(old)
io.open(p, 'w', encoding='utf-8', newline='').write(s.replace(old, new, 1))
print('ok')
