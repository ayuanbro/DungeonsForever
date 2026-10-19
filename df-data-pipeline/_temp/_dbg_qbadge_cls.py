# -*- coding: utf-8 -*-
"""任务行小卡片落点探针：渲染任务页行池，dump 名称/地图/等级/两枚 badge 的落点与宽度。"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = r'D:\Game\World of Warcraft\_classic_titan_\Interface\AddOns\BGLite\_temp\tools'
sys.path.insert(0, TOOLS)
sys.path.insert(0, HERE)
import tf_dryrun as T  # noqa: E402
from lupa import lua51  # noqa: E402

ADDON = (os.environ.get('DF_ADDON_ROOT') or r'D:\workspace\DungeonsForever')
TOC = os.path.join(ADDON, 'DungeonsForever.toc')

BUILD = r'''
(function()
  local U = TF_NS.DungeonUI
  if TF_NS.hui then TF_NS.hui.ReskinToggle = function() end end
  C_QuestLog = C_QuestLog or {}
  C_QuestLog.GetTitleForQuestID = function(id) return (id % 2 == 0) and "四字任务名" or "通缉：霍格与他的八个同伙" end
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

DUMP = r'''
(function()
  local U = TF_NS.DungeonUI
  local DG = TF_NS.ProfHost.DG
  local out = {}
  local function p(s) out[#out+1] = s end
  local function n(v) return (type(v) == 'number') and string.format('%.1f', v) or ('<'..type(v)..'>') end
  local function a(f)
    if not f then return 'nil' end
    local t = f.__pts
    if not t then return '__pts=nil' end
    return string.format('{%s,%s,%s,%s} w=%s', tostring(t[1]), tostring(t[3]), n(t[4]), n(t[5]), n(f.__w))
  end
  p('常量: Q_X_NAME='..n(DG.Q_X_NAME)..' Q_W_NAME='..n(DG.Q_W_NAME)..' Q_X_LOC='..n(DG.Q_X_LOC)
    ..' Q_W_LOC='..n(DG.Q_W_LOC)..' Q_X_LV='..n(DG.Q_X_LV)
    ..' BADGE_H='..n(DG.Q_BADGE_H)..' GAP='..n(DG.Q_BADGE_GAP)..' PAD='..n(DG.Q_BADGE_PAD))
  p('开关: tg='..tostring(U.dungeonQDoneTg ~= nil)
    ..' label="'..tostring(U.dungeonQDoneTg and U.dungeonQDoneTg.label and U.dungeonQDoneTg.label.__text)..'"'
    ..' '..(U.dungeonQDoneTg and a(U.dungeonQDoneTg) or '')
    ..' checked='..tostring(U.dungeonQDoneTg and U.dungeonQDoneTg.__checked))
  local function ob(bt)
    if not bt then return 'nil' end
    if type(bt.__outlineFrame) == 'table' then return bt.__outlineFrame.__shown and 'ON' or 'off' end
    if bt.__bars and bt.__bars[1] then return bt.__bars[1].__shown and 'ON' or 'off' end
    return 'no-outline'
  end
  local fb = U.dungeonFilterBtns or {}
  p('选中态 side='..tostring(U.dungeonQSide)..' | 1全部='..ob(fb[1])..' 2联盟='..ob(fb[2])..' 3部落='..ob(fb[3]))
  local function bd(b)
    if not b then return 'nil' end
    local hc = b.__huiCard
    local c = hc and hc.fill and hc.fill[1] and hc.fill[1].__huiGlass and hc.fill[1].__huiGlass.c
    return string.format('shown=%s x=%s w=%s txt=%s bg=%s', tostring(b.__shown),
      n(b.__pts and b.__pts[4]), n(b.__w),
      tostring(b.lab and b.lab.__text), c and string.format('%.2f/%.2f/%.2f', c[1], c[2], c[3]) or 'nil')
  end
  local qrow = U.dungeonQuestPool and U.dungeonQuestPool.row and U.dungeonQuestPool.row[1]
  p('徽章底色: preB='..bd(qrow and qrow.preB)..' | shareB='..bd(qrow and qrow.shareB))
  local dpool = U.dungeonQDetPool
  if dpool then
    local n1 = dpool.node and dpool.node[1]
    p('详情节点行1: bar='..tostring(n1 and n1.bar)..' name_x='..tostring(n1 and n1.name and n1.name.__pts and n1.name.__pts[4]))
    for i = 1, #(dpool.lab or {}) do
      local t = dpool.lab[i] and dpool.lab[i].__text
      if t then p('详情标签'..i..'='..tostring(t)) end
    end
  end
  local pool = U.dungeonQuestPool
  for i = 1, #pool.row do
    local r = pool.row[i]
    if r.__shown then
      local cs = {}
      local cbt = r.clsB
      if type(cbt) == 'table' then
        for k = 1, #cbt do cs[#cs+1] = 'clsB'..k..'='..bd(cbt[k]) end
      end
      p(string.format('row%d name="%s" %s | factionTex=%s | %s | preB=%s | shareB=%s',
        i, tostring(r.name.__text), a(r.name), a(r.em), table.concat(cs, ' '), a(r.preB), a(r.shareB)))
    end
  end
  return table.concat(out, '\n')
end)()
'''


DUMP_ONE = r'''
(function()
  local U = TF_NS.DungeonUI
  local out = {}
  local function p(s) out[#out+1] = s end
  local function ob(bt)
    if not bt then return 'nil' end
    if type(bt.__outlineFrame) == 'table' then return bt.__outlineFrame.__shown and 'ON' or 'off' end
    if bt.__bars and bt.__bars[1] then return bt.__bars[1].__shown and 'ON' or 'off' end
    return 'no-outline'
  end
  local fb = U.dungeonFilterBtns or {}
  p('选中态 side='..tostring(U.dungeonQSide)..' | 1全部='..ob(fb[1])..' 2联盟='..ob(fb[2])..' 3部落='..ob(fb[3]))
  return table.concat(out, '\n')
end)()
'''


def build_lua():
    toc = open(TOC, encoding='utf-8', errors='replace').read()
    files = [re.sub(r'\s*\[[^\]]*\]\s*$', '', l.strip()).replace('\\', '/')
             for l in toc.splitlines()
             if l.strip() and not l.strip().startswith('##')]
    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    stub = T.STUB.replace(
        '            elseif NUMERIC[k] then f = function() return 100 end',
        '            elseif k == "GetStringWidth" then'
        ' f = function(self) return #(self.__text or "") * 6 end\n'
        '            elseif NUMERIC[k] then f = function() return 100 end', 1)
    assert stub != T.STUB, 'GetStringWidth stub patch failed'
    lua.execute(stub)
    lua.execute('PUMPS = {}')
    lua.execute('C_Timer = { After = function(t, fn) PUMPS[#PUMPS + 1] = fn end }')
    lua.execute('os = nil')
    lua.execute('time = function() return 1796850000 - 3660 end')
    lua.execute("BG.hui.OnThemeChange = function(fn) end")
    lua.execute('UnitClass = function() return "战士", "WARRIOR", 1 end')
    lua.execute('UnitLevel = function() return 60 end')
    lua.execute('UnitFactionGroup = function() return "Horde" end')
    lua.execute('BG.hui = nil')
    lua.execute(r'''
RAID_CLASS_COLORS = {
  WARRIOR = { r = 0.78, g = 0.61, b = 0.43 }, PALADIN = { r = 0.96, g = 0.55, b = 0.73 },
  HUNTER = { r = 0.67, g = 0.83, b = 0.45 }, ROGUE = { r = 1.00, g = 0.96, b = 0.41 },
  PRIEST = { r = 1.00, g = 1.00, b = 1.00 }, SHAMAN = { r = 0.00, g = 0.44, b = 0.87 },
  MAGE = { r = 0.41, g = 0.80, b = 0.94 }, WARLOCK = { r = 0.58, g = 0.51, b = 0.79 },
  DRUID = { r = 1.00, g = 0.49, b = 0.04 },
}
''')
    lua.execute('ADDON_ROOT = %r' % ADDON.replace('\\', '/'))
    lua.execute('TF_NS = TF_NS or {}')
    lua.execute('do local orig = GetBuildInfo; GetBuildInfo = function(...) '
                'local a, b, c, d = orig(...); return a, b, c, 16001, d end end')
    lua.execute(r'''
UIErrorsFrame = { AddMessage = function() end }
C_Map = {
  CanSetUserWaypointOnMap = function() return true end,
  SetUserWaypoint = function(pt) end,
  OpenWorldMap = function(mapID) end,
  GetAreaInfo = function(id) return "test area" .. tostring(id) end,
}
''')
    loadfile = lua.eval(
        'function(rel)\n'
        '  local chunk = loadfile(ADDON_ROOT .. "/" .. rel)\n'
        '  if not chunk then return nil end\n'
        '  return function() return chunk("DungeonsForever", TF_NS) end\n'
        'end')
    for rel in files:
        if rel.lower().endswith('.xml'):
            continue
        chunk = loadfile(rel)
        if chunk is None:
            raise RuntimeError('load %s failed (loadfile nil)' % rel)
        chunk()
    return lua


def drain(lua):
    lua.eval('(function() while #PUMPS > 0 do table.remove(PUMPS, 1)() end return 1 end)()')


def main():
    lua = build_lua()
    lua.execute(BUILD)
    drain(lua)
    print(lua.eval(DUMP))
    print('--- 切到「全部」后 ---')
    lua.eval('(function() TF_NS.DungeonUI:SetQuestSide("all") end)()')
    drain(lua)
    print(lua.eval(DUMP_ONE))
    return 0


if __name__ == '__main__':
    sys.exit(main())
