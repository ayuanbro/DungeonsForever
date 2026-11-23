local _, ns = ...

local VDB = { revision = 0, SourceQuestSchema = 2, SourceAccessSchema = 2, SourcePurchaseSchema = 2 }
ns.VendorPriceDB = VDB
local watchers = {}
local capitalMaps = { [1453]=true, [1454]=true, [1455]=true, [1456]=true, [1457]=true, [1458]=true }
local capitalAreas = { [1519]=true, [1637]=true, [1537]=true, [1638]=true, [1657]=true, [1497]=true }
local capitalNPCs = {}

local function getProfAPI()
    if type(ns.EnsureProfAPI) == "function" then return ns.EnsureProfAPI() end
    return type(ns.ProfAPI) == "table" and ns.ProfAPI or nil
end

local function getDS()
    local ds = ns.ProfDataStore or (_G.DF_NS and _G.DF_NS.ProfDataStore) or nil
    if type(ds) == "table" then return ds end
    getProfAPI()
    return ns.ProfDataStore or (_G.DF_NS and _G.DF_NS.ProfDataStore) or nil
end

local function getCond()
    return ns.ProfConditions or (_G.DF_NS and _G.DF_NS.ProfConditions) or nil
end

local function npcNameOf(npcID)
    if type(npcID) ~= "number" then return nil end
    local ds = getDS()
    return ds and type(ds.RawText) == "function" and ds.RawText("npc", npcID) or nil
end

function VDB.IsCapitalOffer(offer)
    if type(offer) ~= "table" or offer.summoned then return false end
    local map = offer.uiMapID or offer.mapID or offer.map
    if type(map) == "number" and map > 0 then return capitalMaps[map] or false end
    if capitalMaps[map] or capitalAreas[offer.areaID or offer.area] then return true end
    local id = offer.npcID or offer.id
    if type(id) ~= "number" then return false end
    if capitalNPCs[id] ~= nil then return capitalNPCs[id] end
    local ds = getDS()
    local npc = ds and type(ds.Npc) == "function" and ds.Npc(id) or nil
    local found = false
    if type(npc) == "table" then
        if capitalAreas[npc.zoneID] then found = true end
        if not found and type(npc.spawns) == "table" then
            for _, sp in ipairs(npc.spawns) do
                if type(sp) == "table" and (capitalMaps[sp.uiMapID] or capitalAreas[sp.zoneID]) then
                    found = true
                    break
                end
            end
        end
    end
    capitalNPCs[id] = found
    return found
end

function VDB.PreferredOffers(offers, eligible)
    local cities, others = {}, {}
    for _, offer in ipairs(offers or {}) do
        if (not eligible or eligible(offer)) and VDB.IsCapitalOffer(offer) then
            cities[#cities + 1] = offer
        else
            others[#others + 1] = offer
        end
    end
    for _, offer in ipairs(others) do cities[#cities + 1] = offer end
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
        if not result.npcName then result.npcName = npcNameOf(result.npcID) end
        result.url = result.url or "https://www.wowhead.com/forever/npc=" .. result.npcID
    end
    return result
end

local function Notify()
    VDB.revision = VDB.revision + 1
    local api = ns.ProfAPI
    if type(api) == "table" and type(api.InvalidatePricing) == "function" then
        pcall(api.InvalidatePricing)
    end
    local route = ns.ProfRouteAuto
    if route and route.Invalidate then pcall(route.Invalidate) end
    for fn in pairs(watchers) do pcall(fn, VDB.revision) end
end

function VDB.OnChanged(fn)
    if type(fn) ~= "function" then return end
    watchers[fn] = true
    return function() watchers[fn] = nil end
end

local function collectNpcConditions(kind, npcID, targetID, extraConditions)
    local list = {}
    local function pushAll(conds)
        if type(conds) ~= "table" then return end
        for i = 1, #conds do
            local c = conds[i]
            if type(c) == "table" then list[#list + 1] = c end
        end
    end
    local ds = getDS()
    if ds and type(npcID) == "number" then
        local npc = type(ds.Npc) == "function" and ds.Npc(npcID) or nil
        if type(npc) == "table" then pushAll(npc.accessConditions) end
        if kind == "trainer" and type(targetID) == "number" and targetID > 0 and type(ds.LearningRoutes) == "function" then
            local lr = ds.LearningRoutes(targetID)
            if type(lr) == "table" and type(lr.routes) == "table" then
                for _, rt in ipairs(lr.routes) do
                    if type(rt) == "table" and rt.kind == "trainer" then
                        pushAll(rt.conditions)
                        for _, tr in ipairs(rt.trainers or {}) do
                            if type(tr) == "table" and tr.npcID == npcID then
                                pushAll(tr.conditions)
                            end
                        end
                    end
                end
            end
        elseif kind == "vendor" and type(targetID) == "number" and targetID > 0 and type(ds.VendorOffers) == "function" then
            local vo = ds.VendorOffers(targetID)
            if type(vo) == "table" and type(vo.offers) == "table" then
                for _, off in ipairs(vo.offers) do
                    if type(off) == "table" and off.npcID == npcID then
                        pushAll(off.conditions)
                    end
                end
            end
        end
    end
    pushAll(extraConditions)
    return list
end

local function evaluateConditionList(conds, context)
    if type(conds) ~= "table" or #conds == 0 then return true end
    local Cond = getCond()
    if Cond and type(Cond.EvaluateAll) == "function" then
        return Cond.EvaluateAll(conds, context)
    end
    local unknown = false
    for _, c in ipairs(conds) do
        if c.kind == "questGroup" then
            local r = VDB.QuestGroupsState(c.groups, context)
            if r == false then return false end
            if r == nil then unknown = true end
        elseif c.kind == "hasItem" or c.kind == "sourceItem" then
            local r = VDB.SourceItemState(c.itemID or c.value, context)
            if r == false then return false end
            if r == nil then unknown = true end
        elseif c.kind == "unknown" or c.kind == "sourceCondition" then
            return nil
        end
    end
    if unknown then return nil end
    return true
end

function VDB.QuestGroupsState(groups, context)
    if type(groups) ~= "table" or #groups == 0 then return nil end
    local anyUnknown = false
    for _, group in ipairs(groups) do
        if type(group) ~= "table" or #group == 0 then return nil end
        local failed, unknown = false, false
        for _, id in ipairs(group) do
            local done
            if type(id) ~= "number" or id <= 0 then return nil end
            if context and (context.completedQuests ~= nil or context.quests ~= nil or context.learningSourcesRequired) then
                local quests = context.completedQuests or context.quests
                done = quests and quests[id]
            elseif C_QuestLog and type(C_QuestLog.IsQuestFlaggedCompleted) == "function" then
                local ok, value = pcall(C_QuestLog.IsQuestFlaggedCompleted, id)
                if ok then done = value end
            elseif type(IsQuestFlaggedCompleted) == "function" then
                local ok, value = pcall(IsQuestFlaggedCompleted, id)
                if ok then done = value end
            end
            if done == false then failed = true elseif done ~= true then unknown = true end
        end
        if not failed and not unknown then return true end
        if not failed and unknown then anyUnknown = true end
    end
    if anyUnknown then return nil end
    return false
end

function VDB.SourceQuestState(kind, npcID, targetID, context, conditions)
    local all = collectNpcConditions(kind, npcID, targetID, conditions)
    local qOnly = {}
    for i = 1, #all do
        if all[i].kind == "questGroup" or all[i].kind == "quest" then
            qOnly[#qOnly + 1] = all[i]
        end
    end
    return evaluateConditionList(qOnly, context)
end

function VDB.ItemHasQuestSources(itemID)
    if type(itemID) ~= "number" then return false end
    local ds = getDS()
    if not ds or type(ds.VendorOffers) ~= "function" then return false end
    local vo = ds.VendorOffers(itemID)
    if type(vo) ~= "table" or type(vo.offers) ~= "table" then return false end
    for _, offer in ipairs(vo.offers) do
        if type(offer) == "table" then
            if type(offer.conditions) == "table" and #offer.conditions > 0 then return true end
            local npc = type(offer.npcID) == "number" and ds.Npc and ds.Npc(offer.npcID) or nil
            if type(npc) == "table" and type(npc.accessConditions) == "table" and #npc.accessConditions > 0 then
                return true
            end
        end
    end
    return false
end

function VDB.SourceItemCount(itemID, context)
    if context and (context.ownedSourceItems ~= nil or context.ownedItems ~= nil or context.completedQuests ~= nil or context.learningSourcesRequired) then
        local map = context.ownedSourceItems or context.ownedItems
        return map and map[itemID]
    end
    local get = C_Item and C_Item.GetItemCount or GetItemCount
    if type(get) == "function" then
        local ok, count = pcall(get, itemID, false)
        if ok and type(count) == "number" then return count end
    end
end

function VDB.SourceItemState(itemID, context)
    local count = VDB.SourceItemCount(itemID, context)
    if type(count) ~= "number" then return nil end
    return count >= 1
end

function VDB.SourceAccessState(kind, npcID, targetID, context, conditions)
    local all = collectNpcConditions(kind, npcID, targetID, conditions)
    return evaluateConditionList(all, context)
end

function VDB.SourceRequiresQuest(kind, npcID, targetID)
    local all = collectNpcConditions(kind, npcID, targetID, nil)
    for i = 1, #all do
        if all[i].kind == "questGroup" or all[i].kind == "quest" then
            return true
        end
    end
    return false
end

local function RequirementsMet(offer, context)
    if VDB.SourceAccessState("vendor", offer.npcID, offer.itemID, context, offer.conditions) ~= true then return false end
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
VDB.OfferAccessible = Accessible

function VDB.GetCachedOffer(itemID)
    if type(itemID) ~= "number" then return end
    local api = Auctionator and Auctionator.API and Auctionator.API.v1
    local quote = api and api.GetVendorPriceByItemID
    if type(quote) == "function" and not VDB.ItemHasQuestSources(itemID) then
        local ok, unit = pcall(quote, "DungeonsForever", itemID)
        if ok and type(unit) == "number" and unit >= 0 and unit < math.huge then
            return {
                price = unit, unit = unit, quantity = 1, bundleSize = 1,
                unlimited = true, available = true, purchasable = true,
                source = "auctionator-vendor", priceSource = "auctionator-vendor", priceBasis = "cached-unit",
            }
        end
    end
end

function VDB.GetOffers(itemID, context)
    if type(itemID) ~= "number" then return {} end
    local cached = VDB.GetCachedOffer(itemID)
    if cached then return { cached } end
    local api = getProfAPI()
    if not api then return {} end
    if ns.ProfSupply and ns.ProfSupply.Ensure then ns.ProfSupply.Ensure() end
    local result = {}
    for _, offer in ipairs(ns.ProfVendorOffers and ns.ProfVendorOffers[itemID] or {}) do
        offer = Copy(offer)
        offer.itemID = itemID
        if offer.reference == true and offer.priceVerified == true and offer.source == "supply-verified"
            and type(offer.npcID) == "number" and offer.npcID > 0 and Accessible(offer, context) then
            result[#result + 1] = offer
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
    if offers[1] and offers[1].unit ~= nil then return offers[1].unit end
    local api = getProfAPI()
    if api and type(api.VendorPrice) == "function" then
        local vp = api.VendorPrice(itemID, context)
        if type(vp) == "table" and type(vp.unitCopper) == "number" then
            local pure = (type(vp.currencies) ~= "table" or #vp.currencies == 0)
                and (type(vp.costItems) ~= "table" or #vp.costItems == 0)
            if pure then return vp.unitCopper end
        end
    end
    return nil
end

function VDB.GetFormulaOffers(itemID, context, source)
    if type(itemID) ~= "number" then return {} end
    source = source or {}
    local result, seen = {}, {}
    local function add(raw, verified)
        if type(raw) ~= "table" or type(raw.npcID) ~= "number" or raw.npcID <= 0 or raw.priceOnly then return end
        local o = {}
        for k, v in pairs(raw) do o[k] = v end
        o.itemID = itemID
        local check = {}
        for k, v in pairs(o) do check[k] = v end
        check.price, check.quantity = 0, 1
        check.unlimited, check.available, check.purchasable = true, true, true
        if not Accessible(check, context) then return end
        local pack = tonumber(raw.quantity or raw.bundleSize)
        local validPack = pack and pack >= 1 and pack < math.huge and pack == math.floor(pack)
        local price = raw.price
        local priced = verified and validPack and type(price) == "number" and price >= 0 and price < math.huge
        o.price = priced and price or nil
        o.quantity = validPack and pack or nil
        o.bundleSize = o.quantity
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
        if not o.npcName then o.npcName = npcNameOf(o.npcID) end
        o.url = o.url or "https://www.wowhead.com/forever/npc=" .. o.npcID
        result[#result + 1] = o
        seen[o.npcID] = true
    end
    local api = getProfAPI()
    local supply = api and ns.ProfSupply or nil
    for _, offer in ipairs(supply and supply.FormulaList and supply.FormulaList(itemID) or {}) do
        add(offer, offer.priceVerified == true and offer.reference == true)
    end
    for _, v in ipairs(source.vendors or {}) do
        local id = v.id or v.npcID or v[5]
        local currency = tonumber(v.currencyID or v.cur) or 0
        if type(id) == "number" and id > 0 and not seen[id] and currency == 0 and not v.hasExtendedCost then
            local o = {}
            for k, value in pairs(v) do o[k] = value end
            o.npcID, o.npcName, o.zone = id, v.name or v[1], v.zone or v[2]
            o.source, o.reference = "catalogue", true
            o.verifiedAt = v.verifiedAt or "catalogue-unpriced"
            add(o, v.priceVerified == true and v.verifiedAt ~= nil)
        end
    end
    table.sort(result, function(a, b)
        local ap, bp = a.unit or math.huge, b.unit or math.huge
        if ap ~= bp then return ap < bp end
        return a.npcID < b.npcID
    end)
    return result
end

local questStamp
local function QuestChanged()
    local ds = ns.ProfDataStore
    if type(ds) ~= "table" or type(ds.Ensure) ~= "function" then return false end
    local ids, items = {}, {}
    local function scanConds(conds)
        if type(conds) ~= "table" then return end
        for _, c in ipairs(conds) do
            if type(c) == "table" then
                if c.kind == "quest" and type(c.questID) == "number" then
                    ids[c.questID] = true
                elseif c.kind == "questGroup" and type(c.groups) == "table" then
                    for _, g in ipairs(c.groups) do
                        for _, qid in ipairs(g or {}) do
                            if type(qid) == "number" then ids[qid] = true end
                        end
                    end
                elseif (c.kind == "hasItem" or c.kind == "sourceItem") and type(c.itemID or c.value) == "number" then
                    items[c.itemID or c.value] = true
                end
            end
        end
    end
    local ent = ds.Ensure("entities")
    if type(ent) == "table" and type(ent.npcs) == "table" then
        for _, npc in pairs(ent.npcs) do
            if type(npc) == "table" then scanConds(npc.accessConditions) end
        end
    end
    local src = ds.Ensure("sources")
    if type(src) == "table" and type(src.vendorOffers) == "table" then
        for _, vo in pairs(src.vendorOffers) do
            if type(vo) == "table" and type(vo.offers) == "table" then
                for _, off in ipairs(vo.offers) do
                    if type(off) == "table" then scanConds(off.conditions) end
                end
            end
        end
    end
    local parts = {}
    local sorted = {}
    for id in pairs(ids) do sorted[#sorted + 1] = id end
    table.sort(sorted)
    for _, id in ipairs(sorted) do parts[#parts + 1] = id .. ":" .. tostring(VDB.QuestGroupsState({ { id } })) end
    sorted = {}
    for id in pairs(items) do sorted[#sorted + 1] = id end
    table.sort(sorted)
    for _, id in ipairs(sorted) do parts[#parts + 1] = "item:" .. id .. ":" .. tostring(VDB.SourceItemState(id)) end
    local stamp = table.concat(parts, ";")
    if stamp == questStamp then return false end
    questStamp = stamp
    return true
end

if CreateFrame then
    local frame = CreateFrame("Frame")
    frame:RegisterEvent("UPDATE_FACTION")
    frame:RegisterEvent("QUEST_TURNED_IN")
    frame:RegisterEvent("QUEST_LOG_UPDATE")
    frame:RegisterEvent("QUEST_ACCEPTED")
    frame:RegisterEvent("BAG_UPDATE_DELAYED")
    frame:RegisterEvent("PLAYER_EQUIPMENT_CHANGED")
    frame:RegisterEvent("MERCHANT_CLOSED")
    frame:SetScript("OnEvent", function(_, event)
        if event == "UPDATE_FACTION" or event == "MERCHANT_CLOSED" or QuestChanged() then
            local api = ns.ProfAPI
            if (event == "BAG_UPDATE_DELAYED" or event == "PLAYER_EQUIPMENT_CHANGED")
                and type(api) == "table" and type(api.RefreshLearningObservations) == "function" then
                pcall(api.RefreshLearningObservations, event)
            end
            Notify()
        end
    end)
end
