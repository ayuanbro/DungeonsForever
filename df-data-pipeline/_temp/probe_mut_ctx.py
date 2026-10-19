# -*- coding: utf-8 -*-
"""找出 4 条变异锚在产物里的全部命中位置及上下文，便于加长消歧。"""
import sys
sys.path.insert(0, r'D:\workspace\DungeonsForever\_temp')
import os
import df_mut_check as M

ADDON = r'D:\workspace\DungeonsForever'
WANT = ['到货后不打 __named', '任务行退回 Frame', '每轮底色复位', 'RequestItem 不再保证监听器']

for name, spec in M.MUTATIONS:
    if not any(w in name for w in WANT):
        continue
    fname, old, new = M.split_spec(spec)
    src = open(os.path.join(ADDON, *fname.split('/')), 'rb').read()
    print('=' * 78)
    print(name, '|', fname, '| old 命中 %d 次' % src.count(old))
    print('OLD = %r' % old.decode('utf-8').replace('\r\n', '\\n'))
    pos = -1
    while True:
        pos = src.find(old, pos + 1)
        if pos < 0:
            break
        ln = src[:pos].count(b'\r\n')
        print('   ---- 命中 @行 %d 上下文 ----' % (ln + 1))
        ctx = src[max(0, pos - 260):pos + len(old) + 160].decode('utf-8', 'replace')
        for l in ctx.replace('\r\n', '\n').split('\n'):
            print('      ' + l)
