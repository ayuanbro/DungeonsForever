# -*- coding: utf-8 -*-
"""GQF 需求清单 vs WDB 缓存覆盖率测试"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _gqf_fetch_names import load_needed  # noqa: E402

wdb = json.load(open(os.path.join(HERE, '_wdb_names.json'),
                     encoding='utf-8'))
npcs, quests = load_needed()

# ---- NPC: enUS cache en->id, zhCN cache id->zh ----
en2id, id2zh = {}, {}
for rid, e in wdb["npcs"].items():
    if e.get("en"):
        en2id.setdefault(e["en"], int(rid))
    if e.get("zh"):
        id2zh[int(rid)] = e["zh"]

hit = 0
miss = []
for name in npcs:
    nid = en2id.get(name)
    zh = id2zh.get(nid) if nid else None
    if zh:
        hit += 1
    else:
        miss.append(name)
print("NPC: wdb join 命中 %d/%d；缺口示例: %s"
      % (hit, len(npcs), miss[:10]), flush=True)

# ---- Quest: enUS cache 前缀匹配 en->id ----
enrecs = []
for rid, e in wdb["quests"].items():
    if e.get("en"):
        enrecs.append((int(rid), e["en"]))
    if e.get("en2"):
        enrecs.append((int(rid), e["en2"]))

qhit = 0
qmiss = []
for name in quests:
    cands = [rid for rid, en in enrecs
             if en.lstrip().startswith(name)]
    if cands:
        qhit += 1
    else:
        qmiss.append(name)
print("Quest: wdb 前缀命中 %d/%d；缺口示例: %s"
      % (qhit, len(quests), qmiss[:10]), flush=True)
