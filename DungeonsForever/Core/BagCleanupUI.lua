local _, ns = ...

local L = ns.L or function(k) return k end
local U = {}
ns.BagCleanupUI = U

local W = 320
local VISIBLE_ROWS = 5
local ROW_H = 44
local ROW_GAP = 6
local ROW_TOP = 96
local CLOSE_S = 36
local DIM = { 0.63, 0.65, 0.68 }
local FAINT = { 0.50, 0.51, 0.53 }
local ACC = (ns.hui and ns.hui.ACCENT) or { 0x46 / 255, 0xbf / 255, 0x72 / 255 }
local RED = { 0.89, 0.30, 0.29 }

local frame, rows, title, countText, emptyText
local tabWhite, tabWhiteFs, tabDestroy, tabDestroyFs
local clearBtn, clearBtnFs, allBtn, allBtnFs, doneBtn
local track, thumb
local confirmFrame, confirmText
local scrollOffset = 0
local listMaxOff = 0
local view = "destroy"

local function BC()
    return ns.BagCleanup
end

local function DB()
    local b = ns.BagCleanup and ns.BagCleanup.DB and ns.BagCleanup.DB()
    if type(b) ~= "table" then return { pos = {} } end
    if type(b.pos) ~= "table" then b.pos = {} end
    return b
end

local function HideTip()
    if GameTooltip then GameTooltip:Hide() end
end

local function Tip(owner, t, d)
    if not (GameTooltip and owner) then return end
    GameTooltip:SetOwner(owner, "ANCHOR_RIGHT")
    GameTooltip:ClearLines()
    GameTooltip:AddLine(t or "", 1, 1, 1, true)
    if d and d ~= "" then GameTooltip:AddLine(d, 0.82, 0.86, 0.90, true) end
    GameTooltip:Show()
end

local function SavePos()
    if not frame then return end
    local p, _, rp, x, y = frame:GetPoint(1)
    if p then
        DB().pos = { p = p, rp = rp or p, x = x or 0, y = y or 0 }
    end
end

local function ApplyPos()
    local o = DB().pos
    frame:ClearAllPoints()
    if type(o) == "table" and o.p then
        frame:SetPoint(o.p, UIParent, o.rp or o.p, o.x or 0, o.y or 0)
    else
        frame:SetPoint("CENTER", UIParent, "CENTER", 0, 0)
    end
end

local function MakeTab(text)
    local b = CreateFrame("Button", nil, frame, "BackdropTemplate")
    b:SetHeight(24)
    if ns.hui and ns.hui.BuildRoundedBG and ns.hui.layer then
        ns.hui.BuildRoundedBG(b, 6, ns.hui.layer.L1, "both", true, 1)
    end
    b.fs = b:CreateFontString(nil, "OVERLAY")
    b.fs:SetFont(ns.FONT, 13, "")
    b.fs:SetPoint("CENTER")
    b.fs:SetText(text)
    return b
end

local function PaintTabs()
    local function paint(btn, on)
        if not (btn and btn.fs) then return end
        if on then
            btn.fs:SetTextColor(ACC[1], ACC[2], ACC[3], 1)
        else
            btn.fs:SetTextColor(FAINT[1], FAINT[2], FAINT[3], 1)
        end
    end
    paint(tabWhite, view == "white")
    paint(tabDestroy, view == "destroy")
end

local function Build()
    frame = CreateFrame("Frame", "DFBagCleanupPanel", UIParent, "BackdropTemplate")
    frame:SetSize(W, ROW_TOP + VISIBLE_ROWS * (ROW_H + ROW_GAP) + 52)
    frame:SetFrameStrata("DIALOG")
    frame:SetClampedToScreen(true)
    frame:EnableMouse(true)
    frame:SetMovable(true)
    frame:RegisterForDrag("LeftButton")
    if ns.hui and ns.hui.SkinPopup and ns.hui.layer then
        ns.hui.SkinPopup(frame, 10, "both", ns.hui.layer.L0)
    end
    ApplyPos()

    title = frame:CreateFontString(nil, "OVERLAY")
    title:SetFont(ns.FONT, 16, "")
    title:SetPoint("TOPLEFT", frame, "TOPLEFT", 14, -12)
    title:SetText(L["背包清理名单"])
    title:SetTextColor(0.95, 0.96, 0.98)

    local close = CreateFrame("Button", nil, frame, "BackdropTemplate")
    close:SetSize(CLOSE_S, CLOSE_S)
    close:SetPoint("TOPRIGHT", frame, "TOPRIGHT", -4, -4)
    close:SetFrameLevel(frame:GetFrameLevel() + 4)
    if ns.hui and ns.hui.SkinButton then ns.hui.SkinButton(close, { noFrame = true }) end
    local ct = close:CreateTexture(nil, "ARTWORK")
    ct:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\textures\\YY_close")
    ct:SetSize(26, 26)
    ct:SetPoint("CENTER")
    ct:SetVertexColor(FAINT[1], FAINT[2], FAINT[3])
    close:SetScript("OnClick", function() frame:Hide() end)
    close:SetScript("OnEnter", function()
        ct:SetVertexColor(1, 1, 1)
        Tip(close, L["关闭"], nil)
    end)
    close:SetScript("OnLeave", function()
        ct:SetVertexColor(FAINT[1], FAINT[2], FAINT[3])
        HideTip()
    end)

    tabWhite = MakeTab(L["白名单"])
    tabWhite:SetPoint("TOPLEFT", frame, "TOPLEFT", 14, -40)
    tabWhite:SetWidth(84)
    tabWhite:SetScript("OnClick", function()
        ns.PlaySound(1)
        view = "white"
        scrollOffset = 0
        U.Refresh()
    end)
    tabDestroy = MakeTab(L["摧毁名单"])
    tabDestroy:SetPoint("LEFT", tabWhite, "RIGHT", 6, 0)
    tabDestroy:SetWidth(96)
    tabDestroy:SetScript("OnClick", function()
        ns.PlaySound(1)
        view = "destroy"
        scrollOffset = 0
        U.Refresh()
    end)

    countText = frame:CreateFontString(nil, "OVERLAY")
    countText:SetFont(ns.FONT, 13, "")
    countText:SetPoint("TOPLEFT", frame, "TOPLEFT", 14, -70)
    countText:SetTextColor(FAINT[1], FAINT[2], FAINT[3])

    rows = {}
    for i = 1, VISIBLE_ROWS do
        local r = CreateFrame("Frame", nil, frame, "BackdropTemplate")
        r:SetSize(W - 28, ROW_H)
        r:SetPoint("TOPLEFT", frame, "TOPLEFT", 14, -ROW_TOP - (i - 1) * (ROW_H + ROW_GAP))
        r:EnableMouse(true)
        r:EnableMouseWheel(true)
        r:SetScript("OnMouseWheel", function(_, delta)
            if frame and frame:IsShown() then U.Refresh(nil, delta) end
        end)
        local fx = ns.hui and ns.hui.HuiCardFX and ns.hui.HuiCardFX(r, 6, 1)
        if not fx and ns.hui and ns.hui.BuildRoundedBG and ns.hui.layer then
            ns.hui.BuildRoundedBG(r, 8, ns.hui.layer.L1, "both", true, 1)
        end
        r:SetScript("OnEnter", function()
            if ns.hui and ns.hui.HuiCardState then ns.hui.HuiCardState(r, "hover") end
            HideTip()
        end)
        r:SetScript("OnLeave", function()
            if ns.hui and ns.hui.HuiCardState then ns.hui.HuiCardState(r, "norm") end
            HideTip()
        end)
        r.icon = r:CreateTexture(nil, "ARTWORK")
        r.icon:SetSize(32, 32)
        r.icon:SetPoint("LEFT", r, "LEFT", 8, 0)
        r.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
        r.name = r:CreateFontString(nil, "OVERLAY")
        r.name:SetFont(ns.FONT, 14, "")
        r.name:SetPoint("TOPLEFT", r, "TOPLEFT", 48, -6)
        r.name:SetTextColor(0.95, 0.96, 0.98)
        r.name:SetWordWrap(false)
        r.name:SetJustifyH("LEFT")
        r.sub = r:CreateFontString(nil, "OVERLAY")
        r.sub:SetFont(ns.FONT, 12, "")
        r.sub:SetPoint("TOPLEFT", r, "TOPLEFT", 48, -26)
        r.sub:SetTextColor(DIM[1], DIM[2], DIM[3])
        r.sub:SetWordWrap(false)
        r.sub:SetJustifyH("LEFT")

        r.b1 = CreateFrame("Button", nil, r)
        r.b1:SetSize(48, 20)
        r.b1t = r.b1:CreateFontString(nil, "OVERLAY")
        r.b1t:SetFont(ns.FONT, 13, "")
        r.b1t:SetPoint("CENTER")
        r.b2 = CreateFrame("Button", nil, r)
        r.b2:SetSize(44, 20)
        r.b2t = r.b2:CreateFontString(nil, "OVERLAY")
        r.b2t:SetFont(ns.FONT, 13, "")
        r.b2t:SetPoint("CENTER")

        r:Hide()
        rows[i] = r
    end

    emptyText = frame:CreateFontString(nil, "OVERLAY")
    emptyText:SetFont(ns.FONT, 14, "")
    emptyText:SetPoint("TOP", frame, "TOP", 0, -(ROW_TOP + (VISIBLE_ROWS * (ROW_H + ROW_GAP)) / 2 - 8))
    emptyText:SetTextColor(FAINT[1], FAINT[2], FAINT[3])
    emptyText:Hide()

    track = CreateFrame("Frame", nil, frame, "BackdropTemplate")
    if ns.hui and ns.hui.BuildCapsule then
        ns.hui.BuildCapsule(track, 3, ns.hui.layer.L2)
    else
        track:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8x8", edgeFile = "Interface\\Buttons\\WHITE8x8", edgeSize = 1 })
        track:SetBackdropColor(0, 0, 0, 0.25)
        track:SetBackdropBorderColor(1, 1, 1, 0.08)
    end
    track:SetWidth(7)
    track:SetHeight(VISIBLE_ROWS * (ROW_H + ROW_GAP) - 4)
    track:SetPoint("TOPRIGHT", frame, "TOPRIGHT", -4, -(ROW_TOP + 2))
    track:SetFrameLevel(frame:GetFrameLevel() + 10)
    track:EnableMouseWheel(true)
    track:SetScript("OnMouseWheel", function(_, delta)
        if frame and frame:IsShown() then U.Refresh(nil, delta) end
    end)
    thumb = CreateFrame("Button", nil, track)
    thumb:SetWidth(5)
    thumb:EnableMouse(true)
    local thTex = nil
    if ns.hui and ns.hui.BuildCapsule then
        thTex = ns.hui.BuildCapsule(thumb, 2, ns.hui.layer.L4)
    else
        thTex = thumb:CreateTexture(nil, "OVERLAY")
        thTex:SetAllPoints()
        thTex:SetColorTexture(1, 1, 1, 0.30)
    end
    thumb:SetScript("OnMouseDown", function(self, b)
        if b ~= "LeftButton" or listMaxOff <= 0 then return end
        local scale = track:GetEffectiveScale() or 1
        local cy0 = select(2, GetCursorPosition()) / scale
        local sc0 = scrollOffset
        self:SetScript("OnUpdate", function(s)
            local okDown, down = pcall(IsMouseButtonDown, "LeftButton")
            if okDown and down == false then s:SetScript("OnUpdate", nil) return end
            local cy = select(2, GetCursorPosition()) / scale
            local span = track:GetHeight() - 2 - thumb:GetHeight()
            if span <= 0 then return end
            local off = math.floor(sc0 + (cy0 - cy) / span * listMaxOff + 0.5)
            if off < 0 then off = 0 end
            if off > listMaxOff then off = listMaxOff end
            if off ~= scrollOffset then scrollOffset = off; U.Refresh() end
        end)
    end)
    thumb:SetScript("OnMouseUp", function(self) self:SetScript("OnUpdate", nil) end)
    thumb:SetScript("OnHide", function(self) self:SetScript("OnUpdate", nil) end)
    thumb:Hide()
    track:Hide()

    frame:EnableMouseWheel(true)
    frame:SetScript("OnMouseWheel", function(_, delta)
        if frame:IsShown() then U.Refresh(nil, delta) end
    end)

    clearBtn = CreateFrame("Button", nil, frame)
    clearBtn:SetHeight(24)
    clearBtn:SetPoint("BOTTOMLEFT", frame, "BOTTOMLEFT", 14, 12)
    clearBtnFs = clearBtn:CreateFontString(nil, "OVERLAY")
    clearBtnFs:SetFont(ns.FONT, 14, "")
    clearBtnFs:SetPoint("CENTER")
    clearBtnFs:SetTextColor(RED[1], RED[2], RED[3])
    clearBtn:SetScript("OnEnter", function() clearBtnFs:SetTextColor(1, 0.55, 0.50) end)
    clearBtn:SetScript("OnLeave", function() clearBtnFs:SetTextColor(RED[1], RED[2], RED[3]) end)

    allBtn = CreateFrame("Button", nil, frame)
    allBtn:SetHeight(24)
    allBtn:SetPoint("BOTTOMLEFT", frame, "BOTTOMLEFT", 14, 12)
    allBtnFs = allBtn:CreateFontString(nil, "OVERLAY")
    allBtnFs:SetFont(ns.FONT, 14, "")
    allBtnFs:SetPoint("CENTER")
    allBtnFs:SetTextColor(RED[1], RED[2], RED[3])
    allBtn:SetScript("OnEnter", function() allBtnFs:SetTextColor(1, 0.55, 0.50) end)
    allBtn:SetScript("OnLeave", function() allBtnFs:SetTextColor(RED[1], RED[2], RED[3]) end)
    allBtn:SetScript("OnClick", function()
        ns.PlaySound(1)
        U.ConfirmDestroyAll()
    end)

    doneBtn = ns.CreateButton(frame)
    doneBtn:SetSize(80, 24)
    doneBtn:SetPoint("BOTTOMRIGHT", frame, "BOTTOMRIGHT", -14, 12)
    doneBtn:SetText(L["完成"])
    doneBtn:SetScript("OnClick", function() frame:Hide() end)

    frame:SetScript("OnDragStart", function()
        if type(InCombatLockdown) == "function" and InCombatLockdown() then return end
        frame:StartMoving()
    end)
    frame:SetScript("OnDragStop", function()
        frame:StopMovingOrSizing()
        SavePos()
    end)

    if UISpecialFrames then
        local found = false
        for i = 1, #UISpecialFrames do
            if UISpecialFrames[i] == "DFBagCleanupPanel" then found = true break end
        end
        if not found then table.insert(UISpecialFrames, "DFBagCleanupPanel") end
    end
end

local function Gather(page)
    local b = BC()
    if not b then return {} end
    if page == "white" then return b.WhiteList() end
    return b.AllItems()
end

local function PaintRow(r, e, page)
    if page == "white" then
        r.icon:SetTexture(e.icon or "Interface\\Icons\\INV_Misc_QuestionMark")
        r.name:SetText(e.name or "")
        r.sub:SetText(string.format(L["物品 #%d"], e.id or 0))
        r.name:SetWidth(W - 28 - 48 - 64)
        r.sub:SetWidth(W - 28 - 48 - 64)
        r.b2:Hide()
        r.b1:ClearAllPoints()
        r.b1:SetPoint("RIGHT", r, "RIGHT", -6, 0)
        r.b1:SetWidth(50)
        r.b1t:SetText(L["移出"])
        r.b1t:SetTextColor(ACC[1], ACC[2], ACC[3])
        r.b1:SetScript("OnClick", function()
            ns.PlaySound(1)
            local b = BC()
            if b and b.RemoveKeep then b.RemoveKeep(e.id) end
            U.Refresh()
        end)
        r.b1:SetScript("OnEnter", function() Tip(r.b1, L["移出白名单"], L["重新回到摧毁名单"]) end)
        r.b1:SetScript("OnLeave", HideTip)
        r.b1:Show()
    else
        r.icon:SetTexture(e.icon or "Interface\\Icons\\INV_Misc_QuestionMark")
        r.name:SetText(e.name or "")
        r.sub:SetText(string.format(L["×%d · 单价 %s"], e.count or 1, BC().MoneyText(e.unit or 0)))
        r.name:SetWidth(W - 28 - 48 - 110)
        r.sub:SetWidth(W - 28 - 48 - 110)
        r.b2:ClearAllPoints()
        r.b2:SetPoint("RIGHT", r, "RIGHT", -6, 0)
        r.b2:SetWidth(44)
        r.b2t:SetText(L["摧毁"])
        r.b2t:SetTextColor(RED[1], RED[2], RED[3])
        r.b2:SetScript("OnClick", function()
            ns.PlaySound(1)
            local b = BC()
            if b and b.DestroyOne then b.DestroyOne(e.bag, e.slot, e.id) end
            U.Refresh()
        end)
        r.b2:SetScript("OnEnter", function() Tip(r.b2, L["摧毁这一件"], nil) end)
        r.b2:SetScript("OnLeave", HideTip)
        r.b2:Show()
        r.b1:ClearAllPoints()
        r.b1:SetPoint("RIGHT", r.b2, "LEFT", -6, 0)
        r.b1:SetWidth(44)
        r.b1t:SetText(L["跳过"])
        r.b1t:SetTextColor(ACC[1], ACC[2], ACC[3])
        r.b1:SetScript("OnClick", function()
            ns.PlaySound(1)
            local b = BC()
            if b and b.Keep then b.Keep(e.id) end
            U.Refresh()
        end)
        r.b1:SetScript("OnEnter", function() Tip(r.b1, L["跳过"], L["加入白名单，不再摧毁"]) end)
        r.b1:SetScript("OnLeave", HideTip)
        r.b1:Show()
    end
end

function U.Refresh(_, wheel)
    if not frame then return end
    local page = view
    local list = Gather(page)
    local n = #list
    local maxOff = math.max(0, n - VISIBLE_ROWS)
    listMaxOff = maxOff
    if type(wheel) == "number" then scrollOffset = scrollOffset - wheel end
    if scrollOffset > maxOff then scrollOffset = maxOff end
    if scrollOffset < 0 then scrollOffset = 0 end

    for i = 1, VISIBLE_ROWS do
        local r = rows[i]
        local e = list[scrollOffset + i]
        if e then
            PaintRow(r, e, page)
            r:Show()
        else
            r:Hide()
        end
    end

    if page == "white" then
        countText:SetText(string.format(L["共 %d 项"], n))
        emptyText:SetText(L["白名单为空"])
        emptyText:SetShown(n == 0)
        clearBtnFs:SetText(L["清空白名单"])
        clearBtn:SetWidth(math.max(80, ns.WIDE_UI and (math.ceil(clearBtnFs:GetStringWidth()) + 24) or (14 + #L["清空白名单"] * 14)))
        clearBtn:Show()
        allBtn:Hide()
    else
        local b = BC()
        local total = 0
        for _, e in ipairs(list) do total = total + (e.value or 0) end
        countText:SetText(string.format(L["可摧毁 %d 件 · 合计 %s"], n, (b and b.MoneyText(total)) or ""))
        emptyText:SetText(L["没有可摧毁的灰色物品"])
        emptyText:SetShown(n == 0)
        allBtnFs:SetText(string.format(L["摧毁全部（%d）"], n))
        allBtn:SetWidth(math.max(90, ns.WIDE_UI and (math.ceil(allBtnFs:GetStringWidth()) + 24) or (14 + (#L["摧毁全部（"] + 3) * 14)))
        allBtn:SetShown(n > 0)
        clearBtn:Hide()
    end

    if maxOff > 0 then
        track:Show()
        local trackH = track:GetHeight() - 2
        local th = math.max(24, trackH * VISIBLE_ROWS / n)
        local frac = (maxOff > 0) and (scrollOffset / maxOff) or 0
        thumb:SetHeight(th)
        thumb:ClearAllPoints()
        thumb:SetPoint("TOP", track, "TOP", 0, -1 - frac * (trackH - th))
        thumb:Show()
    else
        track:Hide()
        thumb:Hide()
    end

    PaintTabs()
end

local function BuildConfirm()
    confirmFrame = CreateFrame("Frame", "DFBagCleanupConfirm", UIParent, "BackdropTemplate")
    confirmFrame:SetSize(340, 130)
    confirmFrame:SetPoint("CENTER", UIParent, "CENTER", 0, 40)
    confirmFrame:SetFrameStrata("FULLSCREEN_DIALOG")
    confirmFrame:EnableMouse(true)
    if ns.hui and ns.hui.SkinPopup and ns.hui.layer then
        ns.hui.SkinPopup(confirmFrame, 10, "both", ns.hui.layer.L0)
    end
    if ns.hui and ns.hui.SkinShadow then ns.hui.SkinShadow(confirmFrame, nil, nil, 8) end
    confirmText = confirmFrame:CreateFontString(nil, "OVERLAY")
    confirmText:SetFont(ns.FONT, 14, "")
    confirmText:SetPoint("TOPLEFT", confirmFrame, "TOPLEFT", 16, -16)
    confirmText:SetWidth(308)
    confirmText:SetWordWrap(true)
    confirmText:SetJustifyH("LEFT")
    confirmText:SetTextColor(0.95, 0.96, 0.98)
    local yes = ns.CreateButton(confirmFrame)
    yes:SetSize(130, 26)
    yes:SetPoint("BOTTOMLEFT", confirmFrame, "BOTTOMLEFT", 16, 14)
    yes:SetText(L["确认摧毁"])
    yes:SetScript("OnClick", function()
        confirmFrame:Hide()
        local b = BC()
        if b and b.DestroyAll then b.DestroyAll(function() U.Refresh() end) end
    end)
    local no = ns.CreateButton(confirmFrame)
    no:SetSize(90, 26)
    no:SetPoint("BOTTOMRIGHT", confirmFrame, "BOTTOMRIGHT", -16, 14)
    no:SetText(L["取消"])
    no:SetScript("OnClick", function() confirmFrame:Hide() end)
    confirmFrame:Hide()
end

function U.ConfirmDestroyAll()
    local b = BC()
    if not b then return end
    local d = b.Get(true)
    if (d.count or 0) <= 0 then return end
    if not confirmFrame then BuildConfirm() end
    confirmText:SetText(string.format(L["确认摧毁全部 %d 件灰色物品？合计卖店价值约 %s，不可恢复。"], d.count, b.MoneyText(d.totalValue)))
    confirmFrame:Show()
    if confirmFrame.Raise then confirmFrame:Raise() end
end

function U.Open(page)
    if not frame then Build() end
    if page == "white" or page == "destroy" then view = page end
    scrollOffset = 0
    ApplyPos()
    U.Refresh()
    frame:Show()
end

function U.Close()
    if frame then frame:Hide() end
end

function U.Toggle(page)
    if frame and frame:IsShown() then
        U.Close()
    else
        U.Open(page)
    end
end

function U.IsShown()
    return frame and frame:IsShown() and true or false
end
