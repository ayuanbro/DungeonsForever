# -*- coding: utf-8 -*-
"""探测 27 个专精指南 URL 的存在性与页面规模。"""
import time

from curl_cffi import requests as cr

PROXY = 'http://127.0.0.1:7897'
HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Upgrade-Insecure-Requests': '1',
    'Referer': 'https://www.wowhead.com/forever/cn',
}

BASE = 'https://www.wowhead.com/forever/cn/guide/classes'
# class slug, spec slug, role guess
SPECS = [
    ('warrior', 'arms', 'dps'), ('warrior', 'fury', 'dps'), ('warrior', 'protection', 'tank'),
    ('paladin', 'holy', 'healer'), ('paladin', 'protection', 'tank'), ('paladin', 'retribution', 'dps'),
    ('hunter', 'beast-mastery', 'dps'), ('hunter', 'marksmanship', 'dps'), ('hunter', 'survival', 'dps'),
    ('rogue', 'assassination', 'dps'), ('rogue', 'combat', 'dps'), ('rogue', 'subtlety', 'dps'),
    ('priest', 'discipline', 'healer'), ('priest', 'holy', 'healer'), ('priest', 'shadow', 'dps'),
    ('shaman', 'elemental', 'dps'), ('shaman', 'enhancement', 'dps'), ('shaman', 'restoration', 'healer'),
    ('mage', 'arcane', 'dps'), ('mage', 'fire', 'dps'), ('mage', 'frost', 'dps'),
    ('warlock', 'affliction', 'dps'), ('warlock', 'demonology', 'dps'), ('warlock', 'destruction', 'dps'),
    ('druid', 'balance', 'dps'), ('druid', 'feral', 'dps'), ('druid', 'restoration', 'healer'),
]

s = cr.Session(impersonate='chrome110',
               proxies={'http': PROXY, 'https': PROXY}, headers=HEADERS)
ok = 0
for i, (cls, spec, role) in enumerate(SPECS):
    url = '%s/%s/%s/overview-pve-%s' % (BASE, cls, spec, role)
    try:
        r = s.head(url, timeout=30, allow_redirects=True)
        code = r.status_code
        if code != 200:
            r2 = s.get(url, timeout=30)
            code = '%s->%s' % (code, r2.status_code)
        else:
            ok += 1
        print('%-2d %-40s %s' % (i + 1, '%s/%s/%s' % (cls, spec, role), code))
    except Exception as e:
        print('%-2d %-40s ERR %s' % (i + 1, spec, str(e)[:60]))
    time.sleep(1.2)
print('ok:', ok, '/', len(SPECS))
