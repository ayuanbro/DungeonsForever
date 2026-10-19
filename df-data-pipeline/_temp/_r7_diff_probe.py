# -*- coding: utf-8 -*-
"""对比「本次链跑后 src」与「beta 副本（=链跑前 src，因链跑前 src==beta）」，
逐文件给出变更行数与前后样例，判定漂移来源。输出：_temp/_r7_diff_probe.txt"""
import difflib
import io
import os

DF = r'D:\workspace\DungeonsForever'
BETA = r'D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\DungeonsForever'
OUT = os.path.join(DF, '_temp', '_r7_diff_probe.txt')

FILES = [
    'Core/Data/Data_Professions.lua',
    'Core/Data/enUS/Data_Professions.lua',
    'Core/Data/zhTW/Data_Professions.lua',
    'Core/Data/enUS/Data_LootFilter.lua',
    'Core/Data/Data_ClassGuide.lua',
    'Core/Data/enUS/Data_ClassGuide.lua',
    'Core/Data/zhTW/Data_ClassGuide.lua',
]

lines = []
w = lines.append
for rel in FILES:
    a_p = os.path.join(BETA, rel)
    b_p = os.path.join(DF, rel)
    exist = (os.path.exists(a_p), os.path.exists(b_p))
    w('=' * 78)
    w('%s   beta存在=%s src存在=%s' % (rel, exist[0], exist[1]))
    if not all(exist):
        w('  （缺文件，跳过）')
        continue
    a = io.open(a_p, encoding='utf-8', errors='replace').read().splitlines()
    b = io.open(b_p, encoding='utf-8', errors='replace').read().splitlines()
    sm = difflib.SequenceMatcher(None, a, b)
    adds = dels = 0
    shown = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            continue
        dels += (i2 - i1)
        adds += (j2 - j1)
        if shown < 12:
            for k in range(i1, i2):
                w('  - %s' % a[k][:160])
            for k in range(j1, j2):
                w('  + %s' % b[k][:160])
            shown += 1
    w('  → beta行=%d src行=%d  删%d 增%d' % (len(a), len(b), dels, adds))

io.open(OUT, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines) + '\n')
print('\n'.join(lines))
