# -*- coding: utf-8 -*-
"""诊断：复刻 df_mut_check.main() 的「同文件内逐条累积替换」逻辑，
列出**每一条**锚点在轮到它时的 count（!=1 即被前面的变异吃掉/或本就重复）。

只读，不改任何文件。用来定位问题 C 的真因。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import df_mut_check as M  # noqa: E402

BETA = r'D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\DungeonsForever'

files = {}
for name, spec in M.MUTATIONS:
    fname, old, new = M.split_spec(spec)
    files.setdefault(fname, []).append((name, old, new))

print('文件处理顺序：%s' % list(files.keys()))
print()
starved = []
for fname, items in files.items():
    p = os.path.join(BETA, *fname.split('/'))
    data = open(p, 'rb').read()
    print('--- %s（%d 字节）共 %d 条变异 ---' % (fname, len(data), len(items)))
    for name, old, new in items:
        n = data.count(old)
        if n != 1:
            starved.append((fname, name, n))
            print('  STARVED count=%d  %s' % (n, name))
            print('      锚点前 80 字节: %r' % old[:80])
        else:
            data = data.replace(old, new)
    print('  (%s 累积替换完成)' % fname)

print()
print('=== 汇总：被前面变异吃掉的锚点 ===')
for fname, name, n in starved:
    print('  [%s] count=%d  %s' % (fname, n, name))
if not starved:
    print('  （无）')
