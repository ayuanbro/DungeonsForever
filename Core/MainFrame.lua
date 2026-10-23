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
if ns.hui and ns.hui.SkinButton then ns.hui.SkinButton(close) end
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
if ns.hui and ns.hui.SkinButton then ns.hui.SkinButton(aboutBtn) end
do
    local q = aboutBtn:CreateTexture(nil, "ARTWORK")
    q:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\HelpIcon")
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
    ns.hui.SkinPopup(about, 8)
    if ns.hui.SkinShadow then ns.hui.SkinShadow(about) end
else
    about:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8x8" })
    about:SetBackdropColor(0x10 / 255, 0x13 / 255, 0x1A / 255, 1)
end

do
    local icon = about:CreateTexture(nil, "ARTWORK")
    icon:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\DungeonsForever.blp")
    icon:SetSize(56, 56)
    icon:SetPoint("CENTER", about, "CENTER", 0, 148)

    local brand = about:CreateFontString(nil, "OVERLAY")
    brand:SetFont(ns.FONT, 16, "")
    brand:SetText(L["无限副本手册"])
    brand:SetPoint("CENTER", about, "CENTER", 0, 92)
    brand:SetTextColor(0.95, 0.96, 0.98)

    local ver = DF_VERSION
    local sub = about:CreateFontString(nil, "OVERLAY")
    sub:SetFont(ns.FONT, 14, "")
    sub:SetText("DungeonsForever" .. (ver and (" · v" .. ver) or ""))
    sub:SetPoint("CENTER", about, "CENTER", 0, 66)
    sub:SetTextColor(0.55, 0.62, 0.70)

    local studio = about:CreateFontString(nil, "OVERLAY")
    studio:SetFont(ns.FONT, 14, "")
    studio:SetText(L["黑科研研究所"])
    studio:SetPoint("CENTER", about, "CENTER", 0, 42)
    studio:SetTextColor(0.55, 0.62, 0.70)

    local rows = {
        { L["作者"], L["圆圆"] },
        { L["鸣谢"], L["黑科研 · 胡里胡涂"] },
        { L["QQ群"], "728916609" },
        { L["指令"], "|cff46bf72/df|r · |cff46bf72/fbsc|r · /副本手册 — " .. L["开关窗口"] },
        { L["页面"], "|cff46bf72/df fb|r" .. L["副本"] .. " · |cff46bf72tb|r" .. L["团本"]
            .. " · |cff46bf72zy|r" .. L["专业"] .. " · |cff46bf72ts|r" .. L["探索"]
            .. " · |cff46bf72hp|r" .. L["藏品"] .. " · |cff46bf72wm|r" .. L["声望"] .. " · |cff46bf72bis|r" .. L["配装"] },
    }
    for i, row in ipairs(rows) do
        local ln = about:CreateFontString(nil, "OVERLAY")
        ln:SetFont(ns.FONT, 14, "")
        ln:SetText("|cff8c9eb3" .. row[1] .. "|r　" .. row[2])
        ln:SetPoint("CENTER", about, "CENTER", 0, 6 - (i - 1) * 28)
        ln:SetTextColor(0.88, 0.90, 0.93)
    end
end

local settingsGlyph
local settingsPop
local BuildTipCard

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
if ns.hui and ns.hui.SkinButton then ns.hui.SkinButton(settingsBtn) end
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

local TIP_CARD_H = 168
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

function BuildTipCard()
    if tipCard then return end
    if not ns.TipLines then return end
    local card = CreateFrame("Frame", nil, settingsPop, "BackdropTemplate")
    if ns.hui and ns.hui.BuildRoundedBG and ns.hui.layer then
        ns.hui.BuildRoundedBG(card, 8, ns.hui.layer.L2, "both", true, 1)
    else
        card:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8x8" })
        card:SetBackdropColor(0x16 / 255, 0x1A / 255, 0x22 / 255, 1)
        card:SetBackdropBorderColor(1, 1, 1, 0.1)
    end
    local qbCard = ns.QuickBar and ns.QuickBar.cardBg
    if qbCard then
        card:SetPoint("TOPLEFT", qbCard, "BOTTOMLEFT", 0, -10)
        card:SetPoint("TOPRIGHT", qbCard, "BOTTOMRIGHT", 0, -10)
    else
        card:SetPoint("BOTTOMLEFT", settingsPop, "BOTTOMLEFT", 6, 12)
        card:SetPoint("BOTTOMRIGHT", settingsPop, "BOTTOMRIGHT", -6, 12)
    end
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
    gsw:SetPoint("TOPRIGHT", card, "TOPRIGHT", -58, -8)
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
        if ns.TipLines.RefreshPreview then ns.TipLines.RefreshPreview() end
    end)

    local function TipToggle(y, label, key)
        local tg = CreateFrame("CheckButton", nil, card)
        tg:SetSize(36, 20)
        tg:EnableMouse(true)
        if ns.hui and ns.hui.ReskinToggle then ns.hui.ReskinToggle(tg) end
        local fs = card:CreateFontString(nil, "OVERLAY")
        fs:SetFont(ns.FONT, 14, "")
        fs:SetPoint("TOPLEFT", card, "TOPLEFT", 8, y + 5)
        fs:SetText(label)
        fs:SetTextColor(C_TIP_TXT[1], C_TIP_TXT[2], C_TIP_TXT[3])
        tg:SetPoint("TOPRIGHT", card, "TOPRIGHT", -8, y + 2)
        local function get() return ns.TipCfg()[key] end
        tg:SetChecked(get() and true or false)
        tg:SetScript("OnClick", function(self)
            ns.PlaySound(1)
            ns.TipCfg()[key] = not (get() and true)
            self:SetChecked(get() and true or false)
            if ns.TipLines.RefreshPreview then ns.TipLines.RefreshPreview() end
        end)
        return tg
    end

    TipToggle(-42, L["掉落来源"], "src")
    TipToggle(-66, L["BIS 推荐"], "bis")
    TipToggle(-90, L["BIS 评分"], "bisScore")
    TipToggle(-114, L["心愿标记"], "wish")
    TipToggle(-138, L["任务来源"], "quest")

    local bt = CreateFrame("Button", nil, card, "BackdropTemplate")
    bt:SetSize(44, 24)
    bt:EnableMouse(true)
    bt:SetPoint("TOPRIGHT", card, "TOPRIGHT", -8, -6)
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
        if ns.TipLines.HidePreview then ns.TipLines.HidePreview() end
    end)
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

local C_PILL_BG = {0x26 / 255, 0x29 / 255, 0x2e / 255}
local C_PILL_ED = {0x55 / 255, 0x58 / 255, 0x5e / 255}
local C_GLYPH   = {0.67, 0.70, 0.73}
local C_NUM     = {0.91, 0.93, 0.94}
local PILL_H    = 22

scaleGroup = CreateFrame("Frame", nil, settingsPop, "BackdropTemplate")
scaleGroup:SetFrameLevel(520)
scaleGroup:SetSize(94, PILL_H)
scaleGroup:SetPoint("TOPRIGHT", settingsPop, "TOPRIGHT", -12, -11)
scaleGroup:SetBackdrop({ bgFile = "Interface/ChatFrame/ChatFrameBackground" })
scaleGroup:SetBackdropColor(C_PILL_BG[1], C_PILL_BG[2], C_PILL_BG[3], 0.6)
do
    local border = CreateFrame("Frame", nil, scaleGroup)
    border:SetAllPoints()
    ns.hui.BuildRoundBorder(border, 8, C_PILL_ED)
    local hover = CreateFrame("Frame", nil, scaleGroup)
    hover:SetAllPoints()
    hover:Hide()
    ns.hui.BuildRoundBorder(hover, 8, ns.hui.ACCENT)
    scaleGroup.hover = hover
end

local function AddDivider(x)
    local d = scaleGroup:CreateTexture(nil, "OVERLAY")
    d:SetColorTexture(C_PILL_ED[1], C_PILL_ED[2], C_PILL_ED[3], 0.7)
    d:SetPoint("TOPLEFT", x, -5)
    d:SetSize(1, PILL_H - 10)
end
AddDivider(24)
AddDivider(69)

local function MakeGlyphButton(width, label, anchor)
    local bt = CreateFrame("Button", nil, scaleGroup, "BackdropTemplate")
    bt:SetFrameLevel(521)
    bt:SetSize(width, PILL_H)
    bt:SetPoint(anchor, scaleGroup, anchor, 0, 0)
    local t = bt:CreateFontString(nil, "OVERLAY")
    bt:SetFontString(t)
    t:SetFont(ns.FONT, 14, "")
    t:SetText(label)
    t:SetPoint("CENTER")
    t:SetTextColor(C_GLYPH[1], C_GLYPH[2], C_GLYPH[3])
    bt.__huiKeepTextColor = true
    if ns.hui and ns.hui.SkinButton then ns.hui.SkinButton(bt) end
    t:SetFont(ns.FONT, 14, "")
    t:SetTextColor(C_GLYPH[1], C_GLYPH[2], C_GLYPH[3])
    return bt
end

local minusBtn = MakeGlyphButton(24, "-", "TOPLEFT")
local plusBtn  = MakeGlyphButton(24, "+", "TOPRIGHT")
scaleText = CreateFrame("Button", nil, scaleGroup, "BackdropTemplate")
scaleText:SetFrameLevel(521)
scaleText:SetSize(44, PILL_H)
scaleText:SetPoint("TOPLEFT", minusBtn, "TOPRIGHT")
if ns.hui and ns.hui.SkinButton then ns.hui.SkinButton(scaleText) end
do
    local t = scaleText:CreateFontString(nil, "OVERLAY")
    t:SetFont(ns.FONT, 14, "")
    t:SetText("100%")
    t:SetPoint("CENTER")
    t:SetTextColor(C_NUM[1], C_NUM[2], C_NUM[3])
    scaleText.text = t
end

local function HoverOn(glyph)
    if scaleGroup.hover then scaleGroup.hover:Show() end
    if glyph then glyph:SetTextColor(ns.hui.ACCENT[1], ns.hui.ACCENT[2], ns.hui.ACCENT[3]) end
end
local function HoverOff(glyph)
    if scaleGroup.hover then scaleGroup.hover:Hide() end
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

plusBtn:SetScript("OnEnter", function(self) HoverOn(self:GetFontString()) ScaleTooltip(self, L["放大界面"]) end)
plusBtn:SetScript("OnLeave", function(self) HoverOff(self:GetFontString()) GameTooltip:Hide() end)
minusBtn:SetScript("OnEnter", function(self) HoverOn(self:GetFontString()) ScaleTooltip(self, L["缩小界面"]) end)
minusBtn:SetScript("OnLeave", function(self) HoverOff(self:GetFontString()) GameTooltip:Hide() end)

scaleText:SetScript("OnEnter", function(self)
    HoverOn()
    GameTooltip:SetOwner(self, "ANCHOR_BOTTOM")
    GameTooltip:ClearLines()
    GameTooltip:AddLine(L["界面大小"], 1, 1, 1, true)
    GameTooltip:AddLine(L["点击复位 100%"], 0.7, 0.75, 0.8, true)
    GameTooltip:Show()
end)
scaleText:SetScript("OnLeave", function(self) HoverOff() GameTooltip:Hide() end)
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

local function RevealCollect(root)
    local order, queue = {}, { root }
    local i = 1
    while i <= #queue do
        local fr = queue[i]
        i = i + 1
        if fr.GetChildren then
            local kids = { fr:GetChildren() }
            for _, c in ipairs(kids) do
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
    if q and not ghost then
        for i = 1, #q do
            local cfr = q[i]
            if cfr and cfr.Show then pcall(cfr.Show, cfr) end
        end
    end
    reveal.q = nil
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
    if #order < 20 then return end
    for i = 1, #order do
        local cfr = order[i]
        if cfr.Hide then pcall(cfr.Hide, cfr) end
    end
    revealedOnce = true
    reveal.on = true
    reveal.q = order
    reveal.total = #order
    reveal.done = 0
    reveal.k = 3
    reveal.lastT = nil
    reveal.heavy = nil
    revealBar:Show()
    RevealPaint()
end

f:HookScript("OnUpdate", function()
    if not reveal.on then return end
    local now = debugprofilestop()
    local dt = now - (reveal.lastT or now)
    reveal.lastT = now
    if dt > 45 then
        reveal.k = math.max(1, (reveal.k or 2) - 1)
        reveal.pause = 1
    elseif dt < 20 then
        reveal.k = math.min(2, (reveal.k or 2) + 1)
        reveal.pause = nil
    end
    local q = reveal.q
    if not q or #q == 0 then
        RevealFinishAll()
        return
    end
    if not reveal.pause and not (DungeonsForeverDB and DungeonsForeverDB.dfGhost) then
        local k = reveal.k or 2
        for _ = 1, k do
            local cfr = q[1]
            if not cfr then break end
            table.remove(q, 1)
            local t0 = debugprofilestop()
            if cfr.Show then pcall(cfr.Show, cfr) end
            local cost = debugprofilestop() - t0
            if cost > 30 then
                local nm = "?"
                if cfr.GetName then
                    local gn = cfr:GetName()
                    if type(gn) == "string" and gn ~= "" then nm = gn end
                end
                reveal.heavy = reveal.heavy or {}
                local h = reveal.heavy
                h[#h + 1] = format("%d%%:%s:%.0f", math.floor(reveal.done / math.max(1, reveal.total) * 100 + 0.5), nm, cost)
            end
            reveal.done = reveal.done + 1
        end
    end
    RevealPaint()
    if #q == 0 then RevealFinishAll() end
end)

f:HookScript("OnHide", function()
    if reveal.on then RevealFinishAll() end
end)

function ns.Open()
    if not f:IsShown() then
        f:Show()
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
        icon = "Interface\\AddOns\\DungeonsForever\\Media\\DungeonsForever.blp",
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
SlashCmdList["DUNGEONSFOREVER"] = function(msg)
    local cmd = strtrim(msg or "")
    if cmd == "" then
        ns.Toggle()
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
    print("  /df fb|副本 · tb|团本 · zy|专业 · ts|探索 · hp|藏品 · wm|声望 · bis|配装 · zn|指南 — " .. L["直达对应页"])
    print("  /dfspeed — " .. L["载入速度"]
          .. "（" .. L["省电"] .. " / " .. L["标准"] .. " / " .. L["激进"] .. "）")
    print("  /dfgate — " .. L["进度条"] .. "（demo / off）")
end

local SUB_RELEASE = {
    { "Raids", "raidPage", "RaidModule" },
    { "Professions", "profPage", "ProfModule" },
    { "Explore", "explorePage", "ExploreModule" },
    { "Collections", "collectionPage", "CollectionModule" },
    { "Factions", "factionPage", "FactionModule" },
    { "Bis", "bisPage", "BisModule" },
    { "Tier", "tierPage", "TierModule" },
    { "PvP", "pvpPage", "PvPModule" },
    { "Gear", "gearPage", "GearModule" },
}
local function HasFrameRef(v, depth)
    local t = type(v)
    if t == "userdata" then return true end
    if t ~= "table" or depth > 3 then return false end
    if type(v.GetObjectType) == "function" then return true end
    for _, x in pairs(v) do
        if HasFrameRef(x, depth + 1) then return true end
    end
    return false
end
function ns.ReleasePages()
    local nsG = _G.DF_NS
    local U = nsG and nsG.DungeonUI
    if not U then return end
    for _, e in ipairs(SUB_RELEASE) do
        local M0 = nsG[e[3]]
        if M0 and M0.building and not M0.built then
            if type(C_Timer) == "table" and type(C_Timer.After) == "function" then
                C_Timer.After(2, function() ns.ReleasePages() end)
            end
            return
        end
    end
    for _, e in ipairs(SUB_RELEASE) do
        local M = nsG[e[3]]
        local pg = U[e[2]]
        if M and M.built and pg then
            local kids = { pg:GetChildren() }
            for i = 1, #kids do
                kids[i]:Hide()
                kids[i]:SetParent(nil)
            end
            for k, v in pairs(M) do
                if HasFrameRef(v, 0) then M[k] = nil end
            end
            M.built = false
            if U.subBuilt then U.subBuilt[e[1]] = nil end
        end
    end
    collectgarbage("collect")
end
