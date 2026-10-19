# -*- coding: utf-8 -*-
"""用真 Lua 5.1 载入 Data_BossPos.lua，输出每个副本的钉点数与坐标范围。"""
import os
import sys

from lupa import lua51

DF = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(DF, 'Core', 'Data', 'Data_BossPos.lua'), 'rb').read().decode('utf-8')

lua = lua51.LuaRuntime(unpack_returned_tuples=True)
lua.execute('ns = {}; _G.__chunk = loadstring or load')
run = lua.eval('function(code) local f = loadstring(code); return f("DungeonsForever", ns) end')
run(src)


boss = lua.eval('ns.BossPos')
total = 0
nz = 0
bad = []
for did in sorted(boss.keys()):
    row = boss[did]
    docs = sorted(row.keys())
    cnt = 0
    for name in docs:
        pts = row[name]
        cnt += len(pts)
        for k in pts.keys():
            lo, hi = pts[k][1], pts[k][2]
            if not (0 <= lo <= 100 and 0 <= hi <= 100):
                bad.append('%s/%s=%s,%s' % (did, name, lo, hi))
    total += cnt
    nz += 1
    print('%-20s bosses=%2d pins=%2d  %s' % (did, len(docs), cnt, ', '.join(docs)))
print('---')
print('dungeons=%d  total_pins=%d  越界坐标=%s' % (nz, total, bad or '无'))
