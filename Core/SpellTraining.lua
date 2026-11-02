local _, ns = ...

if not ns.IsTitan then return end

local ST = {}
ns.SpellTraining = ST

local knowCache = {}
local cacheDirty = true

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
end

function ST.Rows()
    local data = ns.SpellBookData
    if not (data and data.classes) or not UnitClass then return nil end
    local cls = data.classes[select(2, UnitClass("player"))]
    if not cls then return nil end
    local lv = (UnitLevel and UnitLevel("player")) or 60
    if lv < 1 or lv > 60 then lv = 60 end

    local groups = { available = {}, next = {}, notlevel = {}, known = {}, talent = {} }
    for _, tab in ipairs(cls.tabs or {}) do
        for _, sp in ipairs(tab.spells or {}) do
            local row = {
                name = sp.name, nameEn = sp.nameEn, icon = sp.icon,
                tab = tab.name, learn = sp.learnLv,
            }
            if sp.isTalent then
                row.id = sp.id
                groups.talent[#groups.talent + 1] = row
            else
                local nr = sp.ranks and #sp.ranks or 0
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
                    local l = (r and (r.learn or sp.learnLv)) or sp.learnLv or 60
                    row.rank = r and ((curRank or 0) + 1) or nil
                    row.learn = l
                    row.id = (r and r.id) or sp.id
                    if l <= lv then
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
