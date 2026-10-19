# -*- coding: utf-8 -*-
"""训练师页 / 配方「全部」页签 · 动态渲染探针（2026-10-12 用户真机报两页空白）。

走真渲染链路（PD.Show → PD.SetTab → PD.Render），不加 pcall 吞错：
  - enchanting 配方页 toolKey=all：数 specs（应为 enchants 171 截到 ROW_CAP）
  - enchanting 训练师页：数 trainerBoard 显示中的 chips + 板卡高度
任一页 specs/内容为 0 或渲染抛错 → 退出码 1。
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

RENDER_RECIPE_ALL = r'''
(function()
  local PD = TF_NS.ProfModule
  PD.sweeping = true
  PD.Show("enchanting")
  PD.SetTab("recipe")
  PD.toolKey = "all"
  PD.Render()
  return #(PD.specs or {})
end)()
'''

RENDER_TRAINER = r'''
(function()
  local PD = TF_NS.ProfModule
  PD.sweeping = true
  PD.Show("enchanting")
  PD.SetTab("trainer")
  PD.Render()
  local out = {}
  out[#out+1] = 'specs=' .. #(PD.specs or {})
  out[#out+1] = 'wantBoard=' .. tostring(PD.wantTrainerBoard)
  out[#out+1] = 'boardCard=' .. tostring(PD.trainerCard and PD.trainerCard.__shown)
  out[#out+1] = 'boardH=' .. tostring(PD.trainerBoardH)
  local chips, shown = 0, 0
  if PD.trainerBoard and PD.trainerBoard.__chips then
    for _, c in ipairs(PD.trainerBoard.__chips) do
      chips = chips + 1
      if c.__shown then shown = shown + 1 end
    end
  end
  out[#out+1] = ('chips=%d/%d'):format(shown, chips)
  local d = TF_NS.ProfTrainers and TF_NS.ProfTrainers[PD.cur]
  out[#out+1] = 'data=' .. tostring(d and d.list and #d.list or 'nil') .. '(cur=' .. tostring(PD.cur) .. ')'
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
    lua.execute('UnitClass = function() return "盗贼", "ROGUE", 4 end')
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
    bad = 0
    # 静态红线：and nil or 陷阱（X and nil or Y 的 Y 恒被 or 吃回，用户定案禁用）
    src = open(os.path.join(ADDON, 'Core', 'ProfessionUI.lua'),
               'rb').read().decode('utf-8')
    hits = [i + 1 for i, line in enumerate(src.splitlines())
            if ' and nil or ' in line and '--' not in line.split(' and nil or ')[0]]
    if hits:
        print('★★ ProfessionUI.lua 残留 and-nil-or 陷阱，行：', hits)
        bad += 1

    lua = build_lua()
    lua.execute(BUILD)

    print('=== 附魔配方页 toolKey=all ===')
    try:
        lua.eval('TF_NS.ProfModule.Show("enchanting")')
        drain(lua)
        n = int(lua.eval(RENDER_RECIPE_ALL))
        drain(lua)
        print('specs = %d' % n)
        if n <= 0:
            print('★★ 配方「全部」页签 0 行！')
            bad += 1
    except Exception as e:
        print('★★ 渲染抛错：%s' % e)
        bad += 1

    print('\n=== 附魔训练师页 ===')
    try:
        r = lua.eval(RENDER_TRAINER)
        drain(lua)
        print(r)
        # 训练师页不走路池（specs=0 正常）；判据 = 板卡显示 + chips 全显示 + 数据在
        if 'boardCard=false' in r or 'chips=0/' in r or 'data=nil' in r:
            print('★★ 训练师页内容为空！')
            bad += 1
    except Exception as e:
        print('★★ 渲染抛错：%s' % e)
        bad += 1

    print('\n结论：%s' % ('有问题' if bad else '两页均正常'))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
