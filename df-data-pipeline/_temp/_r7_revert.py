# -*- coding: utf-8 -*-
"""第七轮 ④：把「生成器链跑动带出的、非本轮 scope 的外溢文件」还原为 beta 基准态。

背景（见 _r7_regress.txt / _r7_diff_probe.txt）：
  全链跑动除产生本轮 3 个 ClassGuide 产物外，还改动了 4 个「并行 WIP 域」文件：
    - Core/Data/Data_Professions.lua        （steps_note：zh.json 里未回灌的源改动被带出）
    - Core/Data/enUS/Data_Professions.lua
    - Core/Data/zhTW/Data_Professions.lua
    - Core/Data/enUS/Data_LootFilter.lua    （LootFilter WIP 的手写占位被半机翻覆盖层冲掉）
  git 显示这些属活动 WIP 域（Data_Professions 为 tracked-且-已改；enUS/Data_LootFilter 为
  untracked 新件、beta 内存放的是该 WIP 刻意留的占位）。为「零漂移 + 不碰并行 WIP」，
  将这 4 个文件从 beta 基准还原。本轮只保留 3 个 ClassGuide 产物。

用法：python _r7_revert.py [--apply]   （默认 dry-run，仅打印将要还原的文件与 md5）
输出：_temp/_r7_revert.txt
"""
import hashlib
import io
import os
import shutil
import sys

DF = r'D:\workspace\DungeonsForever'
BETA = r'D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\DungeonsForever'
OUT = os.path.join(DF, '_temp', '_r7_revert.txt')
APPLY = '--apply' in sys.argv

REVERT = [
    'Core/Data/Data_Professions.lua',
    'Core/Data/enUS/Data_Professions.lua',
    'Core/Data/zhTW/Data_Professions.lua',
    'Core/Data/enUS/Data_LootFilter.lua',
]


def md5(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()


lines = []
w = lines.append
w('=' * 78)
w('第七轮 ④ · 外溢文件还原（beta 基准）  apply=%s' % APPLY)
w('=' * 78)
for rel in REVERT:
    b = os.path.join(BETA, rel)
    s = os.path.join(DF, rel)
    if not os.path.exists(b):
        w('!! beta 缺 %s —— 跳过' % rel)
        continue
    before = md5(s)
    if APPLY:
        shutil.copy2(b, s)
    after = md5(s)
    w('%-42s beta=%s  src(before)=%s  src(after)=%s  %s'
      % (rel, md5(b)[:12], before[:12], after[:12],
         ('已还原' if APPLY and before != after else ('本就一致' if before == md5(b) else ''))))
w('')
w('★ 本轮保留的 scope 内产物（不还原）：')
for rel in ('Core/Data/Data_ClassGuide.lua',
            'Core/Data/enUS/Data_ClassGuide.lua',
            'Core/Data/zhTW/Data_ClassGuide.lua'):
    w('    %s' % rel)

text = '\n'.join(lines) + '\n'
io.open(OUT, 'w', encoding='utf-8', newline='\n').write(text)
print(text)
