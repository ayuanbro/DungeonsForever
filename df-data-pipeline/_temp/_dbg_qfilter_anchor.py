# -*- coding: utf-8 -*-
"""任务页筛选行首入锚点竞态探针：首入 quest vs 切页后回 quest，dump 1-5 号按钮锚点。"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import importlib.util as ilu

spec = ilu.spec_from_file_location('qbadge', os.path.join(HERE, '_dbg_qbadge_cls.py'))
qbadge = ilu.module_from_spec(spec)
spec.loader.exec_module(qbadge)
qbadge_main = qbadge.__dict__

BUILD2 = r'''
(function()
  local U = TF_NS.DungeonUI
  if TF_NS.hui then TF_NS.hui.ReskinToggle = function() end end
  C_QuestLog = C_QuestLog or {}
  C_QuestLog.GetTitleForQuestID = function(id) return "任务" .. tostring(id) end
  local DGx = TF_NS.ProfHost and TF_NS.ProfHost.DG
  if DGx then DGx.HarvestTipName = function() return nil end end
  TF_NS.DungeonUI:Build()
  local d
  for _, x in ipairs(TF_NS.DungeonData.dungeons) do
    if x.id == "shadowfang_keep" then d = x end
  end
  U:ShowDungeonDetail(d)
  U:SetDungeonTab("quest")
end)()
'''

DUMP_BTNS = r'''
(function()
  local U = TF_NS.DungeonUI
  local out = {}
  local function p(s) out[#out+1] = s end
  local fb = U.dungeonFilterBtns or {}
  local plateOk = U.dungeonQPlateL ~= nil
  p('plateL=' .. tostring(plateOk) .. ' tab=' .. tostring(U.dungeonTab))
  for i = 1, 5 do
    local bt = fb[i]
    if bt then
      local t = bt.__pts
      local rel = 'nil'
      if t and t[2] then
        rel = tostring(t[2])
        if U.dungeonQPlateL and t[2] == U.dungeonQPlateL then rel = 'PLATE_L'
        elseif U.dungeonDetail and t[2] == U.dungeonDetail then rel = 'DETAIL' end
      end
      local xy = 'x=nil,y=nil'
      if t then xy = string.format('x=%s,y=%s',
        (type(t[4]) == 'number') and string.format('%.0f', t[4]) or '?',
        (type(t[5]) == 'number') and string.format('%.0f', t[5]) or '?') end
      p(string.format('btn%d mode=%s key=%s anchor=%s %s w=%s shown=%s',
        i, tostring(bt.__mode), tostring(bt.__key), rel, xy,
        (type(bt.__w) == 'number') and string.format('%.0f', bt.__w) or '?',
        tostring(bt.__shown)))
    else
      p('btn' .. i .. '=nil')
    end
  end
  return table.concat(out, '\n')
end)()
'''


def main():
    lua = qbadge_main['build_lua']()
    lua.execute(BUILD2)
    qbadge_main['drain'](lua)
    print('=== 首入 quest（Build→ShowDungeonDetail→SetDungeonTab(quest)）===')
    print(lua.eval(DUMP_BTNS))
    lua.eval('(function() TF_NS.DungeonUI:SetDungeonTab("loot") end)()')
    qbadge_main['drain'](lua)
    print('=== 切到 loot ===')
    print(lua.eval(DUMP_BTNS))
    lua.eval('(function() TF_NS.ProfHost.DG.ApplyLootDropdownChrome() end)()')
    print('--- 单跑 ApplyLootDropdownChrome 后 ---')
    print(lua.eval(DUMP_BTNS))
    lua.eval('(function() TF_NS.ProfHost.DG.ApplyDetailChrome("loot") end)()')
    print('--- 再跑 ApplyDetailChrome(loot) 后 ---')
    print(lua.eval(DUMP_BTNS))
    lua.eval('(function() TF_NS.DungeonUI:SetDungeonTab("quest") end)()')
    qbadge_main['drain'](lua)
    print('=== 再切回 quest ===')
    print(lua.eval(DUMP_BTNS))
    return 0


if __name__ == '__main__':
    sys.exit(main())
