# -*- coding: utf-8 -*-
"""职业专精指南：抓 wowhead 无限服指南页原始 HTML，缓存到 _cg_probe/。"""
import argparse
import os
import sys
import time

from curl_cffi import requests as cr

PROXY = 'http://127.0.0.1:7897'
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '_cg_probe')
os.makedirs(OUT, exist_ok=True)

HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Upgrade-Insecure-Requests': '1',
    'Referer': 'https://www.wowhead.com/forever/cn',
}


def fetch(key, url, force=False):
    dst = os.path.join(OUT, key + '.html')
    if os.path.exists(dst) and not force:
        print('[cache] %s %d' % (key, os.path.getsize(dst)))
        return dst
    s = cr.Session(impersonate='chrome110',
                   proxies={'http': PROXY, 'https': PROXY}, headers=HEADERS)
    for attempt in range(4):
        if attempt:
            time.sleep(15 + 10 * attempt)
        try:
            r = s.get(url, timeout=45)
        except Exception as e:
            print('[err] %s %s' % (key, str(e)[:90]))
            continue
        print('[%s] %s len=%d' % (key, r.status_code, len(r.text)))
        if r.status_code == 200 and len(r.text) > 20000:
            with open(dst, 'w', encoding='utf-8') as f:
                f.write(r.text)
            return dst
    return None


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--force', action='store_true')
    ap.add_argument('urls', nargs='*')
    a = ap.parse_args()
    if not a.urls:
        a.urls = ['balance|https://www.wowhead.com/forever/cn/guide/classes/druid/balance/overview-pve-dps']
    for item in a.urls:
        key, _, url = item.partition('|')
        p = fetch(key, url, a.force)
        print('  ->', p)
        time.sleep(5)
