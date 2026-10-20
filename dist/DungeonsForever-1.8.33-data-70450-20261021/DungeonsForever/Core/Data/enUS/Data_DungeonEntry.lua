local _, ns = ...

if (type(GetLocale) ~= "function") or GetLocale() ~= "enUS" then return end
local _, ns = ...

ns.DungeonEntry = {
    ["razorfen_kraul"] = { 1413, 41.8, 89.4, "The Barrens" },
    ["wailing_caverns"] = { 1413, 46.0, 36.4, "The Barrens" },
    ["razorfen_downs"] = { 1413, 49.1, 93.4, "The Barrens" },
    ["city_of_dalaran"] = { 1416, 8.0, 61.2, "Alterac Mountains" },
    ["uldaman"] = { 1418, 44.6, 12.1, "Badlands" },
    ["ruins_of_lordaeron"] = { 1420, 65.0, 70.0, "Tirisfal Glades" },
    ["sm_armory"] = { 1420, 85.2, 32.1, "Tirisfal Glades" },
    ["sm_cathedral"] = { 1420, 85.2, 32.1, "Tirisfal Glades" },
    ["sm_graveyard"] = { 1420, 85.2, 32.1, "Tirisfal Glades" },
    ["sm_library"] = { 1420, 85.2, 32.1, "Tirisfal Glades" },
    ["shadowfang_keep"] = { 1421, 44.8, 67.8, "Silverpine Forest" },
    ["scholomance"] = { 1422, 68.9, 72.8, "Western Plaguelands" },
    ["stratholme_main"] = { 1423, 27.1, 10.7, "Eastern Plaguelands" },
    ["stratholme_service"] = { 1423, 43.5, 19.4, "Eastern Plaguelands" },
    ["gnomeregan"] = { 1426, 24.4, 39.8, "Dun Morogh" },
    ["sunken_temple"] = { 1435, 69.5, 52.5, "Swamp of Sorrows" },
    ["the_deadmines"] = { 1436, 42.5, 71.7, "Westfall" },
    ["excavation_wetlands"] = { 1437, 47.8, 56.3, "Wetlands" },
    ["blackfathom_deeps"] = { 1440, 14.1, 13.1, "Ashenvale" },
    ["maraudon"] = { 1443, 29.1, 62.5, "Desolace" },
    ["dire_maul_west"] = { 1444, 60.3, 30.2, "Feralas" },
    ["dire_maul_north"] = { 1444, 62.5, 24.9, "Feralas" },
    ["dire_maul_east"] = { 1444, 64.8, 30.2, "Feralas" },
    ["onyxias_lair"] = { 1445, 52.3, 76.1, "Dustwallow Marsh" },
    ["zul_farrak"] = { 1446, 38.7, 20.0, "Tanaris" },
    ["the_stockade"] = { 1453, 50.4, 66.4, "Stormwind City" },
    ["ragefire_chasm"] = { 1454, 51.5, 49.7, "Orgrimmar" },
    ["hall_of_thanes"] = { 1455, 28.2, 47.7, "Ironforge" },
}

ns.DungeonEntryRoute = {
    ["excavation_wetlands"] = { { 1437, 53.4, 65.3, "Meeting Stone", "Wetlands" } },
    ["hall_of_thanes"] = { { 1455, 44.2, 52.0, "Stairway", "Ironforge" } },
}
