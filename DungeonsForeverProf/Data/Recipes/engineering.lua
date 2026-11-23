local _, ns = ...
if type(ns) ~= "table" then ns = _G.DF_NS or {} end

ns.Data._recipeLoaders["engineering"] = function()
  return {
    catalogEntries = {},
    recipes = {
      [12800] = {
        availability = "live",
        categoryKey = "",
        green = 245,
        grey = 265,
        isNew = false,
        learnedAt = 205,
        orange = 205,
        outputCountMax = 1,
        outputCountMin = 1,
        outputKind = "effect",
        profession = "engineering",
        reagents = {},
        recommendedSpecs = {},
        requiredTools = {},
        skillLineID = 202,
        spellID = 12800,
        yellow = 225,
      },
    },
  }
end
