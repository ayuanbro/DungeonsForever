local _, ns = ...

if not ns.LoadForeverPages then return end

local RA = {}
ns.ProfRouteAuto = RA

local CALLER = "DungeonsForever"
local CAP = 300
local MAX_STALE = 2
local MAX_PER_RECIPE = 3
local CACHE_TTL = 600
local CACHE_SLOTS = 4
local G_YELLOW, G_GREEN = 0.5, 0.05

local SCHEME_ORDER = { "cheapest", "matcost", "crafts", "optim" }
local SCHEME_LABEL = {
    cheapest = "最省钱",
    matcost = "材料成本",
    crafts = "次数最少",
    optim = "乐观计数",
}
function RA.SchemeOrder() return SCHEME_ORDER end
function RA.SchemeLabel(s)
    local k = (s and SCHEME_LABEL[s]) and SCHEME_LABEL[s] or "最省钱"
    return type(L) == "table" and L[k] or k
end

function RA.Available()
    return type(Auctionator) == "table"
        and type(Auctionator.API) == "table"
        and type(Auctionator.API.v1) == "table"
        and type(Auctionator.API.v1.GetAuctionPriceByItemID) == "function"
end

local function CallAPI(fn, ...)
    local ok, v = pcall(fn, CALLER, ...)
    if ok then return v end
    return nil
end

local priceCache = {}
local NEG_TTL = 60
local ahReason, ahAge = {}, {}

local function AHPrice(id)
    local c = priceCache[id]
    if c ~= nil then
        if c ~= false then return c end
        local now = (type(time) == "function") and time() or 0
        local t0 = priceCache.__t and priceCache.__t[id] or nil
        if t0 and (now - t0) < NEG_TTL then return nil end
    end
    local p
    if RA.Available() then
        p = CallAPI(Auctionator.API.v1.GetAuctionPriceByItemID, id)
        if type(p) ~= "number" or p <= 0 then p = nil end
        if p and type(Auctionator.API.v1.GetAuctionAgeByItemID) == "function" then
            local age = CallAPI(Auctionator.API.v1.GetAuctionAgeByItemID, id)
            if type(age) == "number" then
                if age > MAX_STALE then
                    ahReason[id], ahAge[id] = "stale", age
                    p = nil
                end
                if age < (priceCache.__minAge or math.huge) then
                    priceCache.__minAge = age
                end
            end
        end
    else
        ahReason[id] = "noapi"
    end
    if not p and ahReason[id] ~= "stale" and ahReason[id] ~= "noapi" then
        ahReason[id] = "norec"
    end
    priceCache[id] = p or false
    if not p then
        priceCache.__t = priceCache.__t or {}
        priceCache.__t[id] = (type(time) == "function") and time() or 0
    end
    if p then priceCache.__any = true end
    return p
end

local vendorCache = {}
local function VendorPrice(id)
    local hit = vendorCache[id]
    if hit ~= nil then return hit or nil end
    local p
    if ns.VendorPriceDB then
        local ok, v = pcall(ns.VendorPriceDB.GetPrice, id)
        if ok and type(v) == "number" and v > 0 then p = v end
    end
    if not p and RA.Available() then
        local fn = Auctionator.API.v1.GetVendorPriceByItemID
        if type(fn) == "function" then
            local v = CallAPI(fn, id)
            if type(v) == "number" and v > 0 then p = v end
        end
    end
    vendorCache[id] = p or false
    return p
end

local function MatPrice(id, soldSet)
    local v = VendorPrice(id)
    if soldSet[id] then return v end
    local a = AHPrice(id)
    if a and v and v < a then return v end
    return a or v
end

local function MatReason(id, soldSet)
    if MatPrice(id, soldSet) then return nil end
    if soldSet[id] then return "novendor" end
    return ahReason[id] or "norec", ahAge[id]
end

function RA.MaxStale()
    return MAX_STALE
end

local sellCache = {}
local function NPCSellPrice(id)
    local hit = sellCache[id]
    if hit then return hit end
    local p
    if C_Item and C_Item.GetItemInfo then
        local ok, a, b, c, d, e, f, g, h, i, j, sell = pcall(C_Item.GetItemInfo, id)
        if ok and type(sell) == "number" and sell > 0 then p = sell end
    end
    if not p and type(GetItemInfo) == "function" then
        local ok, a, b, c, d, e, f, g, h, i, j, sell = pcall(GetItemInfo, id)
        if ok and type(sell) == "number" and sell > 0 then p = sell end
    end
    if not p and C_Item and C_Item.GetItemSellPrice then
        local ok, sell = pcall(C_Item.GetItemSellPrice, id)
        if ok and type(sell) == "number" and sell > 0 then p = sell end
    end
    if p then sellCache[id] = p end
    return p
end

local function ClientKnown(id)
    local dg = ns.ProfHost and ns.ProfHost.DG
    if dg and type(dg.ItemInfo) == "function" then
        return dg.ItemInfo(id) ~= nil
    end
    if C_Item and C_Item.GetItemInfo then
        return (C_Item.GetItemInfo(id)) ~= nil
    end
    return true
end

local MATSOLD_EMPTY = {}
local function MatListCost(mats)
    if type(mats) ~= "table" or #mats == 0 then return nil, 0 end
    local total, unpriced = 0, 0
    for _, m in ipairs(mats) do
        local id, cnt = m[1] or m.id, (m[2] or m.cnt or 1)
        local p = MatPrice(id, MATSOLD_EMPTY)
        if p then total = total + p * cnt else unpriced = unpriced + 1 end
    end
    return total, unpriced
end

function RA.AHPriceOf(itemID)
    if not itemID then return nil end
    return AHPrice(itemID)
end

function RA.NPCSellPriceOf(itemID)
    if not itemID then return nil end
    return NPCSellPrice(itemID)
end

function RA.NPCBuyPriceOf(itemID)
    if not itemID then return nil end
    return VendorPrice(itemID)
end

function RA.NPCBuySupplierOf(itemID)
    if not itemID then return nil end
    local db = ns.VendorPriceDB
    if not (db and db.GetOffers) then return nil end
    local ok, offers = pcall(db.GetOffers, itemID)
    if not ok or type(offers) ~= "table" then return nil end
    local first = offers[1]
    local npc = first and first.npcID
    if not npc then return nil end
    local name = ns.ProfVendorNames and ns.ProfVendorNames[npc] or nil
    if type(name) ~= "string" or name == "" then return nil end
    return name
end

function RA.Cancel(slug)
    local SR = ns.ProfSolverRun
    if not (SR and SR.Stop) then return false end
    if slug and SR.Running and not SR.Running(slug) then return false end
    SR.Stop()
    local UIm = ns.ProfModule
    local plan = UIm and UIm.autoSnapshot
    if type(plan) == "table" and plan.status == "searching" then
        plan.status = "stopped"
        plan.searchComplete = true
        plan.budgetLimited = true
        UIm.solverFrac = nil
    end
    return true
end

function RA.MatListCost(mats)
    return MatListCost(mats)
end

local function RequestProduct(id)
    local H = ns.ProfHost
    local dg = H and H.DG
    if dg and dg.RequestItem then pcall(dg.RequestItem, id) end
end

local function SnapshotSec()
    local A = Auctionator
    local st = (type(A) == "table") and A.SavedState
    if type(st) ~= "table" then return nil end
    local best
    for _, k in ipairs({ "TimeOfLastGetAllScan", "TimeOfLastReplicateScan", "TimeOfLastBrowseScan" }) do
        local v = tonumber(st[k])
        if v and v > 0 and (not best or v > best) then best = v end
    end
    if not best then return nil end
    local now = (type(time) == "function") and time() or 0
    local age = now - best
    if age < 0 then return nil end
    return age
end

function RA.HasPriceData()
    if priceCache.__any then return true end
    local supply = ns.ProfSupply
    return (supply and supply.Ready and supply.Ready()) and true or false
end

function RA.SnapshotAge()
    return SnapshotSec()
end

local ICON_G = "|TInterface\\MoneyFrame\\UI-GoldIcon:0|t"
local ICON_S = "|TInterface\\MoneyFrame\\UI-SilverIcon:0|t"
local ICON_C = "|TInterface\\MoneyFrame\\UI-CopperIcon:0|t"

function RA.MoneyStr(copper, opt)
    copper = tonumber(copper)
    if copper and copper < 0 then
        return "-" .. RA.MoneyStr(-copper, opt)
    end
    if not copper or copper <= 0 then
        return "0" .. ICON_C
    end
    if opt == "copper" then
        local g = math.floor(copper / 10000)
        local s = math.floor(copper / 100) % 100
        local c = copper % 100
        if g > 0 then
            return format("%d%s%02d%s%02d%s", g, ICON_G, s, ICON_S, c, ICON_C)
        end
        return format("%d%s%02d%s", s, ICON_S, c, ICON_C)
    end
    local g = math.floor(copper / 10000)
    local s = math.floor(copper / 100) % 100
    local c = copper % 100
    if g > 0 then
        return format("%d%s%02d%s%02d%s", g, ICON_G, s, ICON_S, c, ICON_C)
    end
    if s > 0 then
        return format("%d%s%02d%s", s, ICON_S, c, ICON_C)
    end
    return format("%d%s", c, ICON_C)
end

local function Gain(skill, c)
    if skill < c.learn or skill >= c.grey then return nil end
    if skill < c.yellow then return 1.0 end
    if skill < c.green then
        local span = c.green - c.yellow
        if span <= 0 then return G_YELLOW end
        local t = (skill - c.yellow) / span
        return 1.0 - t * (1.0 - G_YELLOW)
    end
    local span = c.grey - c.green
    if span <= 0 then return G_GREEN end
    local t = (skill - c.green) / span
    return G_YELLOW - t * (G_YELLOW - G_GREEN)
end

local function LearnKnown(spell)
    if type(IsSpellKnown) == "function" then
        local ok, v = pcall(IsSpellKnown, spell)
        if ok and v then return true end
    end
    if type(IsPlayerSpell) == "function" then
        local ok, v = pcall(IsPlayerSpell, spell)
        if ok and v then return true end
    end
    return false
end

function RA.SpellKnown(spell)
    return LearnKnown(spell)
end

local rtGate = 0
local function RouteTick()
    if not coroutine.running() then return end
    if not debugprofilestop then return end
    local now = debugprofilestop()
    if now - rtGate >= 3 then
        rtGate = now
        coroutine.yield()
    end
end

-- Keep the dev tuple schema while sharing client corrections with the solver.
local function ResolvedRow(row, slug, spell)
    local E=ns.ProfEconomy
    if not (E and E.ResolveRecipe) then return row end
    local seed
    if row.mats or row.learn then
        seed={};for key,value in pairs(row) do seed[key]=value end
        seed.spell=spell or seed.spell;seed.item=seed.item or seed.makes
    else
        seed={spell=row[1],item=row[2],count=row[3],learn=row[7],yellow=row[8],green=row[9],grey=row[10],
            mats=row[12],formula=type(row[13])=="table" and row[13][1] or nil,source=row[14],category=row[4]}
    end
    local resolved=E.Normalize and E.Normalize(seed,slug) or E.ResolveRecipe(seed,slug)
    if not resolved then return row end
    if row.mats or row.learn then resolved.makes=resolved.item;return resolved end
    local out={};for key,value in pairs(row) do out[key]=value end
    out[2],out[3],out[7],out[8],out[9],out[10],out[12]=resolved.item,resolved.count,resolved.learn,resolved.yellow,resolved.green,resolved.grey,resolved.mats
    out.clientUnavailable,out.clientPending=resolved.clientUnavailable,resolved.clientPending
    out.cooldown,out.cooldownUnknown=resolved.cooldown,resolved.cooldownUnknown
    out.requiredDataUnknown=resolved.requiredDataUnknown
    out.outputMin,out.outputMax,out.variableOutput=resolved.outputMin,resolved.outputMax,resolved.variableOutput
    return out
end

local function BuildCandidates(slug, opts)
    local specBlocked = 0
    local pr = ns.ProfRecipes
    local Rg = pr and pr[slug]
    local LV = ns.ProfLeveling and ns.ProfLeveling[slug]
    if not (Rg and (type(Rg.rows) == "table"
                    or (LV and type(LV.rinfo) == "table"))) then return nil end
    local soldSet = {}
    if LV and type(LV.sold) == "table" then
        for _, id in ipairs(LV.sold) do soldSet[id] = true end
    end

    local cands, recOf = {}, {}
    for _, rec in ipairs(Rg.rows or {}) do
        RouteTick()
        rec=ResolvedRow(rec,slug)
        local spell, learn, yellow, green, grey = rec[1], rec[7], rec[8], rec[9], rec[10]
        local reagents = rec[12]
        if type(spell) == "number" and type(learn) == "number"
           and type(grey) == "number" and grey > learn
           and type(reagents) == "table" and #reagents > 0 then
            local ok = not rec.clientUnavailable and not rec.clientPending and not rec.cooldown and not rec.cooldownUnknown
            local skipFormula = opts.noFormula
            if ok and skipFormula and type(rec[13]) == "table" and type(rec[13][1]) == "number" then
                local SM = ns.ProfSourceMerge
                local view = (SM and SM.SourceOf and SM.SourceOf(rec[13][1])) or rec[14]
                local kind = (SM and SM.Primary) and SM.Primary(view) or nil
                if kind ~= "vendor" then ok = false end
            end
            if ok and opts.learnedOnly and not LearnKnown(spell) then ok = false end
            if ok and not LearnKnown(spell) and type(rec[13]) == "table"
               and type(rec[13][1]) == "number" then
                local PDm = ns.ProfModule
                local skipUnknown = (PDm and PDm.SettingRaw and PDm.SettingRaw("autoSkipUnpricedFormulas")) and true or false
                if skipUnknown and not MatPrice(rec[13][1], soldSet) then ok = false end
            end
            if ok then
                local cost, unpriced = 0, false
                for _, m in ipairs(reagents) do
                    local p = MatPrice(m[1], soldSet)
                    if p then
                        cost = cost + p * (m[2] or 1)
                    else
                        unpriced = true
                    end
                end
                if ok then
                    local itemID = rec[2]
                    local f = rec[13]
                    local fcost, funpriced = 0, false
                    if type(f) == "table" and type(f[1]) == "number" and not LearnKnown(spell) then
                        local fp = MatPrice(f[1], soldSet)
                        if fp then fcost = fp else funpriced = true end
                    end
                    local base, unknown = 0, false
                    for _, m in ipairs(reagents) do
                        if not ClientKnown(m[1]) then unknown = true end
                        local sp = NPCSellPrice(m[1])
                        if sp then base = base + sp * (m[2] or 1) end
                    end
                    local cY = (type(yellow) == "number") and yellow or learn
                    cands[#cands + 1] = {
                        spell = spell, item = (type(itemID) == "number") and itemID or nil,
                        learn = learn, yellow = cY,
                        green = (type(green) == "number") and green or yellow or learn,
                        grey = grey, mats = reagents, cost = cost, unpriced = unpriced,
                        fcost = fcost, funpriced = funpriced or nil, base = base, cd = (rec[4] == "Transmutes") or nil,
                        unknown = unknown or nil,
                        learnO = math.max(1, math.min(learn, cY - 25)),
                    }
                    recOf[spell] = rec
                end
            end
        end
    end
    if LV and type(LV.rinfo) == "table" then
        for spell, ri in pairs(LV.rinfo) do
            RouteTick()
            ri=ResolvedRow(ri,slug,spell)
            if type(spell) == "number" and not recOf[spell]
               and type(ri.learn) == "number" and type(ri.grey) == "number"
               and ri.grey > ri.learn
               and type(ri.mats) == "table" and #ri.mats > 0 then
                local ok = not ri.clientUnavailable and not ri.clientPending and not ri.cooldown and not ri.cooldownUnknown
                    and not (opts.learnedOnly and not LearnKnown(spell))
                local cost, unpriced = 0, false
                if ok then
                    for _, m in ipairs(ri.mats) do
                        local p = MatPrice(m[1], soldSet)
                        if p then
                            cost = cost + p * (m[2] or 1)
                        else
                            unpriced = true
                        end
                    end
                end
                if ok then
                    local y = (type(ri.yellow) == "number") and ri.yellow or ri.learn
                    local g = (type(ri.green) == "number") and ri.green or y
                    local base, unknown = 0, false
                    for _, m in ipairs(ri.mats) do
                        if not ClientKnown(m[1]) then unknown = true end
                        local sp = NPCSellPrice(m[1])
                        if sp then base = base + sp * (m[2] or 1) end
                    end
                    cands[#cands + 1] = {
                        spell = spell, item = (type(ri.makes) == "number") and ri.makes or nil,
                        learn = ri.learn, yellow = y, green = g, grey = ri.grey,
                        mats = ri.mats, cost = cost, unpriced = unpriced,
                        fcost = 0, base = base, unknown = unknown or nil,
                        learnO = math.max(1, math.min(ri.learn, y - 25)),
                    }
                    recOf[spell] = ri
                end
            end
        end
    end
    local Pol = ns.ProfEconomy
    local pol = Pol and Pol.GetPolicies and Pol.GetPolicies(slug) or nil
    if pol and next(pol) then
        local kept = {}
        for _, c in ipairs(cands) do
            if pol[slug .. ":" .. tostring(c.spell)] ~= "ban" and pol[c.spell] ~= "ban" then
                kept[#kept + 1] = c
            end
        end
        cands = kept
    end
    local G = ns.ProfGates
    if G and not opts.ignoreSpecGate then
        local kept, blocked = {}, 0
        for _, c in ipairs(cands) do
            local allowed, need = G.Allowed(slug, c.spell)
            if allowed then
                if G.TrainerTaught(c.spell) then c.fcost = 0; c.funpriced = nil; c.taughtByTrainer = true end
                kept[#kept + 1] = c
            else
                blocked = blocked + 1
                c.specBlocked = need
            end
        end
        cands = kept
        specBlocked = blocked
    end
    return cands, recOf, soldSet, specBlocked
end

local function Eligible(c, allowUnpriced)
    return allowUnpriced or (not c.funpriced)
end

local function CanUse(scheme, c, cur)
    local lo = (scheme == "optim") and (c.learnO or c.learn) or c.learn
    return cur >= lo and cur < c.grey
end
local function Usable(scheme, c, cur, allowUnpriced)
    if (scheme == "optim") and (c.cd or c.unknown) then return false end
    if not Eligible(c, allowUnpriced) then return false end
    return CanUse(scheme, c, cur)
end
local function GainOf(scheme, c, cur)
    if not CanUse(scheme, c, cur) then return nil end
    if scheme == "optim" then return 1 end
    return Gain(cur, c)
end
local function MetricOf(scheme, c, g)
    if scheme == "cheapest" then
        local span = math.max(1, (c.grey or 0) - (c.learn or 0))
        return c.cost / g + (c.fcost or 0) / span
    end
    if scheme == "crafts" then return 1 / g end
    if scheme == "optim" then return (c.base or 0) / g end
    return c.cost / g
end

local function Simulate(cands, start, cap, allowUnpriced, scheme)
    local steps, gaps = {}, {}
    local banned, segRun = {}, {}
    local cur = math.max(1, math.min(cap - 1, start or 1))
    local guard = 0

    while cur < cap do
        RouteTick()
        guard = guard + 1
        if guard > 4000 then break end

        local best, bestMetric
        for _, c in ipairs(cands) do
            if not banned[c.spell] and Usable(scheme, c, cur, allowUnpriced) then
                local g = GainOf(scheme, c, cur)
                if g then
                    local metric = MetricOf(scheme, c, g)
                    if not best or metric < bestMetric - 1e-9
                       or (metric < bestMetric + 1e-9 and c.grey > best.grey) then
                        best, bestMetric = c, metric
                    end
                end
            end
        end

        if not best then
            local nxt
            for _, c in ipairs(cands) do
                if not banned[c.spell] and Usable(scheme, c, cur, allowUnpriced) then
                    local lo = (scheme == "optim") and (c.learnO or c.learn) or c.learn
                    if lo > cur and (not nxt or lo < nxt) then nxt = lo end
                end
            end
            if nxt then
                gaps[#gaps + 1] = { cur, nxt - 1 }
                cur = nxt
            else
                if cur < cap then gaps[#gaps + 1] = { cur, cap - 1 } end
                cur = cap
            end
        else
            local from = cur
            local crafts = 0
            while cur < cap do
                local g = Gain(cur, best)
                if not g then break end
                crafts = crafts + 1 / g
                cur = cur + 1
                local stop = false
                for _, c in ipairs(cands) do
                    if c ~= best and not banned[c.spell] and Usable(scheme, c, cur, allowUnpriced) then
                        local g2 = GainOf(scheme, c, cur)
                        if g2 and MetricOf(scheme, c, g2) < bestMetric - 1e-9 then
                            stop = true
                            break
                        end
                    end
                end
                if stop then break end
            end
            local qty = math.max(1, math.ceil(crafts - 1e-9))
            local last = steps[#steps]
            if last and last[3] == best.spell and last[2] + 1 == from then
                last[2] = cur - 1
                last[4] = last[4] + qty
                last.cost = last.cost + best.cost * qty
            else
                steps[#steps + 1] = {
                    from, cur - 1, best.spell, qty,
                    cost = best.cost * qty, item = best.item,
                    unpriced = best.unpriced,
                }
                segRun[best.spell] = (segRun[best.spell] or 0) + 1
                if segRun[best.spell] >= MAX_PER_RECIPE then banned[best.spell] = true end
            end
        end
    end
    return steps, gaps
end

local function SimulateRange(cands, a, b, scheme, allowUnpriced)
    local steps = {}
    local banned, segRun = {}, {}
    local cur = a
    local guard = 0
    while cur <= b do
        RouteTick()
        guard = guard + 1
        if guard > 1000 then break end
        local best, bestMetric
        for _, c in ipairs(cands) do
            if not banned[c.spell] and Usable(scheme, c, cur, allowUnpriced) then
                local g = GainOf(scheme, c, cur)
                if g then
                    local metric = MetricOf(scheme, c, g)
                    if not best or metric < bestMetric - 1e-9
                       or (metric < bestMetric + 1e-9 and c.grey > best.grey) then
                        best, bestMetric = c, metric
                    end
                end
            end
        end
        if not best then
            local nxt
            for _, c in ipairs(cands) do
                if not banned[c.spell] and Eligible(c, allowUnpriced)
                   and not ((scheme == "optim") and (c.cd or c.unknown)) then
                    local lo = (scheme == "optim") and (c.learnO or c.learn) or c.learn
                    if lo > cur and lo <= b and (not nxt or lo < nxt) then nxt = lo end
                end
            end
            if not nxt then break end
            cur = nxt
        else
            local from = cur
            local crafts = 0
            while cur <= b do
                local g = Gain(cur, best)
                if not g then break end
                crafts = crafts + 1 / g
                cur = cur + 1
                local stop = false
                for _, c in ipairs(cands) do
                    if c ~= best and not banned[c.spell] and cur <= b
                       and Usable(scheme, c, cur, allowUnpriced) then
                        local g2 = GainOf(scheme, c, cur)
                        if g2 and MetricOf(scheme, c, g2) < bestMetric - 1e-9 then
                            stop = true
                            break
                        end
                    end
                end
                if stop then break end
            end
            local qty = math.max(1, math.ceil(crafts - 1e-9))
            local to = math.min(cur - 1, b)
            local last = steps[#steps]
            if last and last[3] == best.spell and last[2] + 1 == from then
                last[2] = to
                last[4] = last[4] + qty
                last.cost = last.cost + best.cost * qty
            else
                steps[#steps + 1] = {
                    from, to, best.spell, qty,
                    cost = best.cost * qty, item = best.item,
                    unpriced = best.unpriced, est = true,
                }
                segRun[best.spell] = (segRun[best.spell] or 0) + 1
                if segRun[best.spell] >= MAX_PER_RECIPE then banned[best.spell] = true end
            end
        end
    end
    local coverTo = a - 1
    for _, s in ipairs(steps) do
        if s[1] <= coverTo + 1 then coverTo = math.max(coverTo, s[2]) end
    end
    local resid = (coverTo < b) and { coverTo + 1, b } or nil
    return steps, resid
end

local function MergeSteps(steps)
    local out = {}
    for _, s in ipairs(steps) do
        local last = out[#out]
        if last and last[3] == s[3] and last[2] + 1 == s[1] then
            last[2] = s[2]
            last[4] = last[4] + s[4]
            last.cost = (last.cost or 0) + (s.cost or 0)
            if s.unpriced then last.unpriced = true end
            if s.est then last.est = true end
        else
            out[#out + 1] = s
        end
    end
    return out
end

local function FillGaps(cands, steps, gaps, scheme, allowUnpriced)
    local out = {}
    local si = 1
    for _, g in ipairs(gaps) do
        while si <= #steps and steps[si][2] < g[1] do
            out[#out + 1] = steps[si]
            si = si + 1
        end
        local fills, resid = SimulateRange(cands, g[1], g[2], scheme, allowUnpriced)
        for _, s in ipairs(fills) do out[#out + 1] = s end
        if resid then out[#out + 1] = { gap = resid } end
    end
    while si <= #steps do
        out[#out + 1] = steps[si]
        si = si + 1
    end
    local newSteps, newGaps = {}, {}
    for _, it in ipairs(out) do
        if it.gap then
            newGaps[#newGaps + 1] = it.gap
        else
            newSteps[#newSteps + 1] = it
        end
    end
    return MergeSteps(newSteps), newGaps
end

local function SummarizeCore(steps, recOf, soldSet, skipLearnedFormulas, specInputs, seedInv, skipMats)
    local total, crafts = 0, 0
    local productAH, productNPC, productPartial = 0, 0, false
    local mats, firstAt, matPrice, specSet = {}, {}, {}, {}
    for _, st in ipairs(steps) do
        local rec = recOf[st[3]]
        local ml = rec and (rec[12] or rec.mats) or nil
        if st.mats == nil then st.mats = ml end
        if st.item == nil and rec then
            local prod = rec[2]
            if type(prod) ~= "number" then prod = rec.makes end
            st.item = prod
        end
        if st.out == nil and rec then
            local n = rec[3]
            if type(n) ~= "number" then n = rec.count end
            st.out = n
        end
        if st.cost == nil then
            local sc, unpriced = 0, false
            if ml then
                for _, m in ipairs(ml) do
                    local id = m[1]
                    if not (skipMats and skipMats[id]) then
                        if matPrice[id] == nil then matPrice[id] = MatPrice(id, soldSet) end
                        local p = matPrice[id]
                        if p then
                            sc = sc + p * (m[2] or 1) * (st[4] or 0)
                        else
                            unpriced = true
                        end
                    end
                end
            end
            st.cost = sc
            st.unpriced = unpriced or nil
        end
        if st.unpriced then
            local code, age, mid, rank = nil, nil, nil, 9
            for _, m in ipairs(ml or {}) do
                local rc, ra = MatReason(m[1], soldSet)
                if rc then
                    local rk = (rc == "stale" and 1) or (rc == "norec" and 2) or (rc == "novendor" and 3) or 4
                    if rk < rank or (rk == rank and (ra or 0) > (age or 0)) then
                        rank, code, age, mid = rk, rc, ra, m[1]
                    end
                end
            end
            st.unpricedReason, st.unpricedAge, st.unpricedMat = code, age, mid
        end
        total = total + (st.cost or 0)
        crafts = crafts + (st[4] or 0)
        local prod = rec and rec[2]
        if type(prod) == "number" and type(rec[3])=="number" and rec[3]>0 then
            local outN = (st[4] or 0) * rec[3]
            RequestProduct(prod)
            local ah = AHPrice(prod)
            if ah then
                productAH = productAH + ah * outN
            else
                productPartial = true
            end
            local sp = NPCSellPrice(prod)
            if sp then productNPC = productNPC + sp * outN end
        elseif type(prod)=="number"then
            productPartial=true
        end
        if ml then
            for _, m in ipairs(ml) do
                local id = m[1]
                if not (skipMats and skipMats[id]) then
                    mats[id] = (mats[id] or 0) + (m[2] or 1) * (st[4] or 0)
                    if not firstAt[id] or st[1] < firstAt[id] then firstAt[id] = st[1] end
                    if matPrice[id] == nil then
                        matPrice[id] = MatPrice(id, soldSet)
                    end
                end
            end
        end
    end
    if specInputs then
        for _, pair in ipairs(specInputs) do
            local sid, sn = pair[1], tonumber(pair[2]) or 0
            if type(sid) == "number" and sn > 0 then
                mats[sid] = (mats[sid] or 0) + sn
                specSet[sid] = true
                if firstAt[sid] == nil then firstAt[sid] = 0 end
                if matPrice[sid] == nil then matPrice[sid] = MatPrice(sid, soldSet) end
            end
        end
    end
    local covered, coveredCost = nil, 0
    if type(seedInv) == "table" then
        for id, have in pairs(seedInv) do
            local need = mats[id]
            if need and need > 0 and type(have) == "number" and have > 0 then
                local use = math.min(need, have)
                local p = matPrice[id]
                if p == nil then p = MatPrice(id, soldSet) end
                if p then coveredCost = coveredCost + p * use end
                covered = covered or {}
                covered[id] = use
                mats[id] = need - use
                if mats[id] <= 0 then mats[id] = nil end
            end
        end
    end
    local list = {}
    for id, n in pairs(mats) do
        local p = matPrice[id]
        if p == nil then p = MatPrice(id, soldSet) end
        local rcode, rage
        if p == nil then rcode, rage = MatReason(id, soldSet) end
        local have = covered and covered[id] or nil
        list[#list + 1] = { id, n, cost = (p or 0) * n, unit = p or 0,
                            have = have, need = n + (have or 0),
                            vendor = soldSet[id] and true or false,
                            unpriced = (p == nil) and true or false,
                            spec = specSet[id] or nil,
                            reason = rcode, age = rage }
    end
    table.sort(list, function(a, b)
        local fa, fb = firstAt[a[1]] or math.huge, firstAt[b[1]] or math.huge
        if fa ~= fb then return fa < fb end
        if a[2] ~= b[2] then return a[2] > b[2] end
        return a[1] < b[1]
    end)
    local vendorTotal = 0
    for _, e in ipairs(list) do
        if e.vendor then vendorTotal = vendorTotal + (e.unit or 0) * e[2] end
    end
    local formulas, formulasTotal = {}, 0
    local vdb = ns.VendorPriceDB
    for _, st in ipairs(steps) do
        local rec = recOf[st[3]]
        local f = rec and rec[13]
        if type(f) == "table" and type(f[1]) == "number"
           and not (skipLearnedFormulas and LearnKnown(st[3])) then
            local dup = false
            for _, x in ipairs(formulas) do
                if x.id == f[1] then dup = true break end
            end
            if not dup then
                local SM = ns.ProfSourceMerge
                local psrc = (SM and SM.SourceOf) and SM.SourceOf(f[1]) or nil
                local primary = (psrc and SM.Primary) and SM.Primary(psrc) or nil
                local currencyOnly = (primary == "currency") or nil
                local p = MatPrice(f[1], soldSet)
                if currencyOnly then p = nil end
                local entry = {
                    id = f[1], spell = st[3], cost = (not currencyOnly) and (p or 0) or nil,
                    vendor = soldSet[f[1]] and true or false,
                    unpriced = (p == nil and not currencyOnly) and true or false,
                    currency = currencyOnly,
                }
                local raw = vdb and vdb.GetOffers and vdb.GetOffers(f[1]) or {}
                local hasU, hasL, hasO = false, false, false
                local offers = {}
                for _, o in ipairs(raw) do
                    if type(o) == "table" and o.npcID and (type(o.price) == "number" or o.unlimited ~= nil or o.limited ~= nil) then
                        hasO = true
                        if o.unlimited == true then hasU = true
                        elseif o.limited or o.unlimited == false then hasL = true end
                        offers[#offers + 1] = {
                            npcID = o.npcID, price = o.price,
                            quantity = o.quantity or o.bundleSize or 1,
                            bundleSize = o.bundleSize or o.quantity or 1,
                            unlimited = o.unlimited, limited = o.limited,
                            stockUnknown = o.stockUnknown, estimated = o.estimated,
                        }
                    end
                end
                if hasO then
                    entry.vendorOffers = offers
                    entry.unlimited = hasU or nil
                    entry.limited = hasL or nil
                    entry.stockUnknown = (not hasU and not hasL) or nil
                end
                formulas[#formulas + 1] = entry
                formulasTotal = formulasTotal + (p or 0)
            end
        end
    end
    if coveredCost > 0 then total = math.max(0, total - coveredCost) end
    return total, crafts, list, firstAt, vendorTotal, formulas, formulasTotal,
           productAH, productNPC, productPartial
end

function RA.SummarizeSteps(steps, slug, opts)
    opts = opts or {}
    local pr = ns.ProfRecipes
    local Rg = pr and pr[slug]
    local LV = ns.ProfLeveling and ns.ProfLeveling[slug]
    if not ((Rg and type(Rg.rows)=="table")
        or (LV and (type(LV.rinfo)=="table" or type(LV.steps)=="table"))) then return nil end
    local soldSet = {}
    if LV and type(LV.sold) == "table" then
        for _, id in ipairs(LV.sold) do soldSet[id] = true end
    end
    local recOf = {}
    for _, rec in ipairs(Rg and Rg.rows or {}) do recOf[rec[1]] = ResolvedRow(rec,slug) end
    if LV and type(LV.rinfo) == "table" then
        for spell, ri in pairs(LV.rinfo) do
            if not recOf[spell] then recOf[spell] = ResolvedRow(ri,slug,spell) end
        end
    end
    local specInputs
    do
        local G = ns.ProfGates
        local cap = tonumber(opts.target) or (steps[#steps] and steps[#steps][2]) or 300
        local goal = G and G.SpecGoal and G.SpecGoal(slug, cap)
        if goal and type(goal.inputs) == "table" then specInputs = goal.inputs end
    end
    local total, crafts, list, firstAt, vendorTotal, formulas, formulasTotal,
          productAH, productNPC, productPartial =
        SummarizeCore(steps, recOf, soldSet, opts.learnedOnly, specInputs, opts.executionInventory)
    local res = {
        steps = steps, mats = list, firstAt = firstAt,
        matTotal = total, formulas = formulas, formulasTotal = formulasTotal,
        total = total + formulasTotal, vendorTotal = vendorTotal,
        ahTotal = total - vendorTotal,
        productAH = productAH, productNPC = productNPC, productPartial = productPartial,
        crafts = crafts,
        scheme = opts.scheme or "fixed",
        priced = RA.HasPriceData(),
        snapshotAge = SnapshotSec(),
        snapshotDays = priceCache.__minAge,
        stamp = time and time() or 0,
    }
    local blockedSteps = RA.MarkFixedSpecializations(slug, steps, opts)
    if blockedSteps then
        res.blockedSteps = blockedSteps
        res.specBlocked = #blockedSteps
        res.feasible=false;res.status="recalculate_required"
        res.diagnostics={}
        for _,blocked in ipairs(blockedSteps) do
            res.diagnostics[#res.diagnostics+1]={code=blocked.reason,spell=blocked.spell,profession=slug}
            if blocked.reason=="clientDataPending" then res.clientPending=true;res.completeCost=false;res.costComplete=false;res.priced=false end
        end
        res.blockingDiagnostics=res.diagnostics
    end
    local _,_,goalRequired=RA.FilterFixedSpecializations(slug,steps,opts)
    if goalRequired then res.specializationGoalRequired=true;res.feasible=false;res.status="recalculate_required" end
    return RA.ApplyRecovery(res, slug, opts, recOf)
end

local function RecoverySnapshot(slug, steps, recOf, toolItems)
    local snap = {
        slug = slug, stamp = (type(time) == "function") and time() or 0,
        recipes = {}, byKey = {}, prices = {}, sellPrices = {},
        auctionSupply = {}, nonAuctionable = {}, retainedToolItems = {},
    }
    for _, st in ipairs(steps or {}) do
        local spell = st[3]
        local rec = type(spell) == "number" and recOf and recOf[spell] or nil
        if rec then
            local key = slug .. ":" .. tostring(spell)
            if not snap.byKey[key] then
                local item = rec[2]
                if type(item) ~= "number" then item = rec.makes end
                local count = rec[3]
                if type(count) ~= "number" then count = rec.count end
                if count==nil and not rec.clientPending then count=1 end
                local mats = rec[12] or rec.mats or {}
                local row = {
                    profession = slug, spell = spell, key = key,
                    item = (type(item) == "number" and item > 0 and type(count)=="number" and count>0) and item or nil,
                    count = (type(count) == "number" and count > 0) and count or 0,
                    mats = mats,
                }
                snap.recipes[#snap.recipes + 1] = row
                snap.byKey[key] = row
            end
        end
    end
    for _, r in ipairs(snap.recipes) do
        if r.item then
            local p = AHPrice(r.item)
            if type(p) == "number" and p > 0 then snap.prices[r.item] = p end
            local sp = NPCSellPrice(r.item)
            if sp then snap.sellPrices[r.item] = sp end
        end
    end
    local AB = ns.AuctionBridge
    if AB and AB.GetAuctionSupply then
        for _, r in ipairs(snap.recipes) do
            if r.item and snap.auctionSupply[r.item] == nil then
                snap.auctionSupply[r.item] = AB.GetAuctionSupply(r.item)
            end
        end
    end
    for _, id in ipairs(toolItems or {}) do
        snap.retainedToolItems[id] = 1
        snap.nonAuctionable[id] = true
    end
    return snap
end

local function RecoveryOptions(opts)
    opts = opts or {}
    local db = DungeonsForeverDB and DungeonsForeverDB.prof
    local enabled = opts.recoveryEnabled
    if enabled == nil then enabled = not (db and db.recoveryEnabled == false) end
    local fee = opts.recoveryFeePercent
    if fee == nil and db then fee = db.recoveryFeePercent end
    return enabled, fee
end

function RA.ApplyRecovery(res, slug, opts, recOf)
    local R = ns.ProfRecovery
    if not res or not R or not R.Apply then return res end
    local enabled, fee = RecoveryOptions(opts)
    local snap = RecoverySnapshot(slug, res.steps, recOf, res.toolItems)
    R.Capture(snap, { recoveryEnabled = enabled, recoveryFeePercent = fee })
    res.scheme = res.scheme or (opts and opts.scheme) or "fixed"
    R.Apply(res, snap)
    res.recoveryOptimized = false
    res.recoveryScheme = snap.recovery and snap.recovery.feePercent or nil
    res.recoveryFeeSource = snap.recovery and snap.recovery.feeSource or nil
    RA.StampSupply(res)
    RA.StampSpecializations(res, slug, opts, res.recoverySnapshot)
    return res
end

function RA.RecoveryForSteps(res, slug, recOf, opts)
    return RA.ApplyRecovery(res, slug, opts, recOf)
end

local function ToReached(steps)
    if type(steps) ~= "table" then return steps end
    local out = {}
    for i, st in ipairs(steps) do
        local c = {}
        for k, v in pairs(st) do c[k] = v end
        c[2] = (tonumber(st[2]) or 0) + 1
        out[i] = c
    end
    return out
end

local function InjectTools(stepsOut, slug, cap, startLv, recOf)
    local kept = {}
    local G = ns.ProfGates
    if not G or not G.AutoCraftTools() then return kept end
    local goals = G.ToolGoals(slug, cap)
    if #goals == 0 then return kept end
    local have = {}
    for _, st in ipairs(stepsOut) do have[st[3]] = true end
    local lo = tonumber(startLv) or 1
    for _, goal in ipairs(goals) do
        local P = goal.minSkill or 1
        if P >= lo and not have[goal.spell] and recOf[goal.spell] and not G.ToolOwned(goal.item) then
            local at = #stepsOut + 1
            for i, st in ipairs(stepsOut) do
                if (tonumber(st[2]) or 0) > P then at = i break end
            end
            table.insert(stepsOut, at, { P, P, goal.spell, 1,
                tool = true, toolItem = goal.item, toolSpell = goal.spell,
                toolBop = goal.bindOnPickup or nil })
            have[goal.spell] = true
            kept[#kept + 1] = goal.item
        end
    end
    return kept
end

function RA.StampToolPolicy(result, targetProfession, unused, snapshot)
    if type(result) ~= "table" then return result end
    local goals = {}
    local s = snapshot or (type(result) == "table" and result.recoverySnapshot) or nil
    if type(s) == "table" then
        for _, goal in ipairs(s.toolGoals or {}) do
            if goal.item then goals[goal.item] = goal end
        end
    end
    for _, listKey in ipairs({ "steps", "executionSteps" }) do
        for _, st in ipairs(result[listKey] or {}) do
            if st.tool and st.toolItem then
                local goal = goals[st.toolItem]
                st.toolBop = st.toolBop or (goal and goal.bindOnPickup) or nil
            end
        end
    end
    for _, m in ipairs(result.mats or {}) do
        if m.id and goals[m.id] then m.tool = true end
    end
    return result
end

local function SpecContext(slug, opts)
    local G = ns.ProfGates
    if not (G and G.SpecializationContext) then return nil end
    local options = {}
    for k, v in pairs(opts or {}) do options[k] = v end
    options.profession = slug or options.profession or "engineering"
    if options.target == nil then
        local db = DungeonsForeverDB and DungeonsForeverDB.prof
        options.target = tonumber(db and db.lvTarget and db.lvTarget[options.profession]) or 300
    end
    return G.SpecializationContext(options)
end

function RA.StampSpecializations(result, slug, opts, snapshot)
    if type(result) ~= "table" then return result end
    RA.StampToolPolicy(result, slug, opts, snapshot)
    local G = ns.ProfGates
    if not (G and G.SpecializationContext) then return result end
    local ctx
    if type(snapshot) == "table" then ctx = snapshot.specializationContext end
    if not ctx then ctx = SpecContext(slug, opts) end
    if not ctx then return result end
    local abilities = {}
    local source = ctx.abilities
    if type(snapshot) == "table" and snapshot.specializationAbilities then
        source = snapshot.specializationAbilities
    end
    for id, known in pairs(source or {}) do
        if known == true then abilities[id] = true end
    end
    result.specializationPolicy = {
        revision = 1,
        profession = slug or (type(snapshot) == "table" and snapshot.targetProfession) or ctx.profession,
        choice = ctx.choice or "none",
        fingerprint = G.SpecFingerprint(ctx.choice),
        actualAbilities = abilities,
        selectionConflict = ctx.selectionConflict == true,
    }
    return result
end

function RA.SpecializationPlanChanged(result, slug, opts)
    if type(result) ~= "table" then return false end
    local G = ns.ProfGates
    if not (G and G.SpecializationContext) then return false end
    local policy = result.specializationPolicy
    local prof = slug
    if not prof and policy then prof = policy.profession end
    local ctx = SpecContext(prof, opts)
    if not ctx then return false end
    if not policy then return ctx.choice ~= "none" end
    if policy.revision ~= 1 or policy.fingerprint ~= G.SpecFingerprint(ctx.choice) then return true end
    for id in pairs(policy.actualAbilities or {}) do
        if (ctx.abilities or {})[id] ~= true then return true end
    end
    if ctx.profession == "engineering" and ctx.selectionConflict and not policy.selectionConflict then
        return true
    end
    return false
end

function RA.FilterFixedSpecializations(slug, steps, opts)
    local G = ns.ProfGates
    local E = ns.ProfEconomy
    local filtered, blocked = {}, {}
    if not (E and E.LearningEligibility) and not (G and G.LearningEligibility) then
        for _, st in ipairs(steps or {}) do filtered[#filtered + 1] = st end
        return filtered, blocked, false
    end
    local ctx = SpecContext(slug, opts)
    for _, st in ipairs(steps or {}) do
        local spell = st[3] or st.spell
        local allowed, reason = true, nil
        if spell and spell~=0 and not st.checkpoint then
            local profession=st.profession or slug
            local recipe=E and E.FindRecipe and E.FindRecipe(profession,spell) or st.recipe
            if recipe and #(recipe.requiredDataUnknown or {})>0 then
                local onlyLearn=true
                for _,field in ipairs(recipe.requiredDataUnknown)do if field~="learn"then onlyLearn=false end end
                allowed,reason=false,onlyLearn and "learningRequirementsUnknown"or"clientDataPending"
            elseif recipe and (recipe.cooldown or recipe.cooldownUnknown)then
                allowed,reason=false,recipe.cooldown and "cooldown"or"cooldownUnknown"
            elseif recipe and E and E.LearningEligibility then
                allowed,reason=E.LearningEligibility(recipe,opts and opts.snapshot)
            elseif E and E.FindRecipe then allowed,reason=false,"clientDataPending"
            elseif G and G.LearningEligibility then allowed,reason=G.LearningEligibility(spell) end
        end
        if allowed then
            filtered[#filtered + 1] = st
        else
            blocked[#blocked + 1] = { spell = spell, from = st[1], to = st[2],
                reason = reason or "specializationRequired" }
        end
    end
    local goalRequired = false
    if ctx and #(ctx.goals or {}) > 0 then goalRequired = true end
    return filtered, blocked, goalRequired
end

function RA.MarkFixedSpecializations(slug, steps, opts)
    local _, blocked = RA.FilterFixedSpecializations(slug, steps, opts)
    for _,st in ipairs(steps or {}) do st.specBlocked=nil end
    if #blocked == 0 then return nil end
    local bySpell = {}
    for _, b in ipairs(blocked) do
        if b.spell then bySpell[b.spell] = b.reason end
    end
    for _, st in ipairs(steps or {}) do
        local reason = bySpell[st[3]]
        st.specBlocked = reason
    end
    return blocked
end

function RA.StampSupply(result, context)
    if type(result) ~= "table" then return result end
    local AB = ns.AuctionBridge
    local unknown = 0
    local now = (type(time) == "function") and time() or 0
    local snapSupply = (type(context) == "table") and context.auctionSupply or nil
    local snapHistory = (type(context) == "table") and context.auctionSupplyHistory or nil
    local snapPriceAt = (type(context) == "table") and context.priceObservedAt or nil
    local function SupplyOf(id)
        local rec = snapSupply and snapSupply[id] or nil
        if rec == nil and not snapSupply and AB and AB.GetAuctionSupply then
            rec = AB.GetAuctionSupply(id)
        end
        return rec
    end
    for _, e in ipairs(result.mats or {}) do
        local mid = e.id or e[1]
        if mid and not e.vendor and (e.source == nil or e.source == "ah") then
            local rec = SupplyOf(mid)
            if rec and rec.complete and rec.ownerExcluded and rec.source == "client-auction-results"
                and type(rec.quantity) == "number" and rec.observedAt > 0
                and now - rec.observedAt <= 172800 then
                e.source = e.source or "ah"
                e.availableCount = rec.quantity
                e.supplyObserved = true
                e.supplyObservedAt = rec.observedAt
                e.supplySource = rec.source
                e.supplyComplete = true
                e.supplyOwnerExcluded = true
                if type(rec.market) == "number" and rec.market > 0 then e.supplyObservedPrice = rec.market end
            else
                e.supplyObserved = false
                unknown = unknown + 1
            end
            local h = (snapHistory and snapHistory[mid])
                or (not snapSupply and AB and AB.GetAuctionSupplyHistory and AB.GetAuctionSupplyHistory(mid))
                or nil
            if type(h) == "table" and tonumber(h.quantity) and h.quantity >= 0 then
                e.supplyHistoryQuantity = h.quantity
                e.supplyHistoryObservedAt = tonumber(h.observedAt) or 0
            end
            local pat = (snapPriceAt and snapPriceAt[mid])
                or (not snapSupply and AB and AB.GetAuctionPriceObservedAt and AB.GetAuctionPriceObservedAt(mid))
                or nil
            if tonumber(pat) and pat > 0 then e.priceObservedAt = pat end
        end
    end
    result.auctionSupplyUnknown = unknown > 0 and unknown or nil
    return result
end

local function FishingCandidates(fishDB)
    local soldSet = {}
    local LV = ns.ProfLeveling and ns.ProfLeveling.cooking
    if LV and type(LV.sold) == "table" then
        for _, id in ipairs(LV.sold) do soldSet[id] = true end
    end
    local Rg = ns.ProfRecipes and ns.ProfRecipes.cooking
    if not (Rg and type(Rg.rows) == "table") then return nil end
    local cands, recOf, fishSet = {}, {}, {}
    for _, rec in ipairs(Rg.rows) do
        RouteTick()
        local spell, learn, grey = rec[1], rec[7], rec[10]
        local mats = rec[12]
        if type(spell) == "number" and type(learn) == "number" and type(grey) == "number"
           and grey > learn and type(mats) == "table" and #mats > 0 then
            local ok, hasFish = true, false
            for _, m in ipairs(mats) do
                local f = fishDB[m[1]]
                if f then
                    if f.season or f.night then ok = false end
                    hasFish = true
                    fishSet[m[1]] = f
                elseif not MatPrice(m[1], soldSet) then
                    ok = false
                end
            end
            if ok and hasFish then
                local cY = (type(rec[8]) == "number") and rec[8] or learn
                cands[#cands + 1] = {
                    spell = spell, item = rec[2], learn = learn, yellow = cY,
                    green = (type(rec[9]) == "number") and rec[9] or cY,
                    grey = grey, mats = mats, cost = 0, fcost = 0, base = 0,
                    learnO = learn,
                }
                recOf[spell] = rec
            end
        end
    end
    return cands, recOf, soldSet, fishSet
end

function RA.ComputeFishing(slug, opts)
    opts = opts or {}
    local F = ns.ProfFishingRoutes
    local fishDB = F and F.fish
    if not fishDB then return nil end
    local cands, recOf, soldSet, fishSet = FishingCandidates(fishDB)
    if not cands or #cands == 0 then return nil end
    local cap = tonumber(opts.target) or CAP
    cap = math.max(2, math.min(CAP, math.floor(cap)))
    local start = math.max(1, math.min(cap - 1, opts.start or 1))
    local steps, gaps = Simulate(cands, start, cap, true, "crafts")
    if #steps == 0 then return nil end
    local stepsOut = ToReached(steps)
    local fishList, fishAt = {}, {}
    for _, st in ipairs(stepsOut) do
        RouteTick()
        local rec = recOf[st[3]]
        local ml = (rec and rec[12]) or {}
        local cnt = st[4] or 0
        local line = {}
        for _, m in ipairs(ml) do
            local f = fishDB[m[1]]
            if f then
                local need = (m[2] or 1) * cnt
                local a1 = f.a and f.a[1]
                local e = fishAt[m[1]]
                if not e then
                    e = { id = m[1], count = 0, need = 0, source = "fishing",
                          areas = f.a, minSkill = a1 and a1.minSkill,
                          noGetaway = a1 and a1.noGetaway, catchRate = f.rate, note = f.note }
                    fishAt[m[1]] = e
                    fishList[#fishList + 1] = e
                end
                e.count = e.count + need
                e.need = e.count
                line[#line + 1] = { id = m[1], count = need, need = need, source = "fishing", areas = f.a, note = f.note }
            end
        end
        if #line > 0 then
            local areas = {}
            for _, e in ipairs(line) do
                for _, a in ipairs(e.areas or {}) do areas[#areas + 1] = a end
            end
            st.fishing = line
            st.fishMaterials = line
            st.fishingAreas = areas
            st.profession = "cooking"
            st.role = "level"
            st.reason = "level"
        end
    end
    local total, crafts, mats, firstAt, vendorTotal, formulas, formulasTotal,
          productAH, productNPC, productPartial =
        SummarizeCore(stepsOut, recOf, soldSet, opts.learnedOnly, nil, opts.executionInventory, fishSet)
    local reached = stepsOut[#stepsOut] and stepsOut[#stepsOut][2] or start
    local res = {
        planVersion = 2, scheme = "fishing", fishingRoute = true,
        steps = stepsOut, gaps = gaps, mats = mats, firstAt = firstAt,
        fishMaterials = fishList,
        matTotal = total, formulas = formulas, formulasTotal = formulasTotal,
        total = total + formulasTotal, vendorTotal = vendorTotal,
        ahTotal = total - vendorTotal,
        productAH = productAH, productNPC = productNPC, productPartial = productPartial,
        crafts = crafts,
        start = start, target = cap, plannedTo = reached,
        targetReached = reached >= cap, partial = reached < cap, feasible = true,
        priced = RA.HasPriceData(),
        snapshotAge = SnapshotSec(),
        snapshotDays = priceCache.__minAge,
        stamp = time and time() or 0,
    }
    res = RA.ApplyRecovery(res, "cooking", opts, recOf)
    if res.targetReached then res.status = "complete" else res.status = "incomplete" end
    return res
end

function RA.Compute(slug, opts)
    opts = opts or {}
    if opts.scheme == "fishing" then
        local fr = RA.ComputeFishing(slug, opts)
        if fr then return fr end
    end
    local cands, recOf, soldSet, blockedCount = BuildCandidates(slug, opts)
    if not cands then return nil end
    local scheme = opts.scheme
    if scheme == nil or not SCHEME_LABEL[scheme] then scheme = "cheapest" end
    local cap = tonumber(opts.target) or CAP
    cap = math.max(2, math.min(CAP, math.floor(cap)))
    local PDm = ns.ProfModule
    local allowUnpriced = false
    if PDm and PDm.Setting then allowUnpriced = not PDm.Setting("autoSkipUnpricedFormulas") end
    local steps, gaps = Simulate(cands, opts.start, cap, allowUnpriced, scheme)
    local filled = false
    if #gaps > 0 then
        steps, gaps = FillGaps(cands, steps, gaps, scheme, allowUnpriced)
        for _, st in ipairs(steps) do
            if st.est then filled = true break end
        end
    end
    if scheme == "optim" then
        local bySpell = {}
        for _, c in ipairs(cands) do bySpell[c.spell] = c end
        for _, st in ipairs(steps) do
            local c = bySpell[st[3]]
            if c then st.cost = (c.base or 0) * (st[4] or 0) end
        end
    end
    local stepsOut = ToReached(steps)
    local kept = InjectTools(stepsOut, slug, cap, opts.start, recOf)
    local total, crafts, mats, firstAt, vendorTotal, formulas, formulasTotal,
          productAH, productNPC, productPartial =
        SummarizeCore(stepsOut, recOf, soldSet, opts.learnedOnly, nil, opts.executionInventory)
    local res = {
        scheme = scheme,
        steps = stepsOut, gaps = gaps, mats = mats, firstAt = firstAt,
        total = total + formulasTotal, matTotal = total,
        formulas = formulas, formulasTotal = formulasTotal,
        vendorTotal = vendorTotal, ahTotal = total - vendorTotal,
        productAH = productAH, productNPC = productNPC, productPartial = productPartial,
        crafts = crafts,
        start = math.max(1, math.min(CAP - 1, opts.start or 1)),
        target = cap,
        priced = RA.HasPriceData(),
        filled = filled,
        specBlocked = blockedCount,
        toolItems = kept,
        snapshotAge = SnapshotSec(),
        snapshotDays = priceCache.__minAge,
        stamp = time and time() or 0,
    }
    return RA.ApplyRecovery(res, slug, opts, recOf)
end

local cache = {}

function RA.Invalidate()
    local R = ns.ProfRecovery
    if R and R.Invalidate then R.Invalidate() end
    local G = ns.ProfGates
    if G and G.Invalidate then G.Invalidate() end
    for k in pairs(cache) do cache[k] = nil end
    for k in pairs(priceCache) do
        if k ~= "__any" then priceCache[k] = nil end
    end
    priceCache.__any = nil
    for k in pairs(vendorCache) do vendorCache[k] = nil end
end

local priceWatchers = {}
function RA.OnPricesChanged(fn)
    if type(fn) == "function" then priceWatchers[#priceWatchers + 1] = fn end
end

local ahWatch = CreateFrame("Frame")
ahWatch:RegisterEvent("AUCTION_HOUSE_CLOSED")
ahWatch:SetScript("OnEvent", function()
    C_Timer.After(0, function()
        RA.Invalidate()
        for _, fn in ipairs(priceWatchers) do pcall(fn) end
    end)
end)

local function Fingerprint(opts, slug)
    local Pol = ns.ProfEconomy
    local pol = Pol and Pol.GetPolicies and Pol.GetPolicies(slug) or nil
    local partner = opts.secondaryProfession
    if partner == nil and Pol and Pol.GetRoutePartner then partner = Pol.GetRoutePartner(slug) end
    return string.format("%s|%s|%s|%s|%s|%s|%s|%s|%s",
        tostring(opts.start), tostring(opts.onlyAH),
        tostring(opts.noFormula), tostring(opts.learnedOnly),
        tostring(opts.target and math.floor(tonumber(opts.target) or CAP)),
        tostring(opts.scheme),
        tostring(opts.allowSecondaryLeveling),
        tostring(partner),
        pol and Pol.PolicyFingerprint(pol) or "")
end

function RA.QuoteSig()
    local AB = ns.AuctionBridge
    local PDm = ns.ProfModule
    local rev = AB and AB.SupplyRevision and AB.SupplyRevision() or 0
    local fee = PDm and PDm.SettingRaw and tonumber(PDm.SettingRaw("recoveryFeePercent")) or 5
    local lim = (PDm and PDm.SettingRaw and PDm.SettingRaw("autoBuyLimitedFormulas")) and 1 or 0
    local unk = (PDm and PDm.SettingRaw and PDm.SettingRaw("autoSkipUnpricedFormulas")) and 1 or 0
    local rec = (PDm and PDm.Setting and PDm.Setting("recoveryEnabled")) and 1 or 0
    local tool = (PDm and PDm.Setting and PDm.Setting("autoCraftTools")) and 1 or 0
    return tostring(rev) .. ":" .. tostring(fee) .. ":" .. tostring(lim) .. ":" .. tostring(unk)
        .. ":" .. tostring(rec) .. ":" .. tostring(tool)
end

function RA.SpecSig(slug)
    local G = ns.ProfGates
    if not (G and G.SpecFingerprint) then return "" end
    local choice = "none"
    if G.GetPlannedChoice then choice = G.GetPlannedChoice() end
    return G.SpecFingerprint(choice)
end

function RA.OptionsFor(slug, current)
    local PDm = ns.ProfModule
    if not (PDm and PDm.Setting) then return nil end
    local fish = PDm.CookingFishingMode and PDm.CookingFishingMode(slug) or false
    local pair = (not fish) and PDm.RoutePairContext and PDm.RoutePairContext() or nil
    local target = PDm.LvTarget and PDm.LvTarget() or CAP
    local lv = tonumber(current)
    return {
        start = (PDm.Setting("autoFromCurrent") and lv) and math.max(1, lv) or 1,
        onlyAH = PDm.Setting("autoOnlyAH"),
        noFormula = PDm.Setting("autoNoFormula"),
        learnedOnly = PDm.Setting("autoLearnedOnly"),
        target = target,
        scheme = fish and "fishing" or PDm.SettingRaw("autoScheme"),
        allowSecondaryLeveling = PDm.Setting("autoSecondaryLeveling"),
        secondaryProfession = pair and pair.partner or nil,
        executionInventory = ns.ProfTrack and ns.ProfTrack.ContinueInventory
            and ns.ProfTrack.ContinueInventory(slug) or nil,
    }
end

function RA.Recalculate(slug, opts)
    RA.Invalidate()
    return true
end

function RA.PlanSig(slug, opts)
    return Fingerprint(opts or {}, slug) .. "#" .. RA.QuoteSig() .. "#" .. RA.SpecSig(slug)
end

function RA.Get(slug, opts)
    opts = opts or {}
    local fp = Fingerprint(opts, slug)
    local sig = RA.QuoteSig()
    local specSig = RA.SpecSig(slug)
    local bucket = cache[slug]
    if not bucket then
        bucket = {}
        cache[slug] = bucket
    end
    local now = (type(time) == "function") and time() or 0
    local e = bucket[fp]
    if e and e.sig == sig and e.specSig == specSig and (now - e.stamp) < CACHE_TTL then return e.res end
    local refreshed = e ~= nil and e.sig ~= sig
    local res = RA.Compute(slug, opts)
    if res then res.planSig = fp .. "#" .. sig .. "#" .. specSig end
    if res and refreshed then res.quotesRefreshed = true end
    bucket[fp] = { res = res, stamp = now, sig = sig, specSig = specSig }
    local n, oldK, oldT = 0, nil, nil
    for k, v in pairs(bucket) do
        n = n + 1
        if k ~= fp and (not oldT or v.stamp < oldT) then oldK, oldT = k, v.stamp end
    end
    if n > CACHE_SLOTS and oldK then bucket[oldK] = nil end
    return res
end
