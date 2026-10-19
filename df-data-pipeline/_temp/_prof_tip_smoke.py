# -*- coding: utf-8 -*-
"""独立冒烟（2026-10-09）：升级路线页「行级提示框退役 + 制作物/材料物品提示框」运行时验证。

背景：共享 harness 的动态块被并行会话的在途改动提前崩掉 → 专业页运行时段跑不到，
      本冒烟自建驱动链（U:Build → Professions → alchemy → leveling）。
只读产品文件、只在内存桩里跑，不写任何产品文件。

用法：
  python _temp/_prof_tip_smoke.py                    # 默认打 beta 副本（harness 口径）
  DF_ADDON_ROOT=D:/workspace/DungeonsForever python _temp/_prof_tip_smoke.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import df_dungeon_check as D  # 复用 T.STUB / ADDON / TOC
from lupa import lua51

FAILS = []


def ck(name, ok, extra=''):
    tag = 'OK ' if ok else 'FAIL'
    line = '  [%s] %s%s' % (tag, name, ('  [%s]' % extra) if extra != '' else '')
    print(line)
    if not ok:
        FAILS.append(name)


def main():
    addon = os.environ.get('DF_ADDON_ROOT') or D.ADDON
    build = 16001
    toc = open(os.path.join(addon, os.path.basename(D.TOC)),
               encoding='utf-8', errors='replace').read()
    files = [re.sub(r'\s*\[[^\]]*\]\s*$', '', l.strip()).replace('\\', '/')
             for l in toc.splitlines()
             if l.strip() and not l.strip().startswith('##')]

    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(D.T.STUB)
    lua.execute('C_Timer = { After = function(t, fn) fn() end }')
    lua.execute('os = nil')
    lua.execute('time = function() return 1796850000 - 3660 end')
    lua.execute("BG.hui.OnThemeChange = function(fn) end")
    lua.execute('UnitClass = function() return "盗贼", "ROGUE", 4 end')
    lua.execute('UnitLevel = function() return 60 end')
    lua.execute('BG.hui = nil')
    lua.execute('ADDON_ROOT = %r' % addon.replace('\\', '/'))
    lua.execute('TF_NS = TF_NS or {}')
    lua.execute(
        'do local orig = GetBuildInfo; GetBuildInfo = function(...) '
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
            print('加载 %s 失败（loadfile nil）' % rel)
            return 1
        try:
            chunk()
        except Exception as e:
            print('加载 %s 抛异常：%s' % (rel, str(e)[:300]))
            return 1
    print('已加载 %d 个 Lua 文件，开始驱动链'
          % len([f for f in files if not f.lower().endswith('.xml')]))

    DRIVER = r'''
do
  UnitLevel = UnitLevel or function() return 60 end
  if TF_NS.hui then TF_NS.hui.ReskinToggle = function() end end
  TF_NS.DungeonUI:Build()
  TF_NS.DungeonUI:SwitchSub("Professions")
  local PD = TF_NS.ProfModule
  PD.Show("alchemy")
  PD.SetTab("leveling")
end
'''
    lua.execute(DRIVER)

    SCRIPT = r'''
(function()
  local PD = TF_NS.ProfModule
  local DG = TF_NS.ProfHost.DG
  local out = {}
  local function ck(name, ok, extra)
    out[#out + 1] = { name, ok and 1 or 0, extra or "" }
  end

  ck("升级页渲染出了规格行", #(PD.specs or {}) > 0, tostring(#(PD.specs or {})))

  -- ① 行级提示框退役：升级行 spec 打 noTip、且不再带 lines
  local _st, _notip, _hasline = 0, 0, 0
  for _, sp in ipairs(PD.specs or {}) do
    if sp.lvstep then
      _st = _st + 1
      if sp.noTip == true then _notip = _notip + 1 end
      if sp.lines ~= nil then _hasline = _hasline + 1 end
    end
  end
  ck("升级行存在且都打了 noTip", _st > 0 and _notip == _st,
     tostring(_notip) .. "/" .. tostring(_st))
  ck("升级行不再带 lines（段落提示框数据已摘）", _hasline == 0, tostring(_hasline))

  -- ② 行级 OnEnter 不再弹任何提示框
  local _row, _spec
  for i = 1, #(PD.specs or {}) do
    local sp = PD.specs[i]
    if sp.lvstep and sp.it then
      _row = (PD.rows or {})[i]; _spec = sp
      break
    end
  end
  ck("找到一条带产物的升级行（行池与 specs 同序）", _row ~= nil and _spec ~= nil)
  if _row and _spec then
    ck("该行 __noTip 已落值（BindRow 从 spec.noTip 取）", _row.__noTip == true)
    ck("该行 __lines 为空（行级提示框已退役）", _row.__lines == nil)

    do
      local _saved = DG.ShowItemTip
      local _n = 0
      DG.ShowItemTip = function() _n = _n + 1 end
      local _lines0 = #TOOLTIP_LINES
      if _row.__scripts and _row.__scripts.OnEnter then _row.__scripts.OnEnter(_row) end
      ck("★ 悬停整行不再出任何提示框（不调 ShowItemTip、不加任何行）",
         _n == 0 and #TOOLTIP_LINES == _lines0,
         "ShowItemTip=" .. tostring(_n) .. " 新行=" .. tostring(#TOOLTIP_LINES - _lines0))
      DG.ShowItemTip = _saved
    end

    -- ③ 制作物热区
    local iz = _row.__iconZone
    ck("★★ 制作物有独立热区（升级行才建）", iz ~= nil)
    if iz then
      ck("★★ 制作物热区挂的是产物 itemID",
         iz.__it ~= nil and iz.__it[1] == _spec.it[1],
         tostring(iz.__it and iz.__it[1]) .. " / " .. tostring(_spec.it[1]))
      ck("★★ 制作物热区盖住「图标 + 名称列」且在行内可见",
         iz.__shown == true and iz.__w == PD.LV_NAME_X - PD.LV_ICON_X + PD.LV_NAME_W
         and iz.__h == PD.TBL_H,
         tostring(iz.__w) .. "x" .. tostring(iz.__h))
      do
        local _saved = DG.ShowItemTip
        local _got = nil
        DG.ShowItemTip = function(owner, it) _got = it and it[1] end
        if iz.__scripts and iz.__scripts.OnEnter then iz.__scripts.OnEnter(iz) end
        ck("★★ 悬停制作物 → 出该产物自己的物品提示框（走 DG.ShowItemTip）",
           _got == _spec.it[1], tostring(_got))
        DG.ShowItemTip = _saved
      end
      ck("★ 制作物热区显式转发滚轮（压在热区上也能滚）",
         iz.__scripts ~= nil and iz.__scripts.OnMouseWheel ~= nil)
    end

    -- ④ 材料热区
    local nb = _spec.blocks and #_spec.blocks or 0
    ck("该行有材料块（否则后面几条无从判定）", nb > 0, tostring(nb))
    local _ok, _bad = 0, 0
    for k = 1, nb do
      local blk = _spec.blocks[k]
      local b = _row.blk and _row.blk[k]
      local z = b and b.zone
      if z and z.__shown == true and z.__it ~= nil and z.__it[1] == blk.id
         and z.__w == PD.TBL_ICON and z.__h == PD.TBL_ICON then
        _ok = _ok + 1
      else
        _bad = _bad + 1
      end
    end
    ck("★★ 每个材料块都有「图标那一格」热区、挂的是该材料 itemID、与图标同尺寸",
       nb > 0 and _bad == 0, tostring(_ok) .. " 好 / " .. tostring(_bad) .. " 坏")

    do
      local b = _row.blk and _row.blk[1]
      local z = b and b.zone
      if z then
        local _saved = DG.ShowItemTip
        local _got = nil
        DG.ShowItemTip = function(owner, it) _got = it and it[1] end
        if z.__scripts and z.__scripts.OnEnter then z.__scripts.OnEnter(z) end
        ck("★★ 悬停需求材料 → 出该材料自己的物品提示框",
           _got == _spec.blocks[1].id, tostring(_got))
        DG.ShowItemTip = _saved
      else
        ck("★★ 悬停需求材料 → 出该材料自己的物品提示框", false, "无热区")
      end
    end
  end

  -- ⑤ 换页不留透明热区（行池跨页共用）：配方页上不该有任何显示中的热区
  PD.SetTab("recipe")
  do
    local _vis = 0
    for _, r in ipairs(PD.rows or {}) do
      if r.__shown ~= false then
        if r.__iconZone and r.__iconZone.__shown == true then _vis = _vis + 1 end
        for j = 1, #(r.blk or {}) do
          local z = r.blk[j].zone
          if z and z.__shown == true then _vis = _vis + 1 end
        end
      end
    end
    ck("★★ 切到配方页后没有任何遗留的显示中热区（行池复用不许吞鼠标）", _vis == 0, _vis)
  end

  -- ⑥ 帧数纪律：两页都画过之后再往返一次 → 零新建帧
  do
    local _cf = CreateFrame
    local _n = 0
    CreateFrame = function(...) _n = _n + 1; return _cf(...) end
    PD.SetTab("leveling")
    PD.SetTab("overview")
    PD.SetTab("leveling")
    CreateFrame = _cf
    ck("★★ 升级页往返重渲染零新建帧（热区随行池一次建好）", _n == 0, _n)
  end

  return out
end)()
'''
    res = lua.eval(SCRIPT)
    for i in range(1, len(res) + 1):
        item = res[i]
        ck(item[1], item[2] == 1, item[3])

    print('=' * 56)
    print('冒烟完成：失败 %d 条' % len(FAILS))
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
