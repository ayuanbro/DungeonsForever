# -*- coding: utf-8 -*-
"""按 NPC ID 从 cn.wowhead 批量抓中文名（r.jina.ai 代理）。输出 _trainers_zh.json。"""
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
PROXY = 'http://127.0.0.1:7897'
OUT = os.path.join(HERE, '_trainers_zh.json')

ids = json.load(open(os.path.join(HERE, '_trainers_npcid.json'), encoding='utf-8'))
done = {}
if os.path.exists(OUT):
    try:
        done = json.load(open(OUT, encoding='utf-8'))
    except Exception:
        done = {}
todo = sorted(set(ids.values()) - set(k for k, v in done.items() if v))
print('total ids: %d, todo: %d' % (len(set(ids.values())), len(todo)))

pat = re.compile(r'^Title:\s*(.+?)\s*$', re.M)


def fetch(eid):
    url = 'https://r.jina.ai/https://cn.wowhead.com/npc=%d' % eid
    try:
        r = subprocess.run(
            ['curl', '-s', '-x', PROXY, url, '--max-time', '30'],
            capture_output=True, text=True, timeout=40)
        m = pat.search(r.stdout or '')
        if m:
            t = m.group(1).strip()
            if t and not t.startswith('[') and 'error' not in t.lower() \
                    and 'http' not in t and len(t) <= 30:
                return eid, t
    except Exception:
        pass
    return eid, None


import time
for round_i in range(15):
    if not todo:
        break
    print('round %d: %d ids' % (round_i + 1, len(todo)), flush=True)
    with ThreadPoolExecutor(max_workers=3) as ex:
        for eid, name in ex.map(fetch, todo):
            if name:
                done[eid] = name
    json.dump(done, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    todo = sorted(set(ids.values()) - set(k for k, v in done.items() if v))
    print('  got %d, missing %d' % (len(done), len(todo)), flush=True)
    if todo:
        time.sleep(20)

print('done: %d / %d' % (len(done), len(set(ids.values()))))
