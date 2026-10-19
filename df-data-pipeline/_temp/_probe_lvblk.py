# -*- coding: utf-8 -*-
"""探针：升级分段行的**材料块**到底画成什么样了（用于定位动态断言红灯）。

对照 mk_df_check.py 里那条「材料块真的画上了且整组右对齐」：
逐行打印 spec.blocks（预期）与行帧 r.blk（实际）的每块：图标显隐 / 物品名 / ×N / 物品名右缘 x。
离线桩 DG.ItemName 回 8 字占位 → 每块 ~139px，预算 297px 只放得下 1 块（桩假象），
所以红灯常见原因是「截断」而不是「没画」—— 本探针把这两种情形分开打。
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

report = lua.eval(r'''function(slug)
  local PD = TF_NS.ProfModule
  PD.Show(slug)
  PD.SetTab("leveling")
  local out = {}
  out[#out+1] = string.format("COL_LW=%d MAT_W=%d NAME_X=%d NAME_W=%d ICON=%d MAT_RPAD=%d",
    PD.COL_LW, PD.LV_MAT_W, PD.LV_NAME_X, PD.LV_NAME_W, PD.TBL_ICON, PD.TBL_MAT_RPAD)
  local bad = 0
  for i, sp in ipairs(PD.specs or {}) do
    if sp.lvstep then
      local r = PD.rows and PD.rows[i]
      local nb = sp.blocks and #sp.blocks or 0
      local line = string.format("[%2d] %-11s nm=%-12s expect=%d row=%s",
        i, tostring(sp.rng), tostring(sp.text), nb, tostring(r ~= nil))
      if r then
        line = line .. string.format(" shown=%s blk=%d icon=%sx%s",
          tostring(r.__shown), r.blk and #r.blk or -1,
          tostring(r.icon and r.icon.__w), tostring(r.icon and r.icon.__h))
      end
      out[#out+1] = line
      for k = 1, nb do
        local e = sp.blocks[k]
        local b = r and r.blk and r.blk[k]
        -- 七轮方案B：块里没有物品名了（b.nm 恒隐藏），校验 = 图标显示 + ×N 角标文本
        local ok = b and b.ic.__shown ~= false and b.nm.__shown == false
                   and b.ct.__text == tostring(e.cnt)
        local right = b and b.ct.__pts and b.ct.__pts[4]
        out[#out+1] = string.format("      k=%d 期望 id=%s ×%-3d | 实际 ct=%-5s right=%s %s icw=%s",
          k, tostring(e.id), e.cnt or 1, b and tostring(b.ct.__text),
          tostring(right),
          ok and "OK" or "**MISMATCH**", b and tostring(b.ic.__w))
        if not ok then bad = bad + 1 end
      end
    end
  end
  out[#out+1] = "=> 块不匹配数 = " .. bad
  return table.concat(out, "\n")
end''')

print(report("engineering"))
