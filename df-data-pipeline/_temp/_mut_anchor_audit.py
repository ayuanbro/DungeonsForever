# -*- coding: utf-8 -*-
"""一次性体检 df_mut_check.py 里**所有**变异锚点（不注入、只统计命中次数）。

为什么需要它：df_mut_check 命中 0 次 / 2 次就 return 2，一次只报**第一条**坏锚点，
修一条跑一轮（每轮还要真跑一遍 harness）太慢。这里把 MUTATIONS 全量拉出来，
按 df_mut_check 自己的规范化口径（_norm_spec → _strip_cmt；to_file_style）在
**目标文件原文**上数命中次数，一次列全部坏锚点。

★ 口径必须**完全复用** df_mut_check 的函数，别在这里重写一套 —— 重写的那套一旦漂移，
  体检就会和真注入判得不一样（本项目踩过「体检 264 条里 111 条假红」）。
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BETA = r'D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\DungeonsForever'

spec = importlib.util.spec_from_file_location('df_mut_check', os.path.join(HERE, 'df_mut_check.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

bad = []
seen = {}
for name, sp in m.MUTATIONS:
    fname, old, new = m.split_spec(sp)
    old = m._strip_cmt(old)
    p = os.path.join(BETA, *fname.split('/'))
    if p not in seen:
        seen[p] = open(p, 'rb').read()
    data = seen[p]
    o = m.to_file_style(old, data)
    n = data.count(o)
    if n != 1:
        bad.append((n, fname, name))

print('变异总数 = %d' % len(m.MUTATIONS))
print('坏锚点 = %d' % len(bad))
for n, fname, name in bad:
    print('  [%d 次] %-24s %s' % (n, fname, name))
sys.exit(1 if bad else 0)
