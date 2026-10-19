# -*- coding: utf-8 -*-
"""把 QuickBar 里的字符串全局取法改成不依赖客户端别名（桩里没有 strbyte / strsub）。"""
import io
import os

ROOT = r'D:\workspace\DungeonsForever'
OLD = 'local strbyte, strsub, format = strbyte, strsub, format'
NEW = 'local strbyte, strsub, format = string.byte, string.sub, format or string.format'

for rel in ('Core/QuickBar.lua', '_temp/_qb_apply.py'):
    p = os.path.join(ROOT, *rel.split('/'))
    with io.open(p, 'r', encoding='utf-8', newline='') as f:
        s = f.read()
    n = s.count(OLD)
    print('%-24s 命中 %d' % (rel, n))
    if n != 1:
        continue
    with io.open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(s.replace(OLD, NEW, 1))
    b = open(p, 'rb').read()
    print('    CRLF=%d bareLF=%d' % (b.count(b'\r\n'), b.count(b'\n') - b.count(b'\r\n')))
