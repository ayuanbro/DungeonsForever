# -*- coding: utf-8 -*-
"""抓 wowhead forever 新闻页到本地缓存（一次性摸底用）。"""
import os
import sys
import json
from curl_cffi import requests

URL = 'https://www.wowhead.com/forever/cn/news/the-ruins-of-lordaeron-new-dungeon-walkthrough-for-wow-forever-383021'
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '_rl_page.html')
JOUT = os.path.join(HERE, '_rl_page.json')

PROXY = {'http': 'http://127.0.0.1:7897', 'https': 'http://127.0.0.1:7897'}


def main():
    r = requests.get(URL, impersonate='chrome', proxies=PROXY, timeout=45)
    print('status', r.status_code, 'len', len(r.content))
    r.raise_for_status()
    html = r.content.decode('utf-8', 'replace')
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(html)
    print('saved', OUT)


if __name__ == '__main__':
    main()
