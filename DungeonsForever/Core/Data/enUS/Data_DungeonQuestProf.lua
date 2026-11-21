local _, ns = ...

if (type(DF_Locale) ~= "function") or DF_Locale() ~= "enUS" then return end

ns.DungeonQuestProf = {
    [5103] = { "blacksmithing" },
    [5305] = { "blacksmithing", 364167, "Hammersmith" },
    [5306] = { "blacksmithing", 364165, "Axesmith" },
    [5307] = { "blacksmithing", 364164, "Swordsmith" },
}
