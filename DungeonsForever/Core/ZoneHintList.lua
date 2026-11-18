local _, ns = ...

local L = ns.L or function(k) return k end
local B = {}
ns.ZoneHintList = B

local VISIBLE_ROWS = 5
local ROW_H = 44
local ROW_GAP = 6
local ROW_TOP = 52
local W = 292
local CLOSE_S = 36
local FAINT = { 0.50, 0.51, 0.53 }
local DIM = { 0.63, 0.65, 0.68 }
local ACC = (ns.hui and ns.hui.ACCENT) or { 0x46 / 255, 0xbf / 255, 0x72 / 255 }

local frame, rows, emptyText, countText
local filterBtn, filterFs
local clearKindBtn, clearKindFs
local track, thumb
local scrollOffset = 0
local menuDefs = {}
local listMaxOff = 0

local function Cfg()
    local db = ns.DB()
    db.ui.zoneHint = db.ui.zoneHint or {}
    local c = db.ui.zoneHint
    if type(c.listPos) ~= "table" then c.listPos = {} end
    if type(c.listFilter) ~= "string" or c.listFilter == "" then c.listFilter = "all" end
    return c
end

local function ChipW(label)
    local w = 16
    for i = 1, #label do
        local b = label:byte(i)
        w = w + ((b and b > 127) and 13 or 7)
    end
    return w
end

local function MenuClose()
    if ns.hui and ns.hui.HideDFMenu then ns.hui.HideDFMenu() end
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

    filterBtn = CreateFrame("Button", nil, frame, "BackdropTemplate")
    filterBtn:SetHeight(22)
    filterBtn:SetPoint("LEFT", title, "RIGHT", 8, -1)
    if ns.hui and ns.hui.BuildRoundedBG and ns.hui.layer then
        ns.hui.BuildRoundedBG(filterBtn, 6, ns.hui.layer.L1, "both", true, 1)
    end
    filterFs = filterBtn:CreateFontString(nil, "OVERLAY")
    filterFs:SetFont(ns.FONT, 12, "")
    filterFs:SetPoint("CENTER")
    filterBtn:SetScript("OnClick", function()
        ns.PlaySound(1)
        B.ToggleMenu()
    end)
    filterBtn:SetScript("OnEnter", function()
        Tip(filterBtn, L["按类型筛选"], L["只显示某一类忽略记录"])
    end)
    filterBtn:SetScript("OnLeave", HideTip)
    filterBtn:EnableMouseWheel(true)
    filterBtn:SetScript("OnMouseWheel", function(_, delta)
        if frame and frame:IsShown() then B.Refresh(nil, delta) end
    end)

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
    for i = 1, VISIBLE_ROWS do
        local r = CreateFrame("Frame", nil, frame, "BackdropTemplate")
        r:SetSize(W - 28, ROW_H)
        r:SetPoint("TOPLEFT", frame, "TOPLEFT", 14, -ROW_TOP - (i - 1) * (ROW_H + ROW_GAP))
        r:EnableMouse(true)
        r:EnableMouseWheel(true)
        r:SetScript("OnMouseWheel", function(_, delta)
            if frame and frame:IsShown() then B.Refresh(nil, delta) end
        end)
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
    emptyText:SetPoint("TOP", frame, "TOP", 0, -(ROW_TOP + (VISIBLE_ROWS * (ROW_H + ROW_GAP)) / 2 - 8))
    emptyText:SetText(L["暂无忽略项"])
    emptyText:SetTextColor(FAINT[1], FAINT[2], FAINT[3])
    emptyText:Hide()

    track = CreateFrame("Frame", nil, frame, "BackdropTemplate")
    if ns.hui and ns.hui.BuildCapsule then
        ns.hui.BuildCapsule(track, 3, ns.hui.layer.L2)
    else
        track:SetBackdrop({
            bgFile = "Interface\\Buttons\\WHITE8x8",
            edgeFile = "Interface\\Buttons\\WHITE8x8",
            edgeSize = 1,
        })
        track:SetBackdropColor(0, 0, 0, 0.25)
        track:SetBackdropBorderColor(1, 1, 1, 0.08)
    end
    track:SetWidth(7)
    track:SetHeight(VISIBLE_ROWS * (ROW_H + ROW_GAP) - 4)
    track:SetPoint("TOPRIGHT", frame, "TOPRIGHT", -4, -(ROW_TOP + 2))
    track:SetFrameLevel(frame:GetFrameLevel() + 10)
    track:EnableMouseWheel(true)
    track:SetScript("OnMouseWheel", function(_, delta)
        if frame and frame:IsShown() then B.Refresh(nil, delta) end
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
    thumb:SetScript("OnEnter", function()
        if type(thTex) == "table" then
            local L5 = ns.hui.layer.L5
            for _, t in ipairs(thTex) do t:SetVertexColor(L5[1], L5[2], L5[3]) end
        elseif thTex then
            thTex:SetColorTexture(1, 1, 1, 0.45)
        end
    end)
    thumb:SetScript("OnLeave", function()
        if type(thTex) == "table" then
            local L4 = ns.hui.layer.L4
            for _, t in ipairs(thTex) do t:SetVertexColor(L4[1], L4[2], L4[3]) end
        elseif thTex then
            thTex:SetColorTexture(1, 1, 1, 0.30)
        end
    end)
    thumb:SetScript("OnMouseDown", function(self, b)
        if b ~= "LeftButton" or listMaxOff <= 0 then return end
        local scale = track:GetEffectiveScale() or 1
        local cy0 = select(2, GetCursorPosition()) / scale
        local sc0 = scrollOffset
        self:SetScript("OnUpdate", function(s)
            local okDown, down = pcall(IsMouseButtonDown, "LeftButton")
            if okDown and down == false then
                s:SetScript("OnUpdate", nil)
                return
            end
            local cy = select(2, GetCursorPosition()) / scale
            local span = track:GetHeight() - 2 - thumb:GetHeight()
            if span <= 0 then return end
            local off = math.floor(sc0 + (cy0 - cy) / span * listMaxOff + 0.5)
            if off < 0 then off = 0 end
            if off > listMaxOff then off = listMaxOff end
            if off ~= scrollOffset then
                scrollOffset = off
                B.Refresh()
            end
        end)
    end)
    thumb:SetScript("OnMouseUp", function(self)
        self:SetScript("OnUpdate", nil)
    end)
    thumb:SetScript("OnHide", function(self)
        self:SetScript("OnUpdate", nil)
    end)
    thumb:Hide()
    track:Hide()

    frame:EnableMouseWheel(true)
    frame:SetScript("OnMouseWheel", function(_, delta)
        if frame:IsShown() then B.Refresh(nil, delta) end
    end)

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

    clearKindBtn = CreateFrame("Button", nil, frame)
    clearKindBtn:SetHeight(24)
    clearKindBtn:SetPoint("BOTTOM", frame, "BOTTOM", 0, 12)
    clearKindFs = clearKindBtn:CreateFontString(nil, "OVERLAY")
    clearKindFs:SetFont(ns.FONT, 14, "")
    clearKindFs:SetPoint("CENTER")
    clearKindFs:SetTextColor(0.89, 0.30, 0.29)
    clearKindBtn:SetScript("OnClick", function()
        local Z = ns.ZoneHint
        local fk = Cfg().listFilter
        if not (Z and fk and fk ~= "all") then return end
        local n = 0
        if Z.ItemList then
            for _, e in ipairs(Z.ItemList()) do
                local kd = (e.scope == "map") and "map" or (e.kind or "item")
                if kd == fk then Z.UnignoreItem(e.key); n = n + 1 end
            end
        end
        if fk == "map" and Z.BlockList and Z.Unblock then
            for _, e in ipairs(Z.BlockList()) do Z.Unblock(e.key); n = n + 1 end
        end
        if n > 0 then
            ns.PlaySound(1)
            B.Refresh()
            if ns.ZoneOrb and ns.ZoneOrb.Refresh then ns.ZoneOrb.Refresh() end
            if ns.MainFrame and ns.MainFrame.SyncZoneHintCard then ns.MainFrame.SyncZoneHintCard() end
        end
    end)
    clearKindBtn:SetScript("OnEnter", function() clearKindFs:SetTextColor(1, 0.55, 0.50) end)
    clearKindBtn:SetScript("OnLeave", function() clearKindFs:SetTextColor(0.89, 0.30, 0.29) end)
    clearKindBtn:Hide()

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
    frame:SetScript("OnHide", MenuClose)

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

local function EntryKind(e)
    return (e.scope == "map") and "map" or (e.kind or "item")
end

function B.ToggleMenu()
    if not frame or not filterBtn then return end
    local items = {}
    local fkind = Cfg().listFilter
    local selMix = ACC[1] + (1 - ACC[1]) * 0.42
    for i = 1, #menuDefs do
        local d = menuDefs[i]
        local sel = (d.k == fkind)
        items[#items + 1] = {
            text = d.label,
            func = function()
                Cfg().listFilter = d.k
                scrollOffset = 0
                B.Refresh()
            end,
            selected = sel,
            hlColor = ACC,
            color = sel and { selMix, ACC[2] + (1 - ACC[2]) * 0.42, ACC[3] + (1 - ACC[3]) * 0.42 } or nil,
        }
    end
    if #items == 0 then return end
    if ns.hui and ns.hui.ShowMenu then
        ns.hui.ShowMenu(items, { owner = filterBtn, anchor = filterBtn })
    end
end

function B.Refresh(_, wheel)
    if not frame then return end
    local list = Gather()
    local Z = ns.ZoneHint
    local kc, order = {}, {}
    for i = 1, #list do
        local k = EntryKind(list[i])
        if not kc[k] then kc[k] = 0; order[#order + 1] = k end
        kc[k] = kc[k] + 1
    end
    table.sort(order, function(a, b)
        if kc[a] ~= kc[b] then return kc[a] > kc[b] end
        local na = (Z.KindName and Z.KindName(a)) or a
        local nb = (Z.KindName and Z.KindName(b)) or b
        return tostring(na) < tostring(nb)
    end)
    local fkind = Cfg().listFilter
    if fkind ~= "all" and not kc[fkind] then
        Cfg().listFilter = "all"
        fkind = "all"
    end
    local frows = {}
    for i = 1, #list do
        local e = list[i]
        if fkind == "all" or fkind == EntryKind(e) then frows[#frows + 1] = e end
    end
    local n = #frows
    local maxOff = math.max(0, n - VISIBLE_ROWS)
    listMaxOff = maxOff
    if type(wheel) == "number" then scrollOffset = scrollOffset - wheel end
    if scrollOffset > maxOff then scrollOffset = maxOff end
    if scrollOffset < 0 then scrollOffset = 0 end
    menuDefs = { { k = "all", label = L["全部"], n = #list } }
    for i = 1, #order do
        menuDefs[#menuDefs + 1] = { k = order[i], label = (Z.KindName and Z.KindName(order[i])) or order[i], n = kc[order[i]] }
    end
    if filterFs then
        local fl = L["全部"]
        if fkind ~= "all" then
            fl = (Z.KindName and Z.KindName(fkind)) or fkind
        end
        filterFs:SetText(fl)
        filterBtn:SetWidth(ChipW(fl) + 8)
        if fkind ~= "all" then
            filterFs:SetTextColor(ACC[1], ACC[2], ACC[3], 1)
        else
            filterFs:SetTextColor(FAINT[1], FAINT[2], FAINT[3], 1)
        end
    end
    if clearKindBtn then
        if fkind ~= "all" then
            local txt = L["清空"] .. ((Z.KindName and Z.KindName(fkind)) or fkind)
            clearKindFs:SetText(txt)
            clearKindBtn:SetWidth(math.max(60, ChipW(txt) + 12))
            clearKindBtn:Show()
        else
            clearKindBtn:Hide()
        end
    end
    for i = 1, VISIBLE_ROWS do
        local r = rows[i]
        local e = frows[scrollOffset + i]
        if e then
            r.key = e.key
            r.scope = e.scope
            if e.scope == "item" then
                local kind = Z.KindName and Z.KindName(e.kind) or ""
                r.icon:SetTexture((Z.IconFor and Z.IconFor(e.kind, e.id)) or "Interface\\Icons\\INV_Misc_QuestionMark")
                r.name:SetText(e.label or e.key or "")
                if e.kind == "quest" then
                    r.sub:SetText(tostring(e.id or ""))
                else
                    r.sub:SetText(kind)
                end
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
    frame:SetHeight(ROW_TOP + VISIBLE_ROWS * (ROW_H + ROW_GAP) + 52)
    if countText then
        countText:SetText(string.format(L["共 %d 条 · 恢复后下次进入会重新提醒"], n))
    end
    if emptyText then
        if n == 0 then emptyText:Show() else emptyText:Hide() end
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
end

function B.Notify()
    if frame and frame:IsShown() then B.Refresh() end
end

function B.Open()
    if not frame then Build() end
    ApplyPos()
    B.Refresh()
    frame:Show()
end

function B.Close()
    if frame then
        MenuClose()
        frame:Hide()
    end
end

function B.Toggle()
    if frame and frame:IsShown() then B.Close() else B.Open() end
end
