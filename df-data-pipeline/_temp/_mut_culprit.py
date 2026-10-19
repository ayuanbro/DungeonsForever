# -*- coding: utf-8 -*-
"""定位 3 条顺序踩踏的元凶：逐条应用，找出「某条锚点被哪条更早的变异吃掉」。"""
import importlib.util, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
BETA = r'D:\workspace\DungeonsForever'

spec = importlib.util.spec_from_file_location('dmut', os.path.join(HERE, 'df_mut_check.py'))
m = importlib.util.module_from_spec(spec); sys.modules['dmut'] = m; spec.loader.exec_module(m)

TARGETS = [
    "专业页：配方详情条长回来",
    "胶囊：SwitchSub 又把 key 丢掉（永远只显示 5人本）",
    "升级 HUD：标签挂开关身上（被 ReskinToggle 的 PurgeNative 隐藏 = 实机看不到）",
]

files = {}
for name, s in m.MUTATIONS:
    fname, old, new = m.split_spec(s)
    files.setdefault(fname, []).append((name, old, new))

# 逐文件模拟，记录每条锚点在其「之前」被消费时、是被哪条吃掉的
for fname, items in files.items():
    p = os.path.join(BETA, *fname.split('/'))
    pristine = open(p, 'rb').read()
    data = pristine
    applied = []
    for name, old, new in items:
        o = m.to_file_style(old, pristine)   # 按 pristine 判定合法性
        c0 = pristine.count(o)
        if c0 != 1:
            continue
        # 现在看它在「当前 data」里还在不在
        o_now = m.to_file_style(old, data)
        if data.count(o_now) != 1:
            if name in TARGETS:
                print('[踩踏] %s' % name)
                print('       文件 %s，被它**之前**已应用的这些变异吃掉：' % fname)
                # 找哪条已应用的变异与它的锚点区域重叠
                for pn, po, pnew in applied:
                    po_f = m.to_file_style(po, pristine)
                    # 判断 po_f 与 o 是否重叠（互为子串或共享行）
                    a = po_f.decode('utf-8', 'replace')
                    b = o.decode('utf-8', 'replace')
                    la = set(a.split('\n')); lb = set(b.split('\n'))
                    common = [x for x in lb if x and x in la]
                    if common:
                        print('         ← 与之重叠: %s' % pn)
                        for x in common[:3]:
                            print('              %r' % x)
                print()
        data = data.replace(m.to_file_style(old, data), m.to_file_style(new, data))
        applied.append((name, old, new))
