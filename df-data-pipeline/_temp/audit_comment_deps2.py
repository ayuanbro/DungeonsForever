# -*- coding: utf-8 -*-
"""① 变异锚点里含注释文本的条数；② 各文件头部注释块长度分布。"""
import os, re, sys

HERE = r'D:\workspace\DungeonsForever\_temp'
ADDON = r'D:\workspace\DungeonsForever'
sys.path.insert(0, HERE)

print('=' * 80)
print('① df_mut_check.MUTATIONS 的 old 锚点含 -- 的条数')
print('=' * 80)
try:
    import df_mut_check as M
    bad = []
    for name, spec in M.MUTATIONS:
        parts = M.split_spec(spec)
        fname, old, new = parts
        if '--' in old:
            bad.append((name, fname, old.replace('\n', '\\n')[:80]))
    print('MUTATIONS 共 %d 条，old 锚点含 -- 的 %d 条：' % (len(M.MUTATIONS), len(bad)))
    for n, f, o in bad:
        print('   %-40s %-34s %s' % (n, f, o))
except Exception as e:
    print('  导入失败：%r' % (e,))

print()
print('=' * 80)
print('② 各文件“头部注释块”长度（从第 1 行起连续注释/空行，直到首个代码行）')
print('=' * 80)

def head_block(path):
    with open(path, encoding='utf-8', errors='replace') as f:
        ln = f.read().replace('\r\n', '\n').split('\n')
    n = 0
    for i, l in enumerate(ln):
        s = l.strip()
        if s == '' or s.startswith('--'):
            n = i + 1
        else:
            break
    return n, ln[:n]

roots = ['Core', 'Locales']
rows = []
for r in roots:
    for dp, dn, fn in os.walk(os.path.join(ADDON, r)):
        for f in sorted(fn):
            if f.endswith('.lua'):
                p = os.path.join(dp, f)
                rel = os.path.relpath(p, ADDON).replace('\\', '/')
                n, _ = head_block(p)
                rows.append((rel, n))
for rel, n in sorted(rows):
    print('  %3d 行头部注释块  %s' % (n, rel))
