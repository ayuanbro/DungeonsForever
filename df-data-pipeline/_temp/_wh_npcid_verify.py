# -*- coding: utf-8 -*-
"""临时：核对 forever 分支各副本 zone payload 的 boss npc id vs 本地掉落表 npc id。"""
from curl_cffi import requests as cr
import re, time, json, os

proxies = {'http': 'http://127.0.0.1:7897', 'https': 'http://127.0.0.1:7897'}
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_fc', 'cache')

ZONES = [
    (1337, 'uldaman'),
    (491, 'razorfen_kraul'),
    (719, 'blackfathom_deeps'),
    (718, 'wailing_caverns'),
    (1581, 'the_deadmines'),
    (209, 'shadowfang_keep'),
    (717, 'the_stockade'),
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


def parse_lua_sources(path):
    lua = open(path, encoding='utf-8').read()
    out = {}
    for m in re.finditer(r'\n    \["([a-z0-9_]+)"\] = \{', lua):
        out[m.group(1)] = m.start()
    keys = sorted(out, key=lambda k: out[k])
    res = {}
    for i, k in enumerate(keys):
        end = out[keys[i + 1]] if i + 1 < len(keys) else len(lua)
        seg = lua[out[k]:end]
        srcs = {}
        for sm in re.finditer(r'\{ \"((?:[^\"\\]|\\.)*)\", \"([^\"]*)\", \"([^\"]*)\", \"(\d*)\"', seg):
            srcs[sm.group(2)] = sm.group(4)
        res[k] = srcs
    return res


ours = parse_lua_sources(os.path.join(CACHE, '..', '..', '..', 'Core', 'Data', 'Data_DungeonLoot.lua'))

for zid, key in ZONES:
    f = os.path.join(CACHE, 'wh_zone_%d_payload.txt' % zid)
    if not os.path.exists(f):
        t = get('https://www.wowhead.com/forever/cn/zone=%d' % zid)
        open(f, 'w', encoding='utf-8').write(t)
        time.sleep(1)
    t = open(f, encoding='utf-8').read()
    bosses = {}
    for m in re.finditer(r'\{"classification":(\d+),"displayName":"((?:[^"\\]|\\.)*)","displayNames":\[[^\]]*\],"id":(\d+)', t):
        cls, nm, nid = m.group(1), m.group(2), m.group(3)
        if cls != '1':
            continue  # 1 = 具名 NPC（boss/稀有），跳过普通小怪
        bosses.setdefault(nm, nid)
    print('=====', key, 'zone', zid, 'payload %d' % len(t), 'boss条目 %d' % len(bosses))
    for zh, ours_id in ours.get(key, {}).items():
        hit = bosses.get(zh)
        flag = '' if not hit else ('' if hit == ours_id else '  << 本地%s vs forever%s' % (ours_id or '(空)', hit))
        if not hit:
            flag = '  (zone payload 无此名)' if not ours_id else ''
        print('  %-16s 本地=%-8s forever=%s%s' % (zh, ours_id or '(空)', hit or '?', flag))
