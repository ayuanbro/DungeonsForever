# -*- coding: utf-8 -*-
"""以英文为锚 v4（最终版）：按 section key 配对（与 fc_guide.find_cn_sec 同口径），
再按 flow 元素索引配对，检查「英文含 Forever → 中文须含『无限』」。"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
EN = json.load(open(os.path.join(HERE, '_cg_parsed.json'), encoding='utf-8'))
TD = os.path.join(HERE, '_cg_trans')
# ★ 只认大写 Forever（版本名）。小写 forever 是副词（"you'll be looking at it forever"），
#   全 27 页统计无反例：152 处大写 = 版本名 / 3 处小写 = 副词。
FW = re.compile(r'Forever')


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


real, fallback, nostruct, flen = [], [], [], []

for spec in sorted(EN):
    tf = os.path.join(TD, spec + '.json')
    tr = json.load(open(tf, encoding='utf-8')) if os.path.exists(tf) else {}
    tmap = {s.get('key'): s for s in (tr.get('sections') or [])}
    for sec in EN[spec].get('sections', []):
        key = sec.get('key')
        tsec = tmap.get(key)
        if tsec is None:
            nostruct.append((spec, key, 'no matching section'))
            continue
        ef, cf = sec.get('flow', []), tsec.get('flow', []) or []
        if len(ef) != len(cf):
            flen.append((spec, key, len(ef), len(cf)))
        for i, e in enumerate(ef):
            etext = text_of(e)
            if not FW.search(etext):
                continue
            ctext = text_of(cf[i]) if i < len(cf) else None
            if ctext is None:
                fallback.append((spec, key, i, e.get('t'), etext))
            elif '无限' not in ctext:
                real.append((spec, key, i, e.get('t'), etext, ctext))

print('★ 真漏网 =', len(real), ' | 译文缺失 =', len(fallback), ' | 无对应section =', len(nostruct))
print('★ flow 长度不一致 =', len(flen), flen)
print('★ 无匹配section明细:', nostruct)
print()
print('===== A. 真漏网（英文有 Forever，中文没「无限」）=====')
for n, (spec, key, i, t, e, c) in enumerate(real, 1):
    print('%2d. [%s / %s #%d t=%s]' % (n, spec, key, i, t))
    print('    EN:', e[:165].replace('\n', '\\n'))
    print('    CN:', c[:165].replace('\n', '\\n'))
print()
print('===== B. 译文缺失（界面回落显示英文）=====')
for n, (spec, key, i, t, e) in enumerate(fallback, 1):
    print('%2d. [%s / %s #%d t=%s] %s' % (n, spec, key, i, t, e[:140].replace('\n', '\\n')))
print()
print('===== C. 误译词归类 =====')
tal = {}
for _, _, _, _, _, c in real:
    for w in ['永驻', '永駐', '永燃', '永夜', '永昼', '怀旧服', '怀旧', '资料片', '经典赛季', '永远的魔兽世界', 'Forefore']:
        if w in c:
            tal[w] = tal.get(w, 0) + 1
print(' ', tal if tal else '(见 A 组逐条)')
