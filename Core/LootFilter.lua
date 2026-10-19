local _, ns = ...

if not ns.IsTitan then return end

local L = ns.L
local D = ns.LootFilterData
local strfind = string.find

local LF = {}
ns.LootFilter = LF

LF.VER = 3
LF.ALPHA_DIM = 0.4
LF.ALPHA_FULL = 1
LF.MAX_SCHEMES = 6
LF.DIMENSIONS = { "Weapon", "Armor", "ShuXing", "Class", "BnetAccount", "Tank" }

LF.tipCache = {}
LF.resCache = {}
LF.attrCache = {}

local function copyInto(dst, src)
    if type(dst) ~= "table" then return end
    for k, v in pairs(src or {}) do dst[k] = v end
end

function LF.ClassName(classFile)
    if not classFile then return nil end
    local names = _G["LOCALIZED_CLASS_NAMES_MALE"]
    if type(names) == "table" and type(names[classFile]) == "string" then return names[classFile] end
    local n = _G[classFile]
    if type(n) == "string" and n ~= "" then return n end
    return classFile
end

function LF.PlayerClass()
    if type(UnitClass) ~= "function" then return nil, nil end
    local locName, classFile = UnitClass("player")
    if not classFile then return nil, nil end
    return classFile, (LF.ClassName(classFile) or locName)
end

local function HasAny(text, list)
    if type(text) ~= "string" or text == "" or type(list) ~= "table" then return false end
    for i = 1, #list do
        local pat = list[i]
        if type(pat) == "string" and pat ~= "" and strfind(text, pat, 1, true) then return true end
    end
    return false
end

local function HasNothave(name, text)
    local list = D.Nothave[name]
    return HasAny(text, list)
end

function LF.EnsureScanTip()
    if LF.scanTip then return LF.scanTip end
    if LF.__scanTried then return nil end
    LF.__scanTried = true
    local ok, tip = pcall(CreateFrame, "GameTooltip", "TFItemScanTip", UIParent, "GameTooltipTemplate")
    if ok and tip then
        LF.scanTip = tip
        pcall(tip.SetAlpha, tip, 0)
        if tip.SetOwner then pcall(tip.SetOwner, tip, UIParent, "ANCHOR_NONE") end
    end
    return LF.scanTip
end

local function IsExcludedLine(t)
    for i = 1, #D.ExcludeLine do
        local pat = D.ExcludeLine[i]
        if type(pat) == "string" and pat ~= "" and strfind(t, pat, 1, true) then return true end
    end
    return false
end

function LF.ScanTip(itemID)
    if not itemID then return "" end
    local cached = LF.tipCache[itemID]
    if cached ~= nil then return cached end

    local DGM = ns.DungeonModule
    if not (DGM and DGM.ItemInfo and DGM.ItemInfo(itemID)) then return "" end

    if (LF.__scanDepth or 0) > 0 then return "" end

    local tip = LF.EnsureScanTip()
    if not tip then return "" end

    LF.__scanDepth = (LF.__scanDepth or 0) + 1
    local okScan, res = pcall(function()
        if tip.SetOwner and not pcall(tip.SetOwner, tip, UIParent, "ANCHOR_NONE") then return nil end
        local set = false
        if tip.SetHyperlink then set = pcall(tip.SetHyperlink, tip, "item:" .. tostring(itemID)) end
        if not set then return nil end

        pcall(tip.Show, tip)
        local n = (tip.NumLines and tip:NumLines()) or 0
        if type(n) ~= "number" or n <= 0 then return "" end

        local parts = {}
        for i = 2, n do
            local fs = _G["TFItemScanTipTextLeft" .. i]
            if fs and fs.GetText then
                local t = fs:GetText()
                if type(t) == "string" and t ~= "" and not IsExcludedLine(t) then
                    parts[#parts + 1] = t
                end
            end
        end
        return table.concat(parts, "|")
    end)
    pcall(tip.Hide, tip)
    LF.__scanDepth = LF.__scanDepth - 1

    if not okScan or res == nil then return "" end
    LF.tipCache[itemID] = res
    return res
end

function LF.Invalidate(itemID)
    if not itemID then return end
    LF.tipCache[itemID] = nil
    LF.resCache[itemID] = nil
    LF.attrCache[itemID] = nil
end

function LF.ClearResults()
    LF.resCache = {}
    LF.attrCache = {}
end

function LF.ConvertPreset(p, classFile, idx)
    local s = {
        Name = p.name or L["未命名方案"],
        Icon = (type(p.icon) == "string" and p.icon ~= "") and p.icon or D.DEFAULT_ICON,
        PresetIdx = idx or 1,
        Weapon = {}, Armor = {}, ShuXing = {},
        Class = { [D.FLAG_CLASS] = 1 },
        BnetAccount = { [D.FLAG_BNET] = 1 },
        Tank = {},
    }
    for _, nm in ipairs(p.useWeapon or {}) do
        local sid = D.WeaponIdByName[nm]
        if sid ~= nil then s.Weapon[tostring(sid)] = 1 end
    end
    for _, nm in ipairs(p.useArmor or {}) do
        local sid = D.ArmorIdByName[nm]
        if sid ~= nil then s.Armor[tostring(sid)] = 1 end
    end
    for _, nm in ipairs(p.useShuXing or {}) do s.ShuXing[nm] = 1 end
    for _, nm in ipairs(p.Tank or {}) do s.Tank[nm] = 1 end
    return s
end

function LF.BuildFallbackPresets(classFile)
    local usable = classFile and D.ClassUsable[classFile]
    local display = (classFile and LF.ClassName(classFile)) or L["本职业"]
    local useW, useA = {}, {}
    for _, nm in ipairs((usable and usable.weapon) or {}) do useW[#useW + 1] = nm end
    for _, nm in ipairs((usable and usable.armor) or {}) do useA[#useA + 1] = nm end
    return {
        { icon = D.DEFAULT_ICON, name = display .. L["-通用"],
          useWeapon = useW, useArmor = useA,
          useShuXing = {}, Tank = {} },
    }
end

function LF.LoadPresets(classFile)
    local presets = classFile and D.Presets[classFile]
    if not presets or #presets == 0 then presets = LF.BuildFallbackPresets(classFile) end
    local list = {}
    for i = 1, #presets do list[i] = LF.ConvertPreset(presets[i], classFile, i) end
    return list
end

function LF.ResolvePresetIndex(scheme, list)
    local n = #(list or {})
    if n == 0 then return 1 end
    if not scheme then return 1 end
    local nm = scheme.Name
    if type(nm) == "string" and nm ~= "" then
        for i = 1, n do
            if list[i].Name == nm then return i end
        end
    end
    local want = tonumber(scheme.PresetIdx)
    if want and want >= 1 and want <= n then return want end
    local hit, cnt = 0, 0
    for i = 1, n do
        if list[i].Icon == scheme.Icon then cnt = cnt + 1; hit = i end
    end
    if cnt == 1 then return hit end
    return 1
end

function LF.ApplyPreset(scheme, classFile, idx)
    if not scheme then return end
    local list = LF.LoadPresets(classFile)
    if #list == 0 then return end
    local want = idx or LF.ResolvePresetIndex(scheme, list)
    local src = list[want] or list[1]

    for _, dim in ipairs(LF.DIMENSIONS) do
        if type(scheme[dim]) ~= "table" then scheme[dim] = {} end
        local t = scheme[dim]
        for k in pairs(t) do t[k] = nil end
    end
    copyInto(scheme.Weapon, src.Weapon)
    copyInto(scheme.Armor, src.Armor)
    copyInto(scheme.ShuXing, src.ShuXing)
    copyInto(scheme.Tank, src.Tank)
    scheme.Class[D.FLAG_CLASS] = 1
    scheme.BnetAccount[D.FLAG_BNET] = 1
    scheme.PresetIdx = want
    if idx then
        if src.Name then scheme.Name = src.Name end
        if src.Icon then scheme.Icon = src.Icon end
    end
    LF.ClearResults()
end

function LF.PopulateFirstTime(c)
    local classFile = LF.PlayerClass()
    local list = LF.LoadPresets(classFile)
    for i = 1, math.min(#list, LF.MAX_SCHEMES) do c[i] = list[i] end
    c.chooseID = nil
end

function LF.BackfillPresetIdx(c)
    local missing = false
    for i = 1, #c do
        local s = c[i]
        if type(s) == "table" and type(s.PresetIdx) ~= "number" then missing = true; break end
    end
    if not missing then return end
    local classFile = LF.PlayerClass()
    if not classFile then return end
    local list = LF.LoadPresets(classFile)
    for i = 1, #c do
        local s = c[i]
        if type(s) == "table" and type(s.PresetIdx) ~= "number" then
            local hit = 0
            if type(s.Name) == "string" and s.Name ~= "" then
                for j = 1, #list do
                    if list[j].Name == s.Name then hit = j; break end
                end
            end
            if hit == 0 and s.Icon ~= nil then
                local cnt = 0
                for j = 1, #list do
                    if list[j].Icon == s.Icon then cnt = cnt + 1; hit = j end
                end
                if cnt ~= 1 then hit = 0 end
            end
            s.PresetIdx = hit
        end
    end
end

local function ShapeStore(c)
    if type(c) ~= "table" then return end
    for i = 1, #c do
        local s = c[i]
        if type(s) == "table" then
            if type(s.Name) ~= "string" or s.Name == "" then s.Name = L["未命名方案"] end
            if type(s.Icon) ~= "string" or s.Icon == "" then s.Icon = D.DEFAULT_ICON end
            for _, dim in ipairs(LF.DIMENSIONS) do
                if type(s[dim]) ~= "table" then s[dim] = {} end
            end
        end
    end
    if type(c.chooseID) == "number" and (c.chooseID < 1 or c.chooseID > #c) then c.chooseID = nil end
    LF.BackfillPresetIdx(c)
end

function LF.GetStore()
    if LF.__store then return LF.__store end
    local db = ns.DB()
    local ui = db.ui
    local lf = ui.lootFilter
    if type(lf) ~= "table" then lf = {}; ui.lootFilter = lf end
    if lf.ver ~= LF.VER then
        for k in pairs(lf) do if k ~= "ver" then lf[k] = nil end end
        lf.ver = LF.VER
    end

    local realm = (type(GetRealmName) == "function" and GetRealmName()) or nil
    if type(realm) ~= "string" or realm == "" then realm = "未知服务器" end
    local char = (type(UnitName) == "function" and UnitName("player")) or nil
    if type(char) ~= "string" or char == "" then char = "未知角色" end

    local r = lf[realm]
    if type(r) ~= "table" then r = {}; lf[realm] = r end
    local c = r[char]
    if type(c) ~= "table" then c = {}; r[char] = c; LF.PopulateFirstTime(c) end

    ShapeStore(c)
    LF.__store = c
    return c
end

function LF.GetActiveScheme()
    local store = LF.GetStore()
    local ch = store.chooseID
    if ch and store[ch] then return store[ch], ch end
    return nil, nil
end

function LF.SetActiveScheme(idx)
    local store = LF.GetStore()
    if idx ~= nil and store[idx] == nil then idx = nil end
    store.chooseID = idx
    LF.ClearResults()
    LF.ApplyAll()
end

function LF.AddScheme(name, icon)
    local store = LF.GetStore()
    if #store >= LF.MAX_SCHEMES then return nil end
    store[#store + 1] = {
        Name = (type(name) == "string" and name ~= "") and name or L["未命名方案"],
        Icon = (type(icon) == "string" and icon ~= "") and icon or D.DEFAULT_ICON,
        PresetIdx = 0,
        Weapon = {}, Armor = {}, ShuXing = {},
        Class = { [D.FLAG_CLASS] = 1 }, BnetAccount = { [D.FLAG_BNET] = 1 }, Tank = {},
    }
    LF.ClearResults()
    return #store
end

function LF.DeleteScheme(idx)
    local store = LF.GetStore()
    if store[idx] == nil then return end
    table.remove(store, idx)
    local ch = store.chooseID
    if ch == idx then store.chooseID = nil
    elseif ch and ch > idx then store.chooseID = ch - 1 end
    LF.ClearResults()
    LF.ApplyAll()
end

function LF.RenameScheme(idx, name)
    local store = LF.GetStore()
    if store[idx] and type(name) == "string" and name ~= "" then store[idx].Name = name end
end

function LF.SetSchemeIcon(idx, icon)
    local store = LF.GetStore()
    if store[idx] and type(icon) == "string" and icon ~= "" then store[idx].Icon = icon end
end

function LF.MoveScheme(idx, dir)
    local store = LF.GetStore()
    local j = idx + (dir or 0)
    if store[idx] == nil or store[j] == nil then return end
    store[idx], store[j] = store[j], store[idx]
    local ch = store.chooseID
    if ch == idx then store.chooseID = j elseif ch == j then store.chooseID = idx end
end

function LF.SetOption(scheme, dim, key, checked)
    if not scheme or type(dim) ~= "string" or key == nil then return end
    if type(scheme[dim]) ~= "table" then scheme[dim] = {} end
    if checked then scheme[dim][key] = 1 else scheme[dim][key] = nil end
    LF.ClearResults()
end

function LF.ToggleBulk(scheme, mode)
    if not scheme then return end
    local all = (mode == "all")
    for _, dim in ipairs(LF.DIMENSIONS) do
        if type(scheme[dim]) ~= "table" then scheme[dim] = {} end
        local t = scheme[dim]
        for k in pairs(t) do t[k] = nil end
    end
    if all then
        for _, k in ipairs(D.KeyList("Weapon")) do scheme.Weapon[k.key] = 1 end
        for _, k in ipairs(D.KeyList("Armor")) do scheme.Armor[k.key] = 1 end
        for _, k in ipairs(D.KeyList("ShuXing")) do scheme.ShuXing[k.key] = 1 end
        scheme.Class[D.FLAG_CLASS] = 1
        scheme.BnetAccount[D.FLAG_BNET] = 1
        scheme.Tank[D.FLAG_TANK] = 1
    end
    LF.ClearResults()
end

function LF.ShouldGrey(itemID, typeID, equipLoc, subID, tipText)
    if typeID == nil then return false end
    local scheme = LF.GetActiveScheme()
    if not scheme then return false end

    local id = itemID
    if id ~= nil then
        local cached = LF.resCache[id]
        if cached ~= nil then return cached end
    end

    local res = LF.Evaluate(scheme, typeID, equipLoc, subID, tipText or "")
    if id ~= nil then LF.resCache[id] = res end
    return res
end

function LF.Evaluate(scheme, typeID, equipLoc, subID, tip)
    if type(tip) ~= "string" then tip = "" end
    local skey = (subID ~= nil) and tostring(subID) or nil

    if typeID == D.CLASS_QUEST or typeID == D.CLASS_QUEST_ALT then return false end

    if scheme.BnetAccount and scheme.BnetAccount[D.FLAG_BNET] and HasAny(tip, D.BnetBound) then
        return false
    end

    if typeID == D.CLASS_ARMOR and D.ArmorSet[subID] and equipLoc ~= "INVTYPE_CLOAK" then
        if skey and scheme.Armor and next(scheme.Armor) ~= nil and not scheme.Armor[skey] then
            if subID == 0 then
                if equipLoc == "INVTYPE_HOLDABLE" then return true end
            else
                return true
            end
        end
    end

    if typeID == D.CLASS_WEAPON and D.WeaponSet[subID] and skey and scheme.Weapon and next(scheme.Weapon) ~= nil
       and not scheme.Weapon[skey] then
        return true
    end

    if tip ~= "" and scheme.ShuXing and next(scheme.ShuXing) ~= nil then
        local hit = false
        for name in pairs(scheme.ShuXing) do
            local pat = D.ShuXing[name]
            if pat and strfind(tip, pat) and not HasNothave(name, tip) then hit = true; break end
        end
        if not hit then return true end
    end

    if tip ~= "" and scheme.Class and scheme.Class[D.FLAG_CLASS] then
        local pre = D.ClassPrefix
        if pre and pre ~= "" and strfind(tip, pre, 1, true) then
            local _, myName = LF.PlayerClass()
            if not (myName and strfind(tip, myName, 1, true)) then return true end
        end
    end

    if tip ~= "" and scheme.Tank and scheme.Tank[D.FLAG_TANK]
       and typeID == D.CLASS_ARMOR
       and equipLoc ~= "INVTYPE_TRINKET" and equipLoc ~= "INVTYPE_RELIC" then
        local kws = D.TankKeywords
        if type(kws) == "table" and #kws > 0 then
            local hit = false
            for i = 1, #kws do
                if strfind(tip, kws[i]) then hit = true; break end
            end
            if not hit then return true end
        end
    end

    return false
end

function LF.Apply(card)
    if not card or not card.SetAlpha then return end

    local store = LF.GetStore()
    local ch = store.chooseID
    local scheme = ch and store[ch]
    if not scheme then card:SetAlpha(LF.ALPHA_FULL); return end

    local it = card.__it
    local id = it and it[1]
    if not id then card:SetAlpha(LF.ALPHA_FULL); return end

    local DG = ns.DungeonModule
    if not DG then card:SetAlpha(LF.ALPHA_FULL); return end

    local _, _, _, equipLoc, _, classID, subID = DG.ItemInfoInstant(id)
    if classID == nil then
        DG.RequestItem(id)
        card:SetAlpha(LF.ALPHA_FULL)
        return
    end

    local tip = LF.ScanTip(id)
    local dim = LF.ShouldGrey(id, classID, equipLoc, subID, tip)
    card:SetAlpha(dim and LF.ALPHA_DIM or LF.ALPHA_FULL)
end

function LF.ApplyAll()
    local U = ns.DungeonUI
    local pool = U and U.dungeonDetailPool and U.dungeonDetailPool.item
    if not pool then return end
    for i = 1, #pool do LF.Apply(pool[i]) end
end

function LF.Init()
    LF.EnsureScanTip()
    LF.GetStore()
end
ns.Init(LF.Init)
