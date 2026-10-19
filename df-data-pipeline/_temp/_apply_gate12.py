# -*- coding: utf-8 -*-
"""第八刀：TinyInspect 提示框皮肤冲突 + ScanTip 加固（采纳外部修复的两处真改进）。

A) TinyInspect 冲突（用户实机：开 TinyInspect 后，本插件里看装备的提示框被错套主题皮肤）
   机制：TinyInspect 的 ItemLevelTooltip 在 OnShow 后**下一帧** ClearLines 整段重加行
   （插入「装备等级」行）再 Show —— 这次重建会清掉客户端 tooltip 的物品内容态；
   我们 OnShow 皮肤判定 `TooltipHasItemContent`（ttItemMark + GetItem）双双落空
   ⇒ 把装备提示框误判成「非物品提示」⇒ 套上主题皮肤。
   修复：ShowItemTip 原生分支显式 `MarkTipItem(GameTooltip, true)` —— 标记是本插件
   自己的表，ClearLines 重建清不掉 ⇒ 装备提示框始终不套主题。

B) 采纳外部修复（Downloads/LootFilter.lua）中两处真改进进 ScanTip：
   1) 数据没到不扫也不缓存：扫了必为空，还会从扫描路径触发同步装载
      （整合包里物品缓存被挤掉 ⇒ 扫描口就是另一条「一帧几百次 SetItemByID」风暴道）；
   2) 失败不留 "" 占位（原先预写 `tipCache[id] = ""` 会把失败结果永久缓存住）；
   3) __scanDepth 重入保护（隐藏 tooltip 的 SetItemByID 在钩子横行环境可能同步转回来）。
   不采纳（有回归风险）：删 ContinueOnItemLoad、删悬停重呼、0.3s 防抖（快速划过不出框）、
   RequestItem 去 force（缓存驱逐后名字永久停在占位）、Invalidate 不再清 tipCache。
"""
import io

# ---- A) DungeonUI.lua（CRLF）----
P1 = 'Core/DungeonUI.lua'
s = io.open(P1, encoding='utf-8', newline='').read()
ORIG1 = s

OLD1 = ('    if native then\r\n'
        '        GameTooltip:Show()\r\n'
        '        return\r\n'
        '    end\r\n')
NEW1 = ('    if native then\r\n'
        '        -- ★★ TinyInspect 兼容（2026-10-03 用户实机）：它给物品提示框插「装备等级」行时，\r\n'
        '        --   是下一帧 ClearLines 整段重加行再 Show —— 那次重建会清掉客户端的物品内容态，\r\n'
        '        --   我们的 OnShow 皮肤判定（ttItemMark + GetItem）双双落空 ⇒ 装备提示框被错套主题。\r\n'
        '        --   这里显式打物品标记（标记是本插件的表，重建清不掉）⇒ 装备提示框始终不套主题。\r\n'
        '        if ns.hui and ns.hui.MarkTipItem then ns.hui.MarkTipItem(GameTooltip, true) end\r\n'
        '        GameTooltip:Show()\r\n'
        '        return\r\n'
        '    end\r\n')
assert s.count(OLD1) == 1, 'A 锚点命中 %d 次' % s.count(OLD1)
s = s.replace(OLD1, NEW1, 1)
bare = s.replace('\r\n', '').count('\n')
assert bare == 0, 'DungeonUI 出现裸 LF %d' % bare
io.open(P1, 'w', encoding='utf-8', newline='').write(s)
print('[OK] A) DungeonUI.lua 原生分支打物品标记（%d -> %d 字节）'
      % (len(ORIG1.encode('utf-8')), len(s.encode('utf-8'))))

# ---- B) LootFilter.lua（LF）----
P2 = 'Core/LootFilter.lua'
t = io.open(P2, encoding='utf-8', newline='').read()
ORIG2 = t

i = t.find('function LF.ScanTip(itemID)')
j = t.find('function LF.Invalidate', i)
assert i != -1 and j != -1, 'ScanTip 区块定位失败'
OLD_FN = t[i:j]

NEW_FN = '''function LF.ScanTip(itemID)
    if not itemID then return "" end
    local cached = LF.tipCache[itemID]
    if cached ~= nil then return cached end

    -- ★★ 数据没到就不扫也不缓存（2026-10-03 整合包悬停风暴）：扫了必为空，还会从
    --    扫描路径触发同步装载；数据到了事件链自然会重扫。失败也不留 "" 占位
    --    （原先的预写会把失败结果永久缓存住）。
    local DGM = ns.DungeonModule
    if not (DGM and DGM.ItemInfo and DGM.ItemInfo(itemID)) then return "" end

    -- ★ 重入保护：隐藏 tooltip 的 SetItemByID 在钩子横行的环境里可能同步转一圈回来
    --   （别的插件钩了 tooltip 数据口），扫到一半再扫 = 栈上叠无限层。
    if (LF.__scanDepth or 0) > 0 then return "" end

    local tip = LF.EnsureScanTip()
    if not tip then return "" end

    LF.__scanDepth = (LF.__scanDepth or 0) + 1
    local okScan, res = pcall(function()
        if tip.SetOwner and not pcall(tip.SetOwner, tip, UIParent, "ANCHOR_NONE") then return nil end
        local set = false
        if tip.SetItemByID then set = pcall(tip.SetItemByID, tip, itemID) end
        if not set and tip.SetHyperlink then set = pcall(tip.SetHyperlink, tip, "item:" .. tostring(itemID)) end
        if not set then return nil end

        pcall(tip.Show, tip)
        local n = (tip.NumLines and tip:NumLines()) or 0
        if type(n) ~= "number" or n <= 0 then return "" end

        local parts = {}
        for i = 2, n do
            local fs = _G["TFItemScanTipTextLeft" .. i]
            if fs and fs.GetText then
                local t = fs:GetText()
                if type(t) == "string" and t ~= "" and not IsExcludedLine(t) then
                    parts[#parts + 1] = t
                end
            end
        end
        return table.concat(parts, "|")
    end)
    pcall(tip.Hide, tip)
    LF.__scanDepth = LF.__scanDepth - 1

    if not okScan or res == nil then return "" end   -- 失败不缓存
    LF.tipCache[itemID] = res
    return res
end

'''
t = t[:i] + NEW_FN + t[j:]
assert '\r\n' not in t, 'LootFilter 不该有 CRLF'
io.open(P2, 'w', encoding='utf-8', newline='').write(t)
print('[OK] B) LootFilter.lua ScanTip 加固（%d -> %d 字节）'
      % (len(ORIG2.encode('utf-8')), len(t.encode('utf-8'))))
