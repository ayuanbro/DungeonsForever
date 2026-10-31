local ADDON, ns = ...

local B = {}
ns.OpenMapBridge = B

local THRESH = 0.02
local pts
local covered = {}
local hooked

local L = ns.L

local function api()
    local a = _G.OpenMapAPI
    if type(a) == "table" and type(a.WorldFromMap) == "function" then return a end
end

local function buildPts()
    local a, de = api(), ns.DungeonEntry
    if not (a and type(de) == "table") then return end
    local out = {}
    for id, e in pairs(de) do
        if type(e) == "table" and type(e[1]) == "number" and e[2] and e[3] then
            local ok, u, v = pcall(a.WorldFromMap, e[1], e[2] / 100, e[3] / 100)
            if ok and type(u) == "number" and type(v) == "number" then
                out[#out + 1] = { u = u, v = v, id = id }
            end
        end
    end
    pts = out
end

function B.IdsAt(u, v)
    if type(u) ~= "number" or type(v) ~= "number" then return nil end
    if not pts then buildPts() end
    if not pts then return nil end
    local list
    local lim = THRESH * THRESH
    for i = 1, #pts do
        local p = pts[i]
        local du, dv = p.u - u, p.v - v
        if du * du + dv * dv <= lim then
            list = list or {}
            list[#list + 1] = p.id
        end
    end
    return list
end

function B.Active()
    local a = api()
    if not (a and hooked) then return false end
    local ok, st = pcall(a.IsStitched)
    return ok and st and true or false
end

function B.Refresh()
    if B.__q then return end
    B.__q = true
    C_Timer.After(0.12, function()
        B.__q = nil
        local W = ns.MapWorldModule
        local P = W and W.pinProvider
        if P and P.RefreshAllData then pcall(P.RefreshAllData, P) end
    end)
end

function B.Keep(rows)
    if type(rows) ~= "table" then return rows end
    if not B.Active() then return rows end
    local hit = false
    for i = 1, #rows do
        if covered[rows[i].id] then hit = true break end
    end
    if not hit then return rows end
    local keys = {}
    for i = 1, #rows do
        local r = rows[i]
        if covered[r.id] then keys[string.format("%.0f:%.0f", r.x, r.y)] = true end
    end
    local out = {}
    for i = 1, #rows do
        local r = rows[i]
        if not keys[string.format("%.0f:%.0f", r.x, r.y)] then out[#out + 1] = r end
    end
    return out
end

local function openIds(ids, anchor)
    local W = ns.MapWorldModule
    if not (W and W.OpenEntryMenu) then return end
    if type(ids) ~= "table" or #ids < 1 then return end
    W.OpenEntryMenu(ids, anchor)
end

local function wrap(pin)
    if pin.OnClick ~= pin.__dfWrap then
        local old = pin.OnClick
        local w = function(p)
            local ids = B.IdsAt(p.u, p.v)
            if ids and #ids > 0 then
                openIds(ids, p)
                return
            end
            if old then old(p) end
        end
        pin.__dfWrap = w
        pin.OnClick = w
    end
    local en = pin:GetScript("OnEnter")
    if en ~= pin.__dfEnter then
        local e = function(p)
            if en then en(p) end
            local ids = B.IdsAt(p.u, p.v)
            if ids and #ids > 0 then
                GameTooltip:AddLine(L["点击查看副本地图"], 0.55, 0.75, 0.55)
                GameTooltip:Show()
            end
        end
        pin.__dfEnter = e
        pin:SetScript("OnEnter", e)
    end
end

function B.Scan(set)
    local pins = set and set.pins
    if type(pins) ~= "table" then return end
    local fresh, changed = {}, false
    for i = 1, #pins do
        local pin = pins[i]
        if pin.instances and type(pin.u) == "number" then
            local ids = B.IdsAt(pin.u, pin.v)
            if ids then
                wrap(pin)
                for k = 1, #ids do
                    if not covered[ids[k]] then changed = true end
                    fresh[ids[k]] = true
                end
            end
        end
    end
    for id in pairs(covered) do
        if not fresh[id] then changed = true end
    end
    covered = fresh
    if changed then B.Refresh() end
end

local function attach()
    local OM = _G.OpenMap
    if type(OM) ~= "table" then return false end
    local S = OM.MapStitch
    if type(S) ~= "table" then return false end
    if S.__dfHooked then hooked = true return true end
    S.__dfHooked = true
    hooked = true
    if type(S.BuildDungeonPins) == "function" then
        hooksecurefunc(S, "BuildDungeonPins", function(set) B.Scan(set) end)
    end
    if type(S.GetPinSet) == "function" then
        local ok, set = pcall(S.GetPinSet, S, "dungeons")
        if ok and set then B.Scan(set) end
    end
    return true
end

local boot = CreateFrame("Frame")
boot:RegisterEvent("ADDON_LOADED")
boot:RegisterEvent("PLAYER_LOGIN")
boot:SetScript("OnEvent", function(self, event, name)
    if event == "ADDON_LOADED" and name ~= "OpenMap" then return end
    local ok = attach()
    if ok or event == "PLAYER_LOGIN" then self:UnregisterAllEvents() end
end)
