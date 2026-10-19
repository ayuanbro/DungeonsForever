# -*- coding: utf-8 -*-
"""清洗 zh/tw = "NPC" 脏值为英文名回退（这些是无限服自定义 NPC，无官方译名）。"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
LUA = os.path.join(REPO, 'Core', 'Data', 'Data_ProfTrainers.lua')

src = open(LUA, encoding='utf-8', newline='').read()
pat = re.compile(r'en = "([^"]*)", zh = "NPC", tw = "[^"]*"')
n = len(pat.findall(src))
out = pat.sub(lambda m: 'en = "%s", zh = "%s", tw = "%s"' % (m.group(1), m.group(1), m.group(1)), src)
open(LUA, 'w', encoding='utf-8', newline='').write(out)
print('cleaned %d rows' % n)
left = len(re.findall(r'zh = "NPC"', out))
print('still NPC:', left)
