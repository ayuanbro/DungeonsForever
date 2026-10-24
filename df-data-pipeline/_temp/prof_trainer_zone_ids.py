# -*- coding: utf-8 -*-
"""78 个待补地名 → QuestieDB zone enum ID 匹配。输出 _trainers_zone_ids.json。"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ZLUA = os.path.join(HERE, 'questie', 'forever', 'QuestieDB', 'src',
                    'corrections', 'enum', 'zones.lua')

src = open(ZLUA, encoding='utf-8', errors='replace').read()
blk = re.search(r'constants\.zoneIDs = \{(.*?)\n\}', src, re.S)
ids = {}
for m in re.finditer(r'([A-Z0-9_]+)\s*=\s*(\d+)', blk.group(1)):
    ids[m.group(1)] = int(m.group(2))
print('zone ids:', len(ids))

need = json.load(open(os.path.join(HERE, '_trainers_zone_zh.json'), encoding='utf-8'))
out, miss = {}, []
for e in need:
    key = re.sub(r'[^A-Z0-9]+', '_', e.upper()).strip('_')
    if key in ids:
        out[e] = ids[key]
    else:
        miss.append(e)
print('hit: %d, miss: %d' % (len(out), len(miss)))
print('miss sample:', miss[:15])
json.dump(out, open(os.path.join(HERE, '_trainers_zone_ids.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=0)
