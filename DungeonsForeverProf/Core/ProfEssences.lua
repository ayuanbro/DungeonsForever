local _, ns = ...
if type(ns) ~= "table" then ns = _G.DF_NS or {} end
local gns = _G.DF_NS

local X = { revision = 1, DataSchema = 2 }
ns.ProfEssences = X
if type(gns) == "table" and gns ~= ns then
    gns.ProfEssences = X
end

local pairsList, byOutput, byItem = {}, {}, {}
local dataSource, dataRevision, initialized = nil, nil, false

local function getDS()
    return ns.ProfDataStore or (type(gns) == "table" and gns.ProfDataStore) or nil
end

local function getAPI()
    return ns.ProfAPI or (type(gns) == "table" and gns.ProfAPI) or nil
end

local function getCond()
    return ns.ProfConditions or (type(gns) == "table" and gns.ProfConditions) or nil
end

local function getEconomy()
    return ns.ProfEconomy or (type(gns) == "table" and gns.ProfEconomy) or nil
end

local function getSupply()
    return ns.ProfSupply or (type(gns) == "table" and gns.ProfSupply) or nil
end

local function normalizeFaction(raw)
    if raw == "A" or raw == "Alliance" then return "A" end
    if raw == "H" or raw == "Horde" then return "H" end
    if raw == "N" or raw == "Neutral" or raw == "Both" then return "N" end
    return nil
end

local function refresh()
    local DS = getDS()
    local source = DS and type(DS.Essences) == "function" and DS.Essences() or nil
    local rev = DS and ((type(DS.Fingerprint) == "function" and DS.Fingerprint())
        or (type(DS.Build) == "function" and DS.Build())) or 1
    if initialized and dataSource == source and dataRevision == rev then return end
    initialized = true
    dataSource, dataRevision = source, rev
    pairsList, byOutput, byItem = {}, {}, {}
    X.revision = rev
    if type(source) ~= "table" then return end

    local seen = {}
    for _, entry in pairs(source) do
        if type(entry) == "table"
            and type(entry.inputItemID) == "number" and entry.inputItemID > 0
            and type(entry.outputItemID) == "number" and entry.outputItemID > 0
            and type(entry.inputCount) == "number" and entry.inputCount > 0
            and type(entry.outputCount) == "number" and entry.outputCount > 0 then
            local pairKey = entry.pairKey or entry.key
            if type(pairKey) == "string" and pairKey ~= "" then
                local lesserID = entry.lesserID
                local greaterID = entry.greaterID
                if type(lesserID) ~= "number" or type(greaterID) ~= "number" then
                    if entry.inputCount > entry.outputCount then
                        lesserID, greaterID = entry.inputItemID, entry.outputItemID
                    else
                        lesserID, greaterID = entry.outputItemID, entry.inputItemID
                    end
                end
                local pair = seen[pairKey]
                if not pair then
                    pair = {
                        key = pairKey,
                        pairKey = pairKey,
                        lesserID = lesserID,
                        greaterID = greaterID,
                    }
                    seen[pairKey] = pair
                    pairsList[#pairsList + 1] = pair
                end
                byItem[entry.inputItemID] = pair
                byItem[entry.outputItemID] = pair
                byOutput[entry.outputItemID] = {
                    key = pairKey,
                    pairKey = pairKey,
                    profession = entry.profession or "enchanting",
                    inputItemID = entry.inputItemID,
                    inputCount = entry.inputCount,
                    outputItemID = entry.outputItemID,
                    outputCount = entry.outputCount,
                    lesserID = pair.lesserID,
                    greaterID = pair.greaterID,
                    noSkillGain = entry.noSkillGain ~= false,
                    status = entry.status or "confirmed",
                }
            end
        end
    end
    table.sort(pairsList, function(a, b)
        if (a.lesserID or 0) ~= (b.lesserID or 0) then
            return (a.lesserID or 0) < (b.lesserID or 0)
        end
        return tostring(a.key) < tostring(b.key)
    end)
end

function X.Name(id)
    refresh()
    if not byItem[id] then return nil end
    local api = getAPI()
    if api and type(api.ItemName) == "function" then
        local nm, known = api.ItemName(id)
        if known == true and type(nm) == "string" and nm ~= "" then
            return nm
        end
    end
    local DS = getDS()
    if DS and type(DS.RawText) == "function" then
        local raw = DS.RawText("item", id)
        if type(raw) == "string" and raw ~= "" then return raw end
    end
    local getter = (_G.C_Item and _G.C_Item.GetItemInfo) or _G.GetItemInfo
    if type(getter) == "function" then
        local ok, name = pcall(getter, id)
        if ok and type(name) == "string" and name ~= "" then return name end
    end
    return nil
end

function X.Pair(id)
    refresh()
    local p = byItem[id]
    if not p then return nil end
    return {
        key = p.key,
        pairKey = p.pairKey,
        lesserID = p.lesserID,
        greaterID = p.greaterID,
    }
end

function X.Pairs()
    refresh()
    local out = {}
    for i = 1, #pairsList do
        local p = pairsList[i]
        out[i] = {
            key = p.key,
            pairKey = p.pairKey,
            lesserID = p.lesserID,
            greaterID = p.greaterID,
        }
    end
    return out
end

function X.ForItem(id)
    refresh()
    local value = byOutput[id]
    if not value then return nil end
    local out = {}
    for key, item in pairs(value) do out[key] = item end
    return out
end

function X.Enabled(slug, opts, snapshot)
    opts = opts or {}
    return slug == "enchanting"
        or (slug == "__purchase" and snapshot and snapshot.essenceConversions == true)
        or (opts.allowSecondaryLeveling == true and opts.secondaryProfession == "enchanting")
        or false
end

function X.ExpandItems(items)
    refresh()
    if type(items) ~= "table" then return items end
    local extra = {}
    for id in pairs(items) do
        local conversion = byOutput[id]
        if conversion then extra[conversion.inputItemID] = true end
    end
    for id in pairs(extra) do items[id] = true end
    return items
end

function X.Contains(mats)
    refresh()
    for _, mat in ipairs(mats or {}) do
        local id = type(mat) == "table" and (mat.id or mat.itemID or mat[1]) or mat
        if byItem[id] then return true end
    end
    return false
end

local function isPureUnlimitedOffer(offer, snapshot, DS, Cond)
    if type(offer) ~= "table" then return false end
    local unlimited = (offer.unlimited == true) or (type(offer.maxStock) == "number" and offer.maxStock < 0)
    if not unlimited or offer.available == false or offer.purchasable == false or offer.maxStock == 0 then
        return false
    end
    local price = offer.priceCopper ~= nil and offer.priceCopper or offer.price
    if type(price) ~= "number" or price ~= price or price < 0 or price >= math.huge then
        return false
    end
    if offer.hasExtendedCost == true or (type(offer.currencyID) == "number" and offer.currencyID > 0) then
        return false
    end
    if (type(offer.currencies) == "table" and #offer.currencies > 0)
        or (type(offer.costItems) == "table" and #offer.costItems > 0) then
        return false
    end
    local npcID = tonumber(offer.npcID or offer.id)
    local npc = npcID and DS and type(DS.Npc) == "function" and DS.Npc(npcID) or nil
    local side = normalizeFaction(offer.faction or (npc and npc.faction))
    local snapSide = normalizeFaction(snapshot.faction)
    if side and side ~= "N" and snapSide and side ~= snapSide then
        return false
    end
    if Cond then
        if npc and type(Cond.IsNpcAccessible) == "function" and not Cond.IsNpcAccessible(npc, snapshot) then
            return false
        end
        if type(offer.conditions) == "table" and #offer.conditions > 0
            and type(Cond.IsMet) == "function" and not Cond.IsMet(offer.conditions, snapshot) then
            return false
        end
    end
    return true
end

function X.MissingQuotes(snapshot, items)
    refresh()
    snapshot = type(snapshot) == "table" and snapshot or {}
    local DS = getDS()
    local Cond = getCond()
    local economy = getEconomy()
    local considerSupply = economy and type(economy.ConsiderAuctionSupply) == "function"
        and economy.ConsiderAuctionSupply(snapshot) == true

    local missing, seen = {}, {}
    local function known(id)
        if snapshot.nonAuctionable and snapshot.nonAuctionable[id] then return true end
        local price = snapshot.prices and snapshot.prices[id]
        if type(price) == "number" and price > 0 and price < math.huge then return true end
        local supply = considerSupply and snapshot.auctionSupply and snapshot.auctionSupply[id] or nil
        if supply and supply.complete == true and supply.quantity == 0 then return true end
        if type(snapshot.offers) == "table" then
            for _, offer in ipairs(snapshot.offers[id] or {}) do
                if isPureUnlimitedOffer(offer, snapshot, DS, Cond) then
                    return true
                end
            end
        else
            local vo = DS and type(DS.VendorOffers) == "function" and DS.VendorOffers(id) or nil
            local offers = type(vo) == "table" and type(vo.offers) == "table" and vo.offers or nil
            if type(offers) == "table" and #offers > 0 then
                for _, offer in ipairs(offers) do
                    if isPureUnlimitedOffer(offer, snapshot, DS, Cond) then
                        return true
                    end
                end
            else
                local sup = getSupply()
                local vp = sup and type(sup.VendorPrice) == "function" and sup.VendorPrice(id, snapshot) or nil
                if not vp then
                    local api = getAPI()
                    if api and type(api.VendorPrice) == "function" then
                        vp = api.VendorPrice(id, snapshot)
                    end
                end
                if type(vp) == "table" and type(vp.unitCopper) == "number"
                    and vp.hasExtendedCost ~= true
                    and not (type(vp.offer) == "table" and (
                        vp.offer.hasExtendedCost == true
                        or (type(vp.offer.currencyID) == "number" and vp.offer.currencyID > 0)
                        or vp.offer.available == false
                        or vp.offer.purchasable == false
                    ))
                    and (type(vp.currencies) ~= "table" or #vp.currencies == 0)
                    and (type(vp.costItems) ~= "table" or #vp.costItems == 0)
                    and vp.maxStock ~= 0
                    and ((type(vp.maxStock) == "number" and vp.maxStock < 0)
                        or (type(vp.offer) == "table" and vp.offer.unlimited == true)) then
                    return true
                end
            end
        end
        return false
    end

    for id in pairs(items or {}) do
        local pair = byItem[id]
        if pair and not seen[pair.key] then
            seen[pair.key] = true
            for _, itemID in ipairs({ pair.lesserID, pair.greaterID }) do
                if not known(itemID) then missing[#missing + 1] = itemID end
            end
        end
    end
    table.sort(missing)
    return missing
end
