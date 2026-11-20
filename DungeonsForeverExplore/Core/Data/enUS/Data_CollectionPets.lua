local ns = _G.DF_NS or {}

if (type(DF_Locale) ~= "function") or DF_Locale() ~= "enUS" then return end

ns.CollectionPets = {
    [1] = {
        4401, "inv_crate_01", nil, "craft",
        false, false, false, "Crafted (Engineering)",
        __display = 7937,
        {
            { t = "Crafted (Engineering) (Schematic: Mechanical Squirrel Box)" },
        },
    },
    [2] = {
        8485, "inv_box_petcarrier_01", "A", "vendor", cost = 4210,
        12, 44.2, 53.2, "Sold by vendors",
        __display = 5556,
        {
            { t = "Purchased from Donni Anthania (Elwynn Forest)", m = { { "Donni Anthania", 12, 44.2, 53.2 } } },
        },
    },
    [3] = {
        8486, "inv_box_petcarrier_01", "A", "vendor", cost = 4210,
        12, 44.2, 53.2, "Sold by vendors",
        __display = 5586,
        {
            { t = "Purchased from Donni Anthania (Elwynn Forest)", m = { { "Donni Anthania", 12, 44.2, 53.2 } } },
        },
    },
    [4] = {
        8487, "inv_box_petcarrier_01", "A", "vendor", cost = 4210,
        12, 44.2, 53.2, "Sold by vendors",
        __display = 5554,
        {
            { t = "Purchased from Donni Anthania (Elwynn Forest)", m = { { "Donni Anthania", 12, 44.2, 53.2 } } },
        },
    },
    [5] = {
        8488, "inv_box_petcarrier_01", "A", "vendor", cost = 4210,
        12, 44.2, 53.2, "Sold by vendors",
        __display = 5555,
        {
            { t = "Purchased from Donni Anthania (Elwynn Forest)", m = { { "Donni Anthania", 12, 44.2, 53.2 } } },
        },
    },
    [6] = {
        8489, "inv_box_petcarrier_01", "A", "vendor", cost = 6000,
        1519, 50.4, 34.0, "Sold by vendors",
        __display = 9989,
        {
            { t = "Purchased from Lil Timmy (Stormwind Canals)", m = { { "Lil Timmy", 1519, 50.4, 34.0 } } },
            { t = "Purchased from Xaphod Bizznox (Stonetalon Mountains)" },
        },
    },
    [7] = {
        8490, "inv_box_petcarrier_01", nil, "drop",
        false, false, false, "Creature drop",
        __display = 5585,
        {
            { t = "Dropped by the parrot \"Cookie\" in The Deadmines" },
        },
    },
    [8] = {
        8491, "inv_box_petcarrier_01", "H", "drop",
        130, 62.8, 62.2, "Creature drop",
        __display = 5448,
        {
            { t = "Dropped by Dalaran Scribes (Silverpine Forest)", m = { { "Dalaran Scribe", 130, 62.8, 62.2 } } },
        },
    },
    [9] = {
        8492, "spell_nature_forceofnature", nil, "drop",
        false, false, false, "Creature drop",
        __display = 5207,
        {
            { t = "Dropped by Defias Pirates in The Deadmines" },
        },
    },
    [10] = {
        8494, "spell_nature_forceofnature", nil, "drop",
        33, 22.8, 54.0, "Creature drop",
        __display = 6192,
        {
            { t = "Dropped by Bloodsail Swashbucklers / Bloodsail Mages (Stranglethorn Vale)", m = { { "Bloodsail Swashbuckler", 33, 22.8, 54.0 } } },
        },
    },
    [11] = {
        8495, "spell_nature_forceofnature", nil, "vendor", cost = 4000,
        33, 28.2, 74.4, "Sold by vendors",
        __display = 6190,
        {
            { t = "Purchased from Narkk (Stranglethorn Vale · Booty Bay)", m = { { "Narkk", 33, 28.2, 74.4 } } },
        },
    },
    [12] = {
        8496, "spell_nature_forceofnature", nil, "vendor", cost = 4000,
        33, 28.2, 74.4, "Sold by vendors",
        __display = 6191,
        {
            { t = "Purchased from Narkk (Stranglethorn Vale · Booty Bay)", m = { { "Narkk", 33, 28.2, 74.4 } } },
        },
    },
    [13] = {
        8497, "inv_crate_02", "A", "vendor",
        1, 63.2, 50.2, "Sold by vendors",
        __display = 6302,
        {
            { t = "Purchased from Yarlyn Amberstill (Dun Morogh)", m = { { "Yarlyn Amberstill", 1, 63.2, 50.2 } } },
        },
    },
    [14] = {
        8498, "inv_misc_head_dragon_green", nil, "drop",
        8, 11.4, 62.0, "Creature drop",
        __display = 6291,
        {
            { t = "Dropped by Dreaming Whelps (Swamp of Sorrows)", m = { { "Dreaming Whelp", 8, 11.4, 62.0 } } },
        },
    },
    [15] = {
        8499, "inv_misc_head_dragon_01", nil, "drop",
        11, 57.4, 41.3, "Creature drop",
        __display = 6290,
        {
            { t = "Dropped by Red Whelps / Crimson Whelps (Wetlands)", m = { { "Red Whelp", 11, 57.4, 41.3 }, { "Crimson Whelp", 11, 61.0, 34.4 } } },
        },
    },
    [16] = {
        8501, "ability_eyeoftheowl", "A", "vendor", cost = 5000,
        1657, 69.4, 45.4, "Sold by vendors",
        __display = 6299,
        {
            { t = "Purchased from Shylenai (Darnassus)", m = { { "Shylenai", 1657, 69.4, 45.4 } } },
        },
    },
    [17] = {
        10394, "ability_hunter_beastcall", "H", "vendor", cost = 5263,
        1638, 62.2, 58.4, "Sold by vendors",
        __display = 1072,
        {
            { t = "Purchased from Halpa (Thunder Bluff)", m = { { "Halpa", 1638, 62.2, 58.4 } } },
        },
    },
    [18] = {
        11023, "inv_chicken2_black", nil, "vendor", cost = 9500,
        400, 78.2, 75.8, "Sold by vendors",
        __display = 147417,
        {
            { t = "Purchased from Magus Tirth (Thousand Needles · Gadgetzan)", m = { { "Magus Tirth", 400, 78.2, 75.8 } } },
        },
    },
    [19] = {
        11027, "inv_crate_02", nil, "vendor",
        12, 40.4, 69.4, "Sold by vendors",
        __display = 901,
        {
            { t = "Purchased from Flik (Elwynn Forest / Mulgore)", m = { { "Flik", 12, 40.4, 69.4 } } },
        },
    },
    [20] = {
        11474, "inv_egg_02", nil, "quest",
        false, false, false, "Quest rewards",
        __display = 6294,
        {
            { t = "Reward from the quest \"Becoming a Parent\"" },
        },
    },
    [21] = {
        11825, "inv_misc_bomb_04", nil, "craft",
        false, false, false, "Crafted (Engineering)",
        __display = 8909,
        {
            { t = "Crafted (Engineering) (Schematic: Pet Bombling)" },
        },
    },
    [22] = {
        11826, "inv_mechagon_spareparts", nil, "craft",
        false, false, false, "Crafted (Engineering)",
        __display = 8910,
        {
            { t = "Crafted (Engineering) (Schematic: Clockwork Doll)" },
        },
    },
    [23] = {
        13582, "spell_shadow_summonfelhunter", nil, "store",
        false, false, false, "From the shop",
        __display = 10993,
        {
            { t = "Reward for buying the \"Azure Epic Pack\" or the \"WoW Forever\" bundle" },
        },
    },
    [24] = {
        13583, "inv_belt_05", nil, "store",
        false, false, false, "From the shop",
        __display = 10990,
        {
            { t = "Reward for buying the \"Azure Epic Pack\" or the \"WoW Forever\" bundle" },
        },
    },
    [25] = {
        13584, "inv_diablostone", nil, "store",
        false, false, false, "From the shop",
        __display = 10992,
        {
            { t = "Reward for buying the \"Azure Epic Pack\" or the \"WoW Forever\" bundle" },
        },
    },
    [26] = {
        15996, "inv_misc_monsterhead_03", nil, "craft",
        false, false, false, "Crafted (Engineering)",
        __display = 901,
        {
            { t = "Crafted (Engineering) (Schematic: Lifelike Mechanical Toad)" },
        },
    },
    [27] = {
        20769, "ability_creature_poison_05", nil, "drop",
        false, false, false, "Creature drop",
        __display = 15436,
        {
            { t = "Opened from a \"Bag of Slime\" dropped by oozes" },
        },
    },
    [28] = {
        21277, "ability_hunter_pet_gorilla", nil, "craft",
        false, false, false, "Crafted (Engineering)",
        __display = 10269,
        {
            { t = "Crafted (Engineering) (Schematic: Tranquil Mechanical Yeti)" },
        },
    },
    [29] = {
        275069, "inv_10_inscription2_repcontracts_scroll_02_uprez_color1", nil, "unknown",
        false, false, false, "Source TBD",
        __display = 1141,
    },
    [30] = {
        276275, "ability_hunter_pet_worm", nil, "vendor", cost = { 1, "i", 274026, "inv_misc_coin_16" },
        33, 27.4, 76.8, "Sold by vendors",
        __display = 145177,
        {
            { t = "Purchased from Jaan (Stranglethorn Vale · Booty Bay)", m = { { "Jaan", 33, 27.4, 76.8 } } },
        },
    },
    [31] = {
        277483, "inv_10_inscription2_repcontracts_scroll_02_uprez_color1", nil, "unknown",
        false, false, false, "Source TBD",
        __display = 6295,
    },
    [32] = {
        277493, "inv_10_inscription2_repcontracts_scroll_02_uprez_color1", nil, "unknown",
        false, false, false, "Source TBD",
        __display = 11709,
    },
    [33] = {
        277508, "inv_box_petcarrier_01", "H", "vendor", cost = 6315,
        1637, 36.6, 29.0, "Sold by vendors",
        __display = 145568,
        {
            { t = "Purchased from Mahoya Skyhoof (Orgrimmar)", m = { { "Mahoya Skyhoof", 1637, 36.6, 29.0 } } },
        },
    },
    [34] = {
        277651, "trade_archaeology_silverscrollcase", nil, "unknown",
        false, false, false, "Source TBD",
    },
    [35] = {
        277714, "inv_pet_babyblizzardbear", nil, "unknown",
        false, false, false, "Source TBD",
        __display = 145638,
    },
    [36] = {
        280347, "inv_squirrelflying_albino", nil, "vendor", cost = 5263,
        2521, false, false, "Sold by vendors", cost = 5263,
        __display = 146639,
        {
            { t = "Purchased from Vayn Moongaze (Zephras Isle) at Revered" },
        },
    },
    [37] = {
        280614, "inv_pachimarapet", nil, "store",
        false, false, false, "From the shop",
        __display = 146839,
        {
            { t = "Reward for buying the \"Azure Epic Pack\" or the \"WoW Forever\" bundle" },
        },
    },
    [38] = {
        280615, "inv_pet_babycrane", nil, "unknown",
        false, false, false, "Source TBD",
        __display = 144905,
    },
    [39] = {
        280699, "spell_shadow_carrionswarm", "H", "vendor", cost = 5263,
        1497, 67.4, 43.4, "Sold by vendors",
        __display = 146860,
        {
            { t = "Purchased from Jeremiah Payson (Undercity)", m = { { "Jeremiah Payson", 1497, 67.4, 43.4 } } },
        },
    },
    [40] = {
        280703, "spell_nature_guardianward", "H", "vendor", cost = 5263,
        1637, 19.0, 59.4, "Sold by vendors",
        __display = 2958,
        {
            { t = "Purchased from Xan'tish (Orgrimmar)", m = { { "Xan'tish", 1637, 19.0, 59.4 } } },
        },
    },
    [41] = {
        280794, "ability_hunter_beastcall", "H", "vendor", cost = 5263,
        1638, 62.2, 58.4, "Sold by vendors",
        __display = 146884,
        {
            { t = "Purchased from Halpa (Thunder Bluff)", m = { { "Halpa", 1638, 62.2, 58.4 } } },
        },
    },
    [42] = {
        280795, "ability_hunter_beastcall", "H", "vendor", cost = 5263,
        1638, 62.2, 58.4, "Sold by vendors",
        __display = 146882,
        {
            { t = "Purchased from Halpa (Thunder Bluff)", m = { { "Halpa", 1638, 62.2, 58.4 } } },
        },
    },
    [43] = {
        280797, "inv_crate_02", "A", "vendor", cost = 2105,
        1, 63.2, 50.2, "Sold by vendors",
        __display = 328,
        {
            { t = "Purchased from Yarlyn Amberstill (Dun Morogh)", m = { { "Yarlyn Amberstill", 1, 63.2, 50.2 } } },
        },
    },
    [44] = {
        280803, "ability_eyeoftheowl", "A", "vendor", cost = 5263,
        1657, 69.4, 45.4, "Sold by vendors",
        __display = 6300,
        {
            { t = "Purchased from Shylenai (Darnassus)", m = { { "Shylenai", 1657, 69.4, 45.4 } } },
        },
    },
    [45] = {
        282637, "inv_egg_03", nil, "pick",
        false, false, false, "Pickpocket",
        __display = 3248,
        {
            { t = "Pickpocketed from \"Kondal\" (Rogue only)" },
        },
    },
    [46] = {
        284176, "ability_hunter_pet_tallstrider", "A", "drop",
        148, 32.8, 88.8, "Creature drop",
        __display = 147717,
        {
            { t = "Dropped by female Forest Striders (Darkshore)", m = { { "Female Forest Strider", 148, 32.8, 88.8 } } },
        },
    },
    [47] = {
        284664, "inv_misc_food_54", nil, "vendor", cost = { 1500, "c", 3402, "racial_dwarf_findtreasure" },
        17, 49.4, 29.4, "Sold by vendors",
        __display = 147969,
        {
            { t = "Purchased from Kisha (The Barrens) or Tamerin Aldrich (Redridge Mountains)", m = { { "Kisha", 17, 49.4, 29.4 }, { "Tamerin Aldrich", 44, nil, nil } } },
        },
    },
    [48] = {
        98550, nil, nil, "unknown",
        false, false, false, "Source TBD",
        __display = 48934,
    },
    [49] = {
        275818, nil, nil, "unknown",
        false, false, false, "Source TBD",
        __display = 144924,
    },
    [50] = {
        229368, nil, nil, "unknown",
        false, false, false, "Source TBD",
        __display = 120330,
    },
    [51] = {
        280697, "spell_shadow_carrionswarm", "H", "vendor",
        1497, 67.4, 43.4, "Sold by vendors", cost = 4736,
        {
            { t = "Purchased from Jeremiah Payson (Undercity)", m = { { "Jeremiah Payson", 1497, 67.4, 43.4 } } },
        },
    },
    [52] = {
        280801, "inv_crate_02", "A", "vendor",
        1, 63.2, 50.2, "Sold by vendors", cost = 1894,
        {
            { t = "Purchased from Yarlyn Amberstill (Dun Morogh)", m = { { "Yarlyn Amberstill", 1, 63.2, 50.2 } } },
        },
    },
    [53] = {
        282047, "inv_pet_babycrocodile_toothy", nil, "drop",
        1519, 22.4, 51.0, "Creature drop",
        {
            { t = "Dropped by Sewer Alligators (Stormwind City)", m = { { "Sewer Alligator", 1519, 22.4, 51.0 } } },
        },
    },
    [54] = {
        275682, "inv_maldraxxusslime", "H", "quest",
        false, false, false, "Quest rewards",
        {
            { t = "Reward from an Undercity quest" },
        },
    },
    [55] = {
        280456, "inv_inscription_pigment_bug04", nil, "quest",
        false, false, false, "Quest rewards",
        {
            { t = "Reward from a Wailing Marsh quest" },
        },
    },
    [56] = {
        268109, "inv_frog2_blue", nil, "world",
        2521, 51.0, 72.0, "World interaction",
        {
            { t = "On Zephras Isle (51, 72), use the /sing emote on the frog, then interact with the frog that appears" },
        },
    },
    [57] = {
        33154, "inv_misc_food_59", nil, "unknown",
        false, false, false, "Source TBD",
    },
    [58] = {
        74610, "achievement_worldevent_lunar", nil, "unknown",
        false, false, false, "Source TBD",
    },
    [59] = {
        74611, "achievement_worldevent_lunar", nil, "unknown",
        false, false, false, "Source TBD",
    },
    [60] = {
        268502, "inv_misc_head_dragon_bronze", nil, "unknown",
        false, false, false, "Source TBD",
    },
    [61] = {
        268503, "inv_misc_head_dragon_blue", nil, "unknown",
        false, false, false, "Source TBD",
    },
    [62] = {
        268879, "inv_diablostone", nil, "unknown",
        false, false, false, "Source TBD",
    },
    [63] = {
        269830, "ability_mount_whitedirewolf", nil, "unknown",
        false, false, false, "Source TBD",
    },
    [64] = {
        274956, "inv_egg_02", nil, "unknown",
        false, false, false, "Source TBD",
    },
    [65] = {
        284214, "spell_shadow_summoninfernal", nil, "unknown",
        false, false, false, "Source TBD",
    },
}
