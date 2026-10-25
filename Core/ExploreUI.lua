local _, ns = ...

if not ns.LoadForeverPages then return end

local L = ns.L

local Host = ns.ProfHost
if not Host then return end

local DG = Host.DG
local MakeFS = Host.MakeFS
local NewButton, MakeOutline, SetButtonSelected = Host.NewButton, Host.MakeOutline, Host.SetButtonSelected
local huiPaintRowSelect = ns.hui and ns.hui.PaintRowSelect or nil
local SetOutline, Unpack = Host.SetOutline, Host.Unpack
local C_GOLD, C_GREY = Host.C_GOLD, Host.C_GREY
local C_DIM, C_WHITE, C_TEXT = Host.C_DIM, Host.C_WHITE, Host.C_TEXT
local C_GREEN = Host.C_GREEN
local C_DONE = { 0.91, 0.78, 0.42 }
local CONTENT_W = Host.CONTENT_W
local PAGE_INSET = Host.PAGE_INSET
local FALLBACK_ICON = Host.FALLBACK_ICON

local B = ns.ExploreBooks
local META = ns.ExploreBookMeta or {}
local REWARDS = ns.ExploreBookRewards or {}
local PETS = ns.ExplorePets or {}
local TOYS = ns.ExploreToys or {}
local BANNER = ns.ExploreBanner or {}

local BAG_REQ_LVL, BAG_QUEST_LVL = 14, 40
local BAG_CHAIN = {
    { key = "p1", no = "①", title = "…and that note you found", xp = 3150,
      q = { A = 79008, H = 79007 },
      note = L["全链起点：无 NPC，在阿历克斯顿农场烧毁的田地点「烧焦的残骸」起链，旁边立着一块镶钉木板；两阵营从这里反向出发。"],
      loc = {
          A = { area = 40, x = 37.4, y = 50.6, zn = L["西部荒野 37.4,50.6"],
                place = L["西部荒野 · 阿历克斯顿农场"], obj = L["烧焦的残骸"] },
          H = { area = 17, x = 46.4, y = 73.9, zn = L["贫瘠之地 46.4,73.9"],
                place = L["贫瘠之地 · 陶拉祖营地以南烧毁塔楼"], obj = L["烧焦的残骸"] },
      },
      rw = { { 2459 }, { 3388 } } },
    { key = "p2", no = "②", title = "Stepping Stones", xp = 3150, q = 79192,
      note = L["两阵营互交互：在对方大陆的「烧焦的残骸 / 镶钉木板」上交①，再从镶钉木板接取本步；必给里的旧工具箱是 12 格包。"],
      loc = {
          A = { area = 17, x = 46.0, y = 74.0, zn = L["贫瘠之地 46,74"],
                place = L["贫瘠之地 · 陶拉祖营地以南烧毁塔楼"], obj = L["烧焦的残骸"] },
          H = { area = 40, x = 37.0, y = 50.0, zn = L["西部荒野 37,50"],
                place = L["西部荒野 · 阿历克斯顿农场"], obj = L["烧焦的残骸"] },
      },
      rw = { { 2901, note = L["二选一"] }, { 3334, note = L["二选一"] },
             { 1652 }, { 4470, note = L["营火材料"] }, { 4471, note = L["营火材料"] },
             { 221498, note = L["12 格包"] } } },
    { key = "p3", no = "③", title = "Scramble", xp = 315, q = 79980,
      note = { L["从烈日石居东北 "], { 406, 50.9, 52.3 }, L[" 的小路离开大路，往西翻过山到废弃营地，点箱子上的「散落杂物」交接；烈日石居是部落据点，联盟会从守卫旁经过。"] },
      loc = { area = 406, x = 40.7, y = 52.4, zn = L["石爪山脉 40.7,52.4"],
              place = L["石爪山脉 · 烈日石居上方废弃营地"], obj = L["散落杂物"] },
      rw = { { 3463, note = L["三选一 · 魔杖"] }, { 217314, note = L["三选一"] },
             { 217315, note = L["三选一"] }, { 3464 }, { 3465 }, { 216619 } } },
    { key = "fire", no = "3½", title = "Rekindle", optional = true, xp = nil, q = 80001,
      note = L["可选步：用②给的普通木柴 + 燧石和火绒重燃营火，燧石和火绒用完会还给你；链路不需要这步。"],
      loc = { area = 406, x = nil, y = nil, zn = L["同营地 · 营火"],
              place = L["石爪山脉 · 同营地营火（可选）"], obj = L["营火"] },
      rw = {} },
    { key = "p4", no = "④", title = "Wet Job", xp = 3150, q = 79974,
      note = L["爬上营地北边的山丘，跳到土堆上点它，途中要跳过一道缺口；注意摔落伤害。"],
      loc = { area = 406, x = 39.6, y = 49.9, zn = L["石爪山脉 39.6,49.9"],
              place = L["石爪山脉 · 营地正北山丘土堆"], obj = L["土堆"] },
      rw = { { 5432 }, { 20709 } } },
    { key = "p5", no = "⑤", title = "Eagle's Fist", xp = 3150, q = 79975,
      note = L["沿巨石水坝走出去、面向北方湿地，跳到坝顶下方的矮人头像雕刻上交接；水坝有联盟守卫，部落小心。"],
      loc = { area = 38, x = 49.4, y = 12.9, zn = L["洛克莫丹 49.4,12.9"],
              place = L["洛克莫丹 · 巨石水坝矮人头像雕刻"], obj = L["雕刻塑像"] },
      rw = {} },
    { key = "p6", no = "⑥", title = "This Must Be The Place", xp = 2350, q = 79976,
      note = { L["最大难点：敦霍尔德城堡东南方的推车（"], { 267, 87.4, 49.7 },
               L[" ）跳上索拉丁之墙，穿过墙内房间点阿拉希一侧的信使行囊（"], { 45, 22.4, 24.2 },
               L[" ）交接、再点下方草草收起的包裹拿睡袋；PVP 服小心。"] },
      loc = { area = 267, x = 87.4, y = 49.7, zn = L["希尔斯布莱德 87.4,49.7"],
              place = L["希尔斯布莱德丘陵 · 索拉丁之墙"], obj = L["信使行囊"] },
      rw = { { 211527, note = L["玩具"] }, { 216619 } } },
}

local BAG_FINAL_ID = 211527
local BAG_FINAL_DESC = L["铺开睡袋躺进去休息：每躺满 1 分钟叠 1 层 +1% 经验，最多 3 层（共 3%），持续 2 小时；铺开需原地站 15 秒，睡袋落地留 20 分钟，使用冷却 1 小时。每 1~2 小时铺一次、躺满 3 分钟即可常驻 3%，队友可同躺。"]
local BAG_RW_GROUPS = {
    { head = L["二选一 · 第②步"],
      items = { { 2901, "②" }, { 3334, "②" } } },
    { head = L["三选一 · 第③步"],
      items = { { 3463, L["③ · 魔杖"] }, { 217314, "③" }, { 217315, "③" } } },
    { head = L["链中必给"],
      items = { { 221498, L["12 格包 · ②"] }, { 216619, "×5 · ③⑥" }, { 1652, "②" },
                { 4470, L["② 营火材料"] }, { 4471, L["② 营火材料"] }, { 3464, "③" },
                { 3465, "③" }, { 2459, "①" }, { 3388, "①" },
                { 5432, "④" }, { 20709, "④" } } },
}

local BM_ID = {
    saberScroll = 277490,
    blade       = 273637,
    saber       = 276631,
    witScroll   = 277504,
    witchBlade  = 13964,
    bundle      = 277651,
    feather     = 17056,
    glyph       = 211779,
}

local BM_TABS = {
    { key = "ov",    text = L["总览"] },
    { key = "saber", text = L["冷焰佩剑"] },
    { key = "witch", text = L["女巫之刃"] },
    { key = "codex", text = L["卷轴图鉴"] },
}

local BM_AREA_SFK, BM_AREA_SCHOLO = 130, 28

local BM_CHAINS = {
    saber = {
        { key = "s1", skill = true, title = L["学习「理解」"], sub = L["6 级 · 法师训练师"],
          det = { sub = L["法师专属副技能 · 破译卷轴升到 300"],
                  lines = {
                      L["法师训练师从 6 级起教你「理解」，像专业一样：破译未翻译的卷轴一路升到 300。"],
                      L["「学习」每小时一次，耗一根轻羽毛，给一捆卷轴（内含数张）；需要先在暴风城或幽暗城的图书馆交书学会。"],
                      L["四档未翻译卷轴：理解 1 / 15 / 50 / 175 起可破译，30 / 75 / 200 / 300 变灰（变灰后不再涨技能）。"],
                  } } },
        { key = "s2", item = BM_ID.saberScroll, sub = L["理解（15）档最可能出"],
          det = { sub = L["破译未翻译的卷轴 · 走运才能拿到"],
                  lines = {
                      L["持续破译未翻译的卷轴，佩剑卷轴最可能来自理解（15）档。"],
                      L["未翻译卷轴名字乱码、只有法师能读；很多怪物都会掉落，掉率约 0.2%–4%。"],
                      L["破译也可能得到所有职业都能用的卷轴（注入 / 魔宠等，见「卷轴图鉴」页签）。"],
                  } } },
        { key = "s3", item = BM_ID.blade, sub = L["影牙城堡 · 约 12 次出"],
          loc = { area = BM_AREA_SFK, x = 44.8, y = 67.8, place = L["影牙城堡 · 银松森林"] },
          det = { sub = L["反复击杀席瓦莱恩男爵直到掉落"],
                  lines = {
                      L["席瓦莱恩之刃由影牙城堡的席瓦莱恩男爵掉落，约 12 次出。"],
                      L["卷轴和刀刃都是拾取后绑定：破译卷轴的法师也要自己拾取刀刃，记得请队友让给你。"],
                      L["20 级就能拾取刀刃并做出佩剑，但两者都需 21 级才能装备（Beta 等级上限 20，暂穿不了）。"],
                  } } },
        { key = "s4", item = BM_ID.saber, sub = L["冻结近战 +98 火焰伤害"],
          det = { sub = L["主手剑 · 需要等级 21 · 法师专属"],
                  lines = {
                      L["对刀刃使用佩剑卷轴即得冷焰佩剑：对冻结目标的近战命中额外造成 98 点火焰伤害（冰霜灼烧）。"],
                      L["冻结手段：冰霜新星；霜寒刺骨（冰冷效果最多 15% 几率冻结 5 秒）；寒冰指（会不会触发灼烧未验证）。"],
                      L["可搭配火花注入卷轴：受近战命中时火焰冲击冷却有机会重置；寒冰之刃注入是匕首注入，与佩剑不兼容。"],
                  } } },
    },
    witch = {
        { key = "w1", item = BM_ID.witScroll, sub = L["理解（175）档最可能出"],
          det = { sub = L["第二张武器卷轴 · 46 级档"],
                  lines = {
                      L["持续破译未翻译的卷轴，机智卷轴最可能来自理解（175）档。"],
                      L["第二把刀刃在 Beta 里也拿不到全流程：先攒卷轴，等等级上限提高。"],
                  } } },
        { key = "w2", item = BM_ID.witchBlade, sub = L["通灵学院 · 约 1/8 掉率"],
          loc = { area = BM_AREA_SCHOLO, x = 68.9, y = 72.8, place = L["通灵学院 · 西瘟疫之地"] },
          det = { sub = L["黑暗院长加丁掉落"],
                  lines = {
                      L["女巫之刃由通灵学院的黑暗院长加丁掉落，经典旧世大约每八次击杀掉一次。"],
                      L["单手匕首，需要等级 57 —— 与冷焰佩剑的剑不同，这是法师的第二条武器链。"],
                  } } },
        { key = "w3", ghost = true, title = L["未知武器"], sub = L["还不在客户端里"],
          det = { sub = L["未实装 · 先攒材料"],
                  lines = {
                      L["机智卷轴对女巫之刃使用后做出的武器还不在 Beta 客户端里：没有名字，也没有属性。"],
                      L["两者都需 57 级：等暴雪把等级上限提高到 30 级之后，这条链才真正可做。"],
                  } } },
    },
}

local BM_TIERS = {
    { req = 1,   gray = 30,  tier = L["5 级档"],
      unc = { 211780, 211785, 211786, 211787 },
      out = {
          { 274947, badge = L["法杖"], note = L["注入法杖 1 小时：火焰伤害最多 +4"] },
          { 275067, badge = L["匕首"], note = L["注入匕首 1 小时：击中时偶尔减速敌人"] },
          { 275069, badge = L["魔宠"], note = L["召唤老鼠魔宠 1 小时：智力 +2"] },
      } },
    { req = 15,  gray = 75,  tier = L["16 级档"],
      unc = { 211784, 211853, 211854, 211855 },
      out = {
          { BM_ID.saberScroll, badge = L["合成"], note = L["对席瓦莱恩之刃使用，合成冷焰佩剑"] },
          { 277489, badge = L["剑"],   note = L["注入剑 1 小时：受近战命中时火焰冲击冷却有机会重置"] },
          { 277488, badge = L["匕首"], note = L["注入匕首 1 小时：击中时偶尔冻结敌人"] },
          { 277485, badge = L["法杖"], note = L["注入法杖 1 小时：冰霜伤害最多 +8"] },
          { 277486, badge = L["法杖"], note = L["注入法杖 1 小时：法术伤害时偶尔释放奥术飞弹"] },
          { 277487, badge = L["法杖"], note = L["注入法杖 1 小时：目标火焰抗性 -10"] },
          { 277483, badge = L["魔宠"], note = L["召唤青蛙魔宠 1 小时：智力 +6"] },
          { 277484, badge = L["其它"], note = L["蛊惑目标野兽：对你造成的伤害降低 15%"] },
      } },
    { req = 50,  gray = 200, tier = L["25 级档"],
      unc = { 213543, 213544, 213545, 213546, 213547 },
      out = {
          { 277498, badge = L["匕首"], note = L["注入匕首 1 小时：击中时偶尔恢复法力值"] },
          { 277494, badge = L["法杖"], note = L["注入法杖 1 小时：法术命中几率 +3"] },
          { 277495, badge = L["法杖"], note = L["注入法杖 1 小时：法术伤害有几率提高魔杖攻速"] },
          { 277496, badge = L["法杖"], note = L["注入法杖 1 小时：目标冰霜抗性 -15"] },
          { 277497, badge = L["法杖"], note = L["注入法杖 1 小时：火焰伤害最多 +12"] },
          { 277491, badge = L["其它"], note = L["目标元素生物受到你的法术伤害提高 15%"] },
          { 277492, badge = L["其它"], note = L["用魔法打开开锁难度 125 或更低的锁"] },
          { 277493, badge = L["魔宠"], note = L["召唤猫魔宠 1 小时：智力 +12"] },
      } },
    { req = 175, gray = 300, tier = L["46 级档"],
      unc = { 281015, 281016, 281017, 281018 },
      out = {
          { BM_ID.witScroll, badge = L["合成"], note = L["对女巫之刃使用，合成第二把武器（未实装）"] },
          { 277499, badge = L["法术"], note = L["对 5 码内所有敌人造成 643–867 冰霜伤害（1 分钟冷却）"] },
          { 277500, badge = L["法杖"], note = L["注入法杖 1 小时：火焰伤害最多 +20"] },
          { 277501, badge = L["法杖"], note = L["注入法杖 1 小时：冰霜伤害最多 +20"] },
          { 277502, badge = L["法杖"], note = L["注入法杖 1 小时：法术爆击几率 +5%"] },
          { 277503, badge = L["法杖"], note = L["注入法杖 1 小时：火焰伤害最多 +4"] },
      } },
}

local BM_BUNDLE = {
    { 213564, 88 }, { 274947, 53 }, { 275067, 47 }, { 275069, 35 }, { 215257, 29 },
}

local EG = {}
EG.__qAsked = {}
ns.ExploreModule = EG
EG.BM_TIERS = BM_TIERS
EG.BM_BUNDLE = BM_BUNDLE

EG.NAV_X, EG.NAV_W = PAGE_INSET, 148
EG.NAV_GROUP_H = 24
EG.NAV_ITEM_H, EG.NAV_GAP = 24, 8
EG.NAV_ICON = 18
EG.W = CONTENT_W - 2 * PAGE_INSET
EG.EDGE = PAGE_INSET
EG.TOP_EDGE = 8
EG.NAV_TOP, EG.NAV_PAD = EG.TOP_EDGE + 8, 8
EG.X0 = EG.NAV_X + EG.NAV_PAD + EG.NAV_W + EG.NAV_PAD + 8
EG.RIGHT_W = CONTENT_W - EG.X0 - EG.EDGE
EG.TICK_Y = EG.TOP_EDGE + 8
EG.BAR_H = 4
EG.BAR_Y = EG.TICK_Y + 14 + 8
EG.TOOL_Y, EG.TOOL_H, EG.TOOL_GAP, EG.TOOL_W = EG.BAR_Y + EG.BAR_H + 8, 24, 8, 96
EG.NOTE_Y = EG.TOOL_Y + EG.TOOL_H + 8
EG.BODY_TOP = EG.NOTE_Y + 22
EG.RW_TOP = EG.NOTE_Y
EG.LIST_PAD = 8
EG.ROW_H, EG.ROW_GAP = 46, 4
EG.ZEBRA_A = 0.02
EG.ICON, EG.CHK = 20, 18
EG.BAR_W = EG.RIGHT_W - 2 * EG.LIST_PAD

EG.PET_CARDS, EG.PET_CARD_H, EG.PET_GAP = 4, 176, 8
EG.PET_HEAD_H = 32
EG.PET_ICON = 64
EG.PET_TX, EG.PET_PAD = 88, 8
EG.PET_ROW_H, EG.PET_ROWS = 18, 5
EG.PET_SEGS = 22
EG.TOY_CARD_PAD = 8

local C_RW = { 0.72, 0.45, 0.9 }
local C_RW_HI = { 0.87, 0.65, 0.98 }

EG.FILTERS = {
    { key = "all",       text = L["全部"] },
    { key = "ally",      text = L["联盟领地"], icon = "Interface\\AddOns\\DungeonsForever\\Media\\icon\\FACTION\\FactionIcon_Alliance" },
    { key = "horde",     text = L["部落领地"], icon = "Interface\\AddOns\\DungeonsForever\\Media\\icon\\FACTION\\FactionIcon_Horde" },
    { key = "contested", text = L["争夺中的领地"] },
    { key = "todo",      text = L["只看没找到"] },
}

local TERRITORY = {
    [10] = "A", [12] = "A", [38] = "A", [40] = "A", [1537] = "A",
    [17] = "H", [85] = "H", [1637] = "H",
    [148] = "A",
    [130] = "H",
}
local function BookTerr(rec)
    return TERRITORY[rec[2]] or "C"
end

EG.NECK_AT, EG.RING_AT, EG.CHOICE_AT = 10, 20, 25
EG.SWEEP_AT = { 0.5, 1.5, 3, 5, 8 }

local function Found()
    local db = ns.DB()
    db.explore = db.explore or {}
    db.explore.found = db.explore.found or {}
    return db.explore.found
end

local function Comma(n)
    local s = tostring(math.floor(n))
    local k
    repeat s, k = s:gsub("^(-?%d+)(%d%d%d)", "%1,%2") until k == 0
    return s
end

local function BagQuestState(qid)
    if not qid or type(C_QuestLog) ~= "table" then return 0 end
    if C_QuestLog.IsQuestFlaggedCompleted then
        local ok, done = pcall(C_QuestLog.IsQuestFlaggedCompleted, qid)
        if ok and done then return 2 end
    end
    if C_QuestLog.HasQuest then
        local ok, on = pcall(C_QuestLog.HasQuest, qid)
        if ok and on then return 1 end
    end
    return 0
end

local function BagQuestTitle(entry, fac)
    local qid = type(entry.q) == "table" and entry.q[fac] or entry.q
    if qid and type(C_QuestLog) == "table" and C_QuestLog.GetTitleForQuestID then
        local ok, t = pcall(C_QuestLog.GetTitleForQuestID, qid)
        if ok and type(t) == "string" and t ~= "" then return t end
    end
    return entry.title
end

local function BagStep(entry, fac)
    local loc = entry.loc
    if loc.A then loc = loc[fac] or loc.A end
    local qid = type(entry.q) == "table" and entry.q[fac] or entry.q
    return loc, qid
end

local function ToyQuestTitle(qid)
    if qid and type(C_QuestLog) == "table" and C_QuestLog.GetTitleForQuestID then
        local ok, t = pcall(C_QuestLog.GetTitleForQuestID, qid)
        if ok and type(t) == "string" and t ~= "" then return t end
        if DG.RequestQuest then DG.RequestQuest(qid) end
    end
    return nil
end

local function BagFac()
    local db = ns.DB()
    db.explore = db.explore or {}
    if db.explore.bagFac == "A" or db.explore.bagFac == "H" then
        return db.explore.bagFac
    end
    local fac = "A"
    if type(UnitFactionGroup) == "function" then
        local ok, _, eng = pcall(UnitFactionGroup, "player")
        if ok and eng == "Horde" then fac = "H" end
    end
    return fac
end

local function View()
    local db = ns.DB()
    db.explore = db.explore or {}
    for _, f in ipairs(EG.FILTERS) do
        if db.explore.view == f.key then return f.key end
    end
    return "all"
end

local function CurSub()
    local db = ns.DB()
    db.explore = db.explore or {}
    if db.explore.subPage == "rewards" then return "rewards" end
    if db.explore.subPage == "bag" then return "bag" end
    if db.explore.subPage == "bm" then return "bm" end
    if db.explore.subPage == "pets" then return "pets" end
    if db.explore.subPage == "torch" then return "torch" end
    if db.explore.subPage == "banner" then return "banner" end
    if db.explore.subPage == "routes" then return "routes" end
    return "books"
end

local function SetSub(key)
    local db = ns.DB()
    db.explore = db.explore or {}
    db.explore.subPage = key
    EG._sweepFails = 0
    if EG.petFrame and EG.petFrame.scroll and EG.petFrame.scroll.SetVerticalScroll then
        pcall(EG.petFrame.scroll.SetVerticalScroll, EG.petFrame.scroll, 0)
    end
    EG.RequestRender()
    ns.PlaySound(1)
end

local QUESTS = ns.ExploreBookQuests or {}

function EG.CountInBags(id)
    if type(GetItemCount) == "function" then
        local ok, c = pcall(GetItemCount, id)
        if ok and type(c) == "number" and c > 0 then return c end
    end
    if type(C_Item) == "table" and type(C_Item.GetItemCount) == "function" then
        local ok, c = pcall(C_Item.GetItemCount, id)
        if ok and type(c) == "number" and c > 0 then return c end
    end
    local numSlots, itemLink
    if type(C_Container) == "table" then
        numSlots = C_Container.GetContainerNumSlots
        itemLink = C_Container.GetContainerItemLink
    end
    numSlots = numSlots or GetContainerNumSlots
    itemLink = itemLink or GetContainerItemLink
    if type(numSlots) ~= "function" or type(itemLink) ~= "function" then return 0 end
    local n = 0
    for bag = 0, 4 do
        local okS, slots = pcall(numSlots, bag)
        if okS and type(slots) == "number" and slots > 0 then
            for slot = 1, slots do
                local okL, link = pcall(itemLink, bag, slot)
                if okL and type(link) == "string" then
                    local iid = tonumber(link:match("^item%:(%d+)"))
                    if iid == id then n = n + 1 end
                end
            end
        end
    end
    return n
end

function EG.ScanAuto()
    local t = {}
    if C_QuestLog and C_QuestLog.IsQuestFlaggedCompleted then
        for _, rec in ipairs(B) do
            local q = QUESTS[rec[1]]
            if q then
                local ok, done = pcall(C_QuestLog.IsQuestFlaggedCompleted, q)
                if ok and done then t[rec[1]] = "quest" end
            end
        end
    end
    if GetItemCount or C_Item or C_Container or GetContainerItemLink then
        for _, rec in ipairs(B) do
            local ok, n = pcall(EG.CountInBags, rec[1])
            if ok and (n or 0) > 0 and not t[rec[1]] then t[rec[1]] = "bag" end
        end
    end
    EG._auto = t
end

local function IsFound(id)
    return (EG.found and EG.found[id]) or (EG._auto and EG._auto[id]) or false
end

function EG.IsBookFound(id)
    return IsFound(id)
end

function EG.ToggleBookFound(id)
    if not id then return end
    local f = Found()
    f[id] = (not f[id]) or nil
    EG.RequestRender()
    ns.PlaySound(1)
end

local AREA_MAP = ns.AreaMap or {}

local function MapIDAlive(mapID)
    if not mapID then return false end
    if not (C_Map and C_Map.GetMapInfo) then return true end
    local ok, mi = pcall(C_Map.GetMapInfo, mapID)
    return ok and mi ~= nil
end

function EG.MarkPoint(areaID, x, y)
    local mapID = areaID and AREA_MAP[areaID] or nil
    if not MapIDAlive(mapID) then
        mapID = nil
        if areaID and C_Map and C_Map.GetMapInfoFromAreaID then
            local ok, mi = pcall(C_Map.GetMapInfoFromAreaID, areaID)
            mapID = ok and mi and mi.mapID or nil
        end
        if not MapIDAlive(mapID) then mapID = nil end
    end
    if not mapID then
        if UIErrorsFrame and UIErrorsFrame.AddMessage then
            pcall(UIErrorsFrame.AddMessage, UIErrorsFrame,
                  format(L["「%s」没有独立世界地图，请按位置细节前往"],
                         tostring(EG.ZoneName(areaID, areaID or "?"))), 1, 0.4, 0.4)
        end
        return
    end
    if type(x) == "number" and type(y) == "number"
       and UiMapPoint and UiMapPoint.CreateFromCoordinates and C_Map and C_Map.SetUserWaypoint then
        local pok, pt = pcall(UiMapPoint.CreateFromCoordinates, mapID, x / 100, y / 100)
        if pok and pt then
            pcall(C_Map.SetUserWaypoint, pt)
            if C_SuperTrack and C_SuperTrack.SetSuperTrackedUserWaypoint then
                pcall(C_SuperTrack.SetSuperTrackedUserWaypoint, false)
            end
        end
    end
    if C_Map and C_Map.OpenWorldMap then
        pcall(C_Map.OpenWorldMap, mapID)
    elseif OpenWorldMap then
        pcall(OpenWorldMap, mapID)
    end
end

function EG.ZoneName(areaID, fallback)
    local f = C_Map and C_Map.GetMapInfoFromAreaID
    if f and areaID then
        local ok, mi = pcall(f, areaID)
        if ok and mi and mi.name and mi.name ~= "" then return mi.name end
    end
    local g = C_Map and C_Map.GetAreaInfo
    if g and areaID then
        local ok, name = pcall(g, areaID)
        if ok and type(name) == "string" and name ~= "" then return name end
    end
    return fallback
end

local function HuiRowFX(f, rad, hovR)
    if not (ns.hui and ns.hui.BuildRoundedBG) then return false end
    if f.SetBackdropColor then f:SetBackdropColor(0, 0, 0, 0) end
    if f.SetBackdropBorderColor then f:SetBackdropBorderColor(0, 0, 0, 0) end
    ns.hui.BuildRoundedBG(f, rad, ns.hui.layer.L2, "both", true, 1)
    f.__huiCard = true
    if hovR and ns.hui.BuildCapsule then
        f.__hov = ns.hui.BuildCapsule(f, hovR, ns.hui.layer.L4, 1, 2)
        for _, t in ipairs(f.__hov) do t:Hide() end
    end
    return true
end

local function HuiPillFX(p, rad, edgeCol)
    if not (ns.hui and ns.hui.BuildRoundedBG) then return false end
    if p.SetBackdropColor then p:SetBackdropColor(0, 0, 0, 0) end
    if p.SetBackdropBorderColor then p:SetBackdropBorderColor(0, 0, 0, 0) end
    ns.hui.BuildRoundedBG(p, rad, ns.hui.layer.L2, "both", false)
    if edgeCol and ns.hui.BuildRoundBorder then
        p.__border = ns.hui.BuildRoundBorder(p, rad, edgeCol, nil, "BORDER", "both", 1)
    end
    return true
end

local function PillEdge(pill, r, g, b, a)
    if pill.__border then
        for _, t in ipairs(pill.__border) do
            t:SetVertexColor(r, g, b)
            t:SetAlpha(a or 1)
        end
    else
        pill:SetBackdropBorderColor(r, g, b, a or 1)
    end
end

local function SetRowHover(r, on)
    on = on and true or false
    r.__hlOn = on
    if r.__huiCard then
        if r.__hov then
            for _, t in ipairs(r.__hov) do t:SetShown(on) end
        end
        return
    end
    if on then
        r:SetBackdropColor(1, 1, 1, 0.06)
        r:SetBackdropBorderColor(1, 1, 1, 0.08)
    elseif r.__z then
        r:SetBackdropColor(1, 1, 1, EG.ZEBRA_A)
        r:SetBackdropBorderColor(1, 1, 1, 0)
    else
        r:SetBackdropColor(1, 1, 1, 0)
        r:SetBackdropBorderColor(1, 1, 1, 0)
    end
end

function EG.SyncHover()
    for i, r in pairs(EG.rows or {}) do
        local over = (r.IsMouseOver and r:IsMouseOver()) and true or false
        if over ~= r.__hlOn then SetRowHover(r, over) end
    end
end

local function Row(i)
    local r = EG.rows[i]
    if r then return r end
    r = CreateFrame("Button", nil, EG.child, "BackdropTemplate")
    r:SetWidth(EG.RIGHT_W - 2 * EG.LIST_PAD)
    r.__hlOn = false
    if not HuiRowFX(r, 6, 12) then
        r:SetBackdrop({
            bgFile = "Interface\\Buttons\\WHITE8x8",
        })
    end
    SetRowHover(r, false)
    r:EnableMouse(true)
    r.chk = CreateFrame("Button", nil, r)
    r.chk:SetSize(EG.CHK, EG.CHK)
    r.chk:SetPoint("LEFT", r, "LEFT", 8, 0)
    r.chk.ring = r.chk:CreateTexture(nil, "ARTWORK")
    r.chk.ring:SetAllPoints()
    r.chk.ring:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\CheckRing")
    r.chk.disc = r.chk:CreateTexture(nil, "ARTWORK")
    r.chk.disc:SetAllPoints()
    r.chk.disc:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\CheckDisc")
    r.chk.tickF = r.chk:CreateTexture(nil, "OVERLAY")
    r.chk.tickF:SetAllPoints()
    r.chk.tickF:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\CheckMark")
    r.chk:SetScript("OnClick", function(self, button)
        local id = self:GetParent().__it
        if not id then return end
        local found = Found()
        found[id] = (not found[id]) or nil
        EG.RequestRender()
        ns.PlaySound(1)
    end)
    r.chk:SetScript("OnEnter", function()
        local f = r:GetScript("OnEnter")
        if f then f(r) end
    end)
    r.chk:SetScript("OnLeave", function()
        local f = r:GetScript("OnLeave")
        if f then f(r) end
    end)
    r.strike = r:CreateTexture(nil, "OVERLAY")
    r.strike:SetHeight(1)
    r.strike:SetColorTexture(0.94, 0.71, 0.24, 0.55)
    r.strike:Hide()
    r.icon = r:CreateTexture(nil, "ARTWORK")
    r.icon:SetSize(EG.ICON, EG.ICON)
    r.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
    if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(r.icon) end
    r.icon:SetPoint("LEFT", r, "LEFT", 8 + EG.CHK + 8, 0)
    r.a = MakeFS(r, 14, C_TEXT, "LEFT")
    r.a:SetPoint("TOPLEFT", r, "TOPLEFT", 8 + EG.CHK + 8 + EG.ICON + 10, -5)
    r.unStrike = r:CreateTexture(nil, "OVERLAY")
    r.unStrike:SetHeight(1)
    r.unStrike:SetColorTexture(0.64, 0.61, 0.55, 0.9)
    r.unStrike:Hide()
    r.b = MakeFS(r, 14, C_GREY, "LEFT")
    r.b:SetPoint("BOTTOMLEFT", r, "BOTTOMLEFT", 8 + EG.CHK + 8 + EG.ICON + 10, 4)
    r.c = MakeFS(r, 14, C_GOLD, "RIGHT")
    r.c:SetPoint("TOPRIGHT", r, "TOPRIGHT", -8, -5)
    r.d = MakeFS(r, 14, C_GREY, "RIGHT")
    r.d:SetPoint("RIGHT", r.c, "LEFT", -6, 0)
    r.d2 = MakeFS(r, 14, C_GREY, "RIGHT")
    r.arr = MakeFS(r, 14, C_GREY, "RIGHT")
    r.c2 = MakeFS(r, 14, C_GOLD, "RIGHT")
    for _, f in ipairs({ r.a, r.b, r.c, r.d, r.d2, r.arr, r.c2 }) do f:SetWordWrap(false) end
    r.s1 = CreateFrame("Button", nil, r)
    r.s2 = CreateFrame("Button", nil, r)
    for _, bt in ipairs({ r.s1, r.s2 }) do
        bt:SetHeight(EG.ROW_H)
        bt:Hide()
        bt:SetScript("OnClick", function(self)
            local loc = self.__loc
            if loc then EG.MarkPoint(loc[1], loc[2], loc[3]) end
            ns.PlaySound(1)
        end)
        bt:SetScript("OnEnter", function(self)
            SetRowHover(r, true)
            if self.__fs then self.__fs:SetTextColor(Unpack(C_TEXT)) end
        end)
        bt:SetScript("OnLeave", function(self)
            SetRowHover(r, false)
            if self.__fs then self.__fs:SetTextColor(Unpack(C_GOLD)) end
        end)
    end
    r.sep = r:CreateTexture(nil, "BACKGROUND")
    r.sep:SetHeight(1)
    r.sep:SetColorTexture(1, 1, 1, 0.055)
    r:SetScript("OnEnter", function(self)
        SetRowHover(self, true)
    end)
    r:SetScript("OnLeave", function(self)
        SetRowHover(self, false)
    end)
    r:SetScript("OnClick", function(self, button)
        if self.__mark then self.__mark() end
        if ns.ExploreMapTrackBook and self.__rec then
            pcall(ns.ExploreMapTrackBook, self.__rec)
        end
        ns.PlaySound(1)
    end)
    r:EnableMouseWheel(true)
    r:SetScript("OnMouseWheel", function(_, delta)
        DG.WheelScroll(EG.scroll, EG.child, delta)
    end)
    EG.rows[i] = r
    return r
end

local FAC_PILL = {
    A = { 0.45, 0.71, 1.0, 0.13, 0.32, 0.55 },
    H = { 0.95, 0.42, 0.40, 0.55, 0.16, 0.15 },
}
local PILL_PREV = { lvTag = "fTag", recTag = "lvTag", unTag = "lvTag" }
local PILL_STORE = setmetatable({}, { __mode = "k" })
local function PillGet(r, key)
    local st = PILL_STORE[r]
    return st and st[key] or nil
end
local function MakeTagPill(r, key)
    local okc, p = pcall(CreateFrame, "Frame", nil, r, "BackdropTemplate")
    if not okc then error("P1-create: " .. tostring(p), 0) end
    local okh, e2 = pcall(function()
        p:SetHeight(16)
        p:SetBackdrop({
            bgFile = "Interface\\Buttons\\WHITE8x8",
            edgeFile = "Interface\\Buttons\\WHITE8x8",
            edgeSize = 1,
        })
        if not HuiPillFX(p, 8, { 0.29, 0.27, 0.24, 0.9 }) then
            p:SetBackdropColor(0, 0, 0, 0.22)
            p:SetBackdropBorderColor(0.29, 0.27, 0.24, 0.9)
        end
        local t = MakeFS(p, 12, nil, "CENTER")
        t:SetAllPoints()
        t:SetWordWrap(false)
        p.t = t
        p:Hide()
    end)
    if not okh then error("P2-body: " .. tostring(e2), 0) end
    local st = PILL_STORE[r]
    if not st then st = {}; PILL_STORE[r] = st end
    st[key] = p
    return p
end
local function PaintPill(r, key, txt, show, tR, tG, tB, eR, eG, eB)
    local p = PillGet(r, key)
    if not show then
        if p then p:Hide() end
        return
    end
    local oka, ea = pcall(function()
        if not p then p = MakeTagPill(r, key) end
        local pk = PILL_PREV[key]
        local prev = pk and PillGet(r, pk) or nil
        if prev and prev.IsShown and prev:IsShown() then
            p:SetPoint("LEFT", prev, "RIGHT", 4, 0)
        else
            p:SetPoint("LEFT", r.a, "RIGHT", 6, 0)
        end
        p.t:SetText(txt)
        p.t:SetTextColor(tR, tG, tB)
        PillEdge(p, eR, eG, eB, 0.9)
        local tw = p.t.GetStringWidth and p.t:GetStringWidth()
        if type(tw) ~= "number" or tw <= 0 then tw = #txt * 4 end
        p:SetWidth(tw + 12)
        p:Show()
    end)
    if not oka then error("PP-" .. key .. ": " .. tostring(ea), 0) end
end
function EG.PillOf(row, key)
    return PillGet(row, key)
end

local function PaintCoords(r, rec)
    local route = rec[8]
    local last = route and route[#route] or nil
    r.c:SetText(format("%.1f, %.1f", last and last[2] or rec[3] or 0,
                                      last and last[3] or rec[4] or 0))
    r.d:SetText(EG.ZoneName(rec[2], tostring(rec[2] or "")))
    r.c2:SetText("")
    r.arr:SetText("")
    r.d2:SetText("")
    r.s1.__loc = nil
    r.s2.__loc = nil
    r.s1:Hide()
    r.s2:Hide()
    r.d:ClearAllPoints()
    r.d:SetPoint("RIGHT", r.c, "LEFT", -6, 0)
    if route and #route >= 2 then
        local s1 = route[1]
        local zn1 = EG.ZoneName(s1[1], tostring(s1[1] or ""))
        local zn2 = EG.ZoneName(last[1], tostring(last[1] or ""))
        if zn1 ~= zn2 then r.d:SetText(zn1) end
        r.c2:SetText(format("%.1f, %.1f", s1[2] or 0, s1[3] or 0))
        r.arr:SetText("→")
        if zn1 == zn2 then
            r.arr:ClearAllPoints()
            r.arr:SetPoint("RIGHT", r.c, "LEFT", -4, 0)
        else
            r.d2:SetText(zn2)
            r.d2:ClearAllPoints()
            r.d2:SetPoint("RIGHT", r.c, "LEFT", -6, 0)
            r.arr:ClearAllPoints()
            r.arr:SetPoint("RIGHT", r.d2, "LEFT", -4, 0)
        end
        r.c2:ClearAllPoints()
        r.c2:SetPoint("RIGHT", r.arr, "LEFT", -4, 0)
        r.d:ClearAllPoints()
        r.d:SetPoint("RIGHT", r.c2, "LEFT", -6, 0)
        r.s1.__loc = s1
        r.s2.__loc = last
    end
    local function pin(bt, fs)
        local txt = fs:GetText()
        if not txt or txt == "" then return end
        local w = fs.GetStringWidth and fs:GetStringWidth()
        if type(w) ~= "number" or w <= 0 then w = #txt * 7 end
        bt:ClearAllPoints()
        bt:SetPoint("TOPLEFT", fs, "TOPLEFT", -2, 0)
        bt:SetPoint("BOTTOMRIGHT", fs, "BOTTOMRIGHT", 2, 0)
        bt:EnableMouse(true)
        bt:Show()
    end
    pin(r.s1, r.c2)
    if route and #route >= 2 then
        pin(r.s2, r.c)
    end
end

local function PaintRow(r, idx, y, rec, zebra)
    r.__idx = idx
    r:ClearAllPoints()
    r:SetPoint("TOPLEFT", EG.child, "TOPLEFT", EG.LIST_PAD, -y)
    r:SetHeight(EG.ROW_H)
    r.sep:ClearAllPoints()
    r.sep:SetPoint("BOTTOMLEFT", r, "BOTTOMLEFT", 0, 0)
    r.sep:SetPoint("BOTTOMRIGHT", r, "BOTTOMRIGHT", 0, 0)
    r.sep:SetShown(not r.__huiCard)
    r:Show()
    r.chk:Show()

    local id = rec[1]
    local name, ok = DG.ItemName(id)
    if not ok then EG.needNames = true end
    r.a:SetText(name)
    r.b:SetText(rec[5] or "")
    PaintCoords(r, rec)

    local isRec = ns.ExploreRecIDs and ns.ExploreRecIDs[id] and true or false
    local isUnver = ns.ExploreUnverIDs and ns.ExploreUnverIDs[id] and true or false
    local terr = BookTerr(rec)
    if terr == "A" or terr == "H" then
        local c = FAC_PILL[terr]
        PaintPill(r, "fTag", terr == "A" and L["联盟领地"] or L["部落领地"], true,
                  c[1], c[2], c[3], c[4], c[5], c[6])
    else
        PaintPill(r, "fTag", "", false)
    end
    local zl = ns.ExploreZoneLv and ns.ExploreZoneLv[rec[2]]
    local lvTxt = nil
    if zl == ns.DL("主城") then
        lvTxt = L["主城"]
    elseif type(zl) == "string" and zl ~= "" then
        lvTxt = zl .. L["级"]
    end
    PaintPill(r, "lvTag", lvTxt or "", lvTxt ~= nil, 0.64, 0.61, 0.55, 0.29, 0.27, 0.24)
    PaintPill(r, "recTag", L["推荐"], isRec, 1, 0.82, 0, 0.54, 0.43, 0.06)
    PaintPill(r, "unTag", L["待确认"], isUnver and not isRec, 0.64, 0.61, 0.55, 0.29, 0.27, 0.24)
    if isUnver and not isRec then
        r.unStrike:ClearAllPoints()
        r.unStrike:SetPoint("LEFT", r.a, "LEFT", 0, 0)
        r.unStrike:SetPoint("RIGHT", r.a, "RIGHT", 0, 0)
        r.unStrike:Show()
    else
        r.unStrike:Hide()
    end

    local manual = EG.found and EG.found[id] or nil
    local autoSt = EG._auto and EG._auto[id] or nil
    local done = (manual or autoSt == "quest") and true or false
    local inbag = (autoSt == "bag") and true or false
    if done then
        r.chk.ring:Hide()
        r.chk.disc:Show()
        r.chk.disc:SetVertexColor(Unpack(C_DONE))
        r.chk.tickF:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\CheckTicks2")
        r.chk.tickF:Show()
        r.chk.tickF:SetVertexColor(1, 1, 1, 1)
    elseif inbag then
        r.chk.ring:Hide()
        r.chk.disc:Show()
        r.chk.disc:SetVertexColor(Unpack(C_GREEN))
        r.chk.tickF:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\CheckMark")
        r.chk.tickF:Show()
        r.chk.tickF:SetVertexColor(1, 1, 1, 1)
    else
        r.chk.disc:Hide()
        r.chk.tickF:Hide()
        r.chk.ring:Show()
        r.chk.ring:SetVertexColor(0.42, 0.41, 0.38, 0.9)
    end
    r.a:SetTextColor(Unpack(done and C_DIM or (isUnver and not isRec and C_GREY or C_TEXT)))
    r.strike:ClearAllPoints()
    local w = r.a.GetStringWidth and r.a:GetStringWidth()
    if done and type(w) == "number" and w > 4 then
        r.strike:SetWidth(w + 8)
        r.strike:SetPoint("LEFT", r.a, "LEFT", -2, 0)
        r.strike:Show()
    else
        r.strike:Hide()
    end
    r:SetAlpha(done and 0.55 or 1)

    local ic = DG.ItemIcon(id)
    if type(ic) == "number" then
        r.icon:SetTexture(ic)
    elseif type(ic) == "string" and ic ~= "" then
        r.icon:SetTexture("Interface\\Icons\\" .. ic)
    else
        r.icon:SetTexture("Interface\\Icons\\" .. tostring(FALLBACK_ICON))
    end

    r.__it = id
    r.__rec = rec
    r.__mark = function() EG.MarkPoint(rec[2], rec[3], rec[4]) end

    r.__z = zebra and true or false
    SetRowHover(r, false)
end

function EG.SweepNames()
    if not EG.built then EG._sweepQueued = false return end
    EG.needNames = false
    local miss = 0
    local function Probe(id)
        if not id then return end
        local _, ok = DG.ItemName(id)
        if not ok then
            miss = miss + 1
            EG.needNames = true
            if DG.RequestItem then DG.RequestItem(id) end
        end
    end
    for i = 1, #(EG.pool or {}) do
        local rec = EG.pool[i]
        if rec then Probe(rec[1]) end
    end
    for _, id in ipairs(EG.bmNameIds or {}) do Probe(id) end
    for _, c in ipairs(EG.bagChips or {}) do Probe(c.__id) end
    for _, nb in ipairs(EG.bagNoteItems or {}) do Probe(nb.__id) end
    local csub = CurSub()
    if csub == "pets" or csub == "torch" or csub == "banner" then
        local ids = (csub == "torch" and EG.toyIds) or (csub == "banner" and EG.bannerIds) or EG.petIds
        for _, id in ipairs(ids or {}) do Probe(id) end
        if csub == "torch" and #TOYS > 0 then
            for _, st in ipairs(TOYS[1][9] or {}) do
                if st.q and not ToyQuestTitle(st.q) then miss = miss + 1; EG.needNames = true end
            end
        end
    end
    local prevMiss = EG._sweepMiss
    EG._sweepMiss = miss
    if not prevMiss or miss < prevMiss then
        EG._sweepFails = 0
    else
        EG._sweepFails = math.min((EG._sweepFails or 0) + 1, 6)
    end
    local onScreen = ns.PageVisible(EG.page)
    if not prevMiss or miss < prevMiss or (miss > 0 and onScreen) then EG.RequestRender() end
    if EG.needNames then
        EG.ScheduleSweep()
    else
        EG._sweepQueued = false
    end
end

function EG.OnItemData(itemID)
    if not EG.built or not itemID then return end
    if not ns.PageVisible(EG.page) then return end
    if not EG.needNames or EG._itemRepaint then return end
    local evtNow = (type(GetTime) == "function") and GetTime() or 0
    if EG.__evtT and (evtNow - EG.__evtT) < 1 then return end
    EG.__evtT = evtNow
    EG._itemRepaint = true
    if type(C_Timer) == "table" and type(C_Timer.After) == "function" then
        C_Timer.After(0.05, function()
            EG._itemRepaint = false
            if EG.needNames then EG.SweepNames() end
        end)
    else
        EG._itemRepaint = false
    end
end

function EG.OnQuestData(qid)
    if not EG.built or not qid then return end
    if not ns.PageVisible(EG.page) then return end
    local cs = CurSub()
    if cs ~= "bag" and cs ~= "pets" and cs ~= "torch" and cs ~= "banner" then return end
    if EG.__qRepaint then return end
    EG.__qRepaint = true
    if type(C_Timer) == "table" and type(C_Timer.After) == "function" then
        C_Timer.After(0.05, function()
            EG.__qRepaint = false
            if not ns.PageVisible(EG.page) then return end
            EG.RequestRender()
        end)
    else
        EG.__qRepaint = false
        EG.RequestRender()
    end
end

do
    local hl = DG.__qDataHooks
    if hl and not hl.__exploreChain then
        hl.__exploreChain = EG.OnQuestData
        hl[#hl + 1] = hl.__exploreChain
    end
end

function EG.ScheduleSweep()
    if EG._sweepQueued then return end
    if type(C_Timer) ~= "table" or type(C_Timer.After) ~= "function" then return end
    if (EG._sweepFails or 0) >= 6 then return end
    EG._sweepQueued = true
    local wait = 1.0
    for _ = 1, (EG._sweepFails or 0) do wait = wait * 2 end
    if wait > 10 then wait = 10 end
    C_Timer.After(wait, function()
        EG._sweepQueued = false
        EG.SweepNames()
    end)
end

local function PaintFilter(bt, sel)
    SetButtonSelected(bt, sel)
    local fs = bt:GetFontString()
    if bt.__baseColor then
        local c = bt.__baseColor
        local m = sel and 1.25 or 0.92
        fs:SetTextColor(min(1, c[1] * m), min(1, c[2] * m), min(1, c[3] * m))
    else
        fs:SetTextColor(Unpack(sel and C_GOLD or C_DIM))
    end
end

function EG.PickFilter()
    for _, f in ipairs(EG.FILTERS) do
        local bt = EG.filterBtns[f.key]
        if bt then PaintFilter(bt, f.key == EG.view) end
    end
end

local function PaintNav()
    local cur = CurSub()
    for key, bt in pairs(EG.navBtns or {}) do
        local sel = (key == "books" and (cur == "books" or cur == "rewards")) or (key == cur)
        SetButtonSelected(bt, sel)
        local fs = bt.GetFontString and bt:GetFontString()
        if fs then fs:SetTextColor(Unpack(sel and C_WHITE or C_DIM)) end
    end
    if EG.navBooks and EG.navBooks.__pv then
        local n = 0
        for _, rec in ipairs(B) do
            if IsFound(rec[1]) then n = n + 1 end
        end
        EG.navBooks.__pv:SetText(format("%d/%d", n, #B))
    end
end

local function PaintRwBtn()
    local on = CurSub() == "rewards"
    SetButtonSelected(EG.rwBtn, on)
    local fs = EG.rwBtn.GetFontString and EG.rwBtn:GetFontString()
    if fs then fs:SetTextColor(Unpack(on and C_WHITE or C_RW)) end
end

local function PaintRouteBtn()
    local on = ns.ExploreMapOn and ns.ExploreMapOn() or false
    if not EG.routeBtn then return end
    SetButtonSelected(EG.routeBtn, on)
    local fs = EG.routeBtn.GetFontString and EG.routeBtn:GetFontString()
    if fs then fs:SetTextColor(Unpack(on and C_WHITE or C_RW)) end
end

local QUALITY_COLORS = {
    [0] = { 0.62, 0.62, 0.62 }, [1] = { 1, 1, 1 }, [2] = { 0.12, 1, 0 },
    [3] = { 0, 0.44, 0.87 }, [4] = { 0.64, 0.21, 0.93 }, [5] = { 1, 0.5, 0 },
    [6] = { 0.9, 0.8, 0.5 }, [7] = { 0.76, 0.86, 0.92 },
}
local function QUALITY_COLOR(q)
    if type(q) == "number" then return QUALITY_COLORS[q] or { 1, 1, 1 } end
    return nil
end
local function TierItem(tier, side)
    if tier.choices then return tier.choices[side] end
    return tier.items and tier.items[side]
end

local function PaintRewards()
    for ti, tier in ipairs(REWARDS) do
        local card = EG.rwCards and EG.rwCards[ti]
        if card and card.hd then
            local pat = (tier.at == EG.NECK_AT) and L["%d本 → 项链"]
                or (tier.at == EG.RING_AT) and L["%d本 → 戒指"] or L["%d本 → 三选一"]
            card.hd:SetText(format(pat, tier.at))
        end
        local done = false
        if C_QuestLog and C_QuestLog.IsQuestFlaggedCompleted and tier.questID then
            local okd, d = pcall(C_QuestLog.IsQuestFlaggedCompleted, tier.questID)
            done = okd and d or false
        end
        local stTxt
        if card and card.state then
            stTxt = done and L["任务已完成"] or L["任务未完成"]
            card.state:SetText(stTxt)
            card.state:SetTextColor(Unpack(done and C_GOLD or C_GREY))
        end
        if card and card.lv then
            card.lv:SetText(format(L["要求等级 %d"], tier.req or 0))
            local sw = card.state and card.state.GetStringWidth and card.state:GetStringWidth()
            if type(sw) ~= "number" or sw <= 0 then sw = stTxt and (#stTxt * 7) or 70 end
            card.lv:SetPoint("TOPRIGHT", card, "TOPRIGHT", -(12 + sw + 6), -12)
        end
    end
    if EG.rwMageHead then
        local MB = ns.ExploreMageBonus
        EG.rwMageHead:SetText(MB and MB.title or "")
    end
    for _, row in ipairs(EG.rwRows or {}) do
        local tier, side = row.tier, row.side
        local id = tier and TierItem(tier, side) or nil
        local nm, ok
        if id then nm, ok = DG.ItemName(id) end
        local q = id and DG.QualOf(id) or nil
        row.__it = id
        row.__resolved = ok
        local ic = id and DG.ItemIcon(id) or nil
        if type(ic) == "number" then
            row.icon:SetTexture(ic)
        elseif type(ic) == "string" and ic ~= "" then
            row.icon:SetTexture("Interface\\Icons\\" .. ic)
        else
            row.icon:SetTexture("Interface\\Icons\\" .. tostring(FALLBACK_ICON))
        end
        row.name:SetText(nm or "?")
        row.name:SetTextColor(Unpack(ok and (q and QUALITY_COLOR(q) or C_TEXT) or C_DIM))
        if not ok then EG.needNames = true end
        local iLvl, reqLvl
        if ok and id then
            local _, _, _, iv, rv = DG.ItemInfo(id)
            iLvl, reqLvl = iv, rv
        end
        local parts = {}
        if ok and id then
            local mt = DG.ItemMeta(id)
            if type(mt) == "string" and mt ~= "" then parts[#parts + 1] = mt end
        end
        if type(iLvl) == "number" and iLvl > 0 then parts[#parts + 1] = format(L["装等%d"], iLvl) end
        if type(reqLvl) == "number" and reqLvl > 0 then parts[#parts + 1] = format(L["需要等级 %d"], reqLvl) end
        row.meta:SetText(#parts > 0 and table.concat(parts, " · ") or "")
        row.meta:SetTextColor(Unpack(C_GREY))
        local plv = type(UnitLevel) == "function" and UnitLevel("player") or nil
        if type(reqLvl) == "number" and reqLvl > 0
            and type(plv) == "number" and reqLvl > plv then
            row.meta:SetTextColor(0.94, 0.31, 0.31, 1)
        end
    end
end

function EG.RewardTip(row, on)
    if not on then
        if GameTooltip then pcall(GameTooltip.Hide, GameTooltip) end
        return
    end
    if not GameTooltip then return end
    GameTooltip:SetOwner(row, "ANCHOR_RIGHT")
    GameTooltip:ClearLines()
    local tier = row.tier
    local id = tier and TierItem(tier, row.side) or nil
    local link = id and DG.ItemLink(id) or nil
    local shown = false
    if link then
        local ok = pcall(GameTooltip.SetHyperlink, GameTooltip, link)
        shown = ok and type(GameTooltip.NumLines) == "function"
            and (GameTooltip:NumLines() or 0) > 0
    end
    if not shown then
        local nm = id and DG.ItemName(id) or nil
        GameTooltip:AddLine(nm or "?", 0.8, 0.8, 0.8, true)
    end
    if tier.quest then
        local qname = tier.quest
        if tier.questID and C_QuestLog then
            local okt, t
            if type(C_QuestLog.GetTitleForQuestID) == "function" then
                okt, t = pcall(C_QuestLog.GetTitleForQuestID, tier.questID)
                if okt and type(t) ~= "string" then t = nil end
            end
            if (not okt or not t) and type(C_QuestLog.GetQuestInfo) == "function" then
                local okq, info = pcall(C_QuestLog.GetQuestInfo, tier.questID)
                if okq and type(info) == "table" and type(info.title) == "string" then
                    t = info.title
                end
            end
            if t and t ~= "" then qname = t end
        end
        GameTooltip:AddLine(qname, 0.55, 0.75, 0.55, true)
    end
    GameTooltip:Show()
end

local function PaintProgress()
    local n, total = 0, #B
    for _, rec in ipairs(B) do
        if IsFound(rec[1]) then n = n + 1 end
    end
    local m = 0
    for _, rec in ipairs(B) do
        if EG._auto and EG._auto[rec[1]] == "quest" then m = m + 1 end
    end
    EG.prog:SetText(format(L["已找到 %d / %d · 已提交 %d / %d"], n, total, m, total))
    if EG.barFill then
        EG.barFill:SetWidth(math.floor(EG.BAR_W * n / total + 0.5))
    end
    for _, at in ipairs({ EG.NECK_AT, EG.RING_AT, EG.CHOICE_AT }) do
        local lab = EG.tickLabs and EG.tickLabs[at]
        if lab then lab:SetTextColor(Unpack((n >= at) and C_GOLD or C_DIM)) end
    end
end

local BAG_FAC_COL = { A = { 0.45, 0.68, 0.98 }, H = { 0.95, 0.5, 0.45 } }
local BAG_FAC_ICON = {
    A = "Interface\\AddOns\\DungeonsForever\\Media\\icon\\FACTION\\FactionIcon_Alliance",
    H = "Interface\\AddOns\\DungeonsForever\\Media\\icon\\FACTION\\FactionIcon_Horde",
}

local function BagRowTint(r)
    local t = r.tint
    if not t then return end
    if r.__hov then
        for _, htx in ipairs(r.__hov) do htx:SetShown(r.__hl or r.__sel or false) end
    end
    if not r.__huiCard then
        if r.__sel then
            t:SetColorTexture(1, 0.82, 0, 0.12)
            t:Show()
        elseif r.__hl then
            t:SetColorTexture(1, 1, 1, 0.07)
            t:Show()
        else
            t:Hide()
        end
    else
        t:Hide()
    end
end

local function PaintBagRow(r, e, fac)
    local loc = BagStep(e, fac)
    local qid = type(e.q) == "table" and e.q[fac] or e.q
    local st = BagQuestState(qid)
    r.no:SetText(e.no)
    r.no:SetTextColor(Unpack(e.optional and C_GREY or C_GOLD))
    r.t:SetText(BagQuestTitle(e, fac))
    r.t:SetTextColor(Unpack(e.optional and C_GREY or (st == 2 and C_DIM or C_TEXT)))
    r.p:SetText(loc.zn or "")
    r.st:SetText(st == 2 and L["已完成"] or (st == 1 and L["已接取"] or L["未完成"]))
    r.st:SetTextColor(Unpack(st == 2 and C_GREEN or (st == 1 and C_GOLD or C_GREY)))
    r.__sel = (EG.bagSel == e.key)
    BagRowTint(r)
end

local function PaintChip(c, id, note)
    c.__id, c.__note = id, note
    local nm, ok = DG.ItemName(id)
    if not ok then EG.needNames = true end
    c.nm:SetText(nm or "?")
    local q = DG.QualOf and DG.QualOf(id) or nil
    c.nm:SetTextColor(Unpack((ok and q and QUALITY_COLOR(q)) or (ok and C_TEXT or C_DIM)))
    local ic = DG.ItemIcon(id)
    if type(ic) == "number" then
        c.icon:SetTexture(ic)
    elseif type(ic) == "string" and ic ~= "" then
        c.icon:SetTexture("Interface\\Icons\\" .. ic)
    else
        c.icon:SetTexture("Interface\\Icons\\" .. tostring(FALLBACK_ICON))
    end
    local w = c.nm.GetStringWidth and c.nm:GetStringWidth() or 0
    w = (type(w) == "number" and w or 0) + 4 + 24 + 5 + 6
    c:SetWidth(math.max(w, 40))
end

function EG.BagChipTip(c, on)
    if not on then
        if GameTooltip then pcall(GameTooltip.Hide, GameTooltip) end
        return
    end
    if not GameTooltip then return end
    GameTooltip:SetOwner(c, "ANCHOR_RIGHT")
    GameTooltip:ClearLines()
    local id = c.__id
    local link = id and DG.ItemLink and DG.ItemLink(id) or nil
    local shown = false
    if link then
        local ok = pcall(GameTooltip.SetHyperlink, GameTooltip, link)
        shown = ok and type(GameTooltip.NumLines) == "function"
            and (GameTooltip:NumLines() or 0) > 0
    end
    if not shown then
        local nm = id and DG.ItemName(id) or nil
        GameTooltip:AddLine(nm or "?", 0.8, 0.8, 0.8, true)
    end
    if c.__note and not tostring(c.__note):find(L["选一"], 1, true) then
        GameTooltip:AddLine(c.__note, 0.55, 0.75, 0.55, true)
    end
    GameTooltip:Show()
end

local function FlowChips(y, list, idx0)
    local x, idx = 8, idx0
    for _, it in ipairs(list) do
        idx = idx + 1
        local c = EG.bagChips and EG.bagChips[idx]
        if not c then break end
        PaintChip(c, it[1], it.note or it[2])
        local w = c:GetWidth()
        if x > 8 and x + w > (EG.bagRWd or 0) - 8 then x, y = 8, y + 36 end
        c:ClearAllPoints()
        c:SetPoint("TOPLEFT", EG.bagChild, "TOPLEFT", x, -y)
        c:Show()
        x = x + w + 8
    end
    return y + (x > 8 and 36 or 0), idx
end

local function HideChips(from)
    for i = from, #(EG.bagChips or {}) do EG.bagChips[i]:Hide() end
end

local function PaintBagDetail(fac)
    local det = EG.bagDetail
    if not det then return end
    local e = BAG_CHAIN[1]
    for _, ce in ipairs(BAG_CHAIN) do
        if ce.key == EG.bagSel then e = ce break end
    end
    local loc, qid = BagStep(e, fac)
    EG.bagDT:SetText(BagQuestTitle(e, fac))
    if EG.bagDId then EG.bagDId:SetText(qid and ("#" .. qid) or "") end
    local co = EG.bagDCo
    if co then
        co.__loc = loc.x and loc or nil
        co.fs:SetText(loc.x and format("%.1f, %.1f", loc.x, loc.y) or "—")
        local w = co.fs.GetStringWidth and co.fs:GetStringWidth() or 0
        co:SetWidth(math.max((type(w) == "number" and w or 0) + 8, 30))
        if EG.bagDCoHint then EG.bagDCoHint:SetShown(co.__loc ~= nil) end
    end
    local st = BagQuestState(qid)
    local stateTxt = st == 2 and L["已完成"] or (st == 1 and L["已接取"] or L["未完成"])
    EG.bagDV[1]:SetText(stateTxt)
    EG.bagDV[1]:SetTextColor(Unpack(st == 2 and C_GREEN or C_GOLD))
    EG.bagDV[2]:SetText(format(L["%d 级可接 · 任务等级 Lv%d"], BAG_REQ_LVL, BAG_QUEST_LVL))
    EG.bagDV[3]:SetText(format(L["由物件「%s」起始"], loc.obj or "—"))
    local sideTxt = L["两阵营通用"]
    if type(e.q) == "table" then
        sideTxt = (fac == "A") and L["联盟专属"] or L["部落专属"]
    end
    EG.bagDV[4]:SetText(sideTxt)
    local choice, rest = {}, {}
    for _, it in ipairs(e.rw) do
        if it.note and tostring(it.note):find(L["选一"], 1, true) then
            choice[#choice + 1] = it
        else
            rest[#rest + 1] = it
        end
    end
    local h1, h2 = EG.bagDRH, EG.bagDRH2
    local y, idx = 132, 0
    if #e.rw > 0 and h1 and h2 then
        EG.bagDRH0:SetShown(true)
        EG.bagDRH0:ClearAllPoints()
        EG.bagDRH0:SetPoint("TOPLEFT", det, "TOPLEFT", 10, -y)
        y = y + 24
        if #choice > 0 and #rest > 0 then
            h1:ClearAllPoints()
            h1:SetPoint("TOPLEFT", det, "TOPLEFT", 10, -y)
            h1:SetText(L["你可以选择一件："])
            h1:SetShown(true)
            y = y + 22
            y, idx = FlowChips(y, choice, idx)
            y = y + 8
            h2:ClearAllPoints()
            h2:SetPoint("TOPLEFT", det, "TOPLEFT", 10, -y)
            h2:SetText(L["你还会获得："])
            h2:SetShown(true)
            y = y + 22
            y, idx = FlowChips(y, rest, idx)
        else
            h1:SetShown(false)
            h2:SetShown(false)
            y, idx = FlowChips(y, e.rw, idx)
        end
    else
        EG.bagDRH0:SetShown(false)
        h1:SetShown(false)
        h2:SetShown(false)
    end
    HideChips(idx + 1)
    y = y + 6
    EG.bagDXH:ClearAllPoints()
    EG.bagDXH:SetPoint("TOPLEFT", det, "TOPLEFT", 10, -y)
    EG.bagDXH:SetShown(true)
    y = y + 22
    EG.bagDX:ClearAllPoints()
    EG.bagDX:SetPoint("TOPLEFT", det, "TOPLEFT", 10, -y)
    DG.RequestQuestRewardData(qid)
    local apiXp = qid and DG.QuestRewardXP(qid) or nil
    if apiXp then
        EG.bagDX:SetText(format(L["%s 经验"], Comma(apiXp)))
    elseif DG.GAINS_FALLBACK or not e.xp then
        EG.bagDX:SetText(e.xp and format(L["%s 经验"], Comma(e.xp)) or "—")
    else
        EG.bagDX:SetText("")
    end
    DG.__bagGains = { questID = qid, sig = DG.QuestDataSig(qid), apply = function() PaintBagDetail(fac) end }
    y = y + 24
    EG.bagDNH:ClearAllPoints()
    EG.bagDNH:SetPoint("TOPLEFT", det, "TOPLEFT", 10, -y)
    EG.bagDNH:SetShown(true)
    y = y + 22
    local segs = (type(e.note) == "table") and e.note or nil
    if segs then
        EG.bagDN:SetShown(false)
        local pool = EG.bagNSegs or {}
        local avail = (EG.bagRWd or 700) - 20
        local nx, used = 0, 0
        for si, seg in ipairs(segs) do
            used = si
            local item = pool[si]
            if not item then break end
            if type(seg) == "table" then
                local b = item.btn
                b.__loc = { area = seg[1], x = seg[2], y = seg[3] }
                b.fs:SetText(format("%d, %d", seg[2], seg[3]))
                local w = b.fs.GetStringWidth and b.fs:GetStringWidth() or 0
                b:SetWidth(math.max((type(w) == "number" and w or 0) + 8, 34))
                local bw = b:GetWidth()
                if nx > 0 and nx + bw > avail then nx, y = 0, y + 24 end
                b:ClearAllPoints()
                b:SetPoint("TOPLEFT", det, "TOPLEFT", 10 + nx, -y)
                b:SetShown(true)
                item.fs:SetShown(false)
                nx = nx + bw + 2
            else
                local f = item.fs
                f:SetText(tostring(seg))
                local w = f.GetStringWidth and f:GetStringWidth() or 0
                w = (type(w) == "number" and w or 0)
                if w <= avail - nx then
                    f:ClearAllPoints()
                    f:SetPoint("TOPLEFT", det, "TOPLEFT", 10 + nx, -y)
                    f:SetPoint("RIGHT", det, "RIGHT", -10, 0)
                    nx = nx + w + 2
                else
                    if nx > 0 then nx, y = 0, y + 22 end
                    f:ClearAllPoints()
                    f:SetPoint("TOPLEFT", det, "TOPLEFT", 10, -y)
                    f:SetPoint("RIGHT", det, "RIGHT", -10, 0)
                    local h = f.GetStringHeight and f:GetStringHeight() or 0
                    if type(h) ~= "number" or h < 22 then
                        h = math.max(1, math.ceil(w / avail)) * 22
                    end
                    y = y + h
                    nx = 0
                end
                f:SetShown(true)
                item.btn:SetShown(false)
            end
        end
        for i = used + 1, #pool do
            pool[i].fs:SetShown(false)
            pool[i].btn:SetShown(false)
        end
        y = y + 26
    else
        for _, pi in ipairs(EG.bagNSegs or {}) do
            pi.fs:SetShown(false)
            pi.btn:SetShown(false)
        end
        EG.bagDN:ClearAllPoints()
        EG.bagDN:SetPoint("TOPLEFT", det, "TOPLEFT", 10, -y)
        EG.bagDN:SetPoint("RIGHT", det, "RIGHT", -10, 0)
        EG.bagDN:SetText(e.note or "")
        EG.bagDN:SetShown(true)
        y = y + 24
    end
    EG.bagTotal:SetShown(false)
    det:SetShown(true)
    det:SetHeight(math.max(y + 10, EG.bagViewH or 300))
end

local function PaintBagTotal()
    local tot = EG.bagTotal
    if not tot then return end
    EG.bagDetail:SetShown(false)
    tot:SetShown(true)
    local id = BAG_FINAL_ID
    local nm, ok = DG.ItemName(id)
    if not ok then EG.needNames = true end
    EG.bagFName:SetText(nm or "?")
    local q = DG.QualOf and DG.QualOf(id) or 3
    EG.bagFName:SetTextColor(Unpack(QUALITY_COLOR(q)))
    local ic = DG.ItemIcon(id)
    if type(ic) == "number" then
        EG.bagFIcon:SetTexture(ic)
    elseif type(ic) == "string" and ic ~= "" then
        EG.bagFIcon:SetTexture("Interface\\Icons\\" .. ic)
    else
        EG.bagFIcon:SetTexture("Interface\\Icons\\" .. tostring(FALLBACK_ICON))
    end
    local y, idx = 140, 0
    for gi, g in ipairs(BAG_RW_GROUPS) do
        local gh = EG.bagTotHeads and EG.bagTotHeads[gi]
        if gh then
            gh:ClearAllPoints()
            gh:SetPoint("TOPLEFT", tot, "TOPLEFT", 10, -y)
        end
        y = y + 24
        y, idx = FlowChips(y, g.items, idx)
        y = y + 8
    end
    HideChips(idx + 1)
    tot:SetHeight(math.max(y + 6, EG.bagViewH or 300))
end

local function PaintBag()
    local fac = BagFac()
    for _, nb in ipairs(EG.bagNoteItems or {}) do
        PaintChip(nb, nb.__id, nil)
    end
    for f, bt in pairs(EG.bagFacBtns or {}) do
        local sel = (f == fac)
        SetButtonSelected(bt, sel)
        local fs = bt.GetFontString and bt:GetFontString()
        if fs then fs:SetTextColor(Unpack(sel and C_WHITE or C_GREY)) end
        if bt.__icon then bt.__icon:SetAlpha(sel and 1 or 0.55) end
    end
    local done = 0
    for _, e in ipairs(BAG_CHAIN) do
        local _, qid = BagStep(e, fac)
        if BagQuestState(qid) == 2 then done = done + 1 end
    end
    if EG.bagProg then
        EG.bagProg:SetText(format(L["进度 %d / %d"], done, #BAG_CHAIN))
    end
    if not EG.bagSel then
        for _, e in ipairs(BAG_CHAIN) do
            local _, qid = BagStep(e, fac)
            if BagQuestState(qid) < 2 then EG.bagSel = e.key break end
        end
        EG.bagSel = EG.bagSel or BAG_CHAIN[1].key
    end
    for i, e in ipairs(BAG_CHAIN) do
        local r = EG.bagRows and EG.bagRows[i]
        if r then PaintBagRow(r, e, fac) end
    end
    local on = EG.bagMode == "total"
    local eb = EG.bagRwBtn
    if eb then
        SetButtonSelected(eb, on)
        local fs = eb.GetFontString and eb:GetFontString()
        if fs then fs:SetTextColor(Unpack(on and C_WHITE or C_DIM)) end
    end
    if EG.bagDetail and EG.bagTotal then
        if on then PaintBagTotal() else PaintBagDetail(fac) end
    end
    if EG.needNames then EG.ScheduleSweep() end
end

local function BagLayoutRows()
    local lc = EG.bagLC
    if not lc then return end
    local ok, h = pcall(lc.GetHeight, lc)
    h = (ok and type(h) == "number" and h > 100 and h) or 316
    local n = #BAG_CHAIN
    local gap = 4
    local rh = (h - (n - 1) * gap) / n
    for i, r in ipairs(EG.bagRows or {}) do
        r:SetHeight(rh)
        r:ClearAllPoints()
        r:SetPoint("TOPLEFT", lc, "TOPLEFT", 8, -((i - 1) * (rh + gap)))
        r:SetPoint("TOPRIGHT", lc, "TOPRIGHT", -8, -((i - 1) * (rh + gap)))
    end
end
EG.BagLayoutRows = BagLayoutRows

local ROUTES = ns.ExploreRoutes or { h = {}, a = {} }
local RT_KIND_TXT = {
    die = { L["送死"], { 0.78, 0.14, 0.12, 1 } },
    grave = { L["复活"], { 0.16, 0.52, 0.26, 1 } },
    fp = { L["飞行点"], { 0.78, 0.60, 0.10, 1 } },
    travel = { L["位移"], { 0.18, 0.45, 0.66, 1 } },
    item = { L["中转"], { 0.36, 0.39, 0.44, 1 } },
}
local RT_LIST_W = 300
EG.RT_LIST_W = RT_LIST_W
EG.RT_GAP, EG.RT_PAD = 8, 8
EG.RT_BODY_W = EG.RIGHT_W - RT_LIST_W - EG.RT_GAP
EG.RT_STEP_W = EG.RT_BODY_W - 2 * EG.RT_PAD
EG.RT_BODY_H = 294
EG.RT_MAX_TARGETS, EG.RT_MAX_STEPS = 10, 14
local RT_PIN_ATLAS = "Waypoint-MapPin-Tracked"
EG.RT_GRAVE_NATIVE = "Interface\\RaidFrame\\Raid-Icon-Rez"
EG.RT_GRAVE_OWN = "Interface\\AddOns\\DungeonsForever\\Media\\SpiritPin"
local RT_SIDE_FALLBACK = { 1.00, 0.84, 0.08 }

local function RtFac()
    local id = "h"
    if type(UnitFactionGroup) == "function" then
        local ok, _, eng = pcall(UnitFactionGroup, "player")
        if ok and eng == "Alliance" then id = "a" end
    end
    local db = ns.DB()
    db.explore = db.explore or {}
    local pick = db.explore.rtFac
    if pick ~= "h" and pick ~= "a" then pick = id end
    return pick
end

local function RtSel(fac)
    local db = ns.DB()
    db.explore = db.explore or {}
    local list = ROUTES[fac] or {}
    local n = db.explore.rtSel
    if type(n) == "number" and n >= 1 and n <= #list then return n end
    return 1
end

local function RtRace(fac, idx)
    local db = ns.DB()
    db.explore = db.explore or {}
    local t = (ROUTES[fac] or {})[idx]
    if not t then return 1 end
    local j = db.explore.rtRace and db.explore.rtRace[fac .. ":" .. idx]
    if type(j) == "number" and j >= 1 and j <= #t.races then return j end
    return 1
end

local function RtPick(fac, n)
    local db = ns.DB()
    db.explore = db.explore or {}
    db.explore.rtFac = fac
    db.explore.rtSel = n
    EG.RequestRender()
    ns.PlaySound(1)
end

local function RtPickRace(fac, idx, j)
    local db = ns.DB()
    db.explore = db.explore or {}
    db.explore.rtRace = db.explore.rtRace or {}
    db.explore.rtRace[fac .. ":" .. idx] = j
    EG.RequestRender()
    ns.PlaySound(1)
end

local function RtGo(mapID, x, y)
    if type(x) == "number" and type(y) == "number"
       and UiMapPoint and UiMapPoint.CreateFromCoordinates
       and C_Map and C_Map.SetUserWaypoint then
        local pok, pt = pcall(UiMapPoint.CreateFromCoordinates, mapID, x / 100, y / 100)
        if pok and pt then
            pcall(C_Map.SetUserWaypoint, pt)
            if C_SuperTrack and C_SuperTrack.SetSuperTrackedUserWaypoint then
                pcall(C_SuperTrack.SetSuperTrackedUserWaypoint, false)
            end
        end
    end
    if C_Map and C_Map.OpenWorldMap then
        pcall(C_Map.OpenWorldMap, mapID)
    elseif OpenWorldMap then
        pcall(OpenWorldMap, mapID)
    end
    ns.PlaySound(1)
end

local function RtTip(self, on, x, y)
    if not on then
        if GameTooltip then pcall(GameTooltip.Hide, GameTooltip) end
        return
    end
    if not GameTooltip then return end
    GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
    GameTooltip:ClearLines()
    if x and y then
        GameTooltip:AddLine(format("%.1f, %.1f", x, y), C_GOLD[1], C_GOLD[2], C_GOLD[3], false)
    end
    GameTooltip:AddLine(L["点击在世界地图上定位"], 0.8, 0.8, 0.8, true)
    GameTooltip:Show()
end

local RT_SEL_MIX = nil
if ns.hui and ns.hui.AddThemeCleanup then
    ns.hui.AddThemeCleanup(function() RT_SEL_MIX = nil end)
end

local function RtRowSel(r, on)
    if not (r and r.__huiCard) then return end
    if r.__tintOn ~= on then
        local hui = ns.hui
        local base = hui.layer.L2
        local acc = hui.ACCENT
        if not RT_SEL_MIX then
            RT_SEL_MIX = {
                base[1] * 0.72 + acc[1] * 0.28,
                base[2] * 0.72 + acc[2] * 0.28,
                base[3] * 0.72 + acc[3] * 0.28,
            }
        end
        local c = on and RT_SEL_MIX or base
        for _, t in ipairs(r.__huiCard.fill or {}) do
            local g = t.__huiGlass
            if g then g.c = c end
            if hui.GlassPaint then hui.GlassPaint(t) end
        end
        r.__tintOn = on
    end
    if huiPaintRowSelect then huiPaintRowSelect(r, on) end
    if r.__huiRowSelTex then r.__huiRowSelTex:Hide() end
    if on and r.__hov then
        for _, t in ipairs(r.__hov) do t:SetShown(false) end
    end
end

local function RtThemeRepaint()
    RT_SEL_MIX = nil
    for _, r in ipairs(EG.rtRows or {}) do r.__tintOn = nil end
    for _, st in ipairs(EG.rtSteps or {}) do st.__tintOn = nil end
    local sel = EG.rtStepSel
    for k, st in ipairs(EG.rtSteps or {}) do
        if st and st:IsShown() then RtRowSel(st, k == sel) end
    end
    if EG.RequestRender then EG.RequestRender() end
end
EG.RtThemeRepaint = RtThemeRepaint
if ns.hui and ns.hui.OnThemeChange then ns.hui.OnThemeChange(RtThemeRepaint) end

local function PaintGraveBtn(on)
    local bt = EG.graveBtn
    if not bt then return end
    if on == nil then
        on = ns.ExploreGraveOn and ns.ExploreGraveOn() or false
    end
    bt:SetText(on and L["复活点图钉：开"] or L["复活点图钉：关"])
    if SetButtonSelected then SetButtonSelected(bt, on) end
end

local function RtZoneOf(t)
    if not (t and t.fp) then return "" end
    local zn = string.match(t.fp, "^(.-)%s*·%s") or t.fp
    return (zn:gsub("%s+$", ""))
end

local function RtTailOf(t)
    if not (t and t.fp) then return "" end
    local tl = string.match(t.fp, "%s*·%s*(.+)$")
    if not tl then return "" end
    return (tl:gsub("%s+$", ""))
end

local function RtFullName(t)
    if not t then return "" end
    local zn = RtZoneOf(t)
    if zn == "" then return t.name or "" end
    if zn ~= t.name then return zn .. " " .. t.name end
    local tl = RtTailOf(t)
    if tl ~= "" and tl ~= zn then return zn .. " " .. tl end
    return t.name or ""
end

local function RtMapPaint(mapID, x, y)
    local mp, cv = EG.rtMap, EG.rtMapCanvas
    if not (mp and cv and mapID) then return end
    local pool = EG.rtMapTex or {}
    local pin = EG.rtMapPin
    local zn
    if C_Map and C_Map.GetMapInfo then
        local ok, mi = pcall(C_Map.GetMapInfo, mapID)
        zn = ok and mi and mi.name or nil
    end
    if EG.rtMapCap then
        if x and y then
            EG.rtMapCap:SetText(format("%s  %.1f, %.1f", zn or "", x, y))
        else
            EG.rtMapCap:SetText(zn or "")
        end
    end
    for i = 1, #pool do pool[i]:Hide() end
    if pin then pin:Hide() end
    local layer, texs
    if C_Map and C_Map.GetMapArtLayers then
        local ok, l = pcall(C_Map.GetMapArtLayers, mapID)
        if ok and type(l) == "table" then layer = l[1] end
    end
    if C_Map and C_Map.GetMapArtLayerTextures then
        local ok, r = pcall(C_Map.GetMapArtLayerTextures, mapID, 1)
        if ok and type(r) == "table" then texs = r end
    end
    local lw = layer and layer.layerWidth or 0
    local lh = layer and layer.layerHeight or 0
    local tw = layer and layer.tileWidth or 256
    local th = layer and layer.tileHeight or 256
    if not (texs and lw > 0 and lh > 0 and tw > 0 and th > 0) then return end
    local aw = (mp:GetWidth() or 0) - 16
    local ah = (mp:GetHeight() or 0) - 40
    if aw <= 0 or ah <= 0 then return end
    local S = math.min(aw / lw, ah / lh)
    local dw, dh = lw * S, lh * S
    cv:ClearAllPoints()
    cv:SetPoint("TOP", mp, "TOP", 0, -30)
    cv:SetSize(dw, dh)
    local cols = math.ceil(lw / tw)
    local rows = math.ceil(lh / th)
    local n = 0
    for r = 0, rows - 1 do
        for c = 0, cols - 1 do
            local f = texs[r * cols + c + 1]
            local t = pool[n + 1]
            if f and t then
                n = n + 1
                local w = math.min(tw, lw - c * tw)
                local h = math.min(th, lh - r * th)
                t:ClearAllPoints()
                t:SetPoint("TOPLEFT", cv, "TOPLEFT", c * tw * S, -r * th * S)
                t:SetSize(w * S, h * S)
                t:SetTexture(f)
                t:SetTexCoord(0, w / tw, 0, h / th)
                t:Show()
            end
        end
    end
    local dp = EG.rtMapTexD or {}
    local det = ns.MapDetail and ns.MapDetail[mapID]
    local k = 0
    if det then
        for i = 1, #det, 5 do
            local t = dp[k + 1]
            if not t then break end
            k = k + 1
            local dx, dy = det[i + 1], det[i + 2]
            local sw, sh = det[i + 3], det[i + 4]
            t:ClearAllPoints()
            t:SetPoint("TOPLEFT", cv, "TOPLEFT", dx * S, dy * S)
            t:SetSize(sw * S, sh * S)
            t:SetTexture(det[i])
            t:SetTexCoord(0, 1, 0, 1)
            t:Show()
        end
    end
    for j = k + 1, #dp do dp[j]:Hide() end
    local opool = EG.rtOvlTex or {}
    for i = 1, #opool do opool[i]:Hide() end
    local otg = EG.rtCurTgt
    local olist = otg and otg.ovl
    if type(olist) == "table" and ns.RouteOvl then
        local on = 0
        for i = 1, #olist do
            local od = ns.RouteOvl[olist[i]]
            if od and od[1] == mapID and od[3] and od[4] and opool[on + 1] then
                on = on + 1
                local ot = opool[on]
                ot:ClearAllPoints()
                ot:SetPoint("TOPLEFT", cv, "TOPLEFT", 0, 0)
                ot:SetSize(dw, dh)
                ot:SetTexture(od[2])
                ot:SetTexCoord(0, od[5] / od[3], 0, od[6] / od[4])
                ot:Show()
            end
        end
    end
    local gpool = EG.rtGraveTex or {}
    local ddp = EG.rtGraveDisc or {}
    local drp = EG.rtGraveRing or {}
    local grm = EG.rtGraveRim or {}
    local gdp = EG.rtGraveDot or {}
    local flat = ns.GravePos and ns.GravePos[mapID]
    if ns.ExploreGraveOn and not ns.ExploreGraveOn() then flat = nil end
    local gk = 0
    local gstyle = (ns.ExploreGraveStyle and ns.ExploreGraveStyle()) or "native"
    local circle = (gstyle == "circle")
    local icon = (gstyle == "native") and EG.RT_GRAVE_NATIVE or EG.RT_GRAVE_OWN
    if type(flat) == "table" then
        local gs = circle and math.max(16, math.min(26, dw * 0.052)) or math.max(14, math.min(22, dw * 0.045))
        local isz = circle and gs * 0.68 or gs
        local ds = isz * 0.40
        local doff = ds * 0.30
        for i = 1, #flat - 2, 3 do
            local t = gpool[gk + 1]
            if not t then break end
            gk = gk + 1
            t:SetTexture(icon)
            t:SetSize(isz, isz)
            t:ClearAllPoints()
            t:SetPoint("CENTER", cv, "TOPLEFT", dw * (flat[i] / 100), -dh * (flat[i + 1] / 100))
            t:Show()
            local sc = ns.SideColor
            sc = (sc and (sc[flat[i + 2] or 0] or sc[0])) or RT_SIDE_FALLBACK
            local rim, dot = grm[gk], gdp[gk]
            if rim and dot then
                rim:SetSize(ds * 1.42, ds * 1.42)
                rim:ClearAllPoints()
                rim:SetPoint("CENTER", t, "TOPRIGHT", -doff, -doff)
                rim:Show()
                dot:SetVertexColor(sc[1], sc[2], sc[3], 1)
                dot:SetSize(ds, ds)
                dot:ClearAllPoints()
                dot:SetPoint("CENTER", rim, "CENTER", 0, 0)
                dot:Show()
            end
            local d, ring = ddp[gk], drp[gk]
            if d then
                d:SetShown(circle)
                if circle then
                    d:SetSize(gs, gs)
                    d:ClearAllPoints()
                    d:SetPoint("CENTER", t, "CENTER", 0, 0)
                end
            end
            if ring then
                ring:SetShown(circle)
                if circle then
                    ring:SetSize(gs, gs)
                    ring:ClearAllPoints()
                    ring:SetPoint("CENTER", t, "CENTER", 0, 0)
                end
            end
        end
    end
    for j = gk + 1, #gpool do gpool[j]:Hide() end
    for j = gk + 1, #ddp do ddp[j]:Hide() end
    for j = gk + 1, #drp do drp[j]:Hide() end
    for j = gk + 1, #grm do grm[j]:Hide() end
    for j = gk + 1, #gdp do gdp[j]:Hide() end
    if pin and x and y then
        pin:ClearAllPoints()
        pin:SetPoint("CENTER", cv, "TOPLEFT", dw * (x / 100), -dh * (y / 100))
        pin:Show()
    end
end

function EG.RtPickStep(i)
    local race, tg = EG.rtCurRace, EG.rtCurTgt
    if not (race and race.steps and race.steps[i]) then return end
    EG.rtStepSel = i
    for k = 1, EG.RT_MAX_STEPS do
        local st = EG.rtSteps and EG.rtSteps[k]
        if st and st:IsShown() then RtRowSel(st, k == i) end
    end
    local sd = race.steps[i]
    if sd.x and sd.y then
        local mm = (type(sd.m) == "table" and sd.m[1]) or (tg and tg.mapID)
        RtMapPaint(mm, sd.x, sd.y)
    elseif tg then
        RtMapPaint(tg.mapID)
    end
end

function EG.RtMapRepaint()
    local sel, race, tg = EG.rtStepSel, EG.rtCurRace, EG.rtCurTgt
    local sd = race and race.steps and sel and race.steps[sel]
    if sd then
        EG.RtPickStep(sel)
    elseif tg then
        RtMapPaint(tg.mapID)
    end
end

local function PaintRoutes()
    PaintGraveBtn()
    if EG.rtStyleSync then EG.rtStyleSync() end
    local fac = RtFac()
    local list = ROUTES[fac] or {}
    if EG.rtListHead then
        EG.rtListHead:SetText(format(L["地点 · 共 %d 条"], #list))
    end
    for i = 1, EG.RT_MAX_TARGETS do
        local r = EG.rtRows and EG.rtRows[i]
        if not r then break end
        local t = list[i]
        if not t then
            r:Hide()
        else
            r:Show()
            local sel = (i == RtSel(fac))
            RtRowSel(r, sel)
            r.name:SetText(RtFullName(t))
            r.name:SetTextColor(Unpack(sel and C_WHITE or C_TEXT))
        end
    end
    for k, fb in pairs(EG.rtFacBtns or {}) do
        local on = (k == fac)
        SetButtonSelected(fb, on)
        local fs = fb.GetFontString and fb:GetFontString()
        if fs then
            if k == "h" then
                fs:SetTextColor(1.00, 0.36, 0.26)
            else
                fs:SetTextColor(0.40, 0.62, 1.00)
            end
        end
    end
    local t = list[RtSel(fac)]
    if not t then
        if EG.rtEmptyHost then EG.rtEmptyHost:Show() end
        if EG.rtBody then EG.rtBody:Hide() end
        if EG.rtMap then EG.rtMap:Hide() end
        return
    end
    if EG.rtEmptyHost then EG.rtEmptyHost:Hide() end
    if EG.rtBody then EG.rtBody:Show() end
    if EG.rtMap then EG.rtMap:Show() end
    local j = RtRace(fac, RtSel(fac))
    local race = t.races[j]
    local bd = EG.rtBody
    local raceKey = fac .. ":" .. RtSel(fac) .. ":" .. j
    if EG.rtMapKey ~= raceKey then
        EG.rtMapKey = raceKey
        EG.rtStepSel = nil
        for i = 1, #(race.steps or {}) do
            local sd = race.steps[i]
            if sd.x and sd.y then EG.rtStepSel = i break end
        end
    end
    EG.rtCurRace, EG.rtCurTgt = race, t
    EG.rtTitle:SetText(t.name)
    local zn = RtZoneOf(t)
    if zn == t.name then zn = RtTailOf(t) end
    local sameZn = (zn == "" or zn == t.name)
    if sameZn then
        EG.rtZone:SetText("")
        EG.rtZone:Hide()
    else
        EG.rtZone:SetText(zn)
        EG.rtZone:Show()
    end
    if EG.rtDstBtn then
        EG.rtDstBtn:ClearAllPoints()
        if sameZn then
            EG.rtDstBtn:SetPoint("LEFT", EG.rtTitle, "RIGHT", 8, 0)
        else
            EG.rtDstBtn:SetPoint("LEFT", EG.rtZone, "RIGHT", 8, 0)
        end
    end
    local multi = #t.races > 1
    local x0 = 8
    for k = 1, 5 do
        local rb = EG.rtRaceBtns and EG.rtRaceBtns[k]
        if rb then
            local rc = t.races[k]
            if rc and multi then
                rb:Show()
                rb:SetText(rc.race)
                local fsr = rb:GetFontString()
                local rw = (fsr and fsr.GetStringWidth and fsr:GetStringWidth() or 40) + 18
                rb:SetWidth(rw)
                rb:ClearAllPoints()
                rb:SetPoint("TOPLEFT", bd, "TOPLEFT", x0, -32)
                x0 = x0 + rw + 8
                SetButtonSelected(rb, (k == j))
            else
                rb:Hide()
            end
        end
    end
    if EG.rtScroll then
        EG.rtScroll:ClearAllPoints()
        EG.rtScroll:SetPoint("TOPLEFT", bd, "TOPLEFT", 8, -(multi and 72 or 40))
        EG.rtScroll:SetPoint("BOTTOMRIGHT", bd, "BOTTOMRIGHT", -8, -8)
    end
    local sw = (EG.rtStepsHost and EG.rtStepsHost:GetWidth()) or EG.RT_STEP_W
    local y = 0
    for i = 1, EG.RT_MAX_STEPS do
        local st = EG.rtSteps and EG.rtSteps[i]
        if not st then break end
        local step = race.steps[i]
        if not step then
            st:Hide()
        else
            st:Show()
            RtRowSel(st, i == EG.rtStepSel)
            st.noTx:SetText(i)
            st.act:SetText(step.t)
            local aw = st.act:GetStringWidth() or 60
            local coW = 0
            local gmap = t.mapID
            if type(step.m) == "table" and step.m[1] then gmap = step.m[1] end
            if step.x and step.y then
                coW = st.co:GetWidth() or 60
                st.co:Show()
                st.__go = { gmap, step.x, step.y }
            else
                st.co:Hide()
                st.__go = nil
            end
            local kd = RT_KIND_TXT[step.k]
            if kd then
                st.kind.lab:SetText(kd[1])
                local kw = (st.kind.lab:GetStringWidth() or 30) + DG.Q_BADGE_PAD * 2
                local minW = (DG.BADGE_CAP_W or 8) * 2 + 2
                if kw < minW then kw = minW end
                st.kind:SetWidth(kw)
                if 36 + aw + 8 + kw <= sw - coW - 12 then
                    DG.BadgeTint(st.kind, kd[2])
                    st.kind:ClearAllPoints()
                    st.kind:SetPoint("TOPLEFT", st.act, "TOPRIGHT", 8, 0)
                    st.kind:Show()
                else
                    st.kind:Hide()
                end
            else
                st.kind:Hide()
            end
            st.d:SetText(step.d)
            st.d:SetWidth(math.max(120, sw - 44))
            local dh = st.d:GetStringHeight() or 17
            local fh = st.d:GetHeight()
            if type(fh) == "number" and fh > dh then dh = fh end
            local h = 8 + 24 + 4 + dh + 8
            st:ClearAllPoints()
            st:SetPoint("TOPLEFT", EG.rtStepsHost, "TOPLEFT", 0, -y)
            st:SetPoint("TOPRIGHT", EG.rtStepsHost, "TOPRIGHT", 0, -y)
            st:SetHeight(h)
            y = y + h + 8
        end
    end
    if EG.rtStepsHost then
        EG.rtStepsHost:SetHeight(math.max(y, 1))
    end
    if EG.rtDstBtn then
        local has = t.dst and t.dst[2] and true or false
        EG.rtDstBtn:SetEnabled(has)
        EG.rtDstBtn.__go = has and { t.dst[1], t.dst[2], t.dst[3] } or nil
    end
    if EG.rtTime then EG.rtTime:SetText(race.time or t.time or "") end
    local msd = EG.rtStepSel and race.steps[EG.rtStepSel]
    if msd and msd.x and msd.y then
        local mm = (type(msd.m) == "table" and msd.m[1]) or t.mapID
        RtMapPaint(mm, msd.x, msd.y)
    else
        RtMapPaint(t.mapID)
    end
    if EG.RtScrollUpdate then EG.RtScrollUpdate() end
end

local BM_TAB_KEYS = { "ov", "saber", "witch", "codex" }

local function BMTab()
    local db = ns.DB()
    db.explore = db.explore or {}
    for _, key in ipairs(BM_TAB_KEYS) do
        if db.explore.bmTab == key then return key end
    end
    return "ov"
end

local BM_IS_MAGE = nil
local function BMIsMage()
    if BM_IS_MAGE == nil then
        local ok, cls = pcall(UnitClass, "player")
        BM_IS_MAGE = (ok and cls == "MAGE") or false
    end
    return BM_IS_MAGE
end

local function PaintBMNode(nd)
    if not nd or not nd.tint then return end
    if nd.__hov then
        for _, htx in ipairs(nd.__hov) do htx:SetShown(nd.__hl and not nd.__sel or false) end
    end
    if nd.__sel then
        nd.tint:SetColorTexture(1, 0.82, 0, 0.12)
        nd.tint:Show()
    elseif nd.__hl and not nd.__hov then
        nd.tint:SetColorTexture(1, 1, 1, 0.07)
        nd.tint:Show()
    else
        nd.tint:Hide()
    end
end

local function PaintBMChain(tab, KeepName)
    local chainData = BM_CHAINS[tab]
    local n = #chainData
    local pad, gap = 8, 8
    local okw, cw = pcall(EG.bmChain.GetWidth, EG.bmChain)
    cw = (okw and type(cw) == "number" and cw > 50 and cw) or (EG.RIGHT_W - 16)
    local nw = math.floor((cw - pad * 2 - gap * (n - 1)) / n + 0.5)
    for i = 1, 5 do
        local nd = EG.bmNodes and EG.bmNodes[i]
        if not nd then break end
        local data = chainData[i]
        if data then
            nd:ClearAllPoints()
            nd:SetPoint("TOPLEFT", EG.bmChain, "TOPLEFT", pad + (i - 1) * (nw + gap), -8)
            nd:SetSize(nw, 58)
            nd.__chainKey, nd.__idx = tab, i
            nd.__id, nd.__note = data.item, data.sub
            nd.__sel = false
            local nm, ok
            if data.item then nm, ok = KeepName(data.item) end
            nd.t:SetText(data.title or nm or "?")
            nd.t:SetTextColor(Unpack(data.ghost and C_GREY or ((ok == false) and C_DIM or C_TEXT)))
            nd.sub:SetText(data.sub or "")
            nd.sub:SetShown(not data.ghost)
            if data.item then
                local ic = DG.ItemIcon(data.item)
                if type(ic) == "number" then
                    nd.icon:SetTexture(ic)
                elseif type(ic) == "string" and ic ~= "" then
                    nd.icon:SetTexture("Interface\\Icons\\" .. ic)
                else
                    nd.icon:SetTexture("Interface\\Icons\\" .. tostring(FALLBACK_ICON))
                end
                nd.icon:SetShown(true)
            else
                nd.icon:SetTexture("Interface\\Icons\\spell_holy_mindsooth")
                nd.icon:SetShown(true)
            end
            PaintBMNode(nd)
            nd:Show()
        else
            nd.__sel, nd.__hl = false, false
            nd:Hide()
        end
        local ar = EG.bmArrows and EG.bmArrows[i]
        if ar then
            if data and i < n then
                ar:ClearAllPoints()
                ar:SetPoint("LEFT", nd, "RIGHT", 0, 0)
                ar:SetPoint("RIGHT", EG.bmNodes[i + 1], "LEFT", 0, 0)
                ar:Show()
            else
                ar:Hide()
            end
        end
    end
    local y = 8
    for i = 1, #(EG.bmSteps or {}) do
        local st = EG.bmSteps[i]
        local e = chainData[i]
        if e then
            st:ClearAllPoints()
            st:SetPoint("TOPLEFT", EG.bmDChild, "TOPLEFT", 8, -y)
            st:SetPoint("TOPRIGHT", EG.bmDChild, "TOPRIGHT", -8, -y)
            st.num:SetText(tostring(i))
            local det = e.det or {}
            local nm, ok
            if e.item then nm, ok = KeepName(e.item) end
            st.t:SetText(nm or e.title or "")
            st.t:SetTextColor(Unpack(e.ghost and C_GREY or ((ok == false) and C_DIM or C_TEXT)))
            st.sub:SetText(det.sub or "")
            st.loc.__loc = e.loc
            st.loc:SetShown(e.loc ~= nil)
            if e.loc then
                st.loc.fs:SetText(format("%.1f, %.1f", e.loc.x, e.loc.y))
                local w = st.loc.fs.GetStringWidth and st.loc.fs:GetStringWidth() or 0
                st.loc:SetWidth(math.max((type(w) == "number" and w or 0) + 12, 40))
            end
            local ly = 26
            for j = 1, #(st.lines or {}) do
                local lf = st.lines[j]
                local txt = det.lines and det.lines[j] or nil
                if txt then
                    lf:ClearAllPoints()
                    lf:SetPoint("TOPLEFT", st, "TOPLEFT", 18, -ly)
                    lf:SetPoint("RIGHT", st, "RIGHT", -8, 0)
                    lf:SetText(txt)
                    lf:Show()
                    local h = lf.GetStringHeight and lf:GetStringHeight() or 0
                    if type(h) ~= "number" or h < 18 then h = 18 end
                    ly = ly + h + 5
                else
                    lf:Hide()
                end
            end
            st:SetHeight(ly + 4)
            st.sep:SetShown(i < n)
            st:Show()
            y = y + ly + 16
        else
            st:Hide()
        end
    end
    if EG.bmDChild then EG.bmDChild:SetHeight(y + 4) end
end

local function StripScrollName(nm)
    if type(nm) == "string" then
        nm = nm:gsub("^卷轴：", "")
        nm = nm:gsub("^卷轴:%s*", "")
        nm = nm:gsub("^卷軸：", "")
        nm = nm:gsub("^卷軸:%s*", "")
        return (nm:gsub("^%s+", ""))
    end
    return nm
end

local function PaintBMCodex(KeepName)
    EG.bmTier = EG.bmTier or 1
    local t = BM_TIERS[EG.bmTier] or BM_TIERS[1]
    for ti, bt in pairs(EG.bmTierBtns or {}) do
        local sel = (ti == EG.bmTier)
        SetButtonSelected(bt, sel)
        local fs = bt.GetFontString and bt:GetFontString()
        if fs then fs:SetTextColor(Unpack(sel and C_WHITE or C_DIM)) end
    end
    local rows = {}
    for _, id in ipairs(t.unc) do
        rows[#rows + 1] = { id = id, badge = format(L["需要理解 %d"], t.req) }
    end
    for _, o in ipairs(t.out) do
        rows[#rows + 1] = { id = o[1], badge = o.badge, note = o.note }
    end
    local synTxt = L["合成"]
    for i = 1, #(EG.bmRows or {}) do
        local rw2 = EG.bmRows[i]
        local rec = rows[i]
        if rec then
            rw2.__id = rec.id
            rw2.__note = rec.note
            local nm, ok = KeepName(rec.id)
            rw2.nm:SetText(StripScrollName(nm) or "?")
            local q = DG.QualOf and DG.QualOf(rec.id) or nil
            rw2.nm:SetTextColor(Unpack((ok and q and QUALITY_COLOR(q)) or (ok and C_TEXT or C_DIM)))
            rw2.note:SetText(rec.note or "")
            rw2.badge:SetText(rec.badge or "")
            rw2.badge:SetTextColor(Unpack((rec.badge == synTxt) and C_GOLD or C_GREY))
            local ic = DG.ItemIcon(rec.id)
            if type(ic) == "number" then
                rw2.icon:SetTexture(ic)
            elseif type(ic) == "string" and ic ~= "" then
                rw2.icon:SetTexture("Interface\\Icons\\" .. ic)
            else
                rw2.icon:SetTexture("Interface\\Icons\\" .. tostring(FALLBACK_ICON))
            end
            rw2:Show()
        else
            rw2.__id, rw2.__note = nil, nil
            rw2:Hide()
        end
    end
    EG.bmChild:SetHeight(#rows * 38 + 4)
end

local function PaintBMOv(KeepName)
    for ti, rw in ipairs(EG.bmOvRows or {}) do
        local t = BM_TIERS[ti]
        if t then
            local names = {}
            for _, id in ipairs(t.unc) do
                local nm = KeepName(id)
                names[#names + 1] = StripScrollName(nm) or "?"
            end
            rw.nm:SetText(table.concat(names, ", "))
            rw.req:SetText(tostring(t.req))
            rw.gray:SetText(tostring(t.gray))
            rw.tier:SetText(t.tier)
            rw:Show()
        else
            rw:Hide()
        end
    end
    for _, rw in ipairs(EG.bmBundleRows or {}) do
        local nm, ok = KeepName(rw.__id)
        rw.nm:SetText(nm or "?")
        local q = rw.__id and DG.QualOf and DG.QualOf(rw.__id) or nil
        rw.nm:SetTextColor(Unpack((ok and q and QUALITY_COLOR(q)) or (ok and C_TEXT or C_DIM)))
        local ic = DG.ItemIcon(rw.__id)
        if type(ic) == "number" then
            rw.icon:SetTexture(ic)
        elseif type(ic) == "string" and ic ~= "" then
            rw.icon:SetTexture("Interface\\Icons\\" .. ic)
        else
            rw.icon:SetTexture("Interface\\Icons\\" .. tostring(FALLBACK_ICON))
        end
    end
end

local function PaintBM()
    EG.bmNameIds = {}
    local function KeepName(id)
        if not id then return nil, false end
        EG.bmNameIds[#EG.bmNameIds + 1] = id
        local nm, ok = DG.ItemName(id)
        if not ok then EG.needNames = true end
        return nm, ok
    end
    if EG.bmHint then EG.bmHint:SetShown(not BMIsMage()) end
    local tab = BMTab()
    for key, bt in pairs(EG.bmTabBtns or {}) do
        local sel = (key == tab)
        SetButtonSelected(bt, sel)
        local fs = bt.GetFontString and bt:GetFontString()
        if fs then fs:SetTextColor(Unpack(sel and C_WHITE or C_DIM)) end
    end
    local isCodex = (tab == "codex")
    local isOv = (tab == "ov")
    EG.bmChain:SetShown(not isCodex and not isOv)
    EG.bmDetail:SetShown(not isCodex and not isOv)
    if EG.bmOv then EG.bmOv:SetShown(isOv) end
    if EG.bmBundle then EG.bmBundle:SetShown(isOv) end
    for _, bt in pairs(EG.bmTierBtns or {}) do bt:SetShown(isCodex) end
    if EG.bmScroll then EG.bmScroll:SetShown(isCodex) end
    if isCodex then PaintBMCodex(KeepName)
    elseif isOv then PaintBMOv(KeepName)
    else PaintBMChain(tab, KeepName) end
    if EG.needNames then EG.ScheduleSweep() end
end

local C_PET_LINK = { 0.55, 0.78, 1.0 }
local C_PET_LINK_HI = { 1, 0.82, 0 }
local C_ITEM_LINK = { 0.42, 0.78, 0.45 }
local C_ITEM_HI = { 0.6, 0.95, 0.62 }
local PET_FAC_TXT = { A = L["联盟限定"], H = L["部落限定"] }
local PET_FAC_COL = { A = { 0.45, 0.68, 0.98 }, H = { 0.95, 0.5, 0.45 } }
local PET_DIFF_TXT = { party = L["难度·组队"], solo = L["难度·单人"], easy = L["难度·简单"] }
local PET_DIFF_COL = {
    party = { 0.88, 0.42, 0.42 },
    solo  = { 0.38, 0.80, 0.50 },
    easy  = { 0.38, 0.80, 0.50 },
}

local function PetTip(owner, on, label, area, x, y)
    if not GameTooltip then return end
    if not on then
        if GameTooltip.Hide then pcall(GameTooltip.Hide, GameTooltip) end
        return
    end
    local has = type(x) == "number" and type(y) == "number"
    local zone = tostring(EG.ZoneName(area, area or "?"))
    GameTooltip:SetOwner(owner, "ANCHOR_RIGHT")
    if GameTooltip.ClearLines then GameTooltip:ClearLines() end
    GameTooltip:AddLine(label or "", 1, 1, 1, false)
    GameTooltip:AddLine(has and format("%s %.1f, %.1f", zone, x, y) or zone, 0.7, 0.75, 0.82, false)
    GameTooltip:AddLine(has and L["点击在世界地图标记"] or L["点击打开该区域地图"], 0.55, 0.78, 1, false)
    if GameTooltip.Show then GameTooltip:Show() end
end

local function PetGo(area, x, y)
    EG.MarkPoint(area, x, y)
    ns.PlaySound(1)
end

local function PetSplit(t, marks)
    local segs, pos = {}, 1
    for _, mk in ipairs(marks or {}) do
        local s = t:find(mk[1], pos, true)
        if s then
            if s > pos then segs[#segs + 1] = { t:sub(pos, s - 1) } end
            segs[#segs + 1] = { t:sub(s, s + #mk[1] - 1), mk }
            pos = s + #mk[1]
        end
    end
    if pos <= #t then segs[#segs + 1] = { t:sub(pos) } end
    return segs
end

local function PetSeg(card, k)
    local sg = card.segs[k]
    if sg then return sg end
    sg = CreateFrame("Button", nil, card)
    sg:SetHeight(EG.PET_ROW_H)
    local fs = MakeFS(sg, 14, C_TEXT, "LEFT")
    sg:SetFontString(fs)
    sg.tx = fs
    sg:SetScript("OnEnter", function(self)
        if not self.__mark then return end
        local m = self.__mark
        self.tx:SetTextColor(Unpack(self.__item and C_ITEM_HI or C_PET_LINK_HI))
        local ul = card.__ul
        if ul then
            ul:ClearAllPoints()
            ul:SetPoint("BOTTOMLEFT", self, "BOTTOMLEFT", 0, -1)
            ul:SetPoint("BOTTOMRIGHT", self, "BOTTOMRIGHT", 0, -1)
            ul:Show()
        end
        if self.__item then
            if DG.ShowItemTip then DG.ShowItemTip(self, { m[3] }) end
        else
            PetTip(self, true, m[1], m[2], m[3], m[4])
        end
    end)
    sg:SetScript("OnLeave", function(self)
        if self.__mark then self.tx:SetTextColor(Unpack(self.__item and C_ITEM_LINK or C_PET_LINK)) end
        if card.__ul then card.__ul:Hide() end
        PetTip(self, false)
    end)
    sg:SetScript("OnClick", function(self)
        local m = self.__mark
        if m and not self.__item then PetGo(m[2], m[3], m[4]) end
    end)
    sg:Hide()
    card.segs[k] = sg
    return sg
end

local PET_NUM = { "①", "②", "③", "④", "⑤" }

local function PetFlow(card, idx, segs, y, maxW)
    local x = 0
    for _, s in ipairs(segs) do
        idx = idx + 1
        local sg = PetSeg(card, idx)
        if not sg then break end
        local txt, m, col = s[1], s[2], s[3]
        sg.__mark = m
        sg.__item = m and (m[2] == "item") or nil
        sg.__col = col
        sg.tx:SetWordWrap(false)
        sg.tx:SetText(txt)
        local w = sg.tx:GetStringWidth()
        if type(w) ~= "number" or w <= 0 then w = 7 * #txt end
        local rows = 1
        if w > maxW then
            if x > 0 and x <= 24 then
                w, rows = maxW - x, math.ceil(w / (maxW - x))
            else
                if x > 0 then x, y = 0, y - EG.PET_ROW_H end
                w, rows = maxW, math.ceil(w / maxW)
            end
            sg.tx:SetWidth(w)
            sg.tx:SetWordWrap(true)
        end
        sg:SetWidth(w + 1)
        sg:SetHeight(EG.PET_ROW_H * rows)
        sg.tx:ClearAllPoints()
        sg.tx:SetPoint("LEFT", sg, "LEFT", 0, 0)
        if x > 0 and x + w > maxW then x, y = 0, y - EG.PET_ROW_H end
        sg:ClearAllPoints()
        sg:SetPoint("TOPLEFT", card, "TOPLEFT", EG.PET_TX + x, y)
        if m then
            sg:EnableMouse(true)
            sg.tx:SetTextColor(Unpack(sg.__item and C_ITEM_LINK or C_PET_LINK))
        else
            sg:EnableMouse(false)
            sg.tx:SetTextColor(Unpack(col or C_TEXT))
        end
        sg:Show()
        x = x + w
        if rows > 1 then x, y = 0, y - EG.PET_ROW_H * (rows - 1) end
    end
    return idx, y
end

local function PaintPets(src, toy, banner)
    src = src or PETS
    EG.needNames = EG.needNames or false
    if EG.petFrame then
        if EG.petFrame.head then
            if banner then
                local bid = BANNER[1] and BANNER[1][1] or nil
                local got = bid and (EG.CountInBags(bid) or 0) > 0 or false
                EG.petFrame.head:SetText(got and L["血色旗帜 · 隐藏寻宝（已拾取）"]
                                             or L["血色旗帜 · 隐藏寻宝（未拾取）"])
            elseif toy then
                EG.petFrame.head:SetText(format(L["玩具 · 共 %d 件"], #src))
            else
                EG.petFrame.head:SetText(format(L["宠物获取 · 共 %d 只"], #src))
            end
        end
        if EG.petFrame.hint then
            EG.petFrame.hint:SetText(banner and L["点地名 / 坐标在世界地图标记 · 悬停物品名看提示"]
                or toy and L["点名称 / 区域名 / 坐标可在世界地图标记"]
                or L["点宠物名 / 区域名 / 坐标可在世界地图标记"])
        end
    end
    local flowY = 0
    for i = 1, EG.PET_CARDS do
        local card = EG.petCards and EG.petCards[i]
        if not card then break end
        local rec = src[i]
        if not rec then
            card:Hide()
        else
            local it, slug = rec[1], rec[2]
            local fac, diff = rec[3], rec[4]
            local area, px, py, srcl = rec[5], rec[6], rec[7], rec[8]
            local steps = rec[9] or {}

            local tex = DG.ItemIcon(it)
            if (type(tex) ~= "string" or tex == "" or tex == FALLBACK_ICON)
               and type(slug) == "string" and slug ~= "" then
                tex = "Interface\\Icons\\" .. slug
            end
            if type(tex) ~= "string" or tex == "" then tex = FALLBACK_ICON end
            card.icon:SetTexture(tex)
            if card.iconBtn then
                card.iconBtn.__it = toy and it or nil
                card.iconBtn:EnableMouse(toy and true or false)
            end

            local nm, ok = DG.ItemName(it)
            if not ok then EG.needNames = true end
            card.name:SetText(ok and nm or format(L["物品 #%d"], it))

            local zone = EG.ZoneName(area, format(L["区域 #%d"], area or 0))
            card.facTx:SetText(fac and PET_FAC_TXT[fac] or L["双阵营"])
            local fc = (fac and PET_FAC_COL[fac]) or { 0.66, 0.70, 0.78 }
            card.facTx:SetTextColor(fc[1], fc[2], fc[3])
            PillEdge(card.facPill, fc[1], fc[2], fc[3], 0.4)

            local dk = (diff == "party" or diff == "solo") and diff or "easy"
            card.diffTx:SetText(PET_DIFF_TXT[dk])
            local dc = PET_DIFF_COL[dk]
            card.diffTx:SetTextColor(dc[1], dc[2], dc[3])
            PillEdge(card.diffPill, dc[1], dc[2], dc[3], 0.4)

            local hasMain = type(px) == "number" and type(py) == "number"
            card.chip:SetShown(hasMain)
            card.chipTx:SetText(hasMain and format("%.1f, %.1f", px, py) or "")
            card.chip.__area, card.chip.__x, card.chip.__y = area, px, py
            card.chip.__label = zone
            card.srcArea, card.srcX, card.srcY = area, px, py
            card.srcName = zone

            local maxW = EG.RIGHT_W - EG.PET_TX - EG.PET_PAD
            local idx = 0
            local srcRow = { { zone, { zone, area, px, py } } }
            local srcMarks = rec[10]
            if srcl and srcl ~= "" then
                if type(srcMarks) == "table" and srcMarks[1] then
                    local segs = PetSplit(tostring(srcl), srcMarks)
                    segs[1][1] = " · " .. tostring(segs[1][1])
                    for _, s in ipairs(segs) do srcRow[#srcRow + 1] = s end
                else
                    srcRow[#srcRow + 1] = { " · " .. tostring(srcl) }
                end
            end
            idx = PetFlow(card, idx, srcRow, -42, maxW)
            local yy = -76
            for si, st in ipairs(steps) do
                local row, gap
                if banner and st.h then
                    row = { { tostring(st.h), nil, C_GOLD } }
                    gap = (si > 1) and 12 or 0
                else
                    local lead
                    if banner then
                        lead = st.num and { st.num .. " ", nil, C_GOLD } or { "· ", nil, C_GREY }
                    else
                        lead = { (PET_NUM[si] or tostring(si)) .. " ", nil, C_GOLD }
                    end
                    row = { lead }
                    local t = st.t
                    if st.q then
                        local qt = ToyQuestTitle(st.q)
                        if not qt then
                            qt = format(L["任务 #%d"], st.q)
                            EG.needNames = true
                        end
                        t = t:gsub("#q", function() return qt end)
                    end
                    for _, s in ipairs(PetSplit(t, st.m)) do
                        row[#row + 1] = s
                    end
                    if banner and st.n then
                        for k = 2, #row do
                            if not row[k][2] then row[k][3] = C_GREY end
                        end
                    end
                    gap = 0
                end
                idx, yy = PetFlow(card, idx, row, yy - gap, maxW)
                yy = yy - EG.PET_ROW_H
            end
            local hCard = -yy + EG.TOY_CARD_PAD
            card:SetHeight(hCard)
            if EG.petFrame and EG.petFrame.child then
                card:SetPoint("TOPLEFT", EG.petFrame.child, "TOPLEFT", 8, -flowY)
                card:SetPoint("TOPRIGHT", EG.petFrame.child, "TOPRIGHT", -8, -flowY)
            end
            flowY = flowY + hCard + EG.PET_GAP
            for k = idx + 1, #card.segs do
                if card.segs[k] then card.segs[k]:Hide() end
            end
            card:Show()
        end
    end
    if EG.petFrame and EG.petFrame.child then
        local h = EG.PET_HEAD_H + (flowY > EG.PET_GAP and (flowY - EG.PET_GAP) or 0)
        local vh = select(2, EG.petFrame:GetSize())
        if type(vh) == "number" and vh > h then h = vh end
        EG.petFrame.child:SetHeight(h)
    end
    if EG.needNames then EG.ScheduleSweep() end
end

local function BuildPets(page)
    local root = CreateFrame("Frame", nil, page)
    root:SetPoint("TOPLEFT", page, "TOPLEFT", EG.X0, -EG.TOP_EDGE)
    root:SetPoint("BOTTOMRIGHT", page, "BOTTOMRIGHT", -EG.EDGE, EG.EDGE)
    EG.petFrame = root
    root.head = MakeFS(root, 14, C_TEXT, "LEFT")
    root.head:SetPoint("TOPLEFT", root, "TOPLEFT", 8, -8)
    root.hint = MakeFS(root, 14, C_GREY, "RIGHT")
    root.hint:SetPoint("TOPRIGHT", root, "TOPRIGHT", -8, -8)

    local sc = CreateFrame("ScrollFrame", nil, root)
    sc:EnableMouseWheel(true)
    sc:SetPoint("TOPLEFT", root, "TOPLEFT", 0, -EG.PET_HEAD_H)
    sc:SetPoint("BOTTOMRIGHT", root, "BOTTOMRIGHT", 0, 0)
    local child = CreateFrame("Frame", nil, sc)
    child:SetSize(EG.RIGHT_W, 10)
    sc:SetScrollChild(child)
    sc:SetScript("OnMouseWheel", function(_, delta)
        if DG.WheelScroll then DG.WheelScroll(sc, child, delta) end
    end)
    root.scroll, root.child = sc, child
    local host = child

        EG.petCards, EG.petIds, EG.toyIds, EG.bannerIds = {}, {}, {}, {}
        for i = 1, EG.PET_CARDS do
            if i % 3 == 0 then coroutine.yield() end
        local card = CreateFrame("Frame", nil, host, "BackdropTemplate")
        card:SetHeight(EG.PET_CARD_H)
        card:SetPoint("TOPLEFT", host, "TOPLEFT", 8, -((i - 1) * (EG.PET_CARD_H + EG.PET_GAP)))
        card:SetPoint("TOPRIGHT", host, "TOPRIGHT", -8, -((i - 1) * (EG.PET_CARD_H + EG.PET_GAP)))
        card:SetBackdrop({
            bgFile = "Interface\\Buttons\\WHITE8x8",
            edgeFile = "Interface\\Buttons\\WHITE8x8",
            edgeSize = 1,
        })
        card:SetBackdropColor(1, 1, 1, 0.035)
        card:SetBackdropBorderColor(1, 1, 1, 0.08)
        if ns.hui and ns.hui.SkinPopup then
            ns.hui.SkinPopup(card, 8, nil, ns.hui.layer.L2)
        end

        card.icon = card:CreateTexture(nil, "ARTWORK")
        card.icon:SetSize(EG.PET_ICON, EG.PET_ICON)
        card.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
        if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(card.icon) end
        card.icon:SetPoint("TOPLEFT", card, "TOPLEFT", EG.PET_PAD, -16)

        card.iconBtn = CreateFrame("Button", nil, card)
        card.iconBtn:SetAllPoints(card.icon)
        card.iconBtn:EnableMouse(false)
        card.iconBtn:SetScript("OnEnter", function(self)
            if self.__it and DG.ShowItemTip then DG.ShowItemTip(self, { self.__it }) end
        end)
        card.iconBtn:SetScript("OnLeave", function()
            if GameTooltip then pcall(GameTooltip.Hide, GameTooltip) end
        end)

        card.name = MakeFS(card, 16, C_WHITE, "LEFT")
        card.name:SetPoint("TOPLEFT", card, "TOPLEFT", EG.PET_TX, -16)
        card.name:SetWordWrap(false)

        card.diffPill = CreateFrame("Frame", nil, card, "BackdropTemplate")
        card.diffPill:SetSize(76, 20)
        card.diffPill:SetPoint("TOPRIGHT", card, "TOPRIGHT", -EG.PET_PAD, -16)
        card.diffPill:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8x8",
                                    edgeFile = "Interface\\Buttons\\WHITE8x8", edgeSize = 1 })
        if not HuiPillFX(card.diffPill, 10, { 1, 1, 1, 0.4 }) then
            card.diffPill:SetBackdropColor(1, 1, 1, 0.04)
        end
        card.diffTx = MakeFS(card.diffPill, 14, C_DIM, "CENTER")
        card.diffTx:SetAllPoints()

        card.facPill = CreateFrame("Frame", nil, card, "BackdropTemplate")
        card.facPill:SetSize(76, 20)
        card.facPill:SetPoint("RIGHT", card.diffPill, "LEFT", -8, 0)
        card.facPill:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8x8",
                                   edgeFile = "Interface\\Buttons\\WHITE8x8", edgeSize = 1 })
        if not HuiPillFX(card.facPill, 10, { 1, 1, 1, 0.4 }) then
            card.facPill:SetBackdropColor(1, 1, 1, 0.04)
        end
        card.facTx = MakeFS(card.facPill, 14, C_DIM, "CENTER")
        card.facTx:SetAllPoints()

        card.chip = CreateFrame("Button", nil, card, "BackdropTemplate")
        card.chip:SetSize(92, 20)
        card.chip:SetPoint("TOPRIGHT", card, "TOPRIGHT", -EG.PET_PAD, -42)
        card.chip:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8x8",
                                edgeFile = "Interface\\Buttons\\WHITE8x8", edgeSize = 1 })
        if not HuiPillFX(card.chip, 10, { 1, 1, 1, 0.14 }) then
            card.chip:SetBackdropColor(1, 1, 1, 0.06)
            card.chip:SetBackdropBorderColor(1, 1, 1, 0.14)
        end
        if ns.hui and ns.hui.BuildCapsule then
            card.chip.__hov = ns.hui.BuildCapsule(card.chip, 10, ns.hui.layer.L4, 1, 2)
            for _, t in ipairs(card.chip.__hov) do t:Hide() end
        end
        card.chipTx = MakeFS(card.chip, 14, C_TEXT, "CENTER")
        card.chipTx:SetAllPoints()
        card.chip:SetScript("OnEnter", function(self)
            if self.__hov then
                for _, t in ipairs(self.__hov) do t:SetShown(true) end
            else
                self:SetBackdropColor(1, 1, 1, 0.1)
            end
            PetTip(self, true, self.__label, self.__area, self.__x, self.__y)
        end)
        card.chip:SetScript("OnLeave", function(self)
            if self.__hov then
                for _, t in ipairs(self.__hov) do t:SetShown(false) end
            else
                self:SetBackdropColor(1, 1, 1, 0.06)
            end
            PetTip(self, false)
        end)
        card.chip:SetScript("OnClick", function(self)
            PetGo(self.__area, self.__x, self.__y)
        end)

        card.sep = card:CreateTexture(nil, "BORDER")
        card.sep:SetHeight(1)
        card.sep:SetColorTexture(1, 1, 1, 0.07)
        card.sep:SetPoint("TOPLEFT", card, "TOPLEFT", EG.PET_TX, -68)
        card.sep:SetPoint("TOPRIGHT", card, "TOPRIGHT", -EG.PET_PAD, -68)

        card.ul = card:CreateTexture(nil, "OVERLAY")
        card.ul:SetColorTexture(1, 0.82, 0, 0.9)
        card.ul:SetHeight(1)
        card.ul:Hide()
        card.__ul = card.ul

        card.segs = {}
        for k = 1, EG.PET_SEGS do PetSeg(card, k) end
        EG.petCards[i] = card
        EG.petIds[i] = PETS[i] and PETS[i][1] or nil
        EG.toyIds[i] = TOYS[i] and TOYS[i][1] or nil
        EG.bannerIds[i] = BANNER[i] and BANNER[i][1] or nil
    end
    root:Hide()
end

function EG.LayoutBody()
    local top, bot = EG.BODY_TOP, EG.EDGE
    EG.scroll:ClearAllPoints()
    EG.scroll:SetPoint("TOPLEFT", EG.page, "TOPLEFT", EG.X0, -top)
    EG.scroll:SetPoint("BOTTOMRIGHT", EG.page, "BOTTOMRIGHT", -EG.EDGE, bot)
    EG.listCard:ClearAllPoints()
    EG.listCard:SetPoint("TOPLEFT", EG.page, "TOPLEFT", EG.X0, -EG.TOP_EDGE)
    EG.listCard:SetPoint("BOTTOMRIGHT", EG.page, "BOTTOMRIGHT",
                         -EG.EDGE, bot)
    EG.listCard:Show()
    if EG.navCard then
        EG.navCard:ClearAllPoints()
        EG.navCard:SetPoint("TOPLEFT", EG.page, "TOPLEFT", EG.NAV_X, -EG.TOP_EDGE)
        EG.navCard:SetPoint("BOTTOMRIGHT", EG.page, "BOTTOMLEFT",
                            EG.X0 - 8, bot)
        EG.navCard:Show()
    end
    if EG.rwFrame then
        EG.rwFrame:ClearAllPoints()
        EG.rwFrame:SetPoint("TOPLEFT", EG.page, "TOPLEFT", EG.X0, -top)
        EG.rwFrame:SetPoint("BOTTOMRIGHT", EG.page, "BOTTOMRIGHT", -EG.EDGE, bot)
    end
    if EG.bagFrame then
        EG.bagFrame:ClearAllPoints()
        EG.bagFrame:SetPoint("TOPLEFT", EG.page, "TOPLEFT", EG.X0, -EG.TOP_EDGE)
        EG.bagFrame:SetPoint("BOTTOMRIGHT", EG.page, "BOTTOMRIGHT", -EG.EDGE, bot)
        if EG.bagScroll then
            local ok, vh = pcall(EG.bagScroll.GetHeight, EG.bagScroll)
            EG.bagViewH = (ok and type(vh) == "number" and vh > 100 and vh) or 300
        end
        BagLayoutRows()
    end
    if EG.bmFrame then
        EG.bmFrame:ClearAllPoints()
        EG.bmFrame:SetPoint("TOPLEFT", EG.page, "TOPLEFT", EG.X0, -EG.TOP_EDGE)
        EG.bmFrame:SetPoint("BOTTOMRIGHT", EG.page, "BOTTOMRIGHT", -EG.EDGE, bot)
        if EG.bmScroll then
            local ok, vh = pcall(EG.bmScroll.GetHeight, EG.bmScroll)
            EG.bmViewH = (ok and type(vh) == "number" and vh > 100 and vh) or 300
        end
    end
    if EG.petFrame then
        EG.petFrame:ClearAllPoints()
        EG.petFrame:SetPoint("TOPLEFT", EG.page, "TOPLEFT", EG.X0, -EG.TOP_EDGE)
        EG.petFrame:SetPoint("BOTTOMRIGHT", EG.page, "BOTTOMRIGHT", -EG.EDGE, bot)
    end
end

local function PY()
    if coroutine.running and coroutine.running() then coroutine.yield() end
end

EG.WIN_BUF = 3

function EG.WindowRange(n)
    local sc = EG.scroll
    local v, viewH = 0, 0
    if sc then
        local okv, vv = pcall(sc.GetVerticalScroll, sc)
        if okv and type(vv) == "number" then v = vv end
        local okh, hh = pcall(sc.GetHeight, sc)
        if okh and type(hh) == "number" then viewH = hh end
    end
    if viewH <= 0 then viewH = 520 end
    local step = EG.ROW_H + EG.ROW_GAP
    if step <= 0 then step = 1 end
    local lo = math.floor((v - EG.LIST_PAD) / step) + 1 - EG.WIN_BUF
    local hi = math.ceil((v + viewH - EG.LIST_PAD) / step) + 1 + EG.WIN_BUF
    if lo < 1 then lo = 1 end
    if n and n > 0 and lo > n then lo = n end
    if n and hi > n then hi = n end
    if hi < lo then hi = lo end
    return lo, hi
end

function EG.NeedWindow()
    local n = #(EG.pool or {})
    if n == 0 then return end
    local lo, hi = EG.WindowRange(n)
    if lo ~= EG.__winLo or hi ~= EG.__winHi then EG.PaintList() end
end

function EG.PaintList()
    local list = {}
    for _, rec in ipairs(B or {}) do
        local id = rec[1]
        local terr = BookTerr(rec)
        local pass = (EG.view == "all")
            or (EG.view == "todo" and not IsFound(id))
            or (EG.view == "ally" and terr == "A")
            or (EG.view == "horde" and terr == "H")
            or (EG.view == "contested" and terr == "C")
        if pass then list[#list + 1] = rec end
    end
    EG.pool = list
    local n = #list
    local lo, hi = EG.WindowRange(n)
    local rowH = EG.ROW_H + EG.ROW_GAP
    local slots = hi - lo + 1
    if slots < 1 then slots = 1 end

    for k, rr in pairs(EG.rows or {}) do rr:Hide() end
    local painted = 0
    for k = 1, slots do
        local idx = lo + k - 1
        local rec = list[idx]
        if rec then
            local r = EG.rows[k]
            if not r then r = Row(k) end
            PaintRow(r, idx, EG.LIST_PAD + (idx - 1) * rowH, rec, ((idx - 1) % 2 == 1))
            painted = painted + 1
            if painted % 4 == 0 then PY() end
        end
    end

    local y = EG.LIST_PAD + n * rowH
    if n == 0 then
        local r = EG.rows and EG.rows[1]
        if not r then r = Row(1) end
        r:ClearAllPoints()
        r:SetPoint("TOPLEFT", EG.child, "TOPLEFT", EG.LIST_PAD, -y)
        r:SetHeight(EG.ROW_H)
        r:Show()
        r.__z = false
        SetRowHover(r, false)
        r.a:SetText(L["这个筛选下没有条目 —— 40 本都找齐了？"])
        r.b:SetText("")
        r.c:SetText("")
        r.d:SetText("")
        r.chk:Hide()
        r.icon:SetTexture("")
        r.__it, r.__mark, r.__rec = nil, nil, nil
        r.sep:Hide()
        y = y + EG.ROW_H + EG.LIST_PAD
    elseif EG.rows[1] then
        EG.rows[1].sep:SetShown(not EG.rows[1].__huiCard)
        y = y - EG.ROW_GAP + EG.LIST_PAD
    end

    EG.child:SetHeight(y)
    if EG.UpdateVScroll then EG.UpdateVScroll() end
    EG.__winLo, EG.__winHi = lo, hi
end

function EG.Render()
    if not EG.built then return end
    EG.found = Found()
    EG.view = View()
    EG.ScanAuto()
    EG.PickFilter()

    local sub = CurSub()
    local isRw = sub == "rewards"
    local isBag = sub == "bag"
    local isBm = sub == "bm"
    local isPets = sub == "pets"
    local isTorch = sub == "torch"
    local isBanner = sub == "banner"
    local isRoutes = sub == "routes"
    local isCard = isPets or isTorch or isBanner
    local isFull = isRw or isBag or isBm or isCard or isRoutes
    if EG.listCard then EG.listCard:SetShown(not isRoutes) end
    EG.scroll:SetShown(not isFull)
    if EG.UpdateVScroll then EG.UpdateVScroll() end
    EG.note:SetShown(not isFull)
    local booksVis = isRw or (not isFull)
    EG.prog:SetShown(booksVis)
    if EG.bar then EG.bar:SetShown(booksVis) end
    for _, lab in pairs(EG.tickLabs or {}) do lab:SetShown(booksVis) end
    for _, bt in pairs(EG.filterBtns or {}) do bt:SetShown(booksVis) end
    if EG.rwBtn then EG.rwBtn:SetShown(booksVis) end
    if EG.routeBtn then EG.routeBtn:SetShown(booksVis) end
    if EG.mapSetBtn then EG.mapSetBtn:SetShown(booksVis) end
    if EG.routeFrame then EG.routeFrame:SetShown(isRoutes) end
    PaintNav()
    if EG.rwBtn then PaintRwBtn() end
    if EG.routeBtn then PaintRouteBtn() end
    if EG.rwFrame then
        EG.rwFrame:SetShown(isRw)
        if isRw then
            EG.rwFrame:SetPoint("TOPLEFT", EG.page, "TOPLEFT", EG.X0, -EG.RW_TOP)
            PaintRewards()
        end
    end
    if EG.bagFrame then
        EG.bagFrame:SetShown(isBag)
        if isBag then
            if EG.bmFrame then EG.bmFrame:Hide() end
            if EG.petFrame then EG.petFrame:Hide() end
            PaintBag() return
        end
    end
    if EG.bmFrame then
        EG.bmFrame:SetShown(isBm)
        if isBm then
            if EG.petFrame then EG.petFrame:Hide() end
            PaintBM() return
        end
    end
    if EG.petFrame then
        EG.petFrame:SetShown(isCard)
        if isPets then PaintPets(PETS, false) return end
        if isTorch then PaintPets(TOYS, true) return end
        if isBanner then PaintPets(BANNER, true, true) return end
    end
    if EG.routeFrame then
        EG.routeFrame:SetShown(isRoutes)
        if isRoutes then
            if EG.bagFrame then EG.bagFrame:Hide() end
            if EG.bmFrame then EG.bmFrame:Hide() end
            if EG.petFrame then EG.petFrame:Hide() end
            PaintRoutes() return
        end
    end
    if isBag or isBm or isCard then return end

    EG.PaintList()
    PaintProgress()
    if EG.needNames then EG.ScheduleSweep() end
    if ns.ExploreMapRefresh then pcall(ns.ExploreMapRefresh) end
end

function EG.RequestRender()
    if not EG.built then return end
    if not (ns.PaintJob and ns.IdleJobs) then
        EG.Render()
        return
    end
    if ns.PaintJob.Active("Explore") then
        EG.__pend = true
        return
    end
    ns.PaintJob.Run("Explore", function() EG.Render() end, function()
        if EG.__pend then
            EG.__pend = false
            EG.RequestRender()
        end
    end)
end

function EG.Open()
    if not EG.built then return end
    EG._sweepFails = 0
    if EG.needNames then EG.ScheduleSweep() end
    EG.RequestRender()
end

function EG.ShowSub(key)
    if not EG.built then return end
    SetSub(key)
end

function EG.FocusPet(itemID)
    if not EG.built then return end
    SetSub("pets")
    if not itemID then return end
    local idx
    for i, id in ipairs(EG.petIds or {}) do
        if id == itemID then idx = i break end
    end
    if not idx then return end
    local card = EG.petCards and EG.petCards[idx]
    if not card then return end
    local pieces = card.__huiBorderPieces
    local function PulseEdge(on)
        local ac = (ns.hui and ns.hui.ACCENT) or { 0.27, 0.75, 0.45 }
        if pieces then
            for _, tex in ipairs(pieces) do
                if on then
                    tex:SetVertexColor(ac[1], ac[2], ac[3])
                    tex:SetAlpha(1)
                else
                    tex:SetVertexColor(1, 1, 1)
                    tex:SetAlpha(0.10)
                end
            end
        elseif card.SetBackdropBorderColor then
            if on then
                card:SetBackdropBorderColor(ac[1], ac[2], ac[3], 1)
            else
                card:SetBackdropBorderColor(1, 1, 1, 0.08)
            end
        end
    end
    local step = 0
    if C_Timer and C_Timer.NewTicker then
        C_Timer.NewTicker(0.22, function(t)
            step = step + 1
            if step >= 6 then
                PulseEdge(false)
                t:Cancel()
                return
            end
            PulseEdge(step % 2 == 1)
        end)
    end
end

function EG.Refresh()
    if not EG.built then return end
    EG.RequestRender()
end

function EG.Build(page)
    if EG.built or EG.building then return end
    EG.building = true
    ns.PhasedStart(56, coroutine.create(function()
    if EG.built then return end
    EG.found = Found()
    EG.view = View()

    EG.navBtns = {}
    local labelHost = CreateFrame("Frame", nil, page)
    local navY = 0
    local nlab = MakeFS(labelHost, 16, C_GREY, "LEFT")
    coroutine.yield()
    nlab:SetPoint("TOPLEFT", page, "TOPLEFT", EG.NAV_X + EG.NAV_PAD + 2, -EG.NAV_TOP)
    nlab:SetText(L["收集"])
    navY = navY + EG.NAV_GROUP_H
    do
        local bt = NewButton(page, L["40本书"], EG.NAV_W, EG.NAV_ITEM_H, 16)
        bt:SetPoint("TOPLEFT", page, "TOPLEFT", EG.NAV_X + EG.NAV_PAD, -(EG.NAV_TOP + navY))
        local fs = bt:GetFontString()
        fs:ClearAllPoints()
        fs:SetPoint("LEFT", bt, "LEFT", 5 + EG.NAV_ICON + 5, 0)
        fs:SetJustifyH("LEFT")
        bt.__huiKeepTextColor = true
        bt.__icon = bt:CreateTexture(nil, "ARTWORK")
        bt.__icon:SetSize(EG.NAV_ICON, EG.NAV_ICON)
        bt.__icon:SetPoint("LEFT", bt, "LEFT", 5, 0)
        bt.__icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
        if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(bt.__icon) end
        bt.__icon:SetTexture("Interface\\Icons\\inv_misc_book_11")
        bt.__pv = MakeFS(bt, 14, C_GOLD, "RIGHT")
        bt.__pv:SetPoint("RIGHT", bt, "RIGHT", -6, 0)
        bt.__pv:SetText("0/40")
        bt:SetScript("OnClick", function() SetSub("books") end)
        EG.navBtns["books"] = bt
        coroutine.yield()
        EG.navBooks = bt
        navY = navY + EG.NAV_ITEM_H + EG.NAV_GAP
    end
    do
        local bt = NewButton(page, L["睡袋"], EG.NAV_W, EG.NAV_ITEM_H, 16)
        bt:SetPoint("TOPLEFT", page, "TOPLEFT", EG.NAV_X + EG.NAV_PAD, -(EG.NAV_TOP + navY))
        local fs = bt:GetFontString()
        fs:ClearAllPoints()
        fs:SetPoint("LEFT", bt, "LEFT", 5 + EG.NAV_ICON + 5, 0)
        fs:SetJustifyH("LEFT")
        bt.__huiKeepTextColor = true
        bt.__icon = bt:CreateTexture(nil, "ARTWORK")
        bt.__icon:SetSize(EG.NAV_ICON, EG.NAV_ICON)
        bt.__icon:SetPoint("LEFT", bt, "LEFT", 5, 0)
        bt.__icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
        if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(bt.__icon) end
        bt.__icon:SetTexture("Interface\\Icons\\inv_misc_bag_08")
        bt:SetScript("OnClick", function() SetSub("bag") end)
        EG.navBtns["bag"] = bt
        coroutine.yield()
        EG.navBag = bt
        navY = navY + EG.NAV_ITEM_H + EG.NAV_GAP
    end
    do
        local bt = NewButton(page, L["战斗法师"], EG.NAV_W, EG.NAV_ITEM_H, 16)
        bt:SetPoint("TOPLEFT", page, "TOPLEFT", EG.NAV_X + EG.NAV_PAD, -(EG.NAV_TOP + navY))
        local fs = bt:GetFontString()
        fs:ClearAllPoints()
        fs:SetPoint("LEFT", bt, "LEFT", 5 + EG.NAV_ICON + 5, 0)
        fs:SetJustifyH("LEFT")
        bt.__huiKeepTextColor = true
        bt.__icon = bt:CreateTexture(nil, "ARTWORK")
        bt.__icon:SetSize(EG.NAV_ICON, EG.NAV_ICON)
        bt.__icon:SetPoint("LEFT", bt, "LEFT", 5, 0)
        bt.__icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
        if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(bt.__icon) end
        bt.__icon:SetTexture("Interface\\Icons\\inv_sword_05")
        bt:SetScript("OnClick", function() SetSub("bm") end)
        EG.navBtns["bm"] = bt
        EG.navBM = bt
        coroutine.yield()
        navY = navY + EG.NAV_ITEM_H + EG.NAV_GAP
    end

    do
        local glab = MakeFS(labelHost, 16, C_GREY, "LEFT")
        glab:SetPoint("TOPLEFT", page, "TOPLEFT", EG.NAV_X + EG.NAV_PAD + 2, -(EG.NAV_TOP + navY))
        coroutine.yield()
        glab:SetText(L["宠物"])
        navY = navY + EG.NAV_GROUP_H
    end
    do
        local bt = NewButton(page, L["小动物"], EG.NAV_W, EG.NAV_ITEM_H, 16)
        bt:SetPoint("TOPLEFT", page, "TOPLEFT", EG.NAV_X + EG.NAV_PAD, -(EG.NAV_TOP + navY))
        local fs = bt:GetFontString()
        fs:ClearAllPoints()
        fs:SetPoint("LEFT", bt, "LEFT", 5 + EG.NAV_ICON + 5, 0)
        fs:SetJustifyH("LEFT")
        bt.__huiKeepTextColor = true
        bt.__icon = bt:CreateTexture(nil, "ARTWORK")
        bt.__icon:SetSize(EG.NAV_ICON, EG.NAV_ICON)
        bt.__icon:SetPoint("LEFT", bt, "LEFT", 5, 0)
        bt.__icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
        if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(bt.__icon) end
        bt.__icon:SetTexture("Interface\\Icons\\ability_hunter_beastcall")
        bt:SetScript("OnClick", function() SetSub("pets") end)
        EG.navBtns["pets"] = bt
        EG.navPets = bt
        coroutine.yield()
        navY = navY + EG.NAV_ITEM_H + EG.NAV_GAP
    end

    do
        local glab = MakeFS(labelHost, 16, C_GREY, "LEFT")
        glab:SetPoint("TOPLEFT", page, "TOPLEFT", EG.NAV_X + EG.NAV_PAD + 2, -(EG.NAV_TOP + navY))
        coroutine.yield()
        glab:SetText(L["玩具"])
        navY = navY + EG.NAV_GROUP_H
    end
    do
        local bt = NewButton(page, L["守夜人火炬"], EG.NAV_W, EG.NAV_ITEM_H, 16)
        bt:SetPoint("TOPLEFT", page, "TOPLEFT", EG.NAV_X + EG.NAV_PAD, -(EG.NAV_TOP + navY))
        local fs = bt:GetFontString()
        fs:ClearAllPoints()
        fs:SetPoint("LEFT", bt, "LEFT", 5 + EG.NAV_ICON + 5, 0)
        fs:SetJustifyH("LEFT")
        bt.__huiKeepTextColor = true
        bt.__icon = bt:CreateTexture(nil, "ARTWORK")
        bt.__icon:SetSize(EG.NAV_ICON, EG.NAV_ICON)
        bt.__icon:SetPoint("LEFT", bt, "LEFT", 5, 0)
        bt.__icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
        if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(bt.__icon) end
        bt.__icon:SetTexture("Interface\\Icons\\inv_torch_lit")
        bt:SetScript("OnClick", function() SetSub("torch") end)
        EG.navBtns["torch"] = bt
        coroutine.yield()
        EG.navTorch = bt
        navY = navY + EG.NAV_ITEM_H + EG.NAV_GAP
    end
    do
        local bt = NewButton(page, L["血色旗帜"], EG.NAV_W, EG.NAV_ITEM_H, 16)
        bt:SetPoint("TOPLEFT", page, "TOPLEFT", EG.NAV_X + EG.NAV_PAD, -(EG.NAV_TOP + navY))
        local fs = bt:GetFontString()
        fs:ClearAllPoints()
        fs:SetPoint("LEFT", bt, "LEFT", 5 + EG.NAV_ICON + 5, 0)
        fs:SetJustifyH("LEFT")
        bt.__huiKeepTextColor = true
        bt.__icon = bt:CreateTexture(nil, "ARTWORK")
        bt.__icon:SetSize(EG.NAV_ICON, EG.NAV_ICON)
        bt.__icon:SetPoint("LEFT", bt, "LEFT", 5, 0)
        bt.__icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
        if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(bt.__icon) end
        bt.__icon:SetTexture("Interface\\Icons\\inv_misc_token_scarletcrusade")
        bt:SetScript("OnClick", function() SetSub("banner") end)
        EG.navBtns["banner"] = bt
        EG.navBanner = bt
        navY = navY + EG.NAV_ITEM_H + EG.NAV_GAP
    end

    do
        local glab = MakeFS(labelHost, 16, C_GREY, "LEFT")
        glab:SetPoint("TOPLEFT", page, "TOPLEFT", EG.NAV_X + EG.NAV_PAD + 2, -(EG.NAV_TOP + navY))
        coroutine.yield()
        glab:SetText(L["速通"])
        navY = navY + EG.NAV_GROUP_H
    end
    do
        local bt = NewButton(page, L["跑图"], EG.NAV_W, EG.NAV_ITEM_H, 16)
        bt:SetPoint("TOPLEFT", page, "TOPLEFT", EG.NAV_X + EG.NAV_PAD, -(EG.NAV_TOP + navY))
        local fs = bt:GetFontString()
        fs:ClearAllPoints()
        fs:SetPoint("LEFT", bt, "LEFT", 5 + EG.NAV_ICON + 5, 0)
        fs:SetJustifyH("LEFT")
        bt.__huiKeepTextColor = true
        bt.__icon = bt:CreateTexture(nil, "ARTWORK")
        bt.__icon:SetSize(EG.NAV_ICON, EG.NAV_ICON)
        bt.__icon:SetPoint("LEFT", bt, "LEFT", 5, 0)
        bt.__icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
        if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(bt.__icon) end
        bt.__icon:SetTexture("Interface\\Icons\\Ability_Druid_FlightForm")
        bt:SetScript("OnClick", function() SetSub("routes") end)
        EG.navBtns["routes"] = bt
        coroutine.yield()
        EG.navRoutes = bt
        navY = navY + EG.NAV_ITEM_H + EG.NAV_GAP
    end

    EG.prog = MakeFS(labelHost, 14, C_TEXT, "RIGHT")
    EG.prog:SetPoint("TOPRIGHT", page, "TOPRIGHT", -(EG.EDGE + EG.LIST_PAD), -EG.TICK_Y)
    EG.note = MakeFS(labelHost, 14, { 0.55, 0.75, 0.55 }, "LEFT")
    EG.note:SetPoint("TOPLEFT", page, "TOPLEFT", EG.X0 + EG.LIST_PAD, -EG.NOTE_Y)
    EG.note:SetText(L["自动识别：金格 = 已上交；绿格 = 背包有书未上交"])

    local bar = CreateFrame("Frame", nil, page)
    bar:SetSize(EG.BAR_W, EG.BAR_H)
    bar:SetPoint("TOPLEFT", page, "TOPLEFT", EG.X0 + EG.LIST_PAD, -EG.BAR_Y)
    bar.bg = bar:CreateTexture(nil, "BACKGROUND")
    bar.bg:SetAllPoints()
    bar.bg:SetColorTexture(1, 1, 1, 0.09)
    local fill = bar:CreateTexture(nil, "ARTWORK")
    fill:SetColorTexture(1, 0.82, 0, 0.9)
    fill:SetPoint("TOPLEFT", bar, "TOPLEFT", 0, 0)
    fill:SetPoint("BOTTOMLEFT", bar, "BOTTOMLEFT", 0, 0)
    fill:SetWidth(0)
    EG.tickLabs = {}
    for _, at in ipairs({ EG.NECK_AT, EG.RING_AT, EG.CHOICE_AT }) do
        local x = math.floor(EG.BAR_W * at / #B)
        local tick = bar:CreateTexture(nil, "OVERLAY")
        tick:SetColorTexture(1, 1, 1, 0.35)
        tick:SetSize(1, EG.BAR_H + 6)
        tick:SetPoint("TOPLEFT", bar, "TOPLEFT", x, -4)
        local lab = MakeFS(labelHost, 14, C_DIM, "CENTER")
        lab:SetPoint("TOP", page, "TOPLEFT", EG.X0 + EG.LIST_PAD + x, -EG.TICK_Y)
        lab:SetText(at == EG.NECK_AT and L["10本 项链"]
            or at == EG.RING_AT and L["20本 戒指"] or L["25本 三选一"])
        EG.tickLabs[at] = lab
    end
    EG.barFill = fill
    EG.bar = bar

    EG.filterBtns = {}
    local FAC_COLOR = {
        ally = { 0x3F / 255, 0x7F / 255, 0xA0 / 255 },
        horde = { 0xC7 / 255, 0x4A / 255, 0x3C / 255 },
        contested = { 0xD9 / 255, 0xB9 / 255, 0x3C / 255 },
    }
    coroutine.yield()
    for fi, f in ipairs(EG.FILTERS) do
        local bt = CreateFrame("Button", nil, page, "BackdropTemplate")
        bt:SetSize(EG.TOOL_W, EG.TOOL_H)
        bt:SetPoint("TOPLEFT", page, "TOPLEFT",
                    EG.X0 + EG.LIST_PAD + (fi - 1) * (EG.TOOL_W + EG.TOOL_GAP), -EG.TOOL_Y)
        bt.__key = f.key
        bt.__baseColor = FAC_COLOR[f.key]
        bt.__huiKeepTextColor = true
        if ns.hui and ns.hui.SkinButton then ns.hui.SkinButton(bt) end
        local tf
        if f.icon then
            local ic = bt:CreateTexture(nil, "ARTWORK")
            ic:SetSize(16, 16)
            ic:SetPoint("LEFT", bt, "LEFT", 8, 0)
            ic:SetTexture(f.icon)
            tf = MakeFS(bt, 14, C_DIM, "LEFT")
            tf:SetPoint("LEFT", ic, "RIGHT", 4, 0)
            tf:SetPoint("RIGHT", bt, "RIGHT", -8, 0)
        else
            tf = MakeFS(bt, 14, C_DIM, "CENTER")
            tf:SetAllPoints()
        end
        tf:SetText(f.text)
        bt:SetFontString(tf)
        bt:SetScript("OnClick", function(self)
            local db = ns.DB()
            db.explore = db.explore or {}
            db.explore.view = (db.explore.view == self.__key) and "all" or self.__key
            if CurSub() == "rewards" then db.explore.subPage = "books" end
            EG.RequestRender()
            ns.PlaySound(1)
        end)
        bt:SetScript("OnEnter", function(self)
            if self.__key ~= EG.view then
                if self.__baseColor then
                    local c = self.__baseColor
                    self:GetFontString():SetTextColor(min(1, c[1] * 1.25), min(1, c[2] * 1.25), min(1, c[3] * 1.25))
                else
                    self:GetFontString():SetTextColor(Unpack(C_WHITE))
                end
            end
        end)
        bt:SetScript("OnLeave", function(self) PaintFilter(self, self.__key == EG.view) end)
        coroutine.yield()
        EG.filterBtns[f.key] = bt
    end

    do
        local rw = CreateFrame("Button", nil, page, "BackdropTemplate")
        rw:SetSize(EG.TOOL_W, EG.TOOL_H)
        rw:SetPoint("LEFT", EG.filterBtns.todo, "RIGHT", 8, 0)
        local rf = MakeFS(rw, 14, C_RW, "CENTER")
        rf:SetAllPoints()
        rf:SetText(L["奖励"] .. " ★")
        rw:SetFontString(rf)
        rw.__huiKeepTextColor = true
        if ns.hui and ns.hui.SkinButton then ns.hui.SkinButton(rw) end
        rw:SetScript("OnClick", function()
            SetSub(CurSub() == "rewards" and "books" or "rewards")
        end)
        rw:SetScript("OnEnter", function(self)
            if CurSub() ~= "rewards" then
                self:GetFontString():SetTextColor(Unpack(C_RW_HI))
            end
        end)
        rw:SetScript("OnLeave", function() PaintRwBtn() end)
        EG.rwBtn = rw
    end

    do
        local rb = CreateFrame("Button", nil, page, "BackdropTemplate")
        rb:SetSize(EG.TOOL_W, EG.TOOL_H)
        rb:SetPoint("LEFT", EG.rwBtn, "RIGHT", 8, 0)
        local rf = MakeFS(rb, 14, C_RW, "CENTER")
        rf:SetAllPoints()
        rf:SetText(L["找书HUD"])
        rb:SetFontString(rf)
        rb.__huiKeepTextColor = true
        if ns.hui and ns.hui.SkinButton then ns.hui.SkinButton(rb) end
        rb:SetScript("OnClick", function()
            if ns.ExploreMapToggle then pcall(ns.ExploreMapToggle) end
            PaintRouteBtn()
        end)
                coroutine.yield()
        rb:SetScript("OnEnter", function(self)
            self:GetFontString():SetTextColor(Unpack(C_RW_HI))
        end)
        rb:SetScript("OnLeave", function() PaintRouteBtn() end)
        EG.routeBtn = rb
    coroutine.yield()
    end

    do
        local gb = CreateFrame("Button", nil, page, "BackdropTemplate")
        gb:SetSize(EG.TOOL_H, EG.TOOL_H)
        gb:SetPoint("TOPRIGHT", page, "TOPRIGHT", -EG.EDGE, -EG.TOOL_Y)
        if ns.hui and ns.hui.SkinButton then ns.hui.SkinButton(gb) end
        gb.gear = gb:CreateTexture(nil, "ARTWORK")
        gb.gear:SetAllPoints()
        gb.gear:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\textures\\DF_Settings")
        gb.gear:SetAlpha(0.7)
        gb:SetScript("OnEnter", function(self)
            self.gear:SetAlpha(1)
            if GameTooltip then
                GameTooltip:SetOwner(self, "ANCHOR_BOTTOM")
                GameTooltip:SetText(L["探索地图设置"], 1, 0.82, 0.24)
                GameTooltip:Show()
            end
        end)
        gb:SetScript("OnLeave", function(self)
            self.gear:SetAlpha(0.7)
            if GameTooltip then GameTooltip:Hide() end
        end)
        gb:SetScript("OnClick", function()
            if ns.ExploreMapSettingsToggle then pcall(ns.ExploreMapSettingsToggle) end
        end)
        coroutine.yield()
        EG.mapSetBtn = gb
    end

    local listCard = CreateFrame("Frame", nil, page, "BackdropTemplate")
    listCard:SetBackdrop({
        bgFile = "Interface\\Buttons\\WHITE8x8",
        edgeFile = "Interface\\Buttons\\WHITE8x8",
        edgeSize = 1,
    })
    listCard:SetBackdropColor(1, 1, 1, 0.03)
    coroutine.yield()
    listCard:SetBackdropBorderColor(1, 1, 1, 0.05)
    EG.listCard = listCard

    local navCard = CreateFrame("Frame", nil, page, "BackdropTemplate")
    navCard:SetBackdrop({
        bgFile = "Interface\\Buttons\\WHITE8x8",
        edgeFile = "Interface\\Buttons\\WHITE8x8",
        edgeSize = 1,
    })
    navCard:SetBackdropColor(1, 1, 1, 0.03)
    navCard:SetBackdropBorderColor(1, 1, 1, 0.05)
    EG.navCard = navCard

    if ns.hui and ns.hui.SkinPopup then
        ns.hui.SkinPopup(listCard, 6)
        ns.hui.SkinPopup(navCard, 6)
    end
    coroutine.yield()
    do
        local cardLvl = listCard:GetFrameLevel()
        EG.cardLvl = cardLvl
        navCard:SetFrameLevel(cardLvl)
        for _, fr in ipairs({ page:GetChildren() }) do
            if fr ~= listCard and fr ~= navCard then
                fr:SetFrameLevel(math.max(fr:GetFrameLevel(), cardLvl + 2))
            end
        end
        local tl = CreateFrame("Frame", nil, page)
        tl:SetFrameLevel(cardLvl + 2)
        for _, rg in ipairs({ page:GetRegions() }) do
            rg:SetParent(tl)
        end
        coroutine.yield()
        EG.textLayer = tl
    end

    local scroll = CreateFrame("ScrollFrame", nil, page)
    scroll:EnableMouseWheel(true)
    scroll:SetScript("OnMouseWheel", function(_, delta)
        DG.WheelScroll(EG.scroll, EG.child, delta)
        if EG.UpdateVScroll then EG.UpdateVScroll() end
    end)
    local child = CreateFrame("Frame", nil, scroll)
    child:SetSize(EG.RIGHT_W - 2 * EG.LIST_PAD, 10)
    child:SetPoint("TOPLEFT", scroll, "TOPLEFT", EG.LIST_PAD, 0)
    scroll:SetScrollChild(child)
    EG.scroll, EG.child = scroll, child

    local hlAcc = 0
    child:SetScript("OnUpdate", function(_, el)
        hlAcc = hlAcc + el
        if hlAcc < 0.1 then return end
        hlAcc = 0
        EG.SyncHover()
    end)

    coroutine.yield()
    local track = CreateFrame("Frame", nil, page, "BackdropTemplate")
    if ns.hui and ns.hui.BuildCapsule then
        ns.hui.BuildCapsule(track, 3, ns.hui.layer.L2)
    else
        track:SetBackdrop({
            bgFile = "Interface\\Buttons\\WHITE8x8",
            edgeFile = "Interface\\Buttons\\WHITE8x8",
            edgeSize = 1,
        })
        track:SetBackdropColor(0, 0, 0, 0.25)
        track:SetBackdropBorderColor(1, 1, 1, 0.08)
    end
    track:SetWidth(9)
    track:SetPoint("TOPRIGHT", scroll, "TOPRIGHT", -1, -2)
    track:SetPoint("BOTTOMRIGHT", scroll, "BOTTOMRIGHT", -1, 2)
    track:SetFrameLevel((scroll:GetFrameLevel() or 0) + 10)
    track:Hide()
    local thumb = CreateFrame("Button", nil, track)
    thumb:SetWidth(6)
    thumb:EnableMouse(true)
    local tp, tx = nil, nil
    if ns.hui and ns.hui.BuildCapsule then
        tp = ns.hui.BuildCapsule(thumb, 2, ns.hui.layer.L4)
    else
        tx = thumb:CreateTexture(nil, "OVERLAY")
        tx:SetAllPoints()
        tx:SetColorTexture(1, 1, 1, 0.30)
    end
    thumb:SetScript("OnEnter", function()
        if tp then
            local L5 = ns.hui.layer.L5
            for _, t in ipairs(tp) do t:SetVertexColor(L5[1], L5[2], L5[3]) end
        elseif tx then
            tx:SetColorTexture(1, 1, 1, 0.45)
        end
    end)
    thumb:SetScript("OnLeave", function()
        if tp then
            local L4 = ns.hui.layer.L4
            for _, t in ipairs(tp) do t:SetVertexColor(L4[1], L4[2], L4[3]) end
        elseif tx then
            tx:SetColorTexture(1, 1, 1, 0.30)
        end
    end)
    thumb:SetPoint("TOP", track, "TOP", 0, -1)
    function EG.UpdateVScroll()
        local sc, ch = EG.scroll, EG.child
        if not (sc and ch) then return end
        if not sc:IsShown() then track:Hide() return end
        local viewH = sc:GetHeight()
        local contentH = ch:GetHeight()
        if contentH <= viewH + 2 or viewH <= 0 then track:Hide() return end
        track:Show()
        local trackH = track:GetHeight() - 2
        local maxScroll = contentH - viewH
        local vpos = sc.GetVerticalScroll and sc:GetVerticalScroll() or 0
        if type(vpos) ~= "number" then vpos = 0 end
        local frac = math.min(1, math.max(0, vpos / maxScroll))
        local th = math.max(24, trackH * viewH / contentH)
        thumb:SetHeight(th)
        thumb:ClearAllPoints()
        thumb:SetPoint("TOP", track, "TOP", 0, -1 - frac * (trackH - th))
    end
    scroll:SetScript("OnVerticalScroll", function()
        EG.UpdateVScroll()
        if EG.NeedWindow then EG.NeedWindow() end
    end)
    thumb:SetScript("OnMouseDown", function(self, btn)
        if btn ~= "LeftButton" then return end
        local scale = UIParent and UIParent:GetEffectiveScale() or 1
        local cy0 = select(2, GetCursorPosition()) / scale
        local sc0 = EG.scroll:GetVerticalScroll()
        if type(sc0) ~= "number" then sc0 = 0 end
        self:SetScript("OnUpdate", function(self)
            local cy = select(2, GetCursorPosition()) / scale
            local trackH = track:GetHeight() - 2
            local span = trackH - thumb:GetHeight()
            if span <= 0 then return end
            local maxScroll = EG.child:GetHeight() - EG.scroll:GetHeight()
            EG.scroll:SetVerticalScroll(math.min(maxScroll, math.max(0, sc0 + (cy0 - cy) / span * maxScroll)))
            if EG.NeedWindow then EG.NeedWindow() end
        end)
    end)
    thumb:SetScript("OnMouseUp", function(self)
        self:SetScript("OnUpdate", nil)
    end)
    thumb:SetScript("OnHide", function(self)
        self:SetScript("OnUpdate", nil)
    end)
    coroutine.yield()

    EG.rows = {}

    local rw = CreateFrame("Frame", nil, page)
    EG.rwFrame = rw
    EG.rwRows = {}
    EG.rwCards = {}
    do
        coroutine.yield()
        local PADX, GAP, ROW_H = EG.LIST_PAD, 8, 44
        local CW = math.floor((EG.RIGHT_W - 2 * PADX - 2 * GAP) / 3)
        local maxN = 2
        for _, tier in ipairs(REWARDS) do
            local n = tier.choices and #tier.choices or 2
            if n > maxN then maxN = n end
        coroutine.yield()
        end
        local CH = 28 + maxN * ROW_H + 8
        local y = 14
        for ti, tier in ipairs(REWARDS) do
            local card = CreateFrame("Frame", nil, rw, "BackdropTemplate")
            card:SetHeight(CH)
            local ox = PADX + (ti - 1) * (CW + GAP)
            card:SetPoint("TOPLEFT", rw, "TOPLEFT", ox, -y)
            card:SetPoint("TOPRIGHT", rw, "TOPLEFT", ox + CW, -y)
            if ns.hui and ns.hui.SkinPopup then
                ns.hui.SkinPopup(card, 6, nil, ns.hui.layer.L2)
            else
                card:SetBackdrop({
                    bgFile = "Interface\\Buttons\\WHITE8x8",
                    edgeFile = "Interface\\Buttons\\WHITE8x8",
                    edgeSize = 1,
                })
                card:SetBackdropColor(1, 1, 1, 0.03)
                card:SetBackdropBorderColor(1, 1, 1, 0.05)
            end
            local hd = MakeFS(card, 14, C_WHITE, "LEFT")
            hd:SetPoint("TOPLEFT", card, "TOPLEFT", 12, -10)
            hd.__tier = ti
            EG["rwHead" .. ti] = hd
            card.hd = hd
            local lv = MakeFS(card, 14, C_GREY, "RIGHT")
            lv:SetPoint("TOPRIGHT", card, "TOPRIGHT", -12, -12)
            card.lv = lv
            local st = MakeFS(card, 14, C_GREY, "RIGHT")
            st:SetPoint("TOPRIGHT", card, "TOPRIGHT", -12, -12)
            card.state = st
            local sides = { "A", "H" }
            if tier.choices then
                coroutine.yield()
                sides = {}
                for ci in ipairs(tier.choices) do sides[#sides + 1] = ci end
            end
            for ri, side in ipairs(sides) do
                local row = CreateFrame("Button", nil, card)
                row:RegisterForClicks("LeftButtonUp", "RightButtonUp")
                row:SetHeight(ROW_H)
                row:SetPoint("TOPLEFT", card, "TOPLEFT", 10, -(28 + (ri - 1) * ROW_H))
                row:SetPoint("TOPRIGHT", card, "TOPRIGHT", -10, -(28 + (ri - 1) * ROW_H))
                row.side, row.tier = side, tier
                row.icon = row:CreateTexture(nil, "ARTWORK")
                row.icon:SetSize(36, 36)
                row.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
                if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(row.icon) end
                row.icon:SetPoint("LEFT", row, "LEFT", 2, 0)
                row.name = MakeFS(row, 14, C_TEXT, "LEFT")
                row.name:SetPoint("TOPLEFT", row.icon, "TOPRIGHT", 9, -1)
                row.name:SetPoint("RIGHT", row, "RIGHT", 0, 0)
                row.name:SetWordWrap(false)
                row.meta = MakeFS(row, 14, C_GREY, "LEFT")
                row.meta:SetPoint("BOTTOMLEFT", row.icon, "BOTTOMRIGHT", 9, 1)
                row.meta:SetPoint("RIGHT", row, "RIGHT", 0, 0)
                row.meta:SetWordWrap(false)
                row:SetScript("OnEnter", function(self) EG.RewardTip(self, true) end)
                row:SetScript("OnLeave", function(self) EG.RewardTip(self, false) end)
                row:SetScript("OnClick", function(self, button)
                    if DG and DG.ItemShiftClick then DG.ItemShiftClick(self, button) end
                end)
                EG.rwRows[#EG.rwRows + 1] = row
            end
            EG.rwCards[ti] = card
        end
        y = y + CH + 8
        local card = CreateFrame("Frame", nil, rw, "BackdropTemplate")
        card:SetPoint("TOPLEFT", rw, "TOPLEFT", PADX, -y)
        card:SetPoint("TOPRIGHT", rw, "TOPRIGHT", -PADX, -y)
        if ns.hui and ns.hui.SkinPopup then
            ns.hui.SkinPopup(card, 6, nil, ns.hui.layer.L2)
        else
            card:SetBackdrop({
                bgFile = "Interface\\Buttons\\WHITE8x8",
                edgeFile = "Interface\\Buttons\\WHITE8x8",
                edgeSize = 1,
            })
            card:SetBackdropColor(1, 1, 1, 0.03)
            card:SetBackdropBorderColor(1, 1, 1, 0.05)
        end
        EG.howCard = card
        local HT = ns.ExploreHowTo or {}
        local iw = EG.RIGHT_W - 2 * PADX - 26
        local cy = 12
        local htitle = MakeFS(card, 16, C_WHITE, "LEFT")
        htitle:SetPoint("TOPLEFT", card, "TOPLEFT", 13, -cy)
        htitle:SetText(HT.title or L["如何获得奖励"])
        cy = cy + 28
        local hintro = MakeFS(card, 14, C_TEXT, "LEFT")
        hintro:SetPoint("TOPLEFT", card, "TOPLEFT", 13, -cy)
        hintro:SetWidth(iw)
        hintro:SetText(HT.intro or "")
        cy = cy + 22
        local hdetail = MakeFS(card, 14, { 0.94, 0.78, 0.35 }, "LEFT")
        hdetail:SetPoint("TOPLEFT", card, "TOPLEFT", 13, -cy)
        hdetail:SetWidth(iw)
        hdetail:SetText(HT.detail or "")
        cy = cy + 34
        EG.howSteps = {}
        coroutine.yield()
        local SGAP = 16
        local stepW = math.floor((iw - 2 * SGAP) / 3)
        local maxStepH = 0
        for si, st in ipairs(HT.steps or {}) do
            local sx = (si - 1) * (stepW + SGAP)
            local num = MakeFS(card, 14, C_GOLD, "LEFT")
            num:SetPoint("TOPLEFT", card, "TOPLEFT", 13 + sx, -cy)
            num:SetText(tostring(si))
            local sl = MakeFS(card, 14, C_TEXT, "LEFT")
            sl:SetPoint("TOPLEFT", card, "TOPLEFT", 13 + sx + 18, -cy)
            sl:SetWidth(stepW - 18)
            sl:SetWordWrap(false)
            sl:SetText(st.t or "")
            EG.howSteps[si] = sl
            local dl = MakeFS(card, 14, C_GREY, "LEFT")
            dl:SetPoint("TOPLEFT", card, "TOPLEFT", 13 + sx + 18, -cy - 20)
            dl:SetWidth(stepW - 18)
            dl:SetText(st.d or "")
            local sw = dl:GetStringWidth()
            if type(sw) ~= "number" or sw <= 0 then sw = #(st.d or "") * 9 end
            local lines = math.max(1, math.ceil(sw / math.max(1, stepW - 18)))
            local h = 20 + lines * 17 + 6
            if h > maxStepH then maxStepH = h end
            coroutine.yield()
        end
        coroutine.yield()
        cy = cy + maxStepH
        card:SetHeight(cy + 4)
        y = y + cy + 8
        local mh = MakeFS(rw, 16, C_WHITE, "LEFT")
        mh:SetPoint("TOPLEFT", rw, "TOPLEFT", PADX, -y)
        EG.rwMageHead = mh
        mh:Hide()
        coroutine.yield()
        y = y + 30
        EG.rwMageLines = {}
        local MB = ns.ExploreMageBonus
        for li, txt in ipairs(MB and MB.desc or {}) do
            local ln = MakeFS(rw, 14, C_DIM, "LEFT")
            ln:SetPoint("TOPLEFT", rw, "TOPLEFT", PADX, -y)
            ln:SetText(txt)
            EG.rwMageLines[li] = ln
            ln:Hide()
            y = y + 22
        end
        rw:SetHeight(y + 4)
        rw:Hide()
    end

    coroutine.yield()
    local bag = CreateFrame("Frame", nil, page)
    EG.bagFrame = bag
    EG.bagMode, EG.bagSel = "detail", nil
    do
        local CW = EG.RIGHT_W
        local LW = 280
        local RWd = CW - LW - 16
        EG.bagRWd = RWd

        local title = MakeFS(bag, 16, C_WHITE, "LEFT")
        title:SetPoint("TOPLEFT", bag, "TOPLEFT", 8, -8)
        title:SetText(L["舒适睡袋"])
        title:SetWordWrap(false)

        local fc = CreateFrame("Frame", nil, bag)
        coroutine.yield()
        fc:SetSize(186, 24)
        fc:SetPoint("TOPLEFT", bag, "TOPLEFT", 86, -8)
        EG.bagFacBtns = {}
        for fi, f in ipairs({ "A", "H" }) do
            local bt = NewButton(fc, f == "A" and L["联盟领地"] or L["部落领地"], 88, 24, 14)
            bt:SetPoint("TOPLEFT", fc, "TOPLEFT", (fi - 1) * 96 + 2, 0)
            bt.__huiKeepTextColor = true
            local tf = bt:GetFontString()
            if tf then
                tf:ClearAllPoints()
                tf:SetPoint("LEFT", bt, "LEFT", 25, 0)
                tf:SetPoint("RIGHT", bt, "RIGHT", -3, 0)
                tf:SetJustifyH("CENTER")
            end
            local ic = bt:CreateTexture(nil, "OVERLAY")
            ic:SetSize(16, 16)
            ic:SetPoint("LEFT", bt, "LEFT", 6, 0)
            ic:SetTexture(BAG_FAC_ICON[f])
            if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(ic) end
            bt.__icon = ic
            bt:SetScript("OnClick", function()
                local db = ns.DB()
                db.explore = db.explore or {}
                db.explore.bagFac = f
                EG.RequestRender()
                ns.PlaySound(1)
            end)
            EG.bagFacBtns[f] = bt
        end
        local tag1 = MakeFS(bag, 14, C_GOLD, "LEFT")
        tag1:SetPoint("TOPLEFT", fc, "TOPRIGHT", 8, 0)
        tag1:SetText(L["需 14 级"])
        tag1:SetWordWrap(false)
        local tag2 = MakeFS(bag, 14, C_GREY, "LEFT")
        tag2:SetPoint("TOPLEFT", tag1, "TOPRIGHT", 8, 0)
        tag2:SetText(L["全程无 NPC · 点地面物件触发"])
        tag2:SetWordWrap(false)
        EG.bagProg = MakeFS(bag, 14, C_GOLD, "RIGHT")
        EG.bagProg:SetPoint("TOPRIGHT", bag, "TOPRIGHT", -166, -8)
        EG.bagProg:SetWordWrap(false)

        local NOTE_H = 110
        EG.bagNoteH = NOTE_H
        local lc = CreateFrame("Frame", nil, bag)
        lc:SetSize(LW, 10)
        lc:SetPoint("TOPLEFT", bag, "TOPLEFT", 0, -32)
        lc:SetPoint("BOTTOMRIGHT", bag, "BOTTOMRIGHT", -(RWd + 8), NOTE_H + 16)
        coroutine.yield()
        EG.bagLC = lc
        EG.bagRows = {}
        for i, e in ipairs(BAG_CHAIN) do
            local r = CreateFrame("Button", nil, lc, "BackdropTemplate")
            r:SetHeight(36)
            r:SetPoint("TOPLEFT", lc, "TOPLEFT", 8, -((i - 1) * 40))
            r:SetPoint("TOPRIGHT", lc, "TOPRIGHT", -8, -((i - 1) * 40))
            r.tint = r:CreateTexture(nil, "BORDER")
            r.tint:SetAllPoints()
            r.tint:SetColorTexture(1, 1, 1, 0)
            r.tint:Hide()
            if not HuiRowFX(r, 10, 10) then
                r:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8x8" })
                r:SetBackdropColor(1, 1, 1, 0.02)
                if ns.hui and ns.hui.BuildCapsule then
                    r.__hov = ns.hui.BuildCapsule(r, 10, ns.hui.layer.L4, 1, 2)
                    for _, t in ipairs(r.__hov) do t:Hide() end
                end
            end
            r.no = MakeFS(r, 16, C_GOLD, "LEFT")
            r.no:SetPoint("TOPLEFT", r, "TOPLEFT", 8, -4)
            r.no:SetWordWrap(false)
            r.t = MakeFS(r, 16, C_TEXT, "LEFT")
            r.t:SetPoint("TOPLEFT", r, "TOPLEFT", 32, -4)
            r.t:SetWordWrap(false)
            r.p = MakeFS(r, 14, C_GREY, "LEFT")
            r.p:SetPoint("BOTTOMLEFT", r, "BOTTOMLEFT", 32, 3)
            r.p:SetWordWrap(false)
            r.st = MakeFS(r, 14, C_GREY, "RIGHT")
            r.st:SetPoint("TOPRIGHT", r, "TOPRIGHT", -8, -4)
            r.st:SetWordWrap(false)
            r.__step = e
            r:SetScript("OnClick", function(self)
                EG.bagSel = self.__step.key
                EG.bagMode = "detail"
                EG.RequestRender()
                ns.PlaySound(1)
            end)
            r:SetScript("OnEnter", function(self) self.__hl = true BagRowTint(self) end)
            r:SetScript("OnLeave", function(self) self.__hl = false BagRowTint(self) end)
            EG.bagRows[i] = r
        end
        local eb = CreateFrame("Button", nil, bag, "BackdropTemplate")
        eb:SetSize(150, 24)
        eb:SetPoint("TOPRIGHT", bag, "TOPRIGHT", -8, -8)
        eb.__huiKeepTextColor = true
        if ns.hui and ns.hui.SkinButton then ns.hui.SkinButton(eb) end
        local ef = MakeFS(eb, 14, C_GOLD, "CENTER")
        ef:SetAllPoints()
        ef:SetText(L["任务线奖励总览"] .. " ›")
        ef:SetWordWrap(false)
        eb:SetFontString(ef)
        eb:SetScript("OnClick", function()
            EG.bagMode = (EG.bagMode == "total") and "detail" or "total"
            EG.RequestRender()
            ns.PlaySound(1)
        end)
        EG.bagRwBtn = eb
        EG.bagProg:ClearAllPoints()
        EG.bagProg:SetPoint("TOPRIGHT", eb, "TOPLEFT", -8, 0)

        local rc
        local rs = CreateFrame("ScrollFrame", nil, bag)
        rs:EnableMouseWheel(true)
        rs:SetScript("OnMouseWheel", function(_, delta)
            DG.WheelScroll(rs, rc, delta)
        end)
        rc = CreateFrame("Frame", nil, rs)
        rc:SetSize(RWd, 10)
        rs:SetScrollChild(rc)
        rs:SetPoint("TOPLEFT", bag, "TOPLEFT", LW + 8, -32)
        rs:SetPoint("BOTTOMRIGHT", bag, "BOTTOMRIGHT", -8, EG.bagNoteH + 16)
        EG.bagScroll, EG.bagChild = rs, rc

        local nc = CreateFrame("Frame", nil, bag)
        nc:SetHeight(EG.bagNoteH)
        nc:SetPoint("BOTTOMLEFT", bag, "BOTTOMLEFT", 8, 8)
        nc:SetPoint("BOTTOMRIGHT", bag, "BOTTOMRIGHT", -8, 8)
        ns.hui.SkinPopup(nc, 8, nil, ns.hui.layer.L2)
        EG.bagNote = nc
        local nHead = MakeFS(nc, 16, C_GOLD, "LEFT")
        nHead:SetPoint("TOPLEFT", nc, "TOPLEFT", 8, -8)
        nHead:SetText(L["注释"])
        nHead:SetWordWrap(false)
        EG.bagNoteItems = {}
        local function NoteRow(id, tail, py)
            local nb = CreateFrame("Button", nil, nc)
            nb:SetHeight(22)
            nb:SetPoint("TOPLEFT", nc, "TOPLEFT", 8, -py)
            nb.__id = id
            local ic = nb:CreateTexture(nil, "ARTWORK")
            ic:SetSize(18, 18)
            ic:SetTexCoord(0.07, 0.93, 0.07, 0.93)
            if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(ic) end
            ic:SetPoint("LEFT", nb, "LEFT", 0, 0)
            nb.icon = ic
            local nf = MakeFS(nb, 14, C_TEXT, "LEFT")
            nf:SetPoint("LEFT", ic, "RIGHT", 4, 0)
            nf:SetPoint("RIGHT", nb, "RIGHT", 0, 0)
            nb.nm = nf
            nb:SetScript("OnEnter", function(self) EG.BagChipTip(self, true) end)
            nb:SetScript("OnLeave", function(self) EG.BagChipTip(self, false) end)
            local tx = MakeFS(nc, 14, C_GREY, "LEFT")
            tx:SetPoint("LEFT", nb, "RIGHT", 8, 0)
            tx:SetPoint("RIGHT", nc, "RIGHT", -8, 0)
            tx:SetText(tail)
            EG.bagNoteItems[#EG.bagNoteItems + 1] = nb
        end
        NoteRow(216619, L["：吃一口立即回 500 血、12 秒内再回 1050，并回复法力 / 50 怒气 / 100 能量，5 分钟冷却、最多叠 30 个；"], 36)
        local nl2 = MakeFS(nc, 14, C_GREY, "LEFT")
        nl2:SetPoint("TOPLEFT", nc, "TOPLEFT", 8, -58)
        nl2:SetPoint("RIGHT", nc, "RIGHT", -8, 0)
        nl2:SetText(L["旧版的休息经验加成在无限服已移除，当应急干粮就好；吃下去还会附一波「方便零嘴」（0.75 秒 60% 移速）；"])
        nl2:SetWordWrap(false)
        NoteRow(211527, L["：躺满 1 分钟 +1% 经验、最多 3 层、持续 2 小时；铺开需原地站 15 秒、睡袋落地留 20 分钟，冷却 1 小时，队友可同躺"], 80)

        local det = CreateFrame("Frame", nil, rc)
        det:SetWidth(RWd)
        det:SetPoint("TOPLEFT", rc, "TOPLEFT", 0, 0)
        ns.hui.SkinPopup(det, 8, nil, ns.hui.layer.L2)
        EG.bagDetail = det
        local dTitle = MakeFS(det, 16, C_WHITE, "LEFT")
        dTitle:SetPoint("TOPLEFT", det, "TOPLEFT", 8, -8)
        dTitle:SetWordWrap(false)
        EG.bagDT = dTitle
        local dId = MakeFS(det, 14, C_GREY, "LEFT")
        dId:SetPoint("LEFT", dTitle, "RIGHT", 8, 0)
        dId:SetWordWrap(false)
        EG.bagDId = dId
        local dCo = CreateFrame("Button", nil, det)
        dCo:SetPoint("TOPRIGHT", det, "TOPRIGHT", -8, -8)
        dCo:SetHeight(20)
        dCo:SetWidth(60)
        local dcf = MakeFS(dCo, 14, C_GOLD, "CENTER")
        dcf:SetAllPoints()
        dCo.fs = dcf
        dCo:SetScript("OnClick", function(self)
            local loc = self.__loc
            if loc then EG.MarkPoint(loc.area, loc.x, loc.y) end
            ns.PlaySound(1)
        end)
        dCo:SetScript("OnEnter", function(self)
            self.fs:SetTextColor(Unpack(C_WHITE))
            if GameTooltip then
                GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
                GameTooltip:ClearLines()
                GameTooltip:AddLine(L["点击在地图上定位"], 0.8, 0.8, 0.8, true)
                GameTooltip:Show()
            end
        end)
        dCo:SetScript("OnLeave", function(self)
            self.fs:SetTextColor(Unpack(C_GOLD))
            if GameTooltip then pcall(GameTooltip.Hide, GameTooltip) end
        end)
        EG.bagDCo = dCo
        local dCoHint = MakeFS(det, 14, C_GREY, "RIGHT")
        dCoHint:SetPoint("RIGHT", dCo, "LEFT", 8, 0)
        dCoHint:SetText(L["点击坐标在地图上定位"])
        dCoHint:SetWordWrap(false)
        coroutine.yield()
        EG.bagDCoHint = dCoHint
        EG.bagDL, EG.bagDV = {}, {}
        local FIELDS = { L["状态："], L["可接等级："], L["起始："], L["阵营："] }
        for fi = 1, 4 do
            local lab = MakeFS(det, 14, C_GREY, "LEFT")
            lab:SetPoint("TOPLEFT", det, "TOPLEFT", 8, -(34 + (fi - 1) * 24))
            lab:SetText(FIELDS[fi])
            lab:SetWordWrap(false)
            local val = MakeFS(det, 14, C_TEXT, "LEFT")
            val:SetPoint("LEFT", lab, "RIGHT", 2, 0)
            val:SetWordWrap(false)
            EG.bagDL[fi], EG.bagDV[fi] = lab, val
        end
        local dRwH0 = MakeFS(det, 16, C_GOLD, "LEFT")
        dRwH0:SetPoint("TOPLEFT", det, "TOPLEFT", 8, -132)
        dRwH0:SetText(L["任务奖励"])
        dRwH0:SetWordWrap(false)
        EG.bagDRH0 = dRwH0
        local dRwH = MakeFS(det, 14, { 0.81, 0.65, 0.21 }, "LEFT")
        dRwH:SetWordWrap(false)
        dRwH:Hide()
        EG.bagDRH = dRwH
        local dRwH2 = MakeFS(det, 14, { 0.81, 0.65, 0.21 }, "LEFT")
        dRwH2:SetText(L["你还会获得："])
        dRwH2:SetWordWrap(false)
        dRwH2:Hide()
        EG.bagDRH2 = dRwH2
        local dXpH = MakeFS(det, 16, C_GOLD, "LEFT")
        dXpH:SetText(L["收获"])
        dXpH:SetWordWrap(false)
        dXpH:Hide()
        EG.bagDXH = dXpH
        local dXp = MakeFS(det, 14, C_TEXT, "LEFT")
        dXp:SetWordWrap(false)
        EG.bagDX = dXp
        local dNH = MakeFS(det, 16, C_GOLD, "LEFT")
        dNH:SetText(L["作者备注"])
        dNH:SetWordWrap(false)
        dNH:Hide()
        EG.bagDNH = dNH
        local dN = MakeFS(det, 14, C_GREY, "LEFT")
        dN:SetJustifyV("TOP")
        coroutine.yield()
        dN:Hide()
        EG.bagDN = dN
        EG.bagNSegs = {}
        for i = 1, 6 do
            local sf = MakeFS(det, 14, C_GREY, "LEFT")
            sf:SetJustifyV("TOP")
            sf:Hide()
            local sb = CreateFrame("Button", nil, det)
            sb:SetHeight(18)
            local bf = MakeFS(sb, 14, C_GOLD, "CENTER")
            bf:SetAllPoints()
            sb.fs = bf
            sb:SetScript("OnClick", function(self)
                local lc2 = self.__loc
                if lc2 and lc2.x then EG.MarkPoint(lc2.area, lc2.x, lc2.y) end
                ns.PlaySound(1)
            end)
            sb:SetScript("OnEnter", function(self) self.fs:SetTextColor(Unpack(C_WHITE)) end)
            sb:SetScript("OnLeave", function(self) self.fs:SetTextColor(Unpack(C_GOLD)) end)
            sb:Hide()
            EG.bagNSegs[i] = { fs = sf, btn = sb }
        end

        local tot = CreateFrame("Frame", nil, rc)
        tot:SetWidth(RWd)
        tot:SetPoint("TOPLEFT", rc, "TOPLEFT", 0, 0)
        ns.hui.SkinPopup(tot, 8, nil, ns.hui.layer.L2)
        tot:Hide()
        EG.bagTotal = tot
        local tTitle = MakeFS(tot, 16, C_WHITE, "LEFT")
        tTitle:SetPoint("TOPLEFT", tot, "TOPLEFT", 8, -8)
        tTitle:SetText(L["任务线奖励总览"])
        tTitle:SetWordWrap(false)
        local fcard = CreateFrame("Frame", nil, tot)
        fcard:SetSize(RWd - 16, 84)
        fcard:SetPoint("TOPLEFT", tot, "TOPLEFT", 8, -32)
        ns.hui.SkinPopup(fcard, 8, nil, ns.hui.layer.L3)
        local fIcon = fcard:CreateTexture(nil, "ARTWORK")
        fIcon:SetSize(36, 36)
        fIcon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
        if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(fIcon) end
        fIcon:SetPoint("TOPLEFT", fcard, "TOPLEFT", 8, -8)
        EG.bagFIcon = fIcon
        local fName = MakeFS(fcard, 14, C_TEXT, "LEFT")
        fName:SetPoint("TOPLEFT", fcard, "TOPLEFT", 52, -8)
        fName:SetWordWrap(false)
        EG.bagFName = fName
        local fDesc = MakeFS(fcard, 14, C_GREY, "LEFT")
        fDesc:SetPoint("TOPLEFT", fcard, "TOPLEFT", 52, -30)
        fDesc:SetPoint("RIGHT", fcard, "RIGHT", -8, 0)
        fDesc:SetJustifyV("TOP")
        coroutine.yield()
        fDesc:SetHeight(50)
        fDesc:SetText(L[BAG_FINAL_DESC])
        EG.bagTotHeads = {}
        for gi, g in ipairs(BAG_RW_GROUPS) do
            local gh = MakeFS(tot, 14, C_GOLD, "LEFT")
            gh:SetText(L[g.head])
            gh:SetWordWrap(false)
            EG.bagTotHeads[gi] = gh
        coroutine.yield()
        end

        EG.bagChips = {}
        for i = 1, 20 do
            local c = CreateFrame("Button", nil, rc)
            c:SetSize(40, 28)
            ns.hui.SkinPopup(c, 8, nil, ns.hui.layer.L3, 1, true)
            c.icon = c:CreateTexture(nil, "ARTWORK")
            c.icon:SetSize(24, 24)
            c.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
            if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(c.icon) end
            c.icon:SetPoint("LEFT", c, "LEFT", 4, 0)
            c.nm = MakeFS(c, 14, C_TEXT, "LEFT")
            c.nm:SetPoint("LEFT", c.icon, "RIGHT", 5, 0)
            c.nm:SetPoint("RIGHT", c, "RIGHT", -6, 0)
            c.nm:SetWordWrap(false)
            c:SetScript("OnEnter", function(self) EG.BagChipTip(self, true) end)
            c:SetScript("OnLeave", function(self) EG.BagChipTip(self, false) end)
            c:Hide()
            EG.bagChips[i] = c
        end
        bag:Hide()
    end
coroutine.yield()

    local bm = CreateFrame("Frame", nil, page)
    EG.bmFrame = bm
    do
        local CW = EG.RIGHT_W
        local btitle = MakeFS(bm, 16, C_WHITE, "LEFT")
        btitle:SetPoint("TOPLEFT", bm, "TOPLEFT", 8, -8)
        btitle:SetText(L["战斗法师"])
        btitle:SetWordWrap(false)
        EG.bmHint = MakeFS(bm, 14, C_GREY, "LEFT")
        EG.bmHint:SetPoint("LEFT", btitle, "RIGHT", 8, 0)
        EG.bmHint:SetText(L["法师专属内容 ——「理解」为法师职业副技能"])
        EG.bmHint:SetWordWrap(false)
coroutine.yield()

        EG.bmTabBtns = {}
        local tx = 8
        for _, t in ipairs(BM_TABS) do
            local bt = CreateFrame("Button", nil, bm, "BackdropTemplate")
            bt:SetSize(96, 24)
            bt:SetPoint("TOPLEFT", bm, "TOPLEFT", tx, -32)
            local tf = MakeFS(bt, 14, C_DIM, "CENTER")
            tf:SetAllPoints()
            tf:SetText(t.text)
            bt:SetFontString(tf)
            bt.__huiKeepTextColor = true
            if ns.hui and ns.hui.SkinButton then ns.hui.SkinButton(bt) end
            tf:SetAllPoints()
            tf:SetFont(ns.FONT, 14, "")
            bt:SetScript("OnClick", function()
                local db = ns.DB()
                db.explore = db.explore or {}
                db.explore.bmTab = t.key
                EG.RequestRender()
                ns.PlaySound(1)
            end)
            EG.bmTabBtns[t.key] = bt
            tx = tx + 104
        end

        local chain = CreateFrame("Frame", nil, bm)
        chain:SetHeight(72)
        chain:SetPoint("TOPLEFT", bm, "TOPLEFT", 8, -62)
        chain:SetPoint("TOPRIGHT", bm, "TOPRIGHT", -8, -62)
        coroutine.yield()
        ns.hui.SkinPopup(chain, 8, nil, ns.hui.layer.L2)
        EG.bmChain = chain
        EG.bmNodes, EG.bmArrows = {}, {}
        for i = 1, 5 do
            local nd = CreateFrame("Button", nil, chain)
            nd:SetSize(90, 58)
            nd.tint = nd:CreateTexture(nil, "BORDER")
            nd.tint:SetAllPoints()
            nd.tint:SetColorTexture(1, 1, 1, 0)
            nd.tint:Hide()
            if ns.hui and ns.hui.BuildCapsule then
                nd.__hov = ns.hui.BuildCapsule(nd, 12, ns.hui.layer.L4, 1, 2)
                for _, t in ipairs(nd.__hov) do t:Hide() end
            end
            nd.icon = nd:CreateTexture(nil, "ARTWORK")
            nd.icon:SetSize(20, 20)
            nd.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
            if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(nd.icon) end
            nd.icon:SetPoint("TOPLEFT", nd, "TOPLEFT", 8, -8)
            nd.t = MakeFS(nd, 14, C_TEXT, "LEFT")
            nd.t:SetPoint("TOPLEFT", nd, "TOPLEFT", 36, -6)
            nd.t:SetWordWrap(false)
            nd.sub = MakeFS(nd, 14, C_GREY, "LEFT")
            nd.sub:SetPoint("BOTTOMLEFT", nd, "BOTTOMLEFT", 8, 8)
            nd.sub:SetWordWrap(false)
            nd:SetScript("OnEnter", function(self)
                self.__hl = true
                PaintBMNode(self)
                if self.__id then
                    EG.BagChipTip(self, true)
                elseif GameTooltip then
                    GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
                    GameTooltip:ClearLines()
                    GameTooltip:AddLine(self.t:GetText() or "", 1, 0.82, 0, true)
                    local st = self.sub:GetText()
                    if st ~= "" then GameTooltip:AddLine(st, 0.8, 0.8, 0.8, true) end
                    GameTooltip:Show()
                end
            end)
            nd:SetScript("OnLeave", function(self)
                self.__hl = false
                PaintBMNode(self)
                if GameTooltip then pcall(GameTooltip.Hide, GameTooltip) end
            end)
            EG.bmNodes[i] = nd
            if i < 5 then
                local ar = MakeFS(chain, 16, C_GOLD, "CENTER")
                ar:SetText("›")
                ar:SetWordWrap(false)
                ar:Hide()
                EG.bmArrows[i] = ar
            end
        end

        local dsf = CreateFrame("ScrollFrame", nil, bm)
        dsf:EnableMouseWheel(true)
        local dcc
        dsf:SetScript("OnMouseWheel", function(_, delta)
            DG.WheelScroll(dsf, dcc, delta)
        end)
        dcc = CreateFrame("Frame", nil, dsf)
        dcc:SetSize(CW - 16, 10)
        dsf:SetScrollChild(dcc)
        dsf:SetPoint("TOPLEFT", bm, "TOPLEFT", 8, -142)
        dsf:SetPoint("BOTTOMRIGHT", bm, "BOTTOMRIGHT", -8, -8)
        coroutine.yield()
        ns.hui.SkinPopup(dsf, 8, nil, ns.hui.layer.L2)
        EG.bmDetail, EG.bmDChild = dsf, dcc
        EG.bmSteps = {}
        for i = 1, 5 do
            local st = CreateFrame("Frame", nil, dcc)
            st.num = MakeFS(st, 14, C_GOLD, "LEFT")
            st.num:SetPoint("TOPLEFT", st, "TOPLEFT", 8, -3)
            st.num:SetWordWrap(false)
            st.t = MakeFS(st, 14, C_TEXT, "LEFT")
            st.t:SetPoint("TOPLEFT", st, "TOPLEFT", 26, -2)
            st.t:SetWordWrap(false)
            st.sub = MakeFS(st, 14, C_GREY, "LEFT")
            st.sub:SetPoint("LEFT", st.t, "RIGHT", 10, 0)
            st.sub:SetWordWrap(false)
            st.loc = CreateFrame("Button", nil, st)
            st.loc:SetHeight(18)
            st.loc.fs = MakeFS(st.loc, 12, C_GOLD, "CENTER")
            st.loc.fs:SetAllPoints()
            st.loc:SetPoint("TOPRIGHT", st, "TOPRIGHT", 0, -2)
            st.loc:SetScript("OnClick", function(self)
                local lc = self.__loc
                if lc and lc.x then EG.MarkPoint(lc.area, lc.x, lc.y) end
                ns.PlaySound(1)
            end)
            st.loc:SetScript("OnEnter", function(self)
                self.fs:SetTextColor(Unpack(C_WHITE))
                if GameTooltip then
                    GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
                    GameTooltip:ClearLines()
                    GameTooltip:AddLine(L["点击在地图上定位"], 0.8, 0.8, 0.8, true)
                    GameTooltip:Show()
                end
            end)
            st.loc:SetScript("OnLeave", function(self)
                self.fs:SetTextColor(Unpack(C_GOLD))
                coroutine.yield()
                if GameTooltip then pcall(GameTooltip.Hide, GameTooltip) end
            end)
            st.lines = {}
            for j = 1, 3 do
                local lf = MakeFS(st, 14, C_TEXT, "LEFT")
                lf:SetJustifyV("TOP")
                lf:Hide()
                st.lines[j] = lf
            end
            st.sep = st:CreateTexture(nil, "BORDER")
            st.sep:SetHeight(1)
            st.sep:SetColorTexture(1, 1, 1, 0.055)
            st.sep:SetPoint("BOTTOMLEFT", st, "BOTTOMLEFT", 0, 0)
            st.sep:SetPoint("BOTTOMRIGHT", st, "BOTTOMRIGHT", 0, 0)
            st:Hide()
            EG.bmSteps[i] = st
        end

        local ov = CreateFrame("Frame", nil, bm)
        ov:SetPoint("TOPLEFT", bm, "TOPLEFT", 8, -62)
        ov:SetPoint("BOTTOMRIGHT", bm, "BOTTOMRIGHT", -8, -8)
        EG.bmOv = ov
        local ot = MakeFS(ov, 14, C_GOLD, "LEFT")
        ot:SetPoint("TOPLEFT", ov, "TOPLEFT", 8, -8)
        ot:SetText(L["提升技能"])
        ot:SetWordWrap(false)
        local oi = MakeFS(ov, 14, C_TEXT, "LEFT")
        oi:SetPoint("TOPLEFT", ov, "TOPLEFT", 8, -30)
        oi:SetPoint("RIGHT", ov, "RIGHT", -8, 0)
        oi:SetText(L["未翻译的卷轴有四种，每一种需要的理解技能等级都更高。一种卷轴变灰之后就不会再提升技能：在技能到达它变灰的等级之前，换成下一种。"])
        local tc = CreateFrame("Frame", nil, ov)
        tc:SetPoint("TOPLEFT", ov, "TOPLEFT", 8, -78)
        tc:SetPoint("TOPRIGHT", ov, "TOPRIGHT", -8, -78)
        tc:SetHeight(8 + 20 + 2 + #BM_TIERS * 36 - 2 + 6)
        ns.hui.SkinPopup(tc, 8, nil, ns.hui.layer.L2)
        EG.bmOvCard = tc
        local oh = MakeFS(tc, 14, C_GREY, "LEFT")
        oh:SetPoint("TOPLEFT", tc, "TOPLEFT", 16, -6)
        oh:SetText(L["未翻译的卷轴"])
        oh:SetWordWrap(false)
        local ohr = MakeFS(tc, 14, C_GREY, "RIGHT")
        ohr:SetPoint("TOPRIGHT", tc, "TOPRIGHT", -203, -6)
        ohr:SetText(L["可破译于"])
        ohr:SetWordWrap(false)
        local ohg = MakeFS(tc, 14, C_GREY, "RIGHT")
        ohg:SetPoint("TOPRIGHT", tc, "TOPRIGHT", -113, -6)
        ohg:SetText(L["变灰于"])
        ohg:SetWordWrap(false)
        local oht = MakeFS(tc, 14, C_GREY, "RIGHT")
        oht:SetPoint("TOPRIGHT", tc, "TOPRIGHT", -20, -6)
        oht:SetText(L["卷轴等级"])
        oht:SetWordWrap(false)
        local ohsep = tc:CreateTexture(nil, "BORDER")
        ohsep:SetHeight(1)
        ohsep:SetColorTexture(1, 1, 1, 0.09)
        coroutine.yield()
        ohsep:SetPoint("TOPLEFT", tc, "TOPLEFT", 8, -28)
        ohsep:SetPoint("TOPRIGHT", tc, "TOPRIGHT", -8, -28)
        EG.bmOvRows = {}
        for ti = 1, #BM_TIERS do
            local rw = CreateFrame("Frame", nil, tc)
            rw:SetHeight(32)
            rw:SetPoint("TOPLEFT", tc, "TOPLEFT", 8, -(32 + (ti - 1) * 36))
            rw:SetPoint("TOPRIGHT", tc, "TOPRIGHT", -8, -(32 + (ti - 1) * 36))
            rw.nm = MakeFS(rw, 14, C_TEXT, "LEFT")
            rw.nm:SetPoint("TOPLEFT", rw, "TOPLEFT", 8, -4)
            rw.nm:SetPoint("RIGHT", rw, "RIGHT", -240, 0)
            rw.nm:SetWordWrap(false)
            rw.req = MakeFS(rw, 14, C_GREY, "RIGHT")
            rw.req:SetPoint("RIGHT", rw, "RIGHT", -195, 0)
            rw.gray = MakeFS(rw, 14, C_GREY, "RIGHT")
            rw.gray:SetPoint("RIGHT", rw, "RIGHT", -105, 0)
            rw.tier = MakeFS(rw, 14, C_GOLD, "RIGHT")
            rw.tier:SetPoint("RIGHT", rw, "RIGHT", -12, 0)
            rw.tier:SetWordWrap(false)
            rw:Hide()
            EG.bmOvRows[ti] = rw
        end
coroutine.yield()

        EG.bmTierBtns = {}
        local cx = 8
        for ti, t in ipairs(BM_TIERS) do
            local bt = CreateFrame("Button", nil, bm, "BackdropTemplate")
            bt:SetSize(118, 24)
            bt:SetPoint("TOPLEFT", bm, "TOPLEFT", cx, -62)
            local tf = MakeFS(bt, 14, C_DIM, "CENTER")
            tf:SetAllPoints()
            tf:SetText(format(L["理解(%d) · %s"], t.req, t.tier))
            bt:SetFontString(tf)
            bt.__huiKeepTextColor = true
            if ns.hui and ns.hui.SkinButton then ns.hui.SkinButton(bt) end
            tf:SetAllPoints()
            tf:SetFont(ns.FONT, 14, "")
            bt:SetScript("OnClick", function()
                EG.bmTier = ti
                EG.RequestRender()
                ns.PlaySound(1)
            end)
            EG.bmTierBtns[ti] = bt
            cx = cx + 126
        end
        local bdh = 26 + #BM_BUNDLE * 24 + 8
        local bd = CreateFrame("Frame", nil, ov)
        bd:SetHeight(bdh)
        bd:SetPoint("TOPLEFT", tc, "BOTTOMLEFT", 0, -8)
        bd:SetPoint("TOPRIGHT", tc, "BOTTOMRIGHT", 0, -8)
        ns.hui.SkinPopup(bd, 8, nil, ns.hui.layer.L2)
        EG.bmBundle = bd
        local bh = MakeFS(bd, 14, C_GREY, "LEFT")
        bh:SetPoint("TOPLEFT", bd, "TOPLEFT", 8, -6)
        coroutine.yield()
        bh:SetText(L["「一捆卷轴」开出率（17 捆样本）"])
        bh:SetWordWrap(false)
        EG.bmBundleRows = {}
        for bi, it in ipairs(BM_BUNDLE) do
            local rw = CreateFrame("Frame", nil, bd)
            rw:SetHeight(22)
            rw:SetPoint("TOPLEFT", bd, "TOPLEFT", 8, -(28 + (bi - 1) * 24))
            rw:SetPoint("TOPRIGHT", bd, "TOPRIGHT", -8, -(28 + (bi - 1) * 24))
            rw.icon = rw:CreateTexture(nil, "ARTWORK")
            rw.icon:SetSize(18, 18)
            rw.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
            if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(rw.icon) end
            rw.icon:SetPoint("LEFT", rw, "LEFT", 8, 0)
            rw.nm = MakeFS(rw, 14, C_TEXT, "LEFT")
            rw.nm:SetPoint("LEFT", rw.icon, "RIGHT", 6, 0)
            rw.nm:SetPoint("RIGHT", rw, "RIGHT", -170, 0)
            rw.nm:SetWordWrap(false)
            rw.barBg = rw:CreateTexture(nil, "BACKGROUND")
            rw.barBg:SetSize(120, 5)
            rw.barBg:SetPoint("RIGHT", rw, "RIGHT", -40, 0)
            rw.barBg:SetColorTexture(1, 1, 1, 0.09)
            rw.bar = rw:CreateTexture(nil, "ARTWORK")
            rw.bar:SetSize(math.floor(120 * it[2] / 100 + 0.5), 5)
            rw.bar:SetPoint("LEFT", rw.barBg, "LEFT", 0, 0)
            rw.bar:SetColorTexture(0.52, 0.72, 0.92, 0.9)
            rw.pct = MakeFS(rw, 14, C_GREY, "RIGHT")
            rw.pct:SetPoint("RIGHT", rw, "RIGHT", 0, 0)
            rw.pct:SetText(it[2] .. "%")
            rw.__id = it[1]
            rw:EnableMouse(true)
            rw:SetScript("OnEnter", function(self) EG.BagChipTip(self, true) end)
            rw:SetScript("OnLeave", function(self) EG.BagChipTip(self, false) end)
            EG.bmBundleRows[bi] = rw
        end
        local rs = CreateFrame("ScrollFrame", nil, bm)
        rs:EnableMouseWheel(true)
        local rcc
        rs:SetScript("OnMouseWheel", function(_, delta)
            DG.WheelScroll(rs, rcc, delta)
        end)
        rcc = CreateFrame("Frame", nil, rs)
        rcc:SetSize(CW - 16, 10)
        rs:SetScrollChild(rcc)
        rs:SetPoint("TOPLEFT", bm, "TOPLEFT", 8, -90)
        coroutine.yield()
        rs:SetPoint("BOTTOMRIGHT", bm, "BOTTOMRIGHT", -8, -8)
        EG.bmScroll, EG.bmChild = rs, rcc
        EG.bmRows = {}
        for i = 1, 12 do
            local rw2 = CreateFrame("Frame", nil, rcc, "BackdropTemplate")
            rw2:SetHeight(34)
            rw2:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8x8" })
            rw2:SetBackdropColor(1, 1, 1, 0.02)
            if not HuiRowFX(rw2, 10, 10) then
                rw2:SetBackdropColor(1, 1, 1, 0.02)
            end
            rw2:SetPoint("TOPLEFT", rcc, "TOPLEFT", 8, -((i - 1) * 38))
            rw2:SetPoint("TOPRIGHT", rcc, "TOPRIGHT", -8, -((i - 1) * 38))
            rw2.icon = rw2:CreateTexture(nil, "ARTWORK")
            rw2.icon:SetSize(20, 20)
            rw2.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
            if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(rw2.icon) end
            rw2.icon:SetPoint("LEFT", rw2, "LEFT", 8, 0)
            rw2.nm = MakeFS(rw2, 14, C_TEXT, "LEFT")
            rw2.nm:SetPoint("TOPLEFT", rw2, "TOPLEFT", 36, -4)
            rw2.nm:SetWordWrap(false)
            rw2.note = MakeFS(rw2, 14, C_GREY, "LEFT")
            rw2.note:SetPoint("BOTTOMLEFT", rw2, "BOTTOMLEFT", 36, 4)
            rw2.note:SetWordWrap(false)
            rw2.badge = MakeFS(rw2, 14, C_GREY, "RIGHT")
            rw2.badge:SetPoint("TOPRIGHT", rw2, "TOPRIGHT", -8, -4)
            rw2.badge:SetWordWrap(false)
            rw2:EnableMouse(true)
            rw2:EnableMouseWheel(true)
            rw2:SetScript("OnMouseWheel", function(_, delta)
                DG.WheelScroll(rs, rcc, delta)
            end)
            rw2:SetScript("OnEnter", function(self)
                if self.__hov then
                    for _, t in ipairs(self.__hov) do t:SetShown(true) end
                else
                    self:SetBackdropColor(1, 1, 1, 0.05)
                end
                if self.__id then EG.BagChipTip(self, true) end
            end)
            rw2:SetScript("OnLeave", function(self)
                if self.__hov then
                    for _, t in ipairs(self.__hov) do t:SetShown(false) end
                else
                    self:SetBackdropColor(1, 1, 1, 0.02)
                end
                if GameTooltip then pcall(GameTooltip.Hide, GameTooltip) end
            end)
            rw2:Hide()
            EG.bmRows[i] = rw2
        end
        coroutine.yield()
        bm:Hide()
    end

    BuildPets(page)

    do
        local root = CreateFrame("Frame", nil, page)
        root:SetPoint("TOPLEFT", page, "TOPLEFT", EG.X0, -EG.TOP_EDGE)
        root:SetPoint("BOTTOMRIGHT", page, "BOTTOMRIGHT", -EG.EDGE, EG.EDGE)
        EG.routeFrame = root
        root:Hide()
        coroutine.yield()

        EG.rtFacBtns = {}
        local FAC_BG = {
            h = "icon\\FACTION\\FactionIcon_Horde",
            a = "icon\\FACTION\\FactionIcon_Alliance",
        }
        for ki, fk in ipairs({ "h", "a" }) do
            local bt = NewButton(root, fk == "h" and L["部落"] or L["联盟"], 76, 24, 14)
            bt:SetPoint("TOPLEFT", root, "TOPLEFT", (ki - 1) * 84, 0)
            local icon = bt:CreateTexture(nil, "OVERLAY")
            icon:SetSize(16, 16)
            icon:SetPoint("LEFT", bt, "LEFT", 7, 0)
            icon:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\" .. FAC_BG[fk])
            if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(icon) end
            local bfs = bt:GetFontString()
            bfs:ClearAllPoints()
            bfs:SetPoint("TOPLEFT", bt, "TOPLEFT", 26, 0)
            bfs:SetPoint("BOTTOMRIGHT", bt, "BOTTOMRIGHT", -2, 0)
            bfs:SetJustifyH("CENTER")
            bt.__huiKeepTextColor = true
            local fk2 = fk
            bt:SetScript("OnClick", function() RtPick(fk2, RtSel(fk2)) end)
            EG.rtFacBtns[fk] = bt
        end
        coroutine.yield()

        do
            local bt = NewButton(root, "", 152, 24, 14)
            bt:SetPoint("TOPRIGHT", root, "TOPRIGHT", 0, 0)
            bt:SetScript("OnClick", function(self)
                local on
                if ns.ExploreGraveToggle then on = ns.ExploreGraveToggle() end
                PaintGraveBtn(on)
                if EG.RtMapRepaint then EG.RtMapRepaint() end
                if ns.PlaySound then ns.PlaySound(1) end
            end)
            bt:SetScript("OnEnter", function(self)
                if GameTooltip then
                    GameTooltip:SetOwner(self, "ANCHOR_BOTTOM")
                    GameTooltip:SetText(L["复活点图钉"], 1, 0.82, 0.24)
                    GameTooltip:AddLine(L["在世界地图上标出灵魂医者的位置。"], 0.85, 0.85, 0.85, true)
                    GameTooltip:Show()
                end
            end)
            bt:SetScript("OnLeave", function()
                if GameTooltip then GameTooltip:Hide() end
            end)
            EG.graveBtn = bt
            PaintGraveBtn()
            coroutine.yield()
        end

        do
            local bt = NewButton(root, "", 150, 24, 14)
            bt:SetPoint("TOPRIGHT", EG.graveBtn, "TOPLEFT", -8, 0)
            local GS_ICON = {
                native = EG.RT_GRAVE_NATIVE,
                circle = "Interface\\AddOns\\DungeonsForever\\Media\\SpiritPinCircle",
                custom = EG.RT_GRAVE_OWN,
            }
            local GS_NAME = {
                native = L["原生"],
                circle = L["圆圈自制"],
                custom = L["自制"],
            }
            local lab = MakeFS(bt, 14, C_GREY, "LEFT")
            lab:SetPoint("LEFT", bt, "LEFT", 9, 0)
            lab:SetText(L["样式："])
            local gsIcon = bt:CreateTexture(nil, "OVERLAY")
            gsIcon:SetSize(18, 18)
            gsIcon:SetPoint("LEFT", lab, "RIGHT", 5, 0)
            local bfs = bt:GetFontString()
            if bfs then
                bfs:ClearAllPoints()
                bfs:SetPoint("LEFT", gsIcon, "RIGHT", 5, 0)
                bfs:SetJustifyH("LEFT")
            end
            local function RepaintMap()
                if EG.RtMapRepaint then EG.RtMapRepaint() end
            end
            local function Sync()
                local cur = (ns.ExploreGraveStyle and ns.ExploreGraveStyle()) or "native"
                bt:SetText(GS_NAME[cur] or GS_NAME.native)
                gsIcon:SetTexture(GS_ICON[cur] or GS_ICON.native)
                gsIcon:Show()
            end
            bt:SetScript("OnClick", function()
                local cur = (ns.ExploreGraveStyle and ns.ExploreGraveStyle()) or "native"
                local function pick(v)
                    if ns.ExploreGraveStyleSet then ns.ExploreGraveStyleSet(v) end
                    Sync()
                    RepaintMap()
                    if ns.PlaySound then ns.PlaySound(1) end
                end
                local items = {}
                for _, k in ipairs({ "native", "circle", "custom" }) do
                    items[#items + 1] = {
                        text = (cur == k and "● " or "") .. GS_NAME[k],
                        icon = GS_ICON[k],
                        func = function() pick(k) end,
                    }
                end
                ns.hui.ShowMenu(items, { owner = bt, anchor = bt })
            end)
            bt:SetScript("OnEnter", function(self)
                if GameTooltip then
                    GameTooltip:SetOwner(self, "ANCHOR_BOTTOM")
                    GameTooltip:SetText(L["图钉样式"], 1, 0.82, 0.24)
                    GameTooltip:AddLine(L["选择灵魂医者图钉的显示样式。"], 0.85, 0.85, 0.85, true)
                    GameTooltip:Show()
                end
            end)
            bt:SetScript("OnLeave", function()
                if GameTooltip then GameTooltip:Hide() end
            end)
            EG.graveStyleBtn = bt
            EG.rtStyleSync = Sync
            Sync()
            coroutine.yield()
        end

        local lc = CreateFrame("Frame", nil, root)
        lc:SetWidth(RT_LIST_W)
        lc:SetPoint("TOPLEFT", root, "TOPLEFT", 0, -32)
        lc:SetPoint("BOTTOMLEFT", root, "BOTTOMLEFT", 0, 0)
        ns.hui.SkinPopup(lc, 6, nil, ns.hui.layer.L1)
        EG.rtList = lc
        EG.rtListHead = MakeFS(lc, 14, C_GREY, "LEFT")
        EG.rtListHead:SetPoint("TOPLEFT", lc, "TOPLEFT", 8, -8)
        coroutine.yield()

        EG.rtRows = {}
        for i = 1, EG.RT_MAX_TARGETS do
            if i % 3 == 0 then coroutine.yield() end
            local r = CreateFrame("Button", nil, lc, "BackdropTemplate")
            r:SetHeight(28)
            r:SetPoint("TOPLEFT", lc, "TOPLEFT", 8, -(30 + (i - 1) * 36))
            r:SetPoint("TOPRIGHT", lc, "TOPRIGHT", -8, -(30 + (i - 1) * 36))
            if ns.hui and ns.hui.BuildRoundedBG then
                local fill, border = ns.hui.BuildRoundedBG(r, 6, ns.hui.layer.L2, "both", true, 1)
                r.__huiCard = { fill = fill, border = border }
            else
                r:SetBackdrop({
                    bgFile = "Interface\\Buttons\\WHITE8x8",
                    edgeFile = "Interface\\Buttons\\WHITE8x8",
                    edgeSize = 1,
                })
                r:SetBackdropColor(1, 1, 1, 0.04)
                r:SetBackdropBorderColor(1, 1, 1, 0.10)
            end
            if ns.hui and ns.hui.BuildCapsule then
                r.__hov = ns.hui.BuildCapsule(r, 6, ns.hui.layer.L4, 1, 2)
                for _, t in ipairs(r.__hov) do t:Hide() end
            end
            r.name = MakeFS(r, 16, C_TEXT, "LEFT")
            r.name:SetPoint("LEFT", r, "LEFT", 10, 0)
            r.name:SetWidth(RT_LIST_W - 28)
            r.name:SetWordWrap(false)
            r.name:SetJustifyV("MIDDLE")
            local i2 = i
            r:SetScript("OnClick", function() RtPick(RtFac(), i2) end)
            r:SetScript("OnEnter", function(self)
                if not self.__tintOn and self.__hov then
                    for _, t in ipairs(self.__hov) do t:SetShown(true) end
                end
            end)
            r:SetScript("OnLeave", function(self)
                if self.__hov then
                    for _, t in ipairs(self.__hov) do t:SetShown(false) end
                end
            end)
            r:Hide()
            EG.rtRows[i] = r
        end
        coroutine.yield()

        local bd = CreateFrame("Frame", nil, root)
        bd:SetPoint("TOPLEFT", root, "TOPLEFT", RT_LIST_W + EG.RT_GAP, -32)
        bd:SetPoint("TOPRIGHT", root, "TOPRIGHT", 0, -32)
        bd:SetHeight(EG.RT_BODY_H)
        ns.hui.SkinPopup(bd, 6, nil, ns.hui.layer.L1)
        EG.rtBody = bd

        EG.rtTitle = MakeFS(bd, 16, C_TEXT, "LEFT")
        EG.rtTitle:SetPoint("TOPLEFT", bd, "TOPLEFT", 8, -8)
        EG.rtTitle:SetWordWrap(false)
        EG.rtZone = MakeFS(bd, 14, C_GREY, "LEFT")
        EG.rtZone:SetPoint("LEFT", EG.rtTitle, "RIGHT", 8, 0)
        EG.rtZone:SetWordWrap(false)
        EG.rtZone:Hide()
        EG.rtTime = MakeFS(bd, 14, C_GREY, "RIGHT")
        EG.rtTime:SetPoint("TOPRIGHT", bd, "TOPRIGHT", -8, -8)
        EG.rtDstBtn = CreateFrame("Button", nil, bd, "BackdropTemplate")
        EG.rtDstBtn:SetSize(24, 24)
        EG.rtDstBtn:SetPoint("LEFT", EG.rtTitle, "RIGHT", 8, 0)
        EG.rtDstBtn:SetPushedTextOffset(0, 0)
        if ns.hui and ns.hui.SkinButton then ns.hui.SkinButton(EG.rtDstBtn) end
        local pin = EG.rtDstBtn:CreateTexture(nil, "ARTWORK")
        pin:SetSize(14, 14)
        pin:SetPoint("CENTER", EG.rtDstBtn, "CENTER", 0, 0)
        pin:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\EntryPin")
        EG.rtDstBtn:SetScript("OnClick", function(self)
            if self.__go then RtGo(self.__go[1], self.__go[2], self.__go[3]) end
        end)
        EG.rtDstBtn:SetScript("OnEnter", function(self)
            RtTip(self, true)
        end)
        EG.rtDstBtn:SetScript("OnLeave", function(self)
            RtTip(self, false)
        end)
        coroutine.yield()

        EG.rtRaceBtns = {}
        for k = 1, 5 do
            local rb = NewButton(bd, "", 60, 24, 14)
            rb:SetPushedTextOffset(0, 0)
            local k2 = k
            rb:SetScript("OnClick", function()
                RtPickRace(RtFac(), RtSel(RtFac()), k2)
            end)
            rb:Hide()
            EG.rtRaceBtns[k] = rb
        end
        coroutine.yield()

        local sc = CreateFrame("ScrollFrame", nil, bd)
        sc:EnableMouseWheel(true)
        sc:SetPoint("TOPLEFT", bd, "TOPLEFT", 8, -72)
        sc:SetPoint("BOTTOMRIGHT", bd, "BOTTOMRIGHT", -8, -8)
        local child = CreateFrame("Frame", nil, sc)
        child:SetWidth(EG.RT_STEP_W)
        child:SetHeight(10)
        sc:SetScrollChild(child)
        sc:SetScript("OnMouseWheel", function(_, delta)
            if DG.WheelScroll then DG.WheelScroll(sc, child, delta) end
        end)
        EG.rtScroll, EG.rtStepsHost = sc, child

        local rtrack = CreateFrame("Frame", nil, bd, "BackdropTemplate")
        if ns.hui and ns.hui.BuildCapsule then
            ns.hui.BuildCapsule(rtrack, 3, ns.hui.layer.L2)
        else
            rtrack:SetBackdrop({
                bgFile = "Interface\\Buttons\\WHITE8x8",
                edgeFile = "Interface\\Buttons\\WHITE8x8",
                edgeSize = 1,
            })
            rtrack:SetBackdropColor(0, 0, 0, 0.25)
            rtrack:SetBackdropBorderColor(1, 1, 1, 0.08)
        end
        rtrack:SetWidth(7)
        rtrack:SetPoint("TOPRIGHT", sc, "TOPRIGHT", 7, -2)
        rtrack:SetPoint("BOTTOMRIGHT", sc, "BOTTOMRIGHT", 7, 2)
        rtrack:SetFrameLevel((sc:GetFrameLevel() or 0) + 10)
        rtrack:Hide()
        local rthumb = CreateFrame("Button", nil, rtrack)
        rthumb:SetWidth(5)
        rthumb:SetPoint("LEFT", rtrack, "LEFT", 1, 0)
        rthumb:SetPoint("RIGHT", rtrack, "RIGHT", -1, 0)
        rthumb:EnableMouse(true)
        local rtp, rtx = nil, nil
        if ns.hui and ns.hui.BuildCapsule then
            rtp = ns.hui.BuildCapsule(rthumb, 2, ns.hui.layer.L4)
        else
            rtx = rthumb:CreateTexture(nil, "OVERLAY")
            rtx:SetAllPoints()
            rtx:SetColorTexture(1, 1, 1, 0.30)
        end
        rthumb:SetScript("OnEnter", function()
            if rtp then
                local L5 = ns.hui.layer.L5
                for _, t in ipairs(rtp) do t:SetVertexColor(L5[1], L5[2], L5[3]) end
            elseif rtx then
                rtx:SetColorTexture(1, 1, 1, 0.45)
            end
        end)
        rthumb:SetScript("OnLeave", function()
            if rtp then
                local L4 = ns.hui.layer.L4
                for _, t in ipairs(rtp) do t:SetVertexColor(L4[1], L4[2], L4[3]) end
            elseif rtx then
                rtx:SetColorTexture(1, 1, 1, 0.30)
            end
        end)
        rthumb:SetPoint("TOP", rtrack, "TOP", 0, -1)
        rthumb:SetScript("OnMouseDown", function(self, btn)
            if btn ~= "LeftButton" then return end
            local scale = UIParent and UIParent:GetEffectiveScale() or 1
            local cy0 = select(2, GetCursorPosition()) / scale
            local sc0 = sc:GetVerticalScroll()
            if type(sc0) ~= "number" then sc0 = 0 end
            self:SetScript("OnUpdate", function(self)
                local cy = select(2, GetCursorPosition()) / scale
                local trackH = rtrack:GetHeight() - 2
                local span = trackH - rthumb:GetHeight()
                if span <= 0 then return end
                local maxScroll = child:GetHeight() - sc:GetHeight()
                sc:SetVerticalScroll(math.min(maxScroll, math.max(0, sc0 + (cy0 - cy) / span * maxScroll)))
            end)
        end)
        rthumb:SetScript("OnMouseUp", function(self) self:SetScript("OnUpdate", nil) end)
        rthumb:SetScript("OnHide", function(self) self:SetScript("OnUpdate", nil) end)
        sc:SetScript("OnVerticalScroll", function()
            if EG.RtScrollUpdate then EG.RtScrollUpdate() end
        end)
        function EG.RtScrollUpdate()
            if not (sc and child and sc:IsShown()) then rtrack:Hide() return end
            local viewH = sc:GetHeight()
            local contentH = child:GetHeight()
            if contentH <= viewH + 2 or viewH <= 0 then rtrack:Hide() return end
            rtrack:Show()
            local trackH = rtrack:GetHeight() - 2
            local maxScroll = contentH - viewH
            local vpos = sc.GetVerticalScroll and sc:GetVerticalScroll() or 0
            if type(vpos) ~= "number" then vpos = 0 end
            local frac = math.min(1, math.max(0, vpos / maxScroll))
            local th = math.max(24, trackH * viewH / contentH)
            rthumb:SetHeight(th)
            rthumb:ClearAllPoints()
            rthumb:SetPoint("LEFT", rtrack, "LEFT", 1, 0)
            rthumb:SetPoint("RIGHT", rtrack, "RIGHT", -1, 0)
            rthumb:SetPoint("TOP", rtrack, "TOP", 0, -1 - frac * (trackH - th))
        end
        coroutine.yield()

        local mp = CreateFrame("Frame", nil, root)
        mp:SetPoint("TOPLEFT", bd, "BOTTOMLEFT", 0, -EG.RT_GAP)
        mp:SetPoint("BOTTOMRIGHT", root, "BOTTOMRIGHT", 0, 0)
        ns.hui.SkinPopup(mp, 6, nil, ns.hui.layer.L1)
        EG.rtMap = mp
        EG.rtMapCap = MakeFS(mp, 14, C_GREY, "LEFT")
        EG.rtMapCap:SetPoint("TOPLEFT", mp, "TOPLEFT", 8, -8)
        EG.rtMapCap:SetWordWrap(false)
        local cv = CreateFrame("Frame", nil, mp)
        cv:SetSize(10, 10)
        cv:SetPoint("TOP", mp, "TOP", 0, -30)
        EG.rtMapCanvas = cv
        EG.rtMapTex = {}
        for i = 1, 24 do
            local tx = cv:CreateTexture(nil, "ARTWORK")
            tx:SetSize(10, 10)
            tx:SetPoint("TOPLEFT", cv, "TOPLEFT", 0, 0)
            tx:Hide()
            EG.rtMapTex[i] = tx
        end
        EG.rtMapTexD = {}
        for i = 1, 32 do
            local tx = cv:CreateTexture(nil, "OVERLAY")
            tx:SetDrawLayer("OVERLAY", 0)
            tx:SetSize(10, 10)
            tx:SetPoint("TOPLEFT", cv, "TOPLEFT", 0, 0)
            tx:Hide()
            EG.rtMapTexD[i] = tx
        end
        EG.rtGraveTex = {}
        for i = 1, 10 do
            local tx = cv:CreateTexture(nil, "OVERLAY")
            tx:SetDrawLayer("OVERLAY", 5)
            tx:SetSize(18, 18)
            tx:SetPoint("TOPLEFT", cv, "TOPLEFT", 0, 0)
            tx:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\SpiritPin")
            tx:Hide()
            EG.rtGraveTex[i] = tx
        end
        EG.rtGraveDisc = {}
        for i = 1, 10 do
            local tx = cv:CreateTexture(nil, "OVERLAY")
            tx:SetDrawLayer("OVERLAY", 4)
            tx:SetSize(20, 20)
            tx:SetPoint("TOPLEFT", cv, "TOPLEFT", 0, 0)
            tx:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\CheckDisc")
            tx:SetVertexColor(0.05, 0.05, 0.06, 0.88)
            tx:Hide()
            EG.rtGraveDisc[i] = tx
        end
        EG.rtGraveRing = {}
        for i = 1, 10 do
            local tx = cv:CreateTexture(nil, "OVERLAY")
            tx:SetDrawLayer("OVERLAY", 4)
            tx:SetSize(20, 20)
            tx:SetPoint("TOPLEFT", cv, "TOPLEFT", 0, 0)
            tx:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\CheckRing")
            tx:SetVertexColor(0.78, 0.74, 0.62, 0.9)
            tx:Hide()
            EG.rtGraveRing[i] = tx
        end
        EG.rtGraveRim = {}
        for i = 1, 10 do
            local tx = cv:CreateTexture(nil, "OVERLAY")
            tx:SetDrawLayer("OVERLAY", 6)
            tx:SetSize(8, 8)
            tx:SetPoint("TOPLEFT", cv, "TOPLEFT", 0, 0)
            tx:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\CheckDisc")
            tx:SetVertexColor(0.03, 0.03, 0.04, 0.92)
            tx:Hide()
            EG.rtGraveRim[i] = tx
        end
        EG.rtGraveDot = {}
        for i = 1, 10 do
            local tx = cv:CreateTexture(nil, "OVERLAY")
            tx:SetDrawLayer("OVERLAY", 6)
            tx:SetSize(6, 6)
            tx:SetPoint("TOPLEFT", cv, "TOPLEFT", 0, 0)
            tx:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\CheckDisc")
            tx:Hide()
            EG.rtGraveDot[i] = tx
        end
        local mpin = cv:CreateTexture(nil, "OVERLAY")
        mpin:SetDrawLayer("OVERLAY", 7)
        mpin:SetSize(22, 22)
        if mpin.SetAtlas then mpin:SetAtlas(RT_PIN_ATLAS) end
        if not mpin.GetAtlas or not mpin:GetAtlas() then
            mpin:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\EntryPin")
        end
        mpin:Hide()
        EG.rtMapPin = mpin
        EG.rtOvlTex = {}
        for i = 1, 4 do
            local ltx = cv:CreateTexture(nil, "OVERLAY")
            ltx:SetDrawLayer("OVERLAY", 2)
            ltx:SetSize(10, 10)
            ltx:SetPoint("TOPLEFT", cv, "TOPLEFT", 0, 0)
            ltx:Hide()
            EG.rtOvlTex[i] = ltx
        end
        coroutine.yield()

        EG.RT_STEP_H = 58
        EG.rtSteps = {}
        for i = 1, EG.RT_MAX_STEPS do
            if i % 4 == 0 then coroutine.yield() end
            local st = CreateFrame("Frame", nil, child, "BackdropTemplate")
            st:SetHeight(EG.RT_STEP_H)
            st:SetPoint("TOPLEFT", child, "TOPLEFT", 0, -((i - 1) * (EG.RT_STEP_H + 8)))
            st:SetPoint("TOPRIGHT", child, "TOPRIGHT", 0, -((i - 1) * (EG.RT_STEP_H + 8)))
            if ns.hui and ns.hui.BuildRoundedBG then
                local fill, border = ns.hui.BuildRoundedBG(st, 6, ns.hui.layer.L2, "both", true, 1)
                st.__huiCard = { fill = fill, border = border }
            end
            st:EnableMouse(true)
            local i3 = i
            st:SetScript("OnMouseDown", function(_, btn)
                if btn == "LeftButton" then EG.RtPickStep(i3) end
            end)
            st.no = CreateFrame("Frame", nil, st)
            st.no:SetSize(20, 20)
            st.no:SetPoint("TOPLEFT", st, "TOPLEFT", 8, -8)
            if ns.hui and ns.hui.SkinPopup then
                ns.hui.SkinPopup(st.no, 6, nil, ns.hui.layer.L3)
            end
            st.noTx = MakeFS(st.no, 14, C_DIM, "CENTER")
            st.noTx:SetAllPoints()
            st.act = MakeFS(st, 14, C_TEXT, "LEFT")
            st.act:SetPoint("TOPLEFT", st, "TOPLEFT", 36, -11)
            st.act:SetWordWrap(false)
            st.kind = DG.MakeBadge(st)
            st.kind:Hide()
            st.co = CreateFrame("Button", nil, st, "BackdropTemplate")
            st.co:SetSize(66, 24)
            st.co:SetPushedTextOffset(0, 0)
            st.co:SetPoint("TOPRIGHT", st, "TOPRIGHT", -8, -6)
            st.coTx = MakeFS(st.co, 14, C_TEXT, "CENTER")
            st.co:SetFontString(st.coTx)
            st.coTx:SetText(L["地图"])
            local tw = st.coTx:GetStringWidth() or 28
            st.co:SetWidth(math.floor(8 + 10.4 + 6 + tw + 8 + 0.5))
            if ns.hui and ns.hui.SkinButton then ns.hui.SkinButton(st.co) end
            st.co.__huiKeepTextColor = true
            st.coRx = st.co:CreateTexture(nil, "OVERLAY")
            st.coRx:SetSize(10.4, 15)
            st.coRx:SetPoint("LEFT", st.co, "LEFT", 8, 0)
            st.coRx:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\EntryPin")
            st.coRx:SetTexCoord(14 / 64, 50 / 64, 9 / 64, 61 / 64)
            st.coTx:ClearAllPoints()
            st.coTx:SetPoint("LEFT", st.coRx, "RIGHT", 6, 0)
            st.co:SetScript("OnClick", function(self)
                local p = self:GetParent()
                if p.__go then
                    local g = p.__go
                    RtGo(g[1], g[2], g[3])
                end
            end)
            st.co:SetScript("OnEnter", function(self)
                local g = self:GetParent().__go
                RtTip(self, true, g and g[2], g and g[3])
            end)
            st.co:SetScript("OnLeave", function(self)
                RtTip(self, false)
            end)
            st.d = MakeFS(st, 14, C_TEXT, "LEFT")
            st.d:SetPoint("TOPLEFT", st, "TOPLEFT", 36, -36)
            st.d:SetWordWrap(true)
            st.d:SetJustifyV("TOP")
            st:Hide()
            EG.rtSteps[i] = st
        end

        local eh = CreateFrame("Frame", nil, root)
        eh:SetPoint("TOPLEFT", bd, "TOPLEFT", 0, 0)
        eh:SetPoint("BOTTOMRIGHT", bd, "BOTTOMRIGHT", 0, 0)
        ns.hui.SkinPopup(eh, 6, nil, ns.hui.layer.L1)
        eh:Hide()
        EG.rtEmptyHost = eh
        local eic = eh:CreateTexture(nil, "ARTWORK")
        eic:SetSize(28, 28)
        eic:SetPoint("CENTER", eh, "CENTER", 0, 26)
        eic:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\NotePin")
        eic:SetAlpha(0.35)
        local etx = MakeFS(eh, 14, C_DIM, "CENTER")
        etx:SetPoint("TOP", eic, "BOTTOM", 0, -8)
        etx:SetText(L["跑图 · 联盟版待补充"])
        eh:Hide()
    end

    EG.page = page
    EG.LayoutBody()

    if EG.cardLvl then
        for _, fr in ipairs({ page:GetChildren() }) do
            if fr ~= EG.listCard and fr ~= EG.navCard then
                fr:SetFrameLevel(math.max(fr:GetFrameLevel(), EG.cardLvl + 2))
            end
        end
    end

    EG.built = true
    EG.building = false
    ns.EvtPool = ns.EvtPool or {}
    if not ns.EvtPool.exploreBag then
        local ev = CreateFrame("Frame")
        ns.EvtPool.exploreBag = ev
        if ev.RegisterEvent then
            pcall(ev.RegisterEvent, ev, "BAG_UPDATE_DELAYED")
            pcall(ev.RegisterEvent, ev, "QUEST_LOG_UPDATE")
            ev:SetScript("OnEvent", function()
                C_Timer.After(0, function()
                    if not EG.built or not ns.PageVisible(EG.page) then return end
                    EG.ScanAuto()
                    EG.RequestRender()
                end)
            end)
        end
    end
    EG.Render()
    end))
end
