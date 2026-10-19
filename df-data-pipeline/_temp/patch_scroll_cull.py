# -*- coding: utf-8 -*-
"""审计⑤⑥⑧+遮罩抬层：DungeonUI.lua 滚动定式三页同款。CRLF 保真。"""
import sys

P = 'Core/DungeonUI.lua'
d = open(P, 'rb').read()

def rep(old, new, tag):
    global d
    o = old.replace('\n', '\r\n').encode('utf-8')
    n = new.replace('\n', '\r\n').encode('utf-8')
    if d.count(o) != 1:
        print('[MISS] %s (count=%d)' % (tag, d.count(o)))
        sys.exit(1)
    d = d.replace(o, n)
    print('[OK] %s' % tag)

NEWFUNCS = '''
function DG.DetailTopMask(topY)
    local detail = U.dungeonDetail
    local base = U.dungeonDetailBase
    if not (detail and base) then return end
    if not (IsHui() and ns.hui and ns.hui.layer and ns.hui.layer.L0) then return end
    local L0 = ns.hui.layer.L0
    local mask = CreateFrame("Frame", nil, detail)
    mask:SetFrameLevel(base + 2)
    mask:SetPoint("TOPLEFT", detail, "TOPLEFT", 0, 8)
    mask:SetPoint("TOPRIGHT", detail, "TOPRIGHT", 0, 8)
    mask:SetPoint("BOTTOMLEFT", detail, "TOPLEFT", 0, -topY)
    mask:SetPoint("BOTTOMRIGHT", detail, "TOPRIGHT", 0, -topY)
    local tex = mask:CreateTexture(nil, "OVERLAY")
    tex:SetAllPoints()
    tex:SetTexture("Interface\\\\Buttons\\\\WHITE8x8")
    tex:SetVertexColor(L0[1], L0[2], L0[3], L0[4] or 1)
    mask:Hide()
    return mask
end

function DG.RaiseDetailChrome()
    local base = U.dungeonDetailBase
    if not base then return end
    local lv = base + 3
    if U.dungeonDetailHero then U.dungeonDetailHero:SetFrameLevel(lv) end
    if U.dungeonBack then U.dungeonBack:SetFrameLevel(lv) end
    if U.dungeonDetailTipZone then U.dungeonDetailTipZone:SetFrameLevel(lv) end
    for _, bt in pairs(U.dungeonTabBtns or {}) do bt:SetFrameLevel(lv) end
    for _, chip in ipairs(U.dungeonEntChips or {}) do chip:SetFrameLevel(lv) end
    for _, bt in ipairs(U.dungeonFilterBtns or {}) do bt:SetFrameLevel(lv) end
    if U.dungeonLootBossDd then U.dungeonLootBossDd:SetFrameLevel(lv) end
    for _, bt in ipairs(U.dungeonLootViewBtns or {}) do bt:SetFrameLevel(lv) end
    if U.lootFilterBar then U.lootFilterBar:SetFrameLevel(lv) end
end

local function VScrollBounds(sc)
    local gt = sc.GetTop and sc:GetTop()
    if type(gt) ~= "number" then return nil end
    local viewH = sc.GetHeight and sc:GetHeight()
    if type(viewH) ~= "number" then return nil end
    local v = sc.GetVerticalScroll and sc:GetVerticalScroll() or 0
    if type(v) ~= "number" then v = 0 end
    return v - 2, v + viewH + 2
end

local function CullVItems(sc, items, defH)
    local vTop, vBot = VScrollBounds(sc)
    if not vTop then return end
    for _, el in ipairs(items) do
        if el.__vgen == DG.__vgen and type(el.__vtop) == "number" then
            if (el.__vtop + (el.__vh or defH)) > vTop and el.__vtop < vBot then
                el:Show()
            else
                el:Hide()
            end
        end
    end
end

function DG.CullQuestRows()
    local sc, pool = U.dungeonQuestScroll, U.dungeonQuestPool
    if not (sc and pool and sc.IsShown and sc:IsShown()) then return end
    CullVItems(sc, pool.row, DG.Q_ROW_H)
    local vTop, vBot = VScrollBounds(sc)
    if not vTop then return end
    for _, hd in ipairs(pool.hdr) do
        if hd.__vgen == DG.__vgen and type(hd.__vtop) == "number" then
            local vis = (hd.__vtop + (hd.__vh or DG.Q_HDR_H)) > vTop and hd.__vtop < vBot
            if vis then hd.name:Show() hd.cnt:Show() else hd.name:Hide() hd.cnt:Hide() end
        end
    end
end

function DG.CullGuideCards()
    local sc, pool = U.dungeonGuideScroll, U.dungeonGuidePool
    if not (sc and pool and sc.IsShown and sc:IsShown()) then return end
    CullVItems(sc, pool.card, 100)
end

function DG.CullLootCards()
    local sc, pool = U.dungeonDetailScroll, U.dungeonDetailPool
    if not (sc and pool and sc.IsShown and sc:IsShown()) then return end
    CullVItems(sc, pool.card, DG.LOOT_CARD_MIN_H)
    CullVItems(sc, pool.item, DG.LOOT_CARD_H)
    local vTop, vBot = VScrollBounds(sc)
    if not vTop then return end
    for _, hd in ipairs(pool.hdr or {}) do
        if hd.__vgen == DG.__vgen and type(hd.__vtop) == "number" then
            local vis = (hd.__vtop + (hd.__vh or DG.LOOT_HDR_H)) > vTop and hd.__vtop < vBot
            if vis then hd.name:Show() hd.cnt:Show() else hd.name:Hide() hd.cnt:Hide() end
        end
    end
end
'''

rep('''function DG.WheelScroll(scroll, child, delta)
    if not (scroll and child) then return end
    local maxScroll = math.max(0, child:GetHeight() - scroll:GetHeight())
    scroll:SetVerticalScroll(math.max(0, math.min(maxScroll, scroll:GetVerticalScroll() - delta * 48)))
end''',
'''function DG.WheelScroll(scroll, child, delta)
    if not (scroll and child) then return end
    local maxScroll = math.max(0, child:GetHeight() - scroll:GetHeight())
    scroll:SetVerticalScroll(math.max(0, math.min(maxScroll, scroll:GetVerticalScroll() - delta * 48)))
    if scroll == U.dungeonQuestScroll then DG.CullQuestRows()
    elseif scroll == U.dungeonGuideScroll then DG.CullGuideCards()
    elseif scroll == U.dungeonDetailScroll then DG.CullLootCards() end
end''', 'B1 WheelScroll 分派')

rep('''function DG.ListFadesVisible(vis)
    local fades = U.dungeonListFades
    if not fades then return end
    for _, f in ipairs(fades) do
        if vis then f:Show() else f:Hide() end
    end
end
''', '''function DG.ListFadesVisible(vis)
    local fades = U.dungeonListFades
    if not fades then return end
    for _, f in ipairs(fades) do
        if vis then f:Show() else f:Hide() end
    end
end
''' + NEWFUNCS, 'B2 新增遮罩/抬层/剔除函数')

rep('''    U.dungeonDetailHero = hero

    local back = NewButton(detail, L["‹ 副本"], 70, 24, 14)''',
'''    U.dungeonDetailHero = hero
    U.dungeonDetailBase = hero:GetFrameLevel()

    local back = NewButton(detail, L["‹ 副本"], 70, 24, 14)''', 'B3 base 捕获')

rep('    dscroll:SetFrameLevel(hero:GetFrameLevel() + 1)',
    '    dscroll:SetFrameLevel(U.dungeonDetailBase + 1)', 'B4 dscroll 层级')

rep('''    U.dungeonDetailPool = { hdr = {}, item = {} }
    U.dungeonDetailNote = MakeFS(dchild, 14, C_GREY, "LEFT")''',
'''    U.dungeonDetailPool = { hdr = {}, item = {} }
    U.dungeonDetailNote = MakeFS(dchild, 14, C_GREY, "LEFT")
    dscroll:HookScript("OnShow", function() DG.CullLootCards() end)
    U.dungeonLMask = DG.DetailTopMask(DG.SCROLL_Y)
    DG.RaiseDetailChrome()''', 'B5 掉落遮罩+钩子')

rep('    qscroll:SetFrameLevel(U.dungeonDetailHero:GetFrameLevel() + 1)',
    '    qscroll:SetFrameLevel(U.dungeonDetailBase + 1)', 'B6 qscroll 层级')
rep('    qdet:SetFrameLevel(U.dungeonDetailHero:GetFrameLevel() + 1)',
    '    qdet:SetFrameLevel(U.dungeonDetailBase + 1)', 'B7 qdet 层级')

rep('    U.dungeonQuestPool = { hdr = {}, row = {} }',
'''    U.dungeonQuestPool = { hdr = {}, row = {} }
    U.dungeonQMask = DG.DetailTopMask(DG.FILTER_Y)
    DG.RaiseDetailChrome()''', 'B8 任务遮罩')

rep('''    qscroll:Hide()
    U.dungeonQuestScroll = qscroll''',
'''    qscroll:Hide()
    qscroll:HookScript("OnShow", function() DG.CullQuestRows() end)
    U.dungeonQuestScroll = qscroll''', 'B9 qscroll 钩子')

rep('''    qdet:Hide()
    U.dungeonQDet = qdet''',
'''    qdet:Hide()
    qdet:HookScript("OnShow", function() DG.CullQuestRows() end)
    U.dungeonQDet = qdet''', 'B10 qdet 钩子')

rep('    gscroll:SetFrameLevel(U.dungeonDetailHero:GetFrameLevel() + 1)',
    '    gscroll:SetFrameLevel(U.dungeonDetailBase + 1)', 'B11 gscroll 层级')

rep('    U.dungeonGuidePool = { card = {} }',
'''    U.dungeonGuidePool = { card = {} }
    U.dungeonGMask = DG.DetailTopMask(DG.GUIDE_TOP_Y)
    DG.RaiseDetailChrome()''', 'B12 攻略遮罩')

rep('''    gscroll:Hide()
    U.dungeonGuideScroll = gscroll''',
'''    gscroll:Hide()
    gscroll:HookScript("OnShow", function() DG.CullGuideCards() end)
    U.dungeonGuideScroll = gscroll''', 'B13 gscroll 钩子')

rep('''    local hdr, rows = pool.hdr, pool.row
    local nH, nR, y = 0, 0, -DG.Q_HEAD_H''',
'''    DG.__vgen = (DG.__vgen or 0) + 1
    local hdr, rows = pool.hdr, pool.row
    local nH, nR, y = 0, 0, -DG.Q_HEAD_H''', 'B14 任务渲染代')

rep('''            hd.name:SetText(g.inside and L["副本内领取 / 交付"] or L["进本前先去接"])
            hd.name:ClearAllPoints()
            hd.name:SetPoint("TOPLEFT", child, "TOPLEFT", DG.Q_PAD, y)
            hd.name:Show()''',
'''            hd.name:SetText(g.inside and L["副本内领取 / 交付"] or L["进本前先去接"])
            hd.name:ClearAllPoints()
            hd.name:SetPoint("TOPLEFT", child, "TOPLEFT", DG.Q_PAD, y)
            hd.__vtop, hd.__vh, hd.__vgen = -y, DG.Q_HDR_H, DG.__vgen
            hd.name:Show()''', 'B15 任务组头登记')

rep('''                r:ClearAllPoints()
                r:SetPoint("TOPLEFT", child, "TOPLEFT", DG.Q_PAD, y - (i - 1) * (DG.Q_ROW_H + DG.Q_GAP_Y))
                r:Show()''',
'''                r:ClearAllPoints()
                r:SetPoint("TOPLEFT", child, "TOPLEFT", DG.Q_PAD, y - (i - 1) * (DG.Q_ROW_H + DG.Q_GAP_Y))
                r.__vtop, r.__vh, r.__vgen = -(y - (i - 1) * (DG.Q_ROW_H + DG.Q_GAP_Y)), DG.Q_ROW_H, DG.__vgen
                r:Show()''', 'B16 任务行登记')

rep('''    child:SetHeight(math.max(10, -y + 12))
    U.dungeonQuestScroll:SetVerticalScroll(0)
    U:RenderQuestDetail()''',
'''    child:SetHeight(math.max(10, -y + 12))
    U.dungeonQuestScroll:SetVerticalScroll(0)
    DG.CullQuestRows()
    U:RenderQuestDetail()''', 'B17 任务收尾剔除')

rep('''    local cards = pool.card
    local nC = 0''',
'''    local cards = pool.card
    local nC = 0
    DG.__vgen = (DG.__vgen or 0) + 1''', 'B18 攻略渲染代')

rep('''        a.frame:ClearAllPoints()
        a.frame:SetPoint("TOPLEFT", child, "TOPLEFT", DG.GUIDE_SIDE, top)
        a.frame:SetSize(DG.GUIDE_CARD_W, rh)''',
'''        a.frame:ClearAllPoints()
        a.frame:SetPoint("TOPLEFT", child, "TOPLEFT", DG.GUIDE_SIDE, top)
        a.frame:SetSize(DG.GUIDE_CARD_W, rh)
        a.frame.__vtop, a.frame.__vh, a.frame.__vgen = -top, rh, DG.__vgen''', 'B19a 攻略卡登记a')

rep('''            b.frame:ClearAllPoints()
            b.frame:SetPoint("TOPLEFT", child, "TOPLEFT", DG.GUIDE_SIDE + DG.GUIDE_CARD_W + DG.GUIDE_GAP_X, top)
            b.frame:SetSize(DG.GUIDE_CARD_W, rh)''',
'''            b.frame:ClearAllPoints()
            b.frame:SetPoint("TOPLEFT", child, "TOPLEFT", DG.GUIDE_SIDE + DG.GUIDE_CARD_W + DG.GUIDE_GAP_X, top)
            b.frame:SetSize(DG.GUIDE_CARD_W, rh)
            b.frame.__vtop, b.frame.__vh, b.frame.__vgen = -top, rh, DG.__vgen''', 'B19b 攻略卡登记b')

rep('''    for i = nC + 1, #cards do cards[i]:Hide() end
    child:SetHeight(math.max(10, -top - DG.GUIDE_GAP_Y + DG.GUIDE_PAD))
    U.dungeonGuideScroll:SetVerticalScroll(0)
end''',
'''    for i = nC + 1, #cards do cards[i]:Hide() end
    child:SetHeight(math.max(10, -top - DG.GUIDE_GAP_Y + DG.GUIDE_PAD))
    U.dungeonGuideScroll:SetVerticalScroll(0)
    DG.CullGuideCards()
end''', 'B20 攻略收尾剔除')

rep('    if not DG.__chromeOnly then DG.__pendRows = {} end',
    '    if not DG.__chromeOnly then DG.__pendRows = {} DG.__vgen = (DG.__vgen or 0) + 1 end',
    'B21 掉落渲染代')

rep('''            hd.name:SetText(s[2] .. (en ~= "" and ("  " .. DG.Hex(C_GREY) .. en .. "|r") or ""))
            hd.name:ClearAllPoints()
            hd.name:SetPoint("TOPLEFT", child, "TOPLEFT", 0, y)
            hd.name:Show()''',
'''            hd.name:SetText(s[2] .. (en ~= "" and ("  " .. DG.Hex(C_GREY) .. en .. "|r") or ""))
            hd.name:ClearAllPoints()
            hd.name:SetPoint("TOPLEFT", child, "TOPLEFT", 0, y)
            hd.__vtop, hd.__vh, hd.__vgen = -y, DG.LOOT_HDR_H, DG.__vgen
            hd.name:Show()''', 'B22 掉落组头登记')

rep('''                    r:ClearAllPoints()
                    r:SetPoint("TOPLEFT", child, "TOPLEFT", 0, baseY)
                    r:Show()''',
'''                    r:ClearAllPoints()
                    r:SetPoint("TOPLEFT", child, "TOPLEFT", 0, baseY)
                    r.__vtop, r.__vh, r.__vgen = -baseY, DG.LOOT_CARD_H, DG.__vgen
                    r:Show()''', 'B23 列表空组行登记')

rep('''                    r:ClearAllPoints()
                    r:SetPoint("TOPLEFT", child, "TOPLEFT", rx, ry)
                    r:Show()
                end
                for i, it in ipairs(items) do''',
'''                    r:ClearAllPoints()
                    r:SetPoint("TOPLEFT", child, "TOPLEFT", rx, ry)
                    r.__vtop, r.__vh, r.__vgen = -ry, DG.LOOT_CARD_H, DG.__vgen
                    r:Show()
                end
                for i, it in ipairs(items) do''', 'B24 列表行登记')

rep('''            card:ClearAllPoints()
            card:SetPoint("TOPLEFT", child, "TOPLEFT", cx, cy)
            card:SetSize(cw, h)''',
'''            card:ClearAllPoints()
            card:SetPoint("TOPLEFT", child, "TOPLEFT", cx, cy)
            card:SetSize(cw, h)
            card.__vtop, card.__vh, card.__vgen = -cy, h, DG.__vgen''', 'B25 掉落卡登记')

rep('    DG.FlushPendingRows()          -- ★ 同上：待建行按预算落地',
'''    DG.FlushPendingRows()          -- ★ 同上：待建行按预算落地
    DG.CullLootCards()''', 'B27 卡片路收尾剔除')

rep('    DG.FlushPendingRows()          -- ★ 这一轮排下的待建行：量小同步、量大分帧',
'''    DG.FlushPendingRows()          -- ★ 这一轮排下的待建行：量小同步、量大分帧
    DG.CullLootCards()''', 'B28 列表路收尾剔除')

rep('''    if #list > 0 then
        DG.PushStep(DG.BuildPendRows)
    else
        DG.Gate.Finish()
    end
end''',
'''    if #list > 0 then
        DG.PushStep(DG.BuildPendRows)
    else
        DG.Gate.Finish()
    end
    DG.CullLootCards()
end''', 'B29 异步批收尾剔除')

rep('    if U.dungeonQPlateR then U.dungeonQPlateR:SetShown(isQuest) end',
'''    if U.dungeonQPlateR then U.dungeonQPlateR:SetShown(isQuest) end
    if U.dungeonQMask then U.dungeonQMask:SetShown(isQuest) end
    if U.dungeonGMask then U.dungeonGMask:SetShown(isGuide) end
    if U.dungeonLMask then U.dungeonLMask:SetShown(not isQuest and not isGuide and not isMap) end''',
    'B30 页签切换遮罩显隐')

rep('''function DG.ApplyDetailChrome(cur)
    cur = cur or U.dungeonTab or "loot"''',
'''function DG.ApplyDetailChrome(cur)
    cur = cur or U.dungeonTab or "loot"
    DG.RaiseDetailChrome()''', 'B31 外壳补刷抬层')

rep('''    U.dungeonQuestSel = nil
    U.dungeonQSide = nil
''',
'''    U.dungeonQuestSel = nil
    U.dungeonQSide = nil
    U.dungeonQMask = nil
    U.dungeonGMask = nil
    U.dungeonLMask = nil
    U.dungeonDetailBase = nil
    DG.__vgen = nil
''', 'B32 teardown 清理')

open(P, 'wb').write(d)
c = d.count(b'\r\n')
print('saved CRLF=%d LF-only=%d' % (c, d.count(b'\n') - c))
