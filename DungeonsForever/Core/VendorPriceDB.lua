local _, ns = ...

local VDB = { revision = 0 }
ns.VendorPriceDB = VDB
local watchers = {}
local capitalMaps = { [1453]=true, [1454]=true, [1455]=true, [1456]=true, [1457]=true, [1458]=true }
local capitalAreas = { [1519]=true, [1637]=true, [1537]=true, [1638]=true, [1657]=true, [1497]=true }
local capitalNPCs = {}

function VDB.IsCapitalOffer(offer)
    if type(offer) ~= "table" or offer.summoned then return false end
    local map = offer.uiMapID or offer.mapID or offer.map
    if type(map)=="number" and map>0 then return capitalMaps[map] or false end
    if capitalMaps[map] or capitalAreas[offer.areaID or offer.area] then return true end
    local id = offer.npcID or offer.id
    if not id then return false end
    if capitalNPCs[id] ~= nil then return capitalNPCs[id] end
    local loc = ns.ProfVendors and ns.ProfVendors[id]
    local locations = ns.EnsureProfNPCLocs and ns.EnsureProfNPCLocs() or ns.ProfNPCLocs
    local found = loc and capitalMaps[loc[2]] or false
    for _, entry in ipairs(locations and locations[id] or {}) do
        if capitalMaps[entry[2]] then found = true; break end
    end
    capitalNPCs[id] = found
    return found
end

function VDB.PreferredOffers(offers, eligible)
    local cities, others = {}, {}
    for _, offer in ipairs(offers or {}) do
        if (not eligible or eligible(offer)) and VDB.IsCapitalOffer(offer) then
            cities[#cities+1] = offer
        else
            others[#others+1] = offer
        end
    end
    for _, offer in ipairs(others) do cities[#cities+1] = offer end
    return cities
end

local function Character()
    local name, realm
    if UnitFullName then name, realm = UnitFullName("player") end
    if not name and UnitName then name = UnitName("player") end
    if not realm or realm == "" then realm = GetRealmName and GetRealmName() end
    if not name or not realm then return nil end
    return name .. "-" .. realm
end
VDB.Character = Character

local function Faction(context)
    local faction = context and context.faction
    if not faction and UnitFactionGroup then faction = UnitFactionGroup("player") end
    if faction == "Alliance" then return "A" end
    if faction == "Horde" then return "H" end
    return faction
end

local function Copy(offer)
    local result = {}
    for key, value in pairs(offer) do result[key] = value end
    result.quantity = tonumber(offer.quantity or offer.bundleSize)
    result.bundleSize = result.quantity
    result.unit = result.quantity and type(offer.price) == "number" and offer.price / result.quantity or nil
    result.estimated = false
    if result.npcID then
        if not result.npcName and ns.ProfVendorNames then result.npcName = ns.ProfVendorNames[result.npcID] end
        result.url = result.url or "https://www.wowhead.com/forever/npc=" .. result.npcID
    end
    return result
end

local function Notify()
    VDB.revision = VDB.revision + 1
    local route = ns.ProfRouteAuto
    if route and route.Invalidate then pcall(route.Invalidate) end
    for fn in pairs(watchers) do pcall(fn, VDB.revision) end
end

function VDB.OnChanged(fn)
    if type(fn) ~= "function" then return end
    watchers[fn] = true
    return function() watchers[fn] = nil end
end

local function RequirementsMet(offer, context)
    if context and context.npcAccess and context.npcAccess[offer.npcID] == false then return false end
    if offer.summoned and not (context and context.npcAccess and context.npcAccess[offer.npcID] == true) then
        return false
    end
    if offer.npcFactionID then
        local standing = context and context.reputations and context.reputations[offer.npcFactionID]
        local atWar
        if standing == nil and C_Reputation and C_Reputation.GetFactionDataByID then
            local data = C_Reputation.GetFactionDataByID(offer.npcFactionID)
            standing, atWar = data and data.reaction, data and data.atWarWith
        elseif standing == nil and GetFactionInfoByID then
            local _, _, reaction, _, _, _, war = GetFactionInfoByID(offer.npcFactionID)
            standing, atWar = reaction, war
        end
        if atWar or standing and standing < 4 then return false end
    end
    local req = offer.requirements
    if not req then return true end
    if context and type(context.requirementsMet) == "function" then
        local ok, met = pcall(context.requirementsMet, req, offer)
        return ok and met == true
    end
    if req.level then
        local level = context and context.level
        if not level and UnitLevel then level = UnitLevel("player") end
        if not level or level < req.level then return false end
    end
    if req.questID then
        local complete
        if context and context.quests then complete = context.quests[req.questID] end
        if complete == nil and C_QuestLog and C_QuestLog.IsQuestFlaggedCompleted then
            complete = C_QuestLog.IsQuestFlaggedCompleted(req.questID)
        end
        if complete == nil and IsQuestFlaggedCompleted then complete = IsQuestFlaggedCompleted(req.questID) end
        if not complete then return false end
    end
    if req.reputationFactionID then
        local standing = context and context.reputations and context.reputations[req.reputationFactionID]
        if standing == nil and C_Reputation and C_Reputation.GetFactionDataByID then
            local data = C_Reputation.GetFactionDataByID(req.reputationFactionID)
            standing = data and data.reaction
        end
        if standing == nil and GetFactionInfoByID then
            local _, _, reaction = GetFactionInfoByID(req.reputationFactionID)
            standing = reaction
        end
        if not standing or standing < (req.minimumStanding or 4) then return false end
    end
    if req.profession then
        local skill = context and context.professions and context.professions[req.profession]
        if type(skill) == "table" then skill = skill.cur or skill.skill end
        if not skill or skill < (req.skill or 1) then return false end
    end
    if req.unknown or req.event or req.currency or req.condition then return false end
    return true
end

local function Accessible(offer, context)
    if type(offer) ~= "table" or offer.unlimited ~= true or offer.available == false
        or offer.purchasable == false or offer.priceOnly == true
        or offer.hasExtendedCost or offer.currencyID and offer.currencyID ~= 0
        or type(offer.price) ~= "number" or not (offer.price >= 0 and offer.price < math.huge)
        or not offer.verifiedAt or not offer.source then return false end
    local quantity = tonumber(offer.quantity or offer.bundleSize)
    if not quantity or quantity < 1 or quantity >= math.huge or quantity ~= math.floor(quantity) then return false end
    local faction = offer.faction
    if faction and faction ~= "N" and faction ~= "Neutral" and faction ~= "AH" and faction ~= "Both"
        and faction ~= Faction(context) then return false end
    return RequirementsMet(offer, context)
end

function VDB.GetOffers(itemID, context)
    if type(itemID) ~= "number" then return {} end
    local api = Auctionator and Auctionator.API and Auctionator.API.v1
    local quote = api and api.GetVendorPriceByItemID
    if type(quote) == "function" then
        local ok, unit = pcall(quote, "DungeonsForever", itemID)
        if ok and type(unit) == "number" and unit >= 0 and unit < math.huge then
            return {{price=unit, unit=unit, quantity=1, bundleSize=1,
                unlimited=true, available=true, purchasable=true,
                source="auctionator-vendor", priceSource="auctionator-vendor", priceBasis="cached-unit"}}
        end
    end
    context = context or {}
    if ns.ProfSupply then ns.ProfSupply.Ensure() end
    local result = {}
    for _, offer in ipairs(ns.ProfVendorOffers and ns.ProfVendorOffers[itemID] or {}) do
        if offer.reference == true and offer.priceVerified == true and offer.source == "supply-verified"
            and type(offer.npcID) == "number" and offer.npcID > 0 and Accessible(offer, context) then
            result[#result + 1] = Copy(offer)
        end
    end
    table.sort(result, function(a, b)
        if a.unit ~= b.unit then return a.unit < b.unit end
        local ac, bc = VDB.IsCapitalOffer(a), VDB.IsCapitalOffer(b)
        if ac ~= bc then return ac end
        if a.quantity ~= b.quantity then return a.quantity < b.quantity end
        return a.npcID < b.npcID
    end)
    return result
end

function VDB.GetSuppliers(itemID, context)
    local suppliers = {}
    for _, offer in ipairs(VDB.GetOffers(itemID, context)) do
        if offer.npcID then suppliers[#suppliers + 1] = offer end
    end
    return suppliers
end

function VDB.GetPrice(itemID, context)
    local offers = VDB.GetOffers(itemID, context)
    return offers[1] and offers[1].unit or nil
end

function VDB.GetFormulaOffers(itemID, context, source)
    if type(itemID) ~= "number" then return {} end
    context = context or {}; source = source or {}
    local result, seen = {}, {}
    local function add(raw, verified)
        if type(raw) ~= "table" or type(raw.npcID) ~= "number" or raw.npcID <= 0 or raw.priceOnly then return end
        local o = {}; for k,v in pairs(raw) do o[k] = v end
        local check = {}; for k,v in pairs(o) do check[k] = v end
        check.price, check.quantity = 0, 1
        check.unlimited, check.available, check.purchasable = true, true, true
        if not Accessible(check, context) then return end
        local pack = tonumber(raw.quantity or raw.bundleSize)
        local validPack = pack and pack >= 1 and pack < math.huge and pack == math.floor(pack)
        local price = raw.price
        local priced = verified and validPack and type(price) == "number" and price >= 0 and price < math.huge
        o.price = priced and price or nil
        o.quantity = validPack and pack or nil; o.bundleSize = o.quantity
        o.unit = priced and price / pack or nil
        o.stock = nil
        local stock = raw.maxStock
        o.limited = (type(stock) == "number" and stock >= 0) or raw.limited == true
            or (type(raw.limited) == "number" and raw.limited >= 0) or raw.stockStatus == "limited" or false
        if not raw.stockUnknown and raw.stockStatus ~= "unknown" and raw.unlimited == false then o.limited = true end
        o.unlimited = not o.limited and (raw.unlimited == true or stock == -1) or false
        o.stockStatus = o.unlimited and "unlimited" or o.limited and "limited" or "unknown"
        o.stockUnknown = o.stockStatus == "unknown" or nil
        o.available = raw.available ~= false and raw.purchasable ~= false and stock ~= 0
        o.priceUsable = o.available and priced and true or false
        o.priceVerified = priced and true or false
        o.reference, o.estimated = true, false
        if not o.npcName and ns.ProfVendorNames then o.npcName = ns.ProfVendorNames[o.npcID] end
        o.url = o.url or "https://www.wowhead.com/forever/npc=" .. o.npcID
        result[#result + 1] = o; seen[o.npcID] = true
    end
    local supply = ns.ProfSupply
    for _, offer in ipairs(supply and supply.FormulaList and supply.FormulaList(itemID) or {}) do
        add(offer, offer.priceVerified == true and offer.reference == true)
    end
    for _, v in ipairs(source.vendors or {}) do
        local id = v.id or v.npcID or v[5]
        local currency = tonumber(v.currencyID or v.cur) or 0
        if type(id) == "number" and id > 0 and not seen[id] and currency == 0 and not v.hasExtendedCost then
            local o = {}; for k,value in pairs(v) do o[k] = value end
            o.npcID, o.npcName, o.zone = id, v.name or v[1], v.zone or v[2]
            o.source, o.reference = "catalogue", true
            o.verifiedAt = v.verifiedAt or "catalogue-unpriced"
            add(o, v.priceVerified == true and v.verifiedAt ~= nil)
        end
    end
    table.sort(result, function(a,b)
        local ap,bp = a.unit or math.huge, b.unit or math.huge
        if ap ~= bp then return ap < bp end
        return a.npcID < b.npcID
    end)
    return result
end

if CreateFrame then
    local frame = CreateFrame("Frame")
    frame:RegisterEvent("UPDATE_FACTION")
    frame:SetScript("OnEvent", Notify)
end
