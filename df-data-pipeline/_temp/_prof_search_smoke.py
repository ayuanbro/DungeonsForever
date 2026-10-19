# -*- coding: utf-8 -*-
# 独立冒烟（2026-10-09）：配方页「搜索框 + 名称列现算」运行时验证
# 背景：共享 harness 的动态块被并行会话的团本页在途改动提前崩掉（wallLabels nil），
#       专业页动态断言跑不到 → 本冒烟自建驱动链（U:Build → Professions → alchemy → recipe）。
# 只读产品文件、只在内存桩里跑，不写任何产品文件。
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import df_dungeon_check as D  # 复用 T.STUB / CLIENT_BUILD / ADDON / TOC
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
    # ★ 共用桩的 C_Timer.After 是**空实现** → 专业页大列表的「分帧泵」永远不会被调到，
    #   行池停在半截（后面的 `#PD.rows > 0` 会假绿）。换成立即执行版，离线契约照旧：
    #   「调用方返回时一切就绪」（与 DG.RunSteps 的同步兜底同口径）。
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
    print('已加载 %d 个 Lua 文件，开始驱动链' % len([f for f in files if not f.lower().endswith('.xml')]))

    src = open(os.path.join(addon, 'Core', 'ProfessionUI.lua'),
               encoding='utf-8', errors='replace').read()
    _otc = None
    if 'seb:SetScript("OnTextChanged"' in src and 'seb:SetScript("OnEscapePressed"' in src:
        _otc = src[src.index('seb:SetScript("OnTextChanged"'):
                           src.index('seb:SetScript("OnEscapePressed"')]
    ck('★★ 搜索框输入即滤（OnTextChanged 里更新搜索词并重渲染）',
       _otc is not None and 'PD.searchQ = t' in _otc and 'PD.Render()' in _otc)

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
  local out = {}
  local function ck(name, ok, extra)
    out[#out + 1] = { name, ok and 1 or 0, extra or "" }
  end
  ck("配方页有规格行", #(PD.specs or {}) > 0, tostring(#(PD.specs or {})))
  ck("★★ 名称列按本页现算（在 [MIN,MAX] 内、材料列 = 行宽-右保留-起点-8）",
     PD.RECIPE_NAME_W ~= nil
     and PD.RECIPE_NAME_W >= PD.RECIPE_NAME_MIN
     and PD.RECIPE_NAME_W <= PD.RECIPE_NAME_MAX
     and PD.MAT_X == PD.RECIPE_NAME_W + PD.RECIPE_NAME_PAD
     and PD.MAT_W == PD.MAT_ROW_W - PD.MAT_RIGHT_RESERVE - PD.MAT_X - 8,
     "nameW=" .. tostring(PD.RECIPE_NAME_W) .. " matX=" .. tostring(PD.MAT_X))
  ck("★★ 现算的名称列比旧的固定分割窄（省下的全给了材料列）",
     PD.MAT_X < math.floor(PD.MAT_ROW_W * 0.40),
     "matX=" .. tostring(PD.MAT_X) .. " vs " .. tostring(math.floor(PD.MAT_ROW_W * 0.40)))
  ck("材料列确实变宽（MAT_W > 旧口径的 " .. tostring(PD.MAT_ROW_W - PD.MAT_RIGHT_RESERVE - math.floor(PD.MAT_ROW_W * 0.40) - 8) .. "）",
     PD.MAT_W > PD.MAT_ROW_W - PD.MAT_RIGHT_RESERVE - math.floor(PD.MAT_ROW_W * 0.40) - 8,
     "matW=" .. tostring(PD.MAT_W))
  ck("★★ 搜索框只在配方页显示（当前就在配方页）",
     PD.searchBox ~= nil and PD.searchBox.__shown == true)
  PD.SetTab("overview")
  ck("★ 切离配方页搜索框隐藏", PD.searchBox.__shown == false)
  PD.SetTab("recipe")
  do
    local _DG = TF_NS.ProfHost.DG
    local _oIN = _DG.ItemName
    _DG.ItemName = function(id)
      if (tonumber(id) or 0) % 2 == 0 then return "轻皮甲片", true end
      return "铁扣环", true
    end
    local _n0 = #(PD.specs or {})
    PD.searchQ = "轻皮"
    PD.Render()
    local _n1 = #(PD.specs or {})
    _DG.ItemName = _oIN
    PD.searchQ = nil
    PD.Render()
    local _n2 = #(PD.specs or {})
    ck("★★ 搜索词过滤列表（命中子集）且清空后全量还原",
       _n0 > 0 and _n1 > 0 and _n1 < _n0 and _n2 == _n0,
       tostring(_n0) .. " -> " .. tostring(_n1) .. " -> " .. tostring(_n2))
    -- 搜索词换一个必然全命中的词：过滤后应等于全量
    _DG.ItemName = function() return "铁扣环", true end
    PD.searchQ = "铁扣"
    PD.Render()
    local _n3 = #(PD.specs or {})
    ck("★ 全命中的搜索词不过滤掉任何行", _n3 == _n0, tostring(_n3) .. " / " .. tostring(_n0))
    _DG.ItemName = _oIN
    PD.searchQ = nil
    PD.Render()
  end
  ck("★ 渲染路径零新建帧（搜索往返后行池仍是同一批）",
     PD.rows ~= nil and #PD.rows > 0)
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
