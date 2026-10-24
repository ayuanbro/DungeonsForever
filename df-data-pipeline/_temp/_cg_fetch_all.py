# -*- coding: utf-8 -*-
"""批量抓 27 页专精指南（缓存 _cg_probe/<cls>_<spec>.html）。"""
import time

from curl_cffi import requests as cr

from _cg_fetch import HEADERS, fetch

BASE = 'https://www.wowhead.com/forever/cn/guide/classes'
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

for i, (cls, spec, role) in enumerate(SPECS):
    key = '%s_%s' % (cls, spec)
    url = '%s/%s/%s/overview-pve-%s' % (BASE, cls, spec, role)
    fetch(key, url)
    time.sleep(4)
print('done')
