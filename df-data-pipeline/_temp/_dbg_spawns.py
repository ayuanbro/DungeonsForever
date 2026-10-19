# -*- coding: utf-8 -*-
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
for f in sorted(os.listdir(HERE)):
    if 'spawn' in f.lower() and f.endswith('.json'):
        print('found:', f)
        d = json.load(open(os.path.join(HERE, f), encoding='utf-8'))
        if isinstance(d, dict):
            ks = list(d.keys())[:5]
            print('  keys:', ks)
            for k in ks[:2]:
                v = d[k]
                print('  ', k, repr(v)[:200])
