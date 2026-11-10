local ADDON, ns = ...

local MW = {}
ns.MapWindowModule = MW

local L = ns.L
local M = ns.MapModule

local EDGE = 12
local TOP_H = 40
local BOT_H = 12
local GAP = 8
local SIDE_W = 330
local MAP_W = 1284
local MAP_H = 856
local PILL_W, PILL_H = 96, 24
local MINI_W, MINI_H, MINI_EDGE = 520, 360, 10
local MINI_TRIM_R = 5
local MINI_TRIM_B = 5
local PIN_REF_W = 642
local SCALE_MIN, SCALE_MAX = 0.2, 1.5
local SCALE_BASE = 0.66
local MINI_SCALE_BASE = 0.76
local winK = 1
local GLYPH = 0xa0 / 255
local TEXT_C = { 0.95, 0.96, 0.98 }

local win, view, mini, mview
local R

local layout
local layoutMini
local miniShell

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
    local h = TOP_H + MAP_H * winK + BOT_H
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
    pill:SetSize(PILL_W, PILL_H)
    pill:SetPoint("RIGHT", win.routeSetBtn, "LEFT", -8, 0)
    pill:SetFrameLevel(f:GetFrameLevel() + 8)
    win.pill = pill
    if ns.hui and ns.hui.BuildRoundedBG and ns.hui.layer then
        ns.hui.BuildRoundedBG(pill, 12, ns.hui.layer.L2, "both", true, 1)
    else
        pill:SetBackdrop({
            bgFile = "Interface\\Buttons\\WHITE8X8",
            edgeFile = "Interface\\Buttons\\WHITE8X8",
            edgeSize = 1,
        })
        pill:SetBackdropColor(0x16 / 255, 0x1a / 255, 0x22 / 255, 1)
        pill:SetBackdropBorderColor(0x55 / 255, 0x58 / 255, 0x5e / 255, 1)
    end
    local lab = pill:CreateFontString(nil, "OVERLAY")
    lab:SetFont(ns.FONT, 13, "")
    lab:SetPoint("CENTER", pill, "CENTER", 0, 0)
    lab:SetTextColor(0.91, 0.93, 0.94)
    lab:SetText("100%")
    win.pillLabel = lab
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
            if self.__hov then
                for _, hv in ipairs(self.__hov) do hv:Show() end
            end
            t:SetTextColor(1, 1, 1)
        end)
        bt:SetScript("OnLeave", function(self)
            if self.__hov then
                for _, hv in ipairs(self.__hov) do hv:Hide() end
            end
            t:SetTextColor(Z_GLYPH[1], Z_GLYPH[2], Z_GLYPH[3])
        end)
        bt:SetScript("OnClick", function()
            local cur = MW.winScale or 1
            applyScale(cur * ((i == 1) and (1 / 1.15) or 1.15), true)
        end)
    end
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

local function backToNative()
    MW.Close()
    local WM = WorldMapFrame
    if not WM then return end
    if ShowUIPanel then
        pcall(ShowUIPanel, WM)
    else
        pcall(WM.Show, WM)
    end
end

local function ensure()
    if win then return view end
    R = ns.MapWorldModule and ns.MapWorldModule.Render
    if not R then return nil end
    if M.LoadMapState then pcall(M.LoadMapState) end

    local f = CreateFrame("Frame", "DungeonsForeverMapWindow", UIParent, "BackdropTemplate")
    f:SetSize(EDGE * 2 + GAP + SIDE_W + MAP_W, TOP_H + MAP_H + BOT_H)
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
    if ns.hui and ns.hui.SkinPopup and ns.hui.layer then
        ns.hui.SkinPopup(f, 10, "both", ns.hui.layer.L0)
    end
    win = f

    local strip = CreateFrame("Frame", nil, f)
    strip:SetSize(560, TOP_H)
    strip:SetPoint("TOPLEFT", f, "TOPLEFT", 0, 0)
    strip:EnableMouse(true)
    strip:SetScript("OnMouseDown", function() f:StartMoving() end)
    strip:SetScript("OnMouseUp", function() f:StopMovingOrSizing() end)

    local tb = CreateFrame("Button", "DungeonsForeverMapTitle", f, "BackdropTemplate")
    tb:SetSize(180, 26)
    tb:SetPoint("TOPLEFT", f, "TOPLEFT", EDGE, -7)
    if ns.hui and ns.hui.SkinButton then pcall(ns.hui.SkinButton, tb, { noFrame = true }) end
    local tfs = tb:CreateFontString(nil, "OVERLAY")
    tfs:SetFont(ns.FONT, 16, "")
    tfs:SetPoint("LEFT", tb, "LEFT", 0, 0)
    tfs:SetTextColor(TEXT_C[1], TEXT_C[2], TEXT_C[3])
    tb:SetFontString(tfs)
    tb:SetText("")
    tb:SetScript("OnClick", function() showDungeonMenu(tb) end)
    tb:SetScript("OnEnter", function(self) self:GetFontString():SetTextColor(1, 1, 1) end)
    tb:SetScript("OnLeave", function(self) self:GetFontString():SetTextColor(TEXT_C[1], TEXT_C[2], TEXT_C[3]) end)
    win.titleFS = tfs
    win.titleBtn = tb

    local fb = {}
    for i = 1, M.MAX_LAYERS do
        local bt = newBtn(f)
        bt.__idx = i
        bt:SetScript("OnClick", function(self)
            local i2 = self.__idx
            if not i2 then return end
            local layers = M.LayersFor(MW.curId)
            if not (layers and layers[i2]) then return end
            if i2 == (M.curLayer or 1) then return end
            if ns.MapZoom then ns.MapZoom.Reset() end
            M.curLayer = i2
            applyScale(MW.winScale or 1)
            MW.Sync()
        end)
        bt:Hide()
        fb[i] = bt
    end
    win.floorBtns = fb

    local cb = CreateFrame("Button", nil, f, "BackdropTemplate")
    cb:SetSize(36, 36)
    cb:SetPoint("CENTER", f, "TOPRIGHT", -20, -20)
    if ns.hui and ns.hui.SkinButton then pcall(ns.hui.SkinButton, cb, { noFrame = true }) end
    local ct = cb:CreateTexture(nil, "ARTWORK")
    ct:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\textures\\YY_close")
    ct:SetSize(32, 32)
    ct:SetPoint("CENTER", cb, "CENTER", 0, 0.4)
    ct:SetVertexColor(GLYPH, GLYPH, GLYPH)
    cb:SetScript("OnClick", function()
        local s = M.MapStore and M.MapStore()
        if (not s or s.closeToMini ~= false) and MW.curId and R.hasArt(MW.curId) then
            MW.MiniOpen()
            return
        end
        MW.Close()
    end)
    cb:SetScript("OnEnter", function() ct:SetVertexColor(1, 1, 1) end)
    cb:SetScript("OnLeave", function() ct:SetVertexColor(GLYPH, GLYPH, GLYPH) end)
    win.closeBtn = cb

    local mb = CreateFrame("Button", nil, f, "BackdropTemplate")
    mb:SetSize(31, 31)
    mb:SetPoint("RIGHT", cb, "LEFT", -6, 0)
    if ns.hui and ns.hui.SkinButton then pcall(ns.hui.SkinButton, mb, { noFrame = true }) end
    local mt = mb:CreateTexture(nil, "ARTWORK")
    mt:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\textures\\DF_mini")
    mt:SetSize(22, 22)
    mt:SetPoint("CENTER", mb, "CENTER", 0, 0.4)
    mt:SetVertexColor(GLYPH, GLYPH, GLYPH)
    mb:SetScript("OnClick", function() MW.MiniOpen() end)
    mb:SetScript("OnEnter", function() mt:SetVertexColor(1, 1, 1) end)
    mb:SetScript("OnLeave", function() mt:SetVertexColor(GLYPH, GLYPH, GLYPH) end)
    win.miniBtn = mb

    local sb = CreateFrame("Button", nil, f, "BackdropTemplate")
    sb:SetSize(36, 36)
    sb:SetPoint("RIGHT", mb, "LEFT", -6, 0)
    if ns.hui and ns.hui.SkinButton then pcall(ns.hui.SkinButton, sb, { noFrame = true }) end
    local st2 = sb:CreateTexture(nil, "ARTWORK")
    st2:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\textures\\DF_Settings")
    st2:SetSize(24, 24)
    st2:SetPoint("CENTER", sb, "CENTER", 0, 0.4)
    st2:SetVertexColor(GLYPH, GLYPH, GLYPH)
    sb:SetScript("OnClick", function(self) showSettingsMenu(self) end)
    sb:SetScript("OnEnter", function() st2:SetVertexColor(1, 1, 1) end)
    sb:SetScript("OnLeave", function() st2:SetVertexColor(GLYPH, GLYPH, GLYPH) end)
    win.setBtn = sb

    local pb = newBtn(f, L["图钉显示"])
    pb:SetPoint("RIGHT", sb, "LEFT", -6, 0)
    pb:SetScript("OnClick", function(self) M.ShowPinMenu(self) end)
    pb:Hide()

    local rb = newBtn(f, L["路线显示"])
    rb:SetPoint("RIGHT", pb, "LEFT", -6, 0)
    rb:SetScript("OnClick", function(self, button)
        R.routeToggle(self, button)
        MW.Sync()
    end)
    rb:Hide()
    win.routeBtn = rb

    local rsb = newBtn(f, L["路线设置"])
    rsb:SetPoint("RIGHT", rb, "LEFT", -6, 0)
    rsb:SetScript("OnClick", function(self)
        if M.ShowRouteSetMenu then M.ShowRouteSetMenu(self) end
    end)
    rsb:Hide()
    win.routeSetBtn = rsb

    local wb = newBtn(f, L["返回原生地图"], 118, 22)
    wb:SetPoint("TOPLEFT", f, "TOPLEFT", EDGE, -(TOP_H + 2))
    wb:SetScript("OnClick", function() backToNative() end)
    win.worldBtn = wb

    local baseL = f:GetFrameLevel()
    strip:SetFrameLevel(baseL + 1)
    tb:SetFrameLevel(baseL + 6)
    for i = 1, M.MAX_LAYERS do fb[i]:SetFrameLevel(baseL + 6) end
    cb:SetFrameLevel(baseL + 8)
    mb:SetFrameLevel(baseL + 8)
    sb:SetFrameLevel(baseL + 8)
    pb:SetFrameLevel(baseL + 8)
    rb:SetFrameLevel(baseL + 8)
    rsb:SetFrameLevel(baseL + 8)
    wb:SetFrameLevel(baseL + 8)

    local v = CreateFrame("Frame", nil, f)
    v:SetSize(EDGE * 2 + GAP + SIDE_W + MAP_W, MAP_H)
    v:SetPoint("TOPLEFT", f, "TOPLEFT", 0, -TOP_H)
    view = v
    win.view = v
    v.routeBtn = rb
    v.pinBtn = pb
    v.routeSetBtn = rsb

    local stage = CreateFrame("Frame", nil, v)
    stage:SetClipsChildren(true)
    stage:Show()
    v.stage = stage

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

    tinsert(UISpecialFrames, "DungeonsForeverMapWindow")
    return view
end

local function syncFloorRow(layers, idx)
    local btns = win.floorBtns
    if not btns then return end
    local n = layers and #layers or 0
    local prev = win.titleBtn
    for i = 1, M.MAX_LAYERS do
        local bt = btns[i]
        if i <= n then
            bt:SetText(R.floorText(MW.curId, i))
            local fs = bt:GetFontString()
            local w = math.max(52, math.floor((fs and fs:GetStringWidth() or 40) + 16))
            bt:SetSize(w, 24)
            bt:ClearAllPoints()
            bt:SetPoint("LEFT", prev, "RIGHT", 8, 0)
            if ns.hui and ns.hui.SetButtonSelected then
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
        local p = mini and mini.pill
        if not p then return end
        if pillHideT then pillHideT:Cancel() pillHideT = nil end
        p:Show()
    end)
    mf:SetScript("OnLeave", function()
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
        if miniShell then miniShell:Hide() end
    end)
    mf:SetScript("OnShow", function()
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

    mv:SetScript("OnUpdate", function(self, dt)
        self.__t = (self.__t or 0) + dt
        if self.__t < 0.5 then return end
        self.__t = 0
        MW.MiniSync()
    end)
    mini.pill = buildMiniScalePill(mf)
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
    local idx = M.curLayer or 1
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
    if ns.MapZoom then ns.MapZoom.Reset() end
    MW.MiniSync(true)
end

function MW.MiniAuto(id, layer)
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
    MW.curId = id
    if Wm then
        Wm.curId = id
        local d0 = Rl.detailOf(id)
        if d0 then Wm.curD = d0 end
    end
    M.curId = id
    local d = Rl.detailOf(id)
    if d then M.curD = d end
    M.curLayer = layer or M.EntryLayer(id) or 1
    if ns.MapZoom then ns.MapZoom.Reset() end
    applyScale(MW.winScale or 1)
    M.SideHost = nil
    M.detailEn = nil
    MiniRestorePos()
    mini:Show()
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
    local idx = M.curLayer or 1
    if layers then
        if idx < 1 or idx > #layers then idx = 1 end
        M.curLayer = idx
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
    if win.titleBtn then
        local d = Rl.detailOf(id)
        local txt = (d and d.name) or id
        win.titleBtn:SetText(txt)
        local fs = win.titleBtn:GetFontString()
        if fs then
            win.titleBtn:SetWidth(math.floor(fs:GetStringWidth() + 24))
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
    if mini and mini:IsShown() then mini:Hide() end
    MW.miniClosed = nil
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
    M.curLayer = layer or e or 1
    if ns.MapZoom then ns.MapZoom.Reset() end
    applyScale(MW.winScale or 1)
    M.sideTask = nil
    M.detailEn = nil
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
        if type(InCombatLockdown) == "function" and InCombatLockdown() then return end
        local Wm = ns.MapWorldModule
        if mini and mini:IsShown() then
            hideNativeSoon()
            if MW.curId then MW.Open(MW.curId) end
            return
        end
        if MW.Visible() then
            local toMini = (not s or s.closeToMini ~= false) and (MW.curId ~= nil)
            hideNativeSoon()
            if toMini then
                MW.MiniOpen()
            else
                MW.Close()
            end
            return
        end
        if not (Wm and Wm.Resolve) then return end
        local ok, id = pcall(Wm.Resolve)
        if not (ok and id) then return end
        hideNativeSoon()
        MW.Open(id)
    end)
end

SLASH_DFMAP1 = "/dfmap"

local zoneDriver = CreateFrame("Frame")
zoneDriver:RegisterEvent("ZONE_CHANGED_NEW_AREA")
zoneDriver:RegisterEvent("PLAYER_ENTERING_WORLD")
zoneDriver:SetScript("OnEvent", function()
    MW.miniClosed = nil
    if mini and mini:IsShown() then mini:Hide() end
    if not IsInInstance() then return end
    C_Timer.After(1.2, function()
        local Wm = ns.MapWorldModule
        if not (Wm and Wm.Resolve) then return end
        local ok, rid = pcall(Wm.Resolve)
        if ok and rid then MW.MiniAuto(rid) end
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
    local id = arg
    if id == "" then
        local W = ns.MapWorldModule
        if W and W.Resolve then
            local ok, rid = pcall(W.Resolve)
            id = ok and rid or nil
        end
    end
    if not id then
        print(L["用法"] .. ": /dfmap <id> (wailing_caverns ...)")
        return
    end
    MW.Open(id)
end
