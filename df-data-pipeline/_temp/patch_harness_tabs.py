# -*- coding: utf-8 -*-
"""QB_SET_TABS harness 守卫（2026-10-08）：
  · df_dungeon_check.py —— ㊷ 静态断言 ×3（QuickBar 小卡/落盘、DungeonUI 重排、Core 配置）
                          + ㊱ 卡片背景断言随行挂卡修正（-6→-36、行不得挂 pop）
                          + QB_SCRIPT 动态断言（行数 / 小卡 / 可见性翻转 / 当前页兜底）
  · df_mut_check.py     —— 反向变异 ×4（不收显隐 / 不隐藏 / 不落存档 / 不回填）
  · df_check_new_muts.py —— DEFAULT_WANT 登记 ×4
纪律：锚点命中数必须 == 1；幂等（标记串在即跳过）。
"""
import io
import os

ROOT = r"D:/workspace/DungeonsForever"


def load(p):
    return io.open(os.path.join(ROOT, p), encoding="utf-8", newline="").read()


def save(p, s):
    io.open(os.path.join(ROOT, p), "w", encoding="utf-8", newline="").write(s)


def eol_of(s):
    return "\r\n" if "\r\n" in s else "\n"


def adapt(t, nl):
    return t.replace("\n", nl) if nl == "\r\n" else t


def patch(p, jobs, marker):
    s = load(p)
    if marker in s:
        print("SKIP (already patched):", p)
        return
    nl = eol_of(s)
    for old, new in jobs:
        old2, new2 = adapt(old, nl), adapt(new, nl)
        n = s.count(old2)
        assert n == 1, "anchor hits=%d in %s: %r" % (n, p, old2[:70])
        s = s.replace(old2, new2, 1)
    save(p, s)
    print("OK:", p)


CHECK = "_temp/df_dungeon_check.py"
MUT = "_temp/df_mut_check.py"
NEWMUT = "_temp/df_check_new_muts.py"

# ───────────── 1. df_dungeon_check.py ─────────────
patch(CHECK, [
    # H1：㊱ 静态断言随行挂卡修正（顶 -6→-36 + 行必须挂卡、禁止再挂回 pop）
    (
        "   and 'self.cardBg:SetPoint(\"TOPLEFT\", pop, \"TOPLEFT\", 6, -6)' in _qb_src\n"
        "   and 'self.cardBg:SetPoint(\"TOPRIGHT\", pop, \"TOPRIGHT\", -6, -6)' in _qb_src\n"
        "   and 'self.cardBg:SetHeight(6 - y)' in _qb_src\n",
        "   and 'self.cardBg:SetPoint(\"TOPLEFT\", pop, \"TOPLEFT\", 6, -36)' in _qb_src\n"
        "   and 'self.cardBg:SetPoint(\"TOPRIGHT\", pop, \"TOPRIGHT\", -6, -36)' in _qb_src\n"
        "   and 'self.cardBg:SetHeight(6 - y)' in _qb_src\n"
        "   and 'local host = self.cardBg' in _qb_src\n"
        "   and 'Fs(pop' not in _qb_src and 'Toggle(pop)' not in _qb_src\n",
    ),
    # H2：㊷ QuickBar 静态断言（小卡 / 落盘 / SyncSettings 回填 / Apply 恒收）
    (
        "   and _qb_src.find('self.cardBg = card') < _qb_src.find('local function Header(text)'))",
        "   and _qb_src.find('self.cardBg = card') < _qb_src.find('local function Header(text)'))\n"
        "ck('★★ ㊷ 标签页开关小卡（QB_SET_TABS，2026-10-08 用户：七页签开关收一张 L3 小卡"
        " + 存档落盘 + SyncSettings 回填 + Apply 恒收显隐）',\n"
        "   'QB_SET_TABS' in _qb_src\n"
        "   and 'set.tabCard = tabCard' in _qb_src\n"
        "   and 'tabs[key] = v' in _qb_src\n"
        "   and 'for k, tg in pairs(set.tabs or {}) do' in _qb_src\n"
        "   and 'tg:SetChecked(cfg.tabs[k] ~= false)' in _qb_src\n"
        "   and 'if ns.ApplyTabVisibility then ns.ApplyTabVisibility() end' in _qb_src\n"
        "   and 'ns.hui.BuildRoundedBG(tabCard, 8, ns.hui.layer.L3, \"both\", true, 1)' in _qb_src\n"
        "   and _qb_src.find('set.tabs = {}') < _qb_src.find('self.cardBg:SetHeight(6 - y)'))",
    ),
    # H3：㊷ DungeonUI / Core 静态断言（挂在 _ex_src 装载之后）
    (
        "_ex_src = open(os.path.join(ADDON, 'Core', 'ExploreUI.lua'), encoding='utf-8',\n"
        "               errors='replace').read().replace('\\r\\n', '\\n')",
        "_ex_src = open(os.path.join(ADDON, 'Core', 'ExploreUI.lua'), encoding='utf-8',\n"
        "               errors='replace').read().replace('\\r\\n', '\\n')\n"
        "ck('★★ ㊷ 标签页显隐重排（QB_SET_TABS，2026-10-08 用户：BuildSubTabs 收口"
        " + 隐藏钮重锚不占位 + host 收宽 + 分段轨重挂 + 当前页兜底落回第一可见页）',\n"
        "   'QB_SET_TABS' in _dg_src\n"
        "   and 'function ns.ApplyTabVisibility()' in _dg_src\n"
        "   and 'ns.ApplyTabVisibility() -- QB_SET_TABS' in _dg_src\n"
        "   and 'bt:SetShown(show)' in _dg_src\n"
        "   and 'host:SetSize(totalW, BTN_H)' in _dg_src\n"
        "   and 'U.subCtrl:AttachButtons(vis)' in _dg_src\n"
        "   and 'U.curSub = firstVis' in _dg_src\n"
        "   and _dg_src.find('function ns.ApplyTabVisibility()')"
        " < _dg_src.find('function U:Build()'))\n"
        "ck('★★ ㊷ 标签页显隐配置（Core.lua：QUICK_TABS 七键 + QuickCfg.tabs 懒默认全开）',\n"
        "   'ns.QUICK_TABS' in _core_src\n"
        "   and 'if type(q.tabs) ~= \"table\" then q.tabs = {} end' in _core_src\n"
        "   and 'for _, k in ipairs(ns.QUICK_TABS) do' in _core_src)",
    ),
    # H4：㊱ 动态断言随几何修正（[5] -6 → -36）
    (
        'ck("★ ㊱ 卡片背景锚定弹窗内容区（末次 SetPoint = TOPRIGHT 槽 -6）",\n'
        "   cardBg ~= nil and cardBg.__pts ~= nil and cardBg.__pts[1] == 'TOPRIGHT'\n"
        "   and cardBg.__pts[4] == -6 and cardBg.__pts[5] == -6,",
        'ck("★ ㊱ 卡片背景锚定弹窗内容区（末次 SetPoint = TOPRIGHT 槽 x=-6 y=-36）",\n'
        "   cardBg ~= nil and cardBg.__pts ~= nil and cardBg.__pts[1] == 'TOPRIGHT'\n"
        "   and cardBg.__pts[4] == -6 and cardBg.__pts[5] == -36,",
    ),
    # H5：QB_SCRIPT 尾部加 ㊷ 动态断言（行数 / 小卡 / 可见性翻转 / 当前页兜底 / 恢复）
    (
        "return table.concat(R, '\\n')\n"
        "\"\"\"",
        "-- ★ 标签页显隐（QB_SET_TABS，2026-10-08 用户）\n"
        "local wantRows = ns.LoadForeverPages and 7 or 2\n"
        "local nTabRows = 0\n"
        "for _ in pairs(QB.set.tabs or {}) do nTabRows = nTabRows + 1 end\n"
        "ck('★ 标签页开关行数（' .. wantRows .. '）', nTabRows == wantRows, 'n=' .. nTabRows)\n"
        "ck('★ 标签页小卡已建（挂大卡）', QB.set.tabCard ~= nil)\n"
        "local MU = ns.ProfHost and ns.ProfHost.U\n"
        "local duBtn, raBtn\n"
        "if MU and MU.subTabs then\n"
        "  for _, t in ipairs(MU.subTabs) do\n"
        "    if t.key == 'Dungeons' then duBtn = t.button end\n"
        "    if t.key == 'Raids' then raBtn = t.button end\n"
        "  end\n"
        "end\n"
        "ck('★ 主窗页签钮已建（Dungeons/Raids）', duBtn ~= nil and raBtn ~= nil)\n"
        "if duBtn and raBtn and ns.ApplyTabVisibility then\n"
        "  if ns.TalentSimFrame and not ns.TalentSimFrame:IsShown() then ns.TalentSimFrame:Show() end\n"
        "  ns.QuickCfg().tabs.Raids = false\n"
        "  ns.ApplyTabVisibility()\n"
        "  ck('★ 隐藏团本 → 可见性翻转（5人本可见 / 团本不可见）',\n"
        "     duBtn:IsVisible() and not raBtn:IsVisible())\n"
        "  ck('★ 隐藏团本 → 当前页不落在团本', MU.curSub ~= 'Raids')\n"
        "  ns.QuickCfg().tabs.Raids = true\n"
        "  ns.ApplyTabVisibility()\n"
        "  ck('★ 恢复团本 → 重新可见', raBtn:IsVisible())\n"
        "end\n"
        "\n"
        "return table.concat(R, '\\n')\n"
        "\"\"\"",
    ),
], "QB_SET_TABS_harness")

# ───────────── 2. df_mut_check.py：反向变异 ×4 ─────────────
patch(MUT, [
    (
        "    ('快捷栏：设置弹窗卡片背景高度不回填（底板缩成 0 高 = 没有卡片背景）',"
        " ('Core/QuickBar.lua', (b'    if self.cardBg then self.cardBg:SetHeight(6 - y) end\\n',"
        " b'    -- MUT: card bg height never set\\n'))),\n"
        "]",
        "    ('快捷栏：设置弹窗卡片背景高度不回填（底板缩成 0 高 = 没有卡片背景）',"
        " ('Core/QuickBar.lua', (b'    if self.cardBg then self.cardBg:SetHeight(6 - y) end\\n',"
        " b'    -- MUT: card bg height never set\\n'))),\n"
        "    # ㊷ 标签页显隐（2026-10-08 用户）\n"
        "    ('标签页：BuildSubTabs 不收显隐（重启后隐藏页签复活）',\n"
        "     ('Core/DungeonUI.lua', b'    ns.ApplyTabVisibility() -- QB_SET_TABS',"
        " b'    do end -- MUT: tab visibility pass dropped')),\n"
        "    ('标签页：ApplyTabVisibility 不隐藏（开关点了页签还在）',\n"
        "     ('Core/DungeonUI.lua', b'            bt:SetShown(show)',"
        " b'            bt:SetShown(true) -- MUT: never hide')),\n"
        "    ('标签页：开关不落存档（重开界面显隐回默认全开）',\n"
        "     ('Core/QuickBar.lua', b'tabs[key] = v', b'-- MUT: tabs[key] = v dropped')),\n"
        "    ('标签页：SyncSettings 不回填开关态（重开设置弹窗勾选错）',\n"
        "     ('Core/QuickBar.lua', b'        tg:SetChecked(cfg.tabs[k] ~= false)',"
        " b'        -- MUT: tabs sync dropped')),\n"
        "]",
    ),
], "标签页：BuildSubTabs 不收显隐")

# ───────────── 3. df_check_new_muts.py：DEFAULT_WANT 登记 ─────────────
patch(NEWMUT, [
    (
        "    '快捷栏：设置弹窗卡片背景高度不回填（底板缩成 0 高 = 没有卡片背景）',\n]",
        "    '快捷栏：设置弹窗卡片背景高度不回填（底板缩成 0 高 = 没有卡片背景）',\n"
        "    # ㊷ 标签页显隐（2026-10-08 用户）\n"
        "    '标签页：BuildSubTabs 不收显隐（重启后隐藏页签复活）',\n"
        "    '标签页：ApplyTabVisibility 不隐藏（开关点了页签还在）',\n"
        "    '标签页：开关不落存档（重开界面显隐回默认全开）',\n"
        "    '标签页：SyncSettings 不回填开关态（重开设置弹窗勾选错）',\n]",
    ),
], "标签页：BuildSubTabs 不收显隐")

print("HARNESS PATCHES DONE")
