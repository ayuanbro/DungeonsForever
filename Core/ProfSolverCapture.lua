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

-- Solver snapshots and execution plans must not share nested recipe/quote data
-- with the live client cache. Cooperatively copy large inputs when requested.
local function copy(value, tick, seen)
    if type(value) ~= "table" then return value end
    seen = seen or {}
    if seen[value] then return seen[value] end
    local out, count = {}, 0
    seen[value] = out
    for k, v in pairs(value) do
        out[k] = copy(v, tick, seen)
        count = count + 1
        if tick and count % 64 == 0 then tick() end
    end
    return out
end
E.Copy = function(value, tick) return type(value)=="table" and copy(value, tick) or {} end

function E.CharacterKey()
    return ((UnitName and UnitName("player")) or "?") .. "-" .. ((GetRealmName and GetRealmName()) or "?")
end

function E.ClientStore()
    DungeonsForeverDB = DungeonsForeverDB or {}
    DungeonsForeverDB.prof = DungeonsForeverDB.prof or {}
    local prof = DungeonsForeverDB.prof
    prof.economy = prof.economy or {}
    local key = E.CharacterKey()
    prof.economy[key] = prof.economy[key] or {}
    return prof.economy[key]
end

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
    vendorFormulaRequired = L["未学配方的图纸没有可用的商人金币报价。"],
    limitedFormulaDisabled = L["当前设置不从商人购买限量图纸；请取得拍卖行报价或先学会该配方。"],
    formulaPolicyChanged = L["限量图纸购买设置已变化，请重新计算路线。"],
    formulaPriceUnknown = L["图纸购买价格尚未核实。"],
    formulaUnknownSource = L["图纸没有可核实的购买报价；可在设置关闭「不使用未知来源的图纸」。"],
    formulaStockUnknown = L["图纸为限量或未核实库存，不能保证商人现货。"],
    auctionSupplyLimited = L["拍卖行可购数量不足，无法继续此配方；请在 Auctionator 重新完整扫描或改用其他配方。"],
    fishingRecipeGap = L["当前技能没有符合纯钓鱼条件的可用配方，请检查食谱、材料来源或排除设置。"],
    fishingRequirementsUnknown = L["鱼类的钓取门槛或时间限制尚未确认，暂不用于纯钓鱼路线。"],
    professionCapUnknown = L["当前专业技能上限尚未读取，暂不推断最后一段采集目标。"],
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
    learningRequirementsUnknown = L["配方学习条件尚未核实。"],
    learningPolicyChanged = L["配方学习条件资料已更新，请重新计算路线。"],
    toolFactsUnknown = L["制作工具的配方或产量资料尚未核实。"],
}

function E.DiagnosticText(d)
    if type(d) == "string" then return DIAG_TEXT[d] or d end
    if type(d) ~= "table" then return nil end
    if type(d.message) == "string" then return d.message end
    local code = d.code
    if type(code) ~= "string" then return nil end
    if code=="auctionSupplyLimited" and d.item and d.required and d.available then
        local name=GetItemInfo and GetItemInfo(d.item) or ("#"..tostring(d.item))
        return string.format(L["%s：拍卖行剩余可购 %d 件，本次需要 %d 件；请在 Auctionator 重新完整扫描或调整路线。"],name,d.available,d.required)
    end
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
    if not next(list) and type(GetProfessions)=="function" and type(GetProfessionInfo)=="function" then
        local ok, a, b, c, d, e, f = pcall(GetProfessions)
        if ok then
            local ids = E.SkillIDs or {[171]="alchemy",[164]="blacksmithing",[333]="enchanting",[202]="engineering",
                [165]="leatherworking",[197]="tailoring",[186]="mining",[182]="herbalism",[393]="skinning",
                [185]="cooking",[129]="first-aid",[356]="fishing"}
            for _, index in pairs({a,b,c,d,e,f}) do
                local found, _, _, cur, cap, _, _, id = pcall(GetProfessionInfo, index)
                if found and ids[id] and type(cur)=="number" and type(cap)=="number" then list[ids[id]]={cur=cur,max=cap} end
            end
        end
    end
    for slug, v in pairs(list) do
        local info = ns.ProfData and ns.ProfData.pro and ns.ProfData.pro[slug]
        local primary = info and info.kind=="primary" or (not info and slug~="cooking" and slug~="fishing" and slug~="first-aid")
        out[slug] = { cur = tonumber(v.cur) or 1, max = tonumber(v.max) or 300, primary = primary }
    end
    return out
end

function E.SpecializationKnown(spell)
    -- Execution completion needs a live ability observation, not a historical
    -- recipe cache. Failed/missing APIs and pre-login queries remain unknown.
    if type(IsLoggedIn)=="function" then
        local ok, ready = pcall(IsLoggedIn)
        if ok and ready==false then return nil end
    end
    for _, name in ipairs({"C_SpellBook.IsSpellKnown", "IsSpellKnown", "IsPlayerSpell", "C_Spell.IsSpellKnown"}) do
        local parent, key = name:match("^([^.]+)%.(.+)$")
        local fn = parent and _G[parent] and _G[parent][key] or (not parent and _G[name])
        if type(fn)=="function" then
            local ok, value = pcall(fn, spell)
            if ok and type(value)=="boolean" then return value end
        end
    end
end

function E.Known(spell)
    local runtime = ns.ProfRecipeRuntime and ns.ProfRecipeRuntime[spell]
    if runtime and runtime.learned == true then return true end
    for _, name in ipairs({"C_SpellBook.IsSpellKnown", "IsSpellKnown", "IsPlayerSpell", "C_Spell.IsSpellKnown"}) do
        local parent, key = name:match("^([^.]+)%.(.+)$")
        local fn = parent and _G[parent] and _G[parent][key] or (not parent and _G[name])
        if type(fn)=="function" then
            local ok, value = pcall(fn, spell)
            if ok and type(value)=="boolean" then return value end
        end
    end
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

function E.GetEngineeringSpecialization()
    return ns.ProfGates and ns.ProfGates.GetPlannedChoice() or "none"
end
function E.GetEngineeringSpecializationContext(opts)
    return ns.ProfGates and ns.ProfGates.SpecializationContext(opts) or {abilities={}, goals={}, choice="none"}
end
function E.SpecializationFingerprint(context)
    return context and context.fingerprint or ""
end
function E.SpecializationAbilityFingerprint(abilities)
    return ns.ProfGates and ns.ProfGates.SpecAbilityFingerprint(abilities) or ""
end
function E.ToolPlanningEnabled(opts)
    if opts and opts.autoCraftTools ~= nil then return opts.autoCraftTools ~= false end
    if opts and opts.snapshot and opts.snapshot.autoCraftTools ~= nil then return opts.snapshot.autoCraftTools ~= false end
    return not (DungeonsForeverDB and DungeonsForeverDB.prof and DungeonsForeverDB.prof.autoCraftTools == false)
end
function E.ToolFingerprint(slug, opts)
    local parts = {tostring(E.ToolPlanningEnabled(opts)), tostring(ns.ProfTools and ns.ProfTools.revision or 0)}
    for _, tool in ipairs(ns.ProfTools and ns.ProfTools[slug] or {}) do
        parts[#parts+1] = table.concat({tool.spell or 0, tool.item or 0, tool.minSkill or 0, tostring(tool.bindOnPickup or false)}, ":")
    end
    return table.concat(parts, "|")
end
local function planningToolRecipe(slug, spell, snapshot)
    for _, recipe in ipairs(snapshot and snapshot.recipes or {}) do
        if recipe.profession==slug and recipe.spell==spell then return recipe end
    end
    -- A supplied snapshot owns its recipe observations. Never mix live client
    -- requirements into an existing execution or synthetic input boundary.
    if not snapshot and E.FindRecipe then return E.FindRecipe(slug, spell) end
end
function E.RequiredLevelingTool(slug, tool)
    -- Preserve the native catalogue. Transmutation equipment is not a gate
    -- for an ordinary potion route; actual dependencies are acquired normally.
    return not tool.optional and not (slug=="alchemy" and (tool.item==9149 or tool.item==13503))
end
function E.HasToolGoals(slug, opts)
    if not E.ToolPlanningEnabled(opts) then return false end
    local target = tonumber(opts and opts.target) or 300
    for _, tool in ipairs(ns.ProfTools and ns.ProfTools[slug] or {}) do
        if E.RequiredLevelingTool(slug,tool) then
            local recipe = planningToolRecipe(slug, tool.spell, opts and opts.snapshot)
            if not recipe or type(recipe.learn)~="number" or target>recipe.learn then return true end
        end
    end
    return false
end
function E.LearningSource(recipe)
    if type(recipe) ~= "table" then return end
    if recipe.learnSource == "trainer" or recipe.trainerObserved then return "trainer" end
    local spell = recipe.spell or recipe[1]
    local runtime = ns.ProfRecipeRuntime and ns.ProfRecipeRuntime[spell]
    if runtime and runtime.trainerObserved then return "trainer" end
    return ns.ProfGates and ns.ProfGates.LearningSource(spell) or recipe.learnSource
end
function E.ResolveRecipe(seed, slug)
    if type(seed) ~= "table" then return end
    local r = copy(seed)
    r.profession = slug or r.profession
    local rt = ns.ProfRecipeRuntime and ns.ProfRecipeRuntime[r.spell]
    local client = false
    if rt then
        if materialsValid(rt.mats) and (#rt.mats > 0 or rt.learned or rt.validated or rt.trainerObserved) then
            r.mats = copy(rt.mats); r.materialSource = "client"; client = true
        end
        if positiveInteger(rt.item) then r.item = rt.item; client = true end
        if positiveInteger(rt.count) then
            r.count = rt.count; r.outputMin = rt.outputMin or rt.count; r.outputMax = rt.outputMax or rt.count
            r.variableOutput = rt.variableOutput; r.outputSource = "client"; client = true
        end
        if rt.variableOutput then
            r.variableOutput = true
            if positiveInteger(rt.outputMin) and positiveInteger(rt.outputMax) and rt.outputMax >= rt.outputMin then
                r.count = rt.outputMin; r.outputMin = rt.outputMin; r.outputMax = rt.outputMax
                r.outputBasis = "minimum"; r.outputConflict = nil
            elseif positiveInteger(r.count) then r.outputBasis = "reference"
            else r.outputConflict = true end
        end
        if rt.learn then r.learn = rt.learn; r.skillSource = "client" end
        if rt.cooldown ~= nil and (rt.cooldown or r.cooldown ~= true or rt.cooldownVerified) then
            r.cooldown = rt.cooldown; r.cooldownUnknown = nil
        end
        if rt.unavailable == true or rt.available == false then r.clientUnavailable = true end
        if rt.available == true and not r.clientUnavailable then r.clientAvailable = true end
        if rt.trainerObserved then
            r.trainerObserved = true; r.trainerAvailable = rt.trainerAvailable
            r.learnSource = "trainer"; r.clientAvailable = true; r.clientUnavailable = nil
        end
    end
    local d = E.ClientStore()
    r.learningRequirements = copy(d.learningRequirements and d.learningRequirements[r.spell])
    local roster = d.recipeRosters and d.recipeRosters[r.profession]
    if roster and roster.complete and not roster.ids[r.spell] and not (rt and rt.trainerObserved) then
        r.clientUnavailable = true; r.clientAvailable = nil
    end
    r.materialSource = r.materialSource or (materialsValid(r.mats) and "catalogue" or "unknown")
    r.outputSource = r.outputSource or ((positiveInteger(r.count) or not r.item) and "catalogue" or "unknown")
    r.outputMin = r.outputMin or r.count
    r.outputMax = r.outputMax or r.count
    r.clientPending = not materialsValid(r.mats) or (r.item and not positiveInteger(r.count)) or nil
    r.dataSource = client and "mixed" or "catalogue"
    r.skillSource = r.skillSource or "catalogue"
    r.key = r.profession and r.spell and r.profession .. ":" .. r.spell or r.key
    return r
end
function E.Normalize(row, slug, kind)
    if type(row) ~= "table" then return end
    local r
    if row.spell then r = copy(row)
    elseif kind == "enchants" then
        r = {spell=row[14], item=row[15], count=1, mats=row[9], learn=row[5], yellow=row[6], green=row[7], grey=row[8], source=row[10]}
    elseif kind == "crafted" then
        r = {spell=row[1], item=row[2], count=row[3], mats=row[8], learn=row[4], yellow=row[5], green=row[6], grey=row[7], formula=tonumber(row[9])}
    else
        local formula = row[13]
        r = {spell=row[1], item=row[2], count=row[3], mats=row[12], learn=row[7], yellow=row[8], green=row[9], grey=row[10],
            source=row[14], formula=type(formula)=="table" and formula[1] or nil, category=row[4]}
    end
    if not positiveInteger(r.spell) then return end
    if not r.item and r.count == nil then r.count = 0 end
    if r.count == nil then r.count = 1 end
    r.profession = slug or r.profession
    r.yellow = r.yellow or r.learn
    r.green = r.green or (r.yellow and r.grey and (r.yellow+r.grey)/2) or r.yellow
    r.catalogue = true
    r = E.ResolveRecipe(r, r.profession)
    local verifyCooldown = r.cooldownVerificationRequired == true or r.cooldownVerificationRequired == 1
        or r.category == "Transmutes" or r.spell == 18560
    if r.cooldown == nil then
        local fn = (C_Spell and C_Spell.GetSpellBaseCooldown) or GetSpellBaseCooldown
        local ok, ms = false, nil
        if fn then ok, ms = pcall(fn, r.spell) end
        if ok and type(ms)=="number" then r.cooldown = ms > 0
        elseif not verifyCooldown then r.cooldown = false end
    end
    -- A zero base cooldown does not verify daily/shared recipe restrictions.
    -- Apply this after runtime overrides too: ReadRecipe may have captured a
    -- zero base duration without receiving an explicit hasCooldown result.
    local runtime = ns.ProfRecipeRuntime and ns.ProfRecipeRuntime[r.spell]
    if verifyCooldown and not r.cooldown and not (runtime and runtime.cooldownVerified) then
        r.cooldownUnknown = true
    end
    return r
end
function E.FindRecipe(slug, spell)
    local group = ns.ProfRecipes and ns.ProfRecipes[slug]
    for _, row in ipairs(group and group.rows or {}) do
        if row[1] == spell then return E.Normalize(row, slug, "rows") end
    end
    -- Retain dev's established upgrade data before adding the generic crafted
    -- and enchant reference lists. Live observations still override either.
    local ri = ns.ProfLeveling and ns.ProfLeveling[slug] and ns.ProfLeveling[slug].rinfo and ns.ProfLeveling[slug].rinfo[spell]
    if ri then
        local r = copy(ri); r.spell=spell; r.item=r.item or r.makes
        r.formula=r.formula or r.formulaID
        return E.Normalize(r, slug)
    end
    for _, kind in ipairs({"crafted", "enchants"}) do
        for _, row in ipairs(group and group[kind] or {}) do
            if (kind=="enchants" and row[14] or row[1]) == spell then return E.Normalize(row, slug, kind) end
        end
    end
end
function E.LearningEligibility(recipe, snapshot, state)
    if type(recipe) ~= "table" then return false, "clientDataPending" end
    snapshot = snapshot and (snapshot.snapshot or snapshot)
    if recipe.clientUnavailable then return false, "clientUnavailable", {status="blocked"} end
    local spell, key = recipe.spell or recipe[1], recipe.key
    key = key or (recipe.profession and recipe.profession .. ":" .. tostring(spell))
    local known = state and state.learned or snapshot and snapshot.known
    if known and (known[key] or known[spell]) or not known and E.Known(spell) then return true, nil, {status="learned"} end
    local requirement = recipe.learningRequirements
    local current = state and state.skill and state.skill[recipe.profession]
        or snapshot and snapshot.professions and snapshot.professions[recipe.profession] and snapshot.professions[recipe.profession].cur
    if requirement then
        local level = snapshot and snapshot.level or (not snapshot and UnitLevel and UnitLevel("player"))
        if type(requirement.level)=="number" and requirement.level>0 then
            if type(level)~="number" then return false,"clientDataPending",{status="unknown"} end
            if level<requirement.level then return false,"characterLevelRequired",{status="blocked"} end
        end
        if type(requirement.skill)=="number" and requirement.skill>0 then
            if type(current)~="number" then return false,"clientDataPending",{status="unknown"} end
            if current<requirement.skill then return false,"skillRequired",{status="blocked"} end
        end
    end
    local G = ns.ProfGates
    local ability = G and G.RequiredAbility(spell) or 0
    local abilities = state and state.specializationAbilities or {}
    local actual = snapshot and (snapshot.specializationAbilities or snapshot.abilities)
        or G and G.Abilities() or {}
    if ability>0 and abilities[ability]~=true and actual[ability]~=true then
        if abilities[ability]==false or actual[ability]==false then return false,"specializationRequired",{status="blocked",requiredAbility=ability,requiredAbilities={ability}} end
        return true,nil,{status="unknown",requiredAbility=ability,hasPending=true}
    end
    if G and G.HasPending(spell) then return true,nil,{status="unknown",hasPending=true} end
    if recipe.trainerAvailable==true or requirement or (G and G.LearningSource(spell)) then return true,nil,{status="allowed"} end
    return true,nil,{status="unknown"}
end
E.RecipeSpecializationAllowed = E.LearningEligibility

local function vendorQuote(o)
    return type(o) == "table" and o.unlimited == true and type(o.price) == "number"
        and o.price >= 0 and o.available ~= false and o.purchasable ~= false
        and not o.hasExtendedCost and (not o.currencyID or o.currencyID == 0)
end

function E.PreferredVendorOffers(offers, eligible)
    local db=ns.VendorPriceDB
    return db and db.PreferredOffers and db.PreferredOffers(offers,eligible) or (offers or {})
end

local function formulaContext(context)
    context=context or {}
    return context.snapshot or context
end
-- This is a purchase-source policy. Learned recipes and explicit trainer
-- learning paths keep their existing eligibility regardless of the setting.
function E.AllowLimitedFormulas(context)
    if context and context.allowLimitedFormulas~=nil then return context.allowLimitedFormulas==true end
    local snapshot=context and context.snapshot
    if snapshot and snapshot.allowLimitedFormulas~=nil then return snapshot.allowLimitedFormulas==true end
    local db=DungeonsForeverDB and DungeonsForeverDB.prof
    return db and db.autoBuyLimitedFormulas==true or false
end
function E.LimitedFormulaOffer(offer)
    if offer.unlimited==true then return false end
    if offer.limited==true or offer.stockStatus=="limited"
        or (type(offer.stock)=="number" and offer.stock>=0)
        or (type(offer.maxStock)=="number" and offer.maxStock>=0) then return true end
    -- Normalized offers also use unlimited=false for missing stock evidence.
    if offer.stockUnknown or offer.stockStatus=="unknown" then return false end
    return offer.unlimited==false
end
local function recipeKnown(r,context)
    if context.professions and context.professions[r.profession] and context.professions[r.profession].unlearned then return false end
    if context.known then return context.known[r.key]==true or context.known[r.spell]==true end
    return E.Known(r.spell)
end
local function hasEntries(t) return type(t)=="table" and next(t)~=nil end
local function questSource(source)
    if source.questOnly or source.quest or hasEntries(source.quests) or source.type=="quest" or source.kind=="quest" then return true end
    -- `read=classic/wowhead` is scrape provenance, and numeric skill is the
    -- required profession level. Neither field identifies a quest reward.
    for _,key in ipairs({"skill","notes","description"}) do
        local value=source[key]
        if type(value)=="string" and (value:lower():find("quest",1,true) or value:find("任务",1,true) or value:find("任務",1,true)) then return true end
    end
    return false
end
-- Injected snapshots may use bare finite budgets. Live client observations must
-- be complete, exclude our auctions, and still be fresh at the capture boundary.
local function validSupply(entry,stamp,live)
    if type(entry)~="table" or type(entry.quantity)~="number" or entry.quantity<0
        or entry.quantity==math.huge or entry.quantity~=floor(entry.quantity)
        or entry.complete==false or entry.ownerExcluded==false then return false end
    if entry.source=="auctionator-daily-maximum" or entry.source=="auctionator-update"
        or entry.source=="auctionator-history" then return false end
    if live or entry.source=="client-auction-results" then
        if entry.source~="client-auction-results" or entry.complete~=true or entry.ownerExcluded~=true
            or type(entry.observedAt)~="number" or entry.observedAt<=0 then return false end
        if stamp and (entry.observedAt>stamp or stamp>(entry.expiresAt or entry.observedAt+1800)) then return false end
    end
    return true
end
function E.AuctionSupplyOf(context,id)
    local entry
    if context and context.auctionSupply then entry=context.auctionSupply[id]
    elseif not context or not context.prices then
        local bridge=ns.AuctionBridge
        if bridge and bridge.GetAuctionSupply then entry=bridge.GetAuctionSupply(id,true) end
    end
    local stamp=context and context.stamp or (not context and time and time())
    if validSupply(entry,stamp,not context) then return entry end
end
local function quoteMetadata(context,id,field,method)
    if context and context[field] then return context[field][id] end
    -- A captured input must not acquire new metadata while its search runs.
    if context and context.prices then return end
    local bridge=ns.AuctionBridge
    if bridge and type(bridge[method])=="function" then return bridge[method](id) end
end
local supplyIdentityFields={"quantity","observedAt","source","complete","ownerExcluded","market","batch","schemaVersion","marketKey","observer"}
local function supplyIdentity(supply)
    if not supply then return false end
    local out={}
    for _,key in ipairs(supplyIdentityFields) do out[key]=supply[key] end
    return out
end
function E.AuctionSupplyChanged(result)
    -- Prices/history have independent freshness. Only quantity evidence belongs
    -- to this comparison, and looking it up never starts a scan or a search.
    for id,previous in pairs(result.auctionSupplyInputs or {}) do
        local current=E.AuctionSupplyOf(nil,id)
        if (previous~=false)~=(current~=nil) then return true end
        if current then
            for _,key in ipairs(supplyIdentityFields) do
                -- A fresh observation of the same offer does not change a route.
                if key~="observedAt" and key~="batch" and previous[key]~=current[key] then return true end
            end
        end
    end
    return false
end
function E.SummarizeAuctionSupply(result,context)
    local seen,needed={},{}
    result.auctionSupplyUnknown=0;result.auctionSupplyObserved=false;result.supplyComplete=true
    result.auctionSupplyShortages={}
    result.auctionSupplyInputs={}
    result.auctionSupplyCandidates={}
    local candidates={}
    local function candidate(id)
        if type(id)=="number" and id>0 and not candidates[id] and not (context and context.nonAuctionable or {})[id] then
            candidates[id]=true;result.auctionSupplyCandidates[#result.auctionSupplyCandidates+1]=id
        end
    end
    for _,r in ipairs(context and context.recipes or {}) do
        for _,m in ipairs(r.mats or {}) do candidate(m[1]) end
        if r.formula and not (context.known or {})[r.key] then candidate(r.formula) end
    end
    -- Include unused, priced candidates: a new quantity for a previously scarce
    -- cheaper recipe also changes the inputs to the saved minimum-cost result.
    for id in pairs(context and context.prices or {}) do
        result.auctionSupplyInputs[id]=supplyIdentity(E.AuctionSupplyOf(context,id))
    end
    for id in pairs(context and context.auctionSupply or {}) do
        result.auctionSupplyInputs[id]=supplyIdentity(E.AuctionSupplyOf(context,id))
    end
    for _,list in ipairs({result.mats or {},result.formulas or {}}) do
        for _,entry in ipairs(list) do
            local id=entry.id or entry[1]
            entry.priceObservedAt=quoteMetadata(context,id,"priceObservedAt","GetAuctionPriceObservedAt")
            if (entry.source=="ah" or entry.source=="auction") and not entry.known then
                candidate(id)
                local supply=E.AuctionSupplyOf(context,id)
                result.auctionSupplyInputs[id]=supplyIdentity(supply)
                entry.supplyObserved=supply~=nil
                entry.supplyStatus=supply and "verified" or (context and context.auctionSupplyStatus or {})[id] or "unknown"
                entry.supplyLimited=nil;entry.supplyRequired=nil;entry.supplyObservedAt=nil;entry.supplySource=nil;entry.supplyMethod=nil
                entry.supplyOwnerExcluded=nil;entry.supplyObservedPrice=nil
                entry.supplyMarket=nil;entry.supplyBatch=nil;entry.supplySchemaVersion=nil
                entry.supplyHistoryQuantity=nil;entry.supplyHistoryObservedAt=nil
                local history=quoteMetadata(context,id,"auctionSupplyHistory","GetAuctionSupplyHistory")
                if type(history)=="table" and type(history.quantity)=="number" and history.quantity>=0
                    and history.quantity<math.huge and history.quantity==floor(history.quantity) then
                    entry.supplyHistoryQuantity=history.quantity;entry.supplyHistoryObservedAt=history.observedAt
                end
                if supply then
                    entry.availableCount=supply.quantity;entry.supplyComplete=supply.complete~=false
                    entry.supplyObservedAt=supply.observedAt
                    entry.supplySource=supply.source;entry.supplyOwnerExcluded=supply.ownerExcluded
                    entry.supplyMethod=supply.method
                    entry.supplyObservedPrice=supply.observedPrice or supply.market;entry.supplyMarket=supply.market
                    entry.supplyBatch=supply.batch;entry.supplySchemaVersion=supply.schemaVersion
                    result.auctionSupplyObserved=true
                    needed[id]=(needed[id] or 0)+(entry.count or entry[2] or 1)
                    entry.supplyLimited=needed[id]>supply.quantity or nil
                    result.supplyComplete=result.supplyComplete and supply.complete~=false
                        and supply.ownerExcluded~=false and not entry.supplyLimited
                else
                    entry.availableCount=nil;entry.supplyComplete=false;result.supplyComplete=false
                    if not seen[id] then result.auctionSupplyUnknown=result.auctionSupplyUnknown+1 end
                end
                seen[id]=true
            end
        end
    end
    -- Show the same aggregate demand on material and teaching-item rows.
    for _,list in ipairs({result.mats or {},result.formulas or {}}) do
        for _,entry in ipairs(list) do
            local id=entry.id or entry[1]
            if entry.supplyObserved and needed[id] then
                entry.supplyRequired=needed[id]
                entry.supplyLimited=needed[id]>(entry.availableCount or 0) or nil
            end
        end
    end
    local shortages={}
    local function shortage(d)
        if d.code=="auctionSupplyLimited" and d.item and not shortages[d.item] then
            shortages[d.item]=true;result.auctionSupplyShortages[#result.auctionSupplyShortages+1]=copy(d)
        end
    end
    if result.targetReached~=true then
        for _,d in ipairs(result.blockingDiagnostics or {}) do shortage(d) end
        if result.feasible==false then for _,d in ipairs(result.diagnostics or {}) do shortage(d) end end
    end
    result.supplyComplete=result.supplyComplete and #result.auctionSupplyShortages==0
    result.purchaseVerified=result.targetReached==true and result.supplyComplete and result.costComplete~=false
        and result.learningComplete~=false and result.formulaComplete~=false
    table.sort(result.auctionSupplyCandidates)
    result.auctionSupplyRevision=3
    return result
end
function E.FormulaFor(r,context,auctionRemaining,purchaseSource)
    if type(r)~="table" then return end
    context=formulaContext(context)
    local id=tonumber(r.formula or r.formulaID)
    local known=recipeKnown(r,context)
    local sources=copy(r.source or {})
    local meta=id and ns.ProfFormulaMeta and ns.ProfFormulaMeta[id]
    meta=meta and {quests=meta.source and meta.source.quests,status="confirmed",questOnly=meta.source and meta.source.questOnly,coverage="partial"}
    if meta then
        sources.quests=copy(meta.quests)
        -- A reward relationship proves an alternative, not exclusivity. Only
        -- a complete acquisition inventory may suppress other purchase paths.
        sources.questOnly=meta.coverage=="complete" and meta.questOnly==true or nil
        sources.acquisitionCoverage=meta.coverage
    end
    -- Procurement sources must be rebuilt from the new item/NPC records.
    -- Recipe-catalogue vendor annotations cannot establish a supplier.
    sources.vendors=nil
    local quest=questSource(sources)
    local exclusiveQuest=meta and meta.status=="confirmed" and meta.coverage=="complete" and meta.questOnly==true
    if not id or id<=0 then
        if not quest then return end
        id=nil
    end
    -- An observed trainer path does not require purchasing the teaching item.
    if E.LearningSource(r)=="trainer" then return end
    local entry={id=id,count=1,need=1,spell=r.spell,profession=r.profession,recipeKey=r.key,
        known=known,sources=sources,recipe=r,recipes={{profession=r.profession,spell=r.spell,key=r.key,source=sources}},
        questOnly=exclusiveQuest and not hasEntries(sources.vendors) and not hasEntries(sources.drops) or false,
        questAcquisition=quest or false,
        vendorOffers={},source="unknown",usable=true}
    local ah=id and context.prices and context.prices[id]
    if ah==nil and id and not context.prices then
        local ra=ns.ProfRouteAuto; if ra and ra.AHPriceOf then ah=ra.AHPriceOf(id) end
    end
    if type(ah)=="number" and ah>0 and not (context.nonAuctionable and context.nonAuctionable[id]) then entry.ahPrice=ah end
    local offers=id and context.formulaOffers and context.formulaOffers[id]
    if not offers and not context.prices and id and ns.VendorPriceDB and ns.VendorPriceDB.GetFormulaOffers then
        offers=ns.VendorPriceDB.GetFormulaOffers(id,context,r.source)
    end
    if not offers and id and context.offers then offers=context.offers[id] end
    -- Price seeds and anonymous catalogue placeholders are not suppliers.
    -- Currency exchanges belong outside this gold procurement list.
    for _,offer in ipairs(offers or {}) do
        local currency=tonumber(offer.currencyID or offer.cur) or 0
        if type(offer.npcID)=="number" and offer.npcID>0 and not offer.priceOnly
            and currency==0 and not offer.hasExtendedCost then
            entry.vendorOffers[#entry.vendorOffers+1]=offer
        end
    end
    local vendors,seen={},{}
    for _,o in ipairs(entry.vendorOffers) do
        if o.npcID and not seen[o.npcID] then
            vendors[#vendors+1]={id=o.npcID,name=o.npcName or o.name or (ns.ProfVendorNames and ns.ProfVendorNames[o.npcID]) or ("#"..o.npcID),zone=o.zone}
            seen[o.npcID]=true
        end
    end
    sources.vendors=vendors
    entry.questOnly=exclusiveQuest and not hasEntries(vendors) and not hasEntries(sources.drops) or false
    local supply=id and E.AuctionSupplyOf and E.AuctionSupplyOf(context,id)
    local ahAvailable=auctionRemaining or (supply and supply.quantity)
    local ahUsable=context.noFormula~=true and entry.ahPrice and (ahAvailable==nil or ahAvailable>=1)
    if supply then entry.availableCount=supply.quantity;entry.supplyObserved=true;entry.supplyComplete=supply.complete==true end
    local best,bestCost
    local allowLimited=E.AllowLimitedFormulas(context)
    local function purchasable(o)
        local factionOK=not o.faction or not context.faction or o.faction==context.faction or o.faction=="N" or o.faction=="Neutral" or o.faction=="AH" or o.faction=="Both"
        local quantity=o.quantity or o.bundleSize or 1
        return not (not allowLimited and E.LimitedFormulaOffer(o)) and factionOK
            and o.available~=false and o.purchasable~=false and o.priceUsable~=false
            and type(o.price)=="number" and o.price>=0 and positiveInteger(quantity)
            and (type(o.stock)~="number" or o.stock<0 or o.stock>=quantity)
    end
    for _,o in ipairs(entry.vendorOffers) do
        if o.unlimited==true then entry.unlimited=true
        elseif E.LimitedFormulaOffer(o) then entry.limited=true
        else entry.stockUnknown=true end
        local limitedBlocked=not allowLimited and E.LimitedFormulaOffer(o)
        if limitedBlocked then entry.limitedVendorDisabled=true end
    end
    for _,o in ipairs(E.PreferredVendorOffers(entry.vendorOffers,purchasable)) do
        if purchasable(o) then
            local quantity=o.quantity or o.bundleSize or 1
            local unit=o.price/quantity
            if not entry.vendorPrice or unit<entry.vendorPrice then entry.vendorPrice=unit end
            local cost=o.price -- One indivisible purchase supplies the formula.
            if not bestCost or cost<bestCost then best,bestCost=o,cost end
        end
    end
    if best then sources.drops=nil end
    if purchaseSource~="ah" and bestCost~=nil and (not ahUsable or bestCost<=entry.ahPrice) then
        entry.source="vendor";entry.cost=bestCost;entry.offer=best;entry.npcID=best.npcID
        local quantity=best.quantity or best.bundleSize or 1
        entry.bundleSize=positiveInteger(quantity) and quantity or 1;entry.count=entry.bundleSize
        entry.availabilityUncertain=best.stockUnknown==true or best.stockStatus=="unknown"
            or best.unlimited~=true and type(best.stock)~="number" or nil
    elseif ahUsable then entry.source="ah";entry.cost=entry.ahPrice
    elseif quest then entry.source="quest";entry.usable=known
    end
    if known then entry.cost=0;entry.usable=true end
    if not known and entry.cost==nil then entry.usable=false end
    entry.unpriced=not known and entry.cost==nil or nil
    entry.costComplete=known or (entry.cost~=nil and not entry.availabilityUncertain) or false
    entry.sourceType=entry.source;entry.totalCost=entry.cost;entry.blocked=not entry.usable
    entry.vendor=entry.source=="vendor"
    if entry.blocked then
        entry.reason=context.noFormula==true and not entry.limitedVendorDisabled and "vendorFormulaRequired"
            or entry.ahPrice and ahAvailable~=nil and ahAvailable<1 and "auctionSupplyLimited"
            or entry.limitedVendorDisabled and "limitedFormulaDisabled" or "formulaUnavailable"
    end
    return entry
end
function E.CollectFormulas(steps,slug,context)
    local snap=formulaContext(context);local list,byID={},{};local total,complete=0,true
    for _,step in ipairs(steps or {}) do
        if not step.checkpoint and (step[4] or step.count or 0)>0 then
            local profession=step.profession or slug
            local r=step.recipe or (snap.byKey and snap.byKey[profession..":"..tostring(step[3] or step.spell)]) or E.FindRecipe(profession,step[3] or step.spell)
            local entry=r and E.FormulaFor(r,snap)
            if entry and not entry.known then
                local key=entry.id or entry.recipeKey or profession..":"..tostring(entry.spell)
                local old=byID[key]
                if old then old.recipes[#old.recipes+1]=entry.recipes[1]
                else
                    byID[key]=entry;list[#list+1]=entry
                    total=total+(entry.cost or 0);complete=complete and entry.costComplete and entry.usable
                end
            end
        end
    end
    table.sort(list,function(a,b) return (a.id or 0)<(b.id or 0) end)
    return list,total,complete
end


function E.Index(s, tick)
    s.recipes = s.recipes or {}
    s.byItem, s.byProfession, s.byKey = {}, {}, {}
    for _, r in ipairs(s.recipes) do
        if tick then tick() end
        r.key = r.key or (r.profession .. ":" .. r.spell)
        r.mats = r.mats or {}
        if not r.clientPending then
            r.count = r.count or 1
            r.yellow = r.yellow or r.learn
            r.green = r.green or r.yellow
        end
        s.byKey[r.key] = r
        local p = s.byProfession[r.profession]
        if not p then p = {}; s.byProfession[r.profession] = p end
        p[#p + 1] = r
        if type(r.item) == "number" and r.item > 0 and type(r.count)=="number" and r.count > 0 then
            local a = s.byItem[r.item]
            if not a then a = {}; s.byItem[r.item] = a end
            a[#a + 1] = r
        end
    end
    for _, field in ipairs({"professions", "known", "prices", "offers", "formulaOffers", "auctionSupplyHistory",
        "priceObservedAt", "auctionSupplyStatus", "nonAuctionable", "vendorItems", "vendorSuppliers", "diagnostics", "toolGoals",
        "toolGoalsPending", "specializationGoals", "specializationAbilities", "retainedToolItems", "toolCraftOnlyItems"}) do
        s[field] = s[field] or {}
    end
    -- Indexing an immutable input never consults the live auction/recipe cache.
    local supply = {}
    for id, entry in pairs(s.auctionSupply or {}) do
        if validSupply(entry,s.stamp) then supply[id] = entry
        else s.auctionSupplyStatus[id]=s.auctionSupplyStatus[id] or "incomplete" end
        if tick then tick() end
    end
    s.auctionSupply = supply
    s.inventory = {}
    s.trainingCosts, s.rankCosts, s.learningRequirements, s.rankRequirements = nil, nil, nil, nil
    s.stations, s.stationRequirements = nil, nil
    return s
end

function E.CaptureToolGoals(s, slug, opts)
    s.autoCraftTools = E.ToolPlanningEnabled(opts)
    s.toolFingerprint = E.ToolFingerprint(slug, opts)
    s.toolGoals, s.toolGoalsPending = {}, {}
    s.retainedToolItems, s.toolCraftOnlyItems = s.retainedToolItems or {}, s.toolCraftOnlyItems or {}
    s.nonAuctionable = s.nonAuctionable or {}
    local G = ns.ProfGates
    local target = tonumber(opts and opts.target) or 300
    for _, tool in ipairs(ns.ProfTools and ns.ProfTools[slug] or {}) do
        if tool.bindOnPickup then s.nonAuctionable[tool.item] = true; s.toolCraftOnlyItems[tool.item] = true end
        if s.autoCraftTools and E.RequiredLevelingTool(slug,tool) then
            local recipe = planningToolRecipe(slug, tool.spell, s)
            if recipe and recipe.item and type(recipe.learn)=="number" and not recipe.clientPending then
                if G and G.ToolOwned(recipe.item) then
                    s.ownedToolItems = s.ownedToolItems or {}; s.ownedToolItems[tool.item] = true
                elseif target>recipe.learn then
                    local goal = copy(tool);goal.profession=slug;goal.item=recipe.item;goal.minSkill=recipe.learn
                    goal.id=slug..":"..recipe.item
                    s.toolGoals[#s.toolGoals+1] = goal;s.retainedToolItems[goal.item] = 1
                    recipe.tool, recipe.toolItem = true, goal.item
                end
            else s.toolGoalsPending[#s.toolGoalsPending+1]={code="toolFactsUnknown",profession=slug,spell=tool.spell} end
        end
    end
    return s
end
function E.CaptureSpecializations(s, opts, slug)
    local G = ns.ProfGates
    if not G then return s end
    local specOpts = copy(opts or {})
    specOpts.profession, specOpts.faction, specOpts.level = slug, s.faction, s.level
    specOpts.snapshot = s
    local spec = G.SpecializationContext(specOpts)
    s.targetProfession, s.engineeringSpecialization = slug, spec.choice
    s.specializationContext, s.specializationAbilities = spec, spec.abilities
    s.specializationFingerprint = spec.fingerprint
    s.specializationGoals = {}
    for _, goal in ipairs(spec.goals or {}) do
        -- Keep blocked goals: their requirements must not silently disappear
        -- from an otherwise apparently complete engineering route.
        s.specializationGoals[#s.specializationGoals+1] = copy(goal)
    end
    return s
end
local function addRecipe(s, slug, row, kind)
    local r = E.Normalize(row, slug, kind)
    if not r or type(r.learn)~="number" or type(r.grey)~="number" or (r.grey<r.learn and not r.knownAtCurrentSkill)
        or not materialsValid(r.mats) then return end
    if s.byKey[r.key] then return end
    s.recipes[#s.recipes+1] = r;s.byKey[r.key] = r
    s.known[r.key] = not (s.professions[slug] and s.professions[slug].unlearned) and E.Known(r.spell) or false
end
function E.NonAuctionableItem(id)
    local fn = (C_Item and C_Item.GetItemInfo) or GetItemInfo
    if type(fn)~="function" then return false end
    local fields = {pcall(fn, id)}
    return fields[1] and (fields[15]==1 or fields[15]==4) or false
end
function E.Capture(slug, opts, tick)
    opts, tick = opts or {}, tick or function() end
    if opts.snapshot then
        local s = copy(opts.snapshot, tick)
        s.professions, s.routeContext = E.RouteProfessions(slug, opts, opts.professions or s.professions or {})
        s.allowLimitedFormulas = E.AllowLimitedFormulas(opts)
        if opts.noFormula~=nil then s.noFormula=opts.noFormula==true end
        if s.coverageComplete == nil then s.coverageComplete = false end
        s.essenceConversions = ns.ProfEssences and ns.ProfEssences.Enabled(slug, opts, s) or false
        -- Explicit fixture/execution snapshots already contain their normalized
        -- tool/specialization facts. Do not replace them with today's client.
        if s.toolGoals == nil then E.CaptureToolGoals(s, slug, opts) end
        if s.specializationContext == nil and ns.ProfGates then E.CaptureSpecializations(s, opts, slug) end
        s = E.Index(s, tick)
        if ns.ProfRecovery then ns.ProfRecovery.Capture(s, opts, tick) end
        return s
    end
    if E.EnsureClientRuntime then E.EnsureClientRuntime() end
    local professions, context = E.RouteProfessions(slug, opts, opts.professions or E.Professions())
    local s = {recipes={},byKey={},known={},prices={},offers={},formulaOffers={},auctionSupply={},auctionSupplyHistory={},auctionSupplyStatus={},
        priceObservedAt={},vendorItems={},vendorSuppliers={},nonAuctionable={},coverageComplete=false,
        professions=copy(professions),routeContext=context,stamp=time and time() or 0,character=E.CharacterKey(),
        allowLimitedFormulas=E.AllowLimitedFormulas(opts),noFormula=opts.noFormula==true}
    s.level = UnitLevel and UnitLevel("player") or nil
    local f = UnitFactionGroup and UnitFactionGroup("player") or nil
    s.faction = f=="Alliance" and "A" or f=="Horde" and "H" or f
    if UnitClass then local ok,_,_,id=pcall(UnitClass,"player");if ok then s.classID=id end end
    if UnitRace then local ok,_,_,id=pcall(UnitRace,"player");if ok then s.raceID=id end end
    -- An unlearned target is a valid 1-to-target preview. A partner is only
    -- required when the user explicitly enables joint profession leveling.
    if context.requiresPartner and not context.partnerValid then return E.Index(s, tick) end
    local loadList, seen = {slug}, {[slug]=true}
    -- Already learned professions may supply a dependency; enabling joint
    -- leveling also permits the selected simulated partner to gain skill.
    for p, info in pairs(professions) do
        if not seen[p] and primaryOf(p) and (not info.unlearned or p==context.partner) then
            loadList[#loadList+1]=p;seen[p]=true
        end
    end
    table.sort(loadList)
    for _, p in ipairs(loadList) do
        local group = ns.ProfRecipes and ns.ProfRecipes[p]
        if E.IndexClientProfession then E.IndexClientProfession(p) end
        for _, kind in ipairs({"rows"}) do
            for _, row in ipairs(group and group[kind] or {}) do
                local spell = kind=="enchants" and row[14] or row[1]
                if E.ReadRecipe and spell then E.ReadRecipe(spell) end
                addRecipe(s,p,row,kind);tick()
            end
        end
        local lv = ns.ProfLeveling and ns.ProfLeveling[p]
        for spell, ri in pairs(lv and lv.rinfo or {}) do
            if E.ReadRecipe then E.ReadRecipe(spell) end
            local r = copy(ri);r.spell=spell;r.item=r.item or r.makes;r.formula=r.formula or r.formulaID
            addRecipe(s,p,r);tick()
        end
        for _, kind in ipairs({"crafted", "enchants"}) do
            for _, row in ipairs(group and group[kind] or {}) do
                local spell = kind=="enchants" and row[14] or row[1]
                if E.ReadRecipe and spell then E.ReadRecipe(spell) end
                addRecipe(s,p,row,kind);tick()
            end
        end
    end
    E.CaptureSpecializations(s, opts, slug)
    E.CaptureToolGoals(s, slug, opts)
    local items = {}
    for _, r in ipairs(s.recipes) do
        if positiveInteger(r.item) then items[r.item]=true end
        if r.formula and not s.known[r.key] and E.LearningSource(r)~="trainer" then items[r.formula]=true end
        for _, m in ipairs(r.mats) do items[m[1]]=true end
        tick()
    end
    for _, goal in ipairs(s.toolGoals or {}) do items[goal.item]=true end
    for _, goal in ipairs(s.specializationGoals or {}) do for _, m in ipairs(goal.inputs or {}) do items[m[1]]=true end end
    s.essenceConversions = ns.ProfEssences and ns.ProfEssences.Enabled(slug, opts, s) or false
    if s.essenceConversions then ns.ProfEssences.ExpandItems(items) end
    local ra, vdb, bridge = ns.ProfRouteAuto, ns.VendorPriceDB, ns.AuctionBridge
    local vendorContext = {character=s.character,faction=s.faction,professions=s.professions,level=s.level}
    s.auctionPriceInputs={}
    for id in pairs(items) do
        if E.NonAuctionableItem(id) then s.nonAuctionable[id]=true end
        local price = ra and ra.AHPriceOf and ra.AHPriceOf(id)
        s.auctionPriceInputs[id]=type(price)=="number" and price>0 and price or false
        if type(price)=="number" and price>0 then s.prices[id]=price end
        local offers = vdb and vdb.GetOffers and vdb.GetOffers(id, vendorContext)
        s.offers[id] = copy(offers or {})
        for _, offer in ipairs(offers or {}) do if vendorQuote(offer) then s.vendorItems[id]=true;break end end
        local supply = E.AuctionSupplyOf(nil, id)
        if supply then s.auctionSupply[id]=copy(supply) end
        s.auctionSupplyStatus[id]=bridge and bridge.GetAuctionSupplyStatus and bridge.GetAuctionSupplyStatus(id) or "unknown"
        if bridge and bridge.GetAuctionSupplyHistory then s.auctionSupplyHistory[id]=copy(bridge.GetAuctionSupplyHistory(id)) end
        if bridge and bridge.GetAuctionPriceObservedAt then s.priceObservedAt[id]=bridge.GetAuctionPriceObservedAt(id) end
        tick()
    end
    for _, r in ipairs(s.recipes) do
        if r.formula and E.LearningSource(r)~="trainer" and not s.formulaOffers[r.formula] then
            local offers = vdb and vdb.GetFormulaOffers and vdb.GetFormulaOffers(r.formula, vendorContext, r.source)
            if not (vdb and vdb.GetFormulaOffers) then
                offers = ns.ProfSupply and ns.ProfSupply.FormulaList and ns.ProfSupply.FormulaList(r.formula) or {}
            end
            s.formulaOffers[r.formula] = copy(offers or {})
        end
        tick()
    end
    s = E.Index(s, tick)
    if ns.ProfRecovery then ns.ProfRecovery.Capture(s, opts, tick) end
    return s
end
