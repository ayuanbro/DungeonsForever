local _, ns = ...
if type(ns) ~= "table" then ns = _G.DF_NS or {} end
local gns = _G.DF_NS

local G = {}
ns.ProfGates = G
if type(gns) == "table" and gns ~= ns then
    gns.ProfGates = G
end

local function getDS()
    return ns.ProfDataStore or (type(gns) == "table" and gns.ProfDataStore) or nil
end

local function getCond()
    return ns.ProfConditions or (type(gns) == "table" and gns.ProfConditions) or nil
end

local function getSolverCfg()
    return ns.SolverConfig or (type(gns) == "table" and gns.SolverConfig) or nil
end

local function getRouteAuto()
    return ns.ProfRouteAuto or (type(gns) == "table" and gns.ProfRouteAuto) or nil
end

local function getProfDB()
    return ns.ProfDB or (type(gns) == "table" and gns.ProfDB) or nil
end

local function getEconomy()
    return ns.ProfEconomy or (type(gns) == "table" and gns.ProfEconomy) or nil
end

local function getL()
    return ns.L or (type(gns) == "table" and gns.L) or nil
end

local function getSettingRaw(key, slug)
    local settings = ns.ProfSettings or (type(gns) == "table" and gns.ProfSettings) or getProfDB()
    if type(settings) == "table" and type(settings.SettingRaw) == "function" then
        return settings.SettingRaw(key, slug)
    end
    if type(ns.ProfSettingRaw) == "function" then
        return ns.ProfSettingRaw(key, slug)
    end
    local dbFn = getProfDB()
    if dbFn then
        local db = dbFn()
        local prof = type(db) == "table" and db.prof or nil
        if type(prof) == "table" then
            if type(slug) == "string" and type(prof.professionSettings) == "table" and type(prof.professionSettings[slug]) == "table" then
                local v = prof.professionSettings[slug][key]
                if v ~= nil then return v end
            end
            return prof[key]
        end
    end
    return nil
end

local function setSettingRaw(key, value, slug)
    local settings = ns.ProfSettings or (type(gns) == "table" and gns.ProfSettings) or getProfDB()
    if type(settings) == "table" and type(settings.SetSettingRaw) == "function" then
        return settings.SetSettingRaw(key, value, slug)
    end
    local dbFn = getProfDB()
    if dbFn then
        local db = dbFn()
        if type(db) == "table" then
            if type(db.prof) ~= "table" then db.prof = {} end
            db.prof[key] = value
            return value
        end
    end
    return nil
end

local SPEC_ABILITIES = {}
local SPEC_BY_GROUP = {}
local GROUPS_BY_PROF = {}
local SPEC_BY_ID = {}
local specsRef = nil
local cache = nil

G.SpecAbilities = SPEC_ABILITIES

local function ensureAbilities()
    local DS = getDS()
    local specs = DS and type(DS.Specializations) == "function" and DS.Specializations() or nil
    if type(specs) ~= "table" then return end
    if specsRef == specs and #SPEC_ABILITIES > 0 then return end
    specsRef = specs
    cache = nil
    for i = #SPEC_ABILITIES, 1, -1 do SPEC_ABILITIES[i] = nil end
    for k in pairs(SPEC_BY_GROUP) do SPEC_BY_GROUP[k] = nil end
    for k in pairs(GROUPS_BY_PROF) do GROUPS_BY_PROF[k] = nil end
    for k in pairs(SPEC_BY_ID) do SPEC_BY_ID[k] = nil end

    local seenGroups = {}
    for id, spec in pairs(specs) do
        if type(id) == "number" and id > 0 and type(spec) == "table" then
            SPEC_ABILITIES[#SPEC_ABILITIES + 1] = id
            SPEC_BY_ID[id] = spec
            local prof = spec.profession
            local grp = spec.exclusiveGroup or prof
            if type(grp) == "string" and grp ~= "" then
                if not SPEC_BY_GROUP[grp] then SPEC_BY_GROUP[grp] = {} end
                SPEC_BY_GROUP[grp][#SPEC_BY_GROUP[grp] + 1] = spec
                if type(prof) == "string" and prof ~= "" then
                    if not GROUPS_BY_PROF[prof] then GROUPS_BY_PROF[prof] = {} end
                    seenGroups[prof] = seenGroups[prof] or {}
                    if not seenGroups[prof][grp] then
                        seenGroups[prof][grp] = true
                        GROUPS_BY_PROF[prof][#GROUPS_BY_PROF[prof] + 1] = grp
                    end
                end
            end
        end
    end
    table.sort(SPEC_ABILITIES)
    for _, list in pairs(SPEC_BY_GROUP) do
        table.sort(list, function(a, b)
            return (a.abilitySpellID or 0) < (b.abilitySpellID or 0)
        end)
    end
    for prof, groups in pairs(GROUPS_BY_PROF) do
        table.sort(groups, function(a, b)
            if a == prof then return true end
            if b == prof then return false end
            return a < b
        end)
    end
end

function G.SpecAbilityIDs()
    ensureAbilities()
    local out = {}
    for i = 1, #SPEC_ABILITIES do
        out[i] = SPEC_ABILITIES[i]
    end
    return out
end

local function spellKnown(spell)
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
            local ok, v = pcall(fn, spell)
            if ok and v == true then return true end
            if ok and v == false then observedFalse = true end
        end
    end
    if observedFalse then return false end
    return nil
end

function G.Invalidate()
    cache = nil
    specsRef = nil
end

function G.Abilities()
    ensureAbilities()
    if cache then return cache end
    local out = {}
    for _, id in ipairs(SPEC_ABILITIES) do
        local v = spellKnown(id)
        if type(v) == "boolean" then out[id] = v end
    end
    cache = out
    return out
end

local SPEC_LABELS = {
    gnomish = { zhCN = "侏儒工程学", zhTW = "侏儒工程學", enUS = "Gnomish Engineering" },
    goblin = { zhCN = "地精工程学", zhTW = "哥布林工程學", enUS = "Goblin Engineering" },
    weaponsmith = { zhCN = "武器锻造师", zhTW = "武器鑄造師", enUS = "Weaponsmith" },
    armorsmith = { zhCN = "防具锻造师", zhTW = "護甲鑄造師", enUS = "Armorsmith" },
    master_swordsmith = { zhCN = "铸剑大师", zhTW = "鑄劍大師", enUS = "Master Swordsmith" },
    master_hammersmith = { zhCN = "铸锤大师", zhTW = "鑄錘大師", enUS = "Master Hammersmith" },
    master_axesmith = { zhCN = "铸斧大师", zhTW = "鑄斧大師", enUS = "Master Axesmith" },
    dragonscale = { zhCN = "龙鳞制皮", zhTW = "龍鱗製皮", enUS = "Dragonscale Leatherworking" },
    elemental = { zhCN = "元素制皮", zhTW = "元素製皮", enUS = "Elemental Leatherworking" },
    tribal = { zhCN = "部族制皮", zhTW = "部族製皮", enUS = "Tribal Leatherworking" },
}

function G.AbilityLabel(id)
    local DS = getDS()
    if DS and type(DS.RawText) == "function" then
        local txt = DS.RawText("spell", id)
        if type(txt) == "string" and txt ~= "" then return txt end
    end
    local fn = (_G.C_Spell and _G.C_Spell.GetSpellName) or _G.GetSpellInfo
    if type(fn) == "function" then
        local ok, value = pcall(fn, id)
        if ok and type(value) == "string" and value ~= "" then return value end
    end
    local spec = DS and type(DS.Specialization) == "function" and DS.Specialization(id) or SPEC_BY_ID[id]
    if type(spec) == "table" and type(spec.specKey) == "string" then
        local loc = (DS and type(DS.GetLocale) == "function" and DS.GetLocale()) or "enUS"
        local labels = SPEC_LABELS[spec.specKey]
        if labels then
            local L = getL()
            if type(L) == "table" then
                local localized = rawget(L, labels.zhCN)
                if type(localized) == "string" and localized ~= "" and (loc == "zhCN" or localized ~= labels.zhCN) then
                    return localized
                end
            end
            return labels[loc] or labels.enUS
        end
    end
    return tostring(id)
end

function G.RequiredAbility(spell)
    if type(spell) ~= "number" or spell <= 0 then return 0 end
    local DS = getDS()
    local rec = DS and type(DS.Recipe) == "function" and DS.Recipe(spell) or nil
    return (type(rec) == "table" and tonumber(rec.requiredAbilityID)) or 0
end

local function routeKindPresent(spell, kind)
    if type(spell) ~= "number" or spell <= 0 then return false end
    local DS = getDS()
    local lr = DS and type(DS.LearningRoutes) == "function" and DS.LearningRoutes(spell) or nil
    if type(lr) ~= "table" or type(lr.routes) ~= "table" then return false end
    for i = 1, #lr.routes do
        local route = lr.routes[i]
        if type(route) == "table" and route.kind == kind then
            return true
        end
    end
    return false
end

function G.TrainerFlag(spell)
    return routeKindPresent(spell, "trainer")
end

function G.ItemFlag(spell)
    return routeKindPresent(spell, "item")
end

function G.TrainerTaught(spell)
    return G.TrainerFlag(spell)
end

function G.ItemTaught(spell)
    return G.ItemFlag(spell)
end

function G.HasPending(spell)
    if type(spell) ~= "number" or spell <= 0 then return false end
    local DS = getDS()
    local lr = DS and type(DS.LearningRoutes) == "function" and DS.LearningRoutes(spell) or nil
    if type(lr) ~= "table" then return false end
    if lr.coverage == "partial" then return true end
    for _, route in ipairs(lr.routes or {}) do
        if type(route) == "table" and route.status == "unknown" then
            return true
        end
    end
    return false
end

function G.LearningSource(spell)
    if type(spell) ~= "number" or spell <= 0 then return nil end
    local DS = getDS()
    local lr = DS and type(DS.LearningRoutes) == "function" and DS.LearningRoutes(spell) or nil
    if type(lr) ~= "table" or type(lr.routes) ~= "table" then return nil end
    local has = {}
    for _, route in ipairs(lr.routes) do
        if type(route) == "table" and type(route.kind) == "string" then
            has[route.kind] = true
        end
    end
    for _, kind in ipairs({ "trainer", "item", "quest", "autoGrant" }) do
        if has[kind] then return kind end
    end
    return nil
end

local function resolveGroup(groupOrSlug)
    ensureAbilities()
    local key = groupOrSlug or "engineering"
    if SPEC_BY_GROUP[key] then return key end
    local groups = GROUPS_BY_PROF[key]
    if type(groups) == "table" and #groups > 0 then
        for i = 1, #groups do
            if groups[i] == key then return groups[i] end
        end
        return groups[1]
    end
    return key
end

local function findSpec(groupOrSlug, specKey)
    if type(specKey) ~= "string" or specKey == "" or specKey == "none" then return nil end
    ensureAbilities()
    local grp = resolveGroup(groupOrSlug)
    for _, spec in ipairs(SPEC_BY_GROUP[grp] or {}) do
        if spec.specKey == specKey then return spec end
    end
    for _, spec in pairs(SPEC_BY_ID) do
        if spec.specKey == specKey and (spec.exclusiveGroup == groupOrSlug or spec.profession == groupOrSlug) then
            return spec
        end
    end
    return nil
end

function G.LearnedChoice(groupOrSlug, abilitiesOpt)
    ensureAbilities()
    local grp = resolveGroup(groupOrSlug)
    local specs = SPEC_BY_GROUP[grp]
    if type(specs) ~= "table" or #specs == 0 then return "none" end
    local abilities = type(abilitiesOpt) == "table" and abilitiesOpt or G.Abilities()
    local knownSpecs = {}
    local anyNil = false
    for _, spec in ipairs(specs) do
        local v = abilities[spec.abilitySpellID]
        if v == true then
            knownSpecs[#knownSpecs + 1] = spec.specKey
        elseif v == nil then
            anyNil = true
        end
    end
    if #knownSpecs > 1 then return "conflict" end
    if #knownSpecs == 1 then return knownSpecs[1] end
    if anyNil then return "unknown" end
    return "none"
end

function G.EngineeringChoice()
    return G.LearnedChoice("engineering")
end

function G.GetChoiceSetting(groupOrSlug)
    ensureAbilities()
    local grp = resolveGroup(groupOrSlug)
    if grp == "engineering" then
        local v = getSettingRaw("engChoice")
        if type(v) == "string" and findSpec(grp, v) then return v end
        return "none"
    end
    local choices = getSettingRaw("specChoices")
    local v = type(choices) == "table" and choices[grp] or nil
    if type(v) == "string" and findSpec(grp, v) then return v end
    return "none"
end

function G.EffectiveChoice(groupOrSlug, abilitiesOpt)
    local grp = resolveGroup(groupOrSlug)
    local selected = G.GetChoiceSetting(grp)
    if selected ~= "none" then return selected, true end
    local learned = G.LearnedChoice(grp, abilitiesOpt)
    if learned ~= "none" and learned ~= "unknown" and learned ~= "conflict" then
        return learned, false
    end
    return "none", false
end

function G.GetPlannedChoice(groupOrSlug)
    local choice = G.EffectiveChoice(groupOrSlug)
    return choice
end

function G.SetPlannedChoice(value, groupOrSlug)
    ensureAbilities()
    local grp = resolveGroup(groupOrSlug)
    if value == "none" then
        if grp == "engineering" then
            local cur = getSettingRaw("engChoice")
            if cur == nil or cur == "none" then
                setSettingRaw("engChoice", "none")
                return true
            end
            setSettingRaw("engChoice", "none")
        else
            local choices = getSettingRaw("specChoices")
            if type(choices) == "table" then
                if choices[grp] == nil then return true end
                choices[grp] = nil
            else
                return true
            end
        end
        G.Invalidate()
        local ra = getRouteAuto()
        if ra and type(ra.Invalidate) == "function" then pcall(ra.Invalidate, "specialization") end
        return true
    end
    local spec = findSpec(grp, value)
    if not spec then return false end
    local targetGrp = spec.exclusiveGroup or grp
    if targetGrp == "engineering" then
        local cur = getSettingRaw("engChoice")
        if cur == spec.specKey then return true end
        setSettingRaw("engChoice", spec.specKey)
    else
        local dbFn = getProfDB()
        local choices = getSettingRaw("specChoices")
        if type(choices) ~= "table" then
            choices = {}
            setSettingRaw("specChoices", choices)
        elseif dbFn then
            local db = dbFn()
            if type(db) == "table" and type(db.prof) == "table" then
                db.prof.specChoices = choices
            end
        end
        if choices[targetGrp] == spec.specKey then return true end
        choices[targetGrp] = spec.specKey
    end
    G.Invalidate()
    local ra = getRouteAuto()
    if ra and type(ra.Invalidate) == "function" then pcall(ra.Invalidate, "specialization") end
    return true
end

function G.Allowed(slug, spell, opts)
    ensureAbilities()
    local ability = G.RequiredAbility(spell)
    if ability == 0 then return true end
    local DS = getDS()
    local spec = (DS and type(DS.Specialization) == "function" and DS.Specialization(ability)) or SPEC_BY_ID[ability]
    if type(spec) == "table" then
        local grp = spec.exclusiveGroup or spec.profession
        local choice = (type(opts) == "table" and type(opts.choicesByGroup) == "table" and opts.choicesByGroup[grp])
            or (type(opts) == "table" and opts.choice and grp == "engineering" and opts.choice)
            or G.EffectiveChoice(grp)
        if grp == "blacksmithing_weaponsmith" then
            local parentChoice = (type(opts) == "table" and type(opts.choicesByGroup) == "table" and opts.choicesByGroup.blacksmithing)
                or G.EffectiveChoice("blacksmithing")
            if parentChoice == "armorsmith" then
                return false, G.AbilityLabel(ability)
            end
        end
        if choice == spec.specKey then return true end
        return false, G.AbilityLabel(ability)
    end
    local v = spellKnown(ability)
    if v == true or v == nil then return true end
    return false, G.AbilityLabel(ability)
end

function G.LearningEligibility(spell)
    local DS = getDS()
    local rec = DS and type(DS.Recipe) == "function" and DS.Recipe(spell) or nil
    if type(rec) ~= "table" then
        return true, nil, { status = "unknown" }
    end
    local hp = G.HasPending(spell) or nil
    local ability = tonumber(rec.requiredAbilityID) or 0
    if ability == 0 then
        return true, nil, { status = G.LearningSource(spell) and "allowed" or "unknown", hasPending = hp }
    end
    local allowed, reason = G.Allowed(rec.profession, spell)
    if not allowed then
        return false, reason, { status = "blocked", hasPending = hp, ability = ability }
    end
    local v = spellKnown(ability)
    if v == true then return true, nil, { status = "allowed", hasPending = hp, ability = ability } end
    if v == nil then return true, nil, { status = "unknown", hasPending = hp, ability = ability } end
    return false, G.AbilityLabel(ability), { status = "blocked", hasPending = hp, ability = ability }
end

local function normalizeFaction(raw)
    if raw == "Alliance" or raw == "A" or raw == "a" then return "A" end
    if raw == "Horde" or raw == "H" or raw == "h" then return "H" end
    if raw == "Neutral" or raw == "N" or raw == "n" or raw == "Both" or raw == "B" then return "N" end
    return nil
end

function G.FactionCode()
    if type(_G.UnitFactionGroup) == "function" then
        local ok, f = pcall(_G.UnitFactionGroup, "player")
        if ok then
            local code = normalizeFaction(f)
            if code == "A" or code == "H" then return code end
        end
    end
    return nil
end

local function cloneInputs(turnInItems)
    local inputs, itemsCopy = {}, {}
    for _, row in ipairs(turnInItems or {}) do
        if type(row) == "table" then
            local id = row.itemID or row[1]
            local count = row.count or row[2] or 1
            if type(id) == "number" and id > 0 then
                inputs[#inputs + 1] = { id, count }
                itemsCopy[#itemsCopy + 1] = { itemID = id, count = count }
            end
        end
    end
    return inputs, itemsCopy
end

local function buildSpecGoal(spec, faction)
    local DS = getDS()
    faction = normalizeFaction(faction) or faction
    local goal = {
        id = spec.specKey,
        choice = spec.specKey,
        specKey = spec.specKey,
        exclusiveGroup = spec.exclusiveGroup,
        profession = spec.profession,
        abilityID = spec.abilitySpellID,
        abilitySpellID = spec.abilitySpellID,
        minSkill = spec.minSkill,
        minLevel = spec.minLevel,
        inputs = {},
        turnInItems = {},
        prerequisiteQuestGroups = {},
        prereqQuestGroups = {},
        prerequisiteQuestIDs = {},
    }
    local variants = spec.variants
    local variant
    if type(variants) ~= "table" or next(variants) == nil then
        goal.blockedReason = "specializationQuestUnknown"
    else
        if faction then
            variant = variants[faction] or variants.N
        elseif not variants.A and not variants.H then
            variant = variants.N
        end
        if type(variant) ~= "table" then
            goal.blockedReason = "specializationFactionUnknown"
        end
    end
    if type(variant) == "table" then
        goal.questID = variant.questID
        if type(variant.questID) == "number" and DS and type(DS.RawText) == "function" then
            goal.questName = DS.RawText("quest", variant.questID)
        end
        goal.npcID = variant.npcID
        if type(variant.npcID) == "number" and DS then
            if type(DS.RawText) == "function" then
                goal.npcName = DS.RawText("npc", variant.npcID)
            end
            local npc = type(DS.Npc) == "function" and DS.Npc(variant.npcID) or nil
            local sp = type(npc) == "table" and type(npc.spawns) == "table" and npc.spawns[1] or nil
            if type(sp) == "table" then
                goal.areaID = sp.areaID
                goal.mapID = sp.uiMapID
                goal.x = sp.x
                goal.y = sp.y
                if type(sp.areaID) == "number" and type(DS.RawText) == "function" then
                    goal.zone = DS.RawText("zone", sp.areaID)
                end
            end
        end
        goal.inputs, goal.turnInItems = cloneInputs(variant.turnInItems)
        local seen = {}
        for _, grp in ipairs(variant.prereqQuestGroups or {}) do
            if type(grp) == "table" and #grp > 0 then
                local g1, g2 = {}, {}
                for _, qid in ipairs(grp) do
                    g1[#g1 + 1] = qid
                    g2[#g2 + 1] = qid
                    if not seen[qid] then
                        seen[qid] = true
                        goal.prerequisiteQuestIDs[#goal.prerequisiteQuestIDs + 1] = qid
                    end
                end
                goal.prerequisiteQuestGroups[#goal.prerequisiteQuestGroups + 1] = g1
                goal.prereqQuestGroups[#goal.prereqQuestGroups + 1] = g2
            end
        end
    end
    return goal
end

function G.PrerequisiteText(goal)
    local groups = goal and (goal.prerequisiteQuestGroups or goal.prereqQuestGroups)
    if type(groups) ~= "table" or #groups == 0 then
        groups = {}
        for _, id in ipairs(goal and goal.prerequisiteQuestIDs or {}) do
            groups[#groups + 1] = { id }
        end
    end
    local out = {}
    for _, grp in ipairs(groups) do
        local parts = {}
        for _, id in ipairs(grp) do
            parts[#parts + 1] = "#" .. tostring(id)
        end
        if #parts > 0 then
            out[#out + 1] = #parts > 1 and ("(" .. table.concat(parts, " & ") .. ")") or parts[1]
        end
    end
    return table.concat(out, " | ")
end

local function questProgressOf(goal, condCtx)
    local out = {}
    if not goal.questID then return out end
    local qt = type(condCtx) == "table" and (condCtx.quests or condCtx.completedQuests) or nil
    if type(qt) == "table" and type(qt[goal.questID]) == "boolean" then
        out.completed = qt[goal.questID]
    end
    local Q = _G.C_QuestLog
    if type(Q) == "table" then
        local probes = {
            { "inLog", "IsOnQuest" },
            { "readyForTurnIn", "ReadyForTurnIn" },
            { "completed", "IsQuestFlaggedCompleted" },
            { "disabled", "IsQuestDisabledForSession" },
        }
        for _, probe in ipairs(probes) do
            if out[probe[1]] == nil then
                local fn = Q[probe[2]]
                if type(fn) == "function" then
                    local ok, v = pcall(fn, goal.questID)
                    if ok and type(v) == "boolean" then out[probe[1]] = v end
                end
            end
        end
    end
    if out.completed == nil and type(_G.IsQuestFlaggedCompleted) == "function" then
        local ok, v = pcall(_G.IsQuestFlaggedCompleted, goal.questID)
        if ok and type(v) == "boolean" then out.completed = v end
    end
    local groups = goal.prerequisiteQuestGroups
    if not out.completed and not out.inLog and type(groups) == "table" and #groups > 0 then
        local Cond = getCond()
        out.prerequisiteGroups = {}
        if Cond and type(Cond.EvaluateQuestGroups) == "function" then
            for i, grp in ipairs(groups) do
                out.prerequisiteGroups[i] = Cond.EvaluateQuestGroups({ grp }, condCtx)
            end
            out.prerequisitesComplete = Cond.EvaluateQuestGroups(groups, condCtx)
        end
    end
    return out
end

function G.SpecAbilityFingerprint(abilities)
    ensureAbilities()
    local parts = {}
    for _, id in ipairs(SPEC_ABILITIES) do
        local v = abilities and abilities[id]
        if v == true then
            parts[#parts + 1] = id .. "=1"
        elseif v == false then
            parts[#parts + 1] = id .. "=0"
        else
            parts[#parts + 1] = id .. "=?"
        end
    end
    return table.concat(parts, ";")
end

local function computeSpecFingerprint(choice, abilities, profession, choicesByGroup)
    ensureAbilities()
    local DS = getDS()
    local cv = DS and type(DS.ContractVersion) == "function" and DS.ContractVersion() or 0
    local fp = DS and type(DS.Fingerprint) == "function" and DS.Fingerprint() or ""
    local skills = type(abilities) == "table" and abilities or G.Abilities()
    local skillSig = G.SpecAbilityFingerprint(skills)
    local groupParts = {}
    local seen = {}
    if type(choicesByGroup) == "table" then
        for grp, v in pairs(choicesByGroup) do
            seen[grp] = true
            groupParts[#groupParts + 1] = tostring(grp) .. "=" .. tostring(v or "none")
        end
    end
    for grp in pairs(SPEC_BY_GROUP) do
        if not seen[grp] then
            local v = (grp == "engineering" and choice) or G.EffectiveChoice(grp, skills)
            groupParts[#groupParts + 1] = tostring(grp) .. "=" .. tostring(v or "none")
        end
    end
    table.sort(groupParts)
    return table.concat({
        "2",
        tostring(cv or 0),
        tostring(fp or ""),
        tostring(profession or ""),
        tostring(choice or "none"),
        table.concat(groupParts, ","),
        skillSig,
    }, ":")
end

local function specFingerprintEntry(choice, abilities, profession, choicesByGroup)
    if G.SpecFingerprint == specFingerprintEntry then
        local E = getEconomy()
        if E and type(E.HookGates) == "function" then
            pcall(E.HookGates)
            if G.SpecFingerprint ~= specFingerprintEntry and type(G.SpecFingerprint) == "function" then
                return G.SpecFingerprint(choice, abilities, profession, choicesByGroup)
            end
        end
    end
    return computeSpecFingerprint(choice, abilities, profession, choicesByGroup)
end

G.SpecFingerprint = specFingerprintEntry

function G.SpecializationContext(opts)
    ensureAbilities()
    opts = opts or {}
    local injected = opts.snapshot
    local hasSnap = type(injected) == "table"
    local prior = hasSnap and injected.specializationContext or nil
    local profession = opts.profession or (hasSnap and injected.targetProfession) or "engineering"

    local supplied
    if type(opts.abilities) == "table" then
        supplied = opts.abilities
    elseif hasSnap then
        supplied = injected.specializationAbilities or (prior and prior.abilities)
    end
    local abilities = {}
    for _, id in ipairs(SPEC_ABILITIES) do
        local v
        if supplied then
            v = supplied[id]
        else
            v = G.Abilities()[id]
        end
        if type(v) == "boolean" then abilities[id] = v end
    end

    local groups = GROUPS_BY_PROF[profession] or {}
    local primaryGroup = resolveGroup(profession)
    local choicesByGroup, actualByGroup = {}, {}

    for _, grp in ipairs(groups) do
        local actual = G.LearnedChoice(grp, abilities)
        actualByGroup[grp] = actual
        local planned
        if type(opts.choicesByGroup) == "table" and opts.choicesByGroup[grp] ~= nil then
            planned = opts.choicesByGroup[grp]
        elseif hasSnap and type(injected.specializationChoices) == "table" and injected.specializationChoices[grp] ~= nil then
            planned = injected.specializationChoices[grp]
        elseif grp == "engineering" then
            planned = opts.engineeringSpecialization or opts.choice or (prior and prior.choice) or (hasSnap and injected.engineeringSpecialization)
        end
        if not findSpec(grp, planned) and planned ~= "none" then
            planned = G.EffectiveChoice(grp, abilities)
        end
        choicesByGroup[grp] = planned or "none"
    end

    local primaryChoice = choicesByGroup[primaryGroup] or "none"
    local primaryActual = actualByGroup[primaryGroup] or "none"
    local selectionConflict = false
    for _, grp in ipairs(groups) do
        local actual = actualByGroup[grp]
        local planned = choicesByGroup[grp]
        if actual == "conflict" or (planned ~= "none" and actual ~= "none" and actual ~= "unknown" and actual ~= planned) then
            selectionConflict = true
            break
        end
    end
    if not selectionConflict and profession == "blacksmithing" then
        local bsPlanned, bsActual = choicesByGroup.blacksmithing, actualByGroup.blacksmithing
        local subPlanned, subActual = choicesByGroup.blacksmithing_weaponsmith, actualByGroup.blacksmithing_weaponsmith
        local armorsmithActive = (bsPlanned == "armorsmith" or bsActual == "armorsmith")
        local subActive = (subPlanned and subPlanned ~= "none") or (subActual and subActual ~= "none" and subActual ~= "unknown")
        if armorsmithActive and subActive then
            selectionConflict = true
        end
    end

    local rawFaction = opts.faction
    if rawFaction == nil and hasSnap then rawFaction = injected.faction end
    local faction = (rawFaction ~= nil and (normalizeFaction(rawFaction) or rawFaction)) or G.FactionCode()
    local level = opts.level or (hasSnap and injected.level)
    if level == nil and type(_G.UnitLevel) == "function" then
        local ok, lvl = pcall(_G.UnitLevel, "player")
        if ok and type(lvl) == "number" and lvl > 0 then level = lvl end
    end

    local Cond = getCond()
    local condCtx = (Cond and type(Cond.LiveContext) == "function" and Cond.LiveContext()) or {}
    if faction ~= nil then condCtx.faction = faction end
    if type(level) == "number" then condCtx.level = level end
    condCtx.abilities = abilities
    if type(opts.quests) == "table" or type(opts.completedQuests) == "table" then
        condCtx.quests = opts.quests or opts.completedQuests
    elseif hasSnap and type(injected.completedQuests or injected.quests) == "table" then
        condCtx.quests = injected.completedQuests or injected.quests
    end
    if type(opts.items) == "table" or type(opts.ownedSourceItems) == "table" then
        condCtx.items = opts.items or opts.ownedSourceItems
    elseif hasSnap and type(injected.ownedSourceItems or injected.items) == "table" then
        condCtx.items = injected.ownedSourceItems or injected.items
    end
    if type(opts.reputations) == "table" then
        condCtx.reputations = opts.reputations
    elseif hasSnap and type(injected.reputations) == "table" then
        condCtx.reputations = injected.reputations
    end
    if opts.strict ~= nil then condCtx.strict = opts.strict == true end

    local solverCfg = getSolverCfg()
    local target = tonumber(opts.target) or (hasSnap and tonumber(injected.target)) or 0
    local ctx = {
        choice = primaryChoice,
        actual = primaryActual,
        choicesByGroup = choicesByGroup,
        actualByGroup = actualByGroup,
        abilities = abilities,
        goals = {},
        profession = profession,
        faction = faction,
        level = level,
        selectionConflict = selectionConflict,
        reason = selectionConflict and "specializationChoiceConflict" or nil,
    }

    if not selectionConflict then
        for _, grp in ipairs(groups) do
            local planned = choicesByGroup[grp]
            local spec = findSpec(grp, planned)
            if spec and target >= (spec.minSkill or 200) then
                local goal = buildSpecGoal(spec, faction)
                if not goal.blockedReason then
                    if abilities[goal.abilityID] == nil then goal.abilityUnknown = true end
                    if Cond and type(Cond.EvaluateAll) == "function" and goal.minLevel then
                        local lvlRes = Cond.EvaluateAll({ { kind = "level", min = goal.minLevel } }, condCtx)
                        if lvlRes == false then
                            goal.blockedReason = "specializationLevelRequired"
                        elseif lvlRes == nil and type(level) ~= "number" and condCtx.strict then
                            goal.blockedReason = "specializationLevelUnknown"
                        end
                    elseif type(level) == "number" and goal.minLevel and level < goal.minLevel then
                        goal.blockedReason = "specializationLevelRequired"
                    end
                    if not goal.blockedReason and goal.npcID and Cond and type(Cond.NpcAccessState) == "function" then
                        local DS = getDS()
                        if DS and type(DS.Npc) == "function" and DS.Npc(goal.npcID) then
                            local npcRes = Cond.NpcAccessState(goal.npcID, condCtx)
                            if npcRes == false then
                                goal.blockedReason = "specializationNpcLocked"
                            end
                        end
                    end
                    local progress = questProgressOf(goal, condCtx)
                    goal.questProgress = progress
                    goal.questCompleted = progress.completed
                    if progress.disabled == true then
                        goal.blockedReason = "specializationQuestDisabled"
                    end
                    if goal.questCompleted and abilities[goal.abilityID] ~= true then
                        goal.blockedReason = "specializationQuestAlreadyCompleted"
                    end
                end
                if goal.blockedReason == "specializationQuestAlreadyCompleted" then
                    ctx.unresolvedGoals = ctx.unresolvedGoals or {}
                    ctx.unresolvedGoals[#ctx.unresolvedGoals + 1] = goal
                    ctx.warnings = ctx.warnings or {}
                    ctx.warnings[#ctx.warnings + 1] = {
                        code = "specializationQuestAlreadyCompleted",
                        profession = profession,
                        questID = goal.questID,
                        abilityID = goal.abilityID,
                        goalID = goal.id,
                    }
                else
                    ctx.goals[#ctx.goals + 1] = goal
                end
            end
        end
    end

    ctx.abilityFingerprint = G.SpecAbilityFingerprint(abilities)
    ctx.fingerprint = G.SpecFingerprint(primaryChoice, abilities, profession, choicesByGroup)
    return ctx
end

function G.SpecGoal(slug, target, opts)
    ensureAbilities()
    local groups = GROUPS_BY_PROF[slug]
    if type(groups) ~= "table" or #groups == 0 then return nil end
    local solverCfg = getSolverCfg()
    local target0 = tonumber(target) or (type(solverCfg) == "table" and solverCfg.DEFAULT_TARGET) or 300
    local abilities = G.Abilities()
    local rawFaction = type(opts) == "table" and opts.faction or nil
    local faction = (rawFaction ~= nil and (normalizeFaction(rawFaction) or rawFaction)) or G.FactionCode()
    for _, grp in ipairs(groups) do
        local actual = G.LearnedChoice(grp, abilities)
        local planned = G.EffectiveChoice(grp, abilities)
        if (actual == "none" or actual == "unknown") and planned ~= "none" then
            if grp == "blacksmithing_weaponsmith" and (G.EffectiveChoice("blacksmithing", abilities) == "armorsmith" or G.LearnedChoice("blacksmithing", abilities) == "armorsmith") then
                return nil
            end
            local spec = findSpec(grp, planned)
            if spec and target0 >= (spec.minSkill or 200) then
                local goal = buildSpecGoal(spec, faction)
                local progress = questProgressOf(goal, opts)
                goal.questProgress = progress
                goal.questCompleted = progress.completed
                if not goal.blockedReason and progress.completed ~= true and progress.disabled ~= true then
                    return goal
                end
            end
        end
    end
    return nil
end

function G.ToolGoals(slug, target)
    local DS = getDS()
    local tools = DS and type(DS.Tools) == "function" and DS.Tools() or nil
    if type(tools) ~= "table" then return {} end
    local solverCfg = getSolverCfg()
    local target0 = tonumber(target) or (type(solverCfg) == "table" and solverCfg.DEFAULT_TARGET) or 300
    local matched = {}
    for _, tool in pairs(tools) do
        if type(tool) == "table" and tool.profession == slug and target0 > (tool.minSkill or 300) then
            matched[#matched + 1] = tool
        end
    end
    table.sort(matched, function(a, b)
        local ma, mb = a.minSkill or 0, b.minSkill or 0
        if ma ~= mb then return ma < mb end
        local ta, tb = a.tier or 0, b.tier or 0
        if ta ~= tb then return ta < tb end
        return (a.itemID or 0) < (b.itemID or 0)
    end)
    local out = {}
    for i = 1, #matched do
        local t = matched[i]
        out[i] = {
            id = slug .. ":" .. tostring(t.itemID),
            profession = slug,
            spell = t.craftSpellID,
            craftSpellID = t.craftSpellID,
            item = t.itemID,
            itemID = t.itemID,
            minSkill = t.minSkill,
            bindOnPickup = t.bindOnPickup,
            toolCategory = t.toolCategory,
            tier = t.tier,
        }
    end
    return out
end

local function toolItemOwned(itemID)
    if type(_G.C_Item) == "table" and type(_G.C_Item.GetItemCount) == "function" then
        local ok, n = pcall(_G.C_Item.GetItemCount, itemID, true)
        if ok and type(n) == "number" and n > 0 then return true end
    end
    if type(_G.GetItemCount) == "function" then
        local ok, n = pcall(_G.GetItemCount, itemID, true)
        if ok and type(n) == "number" and n > 0 then return true end
    end
    return false
end

function G.ToolOwned(itemID)
    if type(itemID) ~= "number" or itemID <= 0 then return false end
    if toolItemOwned(itemID) then return true end
    local DS = getDS()
    local tool = DS and type(DS.Tool) == "function" and DS.Tool(itemID) or nil
    if type(tool) == "table" and type(tool.toolCategory) == "string" and type(tool.tier) == "number" then
        local tools = DS and type(DS.Tools) == "function" and DS.Tools() or {}
        for _, cand in pairs(tools) do
            if type(cand) == "table"
                and cand.profession == tool.profession
                and cand.toolCategory == tool.toolCategory
                and (cand.tier or 0) > tool.tier
                and toolItemOwned(cand.itemID) then
                return true
            end
        end
    end
    return false
end

function G.AutoCraftTools(slug)
    local v = getSettingRaw("autoCraftTools", slug)
    if v ~= nil then return v ~= false end
    return true
end

function G.ToolItemSet(slug)
    local DS = getDS()
    local tools = DS and type(DS.Tools) == "function" and DS.Tools() or nil
    local set = {}
    if type(tools) == "table" then
        for _, tool in pairs(tools) do
            if type(tool) == "table" and tool.profession == slug and type(tool.itemID) == "number" then
                set[tool.itemID] = true
            end
        end
    end
    return set
end
