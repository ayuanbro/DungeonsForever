local _, ns = ...

if not ns.LoadForeverPages then return end

local format = string.format
local L = ns.L

local Host = ns.ProfHost
if not Host then return end

local DG = Host.DG
local MakeFS = Host.MakeFS
local NewButton = Host.NewButton
local Unpack = Host.Unpack
local C_GOLD, C_GREY = Host.C_GOLD, Host.C_GREY
local C_DIM, C_WHITE, C_TEXT = Host.C_DIM, Host.C_WHITE, Host.C_TEXT
local FALLBACK_ICON = Host.FALLBACK_ICON
local CONTENT_W = Host.CONTENT_W
local PAGE_INSET = Host.PAGE_INSET

local ROW_H = 38
local PAGE_TOP, PAGE_BOTTOM = 8, PAGE_INSET
local CARD_GAP = 8
local CARD_PAD = 10
local LEFT_W = 190
local TITLE_ZONE = 0
local CHIP_ZONE = 0
local SORT_ZONE = 0
local HEAD_ZONE = 20
local PAGER_ZONE = 42

local QUALITY_ORDER = { 5, 4, 3, 2, 1, 0 }
local BIND_LABEL = {
    [1] = L["拾取绑定"],
    [2] = L["装备后绑定"],
    [3] = L["装备后绑定"],
    [4] = L["任务物品"],
}
local Q_COLORS = {
    [0] = { 0.62, 0.62, 0.62 },
    [1] = { 1, 1, 1 },
    [2] = { 0.12, 1, 0 },
    [3] = { 0, 0.44, 0.87 },
    [4] = { 0.64, 0.21, 0.93 },
    [5] = { 1, 0.5, 0 },
    [6] = { 0.9, 0.8, 0.5 },
    [7] = { 0.83, 0.68, 0.41 },
}
local QUALITY_LABEL = {
    [5] = L["传说"], [4] = L["史诗"], [3] = L["精良"],
    [2] = L["优秀"], [1] = L["普通"], [0] = L["粗糙"],
}

local STAT_KEYS = {
    "ITEM_MODIFIER_STRENGTH",
    "ITEM_MODIFIER_AGILITY",
    "ITEM_MODIFIER_INTELLECT",
    "ITEM_MODIFIER_STAMINA",
    "ITEM_MODIFIER_HIT_RATING",
    "ITEM_MODIFIER_CRIT_RATING",
    "ITEM_MODIFIER_HASTE_RATING",
}
local STAT_LABELS = {
    ITEM_MODIFIER_STRENGTH = L["力量"],
    ITEM_MODIFIER_AGILITY = L["敏捷"],
    ITEM_MODIFIER_INTELLECT = L["智力"],
    ITEM_MODIFIER_STAMINA = L["耐力"],
    ITEM_MODIFIER_HIT_RATING = L["命中等级"],
    ITEM_MODIFIER_CRIT_RATING = L["暴击等级"],
    ITEM_MODIFIER_HASTE_RATING = L["急速等级"],
}

local RS = ns.RaidSetData

local SET_CLASS_ICON = {
    WARRIOR = "Interface\\AddOns\\DungeonsForever\\Media\\icon\\CLASS\\ClassIcon_Warrior",
    PALADIN = "Interface\\AddOns\\DungeonsForever\\Media\\icon\\CLASS\\ClassIcon_Paladin",
    HUNTER = "Interface\\AddOns\\DungeonsForever\\Media\\icon\\CLASS\\ClassIcon_Hunter",
    ROGUE = "Interface\\AddOns\\DungeonsForever\\Media\\icon\\CLASS\\ClassIcon_Rogue",
    PRIEST = "Interface\\AddOns\\DungeonsForever\\Media\\icon\\CLASS\\ClassIcon_Priest",
    SHAMAN = "Interface\\AddOns\\DungeonsForever\\Media\\icon\\CLASS\\ClassIcon_Shaman",
    MAGE = "Interface\\AddOns\\DungeonsForever\\Media\\icon\\CLASS\\ClassIcon_Mage",
    WARLOCK = "Interface\\AddOns\\DungeonsForever\\Media\\icon\\CLASS\\ClassIcon_Warlock",
    DRUID = "Interface\\AddOns\\DungeonsForever\\Media\\icon\\CLASS\\ClassIcon_Druid",
}
local SET_CLS_ORDER = { "WARRIOR", "PALADIN", "HUNTER", "ROGUE", "PRIEST", "SHAMAN", "MAGE", "WARLOCK", "DRUID" }
local SET_CLS_ZH = {
    WARRIOR = "战士", PALADIN = "圣骑士", HUNTER = "猎人", ROGUE = "盗贼",
    PRIEST = "牧师", SHAMAN = "萨满", MAGE = "法师", WARLOCK = "术士", DRUID = "德鲁伊",
}
local WISH_WORLD_KINDS = {
    ["世界掉落"] = true, ["怪物掉落"] = true, ["任何敌人"] = true,
}
local SRC_ORDER = {
    "vendor", "mob", "world", "dungeon", "raid", "quest", "craft", "unknown",
}
local SRC_LABEL = {
    vendor = L["来源：商人"],
    mob = L["来源：怪物掉落"],
    world = L["来源：世界掉落"],
    dungeon = L["来源：5人本掉落"],
    raid = L["来源：团本掉落"],
    quest = L["来源：任务奖励"],
    craft = L["来源：专业制作"],
    unknown = L["来源：不明"],
}
local RAID_INST_IDS = { ["onyxias_lair"] = true }
local RAID_PLACE = {
    "熔火之心", "黑翼之巢", "安其拉神殿", "安其拉废墟",
    "纳克萨玛斯", "祖尔格拉布", "奥妮克希亚的巢穴",
}
local WBOSS_PLACE = { "艾莫莉丝", "伊森德雷", "泰拉尔", "莱索恩" }

local SLOT_LABEL = {
    Head = L["头部"], Neck = L["颈部"], Shoulder = L["肩部"], Back = L["背部"],
    Chest = L["胸部"], Shirt = L["衬衫"], Tabard = L["公会徽章"], Wrist = L["手腕"],
    Hands = L["手部"], Waist = L["腰部"], Legs = L["腿部"], Feet = L["脚部"],
    Finger = L["手指"], Trinket = L["饰品"], ["One-Hand"] = L["单手"],
    ["Main Hand"] = L["主手"], ["Off Hand"] = L["副手"],
    ["Held In Off-hand"] = L["副手物品"], Shield = L["盾牌"],
    ["Two-Hand"] = L["双手"], Ranged = L["远程"], Thrown = L["投掷"],
    Relic = L["圣物"], Ammo = L["弹药"], Bag = L["背包"],
}

local CLS_LABEL, SUB_LABEL, SUB_OF = {}, {}, {}

local GD, GD_ITEMS, GD_SRC, GD_SRC_Q, GD_WDLV, GD_SRC_LV, GD_QMAP, GD_SRC_RACE, INST_MIN, GD_SLOTS
local GD_QLOC2, GD_CHAIN
local __pfac = nil
local function PlayerFac()
    if __pfac == nil then
        local ok, fg = pcall(UnitFactionGroup, "player")
        __pfac = (ok and fg == "Horde") and "h" or "a"
    end
    return __pfac
end
local function QuestFac(id)
    local qid = GD_SRC_Q and id and GD_SRC_Q[id]
    if not qid or not GD_SRC_RACE then return nil end
    return GD_SRC_RACE[qid]
end
local FAC_TEX = {
    a = "Interface\\AddOns\\DungeonsForever\\Media\\icon\\FACTION\\FactionIcon_Alliance",
    h = "Interface\\AddOns\\DungeonsForever\\Media\\icon\\FACTION\\FactionIcon_Horde",
}
local QN_MARK = format("|cff%02x%02x%02x",
    math.floor((C_TEXT[1] or 1) * 255 + 0.5),
    math.floor((C_TEXT[2] or 1) * 255 + 0.5),
    math.floor((C_TEXT[3] or 1) * 255 + 0.5))
local function ApplyFacIcon(r, id)
    if not r.facIcon then return end
    local f = QuestFac(id)
    if f and FAC_TEX[f] then
        r.facIcon:SetTexture(FAC_TEX[f])
        r.facIcon:Show()
    else
        r.facIcon:Hide()
    end
end
local function EnsureGD()
    if not GD then
        local fn = ns.EnsureGearData
        GD = type(fn) == "function" and fn() or nil
        GD_ITEMS = GD and GD.items or {}
        local fsrc = ns.EnsureGearSrc
        GD_SRC = (type(fsrc) == "function" and fsrc()) or (GD and GD.src) or nil
        GD_SRC_Q = type(ns.GearSrcQ) == "table" and ns.GearSrcQ or nil
        GD_WDLV = type(ns.GearWDLv) == "table" and ns.GearWDLv or nil
        GD_SRC_LV = type(ns.GearSrcQLv) == "table" and ns.GearSrcQLv or nil
        GD_QMAP = type(ns.GearQuestMap) == "table" and ns.GearQuestMap or nil
        GD_QLOC2 = type(ns.GearQuestLoc2) == "table" and ns.GearQuestLoc2 or nil
        GD_CHAIN = type(ns.GearQuestChain) == "table" and ns.GearQuestChain or nil
        GD_SRC_RACE = type(ns.GearQuestRace) == "table" and ns.GearQuestRace or nil
        GD_SLOTS = type(ns.GearSlots) == "table" and ns.GearSlots or nil
        for _, pair in ipairs(GD and GD.cls or {}) do
            CLS_LABEL[pair[1]] = pair[2]
            local arr
            local subs = GD.sub and GD.sub[pair[1]]
            if subs then
                arr = {}
                for _, sp in ipairs(subs) do
                    arr[#arr + 1] = sp
                    SUB_LABEL[pair[1] .. ":" .. sp[1]] = sp[2]
                end
            end
            SUB_OF[pair[1]] = arr
        end
    end
    local gm = ns.GearModule
    if gm and not gm.catalog and not gm.__building and type(gm.BuildCatalog) == "function" then
        gm.__building = true
        gm.__noYield = true
        pcall(gm.BuildCatalog, gm)
        gm.__noYield = nil
        gm.__building = nil
    end
    return GD
end

local W_GROUPS = {
    { key = "w1", lk = L["单手"], us = { [0] = true, [4] = true, [7] = true, [15] = true, [13] = true, [19] = true },
        leaves = { 0, 4, 7, 15, 13, 19 } },
    { key = "w2", lk = L["双手"], us = { [1] = true, [5] = true, [8] = true, [6] = true, [10] = true },
        leaves = { 1, 5, 8, 6, 10 } },
    { key = "w3", lk = L["远程"], us = { [2] = true, [18] = true, [3] = true, [16] = true },
        leaves = { 2, 18, 3, 16 } },
    { key = "w4", lk = L["杂项"], us = { [20] = true, [14] = true, [9] = true },
        leaves = { 20, 14, 9 } },
}
local WU2G = {}
for _, g in ipairs(W_GROUPS) do
    for u in pairs(g.us) do WU2G[u] = g end
end
local ARMOR_SLOTS = { "Head", "Shoulder", "Chest", "Waist", "Legs", "Feet", "Wrist", "Hands" }
local AS8 = {}
for _, s in ipairs(ARMOR_SLOTS) do AS8[s] = true end
local TM_SLOTS = {
    { "Neck", L["颈部"] }, { "Back", L["披风"] }, { "Finger", L["手指"] }, { "Trinket", L["饰品"] },
    { "Held In Off-hand", L["副手物品"] }, { "Shield", L["盾牌"] }, { "Shirt", L["衬衫"] },
    { "Tabard", L["公会徽章"] },
}
local TMSK = {}
for _, p in ipairs(TM_SLOTS) do TMSK[p[1]] = true end
local pathCache = {}
local NO_KEYS = {}
local function PathKeysOf(c, u, s)
    if c == nil then return NO_KEYS end
    local ck = c .. "|" .. (u or -1) .. "|" .. (s or "")
    local hit = pathCache[ck]
    if hit then return hit end
    local keys = { "c:" .. c }
    if c == 2 then
        local g = WU2G[u]
        if g then
            keys[2] = "c:2:" .. g.key
            keys[3] = "c:2:" .. g.key .. ":u" .. u
        end
    elseif c == 4 then
        if u == 7 or u == 8 or u == 9 then
            keys[2] = "c:4:tR"
        elseif TMSK[s] then
            keys[2] = "c:4:tM"
            keys[3] = "c:4:tM:" .. s
        elseif u == 1 or u == 2 or u == 3 or u == 4 then
            keys[2] = "c:4:t" .. u
            if AS8[s] then keys[3] = "c:4:t" .. u .. ":" .. s end
        elseif u == 5 then
            keys[2] = "c:4:tM"
            keys[3] = "c:4:tM:u5"
        else
            keys[2] = "c:4:tM"
            keys[3] = "c:4:tM:rest"
        end
    end
    pathCache[ck] = keys
    return keys
end

local SORTS = {
    { key = "req",  label = L["需要等级"] },
    { key = "ilvl", label = L["物品等级"] },
    { key = "name", label = L["名称"] },
}

local G = {}
ns.GearModule = G

local ROW_FIELDS = { id = 1, name = 2, pack = 3, icon = 4 }
local ROW_MT = {
    __index = function(t, k)
        local f = ROW_FIELDS[k]
        if f then return t[f] end
        if k == "done" then return true end
        local p = t[3]
        if k == "isNew" then return math.floor(p / 33554432) % 2 == 1 end
        if k == "q" then return p % 8 end
        if k == "ilvl" then return math.floor(p / 8) % 256 end
        if k == "req" then return math.floor(p / 2048) % 256 end
        if k == "u" then return math.floor(p / 524288) % 32 end
        if k == "c" then return math.floor(p / 16777216) % 2 == 1 and 4 or 2 end
        if k == "st" then return math.floor(p / 33554432) % 2 == 1 and "new" or "" end
        if k == "s" then
            local sl = GD_SLOTS
            if not sl then return "" end
            return sl[math.floor(p / 67108864) % 64 + 1] or ""
        end
        if k == "inst" or k == "instName" or k == "boss" then
            local so = G.srcOf and G.srcOf[t[1]]
            if so then
                if k == "inst" then return so.inst end
                if k == "boss" then return so.boss end
                return so.inst and so.inst.name or ""
            end
            if k ~= "inst" then return "" end
        end
        return rawget(t, k)
    end,
}

local recs = {}

local function GDB()
    DungeonsForeverDB = DungeonsForeverDB or {}
    local s = DungeonsForeverDB.gear
    if not s then
        s = {}
        DungeonsForeverDB.gear = s
    end
    return s
end

local function WishTable()
    DungeonsForeverDB = DungeonsForeverDB or {}
    local s = DungeonsForeverDB.wishlist
    if not s then
        s = {}
        DungeonsForeverDB.wishlist = s
    end
    return s
end

local function WishIs(id) return WishTable()[id] ~= nil end

local function WishIDs()
    local t = WishTable()
    local ids = {}
    for k in pairs(t) do
        if type(k) == "number" then ids[#ids + 1] = k end
    end
    table.sort(ids)
    return ids
end

local function BumpView()
    G.__viewVer = (G.__viewVer or 0) + 1
end

local function WishToggle(id)
    local t = WishTable()
    if t[id] then t[id] = nil else t[id] = true end
    BumpView()
end

function G.WishIs(id) return WishIs(id) end

function G.WishIDs() return WishIDs() end

function G.WishToggle(id) WishToggle(id) end

function G.AskItem(id)
    if C_Item and type(C_Item.RequestLoadItemDataByID) == "function" then
        pcall(C_Item.RequestLoadItemDataByID, id)
    end
    local fn = GetItemInfo or (C_Item and C_Item.GetItemInfo)
    if type(fn) == "function" then pcall(fn, id) end
end

local function FillRec(id)
    local r = recs[id]
    if r then return r end
    return nil
end

local function QColor(q)
    if type(q) ~= "number" then return Unpack(C_DIM) end
    local c = G.qcolors[q]
    if c then return c[1], c[2], c[3] end
    return Unpack(C_TEXT)
end

local function HasStat(r)
    local sel = G.attrs
    if next(sel) == nil then return true end
    if not r.done then return true end
    if r.stats == nil then
        local ok, st = pcall(GetItemStats, DG.ItemLink(r.id))
        r.stats = (ok and type(st) == "table") and st or false
    end
    if r.stats == false then return true end
    for key in pairs(sel) do
        local v = r.stats[key]
        if type(v) ~= "number" or v <= 0 then return false end
    end
    return true
end

local function NamePass(r)
    local s = G.search
    if s == "" then return true end
    if not r.done then return false end
    return r.name:lower():find(s, 1, true) ~= nil
end

local function IlvlInRange(r)
    if not (G.ilvlMin or G.ilvlMax) then return true end
    if not r.done then return true end
    local v = r.ilvl
    if G.ilvlMin and (v == nil or v < G.ilvlMin) then return false end
    if G.ilvlMax and (v == nil or v > G.ilvlMax) then return false end
    return true
end

local ARMOR_OK = {
    WARRIOR = { 1, 2, 3, 4 }, PALADIN = { 1, 2, 3, 4 }, DEATHKNIGHT = { 1, 2, 3, 4 },
    ROGUE = { 1, 2 }, DRUID = { 1, 2 }, MONK = { 1, 2 },
    HUNTER = { 1, 2, 3 }, SHAMAN = { 1, 2, 3 }, EVOKER = { 1, 2, 3 },
    MAGE = { 1 }, PRIEST = { 1 }, WARLOCK = { 1 },
}
local RELIC_OK = { PALADIN = { 7 }, DRUID = { 8 }, SHAMAN = { 9 }, DEATHKNIGHT = { 5 } }
local WEAPON_OK = {
    WARRIOR = { 0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 13, 15, 16, 18 },
    DEATHKNIGHT = { 0, 1, 4, 5, 6, 7, 8 },
    PALADIN = { 0, 1, 4, 5, 6 },
    HUNTER = { 0, 1, 2, 3, 7, 10, 13, 15, 16, 18 },
    ROGUE = { 0, 2, 3, 4, 7, 13, 15, 16, 18 },
    PRIEST = { 4, 10, 15, 19 },
    MAGE = { 7, 10, 15, 19 },
    WARLOCK = { 7, 10, 15, 19 },
    DRUID = { 4, 5, 10, 13, 15 },
    SHAMAN = { 0, 1, 4, 5, 6, 10, 13, 15 },
    MONK = { 0, 4, 7, 10, 13, 15 },
    EVOKER = {},
}
local __pcls = false
local function EnsureInstMin()
    if INST_MIN ~= nil then return INST_MIN end
    local dd = ns.DungeonData
    if type(dd) == "table" and type(dd.dungeons) == "table" then
        local m = {}
        for _, d in ipairs(dd.dungeons) do
            if d and d.id ~= nil and type(d.levelMin) == "number" then
                m[tostring(d.id)] = d.levelMin
            end
        end
        INST_MIN = m
    end
    return INST_MIN
end
local function UsetypePass(r)
    if not G.useType then return true end
    if not r.done then return true end
    if __pcls == false then
        local ok, _, eng = pcall(UnitClass, "player")
        __pcls = (ok and type(eng) == "string") and eng or ""
    end
    if __pcls == "" then return true end
    local lv = UnitLevel("player")
    if type(lv) == "number" and lv > 0 then
        local req = r.req
        if type(req) == "number" and req > lv then return false end
    end
    local c, u = r.c, r.u
    if c == 2 then
        local t = WEAPON_OK[__pcls]
        if not t then return true end
        for i = 1, #t do
            if t[i] == u then return true end
        end
        return false
    elseif c == 4 then
        if u == nil or u == 0 then return true end
        if u >= 1 and u <= 4 then
            local t = ARMOR_OK[__pcls]
            if not t then return true end
            for i = 1, #t do
                if t[i] == u then return true end
            end
            return false
        end
        local rl = RELIC_OK[__pcls]
        if rl then
            for i = 1, #rl do
                if rl[i] == u then return true end
            end
            return false
        end
    end
    return true
end

local function SrcKindOf(id)
    local src = GD_SRC and GD_SRC[id]
    local kind, place
    if type(src) == "string" and src ~= "" then
        kind, place = src:match("^(.-)|(.*)$")
        if not kind then kind = src end
    end
    if kind then
        if kind == "商人" then return "vendor" end
        if kind == "任务奖励" then return "quest" end
        if kind == "世界掉落" then return "world" end
        if kind == "a" or kind == "h" then return "unknown" end
        if kind == "物件" then return "world" end
        if kind:find("制作", 1, true) or kind:find("（", 1, true) then
            return "craft"
        end
    end
    if place == "专业制作" then return "craft" end
    local so = G.srcOf and G.srcOf[id]
    if so and so.inst then
        if so.inst.raid or RAID_INST_IDS[so.inst.id] then return "raid" end
        return "dungeon"
    end
    if kind == "怪物掉落" or kind == "任何敌人" or kind == "稀有掉落"
        or kind == "小怪掉落" then
        return "mob"
    end
    if kind and kind ~= "" then
        if place and place ~= "" then
            for i = 1, #RAID_PLACE do
                if place:find(RAID_PLACE[i], 1, true) then return "raid" end
            end
            for i = 1, #WBOSS_PLACE do
                if place:find(WBOSS_PLACE[i], 1, true) then return "mob" end
            end
            if place:find("稀有", 1, true) then return "mob" end
        end
        return "dungeon"
    end
    return "unknown"
end

local function SrcPass(id)
    local sel = G.srcSet
    if type(sel) ~= "table" or next(sel) == nil then return false end
    return sel[SrcKindOf(id)] == true
end

local function PassFilters(r)
    local cat = G.cat
    if cat ~= "ALL" then
        local keys = PathKeysOf(r.c, r.u, r.s)
        local ok = false
        for i = 1, #keys do
            if keys[i] == cat then
                ok = true
                break
            end
        end
        if not ok then return false end
    end
    local qs = G.qset
    if next(qs) ~= nil and not qs[r.q] then return false end
    if not IlvlInRange(r) then return false end
    if not UsetypePass(r) then return false end
    if not SrcPass(r[1]) then return false end
    if G.useType then
        local lv = UnitLevel("player")
        if type(lv) == "number" and lv > 0 then
            local rl = GD_SRC_LV and GD_SRC_LV[r[1]]
            if type(rl) == "number" and rl > lv then return false end
            local e = recs[r[1]]
            local inst = e and e.inst
            if inst and inst.id ~= nil then
                local im = EnsureInstMin()
                local dm = im and im[tostring(inst.id)]
                if type(dm) == "number" and dm > lv then return false end
            end
        end
        local fac = QuestFac(r[1])
        if fac and fac ~= PlayerFac() then return false end
    end
    if not HasStat(r) then return false end
    return NamePass(r)
end

local function SortLess(a, b)
    local mode = G.sort
    if mode == "name" then
        local na, nb = a[2] or "", b[2] or ""
        if na ~= nb then return na < nb end
    else
        local ka = (mode == "ilvl") and a.ilvl or a.req
        local kb = (mode == "ilvl") and b.ilvl or b.req
        if ka ~= kb then
            if G.sortDir == -1 then return ka < kb end
            return ka > kb
        end
    end
    return a[1] < b[1]
end

local function WishBucketOf(id, e)
    if e.inst and e.instName and e.instName ~= "" then
        local idx = G.instOrder and G.instOrder[e.inst.id] or 9999
        return "d:" .. tostring(e.inst.id or e.instName), e.instName, 100000 + idx
    end
    local kind, place
    local src = GD_SRC and GD_SRC[id]
    if type(src) == "string" then kind, place = src:match("^(.-)|(.*)$") end
    if WISH_WORLD_KINDS[kind] then
        return "world", L["开放世界"], 200001
    end
    if kind == "任务奖励" then
        return "quest", L["任务奖励"], 200004
    end
    if kind == "商人" then
        return "vendor", L["商人"], 200002
    end
    if place == "专业制作" or (kind and (kind:find("制作", 1, true) or kind:find("（%d+）"))) then
        return "craft", L["专业制作"], 200003
    end
    if place and place ~= "" then
        return "p:" .. place, place, 300000
    end
    return "misc", L["其他来源"], 400000
end

local function WishViewEntries()
    local out = {}
    local groups, gorder = {}, {}
    for id in pairs(WishTable()) do
        local e = recs[id]
        if e then
            local rec = recs[id]
            if (G.search or "") == "" or (rec and NamePass(rec)) then
                local key, label, ord = WishBucketOf(id, e)
                local g = groups[key]
                if not g then
                    g = { label = label, ord = ord, items = {} }
                    groups[key] = g
                    gorder[#gorder + 1] = key
                end
                g.items[#g.items + 1] = e
            end
        end
    end
    table.sort(gorder, function(a, b)
        local ga, gb = groups[a], groups[b]
        if ga.ord ~= gb.ord then return ga.ord < gb.ord end
        return ga.label < gb.label
    end)
    for _, key in ipairs(gorder) do
        local g = groups[key]
        table.sort(g.items, function(a, b) return a.id < b.id end)
        out[#out + 1] = { hdr = format(L["%s · %d 件"], g.label, #g.items) }
        for _, e in ipairs(g.items) do out[#out + 1] = e end
    end
    return out
end

local function IsSetCat(k)
    return k == "SETS" or (type(k) == "string" and k:sub(1, 4) == "SET:")
end

local function SetKeyOf(set, idx)
    return "SET:" .. (set.batch or "t1") .. ":" .. idx
end

local function SetsViewEntries()
    local out = {}
    if not RS or type(RS.sets) ~= "table" then return out end
    local function emitSet(set, idx, withItems)
        local skey = SetKeyOf(set, idx)
        out[#out + 1] = { kind = "set", set = set, skey = skey }
        if not withItems and G.setOpen ~= skey then return end
        for _, pid in ipairs(set.ids or {}) do
            out[#out + 1] = { id = pid }
        end
        if set.revealed == false then
            out[#out + 1] = { kind = "bonus", n = 0, text = L["效果尚未揭示"], dim = true }
        else
            for n = 2, 9 do
                local txt = set.bonuses and set.bonuses[n]
                if txt then out[#out + 1] = { kind = "bonus", n = n, text = txt } end
            end
        end
    end
    if G.cat == "SETS" then
        local batches = RS.batches
        if type(batches) ~= "table" or #batches == 0 then
            batches = { { key = "t1", label = RS.raid or "" } }
        end
        for _, bt in ipairs(batches) do
            local any = false
            for idx, set in ipairs(RS.sets) do
                if (set.batch or "t1") == bt.key then any = true break end
            end
            if any then
                out[#out + 1] = { hdr = bt.label or bt.key }
                for idx, set in ipairs(RS.sets) do
                    if (set.batch or "t1") == bt.key then
                        emitSet(set, idx, false)
                    end
                end
            end
        end
    elseif IsSetCat(G.cat) then
        local rest = G.cat:sub(5)
        local si = rest:match(":(%d+)$")
        if si then
            local set = RS.sets[tonumber(si)]
            if set then emitSet(set, tonumber(si), true) end
        else
            local bt, cls = rest:match("^([%w]+):([%a]+)$")
            for idx, set in ipairs(RS.sets) do
                local ok
                if bt and cls then
                    ok = (set.batch or "t1") == bt and set.class == cls
                else
                    ok = (set.batch or "t1") == rest
                end
                if ok then emitSet(set, idx, false) end
            end
        end
    end
    return out
end

local function EstRowH(e)
    if e.hdr then return 26 end
    if e.kind == "bonus" then
        local text = e.n > 0 and format(L["%d 件：%s"], e.n, e.text or "") or (e.text or "")
        local wide = 0
        for i = 1, #text do
            local b = text:byte(i)
            if b < 0x80 or b >= 0xC0 then
                wide = wide + (b < 0x80 and 8 or 14)
            end
        end
        local lw = G.listHost and G.listHost.GetWidth and G.listHost:GetWidth()
        if type(lw) ~= "number" or lw <= 0 then lw = 560 end
        local avail = lw - 2 * CARD_PAD - 40 - 6
        if avail < 120 then avail = 120 end
        local lines = math.ceil(wide / avail)
        if lines < 1 then lines = 1 end
        local h = lines * 18 + 14
        if h < 34 then h = 34 end
        return h
    end
    return ROW_H
end

local function ChunkByRows(entries)
    local pages, size, cur = {}, G.pageSize or 20, {}
    for _, e in ipairs(entries) do
        cur[#cur + 1] = e
        if #cur >= size then
            pages[#pages + 1] = cur
            cur = {}
        end
    end
    if #cur > 0 then pages[#pages + 1] = cur end
    return pages
end

local function ChunkByHeight(entries, budget)
    local pages, cur, used = {}, {}, 0
    for _, e in ipairs(entries) do
        local h = EstRowH(e)
        if #cur > 0 and used + h > budget then
            pages[#pages + 1] = cur
            cur, used = {}, 0
        end
        cur[#cur + 1] = e
        used = used + h
    end
    if #cur > 0 then pages[#pages + 1] = cur end
    return pages
end

local function RebuildView()
    local entries
    if G.cat == "WISH" then
        entries = WishViewEntries()
    elseif IsSetCat(G.cat) then
        entries = SetsViewEntries()
    else
        local out = {}
        for _, r in ipairs(G.catalog or {}) do
            if PassFilters(r) then out[#out + 1] = r end
        end
        table.sort(out, SortLess)
        entries = out
    end
    G.view = entries
    if IsSetCat(G.cat) then
        G.pagesData = ChunkByHeight(entries, (G.pageSize or 20) * ROW_H)
    else
        G.pagesData = ChunkByRows(entries)
    end
    G.pages = math.max(1, #G.pagesData)
    if (G.page or 1) > G.pages then G.page = G.pages end
end

local function CountPass(r)
    local qs = G.qset
    return (next(qs) == nil or (r.q ~= nil and qs[r.q]))
        and IlvlInRange(r) and UsetypePass(r) and HasStat(r) and NamePass(r)
end

local function CatCountsSync()
    local counts, total = {}, 0
    for _, r in ipairs(G.catalog or {}) do
        if CountPass(r) then
            total = total + 1
            local keys = PathKeysOf(r.c, r.u, r.s)
            for i = 1, #keys do
                counts[keys[i]] = (counts[keys[i]] or 0) + 1
            end
        end
    end
    G.__countSig = G.__viewSig
    G.__countCache = { counts, total }
    return counts, total
end

local function CatCounts()
    if G.__countCache and G.__countSig == G.__viewSig then
        return G.__countCache[1], G.__countCache[2]
    end
    return CatCountsSync()
end

local function Cardify(f, hoverR, baseN)
    if ns.hui and ns.hui.HuiCardFX and ns.hui.HuiCardFX(f, hoverR, baseN) then return end
    f:SetBackdrop({
        bgFile = "Interface\\Buttons\\WHITE8x8",
        edgeFile = "Interface\\Buttons\\WHITE8x8",
        edgeSize = 1,
    })
    f:SetBackdropColor(0x16 / 255, 0x1A / 255, 0x22 / 255, 1)
    f:SetBackdropBorderColor(1, 1, 1, 0.1)
    f.__plainCard = true
end

local function CardState(f, st)
    if f.__huiCard then
        ns.hui.HuiCardState(f, st)
        return
    end
    if f.__plainCard and f.SetBackdropColor then
        if st == "hover" then
            f:SetBackdropColor(0x2B / 255, 0x31 / 255, 0x40 / 255, 1)
        elseif st == "norm" then
            f:SetBackdropColor(0x16 / 255, 0x1A / 255, 0x22 / 255, 1)
        end
    end
end

local function SrcLines(e)
    local boss = e.boss or ""
    local inst = e.instName or ""
    if boss ~= "" or inst ~= "" then
        if boss == inst then return boss, "" end
        return boss, inst
    end
    local r = recs[e.id]
    if r and r.srcText then
        local kind, place = r.srcText:match("^(.-)|(.*)$")
        if kind then
            if kind == place or place == "" then return kind, "" end
            return kind, place
        end
        return r.srcText, ""
    end
    if GD_SRC then
        local s = GD_SRC[e.id]
        if type(s) == "string" and s ~= "" then
            local kind, place = s:match("^(.-)|(.*)$")
            if kind then
                local qlv = GD_SRC_LV and GD_SRC_LV[e.id]
                local locked = false
                if qlv and qlv > 0 then
                    local pl = UnitLevel and UnitLevel("player") or 0
                    locked = pl > 0 and qlv > pl
                    place = (place ~= "" and (place .. " · ") or "")
                            .. format(L["%d级可接"], qlv)
                end
                local lv = GD_WDLV and GD_WDLV[e.id]
                if lv then
                    place = (place ~= "" and (place .. " · ") or "")
                            .. format(L["%s级怪物"], lv[1] .. "-" .. lv[2])
                end
                if kind == place or place == "" then return kind, "", locked end
                return kind, place, locked
            end
            return s, ""
        end
    end
    return "", ""
end

local function QuestLocOf(qid)
    local l = GD_QMAP and GD_QMAP[qid]
    if type(l) == "table" and l[1] then return l end
    l = GD_QLOC2 and GD_QLOC2[qid]
    if type(l) == "table" and l[1] then return l end
    return nil
end

local function ChainIndexOf(qid)
    if not GD_CHAIN or not qid then return nil end
    local cache = G.__chainIdx
    if not cache then
        cache = {}
        for ci, ch in ipairs(GD_CHAIN) do
            for _, st in ipairs(ch) do
                for _, q in ipairs(st) do cache[q] = ci end
            end
        end
        G.__chainIdx = cache
    end
    return cache[qid]
end

local function ItemTip(owner, id)
    if not GameTooltip then return end
    local gif = GetItemInfo or (C_Item and C_Item.GetItemInfo)
    if not gif then return end
    local ok, known = pcall(gif, id)
    if type(known) == "string" and known ~= "" then
        GameTooltip:SetOwner(owner, "ANCHOR_RIGHT")
        GameTooltip:SetHyperlink(DG.ItemLink(id))
        local qid = GD_SRC_Q and GD_SRC_Q[id]
        if qid then
            if ChainIndexOf(qid) then
                GameTooltip:AddLine(L["点击：查看任务链"], 1, 0.82, 0, true)
            else
                local loc = QuestLocOf(qid)
                if type(loc) == "table" and loc[1] and loc[2] then
                    GameTooltip:AddLine(L["点击：在地图上标记该任务"], 1, 0.82, 0, true)
                elseif type(loc) == "table" and loc[1] then
                    GameTooltip:AddLine(L["点击：打开任务所在地图"], 1, 0.82, 0, true)
                end
            end
        end
        GameTooltip:Show()
        G.__tipOwner = owner
        G.__tipId = id
        return
    end
    GameTooltip:SetOwner(owner, "ANCHOR_RIGHT")
    GameTooltip:ClearLines()
    local r = recs[id]
    if r then
        local cr, cg, cb = QColor(r.q)
        GameTooltip:AddLine(r.name or format(L["未识别物品 #%d"], id), cr, cg, cb, true)
        local slot = r.s ~= "" and SLOT_LABEL[r.s] or nil
        local sub = SUB_LABEL[r.c .. ":" .. r.u]
        local meta = (slot and sub) and (slot .. " · " .. sub) or (slot or sub)
        if meta and meta ~= "" then
            GameTooltip:AddLine(meta, 0.7, 0.7, 0.7, true)
        end
        if r.ilvl and r.ilvl > 0 then
            GameTooltip:AddLine(format(L["物品等级 %d"], r.ilvl), 1, 1, 1, true)
        end
        if r.req and r.req > 0 then
            GameTooltip:AddLine(format(L["需要等级 %d"], r.req), 1, 1, 1, true)
        end
        local l1, l2, llock = SrcLines(r)
        if l1 and l1 ~= "" then GameTooltip:AddLine(l1, 0.7, 0.7, 0.7, true) end
        if l2 and l2 ~= "" then
            if llock then
                GameTooltip:AddLine(l2, 1, 0.35, 0.3, true)
            else
                GameTooltip:AddLine(l2, 0.5, 0.5, 0.5, true)
            end
        end
    else
        GameTooltip:AddLine(format(L["未识别物品 #%d"], id), 1, 1, 1, true)
    end
    local qid = GD_SRC_Q and GD_SRC_Q[id]
    if qid then
        if ChainIndexOf(qid) then
            GameTooltip:AddLine(L["点击：查看任务链"], 1, 0.82, 0, true)
        else
            local loc = QuestLocOf(qid)
            if type(loc) == "table" and loc[1] and loc[2] then
                GameTooltip:AddLine(L["点击：在地图上标记该任务"], 1, 0.82, 0, true)
            elseif type(loc) == "table" and loc[1] then
                GameTooltip:AddLine(L["点击：打开任务所在地图"], 1, 0.82, 0, true)
            end
        end
    end
    GameTooltip:AddLine(L["正在向服务器查询物品数据…"], 0.5, 0.5, 0.5, true)
    GameTooltip:Show()
    G.__tipOwner = owner
    G.__tipId = id
end

local function TipOff()
    G.__tipOwner = nil
    G.__tipId = nil
    if GameTooltip then GameTooltip:Hide() end
end

local function SaveQset()
    local arr = {}
    for q in pairs(G.qset) do arr[#arr + 1] = q end
    GDB().qset = arr
end

local function SetTextC(fs, s)
    local db = DungeonsForeverDB
    if db and db.dfTextOff then return end
    if fs.__dfT ~= s then
        fs.__dfT = s
        fs:SetText(s)
    end
end

local function SetTexC(tex, p)
    local db = DungeonsForeverDB
    if db and db.dfIconOff then return end
    if tex.__dfP ~= p then
        tex.__dfP = p
        tex:SetTexture(p)
    end
end

local function PaintRow(r)
    local e = r.entry
    if not e then
        r:Hide()
        return
    end
    r:Show()
    r.__hover = r:IsMouseOver()
    if r.__huiCard or r.__plainCard then
        CardState(r, r.__hover and "hover" or "norm")
    end
    r.name:ClearAllPoints()
    r.name:SetPoint("TOPLEFT", r, "TOPLEFT", CARD_PAD + 40, -3)
    r.src:ClearAllPoints()
    r.src:SetPoint("TOPLEFT", CARD_PAD + 470, -3)
    r.src:SetPoint("RIGHT", r, "RIGHT", -(CARD_PAD + 34), 0)
    SetTextC(r.src2, "")
    if e.hdr then
        r.icon:SetShown(false)
        r.newTag:SetShown(false)
        r.star:SetAlpha(0)
        SetTextC(r.name, e.hdr)
        r.name:SetTextColor(Unpack(C_GOLD))
        r.name:ClearAllPoints()
        r.name:SetPoint("TOPLEFT", r, "TOPLEFT", CARD_PAD + 40, -6)
        SetTextC(r.meta, "")
        SetTextC(r.req, "")
        SetTextC(r.ilvl, "")
        r.src:ClearAllPoints()
        r.src:SetPoint("TOPLEFT", CARD_PAD + 470, -6)
        r.src:SetPoint("RIGHT", r, "RIGHT", -(CARD_PAD + 34), 0)
        r.src:SetWordWrap(false)
        SetTextC(r.src2, "")
        SetTextC(r.sub, "")
        SetTextC(r.src, "")
        if r.facIcon then r.facIcon:Hide() end
        if r.srcQ then r.srcQ:SetText("") r.srcQ:Hide() end
        r.__h = 26
        return
    end
    if e.kind == "bonus" then
        r.icon:SetShown(false)
        r.newTag:SetShown(false)
        r.star:SetAlpha(0)
        SetTextC(r.name, "")
        SetTextC(r.meta, "")
        SetTextC(r.req, "")
        SetTextC(r.ilvl, "")
        r.src:ClearAllPoints()
        r.src:SetPoint("LEFT", CARD_PAD + 40, 0)
        r.src:SetPoint("RIGHT", r, "RIGHT", -CARD_PAD, 0)
        r.src:SetWordWrap(true)
        SetTextC(r.src, e.n > 0 and format(L["%d 件：%s"], e.n, e.text or "") or (e.text or ""))
        r.src:SetTextColor(Unpack(e.dim and C_DIM or C_GOLD))
        SetTextC(r.src2, "")
        SetTextC(r.sub, "")
        local h = r.src.GetStringHeight and r.src:GetStringHeight()
        if type(h) ~= "number" or h < 18 then h = 18 end
        r.__h = h + 14
        if r.facIcon then r.facIcon:Hide() end
        if r.srcQ then r.srcQ:SetText("") r.srcQ:Hide() end
        return
    end
    r.icon:SetShown(true)
    r.src:ClearAllPoints()
    r.src:SetPoint("TOPLEFT", CARD_PAD + 470, -3)
    r.src:SetPoint("RIGHT", r, "RIGHT", -(CARD_PAD + 34), 0)
    r.src:SetWordWrap(false)
    if e.kind == "set" then
        local set = e.set or {}
        r.newTag:SetShown(false)
        r.star:SetAlpha(0)
        local iconSet = set.class and SET_CLASS_ICON[set.class]
        if iconSet then
            SetTexC(r.icon, iconSet)
        else
            local rec = recs[(set.ids or {})[1]]
            if rec and rec.icon and rec.icon ~= "" then
                SetTexC(r.icon, "Interface\\Icons\\" .. rec.icon)
            else
                SetTexC(r.icon, FALLBACK_ICON)
            end
        end
        local cr, cg, cb
        if G.setOpen == e.skey then
            cr, cg, cb = Unpack(C_GOLD)
        elseif set.class and set.class ~= "" and RAID_CLASS_COLORS then
            local cc = RAID_CLASS_COLORS[set.class]
            if cc and cc.r then cr, cg, cb = cc.r, cc.g, cc.b end
        end
        if not cr then
            if set.revealed == false then
                cr, cg, cb = Unpack(C_DIM)
            else
                cr, cg, cb = Unpack(C_TEXT)
            end
        end
        SetTextC(r.name, (G.setOpen == e.skey and "- " or "+ ") .. (set.name or ""))
        r.name:SetTextColor(cr, cg, cb)
        local meta
        if set.armor and set.spec then
            meta = set.armor .. " · " .. set.spec
        else
            meta = set.armor or set.spec or ""
        end
        SetTextC(r.meta, meta)
        SetTextC(r.req, "")
        SetTextC(r.ilvl, "")
        SetTextC(r.src, format(L["%d 件套"], #(set.ids or {})))
        r.src:SetTextColor(Unpack(C_GREY))
        r.__h = ROW_H
        return
    end
    local rec = FillRec(e.id)
    if rec then
        local k = rec.icon
        if type(k) == "string" and k ~= "" then
            SetTexC(r.icon, "Interface\\Icons\\" .. k)
        else
            SetTexC(r.icon, FALLBACK_ICON)
        end
        local cr, cg, cb = QColor(rec.q)
        SetTextC(r.name, rec.name)
        r.name:SetTextColor(cr, cg, cb)
        local slot = rec.s ~= "" and SLOT_LABEL[rec.s] or nil
        local sub = SUB_LABEL[rec.c .. ":" .. rec.u]
        local meta
        if slot and sub then
            meta = slot .. " · " .. sub
        else
            meta = slot or sub or ""
        end
        SetTextC(r.meta, meta)
        SetTextC(r.req, rec.req and rec.req > 0 and tostring(rec.req) or "-")
        SetTextC(r.ilvl, rec.ilvl and rec.ilvl > 0 and tostring(rec.ilvl) or "-")
        r.ilvl:SetTextColor(cr, cg, cb)
        if rec.bind == nil then
            local bfn = GetItemInfo or (C_Item and C_Item.GetItemInfo)
            if type(bfn) == "function" then
                local ok, bt = pcall(function()
                    local _, _, _, _, _, _, _, _, _, _, _, _, _, b = bfn(rec.id)
                    return b
                end)
                rec.bind = (ok and type(bt) == "number") and bt or false
            else
                rec.bind = false
            end
        end
        SetTextC(r.sub, BIND_LABEL[rec.bind] or "")
    else
        SetTexC(r.icon, FALLBACK_ICON)
        local gif = GetItemInfo or (C_Item and C_Item.GetItemInfo)
        local ok, nm
        if type(gif) == "function" then ok, nm = pcall(gif, e.id) end
        if ok and type(nm) == "string" and nm ~= "" then
            SetTextC(r.name, nm)
        else
            SetTextC(r.name, format(L["未识别物品 #%d"], e.id))
            if not G.__asked[e.id] then
                G.__asked[e.id] = true
                G.AskItem(e.id)
            end
        end
        r.name:SetTextColor(Unpack(C_DIM))
        SetTextC(r.meta, "")
        SetTextC(r.req, "")
        SetTextC(r.ilvl, "")
    end
    local s1, s2, slock = SrcLines(e)
    SetTextC(r.src, s1)
    r.src:SetTextColor(Unpack(C_TEXT))
    SetTextC(r.src2, s2)
    if slock then
        r.src2:SetTextColor(1, 0.35, 0.3)
    else
        r.src2:SetTextColor(Unpack(C_DIM))
    end
    local qid = GD_SRC_Q and GD_SRC_Q[e.id]
    local qn = nil
    if qid then
        local qfn = C_QuestLog and C_QuestLog.GetTitleForQuestID
        if type(qfn) == "function" then
            local ok, t = pcall(qfn, qid)
            if ok and type(t) == "string" and t ~= "" then qn = t end
        end
        if not qn then
            local req = C_QuestLog and C_QuestLog.RequestLoadQuestByID
            if type(req) == "function" then
                G.__qAsked = G.__qAsked or {}
                if not G.__qAsked[qid] then
                    G.__qAsked[qid] = true
                    pcall(req, qid)
                end
            end
        end
    end
    ApplyFacIcon(r, e.id)
    local facOn = r.facIcon and r.facIcon:IsShown()
    if r.srcQ then
        if qid then
            if qn and qn ~= "" then
                r.srcQ:SetText(QN_MARK .. qn .. "|r #" .. qid)
            else
                r.srcQ:SetText("#" .. qid)
            end
            local w1 = r.src:GetStringWidth()
            if type(w1) ~= "number" or w1 < 0 then w1 = 0 end
            local qx = w1 + 8
            if facOn then
                r.facIcon:SetPoint("TOPLEFT", r.src, "TOPLEFT", w1 + 4, 1)
                qx = w1 + 4 + 16 + 6
            end
            r.srcQ:SetPoint("TOPLEFT", r.src, "TOPLEFT", qx, 0)
            r.srcQ:Show()
        else
            r.srcQ:SetText("")
            r.srcQ:Hide()
        end
    end
    if r.srcZone then
        local w1 = r.src:GetStringWidth()
        if type(w1) ~= "number" or w1 < 0 then w1 = 0 end
        local wq = 0
        if r.srcQ and r.srcQ:IsShown() then
            wq = r.srcQ:GetStringWidth()
            if type(wq) ~= "number" or wq < 0 then wq = 0 end
            wq = wq + (facOn and 28 or 8)
        elseif facOn then
            wq = 18
        end
        local sw = math.max(w1 + wq, r.src2:GetStringWidth())
        local fw = r.src:GetWidth()
        if type(fw) == "number" and fw > 0 and sw > fw then sw = fw end
        if sw < 40 then sw = 40 end
        r.srcZone:SetWidth(sw + 6)
    end
    r.newTag:SetShown(e.isNew ~= nil and e.isNew or false)
    local wid = e.id
    if wid and WishIs(wid) then
        SetTextC(r.star.tex, "★")
        r.star.tex:SetTextColor(1, 0.82, 0)
        r.star:SetAlpha(1)
    else
        SetTextC(r.star.tex, "☆")
        r.star.tex:SetTextColor(Unpack(C_GREY))
        r.star:SetAlpha(1)
    end
    r.__h = ROW_H
end

local function StarClick(r)
    local e = r.entry
    if not e or not e.id then return end
    WishToggle(e.id)
    ns.PlaySound(1)
    G.PaintList()
end

local function PlaceMapID(place)
    if not place or place == "" then return nil end
    local dd = ns.DungeonData and ns.DungeonData.dungeons
    if type(dd) ~= "table" then return nil end
    for _, d in ipairs(dd) do
        if d.name == place and ns.DungeonEntry and ns.DungeonEntry[d.id] then
            return ns.DungeonEntry[d.id][1]
        end
    end
    return nil
end

local REV_ZONE, REV_BUILT
local function PlaceZoneID(place)
    if not place or place == "" then return nil end
    local zone = place:match("^(.-)·") or place
    if zone == "" then return nil end
    if not REV_BUILT then
        REV_BUILT = true
        REV_ZONE = {}
        if ns.AreaMap and C_Map and C_Map.GetMapInfo then
            for _, mid in pairs(ns.AreaMap) do
                local ok, mi = pcall(C_Map.GetMapInfo, mid)
                if ok and mi and mi.name and not REV_ZONE[mi.name] then
                    REV_ZONE[mi.name] = mid
                end
            end
        end
    end
    return REV_ZONE[zone]
end

local function MarkQuest(qid, loc)
    local ver = select(4, GetBuildInfo()) or 0
    if ver < 16000 or ver > 16999 then
        if UIErrorsFrame and UIErrorsFrame.AddMessage then
            pcall(UIErrorsFrame.AddMessage, UIErrorsFrame,
                  L["地图标记仅无限客户端支持"], 1, 0.6, 0.2)
        end
        return
    end
    if type(loc) ~= "table" or not loc[1] then
        if UIErrorsFrame and UIErrorsFrame.AddMessage then
            pcall(UIErrorsFrame.AddMessage, UIErrorsFrame,
                  format(L["未收录任务 #%d 的地图位置"], qid), 1, 0.4, 0.4)
        end
        return
    end
    if loc[2] and UiMapPoint and UiMapPoint.CreateFromCoordinates
            and C_Map and C_Map.SetUserWaypoint
            and (not C_Map.CanSetUserWaypointOnMap
                 or C_Map.CanSetUserWaypointOnMap(loc[1])) then
        local ok, pt = pcall(UiMapPoint.CreateFromCoordinates,
                             loc[1], loc[2] / 100, loc[3] / 100)
        if ok and pt then
            pcall(C_Map.SetUserWaypoint, pt)
            if C_SuperTrack and C_SuperTrack.SetSuperTrackedUserWaypoint then
                pcall(C_SuperTrack.SetSuperTrackedUserWaypoint, false)
            end
        end
    end
    if C_Map and C_Map.OpenWorldMap then
        pcall(C_Map.OpenWorldMap, loc[1])
    elseif OpenWorldMap then
        pcall(OpenWorldMap, loc[1])
    end
end

local CQF = nil

local function ChainHookSync()
    local hl = DG.__qDataHooks
    if not hl then return end
    if CQF and CQF.IsShown and CQF:IsShown() then
        if not hl.__gearChain then
            hl.__gearChain = function(id)
                if CQF and CQF.IsShown and CQF:IsShown()
                        and CQF.__pending and CQF.__pending[id] then
                    CQF.__pending[id] = nil
                    if CQF.__render then CQF.__render() end
                end
            end
            hl[#hl + 1] = hl.__gearChain
        end
    elseif hl.__gearChain then
        for i = #hl, 1, -1 do
            if hl[i] == hl.__gearChain then table.remove(hl, i) end
        end
        hl.__gearChain = nil
    end
end

local function ChainQuestDone(qid)
    if C_QuestLog and C_QuestLog.IsQuestFlaggedCompleted then
        local ok, r = pcall(C_QuestLog.IsQuestFlaggedCompleted, qid)
        if ok and r then return true end
    end
    return false
end

local function ChainRender()
    local qid0, ci = CQF.__qid, CQF.__ci
    local ch = GD_CHAIN and GD_CHAIN[ci]
    if not (qid0 and type(ch) == "table") then return end
    CQF.__pending = CQF.__pending or {}
    for k in pairs(CQF.__pending) do CQF.__pending[k] = nil end

    local rows = {}
    for si, st in ipairs(ch) do
        for bi, q in ipairs(st) do
            rows[#rows + 1] = { q = q, si = si, sub = #st > 1 }
        end
    end

    local nm0, nm0ok
    if DG.QuestName then nm0, nm0ok = DG.QuestName(qid0) end
    if not nm0ok then
        if DG.RequestQuest then DG.RequestQuest(qid0) end
        CQF.__pending[qid0] = true
        nm0 = "……"
    end
    CQF.__sub:SetText(L["装备奖励需要完成任务："] .. nm0)

    local n = #rows
    local avail = 760
    local par = CQF:GetParent()
    if par and par.GetHeight then
        local ph = math.floor((par:GetHeight() or 800) - 40)
        if ph > 200 and ph < avail then avail = ph end
    end
    local RH = 46
    if 52 + n * 46 > avail then
        RH = math.floor((avail - 52) / n)
        if RH < 24 then RH = 24 end
    end
    local two = RH >= 40
    local ROWW = CQF.__rowW
    local child = CQF.__child
    child:SetHeight(n * RH + 4)
    CQF:SetHeight(52 + n * RH)

    local firstTodo
    for i, rr in ipairs(rows) do
        if not ChainQuestDone(rr.q) then firstTodo = i break end
    end

    local pool = CQF.__rows
    while #pool < n do
        local rb = CreateFrame("Button", nil, child, "BackdropTemplate")
        rb:SetSize(ROWW, RH)
        if ns.hui and ns.hui.HuiCardFX then
            ns.hui.HuiCardFX(rb, 6, 2)
        end
        if not rb.__huiCard then
            rb.__plainCard = true
            rb:SetBackdrop({
                bgFile = "Interface\\Buttons\\WHITE8x8",
                edgeFile = "Interface\\Buttons\\WHITE8x8",
                edgeSize = 1,
            })
            rb:SetBackdropColor(1, 1, 1, 0.04)
            rb:SetBackdropBorderColor(1, 1, 1, 0.08)
        end
        rb:SetHighlightTexture("Interface\\Buttons\\WHITE8x8")
        rb:GetHighlightTexture():SetVertexColor(1, 1, 1, 0.07)
        if ns.hui and ns.hui.BuildRoundBorder then
            rb.__ring = ns.hui.BuildRoundBorder(rb, 6, { 1, 0.82, 0, 0.9 },
                rb, "OVERLAY", "both", 1)
            if rb.__ring then
                for _, t in ipairs(rb.__ring) do t:SetShown(false) end
            end
        end
        rb.nm = MakeFS(rb, 14, C_TEXT, "LEFT")
        rb.nm:SetWordWrap(false)
        rb.sub = MakeFS(rb, 12, C_GREY, "LEFT")
        rb.sub:SetWordWrap(false)
        rb.zone = MakeFS(rb, 12, C_GREY, "RIGHT")
        rb.zone:SetWordWrap(false)
        rb.tag = MakeFS(rb, 12, C_GOLD, "RIGHT")
        rb.tag:SetWordWrap(false)
        rb.tag:SetText(L["下一步"])
        rb.disc = rb:CreateTexture(nil, "ARTWORK")
        rb.disc:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\CheckDisc")
        rb.disc:SetSize(16, 16)
        rb.discT = rb:CreateTexture(nil, "OVERLAY")
        rb.discT:SetAllPoints(rb.disc)
        rb:SetScript("OnEnter", function(self)
            if not CardState(self, "hover") then
                self:SetBackdropColor(1, 1, 1, 0.08)
                if not self.__isCur then
                    self:SetBackdropBorderColor(1, 1, 1, 0.22)
                end
            end
            local t = self.__tip
            if t and GameTooltip then
                GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
                GameTooltip:ClearLines()
                GameTooltip:AddLine(t.nm, 1, 0.82, 0, true)
                GameTooltip:AddLine(t.st, 0.75, 0.75, 0.75, true)
                if t.locTxt and t.locTxt ~= "" then
                    GameTooltip:AddLine(t.locTxt, 0.75, 0.75, 0.75, true)
                end
                GameTooltip:Show()
            end
        end)
        rb:SetScript("OnLeave", function(self)
            if not CardState(self, "norm") then
                self:SetBackdropColor(1, 1, 1, 0.04)
                if self.__isCur then
                    self:SetBackdropBorderColor(1, 0.82, 0, 0.55)
                else
                    self:SetBackdropBorderColor(1, 1, 1, 0.08)
                end
            end
            if GameTooltip then GameTooltip:Hide() end
        end)
        pool[#pool + 1] = rb
    end

    local GREEN = { 0.30, 0.74, 0.45 }
    local INK = {
        done = { 0.043, 0.239, 0.102 },
        active = { 0.227, 0.165, 0 },
        todo = { 0.102, 0.102, 0.102 },
    }
    for i = 1, #pool do
        local rb = pool[i]
        if i <= n then
            local rr = rows[i]
            local done = ChainQuestDone(rr.q)
            local active = false
            if not done and DG.QuestState then
                active = DG.QuestState(rr.q) == "active"
            end
            local nm, nmOk
            if DG.QuestName then nm, nmOk = DG.QuestName(rr.q) end
            if not nmOk then
                if DG.RequestQuest then DG.RequestQuest(rr.q) end
                CQF.__pending[rr.q] = true
                nm = "……"
            end
            local loc = QuestLocOf(rr.q)
            local isCur = rr.q == qid0
            local stTag
            local stCol
            if done then
                stTag, stCol = L["已完成"], GREEN
            elseif i == firstTodo then
                stTag, stCol = L["下一步"], C_GOLD
            elseif active then
                stTag, stCol = L["进行中"], C_GOLD
            else
                stTag, stCol = L["可接"], C_GREY
            end
            local statHex = format("%02x%02x%02x",
                stCol[1] * 255 + 0.5, stCol[2] * 255 + 0.5, stCol[3] * 255 + 0.5)
            local locTxt = L["未收录位置"]
            if loc then
                local zname = ""
                if C_Map and C_Map.GetMapInfo then
                    local ok, mi = pcall(C_Map.GetMapInfo, loc[1])
                    if ok and mi and mi.name then zname = mi.name end
                end
                locTxt = zname .. format("(%.1f, %.1f)", loc[2] or 0, loc[3] or 0)
                if loc[4] and loc[4] > 0 then
                    locTxt = locTxt .. " · " .. format(L["%d 级可接"], loc[4])
                end
            end
            rb:ClearAllPoints()
            rb:SetHeight(RH)
            rb:SetWidth(ROWW)
            rb:SetPoint("TOPLEFT", child, "TOPLEFT", 0, -(i - 1) * RH)
            rb.nm:SetText(nm)
            rb.nm:ClearAllPoints()
            rb.sub:ClearAllPoints()
            rb.zone:ClearAllPoints()
            rb.tag:ClearAllPoints()
            rb.tag:SetPoint("CENTER", rb, "RIGHT", -45, 0)
            local isNext = two and i == firstTodo and not done
            if two then
                if isNext then
                    rb.nm:SetPoint("TOPLEFT", rb, "TOPLEFT", 12, -5)
                    rb.nm:SetPoint("RIGHT", rb, "RIGHT", -76, 0)
                    rb.sub:Show()
                    rb.sub:SetPoint("TOPLEFT", rb, "TOPLEFT", 12, -25)
                    rb.sub:SetPoint("RIGHT", rb, "RIGHT", -76, 0)
                    rb.sub:SetText(locTxt)
                    rb.tag:Show()
                else
                    rb.nm:SetPoint("TOPLEFT", rb, "TOPLEFT", 12, -5)
                    rb.nm:SetPoint("RIGHT", rb, "RIGHT", -34, 0)
                    rb.sub:Show()
                    rb.sub:SetPoint("TOPLEFT", rb, "TOPLEFT", 12, -25)
                    rb.sub:SetPoint("RIGHT", rb, "RIGHT", -34, 0)
                    rb.sub:SetText("|cff" .. statHex .. stTag .. "|r " .. locTxt)
                    rb.tag:Hide()
                end
                rb.zone:Hide()
            else
                rb.tag:Hide()
                rb.nm:SetPoint("LEFT", rb, "LEFT", 12, 0)
                rb.nm:SetPoint("RIGHT", rb, "RIGHT", -150, 0)
                rb.sub:Hide()
                rb.zone:Show()
                rb.zone:SetPoint("RIGHT", rb, "RIGHT", -34, 0)
                rb.zone:SetPoint("LEFT", rb, "RIGHT", -140, 0)
                rb.zone:SetText(locTxt)
            end
            rb.disc:ClearAllPoints()
            rb.disc:SetPoint("CENTER", rb, "RIGHT", -18, 0)
            rb.disc:Show()
            rb.discT:Show()
            local sym, ink
            if done then
                sym = "Interface\\AddOns\\DungeonsForever\\Media\\CheckMark"
                ink = INK.done
            elseif active then
                sym = "Interface\\AddOns\\DungeonsForever\\Media\\QMarkAsk"
                ink = INK.active
            else
                sym = "Interface\\AddOns\\DungeonsForever\\Media\\QMarkExcl"
                ink = INK.todo
            end
            rb.disc:SetVertexColor(stCol[1], stCol[2], stCol[3], 1)
            rb.discT:SetTexture(sym)
            rb.discT:SetVertexColor(ink[1], ink[2], ink[3], 1)
            rb.__isCur = isCur
            if rb.__ring then
                for _, t in ipairs(rb.__ring) do t:SetShown(isCur) end
            end
            if not rb.__huiCard then
                rb:SetBackdropColor(1, 1, 1, 0.04)
                if isCur then
                    rb:SetBackdropBorderColor(1, 0.82, 0, 0.55)
                else
                    rb:SetBackdropBorderColor(1, 1, 1, 0.08)
                end
            end
            if isCur then
                rb.nm:SetTextColor(Unpack(C_GOLD))
            elseif done then
                rb.nm:SetTextColor(Unpack(GREEN))
            else
                rb.nm:SetTextColor(Unpack(C_TEXT))
            end
            rb.__tip = { nm = nm, st = stTag, locTxt = locTxt }
            if loc then
                rb:SetScript("OnClick", function()
                    ns.PlaySound(1)
                    MarkQuest(rr.q, loc)
                end)
            else
                rb:SetScript("OnClick", function() end)
            end
            rb:Show()
        else
            rb:Hide()
        end
    end
end

local POP_WATCH, POP_WATCH_EVT = {}, nil

local function PopEscape(name)
    if type(UISpecialFrames) ~= "table" then return end
    for i = #UISpecialFrames, 1, -1 do
        if UISpecialFrames[i] == name then table.remove(UISpecialFrames, i) end
    end
    table.insert(UISpecialFrames, 1, name)
end

local function PopWatch(pop, exempt)
    for _, e in ipairs(POP_WATCH) do
        if e.pop == pop then
            e.exempt = exempt
            return
        end
    end
    POP_WATCH[#POP_WATCH + 1] = { pop = pop, exempt = exempt }
    if POP_WATCH_EVT then return end
    local ev = CreateFrame("Frame")
    POP_WATCH_EVT = ev
    ev:RegisterEvent("GLOBAL_MOUSE_DOWN")
    ev:SetScript("OnEvent", function()
        for i = #POP_WATCH, 1, -1 do
            local e = POP_WATCH[i]
            local p = e.pop
            if p and p.IsShown and p:IsShown()
                    and not (p.IsMouseOver and p:IsMouseOver()) then
                local ex = e.exempt
                if not (ex and ex()) then p:Hide() end
            end
        end
    end)
end

local function PopFullMask(parent, lvl, onClick)
    local m = CreateFrame("Frame", nil, parent)
    m:SetPoint("TOPLEFT", UIParent, "TOPLEFT", 0, 0)
    m:SetPoint("BOTTOMRIGHT", UIParent, "BOTTOMRIGHT", 0, 0)
    m:SetFrameLevel(lvl)
    m:EnableMouse(true)
    m:SetScript("OnMouseDown", onClick)
    m:Hide()
    return m
end

local function ChainPopup(qid)
    EnsureGD()
    local ci = ChainIndexOf(qid)
    if not ci then
        MarkQuest(qid, QuestLocOf(qid))
        return
    end
    if not CQF then
        local page = G.pageFrame
        if not page or (page.IsShown and not page:IsShown()) then
            page = _G.DungeonsForever_MainFrame or UIParent
        end
        local baseLv = (page.GetFrameLevel and type(page:GetFrameLevel()) == "number")
                       and page:GetFrameLevel() or 0
        local mask = PopFullMask(page, baseLv + 40, function()
            if CQF then CQF:Hide() end
        end)
        local pop = CreateFrame("Frame", "DFGearChainPop", page)
        pop:SetSize(420, 380)
        pop:SetFrameLevel(baseLv + 41)
        pop:EnableMouse(true)
        pop:Hide()
        if ns.hui and ns.hui.BuildRoundedBG then
            ns.hui.BuildRoundedBG(pop, 6, ns.hui.layer.L0, "both", true, 1)
        else
            Cardify(pop, nil, 2)
        end
        if ns.hui and ns.hui.SkinShadow then
            ns.hui.SkinShadow(pop, 16, 0.65, 8)
        end
        local ty = MakeFS(pop, 16, C_GOLD, "LEFT")
        ty:SetPoint("TOPLEFT", pop, "TOPLEFT", 14, -12)
        ty:SetText(L["任务链"])
        local sub = MakeFS(pop, 12, C_TEXT, "RIGHT")
        sub:SetWordWrap(false)
        sub:SetPoint("TOPRIGHT", pop, "TOPRIGHT", -14, -15)
        sub:SetPoint("LEFT", pop, "LEFT", 200, 0)
        local hint = MakeFS(pop, 11, C_DIM, "LEFT")
        hint:SetPoint("LEFT", ty, "RIGHT", 10, 1)
        hint:SetPoint("RIGHT", sub, "LEFT", -12, 0)
        hint:SetText(L["点击：在地图上标记"])
        local child = CreateFrame("Frame", nil, pop)
        child:SetSize(392, 10)
        child:SetPoint("TOPLEFT", pop, "TOPLEFT", 14, -40)
        child:SetPoint("BOTTOMRIGHT", pop, "BOTTOMRIGHT", -14, -12)
        CQF = pop
        CQF.__mask = mask
        CQF.__child = child
        CQF.__sub = sub
        CQF.__rows = {}
        CQF.__rowW = 392
        CQF.__render = ChainRender
        pop:SetScript("OnHide", function()
            if CQF.__mask then CQF.__mask:Hide() end
            ChainHookSync()
        end)
        pop:SetScript("OnShow", function()
            if CQF.__mask then CQF.__mask:Show() end
            ChainHookSync()
        end)
        if UISpecialFrames then
            PopEscape("DFGearChainPop")
        end
        PopWatch(pop)
    end
    CQF.__qid = qid
    CQF.__ci = ci
    CQF:ClearAllPoints()
    CQF:SetPoint("CENTER", CQF:GetParent(), "CENTER", 0, 0)
    if UISpecialFrames then PopEscape("DFGearChainPop") end
    CQF:Show()
    ChainRender()
end

local function MarkQuestSmart(qid)
    if ChainIndexOf(qid) then
        ChainPopup(qid)
        return
    end
    MarkQuest(qid, QuestLocOf(qid))
end

ns.GearChainIndexOf = function(qid)
    EnsureGD()
    return ChainIndexOf(qid)
end

ns.GearQuestLocOf = function(qid)
    EnsureGD()
    return QuestLocOf(qid)
end

ns.GearMarkQuestSmart = function(qid)
    EnsureGD()
    MarkQuestSmart(qid)
end

ns.GearDismissPopups = function()
    if CQF and CQF.IsShown and CQF:IsShown() then
        CQF:Hide()
        return true
    end
    if G.vendorPick and G.vendorPick.IsShown and G.vendorPick:IsShown() then
        G.VendorPickHide()
        return true
    end
    if G.attrPop and G.attrPop.IsShown and G.attrPop:IsShown() then
        G.SetAttrPop(false)
        return true
    end
    return false
end

local function GearVendorMsg(msg)
    if UIErrorsFrame and UIErrorsFrame.AddMessage then
        pcall(UIErrorsFrame.AddMessage, UIErrorsFrame, msg, 1, 0.4, 0.4)
    end
end

local function GearMarkVendor(loc)
    if type(loc) ~= "table" then
        GearVendorMsg(L["该商人的位置暂未收录"])
        return
    end
    local mapID = loc[1]
    if not mapID and loc[2] then
        mapID = ns.AreaMap and ns.AreaMap[loc[2]] or nil
        if not mapID and C_Map and C_Map.GetMapInfoFromAreaID then
            local ok, mi = pcall(C_Map.GetMapInfoFromAreaID, loc[2])
            mapID = ok and mi and mi.mapID or nil
        end
    end
    if not mapID then
        GearVendorMsg(L["该商人的位置暂未收录"])
        return
    end
    if UiMapPoint and UiMapPoint.CreateFromCoordinates
            and C_Map and C_Map.SetUserWaypoint
            and (not C_Map.CanSetUserWaypointOnMap
                 or C_Map.CanSetUserWaypointOnMap(mapID)) then
        local ok, pt = pcall(UiMapPoint.CreateFromCoordinates,
                             mapID, (loc[3] or 0) / 100, (loc[4] or 0) / 100)
        if ok and pt then
            pcall(C_Map.SetUserWaypoint, pt)
            if C_SuperTrack and C_SuperTrack.SetSuperTrackedUserWaypoint then
                pcall(C_SuperTrack.SetSuperTrackedUserWaypoint, false)
            end
        end
    end
    if C_Map and C_Map.OpenWorldMap then
        pcall(C_Map.OpenWorldMap, mapID)
    elseif OpenWorldMap then
        pcall(OpenWorldMap, mapID)
    end
end

local function GearZoneName(aid)
    if not aid or not C_Map or not C_Map.GetAreaInfo then return "" end
    local ok, name = pcall(C_Map.GetAreaInfo, aid)
    return (ok and name) or ""
end

local function GearVendorEnts(id)
    local GV = ns.EnsureGearVendors and ns.EnsureGearVendors() or ns.GearVendors
    local rows = GV and GV[id]
    if type(rows) ~= "table" or #rows == 0 then return nil end
    local f
    if UnitFactionGroup then
        local ok, eng = pcall(UnitFactionGroup, "player")
        if ok and eng == "Alliance" then f = "a"
        elseif ok and eng == "Horde" then f = "h" end
    end
    local out = {}
    for _, r in ipairs(rows) do
        local nid, zone, side, name = r[1], r[2], r[3], r[4]
        if not side or not f or side == f then
            local sp = ns.GearVendorSpawns and ns.GearVendorSpawns[nid]
            local loc
            if type(sp) == "table" then
                for _, s in ipairs(sp) do
                    if zone and s[1] == zone and s[2] then
                        loc = { s[2], s[1], s[3], s[4] }
                        break
                    end
                end
                if not loc then
                    for _, s in ipairs(sp) do
                        if s[2] then
                            loc = { s[2], s[1], s[3], s[4] }
                            break
                        end
                    end
                end
                if not loc and sp[1] then
                    loc = { nil, sp[1][1], sp[1][3], sp[1][4] }
                end
            end
            out[#out + 1] = { name = r[5] or name, zone = zone, loc = loc }
        end
    end
    return out
end

local function GearRareEnts(id)
    local rows = ns.GearRareSpawns and ns.GearRareSpawns[id]
    if type(rows) ~= "table" or #rows == 0 then return nil end
    local out = {}
    for _, r in ipairs(rows) do
        out[#out + 1] = {
            name = (r[6] and r[6] ~= "" and r[6] or L["稀有怪"])
                   .. format(" (%.1f, %.1f)", r[4], r[5]),
            zone = r[3],
            loc = { r[2], r[3], r[4], r[5] },
        }
    end
    return out
end

local PICK_PAD, PICK_ROW_H, PICK_GAP, PICK_W = 8, 22, 4, 216

function G.VendorPickHide()
    local pick = G.vendorPick
    if not pick then return end
    if pick:IsShown() then pick:Hide() end
    if pick.__shield then pick.__shield:Hide() end
end

function G.VendorPickShow(anchor, ents, title)
    local pick = G.vendorPick
    if pick and pick:IsShown() and pick.__anchor == anchor then
        G.VendorPickHide()
        return
    end
    if not (ns.hui and ns.hui.layer and ns.hui.BuildRoundedBG) then
        if ents and ents[1] then
            ns.PlaySound(1)
            GearMarkVendor(ents[1].loc)
        end
        return
    end
    if not pick then
        pick = CreateFrame("Button", "DFGearVendorPick", G.pageFrame,
                           "BackdropTemplate")
        pick:EnableMouse(true)
        pick:SetFrameLevel(515)
        local shield = PopFullMask(G.pageFrame, 514, function()
            G.VendorPickHide()
        end)
        pick.__shield = shield
        pick:SetScript("OnHide", function()
            if pick.__shield then pick.__shield:Hide() end
        end)
        PopEscape("DFGearVendorPick")
        PopWatch(pick, function()
            local cur = G.vendorPick
            local a = cur and cur.__anchor
            return a and a.IsMouseOver and a:IsMouseOver()
        end)
        ns.hui.BuildRoundedBG(pick, 6, ns.hui.layer.L3, "both", true, 1)
        pick.title = MakeFS(pick, 11, C_GOLD, "LEFT")
        pick.title:SetPoint("TOPLEFT", pick, "TOPLEFT", PICK_PAD + 4, -PICK_PAD)
        pick.__rows = {}
        G.vendorPick = pick
    end
    local rows = pick.__rows
    for k = 1, #ents do
        local e = ents[k]
        local r = rows[k]
        if not r then
            r = CreateFrame("Button", nil, pick, "BackdropTemplate")
            r:SetHeight(PICK_ROW_H)
            r.txt = MakeFS(r, 11, C_TEXT, "LEFT")
            r.txt:SetWordWrap(false)
            r.txt:SetPoint("LEFT", r, "LEFT", 6, 0)
            r.txt:SetPoint("RIGHT", r, "RIGHT", -6, 0)
            if ns.hui.BuildCapsule then
                r.__hov = ns.hui.BuildCapsule(r, 4, ns.hui.layer.L5, 0, 2)
                for _, ht in ipairs(r.__hov) do ht:Hide() end
            end
            r:SetScript("OnEnter", function(self)
                if self.__hov then
                    for _, ht in ipairs(self.__hov) do ht:Show() end
                end
            end)
            r:SetScript("OnLeave", function(self)
                if self.__hov then
                    for _, ht in ipairs(self.__hov) do ht:Hide() end
                end
            end)
            rows[k] = r
        end
        local zn = GearZoneName(e.zone)
        r.txt:SetText(zn ~= "" and (tostring(e.name or "?") .. " · " .. zn)
                      or tostring(e.name or "?"))
        if e.loc then
            r.txt:SetTextColor(Unpack(C_TEXT))
            r:SetScript("OnClick", function()
                ns.PlaySound(1)
                G.VendorPickHide()
                GearMarkVendor(e.loc)
            end)
        else
            r.txt:SetTextColor(Unpack(C_DIM))
            r:SetScript("OnClick", function()
                GearVendorMsg(L["该商人的位置暂未收录"])
            end)
        end
        r:ClearAllPoints()
        local per = 10
        local col = math.floor((k - 1) / per)
        local ri = (k - 1) % per
        local colW = PICK_W - PICK_PAD * 2
        r:SetPoint("TOPLEFT", pick, "TOPLEFT",
                   PICK_PAD + col * (colW + PICK_GAP),
                   -(PICK_PAD + 18 + ri * (PICK_ROW_H + PICK_GAP)))
        r:SetWidth(colW)
        r:Show()
    end
    for k = #ents + 1, #rows do
        rows[k]:Hide()
    end
    local vis = math.min(#ents, 10)
    local cols = math.max(1, math.ceil(#ents / 10))
    local colW = PICK_W - PICK_PAD * 2
    pick:SetWidth(PICK_PAD * 2 + cols * colW + (cols - 1) * PICK_GAP)
    pick:SetHeight(PICK_PAD + 18 + vis * PICK_ROW_H
                   + (vis - 1) * PICK_GAP + PICK_PAD)
    pick.title:SetText(title or L["选择要标记的商人"])
    pick:ClearAllPoints()
    pick.__anchor = anchor
    pick:SetPoint("TOPRIGHT", anchor, "BOTTOMRIGHT", 0, -2)
    if pick.__shield then
        pick.__shield:SetFrameLevel(pick:GetFrameLevel() - 1)
        pick.__shield:Show()
    end
    if UISpecialFrames then PopEscape("DFGearVendorPick") end
    pick:Show()
end

local function BuildRow(parent)
    local r = CreateFrame("Button", nil, parent)
    r:SetHeight(ROW_H)
    r:RegisterForClicks("LeftButtonUp", "RightButtonUp")
    Cardify(r, 4, 2)
    r.icon = r:CreateTexture(nil, "ARTWORK")
    r.icon:SetSize(32, 32)
    r.icon:SetPoint("LEFT", CARD_PAD, 0)
    r.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
    if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(r.icon) end
    r.name = MakeFS(r, 14, C_TEXT, "LEFT")
    r.name:SetPoint("TOPLEFT", CARD_PAD + 40, -3)
    r.name:SetWidth(180)
    r.name:SetWordWrap(false)
    r.sub = MakeFS(r, 12, C_DIM, "LEFT")
    r.sub:SetPoint("TOPLEFT", CARD_PAD + 40, -23)
    r.sub:SetWidth(180)
    r.sub:SetWordWrap(false)
    r.newTag = CreateFrame("Frame", nil, r)
    r.newTag:SetSize(34, 16)
    r.newTag:SetPoint("LEFT", r.name, "RIGHT", 4, 0)
    if ns.hui and ns.hui.BuildRoundedBG then
        ns.hui.BuildRoundedBG(r.newTag, 4, ns.hui.layer.L2, "both", true, 1)
    else
        Cardify(r.newTag, 3, 2)
    end
    r.newTag.tex = MakeFS(r.newTag, 12, C_GOLD, "CENTER")
    r.newTag.tex:SetAllPoints()
    r.newTag.tex:SetText(L["新增"])
    r.ilvl = MakeFS(r, 14, C_GREY, "CENTER")
    r.ilvl:SetPoint("LEFT", CARD_PAD + 214, 0)
    r.ilvl:SetWidth(56)
    r.req = MakeFS(r, 14, C_GREY, "CENTER")
    r.req:SetPoint("LEFT", CARD_PAD + 322, 0)
    r.req:SetWidth(56)
    r.meta = MakeFS(r, 14, C_GREY, "LEFT")
    r.meta:SetPoint("LEFT", CARD_PAD + 366, 0)
    r.meta:SetWidth(96)
    r.meta:SetWordWrap(false)
    r.src = MakeFS(r, 12, C_TEXT, "LEFT")
    r.src:SetPoint("TOPLEFT", CARD_PAD + 470, -3)
    r.src:SetPoint("RIGHT", r, "RIGHT", -(CARD_PAD + 34), 0)
    r.src:SetWordWrap(false)
    r.facIcon = r:CreateTexture(nil, "ARTWORK")
    r.facIcon:SetSize(16, 16)
    r.facIcon:SetPoint("TOPLEFT", CARD_PAD + 470, -9)
    r.facIcon:Hide()
    r.srcQ = MakeFS(r, 12, C_DIM, "LEFT")
    r.srcQ:SetWordWrap(false)
    r.srcQ:Hide()
    r.src2 = MakeFS(r, 12, C_DIM, "LEFT")
    r.src2:SetPoint("TOPLEFT", CARD_PAD + 470, -23)
    r.src2:SetPoint("RIGHT", r, "RIGHT", -(CARD_PAD + 34), 0)
    r.src2:SetWordWrap(false)
    r.star = CreateFrame("Button", nil, r)
    r.star:SetSize(24, 24)
    r.star:SetPoint("RIGHT", r, "RIGHT", -(CARD_PAD + 4), 0)
    r.star.tex = MakeFS(r.star, 20, C_GREY, "CENTER")
    r.star.tex:SetAllPoints()
    r.star:SetScript("OnClick", function()
        StarClick(r)
    end)
    r.star:SetScript("OnEnter", function()
        r.star:SetAlpha(1)
        local e = r.entry
        if e and e.id then
            GameTooltip:SetOwner(r.star, "ANCHOR_RIGHT")
            GameTooltip:ClearLines()
            GameTooltip:SetText(WishIs(e.id) and L["移出心愿清单"] or L["加入心愿清单"], 1, 1, 1)
            GameTooltip:Show()
        end
    end)
    r.star:SetScript("OnLeave", function()
        r.star:SetAlpha(1)
        TipOff()
    end)
    r:SetScript("OnEnter", function()
        r.__hover = true
        if r.__huiCard or r.__plainCard then CardState(r, "hover") end
    end)
    r:SetScript("OnLeave", function()
        r.__hover = false
        if r.__huiCard or r.__plainCard then CardState(r, "norm") end
    end)
    local function RowClick(_, btn)
        local e = r.entry
        if not e then return end
        if btn == "RightButton" then
            if e.id then StarClick(r) end
            return
        end
        if e.kind == "set" then
            if G.setOpen == e.skey then G.setOpen = nil else G.setOpen = e.skey end
            GDB().setOpen = G.setOpen
            G.Refresh()
            ns.PlaySound(1)
            return
        end
        if not e.id then return end
        if IsShiftKeyDown() and DG.InsertItemLink then
            DG.InsertItemLink(e.id)
            return
        end
        if type(IsControlKeyDown) == "function" and IsControlKeyDown() and DG.TryOn then
            DG.TryOn(e.id)
            return
        end
        if e.inst and e.inst.id and ns.ShowDungeonDetail then
            ns.PlaySound(1)
            ns.ShowDungeonDetail(e.inst.id)
            return
        end
        local qid = GD_SRC_Q and e.id and GD_SRC_Q[e.id]
        if qid then
            ns.PlaySound(1)
            EnsureGD()
            MarkQuestSmart(qid)
        end
    end
    r:SetScript("OnClick", RowClick)
    r.tipZone = CreateFrame("Button", nil, r)
    r.tipZone:RegisterForClicks("LeftButtonUp", "RightButtonUp")
    r.tipZone:SetPoint("TOPLEFT", r, "TOPLEFT", CARD_PAD, 0)
    r.tipZone:SetPoint("BOTTOMRIGHT", r, "BOTTOMLEFT", CARD_PAD + 40 + 180 + 4, 0)
    r.tipZone:SetScript("OnEnter", function()
        local e = r.entry
        if e and e.id then ItemTip(r.tipZone, e.id) end
    end)
    r.tipZone:SetScript("OnLeave", TipOff)
    r.tipZone:SetScript("OnClick", RowClick)
    r.srcZone = CreateFrame("Button", nil, r)
    r.srcZone:RegisterForClicks("LeftButtonUp")
    r.srcZone:SetPoint("TOPLEFT", r.src, "TOPLEFT", -2, 2)
    r.srcZone:SetHeight(30)
    r.srcZone:SetScript("OnEnter", function()
        local e = r.entry
        if not e then return end
        local qid = e.id and GD_SRC_Q and GD_SRC_Q[e.id]
        local loc = qid and QuestLocOf(qid)
        GameTooltip:SetOwner(r.srcZone, "ANCHOR_RIGHT")
        GameTooltip:ClearLines()
        if qid and ChainIndexOf(qid) then
            GameTooltip:AddLine(L["点击：查看任务链"], 1, 0.82, 0, true)
            if type(loc) == "table" and loc[1] and loc[2] then
                local mname = ""
                if C_Map and C_Map.GetMapInfo then
                    local ok, mi = pcall(C_Map.GetMapInfo, loc[1])
                    if ok and mi and mi.name then mname = mi.name end
                end
                GameTooltip:AddLine(mname .. format(" (%.1f, %.1f)", loc[2], loc[3]), 1, 1, 1, true)
            end
        elseif type(loc) == "table" and loc[1] and loc[2] then
            GameTooltip:AddLine(L["点击：在地图上标记"], 1, 0.82, 0, true)
            local mname = ""
            if C_Map and C_Map.GetMapInfo then
                local ok, mi = pcall(C_Map.GetMapInfo, loc[1])
                if ok and mi and mi.name then mname = mi.name end
            end
            GameTooltip:AddLine(mname .. format(" (%.1f, %.1f)", loc[2], loc[3]), 1, 1, 1, true)
        elseif e.inst and e.inst.id and ns.ShowDungeonDetail then
            GameTooltip:AddLine(L["点击：打开该副本掉落详情"], 1, 0.82, 0, true)
            if e.instName and e.instName ~= "" then
                GameTooltip:AddLine(e.instName, 1, 1, 1, true)
            end
        else
            local rents = e.id and GearRareEnts(e.id) or nil
            if rents and #rents > 0 then
                GameTooltip:AddLine(format(L["点击：查看稀有怪位置（%d 处刷新）"],
                                           #rents), 1, 0.82, 0, true)
            else
                local vents = e.id and GearVendorEnts(e.id) or nil
                if vents and #vents > 0 then
                GameTooltip:AddLine(format(L["点击：查看商人位置（%d 位商人）"], #vents), 1, 0.82, 0, true)
            else
                local src = e.id and GD_SRC and GD_SRC[e.id]
                local place = type(src) == "string" and select(2, src:match("^(.-)|(.*)$")) or nil
                local mid = place and PlaceMapID(place)
                local zname
                if not mid and place then
                    zname = place:match("^(.-)·") or place
                    mid = PlaceZoneID(place)
                end
                if mid then
                    GameTooltip:AddLine(format(L["点击：打开%s的地图"], zname or place), 1, 0.82, 0, true)
                else
                    return
                end
            end
            end
        end
        GameTooltip:Show()
    end)
    r.srcZone:SetScript("OnLeave", TipOff)
    r.srcZone:SetScript("OnClick", function()
        local e = r.entry
        if not e then return end
        local qid = e.id and GD_SRC_Q and GD_SRC_Q[e.id]
        if qid and ChainIndexOf(qid) then
            ns.PlaySound(1)
            ChainPopup(qid)
            return
        end
        local loc = qid and QuestLocOf(qid)
        if type(loc) == "table" and loc[1] then
            ns.PlaySound(1)
            EnsureGD()
            MarkQuest(qid, loc)
            return
        end
        if e.inst and e.inst.id and ns.ShowDungeonDetail then
            ns.PlaySound(1)
            ns.ShowDungeonDetail(e.inst.id)
            return
        end
        local rents = e.id and GearRareEnts(e.id) or nil
        if rents and #rents > 0 then
            ns.PlaySound(1)
            if #rents == 1 and rents[1].loc then
                GearMarkVendor(rents[1].loc)
            else
                G.VendorPickShow(r.srcZone, rents, L["选择要标记的稀有怪刷新点"])
            end
            return
        end
        local vents = e.id and GearVendorEnts(e.id) or nil
        if vents and #vents > 0 then
            ns.PlaySound(1)
            if #vents == 1 and vents[1].loc then
                GearMarkVendor(vents[1].loc)
            else
                G.VendorPickShow(r.srcZone, vents)
            end
            return
        end
        local src = e.id and GD_SRC and GD_SRC[e.id]
        local place = type(src) == "string" and select(2, src:match("^(.-)|(.*)$")) or nil
        local mid = place and PlaceMapID(place)
        if not mid and place then mid = PlaceZoneID(place) end
        if mid then
            ns.PlaySound(1)
            if C_Map and C_Map.OpenWorldMap then
                pcall(C_Map.OpenWorldMap, mid)
            elseif OpenWorldMap then
                pcall(OpenWorldMap, mid)
            end
        end
    end)
    return r
end

local PAINT_FIRST = 2
local PAINT_BATCH = 2

function G.PaintList(full)
    if not G.built then return end
    local cur = (G.pagesData or {})[G.page or 1] or {}
    local total = #cur
    local token = (G.__paintToken or 0) + 1
    G.__paintToken = token
    local pool = G.rowPool or {}
    for i = total + 1, #pool do
        local r = pool[i]
        if r then
            r.entry = nil
            r:Hide()
        end
    end
    if total == 0 then
        G.emptyFs:SetText(G.EmptyHint())
        G.emptyFs:Show()
    else
        G.emptyFs:Hide()
    end
    G.PaintCats()
    G.PaintChips()
    G.PaintPager()
    G.PaintChrome()
    if total == 0 then
        G.__paintedSig = G.__viewSig
        return
    end
    local idx = 0
    local y = 0
    local function step(first)
        local pt0 = debugprofilestop()
        local upto = idx + (first and PAINT_FIRST or PAINT_BATCH)
        if upto > total then upto = total end
        while idx < upto do
            idx = idx + 1
            local r = pool[idx]
            if not r then
                r = BuildRow(G.listHost)
                pool[idx] = r
            end
            local e = cur[idx]
            r.entry = e
            r:ClearAllPoints()
            r:SetPoint("TOPLEFT", G.listHost, "TOPLEFT", 0, -y)
            r:SetPoint("RIGHT", G.listHost, "RIGHT", 0, 0)
            PaintRow(r)
            local h = r.__h or ROW_H
            r:SetHeight(h)
            y = y + h
        end
        local pd = debugprofilestop() - pt0
        if pd > 3 then
            G.__paintMs = (G.__paintMs or "")
                .. string.format("%.2fs:%.0f ", (debugprofilestop() - (G.__paintT0 or pt0)) / 1000, pd)
        end
        return idx >= total
    end
    if full or not ns.IdleJobs then
        while idx < total do
            step(false)
        end
    else
        step(true)
    end
    if not full and idx < total then
        local stepper = G.__paintStepper
        if not stepper then
            stepper = CreateFrame("Frame", nil, G.listHost)
            stepper:Hide()
            G.__paintStepper = stepper
        end
        stepper:SetScript("OnUpdate", function(s)
            if G.__paintToken ~= token then
                s:SetScript("OnUpdate", nil)
                s:Hide()
                return
            end
            local mf = _G.DungeonsForever_MainFrame
            if mf and mf.IsShown and not mf:IsShown() then return end
            if G.listHost and not G.listHost:IsVisible() then return end
            if step(false) then
                s:SetScript("OnUpdate", nil)
                s:Hide()
            end
        end)
        stepper:Show()
    end
    G.__paintedSig = G.__viewSig
end

function G.PaintCats()
    local counts, total = CatCounts()
    local function paintNode(key, nOverride)
        local b = G.catRows[key]
        if not b then return end
        b.n:SetText(tostring(nOverride or counts[key] or 0))
        local sel = (G.cat == key)
        if sel then
            b.txt:SetTextColor(Unpack(C_GOLD))
        elseif b.__clsColor then
            b.txt:SetTextColor(Unpack(b.__clsColor))
        else
            b.txt:SetTextColor(Unpack(C_TEXT))
        end
        if b.__huiCard or b.__plainCard then
            CardState(b, sel and "norm" or (b:IsMouseOver() and "hover" or "flat"))
        end
    end
    paintNode("ALL", total)
    for _, key in ipairs(G.catOrder or {}) do
        if key:sub(1, 4) == "SET:" then
            local rest = key:sub(5)
            local si = rest:match(":(%d+)$")
            if si then
                local set = RS and RS.sets and RS.sets[tonumber(si)]
                paintNode(key, set and (#(set.ids or {}) .. " 件") or "")
            else
                local n = 0
                if RS and type(RS.sets) == "table" then
                    local bt, cls = rest:match("^([%w]+):([%a]+)$")
                    for _, set in ipairs(RS.sets) do
                        if bt and cls then
                            if (set.batch or "t1") == bt and set.class == cls then n = n + 1 end
                        elseif (set.batch or "t1") == rest then
                            n = n + 1
                        end
                    end
                end
                paintNode(key, n .. " 套")
            end
        elseif key ~= "ALL" and key ~= "WISH" and key ~= "SETS" then
            paintNode(key)
        end
    end
    local wishN = 0
    for _ in pairs(WishTable()) do wishN = wishN + 1 end
    paintNode("WISH", wishN)
    local setShown = 0
    if RS and type(RS.sets) == "table" then
        setShown = #RS.sets
    end
    paintNode("SETS", setShown .. " 套")
end

function G.EmptyHint()
    if G.cat == "WISH" then
        return L["还没有收藏的装备：在装备列表悬停行星标，点 ☆ 即可加入心愿清单"]
    end
    if IsSetCat(G.cat) then
        return L["该筛选下暂无套装"]
    end
    local totalAll = #(G.catalog or {})
    if totalAll == 0 then return L["装备目录为空"] end
    return format(L["当前筛选无匹配装备（全库共 %d 件，可点品质标签取消筛选）"], totalAll)
end

local function FoldTable()
    local s = GDB()
    if type(s.fold) ~= "table" then s.fold = {} end
    return s.fold
end

local function BuildCats(parent)
    local LayoutCats
    local rawCounts = {}
    local cidx = 0
    for _, e in ipairs(G.catalog or {}) do
        local keys = PathKeysOf(e.c, e.u, e.s)
        for i = 1, #keys do
            rawCounts[keys[i]] = (rawCounts[keys[i]] or 0) + 1
        end
        cidx = cidx + 1
        if cidx % 1200 == 0 then coroutine.yield() end
    end
    local function MakeCat(key, label, depth)
        local b = CreateFrame("Button", nil, parent)
        b:SetHeight(22)
        Cardify(b, 4, 2)
        local pad = depth and (CARD_PAD + depth * 12) or CARD_PAD
        b.txt = MakeFS(b, 14, C_TEXT, "LEFT")
        b.txt:SetPoint("LEFT", pad, 0)
        b.txt:SetText(label)
        b.txt:SetWordWrap(false)
        b.n = MakeFS(b, 14, C_GREY, "RIGHT")
        b.n:SetPoint("RIGHT", -CARD_PAD, 0)
        b:SetScript("OnEnter", function()
            if G.cat ~= key and (b.__huiCard or b.__plainCard) then CardState(b, "hover") end
        end)
        b:SetScript("OnLeave", function()
            if G.cat ~= key and (b.__huiCard or b.__plainCard) then CardState(b, "flat") end
        end)
        b:SetScript("OnClick", function()
            G.SetCat(key)
            ns.PlaySound(1)
        end)
        G.catRows[key] = b
        G.catLabels[key] = label
        return b
    end
    local nodes = {}
    G.catOrder = {}
    G.catFold = {}
    local function Node(key, label, depth, foldable, pre)
        local b = MakeCat(key, label, depth)
        local n = { f = b, h = 22, key = key, pre = pre or 0 }
        nodes[#nodes + 1] = n
        G.catOrder[#G.catOrder + 1] = key
        if foldable then
            G.catFold[#G.catFold + 1] = key
            b:HookScript("OnClick", function()
                local t = FoldTable()
                if t[key] then t[key] = nil else t[key] = true end
                G.PaintCatArrows()
                LayoutCats()
            end)
        end
        return n
    end
    local root = {}
    root[#root + 1] = Node("WISH", L["心愿清单"], nil, nil, 8)
    root[#root + 1] = Node("ALL", L["全部装备"])
    for _, pair in ipairs(GD and GD.cls or {}) do
        local cid = pair[1]
        if cid == 2 or cid == 4 then
            local kids = {}
            if cid == 2 then
                for _, g in ipairs(W_GROUPS) do
                    local gKids = {}
                    local gTotal = 0
                    for _, u in ipairs(g.leaves) do
                        local n = rawCounts["c:2:" .. g.key .. ":u" .. u] or 0
                        if n > 0 then
                            gTotal = gTotal + n
                            gKids[#gKids + 1] = Node("c:2:" .. g.key .. ":u" .. u,
                                SUB_LABEL["2:" .. u] or ("#" .. u), 2)
                        end
                    end
                    if gTotal > 0 then
                        local gn = Node("c:2:" .. g.key, g.lk, 1, true, 2)
                        gn.kids = gKids
                        kids[#kids + 1] = gn
                    end
                end
            else
                for _, u in ipairs({ 4, 3, 2, 1 }) do
                    local tKids = {}
                    for _, s in ipairs(ARMOR_SLOTS) do
                        local n = rawCounts["c:4:t" .. u .. ":" .. s] or 0
                        if n > 0 then
                            tKids[#tKids + 1] = Node("c:4:t" .. u .. ":" .. s,
                                SLOT_LABEL[s] or s, 2)
                        end
                    end
                    local tn = Node("c:4:t" .. u, SUB_LABEL["4:" .. u] or ("#" .. u), 1, true, 2)
                    tn.kids = tKids
                    kids[#kids + 1] = tn
                end
                if (rawCounts["c:4:tR"] or 0) > 0 then
                    kids[#kids + 1] = Node("c:4:tR", L["圣物"], 1, nil, 2)
                end
                local mKids = {}
                local mTotal = 0
                for _, p in ipairs(TM_SLOTS) do
                    local n = rawCounts["c:4:tM:" .. p[1]] or 0
                    if n > 0 then
                        mTotal = mTotal + n
                        mKids[#mKids + 1] = Node("c:4:tM:" .. p[1], p[2], 2)
                    end
                end
                local n5 = rawCounts["c:4:tM:u5"] or 0
                if n5 > 0 then
                    mTotal = mTotal + n5
                    mKids[#mKids + 1] = Node("c:4:tM:u5", SUB_LABEL["4:5"] or L["装饰品"], 2)
                end
                local nr = rawCounts["c:4:tM:rest"] or 0
                if nr > 0 then
                    mTotal = mTotal + nr
                    mKids[#mKids + 1] = Node("c:4:tM:rest", L["杂件"], 2)
                end
                if mTotal > 0 then
                    local mn = Node("c:4:tM", L["其它"], 1, true, 2)
                    mn.kids = mKids
                    kids[#kids + 1] = mn
                end
            end
            local cn = Node("c:" .. cid, pair[2], 0, true, 4)
            cn.kids = kids
            root[#root + 1] = cn
        end
    end
    local setKids = {}
    if RS and type(RS.sets) == "table" then
        local batches = RS.batches
        if type(batches) ~= "table" or #batches == 0 then
            batches = { { key = "t1", label = RS.raid or "" } }
        end
        for _, bt in ipairs(batches) do
            local bKids = {}
            local anyCls = false
            for _, set in ipairs(RS.sets) do
                if (set.batch or "t1") == bt.key and set.class and set.class ~= "" then
                    anyCls = true
                    break
                end
            end
            if anyCls then
                for _, cls in ipairs(SET_CLS_ORDER) do
                    local n = 0
                    for _, set in ipairs(RS.sets) do
                        if (set.batch or "t1") == bt.key and set.class == cls then n = n + 1 end
                    end
                    if n > 0 then
                        local kb = Node("SET:" .. bt.key .. ":" .. cls, L[SET_CLS_ZH[cls]], 2)
                        local cc = RAID_CLASS_COLORS and RAID_CLASS_COLORS[cls]
                        if cc and cc.r then
                            kb.f.txt:SetTextColor(cc.r, cc.g, cc.b)
                            kb.f.__clsColor = { cc.r, cc.g, cc.b }
                        end
                        bKids[#bKids + 1] = kb
                    end
                end
            else
                for idx, set in ipairs(RS.sets) do
                    if (set.batch or "t1") == bt.key then
                        local kb = Node(SetKeyOf(set, idx), set.name or ("#" .. idx), 2)
                        if set.revealed == false then
                            kb.f.txt:SetTextColor(Unpack(C_DIM))
                        end
                        bKids[#bKids + 1] = kb
                    end
                end
            end
            if #bKids > 0 then
                local bn = Node("SET:" .. bt.key, bt.label or bt.key, 1, true, 2)
                bn.kids = bKids
                setKids[#setKids + 1] = bn
            end
        end
    end
    local sn = Node("SETS", L["套装"], nil, true, 8)
    sn.kids = setKids
    root[#root + 1] = sn
    local scroll = 0
    local contentH = 0
    local hostH = 0
    local y
    local gen = 0
    local function Place(f, h)
        if not f then
            y = y - (h or 22)
            return
        end
        local show = hostH <= 0
        if not show then
            local d = -y
            show = d >= -0.5 and (d + h) <= hostH + 0.5
        end
        f.__laid = gen
        if show then
            f:ClearAllPoints()
            f:SetPoint("TOPLEFT", parent, "TOPLEFT", 0, y)
            f:SetPoint("RIGHT", parent, "RIGHT", 0, 0)
            f:SetHeight(h)
            f:Show()
        else
            f:Hide()
        end
        y = y - h
    end
    local function WalkNode(n, fn)
        if n.pre > 0 then fn(nil, n.pre) end
        fn(n.f, n.h)
        if n.kids and FoldTable()[n.key] then
            for _, k in ipairs(n.kids) do WalkNode(k, fn) end
        end
    end
    local function Walk(fn)
        for _, n in ipairs(root) do WalkNode(n, fn) end
    end
    LayoutCats = function()
        gen = gen + 1
        local hv = parent.GetHeight and parent:GetHeight()
        if type(hv) == "number" and hv > 0 then hostH = hv end
        contentH = 0
        Walk(function(_, h) contentH = contentH + h end)
        local maxS = math.max(0, contentH - hostH)
        if scroll > maxS then scroll = maxS end
        if scroll < 0 then scroll = 0 end
        y = -4 + scroll
        Walk(function(f, h) Place(f, h) end)
        for _, n in ipairs(nodes) do
            if n.f.__laid ~= gen then n.f:Hide() end
        end
    end
    parent:EnableMouseWheel(true)
    parent:SetScript("OnMouseWheel", function(_, delta)
        scroll = scroll - delta * 48
        LayoutCats()
    end)
    parent:HookScript("OnShow", function() LayoutCats() end)
    G.PaintCatArrows()
    LayoutCats()
end

function G.PaintCatArrows()
    for _, key in ipairs(G.catFold or {}) do
        local b = G.catRows[key]
        if b then
            b.txt:SetText((FoldTable()[key] and "- " or "+ ") .. (G.catLabels[key] or ""))
        end
    end
end

function G.SetCat(key)
    if G.cat == key then return end
    G.cat = key
    GDB().cat = key
    G.page = 1
    GDB().page = 1
    if G.attrPop then G.SetAttrPop(false) end
    G.Refresh()
    ns.PlaySound(1)
end

function G.BuildChips(parent)
    G.filterBtn = NewButton(parent, L["过滤器"], 50, 24, 14)
    G.filterBtn:GetFontString():SetTextColor(Unpack(C_TEXT))
    G.filterBtn:SetScript("OnClick", function()
        if G.attrPop and G.attrPop:IsShown() then
            G.SetAttrPop(false)
        else
            G.SetAttrPop(true)
        end
    end)
    G.ddBtn = G.filterBtn
end

function G.PaintChips()
    if G.filterBtn then
        local srcOn = false
        if type(G.srcSet) == "table" then
            for _, key in ipairs(SRC_ORDER) do
                if not G.srcSet[key] then srcOn = true break end
            end
        end
        local active = next(G.qset) ~= nil or (G.ilvlMin or G.ilvlMax) ~= nil
            or srcOn == true
        G.filterBtn:GetFontString():SetTextColor(Unpack(active and C_GOLD or C_TEXT))
    end
    if G.headSort then
        for key, hd in pairs(G.headSort) do
            local on = G.sort == key
            hd.fs:SetText(L[key == "ilvl" and "物品等级" or "需要等级"])
            hd.fs:SetTextColor(Unpack(on and C_GOLD or C_GREY))
            if on then
                if G.sortDir == 1 then
                    hd.arrow:SetTexCoord(0, 0.5, 0, 1)
                else
                    hd.arrow:SetTexCoord(0.5, 1, 0, 1)
                end
                hd.arrow:SetVertexColor(1, 0.82, 0, 1)
            else
                hd.arrow:SetTexCoord(0, 1, 0, 1)
                hd.arrow:SetVertexColor(0.55, 0.57, 0.62, 1)
            end
        end
    end
end

local function QSelected(q)
    if next(G.qset) == nil then return true end
    return G.qset[q] ~= nil
end

local function QToggle(q)
    if next(G.qset) == nil then
        for _, other in ipairs(QUALITY_ORDER) do
            if other ~= q then G.qset[other] = true end
        end
    else
        if G.qset[q] then G.qset[q] = nil else G.qset[q] = true end
        local n = 0
        for _ in pairs(G.qset) do n = n + 1 end
        if n == #QUALITY_ORDER then G.qset = {} end
    end
    SaveQset()
end

local function SaveIlvlRange()
    GDB().ilvlMin = G.ilvlMin
    GDB().ilvlMax = G.ilvlMax
    G.page = 1
    GDB().page = 1
    G.Refresh()
    G.PaintChips()
end

function G.SyncFilterPop()
    if not G.filterRows then return end
    for q, bt in pairs(G.filterRows) do
        local on = QSelected(q)
        bt.ring:SetShown(not on)
        bt.disc:SetShown(on)
        bt.tick:SetShown(on)
        if on then
            local col = G.qcolors[q] or { 0.91, 0.78, 0.42 }
            bt.disc:SetVertexColor(0.91, 0.78, 0.42)
            bt.tick:SetVertexColor(1, 1, 1, 1)
            bt.label:SetTextColor(col[1], col[2], col[3], 1)
        else
            bt.ring:SetVertexColor(0.42, 0.41, 0.38, 0.9)
            bt.label:SetTextColor(0.55, 0.58, 0.65, 1)
        end
    end
    local ub = G.useTypeBtn
    if ub then
        local on = G.useType and true or false
        ub.ring:SetShown(not on)
        ub.disc:SetShown(on)
        ub.tick:SetShown(on)
        if on then
            ub.disc:SetVertexColor(0.91, 0.78, 0.42)
            ub.tick:SetVertexColor(1, 1, 1, 1)
            ub.label:SetTextColor(Unpack(C_TEXT))
        else
            ub.ring:SetVertexColor(0.42, 0.41, 0.38, 0.9)
            ub.label:SetTextColor(0.55, 0.58, 0.65, 1)
        end
    end
    if G.srcBtns then
        for key, bt in pairs(G.srcBtns) do
            local on = false
            if type(G.srcSet) == "table" and G.srcSet[key] then on = true end
            bt.ring:SetShown(not on)
            bt.disc:SetShown(on)
            bt.tick:SetShown(on)
            if on then
                bt.disc:SetVertexColor(0.91, 0.78, 0.42)
                bt.tick:SetVertexColor(1, 1, 1, 1)
                bt.label:SetTextColor(Unpack(C_TEXT))
            else
                bt.ring:SetVertexColor(0.42, 0.41, 0.38, 0.9)
                bt.label:SetTextColor(0.55, 0.58, 0.65, 1)
            end
        end
    end
    if G.ilvlMinBox then
        G.ilvlMinBox:SetText(G.ilvlMin and tostring(G.ilvlMin) or "")
        G.ilvlMaxBox:SetText(G.ilvlMax and tostring(G.ilvlMax) or "")
    end
end

function G.SetAttrPop(on)
    if not G.attrPop then return end
    G.attrMask:SetShown(on)
    G.attrPop:SetShown(on)
    if on then
        G.attrPop:ClearAllPoints()
        G.attrPop:SetPoint("TOPRIGHT", G.filterBtn, "BOTTOMRIGHT", 0, -4)
        G.SyncFilterPop()
        if UISpecialFrames then PopEscape("DFGearAttrPop") end
    end
end

function G.BuildAttrPop()
    if G.attrPop or not G.pageFrame then return end
    local page = G.pageFrame
    local baseLv = (page.GetFrameLevel and type(page:GetFrameLevel()) == "number") and page:GetFrameLevel() or 0
    local mask = PopFullMask(page, baseLv + 30, function()
        G.SetAttrPop(false)
    end)
    G.attrMask = mask
    local popH = 24 + 32 + 24 + #QUALITY_ORDER * 26 + 26 + 6 + 18 + #SRC_ORDER * 26 + 8
    local pop = CreateFrame("Frame", "DFGearAttrPop", page)
    pop:SetSize(170, popH)
    pop:EnableMouse(true)
    pop:SetFrameLevel(baseLv + 31)
    pop:SetScript("OnHide", function()
        if G.attrMask then G.attrMask:Hide() end
    end)
    pop:Hide()
    if ns.hui and ns.hui.BuildRoundedBG then
        ns.hui.BuildRoundedBG(pop, 6, ns.hui.layer.L3, "both", true, 1)
    else
        Cardify(pop, nil, 2)
    end
    G.attrPop = pop
    PopEscape("DFGearAttrPop")
    PopWatch(pop, function()
        return G.filterBtn and G.filterBtn.IsMouseOver
               and G.filterBtn:IsMouseOver() or false
    end)
    local ty = MakeFS(pop, 14, C_GOLD, "LEFT")
    ty:SetPoint("TOPLEFT", pop, "TOPLEFT", 10, -8)
    ty:SetText(L["等级范围"])
    G.ilvlMinBox = ns.CreateEditBox(pop, 56)
    G.ilvlMinBox:SetPoint("TOPLEFT", pop, "TOPLEFT", 10, -30)
    G.ilvlMinBox:SetNumeric(true)
    G.ilvlMaxBox = ns.CreateEditBox(pop, 56)
    G.ilvlMaxBox:SetPoint("LEFT", G.ilvlMinBox, "RIGHT", 18, 0)
    G.ilvlMaxBox:SetNumeric(true)
    local dash = MakeFS(pop, 14, C_TEXT, "CENTER")
    dash:SetPoint("LEFT", G.ilvlMinBox, "RIGHT", 0, 0)
    dash:SetPoint("RIGHT", G.ilvlMaxBox, "LEFT", 0, 0)
    dash:SetText("-")
    local rb = CreateFrame("Button", nil, pop, "BackdropTemplate")
    rb:SetSize(48, 20)
    rb:SetPoint("TOPRIGHT", pop, "TOPRIGHT", -8, -7)
    rb.__huiKeepTextColor = true
    if ns.hui and ns.hui.SkinButton then ns.hui.SkinButton(rb) end
    rb.label = MakeFS(rb, 14, C_TEXT, "CENTER")
    rb.label:SetAllPoints()
    rb.label:SetText(L["重置"])
    rb.label:SetTextColor(0.92, 0.28, 0.28, 1)
    rb:SetScript("OnClick", function()
        G.qset = {}
        GDB().qset = {}
        G.ilvlMin = nil
        G.ilvlMax = nil
        GDB().ilvlMin = nil
        GDB().ilvlMax = nil
        G.useType = false
        GDB().useType = false
        G.srcSet = {}
        for _, key in ipairs(SRC_ORDER) do G.srcSet[key] = true end
        GDB().srcSet = G.srcSet
        G.search = ""
        if G.searchEb then G.searchEb:SetText("") end
        G.SyncFilterPop()
        G.page = 1
        GDB().page = 1
        G.Refresh()
        G.PaintChips()
        ns.PlaySound(1)
    end)
    local function EditCommit(box, setter)
        local v = tonumber(box:GetText())
        if v ~= nil then v = math.floor(v) end
        if v ~= nil and v < 0 then v = nil end
        setter(v)
        SaveIlvlRange()
    end
    G.ilvlMinBox:SetScript("OnEnterPressed", function()
        EditCommit(G.ilvlMinBox, function(v) G.ilvlMin = v end)
        G.ilvlMinBox:ClearFocus()
    end)
    G.ilvlMaxBox:SetScript("OnEnterPressed", function()
        EditCommit(G.ilvlMaxBox, function(v) G.ilvlMax = v end)
        G.ilvlMaxBox:ClearFocus()
    end)
    local qy = MakeFS(pop, 14, C_GOLD, "LEFT")
    qy:SetPoint("TOPLEFT", pop, "TOPLEFT", 10, -60)
    qy:SetText(L["稀有程度"])
    G.filterRows = {}
    local function MakeRow(idx, label, col, onClick)
        local bt = CreateFrame("Button", nil, pop)
        bt:SetSize(156, 26)
        bt:SetPoint("TOPLEFT", pop, "TOPLEFT", 7, -84 - (idx - 1) * 26)
        local boxF = CreateFrame("Frame", nil, bt)
        boxF:SetSize(18, 18)
        boxF:SetPoint("LEFT", bt, "LEFT", 4, 0)
        bt.ring = boxF:CreateTexture(nil, "ARTWORK")
        bt.ring:SetAllPoints()
        bt.ring:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\CheckRing")
        bt.disc = boxF:CreateTexture(nil, "ARTWORK")
        bt.disc:SetAllPoints()
        bt.disc:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\CheckDisc")
        bt.tick = boxF:CreateTexture(nil, "OVERLAY")
        bt.tick:SetAllPoints()
        bt.tick:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\CheckMark")
        bt.label = MakeFS(bt, 14, C_TEXT, "LEFT")
        bt.label:SetPoint("LEFT", boxF, "RIGHT", 7, 0)
        bt.label:SetText(label)
        bt.label:SetTextColor(col[1], col[2], col[3], 1)
        bt:SetScript("OnClick", onClick)
        return bt
    end
    local function MakeCheckRow(y, label, onClick)
        local bt = CreateFrame("Button", nil, pop)
        bt:SetSize(156, 26)
        bt:SetPoint("TOPLEFT", pop, "TOPLEFT", 7, -y)
        local bx = CreateFrame("Frame", nil, bt)
        bx:SetSize(18, 18)
        bx:SetPoint("LEFT", bt, "LEFT", 4, 0)
        bt.ring = bx:CreateTexture(nil, "ARTWORK")
        bt.ring:SetAllPoints()
        bt.ring:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\CheckRing")
        bt.disc = bx:CreateTexture(nil, "ARTWORK")
        bt.disc:SetAllPoints()
        bt.disc:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\CheckDisc")
        bt.tick = bx:CreateTexture(nil, "OVERLAY")
        bt.tick:SetAllPoints()
        bt.tick:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\CheckMark")
        bt.label = MakeFS(bt, 14, C_TEXT, "LEFT")
        bt.label:SetPoint("LEFT", bx, "RIGHT", 7, 0)
        bt.label:SetText(label)
        bt:SetScript("OnClick", onClick)
        return bt
    end
    local function SrcToggle(key)
        if type(G.srcSet) ~= "table" then G.srcSet = {} end
        if G.srcSet[key] then G.srcSet[key] = nil else G.srcSet[key] = true end
        GDB().srcSet = G.srcSet
        G.SyncFilterPop()
        G.PaintChips()
        G.page = 1
        GDB().page = 1
        G.Refresh()
        ns.PlaySound(1)
    end
    for i, q in ipairs(QUALITY_ORDER) do
        local col = Q_COLORS[q] or { 0.7, 0.7, 0.7 }
        if GetItemQualityColor then
            local ok, r, g, b = pcall(GetItemQualityColor, q)
            if ok and type(r) == "number" then col = { r, g, b } end
        end
        G.qcolors[q] = col
        G.filterRows[q] = MakeRow(i, QUALITY_LABEL[q], col, function()
            QToggle(q)
            G.SyncFilterPop()
            G.PaintChips()
            G.page = 1
            GDB().page = 1
            G.Refresh()
            ns.PlaySound(1)
        end)
    end
    local uy = 84 + #QUALITY_ORDER * 26 + 4
    local ub = CreateFrame("Button", nil, pop)
    ub:SetSize(156, 26)
    ub:SetPoint("TOPLEFT", pop, "TOPLEFT", 7, -uy)
    local boxF = CreateFrame("Frame", nil, ub)
    boxF:SetSize(18, 18)
    boxF:SetPoint("LEFT", ub, "LEFT", 4, 0)
    ub.ring = boxF:CreateTexture(nil, "ARTWORK")
    ub.ring:SetAllPoints()
    ub.ring:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\CheckRing")
    ub.disc = boxF:CreateTexture(nil, "ARTWORK")
    ub.disc:SetAllPoints()
    ub.disc:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\CheckDisc")
    ub.tick = boxF:CreateTexture(nil, "OVERLAY")
    ub.tick:SetAllPoints()
    ub.tick:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\CheckMark")
    ub.label = MakeFS(ub, 14, C_TEXT, "LEFT")
    ub.label:SetPoint("LEFT", boxF, "RIGHT", 7, 0)
    ub.label:SetText(L["只显示可用种类"])
    ub:SetScript("OnClick", function()
        G.useType = not G.useType
        GDB().useType = G.useType
        G.SyncFilterPop()
        G.page = 1
        GDB().page = 1
        G.Refresh()
        ns.PlaySound(1)
    end)
    G.useTypeBtn = ub
    local sy = uy + 26 + 6
    local sty = MakeFS(pop, 14, C_GOLD, "LEFT")
    sty:SetPoint("TOPLEFT", pop, "TOPLEFT", 10, -sy)
    sty:SetText(L["来源"])
    G.srcBtns = {}
    for i, key in ipairs(SRC_ORDER) do
        G.srcBtns[key] = MakeCheckRow(sy + 18 + (i - 1) * 26, SRC_LABEL[key],
                                      function() SrcToggle(key) end)
    end
end

function G.BuildPager(parent)
    G.pgPrev = NewButton(parent, L["上一页"], 62, 24, 14)
    G.pgPrev:GetFontString():SetTextColor(Unpack(C_TEXT))
    G.pgPrev:SetScript("OnClick", function()
        if (G.page or 1) > 1 then
            G.page = G.page - 1
            GDB().page = G.page
            G.PaintList()
        end
    end)
    G.pgNext = NewButton(parent, L["下一页"], 62, 24, 14)
    G.pgNext:GetFontString():SetTextColor(Unpack(C_TEXT))
    G.pgNext:SetScript("OnClick", function()
        if (G.page or 1) < (G.pages or 1) then
            G.page = G.page + 1
            GDB().page = G.page
            G.PaintList()
        end
    end)
    G.pgNums = {}
    for i = 1, 9 do
        local b = NewButton(parent, tostring(i), 28, 24, 14)
        b:SetScript("OnClick", function()
            if b.page then
                G.page = b.page
                GDB().page = G.page
                G.PaintList()
            end
        end)
        b:Hide()
        G.pgNums[i] = b
    end
    G.pgJump = ns.CreateEditBox(parent, 44)
    G.pgJump:SetNumeric(true)
    G.pgJump:SetScript("OnEnterPressed", function()
        local v = tonumber(G.pgJump:GetText())
        G.pgJump:ClearFocus()
        if v and G.pages and v >= 1 and v <= G.pages then
            G.page = math.floor(v)
            GDB().page = G.page
            G.PaintList()
        end
    end)
    G.pgGo = NewButton(parent, L["确定"], 44, 24, 14)
    G.pgGo:GetFontString():SetTextColor(Unpack(C_TEXT))
    G.pgGo:SetScript("OnClick", function()
        local v = tonumber(G.pgJump:GetText())
        if v and G.pages and v >= 1 and v <= G.pages then
            G.page = math.floor(v)
            GDB().page = G.page
            G.PaintList()
        end
    end)
    G.pgTotal = MakeFS(parent, 14, C_GREY, "RIGHT")
end

function G.PaintPager()
    local page = G.page or 1
    local pages = G.pages or 1
    G.pgPrev:SetEnabled(page > 1)
    G.pgNext:SetEnabled(page < pages)
    local slots
    if pages <= 9 then
        slots = {}
        for i = 1, pages do slots[#slots + 1] = i end
    else
        local w1 = math.min(math.max(page - 2, 3), pages - 6)
        local w5 = w1 + 4
        slots = { 1 }
        slots[#slots + 1] = (w1 == 3) and 2 or -1
        for i = w1, w5 do slots[#slots + 1] = i end
        slots[#slots + 1] = (w5 == pages - 2) and (pages - 1) or -1
        slots[#slots + 1] = pages
    end
    local prev = G.pgPrev
    for i = 1, 9 do
        local b = G.pgNums[i]
        local p = slots[i]
        if p then
            b:ClearAllPoints()
            b:SetPoint("LEFT", prev, "RIGHT", 8, 0)
            prev = b
            if p == -1 then
                b.page = nil
                b:SetEnabled(false)
                b:GetFontString():SetText("...")
                b:GetFontString():SetTextColor(Unpack(C_GREY))
                b:Show()
            else
                b.page = p
                b:SetEnabled(p ~= page)
                b:GetFontString():SetText(tostring(p))
                b:GetFontString():SetTextColor(Unpack(p == page and C_GOLD or C_TEXT))
                b:Show()
            end
        else
            b:Hide()
        end
    end
    G.pgNext:ClearAllPoints()
    G.pgNext:SetPoint("LEFT", prev, "RIGHT", 8, 0)
    if G.cat == "SETS" then
        local setN = RS and (RS.total or #(RS.sets or {})) or 0
        G.pgTotal:SetText(format(L["第 %d / %d 页 · 共 %d 套"], page, pages, setN))
    else
        G.pgTotal:SetText(format(L["第 %d / %d 页 · 共 %d 件"], page, pages, #(G.view or {})))
    end
end

function G.PaintChrome()
    local setView = IsSetCat(G.cat)
    local special = G.cat == "WISH" or setView
    if G.filterBtn then G.filterBtn:SetShown(not special) end
    if G.sortRow then G.sortRow:SetShown(not special) end
    if G.headRow then G.headRow:SetShown(not setView) end
    if G.wishClear then G.wishClear:SetShown(G.cat == "WISH") end
    if G.pageRight then
        local top
        if G.cat == "WISH" then
            top = CARD_PAD + TITLE_ZONE + HEAD_ZONE
        elseif setView then
            top = CARD_PAD + TITLE_ZONE
        else
            top = CARD_PAD + TITLE_ZONE + CHIP_ZONE + SORT_ZONE + HEAD_ZONE
        end
        if G.listHost then
            G.listHost:ClearAllPoints()
            G.listHost:SetPoint("TOPLEFT", G.pageRight, "TOPLEFT", CARD_PAD, -top)
            G.listHost:SetPoint("BOTTOMRIGHT", G.pageRight, "BOTTOMRIGHT", -CARD_PAD, CARD_PAD + 30)
        end
    end
end

local function ViewSig()
    local function setKeys(t)
        if type(t) ~= "table" or next(t) == nil then return "-" end
        local ks = {}
        for k in pairs(t) do ks[#ks + 1] = tostring(k) end
        table.sort(ks)
        return table.concat(ks, ",")
    end
    return table.concat({
        tostring(G.cat), tostring(G.sort), tostring(G.sortDir),
        tostring(G.ilvlMin), tostring(G.ilvlMax),
        tostring(G.useType), tostring(G.search), tostring(G.setOpen),
        tostring(G.pageSize), tostring(G.__viewVer or 0),
        setKeys(G.attrs), setKeys(G.qset), setKeys(G.srcSet),
    }, "|")
end

local function SortLessFor(mode, dir)
    if dir == -1 then
        return function(a, b)
            local x, y = a.__sk, b.__sk
            if x ~= y then return x > y end
            return a[1] < b[1]
        end
    end
    return function(a, b)
        local x, y = a.__sk, b.__sk
        if x ~= y then return x < y end
        return a[1] < b[1]
    end
end

local function SortedCatalog()
    local c = G.catalog or {}
    local mode, dir = G.sort, G.sortDir
    if G.__sortRef == c and G.__sortMode == mode and G.__sortDir == dir
            and G.__sorted and #G.__sorted == #c then
        return G.__sorted
    end
    local arr = G.__sorted or {}
    G.__sorted = arr
    if mode == "name" then
        for i = 1, #c do arr[i] = c[i] end
        for i = #c + 1, #arr do arr[i] = nil end
        for i = 1, #arr do
            local r = arr[i]
            r.__sk = r[2] or ""
        end
        table.sort(arr, SortLessFor("name", dir))
    else
        if G.__catRef ~= c then
            G.__catRef = c
            G.__catAsc = true
            for i = 2, #c do
                if c[i - 1][1] > c[i][1] then G.__catAsc = false break end
            end
        end
        if G.__catAsc then
            local bk = G.__bk
            if not bk then
                bk = {}
                G.__bk = bk
                for k = 0, 255 do bk[k] = {} end
            end
            for k = 0, 255 do
                local b = bk[k]
                for i = #b, 1, -1 do b[i] = nil end
            end
            local useIlvl = (mode == "ilvl")
            for i = 1, #c do
                local r = c[i]
                local k = useIlvl and r.ilvl or r.req
                if type(k) ~= "number" then k = 0 end
                if k < 0 then k = 0 elseif k > 255 then k = 255 end
                local b = bk[k]
                b[#b + 1] = r
            end
            local w = 0
            if dir == -1 then
                for k = 255, 0, -1 do
                    local b = bk[k]
                    for i = 1, #b do w = w + 1; arr[w] = b[i] end
                end
            else
                for k = 0, 255 do
                    local b = bk[k]
                    for i = 1, #b do w = w + 1; arr[w] = b[i] end
                end
            end
            for i = w + 1, #arr do arr[i] = nil end
        else
            for i = 1, #c do arr[i] = c[i] end
            for i = #c + 1, #arr do arr[i] = nil end
            local useIlvl = (mode == "ilvl")
            for i = 1, #arr do
                local r = arr[i]
                r.__sk = useIlvl and r.ilvl or r.req
            end
            table.sort(arr, SortLessFor(mode, dir))
        end
    end
    G.__sortRef, G.__sortMode, G.__sortDir = c, mode, dir
    return arr
end

local function StartViewPipeline(gen, full)
    local out, i, stage, src
    local cCounts, cTotal, cidx
    if G.cat == "WISH" then
        out = WishViewEntries()
        i = 0
        stage = "counts"
    elseif IsSetCat(G.cat) then
        out = SetsViewEntries()
        i = 0
        stage = "counts"
    else
        out = {}
        i = 0
        stage = "sortfirst"
    end
    local f = G.__pipeFrame
    if not f then
        f = CreateFrame("Frame", nil, G.listHost)
        f:Hide()
        G.__pipeFrame = f
    end
    f:SetScript("OnUpdate", function(s)
        if G.__viewGen ~= gen then
            s:SetScript("OnUpdate", nil)
            s:Hide()
            return
        end
        if stage == "sortfirst" then
            src = SortedCatalog()
            stage = "filter"
            return
        end
        if stage == "filter" then
            local t0 = debugprofilestop()
            while i < #src do
                i = i + 1
                local r = src[i]
                if PassFilters(r) then out[#out + 1] = r end
                if debugprofilestop() - t0 > 4 then return end
            end
            stage = "counts"
            return
        end
        if stage == "counts" then
            if not cCounts then cCounts, cTotal, cidx = {}, 0, 0 end
            local cc = G.catalog or {}
            local t0 = debugprofilestop()
            while cidx < #cc do
                cidx = cidx + 1
                local r = cc[cidx]
                if CountPass(r) then
                    cTotal = cTotal + 1
                    local keys = PathKeysOf(r.c, r.u, r.s)
                    for k = 1, #keys do
                        cCounts[keys[k]] = (cCounts[keys[k]] or 0) + 1
                    end
                end
                if debugprofilestop() - t0 > 4 then return end
            end
            G.__countCache = { cCounts, cTotal }
            G.__countSig = G.__viewSig
            stage = "apply"
            return
        end
        if stage == "apply" then
            G.view = out
            if IsSetCat(G.cat) then
                G.pagesData = ChunkByHeight(out, (G.pageSize or 20) * ROW_H)
            else
                G.pagesData = ChunkByRows(out)
            end
            G.pages = math.max(1, #G.pagesData)
            if (G.page or 1) > G.pages then G.page = G.pages end
            stage = "paint"
            return
        end
        s:SetScript("OnUpdate", nil)
        s:Hide()
        G.__pipeActive = nil
        G.PaintList(full)
        if G.__pipeRestart then
            G.__pipeRestart = nil
            G.Refresh()
        end
    end)
    G.__pipeActive = true
    G.__pipeT = debugprofilestop()
    f:Show()
end

function G.Refresh(full)
    if not G.built then return end
    G.VendorPickHide()
    local nowT = debugprofilestop()
    if not full and G.__lastRefreshT and nowT - G.__lastRefreshT < 150 then return end
    G.__lastRefreshT = nowT
    local sig = ViewSig()
    if not full and sig == G.__viewSig and G.__viewReady and G.view and G.pagesData
            and G.__paintedSig == sig then
        return
    end
    if G.__pipeActive and G.__pipeFrame and G.__pipeFrame:IsVisible()
            and nowT - (G.__pipeT or nowT) < 1000 then
        G.__pipeRestart = true
        return
    end
    G.__viewSig = sig
    G.__viewReady = true
    G.__viewGen = (G.__viewGen or 0) + 1
    StartViewPipeline(G.__viewGen, full)
end

local function QueueRefresh()
    if G.__repaintQueued then return end
    G.__repaintQueued = true
    if type(C_Timer) == "table" and type(C_Timer.After) == "function" then
        C_Timer.After(2, function()
            G.__repaintQueued = false
            if not G.built then return end
            if G.pageFrame and G.pageFrame:IsShown() then
                G.Refresh()
            else
                G.__dirty = true
            end
        end)
    else
        G.__repaintQueued = false
        G.Refresh()
    end
end

function G.OnItemData(id)
    if G.__tipOwner and G.__tipId == id and GameTooltip
            and GameTooltip:IsShown() and GameTooltip:GetOwner() == G.__tipOwner then
        ItemTip(G.__tipOwner, id)
    end
    if not recs[id] then return end
    local r = recs[id]
    if r then r.stats = nil end
    BumpView()
    QueueRefresh()
end

function G.EnsureListener()
    ns.EvtPool = ns.EvtPool or {}
    if ns.EvtPool.gearItem then return end
    local ev = CreateFrame("Frame")
    ev:RegisterEvent("GET_ITEM_INFO_RECEIVED")
    pcall(ev.RegisterEvent, ev, "QUEST_DATA_LOAD_RESULT")
    local pendIds, pendQ, queued = {}, false, nil
    local function flush()
        queued = nil
        if pendQ then
            pendQ = false
            BumpView()
            QueueRefresh()
        end
        if #pendIds > 0 then
            for i = 1, #pendIds do G.OnItemData(pendIds[i]) end
            pendIds = {}
        end
    end
    ev:SetScript("OnEvent", function(_, event, arg1, success)
        if event == "QUEST_DATA_LOAD_RESULT" then
            if not arg1 then return end
            pendQ = true
        else
            if success == false or not arg1 then return end
            pendIds[#pendIds + 1] = arg1
        end
        if type(C_Timer) == "table" and type(C_Timer.After) == "function" then
            if not queued then queued = C_Timer.After(0, flush) end
        else
            flush()
        end
    end)
    ns.EvtPool.gearItem = ev
end

function G.StartWarm()
    G.EnsureListener()
end

function G.StartIconWarm()
    if G.__iconWarm then return end
    G.__iconWarm = true
    G.__iconWarmDone = nil
    G.__iconWarmN = 0
    EnsureGD()
    local holder = CreateFrame("Frame", nil, UIParent)
    holder:SetFrameStrata("BACKGROUND")
    holder:SetPoint("BOTTOMLEFT", UIParent, "BOTTOMLEFT", 1, 1)
    holder:SetSize(24, 24)
    holder:Show()
    local tex = {}
    for i = 1, 6 do
        tex[i] = holder:CreateTexture()
        tex[i]:SetAllPoints()
        tex[i]:Show()
    end
    local seen = {}
    local list = {}
    for i = 1, #GD_ITEMS do
        local ic = GD_ITEMS[i][ROW_FIELDS.icon]
        if ic and ic ~= "" and not seen[ic] then
            seen[ic] = true
            list[#list + 1] = "Interface\\Icons\\" .. ic
        end
    end
    local n = #list
    G.__iconWarmTotal = n
    local idx = 0
    holder:SetScript("OnUpdate", function(s)
        if idx >= n then
            G.__iconWarmDone = true
            G.__iconWarmN = n
            s:SetScript("OnUpdate", nil)
            s:Hide()
            return
        end
        local mf = _G.DungeonsForever_MainFrame
        local shown = mf and mf.IsShown and mf:IsShown()
        if shown then
            local av = mf.GetAlpha and mf:GetAlpha()
            if type(av) ~= "number" or av >= 0.05 then
                for k = 1, 6 do
                    if idx < n then
                        idx = idx + 1
                        tex[(idx % 6) + 1]:SetTexture(list[idx])
                    end
                end
                G.__iconWarmN = idx
                return
            end
        end
        for k = 1, 48 do
            if idx < n then
                idx = idx + 1
                tex[(idx % 6) + 1]:SetTexture(list[idx])
            end
        end
        G.__iconWarmN = idx
    end)
end

local function GlyphWarmFeed()
    local seen, chars = {}, {}
    local function feed(s)
        if type(s) ~= "string" then return end
        for u in s:gmatch("[\1-\127\194-\244][\128-\191]*") do
            if not seen[u] then
                seen[u] = true
                chars[#chars + 1] = u
            end
        end
    end
    for i = 1, #GD_ITEMS do feed(GD_ITEMS[i][2]) end
    for _, v in pairs(SLOT_LABEL) do feed(v) end
    for _, v in pairs(SUB_LABEL) do feed(v) end
    for _, v in pairs(BIND_LABEL) do feed(v) end
    for _, v in pairs(STAT_LABELS) do feed(v) end
    feed(format(L["未识别物品 #%d"], 888))
    return chars
end

function G.StartTexWarm()
    if G.__texWarm then return end
    G.__texWarm = true
    local B = "Interface/AddOns/DungeonsForever/Media/"
    local list = {}
    local function p(s)
        list[#list + 1] = s
    end
    for _, r in ipairs({ 4, 6, 8, 10, 12 }) do
        p(B .. "LibHUI/HUIGlassFill" .. r)
        p(B .. "LibHUI/HUIGlassRing" .. r)
    end
    p(B .. "LibHUI/HUIGlassShadow")
    p(B .. "LibHUI/HUIGlassGlow")
    p(B .. "LibHUI/HUIPillL")
    p(B .. "LibHUI/HUIPillR")
    p(B .. "LibHUI/HUIRoundCorner")
    p(B .. "LibHUI/HUIRoundCornerFill")
    p(B .. "LibHUI/HUICircle")
    p(B .. "LibHUI/HUIRoundRectMask")
    p(B .. "LibHUI/HUIRoundImageMask")
    p(B .. "textures/YY_close")
    p(B .. "textures/DF_Settings")
    p(B .. "textures/arrow")
    p(B .. "textures/route_arrow")
    p(B .. "textures/route_dial")
    p(B .. "textures/BossSkull")
    p(B .. "textures/CheckDisc")
    p(B .. "textures/CheckMark")
    p(B .. "textures/CheckRing")
    p(B .. "textures/CheckTicks2")
    p(B .. "textures/EntryPin")
    p(B .. "DungeonsForever.blp")
    p(B .. "MapDoor.blp")
    local n = #list
    local idx = 0
    local holder = CreateFrame("Frame", nil, UIParent)
    holder:SetFrameStrata("BACKGROUND")
    holder:SetPoint("BOTTOMLEFT", UIParent, "BOTTOMLEFT", 1, 1)
    holder:SetSize(16, 16)
    holder:Show()
    local tex = holder:CreateTexture()
    tex:SetAllPoints()
    tex:Show()
    holder:SetScript("OnUpdate", function(s)
        if idx >= n then
            s:SetScript("OnUpdate", nil)
            s:Hide()
            return
        end
        local mf = _G.DungeonsForever_MainFrame
        if mf and mf.IsShown and mf:IsShown() then return end
        for _ = 1, 4 do
            if idx < n then
                idx = idx + 1
                tex:SetTexture(list[idx])
            end
        end
    end)
end

function G.StartGlyphWarm()
    if G.__glyphWarm then return end
    G.__glyphWarm = true
    EnsureGD()
    local chars = GlyphWarmFeed()
    local n = #chars
    if n == 0 then return end
    local holder = CreateFrame("Frame", nil, UIParent)
    holder:SetFrameStrata("BACKGROUND")
    holder:SetPoint("BOTTOMLEFT", UIParent, "BOTTOMLEFT", 1, 1)
    holder:SetSize(2, 2)
    holder:Show()
    local fs1 = MakeFS(holder, 16, nil)
    local fs2 = MakeFS(holder, 14, nil)
    local fs3 = MakeFS(holder, 12, nil)
    local fs4 = MakeFS(holder, 11, nil)
    local ga = (DungeonsForeverDB and DungeonsForeverDB.dfGlyphA) or 0.02
    pcall(function()
        fs1:SetAlpha(ga)
        fs2:SetAlpha(ga)
        fs3:SetAlpha(ga)
        fs4:SetAlpha(ga)
    end)
    fs1:SetAllPoints()
    fs2:SetAllPoints()
    fs3:SetAllPoints()
    fs4:SetAllPoints()
    local idx = 0
    holder:SetScript("OnUpdate", function(s)
        if idx >= n then
            s:SetScript("OnUpdate", nil)
            s:Hide()
            return
        end
        local to = idx + 64
        if to > n then to = n end
        local chunk = table.concat(chars, "", idx + 1, to)
        idx = to
        fs1:SetText(chunk)
        fs2:SetText(chunk)
        fs3:SetText(chunk)
        fs4:SetText(chunk)
    end)
end

function G.StartDataWarm()
    if DungeonsForeverDB and DungeonsForeverDB.dfDataWarm == false then return end
    if G.__dataWarm then return end
    G.__dataWarm = true
    EnsureGD()
    local ids = {}
    for i = 1, #GD_ITEMS do
        local id = GD_ITEMS[i][1]
        if id then ids[#ids + 1] = id end
    end
    local n = math.min(#ids, #ids)
    if n == 0 then return end
    local idx = 0
    local holder = CreateFrame("Frame", nil, UIParent)
    holder:Hide()
    holder:SetScript("OnUpdate", function(s)
        local mf = _G.DungeonsForever_MainFrame
        if mf and mf.IsShown and mf:IsShown() then
            local av = mf.GetAlpha and mf:GetAlpha()
            if type(av) ~= "number" or av >= 0.05 then return end
        end
        for _ = 1, 4 do
            if idx >= n then
                s:SetScript("OnUpdate", nil)
                return
            end
            idx = idx + 1
            G.AskItem(ids[idx])
        end
    end)
end

function G.BuildCatalog()
    EnsureGD()
    for k in pairs(recs) do recs[k] = nil end
    for i = 1, #GD_ITEMS do
        local it = GD_ITEMS[i]
        setmetatable(it, ROW_MT)
        recs[it[1]] = it
        if not G.__noYield and i % 2000 == 0 and coroutine.running() then coroutine.yield() end
    end
    local srcOf = {}
    local order = {}
    if ns.DungeonData and type(ns.DungeonData.dungeons) == "table" then
        for _, d in ipairs(ns.DungeonData.dungeons) do order[#order + 1] = d end
    end
    G.instOrder = {}
    for idx, d in ipairs(order) do G.instOrder[d.id] = idx end
    local function NoteSrc(id, d, boss)
        if srcOf[id] then return end
        srcOf[id] = { inst = d, boss = boss or "" }
    end
    for _, d in ipairs(order) do
        local loot = (ns.DungeonLoot or {})[d.id]
        if loot then
            for _, s in ipairs(loot) do
                local its = s[5]
                for k = 1, #(its or {}) do NoteSrc(its[k][1], d, s[2] or "") end
            end
        end
    end
    for instKey, loot in pairs(ns.DungeonLoot or {}) do
        local known = false
        for _, d in ipairs(order) do if d.id == instKey then known = true break end end
        if not known then
            for _, s in ipairs(loot) do
                local its = s[5]
                for k = 1, #(its or {}) do NoteSrc(its[k][1], nil, s[2] or "") end
            end
        end
    end
    G.srcOf = srcOf
    G.catalog = GD_ITEMS
end

local function RefreshSoon()
    if G.__refreshQueued then return end
    G.__refreshQueued = true
    if ns.IdleJobs then
        ns.IdleJobs.Urgent(function()
            G.__refreshQueued = nil
            if G.__lastRefreshT and debugprofilestop() - G.__lastRefreshT < 250 then
                return true
            end
            G.Refresh()
            G.__lastRefreshT = debugprofilestop()
            return true
        end)
    else
        G.__refreshQueued = nil
        G.Refresh()
    end
end

function G.Open()
    if not G.built then return end
    ns.OpenPerf.Begin("装备库")
    G.__paintT0 = debugprofilestop()
    G.__paintMs = nil
    G.StartWarm()
    G.StartIconWarm()
    if G.__dirty then
        G.__dirty = false
    end
    RefreshSoon()
    if not G.__memOpened and DungeonsForeverDB and DungeonsForeverDB.dfMemProbe then
        G.__memOpened = true
        C_Timer.After(1, function()
            if ns.MemMark then ns.MemMark("gearOpen") end
        end)
    end
end

function G.Build(page)
    if G.built or G.building then return end
    if not page or not page.SetParent then return end
    G.building = true
    ns.OpenPerf.Begin("装备库·首建")
    ns.PhasedStart(28, function()
    local cfg = GDB()
    G.cat = cfg.cat or "ALL"
    G.sort = (cfg.sort == "ilvl" or cfg.sort == "name") and cfg.sort or "req"
    G.sortDir = (cfg.sortDir == -1 or cfg.sortDir == 1) and cfg.sortDir or 1
    G.ilvlMin = (type(cfg.ilvlMin) == "number" and cfg.ilvlMin > 0) and cfg.ilvlMin or nil
    G.ilvlMax = (type(cfg.ilvlMax) == "number" and cfg.ilvlMax > 0) and cfg.ilvlMax or nil
    G.attrs = {}
    if type(cfg.attrs) == "table" then
        for key in pairs(cfg.attrs) do
            if STAT_LABELS[key] then G.attrs[key] = true end
        end
    elseif type(cfg.attr) == "string" and cfg.attr ~= "any" and STAT_LABELS[cfg.attr] then
        G.attrs[cfg.attr] = true
    end
    G.qset = {}
    if type(cfg.qset) == "table" then
        for _, q in ipairs(cfg.qset) do G.qset[q] = true end
    end
    G.qcolors = {}
    G.useType = cfg.useType and true or false
    G.srcSet = {}
    if type(cfg.srcSet) == "table" then
        for key in pairs(cfg.srcSet) do
            if SRC_LABEL[key] then G.srcSet[key] = true end
        end
    elseif cfg.showUnknown == false then
        for _, key in ipairs(SRC_ORDER) do
            if key ~= "unknown" then G.srcSet[key] = true end
        end
    else
        for _, key in ipairs(SRC_ORDER) do
            G.srcSet[key] = true
        end
    end
    G.setOpen = cfg.setOpen
    if not cfg.foldInit then
        FoldTable().SETS = true
        cfg.foldInit = true
    end
    G.search = ""
    G.page = cfg.page or 1
    G.rowPool = {}
    G.catRows = {}
    G.catHeads = {}
    G.catLabels = {}
    G.pagesData = {}
    G.__asked = {}
    coroutine.yield()

    G.BuildCatalog()
    ns.OpenPerf.Mark("目录")
    coroutine.yield()
    G.EnsureListener()
    coroutine.yield()

    local py, pb = PAGE_TOP, PAGE_BOTTOM
    G.pageFrame = page

    local left = CreateFrame("Frame", nil, page)
    Cardify(left, nil, 1)
    left:SetPoint("TOPLEFT", page, "TOPLEFT", PAGE_INSET, -py)
    left:SetPoint("BOTTOMRIGHT", page, "BOTTOMLEFT", PAGE_INSET + LEFT_W, pb)
    coroutine.yield()

    local search = ns.CreateEditBox(left, LEFT_W - 2 * CARD_PAD - 54)
    search:SetPoint("TOPLEFT", left, "TOPLEFT", CARD_PAD, -CARD_PAD)
    G.searchEb = search
    search:SetScript("OnTextChanged", function()
        G.search = search:GetText():lower()
        G.page = 1
        GDB().page = 1
        G.Refresh()
    end)
    coroutine.yield()

    local catHost = CreateFrame("Frame", nil, left)
    catHost:SetPoint("TOPLEFT", left, "TOPLEFT", CARD_PAD, -(CARD_PAD + 26))
    catHost:SetPoint("BOTTOMRIGHT", left, "BOTTOMRIGHT", -CARD_PAD, CARD_PAD)
    coroutine.yield()
    BuildCats(catHost)
    if not G.catRows[G.cat] then
        G.cat = "ALL"
        GDB().cat = "ALL"
    end
    coroutine.yield()

    local rightX = PAGE_INSET + LEFT_W + CARD_GAP
    local right = CreateFrame("Frame", nil, page)
    Cardify(right, nil, 1)
    right:SetPoint("TOPLEFT", page, "TOPLEFT", rightX, -py)
    right:SetPoint("BOTTOMRIGHT", page, "BOTTOMRIGHT", -PAGE_INSET, pb)
    coroutine.yield()

    G.wishClear = NewButton(right, L["清空"], 52, 24, 14)
    G.wishClear:GetFontString():SetTextColor(Unpack(C_GREY))
    G.wishClear:SetPoint("TOPLEFT", left, "TOPLEFT", CARD_PAD + LEFT_W - 2 * CARD_PAD - 50, -(CARD_PAD))
    G.wishClear:SetScript("OnClick", function()
        if IsShiftKeyDown() then
            local t = WishTable()
            for k in pairs(t) do t[k] = nil end
            G.Refresh()
            ns.PlaySound(1)
        else
            GameTooltip:SetOwner(G.wishClear, "ANCHOR_RIGHT")
            GameTooltip:ClearLines()
            GameTooltip:SetText(L["Shift+点击确认清空"], 1, 1, 1)
            GameTooltip:Show()
        end
    end)
    G.wishClear:SetScript("OnLeave", TipOff)
    G.wishClear:Hide()
    coroutine.yield()

    G.BuildChips(left)
    G.filterBtn:ClearAllPoints()
    G.filterBtn:SetPoint("TOPLEFT", left, "TOPLEFT", CARD_PAD + LEFT_W - 2 * CARD_PAD - 50, -(CARD_PAD))
    coroutine.yield()
    G.BuildAttrPop()
    G.pageRight = right
    coroutine.yield()

    local listTop = CARD_PAD + TITLE_ZONE + CHIP_ZONE + SORT_ZONE + HEAD_ZONE
    G.listHost = CreateFrame("Frame", nil, right)
    G.listHost:SetPoint("TOPLEFT", right, "TOPLEFT", CARD_PAD, -listTop)
    G.listHost:SetPoint("BOTTOMRIGHT", right, "BOTTOMRIGHT", -CARD_PAD, CARD_PAD + 30)

    local headRow = CreateFrame("Frame", nil, right)
    headRow:SetHeight(20)
    headRow:SetPoint("BOTTOMLEFT", G.listHost, "TOPLEFT", 0, 0)
    headRow:SetPoint("BOTTOMRIGHT", G.listHost, "TOPRIGHT", 0, 0)
    local function HeadL(txt, x)
        local f = MakeFS(headRow, 16, C_GREY, "LEFT")
        f:SetPoint("LEFT", x, 0)
        f:SetText(txt)
    end
    HeadL(L["名称"], CARD_PAD + 40)
    G.headSort = {}
    local function HeadSortBtn(key, x)
        local b = CreateFrame("Button", nil, headRow)
        b:SetSize(88, 20)
        b:SetPoint("LEFT", x, 0)
        local arrow = b:CreateTexture(nil, "OVERLAY")
        arrow:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\icon\\NAV\\SortIcon")
        arrow:SetSize(14, 14)
        arrow:SetPoint("LEFT", b, "LEFT", 0, 0)
        local f = MakeFS(b, 16, C_GREY, "LEFT")
        f:SetPoint("LEFT", b, "LEFT", 16, 0)
        f:SetText(L[key == "ilvl" and "物品等级" or "需要等级"])
        b:SetScript("OnClick", function()
            if G.sort ~= key then
                G.sort = key
                G.sortDir = 1
            else
                if G.sortDir == -1 then G.sortDir = 1 else G.sortDir = -1 end
            end
            GDB().sort = G.sort
            GDB().sortDir = G.sortDir
            G.page = 1
            GDB().page = 1
            G.PaintChips()
            G.Refresh()
            ns.PlaySound(1)
        end)
        G.headSort[key] = { fs = f, arrow = arrow }
        return b
    end
    HeadSortBtn("ilvl", CARD_PAD + 168)
    HeadSortBtn("req", CARD_PAD + 276)
    HeadL(L["类型"], CARD_PAD + 366)
    HeadL(L["来源"], CARD_PAD + 470)
    local headWish = MakeFS(headRow, 16, C_GREY, "CENTER")
    headWish:SetPoint("RIGHT", headRow, "RIGHT", -(CARD_PAD + 4), 0)
    headWish:SetText(L["心愿"])
    G.headRow = headRow
    coroutine.yield()

    G.emptyFs = MakeFS(G.listHost, 14, C_GREY, "CENTER")
    G.emptyFs:SetPoint("CENTER", G.listHost, "CENTER", 0, 0)
    G.emptyFs:SetText(L["没有匹配的装备"])
    G.emptyFs:Hide()

    local pagerRow = CreateFrame("Frame", nil, right)
    pagerRow:SetHeight(24)
    pagerRow:SetPoint("BOTTOMLEFT", right, "BOTTOMLEFT", CARD_PAD, CARD_PAD)
    pagerRow:SetPoint("BOTTOMRIGHT", right, "BOTTOMRIGHT", -CARD_PAD, CARD_PAD)
    G.BuildPager(pagerRow)
    G.pgTotal:ClearAllPoints()
    G.pgTotal:SetParent(pagerRow)
    G.pgTotal:SetPoint("RIGHT", -CARD_PAD, 0)
    G.pgPrev:SetPoint("LEFT", pagerRow, "LEFT", CARD_PAD, 0)
    G.pgJump:ClearAllPoints()
    G.pgJump:SetPoint("LEFT", G.pgNext, "RIGHT", 8, 0)
    G.pgGo:ClearAllPoints()
    G.pgGo:SetPoint("LEFT", G.pgJump, "RIGHT", 8, 0)
    for i = 1, 5 do
        G.pgNums[i]:SetPoint("LEFT", i == 1 and G.pgNext or G.pgNums[i - 1], "RIGHT", 8, 0)
    end
    coroutine.yield()

    local inner = right:GetHeight() - 2 * CARD_PAD - TITLE_ZONE - CHIP_ZONE - SORT_ZONE - PAGER_ZONE
    local size = math.floor(inner / ROW_H)
    if size < 8 then size = 8 end
    if size > 60 then size = 60 end
    G.pageSize = size

    ns.OpenPerf.Mark("骨架")
    G.built = true
    G.building = false
    G.StartWarm()
    G.StartIconWarm()
    RefreshSoon()
    ns.OpenPerf.Mark("首绘")
    if not G.__gc1 then
        G.__gc1 = true
        if ns.IdleJobs then
            ns.IdleJobs.StepGC(120, 512)
        elseif C_Timer and C_Timer.After then
            C_Timer.After(1, function() collectgarbage("collect") end)
        end
    end
    end, function()
        G.building = false
        local U0 = ns.DungeonUI
        if U0 and U0.subBuilt then U0.subBuilt["Gear"] = nil end
    end)
end
