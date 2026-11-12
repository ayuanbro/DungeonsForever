local ns = _G.DF_NS or {}

local SR = {}
ns.SpellRank = SR

local L = ns.L or setmetatable({}, { __index = function(_, k) return k end })

local MAX_SLOT = 180

local function Say(msg)
    if DEFAULT_CHAT_FRAME then
        DEFAULT_CHAT_FRAME:AddMessage("|cff46bf72DungeonsForever|r " .. msg)
    end
end
SR.Say = Say

local BANK

local function Bank()
    if BANK ~= nil then return BANK end
    local e = Enum and Enum.SpellBookSpellBank
    BANK = (e and e.Player) or 0
    return BANK
end

local function Raw(v)
    if type(issecretvalue) == "function" then
        local ok, s = pcall(issecretvalue, v)
        if ok and s then return nil end
    end
    return v
end

local function InCombat()
    if type(InCombatLockdown) ~= "function" then return false end
    local ok, v = pcall(InCombatLockdown)
    return ok and v or false
end
SR.InCombat = InCombat

local function CursorBusy()
    if type(GetCursorInfo) ~= "function" then return false end
    local ok, kind = pcall(GetCursorInfo)
    return ok and kind ~= nil
end

local function SpellName(id)
    if not id then return nil end
    if C_Spell and C_Spell.GetSpellName then
        local ok, v = pcall(C_Spell.GetSpellName, id)
        if ok and type(v) == "string" and v ~= "" then return v end
    end
    if type(GetSpellInfo) == "function" then
        local ok, v = pcall(GetSpellInfo, id)
        if ok and type(v) == "string" and v ~= "" then return v end
    end
    return nil
end
SR.SpellName = SpellName

local function RankText(id)
    if not id then return nil end
    if C_Spell and C_Spell.GetSpellSubtext then
        local ok, v = pcall(C_Spell.GetSpellSubtext, id)
        if ok and type(v) == "string" and v ~= "" then return v end
    end
    if type(GetSpellSubtext) == "function" then
        local ok, v = pcall(GetSpellSubtext, id)
        if ok and type(v) == "string" and v ~= "" then return v end
    end
    return nil
end
SR.RankText = RankText

local function SpellIcon(id)
    if id then
        if C_Spell and C_Spell.GetSpellTexture then
            local ok, v = pcall(C_Spell.GetSpellTexture, id)
            if ok and v then return v end
        end
        if type(GetSpellTexture) == "function" then
            local ok, v = pcall(GetSpellTexture, id)
            if ok and v then return v end
        end
    end
    return "Interface\\Icons\\INV_Misc_QuestionMark"
end
SR.SpellIcon = SpellIcon

local FAM
local FAM_TRIED

local function BuildFamily()
    if FAM_TRIED then return end
    FAM_TRIED = true
    FAM = {}
    local data = ns.SpellBookData
    if type(data) ~= "table" or type(data.classes) ~= "table" then return end
    local _, cls = UnitClass("player")
    local c = cls and data.classes[cls]
    if type(c) ~= "table" or type(c.tabs) ~= "table" then return end
    for _, tab in ipairs(c.tabs) do
        for _, spell in ipairs(tab.spells or {}) do
            local ranks = spell.ranks
            if type(ranks) == "table" and #ranks > 0 then
                local minId
                for i = 1, #ranks do
                    local id = ranks[i].id
                    if id and (not minId or id < minId) then minId = id end
                end
                local fam = { minId = minId, ranks = ranks, name = spell.name }
                for i = 1, #ranks do
                    local id = ranks[i].id
                    if id and not FAM[id] then
                        FAM[id] = { fam = fam, idx = i }
                    end
                end
            end
        end
    end
end

local function FamilyOf(id)
    BuildFamily()
    return FAM and FAM[id]
end

local function FamilyKey(id, name)
    local e = FamilyOf(id)
    if e and e.fam and e.fam.minId then return e.fam.minId end
    return name or tostring(id)
end
SR.FamilyKey = FamilyKey

local function DB()
    local g = _G.DungeonsForeverSpellDB
    if type(g) ~= "table" then
        g = {}
        _G.DungeonsForeverSpellDB = g
    end
    local r = g.rank
    if type(r) ~= "table" then
        r = {}
        g.rank = r
    end
    if r.on == nil then r.on = true end
    if r.hintLearn == nil then r.hintLearn = true end
    if r.hintLogin == nil then r.hintLogin = true end
    if type(r.whitelist) ~= "table" then r.whitelist = {} end
    if type(r.ignores) ~= "table" then r.ignores = {} end
    return r
end
SR.DB = DB

function SR.Setting(k, v)
    DB()[k] = v
end

function SR.Whitelisted(key)
    local w = DB().whitelist
    return key ~= nil and w[key] ~= nil
end

function SR.AddWhitelist(rows)
    local db = DB()
    local n = 0
    for _, row in ipairs(rows or {}) do
        if row.key ~= nil and db.whitelist[row.key] == nil then
            db.whitelist[row.key] = (type(time) == "function" and time()) or 1
            db.ignores[row.key] = nil
            n = n + 1
        end
    end
    SR.Dirty()
    return n
end

function SR.RemoveWhitelist(keys)
    local db = DB()
    local n = 0
    for _, k in ipairs(keys or {}) do
        if db.whitelist[k] ~= nil then
            db.whitelist[k] = nil
            n = n + 1
        end
    end
    SR.Dirty()
    return n
end

function SR.NoteIgnore(rows)
    local db = DB()
    for _, row in ipairs(rows or {}) do
        if row.key ~= nil and db.whitelist[row.key] == nil then
            db.ignores[row.key] = (tonumber(db.ignores[row.key]) or 0) + 1
        end
    end
end

function SR.IgnoreCount(key)
    if key == nil then return 0 end
    return tonumber(DB().ignores[key]) or 0
end

local function BindFor(slot)
    local bind
    if slot >= 1 and slot <= 12 then
        bind = "ACTIONBUTTON" .. slot
    elseif slot >= 13 and slot <= 24 then
        bind = "MULTIACTIONBAR5BUTTON" .. (slot - 12)
    elseif slot >= 25 and slot <= 36 then
        bind = "MULTIACTIONBAR3BUTTON" .. (slot - 24)
    elseif slot >= 37 and slot <= 48 then
        bind = "MULTIACTIONBAR4BUTTON" .. (slot - 36)
    elseif slot >= 49 and slot <= 60 then
        bind = "MULTIACTIONBAR2BUTTON" .. (slot - 48)
    elseif slot >= 61 and slot <= 72 then
        bind = "MULTIACTIONBAR1BUTTON" .. (slot - 60)
    end
    if not bind or type(GetBindingKey) ~= "function" then return nil end
    local ok, k1 = pcall(GetBindingKey, bind)
    if ok and type(k1) == "string" and k1 ~= "" then
        local s = k1:gsub("ALT%-", "A-"):gsub("CTRL%-", "C-"):gsub("SHIFT%-", "S-")
        return s
    end
    return nil
end
SR.BindFor = BindFor

local function RankNum(id)
    local t = RankText(id)
    if type(t) ~= "string" then return 0 end
    local n = tonumber(t:match("(%d+)"))
    return n or 0
end

local function ScanBook()
    local best = {}
    local bank = Bank()
    if not (C_SpellBook and C_SpellBook.GetNumSpellBookSkillLines) then return best end
    local ok, n = pcall(C_SpellBook.GetNumSpellBookSkillLines)
    if not ok or type(n) ~= "number" or n <= 0 then return best end
    for i = 1, n do
        local okl, line = pcall(C_SpellBook.GetSpellBookSkillLineInfo, i)
        if okl and type(line) == "table" then
            local from = (line.itemIndexOffset or 0) + 1
            local to = from + (line.numSpellBookItems or 0) - 1
            for slot = from, to do
                local oki, info = pcall(C_SpellBook.GetSpellBookItemInfo, slot, bank)
                if oki and type(info) == "table" and info.spellID then
                    local low = false
                    if C_SpellBook.IsSpellBookItemLowRank then
                        local okr, r = pcall(C_SpellBook.IsSpellBookItemLowRank, slot, bank)
                        low = (okr and r == true)
                    end
                    local isSpell = true
                    local t = info.itemType
                    if t ~= nil and Enum and Enum.SpellBookItemType and Enum.SpellBookItemType.Spell then
                        isSpell = (t == Enum.SpellBookItemType.Spell)
                    end
                    if isSpell and not low and not info.isOffSpec then
                        local nm = info.name or SpellName(info.spellID)
                        if nm then
                            local cur = best[nm]
                            if cur == nil then
                                best[nm] = info.spellID
                            elseif RankNum(info.spellID) > RankNum(cur) then
                                best[nm] = info.spellID
                            end
                        end
                    end
                end
            end
        end
    end
    return best
end

local function InStance(id, nm)
    if type(GetNumShapeshiftForms) ~= "function" then return false end
    local ok, n = pcall(GetNumShapeshiftForms)
    if not ok or type(n) ~= "number" then return false end
    for i = 1, n do
        local oki, _, _, _, sid = pcall(GetShapeshiftFormInfo, i)
        if oki and sid then
            if id and sid == id then return true end
            if nm and SpellName(sid) == nm then return true end
        end
    end
    return false
end

local function InBar(id, nm, onBar)
    if nm and onBar[nm] then return true end
    if not id then return false end
    if C_ActionBar and C_ActionBar.FindSpellActionButtons then
        local ok, r = pcall(C_ActionBar.FindSpellActionButtons, id)
        if ok and r then return true end
    end
    return InStance(id, nm)
end

local function IsAutoAttack(id)
    if not id then return false end
    if C_Spell and C_Spell.IsAutoAttackSpell then
        local ok, v = pcall(C_Spell.IsAutoAttackSpell, id)
        if ok then return v == true end
    end
    return false
end

local function IsPassive(id)
    if not id then return false end
    if C_Spell and C_Spell.IsSpellPassive then
        local ok, v = pcall(C_Spell.IsSpellPassive, id)
        if ok then return v == true end
    end
    if type(IsPassiveSpell) == "function" then
        local ok, v = pcall(IsPassiveSpell, id)
        if ok then return v == true end
    end
    return false
end

local cache
local dirty = true
local EMPTY = { rows = {}, slots = 0 }

function SR.Dirty()
    dirty = true
    if SR.OnDirty then SR.OnDirty() end
end

function SR.IsDirty()
    return dirty
end

function SR.Clear()
    cache = nil
    dirty = true
end

function SR.Scan()
    if cache and not dirty then return cache end
    if InCombat() then return cache or EMPTY end
    dirty = false
    local out = { rows = {}, slots = 0 }
    if not (C_SpellBook and C_SpellBook.GetSpellBookItemInfo) then
        cache = out
        return out
    end
    local best = ScanBook()
    if not next(best) then
        dirty = true
        return cache or out
    end
    local groups, order, onBar = {}, {}, {}
    for slot = 1, MAX_SLOT do
        local ok, kind, id = pcall(GetActionInfo, slot)
        if ok and kind == "spell" then
            id = Raw(id)
            if id then
                local nm = SpellName(id)
                if nm then onBar[nm] = true end
                local target = nm and best[nm]
                if nm and target and target ~= id then
                    local g = groups[nm]
                    if not g then
                        g = { name = nm, bestId = target, slots = {}, ids = {}, seen = {} }
                        groups[nm] = g
                        order[#order + 1] = g
                    end
                    if not g.seen[slot] then
                        g.seen[slot] = true
                        g.slots[#g.slots + 1] = slot
                    end
                    g.ids[id] = true
                end
            end
        end
    end
    for nm, target in pairs(best) do
        if not groups[nm] and not InBar(target, nm, onBar)
            and not IsPassive(target) and not IsAutoAttack(target) then
            local g = { name = nm, bestId = target, slots = {}, ids = {}, seen = {}, noBar = true }
            groups[nm] = g
            order[#order + 1] = g
        end
    end
    for _, g in ipairs(order) do
        local from = {}
        for id in pairs(g.ids) do
            local t = RankText(id)
            if t then from[#from + 1] = t end
        end
        table.sort(from)
        local key = FamilyKey(g.bestId, g.name)
        local row = {
            key = key,
            name = g.name,
            bestId = g.bestId,
            slots = g.slots,
            from = #from > 0 and table.concat(from, " / ") or nil,
            to = RankText(g.bestId),
            icon = SpellIcon(g.bestId),
            white = SR.Whitelisted(key),
            noBar = g.noBar and true or nil,
        }
        table.sort(row.slots)
        if row.noBar or row.to ~= nil or row.from ~= nil then
            out.rows[#out.rows + 1] = row
            out.slots = out.slots + #row.slots
        end
    end
    local function slotKey(r) return r.slots[1] or 9999 end
    table.sort(out.rows, function(a, b)
        local ka, kb = slotKey(a), slotKey(b)
        if ka ~= kb then return ka < kb end
        return (a.name or "") < (b.name or "")
    end)
        cache = out
    return out
end

function SR.Diagnose()
    if InCombat() then return { rows = {}, spells = 0 } end
    local best = ScanBook()
    local rows, index = {}, {}
    local spells = 0
    for slot = 1, MAX_SLOT do
        local ok, kind, id = pcall(GetActionInfo, slot)
        if ok and kind == "spell" then
            id = Raw(id)
            if id then
                spells = spells + 1
                local nm = SpellName(id)
                local key = nm or ("#" .. tostring(id))
                local r = index[key]
                if not r then
                    r = { name = nm, id = id, slots = {}, bestId = nm and best[nm] or nil }
                    index[key] = r
                    rows[#rows + 1] = r
                end
                r.slots[#r.slots + 1] = slot
            end
        end
    end
    for _, r in ipairs(rows) do
        if not r.name then
            r.state = "noname"
        elseif not r.bestId then
            r.state = "bookless"
        elseif r.bestId == r.id then
            r.state = "top"
        else
            r.state = "old"
        end
        r.cur = RankText(r.id)
        r.best = r.bestId and RankText(r.bestId) or nil
    end
    return { rows = rows, spells = spells }
end

local STATE_TAG = { old = "过期", top = "已最高", bookless = "书里无同名", noname = "取不到名字" }

function SR.ReportDiagnose()
    local d = SR.Diagnose()
    local c = { old = 0, top = 0, bookless = 0, noname = 0 }
    for _, r in ipairs(d.rows) do c[r.state] = (c[r.state] or 0) + 1 end
    Say(string.format("动作条检查：%d 个法术槽位 · %d 个法术", d.spells, #d.rows))
    Say(string.format("  过期 %d · 已最高 %d · 书里无同名 %d · 取不到名字 %d",
        c.old, c.top, c.bookless, c.noname))
    local n = 0
    for _, r in ipairs(d.rows) do
        if r.state ~= "top" then
            n = n + 1
            if n <= 12 then
                local slotText = table.concat(r.slots, "、")
                local from = r.cur or "-"
                local to = r.best or "-"
                if r.state == "old" then
                    Say(string.format("  [过期] %s · 槽位 %s · %s → %s", r.name, slotText, from, to))
                else
                    Say(string.format("  [%s] %s · 槽位 %s · 当前 %s",
                        STATE_TAG[r.state] or r.state, r.name or "?", slotText, from))
                end
            end
        end
    end
    if n > 12 then Say(string.format("  …另有 %d 个", n - 12)) end
end

function SR.Pending()
    local v = 0
    for _, row in ipairs(SR.Scan().rows) do
        if not row.white and not row.noBar then v = v + 1 end
    end
    return v
end

function SR.PickupToBar(id)
    if not id then return false end
    if InCombat() then
        Say(L["战斗中不能改动作条"])
        return false
    end
    local ok = false
    if C_Spell and C_Spell.PickupSpell then ok = pcall(C_Spell.PickupSpell, id) end
    if not ok then return false end
    Say(L["把法术拖到动作条的空槽上"])
    return true
end

function SR.RowsForAll()
    local out = {}
    for _, row in ipairs(SR.Scan().rows) do
        if not row.white and not row.noBar then out[#out + 1] = row end
    end
    return out
end

local function CursorSpell()
    if type(CursorHasSpell) ~= "function" then return true end
    local ok, v = pcall(CursorHasSpell)
    return ok and v == true
end

local function Pickup(id)
    if C_SpellBook and C_SpellBook.FindSpellBookSlotForSpell and C_SpellBook.PickupSpellBookItem then
        local ok, bslot, bbank = pcall(C_SpellBook.FindSpellBookSlotForSpell, id)
        if ok and bslot then
            pcall(C_SpellBook.PickupSpellBookItem, bslot, bbank or Bank())
            if CursorSpell() then return true end
        end
    end
    if C_Spell and type(C_Spell.PickupSpell) == "function" then
        pcall(C_Spell.PickupSpell, id)
        if CursorSpell() then return true end
    end
    return false
end

local function Place(row, slot)
    if InCombat() then return false end
    if not row.bestId then return false end
    if not Pickup(row.bestId) then
        if type(ClearCursor) == "function" then pcall(ClearCursor) end
        return false
    end
    local okp = pcall(PlaceAction, slot)
    if type(ClearCursor) == "function" then pcall(ClearCursor) end
    if not okp then return false end
    local okk, kind, id = pcall(GetActionInfo, slot)
    return (okk and kind == "spell" and Raw(id) == row.bestId)
end

local function Run(rows, onDone)
    local done, bad = 0, {}
    for _, row in ipairs(rows or {}) do
        if #(row.slots or {}) > 0 then
            local hit = 0
            for _, slot in ipairs(row.slots) do
                if Place(row, slot) then hit = hit + 1 end
            end
            if hit == #row.slots then
                done = done + 1
                DB().ignores[row.key] = nil
            else
                bad[#bad + 1] = row
            end
        end
    end
    SR.Dirty()
    if done > 0 then
        Say(string.format(L["已升级 %d 项动作条法术"], done))
    end
    if #bad > 0 then
        local names = {}
        for i, row in ipairs(bad) do
            if i <= 5 then names[#names + 1] = row.name or "?" end
        end
        local tail = ""
        if #names > 0 then tail = "：" .. table.concat(names, "、") end
        Say(string.format(L["%d 项未能升级，请手动拖动"], #bad) .. tail)
    end
    if onDone then onDone(done, bad) end
    return done, bad
end

local queued
local queueFrame

local function Flush()
    if not queued then return end
    if InCombat() or CursorBusy() then return end
    local rows = queued
    queued = nil
    if queueFrame then
        queueFrame:UnregisterEvent("PLAYER_REGEN_ENABLED")
        queueFrame:UnregisterEvent("CURSOR_CHANGED")
    end
    Run(rows, function(done)
        if done > 0 and SR.OnChanged then SR.OnChanged() end
        if SR.OnFlushed then SR.OnFlushed(done) end
    end)
end
SR.Flush = Flush

function SR.Apply(rows, onDone)
    if not rows or #rows == 0 then return 0 end
    if InCombat() or CursorBusy() then
        queued = rows
        if not queueFrame then
            queueFrame = CreateFrame("Frame")
            queueFrame:SetScript("OnEvent", Flush)
        end
        queueFrame:RegisterEvent("PLAYER_REGEN_ENABLED")
        queueFrame:RegisterEvent("CURSOR_CHANGED")
        if SR.OnQueued then SR.OnQueued(#rows) end
        return -1
    end
    local done, bad = Run(rows, onDone)
    if SR.OnChanged then SR.OnChanged() end
    return done, bad
end

local booted
local bootFrame

local function FeatureOn()
    if not DB().on then return false end
    if ns.SpellEnhOn and not ns.SpellEnhOn() then return false end
    return true
end
SR.FeatureOn = FeatureOn

function SR.Stop()
    if not booted then return end
    booted = false
    if bootFrame then
        bootFrame:UnregisterAllEvents()
        bootFrame:SetScript("OnEvent", nil)
        bootFrame:Hide()
        bootFrame = nil
    end
    if queueFrame then
        queueFrame:UnregisterAllEvents()
        queueFrame:SetScript("OnEvent", nil)
        queueFrame:Hide()
        queueFrame = nil
    end
    queued = nil
    SR.Clear()
end

function SR.Sync()
    if FeatureOn() then
        SR.Boot()
    else
        SR.Stop()
    end
    return booted
end

function SR.Boot()
    if booted then return end
    if not FeatureOn() then return end
    booted = true
    if not (C_SpellBook and C_SpellBook.GetSpellBookItemInfo) then return end
    local f = CreateFrame("Frame")
    bootFrame = f
    local learned, learnedAt
    local loginDone
    local barPending
    local lastKeys
    f:RegisterEvent("PLAYER_LOGIN")
    f:RegisterEvent("SPELLS_CHANGED")
    f:RegisterEvent("LEARNED_SPELL_IN_SKILL_LINE")
    f:RegisterEvent("ACTIONBAR_SLOT_CHANGED")
    f:RegisterEvent("ACTIONBAR_PAGE_CHANGED")
    f:RegisterEvent("UPDATE_BINDINGS")
    f:RegisterEvent("PLAYER_REGEN_ENABLED")
    local function FlushLearned()
        if InCombat() then
            if C_Timer and C_Timer.After then
                learnedAt = true
                C_Timer.After(1, FlushLearned)
            end
            return
        end
        learnedAt = nil
        local names = learned
        learned = nil
        if not names then return end
        SR.Dirty()
        local rows, seen = {}, {}
        for _, row in ipairs(SR.Scan().rows) do
            if not row.white and not row.noBar and names[row.name] and not seen[row.name] then
                seen[row.name] = true
                rows[#rows + 1] = row
            end
        end
        if #rows > 0 and DB().hintLearn and SR.OnLearn and not InCombat() then
            SR.OnLearn(rows)
        end
        if SR.OnChanged then SR.OnChanged() end
    end
    f:SetScript("OnEvent", function(_, event, arg1, arg2, arg3)
        if event == "PLAYER_REGEN_ENABLED" then
            if not (dirty or barPending or learned) then return end
            barPending = false
            if learned then
                FlushLearned()
                return
            end
            SR.Dirty()
            if SR.OnChanged then SR.OnChanged() end
        elseif event == "SPELLS_CHANGED" then
            SR.Dirty()
            if C_Timer and C_Timer.After then
                C_Timer.After(0.6, function()
                    if InCombat() then return end
                    local keys, fresh, seen = {}, {}, {}
                    for _, row in ipairs(SR.Scan().rows) do
                        local k = tostring(row.key)
                        keys[#keys + 1] = k
                        if lastKeys and not lastKeys[k] and not row.white and not row.noBar then fresh[#fresh + 1] = row end
                    end
                    table.sort(keys)
                    local now = {}
                    for i = 1, #keys do now[keys[i]] = true end
                    if lastKeys and #fresh > 0 and DB().hintLearn and SR.OnLearn and not InCombat() then
                        SR.OnLearn(fresh)
                    end
                    lastKeys = now
                    if SR.OnChanged then SR.OnChanged() end
                end)
            end
        elseif event == "LEARNED_SPELL_IN_SKILL_LINE" then
            local id = Raw(arg1)
            if not id or arg3 then return end
            local nm = SpellName(id)
            if not nm then return end
            learned = learned or {}
            learned[nm] = true
            if not learnedAt and C_Timer and C_Timer.After then
                learnedAt = true
                C_Timer.After(0.8, FlushLearned)
            end
        elseif event == "ACTIONBAR_SLOT_CHANGED" or event == "ACTIONBAR_PAGE_CHANGED"
            or event == "UPDATE_BINDINGS" then
            SR.Dirty()
            if barPending then return end
            barPending = true
            if C_Timer and C_Timer.After then
                C_Timer.After(0.2, function()
                    barPending = false
                    if InCombat() then return end
                    SR.Dirty()
                    if SR.OnChanged then SR.OnChanged() end
                end)
            else
                barPending = false
                if not InCombat() and SR.OnChanged then SR.OnChanged() end
            end
        elseif event == "PLAYER_LOGIN" then
            if loginDone then return end
            loginDone = true
            if C_Timer and C_Timer.After then
                C_Timer.After(3, function()
                    if InCombat() then return end
                    SR.Dirty()
                    local keys = {}
                    for _, row in ipairs(SR.Scan().rows) do keys[tostring(row.key)] = true end
                    lastKeys = keys
                    if DB().hintLogin and SR.OnLogin then
                        local rows = SR.RowsForAll()
                        if #rows > 0 then SR.OnLogin(rows) end
                    end
                    if SR.OnChanged then SR.OnChanged() end
                end)
            end
        end
    end)
end

SR.L = L
