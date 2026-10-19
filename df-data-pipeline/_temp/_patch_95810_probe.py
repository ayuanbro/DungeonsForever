# -*- coding: utf-8 -*-
"""df_dungeon_check.py 补定向断言：挖掘场 98824 前导链 95810 节点 → QuestPreNpcID[95810]=1077
→ 落勘察员维尔加湿地航点（1437）。幂等补丁（注意 df_dungeon_check.py 是 CRLF）。"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

P = r'D:/workspace/DungeonsForever/_temp/df_dungeon_check.py'
ANCHOR = '    -- 还原现场：后续 5722/5724 断言依赖原副本与原选中\r\n'
MARK = '98824 前导链 95810 节点'

BLOCK = '''    -- ★★ 挖掘场 98824 前置链定向：前置 95810（物品起始、行内无 NPCID）→ QuestPreNpcID[95810]=1077 → 落维尔加湿地航点
    do
      local _pd, _pq
      for _, dg in ipairs(TF_NS.DungeonData.dungeons) do
        if dg.id == "excavation_wetlands" then
          _pd = dg
          for _, qq in ipairs(DQ.QuestList(dg)) do
            if qq[1] == 98824 then _pq = qq break end
          end
          break
        end
      end
      ck("★ 挖掘场 98824 定位（前置 95810）", _pd ~= nil and _pq ~= nil and _pq[9] ~= nil and _pq[9][1] == 95810)
      if _pd and _pq then
        U.dungeonDetailCur = _pd
        U.dungeonQuestSel = _pq[1]
        U.dungeonQFilter = "all"
        U.dungeonQSide = "all"
        U:RenderDungeonQuests()
        local _n95810
        for _, nd in ipairs(U.dungeonQDetPool.node) do
          if nd.__shown and nd.__preID == 95810 then _n95810 = nd break end
        end
        ck("''' + MARK + '''挂 __npc=1077（QuestPreNpcID 兜底）",
           _n95810 ~= nil and _n95810.__npc == 1077, tostring(_n95810 and _n95810.__npc))
        if _n95810 then
          C_MAP_MARK.wp, C_MAP_MARK.opened = nil, nil
          _n95810.__scripts.OnClick(_n95810)
          ck("★ 点 95810 节点 → 落勘察员维尔加湿地航点 + 开图 1437",
             IS_FOREVER and C_MAP_MARK.opened == 1437 and C_MAP_MARK.wp ~= nil
             and C_MAP_MARK.wp.uiMapID == 1437 and C_MAP_MARK.wp.x == TF_NS.NPCLoc[1077][2] / 100,
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
block = BLOCK.replace('\n', '\r\n')
s = s.replace(ANCHOR, block + ANCHOR, 1)
compile(s, P, 'exec')
open(P, 'w', encoding='utf-8', newline='').write(s)
print('[OK] 已插入定向断言')
