# -*- coding: utf-8 -*-
"""拆分 loc_en 为 zone / sub / note，输出去重清单。"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
TRAINERS = os.path.join(REPO, 'Core', 'Data', 'Data_ProfTrainers.lua')

txt = open(TRAINERS, encoding='utf-8', errors='replace').read()
locs = re.findall(r'loc_en = "([^"]*)"', txt)
zones, subs, notes = set(), set(), set()
for le in locs:
    note = ''
    m = re.search(r' \((.*)\)$', le)
    if m:
        note = m.group(1)
        le = le[:m.start()]
    notes.add(note)
    parts = le.split(', ')
    if len(parts) == 2:
        subs.add(parts[0])
        zones.add(parts[1])
    else:
        zones.add(parts[0])
print('zones: %d, subs: %d, notes: %d' % (len(zones), len(subs), len(notes)))
print('--- zones ---')
for z in sorted(zones):
    print(' ', z)
print('--- subs ---')
for s in sorted(subs):
    print(' ', s)
print('--- notes ---')
for n in sorted(notes):
    print(' ', repr(n))
json.dump({'zones': sorted(zones), 'subs': sorted(subs), 'notes': sorted(notes)},
          open(os.path.join(HERE, '_trainers_zone_parts.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
