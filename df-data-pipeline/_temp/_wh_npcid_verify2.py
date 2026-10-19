# -*- coding: utf-8 -*-
"""临时②：拉剩余经典副本的 forever zone payload，对出全量 zh名→forever npc id 映射。"""
from curl_cffi import requests as cr
import re, time, os, json

proxies = {'http': 'http://127.0.0.1:7897', 'https': 'http://127.0.0.1:7897'}
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_fc', 'cache')

ZONES = [
    (721, 'gnomeregan'),
    (722, 'razorfen_downs'),
    (796, 'sm'),
    (1176, 'zul_farrak'),
    (1417, 'sunken_temple'),
    (1583, 'blackrock_spire'),
    (1584, 'blackrock_depths'),
    (2017, 'stratholme'),
    (2057, 'scholomance'),
    (2100, 'maraudon'),
    (2557, 'dire_maul'),
]


def get(url):
    for i in range(4):
        time.sleep(2 * (i + 1))
        try:
            r = cr.get(url, impersonate='chrome110', timeout=40, proxies=proxies)
            if r.status_code == 200:
                return r.text
        except Exception:
            pass
    return ''


# 本地 zh 名清单（按副本）
import re as _re
lua = open(os.path.join(CACHE, '..', '..', '..', 'Core', 'Data', 'Data_DungeonLoot.lua'), encoding='utf-8').read()
pos = {}
for m in _re.finditer(r'\n    \["([a-z0-9_]+)"\] = \{', lua):
    pos[m.group(1)] = m.start()
keys = sorted(pos, key=lambda k: pos[k])
local = {}
for i, k in enumerate(keys):
    end = pos[keys[i + 1]] if i + 1 < len(keys) else len(lua)
    seg = lua[pos[k]:end]
    names = _re.findall(r'\{ \"(?:[^\"\\]|\\.)*\", \"([^\"]+)\", ', seg)
    local[k] = names

result = {}
for zid, key in ZONES:
    f = os.path.join(CACHE, 'wh_zone_%d_payload.txt' % zid)
    if not os.path.exists(f):
        t = get('https://www.wowhead.com/forever/cn/zone=%d' % zid)
        open(f, 'w', encoding='utf-8').write(t)
        time.sleep(1)
    t = open(f, encoding='utf-8').read()
    mp = {}
    for m in re.finditer(r'\{"classification":(\d+),"displayName":"((?:[^"\\]|\\.)*)","displayNames":\[[^\]]*\],"id":(\d+)', t):
        if m.group(1) == '1':
            mp.setdefault(m.group(2), m.group(3))
    result[key] = {'zid': zid, 'map': mp}
    print('== zone %d (%s) payload %d, 名条目 %d' % (zid, key, len(t), len(mp)))

print()
print('===== 本地 zh 名 → forever id（仅命中）=====')
for key, names in local.items():
    mp = result.get(key, {}).get('map') or result.get(
        {'sm_graveyard': 'sm', 'sm_library': 'sm', 'sm_armory': 'sm', 'sm_cathedral': 'sm',
         'dire_maul_east': 'dire_maul', 'dire_maul_west': 'dire_maul', 'dire_maul_north': 'dire_maul',
         'lower_blackrock_spire': 'blackrock_spire', 'upper_blackrock_spire': 'blackrock_spire',
         'stratholme_main': 'stratholme', 'stratholme_service': 'stratholme'}.get(key, ''), {}).get('map')
    if mp is None:
        continue
    hits = {}
    for zh in names:
        if zh in mp:
            hits[zh] = mp[zh]
        else:
            for k2, v in mp.items():
                if k2 and (zh in k2 or k2 in zh):
                    hits[zh] = v
                    break
    if hits:
        print('%s:' % key)
        for zh, nid in hits.items():
            print('  %s -> %s' % (zh, nid))
