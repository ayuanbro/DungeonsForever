# -*- coding: utf-8 -*-
"""统计三页 markup 里的所有标签种类，确认内联节点（spell/item 等）怎么呈现。"""
import json
import os
import re
import sys
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, '_tier_probe')
STR = '("(?:[^"\\\\]|\\\\.)*")'


def markup(path):
    h = open(path, encoding='utf-8').read()
    m = re.search(r'WH\.markup\.printHtml\(\s*' + STR, h, re.S)
    return json.loads(m.group(1)) if m else ''


for k in ('dps', 'tank', 'healer'):
    mk = markup(os.path.join(D, k + '.html'))
    cnt = Counter(m.group(1).split()[0].split('=')[0]
                  for m in re.finditer(r'\[([^\]]+)\]', mk))
    print('###', k, len(mk))
    for tag, n in cnt.most_common():
        print('   %-14s %d' % (tag, n))
    for m in re.finditer(r'\[spell=\d+\]|\[item=\d+\]|\[npc=\d+\]|\[icon[^\]]*\]', mk):
        print('   inline:', m.group(0))
    print()
