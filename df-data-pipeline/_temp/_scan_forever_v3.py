# -*- coding: utf-8 -*-
"""以英文为锚 v3：按 flow 元素索引配对，取元素全文比较。

比叶子级对齐稳健（不受 tb 的 dict-cells / list 两种形态影响）。
"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
EN = json.load(open(os.path.join(HERE, '_cg_parsed.json'), encoding='utf-8'))
TD = os.path.join(HERE, '_cg_trans')
FW = re.compile(r'forever', re.I)


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
    if not isinstance(el, dict):
        return ''
    return ''.join(flat({k: v for k, v in el.items() if k != 't'}, []))


real, fallback, mismatch = [], [], []

for spec in sorted(EN):
    tf = os.path.join(TD, spec + '.json')
    tr = json.load(open(tf, encoding='utf-8')) if os.path.exists(tf) else {}
    for si, sec in enumerate(EN[spec].get('sections', [])):
        tsecs = tr.get('sections') or []
        tsec = tsecs[si] if si < len(tsecs) else {}
        ef = sec.get('flow', [])
        cf = tsec.get('flow', []) or []
        if len(ef) != len(cf):
            mismatch.append((spec, si, len(ef), len(cf)))
        for i, e in enumerate(ef):
            etext = text_of(e)
            if not FW.search(etext):
                continue
            ctext = text_of(cf[i]) if i < len(cf) else None
            if ctext is None:
                fallback.append((spec, si, i, e.get('t'), etext))
            elif '无限' not in ctext:
                real.append((spec, si, i, e.get('t'), etext, ctext))

print('★ 按 flow 元素配对：真漏网 =', len(real), ' / 译文缺失 =', len(fallback))
print('★ flow 元素数不一致的 section =', len(mismatch))
for m in mismatch[:20]:
    print('   ', m)
print()
print('===== A. 真漏网 =====')
for spec, si, i, t, e, c in real:
    print('[%s §%d #%d t=%s]' % (spec, si, i, t))
    print('  EN:', e[:170].replace('\n', '\\n'))
    print('  CN:', c[:170].replace('\n', '\\n'))
print()
print('===== B. 译文缺失 =====')
for spec, si, i, t, e in fallback:
    print('[%s §%d #%d t=%s] %s' % (spec, si, i, t, e[:120].replace('\n', '\\n')))
