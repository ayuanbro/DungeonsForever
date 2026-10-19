# -*- coding: utf-8 -*-
"""生成 Core/Data/Data_Plunder.lua（贸易局遭劫货物目录 · 生成物）。

数据源 = wuxianwow.com/ah/data/commerce.json（贸易局采买，每日拍卖行快照）。
口径与板条箱页一致：只存 ID / 数量 / 分类 key / 物品等级段，
**网站上的当日价格一律不落盘**，价格运行期走专业页 RA.AHPriceOf（本地拍卖行扫描）。
名字 / 图标运行期由客户端给出。

用法：python gen_plunder_data.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(HERE)
DST = os.path.join(DF, 'Core', 'Data', 'Data_Plunder.lua')
SRC = os.path.join(HERE, '_plunder_src.json')
URL = 'https://wuxianwow.com/ah/data/commerce.json'

if not os.path.isfile(SRC):
    import urllib.request
    req = urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    with open(SRC, 'wb') as f:
        f.write(data)
with open(SRC, 'rb') as f:
    d = json.loads(f.read().decode('utf-8'))

CAT_ORDER = ['ingot', 'herb', 'leather', 'enchant', 'potion', 'food',
             'bandage', 'device', 'gear', 'other', 'mismatch']
CAT_RANK = {k: i for i, k in enumerate(CAT_ORDER)}

goods = []
for g in d.get('goods') or []:
    mats = [(int(m['id']), int(m['count'] or 1)) for m in (g.get('mats') or [])]
    if not mats:
        continue
    goods.append((int(g['id']), int(g.get('band') or 0), g.get('cat') or 'other', mats))
goods.sort(key=lambda x: (CAT_RANK.get(x[2], 99), x[1], x[0]))

lines = []
lines.append('')
lines.append('')
lines.append('')
lines.append('local _, ns = ...')
lines.append('')
lines.append('ns.PlunderData = {')
lines.append('    goods = {')
for pid, band, cat, mats in goods:
    mstr = ', '.join('{ %d, %d }' % m for m in mats)
    lines.append('        { id = %d, band = %d, cat = "%s", mats = { %s } },'
                 % (pid, band, cat, mstr))
lines.append('    },')
lines.append('}')
lines.append('')

with open(DST, 'wb') as f:
    f.write('\n'.join(lines).encode('utf-8'))

n_mat = sum(len(g[3]) for g in goods)
print('[gen_plunder_data] goods=%d (mats=%d) day=%s -> %s'
      % (len(goods), n_mat, d.get('day'), DST))
