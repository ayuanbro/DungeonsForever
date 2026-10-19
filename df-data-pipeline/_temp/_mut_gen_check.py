# -*- coding: utf-8 -*-
"""按 main() 的口径把变异注入到副本，写出到 _mut_out/，供 Lua 语法门禁复现。"""
import importlib.util, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEV = r'D:\workspace\DungeonsForever'
OUT = os.path.join(HERE, '_mut_out')
os.makedirs(OUT, exist_ok=True)

spec = importlib.util.spec_from_file_location('dmut', os.path.join(HERE, 'df_mut_check.py'))
m = importlib.util.module_from_spec(spec); sys.modules['dmut'] = m; spec.loader.exec_module(m)

files = {}
for name, s in m.MUTATIONS:
    fname, old, new = m.split_spec(s)
    files.setdefault(fname, []).append((name, old, new))

for fname, items in files.items():
    p = os.path.join(DEV, *fname.split('/'))
    data = open(p, 'rb').read()
    pristine = data
    for name, old, new in items:
        if pristine.count(m.to_file_style(old, pristine)) != 1:
            continue
        o, nw = m.to_file_style(old, data), m.to_file_style(new, data)
        if data.count(o) != 1:
            continue
        data = data.replace(o, nw)
    outp = os.path.join(OUT, fname.replace('/', '__'))
    open(outp, 'wb').write(data)
    print('写出 %s -> %s' % (fname, outp))
