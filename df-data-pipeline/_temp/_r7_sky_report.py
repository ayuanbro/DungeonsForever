# -*- coding: utf-8 -*-
"""R7 交付：Skyborne 旧写法残留计数（全库，规范化后应为 0）+ 规范名分布。"""
import io
import json
import os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
EN = json.load(io.open(os.path.join(HERE, '_cg_parsed.json'), encoding='utf-8'))
TD = os.path.join(HERE, '_cg_trans')
OUT = os.path.join(HERE, '_r7_sky_final.txt')

VARIANTS = ['高空天行者', '尊主天空裔', '掠风天空裔', '天空行者', '天空之裔', '天空之灵',
            '天空之民', '天空之城', '天裔族', '天空裔', '空中族', '天翔族', '天生族',
            '空中精灵', '驭风者', '驭空']
CANON = ['高阶天裔', '掠风天裔', '联盟天裔', '天裔精灵', '天裔']


def flat(o, acc):
    if isinstance(o, str):
        acc.append(o)
    elif isinstance(o, list):
        for x in o:
            flat(x, acc)
    elif isinstance(o, dict):
        for k, v in o.items():
            if k in ('t', 'key', 'icon', 'side', 'mark'):
                continue
            flat(v, acc)
    return acc


allc = Counter()
for spec in sorted(EN):
    p = os.path.join(TD, spec + '.json')
    if not os.path.exists(p):
        continue
    obj = json.load(io.open(p, encoding='utf-8'))
    texts = flat(obj, [])
    blob = '\n'.join(texts)
    for v in VARIANTS:
        allc['[旧] ' + v] += blob.count(v)
    for c in CANON:
        allc['[新] ' + c] += blob.count(c)
    allc['[旧] 拉丁 Skyborne'] += blob.count('Skyborne')

lines = ['===== Skyborne 旧写法残留（应全为 0）=====']
for v in VARIANTS:
    lines.append('  %-10s = %d' % (v, allc['[旧] ' + v]))
lines.append('  %-10s = %d' % ('拉丁 Skyborne', allc['[旧] 拉丁 Skyborne']))
lines.append('')
lines.append('===== 规范名分布 =====')
for c in CANON:
    lines.append('  %-10s = %d' % (c, allc['[新] ' + c]))
with io.open(OUT, 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(lines) + '\n')
print('\n'.join(lines))
