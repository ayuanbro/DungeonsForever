local _, ns = ...

ns.MapPins = {
    ["the_stockade"] = {
        quest = { { 12.8, 17.8, 377, 1 }, { 69.3, 26.4, 378, 1 }, { 42.1, 42.1, 386, 1 }, { 87.9, 50.2, 391, 1 } },
        entrance = { { 50.1, 81.3, nil, 1 } },
    },
    ["blackfathom_deeps"] = {
        quest = { { 20.8, 73.8, 1200, 1 }, { 20.9, 73.7, 6561, 1 } },
        entrance = { { 45.7, 11.5, nil, 1 } },
        icon = { { 33.3, 39.8, 1, "洛迦里斯手稿", "A" } },
        next = { { 61.9, 74.7, 1 } },
    },
    ["onyxias_lair"] = {
        entrance = { { 33.9, 20.7 } },
    },
    ["city_of_dalaran"] = {
        entrance = { { 14.4, 79.2, nil, 2 } },
    },
    ["excavation_wetlands"] = {
        entrance = { { 88.7, 26, nil, 1 } },
    },
    ["hall_of_thanes"] = {
        quest = { { 41.5, 65, 96395, 1 }, { 55, 22, 98423, 1 } },
        entrance = { { 50.5, 94.9, nil, 1 } },
    },
    ["ragefire_chasm"] = {
        quest = { { 63.8, 51.7, 5724, 1 } },
        entrance = { { 61, 8.6, nil, 1 } },
    },
    ["ruins_of_lordaeron"] = {
        entrance = { { 61.2, 21.5, nil, 1 } },
    },
    ["shadowfang_keep"] = {
        entrance = { { 70.4, 60.9, nil, 1 }, { 62, 12.6, nil, 2 } },
        prev = { { 52.6, 89, 3 }, { 52.3, 87.7, 4 }, { 49, 77.6, 5 }, { 41.5, 84.4, 6 }, { 23.8, 76, 7 } },
        next = { { 15.1, 85.9, 1, "饭厅" }, { 35.9, 66.9, 1 }, { 36.1, 39.8, 1, "饭厅" }, { 27.1, 88.6, 2 }, { 53.5, 60.5, 3 }, { 42.3, 73.1, 5 }, { 43.4, 33, 7 } },
    },
    ["the_deadmines"] = {
        entrance = { { 30.8, 15.7, nil, 1 }, { 12.5, 70.1, nil, 2 } },
        next = { { 65.4, 68.8, 1 }, { 84.3, 43, 2 } },
    },
    ["wailing_caverns"] = {
        entrance = { { 47.1, 60.3, nil, 1 } },
    },
}
