local _, ns = ...
if type(ns) ~= "table" then ns = _G.DF_NS or {} end

if type(DF_Locale) ~= "function" or DF_Locale() ~= "zhTW" then return end

ns.Data.locales = ns.Data.locales or {}

ns.Data.locales.zhTW = ns.Data._freeze({
  category = { transmutes = "轉化" },
  currency = { [3402] = "商人青睞" },
  faction = { [529] = "銀色黎明" },
  item = { [2318] = "輕皮", [2770] = "銅礦石", [9149] = "點金石", [13544] = "靈質精華" },
  npc = { [1937] = "大師級鍊金師", [11278] = "馬格努斯·霜醒" },
  perk = {
    legacy_node_1001 = { desc = "提高鍊金術產量", name = "鍊金傳世秘術" },
  },
  profession = {
    alchemy = "鍊金術",
    comprehension = "理解",
    mining = "採礦",
    poisons = "毒藥",
    ["skill:171"] = "鍊金術",
    ["skill:186"] = "採礦",
    ["skill:3012"] = "理解",
    ["skill:40"] = "毒藥",
  },
  spell = { [2657] = "熔煉銅錠", [11459] = "點金石", [20009] = "附魔副手 - 精神" },
  zone = { [12] = "艾爾文森林", [17] = "貧瘠之地", [1519] = "暴風城" },
})
