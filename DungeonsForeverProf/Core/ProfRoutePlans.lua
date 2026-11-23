local _, ns = ...
if type(ns) ~= "table" then ns = _G.DF_NS or {} end
local gns = _G.DF_NS

local RA = ns.ProfRouteAuto or (type(gns) == "table" and gns.ProfRouteAuto) or {}
ns.ProfRouteAuto = RA
if type(gns) == "table" and gns ~= ns then
    gns.ProfRouteAuto = RA
end

local run = ns.ProfSolverRun or (type(gns) == "table" and gns.ProfSolverRun) or {}
ns.ProfSolverRun = run
if type(gns) == "table" and gns ~= ns then
    gns.ProfSolverRun = run
end

local quickCompute, clearPrices, baseOptions, baseFixedPlan =
    RA._BaseCompute or RA.Compute,
    RA._BaseInvalidate or RA.Invalidate,
    RA._BaseOptionsFor or RA.OptionsFor,
    RA._BaseFixedPlan or RA.FixedPlan

local function getBaseCompute()
    return quickCompute or RA._BaseCompute or RA.ComputeFishing
end

local function getBaseInvalidate()
    return clearPrices or RA._BaseInvalidate
end

local function getBaseOptions()
    return baseOptions or RA._BaseOptionsFor
end

local function getBaseFixedPlan()
    return baseFixedPlan or RA._BaseFixedPlan
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

local function getDB()
    return ns.ProfDB or (type(gns) == "table" and gns.ProfDB) or nil
end

local function getSettings()
    return ns.ProfSettings or (type(gns) == "table" and gns.ProfSettings) or getDB()
end

local function getSolverCfg()
    return ns.SolverConfig or (type(gns) == "table" and gns.SolverConfig) or nil
end

local function getProfCfg()
    return ns.ProfessionsConfig or (type(gns) == "table" and gns.ProfessionsConfig) or nil
end

local function getPricingCfg()
    return ns.PricingConfig or (type(gns) == "table" and gns.PricingConfig) or nil
end

local function getAPI()
    return ns.ProfAPI or (type(gns) == "table" and gns.ProfAPI) or nil
end

local function getAuctionBridge()
    return ns.AuctionBridge or (type(gns) == "table" and gns.AuctionBridge) or nil
end

local function getIdle()
    return ns.ProfIdle or (type(gns) == "table" and gns.ProfIdle) or nil
end

local jobs, results, active, listeners, progressListeners = {}, {}, {}, {}, {}
local planPrevMem = {}
local serial, revision = 0, 0
local legacyRun
local lastRunSlug
local hookedBridge
local invalidating = false
local MODEL = 1

local function cfgCap()
    local cfg = getSolverCfg()
    return (type(cfg) == "table" and type(cfg.CAP) == "number" and cfg.CAP) or 300
end

local function cfgDefaultTarget()
    local cfg = getSolverCfg()
    return (type(cfg) == "table" and type(cfg.DEFAULT_TARGET) == "number" and cfg.DEFAULT_TARGET) or 300
end

local function cfgCpuLimitMs()
    local cfg = getSolverCfg()
    local b = type(cfg) == "table" and type(cfg.COROUTINE_BUDGET) == "table" and cfg.COROUTINE_BUDGET or nil
    return (b and type(b.cpuLimitMs) == "number" and b.cpuLimitMs) or 8000
end

local function cfgDefaultFee()
    local pcfg = getPricingCfg()
    return (type(pcfg) == "table" and type(pcfg.DEFAULT_RECOVERY_FEE_PCT) == "number" and pcfg.DEFAULT_RECOVERY_FEE_PCT) or 5
end

local function isFixedOnly(slug)
    if type(slug) ~= "string" or slug == "" then return false end
    local cfg = getProfCfg()
    local entry = type(cfg) == "table" and type(cfg.BY_SLUG) == "table" and cfg.BY_SLUG[slug]
    if type(entry) == "table" then return entry.fixedOnly == true end
    return slug == "first-aid" or slug == "poisons"
end

local function adaptiveSliceMs()
    local cfg = getSolverCfg()
    local b = type(cfg) == "table" and type(cfg.COROUTINE_BUDGET) == "table" and cfg.COROUTINE_BUDGET or nil
    local a = b and type(b.adaptiveSlice) == "table" and b.adaptiveSlice or nil
    local defFps = (a and type(a.defaultFps) == "number" and a.defaultFps) or 60
    local lowThr = (a and type(a.lowFpsThreshold) == "number" and a.lowFpsThreshold) or 25
    local lowMs = (a and type(a.lowFpsMs) == "number" and a.lowFpsMs) or 0.6
    local frac = (a and type(a.frameFraction) == "number" and a.frameFraction) or 0.09
    local minMs = (a and type(a.minMs) == "number" and a.minMs) or 0.8
    local maxMs = (a and type(a.maxMs) == "number" and a.maxMs) or 2.25
    local fps = type(_G.GetFramerate) == "function" and _G.GetFramerate() or defFps
    if type(fps) ~= "number" or fps <= 0 then fps = defFps end
    if fps < lowThr then return lowMs end
    return math.min(maxMs, math.max(minMs, (1000 / fps) * frac))
end

local function learningPolicy()
    local E = getEconomy()
    if E and type(E.LearningPolicyFingerprint) == "function" then
        local ok, v = pcall(E.LearningPolicyFingerprint)
        if ok and v ~= nil then return v end
    end
    return "native-learning:7:native-route-eligibility"
end

local function learningStale(result)
    result.stale = true
    result.staleReason = "learning-data"
    result.learningBlocked = true
    result.learningBlockReason = "learningPolicyChanged"
    result.status = "recalculate_required"
    result.learningComplete = false
    result.completeCost = false
    result.optimal = false
    result.diagnostics = result.diagnostics or {}
    local found = false
    for _, d in ipairs(result.diagnostics) do
        if d.code == "learningPolicyChanged" then found = true; break end
    end
    if not found then result.diagnostics[#result.diagnostics + 1] = { code = "learningPolicyChanged" } end
    return result
end

local function now()
    if type(_G.time) == "function" then
        local ok, v = pcall(_G.time)
        if ok and type(v) == "number" then return v end
    end
    if type(os) == "table" and type(os.time) == "function" then
        return os.time()
    end
    return 0
end

local function copy(value, seen, preserveSnapshot)
    if type(value) ~= "table" then return value end
    local view = getmetatable(value)
    if type(view) == "table" and type(view.__profLearningMaterialize) == "function" then
        value = view.__profLearningMaterialize(value)
    end
    seen = seen or {}
    if seen[value] then return seen[value] end
    local out = {}
    seen[value] = out
    for k, v in pairs(value) do
        if preserveSnapshot and k == "snapshot" then
            out[k] = v
        elseif type(k) == "string" or type(k) == "number" then
            local kind = type(v)
            if kind == "table" then
                out[k] = copy(v, seen)
            elseif kind == "string" or kind == "number" or kind == "boolean" then
                out[k] = v
            end
        end
    end
    return out
end

local function character()
    local E = getEconomy()
    if type(E) == "table" and type(E.CharacterKey) == "function" then
        local ok, key = pcall(E.CharacterKey)
        if ok and type(key) == "string" and key ~= "" then return key end
    end
    local dbMod = getDB()
    if type(dbMod) == "table" and type(dbMod.CharacterKey) == "function" then
        local ok, key = pcall(dbMod.CharacterKey)
        if ok and type(key) == "string" and key ~= "" then return key end
    end
    if type(_G.UnitGUID) == "function" then
        local ok, guid = pcall(_G.UnitGUID, "player")
        if ok and type(guid) == "string" and guid ~= "" then return guid end
    end
    local name = type(_G.UnitName) == "function" and _G.UnitName("player") or nil
    local realm = type(_G.GetRealmName) == "function" and _G.GetRealmName() or nil
    if name or realm then
        return "offline:" .. tostring(name or "?") .. "-" .. tostring(realm or "?")
    end
    return "offline:player"
end

local function validSavedStore(store)
    return type(store) == "table"
        and store.version == MODEL
        and type(store.routes) == "table"
        and type(store.active) == "table"
        and type(store.nextID) == "number"
        and store.nextID >= 0
        and store.nextID == math.floor(store.nextID)
end

local function resolveDBRoot(dbMod)
    if type(dbMod) == "table" then
        if type(dbMod.Get) == "function" then
            local ok, root = pcall(dbMod.Get)
            if ok and type(root) == "table" then return root end
        end
        local mt = getmetatable(dbMod)
        if type(mt) == "table" and type(mt.__call) == "function" then
            local ok, root = pcall(dbMod)
            if ok and type(root) == "table" then return root end
        end
    elseif type(dbMod) == "function" then
        local ok, root = pcall(dbMod)
        if ok and type(root) == "table" then return root end
    end
    return nil
end

local function saved()
    local dbMod = getDB()
    if not dbMod then return nil, "historyUnreadable" end
    local key = character()
    if type(dbMod) == "table" and type(dbMod.Get) == "function" and type(dbMod.CharacterStore) == "function" then
        local okRoot, root = pcall(dbMod.Get)
        if not okRoot or type(root) ~= "table" or (root.routePlans ~= nil and type(root.routePlans) ~= "table") then
            return nil, "historyUnreadable"
        end
        local existing = type(root.routePlans) == "table" and root.routePlans[key] or nil
        if existing ~= nil then
            if not validSavedStore(existing) then return nil, "historyUnreadable" end
            return existing
        end
        local okStore, store = pcall(dbMod.CharacterStore, "routePlans", key)
        if not okStore or type(store) ~= "table" then return nil, "historyUnreadable" end
        store.version = MODEL
        store.routes = {}
        store.active = {}
        store.nextID = 0
        return store
    end
    local root = resolveDBRoot(dbMod)
    local prof = type(root) == "table" and root.prof or nil
    if type(prof) ~= "table" then return nil, "historyUnreadable" end
    if prof.routePlans ~= nil and (type(prof.routePlans) ~= "table" or prof.routePlans.version ~= MODEL) then
        return nil, "historyUnreadable"
    end
    prof.routePlans = prof.routePlans or { version = MODEL, characters = {} }
    local all = prof.routePlans.characters
    if type(all) ~= "table" then return nil, "historyUnreadable" end
    if all[key] ~= nil and not validSavedStore(all[key]) then
        return nil, "historyUnreadable"
    end
    all[key] = all[key] or { version = MODEL, routes = {}, active = {}, nextID = 0 }
    return all[key]
end

local function setting(key, fallback, slug)
    local st = getSettings()
    if type(st) == "table" and type(st.SettingRaw) == "function" then
        local ok, value = pcall(st.SettingRaw, key, slug)
        if ok then
            if value ~= nil then return value end
            return fallback
        end
    end
    local root = resolveDBRoot(st) or resolveDBRoot(getDB())
    local prof = type(root) == "table" and root.prof or nil
    if type(prof) == "table" then
        if type(slug) == "string" and slug ~= "" and type(prof.professionSettings) == "table"
            and type(prof.professionSettings[slug]) == "table" then
            local value = prof.professionSettings[slug][key]
            if value ~= nil then return value end
        end
        if prof[key] ~= nil then return prof[key] end
    end
    return fallback
end

local function computationClock()
    if type(_G.debugprofilestop) == "function" then
        local ok, v = pcall(_G.debugprofilestop)
        if ok and type(v) == "number" then return v end
    end
    if type(os) == "table" and type(os.clock) == "function" then
        return os.clock() * 1000
    end
    return 0
end

local function runSlice(job)
    local S = getSolver()
    if not (S and type(S.Run) == "function") then return true end
    local cfg = getSolverCfg()
    local b = type(cfg) == "table" and type(cfg.COROUTINE_BUDGET) == "table" and cfg.COROUTINE_BUDGET or nil
    local presets = b and type(b.speedPresets) == "table" and b.speedPresets or nil
    local fastMs = (presets and type(presets.fast) == "table" and type(presets.fast.budgetMs) == "number" and presets.fast.budgetMs) or 8
    local turboMs = (presets and type(presets.turbo) == "table" and type(presets.turbo.budgetMs) == "number" and presets.turbo.budgetMs) or 60
    local turboStride = (presets and type(presets.turbo) == "table" and type(presets.turbo.tickClockStride) == "number" and presets.turbo.tickClockStride) or 16
    local speed = setting("computationSpeed", "fast")
    local turbo = speed == "turbo"
    local budget = (speed == "fast" and fastMs) or (turbo and turboMs) or nil
    job.tickClockStride = turbo and turboStride or nil
    if not budget then
        local ok, done = pcall(S.Run, job, adaptiveSliceMs())
        if not ok then
            job.status = "error"
            job.finished = true
            return true
        end
        return done
    end
    local started = computationClock()
    local remaining = budget
    for _ = 1, 64 do
        local ok, done = pcall(S.Run, job, remaining, turbo)
        if not ok then
            job.status = "error"
            job.finished = true
            return true
        end
        if done or job.finished or job.cancelled or job.invalid then return true end
        local elapsed = computationClock() - started
        if elapsed < 0 or elapsed >= budget then break end
        remaining = budget - elapsed
    end
    if turbo and type(S.RefreshStatus) == "function" then pcall(S.RefreshStatus, job) end
    return false
end

function RA.OptionsFor(slug, current)
    local E = getEconomy()
    local baseOptFn = getBaseOptions()
    local opts
    if type(baseOptFn) == "function" then
        local ok, v = pcall(baseOptFn, slug, current, true)
        if ok and type(v) == "table" then opts = v end
    end
    opts = opts or {}
    opts.fromCurrent = setting("autoFromCurrent", true, slug)
    opts.cpuLimitMs = cfgCpuLimitMs()
    opts.autoCraftTools = setting("autoCraftTools", true, slug)
    opts.residualMass = setting("autoResidualMass", false, slug)
    opts.skillBudgetAll = true
    local rawBudget = setting("autoSkillBudget", "balanced", slug)
    if E and type(E.GreenBudgetMode) == "function" then
        local ok, v = pcall(E.GreenBudgetMode, rawBudget)
        opts.greenBudget = (ok and v ~= nil) and v or rawBudget
    else
        opts.greenBudget = rawBudget
    end
    opts.recoveryEnabled = setting("recoveryEnabled", false, slug)
    opts.recoveryFeePercent = setting("recoveryFeePercent", cfgDefaultFee(), slug)
    opts.allowLimitedFormulas = setting("autoBuyLimitedFormulas", false, slug)
    opts.allowBindOnPickupFormulas = setting("autoAllowBindOnPickupFormulas", false, slug)
    opts.allowCurrencyFormulas = setting("autoAllowCurrencyFormulas", false, slug)
    opts.considerAuctionSupply = setting("autoConsiderAuctionSupply", false, slug)
    opts.useBagMaterials = setting("autoUseBagMaterials", false, slug)
    if isFixedOnly(slug) then
        opts.scheme = "fixed"
        opts.autoCraftTools = false
    end
    local pol
    if E and type(E.GetPolicies) == "function" then
        local ok, v = pcall(E.GetPolicies, slug)
        if ok and type(v) == "table" then pol = v end
    end
    opts.exclusions = copy(pol or {})
    if E and type(E.GetRoutePartner) == "function" then
        local ok, p = pcall(E.GetRoutePartner, slug)
        if ok then opts.secondaryProfession = p end
    end
    opts.executionInventory = nil
    return opts
end

local function options(slug, supplied)
    local E = getEconomy()
    local cap = cfgCap()
    local defTarget = cfgDefaultTarget()
    local opts = copy(supplied or RA.OptionsFor(slug), nil, true)
    if supplied and supplied.snapshot then opts.snapshot = supplied.snapshot end
    opts.scheme = opts.scheme or "cheapest"
    if opts.scheme == "stable" then opts.scheme = "cheapest" end
    if opts.useBagMaterials == nil then opts.useBagMaterials = setting("autoUseBagMaterials", false, slug) end
    opts.useBagMaterials = opts.useBagMaterials == true
        and not isFixedOnly(slug)
        and opts.scheme ~= "fixed"
        and opts.scheme ~= "fishing"
        and slug ~= "fishing"
    opts.profession = slug
    opts.learnedOnly, opts.noFormula, opts.allowUnknownLearning, opts.skipUnpricedFormulas = nil, nil, nil, nil
    local consider = false
    if E and type(E.ConsiderAuctionSupply) == "function" then
        local ok, v = pcall(E.ConsiderAuctionSupply, opts)
        if ok and v then consider = true end
    end
    opts.considerAuctionSupply = consider
    opts.start = math.max(1, math.min(cap, math.floor(tonumber(opts.start) or 1)))
    opts.target = math.max(1, math.min(cap, math.floor(tonumber(opts.target) or defTarget)))
    if opts.residualMass == nil then opts.residualMass = setting("autoResidualMass", false, slug) end
    if opts.skillBudgetAll == nil then opts.skillBudgetAll = true end
    local rawBudget = opts.greenBudget or setting("autoSkillBudget", "balanced", slug)
    if E and type(E.GreenBudgetMode) == "function" then
        local ok, v = pcall(E.GreenBudgetMode, rawBudget)
        opts.greenBudget = (ok and v ~= nil) and v or rawBudget
    else
        opts.greenBudget = rawBudget
    end
    if opts.recoveryEnabled == nil then opts.recoveryEnabled = setting("recoveryEnabled", false, slug) end
    if opts.recoveryFeePercent == nil then opts.recoveryFeePercent = setting("recoveryFeePercent", cfgDefaultFee(), slug) end
    if opts.autoCraftTools == nil then opts.autoCraftTools = setting("autoCraftTools", true, slug) end
    if opts.allowLimitedFormulas == nil then opts.allowLimitedFormulas = setting("autoBuyLimitedFormulas", false, slug) end
    if opts.allowBindOnPickupFormulas == nil then opts.allowBindOnPickupFormulas = setting("autoAllowBindOnPickupFormulas", false, slug) end
    if opts.allowCurrencyFormulas == nil then opts.allowCurrencyFormulas = setting("autoAllowCurrencyFormulas", false, slug) end
    if not opts.exclusions then
        local pol
        if E and type(E.GetPolicies) == "function" then
            local ok, v = pcall(E.GetPolicies, slug)
            if ok and type(v) == "table" then pol = v end
        end
        opts.exclusions = copy(pol or {})
    end
    local profs = opts.snapshot and opts.snapshot.professions or opts.professions
    local context
    if E and type(E.RouteContext) == "function" then
        local ok, v = pcall(E.RouteContext, slug, opts, profs)
        if ok and type(v) == "table" then context = v end
    end
    opts.targetUnlearned = context and context.unlearned or false
    opts.partnerRequired = context and context.requiresPartner and not context.partnerValid or false
    if context and context.requiresPartner then opts.secondaryProfession = context.partner end
    if opts.scheme == "fishing" then
        opts.allowSecondaryLeveling = false
        opts.secondaryProfession = nil
    end
    return opts
end

local function signature(slug, opts)
    local E = getEconomy()
    local start = opts.fromCurrent == false and ("fixed:" .. opts.start) or "current"
    if opts.snapshot then start = tostring(opts.start) end
    local policy = ""
    if E and type(E.PolicyFingerprint) == "function" then
        local ok, v = pcall(E.PolicyFingerprint, opts.exclusions)
        if ok and v ~= nil then policy = v end
    end
    local specSig = ""
    if type(RA.SpecSig) == "function" then
        local ok, v = pcall(RA.SpecSig, slug)
        if ok and v ~= nil then specSig = v end
    end
    local learnObs = ""
    if E and type(E.LearningObservationFingerprint) == "function" then
        local ok, v = pcall(E.LearningObservationFingerprint)
        if ok and v ~= nil then learnObs = v end
    end
    local sig = table.concat({
        "profession:" .. tostring(slug),
        opts.scheme,
        tostring(opts.target),
        start,
        tostring(opts.onlyAH),
        tostring(opts.allowBindOnPickupFormulas),
        tostring(opts.allowCurrencyFormulas),
        tostring(opts.considerAuctionSupply),
        tostring(opts.allowSecondaryLeveling),
        tostring(opts.secondaryProfession),
        tostring(opts.autoCraftTools),
        tostring(opts.allowLimitedFormulas),
        tostring(opts.useBagMaterials == true),
        "formula-channels:2",
        "profit-priority:20",
        "recipe-batches:12:risk:1",
        "auction-depth:1",
        tostring(opts.residualMass),
        tostring(opts.recoveryEnabled),
        tostring(opts.recoveryFeePercent),
        tostring(opts.targetUnlearned),
        specSig,
        policy,
        learningPolicy(),
        learnObs,
    }, "|")
    if opts.scheme ~= "fixed" and opts.scheme ~= "fishing" then
        local gb = tostring(opts.greenBudget)
        if E and type(E.GreenBudgetMode) == "function" then
            local ok, v = pcall(E.GreenBudgetMode, opts.greenBudget)
            if ok and v ~= nil then gb = v end
        end
        sig = sig .. (opts.skillBudgetAll and "|skill-budget:2:" or "|green-budget:1:") .. gb
    end
    return sig
end

local function identity(slug, opts)
    local scope = character() .. "|" .. slug
    if opts.snapshot then scope = scope .. "|" .. tostring(opts.snapshot) end
    return scope .. "|" .. signature(slug, opts), scope
end

local function gate(slug, opts, code)
    return {
        slug = slug,
        planVersion = 2,
        executionVersion = 1,
        scheme = opts.scheme,
        start = opts.start,
        target = opts.target,
        status = code == "secondaryRequired" and "selection_required" or "recalculate_required",
        feasible = false,
        steps = {},
        executionSteps = {},
        actions = {},
        mats = {},
        formulas = {},
        gaps = {},
        total = 0,
        crafts = 0,
        diagnostics = { { code = code } },
        completeCost = false,
    }
end

local function scopeConflict(plan, slug, opts)
    if opts.allowSecondaryLeveling or slug == "__purchase" then return false end
    for _, step in ipairs(plan.executionSteps or plan.steps or {}) do
        if step.profession and step.profession ~= slug then return true end
    end
    return false
end

local function refreshFreshness(result, slug, opts)
    local E = getEconomy()
    local S = getSolver()
    if scopeConflict(result, slug, opts) then return gate(slug, opts, "secondaryDisabled") end
    if result.learningPolicyFingerprint and result.learningPolicyFingerprint ~= learningPolicy() then
        return learningStale(result)
    end
    local diagnosticPolicyChanged = result.planVersion == 2 and result.scheme ~= "fishing"
        and result.targetReached ~= true and S and result.failureDiagnosticVersion ~= S.FailureDiagnosticVersion
    local settingsChanged = result.cacheSignature and result.cacheSignature ~= signature(slug, opts) or false
    local bagChanged, bagUnknown = false, false
    if E and type(E.BagInventoryChanged) == "function" then
        local ok, c, u = pcall(E.BagInventoryChanged, result)
        if ok then bagChanged, bagUnknown = c, u end
    end
    result.bagInventoryChanged = bagChanged or nil
    result.bagInventoryUnknown = bagUnknown or result.bagInventoryUnknown or nil
    local procurementPolicyChanged = result.planVersion == 2 and
        (result.scheme == "fishing" and result.fishingRouteRevision ~= 2
            or result.scheme ~= "fishing" and S and result.procurementPolicyVersion ~= S.ProcurementPolicyVersion)
    local marketChanged = false
    if E and type(E.AuctionDepthChanged) == "function" then
        local ok, v = pcall(E.AuctionDepthChanged, result)
        if ok and v then marketChanged = true end
    end
    if not marketChanged and E and type(E.VendorPricesChanged) == "function" then
        local ok, v = pcall(E.VendorPricesChanged, result)
        if ok and v then marketChanged = true end
    end
    if result.auctionPriceInputs and RA.AHPriceOf then
        for id, previous in pairs(result.auctionPriceInputs) do
            local price = RA.AHPriceOf(id)
            local current = type(price) == "number" and price > 0 and price or false
            if current ~= previous then marketChanged = true; break end
        end
    end
    local supplyChanged = (result.planVersion == 2 and result.scheme ~= "fishing" and result.auctionSupplyRevision ~= 3)
    if not supplyChanged and E and type(E.AuctionSupplyChanged) == "function" then
        local ok, v = pcall(E.AuctionSupplyChanged, result)
        if ok and v then supplyChanged = true end
    end
    supplyChanged = supplyChanged or false
    local reason = result.staleReason
    local explicit = result.stale and (reason == "recipes" or reason == "client-inputs" or reason == "specialization" or reason == "learning-data"
        or (reason == "prices" and not result.auctionPriceInputs))
    result.settingsChanged = settingsChanged or nil
    result.diagnosticPolicyChanged = diagnosticPolicyChanged or nil
    result.stale = (diagnosticPolicyChanged or procurementPolicyChanged or settingsChanged or marketChanged or supplyChanged or bagChanged or result.bagInventoryUnknown or explicit) and true or nil
    result.staleReason = diagnosticPolicyChanged and "diagnostic-policy"
        or procurementPolicyChanged and "procurement-policy"
        or settingsChanged and "settings"
        or supplyChanged and "supply"
        or marketChanged and "prices"
        or result.bagInventoryUnknown and "inventory-unknown"
        or bagChanged and "inventory"
        or (explicit and reason) or nil
    return result
end

local function ensureBridgeHook()
    local bridge = getAuctionBridge()
    if not bridge or bridge == hookedBridge or type(bridge.OnChanged) ~= "function" then return end
    hookedBridge = bridge
    bridge.OnChanged(function(_, reason)
        if reason == "supply" then
            local invFn = getBaseInvalidate()
            if type(invFn) == "function" then pcall(invFn) end
            for _, job in pairs(jobs) do
                if job.published and not job.opts.snapshot then
                    refreshFreshness(job.published, job.slug, job.opts)
                end
            end
        elseif reason == "replicate-mode" then
            if type(bridge.ReplicateScanReady) == "function" and not bridge.ReplicateScanReady() then
                RA.Cancel()
                RA.Invalidate("auction-mode")
            end
        elseif reason == "prices" then
            RA.Invalidate(reason)
        end
    end)
end

local function replicatePrerequisite(slug, opts)
    ensureBridgeHook()
    local bridge = getAuctionBridge()
    if not (bridge and type(bridge.ReplicateScanReady) == "function") then
        return gate(slug, opts, "replicateModeUnknown")
    end
    local ready, reason = bridge.ReplicateScanReady()
    if ready ~= true then
        return gate(slug, opts, reason or "replicateScanRequired")
    end
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

local function sanitizePositivePrices(tbl)
    if type(tbl) ~= "table" then return nil end
    local out = {}
    for k, v in pairs(tbl) do
        if type(v) == "number" and v > 0 and v < math.huge then
            out[k] = v
        end
    end
    return out
end

local function validOfferNumber(v)
    return type(v) == "number" and v >= 0 and v < math.huge
end

local function validOfferInteger(v)
    return type(v) == "number" and v >= 1 and v < math.huge and v == math.floor(v)
end

local function validSnapshotOffer(o)
    if type(o) ~= "table" then return false end
    if o.price ~= nil and not validOfferNumber(o.price) then return false end
    if o.priceCopper ~= nil and not validOfferNumber(o.priceCopper) then return false end
    if o.unitCopper ~= nil and not validOfferNumber(o.unitCopper) then return false end
    if o.quantity ~= nil and not validOfferInteger(o.quantity) then return false end
    if o.bundleSize ~= nil and not validOfferInteger(o.bundleSize) then return false end
    if o.stock ~= nil and (type(o.stock) ~= "number" or not (o.stock > -math.huge and o.stock < math.huge)) then
        return false
    end
    if o.maxStock ~= nil and (type(o.maxStock) ~= "number" or not (o.maxStock > -math.huge and o.maxStock < math.huge)) then
        return false
    end
    if (o.currencies ~= nil and type(o.currencies) ~= "table") or (o.costItems ~= nil and type(o.costItems) ~= "table") then
        return false
    end
    if o.price == nil and o.priceCopper == nil and o.unitCopper == nil then
        local hasExt = (type(o.currencies) == "table" and #o.currencies > 0)
            or (type(o.costItems) == "table" and #o.costItems > 0)
            or o.hasExtendedCost == true
            or (type(o.currencyID) == "number" and o.currencyID > 0 and o.currencyID < math.huge)
        if not hasExt then return false end
    end
    return true
end

local function sanitizeOffersMap(tbl)
    if type(tbl) ~= "table" then return nil end
    local out = {}
    for id, list in pairs(tbl) do
        if type(list) == "table" then
            local clean = {}
            for _, o in ipairs(list) do
                if validSnapshotOffer(o) then
                    clean[#clean + 1] = o
                end
            end
            out[id] = clean
        end
    end
    return out
end

local function sanitizeSnapshot(snap)
    if type(snap) ~= "table" then return snap end
    local out = {}
    for k, v in pairs(snap) do
        out[k] = v
    end
    if type(snap.prices) == "table" then
        out.prices = sanitizePositivePrices(snap.prices)
    end
    if type(snap.sellPrices) == "table" then
        local sp = {}
        for k, v in pairs(snap.sellPrices) do
            if type(v) == "number" and v >= 0 and v < math.huge then
                sp[k] = v
            end
        end
        out.sellPrices = sp
    end
    if type(snap.auctionDepth) == "table" then
        local depth = {}
        for id, book in pairs(snap.auctionDepth) do
            if validDepthBook(book) then
                depth[id] = book
            elseif type(out.prices) == "table" then
                out.prices[id] = nil
            end
        end
        out.auctionDepth = depth
    end
    if snap.offers ~= nil then
        out.offers = sanitizeOffersMap(snap.offers)
    end
    if snap.formulaOffers ~= nil then
        out.formulaOffers = sanitizeOffersMap(snap.formulaOffers)
    end
    if snap.stamp ~= nil and (type(snap.stamp) ~= "number" or not (snap.stamp >= 0 and snap.stamp < math.huge)) then
        out.stamp = nil
    end
    return out
end

local function sanitizeSolverOpts(opts)
    if type(opts) ~= "table" then return opts end
    if opts.snapshot == nil and opts.ahPrices == nil and opts.prices == nil then
        return opts
    end
    local out = {}
    for k, v in pairs(opts) do
        out[k] = v
    end
    if type(opts.snapshot) == "table" then
        out.snapshot = sanitizeSnapshot(opts.snapshot)
    end
    if type(opts.ahPrices) == "table" then
        out.ahPrices = sanitizePositivePrices(opts.ahPrices)
    end
    if type(opts.prices) == "table" then
        out.prices = sanitizePositivePrices(opts.prices)
    end
    return out
end

function RA.FixedPlan(slug, supplied)
    ensureBridgeHook()
    local opts = supplied or RA.OptionsFor(slug)
    if type(opts) == "table" and not opts.scheme and isFixedOnly(slug) then
        opts = copy(opts, nil, true)
        opts.scheme = "fixed"
    end
    local blocked = replicatePrerequisite(slug, opts)
    if blocked then return blocked end
    local fpFn = getBaseFixedPlan()
    if type(fpFn) == "function" then
        return fpFn(slug, sanitizeSolverOpts(opts))
    end
    return nil
end

local skeletonStepFields = {
    "profession", "kind", "reason", "checkpoint", "segmentID",
    "tool", "toolItem", "toolSpell", "toolBop", "fromProgress", "toProgress", "displayFrom", "displayTo",
    "goalID", "questID", "abilityID", "sourceItem", "targetItem",
}
local skeletonOptionFields = {
    "fromCurrent", "onlyAH", "allowSecondaryLeveling", "secondaryProfession",
    "autoCraftTools", "allowLimitedFormulas", "allowBindOnPickupFormulas", "allowCurrencyFormulas",
    "considerAuctionSupply", "greenBudget", "skillBudgetAll", "residualMass", "recoveryEnabled",
    "recoveryFeePercent", "engineeringSpecialization", "useBagMaterials",
}

local function planSkeleton(result, opts, status)
    local rows = result.executionSteps or result.steps
    if type(rows) ~= "table" or #rows == 0 then return end
    local steps = {}
    for _, st in ipairs(rows) do
        local e = { st[1], st[2], st[3], st[4] }
        for _, key in ipairs(skeletonStepFields) do e[key] = st[key] end
        e.allocations = {}
        local edges = {}
        for _, allocation in ipairs(st.allocations or {}) do
            local key = allocation.consumerID .. ":" .. allocation.itemID
            local edge = edges[key]
            if not edge then
                edge = { consumerID = allocation.consumerID, itemID = allocation.itemID, count = 0 }
                edges[key] = edge
                e.allocations[#e.allocations + 1] = edge
            end
            edge.count = edge.count + allocation.count
        end
        steps[#steps + 1] = e
    end
    local settings = {}
    for _, key in ipairs(skeletonOptionFields) do settings[key] = opts[key] end
    settings.skillBudgetAll = result.skillBudgetAll == true
    settings.greenBudget = result.greenBudget or settings.greenBudget or "optimistic"
    settings.useBagMaterials = result.useBagMaterials == true
    settings.exclusions = copy(opts.exclusions or {})
    if result.useBagMaterials then
        settings.bagInventory = copy(result.bagInventory or {})
        settings.bagInventoryStamp = result.bagInventoryStamp
        settings.bagInventoryFingerprint = result.bagInventoryFingerprint
        settings.bagInventoryVersion = result.bagInventoryVersion
    end
    settings.engineeringSpecialization = result.specializationPolicy and result.specializationPolicy.choice or settings.engineeringSpecialization
    return {
        v = 1,
        slug = result.slug,
        pv = result.planVersion,
        sig = result.cacheSignature,
        auctionDepthRevision = result.auctionDepthRevision,
        planID = result.planID,
        start = result.start,
        target = result.target,
        scheme = result.scheme,
        stamp = now(),
        status = status or result.status,
        steps = steps,
        options = settings,
    }
end

local function remember(job, result, status)
    if job.opts.snapshot or (job.opts.routeSkeleton and not (job.opts.regroupSaved and result.targetReached)) or (result.status == "searching" and not status) then
        return
    end
    local skeleton = planSkeleton(result, job.opts, status)
    if not skeleton then return end
    local db = saved()
    if not db then return end
    db.routes[job.signature] = { slug = job.slug, skeleton = skeleton, model = MODEL, batchVersion = 4 }
    db.active[job.slug] = job.signature
    for key, row in pairs(db.routes) do
        if key ~= job.signature and type(row) == "table" and row.slug == job.slug then
            db.routes[key] = nil
        end
    end
end

local searchFields = {
    "status", "expanded", "improvements", "initialTotal", "bestTotal", "savings", "budgetLimited",
    "searchComplete", "searchTermination", "searchCpuMs", "searchCpuLimitMs", "inputModelOptimal",
    "costSearchPerformed", "costSearchStatus",
    "catalogueCoverageComplete", "quoteComplete", "restrictedReason", "searchModel", "frontierStates", "memoStates",
    "searchFrontierLimit", "initialNetTotal", "bestNetTotal", "netSavings", "recoveryOptimized",
}

local function updateExecution(job, result)
    local xp = getExecution()
    if job.opts.snapshot or not xp then return end
    if job.finished and job.deferBagPreparation and result.feasible and not result.bagInventoryUnknown then
        job.deferBagPreparation = nil
        if type(xp.PrepareRecalculate) == "function" then
            local okPrep, _, source, reason = pcall(xp.PrepareRecalculate, job.slug)
            if not okPrep or reason then result.bagInventoryUnknown = true; result.stale = true; return end
            if source then
                job.opts.executionSourcePlanID = source
                result.executionOptions.executionSourcePlanID = source
            end
        end
    end
    if job.finished and not job.opts.routeSkeleton and type(xp.PlanRecalculated) == "function" then
        pcall(xp.PlanRecalculated, job.slug, result)
    end
    local frozen
    if type(xp.GetPlan) == "function" then
        local okP, p = pcall(xp.GetPlan, job.slug)
        if okP then frozen = p end
    end
    if not frozen then return end
    if frozen.planID == result.planID or frozen.originPlanID == result.planID then
        local state = { running = not job.finished and not job.cancelled }
        for _, key in ipairs(searchFields) do state[key] = result[key] end
        frozen.searchState = state
    elseif type(xp.GetRun) == "function" then
        local okR, r = pcall(xp.GetRun, job.slug)
        if okR and r then r.newPlanAvailable = true; r.candidateRevision = result.revision end
    end
end

local function publish(job, result)
    if not result or job.invalid then return end
    local S = getSolver()
    if result.bagInventoryUnknown and not result.feasible and job.previousBagPlan then
        result = job.previousBagPlan
        result.bagInventoryUnknown = true
        result.stale = true
        result.staleReason = "inventory-unknown"
        local xp = getExecution()
        local frozen
        if xp and type(xp.GetPlan) == "function" then
            local okP, p = pcall(xp.GetPlan, job.slug)
            if okP then frozen = p end
        end
        if frozen then
            frozen.bagInventoryUnknown = true
            frozen.stale = true
            frozen.staleReason = "inventory-unknown"
        end
        job.result = result
        job.previousBagPlan = nil
        job.deferBagPreparation = nil
        job.published = result
        results[job.key] = result
        active[job.scope] = job.key
        for _, fn in ipairs(listeners) do pcall(fn, job.slug, result) end
        return
    end
    local started = type(_G.debugprofilestop) == "function" and _G.debugprofilestop() or nil
    revision = revision + 1
    result.slug = job.slug
    result.revision = revision
    result.planID = job.planID
    result.routeModel = MODEL
    result.learningPolicyFingerprint = learningPolicy()
    local executionOptions = {}
    for key, value in pairs(job.opts) do
        if key ~= "snapshot" and key ~= "routeSkeleton" and key ~= "regroupSaved" and key ~= "deferBagPreparation" then
            executionOptions[key] = value
        end
    end
    result.executionOptions = copy(executionOptions)
    if result.useBagMaterials then
        result.executionOptions.bagInventory = copy(result.bagInventory or {})
        result.executionOptions.bagInventoryStamp = result.bagInventoryStamp
        result.executionOptions.bagInventoryVersion = result.bagInventoryVersion
    end
    result.stale = job.stale or nil
    result.staleReason = job.staleReason
    if result.bagInventoryUnknown then
        result.stale = true
        result.staleReason = "inventory-unknown"
    end
    if RA.StampSpecializations then RA.StampSpecializations(result, job.slug, job.opts, job.snap) end
    result.quoteSignature = RA.QuoteSig and RA.QuoteSig(job.slug) or ""
    result.cacheSignature = job.signature
    job.published = result
    results[job.key] = result
    active[job.scope] = job.key
    job.publishedProgressVersion = job.progressVersion
    if job.opts.routeSkeleton then
        result.cached = true
        result.fromSkeleton = true
        result.optimal = false
        result.inputModelOptimal = false
        result.searchComplete = false
        result.costSearchPerformed = false
        refreshFreshness(result, job.slug, job.requestOptions or job.opts)
    end
    if result.useBagMaterials and not job.opts.snapshot then
        refreshFreshness(result, job.slug, job.requestOptions or job.opts)
    end
    updateExecution(job, result)
    remember(job, result)
    for _, fn in ipairs(listeners) do pcall(fn, job.slug, result) end
    if started and S and S.ChargeExternalWork and job.co and type(_G.debugprofilestop) == "function" then
        S.ChargeExternalWork(job, math.max(0, _G.debugprofilestop() - started))
    end
end

local function release(job)
    job.co = nil
    job.snap = nil
    job.best = nil
    job.partial = nil
    job.preview = nil
    job.rebatchFinal = nil
    job.tick = nil
    job.resultState = nil
    job.resultCache = nil
    job.auctionSupply = nil
    job.candidateIndex = nil
    job.pump = nil
    job.invalid = true
end

local function discardScope(scope)
    if legacyRun and legacyRun.job and legacyRun.job.scope == scope then legacyRun = nil end
    for key, job in pairs(jobs) do
        if job.scope == scope then
            release(job)
            jobs[key] = nil
            results[key] = nil
        end
    end
    local key = active[scope]
    if key then results[key] = nil end
    active[scope] = nil
end

local function pause(job, reason)
    if not job.cancelled then
        job.resumeStatus = job.status
        job.resumeTermination = job.searchTermination
    end
    job.cancelled = true
    job.status = "stopped"
    job.searchTermination = reason
end

local function pump(job)
    local S = getSolver()
    if job.invalid or job.cancelled or job.finished then return true end
    if replicatePrerequisite(job.slug, job.opts) then
        pause(job, "replicate_scan_required")
        if job.published then
            job.published.status = "stopped"
            job.published.inFlight = false
            job.published.searchTermination = "replicate_scan_required"
        end
        return true
    end
    local done = runSlice(job)
    if job.result and (job.result ~= job.published or done) then
        publish(job, job.result)
    elseif job.published and job.progressVersion ~= job.publishedProgressVersion then
        if S and S.Progress then
            local ok, state = pcall(S.Progress, job, job.published)
            if ok then
                for key, value in pairs(state or {}) do job.published[key] = value end
            end
        end
        job.publishedProgressVersion = job.progressVersion
        updateExecution(job, job.published)
        for _, fn in ipairs(progressListeners) do
            local progressState
            if S and S.Progress then
                local ok, st = pcall(S.Progress, job, job.published)
                if ok then progressState = st end
            end
            pcall(fn, job.slug, job.published, progressState)
        end
    end
    if job.hooks and job.hooks.onProgress then
        pcall(job.hooks.onProgress, job, run.State(job), done)
    end
    if done or job.finished then
        if job.hooks and job.hooks.onDone then pcall(job.hooks.onDone, job) end
        if jobs[job.key] == job then jobs[job.key] = nil end
        release(job)
        return true
    end
    return false
end

local function schedule(job)
    if job.scheduled then return end
    job.scheduled = true
    job.scheduleVersion = (job.scheduleVersion or 0) + 1
    local generation = job.scheduleVersion
    local weakRef = setmetatable({ job = job }, { __mode = "v" })
    local function step()
        local j = weakRef.job
        if not j or j.scheduleVersion ~= generation then return true end
        local done = pump(j)
        if done then j.scheduled = false end
        return done
    end
    job.pump = step
    local idle = getIdle()
    if idle and type(idle.Add) == "function" then
        idle.Add(step)
    elseif type(_G.C_Timer) == "table" and type(_G.C_Timer.After) == "function" then
        local function later() if not step() then _G.C_Timer.After(0, later) end end
        _G.C_Timer.After(0, later)
    end
end

local function start(slug, opts, sigOpts)
    local S = getSolver()
    local blocked = replicatePrerequisite(slug, opts)
    if blocked then return blocked end
    lastRunSlug = slug
    local key, scope = identity(slug, sigOpts or opts)
    serial = serial + 1
    local skel = opts.routeSkeleton
    local db = not opts.snapshot and saved()
    if db and (not skel or opts.regroupSaved) then db.nextID = (db.nextID or 0) + 1 end
    local id = skel and not opts.regroupSaved and skel.planID or character() .. ":route:" .. tostring(db and db.nextID or serial)
    if opts.scheme == "fishing" then
        local computeFn = getBaseCompute()
        local runOpts = sanitizeSolverOpts(opts)
        if type(computeFn) ~= "function" then
            return gate(slug, opts, "solverUnavailable")
        end
        local okComp, result = pcall(computeFn, slug, runOpts)
        if not okComp or type(result) ~= "table" then
            return gate(slug, opts, "solverUnavailable")
        end
        result.status = result.status or "complete"
        local xp = getExecution()
        if xp and type(xp.NormalizePlan) == "function" then
            local okNorm, norm = pcall(xp.NormalizePlan, slug, result)
            if okNorm and type(norm) == "table" then result = norm end
        end
        local job = {
            key = key,
            scope = scope,
            slug = slug,
            signature = skel and skel.sig or signature(slug, sigOpts or opts),
            opts = runOpts,
            requestOptions = sigOpts,
            planID = id,
            finished = true,
        }
        discardScope(scope)
        publish(job, result)
        return result
    end
    if not (S and type(S.NewJob) == "function" and type(S.Result) == "function") then
        return gate(slug, opts, "solverUnavailable")
    end
    local runOpts = sanitizeSolverOpts(opts)
    local okJob, job = pcall(S.NewJob, slug, runOpts)
    if not okJob or type(job) ~= "table" then
        return gate(slug, opts, "solverUnavailable")
    end
    job.deferBagPreparation = opts.deferBagPreparation
    if opts.useBagMaterials then
        local previous = active[scope] and results[active[scope]]
        local xp = getExecution()
        if not opts.snapshot and xp and type(xp.GetPlan) == "function" then
            local okP, plan = pcall(xp.GetPlan, slug)
            if okP and plan then previous = plan end
        end
        if previous and #(previous.steps or {}) > 0 then job.previousBagPlan = copy(previous) end
    end
    job.key, job.scope, job.slug, job.planID = key, scope, slug, id
    job.signature = skel and skel.sig or signature(slug, sigOpts or opts)
    job.requestOptions = sigOpts
    local okRes, result = pcall(S.Result, job, nil, "searching")
    if not okRes or type(result) ~= "table" then
        return gate(slug, opts, "solverUnavailable")
    end
    result.slug = slug
    result.planID = id
    result.cacheSignature = job.signature
    result.learningPolicyFingerprint = learningPolicy()
    discardScope(scope)
    jobs[key] = job
    active[scope] = key
    job.published = result
    results[key] = result
    schedule(job)
    return result
end

function RA.OnPlanChanged(fn)
    if type(fn) == "function" then listeners[#listeners + 1] = fn end
end

function RA.OnProgress(fn)
    if type(fn) == "function" then progressListeners[#progressListeners + 1] = fn end
end

function RA.Get(slug, supplied)
    ensureBridgeHook()
    if isFixedOnly(slug) then
        if RA.Cancel then RA.Cancel(slug) end
        return RA.FixedPlan(slug, supplied or RA.OptionsFor(slug))
    end
    local opts = options(slug, supplied)
    if opts.partnerRequired then return gate(slug, opts, "secondaryRequired") end
    local key, scope = identity(slug, opts)
    local xp = not opts.snapshot and getExecution()
    local frozen, reason
    if xp and type(xp.GetPlan) == "function" then
        local okP, f, r = pcall(xp.GetPlan, slug)
        if okP then frozen, reason = f, r else reason = "historyUnreadable" end
    end
    if reason == "historyUnreadable" then return gate(slug, opts, reason) end
    if frozen and frozen.slug and frozen.slug ~= slug then frozen = nil end
    if frozen then
        if frozen.learningPolicyFingerprint ~= learningPolicy() then return learningStale(frozen) end
        if RA.SpecializationPlanChanged and RA.SpecializationPlanChanged(frozen, slug, opts) then
            return gate(slug, opts, "specializationChanged")
        end
        return refreshFreshness(frozen, slug, opts)
    end
    local blocked = replicatePrerequisite(slug, opts)
    if blocked then return blocked end
    local result = results[key]
    if result and result.slug and result.slug ~= slug then result = nil end
    if result then
        if not opts.snapshot then refreshFreshness(result, slug, opts) end
        return result
    end
    local selected = active[scope] and results[active[scope]]
    if selected and selected.slug and selected.slug ~= slug then selected = nil end
    if not opts.snapshot and selected then
        if selected.learningPolicyFingerprint ~= learningPolicy() then return learningStale(selected) end
        return refreshFreshness(selected, slug, opts)
    end
    local db, cacheError
    if not opts.snapshot then db, cacheError = saved() end
    if cacheError then return gate(slug, opts, cacheError) end
    local function validRecord(rec)
        return type(rec) == "table" and rec.slug == slug
    end
    local record = db and db.routes[signature(slug, opts)]
    if not validRecord(record) then record = nil end
    if not record and db and db.active[slug] then
        local selectedRecord = db.routes[db.active[slug]]
        if validRecord(selectedRecord) then record = selectedRecord end
    end
    if record then
        local skel = record.skeleton
        if record.model ~= MODEL or type(skel) ~= "table" or skel.v ~= 1 or skel.pv ~= 2 or skel.slug ~= slug
            or type(skel.steps) ~= "table" or #skel.steps == 0 or type(skel.options) ~= "table" then
            return gate(slug, opts, "historyUnreadable")
        end
        if ((record.batchVersion or 0) < 4 and skel.status == "complete" or skel.status == "interrupted")
            and skel.scheme ~= "fixed" and skel.scheme ~= "fishing" then
            local seen, previous, repeated, reached = {}, nil, false, false
            for _, step in ipairs(skel.steps) do
                local k = not step.kind and not step.checkpoint and (step[3] or 0) > 0 and (step.profession or slug) .. ":" .. step[3]
                if k and seen[k] and k ~= previous then repeated = true end
                if (step.profession or slug) == slug and (step[2] or 0) >= skel.target then reached = true end
                if k then seen[k] = true end
                previous = k
            end
            if reached and (repeated or skel.status == "interrupted") then
                return RA.RebuildFromSkel(slug, skel, opts, true)
            end
        end
        return RA.RebuildFromSkel(slug, skel, opts)
    end
    return start(slug, opts)
end

function RA.RebuildFromSkel(slug, skel, supplied, regroup)
    local request = options(slug, supplied)
    if skel.pricingPolicyStale then return gate(slug, request, "pricingPolicyChanged") end
    if scopeConflict(skel, slug, request) then return gate(slug, request, "secondaryDisabled") end
    local restored = copy(skel.options)
    restored.skillBudgetAll = restored.skillBudgetAll == true
    restored.greenBudget = restored.greenBudget or "optimistic"
    restored.useBagMaterials = restored.useBagMaterials == true
    if restored.useBagMaterials and (restored.bagInventoryVersion ~= 1 or type(restored.bagInventory) ~= "table") then
        return gate(slug, request, "historyUnreadable")
    end
    if not request.allowSecondaryLeveling then restored.allowSecondaryLeveling = false end
    restored.start, restored.target, restored.scheme = skel.start, skel.target, skel.scheme
    local opts = options(slug, restored)
    opts.routeSkeleton = skel
    opts.regroupSaved = regroup or nil
    return start(slug, opts, request)
end

function RA.Compute(slug, supplied)
    ensureBridgeHook()
    if isFixedOnly(slug) then return RA.FixedPlan(slug, supplied or RA.OptionsFor(slug)) end
    local opts = options(slug, supplied)
    local blocked = replicatePrerequisite(slug, opts)
    if blocked then return blocked end
    if opts.partnerRequired then return gate(slug, opts, "secondaryRequired") end
    local runOpts = sanitizeSolverOpts(opts)
    if opts.scheme == "fishing" then
        local computeFn = getBaseCompute()
        if type(computeFn) ~= "function" then return gate(slug, opts, "solverUnavailable") end
        local okComp, result, job = pcall(computeFn, slug, runOpts)
        if not okComp or type(result) ~= "table" then return gate(slug, opts, "solverUnavailable") end
        return result, job
    end
    local S = getSolver()
    if not (S and type(S.Compute) == "function") then return gate(slug, opts, "solverUnavailable") end
    local okComp, result, job = pcall(S.Compute, slug, runOpts)
    if not okComp or type(result) ~= "table" then return gate(slug, opts, "solverUnavailable") end
    if result then result.learningPolicyFingerprint = learningPolicy() end
    if RA.StampSpecializations then RA.StampSpecializations(result, slug, runOpts, job and job.snap) end
    return result, job
end

function RA.Recalculate(slug, supplied)
    ensureBridgeHook()
    if isFixedOnly(slug) then
        if RA.Cancel then RA.Cancel(slug) end
        return RA.FixedPlan(slug, supplied or RA.OptionsFor(slug))
    end
    local E = getEconomy()
    local opts = options(slug, supplied)
    local sigOpts = copy(opts, nil, true)
    sigOpts.snapshot = opts.snapshot
    local blocked = replicatePrerequisite(slug, opts)
    if blocked then return blocked end
    if not opts.snapshot then
        local _, cacheError = saved()
        if cacheError then return gate(slug, opts, cacheError) end
    end
    if not opts.snapshot then RA.SavePlanPrev(slug) end
    local xp = not opts.snapshot and getExecution()
    opts.bagInventory = nil
    opts.bagInventoryStamp = nil
    opts.bagInventoryFingerprint = nil
    opts.bagInventoryVersion = nil
    if xp and xp.PrepareRecalculate and opts.useBagMaterials then
        opts.deferBagPreparation = true
        if opts.fromCurrent ~= false then
            local professions = {}
            if E and type(E.Professions) == "function" then
                local okP, v = pcall(E.Professions)
                if okP and type(v) == "table" then professions = v end
            end
            opts.start = (professions[slug] or {}).cur or opts.start
        end
    elseif xp and xp.PrepareRecalculate then
        local okPrep, inventory, source, errorCode = pcall(xp.PrepareRecalculate, slug)
        if not okPrep then return gate(slug, opts, "historyUnreadable") end
        if errorCode then return gate(slug, opts, errorCode) end
        if source then
            opts.executionInventory = inventory or {}
            opts.executionSourcePlanID = source
            local professions = {}
            if E and type(E.Professions) == "function" then
                local okP, v = pcall(E.Professions)
                if okP and type(v) == "table" then professions = v end
            end
            if opts.fromCurrent ~= false then opts.start = (professions[slug] or {}).cur or opts.start end
        end
    end
    local invFn = getBaseInvalidate()
    if type(invFn) == "function" then pcall(invFn) end
    if opts.partnerRequired then return gate(slug, opts, "secondaryRequired") end
    return start(slug, opts, sigOpts)
end

function RA.CacheReferencesChanged(owner)
    local xp = getExecution()
    if not (xp and type(xp.CanRevertCandidate) == "function") then return end
    local prefix = (owner or character()) .. "|"
    for scope in pairs(planPrevMem) do
        if scope:sub(1, #prefix) == prefix then
            local okC, canC = pcall(xp.CanRevertCandidate, scope:sub(#prefix + 1))
            if not okC or not canC then
                planPrevMem[scope] = nil
            end
        end
    end
end

function RA.SavePlanPrev(slug)
    local scope = character() .. "|" .. slug
    local xp = getExecution()
    if xp and type(xp.CanRevertCandidate) == "function" then
        local okC, canC = pcall(xp.CanRevertCandidate, slug)
        if not okC or not canC then
            planPrevMem[scope] = nil
            return
        end
    end
    local key = active[scope]
    local result = key and results[key]
    if type(result) ~= "table" or result.finalizing or type(result.steps) ~= "table" or #result.steps == 0 then return end
    local previous = copy(result)
    if previous.status == "searching" then
        previous.status = "stopped"
        previous.searchTermination = "user_stopped"
    end
    previous.inFlight = false
    planPrevMem[scope] = { key = key, result = previous }
end

function RA.HasPlanPrev(slug)
    if not slug then return false end
    local xp = getExecution()
    local previous = planPrevMem[character() .. "|" .. slug]
    local canRevert = true
    if xp and type(xp.CanRevertCandidate) == "function" then
        local okC, canC = pcall(xp.CanRevertCandidate, slug)
        canRevert = okC and canC
    end
    return canRevert and previous ~= nil and not previous.result.finalizing
end

function RA.RevertPlan(slug, supplied)
    if not RA.HasPlanPrev(slug) then return false end
    local db = saved()
    if not db then return false end
    local scope = character() .. "|" .. slug
    local previous = planPrevMem[scope]
    local result = previous.result
    discardScope(scope)
    planPrevMem[scope] = nil
    revision = revision + 1
    result.revision = revision
    results[previous.key] = result
    active[scope] = previous.key
    refreshFreshness(result, slug, options(slug, supplied))
    remember({ slug = slug, signature = result.cacheSignature, opts = result.executionOptions or {} }, result)
    for _, fn in ipairs(listeners) do pcall(fn, slug, result) end
    return result
end

function RA.SkeletonOf(plan)
    if type(plan) ~= "table" then return nil end
    return planSkeleton(plan, plan.executionOptions or {}, plan.status)
end

function RA.SnapshotPlan(plan)
    if type(plan) ~= "table" then return nil end
    if type(plan.steps) ~= "table" or #plan.steps == 0 then return nil end
    return copy(plan)
end

function RA.RestorePlan(slug, snapshot, supplied)
    if not slug or type(snapshot) ~= "table" then return false end
    if type(snapshot.steps) ~= "table" or #snapshot.steps == 0 then return false end
    local db = saved()
    if not db then return false end
    local result = copy(snapshot)
    local scope = character() .. "|" .. slug
    local key = result.cacheSignature or result.key
    if not key then return false end
    ensureBridgeHook()
    discardScope(scope)
    revision = revision + 1
    result.revision = revision
    result.inFlight = false
    result.finalizing = nil
    if result.status == "searching" then result.status = "stopped" end
    results[key] = result
    active[scope] = key
    refreshFreshness(result, slug, options(slug, supplied))
    remember({ slug = slug, signature = result.cacheSignature, opts = result.executionOptions or {} }, result)
    for _, fn in ipairs(listeners) do pcall(fn, slug, result) end
    return result
end

function RA.Invalidate(reason)
    if invalidating then return end
    invalidating = true
    local invFn = getBaseInvalidate()
    if type(invFn) == "function" then pcall(invFn) end
    if reason ~= nil then
        reason = type(reason) == "string" and reason or "inputs"
        for _, job in pairs(jobs) do job.stale = true; job.staleReason = reason end
        for _, result in pairs(results) do result.stale = true; result.staleReason = reason end
        for _, entry in pairs(planPrevMem) do entry.result.stale = true; entry.result.staleReason = reason end
        local xp = getExecution()
        local E = getEconomy()
        if xp and type(xp.GetPlan) == "function" then
            local list = (E and E.PrimaryOrder) or { "alchemy", "blacksmithing", "cooking", "enchanting", "engineering", "first-aid", "leatherworking", "mining", "tailoring" }
            for _, slug in ipairs(list) do
                local okP, plan = pcall(xp.GetPlan, slug)
                if okP and plan then plan.stale = true; plan.staleReason = reason end
            end
        end
    end
    invalidating = false
end

function RA.Pump(slug)
    for _, job in pairs(jobs) do if not slug or job.slug == slug then pump(job) end end
end

function RA.Peek(slug)
    if slug then
        local scope = character() .. "|" .. slug
        return active[scope] and results[active[scope]]
    end
    for _, job in pairs(jobs) do if not job.invalid then return job.published end end
end

function RA.HasWork(slug)
    for _, job in pairs(jobs) do
        if (not slug or job.slug == slug) and not job.cancelled and not job.finished and not job.invalid then
            return true
        end
    end
    return false
end

function RA.Cancel(slug, reason)
    local changed = false
    for _, job in pairs(jobs) do
        if (not slug or job.slug == slug) and not job.finished and not job.invalid then
            pause(job, "user_stopped")
            job.scheduled = false
            job.scheduleVersion = (job.scheduleVersion or 0) + 1
            if reason == "settings" then job.bagSettingChanged = true end
            local result = job.published
            if result then
                result.status = "stopped"
                result.inFlight = false
                result.searchTermination = "user_stopped"
                publish(job, result)
            end
            changed = true
        end
    end
    return changed
end

function RA.Continue(slug)
    if replicatePrerequisite(slug, {}) then return false end
    for _, job in pairs(jobs) do
        if (not slug or job.slug == slug) and job.cancelled and not job.finished and not job.invalid then
            if job.bagSettingChanged then return false end
            job.cancelled = false
            job.status = job.resumeStatus or "searching"
            job.searchTermination = job.resumeTermination
            job.resumeStatus = nil
            job.resumeTermination = nil
            if job.published then
                job.published.status = job.status
                job.published.searchTermination = job.searchTermination
            end
            schedule(job)
        end
    end
end

function RA.ReleaseExecution(slug)
    for key, job in pairs(jobs) do
        if job.slug == slug then
            job.status = "stopped"
            job.cancelled = true
            job.searchTermination = "execution_ended"
            local result = job.published
            if result then
                result.status = "stopped"
                result.inFlight = false
                result.searchTermination = "execution_ended"
                publish(job, result)
            end
            if legacyRun and legacyRun.job == job then
                legacyRun = nil
            end
            release(job)
            jobs[key] = nil
        end
    end
    if legacyRun and (legacyRun.slug == slug or (legacyRun.job and legacyRun.job.slug == slug)) then
        legacyRun = nil
    end
end

function RA.EndExecution(slug)
    local xp = getExecution()
    local ended
    if xp and type(xp.End) == "function" then
        local okE, vE = pcall(xp.End, slug, "ended")
        if okE then ended = vE end
    end
    RA.ReleaseExecution(slug)
    return ended
end

function RA.PlanSig(slug, opts)
    return signature(slug, options(slug, opts))
end

RA.Start = RA.Get

run.Running = RA.HasWork
run.Stop = RA.Cancel

run.Result = function(job)
    if type(job) == "string" then
        return RA.Peek(job)
    end
    job = job or (legacyRun and legacyRun.job)
    if job then return job.result or job.published end
    local s = lastRunSlug
    if not s then
        local dbMod = getDB()
        local root = resolveDBRoot(dbMod)
        s = type(root) == "table" and type(root.prof) == "table" and root.prof.lastSlug or nil
    end
    return RA.Peek(s)
end

run.Active = function(slug)
    for _, job in pairs(jobs) do
        if (not slug or job.slug == slug) and not job.finished and not job.invalid and not job.cancelled then
            return { job = job, slug = job.slug }
        end
    end
end

run.State = function(job)
    if type(job) == "string" or not job then
        local entry = run.Active(job)
        job = entry and entry.job
    end
    local phase, fraction
    if type(run.Stamp) == "function" then
        phase, fraction = run.Stamp(job)
    else
        phase, fraction = "idle", 0
    end
    return {
        phase = phase,
        fraction = fraction,
        seedSkill = job and job.seedSkill,
        target = job and job.target,
        finalizeProgress = job and job.finalizeProgress,
        batchSearch = job and job.batchSearch,
        expanded = job and job.expanded,
        cpuUsed = job and job.cpuUsed,
        cpuLimitMs = job and job.cpuLimitMs,
        status = job and job.status,
    }
end

run.Start = function(slug, opts, hooks)
    local supplied = opts
    opts = copy(opts or RA.OptionsFor(slug), nil, true)
    opts.cpuLimitMs = opts.cpuLimitMs or cfgCpuLimitMs()
    if supplied and supplied.snapshot then opts.snapshot = supplied.snapshot end
    lastRunSlug = slug
    local result = RA.Recalculate(slug, opts)
    local key, scope = identity(slug, options(slug, opts))
    local job = jobs[key] or { key = key, scope = scope, slug = slug, result = result, published = result, finished = true }
    job.hooks = hooks
    legacyRun = { job = job, slug = slug, hooks = hooks }
    if job.finished and hooks and hooks.onDone then pcall(hooks.onDone, job) end
    return legacyRun
end

local function registerSolverDelegate()
    local API = getAPI()
    if API and type(API.RegisterDelegate) == "function" then
        API.RegisterDelegate("solver", {
            Invalidate = function(reason)
                return RA.Invalidate(reason or "prices")
            end,
        })
    end
end

RA.RegisterSolverDelegate = registerSolverDelegate
registerSolverDelegate()

local fishingPlanWraps = setmetatable({}, { __mode = "k" })
local function guardComputeFishing()
    if type(RA._WrapComputeFishing) == "function" then
        RA._WrapComputeFishing()
        return
    end
    local fn = RA.ComputeFishing
    if type(fn) ~= "function" or fishingPlanWraps[fn] then return end
    local wrapped = function(slug, opts)
        local ok, res = pcall(fn, slug, opts)
        if ok then return res end
        if type(RA._StandaloneComputeFishing) == "function" then
            local okS, resS = pcall(RA._StandaloneComputeFishing, slug, opts)
            if okS then return resS end
        end
        return nil
    end
    fishingPlanWraps[wrapped] = true
    RA.ComputeFishing = wrapped
end

local function initialize()
    ensureBridgeHook()
    guardComputeFishing()
    if type(RA.RegisterDelegate) == "function" then
        RA.RegisterDelegate()
    end
    if type(_G.CreateFrame) == "function" then
        local ok, frame = pcall(_G.CreateFrame, "Frame")
        if ok and type(frame) == "table" and type(frame.RegisterEvent) == "function" and type(frame.SetScript) == "function" then
            pcall(frame.RegisterEvent, frame, "PLAYER_LOGOUT")
            pcall(frame.RegisterEvent, frame, "BAG_UPDATE_DELAYED")
            pcall(frame.SetScript, frame, "OnEvent", function(_, event)
                if event == "BAG_UPDATE_DELAYED" then
                    for _, result in pairs(results) do
                        if result.useBagMaterials then
                            refreshFreshness(result, result.slug, result.executionOptions or {})
                        end
                    end
                    local xp = getExecution()
                    local E = getEconomy()
                    if xp and type(xp.GetPlan) == "function" then
                        for _, slug in ipairs((E and E.PrimaryOrder) or {}) do
                            local okP, plan = pcall(xp.GetPlan, slug)
                            if okP and plan and plan.useBagMaterials then
                                refreshFreshness(plan, slug, plan.executionOptions or {})
                            end
                        end
                    end
                    return
                end
                for _, job in pairs(jobs) do
                    local result = job.published
                    if result and #(result.steps or {}) > 0 then
                        remember(job, result, "interrupted")
                    end
                end
            end)
        end
    end
end

local initFn = ns.Init or (type(gns) == "table" and gns.Init) or nil
if type(initFn) == "function" then
    initFn(initialize)
else
    initialize()
end
