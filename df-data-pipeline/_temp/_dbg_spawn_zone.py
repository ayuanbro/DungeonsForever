# -*- coding: utf-8 -*-
"""新链路验证：训练师 NPC -> spawns zone ID -> 与已有 33 个 areaID 比对。"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))

npcid = json.load(open(os.path.join(HERE, '_trainers_npcid.json'), encoding='utf-8'))
zhdb = json.load(open(os.path.join(HERE, '_trainers_zh.json'), encoding='utf-8'))
spawns = json.load(open(os.path.join(HERE, 'questie', 'questie_forever.json'), encoding='utf-8')).get('npc_spawns') or {}
zone_ids = json.load(open(os.path.join(HERE, '_trainers_zone_ids.json'), encoding='utf-8'))

name2zid = {}
for en, eid in npcid.items():
    sp = spawns.get(str(eid))
    if sp:
        name2zid[en] = sorted(int(k) for k in sp.keys())

print('trainers with spawns:', len(name2zid))
print('--- zone name -> areaID(enum) vs spawns zone IDs ---')
mism = same = 0
for zn, aid in sorted(zone_ids.items()):
    # 找该 zone 名下的训练师
    hits = []
    for en, zids in name2zid.items():
        if aid in zids:
            hits.append(en)
    tag = 'HIT' if hits else '---'
    if hits:
        same += 1
    print('%s %-22s enum=%d trainers=%d' % (tag, zn, aid, len(hits)))
print('matched: %d/%d' % (same, len(zone_ids)))
