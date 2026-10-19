# -*- coding: utf-8 -*-
"""df_dungeon_check.py 补定向断言：挖掘场 98815 前导链 469（表外链）节点挂 __npc=2093
且点击落湿地 1437 航点（QuestPreNpcID → NPCLoc 全链）。幂等补丁。"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

P = r'D:/workspace/DungeonsForever/_temp/df_dungeon_check.py'
ANCHOR = '    -- 还原现场：后续 5722/5724 断言依赖原副本与原选中\r\n'
MARK = '98815 前导链 469 节点'

BLOCK = '''    -- ★★ 挖掘场新任务定向：98815 前置 469（表外链）→ QuestPreNpcID[469]=2093 → NPCLoc 落湿地航点
    do
      local _exd, _exq
      for _, dg in ipairs(TF_NS.DungeonData.dungeons) do
        if dg.id == "excavation_wetlands" then
          _exd = dg
          for _, qq in ipairs(DQ.QuestList(dg)) do
            if qq[1] == 98815 then _exq = qq break end
          end
          break
        end
      end
      ck("★ 挖掘场 98815 定位（前置 469 表外链）", _exd ~= nil and _exq ~= nil and _exq[9] ~= nil and _exq[9][1] == 469)
      if _exd and _exq then
        U.dungeonDetailCur = _exd
        U.dungeonQuestSel = _exq[1]
        U.dungeonQFilter = "all"
        U.dungeonQSide = "all"
        U:RenderDungeonQuests()
        local _n469
        for _, nd in ipairs(U.dungeonQDetPool.node) do
          if nd.__shown and nd.__preID == 469 then _n469 = nd break end
        end
        ck("]]''' + '"' + MARK + '''挂 __npc=2093（QuestPreNpcID 兜底）",
           _n469 ~= nil and _n469.__npc == 2093, tostring(_n469 and _n469.__npc))
        if _n469 then
          C_MAP_MARK.wp, C_MAP_MARK.opened = nil, nil
          _n469.__scripts.OnClick(_n469)
          ck("★ 点 469 节点 → 落埃纳尔·石钳湿地航点 + 开图 1437",
             IS_FOREVER and C_MAP_MARK.opened == 1437 and C_MAP_MARK.wp ~= nil
             and C_MAP_MARK.wp.uiMapID == 1437,
             tostring(C_MAP_MARK.opened))
        end
      end
    end
'''

s = open(P, encoding='utf-8', newline='').read()
if MARK in s:
    print('[SAME] 已插入过')
    sys.exit(0)
n = s.count(ANCHOR)
if n != 1:
    raise SystemExit('[ABORT] 还原现场锚点命中 %d 次' % n)
s = s.replace(ANCHOR, BLOCK + ANCHOR, 1)
compile(s, P, 'exec')
open(P, 'w', encoding='utf-8', newline='').write(s.replace('\r\n', '\n').replace('\n', '\r\n'))
print('[OK] 已插入定向断言')
