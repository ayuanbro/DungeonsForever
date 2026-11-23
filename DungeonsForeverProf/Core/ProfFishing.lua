local _, ns = ...
if type(ns) ~= "table" then ns = _G.DF_NS or {} end
local gns = _G.DF_NS

local P = { DataSchema = 2 }
ns.ProfFishing = P
if type(gns) == "table" and gns ~= ns then
    gns.ProfFishing = P
end

local floor, ceil, min, max = math.floor, math.ceil, math.min, math.max

local function getDS()
    return ns.ProfDataStore or (type(gns) == "table" and gns.ProfDataStore) or nil
end

local function getCond()
    return ns.ProfConditions or (type(gns) == "table" and gns.ProfConditions) or nil
end

local function getEconomy()
    return ns.ProfEconomy or (type(gns) == "table" and gns.ProfEconomy) or nil
end

local function getSolverCfg()
    return ns.SolverConfig or (type(gns) == "table" and gns.SolverConfig) or nil
end

local function getRouteAuto()
    return ns.ProfRouteAuto or (type(gns) == "table" and gns.ProfRouteAuto) or nil
end

local function getExecution()
    return ns.ProfExecution or (type(gns) == "table" and gns.ProfExecution) or nil
end

local function getRecovery()
    return ns.ProfRecovery or (type(gns) == "table" and gns.ProfRecovery) or nil
end

local function clone(value)
    if type(value) ~= "table" then return value end
    local meta = getmetatable(value)
    if type(meta) == "table" and type(meta.__profLearningMaterialize) == "function" then
        value = meta.__profLearningMaterialize(value)
    end
    local out = {}
    for k, v in pairs(value) do out[k] = clone(v) end
    return out
end

local function normalizeFaction(raw)
    if raw == "A" or raw == "Alliance" then return "A" end
    if raw == "H" or raw == "Horde" then return "H" end
    if raw == "N" or raw == "Neutral" or raw == "Both" then return "N" end
    return nil
end

local function mergeExtraFishAreas(itemID, areas, DS)
    if type(itemID) ~= "number" or not DS or type(DS.ExtraSources) ~= "function" then
        return areas
    end
    local extras = DS.ExtraSources(itemID)
    if type(extras) ~= "table" or #extras == 0 then return areas end
    local seen = {}
    for _, a in ipairs(areas) do
        if type(a) == "table" and type(a.areaID) == "number" then
            seen[a.areaID] = true
        end
    end
    local added = false
    for _, e in ipairs(extras) do
        if type(e) == "table" and e.sourceKind == "fished" and e.targetType == "zone" and type(e.targetID) == "number" then
            if not seen[e.targetID] then
                seen[e.targetID] = true
                areas[#areas + 1] = {
                    areaID = e.targetID,
                    dropRatePct = e.dropRatePct,
                    sampleCount = e.sampleCount,
                    avgStack = e.avgStack,
                }
                added = true
            end
        end
    end
    return areas, added
end

local function fishingData(opts)
    opts = opts or {}
    local DS = getDS()
    local source = opts.fishingData
        or (opts.snapshot and opts.snapshot.fishingRoutes)
        or (DS and type(DS.FishingGuide) == "function" and DS.FishingGuide())
        or {}
    local out = { fish = {}, authored = {} }
    local authored = out.authored
    for _, stage in ipairs(source.fishingSteps or {}) do
        for _, id in ipairs(stage.fishIDs or {}) do
            if type(id) == "number" then authored[id] = true end
        end
    end
    for id, raw in pairs(source.fish or {}) do
        if type(raw) == "table" then
            local numID = tonumber(id)
            local areas = clone(raw.areas or raw.a or {})
            if numID then mergeExtraFishAreas(numID, areas, DS) end
            local f = {}
            for key, value in pairs(raw) do f[key] = clone(value) end
            f.areas = areas
            f.catchRate = raw.catchRate or raw.rate or (type(raw.dropRatePct) == "number" and raw.dropRatePct / 100 or nil)
            f.seasonal = raw.seasonal or raw.season
            f.timeRestricted = raw.timeRestricted or raw.night
            f.requirementsKnown = raw.restrictionsVerified == true or (numID ~= nil and authored[numID] == true)
            f.restrictionsReference = (raw.restrictionsVerified ~= true and numID ~= nil and authored[numID] == true) or nil
            out.fish[numID or id] = f
        end
    end
    return out
end
P.Data = fishingData

local function fishRecord(data, itemID)
    local fish = data.fish
    local found = fish and (fish[itemID] or fish[tostring(itemID)])
    if found then return found end
    if type(itemID) ~= "number" then return nil end
    local DS = getDS()
    if not DS or type(DS.ExtraSources) ~= "function" then return nil end
    local areas = {}
    local _, added = mergeExtraFishAreas(itemID, areas, DS)
    if not added then return nil end
    local authored = data.authored or {}
    local rate
    for _, a in ipairs(areas) do
        if type(a.dropRatePct) == "number" then
            local r = a.dropRatePct / 100
            if not rate or r > rate then rate = r end
        end
    end
    local f = {
        areas = areas,
        catchRate = rate,
        requirementsKnown = authored[itemID] == true,
        restrictionsReference = authored[itemID] == true or nil,
    }
    data.fish[itemID] = f
    return f
end

local function vendorOK(o, snap, DS, Cond, condCtx)
    if type(o) ~= "table" then return false end
    local unlimited = (o.unlimited == true) or (type(o.maxStock) == "number" and o.maxStock < 0)
    if not unlimited or o.available == false or o.purchasable == false or o.maxStock == 0 then
        return false
    end
    local isPure = not o.hasExtendedCost
        and (not o.currencyID or o.currencyID == 0)
        and (type(o.currencies) ~= "table" or #o.currencies == 0)
        and (type(o.costItems) ~= "table" or #o.costItems == 0)
    if not isPure then return false end
    local price = o.price ~= nil and o.price or o.priceCopper
    if type(price) ~= "number" or price ~= price or price < 0 or price >= math.huge then
        return false
    end
    local bundle = o.quantity or o.bundleSize or 1
    if type(bundle) ~= "number" or bundle < 1 or bundle ~= floor(bundle) then
        return false
    end
    local npcID = tonumber(o.npcID or o.id)
    local npc = npcID and DS and type(DS.Npc) == "function" and DS.Npc(npcID) or nil
    local side = normalizeFaction(o.faction or (npc and npc.faction))
    local snapSide = normalizeFaction(snap and snap.faction)
    if side and side ~= "N" and snapSide and side ~= snapSide then
        return false
    end
    if Cond then
        if npc and type(Cond.IsNpcAccessible) == "function" and not Cond.IsNpcAccessible(npc, condCtx) then
            return false
        end
        if type(o.conditions) == "table" and #o.conditions > 0
            and type(Cond.IsMet) == "function" and not Cond.IsMet(o.conditions, condCtx) then
            return false
        end
    end
    return true
end

function P.Capture(opts)
    local E = getEconomy()
    if E and type(E.Capture) == "function" then
        return E.Capture("cooking", opts or {})
    end
    if type(opts) == "table" and type(opts.snapshot) == "table" then
        return opts.snapshot
    end
    return {
        targetProfession = "cooking",
        professions = {},
        recipes = {},
        known = {},
        offers = {},
        prices = {},
        nonAuctionable = {},
    }
end

local function ease(fish)
    local skill, rate
    for _, area in ipairs(fish.areas or {}) do
        local required = area.minSkill or fish.minSkill
        local observed = fish.catchRate or area.catchRate or (type(area.dropRatePct) == "number" and area.dropRatePct / 100 or nil)
        if required and (not skill or required < skill) then
            skill = required
            rate = observed
        elseif required and required == skill and observed then
            rate = max(rate or observed, observed)
        end
    end
    if not skill then skill = fish.minSkill end
    return skill, rate
end

local function recipeMats(r)
    if type(r.mats) == "table" then return r.mats end
    local out = {}
    if type(r.reagents) == "table" then
        for i = 1, #r.reagents do
            local rg = r.reagents[i]
            if type(rg) == "table" then
                local id = rg.itemID or rg.id or rg[1]
                local cnt = rg.count or rg[2] or 1
                if type(id) == "number" then
                    out[#out + 1] = { id, cnt }
                end
            end
        end
    end
    return out
end

local function gainFallback(r, skill, solverCfg)
    local rates = type(solverCfg) == "table" and solverCfg.DIFFICULTY_RATES or nil
    local gYellow = (type(rates) == "table" and rates.G_YELLOW) or 0.5
    local gGreen = (type(rates) == "table" and rates.G_GREEN) or 0.05
    local grey = r.grey
    if type(grey) ~= "number" or skill >= grey then return 0 end
    local yellow = r.yellow or r.learn or r.learnedAt or r.orange or 1
    local green = r.green or grey
    if skill < yellow then return 1 end
    if skill < green then return gYellow end
    return gGreen
end

function P.Compute(opts)
    opts = opts or {}
    local E = getEconomy()
    local DS = getDS()
    local Cond = getCond()
    local solverCfg = getSolverCfg()
    local ra = getRouteAuto()
    local xp = getExecution()
    local recMod = getRecovery()

    local cap = (type(solverCfg) == "table" and type(solverCfg.CAP) == "number" and solverCfg.CAP) or 300
    local defTarget = (type(solverCfg) == "table" and type(solverCfg.DEFAULT_TARGET) == "number" and solverCfg.DEFAULT_TARGET) or cap

    local data = fishingData(opts)
    local snap = P.Capture(opts) or {}
    snap.professions = snap.professions or {}
    snap.recipes = snap.recipes or {}
    snap.known = snap.known or {}
    snap.offers = snap.offers or {}
    snap.prices = snap.prices or {}
    snap.nonAuctionable = snap.nonAuctionable or {}

    local source = opts.fishingData
        or (opts.snapshot and opts.snapshot.fishingRoutes)
        or (DS and type(DS.FishingGuide) == "function" and DS.FishingGuide())
        or {}
    local routes = { cookingSteps = opts.cookingGuide or source.cookingSteps or {} }
    local start = max(1, min(cap, floor(opts.start or (snap.professions.cooking or {}).cur or 1)))
    local target = max(start, min(cap, floor(opts.target or defTarget)))

    local out = {
        planVersion = 2,
        scheme = "fishing",
        routeMode = "fishing",
        start = start,
        target = target,
        steps = {},
        executionSteps = {},
        actions = {},
        mats = {},
        fishMaterials = {},
        formulas = {},
        diagnostics = {},
        blockingDiagnostics = {},
        firstAt = {},
        gaps = {},
        total = 0,
        matTotal = 0,
        vendorTotal = 0,
        ahTotal = 0,
        formulasTotal = 0,
        formulaAHTotal = 0,
        formulaVendorTotal = 0,
        formulaRevision = 1,
        formulaComplete = true,
        completeCost = true,
        costComplete = true,
        priced = true,
        crafts = 0,
        productAH = 0,
        productNPC = 0,
        productPartial = false,
        optimal = false,
        searchComplete = true,
        status = "complete",
        targetUnlearned = not snap.professions.cooking or snap.professions.cooking.unlearned == true,
        professionPolicy = 1,
        stamp = (type(_G.time) == "function" and _G.time()) or (type(os) == "table" and type(os.time) == "function" and os.time()) or 0,
        fishingRouteRevision = 2,
    }

    local condCtx = {
        faction = snap.faction or opts.faction,
        quests = snap.completedQuests or opts.quests,
        items = snap.ownedSourceItems or opts.items,
        reputations = snap.reputations or opts.reputations,
        level = snap.level or opts.level,
        strict = opts.strict,
    }

    local candidates, blocked = {}, {}
    local function fail(code, r, id)
        local key = code .. ":" .. tostring(r and (r.spell or r.spellID) or "") .. ":" .. tostring(id or "")
        blocked[key] = { code = code, spell = r and (r.spell or r.spellID), recipe = r and r.key, profession = "cooking", item = id }
    end

    local function gainOf(r, skill)
        if E and type(E.Gain) == "function" then
            return E.Gain(r, skill)
        end
        return gainFallback(r, skill, solverCfg)
    end

    for _, rawR in ipairs(snap.recipes) do
        if rawR.profession == "cooking" and (rawR.availability == nil or rawR.availability == "live") then
            local r = clone(rawR)
            r.spell = r.spell or r.spellID
            r.learn = r.learn or r.learnedAt or r.orange
            r.item = r.item or r.outputItemID
            r.mats = recipeMats(r)
            if not r.key and r.spell then
                r.key = "cooking:" .. tostring(r.spell)
            end

            local valid = true
            local fish = {}
            local skill, rate = 0, 1
            local learningUnknown = false
            if E and type(E.LearningEligibility) == "function" then
                local eligible, reason, detail = E.LearningEligibility(r, snap)
                if not eligible then
                    valid = false
                    fail(reason or "learningRequirementsUnknown", r)
                elseif detail and detail.status == "unknown" then
                    learningUnknown = true
                end
            end
            if E and type(E.Policy) == "function" and E.Policy(opts.exclusions, r) then
                valid = false
                fail("excluded", r)
            end
            if r.clientUnavailable or r.cooldown or r.cooldownUnknown or r.clientPending or r.outputConflict then
                valid = false
            end
            if (r.availabilityUnknown or r.verified == false) and not r.clientAvailable
                and not (snap.known[r.key] or snap.known[r.spell]) then
                valid = false
            end
            for _, m in ipairs(r.mats) do
                local f = fishRecord(data, m[1])
                if f then
                    fish[#fish + 1] = m[1]
                    local sk, rt = ease(f)
                    if not sk or not f.requirementsKnown then
                        valid = false
                        fail("fishingRequirementsUnknown", r, m[1])
                    else
                        skill = max(skill, sk)
                    end
                    if rt then rate = min(rate, rt) end
                    if f.restrictionsReference then out.fishingReference = true end
                    if f.restricted or f.seasonal or f.timeRestricted or f.uncertain then valid = false end
                else
                    local found = false
                    local offersList = snap.offers[m[1]]
                    if offersList == nil and DS and type(DS.VendorOffers) == "function" then
                        local vo = DS.VendorOffers(m[1])
                        offersList = type(vo) == "table" and vo.offers or nil
                    end
                    for _, o in ipairs(offersList or {}) do
                        if vendorOK(o, snap, DS, Cond, condCtx) then
                            found = true
                            break
                        end
                    end
                    local price = snap.prices[m[1]]
                    local supply = E and type(E.AuctionSupplyOf) == "function" and E.AuctionSupplyOf(snap, m[1]) or nil
                    local auction = not snap.nonAuctionable[m[1]] and type(price) == "number"
                        and price > 0 and price < math.huge and (not supply or supply.quantity ~= 0)
                    if not found and not auction then
                        valid = false
                        fail(type(price) == "number" and price > 0 and supply and supply.quantity == 0
                            and "auctionSupplyLimited" or "materialUnavailable", r, m[1])
                    end
                end
            end
            local formula
            if valid and #fish > 0 and E and type(E.FormulaFor) == "function" then
                formula = E.FormulaFor(r, snap)
                if formula and not formula.usable then
                    valid = false
                    fail(formula.reason or "formulaUnavailable", r, formula.id)
                end
            end
            if valid and #fish > 0 and type(r.learn) == "number" and type(r.grey) == "number" then
                candidates[#candidates + 1] = {
                    r = r,
                    fish = fish,
                    skill = skill,
                    rate = rate,
                    formula = formula,
                    learningUnknown = learningUnknown,
                }
            end
        end
    end

    local cur = start
    local guide = routes.cookingSteps or {}
    local guard = 0
    if opts.routeSkeleton then
        local valid = true
        for _, src in ipairs(opts.routeSkeleton.steps) do
            local selected
            for _, candidate in ipairs(candidates) do
                if candidate.r.spell == src[3] then
                    selected = candidate
                    break
                end
            end
            local r = selected and selected.r
            if not r or r.learn > src[1] or src[1] ~= cur then
                valid = false
                break
            end
            out.steps[#out.steps + 1] = {
                src[1], src[2], src[3], src[4],
                profession = "cooking",
                role = "level",
                reason = "level",
                recipe = clone(r),
                item = r.item,
                cost = 0,
                leveling = true,
                stepIndex = #out.steps + 1,
                fishing = {},
                fishMaterials = {},
                fishingAreas = {},
                actionIDs = {},
            }
            if selected.learningUnknown then out.learningRequirementsUnknown = true end
            out.crafts = out.crafts + src[4]
            cur = src[2]
        end
        if not valid then
            out.steps = clone(opts.routeSkeleton.steps)
            out.executionSteps = clone(out.steps)
            out.status = "recalculate_required"
            out.feasible = false
            out.costComplete = false
            out.completeCost = false
            out.priced = false
            for _, d in pairs(blocked) do out.diagnostics[#out.diagnostics + 1] = d end
            out.diagnostics[#out.diagnostics + 1] = { code = "fishingRecipeGap", profession = "cooking" }
            return out
        end
    end

    while not opts.routeSkeleton and cur < target and guard < 1000 do
        guard = guard + 1
        local preferred, stageTo
        for _, stage in ipairs(guide) do
            local a = stage.from or stage[1] or stage.learnedAt or stage.orange
            local b = stage.to or stage[2] or stage.grey
            if type(a) == "number" and type(b) == "number" and a <= cur and cur < b then
                preferred = stage.spell or stage.spellID or stage[3]
                stageTo = b
                break
            end
        end
        local best
        for _, c in ipairs(candidates) do
            local r = c.r
            if r.learn <= cur and cur < r.grey then
                if r.spell == preferred then
                    best = c
                    break
                end
                local g = gainOf(r, cur)
                if not best or c.skill < best.skill or (c.skill == best.skill and
                    (c.rate > best.rate or (c.rate == best.rate and (g > gainOf(best.r, cur)
                    or (g == gainOf(best.r, cur) and r.spell < best.r.spell))))) then
                    best = c
                end
            end
        end
        if not best then break end
        local r = best.r
        local to = min(target, stageTo or target, r.grey)
        if best.learningUnknown then
            out.learningRequirementsUnknown = true
            local seen = false
            for _, diagnostic in ipairs(out.diagnostics) do
                if diagnostic.code == "learningRequirementsUnknown" and diagnostic.spell == r.spell then
                    seen = true
                    break
                end
            end
            if not seen then
                out.diagnostics[#out.diagnostics + 1] = { code = "learningRequirementsUnknown", spell = r.spell, detail = r.key }
            end
        end
        if not preferred or r.spell ~= preferred then
            for _, c in ipairs(candidates) do
                if cur < c.r.learn and c.r.learn < to then to = c.r.learn end
            end
        end
        if to <= cur then break end
        local expected = 0
        for skill = cur, to - 1 do
            local gain = gainOf(r, skill)
            if gain <= 0 then
                to = skill
                break
            end
            expected = expected + 1 / gain
        end
        local count = max(1, ceil(expected - 1e-7))
        local step = out.steps[#out.steps]
        if not step or step[3] ~= r.spell then
            step = {
                cur, to, r.spell, count,
                profession = "cooking",
                role = "level",
                reason = "level",
                recipe = clone(r),
                item = r.item,
                cost = 0,
                leveling = true,
                stepIndex = #out.steps + 1,
                fishing = {},
                fishMaterials = {},
                fishingAreas = {},
                actionIDs = {},
            }
            out.steps[#out.steps + 1] = step
        else
            step[2] = to
            step[4] = step[4] + count
        end
        out.crafts = out.crafts + count
        cur = to
    end

    local fishOf, matOf = {}, {}
    for _, step in ipairs(out.steps) do
        local r = step.recipe
        for _, m in ipairs(r.mats) do
            local need = m[2] * step[4]
            local f = fishRecord(data, m[1])
            if f then
                local entry = fishOf[m[1]]
                if not entry then
                    entry = {
                        id = m[1],
                        count = 0,
                        need = 0,
                        source = "fishing",
                        areas = clone(f.areas or {}),
                        minSkill = f.minSkill,
                        noGetaway = f.noGetaway,
                        catchRate = f.catchRate,
                        name = f.name,
                    }
                    fishOf[m[1]] = entry
                    out.fishMaterials[#out.fishMaterials + 1] = entry
                end
                entry.count = entry.count + need
                entry.need = entry.count
                step.fishing[#step.fishing + 1] = { id = m[1], count = need, need = need, source = "fishing", areas = clone(f.areas or {}) }
                step.fishMaterials = step.fishing
                for _, area in ipairs(f.areas or {}) do
                    step.fishingAreas[#step.fishingAreas + 1] = clone(area)
                end
            else
                local entry = matOf[m[1]]
                if not entry then
                    entry = { id = m[1], need = 0 }
                    matOf[m[1]] = entry
                end
                entry.need = entry.need + need
            end
            out.firstAt[m[1]] = out.firstAt[m[1]] or step[1]
        end
    end

    if E and type(E.CollectFormulas) == "function" then
        out.formulas, out.formulasTotal, out.formulaComplete = E.CollectFormulas(out.steps, "cooking", snap)
    else
        out.formulas, out.formulasTotal, out.formulaComplete = {}, 0, true
    end
    out.formulas = out.formulas or {}

    local remaining = {}
    local considerSupply = E and type(E.ConsiderAuctionSupply) == "function" and E.ConsiderAuctionSupply(snap)
    for id, supply in pairs(considerSupply and snap.auctionSupply or {}) do
        if type(supply) == "table" and type(supply.quantity) == "number" then
            remaining[id] = max(0, supply.quantity)
        end
    end

    out.formulasTotal, out.formulaComplete = 0, true
    for i, entry in ipairs(out.formulas) do
        local f = entry
        if matOf[f.id] and ra and type(ra.PreferSharedFormula) == "function" then
            f = ra.PreferSharedFormula(f, matOf[f.id].need, { snapshot = snap, auctionRemaining = remaining }) or f
            out.formulas[i] = f
        end
        out.formulasTotal = out.formulasTotal + (f.cost or 0)
        out.formulaComplete = out.formulaComplete and f.costComplete == true and f.usable == true
        out.referencePrices = out.referencePrices or (f.offer and f.offer.reference)
        if f.availabilityUncertain then
            out.diagnostics[#out.diagnostics + 1] = { code = "formulaStockUnknown", item = f.id }
        end
        if f.source == "vendor" or f.source == "trainer" or (f.source == "acquire" and f.acquisitionKind == "currency") then
            out.formulaVendorTotal = out.formulaVendorTotal + (f.cost or 0)
        elseif f.source == "ah" then
            out.formulaAHTotal = out.formulaAHTotal + (f.cost or 0)
            if remaining[f.id] ~= nil then remaining[f.id] = max(0, remaining[f.id] - (f.count or 1)) end
        end
        for _, step in ipairs(out.steps) do
            local owns = false
            for _, ref in ipairs(f.recipes or {}) do
                if ref.spell == step[3] then owns = true end
            end
            if owns then
                step.cost = step.cost + (f.cost or 0)
                step.unpriced = step.unpriced or f.unpriced
                break
            end
        end
    end

    local materialComplete, materialAvailable = true, true
    for id, need in pairs(matOf) do
        local entries, total, complete, reason
        if ra and type(ra.MaterialPurchases) == "function" then
            entries, total, complete, reason = ra.MaterialPurchases(id, need.need, { snapshot = snap, auctionRemaining = remaining })
        else
            entries, total, complete, reason = {}, 0, false, "materialUnavailable"
        end
        entries = entries or {}
        materialComplete = materialComplete and complete == true
        if complete ~= true then
            local code = reason == "auctionSupplyInsufficient" and "auctionSupplyLimited" or reason or "materialUnavailable"
            out.diagnostics[#out.diagnostics + 1] = {
                code = code,
                item = id,
                required = need.need,
                available = remaining[id],
                profession = "cooking",
            }
            if code == "materialUnavailable" or code == "auctionSupplyLimited" then
                materialAvailable = false
                out.blockingDiagnostics[#out.blockingDiagnostics + 1] = {
                    code = code,
                    item = id,
                    required = need.need,
                    available = remaining[id],
                    profession = "cooking",
                }
            end
        end
        local ledger = {}
        for _, raw in ipairs(entries) do
            local entry = clone(raw)
            entry.id = entry.id or entry[1] or id
            entry.count = entry.count or entry[2] or 0
            entry[1], entry[2] = entry.id, entry.count
            if entry.source == "ah" then
                if remaining[id] ~= nil and not entry.unavailable then
                    remaining[id] = max(0, remaining[id] - entry.count)
                end
                out.ahTotal = out.ahTotal + (entry.cost or 0)
            elseif entry.source == "vendor" then
                out.vendorTotal = out.vendorTotal + (entry.cost or 0)
            end
            out.referencePrices = out.referencePrices or entry.reference
            out.mats[#out.mats + 1] = entry
            ledger[#ledger + 1] = { entry = entry, used = 0 }
        end
        out.matTotal = out.matTotal + (total or 0)
        local index = 1
        for _, step in ipairs(out.steps) do
            for _, m in ipairs(step.recipe.mats) do
                if m[1] == id then
                    if complete ~= true then step.unpriced = true end
                    local left = m[2] * step[4]
                    while left > 0 and ledger[index] do
                        local row = ledger[index]
                        local entry = row.entry
                        local size = entry.source == "vendor" and (entry.bundleSize or 1) or 1
                        local quantity = min(left, max(0, entry.count - row.used))
                        local packPrice = entry.bundlePrice or (entry.cost or 0) / max(1, entry.count) * size
                        step.cost = step.cost + (ceil((row.used + quantity) / size) - ceil(row.used / size)) * packPrice
                        row.used = row.used + quantity
                        left = left - quantity
                        if row.used >= entry.count then index = index + 1 end
                    end
                end
            end
        end
    end

    out.vendorTotal = out.vendorTotal + out.formulaVendorTotal
    out.ahTotal = out.ahTotal + out.formulaAHTotal
    out.total = out.matTotal + out.formulasTotal
    out.costComplete = out.formulaComplete and materialComplete and not out.learningRequirementsUnknown
    out.completeCost = out.costComplete
    out.priced = out.costComplete
    out.plannedTo = cur
    out.targetReached = cur >= target
    out.partial = cur > start and cur < target
    out.feasible = (#out.steps > 0 or out.targetReached) and materialAvailable
    if not out.costComplete then out.status = "incomplete" end
    if not out.targetReached then
        out.status = "incomplete"
        out.gaps = { { cur, target } }
        out.remainingUnknown = true
        for _, d in pairs(blocked) do out.blockingDiagnostics[#out.blockingDiagnostics + 1] = d end
        out.blockingDiagnostics[#out.blockingDiagnostics + 1] = { code = "fishingRecipeGap", profession = "cooking" }
        if not out.feasible then out.diagnostics = clone(out.blockingDiagnostics) end
    end

    for i, step in ipairs(out.steps) do
        local id = "fishing-cook:" .. i
        step.actionID = id
        step.actionIDs = { id }
        local inputs = {}
        for _, m in ipairs(step.recipe.mats) do inputs[#inputs + 1] = { m[1], m[2] * step[4] } end
        out.actions[#out.actions + 1] = {
            id = id,
            type = "craft",
            profession = "cooking",
            spell = step[3],
            count = step[4],
            from = step[1],
            to = step[2],
            reason = "level",
            inputs = inputs,
            item = step.item,
            outputs = step.item and { { step.item, (step.recipe.count or 1) * step[4] } } or {},
        }
    end

    out.executionSteps = clone(out.steps)
    if xp and type(xp.NormalizePlan) == "function" then
        out = xp.NormalizePlan("cooking", out) or out
    end
    table.sort(out.mats, function(a, b) return a.id < b.id end)
    table.sort(out.fishMaterials, function(a, b) return (out.firstAt[a.id] or 0) < (out.firstAt[b.id] or 0) end)
    if E and type(E.SummarizeAuctionSupply) == "function" then
        E.SummarizeAuctionSupply(out, snap)
    end
    if recMod and type(recMod.Apply) == "function" then
        recMod.Apply(out, snap)
    end
    if ra and type(ra.StampVendorQuotes) == "function" then
        return ra.StampVendorQuotes(out) or out
    end
    return out
end

local function computeFishing(slug, opts)
    if slug ~= "cooking" then return nil end
    return P.Compute(opts)
end

P.ComputeFishing = computeFishing

function P.AttachRouteAuto(ra)
    local target = ra or getRouteAuto() or {}
    ns.ProfRouteAuto = target
    if type(gns) == "table" and gns ~= ns then
        gns.ProfRouteAuto = target
    end
    target.ComputeFishing = computeFishing
    return target
end

P.AttachRouteAuto()
