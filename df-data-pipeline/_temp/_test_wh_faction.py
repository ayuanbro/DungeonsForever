# -*- coding: utf-8 -*-
"""探测：nether tooltip 端点是否可用、是否带阵营字段。"""
import json
from curl_cffi import requests as cr

PROXIES = {'http': 'http://127.0.0.1:7897', 'https': 'http://127.0.0.1:7897'}
for branch in ('wotlk', 'classic', 'retail'):
    url = 'https://nether.wowhead.com/%s/tooltip/npc/1685' % branch
    try:
        r = cr.get(url, impersonate='chrome', proxies=PROXIES, timeout=40)
        print(branch, r.status_code, len(r.text))
        if r.status_code == 200:
            try:
                d = json.loads(r.text)
                print(json.dumps(d, ensure_ascii=False)[:800])
            except Exception as e:
                print('json err', e, r.text[:300])
    except Exception as e:
        print(branch, 'ERR', repr(e)[:120])
