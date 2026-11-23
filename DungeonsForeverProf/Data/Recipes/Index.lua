local _, ns = ...
if type(ns) ~= "table" then ns = _G.DF_NS or {} end

local freeze = ns.Data._freeze
ns.Data.craftIndex = freeze({
  [2840] = { 2657 },
  [3371] = { 4508 },
  [6290] = { 7751 },
  [9149] = { 11459 },
})

ns.Data.recipeProfession = freeze({
  [2657] = "mining",
  [2842] = "poisons",
  [3816] = "leatherworking",
  [4508] = "alchemy",
  [7751] = "cooking",
  [11459] = "alchemy",
  [12800] = "engineering",
  [20009] = "enchanting",
  [1234567] = "comprehension",
  [1244645] = "alchemy",
  [1255102] = "leatherworking",
})

ns.Data.recipeProfessions = freeze({
  "alchemy",
  "comprehension",
  "cooking",
  "enchanting",
  "engineering",
  "leatherworking",
  "mining",
  "poisons",
})
