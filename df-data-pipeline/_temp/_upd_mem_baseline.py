# -*- coding: utf-8 -*-
import io

p = r'D:/workspace/DungeonsForever/.workbuddy/memory/MEMORY.md'
s = io.open(p, encoding='utf-8', newline='').read()
BT = chr(96)  # backtick
NL = chr(13) + chr(10)  # CRLF

old = ('## 基线（2026-09-30 · 职业指南页第三轮后）' + NL + NL
       + BT + 'run_all_checks.py' + BT + ' **五项全绿**：'
       + BT + 'qa_lf_verify' + BT + ' **244/0** / '
       + BT + 'df_dungeon_check' + BT + ' **966/0** / '
       + BT + '_qa_probe_spec' + BT + ' **75/0** / '
       + BT + 'strip_comments --selftest' + BT + ' 12/12 / '
       + BT + 'df_mut_check' + BT + ' exit 0。真 Lua 5.1 全过、两侧零漂移。')
assert s.count(old) == 1, s.count(old)

new = ('## 基线（2026-10-04 · 图钉扩展收口）' + NL + NL
       + BT + 'run_all_checks.py' + BT + ' **五项全绿**；'
       + BT + 'df_dungeon_check' + BT + ' **1484（16001）/ 1220（38002）双端 0**；'
       '变异 **387 条 / 坏锚点 0**；'
       + BT + 'lua51_check' + BT + ' OK；'
       + BT + 'sync_beta.py' + BT + ' 零漂移。' + NL +
       '- ★ 图钉扩展口径：ns.MapPins（Data_MapPins.lua，fc_pins.py 生成）= 入口/任务/物品/稀有四类；'
       'SyncPins = boss 在前 + extras 按 entrance→quest→object→rare 追加，extras 无层号只落第 1 层；'
       'boss 钉体=金骷髅恒定（颜色即身份只在名字）、稀有银染 (0.72,0.76,0.85)、'
       '任务=客户端黄「!」、入口=Media/MapDoor.tga、物品=DG.ItemIcon；'
       '任务钉点击→任务页选中；开关「隐藏图钉」藏全部；HasPins 计入 extras。')

s = s.replace(old, new, 1)
io.open(p, 'w', encoding='utf-8', newline='').write(s)
print('MEMORY.md 基线节已更新')
