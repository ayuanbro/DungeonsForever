# -*- coding: utf-8 -*-
"""拉取挖掘场 13 个 forever 任务页的评论（&comments SEO 出口，lv_comments0 JSON）。"""
import json
import re
import time

from curl_cffi import requests

PROXIES = {'http': 'http://127.0.0.1:7897', 'https': 'http://127.0.0.1:7897'}
IDS = [469, 95646, 95647, 95664, 95682, 95697, 95737, 95772, 95809, 95810, 98815, 98823, 98824]


def unesc(s):
    return s.replace('\\/', '/').replace('\\"', '"').replace('\\r\\n', '\n')


out = {}
for q in IDS:
    try:
        r = requests.get('https://www.wowhead.com/forever/quest=%d&comments' % q,
                         proxies=PROXIES, impersonate='chrome110', timeout=30)
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
                    'body': re.sub(r'\s+', ' ', c.get('body') or '')[:500],
                })
        out[str(q)] = rows
        print(q, len(rows))
    except Exception as e:
        print(q, 'FAIL', e)
        out[str(q)] = []
    time.sleep(1.0)

json.dump(out, open('_wh_q_comments_excavation.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('saved')
