local ns = _G.DF_NS or {}

if (type(DF_Locale) ~= "function") or DF_Locale() ~= "enUS" then return end

local function z(id, min, ng)
    return { zoneID = id, minSkill = min, noGetaway = ng }
end

local W = {
    start     = { z(12, 1, 25), z(215, 1, 25), z(14, 1, 25), z(141, 1, 25) },
    city      = { z(1519, 1, 75), z(1537, 1, 75), z(1637, 1, 75), z(1638, 1, 75) },
    catfish   = { z(267, 55, 150), z(44, 55, 150), z(406, 55, 150) },
    trout     = { z(36, 130, 225), z(15, 130, 225), z(33, 130, 225) },
    cod       = { z(15, 130, 225), z(33, 130, 225) },
    yellow    = { z(440, 205, 300), z(47, 205, 300), z(357, 205, 300) },
    redgill   = { z(47, 205, 300), z(361, 205, 300) },
    salmon    = { z(618, 330, 425), z(357, 330, 425) },
    coastLow  = { z(14, 1, 25), z(141, 1, 25) },
    coastMid  = { z(17, 1, 75), z(40, 1, 75) },
    sagefish  = { z(38, 1, 75), z(130, 1, 75) },
    sageGreat = { z(36, 130, 225), z(33, 130, 225) },
}

local early = {}
for _, area in ipairs(W.city) do early[#early + 1] = area end
for _, area in ipairs(W.catfish) do early[#early + 1] = area end

local salmonNote = "Guides disagree on the Whitescale Salmon threshold; the conservative value is used. A fishing bonus is still needed."
W.salmon[1].note = salmonNote
W.salmon[2].note = salmonNote

ns.ProfFishingRoutes = {
    cookingSteps={{from=1,to=50,spell=7751},{from=50,to=100,spell=7753},{from=100,to=175,spell=7755},{from=175,to=225,spell=20916},{from=225,to=300,spell=18238},},
    fish = {
        [6291]  = { a = W.start,     rate = 0.60 },
        [6289]  = { a = W.city },
        [6308]  = { a = W.catfish,   rate = 0.60 },
        [8365]  = { a = W.trout },
        [6362]  = { a = W.cod },
        [4603]  = { a = W.yellow,    rate = 0.40 },
        [13758] = { a = W.redgill,   rate = 0.40 },
        [13754] = { a = W.yellow,    rate = 0.20 },
        [13889] = { a = W.salmon,    rate = 0.40 },
        [6303]  = { a = W.coastLow },
        [6361]  = { a = W.coastMid },
        [21071] = { a = W.sagefish,  pool = true },
        [21153] = { a = W.sageGreat, pool = true },
        [13759] = { a = W.redgill,   rate = 0.25, night = true },
        [13760] = { a = W.redgill,   rate = 0.25, night = true },
        [13755] = { a = W.yellow,    rate = 0.10, season = true },
        [13756] = { a = W.yellow,    rate = 0.10, season = true },
    },
    fishingSteps = {
        { from = 1, to = 25, areas = W.start, fishIDs = { 6291 },
          note = "Start in inland waters near your starting zone to reduce fish getting away." },
        { from = 25, to = 150, areas = early, fishIDs = { 6291, 6289, 6308 },
          note = "Capital city waters are safe and convenient; Undercity has more junk fish, so prefer other capitals." },
        { from = 150, to = 225, areas = W.trout, fishIDs = { 6362, 8365 },
          note = "Dustwallow Marsh: fish Rockscale Cod on the coast, Mithril Head Trout inland; changing zones is not required to gain skill." },
        { from = 225, to = 300, areas = W.yellow, fishIDs = { 4603 },
          note = "Steamwheedle Port first; Spotted Yellowtail can be caught all year at any time. If effective skill is short, keep fishing lower-level waters or use a fishing bonus." },
    },
}
