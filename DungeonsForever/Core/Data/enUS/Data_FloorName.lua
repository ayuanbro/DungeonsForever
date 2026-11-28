local _, ns = ...

if (type(DF_Locale) ~= "function") or DF_Locale() ~= "enUS" then return end

ns.FloorName = {
    ["city_of_dalaran"] = {
        [1] = "City of Dalaran",
        [2] = "Sewers",
    },
    ["gnomeregan"] = {
        [5] = "Dungeon entrance",
    },
    ["lower_blackrock_spire"] = {
        [1] = "L1 Tazz'Alaor",
        [2] = "L2 Skitterweb Tunnels",
        [3] = "L3 Hordemar City",
        [4] = "L4 Hall of Blackhand",
        [5] = "L5 Halycon's Lair",
        [6] = "L6 Chamber of Battle",
        [8] = "Entrance level",
    },
    ["sm_graveyard"] = {
        [1] = "Graveyard",
    },
    ["sm_library"] = {
        [1] = "Library",
    },
    ["sunken_temple"] = {
        [1] = "Upper level",
        [2] = "Middle level",
        [3] = "Lower level",
    },
}
