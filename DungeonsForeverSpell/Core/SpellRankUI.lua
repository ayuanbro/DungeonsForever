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
local WARN = { 0.78, 0.52, 0.14 }
local LAYER = (ns.hui and ns.hui.layer) or {}

local MEDIA = "Interface\\AddOns\\DungeonsForever\\Media\\Common\\"
local TEX = {
    ring = MEDIA .. "CheckRing",
    disc = MEDIA .. "CheckDisc",
    mark = MEDIA .. "CheckMark",
}

local WIN_W, WIN_H = 460, 424
local CARD_W = 440
local ROW_H = 44
local ROW_PITCH = 46
local LIST_H = 252
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
        if self.data and self.data.name and not self.data.all then
            GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
            GameTooltip:ClearLines()
            GameTooltip:AddLine(self.data.name, 1, 1, 1)
            if self.data.from or self.data.to then
                GameTooltip:AddLine((self.data.from or "?") .. " → " .. (self.data.to or "?"), ACC[1], ACC[2], ACC[3])
            end
            if self.data.slots and #self.data.slots > 0 then
                local t = {}
                for i = 1, #self.data.slots do
                    local b = SR.BindFor(self.data.slots[i])
                    t[i] = b and (self.data.slots[i] .. " (" .. b .. ")") or tostring(self.data.slots[i])
                end
                GameTooltip:AddLine(L["槽位"] .. " " .. table.concat(t, "、"), 0.82, 0.86, 0.9, true)
            end
            GameTooltip:Show()
        end
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

local function MakeToggle(parent, label, key)
    local tg = CreateFrame("CheckButton", nil, parent)
    tg:SetSize(36, 20)
    tg:EnableMouse(true)
    if ns.hui and ns.hui.ReskinToggle then ns.hui.ReskinToggle(tg) end
    tg:SetChecked(SR.DB()[key] and true or false)
    tg:SetScript("OnClick", function(self)
        SR.Setting(key, self:GetChecked() and true or false)
    end)
    tg.label = FS(parent, 14, SUB, "LEFT")
    tg.label:SetPoint("LEFT", tg, "RIGHT", 7, 0)
    tg.label:SetText(label)
    return tg
end

local function PendingRows()
    local out = {}
    for _, row in ipairs(SR.Scan().rows) do
        if not row.white then out[#out + 1] = row end
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
local SetBanner

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
        if self.data and self.data.name then
            GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
            GameTooltip:ClearLines()
            GameTooltip:AddLine(self.data.name, 1, 1, 1)
            if self.data.from or self.data.to then
                GameTooltip:AddLine((self.data.from or "?") .. " → " .. (self.data.to or "?"), ACC[1], ACC[2], ACC[3])
            end
            if self.data.slots and #self.data.slots > 0 then
                GameTooltip:AddLine(L["槽位"] .. " " .. table.concat(self.data.slots, "、"), 0.82, 0.86, 0.9, true)
            end
            GameTooltip:Show()
        end
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

    f.title = FS(f, 16, TXT, "LEFT")
    f.title:SetPoint("LEFT", f, "TOPLEFT", 18, -20)
    f.title:SetText(L["法术升级管理"])
    f.count = FS(f, 14, SUB, "LEFT")
    f.count:SetPoint("LEFT", f.title, "RIGHT", 8, 0)

    local close = CloseButton(f)
    close:SetScript("OnClick", function() f:Hide() end)

    f.check = CardButton(f, L["检查"], 60)
    f.check:SetPoint("RIGHT", close, "LEFT", -8, 0)
    f.check:SetScript("OnClick", function()
        ns.PlaySound(1)
        SR.ReportDiagnose()
    end)

    f.banner = FS(f, 14, ACC, "LEFT")
    f.banner:SetPoint("TOPLEFT", f, "TOPLEFT", 18, -44)
    f.banner:SetWordWrap(false)
    f.banner:SetWidth(WIN_W - 36)
    f.banner:Hide()

    local holder = CreateFrame("Frame", nil, f)
    holder:SetSize(WIN_W - 24, LIST_H)
    holder:SetPoint("TOPLEFT", f, "TOPLEFT", 12, -68)
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
    f.empty:SetPoint("TOP", holder, "TOP", 0, -80)
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
        local rows = PendingRows()
        if #rows > 0 then SR.Apply(rows) end
    end)

    f.manage = CardButton(f, L["白名单管理"], halfW)
    f.manage:SetPoint("LEFT", f.doAll, "RIGHT", 8, 0)
    f.manage:SetScript("OnClick", function()
        viewKept = not viewKept
        ns.PlaySound(1)
        RefreshWin()
    end)

    local tgTop = -368
    f.tgh = MakeToggle(f, L["新技能时弹窗"], "hintLearn")
    f.tgh:SetPoint("TOPLEFT", f, "TOPLEFT", 18, tgTop)
    f.tgl = MakeToggle(f, L["登录时弹窗"], "hintLogin")
    f.tgl:SetPoint("TOPLEFT", f, "TOPLEFT", 240, tgTop)

    local function tip(tg, txt)
        tg:SetScript("OnEnter", function(self)
            GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
            GameTooltip:ClearLines()
            GameTooltip:AddLine(txt, 1, 1, 1, true)
            GameTooltip:Show()
        end)
        tg:SetScript("OnLeave", function() GameTooltip:Hide() end)
    end
    tip(f.tgh, L["学会新技能、且动作条上有低等级、且不在白名单时弹窗"])
    tip(f.tgl, L["登录时、且动作条上有低等级、且不在白名单时弹窗"])

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
        r.sub:SetText(data.slotText or SlotText(data.slots))
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
        else
            r.rank:SetText(RankMarkup(data.from, data.to))
            r.rank:SetTextColor(TXT[1], TXT[2], TXT[3])
            r.bDo:SetWidth(BTN_W)
            r.bDo:SetPoint("RIGHT", r, "RIGHT", -80, 0)
            r.bDo:SetText(L["替换"])
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
        win.empty:SetText(L["白名单为空"])
        win.empty:SetShown(#kept == 0)
        win.doAll:ClearAllPoints()
        win.doAll:SetPoint("TOPLEFT", win, "TOPLEFT", 12, -328)
        win.doAll:SetWidth(WIN_W - 24)
        win.doAll:SetText(L["返回待升级"])
        win.manage:Hide()
        if ns.hui and ns.hui.SetButtonSelected then ns.hui.SetButtonSelected(win.doAll, false) end
    else
        win.title:SetText(L["法术升级管理"])
        win.count:SetText(#pend > 0 and string.format(L["%d 项可升阶"], #pend) or "")
        win.empty:SetText(#pend == 0 and L["动作条上的法术都是最高阶"]
            or L["这些法术里的低阶已全部替换"])
        win.empty:SetShown(#pend == 0)
        win.doAll:ClearAllPoints()
        win.doAll:SetPoint("TOPLEFT", win, "TOPLEFT", 12, -328)
        win.doAll:SetWidth((WIN_W - 24 - 8) / 2)
        win.doAll:SetText(#pend > 0 and string.format(L["全部替换（%d）"], #pend) or L["全部替换"])
        if ns.hui and ns.hui.SetButtonSelected then
            ns.hui.SetButtonSelected(win.doAll, #pend > 0, "main")
        end
        win.manage:Show()
        win.manage:SetText(#kept > 0 and string.format(L["白名单管理（%d）"], #kept) or L["白名单管理"])
    end
    return
end

SetBanner = function(txt)
    if not win or not win.banner then return end
    win.banner:SetText(txt or "")
    win.banner:SetShown(txt ~= nil and txt ~= "")
end

UI.ShowLearn = function(rows)
    local n = #(rows or {})
    if n == 0 then return end
    if not win then BuildWin() end
    local txt
    if n == 1 then
        local r = rows[1]
        txt = string.format("%s　%s → %s", r.name or "?", r.from or "?", r.to or "?")
    else
        local names = {}
        for i = 1, math.min(n, 3) do names[i] = rows[i].name or "?" end
        txt = table.concat(names, "、") .. (n > 3 and "…" or "")
    end
    SR.Dirty()
    viewKept = false
    RefreshWin()
    SetBanner(string.format(L["刚学会：%s"], txt))
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
    if win then SetBanner(nil) end
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
    f.title = FS(f, 16, TXT, "LEFT")
    f.title:SetPoint("LEFT", f, "TOPLEFT", 18, -20)
    f.title:SetText(L["法术升级管理"])
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

local function PickSpellbook()
    local psf = PlayerSpellsFrame
    if psf and psf.SpellBookFrame and psf.SpellBookFrame.PagedSpellsFrame then
        return psf.SpellBookFrame, psf
    end
    if psf and psf.SpellBookFrame then return psf.SpellBookFrame, psf end
    if type(SpellBookFrame) == "table" and SpellBookFrame then return SpellBookFrame, psf end
    if psf then return psf, psf end
    return nil, nil
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

RefreshEntry = function()
    if not entry then return false end
    AdoptBox()
    local vis = entryHost ~= nil and entryHost:IsVisible() and entryPage ~= "weapon"
    entry:SetShown(vis and true or false)
    return vis and true or false
end

local ENTRY_TEXT = "技能升级时动作条上的低等级技能自动替换"

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
    if entry then return RefreshEntry() end
    local host, watch = PickSpellbook()
    if not host then return false end
    local paged = host.PagedSpellsFrame
    local bt = CreateFrame("Button", nil, paged or host, "UIPanelButtonTemplate")
    bt:SetSize(320, 32)
    bt:SetFrameLevel((bt:GetParent():GetFrameLevel() or 1) + 5)
    bt:SetText("")
    local fs = bt:CreateFontString(nil, "OVERLAY")
    fs:SetFont(ns.FONT, 13, "")
    fs:SetPoint("CENTER", bt, "CENTER", 0, 0)
    fs:SetText("")
    bt.label = fs
    if paged then
        bt:SetPoint("BOTTOMRIGHT", BoxAnchor() or paged, "BOTTOMLEFT", -6, 0)
    else
        bt:SetPoint("BOTTOMLEFT", host, "BOTTOMLEFT", 10, 2)
    end
    bt:SetScript("OnClick", function()
        ns.PlaySound(1)
        UI.Toggle()
    end)
    bt:Hide()
    entry = bt
    entryHost = host
    entryWatch = watch
    HookWatch(host)
    if watch ~= host then HookWatch(watch) end
    PaintEntry(0)
    local acc, life = 0, 0
    local dog = CreateFrame("Frame")
    dog:SetScript("OnUpdate", function(self, elapsed)
        acc = acc + elapsed
        life = life + elapsed
        if acc < 0.5 then return end
        acc = 0
        if life > 180 then self:SetScript("OnUpdate", nil) return end
        if RefreshEntry() then self:SetScript("OnUpdate", nil) end
    end)
    return RefreshEntry()
end

UpdateEntry = function()
    if not EnsureEntry() then return end
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
    if ns.NativeSpellBook then
        ns.NativeSpellBook.OnPage = function() UpdateEntry() end
    end
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
