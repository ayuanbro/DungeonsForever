# -*- coding: utf-8 -*-
"""R7 精炼：只报「中文里夹生的英文实词」（排除游戏缩写/标记/races 型 markup）。只读，落盘。"""
import io
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
EN = json.load(io.open(os.path.join(HERE, '_cg_parsed.json'), encoding='utf-8'))
TD = os.path.join(HERE, '_cg_trans')
REPORT = os.path.join(HERE, '_r7_mixed_report.txt')

SID = re.compile(r'\|s\d+\|')
CJK = re.compile(r'[\u4e00-\u9fff]')
# 允许的缩写/术语/专名（大小写不敏感，整词）
ALLOW = re.compile(
    r'(?<![A-Za-z])(?:PVP|PVE|AOE|DPS|HPS|DOT|HOT|BOSS|BETA|TBC|WOTLK|WOD|RAIDBOTS|DISCORD|WCL'
    r'|GCD|CD|AP|SP|HP|MP|XP|NPC|OMEN|RDF|AH|TANK|HEALER)(?![A-Za-z])', re.I)
# 整段就是标记的行（races 型）直接跳过
SKIP_TYPES = {'races'}

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
            if k in ('t', 'key', 'icon', 'side', 'mark', 'race', 'bg'):
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


hits = []
for spec in sorted(EN):
    tr = load(spec)
    tmap = {s.get('key'): s for s in (tr.get('sections') or [])}
    for sec in EN[spec].get('sections', []):
        tsec = tmap.get(sec.get('key'))
        cf = (tsec or {}).get('flow', []) or []
        for i, e in enumerate(sec.get('flow', [])):
            t = e.get('t')
            if t in SKIP_TYPES:
                continue
            cc = clean(text_of(cf[i])) if i < len(cf) else ''
            if not cc:
                continue
            stripped = ALLOW.sub(' ', cc)
            runs = []
            for m in re.finditer(r'[A-Za-z][A-Za-z\-\'\. ]*[A-Za-z]', stripped):
                seg = m.group(0).strip()
                # 掐掉首尾空格与悬垂标点
                seg = re.sub(r'[\.\-\' ]+$', '', seg).strip()
                if len(seg) < 2:
                    continue
                # 必须与中文相邻（前后 4 字内有 CJK）才算「夹生」
                a = max(0, m.start() - 4)
                b = min(len(stripped), m.end() + 4)
                near = stripped[a:m.start()] + stripped[m.end():b]
                if CJK.search(near):
                    runs.append(seg)
            if runs:
                ec = clean(text_of(e))
                hits.append((spec, sec.get('key'), i, t, ec, cc, runs))

w('########## ② 中英夹杂（CJK 相邻英文实词）命中元素数 = %d ##########' % len(hits))
for spec, key, i, t, ec, cc, runs in hits:
    w('[%s / %s #%d t=%s]' % (spec, key, i, t))
    w('   latin: %s' % runs)
    # 打印每个 run 的上下文
    for r in runs:
        p = cc.find(r)
        if p >= 0:
            w('     …%s…' % cc[max(0, p - 22):p + len(r) + 22])
    w('   EN: %s' % ec[:200])
    w('   CN: %s' % cc[:200])

with io.open(REPORT, 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(OUT) + '\n')
print('report written: %s  (hits=%d)' % (REPORT, len(hits)))
