local _, ns = ...

local D = {}
ns.LootFilterData = D

D.CLASS_WEAPON = 2
D.CLASS_ARMOR = 4
D.CLASS_QUEST = 12
D.CLASS_QUEST_ALT = 9
D.DEFAULT_ICON = "Interface\\Icons\\INV_Misc_QuestionMark"

D.FLAG_CLASS = "过滤职业限定"
D.FLAG_BNET = "忽略战网绑定"
D.FLAG_TANK = "过滤坦克"

D.FlagLabel = {
    [D.FLAG_CLASS] = "职业限定",
    [D.FLAG_BNET]  = "保留战网",
    [D.FLAG_TANK]  = "坦克装备",
}

D.ShuXingLabel = {
    ["特定法术强度"] = "法术伤害",
}

D.WeaponName = {
    [0] = "单手斧", [1] = "双手斧", [2] = "弓", [3] = "枪",
    [4] = "单手锤", [5] = "双手锤", [6] = "长柄武器", [7] = "单手剑",
    [8] = "双手剑", [9] = "战刃", [10] = "法杖", [11] = "其他武器",
    [13] = "拳套", [14] = "杂项武器", [15] = "匕首", [16] = "投掷武器",
    [17] = "长矛", [18] = "弩", [19] = "魔杖", [20] = "钓鱼竿",
}
D.WeaponOrder = { 0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 13, 15, 16, 18, 19 }

D.ArmorName = {
    [0] = "副手物品", [1] = "布甲", [2] = "皮甲", [3] = "锁甲",
    [4] = "板甲", [6] = "盾牌", [7] = "圣契",
    [8] = "神像", [9] = "图腾", [10] = "魔印",
}
D.ArmorOrder = { 0, 1, 2, 3, 4, 6, 7, 8, 9, 10 }

D.WeaponIdByName = {}
for _, sid in ipairs(D.WeaponOrder) do
    local nm = D.WeaponName[sid]
    if nm then D.WeaponIdByName[nm] = sid end
end
D.ArmorIdByName = {}
for _, sid in ipairs(D.ArmorOrder) do
    local nm = D.ArmorName[sid]
    if nm then D.ArmorIdByName[nm] = sid end
end

D.WeaponSet, D.ArmorSet = {}, {}
for _, sid in ipairs(D.WeaponOrder) do D.WeaponSet[sid] = true end
for _, sid in ipairs(D.ArmorOrder)  do D.ArmorSet[sid] = true end

D.ClassUsable = {
    WARRIOR = {
        weapon = { "匕首", "拳套", "单手斧", "单手锤", "单手剑", "双手斧", "双手锤", "双手剑",
                   "长柄武器", "法杖", "弓", "弩", "枪", "投掷武器" },
        armor = { "皮甲", "锁甲", "板甲", "盾牌" },
    },
    PALADIN = {
        weapon = { "单手斧", "单手锤", "单手剑", "双手斧", "双手锤", "双手剑", "长柄武器" },
        armor = { "布甲", "皮甲", "锁甲", "板甲", "盾牌", "副手物品", "圣契" },
    },
    DEATHKNIGHT = {
        weapon = { "单手斧", "单手锤", "单手剑", "双手斧", "双手锤", "双手剑", "长柄武器" },
        armor = { "皮甲", "锁甲", "板甲", "魔印" },
    },
    SHAMAN = {
        weapon = { "匕首", "拳套", "单手斧", "单手锤", "双手斧", "双手锤", "法杖" },
        armor = { "布甲", "皮甲", "锁甲", "盾牌", "副手物品", "图腾" },
    },
    HUNTER = {
        weapon = { "匕首", "拳套", "单手斧", "单手剑", "双手斧", "双手剑", "长柄武器", "法杖",
                   "弓", "弩", "枪" },
        armor = { "皮甲", "锁甲" },
    },
    ROGUE = {
        weapon = { "匕首", "拳套", "单手斧", "单手锤", "单手剑", "弓", "弩", "枪", "投掷武器" },
        armor = { "皮甲" },
    },
    DRUID = {
        weapon = { "匕首", "拳套", "单手锤", "双手锤", "长柄武器", "法杖" },
        armor = { "布甲", "皮甲", "副手物品", "神像" },
    },
    MONK = {
        weapon = { "拳套", "单手斧", "单手锤", "单手剑", "长柄武器", "法杖" },
        armor = { "皮甲", "副手物品" },
    },
    MAGE = {
        weapon = { "匕首", "单手剑", "法杖", "魔杖" },
        armor = { "布甲", "副手物品" },
    },
    WARLOCK = {
        weapon = { "匕首", "单手剑", "法杖", "魔杖" },
        armor = { "布甲", "副手物品" },
    },
    PRIEST = {
        weapon = { "匕首", "单手锤", "法杖", "魔杖" },
        armor = { "布甲", "副手物品" },
    },
}

local MAGIC = "([%-%.%(%)%[%]%*%+%?%^%$%%])"
function D.toPattern(s)
    if type(s) ~= "string" or s == "" then return nil end
    local esc = s:gsub(MAGIC, "%%%1")
    esc = esc:gsub("%s+", "(.+)")
    return esc
end

local function pick(...)
    for i = 1, select("#", ...) do
        local v = select(i, ...)
        if type(v) == "string" and v ~= "" then return v end
    end
    return nil
end

local function num2blank(s)
    if type(s) ~= "string" or s == "" then return nil end
    s = s:gsub("%%%d+%$d", " ")
    s = s:gsub("%%d", " ")
    return s
end

local function shuxingPat(globalName, fallback)
    return D.toPattern(pick(num2blank(_G[globalName]), fallback))
end

D.ShuXing = {}
D.ShuXingOrder = {}
if ns.IsForever then
    local specs = {
        { "力量", "ITEM_MOD_STRENGTH_SHORT", "力量" },
        { "敏捷", "ITEM_MOD_AGILITY_SHORT", "敏捷" },
        { "智力", "ITEM_MOD_INTELLECT_SHORT", "智力" },
        { "精神", "ITEM_MOD_SPIRIT_SHORT", "精神" },
        { "5回法力值", "TOOLTIP_ITEM_STAT_MANA_REGEN_INCREASE", "每5秒" },
        { "防御", "STAT_CATEGORY_DEFENSE", "防御" },
        { "招架", "STAT_PARRY", "招架" },
        { "躲闪", "STAT_DODGE", "躲闪" },
        { "格挡", "ITEM_MOD_BLOCK_VALUE_SHORT", "格挡值" },
        { "攻击强度", "ITEM_MOD_ATTACK_POWER_SHORT", "攻击强度" },
        { "武器技能", "COMBAT_RATING_NAME1", "武器技能" },
        { "击中时可能", "ITEM_SPELL_TRIGGER_ONPROC", "击中时可能" },
        { "命中", "TOOLTIP_ITEM_STAT_HIT_PERCENT_INCREASE", "命中" },
        { "特定法术强度", nil, "法术和效果所造成的伤害" },
        { "法术强度", "TOOLTIP_ITEM_STAT_SPELL_POWER_INCREASE", "所有法术和魔法效果所造成的伤害和治疗效果" },
        { "治疗强度", "TOOLTIP_ITEM_STAT_SPELL_HEALING_INCREASE_DAMAGE_INCREASE", "法术所造成的治疗效果" },
        { "移动速度", nil, "移动速度" },
    }
    for _, e in ipairs(specs) do
        local pat = shuxingPat(e[2], e[3])
        if pat then D.ShuXing[e[1]] = pat; D.ShuXingOrder[#D.ShuXingOrder + 1] = e[1] end
    end
else
    local specs = {
        { "力量", { _G["ITEM_MOD_STRENGTH_SHORT"], _G["STAT_STRENGTH"], "力量" } },
        { "敏捷", { _G["ITEM_MOD_AGILITY_SHORT"], _G["STAT_AGILITY"], "敏捷" } },
        { "智力", { _G["ITEM_MOD_INTELLECT_SHORT"], _G["STAT_INTELLECT"], "智力" } },
        { "精神", { _G["ITEM_MOD_SPIRIT_SHORT"], _G["STAT_SPIRIT"], "精神" } },
        { "耐力", { _G["ITEM_MOD_STAMINA_SHORT"], _G["STAT_STAMINA"], "耐力" } },
        { "急速", { _G["STAT_HASTE"], _G["ITEM_MOD_HASTE_RATING_SHORT"], "急速" } },
        { "暴击", { _G["STAT_CRITICAL_STRIKE"], _G["ITEM_MOD_CRIT_RATING_SHORT"], "暴击" } },
        { "精通", { _G["STAT_MASTERY"], _G["ITEM_MOD_MASTERY_RATING_SHORT"], "精通" } },
        { "全能", { _G["STAT_VERSATILITY"], "全能" } },
        { "命中", { _G["ITEM_MOD_HIT_RATING_SHORT"], _G["STAT_HIT"], "命中" } },
        { "精准", { _G["ITEM_MOD_EXPERTISE_RATING_SHORT"], "精准" } },
        { "招架", { _G["ITEM_MOD_PARRY_RATING_SHORT"], _G["STAT_PARRY"], "招架" } },
        { "躲闪", { _G["ITEM_MOD_DODGE_RATING_SHORT"], _G["STAT_DODGE"], "躲闪" } },
        { "格挡", { _G["ITEM_MOD_BLOCK_RATING_SHORT"], _G["STAT_BLOCK"], "格挡" } },
        { "护甲穿透", { _G["ITEM_MOD_ARMOR_PENETRATION_RATING_SHORT"], "护甲穿透" } },
    }
    for _, e in ipairs(specs) do
        local pat = D.toPattern(pick(unpack(e[2])))
        if pat then D.ShuXing[e[1]] = pat; D.ShuXingOrder[#D.ShuXingOrder + 1] = e[1] end
    end
    local extra = {
        { "攻击强度", "ITEM_MOD_ATTACK_POWER_SHORT", "攻击强度" },
        { "防御", "STAT_CATEGORY_DEFENSE", "防御" },
        { "武器技能", "COMBAT_RATING_NAME1", "武器技能" },
        { "击中时可能", "ITEM_SPELL_TRIGGER_ONPROC", "击中时可能" },
        { "5回法力值", "TOOLTIP_ITEM_STAT_MANA_REGEN_INCREASE", "每5秒" },
        { "法术强度", "TOOLTIP_ITEM_STAT_SPELL_POWER_INCREASE", "所有法术和魔法效果所造成的伤害和治疗效果" },
        { "治疗强度", "TOOLTIP_ITEM_STAT_SPELL_HEALING_INCREASE_DAMAGE_INCREASE", "法术所造成的治疗效果" },
        { "特定法术强度", nil, "法术和效果所造成的伤害" },
        { "移动速度", nil, "移动速度" },
    }
    for _, e in ipairs(extra) do
        local pat = shuxingPat(e[2], e[3])
        if pat then D.ShuXing[e[1]] = pat; D.ShuXingOrder[#D.ShuXingOrder + 1] = e[1] end
    end
end

D.Nothave = {}
do
    local proc = pick(_G["ITEM_SPELL_TRIGGER_ONPROC"], "击中时可能")
    if proc then
        for _, nm in ipairs({ "命中", "特定法术强度", "法术强度", "治疗强度" }) do
            D.Nothave[nm] = { proc }
        end
    end
end

D.TankKeywords = {}
do
    local cand = {
        { _G["ITEM_MOD_DEFENSE_SKILL_RATING_SHORT"], _G["STAT_DEFENSE"], "防御" },
        { _G["ITEM_MOD_PARRY_RATING_SHORT"], _G["STAT_PARRY"], "招架" },
        { _G["ITEM_MOD_DODGE_RATING_SHORT"], _G["STAT_DODGE"], "躲闪" },
        { _G["ITEM_MOD_BLOCK_RATING_SHORT"], _G["STAT_BLOCK"], "格挡" },
        { _G["ITEM_MOD_BLOCK_VALUE_SHORT"], "盾牌格挡值" },
        { _G["ITEM_MOD_EXTRA_ARMOR_SHORT"], "额外护甲" },
    }
    for _, e in ipairs(cand) do
        local pat = D.toPattern(pick(unpack(e)))
        if pat then D.TankKeywords[#D.TankKeywords + 1] = pat end
    end
end

D.ClassPrefix = pick(_G["ITEM_CLASSES"], "职业：", "职业:", _G["CLASSES"])
D.BnetBound = {}
do
    local b = pick(_G["ITEM_BNETACCOUNTBOUND"], _G["BNET_ACCOUNT_BOUND"], "战网绑定")
    if b then D.BnetBound[#D.BnetBound + 1] = b end
    D.BnetBound[#D.BnetBound + 1] = "帐号绑定"
    D.BnetBound[#D.BnetBound + 1] = "账号绑定"
end

D.ExcludeLine = {}
do
    local function add(s)
        if type(s) == "string" and s ~= "" then D.ExcludeLine[#D.ExcludeLine + 1] = s end
    end
    add(pick(_G["ITEM_SET_BONUS"]))
    add(pick(_G["ITEM_SOCKET_BONUS"]))
    add("套装")
    add("镶孔奖励")
    add("猫熊形态攻击强度")
    add("Feral Attack Power")
    add(pick(_G["ITEM_UNIQUE"]))
    add("装备唯一")
end

local ICON = {
    WAR_ARMS  = "Interface\\Icons\\Ability_Warrior_Charge",
    WAR_FURY  = "Interface\\Icons\\Ability_Warrior_BattleShout",
    WAR_PROT  = "Interface\\Icons\\Ability_Warrior_DefensiveStance",
    PAL_HOLY  = "Interface\\Icons\\Spell_Holy_DevotionAura",
    PAL_RET   = "Interface\\Icons\\Spell_Holy_HolyBolt",
    PAL_PROT  = "Interface\\Icons\\Spell_Holy_SealOfProtection",
    DK_BLOOD  = "Interface\\Icons\\Spell_DeathKnight_BloodPresence",
    DK_FROST  = "Interface\\Icons\\Spell_DeathKnight_FrostPresence",
    DK_UNHOLY = "Interface\\Icons\\Spell_DeathKnight_UnholyPresence",

    HUN_CLASS = "Interface\\Icons\\Ability_Hunter_BeastCall",
    HUN_BM    = "Interface\\Icons\\Ability_Hunter_BeastTaming",
    HUN_MM    = "Interface\\Icons\\Ability_Marksmanship",
    HUN_SV    = "Interface\\Icons\\Ability_Hunter_Camouflage",
    SHA_CLASS = "Interface\\Icons\\Spell_Nature_LightningBolt",
    SHA_ENH   = "Interface\\Icons\\Spell_Nature_LightningShield",
    SHA_ELE   = "Interface\\Icons\\Spell_Nature_Lightning",
    SHA_RES   = "Interface\\Icons\\Spell_Nature_MagicImmunity",
    DRU_CLASS = "Interface\\Icons\\Spell_Nature_Regrowth",
    DRU_BEAR  = "Interface\\Icons\\Ability_Racial_BearForm",
    DRU_CAT   = "Interface\\Icons\\Ability_Druid_CatForm",
    DRU_BOOM  = "Interface\\Icons\\Spell_Nature_Starfall",
    DRU_RES   = "Interface\\Icons\\Spell_Nature_HealingTouch",
    ROG_CLASS = "Interface\\Icons\\Ability_Stealth",
    MNK_CLASS = "Interface\\Icons\\Ability_Monk_RisingSunKick",
    MNK_BREW  = "Interface\\Icons\\Spell_Monk_Brewmaster_Spec",
    MNK_WW    = "Interface\\Icons\\Spell_Monk_Windwalker_Spec",
    MNK_MW    = "Interface\\Icons\\Spell_Monk_Mistweaver_Spec",
    PRI_CLASS = "Interface\\Icons\\Spell_Holy_WordFortitude",
    PRI_SHA   = "Interface\\Icons\\Spell_Shadow_ShadowWordPain",
    PRI_DISC  = "Interface\\Icons\\Spell_Holy_PowerWordShield",
    PRI_HOLY  = "Interface\\Icons\\Spell_Holy_GuardianSpirit",
    MAG_CLASS = "Interface\\Icons\\Spell_Frost_Frostbolt02",
    WLK_CLASS = "Interface\\Icons\\Spell_Shadow_ShadowBolt",
}
D.PresetIcon = ICON

local ROLE = {}

local function merge(...)
    local seen, out = {}, {}
    for i = 1, select("#", ...) do
        local t = select(i, ...)
        if type(t) == "table" then
            for _, v in ipairs(t) do
                if not seen[v] then seen[v] = true; out[#out + 1] = v end
            end
        end
    end
    return out
end

ROLE.all = { "精通", "爆击", "急速", "全能" }
ROLE.t0  = merge(ROLE.all, { "命中", "防御", "躲闪", "攻击强度", "精准", "护甲穿透",
                             "近战攻击", "物理命中", "物理爆击", "击中时可能" })
ROLE.t1  = merge(ROLE.t0, { "力量", "敏捷", "招架" })
ROLE.t2  = merge(ROLE.t0, { "力量", "敏捷", "招架", "格挡", "武器技能" })
ROLE.t3  = merge(ROLE.t0, { "力量", "敏捷" })
ROLE.t4  = merge(ROLE.t0, { "敏捷", "招架" })
ROLE.t5  = merge(ROLE.t2, { "法术强度" })

ROLE.dps0 = merge(ROLE.all, { "命中", "攻击强度", "精准", "护甲穿透", "近战攻击",
                              "物理命中", "物理爆击", "武器技能", "击中时可能" })
ROLE.dps1 = merge(ROLE.dps0, { "力量", "敏捷", "智力" })
ROLE.dps2 = merge(ROLE.dps0, { "力量", "敏捷" })
ROLE.dps3 = merge(ROLE.dps0, { "力量", "敏捷", "智力", "法术强度", "法术命中", "法术爆击" })
ROLE.dps4 = merge(ROLE.dps1, { "法术强度" })

ROLE.lr0 = merge(ROLE.all, { "敏捷", "命中", "攻击强度", "护甲穿透", "远程攻击",
                             "物理命中", "物理爆击", "武器技能", "击中时可能" })
ROLE.lr1 = merge(ROLE.lr0, { "智力" })

ROLE.fx0 = merge(ROLE.all, { "智力", "命中", "法术强度", "法术伤害强度", "法术命中",
                             "法术爆击", "特定法术强度" })
ROLE.fx1 = merge(ROLE.fx0, { "精神" })
ROLE.fx2 = merge(ROLE.fx0, { "精神" })

ROLE.n0 = merge(ROLE.all, { "智力", "5回法力值", "法术强度", "治疗强度", "法术爆击" })
ROLE.n1 = merge(ROLE.n0, { "精神" })
ROLE.n2 = merge(ROLE.n0, { "精神" })

D.RoleShuXing = ROLE

D.Presets = {
    WARRIOR = {
        { icon = ICON.WAR_ARMS, name = "战士-武器",
          useWeapon = { "双手斧", "双手锤", "双手剑", "长柄武器", "法杖", "弓", "弩", "枪", "投掷武器" },
          useArmor = { "皮甲", "锁甲", "板甲" },
          useShuXing = ROLE.dps1, Tank = {} },
        { icon = ICON.WAR_FURY, name = "战士-狂怒",
          useWeapon = { "匕首", "拳套", "单手斧", "单手锤", "单手剑", "弓", "弩", "枪", "投掷武器" },
          useArmor = { "皮甲", "锁甲", "板甲" },
          useShuXing = ROLE.dps1, Tank = {} },
        { icon = ICON.WAR_PROT, name = "战士-防护",
          useWeapon = { "匕首", "拳套", "单手斧", "单手锤", "单手剑", "弓", "弩", "枪", "投掷武器" },
          useArmor = { "板甲", "盾牌" },
          useShuXing = ROLE.t2, Tank = { "过滤坦克" } },
    },
    PALADIN = {
        { icon = ICON.PAL_HOLY, name = "圣骑士-神圣",
          useWeapon = { "单手斧", "单手锤", "单手剑" },
          useArmor = { "布甲", "皮甲", "锁甲", "板甲", "盾牌", "副手物品", "圣契" },
          useShuXing = ROLE.n2, Tank = {} },
        { icon = ICON.PAL_RET, name = "圣骑士-惩戒",
          useWeapon = { "双手斧", "双手锤", "双手剑", "长柄武器" },
          useArmor = { "皮甲", "锁甲", "板甲", "圣契" },
          useShuXing = ROLE.dps4, Tank = {} },
        { icon = ICON.PAL_PROT, name = "圣骑士-防护",
          useWeapon = { "单手斧", "单手锤", "单手剑" },
          useArmor = { "板甲", "盾牌", "圣契" },
          useShuXing = ROLE.t5, Tank = { "过滤坦克" } },
    },
    DEATHKNIGHT = {
        { icon = ICON.DK_BLOOD, name = "死亡骑士-鲜血",
          useWeapon = { "单手斧", "单手锤", "单手剑", "双手斧", "双手锤", "双手剑", "长柄武器" },
          useArmor = { "板甲", "魔印" },
          useShuXing = ROLE.t1, Tank = { "过滤坦克" } },
        { icon = ICON.DK_FROST, name = "死亡骑士-冰霜",
          useWeapon = { "单手斧", "单手锤", "单手剑", "双手斧", "双手锤", "双手剑", "长柄武器" },
          useArmor = { "皮甲", "锁甲", "板甲", "魔印" },
          useShuXing = ROLE.dps1, Tank = {} },
        { icon = ICON.DK_UNHOLY, name = "死亡骑士-邪恶",
          useWeapon = { "单手斧", "单手锤", "单手剑", "双手斧", "双手锤", "双手剑", "长柄武器" },
          useArmor = { "皮甲", "锁甲", "板甲", "魔印" },
          useShuXing = ROLE.dps1, Tank = {} },
    },

    HUNTER = {
        { icon = ICON.HUN_CLASS, name = "猎人",
          useWeapon = { "匕首", "拳套", "单手斧", "单手剑", "双手斧", "双手剑", "长柄武器", "法杖", "弓", "弩", "枪" },
          useArmor = { "皮甲", "锁甲" },
          useShuXing = ROLE.lr1, Tank = {} },
        { icon = ICON.HUN_BM, name = "猎人-兽王",
          useWeapon = { "匕首", "拳套", "单手斧", "单手剑", "双手斧", "双手剑", "长柄武器", "法杖", "弓", "弩", "枪" },
          useArmor = { "皮甲", "锁甲" },
          useShuXing = ROLE.lr1, Tank = {} },
        { icon = ICON.HUN_MM, name = "猎人-射击",
          useWeapon = { "匕首", "拳套", "单手斧", "单手剑", "双手斧", "双手剑", "长柄武器", "法杖", "弓", "弩", "枪" },
          useArmor = { "皮甲", "锁甲" },
          useShuXing = ROLE.lr1, Tank = {} },
        { icon = ICON.HUN_SV, name = "猎人-生存",
          useWeapon = { "匕首", "拳套", "单手斧", "单手剑", "双手斧", "双手剑", "长柄武器", "法杖", "弓", "弩", "枪" },
          useArmor = { "皮甲", "锁甲" },
          useShuXing = ROLE.lr1, Tank = {} },
    },
    SHAMAN = {
        { icon = ICON.SHA_CLASS, name = "萨满",
          useWeapon = { "匕首", "拳套", "单手斧", "单手锤", "双手斧", "双手锤", "法杖" },
          useArmor = { "布甲", "皮甲", "锁甲", "盾牌", "副手物品", "图腾" },
          useShuXing = merge(ROLE.dps3, ROLE.fx2, ROLE.n2), Tank = {} },
        { icon = ICON.SHA_ENH, name = "萨满-增强",
          useWeapon = { "匕首", "拳套", "单手斧", "单手锤", "双手斧", "双手锤", "法杖" },
          useArmor = { "布甲", "皮甲", "锁甲", "图腾" },
          useShuXing = ROLE.dps3, Tank = {} },
        { icon = ICON.SHA_ELE, name = "萨满-元素",
          useWeapon = { "匕首", "拳套", "单手斧", "单手锤", "法杖" },
          useArmor = { "布甲", "皮甲", "锁甲", "盾牌", "副手物品", "图腾" },
          useShuXing = ROLE.fx2, Tank = {} },
        { icon = ICON.SHA_RES, name = "萨满-恢复",
          useWeapon = { "匕首", "拳套", "单手斧", "单手锤", "法杖" },
          useArmor = { "布甲", "皮甲", "锁甲", "盾牌", "副手物品", "图腾" },
          useShuXing = ROLE.n2, Tank = {} },
    },
    DRUID = {
        { icon = ICON.DRU_CLASS, name = "德鲁伊",
          useWeapon = { "匕首", "拳套", "单手锤", "双手锤", "长柄武器", "法杖" },
          useArmor = { "布甲", "皮甲", "副手物品", "神像" },
          useShuXing = merge(ROLE.t3, ROLE.dps2, ROLE.fx1, ROLE.n1), Tank = {} },
        { icon = ICON.DRU_BEAR, name = "德鲁伊-巨熊",
          useWeapon = { "双手锤", "长柄武器", "法杖" },
          useArmor = { "皮甲", "神像" },
          useShuXing = ROLE.t3, Tank = { "过滤坦克" } },
        { icon = ICON.DRU_CAT, name = "德鲁伊-猎豹",
          useWeapon = { "双手锤", "长柄武器", "法杖" },
          useArmor = { "皮甲", "神像" },
          useShuXing = ROLE.dps2, Tank = {} },
        { icon = ICON.DRU_BOOM, name = "德鲁伊-平衡",
          useWeapon = { "匕首", "拳套", "单手锤", "法杖" },
          useArmor = { "布甲", "皮甲", "副手物品", "神像" },
          useShuXing = ROLE.fx1, Tank = {} },
        { icon = ICON.DRU_RES, name = "德鲁伊-恢复",
          useWeapon = { "匕首", "拳套", "单手锤", "法杖" },
          useArmor = { "布甲", "皮甲", "副手物品", "神像" },
          useShuXing = ROLE.n1, Tank = {} },
    },
    ROGUE = {
        { icon = ICON.ROG_CLASS, name = "盗贼",
          useWeapon = { "匕首", "拳套", "单手斧", "单手锤", "单手剑", "弓", "弩", "枪", "投掷武器" },
          useArmor = { "皮甲" },
          useShuXing = ROLE.dps2, Tank = {} },
    },
    MONK = {
        { icon = ICON.MNK_CLASS, name = "武僧",
          useWeapon = { "拳套", "单手斧", "单手锤", "单手剑", "长柄武器", "法杖" },
          useArmor = { "皮甲", "副手物品" },
          useShuXing = merge(ROLE.t4, ROLE.dps2, ROLE.n1), Tank = {} },
        { icon = ICON.MNK_BREW, name = "武僧-酒仙",
          useWeapon = { "拳套", "单手斧", "单手锤", "单手剑", "长柄武器", "法杖" },
          useArmor = { "皮甲" },
          useShuXing = ROLE.t4, Tank = { "过滤坦克" } },
        { icon = ICON.MNK_WW, name = "武僧-踏风",
          useWeapon = { "拳套", "单手斧", "单手锤", "单手剑", "长柄武器", "法杖" },
          useArmor = { "皮甲" },
          useShuXing = ROLE.dps2, Tank = {} },
        { icon = ICON.MNK_MW, name = "武僧-织雾",
          useWeapon = { "拳套", "单手斧", "单手锤", "单手剑", "法杖" },
          useArmor = { "皮甲", "副手物品" },
          useShuXing = ROLE.n1, Tank = {} },
    },
    PRIEST = {
        { icon = ICON.PRI_CLASS, name = "牧师",
          useWeapon = { "匕首", "单手锤", "法杖", "魔杖" },
          useArmor = { "布甲", "副手物品" },
          useShuXing = merge(ROLE.fx1, ROLE.n1), Tank = {} },
        { icon = ICON.PRI_SHA, name = "牧师-暗影",
          useWeapon = { "匕首", "单手锤", "法杖", "魔杖" },
          useArmor = { "布甲", "副手物品" },
          useShuXing = ROLE.fx1, Tank = {} },
        { icon = ICON.PRI_DISC, name = "牧师-戒律",
          useWeapon = { "匕首", "单手锤", "法杖", "魔杖" },
          useArmor = { "布甲", "副手物品" },
          useShuXing = ROLE.n1, Tank = {} },
        { icon = ICON.PRI_HOLY, name = "牧师-神圣",
          useWeapon = { "匕首", "单手锤", "法杖", "魔杖" },
          useArmor = { "布甲", "副手物品" },
          useShuXing = ROLE.n1, Tank = {} },
    },
    MAGE = {
        { icon = ICON.MAG_CLASS, name = "法师",
          useWeapon = { "匕首", "单手剑", "法杖", "魔杖" },
          useArmor = { "布甲", "副手物品" },
          useShuXing = ROLE.fx1, Tank = {} },
    },
    WARLOCK = {
        { icon = ICON.WLK_CLASS, name = "术士",
          useWeapon = { "匕首", "单手剑", "法杖", "魔杖" },
          useArmor = { "布甲", "副手物品" },
          useShuXing = ROLE.fx1, Tank = {} },
    },
}

do
    for _, list in pairs(D.Presets) do
        for i = 1, #list do
            local p = list[i]
            local kept = {}
            for _, nm in ipairs(p.useShuXing or {}) do
                if D.ShuXing[nm] then kept[#kept + 1] = nm end
            end
            p.useShuXing = kept
        end
    end
end

function D.KeyList(dim)
    local out = {}
    if dim == "Weapon" then
        for _, sid in ipairs(D.WeaponOrder) do
            local nm = D.WeaponName[sid]
            if nm then out[#out + 1] = { key = tostring(sid), label = nm } end
        end
    elseif dim == "Armor" then
        for _, sid in ipairs(D.ArmorOrder) do
            local nm = D.ArmorName[sid]
            if nm then out[#out + 1] = { key = tostring(sid), label = nm } end
        end
    elseif dim == "ShuXing" then
        for _, nm in ipairs(D.ShuXingOrder) do
            if D.ShuXing[nm] then
                out[#out + 1] = { key = nm, label = (D.ShuXingLabel and D.ShuXingLabel[nm]) or nm }
            end
        end
    elseif dim == "Class" then
        out[#out + 1] = { key = D.FLAG_CLASS, label = D.FlagLabel[D.FLAG_CLASS] }
    elseif dim == "BnetAccount" then
        out[#out + 1] = { key = D.FLAG_BNET, label = D.FlagLabel[D.FLAG_BNET] }
    elseif dim == "Tank" then
        out[#out + 1] = { key = D.FLAG_TANK, label = D.FlagLabel[D.FLAG_TANK] }
    end
    return out
end
