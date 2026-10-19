# -*- coding: utf-8 -*-
"""诊断 v4：升级页「显示中的行」逐行取证（含索引越界的孤儿行）。

为什么还要写一个：已有探针（_diag_zone_legit / _diag_page_subtree）只看
「PD.specs[i] 存在」的行，或用整页帧集合做集合差。若残留行是**索引超过
#PD.specs 的孤儿**（上一页画过、本页没有对应 spec），前者直接跳过、后者
在「两边都残留」时也判 OK。这里直接扫 ALL_FRAMES 里所有行帧（有 r.mn 的），
判「自身 + 全父链都显示」，再把 a..f / dv 文本、blk 块、mn/mz 段、iconZone
全打出来 —— 谁在升级页上显示着材料，一眼可见。

只读，不写产品文件。
用法：python _temp/_diag_visrows.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import df_dungeon_check as D  # noqa: E402
from lupa import lua51  # noqa: E402


def main():
    addon = os.environ.get('DF_ADDON_ROOT') or D.ADDON
    toc = open(os.path.join(addon, os.path.basename(D.TOC)),
               encoding='utf-8', errors='replace').read()
    files = [re.sub(r'\s*\[[^\]]*\]\s*$', '', l.strip()).replace('\\', '/')
             for l in toc.splitlines()
             if l.strip() and not l.strip().startswith('##')]

    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    stub = D.T.STUB.replace(
        '            elseif NUMERIC[k] then f = function() return 100 end',
        '            elseif k == "GetStringWidth" then'
        ' f = function(self) return #(self.__text or "") * 6 end\n'
        '            elseif NUMERIC[k] then f = function() return 100 end', 1)
    assert stub != D.T.STUB
    lua.execute(stub)
    lua.execute('C_Timer = { After = function(t, fn) fn() end }')
    lua.execute('os = nil')
    lua.execute('time = function() return 1796850000 end')
    lua.execute("BG.hui.OnThemeChange = function(fn) end")
    lua.execute('UnitClass = function() return "盗贼", "ROGUE", 4 end')
    lua.execute('UnitLevel = function() return 60 end')
    lua.execute('BG.hui = nil')
    lua.execute('ADDON_ROOT = %r' % addon.replace('\\', '/'))
    lua.execute('TF_NS = TF_NS or {}')
    lua.execute('do local o = GetBuildInfo; GetBuildInfo = function(...) '
                'local a, b, c, d = o(...); return a, b, c, 16001, e end end')
    lua.execute('UIErrorsFrame = { AddMessage = function() end }')
    lua.execute('C_Map = { CanSetUserWaypointOnMap = function() return true end, '
                'SetUserWaypoint = function() end, OpenWorldMap = function() end, '
                'GetAreaInfo = function() return "x" end }')
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
    lf = lua.eval('function(rel) local c = loadfile(ADDON_ROOT .. "/" .. rel) '
                  'if not c then return nil end '
                  'return function() return c("DungeonsForever", TF_NS) end end')
    for rel in files:
        if rel.lower().endswith('.xml'):
            continue
        lf(rel)()
    lua.execute('do UnitLevel = function() return 60 end '
                'if TF_NS.hui then TF_NS.hui.ReskinToggle = function() end end '
                'TF_NS.DungeonUI:Build() TF_NS.DungeonUI:SwitchSub("Professions") end')

    DUMP = r'''(function()
  local PD = TF_NS.ProfModule
  local page = PD.page
  local function up(f, guard)          -- 自身 + 全父链都显示？
    local p, g = f, 0
    while p and g < 40 do
      if rawget(p, "__shown") == false then return false end
      if p == page then return true end
      p = rawget(p, "__parent"); g = g + 1
    end
    return false
  end
  local function T(f) local v = f and rawget(f, "__text") return (v ~= nil) and tostring(v) or "" end
  local out, nOrphan, nMat = {}, 0, 0
  local nSpec = #(PD.specs or {})
  for _, f in ipairs(ALL_FRAMES or {}) do
    if rawget(f, "mn") ~= nil and rawget(f, "__shown") ~= false and up(f, 0) then
      -- 这是「显示中的一行」，找出它在池里的索引 + 对应 spec
      local idx
      for i, rr in pairs(PD.rows or {}) do if rr == f then idx = i break end end
      local sp = idx and PD.specs and PD.specs[idx] or nil
      local orphan = (sp == nil) and true or false
      if orphan then nOrphan = nOrphan + 1 end
      local seg, nseg = {}, 0
      for j = 2, #(rawget(f, "mn") or {}) do
        local fs = rawget(f, "mn")[j]
        if rawget(fs, "__shown") == true then nseg = nseg + 1; seg[#seg + 1] = T(fs) end
      end
      local mz = 0
      for j = 1, #(rawget(f, "mz") or {}) do
        if rawget(rawget(f, "mz")[j], "__shown") == true then mz = mz + 1 end
      end
      local blk, nb = {}, 0
      for j = 1, #(rawget(f, "blk") or {}) do
        local b = rawget(f, "blk")[j]
        if rawget(b.ic, "__shown") == true or rawget(b.ct, "__shown") == true then
          nb = nb + 1; blk[#blk + 1] = T(b.ct)
        end
      end
      local dvShown = rawget(rawget(f, "dv"), "__shown") == true
      local matish = (T(f.f) ~= "") or dvShown or (nseg > 0) or (mz > 0)
      if matish then nMat = nMat + 1 end
      out[#out + 1] = string.format(
        "idx=%s orphan=%s | f=%q | dv=%q(sh=%s) | seg=%d[%s] mz=%d | blk=%d%s | a=%q",
        tostring(idx), tostring(orphan and 1 or 0), T(f.f), T(f.dv),
        tostring(dvShown and 1 or 0), nseg, table.concat(seg, ","), mz,
        nb, (#blk > 0) and ("[" .. table.concat(blk, ",") .. "]") or "", T(f.a))
    end
  end
  local rowsShown = 0
  for i, rr in pairs(PD.rows or {}) do
    if rawget(rr, "__shown") ~= false and up(rr, 0) then rowsShown = rowsShown + 1 end
  end
  return nSpec, rowsShown, nOrphan, nMat, table.concat(out, "\n")
end)()'''

    GO = '(function() local PD=TF_NS.ProfModule PD.setOpen=false PD.SetTab("%s") return 1 end)()'
    LV = '(function() local PD=TF_NS.ProfModule PD.autoPage="%s" PD.SetTab("leveling") return 1 end)()'
    lua.eval('(function() local PD=TF_NS.ProfModule PD.sweeping=true PD.Show("alchemy") return 1 end)()')

    def report(tag):
        nSpec, rowsShown, nOrphan, nMat, body = lua.eval(DUMP)
        print('[%s] #PD.specs=%s  显示中行=%s  孤儿行=%s  **含材料痕迹的行=%s**'
              % (tag, nSpec, rowsShown, nOrphan, nMat))
        for line in (str(body).split('\n') if body else []):
            if line.strip():
                print('    ' + line)
        print('')

    LV_ROUTE = LV % 'route'
    lua.eval(LV_ROUTE)
    lua.eval(LV_ROUTE)
    report('基线 · 直接进升级/路线')

    lua.eval(GO % 'recipe')
    lua.eval(LV_ROUTE)
    lua.eval(LV_ROUTE)
    report('★ 配方 → 升级/路线')

    LV_SHOP = LV % 'shop'
    LV_SHOP2 = LV % 'shop'
    lua.eval(LV_SHOP2)
    lua.eval(LV_SHOP2)
    report('基线 · 直接进升级/购物清单')

    lua.eval(GO % 'recipe')
    lua.eval(LV_SHOP2)
    lua.eval(LV_SHOP2)
    report('★ 配方 → 升级/购物清单')

    lua.eval(GO % 'recipe')
    report('配方页本身')
    return 0


if __name__ == '__main__':
    sys.exit(main())
