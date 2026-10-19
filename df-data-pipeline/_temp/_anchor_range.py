# -*- coding: utf-8 -*-
"""列出 df_mut_check.py 里落在某个函数体内的变异锚点（重构前风险评估）。"""
import importlib.util
import sys

HERE = 'D:/workspace/DungeonsForever/'

spec = importlib.util.spec_from_file_location('dmut', HERE + '_temp/df_mut_check.py')
mod = importlib.util.module_from_spec(spec)
sys.modules['dmut'] = mod
spec.loader.exec_module(mod)

TARGET_FILE = sys.argv[1] if len(sys.argv) > 1 else 'Core/MapUI.lua'
FUNC_DECL = sys.argv[2] if len(sys.argv) > 2 else 'function M.Build(detail, hero)'
NEXT_DECL = sys.argv[3] if len(sys.argv) > 3 else '\nfunction M.WheelScroll'

target = open(HERE + TARGET_FILE, encoding='utf-8').read().replace('\r\n', '\n')
start = target.index(FUNC_DECL)
end = target.index(NEXT_DECL)


def lineno(i):
    return target.count('\n', 0, i) + 1


print('目标函数行范围 =', lineno(start), '-', lineno(end))
print('MUTATIONS 条数 =', len(mod.MUTATIONS))
hits = []
for name, sp in mod.MUTATIONS:
    f, old, new = mod.split_spec(sp)
    if f != TARGET_FILE:
        continue
    if isinstance(old, bytes):
        old = old.decode('utf-8')
    idx = target.find(old)
    if idx >= 0 and start <= idx <= end:
        hits.append((name, lineno(idx), old.strip().split('\n')[0][:74]))
print('落在该函数内的锚点 =', len(hits))
for n, ln, t in sorted(hits, key=lambda x: x[1]):
    print('  %-30s L%-5d %s' % (n, ln, t))
