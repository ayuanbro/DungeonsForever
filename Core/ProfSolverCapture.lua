local _, ns = ...

if not ns.LoadForeverPages then return end

local E = ns.ProfEconomy
if not E then return end

local floor, min, max = math.floor, math.min, math.max

local function shallow(t)
    local o = {}
    for k, v in pairs(t or {}) do o[k] = v end
    return o
end

local function validMats(mats)
    if type(mats) ~= "table" or #mats == 0 then return false end
    for _, m in ipairs(mats) do
        if type(m) ~= "table" or type(m[1]) ~= "number" or m[1] <= 0
            or type(m[2]) ~= "number" or m[2] <= 0 then return false end
    end
    return true
end

E.Copy = shallow

if not E.GetPolicies then
    function E.GetPolicies()
        return {}
    end
end

if not E.Policy then
    function E.Policy(policies, r)
        if not policies or not r then return nil end
        local key = r.key or (r.profession and (tostring(r.profession) .. ":" .. tostring(r.spell)))
        return (key and policies[key]) or policies[r.spell]
    end
end

function E.Gain(r, skill)
    if type(r) ~= "table" then return 0 end
    local learn, grey = r.learn, r.grey
    if type(learn) ~= "number" or type(grey) ~= "number" then return 0 end
    local yellow = r.yellow or learn
    local green = r.green or yellow
    if skill < learn or skill >= grey then return 0 end
    if skill < yellow then return 1 end
    if skill < green then
        return 1 - ((skill - yellow) / max(1, green - yellow)) * .5
    end
    return max(.05, .5 - ((skill - green) / max(1, grey - green)) * .45)
end

function E.Professions()
    local out = {}
    local PD = ns.ProfModule
    local list = PD and PD.ProfLearned and PD.ProfLearned() or {}
    for slug, v in pairs(list) do
        out[slug] = { cur = tonumber(v.cur) or 1, max = tonumber(v.max) or 300, primary = true }
    end
    return out
end

function E.Known(spell)
    local ra = ns.ProfRouteAuto
    if ra and ra.SpellKnown then
        local ok, v = pcall(ra.SpellKnown, spell)
        if ok then return v and true or false end
    end
    return false
end

function E.RouteContext(slug, opts, professions)
    local p = professions and professions[slug]
    local ctx = { requiresPartner = false, partnerValid = true, unlearned = (p == nil) }
    local G = ns.ProfGates
    if G then
        local choice = G.EngineeringChoice()
        ctx.specializationContext = { choice = choice, abilities = G.Abilities(),
            selectionConflict = (choice == "conflict") or false }
    end
    return ctx
end

function E.NonAuctionableItem()
    return false
end

function E.AuctionSupplyOf()
    return nil
end

function E.SummarizeAuctionSupply()
end

local function vendorQuote(o)
    return type(o) == "table" and o.unlimited == true and type(o.price) == "number"
        and o.price >= 0 and o.available ~= false and o.purchasable ~= false
        and not o.hasExtendedCost and (not o.currencyID or o.currencyID == 0)
end

function E.FormulaFor(r, context)
    if type(r) ~= "table" then return end
    local id = tonumber(r.formula)
    if not id or id <= 0 then return nil end
    local known = E.Known(r.spell)
    if type(context) == "table" and type(context.known) == "table" then
        if context.known[r.key] or context.known[r.spell] then known = true end
    end
    if known then return { id = id, known = true, usable = true } end
    local ra = ns.ProfRouteAuto
    local cost, source, unpriced
    local ah = ra and ra.AHPriceOf and ra.AHPriceOf(id)
    if type(ah) == "number" and ah > 0 then cost, source = ah, "ah" end
    local offers, hasUnlimited, hasLimited, hasOffer = {}, false, false, false
    local vdb = ns.VendorPriceDB
    local raw = vdb and vdb.GetOffers and vdb.GetOffers(id, context) or {}
    for _, o in ipairs(raw) do
        if type(o) == "table" and (type(o.price) == "number" or o.unlimited ~= nil or o.limited ~= nil) then
            hasOffer = true
            if o.unlimited == true then hasUnlimited = true
            elseif o.limited or o.unlimited == false then hasLimited = true end
            offers[#offers + 1] = {
                npcID = o.npcID, price = o.price, quantity = o.quantity or o.bundleSize or 1,
                bundleSize = o.bundleSize or o.quantity or 1, unlimited = o.unlimited,
                limited = o.limited, stockUnknown = o.stockUnknown, estimated = o.estimated,
            }
        end
        if vendorQuote(o) and (not cost or source == "vendor" and o.price < cost) then
            cost, source = o.price, "vendor"
        end
    end
    if not cost then unpriced = true end
    local PDm = ns.ProfModule
    local allowLimited = (PDm and PDm.SettingRaw and PDm.SettingRaw("autoBuyLimitedFormulas")) and true or false
    if not allowLimited and not cost and hasOffer and not hasUnlimited then
        return {
            id = id, count = 1, need = 1, spell = r.spell, profession = r.profession,
            recipeKey = r.key, known = false, sources = shallow(r.source),
            vendorOffers = offers, source = "unknown", cost = nil,
            usable = false, reason = "formulaLimited", unpriced = true,
            limited = hasLimited, stockUnknown = hasOffer and not hasLimited or nil,
        }
    end
    return {
        id = id, count = 1, need = 1, spell = r.spell, profession = r.profession,
        recipeKey = r.key, known = false, sources = shallow(r.source),
        vendorOffers = offers, source = source or "unknown", cost = cost,
        usable = true, unpriced = unpriced,
        unlimited = hasUnlimited or nil, limited = hasLimited or nil,
        stockUnknown = hasOffer and not hasUnlimited and not hasLimited or nil,
    }
end

function E.Index(s)
    s.recipes = s.recipes or {}
    s.byItem, s.byProfession, s.byKey = {}, {}, {}
    for _, r in ipairs(s.recipes) do
        r.key = r.key or (r.profession .. ":" .. r.spell)
        r.count = r.count or 1
        r.mats = r.mats or {}
        r.yellow = r.yellow or r.learn
        r.green = r.green or r.yellow
        s.byKey[r.key] = r
        local p = s.byProfession[r.profession]
        if not p then p = {}; s.byProfession[r.profession] = p end
        p[#p + 1] = r
        if type(r.item) == "number" and r.item > 0 and r.count > 0 then
            local a = s.byItem[r.item]
            if not a then a = {}; s.byItem[r.item] = a end
            a[#a + 1] = r
        end
    end
    s.professions = s.professions or {}
    s.known = s.known or {}
    s.prices = s.prices or {}
    s.offers = s.offers or {}
    s.formulaOffers = s.formulaOffers or {}
    s.auctionSupply = s.auctionSupply or {}
    s.auctionSupplyHistory = s.auctionSupplyHistory or {}
    s.priceObservedAt = s.priceObservedAt or {}
    s.nonAuctionable = s.nonAuctionable or {}
    s.vendorItems = s.vendorItems or {}
    s.vendorSuppliers = s.vendorSuppliers or {}
    s.diagnostics = s.diagnostics or {}
    s.toolGoals = s.toolGoals or {}
    s.specializationGoals = s.specializationGoals or {}
    s.specializationAbilities = s.specializationAbilities or {}
    s.inventory = {}
    return s
end

local function addRecipe(s, slug, spell, item, count, learn, yellow, green, grey, mats, formula, source, category)
    if type(spell) ~= "number" or spell <= 0 then return end
    if type(learn) ~= "number" or type(grey) ~= "number" or grey <= learn then return end
    if not validMats(mats) then return end
    local key = slug .. ":" .. spell
    if s.byKey[key] then return end
    local r = {
        profession = slug, spell = spell, item = item, count = count or 1,
        learn = learn, yellow = yellow or learn, green = green or yellow or learn,
        grey = grey, mats = mats, formula = formula, source = source or {},
        category = category, key = key, catalogue = true,
    }
    s.recipes[#s.recipes + 1] = r
    s.byKey[key] = r
    s.known[key] = E.Known(spell)
end

function E.Capture(slug, opts, tick)
    opts = opts or {}
    tick = tick or function() end
    if opts.snapshot then
        local s = shallow(opts.snapshot)
        s.professions = opts.professions or s.professions or E.Professions()
        s.routeContext = s.routeContext or E.RouteContext(slug, opts, s.professions)
        return E.Index(s)
    end
    local s = {
        recipes = {}, byKey = {}, known = {}, prices = {}, offers = {},
        auctionSupply = {}, auctionSupplyHistory = {}, priceObservedAt = {},
        vendorItems = {}, vendorSuppliers = {}, coverageComplete = true,
        professions = opts.professions or E.Professions(),
        stamp = (time and time()) or 0,
        character = ns.ProfEconomy.CharacterKey and ns.ProfEconomy.CharacterKey() or nil,
    }
    s.level = UnitLevel and UnitLevel("player") or nil
    local f = UnitFactionGroup and UnitFactionGroup("player") or nil
    s.faction = f == "Alliance" and "A" or (f == "Horde" and "H" or nil)
    s.routeContext = E.RouteContext(slug, opts, s.professions)
    if s.routeContext.unlearned then return E.Index(s) end
    local tables = ns.ProfRecipes or {}
    local d = tables[slug] or {}
    for _, row in ipairs(d.rows or {}) do
        local f13 = row[13]
        addRecipe(s, slug, row[1], row[2], row[3], row[7], row[8], row[9], row[10],
            row[12], type(f13) == "table" and f13[1] or nil, row[14], row[4])
        tick()
    end
    local lv = ns.ProfLeveling and ns.ProfLeveling[slug]
    for spell, ri in pairs(lv and lv.rinfo or {}) do
        local formula = ri.formula or ri.formulaID
        addRecipe(s, slug, spell, ri.makes, ri.count, ri.learn, ri.yellow, ri.green, ri.grey,
            ri.mats, formula, ri.source, ri.category)
        tick()
    end
    local items = {}
    for _, r in ipairs(s.recipes) do
        if type(r.item) == "number" and r.item > 0 then items[r.item] = true end
        for _, m in ipairs(r.mats) do items[m[1]] = true end
        if r.formula and not s.known[r.key] then items[r.formula] = true end
    end
    local ra = ns.ProfRouteAuto
    local vdb = ns.VendorPriceDB
    local context = { character = s.character, faction = s.faction, professions = s.professions, level = s.level }
    for id in pairs(items) do
        local price = ra and ra.AHPriceOf and ra.AHPriceOf(id)
        if type(price) == "number" and price > 0 then s.prices[id] = price end
        local offers = vdb and vdb.GetOffers and vdb.GetOffers(id, context)
        if offers and #offers > 0 then
            s.offers[id] = offers
            for _, o in ipairs(offers) do
                if vendorQuote(o) then s.vendorItems[id] = true; break end
            end
        end
        tick()
    end
    s.formulaOffers = {}
    local G = ns.ProfGates
    if G then
        s.abilities = s.abilities or G.Abilities()
        s.specializationAbilities = G.Abilities()
        s.toolGoals = G.ToolGoals(slug, opts.target)
        s.retainedToolItems = s.retainedToolItems or {}
        s.nonAuctionable = s.nonAuctionable or {}
        local keptGoals = {}
        for _, goal in ipairs(s.toolGoals) do
            if goal.item and s.byKey[slug .. ":" .. tostring(goal.spell)] then
                keptGoals[#keptGoals + 1] = goal
                s.retainedToolItems[goal.item] = 1
                s.nonAuctionable[goal.item] = true
            end
        end
        s.toolGoals = keptGoals
        local specGoal = G.SpecGoal(slug, opts.target)
        if specGoal then s.specializationGoals = { specGoal } end
        local choice = G.EngineeringChoice()
        s.specializationContext = { choice = choice, abilities = G.Abilities(),
            selectionConflict = (choice == "conflict") or false }
    end
    if ns.ProfRecovery then ns.ProfRecovery.Capture(s, opts) end
    return E.Index(s)
end
