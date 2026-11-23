local _, ns = ...
if type(ns) ~= "table" then ns = _G.DF_NS or {} end
local gns = _G.DF_NS

local NAME = "DungeonsForeverProfDB"

local function getSolverCfg()
    return ns.SolverConfig or (type(gns) == "table" and gns.SolverConfig) or nil
end

local function getPricingCfg()
    return ns.PricingConfig or (type(gns) == "table" and gns.PricingConfig) or nil
end

local function getProfCfg()
    return ns.ProfessionsConfig or (type(gns) == "table" and gns.ProfessionsConfig) or nil
end

local solverCfg = getSolverCfg()
local pricingCfg = getPricingCfg()

local DB = {}
DB.SCHEMA_VERSION = 3
DB.LV_CAP = (type(solverCfg) == "table" and type(solverCfg.CAP) == "number" and solverCfg.CAP) or 300
DB.LV_DEF = (type(solverCfg) == "table" and type(solverCfg.DEFAULT_TARGET) == "number" and solverCfg.DEFAULT_TARGET) or 300

DB.SETTING_DEF = {
    greyPassed = true,
    hlCurrent = true,
    autoRoute = false,
    autoOnlyAH = true,
    autoUseBagMaterials = false,
    autoConsiderAuctionSupply = false,
    autoBuyLimitedFormulas = false,
    autoAllowBindOnPickupFormulas = false,
    autoAllowCurrencyFormulas = false,
    autoScheme = "cheapest",
    autoSecondaryLeveling = false,
    autoResidualMass = false,
    autoSkillBudget = "balanced",
    computationSpeed = "fast",
    recoveryEnabled = false,
    recoveryFeePercent = (type(pricingCfg) == "table" and type(pricingCfg.DEFAULT_RECOVERY_FEE_PCT) == "number" and pricingCfg.DEFAULT_RECOVERY_FEE_PCT) or 5,
    autoCraftTools = true,
    autoFromCurrent = true,
    autoStartSkill = 1,
    writOwnProfessionsOnly = false,
    autoSnapshot = false,
}

DB.PROF_SETTING_KEYS = {
    autoRoute = true,
    autoScheme = true,
    autoOnlyAH = true,
    autoConsiderAuctionSupply = true,
    autoUseBagMaterials = true,
    autoBuyLimitedFormulas = true,
    autoAllowBindOnPickupFormulas = true,
    autoAllowCurrencyFormulas = true,
    autoSecondaryLeveling = true,
    autoFromCurrent = true,
    autoStartSkill = true,
    autoCraftTools = true,
    recoveryEnabled = true,
    recoveryFeePercent = true,
    autoResidualMass = true,
    autoSkillBudget = true,
}

local RETIRED_SETTINGS = {
    autoLearnedOnly = true,
    autoAllowUnknownLearning = true,
    autoSkipUnpricedFormulas = true,
    autoNoFormula = true,
    autoReserveMode = true,
}

local function ensureTable(parent, key)
    if type(parent[key]) ~= "table" then
        parent[key] = {}
    end
    return parent[key]
end

local function seedProfDefaults(prof)
    if prof.target == nil then prof.target = DB.LV_DEF end
    if prof.autoSnapshot == nil then prof.autoSnapshot = false end
    if prof.engChoice == nil then prof.engChoice = "none" end
    if prof.cookingRoute == nil then prof.cookingRoute = "fishing" end
    if prof.gatherMode == nil then prof.gatherMode = "gather" end
    ensureTable(prof, "policies")
    ensureTable(prof, "lvTarget")
    ensureTable(prof, "professionSettings")
    ensureTable(prof, "routePartners")
    ensureTable(prof, "specChoices")
    ensureTable(prof, "matBan")
end

local function initFresh(tbl)
    if type(tbl) ~= "table" then
        tbl = {}
    else
        for k in pairs(tbl) do
            tbl[k] = nil
        end
    end
    tbl.schemaVersion = DB.SCHEMA_VERSION
    tbl.prof = {
        target = DB.LV_DEF,
        autoSnapshot = false,
        engChoice = "none",
        policies = {},
        lvTarget = {},
        professionSettings = {},
        routePartners = {},
        specChoices = {},
        matBan = {},
        cookingRoute = "fishing",
        gatherMode = "gather",
    }
    tbl.chars = {}
    tbl.client = {}
    tbl.cdWatch = {}
    tbl.execution = {}
    tbl.routePlans = {}
    return tbl
end

local function ensureSchema(db)
    if type(db) ~= "table" or db.schemaVersion ~= DB.SCHEMA_VERSION then
        db = initFresh(db)
        _G[NAME] = db
    end
    local prof = ensureTable(db, "prof")
    seedProfDefaults(prof)
    ensureTable(db, "chars")
    ensureTable(db, "client")
    ensureTable(db, "cdWatch")
    ensureTable(db, "execution")
    ensureTable(db, "routePlans")
    return db
end

function DB.Get()
    return ensureSchema(_G[NAME])
end

function DB.Reset()
    local db = initFresh(_G[NAME])
    _G[NAME] = db
    seedProfDefaults(db.prof)
    return db
end

function DB.CharacterKey()
    if type(_G.UnitGUID) == "function" then
        local ok, guid = pcall(_G.UnitGUID, "player")
        if ok and type(guid) == "string" and guid ~= "" then
            return guid
        end
    end
    local name, realm
    if type(_G.UnitNameUnmodified) == "function" then
        local ok, v = pcall(_G.UnitNameUnmodified, "player")
        if ok and type(v) == "string" and v ~= "" then name = v end
    end
    if not name and type(_G.UnitName) == "function" then
        local ok, v = pcall(_G.UnitName, "player")
        if ok and type(v) == "string" and v ~= "" then name = v end
    end
    if type(_G.GetRealmName) == "function" then
        local ok, v = pcall(_G.GetRealmName)
        if ok and type(v) == "string" and v ~= "" then realm = v end
    end
    if name or realm then
        return "offline:" .. tostring(name or "?") .. "-" .. tostring(realm or "?")
    end
    return "offline:player"
end

function DB.CharacterMeta(key)
    local db = DB.Get()
    if type(key) ~= "string" or key == "" then
        key = DB.CharacterKey()
    end
    local meta = ensureTable(db.chars, key)
    meta.guid = key
    local name
    if type(_G.UnitNameUnmodified) == "function" then
        local ok, v = pcall(_G.UnitNameUnmodified, "player")
        if ok and type(v) == "string" and v ~= "" then name = v end
    end
    if not name and type(_G.UnitName) == "function" then
        local ok, v = pcall(_G.UnitName, "player")
        if ok and type(v) == "string" and v ~= "" then name = v end
    end
    if name then meta.name = name end
    if type(_G.GetRealmName) == "function" then
        local ok, v = pcall(_G.GetRealmName)
        if ok and type(v) == "string" and v ~= "" then meta.realm = v end
    end
    if type(_G.UnitClass) == "function" then
        local ok, _, classToken, classID = pcall(_G.UnitClass, "player")
        if ok then
            if type(classToken) == "string" and classToken ~= "" then meta.class = classToken end
            if type(classID) == "number" then meta.classID = classID end
        end
    end
    return meta
end

function DB.CharacterStore(domain, key)
    if type(domain) ~= "string" or domain == "" then domain = "client" end
    local db = DB.Get()
    if type(key) ~= "string" or key == "" then
        key = DB.CharacterKey()
    end
    local bucket = ensureTable(db, domain)
    local store = ensureTable(bucket, key)
    DB.CharacterMeta(key)
    return store, key
end

local function isFixedOnly(slug)
    if type(slug) ~= "string" or slug == "" then return false end
    local cfg = getProfCfg()
    local entry = type(cfg) == "table" and type(cfg.BY_SLUG) == "table" and cfg.BY_SLUG[slug]
    if type(entry) == "table" then
        return entry.fixedOnly == true
    end
    return slug == "first-aid" or slug == "poisons"
end

function DB.TargetSkill(slug)
    local prof = DB.Get().prof
    local v
    if type(slug) == "string" and slug ~= "" and type(prof.lvTarget) == "table" then
        v = tonumber(prof.lvTarget[slug])
    end
    if not v then
        v = tonumber(prof.target)
    end
    if not v or v ~= v then return DB.LV_DEF end
    return math.max(1, math.min(DB.LV_CAP, math.floor(v)))
end

function DB.SetTargetSkill(slug, value)
    if value == nil and type(slug) == "number" then
        value = slug
        slug = nil
    end
    local n = tonumber(value)
    if not n or n ~= n then return nil end
    n = math.max(1, math.min(DB.LV_CAP, math.floor(n)))
    local prof = DB.Get().prof
    if type(slug) == "string" and slug ~= "" and slug ~= "__index" then
        ensureTable(prof, "lvTarget")[slug] = n
    else
        prof.target = n
    end
    return n
end

function DB.SettingRaw(k, slug)
    if RETIRED_SETTINGS[k] then return nil end
    if isFixedOnly(slug) then
        if k == "autoRoute" then return false end
        if k == "autoScheme" then return "fixed" end
    end
    local prof = DB.Get().prof
    if k == "target" then return DB.TargetSkill(slug) end
    if k == "engChoice" then
        local v = prof.engChoice
        return (v == "goblin" or v == "gnomish") and v or "none"
    end
    if k == "policies" then return ensureTable(prof, "policies") end
    local values = DB.PROF_SETTING_KEYS[k] and type(slug) == "string" and type(prof.professionSettings) == "table" and prof.professionSettings[slug]
    local v
    if type(values) == "table" then v = values[k] end
    if v == nil then v = prof[k] end
    if k == "autoScheme" and v == "stable" then return "cheapest" end
    if v == nil then return DB.SETTING_DEF[k] end
    return v
end

function DB.Setting(k, slug)
    return DB.SettingRaw(k, slug) and true or false
end

function DB.SetSettingRaw(k, value, slug)
    if RETIRED_SETTINGS[k] then return nil end
    if isFixedOnly(slug) and (k == "autoRoute" or k == "autoScheme") then return nil end
    if k == "target" then return DB.SetTargetSkill(slug, value) end
    local prof = DB.Get().prof
    if DB.PROF_SETTING_KEYS[k] and type(slug) == "string" and slug ~= "" and slug ~= "__index" then
        local ps = ensureTable(prof, "professionSettings")
        local bucket = ensureTable(ps, slug)
        bucket[k] = value
    else
        prof[k] = value
    end
    return value
end

function DB.SetSetting(k, value, slug)
    return DB.SetSettingRaw(k, value, slug)
end

function DB.AutoStartSkillOf(slug, current)
    if DB.Setting("autoFromCurrent", slug) then
        local lv = tonumber(current)
        return lv and math.max(1, math.floor(lv)) or 1
    end
    local n = tonumber(DB.SettingRaw("autoStartSkill", slug)) or 1
    if n < 1 then
        n = 1
    elseif n > DB.LV_CAP then
        n = DB.LV_CAP
    end
    return math.floor(n)
end

setmetatable(DB, {
    __call = function()
        return DB.Get()
    end,
})

ns.ProfDB = DB
ns.ProfSettings = DB
if type(gns) == "table" and gns ~= ns then
    gns.ProfDB = DB
    gns.ProfSettings = DB
end
