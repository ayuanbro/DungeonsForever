local _, ns = ...

ns.ProfRecipes = ns.ProfRecipes or {}

ns.ProfRecipes.mining = {
    word = "Recipe",
    counts = { items = 15, total = 15, sourced = 13, unreadable = 2 },
    groups = {
        { "Smelting", "熔炼", "inv_ingot_02", 15 },
    },
    rows = {
        { 2657, 2840, 1, "Smelting", "", "", 1, 25, 47, 70, false, { { 2770, 1 } }, nil,
          { skill = 1, read = "forever", vendors = {}, drops = {} } },
        { 3304, 3576, 1, "Smelting", "", "", 65, 65, 65, 75, false, { { 2771, 1 } }, nil,
          { skill = 65, read = "forever", vendors = {}, drops = {} } },
        { 2659, 2841, 2, "Smelting", "", "", 65, 65, 90, 115, false, { { 2840, 1 }, { 3576, 1 } }, nil,
          { skill = 65, read = "forever", vendors = {}, drops = {} } },
        { 2658, 2842, 1, "Smelting", "", "", 75, 100, 112, 125, false, { { 2775, 1 } }, nil,
          { skill = 75, read = "forever", vendors = {}, drops = {} } },
        { 3307, 3575, 1, "Smelting", "", "", 125, 130, 135, 140, false, { { 2772, 1 } }, nil,
          { skill = 125, read = "forever", vendors = {}, drops = {} } },
        { 3308, 3577, 1, "Smelting", "", "", 155, 170, 177, 185, false, { { 2776, 1 } }, nil,
          { skill = 155, read = "forever", vendors = {}, drops = {} } },
        { 3569, 3859, 1, "Smelting", "", "", 165, 165, 165, 165, false, { { 3575, 1 }, { 3857, 1 } }, nil,
          { skill = 165, read = "forever", vendors = {}, drops = {} } },
        { 10097, 3860, 1, "Smelting", "", "", 175, 175, 175, 175, false, { { 3858, 1 } }, nil,
          { skill = 175, read = "forever", vendors = {}, drops = {} } },
        { 10098, 6037, 1, "Smelting", "", "", 230, 230, 230, 230, false, { { 7911, 1 } }, nil,
          { skill = 230, read = "forever", vendors = {}, drops = {} } },
        { 14891, 11371, 1, "Smelting", "", "", 230, 230, 230, 230, false, { { 11370, 8 } }, nil,
          { skill = 230, read = "forever", vendors = {}, drops = {} } },
        { 16153, 12359, 1, "Smelting", "", "", 250, 250, 250, 250, false, { { 10620, 1 } }, nil,
          { skill = 250, read = "forever", vendors = {}, drops = {} } },
        { 1249637, 249726, 1, "Smelting", "", "", 275, 275, 275, 275, true, { { 249426, 2 }, { 3857, 1 } }, nil,
          { skill = 275, read = "forever", vendors = {}, drops = {} } },
        { 1306126, 251291, 1, "Smelting", "", "", 300, 300, 307, 315, true, { { 248815, 1 } }, nil,
          { skill = 300, read = "forever", vendors = {}, drops = {} } },
        { 22967, 17771, 1, "Smelting", "", "", 310, 310, 315, 320, false,
          { { 18562, 1 }, { 12360, 10 }, { 17010, 1 }, { 18567, 3 } }, nil,
          { skill = 310, read = "unknown", vendors = {}, drops = {} } },
        { 1213638, 234003, 2, "Smelting", "", "", 315, 315, 322, 330, true, { { 12655, 2 }, { 22203, 2 } }, nil,
          { skill = 315, read = "unknown", vendors = {}, drops = {} } },
    },
}

ns.ProfRecipeKeys = ns.ProfRecipeKeys or {}
local hasKey
for _, key in ipairs(ns.ProfRecipeKeys) do
    if key == "mining" then hasKey = true end
end
if not hasKey then ns.ProfRecipeKeys[#ns.ProfRecipeKeys + 1] = "mining" end

ns.ProfRecipeMeta = ns.ProfRecipeMeta or {}
local meta = {
    { 2657, "forge" },
    { 3304, "forge" },
    { 2659, "forge" },
    { 2658, "forge" },
    { 3307, "forge" },
    { 3308, "forge" },
    { 3569, "forge" },
    { 10097, "forge" },
    { 10098, "forge" },
    { 14891, "blackForge", true },
    { 16153, "forge" },
    { 1249637, "forge" },
    { 1306126, "moltenFoundry" },
    { 22967, "forge", true },
    { 1213638, "forge", true },
}
for _, m in ipairs(meta) do
    ns.ProfRecipeMeta[m[1]] = {
        profession = "mining", station = m[2], tools = {},
        availabilityUnknown = m[3] or nil,
    }
end

ns.ProfLeveling = ns.ProfLeveling or {}
ns.ProfLeveling.mining = {
    steps = {
        { 1, 65, 2657, 130 },
        { 65, 75, 3304, 60 },
        { 75, 100, 2659, 60 },
        { 100, 125, 2658, 70 },
        { 125, 140, 3307, 35 },
        { 140, 155, 0, 0, checkpoint = true, profession = "mining", reason = "gather" },
        { 155, 185, 3308, 60 },
        { 185, 300, 0, 0, checkpoint = true, profession = "mining", reason = "gather" },
    },
    shopping = {},
    sold = { 3857 },
    learn = { 2657, 3304, 2659, 2658, 3307, 3308, 3569, 10097, 10098, 16153, 1249637, 1306126 },
}
