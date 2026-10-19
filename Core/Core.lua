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

local function DB()
    DungeonsForeverDB = DungeonsForeverDB or {}
    DungeonsForeverDB.ui = DungeonsForeverDB.ui or {}
    return DungeonsForeverDB
end
ns.DB = DB

ns.options = ns.options or {}
if ns.options.buttonSound == nil then ns.options.buttonSound = true end

ns.QUICK_VER = 1
ns.QUICK_GROUPS = { "dungeon", "prof", "explore" }
ns.QUICK_EXPLORE = { "books", "rewards", "bag", "bm" }
ns.QUICK_TABS = { "Dungeons", "Raids", "Professions", "Explore", "Collections", "Factions", "Bis", "Tier", "PvP", "Gear" }

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
    if type(q.tabs) ~= "table" then q.tabs = {} end
    for _, k in ipairs(ns.QUICK_TABS) do
        if q.tabs[k] == nil then q.tabs[k] = true end
    end
    return q
end

do
    local candidates = {
        "ARKai_T.ttf", "ARHei.TTF", "ARKai_C.ttf",
        "bLEI00D.TTF", "bHEI00M.TTF", "bKAI00M.TTF", "arheiuhk_bd.TTF",
    }
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

    if InputUtil and InputUtil.RegisterForInterfaceTransitions and InputUtil.RegisterGamepadInit then
        pcall(function()
            InputUtil.RegisterForInterfaceTransitions(guard)
            InputUtil.RegisterGamepadInit(guard, function()
                UnregisterForbidden()
            end)
        end)
    end

    guard:RegisterEvent("PLAYER_LOGIN")
    guard:SetScript("OnEvent", function(self, event)
        C_Timer.After(0, function()
        if event == "PLAYER_LOGIN" then
            self:UnregisterEvent("PLAYER_LOGIN")
            if not TrySilence() then
                self:RegisterEvent("PLAYER_ENTERING_WORLD")
            end
        else
            self:UnregisterEvent("PLAYER_ENTERING_WORLD")
            TrySilence()
        end
        end)
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
    t:SetTextColor(1, 1, 1)
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
    eb:HookScript("OnEditFocusGained", function() Paint(EDIT_BORDER_FOCUS) end)
    eb:HookScript("OnEditFocusLost", function() Paint(EDIT_BORDER) end)
    eb.RestoreBorder = function() Paint(EDIT_BORDER) end
    eb:HookScript("OnEscapePressed", function(self) self:ClearFocus() end)
    eb:HookScript("OnEnterPressed", function(self) self:ClearFocus() end)
    return eb
end

function ns.GetWindowTheme() return "hui" end
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
                        local probe = DungeonsForeverDB and DungeonsForeverDB.dfMemProbe
                        local gear = ns.GearModule
                        local ensure = ns.EnsureGearData
                        local tabs = (type(ns.QuickCfg) == "function") and ns.QuickCfg().tabs or {}
                        local wantProf = tabs["Professions"] ~= false
                        local wantBis = tabs["Bis"] ~= false
                        local wantGear = tabs["Gear"] ~= false
                        if type(ensure) == "function" and (wantGear or wantBis) then
                J.Add(function()
                    if gear and gear.built then return true end
                    ensure()
                    if probe then ns.MemMark("gearData") end
                    if gear and type(gear.BuildCatalog) == "function"
                       and not gear.built and not gear.catalog then
                        pcall(gear.BuildCatalog, gear)
                    end
                    if probe then ns.MemMark("catalog") end
                    if gear and type(gear.StartTexWarm) == "function" then
                        pcall(gear.StartTexWarm)
                    end
                    if gear and type(gear.StartIconWarm) == "function" then
                        pcall(gear.StartIconWarm)
                    end
                    if gear and type(gear.StartGlyphWarm) == "function" then
                        pcall(gear.StartGlyphWarm)
                    end
                    if gear and type(gear.StartDataWarm) == "function" then
                        pcall(gear.StartDataWarm)
                    end
                    return true
                end)
                if wantGear then J.Add(function()
                    if gear and gear.built then return true end
                    local mf = _G.DungeonsForever_MainFrame
                    if mf and mf.IsShown and mf:IsShown() then return false end
                    if gear and type(gear.Build) == "function" then
                        local UD = ns.DungeonUI
                        local gp = UD and UD.gearPage or nil
                        if gp and gp.SetParent then
                            pcall(gear.Build, gear, gp)
                            gear.__lastRefreshT = nil
                            if type(gear.Refresh) == "function" then
                                pcall(gear.Refresh, gear, true)
                            end
                            local pool = gear.rowPool
                            if pool then
                                for i = 1, #pool do
                                    local r = pool[i]
                                    if r and r.Hide then r:Hide() end
                                end
                            end
                        end
                    end
                    if DungeonsForeverDB and DungeonsForeverDB.dfMemProbe then
                        ns.MemMark("gearSkel")
                    end
                    return true
                end) end
                end
                local profEnsure = ns.EnsureProfRecipes
                local profKeys = nil
                if not wantProf and wantBis then
                    profKeys = { "enchanting", "leatherworking" }
                end
                if type(profEnsure) == "function" and (wantProf or wantBis) then
                    J.Add(function()
                        local mf = _G.DungeonsForever_MainFrame
                        if mf and mf.IsShown and mf:IsShown() then return false end
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
                            if not UD.built and type(UD.Build) == "function" then
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
        local budget = urgent and 12 or 6
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
    DungeonsForeverDB = DungeonsForeverDB or {}
    DungeonsForeverDB.memProbe = DungeonsForeverDB.memProbe or {}
    local log = DungeonsForeverDB.memProbe
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
    DungeonsForeverDB = DungeonsForeverDB or {}
    local m = DungeonsForeverDB.memMarks
    if not m then
        m = {}
        DungeonsForeverDB.memMarks = m
    end
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
        DungeonsForeverDB = DungeonsForeverDB or {}
        local arr = DungeonsForeverDB.openPerf
        if not arr then
            arr = {}
            DungeonsForeverDB.openPerf = arr
        end
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
