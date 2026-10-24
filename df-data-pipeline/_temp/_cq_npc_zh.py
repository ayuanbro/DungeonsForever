import io
import json
import os
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'Core', 'Data', 'Data_ClassQuest.lua')
OUT = os.path.join(ROOT, '_temp', '_cq_npc_zh.json')
PROXY = 'http://127.0.0.1:7897'
URL = 'https://nether.wowhead.com/tooltip/npc/%d?dataEnv=1&locale=zhCN'


def npc_ids():
    s = io.open(SRC, encoding='utf-8').read()
    ids = {}
    for m in re.finditer(r'\{\s*(\d{2,7})\s*,\s*"((?:[^"\\]|\\.)*)"', s):
        nid = int(m.group(1))
        name = m.group(2)
        if nid >= 100:
            ids.setdefault(nid, name)
    return ids


def fetch(nid):
    op = urllib.request.build_opener(urllib.request.ProxyHandler({'http': PROXY, 'https': PROXY}))
    req = urllib.request.Request(URL % nid, headers={'User-Agent': 'Mozilla/5.0'})
    for _ in range(3):
        try:
            with op.open(req, timeout=20) as r:
                data = json.loads(r.read().decode('utf-8'))
            name = data.get('name') or ''
            if name:
                return nid, name
            return nid, None
        except Exception:
            time.sleep(0.6)
    return nid, None


def main():
    ids = npc_ids()
    print('unique npc: %d' % len(ids))
    old = {}
    if os.path.exists(OUT):
        try:
            old = json.load(io.open(OUT, encoding='utf-8'))
        except Exception:
            old = {}
    todo = [n for n in sorted(ids) if str(n) not in old]
    print('need fetch: %d (cached %d)' % (len(todo), len(old)))
    got = dict(old)
    done = [0]
    with ThreadPoolExecutor(max_workers=8) as ex:
        for nid, name in ex.map(fetch, todo):
            done[0] += 1
            if name:
                got[str(nid)] = name
            if done[0] % 40 == 0:
                print('  %d/%d' % (done[0], len(todo)))
                io.open(OUT, 'w', encoding='utf-8', newline='\n').write(
                    json.dumps(got, ensure_ascii=False, indent=0, sort_keys=True))
    io.open(OUT, 'w', encoding='utf-8', newline='\n').write(
        json.dumps(got, ensure_ascii=False, indent=0, sort_keys=True))
    miss = [n for n in ids if str(n) not in got]
    print('done: %d / %d, miss %d' % (len(got), len(ids), len(miss)))
    if miss:
        print('miss ids:', miss[:30])


main()
