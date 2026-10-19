# -*- coding: utf-8 -*-
"""探针：对比站点「职业主页」与「细分专精子页」的内容差异，判断是否需要扩展抓取。"""
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fc_bis as F

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_fc_bis', 'probe')
os.makedirs(OUT, exist_ok=True)

TARGETS = [
    ('druid', ''), ('druid', '/balance'), ('druid', '/restoration'),
    ('priest', ''), ('priest', '/holy'), ('priest', '/shadow-pvp'),
    ('mage', ''), ('mage', '/arcane'),
    ('paladin', ''), ('paladin', '/holy'),
    ('rogue', ''), ('rogue', '/assassination'),
    ('shaman', ''), ('shaman', '/enhancement'),
]

for cls, suffix in TARGETS:
    name = '%s%s.html' % (cls, suffix.strip('/').replace('/', '_'))
    dst = os.path.join(OUT, name)
    url = '%s/zh-cn/bis/%s%s' % (F.BASE, cls, suffix)
    st = F.fetch(url, dst, force=False, offline=False, allow_net=True)
    print('%-28s %s' % (name, st))
    time.sleep(0.8)

print()
print('%-24s %-6s %-8s %-8s %s' % ('page', 'slots', 'rows', 'enchs', 'title'))
for cls, suffix in TARGETS:
    name = '%s%s.html' % (cls, suffix.strip('/').replace('/', '_'))
    p = os.path.join(OUT, name)
    if not os.path.exists(p):
        continue
    h = open(p, encoding='utf-8', errors='replace').read()
    tm = re.search(r'<title>(.*?)</title>', h, re.S)
    spec = F.parse_page(h)
    nrows = sum(len(v) for v in spec['rows'].values())
    print('%-24s %-6d %-8d %-8d %s' % (
        '%s%s' % (cls, suffix), len(spec['slots']), nrows, len(spec.get('enchs') or []),
        (tm.group(1).strip()[:60] if tm else '')))
