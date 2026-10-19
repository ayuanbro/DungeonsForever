# -*- coding: utf-8 -*-
"""对比「备份(old) harness」与「当前(new) harness」的累积锚点注入结果。只读。"""
import os
import sys
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

BETA = r'D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\DungeonsForever'

# 把备份复制成可导入的模块名
bakmod = os.path.join(HERE, 'qa_mut_bak_mod.py')
shutil.copyfile(os.path.join(HERE, 'df_mut_check.py.qa_bak'), bakmod)

import importlib
old = importlib.import_module('qa_mut_bak_mod')
import df_mut_check as new


def simulate(mod, label):
    files = {}
    for name, spec in mod.MUTATIONS:
        fname, o, n = mod.split_spec(spec)
        files.setdefault(fname, []).append((name, o, n))
    print('===== %s：%d 条变异 =====' % (label, len(mod.MUTATIONS)))
    starved = []
    for fname, items in files.items():
        data = open(os.path.join(BETA, *fname.split('/')), 'rb').read()
        for name, o, n in items:
            c = data.count(o)
            if c != 1:
                starved.append((fname, name, c))
            else:
                data = data.replace(o, n)
    if starved:
        for fname, name, c in starved:
            print('  STARVED count=%d  [%s]  %s' % (c, fname, name))
    else:
        print('  （无失效锚点，全部 186 条均可注入）')
    return starved


s_old = simulate(old, '备份 harness（= 会话开始时的 14:00 版）')
print()
s_new = simulate(new, '当前 harness（18:32:40 外部修改后）')
