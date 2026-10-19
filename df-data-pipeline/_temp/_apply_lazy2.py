# -*- coding: utf-8 -*-
"""
首屏懒建（第 2 刀）：把「详情页全部内容」和「总览页」从 DG.BuildDungeons 拆出，
改成首次进入时才建。

  改前：打开界面 → 建 列表 + 详情页全部池(boss 卡池 29 / 任务 2 栏 / 攻略栏 / 地图页) + 总览 35 条
                    —— 其中详情页 detail:Hide()、总览 oscroll:Hide()，**打开时都不可见**、白建
  改后：打开界面 → 只建 列表 + 两个空壳容器；详情/总览首次进入时建（只付一次）

行尾：DungeonUI.lua 是 CRLF；内部按 LF 处理，写回时还原。
"""
import os, shutil, sys

P = r'D:/workspace/DungeonsForever/Core/DungeonUI.lua'
raw = open(P, 'rb').read()
s = raw.decode('utf-8').replace('\r\n', '\n')
print('原文件 CRLF=%d  LF-only=%d' % (s.count('\r\n'), 0))

def rep(old, new, why):
    global s
    n = s.count(old)
    assert n == 1, '锚点命中 %d 次: %s' % (n, why)
    s = s.replace(old, new, 1)
    print('  ok  ' + why)

# ── 1) 剪出详情页内容块（hero → questPlate 结束）────────────────────
START = '    local hero = CreateFrame("Frame", nil, detail)\n'
ENDMK = '    U.dungeonQPlateR = plateR\n'
i = s.index(START)
j = s.index(ENDMK) + len(ENDMK)
block = s[i:j]
assert 'listW' not in block, 'block 里引用了 listW（BuildDungeons 的 local）'
s = s[:i] + s[j:]
print('  ok  剪出详情页内容块（%d 行）' % block.count('\n'))

# ── 2) 总览：摘掉 BuildDungeonOverview 调用（容器保留）─────────────
rep('    oscroll:Hide()\n    DG.BuildDungeonOverview()\n',
    '    oscroll:Hide()\n'
    '    -- ★ 懒建：总览内容见 DG.EnsureOverviewBuilt()，首屏不再整包建 35 条\n',
    '总览构建调用改懒建')

# ── 3) 插入两个懒建函数（放在 DG.PaintCurrentLevel 之前）──────────
NEW = (
    '-- ══════════════════════════════════════════════════════════════════════════\n'
    '-- ★★★ 懒建：详情页 / 总览页（2026-10-03「打开就卡死」第二刀）\n'
    '--   实测：DG.BuildDungeons() 原本在**首屏**就把详情页整套一次建全\n'
    '--   （boss 卡池 29 张 + 任务两栏 + 攻略栏 + 地图页 + 圆角/遮罩纹理，约 400+ 纹理），\n'
    '--   而 detail 容器是 Hide 的 —— 打开界面时完全不可见，纯属白建；\n'
    '--   总览页同理（35 条等级条，oscroll:Hide()）。\n'
    '--   现在：首屏只建两个空壳容器；内容首次进入时才建（各只付一次）。\n'
    '--   ★ 触发点：详情页 = U:ShowDungeonDetail 开头；总览页 = U:UpdateDungeons 的 overview 分支。\n'
    '-- ══════════════════════════════════════════════════════════════════════════\n'
    'function DG.EnsureDetailBuilt()\n'
    '    if U.detailBuilt then return end\n'
    '    local detail = U.dungeonDetail\n'
    '    local listScroll = U.dungeonListScroll\n'
    '    if not (detail and listScroll) then return end\n'
    '    U.detailBuilt = true\n'
    + block +
    'end\n'
    '\n'
    'function DG.EnsureOverviewBuilt()\n'
    '    if U.overviewBuilt then return end\n'
    '    if not U.dungeonOverviewChild then return end\n'
    '    U.overviewBuilt = true\n'
    '    DG.BuildDungeonOverview()\n'
    'end\n'
    '\n'
)
rep('function DG.PaintCurrentLevel()', NEW + 'function DG.PaintCurrentLevel()',
    '插入 EnsureDetailBuilt / EnsureOverviewBuilt')

# ── 4) 触发点：打开详情页 ────────────────────────────────────────
rep('function U:ShowDungeonDetail(d)\n'
    '    if not U.dungeonBuilt then return end\n'
    '    local detail = U.dungeonDetail\n',
    'function U:ShowDungeonDetail(d)\n'
    '    if not U.dungeonBuilt then return end\n'
    '    DG.EnsureDetailBuilt()          -- ★ 懒建：首次打开详情页时才建那整套\n'
    '    local detail = U.dungeonDetail\n',
    'ShowDungeonDetail 触发详情懒建')

# ── 5) 触发点：切到总览 ──────────────────────────────────────────
rep('    local isOverview = (view == "overview")\n'
    '    if U.dungeonOverviewScroll then U.dungeonOverviewScroll:SetShown(isOverview) end\n',
    '    local isOverview = (view == "overview")\n'
    '    if isOverview then DG.EnsureOverviewBuilt() end   -- ★ 懒建：首次切总览才建 35 条\n'
    '    if U.dungeonOverviewScroll then U.dungeonOverviewScroll:SetShown(isOverview) end\n',
    'UpdateDungeons 触发总览懒建')

# ── 6) U:Build 重置懒建标志 ──────────────────────────────────────
rep('    U.dungeonBuilt = false\n    U.dungeonListChild = nil\n',
    '    U.dungeonBuilt = false\n    U.detailBuilt = nil\n    U.overviewBuilt = nil\n'
    '    U.dungeonListChild = nil\n',
    'U:Build 重置懒建标志')

# ── 7) 更新 boss 卡池那段过时注释 ────────────────────────────────
rep('    --   一个来源一张卡。**在这里一次建全** ⇒ 渲染路径零新建帧（与列表行池同一条纪律）。',
    '    --   一个来源一张卡。**首次打开详情页时一次建全**（懒建）⇒ 渲染路径零新建帧（与列表行池同一条纪律）。',
    '更新 boss 卡池注释')

# ── 写回 ─────────────────────────────────────────────────────────
shutil.copy(P, P + '.bak_lazy2')
open(P, 'wb').write(s.replace('\n', '\r\n').encode('utf-8'))
print('  done 已写回（CRLF 还原）')
