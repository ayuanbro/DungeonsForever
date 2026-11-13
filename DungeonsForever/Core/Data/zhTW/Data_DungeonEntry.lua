local gl = (type(GetLocale) == 'function') and GetLocale() or 'zhCN'
if gl ~= 'zhTW' then return end

local _, ns = ...

ns.DungeonEntry = {
    ["razorfen_kraul"] = { 1413, 41.8, 89.4, "貧瘠之地" },
    ["wailing_caverns"] = { 1413, 46.0, 36.4, "貧瘠之地" },
    ["razorfen_downs"] = { 1413, 49.1, 93.4, "貧瘠之地" },
    ["city_of_dalaran"] = { 1416, 8.0, 61.2, "奧特蘭克山脈" },
    ["uldaman"] = { 1418, 44.6, 12.1, "荒蕪之地" },
    ["ruins_of_lordaeron"] = { 1420, 65.0, 70.0, "提瑞斯法林地" },
    ["sm_armory"] = { 1420, 85.2, 32.1, "提瑞斯法林地" },
    ["sm_cathedral"] = { 1420, 85.2, 32.1, "提瑞斯法林地" },
    ["sm_graveyard"] = { 1420, 85.2, 32.1, "提瑞斯法林地" },
    ["sm_library"] = { 1420, 85.2, 32.1, "提瑞斯法林地" },
    ["shadowfang_keep"] = { 1421, 44.8, 67.8, "銀松森林" },
    ["scholomance"] = { 1422, 68.9, 72.8, "西瘟疫之地" },
    ["stratholme_main"] = { 1423, 27.1, 10.7, "東瘟疫之地" },
    ["stratholme_service"] = { 1423, 43.5, 19.4, "東瘟疫之地" },
    ["gnomeregan"] = { 1426, 24.4, 39.8, "丹莫羅" },
    ["blackrock_depths"] = { 1427, 45.6, 89.4, "灼熱峽谷" },
    ["lower_blackrock_spire"] = { 1428, 33.0, 25.2, "燃燒平原" },
    ["upper_blackrock_spire"] = { 1428, 33.0, 25.2, "燃燒平原" },
    ["the_drowned_city"] = { 1434, 21.5, 27.7, "荊棘谷" },
    ["sunken_temple"] = { 1435, 69.5, 52.5, "悲傷沼澤" },
    ["the_deadmines"] = { 1436, 42.5, 71.7, "西部荒野" },
    ["excavation_wetlands"] = { 1437, 47.8, 56.3, "溼地" },
    ["blackfathom_deeps"] = { 1440, 14.1, 13.1, "灰谷" },
    ["maraudon"] = { 1443, 29.1, 62.5, "淒涼之地" },
    ["dire_maul_west"] = { 1444, 60.3, 30.2, "菲拉斯" },
    ["dire_maul_north"] = { 1444, 62.5, 24.9, "菲拉斯" },
    ["dire_maul_east"] = { 1444, 64.8, 30.2, "菲拉斯" },
    ["onyxias_lair"] = { 1445, 52.3, 76.1, "塵泥沼澤" },
    ["alcaz_prison"] = { 1445, 75.3, 14.1, "塵泥沼澤" },
    ["zul_farrak"] = { 1446, 38.7, 20.0, "塔納利斯" },
    ["blackmaw_hold"] = { 1447, 38.6, 33.2, "艾薩拉" },
    ["shapers_terrace"] = { 1449, 48.1, 6.1, "安戈洛環形山" },
    ["the_stockade"] = { 1453, 50.4, 66.4, "暴風城" },
    ["ragefire_chasm"] = { 1454, 51.5, 49.7, "奧格瑞瑪" },
    ["hall_of_thanes"] = { 1455, 28.2, 47.7, "鐵爐堡" },
    ["kroldok_stronghold"] = { 2548, 37.5, 37.9, "河林" },
}

ns.DungeonEntryRoute = {
    ["excavation_wetlands"] = { { 1437, 53.4, 65.3, "集合石入口", "溼地" } },
    ["hall_of_thanes"] = { { 1455, 44.2, 52.0, "樓梯入口", "鐵爐堡" } },
}
