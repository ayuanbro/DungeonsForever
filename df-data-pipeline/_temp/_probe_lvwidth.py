# -*- coding: utf-8 -*-
"""探针：改完升级页列宽后，四列几何与「材料串有没有被截断」到底是多少。

用户 2026-09-24 四轮：材料显示不全（末尾「…」）+ 名称与材料之间白太多。
改法是四列全按本页内容现算。本探针把改后的真实数值打出来（用于给断言定阈值）：
  COL_LW / COL_RW、LV_NAME_X / LV_NAME_W / LV_CNT_W / LV_MAT_X / LV_MAT_W，
  以及每个分段行的「名称宽 / 材料串 / 材料串实测宽 / 是否含 …」。
离线物品名是桩里的占位「暂时没有客户端数据」（8 个 CJK = 104px）→ 量出来是**保守上界**。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = r'D:\Game\World of Warcraft\_classic_titan_\Interface\AddOns\BGLite\_temp\tools'
sys.path.insert(0, TOOLS)
sys.path.insert(0, HERE)

import tf_dryrun as T  # noqa: E402
from lupa import lua51  # noqa: E402

ADDON = r'D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\DungeonsForever'
BUILD = int(os.environ.get('TF_BUILD', '16001'))

files = []
for raw in open(os.path.join(ADDON, 'DungeonsForever.toc'), encoding='utf-8-sig'):
    line = raw.strip()
    if not line or line.startswith('##') or line.startswith('#'):
        continue
    files.append(line.replace('\\', '/'))

lua = lua51.LuaRuntime(unpack_returned_tuples=True)
lua.execute(T.STUB)
lua.execute('UnitClass = function() return "盗贼", "ROGUE", 4 end')
lua.execute('BG.hui = nil')
lua.execute('ADDON_ROOT = %r' % ADDON.replace('\\', '/'))
lua.execute('TF_NS = TF_NS or {}')
lua.execute('UIErrorsFrame = { AddMessage = function() end }')
lua.execute('''
do
  local orig = GetBuildInfo
  GetBuildInfo = function(...)
    local a, b, c, d, e = orig(...)
    return a, b, c, %d, e
  end
end
''' % BUILD)

for rel in files:
    if rel.lower().endswith('.xml'):
        continue
    chunk = lua.eval('function(rel)\n'
                     '  local c = loadfile(ADDON_ROOT .. "/" .. rel)\n'
                     '  if not c then return nil end\n'
                     '  return function() return c("DungeonsForever", TF_NS) end\n'
                     'end')(rel)
    if chunk is None:
        print('loadfile nil:', rel)
        continue
    chunk()

PD = lua.eval('TF_NS.ProfModule')
print('IsForever =', lua.eval('TF_NS.IsForever'))
print('build =', BUILD)
# 走正式入口把骨架建起来（U:Build → SwitchSub("Professions") → PD.Build）——
# 直接调 PD.Build 会漏掉 FONT_BASE 的延迟赋值（它是 U:Build 里赋的），SetFont 就报「字体为 nil」。
lua.execute('''
PD_BUILT = false
do
  local U = TF_NS.DungeonUI
  if U == nil then PD_BUILT = "ns.DungeonUI 不存在" return end
  local ok, e = pcall(function() U:Build(); U:SwitchSub("Professions") end)
  PD_BUILT = ok and true or tostring(e)
end
''')
print('U:Build + SwitchSub =', lua.eval('PD_BUILT'))
print(lua.eval(r'''function()
  local LV, PD = TF_NS.ProfLeveling, TF_NS.ProfModule
  local o = {}
  o[#o+1] = "ProfData=" .. tostring(TF_NS.ProfData ~= nil)
    .. "  ProfLeveling=" .. tostring(LV ~= nil)
    .. "  ProfRecipes=" .. tostring(TF_NS.ProfRecipes ~= nil)
  if LV then
    local n = 0
    for _ in pairs(LV) do n = n + 1 end
    o[#o+1] = "LV keys=" .. n
    local lv = LV["alchemy"]
    o[#o+1] = "LV.alchemy=" .. tostring(lv ~= nil)
    if lv then o[#o+1] = "steps=" .. tostring(lv["steps"] ~= nil and #lv["steps"] or "nil") end
  end
  o[#o+1] = "PD=" .. tostring(PD ~= nil)
  PD.Show("alchemy")
  o[#o+1] = "cur=" .. tostring(PD.cur) .. "  tab=" .. tostring(PD.tab)
  PD.SetTab("leveling")
  o[#o+1] = "SetTab 后 cur=" .. tostring(PD.cur) .. " tab=" .. tostring(PD.tab)
    .. " specs=" .. tostring(PD.specs and #PD.specs or "nil")
  return table.concat(o, "\n")
end''')())

dump = lua.eval(r'''function(slug)
  local PD = TF_NS.ProfModule
  PD.Show(slug)
  PD.SetTab("leveling")
  local out = {}
  out[#out+1] = string.format(
    "COL_LW=%d COL_RW=%d | ICON=%d ICON_X=%d NAME_X=%d NAME_W=%d CNT_W=%d CNT_R=%d MAT_W=%d",
    PD.COL_LW, PD.COL_RW, PD.TBL_ICON, PD.LV_ICON_X, PD.LV_NAME_X, PD.LV_NAME_W,
    PD.LV_CNT_W, PD.LV_CNT_R, PD.LV_MAT_W)
  local cut, tot = 0, 0
  for _, sp in ipairs(PD.specs or {}) do
    if sp.lvstep then
      tot = tot + 1
      local nb = sp.blocks and #sp.blocks or 0
      local w = 0
      for i = 1, nb do w = w + sp.blocks[i].w + (i > 1 and PD.TBL_BLK_GAP or 0) end
      if sp.matCut then cut = cut + 1 end
      out[#out+1] = string.format("  %-11s %-14s nmw=%5.1f src=%-14s blocks=%d w=%5.1f%s",
        sp.rng, sp.text, PD.TextW(sp.text, PD.LV_FS), tostring(sp.src), nb, w,
        sp.matCut and "  <CUT>" or "")
    end
  end
  out[#out+1] = string.format("  => 分段 %d 条，材料被截断 %d 条", tot, cut)
  return table.concat(out, "\n")
end''')

cap = lua.eval(r'''function()
  local PD = TF_NS.ProfModule
  local DG = TF_NS.ProfHost.DG
  local save = DG.ItemName
  local o = {}
  for _, L in ipairs({ 2, 3, 4, 5 }) do
    DG.ItemName = function() return string.rep("测", L) end
    local blocks, tot = PD.PackMats({{1, 1}, {2, 1}, {3, 1}, {4, 1}, {5, 1}, {6, 1}}, PD.LV_MAT_W)
    o[#o+1] = string.format("  %d 字名 → 放下 %d 块（总宽 %.0f / 预算 %d）",
                            L, #blocks, tot, PD.LV_MAT_W)
  end
  DG.ItemName = save
  return table.concat(o, "\n")
end''')

for slug in ('alchemy', 'blacksmithing', 'tailoring'):
    print('-' * 70)
    print(dump(slug))
print('-' * 70)
print(cap())
