# -*- coding: utf-8 -*-
"""列出 MapUI.lua 用到的 L 键，并检查 gen_enus.py 的 EN 表是否覆盖。"""
import os
import re

DF = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(DF, 'Core', 'MapUI.lua'), 'rb').read().decode('utf-8')
keys = set(re.findall(r'L\["([^"]+)"\]', src))
gen = open(os.path.join(DF, '_temp', 'gen_enus.py'), 'rb').read().decode('utf-8')
print('MapUI 用键 %d 个：' % len(keys))
for k in sorted(keys):
    print(('  OK   ' if ("'" + k + "'") in gen else '  MISS ') + k)
