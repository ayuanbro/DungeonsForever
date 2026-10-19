# -*- coding: utf-8 -*-
"""一次性：第㊷步 iOS 开关绑定变异 镜像进 mk_df_mut.py（跑完即删）。"""
import io, ast

BS, NL, Q, BQ = chr(92), chr(10), chr(34), chr(39)
NESC = BS + BS + 'n'   # mk 源码里 Python 字符串转义的 \n（文件字面 = 双反斜杠 + n）
p = '_temp/mk_df_mut.py'
s = io.open(p, encoding='utf-8', newline='').read()
if 'MUT_PROF_SET_TOG_GONE' in s:
    raise SystemExit('已存在（幂等保护）')

L1 = '    ' + Q + 'MUT_PROF_SET_PAGE_GONE = (' + BQ + 'Core/ProfessionUI.lua' + BQ + ', (' + BS + 'n' + Q + NL
L2 = '    ' + Q + '    b' + BS + Q + '        PD.RowsSettings(rows)' + NESC + BS + Q + ',' + Q + NL
L3 = '    ' + Q + '    b' + BS + Q + '        -- MUT: settings page unreachable' + NESC + BS + Q + '))' + Q + NL
L4 = '    ' + Q + Q + NL
anchor = L1 + L2 + L3 + L4
assert s.count(anchor) == 1, ('anchor', s.count(anchor))

T2 = '    ' + Q + '    b' + BS + Q + '            tg.__key = spec.togKey' + NESC + BS + Q + ',' + Q + NL
T3 = '    ' + Q + '    b' + BS + Q + '            do end -- MUT: toggle unbound' + NESC + BS + Q + '))' + Q + NL
ins = ('MUT_PROF_SET_TOG_GONE = (' + BQ + 'Core/ProfessionUI.lua' + BQ + ', (' + BS + 'n' + Q + NL
       + T2 + T3 + L4)
s = s.replace(anchor, anchor + ins, 1)

reg_anchor = ('    ' + Q + "    ('专业页：设置页不可达（齿轮点了没反应）', MUT_PROF_SET_PAGE_GONE)," + BS + 'n' + Q + NL)
assert s.count(reg_anchor) == 1, ('reg', s.count(reg_anchor))
s = s.replace(reg_anchor,
    reg_anchor + '    ' + Q + "    ('专业页：iOS 开关不再绑定设置键（点了也写不进 DB）', MUT_PROF_SET_TOG_GONE)," + BS + 'n' + Q + NL, 1)

io.open(p, 'w', encoding='utf-8', newline='').write(s)
ast.parse(s)
print('mk_df_mut.py mirrored: TOG_GONE def + reg')
