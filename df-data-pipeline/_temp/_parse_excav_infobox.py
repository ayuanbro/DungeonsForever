# -*- coding: utf-8 -*-
"""任务页 infobox：Start/End NPC、side、type、难度。"""
import re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

QIDS = [95772, 95647, 95646, 98815, 95795, 95697, 95664, 95810]
for qid in QIDS:
    t = open('_wh_quest_%d.html' % qid, encoding='utf-8', errors='replace').read()
    d = re.search(r'WH\.markup\.printHtml\("(\[ul\].*?)", "infobox', t)
    bb = d.group(1) if d else ''
    out = {}
    for label in ('Start', 'End'):
        segs = re.findall(label + r': \[url=([^\]]+)\]([^\[]*)', bb)
        out[label] = []
        for url, name in segs:
            nid = re.search(r'npc=(\d+)', url)
            iid = re.search(r'item=(\d+)', url)
            out[label].append(('npc', nid.group(1), name.strip()) if nid else (('item', iid.group(1), name.strip()) if iid else (url, name.strip())))
    side = re.search(r'Side: \[span class=icon-(\w+)\](\w+)', bb) or re.search(r'Side: (None|Alliance|Horde)', bb)
    typ = re.search(r'Type: (\w+)', bb)
    print(qid, '|', out, '| side:', side.group(1) if side else None, '| type:', typ.group(1) if typ else None)
