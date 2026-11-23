local _, ns = ...
if type(ns) ~= "table" then ns = _G.DF_NS or {} end

if type(DF_Locale) ~= "function" or DF_Locale() ~= "zhCN" then return end

ns.Data.locales = ns.Data.locales or {}

ns.Data.locales.zhCN = ns.Data._freeze({
  camp = {
    camp_spell_40001 = { desc = "", effect = "", name = "基础营火" },
    camp_spell_40002 = { desc = "", effect = "", name = "发酵桶" },
  },
  category = { transmutes = "转化" },
  currency = { [3402] = "商人青睐" },
  faction = { [529] = "银色黎明" },
  item = {
    [2318] = "轻皮",
    [2770] = "铜矿石",
    [3371] = "食人魔力量药剂",
    [9149] = "点金石",
    [13544] = "灵质精华",
    [264011] = "工匠文书：食人魔力量药剂",
    [273085] = "图纸：发酵桶",
  },
  npc = { [1937] = "大师级炼金师", [11278] = "马格努斯·霜醒", [249713] = "永望训练师" },
  perk = {
    legacy_node_1001 = { desc = "提高炼金术产量", name = "炼金传世秘术" },
  },
  profession = {
    alchemy = "炼金术",
    camping = "露营",
    comprehension = "理解",
    mining = "采矿",
    poisons = "毒药",
    ["skill:171"] = "炼金术",
    ["skill:186"] = "采矿",
    ["skill:3012"] = "理解",
    ["skill:40"] = "毒药",
  },
  quest = { [94004] = "工匠文书：食人魔力量药剂" },
  spell = { [2657] = "熔炼铜锭", [11459] = "点金石", [20009] = "附魔副手 - 精神" },
  zone = { [12] = "艾尔文森林", [17] = "贫瘠之地", [1519] = "暴风城" },
})
