local ns = _G.DF_NS or {}

if not ns.IsTitan then return end

local ST = {}
ns.SpellTraining = ST

local knowCache = {}
local cacheDirty = true
local questIndex

local function SpellName(id)
    if C_Spell and C_Spell.GetSpellName then
        local ok, name = pcall(C_Spell.GetSpellName, id)
        if ok and name then return name end
    end
    if GetSpellInfo then
        local ok, name = pcall(GetSpellInfo, id)
        if ok and name then return name end
    end
    return ""
end

local function SpellTexture(id)
    if C_Spell and C_Spell.GetSpellTexture then
        local ok, tex = pcall(C_Spell.GetSpellTexture, id)
        if ok and tex then return tex end
    end
    if GetSpellTexture then
        local ok, tex = pcall(GetSpellTexture, id)
        if ok and tex then return tex end
    end
    return "Interface\\Icons\\INV_Misc_QuestionMark"
end

local function MySide()
    local f = UnitFactionGroup and UnitFactionGroup("player")
    if f == "Alliance" then return "A" end
    if f == "Horde" then return "H" end
    return nil
end

function ST.RaceShown(races)
    if not races or races == "" then return true end
    local tbl = ns.SpellExtra and ns.SpellExtra.raceSide
    if not tbl then return true end
    local myName = UnitRace("player")
    local n, mine = 0, false
    for token in string.gmatch(races, "[^/]+") do
        n = n + 1
        if token == myName then mine = true end
        if not tbl[token] then return true end
    end
    if n == 0 or mine then return true end
    if n == 1 then return false end
    local side = MySide()
    if not side then return true end
    for token in string.gmatch(races, "[^/]+") do
        if tbl[token] ~= side then return false end
    end
    return true
end

function ST.Knows(id)
    if not id then return false end
    if not cacheDirty then
        local c = knowCache[id]
        if c ~= nil then return c end
    end
    local v = false
    local bank = Enum and Enum.SpellBookSpellBank and Enum.SpellBookSpellBank.Player or "Player"
    if C_SpellBook and C_SpellBook.IsSpellKnownOrInSpellBook then
        local ok, r = pcall(C_SpellBook.IsSpellKnownOrInSpellBook, id, bank)
        if ok then v = (r == true) end
    elseif C_SpellBook and C_SpellBook.IsSpellInSpellBook then
        local ok, r = pcall(C_SpellBook.IsSpellInSpellBook, id, bank, false)
        if ok and r == true then
            v = true
        else
            ok, r = pcall(C_SpellBook.IsSpellKnown, id, bank)
            if ok then v = (r == true) end
        end
    elseif C_SpellBook and C_SpellBook.IsSpellKnown then
        local ok, r = pcall(C_SpellBook.IsSpellKnown, id)
        if ok then v = (r == true) end
    elseif IsSpellKnown then
        local ok, r = pcall(IsSpellKnown, id)
        if ok then v = (r == true) end
    end
    if cacheDirty then
        for k in pairs(knowCache) do knowCache[k] = nil end
        cacheDirty = false
    end
    knowCache[id] = v
    return v
end

function ST.Invalidate()
    cacheDirty = true
    questIndex = nil
end

local function ChainKeyFor(cls, qid)
    local chains = ns.ClassQuestChains and ns.ClassQuestChains[cls]
    if not chains then return nil end
    local function has(t)
        for _, v in ipairs(t) do
            if type(v) == "table" then
                if has(v) then return true end
            elseif v == qid then
                return true
            end
        end
        return false
    end
    for _, c in ipairs(chains) do
        if c.steps and has(c.steps) then return c.key end
    end
    return nil
end

local function BuildQuestIndex()
    if questIndex then return questIndex end
    local idx = {}
    questIndex = idx
    if not ns.EnsureClassQuestInfo then
        if C_AddOns and C_AddOns.EnableAddOn then pcall(C_AddOns.EnableAddOn, "DungeonsForeverClass") end
        if C_AddOns and C_AddOns.LoadAddOn then
            pcall(C_AddOns.LoadAddOn, "DungeonsForeverClass")
        elseif type(LoadAddOn) == "function" then
            pcall(LoadAddOn, "DungeonsForeverClass")
        end
    end
    local info = ns.EnsureClassQuestInfo and ns.EnsureClassQuestInfo()
    if not info then return idx end
    local cls = select(2, UnitClass("player"))
    local _, _, myId = UnitRace("player")
    local side = MySide()

    local function rate(q)
        local s = 0
        if type(q.races) == "table" and #q.races > 0 then
            local hit
            for _, rid in ipairs(q.races) do
                if rid == myId then hit = true break end
            end
            if not hit then return -1 end
            s = s + 4
        end
        if q.f and side then
            if (q.f == "A" and side == "A") or (q.f == "H" and side == "H") then
                s = s + 2
            else
                return -1
            end
        end
        return s
    end

    local function put(sid, qid, q, s)
        local cur = idx[sid]
        if cur and cur.score >= s then return end
        local npc = type(q.s) == "table" and q.s[1] or nil
        idx[sid] = {
            score = s,
            qid = qid,
            name = q.cn,
            lv = q.r or q.l,
            npc = npc and npc[2] or nil,
            zone = npc and npc[3] or nil,
            x = npc and npc[4] or nil,
            y = npc and npc[5] or nil,
            uiMapId = npc and npc[6] or nil,
            key = ChainKeyFor(cls, qid),
        }
    end

    for qid, q in pairs(info) do
        if type(q) == "table" and type(q.spells) == "table" then
            local s = rate(q)
            if s >= 0 then
                for _, sid in ipairs(q.spells) do put(sid, qid, q, s) end
            end
        end
    end

    local extra = ns.SpellExtra and ns.SpellExtra.quest
    if extra then
        for sid, qids in pairs(extra) do
            for _, qid in ipairs(qids) do
                local q = info[qid]
                if type(q) == "table" then
                    local s = rate(q)
                    if s >= 0 then put(sid, qid, q, s + 8) end
                end
            end
        end
    end

    return idx
end

function ST.Rows()
    local data = ns.SpellBookData
    if not (data and data.classes) or not UnitClass then return nil end
    local clsKey = select(2, UnitClass("player"))
    local cls = data.classes[clsKey]
    if not cls then return nil end
    local lv = (UnitLevel and UnitLevel("player")) or 60
    if lv < 1 or lv > 60 then lv = 60 end
    local extra = ns.SpellExtra
    local fix = extra and extra.fix and extra.fix[clsKey]
    local hide = extra and extra.hide and extra.hide[clsKey]
    local qidx = BuildQuestIndex()

    local groups = { available = {}, next = {}, notlevel = {}, quest = {}, known = {}, talent = {} }
    for _, tab in ipairs(cls.tabs or {}) do
        for _, sp in ipairs(tab.spells or {}) do
            if not (hide and hide[sp.id]) and ST.RaceShown(sp.races) then
                local baseLv = sp.learnLv
                if fix and fix[sp.id] then baseLv = fix[sp.id] end
                local row = {
                    name = sp.name, icon = sp.icon,
                    tab = tab.name, learn = baseLv, base = sp.id,
                }
                local nr = sp.ranks and #sp.ranks or 0
                local knownAny = false
                if nr > 0 then
                    for i = 1, nr do
                        if ST.Knows(sp.ranks[i].id) then knownAny = true break end
                    end
                else
                    knownAny = ST.Knows(sp.id)
                end
                if sp.isTalent and not knownAny then
                    row.id = sp.id
                    groups.talent[#groups.talent + 1] = row
                else
                    local curRank = nil
                    if nr > 0 then
                        for i = nr, 1, -1 do
                            if ST.Knows(sp.ranks[i].id) then
                                curRank = i
                                break
                            end
                        end
                    elseif ST.Knows(sp.id) then
                        curRank = 1
                    end
                    local isFull = (nr > 0 and curRank == nr) or (nr == 0 and curRank ~= nil)
                    if isFull then
                        row.id = nr > 0 and sp.ranks[nr].id or sp.id
                        row.rank = nil
                        row.learn = nil
                        groups.known[#groups.known + 1] = row
                    else
                        local r = nr > 0 and sp.ranks[(curRank or 0) + 1] or nil
                        local l = (r and (r.learn or baseLv)) or baseLv or 60
                        row.rank = r and ((curRank or 0) + 1) or nil
                        row.learn = l
                        row.id = (r and r.id) or sp.id
                        if r and curRank then row.knownId = sp.ranks[curRank].id end
                        local q = qidx[row.id]
                        if q then
                            row.quest = q
                            groups.quest[#groups.quest + 1] = row
                        elseif l <= lv then
                            groups.available[#groups.available + 1] = row
                        elseif l <= lv + 2 then
                            groups.next[#groups.next + 1] = row
                        else
                            groups.notlevel[#groups.notlevel + 1] = row
                        end
                    end
                end
            end
        end
    end

    local pv = extra and extra.passive and extra.passive[clsKey]
    if pv then
        for _, p in ipairs(pv) do
            local id, need = p[1], p[2]
            local row = { id = id, name = SpellName(id), icon = SpellTexture(id), learn = need, passive = true }
            if ST.Knows(id) then
                row.learn = nil
                groups.known[#groups.known + 1] = row
            elseif qidx[id] then
                row.quest = qidx[id]
                groups.quest[#groups.quest + 1] = row
            elseif need <= lv then
                groups.available[#groups.available + 1] = row
            elseif need <= lv + 2 then
                groups.next[#groups.next + 1] = row
            else
                groups.notlevel[#groups.notlevel + 1] = row
            end
        end
    end

    for _, g in pairs(groups) do
        table.sort(g, function(a, b)
            local la, lb = a.learn or 999, b.learn or 999
            if la ~= lb then return la < lb end
            return (a.name or "") < (b.name or "")
        end)
    end
    return groups, lv
end

local ev = CreateFrame("Frame")
for _, name in ipairs({
    "PLAYER_ENTERING_WORLD",
    "PLAYER_LEVEL_UP",
    "LEARNED_SPELL_IN_SKILL_LINE",
    "SKILL_LINES_CHANGED",
}) do
    pcall(ev.RegisterEvent, ev, name)
end
ev:SetScript("OnEvent", function()
    ST.Invalidate()
    if ST.OnDirty then ST.OnDirty() end
end)
