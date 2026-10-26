local _, ns = ...

if not ns.LoadForeverPages then return end

local format = string.format
local L = ns.L

local Host = ns.ProfHost
if not Host then return end

local DG = Host.DG
local MakeFS = Host.MakeFS
local NewButton, MakeOutline = Host.NewButton, Host.MakeOutline
local SetOutline, SetButtonSelected, Unpack = Host.SetOutline, Host.SetButtonSelected, Host.Unpack
local C_GOLD, C_GREY = Host.C_GOLD, Host.C_GREY
local C_DIM, C_WHITE, C_TEXT = Host.C_DIM, Host.C_WHITE, Host.C_TEXT
local C_GREEN = Host.C_GREEN
local PAGE_INSET = Host.PAGE_INSET
local CONTENT_W = Host.CONTENT_W
local FALLBACK_ICON = Host.FALLBACK_ICON

local BIS, VOLS, N_PRESET
local SPEC_DEFS = { { id = "pve", label = L["副本"] }, { id = "pvp", label = L["战场"] },
                    { id = "tank", label = L["坦克"] } }
local SPEC_LABEL = {}
for _, def in ipairs(SPEC_DEFS) do SPEC_LABEL[def.id] = def.label end
local function EnsureBIS()
    if VOLS then return BIS end
    VOLS = {}
    local d = ns.EnsureBISData and ns.EnsureBISData() or nil
    BIS = (d and type(d.classes) == "table") and d or nil
    if BIS then
        if type(BIS.levels) == "table" then
            for lv, v in pairs(BIS.levels) do
                if type(v) == "table" and type(v.classes) == "table" then
                    VOLS[#VOLS + 1] = { lv = tonumber(lv) or 0, classes = v.classes }
                end
            end
            table.sort(VOLS, function(a, b) return a.lv < b.lv end)
        end
        if #VOLS == 0 then
            VOLS = { { lv = tonumber(BIS.default) or 0, classes = BIS.classes } }
        end
    end
    local maxPages = 2
    local slugs, seen = {}, {}
    for _, v in ipairs(VOLS) do
        for _, c in ipairs(v.classes) do
            if not seen[c.slug] then seen[c.slug] = true slugs[#slugs + 1] = c.slug end
        end
    end
    for _, slug in ipairs(slugs) do
        local n = 0
        for _, v in ipairs(VOLS) do
            for _, c in ipairs(v.classes) do
                if c.slug == slug then n = n + #c.specs end
            end
        end
        if n > maxPages then maxPages = n end
    end
    N_PRESET = maxPages * 2 + 3
    return BIS
end
local N_USER = 7

local BG = {}
ns.BisModule = BG

local function DefaultVol()
    EnsureBIS()
    local d = BIS and tonumber(BIS.default) or nil
    if d then
        for i, v in ipairs(VOLS) do
            if v.lv == d then return i end
        end
    end
    return #VOLS
end

local function CurVol() EnsureBIS() return VOLS[BG.vol] or VOLS[#VOLS] end

local CLASS_FILE = {
    warrior = "WARRIOR", paladin = "PALADIN", hunter = "HUNTER",
    rogue = "ROGUE", priest = "PRIEST", mage = "MAGE",
    warlock = "WARLOCK", druid = "DRUID", shaman = "SHAMAN",
}

local function ClassIconPath(slug)
    return "Interface\\AddOns\\DungeonsForever\\Media\\icon\\CLASS\\ClassIcon_"
        .. slug:sub(1, 1) .. slug:sub(2):lower()
end

local SLOTS_LEFT  = { "head", "neck", "shoulder", "back", "chest",
                      "shirt", "tabard", "wrist" }
local SLOTS_RIGHT = { "hands", "waist", "legs", "feet", "finger", "finger2",
                      "trinket", "trinket2" }
local SLOT_NAMES = {
    head = L["头部"], neck = L["颈部"], shoulder = L["肩部"], back = L["背部"], chest = L["胸部"],
    wrist = L["手腕"], hands = L["手部"], waist = L["腰部"], legs = L["腿部"], feet = L["脚"],
    finger = L["戒指"], finger2 = L["戒指"], trinket = L["饰品"], trinket2 = L["饰品"],
    shirt = L["衬衣"], tabard = L["公会徽章"],
    ["two-hand"] = L["双手武器"], ["main-hand"] = L["主手"], ["off-hand"] = L["副手"],
    ranged = L["远程"],
}

local function RowsKey(slotKey)
    if slotKey == "finger2" then return "finger" end
    if slotKey == "trinket2" then return "trinket" end
    if slotKey == "main" then return "main-hand" end
    if slotKey == "off" then return "off-hand" end
    return slotKey
end

local FILTERS = {
    { id = "craft", label = L["制造"] },
    { id = "quest", label = L["任务"] }, { id = "boss", label = L["副本"] },
    { id = "rare", label = L["稀有"] }, { id = "vendor", label = L["商人"] },
    { id = "other", label = L["其他"] },
}

local STAT_ROWS = {
    { "ITEM_MOD_STRENGTH_SHORT",     L["力量"] },
    { "ITEM_MOD_AGILITY_SHORT",      L["敏捷"] },
    { "ITEM_MOD_STAMINA_SHORT",      L["耐力"] },
    { "ITEM_MOD_INTELLECT_SHORT",    L["智力"] },
    { "ITEM_MOD_SPIRIT_SHORT",       L["精神"] },
    { "ITEM_MOD_ATTACK_POWER_SHORT", L["攻击强度"] },
    { "ITEM_MOD_SPELL_POWER_SHORT",  L["法术强度"] },
    { "ITEM_MOD_CRIT_RATING_SHORT",  L["暴击等级"] },
    { "ITEM_MOD_HASTE_RATING_SHORT", L["急速等级"] },
    { "ITEM_MOD_HIT_RATING_SHORT",   L["命中等级"] },
}

local ENCH_CARD_H = 8 + 24 + 8 + (4 * 36 + 3 * 2) + 8

local QUALITY_COLORS = {
    [0] = { 0.62, 0.62, 0.62 }, [1] = { 1, 1, 1 }, [2] = { 0.12, 1, 0 },
    [3] = { 0, 0.44, 0.87 }, [4] = { 0.64, 0.21, 0.93 }, [5] = { 1, 0.5, 0.2 },
}

local PHYS_CLS = { warrior = true, paladin = true, hunter = true,
                   rogue = true, druid = true, shaman = true }
local PRIM_STAT = {
    warrior = "STRENGTH", paladin = "STRENGTH", hunter = "AGILITY",
    rogue = "AGILITY", priest = "INTELLECT", mage = "INTELLECT",
    warlock = "INTELLECT", druid = "AGILITY", shaman = "AGILITY",
}

local SPEC_DIR = {
    warrior = {
        { key = "arms",   label = "武器", role = "phys", icon = "Interface\\Icons\\ability_warrior_savageblow" },
        { key = "fury",   label = "狂暴", role = "phys", icon = "Interface\\Icons\\ability_warrior_innerrage" },
        { key = "prot",   label = "防战", role = "tank", icon = "Interface\\Icons\\ability_warrior_defensivestance" },
    },
    paladin = {
        { key = "holy",   label = "奶骑", role = "heal", icon = "Interface\\Icons\\Spell_Holy_HolyBolt" },
        { key = "prot",   label = "防骑", role = "tank", icon = "Interface\\Icons\\Spell_Holy_DevotionAura" },
        { key = "ret",    label = "惩戒", role = "phys", icon = "Interface\\Icons\\Spell_Holy_AuraOfLight" },
    },
    hunter = {
        { key = "bm",     label = "兽王", role = "phys", icon = "Interface\\Icons\\Ability_Hunter_BeastTaming" },
        { key = "mm",     label = "射击", role = "phys", icon = "Interface\\Icons\\Ability_Marksmanship" },
        { key = "surv",   label = "生存", role = "phys", icon = "Interface\\Icons\\Ability_Hunter_SwiftStrike" },
    },
    rogue = {
        { key = "assa",   label = "奇袭", role = "phys", icon = "Interface\\Icons\\ability_rogue_eviscerate" },
        { key = "combat", label = "战斗", role = "phys", icon = "Interface\\Icons\\ability_backstab" },
        { key = "sub",    label = "敏锐", role = "phys", icon = "Interface\\Icons\\ability_stealth" },
    },
    priest = {
        { key = "disc",   label = "戒律", role = "heal", icon = "Interface\\Icons\\spell_holy_wordfortitude" },
        { key = "holy",   label = "神牧", role = "heal", icon = "Interface\\Icons\\spell_holy_guardianspirit" },
        { key = "shadow", label = "暗牧", role = "spell", icon = "Interface\\Icons\\spell_shadow_shadowwordpain" },
    },
    shaman = {
        { key = "ele",    label = "元素", role = "spell", icon = "Interface\\Icons\\spell_nature_lightning" },
        { key = "enh",    label = "增强", role = "phys", icon = "Interface\\Icons\\spell_nature_lightningshield" },
        { key = "resto",  label = "奶萨", role = "heal", icon = "Interface\\Icons\\Spell_Nature_HealingWaveGreater" },
    },
    mage = {
        { key = "arcane", label = "奥法", role = "spell", icon = "Interface\\Icons\\inv_misc_rune_03" },
        { key = "fire",   label = "火法", role = "spell", icon = "Interface\\Icons\\spell_fire_firebolt02" },
        { key = "frost",  label = "冰法", role = "spell", icon = "Interface\\Icons\\spell_frost_frostbolt02" },
    },
    warlock = {
        { key = "affli",  label = "痛苦", role = "spell", icon = "Interface\\Icons\\spell_shadow_deathcoil" },
        { key = "demo",   label = "恶魔", role = "spell", icon = "Interface\\Icons\\spell_shadow_metamorphosis" },
        { key = "destro", label = "毁灭", role = "spell", icon = "Interface\\Icons\\spell_shadow_rainoffire" },
    },
    druid = {
        { key = "balance", label = "鸟德", role = "spell", icon = "Interface\\Icons\\spell_nature_starfall" },
        { key = "cat",     label = "猫德", role = "phys", icon = "Interface\\Icons\\Ability_Druid_CatForm" },
        { key = "bear",    label = "熊德", role = "tank", icon = "Interface\\Icons\\ability_racial_bearform" },
        { key = "resto",   label = "奶德", role = "heal", icon = "Interface\\Icons\\Spell_Nature_HealingTouch" },
    },
}

local function RoleOfKey(cls, key)
    for _, sr in ipairs(SPEC_DIR[cls] or {}) do
        if sr.key == key then return sr.role end
    end
    return nil
end
local ROLE_TALENT = {
    druid = { [1] = "spell", [2] = "phys", [3] = "heal" },
    shaman = { [1] = "spell", [2] = "phys", [3] = "heal" },
    paladin = { [1] = "heal", [2] = "heal", [3] = "phys" },
    priest = { [1] = "heal", [2] = "heal", [3] = "spell" },
}
local ROLE_CONST = {
    mage = "spell", warlock = "spell", hunter = "phys",
    warrior = "phys", rogue = "phys",
}
local PURE_PHYS = { warrior = true, rogue = true, hunter = true }
local __tprof, __tprofDirty = nil, true

local function TalentSpent(tab)
    local n = 0
    local okG, cnt = pcall(GetNumTalents, tab)
    if not okG or type(cnt) ~= "number" then return nil end
    for i = 1, cnt do
        local ok, _, _, _, _, rank = pcall(GetTalentInfo, tab, i)
        if ok and type(rank) == "number" then n = n + rank end
    end
    return n
end

local function RoleOf(cls)
    if __tprofDirty or __tprof == nil then
        __tprofDirty = false
        __tprof = {}
    end
    local c = __tprof[cls]
    if c ~= nil then return c end
    local role = ROLE_CONST[cls]
    if role == nil then
        local m = ROLE_TALENT[cls]
        if m then
            local best, bestN = nil, 0
            for tab = 1, 3 do
                local n = TalentSpent(tab)
                if type(n) == "number" and n > bestN then
                    best, bestN = tab, n
                end
            end
            role = (best and m[best]) or "phys"
        else
            role = "phys"
        end
    end
    __tprof[cls] = role
    return role
end

local function SpecWeights(cls, specId)
    local role = RoleOfKey(cls, BG.wRole) or RoleOf(cls)
    local phys = role == "phys"
    local heal = role == "heal"
    local w = {
        STRENGTH = 0, AGILITY = 0, INTELLECT = phys and 0.42 or 1,
        SPIRIT = phys and 0.3 or 0.35,
        STAMINA = 0.1,
        ARMOR = 0.004,
        ATTACK_POWER = phys and 0.48 or 0.05,
        RANGED_ATTACK_POWER = 0,
        SPELL_POWER = phys and 0.4 or 1,
        CRIT_RATING = phys and 0.75 or 0.7,
        HIT_RATING = 1.1, HASTE_RATING = 0.5,
        WEAPON_DPS = 0, RANGED_DPS = 0,
        MANA_REGENERATION = 0,
        HEALTH_REGEN = 0, BLOCK_VALUE = 0, SPELL_PENETRATION = 0,
        SPELL_DAMAGE_DONE = 0, SPELL_HEALING_DONE = 0,
        ARCANE_DAMAGE_DONE = 0, FIRE_DAMAGE_DONE = 0, FROST_DAMAGE_DONE = 0,
        NATURE_DAMAGE_DONE = 0, SHADOW_DAMAGE_DONE = 0, HOLY_DAMAGE_DONE = 0,
        ARCANE_RESISTANCE = 0, FIRE_RESISTANCE = 0, FROST_RESISTANCE = 0,
        NATURE_RESISTANCE = 0, SHADOW_RESISTANCE = 0,
    }
    if phys then
        w.AGILITY = (PRIM_STAT[cls] == "AGILITY") and 1 or 0.66
        w.STRENGTH = (PRIM_STAT[cls] == "STRENGTH") and 1 or 0.05
        w[PRIM_STAT[cls] or "STRENGTH"] = 1
        w.RANGED_ATTACK_POWER = w.ATTACK_POWER
        w.SPELL_DAMAGE_DONE = 0.08
        w.ARCANE_DAMAGE_DONE = 0.06
        w.FIRE_DAMAGE_DONE = 0.06
        w.FROST_DAMAGE_DONE = 0.06
        w.NATURE_DAMAGE_DONE = 0.06
        w.SHADOW_DAMAGE_DONE = 0.06
        w.HEALTH_REGEN = 0.08
        if cls == "hunter" then
            w.RANGED_DPS = 2.5
            w.WEAPON_DPS = 1.0
        else
            w.WEAPON_DPS = 5.0
        end
    elseif heal then
        w.INTELLECT = 0.5
        w.SPIRIT = 0.5
        w.MANA_REGENERATION = 1.5
        w.CRIT_RATING = 0.3
        w.HASTE_RATING = 0.3
        w.SPELL_HEALING_DONE = 0.95
        w.SPELL_DAMAGE_DONE = 0.05
        w.ARCANE_DAMAGE_DONE = 0.05
        w.FIRE_DAMAGE_DONE = 0.05
        w.FROST_DAMAGE_DONE = 0.05
        w.NATURE_DAMAGE_DONE = 0.05
        w.SHADOW_DAMAGE_DONE = 0.05
        w.HEALTH_REGEN = 0.04
    else
        w.SPIRIT = 0.35
        w.CRIT_RATING = 0.7
        w.HASTE_RATING = 0.55
        w.SPELL_DAMAGE_DONE = 0.85
        w.SPELL_HEALING_DONE = 0.05
        w.ARCANE_DAMAGE_DONE = 0.7
        w.FIRE_DAMAGE_DONE = 0.7
        w.FROST_DAMAGE_DONE = 0.7
        w.NATURE_DAMAGE_DONE = 0.7
        w.SHADOW_DAMAGE_DONE = 0.7
        w.HEALTH_REGEN = 0.03
    end
    if specId == "pvp" then
        w.STAMINA = 0.5
        w.RESILIENCE_RATING = 0.6
    elseif specId == "tank" then
        w.STAMINA = 1
        w.DEFENSE_SKILL_RATING = 0.8
        w.DODGE_RATING = 0.7
        w.PARRY_RATING = 0.6
        w.BLOCK_RATING = 0.55
        w.BLOCK_VALUE = 0.35
        w.ARMOR = 0.008
        w.HEALTH_REGEN = 0.15
        w.CRIT_RATING = 0.3
        w.HIT_RATING = 0.7
        w.HASTE_RATING = 0.3
        if cls == "warrior" then
            w.STRENGTH = 0.55
            w.AGILITY = 0.45
            w.ATTACK_POWER = 0.3
            w.WEAPON_DPS = 3.0
        elseif cls == "druid" then
            w.STRENGTH = 0.55
            w.AGILITY = 0.6
            w.ATTACK_POWER = 0.35
            w.WEAPON_DPS = 3.5
            w.BLOCK_RATING = 0
            w.INTELLECT = 0
            w.SPIRIT = 0
            w.SPELL_POWER = 0
        elseif cls == "paladin" then
            w.STRENGTH = 0.5
            w.AGILITY = 0.3
            w.ATTACK_POWER = 0.25
            w.INTELLECT = 0.4
            w.SPIRIT = 0.08
            w.SPELL_POWER = 0.55
            w.MANA_REGENERATION = 0.2
            w.WEAPON_DPS = 2.5
        end
    end
    if PURE_PHYS[cls] then
        w.INTELLECT = 0
        w.SPIRIT = 0
        w.SPELL_POWER = 0
        w.SPELL_DAMAGE_DONE = 0
        w.SPELL_HEALING_DONE = 0
        w.ARCANE_DAMAGE_DONE = 0
        w.FIRE_DAMAGE_DONE = 0
        w.FROST_DAMAGE_DONE = 0
        w.NATURE_DAMAGE_DONE = 0
        w.SHADOW_DAMAGE_DONE = 0
    end
    return w
end

local statCache, scoreCache, scoreKey = {}, {}, nil
local statSeen = {}
local askedItem = {}
local dpsCache, dpsMiss, dpsGen = {}, {}, 0

local function StatBucket(key)
    if type(key) ~= "string" then return nil end
    if string.sub(key, -6) == "_SHORT" then key = string.sub(key, 1, -7) end
    return string.match(key, "ITEM_MOD_(.+)$")
end

local W_KEYS = {
    { "STRENGTH", L["力量"] }, { "AGILITY", L["敏捷"] }, { "INTELLECT", L["智力"] },
    { "SPIRIT", L["精神"] }, { "STAMINA", L["耐力"] },
    { "MANA_REGENERATION", L["5秒回蓝"] }, { "HEALTH_REGEN", L["5秒回血"] },
    { "ATTACK_POWER", L["攻击强度"] }, { "RANGED_ATTACK_POWER", L["远程攻强"] },
    { "WEAPON_DPS", L["武器伤害"] }, { "RANGED_DPS", L["远程武器伤害"] },
    { "SPELL_POWER", L["法术强度"] }, { "SPELL_DAMAGE_DONE", L["法术伤害"] },
    { "SPELL_HEALING_DONE", L["治疗效果"] }, { "SPELL_PENETRATION", L["法术穿透"] },
    { "ARCANE_DAMAGE_DONE", L["奥术伤害"] }, { "FIRE_DAMAGE_DONE", L["火焰伤害"] },
    { "FROST_DAMAGE_DONE", L["冰霜伤害"] }, { "NATURE_DAMAGE_DONE", L["自然伤害"] },
    { "SHADOW_DAMAGE_DONE", L["暗影伤害"] }, { "HOLY_DAMAGE_DONE", L["神圣伤害"] },
    { "ARCANE_RESISTANCE", L["奥术抗性"] }, { "FIRE_RESISTANCE", L["火焰抗性"] },
    { "FROST_RESISTANCE", L["冰霜抗性"] }, { "NATURE_RESISTANCE", L["自然抗性"] },
    { "SHADOW_RESISTANCE", L["暗影抗性"] },
    { "CRIT_RATING", L["暴击等级"] }, { "HIT_RATING", L["命中等级"] },
    { "HASTE_RATING", L["急速等级"] }, { "DEFENSE_SKILL_RATING", L["防御技能"] },
    { "DODGE_RATING", L["躲闪等级"] }, { "PARRY_RATING", L["招架等级"] },
    { "BLOCK_RATING", L["格挡等级"] }, { "BLOCK_VALUE", L["格挡值"] },
    { "ARMOR", L["护甲"] }, { "RESILIENCE_RATING", L["韧性"] },
}
local W_SCHEME_MAX = 6

local function EnsureDpsTip()
    if BG.dpsTip then return BG.dpsTip end
    if BG.__dpsTried then return nil end
    BG.__dpsTried = true
    local ok, tip = pcall(CreateFrame, "GameTooltip", "DFBisDpsTip", UIParent, "GameTooltipTemplate")
    if ok and tip then
        BG.dpsTip = tip
        pcall(tip.SetAlpha, tip, 0)
        if tip.SetOwner then pcall(tip.SetOwner, tip, UIParent, "ANCHOR_NONE") end
    else
        BG.dpsTip = nil
    end
    if not BG.dpsTip then BG.__dpsDead = true end
    return BG.dpsTip
end

local function ScanDps(itemID)
    if type(itemID) ~= "number" or BG.__dpsDead then return nil end
    local c = dpsCache[itemID]
    if c ~= nil then return c end
    if dpsMiss[itemID] then return nil end
    if not DG.ItemInfo(itemID) then return nil end
    if (BG.__dpsDepth or 0) > 0 then return nil end
    local tip = EnsureDpsTip()
    if not tip then return nil end
    BG.__dpsDepth = (BG.__dpsDepth or 0) + 1
    local dps = nil
    local okScan = pcall(function()
        if tip.SetOwner and not pcall(tip.SetOwner, tip, UIParent, "ANCHOR_NONE") then return end
        local set = false
        if tip.SetHyperlink then set = pcall(tip.SetHyperlink, tip, "item:" .. tostring(itemID)) end
        if not set then return end
        pcall(tip.Show, tip)
        local n = (tip.NumLines and tip:NumLines()) or 0
        for i = 1, n do
            local fs = _G["DFBisDpsTipTextLeft" .. i]
            local t = (fs and fs.GetText) and fs:GetText() or nil
            if type(t) == "string" and t ~= ""
                and (string.find(t, "每秒伤害", 1, true)
                    or string.find(t, "每秒傷害", 1, true)
                    or string.find(t, "per second", 1, true)) then
                local v = tonumber(string.match(t, "伤害%s*([%d%.]+)"))
                    or tonumber(string.match(t, "傷害%s*([%d%.]+)"))
                    or tonumber(string.match(t, "([%d%.]+)%s*per second"))
                    or tonumber(string.match(t, "([%d%.]+)%s*[%)）]%s*$"))
                if v and v > 0 then dps = v end
            end
        end
        pcall(tip.Hide, tip)
    end)
    BG.__dpsDepth = BG.__dpsDepth - 1
    if not okScan or dps == nil then
        local pending = false
        pcall(function()
            local fs = _G["DFBisDpsTipTextLeft1"]
            local t = (fs and fs.GetText) and fs:GetText() or nil
            if type(t) == "string"
                and (string.find(t, "正在获取", 1, true)
                    or string.find(t, "正在載入", 1, true)
                    or string.find(t, "RETRIEVING", 1, true)) then pending = true end
        end)
        if not pending then dpsMiss[itemID] = true end
        return nil
    end
    dpsCache[itemID] = dps
    dpsGen = dpsGen + 1
    BG.needScores = true
    return dps
end

local function MatchStatNum(t, name)
    local esc = string.gsub(name, "([%^%$%(%)%%%.%[%]%*%+%-%?])", "%%%1")
    return tonumber(string.match(t, "([%-%+]?[%d%.]+)%s*" .. esc))
        or tonumber(string.match(t, esc .. "%s*([%-%+]?[%d%.]+)"))
end

local tipStatCache = {}

local function ScanStatsTip(id)
    if type(id) ~= "number" or BG.__dpsDead then return nil end
    local c = tipStatCache[id]
    if c ~= nil then return c end
    if not DG.ItemInfo(id) then return nil end
    if (BG.__dpsDepth or 0) > 0 then return nil end
    local tip = EnsureDpsTip()
    if not tip then return nil end
    BG.__dpsDepth = (BG.__dpsDepth or 0) + 1
    local out = {}
    local okScan = pcall(function()
        if tip.SetOwner and not pcall(tip.SetOwner, tip, UIParent, "ANCHOR_NONE") then return end
        local set = false
        if tip.SetHyperlink then set = pcall(tip.SetHyperlink, tip, "item:" .. tostring(id)) end
        if not set then return end
        pcall(tip.Show, tip)
        local n = (tip.NumLines and tip:NumLines()) or 0
        local allKey = L["所有属性"]
        for i = 1, n do
            local fs = _G["DFBisDpsTipTextLeft" .. i]
            local t = (fs and fs.GetText) and fs:GetText() or nil
            if type(t) == "string" and t ~= "" then
                if type(allKey) == "string" and allKey ~= "" and string.find(t, allKey, 1, true) then
                    local nv = MatchStatNum(t, allKey)
                    if nv then
                        for _, k in ipairs({ "STRENGTH", "AGILITY", "INTELLECT", "SPIRIT", "STAMINA" }) do
                            out[k] = (out[k] or 0) + nv
                        end
                    end
                end
                for _, wk in ipairs(W_KEYS) do
                    local k, nm = wk[1], wk[2]
                    if k ~= "WEAPON_DPS" and type(nm) == "string" and nm ~= "" then
                        local nv = MatchStatNum(t, nm)
                        if nv and nv > 0 then out[k] = (out[k] or 0) + nv end
                    end
                end
            end
        end
        pcall(tip.Hide, tip)
    end)
    BG.__dpsDepth = BG.__dpsDepth - 1
    if not okScan then return nil end
    if not next(out) then return nil end
    tipStatCache[id] = out
    BG.__statCacheN = (BG.__statCacheN or 0) + 1
    if BG.__statCacheN > 2500 then
        for k in pairs(tipStatCache) do tipStatCache[k] = nil end
        BG.__statCacheN = 0
    end
    return out
end

local function ItemStatsOf(id)
    local link
    if DG.ItemLink then
        local ok, l = pcall(DG.ItemLink, id)
        if ok then link = l end
    end
    local fn = GetItemStats or (C_Item and C_Item.GetItemStats)
    if type(fn) == "function" and type(link) == "string" and link ~= "" then
        local ok, st = pcall(fn, link)
        if ok and type(st) == "table" then
            statSeen[id] = true
            local out = {}
            local av = st.RESISTANCE0_NAME
            if type(av) == "number" and av > 0 then out.ARMOR = av end
            for sk, sv in pairs(st) do
                local b = StatBucket(sk)
                if b and type(sv) == "number" then out[b] = sv end
                if type(sv) == "number" and sv > 0 then
                    if sk == "RESISTANCE2_NAME" then out.FIRE_RESISTANCE = sv
                    elseif sk == "RESISTANCE3_NAME" then out.NATURE_RESISTANCE = sv
                    elseif sk == "RESISTANCE4_NAME" then out.FROST_RESISTANCE = sv
                    elseif sk == "RESISTANCE5_NAME" then out.SHADOW_RESISTANCE = sv
                    elseif sk == "RESISTANCE6_NAME" then out.ARCANE_RESISTANCE = sv end
                end
            end
            if next(out) then
                statCache[id] = out
                return out
            end
        end
    end
    local out = ScanStatsTip(id)
    if out then statCache[id] = out end
    return out
end

local function ItemScore(id, w)
    if not id then return nil end
    local k = BG.cls .. ":" .. BG.spec .. ":" .. (BG.wGen or 0) .. ":" .. dpsGen
    if scoreKey ~= k then
        scoreCache, scoreKey = {}, k
    end
    local v = scoreCache[id]
    if v ~= nil then return v end
    local st = ItemStatsOf(id)
    local sum = 0
    if type(st) == "table" then
        local av = st.ARMOR
        if type(av) == "number" and av > 0 and type(w.ARMOR) == "number" then
            sum = sum + av * w.ARMOR
        end
        for bkt, sv in pairs(st) do
            local wv = w[bkt]
            if type(wv) == "number" and type(sv) == "number" and sv > 0 then sum = sum + sv * wv end
        end
    end
    ScanDps(id)
    local dps = dpsCache[id]
    if type(dps) ~= "number" and type(st) == "table" and type(st.DAMAGE_PER_SECOND) == "number" then
        dps = st.DAMAGE_PER_SECOND
    end
    if type(dps) == "number" then
        local dw = w.WEAPON_DPS or 0
        local fn = GetItemInfoInstant or (C_Item and C_Item.GetItemInfoInstant)
        if type(fn) == "function" then
            local ok, _, _, _, eq = pcall(fn, id)
            if ok and (eq == "INVTYPE_RANGED" or eq == "INVTYPE_RANGEDRIGHT" or eq == "INVTYPE_THROWN") then
                dw = w.RANGED_DPS or 0
            end
        end
        if dw > 0 then sum = sum + dps * dw end
    end
    if sum <= 0 then return nil end
    scoreCache[id] = sum
    return sum
end

local W_ICONS = {
    "Interface\\Icons\\Trade_Engineering", "Interface\\Icons\\INV_Misc_Gear_01",
    "Interface\\Icons\\INV_Misc_PocketWatch_01", "Interface\\Icons\\INV_Jewelry_Talisman_01",
    "Interface\\Icons\\INV_Misc_Gem_01", "Interface\\Icons\\INV_Misc_Book_01",
    "Interface\\Icons\\Ability_Warrior_DefensiveStance", "Interface\\Icons\\INV_Misc_QuestionMark",
}
local C_RED_W = { 0.85, 0.3, 0.3 }

local function DB()
    DungeonsForeverDB = DungeonsForeverDB or {}
    local s = DungeonsForeverDB.bis
    if not s then
        s = { plans = {} }
        DungeonsForeverDB.bis = s
    end
    if not s.plans then s.plans = {} end
    return s
end

local function LoadWeightPrefs()
    local s = DB()
    local list = s.wSchemes
    BG.wSchemes = {}
    if type(list) == "table" then
        for _, sch in ipairs(list) do
            if type(sch) == "table" and type(sch.name) == "string" and type(sch.w) == "table" then
                BG.wSchemes[#BG.wSchemes + 1] = { name = sch.name, icon = sch.icon, w = sch.w }
            end
        end
    end
    local a = tonumber(s.wActive)
    BG.wActive = (a and BG.wSchemes[a]) and a or nil
    local r = s.wRole
    BG.wRole = (type(r) == "string" and r ~= "") and r or nil
end

local function SaveWeightPrefs()
    local s = DB()
    local list = {}
    for _, sch in ipairs(BG.wSchemes or {}) do
        list[#list + 1] = { name = sch.name, icon = sch.icon, w = sch.w }
    end
    s.wSchemes = list
    s.wActive = BG.wActive
    s.wRole = BG.wRole
end

local function BumpWeights()
    BG.wGen = (BG.wGen or 0) + 1
    if BG.built and BG.usingPlan == nil and BG.autoPlan then
        BG.UseAutoPlan(BG.autoPlan)
    end
end

local function EffWeights()
    local sch = BG.wActive and BG.wSchemes and BG.wSchemes[BG.wActive] or nil
    if sch and type(sch.w) == "table" then
        local w = SpecWeights(BG.cls, BG.spec)
        for k, v in pairs(sch.w) do w[k] = v end
        return w
    end
    return SpecWeights(BG.cls, BG.spec)
end

local function MakeWeightIcon(parent, size)
    local bt = CreateFrame("Button", nil, parent)
    bt:SetSize(size, size)
    bt.tex = bt:CreateTexture(nil, "ARTWORK")
    bt.tex:SetAllPoints()
    bt.tex:SetTexCoord(0.07, 0.93, 0.07, 0.93)
    if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(bt.tex) end
    bt.hi = bt:CreateTexture(nil, "HIGHLIGHT")
    bt.hi:SetAllPoints()
    bt.hi:SetColorTexture(1, 1, 1, 0.15)
    MakeOutline(bt, Unpack(C_GOLD))
    return bt
end

local wdlg = nil
local function EnsureWeightDialog()
    if wdlg then return wdlg end
    local host = ns.MainFrame or UIParent
    local popup = CreateFrame("Frame", "DungeonsForever_BisWeightDlg", host, "BackdropTemplate")
    popup:SetSize(300, 174)
    popup:SetFrameStrata("DIALOG")
    popup:SetMovable(true)
    popup:EnableMouse(true)
    popup:SetClampedToScreen(true)
    popup:SetPoint("CENTER", host, "CENTER", 0, 0)
    popup:Hide()
    if ns.hui and ns.hui.SkinPopup then ns.hui.SkinPopup(popup, 8) end
    if ns.hui and ns.hui.SkinShadow then ns.hui.SkinShadow(popup) end
    local titleBar = CreateFrame("Frame", nil, popup)
    titleBar:SetPoint("TOPLEFT", popup, "TOPLEFT", 0, 0)
    titleBar:SetPoint("TOPRIGHT", popup, "TOPRIGHT", 0, 0)
    titleBar:SetHeight(30)
    titleBar:EnableMouse(true)
    titleBar:RegisterForDrag("LeftButton")
    titleBar:SetScript("OnDragStart", function() popup:StartMoving() end)
    titleBar:SetScript("OnDragStop", function() popup:StopMovingOrSizing() end)
    local title = MakeFS(titleBar, 16, C_WHITE, "LEFT")
    title:SetPoint("LEFT", titleBar, "LEFT", 8, 0)
    local nl = MakeFS(popup, 14, C_TEXT, "LEFT")
    nl:SetPoint("TOPLEFT", popup, "TOPLEFT", 8, -40)
    nl:SetText(L["名称："])
    local edit = ns.CreateEditBox and ns.CreateEditBox(popup, 190) or nil
    if edit then edit:SetPoint("LEFT", nl, "RIGHT", 6, 0) end
    local il = MakeFS(popup, 14, C_TEXT, "LEFT")
    il:SetPoint("TOPLEFT", popup, "TOPLEFT", 8, -72)
    il:SetText(L["图标："])
    local icons = {}
    for i, tex in ipairs(W_ICONS) do
        local bt = MakeWeightIcon(popup, 28)
        bt:SetPoint("TOPLEFT", popup, "TOPLEFT", 8 + (i - 1) * 32, -92)
        bt.tex:SetTexture(tex)
        bt.icon = tex
        bt:SetScript("OnClick", function(self)
            ns.PlaySound(1)
            wdlg.picked = self.icon
            for _, ob in ipairs(icons) do SetOutline(ob, ob.icon == wdlg.picked) end
        end)
        icons[i] = bt
    end
    local hint = MakeFS(popup, 14, C_RED_W, "LEFT")
    hint:SetPoint("TOPLEFT", popup, "TOPLEFT", 8, -130)
    hint:Hide()
    local ok = NewButton(popup, L["确定"], 84, 24, 14)
    ok:SetPoint("BOTTOMRIGHT", popup, "BOTTOMRIGHT", -8, -8)
    ok:SetScript("OnClick", function()
        ns.PlaySound(1)
        local name = string.match(wdlg.edit and wdlg.edit:GetText() or "", "^%s*(.-)%s*$")
        if name == "" then
            wdlg.hint:SetText(L["请先填写方案名称"])
            wdlg.hint:Show()
            return
        end
        if wdlg.mode == "new" then
            if #(BG.wSchemes or {}) >= W_SCHEME_MAX - 1 then
                wdlg.hint:SetText(L["方案数量已达上限（最多 5 个）"])
                wdlg.hint:Show()
                return
            end
            local base = EffWeights()
            local w = {}
            for _, wk in ipairs(W_KEYS) do w[wk[1]] = base[wk[1]] or 0 end
            BG.wSchemes[#BG.wSchemes + 1] = { name = name, icon = wdlg.picked, w = w }
            BG.wActive = #BG.wSchemes
        else
            local sch = BG.wSchemes[wdlg.idx]
            if sch then
                sch.name = name
                sch.icon = wdlg.picked
            end
        end
        BumpWeights()
        SaveWeightPrefs()
        wdlg.popup:Hide()
        if BG.SyncSettingPop then BG.SyncSettingPop() end
        BG.RequestRender()
    end)
    local back = NewButton(popup, L["返回"], 84, 24, 14)
    back:SetPoint("RIGHT", ok, "LEFT", -8, 0)
    back:SetScript("OnClick", function() ns.PlaySound(1); wdlg.popup:Hide() end)
    wdlg = { popup = popup, title = title, edit = edit, icons = icons, hint = hint, picked = W_ICONS[1] }
    return wdlg
end

local function OpenWeightDialog(mode, idx)
    EnsureWeightDialog()
    if not wdlg then return end
    wdlg.mode = mode
    wdlg.idx = idx
    wdlg.hint:Hide()
    if mode == "edit" then
        local sch = BG.wSchemes and BG.wSchemes[idx] or nil
        if not sch then return end
        wdlg.title:SetText(L["重命名方案"])
        wdlg.edit:SetText(sch.name or "")
        wdlg.picked = sch.icon or W_ICONS[1]
    else
        wdlg.title:SetText(L["添加评分方案"])
        wdlg.edit:SetText("")
        wdlg.picked = W_ICONS[1]
    end
    if wdlg.edit then wdlg.edit:SetFocus() end
    for _, ob in ipairs(wdlg.icons) do SetOutline(ob, ob.icon == wdlg.picked) end
    wdlg.popup:Show()
end

local function WeightSchemeMenu(owner, idx)
    local items = {
        { text = L["应用此方案"], func = function()
            BG.wActive = idx
            BumpWeights()
            SaveWeightPrefs()
            if BG.SyncSettingPop then BG.SyncSettingPop() end
            BG.RequestRender()
        end },
        { text = L["重命名 / 更换图标"], func = function() OpenWeightDialog("edit", idx) end },
        { text = L["删除方案"], func = function()
            table.remove(BG.wSchemes, idx)
            if BG.wActive == idx then
                BG.wActive = nil
            elseif BG.wActive and BG.wActive > idx then
                BG.wActive = BG.wActive - 1
            end
            BumpWeights()
            SaveWeightPrefs()
            if BG.SyncSettingPop then BG.SyncSettingPop() end
            BG.RequestRender()
        end },
    }
    ns.hui.ShowMenu(items, { owner = owner })
end

local SLOT_GEAR = {
    head = { "Head" }, neck = { "Neck" }, shoulder = { "Shoulder" },
    back = { "Back" }, chest = { "Chest" }, wrist = { "Wrist" },
    hands = { "Hands" }, waist = { "Waist" }, legs = { "Legs" }, feet = { "Feet" },
    finger = { "Finger" }, trinket = { "Trinket" },
    shirt = { "Shirt" }, tabard = { "Tabard" },
    ["two-hand"] = { "Two-Hand" }, ["main-hand"] = { "One-Hand", "Main Hand" },
    ["off-hand"] = { "Off Hand", "Held In Off-hand", "Shield" },
    ranged = { "Ranged", "Thrown", "Relic" },
}

local USABLE = {
    warrior = { armor = { 1, 2, 3, 4 },
                weapon = { 0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 13, 15, 16, 18 },
                shield = true },
    paladin = { armor = { 1, 2, 3, 4 }, weapon = { 0, 1, 4, 5, 6 },
                shield = true, relic = { 7 } },
    hunter = { armor = { 1, 2, 3 },
               weapon = { 0, 1, 2, 3, 7, 10, 13, 15, 16, 18 } },
    rogue = { armor = { 1, 2 }, weapon = { 0, 2, 3, 4, 7, 13, 15, 16, 18 } },
    priest = { armor = { 1 }, weapon = { 4, 10, 15, 19 } },
    mage = { armor = { 1 }, weapon = { 7, 10, 15, 19 } },
    warlock = { armor = { 1 }, weapon = { 7, 10, 15, 19 } },
    druid = { armor = { 1, 2 }, weapon = { 4, 5, 10, 13, 15 }, relic = { 8 } },
    shaman = { armor = { 1, 2, 3 }, weapon = { 0, 1, 4, 5, 6, 10, 13, 15 },
               shield = true, relic = { 9 } },
}

local function InList(list, v)
    for i = 1, #list do if list[i] == v then return true end end
    return false
end

local function ClassWear(cls, c, u)
    local t = USABLE[cls]
    if not t then return true end
    if c == 2 then return InList(t.weapon, u) end
    if c == 4 then
        if u == nil or u == 0 or u == 5 then return true end
        if u == 6 then return t.shield and true or false end
        if u >= 1 and u <= 4 then return InList(t.armor, u) end
        if t.relic then return InList(t.relic, u) end
        return false
    end
    return true
end

local CLS_BIT = { warrior = 1, paladin = 2, hunter = 4, rogue = 8, priest = 16,
                  dk = 32, deathknight = 32, shaman = 64, mage = 128,
                  warlock = 256, monk = 512, druid = 1024 }
local function ClsOK(id)
    local m = ns.GearCls and ns.GearCls[id]
    if not m then return true end
    local b = CLS_BIT[BG.cls]
    if not b then return true end
    return bit.band(m, b) ~= 0
end

local catItems, catKey = nil, nil

local function EnsureCatalog()
    local gm = ns.GearModule
    if not (gm and gm.catalog) then
        if gm and gm.BuildCatalog and ns.EnsureGearData then
            ns.EnsureGearData()
            gm.BuildCatalog()
        end
    end
    return gm and gm.catalog or nil
end

local UsableCap
local function CatRowsFor(rkey)
    local cap = UsableCap and UsableCap() or 60
    local key = rkey .. ":" .. tostring(cap) .. ":" .. BG.cls
    if catKey == key then return catItems end
    local slots = SLOT_GEAR[rkey]
    local out = {}
    local cat = EnsureCatalog()
    if cat and slots then
        for i = 1, #cat do
            local r = cat[i]
            if r.s and InList(slots, r.s) and ClassWear(BG.cls, r.c, r.u) and ClsOK(r.id)
                and (r.req or 0) <= cap then
                out[#out + 1] = r
            end
        end
    end
    catItems, catKey = out, key
    return out
end

local function CatSrcOf(id)
    local gm = ns.GearModule
    local so = gm and gm.srcOf and gm.srcOf[id]
    if so and so.inst then return nil, so end
    local gs = ns.EnsureGearSrc and ns.EnsureGearSrc()
    local src = gs and gs[id]
    if type(src) == "string" and src ~= "" then return src end
    return ""
end

local function CatKind(id)
    local _, so = CatSrcOf(id)
    if so then return "boss" end
    local src = CatSrcOf(id)
    local kind = string.match(src, "^(.-)|") or src
    if kind == "任务奖励" then return "quest" end
    if kind == "商人" then return "vendor" end
    if string.find(kind, "制作", 1, true) or string.find(kind, "（", 1, true) then
        return "craft"
    end
    if kind == "世界掉落" or kind == "怪物掉落" or kind == "任何敌人"
        or kind == "稀有掉落" or kind == "小怪掉落" or kind == "物件" then
        return "rare"
    end
    return "other"
end

local function CatSrcText(id)
    local src, so = CatSrcOf(id)
    if so then
        local nm = so.inst and so.inst.name or ""
        if so.boss and so.boss ~= "" then return nm .. " · " .. so.boss end
        return nm
    end
    return string.gsub(src, "|", " · ")
end

local ROW_H = 46
local PLAN_H = 28
BG.PLAN_TALL = 40
BG.CHIP_INK_PRESET = { 0.52, 0.68, 0.94 }
local LIST_PAD = 8

local BT = BackdropTemplateMixin and "BackdropTemplate" or nil
local function Cardify(f, bgA, edA)
    if not f.SetBackdrop then return end
    f:SetBackdrop({
        bgFile = "Interface\\Buttons\\WHITE8x8",
        edgeFile = "Interface\\Buttons\\WHITE8x8",
        edgeSize = 1,
        insets = { left = 1, right = 1, top = 1, bottom = 1 },
    })
    f:SetBackdropColor(1, 1, 1, bgA or 0.035)
    f:SetBackdropBorderColor(1, 1, 1, edA or 0.09)
end

local function BuildPanels(page)
    BG.panels = {}
    for i = 1, 5 do
        local p = CreateFrame("Frame", nil, page, BT)
        if ns.hui and ns.hui.BuildRoundedBG then
            ns.hui.BuildRoundedBG(p, 8, ns.hui.layer.L1, "both", true, 1)
        else
            Cardify(p, 0.05, 0.12)
        end
        BG.panels[i] = p
    end
end

local function PlansFor(slug)
    local s = DB()
    if not s.plans[slug] then s.plans[slug] = {} end
    return s.plans[slug]
end

local function MigratePlans()
    local s = DB()
    if s.migVol then return end
    s.migVol = true
    local lv = VOLS[1] and VOLS[1].lv or 20
    local pre = format(L["%d级 · "], lv)
    for _, list in pairs(s.plans) do
        for _, p in ipairs(list) do
            if type(p) == "table" and p.vol == nil then
                p.vol = lv
                local nm = tostring(p.name or "")
                if string.sub(nm, 1, #pre) ~= pre then
                    p.name = pre .. nm
                end
            end
        end
    end
end

local function MigrateTSpec()
    local s = DB()
    if s.migTS then return end
    s.migTS = true
    for slug, list in pairs(s.plans) do
        if type(list) == "table" then
            local tk, nt
            for _, sr in ipairs(SPEC_DIR[slug] or {}) do
                if sr.role == "tank" then tk = tk or sr.key else nt = nt or sr.key end
            end
            for _, p in ipairs(list) do
                if type(p) == "table" then
                    if p.tspec == "feral" then p.tspec = "cat" end
                    local bad = p.tspec == nil
                    if not bad then
                        bad = true
                        for _, sr in ipairs(SPEC_DIR[slug] or {}) do
                            if sr.key == p.tspec then bad = false break end
                        end
                    end
                    if bad then
                        p.tspec = (p.spec == "tank" and tk) or nt
                    end
                end
            end
        end
    end
end

local __playerCls
local function PlayerClassSlug()
    if __playerCls then return __playerCls end
    local ok, _, file = pcall(UnitClass, "player")
    if not ok or type(file) ~= "string" or file == "" then return nil end
    for slug, f in pairs(CLASS_FILE) do
        if f == file then __playerCls = slug break end
    end
    return __playerCls
end

BG.cls = PlayerClassSlug() or "warrior"
BG.spec = "pve"
BG.pkey = nil
BG.vol = nil
BG.cur = {}
BG.ench = {}
BG.usingPlan = nil
BG.search = ""
BG.filterLv = nil
BG.onlyUsable = true
BG.srcSet = {}
BG.sel = nil
BG.wSchemes = {}
BG.wActive = nil
BG.wGen = 0
BG.autoPlan = nil

local function LoadFilterPrefs()
    local s = DB()
    if s.fOnlyUsable == nil then s.fOnlyUsable = true end
    BG.onlyUsable = s.fOnlyUsable and true or false
    local lv = s.fFilterLv
    BG.filterLv = (type(lv) == "number" and lv >= 1 and lv <= 60) and math.floor(lv) or nil
    if s.fSrcVer ~= 3 then
        s.fSrcVer = 3
        local ss = s.fSrcSet
        if ss == nil then
            ss = {}
            for _, f in ipairs(FILTERS) do ss[f.id] = true end
        end
        ss.other = nil
        s.fSrcSet = ss
    end
    BG.srcSet = {}
    for _, f in ipairs(FILTERS) do
        BG.srcSet[f.id] = (s.fSrcSet[f.id] == true)
    end
end

local function SaveFilterPrefs()
    local s = DB()
    s.fOnlyUsable = BG.onlyUsable and true or nil
    s.fFilterLv = BG.filterLv
    local ss = {}
    for _, f in ipairs(FILTERS) do
        if BG.srcSet[f.id] then ss[f.id] = true end
    end
    s.fSrcSet = ss
end

local function PlayerLevel()
    local ok, lv = pcall(UnitLevel, "player")
    return (ok and type(lv) == "number" and lv > 0) and lv or nil
end

UsableCap = function()
    if not BG.onlyUsable then return 60 end
    return tonumber(BG.filterLv) or PlayerLevel() or 60
end

local __pfac = nil
local function PlayerFac()
    if __pfac == nil then
        local ok, fg = pcall(UnitFactionGroup, "player")
        __pfac = (ok and fg == "Horde") and "h" or "a"
    end
    return __pfac
end

local function GearSrcReady()
    if type(ns.GearSrcQ) ~= "table" then
        local fn = ns.EnsureGearData
        if type(fn) == "function" then fn() end
    end
end

local function UsableAt(id, lv, catReq)
    GearSrcReady()
    local _, _, _, _, req = DG.ItemInfo(id)
    if type(req) == "number" and req > 0 and req > lv then return false end
    if type(catReq) == "number" and catReq > lv then return false end
    local qlv = ns.GearSrcQLv and ns.GearSrcQLv[id]
    if type(qlv) == "number" and qlv > 0 and qlv > lv then return false end
    local gm = ns.GearModule
    local so = gm and gm.srcOf and gm.srcOf[id]
    local inst = so and so.inst
    if inst and type(inst.levelMin) == "number" and inst.levelMin > lv then return false end
    local qid = ns.GearSrcQ and ns.GearSrcQ[id]
    local fac = qid and ns.GearQuestRace and ns.GearQuestRace[qid]
    if fac and fac ~= PlayerFac() then return false end
    return true
end

local function ClassRec()
    for _, c in ipairs(CurVol().classes) do
        if c.slug == BG.cls then return c end
    end
end

local function SpecRec()
    local c = ClassRec()
    if not c then return nil end
    local byId, byT, exact = nil, nil, nil
    for _, sp in ipairs(c.specs) do
        local idHit = (sp.id == BG.spec)
        local tHit = (BG.tspec ~= nil and sp.tspec == BG.tspec)
        if idHit then byId = byId or sp end
        if tHit then byT = byT or sp end
        if idHit and tHit then
            if BG.pkey and BG.pkey == sp.key then return sp end
            exact = exact or sp
        end
    end
    return exact or byT or byId or c.specs[1]
end

local function SyncSpecFromTspec()
    local c = ClassRec()
    if not (c and BG.tspec) then return end
    for _, sp in ipairs(c.specs) do
        if sp.tspec == BG.tspec and sp.id then
            BG.spec = sp.id
            BG.pkey = sp.key
            return
        end
    end
end

local function SpecLabel()
    for _, def in ipairs(SPEC_DEFS) do
        if def.id == BG.spec then return def.label end
    end
    return string.upper(BG.spec)
end

local function TSpecLabel()
    for _, sr in ipairs(SPEC_DIR[BG.cls] or {}) do
        if sr.key == BG.tspec then return L[sr.label] or sr.label end
    end
    return SpecLabel()
end

local function RecItem(sp, slotKey)
    if not sp then return nil end
    local sides = sp.slots[slotKey]
    if type(sides) ~= "table" then return nil end
    local s = sides[(BG.side or PlayerFac()) == "h" and 2 or 1]
    if type(s) ~= "table" then return nil end
    return s[1], s[2], s[3]
end

local function CurSide()
    return BG.side or PlayerFac()
end

local function SideHas(sp, slotKey, side)
    local sides = sp and sp.slots and sp.slots[slotKey]
    if type(sides) ~= "table" then return false end
    local s = sides[(side or CurSide()) == "h" and 2 or 1]
    return type(s) == "table" and s[1] ~= nil
end

local function MainKey(sp, side)
    if not sp then return "main-hand" end
    side = side or CurSide()
    if SideHas(sp, "two-hand", side) then return "two-hand" end
    if SideHas(sp, "main-hand", side) then return "main-hand" end
    if sp.slots["two-hand"] then return "two-hand" end
    return "main-hand"
end

local function OffKey(sp, side)
    if not sp then return "off-hand" end
    side = side or CurSide()
    for _, k in ipairs({ "off-hand", "held", "shield" }) do
        if SideHas(sp, k, side) then return k end
    end
    for _, k in ipairs({ "off-hand", "held", "shield" }) do
        if sp.slots[k] then return k end
    end
    return "off-hand"
end

local function DataKey(sp, slotKey)
    if slotKey == "main" or slotKey == "two-hand" or slotKey == "main-hand" then
        if slotKey == "two-hand" and not SideHas(sp, "two-hand") then
            return MainKey(sp)
        end
        if slotKey == "main-hand" and not SideHas(sp, "main-hand") then
            return MainKey(sp)
        end
        return slotKey == "main" and MainKey(sp) or slotKey
    end
    if slotKey == "off" or slotKey == "off-hand" or slotKey == "held" or slotKey == "shield" then
        if MainKey(sp) == "two-hand" then return "off-hand" end
        return OffKey(sp)
    end
    if slotKey == "ranged" then return "ranged" end
    return slotKey
end

local function CurItem(sp, slotKey)
    local dk = DataKey(sp, slotKey)
    local id = BG.cur[dk]
    if id then return id end
    local pl = BG.usingPlan
    if pl and pl.items and pl.items[dk] then return pl.items[dk] end
    if BG.usingPlan == nil and BG.autoPlan == nil then return RecItem(sp, dk) end
    return nil
end

local ENCH_SLOTS = {
    [ns.DL("颈部")] = { "neck" }, [ns.DL("背部")] = { "back" }, [ns.DL("胸部")] = { "chest" },
    [ns.DL("手腕")] = { "wrist" }, [ns.DL("手部")] = { "hands" }, [ns.DL("腿部")] = { "legs" },
    [ns.DL("脚")] = { "feet" }, [ns.DL("肩部")] = { "shoulder" }, [ns.DL("双手武器")] = { "two-hand" },
    [ns.DL("主手")] = { "main-hand" }, [ns.DL("副手")] = { "off-hand" },
    [ns.DL("副手：盾牌")] = { "off-hand" }, [ns.DL("远程")] = { "ranged" },
    [ns.DL("手部、腿部")] = { "hands", "legs" }, [ns.DL("主手、副手")] = { "main-hand", "off-hand" },
}

local ENCH_PART = {
    [ns.DL("护腕")] = ns.DL("手腕"), [ns.DL("手套")] = ns.DL("手部"),
    [ns.DL("武器")] = ns.DL("主手"), [ns.DL("双手武器")] = ns.DL("双手武器"),
    [ns.DL("披风")] = ns.DL("背部"), [ns.DL("胸甲")] = ns.DL("胸部"),
    [ns.DL("靴子")] = ns.DL("脚"), [ns.DL("盾牌")] = ns.DL("副手：盾牌"),
    [ns.DL("项链")] = ns.DL("颈部"),
}

local ENCH_DB = nil

local function KitEff(text)
    if type(text) ~= "string" then return "" end
    local parts = {}
    local sta = string.match(text, "Stamina value by (%d+)")
    local ap = string.match(text, "Attack Power value by (%d+)")
    local sp = string.match(text, "Spell Power value by (%d+)")
    local def = string.match(text, "Defense Skill by (%d+)")
        or string.match(text, "hands or feet by (%d+)")
    local arm = string.match(text, "[Aa]rmor value by (%d+)")
    if sta then parts[#parts + 1] = L["耐力"] .. " +" .. sta end
    if ap then parts[#parts + 1] = L["攻击强度"] .. " +" .. ap end
    if sp then parts[#parts + 1] = L["法术强度"] .. " +" .. sp end
    if def then parts[#parts + 1] = L["防御技能"] .. " +" .. def end
    if arm then parts[#parts + 1] = L["护甲"] .. " +" .. arm end
    return table.concat(parts, "，")
end

local function EnsureEnchDB()
    if ENCH_DB then return ENCH_DB end
    if type(ns.EnsureProfRecipes) == "function" then
        ns.EnsureProfRecipes({ "enchanting", "leatherworking" })
    end
    local pr = ns.ProfRecipes
    local src = pr and pr.enchanting and pr.enchanting.enchants
    local db = {}
    local CLASSES = { "warrior", "paladin", "hunter", "rogue",
                      "priest", "mage", "warlock", "druid", "shaman" }
    local function AddEntry(entry)
        for _, cls in ipairs(CLASSES) do
            for _, spec in ipairs({ "pve", "pvp", "tank" }) do
                local k = cls .. ":" .. spec
                local list = db[k]
                if not list then list = {} db[k] = list end
                list[#list + 1] = entry
            end
        end
    end
    for _, e in ipairs(src or {}) do
        local slot = ENCH_PART[e[3]]
        if slot then
            AddEntry({ slot = slot, name = e[2], eff = e[4],
                       lvl = tonumber(e[5]) or nil, mats = e[9] })
        end
    end
    local lw = pr and pr.leatherworking or nil
    if lw and type(lw.rows) == "table" then
        for _, r in ipairs(lw.rows) do
            if type(r) == "table" and r[4] == "Kits" and type(r[2]) == "number" then
                local eff = KitEff(r[6])
                local req = tonumber(string.match(r[6] or "", "Only usable on items level (%d+) and above")) or nil
                for _, slot in ipairs({ ns.DL("胸部"), ns.DL("腿部"), ns.DL("手部"), ns.DL("脚") }) do
                    AddEntry({ slot = slot, item = r[2], eff = eff,
                               lvl = tonumber(r[7]) or nil, mats = r[12], req = req })
                end
            end
        end
    end
    ENCH_DB = db
    return ENCH_DB
end

local function EnchCap(lvOverride)
    if lvOverride then return tonumber(lvOverride) or nil end
    if BG.onlyUsable then return tonumber(BG.filterLv) or PlayerLevel() or 60 end
    return nil
end

local function EnchRowsFor(sp, dk)
    local out = {}
    if not dk then return out end
    local db = EnsureEnchDB()
    local list = db[BG.cls .. ":" .. (sp and sp.id or BG.spec)]
    if list and #list > 0 then
        local seen = {}
        for _, e in ipairs(list) do
            for _, k in ipairs(ENCH_SLOTS[e.slot] or {}) do
                if k == dk then
                    local key = tostring(e.eff or "") .. "|" .. tostring(e.lvl or "")
                    if not seen[key] then
                        seen[key] = true
                        out[#out + 1] = e
                    end
                    break
                end
            end
        end
        table.sort(out, function(a, b)
            local la, lb = tonumber(a.lvl) or 0, tonumber(b.lvl) or 0
            if la ~= lb then return la > lb end
            return tostring(a.name or a.eff or "") < tostring(b.name or b.eff or "")
        end)
    end
    return out
end

local function EnchCat(e)
    local s = tostring(e.eff or "") .. tostring(e.name or "")
    local has = function(w) return string.find(s, w, 1, true) ~= nil end
    if has(L["力量"]) or has(L["敏捷"]) or has(L["智力"]) or has(L["精神"]) then return "main" end
    if has(L["耐力"]) then return "sta" end
    if has(L["抗性"]) then return "res" end
    if has(L["攻击强度"]) or has(L["法术强度"]) or has(L["伤害"]) or has(L["治疗"]) then return "pow" end
    if has(L["几率"]) or has(L["触发"]) or has(L["命中时"]) then return "proc" end
    return "misc"
end

local function EnchMatchFilter(e)
    local f = BG.enchFilter
    if not f then return true end
    return EnchCat(e) == f
end

local function EnchToken(e)
    return e.item or e.eff
end

local function EnchName(e)
    if e.item then
        local nm = DG.ItemName(e.item) or ""
        for _, p in ipairs({ L["公式："], L["公式: "], L["公式:"] }) do
            if string.sub(nm, 1, #p) == p then
                return string.sub(nm, #p + 1)
            end
        end
        return nm
    end
    return e.name or e.eff or ""
end

local function EnchFind(sp, tok)
    local db = EnsureEnchDB()
    local list = db[BG.cls .. ":" .. (sp and sp.id or BG.spec)]
    for _, e in ipairs(list or {}) do
        if e.eff == tok then return e end
    end
    return nil
end

local function EnchText(sp, tok)
    if tok == nil then return "" end
    local e = EnchFind(sp, tok)
    if e then
        return e.name or EnchName(e) or e.eff or ""
    end
    if type(tok) == "string" then return tok end
    return DG.ItemName(tok)
end

local function PlanEnch(sp, dk)
    if not sp or type(sp.enchs) ~= "table" or not dk then return nil end
    for _, e in ipairs(sp.enchs) do
        for _, k in ipairs(ENCH_SLOTS[e.slot] or {}) do
            if k == dk then return e end
        end
    end
    return nil
end

local function CurEnch(sp, dk, lvOverride)
    local id = BG.ench and BG.ench[dk]
    if id then return id end
    local pl = BG.usingPlan
    if pl and pl.enchs and pl.enchs[dk] then return pl.enchs[dk] end
    local pe = PlanEnch(sp, dk)
    if pe then return pe.eff or EnchToken(pe) end
    local capSel = lvOverride and lvOverride * 5 or nil
    local cap = EnchCap(lvOverride)
    local rec
    for _, e in ipairs(EnchRowsFor(sp, dk)) do
        if not (cap and e.req and e.req > cap)
           and not (capSel and e.lvl and e.lvl > capSel) then rec = e break end
    end
    if rec then return EnchToken(rec) end
    return nil
end

local CLASS_CN = {
    warrior = L["战士"], paladin = L["圣骑士"], hunter = L["猎人"], rogue = L["潜行者"],
    priest = L["牧师"], mage = L["法师"], warlock = L["术士"], druid = L["德鲁伊"],
    shaman = L["萨满祭司"],
}
local function ClassName(slug)
    local file = CLASS_FILE[slug]
    local T = type(LOCALIZED_CLASS_NAMES) == "table" and LOCALIZED_CLASS_NAMES
    local loc = T and file and T[file]
    return loc or CLASS_CN[slug] or file or slug
end

local function QColor(q)
    if type(q) == "number" then return QUALITY_COLORS[q] or C_TEXT end
    return C_TEXT
end

local function ItemQuality(sp, itemID, siteQ)
    local _, _, cq = DG.ItemInfo(itemID)
    if type(cq) == "number" then return cq end
    if sp and type(siteQ) == "number" then return siteQ end
    return nil
end

local function ItemIcon(itemID)
    if itemID == nil then return FALLBACK_ICON end
    if C_Item and type(C_Item.GetItemIconByID) == "function" then
        local ok, ic = pcall(C_Item.GetItemIconByID, itemID)
        if ok and type(ic) == "number" and ic ~= 0 then return ic end
    end
    if type(GetItemIcon) == "function" then
        local ok, ic = pcall(GetItemIcon, itemID)
        if ok and type(ic) == "number" and ic ~= 0 then return ic end
    end
    local info = { DG.ItemInfo(itemID) }
    if type(info[10]) == "number" and info[10] ~= 0 then return info[10] end
    local ins = { DG.ItemInfoInstant(itemID) }
    if type(ins[10]) == "number" and ins[10] ~= 0 then return ins[10] end
    return FALLBACK_ICON
end

local function ItemTip(owner, itemID, extra)
    if not GameTooltip then return end
    GameTooltip:SetOwner(owner, "ANCHOR_RIGHT")
    GameTooltip:ClearLines()
    local link = DG.ItemLink(itemID)
    local ok = false
    if link then
        ok = pcall(GameTooltip.SetHyperlink, GameTooltip, link)
            and type(GameTooltip.NumLines) == "function"
            and (GameTooltip:NumLines() or 0) > 0
    end
    if not ok then
        GameTooltip:AddLine(DG.ItemName(itemID), 0.8, 0.8, 0.8, true)
    end
    if extra then
        for _, ln in ipairs(extra) do
            GameTooltip:AddLine(ln, 0.55, 0.75, 0.55, true)
        end
    end
    GameTooltip:Show()
end

local function TipOff()
    if GameTooltip then pcall(GameTooltip.Hide, GameTooltip) end
end

local function EnchTip(owner, e)
    if not GameTooltip or not e then return end
    GameTooltip:SetOwner(owner, "ANCHOR_RIGHT")
    GameTooltip:ClearLines()
    GameTooltip:AddLine(EnchName(e), 1, 0.82, 0.4, true)
    if e.eff and e.eff ~= "" then
        GameTooltip:AddLine(e.eff, 0.9, 0.9, 0.9, true)
    end
    if e.lvl then
        GameTooltip:AddLine(format(L["附魔 %d"], e.lvl), 0.6, 0.65, 0.7, true)
    end
    if type(e.mats) == "table" and #e.mats > 0 then
        local parts = {}
        for _, m in ipairs(e.mats) do
            parts[#parts + 1] = (DG.ItemName(m[1]) or tostring(m[1])) .. " x" .. tostring(m[2] or 1)
        end
        GameTooltip:AddLine(format(L["材料：%s"], table.concat(parts, "、")), 0.7, 0.7, 0.7, true)
    end
    GameTooltip:Show()
end

local function LinkToChat(itemID)
    if DG and DG.InsertItemLink then
        DG.InsertItemLink(itemID)
        return
    end
    local _, link = DG.ItemInfo(itemID)
    if link and ChatFrame_InsertLink then
        ChatFrame_InsertLink(link)
    end
end

local PROF_NAMES = {
    blacksmithing = L["锻造"], leatherworking = L["制皮"], tailoring = L["裁缝"],
    alchemy = L["炼金"], engineering = L["工程学"], enchanting = L["附魔"],
    cooking = L["烹饪"], firstaid = L["急救"], fishing = L["钓鱼"],
}

local function QuestTitle(qid)
    if not (C_QuestLog and C_QuestLog.GetTitleForQuestID) then return nil end
    local ok, t = pcall(C_QuestLog.GetTitleForQuestID, qid)
    if ok and type(t) == "string" and t ~= "" then return t end
    return nil
end

local function SrcText(src)
    if type(src) ~= "table" then return "" end
    local t = src.t
    if t == "quest" then
        local qid = src.q and tonumber(src.q) or nil
        local qn = qid and QuestTitle(qid) or nil
        local head = L["任务："] .. (qn or (qid and ("#" .. qid) or "?"))
        if not src.note or src.note == "" then return head end
        local note = src.note:gsub("(%d+)%s*级起", "%1级可接")
        note = note:gsub("(%d+)%s*級起", "%1級可接")
        note = note:gsub("[、，]", " · ")
        return head .. " · " .. note
    elseif t == "boss" then
        local who = src.boss and (src.boss .. " · ") or ""
        return who .. (src.dung or L["副本"]) .. (src.rate and (" · " .. src.rate) or "")
    elseif t == "craft" then
        local pn = PROF_NAMES[src.prof] or src.prof or L["制造"]
        return pn .. (src.lvl and format("（%d）", src.lvl) or "")
            .. (src.note and (" · " .. src.note) or "")
    elseif t == "rare" then
        return L["稀有 · "] .. (src.note or "")
    elseif t == "books" then
        return src.note or L["图书馆之友"]
    end
    return src.note or ""
end

local ALL_SLOT_KEYS = {}
for _, k in ipairs(SLOTS_LEFT) do ALL_SLOT_KEYS[#ALL_SLOT_KEYS + 1] = k end
for _, k in ipairs(SLOTS_RIGHT) do ALL_SLOT_KEYS[#ALL_SLOT_KEYS + 1] = k end
ALL_SLOT_KEYS[#ALL_SLOT_KEYS + 1] = "two-hand"
ALL_SLOT_KEYS[#ALL_SLOT_KEYS + 1] = "main-hand"
ALL_SLOT_KEYS[#ALL_SLOT_KEYS + 1] = "off-hand"
ALL_SLOT_KEYS[#ALL_SLOT_KEYS + 1] = "ranged"

local function SumStats()
    local sp = SpecRec()
    local acc = {}
    if not sp then return acc end
    local seen = {}
    local dkMain, dkOff = MainKey(sp), OffKey(sp)
    for _, key in ipairs(ALL_SLOT_KEYS) do
        local dk = key
        if key == "two-hand" or key == "main-hand" then
            dk = dkMain
        elseif key == "off-hand" then
            dk = (dkMain == "two-hand") and nil or dkOff
        end
        local id = dk and CurItem(sp, dk) or nil
        if id and not seen[id] then
            seen[id] = true
            local fn = GetItemStats or (C_Item and C_Item.GetItemStats)
            if type(fn) == "function" then
                local ok, stats = pcall(fn, DG.ItemLink(id))
                if ok and type(stats) == "table" then
                    for k, v in pairs(stats) do
                        if type(v) == "number" then acc[k] = (acc[k] or 0) + v end
                    end
                end
            end
        end
    end
    return acc
end

local function PaintTopbar()
    local dir = SPEC_DIR[BG.cls] or {}
    for i = 1, 4 do
        local bt = BG.tspecBtns and BG.tspecBtns[i]
        if bt then
            local sr = dir[i]
            if sr then
                bt:SetShown(true)
                bt:SetText(L[sr.label] or sr.label)
                if bt.__icon then bt.__icon:SetTexture(sr.icon) end
                local on = (sr.role == "tank" and BG.spec == "tank")
                    or (sr.role ~= "tank" and BG.spec ~= "tank" and BG.tspec == sr.key)
                SetButtonSelected(bt, on)
            else
                bt:SetShown(false)
            end
        end
    end
    if BG.ddBtn then
        BG.ddBtn:SetText(ClassName(BG.cls))
        local rc = RAID_CLASS_COLORS and RAID_CLASS_COLORS[CLASS_FILE[BG.cls] or ""]
        if rc and rc.r then BG.ddBtn.lbl:SetTextColor(rc.r, rc.g, rc.b) end
        if BG.ddBtn.__icon then BG.ddBtn.__icon:SetTexture(ClassIconPath(BG.cls)) end
    end
    BG.head:SetText(format("%s · %s", ClassName(BG.cls), TSpecLabel()))
end

local function PaintDoll()
    local sp = SpecRec()
    if not sp then return end
    local mk = MainKey(sp)
    local ok2 = (mk == "two-hand") and "off-hand" or OffKey(sp)
    for key, cell in pairs(BG.dollCells) do
        local dkey = key
        if key == "main" then dkey = mk end
        if key == "off" then dkey = ok2 end
        if key == "ranged" then dkey = "ranged" end
        cell.__dkey = dkey
        local id, q, ench = CurItem(sp, key)
        local empty = not id
        if key == "off" and mk == "two-hand" then empty = true end
        if empty then
            cell.icon:SetTexture("")
            cell.name:SetText(key == "off" and mk == "two-hand"
                and L["被双手武器占用"] or "—")
            cell.name:SetTextColor(Unpack(C_DIM))
        else
            cell.icon:SetTexture(ItemIcon(id))
            cell.name:SetText(DG.ItemName(id))
            cell.name:SetTextColor(Unpack(QColor(ItemQuality(sp, id, q))))
        end
        local capLv = nil
        if BG.usingPlan then capLv = BG.usingPlan.vol end
        if empty then
            cell.ench:SetText("")
        else
            cell.ench:SetText(EnchText(sp, CurEnch(sp, dkey, capLv)))
        end
        local sel = BG.sel ~= nil and BG.sel == key
        cell.__sel = sel
        if cell.__huiCard then
            ns.hui.HuiCardState(cell, (sel or cell:IsMouseOver()) and "hover" or "norm")
        end
        cell.dot:SetShown(BG.cur[dkey] ~= nil)
    end
end

local function PaintStats()
    local acc = SumStats()
    local n = 0
    for i, row in ipairs(BG.statRows) do
        local col = (i > 5) and 2 or 1
        local r = (col == 1) and (i - 1) or (i - 6)
        local ry = 32 + r * ((ENCH_CARD_H - 60) / 4)
        local lx = (col == 1) and 8 or 112
        local vx = (col == 1) and 106 or 216
        local v = acc[row[1]] or 0
        row.lab:ClearAllPoints()
        row.lab:SetPoint("TOPLEFT", BG.statParent, "TOPLEFT", lx, -ry)
        row.val:ClearAllPoints()
        row.val:SetPoint("TOPRIGHT", BG.statParent, "TOPLEFT", vx, -ry)
        row.val:SetText(tostring(v))
        row.val:SetTextColor(Unpack(C_GREEN))
        row.lab:Show()
        row.val:Show()
        n = n + 1
    end
    BG.LayoutMid()
end

function BG.LayoutMid()
    if not (BG.page and BG.py and BG.panels and BG.panels[2] and BG.panels[3]) then return end
    local statH = ENCH_CARD_H
    local p3 = BG.panels[3]
    p3:ClearAllPoints()
    p3:SetPoint("TOPLEFT", BG.page, "BOTTOMLEFT", 399, PAGE_INSET + statH)
    p3:SetPoint("BOTTOMRIGHT", BG.page, "BOTTOMLEFT", 623, PAGE_INSET)
    local p2 = BG.panels[2]
    p2:ClearAllPoints()
    p2:SetPoint("TOPLEFT", BG.page, "TOPLEFT", 399, -BG.py)
    p2:SetPoint("BOTTOMRIGHT", p3, "TOPLEFT", 224, 8)
end

do
local AUTO_SRC_KNOWN = { craft = true, quest = true, boss = true, rare = true, vendor = true }
local AUTO_SRC_DQ = { boss = true, quest = true }
local AUTO_SNAP_MAX = 6
local AUTO_BUDGET_MS = 6

BG.AUTO_SRC = { known = AUTO_SRC_KNOWN, dq = AUTO_SRC_DQ }

function BG.AutoLevel()
    local lv = tonumber(BG.filterLv) or PlayerLevel() or 60
    lv = math.floor(lv)
    if lv < 1 then lv = 1 elseif lv > 60 then lv = 60 end
    return lv
end

local function CopyCur(src)
    local out = {}
    if type(src) == "table" then
        for k, v in pairs(src) do out[k] = v end
    end
    return out
end

local function ManualSlot(cls, tspec)
    return tostring(cls or "") .. "|" .. tostring(tspec or "")
end

local function ManualGet()
    local t = DB().manual
    if type(t) ~= "table" then return nil end
    local p = t[ManualSlot(BG.cls, BG.tspec)]
    if type(p) == "table" and type(p.items) == "table" then return p end
    return nil
end
BG.ManualPlan = ManualGet

local function ManualPut(items, cls, tspec, lv, srcSet)
    local s = DB()
    local t = s.manual
    if type(t) ~= "table" then
        t = {}
        s.manual = t
    end
    local key = ManualSlot(cls, tspec)
    local p = t[key]
    if type(p) ~= "table" then
        p = {}
        t[key] = p
    end
    p.manual = true
    p.name = L["手动过滤生成的BIS结果"]
    p.cls = cls
    p.tspec = tspec
    p.vol = lv
    p.items = CopyCur(items)
    local ss = {}
    for k, v in pairs(srcSet or {}) do ss[k] = v end
    p.srcSet = ss
    return p
end

local autoVer

local function AutoVer()
    if autoVer then return autoVer end
    local fn = (C_AddOns and C_AddOns.GetAddOnMetadata) or GetAddOnMetadata
    local v
    if type(fn) == "function" then
        local ok, r = pcall(fn, "DungeonsForever", "Version")
        if ok and type(r) == "string" and r ~= "" then v = r end
    end
    if not v then v = tostring(ns.version or "0") end
    autoVer = v
    return autoVer
end

local function AutoSig(mode, cap)
    return table.concat({ tostring(AutoVer()), tostring(BG.cls or ""),
        tostring(BG.spec or ""), tostring(BG.tspec or ""), tostring(mode),
        tostring(cap), tostring(BG.wGen or 0), tostring(BG.wActive or 0),
        PlayerFac() or "" }, "|")
end

local autoSnaps, autoSnapsLoaded = {}, false

local function NowSec()
    local f = time
    if type(f) ~= "function" then return 0 end
    local ok, v = pcall(f)
    if ok and type(v) == "number" then return v end
    return 0
end

local function LoadAutoSnaps()
    autoSnapsLoaded = true
    autoSnaps = {}
    local list = DB().autoSnaps
    if type(list) ~= "table" then return end
    for i = 1, #list do
        local e = list[i]
        if type(e) == "table" and type(e.sig) == "string" and type(e.items) == "table" then
            autoSnaps[e.sig] = e
        end
    end
end

local function SaveAutoSnaps()
    local list = {}
    for _, e in pairs(autoSnaps) do list[#list + 1] = e end
    table.sort(list, function(a, b) return (a.t or 0) > (b.t or 0) end)
    while #list > AUTO_SNAP_MAX do table.remove(list) end
    local keep = {}
    for _, e in ipairs(list) do keep[e.sig] = e end
    autoSnaps = keep
    DB().autoSnaps = list
end

local function AutoStore(mode, cap, sig, items, cls)
    if not autoSnapsLoaded then LoadAutoSnaps() end
    autoSnaps[sig] = { sig = sig, mode = mode, cls = cls, lv = cap,
                       t = NowSec(), items = CopyCur(items) }
    SaveAutoSnaps()
end

local function AutoStale(mode)
    if not autoSnapsLoaded then LoadAutoSnaps() end
    local best, any
    for _, e in pairs(autoSnaps) do
        if e.cls == BG.cls then
            if e.mode == mode and (not best or (e.t or 0) > (best.t or 0)) then best = e end
            if not any or (e.t or 0) > (any.t or 0) then any = e end
        end
    end
    return best or any
end

local autoJob, autoJobSeq = nil, 0

function BG.PaintAutoProg(frac)
    local host = BG.panels and BG.panels[2]
    if not host then return end
    local h = BG.autoProg
    if frac == nil then
        if h and h:IsShown() then h:Hide() end
        if BG.saveBtn then BG.saveBtn:Show() end
        if BG.resetBtn then BG.resetBtn:Show() end
        return
    end
    if not h then
        h = CreateFrame("Frame", nil, host)
        h:SetHeight(24)
        h:SetPoint("TOPLEFT", host, "TOPLEFT", 8, -40)
        h:SetPoint("TOPRIGHT", host, "TOPRIGHT", -8, -40)
        h:SetFrameLevel((host:GetFrameLevel() or 0) + 5)
        h.fs = MakeFS(h, 14, C_GOLD, "LEFT")
        h.fs:SetPoint("TOPLEFT", h, "TOPLEFT", 0, 0)
        h.fs:SetWordWrap(false)
        local tr = CreateFrame("Frame", nil, h)
        tr:SetHeight(4)
        tr:SetPoint("BOTTOMLEFT", h, "BOTTOMLEFT", 0, 0)
        tr:SetPoint("BOTTOMRIGHT", h, "BOTTOMRIGHT", 0, 0)
        if ns.hui and ns.hui.BuildCapsule then
            ns.hui.BuildCapsule(tr, 2, ns.hui.layer.L2)
        else
            local bt = tr:CreateTexture(nil, "BACKGROUND")
            bt:SetAllPoints()
            bt:SetColorTexture(0, 0, 0, 0.45)
        end
        local fill = CreateFrame("Frame", nil, tr)
        fill:SetHeight(4)
        fill:SetWidth(2)
        fill:SetPoint("LEFT", tr, "LEFT", 0, 0)
        if ns.hui and ns.hui.BuildCapsule then
            ns.hui.BuildCapsule(fill, 2, { 0.93, 0.76, 0.32 })
        else
            local ft = fill:CreateTexture(nil, "ARTWORK")
            ft:SetAllPoints()
            ft:SetColorTexture(0.93, 0.76, 0.32, 1)
        end
        h.track, h.fill = tr, fill
        BG.autoProg = h
    end
    if BG.saveBtn then BG.saveBtn:Hide() end
    if BG.resetBtn then BG.resetBtn:Hide() end
    h:Show()
    if h.track then h.track:SetAlpha(1) end
    h.fs:SetTextColor(Unpack(C_GOLD))
    if frac < 0 then frac = 0 elseif frac > 1 then frac = 1 end
    local pct = math.floor(frac * 100 + 0.5)
    if h.pct ~= pct then
        h.pct = pct
        h.fs:SetText(format(L["正在生成方案"] .. " %d%%", pct))
    end
    local w = h:GetWidth() or 0
    if w < 2 then w = 192 end
    local fw = math.floor(w * frac + 0.5)
    if fw < 2 then fw = 2 end
    h.fill:SetWidth(fw)
end

function BG.WarnEmpty()
    local names = {}
    for _, f in ipairs(FILTERS) do
        if BG.srcSet[f.id] then names[#names + 1] = f.label end
    end
    local src = (#names > 0) and table.concat(names, " · ") or L["未选来源"]
    local msg = format(L["%d级 · "], BG.AutoLevel()) .. src .. " · " .. L["筛选范围内没有可用装备"]
    if DEFAULT_CHAT_FRAME and DEFAULT_CHAT_FRAME.AddMessage then
        pcall(DEFAULT_CHAT_FRAME.AddMessage, DEFAULT_CHAT_FRAME, "|cffff7a66" .. msg .. "|r")
    end
    local host = BG.panels and BG.panels[2]
    if not host then return end
    BG.PaintAutoProg(0)
    local h = BG.autoProg
    if not h then return end
    h.pct = nil
    h.fs:SetTextColor(0.95, 0.45, 0.40)
    h.fs:SetText(L["没有可用装备"])
    if h.track then h.track:SetAlpha(0) end
    BG.emptySeq = (BG.emptySeq or 0) + 1
    local seq = BG.emptySeq
    C_Timer.After(4, function()
        if BG.emptySeq ~= seq then return end
        if h.track then h.track:SetAlpha(1) end
        h.fs:SetTextColor(Unpack(C_GOLD))
        BG.PaintAutoProg(nil)
    end)
end

local function AutoJobCancel()
    if not autoJob then return end
    autoJobSeq = autoJobSeq + 1
    autoJob = nil
    BG.PaintAutoProg(nil)
end
BG.AutoJobCancel = AutoJobCancel

local autoKind = {}

local function AutoKind(id)
    local v = autoKind[id]
    if v == nil then
        v = CatKind(id)
        autoKind[id] = v
    end
    return v
end

local function AutoRawOK(id, cap)
    GearSrcReady()
    local qlv = ns.GearSrcQLv and ns.GearSrcQLv[id]
    if type(qlv) == "number" and qlv > 0 and qlv > cap then return false end
    local qid = ns.GearSrcQ and ns.GearSrcQ[id]
    local fac = qid and ns.GearQuestRace and ns.GearQuestRace[qid]
    if fac and fac ~= PlayerFac() then return false end
    return true
end

local function AutoBuckets(job)
    local cat = job.cat
    if not cat or job.total < 1 then return true end
    local i = job.ci
    while i < job.total do
        i = i + 1
        local r = cat[i]
        if r.s and ClassWear(job.cls, r.c, r.u) and ClsOK(r.id) and (r.req or 0) <= job.cap
            and AutoRawOK(r.id, job.cap)
            and not (job.srcSet and not job.srcSet[AutoKind(r.id)]) then
            local b = job.buckets[r.s]
            if not b then
                b = {}
                job.buckets[r.s] = b
            end
            b[#b + 1] = r
        end
        if debugprofilestop() - job.t0 > AUTO_BUDGET_MS then break end
    end
    job.ci = i
    return i >= job.total
end

local function AutoPick(job)
    local keys = job.keys
    while job.ki <= #keys do
        if not job.curKey then
            job.curKey = keys[job.ki]
            job.dk = DataKey(job.sp, job.curKey)
            if job.curKey == "off-hand" and job.mk == "two-hand" then
                job.cur[job.dk] = nil
                job.ki = job.ki + 1
                job.curKey = nil
            else
                local rkey = RowsKey(job.curKey)
                if rkey == "main-hand" then rkey = job.mk end
                job.groups = SLOT_GEAR[rkey] or {}
                job.gi, job.bi = 1, 1
                job.best, job.bestScore = nil, nil
            end
        else
            local g = job.groups[job.gi]
            if not g then
                if job.best then
                    job.cur[job.dk] = job.best
                    if AutoKind(job.best) == "quest" or (ns.GearUni and ns.GearUni[job.best]) then
                        job.usedQ[job.best] = true
                    end
                end
                job.ki = job.ki + 1
                job.curKey = nil
            else
                local b = job.buckets[g]
                local r = b and b[job.bi]
                if not r then
                    job.gi = job.gi + 1
                    job.bi = 1
                else
                    job.bi = job.bi + 1
                    if UsableAt(r.id, job.cap, r.req or 0) and not job.usedQ[r.id] then
                        local sc = ItemScore(r.id, job.w)
                        if sc and (job.bestScore == nil or sc > job.bestScore) then
                            job.best, job.bestScore = r.id, sc
                        end
                    end
                end
            end
        end
        if debugprofilestop() - job.t0 > AUTO_BUDGET_MS then return false end
    end
    return true
end

local function AutoPump(jobId)
    local job = autoJob
    if not job or job.id ~= jobId then return end
    if job.phase == 1 and job.cat == nil then
        job.cat = EnsureCatalog()
        job.total = job.cat and #job.cat or 0
        if job.total < 1 then
            job.retry = (job.retry or 0) + 1
            if job.retry > 25 then
                autoJob = nil
                BG.PaintAutoProg(nil)
                return
            end
            job.cat = nil
            BG.PaintAutoProg(0)
            C_Timer.After(0.2, function() AutoPump(jobId) end)
            return
        end
    end
    job.t0 = debugprofilestop()
    local done = false
    if job.phase == 1 then
        if AutoBuckets(job) then
            job.phase = 2
        else
            done = false
        end
    end
    if job.phase == 2 then done = AutoPick(job) end
    if autoJob ~= job then return end
    local frac
    if job.phase == 1 then
        frac = 0.4 * ((job.ci or 0) / math.max(1, job.total or 1))
    else
        local sub = 0
        if job.curKey and job.groups and #job.groups > 0 then
            sub = ((job.gi or 1) - 1) / #job.groups
            if sub > 1 then sub = 1 end
        end
        frac = 0.4 + 0.6 * ((job.ki - 1 + sub) / math.max(1, #job.keys))
    end
    if done then
        autoJob = nil
        if job.mode == "manual" then
            local p = ManualPut(job.cur, job.cls, job.tspec, job.cap, job.srcSet)
            if BG.cls == job.cls and BG.tspec == job.tspec then
                BG.usingPlan = p
                BG.cur = {}
                BG.autoStale = nil
                BG.RequestRender()
            end
            BG.PaintAutoProg(nil)
            local cnt = 0
            for _ in pairs(p.items or {}) do cnt = cnt + 1 end
            if cnt < 1 then
                BG.WarnEmpty()
            end
            return
        end
        AutoStore(job.mode, job.cap, job.sig, job.cur, job.cls)
        if BG.cls == job.cls and BG.autoPlan == job.mode and BG.usingPlan == nil then
            BG.cur = CopyCur(job.cur)
            BG.autoStale = nil
            BG.RequestRender()
        end
        BG.PaintAutoProg(nil)
        return
    end
    BG.PaintAutoProg(frac)
    C_Timer.After(0, function() AutoPump(jobId) end)
end

local function AutoJobStart(mode, cap, sig, srcSet)
    autoJobSeq = autoJobSeq + 1
    local sp = SpecRec()
    if not sp then return end
    autoJob = {
        id = autoJobSeq, mode = mode, cap = cap, sig = sig,
        cls = BG.cls, tspec = BG.tspec, sp = sp, mk = MainKey(sp), w = EffWeights(),
        srcSet = srcSet or ((mode == "known") and AUTO_SRC_KNOWN)
            or ((mode == "dq") and AUTO_SRC_DQ) or nil,
        cat = nil, total = 0, ci = 0,
        phase = 1, buckets = {}, cur = {}, usedQ = {},
        keys = ALL_SLOT_KEYS, ki = 1,
    }
    BG.emptySeq = (BG.emptySeq or 0) + 1
    BG.PaintAutoProg(0)
    local id = autoJobSeq
    C_Timer.After(0, function() AutoPump(id) end)
end

function BG.AutoJobState()
    if not autoJob then return nil end
    return autoJob.mode, autoJob.phase, autoJob.ki, autoJob.ci, autoJob.total
end

function BG.UseAutoPlan(mode)
    if not mode then return end
    BG.autoPlan = mode
    BG.usingPlan = nil
    AutoJobCancel()
    if not autoSnapsLoaded then LoadAutoSnaps() end
    local cap = BG.AutoLevel()
    local sig = AutoSig(mode, cap)
    local snap = autoSnaps[sig]
    if snap then
        snap.t = NowSec()
        BG.autoStale = nil
        BG.cur = CopyCur(snap.items)
        BG.RequestRender()
        return
    end
    local old = AutoStale(mode)
    BG.cur = old and CopyCur(old.items) or {}
    BG.autoStale = old and old.lv or nil
    BG.RequestRender()
    AutoJobStart(mode, cap, sig)
end

function BG.UseManualPlan()
    local p = ManualGet()
    if not p then return end
    if BG.usingPlan ~= p then
        BG.cur = {}
        BG.ench = {}
    end
    BG.usingPlan = p
    BG.autoPlan = nil
    if not (autoJob and autoJob.mode == "manual") then AutoJobCancel() end
    BG.RequestRender()
end

function BG.StartManualGen()
    if not SpecRec() then return end
    local ss = {}
    for k, v in pairs(BG.srcSet) do ss[k] = v end
    local old = ManualGet()
    AutoJobCancel()
    BG.autoPlan = nil
    BG.usingPlan = old
    BG.cur = {}
    BG.ench = {}
    BG.RequestRender()
    local cap = BG.AutoLevel()
    AutoJobStart("manual", cap, AutoSig("manual", cap), ss)
end
end

local function PresetList()
    local out = {}
    local tsp = BG.tspec
    local src = BG.AUTO_SRC or {}
    out[#out + 1] = { auto = "known", lv = BG.AutoLevel(), srcSet = src.known }
    out[#out + 1] = { auto = "dq", lv = BG.AutoLevel(), srcSet = src.dq }
    local mp = BG.ManualPlan()
    if mp then
        out[#out + 1] = { manual = true, type = L["手动过滤生成的BIS结果"],
                          srcSet = mp.srcSet or BG.srcSet }
    end
    for i = #VOLS, 1, -1 do
        local v = VOLS[i]
        local c
        for _, cc in ipairs(v.classes or {}) do
            if cc.slug == BG.cls then c = cc break end
        end
        if c then
            local cnt = {}
            for _, sp in ipairs(c.specs) do
                cnt[sp.id] = (cnt[sp.id] or 0) + 1
            end
            local pages = {}
            for _, sp in ipairs(c.specs) do
                if (cnt[sp.id] or 0) <= 1 or sp.tspec == nil or sp.tspec == tsp then
                    pages[#pages + 1] = sp
                end
            end
            if #pages == 0 then
                for _, sp in ipairs(c.specs) do pages[#pages + 1] = sp end
            end
            for _, sp in ipairs(pages) do
                local solo = (cnt[sp.id] or 0) <= 1
                local lab, ts = sp.label, sp.tspec
                if solo then lab, ts = nil, nil end
                if lab == SPEC_LABEL[sp.id] then lab = nil end
                for _, sd in ipairs({ "a", "h" }) do
                    out[#out + 1] = { vol = i, spec = sp.id, tspec = ts,
                                      key = sp.key, type = SPEC_LABEL[sp.id] or sp.id,
                                      talent = lab, side = sd }
                end
            end
        end
    end
    return out
end

local function PresetText(pe)
    if pe.manual then return pe.type end
    if pe.auto then return format(L["%d级 自动方案"], pe.lv) end
    local lv = format(L["%d级 · "], VOLS[pe.vol].lv)
    local side = (pe.side == "a") and L["联盟"] or L["部落"]
    return lv .. pe.type .. " · " .. side, pe.talent and (lv .. pe.type .. " · " .. pe.talent .. " · " .. side) or nil
end

BG.CHIP_INK_SRC = {
    craft = { 0.95, 0.70, 0.38 }, quest = { 0.50, 0.80, 0.98 },
    boss = { 0.94, 0.52, 0.50 }, rare = { 0.76, 0.60, 0.96 },
    vendor = { 0.50, 0.84, 0.62 }, other = { 0.70, 0.72, 0.76 },
}

function BG.PaintSrcChips(r, set)
    local cs = r.__srcChips
    if not cs then
        cs = {}
        r.__srcChips = cs
    end
    if not set then
        for i = 1, 7 do
            local c = cs[i]
            if c and c:IsShown() then c:Hide() end
        end
        return
    end
    if not (ns.hui and ns.hui.MakeSolidChip and ns.hui.PaintSolidChip) then return end
    local inks = BG.CHIP_INK_SRC
    local used, ws = 0, {}
    for _, f in ipairs(FILTERS) do
        if set[f.id] then
            used = used + 1
            local c = cs[used]
            if not c then
                c = ns.hui.MakeSolidChip(r, (r:GetFrameLevel() or 0) + 2, ns.hui.ChipH(13))
                cs[used] = c
            end
            ns.hui.PaintSolidChip(c, f.label, inks[f.id] or inks.other)
            ws[used] = c:GetWidth() or 24
        end
    end
    local tail = cs[7]
    local cut = used
    local function span(k)
        local t = 0
        for i = 1, k do t = t + (ws[i] or 0) + ((i > 1) and 4 or 0) end
        return t
    end
    if used > 0 and span(used) > 170 then
        cut = used - 1
        while cut > 0 do
            if not tail then
                tail = ns.hui.MakeSolidChip(r, (r:GetFrameLevel() or 0) + 2, ns.hui.ChipH(13))
                cs[7] = tail
            end
            ns.hui.PaintSolidChip(tail, format("+%d", used - cut), inks.other)
            if span(cut) + 4 + (tail:GetWidth() or 24) <= 170 then break end
            cut = cut - 1
        end
    end
    local x = 0
    for i = 1, 7 do
        local c = cs[i]
        if c and i ~= 7 then
            if i <= cut then
                c:ClearAllPoints()
                c:SetPoint("BOTTOMLEFT", r, "BOTTOMLEFT", 8 + x, 5)
                c:Show()
                x = x + (ws[i] or 24) + 4
            elseif c:IsShown() then
                c:Hide()
            end
        end
    end
    if used == 0 then
        if not tail then
            tail = ns.hui.MakeSolidChip(r, (r:GetFrameLevel() or 0) + 2, ns.hui.ChipH(13))
            cs[7] = tail
        end
        ns.hui.PaintSolidChip(tail, L["未选来源"], inks.other)
        tail:ClearAllPoints()
        tail:SetPoint("BOTTOMLEFT", r, "BOTTOMLEFT", 8, 5)
        tail:Show()
    elseif cut < used then
        tail:ClearAllPoints()
        tail:SetPoint("BOTTOMLEFT", r, "BOTTOMLEFT", 8 + x, 5)
        tail:Show()
    elseif tail and tail:IsShown() then
        tail:Hide()
    end
end

local function PlanChip(r)
    if r.chip then return r.chip end
    local c
    if ns.hui and ns.hui.MakeSolidChip and ns.hui.ChipH then
        c = ns.hui.MakeSolidChip(r, (r:GetFrameLevel() or 0) + 2, ns.hui.ChipH(14))
        ns.hui.PaintSolidChip(c, L["预设"], BG.CHIP_INK_PRESET)
    else
        c = CreateFrame("Frame", nil, r)
        c:SetSize(29, 14)
        c.t = MakeFS(c, 14, C_WHITE, "CENTER")
        c.t:SetAllPoints(c)
        c.t:SetWordWrap(false)
        c.t:SetText(L["预设"])
    end
    c:SetPoint("TOPRIGHT", r, "TOPRIGHT", -8, -7)
    r.chip = c
    r.dot:ClearAllPoints()
    r.dot:SetPoint("TOP", c, "BOTTOM", 0, -2)
    return c
end

function BG.FitPlanRows()
    local sc = BG.planScroll
    if not sc then return end
    local vh = sc:GetHeight()
    if type(vh) ~= "number" or vh <= 0 then return end
    local off = 0
    if sc.GetVerticalScroll then
        local ok, v = pcall(sc.GetVerticalScroll, sc)
        if ok and type(v) == "number" then off = v end
    end
    for _, r in ipairs(BG.planRows) do
        local full = r.__fillH
        if full and r.__on then
            local top = (r.__top or 0) - off
            if top >= vh - 0.5 or top + full <= 0.5 then
                if r:IsShown() then r:Hide() end
            else
                if not r:IsShown() then r:Show() end
                local h = full
                if top + h > vh then h = vh - top end
                if h < 12 then h = 12 end
                if math.abs((r:GetHeight() or 0) - h) > 0.5 then r:SetHeight(h) end
            end
        end
    end
end

local function PaintPlans()
    local plans = PlansFor(BG.cls)
    local rows = BG.planRows
    local y = 0
    local presets = PresetList()
    local cur = SpecRec()
    local curKey = cur and cur.key or nil
    for i = 1, N_PRESET do
        local r = rows[i]
        local pe = presets[i]
        if pe then
            r:Show()
            local sideNow = BG.side or PlayerFac()
            local active
            if pe.auto then
                active = (BG.usingPlan == nil and BG.autoPlan == pe.auto)
            elseif pe.manual then
                active = (BG.usingPlan ~= nil and BG.usingPlan.manual == true)
            else
                active = (BG.usingPlan == nil and BG.autoPlan == nil and BG.vol == pe.vol
                    and curKey == pe.key and sideNow == pe.side)
            end
            local chip = (pe.auto or pe.manual) and true or false
            local rh = chip and BG.PLAN_TALL or PLAN_H
            if r.__chipOn ~= chip or r.__h ~= rh then
                r.__chipOn = chip
                r.__h = rh
                r:SetHeight(rh)
                r.title:ClearAllPoints()
                if chip then
                    local c = PlanChip(r)
                    c:Show()
                    r.title:SetPoint("TOPLEFT", r, "TOPLEFT", 8, -4)
                    r.title:SetPoint("BOTTOMRIGHT", r, "BOTTOMRIGHT", -(c:GetWidth() or 29) - 13, 22)
                else
                    if r.chip then r.chip:Hide() end
                    r.title:SetPoint("TOPLEFT", r, "TOPLEFT", 8, -2)
                    r.title:SetPoint("BOTTOMLEFT", r, "BOTTOMLEFT", 8, 2)
                    r.title:SetPoint("RIGHT", r, "RIGHT", -30, 0)
                end
                r.title:SetWordWrap(false)
                r.title:SetJustifyH("LEFT")
                r.title:SetJustifyV("MIDDLE")
            end
            local short, full = PresetText(pe)
            r.title:SetText(full or short)
            if full and (r.title:GetStringWidth() or 0) > 168 then
                r.title:SetText(short)
            end
            BG.PaintSrcChips(r, chip and pe.srcSet or nil)
            r.dot:SetShown(active)
            r.__plan = nil
            r.__vol = pe.vol
            r.__spec = pe.spec
            r.__tspec = pe.tspec
            r.__key = pe.key
            r.__side = pe.side
            r.__auto = pe.auto
            r.__manual = pe.manual
            r.__sel = active
            if r.__huiCard then
                ns.hui.HuiCardState(r, (active or r:IsMouseOver()) and "hover" or "norm")
            end
            r.title:SetTextColor(Unpack(active and C_GOLD or C_TEXT))
            r.__on = true
            r.__top = y
            r.__fillH = rh
            r:SetPoint("TOPLEFT", BG.planChild, "TOPLEFT", 0, -y)
            r:SetPoint("RIGHT", BG.planChild, "RIGHT", 0, 0)
            y = y + rh + 2
        else
            r:Hide()
            r.__on = nil
            r.__key = nil
            r.__auto = nil
            r.__manual = nil
        end
    end
    local shown = 0
    for i = 1, N_USER do
        local r0 = rows[N_PRESET + i]
        r0:Hide()
        r0.__plan = nil
    end
    for _, p in ipairs(plans) do
        if shown >= N_USER then break end
        if p.tspec == nil or p.tspec == BG.tspec then
            local r = rows[N_PRESET + shown + 1]
            shown = shown + 1
            r:Show()
            r.title:SetText(p.name)
            BG.PaintSrcChips(r, nil)
            local active = p == BG.usingPlan
            r.dot:SetShown(false)
            r.__sel = active
            if r.__huiCard then
                ns.hui.HuiCardState(r, (active or r:IsMouseOver()) and "hover" or "norm")
            end
            r.title:SetTextColor(Unpack(active and C_GOLD or C_TEXT))
            r.__plan = p
            r.__vol = nil
            r.__key = nil
            r.__on = true
            r.__top = y
            r.__fillH = PLAN_H
            r:SetPoint("TOPLEFT", BG.planChild, "TOPLEFT", 0, -y)
            r:SetPoint("RIGHT", BG.planChild, "RIGHT", 0, 0)
            y = y + PLAN_H + 2
        end
    end
    local has = BG.usingPlan ~= nil and BG.usingPlan.manual ~= true
    BG.renameBtn:SetEnabled(has)
    BG.deleteBtn:SetEnabled(has)
    BG.renameBtn.lbl:SetTextColor(Unpack(has and C_TEXT or C_DIM))
    BG.deleteBtn.lbl:SetTextColor(Unpack(has and C_TEXT or C_DIM))
    BG.planChild:SetHeight(y + 6)
    if BG.planScroll and BG.planScroll.GetVerticalScroll then
        local mx = math.max(0, y + 6 - (BG.planScroll:GetHeight() or 0))
        local ok, v = pcall(BG.planScroll.GetVerticalScroll, BG.planScroll)
        if ok and type(v) == "number" and v > mx then BG.planScroll:SetVerticalScroll(mx) end
    end
    BG.FitPlanRows()
    if BG.planBar then BG.planBar.Update() end
end

local FillBwRow

BG.ROW_PITCH = ROW_H + 2
BG.POOL_MAX = 120
BG.POOL_MIN = 10

function BG.BwVirtualOn()
    local db = DB()
    return not (type(db) == "table" and db.bisPool120)
end

function BG.BwPoolSize()
    if not BG.BwVirtualOn() then return BG.POOL_MAX end
    local sc = BG.bwScroll
    local h = sc and sc.GetHeight and sc:GetHeight()
    if type(h) ~= "number" or h <= 0 then h = 720 end
    local n = math.ceil(h / BG.ROW_PITCH) + 3
    if n < BG.POOL_MIN then n = BG.POOL_MIN end
    if n > BG.POOL_MAX then n = BG.POOL_MAX end
    return n
end

function BG.BindBwWindow(first)
    local rows = BG.bwRows
    local child = BG.bwChild
    if not (rows and child) then return end
    local list = BG.bwList or {}
    local n = #rows
    if first < 1 then first = 1 end
    if #list > 0 then
        local maxFirst = #list - n + 1
        if maxFirst < 1 then maxFirst = 1 end
        if first > maxFirst then first = maxFirst end
    end
    local pitch = BG.ROW_PITCH
    for k = 1, n do
        local r = rows[k]
        local idx = first + k - 1
        local row = list[idx]
        if row then
            if r.__idx ~= idx then r.__painted = false end
            r.__active = true
            r.__row = row
            r.__idx = idx
            r.__vtop = (idx - 1) * pitch
            r.__vh = ROW_H
            r:ClearAllPoints()
            r:SetPoint("TOPLEFT", child, "TOPLEFT", 0, -r.__vtop)
            r:SetPoint("RIGHT", child, "RIGHT", 0, 0)
        else
            r.__active = false
            r.__row = nil
            r.__idx = nil
            r.__painted = false
            r:Hide()
        end
    end
    if #list == 0 and BG.sel and rows[1] then
        local r = rows[1]
        r.__active = true
        r.__row = nil
        r.__idx = 0
        r.__vtop = 0
        r.__vh = ROW_H
        r.__painted = false
        r:ClearAllPoints()
        r:SetPoint("TOPLEFT", child, "TOPLEFT", 0, 0)
        r:SetPoint("RIGHT", child, "RIGHT", 0, 0)
    end
    BG.bwFirst = first
end

local function CullBwRows()
    local sc = BG.bwScroll
    if not (sc and sc.GetTop) then return end
    local gt = sc:GetTop()
    local viewH = sc.GetHeight and sc:GetHeight()
    if type(gt) ~= "number" or type(viewH) ~= "number" or viewH <= 0 then
        if BG.BwVirtualOn() then BG.BindBwWindow(1) end
        for _, r in ipairs(BG.bwRows or {}) do
            if r.__active then
                if not r.__painted then FillBwRow(r) end
                r:Show()
            else
                r:Hide()
            end
        end
        if BG.needNames or BG.needScores then BG.ScheduleSweep() end
        return
    end
    local v = sc.GetVerticalScroll and sc:GetVerticalScroll() or 0
    if type(v) ~= "number" then v = 0 end
    if BG.BwVirtualOn() then
        local first = math.floor(v / BG.ROW_PITCH) + 1
        if first < 1 then first = 1 end
        local cnt = #(BG.bwList or {})
        if cnt > 0 then
            local maxFirst = cnt - #(BG.bwRows or {}) + 1
            if maxFirst < 1 then maxFirst = 1 end
            if first > maxFirst then first = maxFirst end
        end
        if first ~= BG.bwFirst then BG.BindBwWindow(first) end
    end
    local vTop, vBot = v - viewH - 2, v + viewH * 2 + 2
    for _, r in ipairs(BG.bwRows or {}) do
        if not r.__active then
            r:Hide()
        else
            local cy = r.__vtop
            if type(cy) == "number" then
                local ch = r.__vh or ROW_H
                if (cy + ch) > vTop and cy < vBot then
                    if not r.__painted then FillBwRow(r) end
                    r:Show()
                else
                    r:Hide()
                end
            end
        end
    end
    if BG.needNames or BG.needScores then BG.ScheduleSweep() end
end

local function CullEnchRows()
    local sc = BG.enchScroll
    if not (sc and sc.GetTop) then return end
    local gt = sc:GetTop()
    local viewH = sc.GetHeight and sc:GetHeight()
    if type(gt) ~= "number" or type(viewH) ~= "number" or viewH <= 0 then
        for _, r in ipairs(BG.enchRows or {}) do
            if r.__enchOn then r:Show() else r:Hide() end
        end
        return
    end
    local v = sc.GetVerticalScroll and sc:GetVerticalScroll() or 0
    if type(v) ~= "number" then v = 0 end
    for _, r in ipairs(BG.enchRows or {}) do
        if not r.__enchOn then
            r:Hide()
        else
            local cy = r.__vtop
            local ch = r.__vh or 36
            local top = (type(cy) == "number") and cy or nil
            local bot = (type(cy) == "number" and type(ch) == "number") and (cy + ch) or nil
            if top and bot and bot > v - 2 and top < v + viewH + 2 then
                r:Show()
            else
                r:Hide()
            end
        end
    end
end

local function ScanOwned()
    local t = {}
    for slot = 1, 19 do
        local id = GetInventoryItemID and GetInventoryItemID("player", slot)
        if id and id > 0 then t[id] = true end
    end
    for bag = 0, 11 do
        for s = 1, 32 do
            local iid
            if C_Container and C_Container.GetContainerItemInfo then
                local ok, ci = pcall(C_Container.GetContainerItemInfo, bag, s)
                if ok and type(ci) == "table" then iid = ci.itemID end
            elseif GetContainerItemInfo then
                local ok, id = pcall(GetContainerItemInfo, bag, s)
                if ok and type(id) == "number" then iid = id end
            end
            if iid and iid > 0 then t[iid] = true end
        end
    end
    return t
end

local CHIP_WISH_BG = { 0.78, 0.60, 0.10, 1 }
local CHIP_UP_BG = { 0.16, 0.52, 0.26, 1 }
local CHIP_DOWN_BG = { 0.36, 0.39, 0.44, 1 }
local CHIP_BOE_BG = { 0.18, 0.45, 0.66, 1 }

local __boeCache = {}
local function BindOnEquip(id)
    if __boeCache[id] ~= nil then return __boeCache[id] end
    local fn = GetItemInfo or (C_Item and C_Item.GetItemInfo)
    if type(fn) ~= "function" then return nil end
    if C_Item and type(C_Item.RequestLoadItemDataByID) == "function" then
        pcall(C_Item.RequestLoadItemDataByID, id)
    end
    local ok, name = pcall(fn, id)
    if not ok or name == nil then return nil end
    local bind = select(15, pcall(fn, id))
    if bind == nil then return nil end
    __boeCache[id] = (bind == 2)
    local v = __boeCache[id]
    BG.__boeCacheN = (BG.__boeCacheN or 0) + 1
    if BG.__boeCacheN > 4000 then
        for k in pairs(__boeCache) do __boeCache[k] = nil end
        BG.__boeCacheN = 0
    end
    return v
end

local function ChipSet(b, text, col, rightOf)
    b.lab:SetText(text)
    DG.BadgeTint(b, col)
    b:ClearAllPoints()
    if rightOf then
        b:SetPoint("RIGHT", rightOf, "LEFT", -4, 0)
    else
        b:SetPoint("TOPRIGHT", b:GetParent(), "TOPRIGHT", -6, -4)
    end
    b:SetWidth((b.lab:GetStringWidth() or 20) + DG.Q_BADGE_PAD * 2)
    b:Show()
end

function FillBwRow(r)
    GearSrcReady()
    local row = r.__row
    if r.__huiCard then ns.hui.HuiCardState(r, "norm") end
    if not row then
        r.icon:SetTexture("")
        r.name:SetText(L["这个筛选下没有条目"])
        r.name:SetTextColor(Unpack(C_DIM))
        r.src:SetText("")
        r.eqTag:SetShown(false)
        r.ownTag:SetShown(false)
        r.sideTag:SetShown(false)
        r.chip:Hide()
        r.chip2:Hide()
        r.chip3:Hide()
        r.wishBt:Hide()
        r.pinBt:Hide()
        r.__pinNpc, r.__pinLoc, r.__pinQid = nil, nil, nil
        r.__painted = true
        return
    end
    local sp = SpecRec()
    r.icon:SetTexture(ItemIcon(row.item))
    local nm, okn = DG.ItemName(row.item)
    if not okn then
        BG.needNames = true
        DG.RequestItem(row.item)
    end
    r.name:SetText(nm)
    r.name:SetTextColor(Unpack(QColor(ItemQuality(sp, row.item, row.q))))
    local st = row.cat and CatSrcText(row.item) or SrcText(row.src)
    r.__pinNpc, r.__pinLoc, r.__pinQid = nil, nil, nil
    local qid = nil
    if row.src and row.src.t == "quest" and row.src.q then
        qid = tonumber(row.src.q)
    elseif row.cat and CatKind(row.item) == "quest" then
        qid = ns.GearSrcQ and ns.GearSrcQ[row.item] or nil
    end
    if qid then
        local qn, qok = DG.QuestName(qid)
        if not qok then BG.needNames = true end
        if row.cat and qok then st = L["任务奖励"] .. " · " .. qn end
        local sn = DG.QuestStartNpc and DG.QuestStartNpc(qid) or nil
        local npc = sn and sn[1] or nil
        local sl = ns.DungeonQuestStartLoc and ns.DungeonQuestStartLoc[qid] or nil
        local loc = nil
        if sl and (not npc or tonumber(sl[1]) == tonumber(npc)) then
            npc = sl[1]
            if sl[3] and sl[4] and sl[5] then loc = { sl[3], sl[4], sl[5] } end
        end
        if not loc then
            local gs = ns.GearQuestStart and ns.GearQuestStart[qid] or nil
            if gs then
                npc = gs[1]
                loc = { gs[2], gs[3], gs[4] }
            elseif sn and sn[3] and sn[4] and sn[5] then
                loc = { sn[3], sn[4], sn[5] }
            end
        end
        if npc and (loc or (ns.NPCLoc and ns.NPCLoc[npc])) then
            r.__pinNpc, r.__pinLoc = npc, loc
        end
        r.__pinQid = qid
    end
    local showPin = r.__pinNpc ~= nil
    if not showPin and r.__pinQid then
        if ns.GearChainIndexOf and ns.GearChainIndexOf(r.__pinQid) then
            showPin = true
        else
            local qloc = ns.GearQuestLocOf and ns.GearQuestLocOf(r.__pinQid) or nil
            showPin = type(qloc) == "table" and qloc[1] ~= nil
        end
    end
    r.pinBt:SetShown(showPin)
    r.src:SetText(st)
    r.src:SetTextColor(Unpack(C_GREY))
    r.eqTag:SetShown(BG.bwEquipped == row.item)
    r.ownTag:SetShown(BG.owned ~= nil and BG.owned[row.item] ~= nil)
    r.sideTag:SetShown(row.side ~= nil)
    if row.side then r.sideTag:SetText(row.side == "a" and L["联盟"] or L["部落"]) end
    local scoreChip = nil
    local rsc = row.score
    if BG.baseId == row.item then
        ChipSet(r.chip2, L["当前"], CHIP_UP_BG, nil)
        scoreChip = r.chip2
    elseif rsc and BG.baseScore and BG.baseScore > 0 then
        local pct = (rsc / BG.baseScore - 1) * 100
        local col = pct > 0.5 and CHIP_UP_BG or CHIP_DOWN_BG
        ChipSet(r.chip2, format("%+d%%", pct), col, nil)
        scoreChip = r.chip2
    else
        r.chip2:Hide()
    end
    local gm = ns.GearModule
    if gm and gm.WishIs and gm.WishIs(row.item) then
        ChipSet(r.chip, L["心愿"], CHIP_WISH_BG, scoreChip)
    else
        r.chip:Hide()
    end
    local boe = BindOnEquip(row.item)
    if boe == nil then
        BG.needNames = true
        DG.RequestItem(row.item)
        r.chip3:Hide()
    elseif boe then
        local left = r.chip:IsShown() and r.chip or (scoreChip or nil)
        ChipSet(r.chip3, L["装绑"], CHIP_BOE_BG, left)
    else
        r.chip3:Hide()
    end
    if gm and gm.WishIs then
        local on = gm.WishIs(row.item)
        r.wishBt.star:SetText(on and "★" or "☆")
        if on then
            r.wishBt.star:SetTextColor(1, 0.82, 0, 1)
        else
            r.wishBt.star:SetTextColor(Unpack(C_GREY))
        end
        r.wishBt:Show()
    else
        r.wishBt:Hide()
    end
    r.__painted = true
end

local function PaintBrowser()
    local sp = SpecRec()
    if not sp then return end
    local rkey = BG.sel and RowsKey(BG.sel) or nil
    if rkey == "main-hand" then rkey = MainKey(sp) end
    if BG.sel then
        BG.bwTitle:SetText(SLOT_NAMES[BG.sel] or BG.sel)
    else
        BG.bwTitle:SetText(L["点左侧部位查看备选"])
    end
    local list = {}
    if BG.sel and rkey then
        local w = EffWeights()
        local lv = BG.onlyUsable and (BG.filterLv or PlayerLevel() or 60) or nil
        local baseId = CurItem(sp, BG.sel)
        BG.baseScore = baseId and ItemScore(baseId, w) or nil
        BG.baseId = baseId
        local pool = {}
        for _, r in ipairs(CatRowsFor(rkey)) do
            local kind = CatKind(r.id)
            local pass = not (next(BG.srcSet) ~= nil and not BG.srcSet[kind])
            if pass and lv and not UsableAt(r.id, lv, r.req or 0) then pass = false end
            if pass and BG.search ~= "" then
                local nm = string.lower(DG.ItemName(r.id) or "")
                if not string.find(nm, BG.search, 1, true) then pass = false end
            end
            if pass then pool[#pool + 1] = r end
        end
        local wishOf = ns.GearModule and ns.GearModule.WishIs
        table.sort(pool, function(a, b)
            if wishOf then
                local wa, wb = wishOf(a.id), wishOf(b.id)
                if wa ~= wb then return wa end
            end
            local sa, sb = ItemScore(a.id, w), ItemScore(b.id, w)
            if sa and sb then return sa > sb end
            if sa or sb then return sa ~= nil end
            return (a.req or 0) < (b.req or 0)
        end)
        local isWep = rkey == "main-hand" or rkey == "two-hand"
            or rkey == "off-hand" or rkey == "ranged"
        BG.baseWep = isWep
        local cap = 120
        for i = 1, #pool do
            if i > cap then break end
            local r = pool[i]
            list[#list + 1] = { item = r.id, q = r.q, cat = true, isWep = isWep,
                                score = ItemScore(r.id, w) }
        end
        if not (BG.baseScore and BG.baseScore > 0) then
            local mx
            for _, row in ipairs(list) do
                if row.score and row.score > 0 and (mx == nil or row.score > mx) then mx = row.score end
            end
            BG.baseScore = mx
        end
        for _, row in ipairs(list) do
            if row.cat and statCache[row.item] == nil then
                BG.needScores = true
                break
            end
        end
    end
    BG.pool = list
    BG.owned = ScanOwned()
    local rows = BG.bwRows
    BG.bwEquipped = BG.sel and BG.cur[DataKey(sp, BG.sel)] or nil
    local y = #list * BG.ROW_PITCH
    for i = 1, #rows do
        local rr = rows[i]
        rr:Hide()
        rr.__active = false
        rr.__painted = false
        rr.__idx = nil
    end
    if BG.sel and #list == 0 then y = ROW_H end
    BG.bwList = list
    BG.bwFirst = nil
    BG.BindBwWindow(1)
    BG.bwChild:SetHeight(y + LIST_PAD)
    if BG.bwBar then BG.bwBar.Update() end
    CullBwRows()
    if BG.needNames or BG.needScores then BG.ScheduleSweep() end
end

local function PaintEnchs()
    local sp = SpecRec()
    local rows = BG.enchRows
    for i = 1, #rows do
        rows[i]:Hide()
        rows[i].__enchOn = false
    end
    local dk = BG.sel and DataKey(sp, BG.sel) or nil
    local list = EnchRowsFor(sp, dk)
    if BG.enchSearch and BG.enchSearch ~= "" then
        local f = {}
        for _, e in ipairs(list) do
            local hay = string.lower(tostring(EnchName(e)) .. " " .. tostring(e.eff or ""))
            if string.find(hay, BG.enchSearch, 1, true) then f[#f + 1] = e end
        end
        list = f
    end
    if BG.enchFilter then
        local f = {}
        for _, e in ipairs(list) do
            if EnchMatchFilter(e) then f[#f + 1] = e end
        end
        list = f
    end
    local y = 0
    local cap = EnchCap(nil)
    for i, e in ipairs(list) do
        if i > #rows then break end
        local r = rows[i]
        r:Show()
        r.__ench = e
        r.__enchOn = true
        r.__vtop = y
        r.__vh = 36
        if e.item then
            local _, okn = DG.ItemName(e.item)
            if not okn then
                BG.needNames = true
                DG.RequestItem(e.item)
            end
        end
        local over = cap and e.req and e.req > cap
        r.name:SetText(EnchName(e))
        if e.item then
            r.lvl:SetText(e.req and format(L["%d 级可用"], e.req) or "")
        else
            r.lvl:SetText(e.lvl and format(L["附魔 %d"], e.lvl) or "")
        end
        r.note:SetText(e.eff or "")
        r.note:SetTextColor(Unpack(over and C_DIM or C_TEXT))
        local capLv = nil
        if BG.usingPlan then capLv = BG.usingPlan.vol end
        local sel = CurEnch(sp, dk, capLv) == EnchToken(e)
        r.__sel = sel
        if r.__huiCard then
            ns.hui.HuiCardState(r, (sel or r:IsMouseOver()) and "hover" or "norm")
        end
        r.name:SetTextColor(Unpack(over and not sel and C_DIM or (sel and C_GOLD or C_TEXT)))
        r:SetPoint("TOPLEFT", BG.enchChild, "TOPLEFT", 0, -y)
        r:SetPoint("RIGHT", BG.enchChild, "RIGHT", 0, 0)
        y = y + 38
    end
    if #list == 0 and rows[1] then
        local r = rows[1]
        r:Show()
        r.__ench = nil
        r.__enchOn = true
        r.__vtop = 0
        r.__vh = 36
        r.name:SetText(BG.sel and L["该部位没有附魔推荐"] or L["点左侧部位查看该部位的附魔"])
        r.name:SetTextColor(Unpack(C_DIM))
        r.lvl:SetText("")
        r.note:SetText("")
        if r.__huiCard then ns.hui.HuiCardState(r, "norm") end
        r:SetPoint("TOPLEFT", BG.enchChild, "TOPLEFT", 0, 0)
        r:SetPoint("RIGHT", BG.enchChild, "RIGHT", 0, 0)
        y = 38
    end
    BG.enchChild:SetHeight(y + 4)
    if BG.enchScroll and BG.enchScroll.SetVerticalScroll then
        local vCur = BG.enchScroll:GetVerticalScroll() or 0
        local viewH = BG.enchScroll.GetHeight and BG.enchScroll:GetHeight() or nil
        if type(vCur) == "number" and type(viewH) == "number" then
            local maxV = math.max(0, BG.enchChild:GetHeight() - viewH)
            if vCur > maxV then BG.enchScroll:SetVerticalScroll(maxV) end
        end
    end
    if BG.enchBar then BG.enchBar.Update() end
    CullEnchRows()
    if BG.needNames then BG.ScheduleSweep() end
end

local function PY()
    if coroutine.running and coroutine.running() then coroutine.yield() end
end

function BG.Render()
    if not BG.built then return end
    EnsureBIS()
    if not BG.vol then BG.vol = DefaultVol() end
    if not BG.sel then BG.sel = SLOTS_LEFT[1] end
    if not BG.tspec then
        local tk, nt
        for _, sr in ipairs(SPEC_DIR[BG.cls] or {}) do
            if sr.role == "tank" then tk = tk or sr.key else nt = nt or sr.key end
            if BG.wRole ~= nil and sr.key == BG.wRole then BG.tspec = sr.key end
        end
        if not BG.tspec then
            BG.tspec = (BG.spec == "tank" and tk) or nt
        end
    end
    PaintTopbar()
    PY()
    PaintDoll()
    PY()
    PaintStats()
    PY()
    PaintPlans()
    PY()
    PaintBrowser()
    PY()
    PaintEnchs()
end

function BG.RequestRender()
    if not BG.built then return end
    if not (ns.PaintJob and ns.IdleJobs) then
        BG.RequestRender()
        return
    end
    if ns.PaintJob.Active("Bis") then
        BG.__pend = true
        return
    end
    ns.PaintJob.Run("Bis", function() BG.Render() end, function()
        if BG.__pend then
            BG.__pend = false
            BG.RequestRender()
        end
    end)
end

function BG.Open()
    if not BG.built then return end
    BG._sweepFails = 0
    BG.__wantDefault = nil
    if not BG.usingPlan then BG.UseAutoPlan(BG.autoPlan or "known") end
    if BG.needNames or BG.needScores then BG.ScheduleSweep() end
    BG.RequestRender()
end

function BG.Refresh()
    if not BG.built then return end
    BG.RequestRender()
end

function BG.ToggleFilterPop()
    if not BG.filterPop then return end
    local show = not BG.filterPop:IsShown()
    BG.filterPop:SetShown(show)
    if BG.filterBtn then
        SetButtonSelected(BG.filterBtn, show)
    end
    if show and BG.SyncFilterPop then BG.SyncFilterPop() end
end

function BG.SyncFilterPop()
    if BG.usableTg then BG.usableTg:SetChecked(BG.onlyUsable) end
    if BG.filterLvBox then
        BG.filterLvBox:SetText(BG.filterLv and tostring(BG.filterLv) or "")
    end
    for id, bt in pairs(BG.srcRows or {}) do
        local on = BG.srcSet[id] and true or false
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

function BG.CloseSettingPop()
    if BG.settingPop and BG.settingPop:IsShown() then
        BG.settingPop:Hide()
        if BG.setBtn then
            SetButtonSelected(BG.setBtn, false)
            if BG.setBtn.__icon then
                local c = ns.SET_ICON_IDLE
                BG.setBtn.__icon:SetVertexColor(c[1], c[2], c[3])
            end
        end
        if ns.QuickBar and ns.QuickBar.Reanchor then pcall(ns.QuickBar.Reanchor, ns.QuickBar) end
    end
end

function BG.ToggleSettingPop()
    if not BG.settingPop then return end
    local show = not BG.settingPop:IsShown()
    if show then
        if not BG.__csHooked then
            BG.__csHooked = true
            local orig = ns.CloseSettings
            ns.CloseSettings = function()
                if orig then orig() end
                BG.CloseSettingPop()
            end
        end
        if ns.CloseSettings then pcall(ns.CloseSettings) end
        if ns.CloseExploreMapSettings then pcall(ns.CloseExploreMapSettings) end
        if ns.CloseQuestPinSettings then pcall(ns.CloseQuestPinSettings) end
        if ns.LootFilterUI and ns.LootFilterUI.CloseConfig then
            pcall(ns.LootFilterUI.CloseConfig, ns.LootFilterUI)
        end
    end
    BG.settingPop:SetShown(show)
    if BG.setBtn then
        SetButtonSelected(BG.setBtn, show)
        if BG.setBtn.__icon then
            local c = show and ns.SET_ICON_ACT or ns.SET_ICON_IDLE
            BG.setBtn.__icon:SetVertexColor(c[1], c[2], c[3])
        end
    end
    if show and BG.SyncSettingPop then BG.SyncSettingPop() end
    if ns.QuickBar and ns.QuickBar.Reanchor then pcall(ns.QuickBar.Reanchor, ns.QuickBar) end
end

function BG.SyncSettingPop()
    local nd = #(SPEC_DIR[BG.cls] or {})
    for i = 1, 1 + 4 + W_SCHEME_MAX do
        local bt = BG.wBtns and BG.wBtns[i] or nil
        if bt then
            local sr = (SPEC_DIR[BG.cls] or {})[i - 1]
            if i == 1 then
                bt.tex:SetTexture(ClassIconPath(BG.cls))
                local active = BG.wRole == nil and BG.spec ~= "tank"
                bt.tex:SetDesaturated(not active)
                bt.tex:SetAlpha(active and 1 or 0.72)
                SetOutline(bt, active)
                bt:Show()
            elseif sr then
                bt.tex:SetTexture(sr.icon)
                local active
                if sr.role == "tank" then
                    active = BG.spec == "tank"
                else
                    active = BG.wRole == sr.key
                end
                bt.tex:SetDesaturated(not active)
                bt.tex:SetAlpha(active and 1 or 0.72)
                SetOutline(bt, active)
                bt:Show()
            elseif i <= 1 + nd then
                bt:Hide()
            else
                local sidx = i - 1 - nd
                local sch = BG.wSchemes and BG.wSchemes[sidx] or nil
                if sch then
                    bt.tex:SetTexture(sch.icon or W_ICONS[1])
                    local active = BG.wActive == sidx
                    bt.tex:SetDesaturated(not active)
                    bt.tex:SetAlpha(active and 1 or 0.72)
                    SetOutline(bt, active)
                    bt:Show()
                else
                    bt:Hide()
                end
            end
        end
    end
    local base = SpecWeights(BG.cls, BG.spec)
    local sch = BG.wActive and BG.wSchemes and BG.wSchemes[BG.wActive] or nil
    for _, row in ipairs(BG.wRows or {}) do
        local v = (sch and sch.w[row.key]) or base[row.key] or 0
        local txt = format("%.2f", v)
        if sch then
            if row.eb then row.eb:SetShown(true) end
            row.ro:SetShown(false)
            if row.eb then row.eb:SetText(txt) end
            row.lab:SetTextColor(Unpack(C_TEXT))
        else
            if row.eb then row.eb:SetShown(false) end
            row.ro:SetShown(true)
            row.ro:SetText(txt)
            row.lab:SetTextColor(0.55, 0.58, 0.65, 1)
        end
    end
    if BG.wHint then BG.wHint:SetShown(not sch) end
end

function BG.GeneratePlan()
    BG.StartManualGen()
end

function BG.SetSlot(slotKey, itemID)
    if not slotKey then return end
    local dk = DataKey(SpecRec(), slotKey)
    if itemID == nil then BG.cur[dk] = nil else BG.cur[dk] = itemID end
    BG.RequestRender()
end

function BG.SelectSlot(slotKey)
    BG.sel = slotKey
    BG.RequestRender()
end

function BG.SelectClass(slug)
    BG.__clsPicked = true
    BG.cls = slug
    BG.cur = {}
    BG.ench = {}
    BG.usingPlan = nil
    BG.autoPlan = nil
    BG.AutoJobCancel()
    BG.sel = nil
    BG.side = nil
    BG.pkey = nil
    local dir = SPEC_DIR[slug] or {}
    local first = dir[1]
    BG.tspec = first and first.key or nil
    local ds = (first and first.role == "tank") and "tank" or "pve"
    local c = ClassRec()
    local okSpec = false
    if c then
        for _, sp in ipairs(c.specs) do
            if sp.id == ds then okSpec = true break end
        end
        if not okSpec and c.specs[1] then ds = c.specs[1].id end
    end
    BG.spec = ds
    local wr = (first and first.role ~= "tank") and first.key or nil
    if BG.wRole ~= wr then
        BG.wRole = wr
        SaveWeightPrefs()
        BumpWeights()
    end
    SyncSpecFromTspec()
    BG.RequestRender()
    if BG.settingPop and BG.settingPop:IsShown() and BG.SyncSettingPop then BG.SyncSettingPop() end
end

function BG.SelectSpec(id)
    local ap = BG.autoPlan
    BG.spec = id
    BG.pkey = nil
    BG.side = nil
    BG.cur = {}
    BG.ench = {}
    BG.usingPlan = nil
    BG.autoPlan = ap
    if ap then
        BG.UseAutoPlan(ap)
    else
        BG.RequestRender()
    end
    if BG.settingPop and BG.settingPop:IsShown() and BG.SyncSettingPop then BG.SyncSettingPop() end
end

function BG.SavePlan()
    local sp = SpecRec()
    if not sp then return end
    local plans = PlansFor(BG.cls)
    local items, seen = {}, {}
    for _, key in ipairs(ALL_SLOT_KEYS) do
        local dk = DataKey(sp, key)
        if not seen[dk] then
            seen[dk] = true
            local id = CurItem(sp, dk)
            if not id and BG.usingPlan == nil and BG.autoPlan == nil then id = RecItem(sp, dk) end
            if id then items[dk] = id end
        end
    end
    local enchs = {}
    for _, dk in ipairs(ALL_SLOT_KEYS) do
        local eid = CurEnch(sp, dk)
        if eid then enchs[dk] = eid end
    end
    local srcLv = (BG.usingPlan and BG.usingPlan.manual and BG.usingPlan.vol) or CurVol().lv
    local p = { name = format(L["%d级 · %s · 我的方案 %d"], srcLv, TSpecLabel(), #plans + 1),
                items = items, enchs = enchs, tspec = BG.tspec,
                vol = srcLv }
    plans[#plans + 1] = p
    BG.cur = {}
    BG.ench = {}
    BG.usingPlan = p
    BG.autoPlan = nil
    BG.AutoJobCancel()
    BG.RequestRender()
end

function BG.UsePlan(plan)
    BG.cur = {}
    BG.ench = {}
    BG.usingPlan = plan
    BG.autoPlan = nil
    BG.AutoJobCancel()
    BG.pkey = nil
    if plan then
        if plan.vol then
            for i, v in ipairs(VOLS) do
                if v.lv == plan.vol then BG.vol = i break end
            end
        end
        if plan.tspec then
            for _, sr in ipairs(SPEC_DIR[BG.cls] or {}) do
                if sr.key == plan.tspec then
                    BG.tspec = sr.key
                    if sr.role == "tank" then
                        if BG.wRole ~= nil then
                            BG.wRole = nil
                            SaveWeightPrefs()
                            BumpWeights()
                        end
                        BG.spec = "tank"
                    else
                        if BG.wRole ~= sr.key then
                            BG.wRole = sr.key
                            SaveWeightPrefs()
                            BumpWeights()
                        end
                        BG.spec = "pve"
                    end
                    SyncSpecFromTspec()
                    break
                end
            end
        elseif plan.spec then
            local c = ClassRec()
            if c then
                for _, sp in ipairs(c.specs) do
                    if sp.id == plan.spec then BG.spec = plan.spec end
                end
            end
        end
    end
    BG.RequestRender()
end

function BG.UsePreset(idx, specId, side, pageKey, tspec)
    if not VOLS[idx] then return end
    BG.vol = idx
    if tspec then BG.tspec = tspec end
    if pageKey then BG.pkey = pageKey end
    if specId then BG.spec = specId else SyncSpecFromTspec() end
    BG.side = side or nil
    BG.cur = {}
    BG.ench = {}
    BG.usingPlan = nil
    BG.autoPlan = nil
    BG.AutoJobCancel()
    BG.RequestRender()
end

function BG.ResetToRec()
    BG.cur = {}
    BG.ench = {}
    BG.usingPlan = nil
    BG.autoPlan = nil
    BG.AutoJobCancel()
    BG.RequestRender()
end

function BG.SweepNames()
    if not BG.built then
        BG._sweepQueued = false
        return
    end
    BG.needNames = false
    BG.needScores = false
    local dpsScanN = 0
    local miss = 0
    local sp = SpecRec()
    if sp then
        for _, key in ipairs(ALL_SLOT_KEYS) do
            local id = CurItem(sp, key)
            if id then
                local _, ok = DG.ItemName(id)
                if not ok then
                    miss = miss + 1
                    BG.needNames = true
                    DG.RequestItem(id)
                end
            end
            local eid = CurEnch(sp, key)
            if eid then
                local _, ok = DG.ItemName(eid)
                if not ok then
                    miss = miss + 1
                    BG.needNames = true
                    DG.RequestItem(eid)
                end
            end
        end
        for _, row in ipairs(BG.pool or {}) do
            local _, ok = DG.ItemName(row.item)
            if not ok then
                miss = miss + 1
                BG.needNames = true
                DG.RequestItem(row.item)
            end
            if row.cat and statCache[row.item] == nil then
                if not askedItem[row.item] then
                    askedItem[row.item] = true
                    local gm = ns.GearModule
                    if gm and gm.AskItem then gm.AskItem(row.item) end
                end
                if ItemScore(row.item, EffWeights()) then
                    BG.needScores = true
                end
            end
            if row.isWep and row.cat and dpsCache[row.item] == nil and not dpsMiss[row.item] then
                if dpsScanN < 12 then
                    dpsScanN = dpsScanN + 1
                    ScanDps(row.item)
                else
                    BG.needScores = true
                end
            end
            if row.src and row.src.t == "quest" and row.src.q then
                local qid = tonumber(row.src.q)
                if qid and not QuestTitle(qid) then miss = miss + 1; BG.needNames = true end
            end
        end
        if BG.baseWep and BG.baseId and dpsCache[BG.baseId] == nil and not dpsMiss[BG.baseId] then
            if dpsScanN < 12 then
                dpsScanN = dpsScanN + 1
                ScanDps(BG.baseId)
            else
                BG.needScores = true
            end
        end
        for _, r in ipairs(BG.enchRows or {}) do
            if r.__ench and r.__ench.item then
                local _, ok = DG.ItemName(r.__ench.item)
                if not ok then miss = miss + 1; BG.needNames = true; DG.RequestItem(r.__ench.item) end
            end
        end
    end
    local prevMiss = BG._sweepMiss
    BG._sweepMiss = miss
    if not prevMiss or miss < prevMiss then
        BG._sweepFails = 0
    else
        BG._sweepFails = math.min((BG._sweepFails or 0) + 1, 6)
    end
    local onScreen = ns.PageVisible(BG.page)
    if not prevMiss or miss < prevMiss or (miss > 0 and onScreen) then BG.RequestRender() end
    if (BG.needNames or BG.needScores) and (BG._sweepFails or 0) < 6 then
        BG.ScheduleSweep()
    end
end

function BG.ScheduleSweep()
    if BG._sweepQueued then return end
    if type(C_Timer) ~= "table" or type(C_Timer.After) ~= "function" then return end
    if (BG._sweepFails or 0) >= 6 then return end
    BG._sweepQueued = true
    local wait = 1.0
    for _ = 1, (BG._sweepFails or 0) do wait = wait * 2 end
    if wait > 10 then wait = 10 end
    C_Timer.After(wait, function()
        BG._sweepQueued = false
        BG.SweepNames()
    end)
end

function BG.OnItemData()
    if not BG.built or BG._itemRepaint then return end
    if not ns.PageVisible(BG.page) then return end
    BG.needNames = true
    local evtNow = (type(GetTime) == "function") and GetTime() or 0
    if BG.__evtT and (evtNow - BG.__evtT) < 1 then return end
    BG.__evtT = evtNow
    BG._itemRepaint = true
    if type(C_Timer) == "table" and type(C_Timer.After) == "function" then
        C_Timer.After(0.05, function()
            BG._itemRepaint = false
            if BG.needNames then BG.SweepNames() end
        end)
    else
        BG._itemRepaint = false
    end
end

local function MakeCell(parent, w, slotLabel, mirror)
    local c = CreateFrame("Button", nil, parent, BT)
    c:SetSize(w, 44)
    local hfx = ns.hui and ns.hui.HuiCardFX or nil
    if not (hfx and hfx(c, 6, 2)) then Cardify(c) end
    c.icon = c:CreateTexture(nil, "ARTWORK")
    c.icon:SetSize(26, 26)
    c.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
    if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(c.icon) end
    c.slot = MakeFS(c, 14, C_GREY, "LEFT")
    c.slot:SetWordWrap(false)
    c.slot:SetText(slotLabel)
    c.name = MakeFS(c, 14, C_TEXT, "LEFT")
    c.name:SetWidth(w - 42)
    c.name:SetWordWrap(false)
    c.ench = MakeFS(c, 14, C_GREEN, "LEFT")
    c.ench:SetWordWrap(false)
    c.dot = c:CreateTexture(nil, "OVERLAY")
    c.dot:SetSize(5, 5)
    c.dot:SetColorTexture(0.94, 0.71, 0.24, 1)
    c.dot:SetShown(false)
    if not mirror then
        c.slot:SetPoint("TOPLEFT", c, "TOPLEFT", 6, -3)
        c.ench:SetPoint("TOPRIGHT", c, "TOPRIGHT", -6, -3)
        c.icon:SetPoint("TOPLEFT", c, "TOPLEFT", 6, -16)
        c.name:SetPoint("LEFT", c.icon, "RIGHT", 6, 0)
    else
        c.slot:SetPoint("TOPRIGHT", c, "TOPRIGHT", -6, -3)
        c.slot:SetJustifyH("RIGHT")
        c.ench:SetPoint("TOPLEFT", c, "TOPLEFT", 6, -3)
        c.icon:SetPoint("TOPRIGHT", c, "TOPRIGHT", -6, -16)
        c.name:SetPoint("RIGHT", c.icon, "LEFT", -6, 0)
        c.name:SetJustifyH("RIGHT")
    end
    c:SetScript("OnEnter", function(self)
        if self.__huiCard then ns.hui.HuiCardState(self, "hover") end
        local sp = SpecRec()
        local id = CurItem(sp, self.__key)
        if id and not (self.__key == "off" and MainKey(sp) == "two-hand") then
            ItemTip(self, id)
        end
    end)
    c:SetScript("OnLeave", function(self)
        if self.__huiCard then ns.hui.HuiCardState(self, self.__sel and "hover" or "norm") end
        TipOff()
    end)
    return c
end

local function ClickSlot(key, dkey)
    return function(self)
        local sp = SpecRec()
        local id = CurItem(sp, key)
        if IsShiftKeyDown() then
            if id then
                LinkToChat(id)
                return
            end
        end
        if type(IsControlKeyDown) == "function" and IsControlKeyDown() then
            if id and DG and DG.TryOn then
                DG.TryOn(id)
                return
            end
        end
        BG.SelectSlot(dkey or key)
        ns.PlaySound(1)
    end
end

function BG.OpenClassMenu(owner)
    local items = {}
    for _, c in ipairs(BIS.classes or {}) do
        local color
        local rc = RAID_CLASS_COLORS and RAID_CLASS_COLORS[CLASS_FILE[c.slug] or ""]
        if rc and rc.r then
            color = format("|cFF%02X%02X%02X",
                math.floor(rc.r * 255 + 0.5), math.floor(rc.g * 255 + 0.5),
                math.floor(rc.b * 255 + 0.5))
        end
        items[#items + 1] = {
            text = (c.slug == BG.cls and "● " or "") .. ClassName(c.slug),
            color = color,
            func = function() BG.SelectClass(c.slug) end,
        }
    end
    ns.hui.ShowMenu(items, { owner = owner })
end

local function BuildVBar(scroll, child, extra)
    local track = CreateFrame("Frame", nil, scroll:GetParent(), BT)
    if ns.hui and ns.hui.BuildCapsule then
        ns.hui.BuildCapsule(track, 3, ns.hui.layer.L2)
    else
        track:SetBackdrop({
            bgFile = "Interface\\Buttons\\WHITE8x8",
            edgeFile = "Interface\\Buttons\\WHITE8x8",
            edgeSize = 1,
        })
        track:SetBackdropColor(0, 0, 0, 0.25)
        track:SetBackdropBorderColor(1, 1, 1, 0.08)
    end
    track:SetWidth(7)
    track:SetFrameLevel((scroll:GetFrameLevel() or 0) + 10)
    track:Hide()
    local thumb = CreateFrame("Button", nil, track)
    thumb:SetWidth(5)
    thumb:EnableMouse(true)
    local tp = nil
    local tx = nil
    if ns.hui and ns.hui.BuildCapsule then
        tp = ns.hui.BuildCapsule(thumb, 2, ns.hui.layer.L4)
    else
        tx = thumb:CreateTexture(nil, "OVERLAY")
        tx:SetAllPoints()
        tx:SetColorTexture(1, 1, 1, 0.30)
    end
    thumb:SetScript("OnEnter", function()
        if tp then
            local L5 = ns.hui.layer.L5
            for _, t in ipairs(tp) do t:SetVertexColor(L5[1], L5[2], L5[3]) end
        elseif tx then
            tx:SetColorTexture(1, 1, 1, 0.45)
        end
    end)
    thumb:SetScript("OnLeave", function()
        if tp then
            local L4 = ns.hui.layer.L4
            for _, t in ipairs(tp) do t:SetVertexColor(L4[1], L4[2], L4[3]) end
        elseif tx then
            tx:SetColorTexture(1, 1, 1, 0.30)
        end
    end)
    thumb:SetPoint("TOP", track, "TOP", 0, -1)
    local bar = { track = track }
    function bar.Update()
        local viewH = scroll:GetHeight()
        local contentH = child:GetHeight()
        if not scroll:IsVisible() or contentH <= viewH + 2 or viewH <= 0 then
            track:Hide()
            return
        end
        track:ClearAllPoints()
        track:SetPoint("TOPRIGHT", scroll, "TOPRIGHT", 7, -2)
        track:SetPoint("BOTTOMRIGHT", scroll, "BOTTOMRIGHT", 7, 2)
        track:Show()
        local trackH = track:GetHeight() - 2
        local maxScroll = contentH - viewH
        local vpos = scroll.GetVerticalScroll and scroll:GetVerticalScroll() or 0
        if type(vpos) ~= "number" then vpos = 0 end
        local frac = math.min(1, math.max(0, vpos / maxScroll))
        local th = math.max(24, trackH * viewH / contentH)
        thumb:SetHeight(th)
        thumb:ClearAllPoints()
        thumb:SetPoint("TOP", track, "TOP", 0, -1 - frac * (trackH - th))
    end
    scroll:SetScript("OnVerticalScroll", function()
        if extra then extra() end
        bar.Update()
    end)
    thumb:SetScript("OnMouseDown", function(self, btn)
        if btn ~= "LeftButton" then return end
        local scale = UIParent and UIParent:GetEffectiveScale() or 1
        local cy0 = select(2, GetCursorPosition()) / scale
        local sc0 = scroll:GetVerticalScroll()
        self:SetScript("OnUpdate", function()
            local cy = select(2, GetCursorPosition()) / scale
            local trackH = track:GetHeight() - 2
            local span = trackH - thumb:GetHeight()
            if span <= 0 then return end
            local maxScroll = child:GetHeight() - scroll:GetHeight()
            scroll:SetVerticalScroll(math.min(maxScroll, math.max(0, sc0 + (cy0 - cy) / span * maxScroll)))
        end)
    end)
    thumb:SetScript("OnMouseUp", function(self)
        self:SetScript("OnUpdate", nil)
    end)
    thumb:SetScript("OnHide", function(self)
        self:SetScript("OnUpdate", nil)
    end)
    return bar
end

local function BuildSpecRow(parent, yt)
    local x, y = 8, yt
    local dd = NewButton(parent, ClassName(BG.cls), 91, 24, 14)
    dd:SetPoint("TOPLEFT", parent, "TOPLEFT", x, -y)
    dd.lbl = dd:GetFontString()
    dd.lbl:ClearAllPoints()
    dd.lbl:SetPoint("LEFT", dd, "LEFT", 27, 0)
    local rc0 = RAID_CLASS_COLORS and RAID_CLASS_COLORS[CLASS_FILE[BG.cls] or ""]
    if rc0 and rc0.r then dd.lbl:SetTextColor(rc0.r, rc0.g, rc0.b) end
    local ic = dd:CreateTexture(nil, "ARTWORK")
    ic:SetSize(16, 16)
    ic:SetPoint("LEFT", dd, "LEFT", 6, 0)
    ic:SetTexture(ClassIconPath(BG.cls))
    dd.__icon = ic
    dd:SetScript("OnClick", function() BG.OpenClassMenu(dd) end)
    BG.ddBtn = dd
    x = x + 99
    BG.tspecBtns = {}
    for i = 1, 4 do
        local bt = NewButton(parent, "", 60, 24, 14)
        bt:SetPoint("TOPLEFT", parent, "TOPLEFT", x, -y)
        bt.lbl = bt:GetFontString()
        bt.lbl:ClearAllPoints()
        bt.lbl:SetPoint("LEFT", bt, "LEFT", 19, 0)
        bt.__icon = bt:CreateTexture(nil, "ARTWORK")
        bt.__icon:SetSize(14, 14)
        bt.__icon:SetPoint("LEFT", bt, "LEFT", 3, 0)
        bt.__icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
        SetButtonSelected(bt, false)
        bt:SetScript("OnClick", function()
            local sr = (SPEC_DIR[BG.cls] or {})[i]
            if not sr then return end
            local on = (sr.role == "tank" and BG.spec == "tank")
                or (sr.role ~= "tank" and BG.spec ~= "tank" and BG.tspec == sr.key)
            if on then return end
            ns.PlaySound(1)
            BG.tspec = sr.key
            BG.pkey = nil
            BG.cur = {}
            BG.ench = {}
            BG.usingPlan = nil
            if sr.role == "tank" then
                BG.spec = "tank"
                BG.wRole = nil
                SaveWeightPrefs()
            else
                BG.spec = "pve"
                if BG.wRole ~= sr.key then
                    BG.wRole = sr.key
                    SaveWeightPrefs()
                    BumpWeights()
                end
            end
            SyncSpecFromTspec()
            if BG.usingPlan == nil and BG.autoPlan then
                BG.UseAutoPlan(BG.autoPlan)
            else
                BG.RequestRender()
            end
            if BG.settingPop and BG.settingPop:IsShown() and BG.SyncSettingPop then BG.SyncSettingPop() end
        end)
        BG.tspecBtns[i] = bt
        x = x + 68
    end
    BG.head = MakeFS(parent, 16, C_WHITE, "LEFT")
    BG.head:SetPoint("TOPLEFT", parent, "TOPLEFT", 8, -(yt + 30))
    return yt + 48
end

local function BuildDoll(parent, lt)
    BG.dollCells = {}
    local w, lh = 177, 52
    for i, key in ipairs(SLOTS_LEFT) do
        local c = MakeCell(parent, w, SLOT_NAMES[key] or key, false)
        c.__key = key
        c:SetPoint("TOPLEFT", parent, "TOPLEFT", 8, -(lt + (i - 1) * lh))
        c:SetScript("OnClick", ClickSlot(key))
        BG.dollCells[key] = c
    end
    local rx = 8 + w + 8
    for i, key in ipairs(SLOTS_RIGHT) do
        local c = MakeCell(parent, w, SLOT_NAMES[key] or key, true)
        c.__key = key
        c:SetPoint("TOPLEFT", parent, "TOPLEFT", rx, -(lt + (i - 1) * lh))
        c:SetScript("OnClick", ClickSlot(key))
        BG.dollCells[key] = c
    end
    local wy = lt + #SLOTS_RIGHT * lh
    for i, wk in ipairs({ { "main", L["主手"], false }, { "ranged", L["远程"], true } }) do
        local c = MakeCell(parent, w, wk[2], wk[3])
        c.__key = wk[1]
        c:SetPoint("TOPLEFT", parent, "TOPLEFT",
                   i == 1 and 8 or rx, -wy)
        c:SetScript("OnClick", ClickSlot(wk[1], wk[1] == "main" and "main" or nil))
        BG.dollCells[wk[1]] = c
    end
    local off = MakeCell(parent, w, L["副手"], false)
    off.__key = "off"
    off:SetPoint("TOPLEFT", parent, "TOPLEFT", 8, -(wy + 44 + 8))
    off:SetScript("OnClick", ClickSlot("off"))
    BG.dollCells["off"] = off
    return wy + 44 + 8 + 44
end

local function MakePlanRow(parent)
    local r = CreateFrame("Button", nil, parent, BT)
    r:SetHeight(PLAN_H)
    r:RegisterForClicks("LeftButtonUp", "RightButtonUp")
    local hfx = ns.hui and ns.hui.HuiCardFX or nil
    if not (hfx and hfx(r, 6, 2)) then Cardify(r) end
    r.title = MakeFS(r, 14, C_TEXT, "LEFT")
    r.title:SetPoint("TOPLEFT", r, "TOPLEFT", 8, -2)
    r.title:SetPoint("BOTTOMLEFT", r, "BOTTOMLEFT", 8, 2)
    r.title:SetWordWrap(false)
    r.title:SetPoint("RIGHT", r, "RIGHT", -30, 0)
    r.meta = MakeFS(r, 14, C_GREY, "LEFT")
    r.meta:SetShown(false)
    if r.SetClipsChildren then r:SetClipsChildren(true) end
    r.dot = CreateFrame("Frame", nil, r)
    r.dot:SetSize(14, 14)
    r.dot:SetPoint("BOTTOMRIGHT", r, "BOTTOMRIGHT", -8, 7)
    r.dot.ring = r.dot:CreateTexture(nil, "BACKGROUND")
    r.dot.ring:SetAllPoints()
    r.dot.ring:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\CheckRing")
    r.dot.disc = r.dot:CreateTexture(nil, "BORDER")
    r.dot.disc:SetAllPoints()
    r.dot.disc:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\CheckDisc")
    r.dot.disc:SetVertexColor(C_GREEN[1], C_GREEN[2], C_GREEN[3])
    r.dot.mark = r.dot:CreateTexture(nil, "OVERLAY")
    r.dot.mark:SetAllPoints()
    r.dot.mark:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\CheckMark")
    r.dot:SetShown(false)
    r:SetScript("OnEnter", function(self)
        if self.__huiCard then ns.hui.HuiCardState(self, "hover") end
    end)
    r:SetScript("OnLeave", function(self)
        if self.__huiCard then ns.hui.HuiCardState(self, self.__sel and "hover" or "norm") end
    end)
    if ns.CreateEditBox then
        r.edit = ns.CreateEditBox(r, 190)
        r.edit:SetPoint("TOPLEFT", r, "TOPLEFT", 5, -3)
    else
        r.edit = CreateFrame("EditBox", nil, r, BT)
        r.edit:SetAllPoints()
    end
    r.edit:SetAutoFocus(false)
    r.edit:SetMaxLetters(16)
    r.edit:Hide()
    r.edit:SetScript("OnEnterPressed", function(self)
        local p = r.__plan
        local txt = self:GetText()
        if p and txt ~= "" then p.name = txt end
        self:ClearFocus()
        self:Hide()
        BG.RequestRender()
    end)
    r.edit:SetScript("OnEscapePressed", function(self)
        self:ClearFocus()
        self:Hide()
    end)
    r.edit:SetScript("OnEditFocusLost", function(self) self:Hide() end)
    r:SetScript("OnClick", function(self, button)
        if button == "RightButton" and self.__plan then
            if IsShiftKeyDown() then
                local plans = PlansFor(BG.cls)
                for i, p in ipairs(plans) do
                    if p == self.__plan then table.remove(plans, i) break end
                end
                if BG.usingPlan == self.__plan then BG.usingPlan = nil end
                BG.RequestRender()
                return
            end
            self.edit:SetText(self.__plan.name or "")
            self.edit:Show()
            self.edit:SetFocus()
            return
        end
        if self.__plan then
            BG.UsePlan(self.__plan)
        elseif self.__auto then
            BG.UseAutoPlan(self.__auto)
        elseif self.__manual then
            BG.UseManualPlan()
        elseif self.__vol then
            BG.UsePreset(self.__vol, self.__spec, self.__side, self.__key, self.__tspec)
        else
            BG.ResetToRec()
        end
        ns.PlaySound(1)
    end)
    return r
end

local function BuildMid(m1, m2)
    local x, w = 8, 208
    BG.planHead = MakeFS(m1, 16, C_WHITE, "LEFT")
    BG.planHead:SetPoint("TOPLEFT", m1, "TOPLEFT", x, -8)
    BG.planHead:SetText(L["方案"])
    local tw = BG.planHead:GetStringWidth() or 0
    BG.renameBtn = NewButton(m1, L["改名"], 56, 24, 14)
    BG.renameBtn.lbl = BG.renameBtn:GetFontString()
    BG.renameBtn:SetPoint("TOPLEFT", m1, "TOPLEFT", x + tw + 8, -8)
    BG.renameBtn:SetScript("OnClick", function()
        local p = BG.usingPlan
        if not p then return end
        for _, r in ipairs(BG.planRows) do
            if r.__plan == p then
                r.edit:SetText(p.name or "")
                r.edit:Show()
                r.edit:SetFocus()
                return
            end
        end
    end)
    BG.deleteBtn = NewButton(m1, L["删除"], 56, 24, 14)
    BG.deleteBtn.lbl = BG.deleteBtn:GetFontString()
    BG.deleteBtn:SetPoint("TOPLEFT", m1, "TOPLEFT", x + tw + 72, -8)
    BG.deleteBtn:SetScript("OnClick", function()
        local p = BG.usingPlan
        if not p then return end
        local plans = PlansFor(BG.cls)
        for i, q in ipairs(plans) do
            if q == p then table.remove(plans, i) break end
        end
        BG.usingPlan = nil
        BG.RequestRender()
        ns.PlaySound(1)
    end)

    local save = NewButton(m1, L["另存当前"], (w - 8) / 2, 24, 14)
    save:SetPoint("TOPLEFT", m1, "TOPLEFT", x, -40)
    save:SetScript("OnClick", function() BG.SavePlan() end)
    local reset = NewButton(m1, L["恢复推荐"], (w - 8) / 2, 24, 14)
    reset:SetPoint("TOPLEFT", m1, "TOPLEFT", x + (w - 8) / 2 + 8, -40)
    reset:SetScript("OnClick", function() BG.ResetToRec() end)
    BG.saveBtn, BG.resetBtn = save, reset

    local pool = CreateFrame("ScrollFrame", nil, m1)
    if pool.SetClipsChildren then pool:SetClipsChildren(true) end
    pool:EnableMouseWheel(true)
    local child = CreateFrame("Frame", nil, pool)
    child:SetSize(w, 10)
    pool:SetScrollChild(child)
    pool:SetPoint("TOPLEFT", m1, "TOPLEFT", x, -72)
    pool:SetPoint("BOTTOMRIGHT", m1, "BOTTOMRIGHT", -8, 8)
    pool:SetScript("OnMouseWheel", function(_, delta)
        DG.WheelScroll(pool, child, delta)
        BG.FitPlanRows()
    end)
    BG.planScroll, BG.planChild = pool, child
    BG.planRows = {}
    for i = 1, N_PRESET + N_USER do
        local r = MakePlanRow(child)
        BG.planRows[i] = r
    end
    BG.planBar = BuildVBar(pool, child, function() BG.FitPlanRows() end)

    BG.statHead = MakeFS(m2, 16, C_WHITE, "LEFT")
    BG.statHead:SetPoint("TOPLEFT", m2, "TOPLEFT", x, -8)
    BG.statHead:SetText(L["属性汇总"])
    BG.statRows = {}
    for i, sr in ipairs(STAT_ROWS) do
        local ry = 32 + (i - 1) * 24
        local lab = MakeFS(m2, 14, C_GREY, "LEFT")
        lab:SetPoint("TOPLEFT", m2, "TOPLEFT", x, -ry)
        lab:SetWordWrap(false)
        lab:SetText(sr[2])
        local val = MakeFS(m2, 14, C_GREEN, "RIGHT")
        val:SetPoint("TOPRIGHT", m2, "TOPRIGHT", -x, -ry)
        val:SetWordWrap(false)
    BG.statRows[i] = { sr[1], lab = lab, val = val }
end
BG.statParent = m2
end

local function BuildBrowser(parent)
    local x, w = 8, 309
    BG.bwTitle = MakeFS(parent, 16, C_WHITE, "LEFT")
    BG.bwTitle:SetPoint("TOPLEFT", parent, "TOPLEFT", x, -8)
    BG.bwTitle:SetWidth(w - 16 - 258)
    BG.bwTitle:SetWordWrap(false)

    local eb = ns.CreateEditBox and ns.CreateEditBox(parent, 150) or CreateFrame("EditBox", nil, parent)
    eb:SetSize(150, 22)
    eb:SetPoint("TOPRIGHT", parent, "TOPRIGHT", -x, -8)
    eb:SetAutoFocus(false)
    eb:SetMaxLetters(30)
    eb:SetScript("OnEscapePressed", function(self) self:ClearFocus() end)
    local ph = MakeFS(eb, 14, C_DIM, "LEFT")
    ph:SetPoint("LEFT", eb, "LEFT", 8, 0)
    ph:SetText(L["搜索物品…"])
    eb:SetScript("OnTextChanged", function(self)
        BG.search = string.lower(self:GetText() or "")
        ph:SetShown(self:GetText() == "")
        BG.RequestRender()
    end)

    local fb = NewButton(parent, L["过滤"], 60, 24, 14)
    fb:SetPoint("RIGHT", eb, "LEFT", -8, 0)
    fb.lbl = fb:GetFontString()
    SetButtonSelected(fb, false)
    fb:SetScript("OnClick", function() BG.ToggleFilterPop() end)
    BG.filterBtn = fb

    local stb = NewButton(parent, "", 24, 24, 14)
    stb:SetPoint("RIGHT", fb, "LEFT", -8, 0)
    stb.lbl = stb:GetFontString()
    stb.__icon = stb:CreateTexture(nil, "ARTWORK")
    stb.__icon:SetSize(16, 16)
    stb.__icon:SetPoint("CENTER", stb, "CENTER", 0, 0)
    stb.__icon:SetTexture(ns.SET_ICON)
    stb.__icon:SetVertexColor(ns.SET_ICON_IDLE[1], ns.SET_ICON_IDLE[2], ns.SET_ICON_IDLE[3])
    stb:SetScript("OnEnter", function()
        stb.__icon:SetVertexColor(ns.SET_ICON_ON[1], ns.SET_ICON_ON[2], ns.SET_ICON_ON[3])
    end)
    stb:SetScript("OnLeave", function()
        local c = (BG.settingPop and BG.settingPop:IsShown()) and ns.SET_ICON_ACT or ns.SET_ICON_IDLE
        stb.__icon:SetVertexColor(c[1], c[2], c[3])
    end)
    stb:SetScript("OnClick", function() BG.ToggleSettingPop() end)
    BG.setBtn = stb
    if ns.hui and ns.hui.SetButtonFrameless then ns.hui.SetButtonFrameless(stb, true) end

    local scroll = CreateFrame("ScrollFrame", nil, parent)
    scroll:EnableMouseWheel(true)
    local child = CreateFrame("Frame", nil, scroll)
    child:SetSize(w - 8, 10)
    scroll:SetScrollChild(child)
    scroll:SetPoint("TOPLEFT", parent, "TOPLEFT", x, -40)
    scroll:SetPoint("BOTTOMRIGHT", parent, "BOTTOMRIGHT", -x, 8)
    scroll:SetScript("OnMouseWheel", function(_, delta)
        DG.WheelScroll(scroll, child, delta)
        CullBwRows()
    end)
    scroll:SetScript("OnVerticalScroll", function() CullBwRows() end)
    BG.bwScroll, BG.bwChild = scroll, child
    BG.bwBar = BuildVBar(scroll, child, CullBwRows)

    BG.bwRows = {}
    local poolN = BG.BwPoolSize()
    BG.bwPoolN = poolN
    for i = 1, poolN do
        local r = CreateFrame("Button", nil, child, BT)
        r:SetHeight(ROW_H)
        local hfx = ns.hui and ns.hui.HuiCardFX or nil
        if not (hfx and hfx(r, 6, 2)) then Cardify(r) end
        r.icon = r:CreateTexture(nil, "ARTWORK")
        r.icon:SetSize(30, 30)
        r.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
        if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(r.icon) end
        r.icon:SetPoint("LEFT", r, "LEFT", 6, 0)
        r.name = MakeFS(r, 14, C_TEXT, "LEFT")
        r.name:SetPoint("TOPLEFT", r, "TOPLEFT", 44, -5)
        r.name:SetWordWrap(false)
        r.src = MakeFS(r, 14, C_GREY, "LEFT")
        r.src:SetPoint("TOPLEFT", r, "TOPLEFT", 44, -24)
        r.src:SetPoint("RIGHT", r, "RIGHT", -52, 0)
        r.src:SetWordWrap(false)
        r.eqTag = MakeFS(r, 14, C_GOLD, "LEFT")
        r.eqTag:SetPoint("LEFT", r.name, "RIGHT", 8, 0)
        r.eqTag:SetWordWrap(false)
        r.eqTag:SetText(L["已装备"])
        r.eqTag:SetShown(false)
        r.ownTag = MakeFS(r, 14, C_GREEN, "LEFT")
        r.ownTag:SetPoint("LEFT", r.eqTag, "RIGHT", 6, 0)
        r.ownTag:SetWordWrap(false)
        r.ownTag:SetText(L["已收藏"])
        r.ownTag:SetShown(false)
        r.chip = DG.MakeBadge(r)
        r.chip:SetFrameLevel(r:GetFrameLevel() + 2)
        r.chip2 = DG.MakeBadge(r)
        r.chip2:SetFrameLevel(r:GetFrameLevel() + 2)
        r.chip3 = DG.MakeBadge(r)
        r.chip3:SetFrameLevel(r:GetFrameLevel() + 2)
        r.sideTag = MakeFS(r, 14, C_GREY, "RIGHT")
        r.sideTag:SetPoint("TOPRIGHT", r, "TOPRIGHT", -6, -23)
        r.sideTag:SetWordWrap(false)
        r.wishBt = CreateFrame("Button", nil, r)
        r.wishBt:SetSize(22, 22)
        r.wishBt:SetPoint("BOTTOMRIGHT", r, "BOTTOMRIGHT", -2, 2)
        r.wishBt:EnableMouse(true)
        r.wishBt.star = MakeFS(r.wishBt, 18, C_GREY, "CENTER")
        r.wishBt.star:SetAllPoints()
        r.wishBt:SetScript("OnClick", function(self)
            local row = self:GetParent().__row
            local gm = ns.GearModule
            if not (row and row.item and gm and gm.WishToggle) then return end
            gm.WishToggle(row.item)
            ns.PlaySound(1)
            BG.RequestRender()
        end)
        r.wishBt:SetScript("OnEnter", function(self)
            local row = self:GetParent().__row
            local gm = ns.GearModule
            local on = gm and gm.WishIs and row and row.item and gm.WishIs(row.item)
            GameTooltip:SetOwner(self, "ANCHOR_LEFT")
            GameTooltip:SetText(on and L["移出心愿清单"] or L["加入心愿清单"], 1, 1, 1, 1, true)
            GameTooltip:Show()
        end)
        r.wishBt:SetScript("OnLeave", function() GameTooltip:Hide() end)
        r.pinBt = CreateFrame("Button", nil, r)
        r.pinBt:SetSize(13.75, 13.75)
        r.pinBt:SetPoint("BOTTOMRIGHT", r.wishBt, "BOTTOMLEFT", 2, 4.75)
        r.pinBt:EnableMouse(true)
        r.pinBt.tex = r.pinBt:CreateTexture(nil, "ARTWORK")
        r.pinBt.tex:SetAllPoints()
        r.pinBt.tex:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\EntryPin")
        r.pinBt:Hide()
        r.pinBt:SetScript("OnClick", function(self)
            local row = self:GetParent()
            if not row then return end
            local qid = row.__pinQid
            if qid and ns.GearMarkQuestSmart then
                local hasChain = ns.GearChainIndexOf and ns.GearChainIndexOf(qid)
                if hasChain or not row.__pinNpc then
                    ns.PlaySound(1)
                    ns.GearMarkQuestSmart(qid)
                    return
                end
            end
            if row.__pinNpc then
                DG.MarkNPC(row.__pinNpc, row.__pinLoc)
                ns.PlaySound(1)
            end
        end)
        r.pinBt:SetScript("OnEnter", function(self)
            local row = self:GetParent()
            if row and row.__pinNpc and DG.ShowNpcTip then
                DG.ShowNpcTip(self, row.__pinNpc, row.__pinLoc)
                return
            end
            local qid = row and row.__pinQid
            if not (qid and ns.GearChainIndexOf) then return end
            GameTooltip:SetOwner(self, "ANCHOR_LEFT")
            GameTooltip:ClearLines()
            if ns.GearChainIndexOf(qid) then
                GameTooltip:AddLine(L["点击：查看任务链"], 1, 0.82, 0, true)
            else
                GameTooltip:AddLine(L["点击：在地图上标记"], 1, 0.82, 0, true)
            end
            GameTooltip:Show()
        end)
        r.pinBt:SetScript("OnLeave", function() GameTooltip:Hide() end)
        r:SetScript("OnEnter", function(self)
            if self.__huiCard then ns.hui.HuiCardState(self, "hover") end
            local row = self.__row
            if not row then return end
            local st = row.cat and CatSrcText(row.item) or SrcText(row.src)
            ItemTip(self, row.item, st ~= "" and { st } or nil)
        end)
        r:SetScript("OnLeave", function(self)
            if self.__huiCard then ns.hui.HuiCardState(self, "norm") end
            TipOff()
        end)
        r:SetScript("OnClick", function(self)
            local row = self.__row
            if not row then return end
            if IsShiftKeyDown() then
                LinkToChat(row.item)
                return
            end
            if type(IsControlKeyDown) == "function" and IsControlKeyDown() then
                if DG and DG.TryOn then
                    DG.TryOn(row.item)
                    return
                end
            end
            BG.SetSlot(BG.sel, row.item)
            ns.PlaySound(1)
        end)
        r:EnableMouseWheel(true)
        r:SetScript("OnMouseWheel", function(_, delta)
            DG.WheelScroll(scroll, child, delta)
        end)
        BG.bwRows[i] = r
        if i % 15 == 0 then coroutine.yield() end
    end

    local baseLv = (parent.GetFrameLevel and type(parent:GetFrameLevel()) == "number")
        and parent:GetFrameLevel() or 0
    ns.EvtPool = ns.EvtPool or {}
    if not ns.EvtPool.bisGmd then
        local ev = CreateFrame("Frame")
        ns.EvtPool.bisGmd = ev
        ev:RegisterEvent("GLOBAL_MOUSE_DOWN")
        ev:SetScript("OnEvent", function()
            if not (BG.filterPop and BG.filterPop.IsShown and BG.filterPop:IsShown()) then return end
            if BG.filterPop:IsMouseOver() then return end
            if BG.filterBtn and BG.filterBtn.IsMouseOver and BG.filterBtn:IsMouseOver() then return end
            BG.ToggleFilterPop()
        end)
    end
    local pop = CreateFrame("Frame", nil, parent)
    pop:SetSize(170, 334)
    pop:EnableMouse(true)
    pop:SetFrameLevel(baseLv + 31)
    pop:Hide()
    if ns.hui and ns.hui.BuildRoundedBG then
        ns.hui.BuildRoundedBG(pop, 6, ns.hui.layer.L0, "both", true, 1)
    else
        Cardify(pop, nil, 2)
    end
    pop:SetPoint("TOPRIGHT", parent, "TOPLEFT", -8, -40)
    if ns.hui and ns.hui.SkinShadow then ns.hui.SkinShadow(pop) end
    BG.filterPop = pop

    local ty = MakeFS(pop, 14, C_GOLD, "LEFT")
    ty:SetPoint("TOPLEFT", pop, "TOPLEFT", 8, -8)
    ty:SetText(L["过滤器"])

    local ly = MakeFS(pop, 14, C_GREY, "LEFT")
    ly:SetPoint("TOPLEFT", pop, "TOPLEFT", 8, -28)
    ly:SetText(L["目标等级"])
    local eb = ns.CreateEditBox and ns.CreateEditBox(pop, 52) or nil
    if eb then
        eb:SetPoint("TOPLEFT", pop, "TOPLEFT", 8, -42)
        eb:SetNumeric(true)
    end
    local lvBox = eb
    BG.filterLvBox = eb
    local function FilterChanged()
        if BG.usingPlan == nil and BG.autoPlan then
            BG.UseAutoPlan(BG.autoPlan)
        else
            BG.RequestRender()
        end
    end
    local function ApplyLvText(txt)
        local n = tonumber(string.match(txt or "", "^%s*(%d+)%s*$"))
        if n then
            n = math.floor(n)
            if n < 1 then n = 1 elseif n > 60 then n = 60 end
        end
        BG.filterLv = n
        SaveFilterPrefs()
        FilterChanged()
    end
    if lvBox then
        lvBox:SetScript("OnEnterPressed", function(self)
            ApplyLvText(self:GetText())
            self:ClearFocus()
        end)
        lvBox:SetScript("OnEditFocusLost", function(self)
            if self.RestoreBorder then self:RestoreBorder() end
            ApplyLvText(self:GetText())
        end)
        lvBox:SetScript("OnEscapePressed", function(self) self:ClearFocus() end)
    end
    local nowBt = NewButton(pop, L["当前"], 44, 24, 14)
    nowBt:SetPoint("LEFT", lvBox or pop, "RIGHT", 6, 0)
    nowBt:SetScript("OnClick", function()
        local lv = PlayerLevel() or 60
        if lv < 1 then lv = 1 elseif lv > 60 then lv = 60 end
        if lvBox then lvBox:SetText(tostring(lv)) end
        ApplyLvText(tostring(lv))
        ns.PlaySound(1)
    end)
    local maxBt = NewButton(pop, L["满级"], 44, 24, 14)
    maxBt:SetPoint("LEFT", nowBt, "RIGHT", 8, 0)
    maxBt:SetScript("OnClick", function()
        if lvBox then lvBox:SetText("60") end
        ApplyLvText("60")
        ns.PlaySound(1)
    end)

    local ug = CreateFrame("CheckButton", nil, pop)
    ug:SetSize(36, 20)
    ug:EnableMouse(true)
    if ns.hui and ns.hui.ReskinToggle then ns.hui.ReskinToggle(ug) end
    ug:SetPoint("TOPRIGHT", pop, "TOPRIGHT", -8, -76)
    ug:SetScript("OnClick", function(self)
        BG.onlyUsable = not BG.onlyUsable
        self:SetChecked(BG.onlyUsable)
        SaveFilterPrefs()
        ns.PlaySound(1)
        FilterChanged()
    end)
    BG.usableTg = ug
    local ul = MakeFS(pop, 14, C_TEXT, "RIGHT")
    ul:SetPoint("RIGHT", ug, "LEFT", -6, 0)
    ul:SetWordWrap(false)
    ul:SetText(L["只显示可用种类"])

    local sy = MakeFS(pop, 14, C_GREY, "LEFT")
    sy:SetPoint("TOPLEFT", pop, "TOPLEFT", 8, -106)
    sy:SetText(L["来源"])

    local function SrcToggle(key)
        BG.srcSet[key] = not BG.srcSet[key]
        SaveFilterPrefs()
        BG.SyncFilterPop()
        ns.PlaySound(1)
        BG.RequestRender()
    end
    BG.srcRows = {}
    for i, f in ipairs(FILTERS) do
        local bt = CreateFrame("Button", nil, pop)
        bt:SetSize(154, 26)
        bt:SetPoint("TOPLEFT", pop, "TOPLEFT", 8, -(122 + (i - 1) * 28))
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
        bt.label:SetText(f.label)
        bt:SetScript("OnClick", function() SrcToggle(f.id) end)
        BG.srcRows[f.id] = bt
    end

    local gb = NewButton(pop, L["生成 BiS 方案"], 154, 24, 14)
    gb:SetPoint("TOPLEFT", pop, "TOPLEFT", 8, -296)
    gb.lbl = gb:GetFontString()
    SetButtonSelected(gb, false)
    gb:SetScript("OnClick", function()
        BG.GeneratePlan()
        BG.ToggleFilterPop()
        ns.PlaySound(1)
    end)

    local spop = CreateFrame("Frame", "DungeonsForever_BisSettings", ns.MainFrame or UIParent, "BackdropTemplate")
    spop:SetFrameLevel(512)
    spop:SetFrameStrata("HIGH")
    spop:EnableMouse(true)
    spop:SetScript("OnMouseWheel", function() end)
    spop:SetWidth(220)
    if ns.MainFrame then
        spop:SetPoint("TOPLEFT", ns.MainFrame, "TOPRIGHT", 4, 0)
        spop:SetPoint("BOTTOMLEFT", ns.MainFrame, "BOTTOMRIGHT", 4, 0)
    else
        spop:SetPoint("CENTER")
        spop:SetSize(220, 600)
    end
    spop:Hide()
    if ns.hui and ns.hui.SkinPopup then ns.hui.SkinPopup(spop, 8, "both", ns.hui.layer.L0) end
    if ns.hui and ns.hui.SkinShadow then ns.hui.SkinShadow(spop) end
    BG.settingPop = spop
    ns.CloseBisSettings = BG.CloseSettingPop
    ns.GetBisSettingsPop = function() return BG.settingPop end

    local sty = MakeFS(spop, 16, C_WHITE, "LEFT")
    sty:SetPoint("TOPLEFT", spop, "TOPLEFT", 8, -8)
    sty:SetText(L["评分权重"])

    local plus = CreateFrame("Button", nil, spop)
    plus:SetSize(18, 18)
    plus:SetPoint("TOPRIGHT", spop, "TOPRIGHT", -8, -36)
    plus.t = MakeFS(plus, 16, C_TEXT, "CENTER")
    plus.t:SetAllPoints()
    plus.t:SetText("+")
    plus:SetScript("OnEnter", function() plus.t:SetTextColor(Unpack(C_GOLD)) end)
    plus:SetScript("OnLeave", function() plus.t:SetTextColor(Unpack(C_TEXT)) end)
    plus:SetScript("OnClick", function()
        ns.PlaySound(1)
        OpenWeightDialog("new")
    end)
    BG.wBtns = {}
    local prev = nil
    for i = 1, 1 + 4 + W_SCHEME_MAX do
        local bt = MakeWeightIcon(spop, 18)
        if i == 1 then
            bt:SetPoint("RIGHT", plus, "LEFT", -4, 0)
        else
            bt:SetPoint("RIGHT", prev, "LEFT", -4, 0)
        end
        bt:RegisterForClicks("LeftButtonUp", "RightButtonUp")
        bt:SetScript("OnClick", function(self, button)
            local dir = SPEC_DIR[BG.cls] or {}
            local sr = dir[i - 1]
            if i == 1 then
                if button == "RightButton" then return end
                ns.PlaySound(1)
                if BG.wRole ~= nil or BG.spec == "tank" then
                    BG.wRole = nil
                    SaveWeightPrefs()
                    BumpWeights()
                    BG.SelectSpec("pve")
                end
                return
            end
            if sr then
                if button == "RightButton" then return end
                ns.PlaySound(1)
                if sr.role == "tank" then
                    BG.wRole = nil
                    SaveWeightPrefs()
                    BG.SelectSpec("tank")
                else
                    if BG.spec == "tank" then BG.SelectSpec("pve") end
                    if BG.wRole ~= sr.key then
                        BG.wRole = sr.key
                        SaveWeightPrefs()
                        BumpWeights()
                        BG.SyncSettingPop()
                        BG.RequestRender()
                    end
                end
                return
            end
            local sidx = i - 1 - #dir
            if button == "RightButton" then
                WeightSchemeMenu(self, sidx)
                return
            end
            ns.PlaySound(1)
            local target = sidx
            if BG.wActive == target then target = nil end
            BG.wActive = target
            BumpWeights()
            SaveWeightPrefs()
            BG.SyncSettingPop()
            BG.RequestRender()
        end)
        bt:SetScript("OnEnter", function(self)
            local dir = SPEC_DIR[BG.cls] or {}
            local sr = dir[i - 1]
            local nm
            if i == 1 then
                nm = L["默认（自动探测）"]
            elseif sr then
                nm = L[sr.label]
            else
                local sch = BG.wSchemes and BG.wSchemes[i - 1 - #dir] or nil
                if not sch then return end
                nm = sch.name or ""
            end
            GameTooltip:SetOwner(self, "ANCHOR_BOTTOM")
            GameTooltip:ClearLines()
            GameTooltip:AddLine(nm, 1, 1, 1, true)
            GameTooltip:AddLine(L["左键应用 · 右键菜单"], 0.7, 0.75, 0.8, true)
            GameTooltip:Show()
        end)
        bt:SetScript("OnLeave", function() GameTooltip:Hide() end)
        bt:Hide()
        BG.wBtns[i] = bt
        prev = bt
    end

    local wscroll = CreateFrame("ScrollFrame", nil, spop)
    wscroll:EnableMouseWheel(true)
    local wchild = CreateFrame("Frame", nil, wscroll)
    wchild:SetSize(204, #W_KEYS * 16 + 12)
    wscroll:SetScrollChild(wchild)
    wscroll:SetPoint("TOPLEFT", spop, "TOPLEFT", 8, -66)
    wscroll:SetPoint("BOTTOMRIGHT", spop, "BOTTOMRIGHT", -10, 34)
    wscroll:SetScript("OnMouseWheel", function(_, delta)
        if DG.WheelScroll then DG.WheelScroll(wscroll, wchild, delta) end
    end)
    BG.wBar = BuildVBar(wscroll, wchild)

    BG.wRows = {}
    for i, wk in ipairs(W_KEYS) do
        local y = -6 - (i - 1) * 16
        local lab = MakeFS(wchild, 14, C_TEXT, "LEFT")
        lab:SetPoint("TOPLEFT", wchild, "TOPLEFT", 0, y)
        lab:SetWidth(140)
        lab:SetWordWrap(false)
        lab:SetText(wk[2])
        local eb = ns.CreateEditBox and ns.CreateEditBox(wchild, 50) or nil
        if eb then
            eb:SetSize(50, 14)
            eb:SetPoint("TOPRIGHT", wchild, "TOPRIGHT", -5, y + 1)
        end
        local ro = MakeFS(wchild, 14, C_DIM, "RIGHT")
        ro:SetPoint("TOPRIGHT", wchild, "TOPRIGHT", -5, y + 2)
        ro:SetWordWrap(false)
        local row = { key = wk[1], lab = lab, eb = eb, ro = ro }
        local function WTone(txt)
            local sch = BG.wActive and BG.wSchemes and BG.wSchemes[BG.wActive] or nil
            if not sch then return end
            local v = tonumber(string.match(txt or "", "^%s*(%d+%.?%d*)%s*$"))
            if v then
                if v < 0 then v = 0 elseif v > 20 then v = 20 end
                sch.w[row.key] = v
                BumpWeights()
                SaveWeightPrefs()
                BG.RequestRender()
            end
            if eb then eb:SetText(format("%.2f", sch.w[row.key] or 0)) end
        end
        if eb then
            eb:SetScript("OnEnterPressed", function(self) WTone(self:GetText()); self:ClearFocus() end)
            eb:SetScript("OnEditFocusLost", function(self)
                if self.RestoreBorder then self:RestoreBorder() end
                WTone(self:GetText())
            end)
            eb:SetScript("OnEscapePressed", function(self)
                local sch2 = BG.wActive and BG.wSchemes and BG.wSchemes[BG.wActive] or nil
                local base = SpecWeights(BG.cls, BG.spec)
                local v = (sch2 and sch2.w[row.key]) or base[row.key] or 0
                self:SetText(format("%.2f", v))
                self:ClearFocus()
            end)
        end
        BG.wRows[i] = row
    end

    BG.wHint = MakeFS(spop, 14, C_DIM, "LEFT")
    BG.wHint:SetPoint("BOTTOMLEFT", spop, "BOTTOMLEFT", 8, 12)
    BG.wHint:SetWordWrap(false)
    BG.wHint:SetText(L["默认只读，添加方案后可编辑"])
end

local function BuildEnchCard(parent)
    local x, w = 8, 309
    local baseLv = (parent.GetFrameLevel and type(parent:GetFrameLevel()) == "number")
        and parent:GetFrameLevel() or 0
    local clip = CreateFrame("Frame", nil, parent)
    clip:SetPoint("TOPLEFT", parent, "TOPLEFT", x, 0)
    clip:SetPoint("BOTTOMRIGHT", parent, "TOPLEFT", x + w - 8, -(8 + 24 + 8))
    clip:SetFrameLevel(baseLv + 6)
    if ns.hui and ns.hui.GlassPlate then
        ns.hui.GlassPlate(clip, ns.hui.layer.L1, "top")
    else
        Cardify(clip, 0.05, 0.12)
    end
    BG.enchClip = clip
    local hdr = CreateFrame("Frame", nil, parent)
    hdr:SetAllPoints(parent)
    hdr:SetFrameLevel(baseLv + 10)
    BG.enchHead = MakeFS(hdr, 16, C_WHITE, "LEFT")
    BG.enchHead:SetPoint("TOPLEFT", hdr, "TOPLEFT", x, -8)
    BG.enchHead:SetText(L["附魔"])
    local eb2 = ns.CreateEditBox and ns.CreateEditBox(hdr, 150) or CreateFrame("EditBox", nil, hdr)
    eb2:SetSize(150, 22)
    eb2:SetPoint("TOPRIGHT", hdr, "TOPRIGHT", -8, -8)
    eb2:SetAutoFocus(false)
    eb2:SetMaxLetters(30)
    eb2:SetScript("OnEscapePressed", function(self) self:ClearFocus() end)
    local ph2 = MakeFS(eb2, 14, C_DIM, "LEFT")
    ph2:SetPoint("LEFT", eb2, "LEFT", 8, 0)
    ph2:SetText(L["搜索附魔…"])
    eb2:SetScript("OnTextChanged", function(self)
        BG.enchSearch = string.lower(self:GetText() or "")
        ph2:SetShown(self:GetText() == "")
        BG.RequestRender()
    end)
    local fbtn = NewButton(hdr, L["筛选"], 48, 24, 14)
    fbtn:SetPoint("RIGHT", eb2, "LEFT", -8, 0)
    fbtn.lbl = fbtn:GetFontString()
    BG.enchFilterBtn = fbtn
    fbtn:SetScript("OnClick", function(self)
        local defs = {
            { key = nil, label = L["全部"] or "全部" },
            { key = "main", label = L["主属性"] or "主属性" },
            { key = "sta", label = L["耐力"] or "耐力" },
            { key = "pow", label = L["强度"] or "强度" },
            { key = "res", label = L["抗性"] or "抗性" },
            { key = "proc", label = L["触发"] or "触发" },
            { key = "misc", label = L["其他"] or "其他" },
        }
        local items = {}
        for _, d in ipairs(defs) do
            items[#items + 1] = {
                text = (BG.enchFilter == d.key and "● " or "") .. tostring(d.label),
                func = function()
                    BG.enchFilter = d.key
                    BG.RequestRender()
                end,
            }
        end
        if ns.hui and ns.hui.ShowMenu then
            ns.hui.ShowMenu(items, { owner = self })
        end
    end)
    local escroll = CreateFrame("ScrollFrame", nil, parent)
    escroll:EnableMouseWheel(true)
    local echild = CreateFrame("Frame", nil, escroll)
    echild:SetSize(w - 8, 10)
    escroll:SetScrollChild(echild)
    escroll:SetPoint("TOPLEFT", parent, "TOPLEFT", x, -(8 + 24 + 8))
    escroll:SetPoint("BOTTOMRIGHT", parent, "BOTTOMRIGHT", -x, 8)
    escroll:SetScript("OnMouseWheel", function(_, delta)
        DG.WheelScroll(escroll, echild, delta)
        CullEnchRows()
    end)
    escroll:SetScript("OnVerticalScroll", function() CullEnchRows() end)
    BG.enchScroll, BG.enchChild = escroll, echild
    BG.enchBar = BuildVBar(escroll, echild, CullEnchRows)
    BG.enchRows = {}
    for i = 1, 40 do
        local r = CreateFrame("Button", nil, echild, BT)
        r:SetHeight(36)
        r:RegisterForClicks("LeftButtonUp")
        local hfx = ns.hui and ns.hui.HuiCardFX or nil
        if not (hfx and hfx(r, 6, 2)) then Cardify(r) end
        r.name = MakeFS(r, 14, C_TEXT, "LEFT")
        r.name:SetPoint("TOPLEFT", r, "TOPLEFT", 8, -3)
        r.name:SetWordWrap(false)
        r.lvl = MakeFS(r, 14, C_GREY, "RIGHT")
        r.lvl:SetPoint("TOPRIGHT", r, "TOPRIGHT", -8, -4)
        r.lvl:SetWordWrap(false)
        r.note = MakeFS(r, 14, C_GREY, "LEFT")
        r.note:SetPoint("TOPLEFT", r, "TOPLEFT", 8, -21)
        r.note:SetWidth(230)
        r.note:SetWordWrap(false)
        r:SetScript("OnEnter", function(self)
            if self.__huiCard then ns.hui.HuiCardState(self, "hover") end
            if self.__ench then
                if self.__ench.item then
                    ItemTip(self, self.__ench.item)
                else
                    EnchTip(self, self.__ench)
                end
            end
        end)
        r:SetScript("OnLeave", function(self)
            if self.__huiCard then ns.hui.HuiCardState(self, self.__sel and "hover" or "norm") end
            TipOff()
        end)
        r:SetScript("OnClick", function(self)
            local e = self.__ench
            if not e or not BG.sel then return end
            local dk = DataKey(SpecRec(), BG.sel)
            local tok = EnchToken(e)
            if CurEnch(SpecRec(), dk) == tok then
                BG.ench[dk] = nil
            else
                BG.ench[dk] = tok
            end
            BG.RequestRender()
            ns.PlaySound(1)
        end)
        BG.enchRows[i] = r
        if i % 10 == 0 then coroutine.yield() end
    end

end

function BG.Build(page)
    if BG.built or BG.building then return end
    BG.building = true
    BG.__buildTag = 2
    ns.OpenPerf.Begin("BIS")
    ns.PhasedStart(25, coroutine.create(function()
    EnsureBIS()
    if not BG.vol then BG.vol = DefaultVol() end
    MigratePlans()
    MigrateTSpec()
    LoadFilterPrefs()
    LoadWeightPrefs()
    if not BG.__clsPicked then
        local slug = PlayerClassSlug()
        if slug and slug ~= BG.cls then
            BG.cls = slug
            BG.cur = {}
            BG.ench = {}
            BG.usingPlan = nil
            BG.autoPlan = nil
            BG.sel = nil
            BG.pkey = nil
            BG.tspec = nil
            BG.spec = "pve"
        end
        if BG.wRole and not RoleOfKey(BG.cls, BG.wRole) then
            BG.wRole = nil
            SaveWeightPrefs()
            BumpWeights()
        end
    end
    coroutine.yield()
    local py = 8
    BG.py = py
    BG.page = page
    coroutine.yield()
    BuildPanels(page)
    coroutine.yield()
    local dollTop = BuildSpecRow(BG.panels[1], 8)
    local dollBotLocal = BuildDoll(BG.panels[1], dollTop)
    local pb = PAGE_INSET
    coroutine.yield()
    BuildMid(BG.panels[2], BG.panels[3])
    coroutine.yield()
    BuildBrowser(BG.panels[4])
    coroutine.yield()
    BuildEnchCard(BG.panels[5])
    coroutine.yield()

    BG.panels[1]:SetPoint("TOPLEFT", page, "TOPLEFT", PAGE_INSET, -py)
    BG.panels[1]:SetPoint("BOTTOMRIGHT", page, "BOTTOMLEFT", 391, pb)
    BG.panels[2]:SetPoint("TOPLEFT", page, "TOPLEFT", 399, -py)
    BG.panels[2]:SetPoint("BOTTOMRIGHT", page, "TOPLEFT", 623, -(py + 228))
    BG.panels[3]:SetPoint("TOPLEFT", page, "TOPLEFT", 399, -(py + 236))
    BG.panels[3]:SetPoint("BOTTOMRIGHT", page, "BOTTOMLEFT", 623, pb)
    BG.panels[4]:SetPoint("TOPLEFT", page, "TOPLEFT", 631, -py)
    BG.panels[4]:SetPoint("BOTTOMRIGHT", page, "BOTTOMLEFT", 948, pb + ENCH_CARD_H + 8)
    BG.panels[5]:SetPoint("TOPLEFT", page, "BOTTOMLEFT", 631, pb + ENCH_CARD_H)
    BG.panels[5]:SetPoint("BOTTOMRIGHT", page, "BOTTOMLEFT", 948, pb)

    BG.built = true
    BG.building = false
    BG.needNames = true
    BG.__wantDefault = true
    if C_Timer and C_Timer.After then
        C_Timer.After(0, function()
            if BG.built and BG.__wantDefault then
                BG.__wantDefault = nil
                BG.UseAutoPlan("known")
            end
        end)
    end
    ns.EvtPool = ns.EvtPool or {}
    if not ns.EvtPool.bisTal then
        local ev = CreateFrame("Frame")
        ns.EvtPool.bisTal = ev
        ev:RegisterEvent("CHARACTER_POINTS_CHANGED")
        ev:RegisterEvent("PLAYER_LEVEL_UP")
        ev:SetScript("OnEvent", function(_, e)
            if e == "PLAYER_LEVEL_UP" then
                if BG.built then
                    if BG.usingPlan == nil and BG.autoPlan then
                        BG.UseAutoPlan(BG.autoPlan)
                    else
                        BG.RequestRender()
                    end
                end
                return
            end
            __tprofDirty = true
            if BG.built and not BG.wActive and not BG.wRole then
                BumpWeights()
                BG.RequestRender()
            end
        end)
    end
    BG.ScheduleSweep()
    BG.Render()
    ns.OpenPerf.Mark("首绘")
    end))
end

local slotById, slotByIdKey
local function CatalogSlotOf(id)
    local cat = EnsureCatalog()
    if type(cat) ~= "table" then return nil end
    local key = tostring(BG.cls or "") .. ":" .. tostring(#cat)
    if slotByIdKey ~= key or not slotById then
        local map = {}
        for i = 1, #cat do
            local r = cat[i]
            local rid = type(r) == "table" and (r.id or r[1]) or nil
            if type(rid) == "number" then map[rid] = r.s or r[3] end
        end
        slotById, slotByIdKey = map, key
    end
    return slotById[id]
end

local INV_SLOT_NAME = {
    back = "BackSlot", chest = "ChestSlot", feet = "FeetSlot",
    finger = "Finger0Slot", finger2 = "Finger1Slot",
    hands = "HandsSlot", head = "HeadSlot", held = "SecondaryHandSlot",
    legs = "LegsSlot", ["main-hand"] = "MainHandSlot", neck = "NeckSlot",
    ["off-hand"] = "SecondaryHandSlot", ranged = "RangedSlot", relic = "RangedSlot",
    shield = "SecondaryHandSlot", shoulder = "ShoulderSlot",
    trinket = "Trinket0Slot", trinket2 = "Trinket1Slot",
    ["two-hand"] = "MainHandSlot", waist = "WaistSlot", wrist = "WristSlot",
}
local PAIR_SLOT = { finger = "finger2", finger2 = "finger", trinket = "trinket2", trinket2 = "trinket" }

local function InvIdOf(name)
    if type(name) ~= "string" or type(GetInventorySlotInfo) ~= "function" then return nil end
    local ok, idx = pcall(GetInventorySlotInfo, name)
    if not ok or type(idx) ~= "number" then return nil end
    local ok2, eid = pcall(GetInventoryItemID, "player", idx)
    if ok2 and type(eid) == "number" and eid > 0 then return eid end
    return nil
end

local function EquippedInSlot(slot, exceptId)
    if type(slot) ~= "string" then return nil end
    local eid = InvIdOf(INV_SLOT_NAME[slot])
    if eid and eid ~= exceptId then return eid end
    local pair = PAIR_SLOT[slot]
    if pair then
        local pid = InvIdOf(INV_SLOT_NAME[pair])
        if pid and pid ~= exceptId then return pid end
    end
    return nil
end

local INVTYPE_SLOT = {
    INVTYPE_BACK = "back", INVTYPE_CLOAK = "back", INVTYPE_CHEST = "chest", INVTYPE_ROBE = "chest",
    INVTYPE_FEET = "feet", INVTYPE_FINGER = "finger", INVTYPE_HAND = "hands",
    INVTYPE_HEAD = "head", INVTYPE_LEGS = "legs", INVTYPE_NECK = "neck",
    INVTYPE_RANGED = "ranged", INVTYPE_RANGEDRIGHT = "ranged",
    INVTYPE_SHOULDER = "shoulder", INVTYPE_TRINKET = "trinket",
    INVTYPE_2HWEAPON = "two-hand", INVTYPE_WAIST = "waist", INVTYPE_WRIST = "wrist",
    INVTYPE_WEAPON = "main-hand", INVTYPE_WEAPONMAINHAND = "main-hand",
    INVTYPE_WEAPONOFFHAND = "off-hand", INVTYPE_SHIELD = "shield",
    INVTYPE_HOLDABLE = "held", INVTYPE_RELIC = "relic",
}

local CAT_SLOT_NORM = {
    ["main hand"] = "main-hand", ["off hand"] = "off-hand",
    ["held in off-hand"] = "held", ["one-hand"] = "main-hand",
    ["thrown"] = "ranged",
}

local function SlotOfAny(id)
    local s = CatalogSlotOf(id)
    if type(s) == "string" then
        s = string.lower(s)
        return CAT_SLOT_NORM[s] or s
    end
    local fn = GetItemInfoInstant or (C_Item and C_Item.GetItemInfoInstant)
    if type(fn) ~= "function" then return nil end
    local ok, _, _, _, eq = pcall(fn, id)
    if ok and type(eq) == "string" then return INVTYPE_SLOT[eq] end
    return nil
end

local function ScoreVsBis(id)
    if type(id) ~= "number" then return nil end
    local slot = SlotOfAny(id)
    if type(slot) ~= "string" then return nil end
    local baseId = EquippedInSlot(slot, id)
    if type(baseId) ~= "number" or baseId == id then return nil end
    local w = EffWeights()
    local my = ItemScore(id, w)
    if not my or my <= 0 then
        local DG = ns.DungeonModule
        if DG and DG.RequestItem then pcall(DG.RequestItem, id) end
        return nil
    end
    local bs = ItemScore(baseId, w)
    if not (statSeen[baseId] or dpsCache[baseId]) then
        local DG = ns.DungeonModule
        if DG and DG.RequestItem then pcall(DG.RequestItem, baseId) end
        return nil
    end
    local delta = my - (type(bs) == "number" and bs or 0)
    local pct = nil
    if type(bs) == "number" and bs > 0 then
        local p = delta / bs * 100
        pct = p < 0 and math.ceil(p - 0.5) or math.floor(p + 0.5)
    end
    return delta, pct
end

BG.ScoreVsBis = ScoreVsBis
