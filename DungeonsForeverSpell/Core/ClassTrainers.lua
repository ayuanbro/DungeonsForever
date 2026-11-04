local ns = _G.DF_NS or {}

if not ns.IsTitan then return end

local CT = {}
ns.ClassTrainers = CT

local TPL_SPELL = "SPELL"
local TPL_HEADER = "HEADER"

local CLASS_ICON = {
    WARRIOR = "Interface\\Icons\\ClassIcon_Warrior",
    PALADIN = "Interface\\Icons\\ClassIcon_Paladin",
    HUNTER  = "Interface\\Icons\\ClassIcon_Hunter",
    ROGUE   = "Interface\\Icons\\ClassIcon_Rogue",
    PRIEST  = "Interface\\Icons\\ClassIcon_Priest",
    SHAMAN  = "Interface\\Icons\\ClassIcon_Shaman",
    MAGE    = "Interface\\Icons\\ClassIcon_Mage",
    WARLOCK = "Interface\\Icons\\ClassIcon_Warlock",
    DRUID   = "Interface\\Icons\\ClassIcon_Druid",
}

local function ZoneName(zoneId)
    if zoneId and C_Map and C_Map.GetAreaInfo then
        local ok, name = pcall(C_Map.GetAreaInfo, zoneId)
        if ok and name and name ~= "" then return name end
    end
    return nil
end

local function CurrentUiMap()
    if C_Map and C_Map.GetBestMapForUnit then
        local ok, id = pcall(C_Map.GetBestMapForUnit, "player")
        if ok then return id end
    end
    return nil
end

local function CurrentZoneId()
    local data = ns.ClassTrainerData
    local cur = CurrentUiMap()
    if not (data and data.zones and cur) then return nil end
    for zid, ui in pairs(data.zones) do
        if ui == cur then return zid end
    end
    if C_Map and C_Map.GetMapInfo then
        local ok, mi = pcall(C_Map.GetMapInfo, cur)
        if ok and mi and mi.parentMapID then
            for zid, ui in pairs(data.zones) do
                if ui == mi.parentMapID then return zid end
            end
        end
    end
    return nil
end

local function Collect(cls, faction)
    local data = ns.ClassTrainerData
    if not (data and data.classes) then return nil end
    local out = {}
    local function add(list, isPortal)
        if not list then return end
        for _, r in ipairs(list) do
            if r.faction == faction or r.faction == "Both" then
                out[#out + 1] = {
                    npc = r.npc,
                    name = r.name,
                    zoneId = r.zoneId,
                    x = r.x,
                    y = r.y,
                    portal = isPortal or nil,
                }
            end
        end
    end
    add(data.classes[cls], false)
    if cls == "MAGE" then add(data.classes.PORTAL, true) end
    if #out == 0 then return nil end
    return out
end

local function SortZones(zids, cur, idx)
    table.sort(zids, function(a, b)
        if a == cur and b ~= cur then return true end
        if b == cur and a ~= cur then return false end
        local ia, ib = idx[a], idx[b]
        if ia and ib then return ia < ib end
        if ia then return true end
        if ib then return false end
        return a < b
    end)
end

function CT.Groups()
    local data = ns.ClassTrainerData
    if not (data and data.classes) then return nil end
    local classLabel, cls = UnitClass("player")
    local faction = UnitFactionGroup("player")
    if not (cls and faction) then return nil end
    local list = Collect(cls, faction)
    if not list then return nil end

    local byZone, zids = {}, {}
    for _, r in ipairs(list) do
        local zid = r.zoneId or 0
        if not byZone[zid] then
            byZone[zid] = {}
            zids[#zids + 1] = zid
        end
        local bucket = byZone[zid]
        bucket[#bucket + 1] = r
    end

    local cur = CurrentZoneId()
    local idx = {}
    for i, z in ipairs(data.zoneOrder or {}) do idx[z] = i end
    SortZones(zids, cur, idx)

    local icon = CLASS_ICON[cls]
    local subClass = format(ns.L["%s训练师"], classLabel or "")
    local subPortal = ns.L["传送门训练师"]
    local unknownZone = ns.L["未知地区"]

    local groups = {}
    for _, zid in ipairs(zids) do
        local zoneName = (zid ~= 0 and ZoneName(zid)) or unknownZone
        local elements = {}
        for _, r in ipairs(byZone[zid]) do
            elements[#elements + 1] = {
                templateKey = TPL_SPELL,
                name = r.name,
                icon = icon,
                sub = (r.portal and subPortal) or subClass,
                req = format("%.1f, %.1f", r.x or 0, r.y or 0),
                trainer = {
                    npc = r.npc,
                    x = r.x,
                    y = r.y,
                    uiMapId = data.zones[zid],
                    zoneName = zoneName,
                },
            }
        end
        groups[#groups + 1] = {
            header = { templateKey = TPL_HEADER, text = zoneName },
            elements = elements,
        }
    end
    return groups
end
