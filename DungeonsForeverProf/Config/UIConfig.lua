local _, ns = ...
if type(ns) ~= "table" then ns = _G.DF_NS or {} end

local C = {
  TABS = {
    { key = "overview", labelKey = "总览" },
    { key = "trainer", labelKey = "训练师" },
    { key = "recipe", labelKey = "配方" },
    { key = "gather", labelKey = "采集" },
    { key = "leveling", labelKey = "升级" },
    { key = "crate", labelKey = "板条箱" },
    { key = "writ", labelKey = "工匠文书" },
  },
  COLORS = {
    GOLD = { 1, 0.82, 0.0 },
    GREEN = { 0.25, 0.85, 0.35 },
    RED = { 0.9, 0.35, 0.35 },
    GREY = { 0.55, 0.55, 0.55 },
    DIM = { 0.63, 0.63, 0.63 },
    DARKGREY = { 0.30, 0.30, 0.30 },
    WHITE = { 1, 1, 1 },
    TEXT = { 0.88, 0.88, 0.88 },
    LINK_Q = { 0.53, 0.81, 0.98 },
    HELP = { 0.58, 0.64, 0.74 },
    PC_ACCENT = { 0.25, 0.44, 0.85, 1 },
    PC_WARN = { 0.93, 0.76, 0.35, 1 },
    CRATE_GREEN = { 0.25, 0.85, 0.25 },
    DIFF = {
      orange = { 1.0, 0.5, 0.25 },
      yellow = { 1.0, 1.0, 0.0 },
      green = { 0.25, 0.75, 0.25 },
      grey = { 0.5, 0.5, 0.5 },
    },
  },
  GEOMETRY = {
    NAV_W_EN = 184,
    NAV_W_ZH = 148,
    NAV_ITEM_H = 24,
    NAV_GROUP_H = 26,
    NAV_GAP = 8,
    NAV_FS = 16,
    NAV_ICON = 20,
    SUB_W = 76,
    SUB_H = 24,
    SUB_STEP = 84,
    ROW_H = 34,
    ROW_H1 = 24,
    ROW_H2 = 38,
    ROW_CAP = 300,
    RECIPE_CAP = 900,
    ROW_POOL_CAP = 32,
    SEC_CARD_MAX = 8,
    TOOL_MAX = 20,
    LV_SPLIT_EN = 0.75,
    LV_SPLIT_ZH = 0.80,
    SEARCH_RESERVED = 190,
    FAVOR_CURID = 3402,
  },
  COMMERCE_LABELS = {
    CRATE_TIERS = { "学徒", "熟练", "专家", "工匠" },
    PLUNDER_CATS = {
      "ingot",
      "herb",
      "leather",
      "enchant",
      "potion",
      "food",
      "bandage",
      "device",
      "gear",
      "other",
    },
  },
  CAMP_WATCH = {
    NEARBY_SPELL = 1283391,
    BOOSTED_SPELL = 1229451,
    RENEW_SECS = 600,
    TENT_ITEM = 288185,
    TENT_ICON = 4624631,
    WHISPER_TEXTS = {
      "大佬，打扰一下，请问可以蹭下帐篷吗？",
      "请问帐篷方便蹭一下吗？",
      "求蹭帐篷，感谢大佬！",
    },
  },
}

local function freezeTable(tbl)
  if type(ns.Data) == "table" and type(ns.Data._freeze) == "function" then
    return ns.Data._freeze(tbl)
  end
  local frozen = {}
  local roMt = {
    __newindex = function() error("DungeonsForeverProf: static data table is read-only", 2) end,
    __metatable = false,
  }
  local function walk(t)
    if type(t) ~= "table" or frozen[t] then return t end
    frozen[t] = true
    for _, v in pairs(t) do
      if type(v) == "table" then walk(v) end
    end
    return setmetatable(t, roMt)
  end
  return walk(tbl)
end

C = freezeTable(C)
ns.UIConfig = C
if type(_G.DF_NS) == "table" and _G.DF_NS ~= ns then
  _G.DF_NS.UIConfig = C
end
