# -*- coding: utf-8 -*-
"""从 wow-ui-source (forever 分支, lock commit) 查客户端 FrameXML 里现成的任务/入口图标引用。"""
from curl_cffi import requests
import re

PROXY = {'http': 'http://127.0.0.1:7897', 'https': 'http://127.0.0.1:7897'}
BASE = ('https://raw.githubusercontent.com/Gethe/wow-ui-source/'
        '966519cf0ad2c10301ea011a88c14b25697c9687')
files = [
    '/Interface/FrameXML/QuestFrame.lua',
    '/Interface/FrameXML/GossipFrame.lua',
    '/Interface/AddOns/Blizzard_WorldMap/Blizzard_WorldMap.lua',
    '/Interface/FrameXML/WorldMapFrame.lua',
]
KEYS = ('AvailableQuest', 'CompletedQuest', 'IncompleteQuest', 'Dungeon', 'POI')
path_re = re.compile(r'Interface[\\/][\w\-\\/\.]+', re.I)

for f in files:
    r = requests.get(BASE + f, impersonate='chrome110', proxies=PROXY, timeout=40)
    if r.status_code != 200:
        print(f, '->', r.status_code)
        continue
    d = r.text
    print('=====', f, len(d))
    found = set()
    for m in path_re.findall(d):
        if any(k.lower() in m.lower() for k in KEYS):
            found.add(m)
    for s in sorted(found):
        print('   path:', s)
    for m in re.finditer(r'SetTexture\(\s*"?([^")]+?)"?\s*\)', d):
        s = m.group(1)
        if any(k.lower() in s.lower() for k in KEYS):
            print('   SetTexture:', s)
