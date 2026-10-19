# -*- coding: utf-8 -*-
"""同步更新 harness 断言 + 变异锚点以适配「懒构建」（2026-10-03）

df_dungeon_check.py 为 CRLF；df_mut_check.py 为 LF —— 各自保持原行尾。
"""
import io, sys

BASE = r'D:\workspace\DungeonsForever\_temp'


def patch(fname, nl, edits):
    p = BASE + '\\' + fname
    s = io.open(p, 'r', encoding='utf-8', newline='').read()

    def rep(old, new, label):
        nonlocal s
        old = old.replace('\n', nl)
        new = new.replace('\n', nl)
        c = s.count(old)
        if c != 1:
            print('!! [%s] %s 命中 %d 次（期望 1）' % (fname, label, c))
            sys.exit(1)
        s = s.replace(old, new, 1)
        print('OK  %s / %s' % (fname, label))

    for e in edits:
        rep(e[0], e[1], e[2])
    io.open(p, 'w', encoding='utf-8', newline='').write(s)
    print('--- %s 写回完成' % fname)


NL_D = '\r\n'
NL_M = '\n'

# ══════════════════════════════════════════════════════════════════════
# df_dungeon_check.py
# ══════════════════════════════════════════════════════════════════════
E = []

# R1 团本静态断言 → 懒构建
E.append((
    '''    _bld = src[src.index('function U:Build()'):src.index('function U:Refresh()')]
    ck('★ 团本页在 Build 里一次建好（不在切页时懒建 → 保住「渲染路径零新建帧」不变量）',
       'U.raidPage = CreateFrame("Frame", nil, panel)' in _bld
       and 'if ns.RaidModule then ns.RaidModule.Build(U.raidPage) end' in _bld)
''',
    '''    _bld = src[src.index('function U:Build()'):src.index('function U:Refresh()')]
    # ★★ 懒构建（2026-10-03）：首屏只建当前子页，其余页由 U:EnsureBuilt 首次切到时建。
    _lazy = src[src.index('function U:EnsureBuilt(k)'):src.index('function U:SwitchSub(key)')]
    ck('★★ 懒构建：Build 只建空壳帧，团本页内容推迟到 U:EnsureBuilt（首屏不再整包建帧）',
       'U.raidPage = CreateFrame("Frame", nil, panel)' in _bld
       and 'ns.RaidModule.Build(U.raidPage)' not in _bld
       and 'U:EnsureBuilt("Raids")' in _lazy
       and 'ns.RaidModule.Build(U.raidPage)' in _lazy)
    ck('★★ 懒构建：SwitchSub 每次切页前先确保该页已建（五页齐）',
       'U:EnsureBuilt("Raids")' in _sw and 'U:EnsureBuilt("Professions")' in _sw
       and 'U:EnsureBuilt("Explore")' in _sw and 'U:EnsureBuilt("Bis")' in _sw
       and 'U:EnsureBuilt("Tier")' in _sw)
    ck('★★ 懒构建：OnShow 后分帧预热其余子页（C_Timer 不可用时静默退化）',
       'U:SchedulePrebuild()' in src
       and 'if type(C_Timer) ~= "table" or type(C_Timer.After) ~= "function" then return end' in _lazy
       and 'C_Timer.After(0.05, step)' in _lazy)
''', 'R1 团本静态'))

# R2 探索静态断言
E.append((
    '''    ck('★ 探索页在 Build 里一次建好（不在切页时懒建）',
       'U.explorePage = CreateFrame("Frame", nil, panel)' in _bld
       and 'if ns.ExploreModule then ns.ExploreModule.Build(U.explorePage) end' in _bld)
''',
    '''    ck('★★ 懒构建：探索页内容推迟到 U:EnsureBuilt（Build 里只留空壳帧）',
       'U.explorePage = CreateFrame("Frame", nil, panel)' in _bld
       and 'ns.ExploreModule.Build(U.explorePage)' not in _bld
       and 'U:EnsureBuilt("Explore")' in _lazy
       and 'ns.ExploreModule.Build(U.explorePage)' in _lazy)
''', 'R2 探索静态'))

# R3 专业静态断言
E.append((
    '''    ck('★ 专业页在 Build 里一次建好（改成切页懒建就破「渲染路径零新建帧」）',
       'U.profPage = CreateFrame("Frame", nil, panel)' in _bld
       and 'ns.ProfModule.Build(U.profPage)' in _bld
       and 'if ns.LoadForeverPages then' in _bld)
''',
    '''    ck('★★ 懒构建：专业页内容推迟到 U:EnsureBuilt（Build 里只留空壳帧）',
       'U.profPage = CreateFrame("Frame", nil, panel)' in _bld
       and 'ns.ProfModule.Build(U.profPage)' not in _bld
       and 'if ns.LoadForeverPages then' in _bld
       and 'U:EnsureBuilt("Professions")' in _lazy
       and 'ns.ProfModule.Build(U.profPage)' in _lazy)
''', 'R3 专业静态'))

# R5 Build 之后：懒构建运行时不变量
E.append((
    '''    if not U.built then U:Build() end
''',
    '''    if not U.built then U:Build() end

    -- ★★ 懒构建（2026-10-03）：Build 只建当前子页，其余页必须**尚未**建
    ck("★★ 懒构建：首屏只建当前子页（Raid/Prof/Explore/Bis/Tier 的 built 仍为 false）",
       (TF_NS.RaidModule == nil or TF_NS.RaidModule.built ~= true)
       and (TF_NS.ProfModule == nil or TF_NS.ProfModule.built ~= true)
       and (TF_NS.ExploreModule == nil or TF_NS.ExploreModule.built ~= true)
       and (TF_NS.BisModule == nil or TF_NS.BisModule.built ~= true)
       and (TF_NS.TierModule == nil or TF_NS.TierModule.built ~= true))
    ck("★★ 懒构建：账本 U.subBuilt 已初始化（切页后逐项置位）",
       type(U.subBuilt) == "table")
''', 'R5 运行时首屏不变量'))

# R6 Tier 段：切页后再断内容
E.append((
    '''        local TM = TF_NS.TierModule
        ck("★★ 职业指南页已建（TierModule 导出 + tierPage 常驻帧）",
           TM ~= nil and U.tierPage ~= nil)
        if TM then
          local _nSub = 0
''',
    '''        local TM = TF_NS.TierModule
        ck("★★ 职业指南页空壳帧常驻（TierModule 导出 + tierPage 帧；内容懒建）",
           TM ~= nil and U.tierPage ~= nil and TM.built ~= true)
        if TM then
          -- ★ 懒构建：页面内容要切到该页才建 → 先切过去
          U:SwitchSub("Tier")
          ck("★★ 切到指南页 → 内容已懒建（TierModule.built = true）", TM.built == true)
          local _nSub = 0
''', 'R6 Tier 切页'))

# R6b 二次切页零新建帧
E.append((
    '''          U:SwitchSub("Tier")
          ck("★★ SwitchSub(Tier) → 指南页显示 / 副本页隐藏（互斥不破）",
''',
    '''          local _fT = FRAMES
          U:SwitchSub("Tier")
          ck("★★ 二次切到指南页零新建帧（懒建只付一次，切页不卡）", FRAMES == _fT, FRAMES - _fT)
          ck("★★ SwitchSub(Tier) → 指南页显示 / 副本页隐藏（互斥不破）",
''', 'R6b Tier 二次切页'))

# R7 团本段：切页后再断内容
E.append((
    '''      local RM = TF_NS.RaidModule
      ck("★★ 团本页是常驻帧（已接 RaidModule 建页）", U.raidPage ~= nil and RM ~= nil)
''',
    '''      local RM = TF_NS.RaidModule
      ck("★★ 团本页空壳帧常驻（内容懒建，未切过 built 仍为 false）",
         U.raidPage ~= nil and RM ~= nil and RM.built ~= true)
      -- ★ 懒构建：团本断言需要页面内容 → 先切过去（首次会建页并记账）
      U:SwitchSub("Raids")
      ck("★★ 首次切团本 → 内容已懒建且记账（RaidModule.built + U.subBuilt[Raids]）",
         RM.built == true and U.subBuilt ~= nil and U.subBuilt["Raids"] == true)
''', 'R7 团本切页'))

# R8 二次切团本零新建帧
E.append((
    '''      ck("★ 切团本零新建帧（空态骨架不做构建）", FRAMES == _f0, FRAMES - _f0)
''',
    '''      ck("★ 二次切团本零新建帧（懒建只付一次 → 切页零等待）", FRAMES == _f0, FRAMES - _f0)
''', 'R8 团本二次切页'))

# R9 探索段：切页后再断行池
E.append((
    '''      if IS_FOREVER then
        ck("★★ 探索模块已挂载且行池建满 40 本",
           TF_NS.ExploreModule ~= nil and #(TF_NS.ExploreModule.rows or {}) == 40,
           TF_NS.ExploreModule and #(TF_NS.ExploreModule.rows or {}))
''',
    '''      if IS_FOREVER then
        ck("★★ 探索模块已挂载（行池内容懒建，未切过为空）",
           TF_NS.ExploreModule ~= nil and TF_NS.ExploreModule.built ~= true)
        -- ★ 懒构建：行池要切到该页才建
        U:SwitchSub("Explore")
        ck("★★ 首次切探索 → 内容已懒建且行池建满 40 本",
           TF_NS.ExploreModule ~= nil and TF_NS.ExploreModule.built == true
           and #(TF_NS.ExploreModule.rows or {}) == 40,
           TF_NS.ExploreModule and #(TF_NS.ExploreModule.rows or {}))
''', 'R9 探索切页'))

# R10 二次切探索零新建帧
E.append((
    '''        ck("★ 切探索零新建帧（骨架首屏一次建全）", FRAMES == _fe0, FRAMES - _fe0)
''',
    '''        ck("★ 二次切探索零新建帧（懒建只付一次）", FRAMES == _fe0, FRAMES - _fe0)
''', 'R10 探索二次切页'))

# R11 专业段：未切=未建，切后内容就位
E.append((
    '''          ck("★ 页面骨架由 ProfModule.Build 建好（PD.built）", PD.built == true)
          ck("★ 行池 / 滚动容器就位（详情条 2026-09-23 晚已退役）",
             PD.child ~= nil and PD.scroll ~= nil and PD.detail == nil)
''',
    '''          -- ★ 懒构建（2026-10-03）：专业页内容要切到该页才建 —— 先断「未切 = 未建」，再切。
          ck("★★ 懒构建：未切过专业页时内容尚未建（PD.built 仍为 false）", PD.built ~= true)
''', 'R11 专业未切=未建'))

E.append((
    '''          ck("★ 首次进专业页只长行池、不重复建骨架（新建帧 < 64）", FRAMES - _f0 < 64, FRAMES - _f0)
''',
    '''          ck("★ 首次切到专业页会一次性建页（懒构建成本）", FRAMES - _f0 > 0, FRAMES - _f0)
          ck("★★ 切到专业页后内容已就位（PD.built + 行池/滚动容器）",
             PD.built == true and PD.child ~= nil and PD.scroll ~= nil and PD.detail == nil)
''', 'R11b 专业切页后内容'))

patch('df_dungeon_check.py', NL_D, E)

# ══════════════════════════════════════════════════════════════════════
# df_mut_check.py —— 变异锚点：原锚在 Build 里，已移到 U:EnsureBuilt
# ══════════════════════════════════════════════════════════════════════
M = []
M.append((
    """MUT_EXPLORE_PAGE_GONE = (
    b'        if ns.ExploreModule then ns.ExploreModule.Build(U.explorePage) end\\r\\n',
    b'        -- MUT: explore page build dropped\\r\\n')
""",
    """MUT_EXPLORE_PAGE_GONE = (
    # 2026-10-03 懒构建：建页调用从 U:Build() 移到 U:EnsureBuilt()，锚点跟着搬。
    b'    elseif k == "Explore" and ns.ExploreModule and U.explorePage then\\r\\n'
    b'        U.subBuilt[k] = true\\r\\n'
    b'        ns.ExploreModule.Build(U.explorePage)\\r\\n',
    b'    elseif k == "Explore" and ns.ExploreModule and U.explorePage then\\r\\n'
    b'        U.subBuilt[k] = true\\r\\n'
    b'        -- MUT: explore page build dropped\\r\\n')
""", 'MUT_EXPLORE_PAGE_GONE 锚点迁移到 U:EnsureBuilt'))

patch('df_mut_check.py', NL_M, M)
print('全部完成')
