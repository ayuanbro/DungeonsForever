# -*- coding: utf-8 -*-
"""第六刀修正：DG.ApplyDetailChrome 只管「按钮组」，容器互斥与掉落筛选栏还给渲染路径。

为什么必须切这一刀（实机/harness 同源）：
    U:RenderDungeonTab 的尾部原本是三件事混在一起：
      ① 页签容器互斥（详情滚动区 / 攻略 / 地图 / 任务 谁显谁隐）
      ② 掉落筛选栏（LFUI:EnsureBar + RefreshBar + Show/Hide，挂在详情页上的常驻件）
      ③ 按钮组补刷（掉落视图按钮显隐、筛选行在攻略/地图下全隐、页签选中态描边）
    第六刀把①②③整段搬进了 DG.ApplyDetailChrome —— 于是**外壳分片那几块**
    在「详情渲染已经跑过、管线还在排」的窗口里又跑了一遍①②，问题就来了：
      · 分帧期间玩家切页签 → 分片补刷拿到的是**当时的**页签，会去 SetShown 别的容器；
        harness 里就是「渲染时把 U.dungeonTab 设成 map → 渲染完恢复 loot → 再抽干管线」
        ⇒ 分片补刷按 loot 把**地图容器藏掉** ⇒ MapUI ⑤收尾的 `if frame:IsShown()`
        不成立 ⇒ 右栏永远不亮（两个断言红）。
      · ② 被提前到分片帧执行 ⇒ 掉落筛选栏那 9 个帧跑到别的帧里去了，
        「首次进入掉落页 = 13 行 + 9 图标行」的帧数账对不上。
    ⇒ ①② 本质是**渲染分派**的职责（谁被渲染、谁就该显），只有③是「按钮壳」的职责。
      所以 ①② 留在 U:RenderDungeonTab 尾部，DG.ApplyDetailChrome 只保留 ③。

只改 Core/DungeonUI.lua；行尾 CRLF 守恒。
"""
import io
import os

ROOT = r'D:\workspace\DungeonsForever'
P = os.path.join(ROOT, 'Core', 'DungeonUI.lua')

b = io.open(P, 'rb').read()
assert b.count(b'\n') - b.count(b'\r\n') == 0
s = b.decode('utf-8').replace('\r\n', '\n')


def rep(old, new, tag, n=1):
    global s
    c = s.count(old)
    assert c == n, '%s：锚点命中 %d 次（期望 %d）\n%r' % (tag, c, n, old[:160])
    s = s.replace(old, new, n)


CONT = '''    if U.dungeonDetailScroll then U.dungeonDetailScroll:SetShown(not isQuest and not isGuide and not isMap) end
    if U.dungeonGuideScroll then U.dungeonGuideScroll:SetShown(isGuide) end
    if U.dungeonMapFrame then U.dungeonMapFrame:SetShown(isMap) end
    if U.dungeonQuestScroll then U.dungeonQuestScroll:SetShown(isQuest) end
    if U.dungeonQDet then U.dungeonQDet:SetShown(isQuest) end
    if U.dungeonQPlateL then U.dungeonQPlateL:SetShown(isQuest) end
    if U.dungeonQPlateR then U.dungeonQPlateR:SetShown(isQuest) end
'''

LFUI = '''    do
        local LFUI = ns.LootFilterUI
        if cur == "loot" then
            if LFUI then LFUI:EnsureBar(); LFUI:RefreshBar() end
            if U.lootFilterBar then U.lootFilterBar:Show() end
        else
            if U.lootFilterBar then U.lootFilterBar:Hide() end
        end
    end
'''

# ── 1) 从 DG.ApplyDetailChrome 里摘掉 CONT + LFUI ──
OLD_HEAD = ('function DG.ApplyDetailChrome(cur)\n'
            '    cur = cur or U.dungeonTab or "loot"\n'
            '    local isQuest = (cur == "quest")\n'
            '    local isGuide = (cur == "guide")\n'
            '    local isMap   = (cur == "map")\n'
            + CONT + LFUI +
            '    -- ★ 显示方式切换只在「掉落」页签出现（其余页签这一行是别的语义，按钮位置也不同）\n'
            '    if #(U.dungeonLootViewBtns or {}) > 0 then\n')

NEW_HEAD = ('-- 详情页外壳的「按钮组」补刷：掉落视图按钮显隐 / 筛选行在攻略·地图下全隐 /\n'
            '--   页签与视图按钮的选中态描边。\n'
            '--   ★ 只管**按钮壳** —— 页签容器互斥（谁渲染谁显）与掉落筛选栏（LFUI:EnsureBar）\n'
            '--     都是**渲染分派**的职责，留在 U:RenderDungeonTab 尾部。第六刀最初的版本把\n'
            '--     它们一起搬进来，结果分片补刷在「渲染已跑、管线还在排」的窗口里又跑了一遍：\n'
            '--     分帧期间切页签时它会去 SetShown **别的**容器，把地图页/任务页藏掉\n'
            '--     （harness 实锤：地图容器被藏 ⇒ MapUI ⑤收尾的 frame:IsShown() 不成立 ⇒\n'
            '--      右栏永远不亮）；掉落筛选栏也被提前到分片帧建，帧数账全乱。\n'
            '--   ⇒ 渲染路径（U:RenderDungeonTab 末尾）与外壳分片**共用这一个按钮补刷口**。\n'
            'function DG.ApplyDetailChrome(cur)\n'
            '    cur = cur or U.dungeonTab or "loot"\n'
            '    local isQuest = (cur == "quest")\n'
            '    local isGuide = (cur == "guide")\n'
            '    local isMap   = (cur == "map")\n'
            '    -- ★ 显示方式切换只在「掉落」页签出现（其余页签这一行是别的语义，按钮位置也不同）\n'
            '    if #(U.dungeonLootViewBtns or {}) > 0 then\n')
rep(OLD_HEAD, NEW_HEAD, 'R1 ApplyDetailChrome 只留按钮壳')

# ── 2) RenderDungeonTab 尾部把 CONT + LFUI 放回去 ──
rep('    DG.ApplyDetailChrome(cur)\nend\n',
    CONT + LFUI + '    DG.ApplyDetailChrome(cur)\nend\n',
    'R3 RenderDungeonTab 收尾补回容器互斥 + 掉落筛选栏')

out = s.replace('\n', '\r\n').encode('utf-8')
assert out.count(b'\n') - out.count(b'\r\n') == 0
io.open(P, 'wb').write(out)
print('OK  %d bytes  CRLF %d  裸LF %d'
      % (len(out), out.count(b'\r\n'), out.count(b'\n') - out.count(b'\r\n')))
