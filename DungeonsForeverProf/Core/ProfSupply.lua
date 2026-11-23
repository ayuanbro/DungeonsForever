local _, ns = ...
if type(ns) ~= "table" then ns = _G.DF_NS or {} end
local gns = _G.DF_NS

local M = {
    built = false,
    offerCount = 0,
    itemCount = 0,
    DataSchema = 2,
    SourceAccessSchema = 1,
    SourcePurchaseSchema = 1,
}
ns.ProfSupply = M
if type(gns) == "table" and gns ~= ns then
    gns.ProfSupply = M
end

local EMPTY = setmetatable({}, {
    __newindex = function() error("ProfSupply: EMPTY table is read-only", 2) end,
    __metatable = false,
})
local formulaFactsCache = setmetatable({}, { __mode = "k" })
local invalidating = false
local delegateInvalidate = nil
local ahPriceGuard = false

local function getDS()
    return ns.ProfDataStore or (type(gns) == "table" and gns.ProfDataStore) or nil
end

local function getCond()
    return ns.ProfConditions or (type(gns) == "table" and gns.ProfConditions) or nil
end

local function getAPI()
    return ns.ProfAPI or (type(gns) == "table" and gns.ProfAPI) or nil
end

local function getPricingCfg()
    return ns.PricingConfig or (type(gns) == "table" and gns.PricingConfig) or nil
end

local function getRouteAuto()
    return ns.ProfRouteAuto or (type(gns) == "table" and gns.ProfRouteAuto) or nil
end

local function getRecovery()
    return ns.ProfRecovery or (type(gns) == "table" and gns.ProfRecovery) or nil
end

local function Int(v, minVal)
    return type(v) == "number" and v == v and v >= minVal and v < math.huge and v == math.floor(v)
end

local function Now()
    if type(_G.debugprofilestop) ~= "function" then return nil end
    local ok, v = pcall(_G.debugprofilestop)
    if ok and type(v) == "number" then return v end
    return nil
end

local function quietMs()
    local cfg = getPricingCfg()
    local cache = type(cfg) == "table" and cfg.CACHE or nil
    if type(cache) == "table" and type(cache.quietDebounceMs) == "number" and cache.quietDebounceMs > 0 then
        return cache.quietDebounceMs
    end
    return 300
end

local function normalizeFaction(raw)
    if raw == "A" or raw == "Alliance" or raw == "联盟" then return "A" end
    if raw == "H" or raw == "Horde" or raw == "部落" then return "H" end
    if raw == "N" or raw == "Neutral" or raw == "Both" then return "N" end
    return nil
end

local function resolvePlayerFaction(ctx)
    if type(ctx) == "table" then
        if ctx.faction ~= nil then
            return normalizeFaction(ctx.faction)
        end
        if ctx.strict == true then
            return nil
        end
    end
    if type(_G.UnitFactionGroup) == "function" then
        local ok, localized, english = pcall(_G.UnitFactionGroup, "player")
        if ok then
            return normalizeFaction(english) or normalizeFaction(localized)
        end
    end
    return nil
end

local function allowedFaction(side, mine)
    if side == nil or side == "N" or mine == nil then return true end
    return side == mine
end

local function copyCurrencies(raw)
    local out = {}
    if type(raw) ~= "table" then return out end
    for i = 1, #raw do
        local c = raw[i]
        if type(c) == "table" then
            local cid = tonumber(c.currencyID or c.id)
            local amt = tonumber(c.amount ~= nil and c.amount or c.count) or 0
            if cid and cid > 0 then
                out[#out + 1] = {
                    currencyID = cid,
                    amount = amt,
                    id = cid,
                    count = amt,
                }
            end
        end
    end
    return out
end

local function copyCostItems(raw)
    local out = {}
    if type(raw) ~= "table" then return out end
    for i = 1, #raw do
        local it = raw[i]
        if type(it) == "table" then
            local iid = tonumber(it.itemID or it.id)
            local cnt = tonumber(it.count ~= nil and it.count or it.amount) or 1
            if iid and iid > 0 then
                out[#out + 1] = {
                    itemID = iid,
                    count = cnt,
                    id = iid,
                }
            end
        end
    end
    return out
end

local function copyConditions(raw)
    local out = {}
    if type(raw) ~= "table" then return out end
    for i = 1, #raw do
        local c = raw[i]
        if type(c) == "table" then
            local cp = {}
            for k, v in pairs(c) do
                if type(v) == "table" then
                    local sub = {}
                    for sk, sv in pairs(v) do
                        if type(sv) == "table" then
                            local sub2 = {}
                            for s2k, s2v in pairs(sv) do sub2[s2k] = s2v end
                            sub[sk] = sub2
                        else
                            sub[sk] = sv
                        end
                    end
                    cp[k] = sub
                else
                    cp[k] = v
                end
            end
            out[#out + 1] = cp
        end
    end
    return out
end

local function copyOffer(offer, currencies, costItems)
    local out = {}
    for k, v in pairs(offer) do
        if k == "currencies" then
            out.currencies = currencies
        elseif k == "costItems" then
            out.costItems = costItems
        elseif k == "conditions" then
            out.conditions = copyConditions(v)
        else
            out[k] = v
        end
    end
    if out.currencies == nil then out.currencies = currencies end
    if out.costItems == nil then out.costItems = costItems end
    if out.conditions == nil then out.conditions = {} end
    return out
end

local function compareOffers(a, b)
    local ca = a.hasExtendedCost and 1 or 0
    local cb = b.hasExtendedCost and 1 or 0
    if ca ~= cb then return ca < cb end
    local ua = a.unitCopper or math.huge
    local ub = b.unitCopper or math.huge
    if ua ~= ub then return ua < ub end
    if (a.npcID or 0) ~= (b.npcID or 0) then return (a.npcID or 0) < (b.npcID or 0) end
    if (a.optionIndex or 0) ~= (b.optionIndex or 0) then return (a.optionIndex or 0) < (b.optionIndex or 0) end
    return (a.sourceOrder or 0) < (b.sourceOrder or 0)
end

local function normalizeOffer(itemID, offer, index, DS, Cond, ctx, playerFaction, checkAccess, commonVendorCount)
    if type(offer) ~= "table" then return nil end
    local rawNpc = offer.npcID ~= nil and offer.npcID or offer.id
    local npcID = rawNpc ~= nil and tonumber(rawNpc) or nil
    if rawNpc ~= nil and not Int(npcID, 1) then return nil end

    local rawBundle = offer.bundleSize ~= nil and offer.bundleSize or offer.quantity
    local bundleSize = rawBundle == nil and 1 or rawBundle
    if not Int(bundleSize, 1) then return nil end

    local ms = offer.maxStock ~= nil and offer.maxStock or offer.stock
    if checkAccess and ms == 0 then return nil end

    local npc = npcID and DS and type(DS.Npc) == "function" and DS.Npc(npcID) or nil
    local npcFaction = normalizeFaction(offer.faction or (npc and npc.faction))

    if checkAccess then
        if not allowedFaction(npcFaction, playerFaction) then return nil end
        if npc and Cond then
            if type(Cond.IsNpcAccessible) == "function" then
                if not Cond.IsNpcAccessible(npc, ctx) then return nil end
            elseif type(npc.accessConditions) == "table" and #npc.accessConditions > 0 and type(Cond.IsMet) == "function" then
                if not Cond.IsMet(npc.accessConditions, ctx) then return nil end
            end
        end
        if type(offer.conditions) == "table" and #offer.conditions > 0 and Cond and type(Cond.IsMet) == "function" then
            if not Cond.IsMet(offer.conditions, ctx) then return nil end
        end
    end

    local currencies = copyCurrencies(offer.currencies)
    local costItems = copyCostItems(offer.costItems)
    if #currencies == 0 and Int(offer.currencyID, 1) then
        local amt = tonumber(offer.currencyAmount ~= nil and offer.currencyAmount or offer.curAmt) or 0
        currencies[1] = {
            currencyID = offer.currencyID,
            amount = amt,
            id = offer.currencyID,
            count = amt,
        }
    end

    local isMixed = (#currencies > 0 or #costItems > 0 or offer.hasExtendedCost == true)
    local rawPrice = offer.priceCopper ~= nil and offer.priceCopper or offer.price
    local hasPrice = type(rawPrice) == "number" and rawPrice == rawPrice and rawPrice >= 0 and rawPrice < math.huge
    local unitCopper = hasPrice and (rawPrice / bundleSize) or nil

    local areaID
    if npc and type(npc.spawns) == "table" and type(npc.spawns[1]) == "table" then
        areaID = npc.spawns[1].areaID
    end

    local unlimited = ms == -1
    local limited = (type(ms) == "number" and ms > 0) and ms or nil

    return {
        npcID = npcID,
        itemID = itemID,
        optionIndex = offer.optionIndex,
        sourceOrder = index,
        priceCopper = hasPrice and rawPrice or nil,
        price = hasPrice and rawPrice or nil,
        unitCopper = unitCopper,
        bundleSize = bundleSize,
        quantity = bundleSize,
        maxStock = ms,
        unlimited = unlimited,
        limited = limited,
        stockUnknown = (ms == nil) or nil,
        available = ms ~= 0,
        purchasable = true,
        currencies = currencies,
        costItems = costItems,
        hasExtendedCost = isMixed,
        currencyID = (#currencies > 0 and currencies[1].currencyID) or 0,
        currencyAmount = (#currencies > 0 and currencies[1].amount) or 0,
        priceVerified = offer.priceVerified == true,
        priceUsable = hasPrice and not isMixed,
        faction = npcFaction or "N",
        areaID = areaID,
        conditions = copyConditions(offer.conditions),
        commonVendorCount = commonVendorCount,
        offer = copyOffer(offer, currencies, costItems),
    }
end

local function buildOfferList(itemID, withCurrency, ctx, checkAccess)
    if not Int(itemID, 1) then return nil end
    local DS = getDS()
    local Cond = getCond()
    if not DS or type(DS.VendorOffers) ~= "function" then return nil end
    local vo = DS.VendorOffers(itemID)
    if type(vo) ~= "table" or type(vo.offers) ~= "table" then return nil end

    local playerFaction = checkAccess and resolvePlayerFaction(ctx) or nil
    local commonCount = type(vo.commonVendorCount) == "number" and vo.commonVendorCount or nil
    local list = {}
    for index = 1, #vo.offers do
        local entry = normalizeOffer(itemID, vo.offers[index], index, DS, Cond, ctx, playerFaction, checkAccess, commonCount)
        if entry and (withCurrency or not entry.hasExtendedCost) then
            list[#list + 1] = entry
        end
    end
    table.sort(list, compareOffers)
    return list
end

function M.CommonVendorCount(itemID)
    if not Int(itemID, 1) then return nil end
    local DS = getDS()
    local vo = DS and type(DS.VendorOffers) == "function" and DS.VendorOffers(itemID) or nil
    return type(vo) == "table" and type(vo.commonVendorCount) == "number" and vo.commonVendorCount or nil
end

function M.FormulaFacts(itemID)
    if not Int(itemID, 1) then return EMPTY end
    local DS = getDS()
    if not DS or type(DS.VendorOffers) ~= "function" then return EMPTY end
    local vo = DS.VendorOffers(itemID)
    if type(vo) ~= "table" or type(vo.offers) ~= "table" then return EMPTY end
    local cached = formulaFactsCache[vo]
    if cached then return cached end
    cached = {}
    for i = 1, #vo.offers do
        local o = vo.offers[i]
        if type(o) == "table" then
            local npcID = tonumber(o.npcID or o.id)
            if Int(npcID, 1) then
                local npc = type(DS.Npc) == "function" and DS.Npc(npcID) or nil
                local side = normalizeFaction(o.faction or (npc and npc.faction))
                local avail = o.maxStock ~= 0
                local prev = cached[npcID]
                if not prev then
                    cached[npcID] = { faction = side, available = avail, purchasable = true }
                else
                    if prev.faction ~= side then prev.faction = nil end
                    prev.available = prev.available or avail
                end
            end
        end
    end
    formulaFactsCache[vo] = cached
    return cached
end

function M.FormulaList(itemID, ctx)
    if not Int(itemID, 1) then return nil end
    return buildOfferList(itemID, false, ctx, ctx ~= nil)
end

function M.DisplayList(itemID, ctx)
    if not Int(itemID, 1) then return nil end
    return buildOfferList(itemID, true, ctx, ctx ~= nil)
end

function M.VendorPrice(itemID, ctx)
    if not Int(itemID, 1) then return nil end
    local list = buildOfferList(itemID, true, ctx, true)
    if type(list) ~= "table" or #list == 0 then return nil end
    local bestPure, bestMixed
    for i = 1, #list do
        local e = list[i]
        if type(e.priceCopper) == "number" and e.priceCopper >= 0 then
            local cand = {
                priceCopper = e.priceCopper,
                unitCopper = e.unitCopper,
                bundleSize = e.bundleSize,
                npcID = e.npcID,
                optionIndex = e.optionIndex,
                currencies = e.currencies,
                costItems = e.costItems,
                hasExtendedCost = e.hasExtendedCost,
                maxStock = e.maxStock,
                priceVerified = e.priceVerified,
                commonVendorCount = e.commonVendorCount,
                offer = e.offer,
            }
            if not e.hasExtendedCost then
                if not bestPure or cand.unitCopper < bestPure.unitCopper then
                    bestPure = cand
                end
            else
                if not bestMixed or cand.unitCopper < bestMixed.unitCopper then
                    bestMixed = cand
                end
            end
        end
    end
    return bestPure or bestMixed
end

function M.Price(itemID, ctx)
    if not Int(itemID, 1) then return nil end
    local list = buildOfferList(itemID, false, ctx, true)
    if type(list) ~= "table" or #list == 0 then return nil end
    local best
    for i = 1, #list do
        local e = list[i]
        if type(e.unitCopper) == "number" and (not best or e.unitCopper < best.unitCopper) then
            best = e
        end
    end
    if not best then return nil end
    return best.unitCopper, best.npcID
end

function M.AHPriceOf(itemID, ctx)
    if type(itemID) ~= "number" then return nil end
    if type(ctx) == "table" and type(ctx.ahPrices) == "table" and type(ctx.ahPrices[itemID]) == "number" then
        return ctx.ahPrices[itemID]
    end
    if ahPriceGuard then return nil end
    local ra = getRouteAuto()
    if ra and type(ra.AHPriceOf) == "function" then
        ahPriceGuard = true
        local ok, price = pcall(ra.AHPriceOf, itemID, ctx)
        ahPriceGuard = false
        if ok and type(price) == "number" then return price end
    end
    local API = getAPI()
    local del = API and type(API.GetDelegate) == "function" and API.GetDelegate("pricing") or nil
    if type(del) == "table" and type(del.AHPriceOf) == "function" and del.AHPriceOf ~= M.AHPriceOf then
        ahPriceGuard = true
        local ok, price = pcall(del.AHPriceOf, itemID, ctx)
        ahPriceGuard = false
        if ok and type(price) == "number" then return price end
    end
    return nil
end

function M.EffectiveCost(itemID, qtyOrCtx, ctxOrNil)
    if type(itemID) ~= "number" then return nil end
    local qty, ctx
    if type(qtyOrCtx) == "table" and ctxOrNil == nil then
        qty, ctx = 1, qtyOrCtx
    else
        qty = tonumber(qtyOrCtx) or 1
        ctx = ctxOrNil
    end
    if qty <= 0 then return 0 end

    local vp = M.VendorPrice(itemID, ctx)
    local vendorUnit = nil
    if vp then
        local pure = vp.hasExtendedCost ~= true
            and not (type(vp.offer) == "table" and vp.offer.hasExtendedCost == true)
            and (type(vp.currencies) ~= "table" or #vp.currencies == 0)
            and (type(vp.costItems) ~= "table" or #vp.costItems == 0)
        if pure and type(vp.unitCopper) == "number" then
            vendorUnit = vp.unitCopper
        end
    end
    local ahUnit = M.AHPriceOf(itemID, ctx)
    local bestUnit
    if type(vendorUnit) == "number" and type(ahUnit) == "number" then
        bestUnit = math.min(vendorUnit, ahUnit)
    elseif type(vendorUnit) == "number" then
        bestUnit = vendorUnit
    elseif type(ahUnit) == "number" then
        bestUnit = ahUnit
    end
    if not bestUnit then return nil end
    return bestUnit * qty
end

function M.MatPriceOf(itemID, ctx)
    return M.EffectiveCost(itemID, 1, ctx)
end

function M.NPCSellPriceOf(itemID)
    if type(itemID) ~= "number" then return nil end
    local rec = getRecovery()
    if rec and type(rec.NPCSellPriceOf) == "function" then
        return rec.NPCSellPriceOf(itemID)
    end
    local DS = getDS()
    local item = DS and type(DS.Item) == "function" and DS.Item(itemID) or nil
    return item and item.sellPriceCopper or nil
end

local function makeVendorOffersProxy()
    return setmetatable({}, {
        __index = function(_, itemID)
            if not Int(itemID, 1) then return EMPTY end
            local now = Now()
            local cache = M.cache
            if cache and now and M.stamp and (now - M.stamp) > quietMs() then
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
            local list = M.FormulaList(itemID) or EMPTY
            cache[itemID] = list
            return list
        end,
    })
end

local function attachVendorOffersProxy()
    if type(ns.ProfVendorOffers) ~= "table" then
        ns.ProfVendorOffers = makeVendorOffersProxy()
    end
    if type(gns) == "table" and gns ~= ns and type(gns.ProfVendorOffers) ~= "table" then
        gns.ProfVendorOffers = ns.ProfVendorOffers
    end
end

function M.Ensure()
    attachVendorOffersProxy()
    if M.built then return end
    M.built = true
    local DS = getDS()
    if not DS or type(DS.Ensure) ~= "function" then return end
    local sources = DS.Ensure("sources")
    local vo = type(sources) == "table" and sources.vendorOffers or nil
    local items, offers = 0, 0
    if type(vo) == "table" then
        for _, entry in pairs(vo) do
            if type(entry) == "table" and type(entry.offers) == "table" and #entry.offers > 0 then
                items = items + 1
                offers = offers + #entry.offers
            end
        end
    end
    M.itemCount = items
    M.offerCount = offers
end

function M.Flush()
    M.cache = nil
    M.stamp = nil
    formulaFactsCache = setmetatable({}, { __mode = "k" })
end

function M.Invalidate()
    if invalidating then return end
    invalidating = true
    M.Flush()
    local rec = getRecovery()
    if rec and type(rec.Invalidate) == "function" then
        pcall(rec.Invalidate)
    end
    local ra = getRouteAuto()
    if ra and type(ra.Invalidate) == "function" then
        pcall(ra.Invalidate)
    end
    invalidating = false
end

function M.Stats()
    M.Ensure()
    return M.itemCount, M.offerCount
end

function M.Ready()
    M.Ensure()
    return (M.offerCount or 0) > 0
end

local function registerDelegate()
    local API = getAPI()
    if not API or type(API.RegisterDelegate) ~= "function" then return end
    local prev = type(API.GetDelegate) == "function" and API.GetDelegate("pricing") or nil
    local impl = {}
    if type(prev) == "table" then
        for k, v in pairs(prev) do impl[k] = v end
    end
    impl.VendorPrice = M.VendorPrice
    impl.EffectiveCost = M.EffectiveCost
    impl.MatPriceOf = M.MatPriceOf
    local prevInv = type(prev) == "table" and type(prev.Invalidate) == "function" and prev.Invalidate or nil
    if prevInv == delegateInvalidate and delegateInvalidate ~= nil then
        impl.Invalidate = delegateInvalidate
    elseif prevInv and prevInv ~= M.Invalidate then
        local active = false
        delegateInvalidate = function()
            if active then return end
            active = true
            M.Invalidate()
            pcall(prevInv)
            active = false
        end
        impl.Invalidate = delegateInvalidate
    else
        impl.Invalidate = M.Invalidate
    end
    if not impl.AHPriceOf then impl.AHPriceOf = M.AHPriceOf end
    if not impl.NPCSellPriceOf then impl.NPCSellPriceOf = M.NPCSellPriceOf end
    API.RegisterDelegate("pricing", impl)
end

M.RegisterDelegate = registerDelegate

attachVendorOffersProxy()
registerDelegate()
