# -*- coding: utf-8 -*-
"""复核问题 C 的证据：
 1) SwitchSub 大锚点在「当前 beta DungeonUI」与「改动前备份」各 count 一次
 2) 本次对 DungeonUI 的改动是否纯插入（difflib +N/-N）
 3) ProfessionUI.lua 是否被本次功能改过（git status）
 4) MUT_PROF_DETAIL_BACK 的锚点被谁吃掉
只读。
"""
import os
import re
import sys
import subprocess
import difflib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import df_mut_check as M  # noqa: E402

BETA = r'D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\DungeonsForever'
SRC = r'D:\workspace\DungeonsForever'
BAK = os.path.join(SRC, '_temp', '_lootfilter_bak')

print('=== 1) SwitchSub 大锚点计数 ===')
_, old, _ = M.split_spec(M.MUT_SWITCH_IGNORES_KEY)
print('  锚点行数 = %d, 含 CR = %s' % (old.count(b'\r\n'), b'\r' in old))
for label, p in [('当前 beta', os.path.join(BETA, 'Core', 'DungeonUI.lua')),
                 ('源仓库', os.path.join(SRC, 'Core', 'DungeonUI.lua')),
                 ('改动前备份', os.path.join(BAK, 'Core__DungeonUI.lua'))]:
    if os.path.exists(p):
        d = open(p, 'rb').read()
        print('  %-10s count=%d' % (label, d.count(old)))
    else:
        print('  %-10s MISSING' % label)

print()
print('=== 2) 本次 DungeonUI 改动是否纯插入（备份 vs 当前）===')
a = open(os.path.join(BAK, 'Core__DungeonUI.lua'), 'rb').read().decode('utf-8').splitlines()
b = open(os.path.join(SRC, 'Core', 'DungeonUI.lua'), 'rb').read().decode('utf-8').splitlines()
plus = minus = 0
for line in difflib.unified_diff(a, b, lineterm='', n=0):
    if line.startswith('+++') or line.startswith('---') or line.startswith('@@'):
        continue
    if line.startswith('+'):
        plus += 1
    elif line.startswith('-'):
        minus += 1
print('  +%d / -%d' % (plus, minus))

print()
print('=== 3) 本次功能改过的文件（git status）===')
r = subprocess.run(['git', 'status', '--porcelain'], cwd=SRC,
                   capture_output=True, text=True, encoding='utf-8', errors='replace')
for line in (r.stdout or '').splitlines():
    if 'ProfessionUI' in line or 'LootFilter' in line or 'DungeonUI' in line or 'MainFrame' in line or 'toc' in line:
        print('  %s' % line)

print()
print('=== 4) 谁吃掉了 MUT_PROF_DETAIL_BACK 的锚点 ===')
prof = open(os.path.join(BETA, 'Core', 'ProfessionUI.lua'), 'rb').read()
# 从归一化后的 MUTATIONS 里按名字取锚点（与 harness 实际使用的一致）
by_name = {nm: M.split_spec(sp) for nm, sp in M.MUTATIONS}
f_detail, a_detail, _ = by_name['专业页：配方详情条长回来']
f_grid, a_grid, n_grid = by_name['总览宫格：Build 里的挂载被摘（宫格永不出现）']
print('  DETAIL_BACK 锚点 repr = %r' % a_detail)
print('  IX_GRID     锚点 repr = %r' % a_grid)
print('  两锚点相同 = %s' % (a_detail == a_grid))
print('  原始 ProfessionUI：DETAIL_BACK 锚点 count = %d, IX_GRID 锚点 count = %d'
      % (prof.count(a_detail), prof.count(a_grid)))
after = prof.replace(a_grid, n_grid)
print('  先注入 IX_GRID（吃掉了那行）后：DETAIL_BACK 锚点 count = %d' % after.count(a_detail))
print('  ProfessionUI.lua 是否在本次功能变更清单：%s'
      % ('否（git status 未列出）' if 'ProfessionUI' not in (r.stdout or '') else '是'))
# 顺序：DETAIL_BACK 在 MUTATIONS 里的下标是否晚于 IX_GRID
order = [nm for nm, _ in M.MUTATIONS]
print('  MUTATIONS 顺序：IX_GRID @%d, DETAIL_BACK @%d → 前者先注入 = %s'
      % (order.index('总览宫格：Build 里的挂载被摘（宫格永不出现）'),
         order.index('专业页：配方详情条长回来'),
         order.index('总览宫格：Build 里的挂载被摘（宫格永不出现）')
         < order.index('专业页：配方详情条长回来')))
