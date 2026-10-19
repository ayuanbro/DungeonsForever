-- Merchant purchase offers. Legacy vendorPrices is retained for saved-variable
-- compatibility, but its unqualified unit prices never enter route calculations.
local _, ns = ...

local VDB = { revision = 0 }
ns.VendorPriceDB = VDB
local watchers = {}
local pendingScan = false
local reputationRevision = 0
local reputationKey

local function DB()
    local db = ns.DB()
    if type(db.vendorPrices) ~= "table" then db.vendorPrices = {} end
    if type(db.profVendorOffers) ~= "table" then db.profVendorOffers = {} end
    return db
end

local function Now()
    return (time and time()) or 0
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

local function ReputationKey(context)
    if context and context.reputationKey then return context.reputationKey end
    if reputationKey then return reputationKey end
    local entries = {}
    local count = C_Reputation and C_Reputation.GetNumFactions and C_Reputation.GetNumFactions()
        or GetNumFactions and GetNumFactions() or 0
    for index = 1, count do
        if C_Reputation and C_Reputation.GetFactionDataByIndex then
            local data = C_Reputation.GetFactionDataByIndex(index)
            if data and not data.isHeader then
                entries[#entries + 1] = tostring(data.factionID or data.name) .. ":"
                    .. tostring(data.reaction)
            end
        elseif GetFactionInfo then
            local name, _, standing, _, _, value, _, _, isHeader, _, _, _, _, id = GetFactionInfo(index)
            if name and not isHeader then
                entries[#entries + 1] = tostring(id or name) .. ":" .. tostring(standing)
            end
        end
    end
    table.sort(entries)
    reputationKey = table.concat(entries, ";")
    return reputationKey
end

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
    result.quantity = tonumber(offer.quantity or offer.bundleSize) or 1
    result.bundleSize = result.quantity
    result.unit = offer.price / result.quantity
    result.estimated = offer.estimated == true
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
    if offer.summoned and offer.source ~= "merchant"
        and not (context and context.npcAccess and context.npcAccess[offer.npcID] == true) then
        -- A catalogue entry alone does not establish access to a summoned NPC.
        local observed = false
        for _, records in pairs(DB().profVendorOffers) do
            for _, record in pairs(records) do
                if record.character == (context and context.character or Character())
                    and record.npcID == offer.npcID and record.source == "merchant"
                    and record.unlimited and record.available ~= false and not record.hasExtendedCost
                    and (not record.currencyID or record.currencyID == 0) then observed = true; break end
            end
            if observed then break end
        end
        if not observed then return false end
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
    -- Unknown conditions are deliberately not treated as satisfied.
    if req.unknown or req.event or req.currency or req.condition then return false end
    return true
end

local function Accessible(offer, context, character)
    if type(offer) ~= "table" or offer.unlimited ~= true or offer.available == false
        or offer.hasExtendedCost or offer.currencyID and offer.currencyID ~= 0
        or type(offer.price) ~= "number" or offer.price < 0
        or not offer.verifiedAt or not offer.source then return false end
    if context and context.requireObservedPrice and (offer.source ~= "merchant" or offer.estimated) then return false end
    local quantity = tonumber(offer.quantity or offer.bundleSize)
    if not quantity or quantity < 1 or quantity ~= math.floor(quantity) then return false end
    if offer.character and offer.character ~= character then return false end
    if offer.source == "merchant" then
        local function tierKey(key)
            local entries={}
            for part in tostring(key or ""):gmatch("[^;]+") do
                entries[#entries+1]=part:match("^(.-:[^:]+):[^:]+$") or part
            end
            return table.concat(entries,";")
        end
        if tierKey(offer.reputationKey)~=tierKey(ReputationKey(context)) then return false end
    end
    local faction = offer.faction
    if faction and faction ~= "N" and faction ~= "Neutral" and faction ~= "AH" and faction ~= "Both"
        and faction ~= Faction(context) then return false end
    return RequirementsMet(offer, context)
end

-- Each entry prices one indivisible purchase bundle, in copper. Current-character
-- merchant quotes take precedence over verified references and cached estimates.
-- A rejection (limited stock, conditions, currency) also blocks that NPC's fallback.
function VDB.GetOffers(itemID, context)
    if type(itemID) ~= "number" then return {} end
    context = context or {}
    local character = context.character or Character()
    local result, blockedNPC = {}, {}
    local records = DB().profVendorOffers[itemID]
    if type(records) == "table" then
        for _, offer in pairs(records) do
            if type(offer) == "table" and offer.character == character then
                if offer.npcID and (offer.available == false or offer.unlimited == false or offer.hasExtendedCost
                    or offer.currencyID and offer.currencyID ~= 0) then blockedNPC[offer.npcID] = true end
                if offer.source == "merchant" and not offer.estimated and Accessible(offer, context, character) then
                    result[#result + 1] = Copy(offer)
                end
            end
        end
    end
    -- A verified permanent shelf is a usable quotation even before visiting
    -- that NPC. Prefer it to Auctionator's unqualified cross-NPC unit cache:
    -- otherwise an old observed pack can downgrade known thread/dye prices to
    -- estimates and keep the route's "open merchant" diagnostic forever.
    if #result == 0 and not context.requireObservedPrice then
        for _, offer in ipairs(ns.ProfVendorOffers and ns.ProfVendorOffers[itemID] or {}) do
            if offer.reference == true and offer.priceVerified == true
                and not blockedNPC[offer.npcID] and Accessible(offer, context, character) then
                result[#result + 1] = Copy(offer)
            end
        end
    end
    -- Auctionator exposes observed unlimited purchase unit prices. A verified
    -- supplier plus an actually observed pack is required to use that cache;
    -- retain an estimate marker because its discount may belong to another NPC.
    if context.allowVendorCache and not context.requireObservedPrice and #result==0 then
        local api=Auctionator and Auctionator.API and Auctionator.API.v1
        local ok,unit=false,nil
        local quote=api and (api.GetVendorPriceByItemID or api.GetVendorPrice)
        if type(quote)=="function" then ok,unit=pcall(quote,"DungeonsForever",itemID) end
        if ok and type(unit)=="number" and unit>=0 then
            for _,supplier in ipairs(VDB.GetSuppliers(itemID,context)) do
                local pack
                for _,record in pairs(records or {}) do
                    if record.npcID==supplier.npcID and record.unlimited and record.available~=false and not record.hasExtendedCost and
                        (not record.currencyID or record.currencyID==0) then
                        pack=tonumber(record.quantity or record.bundleSize); if pack then break end
                    end
                end
                local faction=supplier.faction
                if pack and (not faction or faction=="N" or faction=="Neutral" or faction==Faction(context)) and RequirementsMet(supplier,context) then
                    local offer={}; for k,v in pairs(supplier) do offer[k]=v end
                    offer.price=unit*pack; offer.quantity=pack; offer.bundleSize=pack
                    offer.source="auctionator-vendor"; offer.estimated=true; offer.priceBasis="observed-unit-cache"
                    offer.reference=nil; offer.priceVerified=nil; offer.catalogueOnly=nil
                    result[#result+1]=Copy(offer); break
                end
            end
        end
    end
    table.sort(result, function(a, b)
        if a.unit ~= b.unit then return a.unit < b.unit end
        if a.estimated ~= b.estimated then return not a.estimated end
        if a.quantity ~= b.quantity then return a.quantity < b.quantity end
        return (a.npcID or 0) < (b.npcID or 0)
    end)
    return result
end

-- Supplier discovery remains separate from quotations: an audited shelf may
-- establish NPC procurement even when no reliable quotation has been recorded.
function VDB.GetSuppliers(itemID,context)
    context=context or {}
    local out={}; local seen={}
    for _,entry in ipairs(ns.ProfVendorOffers and ns.ProfVendorOffers[itemID] or {}) do
        local faction=entry.faction
        local blocked=false
        for _,observed in pairs(DB().profVendorOffers[itemID] or {}) do
            if observed.character==(context.character or Character()) and observed.npcID==entry.npcID and
                (observed.available==false or observed.unlimited==false or observed.hasExtendedCost or (observed.currencyID and observed.currencyID~=0)) then blocked=true end
        end
        if not blocked and (not faction or faction=="N" or faction=="Neutral" or faction=="AH" or faction==Faction(context))
           and RequirementsMet(entry,context) then
            local record={}; for k,v in pairs(entry) do record[k]=v end
            out[#out+1]=record; seen[entry.npcID]=true
        end
    end
    for _,entry in pairs(DB().profVendorOffers[itemID] or {}) do
        if not seen[entry.npcID] and entry.character==(context.character or Character()) and entry.source=="merchant" and
            entry.unlimited and entry.available~=false and not entry.hasExtendedCost and
            (not entry.currencyID or entry.currencyID==0) and RequirementsMet(entry,context) then
            local record={}; for k,v in pairs(entry) do record[k]=v end
            out[#out+1]=record; seen[entry.npcID]=true
        end
    end
    return out
end

function VDB.GetPrice(itemID, context)
    local priceContext = {}
    for key, value in pairs(context or {}) do priceContext[key] = value end
    if priceContext.requireObservedPrice == nil then priceContext.requireObservedPrice = false end
    if priceContext.allowVendorCache == nil then priceContext.allowVendorCache = true end
    local offers = VDB.GetOffers(itemID, priceContext)
    return offers[1] and offers[1].unit or nil
end

-- Formula acquisition has a separate shelf policy: a limited recipe is a
-- legitimate purchase, but never becomes an unlimited material quotation.
function VDB.GetFormulaOffers(itemID,context,source)
    context=context or {}; source=source or {}
    local character=context.character or Character()
    local result,seen={},{}
    local function add(raw,observed)
        if type(raw)~="table" then return end
        local o={}; for k,v in pairs(raw) do o[k]=v end
        local price=observed and raw.formulaPrice or raw.price
        if observed and price==nil and raw.unlimited then price=raw.price end
        local pack=tonumber(raw.quantity or raw.bundleSize)
        if observed and (not pack or pack<1 or pack~=math.floor(pack)) then price=nil end
        -- Reuse faction, reputation, character and purchase-condition checks.
        -- A sold-out or restricted shelf may still be displayed with its price.
        local check={}; for k,v in pairs(o) do check[k]=v end
        check.price=price or 0;check.quantity=check.quantity or check.bundleSize or 1
        check.unlimited=true;check.available=true
        if not Accessible(check,context,character) then return end
        o.price=price;o.quantity=check.quantity;o.bundleSize=check.quantity
        o.unit=type(price)=="number" and price/o.quantity or nil
        o.stock=observed and raw.stock or nil
        o.limited=raw.unlimited==false or raw.limited==true or nil
        o.stockStatus=raw.unlimited==true and "unlimited" or o.limited and "limited" or "unknown"
        o.stockUnknown=o.stockStatus=="unknown" or nil
        o.purchasable=raw.purchasable
        o.available=not (raw.purchasable==false or o.stock==0)
        o.priceUsable=o.available and type(price)=="number" and price>=0
        o.reference=not observed and raw.reference or nil
        if observed then
            o.priceUsable=o.priceUsable and (raw.purchasable==true
                or raw.formulaPrice==nil and raw.unlimited==true and raw.available~=false)
        end
        result[#result+1]=o
        if o.npcID then seen[o.npcID]=true end
    end
    for _,o in pairs(DB().profVendorOffers[itemID] or {}) do
        if o.character==character and o.source=="merchant" then
            if o.npcID and (o.purchasable==false or o.hasExtendedCost or o.currencyID and o.currencyID~=0) then seen[o.npcID]=true end
            add(o,true)
        end
    end
    if not context.requireObservedPrice then
        for _,o in ipairs(ns.ProfFormulaOffers and ns.ProfFormulaOffers[itemID] or {}) do
            if not seen[o.npcID] and o.reference and o.priceVerified then add(o,false) end
        end
    end
    -- Catalogue source names and locations remain useful without an audited
    -- purchase quotation. Never infer a buy price from an item's sale value.
    for _,v in ipairs(source.vendors or {}) do
        local id=v.id or v.npcID or v[5]
        if not id or not seen[id] then
            local o={npcID=id,npcName=v.name or v[1],name=v.name or v[1],zone=v.zone or v[2],
                price=type(v.price)=="number" and v.price or nil,quantity=v.quantity or 1,
                unlimited=v.unlimited,limited=v.limited,stockUnknown=v.unlimited==nil and v.limited==nil or nil,
                stockStatus=v.unlimited and "unlimited" or v.limited and "limited" or "unknown",
                source="catalogue",reference=true,url=v.url,available=true,priceUsable=false}
            if o.price and v.priceVerified and v.verifiedAt then
                o.verifiedAt=v.verifiedAt;o.priceVerified=true;add(o,false)
            else result[#result+1]=o;if id then seen[id]=true end end
        end
    end
    table.sort(result,function(a,b)
        local ap,bp=a.unit or math.huge,b.unit or math.huge
        if ap~=bp then return ap<bp end
        return (a.npcID or 0)<(b.npcID or 0)
    end)
    return result
end

local function MerchantNPC()
    local guid = UnitGUID and UnitGUID("npc")
    return guid and tonumber(guid:match("^[^-]+%-[^-]+%-[^-]+%-[^-]+%-[^-]+%-(%d+)%-"))
end

local function ReadMerchantInfo(index)
    if C_MerchantFrame and C_MerchantFrame.GetItemInfo then
        local ok, data = pcall(C_MerchantFrame.GetItemInfo, index)
        if ok and type(data) == "table" then
            return data.name, data.price, data.stackCount or data.quantity,
                data.numAvailable, data.isPurchasable, data.hasExtendedCost, data.currencyID
        end
    end
    if not GetMerchantItemInfo then return end
    local ok, name, _, price, quantity, available, sixth, seventh, eighth, currencyID =
        pcall(GetMerchantItemInfo, index)
    if not ok then return end
    if eighth ~= nil or currencyID ~= nil then
        return name, price, quantity, available, sixth, eighth, currencyID
    end
    -- Older clients expose isUsable, hasExtendedCost in slots 6 and 7.
    -- false usability is insufficient evidence that a restricted item is buyable.
    return name, price, quantity, available, sixth == true, seventh, nil
end

function VDB.Scan()
    if not GetMerchantNumItems then return 0 end
    local ok, count = pcall(GetMerchantNumItems)
    local npcID, character = MerchantNPC(), Character()
    if not ok or type(count) ~= "number" or count <= 0 or not npcID or not character then return 0 end
    local db, stamp, fresh, changed = DB(), Now(), 0, false
    local repKey = ReputationKey()
    local mapID = C_Map and C_Map.GetBestMapForUnit and C_Map.GetBestMapForUnit("player")
    local position = mapID and C_Map.GetPlayerMapPosition and C_Map.GetPlayerMapPosition(mapID, "player")
    for index = 1, count do
        local name, price, quantity, available, purchasable, extendedCost, currencyID = ReadMerchantInfo(index)
        local itemID
        if GetMerchantItemID then local success, id = pcall(GetMerchantItemID, index); if success then itemID = id end end
        if not itemID and GetMerchantItemLink then
            local success, link = pcall(GetMerchantItemLink, index)
            itemID = success and link and tonumber(link:match("item:(%d+)")) or nil
        end
        quantity = tonumber(quantity)
        if itemID then
            local unlimited
            if type(available) == "number" then unlimited = available == -1 end
            local rejected = unlimited == false or purchasable == false or extendedCost == true
                or currencyID and currencyID ~= 0
            local eligible = available == -1 and purchasable == true and not extendedCost
                and (not currencyID or currencyID == 0) and type(price) == "number" and price >= 0
                and quantity and quantity >= 1 and quantity == math.floor(quantity)
            -- Keep rejection evidence even when the API has not loaded a price.
            -- Missing fields alone do not disprove the audited permanent shelf.
            local quotedPrice = eligible and price or nil
            local formulaPrice=type(price)=="number" and price>=0 and quantity and quantity>=1
                and quantity==math.floor(quantity) and not extendedCost and (not currencyID or currencyID==0) and price or nil
            local records = db.profVendorOffers[itemID]
            if type(records) ~= "table" then records = {}; db.profVendorOffers[itemID] = records end
            local key = character .. ":" .. npcID
            local old = records[key]
            if not old or old.price ~= quotedPrice or old.quantity ~= quantity or old.available ~= (not rejected)
                or old.unlimited ~= unlimited or old.hasExtendedCost ~= (not not extendedCost)
                or old.currencyID ~= currencyID or old.reputationKey ~= repKey
                or old.formulaPrice~=formulaPrice or old.stock~=available or old.purchasable~=purchasable then
                records[key] = {
                    itemID = itemID, npcID = npcID, npcName = UnitName and UnitName("npc"),
                    price = quotedPrice, quantity = quantity, bundleSize = quantity,
                    formulaPrice=formulaPrice,stock=available,purchasable=purchasable,
                    unlimited = unlimited, available = not rejected, hasExtendedCost = not not extendedCost,
                    currencyID = currencyID, source = "merchant", verifiedAt = stamp,
                    url = "https://www.wowhead.com/forever/npc=" .. npcID,
                    character = character, faction = Faction(), estimated = false,
                    priceBasis = "current-character", reputationRevision = reputationRevision, reputationKey = repKey,
                    mapID = mapID, x = position and position.x, y = position and position.y,
                }
                changed = true
                if eligible and not old then fresh = fresh + 1 end
                if eligible then db.vendorPrices[itemID] = { p = price / quantity, t = stamp } end
            end
        end
    end
    if changed then Notify() end
    return fresh
end

function VDB.Count()
    local count = 0
    for itemID in pairs(DB().profVendorOffers) do
        if #VDB.GetOffers(itemID,{requireObservedPrice=true}) > 0 then count = count + 1 end
    end
    return count
end

if CreateFrame then
    local frame = CreateFrame("Frame")
    frame:RegisterEvent("MERCHANT_SHOW")
    frame:RegisterEvent("MERCHANT_UPDATE")
    frame:RegisterEvent("UPDATE_FACTION")
    frame:SetScript("OnEvent", function(_, event)
        if event == "UPDATE_FACTION" then
            reputationRevision = reputationRevision + 1
            reputationKey = nil
            Notify()
        end
        if pendingScan then return end
        pendingScan = true
        local function ScanLater()
            pendingScan = false
            pcall(VDB.Scan)
        end
        if C_Timer and C_Timer.After then C_Timer.After(0, ScanLater) else ScanLater() end
    end)
end
