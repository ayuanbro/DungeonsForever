# -*- coding: utf-8 -*-
"""dump 指定 spec/key 的 EN / CN 逐元素全文（不截断）。"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EN = json.load(io.open(os.path.join(HERE, '_cg_parsed.json'), encoding='utf-8'))
TD = os.path.join(HERE, '_cg_trans')

TARGETS = [
    ('mage_arcane', 'races'),
    ('mage_fire', 'races'),
    ('priest_discipline', 'prof'),
]


def flat(o, acc):
    if isinstance(o, str):
        acc.append(o)
    elif isinstance(o, list):
        for x in o:
            flat(x, acc)
    elif isinstance(o, dict):
        for k, v in o.items():
            if k in ('title', 't', 'key'):
                continue
            flat(v, acc)
    return acc


def text_of(el):
    return ''.join(flat({k: v for k, v in el.items() if k != 't'}, [])) if isinstance(el, dict) else ''


def main():
    for spec, key in TARGETS:
        tr = json.load(io.open(os.path.join(TD, spec + '.json'), encoding='utf-8'))
        tmap = {s.get('key'): s for s in (tr.get('sections') or [])}
        sec = next(s for s in EN[spec]['sections'] if s.get('key') == key)
        tsec = tmap.get(key)
        print('#' * 70)
        print('## %s / %s' % (spec, key))
        ef = sec.get('flow', [])
        cf = (tsec or {}).get('flow', [])
        for i, e in enumerate(ef):
            c = cf[i] if i < len(cf) else None
            print('--- [%02d] EN.t=%s' % (i, e.get('t')))
            print('EN:', json.dumps(e.get('v'), ensure_ascii=False)[:1200])
            if c is not None:
                print('CN:', json.dumps(c.get('v'), ensure_ascii=False)[:1200])


if __name__ == '__main__':
    main()
