# -*- coding: utf-8 -*-
"""给 Core/DungeonUI.lua 加「攻略」子页签（落在任务/掉落左侧）。

纯文本精确替换；文件为 CRLF，脚本内部转 LF 处理再还原。
每处替换都 assert 唯一命中，否则退出。
"""
import io
import sys

P = 'Core/DungeonUI.lua'
raw = io.open(P, 'rb').read().decode('utf-8')
assert '\r\n' in raw, '期望 CRLF 文件'
src = raw.replace('\r\n', '\n')

def rep(old, new, tag):
    global src
    n = src.count(old)
    if n != 1:
        print('!! [%s] 命中 %d 次（应为 1）' % (tag, n))
        sys.exit(1)
    src = src.replace(old, new)
    print('OK  [%s]' % tag)

# ---------------------------------------------------------------- 1. 页签按钮
rep(
'''    local tabs = { { key = "loot", text = L["掉落"] }, { key = "quest", text = L["任务"] } }''',
'''    local tabs = { { key = "loot", text = L["掉落"] }, { key = "quest", text = L["任务"] }, { key = "guide", text = L["攻略"] } }''',
'tabs 加攻略')

# ------------------------------------------------------- 2. 攻略滚动区（Build 内）
rep(
'''    U.dungeonQDetSt = MakeFS(qdchild, 14, C_GREY, "LEFT")

    local function questPlate()''',
'''    U.dungeonQDetSt = MakeFS(qdchild, 14, C_GREY, "LEFT")

    local gscroll = CreateFrame("ScrollFrame", nil, detail)
    gscroll:SetFrameLevel(hero:GetFrameLevel() + 1)
    gscroll:SetPoint("TOPLEFT", detail, "TOPLEFT", 0, -DG.SCROLL_Y)
    gscroll:SetPoint("BOTTOMRIGHT", detail, "BOTTOMRIGHT", 0, 0)
    local gchild = CreateFrame("Frame", nil, gscroll)
    gchild:SetSize(DG.CHILD_W, 10)
    gscroll:SetScrollChild(gchild)
    gscroll:EnableMouseWheel(true)
    gscroll:SetScript("OnMouseWheel", function(self, delta)
        DG.WheelScroll(self, U.dungeonGuideChild, delta)
    end)
    gscroll:Hide()
    U.dungeonGuideScroll = gscroll
    U.dungeonGuideChild = gchild
    U.dungeonGuidePool = { h = {}, t = {} }

    local function questPlate()''',
'guide 滚动区')

# ------------------------------------------- 3. SetDungeonTab + RenderDungeonTab
GUIDE_FN = '''function DG.GuideBossName(dungeonID, en)
    local loot = (ns.DungeonLoot or {})[dungeonID]
    if loot then
        for i = 1, #loot do
            if loot[i][1] == en then return loot[i][2] or en end
        end
    end
    return en
end

function U:RenderDungeonGuide()
    local d = U.dungeonDetailCur
    local child, pool = U.dungeonGuideChild, U.dungeonGuidePool
    if not (d and child and pool) then return end
    local g = (ns.DungeonGuide or {})[d.id]
    local hs, ts = pool.h, pool.t
    local nH, nT, y = 0, 0, -2

    local function takeH()
        nH = nH + 1
        local f = hs[nH]
        if not f then
            f = MakeFS(child, 16, C_GOLD, "LEFT")
            f:SetWidth(DG.CHILD_W)
            f:SetWordWrap(false)
            hs[nH] = f
        end
        f:Show()
        return f
    end
    local function takeT()
        nT = nT + 1
        local f = ts[nT]
        if not f then
            f = MakeFS(child, 14, C_TEXT, "LEFT")
            f:SetWidth(DG.CHILD_W - 20)
            f:SetWordWrap(true)
            ts[nT] = f
        end
        f:Show()
        return f
    end
    local function putH(text, gap)
        local f = takeH()
        f:SetText(text)
        f:ClearAllPoints()
        f:SetPoint("TOPLEFT", child, "TOPLEFT", 0, y)
        y = y - (gap or 24)
    end
    local function putT(text, color, x, gap)
        local f = takeT()
        f:SetTextColor(Unpack(color or C_TEXT))
        f:SetText(text)
        f:ClearAllPoints()
        f:SetPoint("TOPLEFT", child, "TOPLEFT", x or 0, y)
        y = y - f:GetStringHeight() - (gap or 6)
    end
    local function space(h) y = y - (h or 10) end

    if not g then
        putT(L["这个副本还没有攻略，数据补上后会自动出现。"], C_GREY, 0, 0)
    else
        if g.tagline then putT(g.tagline, C_GREY, 0, 8) end

        if g.tips and #g.tips > 0 then
            putH(L["副本须知"], 24)
            for i = 1, #g.tips do
                putT("· " .. g.tips[i], C_TEXT, 4, 4)
            end
            space(10)
        end

        if g.entrance then
            putH(L["怎么进本"], 24)
            if g.entrance.H then
                putT(L["部落"] .. "：" .. g.entrance.H, C_TEXT, 4, 6)
            end
            if g.entrance.A and #g.entrance.A > 0 then
                putT(L["联盟"] .. "：", C_TEXT, 4, 2)
                for i = 1, #g.entrance.A do
                    putT(i .. ". " .. g.entrance.A[i], C_TEXT, 16, 4)
                end
            end
            space(10)
        end

        if g.bosses and #g.bosses > 0 then
            putH(L["BOSS 打法"], 24)
            for i = 1, #g.bosses do
                local b = g.bosses[i]
                local cn = DG.GuideBossName(d.id, b.en)
                if cn ~= b.en then
                    putT(cn .. "（" .. b.en .. "）", C_GOLD, 4, 3)
                else
                    putT(b.en, C_GOLD, 4, 3)
                end
                putT(b.text, C_TEXT, 4, 8)
            end
            space(6)
        end

        if g.trash and #g.trash > 0 then
            putH(L["小怪应对"], 24)
            for i = 1, #g.trash do
                local t = g.trash[i]
                putT(t.title, C_GOLD, 4, 3)
                putT(t.text, C_TEXT, 4, 8)
            end
            space(6)
        end
    end

    for i = nH + 1, #hs do hs[i]:Hide() end
    for i = nT + 1, #ts do ts[i]:Hide() end
    child:SetHeight(math.max(10, -y + 10))
    U.dungeonGuideScroll:SetVerticalScroll(0)
end

function U:SetDungeonTab(tab)'''

rep(
'''function U:SetDungeonTab(tab)''',
GUIDE_FN,
'RenderDungeonGuide 函数')

rep(
'''    local t = (tab == "quest") and "quest" or "loot"''',
'''    local t = "loot"
    if tab == "quest" then t = "quest" elseif tab == "guide" then t = "guide" end''',
'SetDungeonTab 三态')

rep(
'''function U:RenderDungeonTab()
    local isQuest = ((U.dungeonTab or "loot") == "quest")
    if U.dungeonDetailScroll then U.dungeonDetailScroll:SetShown(not isQuest) end
    if U.dungeonQuestScroll then U.dungeonQuestScroll:SetShown(isQuest) end
    if U.dungeonQDet then U.dungeonQDet:SetShown(isQuest) end
    if U.dungeonQPlateL then U.dungeonQPlateL:SetShown(isQuest) end
    if U.dungeonQPlateR then U.dungeonQPlateR:SetShown(isQuest) end''',
'''function U:RenderDungeonTab()
    local cur = U.dungeonTab or "loot"
    local isQuest = (cur == "quest")
    local isGuide = (cur == "guide")
    if U.dungeonDetailScroll then U.dungeonDetailScroll:SetShown(not isQuest and not isGuide) end
    if U.dungeonGuideScroll then U.dungeonGuideScroll:SetShown(isGuide) end
    if U.dungeonQuestScroll then U.dungeonQuestScroll:SetShown(isQuest) end
    if U.dungeonQDet then U.dungeonQDet:SetShown(isQuest) end
    if U.dungeonQPlateL then U.dungeonQPlateL:SetShown(isQuest) end
    if U.dungeonQPlateR then U.dungeonQPlateR:SetShown(isQuest) end
    if isGuide then
        for i = 1, #(U.dungeonFilterBtns or {}) do
            U.dungeonFilterBtns[i]:Hide()
        end
    end''',
'RenderDungeonTab 显隐')

rep(
'''    for key, bt in pairs(U.dungeonTabBtns or {}) do
        local sel = (key == (U.dungeonTab or "loot"))
        SetOutline(bt, sel, 1, 0.82, 0)
        local fs = bt:GetFontString()
        if fs then fs:SetTextColor(Unpack(sel and C_GOLD or C_GREY)) end
    end
    if isQuest then
        U:RenderDungeonQuests()
    else
        U:RenderDungeonLoot()
    end
end''',
'''    for key, bt in pairs(U.dungeonTabBtns or {}) do
        local sel = (key == cur)
        SetOutline(bt, sel, 1, 0.82, 0)
        local fs = bt:GetFontString()
        if fs then fs:SetTextColor(Unpack(sel and C_GOLD or C_GREY)) end
    end
    if isQuest then
        U:RenderDungeonQuests()
    elseif isGuide then
        U:RenderDungeonGuide()
    else
        U:RenderDungeonLoot()
    end
end''',
'RenderDungeonTab 分派')

# ------------------------------------------------------------ 4. Build 复位/初始化
rep(
'''    U.dungeonQuestNote = nil
    U.dungeonQuestHover = nil
    U.dungeonTabBtns = nil''',
'''    U.dungeonQuestNote = nil
    U.dungeonQuestHover = nil
    U.dungeonGuideScroll = nil
    U.dungeonGuideChild = nil
    U.dungeonGuidePool = nil
    U.dungeonTabBtns = nil''',
'Build 复位')

rep(
'''    U.dungeonTab = (DB().dungeonTab == "quest") and "quest" or "loot"''',
'''    do
        local dt = DB().dungeonTab
        U.dungeonTab = (dt == "quest" or dt == "guide") and dt or "loot"
    end''',
'Build 三态初始化')

io.open(P, 'wb').write(src.replace('\n', '\r\n').encode('utf-8'))
print('\n写入完成：%s' % P)
