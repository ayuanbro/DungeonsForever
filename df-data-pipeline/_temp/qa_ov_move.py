# -*- coding: utf-8 -*-
"""QA 动态校验（只读）：任务总览移动体验重构 + 垂直滚动条。

加载**客户端已部署副本**（只读，绝不修改），在 lua51 桩环境里跑
`_temp/qa_ov_move.lua` 的行为断言：滚轮=平移 / 拖拽自停 / 视口全穿透 /
滚动条显隐与几何 / 滑块三处 OnUpdate 清理 / 重画刷新。

用法：python _temp/qa_ov_move.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = r'D:\Game\World of Warcraft\_classic_titan_\Interface\AddOns\BGLite\_temp\tools'
sys.path.insert(0, TOOLS)
sys.path.insert(0, HERE)

import tf_dryrun as T  # noqa: E402
from lupa import lua51  # noqa: E402

ADDON = (os.environ.get('DF_ADDON_ROOT')
         or r'D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\DungeonsForever')
TOC = os.path.join(ADDON, 'DungeonsForever.toc')
CLIENT_BUILD = int(os.environ.get('TF_BUILD', '16001'))

LUA_CASE = os.path.join(HERE, 'qa_ov_move.lua')

PASSED, FAILED = [], []


def ck(name, ok, extra=None):
    (PASSED if ok else FAILED).append(name)
    print('  [%s] %s%s' % ('OK ' if ok else 'FAIL', name,
                           '' if extra is None else '  [%s]' % extra))


# ---------------------------------------------------------------------------
# 逐帧补桩：几何 / 滚动位移 / 鼠标开关按真实客户端语义记账
# （tf_dryrun 的桩 GetWidth/GetHeight/GetVerticalScroll 一律回常数 100，
#   滚动条与拖拽的算术在那种桩上恒等于「无变化」，断言会变成假绿）
# ---------------------------------------------------------------------------
DECORATE = r'''
QAFRAMES = {}
do
  local _cf = CreateFrame
  local function decorate(f)
    rawset(f, "GetWidth", function(self)
      local w = rawget(self, "__w"); if w == nil then return 100 end; return w
    end)
    rawset(f, "GetHeight", function(self)
      local h = rawget(self, "__h"); if h == nil then return 100 end; return h
    end)
    rawset(f, "SetWidth", function(self, w) rawset(self, "__w", w); return self end)
    rawset(f, "SetHeight", function(self, h) rawset(self, "__h", h); return self end)
    rawset(f, "SetVerticalScroll", function(self, v) rawset(self, "__vs", v); return self end)
    rawset(f, "GetVerticalScroll", function(self) return rawget(self, "__vs") or 0 end)
    rawset(f, "SetHorizontalScroll", function(self, v) rawset(self, "__hs", v); return self end)
    rawset(f, "GetHorizontalScroll", function(self) return rawget(self, "__hs") or 0 end)
    rawset(f, "EnableMouse", function(self, v) rawset(self, "__mouse", v and true or false); return self end)
    rawset(f, "EnableMouseWheel", function(self, v) rawset(self, "__wheel", v and true or false); return self end)
    rawset(f, "GetEffectiveScale", function(self) return 1 end)
    rawset(f, "GetLeft", function(self) return 0 end)
    rawset(f, "GetBottom", function(self) return 0 end)
    rawset(f, "SetPoint", function(self, a, b, c, d, e)
      local l = rawget(self, "__ptlist")
      if not l then l = {}; rawset(self, "__ptlist", l) end
      l[#l + 1] = { a, b, c, d, e }
      rawset(self, "__pts", { a, b, c, d, e })
      return self
    end)
    QAFRAMES[#QAFRAMES + 1] = f
    return f
  end
  CreateFrame = function(a, b, c, d) return decorate(_cf(a, b, c, d)) end
  rawset(UIParent, "GetEffectiveScale", function() return 1 end)
  QACUR = { x = 400, y = 300 }
  QADOWN = true
  GetCursorPosition = function() return QACUR.x, QACUR.y end
  IsShiftKeyDown = function() return false end
  IsMouseButtonDown = function() return QADOWN == true end
end
'''


def main():
    print('=' * 72)
    print('QA 动态校验：总览平移 + 垂直滚动条（TF_BUILD=%d）' % CLIENT_BUILD)
    print('=' * 72)

    toc = open(TOC, encoding='utf-8', errors='replace').read()
    files = [re.sub(r'\s*\[[^\]]*\]\s*$', '', l.strip()).replace('\\', '/')
             for l in toc.splitlines()
             if l.strip() and not l.strip().startswith('##')]

    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(T.STUB)
    lua.execute(r'''
C_Timer = { After = function(t, fn)
    if t == 0 then fn(); return end
    SWEEPS = SWEEPS or {}
    SWEEPS[#SWEEPS + 1] = { t = t, fn = fn }
end }''')
    lua.execute('os = nil')
    lua.execute('time = function() return 1796850000 - 3660 end')
    lua.execute('BG.hui = nil')
    lua.execute('ADDON_ROOT = %r' % ADDON.replace('\\', '/'))
    lua.execute('TF_NS = TF_NS or {}')
    lua.execute('UIErrorsFrame = { AddMessage = function() end }')
    # 任务页所需的客户端任务口（与 df_dungeon_check 同口径）
    lua.execute(r'''
QUEST_DONE, QUEST_ON = {}, {}
C_QuestLog = {
  GetTitleForQuestID = function(id) return "客户端任务" .. tostring(id) end,
  GetQuestDifficultyLevel = function() return 16 end,
  IsQuestFlaggedCompleted = function(id) return QUEST_DONE[id] == true end,
  IsOnQuest = function(id) return QUEST_ON[id] == true end,
}
GetQuestLink = function(id) return "|cff808080|Hquest:" .. tostring(id) .. "|h[客户端任务]|r" end
UnitFactionGroup = function() return "Horde" end
UnitLevel = function() return 16 end
UnitName = function() return "QA" end
RAID_CLASS_COLORS = { WARRIOR = { r = 0.78, g = 0.61, b = 0.43 },
                      ROGUE = { r = 1.00, g = 0.96, b = 0.41 } }
''')
    lua.execute(
        'do local orig = GetBuildInfo; GetBuildInfo = function(...) '
        'local a,b,c,d,e = orig(...); return a, b, c, %d, e end end' % CLIENT_BUILD)
    lua.execute(DECORATE)

    # 锚点期望值取自**当前源码**（口径可能与任务简报不同：以代码实况为准并单独报告）
    src = open(os.path.join(ADDON, 'Core', 'DungeonUI.lua'), encoding='utf-8',
               errors='replace').read().replace('\r\n', '\n')
    m_top = re.search(r'vbar:SetPoint\("TOPRIGHT", sf, "TOPRIGHT", (-?\d+), (-?\d+)\)', src)
    m_bot = re.search(r'vbar:SetPoint\("BOTTOMRIGHT", sf, "BOTTOMRIGHT", (-?\d+), (-?\d+)\)', src)
    exp = (m_top.groups() + m_bot.groups()) if (m_top and m_bot) else (0, 0, 0, 0)
    lua.execute('EXP_TX, EXP_TY, EXP_BX, EXP_BY = %s, %s, %s, %s' % exp)
    m_qlw = re.search(r'DG\.Q_LIST_W = (\d+)', src)
    lua.execute('EXP_QLW = %s' % (m_qlw.group(1) if m_qlw else 520))
    print('   源码 vbar 锚点口径：TOPRIGHT(%s,%s) BOTTOMRIGHT(%s,%s)' % exp)
    print('   源码 Q_LIST_W = %s' % (m_qlw.group(1) if m_qlw else '?'))

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
            ck('加载 %s' % rel, False, 'loadfile 返回 nil')
            return 1
        try:
            chunk()
        except Exception as e:  # noqa: BLE001
            ck('加载 %s' % rel, False, str(e)[:300])
            return 1
    print('   已加载 %d 个文件（客户端副本）' % len([f for f in files if not f.lower().endswith('.xml')]))

    lua.execute('QA_CASE = %r' % LUA_CASE.replace('\\', '/'))
    out = lua.eval('dofile(QA_CASE)')
    for line in (out or '').split('\n'):
        if not line.strip():
            continue
        parts = line.split('\t')
        if len(parts) < 2:
            ck('Lua 侧输出缺制表符（多行文本被拆行）', False, line[:300])
            continue
        ck(parts[1], parts[0] == 'OK', parts[2] if len(parts) > 2 else None)

    print('=' * 72)
    print('通过 %d 项 / 失败 %d 项' % (len(PASSED), len(FAILED)))
    if FAILED:
        for f in FAILED:
            print('  ✗ %s' % f)
        return 1
    print('  ✓ 全部通过')
    return 0


if __name__ == '__main__':
    sys.exit(main())
