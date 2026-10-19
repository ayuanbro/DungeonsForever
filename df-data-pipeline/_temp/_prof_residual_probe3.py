# -*- coding: utf-8 -*-
"""配方→升级(购物清单)残留探针 · 价格模式 + 深度转储（2026-10-09 第三轮）。

用户 /reload 后仍见残留，而探针 1/2（无价格数据）全绿 ⇒ 补上实机有的条件：
Auctionator 价格桩（全程有价 → 路线行带价格、购物清单带单价/小计），
跑用户完整链路后逐行转储（行文本 + 可见材料块 + 可见分段链），找「内容与 spec 不符」的行。

用法：python _temp/_prof_residual_probe3.py [slug]
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
  -- ★ Auctionator 价格桩：任何物品都有价（模拟用户实机的已扫描状态）
  Auctionator = {
    API = { v1 = {
      GetAuctionPriceByItemID = function(caller, id)
        return ((tonumber(id) or 1) * 137) % 90000 + 40
      end,
      GetAuctionAgeByItemID = function(caller, id) return 0 end,
      GetVendorPriceByItemID = function(caller, id)
        return ((tonumber(id) or 1) * 137) % 900 + 5
      end,
    } },
    SavedState = { lastDatabase = { DEPRECATED_5_0_2 = { ScanTime = os_time_stub or 1796850000 } } },
  }
  TF_NS.DungeonUI:Build()
  TF_NS.DungeonUI:SwitchSub("Professions")
end
'''

PICK = r'''
(function()
  local NS, PD = TF_NS, TF_NS.ProfModule
  local LV = NS.ProfLeveling or {}
  local list = {}
  for _, s in ipairs((NS.ProfData or {}).order or {}) do
    if LV[s] then list[#list + 1] = s end
  end
  PD.lvSlugs = list
  return #list
end)()
'''

USE = r'''
(function(slug)
  local PD = TF_NS.ProfModule
  PD.sweeping = true
  PD.Show(slug); PD.SetTab("leveling")
  return slug
end)(...)
'''

SETPAGE = r'''
(function(mode)
  local PD = TF_NS.ProfModule
  PD.autoPage = mode
  PD.Render()
  return 1
end)(...)
'''

SETTAB = r'''
(function(mode)
  local PD = TF_NS.ProfModule
  PD.SetTab(mode)
  return PD.tab
end)(...)
'''

DUMP = r'''
(function()
  local PD = TF_NS.ProfModule
  local nspec = #(PD.specs or {})
  local maxi, gap = 0, 0
  for i = 1, 20000 do
    if PD.rows[i] then maxi = i; gap = 0 else gap = gap + 1; if gap > 40 then break end end
  end
  local function txt(fs)
    if type(fs) == "table" and fs.__text then return tostring(fs.__text) end
    return ""
  end
  local out = {}
  out[#out + 1] = ("page=%s tab=%s autoPage=%s specs=%d pool=%d shown?")
      :format(tostring(PD.cur), tostring(PD.tab), tostring(PD.autoPage), nspec, maxi)
  local shown = 0
  for i = 1, maxi do
    local r = PD.rows[i]
    if r and r.__shown then
      shown = shown + 1
      local spec = PD.specs and PD.specs[i]
      local blkN = 0
      if r.blk then
        for j = 1, #r.blk do
          if r.blk[j].ic and r.blk[j].ic.__shown then blkN = blkN + 1 end
        end
      end
      local fT = txt(r.f)
      out[#out + 1] = ("  row[%d] a=%q e=%q f=%q(%d) blk=%d spec=%s")
          :format(i, txt(r.a):sub(1, 18), txt(r.e):sub(1, 18), fT:sub(1, 30), #fT,
                  blkN, spec and (spec.kind .. (spec.lvstep and "+lv" or "")) or "nil")
    end
  end
  -- 非行池、仍显示、挂在 child 下的帧
  local inPool = {}
  for i = 1, maxi do inPool[PD.rows[i]] = true end
  for _, fr in ipairs(ALL_FRAMES or {}) do
    if rawget(fr, "__parent") == PD.child and fr.__shown and not inPool[fr] then
      local t = txt(fr.a) or ""
      out[#out + 1] = ("  STRAY %s w=%s h=%s a=%q")
          :format(tostring(fr.__name), tostring(fr.__w), tostring(fr.__h), t:sub(1, 24))
    end
  end
  out[#out + 1] = ("  shown=%d") : format(shown)
  local fh = io.open(ADDON_ROOT .. "/../_df_residue_dump.txt", "wb")
  fh:write(table.concat(out, "\n"))
  fh:close()
  return 1
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
    lua.execute(r'''
do
  local orig = CreateFrame
  ALL_FRAMES = {}
  CreateFrame = function(...)
    local o = orig(...)
    if type(o) == "table" then ALL_FRAMES[#ALL_FRAMES + 1] = o end
    return o
  end
end
''')
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


def pump_n(lua, n):
    lua.eval('(function(k) for _ = 1, k do if #PUMPS > 0 then table.remove(PUMPS, 1)() end end return 1 end)(%d)' % n)


def dump(lua, tag):
    lua.eval(DUMP)
    p = os.path.join(os.path.dirname(ADDON), '_df_residue_dump.txt')
    data = open(p, 'rb').read()
    print('---- %s ----' % tag)
    print(data.decode('utf-8', errors='replace'))


def main():
    lua = build_lua()
    lua.execute(BUILD)
    n = lua.eval(PICK)
    slugs = lua.eval('TF_NS.ProfModule.lvSlugs')
    only = sys.argv[1] if len(sys.argv) > 1 else None

    for i in range(1, int(n) + 1):
        slug = slugs[i]
        if only and slug != only:
            continue
        lua.eval(USE.replace('...', '"%s"' % slug))
        print('\n=== %s ===' % slug)
        # 用户完整链路（都建完再切，实机点击间隔 >> 建行时长）
        lua.eval(SETTAB.replace('...', '"recipe"'))
        drain(lua)
        lua.eval(SETTAB.replace('...', '"leveling"'))   # 落「路线」
        drain(lua)
        lua.eval(SETPAGE.replace('...', '"shop"'))
        drain(lua)
        dump(lua, 'shop-建完')

        # 半途窗口：配方建行中 → 路线 → 购物清单
        lua.eval(SETTAB.replace('...', '"recipe"'))
        pump_n(lua, 4)
        lua.eval(SETTAB.replace('...', '"leveling"'))
        lua.eval(SETPAGE.replace('...', '"shop"'))
        drain(lua)
        dump(lua, 'shop-半途窗口')

    return 0


if __name__ == '__main__':
    sys.exit(main())
