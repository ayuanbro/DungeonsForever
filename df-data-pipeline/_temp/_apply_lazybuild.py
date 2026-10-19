# -*- coding: utf-8 -*-
"""懒构建 + 分帧预热补丁（2026-10-03）

起因：实机反馈「打开界面后整窗变灰」。实测首屏一次同步构建 6 个页面共 1673 帧。
本补丁把 U:Build() 里 5 个模块的 eager Build 改为懒建（首次切到该页才建），
并在 OnShow 后用 C_Timer 分帧逐页补建，使切页仍然零等待。

全程保持 CRLF（本文件行尾为 CRLF）。
"""
import io, sys

P = r'D:\workspace\DungeonsForever\Core\DungeonUI.lua'
NL = '\r\n'
s = io.open(P, 'r', encoding='utf-8', newline='').read()
before = s


def rep(old, new, label):
    global s
    c = s.count(old)
    if c != 1:
        print('!! [%s] 命中 %d 次（期望 1）' % (label, c))
        sys.exit(1)
    s = s.replace(old, new, 1)
    print('OK  %s' % label)


# ── ① Build 内 5 处 eager Build → 注释（内容改由 U:EnsureBuilt 首次切页时建） ──
rep(
    '    if ns.RaidModule then ns.RaidModule.Build(U.raidPage) end' + NL,
    '    -- ★ 懒构建：团本页内容见 U:EnsureBuilt("Raids")，首屏不再整包建帧' + NL,
    'Build/raids -> lazy')

rep(
    '        if ns.ProfModule then ns.ProfModule.Build(U.profPage) end' + NL,
    '        -- ★ 懒构建：专业页内容见 U:EnsureBuilt("Professions")' + NL,
    'Build/prof -> lazy')

rep(
    '        if ns.ExploreModule then ns.ExploreModule.Build(U.explorePage) end' + NL,
    '        -- ★ 懒构建：探索页内容见 U:EnsureBuilt("Explore")' + NL,
    'Build/explore -> lazy')

rep(
    '        if ns.BisModule then ns.BisModule.Build(U.bisPage) end' + NL,
    '        -- ★ 懒构建：BIS 配装页内容见 U:EnsureBuilt("Bis")' + NL,
    'Build/bis -> lazy')

rep(
    '        if ns.TierModule then ns.TierModule.Build(U.tierPage) end' + NL,
    '        -- ★ 懒构建：职业指南页内容见 U:EnsureBuilt("Tier")' + NL,
    'Build/tier -> lazy')

# ── ② Build 里初始化懒建账本 ──
rep(
    '    U.sourceCredits = {}' + NL,
    '    U.sourceCredits = {}' + NL +
    '    -- ★ 懒构建账本：记录已被触发建过的子页（见 U:EnsureBuilt）' + NL +
    '    U.subBuilt = {}' + NL,
    'Build/subBuilt init')

# ── ③ 插入 U:EnsureBuilt + U:SchedulePrebuild（在 SwitchSub 定义之前） ──
LAZY = (
    '-- ══════════════════════════════════════════════════════════════════════' + NL +
    '-- ★★ 懒构建 + 分帧预热（2026-10-03，实机「打开界面整窗变灰」）' + NL +
    '--   实测：首屏 U:Build() 原本无条件同步构建全部 6 个页面共 1673 帧' + NL +
    '--   （不含纹理/字体串）→ 阻塞主线程。' + NL +
    '--   现在：U:Build() 只建「当前子页」；其余页由 U:EnsureBuilt 在首次切到时同步建，' + NL +
    '--         并由 U:SchedulePrebuild 在随后空闲帧里逐页补建 → 切页依然零等待。' + NL +
    '--   幂等：各模块自带 built 闸；U.subBuilt 记录已触发过的页。' + NL +
    '-- ══════════════════════════════════════════════════════════════════════' + NL +
    'function U:EnsureBuilt(k)' + NL +
    '    if k == "Dungeons" then' + NL +
    '        DG.BuildDungeons()          -- 副本页原本就懒建（U.dungeonBuilt 幂等）' + NL +
    '        return' + NL +
    '    end' + NL +
    '    if not U.subBuilt then U.subBuilt = {} end' + NL +
    '    if U.subBuilt[k] then return end' + NL +
    '    if k == "Raids" and ns.RaidModule and U.raidPage then' + NL +
    '        U.subBuilt[k] = true' + NL +
    '        ns.RaidModule.Build(U.raidPage)' + NL +
    '    elseif k == "Professions" and ns.ProfModule and U.profPage then' + NL +
    '        U.subBuilt[k] = true' + NL +
    '        ns.ProfModule.Build(U.profPage)' + NL +
    '    elseif k == "Explore" and ns.ExploreModule and U.explorePage then' + NL +
    '        U.subBuilt[k] = true' + NL +
    '        ns.ExploreModule.Build(U.explorePage)' + NL +
    '    elseif k == "Bis" and ns.BisModule and U.bisPage then' + NL +
    '        U.subBuilt[k] = true' + NL +
    '        ns.BisModule.Build(U.bisPage)' + NL +
    '    elseif k == "Tier" and ns.TierModule and U.tierPage then' + NL +
    '        U.subBuilt[k] = true' + NL +
    '        ns.TierModule.Build(U.tierPage)' + NL +
    '    end' + NL +
    'end' + NL +
    '' + NL +
    '-- ★ 分帧预热：首屏只需付「当前子页」的建帧成本；其余页在随后的空闲帧里逐页补建。' + NL +
    '--   切页因此仍是「零等待」，而打开动作不再被 6 页的建帧量一次性阻塞。' + NL +
    '--   C_Timer 不可用时直接返回，退化为「首次切到时同步建」（U:EnsureBuilt 兜底）。' + NL +
    'function U:SchedulePrebuild()' + NL +
    '    if U.prebuildOn then return end' + NL +
    '    if type(C_Timer) ~= "table" or type(C_Timer.After) ~= "function" then return end' + NL +
    '    U.prebuildOn = true' + NL +
    '    local order = { "Raids" }' + NL +
    '    if ns.LoadForeverPages then' + NL +
    '        order[#order + 1] = "Professions"' + NL +
    '        order[#order + 1] = "Explore"' + NL +
    '        order[#order + 1] = "Bis"' + NL +
    '        order[#order + 1] = "Tier"' + NL +
    '    end' + NL +
    '    local i = 0' + NL +
    '    local function step()' + NL +
    '        local frame = ns.TalentSimFrame' + NL +
    '        if not frame or not frame:IsShown() then' + NL +
    '            U.prebuildOn = false            -- 界面已关：停止预热，下次开窗重启排程' + NL +
    '            return' + NL +
    '        end' + NL +
    '        i = i + 1' + NL +
    '        local k = order[i]' + NL +
    '        if not k then U.prebuildOn = false return end' + NL +
    '        if k ~= U.curSub then U:EnsureBuilt(k) end' + NL +
    '        if order[i + 1] then' + NL +
    '            C_Timer.After(0.05, step)' + NL +
    '        else' + NL +
    '            U.prebuildOn = false' + NL +
    '        end' + NL +
    '    end' + NL +
    '    C_Timer.After(0.6, step)' + NL +
    'end' + NL +
    '' + NL
)
rep('function U:SwitchSub(key)' + NL, LAZY + 'function U:SwitchSub(key)' + NL, 'insert EnsureBuilt+SchedulePrebuild')

# ── ④ SwitchSub：切页前确保该页已建 ──
rep(
    '    if isDun then' + NL,
    '    if isRaid then' + NL +
    '        U:EnsureBuilt("Raids")' + NL +
    '    elseif isDun then' + NL,
    'SwitchSub +Raids branch')

rep(
    '    elseif isProf and ns.ProfModule then' + NL + '        ns.ProfModule.Open()' + NL,
    '    elseif isProf and ns.ProfModule then' + NL +
    '        U:EnsureBuilt("Professions")' + NL +
    '        ns.ProfModule.Open()' + NL,
    'SwitchSub +EnsureBuilt(Professions)')

rep(
    '    elseif isExpl and ns.ExploreModule then' + NL + '        ns.ExploreModule.Open()' + NL,
    '    elseif isExpl and ns.ExploreModule then' + NL +
    '        U:EnsureBuilt("Explore")' + NL +
    '        ns.ExploreModule.Open()' + NL,
    'SwitchSub +EnsureBuilt(Explore)')

rep(
    '    elseif isBis and ns.BisModule then' + NL + '        ns.BisModule.Open()' + NL,
    '    elseif isBis and ns.BisModule then' + NL +
    '        U:EnsureBuilt("Bis")' + NL +
    '        ns.BisModule.Open()' + NL,
    'SwitchSub +EnsureBuilt(Bis)')

rep(
    '    elseif isTier and ns.TierModule then' + NL + '        ns.TierModule.Refresh()' + NL,
    '    elseif isTier and ns.TierModule then' + NL +
    '        U:EnsureBuilt("Tier")' + NL +
    '        ns.TierModule.Refresh()' + NL,
    'SwitchSub +EnsureBuilt(Tier)')

# ── ⑤ OnShow：开窗后分帧补建其余页 ──
rep(
    '        U:UpdateActiveSub()' + NL + '    end)' + NL,
    '        U:UpdateActiveSub()' + NL +
    '        -- ★ 懒构建：其余子页在随后空闲帧里逐页补建（首屏只建了当前页）' + NL +
    '        U:SchedulePrebuild()' + NL +
    '    end)' + NL,
    'OnShow +SchedulePrebuild')

# ── 写回 ──
if s == before:
    print('!! 无改动'); sys.exit(1)
io.open(P, 'w', encoding='utf-8', newline='').write(s)
b = open(P, 'rb').read()
print('---')
print('CRLF %d / LF-only %d' % (b.count(b'\r\n'), b.count(b'\n') - b.count(b'\r\n')))
print('写入完成，字节 %d -> %d' % (len(before.encode('utf-8')), len(b)))
