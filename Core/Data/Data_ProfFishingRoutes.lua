local _, ns = ...

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

local salmonNote = "指南对白鳞鲑鱼门槛记载不一致，取保守值；仍需钓鱼加成。"
W.salmon[1].note = salmonNote
W.salmon[2].note = salmonNote

ns.ProfFishingRoutes = {
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
          note = "先在出生地内陆水域起步，减少脱钩。" },
        { from = 25, to = 150, areas = early, fishIDs = { 6291, 6289, 6308 },
          note = "主城水域安全便利；幽暗城杂鱼较多，优先其他主城。" },
        { from = 150, to = 225, areas = W.trout, fishIDs = { 6362, 8365 },
          note = "尘泥沼泽：海岸钓鳕鱼，内陆钓冠鳟；换区不是涨点的必要条件。" },
        { from = 225, to = 300, areas = W.yellow, fishIDs = { 4603 },
          note = "热砂港优先，斑点黄尾鱼全年全天可钓；有效技能不足时可继续低级水域或使用钓鱼加成。" },
    },
}
