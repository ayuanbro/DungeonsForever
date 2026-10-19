# -*- coding: utf-8 -*-
"""Fetch wowhead /forever/cn quest pages for City of Dalaran quests."""
import os, sys, time
from curl_cffi import requests as cr

HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Upgrade-Insecure-Requests': '1',
    'Referer': 'https://www.wowhead.com/forever/cn',
}

QUESTS = [92489, 92458, 92456, 96986, 96988, 96984, 96987,
          92432, 92459, 93680, 92434, 97287]

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cod_quests')
os.makedirs(OUT, exist_ok=True)

def main():
    s = cr.Session(impersonate='chrome110',
                   proxies={'http': 'http://127.0.0.1:7897', 'https': 'http://127.0.0.1:7897'},
                   headers=HEADERS, timeout=30)
    for qid in QUESTS:
        path = os.path.join(OUT, f'q{qid}.html')
        if os.path.exists(path) and os.path.getsize(path) > 20000:
            print(qid, 'cached')
            continue
        url = f'https://www.wowhead.com/forever/cn/quest={qid}'
        for attempt in range(3):
            try:
                r = s.get(url)
                if r.status_code == 200 and len(r.content) > 20000 and b'2025' not in r.content[:1000]:
                    with open(path, 'wb') as f:
                        f.write(r.content)
                    print(qid, 'OK', len(r.content))
                    break
                print(qid, 'attempt', attempt, 'status', r.status_code, 'len', len(r.content))
            except Exception as e:
                print(qid, 'attempt', attempt, 'ERR', e)
            time.sleep(5)
        else:
            print(qid, 'FAILED')
        time.sleep(1.5)

if __name__ == '__main__':
    main()
