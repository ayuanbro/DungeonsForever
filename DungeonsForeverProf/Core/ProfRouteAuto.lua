local _, ns = ...
if type(ns) ~= "table" then ns = _G.DF_NS or {} end
local gns = _G.DF_NS

local RA = ns.ProfRouteAuto or (type(gns) == "table" and gns.ProfRouteAuto) or {}
ns.ProfRouteAuto = RA
if type(gns) == "table" and gns ~= ns then
    gns.ProfRouteAuto = RA
end

local existingComputeFishing = RA.ComputeFishing
local format = string.format

local function getDS()
    return ns.ProfDataStore or (type(gns) == "table" and gns.ProfDataStore) or nil
end

local function getCond()
    return ns.ProfConditions or (type(gns) == "table" and gns.ProfConditions) or nil
end

local function getAPI()
    return ns.ProfAPI or (type(gns) == "table" and gns.ProfAPI) or nil
end

local function getDB()
    return ns.ProfDB or (type(gns) == "table" and gns.ProfDB) or nil
end

local function getSettings()
    return ns.ProfSettings or (type(gns) == "table" and gns.ProfSettings) or getDB()
end

local function getPricingCfg()
    return ns.PricingConfig or (type(gns) == "table" and gns.PricingConfig) or nil
end

local function getSolverCfg()
    return ns.SolverConfig or (type(gns) == "table" and gns.SolverConfig) or nil
end

local function getProfCfg()
    return ns.ProfessionsConfig or (type(gns) == "table" and gns.ProfessionsConfig) or nil
end

local function getSupply()
    return ns.ProfSupply or (type(gns) == "table" and gns.ProfSupply) or nil
end

local function getRecovery()
    return ns.ProfRecovery or (type(gns) == "table" and gns.ProfRecovery) or nil
end

local function getFishing()
    return ns.ProfFishing or (type(gns) == "table" and gns.ProfFishing) or nil
end

local function getGates()
    return ns.ProfGates or (type(gns) == "table" and gns.ProfGates) or nil
end

local function getEssences()
    return ns.ProfEssences or (type(gns) == "table" and gns.ProfEssences) or nil
end

local function getEconomy()
    return ns.ProfEconomy or (type(gns) == "table" and gns.ProfEconomy) or nil
end

local function getSolver()
    return ns.ProfRouteSolver or (type(gns) == "table" and gns.ProfRouteSolver) or nil
end

local function getExecution()
    return ns.ProfExecution or (type(gns) == "table" and gns.ProfExecution) or nil
end

local function getAuctionBridge()
    return ns.AuctionBridge or (type(gns) == "table" and gns.AuctionBridge) or nil
end

local function getEasyBridge()
    return ns.EasyBridge or (type(gns) == "table" and gns.EasyBridge) or nil
end

local function getIdle()
    return ns.ProfIdle or (type(gns) == "table" and gns.ProfIdle) or nil
end

local function getFollow()
    return ns.ProfFollow or (type(gns) == "table" and gns.ProfFollow) or nil
end

local function getHost()
    return ns.ProfHost or (type(gns) == "table" and gns.ProfHost) or nil
end

local function tr(k)
    local L = ns.L or (type(gns) == "table" and gns.L) or nil
    if type(L) == "table" and L[k] ~= nil then return L[k] end
    return k
end

local function nowSec()
    if type(_G.time) == "function" then
        local ok, v = pcall(_G.time)
        if ok and type(v) == "number" then return v end
    end
    if type(os) == "table" and type(os.time) == "function" then
        return os.time()
    end
    return 0
end

local CALLER = "DungeonsForever"
local DEFAULT_SCHEME_ORDER = { "cheapest", "matcost", "crafts", "optim" }
local DEFAULT_SCHEME_LABELS = {
    cheapest = "最省钱",
    stable = "稳定升级",
    matcost = "材料成本",
    crafts = "次数最少",
    optim = "乐观计数",
}

local function cfgCap()
    local cfg = getSolverCfg()
    return (type(cfg) == "table" and type(cfg.CAP) == "number" and cfg.CAP) or 300
end

local function cfgDefaultTarget()
    local cfg = getSolverCfg()
    return (type(cfg) == "table" and type(cfg.DEFAULT_TARGET) == "number" and cfg.DEFAULT_TARGET) or 300
end

local function cfgMaxPerRecipe()
    local cfg = getSolverCfg()
    return (type(cfg) == "table" and type(cfg.MAX_PER_RECIPE) == "number" and cfg.MAX_PER_RECIPE) or 3
end

local function cfgDiffRates()
    local cfg = getSolverCfg()
    local dr = type(cfg) == "table" and type(cfg.DIFFICULTY_RATES) == "table" and cfg.DIFFICULTY_RATES or nil
    local gy = (dr and type(dr.G_YELLOW) == "number" and dr.G_YELLOW) or 0.5
    local gg = (dr and type(dr.G_GREEN) == "number" and dr.G_GREEN) or 0.05
    return gy, gg
end

local function cfgCacheTTL()
    local pcfg = getPricingCfg()
    local c = type(pcfg) == "table" and type(pcfg.CACHE) == "table" and pcfg.CACHE or nil
    if c and type(c.quoteTTL) == "number" then return c.quoteTTL end
    local scfg = getSolverCfg()
    local f = type(scfg) == "table" and type(scfg.FRESHNESS) == "table" and scfg.FRESHNESS or nil
    return (f and type(f.resultCacheTTL) == "number" and f.resultCacheTTL) or 600
end

local function cfgCacheSlots()
    local pcfg = getPricingCfg()
    local c = type(pcfg) == "table" and type(pcfg.CACHE) == "table" and pcfg.CACHE or nil
    if c and type(c.slotsPerSlug) == "number" then return c.slotsPerSlug end
    local scfg = getSolverCfg()
    local f = type(scfg) == "table" and type(scfg.FRESHNESS) == "table" and scfg.FRESHNESS or nil
    return (f and type(f.resultCacheSlots) == "number" and f.resultCacheSlots) or 4
end

local function cfgNegTTL()
    local pcfg = getPricingCfg()
    local c = type(pcfg) == "table" and type(pcfg.CACHE) == "table" and pcfg.CACHE or nil
    return (c and type(c.negTTL) == "number" and c.negTTL) or 60
end

local function isFixedOnly(slug)
    if type(slug) ~= "string" or slug == "" then return false end
    local cfg = getProfCfg()
    local entry = type(cfg) == "table" and type(cfg.BY_SLUG) == "table" and cfg.BY_SLUG[slug]
    if type(entry) == "table" then return entry.fixedOnly == true end
    return slug == "first-aid" or slug == "poisons"
end

local function skipEconomy(slug)
    if type(slug) ~= "string" or slug == "" then return false end
    local cfg = getProfCfg()
    local entry = type(cfg) == "table" and type(cfg.BY_SLUG) == "table" and cfg.BY_SLUG[slug]
    if type(entry) == "table" then return entry.skipEconomy == true end
    return slug == "poisons"
end

local function resolveDBRoot(db)
    if type(db) == "table" then
        if type(db.Get) == "function" then
            local ok, root = pcall(db.Get)
            if ok and type(root) == "table" then return root end
        end
        local mt = getmetatable(db)
        if type(mt) == "table" and type(mt.__call) == "function" then
            local ok, root = pcall(db)
            if ok and type(root) == "table" then return root end
        end
    elseif type(db) == "function" then
        local ok, root = pcall(db)
        if ok and type(root) == "table" then return root end
    end
    return nil
end

local function readSetting(key, slug, fallback)
    local st = getSettings()
    if type(st) == "table" and type(st.Setting) == "function" then
        local ok, v = pcall(st.Setting, key, slug)
        if ok and v ~= nil then return v end
    end
    local root = resolveDBRoot(st) or resolveDBRoot(getDB())
    local prof = type(root) == "table" and root.prof or nil
    if type(prof) == "table" then
        if type(slug) == "string" and slug ~= "" and type(prof.professionSettings) == "table"
            and type(prof.professionSettings[slug]) == "table" then
            local v = prof.professionSettings[slug][key]
            if v ~= nil then return v and true or false end
        end
        if prof[key] ~= nil then return prof[key] and true or false end
    end
    return fallback
end

local function readSettingRaw(key, slug, fallback)
    local st = getSettings()
    if type(st) == "table" and type(st.SettingRaw) == "function" then
        local ok, v = pcall(st.SettingRaw, key, slug)
        if ok and v ~= nil then return v end
    end
    local root = resolveDBRoot(st) or resolveDBRoot(getDB())
    local prof = type(root) == "table" and root.prof or nil
    if type(prof) == "table" then
        if type(slug) == "string" and slug ~= "" and type(prof.professionSettings) == "table"
            and type(prof.professionSettings[slug]) == "table" then
            local v = prof.professionSettings[slug][key]
            if v ~= nil then return v end
        end
        if prof[key] ~= nil then return prof[key] end
    end
    return fallback
end

local function readTargetSkill(slug)
    local db = getDB()
    if type(db) == "table" and type(db.TargetSkill) == "function" then
        local ok, v = pcall(db.TargetSkill, slug)
        if ok and type(v) == "number" then return v end
    end
    local root = resolveDBRoot(db)
    local prof = type(root) == "table" and root.prof or nil
    if type(prof) == "table" then
        local v
        if type(slug) == "string" and slug ~= "" and type(prof.lvTarget) == "table" then
            v = tonumber(prof.lvTarget[slug])
        end
        if not v then v = tonumber(prof.target) end
        if v and v == v then
            return math.max(1, math.min(cfgCap(), math.floor(v)))
        end
    end
    return cfgDefaultTarget()
end

function RA.SchemeOrder()
    local cfg = getSolverCfg()
    local order = type(cfg) == "table" and type(cfg.OBJECTIVES) == "table" and cfg.OBJECTIVES.ORDER
    if type(order) == "table" and #order > 0 then
        local out = {}
        for i = 1, #order do out[i] = order[i] end
        return out
    end
    local out = {}
    for i = 1, #DEFAULT_SCHEME_ORDER do out[i] = DEFAULT_SCHEME_ORDER[i] end
    return out
end

function RA.SchemeLabel(s)
    local cfg = getSolverCfg()
    local labels = type(cfg) == "table" and type(cfg.OBJECTIVES) == "table" and cfg.OBJECTIVES.LABELS
    local k = (s and type(labels) == "table" and labels[s])
        or (s and DEFAULT_SCHEME_LABELS[s])
        or (type(labels) == "table" and labels.cheapest)
        or DEFAULT_SCHEME_LABELS.cheapest
    return tr(k)
end

function RA.MaxStale()
    local cfg = getPricingCfg()
    return (type(cfg) == "table" and type(cfg.MAX_STALE_DAYS) == "number" and cfg.MAX_STALE_DAYS) or 2
end

function RA.MaxStaleSeconds()
    return RA.MaxStale() * 86400
end

function RA.MaxAuctionSupplyAgeSeconds()
    local cfg = getPricingCfg()
    return (type(cfg) == "table" and type(cfg.SUPPLY_MAX_AGE_SEC) == "number" and cfg.SUPPLY_MAX_AGE_SEC) or 172800
end

local function AuctionatorReady()
    local a = _G.Auctionator
    return type(a) == "table"
        and type(a.API) == "table"
        and type(a.API.v1) == "table"
        and type(a.API.v1.GetAuctionPriceByItemID) == "function"
end

function RA.Available()
    if AuctionatorReady() then return true end
    local eb = getEasyBridge()
    if eb and type(eb.Available) == "function" and eb.Available() then return true end
    local ab = getAuctionBridge()
    if ab and type(ab.Available) == "function" and ab.Available() then return true end
    return false
end

local function CallAPI(fn, ...)
    local ok, v = pcall(fn, CALLER, ...)
    if ok then return v end
    return nil
end

local priceCache = {}
local vendorCache = {}
local sellCache = {}
local ahReason, ahAge = {}, {}

local function AHPrice(id)
    local c = priceCache[id]
    if c ~= nil then
        if c ~= false then return c end
        local now = nowSec()
        local t0 = priceCache.__t and priceCache.__t[id] or nil
        if t0 and (now - t0) < cfgNegTTL() then return nil end
    end
    local p
    local maxStale = RA.MaxStale()
    if AuctionatorReady() then
        local api = _G.Auctionator.API.v1
        p = CallAPI(api.GetAuctionPriceByItemID, id)
        if type(p) ~= "number" or not (p > 0 and p < math.huge) then p = nil end
        if p and type(api.GetAuctionAgeByItemID) == "function" then
            local age = CallAPI(api.GetAuctionAgeByItemID, id)
            if type(age) == "number" then
                if age > maxStale then
                    local bridge = getAuctionBridge()
                    if bridge and type(bridge.ForceExpiredActive) == "function" and bridge.ForceExpiredActive() then
                        ahAge[id] = age
                        ahReason[id] = nil
                    else
                        ahReason[id], ahAge[id] = "stale", age
                        p = nil
                    end
                end
                if age < (priceCache.__minAge or math.huge) then
                    priceCache.__minAge = age
                end
            end
        end
    else
        local eb = getEasyBridge()
        if eb and type(eb.Status) == "function" and eb.Status(id) == "verified" and type(eb.Price) == "function" then
            local ep = eb.Price(id)
            if type(ep) == "number" and ep > 0 and ep < math.huge then
                p = ep
            end
        end
        if not p then
            ahReason[id] = RA.Available() and "norec" or "noapi"
        end
    end
    if not p and ahReason[id] ~= "stale" and ahReason[id] ~= "noapi" then
        ahReason[id] = "norec"
    end
    priceCache[id] = p or false
    if not p then
        priceCache.__t = priceCache.__t or {}
        priceCache.__t[id] = nowSec()
    end
    if p then priceCache.__any = true end
    return p
end

function RA.ResetPrices()
    priceCache = {}
    vendorCache = {}
    sellCache = {}
    ahReason, ahAge = {}, {}
end

local function normalizeFaction(raw)
    if raw == "A" or raw == "Alliance" or raw == "联盟" then return "A" end
    if raw == "H" or raw == "Horde" or raw == "部落" then return "H" end
    if raw == "N" or raw == "Neutral" or raw == "Both" then return "N" end
    return nil
end

local function resolvePlayerFaction(ctx)
    if type(ctx) == "table" then
        if ctx.faction ~= nil then return normalizeFaction(ctx.faction) end
        if ctx.strict == true then return nil end
    end
    if type(_G.UnitFactionGroup) == "function" then
        local ok, localized, english = pcall(_G.UnitFactionGroup, "player")
        if ok then return normalizeFaction(english) or normalizeFaction(localized) end
    end
    return nil
end

local function allowedFaction(side, mine, ctx)
    if side == nil or side == "N" then return true end
    if mine == nil then
        return not (type(ctx) == "table" and ctx.strict == true)
    end
    return side == mine
end

local function isPureOffer(o)
    if type(o) ~= "table" then return false end
    if o.hasExtendedCost == true then return false end
    if type(o.offer) == "table" and o.offer.hasExtendedCost == true then return false end
    if type(o.currencies) == "table" and #o.currencies > 0 then return false end
    if type(o.costItems) == "table" and #o.costItems > 0 then return false end
    if type(o.currencyID) == "number" and o.currencyID > 0 then return false end
    return true
end

local function evalStandaloneOffers(itemID, ctx, withCurrency)
    local DS = getDS()
    local Cond = getCond()
    if not DS or type(DS.VendorOffers) ~= "function" then return nil end
    local vo = DS.VendorOffers(itemID)
    if type(vo) ~= "table" or type(vo.offers) ~= "table" then return nil end
    local playerFaction = resolvePlayerFaction(ctx)
    local commonCount = type(vo.commonVendorCount) == "number" and vo.commonVendorCount or nil
    local list = {}
    for index = 1, #vo.offers do
        local o = vo.offers[index]
        if type(o) == "table" then
            local ms = o.maxStock ~= nil and o.maxStock or o.stock
            if ms ~= 0 then
                local npcID = tonumber(o.npcID ~= nil and o.npcID or o.id)
                local npc = npcID and type(DS.Npc) == "function" and DS.Npc(npcID) or nil
                local npcFaction = normalizeFaction(o.faction or (npc and npc.faction))
                local ok = allowedFaction(npcFaction, playerFaction, ctx)
                if ok and npc and Cond then
                    if type(Cond.IsNpcAccessible) == "function" then
                        if not Cond.IsNpcAccessible(npc, ctx) then ok = false end
                    elseif type(npc.accessConditions) == "table" and #npc.accessConditions > 0 and type(Cond.IsMet) == "function" then
                        if not Cond.IsMet(npc.accessConditions, ctx) then ok = false end
                    end
                end
                if ok and type(o.conditions) == "table" and #o.conditions > 0 and Cond and type(Cond.IsMet) == "function" then
                    if not Cond.IsMet(o.conditions, ctx) then ok = false end
                end
                if ok then
                    local bundle = tonumber(o.bundleSize ~= nil and o.bundleSize or o.quantity) or 1
                    if type(bundle) ~= "number" or not (bundle >= 1 and bundle < math.huge) then
                        bundle = 1
                    else
                        bundle = math.floor(bundle)
                    end
                    local rawPrice = o.priceCopper ~= nil and o.priceCopper or o.price
                    local hasPrice = type(rawPrice) == "number" and rawPrice == rawPrice and rawPrice >= 0 and rawPrice < math.huge
                    local currencies = type(o.currencies) == "table" and o.currencies or {}
                    local costItems = type(o.costItems) == "table" and o.costItems or {}
                    local mixed = (#currencies > 0 or #costItems > 0 or o.hasExtendedCost == true or (type(o.currencyID) == "number" and o.currencyID > 0))
                    if withCurrency or not mixed then
                        list[#list + 1] = {
                            npcID = npcID,
                            itemID = itemID,
                            optionIndex = o.optionIndex,
                            sourceOrder = index,
                            priceCopper = hasPrice and rawPrice or nil,
                            price = hasPrice and rawPrice or nil,
                            unitCopper = hasPrice and (rawPrice / bundle) or nil,
                            bundleSize = bundle,
                            quantity = bundle,
                            maxStock = ms,
                            unlimited = ms == -1,
                            limited = (type(ms) == "number" and ms > 0) and ms or nil,
                            stockUnknown = (ms == nil) or nil,
                            available = ms ~= 0,
                            purchasable = true,
                            currencies = currencies,
                            costItems = costItems,
                            hasExtendedCost = mixed,
                            priceVerified = o.priceVerified == true,
                            faction = npcFaction or "N",
                            commonVendorCount = commonCount,
                            offer = o,
                        }
                    end
                end
            end
        end
    end
    table.sort(list, function(a, b)
        local ca = a.hasExtendedCost and 1 or 0
        local cb = b.hasExtendedCost and 1 or 0
        if ca ~= cb then return ca < cb end
        local ua = a.unitCopper or math.huge
        local ub = b.unitCopper or math.huge
        if ua ~= ub then return ua < ub end
        return (a.npcID or 0) < (b.npcID or 0)
    end)
    return list
end

function RA.VendorPrice(itemID, ctx)
    if type(itemID) ~= "number" or itemID <= 0 then return nil end
    local strictMissingFaction = type(ctx) == "table" and ctx.strict == true and normalizeFaction(ctx.faction) == nil
    local sup = getSupply()
    if not strictMissingFaction and sup and type(sup.VendorPrice) == "function" then
        return sup.VendorPrice(itemID, ctx)
    end
    local list = evalStandaloneOffers(itemID, ctx, true)
    if type(list) ~= "table" or #list == 0 then return nil end
    local bestPure, bestMixed
    for i = 1, #list do
        local e = list[i]
        if type(e.priceCopper) == "number" and e.priceCopper >= 0 and e.priceCopper < math.huge
            and type(e.unitCopper) == "number" and e.unitCopper >= 0 and e.unitCopper < math.huge then
            if not e.hasExtendedCost then
                if not bestPure or e.unitCopper < bestPure.unitCopper then bestPure = e end
            else
                if not bestMixed or e.unitCopper < bestMixed.unitCopper then bestMixed = e end
            end
        end
    end
    return bestPure or bestMixed
end

local function pureVendorUnit(itemID, ctx)
    local vp = RA.VendorPrice(itemID, ctx)
    if not vp or not isPureOffer(vp) then return nil end
    local u = vp.unitCopper
    if type(u) == "number" and u == u and u >= 0 and u < math.huge then
        return u
    end
    return nil
end

function RA.AHPriceOf(itemID, ctx)
    if type(itemID) ~= "number" or not (itemID > -math.huge and itemID < math.huge) then return nil end
    if type(ctx) == "table" then
        if type(ctx.ahPrices) == "table" and type(ctx.ahPrices[itemID]) == "number" then
            local ov = ctx.ahPrices[itemID]
            return (ov > 0 and ov < math.huge) and ov or nil
        end
        if type(ctx.snapshot) == "table" and type(ctx.snapshot.prices) == "table" then
            local sp = ctx.snapshot.prices[itemID]
            return (type(sp) == "number" and sp > 0 and sp < math.huge) and sp or nil
        end
        if type(ctx.prices) == "table" then
            local sp = ctx.prices[itemID]
            return (type(sp) == "number" and sp > 0 and sp < math.huge) and sp or nil
        end
    end
    local bridge = getAuctionBridge()
    local supply = bridge and type(bridge.GetAuctionSupply) == "function" and bridge.GetAuctionSupply(itemID) or nil
    if supply and (supply.quantity or 0) > 0 and type(supply.market) == "number" and supply.market > 0 and supply.market < math.huge then
        return supply.market
    end
    return AHPrice(itemID)
end

function RA.EffectiveCost(itemID, qtyOrCtx, ctxOrNil)
    if type(itemID) ~= "number" or not (itemID > -math.huge and itemID < math.huge) then return nil end
    local qty, ctx
    if type(qtyOrCtx) == "table" and ctxOrNil == nil then
        qty, ctx = 1, qtyOrCtx
    else
        qty = tonumber(qtyOrCtx) or 1
        ctx = ctxOrNil
    end
    if type(qty) ~= "number" or not (qty > -math.huge and qty < math.huge) then return nil end
    if qty <= 0 then return 0 end

    local v = pureVendorUnit(itemID, ctx)
    local a = RA.AHPriceOf(itemID, ctx)
    if type(a) ~= "number" or a <= 0 or a >= math.huge then a = nil end
    local best
    if v and a then
        best = math.min(v, a)
    else
        best = v or a
    end
    if not best then return nil end
    local total = best * qty
    if not (total >= 0 and total < math.huge) then return nil end
    return total
end

function RA.MatPriceOf(id, ctx)
    if type(id) ~= "number" then return nil end
    return RA.EffectiveCost(id, 1, ctx)
end

local function buildVendorCtx(opts)
    if type(opts) ~= "table" then return {} end
    if type(opts.snapshot) == "table" then
        local snap = opts.snapshot
        if (opts.faction ~= nil and snap.faction == nil) or (opts.strict ~= nil and snap.strict == nil) then
            local ctx = {}
            for k, v in pairs(snap) do ctx[k] = v end
            if ctx.faction == nil then ctx.faction = opts.faction end
            if ctx.strict == nil then ctx.strict = opts.strict end
            return ctx
        end
        return snap
    end
    local ctx = {}
    for _, k in ipairs({ "faction", "quests", "completedQuests", "items", "ownedSourceItems", "reputations", "abilities", "skills", "skillLines", "professions", "level", "classID", "raceID", "strict", "ahPrices", "includeBank" }) do
        if opts[k] ~= nil then ctx[k] = opts[k] end
    end
    return ctx
end

local function hasBlockedOffers(id, ctx)
    local DS = getDS()
    local vo = DS and type(DS.VendorOffers) == "function" and DS.VendorOffers(id) or nil
    if type(vo) == "table" and type(vo.offers) == "table" and #vo.offers > 0 then
        return pureVendorUnit(id, ctx) == nil
    end
    return false
end

local function MatReason(id, ctx)
    if RA.MatPriceOf(id, ctx) then return nil end
    if hasBlockedOffers(id, ctx) then return "novendor" end
    return ahReason[id] or "norec", ahAge[id]
end

local function isNonAuctionable(id)
    local DS = getDS()
    local item = DS and type(DS.Item) == "function" and DS.Item(id) or nil
    if type(item) == "table" then
        if item.nonAuctionable == true or item.bindType == 1 or item.bindType == 4 then return true end
    end
    return false
end

local function validDepthBook(book)
    if type(book) ~= "table" then return false end
    local total = book.total
    if type(total) ~= "number" or not (total >= 0 and total < math.huge) then return false end
    local totalCost = book.totalCost
    if totalCost ~= nil and (type(totalCost) ~= "number" or not (totalCost >= 0 and totalCost < math.huge)) then
        return false
    end
    local prices = book.prices
    local quantity = book.quantity
    local cost = book.cost
    if type(prices) ~= "table" or type(quantity) ~= "table" or type(cost) ~= "table" then
        return false
    end
    local n = #prices
    if total > 0 and n < 1 then return false end
    if #quantity < n or #cost < n then return false end
    for i = 1, n do
        local p = prices[i]
        local q = quantity[i]
        local c = cost[i]
        if type(p) ~= "number" or not (p > 0 and p < math.huge) then return false end
        if type(q) ~= "number" or not (q >= 0 and q < math.huge) then return false end
        if type(c) ~= "number" or not (c >= 0 and c < math.huge) then return false end
    end
    return true
end

function RA.MaterialPurchases(id, need, opts)
    opts = opts or {}
    local rawNeed = tonumber(need)
    if not rawNeed or rawNeed ~= rawNeed or rawNeed <= 0 then
        return {}, 0, true
    end
    if rawNeed >= math.huge then
        return { { id, 0, id = id, count = 0, need = 0, cost = 0, unit = 0, vendor = false, source = "ah", unpriced = true, unavailable = true } }, 0, false, "materialUnavailable"
    end
    need = math.ceil(rawNeed)
    local snap = opts.snapshot
    local economy = getEconomy()
    local sup = getSupply()
    local vendorCtx = buildVendorCtx(opts)
    local offers, auction, supply
    if snap then
        local rawOffers = type(snap.offers) == "table" and snap.offers[id] or nil
        local playerFaction = resolvePlayerFaction(vendorCtx)
        offers = {}
        if type(rawOffers) == "table" then
            for _, o in ipairs(rawOffers) do
                if type(o) == "table" then
                    local normSide = normalizeFaction(o.faction)
                    if allowedFaction(normSide, playerFaction, vendorCtx) then
                        if o.faction ~= nil and normSide ~= nil and normSide ~= o.faction then
                            local copy = {}
                            for k, v in pairs(o) do copy[k] = v end
                            copy.faction = normSide
                            offers[#offers + 1] = copy
                        else
                            offers[#offers + 1] = o
                        end
                    end
                end
            end
        end
        auction = snap.prices and snap.prices[id]
        if economy and type(economy.AuctionSupplyOf) == "function" then
            local ok, v = pcall(economy.AuctionSupplyOf, opts, id)
            if ok then supply = v end
        end
    else
        local strictMissingFaction = type(vendorCtx) == "table" and vendorCtx.strict == true and normalizeFaction(vendorCtx.faction) == nil
        if not strictMissingFaction and sup and type(sup.DisplayList) == "function" then
            offers = sup.DisplayList(id, vendorCtx) or {}
        else
            offers = evalStandaloneOffers(id, vendorCtx, true) or {}
        end
        auction = RA.AHPriceOf(id, opts)
        if economy and type(economy.AuctionSupplyOf) == "function" then
            local ok, v = pcall(economy.AuctionSupplyOf, opts, id)
            if ok then supply = v end
        end
    end
    local nonAucEco = false
    if not snap and economy and type(economy.NonAuctionableItem) == "function" then
        local ok, v = pcall(economy.NonAuctionableItem, id)
        if ok and v then nonAucEco = true end
    end
    if type(auction) ~= "number" or not (auction > 0 and auction < math.huge)
        or (snap and snap.nonAuctionable and snap.nonAuctionable[id])
        or (opts.nonAuctionable and opts.nonAuctionable[id])
        or nonAucEco
        or (not snap and isNonAuctionable(id)) then
        auction = nil
    end
    local rawRemaining = opts.auctionRemaining and opts.auctionRemaining[id]
    local available
    if rawRemaining ~= nil then
        if type(rawRemaining) == "number" and rawRemaining >= 0 and rawRemaining <= math.huge then
            available = rawRemaining
        else
            available = 0
        end
    elseif supply and supply.quantity ~= nil then
        if type(supply.quantity) == "number" and supply.quantity >= 0 and supply.quantity < math.huge then
            available = supply.quantity
        else
            available = 0
        end
    end
    local depth = ns.ProfAuctionDepth or (type(gns) == "table" and gns.ProfAuctionDepth) or nil
    local rawBook = snap and snap.auctionDepth and snap.auctionDepth[id]
    local book = nil
    local used = opts.auctionUsed and opts.auctionUsed[id]
    if type(used) ~= "number" or not (used >= 0 and used < math.huge) then
        used = 0
    else
        used = math.floor(used)
    end
    if snap and snap.auctionDepth and rawBook ~= nil then
        if validDepthBook(rawBook) then
            if rawBook.total > 0 then
                book = rawBook
                local remaining = math.max(0, book.total - used)
                available = available ~= nil and math.min(available, remaining) or remaining
                if not (snap.nonAuctionable and snap.nonAuctionable[id]) and not (opts.nonAuctionable and opts.nonAuctionable[id]) then
                    auction = book.prices[1]
                else
                    auction = nil
                end
            else
                available = 0
                auction = nil
            end
        else
            auction = nil
        end
    end
    if economy and type(economy.MaterialPurchases) == "function" then
        local rawFaction = (snap and snap.faction) or opts.faction
        local ok, rows, cost, complete, reason = pcall(economy.MaterialPurchases, id, need, {
            offers = offers,
            auction = auction,
            supply = supply,
            available = available,
            faction = normalizeFaction(rawFaction) or rawFaction,
            auctionCost = (auction ~= nil and book and used <= book.total and depth and depth.Cost) and function(count) return depth.Cost(book, used, count) end or nil,
        })
        if ok then
            return rows, cost, complete, reason
        end
    end
    local bestUnit
    local bestOffer
    local playerFaction = resolvePlayerFaction(vendorCtx)
    for _, o in ipairs(offers or {}) do
        if o.unlimited == true and o.available ~= false and o.purchasable ~= false and not o.priceOnly and isPureOffer(o)
            and allowedFaction(normalizeFaction(o.faction), playerFaction, vendorCtx) then
            local bundle = o.bundleSize ~= nil and o.bundleSize or o.quantity or 1
            local rawP = o.price ~= nil and o.price or o.priceCopper
            local validBundle = type(bundle) == "number" and bundle >= 1 and bundle < math.huge and bundle == math.floor(bundle)
            local validRaw = rawP == nil or (type(rawP) == "number" and rawP >= 0 and rawP < math.huge)
            if validBundle and validRaw then
                local u = (rawP ~= nil and (rawP / bundle)) or o.unitCopper
                if type(u) == "number" and u >= 0 and u < math.huge and (not bestUnit or u < bestUnit) then
                    bestUnit, bestOffer = u, o
                end
            end
        end
    end
    local ahLimit = (available ~= nil) and math.max(0, math.floor(available)) or nil
    local ahUsable = auction ~= nil and (ahLimit == nil or ahLimit >= need)
    if bestUnit and (not ahUsable or bestUnit <= auction) then
        local bundle = bestOffer.bundleSize ~= nil and bestOffer.bundleSize or bestOffer.quantity or 1
        local packs = math.ceil(need / bundle)
        local offerPrice = bestOffer.price ~= nil and bestOffer.price or bestOffer.priceCopper
        local cost = packs * (offerPrice or bestUnit * bundle)
        return { { id, need, id = id, count = need, need = need, cost = cost, unit = bestUnit, vendor = true, source = "vendor", offer = bestOffer } }, cost, true
    elseif ahUsable then
        local dCost = (book and used <= book.total and depth and type(depth.Cost) == "function") and depth.Cost(book, used, need) or nil
        local cost = dCost or (auction * need)
        local unit = need > 0 and (cost / need) or auction
        return { { id, need, id = id, count = need, need = need, cost = cost, unit = unit, vendor = false, source = "ah" } }, cost, true
    elseif auction then
        local dCost = (book and used <= book.total and depth and type(depth.Cost) == "function") and depth.Cost(book, used, need) or nil
        local unpriced = (book ~= nil and used <= book.total and dCost == nil) and true or nil
        local cost = unpriced and nil or (dCost or (auction * need))
        local unit = (cost and need > 0) and (cost / need) or nil
        return { {
            id, need,
            id = id, count = need, need = need,
            cost = cost, unit = unit,
            vendor = false, source = "ah",
            availableCount = available, supplyRequired = need,
            unavailable = true, costComplete = false,
            unpriced = unpriced,
        } }, cost, false, "auctionSupplyLimited"
    end
    return { { id, need, id = id, count = need, need = need, cost = 0, unit = 0, vendor = false, source = "ah", unpriced = true, unavailable = true } }, 0, false, "materialUnavailable"
end

function RA.PreferSharedFormula(entry, materialNeed, opts)
    opts = opts or {}
    local economy = getEconomy()
    local id = entry and entry.id
    if not id or not entry.recipe or not (economy and economy.FormulaFor) or not materialNeed or materialNeed <= 0 then return entry end
    local context = opts.snapshot
    if not context then
        context = {}
        for key, value in pairs(opts) do context[key] = value end
        context.profession = context.profession or entry.profession or entry.recipe.profession
    end
    local supply
    if type(economy.AuctionSupplyOf) == "function" then
        local ok, v = pcall(economy.AuctionSupplyOf, opts.snapshot and opts or context, id)
        if ok then supply = v end
    end
    local available = opts.auctionRemaining and opts.auctionRemaining[id]
    if available == nil and supply then available = supply.quantity end
    local candidates = {}
    local okNpc, npc = pcall(economy.FormulaFor, entry.recipe, context, 0)
    local okAh, auction = pcall(economy.FormulaFor, entry.recipe, context, available, "ah")
    if okNpc and npc then candidates[#candidates + 1] = npc end
    if okAh and auction then candidates[#candidates + 1] = auction end
    local best, bestRank, bestCost
    for _, candidate in ipairs(candidates) do
        if candidate and candidate.usable and not candidate.known
            and (candidate.source == "vendor" or candidate.source == "ah") then
            local remaining = available
            if candidate.source == "ah" and remaining ~= nil then remaining = math.max(0, remaining - (candidate.count or 1)) end
            local purchaseOpts = {}
            for key, value in pairs(opts) do purchaseOpts[key] = value end
            purchaseOpts.auctionRemaining = { [id] = remaining }
            local materials, cost, complete = RA.MaterialPurchases(id, materialNeed, purchaseOpts)
            local executable = true
            for _, material in ipairs(materials) do if material.unavailable then executable = false end end
            local rank = not executable and 2 or complete and candidate.costComplete ~= false and 0 or 1
            local combined = (candidate.cost or 0) + cost
            if bestRank == nil or rank < bestRank or rank == bestRank and combined < bestCost - 1e-9 then
                best, bestRank, bestCost = candidate, rank, combined
            end
        end
    end
    if best then
        best.recipes = entry.recipes or best.recipes
        return best
    end
    return entry
end

function RA.StampFormulaCosts(result)
    if type(result) ~= "table" then return result end
    for _, entry in ipairs(result.formulas or {}) do
        if entry.unpriced or entry.costComplete == false then
            result.costComplete = false
            result.completeCost = false
            result.formulaComplete = false
            result.optimal = false
            result.inputModelOptimal = false
            result.diagnostics = result.diagnostics or {}
            result.diagnostics[#result.diagnostics + 1] = { code = "formulaPriceUnknown", item = entry.id, spell = entry.spell }
        end
    end
    return result
end

function RA.StampMaterialPurchases(result)
    if type(result) ~= "table" then return result end
    for _, entry in ipairs(result.mats or {}) do
        if entry.unavailable or entry.costComplete == false then
            result.costComplete = false
            result.completeCost = false
            result.diagnostics = result.diagnostics or {}
            local code = entry.procurementReason or (entry.unavailable and "materialUnavailable" or "vendorEstimate")
            result.diagnostics[#result.diagnostics + 1] = {
                code = code,
                item = entry.id or entry[1],
                required = entry.supplyRequired or entry.count or entry[2],
                available = entry.availableCount,
            }
            if entry.unavailable then
                result.feasible = false
                result.status = "recalculate_required"
            end
        end
    end
    return result
end

function RA.NPCSellPriceOf(itemID)
    if type(itemID) ~= "number" or not (itemID > 0 and itemID < math.huge) then return nil end
    local hit = sellCache[itemID]
    if hit then return hit end
    local p
    local rec = getRecovery()
    if rec and type(rec.NPCSellPriceOf) == "function" then
        local ok, v = pcall(rec.NPCSellPriceOf, itemID)
        if ok and type(v) == "number" and v >= 0 and v < math.huge then p = v end
    end
    if not p then
        local DS = getDS()
        local item = DS and type(DS.Item) == "function" and DS.Item(itemID) or nil
        if type(item) == "table" and type(item.sellPriceCopper) == "number" and item.sellPriceCopper >= 0 and item.sellPriceCopper < math.huge then
            p = math.floor(item.sellPriceCopper)
        end
    end
    local ci = _G.C_Item
    if not p and type(ci) == "table" and type(ci.GetItemInfo) == "function" then
        local ok, _, _, _, _, _, _, _, _, _, _, sell = pcall(ci.GetItemInfo, itemID)
        if ok and type(sell) == "number" and sell > 0 and sell < math.huge then p = sell end
    end
    if not p and type(_G.GetItemInfo) == "function" then
        local ok, _, _, _, _, _, _, _, _, _, _, sell = pcall(_G.GetItemInfo, itemID)
        if ok and type(sell) == "number" and sell > 0 and sell < math.huge then p = sell end
    end
    if not p and type(ci) == "table" and type(ci.GetItemSellPrice) == "function" then
        local ok, sell = pcall(ci.GetItemSellPrice, itemID)
        if ok and type(sell) == "number" and sell > 0 and sell < math.huge then p = sell end
    end
    if p then sellCache[itemID] = p end
    return p
end

function RA.NPCBuyPriceOf(itemID, ctx)
    if type(itemID) ~= "number" or itemID <= 0 then return nil end
    return pureVendorUnit(itemID, ctx)
end

function RA.NPCBuySupplierOf(itemID, ctx)
    if type(itemID) ~= "number" or itemID <= 0 then return nil end
    local vp = RA.VendorPrice(itemID, ctx)
    local npc = vp and vp.npcID
    if not npc then return nil end
    local DS = getDS()
    local name = DS and type(DS.RawText) == "function" and DS.RawText("npc", npc) or nil
    if type(name) ~= "string" or name == "" then return nil end
    return name
end

local function ClientKnown(id)
    local h = getHost()
    local dg = type(h) == "table" and h.DG or nil
    if dg and type(dg.ItemInfo) == "function" then
        local ok, info = pcall(dg.ItemInfo, id)
        if ok then return info ~= nil end
    end
    local ci = _G.C_Item
    if type(ci) == "table" and type(ci.GetItemInfo) == "function" then
        local ok, info = pcall(ci.GetItemInfo, id)
        if ok then return info ~= nil end
    end
    return true
end

function RA.MatListCost(mats, ctx)
    if type(mats) ~= "table" or #mats == 0 then return nil, 0, 0 end
    local total, unpriced = 0, 0
    for _, m in ipairs(mats) do
        local id = type(m) == "table" and (m[1] or m.id or m.itemID) or nil
        local cnt = type(m) == "table" and (m[2] or m.cnt or m.count or 1) or 1
        local p = id and RA.MatPriceOf(id, ctx) or nil
        if p and type(cnt) == "number" and cnt >= 0 and cnt < math.huge then
            local add = p * cnt
            if add >= 0 and add < math.huge then
                total = total + add
            else
                unpriced = unpriced + 1
            end
        else
            unpriced = unpriced + 1
        end
    end
    return total, unpriced, #mats
end

if type(RA.Cancel) ~= "function" then
    function RA.Cancel(slug)
        local sr = ns.ProfSolverRun or (type(gns) == "table" and gns.ProfSolverRun) or nil
        if not (sr and type(sr.Stop) == "function") then return false end
        if slug and type(sr.Running) == "function" and not sr.Running(slug) then return false end
        sr.Stop(slug)
        return true
    end
end

local function RequestProduct(id)
    local h = getHost()
    local dg = type(h) == "table" and h.DG or nil
    if dg and type(dg.RequestItem) == "function" then pcall(dg.RequestItem, id) end
end

local function SnapshotSec()
    local bridge = getAuctionBridge()
    if bridge and type(bridge.FullScanSnapshotStatus) == "function" then
        local snapshot = bridge.FullScanSnapshotStatus()
        local stamp = snapshot and snapshot.status == "available" and tonumber(snapshot.observedAt)
        if stamp and stamp > 0 then
            return math.max(0, nowSec() - stamp)
        end
    end
    local A = _G.Auctionator
    local st = (type(A) == "table") and A.SavedState or nil
    if type(st) ~= "table" then return nil end
    local best
    for _, k in ipairs({ "TimeOfLastGetAllScan", "TimeOfLastReplicateScan", "TimeOfLastBrowseScan" }) do
        local v = tonumber(st[k])
        if v and v > 0 and (not best or v > best) then best = v end
    end
    if not best then return nil end
    local age = nowSec() - best
    if age < 0 then return nil end
    return age
end

function RA.HasPriceData()
    if priceCache.__any then return true end
    local eb = getEasyBridge()
    if eb and type(eb.Available) == "function" and eb.Available() then return true end
    local ab = getAuctionBridge()
    if ab and type(ab.Available) == "function" and ab.Available() then
        local snap = type(ab.FullScanSnapshotStatus) == "function" and ab.FullScanSnapshotStatus()
        if snap and snap.status == "available" then return true end
    end
    local supply = getSupply()
    return (supply and type(supply.Ready) == "function" and supply.Ready()) and true or false
end

function RA.SnapshotAge()
    return SnapshotSec()
end

local ICON_G = "|TInterface\\MoneyFrame\\UI-GoldIcon:0|t"
local ICON_S = "|TInterface\\MoneyFrame\\UI-SilverIcon:0|t"
local ICON_C = "|TInterface\\MoneyFrame\\UI-CopperIcon:0|t"

function RA.StepConsumeCost(st, ctx)
    if type(st) ~= "table" then return nil end
    local rec = st.recipe
    local mats = rec and (rec.mats or rec[12]) or st.mats
    if type(mats) ~= "table" then return nil end
    local count = tonumber(st[4]) or 0
    if type(count) ~= "number" or not (count > 0 and count < math.huge) then return nil end
    local total, priced = 0, 0
    for _, m in ipairs(mats) do
        local id = type(m) == "table" and (m[1] or m.id or m.itemID) or nil
        local qty = type(m) == "table" and (m[2] or m.count or 1) or 1
        if type(id) == "number" and type(qty) == "number" and qty > 0 and qty < math.huge then
            local p = RA.MatPriceOf(id, ctx)
            if p then
                local add = p * qty * count
                if add >= 0 and add < math.huge then
                    total = total + add
                    priced = priced + 1
                end
            end
        end
    end
    if priced == 0 then return nil end
    return total, priced < #mats
end

function RA.MoneyStr(copper, opt)
    copper = tonumber(copper)
    if type(copper) ~= "number" or not (copper > -math.huge and copper < math.huge) then
        return "0" .. ICON_C
    end
    if copper < 0 then
        return "-" .. RA.MoneyStr(-copper, opt)
    end
    if copper <= 0 then
        return "0" .. ICON_C
    end
    if opt == "copper" then
        local g = math.floor(copper / 10000)
        local s = math.floor(copper / 100) % 100
        local c = copper % 100
        if g > 0 then
            return format("%d%s%02d%s%02d%s", g, ICON_G, s, ICON_S, c, ICON_C)
        end
        return format("%d%s%02d%s", s, ICON_S, c, ICON_C)
    end
    local g = math.floor(copper / 10000)
    local s = math.floor(copper / 100) % 100
    local c = copper % 100
    if g > 0 then
        return format("%d%s%02d%s%02d%s", g, ICON_G, s, ICON_S, c, ICON_C)
    end
    if s > 0 then
        return format("%d%s%02d%s", s, ICON_S, c, ICON_C)
    end
    return format("%d%s", c, ICON_C)
end

function RA.MoneyStrTip(copper)
    copper = tonumber(copper)
    if type(copper) ~= "number" or not (copper > -math.huge and copper < math.huge) then return "—" end
    if copper < 0 then return "-" .. RA.MoneyStrTip(-copper) end
    if copper <= 0 then return "0" .. ICON_C end
    local g = math.floor(copper / 10000)
    local s = math.floor(copper / 100) % 100
    local c = copper % 100
    if g > 0 then
        return format("%d %s%02d %s%02d%s", g, ICON_G, s, ICON_S, c, ICON_C)
    end
    if s > 0 then
        return format("%d %s%02d%s", s, ICON_S, c, ICON_C)
    end
    return format("%d%s", c, ICON_C)
end

local function Gain(skill, c)
    if skill < c.learn or (c.orange and skill < c.orange) or skill >= c.grey then return nil end
    if skill < c.yellow then return 1.0 end
    local gYellow, gGreen = cfgDiffRates()
    if skill < c.green then
        local span = c.green - c.yellow
        if span <= 0 then return gYellow end
        local t = (skill - c.yellow) / span
        return 1.0 - t * (1.0 - gYellow)
    end
    local span = c.grey - c.green
    if span <= 0 then return gGreen end
    local t = (skill - c.green) / span
    return gYellow - t * (gYellow - gGreen)
end

local function LearnKnown(spell)
    if type(_G.IsSpellKnown) == "function" then
        local ok, v = pcall(_G.IsSpellKnown, spell)
        if ok and v then return true end
    end
    if type(_G.IsPlayerSpell) == "function" then
        local ok, v = pcall(_G.IsPlayerSpell, spell)
        if ok and v then return true end
    end
    return false
end

function RA.SpellKnown(spell)
    return LearnKnown(spell)
end

local rtGate = 0
local function RouteTick()
    if not coroutine.running() then return end
    if type(_G.debugprofilestop) ~= "function" then return end
    local ok, now = pcall(_G.debugprofilestop)
    if ok and type(now) == "number" and (now - rtGate) >= 1 then
        rtGate = now
        coroutine.yield()
    end
end

local function decodeDSRow(row, slug, spell)
    local E = getEconomy()
    if E and type(E.Normalize) == "function" then
        local ok, resolved = pcall(E.Normalize, row, slug, "ds", spell)
        if ok and resolved then
            if type(E.AttachLearningInfo) == "function" then
                pcall(E.AttachLearningInfo, resolved, LearnKnown(resolved.spell))
            end
            return resolved
        end
        if ok then return nil end
    end
    if type(row) ~= "table" then return nil end
    if row.availability ~= nil and row.availability ~= "live" then return nil end
    if row.nip == true then return nil end
    local s = spell or row.spell or row.spellID or row[1]
    if type(s) ~= "number" or s <= 0 then return nil end
    local mats = {}
    if type(row.mats) == "table" then
        for i = 1, #row.mats do
            local m = row.mats[i]
            if type(m) == "table" then mats[#mats + 1] = { m[1] or m.itemID or m.id, m[2] or m.count or 1 } end
        end
    elseif type(row.reagents) == "table" then
        for i = 1, #row.reagents do
            local m = row.reagents[i]
            if type(m) == "table" then mats[#mats + 1] = { m.itemID or m.id or m[1], m.count or m.amount or m[2] or 1 } end
        end
    elseif type(row[12]) == "table" then
        for i = 1, #row[12] do
            local m = row[12][i]
            if type(m) == "table" then mats[#mats + 1] = { m[1], m[2] or 1 } end
        end
    end
    local item = row.item or row.outputItemID or row.makes or row[2]
    local count = tonumber(row.count or row.outputCountMin or row.outputMin or row[3]) or (item and 1 or 0)
    local learn = tonumber(row.learn or row.learnedAt or row[7])
    local yellow = tonumber(row.yellow or row[8]) or learn
    local green = tonumber(row.green or row[9]) or yellow
    local grey = tonumber(row.grey or row[10])
    return {
        spell = s,
        spellID = s,
        profession = slug or row.profession,
        item = item,
        outputItemID = item,
        makes = item,
        count = count,
        outputMin = tonumber(row.outputMin or row.outputCountMin) or count,
        outputMax = tonumber(row.outputMax or row.outputCountMax) or count,
        learn = learn,
        orange = tonumber(row.orange),
        yellow = yellow,
        green = green,
        grey = grey,
        mats = mats,
        formula = row.formula or row.formulaID or (type(row[13]) == "table" and row[13][1] or nil),
        formulaID = row.formulaID or row.formula,
        category = row.category or row.categoryKey or row[4],
        cooldown = (type(row.cooldownSeconds) == "number" and row.cooldownSeconds > 0) or row.cooldown or nil,
        availability = row.availability or "live",
        requiredAbilityID = row.requiredAbilityID,
        [1] = s,
        [2] = item,
        [3] = count,
        [4] = row.category or row.categoryKey or row[4],
        [7] = learn,
        [8] = yellow,
        [9] = green,
        [10] = grey,
        [12] = mats,
    }
end

local function stampLegacyIndices(rec)
    if type(rec) ~= "table" then return rec end
    if rec[1] == nil then rec[1] = rec.spell or rec.spellID end
    if rec[2] == nil then rec[2] = rec.item or rec.outputItemID or rec.makes end
    if rec[3] == nil then rec[3] = rec.count or rec.outputCountMin or rec.outputMin end
    if rec[4] == nil then rec[4] = rec.category or rec.categoryKey end
    if rec[7] == nil then rec[7] = rec.learn or rec.learnedAt end
    if rec[8] == nil then rec[8] = rec.yellow end
    if rec[9] == nil then rec[9] = rec.green end
    if rec[10] == nil then rec[10] = rec.grey end
    if rec[12] == nil then rec[12] = rec.mats end
    if rec.makes == nil then rec.makes = rec[2] end
    return rec
end

local function loadCatalogRecipes(slug)
    local DS = getDS()
    if not DS or type(DS.Recipes) ~= "function" then return nil end
    local bucket = DS.Recipes(slug)
    if type(bucket) ~= "table" or type(bucket.recipes) ~= "table" then return nil end
    local spells = {}
    for spell, row in pairs(bucket.recipes) do
        if type(spell) == "number" and type(row) == "table" then
            spells[#spells + 1] = spell
        end
    end
    table.sort(spells)
    return { recipes = bucket.recipes, spells = spells }
end

function RA.LearningDiagnostic(code, recipe, detail)
    detail = type(detail) == "table" and detail or {}
    local route = detail.route or {}
    local reasons = {}
    for _, reason in ipairs(detail.missingReasons or {}) do reasons[#reasons + 1] = reason end
    local items = {}
    for _, id in ipairs(detail.missingItemIDs or {}) do items[#items + 1] = id end
    return {
        code = code or "learningDataMissing",
        recipe = recipe and recipe.key,
        spell = recipe and (recipe.spell or recipe.spellID or recipe[1]),
        profession = recipe and recipe.profession,
        item = detail.teachingItemID or route.teachingItemID or route.itemID
            or recipe and (recipe.formula or recipe.formulaID),
        routeId = detail.routeId or route.id,
        coverage = detail.coverage,
        missingReasons = reasons,
        missingItemIDs = items,
        learningStatus = detail.status,
    }
end

local function sourceGap(code, detail)
    return code == "learningDataMissing" or code == "learningRequirementsUnknown"
        or (detail and type(detail.missingReasons) == "table" and #detail.missingReasons > 0)
end

local function FormulaQuote(rec, slug, opts)
    local E = getEconomy()
    if not (E and E.FormulaFor and E.Normalize) then return nil end
    local recipe = rec.learningRecipe or (rec.catalogue and rec) or nil
    if not recipe then
        local okN, norm = pcall(E.Normalize, rec, slug, "ds", rec.spell or rec[1])
        if okN then recipe = norm end
    end
    if not recipe then return nil end
    if E.AttachLearningInfo and not (opts and opts.snapshot) then
        pcall(E.AttachLearningInfo, recipe, LearnKnown(recipe.spell))
    end
    local context = { profession = slug }
    for key, value in pairs(opts or {}) do context[key] = value end
    local remaining = context.auctionRemaining and context.auctionRemaining[recipe.formula or recipe.formulaID]
    local okF, q = pcall(E.FormulaFor, recipe, context, remaining)
    if okF then return q end
    return nil
end

local function BuildCandidates(slug, opts)
    opts = opts or {}
    local specBlocked = 0
    local learningGaps, gapSeen = {}, {}
    local E = getEconomy()
    local function checkLearning(rec, spell)
        if not (E and E.RouteRecipeEligibility) then return true end
        local okCall, ok, reason, detail = pcall(E.RouteRecipeEligibility, rec, opts.snapshot)
        if not okCall then
            if not gapSeen[spell] then
                gapSeen[spell] = true
                learningGaps[#learningGaps + 1] = RA.LearningDiagnostic("clientDataPending", rec)
            end
            return false
        end
        if not ok and sourceGap(reason, detail) and not gapSeen[spell] then
            gapSeen[spell] = true
            learningGaps[#learningGaps + 1] = RA.LearningDiagnostic(reason, rec, detail)
        end
        return ok
    end

    local catalog = loadCatalogRecipes(slug)
    if not catalog then return nil end

    local vendorCtx = buildVendorCtx(opts)
    local cands, recOf = {}, {}
    for _, spell in ipairs(catalog.spells) do
        RouteTick()
        local raw = catalog.recipes[spell]
        local rec = decodeDSRow(raw, slug, spell)
        if rec then
            stampLegacyIndices(rec)
            local learn, yellow, green, grey = rec.learn, rec.yellow, rec.green, rec.grey
            local reagents = rec.mats
            if type(spell) == "number" and type(learn) == "number"
                and type(grey) == "number" and grey > learn
                and type(reagents) == "table" and (#reagents > 0 or skipEconomy(slug)) then
                local ok = not rec.clientUnavailable and not rec.clientPending and not rec.cooldown and not rec.cooldownUnknown
                if ok and not checkLearning(rec, spell) then
                    ok = false
                    specBlocked = specBlocked + 1
                end
                local formulaFacade = E and E.FormulaFor and E.Normalize
                local formula = FormulaQuote(rec, slug, opts)
                if formula and not formula.usable then ok = false end
                if ok then
                    local cost, unpriced = 0, false
                    for _, m in ipairs(reagents) do
                        local p
                        if opts.snapshot then
                            local entries, qcost = RA.MaterialPurchases(m[1], 1, opts)
                            if entries[1] and not entries[1].unpriced then p = qcost end
                        else
                            p = RA.MatPriceOf(m[1], vendorCtx)
                        end
                        if p then
                            cost = cost + p * (m[2] or 1)
                        else
                            unpriced = true
                        end
                    end
                    local itemID = rec.item or rec[2]
                    local f = rec.formula or rec.formulaID or (type(rec[13]) == "table" and rec[13][1] or nil)
                    local fcost, funpriced = 0, false
                    if formula and not formula.known then
                        fcost = formula.cost or 0
                        funpriced = formula.unpriced or formula.cost == nil
                    elseif type(f) == "number" and not LearnKnown(spell) then
                        if formulaFacade then
                            fcost = formula and formula.cost or 0
                            funpriced = formula and formula.unpriced or false
                        else
                            local fp = RA.MatPriceOf(f, vendorCtx)
                            if fp then fcost = fp else funpriced = true end
                        end
                    end
                    local base, unknown = 0, false
                    for _, m in ipairs(reagents) do
                        if not ClientKnown(m[1]) then unknown = true end
                        local sp = RA.NPCSellPriceOf(m[1])
                        if sp then base = base + sp * (m[2] or 1) end
                    end
                    local cY = (type(yellow) == "number") and yellow or learn
                    cands[#cands + 1] = {
                        spell = spell,
                        item = (type(itemID) == "number") and itemID or nil,
                        learn = learn,
                        orange = rec.orange,
                        yellow = cY,
                        green = (type(green) == "number") and green or cY,
                        grey = grey,
                        mats = reagents,
                        cost = cost,
                        unpriced = unpriced,
                        fcost = fcost,
                        funpriced = funpriced or nil,
                        base = base,
                        cd = (rec.category == "Transmutes" or rec.categoryKey == "transmutes") or nil,
                        learningCostKnown = formula ~= nil,
                        learningUsable = formula and formula.usable,
                        unknown = unknown or nil,
                        learnO = math.max(1, math.min(learn, cY - 25)),
                    }
                    recOf[spell] = rec
                end
            end
        end
    end

    local pol
    if E and type(E.GetPolicies) == "function" then
        local ok, v = pcall(E.GetPolicies, slug)
        if ok and type(v) == "table" then pol = v end
    end
    if pol and next(pol) then
        local kept = {}
        for _, c in ipairs(cands) do
            if pol[slug .. ":" .. tostring(c.spell)] ~= "ban" and pol[c.spell] ~= "ban" then
                kept[#kept + 1] = c
            end
        end
        cands = kept
    end

    local G = getGates()
    if (G and not opts.ignoreSpecGate) or (E and E.RouteRecipeEligibility) then
        local kept, blocked = {}, 0
        for _, c in ipairs(cands) do
            local allowed, need = true, nil
            if G and not opts.ignoreSpecGate and type(G.Allowed) == "function" then
                local okG, a, n = pcall(G.Allowed, slug, c.spell)
                if okG then
                    allowed, need = a, n
                else
                    allowed, need = false, "clientDataPending"
                end
            end
            if allowed and E and E.RouteRecipeEligibility and E.FindRecipe then
                local recipe = recOf[c.spell]
                local okR = true
                if not recipe then
                    local r
                    okR, r = pcall(E.FindRecipe, slug, c.spell)
                    if okR then recipe = r end
                end
                if not okR then
                    allowed, need = false, "clientDataPending"
                elseif recipe then
                    local okE, a, n = pcall(E.RouteRecipeEligibility, recipe, opts.snapshot)
                    if okE then
                        allowed, need = a, n
                    else
                        allowed, need = false, "clientDataPending"
                    end
                end
            end
            if allowed then
                if G and type(G.TrainerTaught) == "function" then
                    local okT, taught = pcall(G.TrainerTaught, c.spell)
                    if okT and taught then
                        if not c.learningCostKnown then c.fcost = 0; c.funpriced = nil end
                        c.taughtByTrainer = true
                    end
                end
                kept[#kept + 1] = c
            else
                blocked = blocked + 1
                c.specBlocked = need
            end
        end
        cands = kept
        specBlocked = specBlocked + blocked
    end
    table.sort(learningGaps, function(a, b) return (a.spell or 0) < (b.spell or 0) end)
    return cands, recOf, specBlocked, learningGaps
end

local function Eligible(c, allowUnpriced)
    return allowUnpriced or c.learningUsable or (not c.funpriced)
end

local function CanUse(scheme, c, cur)
    local lo = (scheme == "optim") and (c.learnO or c.learn) or c.learn
    if c.orange and lo == c.learn and c.orange > lo then lo = c.orange end
    return cur >= lo and cur < c.grey
end

local function Usable(scheme, c, cur, allowUnpriced)
    if (scheme == "optim") and (c.cd or c.unknown) then return false end
    if not Eligible(c, allowUnpriced) then return false end
    return CanUse(scheme, c, cur)
end

local function GainOf(scheme, c, cur)
    if not CanUse(scheme, c, cur) then return nil end
    if scheme == "optim" then return 1 end
    return Gain(cur, c)
end

local function MetricOf(scheme, c, g)
    if scheme == "cheapest" then
        local span = math.max(1, (c.grey or 0) - (c.learn or 0))
        return c.cost / g + (c.fcost or 0) / span
    end
    if scheme == "crafts" then return 1 / g end
    if scheme == "optim" then return (c.base or 0) / g end
    return c.cost / g
end

local function Simulate(cands, start, cap, allowUnpriced, scheme)
    local steps, gaps = {}, {}
    local banned, segRun = {}, {}
    local cur = math.max(1, math.min(cap - 1, start or 1))
    local guard = 0
    local maxPer = cfgMaxPerRecipe()

    while cur < cap do
        RouteTick()
        guard = guard + 1
        if guard > 4000 then break end

        local best, bestMetric
        for _, c in ipairs(cands) do
            if not banned[c.spell] and Usable(scheme, c, cur, allowUnpriced) then
                local g = GainOf(scheme, c, cur)
                if g then
                    local metric = MetricOf(scheme, c, g)
                    if not best or metric < bestMetric - 1e-9
                        or (metric < bestMetric + 1e-9 and c.grey > best.grey) then
                        best, bestMetric = c, metric
                    end
                end
            end
        end

        if not best then
            local nxt
            for _, c in ipairs(cands) do
                if not banned[c.spell] and Eligible(c, allowUnpriced)
                    and not ((scheme == "optim") and (c.cd or c.unknown)) then
                    local lo = (scheme == "optim") and (c.learnO or c.learn) or c.learn
                    if lo > cur and (not nxt or lo < nxt) then nxt = lo end
                end
            end
            if nxt and nxt < cap then
                gaps[#gaps + 1] = { cur, nxt - 1 }
                cur = nxt
            else
                if cur < cap then gaps[#gaps + 1] = { cur, cap - 1 } end
                cur = cap
            end
        else
            local from = cur
            local crafts = 0
            while cur < cap do
                local g = Gain(cur, best)
                if not g then break end
                crafts = crafts + 1 / g
                cur = cur + 1
                local stop = false
                for _, c in ipairs(cands) do
                    if c ~= best and not banned[c.spell] and Usable(scheme, c, cur, allowUnpriced) then
                        local g2 = GainOf(scheme, c, cur)
                        if g2 and MetricOf(scheme, c, g2) < bestMetric - 1e-9 then
                            stop = true
                            break
                        end
                    end
                end
                if stop then break end
            end
            local qty = math.max(1, math.ceil(crafts - 1e-9))
            local last = steps[#steps]
            if last and last[3] == best.spell and last[2] + 1 == from then
                last[2] = cur - 1
                last[4] = last[4] + qty
                last.cost = last.cost + best.cost * qty
            else
                steps[#steps + 1] = {
                    from, cur - 1, best.spell, qty,
                    cost = best.cost * qty, item = best.item,
                    unpriced = best.unpriced,
                }
                segRun[best.spell] = (segRun[best.spell] or 0) + 1
                if segRun[best.spell] >= maxPer then banned[best.spell] = true end
            end
        end
    end
    return steps, gaps
end

local function SimulateRange(cands, a, b, scheme, allowUnpriced)
    local steps = {}
    local banned, segRun = {}, {}
    local cur = a
    local guard = 0
    local maxPer = cfgMaxPerRecipe()
    while cur <= b do
        RouteTick()
        guard = guard + 1
        if guard > 1000 then break end
        local best, bestMetric
        for _, c in ipairs(cands) do
            if not banned[c.spell] and Usable(scheme, c, cur, allowUnpriced) then
                local g = GainOf(scheme, c, cur)
                if g then
                    local metric = MetricOf(scheme, c, g)
                    if not best or metric < bestMetric - 1e-9
                        or (metric < bestMetric + 1e-9 and c.grey > best.grey) then
                        best, bestMetric = c, metric
                    end
                end
            end
        end
        if not best then
            local nxt
            for _, c in ipairs(cands) do
                if not banned[c.spell] and Eligible(c, allowUnpriced)
                    and not ((scheme == "optim") and (c.cd or c.unknown)) then
                    local lo = (scheme == "optim") and (c.learnO or c.learn) or c.learn
                    if lo > cur and lo <= b and (not nxt or lo < nxt) then nxt = lo end
                end
            end
            if not nxt then break end
            cur = nxt
        else
            local from = cur
            local crafts = 0
            while cur <= b do
                local g = Gain(cur, best)
                if not g then break end
                crafts = crafts + 1 / g
                cur = cur + 1
                local stop = false
                for _, c in ipairs(cands) do
                    if c ~= best and not banned[c.spell] and cur <= b
                        and Usable(scheme, c, cur, allowUnpriced) then
                        local g2 = GainOf(scheme, c, cur)
                        if g2 and MetricOf(scheme, c, g2) < bestMetric - 1e-9 then
                            stop = true
                            break
                        end
                    end
                end
                if stop then break end
            end
            local qty = math.max(1, math.ceil(crafts - 1e-9))
            local to = math.min(cur - 1, b)
            local last = steps[#steps]
            if last and last[3] == best.spell and last[2] + 1 == from then
                last[2] = to
                last[4] = last[4] + qty
                last.cost = last.cost + best.cost * qty
            else
                steps[#steps + 1] = {
                    from, to, best.spell, qty,
                    cost = best.cost * qty, item = best.item,
                    unpriced = best.unpriced, est = true,
                }
                segRun[best.spell] = (segRun[best.spell] or 0) + 1
                if segRun[best.spell] >= maxPer then banned[best.spell] = true end
            end
        end
    end
    local coverTo = a - 1
    for _, s in ipairs(steps) do
        if s[1] <= coverTo + 1 then coverTo = math.max(coverTo, s[2]) end
    end
    local resid = (coverTo < b) and { coverTo + 1, b } or nil
    return steps, resid
end

local function MergeSteps(steps)
    local out = {}
    for _, s in ipairs(steps) do
        local last = out[#out]
        if last and last[3] == s[3] and last[2] + 1 == s[1] then
            last[2] = s[2]
            last[4] = last[4] + s[4]
            last.cost = (last.cost or 0) + (s.cost or 0)
            if s.unpriced then last.unpriced = true end
            if s.est then last.est = true end
        else
            out[#out + 1] = s
        end
    end
    return out
end

local function FillGaps(cands, steps, gaps, scheme, allowUnpriced)
    local out = {}
    local si = 1
    for _, g in ipairs(gaps) do
        while si <= #steps and steps[si][2] < g[1] do
            out[#out + 1] = steps[si]
            si = si + 1
        end
        local fills, resid = SimulateRange(cands, g[1], g[2], scheme, allowUnpriced)
        for _, s in ipairs(fills) do out[#out + 1] = s end
        if resid then out[#out + 1] = { gap = resid } end
    end
    while si <= #steps do
        out[#out + 1] = steps[si]
        si = si + 1
    end
    local newSteps, newGaps = {}, {}
    for _, it in ipairs(out) do
        if it.gap then
            newGaps[#newGaps + 1] = it.gap
        else
            newSteps[#newSteps + 1] = it
        end
    end
    return MergeSteps(newSteps), newGaps
end

local function SummarizeCore(steps, recOf, skipLearnedFormulas, specInputs, skipMats, slug, opts)
    local total, crafts = 0, 0
    local productAH, productNPC, productPartial = 0, 0, false
    local mats, firstAt, matPrice, specSet = {}, {}, {}, {}
    local vendorCtx = buildVendorCtx(opts)
    local function quote(id)
        if opts and opts.snapshot then
            local entries, cost = RA.MaterialPurchases(id, 1, opts)
            if entries[1] and not entries[1].unpriced then return cost end
            return nil
        end
        return RA.MatPriceOf(id, vendorCtx)
    end
    for _, st in ipairs(steps) do
        local rec = recOf[st[3]]
        local ml = rec and (rec.mats or rec[12]) or nil
        if st.mats == nil then st.mats = ml end
        if st.item == nil and rec then
            local prod = rec.item or rec[2] or rec.makes
            st.item = prod
        end
        if st.out == nil and rec then
            local n = rec.count or rec[3]
            st.out = n
        end
        if st.cost == nil then
            local sc, unpriced = 0, false
            if ml then
                for _, m in ipairs(ml) do
                    local id = m[1]
                    if not (skipMats and skipMats[id]) then
                        if matPrice[id] == nil then matPrice[id] = quote(id) end
                        local p = matPrice[id]
                        if p then
                            sc = sc + p * (m[2] or 1) * (st[4] or 0)
                        else
                            unpriced = true
                        end
                    end
                end
            end
            st.cost = sc
            st.unpriced = unpriced or nil
        end
        if st.unpriced then
            local code, age, mid, rank = nil, nil, nil, 9
            for _, m in ipairs(ml or {}) do
                local rc, ra = MatReason(m[1], vendorCtx)
                if rc then
                    local rk = (rc == "stale" and 1) or (rc == "norec" and 2) or (rc == "novendor" and 3) or 4
                    if rk < rank or (rk == rank and (ra or 0) > (age or 0)) then
                        rank, code, age, mid = rk, rc, ra, m[1]
                    end
                end
            end
            st.unpricedReason, st.unpricedAge, st.unpricedMat = code, age, mid
        end
        total = total + (st.cost or 0)
        crafts = crafts + (st[4] or 0)
        local prod = rec and (rec.item or rec[2])
        local prodCount = rec and (rec.count or rec[3])
        if type(prod) == "number" and type(prodCount) == "number" and prodCount > 0 then
            local outN = (st[4] or 0) * prodCount
            RequestProduct(prod)
            local ah = RA.AHPriceOf(prod, opts)
            if ah then
                productAH = productAH + ah * outN
            else
                productPartial = true
            end
            local sp = RA.NPCSellPriceOf(prod)
            if sp then productNPC = productNPC + sp * outN end
        elseif type(prod) == "number" then
            productPartial = true
        end
        if ml then
            for _, m in ipairs(ml) do
                local id = m[1]
                if not (skipMats and skipMats[id]) then
                    mats[id] = (mats[id] or 0) + (m[2] or 1) * (st[4] or 0)
                    if not firstAt[id] or st[1] < firstAt[id] then firstAt[id] = st[1] end
                    if matPrice[id] == nil then
                        matPrice[id] = quote(id)
                    end
                end
            end
        end
    end
    if specInputs then
        for _, pair in ipairs(specInputs) do
            local sid, sn = pair[1], tonumber(pair[2]) or 0
            if type(sid) == "number" and sn > 0 then
                mats[sid] = (mats[sid] or 0) + sn
                specSet[sid] = true
                if firstAt[sid] == nil then firstAt[sid] = 0 end
                if matPrice[sid] == nil then matPrice[sid] = quote(sid) end
            end
        end
    end
    local purchaseOpts = {}
    for key, value in pairs(opts or {}) do purchaseOpts[key] = value end
    local remaining = {}
    for id, count in pairs(purchaseOpts.auctionRemaining or {}) do remaining[id] = count end
    purchaseOpts.auctionRemaining = remaining
    local economy = getEconomy()
    local function observe(id)
        if id and remaining[id] == nil and economy and economy.AuctionSupplyOf then
            local ok, supply = pcall(economy.AuctionSupplyOf, purchaseOpts, id)
            if ok and supply then remaining[id] = supply.quantity end
        end
    end
    for id in pairs(mats) do observe(id) end
    local formulas, formulasTotal, formulaVendorTotal = {}, 0, 0
    local paidLearning = {}
    for _, st in ipairs(steps) do
        local rec = recOf[st[3]]
        if rec and not (skipLearnedFormulas and LearnKnown(st[3])) then
            local entry = FormulaQuote(rec, st.profession or slug, purchaseOpts)
            if entry and not entry.known and not entry.automatic then
                local formulaID = entry.id
                local key = formulaID or entry.recipeKey or (st.profession or slug) .. ":" .. tostring(st[3])
                if not paidLearning[key] then
                    paidLearning[key] = true
                    observe(formulaID)
                    entry = RA.PreferSharedFormula(entry, formulaID and mats[formulaID], purchaseOpts)
                    formulas[#formulas + 1] = entry
                    formulasTotal = formulasTotal + (entry.cost or 0)
                    if entry.source == "vendor" or entry.source == "npc" or entry.source == "trainer"
                        or (entry.source == "acquire" and entry.acquisitionKind == "currency") then
                        formulaVendorTotal = formulaVendorTotal + (entry.cost or 0)
                    elseif entry.source == "ah" and remaining[formulaID] ~= nil then
                        remaining[formulaID] = math.max(0, remaining[formulaID] - (entry.count or 1))
                    end
                end
            end
        end
    end
    local list = {}
    for id, n in pairs(mats) do
        local entries, _, complete, reason = RA.MaterialPurchases(id, n, purchaseOpts)
        for _, entry in ipairs(entries) do
            entry.spec = specSet[id] or nil
            if entry.unpriced then entry.reason, entry.age = MatReason(id, vendorCtx) end
            if not complete then entry.costComplete = false; entry.procurementReason = reason end
            list[#list + 1] = entry
        end
    end
    table.sort(list, function(a, b)
        local fa, fb = firstAt[a[1]] or math.huge, firstAt[b[1]] or math.huge
        if fa ~= fb then return fa < fb end
        if a[2] ~= b[2] then return a[2] > b[2] end
        return a[1] < b[1]
    end)
    local vendorTotal = formulaVendorTotal
    total = 0
    for _, e in ipairs(list) do
        total = total + (e.cost or 0)
        if e.vendor then vendorTotal = vendorTotal + (e.cost or 0) end
    end
    return total, crafts, list, firstAt, vendorTotal, formulas, formulasTotal,
        productAH, productNPC, productPartial
end

local function SummarizePoisons(steps, opts)
    opts = opts or {}
    local catalog = loadCatalogRecipes("poisons")
    if not catalog then return nil end
    local recOf = {}
    for _, spell in ipairs(catalog.spells) do
        local rec = decodeDSRow(catalog.recipes[spell], "poisons", spell)
        if rec then
            stampLegacyIndices(rec)
            recOf[spell] = rec
        end
    end
    local vendorCtx = buildVendorCtx(opts)
    local counts, firstAt, prices = {}, {}, {}
    local crafts, productAH, productNPC, productPartial = 0, 0, 0, false
    for _, step in ipairs(steps or {}) do
        local spell = step[3] or step.spell
        local rec = recOf[spell] or step.recipe
        if rec then stampLegacyIndices(rec) end
        local mats = rec and (rec.mats or rec[12]) or {}
        step.mats, step.item, step.out = mats, rec and (rec.item or rec[2]), rec and (rec.count or rec[3])
        step.cost, step.unpriced = 0, nil
        step.unpricedReason, step.unpricedAge, step.unpricedMat = nil, nil, nil
        for _, material in ipairs(mats) do
            local id = material[1]
            local quantity = (material[2] or 1) * (step[4] or 0)
            local price = RA.MatPriceOf(id, vendorCtx)
            prices[id] = price
            counts[id] = (counts[id] or 0) + quantity
            firstAt[id] = math.min(firstAt[id] or math.huge, step[1] or 1)
            if price then
                step.cost = step.cost + price * quantity
            else
                step.unpriced = true
                local rc, ra = MatReason(id, vendorCtx)
                step.unpricedReason = rc or "norec"
                step.unpricedAge = ra
                step.unpricedMat = id
            end
        end
        crafts = crafts + (step[4] or 0)
        local prod = rec and (rec.item or rec[2])
        local prodCnt = rec and (rec.count or rec[3]) or 1
        if type(prod) == "number" then
            local count = prodCnt * (step[4] or 0)
            RequestProduct(prod)
            local auction = RA.AHPriceOf(prod, opts)
            if auction then productAH = productAH + auction * count else productPartial = true end
            productNPC = productNPC + (RA.NPCSellPriceOf(prod) or 0) * count
        end
    end
    local list, total, vendorTotal = {}, 0, 0
    for id, need in pairs(counts) do
        if need > 0 then
            local entries, cost, complete, reason = RA.MaterialPurchases(id, need, opts)
            for _, entry in ipairs(entries) do
                if entry.unpriced then
                    entry.reason = entry.reason or reason or MatReason(id, vendorCtx)
                    entry.age = entry.age or ahAge[id]
                end
                if not complete then entry.costComplete = false end
                list[#list + 1] = entry
                if entry.vendor then vendorTotal = vendorTotal + (entry.cost or 0) end
            end
            total = total + (cost or 0)
        end
    end
    table.sort(list, function(a, b)
        local fa, fb = firstAt[a[1]] or math.huge, firstAt[b[1]] or math.huge
        if fa ~= fb then return fa < fb end
        if a[2] ~= b[2] then return a[2] > b[2] end
        return a[1] < b[1]
    end)
    local result = {
        slug = "poisons",
        steps = steps,
        mats = list,
        firstAt = firstAt,
        matTotal = total,
        total = total,
        vendorTotal = vendorTotal,
        ahTotal = total - vendorTotal,
        formulas = {},
        formulasTotal = 0,
        crafts = crafts,
        productAH = productAH,
        productNPC = productNPC,
        productPartial = productPartial,
        scheme = "fixed",
        considerAuctionSupply = false,
        feasible = #(steps or {}) > 0,
        status = #(steps or {}) > 0 and "complete" or "recalculate_required",
        priced = RA.HasPriceData(),
        snapshotAge = SnapshotSec(),
        snapshotDays = priceCache.__minAge,
        stamp = nowSec(),
    }
    return RA.ApplyRecovery(result, "poisons", opts, recOf)
end

function RA.SummarizeSteps(steps, slug, opts)
    opts = opts or {}
    local economy = getEconomy()
    local hasNIP = false
    if economy and type(economy.StepsHaveNIP) == "function" then
        local ok, v = pcall(economy.StepsHaveNIP, steps)
        if ok and v then hasNIP = true end
    end
    if hasNIP then
        return {
            steps = {},
            executionSteps = {},
            mats = {},
            formulas = {},
            status = "recalculate_required",
            feasible = false,
            targetReached = false,
            completeCost = false,
            costComplete = false,
            diagnostics = { { code = "catalogueFiltered" } },
        }
    end
    if slug == "poisons" then return SummarizePoisons(steps, opts) end
    opts.profession = slug
    if economy and type(economy.ConsiderAuctionSupply) == "function" then
        local ok, v = pcall(economy.ConsiderAuctionSupply, opts)
        if ok then opts.considerAuctionSupply = v end
    end
    local catalog = loadCatalogRecipes(slug)
    local recOf = {}
    if catalog then
        for _, spell in ipairs(catalog.spells) do
            local rec = decodeDSRow(catalog.recipes[spell], slug, spell)
            if rec then
                stampLegacyIndices(rec)
                recOf[spell] = rec
            end
        end
    end
    for _, st in ipairs(steps or {}) do
        local sp = st[3] or st.spell
        if sp and not recOf[sp] and type(st.recipe) == "table" then
            local rec = decodeDSRow(st.recipe, slug, sp)
            if rec then
                stampLegacyIndices(rec)
                recOf[sp] = rec
            end
        end
    end
    if next(recOf) == nil and not catalog then return nil end

    local specInputs
    do
        local G = getGates()
        local cap = tonumber(opts.target) or (steps[#steps] and steps[#steps][2]) or cfgDefaultTarget()
        local goal
        if G and type(G.SpecGoal) == "function" then
            local ok, v = pcall(G.SpecGoal, slug, cap)
            if ok then goal = v end
        end
        if goal and type(goal.inputs) == "table" then specInputs = goal.inputs end
    end
    local total, crafts, list, firstAt, vendorTotal, formulas, formulasTotal,
        productAH, productNPC, productPartial =
        SummarizeCore(steps, recOf, false, specInputs, nil, slug, opts)
    local res = {
        slug = slug,
        steps = steps,
        mats = list,
        firstAt = firstAt,
        matTotal = total,
        formulas = formulas,
        formulasTotal = formulasTotal,
        total = total + formulasTotal,
        vendorTotal = vendorTotal,
        ahTotal = total + formulasTotal - vendorTotal,
        productAH = productAH,
        productNPC = productNPC,
        productPartial = productPartial,
        crafts = crafts,
        scheme = opts.scheme or "fixed",
        priced = RA.HasPriceData(),
        snapshotAge = SnapshotSec(),
        snapshotDays = priceCache.__minAge,
        stamp = nowSec(),
    }
    if economy and type(economy.LearningPolicyFingerprint) == "function" then
        local ok, v = pcall(economy.LearningPolicyFingerprint)
        if ok then res.learningPolicyFingerprint = v end
    end
    for _, entry in ipairs(formulas) do
        if entry.usable == false then
            res.completeCost = false
            res.feasible = false
            res.status = "recalculate_required"
            res.diagnostics = res.diagnostics or {}
            res.diagnostics[#res.diagnostics + 1] = { code = entry.reason or "formulaUnavailable", item = entry.id, spell = entry.spell }
        end
    end
    local blockedSteps = RA.MarkFixedSpecializations(slug, steps, opts)
    if blockedSteps then
        res.blockedSteps = blockedSteps
        res.specBlocked = #blockedSteps
        res.feasible = false
        res.status = "recalculate_required"
        res.diagnostics = {}
        for _, blocked in ipairs(blockedSteps) do
            local diagnostic = blocked.learningDetail or { code = blocked.reason, spell = blocked.spell, profession = slug }
            res.diagnostics[#res.diagnostics + 1] = diagnostic
            if sourceGap(blocked.reason, diagnostic) then
                res.learningGaps = res.learningGaps or {}
                res.learningGaps[#res.learningGaps + 1] = diagnostic
                res.learningCoverageComplete = false
                res.learningComplete = false
                res.completeCost = false
            end
            if blocked.reason == "clientDataPending" then
                res.clientPending = true
                res.completeCost = false
                res.costComplete = false
                res.priced = false
            end
        end
        res.blockingDiagnostics = res.diagnostics
    end
    local _, _, goalRequired = RA.FilterFixedSpecializations(slug, steps, opts)
    if goalRequired then
        res.specializationGoalRequired = true
        res.feasible = false
        res.status = "recalculate_required"
    end
    RA.StampMaterialPurchases(res)
    RA.StampSupply(res, opts)
    RA.ApplyRecovery(res, slug, opts, recOf)
    for _, step in ipairs(res.steps or {}) do
        if not step.clientPending and not step.unpriced and step.attributedCost ~= nil then step.cost = step.attributedCost end
    end
    return res
end

local function ToReached(steps)
    if type(steps) ~= "table" then return steps end
    local out = {}
    for i, st in ipairs(steps) do
        local c = {}
        for k, v in pairs(st) do c[k] = v end
        c[2] = (tonumber(st[2]) or 0) + 1
        out[i] = c
    end
    return out
end

local function synthesizePoisonSteps(start, target)
    local catalog = loadCatalogRecipes("poisons")
    if not catalog or #catalog.spells == 0 then return nil end
    local cands = {}
    for _, spell in ipairs(catalog.spells) do
        local rec = decodeDSRow(catalog.recipes[spell], "poisons", spell)
        if rec and type(rec.learn) == "number" and type(rec.grey) == "number" and rec.grey > rec.learn then
            cands[#cands + 1] = {
                spell = spell,
                item = rec.item,
                learn = rec.learn,
                orange = rec.orange,
                yellow = rec.yellow or rec.learn,
                green = rec.green or rec.yellow or rec.learn,
                grey = rec.grey,
                mats = rec.mats or {},
                cost = 0,
                fcost = 0,
                base = 0,
                learnO = rec.learn,
            }
        end
    end
    if #cands == 0 then return nil end
    local maxGrey = 1
    for _, c in ipairs(cands) do
        if c.grey > maxGrey then maxGrey = c.grey end
    end
    local cap = math.min(target, maxGrey)
    if start >= cap then
        local last = cands[#cands]
        return { { start, start, last.spell, 1, item = last.item, cost = 0 } }
    end
    local steps = Simulate(cands, start, cap, true, "crafts")
    return ToReached(steps)
end

local function fixedPendingResult(slug, start, target)
    local res = {
        slug = slug,
        planVersion = 2,
        mode = "fixed",
        scheme = "fixed",
        start = start,
        target = target,
        steps = {},
        executionSteps = {},
        mats = {},
        formulas = {},
        total = 0,
        matTotal = 0,
        formulasTotal = 0,
        crafts = 0,
        feasible = false,
        targetReached = false,
        clientPending = true,
        completeCost = false,
        costComplete = false,
        status = "recalculate_required",
        diagnostics = { { code = "clientDataPending", profession = slug } },
        stamp = nowSec(),
    }
    if slug == "first-aid" then
        res.referenceOnly = true
    end
    return res
end

local function baseFixedPlan(slug, supplied)
    if type(slug) ~= "string" or slug == "" then return nil end
    local opts = {}
    for key, value in pairs(supplied or {}) do opts[key] = value end
    local cap = cfgCap()
    local target = math.max(1, math.min(cap, math.floor(tonumber(opts.target) or cfgDefaultTarget())))
    local start = math.max(1, math.min(cap, math.floor(tonumber(opts.start) or 1)))
    opts.target, opts.start, opts.scheme, opts.profession = target, start, "fixed", slug
    if slug == "first-aid" then opts.recoveryEnabled = false end

    local steps, clipped = {}, false
    if type(opts.steps) == "table" and #opts.steps > 0 then
        for _, row in ipairs(opts.steps) do
            local from, to = tonumber(row[1]) or 1, tonumber(row[2]) or target
            if slug ~= "poisons" and from >= target and not row.checkpoint then break end
            if from > target then break end
            local copy = {}
            for key, value in pairs(row) do
                if key ~= "cost" and key ~= "unpriced" and key ~= "unpricedReason"
                    and key ~= "unpricedAge" and key ~= "unpricedMat" then
                    copy[key] = value
                end
            end
            if to > target then
                copy[2] = target
                copy[4] = row.checkpoint and 0 or math.max(1, math.ceil((row[4] or 0) * (target - from) / math.max(1, to - from) - 1e-9))
                copy._clip = true
                clipped = true
            end
            steps[#steps + 1] = copy
        end
    elseif slug == "poisons" then
        local synth = synthesizePoisonSteps(start, target)
        if not synth or #synth == 0 then
            return fixedPendingResult(slug, start, target)
        end
        steps = synth
    else
        local cands, _, blockedCount, learningGaps = BuildCandidates(slug, opts)
        if not cands or #cands == 0 then
            if isFixedOnly(slug) then
                return fixedPendingResult(slug, start, target)
            end
            return nil
        end
        local rawSteps, gaps = Simulate(cands, start, target, true, "cheapest")
        if #gaps > 0 then
            rawSteps, gaps = FillGaps(cands, rawSteps, gaps, "cheapest", true)
        end
        if #rawSteps == 0 then
            local pending = fixedPendingResult(slug, start, target)
            if #learningGaps > 0 then
                pending.diagnostics = learningGaps
                pending.learningGaps = learningGaps
            elseif blockedCount > 0 then
                pending.diagnostics = { { code = "specializationRequired", profession = slug } }
            end
            return pending
        end
        steps = ToReached(rawSteps)
    end

    local result = RA.SummarizeSteps(steps, slug, opts)
    if not result then
        if isFixedOnly(slug) then return fixedPendingResult(slug, start, target) end
        return nil
    end
    result.slug = slug
    result.planVersion = result.planVersion or 2
    result.mode, result.scheme, result.target = "fixed", "fixed", target
    if slug == "first-aid" and result.clientPending then result.referenceOnly = true end
    if slug ~= "poisons" then
        local solver = getSolver()
        result.procurementPolicyVersion = (solver and solver.ProcurementPolicyVersion) or 11
    end
    result.start = steps[1] and steps[1][1] or start
    result.clipped = clipped
    if result.feasible == nil then result.feasible = #steps > 0 end
    if result.status == nil then result.status = result.feasible and "complete" or "recalculate_required" end
    return result
end

RA._BaseFixedPlan = baseFixedPlan
if type(RA.FixedPlan) ~= "function" then
    RA.FixedPlan = baseFixedPlan
end

local function RecoverySnapshot(slug, steps, recOf, toolItems, opts)
    local srcSnap = type(opts) == "table" and type(opts.snapshot) == "table" and opts.snapshot or nil
    local snap = {
        slug = slug,
        stamp = (srcSnap and type(srcSnap.stamp) == "number" and srcSnap.stamp) or nowSec(),
        recipes = {},
        byKey = {},
        prices = {},
        sellPrices = {},
        auctionSupply = {},
        nonAuctionable = {},
        retainedToolItems = {},
    }
    for _, st in ipairs(steps or {}) do
        local spell = st[3]
        local rec = type(spell) == "number" and recOf and recOf[spell] or nil
        if rec then
            local key = slug .. ":" .. tostring(spell)
            if not snap.byKey[key] then
                local item = rec.item or rec[2] or rec.makes
                local count = rec.count or rec[3]
                if count == nil and not rec.clientPending then count = 1 end
                local mats = rec.mats or rec[12] or {}
                local row = {
                    profession = slug,
                    spell = spell,
                    key = key,
                    item = (type(item) == "number" and item > 0 and type(count) == "number" and count > 0) and item or nil,
                    count = (type(count) == "number" and count > 0) and count or 0,
                    mats = mats,
                }
                snap.recipes[#snap.recipes + 1] = row
                snap.byKey[key] = row
            end
        end
    end
    for _, r in ipairs(snap.recipes) do
        if r.item then
            local p = RA.AHPriceOf(r.item, opts)
            if type(p) == "number" and p > 0 then snap.prices[r.item] = p end
            local sp = (srcSnap and type(srcSnap.sellPrices) == "table" and srcSnap.sellPrices[r.item])
                or RA.NPCSellPriceOf(r.item)
            if sp then snap.sellPrices[r.item] = sp end
            if srcSnap and type(srcSnap.nonAuctionable) == "table" and srcSnap.nonAuctionable[r.item] then
                snap.nonAuctionable[r.item] = true
            end
        end
    end
    local AB = getAuctionBridge()
    local srcSupply = (srcSnap and type(srcSnap.auctionSupply) == "table" and srcSnap.auctionSupply)
        or (type(opts) == "table" and type(opts.auctionSupply) == "table" and opts.auctionSupply)
        or nil
    local srcHistory = (srcSnap and type(srcSnap.auctionSupplyHistory) == "table" and srcSnap.auctionSupplyHistory)
        or (type(opts) == "table" and type(opts.auctionSupplyHistory) == "table" and opts.auctionSupplyHistory)
        or nil
    local srcDepth = srcSnap and type(srcSnap.auctionDepth) == "table" and srcSnap.auctionDepth or nil
    for _, r in ipairs(snap.recipes) do
        if r.item then
            if snap.auctionSupply[r.item] == nil then
                if srcSupply then
                    snap.auctionSupply[r.item] = srcSupply[r.item]
                elseif AB and AB.GetAuctionSupply then
                    snap.auctionSupply[r.item] = AB.GetAuctionSupply(r.item)
                end
            end
            if srcHistory and srcHistory[r.item] ~= nil then
                snap.auctionSupplyHistory = snap.auctionSupplyHistory or {}
                snap.auctionSupplyHistory[r.item] = srcHistory[r.item]
            end
            if srcDepth and srcDepth[r.item] ~= nil then
                snap.auctionDepth = snap.auctionDepth or {}
                snap.auctionDepth[r.item] = srcDepth[r.item]
            end
        end
    end
    if srcSnap and type(srcSnap.auctionFee) == "table" then
        snap.auctionFee = srcSnap.auctionFee
    end
    for _, id in ipairs(toolItems or {}) do
        snap.retainedToolItems[id] = 1
        snap.nonAuctionable[id] = true
    end
    return snap
end

local function RecoveryOptions(opts, slug)
    opts = opts or {}
    local pcfg = getPricingCfg()
    local defFee = (type(pcfg) == "table" and type(pcfg.DEFAULT_RECOVERY_FEE_PCT) == "number" and pcfg.DEFAULT_RECOVERY_FEE_PCT) or 5
    local enabled = opts.recoveryEnabled
    if enabled == nil then enabled = readSetting("recoveryEnabled", slug, false) end
    local fee = opts.recoveryFeePercent
    if fee == nil then fee = readSettingRaw("recoveryFeePercent", slug, defFee) end
    local residual = opts.residualMass
    if residual == nil then residual = readSetting("autoResidualMass", slug, false) end
    return enabled == true, fee, residual == true
end

function RA.ApplyRecovery(res, slug, opts, recOf)
    RA.StampFormulaCosts(res)
    local R = getRecovery()
    if not res or not R or not R.Apply then return res end
    local enabled, fee, residual = RecoveryOptions(opts, slug)
    local snap = RecoverySnapshot(slug, res.steps, recOf, res.toolItems, opts)
    if type(R.Capture) == "function" then
        pcall(R.Capture, snap, { recoveryEnabled = enabled, recoveryFeePercent = fee, residualMass = residual })
    end
    res.scheme = res.scheme or (opts and opts.scheme) or "fixed"
    pcall(R.Apply, res, snap)
    res.recoveryOptimized = false
    res.recoveryScheme = snap.recovery and snap.recovery.feePercent or nil
    res.recoveryFeeSource = snap.recovery and snap.recovery.feeSource or nil
    if slug ~= "poisons" then
        RA.StampSupply(res, opts)
        RA.StampSpecializations(res, slug, opts, res.recoverySnapshot)
    end
    return res
end

function RA.RecoveryForSteps(res, slug, recOf, opts)
    return RA.ApplyRecovery(res, slug, opts, recOf)
end

local function InjectTools(stepsOut, slug, cap, startLv, recOf)
    local kept = {}
    local G = getGates()
    if not G or type(G.AutoCraftTools) ~= "function" then return kept end
    local okAuto, autoTools = pcall(G.AutoCraftTools, slug)
    if not okAuto then autoTools = readSetting("autoCraftTools", slug, true) end
    if not autoTools then return kept end
    local okGoals, goals = pcall(G.ToolGoals, slug, cap)
    if not okGoals or type(goals) ~= "table" or #goals == 0 then return kept end
    local have = {}
    for _, st in ipairs(stepsOut) do have[st[3]] = true end
    local lo = tonumber(startLv) or 1
    local E = getEconomy()
    for _, goal in ipairs(goals) do
        local P = goal.minSkill or 1
        local required = true
        if E and type(E.RequiredLevelingTool) == "function" then
            local okReq, v = pcall(E.RequiredLevelingTool, slug, goal)
            if okReq then required = v end
        end
        local owned = false
        if type(G.ToolOwned) == "function" then
            local okOwned, vOwned = pcall(G.ToolOwned, goal.item)
            if okOwned then owned = vOwned end
        end
        if required and P >= lo and not have[goal.spell] and recOf[goal.spell] and not owned then
            local at = #stepsOut + 1
            for i, st in ipairs(stepsOut) do
                if (tonumber(st[1]) or 0) >= P then at = i; break end
            end
            table.insert(stepsOut, at, {
                P, P, goal.spell, 1,
                tool = true,
                toolItem = goal.item,
                toolSpell = goal.spell,
                toolBop = goal.bindOnPickup or nil,
            })
            have[goal.spell] = true
            kept[#kept + 1] = goal.item
        end
    end
    return kept
end

function RA.StampToolPolicy(result, targetProfession, unused, snapshot)
    if type(result) ~= "table" then return result end
    local goals = {}
    local s = snapshot or (type(result) == "table" and result.recoverySnapshot) or nil
    if type(s) == "table" then
        for _, goal in ipairs(s.toolGoals or {}) do
            if goal.item then goals[goal.item] = goal end
        end
    end
    for _, listKey in ipairs({ "steps", "executionSteps" }) do
        for _, st in ipairs(result[listKey] or {}) do
            if st.tool and st.toolItem then
                local goal = goals[st.toolItem]
                st.toolBop = st.toolBop or (goal and goal.bindOnPickup) or nil
            end
        end
    end
    for _, m in ipairs(result.mats or {}) do
        if m.id and goals[m.id] then m.tool = true end
    end
    return result
end

local function SpecContext(slug, opts)
    local G = getGates()
    if not (G and G.SpecializationContext) then return nil end
    local options = {}
    for k, v in pairs(opts or {}) do options[k] = v end
    options.profession = slug or options.profession or "engineering"
    if options.target == nil then
        options.target = readTargetSkill(options.profession)
    end
    local ok, ctx = pcall(G.SpecializationContext, options)
    if ok and type(ctx) == "table" then return ctx end
    return nil
end

function RA.StampSpecializations(result, slug, opts, snapshot)
    if type(result) ~= "table" then return result end
    RA.StampToolPolicy(result, slug, opts, snapshot)
    local G = getGates()
    if not (G and G.SpecializationContext) then return result end
    local ctx
    if type(snapshot) == "table" then ctx = snapshot.specializationContext end
    if not ctx then ctx = SpecContext(slug, opts) end
    if not ctx then return result end
    local abilities = {}
    local source = ctx.abilities
    if type(snapshot) == "table" and snapshot.specializationAbilities then
        source = snapshot.specializationAbilities
    end
    for id, known in pairs(source or {}) do
        if known == true then abilities[id] = true end
    end
    local fp = ctx.fingerprint
    if not fp and type(G.SpecFingerprint) == "function" then
        local ok, v = pcall(G.SpecFingerprint, ctx.choice, ctx.abilities, ctx.profession, ctx.choicesByGroup)
        if ok then fp = v end
    end
    result.specializationPolicy = {
        revision = 1,
        profession = slug or (type(snapshot) == "table" and snapshot.targetProfession) or ctx.profession,
        choice = ctx.choice or "none",
        fingerprint = fp or "",
        actualAbilities = abilities,
        selectionConflict = ctx.selectionConflict == true,
    }
    return result
end

function RA.SpecializationPlanChanged(result, slug, opts)
    if type(result) ~= "table" then return false end
    local G = getGates()
    if not (G and G.SpecializationContext) then return false end
    local policy = result.specializationPolicy
    local prof = slug
    if not prof and policy then prof = policy.profession end
    local ctx = SpecContext(prof, opts)
    if not ctx then return false end
    if not policy then return ctx.choice ~= "none" end
    local fp = ctx.fingerprint
    if not fp and type(G.SpecFingerprint) == "function" then
        local ok, v = pcall(G.SpecFingerprint, ctx.choice, ctx.abilities, ctx.profession, ctx.choicesByGroup)
        if ok then fp = v end
    end
    if policy.revision ~= 1 or policy.fingerprint ~= (fp or "") then return true end
    for id in pairs(policy.actualAbilities or {}) do
        if (ctx.abilities or {})[id] ~= true then return true end
    end
    if ctx.profession == "engineering" and ctx.selectionConflict and not policy.selectionConflict then
        return true
    end
    return false
end

function RA.FilterFixedSpecializations(slug, steps, opts)
    local G = getGates()
    local E = getEconomy()
    local filtered, blocked = {}, {}
    if not (E and E.LearningEligibility) and not (G and G.LearningEligibility) then
        for _, st in ipairs(steps or {}) do filtered[#filtered + 1] = st end
        return filtered, blocked, false
    end
    local ctx = SpecContext(slug, opts)
    for _, st in ipairs(steps or {}) do
        local spell = st[3] or st.spell
        local allowed, reason, detail, recipe = true, nil, nil, nil
        if spell and spell ~= 0 and not st.checkpoint then
            local profession = st.profession or slug
            if E and type(E.FindRecipe) == "function" then
                local okR, r = pcall(E.FindRecipe, profession, spell)
                if okR then recipe = r end
            end
            recipe = recipe or st.recipe
            if recipe and #(recipe.requiredDataUnknown or {}) > 0 then
                local onlyLearn = true
                for _, field in ipairs(recipe.requiredDataUnknown) do
                    if field ~= "learn" then onlyLearn = false end
                end
                allowed, reason = false, onlyLearn and "learningRequirementsUnknown" or "clientDataPending"
            elseif recipe and (recipe.cooldown or recipe.cooldownUnknown) then
                allowed, reason = false, recipe.cooldown and "cooldown" or "cooldownUnknown"
            elseif recipe and E and E.LearningEligibility then
                local fn = E.RouteRecipeEligibility or E.LearningEligibility
                local okE, a, r, d = pcall(fn, recipe, opts and opts.snapshot)
                if okE then
                    allowed, reason, detail = a, r, d
                else
                    allowed, reason = false, "clientDataPending"
                end
            elseif E and E.FindRecipe then
                allowed, reason = false, "clientDataPending"
            elseif G and G.LearningEligibility then
                local okG, a, r = pcall(G.LearningEligibility, spell)
                if okG then
                    allowed, reason = a, r
                else
                    allowed, reason = false, "clientDataPending"
                end
            end
        end
        if allowed then
            filtered[#filtered + 1] = st
        else
            blocked[#blocked + 1] = {
                spell = spell,
                from = st[1],
                to = st[2],
                learningDetail = detail and RA.LearningDiagnostic(reason, recipe, detail),
                reason = reason or "specializationRequired",
            }
        end
    end
    local goalRequired = false
    if ctx and #(ctx.goals or {}) > 0 then goalRequired = true end
    return filtered, blocked, goalRequired
end

function RA.MarkFixedSpecializations(slug, steps, opts)
    local _, blocked = RA.FilterFixedSpecializations(slug, steps, opts)
    for _, st in ipairs(steps or {}) do st.specBlocked = nil end
    if #blocked == 0 then return nil end
    local bySpell = {}
    for _, b in ipairs(blocked) do
        if b.spell then bySpell[b.spell] = b.reason end
    end
    for _, st in ipairs(steps or {}) do
        st.specBlocked = bySpell[st[3] or st.spell]
    end
    return blocked
end

function RA.StampSupply(result, context)
    if type(result) ~= "table" then return result end
    local economy = getEconomy()
    if economy and type(economy.SummarizeFormulaSupply) == "function" then
        pcall(economy.SummarizeFormulaSupply, result, context)
    end
    local consider = false
    if economy and type(economy.ConsiderAuctionSupply) == "function" then
        local ok, v = pcall(economy.ConsiderAuctionSupply, context)
        if ok and v then consider = true end
    end
    result.considerAuctionSupply = consider
    if not result.considerAuctionSupply then
        result.auctionSupplyUnknown = nil
        for _, entry in ipairs(result.mats or {}) do entry.considerAuctionSupply = false end
        for _, entry in ipairs(result.formulas or {}) do
            entry.considerAuctionSupply = entry.source == "ah" or entry.source == "auction"
        end
        return result
    end
    local AB = getAuctionBridge()
    local unknown = 0
    local now = nowSec()
    local snapSupply = (type(context) == "table") and context.auctionSupply or nil
    local snapHistory = (type(context) == "table") and context.auctionSupplyHistory or nil
    local snapPriceAt = (type(context) == "table") and context.priceObservedAt or nil
    local function SupplyOf(id)
        local rec = snapSupply and snapSupply[id] or nil
        if rec == nil and not snapSupply and AB and AB.GetAuctionSupply then
            rec = AB.GetAuctionSupply(id)
        end
        return rec
    end
    for _, e in ipairs(result.mats or {}) do
        e.considerAuctionSupply = true
        local mid = e.id or e[1]
        if mid and not e.vendor and (e.source == nil or e.source == "ah") then
            local rec = SupplyOf(mid)
            local forced = AB and AB.ForceExpiredActive and AB.ForceExpiredActive()
            if rec and rec.complete and rec.source == "client-auction-results"
                and type(rec.quantity) == "number" and rec.observedAt > 0
                and rec.observedAt <= now
                and (forced or now - rec.observedAt <= RA.MaxAuctionSupplyAgeSeconds()) then
                e.source = e.source or "ah"
                e.availableCount = rec.quantity
                e.supplyObserved = true
                e.supplyObservedAt = rec.observedAt
                e.supplySource = rec.source
                e.supplyComplete = true
                e.supplyOwnerExcluded = rec.ownerExcluded == true
                if type(rec.market) == "number" and rec.market > 0 then e.supplyObservedPrice = rec.market end
            else
                e.supplyObserved = false
                unknown = unknown + 1
            end
            local h = (snapHistory and snapHistory[mid])
                or (not snapSupply and AB and AB.GetAuctionSupplyHistory and AB.GetAuctionSupplyHistory(mid))
                or nil
            if type(h) == "table" and tonumber(h.quantity) and h.quantity >= 0 then
                e.supplyHistoryQuantity = h.quantity
                e.supplyHistoryObservedAt = tonumber(h.observedAt) or 0
            end
            local pat = (snapPriceAt and snapPriceAt[mid])
                or (not snapSupply and AB and AB.GetAuctionPriceObservedAt and AB.GetAuctionPriceObservedAt(mid))
                or nil
            if tonumber(pat) and pat > 0 then e.priceObservedAt = pat end
        end
    end
    result.auctionSupplyUnknown = unknown > 0 and unknown or nil
    return result
end

local function standaloneComputeFishing(slug, opts)
    if slug ~= "cooking" then return nil end
    opts = opts or {}
    local DS = getDS()
    local guide = DS and type(DS.FishingGuide) == "function" and DS.FishingGuide() or nil
    local fishDB = type(guide) == "table" and guide.fish or nil
    if type(fishDB) ~= "table" then return nil end
    local catalog = loadCatalogRecipes("cooking")
    if not catalog then return nil end
    local vendorCtx = buildVendorCtx(opts)
    local cands, recOf, fishSet = {}, {}, {}
    for _, spell in ipairs(catalog.spells) do
        RouteTick()
        local rec = decodeDSRow(catalog.recipes[spell], "cooking", spell)
        if rec then
            stampLegacyIndices(rec)
            local learn, grey, mats = rec.learn, rec.grey, rec.mats
            if type(learn) == "number" and type(grey) == "number" and grey > learn and type(mats) == "table" and #mats > 0 then
                local ok, hasFish = true, false
                for _, m in ipairs(mats) do
                    local f = fishDB[m[1]]
                    if not f and DS and type(DS.ExtraSources) == "function" then
                        for _, es in ipairs(DS.ExtraSources(m[1])) do
                            if type(es) == "table" and es.sourceKind == "fished" then
                                f = { areas = { { areaID = es.targetID } } }
                                break
                            end
                        end
                    end
                    if f then
                        if f.season or f.night then ok = false end
                        hasFish = true
                        fishSet[m[1]] = f
                    elseif not RA.MatPriceOf(m[1], vendorCtx) then
                        ok = false
                    end
                end
                if ok and hasFish then
                    local cY = (type(rec.yellow) == "number") and rec.yellow or learn
                    cands[#cands + 1] = {
                        spell = spell,
                        item = rec.item,
                        learn = learn,
                        orange = rec.orange,
                        yellow = cY,
                        green = (type(rec.green) == "number") and rec.green or cY,
                        grey = grey,
                        mats = mats,
                        cost = 0,
                        fcost = 0,
                        base = 0,
                        learnO = learn,
                    }
                    recOf[spell] = rec
                end
            end
        end
    end
    if #cands == 0 then return nil end
    local capMax = cfgCap()
    local cap = math.max(2, math.min(capMax, math.floor(tonumber(opts.target) or capMax)))
    local start = math.max(1, math.min(cap - 1, opts.start or 1))
    local steps, gaps = Simulate(cands, start, cap, true, "crafts")
    if #steps == 0 then return nil end
    local stepsOut = ToReached(steps)
    local fishList, fishAt = {}, {}
    for _, st in ipairs(stepsOut) do
        RouteTick()
        local rec = recOf[st[3]]
        local ml = (rec and rec.mats) or {}
        local cnt = st[4] or 0
        local line = {}
        for _, m in ipairs(ml) do
            local f = fishSet[m[1]] or fishDB[m[1]]
            if f then
                local need = (m[2] or 1) * cnt
                local areas = f.areas or f.a or {}
                local a1 = areas[1]
                local e = fishAt[m[1]]
                if not e then
                    e = {
                        id = m[1],
                        count = 0,
                        need = 0,
                        source = "fishing",
                        areas = areas,
                        minSkill = a1 and a1.minSkill,
                        noGetaway = a1 and a1.noGetaway,
                        catchRate = f.rate,
                        note = f.note,
                    }
                    fishAt[m[1]] = e
                    fishList[#fishList + 1] = e
                end
                e.count = e.count + need
                e.need = e.count
                line[#line + 1] = { id = m[1], count = need, need = need, source = "fishing", areas = areas, note = f.note }
            end
        end
        if #line > 0 then
            local areas = {}
            for _, e in ipairs(line) do
                for _, a in ipairs(e.areas or {}) do areas[#areas + 1] = a end
            end
            st.fishing = line
            st.fishMaterials = line
            st.fishingAreas = areas
            st.profession = "cooking"
            st.role = "level"
            st.reason = "level"
        end
    end
    local total, crafts, mats, firstAt, vendorTotal, formulas, formulasTotal,
        productAH, productNPC, productPartial =
        SummarizeCore(stepsOut, recOf, false, nil, fishSet, slug, opts)
    local reached = stepsOut[#stepsOut] and stepsOut[#stepsOut][2] or start
    local res = {
        planVersion = 2,
        scheme = "fishing",
        fishingRoute = true,
        fishingRouteRevision = 2,
        steps = stepsOut,
        gaps = gaps,
        mats = mats,
        firstAt = firstAt,
        fishMaterials = fishList,
        matTotal = total,
        formulas = formulas,
        formulasTotal = formulasTotal,
        total = total + formulasTotal,
        vendorTotal = vendorTotal,
        ahTotal = total + formulasTotal - vendorTotal,
        productAH = productAH,
        productNPC = productNPC,
        productPartial = productPartial,
        crafts = crafts,
        start = start,
        target = cap,
        plannedTo = reached,
        targetReached = reached >= cap,
        partial = reached < cap,
        feasible = true,
        priced = RA.HasPriceData(),
        snapshotAge = SnapshotSec(),
        snapshotDays = priceCache.__minAge,
        stamp = nowSec(),
    }
    res = RA.ApplyRecovery(res, "cooking", opts, recOf)
    res.status = res.targetReached and "complete" or "incomplete"
    return res
end

RA._StandaloneComputeFishing = standaloneComputeFishing

local fishingWraps = setmetatable({}, { __mode = "k" })
local function wrapComputeFishing(fn)
    local target = type(fn) == "function" and fn or nil
    if target and fishingWraps[target] then
        return target
    end
    local wrapped
    wrapped = function(slug, opts)
        local pf = getFishing()
        local callFn = (type(target) == "function" and target ~= wrapped) and target
            or (pf and type(pf.ComputeFishing) == "function" and pf.ComputeFishing)
            or nil
        if type(callFn) == "function" then
            local ok, res = pcall(callFn, slug, opts)
            if ok then return res end
        end
        local okS, resS = pcall(standaloneComputeFishing, slug, opts)
        if okS then return resS end
        return nil
    end
    fishingWraps[wrapped] = true
    return wrapped
end

local currentComputeFishing = wrapComputeFishing(existingComputeFishing)
do
    local prevMt = getmetatable(RA)
    if not (type(prevMt) == "table" and prevMt.__dfFishingGuard) then
        rawset(RA, "ComputeFishing", nil)
        local prevIndex = type(prevMt) == "table" and prevMt.__index or nil
        local prevNewIndex = type(prevMt) == "table" and prevMt.__newindex or nil
        local mt = {}
        if type(prevMt) == "table" then
            for k, v in pairs(prevMt) do mt[k] = v end
        end
        mt.__dfFishingGuard = true
        mt.__index = function(t, k)
            if k == "ComputeFishing" then return currentComputeFishing end
            if type(prevIndex) == "function" then return prevIndex(t, k) end
            if type(prevIndex) == "table" then return prevIndex[k] end
            return nil
        end
        mt.__newindex = function(t, k, v)
            if k == "ComputeFishing" then
                if v == nil then
                    currentComputeFishing = nil
                elseif type(v) == "function" then
                    currentComputeFishing = wrapComputeFishing(v)
                else
                    currentComputeFishing = v
                end
                return
            end
            if type(prevNewIndex) == "function" then
                prevNewIndex(t, k, v)
                return
            end
            rawset(t, k, v)
        end
        setmetatable(RA, mt)
    end
end

function RA._WrapComputeFishing()
    local cur = RA.ComputeFishing
    if type(cur) == "function" and not fishingWraps[cur] then
        RA.ComputeFishing = wrapComputeFishing(cur)
    end
    return RA.ComputeFishing
end

local function baseCompute(slug, opts)
    opts = opts or {}
    if opts.scheme == "fishing" then
        if type(RA.ComputeFishing) == "function" then
            local okF, fr = pcall(RA.ComputeFishing, slug, opts)
            if okF and type(fr) == "table" then return fr end
            if not okF then
                local okS, sr = pcall(standaloneComputeFishing, slug, opts)
                if okS and type(sr) == "table" then return sr end
                return nil
            end
        else
            local okS, sr = pcall(standaloneComputeFishing, slug, opts)
            if okS and type(sr) == "table" then return sr end
        end
    end
    local cands, recOf, blockedCount, learningGaps = BuildCandidates(slug, opts)
    if not cands then return nil end
    local scheme = opts.scheme
    if scheme == nil or scheme == "stable" or not DEFAULT_SCHEME_LABELS[scheme] then scheme = "cheapest" end
    local capMax = cfgCap()
    local cap = tonumber(opts.target) or capMax
    cap = math.max(2, math.min(capMax, math.floor(cap)))
    local allowUnpriced = false
    local steps, gaps = Simulate(cands, opts.start, cap, allowUnpriced, scheme)
    local filled = false
    if #gaps > 0 then
        steps, gaps = FillGaps(cands, steps, gaps, scheme, allowUnpriced)
        for _, st in ipairs(steps) do
            if st.est then filled = true; break end
        end
    end
    if #learningGaps > 0 and #gaps > 0 then
        local stop = cap
        for _, gap in ipairs(gaps) do stop = math.min(stop, gap[1]) end
        local prefix = {}
        for _, step in ipairs(steps) do if step[1] < stop then prefix[#prefix + 1] = step end end
        steps = prefix
    end
    if scheme == "optim" then
        local bySpell = {}
        for _, c in ipairs(cands) do bySpell[c.spell] = c end
        for _, st in ipairs(steps) do
            local c = bySpell[st[3]]
            if c then st.cost = (c.base or 0) * (st[4] or 0) end
        end
    end
    local stepsOut = ToReached(steps)
    local kept = InjectTools(stepsOut, slug, cap, opts.start, recOf)
    local total, crafts, mats, firstAt, vendorTotal, formulas, formulasTotal,
        productAH, productNPC, productPartial =
        SummarizeCore(stepsOut, recOf, false, nil, nil, slug, opts)
    local res = {
        scheme = scheme,
        steps = stepsOut,
        gaps = gaps,
        mats = mats,
        firstAt = firstAt,
        total = total + formulasTotal,
        matTotal = total,
        formulas = formulas,
        formulasTotal = formulasTotal,
        vendorTotal = vendorTotal,
        ahTotal = total + formulasTotal - vendorTotal,
        productAH = productAH,
        productNPC = productNPC,
        productPartial = productPartial,
        crafts = crafts,
        start = math.max(1, math.min(capMax - 1, opts.start or 1)),
        target = cap,
        priced = RA.HasPriceData(),
        filled = filled,
        specBlocked = blockedCount,
        learningGaps = learningGaps,
        learningCoverageComplete = #learningGaps == 0,
        toolItems = kept,
        snapshotAge = SnapshotSec(),
        snapshotDays = priceCache.__minAge,
        stamp = nowSec(),
    }
    if #learningGaps > 0 then
        res.plannedTo = stepsOut[#stepsOut] and stepsOut[#stepsOut][2] or res.start
        res.targetReached = res.plannedTo >= cap
        res.partial = not res.targetReached
        res.feasible = #stepsOut > 0
        res.status = res.targetReached and "complete" or res.feasible and "incomplete" or "infeasible"
        res.optimal = false
        if not res.targetReached then
            res.learningComplete = false
            res.completeCost = false
            res.blockingDiagnostics = learningGaps
            res.diagnostics = learningGaps
        end
    end
    local economy = getEconomy()
    if economy and type(economy.LearningPolicyFingerprint) == "function" then
        local ok, v = pcall(economy.LearningPolicyFingerprint)
        if ok then res.learningPolicyFingerprint = v end
    end
    return RA.ApplyRecovery(res, slug, opts, recOf)
end

RA._BaseCompute = baseCompute
if type(RA.Compute) ~= "function" then
    RA.Compute = baseCompute
end

local cache = {}
local invalidating = false

local function baseInvalidate()
    if invalidating then return end
    invalidating = true
    local sup = getSupply()
    if sup and type(sup.Invalidate) == "function" then pcall(sup.Invalidate) end
    local rec = getRecovery()
    if rec and type(rec.Invalidate) == "function" then pcall(rec.Invalidate) end
    local gates = getGates()
    if gates and type(gates.Invalidate) == "function" then pcall(gates.Invalidate) end
    for k in pairs(cache) do cache[k] = nil end
    for k in pairs(priceCache) do
        if k ~= "__any" then priceCache[k] = nil end
    end
    priceCache.__any = nil
    for k in pairs(vendorCache) do vendorCache[k] = nil end
    for k in pairs(sellCache) do sellCache[k] = nil end
    for k in pairs(ahReason) do ahReason[k] = nil end
    for k in pairs(ahAge) do ahAge[k] = nil end
    invalidating = false
end

RA._BaseInvalidate = baseInvalidate
if type(RA.Invalidate) ~= "function" then
    RA.Invalidate = baseInvalidate
end

local priceWatchers = {}
function RA.OnPricesChanged(fn)
    if type(fn) == "function" then priceWatchers[#priceWatchers + 1] = fn end
end

function RA.NotifyPricesChanged()
    if type(RA.Invalidate) == "function" then RA.Invalidate() else baseInvalidate() end
    for _, fn in ipairs(priceWatchers) do pcall(fn) end
end

if type(_G.CreateFrame) == "function" then
    local ok, ahWatch = pcall(_G.CreateFrame, "Frame")
    if ok and type(ahWatch) == "table" and type(ahWatch.RegisterEvent) == "function" and type(ahWatch.SetScript) == "function" then
        pcall(ahWatch.RegisterEvent, ahWatch, "AUCTION_HOUSE_CLOSED")
        pcall(ahWatch.SetScript, ahWatch, "OnEvent", function()
            if type(_G.C_Timer) == "table" and type(_G.C_Timer.After) == "function" then
                _G.C_Timer.After(0, function() RA.NotifyPricesChanged() end)
            else
                RA.NotifyPricesChanged()
            end
        end)
    end
end

local function Fingerprint(opts, slug)
    local Pol = getEconomy()
    local pol
    if Pol and type(Pol.GetPolicies) == "function" then
        local ok, v = pcall(Pol.GetPolicies, slug)
        if ok and type(v) == "table" then pol = v end
    end
    local partner = opts.secondaryProfession
    if partner == nil and Pol and type(Pol.GetRoutePartner) == "function" then
        local ok, v = pcall(Pol.GetRoutePartner, slug)
        if ok then partner = v end
    end
    local polFp, learnPolFp, learnObsFp = "", "", ""
    if pol and Pol and type(Pol.PolicyFingerprint) == "function" then
        local ok, v = pcall(Pol.PolicyFingerprint, pol)
        if ok and v ~= nil then polFp = v end
    end
    if Pol and type(Pol.LearningPolicyFingerprint) == "function" then
        local ok, v = pcall(Pol.LearningPolicyFingerprint)
        if ok and v ~= nil then learnPolFp = v end
    end
    if Pol and type(Pol.LearningObservationFingerprint) == "function" then
        local ok, v = pcall(Pol.LearningObservationFingerprint)
        if ok and v ~= nil then learnObsFp = v end
    end
    return format("%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s",
        tostring(opts.start), tostring(opts.onlyAH), tostring(opts.considerAuctionSupply),
        tostring(opts.allowBindOnPickupFormulas), tostring(opts.allowCurrencyFormulas),
        tostring(opts.allowLimitedFormulas),
        tostring(opts.target and math.floor(tonumber(opts.target) or cfgCap())),
        tostring(opts.scheme),
        tostring(opts.allowSecondaryLeveling),
        tostring(partner),
        polFp,
        learnPolFp,
        learnObsFp)
end

function RA.QuoteSig(slug)
    local AB = getAuctionBridge()
    local pcfg = getPricingCfg()
    local defFee = (type(pcfg) == "table" and type(pcfg.DEFAULT_RECOVERY_FEE_PCT) == "number" and pcfg.DEFAULT_RECOVERY_FEE_PCT) or 5
    local rev = AB and AB.SupplyRevision and AB.SupplyRevision() or 0
    local fee = tonumber(readSettingRaw("recoveryFeePercent", slug, defFee)) or defFee
    local lim = readSetting("autoBuyLimitedFormulas", slug, false) and 1 or 0
    local bop = readSetting("autoAllowBindOnPickupFormulas", slug, false) and 1 or 0
    local currency = readSetting("autoAllowCurrencyFormulas", slug, false) and 1 or 0
    local rec = readSetting("recoveryEnabled", slug, false) and 1 or 0
    local tool = readSetting("autoCraftTools", slug, true) and 1 or 0
    return tostring(rev) .. ":" .. tostring(fee) .. ":" .. tostring(lim) .. ":" .. tostring(bop) .. ":" .. tostring(currency)
        .. ":" .. tostring(rec) .. ":" .. tostring(tool)
end

function RA.SpecSig(slug)
    local G = getGates()
    if not (G and G.SpecFingerprint) then return "" end
    local choice = "none"
    if type(G.GetPlannedChoice) == "function" then
        local ok, v = pcall(G.GetPlannedChoice)
        if ok and v ~= nil then choice = v end
    end
    local ok, fp = pcall(G.SpecFingerprint, choice, nil, slug)
    if ok and type(fp) == "string" then return fp end
    return ""
end

local function baseOptionsFor(slug, current, skipExecutionInventory)
    local db = getDB()
    local root = resolveDBRoot(db)
    local fish = (slug == "cooking") and (((type(root) == "table" and type(root.prof) == "table" and root.prof.cookingRoute) or "fishing") == "fishing")
    local lv = tonumber(current)
    local start
    if type(db) == "table" and type(db.AutoStartSkillOf) == "function" then
        local ok, v = pcall(db.AutoStartSkillOf, slug, lv)
        if ok and type(v) == "number" then start = v end
    end
    if not start then
        start = (readSetting("autoFromCurrent", slug, true) and lv) and math.max(1, math.floor(lv)) or 1
    end
    local allowSec = readSetting("autoSecondaryLeveling", slug, false)
    local E = getEconomy()
    local pairPartner = nil
    if not fish and E then
        local partnerArg
        if type(E.GetRoutePartner) == "function" then
            local okp, p = pcall(E.GetRoutePartner, slug)
            if okp then partnerArg = p end
        end
        local ctx
        if type(E.RouteContext) == "function" then
            local okc, c = pcall(E.RouteContext, slug, { start = start, allowSecondaryLeveling = allowSec, secondaryProfession = partnerArg })
            if okc and type(c) == "table" then ctx = c end
        end
        if ctx and ctx.requiresPartner and ctx.partnerValid then
            pairPartner = ctx.partner
        elseif partnerArg ~= nil then
            pairPartner = partnerArg
        end
    end
    local target = readTargetSkill(slug)
    local scheme = isFixedOnly(slug) and "fixed" or (fish and "fishing") or readSettingRaw("autoScheme", slug, "cheapest")
    if scheme == "stable" then scheme = "cheapest" end
    local xp = getExecution()
    local execInv = nil
    if not skipExecutionInventory and xp and type(xp.GetContinuation) == "function" then
        local okInv, inv = pcall(xp.GetContinuation, slug)
        if okInv then execInv = inv end
    end
    return {
        start = start,
        onlyAH = readSetting("autoOnlyAH", slug, true),
        considerAuctionSupply = readSetting("autoConsiderAuctionSupply", slug, false),
        allowLimitedFormulas = readSetting("autoBuyLimitedFormulas", slug, false),
        allowBindOnPickupFormulas = readSetting("autoAllowBindOnPickupFormulas", slug, false),
        allowCurrencyFormulas = readSetting("autoAllowCurrencyFormulas", slug, false),
        target = target,
        scheme = scheme,
        allowSecondaryLeveling = allowSec,
        secondaryProfession = pairPartner,
        executionInventory = execInv,
    }
end

RA._BaseOptionsFor = baseOptionsFor
if type(RA.OptionsFor) ~= "function" then
    RA.OptionsFor = baseOptionsFor
end

if type(RA.Recalculate) ~= "function" then
    function RA.Recalculate(slug, opts)
        RA.Invalidate()
        return true
    end
end

if type(RA.PlanSig) ~= "function" then
    function RA.PlanSig(slug, opts)
        return Fingerprint(opts or {}, slug) .. "#" .. RA.QuoteSig(slug) .. "#" .. RA.SpecSig(slug)
    end
end

if type(RA.Get) ~= "function" then
    function RA.Get(slug, opts)
        opts = opts or {}
        local fp = Fingerprint(opts, slug)
        local sig = RA.QuoteSig(slug)
        local specSig = RA.SpecSig(slug)
        local bucket = cache[slug]
        if not bucket then
            bucket = {}
            cache[slug] = bucket
        end
        local now = nowSec()
        local ttl = cfgCacheTTL()
        local slots = cfgCacheSlots()
        local e = bucket[fp]
        if e and e.sig == sig and e.specSig == specSig and (now - e.stamp) < ttl then return e.res end
        local refreshed = e ~= nil and e.sig ~= sig
        local res = RA.Compute(slug, opts)
        if res then res.planSig = fp .. "#" .. sig .. "#" .. specSig end
        if res and refreshed then res.quotesRefreshed = true end
        bucket[fp] = { res = res, stamp = now, sig = sig, specSig = specSig }
        local n, oldK, oldT = 0, nil, nil
        for k, v in pairs(bucket) do
            n = n + 1
            if k ~= fp and (not oldT or v.stamp < oldT) then oldK, oldT = k, v.stamp end
        end
        if n > slots and oldK then bucket[oldK] = nil end
        return res
    end
end

if type(RA.VendorQuotesChanged) ~= "function" then
    function RA.VendorQuotesChanged(result)
        local E = getEconomy()
        if E and type(E.VendorPricesChanged) == "function" then
            local ok, v = pcall(E.VendorPricesChanged, result)
            if ok then return v end
        end
        return false
    end
end

if type(RA.ValidateVendorQuotes) ~= "function" then
    function RA.ValidateVendorQuotes(result)
        return result
    end
end

local delegateInvalidate = nil
local registeringPricingDelegate = false
local inPricingChain = false
if type(RA._PricingRegisterWraps) ~= "table" then
    RA._PricingRegisterWraps = setmetatable({}, { __mode = "k" })
end

local function registerDelegate()
    if registeringPricingDelegate then return end
    local API = getAPI()
    if not API or type(API.RegisterDelegate) ~= "function" then return end
    local wraps = RA._PricingRegisterWraps
    local entry = wraps[API]
    if not entry then
        entry = { raw = API.RegisterDelegate }
        wraps[API] = entry
    elseif API.RegisterDelegate ~= entry.wrapped then
        entry.raw = API.RegisterDelegate
    end
    local rawRegister = entry.raw
    if API.RegisterDelegate ~= entry.wrapped or entry.owner ~= registerDelegate then
        local function wrappedRegister(name, impl)
            rawRegister(name, impl)
            if name == "pricing" and type(impl) == "table" and not registeringPricingDelegate then
                registerDelegate()
            end
        end
        entry.wrapped = wrappedRegister
        entry.owner = registerDelegate
        API.RegisterDelegate = wrappedRegister
    end
    registeringPricingDelegate = true
    local ok, err = pcall(function()
        local prev = type(API.GetDelegate) == "function" and API.GetDelegate("pricing") or nil
        local impl = {}
        if type(prev) == "table" then
            for k, v in pairs(prev) do impl[k] = v end
        end
        impl.AHPriceOf = RA.AHPriceOf
        impl.VendorPrice = RA.VendorPrice
        impl.EffectiveCost = RA.EffectiveCost
        impl.MatPriceOf = RA.MatPriceOf
        if type(impl.NPCSellPriceOf) ~= "function" then impl.NPCSellPriceOf = RA.NPCSellPriceOf end

        local prevInv = type(prev) == "table" and type(prev.Invalidate) == "function" and prev.Invalidate or nil
        if prevInv == delegateInvalidate and delegateInvalidate ~= nil then
            impl.Invalidate = delegateInvalidate
        elseif prevInv and prevInv ~= baseInvalidate then
            local active = false
            delegateInvalidate = function()
                if active then return end
                active = true
                local wasInChain = inPricingChain
                inPricingChain = true
                if not wasInChain then
                    baseInvalidate()
                end
                pcall(prevInv)
                inPricingChain = wasInChain
                active = false
            end
            impl.Invalidate = delegateInvalidate
        else
            impl.Invalidate = baseInvalidate
        end
        rawRegister("pricing", impl)
    end)
    registeringPricingDelegate = false
    if not ok then error(err, 0) end
end

RA.RegisterDelegate = registerDelegate
registerDelegate()

local initFn = ns.Init or (type(gns) == "table" and gns.Init) or nil
if type(initFn) == "function" then
    initFn(registerDelegate)
end
