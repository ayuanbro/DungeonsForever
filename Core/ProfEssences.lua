-- Verified Classic item-use conversions. These actions consume no skill point
-- and belong to the route's material ledger, not to its crafting recipe list.
local _, ns = ...
if not ns.LoadForeverPages then return end
local X = { revision = 1 }
ns.ProfEssences = X

local pairsList = {
    { lesserID = 10938, greaterID = 10939 },
    { lesserID = 10998, greaterID = 11082 },
    { lesserID = 11134, greaterID = 11135 },
    { lesserID = 11174, greaterID = 11175 },
    { lesserID = 16202, greaterID = 16203 },
}
local byOutput, byItem = {}, {}
for _, pair in ipairs(pairsList) do
    pair.key = pair.lesserID .. ":" .. pair.greaterID
    byItem[pair.lesserID], byItem[pair.greaterID] = pair, pair
    for _, direction in ipairs({
        { pair.lesserID, 3, pair.greaterID, 1 },
        { pair.greaterID, 1, pair.lesserID, 3 },
    }) do
        byOutput[direction[3]] = {
            key = pair.key, lesserID = pair.lesserID, greaterID = pair.greaterID,
            inputItemID = direction[1], inputCount = direction[2],
            outputItemID = direction[3], outputCount = direction[4],
            status = "confirmed", noSkillGain = true, manual = true,
        }
    end
end
function X.Name(id)
    if not byItem[id] then return end
    local getter = C_Item and C_Item.GetItemInfo or GetItemInfo
    if type(getter) == "function" then
        local ok, name = pcall(getter, id)
        if ok and type(name) == "string" and name ~= "" then return name end
    end
    local names = ns.ProfItemNames
    return type(names) == "table" and names[id] or nil
end
function X.Pair(id) return byItem[id] end
function X.Pairs() return pairsList end
function X.ForItem(id)
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
    local extra = {}
    for id in pairs(items) do
        local conversion = byOutput[id]
        if conversion then extra[conversion.inputItemID] = true end
    end
    for id in pairs(extra) do items[id] = true end
    return items
end
function X.Contains(mats)
    for _, mat in ipairs(mats or {}) do
        if byItem[mat.id or mat[1]] then return true end
    end
    return false
end
-- Missing alternative quotes limit an optimality claim even when the selected
-- material purchases have complete costs. An observed zero supply is evidence.
function X.MissingQuotes(snapshot, items)
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
