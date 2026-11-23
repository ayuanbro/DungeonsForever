local _, ns = ...
if type(ns) ~= "table" then ns = _G.DF_NS or {} end

ns.Data._recipeLoaders["mining"] = function()
  return {
    catalogEntries = {
      ["favor:2840"] = {
        availability = "live",
        categoryKey = "favor_exchange",
        currencyID = 3402,
        entryKey = "favor:2840",
        entryKind = "favor_exchange",
        isNew = false,
        itemID = 2840,
        profession = "mining",
      },
    },
    recipes = {
      [2657] = {
        availability = "live",
        categoryKey = "",
        green = 45,
        grey = 50,
        isNew = false,
        learnedAt = 1,
        orange = 1,
        outputCountMax = 1,
        outputCountMin = 1,
        outputItemID = 2840,
        outputKind = "item",
        profession = "mining",
        reagents = {
          { count = 1, itemID = 2770 },
        },
        recommendedSpecs = {},
        requiredTools = {},
        skillLineID = 186,
        spellID = 2657,
        yellow = 25,
      },
    },
  }
end
