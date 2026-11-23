local _, ns = ...
if type(ns) ~= "table" then ns = _G.DF_NS or {} end

ns.Data = ns.Data or {}
local Data = ns.Data
Data._loaders = Data._loaders or {}
Data._recipeLoaders = Data._recipeLoaders or {}
Data.recipes = Data.recipes or {}
Data.locales = Data.locales or {}

local _frozen = {}
local _roMt = {
  __newindex = function() error("DungeonsForeverProf: static data table is read-only", 2) end,
  __metatable = false,
}

local function _freeze(tbl)
  if type(tbl) ~= "table" or _frozen[tbl] then return tbl end
  _frozen[tbl] = true
  for _, v in pairs(tbl) do
    if type(v) == "table" then _freeze(v) end
  end
  return setmetatable(tbl, _roMt)
end
Data._freeze = _freeze

Data.meta = _freeze({
  branch = "forever",
  contractVersion = 1,
  fingerprint = "sha256:44edb0e199ae9f371855dbc2f6eec87fc9422916bda4a099cc2faa9c14f76366",
  foreverBuild = "1.60.1.71037",
})

Data.professions = _freeze({
  alchemy = {
    categories = {
      { icon = "inv_misc_gem_01", key = "transmutes", order = 1 },
    },
    icon = "trade_alchemy",
    kind = "primary",
    maxSkillCap = 300,
    perkKeys = { "legacy_node_1001" },
    racialKeys = {},
    slug = "alchemy",
  },
  blacksmithing = {
    categories = {},
    icon = "",
    kind = "primary",
    maxSkillCap = 300,
    perkKeys = {},
    racialKeys = {},
    slug = "blacksmithing",
  },
  camping = {
    categories = {},
    icon = "inv_campfire_01",
    kind = "system",
    maxSkillCap = 300,
    perkKeys = {},
    racialKeys = {},
    slug = "camping",
  },
  comprehension = {
    categories = {},
    icon = "",
    kind = "system",
    maxSkillCap = 300,
    perkKeys = {},
    racialKeys = {},
    slug = "comprehension",
  },
  cooking = {
    categories = {},
    icon = "",
    kind = "secondary",
    maxSkillCap = 300,
    perkKeys = {},
    racialKeys = {},
    slug = "cooking",
  },
  enchanting = {
    categories = {},
    icon = "",
    kind = "primary",
    maxSkillCap = 300,
    perkKeys = {},
    racialKeys = {},
    slug = "enchanting",
  },
  engineering = {
    categories = {},
    icon = "",
    kind = "primary",
    maxSkillCap = 300,
    perkKeys = {},
    racialKeys = {},
    slug = "engineering",
  },
  leatherworking = {
    categories = {},
    icon = "",
    kind = "primary",
    maxSkillCap = 300,
    perkKeys = {},
    racialKeys = {},
    slug = "leatherworking",
  },
  mining = {
    categories = {},
    icon = "",
    kind = "primary",
    maxSkillCap = 300,
    perkKeys = {},
    racialKeys = {},
    slug = "mining",
  },
  poisons = {
    categories = {},
    icon = "",
    kind = "system",
    maxSkillCap = 300,
    perkKeys = {},
    racialKeys = {},
    slug = "poisons",
  },
})

Data.skillLines = _freeze({
  [40] = { isPrimarySlot = false, profession = "poisons", skillLineID = 40, track = "forever" },
  [165] = { isPrimarySlot = true, profession = "leatherworking", skillLineID = 165, track = "forever" },
  [171] = { isPrimarySlot = true, profession = "alchemy", skillLineID = 171, track = "forever" },
  [185] = { isPrimarySlot = false, profession = "cooking", skillLineID = 185, track = "forever" },
  [186] = { isPrimarySlot = true, profession = "mining", skillLineID = 186, track = "forever" },
  [202] = { isPrimarySlot = true, profession = "engineering", skillLineID = 202, track = "forever" },
  [333] = { isPrimarySlot = true, profession = "enchanting", skillLineID = 333, track = "forever" },
  [2939] = { isPrimarySlot = false, profession = "cooking", skillLineID = 2939, track = "forever" },
  [2946] = { isPrimarySlot = true, profession = "mining", skillLineID = 2946, track = "forever" },
  [3012] = { isPrimarySlot = false, profession = "comprehension", skillLineID = 3012, track = "forever" },
})

function Data.Ensure(domain)
  if type(domain) ~= "string" then error("Ensure(domain): string expected", 2) end
  local existing = Data[domain]
  if type(existing) == "table" then return existing end
  local loader = Data._loaders[domain]
  if type(loader) ~= "function" then error("Ensure(domain): unknown domain " .. domain, 2) end
  local loaded = loader()
  Data._loaders[domain] = nil
  Data[domain] = _freeze(loaded)
  return Data[domain]
end
ns.Ensure = Data.Ensure

function Data.EnsureRecipes(slug)
  if type(slug) ~= "string" then error("EnsureRecipes(slug): string expected", 2) end
  local existing = Data.recipes[slug]
  if type(existing) == "table" then return existing end
  local loader = Data._recipeLoaders[slug]
  if type(loader) ~= "function" then error("EnsureRecipes(slug): unknown profession " .. slug, 2) end
  local loaded = loader()
  Data._recipeLoaders[slug] = nil
  Data.recipes[slug] = _freeze(loaded)
  return Data.recipes[slug]
end
ns.EnsureRecipes = Data.EnsureRecipes
