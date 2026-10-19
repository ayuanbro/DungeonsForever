# -*- coding: utf-8 -*-
"""以英文为锚 v2：把 flow 结构摊平成叶子文本序列，按序配对英文/中文。

规避 tb 的两种形态（英文 row = {"cells":[...]}，译文 row = [...]）。
"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
EN = json.load(open(os.path.join(HERE, '_cg_parsed.json'), encoding='utf-8'))
TD = os.path.join(HERE, '_cg_trans')
FW = re.compile(r'forever', re.I)


def leaves(o, out):
    """按插入顺序摊平出所有字符串叶子（跳过 title 键）。"""
    if isinstance(o, str):
        out.append(o)
    elif isinstance(o, list):
        for x in o:
            leaves(x, out)
    elif isinstance(o, dict):
        for k, v in o.items():
            if k == 'title':
                continue
            leaves(v, out)


real = []      # 英文含 Forever、中文存在但不含「无限」
fallback = []  # 英文含 Forever、中文缺失（界面回落英文）
count_mismatch = []
total_en_forever = 0

for spec in sorted(EN):
    en = EN[spec]
    tf = os.path.join(TD, spec + '.json')
    tr = json.load(open(tf, encoding='utf-8')) if os.path.exists(tf) else {}
    for si, sec in enumerate(en.get('sections', [])):
        tsec = (tr.get('sections') or [])
        tsec = tsec[si] if si < len(tsec) else {}
        ef, cf = [], []
        leaves(sec.get('flow', []), ef)
        leaves(tsec.get('flow', []), cf)
        if len(ef) != len(cf):
            count_mismatch.append((spec, si, len(ef), len(cf)))
        for i, e in enumerate(ef):
            if not FW.search(e):
                continue
            total_en_forever += 1
            c = cf[i] if i < len(cf) else None
            if c is None:
                fallback.append((spec, si, i, e))
            elif '无限' not in c:
                real.append((spec, si, i, e, c))

print('英文含 Forever 的叶子总数 =', total_en_forever)
print('★ 中文存在但缺「无限」= ', len(real))
print('★ 中文缺失（回落英文）= ', len(fallback))
print('段落叶子数不一致的 section = ', len(count_mismatch), count_mismatch[:8])
print()
print('===== A. 真漏网（中文有内容但没「无限」）=====')
for spec, si, i, e, c in real:
    print('[%s §%d #%d]' % (spec, si, i))
    print('  EN :', e[:150].replace('\n', '\\n'))
    print('  CN :', c[:150].replace('\n', '\\n'))
print()
print('===== B. 译文缺失（界面会显示英文原文）=====')
for spec, si, i, e in fallback:
    print('[%s §%d #%d]' % (spec, si, i))
    print('  EN :', e[:130].replace('\n', '\\n'))
print()
print('===== C. 漏网中文里出现的所有疑似版本名片段 =====')
pat = re.compile(r'《[^》]{0,14}》|[\u4e00-\u9fff]{0,3}(?:服|赛季|賽季|资料片|資料片|版本)')
tal = {}
for _, _, _, _, c in real:
    for m in pat.finditer(c):
        tal[m.group(0)] = tal.get(m.group(0), 0) + 1
for k, v in sorted(tal.items(), key=lambda kv: -kv[1]):
    print(' ', repr(k), v)
