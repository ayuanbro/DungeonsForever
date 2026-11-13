local ADDON, ns = ...

local MW = {}
ns.MapWindowModule = MW

local L = ns.L
local M = ns.MapModule
if type(M) ~= "table" then return end

local EDGE = 8
local TOP_H = 28
local TOOL_H = 34
local BOT_H = 8
local GAP = 8
local SIDE_W = 330
local MAP_W = 1284
local MAP_H = 856
local STEP_W, STEP_H = 108, 28
local PILL_W, PILL_H = 96, 24
local MINI_W, MINI_H, MINI_EDGE = 520, 360, 10
local MINI_TRIM_R = 5
local MINI_TRIM_B = 5
local PIN_REF_W = 642
local SCALE_MIN, SCALE_MAX = 0.7, 1.3
local SCALE_BASE = 0.66
local MINI_SCALE_BASE = 0.76
local winK = 1
local GLYPH = 0xa0 / 255
local TEXT_C = { 0.95, 0.96, 0.98 }

local win, view, mini, mview
local R
local SKIN = "native"
local applySkin

local function addonOn(name)
    local C = _G.C_AddOns
    if C and C.IsAddOnLoaded then
        local ok, v = pcall(C.IsAddOnLoaded, name)
        if ok then return v and true or false end
    end
    if _G.IsAddOnLoaded then
        local ok, _, v = pcall(_G.IsAddOnLoaded, name)
        if ok then return v and true or false end
    end
    return false
end

local function autoSkinPick()
    if addonOn("Leatrix_Maps") then return "hui" end
    if addonOn("NDui") or _G.NDuiDB then return "hui" end
    local E = _G.E
    if _G.ElvUI or (type(E) == "table" and E.private) then
        local sk = E and E.private and E.private.skins and E.private.skins.blizzard
        if not sk then return "hui" end
        if sk.enable ~= false and sk.worldmap ~= false then return "hui" end
    end
    local edb = _G.EllesmereUIDB
    if edb then
        local killed
        local EU = _G.EllesmereUI
        if EU and EU.BlizzWindowSkinsKilled then
            local ok, v = pcall(EU.BlizzWindowSkinsKilled)
            if ok then killed = v end
        end
        local styles = edb.blizzWindowSkinStyles
        local style = styles and styles.worldmap
        local on = edb.reskinWorldMap ~= false
        if killed or edb.disableWindowSkins == true or style == "blizzard" then on = false end
        if on then return "hui" end
    end
    return "native"
end
MW.AutoSkin = autoSkinPick

local function skinFromStore()
    local s = M.MapStore and M.MapStore()
    local v = s and s.mapSkin
    if v == "hui" then return "hui" end
    if v == "native" then return "native" end
    return autoSkinPick()
end

local layout
local layoutMini
local miniShell
local floorWant = false

local MINI_ALPHA_DEF = 0.6
local MINI_ALPHA_STEPS = { 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0 }
local FADE_DELAY = 2
local FADE_DUR = 0.5

local function miniAlphaVal()
    local s = M.MapStore and M.MapStore()
    local v = s and s.miniAlpha
    if type(v) ~= "number" or v < 0.1 or v > 1 then return MINI_ALPHA_DEF end
    return v
end

local fadeDelayT
local fadeTicker

local function fadeStop()
    if fadeDelayT then fadeDelayT:Cancel() fadeDelayT = nil end
    if fadeTicker then fadeTicker:Cancel() fadeTicker = nil end
end

local function miniFloorVis()
    local b = mini and mini.floorBar
    if not b then return end
    if b.__has and floorWant and mini:IsShown() then
        if not b:IsShown() then b:SetAlpha(1) end
        b:Show()
    else
        b:Hide()
    end
end

local function fadeStart(target)
    fadeStop()
    if not (mini and mini:IsShown()) then return end
    local bar = mini.floorBar
    local from, barFrom = mini:GetAlpha(), (bar and bar:IsShown() and bar:GetAlpha()) or 0
    if math.abs(from - target) < 0.01 and not (bar and bar:IsShown()) then
        mini:SetAlpha(target)
        floorWant = false
        miniFloorVis()
        return
    end
    local el = 0
    fadeTicker = C_Timer.NewTicker(0.03, function(t)
        el = el + 0.03
        local k = math.min(1, el / FADE_DUR)
        k = k * k * (3 - 2 * k)
        if mini and mini:IsShown() then
            mini:SetAlpha(from + (target - from) * k)
            if bar and bar:IsShown() then
                bar:SetAlpha(barFrom * (1 - k))
            end
        end
        if k >= 1 then
            t:Cancel()
            fadeTicker = nil
            if bar and bar:IsShown() then bar:SetAlpha(0) end
            floorWant = false
            miniFloorVis()
        end
    end)
end

local function miniFadeSoon()
    fadeStop()
    fadeDelayT = C_Timer.NewTimer(FADE_DELAY, function()
        fadeDelayT = nil
        if not (mini and mini:IsShown()) then return end
        if mini:IsMouseOver() then return end
        local bar = mini.floorBar
        if bar and bar:IsShown() and bar:IsMouseOver() then return end
        if mini.pill and mini.pill:IsShown() and (mini.pill.__hover or mini.pill:IsMouseOver()) then return end
        fadeStart(miniAlphaVal())
    end)
end

local function miniFloorShow()
    fadeStop()
    floorWant = true
    miniFloorVis()
end

local function applyMiniAlpha(hovered)
    if not mini then return end
    if hovered == true then
        fadeStop()
        mini:SetAlpha(1)
        local bar = mini.floorBar
        if bar and bar:IsShown() then bar:SetAlpha(1) end
    elseif hovered == false then
        miniFadeSoon()
    else
        fadeStop()
        mini:SetAlpha(miniAlphaVal())
    end
end

local function cursorScaled()
    local x, y = GetCursorPosition()
    local s = UIParent and UIParent:GetEffectiveScale() or 1
    if not s or s <= 0 then s = 1 end
    return x / s, y / s
end

local function newBtn(parent, text, w, h)
    local bt
    if ns.CreateButton then
        local ok, v = pcall(ns.CreateButton, parent)
        if ok and v then bt = v end
    end
    if not bt then bt = CreateFrame("Button", nil, parent, "UIPanelButtonTemplate") end
    bt:SetSize(w or 80, h or 24)
    if text and bt.SetText then bt:SetText(text) end
    local fs = bt.GetFontString and bt:GetFontString()
    if fs and fs.SetFont then
        pcall(fs.SetFont, fs, ns.FONT or fs.GetFont(), 14, "")
    end
    if bt.SetPushedTextOffset then pcall(bt.SetPushedTextOffset, bt, 0, 0) end
    return bt
end

local function nativeBtn(parent, text, w, h)
    local bt = CreateFrame("Button", nil, parent, "UIPanelButtonTemplate")
    bt:SetSize(w or 84, h or 28)
    if text then bt:SetText(text) end
    local fs = bt.GetFontString and bt:GetFontString()
    if fs and fs.SetFont then
        pcall(fs.SetFont, fs, ns.FONT or fs.GetFont(), 12, "")
    end
    if bt.SetPushedTextOffset then pcall(bt.SetPushedTextOffset, bt, 0, 0) end
    return bt
end

local function tabSelect(bt, on)
    if not bt then return end
    if on then
        if PanelTemplates_SelectTab then pcall(PanelTemplates_SelectTab, bt) end
    else
        if PanelTemplates_DeselectTab then pcall(PanelTemplates_DeselectTab, bt) end
        bt:Enable()
    end
end

local function tabBtn(parent)
    local bt = CreateFrame("Button", nil, parent, "PanelTabButtonTemplate")
    bt:SetSize(60, 32)
    local fs = bt:GetFontString()
    if fs and fs.SetFont then
        pcall(fs.SetFont, fs, ns.FONT or fs.GetFont(), 12, "")
    end
    return bt
end

local function dragUpdate(self)
    if type(IsMouseButtonDown) == "function" and not IsMouseButtonDown("LeftButton") then
        self.__lx, self.__ly = nil, nil
        self:SetScript("OnUpdate", nil)
        MW.Sync()
        return
    end
    local ZM = ns.MapZoom
    if not (ZM and view) then return end
    local x, y = cursorScaled()
    local lx, ly = self.__lx or x, self.__ly or y
    self.__lx, self.__ly = x, y
    local dx, dy = x - lx, y - ly
    if dx == 0 and dy == 0 then return end
    local us = UIParent and UIParent:GetEffectiveScale() or 1
    local ws = win and win.GetEffectiveScale and win:GetEffectiveScale() or 1
    if ws and ws > 0 and us and us > 0 then
        local k2 = us / ws
        dx, dy = dx * k2, dy * k2
    end
    local cw, ch = view.cw or MAP_W, view.ch or MAP_H
    local mx, my = ZM.Limits(cw, ch)
    ZM.x, ZM.y = ZM.x + dx, ZM.y + dy
    ZM.ClampTo(mx, my)
    layout()
end

local function buildMapContent(stage)
    local canvas = CreateFrame("Frame", nil, stage)
    canvas:SetPoint("TOPLEFT", stage, "TOPLEFT", 0, 0)
    canvas:SetFrameLevel(stage:GetFrameLevel() + 1)
    local v2 = { canvas = canvas }

    local tiles = {}
    for i = 1, M.N do
        local t = canvas:CreateTexture(nil, "ARTWORK")
        t:SetTexCoord(0, 1, 0, 1)
        t:Hide()
        tiles[i] = t
    end
    v2.tiles = tiles

    local custom = canvas:CreateTexture(nil, "ARTWORK")
    custom:SetTexCoord(0, 1, 0, 1)
    custom:Hide()
    v2.custom = custom

    local route = CreateFrame("Frame", nil, stage)
    route:SetPoint("TOPLEFT", stage, "TOPLEFT", 0, 0)
    route:SetFrameLevel(stage:GetFrameLevel() + 2)
    route:Hide()
    v2.route = route
    v2.routePool = {}
    v2.routeUsed = 0

    local pins = CreateFrame("Frame", nil, stage)
    pins:SetPoint("TOPLEFT", stage, "TOPLEFT", 0, 0)
    pins:SetFrameLevel(stage:GetFrameLevel() + 3)
    v2.pins = pins
    R.buildPinPool(v2)
    return v2
end

local function applyScale(k, save)
    if not win then return end
    k = math.floor((k * 100) + 0.5) / 100
    if k < SCALE_MIN then k = SCALE_MIN end
    if k > SCALE_MAX then k = SCALE_MAX end
    if type(InCombatLockdown) == "function" and InCombatLockdown() then return end
    winK = k * SCALE_BASE
    local w = EDGE * 2 + GAP + SIDE_W + MAP_W * winK
    local h = TOP_H + TOOL_H + MAP_H * winK + BOT_H
    pcall(win.SetSize, win, w, h)
    if view then pcall(view.SetSize, view, w, MAP_H * winK) end
    MW.winScale = k
    if win.pillLabel then
        win.pillLabel:SetText(math.floor((k * 100) + 0.5) .. "%")
    end
    if save then
        local s = M.MapStore and M.MapStore()
        if s then s.mapWinScale = (k ~= 1.0) and k or nil end
    end
    layout()
    MW.Sync()
end

local function buildScalePill(f)
    local pill = CreateFrame("Frame", nil, f)
    pill:SetSize(STEP_W, STEP_H)
    pill:SetPoint("TOPRIGHT", f, "TOPRIGHT", -EDGE - 2, -(TOP_H + (TOOL_H - STEP_H) / 2 - 5.5))
    win.pill = pill
    local minus = nativeBtn(pill, "-", 24, STEP_H)
    minus:SetPoint("LEFT", pill, "LEFT", 0, 0)
    local plus = nativeBtn(pill, "+", 24, STEP_H)
    plus:SetPoint("RIGHT", pill, "RIGHT", 0, 0)
    local lab = pill:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
    lab:SetPoint("CENTER", pill, "CENTER", 0, 0)
    lab:SetText("100%")
    win.pillLabel = lab
    minus:SetScript("OnClick", function()
        applyScale((MW.winScale or 1) / 1.15, true)
    end)
    plus:SetScript("OnClick", function()
        applyScale((MW.winScale or 1) * 1.15, true)
    end)
end

local function applyMiniScale(k, save)
    if not mini then return end
    k = math.floor((k * 100) + 0.5) / 100
    if k < SCALE_MIN then k = SCALE_MIN end
    if k > SCALE_MAX then k = SCALE_MAX end
    if type(InCombatLockdown) == "function" and InCombatLockdown() then return end
    MW.miniScale = k
    pcall(mini.SetScale, mini, k * MINI_SCALE_BASE)
    if mini.pillLabel then
        mini.pillLabel:SetText(math.floor((k * 100) + 0.5) .. "%")
    end
    if save then
        local s = M.MapStore and M.MapStore()
        if s then s.miniWinScale = (k ~= 1.0) and k or nil end
    end
    if mview and layoutMini then layoutMini() end
end

local function buildMiniScalePill(f)
    local pill = CreateFrame("Frame", nil, f)
    pill:SetSize(PILL_W, PILL_H)
    pill:SetPoint("BOTTOMLEFT", f, "BOTTOMLEFT", 6, 6)
    pill:SetFrameLevel(f:GetFrameLevel() + 10)
    if ns.hui and ns.hui.BuildRoundedBG and ns.hui.layer then
        ns.hui.BuildRoundedBG(pill, 12, ns.hui.layer.L2, "both", true, 1)
    end
    local lab = pill:CreateFontString(nil, "OVERLAY")
    lab:SetFont(ns.FONT, 13, "")
    lab:SetPoint("CENTER", pill, "CENTER", 0, 0)
    lab:SetTextColor(0.91, 0.93, 0.94)
    lab:SetText("100%")
    mini.pillLabel = lab
    local Z_GLYPH = { 0.67, 0.70, 0.73 }
    for i = 1, 2 do
        local bt = CreateFrame("Button", nil, pill)
        bt:SetSize(24, 24)
        if i == 1 then
            bt:SetPoint("LEFT", pill, "LEFT", 2, 0)
        else
            bt:SetPoint("RIGHT", pill, "RIGHT", -2, 0)
        end
        bt:EnableMouse(true)
        if ns.hui and ns.hui.BuildCapsule then
            bt.__hov = ns.hui.BuildCapsule(bt, 8, ns.hui.layer.L4, 1, 2)
            for _, hv in ipairs(bt.__hov) do hv:Hide() end
        end
        local t = bt:CreateFontString(nil, "OVERLAY")
        t:SetFont(ns.FONT, 20, "")
        t:SetPoint("CENTER", 0, 1)
        t:SetText(i == 1 and "-" or "+")
        t:SetTextColor(Z_GLYPH[1], Z_GLYPH[2], Z_GLYPH[3])
        bt:SetScript("OnEnter", function(self)
            if bt.__hov then
                for _, hv in ipairs(bt.__hov) do hv:Show() end
            end
            t:SetTextColor(1, 1, 1)
        end)
        bt:SetScript("OnLeave", function(self)
            if bt.__hov then
                for _, hv in ipairs(bt.__hov) do hv:Hide() end
            end
            t:SetTextColor(Z_GLYPH[1], Z_GLYPH[2], Z_GLYPH[3])
        end)
        bt:SetScript("OnClick", function()
            local cur = MW.miniScale or 1
            applyMiniScale(cur * ((i == 1) and (1 / 1.15) or 1.15), true)
        end)
    end
    pill:SetScript("OnEnter", function(self) self.__hover = true end)
    pill:SetScript("OnLeave", function(self) self.__hover = nil end)
    pill:Hide()
    return pill
end

local function showSettingsMenu(btn)
    if not (ns.hui and ns.hui.ShowMenu) then return end
    local s = M.MapStore and M.MapStore()
    local cur = math.floor(((MW.winScale or 1) * 100) + 0.5)
    ns.hui.ShowMenu({
        {
            text = L["原生皮肤"],
            checked = MW.SkinMode() == "native",
            func = function()
                MW.SetSkin("native")
                showSettingsMenu(btn)
            end,
        },
        {
            text = L["现代皮肤"],
            checked = MW.SkinMode() == "hui",
            func = function()
                MW.SetSkin("hui")
                showSettingsMenu(btn)
            end,
        },
        {
            text = L["自适应地图皮肤"],
            checked = MW.SkinMode() == "auto",
            func = function()
                MW.SetSkin("auto")
                showSettingsMenu(btn)
            end,
        },
        {
            text = format(L["界面缩放：%d%%"], cur),
            color = "|cffe0c060",
            func = function()
                applyScale(1.0, true)
                showSettingsMenu(btn)
            end,
        },
        {
            text = L["界面缩放大"],
            func = function()
                applyScale((MW.winScale or 1) + 0.05, true)
                showSettingsMenu(btn)
            end,
        },
        {
            text = L["界面缩放小"],
            func = function()
                applyScale((MW.winScale or 1) - 0.05, true)
                showSettingsMenu(btn)
            end,
        },
        {
            text = L["副本地图自动打开迷你地图"],
            checked = not (s and s.autoMini == false),
            func = function()
                local st = M.MapStore and M.MapStore()
                if not st then return end
                if st.autoMini == false then
                    st.autoMini = nil
                else
                    st.autoMini = false
                end
            end,
        },
        {
            text = L["M键打开副本地图"],
            checked = not (s and s.mKeyOpen == false),
            func = function()
                local st = M.MapStore and M.MapStore()
                if not st then return end
                if st.mKeyOpen == false then
                    st.mKeyOpen = nil
                else
                    st.mKeyOpen = false
                end
            end,
        },
        {
            text = L["关闭副本地图时切换到迷你窗口"],
            checked = not (s and s.closeToMini == false),
            func = function()
                local st = M.MapStore and M.MapStore()
                if not st then return end
                if st.closeToMini == false then
                    st.closeToMini = nil
                else
                    st.closeToMini = false
                end
            end,
        },
        {
            text = format(L["迷你地图透明度：%d%%"], math.floor(miniAlphaVal() * 100 + 0.5)),
            color = "|cffe0c060",
            func = function()
                local st = M.MapStore and M.MapStore()
                if not st then return end
                local cur = miniAlphaVal()
                local nxt = MINI_ALPHA_STEPS[1]
                for i = 1, #MINI_ALPHA_STEPS do
                    if math.abs(MINI_ALPHA_STEPS[i] - cur) < 0.001 then
                        nxt = MINI_ALPHA_STEPS[i % #MINI_ALPHA_STEPS + 1]
                        break
                    end
                end
                if math.abs(nxt - MINI_ALPHA_DEF) < 0.001 then
                    st.miniAlpha = nil
                else
                    st.miniAlpha = nxt
                end
                applyMiniAlpha()
                showSettingsMenu(btn)
            end,
        },
    }, { owner = btn, anchor = btn })
end

local function showDungeonMenu(btn)
    local items = {}
    local dd = ns.DungeonData and ns.DungeonData.dungeons
    if type(dd) == "table" then
        for i = 1, #dd do
            local d = dd[i]
            if d and d.id and R.hasArt(d.id) then
                items[#items + 1] = {
                    text = d.name or d.id,
                    checked = (d.id == MW.curId),
                    func = function()
                        MW.Open(d.id)
                    end,
                }
            end
        end
    end
    if #items > 0 and ns.hui and ns.hui.ShowMenu then
        ns.hui.ShowMenu(items, { owner = btn, anchor = btn })
    end
end

local function miniStrata(st)
    if not mini then return end
    local function walk(f)
        pcall(f.SetFrameStrata, f, st)
        for _, c in ipairs({ f:GetChildren() }) do walk(c) end
    end
    walk(mini)
    if miniShell then pcall(miniShell.SetFrameStrata, miniShell, st) end
end

local function backToNative()
    local s = M.MapStore and M.MapStore()
    local wantMini = (not s or s.closeToMini ~= false) and not MW.miniSkip and MW.curId
        and R and R.hasArt and R.hasArt(MW.curId)
    if wantMini and win and win:IsShown() then
        MW.MiniOpen()
    else
        MW.Close()
    end
    local WM = WorldMapFrame
    if not WM then return end
    if ShowUIPanel then
        pcall(ShowUIPanel, WM)
    else
        pcall(WM.Show, WM)
    end
end

local function bindTitleDrag(bt, hover)
    local down
    bt:SetScript("OnMouseDown", function(_, btn)
        if btn ~= "LeftButton" then return end
        down = { cursorScaled() }
        local f = bt:GetParent()
        if f and f.StartMoving then f:StartMoving() end
    end)
    bt:SetScript("OnMouseUp", function(self, btn)
        if btn ~= "LeftButton" then return end
        local f = self:GetParent()
        if f and f.StopMovingOrSizing then f:StopMovingOrSizing() end
        local x, y = cursorScaled()
        local dx, dy = 99, 99
        if down then dx, dy = math.abs(x - down[1]), math.abs(y - down[2]) end
        down = nil
        if dx + dy < 5 then showDungeonMenu(self) end
    end)
    if hover then
        bt:SetScript("OnEnter", function(self) hover(self, true) end)
        bt:SetScript("OnLeave", function(self) hover(self, false) end)
    end
end

local function ensure()
    if win then return view end
    R = ns.MapWorldModule and ns.MapWorldModule.Render
    if not R then return nil end
    if M.LoadMapState then pcall(M.LoadMapState) end

    local f = CreateFrame("Frame", "DungeonsForeverMapWindow", UIParent, "PortraitFrameTemplate")
    f:SetSize(EDGE * 2 + GAP + SIDE_W + MAP_W, TOP_H + TOOL_H + MAP_H + BOT_H)
    f:SetPoint("CENTER")
    f:SetFrameStrata("HIGH")
    f:SetFrameLevel(400)
    f:SetScale(1)
    f:SetMovable(true)
    f:EnableMouse(true)
    f:SetClampedToScreen(true)
    f:SetScript("OnMouseDown", function(_, btn)
        if btn == "LeftButton" then f:StartMoving() end
    end)
    f:SetScript("OnMouseUp", function()
        f:StopMovingOrSizing()
    end)
    f:Hide()
    local pc = f.PortraitContainer
    if pc then
        pc:SetAlpha(1)
        local pt
        for _, reg in ipairs({ pc:GetRegions() }) do
            local nm = reg.GetName and reg:GetName()
            if nm and nm:find("Portrait") then pt = reg end
        end
        if pt then
            pt:SetAlpha(0)
            local mask = pc.CircleMask
            local lgBg = pc:CreateTexture(nil, "ARTWORK", nil, 1)
            lgBg:SetColorTexture(0.04, 0.05, 0.07, 1)
            lgBg:SetSize(56, 56)
            lgBg:SetPoint("CENTER", pt, "CENTER", 0, 2)
            local lg = pc:CreateTexture(nil, "ARTWORK", nil, 2)
            lg:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\Brand\\DungeonsForever.blp")
            lg:SetSize(42, 42)
            lg:SetPoint("CENTER", lgBg, "CENTER", 0, 0)
            lg:SetTexCoord(0, 1, 0, 1)
            if mask and lgBg.AddMaskTexture then
                pcall(lgBg.AddMaskTexture, lgBg, mask)
                pcall(lg.AddMaskTexture, lg, mask)
            end
            f.logoBg = lgBg
            f.logo = lg
        end
    end
    for _, reg in ipairs({ f:GetRegions() }) do
        local nm = reg.GetName and reg:GetName()
        if nm and nm:find("Portrait") then reg:Hide() end
    end
    win = f

    local strip = CreateFrame("Frame", nil, f)
    strip:SetSize(560, TOP_H)
    strip:SetPoint("TOPLEFT", f, "TOPLEFT", 0, 0)
    strip:EnableMouse(true)
    strip:SetScript("OnMouseDown", function() f:StartMoving() end)
    strip:SetScript("OnMouseUp", function() f:StopMovingOrSizing() end)

    local tb = CreateFrame("Button", "DungeonsForeverMapTitle", f)
    tb:SetPoint("TOPLEFT", f, "TOPLEFT", 44, 0)
    tb:SetPoint("BOTTOMRIGHT", f, "TOPRIGHT", -140, -TOP_H)
    local tfs = f.TitleContainer and f.TitleContainer.TitleText
    bindTitleDrag(tb, function(_, on)
        if not tfs then return end
        if on then tfs:SetTextColor(1, 1, 1) else tfs:SetTextColor(1, 0.82, 0) end
    end)
    win.titleFS = tfs
    win.titleBtn = tb

    local fb = {}
    for i = 1, M.MAX_LAYERS do
        local bt = tabBtn(f)
        bt.__idx = i
        bt.tabBtn = true
        bt:SetScript("OnClick", function(self)
            local i2 = self.__idx
            if not i2 then return end
            local layers = M.LayersFor(MW.curId)
            if not (layers and layers[i2]) then return end
            if i2 == (MW.curLayer or 1) then return end
            if ns.MapZoom then ns.MapZoom.Reset() end
            MW.subFollow = false
            MW.curLayer = i2
            applyScale(MW.winScale or 1)
            MW.Sync()
        end)
        bt:Hide()
        fb[i] = bt
    end
    win.floorBtns = fb

    local cb = f.CloseButton
    if not cb then
        cb = CreateFrame("Button", nil, f, "UIPanelCloseButton")
        cb:SetPoint("TOPRIGHT", f, "TOPRIGHT", 0, 3)
    end
    cb:SetScript("OnClick", function()
        local s = M.MapStore and M.MapStore()
        if (not s or s.closeToMini ~= false) and not MW.miniSkip and MW.curId and R.hasArt(MW.curId) then
            MW.MiniOpen()
            return
        end
        MW.Close()
    end)
    cb:SetFrameLevel(511)
    win.closeBtn = cb

    buildScalePill(f)

    local mb = nativeBtn(f, L["小地图"])
    mb:SetPoint("RIGHT", win.pill, "LEFT", -6, 0)
    mb:SetScript("OnClick", function() MW.MiniOpen() end)
    win.miniBtn = mb

    local sb = nativeBtn(f, L["设置"])
    sb:SetPoint("RIGHT", mb, "LEFT", -6, 0)
    sb:SetScript("OnClick", function(self) showSettingsMenu(self) end)
    win.setBtn = sb

    local pb = nativeBtn(f, L["图钉显示"])
    pb:SetPoint("RIGHT", sb, "LEFT", -6, 0)
    pb:SetScript("OnClick", function(self) M.ShowPinMenu(self) end)
    pb:Hide()

    local rb = nativeBtn(f, L["路线显示"])
    rb:SetPoint("RIGHT", pb, "LEFT", -6, 0)
    rb:SetScript("OnClick", function(self, button)
        R.routeToggle(self, button)
        MW.Sync()
    end)
    rb:Hide()
    win.routeBtn = rb

    local rsb = nativeBtn(f, L["路线设置"])
    rsb:SetPoint("RIGHT", rb, "LEFT", -6, 0)
    rsb:SetScript("OnClick", function(self)
        if M.ShowRouteSetMenu then M.ShowRouteSetMenu(self) end
    end)
    rsb:Hide()
    win.routeSetBtn = rsb

    local wb = nativeBtn(f, L["返回原生地图"], 112, 28)
    wb:SetPoint("RIGHT", cb, "LEFT", -8, 0)
    wb:SetScript("OnClick", function() backToNative() end)
    win.worldBtn = wb

    local baseL = f:GetFrameLevel()
    strip:SetFrameLevel(baseL + 1)
    tb:SetFrameLevel(baseL + 6)
    for i = 1, M.MAX_LAYERS do fb[i]:SetFrameLevel(baseL + 6) end
    cb:SetFrameLevel(baseL + 111)
    mb:SetFrameLevel(baseL + 8)
    sb:SetFrameLevel(baseL + 8)
    pb:SetFrameLevel(baseL + 8)
    rb:SetFrameLevel(baseL + 8)
    rsb:SetFrameLevel(baseL + 8)
    wb:SetFrameLevel(baseL + 111)

    local topL = baseL
    for _, c in ipairs({ f:GetChildren() }) do
        local l = c.GetFrameLevel and c:GetFrameLevel() or 0
        if l > topL then topL = l end
    end
    cb:SetFrameLevel(topL + 2)
    wb:SetFrameLevel(topL + 2)

    local huiShell = CreateFrame("Frame", nil, f, "BackdropTemplate")
    huiShell:SetAllPoints(f)
    huiShell:SetFrameLevel(baseL + 1)
    if ns.hui and ns.hui.SkinPopup and ns.hui.layer then
        pcall(ns.hui.SkinPopup, huiShell, 10, "both", ns.hui.layer.L0)
    end
    huiShell:Hide()

    local htb = CreateFrame("Button", "DungeonsForeverMapTitleHui", f)
    htb:SetSize(200, 24)
    htb:SetPoint("TOPLEFT", f, "TOPLEFT", EDGE + 2, -15)
    htb:SetFrameLevel(baseL + 8)
    local htfs = htb:CreateFontString(nil, "OVERLAY")
    htfs:SetFont(ns.FONT, 16, "")
    htfs:SetPoint("LEFT", htb, "LEFT", 0, 0)
    htfs:SetTextColor(TEXT_C[1], TEXT_C[2], TEXT_C[3])
    htb:SetFontString(htfs)
    bindTitleDrag(htb, function(_, on)
        if on then
            htfs:SetTextColor(1, 1, 1)
        else
            htfs:SetTextColor(TEXT_C[1], TEXT_C[2], TEXT_C[3])
        end
    end)
    htb:Hide()

    local hfb = {}
    for i = 1, M.MAX_LAYERS do
        local bt = newBtn(f, "", 64, 28)
        bt.__idx = i
        bt:SetScript("OnClick", function(self)
            local i2 = self.__idx
            if not i2 then return end
            local layers = M.LayersFor(MW.curId)
            if not (layers and layers[i2]) then return end
            if i2 == (MW.curLayer or 1) then return end
            if ns.MapZoom then ns.MapZoom.Reset() end
            MW.subFollow = false
            MW.curLayer = i2
            applyScale(MW.winScale or 1)
            MW.Sync()
        end)
        bt:Hide()
        hfb[i] = bt
    end

    local hcb = CreateFrame("Button", nil, f, "BackdropTemplate")
    hcb:SetSize(30, 30)
    hcb:SetPoint("TOPRIGHT", f, "TOPRIGHT", -12, -12)
    hcb:SetFrameLevel(topL + 2)
    if ns.hui and ns.hui.SkinButton then pcall(ns.hui.SkinButton, hcb, { noFrame = true }) end
    local hct = hcb:CreateTexture(nil, "ARTWORK")
    hct:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\textures\\YY_close")
    hct:SetSize(26, 26)
    hct:SetPoint("CENTER", hcb, "CENTER", 0, 0.4)
    hct:SetVertexColor(GLYPH, GLYPH, GLYPH)
    hcb:SetScript("OnClick", function()
        local s = M.MapStore and M.MapStore()
        if (not s or s.closeToMini ~= false) and not MW.miniSkip and MW.curId and R.hasArt(MW.curId) then
            MW.MiniOpen()
            return
        end
        MW.Close()
    end)
    hcb:SetScript("OnEnter", function() hct:SetVertexColor(1, 1, 1) end)
    hcb:SetScript("OnLeave", function() hct:SetVertexColor(GLYPH, GLYPH, GLYPH) end)

    local hmb = newBtn(f, L["小地图"], 76, 28)
    hmb:SetPoint("RIGHT", hcb, "LEFT", -6, 0)
    hmb:SetFrameLevel(topL + 2)
    hmb:SetScript("OnClick", function() MW.MiniOpen() end)

    local hsb = newBtn(f, L["设置"], 66, 28)
    hsb:SetPoint("RIGHT", hmb, "LEFT", -6, 0)
    hsb:SetFrameLevel(topL + 2)
    hsb:SetScript("OnClick", function(self) showSettingsMenu(self) end)

    local hpb = newBtn(f, L["图钉显示"], 84, 28)
    hpb:SetPoint("RIGHT", hsb, "LEFT", -6, 0)
    hpb:SetFrameLevel(topL + 2)
    hpb:SetScript("OnClick", function(self) M.ShowPinMenu(self) end)
    hpb:Hide()

    local hrb = newBtn(f, L["路线显示"], 84, 28)
    hrb:SetPoint("RIGHT", hpb, "LEFT", -6, 0)
    hrb:SetFrameLevel(topL + 2)
    hrb:SetScript("OnClick", function(self, button)
        R.routeToggle(self, button)
        MW.Sync()
    end)
    hrb:Hide()

    local hrsb = newBtn(f, L["路线设置"], 84, 28)
    hrsb:SetPoint("RIGHT", hrb, "LEFT", -6, 0)
    hrsb:SetFrameLevel(topL + 2)
    hrsb:SetScript("OnClick", function(self)
        if M.ShowRouteSetMenu then M.ShowRouteSetMenu(self) end
    end)
    hrsb:Hide()

    local hwb = CreateFrame("Button", nil, f)
    hwb:SetSize(112, 28)
    hwb:RegisterForClicks("LeftButtonUp")
    hwb:EnableMouse(true)
    local HUI_RED = { 0.58, 0.13, 0.10, 1 }
    local HUI_RED_HOT = { 0.72, 0.18, 0.13, 1 }
    local C_TXT = { 1, 1, 1 }
    local C_TXT_HOT = { 1, 1, 1 }
    local hwbFill = {}
    if ns.hui and ns.hui.BuildRoundedBG then
        local raw = ns.hui.BuildRoundedBG(hwb, 6, HUI_RED, "both", false, nil, true)
        for i = 1, #(raw or {}) do hwbFill[#hwbFill + 1] = raw[i] end
        if ns.hui.BuildRoundBorder then
            ns.hui.BuildRoundBorder(hwb, 6, ns.hui.CTRL_BORDER or { 0x4A / 255, 0x52 / 255, 0x63 / 255, 1 },
                hwb, "OVERLAY", "both", 1)
        end
    else
        local fb = hwb:CreateTexture(nil, "BACKGROUND")
        fb:SetAllPoints()
        fb:SetColorTexture(HUI_RED[1], HUI_RED[2], HUI_RED[3], 1)
        hwbFill[#hwbFill + 1] = fb
    end
    local hwfs = hwb:CreateFontString()
    hwfs:SetAllPoints()
    hwfs:SetFont(ns.FONT, 14, "")
    hwfs:SetText(L["返回原生地图"])
    hwfs:SetJustifyH("CENTER")
    hwfs:SetTextColor(C_TXT[1], C_TXT[2], C_TXT[3])
    hwb:SetFontString(hwfs)
    local function paintRed(c)
        for _, t in ipairs(hwbFill) do
            if t.__huiGlass then t.__huiGlass.c = c end
            if ns.hui and ns.hui.GlassPaint then pcall(ns.hui.GlassPaint, t) end
        end
    end
    hwb:SetFrameLevel(topL + 2)
    hwb:SetScript("OnClick", function() backToNative() end)
    hwb:SetScript("OnEnter", function()
        paintRed(HUI_RED_HOT)
        hwfs:SetTextColor(C_TXT_HOT[1], C_TXT_HOT[2], C_TXT_HOT[3])
    end)
    hwb:SetScript("OnLeave", function()
        paintRed(HUI_RED)
        hwfs:SetTextColor(C_TXT[1], C_TXT[2], C_TXT[3])
    end)
    hwb:Hide()

    win.nat = {
        close = cb, world = wb, mini = mb, set = sb, pin = pb, route = rb,
        routeSet = rsb, tabs = fb, title = nil,
    }
    win.huiSet = {
        shell = huiShell, close = hcb, world = hwb, mini = hmb, set = hsb,
        pin = hpb, route = hrb, routeSet = hrsb, tabs = hfb, title = htb, titleFS = htfs,
    }

    local v = CreateFrame("Frame", nil, f)
    v.__mapWin = true
    v:SetSize(EDGE * 2 + GAP + SIDE_W + MAP_W, MAP_H)
    v:SetPoint("TOPLEFT", f, "TOPLEFT", 0, -(TOP_H + TOOL_H))
    view = v
    win.view = v
    hwb:ClearAllPoints()
    hwb:SetPoint("TOPLEFT", v, "TOPLEFT", 12, -6)
    v.routeBtn = rb
    v.pinBtn = pb
    v.routeSetBtn = rsb

    local stage = CreateFrame("Frame", nil, v)
    stage:SetClipsChildren(true)
    stage:Show()
    v.stage = stage

    local sideBg = CreateFrame("Frame", nil, v)
    sideBg:SetSize(SIDE_W, MAP_H)
    local sideRim = sideBg:CreateTexture(nil, "BACKGROUND", nil, 0)
    sideRim:SetColorTexture(0, 0, 0, 0.6)
    sideRim:SetPoint("TOPLEFT", sideBg, "TOPLEFT", -1, 1)
    sideRim:SetPoint("BOTTOMRIGHT", sideBg, "BOTTOMRIGHT", 1, -1)
    local sidePaper = sideBg:CreateTexture(nil, "BACKGROUND", nil, 1)
    sidePaper:SetAtlas("QuestLog-empty-quest-background")
    sidePaper:SetAllPoints(sideBg)
    local sideGrad = sideBg:CreateTexture(nil, "BACKGROUND", nil, 2)
    sideGrad:SetAtlas("QuestLog-Frame-Gradient-bottom")
    sideGrad:SetPoint("BOTTOMLEFT", sideBg, "BOTTOMLEFT", 4, 4)
    sideGrad:SetPoint("BOTTOMRIGHT", sideBg, "BOTTOMRIGHT", -4, 4)
    sideGrad:SetHeight(46)
    sideBg:Hide()
    win.sideBg = sideBg

    local mapBg = CreateFrame("Frame", nil, v)
    local mapRim = mapBg:CreateTexture(nil, "BACKGROUND", nil, 0)
    mapRim:SetColorTexture(0, 0, 0, 0.6)
    mapRim:SetAllPoints(mapBg)
    mapBg:Hide()
    win.mapBg = mapBg

    stage:SetFrameLevel(v:GetFrameLevel() + 1)
    mapBg:SetFrameLevel(v:GetFrameLevel())
    sideBg:SetFrameLevel(v:GetFrameLevel())

    local content = buildMapContent(stage)
    for kk, vv in pairs(content) do v[kk] = vv end

    local side = M.BuildSide(v, SIDE_W, MAP_H, true, nil, true, true)
    side:SetFrameLevel(v:GetFrameLevel() + 4)
    v.side = side

    stage:EnableMouse(true)
    stage:SetScript("OnMouseDown", function(self, btn)
        if btn == "RightButton" then
            backToNative()
            return
        end
        if btn ~= "LeftButton" then return end
        local ZM = ns.MapZoom
        if not ZM then return end
        local cw, ch = view.cw or MAP_W, view.ch or MAP_H
        local mx, my = ZM.Limits(cw, ch)
        if (mx or 0) <= 0 and (my or 0) <= 0 then return end
        self.__lx, self.__ly = cursorScaled()
        self:SetScript("OnUpdate", dragUpdate)
    end)
    stage:SetScript("OnMouseUp", function(self)
        self.__lx, self.__ly = nil, nil
        self:SetScript("OnUpdate", nil)
    end)
    stage:SetScript("OnHide", function(self)
        self.__lx, self.__ly = nil, nil
        self:SetScript("OnUpdate", nil)
    end)

    stage:EnableMouseWheel(true)
    stage:SetScript("OnMouseWheel", function(_, d)
        local ZM = ns.MapZoom
        if not ZM then return end
        local nk = (ZM.k or 1) * ((d > 0) and 1.15 or (1 / 1.15))
        if nk < 1 then nk = 1 end
        if nk > (ZM.max or 3) then nk = (ZM.max or 3) end
        ZM.k = nk
        local cw, ch = view.cw or MAP_W, view.ch or MAP_H
        local lx, ly = ZM.Limits(cw, ch)
        ZM.ClampTo(lx, ly)
        MW.Sync()
    end)

    v:SetScript("OnUpdate", function(self, dt)
        self.__t = (self.__t or 0) + dt
        if self.__t < 0.3 then return end
        self.__t = 0
        MW.Sync()
    end)

    applyScale(sv0 or 1.0)

    if WorldMapFrame and WorldMapFrame.HookScript and not MW.__wmHideHook then
        MW.__wmHideHook = true
        pcall(WorldMapFrame.HookScript, WorldMapFrame, "OnHide", function() miniStrata("MEDIUM") end)
    end

    tinsert(UISpecialFrames, "DungeonsForeverMapWindow")
    if f.HookScript then
        pcall(f.HookScript, f, "OnShow", function()
            if applySkin then applySkin(SKIN) end
        end)
    end
    if applySkin then applySkin(skinFromStore()) end
    return view
end

applySkin = function(mode)
    SKIN = (mode == "hui") and "hui" or "native"
    local f = win
    if not f then return end
    local isHui = SKIN == "hui"
    local nat = win.nat or {}
    local hs = win.huiSet or {}

    for _, o in ipairs({ nat.mini, nat.set, nat.close, nat.world }) do
        if o and o.SetShown then o:SetShown(not isHui) end
    end
    for _, o in ipairs({ nat.pin, nat.route, nat.routeSet }) do
        if o and o.SetShown then o:SetShown(false) end
    end
    for i = 1, #(nat.tabs or {}) do nat.tabs[i]:Hide() end
    if win.pill then win.pill:SetShown(not isHui) end

    for _, o in ipairs({ hs.shell, hs.close, hs.world, hs.mini, hs.set, hs.title }) do
        if o and o.SetShown then o:SetShown(isHui) end
    end
    if not isHui then
        for _, o in ipairs({ hs.pin, hs.route, hs.routeSet }) do
            if o then o:Hide() end
        end
        for i = 1, #(hs.tabs or {}) do hs.tabs[i]:Hide() end
    end

    if NineSliceUtil and NineSliceUtil.SetLayoutShown then
        pcall(NineSliceUtil.SetLayoutShown, f, not isHui)
    end
    if f.NineSlice then f.NineSlice:SetShown(not isHui) end
    for _, reg in ipairs({ f:GetRegions() }) do
        if reg.SetShown then reg:SetShown(not isHui) end
    end
    if f.TitleContainer then f.TitleContainer:SetShown(not isHui) end
    if f.PortraitContainer then f.PortraitContainer:SetAlpha(isHui and 0 or 1) end
    if win.logoBg then win.logoBg:SetShown(not isHui) end
    if win.logo then win.logo:SetShown(not isHui) end

    win.titleFS = isHui and hs.titleFS or (f.TitleContainer and f.TitleContainer.TitleText)
    win.closeBtn = isHui and hs.close or nat.close
    win.miniBtn = isHui and hs.mini or nat.mini
    win.setBtn = isHui and hs.set or nat.set
    win.routeBtn = isHui and hs.route or nat.route
    win.routeSetBtn = isHui and hs.routeSet or nat.routeSet
    win.floorBtns = isHui and hs.tabs or nat.tabs
    if view then
        view.routeBtn = win.routeBtn
        view.pinBtn = isHui and hs.pin or nat.pin
        view.routeSetBtn = win.routeSetBtn
    end
    if layout then layout() end
    if MW.Sync then MW.Sync() end
end

function MW.SetSkin(mode)
    local s = M.MapStore and M.MapStore()
    if s then
        if mode == "hui" then
            s.mapSkin = "hui"
        elseif mode == "auto" then
            s.mapSkin = nil
        else
            s.mapSkin = "native"
        end
    end
    local real = skinFromStore()
    if win and applySkin then
        applySkin(real)
    else
        SKIN = real
    end
end

function MW.SkinMode()
    local s = M.MapStore and M.MapStore()
    local v = s and s.mapSkin
    if v == "hui" then return "hui" end
    if v == "native" then return "native" end
    return "auto"
end

function MW.Skin()
    return SKIN
end

local function syncFloorRow(layers, idx)
    local btns = win.floorBtns
    if not btns then return end
    local n = layers and #layers or 0
    local prev
    for i = 1, M.MAX_LAYERS do
        local bt = btns[i]
        if i <= n then
            bt:SetText(R.floorText(MW.curId, i))
            if bt.__idx and bt.tabBtn then
                if PanelTemplates_TabResize then
                    pcall(PanelTemplates_TabResize, bt, 0)
                end
                bt:SetWidth(math.max(64, math.floor(bt:GetWidth() or 64)))
            else
                local fs = bt.GetFontString and bt:GetFontString()
                bt:SetWidth(math.max(56, math.floor((fs and fs:GetStringWidth() or 40) + 20)))
            end
            bt:ClearAllPoints()
            if prev then
                bt:SetPoint("TOPLEFT", prev, "TOPRIGHT", bt.tabBtn and 0 or 6, 0)
            elseif bt.tabBtn then
                bt:SetPoint("TOPLEFT", win, "TOPLEFT", EDGE + 38, -(TOP_H + 1))
            elseif win.huiSet and win.huiSet.title then
                bt:SetPoint("LEFT", win.huiSet.title, "RIGHT", 10, 0)
            end
            if bt.tabBtn then
                tabSelect(bt, i == idx)
            elseif ns.hui and ns.hui.SetButtonSelected then
                pcall(ns.hui.SetButtonSelected, bt, i == idx)
            end
            bt:Show()
            prev = bt
        else
            bt:Hide()
        end
    end
end

layout = function()
    if not view then return end
    local mw, mh = MAP_W * winK, MAP_H * winK
    local cw, ch, cx, cy = M.FitBox(mw, mh)
    view.cw, view.ch = cw, ch
    if cw > 0 then view.__uiK = cw / PIN_REF_W end
    if view.stage then
        view.stage:ClearAllPoints()
        view.stage:SetPoint("TOPLEFT", view, "TOPLEFT", EDGE + cx, -(cy))
        view.stage:SetSize(cw, ch)
        if win.mapBg then
            win.mapBg:ClearAllPoints()
            win.mapBg:SetPoint("TOPLEFT", view.stage, "TOPLEFT", -5, 5)
            win.mapBg:SetPoint("BOTTOMRIGHT", view.stage, "BOTTOMRIGHT", 5, -5)
            if SKIN == "hui" then win.mapBg:Hide() else win.mapBg:Show() end
        end
    end
    local ZM = ns.MapZoom
    local k = (ZM and ZM.k) or 1
    if ZM then
        local lx, ly = ZM.Limits(cw, ch)
        ZM.ClampTo(lx, ly)
    end
    local zx = (ZM and ZM.x) or 0
    local zy = (ZM and ZM.y) or 0
    local zw, zh = cw * k, ch * k
    view.zw, view.zh = zw, zh
    if view.canvas then
        view.canvas:ClearAllPoints()
        view.canvas:SetPoint("CENTER", view.stage, "CENTER", zx, zy)
        view.canvas:SetSize(zw, zh)
    end
    if view.route then
        view.route:ClearAllPoints()
        view.route:SetPoint("TOPLEFT", view.canvas, "TOPLEFT", 0, 0)
        view.route:SetSize(zw, zh)
    end
    if view.pins then
        view.pins:ClearAllPoints()
        view.pins:SetPoint("TOPLEFT", view.canvas, "TOPLEFT", 0, 0)
        view.pins:SetSize(zw, zh)
    end
    if view.side then
        view.side:ClearAllPoints()
        view.side:SetPoint("TOPLEFT", view, "TOPLEFT", EDGE + mw + GAP, 0)
        view.side:SetSize(SIDE_W, mh)
        view.sideAvail = SIDE_W
        view.sideL = EDGE + mw + GAP
        view.sideT = 0
        if win.sideBg then
            win.sideBg:ClearAllPoints()
            win.sideBg:SetPoint("TOPLEFT", view, "TOPLEFT", EDGE + mw + GAP, 0)
            win.sideBg:SetSize(SIDE_W, mh)
            if view.side:IsShown() and SKIN ~= "hui" then win.sideBg:Show() else win.sideBg:Hide() end
        end
    end
end

layoutMini = function()
    if not mview then return end
    local bw, bh = M.FitBox(MAP_W, MAP_H)
    local es = (mini and mini.GetEffectiveScale and mini:GetEffectiveScale()) or 1
    if es <= 0 then es = 1 end
    local trimR = MINI_TRIM_R / es
    local trimB = MINI_TRIM_B / es
    local aw, ah = MINI_W - MINI_EDGE * 2 - trimR, MINI_H - MINI_EDGE * 2 - trimB
    local k = math.min(aw / bw, ah / bh)
    mview.__uiK = 1 / k
    mview.cw, mview.ch = bw, bh
    if mview.stage then
        mview.stage:SetScale(k)
        mview.stage:ClearAllPoints()
        mview.stage:SetPoint("TOPLEFT", mview, "TOPLEFT", MINI_EDGE, -(MINI_EDGE))
        mview.stage:SetSize(bw, bh)
    end
    local w = bw * k + MINI_EDGE + (MINI_EDGE - trimR)
    local h = bh * k + MINI_EDGE + (MINI_EDGE - trimB)
    if mini then mini:SetSize(w, h) end
    if miniShell and mini then
        miniShell:SetSize(w * mini:GetScale(), h * mini:GetScale())
        mini:ClearAllPoints()
        mini:SetPoint("TOPLEFT", miniShell, "TOPLEFT", 0, 0)
    end
    if mini.wingBar then
        local tgt = ns.MainFrame and ns.MainFrame.GetEffectiveScale and ns.MainFrame:GetEffectiveScale()
        tgt = tgt or (UIParent and UIParent.GetEffectiveScale and UIParent:GetEffectiveScale()) or 1
        local me = mini:GetEffectiveScale() or 1
        if me > 0 then
            mini.wingBar:SetScale(tgt / me)
            if mini.floorBar then mini.floorBar:SetScale(tgt / me) end
        end
    end
    mview:SetSize(w, h)
    local ZM = ns.MapZoom
    local k2 = (ZM and ZM.k) or 1
    if ZM then
        local lx, ly = ZM.Limits(bw, bh)
        ZM.ClampTo(lx, ly)
    end
    local zx = (ZM and ZM.x) or 0
    local zy = (ZM and ZM.y) or 0
    local zw, zh = bw * k2, bh * k2
    mview.zw, mview.zh = zw, zh
    if mview.canvas then
        mview.canvas:ClearAllPoints()
        mview.canvas:SetPoint("CENTER", mview.stage, "CENTER", zx, zy)
        mview.canvas:SetSize(zw, zh)
    end
    if mview.route then
        mview.route:ClearAllPoints()
        mview.route:SetPoint("TOPLEFT", mview.canvas, "TOPLEFT", 0, 0)
        mview.route:SetSize(zw, zh)
    end
    if mview.pins then
        mview.pins:ClearAllPoints()
        mview.pins:SetPoint("TOPLEFT", mview.canvas, "TOPLEFT", 0, 0)
        mview.pins:SetSize(zw, zh)
    end
    if mini.skipBtn then
        local need = (mini.skipBtn:GetWidth() or 88) + 56
        mini.skipBtn:SetShown(w >= need)
    end
end

local function miniDragUpdate(self)
    if type(IsMouseButtonDown) == "function" and not IsMouseButtonDown("LeftButton") then
        self.__lx, self.__ly = nil, nil
        self:SetScript("OnUpdate", nil)
        MW.MiniSync(true)
        return
    end
    local ZM = ns.MapZoom
    if not (ZM and mview) then return end
    local x, y = cursorScaled()
    local lx, ly = self.__lx or x, self.__ly or y
    self.__lx, self.__ly = x, y
    local dx, dy = x - lx, y - ly
    if dx == 0 and dy == 0 then return end
    local us = UIParent and UIParent:GetEffectiveScale() or 1
    local ms = mini and mini.GetEffectiveScale and mini:GetEffectiveScale() or 1
    if ms and ms > 0 and us and us > 0 then
        local k2 = us / ms
        dx, dy = dx * k2, dy * k2
    end
    local cw, ch = mview.cw or MAP_W, mview.ch or MAP_H
    local mx, my = ZM.Limits(cw, ch)
    ZM.x, ZM.y = ZM.x + dx, ZM.y + dy
    ZM.ClampTo(mx, my)
    layoutMini()
end

local function wingZoneName()
    if type(GetInstanceInfo) ~= "function" then return nil end
    local ok, nm = pcall(GetInstanceInfo)
    if ok and type(nm) == "string" and nm ~= "" then return nm end
    return nil
end

local function wingShort(d, zn)
    local short = d.name or d.id
    if zn and short:sub(1, #zn) == zn then short = short:sub(#zn + 1) end
    short = short:gsub("^[：:%s]+", "")
    if short == "" then short = d.name or d.id end
    return short
end

local function syncWingBar()
    local bar = mini and mini.wingBar
    if not bar then return end
    local group
    local zn = wingZoneName()
    if zn and MW.curId then
        local zk = zn:gsub("[%s%p]", ""):lower()
        if zk ~= "" then
            local list = ns.DungeonData and ns.DungeonData.dungeons
            if type(list) == "table" then
                group = {}
                for i = 1, #list do
                    local d = list[i]
                    local has = (M.LayersFor and M.LayersFor(d.id)) or (M.CustomFor and M.CustomFor(d.id))
                    if has and d.name then
                        local k1 = d.name:gsub("[%s%p]", ""):lower()
                        if #k1 >= #zk and k1:sub(1, #zk) == zk then
                            group[#group + 1] = d
                        end
                    end
                end
                if #group < 2 then group = nil end
            end
        end
    end
    if not group or not mini:IsShown() then
        bar:Hide()
        return
    end
    local btns = mini.wingBtns
    local prev
    for i = 1, #group do
        local d = group[i]
        local bt = btns[i]
        if not bt then
            bt = newBtn(bar, "", 60, 20)
            bt:SetScript("OnClick", function(self)
                local wid = self.__wingId
                if not (wid and MW.curId and wid ~= MW.curId) then return end
                local Wm = ns.MapWorldModule
                MW.curId = wid
                M.curId = wid
                MW.curLayer = 1
                if Wm then
                    Wm.curId = wid
                    local d0 = R and R.detailOf and R.detailOf(wid)
                    if d0 then Wm.curD = d0 end
                end
                local d0 = R and R.detailOf and R.detailOf(wid)
                if d0 then M.curD = d0 end
                M.SideHost = nil
                M.detailEn = nil
                if ns.MapZoom then ns.MapZoom.Reset() end
                MW.MiniSync(true)
                syncWingBar()
            end)
            btns[i] = bt
        end
        bt.__wingId = d.id
        bt:SetText(wingShort(d, zn))
        bt:SetWidth(math.max(44, math.floor((bt:GetFontString():GetStringWidth() or 20) + 14)))
        bt:ClearAllPoints()
        if prev then
            bt:SetPoint("LEFT", prev, "RIGHT", 4, 0)
        else
            bt:SetPoint("LEFT", bar, "LEFT", 0, 0)
        end
        if ns.hui and ns.hui.SetButtonSelected then
            pcall(ns.hui.SetButtonSelected, bt, d.id == MW.curId)
        end
        bt:Show()
        prev = bt
    end
    for i = #group + 1, #btns do
        btns[i]:Hide()
    end
    local w = 0
    for i = 1, #group do
        w = w + (btns[i]:GetWidth() or 0) + ((i > 1) and 4 or 0)
    end
    bar:SetWidth(w)
    bar:Show()
end

local function syncMiniFloorBar()
    local bar = mini and mini.floorBar
    if not bar then return end
    local layers = (mini:IsShown() and MW.curId) and M.LayersFor(MW.curId) or nil
    if not (layers and #layers > 1) then
        bar.__has = false
        bar:Hide()
        return
    end
    local btns = mini.floorBtns
    local maxW = MINI_W
    local rowH, rowGap = 20, 4
    local rows = { { w = 0, n = 0 } }
    for i = 1, math.min(#layers, M.MAX_LAYERS) do
        local bt = btns[i]
        if not bt then
            bt = newBtn(bar, "", 60, rowH)
            bt:SetScript("OnClick", function(self)
                local i2 = self.__idx
                if not (i2 and MW.curId and mini:IsShown()) then return end
                local ls = M.LayersFor(MW.curId)
                if not (ls and ls[i2]) then return end
                if i2 == (MW.curLayer or 1) then return end
                if ns.MapZoom then ns.MapZoom.Reset() end
                MW.subFollow = false
                MW.curLayer = i2
                MW.MiniSync(true)
                syncMiniFloorBar()
            end)
            btns[i] = bt
        end
        bt.__idx = i
        bt:SetText(R.floorText(MW.curId, i))
        local fs = bt:GetFontString()
        bt:SetWidth(math.max(44, math.floor((fs and fs:GetStringWidth() or 40) + 14)))
        local row = rows[#rows]
        local need = bt:GetWidth() or 44
        if row.w > 0 and (row.n >= 3 or row.w + 4 + need > maxW) then
            row = { w = 0, n = 0 }
            rows[#rows + 1] = row
        end
        row[#row + 1] = bt
        row.n = (row.n or 0) + 1
        row.w = row.w + need + ((row.w > 0) and 4 or 0)
    end
    for i = math.min(#layers, M.MAX_LAYERS) + 1, #btns do
        btns[i]:Hide()
    end
    bar.__rows = rows
    local dx = bar.__dx or 0
    local nRows = #rows
    bar:SetWidth(maxW)
    bar:SetHeight(nRows * rowH + math.max(0, nRows - 1) * rowGap)
    bar.__has = true
    for r = 1, #rows do
        local row = rows[r]
        local x = 0
        local y = (r - 1) * (rowH + rowGap)
        for _, bt in ipairs(row) do
            bt:ClearAllPoints()
            bt:SetPoint("TOPLEFT", bar, "TOPLEFT", x + dx, -y)
            bt.__bx, bt.__y = x + dx, -y
            if ns.hui and ns.hui.SetButtonSelected then
                pcall(ns.hui.SetButtonSelected, bt, bt.__idx == (MW.curLayer or 1))
            end
            bt:Show()
            x = x + (bt:GetWidth() or 0) + 4
        end
    end
    miniFloorVis()
end

local function ensureMini()
    if mini then return mview end
    if not R then R = ns.MapWorldModule and ns.MapWorldModule.Render end
    if not R then return nil end
    local mf = CreateFrame("Frame", "DungeonsForeverMapMini", UIParent, "BackdropTemplate")
    local shell = CreateFrame("Frame", "DungeonsForeverMapMiniShell", UIParent)
    shell:SetSize(MINI_W, MINI_H)
    shell:SetPoint("CENTER")
    shell:SetFrameStrata("MEDIUM")
    shell:SetFrameLevel(0)
    shell:SetMovable(true)
    shell:SetClampedToScreen(true)
    shell:Hide()
    miniShell = shell

    mf:SetParent(shell)
    mf:SetPoint("TOPLEFT", shell, "TOPLEFT", 0, 0)
    mf:SetFrameStrata("MEDIUM")
    mf:SetFrameLevel(0)
    mf:SetScale(1)
    mf:SetMovable(false)
    mf:SetClampedToScreen(false)
    mf:Hide()
    if ns.hui and ns.hui.SkinPopup and ns.hui.layer then
        ns.hui.SkinPopup(mf, 8, "both", ns.hui.layer.L0)
    end
    mini = mf
    if mini.HookScript then
        pcall(mini.HookScript, mini, "OnHide", function() miniStrata("MEDIUM") end)
    end

    local mv = CreateFrame("Frame", nil, mf)
    mv:SetSize(MINI_W, MINI_H)
    mv:SetPoint("TOPLEFT", mf, "TOPLEFT", 0, 0)
    mview = mv
    mini.view = mv

    local stage = CreateFrame("Frame", nil, mv)
    stage:SetClipsChildren(true)
    stage:Show()
    mview.stage = stage

    local content = buildMapContent(stage)
    for kk, vv in pairs(content) do mview[kk] = vv end
    R.miniView = mview

    function MW.IsMiniView(v)
        return mview ~= nil and v == mview
    end

    local downX, downY
    local panMode
    mf:EnableMouse(true)
    mf:EnableMouseWheel(true)
    local pillHideT
    mf:SetScript("OnEnter", function()
        applyMiniAlpha(true)
        miniFloorShow()
        local p = mini and mini.pill
        if not p then return end
        if pillHideT then pillHideT:Cancel() pillHideT = nil end
        p:Show()
    end)
    mf:SetScript("OnLeave", function()
        applyMiniAlpha(false)
        local p = mini and mini.pill
        if not p then return end
        if pillHideT then pillHideT:Cancel() end
        pillHideT = C_Timer.NewTimer(5, function()
            pillHideT = nil
            if p.__hover then return end
            if mini and mini:IsShown() and p:IsShown() and p:IsMouseOver() then return end
            p:Hide()
        end)
    end)
    mf:SetScript("OnMouseDown", function(_, btn)
        if btn ~= "LeftButton" then return end
        downX, downY = cursorScaled()
        local ZM = ns.MapZoom
        local mx, my = 0, 0
        if ZM and mview then
            mx, my = ZM.Limits(mview.cw or MAP_W, mview.ch or MAP_H)
        end
        if (mx or 0) > 0 or (my or 0) > 0 then
            panMode = true
            mf.__lx, mf.__ly = downX, downY
            mf:SetScript("OnUpdate", miniDragUpdate)
        else
            panMode = nil
            miniShell:StartMoving()
        end
    end)
    mf:SetScript("OnMouseUp", function(_, btn)
        mf:SetScript("OnUpdate", nil)
        mf.__lx, mf.__ly = nil, nil
        if panMode then
            panMode = nil
        else
            miniShell:StopMovingOrSizing()
            local s = M.MapStore and M.MapStore()
            if s then
                local l, t = miniShell:GetLeft(), miniShell:GetTop()
                if l and t then
                    s.miniPos = { math.floor(l + 0.5), math.floor(t + 0.5) }
                end
            end
        end
        if btn == "RightButton" then
            MW.miniClosed = true
            mf:Hide()
            return
        end
        if btn ~= "LeftButton" or not downX then return end
        local x, y = cursorScaled()
        local moved = math.abs(x - downX) + math.abs(y - downY)
        downX, downY = nil, nil
        if moved < 5 then MW.Restore() end
    end)
    mf:SetScript("OnMouseWheel", function(_, d)
        local ZM = ns.MapZoom
        if not (ZM and mview) then return end
        local bw, bh = mview.cw or MAP_W, mview.ch or MAP_H
        local nk = (ZM.k or 1) * ((d > 0) and 1.15 or (1 / 1.15))
        if nk < 1 then nk = 1 end
        if nk > (ZM.max or 3) then nk = (ZM.max or 3) end
        ZM.k = nk
        local lx, ly = ZM.Limits(bw, bh)
        ZM.ClampTo(lx, ly)
        MW.MiniSync(true)
    end)
    mf:SetScript("OnHide", function(self)
        self:SetScript("OnUpdate", nil)
        self.__lx, self.__ly = nil, nil
        panMode = nil
        GameTooltip:Hide()
        floorWant = false
        fadeStop()
        if mini.floorBar then mini.floorBar:Hide() end
        if miniShell then miniShell:Hide() end
    end)
    mf:SetScript("OnShow", function()
        floorWant = false
        if mini.floorBar then mini.floorBar:Hide() end
        if miniShell then miniShell:Show() end
    end)

    local xbtn = CreateFrame("Button", nil, mf, "BackdropTemplate")
    xbtn:SetSize(36, 36)
    xbtn:SetPoint("TOPRIGHT", mf, "TOPRIGHT", -4, -4)
    xbtn:SetFrameLevel(mf:GetFrameLevel() + 12)
    if ns.hui and ns.hui.SkinButton then pcall(ns.hui.SkinButton, xbtn) end
    local xbg = xbtn:CreateTexture(nil, "BORDER")
    xbg:SetTexture("Interface\\Buttons\\WHITE8X8")
    xbg:SetVertexColor(0.62, 0.16, 0.16, 1)
    xbg:SetAllPoints(xbtn)
    if ns.hui and ns.hui.RoundIcon then pcall(ns.hui.RoundIcon, xbg) end
    local xt = xbtn:CreateTexture(nil, "ARTWORK")
    xt:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\textures\\YY_close")
    xt:SetSize(21, 21)
    xt:SetPoint("CENTER", xbtn, "CENTER", 0, 0.3)
    xt:SetVertexColor(1, 1, 1)
    xbtn:SetScript("OnEnter", function()
        xt:SetVertexColor(1, 1, 1)
        xbg:SetVertexColor(0.78, 0.18, 0.18, 1)
    end)
    xbtn:SetScript("OnLeave", function()
        xt:SetVertexColor(1, 1, 1)
        xbg:SetVertexColor(0.62, 0.16, 0.16, 1)
    end)
    xbtn:SetScript("OnClick", function()
        MW.miniClosed = true
        mf:Hide()
    end)
    mini.xbtn = xbtn

    local sbtn = CreateFrame("Button", nil, mf, "BackdropTemplate")
    sbtn:SetSize(88, 24)
    sbtn:SetPoint("RIGHT", xbtn, "LEFT", -6, 0)
    sbtn:SetFrameLevel(mf:GetFrameLevel() + 12)
    if ns.hui and ns.hui.SkinButton then pcall(ns.hui.SkinButton, sbtn) end
    local sfs = sbtn:CreateFontString(nil, "OVERLAY")
    sfs:SetFont(ns.FONT, 14, "")
    sfs:SetPoint("CENTER", sbtn, "CENTER", 0, 0)
    sfs:SetJustifyH("CENTER")
    sfs:SetText(L["本次不提醒"])
    sbtn:SetFontString(sfs)
    local sw = sfs:GetStringWidth() + 18
    if sw < 72 then sw = 72 end
    sbtn:SetWidth(sw)
    sbtn:SetScript("OnClick", function()
        MW.miniSkip = true
        MW.miniClosed = true
        if mini then mini:Hide() end
    end)
    mini.skipBtn = sbtn

    mv:SetScript("OnUpdate", function(self, dt)
        self.__t = (self.__t or 0) + dt
        if self.__t < 0.5 then return end
        self.__t = 0
        MW.MiniSync()
    end)
    mini.pill = buildMiniScalePill(mf)
    local wingBar = CreateFrame("Frame", nil, mf)
    wingBar:SetHeight(22)
    wingBar:SetPoint("BOTTOM", mf, "TOP", 0, 6)
    wingBar:Hide()
    mini.wingBar = wingBar
    mini.wingBtns = {}
    local floorBar = CreateFrame("Frame", nil, mf)
    floorBar:SetHeight(22)
    floorBar:SetPoint("TOPLEFT", mf, "BOTTOMLEFT", 0, -1)
    floorBar:EnableMouse(true)
    floorBar:SetScript("OnEnter", function()
        applyMiniAlpha(true)
    end)
    floorBar:SetScript("OnLeave", function()
        if not (mini and mini:IsMouseOver()) then applyMiniAlpha(false) end
        miniFadeSoon()
    end)
    floorBar:SetScript("OnUpdate", function(fb)
        local rows = fb.__rows
        local b = rows and rows[1] and rows[1][1]
        if not (b and mini and mini:IsShown() and mview) then return end
        local ml, bl = mview:GetLeft(), b:GetLeft()
        if not (ml and bl) then return end
        local d = ml - bl
        if math.abs(d) <= 0.5 then return end
        fb.__dx = (fb.__dx or 0) + d
        for r2 = 1, #rows do
            for _, bt in ipairs(rows[r2]) do
                bt.__bx = (bt.__bx or 0) + d
                bt:ClearAllPoints()
                bt:SetPoint("TOPLEFT", fb, "TOPLEFT", bt.__bx, bt.__y or 0)
            end
        end
    end)
    floorBar:Hide()
    mini.floorBar = floorBar
    mini.floorBtns = {}
    local s = M.MapStore and M.MapStore()
    local msv = s and tonumber(s.miniWinScale)
    applyMiniScale(msv or 1.0)
    return mview
end

function MW.MiniSync(force)
    local id = MW.curId
    if not (mini and mview and mini:IsShown() and id) then
        mview = mview or nil
        if mview then mview.__sig = nil end
        return
    end
    syncWingBar()
    syncMiniFloorBar()
    local Rl = R or (ns.MapWorldModule and ns.MapWorldModule.Render)
    if not Rl then return end
    if not Rl.hasArt(id) then
        mini:Hide()
        mview.__sig = nil
        return
    end
    layoutMini()
    local cw, ch = mview.zw or mview.cw or 0, mview.zh or mview.ch or 0
    if cw <= 0 or ch <= 0 then return end
    local idx = MW.curLayer or 1
    if not force then
        local dg = ns.DungeonUI
        local sig = tostring(id) .. "|" .. tostring(idx) .. "|" .. cw .. "|" .. ch
            .. "|" .. tostring(mview.zw) .. "|" .. tostring(mview.zh)
            .. "|" .. tostring(dg and dg.questRev)
        if mview.__sig == sig and (GetTime() - (mview.__sigT or 0)) < 10 then return end
        mview.__sig, mview.__sigT = sig, GetTime()
    else
        mview.__sig, mview.__sigT = nil, nil
    end
    local floor = Rl.floorNumAt(id, idx)
    Rl.paintArt(mview, id, idx, cw, ch)
    Rl.paintArea(mview, id, floor, cw, ch)
    Rl.syncRoute(mview, id, floor, cw, ch)
    Rl.syncPins(mview, id, floor, cw, ch)
end

local function MiniRestorePos()
    if not mini then return end
    local s = M.MapStore and M.MapStore()
    local pos = s and s.miniPos
    local host = miniShell or mini
    host:ClearAllPoints()
    if type(pos) == "table" and tonumber(pos[1]) and tonumber(pos[2]) then
        host:SetPoint("TOPLEFT", UIParent, "BOTTOMLEFT", pos[1], pos[2])
    else
        host:SetPoint("TOPLEFT", UIParent, "TOPLEFT", 20, -20)
    end
    host:Show()
    if miniShell and mini then
        local w, h = mini:GetSize()
        local ms = mini:GetScale() or 1
        miniShell:SetSize(w * ms, h * ms)
        mini:ClearAllPoints()
        mini:SetPoint("TOPLEFT", miniShell, "TOPLEFT", 0, 0)
    end
end

function MW.MiniOpen()
    if not (win and win:IsShown() and MW.curId) then return end
    if not ensureMini() then return end
    MW.miniClosed = nil
    M.SideHost = nil
    M.detailEn = nil
    win:Hide()
    MiniRestorePos()
    mini:Show()
    applyMiniAlpha()
    if ns.MapZoom then ns.MapZoom.Reset() end
    MW.MiniSync(true)
end

function MW.SubzoneLayerFor(id)
    local Wm = ns.MapWorldModule
    if not (Wm and Wm.SubzoneLayerFor) then return nil end
    local ok, idx = pcall(Wm.SubzoneLayerFor, id)
    if not (ok and idx) then return nil end
    local layers = M.LayersFor(id)
    if not (layers and layers[idx]) then return nil end
    return idx
end

function MW.ApplySubzone(id)
    if MW.subFollow == false then return false end
    local idx = MW.SubzoneLayerFor(id)
    if not idx or idx == (MW.curLayer or 1) then return false end
    MW.curLayer = idx
    return true
end

function MW.Retarget(id, layer)
    local Rl = R or (ns.MapWorldModule and ns.MapWorldModule.Render)
    if not (Rl and Rl.hasArt(id)) then return end
    local Wm = ns.MapWorldModule
    if Wm then
        Wm.curId = id
        local d0 = Rl.detailOf(id)
        if d0 then Wm.curD = d0 end
    end
    if MW.curId ~= id then MW.subFollow = true end
    MW.curId = id
    M.curId = id
    local d = Rl.detailOf(id)
    if d then M.curD = d end
    MW.curLayer = layer or M.EntryLayer(id) or 1
    M.SideHost = nil
    M.detailEn = nil
    if ns.MapZoom then ns.MapZoom.Reset() end
    if win and win:IsShown() then
        applyScale(MW.winScale or 1)
        MW.Sync()
    elseif mini and mini:IsShown() then
        MW.MiniSync(true)
    else
        MW.MiniAuto(id)
    end
end

function MW.MiniAuto(id, layer)
    if MW.miniSkip then return end
    if MW.miniClosed then return end
    local sa = M.MapStore and M.MapStore()
    if sa and sa.autoMini == false then return end
    if not (id and IsInInstance()) then return end
    if type(InCombatLockdown) == "function" and InCombatLockdown() then return end
    if win and win:IsShown() then return end
    local Wm = ns.MapWorldModule
    if Wm and Wm.Active and Wm.Active() then return end
    if not ensureMini() then return end
    local Rl = R or (ns.MapWorldModule and ns.MapWorldModule.Render)
    if not (Rl and Rl.hasArt(id)) then return end
    if mini:IsShown() then return end
    if MW.curId ~= id then MW.subFollow = true end
    MW.curId = id
    if Wm then
        Wm.curId = id
        local d0 = Rl.detailOf(id)
        if d0 then Wm.curD = d0 end
    end
    M.curId = id
    local d = Rl.detailOf(id)
    if d then M.curD = d end
    MW.curLayer = layer or M.EntryLayer(id) or 1
    if ns.MapZoom then ns.MapZoom.Reset() end
    applyScale(MW.winScale or 1)
    M.SideHost = nil
    M.detailEn = nil
    MiniRestorePos()
    mini:Show()
    applyMiniAlpha()
    if ns.MapZoom then ns.MapZoom.Reset() end
    MW.MiniSync(true)
end

function MW.MinioCardWanted()
    if mini and mini:IsShown() then return false end
    if win and win:IsShown() then return false end
    local Wm = ns.MapWorldModule
    if not (Wm and Wm.Resolve) then return false end
    local ok, id = pcall(Wm.Resolve)
    if not (ok and id) then return false end
    MW.curId = id
    return true
end

function MW.TodoCard()
    local id = MW.curId
    if not id then return nil end
    local Rl = R or (ns.MapWorldModule and ns.MapWorldModule.Render)
    if not Rl then return nil end
    local d = Rl.detailOf(id)
    local tex = "Interface\\AddOns\\DungeonsForever\\Media\\Brand\\DungeonsForever"
    return {
        title = L["副本地图"],
        kind = "mapcard",
        n = 1,
        list = {
            {
                name = L["打开副本地图"],
                sub = d and d.name or id,
                icon = tex,
                slug = id,
                jump = function()
                    MW.Open(id)
                    return true
                end,
            },
        },
    }
end

function MW.Restore()
    if not mini then return end
    mini:Hide()
    if MW.curId then MW.Open(MW.curId) end
end

function MW.Sync()
    local id = MW.curId
    if not (win and view and view:IsShown() and id) then return end
    local Rl = R or (ns.MapWorldModule and ns.MapWorldModule.Render)
    if not Rl then return end
    if not Rl.hasArt(id) then
        MW.Close()
        return
    end
    layout()
    local cw, ch = view.zw or 0, view.zh or 0
    if cw <= 0 or ch <= 0 then return end
    local layers = M.LayersFor(id)
    local idx = MW.curLayer or 1
    if layers then
        if idx < 1 or idx > #layers then idx = 1 end
        MW.curLayer = idx
    end
    local floor = Rl.floorNumAt(id, idx)
    Rl.paintArt(view, id, idx, cw, ch)
    Rl.paintArea(view, id, floor, cw, ch)
    Rl.syncRoute(view, id, floor, cw, ch)
    Rl.syncPins(view, id, floor, cw, ch)
    Rl.syncButtons(view, id)
    for _, b in ipairs({ view.routeBtn, view.pinBtn }) do
        local fs = b and b.GetFontString and b:GetFontString()
        if fs then
            b:SetWidth(math.max(64, math.floor(fs:GetStringWidth() + 18)))
        end
    end
    syncFloorRow(layers, idx)
    if win.titleFS then
        local d = Rl.detailOf(id)
        local txt = (d and d.name) or id
        win.titleFS:SetText(txt)
        if SKIN == "hui" and win.huiSet and win.huiSet.title then
            win.huiSet.title:SetWidth(math.max(40, math.floor(win.titleFS:GetStringWidth() + 10)))
        end
    end
    if view.side then
        M.SideHost = view
        M.SyncSide()
        if not view.side:IsShown() and not M.sideTask and (view.sideAvail or 0) >= 120 then
            view.side:Show()
        end
    end
end

function MW.Open(id, layer)
    local Rl = R or (ns.MapWorldModule and ns.MapWorldModule.Render)
    if not Rl then return end
    if not ensure() then return end
    if not (id and Rl.hasArt(id)) then return end
    if MW.SkinMode() == "auto" and applySkin then
        local pick = autoSkinPick()
        if pick ~= SKIN then applySkin(pick) end
    end
    if mini and mini:IsShown() then mini:Hide() end
    MW.miniClosed = nil
    if MW.curId ~= id then MW.subFollow = true end
    MW.curId = id
    local Wm = ns.MapWorldModule
    if Wm then
        Wm.curId = id
        local d0 = Rl.detailOf(id)
        if d0 then Wm.curD = d0 end
    end
    M.curId = id
    local d = Rl.detailOf(id)
    if d then M.curD = d end
    local e = M.EntryLayer(id)
    MW.curLayer = layer or e or 1
    if ns.MapZoom then ns.MapZoom.Reset() end
    applyScale(MW.winScale or 1)
    M.sideTask = nil
    M.detailEn = nil
    view.__detailEn = nil
    if view.side then view.side:Show() end
    win:Show()
    MW.Sync()
end

function MW.Toggle(id)
    if win and win:IsShown() then
        MW.Close()
        return
    end
    MW.Open(id)
end

function MW.Close()
    if mini and mini:IsShown() then mini:Hide() end
    if not win then return end
    win:Hide()
    M.SideHost = nil
end

function MW.Visible()
    if mini and mini:IsShown() then return true end
    return win and win:IsShown() and true or false
end

if type(hooksecurefunc) == "function" then
    local function hideNativeSoon()
        if type(InCombatLockdown) == "function" and InCombatLockdown() then return end
        if WorldMapFrame and WorldMapFrame:IsShown() then
            C_Timer.After(0, function()
                if WorldMapFrame and WorldMapFrame:IsShown() then
                    pcall(HideUIPanel, WorldMapFrame)
                    if WorldMapFrame and WorldMapFrame:IsShown() then
                        pcall(WorldMapFrame.Hide, WorldMapFrame)
                    end
                end
            end)
        end
    end
    hooksecurefunc("ToggleWorldMap", function()
        local s = M.MapStore and M.MapStore()
        if s and s.mKeyOpen == false then return end
        if type(IsInInstance) ~= "function" or not IsInInstance() then return end
        local inCombat = type(InCombatLockdown) == "function" and InCombatLockdown() or false
        local Wm = ns.MapWorldModule
        if mini and mini:IsShown() then
            if not inCombat then hideNativeSoon() end
            if MW.curId then
                MW.Open(MW.curId)
                if inCombat and win and win:IsShown() then win:Raise() end
            end
            return
        end
        if MW.Visible() then
            local toMini = (not s or s.closeToMini ~= false) and not MW.miniSkip and (MW.curId ~= nil)
            if not inCombat then hideNativeSoon() end
            if toMini then
                MW.MiniOpen()
            else
                MW.Close()
            end
            return
        end
        if not (Wm and Wm.Resolve) then return end
        local ok, id = pcall(Wm.Resolve)
        if not (ok and id) then
            local cok, cands = pcall(Wm.ResolveCandidates)
            if not (cok and type(cands) == "table" and #cands > 0) then return end
            if not inCombat then hideNativeSoon() end
            if #cands == 1 then
                MW.Open(cands[1].id)
                if inCombat and win and win:IsShown() then win:Raise() end
                return
            end
            if ns.hui and ns.hui.ShowMenu then
                local items = {}
                for i = 1, #cands do
                    items[#items + 1] = {
                        text = cands[i].name,
                        func = function()
                            MW.Open(cands[i].id)
                            if inCombat and win and win:IsShown() then win:Raise() end
                        end,
                    }
                end
                ns.hui.ShowMenu(items, { owner = WorldMapFrame or UIParent, anchor = WorldMapFrame or UIParent })
            end
            return
        end
        if not inCombat then hideNativeSoon() end
        MW.Open(id)
        if inCombat and win and win:IsShown() then win:Raise() end
    end)
end

SLASH_DFMAP1 = "/dfmap"

local zoneDriver = CreateFrame("Frame")
zoneDriver:RegisterEvent("ZONE_CHANGED_NEW_AREA")
zoneDriver:RegisterEvent("PLAYER_ENTERING_WORLD")
zoneDriver:RegisterEvent("ZONE_CHANGED")
zoneDriver:RegisterEvent("ZONE_CHANGED_INDOORS")
zoneDriver:SetScript("OnEvent", function(_, ev)
    local hard = ev == "ZONE_CHANGED_NEW_AREA" or ev == "PLAYER_ENTERING_WORLD"
    if hard then
        MW.miniClosed = nil
        MW.subFollow = true
        if mini and mini:IsShown() then mini:Hide() end
    end
    if not IsInInstance() then return end
    C_Timer.After(1.2, function()
        local Wm = ns.MapWorldModule
        if not (Wm and Wm.Resolve) then return end
        local ok, rid = pcall(Wm.Resolve)
        if ok and rid then
            if MW.curId ~= rid then
                MW.Retarget(rid, MW.SubzoneLayerFor(rid))
                return
            end
            if MW.ApplySubzone(rid) then
                if win and win:IsShown() then MW.Sync() end
                if mini and mini:IsShown() then MW.MiniSync(true) end
            end
            MW.MiniAuto(rid)
            return
        end
        local cok, cands = pcall(Wm.ResolveCandidates)
        if not (cok and type(cands) == "table" and #cands >= 1) then return end
        MW.MiniAuto(cands[1].id)
    end)
end)

local regenDriver = CreateFrame("Frame")
regenDriver:RegisterEvent("PLAYER_REGEN_ENABLED")
regenDriver:SetScript("OnEvent", function()
    if win and win:IsShown() then
        applyScale(MW.winScale or 1)
        MW.Sync()
    end
end)
SlashCmdList["DFMAP"] = function(msg)
    local arg = (msg or ""):gsub("%s+", "")
    if arg == "sub" then
        local Wm = ns.MapWorldModule
        local ok, rid = false, nil
        if Wm and Wm.Resolve then ok, rid = pcall(Wm.Resolve) end
        local zn, sub = nil, nil
        if type(GetRealZoneText) == "function" then
            local zok, zv = pcall(GetRealZoneText)
            if zok then zn = zv end
        end
        if type(GetSubZoneText) == "function" then
            local sok, sv = pcall(GetSubZoneText)
            if sok then sub = sv end
        end
        local hit = (ok and rid) and MW.SubzoneLayerFor(rid) or nil
        print("DFMAP sub: dungeon=" .. tostring(rid) .. " zone=" .. tostring(zn)
            .. " sub=" .. tostring(sub) .. " layer=" .. tostring(MW.curLayer or 1)
            .. " hit=" .. tostring(hit))
        return
    end
    local id = arg
    if id == "" then
        local W = ns.MapWorldModule
        if W and W.Resolve then
            local ok, rid = pcall(W.Resolve)
            id = ok and rid or nil
        end
        if not id and W and W.ResolveCandidates then
            local cok, cands = pcall(W.ResolveCandidates)
            if cok and type(cands) == "table" and #cands > 0 then
                id = cands[1].id
            end
        end
    end
    if not id then
        print(L["用法"] .. ": /dfmap <id> (wailing_caverns ...)")
        return
    end
    MW.Open(id)
end
