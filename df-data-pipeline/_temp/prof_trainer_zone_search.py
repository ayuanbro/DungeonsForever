# -*- coding: utf-8 -*-
"""45 个未命中 zone enum 的地名 → wowhead 搜索页抓中文（r.jina.ai）。
输出 _trainers_zone_zh2.json（en -> zh）。后台运行。"""
import json
import os
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote

HERE = os.path.dirname(os.path.abspath(__file__))
PROXY = 'http://127.0.0.1:7897'
OUT = os.path.join(HERE, '_trainers_zone_zh2.json')

need = json.load(open(os.path.join(HERE, '_trainers_zone_zh.json'), encoding='utf-8'))
have = json.load(open(os.path.join(HERE, '_trainers_zone_ids.json'), encoding='utf-8'))
todo = [e for e in need if e not in have]
print('todo:', len(todo))

done = {}
if os.path.exists(OUT):
    try:
        done = json.load(open(OUT, encoding='utf-8'))
    except Exception:
        done = {}
todo = [e for e in todo if e not in done]

link = re.compile(r'\[([^\]]+)\]\(/zone=(\d+)[^)]*\)')


def fetch(en):
    url = 'https://r.jina.ai/https://cn.wowhead.com/search?q=%s' % quote(en)
    try:
        r = subprocess.run(['curl', '-s', '-x', PROXY, url, '--max-time', '30'],
                           capture_output=True, text=True, timeout=40)
        m = link.search(r.stdout or '')
        if m:
            return en, m.group(1).strip()
    except Exception:
        pass
    return en, None


for round_i in range(6):
    if not todo:
        break
    print('round %d: %d' % (round_i + 1, len(todo)), flush=True)
    with ThreadPoolExecutor(max_workers=3) as ex:
        for en, zh in ex.map(fetch, todo):
            if zh:
                done[en] = zh
    json.dump(done, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    todo = [e for e in todo if e not in done]
    print('  got %d, missing %d' % (len(done), len(todo)), flush=True)
    if todo:
        time.sleep(15)
print('done: %d' % len(done))
