local gl = (type(GetLocale) == 'function') and GetLocale() or 'zhCN'
if gl ~= 'zhTW' then return end

local _, ns = ...

ns.DungeonData = {
    dungeons = {
        { id = "hall_of_thanes",     name = "領主大廳",       nameEn = "Hall of Thanes",            levelMin = 13, levelMax = 18, isNew = true,  zone = "鐵爐堡地下，丹莫羅",   bossCount = 4,  dropCount = 13,  art = "art-hall-of-thanes",     bosses = {} },
        { id = "ragefire_chasm",     name = "怒焰裂谷",       nameEn = "Ragefire Chasm",           levelMin = 13, levelMax = 18, isNew = false, zone = "奧格瑞瑪",             bossCount = 4,  dropCount = 12,  art = "art-ragefirechasm",      bosses = {} },
        { id = "ruins_of_lordaeron", name = "洛丹倫廢墟",     nameEn = "Ruins of Lordaeron",       levelMin = 15, levelMax = 20, isNew = true,  zone = "洛丹倫廢城",           bossCount = 8,  dropCount = 25,  art = "art-ruins-of-lordaeron", bosses = {} },
        { id = "wailing_caverns",    name = "哀嚎洞穴",       nameEn = "Wailing Caverns",          levelMin = 17, levelMax = 24, isNew = false, zone = "貧瘠之地",             bossCount = 10, dropCount = 37,  art = "art-wailingcaverns",     bosses = {} },
        { id = "the_deadmines",      name = "死亡礦井",       nameEn = "The Deadmines",            levelMin = 17, levelMax = 26, isNew = false, zone = "西部荒野",             bossCount = 11, dropCount = 49,  art = "art-deadmines",          bosses = {} },
        { id = "shadowfang_keep",    name = "影牙城堡",       nameEn = "Shadowfang Keep",          levelMin = 22, levelMax = 30, isNew = false, zone = "銀松森林",             bossCount = 15, dropCount = 48,  art = "art-shadowfangkeep",     bosses = {} },
        { id = "excavation_wetlands",name = "挖掘場：溼地",   nameEn = "Excavation Site: Wetlands",levelMin = 24, levelMax = 29, isNew = true,  zone = "溼地，維爾加挖掘場上方", bossCount = 4,  dropCount = 13, art = "art-excavation-site",    bosses = {} },
        { id = "blackfathom_deeps",  name = "黑暗深淵",       nameEn = "Blackfathom Deeps",        levelMin = 24, levelMax = 32, isNew = false, zone = "灰谷",                 bossCount = 9,  dropCount = 62,  art = "art-blackfathomdeeps",   bosses = {} },
        { id = "the_stockade",       name = "監獄",           nameEn = "The Stockade",             levelMin = 24, levelMax = 32, isNew = false, zone = "暴風城",               bossCount = 7,  dropCount = 36,   art = "art-stockade",           bosses = {} },
        { id = "city_of_dalaran",    name = "達拉然城",       nameEn = "City of Dalaran",          levelMin = 28, levelMax = 33, isNew = true,  zone = "奧特蘭克山脈",         bossCount = 8,   dropCount = 27, art = "art-city-of-dalaran",    bosses = {} },
        { id = "gnomeregan",         name = "諾莫瑞根",       nameEn = "Gnomeregan",               levelMin = 29, levelMax = 38, isNew = false, zone = "丹莫羅",               bossCount = 8,  dropCount = 49,  art = "art-gnomeregan",         bosses = {} },
        { id = "razorfen_kraul",     name = "剃刀沼澤",       nameEn = "Razorfen Kraul",           levelMin = 29, levelMax = 38, isNew = false, zone = "貧瘠之地",             bossCount = 10,  dropCount = 61,  art = "art-razorfenkraul",      bosses = {} },
        { id = "sm_graveyard",       name = "血色修道院：墓地", nameEn = "Scarlet Monastery Graveyard", levelMin = 30, levelMax = 38, isNew = false, zone = "提瑞斯法林地",   bossCount = 7,  dropCount = 55,  art = "art-scarletmonastery",   bosses = {} },
        { id = "sm_library",         name = "血色修道院：圖書館", nameEn = "Scarlet Monastery Library", levelMin = 33, levelMax = 41, isNew = false, zone = "提瑞斯法林地",   bossCount = 4,  dropCount = 39,  art = "art-scarlethalls",       bosses = {} },
        { id = "the_drowned_city",   name = "沉沒之城",       nameEn = "The Drowned City",         levelMin = 35, levelMax = 40, isNew = true,  zone = "荊棘谷近海",           bossCount = nil, dropCount = nil, art = "art-the-drowned-city",  bosses = {} },
        { id = "sm_armory",          name = "血色修道院：軍械庫", nameEn = "Scarlet Monastery Armory", levelMin = 36, levelMax = 44, isNew = false, zone = "提瑞斯法林地",   bossCount = 2,  dropCount = 33,  art = "art-scarlethalls",       bosses = {} },
        { id = "razorfen_downs",     name = "剃刀高地",       nameEn = "Razorfen Downs",           levelMin = 37, levelMax = 46, isNew = false, zone = "貧瘠之地",             bossCount = 8,  dropCount = 31,  art = "art-razorfendowns",      bosses = {} },
        { id = "sm_cathedral",       name = "血色修道院：大教堂", nameEn = "Scarlet Monastery Cathedral", levelMin = 38, levelMax = 46, isNew = false, zone = "提瑞斯法林地",  bossCount = 4,  dropCount = 38,  art = "art-scarletmonastery",   bosses = {} },
        { id = "kroldok_stronghold", name = "克羅多克要塞",   nameEn = "Krol'dok Stronghold",      levelMin = 40, levelMax = 45, isNew = true,  zone = "河谷林地（新區域）",   bossCount = nil, dropCount = nil, art = "art-kroldok-stronghold", bosses = {} },
        { id = "uldaman",            name = "奧達曼",         nameEn = "Uldaman",                  levelMin = 41, levelMax = 51, isNew = false, zone = "荒蕪之地",             bossCount = 15, dropCount = 59,  art = "art-uldaman",            bosses = {} },
        { id = "zul_farrak",         name = "祖爾法拉克",     nameEn = "Zul'Farrak",               levelMin = 44, levelMax = 54, isNew = false, zone = "塔納利斯",             bossCount = 14, dropCount = 39,  art = "art-zulfarrak",          bosses = {} },
        { id = "maraudon",           name = "瑪拉頓",         nameEn = "Maraudon",                 levelMin = 46, levelMax = 55, isNew = false, zone = "淒涼之地",             bossCount = 15, dropCount = 40,  art = "art-maraudon",           bosses = {} },
        { id = "alcaz_prison",       name = "奧卡茲監獄",     nameEn = "Alcaz Prison",             levelMin = 48, levelMax = 53, isNew = true,  zone = "奧卡茲島，塵泥沼澤",   bossCount = nil, dropCount = nil, art = "art-alcaz-prison",      bosses = {} },
        { id = "sunken_temple",      name = "沉沒的神廟",     nameEn = "Sunken Temple",            levelMin = 50, levelMax = 60, isNew = false, zone = "悲傷沼澤",             bossCount = 12, dropCount = 104, art = "art-sunkentemple",       bosses = {} },
        { id = "blackrock_depths",   name = "黑石深淵",       nameEn = "Blackrock Depths",         levelMin = 52, levelMax = 60, isNew = false, zone = "黑石山",               bossCount = 29, dropCount = 180, art = "art-blackrockdepths",    bosses = {} },
        { id = "dire_maul_east",     name = "厄運之槌：東",   nameEn = "Dire Maul East",           levelMin = 54, levelMax = 60, isNew = false, zone = "菲拉斯",               bossCount = 6,  dropCount = 56,  art = "art-diremaul",           bosses = {} },
        { id = "blackmaw_hold",      name = "黑喉要塞",       nameEn = "Blackmaw Hold",            levelMin = 55, levelMax = 60, isNew = true,  zone = "艾薩拉的大門之後",     bossCount = nil, dropCount = nil, art = "art-blackmaw-hold",     bosses = {} },
        { id = "lower_blackrock_spire", name = "黑石塔下層",  nameEn = "Lower Blackrock Spire",    levelMin = 55, levelMax = 60, isNew = false, zone = "黑石山",               bossCount = 17, dropCount = 93,  art = "art-blackrockspire",     bosses = {} },
        { id = "dire_maul_north",    name = "厄運之槌：北",   nameEn = "Dire Maul North",          levelMin = 56, levelMax = 60, isNew = false, zone = "菲拉斯",               bossCount = 10, dropCount = 126, art = "art-diremaul",           bosses = {} },
        { id = "dire_maul_west",     name = "厄運之槌：西",   nameEn = "Dire Maul West",           levelMin = 56, levelMax = 60, isNew = false, zone = "菲拉斯",               bossCount = 9,  dropCount = 69,  art = "art-diremaul",           bosses = {} },
        { id = "scholomance",        name = "通靈學院",       nameEn = "Scholomance",              levelMin = 58, levelMax = 60, isNew = false, zone = "西瘟疫之地",           bossCount = 16, dropCount = 292, art = "art-scholomance",        bosses = {} },
        { id = "shapers_terrace",    name = "塑造者平臺",     nameEn = "Shaper's Terrace",         levelMin = 58, levelMax = 60, isNew = true,  zone = "安戈洛環形山",         bossCount = nil, dropCount = nil, art = "art-shapers-terrace",    bosses = {} },
        { id = "stratholme_main",    name = "斯坦索姆：正門", nameEn = "Stratholme Main Gate",     levelMin = 58, levelMax = 60, isNew = false, zone = "東瘟疫之地",           bossCount = 13, dropCount = 106, art = "art-stratholme",         bosses = {} },
        { id = "stratholme_service", name = "斯坦索姆：側門", nameEn = "Stratholme Service Gate",  levelMin = 58, levelMax = 60, isNew = false, zone = "東瘟疫之地",           bossCount = 10, dropCount = 112, art = "art-stratholme",         bosses = {} },
        { id = "upper_blackrock_spire", name = "黑石塔上層",  nameEn = "Upper Blackrock Spire",    levelMin = 59, levelMax = 60, isNew = false, zone = "黑石山",               bossCount = 10, dropCount = 89,  art = "art-blackrockspire",     bosses = {} },
    },
}
