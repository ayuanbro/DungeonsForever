# -*- coding: utf-8 -*-
"""抓稀有怪 zhCN 名 + 影牙物品钉的 itemID（fc 页缓存 → wowhead）。"""
import re, json, time, os
from curl_cffi import requests

HERE = os.path.dirname(os.path.abspath(__file__))
PROXY = {'http': 'http://127.0.0.1:7897', 'https': 'http://127.0.0.1:7897'}

out = {}
# 1) wowhead zhCN NPC 名
for npc in (6669, 556, 2142, 3224):
    url = 'https://www.wowhead.com/zh-cn/npc=%d' % npc
    r = requests.get(url, impersonate='chrome110', proxies=PROXY, timeout=40)
    m = re.search(r'<title>([^<]+?)\s*[-—] ', r.text or '')
    name = m.group(1) if m else '?'
    # wowhead 页头 name JSON
    m2 = re.search(r'"name":"([^"]+)"', r.text or '')
    out[npc] = name
    print(npc, '->', name, '| json:', (m2.group(1) if m2 else '-'))
    time.sleep(1.5)

# 2) 影牙 object 段的 itemID
d = open(os.path.join(HERE, '_ref/dg_shadowfang-keep.html'), encoding='utf-8', errors='replace').read()
for sid in ('jordan-s-smithing-hammer', 'the-book-of-ur'):
    i = d.find('id="%s"' % sid)
    seg = d[i:i+2500]
    # object section 的掉落行里第一个 /zh-cn/item/NNN
    m = re.search(r'/zh-cn/item/(\d+)', seg)
    print(sid, '-> item', m.group(1) if m else '?')
    out[sid] = m.group(1) if m else None

json.dump(out, open(os.path.join(HERE, '_fc_rare_names.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('已存 _fc_rare_names.json')
