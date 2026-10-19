# -*- coding: utf-8 -*-
"""升级页「行池空洞 ⇒ 上一页的行藏不掉」探针（2026-10-09）。

为什么必须新写一个：
  `_prof_residual_probe.py` / `_prof_rowsig_probe.py` / `_diag_page_subtree.py`
  都是**满载、无空洞**地跑 —— 桩里 `PD.Row` 从不失败，`PD.rows` 永远是 1..N
  连续的，`#PD.rows` 就等于真实上界，于是「上一页尾部行藏不掉」这条路径
  在任何判据下都**不可能出现**。这就是用户报的残留离线复现不出来的原因。

本探针：**人为在行池里造一个空洞**（让 `PD.Row(k)` 返回 nil，等价于真机里
建帧失败 / pcall 兜住的行），再走「购物清单（行多）→ 路线（行少）」，
断言「路线页上不存在索引超出本页 spec 数的可见行」。

用法：DF_ADDON_ROOT=<addon> python _temp/_prof_rowhole_probe.py
退出码：0 = 无残留；1 = 有残留。
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = r'D:\Game\World of Warcraft\_classic_titan_\Interface\AddOns\BGLite\_temp\tools'
sys.path.insert(0, TOOLS)
sys.path.insert(0, HERE)
# ★ 不 import df_dungeon_check：并行会话正在改它（曾把 `ADDON = ` 那行改没 ⇒ 导入即 NameError）
import tf_dryrun as T  # noqa: E402
from lupa import lua51  # noqa: E402

ADDON = (os.environ.get('DF_ADDON_ROOT')
         or r'D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\DungeonsForever')
TOC = os.path.join(ADDON, 'DungeonsForever.toc')

# 造「行帧丢失」：真机里 `pcall(PD.Row, idx)` 失败 / 建帧返回 nil 时，
# `PD.rows[idx]` 就留 nil。★ 只有当**最后一行也丢**时才致命：
#   Lua 5.1 的 `#` 在 `t[sizearray] ~= nil` 时直接返回 sizearray（中间的洞被忽略），
#   可一旦末尾为 nil 就走二分找边界 —— 找到的是**第一个**洞 ⇒ 回落成一个小得多的数，
#   于是 `for i = n+1, #PD.rows` 完全跑不到尾部那些**仍在显示中**的行。
# 这正是「上一页的行藏不掉」唯一可能的机制，也是老写法唯一会漏的地方。
LOSE = r'''
(function(mid, last)
  local PD = TF_NS.ProfModule
  local orig = PD.Row
  PD.Row = function(i)
    if i == mid or i == last then return nil end
    return orig(i)
  end
  return 1
end)(...)
'''

# 数：「索引 > 本页 spec 数」却仍然可见的行（= 上一页残留）
LEAK = r'''
(function()
  local PD = TF_NS.ProfModule
  local nspec = 0
  for i = 1, 20000 do
    if PD.specs and PD.specs[i] then nspec = i else if i > (nspec + 20) then break end end
  end
  local n, names = 0, {}
  for i, r in pairs(PD.rows or {}) do
    if r and rawget(r, "__shown") ~= false and i > nspec then
      n = n + 1
      if #names < 6 then
        local t = ""
        local fs = rawget(r, "a")
        if fs and fs.__text then t = tostring(fs.__text) end
        names[#names + 1] = string.format("i=%d(%s)", i, t)
      end
    end
  end
  return n, table.concat(names, ", "), nspec
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


def main():
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
    lua.execute('C_Timer = { After = function(t, fn) fn() end }')
    lua.execute('os = nil')
    lua.execute('time = function() return 1796850000 - 3660 end')
    lua.execute("BG.hui.OnThemeChange = function(fn) end")
    lua.execute('UnitClass = function() return "盗贼", "ROGUE", 4 end')
    lua.execute('UnitLevel = function() return 60 end')
    lua.execute('BG.hui = nil')
    lua.execute('ADDON_ROOT = %r' % addon.replace('\\', '/'))
    lua.execute('TF_NS = TF_NS or {}')
    lua.execute('do local o = GetBuildInfo; GetBuildInfo = function(...) '
                'local a, b, c, d = o(...); return a, b, c, 16001, e end end')
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
    lua.eval('(function() local PD = TF_NS.ProfModule PD.sweeping = true '
             'PD.Show("alchemy") return 1 end)()')

    def lv(mode):
        lua.eval('(function() local PD = TF_NS.ProfModule PD.autoPage = "%s" '
                 'PD.SetTab("leveling") return 1 end)()' % mode)

    def reset():
        lua.eval('(function() local PD = TF_NS.ProfModule '
                 'for _, r in pairs(PD.rows or {}) do r:Hide() end '
                 'PD.rows = {} PD.__pendRows = {} PD.sweeping = true return 1 end)()')

    # 先热身：让池子长到「购物清单」需要的规模（这样路线页只需一部分行）
    lv('shop')
    lv('shop')
    lv('route')
    lv('route')

    bad = 0
    cases = [6, 11, 2]
    for mid in cases:
        reset()
        # 先让池子长满（不丢行），量出购物清单的真实最大行号 k
        lv('shop'); lv('shop')
        k = int(lua.eval('(function() local PD = TF_NS.ProfModule '
                         'local m = 0 for i in pairs(PD.rows or {}) do '
                         'if i > m then m = i end end return m end)()'))
        # 这次让「第 mid 行」与「第 k 行」都丢（= 真机里建帧失败）
        lua.eval(LOSE.replace('...', '%d, %d' % (mid, k)))
        reset()
        lv('shop')
        # 半途切回路线（用户口径：「点回升级」）
        lv('route')
        lv('route')
        n, names, nspec = lua.eval(LEAK)
        mark = 'OK  ' if int(n) == 0 else 'FAIL'
        if int(n) != 0:
            bad += 1
        print('[%s] 丢行 mid=%d / 末=%d → 路线页可见超出行 = %s（本页 spec 数 %s）%s'
              % (mark, mid, k, n, nspec, ('  ' + str(names)) if names else ''))

    print('\n结论：%s（%d 个丢行场景）'
          % ('★ 有上一页残留' if bad else '无残留（清场不依赖 #PD.rows）', len(cases)))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
