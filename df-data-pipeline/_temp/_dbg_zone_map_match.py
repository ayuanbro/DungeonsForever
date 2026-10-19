# -*- coding: utf-8 -*-
"""验证：loc_en 的 zone 部分英文名 == t.map(uiMapID) 的英文名？
路径：zone 名 -> enum areaID -> Data_AreaMap -> uiMapID == t.map ?"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

ENUM = os.path.join(HERE, 'questie', 'forever', 'QuestieDB', 'src', 'corrections', 'enum', 'zones.lua')
AREA_MAP = os.path.join(REPO, 'Core', 'Data', 'Data_AreaMap.lua')
TRAINERS = os.path.join(REPO, 'Core', 'Data', 'Data_ProfTrainers.lua')

consts = {}
for m in re.finditer(r'^\s*([A-Z0-9_]+)\s*=\s*(\d+),',
                     open(ENUM, encoding='utf-8', errors='replace').read(), re.M):
    consts[m.group(1)] = int(m.group(2))


def norm(s):
    return re.sub(r'_+$', '', s.upper().replace("'", '').replace(' ', '_').replace('-', '_'))


by_name = {}
for k, v in consts.items():
    by_name[norm(k)] = v

amap = {}
for m in re.finditer(r'\[\s*(\d+)\s*\]\s*=\s*(\d+)',
                     open(AREA_MAP, encoding='utf-8', errors='replace').read()):
    amap[int(m.group(1))] = int(m.group(2))

rows = json.load(open(os.path.join(HERE, '_trainers_rows.json'), encoding='utf-8'))
# loc_en 形如 "sub, zone" 或 "zone"
pairs = {}
for r in rows:
    le = r['loc_en']
    parts = le.split(', ')
    zone = parts[1] if len(parts) == 2 else parts[0]
    pairs.setdefault(zone, set()).add(r['map'])

ok = bad = noenum = 0
bad_list = []
for zone, maps in sorted(pairs.items()):
    aid = by_name.get(norm(zone))
    if aid is None:
        noenum += 1
        continue
    um = amap.get(aid)
    if um is None:
        noenum += 1
        continue
    if um in maps:
        ok += 1
    else:
        bad += 1
        bad_list.append((zone, aid, um, sorted(maps)))
print('zone名==map英文名  ok=%d bad=%d 无enum/amap=%d' % (ok, bad, noenum))
for z, aid, um, ms in bad_list[:15]:
    print('  MISMATCH %s enum=%d uiMapID=%d rowMaps=%s' % (z, aid, um, ms))
