local _, ns = ...
if type(ns) ~= "table" then ns = _G.DF_NS or {} end
local gns = _G.DF_NS

local G = { DataSchema = 2 }
ns.ProfGatheringRoutes = G
if type(gns) == "table" and gns ~= ns then
    gns.ProfGatheringRoutes = G
end

local allowed = { mining = true, herbalism = true, skinning = true, fishing = true }

local function getDS()
    return ns.ProfDataStore or (type(gns) == "table" and gns.ProfDataStore) or nil
end

local function getAPI()
    return ns.ProfAPI or (type(gns) == "table" and gns.ProfAPI) or nil
end

local function getRanks()
    return ns.ProfRanks or (type(gns) == "table" and gns.ProfRanks) or nil
end

local function getSolverCfg()
    return ns.SolverConfig or (type(gns) == "table" and gns.SolverConfig) or nil
end

local function text(key)
    local L = ns.L or (type(gns) == "table" and gns.L)
    if type(L) == "table" and L[key] ~= nil then return L[key] end
    return key
end

local function actualCap(slug, opts)
    local cap = tonumber(opts and opts.maxSkill)
    if cap and cap > 0 then return cap end
    local ranks = getRanks()
    local state = ranks and type(ranks.Status) == "function" and ranks.Status(slug) or nil
    if state and state.known and type(state.maxSkill) == "number" and state.maxSkill > 0 then
        return state.maxSkill
    end
    local api = getAPI()
    local professions = api and type(api.ProfLearned) == "function" and api.ProfLearned() or nil
    cap = professions and professions[slug] and tonumber(professions[slug].max)
    return cap and cap > 0 and cap or nil
end

local function copyList(raw)
    local out = {}
    if type(raw) ~= "table" then return out end
    for i = 1, #raw do
        out[i] = raw[i]
    end
    return out
end

local function copyLocations(raw)
    local out = {}
    if type(raw) ~= "table" then return out end
    for i = 1, #raw do
        local loc = raw[i]
        if type(loc) == "table" then
            local cp = {}
            for k, v in pairs(loc) do cp[k] = v end
            out[#out + 1] = cp
        else
            out[#out + 1] = loc
        end
    end
    return out
end

local function zoneNames(locations)
    local names, seen = {}, {}
    local DS = getDS()
    for _, area in ipairs(locations or {}) do
        local id = type(area) == "table" and (area.areaID or area.zoneID or area[1]) or (type(area) == "number" and area or nil)
        if type(id) == "number" and not seen[id] then
            seen[id] = true
            local nm = DS and type(DS.ZoneName) == "function" and DS.ZoneName(id) or ("#" .. tostring(id))
            names[#names + 1] = nm
        elseif not id and type(area) == "table" and type(area.name) == "string" and not seen[area.name] then
            seen[area.name] = true
            names[#names + 1] = area.name
        end
    end
    return table.concat(names, " / ")
end

function G.HasRoute(slug)
    if not allowed[slug] then return false end
    local DS = getDS()
    if not DS then return false end
    if slug == "fishing" then
        local fg = type(DS.FishingGuide) == "function" and DS.FishingGuide() or nil
        return type(fg) == "table" and type(fg.fishingSteps) == "table" and #fg.fishingSteps > 0
    end
    local gg = type(DS.GatheringGuide) == "function" and DS.GatheringGuide(slug) or nil
    return type(gg) == "table" and type(gg.bands) == "table" and #gg.bands > 0
end

function G.Steps(slug, target, opts)
    if not G.HasRoute(slug) then return nil end
    opts = opts or {}
    if slug == "mining" and opts.mode == "smelt" then return nil end

    local DS = getDS()
    local cap = actualCap(slug, opts)
    local cfg = getSolverCfg()
    local defTarget = (type(cfg) == "table" and type(cfg.DEFAULT_TARGET) == "number" and cfg.DEFAULT_TARGET) or 300
    target = tonumber(target) or defTarget

    local out = {}
    local function add(lo, hi, rawLocations, rawItems, band)
        if type(lo) ~= "number" then return end
        if cap then hi = hi and math.min(hi, cap) or cap end
        if hi then hi = math.min(hi, target) end
        if not hi or hi <= lo then return end
        local locations = copyLocations(rawLocations)
        local items = copyList(rawItems)
        local name = slug == "mining" and text("实地采矿")
            or slug == "skinning" and text("实地剥皮")
            or slug == "fishing" and text("钓鱼练习")
            or text("实地采集")
        out[#out + 1] = {
            lo,
            hi,
            0,
            0,
            kind = "gather",
            profession = slug,
            reference = true,
            navigationOnly = true,
            checkpoint = true,
            name = text("参考") .. " · " .. name,
            locations = locations,
            gatheredItems = items,
            mobLevelMin = type(band) == "table" and band.mobLevelMin or nil,
            mobLevelMax = type(band) == "table" and band.mobLevelMax or nil,
            detail = zoneNames(locations) .. "\n" .. text("参考采集导航；门槛不代表技能提升范围。"),
        }
    end

    if slug == "fishing" then
        local fg = DS.FishingGuide()
        for _, stage in ipairs((type(fg) == "table" and fg.fishingSteps) or {}) do
            if type(stage.from) == "number" and type(stage.to) == "number" then
                add(stage.from, stage.to, stage.areas or {}, stage.fishIDs)
            end
        end
        return #out > 0 and out or nil
    end

    local gg = DS.GatheringGuide(slug)
    local bands = type(gg) == "table" and gg.bands or nil
    if type(bands) ~= "table" then return nil end
    for i = 1, #bands do
        local band = bands[i]
        if type(band) == "table" and type(band.minSkill) == "number" then
            local lo = band.minSkill
            local hi = type(band.maxSkill) == "number" and band.maxSkill or nil
            if hi == nil and type(bands[i + 1]) == "table" and type(bands[i + 1].minSkill) == "number" and bands[i + 1].minSkill > lo then
                hi = bands[i + 1].minSkill
            end
            add(lo, hi, band.zones or band.areas or {}, band.itemIDs, band)
        end
    end
    return #out > 0 and out or nil
end
