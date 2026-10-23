local _, ns = ...
if not ns.LoadForeverPages then return end

local M = { built = false, offerCount = 0, itemCount = 0 }
ns.ProfSupply = M

local SIDES = { "A", "H", "N" }
local EMPTY = {}
local QUIET_MS = 300

local function Int(v, min)
    return type(v) == "number" and v >= min and v < math.huge and v == math.floor(v)
end

local function Now()
    if type(debugprofilestop) ~= "function" then return nil end
    local ok, v = pcall(debugprofilestop)
    if ok and type(v) == "number" then return v end
    return nil
end

local function Text(v)
    return type(v) == "string" and v ~= ""
end

local function FactionOf(code)
    return SIDES[code]
end

local function PlayerSide()
    if type(UnitFactionGroup) ~= "function" then return nil end
    local ok, localized, english = pcall(UnitFactionGroup, "player")
    if not ok then return nil end
    local v = english
    if not Text(v) then v = localized end
    if v == "Alliance" or v == "联盟" then return "A" end
    if v == "Horde" or v == "部落" then return "H" end
    return nil
end

local function Allowed(side, mine)
    if side == nil or side == "N" then return true end
    if mine == nil then return true end
    return side == mine
end

local function Compare(a, b)
    local ca = (a.currencyID or 0) > 0 and 1 or 0
    local cb = (b.currencyID or 0) > 0 and 1 or 0
    if ca ~= cb then return ca < cb end
    local ua, ub
    if ca == 1 then
        ua, ub = a.currencyAmount or 0, b.currencyAmount or 0
    else
        local qa, qb = a.quantity, b.quantity
        if type(qa) ~= "number" or qa < 1 then qa = 1 end
        if type(qb) ~= "number" or qb < 1 then qb = 1 end
        ua, ub = (a.price or 0) / qa, (b.price or 0) / qb
    end
    if ua ~= ub then return ua < ub end
    return (a.npcID or 0) < (b.npcID or 0)
end

local function BuildList(itemID)
    local supply = M.supply
    if type(supply) ~= "table" then return nil end
    local flat = supply[itemID]
    if type(flat) ~= "table" then return nil end
    local total = #flat
    if total < 5 or total % 5 ~= 0 then return nil end
    local verifiedAt = M.verifiedAt
    local list
    for i = 1, total, 5 do
        local npcID, price, quantity = flat[i], flat[i + 1], flat[i + 2]
        if Int(npcID, 1) and Int(price, 0) and Int(quantity, 1) then
            list = list or {}
            list[#list + 1] = {
                npcID = npcID, price = price, quantity = quantity, bundleSize = quantity,
                unlimited = true, available = true,
                hasExtendedCost = false, currencyID = 0,
                reference = true, priceVerified = true,
                source = "supply-verified", verifiedAt = verifiedAt,
                faction = FactionOf(flat[i + 3]),
            }
        end
    end
    if not list then return nil end
    table.sort(list, Compare)
    return list
end

local FORMULA_STEP = 8

local function BuildFormulaList(itemID, withCurrency)
    local flat = ns.ProfFormulaOffers and ns.ProfFormulaOffers[itemID]
    if type(flat) ~= "table" then return nil end
    local total = #flat
    if total < FORMULA_STEP or total % FORMULA_STEP ~= 0 then return nil end
    local verifiedAt = M.formulaVerifiedAt
    local list
    for i = 1, total, FORMULA_STEP do
        local npcID, cost, stock, side = flat[i], flat[i + 1], flat[i + 2], flat[i + 3]
        local areaID, pack, curID, curAmt = flat[i + 4], flat[i + 5], flat[i + 6], flat[i + 7]
        if Int(npcID, 1) then
            local unlimited = stock == -1
            local limited = (type(stock) == "number" and stock >= 0) and stock or nil
            local entry = {
                npcID = npcID,
                quantity = Int(pack, 1) and pack or 1,
                unlimited = unlimited, limited = limited,
                maxStock = limited and stock or nil,
                stockUnknown = (not unlimited and limited == nil) or nil,
                available = stock ~= 0, purchasable = true,
                reference = true, priceVerified = true, estimated = false,
                source = "formula-offers", verifiedAt = verifiedAt,
                faction = FactionOf(side),
                areaID = Int(areaID, 1) and areaID or nil,
                hasExtendedCost = false, currencyID = 0, price = 0,
            }
            entry.bundleSize = entry.quantity
            if Int(curID, 1) then
                if not withCurrency then entry = nil end
                if entry then
                    entry.currencyID = curID
                    entry.currencyAmount = tonumber(curAmt) or 0
                    entry.hasExtendedCost = true
                end
            elseif type(cost) == "number" then
                entry.price = cost
            else
                entry = nil
            end
            if entry then
                list = list or {}
                list[#list + 1] = entry
            end
        end
    end
    if not list then return nil end
    table.sort(list, Compare)
    return list
end

local function Count(supply)
    local items, offers = 0, 0
    for _, flat in pairs(supply) do
        if type(flat) == "table" and #flat >= 5 then
            items = items + 1
            offers = offers + math.floor(#flat / 5)
        end
    end
    return items, offers
end

function M.Ensure()
    if M.built then return end
    M.built = true
    local fmeta = ns.ProfFormulaOffersMeta
    if type(fmeta) == "table" and fmeta.schemaVersion == 1 then
        M.formulaVerifiedAt = fmeta.source or "formula-offers"
    end
    local meta = ns.ProfMaterialSupplyMeta
    local supply = ns.ProfMaterialSupply
    if type(meta) ~= "table" or meta.schemaVersion ~= 2 then return end
    if not Text(meta.fingerprint) or not Text(meta.verifiedAt) or type(supply) ~= "table" then return end
    M.supply = supply
    M.verifiedAt = meta.verifiedAt
    M.itemCount, M.offerCount = Count(supply)
    ns.ProfVendorOffers = setmetatable({}, {
        __index = function(_, itemID)
            if type(itemID) ~= "number" or itemID < 1 then return EMPTY end
            local now = Now()
            local cache = M.cache
            if cache and now and M.stamp and (now - M.stamp) > QUIET_MS then
                cache = nil
                M.cache = nil
            end
            if not cache then
                cache = {}
                M.cache = cache
            end
            if now then M.stamp = now end
            local hit = cache[itemID]
            if hit then return hit end
            local list = BuildList(itemID) or EMPTY
            cache[itemID] = list
            return list
        end,
    })
end

function M.FormulaList(itemID)
    if not Int(itemID, 1) then return nil end
    if not M.formulaVerifiedAt then
        local fmeta = ns.ProfFormulaOffersMeta
        if type(fmeta) == "table" and fmeta.schemaVersion == 1 then
            M.formulaVerifiedAt = fmeta.source or "formula-offers"
        end
    end
    return BuildFormulaList(itemID)
end

function M.DisplayList(itemID)
    if not Int(itemID, 1) then return nil end
    if not M.formulaVerifiedAt then
        local fmeta = ns.ProfFormulaOffersMeta
        if type(fmeta) == "table" and fmeta.schemaVersion == 1 then
            M.formulaVerifiedAt = fmeta.source or "formula-offers"
        end
    end
    return BuildFormulaList(itemID, true)
end

function M.Flush()
    M.cache = nil
    M.stamp = nil
end
function M.Price(itemID)
    if not Int(itemID, 1) then return nil end
    M.Ensure()
    local source = ns.ProfVendorOffers
    if type(source) ~= "table" then return nil end
    local list = source[itemID]
    if type(list) ~= "table" or #list == 0 then return nil end
    local mine = PlayerSide()
    local best, bestNpc
    for _, offer in ipairs(list) do
        if Allowed(offer.faction, mine) then
            local unit = offer.price / offer.quantity
            if not best or unit < best then best, bestNpc = unit, offer.npcID end
        end
    end
    return best, bestNpc
end

function M.Stats()
    M.Ensure()
    return M.itemCount, M.offerCount
end

function M.Ready()
    M.Ensure()
    return (M.offerCount or 0) > 0
end
