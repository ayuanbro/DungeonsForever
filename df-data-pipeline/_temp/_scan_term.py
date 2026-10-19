# -*- coding: utf-8 -*-
"""扫描 _cg_trans/*.json 里所有指代版本名（英文 Forever）的中文译法分布。"""
import json, os, re, collections

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_cg_trans')
pat = re.compile(r'.{0,8}(?:永恒|永久).{0,8}')
cnt = collections.Counter()
per = collections.Counter()

def walk(o, fn):
    if isinstance(o, str):
        for m in pat.finditer(o):
            cnt[m.group(0).replace('\n', '\\n')] += 1
            per[fn] += 1
    elif isinstance(o, list):
        for x in o:
            walk(x, fn)
    elif isinstance(o, dict):
        for x in o.values():
            walk(x, fn)

for f in sorted(os.listdir(D)):
    if f.endswith('.json'):
        with open(os.path.join(D, f), encoding='utf-8') as fh:
            walk(json.load(fh), f)

print('=== pattern counts (top 90) ===')
for k, v in cnt.most_common(90):
    print(v, repr(k))
print('=== total ===', sum(cnt.values()))
print('=== files with hits ===')
for k, v in per.most_common():
    print(k, v)
