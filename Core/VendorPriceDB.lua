-- Supplier catalogues retain locations and availability, without purchase prices.
-- Quotation interfaces stay unpriced until the purchase-price design is replaced.
-- Opening a merchant never reads, records or changes a purchase quotation.
local _, ns = ...
local VDB = {}
ns.VendorPriceDB = VDB

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
    return result
end

local function RequirementsMet(offer, context)
    local access = context and context.npcAccess
    if access and access[offer.npcID] == false then return false end
    if offer.summoned and not (access and access[offer.npcID] == true) then return false end
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
        local complete = context and context.quests and context.quests[req.questID]
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
    return not (req.unknown or req.event or req.currency or req.condition)
end

local function HasAccess(offer, context)
    if type(offer) ~= "table" or offer.hasExtendedCost
        or offer.currencyID and offer.currencyID ~= 0 then return false end
    local faction = offer.faction
    if faction and faction ~= "N" and faction ~= "Neutral" and faction ~= "AH" and faction ~= "Both"
        and faction ~= Faction(context) then return false end
    return RequirementsMet(offer, context)
end

local function Bundle(offer)
    local quantity = tonumber(offer.quantity or offer.bundleSize)
    if not quantity or quantity < 1 or quantity ~= math.floor(quantity) or quantity == math.huge then return end
    return quantity
end

local function AuditedPrice(offer)
    local price = offer.price
    return offer.reference == true and offer.priceVerified == true and offer.verifiedAt and offer.source
        and type(price) == "number" and price >= 0 and price < math.huge and Bundle(offer)
end

local function SortQuotes(result)
    table.sort(result, function(a, b)
        local ap, bp = a.unit or math.huge, b.unit or math.huge
        if ap ~= bp then return ap < bp end
        if a.quantity ~= b.quantity then return (a.quantity or 1) < (b.quantity or 1) end
        return (a.npcID or 0) < (b.npcID or 0)
    end)
    return result
end

-- One row prices an indivisible bundle, in copper. Only audited permanent
-- shelves are usable reagent sources; base item prices do not prove stock.
function VDB.GetOffers(itemID, context)
    local result = {}
    for _, offer in ipairs(ns.ProfVendorOffers and ns.ProfVendorOffers[itemID] or {}) do
        if offer.unlimited == true and offer.available ~= false and offer.purchasable ~= false
            and AuditedPrice(offer) and HasAccess(offer, context) then
            local quote = Copy(offer)
            quote.quantity = Bundle(offer)
            quote.bundleSize = quote.quantity
            quote.unit = quote.price / quote.quantity
            quote.estimated = quote.estimated == true
            result[#result + 1] = quote
        end
    end
    return SortQuotes(result)
end

-- An audited supplier can be known while its purchase price remains unknown.
function VDB.GetSuppliers(itemID, context)
    local result, seen = {}, {}
    for _, offer in ipairs(ns.ProfVendorOffers and ns.ProfVendorOffers[itemID] or {}) do
        if offer.unlimited == true and offer.available ~= false and offer.purchasable ~= false
            and offer.source and offer.verifiedAt and HasAccess(offer, context)
            and not seen[offer.npcID or offer] then
            result[#result + 1] = Copy(offer)
            seen[offer.npcID or offer] = true
        end
    end
    return result
end

function VDB.GetPrice(itemID, context)
    local offers = VDB.GetOffers(itemID, context)
    return offers[1] and offers[1].unit or nil
end

-- Limited formula shelves may price learning costs without becoming unlimited
-- reagent sources. A refresh cap is not a reading of current merchant stock.
function VDB.GetFormulaOffers(itemID, context, source)
    local result, seen = {}, {}
    local function add(raw, catalogue)
        if not HasAccess(raw, context) then return end
        local offer = Copy(raw)
        local priced = AuditedPrice(raw)
        offer.price = priced and raw.price or nil
        offer.quantity = Bundle(raw) or 1
        offer.bundleSize = offer.quantity
        offer.unit = priced and offer.price / offer.quantity or nil
        offer.stock = nil
        offer.limited = raw.unlimited == false or raw.limited == true or nil
        offer.stockStatus = raw.unlimited == true and "unlimited" or offer.limited and "limited" or "unknown"
        offer.stockUnknown = offer.stockStatus == "unknown" or nil
        offer.available = raw.available ~= false and raw.purchasable ~= false
        offer.priceUsable = offer.available and not not priced
        if catalogue and not priced then offer.source = "catalogue" end
        result[#result + 1] = offer
        if offer.npcID then seen[offer.npcID] = true end
    end
    for _, offer in ipairs(ns.ProfFormulaOffers and ns.ProfFormulaOffers[itemID] or {}) do
        add(offer, true)
    end
    for _, vendor in ipairs(source and source.vendors or {}) do
        local id = vendor.id or vendor.npcID or vendor[5]
        if not id or not seen[id] then
            local offer = Copy(vendor)
            offer.npcID = id
            offer.npcName = vendor.name or vendor[1]
            offer.name = offer.npcName
            offer.zone = vendor.zone or vendor[2]
            offer.quantity = vendor.quantity or vendor.bundleSize or 1
            offer.reference = true
            offer.source = vendor.source or "catalogue"
            add(offer, true)
        end
    end
    return SortQuotes(result)
end

-- Reputation affects access to suppliers; it never changes bundled prices.
if CreateFrame then
    local frame = CreateFrame("Frame")
    frame:RegisterEvent("UPDATE_FACTION")
    frame:SetScript("OnEvent", function(_, event)
        if event == "UPDATE_FACTION" and ns.ProfRouteAuto and ns.ProfRouteAuto.Invalidate then
            ns.ProfRouteAuto.Invalidate()
        end
    end)
end
