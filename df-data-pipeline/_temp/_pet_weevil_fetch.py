# -*- coding: utf-8 -*-
import re, json, sys
from curl_cffi import requests as cr

HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Upgrade-Insecure-Requests': '1',
    'Referer': 'https://www.wowhead.com/forever/cn',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-User': '?1',
}
s = cr.Session(impersonate='chrome110',
               proxies={'http': 'http://127.0.0.1:7897', 'https': 'http://127.0.0.1:7897'},
               headers=HEADERS)

def get(url, tag, tries=('chrome110','chrome120','chrome124','edge101','safari15_5')):
    for imp in tries:
        try:
            r = s.get(url, timeout=40, impersonate=imp)
        except TypeError:
            r = s.get(url, timeout=40)
        print(f'[{tag}] {imp} -> {r.status_code} {len(r.text)}', file=sys.stderr)
        if r.status_code == 200 and len(r.text) > 50000:
            return r.text
    return None

TARGETS = {
    'item': 'https://www.wowhead.com/forever/cn/item=280456',
    'quest': 'https://www.wowhead.com/forever/cn/quest=93176',
}
for tag, url in TARGETS.items():
    html = get(url, tag)
    if not html:
        print(f'### {tag} FAILED'); continue
    open(f'_temp/_pet_weevil_{tag}.html', 'w', encoding='utf-8').write(html)
    m = re.search(r'<title>(.*?)</title>', html, re.S)
    print(f'### {tag} TITLE:', m.group(1).strip() if m else None)
    loads = re.findall(r'WH\.markup\.printHtml\(\s*("(?:[^"\\]|\\.)*")', html)
    print(f'### {tag} printHtml blocks:', len(loads))
    for i, raw in enumerate(loads):
        try:
            txt = json.loads(raw)
        except Exception:
            continue
        print(f'--- {tag} block {i} (len={len(txt)}) ---')
        print(txt[:6000])
