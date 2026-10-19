# -*- coding: utf-8 -*-
"""
首屏懒建（第 3 刀）：详情页自身的四个「重池」也分帧建。

  第 2 刀后实测：打开界面 368→68 帧，但**首次打开详情页**变成 264 帧（成本转移了）。
  本刀把详情页里四块重活拆成幂等构建器，用带同步兜底的分帧器摊到随后的空闲帧：
    - boss 卡池（卡片视图用，最重）
    - 任务两栏 + 任务页底板
    - 攻略栏
    - 地图页（MapModule.Build）
  同步只建「壳体」（hero/返回/四页签/标题/芯片/筛选/掉落滚动区），首次点副本 ≈ 25 帧。

  ★ 分帧器带同步兜底：C_Timer 不可用（离线 harness）时 pump 递归同步跑完，
    断言看到的仍是「全都建好了」⇒ harness 几乎零改动。

行尾：DungeonUI.lua 是 CRLF；内部按 LF 处理，写回时还原。
"""
import shutil

P = r'D:/workspace/DungeonsForever/Core/DungeonUI.lua'
s = open(P, 'rb').read().decode('utf-8').replace('\r\n', '\n')

def rep(old, new, why):
    global s
    n = s.count(old)
    assert n == 1, '锚点命中 %d 次: %s' % (n, why)
    s = s.replace(old, new, 1)
    print('  ok  ' + why)

# ── 0) 切分出四个重池 ───────────────────────────────────────────────────
A_START  = '    -- ★★ boss 卡池（卡片视图专用，2026-10-01）'
B1_START = '    local qscroll = CreateFrame("ScrollFrame", nil, detail)\n'
C_START  = '    local gscroll = CreateFrame("ScrollFrame", nil, detail)\n'
D_START  = ('    if ns.MapModule then\n'
            '        U.dungeonMapFrame = ns.MapModule.Build(detail, hero)\n'
            '    end\n')
P_START  = '    local function questPlate()\n'
P_END    = '    U.dungeonQPlateR = plateR\n'

iA, iB1, iC, iD, iP = (s.index(x) for x in (A_START, B1_START, C_START, D_START, P_START))
jP = s.index(P_END) + len(P_END)
assert iA < iB1 < iC < iD < iP < jP

blockA  = s[iA:iB1]    # boss 卡池
blockB1 = s[iB1:iC]    # qscroll + qdet
blockC  = s[iC:iD]     # gscroll
blockD  = s[iD:iP]     # MapModule.Build
blockP  = s[iP:jP]     # questPlate ×2（依赖 qscroll / qdet）
HEAD, TAIL = s[:iA], s[jP:]
print('  ok  切分：A=%d B1=%d C=%d D=%d P=%d 行' % tuple(
    x.count('\n') for x in (blockA, blockB1, blockC, blockD, blockP)))

# ── 1) 分帧调用（接在壳体之后，闭合到函数原有的 end）────────────────────
PUSH = (
    '    -- ★ 分帧：四块重池摊到随后的空闲帧里建（首屏只付壳体 ≈ 25 帧）。\n'
    '    --   每块都幂等；切页/切视图时若还没轮到，会由对应的 Ensure* 同步补建。\n'
    '    DG.PushStep(DG.EnsureCardPool)\n'
    '    DG.PushStep(DG.EnsureQuestLane)\n'
    '    DG.PushStep(DG.EnsureGuideLane)\n'
    '    DG.PushStep(DG.EnsureMapPage)\n'
    '    DG.RunSteps()\n'
)
s = HEAD + PUSH + TAIL

# ── 2) 插入分帧器 + 四个子块构建器 ──────────────────────────────────────
ANCHOR = ('-- ══════════════════════════════════════════════════════════════════════════\n'
          '-- ★★★ 懒建：详情页 / 总览页（2026-10-03「打开就卡死」第二刀）')
NEWFUNCS = (
    '-- ══════════════════════════════════════════════════════════════════════════\n'
    '-- ★★ 分帧器：把一串「建帧块」摊到随后的空闲帧里逐块执行。\n'
    '--   ★ 同步兜底：C_Timer 不可用（离线 harness / 极端环境）时**递归同步跑完**，\n'
    '--     调用方返回时一切就绪 —— 断言因此看到的仍是「全都建好了」，无需感知分帧。\n'
    '--   ★ 幂等由各子块自己的 built 闸保证：若分帧还没轮到就被「按需同步」抢先建过，\n'
    '--     轮到执行时会直接 return，不重复建。\n'
    '-- ══════════════════════════════════════════════════════════════════════════\n'
    'DG.pendingSteps = {}\n'
    'DG.stepping = false\n'
    'function DG.PushStep(fn)\n'
    '    DG.pendingSteps[#DG.pendingSteps + 1] = fn\n'
    'end\n'
    'function DG.RunSteps()\n'
    '    if DG.stepping then return end\n'
    '    DG.stepping = true\n'
    '    local function pump()\n'
    '        local fn = table.remove(DG.pendingSteps, 1)\n'
    '        if not fn then\n'
    '            DG.stepping = false\n'
    '            return\n'
    '        end\n'
    '        local ok, err = pcall(fn)\n'
    '        if not ok then\n'
    '            print("|cffff5040[无限副本手册] 分帧构建出错（已跳过该块）：|r" .. tostring(err))\n'
    '        end\n'
    '        if #DG.pendingSteps > 0 then\n'
    '            if type(C_Timer) == "table" and type(C_Timer.After) == "function" then\n'
    '                C_Timer.After(0, pump)\n'
    '            else\n'
    '                pump()\n'
    '            end\n'
    '        else\n'
    '            DG.stepping = false\n'
    '        end\n'
    '    end\n'
    '    pump()\n'
    'end\n'
    '\n'
    '-- ══ 详情页四个「重池」（幂等；分帧 + 按需同步双入口）══════════════════════\n'
    '-- boss 卡池（卡片视图专用）\n'
    'function DG.EnsureCardPool()\n'
    '    if U.cardPoolBuilt then return end\n'
    '    local dchild, pool = U.dungeonDetailChild, U.dungeonDetailPool\n'
    '    if not (dchild and pool) then return end\n'
    '    U.cardPoolBuilt = true\n'
    + blockA +
    'end\n'
    '\n'
    '-- 任务两栏 + 任务页底板\n'
    'function DG.EnsureQuestLane()\n'
    '    if U.questLaneBuilt then return end\n'
    '    local detail = U.dungeonDetail\n'
    '    if not detail then return end\n'
    '    U.questLaneBuilt = true\n'
    + blockB1 + blockP +
    'end\n'
    '\n'
    '-- 攻略栏\n'
    'function DG.EnsureGuideLane()\n'
    '    if U.guideLaneBuilt then return end\n'
    '    local detail = U.dungeonDetail\n'
    '    if not detail then return end\n'
    '    U.guideLaneBuilt = true\n'
    + blockC +
    'end\n'
    '\n'
    '-- 地图页\n'
    'function DG.EnsureMapPage()\n'
    '    if U.mapPageBuilt then return end\n'
    '    local detail, hero = U.dungeonDetail, U.dungeonDetailHero\n'
    '    if not (detail and hero) then return end\n'
    '    U.mapPageBuilt = true\n'
    + blockD +
    'end\n'
    '\n'
)
rep(ANCHOR, NEWFUNCS + ANCHOR, '插入分帧器 + 四个子块构建器')

# ── 3) RenderDungeonTab：切页前先确保该栏已建（分帧没轮到就同步补）──────
rep('''    if isQuest then
        U:RenderDungeonQuests()
    elseif isGuide then
        U:RenderDungeonGuide()
    elseif isMap then
        if ns.MapModule then ns.MapModule.Paint(U.dungeonDetailCur) end
    else
        U:RenderDungeonLoot()
    end''',
'''    if isQuest then
        DG.EnsureQuestLane()          -- ★ 分帧没轮到就同步补建（切页不空白）
        U:RenderDungeonQuests()
    elseif isGuide then
        DG.EnsureGuideLane()
        U:RenderDungeonGuide()
    elseif isMap then
        DG.EnsureMapPage()
        if ns.MapModule then ns.MapModule.Paint(U.dungeonDetailCur) end
    else
        U:RenderDungeonLoot()
    end''',
    'RenderDungeonTab 按页签补建')

# ── 4) 卡片视图入口补建 boss 卡池 ───────────────────────────────────────
rep('''function U:RenderDungeonLootCards(groups, filter, takeCard)''',
    '''function U:RenderDungeonLootCards(groups, filter, takeCard)
    DG.EnsureCardPool()               -- ★ 卡片视图需要 boss 卡池；没轮到就同步补建''',
    'RenderDungeonLootCards 补建卡池')

rep('''    local nv = (v == "card") and "card" or "list"
    U.lootView = nv
    DB().lootView = nv
    U:RefreshLootViewBtns()''',
'''    local nv = (v == "card") and "card" or "list"
    U.lootView = nv
    DB().lootView = nv
    if nv == "card" then DG.EnsureCardPool() end   -- ★ 首次切卡片视图才建 boss 卡池
    U:RefreshLootViewBtns()''',
    'SetLootView 切卡片视图时补建卡池')

# ── 5) U:Build 重置四个子块标志 ─────────────────────────────────────────
rep('    U.dungeonBuilt = false\n    U.detailBuilt = nil\n    U.overviewBuilt = nil\n',
    '    U.dungeonBuilt = false\n    U.detailBuilt = nil\n    U.overviewBuilt = nil\n'
    '    U.cardPoolBuilt = nil\n    U.questLaneBuilt = nil\n'
    '    U.guideLaneBuilt = nil\n    U.mapPageBuilt = nil\n',
    'U:Build 重置子块标志')

# ── 写回 ────────────────────────────────────────────────────────────────
shutil.copy(P, r'D:/workspace/DungeonsForever/_temp/_bak_DungeonUI_lazy3.lua.bak')
open(P, 'wb').write(s.replace('\n', '\r\n').encode('utf-8'))
print('  done 已写回（CRLF 还原）')
