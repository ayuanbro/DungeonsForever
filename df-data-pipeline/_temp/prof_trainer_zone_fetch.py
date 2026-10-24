# -*- coding: utf-8 -*-
"""从 wowhead zones 数据端点抓 zone id->中文名，匹配 78 个待补地名。
输出 _trainers_zone_zh.json。后台运行。"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROXY = 'http://127.0.0.1:7897'
OUT = os.path.join(HERE, '_trainers_zone_zh.json')

need = json.load(open(os.path.join(HERE, '_trainers_zone_zh.json'), encoding='utf-8'))
print('need:', len(need))

url = 'https://r.jina.ai/https://cn.wowhead.com/data=zones'
r = subprocess.run(['curl', '-s', '-x', PROXY, url, '--max-time', '60'],
                   capture_output=True, text=True, timeout=90)
body = r.stdout or ''
print('fetched bytes:', len(body))
open(os.path.join(HERE, '_wowhead_zones.txt'), 'w', encoding='utf-8').write(body)

got = {}
for m in re.finditer(r'"(\d+)":\s*\{[^{}]*?"name":"([^"]+)"', body):
    got[m.group(2)] = int(m.group(1))
print('zones parsed:', len(got))
hit = [e for e in need if e in got]
print('hit: %d / %d' % (len(hit), len(need)))
if hit[:5]:
    print('sample:', hit[:5])
