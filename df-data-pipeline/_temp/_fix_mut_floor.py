# -*- coding: utf-8 -*-
# 重锚「ExtraPinsFor 层判据」变异：旧锚（floor == 1）已被 pf 判据取代
import io

P = 'df_mut_check.py'
s = io.open(P, encoding='utf-8', newline='').read()

old = ("         u8('                    if floor == nil or floor == 1 then\\n'),\n"
       "         u8('                    if floor == nil or floor == 2 then -- MUT: floor guard broken\\n')))),")
new = ("         u8('                    local pf = p[(kind == \"rare\") and 5 or 4] or 1\\n'\n"
       "            '                    if floor == nil or pf == floor then\\n'),\n"
       "         u8('                    local pf = p[(kind == \"rare\") and 5 or 4] or 1\\n'\n"
       "            '                    if floor == nil or pf == 2 then -- MUT: floor guard broken\\n')))),")
n = s.count(old)
assert n == 1, n
s = s.replace(old, new, 1)
io.open(P, 'w', encoding='utf-8', newline='').write(s)
print('层判据变异已重锚')
