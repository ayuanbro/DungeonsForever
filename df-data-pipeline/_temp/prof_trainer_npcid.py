# -*- coding: utf-8 -*-
"""训练师英文名 → QuestieDB NPC ID 匹配（坐标验证消重名）。输出 _trainers_npcid.json。"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'questie'))
from questie_extract import decode_b64  # noqa: E402


def as_text(v):
    if isinstance(v, bytes):
        return v.decode('utf-8', 'replace')
    if isinstance(v, str):
        return v
    return None

TOC = os.path.join(HERE, 'questie', 'forever', 'QuestieDB', 'QuestieDB_Forever.toc')
DATA = os.path.join(HERE, '..', 'Core', 'Data', 'Data_ProfTrainers.lua')

pat = re.compile(r"^## X-(Npc)-(\d+)-S:\s*(\S+)\s*$", re.M)

txt = open(TOC, encoding='utf-8', errors='replace').read()
names = {}
for m in pat.finditer(txt):
    eid, val = int(m.group(2)), m.group(3)
    try:
        row = decode_b64(val)
    except Exception:
        continue
    if isinstance(row, dict):
        nm = as_text(row.get(1))
        if nm:
            names.setdefault(nm, []).append(eid)

multi = sum(1 for v in names.values() if len(v) > 1)
print('questie npc names: %d (ambiguous: %d)' % (len(names), multi))

src = open(DATA, encoding='utf-8').read()
entries = re.findall(
    r'\{\s*rng\s*=\s*"([^"]*)".*?fac\s*=\s*"([AHB])".*?map\s*=\s*(\d+),\s*'
    r'x\s*=\s*([\d.]+),\s*y\s*=\s*([\d.]+).*?en\s*=\s*"([^"]*)"',
    src)
print('trainer entries:', len(entries))

# spawns: npc_spawns 在 questie_forever.json（id -> {mapID: [[x,y],...]}）
qf = json.load(open(os.path.join(HERE, 'questie', 'questie_forever.json'), encoding='utf-8'))
spawns = qf.get('npc_spawns') or {}

out = {}
miss_name, miss_loc = [], []
for rng, fac, mp, x, y, en in entries:
    if en in out:
        continue
    cands = names.get(en) or names.get(en.replace("'", "\u2019")) or []
    if not cands:
        base = re.sub(r'\s*\([^)]*\)\s*$', '', en).strip()
        cands = names.get(base) or names.get(base.replace("'", "\u2019")) or []
    if not cands:
        cands = names.get(en.split(' <')[0]) or []
    if not cands:
        miss_name.append(en)
        continue
    if len(cands) == 1:
        out[en] = cands[0]
        continue
    fx, fy = float(x), float(y)
    picked = None
    for eid in cands:
        sp = spawns.get(str(eid)) or spawns.get(eid) or {}
        pts = sp.get(str(mp)) or sp.get(int(mp)) or []
        for pt in pts:
            px, py = float(pt[0]), float(pt[1])
            if abs(px - fx) < 3 and abs(py - fy) < 3:
                picked = eid
                break
        if picked:
            break
    if picked:
        out[en] = picked
    else:
        miss_loc.append('%s (cands=%s)' % (en, cands))

print('resolved: %d, no-name: %d, no-loc: %d' % (len(out), len(miss_name), len(miss_loc)))
json.dump(out, open(os.path.join(HERE, '_trainers_npcid.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=0)
if miss_name[:10]:
    print('no-name sample:', miss_name[:10])
if miss_loc[:10]:
    print('no-loc sample:', miss_loc[:10])
