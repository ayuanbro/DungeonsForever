local ns = _G.DF_NS or {}

if not ns.IsTitan then return end

ns.SpellExtra = {
    fix = {
        PALADIN = { [25780] = 10 },
    },
    hide = {
        HUNTER = { [5149] = true, [883] = true, [2641] = true, [6991] = true, [982] = true, [13481] = true, [1299332] = true, [75] = true },
        PALADIN = { [1279399] = true },
        DRUID = { [6795] = true },
        MAGE = { [1310030] = true, [1302508] = true },
        PRIEST = { [27871] = true, [27874] = true },
        ROGUE = { [8681] = true },
        WARRIOR = { [2457] = true },
    },
    cut = {
        DRUID = { [25298] = true, [31018] = true, [25297] = true, [25299] = true },
        HUNTER = { [25296] = true, [25295] = true },
        MAGE = { [25345] = true, [28612] = true, [25306] = true, [25304] = true },
        PALADIN = { [25292] = true, [25290] = true, [25291] = true },
        PRIEST = { [25315] = true, [25316] = true, [25314] = true },
        ROGUE = { [31016] = true, [25300] = true, [25302] = true },
        SHAMAN = { [29228] = true, [25361] = true, [25359] = true, [25357] = true, [21169] = true },
        WARLOCK = { [25311] = true, [28610] = true, [25309] = true, [25307] = true, [437169] = true },
        WARRIOR = { [25286] = true, [25289] = true, [25288] = true },
    },
    src = {
        HUNTER = { [19801] = { "book", 16665 } },
        MAGE = {
            [28609] = { "book", 22890 },
            [23028] = { "book", 18600 },
            [10140] = { "quest" },
            [28270] = { "misc" },
            [24530] = { "misc" },
            [1297659] = { "misc" },
        },
        PRIEST = {
            [27683] = { "book", 22393 },
            [21562] = { "book", 17413 },
            [21564] = { "book", 17414 },
        },
        DRUID = { [21849] = { "book", 17682 }, [21850] = { "book", 17683 } },
        ROGUE = { [25347] = { "misc" } },
    },
    passive = {
        WARRIOR = { { 3127, 6 }, { 674, 20 }, { 750, 40 } },
        PALADIN = { { 3127, 8 }, { 750, 40 } },
        HUNTER = { { 3127, 8 }, { 674, 20 }, { 8737, 40 } },
        ROGUE = { { 674, 10 }, { 3127, 12 } },
        SHAMAN = { { 8737, 40 } },
    },
    quest = {
        [355] = { 1498, 1665, 1678, 1683, 1819, 94003 },
        [7386] = { 1498, 1665, 1678, 1683, 1819, 94003 },
        [20252] = { 1719 },
        [10140] = { 7463 },
        [18960] = { 5921, 5922, 94913, 94914 },
    },
    raceSide = {
        ["Human"] = "A", ["Dwarf"] = "A", ["Gnome"] = "A", ["Night Elf"] = "A",
        ["人类"] = "A", ["矮人"] = "A", ["侏儒"] = "A", ["暗夜精灵"] = "A",
        ["人類"] = "A", ["暗夜精靈"] = "A",
        ["高阶会天裔"] = "A", ["高階會天裔"] = "A",
        ["Orc"] = "H", ["Troll"] = "H", ["Undead"] = "H",
        ["兽人"] = "H", ["巨魔"] = "H", ["亡灵"] = "H",
        ["獸人"] = "H", ["亡靈"] = "H",
    },
}
