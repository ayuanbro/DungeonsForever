local _, ns = ...
if type(ns) ~= "table" then return end

local M = {}
ns.BossKill = M

local KEY = "bossKill"
local RUN_GAP = 1800
local KEEP = 86400
local REPEAT_WINDOW = 10
local LOGN = 60

local function now()
    if type(time) == "function" then return time() end
    return 0
end

local function isSecret(v)
    if type(issecretvalue) ~= "function" then return false end
    local ok, s = pcall(issecretvalue, v)
    return (ok and s) and true or false
end

local function plain(v)
    if type(v) ~= "string" then return nil end
    if isSecret(v) then return nil end
    return v
end

local function safeStr(v)
    if v == nil then return "nil" end
    local t = type(v)
    if t == "boolean" or t == "number" then return tostring(v) end
    if t ~= "string" then return "<" .. t .. ">" end
    if isSecret(v) then return "<secret>" end
    local ok, s = pcall(string.format, "%s", v)
    if not ok or type(s) ~= "string" then return "<unreadable>" end
    return s
end

local function store()
    local db = DungeonsForeverDB
    if type(db) ~= "table" then return nil end
    if type(db.dungeon) ~= "table" then db.dungeon = {} end
    local s = db.dungeon[KEY]
    if type(s) ~= "table" then
        s = {}
        db.dungeon[KEY] = s
    end
    return s
end

local function nkey(v)
    if type(v) ~= "string" then return nil end
    v = v:gsub("[%s'%-%.,:]", "")
    if v == "" then return nil end
    return v:lower()
end

local index

local function rowOK(s)
    if type(s[1]) ~= "string" or s[1] == "" then return false end
    if s[1] == "Trash mobs" or s[1] == "Plans" then return false end
    local meta = type(s[3]) == "string" and s[3] or ""
    if meta:find("宝箱", 1, true) or meta:find("图纸", 1, true) then return false end
    if meta:find("任意敌人", 1, true) then return false end
    return true
end

local function build()
    local t = {}
    local loot = ns.DungeonLoot
    if type(loot) == "table" then
        for slug, list in pairs(loot) do
            if type(list) == "table" then
                local names, all, bosses, seen = {}, {}, {}, {}
                for i = 1, #list do
                    local s = list[i]
                    if type(s) == "table" and rowOK(s) then
                        local a = nkey(s[1])
                        if a then
                            names[a] = s[1]
                            all[#all + 1] = { a, s[1] }
                        end
                        local b = nkey(s[2])
                        if b then
                            names[b] = s[1]
                            all[#all + 1] = { b, s[1] }
                        end
                        if not seen[s[1]] then
                            seen[s[1]] = true
                            local meta = type(s[3]) == "string" and s[3] or ""
                            bosses[#bosses + 1] = { en = s[1], rare = meta:find("稀有", 1, true) ~= nil }
                        end
                    end
                end
                t[slug] = { names = names, all = all, bosses = bosses }
            end
        end
    end
    index = t
    return t
end

function M.Rebuild()
    index = nil
    return build()
end

local function insideSlug()
    local dg = ns.DungeonDG or (ns.ProfHost and ns.ProfHost.DG)
    if type(dg) ~= "table" or type(dg.HereSlug) ~= "function" then return nil end
    local ok, v = pcall(dg.HereSlug)
    if ok and type(v) == "string" and v ~= "" then return v end
    return nil
end

local function inCombat()
    return type(InCombatLockdown) == "function" and InCombatLockdown() and true or false
end

local function fire(full)
    local mm = ns.MapModule
    if mm and mm.SyncPins then pcall(mm.SyncPins) end
    local mw = ns.MapWindowModule
    if mw then
        if mw.Sync then pcall(mw.Sync) end
        if mw.MiniSync then pcall(mw.MiniSync, true) end
    end
    if full then
        local wm = ns.MapWorldModule
        if wm and wm.Sync then pcall(wm.Sync) end
    end
end

local function refresh()
    fire(not inCombat())
    if inCombat() then
        M.dirty = true
    else
        M.dirty = nil
    end
end

local function killedAt(slug, en)
    if not (slug and en) then return nil end
    local db = DungeonsForeverDB
    local d = type(db) == "table" and db.dungeon
    local s = type(d) == "table" and d[KEY]
    if type(s) ~= "table" then return nil end
    local row = s[slug]
    if type(row) ~= "table" or type(row.k) ~= "table" then return nil end
    local v = row.k[en]
    if v == nil or v == false then return nil end
    if type(v) == "number" then return v end
    return 0
end

function M.Killed(slug, en)
    return killedAt(slug, en) ~= nil
end

local function mark(slug, en)
    local s = store()
    if not s then return false end
    local row = s[slug]
    if type(row) ~= "table" or type(row.k) ~= "table" then
        row = { t = now(), k = {} }
        s[slug] = row
    end
    if row.k[en] ~= nil then return false end
    row.k[en] = now()
    row.t = now()
    return true
end

local function nameOf(slug, name)
    local ix = index or build()
    local row = ix[slug]
    if not row then return nil end
    local k = nkey(name)
    if not k then return nil end
    local en = row.names[k]
    if en then return en end
    if #k < 3 then return nil end
    local all = row.all
    for i = 1, #all do
        local a = all[i][1]
        if #a >= 3 and (a:find(k, 1, true) or k:find(a, 1, true)) then return all[i][2] end
    end
    return nil
end

function M.Name(slug, name)
    if not slug then return nil end
    return nameOf(slug, plain(name))
end

local function slugByName(name)
    local k = nkey(name)
    if not k then return nil end
    local ix = index or build()
    local hitSlug, hitEn
    for slug, row in pairs(ix) do
        local en = row.names[k]
        if en then return slug, en end
    end
    if #k < 3 then return nil end
    for slug, row in pairs(ix) do
        local all = row.all
        for i = 1, #all do
            local a = all[i][1]
            if #a >= 3 and (a:find(k, 1, true) or k:find(a, 1, true)) then
                if hitSlug and hitSlug ~= slug then return nil end
                hitSlug, hitEn = slug, all[i][2]
            end
        end
    end
    return hitSlug, hitEn
end

function M.SlugOf(name)
    return slugByName(plain(name))
end

local function fullClear(slug)
    local ix = index or build()
    local row = ix[slug]
    if not (row and row.bosses) then return false end
    local db = DungeonsForeverDB
    local d = type(db) == "table" and db.dungeon
    local s = type(d) == "table" and d[KEY]
    local e = type(s) == "table" and s[slug]
    local k = type(e) == "table" and e.k
    if type(k) ~= "table" then return false end
    local need = 0
    for i = 1, #row.bosses do
        local b = row.bosses[i]
        if not b.rare then
            need = need + 1
            if k[b.en] == nil then return false end
        end
    end
    return need > 0
end

function M.FullClear(slug)
    return fullClear(slug)
end

local function hit(name)
    name = plain(name)
    if not name then return nil end
    local slug = M.slug
    local en
    if slug then en = nameOf(slug, name) end
    if not en then
        local s2, e2 = slugByName(name)
        if s2 then
            slug, en = s2, e2
            if not M.slug then M.slug = s2 end
        end
    end
    if not (slug and en) then return nil end
    local at = killedAt(slug, en)
    if at and (now() - at) >= REPEAT_WINDOW then
        local s = store()
        if s then s[slug] = nil end
    end
    if mark(slug, en) then
        refresh()
        if not M.quiet then
            print("|cff46bf72DungeonsForever|r bossKill: " .. en)
        end
    end
    return en
end

function M.Hit(name)
    return hit(name)
end

local function started(name)
    name = plain(name)
    if not name then return end
    local slug = M.slug
    local en = slug and nameOf(slug, name) or nil
    if not en then
        local s2, e2 = slugByName(name)
        if s2 then
            slug, en = s2, e2
        end
    end
    if not (slug and en) then return end
    local at = killedAt(slug, en)
    if not at or (now() - at) < REPEAT_WINDOW then return end
    local s = store()
    if s and s[slug] then
        s[slug] = nil
        refresh()
    end
end

function M.Clear(slug)
    local s = store()
    if not s then return end
    if slug then
        s[slug] = nil
    else
        for k in pairs(s) do s[k] = nil end
    end
    refresh()
end

local function clearByText(txt)
    if type(txt) ~= "string" or #txt < 2 then return end
    local zone = txt:gsub("%s*[Hh]as been reset%.?%s*$", ""):gsub("%s*已重置.*$", "")
    zone = zone:gsub("^%s+", ""):gsub("%s+$", "")
    if #zone < 2 then return end
    local s = store()
    if not s then return end
    local list = ns.DungeonData and ns.DungeonData.dungeons
    local low = zone:lower()
    local n = 0
    for slug in pairs(s) do
        local hitOne = false
        if type(list) == "table" then
            for i = 1, #list do
                local d = list[i]
                if d.id == slug then
                    local nm = d.name
                    local en = d.nameEn
                    if type(nm) == "string" and nm ~= ""
                       and (txt:find(nm, 1, true) or nm:find(zone, 1, true)) then
                        hitOne = true
                    elseif type(en) == "string" and #en >= 3
                       and (low:find(en:lower(), 1, true) or en:lower():find(low, 1, true)) then
                        hitOne = true
                    end
                    break
                end
            end
        end
        if hitOne then
            s[slug] = nil
            n = n + 1
        end
    end
    if n > 0 then refresh() end
end

local buf, seq = {}, 0
local seen = { start = 0, enc = 0, kill = 0 }

local function logev(event, ...)
    seq = seq + 1
    local parts = { tostring(seq) .. " " .. event }
    for i = 1, 6 do
        local v = select(i, ...)
        if v == nil then break end
        parts[#parts + 1] = safeStr(v)
    end
    buf[((seq - 1) % LOGN) + 1] = table.concat(parts, " ")
end

M.buf = buf

function M.Dump()
    local s = store()
    local ix = index or build()
    print("|cff46bf72bossKill|r slug=" .. tostring(M.slug) .. " seq=" .. tostring(seq))
    print(string.format("  events: START=%d END=%d KILL=%d",
        seen.start, seen.enc, seen.kill))
    if type(s) ~= "table" then return end
    for slug, row in pairs(s) do
        local n = 0
        local list = {}
        if type(row) == "table" and type(row.k) == "table" then
            for en in pairs(row.k) do
                n = n + 1
                list[#list + 1] = tostring(en)
            end
        end
        table.sort(list)
        print(string.format("  %s t=%s n=%d known=%s %s", slug, tostring(row and row.t),
            n, tostring(ix[slug] and true or false), table.concat(list, ", ")))
    end
end

function M.DumpLog(n)
    n = tonumber(n) or 12
    local out = {}
    for i = 1, LOGN do
        local line = buf[i]
        if type(line) == "string" then out[#out + 1] = line end
    end
    table.sort(out, function(a, b)
        return (tonumber(a:match("^(%d+)")) or 0) < (tonumber(b:match("^(%d+)")) or 0)
    end)
    print("|cff46bf72bossKill|r log " .. #out .. " 条")
    local from = math.max(1, #out - n + 1)
    for i = from, #out do print("  " .. out[i]) end
end

SLASH_DUNGEONSFOREVERBOSSKILL1 = "/dfboss"
SlashCmdList["DUNGEONSFOREVERBOSSKILL"] = function(msg)
    msg = tostring(msg or ""):lower()
    if msg == "clear" then
        M.Clear()
        print("|cff46bf72bossKill|r cleared")
        return
    end
    if msg == "rebuild" then
        M.Rebuild()
        print("|cff46bf72bossKill|r index rebuilt")
        return
    end
    if msg == "log" then
        M.DumpLog(20)
        return
    end
    if msg == "quiet" then
        M.quiet = not M.quiet
        print("|cff46bf72bossKill|r quiet=" .. tostring(M.quiet))
        return
    end
    M.Dump()
end

local function hookReset()
    if M.resetHooked then return end
    if type(hooksecurefunc) ~= "function" or type(ResetInstances) ~= "function" then return end
    M.resetHooked = true
    pcall(hooksecurefunc, "ResetInstances", function()
        M.Clear()
    end)
end

local function zone()
    local slug = insideSlug()
    local was = M.slug
    M.slug = slug
    local s = store()
    if type(s) == "table" then
        local t = now()
        for k, row in pairs(s) do
            local ts = type(row) == "table" and tonumber(row.t) or nil
            if (not ts) or (t - ts > KEEP) then s[k] = nil end
        end
        if was and not slug and s[was] and fullClear(was) then
            s[was] = nil
        end
        if slug and was ~= slug then
            local row = s[slug]
            local ts = type(row) == "table" and tonumber(row.t) or nil
            if ts and (t - ts > RUN_GAP) then s[slug] = nil end
        end
    end
    hookReset()
    refresh()
end

local f = CreateFrame("Frame")
M.frame = f
f:RegisterEvent("PLAYER_ENTERING_WORLD")
f:RegisterEvent("ZONE_CHANGED_NEW_AREA")
f:RegisterEvent("PLAYER_LOGIN")
f:RegisterEvent("ENCOUNTER_END")
f:RegisterEvent("ENCOUNTER_START")
f:RegisterEvent("BOSS_KILL")
f:RegisterEvent("CHAT_MSG_SYSTEM")
f:RegisterEvent("PLAYER_REGEN_ENABLED")

f:SetScript("OnEvent", function(_, event, ...)
    if event == "PLAYER_REGEN_ENABLED" then
        if M.dirty then refresh() end
        return
    end
    if event == "ENCOUNTER_END" then
        seen.enc = seen.enc + 1
        logev(event, ...)
        local _, name, _, _, success = ...
        if success ~= false and success ~= 0 then hit(name) end
        return
    end
    if event == "BOSS_KILL" then
        seen.kill = seen.kill + 1
        logev(event, ...)
        local _, name = ...
        hit(name)
        return
    end
    if event == "ENCOUNTER_START" then
        seen.start = seen.start + 1
        logev(event, ...)
        local _, name = ...
        started(name)
        return
    end
    if event == "CHAT_MSG_SYSTEM" then
        local msg = plain((...))
        if msg then
            local low = msg:lower()
            if msg:find("已重置", 1, true) or low:find("has been reset", 1, true) then
                clearByText(msg)
            end
        end
        return
    end
    if event == "PLAYER_ENTERING_WORLD" or event == "ZONE_CHANGED_NEW_AREA" or event == "PLAYER_LOGIN" then
        zone()
    end
end)

ns.MapModule = ns.MapModule or {}
ns.MapModule.BossKilled = M.Killed
