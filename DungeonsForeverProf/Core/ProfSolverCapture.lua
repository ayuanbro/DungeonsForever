local _, ns = ...
if type(ns) ~= "table" then ns = _G.DF_NS or {} end
local gns = _G.DF_NS

local E = ns.ProfEconomy or (type(gns) == "table" and gns.ProfEconomy) or {}
ns.ProfEconomy = E
local D = ns.ProfAuctionDepth or (type(gns) == "table" and gns.ProfAuctionDepth) or {}
ns.ProfAuctionDepth = D
if type(gns) == "table" and gns ~= ns then
    gns.ProfEconomy = E
    gns.ProfAuctionDepth = D
end

local floor, ceil, min, max, huge = math.floor, math.ceil, math.min, math.max, math.huge

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

local function getGates()
    return ns.ProfGates or (type(gns) == "table" and gns.ProfGates) or nil
end

local function getSupply()
    return ns.ProfSupply or (type(gns) == "table" and gns.ProfSupply) or nil
end

local function getRecovery()
    return ns.ProfRecovery or (type(gns) == "table" and gns.ProfRecovery) or nil
end

local function getEssences()
    return ns.ProfEssences or (type(gns) == "table" and gns.ProfEssences) or nil
end

local function getProfCfg()
    return ns.ProfessionsConfig or (type(gns) == "table" and gns.ProfessionsConfig) or nil
end

local function getSolverCfg()
    return ns.SolverConfig or (type(gns) == "table" and gns.SolverConfig) or nil
end

local function getPricingCfg()
    return ns.PricingConfig or (type(gns) == "table" and gns.PricingConfig) or nil
end

local function getRouteAuto()
    return ns.ProfRouteAuto or (type(gns) == "table" and gns.ProfRouteAuto) or nil
end

local function getExecution()
    return ns.ProfExecution or (type(gns) == "table" and gns.ProfExecution) or nil
end

local function getAuctionBridge()
    return ns.AuctionBridge or (type(gns) == "table" and gns.AuctionBridge) or nil
end

local function getL()
    return ns.L or (type(gns) == "table" and gns.L) or nil
end

local function tr(key)
    local L = getL()
    if type(L) == "table" then
        local ok, v = pcall(function() return L[key] end)
        if ok and type(v) == "string" and v ~= "" then return v end
    end
    return key
end

local function Now()
    if type(_G.time) == "function" then
        local ok, v = pcall(_G.time)
        if ok and type(v) == "number" then return v end
    end
    if type(os) == "table" and type(os.time) == "function" then
        local ok, v = pcall(os.time)
        if ok and type(v) == "number" then return v end
    end
    return 0
end

local function solverCap()
    local cfg = getSolverCfg()
    return (type(cfg) == "table" and type(cfg.CAP) == "number" and cfg.CAP) or 300
end

local function solverDefaultTarget()
    local cfg = getSolverCfg()
    return (type(cfg) == "table" and type(cfg.DEFAULT_TARGET) == "number" and cfg.DEFAULT_TARGET) or 300
end

local function supplyMaxAge()
    local ra = getRouteAuto()
    if ra and type(ra.MaxAuctionSupplyAgeSeconds) == "function" then
        local ok, v = pcall(ra.MaxAuctionSupplyAgeSeconds)
        if ok and type(v) == "number" and v > 0 then return v end
    end
    local cfg = getPricingCfg()
    if type(cfg) == "table" and type(cfg.SUPPLY_MAX_AGE_SEC) == "number" and cfg.SUPPLY_MAX_AGE_SEC > 0 then
        return cfg.SUPPLY_MAX_AGE_SEC
    end
    return 172800
end

local function shallow(t)
    local o = {}
    for k, v in pairs(t or {}) do o[k] = v end
    return o
end

local function copy(value, tick, seen, overrides)
    if type(value) ~= "table" then return value end
    seen = seen or {}
    if seen[value] then return seen[value] end
    local original = value
    local meta = getmetatable(value)
    if type(meta) == "table" and type(meta.__profLearningMaterialize) == "function" then
        value = meta.__profLearningMaterialize(value)
    end
    local out, count = {}, 0
    seen[original] = out
    if value ~= original then seen[value] = out end
    if overrides then
        for k, v in pairs(value) do
            if overrides[k] == nil then out[k] = copy(v, tick, seen) end
            count = count + 1
            if tick and count % 64 == 0 then tick() end
        end
        for k, v in pairs(overrides) do out[k] = v end
        return out
    end
    for k, v in pairs(value) do
        out[k] = copy(v, tick, seen)
        count = count + 1
        if tick and count % 64 == 0 then tick() end
    end
    return out
end

if type(E.Copy) ~= "function" then
    E.Copy = function(value, tick, overrides)
        return type(value) == "table" and copy(value, tick, nil, overrides) or {}
    end
end

local function positiveInteger(value)
    return type(value) == "number" and value > 0 and value == floor(value)
end

local function materialsValid(mats)
    if type(mats) ~= "table" then return false end
    for _, m in ipairs(mats) do
        if type(m) ~= "table" or not positiveInteger(m[1]) or not positiveInteger(m[2]) then return false end
    end
    return true
end

local function normalizeFaction(value)
    if value == "Alliance" or value == "a" or value == "A" or value == "联盟" then return "A" end
    if value == "Horde" or value == "h" or value == "H" or value == "部落" then return "H" end
    if value == "Neutral" or value == "n" or value == "N" or value == "Both" or value == "B" then return "N" end
    return value
end

local function resolveDB()
    local dbFn = getDB()
    if type(dbFn) == "table" and type(dbFn.Get) == "function" then
        local ok, root = pcall(dbFn.Get)
        if ok and type(root) == "table" then return root end
    elseif type(dbFn) == "function" then
        local ok, root = pcall(dbFn)
        if ok and type(root) == "table" then return root end
    end
    return nil
end

local fallbackClientStore = {}

if type(E.CharacterKey) ~= "function" then
    function E.CharacterKey()
        local db = getDB()
        if type(db) == "table" and type(db.CharacterKey) == "function" then
            return db.CharacterKey()
        end
        if type(_G.UnitGUID) == "function" then
            local ok, guid = pcall(_G.UnitGUID, "player")
            if ok and type(guid) == "string" and guid ~= "" then return guid end
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
end

if type(E.ClientStore) ~= "function" then
    function E.ClientStore()
        local db = getDB()
        if type(db) == "table" and type(db.CharacterStore) == "function" then
            return db.CharacterStore("client")
        end
        local root = resolveDB()
        if type(root) == "table" then
            root.client = type(root.client) == "table" and root.client or {}
            local key = E.CharacterKey()
            root.client[key] = type(root.client[key]) == "table" and root.client[key] or {}
            return root.client[key]
        end
        return fallbackClientStore
    end
end

if type(E.GetPolicies) ~= "function" then
    function E.GetPolicies()
        return {}
    end
end

if type(E.Policies) ~= "function" then
    E.Policies = E.GetPolicies
end

if type(E.Policy) ~= "function" then
    function E.Policy(policies, r)
        if not policies or not r then return nil end
        local spell = r.spell or r.spellID
        local key = r.key or (r.profession and spell ~= nil and (tostring(r.profession) .. ":" .. tostring(spell)))
        return (key and policies[key]) or (spell ~= nil and policies[spell]) or nil
    end
end

if type(E.RecipeNIP) ~= "function" then
    function E.RecipeNIP(spell, recipe)
        if type(recipe) == "table" then
            if recipe.availability ~= nil then return recipe.availability ~= "live" end
            if recipe.nip == true then return true end
        end
        local id = spell
        if id == nil and type(recipe) == "table" then
            id = recipe.spellID or recipe.spell or recipe[1]
        end
        if positiveInteger(id) then
            local DS = getDS()
            local rec = DS and type(DS.Recipe) == "function" and DS.Recipe(id) or nil
            if type(rec) == "table" then
                return rec.availability ~= "live"
            end
        end
        return false
    end
end

local function buildPrimaryOrder()
    local cfg = getProfCfg()
    local order = type(cfg) == "table" and cfg.ORDER
    local bySlug = type(cfg) == "table" and cfg.BY_SLUG
    if type(order) == "table" and type(bySlug) == "table" then
        local out = {}
        for i = 1, #order do
            local slug = order[i]
            local meta = bySlug[slug]
            if type(meta) == "table" and (meta.supportsAutoRoute or meta.supportsExecution or meta.fixedOnly) and not meta.skipEconomy then
                out[#out + 1] = slug
            end
        end
        if #out > 0 then return out end
    end
    return {
        "alchemy", "blacksmithing", "enchanting", "engineering",
        "leatherworking", "tailoring", "mining", "cooking", "first-aid",
    }
end

E.PrimaryOrder = buildPrimaryOrder()

local DIAG_KEYS = {
    inventoryUnknown = "请打开背包和银行，再查看需要购买的数量。",
    vendorEstimate = "NPC购买价格尚未配置。",
    vendorQuoteChanged = "NPC购买价格资料已更新，请重新计算路线。",
    toolPolicyChanged = "工具设置或工具列表已变化，请手动重新计算路线。",
    fixedOnlyChanged = "急救已改为固定路线，请重新计算。",
    cooldown = "已排除有冷却的制作配方。",
    cooldownUnknown = "制作冷却尚未核实，请打开对应专业面板。",
    outputConflict = "制作产量待读取，请打开对应专业面板。",
    availabilityUnknown = "配方学习条件尚未核实。",
    excluded = "配方已按自定义规则排除。",
    catalogueFiltered = "路线包含已排除的配方，请重新计算。",
    notLearned = "当前设置仅允许已学配方。",
    clientUnavailable = "客户端已确认此配方不可用。",
    specializationRequired = "尚未满足此配方的专业专精学习要求。",
    specializationChanged = "专精选择或学习条件已变化，请手动重新计算路线。",
    specializationFixed = "固定攻略包含尚不可用的专精配方或入门任务，请切换自动规划。",
    specializationEvidenceConflict = "此配方的专精学习资料存在冲突，需要确认。",
    specializationChoiceConflict = "当前已学专精与所选目标不同；本路线不处理转修专精。",
    specializationFactionUnknown = "尚未读取角色阵营，无法确定专精任务交付地点。",
    specializationQuestAlreadyCompleted = "入门任务已经完成，但当前未确认所需专精；请先核实转修条件。",
    specializationUnknown = "角色专精状态尚未读取，请登录角色并打开工程学面板后重试。",
    specializationLevelRequired = "角色等级不足 30，暂时无法完成工程专精入门任务。",
    specializationLevelUnknown = "尚未读取角色等级，无法确认工程专精任务资格。",
    specializationQuestDisabled = "客户端已确认此专精任务当前不可用。",
    professionMissing = "角色尚未学习所需专业。",
    skillRequired = "另一专业技能不足，可开启联合升级或购买材料。",
    secondaryRequired = "请先选择联合升级的另一个专业。",
    secondaryDisabled = "联合升级已关闭，请重新计算当前专业路线。",
    pairingChanged = "搭配专业已更改，点击重新计算应用。",
    professionChanged = "专业学习状态或旧路线规则已变化，请重新计算路线。",
    pricingPolicyChanged = "专业学习状态或旧路线规则已变化，请重新计算路线。",
    formulaUnavailable = "未学配方的图纸没有可靠的购买报价；任务图纸需先学会或取得拍卖行报价。",
    bindOnPickupFormulaDisabled = "非金币获取的拾取绑定图纸未开启；此配方暂不参与路线。",
    currencyFormulaDisabled = "非金币拾取绑定与通货兑换均未开启；此配方暂不参与路线。",
    formulaAcquisitionPending = "请先取得并学习所需图纸，再开始制作。",
    formulaAuctionSupplyUnknown = "请打开拍卖行完成一次完整扫描，确认图纸在售后重新计算路线。",
    formulaAuctionSupplyInsufficient = "本次扫描的图纸数量不够；请打开拍卖行完成一次完整扫描后重新计算，或选择其他图纸来源。",
    limitedFormulaDisabled = "限量NPC采购已关闭；可开启「允许NPC限量销售图纸」，或使用有价格且近期在售数量至少1张的拍卖行图纸。",
    formulaPriceUnknown = "请在购物清单核对图纸费用；拍卖行报价请在完整扫描后更新。",
    learningPriceUnknown = "请打开训练师页面核对学习费用。",
    formulaStockUnknown = "请向商人核对图纸现货；限量图纸可能需要等待刷新。",
    auctionSupplyLimited = "本次扫描的材料数量不够；请打开拍卖行完成一次完整扫描后重新计算，或更换货源。",
    fishingRecipeGap = "当前技能没有符合纯钓鱼条件的可用配方，请检查食谱、材料来源或排除设置。",
    fishingRequirementsUnknown = "鱼类的钓取门槛或时间限制尚未确认，暂不用于纯钓鱼路线。",
    professionCapUnknown = "当前专业技能上限尚未读取，暂不推断最后一段采集目标。",
    materialUnavailable = "材料没有可靠的购买或制作来源。",
    levelGap = "当前技能区间没有可用升级配方。",
    clientDataPending = "客户端数据待读取，请打开对应专业面板。",
    solverError = "计算发生错误，请重新计算。",
    vendorPending = "商人购买价格尚未配置。",
    characterLevelRequired = "角色等级不足，无法学习所需专业等级。",
    vendorPriceUnknown = "请向商人核对购买价格。",
    materialPriceUnknown = "请打开拍卖行完成一次完整扫描，再重新计算路线。",
    batchDependency = "合并制作所需的材料或学习等级尚未满足。",
    batchSkillGap = "合并制作后无法达到目标技能，请调整配方限制。",
    executionInvalid = "制作顺序或材料用途无法验证，请调整限制后重新计算。",
    learningRequirementsUnknown = "配方学习条件尚未核实。",
    learningDataMissing = "学习资料缺失：该配方没有已确认的学习路径。",
    characterRaceRequired = "当前种族不满足这条学习路径。",
    characterClassRequired = "当前职业不满足这条学习路径。",
    poisonRogueRequired = "毒药仅限盗贼学习和制作。",
    reputationRequired = "当前声望不满足这条学习路径。",
    questRequired = "尚未完成这条学习路径要求的任务。",
    learningFactionRequired = "当前阵营不满足这条学习路径。",
    learningConditionFailed = "尚未满足这条学习路径的条件。",
    learningPolicyChanged = "学习资料已更新，请重新计算；执行记录与进度已保留。",
    toolFactsUnknown = "制作工具的配方或产量资料尚未核实。",
}

local function itemDisplayName(id)
    local API = getAPI()
    if API and type(API.ItemName) == "function" then
        local name = API.ItemName(id)
        if type(name) == "string" and name ~= "" and name ~= ("#" .. tostring(id)) then
            return name
        end
    end
    local DS = getDS()
    if DS and type(DS.RawText) == "function" then
        local name = DS.RawText("item", id)
        if type(name) == "string" and name ~= "" then return name end
    end
    local ci = _G.C_Item
    local fn = (type(ci) == "table" and ci.GetItemInfo) or _G.GetItemInfo
    if type(fn) == "function" then
        local ok, name = pcall(fn, id)
        if ok and type(name) == "string" and name ~= "" then return name end
    end
    return "#" .. tostring(id)
end

function E.DiagnosticText(d)
    if type(d) == "string" then
        local key = DIAG_KEYS[d]
        return key and tr(key) or d
    end
    if type(d) ~= "table" then return nil end
    if type(d.message) == "string" then return d.message end
    local code = d.code
    if type(code) ~= "string" then return nil end
    if code == "auctionSupplyLimited" and d.item and d.required and d.available then
        local name = itemDisplayName(d.item)
        return string.format(tr("%s：扫描记录有 %d 件，需要 %d 件；请打开拍卖行完成一次完整扫描后重新计算，或更换货源。"), name, d.available, d.required)
    end
    local key = DIAG_KEYS[code]
    return key and tr(key) or code
end

function E.Gain(r, skill)
    if type(r) ~= "table" then return 0 end
    if not E.HasGainThresholds(r) then return 0 end
    local yellow, green, grey = r.yellow, r.green, r.grey
    if skill < r.learn or (r.orange and skill < r.orange) or skill >= grey then return 0 end
    if skill < yellow then return 1 end
    local cfg = getSolverCfg()
    local dr = type(cfg) == "table" and type(cfg.DIFFICULTY_RATES) == "table" and cfg.DIFFICULTY_RATES or nil
    local gYellow = (dr and type(dr.G_YELLOW) == "number" and dr.G_YELLOW) or 0.5
    local gGreen = (dr and type(dr.G_GREEN) == "number" and dr.G_GREEN) or 0.05
    if skill < green then
        return 1 - ((skill - yellow) / max(1, green - yellow)) * (1 - gYellow)
    end
    return max(gGreen, gYellow - ((skill - green) / max(1, grey - green)) * (gYellow - gGreen))
end

local greenRates = {}

function E.GreenBudgetMode(mode)
    local cfg = getSolverCfg()
    local modes = type(cfg) == "table" and type(cfg.GREEN_BUDGET_MODES) == "table" and cfg.GREEN_BUDGET_MODES or nil
    if modes and modes[mode] then return mode end
    if mode == "optimistic" or mode == "pessimistic" then return mode end
    return "balanced"
end

function E.PlanningGain(r, skill, mode, allColors)
    local p = E.Gain(r, skill)
    if p <= 0 or p >= 1 then return p, 1 end
    mode = E.GreenBudgetMode(mode)
    local cfg = getSolverCfg()
    local modes = type(cfg) == "table" and type(cfg.GREEN_BUDGET_MODES) == "table" and cfg.GREEN_BUDGET_MODES or nil
    local modeCfg = modes and modes[mode] or nil
    local expectedOnly = modeCfg and modeCfg.expectedCraftsOnly == true
    local missLog = modeCfg and modeCfg.missLog or (mode == "balanced" and math.log(0.20) or mode == "pessimistic" and math.log(0.05) or nil)
    if expectedOnly or not missLog then return p, 1 end
    local green = skill >= r.green
    if not allColors and not green then return p, 1 end
    local factor = 1.0
    if green then
        if modeCfg and type(modeCfg.greenRateFactor) == "number" then
            factor = modeCfg.greenRateFactor
        elseif mode == "pessimistic" then
            factor = 0.5
        end
    end
    local assumed = p * factor
    if assumed <= 0 or assumed >= 1 then return p, 1 end
    local cache = greenRates[mode]
    if not cache then
        cache = {}
        greenRates[mode] = cache
    end
    local gain = cache[assumed]
    if not gain then
        local attempts = ceil(missLog / math.log(1 - assumed) - 1e-10)
        gain = min(p, ceil(1000000 / attempts) / 1000000)
        cache[assumed] = gain
    end
    return gain, floor(gain / p * 65536 + 0.5) / 65536
end

local function isPrimarySlug(slug)
    if type(slug) ~= "string" then return false end
    local DS = getDS()
    if DS and type(DS.Profession) == "function" then
        local info = DS.Profession(slug)
        if type(info) == "table" and info.kind ~= nil then
            return info.kind == "primary"
        end
    end
    local cfg = getProfCfg()
    local entry = type(cfg) == "table" and type(cfg.BY_SLUG) == "table" and cfg.BY_SLUG[slug] or nil
    if type(entry) == "table" then
        return entry.navGroup == "primary"
    end
    return slug ~= "cooking" and slug ~= "fishing" and slug ~= "first-aid"
        and slug ~= "poisons" and slug ~= "comprehension" and slug ~= "camping"
end

if type(E.ProfessionSlug) ~= "function" then
    function E.ProfessionSlug(id)
        if type(id) ~= "number" then return nil end
        local DS = getDS()
        if DS and type(DS.SkillLineToSlug) == "function" then
            local slug = DS.SkillLineToSlug(id)
            if slug then return slug end
        end
        local cfg = getProfCfg()
        if type(cfg) == "table" and type(cfg.SKILL_LINE_TO_SLUG) == "table" then
            return cfg.SKILL_LINE_TO_SLUG[id]
        end
        return nil
    end
end

local function profLearnedFallback()
    local API = getAPI()
    if API and type(API.ProfLearned) == "function" then
        local list = API.ProfLearned()
        if type(list) == "table" and next(list) ~= nil then
            return list
        end
    end
    local out = {}
    if type(_G.GetProfessions) == "function" and type(_G.GetProfessionInfo) == "function" then
        local ok, a, b, c, d, e, f = pcall(_G.GetProfessions)
        if ok then
            local slots = { a, b, c, d, e, f }
            for i = 1, 6 do
                local idx = slots[i]
                if idx then
                    local found, _, _, cur, cap, _, _, id = pcall(_G.GetProfessionInfo, idx)
                    local slug = found and E.ProfessionSlug(id) or nil
                    if slug and type(cur) == "number" and type(cap) == "number" then
                        local prev = out[slug]
                        if prev then
                            if cur > prev.cur then
                                prev.cur = cur
                                prev.skillLineID = id
                            end
                            if cap > prev.max then prev.max = cap end
                        else
                            out[slug] = { cur = cur, max = cap, skillLineID = id }
                        end
                    end
                end
            end
        end
    end
    return out
end

if type(E.Professions) ~= "function" then
    function E.Professions()
        local out = {}
        local defCap = solverCap()
        for slug, v in pairs(profLearnedFallback()) do
            if type(v) == "table" then
                out[slug] = {
                    cur = tonumber(v.cur) or 1,
                    max = tonumber(v.max) or defCap,
                    primary = v.primary ~= nil and v.primary == true or isPrimarySlug(slug),
                    skillLineID = v.skillLineID,
                }
            end
        end
        return out
    end
end

function E.SpecializationKnown(spell)
    if not positiveInteger(spell) then return nil end
    if type(_G.IsLoggedIn) == "function" then
        local ok, ready = pcall(_G.IsLoggedIn)
        if ok and ready == false then return nil end
    end
    local Cond = getCond()
    if Cond and type(Cond.Evaluate) == "function" then
        return Cond.Evaluate({ kind = "ability", spellID = spell })
    end
    local apis = {
        { _G.C_SpellBook, "IsSpellKnown" },
        { _G, "IsSpellKnown" },
        { _G, "IsPlayerSpell" },
        { _G.C_Spell, "IsSpellKnown" },
    }
    for i = 1, #apis do
        local parent, key = apis[i][1], apis[i][2]
        local fn = type(parent) == "table" and parent[key]
        if type(fn) == "function" then
            local ok, value = pcall(fn, spell)
            if ok and type(value) == "boolean" then return value end
        end
    end
    return nil
end

if type(E.Known) ~= "function" then
    function E.Known(spell)
        if not positiveInteger(spell) then return nil end
        local d = E.ClientStore()
        local rt = type(d) == "table" and type(d.recipes) == "table" and d.recipes[spell] or nil
        if type(rt) == "table" and rt.learned == true then return true end
        local Cond = getCond()
        if Cond and type(Cond.Evaluate) == "function" then
            return Cond.Evaluate({ kind = "ability", spellID = spell })
        end
        local observedFalse = false
        local apis = {
            { _G.C_SpellBook, "IsSpellKnown" },
            { _G, "IsSpellKnown" },
            { _G, "IsPlayerSpell" },
            { _G.C_Spell, "IsSpellKnown" },
        }
        for i = 1, #apis do
            local parent, key = apis[i][1], apis[i][2]
            local fn = type(parent) == "table" and parent[key]
            if type(fn) == "function" then
                local ok, value = pcall(fn, spell)
                if ok and value == true then return true end
                if ok and value == false then observedFalse = true end
            end
        end
        if observedFalse then return false end
        return nil
    end
end

local PRIMARY_FALLBACK = {
    "alchemy", "blacksmithing", "enchanting", "engineering",
    "leatherworking", "tailoring", "mining", "herbalism", "skinning",
}

local fallbackPartners = {}
local function partnerStore()
    local root = resolveDB()
    if type(root) == "table" then
        root.prof = type(root.prof) == "table" and root.prof or {}
        root.prof.routePartners = type(root.prof.routePartners) == "table" and root.prof.routePartners or {}
        return root.prof.routePartners
    end
    return fallbackPartners
end

function E.PartnerCandidates(slug)
    local out, seen = {}, {}
    local function add(p)
        if p ~= slug and not seen[p] and isPrimarySlug(p) then
            seen[p] = true
            out[#out + 1] = p
        end
    end
    local cfg = getProfCfg()
    local order = (type(cfg) == "table" and type(cfg.ORDER) == "table" and cfg.ORDER) or PRIMARY_FALLBACK
    for i = 1, #order do add(order[i]) end
    for i = 1, #PRIMARY_FALLBACK do add(PRIMARY_FALLBACK[i]) end
    return out
end

function E.ValidPartner(slug, partner)
    if type(partner) ~= "string" or partner == "" then return false end
    local list = E.PartnerCandidates(slug)
    for i = 1, #list do
        if list[i] == partner then return true end
    end
    return false
end

function E.GetRoutePartner(slug)
    local partner = partnerStore()[slug]
    if E.ValidPartner(slug, partner) then return partner end
    return nil
end

function E.SetRoutePartner(slug, partner)
    if partner ~= nil and not E.ValidPartner(slug, partner) then return false end
    local saved = partnerStore()
    if saved[slug] == partner then return true end
    saved[slug] = partner
    local ra = getRouteAuto()
    if ra and type(ra.Invalidate) == "function" then pcall(ra.Invalidate) end
    return true
end

function E.RouteContext(slug, opts, professions)
    opts = opts or {}
    professions = professions or (opts.snapshot and opts.snapshot.professions) or E.Professions()
    local target = professions[slug]
    local unlearned = not target or target.unlearned == true
    local partner = opts.secondaryProfession
    if partner == nil then partner = E.GetRoutePartner(slug) end
    local valid = E.ValidPartner(slug, partner)
    local ctx = {
        unlearned = unlearned,
        requiresPartner = slug ~= "__purchase" and unlearned and opts.allowSecondaryLeveling == true,
        partner = valid and partner or nil,
        partnerValid = valid,
    }
    local G = getGates()
    if G and type(G.EngineeringChoice) == "function" then
        local choice = G.EngineeringChoice()
        ctx.specializationContext = {
            choice = choice,
            abilities = type(G.Abilities) == "function" and G.Abilities() or {},
            selectionConflict = (choice == "conflict") or false,
        }
    end
    return ctx
end

local function learnedCap(professions)
    for _, v in pairs(professions or {}) do
        if type(v) == "table" and type(v.max) == "number" and v.max > 0 and not v.unlearned then
            return v.max
        end
    end
    return solverCap()
end

function E.RouteProfessions(slug, opts, professions)
    opts = opts or {}
    professions = professions or (opts.snapshot and opts.snapshot.professions) or E.Professions()
    local context = E.RouteContext(slug, opts, professions)
    if slug == "__purchase" then return professions, context end
    if not context.unlearned and opts.allowSecondaryLeveling then return professions, context end
    local cap = learnedCap(professions)
    local selected = {}
    local target = professions[slug]
    if target then
        selected[slug] = shallow(target)
    else
        selected[slug] = { cur = tonumber(opts.start) or 1, max = cap, primary = true }
    end
    if context.unlearned then selected[slug].unlearned = true end
    if context.requiresPartner and context.partnerValid then
        local partner = professions[context.partner]
        if partner and not partner.unlearned then
            selected[context.partner] = shallow(partner)
        else
            selected[context.partner] = { cur = 1, max = cap, primary = true, unlearned = true }
        end
    end
    return selected, context
end

local function readSettingRaw(setting, slug)
    local settings = getSettings()
    if type(settings) == "table" and type(settings.SettingRaw) == "function" then
        return settings.SettingRaw(setting, slug)
    end
    local root = resolveDB()
    local prof = type(root) == "table" and root.prof or nil
    if type(prof) == "table" then
        if type(slug) == "string" and type(prof.professionSettings) == "table" and type(prof.professionSettings[slug]) == "table" then
            local v = prof.professionSettings[slug][setting]
            if v ~= nil then return v end
        end
        return prof[setting]
    end
    return nil
end

local function settingPermission(context, field, setting, profession)
    if type(context) == "table" and context[field] ~= nil then return context[field] == true end
    local snapshot = type(context) == "table" and context.snapshot or nil
    if type(snapshot) == "table" and snapshot[field] ~= nil then return snapshot[field] == true end
    if snapshot or (type(context) == "table" and (context.prices ~= nil or context.known ~= nil or context.recipes ~= nil)) then
        return false
    end
    local slug = profession or (type(context) == "table" and (context.profession or context.targetProfession))
        or (type(snapshot) == "table" and snapshot.targetProfession)
    return readSettingRaw(setting, slug) == true
end

function E.GetEngineeringSpecialization()
    local G = getGates()
    return (G and type(G.GetPlannedChoice) == "function" and G.GetPlannedChoice()) or "none"
end

function E.GetEngineeringSpecializationContext(opts)
    local G = getGates()
    return (G and type(G.SpecializationContext) == "function" and G.SpecializationContext(opts)) or { abilities = {}, goals = {}, choice = "none" }
end

function E.SpecializationFingerprint(context)
    return context and context.fingerprint or ""
end

function E.SpecializationAbilityFingerprint(abilities)
    local G = getGates()
    return (G and type(G.SpecAbilityFingerprint) == "function" and G.SpecAbilityFingerprint(abilities)) or ""
end

local function professionTools(slug)
    if type(slug) ~= "string" or slug == "" then return {} end
    local DS = getDS()
    local tools = DS and type(DS.Tools) == "function" and DS.Tools() or nil
    if type(tools) ~= "table" then return {} end
    local out = {}
    for key, tool in pairs(tools) do
        if type(tool) == "table" and tool.profession == slug then
            local itemID = tool.itemID or tool.item or (positiveInteger(key) and key or nil)
            local spellID = tool.craftSpellID or tool.spell
            local entry = copy(tool)
            entry.itemID = itemID
            entry.item = itemID
            entry.craftSpellID = spellID
            entry.spell = spellID
            out[#out + 1] = entry
        end
    end
    table.sort(out, function(a, b)
        local ma, mb = a.minSkill or 0, b.minSkill or 0
        if ma ~= mb then return ma < mb end
        local ta, tb = a.tier or 0, b.tier or 0
        if ta ~= tb then return ta < tb end
        return (a.itemID or 0) < (b.itemID or 0)
    end)
    return out
end

function E.ToolPlanningEnabled(opts, slug)
    if type(opts) == "table" and opts.autoCraftTools ~= nil then return opts.autoCraftTools ~= false end
    if type(opts) == "table" and type(opts.snapshot) == "table" and opts.snapshot.autoCraftTools ~= nil then
        return opts.snapshot.autoCraftTools ~= false
    end
    slug = slug or (type(opts) == "table" and (opts.profession or opts.targetProfession or (type(opts.snapshot) == "table" and opts.snapshot.targetProfession)))
    local value = readSettingRaw("autoCraftTools", slug)
    if value ~= nil then return value ~= false end
    return true
end

function E.ToolFingerprint(slug, opts)
    local DS = getDS()
    local rev = (DS and type(DS.Fingerprint) == "function" and DS.Fingerprint())
        or (DS and type(DS.Build) == "function" and DS.Build())
        or 0
    local parts = { tostring(E.ToolPlanningEnabled(opts, slug)), tostring(rev) }
    for _, tool in ipairs(professionTools(slug)) do
        local spellID = tool.craftSpellID or tool.spell or 0
        local itemID = tool.itemID or tool.item or 0
        parts[#parts + 1] = table.concat({ spellID, itemID, tool.minSkill or 0, tostring(tool.bindOnPickup or false), tool.tier or 0 }, ":")
    end
    return table.concat(parts, "|")
end

local function planningToolRecipe(slug, spell, snapshot)
    if not positiveInteger(spell) then return nil end
    for _, recipe in ipairs(type(snapshot) == "table" and snapshot.recipes or {}) do
        if recipe.profession == slug and (recipe.spell == spell or recipe.spellID == spell) then return recipe end
    end
    if not snapshot and E.FindRecipe then return E.FindRecipe(slug, spell) end
    return nil
end

function E.RequiredLevelingTool(slug, tool, start, snapshot)
    if type(tool) ~= "table" then return false end
    local itemID = tool.itemID or tool.item
    if tool.optional or (slug == "alchemy" and (itemID == 9149 or itemID == 13503)) then return false end
    start = tonumber(start) or (type(snapshot) == "table" and type(snapshot.professions) == "table" and snapshot.professions[slug] and snapshot.professions[slug].cur)
    if slug == "enchanting" and tool.tier and start then
        for _, higher in ipairs(professionTools("enchanting")) do
            if (higher.tier or 0) > tool.tier and not higher.optional then
                local recipe = planningToolRecipe(slug, higher.craftSpellID or higher.spell, snapshot)
                if recipe and (recipe.item or recipe.outputItemID) and type(recipe.learn) == "number" and recipe.learn <= start
                    and not recipe.clientPending and not recipe.clientUnavailable then
                    return false
                end
            end
        end
    end
    return true
end

function E.HasToolGoals(slug, opts)
    if not E.ToolPlanningEnabled(opts, slug) then return false end
    local target = tonumber(type(opts) == "table" and opts.target) or solverDefaultTarget()
    for _, tool in ipairs(professionTools(slug)) do
        if E.RequiredLevelingTool(slug, tool, type(opts) == "table" and opts.start, type(opts) == "table" and opts.snapshot) then
            local recipe = planningToolRecipe(slug, tool.craftSpellID or tool.spell, type(opts) == "table" and opts.snapshot)
            if not recipe or type(recipe.learn) ~= "number" or target > recipe.learn then return true end
        end
    end
    return false
end

local function baseLearningSource(recipe)
    if type(recipe) ~= "table" then return nil end
    if recipe.learnSource == "trainer" or recipe.trainerObserved then return "trainer" end
    local spell = recipe.spell or recipe.spellID or recipe[1]
    local d = E.ClientStore()
    local rt = type(d) == "table" and type(d.recipes) == "table" and d.recipes[spell] or nil
    if type(rt) == "table" and rt.trainerObserved then return "trainer" end
    local G = getGates()
    return (G and type(G.LearningSource) == "function" and G.LearningSource(spell)) or recipe.learnSource
end

function E.ResolveRecipe(seed, slug)
    if type(seed) ~= "table" then return nil end
    local r = copy(seed)
    r.profession = slug or r.profession
    r.spell = r.spell or r.spellID
    r.spellID = r.spell
    local d = E.ClientStore()
    local rtMap = (E.EnsureClientRuntime and E.EnsureClientRuntime()) or (type(d) == "table" and type(d.recipes) == "table" and d.recipes) or nil
    local rt = rtMap and r.spell and rtMap[r.spell] or nil
    local client = false
    if type(rt) == "table" then
        if materialsValid(rt.mats) and (#rt.mats > 0 or rt.learned or rt.validated or rt.trainerObserved) then
            r.mats = copy(rt.mats)
            r.materialSource = "client"
            client = true
        end
        if positiveInteger(rt.item) then r.item = rt.item; client = true end
        if positiveInteger(rt.count) then
            r.count = rt.count
            r.outputMin = rt.outputMin or rt.count
            r.outputMax = rt.outputMax or rt.count
            r.variableOutput = rt.variableOutput
            r.outputSource = "client"
            client = true
        end
        if rt.variableOutput then
            r.variableOutput = true
            if positiveInteger(rt.outputMin) and positiveInteger(rt.outputMax) and rt.outputMax >= rt.outputMin then
                r.count = rt.outputMin
                r.outputMin = rt.outputMin
                r.outputMax = rt.outputMax
                r.outputBasis = "minimum"
                r.outputConflict = nil
            elseif positiveInteger(r.count) then
                r.outputBasis = "reference"
            else
                r.outputConflict = true
            end
        end
        if rt.learn then r.learn = rt.learn; r.skillSource = "client" end
        if rt.cooldown ~= nil and (rt.cooldown or r.cooldown ~= true or rt.cooldownVerified) then
            r.cooldown = rt.cooldown
            r.cooldownUnknown = nil
        end
        if rt.unavailable == true or rt.available == false then r.clientUnavailable = true end
        if rt.available == true and not r.clientUnavailable then r.clientAvailable = true end
        if rt.trainerObserved then
            r.trainerObserved = true
            r.trainerAvailable = rt.trainerAvailable
            r.learnSource = "trainer"
            r.clientAvailable = true
            r.clientUnavailable = nil
        end
    end
    if type(d) == "table" then
        r.learningRequirements = copy(type(d.learningRequirements) == "table" and d.learningRequirements[r.spell] or nil)
        local roster = type(d.recipeRosters) == "table" and d.recipeRosters[r.profession] or nil
        if type(roster) == "table" and roster.complete and type(roster.ids) == "table" and not roster.ids[r.spell]
            and not (type(rt) == "table" and rt.trainerObserved) and E.Known(r.spell) ~= true then
            r.clientUnavailable = true
            r.clientAvailable = nil
        end
    end
    r.materialSource = r.materialSource or (materialsValid(r.mats) and "catalogue" or "unknown")
    r.outputSource = r.outputSource or ((positiveInteger(r.count) or not r.item) and "catalogue" or "unknown")
    r.outputMin = r.outputMin or r.count
    r.outputMax = r.outputMax or r.count
    r.clientPending = not materialsValid(r.mats) or (r.item and not positiveInteger(r.count)) or nil
    r.dataSource = client and "mixed" or "catalogue"
    r.skillSource = r.skillSource or "catalogue"
    r.key = r.profession and r.spell and (r.profession .. ":" .. r.spell) or r.key
    return r
end

function E.ThresholdsUnknown(r)
    return type(r) == "table" and r.thresholdsUnknown == true or false
end

function E.HasGainThresholds(r)
    return type(r) == "table" and not E.ThresholdsUnknown(r) and type(r.learn) == "number" and type(r.yellow) == "number"
        and type(r.green) == "number" and type(r.grey) == "number" and (r.orange == nil or type(r.orange) == "number")
end

function E.MaterialFactsUnknown(r)
    return type(r) == "table" and r.materialsUnknown == true or false
end

local function recipeSpell(row, kind)
    if type(row) ~= "table" then return nil end
    if kind == "enchants" then return row.spell or row.spellID or row[14] end
    return row.spell or row.spellID or row[1]
end

function E.DecodeRecipeRow(row, kind, spell)
    if type(row) ~= "table" then return nil end
    if kind == "rinfo" or kind == "ds" or row.spell or row.spellID then
        local r = copy(row)
        r.spell = spell or r.spell or r.spellID
        r.spellID = r.spell
        r.item = r.item or r.outputItemID or r.makes
        r.outputItemID = r.item
        r.formula = r.formula or r.formulaID
        r.learn = r.learn or r.learnedAt
        r.category = r.category or r.categoryKey
        if r.mats == nil and type(r.reagents) == "table" then
            local mats = {}
            for _, m in ipairs(r.reagents) do
                if type(m) == "table" then
                    local mid = m.itemID or m.id or m[1]
                    local mcnt = m.count or m.amount or m[2]
                    if positiveInteger(mid) and positiveInteger(mcnt) then
                        mats[#mats + 1] = { mid, mcnt }
                    end
                end
            end
            r.mats = mats
        end
        if r.count == nil then
            if r.outputCountMin ~= nil then
                r.count = tonumber(r.outputCountMin) or r.outputCountMin
            elseif r.outputMin ~= nil then
                r.count = tonumber(r.outputMin) or r.outputMin
            end
        end
        r.outputMin = r.outputMin or r.outputCountMin or r.count
        r.outputMax = r.outputMax or r.outputCountMax or r.outputMin
        if type(r.outputMin) == "number" and type(r.outputMax) == "number" and r.outputMax > r.outputMin then
            r.variableOutput = true
        end
        return r
    elseif kind == "enchants" then
        return { spell = row[14], item = row[15], count = 1, mats = row[9], learn = row[5], orange = row.orange, yellow = row[6], green = row[7], grey = row[8], source = row[10] }
    elseif kind == "crafted" then
        return { spell = row[1], item = row[2], count = row[3], mats = row[8], learn = row[4], orange = row.orange, yellow = row[5], green = row[6], grey = row[7], formula = tonumber(row[9]) }
    end
    local formula = row[13]
    return {
        spell = row[1], item = row[2], count = row[3], mats = row[12], learn = row[7],
        orange = row.orange, yellow = row[8], green = row[9], grey = row[10],
        source = row[14], formula = type(formula) == "table" and formula[1] or nil, category = row[4],
    }
end

function E.Normalize(row, slug, kind, spell)
    if type(row) ~= "table" or E.RecipeNIP(spell or recipeSpell(row, kind), row) then return nil end
    local r = E.DecodeRecipeRow(row, kind, spell)
    if not r or not positiveInteger(r.spell) then return nil end
    if not r.item and r.count == nil then r.count = 0 end
    if r.count == nil then r.count = 1 end
    r.profession = slug or r.profession
    r.thresholdsUnknown = E.ThresholdsUnknown(r) or nil
    r.catalogue = true
    r = E.ResolveRecipe(r, r.profession)
    r.materialsUnknown = E.MaterialFactsUnknown(r) or nil
    if r.materialsUnknown then r.clientPending = true end
    local verifyCooldown = r.cooldownVerificationRequired == true or r.cooldownVerificationRequired == 1
        or r.category == "Transmutes" or r.categoryKey == "transmutes" or r.spell == 18560
    if r.cooldown == nil and type(r.cooldownSeconds) == "number" and r.cooldownSeconds > 0 then
        r.cooldown = true
    end
    if r.cooldown == nil then
        local cs = _G.C_Spell
        local fn = (type(cs) == "table" and cs.GetSpellBaseCooldown) or _G.GetSpellBaseCooldown
        local ok, ms = false, nil
        if type(fn) == "function" then ok, ms = pcall(fn, r.spell) end
        if ok and type(ms) == "number" then
            r.cooldown = ms > 0
        elseif not verifyCooldown then
            r.cooldown = false
        end
    end
    local d = E.ClientStore()
    local rt = type(d) == "table" and type(d.recipes) == "table" and d.recipes[r.spell] or nil
    if verifyCooldown and not r.cooldown and not (type(rt) == "table" and rt.cooldownVerified) then
        r.cooldownUnknown = true
    end
    return r
end

local function baseFindRecipe(slug, spell)
    if not positiveInteger(spell) then return nil end
    if E.EnsureClientRuntime then E.EnsureClientRuntime() end
    if E.RecipeNIP(spell) then return nil end
    local DS = getDS()
    if not DS then return nil end
    if type(slug) == "string" and slug ~= "" and type(DS.Recipes) == "function" then
        local bucket = DS.Recipes(slug)
        local row = type(bucket) == "table" and type(bucket.recipes) == "table" and bucket.recipes[spell] or nil
        if type(row) == "table" then
            return E.Normalize(row, slug, "ds", spell)
        end
    end
    if type(DS.Recipe) == "function" then
        local row = DS.Recipe(spell)
        if type(row) == "table" and (slug == nil or row.profession == slug) then
            return E.Normalize(row, row.profession or slug, "ds", spell)
        end
    end
    return nil
end

local function baseLearningEligibility(recipe, snapshot, state)
    if type(recipe) ~= "table" then return false, "clientDataPending" end
    if E.RecipeNIP(recipe.spell or recipe.spellID or recipe[1], recipe) then
        return false, "catalogueFiltered", { status = "blocked" }
    end
    snapshot = snapshot and (snapshot.snapshot or snapshot)
    if recipe.clientUnavailable then return false, "clientUnavailable", { status = "blocked" } end
    local spell = recipe.spell or recipe.spellID or recipe[1]
    local key = recipe.key or (recipe.profession and (recipe.profession .. ":" .. tostring(spell)))
    local known = (state and state.learned) or (snapshot and snapshot.known)
    if (known and (known[key] or known[spell])) or (not known and E.Known(spell) == true) then
        return true, nil, { status = "learned" }
    end
    local requirement = recipe.learningRequirements
    local current = (state and state.skill and state.skill[recipe.profession])
        or (snapshot and snapshot.professions and snapshot.professions[recipe.profession] and snapshot.professions[recipe.profession].cur)
    if requirement then
        local level = (snapshot and snapshot.level) or (not snapshot and type(_G.UnitLevel) == "function" and _G.UnitLevel("player"))
        if type(requirement.level) == "number" and requirement.level > 0 then
            if type(level) ~= "number" then return false, "clientDataPending", { status = "unknown" } end
            if level < requirement.level then return false, "characterLevelRequired", { status = "blocked" } end
        end
        if type(requirement.skill) == "number" and requirement.skill > 0 then
            if type(current) ~= "number" then return false, "clientDataPending", { status = "unknown" } end
            if current < requirement.skill then return false, "skillRequired", { status = "blocked" } end
        end
    end
    local G = getGates()
    local ability = G and type(G.RequiredAbility) == "function" and G.RequiredAbility(spell) or (tonumber(recipe.requiredAbilityID) or 0)
    local abilities = (state and state.specializationAbilities) or {}
    local actual
    if snapshot then
        actual = snapshot.specializationAbilities or snapshot.abilities or {}
    else
        actual = G and type(G.Abilities) == "function" and G.Abilities() or {}
    end
    if ability > 0 and abilities[ability] ~= true and actual[ability] ~= true then
        if abilities[ability] == false or actual[ability] == false then
            return false, "specializationRequired", { status = "blocked", requiredAbility = ability, requiredAbilities = { ability } }
        end
        return true, nil, { status = "unknown", requiredAbility = ability, hasPending = true }
    end
    if G and type(G.HasPending) == "function" and G.HasPending(spell) then
        return true, nil, { status = "unknown", hasPending = true }
    end
    if recipe.trainerAvailable == true or requirement or (G and type(G.LearningSource) == "function" and G.LearningSource(spell)) then
        return true, nil, { status = "allowed" }
    end
    return true, nil, { status = "unknown" }
end

local function vendorQuote(o)
    return type(o) == "table" and o.unlimited == true and type(o.price) == "number"
        and o.price >= 0 and o.available ~= false and o.purchasable ~= false
        and not o.hasExtendedCost and (not o.currencyID or o.currencyID == 0)
end

function E.PreferredVendorOffers(offers, eligible)
    return offers or {}
end

function D.Build(rows)
    local byPrice = {}
    for _, row in ipairs(rows or {}) do
        local p, q = row[1], row[2]
        assert(type(p) == "number" and p > 0 and p < huge and p == p, "invalid unit price")
        assert(type(q) == "number" and q >= 0 and q < huge and q == floor(q), "invalid quantity")
        if q > 0 then byPrice[p] = (byPrice[p] or 0) + q end
    end
    local prices = {}
    for p in pairs(byPrice) do prices[#prices + 1] = p end
    table.sort(prices)
    local book = { prices = prices, quantity = {}, cost = {}, total = 0, totalCost = 0 }
    for i, p in ipairs(prices) do
        book.total = book.total + byPrice[p]
        book.totalCost = book.totalCost + p * byPrice[p]
        book.quantity[i] = book.total
        book.cost[i] = book.totalCost
    end
    return book
end

function D.Prefix(book, q)
    if type(q) ~= "number" or q ~= q or q ~= floor(q) then return nil end
    if q == 0 then return 0 end
    if q < 0 or q > book.total then return nil end
    local lo, hi = 1, #book.prices
    while lo < hi do
        local mid = floor((lo + hi) / 2)
        if book.quantity[mid] < q then lo = mid + 1 else hi = mid end
    end
    return (book.cost[lo - 1] or 0) + (q - (book.quantity[lo - 1] or 0)) * book.prices[lo]
end

function D.Cost(book, used, q)
    used = used or 0
    if type(used) ~= "number" or type(q) ~= "number" or q < 0 or q ~= floor(q) then return nil end
    local begin = D.Prefix(book, used)
    local finish = D.Prefix(book, used + q)
    if not begin or not finish then return nil end
    return finish - begin
end

function D.Quote(snapshot, id, used, q)
    local book = snapshot.auctionDepth and snapshot.auctionDepth[id]
    if book then
        return D.Cost(book, used, q)
    end
    return (snapshot.prices[id] or 0) * q
end

function D.Identity(entry)
    if not entry then return false end
    local hash = 0
    for _, row in ipairs(entry.levels or {}) do
        local text = string.format("%.17g:%d;", row[1], row[2])
        for i = 1, #text do hash = (hash * 131 + string.byte(text, i)) % 2147483647 end
    end
    return table.concat({ entry.marketKey or "", entry.observedAt or 0, entry.quantity or 0, hash }, ":")
end

function E.AuctionDepthChanged(result)
    local bridge = getAuctionBridge()
    for id, previous in pairs(result.auctionDepthInputs or {}) do
        local current = bridge and bridge.GetAuctionDepth and bridge.GetAuctionDepth(id)
        if previous ~= D.Identity(current) then return true end
    end
    return false
end

function E.VendorPricesChanged(result)
    return false
end

local raInit = getRouteAuto()
if type(raInit) == "table" then
    raInit.VendorQuotesChanged = E.VendorPricesChanged
    raInit.ValidateVendorQuotes = function(result)
        return result
    end
end

function E.MaterialPurchases(id, need, context, tick)
    need = max(0, ceil(tonumber(need) or 0))
    if need == 0 then return {}, 0, true end
    local offers, auction, supply = context.offers or {}, context.auction, context.supply
    local available, faction = context.available, context.faction
    local function auctionCost(n)
        if context.auctionCost then return context.auctionCost(n) or huge end
        return n * (auction or 0)
    end
    local limit = auction and min(need, max(0, floor(available or need))) or 0
    local byPack, reliable, maxPack = {}, {}, 1
    for _, offer in ipairs(offers) do
        local size = offer.quantity or offer.bundleSize or 1
        local price = offer.price ~= nil and offer.price or offer.priceCopper
        local side = offer.faction
        local valid = offer.unlimited == true and offer.available ~= false and offer.purchasable ~= false
            and not offer.priceOnly and not offer.hasExtendedCost and (not offer.currencyID or offer.currencyID == 0)
            and #(offer.currencies or {}) == 0 and #(offer.costItems or {}) == 0
            and (not side or not faction or side == faction or side == "N" or side == "Neutral" or side == "Both" or side == "AH")
            and type(price) == "number" and price >= 0 and price < huge
            and type(size) == "number" and size >= 1 and size < huge and size == floor(size)
        if valid then
            local old = byPack[size]
            local oldPrice = old and (old.price ~= nil and old.price or old.priceCopper)
            local uncertain = offer.estimated and not offer.reference
            if not old or price < oldPrice or (price == oldPrice and old.estimated and not old.reference and not uncertain) then
                byPack[size] = offer
            end
            local relOld = reliable[size]
            local relPrice = relOld and (relOld.price ~= nil and relOld.price or relOld.priceCopper)
            if not uncertain and (not relOld or price < relPrice) then reliable[size] = offer end
        end
    end
    if next(reliable) or (auction and limit >= need) then byPack = reliable end
    local sizes = {}
    for size in pairs(byPack) do sizes[#sizes + 1] = size; maxPack = max(maxPack, size) end
    table.sort(sizes)
    local costs, previous, chosen = { [0] = 0 }, {}, {}
    local maximum = #sizes > 0 and need + maxPack - 1 or 0
    for quantity = 1, maximum do
        if tick then tick() end
        for _, size in ipairs(sizes) do
            local before = quantity - size
            if before >= 0 and costs[before] then
                local bp = byPack[size]
                local bpPrice = bp.price ~= nil and bp.price or bp.priceCopper
                local cost = costs[before] + bpPrice
                if not costs[quantity] or cost < costs[quantity] - 1e-9 then
                    costs[quantity] = cost
                    previous[quantity] = before
                    chosen[quantity] = size
                end
            end
        end
    end
    local best, bestNPC, bestAH
    for quantity = 0, maximum do
        local rest = max(0, need - quantity)
        if costs[quantity] and (rest == 0 or (auction and rest <= limit)) then
            local cost = costs[quantity] + auctionCost(rest)
            if not best or cost < best - 1e-9 or (math.abs(cost - best) < 1e-9 and rest < bestAH) then
                best, bestNPC, bestAH = cost, quantity, rest
            end
        end
    end
    local function ahRow(count)
        return {
            id, count,
            id = id, count = count, need = count,
            cost = auctionCost(count), unit = count > 0 and auctionCost(count) / count or 0,
            source = "ah", vendor = false, availableCount = available, supplyRequired = count,
            supplyObserved = available ~= nil, supplyComplete = supply and supply.complete,
            supplyObservedAt = supply and supply.observedAt, supplySource = supply and supply.source,
            supplyMethod = supply and supply.method,
        }
    end
    if not best then
        local entry
        if auction then
            entry = ahRow(need)
        else
            entry = { id, need, id = id, count = need, need = need, cost = 0, unit = 0, unpriced = true }
        end
        entry.unavailable = true
        entry.costComplete = false
        if type(entry.cost) == "number" and entry.cost == huge then
            entry.cost = nil
            entry.unit = nil
            entry.unpriced = true
        end
        return { entry }, entry.cost, false, auction and "auctionSupplyLimited" or "materialUnavailable"
    end
    local list, counts = {}, {}
    local quantity = bestNPC
    while quantity > 0 do
        local size = chosen[quantity]
        counts[size] = (counts[size] or 0) + 1
        quantity = previous[quantity]
    end
    local complete, reason = true, nil
    for _, size in ipairs(sizes) do
        local packs = counts[size]
        if packs then
            local offer = byPack[size]
            local offerPrice = offer.price ~= nil and offer.price or offer.priceCopper
            local entry = {}
            for key, value in pairs(offer) do entry[key] = value end
            local count = packs * size
            entry[1], entry[2], entry.id, entry.count = id, count, id, count
            entry.need = min(need, count)
            entry.cost = packs * offerPrice
            entry.unit = offerPrice / size
            entry.bundleSize, entry.bundlePrice = size, offerPrice
            entry.quoteSource = offer.quoteSource or offer.source
            entry.source, entry.vendor = "vendor", true
            if offer.estimated and not offer.reference then
                complete = false
                reason = "vendorEstimate"
                entry.costComplete = false
            end
            list[#list + 1] = entry
        end
    end
    if bestAH > 0 then list[#list + 1] = ahRow(bestAH) end
    return list, best, complete, reason
end

local function formulaContext(context)
    context = context or {}
    return context.snapshot or context
end

if type(E.AllowLimitedFormulas) ~= "function" then
    function E.AllowLimitedFormulas(context, profession)
        return settingPermission(context, "allowLimitedFormulas", "autoBuyLimitedFormulas", profession)
    end
end

if type(E.AllowBindOnPickupFormulas) ~= "function" then
    function E.AllowBindOnPickupFormulas(context, profession)
        return settingPermission(context, "allowBindOnPickupFormulas", "autoAllowBindOnPickupFormulas", profession)
    end
end

if type(E.AllowCurrencyFormulas) ~= "function" then
    function E.AllowCurrencyFormulas(context, profession)
        return E.AllowBindOnPickupFormulas(context, profession)
            or settingPermission(context, "allowCurrencyFormulas", "autoAllowCurrencyFormulas", profession)
    end
end

if type(E.LimitedFormulaOffer) ~= "function" then
    function E.LimitedFormulaOffer(offer)
        if type(offer) ~= "table" then return false end
        if offer.unlimited == true or offer.maxStock == -1 then return false end
        if offer.limited == true or offer.stockStatus == "limited"
            or (type(offer.stock) == "number" and offer.stock >= 0)
            or (type(offer.maxStock) == "number" and offer.maxStock >= 0) then
            return true
        end
        if offer.stockUnknown or offer.stockStatus == "unknown" then return false end
        return offer.unlimited == false
    end
end

local function formulaStockRestricted(offer)
    return E.LimitedFormulaOffer(offer) or offer.stockUnknown == true or offer.stockStatus == "unknown"
        or (offer.unlimited ~= true and not (type(offer.stock) == "number" and offer.stock < 0))
end

local function recipeKnown(r, context)
    if context.professions and context.professions[r.profession] and context.professions[r.profession].unlearned then return false end
    if context.known then return context.known[r.key] == true or context.known[r.spell] == true end
    return E.Known(r.spell) == true
end

local function hasEntries(t) return type(t) == "table" and next(t) ~= nil end

local function questSource(source)
    if type(source) ~= "table" then return false end
    if source.questOnly or source.quest or hasEntries(source.quests) or source.type == "quest" or source.kind == "quest" then return true end
    for _, key in ipairs({ "skill", "notes", "description" }) do
        local value = source[key]
        if type(value) == "string" and (value:lower():find("quest", 1, true) or value:find("任务", 1, true) or value:find("任務", 1, true)) then
            return true
        end
    end
    return false
end

local function validSupply(entry, stamp, live)
    if type(entry) ~= "table" or type(entry.quantity) ~= "number" or entry.quantity < 0
        or entry.quantity == huge or entry.quantity ~= floor(entry.quantity)
        or entry.complete == false then return false end
    if entry.source == "auctionator-daily-maximum" or entry.source == "auctionator-update"
        or entry.source == "auctionator-history" then return false end
    if live or entry.source == "client-auction-results" then
        if entry.source ~= "client-auction-results" or entry.complete ~= true
            or type(entry.observedAt) ~= "number" or entry.observedAt <= 0 then return false end
        local bridge = getAuctionBridge()
        local forced = bridge and bridge.ForceExpiredActive and bridge.ForceExpiredActive()
        if not forced and stamp and (entry.observedAt > stamp or stamp - entry.observedAt > supplyMaxAge()) then return false end
    end
    return true
end

function E.ConsiderAuctionSupply(context)
    if type(context) == "table" and context.considerAuctionSupply ~= nil then return context.considerAuctionSupply == true end
    if type(context) == "table" and type(context.snapshot) == "table" and context.snapshot.considerAuctionSupply ~= nil then
        return context.snapshot.considerAuctionSupply == true
    end
    local slug = type(context) == "table" and (context.profession or context.slug) or nil
    return readSettingRaw("autoConsiderAuctionSupply", slug) == true
end

function E.AuctionSupplyOf(context, id)
    if context and not E.ConsiderAuctionSupply(context) then return nil end
    context = context and (context.snapshot or context)
    local entry
    if context and context.auctionSupply then
        entry = context.auctionSupply[id]
    elseif not context or not context.prices then
        local bridge = getAuctionBridge()
        if bridge and bridge.GetAuctionSupply then entry = bridge.GetAuctionSupply(id, true) end
    end
    local stamp = context and context.stamp or (not context and Now())
    if stamp == 0 then stamp = nil end
    if validSupply(entry, stamp, not context) then return entry end
    return nil
end

if type(E.FormulaAuctionSupplyOf) ~= "function" then
    function E.FormulaAuctionSupplyOf(context, id)
        context = context and (context.snapshot or context)
        local frozen = context and (context.prices ~= nil or context.known ~= nil or context.recipes ~= nil
            or context.byKey ~= nil or context.learningSourcesRequired ~= nil)
        local entry = context and context.auctionSupply and context.auctionSupply[id]
        if not entry and not frozen then
            local bridge = getAuctionBridge()
            if bridge and bridge.GetAuctionSupply then entry = bridge.GetAuctionSupply(id, true) end
        end
        local stamp = (context and context.stamp) or Now()
        if type(stamp) == "number" and stamp > 0 and validSupply(entry, stamp, true) then return entry end
        return nil
    end
end

local function quoteMetadata(context, id, field, method)
    if context and context[field] then return context[field][id] end
    if context and context.prices then return nil end
    local bridge = getAuctionBridge()
    if bridge and type(bridge[method]) == "function" then return bridge[method](id) end
    return nil
end

local supplyIdentityFields = { "quantity", "observedAt", "source", "complete", "ownerExcluded", "market", "batch", "schemaVersion", "marketKey", "observer" }
local function supplyIdentity(supply)
    if not supply then return false end
    local out = {}
    for _, key in ipairs(supplyIdentityFields) do out[key] = supply[key] end
    return out
end

function E.AuctionSupplyChanged(result)
    for id, previous in pairs(result.formulaAuctionSupplyInputs or {}) do
        local current = E.FormulaAuctionSupplyOf(nil, id)
        if (previous ~= false) ~= (current ~= nil) then return true end
        if current then
            for _, key in ipairs(supplyIdentityFields) do
                if key ~= "observedAt" and key ~= "batch" and key ~= "observer" and previous[key] ~= current[key] then return true end
            end
        end
    end
    if result.considerAuctionSupply == false then return false end
    for id, previous in pairs(result.auctionSupplyInputs or {}) do
        local current = E.AuctionSupplyOf(nil, id)
        if (previous ~= false) ~= (current ~= nil) then return true end
        if current then
            for _, key in ipairs(supplyIdentityFields) do
                if key ~= "observedAt" and key ~= "batch" and key ~= "observer" and previous[key] ~= current[key] then return true end
            end
        end
    end
    return false
end

function E.SummarizeFormulaSupply(result, context, tick)
    context = formulaContext(context)
    local inputs, needed = {}, {}
    for _, list in ipairs({ result.mats or {}, result.formulas or {} }) do
        for _, entry in ipairs(list) do
            if (entry.source == "ah" or entry.source == "auction") and not entry.known then
                local id = entry.id or entry[1]
                if id then needed[id] = (needed[id] or 0) + (entry.count or entry[2] or 1) end
            end
            if tick then tick() end
        end
    end
    local function candidate(id)
        if positiveInteger(id) and inputs[id] == nil then
            inputs[id] = supplyIdentity(E.FormulaAuctionSupplyOf(context, id))
        end
    end
    for _, recipe in ipairs(context.recipes or {}) do
        if not (context.known or {})[recipe.key] then
            candidate(recipe.formula or recipe.formulaID)
            for _, routes in ipairs({ recipe.learningRoutes or {}, recipe.learningInfo and recipe.learningInfo.routes or {} }) do
                for _, route in ipairs(routes) do
                    if route.kind == "item" then
                        candidate(route.teachingItemID or route.itemID)
                    end
                end
            end
        end
        if tick then tick() end
    end
    for _, entry in ipairs(result.formulas or {}) do
        if not entry.known then
            candidate(entry.id)
            if entry.source == "ah" or entry.source == "auction" then
                local supply = E.FormulaAuctionSupplyOf(context, entry.id)
                entry.considerAuctionSupply = true
                entry.supplyObserved = supply ~= nil
                entry.availableCount = supply and supply.quantity
                entry.supplyRequired = needed[entry.id]
                entry.supplyLimited = supply and needed[entry.id] > supply.quantity or nil
                entry.supplyComplete = supply ~= nil and not entry.supplyLimited
                entry.supplyStatus = supply and "verified" or "unknown"
                entry.supplyObservedAt = supply and supply.observedAt
                entry.supplySource = supply and supply.source
                entry.supplyOwnerExcluded = supply and supply.ownerExcluded
                entry.supplyMethod = supply and supply.method
            end
        end
        if tick then tick() end
    end
    result.formulaAuctionSupplyInputs = inputs
    return result
end

function E.SummarizeAuctionSupply(result, context, tick)
    E.SummarizeFormulaSupply(result, context, tick)
    result.considerAuctionSupply = E.ConsiderAuctionSupply(context)
    if not result.considerAuctionSupply then
        result.auctionSupplyUnknown = nil
        result.auctionSupplyObserved = nil
        result.supplyComplete = nil
        result.auctionSupplyInputs = {}
        result.auctionSupplyCandidates = {}
        result.auctionSupplyShortages = {}
        result.purchaseVerified = false
        result.auctionSupplyRevision = 3
        for _, entry in ipairs(result.mats or {}) do entry.considerAuctionSupply = false; if tick then tick() end end
        for _, entry in ipairs(result.formulas or {}) do
            entry.considerAuctionSupply = (entry.source == "ah" or entry.source == "auction") and not entry.known
            if tick then tick() end
        end
        return result
    end
    local seen, needed = {}, {}
    result.auctionSupplyUnknown = 0
    result.auctionSupplyObserved = false
    result.supplyComplete = true
    result.auctionSupplyShortages = {}
    result.auctionSupplyInputs = {}
    result.auctionSupplyCandidates = {}
    local candidates = {}
    local function candidate(id)
        if positiveInteger(id) and not candidates[id] and not (context and context.nonAuctionable or {})[id] then
            candidates[id] = true
            result.auctionSupplyCandidates[#result.auctionSupplyCandidates + 1] = id
        end
    end
    for _, r in ipairs(context and context.recipes or {}) do
        for _, m in ipairs(r.mats or {}) do candidate(m[1]) end
        if r.formula and not (context.known or {})[r.key] then candidate(r.formula) end
        if tick then tick() end
    end
    for id in pairs(context and context.prices or {}) do
        result.auctionSupplyInputs[id] = supplyIdentity(E.AuctionSupplyOf(context, id))
        if tick then tick() end
    end
    for id in pairs(context and context.auctionSupply or {}) do
        if result.auctionSupplyInputs[id] == nil then
            result.auctionSupplyInputs[id] = supplyIdentity(E.AuctionSupplyOf(context, id))
        end
        if tick then tick() end
    end
    for _, list in ipairs({ result.mats or {}, result.formulas or {} }) do
        for _, entry in ipairs(list) do
            local id = entry.id or entry[1]
            entry.considerAuctionSupply = true
            entry.priceObservedAt = quoteMetadata(context, id, "priceObservedAt", "GetAuctionPriceObservedAt")
            if (entry.source == "ah" or entry.source == "auction") and not entry.known then
                candidate(id)
                local supply = E.AuctionSupplyOf(context, id)
                result.auctionSupplyInputs[id] = supplyIdentity(supply)
                entry.supplyObserved = supply ~= nil
                entry.supplyStatus = supply and "verified" or (context and context.auctionSupplyStatus or {})[id] or "unknown"
                entry.supplyLimited = nil
                entry.supplyRequired = nil
                entry.supplyObservedAt = nil
                entry.supplySource = nil
                entry.supplyMethod = nil
                entry.supplyOwnerExcluded = nil
                entry.supplyObservedPrice = nil
                entry.supplyMarket = nil
                entry.supplyBatch = nil
                entry.supplySchemaVersion = nil
                entry.supplyHistoryQuantity = nil
                entry.supplyHistoryObservedAt = nil
                local history = quoteMetadata(context, id, "auctionSupplyHistory", "GetAuctionSupplyHistory")
                if type(history) == "table" and type(history.quantity) == "number" and history.quantity >= 0
                    and history.quantity < huge and history.quantity == floor(history.quantity) then
                    entry.supplyHistoryQuantity = history.quantity
                    entry.supplyHistoryObservedAt = history.observedAt
                end
                if supply then
                    entry.availableCount = supply.quantity
                    entry.supplyComplete = supply.complete ~= false
                    entry.supplyObservedAt = supply.observedAt
                    entry.supplySource = supply.source
                    entry.supplyOwnerExcluded = supply.ownerExcluded
                    entry.supplyMethod = supply.method
                    entry.supplyObservedPrice = supply.observedPrice or supply.market
                    entry.supplyMarket = supply.market
                    entry.supplyBatch = supply.batch
                    entry.supplySchemaVersion = supply.schemaVersion
                    result.auctionSupplyObserved = true
                    needed[id] = (needed[id] or 0) + (entry.count or entry[2] or 1)
                    entry.supplyLimited = needed[id] > supply.quantity or nil
                    result.supplyComplete = result.supplyComplete and supply.complete ~= false and not entry.supplyLimited
                else
                    entry.availableCount = nil
                    entry.supplyComplete = false
                    result.supplyComplete = false
                    if not seen[id] then result.auctionSupplyUnknown = result.auctionSupplyUnknown + 1 end
                end
                seen[id] = true
            end
            if tick then tick() end
        end
    end
    for _, list in ipairs({ result.mats or {}, result.formulas or {} }) do
        for _, entry in ipairs(list) do
            local id = entry.id or entry[1]
            if entry.supplyObserved and needed[id] then
                entry.supplyRequired = needed[id]
                entry.supplyLimited = needed[id] > (entry.availableCount or 0) or nil
            end
            if tick then tick() end
        end
    end
    local shortages = {}
    local function shortage(d)
        if d.code == "auctionSupplyLimited" and d.item and not shortages[d.item] then
            shortages[d.item] = true
            result.auctionSupplyShortages[#result.auctionSupplyShortages + 1] = copy(d)
        end
    end
    if result.targetReached ~= true then
        for _, d in ipairs(result.blockingDiagnostics or {}) do shortage(d); if tick then tick() end end
        if result.feasible == false then for _, d in ipairs(result.diagnostics or {}) do shortage(d); if tick then tick() end end end
    end
    result.supplyComplete = result.supplyComplete and #result.auctionSupplyShortages == 0
    result.purchaseVerified = result.targetReached == true and result.supplyComplete and result.costComplete ~= false
        and result.learningComplete ~= false and result.formulaComplete ~= false
    table.sort(result.auctionSupplyCandidates)
    result.auctionSupplyRevision = 3
    return result
end

local function npcDisplayName(npcID)
    local DS = getDS()
    if DS and type(DS.RawText) == "function" then
        local txt = DS.RawText("npc", npcID)
        if type(txt) == "string" and txt ~= "" then return txt end
    end
    return "#" .. tostring(npcID)
end

local function vendorOffersDirect(id, ctx)
    if not positiveInteger(id) then return {} end
    local DS = getDS()
    local Cond = getCond()
    if not DS or type(DS.VendorOffers) ~= "function" then return {} end
    local vo = DS.VendorOffers(id)
    if type(vo) ~= "table" or type(vo.offers) ~= "table" then return {} end
    local playerFaction = type(ctx) == "table" and ctx.faction and normalizeFaction(ctx.faction) or nil
    local out = {}
    for _, o in ipairs(vo.offers) do
        if type(o) == "table" then
            local npcID = tonumber(o.npcID or o.id)
            local ms = o.maxStock ~= nil and o.maxStock or o.stock
            if ms ~= 0 then
                local npc = positiveInteger(npcID) and type(DS.Npc) == "function" and DS.Npc(npcID) or nil
                local npcFaction = normalizeFaction(o.faction or (npc and npc.faction))
                local factionOK = (npcFaction == nil or npcFaction == "N" or playerFaction == nil or npcFaction == playerFaction)
                local npcAccessOK = true
                if npc and Cond then
                    if type(Cond.IsNpcAccessible) == "function" then
                        npcAccessOK = Cond.IsNpcAccessible(npc, ctx)
                    elseif type(npc.accessConditions) == "table" and #npc.accessConditions > 0 and type(Cond.IsMet) == "function" then
                        npcAccessOK = Cond.IsMet(npc.accessConditions, ctx)
                    end
                end
                local condOK = true
                if type(o.conditions) == "table" and #o.conditions > 0 and Cond and type(Cond.IsMet) == "function" then
                    condOK = Cond.IsMet(o.conditions, ctx)
                end
                if factionOK and npcAccessOK and condOK then
                    local bundle = tonumber(o.bundleSize or o.quantity) or 1
                    local currencies = copy(o.currencies or {})
                    local costItems = copy(o.costItems or {})
                    local hasExt = (#currencies > 0 or #costItems > 0 or o.hasExtendedCost == true)
                    local price = o.priceCopper ~= nil and o.priceCopper or o.price
                    out[#out + 1] = {
                        npcID = npcID,
                        itemID = id,
                        priceCopper = price,
                        price = price,
                        unitCopper = type(price) == "number" and (price / bundle) or nil,
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
                        hasExtendedCost = hasExt,
                        currencyID = (#currencies > 0 and (currencies[1].currencyID or currencies[1].id)) or 0,
                        currencyAmount = (#currencies > 0 and (currencies[1].amount or currencies[1].count)) or 0,
                        priceVerified = o.priceVerified == true,
                        priceUsable = type(price) == "number" and not hasExt,
                        faction = npcFaction or "N",
                        areaID = npc and type(npc.spawns) == "table" and type(npc.spawns[1]) == "table" and npc.spawns[1].areaID or nil,
                        conditions = copy(o.conditions or {}),
                        commonVendorCount = vo.commonVendorCount,
                    }
                end
            end
        end
    end
    return out
end

local function vendorOffersForItem(id, ctx)
    if not positiveInteger(id) then return {} end
    local sup = getSupply()
    if sup and type(sup.DisplayList) == "function" then
        local list = sup.DisplayList(id, ctx)
        return copy(list or {})
    end
    return vendorOffersDirect(id, ctx)
end

local function baseFormulaFor(r, context, auctionRemaining, purchaseSource)
    if type(r) ~= "table" then return nil end
    context = formulaContext(context)
    local id = tonumber(r.formula or r.formulaID)
    local known = recipeKnown(r, context)
    local sources = copy(r.source or {})
    sources.vendors = nil
    local quest = questSource(sources)
    if not id or id <= 0 then
        if not quest then return nil end
        id = nil
    end
    if E.LearningSource(r) == "trainer" then return nil end
    local entry = {
        id = id, count = 1, need = 1, spell = r.spell, profession = r.profession, recipeKey = r.key,
        known = known, sources = sources, recipe = r,
        recipes = { { profession = r.profession, spell = r.spell, key = r.key, source = sources } },
        questOnly = false,
        questAcquisition = quest or false,
        vendorOffers = {}, source = "unknown", usable = true,
    }
    local ah = id and context.prices and context.prices[id]
    if ah == nil and id and not context.prices then
        local ra = getRouteAuto()
        if ra and ra.AHPriceOf then ah = ra.AHPriceOf(id) end
    end
    local acquisition = r.selectedLearningRoute and r.selectedLearningRoute.acquisition
    local bound = (context.nonAuctionable and context.nonAuctionable[id]) or r.bindOnPickup == true
        or (acquisition and acquisition.nonAuctionable == true)
        or (not context.prices and id and E.NonAuctionableItem(id))
    entry.bindOnPickup = bound and true or nil
    if type(ah) == "number" and ah > 0 and ah < huge then entry.ahPrice = ah end
    local offers = id and context.formulaOffers and context.formulaOffers[id]
    if not offers and not context.prices and id then
        offers = vendorOffersForItem(id, context)
    end
    if not offers and id and context.offers then offers = context.offers[id] end
    for _, offer in ipairs(offers or {}) do
        local currency = tonumber(offer.currencyID or offer.cur) or 0
        if type(offer.npcID) == "number" and offer.npcID > 0 and not offer.priceOnly
            and currency == 0 and not offer.hasExtendedCost
            and #(offer.currencies or {}) == 0 and #(offer.costItems or {}) == 0 then
            entry.vendorOffers[#entry.vendorOffers + 1] = offer
        end
    end
    local vendors, seen = {}, {}
    for _, o in ipairs(entry.vendorOffers) do
        if o.npcID and not seen[o.npcID] then
            vendors[#vendors + 1] = { id = o.npcID, name = o.npcName or o.name or npcDisplayName(o.npcID), zone = o.zone }
            seen[o.npcID] = true
        end
    end
    sources.vendors = vendors
    local supply = id and E.FormulaAuctionSupplyOf(context, id)
    local ahAvailable = auctionRemaining or (supply and supply.quantity)
    local ahUsable = entry.ahPrice and supply and supply.quantity >= 1 and ahAvailable >= 1
    if supply then
        entry.availableCount = supply.quantity
        entry.supplyObserved = true
        entry.supplyComplete = supply.complete == true
        entry.supplyObservedAt = supply.observedAt
        entry.supplySource = supply.source
        entry.supplyOwnerExcluded = supply.ownerExcluded
        entry.supplyMethod = supply.method
    end
    local best, bestCost
    local allowLimited = E.AllowLimitedFormulas(context, r.profession)
    local function quoted(o)
        local factionOK = not o.faction or not context.faction or o.faction == context.faction or o.faction == "N" or o.faction == "Neutral" or o.faction == "AH" or o.faction == "Both"
        local quantity = o.quantity or o.bundleSize or 1
        local price = o.price ~= nil and o.price or o.priceCopper
        return factionOK
            and o.available ~= false and o.purchasable ~= false and o.priceUsable ~= false
            and type(price) == "number" and price >= 0 and positiveInteger(quantity)
    end
    local function purchasable(o)
        local quantity = o.quantity or o.bundleSize or 1
        return quoted(o) and not (not allowLimited and formulaStockRestricted(o))
            and (type(o.stock) ~= "number" or o.stock < 0 or o.stock >= quantity)
    end
    for _, o in ipairs(entry.vendorOffers) do
        if o.unlimited == true then
            entry.unlimited = true
        elseif E.LimitedFormulaOffer(o) then
            entry.limited = true
        else
            entry.stockUnknown = true
        end
        local limitedBlocked = not allowLimited and formulaStockRestricted(o)
        if limitedBlocked then entry.limitedVendorDisabled = true end
        if quoted(o) then
            local price = o.price ~= nil and o.price or o.priceCopper
            local unit = price / (o.quantity or o.bundleSize or 1)
            if not entry.vendorPrice or unit < entry.vendorPrice then entry.vendorPrice = unit end
        end
    end
    for _, o in ipairs(entry.vendorOffers) do
        if purchasable(o) then
            local cost = o.price ~= nil and o.price or o.priceCopper
            if not bestCost or cost < bestCost then best, bestCost = o, cost end
        end
    end
    if purchaseSource ~= "ah" and bestCost ~= nil and (not ahUsable or bestCost < entry.ahPrice
        or (bestCost == entry.ahPrice and not formulaStockRestricted(best))) then
        entry.source = "vendor"
        entry.cost = bestCost
        entry.offer = best
        entry.npcID = best.npcID
        entry.stock = best.stock
        entry.maxStock = best.maxStock
        entry.stockStatus = best.stockStatus
        local quantity = best.quantity or best.bundleSize or 1
        entry.bundleSize = positiveInteger(quantity) and quantity or 1
        entry.count = entry.bundleSize
        entry.availabilityUncertain = best.stockUnknown == true or best.stockStatus == "unknown"
            or (best.unlimited ~= true and type(best.stock) ~= "number") or nil
    elseif ahUsable then
        entry.source = "ah"
        entry.cost = entry.ahPrice
    elseif quest then
        entry.source = "quest"
        entry.usable = known
    end
    if known then entry.cost = 0; entry.usable = true end
    if not known and entry.cost == nil then entry.usable = false end
    entry.unpriced = not known and entry.cost == nil or nil
    entry.costComplete = known or (entry.cost ~= nil and not entry.availabilityUncertain) or false
    entry.sourceType = entry.source
    entry.totalCost = entry.cost
    entry.blocked = not entry.usable
    entry.vendor = entry.source == "vendor"
    entry.considerAuctionSupply = entry.source == "ah" and not known
    if entry.blocked then
        entry.reason = entry.ahPrice and not supply and "formulaAuctionSupplyUnknown"
            or entry.ahPrice and (supply.quantity < 1 or ahAvailable < 1) and "formulaAuctionSupplyInsufficient"
            or entry.limitedVendorDisabled and "limitedFormulaDisabled" or "formulaUnavailable"
    end
    return entry
end

function E.CollectFormulas(steps, slug, context)
    local snap = formulaContext(context)
    local list, byID = {}, {}
    local total, complete = 0, true
    for _, step in ipairs(steps or {}) do
        if not step.checkpoint and (step[4] or step.count or 0) > 0 then
            local profession = step.profession or slug
            local r = step.recipe or (snap.byKey and snap.byKey[profession .. ":" .. tostring(step[3] or step.spell)]) or E.FindRecipe(profession, step[3] or step.spell)
            local entry = r and E.FormulaFor(r, snap)
            if entry and not entry.known and not entry.automatic then
                local key = entry.id or entry.recipeKey or (profession .. ":" .. tostring(entry.spell))
                local old = byID[key]
                if old then
                    old.recipes[#old.recipes + 1] = entry.recipes[1]
                else
                    byID[key] = entry
                    list[#list + 1] = entry
                    total = total + (entry.cost or 0)
                    complete = complete and entry.costComplete and entry.usable
                end
            end
        end
    end
    table.sort(list, function(a, b) return (a.id or 0) < (b.id or 0) end)
    return list, total, complete
end

function E.Index(s, tick)
    local recipes = {}
    for _, r in ipairs(s.recipes or {}) do
        if not E.RecipeNIP(r.spell, r) and E.HasGainThresholds(r) and not E.MaterialFactsUnknown(r) then
            recipes[#recipes + 1] = r
        end
        if tick then tick() end
    end
    s.recipes = recipes
    s.byItem, s.byProfession, s.byKey = {}, {}, {}
    for _, r in ipairs(s.recipes) do
        if tick then tick() end
        r.key = r.key or (r.profession .. ":" .. r.spell)
        r.mats = r.mats or {}
        if not r.clientPending then
            r.count = r.count or 1
        end
        s.byKey[r.key] = r
        local p = s.byProfession[r.profession]
        if not p then p = {}; s.byProfession[r.profession] = p end
        p[#p + 1] = r
        if positiveInteger(r.item) and type(r.count) == "number" and r.count > 0 then
            local a = s.byItem[r.item]
            if not a then a = {}; s.byItem[r.item] = a end
            a[#a + 1] = r
        end
    end
    for _, field in ipairs({
        "professions", "known", "prices", "offers", "formulaOffers", "formulaItems", "auctionSupplyHistory",
        "priceObservedAt", "auctionSupplyStatus", "nonAuctionable", "vendorItems", "vendorSuppliers", "diagnostics",
        "toolGoals", "toolGoalsPending", "specializationGoals", "specializationAbilities", "retainedToolItems",
        "toolCraftOnlyItems",
    }) do
        s[field] = s[field] or {}
    end
    local supply = {}
    for id, entry in pairs(s.auctionSupply or {}) do
        if validSupply(entry, s.stamp) then
            supply[id] = entry
        else
            s.auctionSupplyStatus[id] = s.auctionSupplyStatus[id] or "incomplete"
        end
        if tick then tick() end
    end
    s.auctionSupply = supply
    for id, book in pairs(s.auctionDepth or {}) do
        if book.prices[1] then s.prices[id] = book.prices[1] end
        s.auctionSupply[id] = s.auctionSupply[id] or { quantity = book.total, complete = true, source = "observed" }
        s.auctionSupply[id].quantity = min(s.auctionSupply[id].quantity, book.total)
        s.considerAuctionSupply = true
        if tick then tick() end
    end
    for _, recipe in ipairs(s.recipes or {}) do
        if not (s.known or {})[recipe.key] then
            local item = recipe.formula or recipe.formulaID
            if positiveInteger(item) then s.formulaItems[item] = true end
            for _, routes in ipairs({ recipe.learningRoutes or {}, recipe.learningInfo and recipe.learningInfo.routes or {} }) do
                for _, route in ipairs(routes) do
                    local rItem = tonumber(route.teachingItemID or route.itemID)
                    if route.kind == "item" and positiveInteger(rItem) then
                        s.formulaItems[rItem] = true
                        if route.acquisition and route.acquisition.nonAuctionable == true then s.nonAuctionable[rItem] = true end
                    end
                end
            end
        end
    end
    s.inventory = {}
    s.trainingCosts, s.rankCosts, s.learningRequirements, s.rankRequirements = nil, nil, nil, nil
    s.stations, s.stationRequirements = nil, nil
    return s
end

function E.CaptureToolGoals(s, slug, opts)
    s.autoCraftTools = E.ToolPlanningEnabled(opts, slug)
    s.toolFingerprint = E.ToolFingerprint(slug, opts)
    s.toolGoals, s.toolGoalsPending = {}, {}
    s.retainedToolItems, s.toolCraftOnlyItems = s.retainedToolItems or {}, s.toolCraftOnlyItems or {}
    s.nonAuctionable = s.nonAuctionable or {}
    local G = getGates()
    local target = tonumber(type(opts) == "table" and opts.target) or solverDefaultTarget()
    for _, tool in ipairs(professionTools(slug)) do
        local itemID = tool.itemID or tool.item
        local spellID = tool.craftSpellID or tool.spell
        if tool.bindOnPickup and positiveInteger(itemID) then
            s.nonAuctionable[itemID] = true
            s.toolCraftOnlyItems[itemID] = true
        end
        if s.autoCraftTools and E.RequiredLevelingTool(slug, tool, type(opts) == "table" and opts.start, s) then
            local recipe = planningToolRecipe(slug, spellID, s)
            local owned = G and type(G.ToolOwned) == "function"
                and ((positiveInteger(itemID) and G.ToolOwned(itemID)) or (recipe and positiveInteger(recipe.item) and G.ToolOwned(recipe.item)))
            if owned then
                s.ownedToolItems = s.ownedToolItems or {}
                if positiveInteger(itemID) then s.ownedToolItems[itemID] = true end
            elseif recipe and positiveInteger(recipe.item) and type(recipe.learn) == "number" and not recipe.clientPending then
                if target > recipe.learn then
                    local goal = copy(tool)
                    goal.profession = slug
                    goal.item = recipe.item
                    goal.itemID = recipe.item
                    goal.spell = spellID
                    goal.craftSpellID = spellID
                    goal.minSkill = recipe.learn
                    goal.id = slug .. ":" .. recipe.item
                    s.toolGoals[#s.toolGoals + 1] = goal
                    s.retainedToolItems[goal.item] = 1
                    recipe.tool, recipe.toolItem = true, goal.item
                end
            else
                s.toolGoalsPending[#s.toolGoalsPending + 1] = { code = "toolFactsUnknown", profession = slug, spell = spellID }
            end
        end
    end
    return s
end

function E.CaptureSpecializations(s, opts, slug)
    local G = getGates()
    if not G or type(G.SpecializationContext) ~= "function" then return s end
    local specOpts = copy(opts or {})
    specOpts.profession, specOpts.faction, specOpts.level = slug, s.faction, s.level
    specOpts.snapshot = s
    local spec = G.SpecializationContext(specOpts)
    s.targetProfession, s.engineeringSpecialization = slug, spec.choice
    s.specializationContext, s.specializationAbilities = spec, spec.abilities
    s.specializationFingerprint = spec.fingerprint
    s.specializationGoals = {}
    for _, goal in ipairs(spec.goals or {}) do
        s.specializationGoals[#s.specializationGoals + 1] = copy(goal)
    end
    return s
end

local function addRecipe(s, slug, row, kind, spell)
    local r = E.Normalize(row, slug, kind, spell)
    if not r or not E.HasGainThresholds(r) or E.MaterialFactsUnknown(r) or (r.grey < r.learn and not r.knownAtCurrentSkill)
        or not materialsValid(r.mats) then return end
    if s.byKey[r.key] then return end
    s.recipes[#s.recipes + 1] = r
    s.byKey[r.key] = r
    s.known[r.key] = not (s.professions[slug] and s.professions[slug].unlearned) and (E.Known(r.spell) == true) or false
    if E.AttachLearningInfo then E.AttachLearningInfo(r, s.known[r.key]) end
end

function E.NonAuctionableItem(id)
    if not positiveInteger(id) then return false end
    local DS = getDS()
    local item = DS and type(DS.Item) == "function" and DS.Item(id) or nil
    if type(item) == "table" then
        if item.nonAuctionable == true or item.bindType == 1 or item.bindType == 4 then return true end
        if item.nonAuctionable == false or item.bindType ~= nil then return false end
    end
    local ci = _G.C_Item
    local fn = (type(ci) == "table" and ci.GetItemInfo) or _G.GetItemInfo
    if type(fn) ~= "function" then return false end
    local fields = { pcall(fn, id) }
    return fields[1] and (fields[15] == 1 or fields[15] == 4) or false
end

local bagRevision = 0
local bagChecks = setmetatable({}, { __mode = "k" })

function E.BagInventoryRevision() return bagRevision end

local function bagCount(id)
    local xp = getExecution()
    if xp and type(xp.BagCount) == "function" then return xp.BagCount(id) end
    local ci = _G.C_Item
    local fn = (type(ci) == "table" and ci.GetItemCount) or _G.GetItemCount
    if type(fn) == "function" then
        local ok, n = pcall(fn, id, false, false, false)
        if ok and type(n) == "number" and n >= 0 and n < huge and n == floor(n) then return n end
    end
    return nil
end

function E.BagInventoryFingerprint(inventory)
    local ids, parts = {}, {}
    for id in pairs(inventory) do ids[#ids + 1] = id end
    table.sort(ids)
    for _, id in ipairs(ids) do parts[#parts + 1] = id .. ":" .. inventory[id] end
    return table.concat(parts, ";")
end

function E.CaptureBagInventory(s, opts, tick)
    if not opts.useBagMaterials or opts.procurementDemands or opts.scheme == "fixed" or opts.scheme == "fishing"
        or opts.profession == "first-aid" or opts.profession == "poisons" then return end
    local items = {}
    for _, r in ipairs(s.recipes or {}) do for _, m in ipairs(r.mats or {}) do items[m[1]] = true end end
    for _, goal in ipairs(s.toolGoals or {}) do if goal.item then items[goal.item] = true end end
    for _, goal in ipairs(s.specializationGoals or {}) do for _, m in ipairs(goal.inputs or {}) do items[m[1]] = true end end
    local ess = getEssences()
    if s.essenceConversions and ess and type(ess.ExpandItems) == "function" then ess.ExpandItems(items) end
    local supplied = opts.bagInventory or s.bagInventory
    local ids = {}
    for id in pairs(items) do ids[#ids + 1] = id end
    table.sort(ids)
    if supplied then
        for id in pairs(supplied) do
            if not positiveInteger(id) then s.bagInventoryUnknown = true; return end
            if not items[id] then ids[#ids + 1] = id; items[id] = true end
        end
    end
    table.sort(ids)
    for _ = 1, 3 do
        local revision = bagRevision
        local inventory = {}
        for _, id in ipairs(ids) do
            local n
            if supplied then n = supplied[id] or 0 else n = bagCount(id) end
            if type(n) ~= "number" or n < 0 or n >= huge or n ~= floor(n) then s.bagInventoryUnknown = true; return end
            inventory[id] = n
            tick()
        end
        if supplied or revision == bagRevision then
            s.bagInventory = inventory
            s.bagInventoryVersion = 1
            s.bagInventoryStamp = opts.bagInventoryStamp or s.bagInventoryStamp or Now()
            s.bagInventoryFingerprint = E.BagInventoryFingerprint(inventory)
            s.bagInventoryUnknown = nil
            s.bagMaterialQuotes = {
                prices = copy(s.prices or {}),
                offers = copy(s.offers or {}),
                auctionSupply = copy(s.auctionSupply or {}),
                auctionDepth = copy(s.auctionDepth or {}),
                nonAuctionable = copy(s.nonAuctionable or {}),
                faction = s.faction,
                considerAuctionSupply = s.considerAuctionSupply,
            }
            return
        end
        tick()
    end
    s.bagInventoryUnknown = true
end

function E.BagInventoryChanged(result)
    if not result.useBagMaterials then return false, false end
    local previous = bagChecks[result]
    if previous and previous.revision == bagRevision and previous.inventory == result.bagInventory then
        return previous.changed, previous.unknown
    end
    local changed, unknown = false, false
    for id, n in pairs(result.bagInventory or {}) do
        local current = bagCount(id)
        if current == nil then unknown = true elseif current ~= n then changed = true end
    end
    bagChecks[result] = { revision = bagRevision, inventory = result.bagInventory, changed = changed, unknown = unknown }
    return changed, unknown
end

if type(_G.CreateFrame) == "function" then
    local ok, bagEvents = pcall(_G.CreateFrame, "Frame")
    if ok and type(bagEvents) == "table" then
        bagEvents:RegisterEvent("BAG_UPDATE_DELAYED")
        bagEvents:RegisterEvent("PLAYER_ENTERING_WORLD")
        bagEvents:SetScript("OnEvent", function() bagRevision = bagRevision + 1 end)
    end
end

local function overlayContextFacts(s, opts)
    local qSrc = opts.completedQuests or opts.quests
    if type(qSrc) == "table" then
        s.completedQuests = s.completedQuests or {}
        for k, v in pairs(qSrc) do s.completedQuests[k] = v end
    end
    if type(opts.reputations) == "table" then
        s.reputations = s.reputations or {}
        for k, v in pairs(opts.reputations) do s.reputations[k] = v end
    end
    local iSrc = opts.ownedSourceItems or opts.items
    if type(iSrc) == "table" then
        s.ownedSourceItems = s.ownedSourceItems or {}
        for k, v in pairs(iSrc) do s.ownedSourceItems[k] = v end
    end
    local aSrc = opts.learningAbilities or opts.abilities
    if type(aSrc) == "table" then
        s.learningAbilities = s.learningAbilities or {}
        for k, v in pairs(aSrc) do s.learningAbilities[k] = v end
    end
    if type(opts.ownedTeachingItems) == "table" then
        s.ownedTeachingItems = s.ownedTeachingItems or {}
        for k, v in pairs(opts.ownedTeachingItems) do s.ownedTeachingItems[k] = v end
    end
end

local function mergeSpecializationAbilities(s)
    if type(s) == "table" and type(s.specializationAbilities) == "table" and type(s.learningAbilities) == "table" then
        for k, v in pairs(s.specializationAbilities) do
            if s.learningAbilities[k] == nil then s.learningAbilities[k] = v end
        end
    end
end

local function baseCapture(slug, opts, tick)
    opts, tick = shallow(opts or {}), tick or function() end
    opts.profession = slug
    opts.noFormula, opts.learnedOnly, opts.allowUnknownLearning = nil, nil, nil
    opts.considerAuctionSupply = E.ConsiderAuctionSupply(opts)
    local ess = getEssences()
    local rec = getRecovery()
    local gates = getGates()
    if opts.snapshot then
        local s = copy(opts.snapshot, tick)
        s.considerAuctionSupply = opts.considerAuctionSupply
        s.noFormula, s.learnedOnly, s.allowUnknownLearning = nil, nil, nil
        s.stamp = s.stamp or Now()
        if s.playerLevel == nil and s.level ~= nil then s.playerLevel = s.level end
        s.professions, s.routeContext = E.RouteProfessions(slug, opts, opts.professions or s.professions or {})
        if slug ~= "__purchase" and not opts.allowSecondaryLeveling then
            local recipes = {}
            for _, recipe in ipairs(s.recipes or {}) do
                if recipe.profession == slug then recipes[#recipes + 1] = recipe end
                tick()
            end
            s.recipes = recipes
        end
        s.allowLimitedFormulas = E.AllowLimitedFormulas(opts)
        s.allowBindOnPickupFormulas = E.AllowBindOnPickupFormulas(opts)
        s.allowCurrencyFormulas = E.AllowCurrencyFormulas(opts)
        if s.coverageComplete == nil then s.coverageComplete = false end
        s.essenceConversions = ess and ess.Enabled and ess.Enabled(slug, opts, s) or false
        if s.toolGoals == nil then E.CaptureToolGoals(s, slug, opts) end
        if s.specializationContext == nil and gates then E.CaptureSpecializations(s, opts, slug) end
        mergeSpecializationAbilities(s)
        s = E.Index(s, tick)
        E.CaptureBagInventory(s, opts, tick)
        if rec and rec.Capture then rec.Capture(s, opts, tick) end
        return s
    end
    if E.EnsureClientRuntime then E.EnsureClientRuntime() end
    local professions, context = E.RouteProfessions(slug, opts, opts.professions or E.Professions())
    local s = {
        recipes = {}, byKey = {}, known = {}, prices = {}, offers = {}, formulaOffers = {},
        auctionSupply = {}, auctionSupplyHistory = {}, auctionSupplyStatus = {},
        priceObservedAt = {}, vendorItems = {}, vendorSuppliers = {}, nonAuctionable = {},
        coverageComplete = false,
        professions = copy(professions),
        routeContext = context,
        stamp = Now(),
        character = E.CharacterKey(),
        allowLimitedFormulas = E.AllowLimitedFormulas(opts),
        allowBindOnPickupFormulas = E.AllowBindOnPickupFormulas(opts),
        allowCurrencyFormulas = E.AllowCurrencyFormulas(opts),
        considerAuctionSupply = opts.considerAuctionSupply,
    }
    if opts.level ~= nil then
        s.level = opts.level
    elseif type(_G.UnitLevel) == "function" then
        local ok, lv = pcall(_G.UnitLevel, "player")
        if ok then s.level = lv end
    end
    s.playerLevel = s.level
    if opts.faction ~= nil then
        s.faction = normalizeFaction(opts.faction)
    elseif type(_G.UnitFactionGroup) == "function" then
        local ok, f = pcall(_G.UnitFactionGroup, "player")
        if ok then s.faction = normalizeFaction(f) end
    end
    if opts.classID ~= nil then
        s.classID = opts.classID
    elseif type(_G.UnitClass) == "function" then
        local ok, _, _, id = pcall(_G.UnitClass, "player")
        if ok then s.classID = id end
    end
    if opts.raceID ~= nil then
        s.raceID = opts.raceID
    elseif type(_G.UnitRace) == "function" then
        local ok, _, _, id = pcall(_G.UnitRace, "player")
        if ok then s.raceID = id end
    end
    overlayContextFacts(s, opts)
    if context.requiresPartner and not context.partnerValid then return E.Index(s, tick) end
    local loadList, seen = { slug }, { [slug] = true }
    for p, info in pairs(professions) do
        if not seen[p] and isPrimarySlug(p) and (not info.unlearned or p == context.partner) then
            loadList[#loadList + 1] = p
            seen[p] = true
        end
    end
    table.sort(loadList)
    local DS = getDS()
    for _, p in ipairs(loadList) do
        if E.IndexClientProfession then E.IndexClientProfession(p) end
        local bucket = DS and type(DS.Recipes) == "function" and DS.Recipes(p) or nil
        local recMap = type(bucket) == "table" and type(bucket.recipes) == "table" and bucket.recipes or nil
        if recMap then
            local spellIDs = {}
            for spellID in pairs(recMap) do
                if positiveInteger(spellID) then spellIDs[#spellIDs + 1] = spellID end
            end
            table.sort(spellIDs)
            for _, spellID in ipairs(spellIDs) do
                if E.ReadRecipe then E.ReadRecipe(spellID) end
                addRecipe(s, p, recMap[spellID], "ds", spellID)
                tick()
            end
        end
    end
    E.CaptureSpecializations(s, opts, slug)
    E.CaptureToolGoals(s, slug, opts)
    if E.CaptureLearningFacts then E.CaptureLearningFacts(s, tick) end
    overlayContextFacts(s, opts)
    mergeSpecializationAbilities(s)
    local items, materials = {}, {}
    s.formulaItems = {}
    for _, r in ipairs(s.recipes) do
        if positiveInteger(r.item) then items[r.item] = true end
        if r.formula and not s.known[r.key] and E.LearningSource(r) ~= "trainer" then
            items[r.formula] = true
            s.formulaItems[r.formula] = true
        end
        if not s.known[r.key] then
            for _, routes in ipairs({ r.learningRoutes or {}, r.learningInfo and r.learningInfo.routes or {} }) do
                for _, route in ipairs(routes) do
                    local item = tonumber(route.teachingItemID or route.itemID)
                    if route.kind == "item" and positiveInteger(item) then
                        items[item] = true
                        s.formulaItems[item] = true
                        if route.acquisition and route.acquisition.nonAuctionable == true then s.nonAuctionable[item] = true end
                    end
                end
            end
        end
        for _, m in ipairs(r.mats) do items[m[1]] = true; materials[m[1]] = true end
        tick()
    end
    for _, goal in ipairs(s.toolGoals or {}) do if goal.item then items[goal.item] = true end end
    for _, goal in ipairs(s.specializationGoals or {}) do for _, m in ipairs(goal.inputs or {}) do items[m[1]] = true end end
    s.essenceConversions = ess and ess.Enabled and ess.Enabled(slug, opts, s) or false
    if s.essenceConversions and ess.ExpandItems then ess.ExpandItems(items) end
    local ra, bridge = getRouteAuto(), getAuctionBridge()
    local hasQuestFacts = opts.strict == true or type(opts.completedQuests or opts.quests) == "table"
    local hasItemFacts = opts.strict == true or type(opts.ownedSourceItems or opts.items) == "table"
    local hasRepFacts = opts.strict == true or type(opts.reputations) == "table"
    local hasAbilityFacts = opts.strict == true or type(opts.learningAbilities or opts.abilities) == "table"
    local vendorAbilities
    if hasAbilityFacts then
        if type(s.specializationAbilities) == "table" and type(s.learningAbilities) == "table" then
            vendorAbilities = {}
            for k, v in pairs(s.specializationAbilities) do vendorAbilities[k] = v end
            for k, v in pairs(s.learningAbilities) do vendorAbilities[k] = v end
        else
            vendorAbilities = s.learningAbilities or s.specializationAbilities
        end
    end
    local vendorContext = {
        character = s.character,
        faction = s.faction,
        level = s.level,
        classID = s.classID,
        raceID = s.raceID,
        professions = s.professions,
        quests = hasQuestFacts and s.completedQuests or nil,
        completedQuests = hasQuestFacts and s.completedQuests or nil,
        items = hasItemFacts and s.ownedSourceItems or nil,
        ownedSourceItems = hasItemFacts and s.ownedSourceItems or nil,
        reputations = hasRepFacts and s.reputations or nil,
        abilities = vendorAbilities,
        strict = opts.strict,
        learningSourcesRequired = s.learningSourcesRequired,
    }
    s.auctionPriceInputs = {}
    s.vendorPriceInputs = {}
    s.auctionDepth = {}
    s.auctionDepthInputs = {}
    for id in pairs(items) do
        if E.NonAuctionableItem(id) then s.nonAuctionable[id] = true end
        local price = ra and ra.AHPriceOf and ra.AHPriceOf(id)
        if price == nil and bridge and type(bridge.GetAuctionSupply) == "function" then
            local sup = bridge.GetAuctionSupply(id)
            if type(sup) == "table" and type(sup.quantity) == "number" and sup.quantity > 0
                and type(sup.market) == "number" and sup.market > 0 then
                price = sup.market
            end
        end
        s.auctionPriceInputs[id] = type(price) == "number" and price > 0 and price or false
        if type(price) == "number" and price > 0 then s.prices[id] = price end
        if materials[id] and not s.formulaItems[id] then
            local depth = bridge and bridge.GetAuctionDepth and bridge.GetAuctionDepth(id)
            s.auctionDepthInputs[id] = D.Identity(depth)
            if depth then s.auctionDepth[id] = D.Build(depth.levels) end
        end
        local offers = vendorOffersForItem(id, vendorContext)
        s.offers[id] = offers
        s.vendorPriceInputs[id] = false
        for _, offer in ipairs(offers) do if vendorQuote(offer) then s.vendorItems[id] = true; break end end
        local supply = E.AuctionSupplyOf(nil, id)
        if supply then s.auctionSupply[id] = copy(supply) end
        s.auctionSupplyStatus[id] = bridge and bridge.GetAuctionSupplyStatus and bridge.GetAuctionSupplyStatus(id) or "unknown"
        if bridge and bridge.GetAuctionSupplyHistory then s.auctionSupplyHistory[id] = copy(bridge.GetAuctionSupplyHistory(id)) end
        if bridge and bridge.GetAuctionPriceObservedAt then s.priceObservedAt[id] = bridge.GetAuctionPriceObservedAt(id) end
        tick()
    end
    for _, r in ipairs(s.recipes) do
        if r.formula and E.LearningSource(r) ~= "trainer" and not s.formulaOffers[r.formula] then
            s.formulaOffers[r.formula] = vendorOffersForItem(r.formula, vendorContext)
        end
        if not s.known[r.key] then
            for _, routes in ipairs({ r.learningRoutes or {}, r.learningInfo and r.learningInfo.routes or {} }) do
                for _, route in ipairs(routes) do
                    local item = tonumber(route.teachingItemID or route.itemID)
                    if route.kind == "item" and positiveInteger(item) and not s.formulaOffers[item] then
                        s.formulaOffers[item] = vendorOffersForItem(item, vendorContext)
                    end
                end
            end
        end
        tick()
    end
    s = E.Index(s, tick)
    E.CaptureBagInventory(s, opts, tick)
    if rec and rec.Capture then rec.Capture(s, opts, tick) end
    return s
end

local learningLoaded = type(E.SelectLearningRoute) == "function"
if not learningLoaded then
    E.LearningSource = baseLearningSource
    E.LearningEligibility = baseLearningEligibility
    E.RecipeSpecializationAllowed = baseLearningEligibility
    E.RouteRecipeEligibility = baseLearningEligibility
    E.FormulaFor = baseFormulaFor
    E.FindRecipe = baseFindRecipe
    E.Capture = baseCapture
else
    E.FindRecipe = function(slug, spell)
        local r = baseFindRecipe(slug, spell)
        if type(r) == "table" and type(E.AttachLearningInfo) == "function" then
            E.AttachLearningInfo(r, E.Known(spell) == true)
        end
        return r
    end
    E.Capture = function(slug, opts, tick)
        local snapshot = baseCapture(slug, opts, tick)
        if snapshot and not (type(opts) == "table" and opts.snapshot) and not snapshot.learningDataFingerprint
            and type(E.CaptureLearningFacts) == "function" then
            E.CaptureLearningFacts(snapshot, tick)
        end
        return snapshot
    end
end
