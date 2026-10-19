# -*- coding: utf-8 -*-
"""全量拉取 Data_DungeonQuests 中 419 个任务页的评论（&comments SEO 出口）。
断点续传：已有 _wh_q_comments_all.json 的键跳过。"""
import json
import re
import time

from curl_cffi import requests

PROXIES = {'http': 'http://127.0.0.1:7897', 'https': 'http://127.0.0.1:7897'}
OUT = '_wh_q_comments_all.json'
notes = json.load(open('_q_notes_map.json', encoding='utf-8'))
ids = []
seen = set()
for dun, rows in notes.items():
    for r in rows:
        if r['id'] not in seen:
            seen.add(r['id'])
            ids.append(r['id'])
print('unique ids:', len(ids))

try:
    out = json.load(open(OUT, encoding='utf-8'))
except Exception:
    out = {}

BACKOFFS = [15, 25, 35, 45]


def fetch(q):
    for attempt, wait in enumerate([0] + BACKOFFS):
        if wait:
            print('  backoff', wait, 's')
            time.sleep(wait)
        try:
            r = requests.get('https://www.wowhead.com/forever/quest=%d&comments' % q,
                             proxies=PROXIES, impersonate='chrome110', timeout=30)
            if r.status_code == 403:
                continue
            m = re.search(r'lv_comments0 = \[(.*?)\];\n', r.text, re.S)
            rows = []
            if m:
                seg = '[' + m.group(1) + ']'
                try:
                    arr = json.loads(seg)
                except Exception:
                    arr = []
                for c in arr:
                    if c.get('deleted'):
                        continue
                    rows.append({
                        'user': c.get('user'),
                        'rating': c.get('rating'),
                        'date': (c.get('date') or '')[:10],
                        'body': re.sub(r'\s+', ' ', c.get('body') or '')[:600],
                    })
            return rows
        except Exception as e:
            print('  err', e)
    return None  # 放弃（网络层）


done = 0
for i, q in enumerate(ids):
    if str(q) in out:
        continue
    rows = fetch(q)
    if rows is None:
        out[str(q)] = []
        print(q, 'GIVEUP', i + 1, '/', len(ids))
    else:
        out[str(q)] = rows
        if rows:
            print(q, len(rows), i + 1, '/', len(ids))
    done += 1
    if done % 20 == 0:
        json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('--- checkpoint', i + 1)
    time.sleep(1.0)

json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
n_with = sum(1 for v in out.values() if v)
print('saved. quests with comments:', n_with, '/', len(out))
