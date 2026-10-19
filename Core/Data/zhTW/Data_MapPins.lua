local gl = (type(GetLocale) == 'function') and GetLocale() or 'zhCN'
if gl ~= 'zhTW' then return end

local _, ns = ...

ns.MapPins = {
    ["onyxias_lair"] = {
        entrance = { { 33.9, 20.7 } },
    },
    ["city_of_dalaran"] = {
        entrance = { { 14.4, 79.2, nil, 2 } },
    },
    ["excavation_wetlands"] = {
        entrance = { { 88.7, 26 } },
    },
    ["hall_of_thanes"] = {
        entrance = { { 50.9, 93.4 } },
        quest = { { 40, 63.8, 96395 }, { 54.6, 16.9, 98423 } },
    },
    ["ragefire_chasm"] = {
        entrance = { { 61, 8.6 } },
    },
    ["ruins_of_lordaeron"] = {
        entrance = { { 61, 21.6 } },
        quest = { { 62.4, 28.5, 95250 } },
    },
    ["shadowfang_keep"] = {
        object = { { 37.3, 53.8, 6895 }, { 47.2, 79.3, 6283, 6 } },
    },
    ["the_deadmines"] = {
        entrance = { { 30.8, 15.7 } },
    },
    ["wailing_caverns"] = {
        entrance = { { 47.1, 60.3 } },
    },
}
