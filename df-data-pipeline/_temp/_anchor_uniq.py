# -*- coding: utf-8 -*-
"""对**源侧**所有变异锚点做唯一性核对（不等 beta、不注入）。

df_mut_check 是注入后才报「锚点不唯一/不存在」；重构期间先在这里快速全量核对一遍，
省得跑一遍完整注入才发现某条锚点已经被搬没了。

用法：python _temp/_anchor_uniq.py [关键字]
"""
import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location(
    'dmut', os.path.join(ROOT, '_temp', 'df_mut_check.py'))
mod = importlib.util.module_from_spec(spec)
sys.modules['dmut'] = mod
spec.loader.exec_module(mod)

kw = sys.argv[1] if len(sys.argv) > 1 else ''
cache = {}
bad, ok = [], 0
for name, sp in mod.MUTATIONS:
    if kw and kw not in name:
        continue
    f, old, new = mod.split_spec(sp)
    if isinstance(old, bytes):
        old = old.decode('utf-8')
    if f not in cache:
        p = os.path.join(ROOT, *f.split('/'))
        cache[f] = open(p, encoding='utf-8', newline='').read()
    src = cache[f]
    # 锚点按仓库行尾（LF）写，比对时把文件行尾归一
    n = src.replace('\r\n', '\n').count(old.replace('\r\n', '\n'))
    if n == 1:
        ok += 1
    else:
        bad.append((name, f, n, old.strip().split('\n')[0][:64]))

print('唯一命中 %d 条；异常 %d 条' % (ok, len(bad)))
for name, f, n, t in bad:
    print('  x%d  %-34s %-22s %s' % (n, name, f, t))
