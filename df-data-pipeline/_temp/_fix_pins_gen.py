# -*- coding: utf-8 -*-
"""修 fc_pins.py：块间逗号 + 字符串引号。"""
src = open('_temp/fc_pins.py', encoding='utf-8').read()
a = 'out = head + ",\\n".join(blocks) + "\\n}\\n"'
assert a in src, '锚点A'
src = src.replace(a, 'out = head + "\\n".join(blocks) + "\\n}\\n"')
b = 'cells = [fmt(p[0]), fmt(p[1])] + [str(v) for v in p[2:]]'
assert b in src, '锚点B'
src = src.replace(b, 'cells = [fmt(p[0]), fmt(p[1])]\n'
                     '                for v in p[2:]:\n'
                     '                    cells.append(\'"%s"\' % v if isinstance(v, str) else str(v))')
open('_temp/fc_pins.py', 'w', encoding='utf-8', newline='\n').write(src)
print('两处已修')
