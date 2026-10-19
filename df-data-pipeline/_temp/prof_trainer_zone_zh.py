# -*- coding: utf-8 -*-
"""提取 Data_ProfTrainers loc 里的英文区域/子区名，QuestieDB zone 表补中文。
输出 _trainers_zone_zh.json（en -> zh）。"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'questie'))
from questie_extract import decode_b64  # noqa: E402
import base64  # noqa: E402


def as_text(v):
    if isinstance(v, bytes):
        return v.decode('utf-8', 'replace')
    return v if isinstance(v, str) else None


TOC = os.path.join(HERE, 'questie', 'forever', 'QuestieDB', 'QuestieDB_Forever.toc')
LUA = os.path.join(HERE, '..', 'Core', 'Data', 'Data_ProfTrainers.lua')
OUT = os.path.join(HERE, '_trainers_zone_zh.json')

src = open(LUA, encoding='utf-8').read()
ens = set()
for m in re.finditer(r'loc_en = "([^"]*)"', src):
    for part in m.group(1).split(', '):
        part = re.sub(r'\s*\([^)]*\)\s*$', '', part).strip()
        if part:
            ens.add(part)
print('english zone/sub strings: %d' % len(ens))

txt = open(TOC, encoding='utf-8', errors='replace').read()
ms = re.findall(r'^## X-Object-(\d+)-S:\s*(\S+)\s*$', txt, re.M)
print('object rows:', len(ms))

out = {}
for m in re.finditer(r'^## X-Quest-(\d+)-(\d+):\s*(\S+)\s*$', txt, re.M):
    pass

zones = {}
for eid, val in ms:
    try:
        row = decode_b64(val)
    except Exception:
        continue
    if isinstance(row, dict):
        nm = as_text(row.get(1))
        if nm:
            zones[nm] = eid

for e in sorted(ens):
    if e in zones:
        out[e] = None

json.dump(sorted(out), open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print('need-zh count: %d' % len(out))
print(sorted(out)[:20])
