local _, ns = ...
if type(ns) ~= "table" then ns = _G.DF_NS or {} end
local gns = _G.DF_NS

local R = { REVISION = 1 }
ns.ProfRecovery = R
if type(gns) == "table" and gns ~= ns then
    gns.ProfRecovery = R
end

local floor, min, max, ceil = math.floor, math.min, math.max, math.ceil

local function getDS()
    return ns.ProfDataStore or (type(gns) == "table" and gns.ProfDataStore) or nil
end

local function getAPI()
    return ns.ProfAPI or (type(gns) == "table" and gns.ProfAPI) or nil
end

local function getDB()
    return ns.ProfDB or (type(gns) == "table" and gns.ProfDB) or nil
end

local function getPricingCfg()
    return ns.PricingConfig or (type(gns) == "table" and gns.PricingConfig) or nil
end

local function getHost()
    return ns.ProfHost or (type(gns) == "table" and gns.ProfHost) or nil
end

local function getRouteAuto()
    return ns.ProfRouteAuto or (type(gns) == "table" and gns.ProfRouteAuto) or nil
end

local function getAuctionBridge()
    return ns.AuctionBridge or (type(gns) == "table" and gns.AuctionBridge) or nil
end

local function getEasyBridge()
    return ns.EasyBridge or (type(gns) == "table" and gns.EasyBridge) or nil
end

local function cfgNum(key, fallback)
    local cfg = getPricingCfg()
    if type(cfg) == "table" and type(cfg[key]) == "number" then
        return cfg[key]
    end
    return fallback
end

local function cfgTbl(key)
    local cfg = getPricingCfg()
    if type(cfg) == "table" and type(cfg[key]) == "table" then
        return cfg[key]
    end
    return nil
end

R.PROFIT_CAP = cfgNum("PROFIT_CAP", 20)

local function copy(t, tick)
    if type(t) ~= "table" then return t end
    local meta = getmetatable(t)
    if type(meta) == "table" and type(meta.__profLearningMaterialize) == "function" then
        t = meta.__profLearningMaterialize(t)
    end
    local o = {}
    local n = 0
    for k, v in pairs(t) do
        o[k] = copy(v, tick)
        n = n + 1
        if tick and n % 32 == 0 then tick() end
    end
    if tick then tick() end
    return o
end

local function amount(n)
    return type(n) == "number" and n == n and n >= 0 and n < math.huge
end

local function percent(n)
    return amount(n) and n <= 100
end

local function now()
    if type(_G.time) == "function" then return _G.time() end
    if type(os) == "table" and type(os.time) == "function" then return os.time() end
    return 0
end

local requestedItems = {}
local function requestMissingItem(id)
    local host = getHost()
    local dg = type(host) == "table" and host.DG or nil
    if not requestedItems[id] and type(dg) == "table" and type(dg.RequestItem) == "function" then
        requestedItems[id] = true
        pcall(dg.RequestItem, id)
    end
end

function R.NPCSellPriceOf(id)
    if type(id) ~= "number" or id <= 0 then return nil end
    local DS = getDS()
    if DS and type(DS.Item) == "function" then
        local item = DS.Item(id)
        if type(item) == "table" and amount(item.sellPriceCopper) then
            return floor(item.sellPriceCopper)
        end
    end
    local ci = _G.C_Item
    for _, fn in ipairs({ type(ci) == "table" and ci.GetItemInfo or false, _G.GetItemInfo or false }) do
        if type(fn) == "function" then
            local values = { pcall(fn, id) }
            if values[1] and amount(values[12]) then return floor(values[12]) end
        end
    end
    if type(ci) == "table" and type(ci.GetItemSellPrice) == "function" then
        local ok, value = pcall(ci.GetItemSellPrice, id)
        if ok and amount(value) then return floor(value) end
    end
    return nil
end

local function bound(id, s)
    if type(s) == "table" and s.nonAuctionable and s.nonAuctionable[id] then return true end
    local DS = getDS()
    if DS and type(DS.Item) == "function" then
        local item = DS.Item(id)
        if type(item) == "table" then
            if item.nonAuctionable == true or item.bindType == 1 or item.bindType == 4 then
                return true
            end
            if item.bindType ~= nil or item.nonAuctionable == false then
                return false
            end
        end
    end
    local ci = _G.C_Item
    local fn = (type(ci) == "table" and ci.GetItemInfo) or _G.GetItemInfo
    if type(fn) == "function" then
        local v = { pcall(fn, id) }
        if v[1] then return v[15] == 1 or v[15] == 4 end
    end
    return false
end

function R.RobustFloorPrice(levels)
    if type(levels) ~= "table" or #levels == 0 then return nil end
    local rows = {}
    local total = 0
    for i = 1, #levels do
        local row = levels[i]
        local p = type(row) == "table" and (row[1] or row.price) or nil
        local q = type(row) == "table" and (row[2] or row.quantity or row.qty) or nil
        if amount(p) and p > 0 and amount(q) and q > 0 then
            local qi = floor(q)
            if qi > 0 then
                rows[#rows + 1] = { p, qi }
                total = total + qi
            end
        end
    end
    if #rows == 0 or total <= 0 then return nil end
    table.sort(rows, function(a, b) return a[1] < b[1] end)

    local rf = cfgTbl("ROBUST_FLOOR") or {}
    local minSupply = type(rf.minConfidenceSupply) == "number" and rf.minConfidenceSupply or 1
    if total < minSupply then return nil end

    local ff = cfgTbl("FISHING_FILTER") or {}
    local startIdx = 1
    local remTotal = total
    if ff.enabled ~= false and total >= (ff.minTotalSupplyForTrim or 5) then
        local maxLots = ff.headMaxLotCount or 3
        local maxShare = ff.headMaxQtyShare or 0.05
        local cliffRatio = ff.cliffPriceRatio or 0.60
        local trimmed = 0
        while startIdx < #rows and trimmed < maxLots do
            local lot = rows[startIdx]
            local nextLot = rows[startIdx + 1]
            if (lot[2] / total) <= maxShare and (lot[1] / nextLot[1]) <= cliffRatio then
                remTotal = remTotal - lot[2]
                startIdx = startIdx + 1
                trimmed = trimmed + 1
            else
                break
            end
        end
    end

    local pct = type(rf.defaultPercentile) == "number" and rf.defaultPercentile or 0.125
    local targetQty = max(1, ceil(remTotal * pct))
    local cum = 0
    local chosen = rows[startIdx][1]
    for i = startIdx, #rows do
        cum = cum + rows[i][2]
        if cum >= targetQty then
            chosen = rows[i][1]
            break
        end
    end
    return floor(chosen)
end

function R.Fee(snapshot, opts)
    opts = opts or {}
    if percent(opts.recoveryFeePercent) then return opts.recoveryFeePercent, "manual", false end
    local client = snapshot and snapshot.auctionFee
    if type(client) == "table" and client.reliable == true and percent(client.percent) then
        return client.percent, client.source or "client", false
    end
    local auct = _G.Auctionator
    local constants = type(auct) == "table" and auct.Constants
    local factor = type(constants) == "table" and constants.AfterAHCut
    if amount(factor) and factor <= 1 then return (1 - factor) * 100, "auctionator-reference", true end
    local eb = getEasyBridge()
    local cut = eb and eb.AuctionCut and eb.AuctionCut()
    if amount(cut) and cut >= 0 and cut < 100 then return cut, "easyauction-reference", true end
    return nil, "unknown", false
end

local function livePrice(id)
    local ra = getRouteAuto()
    if ra and type(ra.AHPriceOf) == "function" then
        return ra.AHPriceOf(id)
    end
    local api = getAPI()
    if api and type(api.AHPriceOf) == "function" then
        return api.AHPriceOf(id)
    end
    return nil
end

local function rerate(q, fee, residualMass)
    local residMass = cfgNum("RESIDUAL_MASS", 0.7)
    local minGain = cfgNum("RERATE_MIN_AH_GAIN_COPPER", 100)
    local minSupply = cfgNum("RERATE_MIN_SUPPLY", 40)
    q.auctionNet = q.auctionGross and fee and floor(q.auctionGross * (residualMass and residMass or 1) * (100 - fee) / 100 + 1e-9) or nil
    q.assumedAllSold = nil
    q.missing = nil
    q.unsellable = q.bound and true or nil
    if q.npcUnit ~= nil then
        q.unit = q.npcUnit
        q.source = "npc"
        if not q.bound and q.auctionNet and q.auctionNet - q.npcUnit > minGain
            and (q.supplyReliable or q.supplyEstimated) and (q.quantity or 0) >= minSupply then
            q.unit = q.auctionNet
            q.source = "ah"
            q.assumedAllSold = true
        end
    else
        q.unit = 0
        q.source = "unknown"
        q.missing = true
    end
    return q
end
R.Rerate = rerate

local function quote(id, s, fee, stamp, live, residualMass)
    local npc
    if not live and type(s.sellPrices) == "table" and s.sellPrices[id] ~= nil then
        npc = s.sellPrices[id]
    else
        npc = R.NPCSellPriceOf(id)
    end
    if not amount(npc) then npc = nil else npc = floor(npc) end

    local b = getAuctionBridge()
    local auction = live and livePrice(id) or (s.prices and s.prices[id])
    if not amount(auction) or auction == 0 then
        local depth = live and (b and type(b.GetAuctionDepth) == "function" and b.GetAuctionDepth(id))
            or (s.auctionDepth and s.auctionDepth[id])
        if type(depth) == "table" and type(depth.levels) == "table" then
            auction = R.RobustFloorPrice(depth.levels)
        else
            auction = nil
        end
    end

    local supply = live and (b and type(b.GetAuctionSupply) == "function" and b.GetAuctionSupply(id, true))
        or (s.auctionSupply and s.auctionSupply[id])
    local ra = getRouteAuto()
    local maxAge = (ra and type(ra.MaxAuctionSupplyAgeSeconds) == "function" and ra.MaxAuctionSupplyAgeSeconds())
        or cfgNum("SUPPLY_MAX_AGE_SEC", 172800)
    local age = type(supply) == "table" and type(supply.observedAt) == "number" and (stamp - supply.observedAt)
    local reliable = type(supply) == "table"
        and amount(supply.quantity) and supply.quantity == floor(supply.quantity)
        and supply.complete == true
        and supply.ownerExcluded ~= false
        and supply.source == "client-auction-results"
        and ((b and type(b.ForceExpiredActive) == "function" and b.ForceExpiredActive())
            or (age and age >= 0 and age <= maxAge)) or false
    local estimated = false
    if not reliable then
        local history
        if live then
            history = b and type(b.GetAuctionSupplyHistory) == "function" and b.GetAuctionSupplyHistory(id)
        else
            history = s.auctionSupplyHistory and s.auctionSupplyHistory[id]
        end
        if type(history) == "table" and history.source == "auctionator-history"
            and amount(history.quantity) and history.quantity == floor(history.quantity)
            and amount(history.observedAt) and history.observedAt > 0 and history.observedAt <= stamp then
            supply = history
            estimated = true
        end
    end
    local blocked = bound(id, live and {} or s)
    local net = auction and fee and floor(auction * (100 - fee) / 100 + 1e-9) or nil
    local q = {
        id = id,
        npcUnit = npc,
        auctionGross = auction,
        auctionNet = net,
        bound = blocked,
        quantity = supply and supply.quantity,
        observedAt = supply and supply.observedAt,
        complete = supply and supply.complete,
        ownerExcluded = supply and supply.ownerExcluded,
        supplySource = supply and supply.source,
        supplyReliable = reliable,
        supplyEstimated = estimated,
        market = supply and supply.market,
        batch = supply and supply.batch,
    }
    return rerate(q, fee, residualMass)
end

local identityFields = {
    "npcUnit", "auctionGross", "auctionNet", "bound", "quantity", "observedAt",
    "complete", "ownerExcluded", "supplySource", "supplyReliable", "supplyEstimated",
    "market", "batch", "source", "unit", "missing",
}
local function identity(q)
    local p = {}
    for _, key in ipairs(identityFields) do
        p[#p + 1] = key .. "=" .. tostring(q[key])
    end
    return table.concat(p, ";")
end

function R.Options(opts, slug)
    opts = opts or {}
    slug = slug or opts.profession or opts.slug
    local DB = getDB()
    local db
    if type(DB) == "function" or (type(DB) == "table" and type(getmetatable(DB)) == "table" and getmetatable(DB).__call) then
        local ok, res = pcall(DB)
        if ok and type(res) == "table" then db = res end
    elseif type(DB) == "table" and type(DB.Get) == "function" then
        local ok, res = pcall(DB.Get)
        if ok and type(res) == "table" then db = res end
    end
    local prof = type(db) == "table" and type(db.prof) == "table" and db.prof or nil
    local ps = prof and type(slug) == "string" and type(prof.professionSettings) == "table" and prof.professionSettings[slug] or nil

    local function readOverride(k)
        if type(ps) == "table" and ps[k] ~= nil then return ps[k] end
        if type(prof) == "table" and prof[k] ~= nil then return prof[k] end
        if type(DB) == "table" and type(DB.Get) ~= "function" and type(DB.SettingRaw) == "function" then
            return DB.SettingRaw(k, slug)
        end
        return nil
    end

    if opts.recoveryEnabled == nil then
        local v = readOverride("recoveryEnabled")
        if v ~= nil then opts.recoveryEnabled = v end
    end
    if opts.residualMass == nil then
        local v = readOverride("autoResidualMass")
        if v ~= nil then opts.residualMass = v end
    end
    if opts.recoveryFeePercent == nil then
        local v = readOverride("recoveryFeePercent")
        if type(v) == "number" then opts.recoveryFeePercent = v end
    end
    return opts
end

function R.Capture(snapshot, opts, tick)
    snapshot = snapshot or {}
    local slug = (opts and (opts.profession or opts.slug)) or snapshot.slug or snapshot.targetProfession
    opts = R.Options(opts, slug)
    if snapshot.recovery and snapshot.recovery.revision == R.REVISION and snapshot.recovery.quotes then
        local old = snapshot.recovery
        if opts.recoveryEnabled ~= nil and opts.recoveryEnabled ~= old.enabled
            or percent(opts.recoveryFeePercent) and opts.recoveryFeePercent ~= old.feePercent
            or opts.residualMass ~= nil and opts.residualMass ~= old.residualMass then
            local r = copy(old, tick)
            if opts.recoveryEnabled ~= nil then r.enabled = opts.recoveryEnabled ~= false end
            if opts.residualMass ~= nil then r.residualMass = opts.residualMass == true end
            if percent(opts.recoveryFeePercent) then
                r.feePercent = opts.recoveryFeePercent
                r.feeSource = "manual"
                r.feeReference = false
                r.feeOverride = opts.recoveryFeePercent
            end
            for _, q in pairs(r.quotes) do
                rerate(q, r.feePercent, r.residualMass)
                if tick then tick() end
            end
            snapshot.recovery = r
        end
        return snapshot.recovery
    end
    local fee, source, reference = R.Fee(snapshot, opts)
    local r = {
        revision = R.REVISION,
        enabled = opts.recoveryEnabled ~= false,
        residualMass = opts.residualMass == true,
        feePercent = fee,
        feeSource = source,
        feeReference = reference,
        feeOverride = opts.recoveryFeePercent,
        clientFee = copy(snapshot.auctionFee, tick),
        capturedAt = snapshot.stamp or now(),
        quotes = {},
    }
    for _, recipe in ipairs(snapshot.recipes or {}) do
        local itemID = recipe.item or recipe.outputItemID
        if type(itemID) == "number" and itemID > 0 and (recipe.count or 1) > 0 then
            r.quotes[itemID] = quote(itemID, snapshot, fee, r.capturedAt, false, r.residualMass)
            if r.quotes[itemID].missing then requestMissingItem(itemID) end
        end
        if tick then tick() end
    end
    snapshot.recovery = r
    return r
end

local function revenue(state, snapshot, produced)
    local total = 0
    for id, count in pairs(produced or {}) do
        local q = snapshot and snapshot.recovery and snapshot.recovery.quotes[id]
        local retained = snapshot and snapshot.retainedToolItems and snapshot.retainedToolItems[id] or 0
        local purchased = max(0, ((state.inv or {})[id] or 0) - ((state.produced or {})[id] or 0))
        local sale = max(0, count - max(0, retained - purchased))
        if q and amount(count) then total = total + sale * (q.unit or 0) end
    end
    return total
end

function R.StateRevenue(state, snapshot)
    return revenue(state, snapshot, state and state.produced)
end

function R.PriorityRevenue(state, snapshot)
    return revenue(state, snapshot, state and state.priorityProduced)
end

function R.Objective(state, snapshot)
    local r = snapshot and snapshot.recovery
    return (state and state.money or 0) - (r and r.enabled and R.PriorityRevenue(state, snapshot) or 0)
end

local function changed(result, opts)
    local old = result and result.recoverySnapshot
    if not old or result.recoveryRevision ~= R.REVISION then return true end
    opts = opts or { recoveryEnabled = old.enabled, recoveryFeePercent = old.feeOverride, residualMass = old.residualMass }
    if (opts.recoveryEnabled ~= false) ~= old.enabled or (opts.residualMass == true) ~= (old.residualMass == true) then
        return true
    end
    local supplied = opts.snapshot
    if supplied and supplied.recovery and supplied.recovery.revision == R.REVISION then
        local current = supplied.recovery
        if current.enabled ~= old.enabled or current.feePercent ~= old.feePercent
            or current.feeSource ~= old.feeSource or current.residualMass ~= old.residualMass then
            return true
        end
        for id, q in pairs(old.quotes or {}) do
            if not current.quotes[id] or identity(current.quotes[id]) ~= identity(q) then return true end
        end
        return false
    end
    local fee, source, reference = R.Fee(supplied or { auctionFee = old.clientFee }, opts)
    if fee ~= old.feePercent or source ~= old.feeSource or reference ~= old.feeReference then return true end
    for id, q in pairs(old.quotes or {}) do
        if identity(quote(id, supplied or {}, fee, now(), not supplied, opts.residualMass)) ~= identity(q) then
            return true
        end
    end
    return false
end

local changedMemo = setmetatable({}, { __mode = "k" })
function R.Invalidate()
    changedMemo = setmetatable({}, { __mode = "k" })
end

function R.Changed(result, opts)
    if not result or (opts and opts.snapshot) or type(_G.GetTime) ~= "function" then
        return changed(result, opts)
    end
    local stamp = _G.GetTime()
    local bridge = getAuctionBridge()
    local revision = bridge and type(bridge.SupplyRevision) == "function" and bridge.SupplyRevision() or 0
    local signature = tostring(opts and opts.recoveryEnabled) .. ":" .. tostring(opts and opts.recoveryFeePercent)
        .. ":" .. tostring(opts and opts.residualMass) .. ":" .. tostring(revision)
    local previous = changedMemo[result]
    if previous and previous.signature == signature and stamp >= previous.at and (stamp - previous.at) < 1 then
        return previous.value
    end
    local value = changed(result, opts)
    changedMemo[result] = { signature = signature, at = stamp, value = value }
    return value
end

local function recipeFor(step, snapshot)
    if step.recipe then return step.recipe end
    local key = tostring(step.profession or snapshot.slug or "") .. ":" .. tostring(step[3])
    if snapshot.byKey and snapshot.byKey[key] then return snapshot.byKey[key] end
    for _, r in ipairs(snapshot.recipes or {}) do
        if (r.spell or r.spellID) == step[3] and (not step.profession or r.profession == step.profession) then
            return r
        end
    end
    return nil
end

local function trace(result, snapshot)
    local recorded = result.actions and #result.actions > 0
    if recorded then
        for _, a in ipairs(result.actions) do
            if a.type == "buy" or a.type == "formula" then return result.actions end
        end
        if #(result.mats or {}) == 0 and #(result.formulas or {}) == 0 then return result.actions end
    end
    local out = {}
    for _, m in ipairs(result.mats or {}) do
        local n = m.count or m[2] or m.need or 0
        out[#out + 1] = { type = "buy", item = m.id or m[1], count = n, cost = m.cost or (m.unit or 0) * n, owner = m.owner }
    end
    for _, f in ipairs(result.formulas or {}) do
        local r = f.recipes and f.recipes[1]
        out[#out + 1] = {
            type = "formula",
            cost = f.cost or 0,
            owner = f.recipeKey or (r and (r.key or (tostring(r.profession) .. ":" .. tostring(r.spell or r.spellID)))),
        }
    end
    if recorded then
        for _, a in ipairs(result.actions) do out[#out + 1] = a end
        return out
    end
    local rows = result.executionSteps and #result.executionSteps > 0 and result.executionSteps or result.steps or {}
    for i, step in ipairs(rows) do
        local r = recipeFor(step, snapshot)
        if step.kind == "essence_conversion" or step.kind == "conversion" then
            local c = step.conversion or {}
            local n = step.expectedCrafts or step[4] or 0
            local source = c.inputItemID or step.sourceItem
            local input = c.inputCount or step.sourcePerConversion
            local target = c.outputItemID or step.targetItem or step.item
            local output = c.outputCount or step.targetPerConversion or step.outputMin
            if source and target and input and output then
                out[#out + 1] = {
                    id = "derived:" .. i,
                    type = "convert",
                    count = n,
                    owner = step.owner,
                    inputs = { { source, input * n } },
                    outputs = { { target, output * n } },
                }
            end
        elseif r and not step.checkpoint then
            local n = step[4] or step.count or 0
            local inputs = {}
            for _, m in ipairs(r.mats or {}) do inputs[#inputs + 1] = { m[1], m[2] * n } end
            local id = r.item or r.outputItemID
            local qty = (r.count or 1) * n
            out[#out + 1] = {
                id = "derived:" .. i,
                type = "craft",
                profession = r.profession,
                spell = r.spell or r.spellID,
                count = n,
                inputs = inputs,
                outputs = id and { { id, qty } } or {},
                item = id,
                outputCount = qty,
                derivedStep = step,
                derivedIndex = i,
                derivedLength = #rows,
            }
        end
    end
    return out
end

local sumFields = {
    "productionCost", "attributedCost", "transferredCost", "recoveryTotal",
    "saleCount", "producedCount", "consumedCount", "naturalRemainder",
    "levelingRemainder", "demandCount", "demandCost",
}

local function newAccounting()
    local a = { recoveryOutputs = {} }
    for _, key in ipairs(sumFields) do a[key] = 0 end
    return a
end

local function addAccounting(target, a, tick)
    for _, key in ipairs(sumFields) do target[key] = (target[key] or 0) + (a[key] or 0) end
    for _, output in ipairs(a.recoveryOutputs or {}) do
        target.recoveryOutputs[#target.recoveryOutputs + 1] = copy(output, tick)
    end
end

function R.GroupOutputs(outputs, tick)
    local grouped, index = {}, {}
    for _, output in ipairs(outputs or {}) do
        local key = table.concat({
            tostring(output.id),
            tostring(output.source or ""),
            tostring(output.unit or 0),
            output.missing and "1" or "0",
        }, "\031")
        local entry = index[key]
        if not entry then
            entry = copy(output)
            entry.count = 0
            entry.cost = 0
            entry.revenue = 0
            index[key] = entry
            grouped[#grouped + 1] = entry
        end
        entry.count = entry.count + (output.count or 0)
        entry.cost = entry.cost + (output.cost or 0)
        entry.revenue = entry.revenue + (output.revenue or 0)
        if tick then tick() end
    end
    return grouped
end

function R.Apply(result, snapshot, tick)
    if not result then return end
    snapshot = snapshot or {}
    local profitCap = cfgNum("PROFIT_CAP", 20)
    R.PROFIT_CAP = profitCap
    local frozen = R.Capture(snapshot, {
        profession = result.profession or snapshot.slug or snapshot.targetProfession,
        recoveryEnabled = result.recoveryEnabled,
        residualMass = snapshot.recovery and snapshot.recovery.residualMass,
    }, tick)
    result.recoveryRevision = R.REVISION
    result.recoveryEnabled = frozen.enabled
    result.residualMass = frozen.residualMass
    result.profitPriorityLimit = profitCap
    result.recoveryOptimized = frozen.enabled and result.scheme == "cheapest" and not result.procurement or false
    result.recoverySnapshot = copy(frozen, tick)
    result.recoveryQuoteMissing = 0
    for _, q in pairs(frozen.quotes or {}) do
        if q.missing then result.recoveryQuoteMissing = result.recoveryQuoteMissing + 1 end
        if tick then tick() end
    end
    result.recoveryFeeMissing = frozen.feePercent == nil or nil
    if result.recoveryOptimized and (result.recoveryQuoteMissing > 0 or result.recoveryFeeMissing) then
        result.optimal = false
    end
    result.purchaseTotal = result.total or 0
    result.recoveryTotal = 0
    result.saleOutputs = {}
    result.recoveryMissing = 0
    result.recoveryMissingItems = {}
    result.purchaseRemainders = {}
    result.demandAttribution = {}
    result.demandCost = 0
    result.demandNonCraftCost = 0
    result.recoveryAssumesAllSold = false
    result.recoveryEstimated = nil

    local actions = trace(result, snapshot)
    local pools, poolHeads, accounts, byID, byStep, byRecipe, formulaCosts, recipeCounts = {}, {}, {}, {}, {}, {}, {}, {}
    local function key(a) return tostring(a.profession or "") .. ":" .. tostring(a.spell or 0) end
    for i, a in ipairs(actions) do
        if a.type == "craft" or a.type == "specialization_quest" then
            local k = a.type == "specialization_quest" and ("quest:" .. tostring(a.quest and a.quest.id or a.goalID)) or key(a)
            local ac = newAccounting()
            ac.key = k
            ac.actionID = a.id
            ac.item = a.item
            ac.count = a.count or 0
            accounts[i] = ac
            if a.id then byID[a.id] = ac end
            if a.derivedStep then
                byStep[a.derivedStep] = ac
                local equivalent = result.steps and result.steps[a.derivedIndex]
                if equivalent and #result.steps == a.derivedLength and equivalent[3] == a.spell and equivalent[4] == a.count then
                    byStep[equivalent] = ac
                end
            end
            byRecipe[k] = byRecipe[k] or {}
            byRecipe[k][#byRecipe[k] + 1] = ac
            recipeCounts[k] = (recipeCounts[k] or 0) + max(1, a.count or 0)
        elseif a.type == "formula" and a.owner then
            formulaCosts[a.owner] = (formulaCosts[a.owner] or 0) + (a.cost or 0)
        end
        if tick then tick() end
    end

    local function put(id, n, cost, origin, owner, usable)
        if not id or not n or n <= 0 then return end
        local p = pools[id] or {}
        pools[id] = p
        p[#p + 1] = { count = n, cost = cost, origin = origin, owner = owner, usable = usable ~= false }
    end

    local function take(id, n, consumer, terminalDemand)
        local cost, remaining = 0, n
        local pool = pools[id] or {}
        local heads = poolHeads[id] or { 1, 1 }
        poolHeads[id] = heads
        for pass = 1, 2 do
            local index = heads[pass]
            while n > 0 and index <= #pool do
                local lot = pool[index]
                if tick then tick() end
                if lot.usable and (lot.origin == nil) == (pass == 1) and n > 0 and lot.count > 0 then
                    if not lot.origin and not lot.owner and consumer then
                        lot.owner = consumer.key
                        lot.ownerAccount = consumer
                    end
                    local used = min(n, lot.count)
                    local part = lot.cost * used / lot.count
                    lot.count = lot.count - used
                    lot.cost = lot.cost - part
                    n = n - used
                    cost = cost + part
                    if lot.origin then
                        if terminalDemand then
                            lot.origin.attributedCost = lot.origin.attributedCost + part
                            lot.origin.demandCost = lot.origin.demandCost + part
                            lot.origin.demandCount = lot.origin.demandCount + used
                        else
                            lot.origin.transferredCost = lot.origin.transferredCost + part
                            lot.origin.consumedCount = lot.origin.consumedCount + used
                        end
                    elseif terminalDemand then
                        result.demandNonCraftCost = result.demandNonCraftCost + part
                    end
                end
                if not lot.usable or (lot.origin == nil) ~= (pass == 1) or lot.count <= 0 then
                    index = index + 1
                else
                    break
                end
            end
            heads[pass] = index
        end
        return cost, remaining - n
    end

    for i, a in ipairs(actions) do
        if a.type == "buy" then
            put(a.item, a.count, a.cost or 0, nil, a.owner)
        elseif a.type == "seed" then
            put(a.item, a.count, 0, nil, nil, a.usableOutput)
        elseif a.type == "convert" then
            local cost = 0
            for _, input in ipairs(a.inputs or {}) do cost = cost + take(input[1], input[2]) end
            local outputN = 0
            for _, output in ipairs(a.outputs or {}) do outputN = outputN + (output[2] or 0) end
            if outputN > 0 then
                for _, output in ipairs(a.outputs) do
                    put(output[1], output[2], cost * output[2] / outputN, nil, a.owner, a.usableOutput)
                end
            end
        elseif accounts[i] then
            local ac = accounts[i]
            local cost = 0
            for _, input in ipairs(a.inputs or {}) do cost = cost + take(input[1], input[2], ac) end
            cost = cost + (formulaCosts[ac.key] or 0) * max(1, a.count or 0) / max(1, recipeCounts[ac.key] or 1)
            ac.productionCost = cost
            local outputN = 0
            for _, o in ipairs(a.outputs or {}) do outputN = outputN + (o[2] or 0) end
            ac.producedCount = outputN
            if outputN > 0 and a.type == "craft" then
                for _, o in ipairs(a.outputs) do put(o[1], o[2], cost * o[2] / outputN, ac, nil, a.usableOutput) end
            else
                ac.attributedCost = cost
            end
        end
        if tick then tick() end
    end

    for id, n in pairs(result.consumedDemands or {}) do
        local cost, consumed = take(id, n, nil, true)
        result.demandAttribution[#result.demandAttribution + 1] = { id = id, count = consumed, cost = cost }
        result.demandCost = result.demandCost + cost
        if tick then tick() end
    end
    table.sort(result.demandAttribution, function(a, b) return a.id < b.id end)

    result.retainedTools = {}
    local demandNonCraftCost = result.demandNonCraftCost
    for id, n in pairs(snapshot.retainedToolItems or result.retainedToolItems or {}) do
        local cost, retained = take(id, n, nil, true)
        if retained > 0 then
            result.retainedTools[#result.retainedTools + 1] = { id = id, count = retained, cost = cost }
        end
        if tick then tick() end
    end
    result.demandNonCraftCost = demandNonCraftCost

    local sold, missing = {}, {}
    for id, pool in pairs(pools) do
        for _, lot in ipairs(pool) do
            if tick then tick() end
            if lot.count > 0 then
                if lot.origin then
                    local ac = lot.origin
                    ac.attributedCost = ac.attributedCost + lot.cost
                    ac.saleCount = ac.saleCount + lot.count
                    local q = frozen.quotes[id] or { unit = 0, source = "unknown", missing = true }
                    local entry = sold[id]
                    if not entry then
                        entry = copy(q)
                        entry.id = id
                        entry.count = 0
                        entry.cost = 0
                        entry.revenue = 0
                        sold[id] = entry
                    end
                    local revenueVal = lot.count * (q.unit or 0)
                    entry.count = entry.count + lot.count
                    entry.cost = entry.cost + lot.cost
                    entry.revenue = entry.revenue + revenueVal
                    ac.recoveryTotal = ac.recoveryTotal + revenueVal
                    ac.recoveryOutputs[#ac.recoveryOutputs + 1] = {
                        id = id,
                        count = lot.count,
                        cost = lot.cost,
                        unit = q.unit or 0,
                        source = q.source,
                        revenue = revenueVal,
                        missing = q.missing,
                    }
                    if q.missing then missing[id] = true end
                else
                    result.purchaseRemainders[#result.purchaseRemainders + 1] = {
                        id = id,
                        count = lot.count,
                        cost = lot.cost,
                        owner = lot.owner,
                    }
                    local owner = lot.ownerAccount or (lot.owner and byRecipe[lot.owner] and byRecipe[lot.owner][1])
                    if owner then owner.attributedCost = owner.attributedCost + lot.cost end
                end
            end
        end
    end

    for _, ac in pairs(accounts) do
        local per = ac.count > 0 and ac.producedCount / ac.count or 0
        local required = ac.consumedCount + ac.demandCount
        local material = per > 0 and ceil(required / per) or 0
        ac.naturalRemainder = min(ac.saleCount, max(0, material * per - required))
        ac.levelingRemainder = ac.saleCount - ac.naturalRemainder
        if tick then tick() end
    end

    for id, entry in pairs(sold) do
        result.saleOutputs[#result.saleOutputs + 1] = entry
        result.recoveryTotal = result.recoveryTotal + entry.revenue
        if entry.supplyEstimated then result.recoveryEstimated = true end
        if entry.source == "ah" then result.recoveryAssumesAllSold = true end
        if missing[id] then
            result.recoveryMissing = result.recoveryMissing + 1
            result.recoveryMissingItems[#result.recoveryMissingItems + 1] = id
        end
        if tick then tick() end
    end
    table.sort(result.saleOutputs, function(a, b) return a.id < b.id end)
    table.sort(result.recoveryMissingItems)
    table.sort(result.purchaseRemainders, function(a, b) return a.id < b.id end)

    local function fill(step)
        local total = newAccounting()
        local found = false
        if byStep[step] then
            addAccounting(total, byStep[step], tick)
            found = true
        end
        if not found then
            for _, id in ipairs(step.actionIDs or {}) do
                if byID[id] then
                    addAccounting(total, byID[id], tick)
                    found = true
                end
            end
        end
        if not found and step.actionID and byID[step.actionID] then
            addAccounting(total, byID[step.actionID], tick)
            found = true
        end
        if not found then
            local r = recipeFor(step, snapshot)
            local k = step.kind == "specialization_quest" and ("quest:" .. tostring(step.goalID))
                or (r and (r.key or (tostring(r.profession) .. ":" .. tostring(r.spell or r.spellID))) or key({ profession = step.profession, spell = step[3] }))
            for _, a in ipairs(byRecipe[k] or {}) do addAccounting(total, a, tick) end
            local all = recipeCounts[k] or 0
            local count = step[4] or 0
            if all > 0 and count > 0 and count < all then
                local ratio = count / all
                for _, field in ipairs(sumFields) do total[field] = total[field] * ratio end
                for _, o in ipairs(total.recoveryOutputs) do
                    o.count = o.count * ratio
                    o.cost = o.cost * ratio
                    o.revenue = o.revenue * ratio
                end
            end
        end
        for _, field in ipairs(sumFields) do step[field] = total[field] end
        step.attributedCostExact = nil
        step.recoveryOutputs = R.GroupOutputs(total.recoveryOutputs, tick)
        step.netTotal = step.attributedCost - step.recoveryTotal
        step.costTransferred = step.saleCount == 0 and step.transferredCost > 0 or nil
        return step.attributedCost
    end

    local allocated = 0
    for _, step in ipairs(result.steps or {}) do
        allocated = allocated + fill(step)
        if tick then tick() end
    end
    local executionAllocated = 0
    for _, step in ipairs(result.executionSteps or {}) do
        executionAllocated = executionAllocated + fill(step)
        if tick then tick() end
    end

    local delta = result.purchaseTotal - result.demandNonCraftCost - allocated
    result.recoveryUnallocatedCost = delta
    local last = result.steps and result.steps[#result.steps]
    if last and math.abs(delta) > 1e-8 then
        last.attributedCost = last.attributedCost + delta
        last.netTotal = last.attributedCost - last.recoveryTotal
        result.recoveryUnallocatedCost = 0
    end
    local executionLast = result.executionSteps and result.executionSteps[#result.executionSteps]
    local executionDelta = result.purchaseTotal - result.demandNonCraftCost - executionAllocated
    if executionLast and executionLast ~= last and math.abs(executionDelta) > 1e-8 then
        executionLast.attributedCost = executionLast.attributedCost + executionDelta
        executionLast.netTotal = executionLast.attributedCost - executionLast.recoveryTotal
    end

    local function roundAttribution(list)
        local exact, rounded = 0, 0
        for _, step in ipairs(list or {}) do
            step.attributedCostExact = step.attributedCost
            exact = exact + step.attributedCostExact
            local nextRounded = floor(exact + 0.5 + 1e-8)
            step.attributedCost = nextRounded - rounded
            rounded = nextRounded
            step.netTotal = step.attributedCost - (step.recoveryTotal or 0)
            if tick then tick() end
        end
    end
    roundAttribution(result.steps)
    for _, step in ipairs(result.executionSteps or {}) do
        if step.attributedCostExact ~= nil then step.attributedCost = step.attributedCostExact end
    end
    roundAttribution(result.executionSteps)

    result.attributedTotal = result.purchaseTotal
    result.netTotal = result.purchaseTotal - result.recoveryTotal
    result.productPartial = result.recoveryMissing > 0
    return result
end

local delegateInvalidate = nil
local function registerDelegate()
    local API = getAPI()
    if not API or type(API.RegisterDelegate) ~= "function" then return end
    local prev = type(API.GetDelegate) == "function" and API.GetDelegate("pricing") or nil
    local impl = {}
    if type(prev) == "table" then
        for k, v in pairs(prev) do impl[k] = v end
    end
    if not impl.NPCSellPriceOf then
        impl.NPCSellPriceOf = R.NPCSellPriceOf
    end
    local prevInv = type(prev) == "table" and type(prev.Invalidate) == "function" and prev.Invalidate or nil
    if prevInv == delegateInvalidate and delegateInvalidate ~= nil then
        impl.Invalidate = delegateInvalidate
    elseif prevInv and prevInv ~= R.Invalidate then
        local active = false
        delegateInvalidate = function()
            if active then return end
            active = true
            R.Invalidate()
            pcall(prevInv)
            active = false
        end
        impl.Invalidate = delegateInvalidate
    else
        impl.Invalidate = R.Invalidate
    end
    API.RegisterDelegate("pricing", impl)
end

R.RegisterDelegate = registerDelegate
registerDelegate()
