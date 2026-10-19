# -*- coding: utf-8 -*-
"""切页残留探针（2026-10-09）：从「购物清单」子页切到「路线」子页后，
行池里是否还有**仍显示**的帧（= 用户报的「购物清单的材料残留在路线页面」）。

做法：走真渲染链路（PD.Render），切页前后各扫一遍 PD.rows 的 __shown，
外加 secCards / secGoldCards 的 __shown。桩已建模 Show/Hide/SetShown（__shown）。

用法：python _temp/_prof_residual_probe.py
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

# 行池清空（模拟「首次进页 / 刚换过专业」的真机状态）：
#   只有当池子里还没有行时，PD.PaintRows 才会把新页的行**排队**而不是同步建 ——
#   这正是「购物清单材料残留到路线页」得以发生的那个分帧窗口。
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
        if #detail < 12 then detail[#detail + 1] = i .. ":" .. txt(r.a) end
      end
    end
  end
  -- PD.child 下的「非当前行」仍显示帧（滚区内容区里多出来的东西）
  local inPool = {}
  for i = 1, maxi do inPool[PD.rows[i]] = (i <= nspec) end
  local stray, strayDetail = 0, {}
  for _, f in ipairs(ALL_FRAMES or {}) do
    if rawget(f, "__parent") == PD.child and f.__shown
       and not (inPool[f] == true) then
      stray = stray + 1
      if #strayDetail < 12 then
        strayDetail[#strayDetail + 1] = tostring(f.__name) .. ":" .. txt(f.a)
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
         stray, table.concat(strayDetail, " | ")
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
    # 桩补丁（仅本探针内存里改，不动共享工具文件）：
    #   GetStringWidth 未建模 → 兜底分支返回 table → `r.a:GetStringWidth() + 6` 当场报错。
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
    # 追踪所有 CreateFrame 产物（供「PD.child 下还有哪些帧仍显示」的排查）
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
                'local a, b, c, d = orig(...); return a, b, c, 16001, e end end')
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


def scan(lua, tag):
    (nspec, maxi, shown, extra, detail,
     sec, gsec, stray, strayDetail) = lua.eval(SCAN)
    print('  [%-5s] specs=%-4s 池到=%-4s 显示=%-4s 超出行=%-3s stray=%-3s 金卡=%s/%s'
          % (tag, nspec, maxi, shown, extra, stray, sec, gsec))
    if detail:
        print('        超出行: %s' % detail)
    if strayDetail:
        print('        stray : %s' % strayDetail)
    return int(extra), int(stray)


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

        # 场景 A：进购物清单 → 建完 → 切路线
        lua.eval(SETPAGE.replace('...', '"shop"'))
        drain(lua)
        scan(lua, 'shop')
        lua.eval(SETPAGE.replace('...', '"route"'))
        drain(lua)
        s, stray = scan(lua, 'route')
        if s > 0 or stray > 0:
            bad += 1
            print('    ★★ A 切回路线后仍有残留！')

        # 场景 B：进购物清单 → **行还没建完**就切路线（真机才有分帧窗口）
        lua.eval(SETPAGE.replace('...', '"shop"'))
        scan(lua, 'shop-未建完')
        lua.eval(SETPAGE.replace('...', '"route"'))
        drain(lua)
        s, stray = scan(lua, 'route-B')
        if s > 0 or stray > 0:
            bad += 1
            print('    ★★ B 半途切回路线后仍有残留！')

        # 场景 C：进购物清单 → 建了一半就切路线
        lua.eval(SETPAGE.replace('...', '"shop"'))
        lua.eval('(function() for _ = 1, 8 do if #PUMPS > 0 then table.remove(PUMPS, 1)() end end return 1 end)()')
        scan(lua, 'shop-半')
        lua.eval(SETPAGE.replace('...', '"route"'))
        drain(lua)
        s, stray = scan(lua, 'route-C')
        if s > 0 or stray > 0:
            bad += 1
            print('    ★★ C 半途切回路线后仍有残留！')

        # 场景 D（★ 真窗口）：行池为空（首次进入）时进购物清单，
        #   行**全在排队**还没建就切路线 —— 此时若不丢掉上一页的排队行，
        #   它们会被逐批建成购物清单的材料行，落在路线页上。
        lua.eval(RESET)
        lua.eval(SETPAGE.replace('...', '"shop"'))
        scan(lua, 'shop-D')
        lua.eval(SETPAGE.replace('...', '"route"'))
        drain(lua)
        s, stray = scan(lua, 'route-D')
        if s > 0 or stray > 0:
            bad += 1
            print('    ★★ D 空池首进购物清单、半途切路线后有残留！')

        # 场景 E（用户报的）：配方页 → 升级页（跨页签；配方页行数远多于升级页）
        lua.eval(RESET)
        lua.eval(SETTAB.replace('...', '"recipe"'))
        drain(lua)
        scan(lua, 'recipe-E')
        lua.eval(SETTAB.replace('...', '"leveling"'))
        lua.eval(SETPAGE.replace('...', '"route"'))
        drain(lua)
        s, stray = scan(lua, 'lv-E')
        if s > 0 or stray > 0:
            bad += 1
            print('    ★★ E 配方页 → 升级页（路线）后有残留！')

    print('\n结论：%s（%s 个专业）' % ('有残留' if bad else '全部无残留', n))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
