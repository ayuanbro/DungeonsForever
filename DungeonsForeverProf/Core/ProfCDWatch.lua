local ns = _G.DF_NS or {}

if not ns.LoadForeverPages then return end

local L = ns.L
local format = string.format

local W = {}
ns.ProfCDWatch = W

local KEEP_SEC = 45 * 86400
local MAX_ROWS = 3
local STEP = 40

local function now()
    return type(time) == "function" and time() or 0
end

local function clock()
    local f = _G.GetTime
    return type(f) == "function" and f() or 0
end

local CD_VER = 2

local function prof()
    local db = ns.ProfDB()
    if type(db.prof) ~= "table" then db.prof = {} end
    local p = db.prof
    if p.cdVer ~= CD_VER then
        p.cdVer = CD_VER
        p.cd = {}
        p.cdKnow = {}
    end
    return p
end

local function store()
    local p = prof()
    if type(p.cd) ~= "table" then p.cd = {} end
    return p.cd
end

local function list()
    local p = prof()
    if type(p.cdList) ~= "table" then p.cdList = {} end
    return p.cdList
end

local function know()
    local p = prof()
    if type(p.cdKnow) ~= "table" then p.cdKnow = {} end
    return p.cdKnow
end

local function offs()
    local p = prof()
    if type(p.cdOff) ~= "table" then p.cdOff = {} end
    return p.cdOff
end

local function todoOns()
    local p = prof()
    if type(p.cdTodoOn) ~= "table" then p.cdTodoOn = {} end
    return p.cdTodoOn
end

local TODO_DEF = { [17187] = true, [1317279] = true, [18560] = true }

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
    local pd = ns.ProfModule
    if pd and pd.RequestRender then pd.RequestRender() end
    if ns.ZoneHint and ns.ZoneHint.RefreshSoft then
        pcall(ns.ZoneHint.RefreshSoft, true)
    end
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
    local pd = ns.ProfModule
    if pd and pd.RequestRender then pd.RequestRender() end
    if ns.ZoneHint and ns.ZoneHint.RefreshSoft then
        pcall(ns.ZoneHint.RefreshSoft, true)
    end
    return true
end

function W.SetSlugEnabled(slug, on)
    if type(slug) ~= "string" then return 0 end
    local l = list()
    local o = offs()
    on = (on == true)
    local n = 0
    for spell, s in pairs(l) do
        if s == slug and W.Enabled(spell) ~= on then
            if on then
                o[spell] = nil
            else
                o[spell] = true
            end
            n = n + 1
        end
    end
    if n > 0 then
        local pd = ns.ProfModule
        if pd and pd.RequestRender then pd.RequestRender() end
        if ns.ZoneHint and ns.ZoneHint.RefreshSoft then
            pcall(ns.ZoneHint.RefreshSoft, true)
        end
    end
    return n
end

W.Store = store

local function hasSurname()
    if type(RegionalUniqueNamesEnabled) ~= "function" then return false end
    local ok, v = pcall(RegionalUniqueNamesEnabled)
    return ok and v == true
end

local function nameParts()
    local n, s2
    if type(UnitNameUnmodified) == "function" then
        local ok, a, b = pcall(UnitNameUnmodified, "player")
        if ok then n, s2 = a, b end
    end
    if type(n) ~= "string" or n == "" then
        local ok, a = pcall(UnitName, "player")
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

local function migrate()
    local p = prof()
    if p.cdMig == 6 then return end
    p.cdMig = 6
    p.cdTodoOff = nil
    local full = W.Name()
    local ok, r = pcall(GetRealmName)
    if not ok or type(r) ~= "string" then r = "?" end
    local newKey = full .. "-" .. r
    local k = know()
    local short = nil
    local okn, a = pcall(UnitName, "player")
    if okn and type(a) == "string" and a ~= "" then short = a end
    if type(short) ~= "string" or short == full then return end
    local old = short .. "-" .. r
    local db = store()
    for _, by in pairs(db) do
        if type(by) == "table" and type(by[old]) == "table" then
            local src, dst = by[old], by[newKey]
            if type(dst) ~= "table" then
                by[newKey] = src
            elseif type(src.u) == "number" and (type(dst.u) ~= "number" or src.u > dst.u) then
                by[newKey] = src
            end
            by[old] = nil
            if type(by[newKey]) == "table" then by[newKey].n = full end
        end
    end
    if type(k[old]) == "table" then
        local src, dst = k[old], k[newKey]
        if type(dst) ~= "table" then
            k[newKey] = src
        else
            for spell, v in pairs(src) do
                if dst[spell] == nil then dst[spell] = v end
            end
        end
        k[old] = nil
    end
    local marks = k[newKey]
    if type(marks) == "table" then
        for spell, v in pairs(marks) do
            if v == short then marks[spell] = full end
        end
    end
end

function W.CharKey()
    local r = type(GetRealmName) == "function" and GetRealmName() or nil
    return W.Name() .. "-" .. tostring(r or "?")
end

local function charName()
    return W.Name()
end

local function charClass()
    if type(UnitClass) ~= "function" then return nil end
    local _, token, id = UnitClass("player")
    if type(token) == "string" and token ~= "" then return token end
    if type(id) == "string" and id ~= "" then return id end
    return nil
end

local function clsOf(key, rec)
    if type(rec) == "table" and type(rec.cls) == "string" then return rec.cls end
    local p = prof()
    local t = p.cdCls
    if type(t) == "table" and type(t[key]) == "string" then return t[key] end
    if key == W.CharKey() then return charClass() end
    return nil
end

local function baseCD(spell)
    local f = _G.GetSpellBaseCooldown
    if type(f) ~= "function" then return nil end
    local ok, ms = pcall(f, spell)
    if ok and type(ms) == "number" then return ms > 0 end
    return nil
end

local function liveCD(spell)
    local api = C_Spell
    if type(api) == "table" and type(api.GetSpellCooldown) == "function" then
        local ok, left, du = pcall(function()
            local sc = api.GetSpellCooldown(spell)
            if type(sc) ~= "table" then return nil end
            local d = sc.duration
            local l = sc.timeUntilEndOfStartRecovery
            if type(l) ~= "number" then
                local st = sc.startTime
                local g = clock()
                if type(st) == "number" and type(d) == "number" and st <= g + 60 then
                    l = st + d - g
                end
            end
            if type(l) ~= "number" or l <= 0 then return nil end
            if type(d) ~= "number" or d <= 0 then d = l end
            return l, d
        end)
        if ok and type(left) == "number" and left > 0 then return left, du end
    end
    local tr = C_TradeSkillUI
    if type(tr) == "table" and type(tr.GetRecipeCooldown) == "function" then
        local ok, sec = pcall(tr.GetRecipeCooldown, spell)
        if ok and type(sec) == "number" and sec > 0 then return sec, sec end
    end
    return nil
end

local function baseDur(spell)
    local f = _G.GetSpellBaseCooldown
    if type(f) ~= "function" then return nil end
    local ok, ms = pcall(f, spell)
    if ok and type(ms) == "number" and ms > 0 then return ms / 1000 end
    return nil
end

local function repairExisting()
    local db = store()
    local key = W.CharKey()
    local l = list()
    local t = now()
    for spell, by in pairs(db) do
        local rec = type(by) == "table" and by[key] or nil
        if type(rec) == "table" and W.Enabled(spell) then
            local left, dur = liveCD(spell)
            if type(left) == "number" and left > 0 then
                local slug = type(l[spell]) == "string" and l[spell] or rec.prof
                if type(slug) == "string" then W.Record(spell, slug, left, dur) end
            else
                local api = C_Spell
                if type(api) == "table" and type(api.GetSpellCooldown) == "function" then
                    local ok, sc = pcall(api.GetSpellCooldown, spell)
                    if ok and type(sc) == "table" and type(sc.duration) == "number" and sc.duration == 0 then
                        local base = baseDur(spell)
                        if base and type(rec.d) == "number" and rec.d > base * 3 then
                            rec.u = t
                            rec.d = base
                            rec.s = t - base
                        end
                    end
                end
            end
        end
    end
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
    if type(spell) ~= "number" then return false end
    local k = know()
    local marks = k[key]
    if type(marks) ~= "table" then marks = {}; k[key] = marks end
    if marks[spell] then return false end
    marks[spell] = nm or key
    local p = prof()
    if type(p.cdCls) ~= "table" then p.cdCls = {} end
    local c = charClass()
    if c then p.cdCls[key] = c end
    return true
end

local function recipeInfo(spell)
    local api = C_TradeSkillUI
    if not (api and api.GetRecipeInfo) then return nil end
    local ok, info = pcall(api.GetRecipeInfo, spell)
    if ok and type(info) == "table" then return info end
    return nil
end

local function openRecipes()
    local api = C_TradeSkillUI
    if not (api and api.GetAllRecipeIDs) then return nil end
    local ok, ids = pcall(api.GetAllRecipeIDs)
    if not ok or type(ids) ~= "table" or #ids == 0 then return nil end
    if api.IsDataSourceChanging then
        local ok2, changing = pcall(api.IsDataSourceChanging)
        if ok2 and changing == true then return nil end
    end
    if api.IsTradeSkillReady then
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
    for slug, g in pairs(ns.ProfRecipes or {}) do
        for _, row in ipairs(g.rows or {}) do
            if row[1] == spell then
                W.Mark(spell, slug)
                return slug
            end
        end
    end
    return nil
end

function W.Record(spell, slug, left, dur)
    if type(spell) ~= "number" or type(left) ~= "number" or left <= 0 then return false end
    local d = (type(dur) == "number" and dur >= left) and dur or left
    local t0 = now()
    local db = store()
    local by = db[spell]
    if type(by) ~= "table" then by = {}; db[spell] = by end
    local key = W.CharKey()
    local rec = by[key]
    if type(rec) ~= "table" then rec = {}; by[key] = rec end
    local stop = t0 + left
    local changed = (type(rec.u) ~= "number") or (math.abs(rec.u - stop) > 3) or rec.prof ~= slug
    rec.u = stop
    rec.d = d
    rec.s = stop - d
    rec.t = t0
    rec.prof = slug
    rec.n = charName()
    rec.cls = charClass() or rec.cls
    return changed
end

function W.Observe(spell, slug)
    if type(spell) ~= "number" or spell <= 0 then return false end
    local left, dur = liveCD(spell)
    if not left then return false end
    if type(slug) ~= "string" then slug = slugOf(spell) end
    if type(slug) ~= "string" then return false end
    return W.Record(spell, slug, left, dur)
end

local function scanRows(slug)
    local g = ns.ProfRecipes and ns.ProfRecipes[slug]
    local rows = g and g.rows
    if type(rows) ~= "table" or #rows == 0 then return 0 end
    local hit = 0
    local key, nm = W.CharKey(), charName()
    for i = 1, #rows do
        local spell = rows[i][1]
        if type(spell) == "number" then
            if baseCD(spell) == true then
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
    end
    return hit
end

local function ensureEvents()
    if W.__ef or type(CreateFrame) ~= "function" then return end
    local ok, f = pcall(CreateFrame, "Frame")
    if not ok or not f then return end
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
                    local pd = ns.ProfModule
                    if pd and pd.RequestRender then pd.RequestRender() end
                end
            end
            if C_Timer and C_Timer.After then C_Timer.After(0.2, grab) else grab() end
            return
        end
        W.__last = 0
        W.ScanAll()
    end)
end

local function allSlugs()
    local out = {}
    for slug in pairs(ns.ProfRecipes or {}) do out[#out + 1] = slug end
    table.sort(out)
    return out
end

function W.ScanAll()
    migrate()
    ensureEvents()
    repairExisting()
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
            if C_Timer and C_Timer.After then
                C_Timer.After(0.02, step)
            else
                step()
            end
        else
            local pd = ns.ProfModule
            if pd and pd.TrackRenderRequest then
                pd.TrackRenderRequest()
            elseif pd and pd.RequestRender then pd.RequestRender() end
            if ns.ZoneHint and ns.ZoneHint.ScheduleSoft then
                pcall(ns.ZoneHint.ScheduleSoft, 1)
            end
        end
    end
    if #list_ == 0 then return 0 end
    step()
    return #list_
end

function W.AutoScan(slug)
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

local function itemName(id)
    if type(id) ~= "number" then return nil end
    local nm
    if C_Item and C_Item.GetItemNameByID then
        local ok, v = pcall(C_Item.GetItemNameByID, id)
        if ok then nm = v end
    end
    if (type(nm) ~= "string" or nm == "") and type(GetItemInfo) == "function" then
        local v = GetItemInfo(id)
        if type(v) == "string" then nm = v end
    end
    return nm
end

local function recipeRow(slug, spell)
    local g = ns.ProfRecipes and ns.ProfRecipes[slug]
    if not g then return nil end
    for _, row in ipairs(g.rows or {}) do
        if row[1] == spell then return row end
    end
    return nil
end

local RA
local function router()
    if RA == nil then RA = ns.ProfRouteAuto or false end
    return RA or nil
end

local function gainOf(item, mats)
    local m = router()
    if not m or not m.AHPriceOf or type(item) ~= "number" then return nil end
    local ok, ah = pcall(m.AHPriceOf, item)
    if not ok or type(ah) ~= "number" or ah <= 0 then return nil end
    if not (m.MatListCost and type(mats) == "table" and #mats > 0) then return nil end
    local ok2, cost, unpriced, n = pcall(m.MatListCost, mats)
    if not ok2 or type(cost) ~= "number" or cost <= 0 then return nil end
    if type(unpriced) == "number" and type(n) == "number" and n > 0 and unpriced >= n then return nil end
    return math.floor(ah * 0.95) - cost
end

local function fmtLeft(sec)
    if type(sec) ~= "number" then return nil end
    if sec <= 0 then return L["可再做"] end
    local s = math.floor(sec)
    local d = math.floor(s / 86400)
    local h = math.floor((s % 86400) / 3600)
    local m = math.floor((s % 3600) / 60)
    if d > 0 then return format(L["%d 天 %d 小时"], d, h) end
    if h > 0 then return format(L["%d 小时 %d 分"], h, m) end
    if m > 0 then return format(L["%d 分钟"], m) end
    return L["不到 1 分钟"]
end

W.FmtLeft = fmtLeft

function W.Cards(slug)
    migrate()
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
        if type(by) == "table" then
            for _, rec in pairs(by) do
                if type(rec) == "table" and rec.prof == slug then spells[spell] = true break end
            end
        end
    end
    for spell in pairs(spells) do
        local by = type(db[spell]) == "table" and db[spell] or {}
        local rows, seen = {}, {}
        for key, rec in pairs(by) do
            local marks = k[key]
            local learned = type(marks) == "table" and marks[spell] ~= nil
            if learned and type(rec) == "table" and (rec.prof == nil or rec.prof == slug) then
                if type(rec.t) == "number" and t - rec.t > KEEP_SEC then
                    by[key] = nil
                else
                    rows[#rows + 1] = {
                        key = key,
                        name = rec.n or key,
                        left = (type(rec.u) == "number") and (rec.u - t) or nil,
                        cls = clsOf(key, rec),
                    }
                    seen[key] = true
                end
            end
        end
        for key, marks in pairs(k) do
            if type(marks) == "table" and marks[spell] and type(by[key]) ~= "table" then
                rows[#rows + 1] = { key = key, name = marks[spell], left = nil,
                                    cls = clsOf(key, nil) }
            end
        end
        if #rows > 0 then
            table.sort(rows, function(a, b)
                local ac, bc = (a.key == cur), (b.key == cur)
                if ac ~= bc then return ac end
                return (a.left or 0) < (b.left or 0)
            end)
            local row = recipeRow(slug, spell)
            local item = row and row[2] or nil
            local mats = row and row[12] or nil
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
                        text = (it.left == nil) and L["可再做"] or fmtLeft(it.left),
                        free = (it.left == nil or it.left <= 0),
                        cur = (it.key == cur),
                        cls = c,
                    }
                end
            end
            if #rows > MAX_ROWS then
                shown[#shown + 1] = {
                    name = format(L["另有 %d 个角色"], #rows - MAX_ROWS),
                    text = "",
                }
            end
            out[#out + 1] = {
                spell = spell,
                item = item,
                name = itemName(item) or format(L["法术 #%d"], spell),
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
    migrate()
    local out = {}
    local db = store()
    local l = list()
    local k = know()
    local t = now()
    for spell, slug in pairs(l) do
        if W.Enabled(spell) and W.TodoOn(spell) then
            local by = type(db[spell]) == "table" and db[spell] or {}
            local names, byc, seen = {}, {}, {}
            for key, rec in pairs(by) do
                local marks = k[key]
                if type(marks) == "table" and marks[spell] and type(rec) == "table"
                   and (rec.prof == nil or rec.prof == slug) then
                    local left = (type(rec.u) == "number") and (rec.u - t) or nil
                    if left == nil or left <= 0 then
                        local nm = rec.n or key
                        names[#names + 1] = nm
                        byc[#byc + 1] = { name = nm, cls = clsOf(key, rec) }
                        seen[key] = true
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
                local row = recipeRow(slug, spell)
                local item = row and row[2] or nil
                out[#out + 1] = {
                    spell = spell,
                    slug = slug,
                    item = item,
                    name = itemName(item) or format(L["法术 #%d"], spell),
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
    migrate()
    local out = {}
    if type(slug) ~= "string" then return out end
    local l = list()
    local db = store()
    local cur = W.CharKey()
    local t = now()
    local g = ns.ProfRecipes and ns.ProfRecipes[slug]
    local src = g and g.rows
    if type(src) ~= "table" then return out end
    for i = 1, #src do
        local spell = src[i][1]
        if type(spell) == "number" and l[spell] == slug then
            local by = type(db[spell]) == "table" and db[spell] or {}
            local rec = by[cur]
            local left
            if type(rec) == "table" and type(rec.u) == "number" then
                left = rec.u - t
                if left < 0 then left = 0 end
            end
            local item = src[i][2]
            out[#out + 1] = {
                spell = spell,
                item = item,
                name = itemName(item) or format(L["法术 #%d"], spell),
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
