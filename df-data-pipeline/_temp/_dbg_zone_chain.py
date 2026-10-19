# -*- coding: utf-8 -*-
"""验证：zone 英文名 -> areaID(enum) -> uiMapID(Data_AreaMap) == Data_ProfTrainers.map？"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

ENUM = os.path.join(HERE, 'questie', 'forever', 'QuestieDB', 'src', 'corrections', 'enum', 'zones.lua')
AREA_MAP = os.path.join(REPO, 'Core', 'Data', 'Data_AreaMap.lua')
TRAINERS = os.path.join(REPO, 'Core', 'Data', 'Data_ProfTrainers.lua')

# 1) enum: CONSTANT = id
consts = {}
txt = open(ENUM, encoding='utf-8', errors='replace').read()
for m in re.finditer(r'^\s*([A-Z0-9_]+)\s*=\s*(\d+),', txt, re.M):
    consts[m.group(1)] = int(m.group(2))


def norm(s):
    s = s.upper().replace("'", '').replace(' ', '_').replace('-', '_')
    s = re.sub(r'_+$', '', s)
    return s


by_name = {}
for k, v in consts.items():
    by_name[norm(k)] = v

# 2) Data_AreaMap: areaID -> uiMapID
amap = {}
atxt = open(AREA_MAP, encoding='utf-8', errors='replace').read()
for m in re.finditer(r'\[\s*(\d+)\s*\]\s*=\s*(\d+)', atxt):
    amap[int(m.group(1))] = int(m.group(2))
print('areaMap entries:', len(amap))

# 3) trainers: map field
ttxt = open(TRAINERS, encoding='utf-8', errors='replace').read()
maps = re.findall(r'map = (\d+),', ttxt)
print('trainer rows:', len(maps), 'unique maps:', len(set(maps)))

# 4) loc_en zone 部分 -> enum -> uiMapID 比对
locs = re.findall(r'loc_en = "([^"]*)"', ttxt)
zone_names = set()
for le in locs:
    z = le.split(', ')[0]
    z = re.sub(r' \(.*\)$', '', z)
    zone_names.add(z)
print('unique zone names:', len(zone_names))

hit = miss = ok = bad = 0
misses = []
for z in sorted(zone_names):
    aid = by_name.get(norm(z))
    if aid is None:
        miss += 1
        misses.append(z)
        continue
    hit += 1
    um = amap.get(aid)
    if um is not None and um in set(int(x) for x in maps):
        ok += 1
print('enum hit=%d miss=%d; hit 中 uiMapID 命中 map 字段=%d' % (hit, miss, ok))
print('miss 样例:', misses[:10])
