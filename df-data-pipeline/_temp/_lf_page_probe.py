# -*- coding: utf-8 -*-
"""P3 自检：方案条翻页「页码回夹」非恒真探针（掉落页「装备过滤」面板 v4）。

缺陷（QA 用 _temp/_qa_probe2.py 复现）：
  方案条每页 4 枚图标。删除方案只走 SchemeActionMenu → LF.DeleteScheme + RefreshBar +
  RefreshConfig（**不经过 TurnPage**）。旧 RefreshConfig 直接按 cfg.page 铺图标、不回夹；
  当方案数从 6 删到 4 时，CountPages() 由 2 落回 1，而 cfg.page 仍停在 1 →
  base = 4，4 枚图标槽 idx 5..8 全空 → 整排 Hide，图标行变空白（要等下一次翻页才自愈）。

修复：在 UI:RefreshConfig() 里、**渲染图标之前**把页码夹回 [0, CountPages()-1]。

本探针只读产品文件，在离线 harness 里跑真实面板代码：
  1) 修复态：断言「剩 4 套时 cfg.page == 0 且 4 枚图标全 IsShown」（应 PASS）。
  2) 反证：把回夹行中性化（maxPage = 9999）后重跑，上面两条关键断言必须变红
     → 证明该断言非恒真（否则是白测）。反证阶段临时改 beta 文件，跑完立即还原并
     校验字节一致。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import tf_dryrun as T            # noqa: E402
from lupa import lua51           # noqa: E402

# 与 harness 一致：断的是已同步的 beta 副本（df_dungeon_check 亦以 beta 为产检对象）
BETA = r'D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\DungeonsForever'
TOC = os.path.join(BETA, 'DungeonsForever.toc')
LF_FILE = os.path.join(BETA, 'Core', 'LootFilterUI.lua')

# 回夹行（修复点）：中性化它 = 还原旧缺陷
CLAMP_ANCHOR = b'local maxPage = math.max(0, (UI:CountPages() or 1) - 1)'
CLAMP_NEUTER = b'local maxPage = 9999 -- MUT: clamp neutered'

# 关键断言名（反证时必须变红的两条）
KEY_PAGE = 'cfg.page 回夹到 0'
KEY_SHOWN = '4 枚全 Show'


def addon_files():
    return [l.strip().replace('\\', '/') for l in
            open(TOC, encoding='utf-8', errors='replace').read().splitlines()
            if l.strip() and not l.strip().startswith('##')]


# 场景：6 套 → cfg.page=1（第 2 页）→ 删到剩 4 套 → 期望回夹 & 图标齐全；再删空验 0 套边界。
SCENARIO = r'''return QA.run(function()
    local LF, UI = TF_NS.LootFilter, TF_NS.LootFilterUI
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
    QA.ck("前置：6 套时切到第 2 页，Show 数 = 2", shownCount() == 2, shownCount())
    QA.ck("前置：CountPages = 2", UI:CountPages() == 2, UI:CountPages())
    -- 模拟 SchemeActionMenu「删除方案」：DeleteScheme + RefreshBar + RefreshConfig（无 TurnPage）
    LF.DeleteScheme(6); UI:RefreshBar(); UI:RefreshConfig()
    QA.ck("删到 5 套：仍 2 页，第 2 页 Show = 1",
          UI:CountPages() == 2 and shownCount() == 1,
          "pages=" .. UI:CountPages() .. " shown=" .. shownCount())
    LF.DeleteScheme(5); UI:RefreshBar(); UI:RefreshConfig()
    -- 剩 4 套 → CountPages=1；旧代码 cfg.page 仍为 1（越界）→ 第 2 页整排空
    QA.ck("★ 剩 4 套：CountPages 回落到 1", UI:CountPages() == 1, UI:CountPages())
    QA.ck("★ cfg.page 回夹到 0（修复点）", cfg.page == 0, "page=" .. tostring(cfg.page))
    QA.ck("★ 剩 4 套图标行 4 枚全 Show（不再整排空）", shownCount() == 4, shownCount())
    -- 0 套边界：删空后 CountPages 仍 >= 1、page 不越界、0 图标且不报错
    LF.DeleteScheme(4); LF.DeleteScheme(3); LF.DeleteScheme(2); LF.DeleteScheme(1)
    UI:RefreshBar(); UI:RefreshConfig()
    QA.ck("0 套边界：CountPages >= 1 且 page = 0 且 0 图标不报错",
          UI:CountPages() >= 1 and (cfg.page or 0) == 0 and shownCount() == 0,
          "pages=" .. UI:CountPages() .. " page=" .. tostring(cfg.page)
          .. " shown=" .. shownCount())
end)'''


def build_runtime():
    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(T.STUB)
    lua.execute('os = nil')
    lua.execute('time = function() return 1796850000 end')
    lua.execute('UnitClass = function() return "战士", "WARRIOR", 1 end')
    lua.execute("ADDON_ROOT = %r" % BETA.replace('\\', '/'))
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
    for rel in addon_files():
        if rel.lower().endswith('.xml'):
            continue
        ch = loadfile(rel)
        if ch is None:
            raise RuntimeError('load nil: ' + rel)
        ch()
    return lua


def run_scenario():
    lua = build_runtime()
    return lua.eval('(function()\n' + SCENARIO + '\nend)()')


def show(tag, out):
    print('--- %s ---' % tag)
    for ln in (out or '').split('\n'):
        if ln.strip():
            print('    ' + ln)


def main():
    print('== P3 页码回夹探针（目标 = beta 产物）==')
    print('  beta =', BETA)

    out = run_scenario()
    show('修复态', out)
    fixed_ok = 'FAIL' not in (out or '')

    orig = open(LF_FILE, 'rb').read()
    n = orig.count(CLAMP_ANCHOR)
    print('  回夹锚点命中 = %d 次（要求 1）' % n)
    if n != 1:
        print('RESULT = SKIP（锚点不唯一，无法做反证）')
        return 2

    hit = False
    restored = False
    try:
        open(LF_FILE, 'wb').write(orig.replace(CLAMP_ANCHOR, CLAMP_NEUTER))
        out2 = run_scenario()
        show('反证：回夹中性化（maxPage=9999）', out2)
        reds = [ln for ln in (out2 or '').split('\n') if ln.startswith('FAIL')]
        hit = any(KEY_PAGE in ln for ln in reds) and any(KEY_SHOWN in ln for ln in reds)
        print('  两条关键断言变红 =', hit)
    finally:
        open(LF_FILE, 'wb').write(orig)
        restored = open(LF_FILE, 'rb').read() == orig
        print('  还原 beta 字节一致 =', restored)

    ok = fixed_ok and hit and restored
    print()
    print('修复态全绿 = %s | 反证命中 = %s | 还原一致 = %s'
          % (fixed_ok, hit, restored))
    print('RESULT =', 'PASS' if ok else 'FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
