# -*- coding: utf-8 -*-
"""探索页 · 抓取 Warcraft Tavern「Arcane Barrage Rune」指南（40 本书清单）。
原文落 _fc/cache/tavern_arcane_barrage.html，解析交给后续步骤。
"""
import os
import sys
from curl_cffi import requests

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, '_fc', 'cache')
URL = ('https://www.warcrafttavern.com/wow-classic/guides/'
       'arcane-barrage-rune-guide-season-of-discovery-sod/')
DST = os.path.join(CACHE, 'tavern_arcane_barrage.html')


def main():
    os.makedirs(CACHE, exist_ok=True)
    r = requests.get(URL, impersonate='chrome',
                     proxies={'http': 'http://127.0.0.1:7897',
                              'https': 'http://127.0.0.1:7897'},
                     timeout=90)
    if r.status_code != 200 or len(r.text) < 100000:
        sys.stderr.write('fetch failed: %s %d bytes\n' % (r.status_code, len(r.text)))
        return 1
    with open(DST, 'w', encoding='utf-8') as f:
        f.write(r.text)
    print('saved %d bytes -> %s' % (len(r.text), DST))
    import re
    h = r.text
    print('item links:', len(set(re.findall(r'item=(\d+)', h))))
    print('quest links:', len(set(re.findall(r'quest=(\d+)', h))))
    print('object links:', len(set(re.findall(r'object=(\d+)', h))))
    print('wowhead hrefs sample:', list(set(re.findall(r'href="([^"]*wowhead[^"]*)"', h)))[:8])
    return 0


if __name__ == '__main__':
    sys.exit(main())
