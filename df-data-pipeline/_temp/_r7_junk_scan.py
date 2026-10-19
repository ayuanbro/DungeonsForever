# -*- coding: utf-8 -*-
"""第七轮 · 「真漏网」+「中英夹杂」全量复扫（JSON 值域，最全口径）。

在 _r7_mixed.py 基础上放宽：不仅报「中文相邻英文」，还报**值域里任何独立英文串**——
后者即「整段未译」的候选漏网（真漏网）。排除 |sID| 占位、结构键、缩写白名单。
输出：_temp/_r7_junk_scan.txt
"""
import io
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
EN = json.load(io.open(os.path.join(HERE, '_cg_parsed.json'), encoding='utf-8'))
TD = os.path.join(HERE, '_cg_trans')
OUT = os.path.join(HERE, '_r7_junk_scan.txt')

SID = re.compile(r'\|s\d+\|')
CJK = re.compile(r'[\u4e00-\u9fff]')
ALLOW = re.compile(
    r'(?<![A-Za-z])(?:PVP|PVE|AOE|DPS|HPS|DOT|HOT|BOSS|BETA|TBC|WOTLK|WOD|RAIDBOTS|DISCORD|WCL'
    r'|GCD|CD|AP|SP|HP|MP|XP|NPC|OMEN|RDF|AH|TANK|HEALER)(?![A-Za-z])', re.I)
SKIP_TYPES = {'races'}
RUN = re.compile(r'[A-Za-z][A-Za-z\-\'\. ]*[A-Za-z]')
# 与 fc_guide.is_junk_element 同口径：p/h4 的值为空或解析垃圾字面量 → 该元素被 drop_junk 丢弃，
# 不计入「真漏网」（这些垃圾不进产物）。
JUNK_VALS = {'false', 'true', 'nil', 'null', 'none', 'undefined'}


def is_junk(el):
    if not isinstance(el, dict) or el.get('t') not in ('p', 'h4'):
        return False
    v = el.get('v')
    if not isinstance(v, str):
        return False
    nv = v.strip().lower()
    return nv == '' or nv in JUNK_VALS


def w_(s=''):
    OUTL.append(s)


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


OUTL = []
mixed = []
standalone = []
for spec in sorted(EN):
    tr = load(spec)
    tmap = {s.get('key'): s for s in (tr.get('sections') or [])}
    for sec in EN[spec].get('sections', []):
        tsec = tmap.get(sec.get('key'))
        cf = (tsec or {}).get('flow', []) or []
        for i, e in enumerate(sec.get('flow', [])):
            if e.get('t') in SKIP_TYPES:
                continue
            ce = cf[i] if i < len(cf) else None
            if is_junk(e) or is_junk(ce):     # fc_guide drop_junk 会把这些垃圾丢弃
                continue
            cc = clean(text_of(cf[i])) if i < len(cf) else ''
            if not cc:
                continue
            stripped = ALLOW.sub(' ', cc)
            for m in RUN.finditer(stripped):
                seg = re.sub(r'[\.\-\' ]+$', '', m.group(0).strip()).strip()
                if len(seg) < 2:
                    continue
                a = max(0, m.start() - 4)
                b = min(len(stripped), m.end() + 4)
                near = stripped[a:m.start()] + stripped[m.end():b]
                rec = (spec, sec.get('key'), i, e.get('t'), seg, cc)
                if CJK.search(near):
                    mixed.append(rec)
                else:
                    standalone.append(rec)

w_('===== ① 中英夹杂（CJK 相邻英文实词）=====')
w_('命中段数 = %d' % len(mixed))
for spec, key, i, t, seg, cc in mixed[:40]:
    w_('  [%s/%s#%d] %s   …%s…' % (spec, key, i, seg, cc[:80]))
w_('')
w_('===== ② 真漏网候选（值域内独立英文串，非 CJK 相邻）=====')
w_('命中段数 = %d' % len(standalone))
for spec, key, i, t, seg, cc in standalone[:60]:
    w_('  [%s/%s#%d] %s   …%s…' % (spec, key, i, seg, cc[:100]))
w_('')
w_('★ 判定：中英夹杂=%d  真漏网候选=%d  → %s'
   % (len(mixed), len(standalone),
      'PASS' if (len(mixed) == 0 and len(standalone) == 0) else '需核对'))

text = '\n'.join(OUTL) + '\n'
io.open(OUT, 'w', encoding='utf-8', newline='\n').write(text)
print(text)
