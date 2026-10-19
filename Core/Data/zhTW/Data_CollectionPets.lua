local gl = (type(GetLocale) == 'function') and GetLocale() or 'zhCN'
if gl ~= 'zhTW' then return end

local _, ns = ...

ns.CollectionPets = {
    [1] = {
        4401, "inv_crate_01", nil, "craft",
        false, false, false, "工程學制造",
        __display = 7937,
        {
            { t = "工程學制造（結構圖：機械松鼠）" },
        },
    },
    [2] = {
        8485, "inv_box_petcarrier_01", "A", "vendor",
        12, 44.2, 53.2, "商人出售",
        __display = 5556,
        {
            { t = "從冬妮·安薩妮婭（艾爾文森林）處購買", m = { { "冬妮·安薩妮婭", 12, 44.2, 53.2 } } },
        },
    },
    [3] = {
        8486, "inv_box_petcarrier_01", "A", "vendor",
        12, 44.2, 53.2, "商人出售",
        __display = 5586,
        {
            { t = "從冬妮·安薩妮婭（艾爾文森林）處購買", m = { { "冬妮·安薩妮婭", 12, 44.2, 53.2 } } },
        },
    },
    [4] = {
        8487, "inv_box_petcarrier_01", "A", "vendor",
        12, 44.2, 53.2, "商人出售",
        __display = 5554,
        {
            { t = "從冬妮·安薩妮婭（艾爾文森林）處購買", m = { { "冬妮·安薩妮婭", 12, 44.2, 53.2 } } },
        },
    },
    [5] = {
        8488, "inv_box_petcarrier_01", "A", "vendor",
        12, 44.2, 53.2, "商人出售",
        __display = 5555,
        {
            { t = "從冬妮·安薩妮婭（艾爾文森林）處購買", m = { { "冬妮·安薩妮婭", 12, 44.2, 53.2 } } },
        },
    },
    [6] = {
        8489, "inv_box_petcarrier_01", "A", "vendor",
        1519, 50.4, 34.0, "商人出售",
        __display = 9989,
        {
            { t = "從利爾·迪米（暴風城運河）處購買", m = { { "利爾·迪米", 1519, 50.4, 34.0 } } },
        },
    },
    [7] = {
        8490, "inv_box_petcarrier_01", nil, "drop",
        false, false, false, "怪物掉落",
        __display = 5585,
        {
            { t = "死亡礦井中的鸚鵡「庫奇」掉落" },
        },
    },
    [8] = {
        8491, "inv_box_petcarrier_01", "H", "drop",
        130, 62.8, 62.2, "怪物掉落",
        __display = 5448,
        {
            { t = "擊殺達拉然書記員掉落（銀松森林）", m = { { "達拉然書記員", 130, 62.8, 62.2 } } },
        },
    },
    [9] = {
        8492, "spell_nature_forceofnature", nil, "drop",
        false, false, false, "怪物掉落",
        __display = 5207,
        {
            { t = "死亡礦井的迪菲亞海盜掉落" },
        },
    },
    [10] = {
        8494, "spell_nature_forceofnature", nil, "drop",
        33, 22.8, 54.0, "怪物掉落",
        __display = 6192,
        {
            { t = "擊殺血帆流氓 / 血帆大法師掉落（荊棘谷）", m = { { "血帆流氓", 33, 22.8, 54.0 } } },
        },
    },
    [11] = {
        8495, "spell_nature_forceofnature", nil, "vendor",
        33, 28.2, 74.4, "商人出售",
        __display = 6190,
        {
            { t = "從納爾克（荊棘谷·藏寶海灣）處購買", m = { { "納爾克", 33, 28.2, 74.4 } } },
        },
    },
    [12] = {
        8496, "spell_nature_forceofnature", nil, "vendor",
        33, 28.2, 74.4, "商人出售",
        __display = 6191,
        {
            { t = "從納爾克（荊棘谷·藏寶海灣）處購買", m = { { "納爾克", 33, 28.2, 74.4 } } },
        },
    },
    [13] = {
        8497, "inv_crate_02", "A", "vendor",
        1, 63.2, 50.2, "商人出售",
        __display = 6302,
        {
            { t = "從亞爾林·凍石（丹莫羅）處購買", m = { { "亞爾林·凍石", 1, 63.2, 50.2 } } },
        },
    },
    [14] = {
        8498, "inv_misc_head_dragon_green", nil, "drop",
        8, 11.4, 62.0, "怪物掉落",
        __display = 6291,
        {
            { t = "擊殺睡夢雛龍掉落（悲傷沼澤）", m = { { "睡夢雛龍", 8, 11.4, 62.0 } } },
        },
    },
    [15] = {
        8499, "inv_misc_head_dragon_01", nil, "drop",
        11, 57.4, 41.3, "怪物掉落",
        __display = 6290,
        {
            { t = "擊殺紅色雛龍 / 深紅雛龍掉落（溼地）", m = { { "紅色雛龍", 11, 57.4, 41.3 }, { "深紅雛龍", 11, 61.0, 34.4 } } },
        },
    },
    [16] = {
        8501, "ability_eyeoftheowl", "A", "vendor",
        1657, 69.4, 45.4, "商人出售",
        __display = 6299,
        {
            { t = "從夏琳奈爾（達納蘇斯）處購買", m = { { "夏琳奈爾", 1657, 69.4, 45.4 } } },
        },
    },
    [17] = {
        10394, "ability_hunter_beastcall", "H", "vendor",
        1638, 62.2, 58.4, "商人出售",
        __display = 1072,
        {
            { t = "從哈爾帕（雷霆崖）處購買", m = { { "哈爾帕", 1638, 62.2, 58.4 } } },
        },
    },
    [18] = {
        11023, "inv_chicken2_black", nil, "vendor",
        400, 78.2, 75.8, "商人出售",
        __display = 147417,
        {
            { t = "從大法師提爾斯（千針石林·加基森）處購買", m = { { "大法師提爾斯", 400, 78.2, 75.8 } } },
        },
    },
    [19] = {
        11027, "inv_crate_02", nil, "vendor",
        12, 40.4, 69.4, "商人出售",
        __display = 901,
        {
            { t = "從弗裏克（艾爾文森林 / 莫高雷）處購買", m = { { "弗裏克", 12, 40.4, 69.4 } } },
        },
    },
    [20] = {
        11474, "inv_egg_02", nil, "quest",
        false, false, false, "任務獎勵",
        __display = 6294,
        {
            { t = "完成任務「Becoming a Parent」獲得" },
        },
    },
    [21] = {
        11825, "inv_misc_bomb_04", nil, "craft",
        false, false, false, "工程學制造",
        __display = 8909,
        {
            { t = "工程學制造（結構圖：寵物炸彈）" },
        },
    },
    [22] = {
        11826, "inv_mechagon_spareparts", nil, "craft",
        false, false, false, "工程學制造",
        __display = 8910,
        {
            { t = "工程學制造（結構圖：發條娃娃）" },
        },
    },
    [23] = {
        13582, "spell_shadow_summonfelhunter", nil, "store",
        false, false, false, "商城獲取",
        __display = 10993,
        {
            { t = "購買「天藍史詩禮包」或「魔獸世界：無限」合集獲得" },
        },
    },
    [24] = {
        13583, "inv_belt_05", nil, "store",
        false, false, false, "商城獲取",
        __display = 10990,
        {
            { t = "購買「天藍史詩禮包」或「魔獸世界：無限」合集獲得" },
        },
    },
    [25] = {
        13584, "inv_diablostone", nil, "store",
        false, false, false, "商城獲取",
        __display = 10992,
        {
            { t = "購買「天藍史詩禮包」或「魔獸世界：無限」合集獲得" },
        },
    },
    [26] = {
        15996, "inv_misc_monsterhead_03", nil, "craft",
        false, false, false, "工程學制造",
        __display = 901,
        {
            { t = "工程學制造（結構圖：仿真機械蛙）" },
        },
    },
    [27] = {
        20769, "ability_creature_poison_05", nil, "drop",
        false, false, false, "怪物掉落",
        __display = 15436,
        {
            { t = "從軟泥怪掉落的「粘液袋」中開出" },
        },
    },
    [28] = {
        21277, "ability_hunter_pet_gorilla", nil, "craft",
        false, false, false, "工程學制造",
        __display = 10269,
        {
            { t = "工程學制造（結構圖：安靜的機械雪人）" },
        },
    },
    [29] = {
        275069, "inv_10_inscription2_repcontracts_scroll_02_uprez_color1", nil, "unknown",
        false, false, false, "獲取方式待補充",
        __display = 1141,
    },
    [30] = {
        276275, "ability_hunter_pet_worm", nil, "vendor",
        33, 27.4, 76.8, "商人出售",
        __display = 145177,
        {
            { t = "從賈恩（荊棘谷·藏寶海灣）處購買", m = { { "賈恩", 33, 27.4, 76.8 } } },
        },
    },
    [31] = {
        277483, "inv_10_inscription2_repcontracts_scroll_02_uprez_color1", nil, "unknown",
        false, false, false, "獲取方式待補充",
        __display = 6295,
    },
    [32] = {
        277493, "inv_10_inscription2_repcontracts_scroll_02_uprez_color1", nil, "unknown",
        false, false, false, "獲取方式待補充",
        __display = 11709,
    },
    [33] = {
        277508, "inv_box_petcarrier_01", "H", "vendor",
        1637, 36.6, 29.0, "商人出售",
        __display = 145568,
        {
            { t = "從瑪霍亞·天蹄（奧格瑞瑪）處購買", m = { { "瑪霍亞·天蹄", 1637, 36.6, 29.0 } } },
        },
    },
    [34] = {
        277651, "trade_archaeology_silverscrollcase", nil, "unknown",
        false, false, false, "獲取方式待補充",
    },
    [35] = {
        277714, "inv_pet_babyblizzardbear", nil, "unknown",
        false, false, false, "獲取方式待補充",
        __display = 145638,
    },
    [36] = {
        280347, "inv_squirrelflying_albino", nil, "vendor",
        16593, false, false, "商人出售",
        __display = 146639,
        {
            { t = "從 Vayn Moongaze（達拉然）處購買", m = { { "Vayn Moongaze", 16593, nil, nil } } },
        },
    },
    [37] = {
        280614, "inv_pachimarapet", nil, "store",
        false, false, false, "商城獲取",
        __display = 146839,
        {
            { t = "購買「天藍史詩禮包」或「魔獸世界：無限」合集獲得" },
        },
    },
    [38] = {
        280615, "inv_pet_babycrane", nil, "unknown",
        false, false, false, "獲取方式待補充",
        __display = 144905,
    },
    [39] = {
        280699, "spell_shadow_carrionswarm", "H", "vendor",
        1497, 67.4, 43.4, "商人出售",
        __display = 146860,
        {
            { t = "從傑雷米亞·派森（幽暗城）處購買", m = { { "傑雷米亞·派森", 1497, 67.4, 43.4 } } },
        },
    },
    [40] = {
        280703, "spell_nature_guardianward", "H", "vendor",
        1637, 19.0, 59.4, "商人出售",
        __display = 2958,
        {
            { t = "從克薩迪斯（奧格瑞瑪）處購買", m = { { "克薩迪斯", 1637, 19.0, 59.4 } } },
        },
    },
    [41] = {
        280794, "ability_hunter_beastcall", "H", "vendor",
        1638, 62.2, 58.4, "商人出售",
        __display = 146884,
        {
            { t = "從哈爾帕（雷霆崖）處購買", m = { { "哈爾帕", 1638, 62.2, 58.4 } } },
        },
    },
    [42] = {
        280795, "ability_hunter_beastcall", "H", "vendor",
        1638, 62.2, 58.4, "商人出售",
        __display = 146882,
        {
            { t = "從哈爾帕（雷霆崖）處購買", m = { { "哈爾帕", 1638, 62.2, 58.4 } } },
        },
    },
    [43] = {
        280797, "inv_crate_02", "A", "vendor",
        1, 63.2, 50.2, "商人出售",
        __display = 328,
        {
            { t = "從亞爾林·凍石（丹莫羅）處購買", m = { { "亞爾林·凍石", 1, 63.2, 50.2 } } },
        },
    },
    [44] = {
        280803, "ability_eyeoftheowl", "A", "vendor",
        1657, 69.4, 45.4, "商人出售",
        __display = 6300,
        {
            { t = "從夏琳奈爾（達納蘇斯）處購買", m = { { "夏琳奈爾", 1657, 69.4, 45.4 } } },
        },
    },
    [45] = {
        282637, "inv_egg_03", nil, "pick",
        false, false, false, "扒竊獲取",
        __display = 3248,
        {
            { t = "從「康達爾」身上扒竊獲得（潛行者專屬）" },
        },
    },
    [46] = {
        284176, "ability_hunter_pet_tallstrider", "A", "drop",
        148, 32.8, 88.8, "怪物掉落",
        __display = 147717,
        {
            { t = "擊殺雌性森林陸行鳥掉落（黑海岸）", m = { { "雌性森林陸行鳥", 148, 32.8, 88.8 } } },
        },
    },
    [47] = {
        284664, "inv_misc_food_54", nil, "vendor",
        17, 49.4, 29.4, "商人出售",
        __display = 147969,
        {
            { t = "從基莎（貧瘠之地）或塔梅琳·奧德里奇（紅色山脈）處購買", m = { { "基莎", 17, 49.4, 29.4 }, { "塔梅琳·奧德里奇", 44, nil, nil } } },
        },
    },
    [48] = {
        98550, nil, nil, "unknown",
        false, false, false, "獲取方式待補充",
        __display = 48934,
    },
    [49] = {
        275818, nil, nil, "unknown",
        false, false, false, "獲取方式待補充",
        __display = 144924,
    },
    [50] = {
        229368, nil, nil, "unknown",
        false, false, false, "獲取方式待補充",
        __display = 120330,
    }
}
