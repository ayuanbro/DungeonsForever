# -*- coding: utf-8 -*-
"""R7 分析：① Skyborne 各写法 EN<->CN 对照 + 变体计数；② 中英夹杂（拉丁残留）扫描。只读，结果落盘。"""
import io
import json
import os
import re
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
EN = json.load(io.open(os.path.join(HERE, '_cg_parsed.json'), encoding='utf-8'))
TD = os.path.join(HERE, '_cg_trans')
REPORT = os.path.join(HERE, '_r7_scan_report.txt')

SID = re.compile(r'\|s\d+\|')
# Skyborne 相关 CN 写法（长词优先，避免子串误配）
SKY_CN = ['尊主天空裔', '掠风天空裔', '高空天行者', '天空行者', '天空之民', '天空之城',
          '天裔族', '天空裔', '空中族', '天翔族', '天生族', '空中精灵', '驭风者', '驭空',
          '天行者', '天裔', '高阶天裔']
# 全库夹生拉丁词白名单（游戏术语/专名，不算未译）
ALLOW = re.compile(
    r'\b(PVP|PVE|AOE|DPS|HPS|DOT|HOT|BOSS|BETA|TBC|WOTLK|WOD|RAIDBOTS|DISCORD|WCL|CD|GCD|AP|SP|HP|MP|AOE)\b',
    re.I)

OUT = []


def w(s=''):
    OUT.append(s)


def flat(o, acc):
    if isinstance(o, str):
        acc.append(o)
    elif isinstance(o, list):
        for x in o:
            flat(x, acc)
    elif isinstance(o, dict):
        for k, v in o.items():
            if k in ('t', 'key'):
                continue
            flat(v, acc)
    return acc


def text_of(el):
    if not isinstance(el, dict):
        return ''
    return ' '.join(flat({k: v for k, v in el.items() if k != 't'}, []))


def clean(s):
    return re.sub(r'\s+', ' ', SID.sub('', s or '')).strip()


def load(spec):
    p = os.path.join(TD, spec + '.json')
    return json.load(io.open(p, encoding='utf-8')) if os.path.exists(p) else {}


def rows():
    for spec in sorted(EN):
        tr = load(spec)
        tmap = {s.get('key'): s for s in (tr.get('sections') or [])}
        for sec in EN[spec].get('sections', []):
            tsec = tmap.get(sec.get('key'))
            cf = (tsec or {}).get('flow', []) or []
            for i, e in enumerate(sec.get('flow', [])):
                et = text_of(e)
                ct = text_of(cf[i]) if i < len(cf) else ''
                yield spec, sec.get('key'), i, e.get('t'), et, ct


R = list(rows())

# ---------------- ① Skyborne ----------------
w('########## ① Skyborne EN<->CN 逐条 ##########')
sky_rows = []
for spec, key, i, t, et, ct in R:
    ec = clean(et)
    cc = clean(ct)
    if 'skyborne' in ec.lower() or any(v in cc for v in SKY_CN) or 'skyborne' in cc.lower():
        sky_rows.append((spec, key, i, t, ec, cc))
for spec, key, i, t, ec, cc in sky_rows:
    w('[%s / %s #%d t=%s]' % (spec, key, i, t))
    w('   EN: %s' % (ec[:220]))
    w('   CN: %s' % (cc[:220]))

w('')
w('########## ① CN 侧 Skyborne 各写法计数 ##########')
cnt = Counter()
for spec, key, i, t, ec, cc in sky_rows:
    for v in SKY_CN:
        if v in cc:
            cnt[v] += 1
for k, v in cnt.most_common():
    w('  %-12s x%d' % (k, v))

# ---------------- ② 中英夹杂 ----------------
w('')
w('########## ② CN 含拉丁字母（去 |sID|/白名单后仍有 >=2 连续字母）##########')
mixed = []
for spec, key, i, t, et, ct in R:
    cc = clean(ct)
    if not cc:
        continue
    stripped = ALLOW.sub(' ', cc)
    runs = re.findall(r'[A-Za-z][A-Za-z\-\' ]{0,}', stripped)
    runs = [r.strip() for r in runs if len(r.strip()) >= 2]
    if runs:
        mixed.append((spec, key, i, t, clean(et), cc, runs))
w('命中元素数 = %d' % len(mixed))
for spec, key, i, t, ec, cc, runs in mixed:
    w('[%s / %s #%d t=%s]  latin=%s' % (spec, key, i, t, runs))
    w('   EN: %s' % (ec[:200]))
    w('   CN: %s' % (cc[:200]))

with io.open(REPORT, 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(OUT) + '\n')
print('report written: %s  (sky=%d, mixed=%d)' % (REPORT, len(sky_rows), len(mixed)))
