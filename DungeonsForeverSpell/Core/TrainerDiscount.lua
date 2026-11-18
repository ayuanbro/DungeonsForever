local ns = _G.DF_NS or {}

if not ns.IsTitan then return end

local TD = {}
ns.TrainerDiscount = TD

local L = ns.L or function(k) return k end

local CITY_FACTION = {
    [1519] = 72,
    [1537] = 47,
    [1657] = 69,
    [1637] = 76,
    [1638] = 81,
    [1497] = 68,
}

local RATE = {
    [5] = 0.05,
    [6] = 0.10,
    [7] = 0.15,
    [8] = 0.20,
}

local function Pct(rate)
    if not rate or rate <= 0 then return 0 end
    return math.floor(rate * 100 + 0.5)
end

local function StandingLabel(reaction)
    if type(reaction) ~= "number" then return "" end
    local s = _G["FACTION_STANDING_LABEL" .. reaction]
    if type(s) == "string" and s ~= "" then return s end
    return ""
end

local function Standing(fid)
    if type(fid) ~= "number" then return nil end
    if type(C_Reputation) == "table" and type(C_Reputation.GetFactionDataByID) == "function" then
        local ok, d = pcall(C_Reputation.GetFactionDataByID, fid)
        if ok and type(d) == "table" then return d.reaction, d.currentStanding, d.name end
    end
    if type(GetFactionInfoByID) == "function" then
        local ok, name, _, reaction, _, _, value = pcall(GetFactionInfoByID, fid)
        if ok then return reaction, value, name end
    end
    return nil
end

local function AreaName(area)
    if type(C_Map) == "table" and type(C_Map.GetAreaInfo) == "function" then
        local ok, name = pcall(C_Map.GetAreaInfo, area)
        if ok and type(name) == "string" and name ~= "" then return name end
    end
    return nil
end

local function CurArea()
    local data = ns.ClassTrainerData
    if not (data and data.zones) then return nil end
    if type(C_Map) ~= "table" or type(C_Map.GetBestMapForUnit) ~= "function" then return nil end
    local ok, cur = pcall(C_Map.GetBestMapForUnit, "player")
    if not (ok and cur) then return nil end
    for zid, ui in pairs(data.zones) do
        if ui == cur then return zid end
    end
    if type(C_Map.GetMapInfo) == "function" then
        local okp, mi = pcall(C_Map.GetMapInfo, cur)
        if okp and mi and mi.parentMapID then
            for zid, ui in pairs(data.zones) do
                if ui == mi.parentMapID then return zid end
            end
        end
    end
    return nil
end

function TD.Cities()
    local data = ns.ClassTrainerData
    if not (data and data.classes and data.zones) then return nil end
    if type(UnitClass) ~= "function" or type(UnitFactionGroup) ~= "function" then return nil end
    local _, cls = UnitClass("player")
    local faction = UnitFactionGroup("player")
    local rows = cls and data.classes[cls]
    if not (rows and faction) then return nil end
    local seen, out = {}, {}
    for i = 1, #rows do
        local r = rows[i]
        local area = r.zoneId
        local fid = area and CITY_FACTION[area]
        if fid and not seen[area] and (r.faction == faction or r.faction == "Both") then
            seen[area] = true
            local reaction, value, facName = Standing(fid)
            out[#out + 1] = {
                area = area,
                map = data.zones[area],
                fid = fid,
                name = AreaName(area) or facName or L["未知地区"],
                reaction = reaction,
                value = value,
                rate = (reaction and RATE[reaction]) or 0,
            }
        end
    end
    if #out == 0 then return nil end
    return out
end

function TD.State()
    local cities = TD.Cities()
    if not cities then return nil end
    local area = CurArea()
    local cur, top
    for i = 1, #cities do
        local c = cities[i]
        if area and c.area == area then cur = c end
        if not top or c.rate > top.rate or (c.rate == top.rate and (c.value or 0) > (top.value or 0)) then top = c end
    end
    return { cities = cities, cur = cur, top = top, area = area }
end

local function Gain(cur, top)
    if not (cur and top) then return nil end
    if top.rate <= cur.rate then return nil end
    local pct = math.floor((1 - (1 - top.rate) / (1 - cur.rate)) * 100 + 0.5)
    if pct < 1 then pct = 1 end
    return pct
end

local function RepPiece(rate, reaction)
    local label = StandingLabel(reaction)
    if label ~= "" then return string.format(L["%d%%（%s）"], Pct(rate), label) end
    return string.format("%d%%", Pct(rate))
end

function TD.Hint()
    local s = TD.State()
    if not (s and s.cur and s.top) then return nil end
    local pct = Gain(s.cur, s.top)
    if not pct then return nil end
    local row = string.format(L["「%s」更省 %d%%"], s.top.name, pct)
    local tip = string.format(L["推荐去「%s」学：此处声望 %s，那边声望 %s，约省 %d%%"],
        s.top.name, RepPiece(s.cur.rate, s.cur.reaction), RepPiece(s.top.rate, s.top.reaction), pct)
    return row, tip
end

function TD.Header()
    local s = TD.State()
    if not (s and s.top) then return nil end
    local pct = s.cur and Gain(s.cur, s.top) or nil
    if pct then return string.format(L["「%s」更省 %d%%"], s.top.name, pct) end
    if not s.cur and s.top.rate > 0 then
        return string.format(L["「%s」声望 %d%%"], s.top.name, Pct(s.top.rate))
    end
    return nil
end

function TD.CityInfo(area)
    if type(area) ~= "number" then return nil end
    local s = TD.State()
    if not (s and s.cities) then return nil end
    for i = 1, #s.cities do
        local c = s.cities[i]
        if c.area == area then
            return {
                pct = Pct(c.rate),
                label = StandingLabel(c.reaction),
                best = (s.top ~= nil and c.area == s.top.area),
            }
        end
    end
    return nil
end
