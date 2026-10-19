# -*- coding: utf-8 -*-
"""清洗 _trainers_zh.json 脏条目。"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
p = os.path.join(HERE, '_trainers_zh.json')
d = json.load(open(p, encoding='utf-8'))
dirty = [k for k, v in d.items()
         if 'http' in v or 'URL Source' in v or len(v) > 30 or not v.strip()]
for k in dirty:
    del d[k]
json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print('cleaned %d dirty, left %d' % (len(dirty), len(d)))
