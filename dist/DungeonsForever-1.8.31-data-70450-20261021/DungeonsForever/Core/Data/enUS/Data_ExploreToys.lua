local _, ns = ...

if (type(GetLocale) ~= "function") or GetLocale() ~= "enUS" then return end
local _, ns = ...

ns.ExploreToys = {
    [1] = {
        280612, "inv_torch_lit", nil, "easy",
        10, false, false, "Night Watch Guard corpse · several spawn points, most often at Raven Hill 17.2,53.8",
        {
            { t = "The dead Night Watch Guard in Duskwood moves between spawn points; a yellow exclamation mark pops on the minimap when it appears; a /tar macro helps you find it",
              m = { { "Night Watch Guard", 10, false, false } } },
            { t = "Known spawn points: Brightwood Grove 66.1,34.0 · by Raven Hill 17.2,53.8 · road south to STV 47.7,59.4 · by Jitters 17,54",
              m = { { "Brightwood Grove 66.1,34.0", 10, 66.1, 34.0 },
                    { "by Raven Hill 17.2,53.8", 10, 17.2, 53.8 },
                    { "road south to STV 47.7,59.4", 10, 47.7, 59.4 },
                    { "by Jitters 17,54", 10, 17, 54 } } },
            { t = "Right-click the corpse to complete the quest \"#q\" and the torch (a green item) goes straight into your bag; while the corpse remains, everyone in the party can claim one", q = 98372 },
            { t = "Use to light the torch: 30 sec cooldown, burns for 5 min each time; it goes out when entering a building or swimming, and cannot be used in major cities" },
        },
        { { "Raven Hill 17.2,53.8", 10, 17.2, 53.8 } },
    },
}

ns.ExploreToyMeta = {
    updated = "2026-10-04",
}
