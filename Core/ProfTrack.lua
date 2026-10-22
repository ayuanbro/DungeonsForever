local _, ns = ...

if not ns.LoadForeverPages then return end

local T = {}
ns.ProfTrack = T

local floor = math.floor
local max = math.max
local EMPTY = {}
local listeners = {}

local function now()
    return (type(time) == "function") and time() or 0
end

local function integer(n)
    return type(n) == "number" and n >= 0 and n == floor(n) and n < math.huge
end

local function charKey()
    local name, realm = "?", "?"
    if type(UnitName) == "function" then
        local ok, v = pcall(UnitName, "player")
        if ok and type(v) == "string" and v ~= "" then name = v end
    end
    if type(GetRealmName) == "function" then
        local ok, v = pcall(GetRealmName)
        if ok and type(v) == "string" and v ~= "" then realm = v end
    end
    return name .. "-" .. realm
end

local function db()
    DungeonsForeverDB = DungeonsForeverDB or {}
    local d = DungeonsForeverDB
    d.prof = d.prof or {}
    d.prof.track = d.prof.track or {}
    local key = charKey()
    local c = d.prof.track[key]
    if type(c) ~= "table" or c.version ~= 1 then
        c = { version = 1, nextID = 0, nextAttempt = 0, active = {}, runs = {}, seen = {}, order = {} }
        d.prof.track[key] = c
    end
    c.active = c.active or {}
    c.runs = c.runs or {}
    c.seen = c.seen or {}
    c.order = c.order or {}
    return c
end

local function skillOf(slug)
    local PD = ns.ProfModule
    if PD and PD.ProfLearned then
        local ok, all = pcall(PD.ProfLearned)
        if ok and type(all) == "table" then
            local e = all[slug]
            if type(e) == "table" then return tonumber(e.cur) end
        end
    end
    return nil
end

local function progressOf(run, i)
    run.progress = run.progress or {}
    local p = run.progress[i]
    if type(p) ~= "table" then
        p = { casts = 0, attempts = {} }
        run.progress[i] = p
    end
    p.attempts = p.attempts or {}
    return p
end

local function notify(slug, run)
    for _, fn in ipairs(listeners) do
        pcall(fn, slug, run)
    end
end

local function activeList()
    local c = db()
    local out = {}
    for slug, planID in pairs(c.active) do
        local run = c.runs[planID]
        if run and run.status == "active" then out[#out + 1] = slug end
    end
    table.sort(out)
    return out
end

function T.OnChanged(fn)
    if type(fn) == "function" then listeners[#listeners + 1] = fn end
end

function T.Get(slug, planID)
    if not planID then return nil end
    return db().runs[planID]
end

function T.GetRun(slug)
    local c = db()
    local id = c.active[slug]
    if not id then return nil end
    return c.runs[id]
end

function T.Active(slug)
    local run = T.GetRun(slug)
    if run and run.status == "active" then return run end
    return nil
end

function T.Extract(result)
    local src = result and result.steps
    if type(src) ~= "table" or #src == 0 then return nil end
    local out = {}
    for _, st in ipairs(src) do
        local spell = st[3]
        if type(spell) ~= "number" then return nil end
        local mats = {}
        for _, m in ipairs(st.mats or EMPTY) do
            if type(m) == "table" and type(m[1]) == "number" then
                mats[#mats + 1] = { m[1], tonumber(m[2]) or 1 }
            end
        end
        out[#out + 1] = {
            from = tonumber(st[1]) or 0,
            to = tonumber(st[2]) or 0,
            spell = spell,
            crafts = tonumber(st[4]) or 0,
            item = st.item,
            out = st.out,
            mats = mats,
            cost = st.cost,
            est = st.est and true or nil,
        }
    end
    if #out == 0 then return nil end
    return out
end

function T.SamePlan(run, result)
    if not (run and result) then return false end
    if run.target ~= result.target or run.scheme ~= result.scheme then return false end
    local other = T.Extract(result)
    if not other then return false end
    local mine = run.steps or EMPTY
    if #other ~= #mine then return false end
    for i, st in ipairs(mine) do
        local o = other[i]
        if not o or o.spell ~= st.spell or o.crafts ~= st.crafts or o.to ~= st.to then return false end
    end
    return true
end

function T.Archive(slug, reason, run)
    run = run or T.GetRun(slug)
    if run then
        run.status = "archived"
        run.archivedAt = now()
        run.archiveReason = reason or "replace"
    end
    db().active[slug] = nil
    if run then notify(slug, run) end
    return run
end

function T.Drop(slug)
    local c = db()
    c.active[slug] = nil
    local kept = {}
    for id, run in pairs(c.runs) do
        if run.slug ~= slug then kept[id] = run end
    end
    c.runs = kept
end

function T.Bind(slug, result, opts)
    if type(slug) ~= "string" then return nil, "bad_slug" end
    opts = opts or {}
    local c = db()
    local old = T.GetRun(slug)
    if old and old.status == "active" and not opts.force then
        return old, "existing"
    end
    local steps = T.Extract(result)
    if not steps then return nil, "no_steps" end
    if old then T.Archive(slug, opts.force and "replace" or "stale", old) end
    c.nextID = (c.nextID or 0) + 1
    local planID = charKey() .. ":track:" .. c.nextID
    local run = {
        planID = planID,
        slug = slug,
        status = "active",
        createdAt = now(),
        updatedAt = now(),
        progressVersion = 0,
        start = tonumber(result.start),
        target = tonumber(result.target),
        scheme = result.scheme,
        totalCost = tonumber(result.total),
        priced = result.priced and true or nil,
        startSkill = skillOf(slug),
        steps = steps,
        progress = {},
        outputs = {},
        currentIndex = 1,
        step = 1,
        casts = 0,
    }
    c.runs[planID] = run
    c.active[slug] = planID
    T.Sync(slug)
    run.updatedAt = now()
    notify(slug, run)
    return run
end

function T.Restart(slug, result)
    return T.Bind(slug, result, { force = true })
end

function T.History(slug)
    local c = db()
    local list = {}
    for _, run in pairs(c.runs) do
        if not slug or run.slug == slug then list[#list + 1] = run end
    end
    table.sort(list, function(a, b)
        if (a.status == "active") ~= (b.status == "active") then return a.status == "active" end
        if a.createdAt ~= b.createdAt then return (a.createdAt or 0) > (b.createdAt or 0) end
        return tostring(a.planID) > tostring(b.planID)
    end)
    return list
end

function T.Skill(slug)
    return skillOf(slug)
end

function T.Sync(slug)
    local run = T.GetRun(slug)
    if not run then return nil end
    local cur = skillOf(slug)
    if cur == nil then return run end
    run.currentSkill = cur
    if run.startSkill and cur < run.startSkill then
        run.status = "stale"
        run.staleReason = "skill_dropped"
        db().active[slug] = nil
        notify(slug, run)
        return run
    end
    local i = 1
    local steps = run.steps or EMPTY
    while i <= #steps and cur >= (steps[i].to or 0) do
        i = i + 1
    end
    local moved = (run.currentIndex ~= i)
    run.currentIndex = i
    run.step = i
    run.finished = (i > #steps) and true or nil
    run.updatedAt = now()
    if run.finished and run.status == "active" then
        run.status = "done"
        run.doneAt = now()
        db().active[slug] = nil
        moved = true
    end
    if moved then
        run.progressVersion = (run.progressVersion or 0) + 1
        notify(slug, run)
    end
    return run
end

function T.Progress(slug, index, run)
    run = run or T.GetRun(slug)
    if not run then return nil end
    local i = index or run.currentIndex or 1
    local st = (run.steps or EMPTY)[i]
    if not st then
        return { index = i, complete = true, finished = true, casts = 0, planned = 0 }
    end
    local p = progressOf(run, i)
    local cur = run.currentSkill
    if cur == nil then cur = skillOf(slug) end
    local done = (cur ~= nil) and cur >= (st.to or 0)
    local outputs = 0
    for _, a in ipairs(p.attempts) do outputs = outputs + (tonumber(a.out) or 0) end
    if type(p.manual) == "table" then outputs = outputs + (tonumber(p.manual.total) or 0) end
    local planned = st.crafts or 0
    local casts = p.casts or 0
    return {
        index = i,
        from = st.from,
        to = st.to,
        spell = st.spell,
        item = st.item,
        mats = st.mats,
        planned = planned,
        casts = casts,
        outputs = outputs,
        remaining = max(0, planned - casts),
        current = cur,
        complete = done,
        skillDone = done,
        started = casts > 0,
        over = (planned > 0 and casts > planned * 1.5) and true or nil,
    }
end

function T.ProgressAll(slug)
    local run = T.GetRun(slug)
    if not run then return nil end
    local out = { run = run, current = run.currentIndex or 1, finished = run.finished and true or nil, steps = {} }
    for i = 1, #(run.steps or EMPTY) do
        out.steps[i] = T.Progress(slug, i, run)
    end
    return out
end

function T.Match(run, spellID)
    local steps = run.steps or EMPTY
    local cur = run.currentIndex or 1
    local st = steps[cur]
    if st and st.spell == spellID then return cur end
    for i = cur + 1, #steps do
        if steps[i].spell == spellID then return i end
    end
    for i = 1, cur - 1 do
        if steps[i].spell == spellID then return i end
    end
    return nil
end

function T.RecordAttempt(slug, spellID, castGUID)
    if type(spellID) ~= "number" then return false, "bad_spell" end
    local run = T.GetRun(slug)
    if not run or run.status ~= "active" then return false, "inactive" end
    local i = T.Match(run, spellID)
    if not i then return false, "no_match" end
    local c = db()
    if castGUID then
        local key = tostring(castGUID)
        if c.seen[key] then return false, "duplicate" end
        c.seen[key] = true
        c.order[#c.order + 1] = key
        while #c.order > 512 do
            c.seen[table.remove(c.order, 1)] = nil
        end
    end
    c.nextAttempt = (c.nextAttempt or 0) + 1
    local p = progressOf(run, i)
    local st = run.steps[i]
    p.casts = (p.casts or 0) + 1
    p.attempts[#p.attempts + 1] = {
        seq = c.nextAttempt,
        spell = spellID,
        castGUID = castGUID,
        at = now(),
        item = st.item,
    }
    run.casts = (run.casts or 0) + 1
    run.progressVersion = (run.progressVersion or 0) + 1
    run.updatedAt = now()
    notify(slug, run)
    return true
end

function T.RecordOutput(slug, itemID, qty, castGUID)
    if not integer(itemID) or itemID <= 0 then return false, "bad_item" end
    qty = integer(qty) and qty or 1
    local run = T.GetRun(slug)
    if not run then return false, "no_run" end
    local steps = run.steps or EMPTY
    local found
    for i = #steps, 1, -1 do
        local st = steps[i]
        local p = (run.progress or {})[i]
        if p then
            for _, a in ipairs(p.attempts or EMPTY) do
                if (st.item == itemID or a.item == itemID) and a.out == nil then
                    if not castGUID or a.castGUID == castGUID then
                        found = a
                        break
                    end
                end
            end
        end
        if found then break end
    end
    if not found then return false, "unmatched" end
    found.out = qty
    found.outputAt = now()
    run.outputs[itemID] = (run.outputs[itemID] or 0) + qty
    run.progressVersion = (run.progressVersion or 0) + 1
    run.updatedAt = now()
    notify(slug, run)
    return true
end

function T.VerifyOutput(slug, index, itemID, total)
    if not integer(itemID) or itemID <= 0 or not integer(total) then return false, "bad_input" end
    local run = T.GetRun(slug)
    if not run then return false, "no_run" end
    local st = (run.steps or EMPTY)[index or 0]
    if not st then return false, "no_step" end
    local p = progressOf(run, index)
    p.manual = { item = itemID, total = total, at = now() }
    run.outputs[itemID] = total
    run.progressVersion = (run.progressVersion or 0) + 1
    run.updatedAt = now()
    notify(slug, run)
    return true
end

function T.RecipeTotals(slug)
    local run = T.GetRun(slug)
    if not run then return EMPTY end
    local list, bySpell = {}, {}
    for i, st in ipairs(run.steps or EMPTY) do
        local entry = bySpell[st.spell]
        if not entry then
            entry = { spell = st.spell, item = st.item, casts = 0, out = 0, from = st.from, to = st.to }
            bySpell[st.spell] = entry
            list[#list + 1] = entry
        end
        local p = (run.progress or {})[i]
        if p then
            entry.casts = entry.casts + (p.casts or 0)
            for _, a in ipairs(p.attempts or EMPTY) do
                entry.out = entry.out + (tonumber(a.out) or 0)
            end
            if type(p.manual) == "table" then
                entry.out = entry.out + (tonumber(p.manual.total) or 0)
            end
        end
    end
    local kept = {}
    for _, e in ipairs(list) do
        if e.casts > 0 then kept[#kept + 1] = e end
    end
    return kept
end

function T.Summary(slug)
    local run = T.GetRun(slug)
    if not run then
        local hist = T.History(slug)
        run = hist[1]
    end
    if not run then return nil end
    local planned, casts, done = 0, 0, 0
    for i, st in ipairs(run.steps or EMPTY) do
        planned = planned + (st.crafts or 0)
        local p = (run.progress or {})[i]
        if p then casts = casts + (p.casts or 0) end
        if i < (run.currentIndex or 1) then done = done + 1 end
    end
    return {
        planID = run.planID,
        status = run.status,
        current = run.currentIndex or 1,
        total = #(run.steps or EMPTY),
        done = done,
        planned = planned,
        casts = casts,
        skill = run.currentSkill,
        target = run.target,
        startSkill = run.startSkill,
        finished = run.finished and true or nil,
        stale = run.status == "stale" and true or nil,
    }
end

local function formatPattern(fmt)
    if type(fmt) ~= "string" or fmt == "" then return nil end
    local out, kinds = {}, {}
    local i = 1
    while i <= #fmt do
        local position, kind = fmt:sub(i):match("^%%(%d+)%$([sd])")
        local advance
        if position then
            advance = #position + 3
        else
            kind = fmt:sub(i):match("^%%([sd])")
            advance = 2
        end
        if kind then
            if kind == "d" then
                out[#out + 1] = "(%d+)"
            else
                out[#out + 1] = "(.-)"
            end
            kinds[#kinds + 1] = kind
            i = i + advance
        elseif fmt:sub(i, i + 1) == "%%" then
            out[#out + 1] = "%%"
            i = i + 2
        else
            local ch = fmt:sub(i, i)
            out[#out + 1] = (ch:gsub("([%^%$%(%)%%%.%[%]%*%+%-%?])", "%%%1"))
            i = i + 1
        end
    end
    return "^" .. table.concat(out) .. "$", kinds
end

local function recordAll(fn)
    for _, slug in ipairs(activeList()) do
        fn(slug)
    end
end

local function onLootMessage(text)
    if type(text) ~= "string" then return end
    local itemID, qty
    for _, name in ipairs({ "LOOT_ITEM_CREATED_SELF_MULTIPLE", "LOOT_ITEM_CREATED_SELF" }) do
        local pat, kinds = formatPattern(_G[name])
        if pat then
            local captures = { text:match(pat) }
            if #captures > 0 then
                for i, v in ipairs(captures) do
                    if kinds[i] == "d" then
                        if qty == nil then qty = tonumber(v) end
                    else
                        local id = tonumber(v:match("item:(%d+)"))
                        if id then itemID = id end
                    end
                end
                if itemID then break end
            end
        end
    end
    if not integer(itemID) then return end
    recordAll(function(slug)
        T.RecordOutput(slug, itemID, qty)
    end)
end

function T.RecordCreatedText(text)
    onLootMessage(text)
end

local function syncAll()
    for _, slug in ipairs(activeList()) do
        T.Sync(slug)
    end
end

local function initialize()
    local c = db()
    c.session = (c.session or 0) + 1
    T.session = tostring(c.session)
    if type(CreateFrame) ~= "function" then return end
    local f = CreateFrame("Frame")
    T.frame = f
    T.capabilities = {}
    f:SetScript("OnEvent", function(_, event, ...)
        if event == "UNIT_SPELLCAST_SUCCEEDED" then
            local unit, castGUID, spellID = ...
            if unit == "player" and type(spellID) == "number" then
                for _, slug in ipairs(activeList()) do
                    if T.RecordAttempt(slug, spellID, castGUID) then break end
                end
            end
        elseif event == "TRADE_SKILL_ITEM_CRAFTED_RESULT" then
            local a = ...
            local itemID, qty
            if type(a) == "table" then
                itemID = tonumber(a.itemID or a.id)
                qty = tonumber(a.quantity or a.count)
            else
                itemID = tonumber(a)
                qty = tonumber((select(2, ...)))
            end
            if integer(itemID) and itemID > 0 then
                recordAll(function(slug)
                    T.RecordOutput(slug, itemID, qty)
                end)
            end
        elseif event == "CHAT_MSG_LOOT" then
            local args = { ... }
            onLootMessage(args[1])
        elseif event == "SKILL_LINES_CHANGED" or event == "CHAT_MSG_SKILL"
            or event == "SPELLS_CHANGED" or event == "LEARNED_SPELL_IN_TAB" then
            syncAll()
        end
    end)
    for _, event in ipairs({
        "UNIT_SPELLCAST_SUCCEEDED", "TRADE_SKILL_ITEM_CRAFTED_RESULT", "CHAT_MSG_LOOT",
        "SKILL_LINES_CHANGED", "CHAT_MSG_SKILL", "SPELLS_CHANGED", "LEARNED_SPELL_IN_TAB",
    }) do
        T.capabilities[event] = pcall(f.RegisterEvent, f, event) and true or false
    end
    syncAll()
end

if ns.Init then ns.Init(initialize) else initialize() end
