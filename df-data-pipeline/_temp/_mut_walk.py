# -*- coding: utf-8 -*-
"""诊断：df_mut_check 全量 main() 走到哪一条锚点会停 —— 按 main() 的**真实**口径
（含 to_file_style 修正后）逐条预演「内存里累积替换」的过程，打印每条锚点的命中次数。

用法：
    python _temp/_mut_walk.py [root]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import df_mut_check as M  # noqa: E402

root = sys.argv[1] if len(sys.argv) > 1 else M.TITAN

# 复刻 main() 的文件分组顺序
files = {}
for name, spec in M.MUTATIONS:
    fname, old, new = M.split_spec(spec)
    files.setdefault(fname, []).append((name, old, new))

zero, many, total = [], [], 0
for fname, items in files.items():
    p = os.path.join(root, *fname.split('/'))
    if not os.path.exists(p):
        print('!! 文件不存在: %s' % fname)
        continue
    data = open(p, 'rb').read()
    for name, old, new in items:
        total += 1
        c = data.count(M.to_file_style(old, data))          # ← 修正后的口径
        c_raw = data.count(old)                              # ← 现状口径
        flag = 'OK ' if c == 1 else ('0  ' if c == 0 else '>1 ')
        if c != 1:
            (zero if c == 0 else many).append((fname, name, c, c_raw))
        print('%s %-22s %-40s 修正后=%d 现状=%d' % (flag, fname, name, c, c_raw))
        if c == 1:
            data = data.replace(M.to_file_style(old, data), M.to_file_style(new, data))

print('=' * 74)
print('共 %d 条：修正后命中 0 次 %d 条 / >1 次 %d 条' % (total, len(zero), len(many)))
for fname, name, c, c_raw in zero:
    print('   0 次  %-22s %s   （现状口径 %d）' % (fname, name, c_raw))
for fname, name, c, c_raw in many:
    print('   >1 次 %-22s %s' % (fname, name, c))
