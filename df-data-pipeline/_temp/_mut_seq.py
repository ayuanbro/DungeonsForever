# -*- coding: utf-8 -*-
"""复现 df_mut_check.main() 的注入循环，区分两类失守：
   A) 真坏锚点（pristine 上就 !=1）
   B) 顺序踩踏（pristine=1，被同文件更早的变异改掉了）
"""
import importlib.util, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
BETA = r'D:\workspace\DungeonsForever'

spec = importlib.util.spec_from_file_location('dmut', os.path.join(HERE, 'df_mut_check.py'))
m = importlib.util.module_from_spec(spec); sys.modules['dmut'] = m; spec.loader.exec_module(m)

files = {}
order = []
for name, s in m.MUTATIONS:
    fname, old, new = m.split_spec(s)
    files.setdefault(fname, []).append((name, old, new))

pristine_cache = {}
A, B = [], []
for fname, items in files.items():
    p = os.path.join(BETA, *fname.split('/'))
    pristine = open(p, 'rb').read()
    data = pristine
    for name, old, new in items:
        c0 = pristine.count(m.to_file_style(old, pristine))
        c1 = data.count(m.to_file_style(old, data))
        if c0 != 1:
            A.append((name, fname, c0))
        elif c1 != 1:
            B.append((name, fname, c0, c1))
        else:
            data = data.replace(m.to_file_style(old, data), m.to_file_style(new, data))

print('A) 真坏锚点（pristine != 1）：%d 条' % len(A))
for n, f, c in A:
    print('   pristine=%d  %-22s %s' % (c, f, n))
print()
print('B) 顺序踩踏（pristine=1 但被更早的变异改掉）：%d 条' % len(B))
for n, f, c0, c1 in B:
    print('   pristine=%d -> seq=%d  %-22s %s' % (c0, c1, f, n))
print()
print('合计失守 = %d（主程序曾报 25）' % (len(A) + len(B)))
