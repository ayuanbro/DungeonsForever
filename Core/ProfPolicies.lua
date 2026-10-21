local _, ns = ...

if not ns.LoadForeverPages then return end

local P = {}
ns.ProfEconomy = P

local drafts = {}

local function store()
    DungeonsForeverDB = DungeonsForeverDB or {}
    local d = DungeonsForeverDB
    d.prof = d.prof or {}
    d.prof.policies = d.prof.policies or {}
    return d.prof.policies
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
    if ns.ProfRouteAuto and ns.ProfRouteAuto.Invalidate then ns.ProfRouteAuto.Invalidate() end
end

function P.ResetPolicies(slug)
    drafts[slug] = {}
end

function P.HasDraft(slug)
    return drafts[slug] ~= nil
end

function P.Policy(policies, r)
    if not policies or not r then return nil end
    local key = r.key
    if not key and r.profession then key = tostring(r.profession) .. ":" .. tostring(r.spell) end
    return (key and policies[key]) or policies[r.spell]
end

function P.PolicyFingerprint(t)
    local keys = {}
    for k, v in pairs(t or {}) do keys[#keys + 1] = tostring(k) .. "=" .. tostring(v) end
    table.sort(keys)
    return table.concat(keys, ";")
end
