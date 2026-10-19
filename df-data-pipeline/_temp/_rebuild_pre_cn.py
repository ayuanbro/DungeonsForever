# -*- coding: utf-8 -*-
"""反向重放 _patch_raid_cn.py 的 RAID_EDITS，重建补丁前的 RaidUI.lua，用于对齐实机 traceback 行号。"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ns = {'__file__': os.path.join(ROOT, '_temp', '_patch_raid_cn.py')}
src = io.open(ns['__file__'], encoding='utf-8').read()
exec(src.split("print('== 1)")[0], ns)
edits = ns['RAID_EDITS']

cur = io.open(os.path.join(ROOT, 'Core', 'RaidUI.lua'), encoding='utf-8').read().replace('\r\n', '\n')
old = cur
for o, n, marker in edits:
    if n not in old:
        print('!! 反向找不到新文本: %s' % marker)
        continue
    old = old.replace(n, o, 1)

out = os.path.join(ROOT, '_temp', '_raid_pre_cn.lua')
io.open(out, 'w', encoding='utf-8', newline='\n').write(old)

cur_l = cur.split('\n')
old_l = old.split('\n')
print('current lines=%d   pre-CN lines=%d   delta=%d'
      % (len(cur_l), len(old_l), len(cur_l) - len(old_l)))
print()
probes = ['function RU.CountdownText',
          'local remain = RU.DATA.unlockAt',
          'local function UpdateCD',
          'local txt = RU.CountdownText()',
          'function RU.Render()',
          'UpdateCD()',
          'RU.Render()']
for p in probes:
    ci = [i + 1 for i, l in enumerate(cur_l) if p in l]
    oi = [i + 1 for i, l in enumerate(old_l) if p in l]
    print('%-38s cur=%-10s pre-CN=%s' % (p, ci[:3], oi[:3]))
