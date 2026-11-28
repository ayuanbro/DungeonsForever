local ns = _G.DF_NS or {}

if (type(DF_Locale) ~= "function") or DF_Locale() ~= "enUS" then return end

-- 英文客户端：自定义坐骑/宠物在客户端没有名字（显示为 Spell #id），这里给出英文名
-- enUS: server-custom mounts/pets have no client name (shown as "Spell #id"); give them English names
ns.NameOverrides = {
    spell = {
        [1279399] = "Warhorse",
        [1296534] = "Forsaken Charger",
        [5784] = "Felsteed",
        [13819] = "Warhorse",
        [23161] = "Dreadsteed",
        [23214] = "Charger",
        [1303215] = "Cargo Kodo",
        [15780] = "Green Mechanostrider",
        [436329] = "Golden Sabercat",
        [25863] = "Black Qiraji Battle Tank",
        [26655] = "Black Qiraji Battle Tank",
        [1292482] = "Swift Hyjal Stag",
        [1309268] = "Black Warden Saber",
        [1309270] = "Brown Warden Saber",
        [1309271] = "Gray Warden Saber",
        [1309272] = "White Warden Saber",
        [1309346] = "Black Devilsaur",
        [1309347] = "Blue Devilsaur",
        [1309348] = "Green Devilsaur",
        [1309349] = "Purple Devilsaur",
        [1309350] = "White Devilsaur",
        [1309377] = "Black Druidic Elk",
        [1309379] = "White Druidic Elk",
        [1309380] = "Green Druidic Elk",
        [1309381] = "Gray Druidic Elk",
    },
    item = {
        [286756] = "Spectral Wolf Pack",
        [286727] = "Crimson Rooster",
        [286724] = "Emerald Sea Turtle",
        [98550] = "Blossoming Ancient",
        [275818] = "Yaoyao",
        [229368] = "Gurfin",
    },
}
