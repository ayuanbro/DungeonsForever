# -*- coding: utf-8 -*-
"""统计 loc_zh 构成 + zh=NPC 脏数据规模。"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
TRAINERS = os.path.join(REPO, 'Core', 'Data', 'Data_ProfTrainers.lua')

txt = open(TRAINERS, encoding='utf-8', errors='replace').read()
rows = re.findall(
    r'\{ rng = "[^"]*", fac = "[AH]", map = (\d+), x = [^,]+, y = [^,]+, '
    r'en = "([^"]*)", zh = "([^"]*)", tw = "([^"]*)", '
    r'loc_en = "([^"]*)", loc_zh = "([^"]*)", loc_tw = "([^"]*)" \}', txt)
print('parsed rows:', len(rows))
bad_zh = [r for r in rows if r[2] in ('NPC', '') or r[2] == r[1]]
print('bad zh rows:', len(bad_zh))
for r in bad_zh[:10]:
    print('  ', r[1], '->', r[2])
print('--- loc_zh samples ---')
for r in rows[:8]:
    print('  loc_en=%r loc_zh=%r' % (r[3], r[4]))
json.dump([{'map': int(r[0]), 'en': r[1], 'zh': r[2], 'tw': r[3],
            'loc_en': r[4], 'loc_zh': r[5], 'loc_tw': r[6]} for r in rows],
          open(os.path.join(HERE, '_trainers_rows.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=0)
