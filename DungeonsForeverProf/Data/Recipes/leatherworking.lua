local _, ns = ...
if type(ns) ~= "table" then ns = _G.DF_NS or {} end

ns.Data._recipeLoaders["leatherworking"] = function()
  return {
    catalogEntries = {
      ["favor:248682"] = {
        availability = "live",
        categoryKey = "favor_exchange",
        currencyAmount = 12,
        currencyID = 3402,
        entryKey = "favor:248682",
        entryKind = "favor_exchange",
        isNew = false,
        itemID = 248682,
        profession = "leatherworking",
        reqSkill = 250,
      },
      ["favor:252805"] = {
        availability = "live",
        categoryKey = "favor_exchange",
        currencyAmount = 5,
        currencyID = 3402,
        entryKey = "favor:252805",
        entryKind = "favor_exchange",
        isNew = false,
        itemID = 252805,
        profession = "leatherworking",
        reqSkill = 120,
      },
    },
    recipes = {
      [3816] = {
        availability = "live",
        categoryKey = "",
        green = 75,
        grey = 95,
        isNew = false,
        learnedAt = 35,
        orange = 35,
        outputCountMax = 1,
        outputCountMin = 1,
        outputKind = "effect",
        profession = "leatherworking",
        reagents = {
          { count = 1, itemID = 2318 },
        },
        recommendedSpecs = {},
        requiredTools = {},
        skillLineID = 165,
        spellID = 3816,
        yellow = 55,
      },
      [1255102] = {
        availability = "live",
        categoryKey = "",
        green = 155,
        grey = 170,
        isNew = false,
        learnedAt = 120,
        orange = 120,
        outputCountMax = 1,
        outputCountMin = 1,
        outputKind = "effect",
        profession = "leatherworking",
        reagents = {
          { count = 4, itemID = 2318 },
        },
        recommendedSpecs = {},
        requiredTools = {},
        skillLineID = 165,
        spellID = 1255102,
        stationKey = "tanning_rack",
        yellow = 140,
      },
    },
  }
end
