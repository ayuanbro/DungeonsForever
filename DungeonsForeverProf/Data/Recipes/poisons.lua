local _, ns = ...
if type(ns) ~= "table" then ns = _G.DF_NS or {} end

ns.Data._recipeLoaders["poisons"] = function()
  return {
    catalogEntries = {},
    recipes = {
      [2842] = {
        availability = "live",
        categoryKey = "",
        green = 40,
        grey = 60,
        isNew = true,
        learnedAt = 1,
        orange = 1,
        outputCountMax = 1,
        outputCountMin = 1,
        outputKind = "effect",
        profession = "poisons",
        reagents = {},
        recommendedSpecs = {},
        requiredTools = {},
        skillLineID = 40,
        spellID = 2842,
        yellow = 20,
      },
    },
  }
end
