local _, ns = ...
if type(ns) ~= "table" then ns = _G.DF_NS or {} end
local gns = _G.DF_NS

local format = string.format

local W = {}
ns.ProfCDWatch = W
if type(gns) == "table" and gns ~= ns then
    gns.ProfCDWatch = W
end

local KEEP_SEC = 45 * 86400
local MAX_ROWS = 3
local fallbackStore = nil

local function getDS()
    return ns.ProfDataStore or (type(gns) == "table" and gns.ProfDataStore) or nil
end

local function getAPI()
    return ns.ProfAPI or (type(gns) == "table" and gns.ProfAPI) or nil
end

local function getDB()
    return ns.ProfDB or (type(gns) == "table" and gns.ProfDB) or nil
end

local function getPricingCfg()
    return ns.PricingConfig or (type(gns) == "table" and gns.PricingConfig) or nil
end

local function getRouteAuto()
    return ns.ProfRouteAuto or (type(gns) == "table" and gns.ProfRouteAuto) or nil
end

local function getZoneHint()
    return ns.ZoneHint or (type(gns) == "table" and gns.ZoneHint) or nil
end

local function getProfModule()
    return ns.ProfModule or (type(gns) == "table" and gns.ProfModule) or nil
end

local function tr(key)
    local L = ns.L or (type(gns) == "table" and gns.L)
    if type(L) == "table" and L[key] ~= nil then return L[key] end
    return key
end

local function now()
    if type(_G.time) == "function" then return _G.time() end
    if type(os) == "table" and type(os.time) == "function" then return os.time() end
    return 0
end

local function clock()
    local f = _G.GetTime
    return type(f) == "function" and f() or 0
end

local function getRootDB()
    local DB = getDB()
    if type(DB) == "function" or (type(DB) == "table" and type(getmetatable(DB)) == "table" and getmetatable(DB).__call) then
        local ok, res = pcall(DB)
        if ok and type(res) == "table" then return res end
    end
    if type(DB) == "table" and type(DB.Get) == "function" then
        local ok, res = pcall(DB.Get)
        if ok and type(res) == "table" then return res end
    end
    if not fallbackStore then
        fallbackStore = { chars = {}, cdWatch = {} }
    end
    return fallbackStore
end

local function cdWatchBucket()
    local db = getRootDB()
    if type(db.cdWatch) ~= "table" then db.cdWatch = {} end
    local cw = db.cdWatch
    if type(cw.records) ~= "table" then cw.records = {} end
    if type(cw.list) ~= "table" then cw.list = {} end
    if type(cw.know) ~= "table" then cw.know = {} end
    if type(cw.off) ~= "table" then cw.off = {} end
    if type(cw.todoOn) ~= "table" then cw.todoOn = {} end
    if type(cw.cls) ~= "table" then cw.cls = {} end
    return cw
end

local function store()
    return cdWatchBucket().records
end

local function list()
    return cdWatchBucket().list
end

local function know()
    return cdWatchBucket().know
end

local function offs()
    return cdWatchBucket().off
end

local function todoOns()
    return cdWatchBucket().todoOn
end

local function clsMap()
    return cdWatchBucket().cls
end

local TODO_DEF = { [17187] = true, [1317279] = true }

function W.TodoOn(spell)
    local v = todoOns()[spell]
    if v ~= nil then return v == true end
    return TODO_DEF[spell] == true
end

function W.SetTodo(spell, on)
    if type(spell) ~= "number" then return false end
    on = (on == true)
    if W.TodoOn(spell) == on then return false end
    local o = todoOns()
    if on then o[spell] = true else o[spell] = false end
    local pd = getProfModule()
    if pd and pd.RequestRender then pcall(pd.RequestRender) end
    local zh = getZoneHint()
    if zh and zh.RefreshSoft then pcall(zh.RefreshSoft, true) end
    return true
end

function W.Enabled(spell)
    return offs()[spell] ~= true
end

function W.SetEnabled(spell, on)
    if type(spell) ~= "number" then return false end
    local o = offs()
    if on then
        if o[spell] == nil then return false end
        o[spell] = nil
    else
        if o[spell] == true then return false end
        o[spell] = true
    end
    local pd = getProfModule()
    if pd and pd.RequestRender then pcall(pd.RequestRender) end
    local zh = getZoneHint()
    if zh and zh.RefreshSoft then pcall(zh.RefreshSoft, true) end
    return true
end

W.Store = store

local function hasSurname()
    if type(_G.RegionalUniqueNamesEnabled) ~= "function" then return false end
    local ok, v = pcall(_G.RegionalUniqueNamesEnabled)
    return ok and v == true
end

local function nameParts()
    local n, s2
    if type(_G.UnitNameUnmodified) == "function" then
        local ok, a, b = pcall(_G.UnitNameUnmodified, "player")
        if ok then n, s2 = a, b end
    end
    if (type(n) ~= "string" or n == "") and type(_G.UnitName) == "function" then
        local ok, a = pcall(_G.UnitName, "player")
        if ok and type(a) == "string" then n = a end
    end
    if type(s2) ~= "string" or s2 == "" then s2 = nil end
    if s2 and not hasSurname() then s2 = nil end
    return n, s2
end

function W.Name()
    local n, s2 = nameParts()
    if type(n) ~= "string" or n == "" then return "?" end
    if s2 and s2 ~= n then return n .. " " .. s2 end
    return n
end

function W.CharKey()
    local DB = getDB()
    if type(DB) == "table" and type(DB.CharacterKey) == "function" then
        return DB.CharacterKey()
    end
    if type(_G.UnitGUID) == "function" then
        local ok, guid = pcall(_G.UnitGUID, "player")
        if ok and type(guid) == "string" and guid ~= "" then
            return guid
        end
    end
    local r
    if type(_G.GetRealmName) == "function" then
        local ok, v = pcall(_G.GetRealmName)
        if ok and type(v) == "string" and v ~= "" then r = v end
    end
    local nm = W.Name()
    if nm ~= "?" or r then
        return "offline:" .. nm .. "-" .. tostring(r or "?")
    end
    return "offline:player"
end

local function charName()
    return W.Name()
end

local function charClass()
    if type(_G.UnitClass) ~= "function" then return nil end
    local ok, _, token, id = pcall(_G.UnitClass, "player")
    if not ok then return nil end
    if type(token) == "string" and token ~= "" then return token end
    if type(id) == "string" and id ~= "" then return id end
    return nil
end

local function syncCharacterMeta(key)
    local DB = getDB()
    if type(DB) == "table" and type(DB.CharacterMeta) == "function" and key == W.CharKey() then
        pcall(DB.CharacterMeta, key)
    end
end

local function clsOf(key, rec)
    if type(rec) == "table" and type(rec.cls) == "string" then return rec.cls end
    local db = getRootDB()
    if type(db.chars) == "table" and type(db.chars[key]) == "table" and type(db.chars[key].class) == "string" then
        return db.chars[key].class
    end
    local t = clsMap()
    if type(t[key]) == "string" then return t[key] end
    if key == W.CharKey() then return charClass() end
    return nil
end

local function baseCD(spell)
    local cs = _G.C_Spell
    if type(cs) == "table" and type(cs.GetSpellBaseCooldown) == "function" then
        local ok, ms = pcall(cs.GetSpellBaseCooldown, spell)
        if ok and type(ms) == "number" then return ms > 0 end
    end
    local f = _G.GetSpellBaseCooldown
    if type(f) == "function" then
        local ok, ms = pcall(f, spell)
        if ok and type(ms) == "number" then return ms > 0 end
    end
    return nil
end

local function liveCD(spell)
    local api = _G.C_Spell
    if type(api) == "table" and type(api.GetSpellCooldown) == "function" then
        local ok, sc = pcall(api.GetSpellCooldown, spell)
        if ok and type(sc) == "table" then
            local st, du = sc.startTime, sc.duration
            if type(st) == "number" and type(du) == "number" and st > 0 and du > 0 then
                local left = st + du - clock()
                if left > 0 then return left, du end
                return nil
            end
        end
    end
    local gsc = _G.GetSpellCooldown
    if type(gsc) == "function" then
        local ok, st, du = pcall(gsc, spell)
        if ok and type(st) == "number" and type(du) == "number" and st > 0 and du > 0 then
            local left = st + du - clock()
            if left > 0 then return left, du end
            return nil
        end
    end
    local ct = _G.C_TradeSkillUI
    if type(ct) == "table" and type(ct.GetRecipeCooldown) == "function" then
        local ok, sec = pcall(ct.GetRecipeCooldown, spell)
        if ok and type(sec) == "number" and sec > 0 then return sec, sec end
    end
    return nil
end

function W.Mark(spell, slug)
    if type(spell) ~= "number" or type(slug) ~= "string" then return false end
    local l = list()
    if l[spell] == slug then return false end
    l[spell] = slug
    return true
end

function W.UnmarkChar(spell, key)
    local k = know()
    local marks = k[key]
    if type(marks) ~= "table" then return false end
    if marks[spell] == nil then return false end
    marks[spell] = nil
    return true
end

function W.MarkChar(spell, key, nm)
    if type(spell) ~= "number" or type(key) ~= "string" or key == "" then return false end
    local k = know()
    local marks = k[key]
    if type(marks) ~= "table" then
        marks = {}
        k[key] = marks
    end
    syncCharacterMeta(key)
    local cm = clsMap()
    local c = charClass()
    if c and key == W.CharKey() then cm[key] = c end
    if marks[spell] then return false end
    marks[spell] = nm or key
    return true
end

local function recipeInfo(spell)
    local api = _G.C_TradeSkillUI
    if type(api) ~= "table" or type(api.GetRecipeInfo) ~= "function" then return nil end
    local ok, info = pcall(api.GetRecipeInfo, spell)
    if ok and type(info) == "table" then return info end
    return nil
end

local function openRecipes()
    local api = _G.C_TradeSkillUI
    if type(api) ~= "table" or type(api.GetAllRecipeIDs) ~= "function" then return nil end
    local ok, ids = pcall(api.GetAllRecipeIDs)
    if not ok or type(ids) ~= "table" or #ids == 0 then return nil end
    if type(api.IsDataSourceChanging) == "function" then
        local ok2, changing = pcall(api.IsDataSourceChanging)
        if ok2 and changing == true then return nil end
    end
    if type(api.IsTradeSkillReady) == "function" then
        local ok3, ready = pcall(api.IsTradeSkillReady)
        if ok3 and ready == false then return nil end
    end
    local set = {}
    for i = 1, #ids do
        local id = ids[i]
        if type(id) == "number" then set[id] = true end
    end
    return set
end

local function confirmedUnlearned(spell, info)
    if type(info) ~= "table" or info.learned ~= false then return false end
    if type(info.recipeID) == "number" and info.recipeID ~= spell then return false end
    local set = openRecipes()
    return set ~= nil and set[spell] == true
end

local function slugOf(spell)
    local l = list()
    if type(l[spell]) == "string" then return l[spell] end
    local DS = getDS()
    if DS and type(DS.RecipeProfession) == "function" then
        local slug = DS.RecipeProfession(spell)
        if type(slug) == "string" and slug ~= "" then
            W.Mark(spell, slug)
            return slug
        end
    end
    return nil
end

local function recipeEntryDS(slug, spell)
    local DS = getDS()
    if not DS then return nil end
    if type(slug) == "string" and type(DS.Recipes) == "function" then
        local bucket = DS.Recipes(slug)
        if type(bucket) == "table" and type(bucket.recipes) == "table" and type(bucket.recipes[spell]) == "table" then
            return bucket.recipes[spell]
        end
    end
    if type(DS.Recipe) == "function" then
        return DS.Recipe(spell)
    end
    return nil
end

local function hasRecipeCooldown(spell, rec)
    if type(rec) == "table" then
        if rec.availability ~= "live" then return false end
        if type(rec.cooldownSeconds) == "number" and rec.cooldownSeconds > 0 then return true end
        if type(rec.cooldownGroup) == "string" and rec.cooldownGroup ~= "" then return true end
        return baseCD(spell) == true
    end
    return baseCD(spell) == true
end

function W.Record(spell, slug, left, dur)
    if type(spell) ~= "number" or type(left) ~= "number" or left <= 0 then return false end
    local d = (type(dur) == "number" and dur >= left) and dur or left
    local t0 = now()
    local db = store()
    local by = db[spell]
    if type(by) ~= "table" then
        by = {}
        db[spell] = by
    end
    local key = W.CharKey()
    syncCharacterMeta(key)
    local rec = by[key]
    if type(rec) ~= "table" then
        rec = {}
        by[key] = rec
    end
    local stop = t0 + left
    local changed = (type(rec.u) ~= "number") or (math.abs(rec.u - stop) > 3) or rec.prof ~= slug
    rec.u = stop
    rec.d = d
    rec.s = stop - d
    rec.t = t0
    rec.prof = slug
    rec.n = charName()
    local c = charClass()
    rec.cls = c or rec.cls
    if rec.cls then clsMap()[key] = rec.cls end
    return changed
end

function W.Observe(spell, slug)
    if type(spell) ~= "number" or spell <= 0 then return false end
    if type(slug) ~= "string" then slug = slugOf(spell) end
    if type(slug) ~= "string" then return false end
    local left, dur = liveCD(spell)
    if not left then return false end
    return W.Record(spell, slug, left, dur)
end

local function scanRows(slug)
    local DS = getDS()
    if not DS or type(DS.Recipes) ~= "function" then return 0 end
    local bucket = DS.Recipes(slug)
    local recipes = type(bucket) == "table" and bucket.recipes or nil
    if type(recipes) ~= "table" then return 0 end
    local ids = {}
    for spell in pairs(recipes) do
        if type(spell) == "number" then ids[#ids + 1] = spell end
    end
    table.sort(ids)
    local hit = 0
    local key, nm = W.CharKey(), charName()
    for i = 1, #ids do
        local spell = ids[i]
        local rec = recipes[spell]
        if hasRecipeCooldown(spell, rec) then
            W.Mark(spell, slug)
            local info = recipeInfo(spell)
            if info and info.learned == true then
                W.UnmarkChar(spell, key)
                W.MarkChar(spell, key, nm)
                if W.Enabled(spell) then
                    local left, dur = liveCD(spell)
                    if left and W.Record(spell, slug, left, dur) then hit = hit + 1 end
                end
            elseif confirmedUnlearned(spell, info) then
                W.UnmarkChar(spell, key)
                local by = store()[spell]
                if type(by) == "table" then by[key] = nil end
            end
        end
    end
    return hit
end

local function ensureEvents()
    if W.__ef or type(_G.CreateFrame) ~= "function" then return end
    local ok, f = pcall(_G.CreateFrame, "Frame")
    if not ok or type(f) ~= "table" or type(f.RegisterEvent) ~= "function" or type(f.SetScript) ~= "function" then
        return
    end
    W.__ef = f
    pcall(f.RegisterEvent, f, "PLAYER_ENTERING_WORLD")
    pcall(f.RegisterEvent, f, "SPELLS_CHANGED")
    pcall(f.RegisterEvent, f, "UNIT_SPELLCAST_SUCCEEDED")
    pcall(f.RegisterEvent, f, "TRADE_SKILL_SHOW")
    pcall(f.RegisterEvent, f, "TRADE_SKILL_UPDATE")
    pcall(f.SetScript, f, "OnEvent", function(_, event, unit, _, spell)
        if event == "UNIT_SPELLCAST_SUCCEEDED" then
            if unit ~= "player" or type(spell) ~= "number" then return end
            local slug = slugOf(spell)
            if not slug then return end
            local function grab()
                if W.Observe(spell, slug) then
                    local pd = getProfModule()
                    if pd and pd.RequestRender then pcall(pd.RequestRender) end
                end
            end
            local ct = _G.C_Timer
            if type(ct) == "table" and type(ct.After) == "function" then
                ct.After(0.2, grab)
            else
                grab()
            end
            return
        end
        W.__last = 0
        W.ScanAll()
    end)
end

local function allSlugs()
    local DS = getDS()
    if not DS or type(DS.RecipeProfessions) ~= "function" then return {} end
    local raw = DS.RecipeProfessions()
    local out = {}
    if type(raw) == "table" then
        for i = 1, #raw do
            if type(raw[i]) == "string" then out[#out + 1] = raw[i] end
        end
    end
    table.sort(out)
    return out
end

function W.ScanAll()
    ensureEvents()
    local list_ = allSlugs()
    local i, hits = 0, 0
    local function step()
        for _ = 1, 2 do
            i = i + 1
            local slug = list_[i]
            if not slug then break end
            hits = hits + scanRows(slug)
        end
        if i < #list_ then
            local ct = _G.C_Timer
            if type(ct) == "table" and type(ct.After) == "function" then
                ct.After(0.02, step)
            else
                step()
            end
        else
            local pd = getProfModule()
            if pd and pd.RequestRender then pcall(pd.RequestRender) end
            local zh = getZoneHint()
            if zh and zh.ScheduleSoft then pcall(zh.ScheduleSoft, 1) end
        end
    end
    if #list_ == 0 then return 0 end
    step()
    return #list_
end

function W.AutoScan(_slug)
    local t = now()
    W.__last = W.__last or 0
    if t - W.__last < 6 then return end
    W.__last = t
    W.ScanAll()
end

function W.Sweep(slug)
    if type(slug) ~= "string" then return 0 end
    return scanRows(slug)
end

function W.ScanOpen()
    ensureEvents()
    return W.ScanAll()
end

function W.Left(rec)
    if type(rec) ~= "table" or type(rec.u) ~= "number" then return nil end
    return rec.u - now()
end

local function itemName(id, spell)
    if type(id) == "number" and id > 0 then
        local api = getAPI()
        if api and type(api.ItemName) == "function" then
            local nm, known = api.ItemName(id)
            if known == true and type(nm) == "string" and nm ~= "" then
                return nm
            end
        end
        local ci = _G.C_Item
        if type(ci) == "table" and type(ci.GetItemNameByID) == "function" then
            local ok, v = pcall(ci.GetItemNameByID, id)
            if ok and type(v) == "string" and v ~= "" then return v end
        end
        if type(_G.GetItemInfo) == "function" then
            local ok, v = pcall(_G.GetItemInfo, id)
            if ok and type(v) == "string" and v ~= "" then return v end
        end
    end
    if type(spell) == "number" then
        local DS = getDS()
        if DS and type(DS.RawText) == "function" then
            local snm = DS.RawText("spell", spell)
            if type(snm) == "string" and snm ~= "" then return snm end
        end
        return format(tr("法术 #%d"), spell)
    end
    return nil
end

local function recipeMats(rec)
    if type(rec) ~= "table" or type(rec.reagents) ~= "table" then return nil end
    local out = {}
    for i = 1, #rec.reagents do
        local rg = rec.reagents[i]
        if type(rg) == "table" and type(rg.itemID) == "number" then
            out[#out + 1] = { rg.itemID, rg.count or 1 }
        end
    end
    return out
end

local function gainOf(item, mats)
    if type(item) ~= "number" then return nil end
    local api = getAPI()
    local ra = getRouteAuto()
    local ah
    if api and type(api.AHPriceOf) == "function" then
        local ok, v = pcall(api.AHPriceOf, item)
        if ok and type(v) == "number" then ah = v end
    end
    if (type(ah) ~= "number" or ah <= 0) and ra and type(ra.AHPriceOf) == "function" then
        local ok, v = pcall(ra.AHPriceOf, item)
        if ok and type(v) == "number" then ah = v end
    end
    if type(ah) ~= "number" or ah <= 0 then return nil end
    if type(mats) ~= "table" or #mats == 0 then return nil end

    local cost
    if ra and type(ra.MatListCost) == "function" then
        local ok2, c, unpriced, n = pcall(ra.MatListCost, mats)
        if ok2 and type(c) == "number" and c > 0
            and not (type(unpriced) == "number" and type(n) == "number" and n > 0 and unpriced >= n) then
            cost = c
        end
    elseif api and type(api.EffectiveCost) == "function" then
        local sum, unpriced = 0, 0
        for i = 1, #mats do
            local m = mats[i]
            local c = api.EffectiveCost(m[1], m[2] or 1)
            if type(c) == "number" and c >= 0 then
                sum = sum + c
            else
                unpriced = unpriced + 1
            end
        end
        if sum > 0 and unpriced < #mats then cost = sum end
    end
    if type(cost) ~= "number" or cost <= 0 then return nil end

    local cfg = getPricingCfg()
    local mult = (type(cfg) == "table" and type(cfg.NET_MULTIPLIER) == "number" and cfg.NET_MULTIPLIER) or 0.95
    return math.floor(ah * mult) - cost
end

local function fmtLeft(sec)
    if type(sec) ~= "number" then return nil end
    if sec <= 0 then return tr("可再做") end
    local s = math.floor(sec)
    local d = math.floor(s / 86400)
    local h = math.floor((s % 86400) / 3600)
    local m = math.floor((s % 3600) / 60)
    if d > 0 then return format(tr("%d 天 %d 小时"), d, h) end
    if h > 0 then return format(tr("%d 小时 %d 分"), h, m) end
    if m > 0 then return format(tr("%d 分钟"), m) end
    return tr("不到 1 分钟")
end

W.FmtLeft = fmtLeft

function W.Cards(slug)
    local out = {}
    if type(slug) ~= "string" then return out end
    local db = store()
    local l = list()
    local k = know()
    local cur = W.CharKey()
    local t = now()
    local spells = {}
    for spell, s in pairs(l) do
        if s == slug and W.Enabled(spell) then spells[spell] = true end
    end
    for spell, by in pairs(db) do
        if type(by) == "table" and W.Enabled(spell) then
            for _, rec in pairs(by) do
                if type(rec) == "table" and rec.prof == slug then
                    spells[spell] = true
                    break
                end
            end
        end
    end
    for spell in pairs(spells) do
        local by = type(db[spell]) == "table" and db[spell] or {}
        local rows = {}
        for key, rec in pairs(by) do
            local marks = k[key]
            local learned = type(marks) == "table" and marks[spell] ~= nil
            if learned and type(rec) == "table" and (rec.prof == nil or rec.prof == slug) then
                if type(rec.t) == "number" and (t - rec.t) > KEEP_SEC then
                    by[key] = nil
                else
                    rows[#rows + 1] = {
                        key = key,
                        name = rec.n or key,
                        left = (type(rec.u) == "number") and (rec.u - t) or nil,
                        cls = clsOf(key, rec),
                    }
                end
            end
        end
        for key, marks in pairs(k) do
            if type(marks) == "table" and marks[spell] and type(by[key]) ~= "table" then
                rows[#rows + 1] = {
                    key = key,
                    name = marks[spell],
                    left = nil,
                    cls = clsOf(key, nil),
                }
            end
        end
        if #rows > 0 then
            table.sort(rows, function(a, b)
                local ac, bc = (a.key == cur), (b.key == cur)
                if ac ~= bc then return ac end
                return (a.left or 0) < (b.left or 0)
            end)
            local rds = recipeEntryDS(slug, spell)
            local item = rds and rds.outputItemID or nil
            local mats = recipeMats(rds)
            local free, best = 0, nil
            for i = 1, #rows do
                local it = rows[i]
                if it.left == nil or it.left <= 0 then
                    free = free + 1
                elseif not best or it.left < best then
                    best = it.left
                end
            end
            local shown = {}
            local myName = W.Name()
            local myCls = nil
            for i = 1, #rows do
                local it = rows[i]
                if i <= MAX_ROWS then
                    local c = it.cls
                    if not c and it.name == myName then
                        if not myCls then myCls = charClass() end
                        c = myCls
                    end
                    shown[#shown + 1] = {
                        name = it.name,
                        text = (it.left == nil) and tr("可再做") or fmtLeft(it.left),
                        free = (it.left == nil or it.left <= 0),
                        cur = (it.key == cur),
                        cls = c,
                    }
                end
            end
            if #rows > MAX_ROWS then
                shown[#shown + 1] = {
                    name = format(tr("另有 %d 个角色"), #rows - MAX_ROWS),
                    text = "",
                }
            end
            out[#out + 1] = {
                spell = spell,
                item = item,
                name = itemName(item, spell),
                mats = mats,
                gain = gainOf(item, mats),
                rows = shown,
                free = free,
                best = best,
                count = #rows,
            }
        end
    end
    table.sort(out, function(a, b)
        local af = (a.free or 0) > 0
        local bf = (b.free or 0) > 0
        if af ~= bf then return af end
        return (a.best or 0) < (b.best or 0)
    end)
    return out
end

function W.TodoList()
    local out = {}
    local db = store()
    local l = list()
    local k = know()
    local t = now()
    for spell, slug in pairs(l) do
        if W.Enabled(spell) and W.TodoOn(spell) then
            local by = type(db[spell]) == "table" and db[spell] or {}
            local names, byc = {}, {}
            for key, rec in pairs(by) do
                local marks = k[key]
                if type(marks) == "table" and marks[spell] and type(rec) == "table"
                    and (rec.prof == nil or rec.prof == slug) then
                    local left = (type(rec.u) == "number") and (rec.u - t) or nil
                    if left == nil or left <= 0 then
                        local nm = rec.n or key
                        names[#names + 1] = nm
                        byc[#byc + 1] = { name = nm, cls = clsOf(key, rec) }
                    end
                end
            end
            for key, marks in pairs(k) do
                if type(marks) == "table" and marks[spell] and type(by[key]) ~= "table" then
                    local nm = marks[spell]
                    names[#names + 1] = nm
                    byc[#byc + 1] = { name = nm, cls = clsOf(key, nil) }
                end
            end
            if #names > 0 then
                table.sort(names)
                table.sort(byc, function(a, b) return (a.name or "") < (b.name or "") end)
                local rds = recipeEntryDS(slug, spell)
                local item = rds and rds.outputItemID or nil
                out[#out + 1] = {
                    spell = spell,
                    slug = slug,
                    item = item,
                    name = itemName(item, spell),
                    by = names,
                    byc = byc,
                }
            end
        end
    end
    table.sort(out, function(a, b)
        if a.slug ~= b.slug then return a.slug < b.slug end
        return a.spell < b.spell
    end)
    return out
end

function W.Manage(slug)
    local out = {}
    if type(slug) ~= "string" then return out end
    local DS = getDS()
    if not DS or type(DS.Recipes) ~= "function" then return out end
    local bucket = DS.Recipes(slug)
    local recipes = type(bucket) == "table" and bucket.recipes or nil
    if type(recipes) ~= "table" then return out end
    local ids = {}
    for spell in pairs(recipes) do
        if type(spell) == "number" then ids[#ids + 1] = spell end
    end
    table.sort(ids)
    local l = list()
    local db = store()
    local cur = W.CharKey()
    local t = now()
    for i = 1, #ids do
        local spell = ids[i]
        local recDS = recipes[spell]
        if type(recDS) == "table" and recDS.availability == "live" and l[spell] == slug then
            local by = type(db[spell]) == "table" and db[spell] or {}
            local rec = by[cur]
            local left
            if type(rec) == "table" and type(rec.u) == "number" then
                left = rec.u - t
                if left < 0 then left = 0 end
            end
            local item = recDS.outputItemID
            out[#out + 1] = {
                spell = spell,
                item = item,
                name = itemName(item, spell),
                on = W.Enabled(spell),
                todo = W.TodoOn(spell),
                left = left,
                has = (type(rec) == "table"),
            }
        end
    end
    return out
end

function W.ManageCount(slug)
    local list_ = W.Manage(slug)
    local on = 0
    for _, it in ipairs(list_) do
        if it.on then on = on + 1 end
    end
    return #list_, on
end

function W.Summary(slug)
    local cards = W.Cards(slug)
    local free, total, priced = 0, 0, 0
    for _, c in ipairs(cards) do
        if c.free > 0 then
            free = free + 1
            if type(c.gain) == "number" then
                total = total + c.gain
                priced = priced + 1
            end
        end
    end
    return free, total, priced, #cards
end

local function ensureDelegate()
    local api = getAPI()
    if api and type(api.RegisterDelegate) == "function" then
        api.RegisterDelegate("cdwatch", { TodoList = W.TodoList })
    end
end

W.RegisterDelegate = ensureDelegate
ensureDelegate()
