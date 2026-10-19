# -*- coding: utf-8 -*-
"""洛丹伦废墟：抓新闻页 / 攻略页原始 HTML（复用已打通的抓取姿势）。"""
import os
import time

from curl_cffi import requests as cr

PROXY = 'http://127.0.0.1:7897'
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '_rl_raw')
os.makedirs(OUT, exist_ok=True)

URLS = {
    'news': 'https://www.wowhead.com/forever/cn/news/the-ruins-of-lordaeron-new-dungeon-walkthrough-for-wow-forever-383021',
    'guide': 'https://www.wowhead.com/forever/cn/guide/ruins-of-lordaeron-dungeon-overview-location-rewards',
    'zone': 'https://www.wowhead.com/forever/cn/zone=16611/ruins-of-lordaeron',
}

HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Upgrade-Insecure-Requests': '1',
    'Referer': 'https://www.wowhead.com/forever/cn',
}
s = cr.Session(impersonate='chrome110', proxies={'http': PROXY, 'https': PROXY}, headers=HEADERS)

for k, url in URLS.items():
    dst = os.path.join(OUT, k + '.html')
    for attempt in range(4):
        if attempt:
            time.sleep(20)
        try:
            r = s.get(url, timeout=40)
        except Exception as e:
            print('[err] %s %s' % (k, str(e)[:90]))
            continue
        print('[%s] %s len=%d' % (k, r.status_code, len(r.text)))
        if r.status_code == 200 and len(r.text) > 20000:
            with open(dst, 'w', encoding='utf-8') as f:
                f.write(r.text)
            break
    time.sleep(6)
