# -*- coding: utf-8 -*-
"""探针：把「详情外壳」那 79 帧 / 365 纹理**按控件拆开**，决定第六刀从哪里切。

背景（2026-10-03 第五刀后）：
  · 掉落行池已经改成「逐帧按预算建」，进度条也做好了；
  · 但**详情外壳本身**（hero / 返回键 / 4 个页签 / 3 个入口 chip / 5 颗筛选 /
    2 颗视图按钮 / 滚动容器）仍旧在「点副本」那一帧**同步**建完 —— 弱机器上
    仍有约 100ms 级的一顿，而且这一段**不在进度条覆盖范围内**。

本探针只做一件事：把外壳按 ns.CreateButton 调用点切段记账，
看「哪几颗按钮贵、非按钮部分多少」，据此决定把哪些段挪进分帧管线。

用法：python _temp/_probe_shell.py
只读，不改任何文件。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import tf_dryrun as T  # noqa: E402
from lupa import lua51  # noqa: E402

ADDON = r'D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\DungeonsForever'
TOC = os.path.join(ADDON, 'DungeonsForever.toc')

toc = open(TOC, encoding='utf-8', errors='replace').read()
files = [l.strip().replace('\\', '/') for l in toc.splitlines()
         if l.strip() and not l.strip().startswith('##')]

lua = lua51.LuaRuntime(unpack_returned_tuples=True)
lua.execute(T.STUB)
lua.execute('os = nil')
lua.execute('time = function() return 1796850000 - 3660 end')
lua.execute("BG.hui.OnThemeChange = function(fn) end")
lua.execute('UnitClass = function() return "盗贼", "ROGUE", 4 end')
lua.execute('BG.hui = nil')
lua.execute('ADDON_ROOT = %r' % ADDON.replace('\\', '/'))
lua.execute('TF_NS = TF_NS or {}')
lua.execute('do local orig = GetBuildInfo; GetBuildInfo = function(...) '
            'local a,b,c,d = orig(...); return a,b,c,16001,e end end')
lua.execute(r'''
UIErrorsFrame = { AddMessage = function() end }
C_SuperTrack = { SetSuperTrackedUserWaypoint = function() end }
C_MAP_MARK = { wp = nil, opened = nil }
C_Map = {
  CanSetUserWaypointOnMap = function() return true end,
  SetUserWaypoint = function(pt) end,
  OpenWorldMap = function(mapID) end,
}
PLAYER_LEVEL = 16
UnitLevel = function() return PLAYER_LEVEL end
DungeonsForeverDB = { dungeon = { subTab = "Raids" }, ui = {} }
''')

loadfile = lua.eval(
    'function(rel)\n'
    '  local chunk = loadfile(ADDON_ROOT .. "/" .. rel)\n'
    '  if not chunk then return nil end\n'
    '  return function() return chunk("DungeonsForever", TF_NS) end\n'
    'end')

bad = 0
for rel in files:
    if rel.lower().endswith('.xml'):
        continue
    chunk = loadfile(rel)
    if chunk is None:
        print('loadfile nil:', rel)
        bad += 1
        continue
    try:
        chunk()
    except Exception as e:
        print('加载失败 %s: %s' % (rel, str(e)[:160]))
        bad += 1
if bad:
    sys.exit(1)

probe = lua.eval(r'''
(function()
  local U  = TF_NS.DungeonUI
  local DG = TF_NS.DungeonModule
  local out = {}

  -- ── 计数器 ──
  local nF, nT, nS, nTex = 0, 0, 0, 0
  local _cf = CreateFrame
  CreateFrame = function(...)
    nF = nF + 1
    local f = _cf(...)
    local _ct  = f.CreateTexture
    local _cfs = f.CreateFontString
    f.CreateTexture = function(self, ...)
      nT = nT + 1
      local t = _ct(self, ...)
      local _st = t.SetTexture
      t.SetTexture = function(s, v)
        if type(v) == "string" or type(v) == "number" then nTex = nTex + 1 end
        return _st(s, v)
      end
      return t
    end
    f.CreateFontString = function(self, ...) nS = nS + 1; return _cfs(self, ...) end
    return f
  end
  _G.GetItemInfo = function() return nil end
  _G.GetItemInfoInstant = function() return nil end

  -- PushStep「只订不排」
  local BUF = {}
  DG.PushStep = function(fn) BUF[#BUF + 1] = fn end
  local Q = {}
  C_Timer = { NewTicker = function() return {} end, After = function(t, fn)
    if type(fn) ~= "function" then return end
    if not t or t <= 0 then Q[#Q + 1] = fn end
  end }

  -- ── 关键：只统计「按钮本体」与「描边」各自吃掉多少 ──
  local acc = { cb = { f = 0, x = 0, n = 0 }, rb = { f = 0, x = 0, n = 0 } }
  local origRB = TF_NS.hui and TF_NS.hui.BuildRoundBorder
  if origRB then
    TF_NS.hui.BuildRoundBorder = function(...)
      local f0, x0 = nF, nT
      local r = origRB(...)
      acc.rb.f = acc.rb.f + (nF - f0)
      acc.rb.x = acc.rb.x + (nT - x0)
      acc.rb.n = acc.rb.n + 1
      return r
    end
  end

  -- ── 关键：在 ns.CreateButton 上装分段探针 ──
  local SEGS, base = {}, nil
  local origCB = TF_NS.CreateButton
  TF_NS.CreateButton = function(parent, ...)
    if base then
      SEGS[#SEGS + 1] = { t = "段" .. (#SEGS + 1), f = nF - base.f, x = nT - base.t,
                          s = nS - base.s, e = nTex - base.e }
    end
    base = { f = nF, t = nT, s = nS, e = nTex }
    local f0, x0 = nF, nT
    local btn = origCB(parent, ...)
    acc.cb.f = acc.cb.f + (nF - f0)
    acc.cb.x = acc.cb.x + (nT - x0)
    acc.cb.n = acc.cb.n + 1
    return btn
  end

  local function reset()
    nF, nT, nS, nTex = 0, 0, 0, 0
    acc.cb = { f = 0, x = 0, n = 0 }
    acc.rb = { f = 0, x = 0, n = 0 }
  end
  local function flush()
    local g = 0
    while #Q > 0 and g < 20000 do g = g + 1; pcall(table.remove(Q, 1)) end
    for _ = 1, #BUF do table.remove(BUF, 1) end
    DG.stepping = false
  end

  U:Build()
  flush()
  U:SwitchSub("Dungeons")
  flush()

  -- ★ 直接量 DG.EnsureDetailBuilt 本体（= 「第一次点副本」那一帧同步跑的那一段）。
  --   U:Build 会把 U.detailBuilt 归零（Core/DungeonUI.lua:4799），所以此刻它是处女态。
  out[#out + 1] = "=== 详情外壳按控件拆段（帧 / 纹理 / 字体串 / 贴图） ==="
  reset()
  SEGS = {}; base = nil
  local ok, err = pcall(function() DG.EnsureDetailBuilt() end)
  if base then
    SEGS[#SEGS + 1] = { t = "段尾（滚动容器 + 备注，非按钮）", f = nF - base.f,
                        x = nT - base.t, s = nS - base.s, e = nTex - base.e }
  end
  out[#out + 1] = string.format("  外壳合计                            帧 %-5d 纹理 %-6d 字体串 %-5d 贴图 %-5d%s",
    nF, nT, nS, nTex, ok and "" or ("  [报错] " .. tostring(err):sub(1, 70)))
  local sumF, sumT = 0, 0
  for _, g in ipairs(SEGS) do
    sumF = sumF + g.f; sumT = sumT + g.x
    out[#out + 1] = string.format("    %-32s 帧 %-5d 纹理 %-6d 字体串 %-5d 贴图 %-5d",
      g.t, g.f, g.x, g.s, g.e)
  end
  out[#out + 1] = string.format("  按钮段合计（前 %d 段）              帧 %-5d 纹理 %-6d",
    #SEGS, sumF, sumT)
  out[#out + 1] = string.format("  非按钮（hero/提示区/滚动容器等）     帧 %-5d 纹理 %-6d",
    nF - sumF, nT - sumT)
  out[#out + 1] = string.format("  ├─ 其中「按钮本体」ns.CreateButton  帧 %-5d 纹理 %-6d（%d 颗，均 %.1f 帧/颗）",
    acc.cb.f, acc.cb.x, acc.cb.n, acc.cb.n > 0 and acc.cb.f / acc.cb.n or 0)
  out[#out + 1] = string.format("  └─ 其中「选中态描边」BuildRoundBorder 帧 %-5d 纹理 %-6d（%d 处，均 %.1f 帧/处）",
    acc.rb.f, acc.rb.x, acc.rb.n, acc.rb.n > 0 and acc.rb.f / acc.rb.n or 0)

  return table.concat(out, "\n")
end)()
''')
print(probe)
