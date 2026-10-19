# -*- coding: utf-8 -*-
"""配方页 → 升级页（购物清单子页）残留探针（2026-10-09）。

用户报障路径：点开专业的「配方」页签 → 再点「升级」页签（子页停在购物清单），
购物清单页上出现上一页的材料残留。既有 _prof_residual_probe.py 场景 E 切的是
「路线」子页，本探针补「购物清单」子页 + 分帧窗口各阶段 + 内容级残留检查。

内容级检查：显示中的行，spec 不是 lvstep 但 r.e（升级行配方名列）/ blk（材料块）
仍挂着内容 ⇒ 上一页内容没除干净。

用法：python _temp/_prof_residual_probe2.py
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

RESET = r'''
(function()
  local PD = TF_NS.ProfModule
  for i = #PD.rows, 1, -1 do if PD.rows[i] then PD.rows[i]:Hide() end end
  PD.rows = {}
  PD.__pendRows = {}
  return 1
end)()
'''

SCAN = r'''
(function()
  local PD = TF_NS.ProfModule
  local nspec = #(PD.specs or {})
  local maxi = 0
  local gap = 0
  for i = 1, 20000 do
    if PD.rows[i] then maxi = i; gap = 0 else gap = gap + 1; if gap > 40 then break end end
  end
  local function txt(fs)
    if type(fs) == "table" and fs.__text then return tostring(fs.__text) end
    return "-"
  end
  local shown, extra, detail = 0, 0, {}
  for i = 1, maxi do
    local r = PD.rows[i]
    if r and r.__shown then
      shown = shown + 1
      if i > nspec then
        extra = extra + 1
        if #detail < 12 then detail[#detail + 1] = i .. ":" .. txt(r.e) .. "/" .. txt(r.a) end
      end
    end
  end
  -- 内容级残留：显示中的行 i<=nspec，spec 不是 lvstep 但 e 列 / blk 还有内容
  local stale, staleDetail = 0, {}
  for i = 1, math.min(nspec, maxi) do
    local r = PD.rows[i]
    local spec = PD.specs and PD.specs[i] or nil
    if r and r.__shown and spec and spec.kind == "row" and not spec.lvstep then
      local hasE = txt(r.e) ~= "" and txt(r.e) ~= "-"
      local hasBlk = false
      if r.blk then
        for j = 1, #r.blk do
          if r.blk[j].ic and r.blk[j].ic.__shown then hasBlk = true break end
        end
      end
      if hasE or hasBlk then
        stale = stale + 1
        if #staleDetail < 8 then
          staleDetail[#staleDetail + 1] = i .. ":e=" .. txt(r.e) .. ",blk=" .. tostring(hasBlk)
        end
      end
    end
  end
  local function cnt(list)
    local c = 0
    for i = 1, #(list or {}) do if list[i] and list[i].__shown then c = c + 1 end end
    return c
  end
  return nspec, maxi, shown, extra, table.concat(detail, " | "),
         cnt(PD.secCards), cnt(PD.secGoldCards),
         stale, table.concat(staleDetail, " | ")
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
    # 追踪所有 CreateFrame 产物 + 版本号打桩（Core.lua 按版本号门控模块注册）
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


def scan(lua, tag):
    (nspec, maxi, shown, extra, detail,
     sec, gsec, stale, staleDetail) = lua.eval(SCAN)
    print('  [%-9s] specs=%-4s 池到=%-4s 显示=%-4s 超出行=%-3s 内容残留=%-3s 金卡=%s/%s'
          % (tag, nspec, maxi, shown, extra, stale, sec, gsec))
    if detail:
        print('        超出行: %s' % detail)
    if staleDetail:
        print('        内容残留: %s' % staleDetail)
    return int(extra) + int(stale)


def main():
    lua = build_lua()
    lua.execute(BUILD)
    n = lua.eval(PICK)
    print('有升级数据的专业 = %s 个' % n)
    slugs = lua.eval('TF_NS.ProfModule.lvSlugs')

    bad = 0
    for i in range(1, int(n) + 1):
        slug = slugs[i]
        lua.eval(USE.replace('...', '"%s"' % slug))
        print('\n=== %s ===' % slug)

        # ── F（用户报的路径）：配方页(建完) → 升级页·购物清单 ──
        lua.eval(RESET)
        lua.eval(SETTAB.replace('...', '"recipe"'))
        drain(lua)
        scan(lua, 'recipe')
        lua.eval(SETPAGE.replace('...', '"shop"'))
        lua.eval(SETTAB.replace('...', '"leveling"'))
        drain(lua)
        s = scan(lua, 'lv-shop')
        if s > 0:
            bad += 1
            print('    ★★ F 配方页 → 升级页(购物清单)后有残留！')

        # ── G（用户报的路径反过来）：升级页·购物清单(建完) → 配方页 → 升级页·购物清单 ──
        lua.eval(SETTAB.replace('...', '"recipe"'))
        drain(lua)
        lua.eval(SETTAB.replace('...', '"leveling"'))
        drain(lua)
        s = scan(lua, 'lv-shop2')
        if s > 0:
            bad += 1
            print('    ★★ G 购物清单 → 配方 → 购物清单后有残留！')

        # ── H（分帧窗口）：配方页建到一半 → 切升级页·购物清单 ──
        lua.eval(RESET)
        lua.eval(SETTAB.replace('...', '"recipe"'))
        pump_n(lua, 5)          # 只建前几帧，行还在排队
        scan(lua, 'recipe-半')
        lua.eval(SETPAGE.replace('...', '"shop"'))
        lua.eval(SETTAB.replace('...', '"leveling"'))
        drain(lua)
        s = scan(lua, 'lv-shopH')
        if s > 0:
            bad += 1
            print('    ★★ H 配方页半途 → 升级页(购物清单)后有残留！')

        # ── I（空池窗口）：清空行池 → 配方页(全在排队，一帧没建) → 切升级页·购物清单 ──
        lua.eval(RESET)
        lua.eval(SETTAB.replace('...', '"recipe"'))
        scan(lua, 'recipe-0帧')
        lua.eval(SETPAGE.replace('...', '"shop"'))
        lua.eval(SETTAB.replace('...', '"leveling"'))
        drain(lua)
        s = scan(lua, 'lv-shopI')
        if s > 0:
            bad += 1
            print('    ★★ I 空池配方页全排队 → 升级页(购物清单)后有残留！')

        # ── J：升级页·购物清单建完 → 配方页 → 只 drain 一半 → 切回升级页·购物清单 ──
        lua.eval(SETTAB.replace('...', '"recipe"'))
        pump_n(lua, 3)
        lua.eval(SETTAB.replace('...', '"leveling"'))
        drain(lua)
        s = scan(lua, 'lv-shopJ')
        if s > 0:
            bad += 1
            print('    ★★ J 配方页半途排队中 → 升级页(购物清单)后有残留！')

        # ── K（用户完整链路）：配方页(建完) → 升级页·路线(建完) → 购物清单 ──
        lua.eval(RESET)
        lua.eval(SETTAB.replace('...', '"recipe"'))
        drain(lua)
        scan(lua, 'recipe')
        lua.eval(SETTAB.replace('...', '"leveling"'))   # 升级页默认落「路线」
        lua.eval(SETPAGE.replace('...', '"route"'))
        drain(lua)
        scan(lua, 'lv-route')
        lua.eval(SETPAGE.replace('...', '"shop"'))
        drain(lua)
        s = scan(lua, 'lv-shopK')
        if s > 0:
            bad += 1
            print('    ★★ K 配方 → 路线 → 购物清单后有残留！')

        # ── L：配方页半途 → 路线(不 drain) → 购物清单 → drain ──
        lua.eval(RESET)
        lua.eval(SETTAB.replace('...', '"recipe"'))
        pump_n(lua, 4)
        lua.eval(SETTAB.replace('...', '"leveling"'))
        lua.eval(SETPAGE.replace('...', '"route"'))
        pump_n(lua, 2)
        lua.eval(SETPAGE.replace('...', '"shop"'))
        drain(lua)
        s = scan(lua, 'lv-shopL')
        if s > 0:
            bad += 1
            print('    ★★ L 配方半途 → 路线半途 → 购物清单后有残留！')

        # ── M：购物清单(建完) → 路线半途 → 购物清单 ──
        lua.eval(SETPAGE.replace('...', '"shop"'))
        drain(lua)
        lua.eval(SETPAGE.replace('...', '"route"'))
        pump_n(lua, 2)
        lua.eval(SETPAGE.replace('...', '"shop"'))
        drain(lua)
        s = scan(lua, 'lv-shopM')
        if s > 0:
            bad += 1
            print('    ★★ M 购物清单 → 路线半途 → 购物清单后有残留！')

    print('\n结论：%s（%s 个专业）' % ('有残留' if bad else '全部无残留', n))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
