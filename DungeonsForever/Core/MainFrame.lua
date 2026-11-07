local _, ns = ...

if not ns.IsTitan then return end

local L = ns.L

local W, H = 1000, 708

local DF_VERSION
do
    if type(C_AddOns) == "table" and type(C_AddOns.GetAddOnMetadata) == "function" then
        DF_VERSION = C_AddOns.GetAddOnMetadata("DungeonsForever", "Version")
    end
    if (DF_VERSION == nil or DF_VERSION == "") and type(GetAddOnMetadata) == "function" then
        DF_VERSION = GetAddOnMetadata("DungeonsForever", "Version")
    end
    if type(DF_VERSION) ~= "string" or DF_VERSION == "" then DF_VERSION = nil end
end

local f = CreateFrame("Frame", "DungeonsForever_MainFrame", UIParent, "BackdropTemplate")
f:SetSize(W, H)
f:SetFrameStrata("HIGH")
f:SetToplevel(true)
f:SetMovable(true)
f:SetClampedToScreen(true)
f:EnableMouse(true)
f:RegisterForDrag("LeftButton")
f:SetPoint("CENTER")
f:Hide()

f:EnableKeyboard(true)
f:SetScript("OnKeyDown", function(self, key)
    if type(InCombatLockdown) == "function" and InCombatLockdown() then return end
    if key == "ESCAPE" and self:IsShown() then
        self:SetPropagateKeyboardInput(false)
        if not (ns.GearDismissPopups and ns.GearDismissPopups()) then
            self:Hide()
        end
    else
        self:SetPropagateKeyboardInput(true)
    end
end)

ns.MainFrame = f
ns.TalentSimFrame = f

do
    if ns.hui and ns.hui.SkinPopup then
        ns.hui.SkinPopup(f, 8, nil, ns.hui.layer and ns.hui.layer.L0 or nil)
    else
        f:SetBackdrop({
            bgFile = "Interface\\Buttons\\WHITE8x8",
            edgeFile = "Interface\\Buttons\\WHITE8x8",
            edgeSize = 1,
        })
        f:SetBackdropColor(0x10 / 255, 0x13 / 255, 0x1A / 255, 0.95)
        f:SetBackdropBorderColor(1, 1, 1, 0.10)
    end
end

local title = f:CreateFontString(nil, "OVERLAY")
title:SetFont(ns.FONT, 15, "")
title:SetPoint("TOPLEFT", f, "TOPLEFT", 18, -4)
title:SetText(L["无限副本手册"])
title:SetTextColor(0.95, 0.96, 0.98)

local subtitle = f:CreateFontString(nil, "OVERLAY")
subtitle:SetFont(ns.FONT, 11, "")
subtitle:SetPoint("LEFT", title, "RIGHT", 10, 0)
subtitle:SetText("DungeonsForever" .. (DF_VERSION and (" v" .. DF_VERSION) or ""))
subtitle:SetTextColor(0.55, 0.62, 0.70)

local close = CreateFrame("Button", nil, f, "BackdropTemplate")
close:SetSize(32, 32)
close:SetFrameLevel(510)
close:SetPoint("TOPRIGHT", f, "TOPRIGHT", -4, -4)
close:SetHitRectInsets(-3, -3, -3, -3)
if ns.hui and ns.hui.SkinButton then ns.hui.SkinButton(close, { noFrame = true }) end
do
    local gray = 0xa0 / 255
    local it = close:CreateTexture(nil, "ARTWORK")
    it:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\textures\\YY_close")
    it:SetSize(20, 20)
    it:SetPoint("CENTER")
    it:SetVertexColor(gray, gray, gray)
    close:HookScript("OnEnter", function() it:SetVertexColor(1, 1, 1) end)
    close:HookScript("OnLeave", function() it:SetVertexColor(gray, gray, gray) end)
end
close:SetScript("OnClick", function()
    ns.PlaySound(1)
    f:Hide()
end)

local aboutGlyph
local about
local aboutBuilt
local BuildAbout

local function SyncAboutGlyph()
    if not aboutGlyph then return end
    if about and about:IsShown() then
        aboutGlyph:SetVertexColor(1, 1, 1)
    else
        aboutGlyph:SetVertexColor(0.56, 0.63, 0.72)
    end
end

local aboutBtn = CreateFrame("Button", nil, f, "BackdropTemplate")
aboutBtn:SetSize(32, 32)
aboutBtn:SetFrameLevel(510)
aboutBtn:SetPoint("TOPRIGHT", f, "TOPRIGHT", -34, -4)
aboutBtn:SetHitRectInsets(-3, -3, -3, -3)
if ns.hui and ns.hui.SkinButton then ns.hui.SkinButton(aboutBtn, { noFrame = true }) end
do
    local q = aboutBtn:CreateTexture(nil, "ARTWORK")
    q:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\Brand\\HelpIcon")
    q:SetSize(14, 14)
    q:SetPoint("CENTER")
    q:SetVertexColor(0.56, 0.63, 0.72)
    aboutGlyph = q
end
aboutBtn:SetScript("OnEnter", function(self)
    aboutGlyph:SetVertexColor(1, 1, 1)
    GameTooltip:SetOwner(self, "ANCHOR_BOTTOM")
    GameTooltip:ClearLines()
    GameTooltip:AddLine(L["关于"], 1, 1, 1, true)
    GameTooltip:Show()
end)
aboutBtn:SetScript("OnLeave", function()
    GameTooltip:Hide()
    SyncAboutGlyph()
end)
aboutBtn:SetScript("OnClick", function()
    ns.PlaySound(1)
    if not aboutBuilt then
        about:Show()
        BuildAbout()
        about:Hide()
    end
    about:SetShown(not about:IsShown())
    SyncAboutGlyph()
end)

about = CreateFrame("Frame", nil, f, "BackdropTemplate")
about:SetFrameLevel(505)
about:SetAllPoints(f)
about:EnableMouse(true)
about:SetScript("OnMouseWheel", function() end)
about:SetScript("OnMouseUp", function()
    ns.PlaySound(1)
    about:Hide()
    SyncAboutGlyph()
end)
about:Hide()
if ns.hui and ns.hui.SkinPopup then
    ns.hui.SkinPopup(about, 8, nil, ns.hui.layer and ns.hui.layer.L0 or nil)
    if ns.hui.SkinShadow then ns.hui.SkinShadow(about) end
else
    about:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8x8" })
    about:SetBackdropColor(0x0A / 255, 0x0C / 255, 0x10 / 255, 1)
end

local AB_EDGE_X = 32
local AB_EDGE_B = 28
local AB_TOP = 52
local AB_GAP = 8
local AB_PAD = 8
local AB_BAR = 8
local AB_CARD_W = (W - AB_EDGE_X * 2 - AB_GAP) / 2
local AB_RIGHT_X = AB_EDGE_X + AB_CARD_W + AB_GAP
local AB_CARD_H = H - AB_TOP - AB_EDGE_B
local AB_INNER_W = AB_CARD_W - AB_PAD * 2
local AB_HDR_H = 24
local AB_COLS = 2
local AB_COL_GAP = 8
local AB_ROW_H = 26
local AB_AVAIL_W = AB_INNER_W - AB_BAR
local AB_COL_W = math.floor((AB_AVAIL_W - (AB_COLS - 1) * AB_COL_GAP) / AB_COLS)
local AB_DIV_Y = AB_PAD + AB_HDR_H + 10
local AB_GRID_TOP = AB_DIV_Y + 10
local AB_GRID_H = AB_CARD_H - AB_GRID_TOP - AB_PAD

local C_AB_VAL = { 0.88, 0.90, 0.93 }
local C_AB_DIM = { 0.62, 0.62, 0.68 }
local C_AB_HEAD = { 0.95, 0.96, 0.98 }
local C_AB_KEYHEX = "|cff8c9eb3"

local function AbAccentHex()
    local a = (ns.hui and ns.hui.ACCENT) or { 0x46 / 255, 0xbf / 255, 0x72 / 255 }
    return string.format("|cff%02x%02x%02x",
        math.floor(a[1] * 255 + 0.5), math.floor(a[2] * 255 + 0.5), math.floor(a[3] * 255 + 0.5))
end

local function AbCharLen(s)
    local i, n, len = 1, 0, #s
    while i <= len do
        local b = s:byte(i)
        if b >= 240 then i = i + 4
        elseif b >= 224 then i = i + 3
        elseif b >= 192 then i = i + 2
        else i = i + 1 end
        n = n + 1
    end
    return n
end

local function AbCharCut(s, keep)
    local i, c, len = 1, 0, #s
    while i <= len and c < keep do
        local b = s:byte(i)
        if b >= 240 then i = i + 4
        elseif b >= 224 then i = i + 3
        elseif b >= 192 then i = i + 2
        else i = i + 1 end
        c = c + 1
    end
    return s:sub(1, i - 1)
end

local function AbFit(fs, text, maxW)
    fs:SetText(text)
    local w = fs:GetStringWidth()
    if type(w) ~= "number" or w <= maxW then return end
    local lo, hi, best = 1, AbCharLen(text), 0
    while lo <= hi do
        local mid = math.floor((lo + hi) / 2)
        fs:SetText(AbCharCut(text, mid) .. "…")
        local mw = fs:GetStringWidth()
        if type(mw) == "number" and mw <= maxW then
            best = mid
            lo = mid + 1
        else
            hi = mid - 1
        end
    end
    fs:SetText(AbCharCut(text, best) .. "…")
end

function BuildAbout()
    if aboutBuilt then return end
    aboutBuilt = true

    local left = CreateFrame("Frame", nil, about, "BackdropTemplate")
    left:SetSize(AB_CARD_W, AB_CARD_H)
    left:SetPoint("TOPLEFT", about, "TOPLEFT", AB_EDGE_X, -AB_TOP)
    left:SetFrameLevel(about:GetFrameLevel() + 1)
    if left.SetBackdropColor then left:SetBackdropColor(0, 0, 0, 0) end
    if left.SetBackdropBorderColor then left:SetBackdropBorderColor(0, 0, 0, 0) end
    ns.hui.BuildRoundedBG(left, 8, ns.hui.layer.L1, "both", true)

    local icon = left:CreateTexture(nil, "ARTWORK")
    icon:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\Brand\\DungeonsForever.blp")
    icon:SetSize(88, 88)
    icon:SetPoint("CENTER", left, "CENTER", 0, 146)

    local brand = left:CreateFontString(nil, "OVERLAY")
    brand:SetFont(ns.FONT, 16, "")
    brand:SetText(L["无限副本手册"])
    brand:SetPoint("CENTER", left, "CENTER", 0, 72)
    brand:SetTextColor(C_AB_HEAD[1], C_AB_HEAD[2], C_AB_HEAD[3])

    local sub = left:CreateFontString(nil, "OVERLAY")
    sub:SetFont(ns.FONT, 14, "")
    sub:SetText("DungeonsForever" .. (DF_VERSION and (" · v" .. DF_VERSION) or ""))
    sub:SetPoint("CENTER", left, "CENTER", 0, 46)
    sub:SetTextColor(0.55, 0.62, 0.70)

    local studio = left:CreateFontString(nil, "OVERLAY")
    studio:SetFont(ns.FONT, 14, "")
    studio:SetText(L["黑科研研究所"])
    studio:SetPoint("CENTER", left, "CENTER", 0, 20)
    studio:SetTextColor(0.55, 0.62, 0.70)

    local QQ_NUM = "728916609"
    local qqPop
    local function ShowQQPop(anchor)
        if not qqPop then
            local p = CreateFrame("Frame", nil, about, "BackdropTemplate")
            p:SetSize(248, 110)
            p:SetFrameLevel(about:GetFrameLevel() + 12)
            p:EnableMouse(true)
            if p.SetBackdropColor then p:SetBackdropColor(0, 0, 0, 0) end
            if p.SetBackdropBorderColor then p:SetBackdropBorderColor(0, 0, 0, 0) end
            ns.hui.BuildRoundedBG(p, 8, ns.hui.layer.L0, "both", true)
            if ns.hui.SkinShadow then ns.hui.SkinShadow(p) end

            local t = p:CreateFontString(nil, "OVERLAY")
            t:SetFont(ns.FONT, 14, "")
            t:SetText(L["QQ群"])
            t:SetTextColor(C_AB_HEAD[1], C_AB_HEAD[2], C_AB_HEAD[3])
            t:SetPoint("TOPLEFT", p, "TOPLEFT", 12, -12)

            local eb = CreateFrame("EditBox", nil, p, "BackdropTemplate")
            eb:SetSize(224, 26)
            eb:SetPoint("TOPLEFT", p, "TOPLEFT", 12, -36)
            eb:SetAutoFocus(false)
            eb:SetFont(ns.FONT, 14, "")
            eb:SetTextColor(1, 1, 1)
            eb:SetTextInsets(8, 8, 0, 0)
            eb:SetJustifyH("LEFT")
            eb:SetMaxLetters(32)
            if eb.SetBackdropColor then eb:SetBackdropColor(0, 0, 0, 0) end
            if eb.SetBackdropBorderColor then eb:SetBackdropBorderColor(0, 0, 0, 0) end
            ns.hui.BuildRoundedBG(eb, 6, ns.hui.layer.L2, "both", true)
            eb:SetScript("OnEscapePressed", function(self)
                self:ClearFocus()
                p:Hide()
            end)

            local tip = p:CreateFontString(nil, "OVERLAY")
            tip:SetFont(ns.FONT, 12, "")
            tip:SetText(L["全选后 Ctrl+C 复制，Esc 关闭"])
            tip:SetTextColor(C_AB_DIM[1], C_AB_DIM[2], C_AB_DIM[3])
            tip:SetPoint("TOPLEFT", p, "TOPLEFT", 12, -72)

            p:SetScript("OnMouseUp", function(self)
                eb:ClearFocus()
                self:Hide()
            end)
            p.eb = eb
            qqPop = p
        end
        qqPop:ClearAllPoints()
        qqPop:SetPoint("TOPLEFT", anchor, "BOTTOMLEFT", -24, -10)
        qqPop:Show()
        qqPop.eb:SetText(QQ_NUM)
        qqPop.eb:HighlightText()
        if type(C_Timer) == "table" and type(C_Timer.After) == "function" then
            C_Timer.After(0, function()
                if qqPop and qqPop:IsShown() then
                    qqPop.eb:SetFocus()
                    qqPop.eb:HighlightText()
                end
            end)
        else
            qqPop.eb:SetFocus()
        end
    end

    local rows = {
        { key = L["作者"], parts = { { t = L["圆圆"] } } },
        { key = L["制作团队"], parts = { { t = L["专业增强"] .. " wzk" } } },
        { key = L["鸣谢"], parts = { { t = L["黑科研 · 胡里胡涂"] } } },
        { key = L["QQ群"], qq = true, parts = { { t = QQ_NUM } } },
        { key = L["指令"], parts = {
            { t = "/df", cmd = "/df" },
            { t = " · " },
            { t = "/fbsc", cmd = "/fbsc" },
            { t = " · " },
            { t = L["/副本手册"], cmd = L["/副本手册"] },
            { t = " — " .. L["开关窗口"] },
        } },
        { key = L["页面"], parts = {
            { t = "/df fb", cmd = "/df fb" }, { t = " " .. L["副本"] }, { t = " · " },
            { t = "/df tb", cmd = "/df tb" }, { t = " " .. L["团本"] }, { t = " · " },
            { t = "/df zy", cmd = "/df zy" }, { t = " " .. L["专业"] }, { t = " · " },
            { t = "/df zn", cmd = "/df zn" }, { t = " " .. L["指南"] },
        } },
        { key = L["页面"], parts = {
            { t = "/df ts", cmd = "/df ts" }, { t = " " .. L["探索"] }, { t = " · " },
            { t = "/df hp", cmd = "/df hp" }, { t = " " .. L["藏品"] }, { t = " · " },
            { t = "/df wm", cmd = "/df wm" }, { t = " " .. L["声望"] }, { t = " · " },
            { t = "/df bis", cmd = "/df bis" }, { t = " " .. L["配装"] },
        } },
    }

    local function BuildLine(row, hot)
        local out = C_AB_KEYHEX .. row.key .. "|r　"
        for pi = 1, #row.parts do
            local p = row.parts[pi]
            if p.cmd or (row.qq and pi == 1) then
                out = out .. ((hot == pi) and "|cffffffff" or AbAccentHex()) .. p.t .. "|r"
            else
                out = out .. p.t
            end
        end
        return out
    end

    local function SendCmd(cmd)
        if type(ChatFrame_OpenChat) == "function" then
            ChatFrame_OpenChat(cmd)
        end
    end

    local lines = {}
    local ly = -8
    for i = 1, #rows do
        local row = rows[i]
        local ln = left:CreateFontString(nil, "OVERLAY")
        ln:SetFont(ns.FONT, 14, "")
        ln:SetJustifyH("CENTER")
        ln:SetWidth(AB_INNER_W)
        ln:SetPoint("TOP", left, "CENTER", 0, ly)
        ln:SetTextColor(C_AB_VAL[1], C_AB_VAL[2], C_AB_VAL[3])

        ln:SetText(row.key)
        local keyW = ln:GetStringWidth() or 0
        ln:SetText(row.key .. "　")
        local headW = ln:GetStringWidth() or 0
        if headW < keyW then headW = keyW + 14 end

        local widths = {}
        local totalW = headW
        for pi = 1, #row.parts do
            ln:SetText(row.parts[pi].t)
            local w = ln:GetStringWidth() or 0
            widths[pi] = w
            totalW = totalW + w
        end

        ln:SetText(BuildLine(row, 0))

        local cursor = (AB_INNER_W - totalW) / 2 + headW
        for pi = 1, #row.parts do
            local p = row.parts[pi]
            local w = widths[pi]
            if p.cmd or (row.qq and pi == 1) then
                local b = CreateFrame("Button", nil, left)
                b:SetSize(w + 2, 20)
                b:SetPoint("LEFT", ln, "LEFT", cursor - 1, 0)
                b:SetFrameLevel(left:GetFrameLevel() + 2)
                b:EnableMouse(true)
                if p.cmd then
                    b:SetScript("OnClick", function() SendCmd(p.cmd) end)
                else
                    b:SetScript("OnClick", function(self) ShowQQPop(self) end)
                end
                b:SetScript("OnEnter", function() ln:SetText(BuildLine(row, pi)) end)
                b:SetScript("OnLeave", function() ln:SetText(BuildLine(row, 0)) end)
                if b.SetCursor then b:SetCursor("Interface/Cursor/Point") end
            end
            cursor = cursor + w
        end

        lines[#lines + 1] = { fs = ln, row = row }
        local vh = ln:GetStringHeight()
        if type(vh) ~= "number" or vh <= 0 then vh = 14 end
        ly = ly - math.max(28, vh + 10)
    end

    local card = CreateFrame("Frame", nil, about, "BackdropTemplate")
    card:SetSize(AB_CARD_W, AB_CARD_H)
    card:SetPoint("TOPLEFT", about, "TOPLEFT", AB_RIGHT_X, -AB_TOP)
    card:SetFrameLevel(about:GetFrameLevel() + 2)
    card:EnableMouse(true)
    card:SetScript("OnMouseUp", function()
        ns.PlaySound(1)
        about:Hide()
        SyncAboutGlyph()
    end)
    if card.SetBackdropColor then card:SetBackdropColor(0, 0, 0, 0) end
    if card.SetBackdropBorderColor then card:SetBackdropBorderColor(0, 0, 0, 0) end
    ns.hui.BuildRoundedBG(card, 8, ns.hui.layer.L1, "both", true)

    local hdr = card:CreateFontString(nil, "OVERLAY")
    hdr:SetFont(ns.FONT, 16, "")
    hdr:SetText(L["支持榜"])
    hdr:SetPoint("TOPLEFT", card, "TOPLEFT", AB_PAD, -(AB_PAD + 4))
    hdr:SetTextColor(C_AB_HEAD[1], C_AB_HEAD[2], C_AB_HEAD[3])

    local members = ns.Supporters or {}
    local cnt = card:CreateFontString(nil, "OVERLAY")
    cnt:SetFont(ns.FONT, 14, "")
    cnt:SetText(string.format(L["共 %d 位"], #members))
    cnt:SetPoint("LEFT", hdr, "RIGHT", 8, 0)
    cnt:SetTextColor(C_AB_DIM[1], C_AB_DIM[2], C_AB_DIM[3])

    local div = card:CreateTexture(nil, "ARTWORK")
    div:SetTexture("Interface\\Buttons\\WHITE8x8")
    local dv = ns.hui.layer.DIV
    div:SetVertexColor(dv[1], dv[2], dv[3], 1)
    div:SetHeight(1)
    div:SetPoint("TOPLEFT", card, "TOPLEFT", AB_PAD, -AB_DIV_Y)
    div:SetPoint("TOPRIGHT", card, "TOPRIGHT", -AB_PAD, -AB_DIV_Y)

    local scroll = CreateFrame("ScrollFrame", nil, card)
    scroll:SetPoint("TOPLEFT", card, "TOPLEFT", AB_PAD, -AB_GRID_TOP)
    scroll:SetSize(AB_AVAIL_W, AB_GRID_H)
    local child = CreateFrame("Frame", nil, scroll)
    child:SetSize(AB_AVAIL_W, AB_GRID_H)
    scroll:SetScrollChild(child)

    for i = 1, #members do
        local col = (i - 1) % AB_COLS
        local row = math.floor((i - 1) / AB_COLS)
        local nm = child:CreateFontString(nil, "OVERLAY")
        nm:SetFont(ns.FONT, 14, "")
        nm:SetJustifyH("LEFT")
        nm:SetWordWrap(false)
        nm:SetTextColor(1, 1, 1)
        nm:SetPoint("TOPLEFT", child, "TOPLEFT",
            col * (AB_COL_W + AB_COL_GAP),
            -(row * AB_ROW_H))
        AbFit(nm, members[i], AB_COL_W - 4)
    end
    local cy = math.ceil(#members / AB_COLS) * AB_ROW_H
    child:SetHeight(math.max(cy, AB_GRID_H))

    if #members == 0 then
        local empty = card:CreateFontString(nil, "OVERLAY")
        empty:SetFont(ns.FONT, 14, "")
        empty:SetText(L["还没有记录"])
        empty:SetTextColor(C_AB_DIM[1], C_AB_DIM[2], C_AB_DIM[3])
        empty:SetPoint("CENTER", scroll, "CENTER", 0, 0)
    end

    local track = CreateFrame("Frame", nil, card)
    track:SetSize(7, AB_GRID_H - 4)
    track:SetPoint("TOPLEFT", scroll, "TOPRIGHT", 0, -2)
    track:SetFrameLevel(card:GetFrameLevel() + 10)
    track.__fill = ns.hui.BuildSolidFill(track, 3, ns.hui.layer.L2)
    track:Hide()

    local thumb = CreateFrame("Frame", nil, card)
    thumb:SetSize(5, 24)
    thumb:SetFrameLevel(card:GetFrameLevel() + 11)
    thumb.__fill = ns.hui.BuildSolidFill(thumb, 2, ns.hui.layer.L4)
    thumb:EnableMouse(true)
    thumb:Hide()

    local function BarUpdate()
        local ch = child:GetHeight() or 0
        local vh = scroll:GetHeight() or 0
        if vh <= 0 or ch <= vh + 2 then
            track:Hide()
            thumb:Hide()
            return
        end
        track:Show()
        thumb:Show()
        local th = math.max(24, track:GetHeight() * vh / ch)
        thumb:SetHeight(th)
        local vp = scroll:GetVerticalScroll()
        if type(vp) ~= "number" then vp = 0 end
        local frac = 0
        local maxs = ch - vh
        if maxs > 0 then frac = vp / maxs end
        if frac < 0 then frac = 0 elseif frac > 1 then frac = 1 end
        local span = math.max(0, track:GetHeight() - th)
        thumb:ClearAllPoints()
        thumb:SetPoint("TOP", track, "TOP", 0, -(frac * span))
    end

    card:SetScript("OnMouseWheel", function(_, delta)
        if not track:IsShown() then return end
        local maxs = (child:GetHeight() or 0) - (scroll:GetHeight() or 0)
        local v = (scroll:GetVerticalScroll() or 0) - delta * 48
        if v < 0 then v = 0 elseif v > maxs then v = maxs end
        scroll:SetVerticalScroll(v)
        BarUpdate()
    end)

    thumb:SetScript("OnMouseDown", function(self)
        local scale = UIParent:GetEffectiveScale()
        local _, cy0 = GetCursorPosition()
        self.__y0 = cy0 / scale
        self.__s0 = scroll:GetVerticalScroll() or 0
        self:SetScript("OnUpdate", function(me)
            local span = (track:GetHeight() or 0) - (me:GetHeight() or 0)
            if span <= 0 then return end
            local _, cy1 = GetCursorPosition()
            local maxs = (child:GetHeight() or 0) - (scroll:GetHeight() or 0)
            local v = me.__s0 + (me.__y0 - cy1 / scale) / span * maxs
            if v < 0 then v = 0 elseif v > maxs then v = maxs end
            scroll:SetVerticalScroll(v)
            BarUpdate()
        end)
    end)
    thumb:SetScript("OnMouseUp", function(self) self:SetScript("OnUpdate", nil) end)
    thumb:SetScript("OnHide", function(self) self:SetScript("OnUpdate", nil) end)
    thumb:SetScript("OnEnter", function(self)
        self.__hover = true
        ns.hui.PaintSolidFill(self.__fill, ns.hui.layer.L5)
    end)
    thumb:SetScript("OnLeave", function(self)
        self.__hover = false
        ns.hui.PaintSolidFill(self.__fill, ns.hui.layer.L4)
    end)

    ns.hui.AddRepaint(about, function()
        for i = 1, #lines do
            local r = lines[i]
            r.fs:SetText(BuildLine(r.row, 0))
        end
        ns.hui.PaintSolidFill(track.__fill, ns.hui.layer.L2)
        ns.hui.PaintSolidFill(thumb.__fill, thumb.__hover and ns.hui.layer.L5 or ns.hui.layer.L4)
        local d2 = ns.hui.layer.DIV
        div:SetVertexColor(d2[1], d2[2], d2[3], 1)
    end)

    local donateShade
    local donateBuilt
    local function HideDonate()
        if donateShade and donateShade:IsShown() then donateShade:Hide() end
    end
    local function BuildDonate()
        if donateBuilt then return end
        donateBuilt = true
        local shade = CreateFrame("Button", "DungeonsForeverDonate", about)
        shade:SetAllPoints(about)
        shade:SetFrameLevel(about:GetFrameLevel() + 20)
        local bg = shade:CreateTexture(nil, "BACKGROUND")
        bg:SetAllPoints()
        bg:SetColorTexture(0, 0, 0, 0.52)
        shade:SetScript("OnClick", function() HideDonate() end)
        shade:Hide()
        table.insert(UISpecialFrames, "DungeonsForeverDonate")

        local pop = CreateFrame("Frame", nil, shade, "BackdropTemplate")
        pop:SetSize(260, 330)
        pop:SetPoint("CENTER", about, "CENTER", 0, 0)
        pop:SetFrameLevel(shade:GetFrameLevel() + 2)
        pop:SetClampedToScreen(true)
        pop:EnableMouse(true)
        if pop.SetBackdropColor then pop:SetBackdropColor(0, 0, 0, 0) end
        if pop.SetBackdropBorderColor then pop:SetBackdropBorderColor(0, 0, 0, 0) end
        if ns.hui.SkinPopup then ns.hui.SkinPopup(pop, 10, nil, ns.hui.layer.L0) end
        if ns.hui.SkinShadow then ns.hui.SkinShadow(pop) end
        local t = pop:CreateFontString(nil, "OVERLAY")
        t:SetFont(ns.FONT, 15, "")
        t:SetText(L["微信赞赏"])
        t:SetTextColor(C_AB_HEAD[1], C_AB_HEAD[2], C_AB_HEAD[3])
        t:SetPoint("TOP", pop, "TOP", 0, -16)

        local close = CreateFrame("Button", nil, pop)
        close:SetSize(24, 24)
        close:SetPoint("TOPRIGHT", pop, "TOPRIGHT", -8, -8)
        close:SetFrameLevel(pop:GetFrameLevel() + 3)
        close:SetHitRectInsets(-4, -4, -4, -4)
        local ci = close:CreateTexture(nil, "ARTWORK")
        ci:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\textures\\YY_close")
        ci:SetSize(14, 14)
        ci:SetPoint("CENTER")
        local cg = 0xa0 / 255
        ci:SetVertexColor(cg, cg, cg)
        close:SetScript("OnEnter", function() ci:SetVertexColor(1, 1, 1) end)
        close:SetScript("OnLeave", function() ci:SetVertexColor(cg, cg, cg) end)
        close:SetScript("OnClick", function()
            ns.PlaySound(1)
            HideDonate()
        end)

        local plate = CreateFrame("Frame", nil, pop, "BackdropTemplate")
        plate:SetSize(216, 216)
        plate:SetPoint("TOP", pop, "TOP", 0, -52)
        plate:SetFrameLevel(pop:GetFrameLevel() + 1)
        if plate.SetBackdropColor then plate:SetBackdropColor(0, 0, 0, 0) end
        if plate.SetBackdropBorderColor then plate:SetBackdropBorderColor(0, 0, 0, 0) end
        ns.hui.BuildRoundedBG(plate, 6, ns.hui.layer.L2, "both", false)

        local qr = plate:CreateTexture(nil, "ARTWORK")
        qr:SetAllPoints()
        qr:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\About\\wechat-support.tga")

        local h1 = pop:CreateFontString(nil, "OVERLAY")
        h1:SetFont(ns.FONT, 13, "")
        h1:SetText(L["手机微信扫一扫"])
        h1:SetTextColor(C_AB_VAL[1], C_AB_VAL[2], C_AB_VAL[3])
        h1:SetPoint("TOP", pop, "TOP", 0, -282)

        local h2 = pop:CreateFontString(nil, "OVERLAY")
        h2:SetFont(ns.FONT, 12, "")
        h2:SetText(L["点击空白处或按 Esc 关闭"])
        h2:SetTextColor(C_AB_DIM[1], C_AB_DIM[2], C_AB_DIM[3])
        h2:SetPoint("TOP", pop, "TOP", 0, -304)

        donateShade = shade
    end
    local function ToggleDonate()
        BuildDonate()
        if donateShade:IsShown() then
            donateShade:Hide()
        else
            donateShade:Show()
        end
    end

    local dbtn = CreateFrame("Button", nil, card, "BackdropTemplate")
    dbtn:SetSize(76, 22)
    dbtn:SetPoint("TOPRIGHT", card, "TOPRIGHT", -8, -9.5)
    dbtn:SetFrameLevel(card:GetFrameLevel() + 3)
    dbtn:SetHitRectInsets(-2, -2, -2, -2)
    if dbtn.SetBackdropColor then dbtn:SetBackdropColor(0, 0, 0, 0) end
    if dbtn.SetBackdropBorderColor then dbtn:SetBackdropBorderColor(0, 0, 0, 0) end
    local C_DN = { 0xc4 / 255, 0x34 / 255, 0x28 / 255, 1 }
    local C_DN_HOT = { 0xd4 / 255, 0x44 / 255, 0x36 / 255, 1 }
    local dFill = ns.hui.BuildRoundedBG(dbtn, 6, C_DN, "both", false)
    local dHot = ns.hui.BuildRoundedBG(dbtn, 6, C_DN_HOT, "both", false)
    for i = 1, #dHot do dHot[i]:Hide() end

    local dText = dbtn:CreateFontString(nil, "OVERLAY")
    dText:SetFont(ns.FONT, 12, "")
    dText:SetText(L["赞赏"])
    dText:SetTextColor(1, 1, 1)
    dText:SetPoint("CENTER", dbtn, "CENTER", 0, 0)

    dbtn:SetScript("OnEnter", function(self)
        for i = 1, #dFill do dFill[i]:Hide() end
        for i = 1, #dHot do dHot[i]:Show() end
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
        GameTooltip:AddLine(L["赞赏"], 1, 1, 1, true)
        GameTooltip:Show()
    end)
    dbtn:SetScript("OnLeave", function()
        for i = 1, #dHot do dHot[i]:Hide() end
        for i = 1, #dFill do dFill[i]:Show() end
        GameTooltip:Hide()
    end)
    dbtn:SetScript("OnClick", function()
        ns.PlaySound(1)
        ToggleDonate()
    end)
    if dbtn.SetCursor then dbtn:SetCursor("Interface/Cursor/Point") end

    about:HookScript("OnHide", function() HideDonate() end)

    BarUpdate()
end

local settingsGlyph
local settingsPop
local BuildTipCard
local BuildAppearanceCard
local appearanceCard
local appearanceBtn
local appearanceDot
local appearanceArrow
local appearanceRingBtn
local appearanceRingDot
local appearanceRingArrow
local THEME_CHOICES = {
    "green", "youfeng", "zhangliangying", "orange", "orangered",
    "red", "pink", "tonghang", "qq",
}
local C_THEME_FALLBACK = { 0x46 / 255, 0xbf / 255, 0x72 / 255 }
local C_RING_LINE = { 0.8, 0.8, 0.8 }
local C_RING_NONE = { 0.45, 0.45, 0.45 }

local function ThemeAccent(key)
    local pal = ns.hui and ns.hui.palette and ns.hui.palette[key]
    return (pal and pal.accent) or C_THEME_FALLBACK
end

local function ThemeName(key)
    local pal = ns.hui and ns.hui.palette and ns.hui.palette[key]
    return (pal and pal.name) or key
end

local function CurTheme()
    local cur = DungeonsForeverDB.libHUI and DungeonsForeverDB.libHUI.colorTheme
    if not cur or not (ns.hui and ns.hui.palette and ns.hui.palette[cur]) then cur = "green" end
    return cur
end

local function PaintAppearance()
    local key = CurTheme()
    local ac = ThemeAccent(key)
    if appearanceDot then appearanceDot:SetVertexColor(ac[1], ac[2], ac[3]) end
    if appearanceArrow then appearanceArrow:SetTextColor(ac[1], ac[2], ac[3]) end
    if appearanceBtn then
        local fs = appearanceBtn:GetFontString()
        if fs then
            fs:SetText(ThemeName(key))
            fs:SetTextColor(1, 1, 1)
        end
        ns.hui.SetButtonSelected(appearanceBtn, true)
    end
end

local function PaintRingMode()
    local mode = "glow"
    if ns.hui and ns.hui.RingMode then mode = ns.hui.RingMode() end
    local ac = (ns.hui and ns.hui.ACCENT) or C_THEME_FALLBACK
    local dc = ac
    if mode == "line" then dc = C_RING_LINE end
    if mode == "none" then dc = C_RING_NONE end
    if appearanceRingDot then appearanceRingDot:SetVertexColor(dc[1], dc[2], dc[3]) end
    if appearanceRingArrow then appearanceRingArrow:SetTextColor(dc[1], dc[2], dc[3]) end
    if appearanceRingBtn then
        local fs = appearanceRingBtn:GetFontString()
        if fs then
            fs:SetText(L["图标描边"])
            fs:SetTextColor(1, 1, 1)
        end
        if ns.hui and ns.hui.SetButtonSelected then ns.hui.SetButtonSelected(appearanceRingBtn, true) end
    end
end

local function SyncSettingsGlyph()
    if not settingsGlyph then return end
    local c = (settingsPop and settingsPop:IsShown()) and ns.SET_ICON_ON or ns.SET_ICON_IDLE
    settingsGlyph:SetVertexColor(c[1], c[2], c[3])
end

local settingsBtn = CreateFrame("Button", nil, f, "BackdropTemplate")
settingsBtn:SetSize(32, 32)
settingsBtn:SetFrameLevel(510)
settingsBtn:SetPoint("TOPRIGHT", f, "TOPRIGHT", -66, -4)
settingsBtn:SetHitRectInsets(-3, -3, -3, -3)
if ns.hui and ns.hui.SkinButton then ns.hui.SkinButton(settingsBtn, { noFrame = true }) end
do
    local g = settingsBtn:CreateTexture(nil, "ARTWORK")
    g:SetTexture(ns.SET_ICON)
    g:SetSize(14, 14)
    g:SetPoint("CENTER")
    g:SetVertexColor(ns.SET_ICON_IDLE[1], ns.SET_ICON_IDLE[2], ns.SET_ICON_IDLE[3])
    settingsGlyph = g
end
settingsBtn:SetScript("OnEnter", function(self)
    GameTooltip:SetOwner(self, "ANCHOR_BOTTOM")
    GameTooltip:ClearLines()
    GameTooltip:AddLine(L["设置"], 1, 1, 1, true)
    GameTooltip:Show()
end)
settingsBtn:SetScript("OnLeave", function()
    GameTooltip:Hide()
    SyncSettingsGlyph()
end)
settingsBtn:SetScript("OnClick", function()
    ns.PlaySound(1)
    local show = not settingsPop:IsShown()
    if show then
        about:Hide()
        SyncAboutGlyph()
        if ns.LootFilterUI and ns.LootFilterUI.CloseConfig then ns.LootFilterUI:CloseConfig() end
        if ns.CloseExploreMapSettings then ns.CloseExploreMapSettings() end
        if ns.CloseQuestPinSettings then ns.CloseQuestPinSettings() end
        if ns.CloseBisSettings then ns.CloseBisSettings() end
    end
    if show and ns.QuickBar then ns.QuickBar:SyncSettings() end
    if show then BuildTipCard() end
    if show then BuildAppearanceCard() end
    if show then BuildEnhCard() end
    settingsPop:SetShown(show)
    SyncSettingsGlyph()
end)

settingsPop = CreateFrame("Frame", nil, f, "BackdropTemplate")
settingsPop:SetFrameLevel(512)
settingsPop:SetPoint("TOPLEFT", f, "TOPRIGHT", 4, 0)
settingsPop:SetPoint("BOTTOMLEFT", f, "BOTTOMRIGHT", 4, 0)
settingsPop:SetWidth(220)
settingsPop:EnableMouse(true)
settingsPop:SetScript("OnMouseWheel", function() end)
settingsPop:Hide()
if ns.hui and ns.hui.SkinPopup and ns.hui.layer then
    ns.hui.SkinPopup(settingsPop, 8, nil, ns.hui.layer.L0)
    if ns.hui.SkinShadow then ns.hui.SkinShadow(settingsPop) end
else
    settingsPop:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8x8" })
    settingsPop:SetBackdropColor(0x0A / 255, 0x0C / 255, 0x10 / 255, 1)
end

ns.CloseSettings = function()
    if settingsPop then settingsPop:Hide() end
    SyncSettingsGlyph()
end

ns.SettingsPopup = settingsPop

do
    local title = settingsPop:CreateFontString(nil, "OVERLAY")
    title:SetFont(ns.FONT, 16, "")
    title:SetText(L["设置"])
    title:SetPoint("TOPLEFT", settingsPop, "TOPLEFT", 16, -14)
    title:SetTextColor(0.95, 0.96, 0.98)
end

local TIP_CARD_H = 66
local SET_COL2_X = 106
local SET_COL3_X = 148
local C_TIP_TXT = { 0.88, 0.88, 0.88 }
local C_TIP_DIM = { 0.62, 0.62, 0.62 }
local tipCard
local tipPreviewBt
local tipPreviewOn = false

local function PaintTipPreview(on)
    if tipPreviewBt and tipPreviewBt.lab then
        if on then
            tipPreviewBt.lab:SetTextColor(1, 0.82, 0)
        else
            tipPreviewBt.lab:SetTextColor(C_TIP_TXT[1], C_TIP_TXT[2], C_TIP_TXT[3])
        end
    end
end

function BuildAppearanceCard()
    if not (ns.hui and ns.hui.layer) then return end
    if appearanceCard then
        PaintAppearance()
        PaintRingMode()
        return
    end
    local card = CreateFrame("Frame", nil, settingsPop, "BackdropTemplate")
    if ns.hui.BuildRoundedBG then
        ns.hui.BuildRoundedBG(card, 8, ns.hui.layer.L2, "both", true, 1)
    else
        card:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8x8" })
        card:SetBackdropColor(0x16 / 255, 0x1A / 255, 0x22 / 255, 1)
        card:SetBackdropBorderColor(1, 1, 1, 0.1)
    end
    if tipCard then
        card:SetPoint("TOPLEFT", tipCard, "BOTTOMLEFT", 0, -10)
        card:SetPoint("TOPRIGHT", tipCard, "BOTTOMRIGHT", 0, -10)
    else
        card:SetPoint("TOPLEFT", settingsPop, "TOPLEFT", 6, -38)
        card:SetPoint("TOPRIGHT", settingsPop, "TOPRIGHT", -6, -38)
    end
    card:SetHeight(94)
    appearanceCard = card

    local hd = card:CreateFontString(nil, "OVERLAY")
    hd:SetFont(ns.FONT, 16, "")
    hd:SetPoint("TOPLEFT", card, "TOPLEFT", 8, -8)
    hd:SetText(L["外观"])
    hd:SetTextColor(C_TIP_DIM[1], C_TIP_DIM[2], C_TIP_DIM[3])

    local bt = ns.CreateButton(card)
    bt:SetSize(192, 24)
    bt:SetPoint("TOPLEFT", card, "TOPLEFT", 8, -30)
    bt.__huiKeepTextColor = true
    local fs = bt:GetFontString()
    if fs then
        fs:ClearAllPoints()
        fs:SetPoint("LEFT", bt, "LEFT", 26, 0)
        fs:SetPoint("RIGHT", bt, "RIGHT", -26, 0)
        fs:SetJustifyH("LEFT")
    end
    local dot = bt:CreateTexture(nil, "ARTWORK")
    dot:SetSize(12, 12)
    dot:SetPoint("LEFT", bt, "LEFT", 9, 0)
    dot:SetTexture("Interface\\Buttons\\WHITE8x8")
    if ns.hui.RoundIcon then ns.hui.RoundIcon(dot) end
    local arrow = bt:CreateFontString(nil, "OVERLAY")
    arrow:SetFont(ns.FONT, 12, "")
    arrow:SetPoint("RIGHT", bt, "RIGHT", -8, 0)
    arrow:SetText("\226\150\188")
    bt:SetScript("OnClick", function(self)
        ns.PlaySound(1)
        if not (ns.hui and ns.hui.ShowMenu) then return end
        local cur = CurTheme()
        local items = {}
        for _, key in ipairs(THEME_CHOICES) do
            local ac = ThemeAccent(key)
            items[#items + 1] = {
                text = ThemeName(key),
                swatch = ac,
                hlColor = ac,
                selected = (key == cur),
                func = function()
                    ns.hui.ApplyColorTheme(key)
                    PaintAppearance()
                    PaintRingMode()
                end,
            }
        end
        ns.hui.ShowMenu(items, { owner = self, anchor = self, up = true })
    end)
    appearanceBtn = bt
    appearanceDot = dot
    appearanceArrow = arrow

    local rb = ns.CreateButton(card)
    rb:SetSize(192, 24)
    rb:SetPoint("TOPLEFT", card, "TOPLEFT", 8, -58)
    rb.__huiKeepTextColor = true
    local rfs = rb:GetFontString()
    if rfs then
        rfs:ClearAllPoints()
        rfs:SetPoint("LEFT", rb, "LEFT", 26, 0)
        rfs:SetPoint("RIGHT", rb, "RIGHT", -26, 0)
        rfs:SetJustifyH("LEFT")
    end
    local rdot = rb:CreateTexture(nil, "ARTWORK")
    rdot:SetSize(12, 12)
    rdot:SetPoint("LEFT", rb, "LEFT", 9, 0)
    rdot:SetTexture("Interface\\Buttons\\WHITE8x8")
    if ns.hui.RoundIcon then ns.hui.RoundIcon(rdot) end
    local rarrow = rb:CreateFontString(nil, "OVERLAY")
    rarrow:SetFont(ns.FONT, 12, "")
    rarrow:SetPoint("RIGHT", rb, "RIGHT", -8, 0)
    rarrow:SetText("\226\150\188")
    rb:SetScript("OnClick", function(self)
        ns.PlaySound(1)
        if not (ns.hui and ns.hui.ShowMenu) then return end
        local cur = "glow"
        if ns.hui.RingMode then cur = ns.hui.RingMode() end
        local ac = ns.hui.ACCENT or C_THEME_FALLBACK
        local items = {
            {
                text = L["柔光"],
                hlColor = ac,
                selected = (cur == "glow"),
                func = function()
                    if ns.hui.SetIconRingMode then ns.hui.SetIconRingMode("glow") end
                    PaintRingMode()
                end,
            },
            {
                text = L["实线"],
                hlColor = C_RING_LINE,
                selected = (cur == "line"),
                func = function()
                    if ns.hui.SetIconRingMode then ns.hui.SetIconRingMode("line") end
                    PaintRingMode()
                end,
            },
            {
                text = L["无描边"],
                hlColor = C_RING_NONE,
                selected = (cur == "none"),
                func = function()
                    if ns.hui.SetIconRingMode then ns.hui.SetIconRingMode("none") end
                    PaintRingMode()
                end,
            },
        }
        ns.hui.ShowMenu(items, { owner = self, anchor = self, up = true })
    end)
    appearanceRingBtn = rb
    appearanceRingDot = rdot
    appearanceRingArrow = rarrow
    PaintAppearance()
    PaintRingMode()
end
ns.BuildAppearanceCard = BuildAppearanceCard
ns.PaintAppearance = PaintAppearance

local enhCard
local spellToggle
local talentToggle
local mapToggle
local zoneToggle

local function SpellBlocked()
    return (ns.SpellTabsTaken and ns.SpellTabsTaken()) and true or false
end

local function SyncEnhCard()
    if spellToggle then
        spellToggle:SetChecked((ns.SpellEnhOn and ns.SpellEnhOn()) and true or false)
        local blocked = SpellBlocked()
        spellToggle:SetAlpha(blocked and 0.4 or 1)
        if blocked then
            spellToggle:Disable()
        else
            spellToggle:Enable()
        end
    end
    if talentToggle then
        talentToggle:SetChecked((ns.TalentEnhOn and ns.TalentEnhOn()) and true or false)
    end
    if mapToggle then
        mapToggle:SetChecked((ns.MapEntryOn and ns.MapEntryOn()) and true or false)
    end
    if zoneToggle then
        local c = ns.ZoneHint and ns.ZoneHint.CFG and ns.ZoneHint.CFG()
        zoneToggle:SetChecked((c and c.on) and true or false)
    end
end

local function AnchorEnhCard()
    if not enhCard then return end
    enhCard:ClearAllPoints()
    local up = appearanceCard or tipCard
    if up then
        enhCard:SetPoint("TOPLEFT", up, "BOTTOMLEFT", 0, -8)
        enhCard:SetPoint("TOPRIGHT", up, "BOTTOMRIGHT", 0, -8)
    else
        enhCard:SetPoint("TOPLEFT", settingsPop, "TOPLEFT", 6, -38)
        enhCard:SetPoint("TOPRIGHT", settingsPop, "TOPRIGHT", -6, -38)
    end
end

local function EnhCell(card, x, y, title, tip, noteFn)
    local tg = CreateFrame("CheckButton", nil, card)
    tg:SetSize(28, 16)
    tg:EnableMouse(true)
    if ns.hui and ns.hui.ReskinToggle then ns.hui.ReskinToggle(tg) end
    tg:SetPoint("TOPLEFT", card, "TOPLEFT", x, y)
    tg:SetScript("OnEnter", function(self)
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
        GameTooltip:ClearLines()
        GameTooltip:AddLine(title, 1, 1, 1, true)
        if noteFn then
            local lines = noteFn()
            if lines then
                for i = 1, #lines do
                    GameTooltip:AddLine(lines[i], 1, 0.55, 0.35, true)
                end
            end
        end
        GameTooltip:AddLine(tip, 0.78, 0.80, 0.84, true)
        GameTooltip:Show()
    end)
    tg:SetScript("OnLeave", function()
        GameTooltip:Hide()
    end)
    local lb = card:CreateFontString(nil, "OVERLAY")
    lb:SetFont(ns.FONT, 12, "")
    lb:SetPoint("LEFT", tg, "RIGHT", 3, 0)
    lb:SetJustifyH("LEFT")
    lb:SetText(title)
    lb:SetTextColor(C_TIP_TXT[1], C_TIP_TXT[2], C_TIP_TXT[3])
    return tg
end

function BuildEnhCard()
    if enhCard then
        AnchorEnhCard()
        SyncEnhCard()
        return
    end
    local card = CreateFrame("Frame", nil, settingsPop, "BackdropTemplate")
    if ns.hui and ns.hui.BuildRoundedBG and ns.hui.layer then
        ns.hui.BuildRoundedBG(card, 8, ns.hui.layer.L2, "both", true, 1)
    else
        card:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8x8" })
        card:SetBackdropColor(0x16 / 255, 0x1A / 255, 0x22 / 255, 1)
        card:SetBackdropBorderColor(1, 1, 1, 0.1)
    end
    enhCard = card
    AnchorEnhCard()
    card:SetHeight(86)

    local hd = card:CreateFontString(nil, "OVERLAY")
    hd:SetFont(ns.FONT, 14, "")
    hd:SetPoint("TOPLEFT", card, "TOPLEFT", 8, -8)
    hd:SetText(L["原生界面增强"])
    hd:SetTextColor(C_TIP_DIM[1], C_TIP_DIM[2], C_TIP_DIM[3])

    spellToggle = EnhCell(card, 2, -34, L["技能页增强"], L["在原生技能书里增加职业技能与训练师页"],
        function()
            if not SpellBlocked() then return nil end
            return { L["其它插件已占用技能书页签，本项暂不可用"],
                     L["两个插件不能同时往技能书里加页；关掉对方的技能页增强并重载后，这里会自动恢复。"] }
        end)
    talentToggle = EnhCell(card, 113, -34, L["天赋页增强"], L["在原生天赋界面增加天赋模拟页与加点序号"])
    mapToggle = EnhCell(card, 2, -58, L["地图副本入口"], L["在世界地图上标出各副本的入口位置"])
    zoneToggle = EnhCell(card, 113, -58, L["地图待办"], L["进入地图时在屏幕左侧显示待办角标"])

    spellToggle:SetScript("OnClick", function(self)
        if SpellBlocked() then return end
        ns.PlaySound(1)
        local nv = not (ns.SpellEnhOn and ns.SpellEnhOn())
        self:SetChecked(nv)
        if ns.SetSpellEnh then ns.SetSpellEnh(nv) end
        SyncEnhCard()
    end)
    talentToggle:SetScript("OnClick", function(self)
        ns.PlaySound(1)
        local nv = not (ns.TalentEnhOn and ns.TalentEnhOn())
        self:SetChecked(nv)
        if ns.SetTalentEnh then ns.SetTalentEnh(nv) end
        SyncEnhCard()
    end)
    mapToggle:SetScript("OnClick", function(self)
        ns.PlaySound(1)
        local nv = not (ns.MapEntryOn and ns.MapEntryOn())
        self:SetChecked(nv)
        if ns.SetMapEntry then ns.SetMapEntry(nv) end
        SyncEnhCard()
    end)
    zoneToggle:SetScript("OnClick", function(self)
        ns.PlaySound(1)
        local c = ns.ZoneHint and ns.ZoneHint.CFG and ns.ZoneHint.CFG()
        if not c then return end
        c.on = self:GetChecked() and true or false
        SyncEnhCard()
        if ns.ZoneHint then ns.ZoneHint.CheckNow("manual") end
    end)
    SyncEnhCard()
end
ns.BuildEnhCard = BuildEnhCard

ns.SyncZoneHintCard = SyncEnhCard

local function AnchorTipCard(card)
    local qbCard = ns.QuickBar and ns.QuickBar.cardBg
    card:ClearAllPoints()
    if qbCard then
        card:SetPoint("TOPLEFT", qbCard, "BOTTOMLEFT", 0, -10)
        card:SetPoint("TOPRIGHT", qbCard, "BOTTOMRIGHT", 0, -10)
    else
        card:SetPoint("BOTTOMLEFT", settingsPop, "BOTTOMLEFT", 6, 12)
        card:SetPoint("BOTTOMRIGHT", settingsPop, "BOTTOMRIGHT", -6, 12)
    end
end

function BuildTipCard()
    if tipCard then
        AnchorTipCard(tipCard)
        return
    end
    if not ns.TipLines then return end
    local card = CreateFrame("Frame", nil, settingsPop, "BackdropTemplate")
    if ns.hui and ns.hui.BuildRoundedBG and ns.hui.layer then
        ns.hui.BuildRoundedBG(card, 8, ns.hui.layer.L2, "both", true, 1)
    else
        card:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8x8" })
        card:SetBackdropColor(0x16 / 255, 0x1A / 255, 0x22 / 255, 1)
        card:SetBackdropBorderColor(1, 1, 1, 0.1)
    end
    AnchorTipCard(card)
    card:SetHeight(TIP_CARD_H)

    local hd = card:CreateFontString(nil, "OVERLAY")
    hd:SetFont(ns.FONT, 16, "")
    hd:SetPoint("TOPLEFT", card, "TOPLEFT", 8, -10)
    hd:SetText(L["提示框内容"])
    hd:SetTextColor(C_TIP_DIM[1], C_TIP_DIM[2], C_TIP_DIM[3])

    local gsw = CreateFrame("CheckButton", nil, card)
    gsw:SetSize(36, 20)
    gsw:EnableMouse(true)
    if ns.hui and ns.hui.ReskinToggle then ns.hui.ReskinToggle(gsw) end
    gsw:SetPoint("TOPLEFT", card, "TOPLEFT", SET_COL2_X, -8)
    gsw:SetChecked(ns.TipCfg().global and true or false)
    gsw:SetScript("OnEnter", function(self)
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
        GameTooltip:ClearLines()
        GameTooltip:AddLine(L["游戏内物品提示框"], 1, 1, 1, true)
        GameTooltip:Show()
    end)
    gsw:SetScript("OnLeave", function()
        GameTooltip:Hide()
    end)
    gsw:SetScript("OnClick", function(self)
        ns.PlaySound(1)
        local c = ns.TipCfg()
        c.global = not (c.global and true)
        self:SetChecked(c.global and true or false)
        if ns.RefreshTipFonts then ns.RefreshTipFonts() end
        if ns.TipLines.RefreshPreview then ns.TipLines.RefreshPreview() end
    end)

    local TIP_ITEMS = {
        { key = "src",      label = L["掉落来源"] },
        { key = "bis",      label = L["BIS 推荐"] },
        { key = "bisScore", label = L["BIS 评分"] },
        { key = "wish",     label = L["心愿标记"] },
        { key = "quest",    label = L["任务来源"] },
        { key = "ilvl",     label = L["物品等级"] },
    }

    local dd = ns.CreateButton(card)
    dd:SetSize(192, 24)
    dd:SetPoint("TOPLEFT", card, "TOPLEFT", 8, -34)
    dd.__huiKeepTextColor = true
    local ddfs = dd:GetFontString()
    if ddfs then
        ddfs:ClearAllPoints()
        ddfs:SetPoint("LEFT", dd, "LEFT", 10, 0)
        ddfs:SetPoint("RIGHT", dd, "RIGHT", -24, 0)
        ddfs:SetJustifyH("LEFT")
        ddfs:SetTextColor(C_TIP_TXT[1], C_TIP_TXT[2], C_TIP_TXT[3])
        ddfs:SetText(L["鼠标提示框筛选"])
    end
    local ddar = dd:CreateFontString(nil, "OVERLAY")
    ddar:SetFont(ns.FONT, 12, "")
    ddar:SetPoint("RIGHT", dd, "RIGHT", -8, 0)
    ddar:SetText("\226\150\188")

    local function TipMenuItems()
        local cfg = ns.TipCfg()
        local items = {}
        for _, it in ipairs(TIP_ITEMS) do
            items[#items + 1] = {
                text = it.label,
                checked = cfg[it.key] and true or false,
                func = function()
                    ns.PlaySound(1)
                    local c = ns.TipCfg()
                    c[it.key] = not (c[it.key] and true)
                    if ns.TipLines.RefreshPreview then ns.TipLines.RefreshPreview() end
                    ns.hui.ShowMenu(TipMenuItems(), { owner = dd, anchor = dd })
                end,
            }
        end
        return items
    end

    dd:SetScript("OnClick", function(self)
        ns.PlaySound(1)
        if not (ns.hui and ns.hui.ShowMenu) then return end
        ns.hui.ShowMenu(TipMenuItems(), { owner = self, anchor = self })
    end)

    local bt = CreateFrame("Button", nil, card, "BackdropTemplate")
    bt:SetSize(44, 24)
    bt:EnableMouse(true)
    bt:SetPoint("TOPLEFT", card, "TOPLEFT", SET_COL3_X, -6)
    local pfs = bt:CreateFontString(nil, "OVERLAY")
    pfs:SetFont(ns.FONT, 13, "")
    pfs:SetPoint("CENTER")
    pfs:SetText(L["预览"])
    pfs:SetTextColor(C_TIP_TXT[1], C_TIP_TXT[2], C_TIP_TXT[3])
    bt:SetFontString(pfs)
    bt.lab = pfs
    bt.__huiKeepTextColor = true
    if ns.hui and ns.hui.SkinButton then ns.hui.SkinButton(bt) end
    pfs:SetFont(ns.FONT, 13, "")
    pfs:SetTextColor(C_TIP_TXT[1], C_TIP_TXT[2], C_TIP_TXT[3])
    bt:SetScript("OnEnter", function(self)
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
        GameTooltip:ClearLines()
        GameTooltip:AddLine(tipPreviewOn and L["关闭提示框预览"] or L["打开提示框预览"], 1, 1, 1, true)
        GameTooltip:Show()
    end)
    bt:SetScript("OnLeave", function(self)
        GameTooltip:Hide()
    end)
    bt:SetScript("OnClick", function()
        ns.PlaySound(1)
        tipPreviewOn = not tipPreviewOn
        PaintTipPreview(tipPreviewOn)
        if tipPreviewOn then
            if not (ns.TipLines.ShowPreview and ns.TipLines.ShowPreview(card)) then
                tipPreviewOn = false
                PaintTipPreview(false)
            end
        elseif ns.TipLines.HidePreview then
            ns.TipLines.HidePreview()
        end
    end)

    tipPreviewBt = bt
    tipCard = card
    settingsPop:HookScript("OnHide", function()
        tipPreviewOn = false
        PaintTipPreview(false)
        if ns.hui and ns.hui.HideDFMenu then ns.hui.HideDFMenu() end
        if ns.TipLines.HidePreview then ns.TipLines.HidePreview() end
    end)
end
ns.BuildTipCard = BuildTipCard

function ns.LayoutSettingsStack()
    if tipCard then
        AnchorTipCard(tipCard)
    end
    if appearanceCard then
        appearanceCard:ClearAllPoints()
        if tipCard then
            appearanceCard:SetPoint("TOPLEFT", tipCard, "BOTTOMLEFT", 0, -10)
            appearanceCard:SetPoint("TOPRIGHT", tipCard, "BOTTOMRIGHT", 0, -10)
        else
            appearanceCard:SetPoint("TOPLEFT", settingsPop, "TOPLEFT", 6, -38)
            appearanceCard:SetPoint("TOPRIGHT", settingsPop, "TOPRIGHT", -6, -38)
        end
    end
    AnchorEnhCard()
end


local SCALE_MIN, SCALE_MAX, SCALE_STEP = 60, 140, 5

local scaleTimer
local scaleReady = false
local scaleValue = 100
local scaleGroup
local scaleText

local function ApplyScale()
    local raw = scaleValue / 100
    local factor = raw
    local ok, pw, ph = pcall(GetPhysicalScreenSize)
    if ok and pw and ph and pw > 0 and ph > 0 then
        local es = 1
        if UIParent and UIParent.GetEffectiveScale then es = UIParent:GetEffectiveScale() or 1 end
        local availW = pw / es
        local availH = ph / es
        if availW > 0 and availH > 0 then
            local fit = math.min(raw, availW / W, availH / H)
            if fit > 0 then factor = fit end
        end
    end
    f:SetScale(factor)
    ns.DB().ui.scale = scaleValue
end

local function ScheduleScale()
    if scaleTimer and scaleTimer.Cancel then scaleTimer:Cancel() end
    if C_Timer and C_Timer.After then
        scaleTimer = C_Timer.After(0.5, function()
            scaleTimer = nil
            ApplyScale()
        end)
    else
        ApplyScale()
    end
end

local function SetScaleValue(v)
    v = math.floor(math.max(SCALE_MIN, math.min(SCALE_MAX, v)) + 0.5)
    if v == scaleValue then return end
    scaleValue = v
    scaleText.text:SetText(v .. "%")
    if scaleReady then ScheduleScale() end
end

local function ScaleTooltip(self, title)
    GameTooltip:SetOwner(self, "ANCHOR_BOTTOM")
    GameTooltip:ClearLines()
    GameTooltip:AddLine(title, 1, 1, 1, true)
    GameTooltip:AddLine(L["范围 60%–140%，停手 0.5 秒生效"], 0.7, 0.75, 0.8, true)
    GameTooltip:Show()
end

local C_PILL_ED = {0x55 / 255, 0x58 / 255, 0x5e / 255}
local C_GLYPH   = {0.67, 0.70, 0.73}
local C_NUM     = {0.91, 0.93, 0.94}
local PILL_H    = 24

scaleGroup = CreateFrame("Frame", nil, settingsPop, "BackdropTemplate")
scaleGroup:SetFrameLevel(520)
scaleGroup:SetSize(96, PILL_H)
scaleGroup:SetPoint("TOPRIGHT", settingsPop, "TOPRIGHT", -12, -11)
scaleGroup:SetBackdrop({ bgFile = "Interface/ChatFrame/ChatFrameBackground" })
do
    local c = ns.hui.layer.L2
    scaleGroup:SetBackdropColor(c[1], c[2], c[3], 1)
end
do
    local border = CreateFrame("Frame", nil, scaleGroup)
    border:SetAllPoints()
    ns.hui.BuildRoundBorder(border, 12, C_PILL_ED)
end

local function MakeGlyphButton(width, label, anchor)
    local bt = CreateFrame("Button", nil, scaleGroup, "BackdropTemplate")
    bt:SetFrameLevel(521)
    bt:SetSize(width, PILL_H)
    local off = (anchor == "TOPLEFT") and 2 or -2
    bt:SetPoint(anchor, scaleGroup, anchor, off, 0)
    if ns.hui and ns.hui.BuildCapsule then
        bt.__hov = ns.hui.BuildCapsule(bt, 8, ns.hui.layer.L4, 1, 2)
        for _, hv in ipairs(bt.__hov) do hv:Hide() end
    end
    local t = bt:CreateFontString(nil, "OVERLAY")
    bt:SetFontString(t)
    t:SetFont(ns.FONT, 28, "")
    t:SetText(label)
    t:SetPoint("CENTER")
    t:SetTextColor(C_GLYPH[1], C_GLYPH[2], C_GLYPH[3])
    bt.__huiKeepTextColor = true
    if ns.hui and ns.hui.SkinButton then ns.hui.SkinButton(bt, { noFrame = true }) end
    t:SetFont(ns.FONT, 28, "")
    t:ClearAllPoints()
    t:SetPoint("CENTER", 0, 1)
    t:SetTextColor(C_GLYPH[1], C_GLYPH[2], C_GLYPH[3])
    return bt
end

local minusBtn = MakeGlyphButton(24, "-", "TOPLEFT")
local plusBtn  = MakeGlyphButton(24, "+", "TOPRIGHT")
scaleText = CreateFrame("Button", nil, scaleGroup, "BackdropTemplate")
scaleText:SetFrameLevel(521)
scaleText:SetSize(44, PILL_H)
scaleText:SetPoint("TOPLEFT", minusBtn, "TOPRIGHT")
if ns.hui and ns.hui.SkinButton then ns.hui.SkinButton(scaleText, { noFrame = true }) end
if ns.hui and ns.hui.BuildCapsule then
    scaleText.__hov = ns.hui.BuildCapsule(scaleText, 8, ns.hui.layer.L4, 1, 2)
    for _, hv in ipairs(scaleText.__hov) do hv:Hide() end
end
do
    local t = scaleText:CreateFontString(nil, "OVERLAY")
    t:SetFont(ns.FONT, 14, "")
    t:SetText("100%")
    t:SetPoint("CENTER")
    t:SetTextColor(C_NUM[1], C_NUM[2], C_NUM[3])
    scaleText.text = t
end

local function HoverShow(bt)
    if bt.__hov then
        for _, hv in ipairs(bt.__hov) do hv:Show() end
    end
end
local function HoverHide(bt)
    if bt.__hov then
        for _, hv in ipairs(bt.__hov) do hv:Hide() end
    end
end

local function HoverOn(glyph)
    if glyph then glyph:SetTextColor(ns.hui.ACCENT[1], ns.hui.ACCENT[2], ns.hui.ACCENT[3]) end
end
local function HoverOff(glyph)
    if glyph then glyph:SetTextColor(C_GLYPH[1], C_GLYPH[2], C_GLYPH[3]) end
end

local function StopRepeat(bt)
    bt.__holding = nil
    if bt.__delay then bt.__delay:Cancel() bt.__delay = nil end
    if bt.__ticker then bt.__ticker:Cancel() bt.__ticker = nil end
end

local function StartRepeat(bt, dir)
    if not (C_Timer and C_Timer.After and C_Timer.NewTicker) then return end
    StopRepeat(bt)
    bt.__holding = true
    bt.__delay = C_Timer.After(0.4, function()
        bt.__delay = nil
        if not bt.__holding then return end
        bt.__ticker = C_Timer.NewTicker(0.12, function()
            if not bt.__holding or not bt:IsMouseOver() then
                StopRepeat(bt)
                return
            end
            SetScaleValue(scaleValue + dir * SCALE_STEP)
        end)
    end)
end

plusBtn:SetScript("OnMouseDown", function()
    SetScaleValue(scaleValue + SCALE_STEP)
    StartRepeat(plusBtn, 1)
end)
plusBtn:SetScript("OnMouseUp", function() StopRepeat(plusBtn) end)
minusBtn:SetScript("OnMouseDown", function()
    SetScaleValue(scaleValue - SCALE_STEP)
    StartRepeat(minusBtn, -1)
end)
minusBtn:SetScript("OnMouseUp", function() StopRepeat(minusBtn) end)

plusBtn:SetScript("OnEnter", function(self) HoverShow(self) HoverOn(self:GetFontString()) ScaleTooltip(self, L["放大界面"]) end)
plusBtn:SetScript("OnLeave", function(self) HoverHide(self) HoverOff(self:GetFontString()) GameTooltip:Hide() end)
minusBtn:SetScript("OnEnter", function(self) HoverShow(self) HoverOn(self:GetFontString()) ScaleTooltip(self, L["缩小界面"]) end)
minusBtn:SetScript("OnLeave", function(self) HoverHide(self) HoverOff(self:GetFontString()) GameTooltip:Hide() end)

scaleText:SetScript("OnEnter", function(self)
    HoverShow(self)
    HoverOn()
    GameTooltip:SetOwner(self, "ANCHOR_BOTTOM")
    GameTooltip:ClearLines()
    GameTooltip:AddLine(L["界面大小"], 1, 1, 1, true)
    GameTooltip:AddLine(L["点击复位 100%"], 0.7, 0.75, 0.8, true)
    GameTooltip:Show()
end)
scaleText:SetScript("OnLeave", function(self) HoverHide(self) HoverOff() GameTooltip:Hide() end)
scaleText:SetScript("OnClick", function()
    ns.PlaySound(1)
    SetScaleValue(100)
end)

f:HookScript("OnShow", function()
    about:Hide()
    SyncAboutGlyph()
    if settingsPop then settingsPop:Hide() end
    SyncSettingsGlyph()
    if ns.LootFilterUI then ns.LootFilterUI:CloseConfig() end
    if ns.QuickBar then ns.QuickBar:OnMainShow() end
end)

local function SavePosition()
    local db = ns.DB().ui
    local point, _, relPoint, x, y = f:GetPoint(1)
    db.window = { point = point, relPoint = relPoint, x = x, y = y }
end

f:SetScript("OnDragStart", function(self) self:StartMoving() end)
f:SetScript("OnDragStop", function(self)
    self:StopMovingOrSizing()
    SavePosition()
end)

ns.Init(function()
    local pos = ns.DB().ui.window
    if pos and pos.point then
        f:ClearAllPoints()
        f:SetPoint(pos.point, UIParent, pos.relPoint or pos.point, pos.x or 0, pos.y or 0)
    end
    local sc = ns.DB().ui.scale
    if sc then
        sc = math.max(60, math.min(140, sc))
        f:SetScale(sc / 100)
        scaleValue = sc
        scaleText.text:SetText(sc .. "%")
    end
    scaleReady = true
end)

local reveal = { on = false, q = nil, total = 0, done = 0 }
local revealBar, revealFill, revealText

local function RevealNow()
    local fn = debugprofilestop
    if type(fn) == "function" then
        local ok, v = pcall(fn)
        if ok and type(v) == "number" then return v end
    end
    fn = GetTime
    if type(fn) == "function" then
        local ok, v = pcall(fn)
        if ok and type(v) == "number" then return v * 1000 end
    end
    return 0
end

local function RevealUI()
    if revealBar then return end
    revealBar = CreateFrame("Frame", nil, f)
    revealBar:SetFrameLevel(f:GetFrameLevel() + 80)
    revealBar:SetPoint("TOPLEFT", f, "TOPLEFT", 8, 0)
    revealBar:SetPoint("TOPRIGHT", f, "TOPRIGHT", -8, 0)
    revealBar:SetHeight(3)
    local bg = revealBar:CreateTexture(nil, "BACKGROUND")
    bg:SetAllPoints()
    if ns.hui and ns.hui.layer then
        local c = ns.hui.layer.L1
        bg:SetColorTexture(c[1], c[2], c[3], 0.9)
    else
        bg:SetColorTexture(0, 0, 0, 0.45)
    end
    revealFill = revealBar:CreateTexture(nil, "OVERLAY")
    revealFill:SetPoint("TOPLEFT", revealBar, "TOPLEFT", 0, 0)
    revealFill:SetPoint("BOTTOMLEFT", revealBar, "BOTTOMLEFT", 0, 0)
    revealFill:SetWidth(1)
    revealFill:SetColorTexture(1, 0.82, 0, 1)
    revealText = revealBar:CreateFontString(nil, "OVERLAY")
    revealText:SetFont(ns.FONT, 11, "")
    revealText:SetPoint("TOP", f, "TOP", 0, -9)
    revealText:SetTextColor(0.7, 0.76, 0.84)
    revealBar:Hide()
end

local REVEAL_MAX = 120

local function RevealCollect(root)
    local order, queue = {}, { root }
    local i = 1
    while i <= #queue and #order < REVEAL_MAX do
        local fr = queue[i]
        i = i + 1
        if fr.GetChildren then
            local kids = { fr:GetChildren() }
            for _, c in ipairs(kids) do
                if #order >= REVEAL_MAX then break end
                if c.IsShown and c:IsShown() then
                    order[#order + 1] = c
                    queue[#queue + 1] = c
                end
            end
        end
    end
    return order
end

local function RevealPaint()
    if not revealBar then return end
    local pct = 0
    if reveal.total > 0 then pct = math.floor(reveal.done / reveal.total * 100 + 0.5) end
    if pct < 0 then pct = 0 elseif pct > 100 then pct = 100 end
    revealFill:SetWidth(math.max(1, math.floor((W - 16) * pct / 100)))
    revealText:SetText(L["正在载入…"] .. " " .. pct .. "%")
end

local function RevealFinishAll()
    local ghost = DungeonsForeverDB and DungeonsForeverDB.dfGhost
    reveal.on = false
    local q = reveal.q
    local i = reveal.i or 1
    if q and not ghost then
        for k = i, #q do
            local cfr = q[k]
            if cfr and cfr.Show then pcall(cfr.Show, cfr) end
        end
    end
    reveal.q = nil
    reveal.i = 1
    reveal.deadline = nil
    reveal.stallT = nil
    if DungeonsForeverDB then
        local ms = math.floor(RevealNow() - (reveal.t0 or RevealNow()))
        local tail = reveal.bg and " bg" or ""
        DungeonsForeverDB.dfRevealLog = string.format("%d/%d %dms%s", reveal.total or 0, reveal.done or 0, ms, tail)
    end
    reveal.t0 = nil
    reveal.bg = nil
    if reveal.heavy and DungeonsForeverDB then
        DungeonsForeverDB.dfRevealHeavy = table.concat(reveal.heavy, " ")
        reveal.heavy = nil
    end
    if revealBar then revealBar:Hide() end
end

local revealedOnce = false

local function RevealStart()
    if revealedOnce then return end
    local db = ns.DB and ns.DB().ui
    if db and db.reveal == false then return end
    RevealUI()
    if reveal.on then RevealFinishAll() end
    local order = RevealCollect(f)
    if #order < 20 then
        if DungeonsForeverDB then DungeonsForeverDB.dfRevealLog = "skip " .. tostring(#order) end
        return
    end
    local t0 = RevealNow()
    revealedOnce = true
    reveal.on = true
    reveal.q = order
    reveal.i = 1
    reveal.total = #order
    reveal.done = 0
    reveal.lastDone = 0
    reveal.t0 = t0
    reveal.deadline = t0 + 6000
    reveal.stallT = t0
    reveal.heavy = nil
    reveal.bg = nil
    for i = 1, #order do
        local cfr = order[i]
        if cfr and cfr.Hide then pcall(cfr.Hide, cfr) end
    end
    revealBar:Show()
    RevealPaint()
end

f:HookScript("OnUpdate", function()
    if not reveal.on then return end
    local now = RevealNow()
    local q = reveal.q
    local i = reveal.i or 1
    if not q or i > #q then
        RevealFinishAll()
        return
    end
    local over = now - (reveal.deadline or now)
    local budget = 2
    if reveal.bg then
        budget = 32
    elseif over > 6000 then
        budget = 32
    elseif over > 0 then
        budget = 8
    end
    local t0 = now
    local startI = i
    while i <= #q do
        local cfr = q[i]
        i = i + 1
        local c0 = RevealNow()
        if cfr and cfr.Show then pcall(cfr.Show, cfr) end
        local c1 = RevealNow()
        local cost = c1 - c0
        if cost > 30 then
            local nm = "?"
            if cfr and cfr.GetName then
                local gn = cfr:GetName()
                if type(gn) == "string" and gn ~= "" then nm = gn end
            end
            reveal.heavy = reveal.heavy or {}
            local h = reveal.heavy
            h[#h + 1] = string.format("%d%%:%s:%.0f", math.floor(reveal.done / math.max(1, reveal.total) * 100 + 0.5), nm, cost)
        end
        reveal.done = reveal.done + 1
        if c1 - t0 >= budget then break end
        if (i - startI) >= 64 then break end
    end
    reveal.i = i
    if not reveal.bg then RevealPaint() end
    if i > #q then
        RevealFinishAll()
        return
    end
    if reveal.done ~= reveal.lastDone then
        reveal.lastDone = reveal.done
        reveal.stallT = now
    elseif now - (reveal.stallT or now) > 4000 then
        reveal.bg = now
    end
end)

f:HookScript("OnHide", function()
    if not reveal.on then return end
    reveal.bg = RevealNow()
    if revealBar then revealBar:Hide() end
end)

function ns.Open()
    if not f:IsShown() then
        f:Show()
        if reveal.on and reveal.bg then
            reveal.bg = nil
            if revealBar then revealBar:Show() end
        end
        RevealStart()
    end
    f:Raise()
end

function ns.Toggle()
    if f:IsShown() then f:Hide() else ns.Open() end
end

ns.OpenDungeon = ns.Open

ns.Init(function()
    local LDB = LibStub("LibDataBroker-1.1", true)
    local LibDBIcon = LibStub("LibDBIcon-1.0", true)
    if not (LDB and LibDBIcon) then return end

    local db = ns.DB().ui
    if not db.minimap then db.minimap = { hide = false, minimapPos = 315 } end
    if db.minimap.minimapPos == nil then db.minimap.minimapPos = 315 end

    local launcher = LDB:NewDataObject("DungeonsForever", {
        type = "launcher",
        icon = "Interface\\AddOns\\DungeonsForever\\Media\\Brand\\DungeonsForever.blp",
        OnClick = function(_, button)
            if button == "LeftButton" then ns.Toggle() end
        end,
        OnTooltipShow = function(tt)
            tt:AddLine("|cff46bf72" .. L["无限副本手册"] .. "|r")
            tt:AddLine(L["左键：打开 / 关闭界面"], 1, 1, 1)
        end,
    })
    LibDBIcon:Register("DungeonsForever", launcher, db.minimap)
end)

SLASH_DUNGEONSFOREVER1 = "/df"
SLASH_DUNGEONSFOREVER2 = L["/副本手册"]
SLASH_DUNGEONSFOREVER3 = "/fbsc"

SLASH_DUNGEONSFOREVERLANG1 = "/dfcn"
SLASH_DUNGEONSFOREVERLANG2 = L["/df中文"]
SlashCmdList["DUNGEONSFOREVERLANG"] = function()
    if type(GetLocale) ~= "function" then return end
    local tag = "|cff46bf72[" .. L["无限副本手册"] .. "]|r "
    if GetLocale() == "zhCN" then
        print(tag .. L["当前客户端已是简体中文，无需切换"])
        return
    end
    DungeonsForeverDB = DungeonsForeverDB or {}
    local on = DungeonsForeverDB.langCN ~= true
    DungeonsForeverDB.langCN = on
    if ns.ConfirmReload then
        ns.ConfirmReload(on and L["已切换为简体中文界面，重载界面后生效"]
            or L["已恢复跟随客户端语言，重载界面后生效"])
    end
end

local PAGE_ALIASES = {
    fb = "Dungeons",    ["副本"] = "Dungeons",
    tb = "Raids",       ["团本"] = "Raids",
    zy = "Professions", ["专业"] = "Professions",
    ts = "Explore",     ["探索"] = "Explore",
    hp = "Collections", ["藏品"] = "Collections",
    wm = "Factions",    ["声望"] = "Factions",
    bis = "Bis",        ["配装"] = "Bis",
    zn = "Tier",        ["指南"] = "Tier",
}
local chipCalib
local chipCalibMain
local chipCalibChip
local chipCalibVal

local function ChipCalibLineH()
    return (ns.hui and ns.hui.ChipLineH and ns.hui.ChipLineH(14)) or 14
end

local function ChipCalibDy()
    local k = (ns.hui and ns.hui.ChipK and ns.hui.ChipK()) or 0
    return k * ChipCalibLineH()
end

local function ChipCalibRefresh()
    if chipCalibChip and chipCalibMain then
        chipCalibChip:ClearAllPoints()
        chipCalibChip:SetPoint("LEFT", chipCalibMain, "RIGHT", 6, ChipCalibDy())
        if ns.hui and ns.hui.PaintSolidChip then
            ns.hui.PaintSolidChip(chipCalibChip, L["可共享"], { 0.45, 0.86, 0.55 })
        end
    end
    if chipCalibVal then
        chipCalibVal:SetText(format(L["当前偏移 %+.2f"], ChipCalibDy()))
    end
end

local function ChipCalibStep(step)
    local k = (ns.hui and ns.hui.ChipK and ns.hui.ChipK()) or 0
    local lh = ChipCalibLineH()
    local dy = k * lh + step
    if ns.hui and ns.hui.SetChipK then ns.hui.SetChipK(dy / lh) end
    ChipCalibRefresh()
end

local function ChipCalibReset()
    if ns.hui and ns.hui.SetChipK then ns.hui.SetChipK(nil) end
    ChipCalibRefresh()
end

function ns.OpenChipCalib()
    if not chipCalib then
        local p = CreateFrame("Frame", nil, UIParent, "BackdropTemplate")
        p:SetSize(420, 214)
        p:SetPoint("CENTER", UIParent, "CENTER", 0, 40)
        p:SetFrameStrata("DIALOG")
        p:EnableMouse(true)
        p:SetMovable(true)
        p:RegisterForDrag("LeftButton")
        p:SetScript("OnDragStart", function(self) self:StartMoving() end)
        p:SetScript("OnDragStop", function(self) self:StopMovingOrSizing() end)
        if ns.hui and ns.hui.SkinPopup and ns.hui.layer then
            ns.hui.SkinPopup(p, 8, nil, ns.hui.layer.L0)
            if ns.hui.SkinShadow then ns.hui.SkinShadow(p) end
        else
            p:SetBackdrop({
                bgFile = "Interface\\Buttons\\WHITE8x8",
                edgeFile = "Interface\\Buttons\\WHITE8x8",
                edgeSize = 1,
            })
            p:SetBackdropColor(0x0A / 255, 0x0C / 255, 0x10 / 255, 1)
            p:SetBackdropBorderColor(1, 1, 1, 0.12)
        end
        chipCalib = p

        local title = p:CreateFontString(nil, "OVERLAY")
        title:SetFont(ns.FONT, 16, "")
        title:SetText(L["卡片对齐校准"])
        title:SetPoint("TOPLEFT", p, "TOPLEFT", 16, -14)
        title:SetTextColor(0.95, 0.96, 0.98)

        local desc = p:CreateFontString(nil, "OVERLAY")
        desc:SetFont(ns.FONT, 13, "")
        desc:SetText(L["对照下面这行，把卡片调到与文字上下齐平。"])
        desc:SetPoint("TOPLEFT", p, "TOPLEFT", 16, -40)
        desc:SetTextColor(C_TIP_DIM[1], C_TIP_DIM[2], C_TIP_DIM[3])

        local host = CreateFrame("Frame", nil, p)
        host:SetSize(388, 34)
        host:SetPoint("TOPLEFT", p, "TOPLEFT", 16, -64)
        local main = host:CreateFontString(nil, "OVERLAY")
        main:SetFont(ns.FONT, 14, "")
        main:SetPoint("LEFT", host, "LEFT", 0, 0)
        main:SetText(L["寻找背包"])
        main:SetTextColor(0.95, 0.96, 0.98)
        chipCalibMain = main
        if ns.hui and ns.hui.MakeSolidChip then
            chipCalibChip = ns.hui.MakeSolidChip(host, (host:GetFrameLevel() or 0) + 2,
                (ns.hui.ChipH and ns.hui.ChipH(14)) or 14)
        end

        local val = p:CreateFontString(nil, "OVERLAY")
        val:SetFont(ns.FONT, 13, "")
        val:SetPoint("TOPLEFT", p, "TOPLEFT", 16, -106)
        val:SetTextColor(0.85, 0.93, 1.0)
        chipCalibVal = val

        local hint = p:CreateFontString(nil, "OVERLAY")
        hint:SetFont(ns.FONT, 12, "")
        hint:SetText(L["默认已对齐，一般不用动；只有换到字形差别很大的字体时才需微调。"])
        hint:SetPoint("TOPLEFT", p, "TOPLEFT", 16, -128)
        hint:SetTextColor(C_TIP_DIM[1], C_TIP_DIM[2], C_TIP_DIM[3])

        local function mkBtn(text, x, y, wpx, fn)
            local bt = CreateFrame("Button", nil, p, "BackdropTemplate")
            bt:SetSize(wpx, 24)
            bt:SetPoint("BOTTOMLEFT", p, "BOTTOMLEFT", x, y)
            local bfs = bt:CreateFontString(nil, "OVERLAY")
            bfs:SetFont(ns.FONT, 13, "")
            bfs:SetPoint("CENTER")
            bfs:SetText(text)
            bt:SetFontString(bfs)
            bt.__huiKeepTextColor = true
            if ns.hui and ns.hui.SkinButton then ns.hui.SkinButton(bt) end
            bfs:SetFont(ns.FONT, 13, "")
            bfs:SetTextColor(C_TIP_TXT[1], C_TIP_TXT[2], C_TIP_TXT[3])
            bt:SetScript("OnClick", function()
                if ns.PlaySound then ns.PlaySound(1) end
                fn()
            end)
            return bt
        end

        mkBtn(L["下移 0.5"], 16, 44, 88, function() ChipCalibStep(-0.5) end)
        mkBtn(L["下移 0.2"], 112, 44, 88, function() ChipCalibStep(-0.2) end)
        mkBtn(L["上移 0.2"], 208, 44, 88, function() ChipCalibStep(0.2) end)
        mkBtn(L["上移 0.5"], 304, 44, 88, function() ChipCalibStep(0.5) end)
        mkBtn(L["重置"], 16, 12, 88, function() ChipCalibReset() end)
        mkBtn(L["关闭"], 304, 12, 88, function() if chipCalib then chipCalib:Hide() end end)
    end
    ChipCalibRefresh()
    chipCalib:Show()
end

SlashCmdList["DUNGEONSFOREVER"] = function(msg)
    local cmd = strtrim(msg or "")
    if cmd == "" then
        ns.Toggle()
        return
    end
    if cmd == "对齐" or cmd == "卡片" or cmd:lower() == "chip" then
        ns.OpenChipCalib()
        return
    end
    if cmd == "rank" or cmd == "动作条" or cmd == "法術" then
        if ns.SpellRankUI then
            ns.SpellRankUI.Toggle()
        else
            print("|cff46bf72[" .. L["无限副本手册"] .. "]|r " .. L["技能书模块未启用"])
        end
        return
    end
    if cmd == "rankcheck" then
        if ns.SpellRank and ns.SpellRank.ReportDiagnose then
            ns.SpellRank.ReportDiagnose()
        else
            print("|cff46bf72[" .. L["无限副本手册"] .. "]|r " .. L["技能书模块未启用"])
        end
        return
    end
    if cmd == "rankdebug" then
        if ns.SpellRankUI and ns.SpellRankUI.Debug then
            ns.SpellRankUI.Debug()
        else
            print("|cff46bf72[" .. L["无限副本手册"] .. "]|r " .. L["技能书模块未启用"])
        end
        return
    end
    if cmd == "hint" or cmd == "模拟" or cmd == "待办" or cmd:match("^hint%s") or cmd:match("^模拟%s") then
        if ns.ZoneHint and ns.ZoneHint.SimCommand then
            ns.ZoneHint.SimCommand(cmd:match("^%S+%s*(.*)$"))
        else
            print("|cff46bf72[" .. L["无限副本手册"] .. "]|r " .. L["地图提醒模块未启用"])
        end
        return
    end
    local key = PAGE_ALIASES[cmd:lower()]
    if key then
        if not ns.IsForever and key ~= "Dungeons" and key ~= "Raids" then
            print("|cff46bf72[" .. L["无限副本手册"] .. "]|r " .. L["该页面仅无限服可用，已为你打开副本页。"])
            key = "Dungeons"
        end
        ns.OpenPage(key)
        return
    end
    print("|cff46bf72[" .. L["无限副本手册"] .. "]|r " .. L["用法：/df 或 /fbsc 打开或关闭界面。"])
    print("  /df fb|副本 · tb|团本 · zy|专业 · ts|探索 · hp|藏品 · wm|声望 · bis|配装 · zn|指南 · rank|动作条 — " .. L["直达对应页"])
    print("  /dfspeed — " .. L["载入速度"]
          .. "（" .. L["省电"] .. " / " .. L["标准"] .. " / " .. L["激进"] .. "）")
    print("  /dfgate — " .. L["进度条"] .. "（demo / off）")
    print("  /df 对齐 — " .. L["卡片与文字对齐校准"])
end
