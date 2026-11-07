local _, ns = ...

local L = ns.L or function(k) return k end
local B = {}
ns.ZoneHintList = B

local MAX_ROWS = 10
local W = 292
local ROW_H = 44
local ROW_GAP = 6
local CLOSE_S = 36
local FAINT = { 0.50, 0.51, 0.53 }
local DIM = { 0.63, 0.65, 0.68 }
local ACC = (ns.hui and ns.hui.ACCENT) or { 0x46 / 255, 0xbf / 255, 0x72 / 255 }

local frame, rows, emptyText, countText

local function Cfg()
    local db = ns.DB()
    db.ui.zoneHint = db.ui.zoneHint or {}
    local c = db.ui.zoneHint
    if type(c.listPos) ~= "table" then c.listPos = {} end
    return c
end

local function SavePos()
    if not frame then return end
    local p, _, rp, x, y = frame:GetPoint(1)
    if p then
        Cfg().listPos = { p = p, rp = rp or p, x = x or 0, y = y or 0 }
    end
end

local function ApplyPos()
    local o = Cfg().listPos
    frame:ClearAllPoints()
    if type(o) == "table" and o.p then
        frame:SetPoint(o.p, UIParent, o.rp or o.p, o.x or 0, o.y or 0)
    else
        frame:SetPoint("CENTER", UIParent, "CENTER", 0, 0)
    end
end

local function HideTip()
    if GameTooltip then GameTooltip:Hide() end
end

local function Tip(owner, title, desc)
    if not (GameTooltip and owner) then return end
    GameTooltip:SetOwner(owner, "ANCHOR_RIGHT")
    GameTooltip:ClearLines()
    GameTooltip:AddLine(title or "", 1, 1, 1, true)
    if desc and desc ~= "" then
        GameTooltip:AddLine(desc, 0.82, 0.86, 0.90, true)
    end
    GameTooltip:Show()
end

local function Build()
    frame = CreateFrame("Frame", "DFZoneHintListPanel", UIParent, "BackdropTemplate")
    frame:SetSize(W, 200)
    frame:SetFrameStrata("DIALOG")
    frame:SetClampedToScreen(true)
    frame:EnableMouse(true)
    frame:SetMovable(true)
    frame:RegisterForDrag("LeftButton")
    if ns.hui and ns.hui.SkinPopup and ns.hui.layer then
        ns.hui.SkinPopup(frame, 10, "both", ns.hui.layer.L0)
    end
    ApplyPos()

    local title = frame:CreateFontString(nil, "OVERLAY")
    title:SetFont(ns.FONT, 16, "")
    title:SetPoint("TOPLEFT", frame, "TOPLEFT", 14, -12)
    title:SetText(L["黑名单"])
    title:SetTextColor(0.95, 0.96, 0.98)

    countText = frame:CreateFontString(nil, "OVERLAY")
    countText:SetFont(ns.FONT, 14, "")
    countText:SetPoint("TOPLEFT", frame, "TOPLEFT", 14, -34)
    countText:SetTextColor(FAINT[1], FAINT[2], FAINT[3])

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
        Tip(close, L["关闭"], L["关闭这个面板，忽略记录仍然保留"])
    end)
    close:SetScript("OnLeave", function()
        ct:SetVertexColor(FAINT[1], FAINT[2], FAINT[3])
        HideTip()
    end)

    rows = {}
    for i = 1, MAX_ROWS do
        local r = CreateFrame("Frame", nil, frame, "BackdropTemplate")
        r:SetSize(W - 28, ROW_H)
        r:SetPoint("TOPLEFT", frame, "TOPLEFT", 14, -52 - (i - 1) * (ROW_H + ROW_GAP))
        r:EnableMouse(true)
        local fx = ns.hui and ns.hui.HuiCardFX and ns.hui.HuiCardFX(r, 6, 1)
        if not fx and ns.hui and ns.hui.BuildRoundedBG and ns.hui.layer then
            ns.hui.BuildRoundedBG(r, 8, ns.hui.layer.L1, "both", true, 1)
        end
        r:SetScript("OnEnter", function()
            if ns.hui and ns.hui.HuiCardState then ns.hui.HuiCardState(r, "hover") end
            if r.onEnter then r.onEnter() end
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
        r.name:SetWidth(W - 28 - 48 - 56)
        r.name:SetWordWrap(false)
        r.name:SetJustifyH("LEFT")
        r.sub = r:CreateFontString(nil, "OVERLAY")
        r.sub:SetFont(ns.FONT, 12, "")
        r.sub:SetPoint("TOPLEFT", r, "TOPLEFT", 48, -26)
        r.sub:SetTextColor(DIM[1], DIM[2], DIM[3])
        r.sub:SetWidth(W - 28 - 48 - 56)
        r.sub:SetWordWrap(false)
        r.sub:SetJustifyH("LEFT")
        local del = CreateFrame("Button", nil, r)
        del:SetSize(44, 20)
        del:SetPoint("RIGHT", r, "RIGHT", -6, 0)
        local dt = del:CreateFontString(nil, "OVERLAY")
        dt:SetFont(ns.FONT, 14, "")
        dt:SetPoint("CENTER", del, "CENTER", 0, 0)
        dt:SetText(L["恢复"])
        dt:SetTextColor(ACC[1], ACC[2], ACC[3])
        del:SetScript("OnClick", function()
            if r.key and ns.ZoneHint then
                if r.scope == "item" then
                    ns.ZoneHint.UnignoreItem(r.key)
                else
                    ns.ZoneHint.Unblock(r.key)
                end
                ns.PlaySound(1)
                B.Refresh()
                if ns.ZoneOrb and ns.ZoneOrb.Refresh then ns.ZoneOrb.Refresh() end
                if ns.MainFrame and ns.MainFrame.SyncZoneHintCard then ns.MainFrame.SyncZoneHintCard() end
            end
        end)
        del:SetScript("OnEnter", function()
            dt:SetTextColor(0.55, 0.95, 0.70)
            Tip(del, L["恢复提醒"], L["重新加回待办，下次进入会再提醒"])
        end)
        del:SetScript("OnLeave", function()
            dt:SetTextColor(ACC[1], ACC[2], ACC[3])
            HideTip()
        end)
        r:Hide()
        rows[i] = r
    end

    emptyText = frame:CreateFontString(nil, "OVERLAY")
    emptyText:SetFont(ns.FONT, 14, "")
    emptyText:SetPoint("TOP", frame, "TOP", 0, -120)
    emptyText:SetText(L["暂无忽略项"])
    emptyText:SetTextColor(FAINT[1], FAINT[2], FAINT[3])
    emptyText:Hide()

    local clear = CreateFrame("Button", nil, frame)
    clear:SetSize(90, 24)
    clear:SetPoint("BOTTOMLEFT", frame, "BOTTOMLEFT", 14, 12)
    local clt = clear:CreateFontString(nil, "OVERLAY")
    clt:SetFont(ns.FONT, 14, "")
    clt:SetPoint("CENTER", clear, "CENTER", 0, 0)
    clt:SetText(L["全部清空"])
    clt:SetTextColor(0.89, 0.30, 0.29)
    clear:SetScript("OnClick", function()
        if ns.ZoneHint then
            ns.ZoneHint.ClearBlock()
            ns.ZoneHint.ClearItems()
            ns.PlaySound(1)
            B.Refresh()
            if ns.ZoneOrb and ns.ZoneOrb.Refresh then ns.ZoneOrb.Refresh() end
            if ns.MainFrame and ns.MainFrame.SyncZoneHintCard then ns.MainFrame.SyncZoneHintCard() end
        end
    end)
    clear:SetScript("OnEnter", function() clt:SetTextColor(1, 0.55, 0.50) end)
    clear:SetScript("OnLeave", function() clt:SetTextColor(0.89, 0.30, 0.29) end)

    local done = ns.CreateButton(frame)
    done:SetSize(80, 24)
    done:SetPoint("BOTTOMRIGHT", frame, "BOTTOMRIGHT", -14, 12)
    done:SetText(L["完成"])
    done:SetScript("OnClick", function() frame:Hide() end)

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
            if UISpecialFrames[i] == "DFZoneHintListPanel" then found = true break end
        end
        if not found then table.insert(UISpecialFrames, "DFZoneHintListPanel") end
    end
end

local function Gather()
    local Z = ns.ZoneHint
    local out = {}
    if not Z then return out end
    if Z.BlockList then
        local maps = Z.BlockList()
        for i = 1, #maps do
            local e = maps[i]
            e.scope = "map"
            out[#out + 1] = e
        end
    end
    if Z.ItemList then
        local items = Z.ItemList()
        for i = 1, #items do
            local e = items[i]
            e.scope = "item"
            out[#out + 1] = e
        end
    end
    return out
end

function B.Count()
    local list = Gather()
    return #list
end

function B.Refresh()
    if not frame then return end
    local list = Gather()
    local Z = ns.ZoneHint
    for i = 1, MAX_ROWS do
        local r = rows[i]
        local e = list[i]
        if e then
            r.key = e.key
            r.scope = e.scope
            if e.scope == "item" then
                local kind = Z.KindName and Z.KindName(e.kind) or ""
                r.icon:SetTexture((Z.IconFor and Z.IconFor(e.kind, e.id)) or "Interface\\Icons\\INV_Misc_QuestionMark")
                r.name:SetText(e.label or e.key or "")
                r.sub:SetText(kind)
            else
                r.icon:SetTexture("Interface\\Icons\\INV_Misc_Map_01")
                r.name:SetText(e.name or e.key or "")
                r.sub:SetText(L["整张地图"])
            end
            r:Show()
        else
            r.key = nil
            r.scope = nil
            r:Hide()
        end
    end
    local n = #list
    local rowsH = math.max(1, math.min(n, MAX_ROWS)) * (ROW_H + ROW_GAP)
    frame:SetHeight(52 + rowsH + 52)
    if countText then
        countText:SetText(string.format(L["共 %d 条 · 恢复后下次进入会重新提醒"], n))
    end
    if emptyText then
        if n == 0 then emptyText:Show() else emptyText:Hide() end
    end
end

function B.Open()
    if not frame then Build() end
    ApplyPos()
    B.Refresh()
    frame:Show()
end

function B.Close()
    if frame then frame:Hide() end
end

function B.Toggle()
    if frame and frame:IsShown() then B.Close() else B.Open() end
end
