# -*- coding: utf-8 -*-
"""第九刀：Auctionator 共存炸栈（用户实机：287x C stack overflow）。

实机堆栈（用户贴的错误日志）：
    ShowItemTip:2243（SetOwner）… ShowItemTip:2248（pcall SetItemByID）
      → TooltipDataHandler → Auctionator Hooks:327→335→306 ShowTipWithPricing
      → DBKeyFromLink:49 → ContinueOnItemLoad（Item.lua:332 → AsyncCallbackSystem:52 AddCallback）
      → 物品数据已就绪 ⇒ **同步**派发回调 → 我们的到货处理（DungeonUI.lua:2092，行还悬着）
      → 再调 DG.ShowItemTip → 再 GameTooltip:SetItemByID ⇒ 无限同步递归
    287 层后 C stack overflow；pcall 把错误吞了以后又落进 SetHyperlink 分支再扫一轮
    （另 49x NineSlice 报错是对比提示框在同一风暴里炸）。

机制：Auctionator 给 GameTooltip 挂了钩子，我们 GameTooltip:SetItemByID 的调用链
会同步转回我们自己的 ShowItemTip —— 数据刚就绪时，正在显示的这一遍 SetItemByID
本来就会成功，再入的那一遍是纯冗余。
对策：ShowItemTip 套一层 O(1) 重入守卫（__tipBusy），重入即忽略；
本体改名 ShowItemTipBody，pcall 包住保证 flag 无论成败都复位（错误原样上抛）。
"""
import io

P1 = 'Core/DungeonUI.lua'
s = io.open(P1, encoding='utf-8', newline='').read()
ORIG1 = s

OLD1 = ('function DG.ShowItemTip(owner, it)\r\n'
        '    local id = it[1]\r\n')
NEW1 = ('function DG.ShowItemTip(owner, it)\r\n'
        '    -- ★★ 第九刀（Auctionator 共存炸栈，2026-10-03 用户实机 287x C stack overflow）：\r\n'
        '    --   实机堆栈：ShowItemTip → GameTooltip:SetItemByID →（Auctionator 挂在 GameTooltip\r\n'
        '    --   上的钩子 → ShowTipWithPricing → DBKeyFromLink → ContinueOnItemLoad：物品数据\r\n'
        '    --   已就绪时 AsyncCallbackSystem **同步**派发回调）→ 我们的到货处理（行还悬着）\r\n'
        '    --   再调 ShowItemTip → 再 SetItemByID ⇒ 无限同步递归直到 C stack overflow。\r\n'
        '    --   对策：重入即忽略 —— 正在显示的这一遍，数据刚就绪 SetItemByID 必然成功，\r\n'
        '    --   再入的那遍是纯冗余。pcall 包住本体保证 flag 无论成败都复位（错误原样上抛）。\r\n'
        '    if DG.__tipBusy then return end\r\n'
        '    DG.__tipBusy = true\r\n'
        '    local ok, err = pcall(DG.ShowItemTipBody, owner, it)\r\n'
        '    DG.__tipBusy = nil\r\n'
        '    if not ok then error(err, 0) end\r\n'
        'end\r\n'
        '\r\n'
        'function DG.ShowItemTipBody(owner, it)\r\n'
        '    local id = it[1]\r\n')
assert s.count(OLD1) == 1, '锚点命中 %d 次' % s.count(OLD1)
s = s.replace(OLD1, NEW1, 1)
bare = s.replace('\r\n', '').count('\n')
assert bare == 0, 'DungeonUI 出现裸 LF %d' % bare
io.open(P1, 'w', encoding='utf-8', newline='').write(s)
print('[OK] DungeonUI.lua ShowItemTip 重入守卫（%d -> %d 字节）'
      % (len(ORIG1.encode('utf-8')), len(s.encode('utf-8'))))
