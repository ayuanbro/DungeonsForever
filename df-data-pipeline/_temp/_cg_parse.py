# -*- coding: utf-8 -*-
"""解析 _cg_probe/*.html：导出 markup 载荷 + 子页链接清单。"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PAT = r'WH\.markup\.printHtml\(\s*("(?:[^"\\]|\\.)*")'

key = sys.argv[1] if len(sys.argv) > 1 else 'balance'
src = io.open(os.path.join(HERE, '_cg_probe', key + '.html'),
              encoding='utf-8', errors='replace').read()

blocks = re.findall(PAT, src)
print('markup blocks:', len(blocks))
for i, b in enumerate(blocks):
    s = json.loads(b)
    print('--- block %d len=%d ---' % (i, len(s)))
    print(s[:300].replace('\n', ' '))

links = sorted(set(re.findall(
    r'/forever/cn/guide/classes/[a-z]+/[a-z0-9\-]+/([a-z0-9\-]+)', src)))
print('subpage slugs:', links)

m = re.search(r'<title>([^<]+)</title>', src)
print('title:', m.group(1) if m else None)

# 导出全部 markup 供细读
out = os.path.join(HERE, '_cg_probe', key + '_markup.txt')
parts = []
for i, b in enumerate(blocks):
    s = json.loads(b)
    parts.append('===== BLOCK %d (len %d) =====\n%s' % (i, len(s), s))
io.open(out, 'w', encoding='utf-8').write('\n\n'.join(parts))
print('->', out)
