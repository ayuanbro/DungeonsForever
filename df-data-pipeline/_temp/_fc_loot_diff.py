# -*- coding: utf-8 -*-
"""临时：全量对查 foreverchanges.pro 各副本掉落 JSON vs 本地 Data_DungeonLoot.lua。

站点数据端点（从 /dungeons 页 JS chunk 逆向）：
  /dungeons/zh-cn/<slug>.json       掉落
对查维度：来源（boss/rare/trash，按英文名对齐）、物品集合、npc id、无限版新增旗标。
zh 名不做对查（本插件 NPC 名走 wowhead 口径，站点译名仅参考）。
"""
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LOOT = os.path.join(HERE, '..', 'Core', 'Data', 'Data_DungeonLoot.lua')
CACHE = os.path.join(HERE, '_fc', 'cache')
BASE = 'https://foreverchanges.pro/dungeons/zh-cn/%s.json'

# 站点全部副本 slug：从 /dungeons 页 list chunk 提取（id:"..." 列表）
CHUNK = os.path.join(CACHE, 'chunks', '2cttse9nln_ps.js')
chunk = open(CHUNK, encoding='utf-8', errors='replace').read()
site_slugs = set()
for m in re.finditer(r'\{id:"([a-z0-9-]+)",name:', chunk):
    site_slugs.add(m.group(1))
# 补：列表页 HTML 里出现过的 the-stockade 形态（个别可能不带 name: 前缀）
html = open(os.path.join(CACHE, 'dungeons_root.html'), encoding='utf-8', errors='replace').read()
for m in re.finditer(r'"([a-z0-9]+(?:-[a-z0-9]+)+)"', html):
    s = m.group(1)
    if 'stockade' in s or 'scarlet' in s or 'blackrock' in s:
        site_slugs.add(s)

# ── 解析本地 Lua ─────────────────────────────────────────────────────────────
SLUG_MAP = {
    'excavation-site': 'excavation_wetlands',
    'scarlet-monastery-graveyard': 'sm_graveyard',
    'scarlet-monastery-library': 'sm_library',
    'scarlet-monastery-armory': 'sm_armory',
    'scarlet-monastery-cathedral': 'sm_cathedral',
    'stratholme-main-gate': 'stratholme_main',
    'stratholme-service-gate': 'stratholme_service',
    'zulfarrak': 'zul_farrak',
}

lua = open(LOOT, encoding='utf-8').read()
ours = {}          # slug -> { src_en: {'zh':, 'note':, 'npc':, 'items': {id:(rate,new)} } }
pos = {}
for m in re.finditer(r'\n    \["([a-z0-9_]+)"\] = \{', lua):
    pos[m.group(1)] = m.start()
keys = sorted(pos, key=lambda k: pos[k])
for i, k in enumerate(keys):
    start = pos[k]
    end = pos[keys[i + 1]] if i + 1 < len(keys) else len(lua)
    seg = lua[start:end]
    srcs = {}
    for sm in re.finditer(r'\{ "([^"]*)", "([^"]*)", "([^"]*)", "(\d*)", \{(.*?)\} \}(?:,|\n)', seg, re.S):
        en, zh, note, npc, body = sm.groups()
        items = {}
        for im in re.finditer(r'\{ (\d+), ([\d.]+|nil), (true|false) \}', body):
            rate = None if im.group(2) == 'nil' else float(im.group(2))
            items[int(im.group(1))] = (rate, im.group(3) == 'true')
        srcs[en] = {'zh': zh, 'note': note, 'npc': npc, 'items': items}
    ours[k] = srcs

# ── 抓站点 JSON ──────────────────────────────────────────────────────────────
report = []
tot_missing_src = tot_missing_it = 0
for slug in sorted(site_slugs):
    dst = os.path.join(CACHE, 'fc_site_dg_%s.json' % slug)
    if not (os.path.exists(dst) and os.path.getsize(dst) > 100):
        r = subprocess.run(['curl', '-s', '-m', '30', '-o', dst, '-w', '%{http_code}',
                            BASE % slug], capture_output=True, text=True)
        if r.stdout.strip() != '200':
            if os.path.exists(dst):
                os.remove(dst)
            report.append('%-34s 抓取失败 HTTP %s' % (slug, r.stdout.strip()))
            continue
        time.sleep(0.4)
    d = json.load(open(dst, encoding='utf-8'))
    our = ours.get(SLUG_MAP.get(slug, slug.replace('-', '_')))
    if our is None:
        report.append('%-34s 本地无此副本表' % slug)
        continue
    site_srcs = {}
    for b in d.get('bosses', []):
        site_srcs[b.get('english') or b['name']] = b
    msgs = []
    for en, b in site_srcs.items():
        o = our.get(en)
        if o is None:
            tot_missing_src += 1
            msgs.append('  缺来源 %s(%s, npc=%s) %d件' % (
                en, b.get('kind'), b.get('display'), len(b.get('items', []))))
            continue
        if (b.get('display') or '') and o['npc'] != str(b['display']):
            msgs.append('  npc id 不一致 %s: 本地%s 站点%s' % (en, o['npc'], b['display']))
        site_items = {it['i']: it for it in b.get('items', [])}
        for iid, it in site_items.items():
            if iid not in o['items']:
                tot_missing_it += 1
                msgs.append('  缺物品 %s(%s) @%s t=%s' % (iid, it.get('n'), en, it.get('t')))
            else:
                rate, new = o['items'][iid]
                want_new = it.get('t') == 'new'
                if new != want_new:
                    msgs.append('  新增旗标不一致 %d @%s: 本地%s 站点t=%s' % (iid, en, new, it.get('t')))
                z = it.get('z')
                if z is not None and rate is not None and abs(z - rate) > 0.6:
                    msgs.append('  掉率差异 %d @%s: 本地%s 站点%s' % (iid, en, rate, z))
    # 本地有而站点没有的来源（站点可能精简）——只提示不算缺口
    for en in our:
        if en not in site_srcs:
            msgs.append('  (站点无此来源: %s)' % en)
    if msgs:
        report.append('%-34s' % slug)
        report.extend(msgs)

print('站点副本数 %d，本地副本数 %d' % (len(site_slugs), len(ours)))
print('缺来源合计 %d，缺物品合计 %d' % (tot_missing_src, tot_missing_it))
print('=' * 60)
print('\n'.join(report))
