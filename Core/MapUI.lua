local _, ns = ...
if type(ns) ~= "table" then return end

local Host = ns.ProfHost
if type(Host) ~= "table" then return end

local L = ns.L
local DG = Host.DG
local U = Host.U
local function MakeFS(parent, size, color, justify)
    if Host.MakeFS then
        local ok, fs = pcall(Host.MakeFS, parent, size, color, justify)
        if ok and fs then return fs end
    end
    local fs = parent:CreateFontString(nil, "OVERLAY")
    local path = ns.FONT or STANDARD_TEXT_FONT or "Fonts\\FRIZQT__.TTF"
    local flags = "OUTLINE"
    if ns.hui and ns.hui.FontFlags then
        local ok, f = pcall(ns.hui.FontFlags, "OUTLINE")
        if ok and type(f) == "string" then flags = f end
    end
    fs:SetFont(path, size or 12, flags)
    if color then fs:SetTextColor(color[1], color[2], color[3], color[4] or 1) end
    if justify then fs:SetJustifyH(justify) end
    return fs
end
local Unpack = Host.Unpack
local C_GREY = Host.C_GREY
local C_GOLD = Host.C_GOLD
local C_TEXT = Host.C_TEXT

local M = {}
ns.MapModule = M

M.COLS, M.ROWS = 4, 3
M.TILE = 256
M.ART_W, M.ART_H = 1002, 668
M.OVL_W, M.OVL_H = 1024, 768
M.N = M.COLS * M.ROWS

M.FRAME_W = Host.CONTENT_W - Host.PAGE_INSET * 2
M.FRAME_H = Host.CONTENT_H - DG.GUTTER - Host.PAGE_INSET - DG.GUIDE_TOP_Y

M.HDR_CARD_H = 50
M.HDR_GAP = 8
M.SIDE_GAP = 8
M.MAP_H = M.FRAME_H - M.HDR_CARD_H - M.HDR_GAP
M.MAP_W = math.floor(M.MAP_H * M.ART_W / M.ART_H)
M.SIDE_W = M.FRAME_W - M.MAP_W - M.SIDE_GAP
M.SIDE_PAD = 8

M.MAX_LAYERS = 10
M.LAYER_W, M.LAYER_GAP = 66, 8
M.BAR_H = 24
M.FLOOR_INSET = 6
M.PIN_BTN_W, M.PIN_BTN_MIN, M.PIN_BTN_GAP = 72, 64, 8

M.BOSS_MODEL_W = 260
M.BOSS_MODEL_UP = 66

M.MAX_PINS = 48
M.LOGO_TEX = "Interface\\AddOns\\DungeonsForever\\Media\\DungeonsForever.blp"
M.LOGO_SIZE = 20
M.PIN_BOSS_TEX = "Interface\\AddOns\\DungeonsForever\\Media\\BossSkull"
M.PIN_QUEST_READY_TEX = "Interface\\AddOns\\DungeonsForever\\Media\\QuestPinReady"
M.PIN_QUEST_LOCKED_TEX = "Interface\\AddOns\\DungeonsForever\\Media\\QuestPinLocked"
M.PIN_QUEST_PRE_TEX = "Interface\\AddOns\\DungeonsForever\\Media\\QuestPinPre"
M.PIN_DOOR_TEX = "Interface\\AddOns\\DungeonsForever\\Media\\MapDoor"
M.PIN_NOTE_TEX = "Interface\\AddOns\\DungeonsForever\\Media\\NotePin"
M.PIN_STAIR_UP_TEX = "Interface\\AddOns\\DungeonsForever\\Media\\StairsUp"
M.PIN_STAIR_DN_TEX = "Interface\\AddOns\\DungeonsForever\\Media\\StairsDown"
M.PIN_GLOW_TEX = "Interface\\AddOns\\DungeonsForever\\Media\\PinGlow"
M.PIN_GLOW_K = 2.1
M.PIN_GLOW_GAIN = 0.85
M.PIN_RING_TEX = "Interface\\AddOns\\DungeonsForever\\Media\\PinRing"
M.PIN_RING_K = 2.5
M.PIN_RING_RGB = { 1.00, 0.78, 0.22 }
M.PIN_RING_SECS = 6
M.PIN_LINK_TOL = 2.5
M.PIN_SIZE = 48
M.PIN_MIN = 27
M.NOTE_SIZE = 21
M.STAIR_SIZE = 26
M.ROUTE_STEP, M.ROUTE_DOT, M.ROUTE_DOT_EDGE = 1.6, 4.2, 8.0
M.ROUTE_THIN_DOT, M.ROUTE_THIN_EDGE = 2.6, 5.0
M.ROUTE_DASH_ON, M.ROUTE_DASH_OFF = 13, 9
M.ROUTE_DOT_TEX = "Interface\\AddOns\\DungeonsForever\\Media\\textures\\route_dot"
M.MAX_ROUTE_DOTS = 2400
M.ROUTE_PALETTES = {
    { id = "rainbow", stops = {
        { 0.00, 0.961, 0.278, 0.227 },
        { 0.20, 0.961, 0.541, 0.180 },
        { 0.42, 0.961, 0.784, 0.259 },
        { 0.62, 0.494, 0.839, 0.294 },
        { 0.82, 0.247, 0.788, 0.757 },
        { 1.00, 0.290, 0.616, 0.961 },
    } },
    { id = "sunset", stops = {
        { 0.00, 0.961, 0.263, 0.608 },
        { 0.20, 0.961, 0.376, 0.290 },
        { 0.42, 0.961, 0.604, 0.180 },
        { 0.62, 0.961, 0.784, 0.259 },
        { 0.82, 0.961, 0.878, 0.353 },
        { 1.00, 1.000, 0.941, 0.627 },
    } },
    { id = "lime", stops = {
        { 0.00, 0.208, 0.910, 0.847 },
        { 0.20, 0.294, 0.878, 0.478 },
        { 0.42, 0.659, 0.910, 0.294 },
        { 0.62, 0.941, 0.894, 0.235 },
        { 0.82, 0.961, 0.725, 0.235 },
        { 1.00, 0.961, 0.522, 0.212 },
    } },
    { id = "nebula", stops = {
        { 0.00, 0.247, 0.627, 0.961 },
        { 0.20, 0.353, 0.424, 0.941 },
        { 0.42, 0.541, 0.333, 0.941 },
        { 0.62, 0.761, 0.302, 0.941 },
        { 0.82, 0.941, 0.310, 0.753 },
        { 1.00, 0.961, 0.478, 0.784 },
    } },
    { id = "aurora", stops = {
        { 0.00, 0.208, 0.878, 0.690 },
        { 0.20, 0.247, 0.714, 0.941 },
        { 0.42, 0.416, 0.435, 0.961 },
        { 0.62, 0.655, 0.361, 0.941 },
        { 0.82, 0.882, 0.361, 0.839 },
        { 1.00, 0.961, 0.545, 0.753 },
    } },
}
M.routePalette = "sunset"
local __dbDungeon = DungeonsForeverDB and DungeonsForeverDB.dungeon
M.routeThin = not (__dbDungeon and __dbDungeon.mapRouteThin == false)
M.ROUTE_PAL_NAMES = {
    rainbow = L["彩虹渐变"],
    sunset = L["落日渐变"],
    lime = L["青柠渐变"],
    nebula = L["蓝紫渐变"],
    aurora = L["极光渐变"],
}

function M.CycleRoutePalette()
    local list = M.ROUTE_PALETTES
    for i, p in ipairs(list) do
        if p.id == M.routePalette then
            M.routePalette = list[i % #list + 1].id
            return M.routePalette
        end
    end
    M.routePalette = list[1].id
    return M.routePalette
end

local BP_MASK_TEX = "Interface\\CharacterFrame\\TempPortraitAlphaMask"
local BP_BASE = nil

local function bpBaseColor()
    if BP_BASE then return BP_BASE end
    local l = ns.hui and ns.hui.layer and ns.hui.layer.L1
    BP_BASE = (type(l) == "table" and l[1]) and l or { 0.10, 0.12, 0.15, 1 }
    return BP_BASE
end

local function bpMask(tex)
    if tex.__bpMask ~= nil then return end
    tex.__bpMask = false
    local parent = tex.GetParent and tex:GetParent()
    if not parent or not parent.CreateMaskTexture then return end
    local ok, m = pcall(parent.CreateMaskTexture, parent)
    if not ok or not m then return end
    pcall(m.SetTexture, m, BP_MASK_TEX, "CLAMPTOBLACKADDITIVE", "CLAMPTOBLACKADDITIVE")
    pcall(m.SetAllPoints, m, tex)
    if pcall(tex.AddMaskTexture, tex, m) then tex.__bpMask = m end
end

local function bpFace(tex, disp)
    if not (disp and SetPortraitTextureFromCreatureDisplayID) then return false end
    if tex.__bpMask then pcall(tex.SetTexCoord, tex, 0, 1, 0, 1) end
    return (pcall(SetPortraitTextureFromCreatureDisplayID, tex, disp))
end

local function bpDisp(id, en)
    local t = ns.BossModelDisplay and ns.BossModelDisplay[id]
    return (t and en and t[en]) or nil
end

local function bpBuild(host)
    host.avRing = host:CreateTexture(nil, "OVERLAY", nil, 1)
    host.avBase = host:CreateTexture(nil, "OVERLAY", nil, 2)
    host.avFace = host:CreateTexture(nil, "OVERLAY", nil, 3)
    bpMask(host.avRing)
    bpMask(host.avBase)
    bpMask(host.avFace)
end

local function bpPaint(host, disp, cr, cg, cb, size)
    if not host.avFace then bpBuild(host) end
    local b = size >= 36 and 2 or 1
    local bc = bpBaseColor()
    host:SetSize(size, size)
    host.avRing:SetColorTexture(cr, cg, cb, 1)
    host.avRing:ClearAllPoints()
    host.avRing:SetAllPoints(host)
    host.avBase:SetColorTexture(bc[1], bc[2], bc[3], bc[4] or 1)
    host.avBase:ClearAllPoints()
    host.avBase:SetPoint("TOPLEFT", host, "TOPLEFT", b, -b)
    host.avBase:SetPoint("BOTTOMRIGHT", host, "BOTTOMRIGHT", -b, b)
    host.avFace:ClearAllPoints()
    host.avFace:SetPoint("TOPLEFT", host, "TOPLEFT", b + 1, -(b + 1))
    host.avFace:SetPoint("BOTTOMRIGHT", host, "BOTTOMRIGHT", -(b + 1), b + 1)
    host.avFace:SetVertexColor(1, 1, 1)
    if not bpFace(host.avFace, disp) then
        host.avFace:SetTexture(M.PIN_BOSS_TEX)
        host.avFace:SetVertexColor(cr, cg, cb)
        pcall(host.avFace.SetTexCoord, host.avFace, 0.08, 0.92, 0.08, 0.92)
    end
end

M.MAX_LIST = 30

M.BOSS_PALETTE = {
    { 0.94, 0.30, 0.28 },
    { 1.00, 0.58, 0.19 },
    { 1.00, 0.82, 0.00 },
    { 0.42, 0.88, 0.34 },
    { 0.30, 0.84, 0.84 },
    { 0.36, 0.55, 1.00 },
    { 0.70, 0.45, 0.95 },
    { 0.95, 0.42, 0.78 },
    { 0.91, 0.89, 0.82 },
    { 0.56, 0.65, 0.75 },
    { 0.79, 0.55, 0.35 },
    { 0.78, 0.90, 0.30 },
}
M.MAX_LOOT = 30
M.MAX_SKILL = 8
M.LIST_H = 38
M.LIST_GAP = 8

M.BLK_PAD = 8
M.BLK_HDR = 26
M.BLK_TITLE_TOP = 5
M.BLK_GAP = 8
M.ROW_GAP = 4

M.BLK_MIN_H = M.BLK_HDR
M.BLK_TITLE_X = 24
M.BLK_ARROW = 10

M.CARD_ICON = 32
M.CARD_H = 40
M.CARD_FS_NAME = 13
M.CARD_FS_META = 11

M.BLK_RADIUS = 6
M.ROW_RADIUS = 4
M.BLK_BG = 0.03

local WM = "Interface\\WorldMap\\"

local function FlattenPieces(...)
    local out = {}
    for i = 1, select("#", ...) do
        local v = select(i, ...)
        if type(v) == "table" then
            for j = 1, #v do out[#out + 1] = v[j] end
        end
    end
    return out
end

local function PiecesSetShown(t, on)
    for i = 1, #(t or {}) do t[i]:SetShown(on) end
end

function M.CardClosed()
    local ui = ns.DB().ui
    local c = ui.mapCards
    if type(c) ~= "table" then c = {} ui.mapCards = c end
    return c
end

local DM = { "DireMaul",
    { "DireMaul1_", "DireMaul2_", "DireMaul3_", "DireMaul4_", "DireMaul5_", "DireMaul6_", "DireMaul" } }
local ST = { "Stratholme", { "Stratholme1_", "Stratholme2_" } }

local SM_DIR = "ScarletMonasteryOld"
local MD = "microdungeon\\"
local SM_ENTRY = MD .. "tirisfal\\scarletmonasteryentrance\\scarletmonasteryentrance13_"
local function SMW(pre) return { SM_DIR, { pre, SM_ENTRY } } end

local SMFIX_DIR = "Interface\\AddOns\\DungeonsForever\\Media\\Maps\\SMEntry13\\"
local SM_FIX = { [3] = SMFIX_DIR .. "Block3", [4] = SMFIX_DIR .. "Block4", [8] = SMFIX_DIR .. "Block8" }
local ATALFIX_DIR = "Interface\\AddOns\\DungeonsForever\\Media\\Maps\\AtalHakkar\\"
local ATAL_FIX = { [2] = ATALFIX_DIR .. "Block2", [3] = ATALFIX_DIR .. "Block3",
                   [6] = ATALFIX_DIR .. "Block6", [7] = ATALFIX_DIR .. "Block7" }
local function AllBlocks(dir)
    local out = {}
    for i = 1, 12 do out[i] = dir .. "Block" .. i end
    return out
end
local ATAL2_FIX = AllBlocks("Interface\\AddOns\\DungeonsForever\\Media\\Maps\\AtalHakkar2\\")
local ATAL3_FIX = AllBlocks("Interface\\AddOns\\DungeonsForever\\Media\\Maps\\AtalHakkar3\\")
local WCFIX_DIR = "Interface\\AddOns\\DungeonsForever\\Media\\Maps\\WCFix\\"
local WC_FIX = { [3] = WCFIX_DIR .. "Block3", [4] = WCFIX_DIR .. "Block4",
                 [7] = WCFIX_DIR .. "Block7", [8] = WCFIX_DIR .. "Block8",
                 [11] = WCFIX_DIR .. "Block11", [12] = WCFIX_DIR .. "Block12" }
local TILE_FIX = {
    sm_graveyard = { [2] = SM_FIX },
    sm_library   = { [2] = SM_FIX },
    sm_armory    = { [2] = SM_FIX },
    sm_cathedral = { [2] = SM_FIX },
    sunken_temple = { [1] = ATAL_FIX, [2] = ATAL2_FIX, [3] = ATAL3_FIX },
    wailing_caverns = { [1] = WC_FIX },
}
M.TILE_FIX = TILE_FIX

M.OUTSIDE_LAYER = { maraudon = 3 }

M.ZONE_AREA = {
    { id = "blackrock_mountain", zone = { "燃烧平原", "Burning Steppes", "灼热峡谷", "Searing Gorge" },
      sub = { "黑石山", "熔岩之桥", "禁闭室", "黑铁酒吧", "黑石塔", "暗炉城", "黑石深渊",
              "铸铁之墓", "熔火之心", "碾石场", "石匠区",
              "Blackrock Mountain", "The Molten Span", "Detention Block", "The Grim Guzzler",
              "Shadowforge City", "Blackrock Spire", "Forgewright's Tomb",
              "The Grinding Quarry", "The Mason's Quarter" },
      mark = { "黑石", "Blackrock" } },
}

M.ZONE_MENU = {
    [1428] = { "blackrock_mountain", "blackrock_depths", "lower_blackrock_spire", "upper_blackrock_spire" },
    [1427] = { "blackrock_mountain", "upper_blackrock_spire", "lower_blackrock_spire" },
}

local BRM = MD .. "burningsteppes\\blackrockmountain\\blackrockmountain"
local BRM14, BRM16 = BRM .. "14_", BRM .. "16_"

local ART = {
    ragefire_chasm        = { "Ragefire", { "Ragefire1_" } },
    wailing_caverns       = { "WailingCaverns",
        { "WailingCaverns1_", MD .. "barrens\\wailingcavernsbarrens\\wailingcavernsbarrens20_" } },
    the_deadmines         = { "TheDeadmines",
        { "TheDeadmines1_", "TheDeadmines2_", MD .. "westfall\\deadmineswestfall\\deadmineswestfall17_" } },
    shadowfang_keep       = { "ShadowfangKeep",
        { "ShadowfangKeep1_", "ShadowfangKeep2_", "ShadowfangKeep3_", "ShadowfangKeep4_",
          "ShadowfangKeep5_", "ShadowfangKeep6_", "ShadowfangKeep7_" } },
    blackfathom_deeps     = { "BlackfathomDeeps",
        { "BlackfathomDeeps1_", "BlackfathomDeeps2_", "BlackfathomDeeps3_" } },
    the_stockade          = { "TheStockade", { "TheStockade1_" } },
    gnomeregan            = { "Gnomeregan",
        { "Gnomeregan1_", "Gnomeregan2_", "Gnomeregan3_", "Gnomeregan4_", "Gnomeregan10_" } },
    razorfen_kraul        = { "RazorfenKraul", { "RazorfenKraul1_" } },
    razorfen_downs        = { "RazorfenDowns", { "RazorfenDowns1_" } },
    sm_graveyard          = SMW("ScarletMonastery1_"),
    sm_library            = SMW("ScarletMonastery2_"),
    sm_armory             = SMW("ScarletMonastery3_"),
    sm_cathedral          = SMW("ScarletMonastery4_"),
    uldaman               = { "Uldaman", { "Uldaman1_", "Uldaman2_", "Uldaman18_" } },
    zul_farrak            = { "ZulFarrak", { "ZulFarrak" } },
    maraudon              = { "Maraudon", { "Maraudon1_", "Maraudon2_",
        "microdungeon\\desolace\\maraudonoutside\\maraudonoutside21_",
        "microdungeon\\desolace\\maraudonoutside\\maraudonoutside22_" } },
    sunken_temple         = { "TheTempleofAtalHakkar",
        { "TheTempleofAtalHakkar1_", "TheTempleofAtalHakkar2_", "TheTempleofAtalhakkar3_" } },
    blackrock_mountain    = { "burningsteppes\\blackrockmountain", { BRM14, BRM16 } },
    blackrock_depths      = { "BlackrockDepths",
        { "BlackrockDepths1_", "BlackrockDepths2_", BRM14, BRM16 } },
    dire_maul_east        = DM,
    dire_maul_north       = DM,
    dire_maul_west        = DM,
    lower_blackrock_spire = { "BlackrockSpire",
        { "BlackrockSpire1_", "BlackrockSpire2_", "BlackrockSpire3_", "BlackrockSpire4_",
          "BlackrockSpire5_", "BlackrockSpire6_", BRM14 } },
    upper_blackrock_spire = { "UpperBlackrockSpire",
        { "UpperBlackrockSpire1_", "UpperBlackrockSpire2_", "BlackrockSpire\\BlackrockSpire7_",
          BRM14 } },
    scholomance           = { "ScholomanceOld",
        { "ScholomanceOld1_", "ScholomanceOld2_", "ScholomanceOld3_", "ScholomanceOld4_" } },
    stratholme_main       = ST,
    stratholme_service    = ST,
    city_of_dalaran       = { "Dalaran", { "Dalaran1_", "Dalaran2_" } },
    onyxias_lair          = { "OnyxiasLair", { "OnyxiasLair1_" } },
}
M.ART = ART

local CUSTOM = {
    hall_of_thanes      = "Interface\\AddOns\\DungeonsForever\\Media\\Maps\\HallOfThanes",
    ruins_of_lordaeron  = "Interface\\AddOns\\DungeonsForever\\Media\\Maps\\RuinsOfLordaeron",
    excavation_wetlands = "Interface\\AddOns\\DungeonsForever\\Media\\Maps\\ExcavationSite",
}
M.CUSTOM = CUSTOM

local CUSTOM_FLOOR = {
    city_of_dalaran = { [1] = "Interface\\AddOns\\DungeonsForever\\Media\\Maps\\Dalaran" },
}
M.CUSTOM_FLOOR = CUSTOM_FLOOR

local FLOOR_NAMES = {
    the_deadmines = {
        { "Deadmines", "死亡矿井", "死亡礦坑" },
        { "Ironclad Cove", "铁甲湾", "鐵甲灣" },
        { "Deadmines Outside", "死亡矿井副本外", "死亡礦坑副本外" },
    },
    wailing_caverns = {
        { "Wailing Caverns", "哀嚎洞穴", "哀嚎洞穴" },
        [2] = { "Wailing Caverns Outside", "哀嚎洞穴副本外", "哀嚎洞穴副本外" },
    },
    sm_graveyard = {
        { "Graveyard", "墓地", "墓地" },
        [2] = { "Monastery Entrance", "修道院入口", "修道院入口" },
    },
    sm_library = {
        { "Library", "图书馆", "圖書館" },
        [2] = { "Monastery Entrance", "修道院入口", "修道院入口" },
    },
    sm_armory = {
        { "Armory", "军械库", "軍械庫" },
        [2] = { "Monastery Entrance", "修道院入口", "修道院入口" },
    },
    sm_cathedral = {
        { "Cathedral", "大教堂", "大教堂" },
        [2] = { "Monastery Entrance", "修道院入口", "修道院入口" },
    },
    shadowfang_keep = {
        { "The Courtyard", "庭院", "庭院" },
        { "Dining Hall", "饭厅", "餐廳" },
        { "The Vacant Den", "空巢", "空穴之地" },
        { "Lower Observatory", "下层瞭望台", "下層觀測所" },
        { "Upper Observatory", "上层瞭望台", "上層觀測所" },
        { "Lord Godfrey's Chamber", "高弗雷勋爵的大厅", "高佛雷領主的房間" },
        { "The Wall Walk", "城墙走道", "巨牆步道" },
    },
    blackfathom_deeps = {
        { "The Pool of Ask'Ar", "阿斯卡之池", "阿斯卡之池" },
        { "Moonshrine Sanctum", "月神圣地密室", "月光神殿密室" },
        { "The Forgotten Pool", "遗忘之池", "遗忘之池" },
    },
    gnomeregan = {
        { "The Hall of Gears", "齿轮大厅", "齒輪大廳" },
        { "The Dormitory", "宿舍", "宿舍" },
        { "Launch Bay", "发射台", "發射台" },
        { "Tinkers' Court", "工匠议会", "技工議會" },
    },
    uldaman = {
        { "Hall of the Keepers", "守护者大厅", "守衛者大廳" },
        { "Khaz'Goroth's Seat", "卡兹格罗斯之座", "卡茲格羅斯的王座" },
        { "Outside Uldaman", "奥达曼副本外地图", "奧達曼副本外地圖" },
    },
    maraudon = {
        { "Caverns of Maraudon", "玛拉顿的洞穴", "瑪拉頓的洞穴" },
        { "Zaetar's Grave", "扎尔塔之墓", "札爾塔之墓" },
        { "Orange Side", "橙门", "橙門" },
        { "Purple Side", "紫门", "紫門" },
    },
    blackrock_mountain = {
        { "Blackrock Mountain", "黑石山", "黑石山" },
        { "Blackrock Depths Entrance", "黑石深渊入口", "黑石深淵入口" },
    },
    blackrock_depths = {
        { "Detention Block", "禁闭室", "拘留所" },
        { "Shadowforge City", "暗炉城", "影爐城" },
        { "Blackrock Mountain", "黑石山", "黑石山" },
        { "Blackrock Depths Entrance", "黑石深渊入口", "黑石深淵入口" },
    },
    dire_maul = {
        { "Gordok Commons", "戈多克议会", "戈多克平民區" },
        { "Capital Gardens", "中心花园", "中心花園" },
        { "Court of the Highborne", "上层精灵庭院", "精靈貴族庭院" },
        { "Prison of Immol'Thar", "伊莫塔尔的牢笼", "伊莫塔爾的牢籠" },
        { "The Hidden Path", "密径", "密徑" },
        { "Warpwood Quarter", "纽木广场", "紐木廣場" },
    },
    lower_blackrock_spire = {
        { "Tazz'Alor", "塔萨洛尔", "塔薩洛爾" },
        { "Skitterweb Tunnels", "蛛网隧道", "蛛網隧道" },
        { "Hordemar City", "霍德玛尔城", "霍德瑪爾城" },
        { "Hall of Blackhand", "黑手大厅", "黑手大廳" },
        { "Halycon's Lair", "哈雷肯之巢", "哈雷肯之巢" },
        { "Chamber of Battle", "战斗之厅", "戰鬥之廳" },
        [14] = { "Blackrock Mountain", "黑石山", "黑石山" },
    },
    upper_blackrock_spire = {
        [4] = { "Blackrock Mountain", "黑石山", "黑石山" },
    },
    scholomance = {
        { "The Reliquary", "遗骨之穴", "聖骨室" },
        { "Chamber of Summoning", "召唤大厅", "召喚之廳" },
        { "The Upper Study", "书房上层", "書房上層" },
        { "Headmaster's Study", "院长的书房", "院長的書房" },
    },
    stratholme = {
        { "Crusader's Square", "十字军广场", "十字軍廣場" },
        { "Slaughter Square", "屠杀广场", "屠殺廣場" },
    },
}

local FLOOR_KEY = {
    dire_maul_east    = "dire_maul",
    dire_maul_north   = "dire_maul",
    dire_maul_west    = "dire_maul",
    stratholme_main   = "stratholme",
    stratholme_service = "stratholme",
}

local function StripOrd(s)
    if type(s) ~= "string" or #s < 4 then return s or "" end
    if s:byte(1) == 0xE2 and s:byte(2) == 0x9D and s:byte(3) >= 0xB6 and s:byte(3) <= 0xBF then
        return s:sub(4)
    end
    return s
end

local function FloorName(id, idx)
    if not id then return nil end
    local ov = ns.FloorName
    local t0 = ov and ov[id] and ov[id][idx]
    if t0 then return t0 end
    local arr = FLOOR_NAMES[FLOOR_KEY[id] or id]
    local t = arr and arr[idx]
    if not t then return nil end
    local gl = (type(GetLocale) == "function") and GetLocale() or "zhCN"
    if gl == "enUS" then return t[1] end
    if gl == "zhTW" then return t[3] end
    return t[2]
end

function M.CustomFor(id)
    local path = id and CUSTOM[id]
    if not path then return nil end
    return path, 1
end

function M.CustomFloorFor(id, idx)
    local row = id and CUSTOM_FLOOR[id]
    if type(row) ~= "table" or type(idx) ~= "number" then return nil end
    local path = row[idx]
    if not path then return nil end
    return path, 1
end

local SHOW_FLOORS = {
    dire_maul_north = { 1 },
    dire_maul_east  = { 5, 6 },
    dire_maul_west  = { 2, 3, 4 },
    stratholme_main = { 1 },
    stratholme_service = { 2 },
    lower_blackrock_spire = { 7, 1, 2, 3, 4, 5, 6 },
}

local FLOOR_NO = {
    blackrock_mountain = { [1] = 1, [2] = 2 },
    blackrock_depths = { [1] = 1, [2] = 2, [3] = 3, [4] = 4 },
    lower_blackrock_spire = { [1] = 9, [2] = 1, [3] = 2, [4] = 3, [5] = 4, [6] = 5, [7] = 6 },
    maraudon = { [1] = 1, [2] = 2, [3] = 3, [4] = 4 },
    sunken_temple = { [1] = 1, [2] = 2, [3] = 3 },
}

local LAYER_PICK = {}

function M.LayersFor(id)
    local row = id and ART[id]
    if not row then return nil end
    local pick = id and SHOW_FLOORS[id]
    if type(pick) ~= "table" then return row[2] end
    local c = LAYER_PICK[id]
    if c then return c end
    local out, n = {}, 0
    for i = 1, #pick do
        local lay = row[2][pick[i]]
        if lay then
            n = n + 1
            out[n] = lay
        end
    end
    if n == 0 then return row[2] end
    LAYER_PICK[id] = out
    return out
end

local function LayPath(id, lay)
    if type(lay) ~= "string" then return nil end
    if lay:find("\\", 1, true) then return WM .. lay end
    return WM .. ART[id][1] .. "\\" .. lay
end

function M.PathFor(id)
    local layers = M.LayersFor(id)
    if not (layers and layers[1]) then return nil end
    return LayPath(id, layers[1])
end

function M.PathAt(id, i)
    local layers = M.LayersFor(id)
    if not (layers and layers[i]) then return nil end
    return LayPath(id, layers[i])
end

function M.PosFor(id, en, floor)
    local all = id and ns.BossPos and ns.BossPos[id]
    local pts = all and en and all[en]
    if type(pts) ~= "table" or #pts == 0 then return nil end
    if floor == nil then return pts end
    local out
    for i = 1, #pts do
        local p = pts[i]
        if (p[3] or 1) == floor then
            out = out or {}
            out[#out + 1] = p
        end
    end
    return out
end

local IN_ZH_RARE = "稀有"
local RARE_INK = { 0.80, 0.66, 1.00 }

function M.BossesFor(id)
    local loot = (ns.DungeonLoot or {})[id]
    if type(loot) ~= "table" then return nil end
    local out
    for i = 1, #loot do
        local s = loot[i]
        if type(s) == "table"
           and ((s[4] and s[4] ~= "") or M.PosFor(id, s[1]) or M.GuideFor(id, s[1])) then
            out = out or {}
            local meta = s[3]
            out[#out + 1] = { en = s[1], zh = s[2] or s[1], npc = s[4] or "", items = s[5] or {},
                rare = type(meta) == "string" and meta:find(IN_ZH_RARE, 1, true) ~= nil or false }
        end
    end
    return out
end

local BOSS_ZH_ALL

local function BossZhAll()
    if BOSS_ZH_ALL then return BOSS_ZH_ALL end
    BOSS_ZH_ALL = {}
    local loot = ns.DungeonLoot
    if type(loot) == "table" then
        for _, list in pairs(loot) do
            if type(list) == "table" then
                for i = 1, #list do
                    local s = list[i]
                    if type(s) == "table" and type(s[1]) == "string"
                       and type(s[2]) == "string" then
                        BOSS_ZH_ALL[s[1]] = s[2]
                    end
                end
            end
        end
    end
    return BOSS_ZH_ALL
end

function M.PinsFor(id, floor)
    local bosses = M.BossesFor(id)
    local out
    local have
    if bosses then
        have = {}
        for i = 1, #bosses do
            local b = bosses[i]
            have[b.en] = true
            local pts = M.PosFor(id, b.en, floor)
            if pts then
                for k = 1, #pts do
                    out = out or {}
                    out[#out + 1] = {
                        en = b.en, zh = b.zh, npc = b.npc,
                        left = pts[k][1], top = pts[k][2],
                    }
                end
            end
        end
    end
    local all = id and ns.BossPos and ns.BossPos[id]
    if type(all) == "table" then
        local extra
        for en in pairs(all) do
            if not (have and have[en]) then
                extra = extra or {}
                extra[#extra + 1] = en
            end
        end
        if extra then
            table.sort(extra)
            local zhall = BossZhAll()
            for i = 1, #extra do
                local pts = M.PosFor(id, extra[i], floor)
                if pts then
                    for k = 1, #pts do
                        out = out or {}
                        out[#out + 1] = {
                            en = extra[i], zh = zhall[extra[i]] or extra[i],
                            npc = "", left = pts[k][1], top = pts[k][2],
                        }
                    end
                end
            end
        end
    end
    return out
end

function M.QuestPinsOn()
    local s = DungeonsForeverDB and DungeonsForeverDB.dungeon
    if not s then return true end
    return s.mapQuestPins ~= false
end

function M.SideOK(sd)
    if not sd then return true end
    local ps = DG.PlayerSide and DG.PlayerSide() or nil
    return (not ps) or ps == sd
end

function M.DetailOf(id)
    local list = ns.DungeonData and ns.DungeonData.dungeons
    if type(list) == "table" then
        for i = 1, #list do
            if list[i].id == id then return list[i] end
        end
    end
    return nil
end

function M.DungeonPinName(id)
    local d = M.DetailOf(id)
    return (d and d.name) or id
end

function M.ExtraPinsFor(id, floor)
    local row = id and ns.MapPins and ns.MapPins[id]
    if type(row) ~= "table" then return nil end
    local qp = M.QuestPinsOn()
    local out
    for _, kind in ipairs({ "entrance", "prev", "next", "quest", "object", "rare", "icon", "dungeon" }) do
        if kind == "quest" and not qp then
        else
            local arr = row[kind]
            if type(arr) == "table" then
                for i = 1, #arr do
                    local p = arr[i]
                    if type(p) == "table" and p[1] and p[2] then
                        if kind == "dungeon" then
                            local pf = p[3] or 1
                            if (floor == nil or pf == floor) and type(p[4]) == "string" then
                                out = out or {}
                                out[#out + 1] = {
                                    kind = "dungeon", left = p[1], top = p[2], floor = pf,
                                    id = (p[4] ~= "") and p[4] or nil,
                                    text = (type(p[5]) == "string") and p[5] or "",
                                }
                            end
                        elseif kind == "icon" or kind == "prev" or kind == "next" then
                            local pf = p[3] or 1
                            local sd = (p[5] == "A" or p[5] == "H") and p[5] or nil
                            if (floor == nil or pf == floor) and M.SideOK(sd) then
                                out = out or {}
                                out[#out + 1] = {
                                    kind = kind, left = p[1], top = p[2], floor = pf,
                                    to = (type(p[6]) == "number") and p[6] or nil,
                                    tox = (type(p[7]) == "number") and p[7] or nil,
                                    toy = (type(p[8]) == "number") and p[8] or nil,
                                    text = (type(p[4]) == "string") and p[4] or "",
                                    side = sd,
                                }
                            end
                        else
                            local pf = p[(kind == "rare") and 5 or 4] or 1
                            if floor == nil or pf == floor then
                                local txt
                                if kind == "quest" and type(p[5]) == "string" then
                                    txt = p[5]
                                end
                                out = out or {}
                                out[#out + 1] = {
                                    kind = kind, left = p[1], top = p[2], id = p[3],
                                    name = (kind == "rare") and p[4] or nil,
                                    to = (type(p[6]) == "number") and p[6] or nil,
                                    tox = (type(p[7]) == "number") and p[7] or nil,
                                    toy = (type(p[8]) == "number") and p[8] or nil,
                                    text = txt,
                                }
                            end
                        end
                    end
                end
            end
        end
    end
    return out
end

function M.NotePinsFor(id, floor)
    if not M.RouteOn(id) then return nil end
    local row = id and ns.DungeonRouteNote and ns.DungeonRouteNote[id]
    if type(row) ~= "table" then return nil end
    local out
    for fl, arr in pairs(row) do
        if type(arr) == "table" and (floor == nil or fl == floor) then
            for i = 1, #arr do
                local p = arr[i]
                if type(p) == "table" and p[1] and p[2] then
                    out = out or {}
                    out[#out + 1] = {
                        kind = "note", left = p[1], top = p[2],
                        text = (type(p[3]) == "string") and p[3] or "",
                    }
                end
            end
        end
    end
    return out
end

function M.HasPins(id)
    if not id then return false end
    if not (M.LayersFor(id) or M.CustomFor(id)) then return false end
    local list = M.PinsFor(id, nil)
    local n = list and #list or 0
    local ex = M.ExtraPinsFor(id, nil)
    if ex then n = n + #ex end
    return (n > 0) and true or false
end

function M.HasKindPins(id, want)
    if not id then return false end
    if not (M.LayersFor(id) or M.CustomFor(id)) then return false end
    if want == "note" then
        local nts = M.NotePinsFor(id, nil)
        return (nts and #nts > 0) and true or false
    end
    if want == "quest" then
        local n = 0
        local ex = M.ExtraPinsFor(id, nil)
        if ex then
            for i = 1, #ex do
                local k = ex[i].kind
                if k == "quest" or k == "icon" then n = n + 1 end
            end
        end
        return (n > 0) and true or false
    end
    if want == "stairs" then
        local n = 0
        local ex = M.ExtraPinsFor(id, nil)
        if ex then
            for i = 1, #ex do
                local k = ex[i].kind
                if k == "prev" or k == "next" then n = n + 1 end
            end
        end
        return (n > 0) and true or false
    end
    local n = 0
    local list = M.PinsFor(id, nil)
    if list then n = n + #list end
    local ex = M.ExtraPinsFor(id, nil)
    if ex then
        for i = 1, #ex do
            if ex[i].kind == "rare" then n = n + 1 end
        end
    end
    return (n > 0) and true or false
end

function M.GuideFor(id, en)
    local g = (ns.DungeonGuide or {})[id]
    local bs = g and g.bosses
    if type(bs) ~= "table" then return nil end
    for i = 1, #bs do
        if bs[i] and bs[i].en == en then return bs[i].text end
    end
    return nil
end

function M.SkillsFor(id, en)
    local row = (ns.BossSkills or {})[id]
    local sk = row and en and row[en]
    if type(sk) ~= "table" or #sk == 0 then return nil end
    return sk
end

local SKILL_TIP_META = {
    "码距离$", "施法时间$", "^瞬发$", "^冷却时间", "法力值$", "^%d+%.?%d*%%基础法力值$",
    " yd range$", " sec cast$", " sec cooldown$", " of base mana$", "^Instant$",
    "^法术 ID$", "^图标 ID$", "^Spell ID$", "^Icon ID$",
}
function M.SpellTipDesc(sid)
    if type(sid) ~= "number" then return nil end
    if not (GameTooltip and GameTooltip.SetSpellByID) then return nil end
    local ok = pcall(GameTooltip.SetSpellByID, GameTooltip, sid)
    if not ok then return nil end
    local out
    for i = 2, 32 do
        local fs = _G["GameTooltipTextLeft" .. i]
        if not (fs and fs.GetText) then break end
        local t = fs:GetText()
        if type(t) == "string" and t ~= "" then
            local meta = false
            for _, p in ipairs(SKILL_TIP_META) do
                if t:find(p) then meta = true break end
            end
            if not meta then out = t break end
        end
    end
    GameTooltip:ClearLines()
    return out
end

M._spellCache = {}
function M.SpellRowFor(sid, fbName, fbDesc, fbIcon)
    if type(sid) ~= "number" then return fbName, fbIcon, fbDesc end
    local c = M._spellCache[sid]
    if c == nil then
        local nm, ic
        if GetSpellInfo then
            local ok, n1, _r, n3 = pcall(GetSpellInfo, sid)
            if ok then nm, ic = n1, n3 end
        end
        if not nm and C_Spell and C_Spell.GetSpellInfo then
            local ok, info = pcall(C_Spell.GetSpellInfo, sid)
            if ok and type(info) == "table" then
                nm, ic = info.name, info.iconID
            end
        end
        if not ic and C_Spell and C_Spell.GetSpellTexture then
            local ok, tid = pcall(C_Spell.GetSpellTexture, sid)
            if ok then ic = tid end
        end
        if not ic and GetSpellTexture then
            local ok, tid = pcall(GetSpellTexture, sid)
            if ok then ic = tid end
        end
        local d
        if C_Spell and C_Spell.GetSpellDescription then
            local ok, t = pcall(C_Spell.GetSpellDescription, sid)
            if ok and type(t) == "string" then d = t end
        end
        if not d and GetSpellDescription then
            local ok, t = pcall(GetSpellDescription, sid)
            if ok and type(t) == "string" then d = t end
        end
        if d then
            d = d:gsub("|c%x%x%x%x%x%x%x%x", ""):gsub("|r", "")
            d = d:gsub("^%s+", ""):gsub("%s+$", "")
            if d == "" then d = nil end
        end
        if not d then d = M.SpellTipDesc(sid) end
        c = {
            name = (type(nm) == "string" and nm ~= "" and nm) or nil,
            icon = ((type(ic) == "string" and ic ~= "" and ic)
                    or (type(ic) == "number" and ic > 0 and ic)) or nil,
            desc = d,
        }
        M._spellCache[sid] = (c.name or c.icon or c.desc) and c or false
    end
    if c == false then return fbName, fbIcon, fbDesc end
    return c.name or fbName, c.icon or fbIcon, c.desc or fbDesc
end

function M.ShowSpellTip(owner, sid)
    if not sid then return end
    GameTooltip:SetOwner(owner, "ANCHOR_RIGHT")
    GameTooltip:ClearLines()
    local native = false
    if GameTooltip.SetSpellByID then
        local ok = pcall(GameTooltip.SetSpellByID, GameTooltip, sid)
        if ok then
            GameTooltip:Show()
            local n = GameTooltip.NumLines and GameTooltip:NumLines() or 0
            native = (type(n) == "number" and n > 1)
        end
    end
    if not native and GameTooltip.SetHyperlink then
        local ok = pcall(GameTooltip.SetHyperlink, GameTooltip, "spell:" .. tostring(sid))
        if ok then
            GameTooltip:Show()
            local n = GameTooltip.NumLines and GameTooltip:NumLines() or 0
            native = (type(n) == "number" and n > 1)
        end
    end
    if native then
        GameTooltip:Show()
    else
        GameTooltip:Hide()
    end
end

function M.FitBox(aw, ah)
    if type(aw) ~= "number" or type(ah) ~= "number" or aw <= 0 or ah <= 0 then return 1, 1, 0, 0 end
    local s = math.min(aw / M.ART_W, ah / M.ART_H)
    local w = math.floor(M.ART_W * s)
    local h = math.floor(M.ART_H * s)
    if w < 1 then w = 1 end
    if h < 1 then h = 1 end
    return w, h, math.floor((aw - w) / 2), math.floor((ah - h) / 2)
end

function M.Box()
    return M.MAP_W, M.MAP_W, M.MAP_H, 0, M.HDR_CARD_H + M.HDR_GAP
end

function M.Layout(cw, ch)
    local out = {}
    if type(cw) ~= "number" or type(ch) ~= "number" or cw <= 0 or ch <= 0 then return out end
    local sx, sy = cw / M.ART_W, ch / M.ART_H
    for n = 1, M.N do
        local col = (n - 1) % M.COLS
        local row = math.floor((n - 1) / M.COLS)
        local x0, x1 = col * M.TILE, (col + 1) * M.TILE
        local y0, y1 = row * M.TILE, (row + 1) * M.TILE
        if x1 > M.ART_W then x1 = M.ART_W end
        if y1 > M.ART_H then y1 = M.ART_H end
        if x1 > x0 and y1 > y0 then
            out[#out + 1] = {
                n = n,
                x = x0 * sx, y = y0 * sy,
                w = (x1 - x0) * sx, h = (y1 - y0) * sy,
                u0 = (x0 - col * M.TILE) / M.TILE, u1 = (x1 - col * M.TILE) / M.TILE,
                v0 = (y0 - row * M.TILE) / M.TILE, v1 = (y1 - row * M.TILE) / M.TILE,
            }
        end
    end
    return out
end

local function BuildPins()
    local frame = M.frame
    if not frame or frame.__pinsReady then return end
    frame.__pinsReady = true
    local pins = frame.pins
    local pinBtns = {}
    local pinText = CreateFrame("Frame", nil, pins)
    pinText:SetAllPoints()
    pinText:SetFrameLevel(pins:GetFrameLevel() + 1)
    frame.pinText = pinText
    for i = 1, M.MAX_PINS do
        local bt = CreateFrame("Button", nil, pins)
        bt:SetSize(M.PIN_SIZE, M.PIN_SIZE)
        bt.__idx = i
        bt.nm = MakeFS(pinText, 12, C_GOLD, "CENTER")
        local nfp, _, nff = bt.nm:GetFont()
        bt.nm:SetFont(nfp, 12, "OUTLINE")
        bt.nm:SetShadowColor(0, 0, 0, 1)
        bt.nm:SetShadowOffset(1, -1)
        bt.dot = bt:CreateTexture(nil, "OVERLAY")
        bt.dot:SetAllPoints()
        bt.dot:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\BossSkull")
        bt.dot:SetVertexColor(1, 0.82, 0)
        if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(bt.dot) end
        bt.__glow = bt:CreateTexture(nil, "BACKGROUND", nil, -1)
        bt.__glow:SetTexture(M.PIN_GLOW_TEX)
        bt.__glow:SetBlendMode("ADD")
        bt.__glow:SetSize(M.PIN_SIZE * M.PIN_GLOW_K, M.PIN_SIZE * M.PIN_GLOW_K)
        bt.__glow:SetPoint("CENTER", bt, "CENTER", 0, 0)
        bt.__glow:Hide()
        bt.__ring = bt:CreateTexture(nil, "BACKGROUND", nil, -2)
        bt.__ring:SetTexture(M.PIN_RING_TEX)
        bt.__ring:SetBlendMode("ADD")
        bt.__ring:SetVertexColor(M.PIN_RING_RGB[1], M.PIN_RING_RGB[2], M.PIN_RING_RGB[3])
        bt.__ring:SetSize(M.PIN_SIZE * M.PIN_RING_K, M.PIN_SIZE * M.PIN_RING_K)
        bt.__ring:SetPoint("CENTER", bt, "CENTER", 0, 0)
        bt.__ring:Hide()
        bt.__av = CreateFrame("Frame", nil, bt)
        bt.__av:SetSize(M.PIN_MIN, M.PIN_MIN)
        bt.__av:SetPoint("CENTER", bt, "CENTER", 0, 0)
        bpBuild(bt.__av)
        bt.__av:Hide()
        bt.nm:SetPoint("TOP", bt.dot, "BOTTOM", 0, -2)
        bt:SetScript("OnClick", function(self) M.Select(self.__en) end)
        bt:Hide()
        pinBtns[i] = bt
    end
    frame.pinBtns = pinBtns
end

local function BuildListRows()
    local frame = M.SideHost or M.frame
    if not frame or frame.__listReady then return end
    frame.__listReady = true
    local listChild, innerW = frame.listChild, frame.innerW
    local listRows = {}
    for i = 1, M.MAX_LIST do
        local r = CreateFrame("Button", nil, listChild)
        r:SetSize(innerW, M.LIST_H)
        r.__av = CreateFrame("Frame", nil, r)
        r.__av:SetSize(32, 32)
        r.__av:SetPoint("LEFT", r, "LEFT", 6, 0)
        bpBuild(r.__av)
        r.fs = MakeFS(r, 14, C_TEXT, "LEFT")
        r.fs:SetPoint("LEFT", r.__av, "RIGHT", 6, 0)
        r.fs:SetPoint("RIGHT", r, "RIGHT", -6, 0)
        if ns.hui and ns.hui.MakeSolidChip and ns.hui.ChipH then
            r.rare = ns.hui.MakeSolidChip(r, (r:GetFrameLevel() or 0) + 2, ns.hui.ChipH(14))
            ns.hui.PaintSolidChip(r.rare, L["稀有"], RARE_INK)
            r.rare:SetPoint("RIGHT", r, "RIGHT", -6, 0)
        end
        if ns.hui and ns.hui.BuildRoundBorder then
            r.__borderPieces = ns.hui.BuildRoundBorder(r, 6, { 1, 1, 1, 0.9 }, r, "BORDER", "both", 1)
        end
        if ns.hui and ns.hui.BuildRoundedBG then
            r.__hl = FlattenPieces(ns.hui.BuildRoundedBG(r, M.ROW_RADIUS,
                { 1, 1, 1, DG.LOOT_CARD_BG_HOVER }, "both"))
            PiecesSetShown(r.__hl, false)
        end
        r.__idx = i
        r:SetScript("OnClick", function(self) M.Select(self.__en) end)
        r:SetScript("OnEnter", function(self)
            U.dungeonMapHover = self
            PiecesSetShown(self.__hl, true)
        end)
        r:SetScript("OnLeave", function(self)
            if U.dungeonMapHover == self then U.dungeonMapHover = nil end
            PiecesSetShown(self.__hl, false)
        end)
        r:Hide()
        listRows[i] = r
    end
    frame.listRows = listRows
end

local function BuildBlocks()
    local frame = M.SideHost or M.frame
    if not frame or frame.__blocksReady then return end
    frame.__blocksReady = true
    local detChild, innerW = frame.detChild, frame.innerW
    local blocks = {}
    for i = 1, 3 do
        local b = CreateFrame("Frame", nil, detChild)
        b:EnableMouse(false)
        if ns.hui and ns.hui.BuildRoundedBG then
            ns.hui.BuildRoundedBG(b, M.BLK_RADIUS, { 1, 1, 1, M.BLK_BG }, "both", true, 1)
        end
        b.hit = CreateFrame("Button", nil, b)
        b.hit:RegisterForClicks("LeftButtonUp")
        b.hit:SetHeight(M.BLK_MIN_H)
        b.arrD = b:CreateTexture(nil, "ARTWORK")
        b.arrD:SetSize(M.BLK_ARROW, M.BLK_ARROW)
        b.arrD:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\textures\\arrow.tga")
        b.arrD:SetRotation(math.pi)
        b.arrU = b:CreateTexture(nil, "ARTWORK")
        b.arrU:SetSize(M.BLK_ARROW, M.BLK_ARROW)
        b.arrU:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\textures\\arrow.tga")
        for _, at in ipairs({ b.arrD, b.arrU }) do
            at:SetVertexColor(Unpack(C_GOLD))
            at:SetPoint("TOPLEFT", b, "TOPLEFT", M.BLK_PAD, -(M.BLK_TITLE_TOP + 4))
        end
        b.hit:SetScript("OnClick", function(self)
            local key = self.__key
            if not key then return end
            local c = M.CardClosed()
            c[key] = not c[key] or nil
            ns.PlaySound(1)
            M.SyncSide()
        end)
        b.hit:SetScript("OnEnter", function(self)
            if not self.__key then return end
            GameTooltip:SetOwner(self, "ANCHOR_TOP")
            GameTooltip:ClearLines()
            GameTooltip:AddLine(L["点击折叠 / 展开该组"], 1, 1, 1, true)
            GameTooltip:Show()
        end)
        b.hit:SetScript("OnLeave", function() GameTooltip:Hide() end)
        b.hit:EnableMouseWheel(true)
        b.hit:SetScript("OnMouseWheel", function(self, delta)
            M.WheelScroll(detScroll, detChild, delta)
        end)
        b:Hide()
        blocks[i] = b
    end
    local blkLoot, blkSkill, blkGuide = blocks[1], blocks[2], blocks[3]
    blkLoot.hit.__key, blkSkill.hit.__key, blkGuide.hit.__key = "loot", "skill", "guide"

    local detLtTtl = MakeFS(blkLoot, 14, C_GOLD, "LEFT")
    detLtTtl:SetText(L["掉落"])
    local detLtCnt = MakeFS(blkLoot, 14, C_GREY, "RIGHT")
    local detLtNote = MakeFS(blkLoot, 14, C_GREY, "LEFT")
    detLtNote:SetText(L["暂无掉落数据"])
    detLtNote:Hide()

    local detSkTtl = MakeFS(blkSkill, 14, C_GOLD, "LEFT")
    detSkTtl:SetText(L["boss技能"])

    local detGdTtl = MakeFS(blkGuide, 14, C_GOLD, "LEFT")
    detGdTtl:SetText(L["攻略"])
    local detGd = MakeFS(blkGuide, 14, C_TEXT, "LEFT")
    detGd:SetWidth(innerW - M.BLK_PAD * 2)
    detGd:SetWordWrap(true)
    frame.blkLoot, frame.blkSkill, frame.blkGuide = blkLoot, blkSkill, blkGuide
    frame.detLtTtl, frame.detLtCnt, frame.detLtNote = detLtTtl, detLtCnt, detLtNote
    frame.detSkTtl = detSkTtl
    frame.detGdTtl, frame.detGd = detGdTtl, detGd
end

local function BuildSideRows()
    local frame = M.SideHost or M.frame
    if not frame or frame.__rowsReady then return end
    frame.__rowsReady = true
    local innerW = frame.innerW
    local blkLoot, blkSkill = frame.blkLoot, frame.blkSkill
    local rowW = innerW - M.BLK_PAD * 2
    local lootRows = {}
    for i = 1, M.MAX_LOOT do
        local r = CreateFrame("Button", nil, blkLoot)
        r:SetSize(rowW, M.CARD_H)
        r.icon = r:CreateTexture(nil, "ARTWORK")
        r.icon:SetSize(M.CARD_ICON, M.CARD_ICON)
        r.icon:SetPoint("LEFT", r, "LEFT", 6, 0)
        r.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
        if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(r.icon) end
        r.name = MakeFS(r, M.CARD_FS_NAME, C_TEXT, "LEFT")
        r.name:SetPoint("TOPLEFT", r, "TOPLEFT", 6 + M.CARD_ICON + 6, -7)
        r.name:SetWordWrap(false)
        r.tp = MakeFS(r, M.CARD_FS_META, C_GREY, "LEFT")
        r.tp:SetPoint("TOPLEFT", r, "TOPLEFT", 6 + M.CARD_ICON + 6, -24)
        r.ch = MakeFS(r, M.CARD_FS_META, C_GREY, "RIGHT")
        r.ch:SetPoint("TOPRIGHT", r, "TOPRIGHT", -6, -7)
        r.tag = MakeFS(r, M.CARD_FS_META, { 0.42, 0.94, 0.62 }, "RIGHT")
        r.tag:SetText(L["新"])
        r.tag:SetPoint("TOPRIGHT", r, "TOPRIGHT", -6, -24)
        r.name:SetWidth(rowW - (6 + M.CARD_ICON + 6) - 34)
        if ns.hui and ns.hui.BuildRoundedBG then
            r.__hl = FlattenPieces(ns.hui.BuildRoundedBG(r, M.ROW_RADIUS,
                { 1, 1, 1, DG.LOOT_CARD_BG_HOVER }, "both", true, 1, true))
            PiecesSetShown(r.__hl, false)
        end
        r:SetScript("OnEnter", function(self)
            U.dungeonMapHover = self
            PiecesSetShown(self.__hl, true)
            if self.__it then DG.ShowItemTip(self, self.__it) end
        end)
        r:SetScript("OnLeave", function(self)
            if U.dungeonMapHover == self then U.dungeonMapHover = nil end
            PiecesSetShown(self.__hl, false)
            GameTooltip:Hide()
        end)
        r:SetScript("OnClick", function(self, button) DG.ItemShiftClick(self, button) end)
        r:Hide()
        lootRows[i] = r
    end

    local skW = rowW - 6
    local skillRows = {}
    for i = 1, M.MAX_SKILL do
        local r = CreateFrame("Button", nil, blkSkill)
        r:SetSize(skW, M.CARD_H)
        r.icon = r:CreateTexture(nil, "ARTWORK")
        r.icon:SetSize(M.CARD_ICON, M.CARD_ICON)
        r.icon:SetPoint("TOPLEFT", r, "TOPLEFT", 0, 0)
        r.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
        if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(r.icon) end
        r.fs = MakeFS(r, 14, C_TEXT, "LEFT")
        r.fs:SetWidth(skW - M.CARD_ICON - 6)
        r.fs:SetWordWrap(true)
        r.fs:SetPoint("TOPLEFT", r.icon, "TOPRIGHT", 6, 0)
        r.ds = MakeFS(r, 14, C_TEXT, "LEFT")
        r.ds:SetWidth(skW - M.CARD_ICON - 6)
        r.ds:SetWordWrap(true)
        r.ds:SetPoint("TOPLEFT", r.fs, "BOTTOMLEFT", 0, -2)
        r:SetScript("OnEnter", function(self)
            if self.__sid then M.ShowSpellTip(self, self.__sid) end
        end)
        r:SetScript("OnLeave", function() GameTooltip:Hide() end)
        r:Hide()
        skillRows[i] = r
    end
    frame.lootRows, frame.skillRows = lootRows, skillRows
end

local function BuildFinal()
    local frame = M.frame
    if not frame or frame.__poolsReady then return end
    frame.__poolsReady = true
    if frame:IsShown() then M.Paint(M.curD) end
end
M.EnsurePins = BuildPins
M.EnsureListRows = BuildListRows
M.EnsureBlocks = BuildBlocks
M.EnsureSideRows = BuildSideRows
M.EnsureFinal = BuildFinal

local function MakeSideBar(side, scroll, child)
    if not (side and scroll and child) then return nil end
    local bar = CreateFrame("Slider", nil, side, "UIPanelScrollBarTemplate")
    bar.__scroll = scroll
    bar.__child = child
    bar:SetScript("OnValueChanged", function(self, value)
        if self.__sync then return end
        local sc = self.__scroll
        if sc and type(value) == "number" then sc:SetVerticalScroll(value) end
    end)
    bar:SetWidth(16)
    bar:SetPoint("TOPRIGHT", side, "TOPRIGHT", -3, -18)
    bar:SetPoint("BOTTOMRIGHT", side, "BOTTOMRIGHT", -3, 18)
    for _, k in ipairs({ bar:GetChildren() }) do k:Hide() end
    local track = bar:CreateTexture(nil, "BACKGROUND")
    track:SetAllPoints(bar)
    track:SetColorTexture(1, 1, 1, 0.08)
    local thumb = bar:GetThumbTexture()
    if thumb then
        thumb:SetTexture("Interface\\Buttons\\WHITE8X8")
        thumb:SetVertexColor(0.62, 0.51, 0.24, 1)
        thumb:SetSize(10, 36)
    end
    bar:SetMinMaxValues(0, 1)
    bar:SetValueStep(1)
    bar:SetValue(0)
    bar:Hide()
    scroll.__bar = bar
    scroll.__child = child
    return bar
end

function M.BuildSide(f, w, h, withBar, bgLayer)
    if not f then return end
    local side = CreateFrame("Frame", nil, f, "BackdropTemplate")
    side:SetSize(w, h)
    side:EnableMouse(true)
    side:EnableMouseWheel(true)
    if ns.hui and ns.hui.BuildRoundedBG then
        ns.hui.BuildRoundedBG(side, M.BLK_RADIUS, bgLayer or ns.hui.layer.L2, "both", true, 1)
    else
        side:SetBackdrop({
            bgFile = "Interface\\Buttons\\WHITE8X8",
            edgeFile = "Interface\\Buttons\\WHITE8X8",
            edgeSize = 1,
        })
        side:SetBackdropColor(1, 1, 1, 0.03)
        side:SetBackdropBorderColor(1, 1, 1, 0.10)
    end
    side:Hide()

    local barW = withBar and 16 or 0
    local innerW = w - M.SIDE_PAD * 2 - barW

    local listScroll = CreateFrame("ScrollFrame", nil, side)
    listScroll:SetPoint("TOPLEFT", side, "TOPLEFT", M.SIDE_PAD, -M.SIDE_PAD)
    listScroll:SetPoint("BOTTOMRIGHT", side, "BOTTOMRIGHT", -(M.SIDE_PAD + barW), M.SIDE_PAD)
    local listChild = CreateFrame("Frame", nil, listScroll)
    listChild:SetSize(innerW, 10)
    listScroll:SetScrollChild(listChild)
    listScroll:EnableMouseWheel(true)
    listScroll:SetScript("OnMouseWheel", function(self, delta)
        M.WheelScroll(self, listChild, delta)
    end)
    local hdrLogo = listChild:CreateTexture(nil, "ARTWORK")
    hdrLogo:SetTexture(M.LOGO_TEX)
    hdrLogo:SetSize(M.LOGO_SIZE, M.LOGO_SIZE)
    hdrLogo:SetPoint("TOPLEFT", listChild, "TOPLEFT", 0, 0)

    local listHdr = MakeFS(listChild, 14, C_GOLD, "LEFT")
    listHdr:SetPoint("TOPLEFT", listChild, "TOPLEFT", M.LOGO_SIZE + 6, 0)
    listHdr:SetText(L["首领"])

    local listNote = MakeFS(listChild, 14, C_GREY, "LEFT")
    listNote:SetPoint("TOPLEFT", listChild, "TOPLEFT", 2, -26)
    listNote:SetWidth(innerW - 4)
    listNote:SetWordWrap(true)
    listNote:SetText(L["尚未收录这个副本的 boss 名单，数据补上后会自动出现。"])
    listNote:Hide()

    local detScroll = CreateFrame("ScrollFrame", nil, side)
    detScroll:SetPoint("TOPLEFT", side, "TOPLEFT", M.SIDE_PAD, -M.SIDE_PAD)
    detScroll:SetPoint("BOTTOMRIGHT", side, "BOTTOMRIGHT", -(M.SIDE_PAD + barW), M.SIDE_PAD)
    local detChild = CreateFrame("Frame", nil, detScroll)
    detChild:SetSize(innerW, 10)
    detScroll:SetScrollChild(detChild)
    detScroll:EnableMouseWheel(true)
    detScroll:SetScript("OnMouseWheel", function(self, delta)
        M.WheelScroll(self, detChild, delta)
    end)

    local detBack = Host.NewButton(detChild, L["全部首领"], 96, 24, 14)
    detBack:SetScript("OnClick", function() M.ShowList() end)
    detBack:SetPoint("TOPRIGHT", detChild, "TOPRIGHT", 0, 0)
    if Host.AddBtnIcon then Host.AddBtnIcon(detBack, "BackChevron", 16, 6) end

    local detName = MakeFS(detChild, 16, C_GOLD, "LEFT")
    detName:SetWordWrap(false)

    if barW > 0 then
        f.listBar = MakeSideBar(side, listScroll, listChild)
        f.detBar = MakeSideBar(side, detScroll, detChild)
    end

    f.innerW = innerW
    f.side = side
    f.listScroll = listScroll
    f.listChild = listChild
    f.listHdr = listHdr
    f.hdrLogo = hdrLogo
    f.listNote = listNote
    f.detScroll = detScroll
    f.detChild = detChild
    f.detBack = detBack
    f.detName = detName
    f.detChildW = innerW - M.BLK_PAD * 2

    local prev = M.SideHost
    M.SideHost = f
    M.EnsureListRows()
    M.EnsureBlocks()
    M.EnsureSideRows()
    M.SideHost = prev
    return side
end

function M.Build(detail, hero)
    local frame = CreateFrame("Frame", nil, detail)
    frame:SetPoint("TOPLEFT", detail, "TOPLEFT", 0, -DG.GUIDE_TOP_Y)
    frame:SetPoint("BOTTOMRIGHT", detail, "BOTTOMRIGHT", 0, 0)
    if hero then frame:SetFrameLevel(hero:GetFrameLevel() + 1) end
    frame:Hide()

    local hdrCard = CreateFrame("Frame", nil, frame, "BackdropTemplate")
    hdrCard:SetPoint("TOPLEFT", frame, "TOPLEFT", 0, 0)
    hdrCard:SetSize(M.MAP_W, M.HDR_CARD_H)
    hdrCard:SetFrameLevel(frame:GetFrameLevel() + 1)
    if ns.hui and ns.hui.BuildRoundedBG then
        ns.hui.BuildRoundedBG(hdrCard, M.BLK_RADIUS, ns.hui.layer.L2, "both", true, 1)
    else
        hdrCard:SetBackdrop({
            bgFile = "Interface\\Buttons\\WHITE8X8",
            edgeFile = "Interface\\Buttons\\WHITE8X8",
            edgeSize = 1,
        })
        hdrCard:SetBackdropColor(1, 1, 1, 0.03)
        hdrCard:SetBackdropBorderColor(1, 1, 1, 0.10)
    end

    local canvas = CreateFrame("Frame", nil, frame)
    canvas:SetPoint("TOPLEFT", frame, "TOPLEFT", 0, 0)
    canvas:SetSize(1, 1)
    canvas:Hide()

    local tiles = {}
    for n = 1, M.N do
        local t = canvas:CreateTexture(nil, "ARTWORK")
        t:SetTexCoord(0, 1, 0, 1)
        t:Hide()
        tiles[n] = t
    end

    local customTex = canvas:CreateTexture(nil, "ARTWORK")
    customTex:SetTexCoord(0, 1, 0, 1)
    customTex:Hide()

    local areaTex = canvas:CreateTexture(nil, "OVERLAY")
    areaTex:SetDrawLayer("OVERLAY", 2)
    areaTex:SetTexCoord(0, 1, 0, 1)
    areaTex:Hide()

    local routeLayer = CreateFrame("Frame", nil, frame)
    routeLayer:SetPoint("TOPLEFT", frame, "TOPLEFT", 0, 0)
    routeLayer:SetSize(1, 1)
    routeLayer:SetFrameLevel(frame:GetFrameLevel() + 2)
    routeLayer:Hide()

    local empty = MakeFS(frame, 14, C_GREY, "CENTER")
    empty:SetPoint("CENTER", frame, "TOPLEFT", (M.FRAME_W - M.SIDE_W - M.SIDE_GAP) / 2, -(M.HDR_CARD_H + M.HDR_GAP + M.MAP_H / 2))
    empty:SetText(L["这个副本没有客户端自带的地图。"])
    empty:Hide()

    local pins = CreateFrame("Frame", nil, frame)
    pins:SetPoint("TOPLEFT", frame, "TOPLEFT", 0, 0)
    pins:SetSize(1, 1)
    pins:SetFrameLevel(frame:GetFrameLevel() + 3)
    pins:Hide()
    local bar = CreateFrame("Frame", nil, frame)
    bar:SetHeight(M.BAR_H)
    bar:SetWidth(M.MAX_LAYERS * (M.LAYER_W + M.LAYER_GAP))
    bar:Hide()

    local btns = {}
    for i = 1, M.MAX_LAYERS do
        local bt = Host.NewButton(bar, "", M.LAYER_W, M.BAR_H, 14)
        bt:SetFrameLevel(frame:GetFrameLevel() + 2)
        bt.__idx = i
        bt:SetScript("OnClick", function(self) M.SetLayer(self.__idx) end)
        bt:Hide()
        btns[i] = bt
    end

    local bossPinBtn = Host.NewButton(frame, "", M.PIN_BTN_W, M.BAR_H, 14)
    bossPinBtn:SetFrameLevel(frame:GetFrameLevel() + 2)
    Host.SetButtonSelected(bossPinBtn, false)
    bossPinBtn:SetScript("OnClick", function() M.ShowPinMenu(bossPinBtn) end)
    bossPinBtn:Hide()

    local routePinBtn = Host.NewButton(frame, "", M.PIN_BTN_W, M.BAR_H, 14)
    routePinBtn:SetFrameLevel(frame:GetFrameLevel() + 2)
    Host.SetButtonSelected(routePinBtn, false)
    routePinBtn:SetScript("OnClick", function() M.ShowRouteMenu(routePinBtn) end)
    routePinBtn:Hide()

    if hero then
        local bossModel = CreateFrame("PlayerModel", nil, hero)
        bossModel:SetWidth(M.BOSS_MODEL_W)
        bossModel:SetPoint("TOPRIGHT", hero, "TOPRIGHT", -6, M.BOSS_MODEL_UP)
        bossModel:SetPoint("BOTTOMRIGHT", hero, "BOTTOMRIGHT", -6, 6)
        bossModel:EnableMouse(false)
        bossModel:EnableMouseWheel(false)
        if bossModel.SetKeepModelOnHide then bossModel:SetKeepModelOnHide(true) end
        bossModel:Hide()
        frame.bossModel = bossModel
    end

    local side = M.BuildSide(frame, M.SIDE_W, M.FRAME_H)
    side:SetPoint("TOPLEFT", frame, "TOPLEFT", M.FRAME_W - M.SIDE_W, 0)

    frame.canvas = canvas
    frame.hdrCard = hdrCard
    frame.tiles = tiles
    frame.customTex = customTex
    frame.areaTex = areaTex
    frame.empty = empty
    frame.pins = pins
    frame.bar = bar
    frame.btns = btns
    frame.route = routeLayer
    frame.bossPinBtn = bossPinBtn
    frame.routePinBtn = routePinBtn
    local pinStore = DungeonsForeverDB and DungeonsForeverDB.dungeon
    M.hideBossPins = (pinStore and pinStore.mapBossHidden) and true or false
    M.hideQuestPins = (pinStore and pinStore.mapQuestHidden) and true or false
    M.hideNotePins = (pinStore and pinStore.mapNoteHidden) and true or false
    M.frame = frame
    local queued = (type(DG) == "table" and type(DG.PushStep) == "function")
    if queued then
        DG.PushStep(BuildPins)
        DG.PushStep(BuildListRows)
        DG.PushStep(BuildBlocks)
        DG.PushStep(BuildSideRows)
        DG.PushStep(BuildFinal)
        DG.RunSteps()
    else
        BuildPins()
        BuildListRows()
        BuildBlocks()
        BuildSideRows()
        BuildFinal()
    end
    return frame
end

function M.SyncScrollBar(scroll)
    local bar = (type(scroll) == "table") and scroll.__bar or nil
    if not bar then return end
    local child = scroll.__child
    local ch = child and child:GetHeight() or 0
    local sh = scroll:GetHeight() or 0
    if type(ch) ~= "number" or type(sh) ~= "number" then return end
    local max = math.floor(ch - sh)
    local v = scroll:GetVerticalScroll() or 0
    bar.__sync = true
    if max <= 1 then
        bar:SetMinMaxValues(0, 1)
        bar:SetValue(0)
        bar:Hide()
        if v ~= 0 then scroll:SetVerticalScroll(0) end
    else
        bar:SetMinMaxValues(0, max)
        if v < 0 then v = 0 end
        if v > max then
            v = max
            scroll:SetVerticalScroll(max)
        end
        bar:SetValue(v)
        bar:Show()
    end
    bar.__sync = nil
end

function M.WheelScroll(scroll, child, delta)
    if not (scroll and child) then return end
    local ch = child:GetHeight()
    local sh = scroll:GetHeight()
    if type(ch) ~= "number" or type(sh) ~= "number" then return end
    local maxScroll = math.max(0, ch - sh)
    scroll:SetVerticalScroll(math.max(0, math.min(maxScroll, scroll:GetVerticalScroll() - delta * 48)))
    M.SyncScrollBar(scroll)
end

function M.SyncBar(layers, cur)
    local frame = M.frame
    if not frame then return end
    local n = layers and #layers or 0
    local multi = (n > 1) or (n == 1 and SHOW_FLOORS[M.curId] ~= nil)
    frame.bar:SetShown(multi)
    if not multi then
        for i = 1, M.MAX_LAYERS do frame.btns[i]:Hide() end
        return
    end
    local GAP = M.LAYER_GAP
    local fmt = L["第 %d 层"] or "第 %d 层"
    local id = M.curId
    local wide = (n > 7)
    local pad = wide and 12 or 24
    local ws = {}
    for i = 1, n do
        local bt = frame.btns[i]
        local fn = SHOW_FLOORS[id] and M.FloorNumAt(id, i) or i
        bt:SetText(FloorName(id, fn) or fmt:format(fn))
        local fs = bt:GetFontString()
        local tw = fs and fs:GetStringWidth() or 0
        ws[i] = math.max(M.LAYER_W, math.ceil(tw) + pad)
    end
    local avail = M.FRAME_W - M.SIDE_PAD * 2
    if frame.bossPinBtn and frame.bossPinBtn:IsShown() then
        avail = avail - frame.bossPinBtn:GetWidth() - M.PIN_BTN_GAP
    end
    if frame.routePinBtn and frame.routePinBtn:IsShown() then
        avail = avail - frame.routePinBtn:GetWidth() - M.PIN_BTN_GAP
    end
    avail = avail - 12
    avail = math.max(240, math.min(avail, wide and 451 or 560))
    local yStep = (frame.btns[1] and frame.btns[1]:GetHeight()) or M.BAR_H
    local rowOf = {}
    local total = 0
    for i = 1, n do
        total = total + ws[i] + (i > 1 and GAP or 0)
    end
    if total <= avail then
        for i = 1, n do rowOf[i] = 1 end
    else
        local nBreak = n - 1
        local bestRows, bestW, bestMask
        for mask = 0, 2 ^ nBreak - 1 do
            local rows, mx, acc, cnt, ok = 1, 0, 0, 0, true
            for i = 1, n do
                cnt = cnt + 1
                acc = acc + ws[i] + (cnt > 1 and GAP or 0)
                local brk = (i < n) and (math.floor(mask / 2 ^ (i - 1)) % 2 == 1)
                if brk or i == n then
                    if acc > avail then
                        ok = false
                        break
                    end
                    if acc > mx then mx = acc end
                    if brk then
                        rows = rows + 1
                        acc, cnt = 0, 0
                    end
                end
            end
            if ok and (not bestRows or rows < bestRows or (rows == bestRows and mx < bestW)) then
                bestRows, bestW, bestMask = rows, mx, mask
            end
        end
        if bestMask then
            local r = 1
            for i = 1, n do
                rowOf[i] = r
                if i < n and math.floor(bestMask / 2 ^ (i - 1)) % 2 == 1 then r = r + 1 end
            end
        else
            for i = 1, n do rowOf[i] = i end
        end
    end
    local rows = (total <= avail) and 1 or math.max(rowOf[1], rowOf[n])
    local yBase = (rows - 1) * yStep / 2
    local i = 1
    while i <= n do
        local rr = rowOf[i]
        local j = i
        while j <= n and rowOf[j] == rr do j = j + 1 end
        local y = yBase - (rr - 1) * yStep
        local off = 0
        for k = j - 1, i, -1 do
            local bt = frame.btns[k]
            bt:ClearAllPoints()
            bt:SetPoint("TOPRIGHT", frame.bar, "TOPRIGHT", -off, y)
            bt:SetWidth(ws[k])
            local sel = (k == cur)
            Host.SetButtonSelected(bt, sel)
            bt:Show()
            off = off + ws[k] + GAP
        end
        i = j
    end
    for i = n + 1, M.MAX_LAYERS do frame.btns[i]:Hide() end
end

function M.SetLayer(i)
    local layers = M.LayersFor(M.curId)
    if not (layers and layers[i]) then return end
    if i == M.curLayer then return end
    M.curLayer = i
    M.Paint(M.curD)
end

function M.LayerOf(id, floorNum)
    local layers = M.LayersFor(id)
    if not (layers and floorNum) then return nil end
    for i = 1, #layers do
        if M.FloorNumAt(id, i) == floorNum then return i end
    end
    return nil
end

function M.StepTarget(dir, to)
    local layers = M.LayersFor(M.curId)
    local cur = M.curLayer
    if not (layers and cur) then return nil end
    local i = to and M.LayerOf(M.curId, to) or (dir and (cur + dir))
    if not i or i < 1 or i > #layers or i == cur then return nil end
    local fn = SHOW_FLOORS[M.curId] and M.FloorNumAt(M.curId, i) or i
    return i, fn, FloorName(M.curId, fn) or format(L["第 %d 层"], fn)
end

function M.StepFloor(dir, to)
    local i = M.StepTarget(dir, to)
    if not i then return false end
    M.SetLayer(i)
    return true
end

function M.CurFloorNum()
    local idx = M.curLayer
    if not (M.curId and idx) then return nil end
    if M.LayersFor(M.curId) then return M.FloorNumAt(M.curId, idx) end
    return 1
end

local function pulseDrv()
    if M.pulseDriver then return M.pulseDriver end
    local d = CreateFrame("Frame")
    d:SetSize(1, 1)
    d:Hide()
    d:SetScript("OnUpdate", function(self)
        local t = GetTime()
        local btn = M.pulseBtn
        local untilT = M.pulseUntil or 0
        if not (btn and btn.__ring and btn:IsShown()) or t >= untilT then
            if btn and btn.__ring then
                btn.__ring:SetAlpha(1)
                btn.__ring:Hide()
            end
            M.pulseBtn = nil
            self:Hide()
            return
        end
        local ph = ((t - (M.pulseStart or t)) % 1.4) / 1.4
        local base = M.PIN_SIZE * M.PIN_RING_K
        local sz = base * (1 + 0.06 * math.sin(ph * 6.2832))
        local a = 0.88 + 0.12 * math.sin(ph * 6.2832 + 1.5708)
        local left = untilT - t
        if left < 0.7 then a = a * (left / 0.7) end
        btn.__ring:SetSize(sz, sz)
        btn.__ring:SetAlpha(a)
    end)
    M.pulseDriver = d
    return d
end

function M.HighlightPin(btn, secs)
    if not (btn and btn.__ring) then return false end
    btn.__ring:SetSize(M.PIN_SIZE * M.PIN_RING_K, M.PIN_SIZE * M.PIN_RING_K)
    btn.__ring:SetAlpha(1)
    btn.__ring:Show()
    M.pulseBtn = btn
    M.pulseStart = GetTime()
    M.pulseUntil = M.pulseStart + (secs or M.PIN_RING_SECS)
    pulseDrv():Show()
    return true
end

function M.ArriveAt(fromFloor, kind, tox, toy, host)
    local frame = host or M.frame
    if not (frame and frame.pinBtns and fromFloor) then return false end
    local want = (kind == "next" and "prev") or (kind == "prev" and "next") or nil
    local paired, exact, stair, anyTo, anyKind
    local tol = M.PIN_LINK_TOL
    for i = 1, M.MAX_PINS do
        local b = frame.pinBtns[i]
        local p = b and b.__p
        if b and b:IsShown() and p then
            local k = b.__kind
            if k == "prev" or k == "next" or k == "entrance" then
                if tox and toy and p.left and p.top
                    and math.abs(p.left - tox) <= tol and math.abs(p.top - toy) <= tol then
                    paired = paired or b
                elseif p.to == fromFloor then
                    if want and k == want then
                        exact = exact or b
                    elseif k == "prev" or k == "next" then
                        stair = stair or b
                    else
                        anyTo = anyTo or b
                    end
                elseif want and k == want then
                    anyKind = anyKind or b
                end
            end
        end
    end
    local pick = paired or exact or stair or anyTo or anyKind
    if pick then return M.HighlightPin(pick) end
    return false
end

local SEQ_OK = {}

local function seqOk(id, layers)
    local ok = SEQ_OK[id]
    if ok ~= nil then return ok end
    ok = true
    for k = 1, #layers do
        local n = tonumber(layers[k]:match("(%d+)_")) or k
        if n ~= k then ok = false break end
    end
    SEQ_OK[id] = ok
    return ok
end

function M.FloorNumAt(id, idx)
    local i = idx or 1
    local o = FLOOR_NO[id] and FLOOR_NO[id][i]
    if o then return o end
    local layers = M.LayersFor(id)
    local lay = layers and layers[i]
    if not lay then return i end
    local n = tonumber(lay:match("(%d+)_")) or i
    if SHOW_FLOORS[id] then return n end
    if #layers > 1 and not seqOk(id, layers) then return i end
    return n
end

function M.BossColor(id, en)
    local bs = M.BossesFor(id)
    if bs and en then
        for i = 1, #bs do
            if bs[i].en == en then
                local c = M.BOSS_PALETTE[((i - 1) % #M.BOSS_PALETTE) + 1]
                return c[1], c[2], c[3]
            end
        end
    end
    return 1, 1, 1
end

M.routeHidden = {}

M.ROUTE_ON = { blackfathom_deeps = true, ragefire_chasm = true, wailing_caverns = true, hall_of_thanes = true, ruins_of_lordaeron = true, the_deadmines = true,
               shadowfang_keep = true, the_stockade = true,
               gnomeregan = true, city_of_dalaran = true, excavation_wetlands = true,
               razorfen_kraul = true, razorfen_downs = true, uldaman = true,
               sm_graveyard = true, sm_library = true, sm_armory = true, sm_cathedral = true,
               blackrock_depths = true, lower_blackrock_spire = true, upper_blackrock_spire = true,
               maraudon = true, zul_farrak = true, sunken_temple = true, scholomance = true,
               stratholme_main = true, stratholme_service = true,
               dire_maul_east = true, dire_maul_north = true, dire_maul_west = true }

function M.RouteOn(id)
    return id ~= nil and M.ROUTE_ON[id] == true
end

function M.RouteSegKey(id, floor, idx)
    return tostring(id) .. ":" .. tostring(floor) .. ":" .. tostring(idx)
end

function M.RouteVisibleCount(id, floor)
    if not M.RouteOn(id) then return 0, 0 end
    local segs = id and ns.DungeonRoute and ns.DungeonRoute[id] and ns.DungeonRoute[id][floor]
    if type(segs) ~= "table" then return 0, 0 end
    local vis, tot = 0, 0
    for i = 1, #segs do
        tot = tot + 1
        if not M.routeHidden[M.RouteSegKey(id, floor, i)] then
            vis = vis + 1
        end
    end
    return vis, tot
end

function M.HasRoute(id, floor)
    if not M.RouteOn(id) then return false end
    local row = id and ns.DungeonRoute and ns.DungeonRoute[id]
    if type(row) ~= "table" then return false end
    if floor then
        local segs = row[floor]
        return type(segs) == "table" and #segs > 0
    end
    for _, v in pairs(row) do
        if type(v) == "table" and #v > 0 then return true end
    end
    return false
end

function M.RouteStops()
    for _, p in ipairs(M.ROUTE_PALETTES) do
        if p.id == M.routePalette then return p.stops end
    end
    return M.ROUTE_PALETTES[1].stops
end

function M.RouteColor(t)
    local C = M.RouteStops()
    if t <= C[1][1] then return C[1][2], C[1][3], C[1][4] end
    for i = 2, #C do
        if t <= C[i][1] then
            local a, b = C[i - 1], C[i]
            local u = (t - a[1]) / (b[1] - a[1])
            return a[2] + (b[2] - a[2]) * u,
                   a[3] + (b[3] - a[3]) * u,
                   a[4] + (b[4] - a[4]) * u
        end
    end
    local z = C[#C]
    return z[2], z[3], z[4]
end

local routePool = {}

local function smoothPts(src)
    local n = #src
    if n < 3 then return src end
    local out = { { src[1][1], src[1][2] } }
    for i = 1, n - 1 do
        local p, q = src[i], src[i + 1]
        out[#out + 1] = { 0.72 * p[1] + 0.28 * q[1], 0.72 * p[2] + 0.28 * q[2] }
        out[#out + 1] = { 0.28 * p[1] + 0.72 * q[1], 0.28 * p[2] + 0.72 * q[2] }
    end
    out[#out + 1] = { src[n][1], src[n][2] }
    return out
end

local function routeTex(host, i)
    local e = routePool[i]
    if not e then
        e = {
            o = host:CreateTexture(nil, "ARTWORK"),
            c = host:CreateTexture(nil, "ARTWORK"),
        }
        e.o:SetTexture(M.ROUTE_DOT_TEX)
        e.o:SetDrawLayer("ARTWORK", 0)
        e.c:SetTexture(M.ROUTE_DOT_TEX)
        e.c:SetDrawLayer("ARTWORK", 1)
        e.o:Hide()
        e.c:Hide()
        routePool[i] = e
    end
    return e
end

local function routeDot(e, host, x, y, cr, cg, cb)
    local edge = M.routeThin and M.ROUTE_THIN_EDGE or M.ROUTE_DOT_EDGE
    local core = M.routeThin and M.ROUTE_THIN_DOT or M.ROUTE_DOT
    e.o:SetSize(edge, edge)
    e.o:ClearAllPoints()
    e.o:SetPoint("CENTER", host, "TOPLEFT", x, -y)
    e.o:SetVertexColor(0.05, 0.04, 0.03, 1)
    e.o:Show()
    e.c:SetSize(core, core)
    e.c:ClearAllPoints()
    e.c:SetPoint("CENTER", host, "TOPLEFT", x, -y)
    e.c:SetVertexColor(cr, cg, cb)
    e.c:SetAlpha(1)
    e.c:Show()
end

function M.SyncRoute(id, floor, cw, ch)
    local frame = M.frame
    local host = frame and frame.route
    if not host then return end
    local used = frame.routeUsed or 0
    local n = 0
    if type(cw) == "number" and cw > 0 and type(ch) == "number" and ch > 0 and M.RouteOn(id) then
        local segs = floor and ns.DungeonRoute and ns.DungeonRoute[id] and ns.DungeonRoute[id][floor]
        if type(segs) == "table" and #segs > 0 then
            local arr, total, dsh = {}, 0, {}
            for si = 1, #segs do
                if M.routeHidden[M.RouteSegKey(id, floor, si)] then
                    arr[si] = nil
                else
                    local src = segs[si].pts
                    local dst = {}
                    for i = 1, #src do
                        dst[i] = { (src[i][1] / 100) * cw, (src[i][2] / 100) * ch }
                    end
                    dst = smoothPts(dst)
                    for i = 2, #dst do
                        total = total + math.sqrt((dst[i][1] - dst[i - 1][1]) ^ 2
                                                + (dst[i][2] - dst[i - 1][2]) ^ 2)
                    end
                    arr[si] = dst
                    if segs[si].dash then dsh[si] = true end
                end
            end
            local step = M.ROUTE_STEP
            local cap = M.MAX_ROUTE_DOTS * 0.95
            if total > 0 and total / step > cap then
                step = total / cap
            end
            local acc = 0
            local full = false
            for si = 1, #segs do
                if full then break end
                local pts = arr[si]
                if pts then
                    local dash = dsh[si]
                    local period = M.ROUTE_DASH_ON + M.ROUTE_DASH_OFF
                    local sd = 0
                    for i = 2, #pts do
                        if full then break end
                        local a, b = pts[i - 1], pts[i]
                        local dx, dy = b[1] - a[1], b[2] - a[2]
                        local d = math.sqrt(dx * dx + dy * dy)
                        if d > 0.01 then
                            local k = math.max(1, math.ceil(d / step))
                            local du = d / k
                            for j = 1, k do
                                if n >= M.MAX_ROUTE_DOTS then
                                    full = true
                                    break
                                end
                                local u = (j - 0.5) / k
                                local ds = sd + du * (j - 0.5)
                                if (not dash) or (ds % period < M.ROUTE_DASH_ON) then
                                    n = n + 1
                                    local t = (total > 0) and ((acc + d * u) / total) or 0
                                    local cr, cg, cb = M.RouteColor(t)
                                    routeDot(routeTex(host, n), host,
                                             a[1] + dx * u, a[2] + dy * u, cr, cg, cb)
                                end
                            end
                            sd = sd + d
                        end
                        acc = acc + d
                    end
                end
            end
        end
    end
    for i = n + 1, used do
        local e = routePool[i]
        if e then
            e.o:Hide()
            e.c:Hide()
        end
    end
    frame.routeUsed = n
    host:SetShown(n > 0)
end

function M.ShowRouteMenu(owner)
    local id, floor = M.curId, M.FloorNumAt(M.curId, M.curLayer or 1)
    if not M.RouteOn(id) then return end
    local segs = id and ns.DungeonRoute and ns.DungeonRoute[id] and ns.DungeonRoute[id][floor]
    if type(segs) ~= "table" or #segs == 0 then return end
    local items = {}
    items[#items + 1] = {
        text = L["全部显示"],
        func = function()
            for i = 1, #segs do
                M.routeHidden[M.RouteSegKey(id, floor, i)] = nil
            end
            M.SyncRoute(id, floor, M.frame and M.frame.pinW, M.frame and M.frame.pinH)
            M.SyncPinBtns()
        end,
    }
    items[#items + 1] = {
        text = L["全部隐藏"],
        func = function()
            for i = 1, #segs do
                M.routeHidden[M.RouteSegKey(id, floor, i)] = true
            end
            M.SyncRoute(id, floor, M.frame and M.frame.pinW, M.frame and M.frame.pinH)
            M.SyncPinBtns()
        end,
    }
    for i = 1, #segs do
        local k = M.RouteSegKey(id, floor, i)
        local hid = M.routeHidden[k] and true or false
        items[#items + 1] = {
            text = StripOrd(segs[i].from) .. " → " .. StripOrd(segs[i].to),
            checked = not hid,
            color = hid and "|cff7a6a52" or nil,
            func = function()
                if hid then
                    M.routeHidden[k] = nil
                else
                    M.routeHidden[k] = true
                end
                M.SyncRoute(id, floor, M.frame and M.frame.pinW, M.frame and M.frame.pinH)
                M.SyncPinBtns()
                M.ShowRouteMenu(owner)
            end,
        }
    end
    items[#items + 1] = {
        text = format(L["配色：%s"], M.ROUTE_PAL_NAMES[M.routePalette] or M.routePalette),
        color = "|cffe0c060",
        func = function()
            M.CycleRoutePalette()
            M.SyncRoute(id, floor, M.frame and M.frame.pinW, M.frame and M.frame.pinH)
            M.ShowRouteMenu(owner)
        end,
    }
    items[#items + 1] = {
        text = format(L["路线粗细：%s"], M.routeThin and L["细"] or L["粗"]),
        color = "|cffe0c060",
        func = function()
            M.routeThin = not M.routeThin
            local s = DungeonsForeverDB and DungeonsForeverDB.dungeon
            if type(s) == "table" then s.mapRouteThin = M.routeThin and nil or false end
            M.SyncRoute(id, floor, M.frame and M.frame.pinW, M.frame and M.frame.pinH)
            M.ShowRouteMenu(owner)
        end,
    }
    ns.hui.ShowMenu(items, { owner = owner, anchor = owner })
end

function M.SyncPins()
    local frame = M.frame
    if not frame then return end
    if not frame.__pinsReady then return end
    local list, n = nil, 0
    local floor
    if M.curId and M.LayersFor(M.curId) then
        floor = M.FloorNumAt(M.curId, M.curLayer or 1)
    elseif M.curId and M.CustomFor(M.curId) then
        floor = 1
    end
    if M.curId and floor then
        list = M.PinsFor(M.curId, floor)
        local ex = M.ExtraPinsFor(M.curId, floor)
        if ex then
            for i = 1, #ex do
                list = list or {}
                list[#list + 1] = ex[i]
            end
        end
        local nts = M.NotePinsFor(M.curId, floor)
        if nts then
            for i = 1, #nts do
                list = list or {}
                list[#list + 1] = nts[i]
            end
        end
    end
    if list and #list > 0 and (M.hideBossPins or M.hideQuestPins or M.hideNotePins) then
        local keep = {}
        for i = 1, #list do
            local p = list[i]
            local k = p.kind or "boss"
            local hide = (M.hideBossPins and (k == "boss" or k == "rare"))
                      or (M.hideQuestPins and (k == "quest" or k == "icon"))
                      or (M.hideNotePins and k == "note")
            if not hide then keep[#keep + 1] = p end
        end
        list = keep
    end
    if list and #list > 0 then
        local lockedPre, preBlock = {}, {}
        if M.QuestPinsOn() then
            for i = 1, #list do
                local p = list[i]
                if (p.kind or "") == "quest" and p.id then
                    local row = DG.QuestRowByID and DG.QuestRowByID(p.id)
                    local pre = row and row[9]
                    if type(pre) == "table" then
                        for _, seg in ipairs(pre) do
                            if DG.QuestState(seg) ~= "done" then
                                lockedPre[p.id] = seg
                                preBlock[seg] = p.id
                                break
                            end
                        end
                    end
                end
            end
        end
        local cw, ch = frame.pinW, frame.pinH
        for i = 1, #list do
            if i > M.MAX_PINS then break end
            n = n + 1
            local p = list[i]
            local bt = frame.pinBtns[n]
            local kind = p.kind or "boss"
            local skip = nil
            bt.__kind, bt.__p = kind, p
            bt.__en, bt.__zh = p.en, p.zh
            if kind == "note" or kind == "quest" or kind == "icon" then
                bt:SetFrameLevel(frame.pins:GetFrameLevel() + 2)
            else
                bt:SetFrameLevel(frame.pins:GetFrameLevel())
            end
            bt.__qState, bt.__qPre, bt.__qPreOf = nil, nil, nil
            bt:ClearAllPoints()
            bt:SetPoint("CENTER", frame.pins, "TOPLEFT",
                        (p.left / 100) * cw, -(p.top / 100) * ch)
            local nm, cr, cg, cb
            if kind == "boss" then
                nm = p.zh or p.en or ""
                cr, cg, cb = M.BossColor(M.curId, p.en)
            elseif kind == "quest" then
                nm = ""
                cr, cg, cb = Unpack(C_GOLD)
            elseif kind == "icon" then
                nm = ""
                cr, cg, cb = Unpack(C_GOLD)
            elseif kind == "prev" or kind == "next" then
                nm = ""
                cr, cg, cb = Unpack(C_GOLD)
            elseif kind == "object" then
                nm = DG.ItemName(p.id)
                cr, cg, cb = Unpack(C_TEXT)
            elseif kind == "entrance" then
                nm = ""
                cr, cg, cb = Unpack(C_GOLD)
            elseif kind == "dungeon" then
                nm = ""
                cr, cg, cb = Unpack(C_GOLD)
            elseif kind == "note" then
                nm = ""
                cr, cg, cb = 1, 1, 1
            else
                nm = p.name or ""
                cr, cg, cb = 0.72, 0.76, 0.85
            end
            if kind == "quest" then
                local st = DG.QuestState(p.id)
                bt.__av:Hide()
                if st ~= "todo" then
                    skip = true
                elseif preBlock[p.id] then
                    bt.dot:SetShown(true)
                    bt.dot:SetTexture(M.PIN_QUEST_PRE_TEX)
                    bt.dot:SetVertexColor(1, 1, 1)
                    bt.__qState, bt.__qPreOf = "pre", preBlock[p.id]
                elseif lockedPre[p.id] then
                    bt.dot:SetShown(true)
                    bt.dot:SetTexture(M.PIN_QUEST_LOCKED_TEX)
                    bt.dot:SetVertexColor(1, 1, 1)
                    bt.__qState, bt.__qPre = "locked", lockedPre[p.id]
                else
                    bt.dot:SetShown(true)
                    bt.dot:SetTexture(M.PIN_QUEST_READY_TEX)
                    bt.dot:SetVertexColor(1, 1, 1)
                    bt.__qState = "ready"
                end
            elseif kind == "entrance" then
                bt.dot:SetShown(true)
                bt.dot:SetTexture(M.PIN_DOOR_TEX)
                bt.dot:SetVertexColor(1, 1, 1)
                bt.__av:Hide()
            elseif kind == "dungeon" then
                bt.dot:SetShown(true)
                bt.dot:SetTexture(M.PIN_DOOR_TEX)
                bt.dot:SetVertexColor(1, 1, 1)
                bt.__av:Hide()
            elseif kind == "icon" then
                bt.dot:SetShown(true)
                bt.dot:SetTexture(M.PIN_QUEST_READY_TEX)
                bt.dot:SetVertexColor(1, 1, 1)
                bt.__av:Hide()
            elseif kind == "prev" or kind == "next" then
                bt.dot:SetShown(true)
                bt.dot:SetTexture((kind == "prev") and M.PIN_STAIR_UP_TEX or M.PIN_STAIR_DN_TEX)
                bt.dot:SetVertexColor(1, 1, 1)
                bt.__av:Hide()
            elseif kind == "object" then
                bt.dot:SetShown(true)
                bt.dot:SetTexture(DG.ItemIcon(p.id))
                bt.dot:SetVertexColor(1, 1, 1)
                bt.__av:Hide()
            elseif kind == "rare" then
                bt.dot:SetShown(true)
                bt.dot:SetTexture(M.PIN_BOSS_TEX)
                bt.dot:SetVertexColor(cr, cg, cb)
                bt.__av:Hide()
            elseif kind == "note" then
                bt.dot:SetShown(true)
                bt.dot:SetTexture(M.PIN_NOTE_TEX)
                bt.dot:SetVertexColor(1, 1, 1)
                bt.__av:Hide()
            else
                bt.dot:Hide()
                bt.__av:Show()
                local isSel = (M.detailEn == p.en) or false
                bpPaint(bt.__av, bpDisp(M.curId, p.en), cr, cg, cb, isSel and M.PIN_SIZE or M.PIN_MIN)
            end
            local sel = (kind == "boss") and (M.detailEn == p.en) or false
            if kind == "boss" and not sel then nm = "" end
            bt.nm:SetText(nm or "")
            if bt.__glow then
                local g = M.PIN_GLOW_GAIN
                bt.__glow:SetVertexColor(cr * g, cg * g, cb * g)
                bt.__glow:SetShown(sel)
            end
            if bt.__ring then bt.__ring:Hide() end
            bt.nm:ClearAllPoints()
            if kind == "boss" then
                bt.nm:SetPoint("TOPLEFT", bt.dot, "BOTTOMLEFT", -2, -2)
                bt.nm:SetJustifyH("LEFT")
            else
                bt.nm:SetPoint("TOP", bt.dot, "BOTTOM", 0, -2)
                bt.nm:SetJustifyH("CENTER")
            end
            local fpath, _, fflags = bt.nm:GetFont()
            bt.nm:SetFont(fpath, sel and 14 or 12, fflags)
            bt.nm:SetTextColor(cr, cg, cb)
            bt.dot:ClearAllPoints()
            bt.dot:SetPoint("CENTER", bt, "CENTER", 0, 0)
            local dsz
            if kind == "note" then
                dsz = M.NOTE_SIZE
            elseif kind == "prev" or kind == "next" then
                dsz = M.STAIR_SIZE
            else
                dsz = sel and M.PIN_SIZE or M.PIN_MIN
            end
            bt.dot:SetSize(dsz, dsz)
            if kind == "note" then
                bt:SetSize(M.NOTE_SIZE + 9, M.NOTE_SIZE + 9)
            else
                bt:SetSize(M.PIN_SIZE, M.PIN_SIZE)
            end
            bt:SetScript("OnClick", function(self) M.PinOnClick(self) end)
            bt:SetScript("OnEnter", M.PinOnEnter)
            bt:SetScript("OnLeave", M.PinOnLeave)
            if skip then
                bt.nm:SetText("")
                bt:Hide()
            else
                bt:Show()
            end
        end
    end
    for i = n + 1, M.MAX_PINS do
        frame.pinBtns[i]:Hide()
        frame.pinBtns[i].nm:SetText("")
    end
    local show = (n > 0)
    if not show then
        for i = 1, M.MAX_PINS do
            frame.pinBtns[i]:Hide()
            frame.pinBtns[i].nm:SetText("")
        end
    end
    frame.pins:SetShown(show)
    M.SyncPinBtns()
end

function M.PinOnClick(self, inWorld)
    local kind, p = self.__kind, self.__p
    if kind == "boss" and p and p.en then
        M.Select(p.en)
    elseif kind == "quest" and p and p.id then
        U.dungeonQuestSel = p.id
        U:SetDungeonTab("quest")
    elseif kind == "prev" or kind == "next" then
        local from = M.CurFloorNum()
        if M.StepFloor((kind == "next") and 1 or -1, p and p.to) then
            ns.PlaySound(1)
            M.PinOnLeave()
            M.ArriveAt(from, kind, p and p.tox, p and p.toy)
        end
    elseif kind == "entrance" and p and p.to then
        local from = M.CurFloorNum()
        if M.StepFloor(nil, p.to) then
            ns.PlaySound(1)
            M.PinOnLeave()
            M.ArriveAt(from, "entrance", p.tox, p.toy)
        end
    elseif kind == "dungeon" and p and p.id then
        M.GotoDungeon(p.id, inWorld)
    end
end

function M.GotoDungeon(id, inWorld)
    if not (id and M.DungeonPinName) then return end
    local MW = ns.MapWorldModule
    if MW and MW.OpenDungeon and (inWorld or (MW.Active and MW.Active())) then
        MW.OpenDungeon(id)
        return
    end
    if MW then
        MW.suppress = true
        if MW.Active and MW.Active() then MW.Hide() end
    end
    if WorldMapFrame and WorldMapFrame.IsShown and WorldMapFrame:IsShown() then
        HideUIPanel(WorldMapFrame)
    end
    if ns.ShowDungeonDetail then ns.ShowDungeonDetail(id) end
    local DU = ns.DungeonUI
    if DU and DU.SetDungeonTab then
        pcall(DU.SetDungeonTab, DU, "map")
    end
end

function M.PinOnEnter(self)
    local p = self.__p
    if not p then return end
    if self.__kind == "boss" then
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
        GameTooltip:ClearLines()
        local cr, cg, cb = M.BossColor(M.curId, p.en)
        GameTooltip:AddLine(p.zh or p.en or "", cr, cg, cb, true)
        GameTooltip:AddLine(L["点击查看首领详情"], 0.7, 0.7, 0.7, true)
        GameTooltip:Show()
        return
    end
    if self.__kind == "object" then
        DG.ShowItemTip(self, { p.id })
        return
    end
    GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
    GameTooltip:ClearLines()
    if self.__kind == "quest" then
        local st = self.__qState
        local nm, ok = DG.QuestName(p.id)
        if not ok then DG.RequestQuest(p.id) end
        if st == "locked" then
            local preNm, preOk = DG.QuestName(self.__qPre)
            if not preOk and self.__qPre then DG.RequestQuest(self.__qPre) end
            GameTooltip:AddLine(nm or L["任务"], 0.72, 0.76, 0.85, true)
            GameTooltip:AddLine(format(L["需先完成：%s"], preNm or L["前置任务"]), 1, 0.82, 0, true)
        elseif st == "pre" then
            local blkNm, blkOk = DG.QuestName(self.__qPreOf)
            if not blkOk and self.__qPreOf then DG.RequestQuest(self.__qPreOf) end
            GameTooltip:AddLine(nm or L["任务"], 0.42, 0.62, 0.95, true)
            GameTooltip:AddLine(format(L["完成本任务后解锁：%s"], blkNm or ""), 1, 0.82, 0, true)
        else
            GameTooltip:AddLine(nm or L["任务"], 1, 0.82, 0, true)
        end
        if p.text and p.text ~= "" then
            GameTooltip:AddLine(p.text, 0.88, 0.85, 0.78, true)
        end
        GameTooltip:AddLine(L["点击查看任务详情"], 0.7, 0.7, 0.7, true)
    elseif self.__kind == "dungeon" then
        if p.id then
            GameTooltip:AddLine(M.DungeonPinName(p.id), 1, 0.82, 0, true)
        else
            GameTooltip:AddLine(L["副本入口"], 1, 0.82, 0, true)
        end
        if p.text and p.text ~= "" then
            GameTooltip:AddLine(p.text, 1, 1, 1, true)
        end
        if p.id then
            GameTooltip:AddLine(L["点击切换地图"], 0.7, 0.7, 0.7, true)
        end
    elseif self.__kind == "entrance" then
        GameTooltip:AddLine(L["副本入口"], 1, 0.82, 0, true)
        if p.text and p.text ~= "" then
            GameTooltip:AddLine(p.text, 1, 1, 1, true)
        end
        local _, _, lbl = M.StepTarget(nil, p and p.to)
        if lbl then
            GameTooltip:AddLine(format(L["点击切换地图：%s"], lbl), 0.7, 0.9, 0.7, true)
        end
    elseif self.__kind == "icon" then
        GameTooltip:AddLine(L["任务"], 1, 0.82, 0, true)
        if p.text and p.text ~= "" then
            GameTooltip:AddLine(p.text, 1, 1, 1, true)
        end
    elseif self.__kind == "prev" then
        GameTooltip:AddLine(L["上一层入口"], 1, 0.82, 0, true)
        if p.text and p.text ~= "" then
            GameTooltip:AddLine(p.text, 1, 1, 1, true)
        end
        local _, _, lbl = M.StepTarget(-1, p and p.to)
        if lbl then
            if p.text and p.text ~= "" then
                GameTooltip:AddLine(L["点击切换地图"], 0.7, 0.9, 0.7, true)
            else
                GameTooltip:AddLine(format(L["点击切换地图：%s"], lbl), 0.7, 0.9, 0.7, true)
            end
        end
    elseif self.__kind == "next" then
        GameTooltip:AddLine(L["下一层入口"], 1, 0.82, 0, true)
        if p.text and p.text ~= "" then
            GameTooltip:AddLine(p.text, 1, 1, 1, true)
        end
        local _, _, lbl = M.StepTarget(1, p and p.to)
        if lbl then
            if p.text and p.text ~= "" then
                GameTooltip:AddLine(L["点击切换地图"], 0.7, 0.9, 0.7, true)
            else
                GameTooltip:AddLine(format(L["点击切换地图：%s"], lbl), 0.7, 0.9, 0.7, true)
            end
        end
    elseif self.__kind == "rare" then
        GameTooltip:AddLine(L["稀有"] .. "：" .. (p.name or ""), 0.72, 0.76, 0.85, true)
    elseif self.__kind == "note" then
        GameTooltip:AddLine(L["注释"], 1, 0.82, 0, true)
        if p.text and p.text ~= "" then
            GameTooltip:AddLine(p.text, 1, 1, 1, true)
        end
    end
    GameTooltip:Show()
end

function M.PinOnLeave()
    GameTooltip:Hide()
end

function M.OnQuestData(id)
    local frame = M.frame
    if not (frame and frame.IsShown and frame:IsShown()) then return end
    local owner = GameTooltip and GameTooltip.GetOwner and GameTooltip:GetOwner()
    if not (owner and owner.__kind == "quest" and owner.__p) then return end
    local p = owner.__p
    if p.id == id or owner.__qPre == id or owner.__qPreOf == id then
        M.PinOnEnter(owner)
    end
end

function M.FitPinBtn(bt)
    local fs = bt and bt:GetFontString()
    local w = (fs and fs:GetStringWidth()) or 0
    bt:SetWidth(math.max(M.PIN_BTN_MIN, math.ceil(w + 22)))
end

function M.SyncPinBtns()
    local frame = M.frame
    if not frame then return end
    local bb = frame.bossPinBtn
    if bb then
        local any = M.HasKindPins(M.curId, "boss") or M.HasKindPins(M.curId, "quest")
            or M.HasKindPins(M.curId, "note") or M.HasKindPins(M.curId, "stairs")
        local dim = (M.hideBossPins and M.HasKindPins(M.curId, "boss"))
            or (M.hideQuestPins and M.HasKindPins(M.curId, "quest"))
            or (M.hideNotePins and M.HasKindPins(M.curId, "note")) or false
        bb:SetText(L["图钉显示"])
        Host.SetButtonSelected(bb, dim)
        M.FitPinBtn(bb)
        bb:SetShown(any)
    end
    local rb = frame.routePinBtn
    if rb then
        local vis, tot = M.RouteVisibleCount(M.curId, M.FloorNumAt(M.curId, M.curLayer or 1))
        rb:SetText(L["路线显示"])
        Host.SetButtonSelected(rb, vis < tot)
        M.FitPinBtn(rb)
        rb:SetShown(M.HasRoute(M.curId))
    end
end

function M.ToggleBossPins()
    M.hideBossPins = not M.hideBossPins
    local s = DungeonsForeverDB and DungeonsForeverDB.dungeon
    if type(s) == "table" then s.mapBossHidden = M.hideBossPins or nil end
    M.SyncPins()
end

function M.ToggleQuestPins()
    M.hideQuestPins = not M.hideQuestPins
    local s = DungeonsForeverDB and DungeonsForeverDB.dungeon
    if type(s) == "table" then s.mapQuestHidden = M.hideQuestPins or nil end
    M.SyncPins()
end

function M.ToggleNotePins()
    M.hideNotePins = not M.hideNotePins
    local s = DungeonsForeverDB and DungeonsForeverDB.dungeon
    if type(s) == "table" then s.mapNoteHidden = M.hideNotePins or nil end
    M.SyncPins()
end

function M.ShowPinMenu(owner)
    local items = {}
    local kinds = {
        { key = "boss", label = L["首领图钉"], off = M.hideBossPins },
        { key = "quest", label = L["任务图钉"], off = M.hideQuestPins },
        { key = "note", label = L["提示图钉"], off = M.hideNotePins },
    }
    for i = 1, #kinds do
        local kd = kinds[i]
        local has = M.HasKindPins(M.curId, kd.key)
        items[#items + 1] = {
            text = kd.label,
            checked = has and not kd.off,
            color = (not has or kd.off) and "|cff7a6a52" or nil,
            func = function()
                if kd.key == "boss" then
                    M.ToggleBossPins()
                elseif kd.key == "quest" then
                    M.ToggleQuestPins()
                else
                    M.ToggleNotePins()
                end
                M.SyncPinBtns()
                M.ShowPinMenu(owner)
            end,
        }
    end
    ns.hui.ShowMenu(items, { owner = owner, anchor = owner })
end

local function layoutLootRow(r, it, y, rowW)
    local id = it[1]
    r.icon:SetTexture(DG.ItemIcon(id))
    if ns.hui and ns.hui.SetIconRing then
        ns.hui.SetIconRing(r.icon, { ns.hui.QColor(DG.QualOf(id)) })
    end
    local nm, hasName = DG.ItemName(id)
    r.name:SetText(nm)
    if hasName then
        r.name:SetTextColor(DG.QColor(DG.QualOf(id)))
    else
        r.name:SetTextColor(Unpack(C_GREY))
    end
    r.tp:SetText(DG.ItemMeta(id))
    r.ch:SetText(DG.Pct(it[2]) or "")
    r.tag:SetShown(it[3] and true or false)
    r.__it = it
    PiecesSetShown(r.__hl, false)
    r:ClearAllPoints()
    r:SetPoint("TOPLEFT", r:GetParent(), "TOPLEFT", M.BLK_PAD, y)
    r:SetSize(rowW, M.CARD_H)
    r:Show()
end

local function LayoutCardHead(blk, ttl, isClosed)
    blk.hit:ClearAllPoints()
    blk.hit:SetPoint("TOPLEFT", blk, "TOPLEFT", 0, 0)
    blk.hit:SetPoint("TOPRIGHT", blk, "TOPRIGHT", 0, 0)
    blk.hit:Show()
    blk.arrD:SetShown(not isClosed)
    blk.arrU:SetShown(isClosed)
    ttl:ClearAllPoints()
    ttl:SetPoint("TOPLEFT", blk, "TOPLEFT", M.BLK_TITLE_X, -M.BLK_TITLE_TOP)
end

local BOSS_MODEL_LATE = { 0.6, 3.5 }

function M.BossModelProbeLoaded(m)
    local ok, v = pcall(m.GetDisplayInfo, m)
    return (ok and type(v) == "number" and v ~= 0) or false
end

function M.BossModelAlpha(m, v)
    if m.SetAlpha then m:SetAlpha(v) end
end

function M.BossModelPose(m)
    m:SetRotation(math.rad(-15))
end

local function ApplyModel(m, npc, disp)
    if disp and type(m.SetDisplayInfo) == "function" then
        pcall(m.SetDisplayInfo, m, disp)
    elseif npc then
        m:SetCreature(npc)
    end
end

function M.BossModelLateCheck(m, npc, disp)
    if type(C_Timer) ~= "table" or type(C_Timer.After) ~= "function" then return end
    for i = 1, #BOSS_MODEL_LATE do
        C_Timer.After(BOSS_MODEL_LATE[i], function()
            if not (m:IsShown() and m.__npc == npc and m.__disp == disp) then return end
            if M.BossModelProbeLoaded(m) then return end
            if i < #BOSS_MODEL_LATE then
                ApplyModel(m, npc, disp)
                M.BossModelPose(m)
            else
                m.__npc, m.__disp = nil, nil
                m:Hide()
            end
        end)
    end
end

function M.HideBossModel()
    local frame = M.frame
    local m = frame and frame.bossModel
    if not (m and m:IsShown()) then return end
    m:Hide()
end

function M.SyncBossModel()
    local frame = M.frame
    if not (frame and frame.bossModel) then return end
    local npc, disp
    if M.detailEn then
        local bosses = M.BossesFor(M.curId)
        for i = 1, #(bosses or {}) do
            if bosses[i].en == M.detailEn then
                npc = tonumber(bosses[i].npc)
                local row = ns.BossModelDisplay and ns.BossModelDisplay[M.curId]
                disp = row and row[bosses[i].en] or nil
                break
            end
        end
    end
    local m = frame.bossModel
    if (not npc and not disp)
       or (type(m.SetCreature) ~= "function" and type(m.SetDisplayInfo) ~= "function") then
        m.__npc, m.__disp = nil, nil
        M.BossModelAlpha(m, 1)
        m:Hide()
        return
    end
    m:Show()
    if m.__npc ~= npc or m.__disp ~= disp then
        m.__npc, m.__disp = npc, disp
        ApplyModel(m, npc, disp)
        M.BossModelPose(m)
        M.BossModelLateCheck(m, npc, disp)
    end
end

function M.SyncSide()
    local frame = M.SideHost
    if not (frame and frame:IsShown()) then frame = M.frame end
    if not frame then return end
    M.SyncBossModel()
    if not (frame.__listReady and frame.__blocksReady and frame.__rowsReady) then return end
    local id = M.curId
    local bosses = M.BossesFor(id)
    local MW = ns.MapWorldModule
    local inTask = M.sideTask and (MW and MW.view == frame)
    frame.side:SetShown(not inTask)

    if M.detailEn then
        local zh, items
        for i = 1, #(bosses or {}) do
            if bosses[i].en == M.detailEn then
                zh = bosses[i].zh
                items = bosses[i].items
                break
            end
        end
        if not zh then M.detailEn = nil end
        if zh then
            frame.listScroll:Hide()
            frame.detScroll:Show()
            frame.detBack:Show()
            frame.detName:SetText(zh)
            frame.detName:ClearAllPoints()
            frame.detName:SetPoint("TOPLEFT", frame.detChild, "TOPLEFT", 0, -1)
            frame.detName:SetWidth(frame.innerW - 90)

            local rowW = frame.detChildW or (frame.innerW - M.BLK_PAD * 2)
            local closed = M.CardClosed()

            for _i = 1, #(items or {}) do
                local iid = items[_i][1]
                local _, ok = DG.ItemName(iid)
                if not ok then DG.RequestItem(iid) end
            end

            local nLoot = 0
            for _i = 1, #(items or {}) do
                if nLoot >= M.MAX_LOOT then break end
                nLoot = nLoot + 1
            end

            local sk = M.SkillsFor(id, M.detailEn)
            local nSk = 0
            for _i = 1, #(sk or {}) do
                if nSk >= M.MAX_SKILL then break end
                nSk = nSk + 1
            end
            local srow = {}
            for i = 1, nSk do
                local r = frame.skillRows[i]
                local nm = sk[i][1] or ""
                local ds = sk[i][2] or ""
                local sid = sk[i][3]
                local sidN = (type(sid) == "number") and sid or nil
                local slug = (type(sid) == "string" and sid ~= "") and sid or sk[i][4]
                local fbIcon = (type(slug) == "string" and slug ~= "")
                    and ("Interface\\Icons\\" .. slug) or nil
                local cn, ic, cd = M.SpellRowFor(sidN, nm, ds ~= "" and ds or nil, fbIcon)
                if sidN and (cn == nil or cn == "") then cn = "法术 #" .. sidN end
                r.__sid = sidN
                r.fs:SetText(cn or "")
                r.ds:SetText(cd or "")
                r.ds:SetShown(type(cd) == "string" and cd ~= "")
                local nh = r.fs:GetStringHeight()
                local dh = r.ds:GetStringHeight()
                local rh = math.max(M.CARD_ICON,
                    (type(nh) == "number" and nh or 18)
                    + ((type(cd) == "string" and cd ~= "")
                        and ((type(dh) == "number" and dh or 15) + 2) or 0))
                srow[i] = { ic = ic, h = rh }
            end

            local guide = M.GuideFor(id, M.detailEn)
            local hasGuide = (type(guide) == "string" and guide ~= "")
            local showGd = hasGuide or (nSk == 0)
            frame.detGd:SetText(hasGuide and guide or L["攻略待补充"])
            local gh = frame.detGd:GetStringHeight()
            local gdTextH = (type(gh) == "number") and gh or 18

            local ltContentH = (nLoot > 0) and (nLoot * M.CARD_H + (nLoot - 1) * M.ROW_GAP) or 18
            local skContentH = 0
            for i = 1, nSk do
                skContentH = skContentH + srow[i].h
                if i < nSk then skContentH = skContentH + M.ROW_GAP end
            end
            local ltH = closed.loot and M.BLK_MIN_H or (M.BLK_HDR + ltContentH + M.BLK_PAD)
            local skH = closed.skill and M.BLK_MIN_H or (M.BLK_HDR + skContentH + M.BLK_PAD)
            local gdH = closed.guide and M.BLK_MIN_H or (M.BLK_HDR + gdTextH + M.BLK_PAD)

            local y = -26
            local by
            local blkLoot = frame.blkLoot
            blkLoot:ClearAllPoints()
            blkLoot:SetPoint("TOPLEFT", frame.detChild, "TOPLEFT", 0, y)
            blkLoot:SetSize(frame.innerW, ltH)
            blkLoot:Show()
            LayoutCardHead(blkLoot, frame.detLtTtl, closed.loot)
            frame.detLtCnt:ClearAllPoints()
            frame.detLtCnt:SetPoint("TOPRIGHT", blkLoot, "TOPRIGHT", -M.BLK_PAD, -(M.BLK_TITLE_TOP + 1))
            frame.detLtCnt:SetText((L["%d 件"] or "%d 件"):format(#(items or {})))
            by = -M.BLK_HDR
            for i = 1, (closed.loot and 0 or nLoot) do
                layoutLootRow(frame.lootRows[i], items[i], by, rowW)
                by = by - (M.CARD_H + M.ROW_GAP)
            end
            for i = (closed.loot and 1 or nLoot + 1), M.MAX_LOOT do frame.lootRows[i]:Hide() end
            frame.detLtNote:SetShown(nLoot == 0 and not closed.loot)
            frame.detLtNote:ClearAllPoints()
            frame.detLtNote:SetPoint("TOPLEFT", blkLoot, "TOPLEFT", M.BLK_PAD, by)
            y = y - ltH - M.BLK_GAP

            local blkSkill = frame.blkSkill
            if nSk > 0 then
                blkSkill:ClearAllPoints()
                blkSkill:SetPoint("TOPLEFT", frame.detChild, "TOPLEFT", 0, y)
                blkSkill:SetSize(frame.innerW, skH)
                blkSkill:Show()
                LayoutCardHead(blkSkill, frame.detSkTtl, closed.skill)
                by = -M.BLK_HDR
                for i = 1, (closed.skill and 0 or nSk) do
                    local r = frame.skillRows[i]
                    if srow[i].ic then
                        r.icon:SetTexture(srow[i].ic)
                        r.icon:Show()
                        if ns.hui and ns.hui.SetIconRing then ns.hui.SetIconRing(r.icon, nil) end
                    else
                        r.icon:Hide()
                        if ns.hui and ns.hui.SetIconRing then ns.hui.SetIconRing(r.icon, nil) end
                    end
                    r:ClearAllPoints()
                    r:SetPoint("TOPLEFT", blkSkill, "TOPLEFT", M.BLK_PAD + 6, by)
                    r:SetHeight(srow[i].h)
                    r:Show()
                    by = by - srow[i].h - M.ROW_GAP
                end
                y = y - skH - M.BLK_GAP
            else
                blkSkill:Hide()
            end
            for i = (closed.skill and 1 or nSk + 1), M.MAX_SKILL do
                frame.skillRows[i].__sid = nil
                frame.skillRows[i]:Hide()
            end

            local blkGuide = frame.blkGuide
            if showGd then
                blkGuide:ClearAllPoints()
                blkGuide:SetPoint("TOPLEFT", frame.detChild, "TOPLEFT", 0, y)
                blkGuide:SetSize(frame.innerW, gdH)
                blkGuide:Show()
                LayoutCardHead(blkGuide, frame.detGdTtl, closed.guide)
                if closed.guide then
                    frame.detGd:Hide()
                else
                    frame.detGd:ClearAllPoints()
                    frame.detGd:SetPoint("TOPLEFT", blkGuide, "TOPLEFT", M.BLK_PAD, -M.BLK_HDR)
                    frame.detGd:Show()
                end
                y = y - gdH - M.BLK_GAP
            else
                blkGuide:Hide()
                frame.detGd:Hide()
            end
            y = y + M.BLK_GAP

            frame.detChild:SetHeight(math.max(30, -y + 10))
            frame.detScroll:SetVerticalScroll(0)
            if frame.listBar then frame.listBar:Hide() end
            M.SyncScrollBar(frame.detScroll)
            return
        end
    end

    frame.detScroll:Hide()
    frame.listScroll:Show()
    local n = 0
    local y = -26
    for i = 1, #(bosses or {}) do
        if n >= M.MAX_LIST then break end
        n = n + 1
        local r = frame.listRows[n]
        r.__en = bosses[i].en
        r.fs:SetText(bosses[i].zh or bosses[i].en)
        r.fs:ClearAllPoints()
        r.fs:SetPoint("LEFT", r.__av, "RIGHT", 6, 0)
        if r.rare then
            if bosses[i].rare then
                local cw = r.rare:GetWidth() or 0
                r.fs:SetPoint("RIGHT", r, "RIGHT", -12 - cw, 0)
                r.rare:Show()
            else
                r.fs:SetPoint("RIGHT", r, "RIGHT", -6, 0)
                r.rare:Hide()
            end
        else
            r.fs:SetPoint("RIGHT", r, "RIGHT", -6, 0)
        end
        local cr, cg, cb = M.BossColor(id, bosses[i].en)
        bpPaint(r.__av, bpDisp(id, bosses[i].en), cr, cg, cb, 32)
        for _, t in ipairs(r.__borderPieces or {}) do t:SetVertexColor(cr, cg, cb) end
        PiecesSetShown(r.__hl, false)
        r:ClearAllPoints()
        r:SetPoint("TOPLEFT", frame.listChild, "TOPLEFT", 0, y)
        r:Show()
        y = y - (M.LIST_H + M.LIST_GAP)
    end
    for i = n + 1, M.MAX_LIST do frame.listRows[i]:Hide() end
    local det = M.DetailOf(id)
    frame.listNote:SetShown(n == 0 and not (det and det.noList))
    frame.listChild:SetHeight(math.max(30, -y + 8))
    frame.listScroll:SetVerticalScroll(0)
    if frame.detBar then frame.detBar:Hide() end
    M.SyncScrollBar(frame.listScroll)
end

function M.BossLayer(id, en)
    local pts = M.PosFor(id, en)
    if not pts then return nil end
    local cur = M.curLayer
    local first
    for i = 1, #pts do
        local idx = M.LayerOf(id, pts[i][3] or 1)
        if idx then
            if cur and idx == cur then return idx end
            first = first or idx
        end
    end
    return first
end

function M.Select(en)
    local id = M.curId
    if not (id and en) then return end
    local bosses = M.BossesFor(id)
    local hit = false
    for i = 1, #(bosses or {}) do
        if bosses[i].en == en then hit = true break end
    end
    if not hit then return end
    if M.detailEn == en then en = nil end
    M.detailEn = en
    if en then
        local idx = M.BossLayer(id, en)
        if idx and idx ~= M.curLayer then
            if M.frame and M.frame:IsShown() then
                M.SetLayer(idx)
            else
                M.curLayer = idx
            end
        end
    end
    M.SyncPins()
    M.SyncSide()
end

function M.ShowList()
    M.detailEn = nil
    M.SyncPins()
    M.SyncSide()
end

function M.OnItemData(itemID)
    local frame = M.SideHost or M.frame
    if not (frame and frame:IsShown() and frame.__listReady and frame.__blocksReady and frame.__rowsReady) then return end
    if not (M.detailEn and M.curId) then return end
    if type(itemID) ~= "number" then return end
    local bosses = M.BossesFor(M.curId)
    local hit
    for i = 1, #(bosses or {}) do
        if bosses[i].en == M.detailEn then
            local its = bosses[i].items
            for k = 1, #(its or {}) do
                if its[k][1] == itemID then hit = true break end
            end
            break
        end
    end
    if not hit then return end
    if M.__oidT then return end
    if type(C_Timer) ~= "table" or type(C_Timer.After) ~= "function" then
        M.SyncSide()
        return
    end
    M.__oidT = C_Timer.After(0.25, function()
        M.__oidT = nil
        if M.frame and M.frame:IsShown() and M.detailEn then M.SyncSide() end
    end)
end

function M.PaintArea(id, fn, cw, ch)
    local frame = M.frame
    local tex = frame and frame.areaTex
    if not tex then return end
    local row = id and ns.RouteArea and ns.RouteArea[id]
    local path = row and fn and row[fn]
    if not path then
        tex:Hide()
        return
    end
    tex:SetTexture(path)
    tex:SetTexCoord(0, M.ART_W / M.OVL_W, 0, M.ART_H / M.OVL_H)
    tex:ClearAllPoints()
    tex:SetPoint("TOPLEFT", frame.canvas, "TOPLEFT", 0, 0)
    tex:SetSize(cw, ch)
    tex:Show()
end

function M.Paint(d)
    local frame = M.frame
    if not frame then return end
    M.curD = d
    local id = d and d.id
    local layers = M.LayersFor(id)
    local leftW, cw, ch, cx, cy = M.Box()
    frame.pinW, frame.pinH = cw, ch

    if M.curId ~= id then
        M.curId, M.curLayer, M.detailEn = id, 1, nil
    end

    frame.canvas:ClearAllPoints()
    frame.canvas:SetPoint("TOPLEFT", frame, "TOPLEFT", cx, -cy)
    frame.canvas:SetSize(cw, ch)
    frame.pins:ClearAllPoints()
    frame.pins:SetPoint("TOPLEFT", frame, "TOPLEFT", cx, -cy)
    frame.pins:SetSize(cw, ch)
    frame.route:ClearAllPoints()
    frame.route:SetPoint("TOPLEFT", frame, "TOPLEFT", cx, -cy)
    frame.route:SetSize(cw, ch)
    frame.bar:ClearAllPoints()
    frame.bar:SetPoint("RIGHT", frame.hdrCard, "RIGHT", -M.SIDE_PAD, 0)
    frame.bossPinBtn:ClearAllPoints()
    frame.bossPinBtn:SetPoint("LEFT", frame.hdrCard, "LEFT", M.SIDE_PAD, 0)
    frame.routePinBtn:ClearAllPoints()
    frame.routePinBtn:SetPoint("LEFT", frame.bossPinBtn, "RIGHT", M.PIN_BTN_GAP, 0)

    if not layers then
        M.curLayer = nil
        for n = 1, M.N do frame.tiles[n]:Hide() end
        local cpath, cv1 = M.CustomFor(id)
        if cpath then
            frame.canvas:Show()
            frame.customTex:SetTexture(cpath)
            frame.customTex:SetTexCoord(0, 1, 0, cv1)
            frame.customTex:ClearAllPoints()
            frame.customTex:SetPoint("TOPLEFT", frame.canvas, "TOPLEFT", 0, 0)
            frame.customTex:SetSize(cw, ch)
            frame.customTex:Show()
            frame.empty:Hide()
        else
            frame.canvas:Hide()
            frame.customTex:Hide()
            frame.empty:Show()
        end
        frame.pins:Hide()
        M.PaintArea(id, M.FloorNumAt(id, 1), cw, ch)
        if cpath then
            M.SyncRoute(id, M.FloorNumAt(id, 1), cw, ch)
        else
            frame.route:Hide()
        end
        M.SyncBar(nil, nil)
        M.SyncPins()
        M.SyncSide()
        return
    end
    frame.empty:Hide()
    frame.customTex:Hide()

    local idx = M.curLayer or 1
    if idx < 1 or idx > #layers then idx = 1 end
    M.curLayer = idx

    frame.canvas:Show()
    local lay = M.Layout(cw, ch)
    local path = M.PathAt(id, idx)
    local fixRow = id and TILE_FIX[id]
    local fixTile = fixRow and fixRow[idx]
    local cpath, cv1 = M.CustomFloorFor(id, idx)
    for n = 1, M.N do frame.tiles[n]:Hide() end
    if cpath then
        frame.customTex:SetTexture(cpath)
        frame.customTex:SetTexCoord(0, 1, 0, cv1)
        frame.customTex:ClearAllPoints()
        frame.customTex:SetPoint("TOPLEFT", frame.canvas, "TOPLEFT", 0, 0)
        frame.customTex:SetSize(cw, ch)
        frame.customTex:Show()
    else
        for _, p in ipairs(lay) do
            local t = frame.tiles[p.n]
            t:SetTexture((fixTile and fixTile[p.n]) or (path .. p.n))
            t:SetTexCoord(p.u0, p.u1, p.v0, p.v1)
            t:ClearAllPoints()
            t:SetPoint("TOPLEFT", frame.canvas, "TOPLEFT", p.x, -p.y)
            t:SetSize(p.w, p.h)
            t:Show()
        end
    end
    M.PaintArea(id, M.FloorNumAt(id, idx), cw, ch)
    M.SyncRoute(id, M.FloorNumAt(id, idx), cw, ch)
    M.SyncPins()
    M.SyncBar(layers, idx)
    M.SyncSide()
end

local wpins, wpinPool = {}, {}
local wpStaticRows
local provider

local function wpRelease()
    for i = #wpins, 1, -1 do
        local p = wpins[i]
        p:Hide()
        p:ClearAllPoints()
        wpins[i] = nil
        wpinPool[#wpinPool + 1] = p
    end
end

local function wpAlive(mapID)
    if not mapID then return false end
    if not (C_Map and C_Map.GetMapInfo) then return true end
    local ok, mi = pcall(C_Map.GetMapInfo, mapID)
    return ok and mi ~= nil
end

local function wpTopParent(mapID)
    local guard = 0
    while mapID and guard < 8 do
        guard = guard + 1
        if not (C_Map and C_Map.GetMapInfo) then return mapID end
        local ok, info = pcall(C_Map.GetMapInfo, mapID)
        if not ok or not info or not info.parentMapID or info.parentMapID <= 0 then
            return mapID
        end
        mapID = info.parentMapID
    end
    return mapID
end

local function wpProject(uiMap, x, y, disp)
    if not uiMap or not disp then return nil end
    if uiMap == disp then return x, y end
    if wpTopParent(uiMap) ~= wpTopParent(disp) then return nil end
    if not (C_Map and C_Map.GetMapRectOnMap) then return nil end
    local ok, left, right, top, bottom = pcall(C_Map.GetMapRectOnMap, uiMap, disp)
    if not ok or not left or right == left then return nil end
    return left + x * (right - left), top + y * (bottom - top)
end

local function wpStatic()
    if wpStaticRows then return wpStaticRows end
    local rows, qnpc, qdk = {}, {}, {}
    if type(ns.DungeonQuests) == "table" then
        for dk, arr in pairs(ns.DungeonQuests) do
            if type(arr) == "table" then
                for i = 1, #arr do
                    local q = arr[i]
                    if type(q) == "table" and q[1] then
                        qnpc[q[1]] = q[16]
                        qdk[q[1]] = dk
                        rows[#rows + 1] = q
                    end
                end
            end
        end
    end
    wpStaticRows = { rows = rows, qnpc = qnpc, qdk = qdk }
    return wpStaticRows
end

local wpDnCache
local function wpDName(dk)
    if not dk then return nil end
    if wpDnCache == nil then
        wpDnCache = {}
        local list = ns.DungeonData and ns.DungeonData.dungeons
        if type(list) == "table" then
            for _, d in ipairs(list) do
                if type(d) == "table" and d.id then wpDnCache[d.id] = d.name end
            end
        end
    end
    return wpDnCache[dk]
end

local function wpPinAcquire(canvas)
    local p = wpinPool[#wpinPool]
    if p then wpinPool[#wpinPool] = nil else
        p = CreateFrame("Button", nil, canvas)
        p:SetSize(16, 16)
        p:EnableMouse(true)
        p:RegisterForClicks("LeftButtonUp")
        p.tex = p:CreateTexture(nil, "OVERLAY")
        p.tex:SetAllPoints()
        p:SetScript("OnEnter", function(self)
            if not GameTooltip or type(self.__qs) ~= "table" then return end
            GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
            local st = wpStatic()
            for i = 1, #self.__qs do
                local it = self.__qs[i]
                local nm, nmOk
                if DG.QuestName then nm, nmOk = DG.QuestName(it.qid) end
                if not nmOk then DG.RequestQuest(it.qid) end
                nm = nm or tostring(it.qid)
                local tag, sub
                if it.blocked then
                    tag = "|cffc8c8c8[" .. L["未解锁"] .. "]|r"
                    DG.RequestQuest(it.pre)
                    sub = format(L["需先完成：%s"], tostring(DG.QuestName and DG.QuestName(it.pre) or it.pre))
                elseif it.blocking then
                    tag = "|cff8ca6ff[" .. L["前置"] .. "]|r"
                    DG.RequestQuest(it.blocking)
                    sub = format(L["完成后解锁：%s"], tostring(DG.QuestName and DG.QuestName(it.blocking) or it.blocking))
                else
                    tag = "|cffffd100[" .. L["可接"] .. "]|r"
                end
                GameTooltip:AddLine(tag .. " " .. nm, 0.94, 0.94, 0.94, true)
                if sub then
                    GameTooltip:AddLine(sub, 0.91, 0.71, 0.35, true)
                end
                local dn = wpDName(st.qdk[it.qid])
                if dn then
                    GameTooltip:AddLine(dn .. " " .. L["副本任务"], 0.66, 0.66, 0.66, true)
                end
            end
            GameTooltip:AddLine((L["点击进入[无限副本手册]任务详情"] or ""):gsub("%[(.-)%]", "|cffffd100[%1]|r"), 0.62, 0.62, 0.62, true)
            local nl = GameTooltip.NumLines and GameTooltip:NumLines() or 0
            local bf, bs, bfl
            for i = 2, nl do
                local f = _G["GameTooltipTextLeft" .. i]
                if f and f.GetFont then
                    local f2, s2, fl2 = f:GetFont()
                    if f2 and s2 then bf, bs, bfl = f2, s2, fl2 break end
                end
            end
            if bf then
                for i = 1, nl do
                    local f = _G["GameTooltipTextLeft" .. i]
                    if f then f:SetFont(bf, bs, bfl) end
                end
            end
            GameTooltip:Show()
        end)
        p:SetScript("OnLeave", function()
            if GameTooltip then GameTooltip:Hide() end
        end)
        p:SetScript("OnClick", function(self)
            local qs = self.__qs
            if type(qs) ~= "table" or #qs == 0 then return end
            local qid
            for i = 1, #qs do
                local it = qs[i]
                if not it.blocked and not it.blocking then qid = it.qid break end
            end
            qid = qid or qs[1].qid
            local dk = wpStatic().qdk[qid]
            if not dk then
                for i = 1, #qs do
                    local it = qs[i]
                    if it.blocking then
                        local dk2 = wpStatic().qdk[it.blocking]
                        if dk2 then
                            qid, dk = it.blocking, dk2
                            break
                        end
                    end
                end
            end
            if not dk then return end
            U.dungeonQuestSel = qid
            if ns.ShowDungeonDetail then ns.ShowDungeonDetail(dk) end
            if U.SetDungeonTab then U:SetDungeonTab("quest") end
            ns.PlaySound(1)
        end)
    end
    p:SetParent(canvas)
    p.tex:SetDesaturated(false)
    p.tex:SetAlpha(1)
    return p
end

local WP_DEF = { size = 32, world = false, scope = { lv = true, reco = true, enter = true, all = false, grey = true } }

local function wpCfg()
    local db = ns.DB and ns.DB()
    if not db then return WP_DEF end
    db.dungeon = db.dungeon or {}
    local c = db.dungeon.mapQuestPinsCfg
    if type(c) ~= "table" then
        c = {}
        db.dungeon.mapQuestPinsCfg = c
    end
    if c.size == nil then c.size = WP_DEF.size end
    if c.world == nil then c.world = WP_DEF.world end
    if type(c.scope) ~= "table" then c.scope = {} end
    for k, v in pairs(WP_DEF.scope) do
        if c.scope[k] == nil then c.scope[k] = v end
    end
    return c
end

local wpDlvCache
local function wpDlv()
    if wpDlvCache then return wpDlvCache end
    local m = {}
    local dd = ns.DungeonData
    local list = dd and dd.dungeons
    if type(list) == "table" then
        for _, d in ipairs(list) do
            if type(d) == "table" and d.id then
                m[d.id] = { d.levelMin or 0, d.levelMax or 999 }
            end
        end
    end
    wpDlvCache = m
    return m
end

function M.SyncWorldQuestPins()
    if not (WorldMapFrame and WorldMapFrame.IsShown and WorldMapFrame:IsShown()
            and WorldMapFrame.GetMapID) then return end
    if not M.QuestPinsOn() then
        wpRelease()
        return
    end
    if not (DG.QuestState and type(ns.NPCLoc) == "table") then return end
    local okID, disp = pcall(WorldMapFrame.GetMapID, WorldMapFrame)
    if not okID or not disp or not wpAlive(disp) then return end
    local okC, canvas = pcall(WorldMapFrame.GetCanvas, WorldMapFrame)
    if not okC or not canvas then return end
    if canvas.GetWidth and (canvas:GetWidth() or 0) <= 1 then return end
    wpRelease()
    local okW, w = pcall(canvas.GetWidth, canvas)
    local okH, h = pcall(canvas.GetHeight, canvas)
    w = (okW and type(w) == "number" and w > 0 and w) or 700
    h = (okH and type(h) == "number" and h > 0 and h) or 500
    local scale = 1
    local sc = WorldMapFrame.ScrollContainer
    if sc and sc.GetCanvasScale then
        local okS, v = pcall(sc.GetCanvasScale, sc)
        if okS and type(v) == "number" and v > 0 then scale = v end
    end
    local size = wpCfg().size or 32
    local cs = canvas.GetScale and canvas:GetScale() or 1
    local k = (cs and cs > 0) and 1 / cs or 1
    local lvl
    if WorldMapFrame.GetPinFrameLevelsManager then
        local okL, mgr = pcall(WorldMapFrame.GetPinFrameLevelsManager, WorldMapFrame)
        if okL and mgr and mgr.GetValidFrameLevel then
            local ok2, lv = pcall(mgr.GetValidFrameLevel, mgr, "PIN_FRAME_LEVEL_DUNGEON_ENTRANCE")
            if ok2 and lv then lvl = lv end
        end
    end
    local data = wpStatic()
    local cfg = wpCfg()
    local sc2 = cfg.scope
    local lv = (UnitLevel and UnitLevel("player")) or 0
    local side = DG.PlayerSide and DG.PlayerSide() or nil
    local nOn = (sc2.lv and 1 or 0) + (sc2.reco and 1 or 0) + (sc2.enter and 1 or 0)
    local useAll = sc2.all == true
    local useGrey = sc2.grey == true
    local useLv, useReco, useEnter
    if useAll then
        useLv, useReco, useEnter = false, false, false
    elseif nOn == 0 then
        useLv, useReco, useEnter = false, true, false
    else
        useLv, useReco, useEnter = sc2.lv == true, sc2.reco == true, sc2.enter == true
    end
    local dlv = wpDlv()
    local pcls = (UnitClass and UnitClass("player")) or nil
    local function wpGrey(qlv)
        if GetQuestDifficultyColor then
            local ok, c = pcall(GetQuestDifficultyColor, qlv)
            if ok and c and c.r then
                if math.abs(c.r - c.g) < 0.01 and math.abs(c.g - c.b) < 0.01 then return true end
                return false
            end
        end
        if lv <= 5 then return false end
        local g
        if lv <= 39 then
            g = lv - 5 - floor(lv / 10)
        elseif lv <= 59 then
            g = lv - 8 - floor((lv - 40) / 5)
        else
            g = lv - 12
        end
        return qlv <= g
    end
    local function qHit(q)
        if side and q[2] and q[2] ~= side then return false end
        if pcls and q[15] and q[15] ~= pcls then return false end
        local r = data.qdk[q[1]] and dlv[data.qdk[q[1]]]
        local qlv = q[3]
        if qlv == nil and r then qlv = r[1] end
        if useGrey then
            local gt
            if type(q[13]) == "table" then
                for _, d in ipairs(q[13]) do
                    if d[2] == 5 and type(d[1]) == "number" then gt = d[1] break end
                end
            end
            if gt then
                if lv >= gt then return false end
            else
                local glv = DG.QuestLevel and DG.QuestLevel(q[1]) or nil
                if glv == nil then glv = q[4] end
                if glv == nil then glv = qlv end
                if glv and wpGrey(glv) then return false end
            end
        end
        if useAll then return true end
        if useLv then
            if qlv ~= nil and qlv <= lv then return true end
        end
        if useReco and r and lv >= r[1] and lv <= r[2] then return true end
        if useEnter and r and lv >= r[1] then return true end
        return false
    end
    local function segOk(seg)
        if (DG.QuestState and DG.QuestState(seg)) ~= "todo" then return false end
        local sq = DG.QuestRowByID and DG.QuestRowByID(seg)
        local qlv
        if sq then
            if side and sq[2] and sq[2] ~= side then return false end
            if pcls and sq[15] and sq[15] ~= pcls then return false end
            local sp = sq[9]
            if type(sp) == "table" then
                for _, ps in ipairs(sp) do
                    if type(ps) == "number" and (DG.QuestState and DG.QuestState(ps)) ~= "done" then
                        return false
                    end
                end
            end
            qlv = sq[3]
        else
            local ex = ns.DungeonQuestPreExtra and ns.DungeonQuestPreExtra[seg]
            if ex then
                if ex.lv then qlv = ex.lv end
                for i = 1, #ex do
                    local ps = ex[i]
                    if type(ps) == "number" and (DG.QuestState and DG.QuestState(ps)) ~= "done" then
                        return false
                    end
                end
            end
        end
        if qlv == nil then
            local rr = data.qdk[seg] and dlv[data.qdk[seg]]
            if rr then qlv = rr[1] end
        end
        if qlv and lv < qlv then return false end
        return true
    end
    local lockedPre, preBlock = {}, {}
    for i = 1, #data.rows do
        local q = data.rows[i]
        if qHit(q) then
            local pre = q[9]
            if type(pre) == "table" then
                for _, seg in ipairs(pre) do
                    if DG.QuestState(seg) ~= "done" then
                        lockedPre[q[1]] = seg
                        preBlock[seg] = q[1]
                        break
                    end
                end
            end
        end
    end
    local byNpc = {}
    for i = 1, #data.rows do
        local q = data.rows[i]
        if qHit(q) and DG.QuestState(q[1]) == "todo" and q[16] then
            local loc = ns.NPCLoc[q[16]]
            if type(loc) == "table" and loc[1] then
                local e = byNpc[q[16]]
                if not e then
                    e = { nid = q[16], loc = loc, qs = {} }
                    byNpc[q[16]] = e
                end
                e.qs[#e.qs + 1] = {
                    qid = q[1],
                    blocked = lockedPre[q[1]],
                    pre = lockedPre[q[1]],
                    blocking = preBlock[q[1]],
                }
            end
        end
    end
    for qid, seg in pairs(lockedPre) do
        if segOk(seg) then
            local nid = data.qnpc[seg] or (ns.QuestPreNpcID and ns.QuestPreNpcID[seg])
            local loc = nid and ns.NPCLoc[nid]
            if type(loc) == "table" and loc[1] then
            local e = byNpc[nid]
            if not e then
                e = { nid = nid, loc = loc, qs = {} }
                byNpc[nid] = e
            end
            local seen
            for k = 1, #e.qs do
                if e.qs[k].qid == seg then seen = true break end
            end
            if not seen then
                e.qs[#e.qs + 1] = { qid = seg, blocking = qid }
            end
            end
        end
    end
    for _, e in pairs(byNpc) do
        local x, y
        if cfg.world == true or e.loc[1] == disp then
            x, y = wpProject(e.loc[1], (e.loc[2] or 0) / 100, (e.loc[3] or 0) / 100, disp)
        end
        if x then
            local hasReady, hasPre, hasLocked = false, false, false
            for k = 1, #e.qs do
                local it = e.qs[k]
                if it.blocking then hasPre = true
                elseif it.blocked then hasLocked = true
                else hasReady = true end
            end
            local p = wpPinAcquire(canvas)
            p.__qs = e.qs
            p.__zone = e.loc[4]
            p.tex:SetTexture((hasReady and M.PIN_QUEST_READY_TEX)
                or (hasPre and M.PIN_QUEST_PRE_TEX)
                or M.PIN_QUEST_LOCKED_TEX)
            p.tex:SetVertexColor(1, 1, 1)
            p:SetSize(size, size)
            p:SetScale(k)
            p:ClearAllPoints()
            p:SetPoint("CENTER", canvas, "TOPLEFT", w * x / k, -h * y / k)
            if lvl then
                p:SetFrameStrata(canvas:GetFrameStrata())
                p:SetFrameLevel(lvl)
            else
                p:SetFrameLevel(canvas:GetFrameLevel() + 20)
            end
            p:Show()
            wpins[#wpins + 1] = p
        end
    end
end

local Provider = {}
function Provider:RemoveAllData() wpRelease() end
function Provider:RefreshAllData() M.SyncWorldQuestPins() end
function Provider:OnHide() wpRelease() end
function Provider:OnCanvasScaleChanged() M.SyncWorldQuestPins() end
function Provider:OnCanvasSizeChanged() M.SyncWorldQuestPins() end

local function wpInit()
    if not WorldMapFrame then return end
    if WorldMapFrame.AddDataProvider and MapCanvasDataProviderMixin and not provider then
        local okP = pcall(function()
            provider = CreateFromMixins(MapCanvasDataProviderMixin, Provider)
            WorldMapFrame:AddDataProvider(provider)
        end)
        if okP and provider then return end
        provider = nil
    end
    if hooksecurefunc then
        pcall(hooksecurefunc, WorldMapFrame, "OnMapChanged", M.SyncWorldQuestPins)
        if WorldMapFrame.OnCanvasScaleChanged then
            pcall(hooksecurefunc, WorldMapFrame, "OnCanvasScaleChanged", M.SyncWorldQuestPins)
        end
    end
    if WorldMapFrame.HookScript then
        pcall(WorldMapFrame.HookScript, WorldMapFrame, "OnShow", M.SyncWorldQuestPins)
    end
end

local wpBoot = CreateFrame("Frame")
pcall(wpBoot.RegisterEvent, wpBoot, "PLAYER_LOGIN")
wpBoot:SetScript("OnEvent", function()
    if C_Timer and C_Timer.After then C_Timer.After(0, wpInit) else wpInit() end
end)

local wpEv = CreateFrame("Frame")
pcall(wpEv.RegisterEvent, wpEv, "QUEST_LOG_UPDATE")
wpEv:SetScript("OnEvent", function()
    if WorldMapFrame and WorldMapFrame.IsShown and WorldMapFrame:IsShown() then
        M.SyncWorldQuestPins()
    end
end)

local wpPanel

local WP_TXT  = { 0.88, 0.88, 0.88 }
local WP_WHT  = { 0.95, 0.96, 0.98 }

local function wpSetFs(parent, size, col)
    local fs = parent:CreateFontString(nil, "OVERLAY")
    local flags = (ns.hui and ns.hui.FontFlags and ns.hui.FontFlags("OUTLINE")) or "OUTLINE"
    fs:SetFont(ns.FONT, size, flags)
    fs:SetTextColor(col[1], col[2], col[3])
    return fs
end

local function wpMkBtn(parent, text, w)
    local b = CreateFrame("Button", nil, parent)
    b:SetSize(w or 46, 24)
    b:EnableMouse(true)
    if ns.hui and ns.hui.BuildRoundedBG and ns.hui.BuildRoundBorder then
        b.fills = ns.hui.BuildRoundedBG(b, 8, { 1, 1, 1, 0.06 }, "both", false, nil, true)
        b.edges = ns.hui.BuildRoundBorder(b, 8, { 0.40, 0.43, 0.50 })
    else
        b.bg = b:CreateTexture(nil, "BACKGROUND")
        b.bg:SetAllPoints()
        b.bg:SetColorTexture(1, 1, 1, 0.06)
    end
    local fs = wpSetFs(b, 14, WP_TXT)
    fs:SetJustifyH("CENTER")
    fs:SetAllPoints()
    fs:SetText(text)
    b:SetFontString(fs)
    b:SetScript("OnEnter", function(self)
        for _, t in ipairs(self.fills or {}) do t:SetAlpha(0.14) end
        if self.bg then self.bg:SetAlpha(0.14) end
    end)
    b:SetScript("OnLeave", function(self)
        for _, t in ipairs(self.fills or {}) do t:SetAlpha(0.06) end
        if self.bg then self.bg:SetAlpha(0.06) end
    end)
    return b
end

local function wpReanchor()
    if ns.QuickBar and ns.QuickBar.Reanchor then pcall(ns.QuickBar.Reanchor, ns.QuickBar) end
end

local function wpToggleRow(content, y, label, get, set)
    local tg = CreateFrame("CheckButton", nil, content)
    tg:SetSize(36, 20)
    tg:EnableMouse(true)
    if ns.hui and ns.hui.ReskinToggle then ns.hui.ReskinToggle(tg) end
    tg.label = wpSetFs(content, 14, WP_TXT)
    tg.label:SetJustifyH("LEFT")
    tg.label:SetPoint("TOPLEFT", content, "TOPLEFT", 0, y - 1)
    tg.label:SetText(label)
    tg:SetPoint("TOPRIGHT", content, "TOPRIGHT", 0, y + 2)
    tg:SetChecked(get() and true or false)
    tg:SetScript("OnClick", function(self)
        set(not (get() and true))
        self:SetChecked(get() and true or false)
        ns.PlaySound(1)
        M.SyncWorldQuestPins()
    end)
    tg.sync = function()
        tg:SetChecked(get() and true or false)
    end
    tg:sync()
    return tg
end

local function wpStepperRow(content, y, label, minv, maxv, step, get, set, fmt)
    local lab = wpSetFs(content, 14, WP_TXT)
    lab:SetJustifyH("LEFT")
    lab:SetPoint("TOPLEFT", content, "TOPLEFT", 0, y - 5)
    lab:SetText(label)
    local plus = wpMkBtn(content, "+", 24)
    plus:SetPoint("TOPRIGHT", content, "TOPRIGHT", 0, y)
    local minus = wpMkBtn(content, "-", 24)
    minus:SetPoint("TOPRIGHT", plus, "TOPLEFT", -4, 0)
    local val = wpSetFs(content, 14, WP_TXT)
    val:SetJustifyH("RIGHT")
    val:SetPoint("RIGHT", minus, "LEFT", -6, 0)
    val:SetPoint("LEFT", lab, "RIGHT", 6, 0)
    local function clamp(v)
        v = math.floor(v + 0.5)
        return math.max(minv, math.min(maxv, v))
    end
    local function bump(dir)
        set(clamp(get() + dir * step))
        val:SetText(fmt(get()))
        M.SyncWorldQuestPins()
    end
    plus:SetScript("OnClick", function() bump(1) end)
    minus:SetScript("OnClick", function() bump(-1) end)
    val:SetText(fmt(get()))
    return {
        sync = function() val:SetText(fmt(get())) end,
    }
end

local function wpCreatePanel()
    local host = ns.MainFrame or UIParent
    local f = CreateFrame("Frame", "DFQuestPinSettings", host, "BackdropTemplate")
    f:SetFrameLevel(512)
    f:SetFrameStrata("HIGH")
    f:EnableMouse(true)
    f:SetScript("OnMouseWheel", function() end)
    f:SetWidth(220)
    if host ~= UIParent then
        f:SetPoint("TOPLEFT", host, "TOPRIGHT", 4, 0)
        f:SetPoint("BOTTOMLEFT", host, "BOTTOMRIGHT", 4, 0)
    else
        f:SetPoint("CENTER", UIParent, "CENTER", 0, 0)
        f:SetHeight(390)
    end
    f:Hide()
    f:SetScript("OnHide", function()
        if ns.SyncQuestPinIcon then pcall(ns.SyncQuestPinIcon) end
    end)
    if ns.hui and ns.hui.SkinPopup then ns.hui.SkinPopup(f, 8, "both", ns.hui.layer.L0) end
    if ns.hui and ns.hui.SkinShadow then ns.hui.SkinShadow(f) end
    local title = wpSetFs(f, 16, WP_WHT)
    title:SetPoint("TOPLEFT", f, "TOPLEFT", 12, -8)
    title:SetJustifyH("LEFT")
    title:SetText(L["图钉设置"])
    local syncers = {}
    local resetB = wpMkBtn(f, L["重置"], 56)
    resetB:SetPoint("TOPRIGHT", f, "TOPRIGHT", -12, -6)
    resetB:SetScript("OnClick", function()
        ns.PlaySound(1)
        local db = ns.DB and ns.DB()
        if db and db.dungeon then db.dungeon.mapQuestPinsCfg = nil end
        wpCfg()
        for _, fn in ipairs(syncers) do fn() end
        M.SyncWorldQuestPins()
    end)
    local content = CreateFrame("Frame", nil, f)
    content:SetPoint("TOPLEFT", f, "TOPLEFT", 12, -34)
    content:SetPoint("BOTTOMRIGHT", f, "BOTTOMRIGHT", -12, 12)
    local y = 0
    do
        local row = wpStepperRow(content, y, L["图钉大小"], 16, 64, 4,
            function() return wpCfg().size or 32 end,
            function(v) wpCfg().size = v end,
            function(v) return tostring(v) end)
        syncers[#syncers + 1] = function() row:sync() end
        y = y - 30
    end
    y = y - 8
    do
        local hd = wpSetFs(content, 14, WP_TXT)
        hd:SetJustifyH("LEFT")
        hd:SetPoint("TOPLEFT", content, "TOPLEFT", 0, y)
        hd:SetText(L["显示范围"])
        y = y - 30
    end
    local scopes = {
        { k = "lv",    t = L["按等级能接的"] },
        { k = "reco",  t = L["当前推荐副本"] },
        { k = "enter", t = L["可进入的副本"] },
        { k = "all",   t = L["全部任务"] },
        { k = "grey",  t = L["任务难度灰色不显示"] },
    }
    for _, s in ipairs(scopes) do
        local tg = wpToggleRow(content, y, s.t,
            function() return wpCfg().scope[s.k] == true end,
            function(v) wpCfg().scope[s.k] = v end)
        syncers[#syncers + 1] = function() tg:sync() end
        y = y - 30
    end
    do
        local tg = wpToggleRow(content, y, L["世界地图显示"],
            function() return wpCfg().world == true end,
            function(v) wpCfg().world = v end)
        syncers[#syncers + 1] = function() tg:sync() end
        y = y - 24
    end
    f.syncAll = function()
        for _, fn in ipairs(syncers) do fn() end
    end
    return f
end

function M.QuestPinPanel()
    return (wpPanel and wpPanel.IsShown and wpPanel:IsShown()) and wpPanel or nil
end

function ns.CloseQuestPinSettings()
    if wpPanel and wpPanel.IsShown and wpPanel:IsShown() then
        wpPanel:Hide()
        wpReanchor()
    end
end

function M.ToggleQuestPinPanel()
    if wpPanel and wpPanel.IsShown and wpPanel:IsShown() then
        wpPanel:Hide()
        wpReanchor()
        return
    end
    if not wpPanel then
        wpPanel = wpCreatePanel()
        if ns.QuickBar and ns.QuickBar.HookSettings then
            pcall(ns.QuickBar.HookSettings, ns.QuickBar)
        end
    end
    if ns.CloseSettings then pcall(ns.CloseSettings) end
    if ns.CloseExploreMapSettings then pcall(ns.CloseExploreMapSettings) end
    if ns.LootFilterUI and ns.LootFilterUI.CloseConfig then
        pcall(ns.LootFilterUI.CloseConfig, ns.LootFilterUI)
    end
    if wpPanel.syncAll then wpPanel:syncAll() end
    wpPanel:Show()
    wpReanchor()
    if ns.SyncQuestPinIcon then pcall(ns.SyncQuestPinIcon) end
end

M.FloorName = FloorName
M.PaintBossPin = bpPaint
M.BossPinDisplay = bpDisp
