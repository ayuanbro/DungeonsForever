# -*- coding: utf-8 -*-
"""第七刀：整合包悬停卡死（事件风暴 + 整池 ApplyAll）。

病灶链（整合包才卡、单开不卡）：
  1) 整合包其他插件海量请求物品 ⇒ 客户端物品缓存被驱逐（ItemMixin:IsDataEvictable 恒 true）
  2) 悬停 → GameTooltip:SetItemByID（未缓存 ⇒ 真机同步装载）→ GET_ITEM_INFO_RECEIVED
  3) 我们的事件监听对**任何来源**的 itemID 都跑 DG.RefreshItemCards：全池扫 + 整池 LF.ApplyAll
  4) LF.ApplyAll 逐卡 LF.ScanTip = 隐藏 tooltip 一帧几十~几百次 SetItemByID（老病根换触发点）；
     缓存被驱逐的卡 classID 为 nil ⇒ DG.RequestItem ⇒ 到货又触发一轮 ⇒ 级联风暴

修复（都在我们这边）：
  A) OnEvent 头上 O(1) 守卫：只服务 DG.__asked 里记过的物品（本插件请求过的）
  B) DG.RefreshItemCards：整池 LF.ApplyAll → 单件 LF.Invalidate + 只对匹配卡 LF.Apply
     （过滤规则没变时其他卡的判定结果不变，无需重判）
"""
import io, sys

P = 'Core/DungeonUI.lua'
s = io.open(P, encoding='utf-8', newline='').read()
ORIG = s

def rep(old, new, tag):
    global s
    n = s.count(old)
    assert n == 1, '[%s] 锚点命中 %d 次（要 1）' % (tag, n)
    s = s.replace(old, new, 1)
    print('[OK] %s' % tag)

# ---- A) 事件守卫：陌生 itemID 直接忽略 ----
rep(
    '    ev:SetScript("OnEvent", function(_, _, itemID, success)\r\n'
    '        if success == false then return end\r\n'
    '        local r = U.dungeonDetailHover\r\n',

    '    ev:SetScript("OnEvent", function(_, _, itemID, success)\r\n'
    '        if success == false then return end\r\n'
    '        -- ★★ 第七刀（整合包悬停卡死）：GET_ITEM_INFO_RECEIVED 对**任何插件**请求的物品都会触发\r\n'
    '        --   —— 整合包里成百上千条陌生 itemID 事件，每条都走「全池扫 + 整池 ApplyAll」会把弱机按死。\r\n'
    '        --   这里 O(1) 查「是否本插件请过的物品」（DG.RequestItem 会记 DG.__asked），陌生的直接忽略。\r\n'
    '        if not (itemID and DG.__asked[itemID]) then return end\r\n'
    '        local r = U.dungeonDetailHover\r\n',
    'A) OnEvent 守卫')

# ---- B1) RefreshItemCards 头部：先单件失效 ----
rep(
    'function DG.RefreshItemCards(itemID)\r\n'
    '    local pool = U.dungeonDetailPool and U.dungeonDetailPool.item\r\n'
    '    if not pool then return end\r\n'
    '    for i = 1, #pool do\r\n',

    'function DG.RefreshItemCards(itemID)\r\n'
    '    local pool = U.dungeonDetailPool and U.dungeonDetailPool.item\r\n'
    '    if not pool then return end\r\n'
    '    local LF = ns.LootFilter\r\n'
    '    -- ★★ 第七刀（整合包悬停卡死）：整合包里其他插件会把客户端物品缓存挤掉\r\n'
    '    --   （ItemMixin:IsDataEvictable 恒 true）⇒ 悬停 → SetItemByID（未缓存即同步装载）→ 到货 → 这里。\r\n'
    '    --   旧尾巴是「整池 LF.ApplyAll」= 对每张卡做隐藏 tooltip 扫描（LF.ScanTip），\r\n'
    '    --   未缓存条目真机同步装载 ⇒ 悬停一次 = 一帧几百次 SetItemByID = 卡死。\r\n'
    '    --   过滤规则没变时其他卡的判定结果不变 ⇒ 只失效这一件、只重判匹配卡（O(命中)）。\r\n'
    '    if LF then LF.Invalidate(itemID) end\r\n'
    '    for i = 1, #pool do\r\n',
    'B1) RefreshItemCards 头部单件失效')

# ---- B2) 匹配卡重判 ----
rep(
    '            if c.tp then c.tp:SetText(DG.ItemMeta(itemID)) end\r\n'
    '        end\r\n'
    '    end\r\n'
    '    local qpool = U.dungeonQDetPool and U.dungeonQDetPool.chip\r\n',

    '            if c.tp then c.tp:SetText(DG.ItemMeta(itemID)) end\r\n'
    '            if LF then LF.Apply(c) end\r\n'
    '        end\r\n'
    '    end\r\n'
    '    local qpool = U.dungeonQDetPool and U.dungeonQDetPool.chip\r\n',
    'B2) 匹配卡 LF.Apply')

# ---- B3) 摘掉整池 ApplyAll 尾巴 ----
rep(
    '    local LF = ns.LootFilter\r\n'
    '    if LF then LF.Invalidate(itemID); LF.ApplyAll() end\r\n'
    'end\r\n',

    'end\r\n',
    'B3) 摘整池 ApplyAll 尾巴')

assert s.count('\r\n') > 0
bare_lf = s.replace('\r\n', '').count('\n')
assert bare_lf == 0, '出现裸 LF %d 处，中止' % bare_lf

io.open(P, 'w', encoding='utf-8', newline='').write(s)
print('写入完成：%d -> %d 字节，裸 LF = 0' % (len(ORIG.encode('utf-8')), len(s.encode('utf-8'))))
