# -*- coding: utf-8 -*-
"""独立冒烟（2026-10-09 需求二）：配方页「材料分段物品提示框 + 商人点击落图」运行时验证。

用户口径：
  「配方页面现在也这样修改  如果鼠标在材料上面，就显示材料的鼠标提示框
    如果鼠标在商人上面，就显示点击定位在地图上标记商人位置」

背景与需求一同源：共享 harness 的动态块被并行会话的在途改动提前崩掉
（`wallLabels` 未初始化），专业页运行时段跑不到 → 本冒烟自建驱动链
（Build → Professions → alchemy → recipe）。
只读产品文件、只在内存桩里跑，不写任何产品文件。

用法：
  python _temp/_recipe_tip_smoke.py                    # 默认打 beta 副本（harness 口径）
  DF_ADDON_ROOT=D:/workspace/DungeonsForever python _temp/_recipe_tip_smoke.py
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
  PD.SetTab("recipe")
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

  -- 分别找一条「带材料分段链」和一条「带商人段」的配方行
  local idxM, specM, idxV, specV
  for i = 1, #(PD.specs or {}) do
    local sp = PD.specs[i]
    if sp.kind == "row" then
      if not specM and sp.matSegs and #sp.matSegs > 0 then idxM, specM = i, sp end
      if not specV and sp.dval then idxV, specV = i, sp end
    end
  end
  ck("★★ 配方页渲染出带「材料分段链」的配方行", specM ~= nil,
     specM and (tostring(#specM.matSegs) .. " 段") or "未找到")
  ck("★★ 配方页渲染出带「商人半段」的配方行", specV ~= nil,
     specV and tostring(specV.dval) or "未找到")

  -- ① 材料分段链逐段落位
  if specM then
    local r = (PD.rows or {})[idxM]
    ck("行池与 specs 同序（拿到同一行）", r ~= nil)
    if r then
      local segOk, segN = true, #specM.matSegs
      for i = 1, segN do
        local fs = (i == 1) and r.f or (r.mn and r.mn[i])
        if not fs or fs.__text ~= (specM.matSegs[i].text or "") then segOk = false end
      end
      ck("★★ 材料列分段链逐段落到 r.f / r.mn[i]（文本逐段对上）", segOk,
         tostring(segN) .. " 段")

      local idOk, idBad, nnOk, nnBad = 0, 0, 0, 0
      for i = 1, segN do
        local z = r.mz and r.mz[i]
        local seg = specM.matSegs[i]
        if seg.id then
          if z and z.__shown == true and z.__it and z.__it[1] == seg.id then
            idOk = idOk + 1
          else idBad = idBad + 1 end
        else
          if (not z) or z.__shown == false then nnOk = nnOk + 1
          else nnBad = nnBad + 1 end
        end
      end
      ck("★★ 有 id 的段：热区显示且挂该材料 itemID", idBad == 0 and idOk > 0,
         tostring(idOk) .. " 好 / " .. tostring(idBad) .. " 坏")
      ck("★★ 省略号段（无 id）：热区隐藏（不吞鼠标）", nnBad == 0,
         tostring(nnOk) .. " 好 / " .. tostring(nnBad) .. " 坏")

      -- ② 悬停材料段 → 该材料物品提示框
      local ti
      for i = 1, segN do if specM.matSegs[i].id then ti = i break end end
      if ti then
        local z = r.mz[ti]
        local _saved = DG.ShowItemTip
        local _got
        DG.ShowItemTip = function(owner, it) _got = it and it[1] end
        if z.__scripts and z.__scripts.OnEnter then z.__scripts.OnEnter(z) end
        ck("★★ 悬停材料段 → 出该材料自己的物品提示框（暴雪原皮口径，走 DG.ShowItemTip）",
           _got == specM.matSegs[ti].id,
           tostring(_got) .. " / " .. tostring(specM.matSegs[ti].id))
        DG.ShowItemTip = _saved
        ck("★ 材料段热区显式转发滚轮（压在热区上也能滚）",
           z.__scripts ~= nil and z.__scripts.OnMouseWheel ~= nil)
      else
        ck("★★ 悬停材料段 → 出该材料自己的物品提示框（暴雪原皮口径，走 DG.ShowItemTip）",
           false, "无带 id 段")
        ck("★ 材料段热区显式转发滚轮（压在热区上也能滚）", false, "无带 id 段")
      end
    end
  end

  -- ③ 商人半段 + 悬停文字提示 + 点击落图
  if specV then
    local r = (PD.rows or {})[idxV]
    ck("★★ 商人半段拆到 r.dv 且文本 = spec.dval",
       r and r.dv and r.dv.__shown == true and r.dv.__text == specV.dval,
       tostring(r and r.dv and r.dv.__text))
    ck("★ 商人半段的前缀留在 r.d（两半用锚点链相接）",
       r and r.d and r.d.__text == (specV.dpre or ""),
       tostring(r and r.d and r.d.__text))
    local vz = r and r.__iconZone
    ck("★★ 商人热区挂文字通道 __tipLines（含商人明细）",
       vz ~= nil and vz.__tipLines ~= nil and #vz.__tipLines > 0,
       tostring(vz and vz.__tipLines and #vz.__tipLines))
    ck("★★ 商人热区有自定义点击 __act", vz ~= nil and type(vz.__act) == "function")
    if vz then
      TOOLTIP_LINES = {}
      if vz.__scripts and vz.__scripts.OnEnter then vz.__scripts.OnEnter(vz) end
      local joined = table.concat(TOOLTIP_LINES, " | ")
      ck("★★ 悬停商人热区 → 出文字提示框（含「点击：在地图上标记该 NPC」）",
         #TOOLTIP_LINES > 0 and joined:find("地图", 1, true) ~= nil, joined)
      local _marked = 0
      local _om = PD.MarkVendorLoc
      PD.MarkVendorLoc = function(loc) _marked = _marked + 1 end
      if vz.__scripts and vz.__scripts.OnClick then
        vz.__scripts.OnClick(vz, "LeftButton")
      end
      PD.MarkVendorLoc = _om
      ck("★★ 点击商人热区 → 触发 PD.MarkVendorLoc（落图链路）", _marked == 1,
         tostring(_marked))
    end
  end

  -- ④ 切回升级页：不许留任何显示中的材料段/商人热区（行池跨页共用）
  PD.SetTab("leveling")
  do
    local _vis, _iz, _mz = 0, 0, 0
    for _, r in ipairs(PD.rows or {}) do
      -- 只统计**显示中的行**：行池尾部的多余行被 Hide 后其子帧不会收鼠标
      --（与需求一冒烟同口径）。升级行的 __iconZone 本就该显示（需求一），
      --所以这里只钉**材料段热区 r.mz** 不许有残留。
      if r.__shown ~= false then
        for _, z in pairs(r.mz or {}) do
          if z.__shown == true then _mz = _mz + 1 end
        end
        if r.__iconZone and r.__iconZone.__shown == true then _iz = _iz + 1 end
      end
    end
    _vis = _mz
    ck("★★ 切回升级页后无遗留的材料段热区（行池复用不许吞鼠标）", _vis == 0,
       "材料段=" .. tostring(_mz) .. " 制作物热区=" .. tostring(_iz))
  end

  -- ⑤ 往返重渲染零新建帧
  PD.SetTab("recipe")
  do
    local _cf = CreateFrame
    local _n = 0
    CreateFrame = function(...) _n = _n + 1; return _cf(...) end
    PD.SetTab("leveling")
    PD.SetTab("overview")
    PD.SetTab("recipe")
    CreateFrame = _cf
    ck("★★ 配方页往返重渲染零新建帧（热区随行池一次建好）", _n == 0, _n)
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
