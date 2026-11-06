local ns = _G.DF_NS or {}
local SR = ns.SpellRank
if not SR then return end

local L = ns.L or setmetatable({}, { __index = function(_, k) return k end })

local UI = {}
ns.SpellRankUI = UI

local HT = (ns.hui and ns.hui.TEXT) or {}
local ACC = (ns.hui and ns.hui.ACCENT) or { 0x46 / 255, 0xbf / 255, 0x72 / 255 }
local TXT = HT[1] or { 0.95, 0.96, 0.98 }
local SUB = HT[3] or { 0.63, 0.63, 0.63 }
local DIM = HT[4] or { 0.53, 0.53, 0.53 }
local GOLD = { 0.98, 0.84, 0.36 }
local LAYER = (ns.hui and ns.hui.layer) or {}

local MEDIA = "Interface\\AddOns\\DungeonsForever\\Media\\Common\\"
local BRAND = "Interface\\AddOns\\DungeonsForever\\Media\\Brand\\"
local TEX = {
    ring = MEDIA .. "CheckRing",
    disc = MEDIA .. "CheckDisc",
    mark = MEDIA .. "CheckMark",
}
local LOGO_TEX = BRAND .. "DungeonsForever.blp"

local WIN_W, WIN_H = 460, 364
local CARD_W = 440
local ROW_H = 44
local ROW_PITCH = 46
local LIST_H = 276
local BTN_H = 24
local BTN_W = 60

local MODE_PENDING, MODE_WHITE = 1, 2

local function FS(parent, size, color, just)
    local t = parent:CreateFontString(nil, "OVERLAY")
    t:SetFont(ns.FONT, size or 13, "")
    if color then t:SetTextColor(color[1], color[2], color[3]) end
    if just then t:SetJustifyH(just) end
    return t
end

local function SetPoints(fs, parent, x, y, just)
    fs:ClearAllPoints()
    fs:SetPoint("TOPLEFT", parent, "TOPLEFT", x, y)
    fs:SetJustifyH(just or "LEFT")
end

local function MakeCheck(parent, size)
    local c = CreateFrame("Button", nil, parent)
    c:SetSize(size or 14, size or 14)
    c.ring = c:CreateTexture(nil, "ARTWORK")
    c.ring:SetAllPoints()
    c.ring:SetTexture(TEX.ring)
    c.disc = c:CreateTexture(nil, "ARTWORK")
    c.disc:SetAllPoints()
    c.disc:SetTexture(TEX.disc)
    c.disc:SetVertexColor(ACC[1], ACC[2], ACC[3])
    c.mark = c:CreateTexture(nil, "OVERLAY")
    c.mark:SetAllPoints()
    c.mark:SetTexture(TEX.mark)
    c.on = false
    function c:SetOn(v)
        self.on = v and true or false
        self.ring:SetShown(not self.on)
        self.disc:SetShown(self.on)
        self.mark:SetShown(self.on)
    end
    function c:IsOn()
        return self.on
    end
    c:SetOn(false)
    return c
end

local function ShowSpellTip(owner, d)
    if not d then return end
    GameTooltip:SetOwner(owner, "ANCHOR_RIGHT")
    local ok = false
    if d.bestId and GameTooltip.SetSpellByID then
        ok = pcall(GameTooltip.SetSpellByID, GameTooltip, d.bestId)
        if ok then ok = (GameTooltip:NumLines() or 0) > 0 end
    end
    if not ok then
        GameTooltip:ClearLines()
        GameTooltip:AddLine(d.name or L["未知法术"], 1, 1, 1)
    end
    if d.from or d.to then
        GameTooltip:AddLine((d.from or "?") .. " → " .. (d.to or "?"), ACC[1], ACC[2], ACC[3])
    end
    if d.slots and #d.slots > 0 then
        local t = {}
        for i = 1, #d.slots do
            local b = SR.BindFor(d.slots[i])
            t[i] = b and (d.slots[i] .. " (" .. b .. ")") or tostring(d.slots[i])
        end
        GameTooltip:AddLine(L["槽位"] .. " " .. table.concat(t, "、"), 0.82, 0.86, 0.9, true)
    elseif d.noBar then
        GameTooltip:AddLine(L["技能书里有，动作条上没有"], 0.82, 0.86, 0.9, true)
    end
    GameTooltip:Show()
end

local function MakeRow(parent, w, mode)
    local r = CreateFrame("Button", nil, parent)
    r:SetSize(w, ROW_H)
    r:RegisterForClicks("LeftButtonUp")
    if ns.hui and ns.hui.HuiCardFX then ns.hui.HuiCardFX(r, 6, 2) end
    r.mode = mode
    r.ck = MakeCheck(r, 14)
    r.ck:SetPoint("LEFT", r, "LEFT", 12, 0)
    r.iconBox = CreateFrame("Frame", nil, r)
    r.iconBox:SetSize(32, 32)
    r.iconBox:SetPoint("LEFT", r, "LEFT", 36, 0)
    r.icon = r.iconBox:CreateTexture(nil, "ARTWORK")
    r.icon:SetAllPoints()
    r.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
    if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(r.icon) end
    r.name = FS(r, 14, TXT, "LEFT")
    SetPoints(r.name, r, 76, -6)
    r.name:SetWordWrap(false)
    r.sub = FS(r, 12, SUB, "LEFT")
    SetPoints(r.sub, r, 76, -26)
    r.sub:SetWordWrap(false)
    r.right = FS(r, 14, TXT, "RIGHT")
    r.right:ClearAllPoints()
    r.right:SetPoint("RIGHT", r, "RIGHT", -10, 0)
    r.right:SetWordWrap(false)
    r.ck:SetScript("OnClick", function(self)
        self:SetOn(not self:IsOn())
        if r.onToggle then r.onToggle(r) end
    end)
    r:SetScript("OnClick", function(self)
        if r.locked then return end
        r.ck:SetOn(not r.ck:IsOn())
        if r.onToggle then r.onToggle(r) end
    end)
    r:SetScript("OnEnter", function(self)
        if ns.hui and ns.hui.HuiCardState then ns.hui.HuiCardState(self, "hover") end
        if self.data and not self.data.all then ShowSpellTip(self, self.data) end
    end)
    r:SetScript("OnLeave", function(self)
        if ns.hui and ns.hui.HuiCardState then ns.hui.HuiCardState(self, "norm") end
        GameTooltip:Hide()
    end)
    r:Hide()
    return r
end

local function SlotText(slots)
    if not slots or #slots == 0 then return L["未上动作条"] end
    local a, b = {}, {}
    for i = 1, #slots do
        a[i] = tostring(slots[i])
        local k = SR.BindFor(slots[i])
        if k then b[#b + 1] = k end
    end
    local s = L["槽位"] .. " " .. table.concat(a, "、")
    if #b > 0 then s = s .. " · " .. L["按键"] .. " " .. table.concat(b, "、") end
    return s
end

local function RankMarkup(from, to)
    local a = from or "?"
    local b = to or "?"
    return "|cff7f8998" .. a .. "|r  →  |cff46bf72" .. b .. "|r"
end

local function PaintRow(r, data, mode)
    r.data = data
    if mode == MODE_WHITE then
        r.name:SetTextColor(TXT[1], TXT[2], TXT[3])
        r.right:SetText(data.slotText or "")
        r.right:SetTextColor(DIM[1], DIM[2], DIM[3])
    else
        r.name:SetTextColor(TXT[1], TXT[2], TXT[3])
        r.right:SetText(RankMarkup(data.from, data.to))
    end
    r.name:ClearAllPoints()
    if data.all then
        r.name:SetPoint("TOPLEFT", r, "TOPLEFT", 36, -14)
    else
        r.name:SetPoint("TOPLEFT", r, "TOPLEFT", 76, -6)
    end
    r.name:SetText(data.name or "")
    r.sub:SetText(data.sub or "")
    r.icon:SetTexture(data.icon or "Interface\\Icons\\INV_Misc_QuestionMark")
    r.ck:SetOn(data.checked and true or false)
    r.locked = data.locked and true or false
    r.iconBox:SetShown(not data.all)
    if data.white then
        r.name:SetTextColor(SUB[1], SUB[2], SUB[3])
    else
        r.name:SetTextColor(TXT[1], TXT[2], TXT[3])
    end
    r:Show()
end

local win
local card
local toast
local rowsWin = {}
local rowsCard = {}
local selCard = {}

local function SavePos(f, key)
    local p, _, _, x, y = f:GetPoint(1)
    if not p or type(x) ~= "number" or type(y) ~= "number" then return end
    SR.DB()[key] = { p = p, x = x, y = y }
end

local function LoadPos(f, key)
    local v = SR.DB()[key]
    if type(v) == "table" and type(v.p) == "string" and type(v.x) == "number" then
        f:ClearAllPoints()
        f:SetPoint(v.p, UIParent, v.p, v.x, v.y or 0)
        return true
    end
    return false
end

local function PendingRows()
    local out = {}
    for _, row in ipairs(SR.Scan().rows) do
        if not row.white then out[#out + 1] = row end
    end
    return out
end

local function ReplaceableRows()
    local out = {}
    for _, row in ipairs(SR.Scan().rows) do
        if not row.white and not row.noBar and #(row.slots or {}) > 0 then out[#out + 1] = row end
    end
    return out
end

local function WhiteRows()
    local out = {}
    local w = SR.DB().whitelist
    local total = SR.Scan()
    local known = {}
    for _, row in ipairs(total.rows) do known[row.key] = row end
    for key, ts in pairs(w) do
        local hit = known[key]
        if hit then
            out[#out + 1] = {
                key = key,
                name = hit.name,
                icon = hit.icon,
                bestId = hit.bestId,
                slots = hit.slots,
                slotText = SlotText(hit.slots),
                from = hit.from,
                to = hit.to,
                checked = false,
                white = true,
            }
        else
            local nm = type(key) == "string" and key or nil
            local id = type(key) == "number" and key or nil
            out[#out + 1] = {
                key = key,
                name = nm or SR.SpellName(id) or L["未知法术"],
                icon = id and SR.SpellIcon(id) or "Interface\\Icons\\INV_Misc_QuestionMark",
                bestId = id,
                slots = {},
                slotText = L["未上动作条"],
                checked = false,
                white = true,
            }
        end
    end
    table.sort(out, function(a, b) return (a.name or "") < (b.name or "") end)
    return out
end

local RefreshWin

local viewKept = false

local function CardButton(parent, text, w)
    local b = ns.CreateButton(parent)
    b:SetSize(w or BTN_W, BTN_H)
    b:SetText(text or "")
    local fs = b:GetFontString()
    if fs then
        fs:ClearAllPoints()
        fs:SetPoint("CENTER", b, "CENTER", 0, 0)
        fs:SetJustifyH("CENTER")
        fs:SetFont(ns.FONT, 14, "")
    end
    b:SetPushedTextOffset(0, 0)
    return b
end

local function CloseButton(parent)
    local close = CreateFrame("Button", nil, parent, "BackdropTemplate")
    close:SetSize(32, 32)
    close:SetPoint("TOPRIGHT", parent, "TOPRIGHT", -4, -4)
    close:SetHitRectInsets(-3, -3, -3, -3)
    if ns.hui and ns.hui.SkinButton then ns.hui.SkinButton(close, { noFrame = true }) end
    local gray = 0xa0 / 255
    local it = close:CreateTexture(nil, "ARTWORK")
    it:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\textures\\YY_close")
    it:SetSize(20, 20)
    it:SetPoint("CENTER", close, "CENTER", 0, 0)
    it:SetVertexColor(gray, gray, gray)
    close:HookScript("OnEnter", function() it:SetVertexColor(1, 1, 1) end)
    close:HookScript("OnLeave", function() it:SetVertexColor(gray, gray, gray) end)
    return close
end

local function MakeActRow(parent, w)
    local r = CreateFrame("Button", nil, parent)
    r:SetSize(w, ROW_H)
    r:RegisterForClicks("LeftButtonUp")
    if ns.hui and ns.hui.HuiCardFX then ns.hui.HuiCardFX(r, 6, 2) end
    r.iconBox = CreateFrame("Frame", nil, r)
    r.iconBox:SetSize(32, 32)
    r.iconBox:SetPoint("LEFT", r, "LEFT", 12, 0)
    r.icon = r.iconBox:CreateTexture(nil, "ARTWORK")
    r.icon:SetAllPoints()
    r.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
    if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(r.icon) end
    r.name = FS(r, 14, TXT, "LEFT")
    r.name:SetPoint("TOPLEFT", r, "TOPLEFT", 52, -6)
    r.name:SetWordWrap(false)
    r.sub = FS(r, 12, SUB, "LEFT")
    r.sub:SetPoint("TOPLEFT", r, "TOPLEFT", 52, -26)
    r.sub:SetWordWrap(false)
    r.rank = FS(r, 14, TXT, "RIGHT")
    r.rank:SetPoint("RIGHT", r, "RIGHT", -148, 0)
    r.rank:SetWordWrap(false)
    r.bDo = CardButton(r, L["替换"], BTN_W)
    r.bDo:SetPoint("RIGHT", r, "RIGHT", -80, 0)
    r.bKeep = CardButton(r, L["保留"], BTN_W)
    r.bKeep:SetPoint("RIGHT", r, "RIGHT", -12, 0)
    r:SetScript("OnEnter", function(self)
        if ns.hui and ns.hui.HuiCardState then ns.hui.HuiCardState(self, "hover") end
        ShowSpellTip(self, self.data)
    end)
    r:SetScript("OnLeave", function(self)
        if ns.hui and ns.hui.HuiCardState then ns.hui.HuiCardState(self, "norm") end
        GameTooltip:Hide()
    end)
    r:SetScript("OnClick", function()
        if r.__act then r.__act() end
    end)
    r.bDo:SetScript("OnClick", function()
        if r.__do then r.__do() end
    end)
    r.bKeep:SetScript("OnClick", function()
        if r.__keep then r.__keep() end
    end)
    r:Hide()
    return r
end

local function BuildBar(holder)
    local track = CreateFrame("Frame", nil, holder)
    track:SetSize(7, LIST_H - 4)
    track:SetPoint("TOPLEFT", holder, "TOPRIGHT", 0, -2)
    track:SetFrameLevel(holder:GetFrameLevel() + 10)
    if ns.hui and ns.hui.BuildCapsule and LAYER.L2 then
        ns.hui.BuildCapsule(track, 3, LAYER.L2, 0)
    end
    local thumb = CreateFrame("Frame", nil, holder)
    thumb:SetSize(5, 24)
    thumb:SetFrameLevel(holder:GetFrameLevel() + 11)
    if ns.hui and ns.hui.BuildCapsule and LAYER.L4 then
        ns.hui.BuildCapsule(thumb, 2, LAYER.L4, 0)
    end
    track:Hide()
    thumb:Hide()
    return track, thumb
end

local function BuildWin()
    local f = CreateFrame("Frame", "DungeonsForeverSpellRankFrame", UIParent, "BackdropTemplate")
    f:SetSize(WIN_W, WIN_H)
    f:SetFrameStrata("DIALOG")
    f:EnableMouse(true)
    f:SetMovable(true)
    f:SetClampedToScreen(true)
    f:RegisterForDrag("LeftButton")
    f:SetScript("OnDragStart", f.StartMoving)
    f:SetScript("OnDragStop", function(self)
        self:StopMovingOrSizing()
        SavePos(self, "winPos")
    end)
    if ns.hui and ns.hui.SkinPopup and LAYER.L0 then
        ns.hui.SkinPopup(f, 8, nil, LAYER.L0)
    else
        f:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8x8", edgeFile = "Interface\\Buttons\\WHITE8x8", edgeSize = 1 })
        f:SetBackdropColor(0.039, 0.047, 0.063, 1)
        f:SetBackdropBorderColor(1, 1, 1, 0.12)
    end
    if not LoadPos(f, "winPos") then f:SetPoint("CENTER", UIParent, "CENTER", 0, 40) end

    f.logo = f:CreateTexture(nil, "ARTWORK")
    f.logo:SetTexture(LOGO_TEX)
    f.logo:SetSize(30, 30)
    f.logo:SetPoint("LEFT", f, "TOPLEFT", 12, -20)
    f.title = FS(f, 16, TXT, "LEFT")
    f.title:SetPoint("LEFT", f, "TOPLEFT", 50, -20)
    f.title:SetText(L["法术管理"])
    f.count = FS(f, 14, GOLD, "LEFT")
    f.count:SetPoint("LEFT", f.title, "RIGHT", 8, 0)

    local close = CloseButton(f)
    close:SetScript("OnClick", function() f:Hide() end)

    f.gear = CreateFrame("Button", nil, f)
    f.gear:SetSize(32, 32)
    f.gear:SetPoint("RIGHT", close, "LEFT", 0, 0)
    f.gear.tex = f.gear:CreateTexture(nil, "ARTWORK")
    f.gear.tex:SetTexture(ns.SET_ICON or "Interface\\AddOns\\DungeonsForever\\Media\\textures\\DF_Settings")
    f.gear.tex:SetSize(16, 16)
    f.gear.tex:SetPoint("CENTER")

    f.check = CardButton(f, L["检查"], 60)
    f.check:SetPoint("RIGHT", f.gear, "LEFT", -8, 0)
    f.check:SetScript("OnClick", function()
        ns.PlaySound(1)
        SR.ReportDiagnose()
    end)

    local holder = CreateFrame("Frame", nil, f)
    holder:SetSize(WIN_W - 24, LIST_H)
    holder:SetPoint("TOPLEFT", f, "TOPLEFT", 12, -44)
    local sf = CreateFrame("ScrollFrame", nil, holder)
    sf:SetSize(WIN_W - 24, LIST_H)
    sf:SetPoint("TOPLEFT", holder, "TOPLEFT", 0, 0)
    sf:EnableMouseWheel(true)
    local child = CreateFrame("Frame", nil, sf)
    child:SetWidth(WIN_W - 24)
    child:SetHeight(10)
    sf:SetScrollChild(child)
    f.scroll = sf
    f.child = child
    local track, thumb = BuildBar(holder)
    f.track = track
    f.thumb = thumb
    local dragging

    local function UpdateBar()
        local ch = child:GetHeight() or 0
        local vh = LIST_H
        if ch <= vh + 2 then
            track:Hide()
            thumb:Hide()
            return
        end
        track:Show()
        local th = math.max(24, math.floor((LIST_H - 4) * vh / ch))
        thumb:SetHeight(th)
        thumb:Show()
        local v = sf:GetVerticalScroll() or 0
        if type(v) ~= "number" then v = 0 end
        local maxv = math.max(1, ch - vh)
        local frac = math.min(1, math.max(0, v / maxv))
        thumb:ClearAllPoints()
        thumb:SetPoint("TOP", track, "TOP", 0, -1 - frac * ((LIST_H - 4) - th))
    end
    f.UpdateBar = UpdateBar

    local function DoScroll(v)
        local ch = child:GetHeight() or 0
        local maxv = math.max(0, ch - LIST_H)
        if v < 0 then v = 0 end
        if type(v) ~= "number" then v = 0 end
        if v > maxv then v = maxv end
        sf:SetVerticalScroll(v)
        UpdateBar()
    end

    sf:SetScript("OnMouseWheel", function(_, delta)
        DoScroll((sf:GetVerticalScroll() or 0) - delta * 46)
    end)

    thumb:EnableMouse(true)
    thumb:SetScript("OnMouseDown", function()
        dragging = { y = select(2, GetCursorPosition()), v = sf:GetVerticalScroll() or 0 }
        thumb:SetScript("OnUpdate", function()
            if not dragging then return end
            local ch = child:GetHeight() or 0
            local maxv = math.max(1, ch - LIST_H)
            local span = math.max(1, (LIST_H - 4) - (thumb:GetHeight() or 24))
            local dy = (select(2, GetCursorPosition()) - dragging.y) * (maxv / span)
            DoScroll(dragging.v - dy)
        end)
    end)
    thumb:SetScript("OnMouseUp", function(self) self:SetScript("OnUpdate", nil) dragging = nil end)
    thumb:SetScript("OnHide", function(self) self:SetScript("OnUpdate", nil) dragging = nil end)

    f.empty = FS(f, 14, DIM, "CENTER")
    f.empty:SetPoint("TOP", holder, "TOP", 0, -120)
    f.empty:SetWidth(WIN_W - 80)
    f.empty:SetText(L["动作条上的法术都是最高阶"])

    local halfW = math.floor((WIN_W - 24 - 8) / 2)
    f.doAll = CardButton(f, L["全部替换"], halfW)
    f.doAll:SetPoint("TOPLEFT", f, "TOPLEFT", 12, -328)
    f.doAll:SetScript("OnClick", function()
        if viewKept then
            viewKept = false
            RefreshWin()
            return
        end
        local rows = ReplaceableRows()
        if #rows > 0 then SR.Apply(rows) end
    end)

    f.manage = CardButton(f, L["白名单管理"], halfW)
    f.manage:SetPoint("LEFT", f.doAll, "RIGHT", 8, 0)
    f.manage:SetScript("OnClick", function()
        viewKept = not viewKept
        ns.PlaySound(1)
        RefreshWin()
    end)

    local pop = CreateFrame("Frame", "DungeonsForeverSpellRankSettings", f, "BackdropTemplate")
    pop:SetSize(200, 80)
    pop:SetPoint("TOPRIGHT", f, "TOPRIGHT", -12, -42)
    pop:SetFrameStrata(f:GetFrameStrata())
    pop:SetFrameLevel(f:GetFrameLevel() + 20)
    pop:EnableMouse(true)
    pop:Hide()
    if ns.hui and ns.hui.SkinPopup then ns.hui.SkinPopup(pop, 8) end
    if ns.hui and ns.hui.SkinShadow then ns.hui.SkinShadow(pop) end
    tinsert(UISpecialFrames, "DungeonsForeverSpellRankSettings")

    local catcher = CreateFrame("Frame", nil, f)
    catcher:SetAllPoints(UIParent)
    catcher:SetFrameStrata(f:GetFrameStrata())
    catcher:SetFrameLevel(f:GetFrameLevel() + 19)
    catcher:EnableMouse(true)
    catcher:Hide()

    local setRows = {}
    local function MakeSetRow(idx, label, key, hint)
        local row = CreateFrame("Button", nil, pop)
        row:SetPoint("TOPLEFT", pop, "TOPLEFT", 8, -8 - (idx - 1) * 32)
        row:SetSize(184, 32)
        row.key = key
        row.ck = MakeCheck(row, 14)
        row.ck:SetPoint("LEFT", row, "LEFT", 6, 0)
        row.label = FS(row, 14, TXT, "LEFT")
        row.label:SetPoint("LEFT", row.ck, "RIGHT", 8, 0)
        row.label:SetText(label)
        row:SetScript("OnClick", function(self)
            local v = not self.ck:IsOn()
            self.ck:SetOn(v)
            SR.Setting(self.key, v)
            ns.PlaySound(1)
        end)
        row:SetScript("OnEnter", function(self)
            GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
            GameTooltip:ClearLines()
            GameTooltip:AddLine(hint, 0.82, 0.86, 0.9, true)
            GameTooltip:Show()
        end)
        row:SetScript("OnLeave", function() GameTooltip:Hide() end)
        setRows[#setRows + 1] = row
        return row
    end
    MakeSetRow(1, L["新技能时弹窗"], "hintLearn", L["学会新技能、且动作条上有低等级、且不在白名单时弹窗"])
    MakeSetRow(2, L["登录时弹窗"], "hintLogin", L["登录时、且动作条上有低等级、且不在白名单时弹窗"])

    local function SyncSetRows()
        local db = SR.DB()
        for i = 1, #setRows do
            local r = setRows[i]
            r.ck:SetOn(db[r.key] and true or false)
        end
    end

    local function PaintGear()
        if pop:IsShown() then
            f.gear.tex:SetVertexColor(ACC[1], ACC[2], ACC[3])
        elseif f.gear.hot then
            f.gear.tex:SetVertexColor(1, 1, 1)
        else
            f.gear.tex:SetVertexColor(0.62, 0.62, 0.62)
        end
    end

    local function CloseSetPop()
        if pop:IsShown() then pop:Hide() end
        if catcher:IsShown() then catcher:Hide() end
        PaintGear()
    end

    f.gear:SetScript("OnEnter", function(self)
        self.hot = true
        PaintGear()
    end)
    f.gear:SetScript("OnLeave", function(self)
        self.hot = nil
        PaintGear()
    end)
    f.gear:SetScript("OnClick", function()
        ns.PlaySound(1)
        if pop:IsShown() then
            CloseSetPop()
        else
            SyncSetRows()
            catcher:Show()
            pop:Show()
            PaintGear()
        end
    end)
    catcher:SetScript("OnMouseDown", function() CloseSetPop() end)

    f:HookScript("OnHide", function() CloseSetPop() end)
    f:Hide()
    tinsert(UISpecialFrames, "DungeonsForeverSpellRankFrame")
    win = f
    return f
end

RefreshWin = function()
    if not win then return end
    local list = viewKept and WhiteRows() or PendingRows()
    for _, r in ipairs(rowsWin) do r:Hide() end
    local y, idx = 0, 0
    for _, data in ipairs(list) do
        idx = idx + 1
        local r = rowsWin[idx]
        if not r then
            r = MakeActRow(win.child, WIN_W - 24)
            rowsWin[idx] = r
        end
        r.data = data
        r.name:SetText(data.name or "")
        r.icon:SetTexture(data.icon or "Interface\\Icons\\INV_Misc_QuestionMark")
        r.sub:SetText(data.noBar and (data.to or L["无等级"]) or (data.slotText or SlotText(data.slots)))
        r:SetPoint("TOPLEFT", win.child, "TOPLEFT", 0, -y)
        if viewKept then
            r.rank:SetText(data.from or data.to or "")
            r.rank:SetTextColor(DIM[1], DIM[2], DIM[3])
            r.bKeep:Hide()
            r.bDo:SetWidth(76)
            r.bDo:SetPoint("RIGHT", r, "RIGHT", -12, 0)
            r.bDo:SetText(L["取消保留"])
            local function unkeep()
                SR.RemoveWhitelist({ data.key })
                SR.Say(string.format(L["已移出白名单 %d 项"], 1))
                RefreshWin()
            end
            r.bDo:SetScript("OnClick", unkeep)
            r.__do = unkeep
            r.__keep = nil
        elseif data.noBar then
            r.rank:SetText("")
            r.bDo:SetWidth(BTN_W * 2 + 8)
            r.bDo:SetPoint("RIGHT", r, "RIGHT", -12, 0)
            r.bDo:SetText(L["拖入动作条"])
            r.bDo:Show()
            r.bKeep:Hide()
            local function toBar() SR.PickupToBar(data.bestId) end
            r.bDo:SetScript("OnClick", toBar)
            r.__do = toBar
            r.__keep = nil
        else
            r.rank:SetText(RankMarkup(data.from, data.to))
            r.rank:SetTextColor(TXT[1], TXT[2], TXT[3])
            r.bDo:SetWidth(BTN_W)
            r.bDo:SetPoint("RIGHT", r, "RIGHT", -80, 0)
            r.bDo:SetText(L["替换"])
            r.bDo:Show()
            r.bKeep:Show()
            local function doIt() SR.Apply({ data }) end
            local function keepIt()
                SR.AddWhitelist({ data })
                SR.Say(string.format(L["已保留 %d 项"], 1))
                RefreshWin()
            end
            r.bDo:SetScript("OnClick", doIt)
            r.__do = doIt
            r.__keep = keepIt
        end
        r:Show()
        y = y + ROW_PITCH
    end
    win.child:SetHeight(math.max(10, y))
    win.scroll:SetVerticalScroll(0)
    if win.UpdateBar then win.UpdateBar() end

    local pend = PendingRows()
    local kept = WhiteRows()
    if viewKept then
        win.title:SetText(L["已保留的法术"])
        win.count:SetText(#kept > 0 and tostring(#kept) or "")
        win.count:SetTextColor(SUB[1], SUB[2], SUB[3])
        win.empty:SetText(L["白名单为空"])
        win.empty:SetShown(#kept == 0)
        win.doAll:ClearAllPoints()
        win.doAll:SetPoint("TOPLEFT", win, "TOPLEFT", 12, -328)
        win.doAll:SetWidth(WIN_W - 24)
        win.doAll:SetText(L["返回待升级"])
        win.manage:Hide()
        if ns.hui and ns.hui.SetButtonSelected then ns.hui.SetButtonSelected(win.doAll, false) end
    else
        local repl = #ReplaceableRows()
        local noBarN = #pend - repl
        local cnt = repl > 0 and string.format(L["%d 项可升阶"], repl) or ""
        if noBarN > 0 then
            local s2 = string.format(L["%d 项未上动作条"], noBarN)
            cnt = cnt ~= "" and (cnt .. " · " .. s2) or s2
        end
        win.title:SetText(L["法术管理"])
        win.count:SetText(cnt)
        win.count:SetTextColor(GOLD[1], GOLD[2], GOLD[3])
        win.empty:SetText(#pend == 0 and L["动作条上的法术都是最高阶"]
            or L["这些法术里的低阶已全部替换"])
        win.empty:SetShown(#pend == 0)
        win.doAll:ClearAllPoints()
        win.doAll:SetPoint("TOPLEFT", win, "TOPLEFT", 12, -328)
        win.doAll:SetWidth((WIN_W - 24 - 8) / 2)
        win.doAll:SetText(repl > 0 and string.format(L["全部替换（%d）"], repl) or L["全部替换"])
        if ns.hui and ns.hui.SetButtonSelected then
            ns.hui.SetButtonSelected(win.doAll, repl > 0, "main")
        end
        win.manage:Show()
        win.manage:SetText(#kept > 0 and string.format(L["白名单管理（%d）"], #kept) or L["白名单管理"])
    end
    return
end

UI.ShowLearn = function(rows)
    local n = #(rows or {})
    if n == 0 then return end
    if not win then BuildWin() end
    SR.Dirty()
    viewKept = false
    RefreshWin()
    win:Show()
end

local function ShowWin()
    SR.Dirty()
    if not win then BuildWin() end
    viewKept = false
    RefreshWin()
    win:Show()
end

UI.Open = function()
    ShowWin()
end
UI.Toggle = function()
    if win and win:IsShown() then
        win:Hide()
    else
        UI.Open()
    end
end
UI.IsShown = function() return win and win:IsShown() end
UI.Rows = function() return rowsWin end

local function BuildCard()
    local f = CreateFrame("Frame", "DungeonsForeverSpellRankCard", UIParent, "BackdropTemplate")
    f:SetSize(CARD_W, 240)
    f:SetPoint("TOP", UIParent, "TOP", 0, -180)
    f:SetFrameStrata("DIALOG")
    f:EnableMouse(true)
    f:SetClampedToScreen(true)
    f:SetMovable(true)
    f:RegisterForDrag("LeftButton")
    f:SetScript("OnDragStart", f.StartMoving)
    f:SetScript("OnDragStop", function(self) self:StopMovingOrSizing() end)
    if ns.hui and ns.hui.SkinPopup and LAYER.L0 then
        ns.hui.SkinPopup(f, 8, nil, LAYER.L0)
    else
        f:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8x8", edgeFile = "Interface\\Buttons\\WHITE8x8", edgeSize = 1 })
        f:SetBackdropColor(0.039, 0.047, 0.063, 1)
        f:SetBackdropBorderColor(1, 1, 1, 0.12)
    end
    f.logo = f:CreateTexture(nil, "ARTWORK")
    f.logo:SetTexture(LOGO_TEX)
    f.logo:SetSize(30, 30)
    f.logo:SetPoint("LEFT", f, "TOPLEFT", 12, -20)
    f.title = FS(f, 16, TXT, "LEFT")
    f.title:SetPoint("LEFT", f, "TOPLEFT", 50, -20)
    f.title:SetText(L["法术管理"])
    f.sub = FS(f, 14, SUB, "LEFT")
    f.sub:SetPoint("LEFT", f.title, "RIGHT", 8, 0)
    local close = CloseButton(f)
    close:SetScript("OnClick", function() f:Hide() end)

    f.host = CreateFrame("Frame", nil, f)
    f.host:SetSize(CARD_W - 24, 10)
    f.host:SetPoint("TOPLEFT", f, "TOPLEFT", 12, -40)

    f.tip = FS(f, 14, DIM, "LEFT")
    f.tip:SetPoint("BOTTOMLEFT", f, "BOTTOMLEFT", 18, 74)
    f.tip:SetWidth(CARD_W - 36)
    f.tip:SetWordWrap(true)

    f.mainBtn = CardButton(f, L["全部替换"], CARD_W - 24)
    f.mainBtn:SetPoint("BOTTOMLEFT", f, "BOTTOMLEFT", 12, 40)
    f.mainBtn:SetScript("OnClick", function()
        local rows = {}
        for _, row in ipairs(selCard) do
            if row.checked then rows[#rows + 1] = row end
        end
        if #rows > 0 then
            SR.Apply(rows)
            f:Hide()
        end
    end)

    f.ignoreBtn = CardButton(f, L["本次忽略"], (CARD_W - 32) / 2)
    f.ignoreBtn:SetPoint("BOTTOMLEFT", f, "BOTTOMLEFT", 12, 8)
    f.ignoreBtn:SetScript("OnClick", function()
        SR.NoteIgnore(selCard)
        f:Hide()
    end)

    f.whiteBtn = CardButton(f, L["忽略并加入白名单"], (CARD_W - 32) / 2)
    f.whiteBtn:SetPoint("LEFT", f.ignoreBtn, "RIGHT", 8, 0)
    f.whiteBtn:SetScript("OnClick", function()
        local rows = {}
        for _, row in ipairs(selCard) do
            if row.checked then rows[#rows + 1] = row end
        end
        local n = SR.AddWhitelist(rows)
        if n > 0 then SR.Say(string.format(L["已加入白名单 %d 项"], n)) end
        for _, row in ipairs(selCard) do SR.NoteIgnore({ row }) end
        f:Hide()
    end)

    f:Hide()
    card = f
    return f
end

UI.ShowCard = function(rows)
    if not card then BuildCard() end
    for _, r in ipairs(rowsCard) do r:Hide() end
    selCard = {}
    local list = rows or {}
    local shown, y = 0, 0
    for _, row in ipairs(list) do
        if shown >= 6 then break end
        shown = shown + 1
        local r = rowsCard[shown]
        if not r then
            r = MakeRow(card.host, CARD_W - 28, MODE_PENDING)
            rowsCard[shown] = r
        end
        local data = {
            key = row.key,
            name = row.name,
            icon = row.icon,
            slots = row.slots,
            from = row.from,
            to = row.to,
            white = row.white,
            checked = not row.white,
        }
        data.sub = SlotText(row.slots)
        selCard[#selCard + 1] = data
        PaintRow(r, {
            name = data.name,
            sub = data.sub,
            icon = data.icon,
            from = data.from,
            to = data.to,
            checked = data.checked,
            white = data.white,
            slots = data.slots,
        }, MODE_PENDING)
        r:SetPoint("TOPLEFT", card.host, "TOPLEFT", 0, -y)
        r.onToggle = function()
            data.checked = r.ck:IsOn()
            local n = 0
            for _, row2 in ipairs(selCard) do
                if row2.checked then n = n + 1 end
            end
            card.mainBtn:SetText(n == 0 and L["全部替换"] or string.format(L["全部替换（%d）"], n))
        end
        y = y + ROW_PITCH
    end
    card.host:SetHeight(math.max(10, y))
    card.sub:SetText(string.format(L["%d 项 · %d 个槽位"], #list, (function()
        local n = 0
        for _, row in ipairs(list) do n = n + #(row.slots or {}) end
        return n
    end)()))
    local extra = #list - shown
    if extra > 0 then
        card.tip:SetText(string.format(L["另有 %d 项，可在管理窗口里查看"], extra))
    else
        card.tip:SetText(L["勾选的项参与下面的操作"])
    end
    card.mainBtn:SetText(string.format(L["全部替换（%d）"], #selCard))
    card:SetHeight(40 + math.max(10, y) + 14 + 74)
    card:ClearAllPoints()
    card:SetPoint("TOP", UIParent, "TOP", 0, -180)
    card:Show()
end

local entry
local entryHost
local entryWatch
local entryPage
local RefreshEntry
local UpdateEntry

local function IsVis(f)
    if not f then return false end
    local ok, v = pcall(f.IsVisible, f)
    return ok and v and true or false
end

local function InCombat()
    if type(InCombatLockdown) ~= "function" then return false end
    local ok, v = pcall(InCombatLockdown)
    return ok and v or false
end

local function FrameLvl(f)
    if not f then return 0 end
    local ok, v = pcall(f.GetFrameLevel, f)
    if ok and type(v) == "number" then return v end
    return 0
end

local function PagedFrame()
    local psf = PlayerSpellsFrame
    local sb = psf and psf.SpellBookFrame
    return (sb and sb.PagedSpellsFrame) or nil
end

local function HostChain()
    local nb = ns.NativeSpellBook
    local seed = entry and entry.__box or nil
    if not seed then seed = nb and nb.ContentBox and nb.ContentBox() or nil end
    if not seed then
        local psf = PlayerSpellsFrame
        local sb = psf and psf.SpellBookFrame
        seed = PagedFrame() or sb or psf
    end
    if not seed and type(SpellBookFrame) == "table" then seed = SpellBookFrame end
    local out = {}
    local f, guard = seed, 0
    while f and guard < 16 do
        guard = guard + 1
        if f ~= UIParent and f ~= WorldFrame then out[#out + 1] = f end
        local ok, p = pcall(f.GetParent, f)
        if not (ok and p) then break end
        f = p
    end
    return out
end

local function PickHost()
    local chain = HostChain()
    local n = #chain
    if n == 0 then return nil, nil end
    local host
    for i = n, 1, -1 do
        if IsVis(chain[i]) then
            host = chain[i]
            break
        end
    end
    return host or chain[n], chain[1]
end

local function HookWatch(f)
    if not (f and f.HookScript) or f.__rankHooked then return end
    f.__rankHooked = true
    f:HookScript("OnShow", function()
        if C_Timer and C_Timer.After then
            C_Timer.After(0.1, function() UpdateEntry() end)
        else
            UpdateEntry()
        end
    end)
    f:HookScript("OnHide", function() RefreshEntry() end)
end

local function BookFrame()
    local psf = PlayerSpellsFrame
    return psf and psf.SpellBookFrame or nil
end

local function BoxAnchor()
    local nb = ns.NativeSpellBook
    if nb and nb.ContentBox then
        local b = nb.ContentBox()
        if b then return b end
    end
    return nil
end

local function AdoptBox()
    if not entry or entry.__box then return entry and entry.__box or nil end
    local nb = ns.NativeSpellBook
    local b = nb and nb.ContentBox and nb.ContentBox() or nil
    if not b then return nil end
    entry.__box = b
    entry:ClearAllPoints()
    entry:SetPoint("BOTTOMRIGHT", b, "BOTTOMLEFT", -6, 0)
    HookWatch(b)
    return b
end

local function PageNow()
    local nb = ns.NativeSpellBook
    if nb and nb.CurrentPage then
        local p = nb.CurrentPage()
        if p ~= nil then return p end
    end
    return entryPage
end

local function AnchorFrame()
    return BoxAnchor() or PagedFrame() or entryHost
end

local function AnchorEntry()
    if not entry then return end
    local anch = AnchorFrame()
    entry:ClearAllPoints()
    if anch then
        entry:SetPoint("BOTTOMRIGHT", anch, "BOTTOMLEFT", -6, 0)
    elseif entryHost then
        entry:SetPoint("BOTTOMLEFT", entryHost, "BOTTOMLEFT", 10, 2)
    end
end

RefreshEntry = function()
    if not entry then return false end
    HookWatch(BookFrame())
    local host = PickHost()
    if host and host ~= entryHost then
        entryHost = host
        if not InCombat() and entry:GetParent() ~= host then entry:SetParent(host) end
        AnchorEntry()
        entry:SetFrameLevel(math.max(FrameLvl(host), FrameLvl(AnchorFrame())) + 5)
        HookWatch(host)
    end
    if not entryHost then return false end
    AdoptBox()
    local par = entry:GetParent()
    local page = PageNow()
    local box = BoxAnchor()
    local inBook = (box == nil) or IsVis(box)
    local vis = IsVis(entryHost) and par ~= nil and IsVis(par) and page == "spell" and inBook
    vis = vis and true or false
    if entry:IsShown() ~= vis then entry:SetShown(vis) end
    return vis
end

local ENTRY_TEXT = "法术管理"

local function PaintEntry(n)
    if not entry then return end
    local txt = L[ENTRY_TEXT]
    if n and n > 0 then txt = txt .. "（" .. n .. "）" end
    entry.label:SetText(txt)
    local ok, w = pcall(entry.label.GetStringWidth, entry.label)
    if ok and type(w) == "number" and w > 0 then
        entry:SetWidth(math.max(186, math.floor(w) + 20))
    else
        entry:SetWidth(320)
    end
end

local function EnsureEntry()
    if entry then
        RefreshEntry()
        return true
    end
    local host, watch = PickHost()
    if not host then return false end
    local bt = CreateFrame("Button", nil, host, "UIPanelButtonTemplate")
    bt:SetSize(320, 32)
    bt:SetFrameLevel(math.max(FrameLvl(host), FrameLvl(BoxAnchor() or PagedFrame())) + 5)
    bt:SetText("")
    local fs = bt:CreateFontString(nil, "OVERLAY")
    fs:SetFont(ns.FONT, 13, "")
    fs:SetPoint("CENTER", bt, "CENTER", 0, 0)
    fs:SetText("")
    bt.label = fs
    bt:SetScript("OnClick", function()
        ns.PlaySound(1)
        UI.Toggle()
    end)
    if ns.NDuiOn and ns.NDuiOn() then ns.NDuiReskin(bt) end
    bt:Hide()
    entry = bt
    entryHost = host
    entryWatch = watch
    AnchorEntry()
    HookWatch(host)
    if watch and watch ~= host then HookWatch(watch) end
    HookWatch(BookFrame())
    PaintEntry(0)
    local acc = 0
    local dog = CreateFrame("Frame")
    dog:SetScript("OnUpdate", function(_, elapsed)
        acc = acc + elapsed
        if acc < 0.5 then return end
        acc = 0
        UpdateEntry()
    end)
    RefreshEntry()
    return true
end

local function PageHook()
    local nb = ns.NativeSpellBook
    if not nb then return false end
    if nb.__rankWrap and nb.OnPage == nb.__rankWrap then return true end
    local prev = nb.OnPage
    if prev == nb.__rankWrap then prev = nil end
    local function wrap(p)
        if prev then prev(p) end
        UpdateEntry()
    end
    nb.OnPage = wrap
    nb.__rankWrap = wrap
    return true
end

UpdateEntry = function()
    EnsureEntry()
    PageHook()
    if not entry then return end
    local n = SR.Pending()
    PaintEntry(n)
    local p = (ns.NativeSpellBook and ns.NativeSpellBook.CurrentPage and ns.NativeSpellBook.CurrentPage()) or nil
    if p ~= entryPage then
        entryPage = p
        entry.__hdr = nil
    end
    RefreshEntry()
end

UI.Refresh = function()
    UpdateEntry()
    if win and win:IsShown() then RefreshWin() end
end

UI.OnPage = function()
    UpdateEntry()
end

UI.Debug = function()
    local psf = PlayerSpellsFrame
    local sb = psf and psf.SpellBookFrame
    local nb = ns.NativeSpellBook
    local lines = {
        "PlayerSpellsFrame = " .. tostring(psf ~= nil),
        "SpellBookFrame = " .. tostring(sb ~= nil),
        "SearchBox = " .. tostring(sb and sb.SearchBox ~= nil),
        "PagedSpellsFrame = " .. tostring(sb and sb.PagedSpellsFrame ~= nil),
        "NativeSpellBook = " .. tostring(nb ~= nil),
        "CurrentPage = " .. tostring(nb and nb.CurrentPage and nb.CurrentPage() or nil),
        "host = " .. tostring(entryHost ~= nil),
        "host visible = " .. tostring(entryHost ~= nil and entryHost:IsVisible() or false),
        "host name = " .. tostring(entryHost and entryHost:GetName() or nil),
        "parent name = " .. tostring(entry and entry:GetParent() and entry:GetParent():GetName() or nil),
        "content box = " .. tostring(entryWatch ~= nil),
        "page = " .. tostring(entryPage),
        "OnPage hooked = " .. tostring(nb ~= nil and nb.OnPage ~= nil),
        "entry = " .. tostring(entry ~= nil),
        "entry shown = " .. tostring(entry ~= nil and entry:IsShown() or false),
        "pending = " .. tostring(SR.Pending()),
    }
    for i = 1, #lines do SR.Say(lines[i]) end
end

local function Register()
    PageHook()
    SR.OnChanged = function() UI.Refresh() end
    SR.OnLogin = function(rows) UI.ShowCard(rows) end
    SR.OnLearn = function(rows) UI.ShowLearn(rows) end
    SR.OnQueued = function(n)
        SR.Say(string.format(L["战斗中不能改动作条，%d 项已排队"], n))
    end
    SR.OnFlushed = function(done)
        if done and done > 0 then
            SR.Say(string.format(L["排队中的 %d 项已升级"], done))
        end
        UI.Refresh()
    end
    SR.Boot()
    local f = CreateFrame("Frame")
    f:RegisterEvent("PLAYER_ENTERING_WORLD")
    f:RegisterEvent("ADDON_LOADED")
    f:SetScript("OnEvent", function()
        if C_Timer and C_Timer.After then
            C_Timer.After(1, UpdateEntry)
            C_Timer.After(3, UpdateEntry)
        else
            UpdateEntry()
        end
    end)
    local tries = 0
    local tick = CreateFrame("Frame")
    tick:SetScript("OnUpdate", function(self, elapsed)
        tries = tries + elapsed
        if entry then self:SetScript("OnUpdate", nil) return end
        if tries > 1 then
            tries = 0
            UpdateEntry()
        end
    end)
    UpdateEntry()
end

ns.Init(Register)
