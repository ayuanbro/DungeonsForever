# -*- coding: utf-8 -*-
"""诊断 v2：升级页 → 配方页 → 升级页，逐行全量可视签名差分。
判据包含：a..f 字串 / dv / 材料块(ic,ct,nm,zone) / 材料分段(mn,mz) / 制作物热区 /
          tagFs / sep / mark / icon / 行可见性。
只读，不写产品文件。
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
    build = 16001
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
    assert stub != D.T.STUB, 'GetStringWidth 桩补丁没生效'
    lua.execute(stub)
    lua.execute('C_Timer = { After = function(t, fn) fn() end }')
    lua.execute('os = nil')
    lua.execute('time = function() return 1796850000 - 3660 end')
    lua.execute("BG.hui.OnThemeChange = function(fn) end")
    lua.execute('UnitClass = function() return "盗贼", "ROGUE", 4 end')
    lua.execute('UnitLevel = function() return 60 end')
    lua.execute('BG.hui = nil')
    lua.execute('ADDON_ROOT = %r' % addon.replace('\\', '/'))
    lua.execute('TF_NS = TF_NS or {}')
    lua.execute('do local orig = GetBuildInfo; GetBuildInfo = function(...) '
                'local a,b,c,d = orig(...); return a, b, c, %d, e end end' % build)
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
            raise RuntimeError('加载 %s 失败' % rel)
        chunk()

    lua.execute(r'''
do
  UnitLevel = UnitLevel or function() return 60 end
  if TF_NS.hui then TF_NS.hui.ReskinToggle = function() end end
  TF_NS.DungeonUI:Build()
  TF_NS.DungeonUI:SwitchSub("Professions")
end
''')

    SIG = r'''
(function()
  local PD = TF_NS.ProfModule
  local function sh(o) return type(o) == "table" and rawget(o, "__shown") ~= false end
  local function shown(o) return type(o) == "table" and rawget(o, "__shown") == true end
  local function txt(o)
    if type(o) ~= "table" then return "" end
    local v = rawget(o, "__text"); if v == nil then return "" end
    return tostring(v)
  end
  local out = {}
  local maxi = #(PD.rows or {})
  for i = 1, maxi do
    local r = PD.rows[i]
    if r and sh(r) then
      local p = { "vis" }
      for _, k in ipairs({ "a", "b", "c", "d", "e", "f" }) do
        local fs = rawget(r, k); if sh(fs) then p[#p + 1] = k .. "=" .. txt(fs) end
      end
      local dv = rawget(r, "dv"); if sh(dv) then p[#p + 1] = "dv=" .. txt(dv) end
      local blk = rawget(r, "blk")
      if type(blk) == "table" then
        for j = 1, #blk do
          local b = blk[j]
          if type(b) == "table" then
            local s2 = "b" .. j
            if sh(b.ic) then s2 = s2 .. "ic" end
            if sh(b.ct) then s2 = s2 .. "ct" .. txt(b.ct) end
            if sh(b.nm) then s2 = s2 .. "nm" .. txt(b.nm) end
            if shown(b.zone) then s2 = s2 .. "ZONE" end
            if s2 ~= ("b" .. j) then p[#p + 1] = s2 end
          end
        end
      end
      local mn = rawget(r, "mn")
      if type(mn) == "table" then
        for j = 1, #mn do if sh(mn[j]) then p[#p + 1] = "mn" .. j .. "=" .. txt(mn[j]) end end
      end
      local mz = rawget(r, "mz")
      if type(mz) == "table" then
        for j = 1, #mz do if shown(mz[j]) then p[#p + 1] = "mz" .. j .. "HOT" end end
      end
      if shown(rawget(r, "__iconZone")) then p[#p + 1] = "IZHOT" end
      for _, k in ipairs({ "tagFs", "sep", "mark", "icon" }) do
        local o = rawget(r, k); if sh(o) then p[#p + 1] = k end
      end
      out[#out + 1] = i .. "{" .. table.concat(p, " ") .. "}"
    else
      out[#out + 1] = i .. "{HIDDEN}"
    end
  end
  return #(PD.rows or {}), table.concat(out, " ;; ")
end)()
'''

    lua.eval('(function() local PD=TF_NS.ProfModule PD.sweeping=true PD.Show("alchemy") return 1 end)()')

    def sig():
        return lua.eval(SIG)

    def tab(script):
        lua.eval(script)

    bad = 0
    for mode, mlabel in (("route", "路线"), ("shop", "购物清单")):
        LV = '(function() local PD=TF_NS.ProfModule PD.autoPage="%s" PD.SetTab("leveling") return 1 end)()' % mode

        # 基线：连渲两次升级页（第二次 = 热路径稳态）
        tab(LV); tab(LV)
        n1, s1 = sig()

        # 往返：配方页 → 升级页
        tab('(function() local PD=TF_NS.ProfModule PD.SetTab("recipe") return 1 end)()')
        tab(LV)
        n2, s2 = sig()

        a = [x.strip() for x in str(s1).split(';;')]
        b = [x.strip() for x in str(s2).split(';;')]
        same = (a == b)
        print('[%s] 池 %s vs %s  行数 %d vs %d  %s'
              % (mlabel, n1, n2, len(a), len(b), '一致' if same else '★不一致'))
        if not same:
            bad += 1
            for k in range(max(len(a), len(b))):
                x = a[k] if k < len(a) else '<缺>'
                y = b[k] if k < len(b) else '<缺>'
                if x != y:
                    print('  基线: %s' % x[:300])
                    print('  往返: %s' % y[:300])
    print('\n结论：%s' % ('有行内残留' if bad else '无行内残留'))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
