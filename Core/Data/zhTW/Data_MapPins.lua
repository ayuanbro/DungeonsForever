local gl = (type(GetLocale) == 'function') and GetLocale() or 'zhCN'
if gl ~= 'zhTW' then return end

local _, ns = ...

ns.MapPins = {
    ["gnomeregan"] = {
        quest = { { 82, 79.1, 2904, 2, "護送任務" }, { 37.4, 67.6, 2951, 1 } },
        entrance = { { 64.4, 27.4, nil, 1 } },
        next = { { 47.5, 83.6, 1 } },
    },
    ["the_stockade"] = {
        quest = { { 12.2, 15.2, 377, 1 }, { 69.7, 24.2, 378, 1 }, { 42, 40.8, 386, 1, "塔格爾在副本內。塔格爾通常刷在中央區右手第一間或左手第二間牢房，偶爾刷在左右兩翼之間最北端的牢房。" }, { 88.2, 48, 391, 1 } },
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
        prev = { { 56.3, 63.4, 1 } },
        next = { { 65.6, 46.5, 2 } },
    },
    ["excavation_wetlands"] = {
        quest = { { 25.4, 51.3, 95646, 1 }, { 44.1, 80.5, 95647, 1 }, { 24.4, 61, 95772, 1 } },
        entrance = { { 83.7, 40.1, nil, 1 } },
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
        next = { { 15.1, 85.9, 1, "飯廳" }, { 35.9, 66.9, 1 }, { 36.1, 39.8, 1, "飯廳" }, { 27.1, 88.6, 2 }, { 53.5, 60.5, 3 }, { 42.3, 73.1, 5 }, { 43.4, 33, 7 } },
    },
    ["the_deadmines"] = {
        entrance = { { 30.8, 15.7, nil, 1 }, { 12.5, 70.1, nil, 2 } },
        next = { { 65.4, 68.8, 1 }, { 84.3, 43, 2 } },
    },
    ["wailing_caverns"] = {
        entrance = { { 47.1, 60.3, nil, 1 } },
    },
}
