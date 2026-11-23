local _, ns = ...
if type(ns) ~= "table" then ns = _G.DF_NS or {} end
local gns = _G.DF_NS

local P = ns.ProfEconomy or (type(gns) == "table" and gns.ProfEconomy) or {}
ns.ProfEconomy = P
if type(gns) == "table" and gns ~= ns then
    gns.ProfEconomy = P
end

local function getDS()
    return ns.ProfDataStore or (type(gns) == "table" and gns.ProfDataStore) or nil
end

local function getDataRoot()
    return ns.Data or (type(gns) == "table" and gns.Data) or nil
end

local function getDB()
    return ns.ProfDB or (type(gns) == "table" and gns.ProfDB) or nil
end

local function getRouteAuto()
    return ns.ProfRouteAuto or (type(gns) == "table" and gns.ProfRouteAuto) or nil
end

function P.RecipeNIP(spell, recipe)
    if type(recipe) == "table" then
        if recipe.availability ~= nil then
            return recipe.availability ~= "live"
        end
        if recipe.nip == true then
            return true
        end
    end
    local id = spell
    if id == nil and type(recipe) == "table" then
        id = recipe.spellID or recipe.spell or recipe[1]
    end
    if type(id) == "number" and id > 0 then
        local DS = getDS()
        if DS and type(DS.Recipe) == "function" then
            local rec = DS.Recipe(id)
            if type(rec) == "table" then
                return rec.availability ~= "live"
            end
        end
        local root = getDataRoot()
        if type(root) == "table" and type(root.recipes) == "table" then
            for _, bucket in pairs(root.recipes) do
                if type(bucket) == "table" and type(bucket.recipes) == "table" then
                    local rec = bucket.recipes[id]
                    if type(rec) == "table" then
                        return rec.availability ~= "live"
                    end
                end
            end
        end
    end
    return false
end

function P.StepsHaveNIP(steps)
    for _, step in ipairs(steps or {}) do
        if type(step) == "table"
            and not step.checkpoint
            and step.kind ~= "specialization_quest"
            and step.kind ~= "essence_conversion"
            and step.kind ~= "conversion" then
            if (step.availability ~= nil and step.availability ~= "live")
                or step.nip == true
                or P.RecipeNIP(step.spell or step.spellID or step[3], step.recipe) then
                return true
            end
        end
    end
    return false
end

local drafts = {}

local function store()
    local dbFn = getDB()
    if not dbFn then return {} end
    local db = dbFn()
    if type(db) ~= "table" then return {} end
    if type(db.prof) ~= "table" then db.prof = {} end
    if type(db.prof.policies) ~= "table" then db.prof.policies = {} end
    return db.prof.policies
end

local function copy(t)
    local o = {}
    for k, v in pairs(t or {}) do o[k] = v end
    return o
end

function P.GetPolicies(slug, draft)
    local all = store()
    if draft then
        if not drafts[slug] then drafts[slug] = copy(all[slug]) end
        return drafts[slug]
    end
    all[slug] = all[slug] or {}
    return all[slug]
end

P.Policies = P.GetPolicies

function P.SetPolicy(slug, profession, spell, mode, draft)
    if mode ~= "ban" then mode = nil end
    local key = tostring(profession) .. ":" .. tostring(spell)
    if draft ~= false then
        P.GetPolicies(slug, true)[key] = mode
    else
        local all = store()
        all[slug] = all[slug] or {}
        all[slug][key] = mode
        drafts[slug] = nil
    end
end

function P.ApplyPolicies(slug)
    if drafts[slug] then
        local all = store()
        all[slug] = copy(drafts[slug])
        drafts[slug] = nil
    end
    local ra = getRouteAuto()
    if ra and type(ra.Invalidate) == "function" then
        pcall(ra.Invalidate)
    end
end

function P.ResetPolicies(slug)
    drafts[slug] = {}
end

function P.HasDraft(slug)
    return drafts[slug] ~= nil
end

function P.Policy(policies, r)
    if not policies or not r then return nil end
    local spell = r.spell or r.spellID
    local key = r.key
    if not key and r.profession and spell ~= nil then
        key = tostring(r.profession) .. ":" .. tostring(spell)
    end
    return (key and policies[key]) or (spell ~= nil and policies[spell]) or nil
end

function P.PolicyFingerprint(t)
    local keys = {}
    for k, v in pairs(t or {}) do keys[#keys + 1] = tostring(k) .. "=" .. tostring(v) end
    table.sort(keys)
    return table.concat(keys, ";")
end
