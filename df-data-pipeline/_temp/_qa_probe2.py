# -*- coding: utf-8 -*-
"""QA 独立探针：v4 配置面板「末页删除后当前页未回夹」反例复现（只读产品文件，不写盘）。

背景：v4 新增方案条分页（每页 4 枚）。RefreshConfig 按 cfg.page 铺图标，但删除方案后
不重算/回夹 cfg.page；当删除使总页数下降到当前页之下时，图标行会全空（等下一次翻页自愈）。
本探针在离线 harness 里复现该路径并打印证据。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import tf_dryrun as T          # noqa: E402
from lupa import lua51         # noqa: E402

ADDON = r'D:\workspace\DungeonsForever'
TOC = os.path.join(ADDON, 'DungeonsForever.toc')

files = [l.strip().replace('\\', '/') for l in
         open(TOC, encoding='utf-8', errors='replace').read().splitlines()
         if l.strip() and not l.strip().startswith('##')]

lua = lua51.LuaRuntime(unpack_returned_tuples=True)
lua.execute(T.STUB)
lua.execute('os = nil')
lua.execute('time = function() return 1796850000 end')
lua.execute('UnitClass = function() return "战士", "WARRIOR", 1 end')
lua.execute("ADDON_ROOT = %r" % ADDON.replace('\\', '/'))
lua.execute('TF_NS = TF_NS or {}')
lua.execute("do local o = GetBuildInfo; GetBuildInfo = function(...) "
            "local a,b,c,d = o(...); return a,b,c,16001,e end end")
lua.execute(r'''
QA = { R = {} }
function QA.ck(name, ok, extra)
    QA.R[#QA.R+1] = (ok and "OK" or "FAIL") .. "\t" .. name .. "\t" .. (extra ~= nil and tostring(extra) or "")
end
function QA.run(chunk)
    QA.R = {}
    local ok, err = pcall(chunk)
    if not ok then QA.R[#QA.R+1] = "FAIL\t[抛异常]\t" .. tostring(err) end
    return table.concat(QA.R, "\n")
end
function QA.reset(schemes, chooseID)
    local LF = TF_NS.LootFilter
    DungeonsForeverDB = { ui = {} }
    LF.__store = nil
    local st = LF.GetStore()
    for i = #st, 1, -1 do st[i] = nil end
    for i = 1, #(schemes or {}) do st[i] = schemes[i] end
    st.chooseID = chooseID
    LF.ClearResults()
    return st
end
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
    ch = loadfile(rel)
    if ch is None:
        print('load nil:', rel)
        sys.exit(1)
    ch()


def LE(expr):
    return lua.eval('(function()\n' + expr + '\nend)()')


out = LE(r'''return QA.run(function()
    local LF, D, UI = TF_NS.LootFilter, TF_NS.LootFilterData, TF_NS.LootFilterUI
    if TF_NS.hui then TF_NS.hui.ReskinToggle = function() end end
    UI:EnsureConfig()
    local cfg = UI.cfg
    local S = {}
    for i = 1, 6 do
        S[i] = { Name="s"..i, Icon="Interface\\Icons\\INV_Sword_01",
                 Weapon={}, Armor={}, ShuXing={}, Class={}, BnetAccount={}, Tank={} }
    end
    QA.reset(S, 5)
    cfg.page = 1
    UI:RefreshConfig()
    local function shownCount()
        local n = 0
        for s = 1, 4 do if cfg.icons[s]:IsShown() then n = n + 1 end end
        return n
    end
    QA.ck("前置：6 套方案时切到第 2 页，图标 Show 数 = 2（#存在方案 = 2）",
          shownCount() == 2, shownCount())
    QA.ck("前置：CountPages = 2", UI:CountPages() == 2, UI:CountPages())
    -- 模拟 SchemeActionMenu 的「删除方案」：LF.DeleteScheme + RefreshBar + RefreshConfig（无 TurnPage）
    LF.DeleteScheme(6); UI:RefreshBar(); UI:RefreshConfig()
    QA.ck("删 1 个（剩 5）后：仍 2 页，第 2 页 Show 数 = 1",
          UI:CountPages() == 2 and shownCount() == 1, "pages=" .. UI:CountPages() .. " shown=" .. shownCount())
    LF.DeleteScheme(5); UI:RefreshBar(); UI:RefreshConfig()
    -- 此时 #store == 4 → CountPages == 1，但 cfg.page 仍为 1（越界）
    local pages = UI:CountPages()
    local shown = shownCount()
    QA.ck("★ 反例：删到只剩 4 套（CountPages=1）后 cfg.page 仍为 1（未回夹）",
          cfg.page == 1, "page=" .. tostring(cfg.page))
    QA.ck("★ 反例：此时第 2 页图标行全空（4 枚全 Hide），但确实存在 4 个方案",
          shown == 0, "shown=" .. shown .. " #store=" .. #LF.GetStore())
    -- 左箭头是否仍可点（能自愈的唯一入口）
    local oLM = cfg.left.EnableMouse
    local lrec
    cfg.left.EnableMouse = function(self, v) lrec = v; return oLM(self, v) end
    UI:RefreshConfig()
    cfg.left.EnableMouse = oLM
    QA.ck("★ 反例：左箭头仍 EnableMouse(true)（唯一自愈入口；不做则整屏空图标）",
          lrec == true, tostring(lrec))
end)''')

print(out)
