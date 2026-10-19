# -*- coding: utf-8 -*-
"""扩展 _ext_pre_ids.json：把总览里仍显示「任务 #id」的节点任务并入 ext 详情段清单。

输入：_temp/_ext_pre_ids.json（现值）+ _temp/_detected_unnamed.txt（实机总览实测到的无名字任务 id）
       + _temp/_ww_quests.json（仅取 prev/next 关系做闭包）
输出：_temp/_ext_pre_ids.json（备份为 .bak2）
"""
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, '_ext_pre_ids.json')
cur = json.load(io.open(P, encoding='utf-8'))['ids']
det = [int(x) for x in io.open(os.path.join(HERE, '_detected_unnamed.txt'), encoding='utf-8').read().split(',') if x.strip()]
qs = {q['id']: q for q in json.load(io.open(os.path.join(HERE, '_ww_quests.json'), encoding='utf-8'))['quests']}

rev = {}
for qid, q in qs.items():
    t = q.get('tmp') or {}
    n = t.get('next') or q.get('next')
    if isinstance(n, int):
        rev.setdefault(n, set()).add(qid)


def links(qid):
    q = qs.get(qid) or {}
    t = q.get('tmp') or {}
    out = set()
    for src in (t.get('prev'), q.get('prev')):
        if isinstance(src, list):
            out |= {x for x in src if isinstance(x, int)}
    return out | rev.get(qid, set())


seed = set(cur) | set(det)
seen = set(x for x in seed if x in qs)
stack = list(seen)
while stack:
    c = stack.pop()
    for p in links(c):
        if p not in seen and p in qs:
            seen.add(p)
            stack.append(p)

out = sorted(seen)
io.open(P + '.bak2', 'w', encoding='utf-8', newline='').write(
    json.dumps({'ids': cur}, ensure_ascii=False, indent=0))
io.open(P, 'w', encoding='utf-8', newline='').write(
    json.dumps({'ids': out}, ensure_ascii=False, indent=0))
print('before=%d detected=%d after=%d' % (len(cur), len(det), len(out)))
