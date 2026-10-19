# -*- coding: utf-8 -*-
"""核对 Data_BossPos.lua：每个副本的钉点数、坐标范围、与 DungeonLoot 的名字对齐。"""
import os
import re

DF = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(p):
    return open(os.path.join(DF, p), 'rb').read().decode('utf-8')


bp = read('Core/Data/Data_BossPos.lua')
loot = read('Core/Data/Data_DungeonLoot.lua')

# 解析 BossPos
blocks = re.findall(r'\["([a-z_]+)"\]\s*=\s*\{(.*?)\n    \}', bp, re.S)
total = 0
for did, body in blocks:
    bosses = re.findall(r'\["([^"]+)"\]\s*=\s*\{([^}]*)\}', body)
    n = 0
    for name, pts in bosses:
        pts = [p for p in re.split(r'\{|\}|,', pts) if p.strip()]
        n += len(re.findall(r'\{', body))  # placeholder
    cnt = len(re.findall(r'\["([^"]+)"\]\s*=\s*\{', body))
    pins = len(re.findall(r'\{ *\d', body))
    total += pins
    print('%-20s bosses=%d pins=%d' % (did, cnt, pins))
print('dungeons=%d total_pins=%d' % (len(blocks), total))

# 提取 DungeonLoot 的 (副本, 英文名) 集合
print('--- 名字对齐抽查 ---')
seg = re.findall(r'\["([a-z_]+)"\]\s*=\s*\{', loot)
print('loot dungeons=%d' % len(seg))
