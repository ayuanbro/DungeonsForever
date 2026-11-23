local _, ns = ...
if type(ns) ~= "table" then ns = _G.DF_NS or {} end

ns.Data._recipeLoaders["enchanting"] = function()
  return {
    catalogEntries = {
      ["favor:2318"] = {
        availability = "live",
        categoryKey = "favor_exchange",
        currencyAmount = 5,
        currencyID = 3402,
        entryKey = "favor:2318",
        entryKind = "favor_exchange",
        isNew = false,
        itemID = 2318,
        profession = "enchanting",
      },
    },
    recipes = {
      [20009] = {
        availability = "live",
        categoryKey = "",
        enchantSlot = "offhand",
        green = 190,
        grey = 200,
        isNew = false,
        learnedAt = 150,
        orange = 150,
        outputCountMax = 1,
        outputCountMin = 1,
        outputKind = "enchant",
        profession = "enchanting",
        reagents = {},
        recommendedSpecs = {},
        requiredTools = {},
        skillLineID = 333,
        spellID = 20009,
        stats = { base_points = 5, enchant_id = 2501 },
        yellow = 175,
      },
    },
  }
end
