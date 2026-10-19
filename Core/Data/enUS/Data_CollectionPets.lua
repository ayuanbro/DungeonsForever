local _, ns = ...

if (type(GetLocale) ~= "function") or GetLocale() ~= "enUS" then return end
local _, ns = ...

ns.CollectionPets = {
    [1] = {
        4401, "inv_crate_01", nil, "craft",
        false, false, false, "工程学制造",
        __display = 7937,
        {
            { t = "工程学制造（结构图：机械松鼠）" },
        },
    },
    [2] = {
        8485, "inv_box_petcarrier_01", "A", "vendor",
        12, 44.2, 53.2, "商人出售",
        __display = 5556,
        {
            { t = "从冬妮·安萨妮娅（艾尔文森林）处购买", m = { { "冬妮·安萨妮娅", 12, 44.2, 53.2 } } },
        },
    },
    [3] = {
        8486, "inv_box_petcarrier_01", "A", "vendor",
        12, 44.2, 53.2, "商人出售",
        __display = 5586,
        {
            { t = "从冬妮·安萨妮娅（艾尔文森林）处购买", m = { { "冬妮·安萨妮娅", 12, 44.2, 53.2 } } },
        },
    },
    [4] = {
        8487, "inv_box_petcarrier_01", "A", "vendor",
        12, 44.2, 53.2, "商人出售",
        __display = 5554,
        {
            { t = "从冬妮·安萨妮娅（艾尔文森林）处购买", m = { { "冬妮·安萨妮娅", 12, 44.2, 53.2 } } },
        },
    },
    [5] = {
        8488, "inv_box_petcarrier_01", "A", "vendor",
        12, 44.2, 53.2, "商人出售",
        __display = 5555,
        {
            { t = "从冬妮·安萨妮娅（艾尔文森林）处购买", m = { { "冬妮·安萨妮娅", 12, 44.2, 53.2 } } },
        },
    },
    [6] = {
        8489, "inv_box_petcarrier_01", "A", "vendor",
        1519, 50.4, 34.0, "商人出售",
        __display = 9989,
        {
            { t = "从利尔·迪米（暴风城运河）处购买", m = { { "利尔·迪米", 1519, 50.4, 34.0 } } },
        },
    },
    [7] = {
        8490, "inv_box_petcarrier_01", nil, "drop",
        false, false, false, "怪物掉落",
        __display = 5585,
        {
            { t = "死亡矿井中的鹦鹉「库奇」掉落" },
        },
    },
    [8] = {
        8491, "inv_box_petcarrier_01", "H", "drop",
        130, 62.8, 62.2, "怪物掉落",
        __display = 5448,
        {
            { t = "击杀达拉然书记员掉落（银松森林）", m = { { "达拉然书记员", 130, 62.8, 62.2 } } },
        },
    },
    [9] = {
        8492, "spell_nature_forceofnature", nil, "drop",
        false, false, false, "怪物掉落",
        __display = 5207,
        {
            { t = "死亡矿井的迪菲亚海盗掉落" },
        },
    },
    [10] = {
        8494, "spell_nature_forceofnature", nil, "drop",
        33, 22.8, 54.0, "怪物掉落",
        __display = 6192,
        {
            { t = "击杀血帆流氓 / 血帆大法师掉落（荆棘谷）", m = { { "血帆流氓", 33, 22.8, 54.0 } } },
        },
    },
    [11] = {
        8495, "spell_nature_forceofnature", nil, "vendor",
        33, 28.2, 74.4, "商人出售",
        __display = 6190,
        {
            { t = "从纳尔克（荆棘谷·藏宝海湾）处购买", m = { { "纳尔克", 33, 28.2, 74.4 } } },
        },
    },
    [12] = {
        8496, "spell_nature_forceofnature", nil, "vendor",
        33, 28.2, 74.4, "商人出售",
        __display = 6191,
        {
            { t = "从纳尔克（荆棘谷·藏宝海湾）处购买", m = { { "纳尔克", 33, 28.2, 74.4 } } },
        },
    },
    [13] = {
        8497, "inv_crate_02", "A", "vendor",
        1, 63.2, 50.2, "商人出售",
        __display = 6302,
        {
            { t = "从亚尔林·冻石（丹莫罗）处购买", m = { { "亚尔林·冻石", 1, 63.2, 50.2 } } },
        },
    },
    [14] = {
        8498, "inv_misc_head_dragon_green", nil, "drop",
        8, 11.4, 62.0, "怪物掉落",
        __display = 6291,
        {
            { t = "击杀睡梦雏龙掉落（悲伤沼泽）", m = { { "睡梦雏龙", 8, 11.4, 62.0 } } },
        },
    },
    [15] = {
        8499, "inv_misc_head_dragon_01", nil, "drop",
        11, 57.4, 41.3, "怪物掉落",
        __display = 6290,
        {
            { t = "击杀红色雏龙 / 深红雏龙掉落（湿地）", m = { { "红色雏龙", 11, 57.4, 41.3 }, { "深红雏龙", 11, 61.0, 34.4 } } },
        },
    },
    [16] = {
        8501, "ability_eyeoftheowl", "A", "vendor",
        1657, 69.4, 45.4, "商人出售",
        __display = 6299,
        {
            { t = "从夏琳奈尔（达纳苏斯）处购买", m = { { "夏琳奈尔", 1657, 69.4, 45.4 } } },
        },
    },
    [17] = {
        10394, "ability_hunter_beastcall", "H", "vendor",
        1638, 62.2, 58.4, "商人出售",
        __display = 1072,
        {
            { t = "从哈尔帕（雷霆崖）处购买", m = { { "哈尔帕", 1638, 62.2, 58.4 } } },
        },
    },
    [18] = {
        11023, "inv_chicken2_black", nil, "vendor",
        400, 78.2, 75.8, "商人出售",
        __display = 147417,
        {
            { t = "从大法师提尔斯（千针石林·加基森）处购买", m = { { "Magus Tirth", 400, 78.2, 75.8 } } },
        },
    },
    [19] = {
        11027, "inv_crate_02", nil, "vendor",
        12, 40.4, 69.4, "商人出售",
        __display = 901,
        {
            { t = "从弗里克（艾尔文森林 / 莫高雷）处购买", m = { { "弗里克", 12, 40.4, 69.4 } } },
        },
    },
    [20] = {
        11474, "inv_egg_02", nil, "quest",
        false, false, false, "任务奖励",
        __display = 6294,
        {
            { t = "完成任务「Becoming a Parent」获得" },
        },
    },
    [21] = {
        11825, "inv_misc_bomb_04", nil, "craft",
        false, false, false, "工程学制造",
        __display = 8909,
        {
            { t = "工程学制造（结构图：宠物炸弹）" },
        },
    },
    [22] = {
        11826, "inv_mechagon_spareparts", nil, "craft",
        false, false, false, "工程学制造",
        __display = 8910,
        {
            { t = "工程学制造（结构图：发条娃娃）" },
        },
    },
    [23] = {
        13582, "spell_shadow_summonfelhunter", nil, "store",
        false, false, false, "商城获取",
        __display = 10993,
        {
            { t = "购买「天蓝史诗礼包」或「魔兽世界：无限」合集获得" },
        },
    },
    [24] = {
        13583, "inv_belt_05", nil, "store",
        false, false, false, "商城获取",
        __display = 10990,
        {
            { t = "购买「天蓝史诗礼包」或「魔兽世界：无限」合集获得" },
        },
    },
    [25] = {
        13584, "inv_diablostone", nil, "store",
        false, false, false, "商城获取",
        __display = 10992,
        {
            { t = "购买「天蓝史诗礼包」或「魔兽世界：无限」合集获得" },
        },
    },
    [26] = {
        15996, "inv_misc_monsterhead_03", nil, "craft",
        false, false, false, "工程学制造",
        __display = 901,
        {
            { t = "工程学制造（结构图：仿真机械蛙）" },
        },
    },
    [27] = {
        20769, "ability_creature_poison_05", nil, "drop",
        false, false, false, "怪物掉落",
        __display = 15436,
        {
            { t = "从软泥怪掉落的「粘液袋」中开出" },
        },
    },
    [28] = {
        21277, "ability_hunter_pet_gorilla", nil, "craft",
        false, false, false, "工程学制造",
        __display = 10269,
        {
            { t = "工程学制造（结构图：安静的机械雪人）" },
        },
    },
    [29] = {
        275069, "inv_10_inscription2_repcontracts_scroll_02_uprez_color1", nil, "unknown",
        false, false, false, "获取方式待补充",
        __display = 1141,
    },
    [30] = {
        276275, "ability_hunter_pet_worm", nil, "vendor",
        33, 27.4, 76.8, "商人出售",
        __display = 145177,
        {
            { t = "从贾恩（荆棘谷·藏宝海湾）处购买", m = { { "贾恩", 33, 27.4, 76.8 } } },
        },
    },
    [31] = {
        277483, "inv_10_inscription2_repcontracts_scroll_02_uprez_color1", nil, "unknown",
        false, false, false, "获取方式待补充",
        __display = 6295,
    },
    [32] = {
        277493, "inv_10_inscription2_repcontracts_scroll_02_uprez_color1", nil, "unknown",
        false, false, false, "获取方式待补充",
        __display = 11709,
    },
    [33] = {
        277508, "inv_box_petcarrier_01", "H", "vendor",
        1637, 36.6, 29.0, "商人出售",
        __display = 145568,
        {
            { t = "从玛霍亚·天蹄（奥格瑞玛）处购买", m = { { "玛霍亚·天蹄", 1637, 36.6, 29.0 } } },
        },
    },
    [34] = {
        277651, "trade_archaeology_silverscrollcase", nil, "unknown",
        false, false, false, "获取方式待补充",
    },
    [35] = {
        277714, "inv_pet_babyblizzardbear", nil, "unknown",
        false, false, false, "获取方式待补充",
        __display = 145638,
    },
    [36] = {
        280347, "inv_squirrelflying_albino", nil, "vendor",
        16593, false, false, "商人出售",
        __display = 146639,
        {
            { t = "从 Vayn Moongaze（达拉然）处购买", m = { { "Vayn Moongaze", 16593, nil, nil } } },
        },
    },
    [37] = {
        280614, "inv_pachimarapet", nil, "store",
        false, false, false, "商城获取",
        __display = 146839,
        {
            { t = "购买「天蓝史诗礼包」或「魔兽世界：无限」合集获得" },
        },
    },
    [38] = {
        280615, "inv_pet_babycrane", nil, "unknown",
        false, false, false, "获取方式待补充",
        __display = 144905,
    },
    [39] = {
        280699, "spell_shadow_carrionswarm", "H", "vendor",
        1497, 67.4, 43.4, "商人出售",
        __display = 146860,
        {
            { t = "从杰雷米亚·派森（幽暗城）处购买", m = { { "杰雷米亚·派森", 1497, 67.4, 43.4 } } },
        },
    },
    [40] = {
        280703, "spell_nature_guardianward", "H", "vendor",
        1637, 19.0, 59.4, "商人出售",
        __display = 2958,
        {
            { t = "从克萨迪斯（奥格瑞玛）处购买", m = { { "克萨迪斯", 1637, 19.0, 59.4 } } },
        },
    },
    [41] = {
        280794, "ability_hunter_beastcall", "H", "vendor",
        1638, 62.2, 58.4, "商人出售",
        __display = 146884,
        {
            { t = "从哈尔帕（雷霆崖）处购买", m = { { "哈尔帕", 1638, 62.2, 58.4 } } },
        },
    },
    [42] = {
        280795, "ability_hunter_beastcall", "H", "vendor",
        1638, 62.2, 58.4, "商人出售",
        __display = 146882,
        {
            { t = "从哈尔帕（雷霆崖）处购买", m = { { "哈尔帕", 1638, 62.2, 58.4 } } },
        },
    },
    [43] = {
        280797, "inv_crate_02", "A", "vendor",
        1, 63.2, 50.2, "商人出售",
        __display = 328,
        {
            { t = "从亚尔林·冻石（丹莫罗）处购买", m = { { "亚尔林·冻石", 1, 63.2, 50.2 } } },
        },
    },
    [44] = {
        280803, "ability_eyeoftheowl", "A", "vendor",
        1657, 69.4, 45.4, "商人出售",
        __display = 6300,
        {
            { t = "从夏琳奈尔（达纳苏斯）处购买", m = { { "夏琳奈尔", 1657, 69.4, 45.4 } } },
        },
    },
    [45] = {
        282637, "inv_egg_03", nil, "pick",
        false, false, false, "扒窃获取",
        __display = 3248,
        {
            { t = "从「康达尔」身上扒窃获得（潜行者专属）" },
        },
    },
    [46] = {
        284176, "ability_hunter_pet_tallstrider", "A", "drop",
        148, 32.8, 88.8, "怪物掉落",
        __display = 147717,
        {
            { t = "击杀雌性森林陆行鸟掉落（黑海岸）", m = { { "雌性森林陆行鸟", 148, 32.8, 88.8 } } },
        },
    },
    [47] = {
        284664, "inv_misc_food_54", nil, "vendor",
        17, 49.4, 29.4, "商人出售",
        __display = 147969,
        {
            { t = "从基莎（贫瘠之地）或塔梅琳·奥德里奇（红色山脉）处购买", m = { { "基莎", 17, 49.4, 29.4 }, { "塔梅琳·奥德里奇", 44, nil, nil } } },
        },
    },
    [48] = {
        98550, nil, nil, "unknown",
        false, false, false, "获取方式待补充",
        __display = 48934,
    },
    [49] = {
        275818, nil, nil, "unknown",
        false, false, false, "获取方式待补充",
        __display = 144924,
    },
    [50] = {
        229368, nil, nil, "unknown",
        false, false, false, "获取方式待补充",
        __display = 120330,
    }
}
