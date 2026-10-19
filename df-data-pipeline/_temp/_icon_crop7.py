# -*- coding: utf-8 -*-
"""一次性补丁：给 7 处「漏裁」的图标纹理补上 UV 裁边 SetTexCoord(0.07, 0.93, 0.07, 0.93)。

口径与全仓一致（ProfessionUI / TierUI / BisUI / ExploreUI / QuickBar …），
四边各内缩 7% 裁掉图标素材自带的那圈边。

覆盖：
  Core/ProfessionUI.lua  737 对照表行图标 / 1065 左列导航图标 / 1119 设置齿轮
  Core/ExploreUI.lua    1767 40本书 / 1789 睡袋 / 1808 战斗法师（三个收集子页导航）
  Core/DungeonUI.lua    2885 任务详情物品图标
（BisUI 两处 844/1259 早已裁，无需动。）

实现：按行处理（不碰行尾）；先清掉此前误插的 `X.SetTexCoord` 坏行（缺冒号），
再在锚点行**之前**插入正确行。幂等：上一行已是同变量的 SetTexCoord 就跳过。
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UV = ':SetTexCoord(0.07, 0.93, 0.07, 0.93)'

# 坏行（此前 bug 插入的点号版），一律删掉
BAD = re.compile(r'^\s*[A-Za-z_][\w\.]*\.SetTexCoord\(0\.07, 0\.93, 0\.07, 0\.93\)\s*$')

# (相对路径, 锚点行原文, 纹理变量)
JOBS = [
    ('Core/ProfessionUI.lua', '        r.icon:SetSize(15, 15)', 'r.icon'),
    ('Core/ProfessionUI.lua', '        bt.__icon:SetSize(PD.NAV_ICON, PD.NAV_ICON)', 'bt.__icon'),
    ('Core/ProfessionUI.lua', '    gear.__icon:SetSize(14, 14)', 'gear.__icon'),
    ('Core/ExploreUI.lua', r'        bt.__icon:SetTexture("Interface\\Icons\\inv_misc_book_11")', 'bt.__icon'),
    ('Core/ExploreUI.lua', r'        bt.__icon:SetTexture("Interface\\Icons\\inv_misc_bag_08")', 'bt.__icon'),
    ('Core/ExploreUI.lua', r'        bt.__icon:SetTexture("Interface\\Icons\\inv_sword_05")', 'bt.__icon'),
    ('Core/DungeonUI.lua', '            r.icon:SetSize(DG.Q_DET_ICON, DG.Q_DET_ICON)', 'r.icon'),
]

by_file = {}
for f, a, v in JOBS:
    by_file.setdefault(f, []).append((a, v))

for f, jobs in by_file.items():
    path = os.path.join(ROOT, f)
    raw = open(path, 'rb').read()
    txt = raw.decode('utf-8')
    eol = '\r\n' if '\r\n' in txt else '\n'
    lines = txt.split(eol)
    print('=== %s  (行尾 %s, %d 行)' % (f, 'CRLF' if eol == '\r\n' else 'LF', len(lines)))

    # ① 清坏行
    kept, dropped = [], 0
    for l in lines:
        if BAD.match(l):
            dropped += 1
            continue
        kept.append(l)
    lines = kept
    if dropped:
        print('   清掉 %d 行坏插入（.SetTexCoord 缺冒号）' % dropped)

    # ② 插正确行
    added = 0
    for a, var in jobs:
        idx = [i for i, l in enumerate(lines) if l == a]
        if len(idx) != 1:
            print('   !! 锚点命中 %d 次，中止: %r' % (len(idx), a))
            sys.exit(2)
        i = idx[0]
        new = a[:len(a) - len(a.lstrip())] + var + UV
        prev_ok = i > 0 and lines[i - 1].strip() == var + UV
        if prev_ok:
            print('   跳过（已裁）: %s' % new.strip())
            continue
        lines.insert(i, new)
        added += 1
        print('   + %s' % new.strip())

    open(path, 'wb').write(eol.join(lines).encode('utf-8'))
    print('   → 清 %d / 插 %d' % (dropped, added))
