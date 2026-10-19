# -*- coding: utf-8 -*-
"""扫 Skyborne 相关种族专名：EN 变体 → 各译文落法对照表。"""
import io
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
EN = json.load(io.open(os.path.join(HERE, '_cg_parsed.json'), encoding='utf-8'))
TD = os.path.join(HERE, '_cg_trans')

SID = re.compile(r'\|s\d+\|')
SKY = re.compile(r'Skyborne', re.I)


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


def clean(s):
    return re.sub(r'\s+', ' ', SID.sub('', s)).strip()


def load(spec):
    p = os.path.join(TD, spec + '.json')
    return json.load(io.open(p, encoding='utf-8')) if os.path.exists(p) else {}


# 1) 枚举 EN 里出现的 Skyborne 相邻短语（大写开头连续词 + Skyborne）
phrases = {}
rows = []
for spec in sorted(EN):
    tr = load(spec)
    tmap = {s.get('key'): s for s in (tr.get('sections') or [])}
    for sec in EN[spec].get('sections', []):
        tsec = tmap.get(sec.get('key'))
        cf = (tsec or {}).get('flow', []) or []
        for i, e in enumerate(sec.get('flow', [])):
            et = text_of(e)
            if not SKY.search(et):
                continue
            ct = text_of(cf[i]) if i < len(cf) else ''
            # EN 里的 Skyborne 短语
            for m in re.finditer(r'((?:[A-Z][a-z]+\s+){0,3}Skybornes?(?:\s+(?:Elves?|Elf))?)', et):
                phrases.setdefault(m.group(1), 0)
                phrases[m.group(1)] += 1
            rows.append((spec, sec.get('key'), i, e.get('t'), clean(et), clean(ct)))

print('===== EN 中 Skyborne 短语形态 =====')
for k, v in sorted(phrases.items(), key=lambda x: -x[1]):
    print('  %-32s x%d' % (k, v))

print('\n===== 逐条 EN→CN 对照 =====')
for spec, key, i, t, et, ct in rows:
    # 只取含 Skyborne 的那一小段
    m = SKY.search(et)
    eseg = et[max(0, m.start() - 20):m.start() + 40]
    print('[%s / %s #%d t=%s]' % (spec, key, i, t))
    print('   EN…%s…' % eseg)
    print('   CN: %s' % ct[:150])

print('\n===== CN 侧含 Skyborne 拉丁（未译）之处 =====')
for spec, key, i, t, et, ct in rows:
    if SKY.search(ct):
        print('  [%s / %s #%d] %s' % (spec, key, i, ct[:120]))

print('\n===== CN 侧已汉化的种族专名落法 =====')
from collections import Counter
c = Counter()
for spec, key, i, t, et, ct in rows:
    for name in ['高阶天裔', '高空天行者', '天裔族', '天裔', '天行者']:
        if name in ct:
            c[name] += 1
for k, v in c.most_common():
    print('  %-12s x%d' % (k, v))
