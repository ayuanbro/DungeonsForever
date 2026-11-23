local _, ns = ...
if type(ns) ~= "table" then ns = _G.DF_NS or {} end
local gns = _G.DF_NS

local E = ns.ProfEconomy or (type(gns) == "table" and gns.ProfEconomy) or {}
ns.ProfEconomy = E
if type(gns) == "table" and gns ~= ns then
    gns.ProfEconomy = E
end

local activeScans = {}
local fallbackStore = {}
local floor = math.floor

local function getDS()
    return ns.ProfDataStore or (type(gns) == "table" and gns.ProfDataStore) or nil
end

local function getCond()
    return ns.ProfConditions or (type(gns) == "table" and gns.ProfConditions) or nil
end

local function getDataRoot()
    return ns.Data or (type(gns) == "table" and gns.Data) or nil
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

local function getGates()
    return ns.ProfGates or (type(gns) == "table" and gns.ProfGates) or nil
end

local function getCDWatch()
    return ns.ProfCDWatch or (type(gns) == "table" and gns.ProfCDWatch) or nil
end

local function getIdle()
    return ns.ProfIdle or (type(gns) == "table" and gns.ProfIdle) or nil
end

local function getTracking()
    return ns.ProfessionTracking or (type(gns) == "table" and gns.ProfessionTracking) or nil
end

local function getModule()
    return ns.ProfModule or (type(gns) == "table" and gns.ProfModule) or nil
end

local function deepCopy(value, tick, seen, overrides)
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
            if overrides[k] == nil then out[k] = deepCopy(v, tick, seen) end
            count = count + 1
            if tick and count % 64 == 0 then tick() end
        end
        for k, v in pairs(overrides) do out[k] = v end
        return out
    end
    for k, v in pairs(value) do
        out[k] = deepCopy(v, tick, seen)
        count = count + 1
        if tick and count % 64 == 0 then tick() end
    end
    return out
end

if type(E.Copy) ~= "function" then
    E.Copy = function(value, tick, overrides)
        return type(value) == "table" and deepCopy(value, tick, nil, overrides) or {}
    end
end

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

function E.ClientStore()
    local db = getDB()
    if type(db) == "table" and type(db.CharacterStore) == "function" then
        local store = db.CharacterStore("client")
        return store
    end
    if type(db) == "function" then
        local root = db()
        root.client = type(root.client) == "table" and root.client or {}
        local key = E.CharacterKey()
        root.client[key] = type(root.client[key]) == "table" and root.client[key] or {}
        return root.client[key]
    end
    return fallbackStore
end

local function store()
    return E.ClientStore()
end

E.SkillIDs = E.SkillIDs or {}

local function refreshSkillIDs()
    local out = E.SkillIDs
    local cfg = getProfCfg()
    if type(cfg) == "table" and type(cfg.SKILL_LINE_TO_SLUG) == "table" then
        for sid, slug in pairs(cfg.SKILL_LINE_TO_SLUG) do
            out[sid] = slug
        end
    end
    local DS = getDS()
    if DS and type(DS.SkillLines) == "function" then
        for sid, row in pairs(DS.SkillLines()) do
            if type(row) == "table" and type(row.profession) == "string" then
                out[sid] = row.profession
            end
        end
    end
    return out
end

function E.ProfessionSlug(id)
    if type(id) ~= "number" then return nil end
    local DS = getDS()
    if DS and type(DS.SkillLineToSlug) == "function" then
        local slug = DS.SkillLineToSlug(id)
        if slug then
            E.SkillIDs[id] = slug
            return slug
        end
    end
    local cfg = getProfCfg()
    if type(cfg) == "table" and type(cfg.SKILL_LINE_TO_SLUG) == "table" then
        local slug = cfg.SKILL_LINE_TO_SLUG[id]
        if slug then
            E.SkillIDs[id] = slug
            return slug
        end
    end
    refreshSkillIDs()
    return E.SkillIDs[id]
end

local function isPrimarySlug(slug)
    if type(slug) ~= "string" then return false end
    local DS = getDS()
    if DS and type(DS.Profession) == "function" then
        local p = DS.Profession(slug)
        if type(p) == "table" and p.kind ~= nil then
            return p.kind == "primary"
        end
    end
    local cfg = getProfCfg()
    local entry = type(cfg) == "table" and type(cfg.BY_SLUG) == "table" and cfg.BY_SLUG[slug]
    return type(entry) == "table" and entry.navGroup == "primary"
end

function E.Professions()
    local out = {}
    if type(_G.GetProfessions) == "function" and type(_G.GetProfessionInfo) == "function" then
        local ok, a, b, c, d, e, f = pcall(_G.GetProfessions)
        if ok then
            local slots = { a, b, c, d, e, f }
            for i = 1, 6 do
                local idx = slots[i]
                if idx then
                    local oki, _, _, cur, maxRank, _, _, sid = pcall(_G.GetProfessionInfo, idx)
                    local slug = oki and E.ProfessionSlug(sid) or nil
                    if slug then
                        local curVal = tonumber(cur) or 0
                        local maxVal = tonumber(maxRank) or 0
                        local prev = out[slug]
                        if prev then
                            if curVal > prev.cur then
                                prev.cur = curVal
                                prev.skillLineID = sid
                            end
                            if maxVal > prev.max then
                                prev.max = maxVal
                            end
                        else
                            out[slug] = {
                                cur = curVal,
                                max = maxVal,
                                primary = isPrimarySlug(slug),
                                skillLineID = sid,
                            }
                        end
                    end
                end
            end
        end
    end
    return out
end

local function call(name, ...)
    local parent, key = name:match("^([^.]+)%.(.+)$")
    local fn = parent and _G[parent] and _G[parent][key] or (not parent and _G[name])
    if type(fn) ~= "function" then return false end
    return pcall(fn, ...)
end

local function positiveInteger(value)
    return type(value) == "number" and value > 0 and value == floor(value)
end

local function validMaterials(mats)
    if type(mats) ~= "table" then return false end
    for _, m in ipairs(mats) do
        if type(m) ~= "table" or not positiveInteger(m[1]) or not positiveInteger(m[2]) then return false end
    end
    return true
end

local function readOutput(r, lo, hi)
    if not positiveInteger(lo) or hi ~= nil and (not positiveInteger(hi) or hi < lo) then return false end
    r.count = lo
    r.outputMin = lo
    r.outputMax = hi or lo
    r.variableOutput = (hi and hi > lo) or nil
    return true
end

local function runtime()
    local d = store()
    local version, build
    if type(_G.GetBuildInfo) == "function" then
        local ok, v, b = pcall(_G.GetBuildInfo)
        if ok then version, build = v, b end
    end
    local scope = tostring(version or "unknown") .. ":" .. tostring(build or "unknown")
    if d.recipeBuild ~= scope then
        d.recipes = {}
        d.recipeRosters = {}
        d.learningRequirements = {}
        d.recipeBuild = scope
        E.observedRankRequirements = nil
    end
    d.recipes = type(d.recipes) == "table" and d.recipes or {}
    ns.ProfRecipeRuntime = d.recipes
    if type(gns) == "table" and gns ~= ns then
        gns.ProfRecipeRuntime = d.recipes
    end
    return d.recipes
end

E.EnsureClientRuntime = runtime

function E.Known(spell)
    if not positiveInteger(spell) then return nil end
    local rt = ns.ProfRecipeRuntime or (type(gns) == "table" and gns.ProfRecipeRuntime)
    if type(rt) == "table" and type(rt[spell]) == "table" and rt[spell].learned == true then
        return true
    end
    local Cond = getCond()
    if Cond and type(Cond.Evaluate) == "function" then
        return Cond.Evaluate({ kind = "ability", spellID = spell })
    end
    local observedFalse = false
    for _, name in ipairs({ "C_SpellBook.IsSpellKnown", "IsSpellKnown", "IsPlayerSpell", "C_Spell.IsSpellKnown" }) do
        local ok, value = call(name, spell)
        if ok and value == true then return true end
        if ok and value == false then observedFalse = true end
    end
    if observedFalse then return false end
    return nil
end

local recipeIDs = {}
local indexed = {}
local indexedMeta = nil

local function syncIndexRoot()
    local DS = getDS()
    local meta = DS and type(DS.Meta) == "function" and DS.Meta() or nil
    if meta ~= indexedMeta then
        indexedMeta = meta
        recipeIDs = {}
        indexed = {}
    end
end

local function indexBucket(slug, bucket)
    if type(slug) ~= "string" or type(bucket) ~= "table" then return end
    if indexed[slug] == bucket then return end
    indexed[slug] = bucket
    for id, rec in pairs(bucket.recipes or {}) do
        if positiveInteger(id) and type(rec) == "table" then
            recipeIDs[id] = (rec.availability == "live") and slug or false
        end
    end
end

local function indexProfession(slug)
    if type(slug) ~= "string" then return end
    syncIndexRoot()
    local DS = getDS()
    if DS and type(DS.Recipes) == "function" then
        local bucket = DS.Recipes(slug)
        if type(bucket) == "table" then
            indexBucket(slug, bucket)
        end
    end
end

local function hasRecipe(spell)
    if not positiveInteger(spell) then return false end
    syncIndexRoot()
    local DS = getDS()
    if DS and type(DS.RecipeProfession) == "function" then
        local slug = DS.RecipeProfession(spell)
        if type(slug) == "string" then
            local rec = DS.Recipe and DS.Recipe(spell)
            return type(rec) == "table" and rec.availability == "live"
        end
    end
    if type(recipeIDs[spell]) == "string" then
        return not (E.RecipeNIP and E.RecipeNIP(spell))
    end
    if recipeIDs[spell] == false then return false end
    for slug in pairs(E.Professions()) do indexProfession(slug) end
    local pd = getModule()
    if pd and pd.cur then indexProfession(pd.cur) end
    local root = getDataRoot()
    if type(root) == "table" and type(root.recipes) == "table" then
        for slug, bucket in pairs(root.recipes) do
            if type(bucket) == "table" then indexBucket(slug, bucket) end
        end
    end
    return type(recipeIDs[spell]) == "string" and not (E.RecipeNIP and E.RecipeNIP(spell))
end

function E.IndexClientProfession(slug)
    indexProfession(slug)
end

local inputFields = {
    "learned", "available", "unavailable", "validated", "trainerObserved", "trainerAvailable",
    "learn", "item", "count", "outputMin", "outputMax", "variableOutput", "cooldown", "cooldownVerified",
}
local notified = setmetatable({}, { __mode = "k" })

local function changedInput()
    local d = store()
    d.clientInputRevision = (tonumber(d.clientInputRevision) or 0) + 1
end

local function recipeBefore(r)
    local before = { mats = r and r.mats }
    for _, key in ipairs(inputFields) do before[key] = r and r[key] end
    return before
end

local function sameMaterials(a, b)
    if a == b then return true end
    if type(a) ~= "table" or type(b) ~= "table" or #a ~= #b then return false end
    for i, row in ipairs(a) do
        local other = b[i]
        if type(row) ~= "table" or type(other) ~= "table" or row[1] ~= other[1] or row[2] ~= other[2] then return false end
    end
    return true
end

local function recipeObserved(before, r)
    local equal = sameMaterials(before.mats, r.mats)
    if equal then r.mats = before.mats end
    for _, key in ipairs(inputFields) do
        if before[key] ~= r[key] then
            equal = false
            break
        end
    end
    if not equal then changedInput() end
end

local function sameProfessions(a, b)
    if type(a) ~= "table" then return false end
    for slug, value in pairs(b) do
        local previous = a[slug]
        if not previous or previous.cur ~= value.cur or previous.max ~= value.max
            or previous.primary ~= value.primary or previous.skillLineID ~= value.skillLineID then
            return false
        end
    end
    for slug in pairs(a) do
        if not b[slug] then return false end
    end
    return true
end

function E.ReadRecipe(spell, observedInfo, infoAlreadyRead)
    if not positiveInteger(spell) or not hasRecipe(spell) then return end
    local api = _G.C_TradeSkillUI
    if type(api) ~= "table" then return end
    local linkedOk, linked = call("C_TradeSkillUI.IsTradeSkillLinked")
    local guildOk, guild = call("C_TradeSkillUI.IsTradeSkillGuild")
    if (linkedOk and linked) or (guildOk and guild) then return end
    local infoOk, info = infoAlreadyRead, observedInfo
    if not infoAlreadyRead then infoOk, info = call("C_TradeSkillUI.GetRecipeInfo", spell) end
    local schematicOk, schematic = call("C_TradeSkillUI.GetRecipeSchematic", spell, false)
    info = infoOk and type(info) == "table" and info or nil
    if info and ((info.recipeID and info.recipeID ~= spell) or (info.spellID and info.spellID ~= spell)) then return end
    if info and not (type(info.learned) == "boolean" or type(info.recipeID) == "number"
        or type(info.spellID) == "number" or (type(info.name) == "string" and info.name ~= "")) then
        info = nil
    end
    schematic = schematicOk and type(schematic) == "table" and schematic or nil
    if schematic and schematic.recipeID and schematic.recipeID ~= spell then return end
    if schematic and not (info or (type(schematic.name) == "string" and schematic.name ~= "")
        or (type(schematic.outputItemID) == "number" and schematic.outputItemID > 0)
        or (type(schematic.quantityMin) == "number" and schematic.quantityMin > 0)
        or (type(schematic.reagentSlotSchematics) == "table" and #schematic.reagentSlotSchematics > 0)) then
        schematic = nil
    end
    if not info and not schematic and not (api.GetRecipeNumReagents and api.GetRecipeReagentInfo) then return end
    local book = runtime()
    local r = book[spell] or {}
    local before = recipeBefore(r)
    book[spell] = r
    local positiveEvidence = info or schematic or r.learned == true or r.trainerObserved or r.validated or (E.Known(spell) == true)
    if positiveEvidence then r.validated = true end
    if info or schematic then r.available = true; r.validated = true end
    if info then
        if type(info.learned) == "boolean" then r.learned = info.learned end
        if type(info.hasCooldown) == "boolean" then r.cooldown = info.hasCooldown; r.cooldownVerified = true end
        local cw = getCDWatch()
        if cw and info.learned == true and type(cw.MarkChar) == "function" then
            local charKey = type(cw.CharKey) == "function" and cw.CharKey() or E.CharacterKey()
            local charName = type(cw.Name) == "function" and cw.Name()
                or (type(_G.UnitName) == "function" and select(2, pcall(_G.UnitName, "player")))
            pcall(cw.MarkChar, spell, charKey, charName)
        end
        if info.hasCooldown == true and cw and type(cw.Observe) == "function" then
            pcall(cw.Observe, spell)
        end
        local skill = info.requiredSkillRank or info.skillRequired
        if positiveInteger(skill) then r.learn = skill end
    end
    local outputRead, materialsRead = false, false
    if schematic then
        local lo, hi = schematic.quantityMin, schematic.quantityMax
        outputRead = readOutput(r, lo, hi)
        if type(schematic.outputItemID) == "number" and schematic.outputItemID > 0 then r.item = schematic.outputItemID end
        if type(schematic.reagentSlotSchematics) == "table" then
            local mats = {}
            local complete = #schematic.reagentSlotSchematics > 0 or r.learned == true
            local basic = _G.Enum and _G.Enum.CraftingReagentType and _G.Enum.CraftingReagentType.Basic
            for _, slot in ipairs(schematic.reagentSlotSchematics) do
                local required = not slot.optional and (basic == nil or slot.reagentType == nil or slot.reagentType == basic)
                if required then
                    local choices = slot.reagents or {}
                    if positiveInteger(slot.quantityRequired) and #choices == 1 and positiveInteger(choices[1].itemID) then
                        mats[#mats + 1] = { choices[1].itemID, slot.quantityRequired }
                    else
                        complete = false
                    end
                end
            end
            if complete then r.mats = mats; materialsRead = true end
        end
    end
    if not outputRead and api.GetRecipeNumItemsProduced then
        local ok, lo, hi = call("C_TradeSkillUI.GetRecipeNumItemsProduced", spell)
        if ok then readOutput(r, lo, hi) end
    end
    local linkOk, link = call("C_TradeSkillUI.GetRecipeItemLink", spell)
    if linkOk and type(link) == "string" then r.item = tonumber(link:match("item:(%d+)")) or r.item end
    if api.GetRecipeOutputItemData then
        local ok, out = call("C_TradeSkillUI.GetRecipeOutputItemData", spell)
        if ok and type(out) == "table" then
            r.item = out.itemID or (type(out.hyperlink) == "string" and tonumber(out.hyperlink:match("item:(%d+)"))) or r.item
        end
    end
    local numOk, num = call("C_TradeSkillUI.GetRecipeNumReagents", spell)
    if not materialsRead and numOk and type(num) == "number" and num >= 0 and api.GetRecipeReagentInfo then
        local mats = {}
        local complete = true
        for i = 1, num do
            local ilOk, il = call("C_TradeSkillUI.GetRecipeReagentItemLink", spell, i)
            local id = ilOk and type(il) == "string" and tonumber(il:match("item:(%d+)"))
            local riOk, _, _, qty = call("C_TradeSkillUI.GetRecipeReagentInfo", spell, i)
            if riOk and positiveInteger(id) and positiveInteger(qty) then
                mats[#mats + 1] = { id, qty }
            else
                complete = false
            end
        end
        if complete and (num > 0 or r.learned == true) then
            r.mats = mats
        elseif num == 0 and not positiveEvidence then
            if r.mats and #r.mats == 0 then r.mats = nil end
            if r.available == true then r.available = nil end
        end
    end
    local baseFn = (_G.C_Spell and _G.C_Spell.GetSpellBaseCooldown) or _G.GetSpellBaseCooldown
    if type(baseFn) == "function" then
        local ok, ms = pcall(baseFn, spell)
        if ok and type(ms) == "number" then
            if ms > 0 then r.cooldown = true elseif r.cooldown ~= true then r.cooldown = false end
        end
    end
    if api.GetRecipeCooldown then
        local ok, seconds, daily, _, maxCharges = call("C_TradeSkillUI.GetRecipeCooldown", spell)
        if ok and ((type(seconds) == "number" and seconds > 0) or daily == true or (type(maxCharges) == "number" and maxCharges > 0)) then
            r.cooldown = true
            r.cooldownVerified = true
        end
    end
    if validMaterials(r.mats) then r.available = true end
    r.observedAt = (type(_G.time) == "function" and select(2, pcall(_G.time))) or 0
    r.source = "client"
    recipeObserved(before, r)
    return r
end

function E.ScanCrafts(tick)
    tick = tick or function() end
    if type(_G.GetNumCrafts) ~= "function" or type(_G.GetCraftInfo) ~= "function" then return end
    local book = runtime()
    local okCount, count = pcall(_G.GetNumCrafts)
    if not okCount or type(count) ~= "number" then return end
    for i = 1, count do
        local okInfo, name, _, kind = pcall(_G.GetCraftInfo, i)
        if okInfo and name and kind ~= "header" then
            local link = type(_G.GetCraftRecipeLink) == "function" and select(2, pcall(_G.GetCraftRecipeLink, i)) or nil
            local spell = type(link) == "string" and tonumber(link:match("enchant:(%d+)") or link:match("spell:(%d+)")) or nil
            if not spell and type(_G.C_Spell) == "table" and type(_G.C_Spell.GetSpellInfo) == "function" then
                local ok, info = pcall(_G.C_Spell.GetSpellInfo, name)
                spell = ok and type(info) == "table" and info.spellID or nil
            end
            if not spell and type(_G.GetSpellInfo) == "function" then
                local ok, _, _, _, _, _, _, sid = pcall(_G.GetSpellInfo, name)
                if ok then spell = sid end
            end
            if spell and hasRecipe(spell) then
                local r = book[spell] or {}
                local before = recipeBefore(r)
                book[spell] = r
                r.learned = true
                if type(_G.GetCraftItemLink) == "function" then
                    local ok, item = pcall(_G.GetCraftItemLink, i)
                    if ok and type(item) == "string" then
                        r.item = tonumber(item:match("item:(%d+)")) or r.item
                    end
                end
                if type(_G.GetCraftNumMade) == "function" then
                    local ok, lo, hi = pcall(_G.GetCraftNumMade, i)
                    if ok then readOutput(r, lo, hi) end
                end
                local mats, complete = {}, true
                if type(_G.GetCraftNumReagents) == "function" and type(_G.GetCraftReagentInfo) == "function" then
                    local okN, nReag = pcall(_G.GetCraftNumReagents, i)
                    if okN and type(nReag) == "number" then
                        for n = 1, nReag do
                            local il = type(_G.GetCraftReagentItemLink) == "function" and select(2, pcall(_G.GetCraftReagentItemLink, i, n)) or nil
                            local id = type(il) == "string" and tonumber(il:match("item:(%d+)")) or nil
                            local riOk, _, _, qty = pcall(_G.GetCraftReagentInfo, i, n)
                            if riOk and id and qty then mats[#mats + 1] = { id, qty } else complete = false end
                        end
                        if complete then r.mats = mats end
                    end
                end
                if type(_G.GetCraftCooldown) == "function" then
                    local ok, seconds = pcall(_G.GetCraftCooldown, i)
                    if ok and type(seconds) == "number" and seconds > 0 then r.cooldown = true end
                end
                r.source = "client"
                r.observedAt = (type(_G.time) == "function" and select(2, pcall(_G.time))) or 0
                recipeObserved(before, r)
            end
        end
        tick()
    end
end

function E.ScanRecipes(tick)
    tick = tick or function() end
    local ui = _G.C_TradeSkillUI
    if type(ui) == "table" then
        if type(ui.IsTradeSkillLinked) == "function" then
            local ok, v = pcall(ui.IsTradeSkillLinked)
            if ok and v then return end
        end
        if type(ui.IsTradeSkillGuild) == "function" then
            local ok, v = pcall(ui.IsTradeSkillGuild)
            if ok and v then return end
        end
    end
    local book = runtime()
    if type(ui) == "table" and ui.GetAllRecipeIDs and ui.GetRecipeInfo then
        local ok, ids = call("C_TradeSkillUI.GetAllRecipeIDs")
        if not ok or type(ids) ~= "table" then return end
        local baseOk, base = call("C_TradeSkillUI.GetBaseProfessionInfo")
        local slug = baseOk and type(base) == "table" and E.ProfessionSlug(base.professionID)
        local changingOk, changing = call("C_TradeSkillUI.IsDataSourceChanging")
        local readyOk, ready = call("C_TradeSkillUI.IsTradeSkillReady")
        local complete = slug and E.Professions()[slug] and changingOk and changing == false and (not readyOk or ready == true) and #ids > 0
        local set, unlearned = {}, false
        for _, spell in ipairs(ids) do
            if hasRecipe(spell) then
                set[spell] = true
                local infoOk, info = call("C_TradeSkillUI.GetRecipeInfo", spell)
                if not infoOk or type(info) ~= "table" then
                    complete = false
                elseif info.learned == false then
                    unlearned = true
                end
                local readOk = pcall(E.ReadRecipe, spell, info, infoOk)
                if not readOk then complete = false end
            end
            tick()
        end
        local endBaseOk, endBase = call("C_TradeSkillUI.GetBaseProfessionInfo")
        local endChangingOk, endChanging = call("C_TradeSkillUI.IsDataSourceChanging")
        if complete and unlearned and endBaseOk and type(endBase) == "table" and E.ProfessionSlug(endBase.professionID) == slug and endChangingOk and endChanging == false then
            local d = store()
            d.recipeRosters = d.recipeRosters or {}
            local previous = d.recipeRosters[slug]
            local same = previous and previous.complete and type(previous.ids) == "table"
            if same then
                for spell in pairs(set) do
                    tick()
                    if not previous.ids[spell] then same = false; break end
                end
                if same then
                    for spell in pairs(previous.ids) do
                        tick()
                        if not set[spell] then same = false; break end
                    end
                end
            end
            local nowSec = (type(_G.time) == "function" and select(2, pcall(_G.time))) or 0
            if same then
                previous.observedAt = nowSec
            else
                d.recipeRosters[slug] = { complete = true, ids = set, observedAt = nowSec }
                changedInput()
            end
        end
    elseif type(_G.GetNumTradeSkills) == "function" and type(_G.GetTradeSkillInfo) == "function" then
        local okCount, count = pcall(_G.GetNumTradeSkills)
        if not okCount or type(count) ~= "number" then return end
        for i = 1, count do
            local okInfo, _, kind = pcall(_G.GetTradeSkillInfo, i)
            local link = type(_G.GetTradeSkillRecipeLink) == "function" and select(2, pcall(_G.GetTradeSkillRecipeLink, i)) or nil
            local spell = type(link) == "string" and tonumber(link:match("enchant:(%d+)") or link:match("spell:(%d+)")) or nil
            if okInfo and spell and kind ~= "header" and hasRecipe(spell) then
                local r = book[spell] or {}
                local before = recipeBefore(r)
                book[spell] = r
                r.learned = true
                if type(_G.GetTradeSkillNumMade) == "function" then
                    local ok, lo, hi = pcall(_G.GetTradeSkillNumMade, i)
                    if ok then readOutput(r, lo, hi) end
                end
                if type(_G.GetTradeSkillItemLink) == "function" then
                    local ok, itemLink = pcall(_G.GetTradeSkillItemLink, i)
                    if ok and type(itemLink) == "string" then
                        r.item = tonumber(itemLink:match("item:(%d+)")) or r.item
                    end
                end
                local mats, complete = {}, true
                if type(_G.GetTradeSkillNumReagents) == "function" and type(_G.GetTradeSkillReagentInfo) == "function" then
                    local okN, nReag = pcall(_G.GetTradeSkillNumReagents, i)
                    if okN and type(nReag) == "number" then
                        for j = 1, nReag do
                            local il = type(_G.GetTradeSkillReagentItemLink) == "function" and select(2, pcall(_G.GetTradeSkillReagentItemLink, i, j)) or nil
                            local id = type(il) == "string" and tonumber(il:match("item:(%d+)")) or nil
                            local riOk, _, _, qty = pcall(_G.GetTradeSkillReagentInfo, i, j)
                            if riOk and id and qty then mats[#mats + 1] = { id, qty } else complete = false end
                        end
                        if complete then r.mats = mats end
                    end
                end
                if type(_G.GetTradeSkillCooldown) == "function" then
                    local ok, seconds = pcall(_G.GetTradeSkillCooldown, i)
                    if ok and type(seconds) == "number" and seconds > 0 then r.cooldown = true end
                end
                local baseFn = (_G.C_Spell and _G.C_Spell.GetSpellBaseCooldown) or _G.GetSpellBaseCooldown
                if type(baseFn) == "function" then
                    local ok, ms = pcall(baseFn, spell)
                    if ok and type(ms) == "number" and ms > 0 then r.cooldown = true end
                end
                r.observedAt = (type(_G.time) == "function" and select(2, pcall(_G.time))) or 0
                r.source = "client"
                recipeObserved(before, r)
            end
            tick()
        end
    end
end

function E.CaptureTrainer(previous)
    if type(_G.GetNumTrainerServices) ~= "function" or type(_G.GetTrainerServiceInfo) ~= "function" then return previous end
    local countOk, count = call("GetNumTrainerServices")
    if not countOk or type(count) ~= "number" or count <= 0 then return previous end
    local snapshot = type(previous) == "table" and previous or { services = {} }
    snapshot.services = snapshot.services or {}
    for i = 1, count do
        local infoOk, name, subtext, serviceType = call("GetTrainerServiceInfo", i)
        local spellOk, spell = call("C_Trainer.GetServiceSpellID", i)
        if not spellOk or not positiveInteger(spell) then spellOk, spell = call("GetTrainerServiceSpellID", i) end
        if not spellOk or not positiveInteger(spell) then
            local linkOk, link = call("GetTrainerServiceItemLink", i)
            spell = linkOk and type(link) == "string" and tonumber(link:match("enchant:(%d+)") or link:match("spell:(%d+)")) or nil
        end
        if not positiveInteger(spell) then spell = nil end
        local requirement = {}
        if serviceType == "available" then
            requirement.available = true
        elseif serviceType == "unavailable" then
            requirement.available = false
        end
        if type(_G.GetTrainerServiceLevelReq) == "function" then
            local ok, level = pcall(_G.GetTrainerServiceLevelReq, i)
            if ok and type(level) == "number" then requirement.level = level end
        end
        if type(_G.GetTrainerServiceSkillReq) == "function" then
            local ok, skillName, skill = pcall(_G.GetTrainerServiceSkillReq, i)
            if ok and type(skill) == "number" then
                requirement.skill = skill
                requirement.skillName = skillName
            end
        end
        if type(_G.GetTrainerServiceCost) == "function" then
            local ok, cost, extra = pcall(_G.GetTrainerServiceCost, i)
            if ok and type(cost) == "number" and cost >= 0 and (extra == nil or extra == 0) then
                requirement.trainingCost = cost
            end
        end
        if spell or (infoOk and type(name) == "string") then
            local key = spell or tostring(name) .. "\031" .. tostring(subtext or "")
            snapshot.services[key] = { spell = spell, name = infoOk and name or nil, subtext = subtext, requirement = requirement }
        end
    end
    return snapshot
end

local trainerNames

function E.ScanTrainer(tick, snapshot)
    tick = tick or function() end
    snapshot = type(snapshot) == "table" and snapshot or E.CaptureTrainer()
    if not snapshot then return end
    runtime()
    local d = store()
    d.learningRequirements = d.learningRequirements or {}
    local spellName = (_G.C_Spell and _G.C_Spell.GetSpellName) or _G.GetSpellInfo
    local subtextFn = _G.C_Spell and _G.C_Spell.GetSpellSubtext
    local function fallback(name, subtext)
        if type(name) ~= "string" or type(spellName) ~= "function" then return nil end
        if not trainerNames or trainerNames.spellName ~= spellName or trainerNames.subtextFn ~= subtextFn then
            trainerNames = { spellName = spellName, subtextFn = subtextFn, names = {}, pending = {} }
            for slug in pairs(E.Professions()) do indexProfession(slug) end
            for spell, slug in pairs(recipeIDs) do
                if type(slug) == "string" then
                    trainerNames.pending[spell] = true
                    tick()
                end
            end
        end
        if not trainerNames.scanned then
            local names = trainerNames.names
            for spell in pairs(trainerNames.pending) do
                local ok, spellText, sub = pcall(spellName, spell)
                local subOk = true
                if type(subtextFn) == "function" then subOk, sub = pcall(subtextFn, spell) end
                if ok and type(spellText) == "string" and spellText ~= "" and subOk then
                    local key = spellText .. "\031" .. tostring(sub or "")
                    if names[key] and names[key] ~= spell then names[key] = false elseif names[key] == nil then names[key] = spell end
                    if names[spellText] and names[spellText] ~= spell then names[spellText] = false elseif names[spellText] == nil then names[spellText] = spell end
                    trainerNames.pending[spell] = nil
                end
                tick()
            end
            trainerNames.scanned = true
        end
        local match = trainerNames.names[name .. "\031" .. tostring(subtext or "")]
        if match == nil then match = trainerNames.names[name] end
        return match or nil
    end
    if trainerNames then trainerNames.scanned = nil end
    for _, service in pairs(snapshot.services or {}) do
        local spell = service.spell or fallback(service.name, service.subtext)
        local requirement = service.requirement or {}
        if spell and hasRecipe(spell) then
            local previous = d.learningRequirements[spell]
            if not previous or previous.level ~= requirement.level or previous.skill ~= requirement.skill
                or previous.skillName ~= requirement.skillName or previous.trainingCost ~= requirement.trainingCost then
                d.learningRequirements[spell] = requirement
                changedInput()
            end
            local book = runtime()
            local r = book[spell] or {}
            local before = recipeBefore(r)
            book[spell] = r
            r.available = true
            r.trainerObserved = true
            r.trainerAvailable = requirement.available
            recipeObserved(before, r)
        end
        tick()
    end
end

function E.ScanRecipeDetails(ids, tick)
    tick = tick or function() end
    if type(ids) ~= "table" or not next(ids) then return false end
    local baseOk, base = call("C_TradeSkillUI.GetBaseProfessionInfo")
    local changingOk, changing = call("C_TradeSkillUI.IsDataSourceChanging")
    local readyOk, ready = call("C_TradeSkillUI.IsTradeSkillReady")
    local linkedOk, linked = call("C_TradeSkillUI.IsTradeSkillLinked")
    local guildOk, guild = call("C_TradeSkillUI.IsTradeSkillGuild")
    local slug = baseOk and type(base) == "table" and E.ProfessionSlug(base.professionID)
    if not slug or not E.Professions()[slug] or not changingOk or changing ~= false
        or not readyOk or ready ~= true or (linkedOk and linked) or (guildOk and guild) then
        return false
    end
    for spell in pairs(ids) do
        if not positiveInteger(spell) then return false end
        local ok, r = pcall(E.ReadRecipe, spell)
        if not ok or not r then return false end
        tick()
    end
    local endBaseOk, endBase = call("C_TradeSkillUI.GetBaseProfessionInfo")
    local endChangingOk, endChanging = call("C_TradeSkillUI.IsDataSourceChanging")
    return endBaseOk and type(endBase) == "table" and E.ProfessionSlug(endBase.professionID) == slug
        and endChangingOk and endChanging == false
end

function E.RefreshClientData(readRecipes, readTrainer, onComplete, recipeSet, forceInputs, background)
    local trk = getTracking()
    if trk and type(trk.IsEnabled) == "function" and not trk.IsEnabled() then
        if onComplete then onComplete(false, "tracking_disabled") end
        return { done = true, cancelled = true, Cancel = function() end }
    end
    if forceInputs == nil then forceInputs = not readRecipes and not readTrainer and not recipeSet end
    runtime()
    local initial = store()
    local initialLevel
    if type(_G.UnitLevel) == "function" then
        local ok, value = pcall(_G.UnitLevel, "player")
        if ok then initialLevel = value end
    end
    local baseline = {
        recipes = initial.recipes,
        build = initial.recipeBuild,
        revision = initial.clientInputRevision or 0,
        professions = E.Copy(E.Professions()),
        level = initialLevel,
        error = E.lastReadError,
    }
    local deadline, ops = 0, 0
    local handle = {}
    activeScans[handle] = true
    local function now()
        if type(_G.debugprofilestop) == "function" then
            local ok, v = pcall(_G.debugprofilestop)
            if ok and type(v) == "number" then return v end
        end
        return 0
    end
    local function tick()
        ops = ops + 1
        if ops >= 1000 or (deadline > 0 and now() >= deadline) then
            ops = 0
            coroutine.yield()
        end
    end
    local co = coroutine.create(function()
        runtime()
        if type(E.RefreshLearningObservations) == "function" then E.RefreshLearningObservations(nil, tick) end
        if readRecipes or (recipeSet and not E.ScanRecipeDetails(recipeSet, tick)) then
            E.ScanRecipes(tick)
            E.ScanCrafts(tick)
        end
        if readTrainer then
            E.ScanTrainer(tick, type(readTrainer) == "table" and readTrainer or nil)
        end
    end)
    local function step()
        local curTrk = getTracking()
        if handle.cancelled or (curTrk and type(curTrk.IsEnabled) == "function" and not curTrk.IsEnabled()) then
            handle.done = true
            activeScans[handle] = nil
            return true
        end
        local idle = getIdle()
        deadline = now() + (idle and type(idle.SliceCap) == "function" and idle.SliceCap(2) or 2)
        local ok, err = coroutine.resume(co)
        if not ok then E.lastReadError = tostring(err) end
        if not ok or coroutine.status(co) == "dead" then
            local d = store()
            local previous = notified[d] or baseline
            local professions = E.Professions()
            local level
            if type(_G.UnitLevel) == "function" then
                local levelOK, value = pcall(_G.UnitLevel, "player")
                if levelOK then level = value end
            end
            if type(E.UpdateLearningContext) == "function" then E.UpdateLearningContext(level, professions) end
            local changed = forceInputs or not previous or previous.recipes ~= d.recipes or previous.build ~= d.recipeBuild
                or previous.revision ~= (d.clientInputRevision or 0) or previous.level ~= level
                or previous.error ~= E.lastReadError or not sameProfessions(previous.professions, professions)
            notified[d] = {
                recipes = d.recipes,
                build = d.recipeBuild,
                revision = d.clientInputRevision or 0,
                professions = professions,
                level = level,
                error = E.lastReadError,
            }
            local ra = getRouteAuto()
            if changed and ra and type(ra.Invalidate) == "function" then
                pcall(ra.Invalidate, "client-inputs")
            end
            handle.done = true
            activeScans[handle] = nil
            if onComplete then onComplete(ok, err) end
            return true
        end
        return false
    end
    function handle.Cancel()
        if handle.done then return end
        handle.cancelled = true
        handle.done = true
        co = nil
        activeScans[handle] = nil
        local idle = getIdle()
        if idle and type(idle.Cancel) == "function" then idle.Cancel(handle) end
        if onComplete then onComplete(false, "tracking_disabled") end
    end
    local idle = getIdle()
    if idle and type(idle.Defer) == "function" then
        function handle.Promote()
            if not handle.done then idle.Defer(handle, step, "normal") end
        end
        idle.Defer(handle, step, background and "background" or "normal")
    elseif background and idle and type(idle.Background) == "function" then
        idle.Background(step)
    elseif idle and type(idle.Add) == "function" then
        idle.Add(step)
    else
        while not step() do end
    end
    return handle
end

function E.CancelClientReads()
    local handles = {}
    for handle in pairs(activeScans) do handles[#handles + 1] = handle end
    for _, handle in ipairs(handles) do handle.Cancel() end
end

if type(_G.CreateFrame) == "function" then
    local ok, frame = pcall(_G.CreateFrame, "Frame")
    if ok and type(frame) == "table" and type(frame.RegisterEvent) == "function" and type(frame.SetScript) == "function" then
        local pendingRecipes, pendingTrainer, queued, scan, rescan = false, nil, false, nil, false
        local flush
        flush = function()
            queued = false
            if scan and not scan.done then rescan = true; return end
            local recipes, trainer = pendingRecipes, pendingTrainer
            pendingRecipes, pendingTrainer, rescan = false, nil, false
            local function complete()
                scan = nil
                if pendingRecipes or pendingTrainer or rescan then flush() end
            end
            local handle = E.RefreshClientData(recipes, trainer, complete, nil, false)
            if handle and not handle.done then scan = handle end
        end
        for _, event in ipairs({
            "TRADE_SKILL_SHOW", "TRADE_SKILL_LIST_UPDATE", "TRADE_SKILL_DATA_SOURCE_CHANGED",
            "TRADE_SKILL_DETAILS_UPDATE", "CRAFT_SHOW", "CRAFT_UPDATE", "TRAINER_SHOW", "TRAINER_UPDATE",
            "SKILL_LINES_CHANGED", "SPELLS_CHANGED", "PLAYER_LEVEL_UP", "PLAYER_LOGIN", "UPDATE_FACTION",
            "QUEST_TURNED_IN", "QUEST_LOG_UPDATE", "QUEST_ACCEPTED", "BAG_UPDATE_DELAYED", "PLAYER_EQUIPMENT_CHANGED",
        }) do
            pcall(frame.RegisterEvent, frame, event)
        end
        frame:SetScript("OnEvent", function(_, event)
            if type(E.QueueLearningObservationEvent) == "function" then
                E.QueueLearningObservationEvent(event)
            end
            local gates = getGates()
            if gates and type(gates.Invalidate) == "function" then gates.Invalidate() end
            if event == "TRAINER_SHOW" or event == "TRAINER_UPDATE" then
                pendingTrainer = E.CaptureTrainer(pendingTrainer)
            elseif type(event) == "string" and (event:find("TRADE_SKILL", 1, true) or event:find("CRAFT", 1, true)) then
                pendingRecipes = true
            end
            if queued then return end
            queued = true
            if type(_G.C_Timer) == "table" and type(_G.C_Timer.After) == "function" then
                pcall(_G.C_Timer.After, 0, flush)
            else
                flush()
            end
        end)
        E.ClientInputFrame = frame
    end
end
