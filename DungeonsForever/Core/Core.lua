local addonName, ns = ...

local ver = select(4, GetBuildInfo())
ns.version = ver
local function IsSupportedClient(v)
    if v >= 38000 and v < 40000 then return true end
    if v >= 16000 and v < 17000 then return true end
    if v >= 120000 and v < 130000 then return true end
    return false
end
ns.IsTitan = IsSupportedClient(ver)
ns.IsSupportedClient = IsSupportedClient
ns.IsForever = (ver >= 16000 and ver < 17000)
ns.IsRetail = (ver >= 120000 and ver < 130000)
ns.LoadForeverPages = ns.IsForever or ns.IsRetail
_G.DF_NS = ns

ns.huiTheme = "hui"

ns.CONTENT_TOP = 46

ns.SET_ICON = "Interface\\AddOns\\DungeonsForever\\Media\\textures\\DF_Settings"
ns.SET_ICON_IDLE = { 0.55, 0.62, 0.70 }
ns.SET_ICON_ON = { 1, 1, 1 }
ns.SET_ICON_ACT = { 1, 0.84, 0 }
ns.SORT_UP = "Interface\\AddOns\\DungeonsForever\\Media\\icon\\NAV\\SortUp"
ns.SORT_DN = "Interface\\AddOns\\DungeonsForever\\Media\\icon\\NAV\\SortDown"
ns.SORT_RATIO = 1.3
ns.SORT_DIM = { 0.34, 0.36, 0.40 }

function ns.SortArrowAccent()
    local a = ns.hui and ns.hui.ACCENT
    if a then return a[1], a[2], a[3] end
    return 0x46 / 255, 0xbf / 255, 0x72 / 255
end

ns.EvtPool = ns.EvtPool or {}

ns.MODULES = {
    { key = "Professions", addon = "DungeonsForeverProf",    sv = "DungeonsForeverProfDB",    legacy = { "prof", "profAudit" }, movedKey = "profMoved", label = "专业", probe = "ProfModule" },
    { key = "Gear",        addon = "DungeonsForeverGear",    sv = "DungeonsForeverGearDB",    legacy = { "gear", "bis", "wishlist" }, label = "装备库", tabs = { "Gear", "Bis" }, probe = "GearModule" },
    { key = "Tier",        addon = "DungeonsForeverClass",   sv = "DungeonsForeverClassDB",   legacy = { "tier", "talent", "talentSim" }, label = "职业指南", probe = "TierModule" },
    { key = "Explore",     addon = "DungeonsForeverExplore", sv = "DungeonsForeverExploreDB", legacy = { "explore" }, label = "探索", tabs = { "Explore", "Collections" }, probe = "ExploreModule" },
    { key = "Factions",    addon = "DungeonsForeverFaction", sv = "DungeonsForeverFactionDB", legacy = { "factions" }, label = "声望", probe = "FactionModule" },
    { key = "PvP",         addon = "DungeonsForeverPvP",     sv = nil, legacy = nil, label = "PvP", probe = "PvPModule" },
    { key = "Spell",       addon = "DungeonsForeverSpell",   sv = "DungeonsForeverSpellDB", legacy = nil, label = "技能书", probe = "NativeSpellBook" },
}

ns.MODULE_BY_TAB = {}
ns.MODULE_BY_ADDON = {}
for _, m in ipairs(ns.MODULES) do
    m.tabs = m.tabs or { m.key }
    for _, t in ipairs(m.tabs) do ns.MODULE_BY_TAB[t] = m end
    ns.MODULE_BY_ADDON[m.addon] = m
end

function ns.AddonLoaded(name)
    if type(C_AddOns) == "table" and C_AddOns.IsAddOnLoaded then
        return C_AddOns.IsAddOnLoaded(name) and true or false
    end
    if type(IsAddOnLoaded) == "function" then
        local ok, a = pcall(IsAddOnLoaded, name)
        if ok then return a == true or a == 1 end
    end
    return false
end

function ns.ModuleOn(tabKey)
    local m = ns.MODULE_BY_TAB[tabKey]
    if not m then return true end
    if m.probe and ns[m.probe] ~= nil then return true end
    return ns.AddonLoaded(m.addon)
end

function ns.ModuleDesc(tabKey)
    return ns.MODULE_BY_TAB[tabKey]
end

function ns.ModuleWant(m)
    if type(m) ~= "table" then return false end
    if m.key == "Spell" then
        local ui = ns.DB and ns.DB().ui
        return not (ui and ui.spellEnh == false)
    end
    local tabs = ns.QuickCfg().tabs
    for _, t in ipairs(m.tabs) do
        if tabs[t] ~= false then return true end
    end
    return false
end

local function DB()
    DungeonsForeverDB = DungeonsForeverDB or {}
    DungeonsForeverDB.ui = DungeonsForeverDB.ui or {}
    local db = DungeonsForeverDB
    if db.svVersion ~= 3 then
        db.openPerf = nil
        db.memProbe = nil
        db.memMarks = nil
        local prof = db.prof
        if type(prof) == "table" then
            prof.planSnap = nil
            prof.planPrev = nil
            local track = prof.track
            if type(track) == "table" then
                for _, c in pairs(track) do
                    if type(c) == "table" then
                        c.seen = nil
                        c.order = nil
                    end
                end
            end
        end
        db.svVersion = 3
    end
    for _, m in ipairs(ns.MODULES) do
        if m.sv and m.legacy then
            local mk = m.movedKey or (m.sv .. "Moved")
            if db[mk] and ns.ModuleDBKeys and ns.ModuleDBKeys(m.sv, m.legacy) then
                for i = 1, #m.legacy do db[m.legacy[i]] = nil end
            end
        end
    end
    return db
end
ns.DB = DB

ns.options = ns.options or {}
if ns.options.buttonSound == nil then ns.options.buttonSound = true end

ns.QUICK_VER = 1
ns.QUICK_GROUPS = { "dungeon", "prof", "explore" }
ns.QUICK_EXPLORE = { "books", "bag" }
ns.QUICK_TABS = { "Dungeons", "Raids", "Professions", "Explore", "Collections", "Factions", "Bis", "Tier", "PvP", "Gear" }

local QUICK_EXPLORE_SET = {}
for _, k in ipairs(ns.QUICK_EXPLORE) do QUICK_EXPLORE_SET[k] = true end

function ns.QuickCfg()
    local ui = DB().ui
    local q = ui.quick
    if type(q) ~= "table" or q.ver ~= ns.QUICK_VER then
        q = { ver = ns.QUICK_VER }
        ui.quick = q
    end
    if q.on == nil then q.on = true end
    if type(q.groups) ~= "table" then q.groups = {} end
    for _, k in ipairs(ns.QUICK_GROUPS) do
        if q.groups[k] == nil then q.groups[k] = true end
    end
    if q.profMode ~= "all" then q.profMode = "learned" end
    if type(q.expl) ~= "table" then q.expl = {} end
    for _, k in ipairs(ns.QUICK_EXPLORE) do
        if q.expl[k] == nil then q.expl[k] = true end
    end
    for k in pairs(q.expl) do
        if not QUICK_EXPLORE_SET[k] then q.expl[k] = nil end
    end
    if type(q.tabs) ~= "table" then q.tabs = {} end
    for _, k in ipairs(ns.QUICK_TABS) do
        if q.tabs[k] == nil then q.tabs[k] = true end
    end
    return q
end

function ns.SpellTabsTaken()
    local NB = ns.NativeSpellBook
    if NB and NB.OthersOccupied then
        return NB.OthersOccupied() and true or false
    end
    return false
end

function ns.SpellEnhOn()
    if ns.SpellTabsTaken() then return false end
    local v = DB().ui.spellEnh
    if v == nil then return true end
    return v == true
end

function ns.ProfModuleOn()
    return ns.QuickCfg().tabs.Professions ~= false
end

function ns.SetProfModule(on)
    ns.QuickCfg().tabs.Professions = on and true or false
end

function ns.TalentEnhOn()
    local v = DB().ui.talentEnh
    if v == nil then return true end
    return v == true
end

function ns.SetTalentEnh(on)
    DB().ui.talentEnh = on and true or false
    if ns.ConfirmReload and ns.AddonLoaded and ns.AddonLoaded("DungeonsForeverClass") then
        ns.ConfirmReload(on and ns.L["「天赋页增强」已开启，重载界面后生效"]
            or ns.L["「天赋页增强」已关闭，重载后生效"])
    end
end

function ns.LegacyEnhOn()
    local v = DB().ui.legacyEnh
    if v == nil then return true end
    return v == true
end

function ns.SetLegacyEnh(on)
    DB().ui.legacyEnh = on and true or false
    local LP = ns.LegacyPage
    if LP and LP.ApplyToggle then LP.ApplyToggle(on and true or false) end
    if ns.ConfirmReload and ns.AddonLoaded and ns.AddonLoaded("DungeonsForeverClass") then
        ns.ConfirmReload(on and ns.L["「传承点增强」已开启，重载界面后生效"]
            or ns.L["「传承点增强」已关闭，重载后生效"])
    end
end

function ns.ConfirmReload(msg)
    if not StaticPopupDialogs["DF_RELOAD_REQUIRED"] then
        StaticPopupDialogs["DF_RELOAD_REQUIRED"] = {
            text = "%s",
            button1 = ns.L["立即重载"],
            button2 = ns.L["稍后"],
            OnAccept = function()
                if ReloadUI then pcall(ReloadUI) end
            end,
            timeout = 0,
            whileDead = true,
            hideOnEscape = true,
            preferredIndex = 3,
        }
    end
    StaticPopup_Show("DF_RELOAD_REQUIRED", msg)
    for i = 1, 4 do
        local f = _G["StaticPopup" .. i]
        if f and f:IsShown() and f.which == "DF_RELOAD_REQUIRED" then
            f:SetFrameStrata("FULLSCREEN_DIALOG")
            f:ClearAllPoints()
            f:SetPoint("CENTER", UIParent, "CENTER", 0, 60)
        end
    end
end

function ns.SetSpellEnh(on)
    if on and ns.SpellTabsTaken() then on = false end
    DB().ui.spellEnh = on and true or false
    if ns.NativeSpellBook and ns.NativeSpellBook.SetEnabled then
        ns.NativeSpellBook.SetEnabled(on and true or false)
    end
end

function ns.MapEntryOn()
    local v = DB().ui.mapEntry
    if v == nil then return true end
    return v == true
end

function ns.SetMapEntry(on)
    DB().ui.mapEntry = on and true or false
    local W = ns.MapWorldModule
    if W and W.ApplyEntryToggle then W.ApplyEntryToggle() end
    if on and ns.WarnGamepadMap then pcall(ns.WarnGamepadMap) end
end

function ns.InstanceMapOn()
    local v = DB().ui.instanceMap
    if v == nil then return true end
    return v == true
end

function ns.SetInstanceMap(on)
    DB().ui.instanceMap = on and true or false
    local W = ns.MapWorldModule
    if W and W.ApplyEntryToggle then W.ApplyEntryToggle() end
end

local gpWarnFrame

local function BuildGpWarn()
    if gpWarnFrame then return gpWarnFrame end
    local shade = CreateFrame("Button", "DungeonsForeverGamepadWarn", UIParent)
    shade:SetAllPoints(UIParent)
    shade:SetFrameStrata("FULLSCREEN_DIALOG")
    shade:EnableMouse(true)
    local dim = shade:CreateTexture(nil, "BACKGROUND")
    dim:SetAllPoints()
    dim:SetColorTexture(0, 0, 0, 0.55)

    local card = CreateFrame("Frame", nil, shade, "BackdropTemplate")
    card:SetSize(340, 190)
    card:SetPoint("CENTER", UIParent, "CENTER", 0, 40)
    card:SetFrameLevel(shade:GetFrameLevel() + 2)
    card:EnableMouse(true)
    if ns.hui and ns.hui.SkinPopup then
        pcall(ns.hui.SkinPopup, card, 10, nil, ns.hui.layer and ns.hui.layer.L0)
    else
        card:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8x8" })
        card:SetBackdropColor(0x0A / 255, 0x0C / 255, 0x10 / 255, 1)
    end
    if ns.hui and ns.hui.SkinShadow then pcall(ns.hui.SkinShadow, card) end

    local title = card:CreateFontString(nil, "OVERLAY")
    title:SetFont(ns.FONT, 15, "")
    title:SetPoint("TOPLEFT", card, "TOPLEFT", 16, -14)
    title:SetText(ns.L["手柄模式提醒"])
    title:SetTextColor(0.95, 0.96, 0.98)

    local body = card:CreateFontString(nil, "OVERLAY")
    body:SetFont(ns.FONT, 12, "")
    body:SetPoint("TOPLEFT", card, "TOPLEFT", 16, -40)
    body:SetPoint("TOPRIGHT", card, "TOPRIGHT", -16, -40)
    body:SetJustifyH("LEFT")
    body:SetText(ns.L["检测到手柄模式，而「地图增强」正开着。它在副本内会接管地图与任务面板，手柄操作可能失灵，建议关闭。"])
    body:SetTextColor(0.80, 0.82, 0.86)

    local function Close()
        shade:Hide()
    end

    local bt1 = ns.CreateButton(card)
    bt1:SetSize(140, 26)
    bt1:SetPoint("BOTTOMLEFT", card, "BOTTOMLEFT", 16, 38)
    bt1:SetText(ns.L["关闭地图增强"])
    bt1:SetScript("OnClick", function()
        ns.PlaySound(1)
        Close()
        ns.SetMapEntry(false)
        if ns.SyncZoneHintCard then pcall(ns.SyncZoneHintCard) end
    end)

    local bt2 = ns.CreateButton(card)
    bt2:SetSize(140, 26)
    bt2:SetPoint("BOTTOMRIGHT", card, "BOTTOMRIGHT", -16, 38)
    bt2:SetText(ns.L["本次保留"])
    bt2:SetScript("OnClick", function()
        ns.PlaySound(1)
        Close()
    end)

    local link = card:CreateFontString(nil, "OVERLAY")
    link:SetFont(ns.FONT, 11, "")
    link:SetPoint("BOTTOM", card, "BOTTOM", 0, 14)
    link:SetText(ns.L["以后不再提示"])
    link:SetTextColor(0.48, 0.50, 0.54)
    link:SetJustifyH("CENTER")

    local linkBtn = CreateFrame("Button", nil, card)
    linkBtn:SetAllPoints(link)
    linkBtn:SetFrameLevel(card:GetFrameLevel() + 3)
    linkBtn:SetScript("OnEnter", function() link:SetTextColor(0.85, 0.86, 0.90) end)
    linkBtn:SetScript("OnLeave", function() link:SetTextColor(0.48, 0.50, 0.54) end)
    linkBtn:SetScript("OnClick", function()
        ns.PlaySound(1)
        DB().ui.gpWarnOff = true
        Close()
    end)

    shade:SetScript("OnClick", Close)
    shade:Hide()
    table.insert(UISpecialFrames, "DungeonsForeverGamepadWarn")
    gpWarnFrame = shade
    return shade
end

function ns.WarnGamepadMap()
    if ns.__gpWarned then return end
    if DB().ui.gpWarnOff then return end
    if not (ns.MapEntryOn and ns.MapEntryOn()) then return end
    if not (InputUtil and InputUtil.IsGamepadUIEnabled and InputUtil.IsGamepadUIEnabled()) then return end
    ns.__gpWarned = true
    C_Timer.After(2, function()
        if DB().ui.gpWarnOff then return end
        if not (InputUtil and InputUtil.IsGamepadUIEnabled and InputUtil.IsGamepadUIEnabled()) then return end
        if not (ns.MapEntryOn and ns.MapEntryOn()) then return end
        local f = BuildGpWarn()
        if f then f:Show() end
    end)
end

do
    local candidates = {}
    if GetLocale() == "zhCN" then
        candidates[#candidates + 1] = "ARHei.ttf"
    end
    for _, name in ipairs({
        "ARKai_T.ttf", "ARHei.ttf", "ARKai_C.ttf",
        "bLEI00D.TTF", "bHEI00M.TTF", "bKAI00M.TTF", "arheiuhk_bd.TTF",
    }) do
        candidates[#candidates + 1] = name
    end
    local probe = UIParent:CreateFontString()
    probe:Hide()
    for _, name in ipairs(candidates) do
        local path = format("Fonts\\%s", name)
        if pcall(probe.SetFont, probe, path, 15, "OUTLINE") and probe:GetFont() then
            ns.FONT = path
            break
        end
    end
    local game = _G.GameFontNormal
    if not ns.FONT and type(game) == "table" and type(game.GetFont) == "function" then
        local ok, p = pcall(game.GetFont, game)
        if ok and type(p) == "string" then ns.FONT = p end
    end
    if not ns.FONT and type(STANDARD_TEXT_FONT) == "string" then
        ns.FONT = STANDARD_TEXT_FONT
    end
    ns.FONT = ns.FONT or "Fonts\\FRIZQT__.TTF"
end

do
    local hit
    function ns.NDuiB()
        if hit then return hit end
        local nd = _G.NDui
        local B = type(nd) == "table" and nd[1]
        if type(B) ~= "table" or type(B.Reskin) ~= "function" then return nil end
        local C = nd[2]
        local skins = type(C) == "table" and C.db and C.db["Skins"]
        if type(skins) == "table" and skins["BlizzardSkins"] == false then return nil end
        hit = B
        return B
    end

    function ns.NDuiOn()
        return ns.NDuiB() ~= nil
    end

    function ns.NDuiReskin(frame)
        if not frame or frame.__dfNd then return frame end
        local B = ns.NDuiB()
        if not B then return frame end
        if pcall(B.Reskin, frame) then frame.__dfNd = true end
        return frame
    end

    function ns.NDuiNavButton(frame)
        if not frame or frame.__dfNav then return frame end
        local B = ns.NDuiB()
        if not B then return frame end
        if not pcall(B.Reskin, frame) then return frame end
        frame.__dfNav = true
        frame.__dfNd = true
        local names = { "arrowUp", "arrowDown" }
        for i = 1, #names do
            local tex = frame[names[i]]
            if type(tex) == "table" and tex.SetAlpha then pcall(tex.SetAlpha, tex, 0) end
        end
        local nd = _G.NDui
        local DB = type(nd) == "table" and nd[4]
        local r = (DB and DB.r) or 0.3
        local g = (DB and DB.g) or 0.3
        local b = (DB and DB.b) or 0.3
        local sel = frame.selected
        if type(sel) == "table" then
            pcall(sel.SetDrawLayer, sel, "BACKGROUND", 1)
            pcall(sel.SetColorTexture, sel, r, g, b, 0.25)
            if frame.__bg then pcall(sel.SetInside, sel, frame.__bg) end
        end
        return frame
    end

    local thinFonts, thinSeq = {}, 0
    function ns.ThinFont(fs)
        if not fs or not fs.GetFont or not fs.SetFontObject then return end
        local ok, fn, size, flags = pcall(fs.GetFont, fs)
        if not ok or type(fn) ~= "string" or not size then return end
        if type(flags) == "string" and flags == "" then return end
        local px = math.floor(size + 0.5)
        local key = fn .. "#" .. px
        local font = thinFonts[key]
        if not font then
            thinSeq = thinSeq + 1
            font = CreateFont("DungeonsForeverThinFont_" .. thinSeq)
            font:SetFont(fn, px, "")
            thinFonts[key] = font
        end
        pcall(fs.SetFontObject, fs, font)
    end
end

local loadedFuncs = {}
local boot = CreateFrame("Frame")
boot:RegisterEvent("ADDON_LOADED")
boot:SetScript("OnEvent", function(self, event, name)
    C_Timer.After(0, function()
    if name ~= addonName then return end
    self:UnregisterEvent("ADDON_LOADED")
    DB()
    for _, fn in ipairs(loadedFuncs) do
        local ok, err = xpcall(fn, function(e)
            return tostring(e) .. "\n" .. debugstack(2)
        end)
        if not ok then
            print("|cffff5040[无限副本手册] 初始化回调出错（已跳过，不影响后续模块）：|r\n" .. tostring(err))
        end
    end
    end)
end)

do
    local function UnregisterForbidden()
        if UIParent and UIParent.UnregisterEvent then
            pcall(UIParent.UnregisterEvent, UIParent, "ADDON_ACTION_FORBIDDEN")
        end
        if GameEvent and GameEvent.UnregisterInternalEvent then
            pcall(GameEvent.UnregisterInternalEvent, "ADDON_ACTION_FORBIDDEN")
        end
    end

    local function GamepadUIEnabled()
        local ok, enabled = pcall(function()
            return InputUtil and InputUtil.IsGamepadUIEnabled and InputUtil.IsGamepadUIEnabled()
        end)
        return (ok and enabled) and true or false
    end

    local function TrySilence()
        if not GamepadUIEnabled() then return false end
        UnregisterForbidden()
        return true
    end

    local guard = CreateFrame("Frame")
    local ticker

    local function Stop()
        if ticker then
            ticker:Cancel()
            ticker = nil
        end
    end

    local function Try()
        if not TrySilence() then return end
        Stop()
        if ns.WarnGamepadMap then pcall(ns.WarnGamepadMap) end
    end

    guard:RegisterEvent("PLAYER_LOGIN")
    guard:RegisterEvent("PLAYER_ENTERING_WORLD")
    guard:RegisterEvent("GAME_PAD_CONNECTED")
    guard:SetScript("OnEvent", function(self, event)
        if event == "PLAYER_LOGIN" then self:UnregisterEvent("PLAYER_LOGIN") end
        if event == "PLAYER_ENTERING_WORLD" then self:UnregisterEvent("PLAYER_ENTERING_WORLD") end
        if C_Timer and C_Timer.After then C_Timer.After(0, Try) end
        if not ticker and C_Timer and C_Timer.NewTicker then ticker = C_Timer.NewTicker(2, Try) end
    end)
end

function ns.Init(fn)
    loadedFuncs[#loadedFuncs + 1] = fn
    local sink = rawget(ns, "__inits")
    if sink then sink[#sink + 1] = fn end
end

function ns.PlaySound(id)
    if type(id) ~= "number" or ns.options.buttonSound == false then return end
    local kit = SOUNDKIT and SOUNDKIT.IG_MAINMENU_OPTION_CHECKBOX_ON
    if kit then
        PlaySound(kit)
    else
        PlaySound(856)
    end
end

function ns.CreateButton(parent)
    local bt = CreateFrame("Button", nil, parent, "BackdropTemplate")
    bt:SetBackdrop({
        edgeFile = "Interface/ChatFrame/ChatFrameBackground",
        edgeSize = 1,
    })
    bt:SetBackdropBorderColor(0, 0, 0, 1)
    local t = bt:CreateFontString()
    t:SetAllPoints()
    t:SetTextColor(0xa0 / 255, 0xa0 / 255, 0xa0 / 255)
    t:SetFont(ns.FONT, 15, "OUTLINE")
    bt:SetFontString(t)
    ns.hui.SkinButton(bt)
    function bt:Disable() self:SetEnabled(false) end
    function bt:Enable() self:SetEnabled(true) end
    bt:SetScript("OnEnter", nil)
    bt:SetScript("OnLeave", nil)
    return bt
end

local EDIT_BG = { 0x0a / 255, 0x0a / 255, 0x0d / 255, 0.55 }
local EDIT_BORDER = { 0.30, 0.30, 0.28, 0.85 }
local EDIT_BORDER_FOCUS = { 0x46 / 255, 0xbf / 255, 0x72 / 255, 1 }
local CORNER_FILL = "Interface/AddOns/DungeonsForever/Media/LibHUI/HUIRoundCornerFill"
local CORNER_INSET = 8

function ns.CreateEditBox(parent, size)
    local eb = CreateFrame("EditBox", nil, parent)
    eb:SetSize(size or 140, 22)
    eb:SetTextInsets(5, 5, 0, 0)
    eb:SetAutoFocus(false)
    eb:SetFont(ns.FONT, 12, "")

    if ns.hui and ns.hui.BuildRoundedBG then
        ns.hui.BuildRoundedBG(eb, CORNER_INSET, EDIT_BG, "both", false)
    else
        local bg = eb:CreateTexture(nil, "BACKGROUND")
        bg:SetColorTexture(EDIT_BG[1], EDIT_BG[2], EDIT_BG[3], EDIT_BG[4])
        bg:SetPoint("TOPLEFT", eb, "TOPLEFT", CORNER_INSET, -CORNER_INSET)
        bg:SetPoint("BOTTOMRIGHT", eb, "BOTTOMRIGHT", -CORNER_INSET, CORNER_INSET)

        local edges = {
            { "TOPLEFT", CORNER_INSET, 0, "TOPRIGHT", -CORNER_INSET, 0, nil, CORNER_INSET },
            { "BOTTOMLEFT", CORNER_INSET, 0, "BOTTOMRIGHT", -CORNER_INSET, 0, nil, CORNER_INSET },
            { "TOPLEFT", 0, -CORNER_INSET, "BOTTOMLEFT", 0, CORNER_INSET, CORNER_INSET, nil },
            { "TOPRIGHT", 0, -CORNER_INSET, "BOTTOMRIGHT", 0, CORNER_INSET, CORNER_INSET, nil },
        }
        for _, e in ipairs(edges) do
            local tex = eb:CreateTexture(nil, "BACKGROUND")
            tex:SetColorTexture(EDIT_BG[1], EDIT_BG[2], EDIT_BG[3], EDIT_BG[4])
            tex:SetPoint(e[1], eb, e[1], e[2], e[3])
            tex:SetPoint(e[4], eb, e[4], e[5], e[6])
            if e[7] then tex:SetWidth(e[7]) end
            if e[8] then tex:SetHeight(e[8]) end
        end
        for _, point in ipairs({ "TOPLEFT", "TOPRIGHT", "BOTTOMLEFT", "BOTTOMRIGHT" }) do
            local corner = eb:CreateTexture(nil, "BACKGROUND")
            corner:SetTexture(CORNER_FILL)
            corner:SetSize(CORNER_INSET, CORNER_INSET)
            corner:SetPoint(point, eb, point, 0, 0)
            corner:SetVertexColor(EDIT_BG[1], EDIT_BG[2], EDIT_BG[3])
            corner:SetAlpha(EDIT_BG[4])
        end
    end

    local border = ns.hui.BuildRoundBorder(eb, CORNER_INSET, EDIT_BORDER, nil, "OVERLAY", "both", 1) or {}
    for _, tex in ipairs(border) do tex:SetShown(true) end
    local function Paint(color)
        for _, tex in ipairs(border) do
            if tex.__huiBorderStrip then
                tex:SetColorTexture(color[1], color[2], color[3], 1)
                tex:SetAlpha(color[4] or 1)
            else
                tex:SetVertexColor(color[1], color[2], color[3])
                tex:SetAlpha(color[4] or 1)
            end
        end
    end
    eb:HookScript("OnEditFocusGained", function()
        local ac = (ns.hui and ns.hui.ACCENT) or EDIT_BORDER_FOCUS
        Paint({ ac[1], ac[2], ac[3], 1 })
    end)
    eb:HookScript("OnEditFocusLost", function() Paint(EDIT_BORDER) end)
    eb.RestoreBorder = function() Paint(EDIT_BORDER) end
    eb:HookScript("OnEscapePressed", function(self) self:ClearFocus() end)
    eb:HookScript("OnEnterPressed", function(self) self:ClearFocus() end)
    return eb
end

function ns.SkinPopupFont(p)
    if not (p and ns.FONT) then return end
    local function fixFS(fs)
        if not (fs and fs.GetFont and fs.SetFont) then return end
        local path, size, flags = fs:GetFont()
        if path and path ~= ns.FONT then
            pcall(fs.SetFont, fs, ns.FONT, size or 12, flags or "")
        end
    end
    local function walk(f, depth)
        if not (f and depth <= 4) then return end
        fixFS(f)
        for _, r in ipairs({ f:GetRegions() }) do fixFS(r) end
        for _, c in ipairs({ f:GetChildren() }) do walk(c, depth + 1) end
    end
    walk(p, 0)
end

function ns.SkinTipFont(tt, size, skipResize)
    tt = tt or _G.GameTooltip
    if not (tt and tt.NumLines and ns.FONT) then return end
    local prefix = tt.GetName and tt:GetName()
    if type(prefix) ~= "string" then return end
    local n = tt:NumLines()
    if type(n) ~= "number" then n = type(n) == "table" and #n or 0 end
    if n <= 0 then return end
    local want = tonumber(size) or 0
    for i = 1, n do
        for _, side in ipairs({ "TextLeft", "TextRight" }) do
            local fs = _G[prefix .. side .. i]
            if fs and fs.SetFont then
                if not fs.__dfOrigFont then
                    local p0, s0, f0 = fs:GetFont()
                    if p0 then fs.__dfOrigFont = { p0, s0, f0 } end
                end
                local _, sz, flags = fs:GetFont()
                pcall(fs.SetFont, fs, ns.FONT, want > 0 and want or tonumber(sz) or 14, flags or "")
            end
        end
    end
    if skipResize then return end
    local sum0 = 0
    local maxW = 0
    for i = 1, n do
        local l = _G[prefix .. "TextLeft" .. i]
        if l and l.SetWidth then
            sum0 = sum0 + (l:GetStringHeight() or 0)
            l:SetWidth(4000)
            if l.GetText then l:SetText(l:GetText()) end
            local w = l:GetStringWidth() or 0
            if w > maxW then maxW = w end
        end
    end
    if maxW > 460 then maxW = 460 end
    local sum1 = 0
    for i = 1, n do
        local l = _G[prefix .. "TextLeft" .. i]
        if l then
            if maxW > 20 then l:SetWidth(maxW) end
            if l.GetText then l:SetText(l:GetText()) end
            sum1 = sum1 + (l:GetStringHeight() or 0)
        end
    end
    if maxW > 20 and tt.SetWidth and tt.SetHeight then
        local pad = (tt:GetHeight() or 0) - sum0
        tt:SetWidth(maxW + 20)
        tt:SetHeight(sum1 + pad)
    end
end

local TIP_FRAMES = { "GameTooltip", "ItemRefTooltip", "ShoppingTooltip1", "ShoppingTooltip2" }

function ns.TipFontOn()
    if ns.hui and ns.hui.ExternalTipSkin and ns.hui.ExternalTipSkin() then return false end
    local db = DungeonsForeverDB
    local ui = db and db.ui
    local t = ui and ui.tip
    return (t and t.global == true) and true or false
end

function ns.RestoreTipFont(tt)
    tt = tt or _G.GameTooltip
    if not (tt and tt.NumLines) then return end
    local prefix = tt.GetName and tt:GetName()
    if type(prefix) ~= "string" then return end
    local n = tt:NumLines()
    if type(n) ~= "number" then n = type(n) == "table" and #n or 0 end
    for i = 1, n do
        for _, side in ipairs({ "TextLeft", "TextRight" }) do
            local fs = _G[prefix .. side .. i]
            if fs and fs.SetFont then
                local o = fs.__dfOrigFont
                if o then
                    pcall(fs.SetFont, fs, o[1], o[2], o[3])
                elseif fs.SetFontObject and GameTooltipText then
                    pcall(fs.SetFontObject, fs, GameTooltipText)
                end
            end
        end
    end
end

function ns.RefreshTipFonts()
    local on = ns.TipFontOn()
    for _, name in ipairs(TIP_FRAMES) do
        local tt = _G[name]
        if tt and tt.IsShown and tt:IsShown() then
            if on then
                ns.SkinTipFont(tt, nil, true)
            else
                ns.RestoreTipFont(tt)
            end
        end
    end
end

function ns.HookTipFont(tt, size)
    if not (tt and tt.HookScript) or tt.__dfTipFont then return end
    tt.__dfTipFont = true
    tt.__dfTipFrames = -1
    tt:HookScript("OnShow", function(self)
        if not ns.TipFontOn() then
            if (self.__dfTipFrames or -1) >= 0 then
                self.__dfTipFrames = -1
                ns.RestoreTipFont(self)
            end
            return
        end
        self.__dfTipFrames = 0
        ns.SkinTipFont(self, size, true)
    end)
    tt:HookScript("OnUpdate", function(self)
        if (self.__dfTipFrames or -1) < 0 then return end
        if not ns.TipFontOn() then
            self.__dfTipFrames = -1
            ns.RestoreTipFont(self)
            return
        end
        self.__dfTipFrames = self.__dfTipFrames + 1
        if self.__dfTipFrames >= 2 then self.__dfTipFrames = -1 end
        ns.SkinTipFont(self, size, true)
    end)
    tt:HookScript("OnHide", function(self) self.__dfTipFrames = -1 end)
end

function ns.HookAllTipFont()
    for _, name in ipairs(TIP_FRAMES) do
        local tt = _G[name]
        if tt then ns.HookTipFont(tt) end
    end
end

ns.Init(function() ns.HookAllTipFont() end)
function ns.GetWindowColorTheme() return nil end
function ns.WithColorThemeScope(_, fn) if fn then return fn() end end
function ns.WithThemeScope(_, fn) if fn then return fn() end end
function ns.After(_, fn) if fn then fn() end end
function ns.UpdateItemLib() end
function ns.PageVisible(page)
    if not page or not page.IsShown or not page:IsShown() then return false end
    local mf = _G.DungeonsForever_MainFrame
    if mf and mf.IsShown then return mf:IsShown() end
    return true
end

do
    local gcGuard = CreateFrame("Frame")
    gcGuard:RegisterEvent("PLAYER_LOGIN")
    gcGuard:SetScript("OnEvent", function(self)
        C_Timer.After(0, function()
        self:UnregisterEvent("PLAYER_LOGIN")
        local run = function()
            local J = ns.IdleJobs
            if J then
                J.StepGC(90, 512)
                J.StepGC(90, 512)
            else
                collectgarbage("step", 512)
            end
        end
        if C_Timer and C_Timer.After then
            C_Timer.After(5, run)
        else
            run()
        end
                if C_Timer and C_Timer.After then
                    C_Timer.After(0.3, function()
                        local J = ns.IdleJobs
                        if not J then return end
                        local tabs = (type(ns.QuickCfg) == "function") and ns.QuickCfg().tabs or {}
                        local wantProf = tabs["Professions"] ~= false
                        local wantBis = tabs["Bis"] ~= false
                        local wantGear = tabs["Gear"] ~= false
                local profEnsure = ns.EnsureProfRecipes
                local profKeys = nil
                if not wantProf and wantBis then
                    profKeys = { "enchanting", "leatherworking" }
                end
                if type(profEnsure) == "function" and (wantProf or wantBis) then
                    J.Add(function()
                        local mf = _G.DungeonsForever_MainFrame
                        if mf and mf.IsShown and mf:IsShown() then return false end
                        if profKeys == nil then
                            local PM = ns.ProfModule
                            local learned = PM and PM.ProfLearned and PM.ProfLearned()
                            local keys = {}
                            if type(learned) == "table" then
                                for slug in pairs(learned) do keys[#keys + 1] = slug end
                            end
                            profKeys = keys
                        end
                        profEnsure(profKeys)
                        if DungeonsForeverDB and DungeonsForeverDB.dfMemProbe then
                            ns.MemMark("profData")
                        end
                        return true
                    end)
                end
                local UD = ns.DungeonUI
                if UD and type(UD.EnsureBuilt) == "function"
                   and type(C_Timer) == "table" and C_Timer.After then
                    local pages = { "Raids", "Professions", "Explore",
                        "Collections", "Factions", "Bis", "Tier", "PvP" }
                    C_Timer.After(0.6, function()
                        pcall(function()
                            local mf0 = _G.DungeonsForever_MainFrame
                            if not UD.built and type(UD.Build) == "function"
                               and mf0 and mf0.IsShown and mf0:IsShown() then
                                UD:Build()
                            end
                        end)
                        if not (DungeonsForeverDB and DungeonsForeverDB.dfPrebuild) then return end
                        local probeUD = DungeonsForeverDB and DungeonsForeverDB.dfMemProbe
                        local pb = { pages = {} }
                        local i = 0
                        local function step()
                            local mf = _G.DungeonsForever_MainFrame
                            if mf and mf.IsShown and mf:IsShown() then
                                C_Timer.After(0.5, step)
                                return
                            end
                            i = i + 1
                            local k = pages[i]
                            if not k then
                                if DungeonsForeverDB then
                                    DungeonsForeverDB.dfPbLog = table.concat(pb.pages, " ")
                                end
                                return
                            end
                            pcall(UD.EnsureBuilt, UD, k)
                            if probeUD then ns.MemMark("pb_" .. k) end
                            pb.pages[#pb.pages + 1] = k .. ":" .. tostring(UD.subBuilt and UD.subBuilt[k] == true and 1 or 0)
                            if ns.IdleJobs then ns.IdleJobs.Urgent(step) end
                        end
                        if ns.IdleJobs then ns.IdleJobs.Urgent(step) end
                    end)
                end
            end)
        end
        if DungeonsForeverDB and DungeonsForeverDB.dfAutoTest
           and C_Timer and C_Timer.After then
            DungeonsForeverDB.dfAutoTest = nil
            pcall(function()
                if io and io.open then
                    local f = io.open("DF_AUTOTEST_RESULT.txt", "w")
                    if f then f:write("running") f:close() end
                end
            end)
            C_Timer.After(1, function()
                local f = CreateFrame("Frame")
                f.samples = {}
                f.last = debugprofilestop()
                f:SetScript("OnUpdate", function(self)
                    local now = debugprofilestop()
                    local d = now - self.last
                    self.last = now
                    if d > 0 and d < 5000 then
                        self.samples[#self.samples + 1] = d
                    end
                end)
                local wlog = {}
                local cfOrig = CreateFrame
                local cfN, cfT, cfMax = 0, 0, 0
                CreateFrame = function(...)
                    local s = debugprofilestop()
                    local r = cfOrig(...)
                    local d = debugprofilestop() - s
                    cfT = cfT + d
                    if d > cfMax then cfMax = d end
                    cfN = cfN + 1
                    return r
                end
                local function wrapw(tbl, fn, label)
                    local orig = tbl[fn]
                    if type(orig) ~= "function" then return end
                    tbl[fn] = function(...)
                        local s = debugprofilestop()
                        local r1, r2, r3, r4 = orig(...)
                        wlog[#wlog + 1] = string.format("%.2fs %s %.0fms",
                            (debugprofilestop() - f.last0) / 1000, label, debugprofilestop() - s)
                        return r1, r2, r3, r4
                    end
                end
                C_Timer.After(DungeonsForeverDB.dfAutoTestDelay or 0.5, function()
                    f.samples = {}
                    f.last = debugprofilestop()
                    f.last0 = debugprofilestop()
                    local mf = _G.DungeonsForever_MainFrame
                    if ns.GearModule then wrapw(ns.GearModule, "Refresh", "GRefresh") end
                    if ns.GearModule then wrapw(ns.GearModule, "BuildCatalog", "BuildCatalog") end
                    wrapw(ns, "EnsureGearData", "GearEnsure")
                    wrapw(ns, "EnsureProfRecipes", "ProfEnsure")
                    local preCatalog = (ns.GearModule and ns.GearModule.catalog ~= nil) or false
                    local white
                    if DungeonsForeverDB.dfWhite then
                        white = CreateFrame("Frame", nil, UIParent)
                        white:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8x8" })
                        white:SetBackdropColor(0.06, 0.07, 0.10, 0.95)
                        if mf and mf.GetWidth and mf:GetWidth() > 0 then
                            white:SetSize(mf:GetWidth(), mf:GetHeight())
                        else
                            white:SetSize(900, 560)
                        end
                        white:SetPoint("CENTER", UIParent, "CENTER", 0, 0)
                        white:SetFrameStrata("HIGH")
                    end
                    local t0 = debugprofilestop()
                    if white then
                        white:Show()
                    elseif ns.Open then ns.Open() elseif mf then mf:Show() end
                    if not white and ns.DungeonUI then ns.DungeonUI:SwitchSub("Gear") end
                    local openMs = debugprofilestop() - t0
                    wlog[#wlog + 1] = string.format("%.2fs icons %s/%s",
                        (debugprofilestop() - f.last0) / 1000,
                        tostring(ns.GearModule and ns.GearModule.__iconWarmN or "?"),
                        tostring(ns.GearModule and ns.GearModule.__iconWarmTotal or "?"))
                    C_Timer.After(5, function()
                        local n1 = #f.samples
                        local t1 = debugprofilestop()
                        if white then white:Hide() elseif mf then mf:Hide() end
                        local closeMs = debugprofilestop() - t1
                        C_Timer.After(0.5, function()
                            local n2 = #f.samples
                            local t2 = debugprofilestop()
                            if white then
                                white:Show()
                            elseif ns.Open then ns.Open() elseif mf then mf:Show() end
                            if not white and ns.DungeonUI then ns.DungeonUI:SwitchSub("Gear") end
                            local reopenMs = debugprofilestop() - t2
                            C_Timer.After(4, function()
                                f:SetScript("OnUpdate", nil)
                                if white then white:Hide() end
                                CreateFrame = cfOrig
                                wlog[#wlog + 1] = string.format("cf=%d %.0fms max%.1f", cfN, cfT, cfMax)
                                local function seg(a, b)
                                    local mx, c40 = 0, 0
                                    local top = {}
                                    for i = a, b do
                                        local v = f.samples[i]
                                        if v then
                                            if v > mx then mx = v end
                                            if v > 40 and #top < 24 then
                                                c40 = c40 + 1
                                                top[#top + 1] = string.format("%.2fs:%.0f", (i - a) * 0.0167, v)
                                            end
                                        end
                                    end
                                    return mx, c40, table.concat(top, " ")
                                end
                                local m1, c1, s1 = seg(1, n1)
                                local m2, c2, s2 = seg(n1 + 1, n2)
                                local m3, c3, s3 = seg(n2 + 1, #f.samples)
                                DungeonsForeverDB.dfAutoTestResult = {
                                    t = type(date) == "function" and date("%H:%M:%S") or "",
                                    prime = "none",
                                    openMs = openMs, closeMs = closeMs, reopenMs = reopenMs,
                                    preCatalog = preCatalog,
                                    segOpen = { max = m1, c40 = c1, spikes = s1 },
                                    segClosed = { max = m2, c40 = c2, spikes = s2 },
                                    segReopen = { max = m3, c40 = c3, spikes = s3 },
                                    paintMs = (ns.GearModule and ns.GearModule.__paintMs) or "",
                                    diag = table.concat(wlog, " | "),
                                }
                                pcall(function()
                                    if not (io and io.open) then return end
                                    local r = DungeonsForeverDB.dfAutoTestResult
                                    local fh = io.open("DF_AUTOTEST_RESULT.txt", "w")
                                    if not fh then return end
                                    fh:write(string.format(
                                        "t=%s prime=%s openMs=%.1f closeMs=%.1f reopenMs=%.1f Omax=%.1f Oc40=%d Ospk=[%s] Cmax=%.1f Cc40=%d Rmax=%.1f Rc40=%d Rspk=[%s] diag=%s",
                                        r.t or "", r.prime or "none",
                                        r.openMs or 0, r.closeMs or 0, r.reopenMs or 0,
                                        r.segOpen.max or 0, r.segOpen.c40 or 0, r.segOpen.spikes or "",
                                        r.segClosed.max or 0, r.segClosed.c40 or 0,
                                        r.segReopen.max or 0, r.segReopen.c40 or 0, r.segReopen.spikes or "",
                                        r.diag or ""))
                                    fh:close()
                                end)
                            end)
                        end)
                    end)
                end)
            end)
        end
        end)
    end)
end

ns.IdleJobs = nil
do
    local J = {}
    ns.IdleJobs = J
    local qNorm, qUrg = {}, {}
    local function inCombat()
        return InCombatLockdown and InCombatLockdown() or false
    end
    local function pump(q, t0, budget, deferred)
        while #q > 0 do
            if debugprofilestop() - t0 > budget then return end
            local fn = table.remove(q, 1)
            local ok, done = pcall(fn)
            if ok and done ~= true then
                deferred[#deferred + 1] = fn
            end
        end
    end
    local f = CreateFrame("Frame")
    local armed = false
    local function tick()
        if #qUrg == 0 and #qNorm == 0 then
            armed = false
            f:SetScript("OnUpdate", nil)
            return
        end
        local urgent = #qUrg > 0
        if not urgent and inCombat() then return end
        local budget = urgent and 4 or 4
        local t0 = debugprofilestop()
        local dUrg, dNorm = {}, {}
        pump(qUrg, t0, budget, dUrg)
        if #qUrg == 0 then
            pump(qNorm, t0, budget, dNorm)
        end
        for i = 1, #dUrg do qUrg[#qUrg + 1] = dUrg[i] end
        for i = 1, #dNorm do qNorm[#qNorm + 1] = dNorm[i] end
    end
    local function arm()
        if armed then return end
        armed = true
        f:SetScript("OnUpdate", tick)
    end
    function J.Add(fn)
        if type(fn) ~= "function" then return end
        qNorm[#qNorm + 1] = fn
        arm()
    end
    function J.Urgent(fn)
        if type(fn) ~= "function" then return end
        qUrg[#qUrg + 1] = fn
        arm()
    end
    function J.StepGC(frames, kb)
        local left = frames or 120
        J.Add(function()
            if left <= 0 then return true end
            left = left - 1
            collectgarbage("step", kb or 512)
            return false
        end)
    end
end

ns.PaintJob = nil
do
    local PJ = {}
    ns.PaintJob = PJ
    local active = {}
    local genOf = {}

    local function nowMs()
        return debugprofilestop and debugprofilestop() or 0
    end

    local function hasClock()
        local f = debugprofilestop
        if type(f) ~= "function" then return false end
        local ok, v = pcall(f)
        return ok and type(v) == "number"
    end

    local function step(key, gen)
        local j = active[key]
        if not j or j.gen ~= gen then return true end
        local cap = j.cap or 4
        local t0 = nowMs()
        while true do
            if coroutine.status(j.co) == "dead" then break end
            local ok, err = coroutine.resume(j.co)
            if not ok then
                _G.DF_LAST_PAINT_ERR = tostring(err)
                print("|cffff5040[无限副本手册] 页面渲染出错（已停止该次渲染）：|r" .. tostring(err))
                break
            end
            if coroutine.status(j.co) == "dead" then break end
            if nowMs() - t0 >= cap then return false end
        end
        active[key] = nil
        if type(j.onDone) == "function" then pcall(j.onDone) end
        return true
    end

    function PJ.Run(key, body, onDone, cap)
        if type(body) ~= "function" and type(body) ~= "thread" then return end
        local gen = (genOf[key] or 0) + 1
        genOf[key] = gen
        active[key] = {
            co = type(body) == "thread" and body or coroutine.create(body),
            gen = gen,
            onDone = onDone,
            cap = cap or 4,
        }
        if not hasClock() or not ns.IdleJobs then
            step(key, gen)
            return gen
        end
        ns.IdleJobs.Urgent(function() return step(key, gen) end)
        return gen
    end

    function PJ.Active(key)
        return active[key] ~= nil
    end

    function PJ.Cancel(key)
        genOf[key] = (genOf[key] or 0) + 1
        active[key] = nil
    end
end

local memProbeLog, memMarkLog = {}, {}

SLASH_DFMEMLUA1 = "/dfmem"
SlashCmdList["DFMEMLUA"] = function()
    if type(UpdateAddOnMemoryUsage) == "function" then UpdateAddOnMemoryUsage() end
    local mem1 = type(GetAddOnMemoryUsage) == "function"
        and GetAddOnMemoryUsage("DungeonsForever") or 0
    local heap1 = collectgarbage("count")
    collectgarbage("collect")
    collectgarbage("collect")
    local mem2 = type(GetAddOnMemoryUsage) == "function"
        and GetAddOnMemoryUsage("DungeonsForever") or 0
    local heap2 = collectgarbage("count")
    local log = memProbeLog
    log[#log + 1] = {
        t = date("%m-%d %H:%M:%S"),
        ver = GetAddOnMetadata and GetAddOnMetadata("DungeonsForever", "Version") or "?",
        mem = mem1, heap = heap1,
        memAfterGC = mem2, heapAfterGC = heap2,
    }
    if #log > 50 then table.remove(log, 1) end
    print(format("[DFMem] %.2f MB -> GC后 %.2f MB (Lua堆 %.2f -> %.2f MB)",
        mem1 / 1024, mem2 / 1024, heap1 / 1024, heap2 / 1024))
end

function ns.MemMark(label)
    collectgarbage("collect")
    local m = memMarkLog
    local ts = ""
    if type(date) == "function" then ts = date("%H:%M:%S") end
    m[#m + 1] = {
        t = ts,
        label = label,
        heap = collectgarbage("count"),
    }
    if #m > 80 then table.remove(m, 1) end
end

ns.OpenPerf = nil
do
    local OP = {}
    ns.OpenPerf = OP
    OP.log = {}
    local function commit(s, altTotal)
        local total
        if #s > 0 then
            total = s[#s][2]
        elseif altTotal then
            total = altTotal
        else
            total = debugprofilestop and (debugprofilestop() - s.t0) or 0
        end
        local ms = math.floor(total + 0.5)
        local parts = {}
        for i = 1, #s do
            parts[#parts + 1] = s[i][1] .. " " .. math.floor(s[i][2] + 0.5)
        end
        local marks = table.concat(parts, ", ")
        local arr = OP.log
        local ts = ""
        if type(date) == "function" then ts = date("%H:%M:%S") end
        arr[#arr + 1] = { t = ts, page = s.label, ms = ms, marks = marks }
        if #arr > 50 then table.remove(arr, 1) end
    end

    function OP.Begin(label)
        if not (debugprofilestop and C_Timer and C_Timer.After) then return end
        local now = debugprofilestop()
        if OP.__cur then
            local prev = OP.__cur
            OP.__cur = nil
            commit(prev, now - prev.t0)
        end
        local s = { label = tostring(label), t0 = now }
        OP.__cur = s
        C_Timer.After(0.75, function()
            if OP.__cur == s then
                OP.__cur = nil
                commit(s, now - s.t0 + 0.75)
            end
        end)
    end

    function OP.Mark(name)
        local s = OP.__cur
        if s and debugprofilestop then
            s[#s + 1] = { tostring(name), debugprofilestop() - s.t0 }
            if name == "就绪" then
                OP.__cur = nil
                commit(s)
            end
        end
    end
end

local function drainLazy(list, label)
    if type(list) ~= "table" then return 0 end
    local bad = 0
    for i = 1, #list do
        local ok, err = pcall(list[i])
        if not ok then
            bad = bad + 1
            if DEFAULT_CHAT_FRAME and bad <= 3 then
                DEFAULT_CHAT_FRAME:AddMessage("|cffff5555DungeonsForever|r " .. label .. "第 " .. i .. " 项初始化失败：" .. tostring(err))
            end
        end
        list[i] = nil
    end
    return bad
end

local moduleBoot = CreateFrame("Frame")
moduleBoot:RegisterEvent("ADDON_LOADED")
moduleBoot:SetScript("OnEvent", function(self, event, name)
    if name ~= "DungeonsForever" then return end
    self:UnregisterEvent("ADDON_LOADED")
    for _, m in ipairs(ns.MODULES) do
        local want = ns.ModuleWant(m)
        if want then
            if not ns.AddonLoaded(m.addon) then
                if type(C_AddOns) == "table" and C_AddOns.EnableAddOn then pcall(C_AddOns.EnableAddOn, m.addon) end
                if type(C_AddOns) == "table" and C_AddOns.LoadAddOn then
                    pcall(C_AddOns.LoadAddOn, m.addon)
                elseif type(LoadAddOn) == "function" then
                    pcall(LoadAddOn, m.addon)
                end
            end
        elseif type(C_AddOns) == "table" and C_AddOns.DisableAddOn then
            pcall(C_AddOns.DisableAddOn, m.addon)
        end
    end
    local bad = drainLazy(_G.DF_PROF_LAZY, "专业模块")
    bad = bad + drainLazy(_G.DF_MODULE_LAZY, "页面模块")
    _G.DF_PROF_LAZY = nil
    _G.DF_MODULE_LAZY = nil
    if bad > 0 and DEFAULT_CHAT_FRAME then
        DEFAULT_CHAT_FRAME:AddMessage("|cffff5555DungeonsForever|r 有 " .. bad .. " 项页面模块初始化失败，请检查对应子插件是否已启用。")
    end
end)
