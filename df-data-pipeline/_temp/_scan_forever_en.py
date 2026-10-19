# -*- coding: utf-8 -*-
"""以英文为锚的永久性排查：英文含 Forever 的条目，中文译文必须含「无限」。

同时反向列出中文字段里出现的其它可疑版本名（永驻/长存/永生/万古…），
用于验证「以中文变体为锚」的做法必然漏网。
"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
EN = json.load(open(os.path.join(HERE, '_cg_parsed.json'), encoding='utf-8'))
TD = os.path.join(HERE, '_cg_trans')
FW = re.compile(r'forever', re.I)

missing = []      # 英文有 Forever、中文没「无限」
pairs = []        # 全部命中对（供人工核）
SUSPECT = re.compile(r'永驻|永駐|长存|長存|永生|万古|萬古|永世|不灭|不滅|永存|永续|永續|恒久|恆久|永久|永恒|永恆')


def walk(en, cn, path):
    if isinstance(en, str):
        if FW.search(en):
            cns = cn if isinstance(cn, str) else ''
            pairs.append((path, en, cns))
            if '无限' not in cns:
                missing.append((path, en, cns))
        return
    if isinstance(en, list):
        cnl = cn if isinstance(cn, list) else []
        for i, x in enumerate(en):
            walk(x, cnl[i] if i < len(cnl) else None, '%s[%d]' % (path, i))
        return
    if isinstance(en, dict):
        cnd = cn if isinstance(cn, dict) else {}
        for k, v in en.items():
            walk(v, cnd.get(k), path + '.' + k)
        return


for spec in EN:
    tf = os.path.join(TD, spec + '.json')
    tr = json.load(open(tf, encoding='utf-8')) if os.path.exists(tf) else {}
    walk(EN[spec], tr, spec)

print('=== A. 英文含 Forever 的条目总数 ===', len(pairs))
print('=== B. 其中中文没「无限」的漏网数 ===', len(missing))
print()
for p, e, c in missing:
    print('###', p)
    print('  EN:', e[:200].replace('\n', '\\n'))
    print('  CN:', (c or '<无译文/回落英文>')[:200].replace('\n', '\\n'))
    print()

print('=== C. 中文译文里出现的可疑版本名变体统计 ===')
tally = {}
for p, e, c in pairs:
    for m in SUSPECT.finditer(c or ''):
        tally[m.group(0)] = tally.get(m.group(0), 0) + 1
for k, v in sorted(tally.items(), key=lambda kv: -kv[1]):
    print(' ', k, v)
if not tally:
    print('  (无)')

print()
print('=== D. 各专精命中数 ===')
per = {}
for p, e, c in pairs:
    top = p.split('.')[0]
    per[top] = per.get(top, 0) + 1
for k, v in sorted(per.items(), key=lambda kv: -kv[1]):
    print(' ', k, v)
