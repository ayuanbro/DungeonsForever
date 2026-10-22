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
        local fn = _G[name]
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

function G.Allowed(slug, spell)
    local rec = ns.ProfSpecializations and ns.ProfSpecializations[spell]
    if not rec or not rec.a then return true end
    local abilities = G.Abilities()
    local known, unknown = false, false
    for _, id in ipairs(rec.a) do
        local v = abilities[id]
        if v == true then return true end
        if v == nil then unknown = true else known = true end
    end
    if unknown then return true end
    if known then
        local names = {}
        for _, id in ipairs(rec.a) do names[#names + 1] = G.AbilityLabel(id) end
        return false, table.concat(names, " / ")
    end
    return true
end

function G.TrainerTaught(spell)
    local rec = ns.ProfSpecializations and ns.ProfSpecializations[spell]
    return (rec and rec.k == "trainer") and true or false
end

function G.ItemTaught(spell)
    local rec = ns.ProfSpecializations and ns.ProfSpecializations[spell]
    return (rec and rec.k == "item") or false
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

function G.SpecGoal(slug, target)
    if slug ~= "engineering" then return nil end
    local choice = G.EngineeringChoice()
    if choice == "gnomish" or choice == "goblin" or choice == "conflict" then return nil end
    local target0 = tonumber(target) or 300
    if target0 < 200 then return nil end
    local source = ns.ProfSpecializationQuests
    if not source then return nil end
    local faction = G.FactionCode()
    local best
    for _, def in pairs(source) do
        if def.profession == slug then
            local goal = {}
            for k, v in pairs(def) do goal[k] = v end
            goal.inputs = cloneInputs(def.inputs)
            local variant = def.variants and faction and def.variants[faction]
            if variant then
                for k, v in pairs(variant) do goal[k] = v end
            elseif def.variants then
                goal = nil
            end
            if goal then
                goal.variants = nil
                goal.prerequisiteQuestIDs = nil
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

function G.AutoCraftTools()
    local db = DungeonsForeverDB and DungeonsForeverDB.prof
    return not (db and db.autoCraftTools == false)
end

function G.ToolItemSet(slug)
    local set = {}
    for _, tool in ipairs((ns.ProfTools and ns.ProfTools[slug]) or {}) do set[tool.item] = true end
    return set
end
