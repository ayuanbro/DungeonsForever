# -*- coding: utf-8 -*-
"""抓 wowhead forever/cn 物品分类页：杂项 - 坐骑 列表页（带预热/重试/多指纹）"""
import re, json, sys, io, time
from curl_cffi import requests as cr

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Upgrade-Insecure-Requests': '1',
    'Referer': 'https://www.wowhead.com/forever/cn',
}

URL = 'https://www.wowhead.com/forever/cn/items/miscellaneous/mounts'

def try_session(imp):
    s = cr.Session(impersonate=imp,
                   proxies={'http': 'http://127.0.0.1:7897', 'https': 'http://127.0.0.1:7897'},
                   headers=HEADERS)
    # 预热：先敲一下 cn 首页拿 cookie
    try:
        w = s.get('https://www.wowhead.com/forever/cn', timeout=30)
        print(f'  [{imp}] warmup status={w.status_code} len={len(w.text)}')
    except Exception as e:
        print(f'  [{imp}] warmup error: {e}')
    for attempt in range(2):
        try:
            r = s.get(URL, timeout=45)
            print(f'  [{imp}] attempt{attempt} status={r.status_code} len={len(r.text)}')
            if r.status_code == 200 and len(r.text) > 20000:
                return r.text
        except Exception as e:
            print(f'  [{imp}] attempt{attempt} error: {e}')
        time.sleep(3)
    return None

html = None
for imp in ('chrome110', 'chrome124', 'chrome116', 'edge101'):
    print('try impersonate:', imp)
    html = try_session(imp)
    if html:
        print('OK with', imp)
        break

if not html:
    print('ALL FAILED')
    sys.exit(1)

with open('_temp/whb_mounts_items.html', 'w', encoding='utf-8') as f:
    f.write(html)

m = re.search(r'new Listview\(\{[^{}]*?template:\s*[\'"]item[\'"]\s*,.*?id:\s*[\'"]items[\'"]\s*,\s*data:\s*(\[.*?\])\s*\}\s*\);', html, re.S)
print('listview match:', bool(m))
if m:
    data = json.loads(m.group(1))
    print('rows:', len(data))
    print(json.dumps(data[:3], ensure_ascii=False, indent=1)[:1500])
