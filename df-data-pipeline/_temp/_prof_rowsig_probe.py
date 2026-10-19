# -*- coding: utf-8 -*-
"""升级页「行内可视残留」探针（2026-10-09）。

用户报：**点配方页 → 点回升级页，页面有材料残留**。
「行池多出来的行帧」那条判据（_prof_residual_probe.py）在跨页签下是干净的
（超出行 = 0），所以残留只可能是**行内可视元素**：同一格行帧被复用，上一页
（配方页）留在里面的材料串 / 材料图标 / 分段字串 / 热区没被清干净。

判据（真·视觉等价）：
    干净升级页(路线) 的**逐行可视签名**  ==  从配方页回来的升级页 的签名。
签名只收**可见**节点（`__shown ~= false`），并带文本；隐藏帧不参与
（否则配方页留下的隐藏 mn/mz 帧会造成假阳性 —— 它们本来就不渲染）。

用法：python _temp/_prof_rowsig_probe.py
退出码：0 = 全部一致；1 = 有差异（= 有残留）。
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

RESET = r'''
(function()
  local PD = TF_NS.ProfModule
  for i = #PD.rows, 1, -1 do if PD.rows[i] then PD.rows[i]:Hide() end end
  PD.rows = {}
  PD.__pendRows = {}
  return 1
end)()
'''

# 清空行池后进「升级 → 路线」（干净基线）
CLEAN = r'''
(function()
  local PD = TF_NS.ProfModule
  PD.autoPage = "route"
  PD.SetTab("leveling")
  return 1
end)()
'''

# 清空行池后先进「某个页签」，再回「升级」（子页由参数给）
VIA = r'''
(function(key)
  local PD = TF_NS.ProfModule
  if not (PD.avail and PD.avail[key]) then return 0 end
  PD.setOpen = false
  PD.SetTab(key)
  return 1
end)(...)
'''

TOLV = r'''
(function(mode)
  local PD = TF_NS.ProfModule
  PD.autoPage = mode
  PD.SetTab("leveling")
  return 1
end)(...)
'''

# PD.child 下「不属于行池且仍显示」的帧（滚区里多出来的东西）
STRAY = r'''
(function()
  local PD = TF_NS.ProfModule
  local maxi, gap = 0, 0
  for i = 1, 20000 do
    if PD.rows[i] then maxi = i; gap = 0 else gap = gap + 1; if gap > 40 then break end end
  end
  local inPool = {}
  for i = 1, maxi do inPool[PD.rows[i]] = true end
  local KNOWN = { { PD.ixRoot, "ixRoot" }, { PD.bonusTable, "bonusTable" },
                  { PD.ixRoot and rawget(PD.ixRoot, "__parent"), "?" } }
  local function tag(f)
    for i = 1, #KNOWN do
      if KNOWN[i][1] and KNOWN[i][1] == f then return KNOWN[i][2] end
    end
    return ""
  end
  local function desc(f)
    local ch = rawget(f, "__children")
    local t = ""
    if ch then
      for i = 1, #ch do
        local v = rawget(ch[i], "__text")
        if v ~= nil and tostring(v) ~= "" then t = t .. "|" .. tostring(v) break end
      end
    end
    local pts = rawget(f, "__pts")
    local anchor = ""
    if pts and pts[1] then anchor = tostring(pts[1]) end
    local tg = tag(f)
    if tg ~= "" then tg = "[" .. tg .. "]" end
    return string.format("%s(%sx%s)@%s%s%s", tostring(rawget(f, "__name")),
                         tostring(rawget(f, "__w")), tostring(rawget(f, "__h")),
                         anchor, tg, t)
  end
  local n, names = 0, {}
  for _, f in ipairs(ALL_FRAMES or {}) do
    if rawget(f, "__parent") == PD.child and f.__shown and not inPool[f] then
      n = n + 1
      names[#names + 1] = desc(f)
    end
  end
  return n, table.concat(names, " ;; ")
end)()
'''

# 逐行可视签名：只收可见节点（隐藏的不渲染，不参与判据）
SIG = r'''
(function()
  local PD = TF_NS.ProfModule
  local maxi, gap = 0, 0
  for i = 1, 20000 do
    if PD.rows[i] then maxi = i; gap = 0 else gap = gap + 1; if gap > 40 then break end end
  end
  local function shown(o)
    if type(o) ~= "table" then return false end
    return rawget(o, "__shown") ~= false
  end
  local function txt(o)
    if type(o) ~= "table" then return "" end
    local v = rawget(o, "__text")
    if v == nil then return "" end
    return tostring(v)
  end
  local out = {}
  for i = 1, maxi do
    local r = PD.rows[i]
    if shown(r) then
      local p = {}
      -- 六个主字串（配方行 / 升级行都会写）
      for _, k in ipairs({ "a", "b", "c", "d", "e", "f" }) do
        local fs = rawget(r, k)
        if shown(fs) then p[#p + 1] = k .. "=" .. txt(fs) end
      end
      -- 右下角「商人：X」半段
      local dv = rawget(r, "dv")
      if shown(dv) then p[#p + 1] = "dv=" .. txt(dv) end
      -- 升级行的材料块（图标 + 数量角标 + 名称 + 热区）
      local blk = rawget(r, "blk")
      if type(blk) == "table" then
        for j = 1, #blk do
          local b = blk[j]
          if type(b) == "table" then
            local seg = "b" .. j
            local any = false
            if shown(b.ic) then seg = seg .. "[ic]" ; any = true end
            if shown(b.ct) then seg = seg .. "[ct]" .. txt(b.ct); any = true end
            if shown(b.nm) then seg = seg .. "[nm]" .. txt(b.nm); any = true end
            if shown(b.zone) then seg = seg .. "[z]" ; any = true end
            if any then p[#p + 1] = seg end
          end
        end
      end
      -- 配方行的材料分段字串 / 热区 / 分隔
      local mn = rawget(r, "mn")
      if type(mn) == "table" then
        for j = 1, #mn do
          if shown(mn[j]) then p[#p + 1] = "mn" .. j .. "=" .. txt(mn[j]) end
        end
      end
      local mz = rawget(r, "mz")
      if type(mz) == "table" then
        for j = 1, #mz do
          if shown(mz[j]) then p[#p + 1] = "mz" .. j end
        end
      end
      local tags = { "tagFs", "tagBg", "sep", "mark", "icon" }
      for _, k in ipairs(tags) do
        local o = rawget(r, k)
        if shown(o) then p[#p + 1] = k .. "=" .. txt(o) end
      end
      out[#out + 1] = i .. "{" .. table.concat(p, " ") .. "}"
    end
  end
  return table.concat(out, " ;; ")
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


def rows_of(sig):
    if not sig:
        return []
    return [x.strip() for x in sig.split(';;')]


def main():
    lua = build_lua()
    lua.execute(BUILD)
    n = lua.eval(PICK)
    print('有升级数据的专业 = %s 个' % n)
    slugs = lua.eval('TF_NS.ProfModule.lvSlugs')

    # 从「哪些页签」回来 × 「升级页的哪个子页」都要试
    FROM = ["recipe", "gather", "camp", "overview", "legacy", "notes"]
    TARGETS = [("route", "路线"), ("shop", "购物清单")]

    bad = 0
    total = 0
    for i in range(1, int(n) + 1):
        slug = slugs[i]
        lua.eval(USE.replace('...', '"%s"' % slug))
        print('=== %s ===' % slug)

        for mode, mlabel in TARGETS:
            lua.eval(RESET)
            lua.eval(CLEAN)
            drain(lua)
            lua.eval(TOLV.replace('...', '"%s"' % mode))
            drain(lua)
            a = rows_of(lua.eval(SIG))
            sa, saNames = lua.eval(STRAY)

            for frm in FROM:
                total += 1
                lua.eval(RESET)
                ok = lua.eval(VIA.replace('...', '"%s"' % frm))
                if not ok:
                    continue
                drain(lua)
                lua.eval(TOLV.replace('...', '"%s"' % mode))
                drain(lua)
                b = rows_of(lua.eval(SIG))
                sb, sbNames = lua.eval(STRAY)

                setA = set(x.strip() for x in str(saNames).split(';;') if x.strip())
                setB = set(x.strip() for x in str(sbNames).split(';;') if x.strip())
                extra = sorted(setB - setA)

                mark = 'OK  '
                if a != b or int(sb) > int(sa):
                    mark = 'FAIL'
                    bad += 1
                print('  [%s] %-16s → 升级/%s：行 %d vs %d，stray %s vs %s'
                      % (mark, frm, mlabel, len(a), len(b), int(sa), int(sb)))
                if mark == 'FAIL':
                    for k in range(max(len(a), len(b))):
                        x = a[k] if k < len(a) else '<缺>'
                        y = b[k] if k < len(b) else '<缺>'
                        if x != y:
                            print('        干净行: %s' % x[:220])
                            print('        回来行: %s' % y[:220])
                            break
                    for e in extra:
                        print('        多出帧: %s' % e[:220])

    print('\n结论：%s（%d 组对照 / %s 个专业）'
          % ('有残留' if bad else '全部干净', total, n))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
