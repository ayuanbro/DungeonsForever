# -*- coding: utf-8 -*-
"""强制 vis=true（真机视口模式）复现训练师页空白。

PaintRows 971-985：vis 判定 = GetVerticalScroll/GetHeight/GetTop 全回数字。
探针桩默认回 table ⇒ vis=false 全量路径 ⇒ 与真机不同。
本探针渲染前覆写 scroll 三 getter 回数字，复现真机路径。
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = r'D:\Game\World of Warcraft\_classic_titan_\Interface\AddOns\BGLite\_temp\tools'
sys.path.insert(0, TOOLS)
sys.path.insert(0, HERE)
import tf_dryrun as T  # noqa: E402
from lupa import lua51  # noqa: E402

ADDON = (os.environ.get('DF_ADDON_ROOT')
         or r'D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\DungeonsForever')
TOC = os.path.join(ADDON, 'DungeonsForever.toc')

BUILD = r'''
do
  UnitLevel = UnitLevel or function() return 60 end
  if TF_NS.hui then TF_NS.hui.ReskinToggle = function() end end
  TF_NS.DungeonUI:Build()
  TF_NS.DungeonUI:SwitchSub("Professions")
end
'''

FORCE_VIS = r'''
(function()
  local PD = TF_NS.ProfModule
  local sc = PD.scroll
  if not sc then return 'no-scroll' end
  sc.GetVerticalScroll = function() return 0 end
  sc.GetHeight = function() return 600 end
  sc.GetTop = function() return 500 end
  return 'vis-forced'
end)()
'''

RENDER_TRAINER = r'''
(function()
  local PD = TF_NS.ProfModule
  PD.sweeping = true
  PD.Show("blacksmithing")
  PD.SetTab("trainer")
  PD.Render()
  local out = {}
  out[#out+1] = 'visMode=' .. tostring(PD.visMode)
  out[#out+1] = 'wantBoard=' .. tostring(PD.wantTrainerBoard)
  out[#out+1] = 'card=' .. tostring(PD.trainerCard and PD.trainerCard.__shown)
  local rw = PD.trainerBoard and PD.trainerBoard.__w or nil
  local rh = PD.trainerBoard and PD.trainerBoard.__h or nil
  out[#out+1] = 'rootWH=' .. tostring(rw) .. 'x' .. tostring(rh)
  out[#out+1] = 'root=' .. tostring(PD.trainerBoard and PD.trainerBoard.__shown)
  local fa, fh = PD.trFacBtns and PD.trFacBtns.A, PD.trFacBtns and PD.trFacBtns.H
  out[#out+1] = 'facBtn=' .. tostring(fa and fa.__trKey) .. '/' .. tostring(fh and fh.__trKey)
  out[#out+1] = 'trFac=' .. tostring(PD.trFac)
  local nA, nH = 0, 0
  for _, c in ipairs(PD.trainerBoard.__chips or {}) do
    local t = c.__tr
    if t then
      if t.fac == 'A' then nA = nA + 1 elseif t.fac == 'H' then nH = nH + 1 end
    end
  end
  out[#out+1] = ('facCount=%dA/%dB'):format(nA, nH)
  out[#out+1] = 'boardH=' .. tostring(PD.trainerBoardH)
  local fsN, fsShown = 0, 0
  if PD.trainerBoard and PD.trainerBoard.__fs then
    for _, f in pairs(PD.trainerBoard.__fs) do
      fsN = fsN + 1
      if f.__shown then fsShown = fsShown + 1 end
    end
  end
  out[#out+1] = ('fs=%d/%d'):format(fsShown, fsN)
  local chips, shown = 0, 0
  if PD.trainerBoard and PD.trainerBoard.__chips then
    for _, c in ipairs(PD.trainerBoard.__chips) do
      chips = chips + 1
      if c.__shown then shown = shown + 1 end
    end
  end
  out[#out+1] = ('chips=%d/%d'):format(shown, chips)
  return table.concat(out, ' ')
end)()
'''


def build_lua():
    addon = ADDON
    toc = open(os.path.join(addon, os.path.basename(TOC)),
               encoding='utf-8', errors='replace').read()
    files = [re.sub(r'\s*\[[^\]]*\]\s*$', '', l.strip()).replace('\\', '/')
             for l in toc.splitlines()
             if l.strip() and not l.strip().startswith('##')]
    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    stub = T.STUB.replace(
        '            elseif NUMERIC[k] then f = function() return 100 end',
        '            elseif k == "GetStringWidth" then'
        ' f = function(self) return #(self.__text or "") * 6 end\n'
        '            elseif NUMERIC[k] then f = function() return 100 end', 1)
    assert stub != T.STUB, 'GetStringWidth 桩补丁没生效'
    lua.execute(stub)
    lua.execute('PUMPS = {}')
    lua.execute('C_Timer = { After = function(t, fn) PUMPS[#PUMPS + 1] = fn end }')
    lua.execute('os = nil')
    lua.execute('time = function() return 1796850000 - 3660 end')
    lua.execute("BG.hui.OnThemeChange = function(fn) end")
    lua.execute('UnitClass = function() return "战士", "WARRIOR", 1 end')
    lua.execute('UnitLevel = function() return 60 end')
    lua.execute('BG.hui = nil')
    lua.execute('ADDON_ROOT = %r' % addon.replace('\\', '/'))
    lua.execute('TF_NS = TF_NS or {}')
    lua.execute('do local orig = GetBuildInfo; GetBuildInfo = function(...) '
                'local a, b, c, d = orig(...); return a, b, c, 16001, d end end')
    lua.execute(r'''
UIErrorsFrame = { AddMessage = function() end }
C_Map = {
  CanSetUserWaypointOnMap = function() return true end,
  SetUserWaypoint = function(pt) end,
  OpenWorldMap = function(mapID) end,
  GetAreaInfo = function(id) return "测区" .. tostring(id) end,
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
            raise RuntimeError('加载 %s 失败（loadfile nil）' % rel)
        chunk()
    return lua


def drain(lua):
    lua.eval('(function() while #PUMPS > 0 do table.remove(PUMPS, 1)() end return 1 end)()')


def main():
    lua = build_lua()
    lua.execute(BUILD)
    print('scroll 补丁:', lua.eval(FORCE_VIS))
    print('=== 锻造训练师页（强制 vis=true） ===')
    try:
        lua.eval('TF_NS.ProfModule.Show("blacksmithing")')
        drain(lua)
        r = lua.eval(RENDER_TRAINER)
        drain(lua)
        print(r)
        if 'rootWH=nilxnil' in r:
            print('★★ trainerBoard root 无尺寸（0 尺寸帧真机渲染不可信）！')
            return 1
        if 'facBtn=nil/nil' in r:
            print('★★ 阵营按钮未落位！')
            return 1
        r2 = lua.eval('''(function()
  local PD = TF_NS.ProfModule
  PD.trFac = "H"
  PD.Render()
  local fa, fh = PD.trFacBtns.A, PD.trFacBtns.H
  local nA, nH = 0, 0
  for _, c in ipairs(PD.trainerBoard.__chips or {}) do
    local t = c.__tr
    if t then
      if t.fac == "A" then nA = nA + 1 elseif t.fac == "H" then nH = nH + 1 end
    end
  end
  return ('trFac=%s keyH=%s chips=%dA/%dB boardH=%s')
    :format(tostring(PD.trFac), tostring(fh.__trKey), nA, nH, tostring(PD.trainerBoardH))
end)()''')
        drain(lua)
        print('切部落:', r2)
        if 'chips=0A/0B' in r2 or '/0B' in r2:
            print('★★ 切部落后本阵营训练师为空！')
            return 1
        r3 = lua.eval('''(function()
  local PD = TF_NS.ProfModule
  PD.trFac = "A"
  PD.Render()
  local nA, nH = 0, 0
  for _, c in ipairs(PD.trainerBoard.__chips or {}) do
    local t = c.__tr
    if t then
      if t.fac == "A" then nA = nA + 1 elseif t.fac == "H" then nH = nH + 1 end
    end
  end
  return ('trFac=%s chips=%dA/%dB'):format(tostring(PD.trFac), nA, nH)
end)()''')
        drain(lua)
        print('切回联盟:', r3)
        if '/0A' in r3:
            print('★★ 切回联盟后联盟训练师为空！')
            return 1
    except Exception as e:
        print('★★ 渲染抛错：%s' % e)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
