local ns = _G.DF_NS or {}
if not ns.LoadForeverPages then return end
local X = { revision = 1, DataSchema = 1 }
ns.ProfEssences = X

local pairsList,byOutput,byItem={},{},{}
local dataSource,dataRevision,initialized
local function refresh()
    local source=ns.ProfData and ns.ProfData.runtime
    local revision=source and source.revision
    if initialized and dataSource==source and dataRevision==revision then return end
    initialized=true
    dataSource,dataRevision=source,revision
    pairsList,byOutput,byItem={},{},{}
    X.revision=revision or 1
    if type(source)=="table" and source.schema==1 then
        local seen={}
        for _,entry in ipairs(source.essenceConversions or {}) do
            if type(entry)=="table" and type(entry.inputItemID)=="number" and type(entry.outputItemID)=="number"
                and type(entry.key)=="string" and type(entry.lesserID)=="number" and type(entry.greaterID)=="number"
                and type(entry.inputCount)=="number" and entry.inputCount>0
                and type(entry.outputCount)=="number" and entry.outputCount>0 then
                local pair=seen[entry.key]
                if not pair then
                    pair={key=entry.key,lesserID=entry.lesserID,greaterID=entry.greaterID}
                    seen[entry.key]=pair;pairsList[#pairsList+1]=pair
                end
                byItem[entry.inputItemID],byItem[entry.outputItemID]=pair,pair
                byOutput[entry.outputItemID]=entry
            end
        end
        return
    end

end
refresh()
function X.Name(id)
    refresh()
    if not byItem[id] then return end
    local getter = C_Item and C_Item.GetItemInfo or GetItemInfo
    if type(getter) == "function" then
        local ok, name = pcall(getter, id)
        if ok and type(name) == "string" and name ~= "" then return name end
    end
    local names = ns.ProfItemNames
    return type(names) == "table" and names[id] or nil
end
function X.Pair(id) refresh();return byItem[id] end
function X.Pairs() refresh();return pairsList end
function X.ForItem(id)
    refresh()
    local value = byOutput[id]
    if not value then return end
    local out = {}; for key, item in pairs(value) do out[key] = item end
    return out
end
function X.Enabled(slug, opts, snapshot)
    opts = opts or {}
    return slug == "enchanting"
        or slug == "__purchase" and snapshot and snapshot.essenceConversions == true
        or opts.allowSecondaryLeveling == true and opts.secondaryProfession == "enchanting"
        or false
end
function X.ExpandItems(items)
    refresh()
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
        if byItem[mat.id or mat[1]] then return true end
    end
    return false
end
function X.MissingQuotes(snapshot, items)
    refresh()
    local missing, seen = {}, {}
    local function known(id)
        if snapshot.nonAuctionable and snapshot.nonAuctionable[id] then return true end
        local price = snapshot.prices and snapshot.prices[id]
        if type(price) == "number" and price > 0 and price < math.huge then return true end
        local economy=ns.ProfEconomy
        local supply = economy and economy.ConsiderAuctionSupply and economy.ConsiderAuctionSupply(snapshot)
            and snapshot.auctionSupply and snapshot.auctionSupply[id]
        if supply and supply.complete == true and supply.quantity == 0 then return true end
        for _, offer in ipairs(snapshot.offers and snapshot.offers[id] or {}) do
            if offer.unlimited == true and type(offer.price) == "number"
                and offer.price >= 0 and offer.price < math.huge
                and offer.available ~= false and offer.purchasable ~= false
                and not offer.hasExtendedCost and (not offer.currencyID or offer.currencyID == 0)
                and (not offer.faction or not snapshot.faction or offer.faction == snapshot.faction
                    or offer.faction == "Neutral" or offer.faction == "N") then return true end
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
