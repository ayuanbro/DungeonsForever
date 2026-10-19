local _, ns = ...
local L = ns.L
ns.ProfRecipeMeta = ns.ProfRecipeMeta or {}

local rows = {}
local function Smelt(spell, item, shownCount, listedCount, learn, yellow, green, grey, mats, station, source)
    local row = { spell, item, listedCount or shownCount, "Smelting", "", "", learn, yellow,
                  green, grey, spell > 1000000, mats, nil,
                  { skill = learn, read = "forever", vendors = {}, drops = {} } }
    rows[#rows + 1] = row
    ns.ProfRecipeMeta[spell] = {
        profession = "mining", cooldown = false, station = station or "forge",
        learnSource = source or "trainer", verified = source ~= "unknown",
        availabilityUnknown = source == "unknown" or source == "quest",
        outputConflict = listedCount == nil,
        listedCount = listedCount, detailCount = shownCount,
        outputReference = listedCount and "wowhead-created-item" or "unresolved",
        tools = {},
    }
end

Smelt(2657, 2840, 2, 1, 1, 25, 47, 70, {{2770, 1}})
Smelt(3304, 3576, 2, 1, 65, 65, 65, 75, {{2771, 1}})
Smelt(2659, 2841, 3, 2, 65, 65, 90, 115, {{2840, 1}, {3576, 1}})
Smelt(2658, 2842, 2, 1, 75, 100, 112, 125, {{2775, 1}})
Smelt(3307, 3575, 2, 1, 125, 130, 135, 140, {{2772, 1}})
Smelt(3308, 3577, 2, 1, 155, 170, 177, 185, {{2776, 1}})
Smelt(3569, 3859, 2, 1, 165, 165, 165, 165, {{3575, 1}, {3857, 1}})
Smelt(10097, 3860, 2, 1, 175, 175, 175, 175, {{3858, 1}})
Smelt(10098, 6037, 2, 1, 230, 230, 230, 230, {{7911, 1}})
Smelt(14891, 11371, 2, 1, 230, 230, 230, 230, {{11370, 8}}, "blackForge", "quest")
Smelt(16153, 12359, 2, 1, 250, 250, 250, 250, {{10620, 1}})
Smelt(1249637, 249726, 2, 1, 275, 275, 275, 275, {{249426, 2}, {3857, 1}})
Smelt(1306126, 251291, 2, 1, 300, 300, 307, 315, {{248815, 1}}, "moltenFoundry")
Smelt(22967, 17771, 2, 1, 310, 310, 315, 320,
      {{18562, 1}, {12360, 10}, {17010, 1}, {18567, 3}}, "forge", "unknown")
Smelt(1213638, 234003, 2, nil, 315, 315, 322, 330,
      {{12655, 2}, {22203, 2}}, "forge", "unknown")

ns.ProfRecipes = ns.ProfRecipes or {}
ns.ProfRecipes.mining = {
    word = "Recipe", counts = {items = 15, total = 15, sourced = 12, unreadable = 3},
    groups = {{"Smelting", L["熔炼"], "inv_ingot_02", 15}}, rows = rows,
}
ns.ProfRecipeKeys = ns.ProfRecipeKeys or {}
local exists
for _, key in ipairs(ns.ProfRecipeKeys) do if key == "mining" then exists = true end end
if not exists then ns.ProfRecipeKeys[#ns.ProfRecipeKeys + 1] = "mining" end

ns.ProfLeveling = ns.ProfLeveling or {}
ns.ProfLeveling.mining = {
    steps = {
        {1, 65, 2657, 130}, {65, 75, 3304, 60}, {75, 100, 2659, 60},
        {100, 125, 2658, 70}, {125, 140, 3307, 35},
        {140, 155, 0, 0, checkpoint = true, profession = "mining", reason = "gather"},
        {155, 185, 3308, 60},
        {185, 300, 0, 0, checkpoint = true, profession = "mining", reason = "gather"},
    },
    shopping = {}, sold = {3857},
    learn = {2657, 3304, 2659, 2658, 3307, 3308, 3569, 10097, 10098, 16153, 1249637, 1306126},
}
