# -*- coding: utf-8 -*-
"""探针：Hui.lua 的提示框换肤在离线 harness 里到底建没建起来。

为什么单独立一个：装备提示框「不套插件皮」的判定全在 GameTooltip 的 OnShow 里，
而 harness 原先从不触发 OnShow → 这段逻辑离线零覆盖。补桩后若 Case 仍不通过，
必须能分清「桩没接上」还是「插件逻辑真的退步」，所以这里逐项打点。
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
TOC = os.path.join(ADDON, 'DungeonsForever.toc')

files = []
for raw in open(TOC, encoding='utf-8-sig'):
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

TIP_PATCH = r'''
do
  local function tipPatch(tt)
    local oldShow, oldHide, oldClear = tt.Show, tt.Hide, tt.ClearLines
    tt.Show = function(self)
      local was = rawget(self, "__shown")
      oldShow(self)
      if was ~= true then
        local s = rawget(self, "__scripts")
        local fn = s and s.OnShow
        if fn then fn() end
      end
      return self
    end
    tt.Hide = function(self) oldHide(self) return self end
    tt.SetOwner = function(self, owner) rawset(self, "__owner", owner) return self end
    tt.GetOwner = function(self) return rawget(self, "__owner") end
    tt.GetItem = function(self) return rawget(self, "__itemName"), rawget(self, "__itemLink") end
    tt.ClearLines = function(self)
      rawset(self, "__itemName", nil)
      rawset(self, "__itemLink", nil)
      return oldClear(self)
    end
    local ns9 = rawget(tt, "NineSlice")
    if ns9 then
      ns9.GetAlpha = function(self) return rawget(self, "__alpha") or 1 end
      ns9.SetAlpha = function(self, a) rawset(self, "__alpha", a) return self end
    end
  end
  tipPatch(GameTooltip)
  tipPatch(ItemRefTooltip)
end
'''
lua.execute(TIP_PATCH)

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

diag = lua.eval(r'''function() return table.concat({
  "hui 表存在          : " .. tostring(TF_NS.hui ~= nil),
  "huiTheme            : " .. tostring(TF_NS.huiTheme),
  "GameTooltip 已建皮   : " .. tostring(rawget(GameTooltip, "__huiSkinned")),
  "GameTooltip 子件数   : " .. tostring((function()
      local c = rawget(GameTooltip, "__children")
      return c and #c or 0 end)()),
  "NineSlice alpha     : " .. tostring(rawget(rawget(GameTooltip, "NineSlice"), "__alpha")),
  "OnShow 钩子已挂      : " .. tostring((function()
      local s = rawget(GameTooltip, "__scripts")
      return s ~= nil and s.OnShow ~= nil end)()),
  "SkinGameTooltip 可调 : " .. tostring(type(TF_NS.hui.SkinGameTooltip)),
}, "\n") end''')
print(diag())

# 对（未建皮的）ItemRefTooltip 走一遍 SkinGameTooltip，把可能的报错原样打出来
err = lua.eval(r'''function()
  local nt = CreateFrame("GameTooltip", "ProbeTip", UIParent, "GameTooltipTemplate")
  nt.NineSlice = GameTooltip.NineSlice
  local ok, e = pcall(TF_NS.hui.SkinGameTooltip, nt)
  local c = rawget(nt, "__children")
  return "SkinGameTooltip(新帧)=" .. tostring(ok) .. "  err=" .. tostring(e)
    .. "  子件=" .. tostring(c and #c or 0)
    .. "  alpha=" .. tostring(rawget(rawget(nt, "NineSlice"), "__alpha"))
end''')
print(err())
