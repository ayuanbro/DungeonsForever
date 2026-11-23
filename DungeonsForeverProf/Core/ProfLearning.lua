local _, ns = ...
if type(ns) ~= "table" then ns = _G.DF_NS or {} end
local gns = _G.DF_NS

local E = ns.ProfEconomy or (type(gns) == "table" and gns.ProfEconomy) or {}
ns.ProfEconomy = E
if type(gns) == "table" and gns ~= ns then
    gns.ProfEconomy = E
end

local floor = math.floor

local function getDS()
    return ns.ProfDataStore or (type(gns) == "table" and gns.ProfDataStore) or nil
end

local function getCond()
    return ns.ProfConditions or (type(gns) == "table" and gns.ProfConditions) or nil
end

local function getAPI()
    return ns.ProfAPI or (type(gns) == "table" and gns.ProfAPI) or nil
end

local function getGates()
    return ns.ProfGates or (type(gns) == "table" and gns.ProfGates) or nil
end

local function getSupply()
    return ns.ProfSupply or (type(gns) == "table" and gns.ProfSupply) or nil
end

local function getDB()
    return ns.ProfDB or (type(gns) == "table" and gns.ProfDB) or nil
end

local function getProfCfg()
    return ns.ProfessionsConfig or (type(gns) == "table" and gns.ProfessionsConfig) or nil
end

local function getRouteAuto()
    return ns.ProfRouteAuto or (type(gns) == "table" and gns.ProfRouteAuto) or nil
end

local function getModule()
    return ns.ProfModule or (type(gns) == "table" and gns.ProfModule) or nil
end

local function shallow(t)
    local o = {}
    for k, v in pairs(t or {}) do o[k] = v end
    return o
end

local function positiveInteger(v)
    return type(v) == "number" and v > 0 and v == floor(v)
end

local function spellOf(recipe)
    return type(recipe) == "table" and (recipe.spell or recipe.spellID or recipe[1]) or nil
end

local function normalizeFaction(value)
    if value == "Alliance" or value == "a" or value == "A" then return "A" end
    if value == "Horde" or value == "h" or value == "H" then return "H" end
    if value == "Neutral" or value == "n" or value == "N" or value == "Both" or value == "B" then return "N" end
    return value
end

local function playerFactionOf(snapshot, pricingContext)
    local raw = (type(snapshot) == "table" and snapshot.faction) or (type(pricingContext) == "table" and pricingContext.faction)
    if raw == nil and not snapshot and type(_G.UnitFactionGroup) == "function" then
        local ok, f = pcall(_G.UnitFactionGroup, "player")
        if ok then raw = f end
    end
    return normalizeFaction(raw)
end

local function identity(snapshot, key, fn)
    if type(snapshot) == "table" then return snapshot[key] end
    if type(fn) == "function" then
        local ok, _, _, id = pcall(fn, "player")
        if ok then return id end
    end
    return nil
end

if type(E.Copy) ~= "function" then
    local function copy(value, tick, seen, overrides)
        if type(value) ~= "table" then return value end
        seen = seen or {}
        if seen[value] then return seen[value] end
        local out, count = {}, 0
        seen[value] = out
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
    E.Copy = function(value, tick, overrides)
        return type(value) == "table" and copy(value, tick, nil, overrides) or {}
    end
end

if type(E.CharacterKey) ~= "function" then
    function E.CharacterKey()
        local db = getDB()
        if type(db) == "table" and type(db.CharacterKey) == "function" then return db.CharacterKey() end
        if type(_G.UnitGUID) == "function" then
            local ok, guid = pcall(_G.UnitGUID, "player")
            if ok and type(guid) == "string" and guid ~= "" then return guid end
        end
        return "offline:player"
    end
end

if type(E.ClientStore) ~= "function" then
    function E.ClientStore()
        local db = getDB()
        if type(db) == "table" and type(db.CharacterStore) == "function" then
            local store = db.CharacterStore("client")
            return store
        end
        return {}
    end
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
        return type(cfg) == "table" and type(cfg.SKILL_LINE_TO_SLUG) == "table" and cfg.SKILL_LINE_TO_SLUG[id] or nil
    end
end

if type(E.Professions) ~= "function" then
    function E.Professions()
        local API = getAPI()
        if API and type(API.ProfLearned) == "function" then
            return API.ProfLearned()
        end
        return {}
    end
end

if type(E.Known) ~= "function" then
    function E.Known(spell)
        if not positiveInteger(spell) then return nil end
        local rt = ns.ProfRecipeRuntime or (type(gns) == "table" and gns.ProfRecipeRuntime)
        if type(rt) == "table" and type(rt[spell]) == "table" and rt[spell].learned == true then return true end
        local Cond = getCond()
        if Cond and type(Cond.Evaluate) == "function" then
            return Cond.Evaluate({ kind = "ability", spellID = spell })
        end
        return nil
    end
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
    local settings = ns.ProfSettings or (type(gns) == "table" and gns.ProfSettings) or getDB()
    if type(settings) == "table" and type(settings.SettingRaw) == "function" then
        return settings.SettingRaw(setting, slug) == true
    end
    local view = getModule()
    if view and type(view.SettingRaw) == "function" then return view.SettingRaw(setting, slug) == true end
    local dbFn = getDB()
    if dbFn then
        local db = dbFn()
        return type(db) == "table" and type(db.prof) == "table" and db.prof[setting] == true or false
    end
    return false
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

if type(E.FormulaAuctionSupplyOf) ~= "function" then
    function E.FormulaAuctionSupplyOf(context, id)
        if type(context) ~= "table" or type(id) ~= "number" then return nil end
        local supply = type(context.auctionSupply) == "table" and context.auctionSupply[id] or nil
        if type(supply) ~= "table" or type(supply.quantity) ~= "number" then return nil end
        return supply
    end
end

local wrappedFns = setmetatable({}, { __mode = "k" })
local hookedGateFns = setmetatable({}, { __mode = "k" })
local baseFns = {}
local wrappedSlots = {}

local function ensureHooks()
    for slot, fn in pairs(wrappedSlots) do
        local cur = E[slot]
        if cur ~= fn then
            if cur ~= nil and not wrappedFns[cur] then
                baseFns[slot] = cur
            end
            E[slot] = fn
        end
    end
    local gates = getGates()
    if type(gates) == "table" and type(gates.SpecFingerprint) == "function" and not hookedGateFns[gates.SpecFingerprint] then
        local orig = gates.SpecFingerprint
        local wrapped = function(...)
            return tostring(orig(...)) .. ":learning:" .. E.LearningPolicyFingerprint()
        end
        hookedGateFns[wrapped] = true
        gates.SpecFingerprint = wrapped
    end
    local API = getAPI()
    if type(API) == "table" and type(API.RegisterDelegate) == "function" then
        API.RegisterDelegate("learning", {
            Refresh = E.RefreshLearningObservations,
            RefreshLearningObservations = E.RefreshLearningObservations,
            SelectLearningRoute = E.SelectLearningRoute,
            LearningPolicyFingerprint = E.LearningPolicyFingerprint,
            LearningObservationFingerprint = E.LearningObservationFingerprint,
            GetLearningInfo = E.GetLearningInfo,
        })
    end
end

local function installWrapped(slot, fn)
    wrappedFns[fn] = true
    wrappedSlots[slot] = fn
    local cur = E[slot]
    if cur ~= nil and cur ~= fn and not wrappedFns[cur] then
        baseFns[slot] = cur
    end
    E[slot] = fn
end

local function isRecipeNIP(spell, recipe)
    if type(E.RecipeNIP) == "function" and not wrappedFns[E.RecipeNIP] then
        return E.RecipeNIP(spell, recipe)
    end
    if type(recipe) == "table" then
        if recipe.availability ~= nil then return recipe.availability ~= "live" end
        if recipe.nip == true then return true end
    end
    local DS = getDS()
    if type(spell) == "number" and spell > 0 and DS and type(DS.Recipe) == "function" then
        local rec = DS.Recipe(spell)
        if type(rec) == "table" then return rec.availability ~= "live" end
    end
    return false
end

local specializationCache = setmetatable({}, { __mode = "k" })

local function specializationGroups(info)
    if type(info) ~= "table" then return nil end
    local cached = specializationCache[info]
    if cached ~= nil then return cached or nil end
    local DS = getDS()
    local specs = DS and type(DS.Specializations) == "function" and DS.Specializations() or {}
    local groups = {}
    for _, route in ipairs(info.routes or {}) do
        local group = {}
        for _, condition in ipairs(route.conditions or {}) do
            local sid = condition.spellID or condition.value
            if condition.kind == "ability" and type(sid) == "number" and specs[sid] then
                group[#group + 1] = sid
            end
        end
        if #group == 0 then
            specializationCache[info] = false
            return nil
        end
        groups[#groups + 1] = group
    end
    specializationCache[info] = #groups > 0 and groups or false
    return #groups > 0 and groups or nil
end

function E.HookGates()
    ensureHooks()
end

function E.LearningPolicyFingerprint()
    ensureHooks()
    local DS = getDS()
    local fp = DS and type(DS.Fingerprint) == "function" and DS.Fingerprint() or "missing"
    return "native-learning:v2:" .. tostring(fp or "missing")
end

function E.GetLearningInfo(slug, spell)
    ensureHooks()
    if not positiveInteger(spell) then return nil end
    local DS = getDS()
    if not DS or type(DS.LearningRoutes) ~= "function" then return nil end
    local info = DS.LearningRoutes(spell)
    if type(info) ~= "table" or info.spellID ~= spell then return nil end
    if slug ~= nil and info.profession ~= slug then return nil end
    return info
end

function E.AttachLearningInfo(recipe, knownFlag)
    ensureHooks()
    if type(recipe) ~= "table" then return recipe end
    recipe.learningSourcesRequired = true
    recipe.learningDataFingerprint = E.LearningPolicyFingerprint()
    local slug, spell = recipe.profession, spellOf(recipe)
    local info = E.GetLearningInfo(slug, spell)
    if type(info) == "table" and type(info.routes) == "table" then
        for _, route in ipairs(info.routes) do
            if type(route) == "table" and route.kind == "autoGrant" and route.status == "confirmed"
                and positiveInteger(route.minSkillRank) and type(recipe.learn) == "number"
                and route.minSkillRank ~= recipe.learn and recipe.skillSource ~= "client" then
                recipe.catalogueLearn = recipe.catalogueLearn or recipe.learn
                recipe.learn = route.minSkillRank
                recipe.skillSource = "automaticSkillGrant"
                break
            end
        end
    end
    recipe.learningSpecializations = specializationGroups(info)
    if knownFlag ~= true then
        recipe.learningInfo = info
    end
    return recipe
end

local function knownRecipe(recipe, snapshot, state)
    local spell = spellOf(recipe)
    local key = recipe.key or (recipe.profession and spell and (recipe.profession .. ":" .. tostring(spell)))
    local learned = type(state) == "table" and state.learned or nil
    if type(learned) == "table" and (learned[key] == true or learned[spell] == true) then return true end
    if type(snapshot) == "table" then
        local observed = snapshot.known
        if type(observed) == "table" then
            return observed[key] == true or observed[spell] == true
        end
    end
    return E.Known(spell) == true
end

local function professionClassEligibility(recipe, snapshot)
    if recipe.profession ~= "poisons" then return true end
    local id = identity(snapshot, "classID", _G.UnitClass)
    if type(id) ~= "number" or id < 1 then return false, "clientDataPending", { status = "unknown" } end
    if id ~= 4 then return false, "poisonRogueRequired", { status = "blocked" } end
    return true
end

local function buildConditionContext(recipe, snapshot, state, pricingContext)
    snapshot = type(snapshot) == "table" and (snapshot.snapshot or snapshot) or nil
    local ctx = {}
    if snapshot then
        ctx.strict = true
        ctx.level = snapshot.level
        ctx.faction = normalizeFaction(snapshot.faction)
        ctx.classID = snapshot.classID
        ctx.raceID = snapshot.raceID
        ctx.quests = snapshot.completedQuests or snapshot.quests
        ctx.reputations = snapshot.reputations
        ctx.items = snapshot.ownedSourceItems or snapshot.items
    elseif type(pricingContext) == "table" and pricingContext.faction ~= nil then
        ctx.faction = normalizeFaction(pricingContext.faction)
    end
    local skills = {}
    local hasSkills = false
    if snapshot and type(snapshot.professions) == "table" then
        ctx.skillsComplete = true
        hasSkills = true
        for pSlug, entry in pairs(snapshot.professions) do
            if type(entry) == "table" and not entry.unlearned and type(entry.cur) == "number" then
                skills[pSlug] = entry.cur
            elseif type(entry) == "number" then
                skills[pSlug] = entry
            end
        end
    end
    if type(state) == "table" and type(state.skill) == "table" then
        hasSkills = true
        for pSlug, cur in pairs(state.skill) do
            if type(cur) == "number" then skills[pSlug] = cur end
        end
    end
    if hasSkills then ctx.skills = skills end

    local abilities = {}
    local hasAbilities = false
    if snapshot then
        local src = snapshot.learningAbilities or snapshot.specializationAbilities or snapshot.abilities
            or (type(snapshot.specializationContext) == "table" and snapshot.specializationContext.abilities) or nil
        if type(src) == "table" then
            hasAbilities = true
            for id, v in pairs(src) do
                if type(v) == "boolean" then abilities[id] = v end
            end
        end
    end
    if type(state) == "table" and type(state.specializationAbilities) == "table" then
        if not snapshot and not hasAbilities then
            local gates = getGates()
            if gates and type(gates.Abilities) == "function" then
                for id, v in pairs(gates.Abilities()) do abilities[id] = v end
            end
        end
        hasAbilities = true
        for id, v in pairs(state.specializationAbilities) do
            if v == true then abilities[id] = true end
        end
    end
    if hasAbilities then ctx.abilities = abilities end
    return ctx
end

local CONDITION_REASON = {
    race = "characterRaceRequired",
    class = "characterClassRequired",
    reputation = "reputationRequired",
    questGroup = "questRequired",
    hasItem = "learningConditionFailed",
    faction = "learningFactionRequired",
    level = "characterLevelRequired",
    skill = "skillRequired",
    ability = "specializationRequired",
}

local function checkConditions(conditions, condCtx)
    if conditions == nil then return true, false, nil, {}, false end
    if type(conditions) ~= "table" then return true, true, nil, {}, true end
    local Cond = getCond()
    local unresolved, reason, abilities, sourceUnknown = false, nil, {}, false
    for _, c in ipairs(conditions) do
        if type(c) == "table" then
            local res
            if Cond and type(Cond.Evaluate) == "function" then
                res = Cond.Evaluate(c, condCtx)
            end
            if res == false then
                reason = reason or CONDITION_REASON[c.kind] or "learningConditionFailed"
                if c.kind == "ability" and type(c.spellID) == "number" then
                    abilities[#abilities + 1] = c.spellID
                end
            elseif res == nil then
                unresolved = true
                if c.kind == "unknown" or not CONDITION_REASON[c.kind] then
                    sourceUnknown = true
                end
            end
        end
    end
    return reason == nil, unresolved, reason, abilities, sourceUnknown
end

local function specializationAllowed(abilityID, snapshot, state, condCtx)
    if type(abilityID) ~= "number" or abilityID <= 0 then return true end
    if type(state) == "table" and type(state.specializationAbilities) == "table" and state.specializationAbilities[abilityID] == true then
        return true
    end
    local DS = getDS()
    local gates = getGates()
    local spec = DS and type(DS.Specialization) == "function" and DS.Specialization(abilityID) or nil
    if type(spec) == "table" then
        local grp = spec.exclusiveGroup or spec.profession
        local choice
        if type(snapshot) == "table" then
            if type(snapshot.specializationChoices) == "table" then
                choice = snapshot.specializationChoices[grp]
            end
            if choice == nil and spec.profession == "engineering" then
                choice = snapshot.engineeringSpecialization
                    or (type(snapshot.specializationContext) == "table" and snapshot.specializationContext.choice)
            end
        elseif gates and type(gates.GetPlannedChoice) == "function" then
            choice = gates.GetPlannedChoice(grp)
        end
        if grp == "blacksmithing_weaponsmith" then
            local parentChoice
            if type(snapshot) == "table" and type(snapshot.specializationChoices) == "table" then
                parentChoice = snapshot.specializationChoices.blacksmithing
            elseif not snapshot and gates and type(gates.GetPlannedChoice) == "function" then
                parentChoice = gates.GetPlannedChoice("blacksmithing")
            end
            if parentChoice == "armorsmith" then return false end
        end
        if choice ~= nil and choice ~= "none" and choice ~= "unknown" and choice ~= "conflict" then
            if choice ~= spec.specKey and choice ~= abilityID then
                return false
            end
        end
    end
    local Cond = getCond()
    if Cond and type(Cond.Evaluate) == "function" then
        local res = Cond.Evaluate({ kind = "ability", spellID = abilityID }, condCtx)
        return res ~= false
    end
    return true
end

local function infoFor(recipe, snapshot)
    if type(recipe.learningInfo) == "table" then return recipe.learningInfo end
    if snapshot then return nil end
    return E.GetLearningInfo(recipe.profession, spellOf(recipe))
end

local function routesFor(recipe, info)
    local out, seen = {}, {}
    local spell = spellOf(recipe)
    for _, list in ipairs({ recipe.learningRoutes or {}, type(info) == "table" and info.routes or {} }) do
        for _, route in ipairs(list) do
            if type(route) == "table" and (route.kind == "trainer" or route.kind == "item" or route.kind == "quest" or route.kind == "autoGrant") then
                local id = route.routeKey or route.id or (route.kind .. ":" .. tostring(route.teachingItemID or route.itemID or spell))
                if not seen[id] then
                    seen[id] = true
                    out[#out + 1] = { route = route, supplemental = (info and list == info.routes) or false }
                end
            end
        end
    end
    if #out == 0 and type(recipe.formula or recipe.formulaID) == "number" then
        local item = recipe.formula or recipe.formulaID
        out[1] = {
            route = {
                routeKey = "native:item:" .. tostring(spell) .. ":" .. tostring(item),
                kind = "item",
                teachingItemID = item,
                status = "unknown",
                conditionsKnown = false,
                conditions = {},
            },
        }
    end
    return out
end

local function ownedItem(snapshot, id)
    if not positiveInteger(id) then return 0 end
    if type(snapshot) == "table" then
        return (type(snapshot.ownedTeachingItems) == "table" and snapshot.ownedTeachingItems[id]) or 0
    end
    local fn = (_G.C_Item and _G.C_Item.GetItemCount) or _G.GetItemCount
    if type(fn) == "function" then
        local ok, n = pcall(fn, id, false, false)
        if ok and type(n) == "number" then return n end
    end
    return 0
end

local function evaluateTrainers(route, condCtx, playerFaction)
    local trainers = route.trainers
    if type(trainers) ~= "table" or #trainers == 0 then
        local ids = route.trainerIDs
        if type(ids) ~= "table" or #ids == 0 then
            return true, nil, nil
        end
        trainers = {}
        for i = 1, #ids do trainers[i] = { npcID = ids[i] } end
    end
    local DS = getDS()
    local Cond = getCond()
    local accessible = {}
    local anyNil, firstFailReason, anySourceUnknown = false, nil, false
    for _, t in ipairs(trainers) do
        local npcID = type(t) == "table" and t.npcID or t
        local npc = type(npcID) == "number" and DS and type(DS.Npc) == "function" and DS.Npc(npcID) or nil
        local side = npc and normalizeFaction(npc.faction) or nil
        local factionOK = not playerFaction or not side or side == "N" or side == playerFaction
        if not factionOK then
            firstFailReason = firstFailReason or "learningFactionRequired"
        else
            local npcPass, npcPending, npcReason, _, npcUnknown = true, false, nil, nil, false
            if type(npc) == "table" and type(npc.accessConditions) == "table" and #npc.accessConditions > 0 then
                npcPass, npcPending, npcReason, _, npcUnknown = checkConditions(npc.accessConditions, condCtx)
            elseif npc == nil and Cond and type(Cond.NpcAccessState) == "function" and type(condCtx) == "table" and condCtx.strict then
                npcPending = false
            end
            local edgePass, edgePending, edgeReason, _, edgeUnknown = true, false, nil, nil, false
            if type(t) == "table" and type(t.conditions) == "table" and #t.conditions > 0 then
                edgePass, edgePending, edgeReason, _, edgeUnknown = checkConditions(t.conditions, condCtx)
            end
            if npcPass and edgePass and not npcPending and not edgePending then
                accessible[#accessible + 1] = npcID
            elseif not npcPass or not edgePass then
                firstFailReason = firstFailReason or npcReason or edgeReason or "learningConditionFailed"
            else
                anyNil = true
                if npcUnknown or edgeUnknown then anySourceUnknown = true end
            end
        end
    end
    if #accessible > 0 then return true, accessible, nil end
    if anyNil then return nil, nil, anySourceUnknown and "learningDataMissing" or "clientDataPending" end
    return false, nil, firstFailReason or "learningConditionFailed"
end

local function quoteTeachingItem(id, recipe, route, snapshot, remaining, purchaseSource, state, pricingContext, condCtx, playerFaction, common)
    local DS = getDS()
    local itemMeta = DS and type(DS.Item) == "function" and DS.Item(id) or nil
    local bound = (type(itemMeta) == "table" and itemMeta.bindType == 1) or (recipe.bindOnPickup == true)
    local nonAuctionable = (type(itemMeta) == "table" and (itemMeta.nonAuctionable == true or itemMeta.bindType == 1 or itemMeta.bindType == 4))
        or (type(snapshot) == "table" and type(snapshot.nonAuctionable) == "table" and snapshot.nonAuctionable[id] == true)
        or (type(pricingContext) == "table" and type(pricingContext.nonAuctionable) == "table" and pricingContext.nonAuctionable[id] == true)
        or bound

    local context = shallow(snapshot or pricingContext)
    if not snapshot and context.faction == nil and playerFaction then context.faction = playerFaction end
    if snapshot then
        context.known = context.known or {}
        context.prices = context.prices or {}
        context.formulaOffers = context.formulaOffers or {}
        context.offers = context.offers or {}
        context.allowLimitedFormulas = context.allowLimitedFormulas == true
    end
    if nonAuctionable then
        context.nonAuctionable = shallow(context.nonAuctionable)
        context.nonAuctionable[id] = true
    end

    local supplyMod = getSupply()
    if supplyMod and type(supplyMod.FormulaFacts) == "function" then
        pcall(supplyMod.FormulaFacts, id)
    end

    local rawOffers = (type(context.formulaOffers) == "table" and context.formulaOffers[id])
        or (DS and type(DS.VendorOffers) == "function" and (DS.VendorOffers(id) or {}).offers)
        or {}

    local pureGoldOffers, exchangeOffers = {}, {}
    local allowLimited = E.AllowLimitedFormulas(context, recipe.profession)
    local limitedDisabled = false
    local sawDisabledCurrencyOffer = false

    for _, o in ipairs(rawOffers) do
        if type(o) == "table" and o.maxStock ~= 0 and o.available ~= false and o.purchasable ~= false and o.priceUsable ~= false then
            local npcID = tonumber(o.npcID or o.id)
            local npc = npcID and DS and type(DS.Npc) == "function" and DS.Npc(npcID) or nil
            local side = normalizeFaction(o.faction or (npc and npc.faction))
            local factionOK = not playerFaction or not side or side == "N" or side == playerFaction
            local npcPass, npcPending = true, false
            if type(npc) == "table" and type(npc.accessConditions) == "table" and #npc.accessConditions > 0 then
                npcPass, npcPending = checkConditions(npc.accessConditions, condCtx)
            end
            local offPass, offPending = checkConditions(o.conditions, condCtx)
            local bundle = tonumber(o.bundleSize or o.quantity or 1)
            local validBundle = bundle and bundle >= 1 and bundle == floor(bundle)
            if factionOK and npcPass and not npcPending and offPass and not offPending and validBundle then
                local hasCurrencies = type(o.currencies) == "table" and #o.currencies > 0
                local hasCostItems = type(o.costItems) == "table" and #o.costItems > 0
                local hasExt = o.hasExtendedCost == true or (tonumber(o.currencyID) or 0) > 0
                local isExchange = hasCurrencies or hasCostItems or hasExt
                local price = tonumber(o.priceCopper ~= nil and o.priceCopper or o.price)
                local unlimited = o.unlimited == true or o.maxStock == -1 or o.stock == -1
                if not unlimited and not allowLimited then
                    limitedDisabled = true
                end
                local stockVal = type(o.maxStock) == "number" and o.maxStock or o.stock
                local stockEnough = (type(stockVal) ~= "number" or stockVal < 0 or stockVal >= bundle)
                local stockOK = (unlimited or allowLimited) and stockEnough
                local cand = shallow(o)
                cand.npcID = npcID
                cand.price = price
                cand.priceCopper = price
                cand.bundleSize = bundle
                cand.quantity = bundle
                cand.unlimited = unlimited
                cand.faction = side
                if isExchange then
                    if stockEnough then sawDisabledCurrencyOffer = true end
                    if stockOK then exchangeOffers[#exchangeOffers + 1] = cand end
                elseif type(price) == "number" and price >= 0 then
                    pureGoldOffers[#pureGoldOffers + 1] = { offer = cand, stockOK = stockOK, price = price, unit = price / bundle }
                end
            end
        end
    end

    local bestVendor, bestVendorCost
    for _, item in ipairs(pureGoldOffers) do
        if item.stockOK then
            if not bestVendorCost or item.price < bestVendorCost then
                bestVendor = item.offer
                bestVendorCost = item.price
            end
        end
    end

    local ahPrice
    if not nonAuctionable then
        ahPrice = type(context.prices) == "table" and context.prices[id] or nil
        if ahPrice == nil and not (type(context) == "table" and context.prices) then
            local ra = getRouteAuto()
            if ra and type(ra.AHPriceOf) == "function" then
                local ok, p = pcall(ra.AHPriceOf, id)
                if ok then ahPrice = p end
            end
            if ahPrice == nil then
                local API = getAPI()
                if API and type(API.AHPriceOf) == "function" then
                    ahPrice = API.AHPriceOf(id, context)
                end
            end
        end
        if type(ahPrice) ~= "number" or ahPrice <= 0 or ahPrice >= math.huge then ahPrice = nil end
    end

    if type(remaining) == "table" then remaining = remaining[id] end
    local supply = E.FormulaAuctionSupplyOf(context, id)
    if remaining == nil and supply then
        local used = (type(state) == "table" and type(state.ahUsed) == "table" and state.ahUsed[id]) or 0
        remaining = math.max(0, supply.quantity - used)
    end
    local ahUsable = (ahPrice ~= nil) and supply ~= nil and supply.quantity >= 1 and (remaining == nil or remaining >= 1)

    local quote = shallow(common)
    quote.id = id
    quote.recipe = recipe
    quote.bindOnPickup = bound or nil
    quote.vendorOffers = {}
    for _, item in ipairs(pureGoldOffers) do
        quote.vendorOffers[#quote.vendorOffers + 1] = item.offer
    end

    if purchaseSource ~= "ah" and bestVendorCost ~= nil and (not ahUsable or bestVendorCost <= ahPrice) then
        quote.source = "vendor"
        quote.sourceType = "vendor"
        quote.vendor = true
        quote.cost = bestVendorCost
        quote.totalCost = bestVendorCost
        quote.offer = bestVendor
        quote.npcID = bestVendor.npcID
        quote.bundleSize = bestVendor.bundleSize
        quote.count = bestVendor.bundleSize
        quote.maxStock = bestVendor.maxStock
        quote.unlimited = bestVendor.unlimited or nil
        quote.limited = (not bestVendor.unlimited and E.LimitedFormulaOffer(bestVendor)) or nil
        quote.availabilityUncertain = (not bestVendor.unlimited and type(bestVendor.maxStock) ~= "number") or nil
        quote.usable = true
        quote.blocked = false
        quote.costComplete = not quote.availabilityUncertain
        return quote
    elseif ahUsable then
        quote.source = "ah"
        quote.sourceType = "ah"
        quote.vendor = false
        quote.cost = ahPrice
        quote.totalCost = ahPrice
        quote.usable = true
        quote.blocked = false
        quote.costComplete = true
        quote.considerAuctionSupply = true
        return quote
    end

    local canCurrency = E.AllowCurrencyFormulas(context, recipe.profession)
    if canCurrency and #exchangeOffers > 0 then
        local first = exchangeOffers[1]
        quote.source = "acquire"
        quote.sourceType = "acquire"
        quote.vendor = false
        quote.usable = true
        quote.blocked = false
        quote.costComplete = false
        quote.unpriced = true
        quote.acquisitionPending = true
        quote.acquisitionKind = "currency"
        quote.acquisitionOffer = first
        quote.acquisitionOffers = exchangeOffers
        quote.cost = type(first.price) == "number" and first.price >= 0 and first.price or nil
        quote.totalCost = quote.cost
        quote.npcID = first.npcID
        return quote
    end

    local canBound = E.AllowBindOnPickupFormulas(context, recipe.profession)
    local hasQuest, hasDrop = false, false
    if type(route.questIDs) == "table" and #route.questIDs > 0 then
        for _, qid in ipairs(route.questIDs) do
            local q = DS and type(DS.Quest) == "function" and DS.Quest(qid) or nil
            local qFac = q and normalizeFaction(q.faction) or nil
            if not playerFaction or not qFac or qFac == "N" or qFac == playerFaction then
                hasQuest = true
                break
            end
        end
    end
    local drops = DS and type(DS.Drops) == "function" and DS.Drops(id) or {}
    local extras = DS and type(DS.ExtraSources) == "function" and DS.ExtraSources(id) or {}
    if #drops > 0 or #extras > 0 then hasDrop = true end

    if bound and canBound and (hasQuest or hasDrop) then
        quote.source = "acquire"
        quote.sourceType = "acquire"
        quote.vendor = false
        quote.usable = true
        quote.blocked = false
        quote.costComplete = false
        quote.unpriced = true
        quote.acquisitionPending = true
        quote.acquisitionKind = hasQuest and "quest" or "drop"
        return quote
    end

    quote.source = "unknown"
    quote.sourceType = "unknown"
    quote.vendor = false
    quote.usable = false
    quote.blocked = true
    quote.costComplete = false
    quote.unpriced = true
    if ahPrice and not supply then
        quote.reason = "formulaAuctionSupplyUnknown"
    elseif ahPrice and (supply.quantity < 1 or (remaining ~= nil and remaining < 1)) then
        quote.reason = "formulaAuctionSupplyInsufficient"
    elseif not canCurrency and sawDisabledCurrencyOffer then
        quote.reason = "currencyFormulaDisabled"
    end
    if not quote.reason and limitedDisabled then
        quote.reason = "limitedFormulaDisabled"
        quote.limitedVendorDisabled = true
    elseif not quote.reason and bound and not canBound and (hasQuest or hasDrop) then
        quote.reason = "bindOnPickupFormulaDisabled"
    end
    quote.reason = quote.reason or "formulaUnavailable"
    return quote
end

local function routeQuote(recipe, route, snapshot, remaining, purchaseSource, state, pricingContext, condCtx, playerFaction, accessibleTrainers)
    local spell = spellOf(recipe)
    local key = recipe.key or (tostring(recipe.profession) .. ":" .. tostring(spell))
    local common = {
        spell = spell,
        profession = recipe.profession,
        recipeKey = key,
        known = false,
        learningRouteId = route.routeKey or route.id,
        learningRoute = route,
        count = 1,
        need = 1,
        recipes = { { profession = recipe.profession, spell = spell, key = key } },
        sources = {},
    }
    if route.kind == "autoGrant" then
        common.source = "trainer"
        common.sourceType = "trainer"
        common.recipe = recipe
        common.cost = 0
        common.totalCost = 0
        common.usable = true
        common.costComplete = true
        common.blocked = false
        common.automatic = true
        return common
    elseif route.kind == "trainer" then
        local cost = tonumber(route.trainingCostCopper)
            or tonumber(route.trainingCost)
            or (type(recipe.learningRequirements) == "table" and tonumber(recipe.learningRequirements.trainingCost))
            or tonumber(recipe.trainingCost)
        local tids = accessibleTrainers or route.trainerIDs
        if not tids and type(route.trainers) == "table" then
            tids = {}
            for _, t in ipairs(route.trainers) do
                if type(t) == "table" and type(t.npcID) == "number" then tids[#tids + 1] = t.npcID end
            end
        end
        common.source = "trainer"
        common.sourceType = "trainer"
        common.recipe = recipe
        common.cost = cost and cost >= 0 and cost or nil
        common.totalCost = common.cost
        common.usable = true
        common.costComplete = common.cost ~= nil
        common.blocked = false
        common.unpriced = common.cost == nil or nil
        common.reason = common.unpriced and "learningPriceUnknown" or nil
        common.trainerIDs = tids
        return common
    elseif route.kind == "quest" then
        local id = tonumber(route.teachingItemID or route.itemID)
        local prepaid = type(state) == "table" and type(state.formulaPaid) == "table" and id and state.formulaPaid[id]
        if id and (prepaid or ownedItem(snapshot, id) > 0) then
            common.id = id
            common.source = "owned"
            common.sourceType = "owned"
            common.cost = 0
            common.totalCost = 0
            common.usable = true
            common.costComplete = true
            common.blocked = false
            common.recipe = recipe
            return common
        end
        local canBound = E.AllowBindOnPickupFormulas(snapshot or pricingContext, recipe.profession)
        if canBound then
            common.source = "acquire"
            common.sourceType = "acquire"
            common.recipe = recipe
            common.usable = true
            common.blocked = false
            common.costComplete = false
            common.unpriced = true
            common.acquisitionPending = true
            common.acquisitionKind = "quest"
            return common
        end
        common.source = "quest"
        common.sourceType = "quest"
        common.recipe = recipe
        common.usable = false
        common.blocked = true
        common.costComplete = false
        common.unpriced = true
        common.reason = "bindOnPickupFormulaDisabled"
        return common
    elseif route.kind ~= "item" then
        common.source = route.kind or "unknown"
        common.usable = false
        common.blocked = true
        common.costComplete = false
        common.unpriced = true
        common.reason = "learningDataMissing"
        common.recipe = recipe
        return common
    end

    local id = tonumber(route.teachingItemID or route.itemID)
    if not positiveInteger(id) then
        common.usable = false
        common.blocked = true
        common.reason = "learningDataMissing"
        common.recipe = recipe
        return common
    end
    local prepaid = type(state) == "table" and type(state.formulaPaid) == "table" and state.formulaPaid[id]
    if prepaid or ownedItem(snapshot, id) > 0 then
        common.id = id
        common.source = "owned"
        common.sourceType = "owned"
        common.cost = 0
        common.totalCost = 0
        common.usable = true
        common.costComplete = true
        common.blocked = false
        common.owned = not prepaid or nil
        common.prepaid = prepaid or nil
        common.recipe = recipe
        return common
    end
    return quoteTeachingItem(id, recipe, route, snapshot, remaining, purchaseSource, state, pricingContext, condCtx, playerFaction, common)
end

local function decision(recipe, info, status, route)
    local detail = {
        status = status,
        route = route,
        routeId = route and (route.routeKey or route.id),
        coverage = (type(info) == "table" and info.coverage) or "none",
        missingReasons = (type(info) == "table" and info.missingReasons) or { "sourceMissing" },
        learningDataFingerprint = recipe.learningDataFingerprint or E.LearningPolicyFingerprint(),
    }
    local id = route and tonumber(route.teachingItemID or route.itemID)
    if id then detail.teachingItemID = id end
    if status == "unknown" then
        local seen, ids = {}, {}
        for _, entry in ipairs((type(info) == "table" and info.routes) or {}) do
            local item = tonumber(entry.teachingItemID or entry.itemID)
            if positiveInteger(item) and not seen[item] then
                seen[item] = true
                ids[#ids + 1] = item
            end
        end
        if #ids > 0 then
            table.sort(ids)
            detail.missingItemIDs = ids
            if #ids == 1 then detail.teachingItemID = ids[1] end
        end
    end
    return detail
end

function E.LearningSource(recipe)
    ensureHooks()
    if type(recipe) ~= "table" then return nil end
    if type(recipe.selectedLearningRoute) == "table" then
        local k = recipe.selectedLearningRoute.kind
        return k == "autoGrant" and "trainer" or k
    end
    if recipe.learnSource == "trainer" or recipe.trainerObserved then return "trainer" end
    local spell = spellOf(recipe)
    local rt = ns.ProfRecipeRuntime or (type(gns) == "table" and gns.ProfRecipeRuntime)
    if type(rt) == "table" and positiveInteger(spell) and type(rt[spell]) == "table" and rt[spell].trainerObserved then
        return "trainer"
    end
    for _, route in ipairs(recipe.learningRoutes or {}) do
        if type(route) == "table" and route.kind == "trainer" and (route.trainerObserved or route.trainerTaught) then
            return "trainer"
        end
    end
    local info = recipe.learningInfo or E.GetLearningInfo(recipe.profession, spell)
    if type(info) == "table" and type(info.routes) == "table" then
        local hasTrainer, hasItem, hasQuest = false, false, false
        for _, route in ipairs(info.routes) do
            if type(route) == "table" then
                if route.kind == "autoGrant" or route.kind == "trainer" then hasTrainer = true
                elseif route.kind == "item" then hasItem = true
                elseif route.kind == "quest" then hasQuest = true end
            end
        end
        if hasTrainer and not hasItem then return "trainer" end
        if hasItem then return "item" end
        if hasTrainer then return "trainer" end
        if hasQuest then return "quest" end
    end
    local gates = getGates()
    if gates and type(gates.LearningSource) == "function" and positiveInteger(spell) then
        local src = gates.LearningSource(spell)
        if src == "autoGrant" then return "trainer" end
        if src then return src end
    end
    return recipe.learnSource
end

function E.SelectLearningRoute(recipe, snapshot, state, remaining, purchaseSource, pricingContext)
    ensureHooks()
    if type(recipe) ~= "table" then return false, "clientDataPending", { status = "unknown" } end
    local spell = spellOf(recipe)
    if isRecipeNIP(spell, recipe) then
        return false, "catalogueFiltered", { status = "blocked" }
    end
    snapshot = type(snapshot) == "table" and (snapshot.snapshot or snapshot) or nil
    local classOK, classReason, classDetail = professionClassEligibility(recipe, snapshot)
    if not classOK then return classOK, classReason, classDetail end
    if recipe.craftingUnavailable or recipe.craftUnavailable or recipe.clientUnavailable then
        return false, "clientUnavailable", { status = "blocked" }
    end

    local condCtx = buildConditionContext(recipe, snapshot, state, pricingContext)
    local gates = getGates()
    local ability = tonumber(recipe.requiredAbilityID)
    if (not ability or ability == 0) and gates and type(gates.RequiredAbility) == "function" and positiveInteger(spell) then
        ability = gates.RequiredAbility(spell)
    end
    if type(ability) == "number" and ability > 0 then
        if not specializationAllowed(ability, snapshot, state, condCtx) then
            return false, "specializationRequired", { status = "blocked", requiredAbility = ability, requiredAbilities = { ability } }
        end
    end

    local isKnown = knownRecipe(recipe, snapshot, state)
    local info = infoFor(recipe, snapshot)
    local groups = isKnown and (recipe.learningSpecializations or specializationGroups(info))
    if groups then
        local allowed, required = false, {}
        for _, grp in ipairs(groups) do
            local pass = true
            for _, id in ipairs(grp) do
                if not specializationAllowed(id, snapshot, state, condCtx) then
                    pass = false
                    required[#required + 1] = id
                end
            end
            if pass then allowed = true; break end
        end
        if not allowed then
            return false, "specializationRequired", {
                status = "blocked",
                requiredAbilities = required,
                requiredAbility = #required == 1 and required[1] or nil,
            }
        end
    end
    if isKnown then return true, nil, { status = "learned" } end

    if type(recipe._conditionsCheck) == "table" and #recipe._conditionsCheck > 0 then
        local pass, pending, why, reqAbilities, sourceUnknown = checkConditions(recipe._conditionsCheck, condCtx)
        if not pass then
            return false, why, {
                status = "blocked",
                requiredAbilities = reqAbilities,
                requiredAbility = #reqAbilities == 1 and reqAbilities[1] or nil,
            }
        end
        if pending then
            return false, sourceUnknown and "learningDataMissing" or "clientDataPending", { status = "unknown", hasPending = true }
        end
        return true, nil, { status = "allowed" }
    end

    if type(recipe.learningConstraints) == "table" and #recipe.learningConstraints > 0 then
        local pass, pending, why, reqAbilities, sourceUnknown = checkConditions(recipe.learningConstraints, condCtx)
        if not pass then
            local detail = decision(recipe, info, "blocked")
            detail.requiredAbilities = reqAbilities
            return false, why, detail
        end
        if pending then
            return false, sourceUnknown and "learningDataMissing" or "clientDataPending", decision(recipe, info, "unknown")
        end
    end

    local playerFaction = playerFactionOf(snapshot, pricingContext)
    local best, bestCost, unpriced, failure, failureReason
    local hasConflict, hasPending = false, false

    for _, entry in ipairs(routesFor(recipe, info)) do
        local route = entry.route
        if route.status == "conflict" then
            hasConflict = true
        elseif route.kind ~= "item" and (route.status ~= "confirmed" or route.conditionsKnown ~= true) then
            hasPending = true
        elseif route.kind == "item" and route.status ~= "confirmed" then
            hasPending = true
        else
            local conds = {}
            for _, c in ipairs(route.conditions or {}) do conds[#conds + 1] = c end
            if route.kind == "autoGrant" and positiveInteger(route.minSkillRank) then
                conds[#conds + 1] = { kind = "skill", profession = recipe.profession, min = route.minSkillRank }
            end
            local pass, pending, why, reqAbilities, sourceUnknown = checkConditions(conds, condCtx)
            local detail = decision(recipe, info, (pass and not pending) and "allowed" or (pending and "unknown" or "blocked"), route)
            detail.requiredAbilities = reqAbilities
            if not pass then
                if not failure then failure, failureReason = detail, why end
            elseif pending then
                if not failure then failure, failureReason = detail, sourceUnknown and "learningDataMissing" or "clientDataPending" end
            else
                local trainersOK, accessibleTrainers, trainerWhy = true, nil, nil
                if route.kind == "trainer" then
                    trainersOK, accessibleTrainers, trainerWhy = evaluateTrainers(route, condCtx, playerFaction)
                end
                if trainersOK == false then
                    detail.status = "blocked"
                    if not failure then failure, failureReason = detail, trainerWhy end
                elseif trainersOK == nil then
                    detail.status = "unknown"
                    if not failure then failure, failureReason = detail, trainerWhy end
                else
                    local quote = routeQuote(recipe, route, snapshot, remaining, purchaseSource, state, pricingContext, condCtx, playerFaction, accessibleTrainers)
                    detail.quote = quote
                    if quote and quote.usable then
                        detail.missingReasons = {}
                        if type(quote.cost) == "number" and not quote.acquisitionPending then
                            if not bestCost or quote.cost < bestCost then
                                best, bestCost = detail, quote.cost
                            end
                        elseif not unpriced then
                            unpriced = detail
                        end
                    elseif not failure then
                        failure, failureReason = detail, (quote and quote.reason) or "formulaUnavailable"
                    end
                end
            end
        end
    end

    if best or unpriced then
        return true, nil, best or unpriced
    end
    if not failure then
        if hasConflict then
            return false, "specializationEvidenceConflict", decision(recipe, info, "conflict")
        end
        if hasPending then
            return false, "learningDataMissing", decision(recipe, info, "unknown")
        end
    end
    return false, failureReason or "learningDataMissing", failure or decision(recipe, info, "unknown")
end

installWrapped("LearningSource", E.LearningSource)
installWrapped("LearningEligibility", E.SelectLearningRoute)
E.RecipeSpecializationAllowed = E.SelectLearningRoute
E.RouteRecipeEligibility = E.SelectLearningRoute

local function normalizeDSRecipe(dsRec)
    if type(dsRec) ~= "table" then return nil end
    local mats = {}
    for _, r in ipairs(dsRec.reagents or {}) do
        if type(r) == "table" and positiveInteger(r.itemID) and positiveInteger(r.count) then
            mats[#mats + 1] = { r.itemID, r.count }
        end
    end
    local lo = tonumber(dsRec.outputCountMin) or 1
    local hi = tonumber(dsRec.outputCountMax) or lo
    return {
        spell = dsRec.spellID,
        spellID = dsRec.spellID,
        profession = dsRec.profession,
        skillLineID = dsRec.skillLineID,
        key = tostring(dsRec.profession) .. ":" .. tostring(dsRec.spellID),
        availability = dsRec.availability,
        categoryKey = dsRec.categoryKey,
        learn = dsRec.learnedAt,
        orange = dsRec.orange,
        yellow = dsRec.yellow,
        green = dsRec.green,
        grey = dsRec.grey,
        item = dsRec.outputItemID,
        outputItemID = dsRec.outputItemID,
        count = lo,
        outputMin = lo,
        outputMax = hi,
        variableOutput = hi > lo or nil,
        mats = mats,
        requiredAbilityID = dsRec.requiredAbilityID,
        cooldownSeconds = dsRec.cooldownSeconds,
        cooldownGroup = dsRec.cooldownGroup,
    }
end

local function wrappedFindRecipe(slug, spell)
    ensureHooks()
    if isRecipeNIP(spell) then return nil end
    local recipe
    if type(baseFns.FindRecipe) == "function" then
        local ok, r = pcall(baseFns.FindRecipe, slug, spell)
        if ok and type(r) == "table" then recipe = r end
    end
    if not recipe and positiveInteger(spell) then
        local DS = getDS()
        local dsRec = DS and type(DS.Recipe) == "function" and DS.Recipe(spell) or nil
        if type(dsRec) == "table" and (slug == nil or dsRec.profession == slug) and dsRec.availability == "live" then
            recipe = normalizeDSRecipe(dsRec)
        end
    end
    if type(recipe) == "table" then
        if isRecipeNIP(spell, recipe) then return nil end
        E.AttachLearningInfo(recipe, E.Known(spell) == true)
    end
    return recipe
end
installWrapped("FindRecipe", wrappedFindRecipe)

local function wrappedFormulaFor(recipe, context, remaining, purchaseSource)
    ensureHooks()
    if type(recipe) ~= "table" then return nil end
    local snapshot = type(context) == "table" and (context.snapshot
        or ((context.known ~= nil or context.recipes ~= nil or context.byKey ~= nil or context.prices ~= nil or context.learningSourcesRequired ~= nil) and context))
        or nil
    local ok, reason, detail = E.SelectLearningRoute(recipe, snapshot, nil, remaining, purchaseSource, context)
    if ok and type(detail) == "table" and detail.status == "learned" then return nil end
    if ok and type(detail) == "table" and detail.quote then return detail.quote end
    if type(detail) == "table" and detail.quote then return detail.quote end
    local item = recipe.formula or recipe.formulaID
    if not positiveInteger(item) and type(detail) == "table" then
        item = detail.teachingItemID
    end
    local quote = {}
    quote.id = item
    quote.spell = spellOf(recipe)
    quote.profession = recipe.profession
    quote.recipeKey = recipe.key
    quote.recipe = recipe
    quote.count = 1
    quote.need = 1
    quote.known = false
    quote.source = "unknown"
    quote.sourceType = "unknown"
    quote.vendor = false
    quote.usable = false
    quote.blocked = true
    quote.costComplete = false
    quote.unpriced = true
    quote.reason = reason
    quote.learningStatus = type(detail) == "table" and detail.status or "unknown"
    quote.missingReasons = type(detail) == "table" and detail.missingReasons or nil
    quote.recipes = { { profession = recipe.profession, spell = spellOf(recipe), key = recipe.key } }
    return quote
end
installWrapped("FormulaFor", wrappedFormulaFor)

local trackedQuests, trackedReputations = {}, {}
local questFacts, reputationFacts = {}, {}
local trackedSourceItems, sourceItemFacts = {}, {}
local trackedAbilities, abilityFacts = {}, {}
local observationRevision = 0
local pendingObservationEvents = {}
local contextState

local function questDone(id)
    local Cond = getCond()
    if Cond and type(Cond.EvaluateQuestGroups) == "function" then
        return Cond.EvaluateQuestGroups({ { id } })
    end
    return nil
end

local function standing(factionID)
    if type(_G.C_Reputation) == "table" and type(_G.C_Reputation.GetFactionDataByID) == "function" then
        local ok, data = pcall(_G.C_Reputation.GetFactionDataByID, factionID)
        if ok and type(data) == "table" and type(data.reaction) == "number" then return data.reaction end
    end
    if type(_G.GetFactionInfoByID) == "function" then
        local ok, _, _, rank = pcall(_G.GetFactionInfoByID, factionID)
        if ok and type(rank) == "number" then return rank end
    end
    return nil
end

local function sourceItemCount(id)
    if not positiveInteger(id) then return nil end
    local fn = (type(_G.C_Item) == "table" and _G.C_Item.GetItemCount) or _G.GetItemCount
    if type(fn) == "function" then
        local ok, n = pcall(fn, id, false, false)
        if ok and type(n) == "number" then return n end
    end
    return nil
end

local function fact(value)
    if value == nil then return "?" end
    if value == true then return "1" end
    if value == false then return "0" end
    return tostring(value)
end

local function observationChanged()
    observationRevision = observationRevision + 1
    local d = E.ClientStore()
    if type(d) == "table" then
        d.clientInputRevision = (tonumber(d.clientInputRevision) or 0) + 1
    end
end

function E.LearningObservationFingerprint()
    ensureHooks()
    if not contextState and E.UpdateLearningContext then
        local lvl
        if type(_G.UnitLevel) == "function" then
            local ok, v = pcall(_G.UnitLevel, "player")
            if ok then lvl = v end
        end
        E.UpdateLearningContext(lvl, E.Professions())
    end
    return "learning-observations:" .. tostring(observationRevision)
end

function E.QueueLearningObservationEvent(event)
    if event == "UPDATE_FACTION" or event == "PLAYER_LOGIN" or event == "QUEST_TURNED_IN"
        or event == "QUEST_LOG_UPDATE" or event == "QUEST_ACCEPTED" or event == "BAG_UPDATE_DELAYED"
        or event == "PLAYER_EQUIPMENT_CHANGED" or event == "SPELLS_CHANGED" then
        pendingObservationEvents[event] = true
    end
end

function E.UpdateLearningContext(level, professions)
    local values = {}
    for slug, entry in pairs(professions or {}) do
        if type(entry) == "table" then
            values[#values + 1] = slug .. ":" .. tostring(entry.cur) .. ":" .. tostring(entry.max)
        end
    end
    table.sort(values)
    local signature = tostring(level) .. "|" .. table.concat(values, "|")
    local changed = contextState ~= nil and contextState ~= signature
    contextState = signature
    if changed then observationChanged() end
    return changed
end

function E.RefreshLearningObservations(event, tick)
    ensureHooks()
    local changed = false
    local events = event and { [event] = true } or pendingObservationEvents
    if not event then pendingObservationEvents = {} end
    if events.BAG_UPDATE_DELAYED or events.PLAYER_EQUIPMENT_CHANGED or events.PLAYER_LOGIN then
        for id in pairs(trackedSourceItems) do
            local cnt = sourceItemCount(id)
            local present
            if type(cnt) == "number" then present = cnt > 0 end
            local value = fact(present)
            if sourceItemFacts[id] and sourceItemFacts[id] ~= value then changed = true end
            sourceItemFacts[id] = value
            if tick then tick() end
        end
    end
    if events.UPDATE_FACTION or events.PLAYER_LOGIN then
        for id in pairs(trackedReputations) do
            local value = fact(standing(id))
            if reputationFacts[id] and reputationFacts[id] ~= value then changed = true end
            reputationFacts[id] = value
            if tick then tick() end
        end
    end
    if events.QUEST_TURNED_IN or events.QUEST_LOG_UPDATE or events.QUEST_ACCEPTED or events.PLAYER_LOGIN then
        for id in pairs(trackedQuests) do
            local value = fact(questDone(id))
            if questFacts[id] and questFacts[id] ~= value then changed = true end
            questFacts[id] = value
            if tick then tick() end
        end
    end
    if events.SPELLS_CHANGED or events.PLAYER_LOGIN then
        local Cond = getCond()
        for id in pairs(trackedAbilities) do
            local v
            if Cond and type(Cond.Evaluate) == "function" then
                v = Cond.Evaluate({ kind = "ability", spellID = id })
            end
            local value = fact(v)
            if abilityFacts[id] and abilityFacts[id] ~= value then changed = true end
            abilityFacts[id] = value
            if tick then tick() end
        end
    end
    if changed then observationChanged() end
    return changed
end

E.Refresh = E.RefreshLearningObservations

function E.CaptureLearningFacts(snapshot, tick)
    ensureHooks()
    if type(snapshot) ~= "table" then return snapshot end
    local DS = getDS()
    local Cond = getCond()
    local ids, reputations, abilities, items, sourceItems = {}, {}, {}, {}, {}
    local changed = false

    local function collect(conditions)
        for _, c in ipairs(conditions or {}) do
            if type(c) == "table" then
                if c.kind == "hasItem" and positiveInteger(c.itemID) then
                    sourceItems[c.itemID] = true
                elseif c.kind == "questGroup" then
                    for _, grp in ipairs(c.groups or {}) do
                        for _, id in ipairs(grp) do
                            if positiveInteger(id) then ids[id] = true end
                        end
                    end
                elseif c.kind == "reputation" and positiveInteger(c.factionID) then
                    reputations[c.factionID] = true
                elseif c.kind == "ability" and positiveInteger(c.spellID) then
                    abilities[c.spellID] = true
                end
            end
        end
    end

    for _, recipe in ipairs(snapshot.recipes or {}) do
        if type(recipe) == "table" and not knownRecipe(recipe, snapshot) then
            collect(recipe.learningConstraints)
            local info = recipe.learningInfo or E.GetLearningInfo(recipe.profession, spellOf(recipe))
            for _, entry in ipairs(routesFor(recipe, info)) do
                local route = entry.route
                collect(route.conditions)
                for _, t in ipairs(route.trainers or {}) do
                    if type(t) == "table" then
                        collect(t.conditions)
                        local npc = type(t.npcID) == "number" and DS and type(DS.Npc) == "function" and DS.Npc(t.npcID) or nil
                        if type(npc) == "table" then collect(npc.accessConditions) end
                    end
                end
                if route.kind == "item" then
                    local id = tonumber(route.teachingItemID or route.itemID)
                    if positiveInteger(id) then
                        items[id] = true
                        local vo = DS and type(DS.VendorOffers) == "function" and DS.VendorOffers(id) or nil
                        for _, o in ipairs((type(vo) == "table" and vo.offers) or {}) do
                            if type(o) == "table" then
                                collect(o.conditions)
                                local npc = type(o.npcID) == "number" and DS and type(DS.Npc) == "function" and DS.Npc(o.npcID) or nil
                                if type(npc) == "table" then collect(npc.accessConditions) end
                            end
                        end
                    end
                end
            end
        end
        if tick then tick() end
    end

    snapshot.completedQuests = snapshot.completedQuests or {}
    snapshot.reputations = snapshot.reputations or {}
    snapshot.learningAbilities = snapshot.learningAbilities or {}
    snapshot.ownedTeachingItems = snapshot.ownedTeachingItems or {}
    snapshot.ownedSourceItems = snapshot.ownedSourceItems or {}

    for id in pairs(sourceItems) do
        local count = sourceItemCount(id)
        snapshot.ownedSourceItems[id] = count
        local present
        if type(count) == "number" then present = count > 0 end
        local value = fact(present)
        if sourceItemFacts[id] and sourceItemFacts[id] ~= value then changed = true end
        trackedSourceItems[id], sourceItemFacts[id] = true, value
        if tick then tick() end
    end
    for id in pairs(ids) do
        local value = questDone(id)
        snapshot.completedQuests[id] = value
        if questFacts[id] and questFacts[id] ~= fact(value) then changed = true end
        trackedQuests[id], questFacts[id] = true, fact(value)
        if tick then tick() end
    end
    for id in pairs(reputations) do
        local value = standing(id)
        snapshot.reputations[id] = value
        if reputationFacts[id] and reputationFacts[id] ~= fact(value) then changed = true end
        trackedReputations[id], reputationFacts[id] = true, fact(value)
        if tick then tick() end
    end
    for id in pairs(abilities) do
        local value
        if Cond and type(Cond.Evaluate) == "function" then
            value = Cond.Evaluate({ kind = "ability", spellID = id })
        end
        snapshot.learningAbilities[id] = value
        if abilityFacts[id] and abilityFacts[id] ~= fact(value) then changed = true end
        trackedAbilities[id], abilityFacts[id] = true, fact(value)
        if tick then tick() end
    end
    for id in pairs(items) do
        local n = ownedItem(nil, id)
        if n > 0 then snapshot.ownedTeachingItems[id] = n end
        if tick then tick() end
    end
    snapshot.learningSourcesRequired = true
    if changed then observationChanged() end
    snapshot.learningDataFingerprint = E.LearningPolicyFingerprint()
    E.UpdateLearningContext(snapshot.level, E.Professions())
    snapshot.learningObservationFingerprint = E.LearningObservationFingerprint()
    return snapshot
end

local function wrappedCapture(slug, opts, tick)
    ensureHooks()
    local snapshot
    if type(baseFns.Capture) == "function" then
        snapshot = baseFns.Capture(slug, opts, tick)
    elseif type(opts) == "table" and type(opts.snapshot) == "table" then
        snapshot = E.Copy(opts.snapshot, tick)
    end
    if not snapshot or (type(opts) == "table" and opts.snapshot) then return snapshot end
    if not snapshot.learningDataFingerprint then E.CaptureLearningFacts(snapshot, tick) end
    return snapshot
end
installWrapped("Capture", wrappedCapture)

ensureHooks()
