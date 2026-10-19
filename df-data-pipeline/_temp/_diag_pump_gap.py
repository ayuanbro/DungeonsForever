# -*- coding: utf-8 -*-
"""诊断 v5：分帧「窗口期」取证 —— 切页那一瞬间，可见行是否还挂着上一页内容。

机理（README）
-------------
`DG.RunSteps` 把**首块**也排到下一帧（`C_Timer.After(0, pump)`；2026-10-03「点副本
就卡死」第四刀）——这是对的。但它带来一个窗口期：

    PD.Render() 切页
      → PD.PaintRows：`i <= syncN` 的行**当帧重绑**；`i > syncN` 的行只入
        `PD.__pendRows`，**既不重绑也不隐藏**
      → `PD.FlushPendingRows` → `DG.PushStep(PD.BuildPendRows)` → 排到**下一帧**
    ⇒ 这一帧里，落在 `syncN < i <= n` 的行**仍然显示上一页的内容**，人眼看得见。

配方页（300 行、材料列在 `PD.MAT_X`）→ 升级页（单栏整宽，行几何一样）正好命中：
窗口期里那几行显示的就是**配方页的材料列文本** —— 就是用户报的「材料残留」。

这个探针把 `C_Timer.After` 改成**只入队不执行**，于是可以精确地停在窗口期里取证：
    A. 配方页（跑满）→ 记基线
    B. 切升级页 → **零帧**就取证  ← 这就是窗口期
    C. 再跑满 → 取证            ← 窗口期之后

只读，不写产品文件。
用法：DF_ADDON_ROOT=<addon> python _temp/_diag_pump_gap.py
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
    # ★ 关键：只入队、不执行 —— 这样才能停在「首块还没跑」的那一帧
    lua.execute('''
TIMER_Q = {}
C_Timer = { After = function(t, fn) TIMER_Q[#TIMER_Q + 1] = fn end }
function PUMP_ROUNDS(maxr)
  local rounds = 0
  while #TIMER_Q > 0 and rounds < (maxr or 200) do
    rounds = rounds + 1
    local batch = TIMER_Q
    TIMER_Q = {}
    for i = 1, #batch do batch[i]() end
  end
  return rounds, #TIMER_Q
end
''')
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

    SURVEY = r'''(function()
  local PD = TF_NS.ProfModule
  local page = PD.page
  local function up(f)
    local p, g = f, 0
    while p and g < 40 do
      if rawget(p, "__shown") == false then return false end
      if p == page then return true end
      p = rawget(p, "__parent"); g = g + 1
    end
    return false
  end
  local nSpec = #(PD.specs or {})
  local vis, mat, samples = 0, 0, {}
  for _, f in ipairs(ALL_FRAMES or {}) do
    if rawget(f, "mn") ~= nil and rawget(f, "__shown") ~= false and up(f) then
      vis = vis + 1
      local ft = rawget(rawget(f, "f"), "__text")
      local nblk = 0
      for j = 1, #(rawget(f, "blk") or {}) do
        if rawget(rawget(f, "blk")[j].ic, "__shown") == true then nblk = nblk + 1 end
      end
      if (ft and ft ~= "") or nblk > 0 then
        mat = mat + 1
        samples[#samples + 1] = string.format("f=%q blk=%d", tostring(ft or ""), nblk)
      end
    end
  end
  return nSpec, vis, mat, table.concat(samples, " ;; ")
end)()'''

    lua.execute('(function() local PD=TF_NS.ProfModule PD.sweeping=true '
                'PD.Show("alchemy") return 1 end)()')
    lua.execute('PUMP_ROUNDS(200)')

    def survey(tag):
        nspec, vis, mat, body = lua.eval(SURVEY)
        print('[%s] spec=%s  可见行=%s  **其中带材料痕迹=%s**' % (tag, nspec, vis, mat))
        if body:
            for s in str(body).split(' ;; ')[:6]:
                print('      ' + s)
        return mat, vis

    def go(tab, mode):
        if tab == 'leveling':
            lua.eval('(function() local PD=TF_NS.ProfModule PD.setOpen=false '
                     'PD.autoPage=%r PD.SetTab("leveling") return 1 end)()' % mode)
        else:
            lua.eval('(function() local PD=TF_NS.ProfModule PD.setOpen=false '
                     'PD.SetTab(%r) return 1 end)()' % tab)

    for mode in ('route', 'shop'):
        # 先跑满配方页（把 300 行都建出来，行几何与升级页一致）
        go('recipe', None)
        lua.eval('PUMP_ROUNDS(200)')
        go('recipe', None)
        lua.eval('PUMP_ROUNDS(200)')
        survey('基线 · 配方页（跑满）')
        # ★ 切升级页：零帧取证 = 窗口期
        go('leveling', mode)
        m0, v0 = survey('★ 窗口期 · 配方 → 升级/%s（0 帧）' % mode)
        lua.eval('PUMP_ROUNDS(200)')
        m1, v1 = survey('窗口期后 · 升级/%s（跑满）' % mode)
        print('    ⇒ %s' % ('窗口期里 %d/%d 个可见行还挂着材料（残留窗口真实存在）'
                            % (m0, v0) if m0 else
                            '窗口期里也没有材料痕迹（本路径不受影响）'))
        print('')
    return 0


if __name__ == '__main__':
    sys.exit(main())
