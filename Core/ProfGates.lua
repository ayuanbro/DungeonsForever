local _, ns = ...

if not ns.LoadForeverPages then return end

local G = {}
ns.ProfGates = G

local floor, max = math.floor, math.max

local SPEC_ABILITIES = { 20219, 20222, 9787, 9788, 17039, 17040, 17041, 10656, 10658, 10660 }
G.SpecAbilities = SPEC_ABILITIES

local cache
local function spellKnown(spell)
    for _, name in ipairs({ "C_SpellBook.IsSpellKnown", "IsSpellKnown", "IsPlayerSpell", "C_Spell.IsSpellKnown" }) do
        local parent, key = name:match("^([^.]+)%.(.+)$")
        local fn = parent and _G[parent] and _G[parent][key] or (not parent and _G[name])
        if type(fn) == "function" then
            local ok, value = pcall(fn, spell)
            if ok and type(value) == "boolean" then return value end
        end
    end
end

function G.Invalidate()
    cache = nil
end

function G.Abilities()
    if cache then return cache end
    local out = {}
    for _, id in ipairs(SPEC_ABILITIES) do
        local v = spellKnown(id)
        if type(v) == "boolean" then out[id] = v end
    end
    cache = out
    return out
end

local SPEC_NAMES = {
    [20219] = "侏儒工程学",
    [20222] = "地精工程学",
    [9787] = "护甲锻造",
    [9788] = "武器锻造",
    [17039] = "铸剑大师",
    [17040] = "铸斧大师",
    [17041] = "铸锤大师",
    [10656] = "龙鳞制皮",
    [10658] = "元素制皮",
    [10660] = "部族制皮",
}

function G.AbilityLabel(id)
    local L = ns.L
    local key = SPEC_NAMES[id]
    return key and L[key] or tostring(id)
end

local function SpecRec(spell)
    return ns.ProfSpecializations and ns.ProfSpecializations[spell]
end

local function SpecFlags(rec)
    return (type(rec) == "table" and tonumber(rec[1])) or 0
end

local function SpecAbility(rec)
    return (type(rec) == "table" and tonumber(rec[2])) or 0
end

function G.TrainerFlag(spell)
    return SpecFlags(SpecRec(spell)) % 2 >= 1
end

function G.ItemFlag(spell)
    return SpecFlags(SpecRec(spell)) % 4 >= 2
end

function G.RequiredAbility(spell)
    return SpecAbility(SpecRec(spell))
end

function G.HasPending(spell)
    return SpecFlags(SpecRec(spell)) % 8 >= 4
end

function G.Allowed(slug, spell)
    local ability = SpecAbility(SpecRec(spell))
    if ability == 0 then return true end
    local v = G.Abilities()[ability]
    if v == true or v == nil then return true end
    return false, G.AbilityLabel(ability)
end

function G.TrainerTaught(spell)
    return G.TrainerFlag(spell)
end

function G.ItemTaught(spell)
    return G.ItemFlag(spell)
end

function G.LearningSource(spell)
    if G.TrainerFlag(spell) then return "trainer" end
    if G.ItemFlag(spell) then return "item" end
    return nil
end

function G.LearningEligibility(spell)
    local rec = SpecRec(spell)
    if not rec then return true, nil, { status = "unknown" } end
    local hp = G.HasPending(spell) or nil
    local ability = SpecAbility(rec)
    if ability == 0 then
        return true, nil, { status = G.LearningSource(spell) and "allowed" or "unknown", hasPending = hp }
    end
    local v = G.Abilities()[ability]
    if v == true then return true, nil, { status = "allowed", hasPending = hp, ability = ability } end
    if v == nil then return true, nil, { status = "unknown", hasPending = hp, ability = ability } end
    return false, G.AbilityLabel(ability), { status = "blocked", hasPending = hp, ability = ability }
end

function G.SpecFingerprint(choice)
    local meta = ns.ProfSpecializationsMeta or {}
    local q = ns.ProfSpecializationQuestMeta or {}
    return table.concat({ "1", tostring(choice or "none"), tostring(meta.revision or 0),
        tostring(meta.fpr or ""), tostring(q.revision or 0), tostring(q.sourceCommit or "") }, ":")
end

function G.EngineeringChoice()
    local abilities = G.Abilities()
    local gn, gob = abilities[20219], abilities[20222]
    if gn and gob then return "conflict" end
    if gn then return "gnomish" end
    if gob then return "goblin" end
    if gn == false and gob == false then return "none" end
    return "unknown"
end

function G.FactionCode()
    local f = UnitFactionGroup and UnitFactionGroup("player") or nil
    if f == "Alliance" then return "A" end
    if f == "Horde" then return "H" end
end

local function cloneInputs(list)
    local out = {}
    for _, v in ipairs(list or {}) do out[#out + 1] = { v[1], v[2] } end
    return out
end

local ENG_CHOICES = { none = true, goblin = true, gnomish = true }

function G.GetPlannedChoice()
    local db = DungeonsForeverDB and DungeonsForeverDB.prof
    local v = db and db.engChoice
    if ENG_CHOICES[v] then return v end
    return "none"
end

function G.SetPlannedChoice(value)
    if not ENG_CHOICES[value] then return false end
    DungeonsForeverDB = DungeonsForeverDB or {}
    DungeonsForeverDB.prof = DungeonsForeverDB.prof or {}
    if G.GetPlannedChoice() == value then return true end
    if value == "none" then
        DungeonsForeverDB.prof.engChoice = nil
    else
        DungeonsForeverDB.prof.engChoice = value
    end
    G.Invalidate()
    local RA = ns.ProfRouteAuto
    if RA and RA.Invalidate then RA.Invalidate("specialization") end
    return true
end

local function buildSpecGoal(def, faction)
    local goal = {}
    for k, v in pairs(def) do
        if k ~= "variants" then goal[k] = v end
    end
    goal.inputs = cloneInputs(def.inputs)
    local variant = def.variants and faction and def.variants[faction]
    if variant then
        for k, v in pairs(variant) do goal[k] = v end
    elseif def.variants then
        goal.blockedReason = "specializationFactionUnknown"
    end
    local prerequisites = {}
    for _, id in ipairs(goal.prerequisiteQuestIDs or {}) do prerequisites[#prerequisites+1] = id end
    goal.prerequisiteQuestIDs = prerequisites
    return goal
end

local function questProgressOf(goal)
    local out = {}
    if not goal.questID then return out end
    local Q = C_QuestLog
    if type(Q) ~= "table" then return out end
    local probes = { { "inLog", "IsOnQuest" }, { "readyForTurnIn", "ReadyForTurnIn" },
        { "completed", "IsQuestFlaggedCompleted" }, { "disabled", "IsQuestDisabledForSession" } }
    for _, probe in ipairs(probes) do
        local fn = Q[probe[2]]
        if type(fn) == "function" then
            local ok, v = pcall(fn, goal.questID)
            if ok and type(v) == "boolean" then out[probe[1]] = v end
        end
    end
    return out
end

function G.SpecAbilityFingerprint(abilities)
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

function G.SpecializationContext(opts)
    opts = opts or {}
    local injected = opts.snapshot
    local hasSnap = type(injected) == "table"
    local prior = hasSnap and injected.specializationContext or nil
    local choice = opts.engineeringSpecialization or (prior and prior.choice)
    if not choice and hasSnap then choice = injected.engineeringSpecialization end
    if not choice then choice = G.GetPlannedChoice() end
    if not ENG_CHOICES[choice] then choice = "none" end
    local supplied
    if hasSnap then supplied = injected.specializationAbilities or (prior and prior.abilities) end
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
    local actual = "unknown"
    local gn, gob = abilities[20219], abilities[20222]
    if gn and gob then
        actual = "conflict"
    elseif gn then
        actual = "gnomish"
    elseif gob then
        actual = "goblin"
    elseif gn == false and gob == false then
        actual = "none"
    end
    local profession = opts.profession or (hasSnap and injected.targetProfession) or "engineering"
    local ctx = { choice = choice, actual = actual, abilities = abilities, goals = {}, profession = profession }
    ctx.selectionConflict = (actual == "conflict")
        or (choice ~= "none" and actual ~= "none" and actual ~= "unknown" and actual ~= choice)
    if ctx.selectionConflict then ctx.reason = "specializationChoiceConflict" end
    local faction = opts.faction or (hasSnap and injected.faction) or G.FactionCode()
    local level = opts.level or (hasSnap and injected.level) or (UnitLevel and UnitLevel("player"))
    ctx.faction, ctx.level = faction, level
    local target = tonumber(opts.target) or (hasSnap and injected.target) or 0
    local def = ns.ProfSpecializationQuests and ns.ProfSpecializationQuests[choice]
    if profession == "engineering" and def and not ctx.selectionConflict and target >= (def.minSkill or 200) then
        local goal = buildSpecGoal(def, faction)
        if not goal.blockedReason then
            if abilities[goal.abilityID] == nil then goal.abilityUnknown = true end
            if type(level) == "number" and goal.minLevel and level < goal.minLevel then
                goal.blockedReason = "specializationLevelRequired"
            end
            local progress = questProgressOf(goal)
            goal.questProgress = progress
            goal.questCompleted = progress.completed
            if progress.disabled == true then goal.blockedReason = "specializationQuestDisabled" end
            if goal.questCompleted and abilities[goal.abilityID] ~= true then
                goal.blockedReason = "specializationQuestAlreadyCompleted"
            end
        end
        if goal.blockedReason=="specializationQuestAlreadyCompleted" then
            -- A completed introduction cannot be performed again. Keep the
            -- unresolved specialization visible, but do not stop ordinary
            -- engineering leveling at 200. Quest completion is not evidence
            -- that the specialization ability is currently learned.
            ctx.unresolvedGoals={goal}
            ctx.warnings={{code="specializationQuestAlreadyCompleted",profession=profession,
                questID=goal.questID,abilityID=goal.abilityID,goalID=goal.id}}
        else
            -- Missing faction facts still block an uncompleted selected task.
            ctx.goals[1] = goal
        end
    end
    ctx.fingerprint = G.SpecFingerprint(choice)
    ctx.abilityFingerprint = G.SpecAbilityFingerprint(abilities)
    return ctx
end

function G.SpecGoal(slug, target)
    if slug ~= "engineering" then return nil end
    local target0 = tonumber(target) or 300
    local source = ns.ProfSpecializationQuests
    if not source then return nil end
    local actual = G.EngineeringChoice()
    if actual == "conflict" then return nil end
    local planned = G.GetPlannedChoice()
    if planned ~= "none" then
        if actual == planned then return nil end
        local def = source[planned]
        if not def or target0 < (def.minSkill or 200) then return nil end
        local goal = buildSpecGoal(def, G.FactionCode())
        if goal.blockedReason then return nil end
        if questProgressOf(goal).completed==true then return nil end
        return goal
    end
    if actual == "gnomish" or actual == "goblin" then return nil end
    if target0 < 200 then return nil end
    local faction = G.FactionCode()
    local best
    for _, def in pairs(source) do
        if def.profession == slug then
            local goal = buildSpecGoal(def, faction)
            if not goal.blockedReason and questProgressOf(goal).completed~=true then
                if not best or (goal.minSkill or 0) < (best.minSkill or 0) then best = goal end
            end
        end
    end
    return best
end

function G.ToolGoals(slug, target)
    local data = ns.ProfTools
    if not data then return {} end
    local target0 = tonumber(target) or 300
    local out = {}
    for _, tool in ipairs(data[slug] or {}) do
        if target0 > (tool.minSkill or 300) then
            out[#out + 1] = {
                id = slug .. ":" .. tostring(tool.item),
                profession = slug, spell = tool.spell, item = tool.item,
                minSkill = tool.minSkill, bindOnPickup = tool.bindOnPickup,
            }
        end
    end
    return out
end

function G.ToolOwned(itemID)
    if type(C_Item) == "table" and type(C_Item.GetItemCount) == "function" then
        local ok, n = pcall(C_Item.GetItemCount, itemID, true)
        if ok and type(n) == "number" and n > 0 then return true end
    end
    if type(GetItemCount) == "function" then
        local ok, n = pcall(GetItemCount, itemID, true)
        if ok and type(n) == "number" and n > 0 then return true end
    end
    return false
end

function G.AutoCraftTools(slug)
    local view=ns.ProfModule
    if view and view.SettingRaw then
        local value=view.SettingRaw("autoCraftTools",slug)
        if value~=nil then return value~=false end
    end
    local db = DungeonsForeverDB and DungeonsForeverDB.prof
    return not (db and db.autoCraftTools == false)
end

function G.ToolItemSet(slug)
    local set = {}
    for _, tool in ipairs((ns.ProfTools and ns.ProfTools[slug]) or {}) do set[tool.item] = true end
    return set
end
