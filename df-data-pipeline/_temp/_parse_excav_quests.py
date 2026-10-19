# -*- coding: utf-8 -*-
"""挖掘场任务页 → 18 字段行草稿。输出 JSON 供落库脚本消费。"""
import re, json, sys, io
import html as H
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

QIDS = [95772, 95647, 95646, 98815, 95795, 95697, 95664, 95810]

out = {}
for qid in QIDS:
    t = open('_wh_quest_%d.html' % qid, encoding='utf-8', errors='replace').read()
    m = re.search(r'\$\.extend\(g_quests\[%d\], (\{.*?\})\);' % qid, t)
    jq = json.loads(m.group(1)) if m else {}
    d = re.search(r'WH\.markup\.printHtml\("(\[ul\].*?)", "infobox', t)
    diff = None
    sharable = None
    if d:
        bb = d.group(1)
        mm = re.search(r'Difficulty: \[color=q10\](\d+).*?\[color=r1\](\d+).*?\[color=r2\](\d+).*?\[color=r3\](\d+).*?\[color=r4\](\d+)', bb)
        if mm:
            diff = [int(x) for x in mm.groups()]
        if 'Sharable' in bb and 'Not Sharable' not in bb:
            sharable = True
        elif 'Not Sharable' in bb:
            sharable = False
        else:
            sharable = None
    i = t.find('id="main-contents"')
    seg = t[i:i+14000] if i >= 0 else ''
    seg = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', seg, flags=re.S)
    txt = re.sub(r'<[^>]+>', '|', seg)
    txt = H.unescape(txt)
    txt = re.sub(r'\|+', ' | ', txt)
    txt = re.sub(r'\s+', ' ', txt)
    # 目标句（Links 之后、Description 之前）
    obj = re.search(r'Links \| \| (.+?) \| \| Description', txt)
    objectives = obj.group(1) if obj else None
    out[qid] = {
        'json': jq,
        'diff': diff,
        'sharable': sharable,
        'objectives': objectives,
    }
    print('==', qid, jq.get('name'), '==')
    print(json.dumps(out[qid], ensure_ascii=False))
    print()

json.dump(out, open('_excav_quests_parsed.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
