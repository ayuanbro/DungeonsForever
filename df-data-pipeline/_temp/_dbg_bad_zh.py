# -*- coding: utf-8 -*-
"""提取 zh=NPC 脏数据行的 NPC ID，供重抓。"""
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

npcid = json.load(open(os.path.join(HERE, '_trainers_npcid.json'), encoding='utf-8'))
zhdb = json.load(open(os.path.join(HERE, '_trainers_zh.json'), encoding='utf-8'))

bad_names = set()
for r in rows:
    if r[2] == 'NPC':
        bad_names.add(r[1])
print('bad names:', len(bad_names))
bad_ids = []
for nm in sorted(bad_names):
    eid = npcid.get(nm) or npcid.get(nm.replace("'", '\u2019')) or npcid.get(nm.split(' <')[0])
    if eid:
        bad_ids.append(int(eid))
print('bad ids:', len(bad_ids))
print('sample:', bad_ids[:10])
json.dump(bad_ids, open(os.path.join(HERE, '_trainers_bad_ids.json'), 'w', encoding='utf-8'))
