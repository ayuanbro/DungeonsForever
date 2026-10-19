# -*- coding: utf-8 -*-
"""导出每条重锚所需的精确行内容（repr），供生成器使用。"""
import os
DEV = r'D:\workspace\DungeonsForever'
SPEC = [
    ('Core/ProfessionUI.lua', [(3882, 3882), (3724, 3724), (2881, 2881)]),
    ('Core/DungeonUI.lua', [
        (1512, 1512), (4919, 4919), (5076, 5076), (2761, 2761),
        (2175, 2179), (2238, 2240), (1957, 1965), (2011, 2019),
        (2699, 2701), (3473, 3474), (4002, 4002), (3803, 3804),
        (4678, 4678), (4652, 4652), (1793, 1793), (2852, 2853),
        (2145, 2151), (2132, 2133), (2691, 2692),
    ]),
]
for rel, ranges in SPEC:
    raw = open(os.path.join(DEV, *rel.split('/')), 'rb').read()
    lines = raw.splitlines(keepends=True)
    print('##### %s  (CRLF=%s, 行数=%d)' % (rel, raw.count(b'\r\n') > 0, len(lines)))
    for a, b in ranges:
        seg = b''.join(lines[a - 1:b])
        print('  [%d-%d] %r' % (a, b, seg))
    print()
