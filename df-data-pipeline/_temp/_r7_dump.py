# -*- coding: utf-8 -*-
"""R7：导出疑难元素的 EN/CN 原文，便于精确修。"""
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
EN = json.load(io.open(os.path.join(HERE, '_cg_parsed.json'), encoding='utf-8'))
TD = os.path.join(HERE, '_cg_trans')
OUT = os.path.join(HERE, '_r7_dump_report.txt')

TARGETS = [
    ('paladin_protection', 'changes', 2),
    ('paladin_retribution', 'changes', 2),
    ('warlock_affliction', 'viability', 0),
    ('warlock_demonology', 'beginner', 0),
    ('warlock_destruction', 'viability', 0),
    ('warlock_destruction', 'sw', 0),
    ('warlock_destruction', 'sw', 1),
    ('shaman_elemental', 'races', 6),
    ('mage_arcane', 'prof', 1),
    ('warlock_affliction', 'changes', 2),
    ('warlock_demonology', 'changes', 3),
    ('warlock_destruction', 'changes', 2),
    ('warrior_arms', 'races', 5),
    ('druid_restoration', 'changes', 4),
]

LOG = []


def load(spec):
    p = os.path.join(TD, spec + '.json')
    return json.load(io.open(p, encoding='utf-8')) if os.path.exists(p) else {}


for spec, key, idx in TARGETS:
    tr = load(spec)
    tmap = {s.get('key'): s for s in (tr.get('sections') or [])}
    esec = None
    for s in EN[spec].get('sections', []):
        if s.get('key') == key:
            esec = s
    tsec = tmap.get(key)
    LOG.append('===== %s / %s #%d =====' % (spec, key, idx))
    LOG.append('--- EN ---')
    LOG.append(json.dumps(esec['flow'][idx] if esec and idx < len(esec['flow']) else None,
                          ensure_ascii=False))
    LOG.append('--- CN ---')
    LOG.append(json.dumps((tsec or {}).get('flow', [])[idx] if tsec else None,
                          ensure_ascii=False))
    LOG.append('')

with io.open(OUT, 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(LOG) + '\n')
print('report written: %s' % OUT)
