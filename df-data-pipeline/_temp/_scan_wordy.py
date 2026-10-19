# -*- coding: utf-8 -*-
"""产线扫描：Core/Data 下生成的 Data_ClassGuide（zhCN/enUS/zhTW）是否含
「版本 token 相邻版本性杂词」的怪搭配（如「《无限》怀旧服」）。"""
import io
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = ['Core/Data/Data_ClassGuide.lua',
         'Core/Data/enUS/Data_ClassGuide.lua',
         'Core/Data/zhTW/Data_ClassGuide.lua']

_VER_TOK = r'(?:《魔兽世界：无限》|《无限》|无限测试服|无限版本|无限服|无限版)'
_WORDY = (r'(?:怀旧服|懷舊服|怀旧|懷舊|资料片|資料片|永驻|永駐|永燃|永夜|永昼'
          r'|永[恒恆](?!之)|永久|经典赛季|經典賽季|永远的魔兽世界|[Ff]orefore)')
RE = re.compile(r'(?:' + _VER_TOK + r'\s*' + _WORDY + r'|' + _WORDY + r'\s*' + _VER_TOK + r')')

total = 0
for rel in FILES:
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        continue
    txt = io.open(p, encoding='utf-8').read()
    hits = RE.findall(txt)
    if hits:
        print('%s: %d 处 %s' % (rel, len(hits), sorted(set(hits))))
    total += len(hits)
print('★ 「无限+杂词」命中 =', total)
