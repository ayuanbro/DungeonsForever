local _, ns = ...
if type(ns) ~= "table" then ns = _G.DF_NS or {} end

ns.Data._recipeLoaders["cooking"] = function()
  return {
    catalogEntries = {},
    recipes = {
      [7751] = {
        availability = "live",
        categoryKey = "",
        green = 45,
        grey = 50,
        isNew = false,
        learnedAt = 1,
        orange = 1,
        outputCountMax = 1,
        outputCountMin = 1,
        outputItemID = 6290,
        outputKind = "item",
        profession = "cooking",
        reagents = {
          { count = 1, itemID = 6291 },
        },
        recommendedSpecs = {},
        requiredTools = {},
        skillLineID = 185,
        spellID = 7751,
        yellow = 30,
      },
    },
  }
end
