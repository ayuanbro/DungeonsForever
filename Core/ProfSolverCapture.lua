local _, ns = ...

if not ns.LoadForeverPages then return end

local E = ns.ProfEconomy
if not E then return end

local floor, min, max = math.floor, math.min, math.max
local L = ns.L

local function shallow(t)
    local o = {}
    for k, v in pairs(t or {}) do o[k] = v end
    return o
end

local yGate = 0
local function MaybeYield()
    if not coroutine.running() then return end
    if not debugprofilestop then return end
    local now = debugprofilestop()
    if now - yGate >= 3 then
        yGate = now
        coroutine.yield()
    end
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

local DIAG_TEXT = {
    vendorEstimate = L["NPC购买价格尚未配置。"],
    vendorQuoteChanged = L["NPC购买价格资料已更新，请重新计算路线。"],
    toolPolicyChanged = L["工具设置或工具列表已变化，请手动重新计算路线。"],
    fixedOnlyChanged = L["急救已改为固定路线，请重新计算。"],
    cooldown = L["已排除有冷却的制作配方。"],
    cooldownUnknown = L["制作冷却尚未核实，请打开对应专业面板。"],
    outputConflict = L["制作产量待读取，请打开对应专业面板。"],
    availabilityUnknown = L["配方学习条件尚未核实。"],
    excluded = L["配方已按自定义规则排除。"],
    notLearned = L["当前设置仅允许已学配方。"],
    clientUnavailable = L["客户端已确认此配方不可用。"],
    specializationRequired = L["尚未满足此配方的专业专精学习要求。"],
    specializationChanged = L["专精选择或学习条件已变化，请手动重新计算路线。"],
    specializationFixed = L["固定攻略包含尚不可用的专精配方或入门任务，请切换自动规划。"],
    specializationEvidenceConflict = L["此配方的专精学习资料存在冲突，需要确认。"],
    specializationChoiceConflict = L["当前已学专精与所选目标不同；本路线不处理转修专精。"],
    specializationFactionUnknown = L["尚未读取角色阵营，无法确定专精任务交付地点。"],
    specializationQuestAlreadyCompleted = L["入门任务已经完成，但当前未确认所需专精；请先核实转修条件。"],
    specializationUnknown = L["角色专精状态尚未读取，请登录角色并打开工程学面板后重试。"],
    specializationLevelRequired = L["角色等级不足 30，暂时无法完成工程专精入门任务。"],
    specializationLevelUnknown = L["尚未读取角色等级，无法确认工程专精任务资格。"],
    specializationQuestDisabled = L["客户端已确认此专精任务当前不可用。"],
    professionMissing = L["角色尚未学习所需专业。"],
    skillRequired = L["另一专业技能不足，可开启联合升级或购买材料。"],
    secondaryRequired = L["请先选择联合升级的另一个专业。"],
    pairingChanged = L["搭配专业已更改，点击重新计算应用。"],
    professionChanged = L["专业学习状态或旧路线规则已变化，请重新计算路线。"],
    formulaUnavailable = L["未学配方的图纸没有可靠的购买报价；任务图纸需先学会或取得拍卖行报价。"],
    limitedFormulaDisabled = L["当前设置不从商人购买限量图纸；请取得拍卖行报价或先学会该配方。"],
    formulaPolicyChanged = L["限量图纸购买设置已变化，请重新计算路线。"],
    formulaPriceUnknown = L["图纸购买价格尚未核实。"],
    formulaUnknownSource = L["图纸没有可核实的购买报价；可在设置关闭「不使用未知来源的图纸」。"],
    formulaStockUnknown = L["图纸为限量或未核实库存，不能保证商人现货。"],
    auctionSupplyLimited = L["拍卖行可购数量不足，无法继续此配方；请查询更多货物或改用其他配方。"],
    fishingRecipeGap = L["当前技能没有符合纯钓鱼条件的可用配方，请检查食谱、材料来源或排除设置。"],
    materialUnavailable = L["材料没有可靠的购买或制作来源。"],
    levelGap = L["当前技能区间没有可用升级配方。"],
    clientDataPending = L["客户端数据待读取，请打开对应专业面板。"],
    solverError = L["计算发生错误，请重新计算。"],
    vendorPending = L["商人购买价格尚未配置。"],
    characterLevelRequired = L["角色等级不足，无法学习所需专业等级。"],
    vendorPriceUnknown = L["商人购买价格尚未核实。"],
    materialPriceUnknown = L["拍卖行价格未知，先按已有资料显示路线。"],
    batchDependency = L["合并制作所需的材料或学习等级尚未满足。"],
    batchSkillGap = L["合并制作后无法达到目标技能，请调整配方限制。"],
    executionInvalid = L["制作顺序或材料用途无法验证，请调整限制后重新计算。"],
}

function E.DiagnosticText(d)
    if type(d) == "string" then return DIAG_TEXT[d] or d end
    if type(d) ~= "table" then return nil end
    if type(d.message) == "string" then return d.message end
    local code = d.code
    if type(code) ~= "string" then return nil end
    return DIAG_TEXT[code] or code
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

local PRIMARY_FALLBACK = {
    "alchemy", "blacksmithing", "enchanting", "engineering",
    "leatherworking", "tailoring", "mining", "herbalism", "skinning",
}

local function partnerStore()
    DungeonsForeverDB = DungeonsForeverDB or {}
    local d = DungeonsForeverDB
    d.prof = d.prof or {}
    d.prof.routePartners = d.prof.routePartners or {}
    return d.prof.routePartners
end

local function primaryOf(slug)
    local data = ns.ProfData
    local info = data and data.pro and data.pro[slug]
    if info then return info.kind == "primary" end
    for i = 1, #PRIMARY_FALLBACK do
        if PRIMARY_FALLBACK[i] == slug then return true end
    end
    return false
end

function E.PartnerCandidates(slug)
    local out, seen = {}, {}
    local function add(p)
        if p ~= slug and not seen[p] and primaryOf(p) then
            seen[p] = true
            out[#out + 1] = p
        end
    end
    local data = ns.ProfData
    local order = (data and data.order) or PRIMARY_FALLBACK
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
end

function E.SetRoutePartner(slug, partner)
    if partner ~= nil and not E.ValidPartner(slug, partner) then return false end
    local saved = partnerStore()
    if saved[slug] == partner then return true end
    saved[slug] = partner
    local ra = ns.ProfRouteAuto
    if ra and ra.Invalidate then ra.Invalidate() end
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
    local G = ns.ProfGates
    if G then
        local choice = G.EngineeringChoice()
        ctx.specializationContext = { choice = choice, abilities = G.Abilities(),
            selectionConflict = (choice == "conflict") or false }
    end
    return ctx
end

local function learnedCap(professions)
    for _, v in pairs(professions or {}) do
        if type(v) == "table" and type(v.max) == "number" and v.max > 0 and not v.unlearned then
            return v.max
        end
    end
    return 300
end

function E.RouteProfessions(slug, opts, professions)
    opts = opts or {}
    professions = professions or (opts.snapshot and opts.snapshot.professions) or E.Professions()
    local context = E.RouteContext(slug, opts, professions)
    if slug == "__purchase" then return professions, context end
    if not context.unlearned then return professions, context end
    local cap = learnedCap(professions)
    local selected = {}
    local target = professions[slug]
    if target then
        selected[slug] = shallow(target)
    else
        selected[slug] = { cur = tonumber(opts.start) or 1, max = cap, primary = true }
    end
    selected[slug].unlearned = true
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

local SUPPLY_FIELDS = { "quantity", "observedAt", "source", "complete", "ownerExcluded", "market" }

local function ValidSupply(entry)
    return type(entry) == "table" and entry.source ~= "auctionator-daily-maximum"
        and type(entry.quantity) == "number" and entry.quantity >= 0
        and entry.quantity < math.huge and entry.quantity == math.floor(entry.quantity)
end

local function SupplyIdentity(entry)
    if not entry then return false end
    local out = {}
    for i = 1, #SUPPLY_FIELDS do out[SUPPLY_FIELDS[i]] = entry[SUPPLY_FIELDS[i]] end
    return out
end

function E.AuctionSupplyOf(context, id)
    if type(id) ~= "number" or id <= 0 then return nil end
    local entry
    if context and context.auctionSupply then
        entry = context.auctionSupply[id]
    elseif not context or not context.prices then
        local bridge = ns.AuctionBridge
        if bridge and bridge.GetAuctionSupply then entry = bridge.GetAuctionSupply(id, true) end
    end
    if ValidSupply(entry) then return entry end
    return nil
end

function E.SummarizeAuctionSupply(result, context)
    if type(result) ~= "table" then return result end
    local ra = ns.ProfRouteAuto
    if ra and ra.StampSupply then ra.StampSupply(result, context) end
    local inputs, needed = {}, {}
    for _, e in ipairs(result.mats or {}) do
        local id = e.id or e[1]
        if type(id) == "number" and id > 0 then
            inputs[id] = SupplyIdentity(E.AuctionSupplyOf(context, id))
            needed[id] = (needed[id] or 0) + (tonumber(e.count or e[2]) or 1)
        end
    end
    result.auctionSupplyInputs = inputs
    local complete = true
    for _, e in ipairs(result.mats or {}) do
        local id = e.id or e[1]
        if type(id) == "number" and not e.vendor
            and (e.source == nil or e.source == "ah" or e.source == "auction") then
            local q = tonumber(e.availableCount)
            if not q then
                complete = false
            else
                if (needed[id] or 0) > q then
                    e.supplyLimited = true
                    complete = false
                end
                if e.supplyComplete ~= true then complete = false end
            end
        end
    end
    result.supplyComplete = complete and true or false
    return result
end

local function vendorQuote(o)
    return type(o) == "table" and o.unlimited == true and type(o.price) == "number"
        and o.price >= 0 and o.available ~= false and o.purchasable ~= false
        and not o.hasExtendedCost and (not o.currencyID or o.currencyID == 0)
end

function E.FormulaFor(r, context)
    MaybeYield()
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
    local seenNpc = {}
    local raw = {}
    local flist = ns.ProfSupply and ns.ProfSupply.FormulaList and ns.ProfSupply.FormulaList(id) or nil
    if type(flist) == "table" then
        for _, o in ipairs(flist) do
            raw[#raw + 1] = o
            if o.npcID then seenNpc[o.npcID] = true end
        end
    end
    local vlist = vdb and vdb.GetOffers and vdb.GetOffers(id, context) or {}
    for _, o in ipairs(vlist) do
        if not (o.npcID and seenNpc[o.npcID]) then raw[#raw + 1] = o end
    end
    local PDm = ns.ProfModule
    local allowLimited = (PDm and PDm.SettingRaw and PDm.SettingRaw("autoBuyLimitedFormulas")) and true or false
    local limitedCost
    for _, o in ipairs(raw) do
        MaybeYield()
        if type(o) == "table" and o.npcID and (type(o.price) == "number" or o.unlimited ~= nil or o.limited ~= nil) then
            hasOffer = true
            if o.unlimited == true then hasUnlimited = true
            elseif o.limited or o.unlimited == false then hasLimited = true end
            local pack = tonumber(o.quantity) or tonumber(o.bundleSize) or 1
            if pack < 1 then pack = 1 end
            offers[#offers + 1] = {
                npcID = o.npcID, price = o.price, quantity = pack,
                bundleSize = pack, unlimited = o.unlimited,
                limited = o.limited, stockUnknown = o.stockUnknown, estimated = o.estimated,
            }
        end
        if vendorQuote(o) and (not cost or source == "vendor" and o.price < cost) then
            cost, source = o.price, "vendor"
        end
        if allowLimited and type(o) == "table" and o.unlimited ~= true
            and type(o.price) == "number" and o.price >= 0
            and not o.hasExtendedCost and (not o.currencyID or o.currencyID == 0)
            and o.available ~= false and o.purchasable ~= false then
            if not limitedCost or o.price < limitedCost then limitedCost = o.price end
        end
    end
    if not cost and limitedCost then cost, source = limitedCost, "vendor" end
    if not cost then unpriced = true end
    local skipUnknown = (PDm and PDm.SettingRaw and PDm.SettingRaw("autoSkipUnpricedFormulas")) and true or false
    if not allowLimited and not cost and hasOffer and not hasUnlimited then
        return {
            id = id, count = 1, need = 1, spell = r.spell, profession = r.profession,
            recipeKey = r.key, known = false, sources = shallow(r.source),
            vendorOffers = offers, source = "unknown", cost = nil,
            usable = false, reason = "formulaLimited", unpriced = true,
            limited = hasLimited, stockUnknown = hasOffer and not hasLimited or nil,
        }
    end
    if not cost and skipUnknown then
        return {
            id = id, count = 1, need = 1, spell = r.spell, profession = r.profession,
            recipeKey = r.key, known = false, sources = shallow(r.source),
            vendorOffers = offers, source = "unknown", cost = nil,
            usable = false, reason = "formulaUnknownSource", unpriced = true,
            unlimited = hasUnlimited or nil, limited = hasLimited or nil,
            stockUnknown = hasOffer and not hasUnlimited and not hasLimited or nil,
        }
    end
    return {
        id = id, count = 1, need = 1, spell = r.spell, profession = r.profession,
        recipeKey = r.key, known = false, sources = shallow(r.source),
        vendorOffers = offers, source = source or "unknown", cost = cost,
        usable = (cost ~= nil) or false, unpriced = unpriced,
        reason = (cost == nil) and "formulaPriceUnknown" or nil,
        unlimited = hasUnlimited or nil, limited = hasLimited or nil,
        stockUnknown = hasOffer and not hasUnlimited and not hasLimited or nil,
    }
end

function E.Index(s)
    s.recipes = s.recipes or {}
    s.byItem, s.byProfession, s.byKey = {}, {}, {}
    for _, r in ipairs(s.recipes) do
        MaybeYield()
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
    local AB = ns.AuctionBridge
    if AB and AB.SupplyFresh then
        local seen = {}
        for _, r in ipairs(s.recipes) do
            MaybeYield()
            if type(r.item) == "number" and r.item > 0 then seen[r.item] = true end
            for _, m in ipairs(r.mats or {}) do
                if type(m[1]) == "number" then seen[m[1]] = true end
            end
        end
        for id in pairs(seen) do
            MaybeYield()
            local rec = AB.SupplyFresh(id)
            if rec then
                s.auctionSupply[id] = rec
            end
            if AB.GetAuctionSupplyHistory then
                local h = AB.GetAuctionSupplyHistory(id)
                if h then s.auctionSupplyHistory[id] = h end
            end
            if AB.GetAuctionPriceObservedAt then
                local pt = AB.GetAuctionPriceObservedAt(id)
                if pt then s.priceObservedAt[id] = pt end
            end
        end
    end
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
    local planProfs, routeCtx = E.RouteProfessions(slug, opts, opts.professions or E.Professions())
    local s = {
        recipes = {}, byKey = {}, known = {}, prices = {}, offers = {},
        auctionSupply = {}, auctionSupplyHistory = {}, priceObservedAt = {},
        vendorItems = {}, vendorSuppliers = {}, coverageComplete = true,
        professions = planProfs,
        stamp = (time and time()) or 0,
        character = ns.ProfEconomy.CharacterKey and ns.ProfEconomy.CharacterKey() or nil,
    }
    s.level = UnitLevel and UnitLevel("player") or nil
    local f = UnitFactionGroup and UnitFactionGroup("player") or nil
    s.faction = f == "Alliance" and "A" or (f == "Horde" and "H" or nil)
    s.routeContext = routeCtx
    if routeCtx.unlearned and not (routeCtx.requiresPartner and routeCtx.partnerValid) then
        return E.Index(s)
    end
    local tables = ns.ProfRecipes or {}
    local loadList = { slug }
    if routeCtx.requiresPartner and routeCtx.partnerValid then
        loadList[#loadList + 1] = routeCtx.partner
    end
    for i = 1, #loadList do
        local profSlug = loadList[i]
        local d = tables[profSlug] or {}
        for _, row in ipairs(d.rows or {}) do
            local f13 = row[13]
            addRecipe(s, profSlug, row[1], row[2], row[3], row[7], row[8], row[9], row[10],
                row[12], type(f13) == "table" and f13[1] or nil, row[14], row[4])
            tick()
        end
        local lv = ns.ProfLeveling and ns.ProfLeveling[profSlug]
        for spell, ri in pairs(lv and lv.rinfo or {}) do
            local formula = ri.formula or ri.formulaID
            addRecipe(s, profSlug, spell, ri.makes, ri.count, ri.learn, ri.yellow, ri.green, ri.grey,
                ri.mats, formula, ri.source, ri.category)
            tick()
        end
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
                if G.ToolOwned and G.ToolOwned(goal.item) then
                    s.ownedToolItems = s.ownedToolItems or {}
                    s.ownedToolItems[goal.item] = true
                else
                    keptGoals[#keptGoals + 1] = goal
                    s.retainedToolItems[goal.item] = 1
                    s.nonAuctionable[goal.item] = true
                end
            end
        end
        s.toolGoals = keptGoals
        local specTarget = tonumber(opts.target)
        if not specTarget then
            local db = DungeonsForeverDB and DungeonsForeverDB.prof
            specTarget = tonumber(db and db.lvTarget and db.lvTarget[slug]) or 300
        end
        local specCtx = G.SpecializationContext and G.SpecializationContext {
            profession = slug, target = specTarget, faction = s.faction, level = s.level,
        } or nil
        if specCtx then
            s.targetProfession = slug
            s.engineeringSpecialization = specCtx.choice
            s.specializationContext = specCtx
            s.specializationAbilities = specCtx.abilities
            s.specializationFingerprint = specCtx.fingerprint
            local keepGoals = {}
            for _, goal in ipairs(specCtx.goals or {}) do
                local reason = goal.blockedReason
                if not reason or reason == "specializationLevelRequired" then
                    keepGoals[#keepGoals + 1] = goal
                end
            end
            s.specializationGoals = keepGoals
        else
            local specGoal = G.SpecGoal(slug, opts.target)
            if specGoal then s.specializationGoals = { specGoal } end
        end
    end
    if ns.ProfRecovery then ns.ProfRecovery.Capture(s, opts) end
    return E.Index(s)
end
