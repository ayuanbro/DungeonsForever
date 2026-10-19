# -*- coding: utf-8 -*-
"""职业排行页调研：抓 wowhead /forever 的 tier list 三页，落原始 HTML 到 _temp/_tier_probe/。"""
import os
import sys
import time

PROXY = 'http://127.0.0.1:7897'
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '_tier_probe')

URLS = {
    'dps': 'https://www.wowhead.com/forever/cn/guide/classes/tier-lists/dps-pve-rankings',
    'tank': 'https://www.wowhead.com/forever/cn/guide/classes/tier-lists/tank-pve-rankings',
    'healer': 'https://www.wowhead.com/forever/cn/guide/classes/tier-lists/healer-pve-rankings',
}

from curl_cffi import requests as cr

os.makedirs(OUT, exist_ok=True)
proxies = {'http': PROXY, 'https': PROXY}
HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Upgrade-Insecure-Requests': '1',
    'Referer': 'https://www.wowhead.com/forever/cn',
}
s = cr.Session(impersonate='chrome110', proxies=proxies, headers=HEADERS)

force = '--force' in sys.argv
for k, url in URLS.items():
    dst = os.path.join(OUT, k + '.html')
    if not force and os.path.exists(dst) and os.path.getsize(dst) > 20000:
        print('[cached] %s %d' % (k, os.path.getsize(dst)))
        continue
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
    time.sleep(8)
