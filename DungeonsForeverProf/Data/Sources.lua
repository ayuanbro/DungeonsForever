local _, ns = ...
if type(ns) ~= "table" then ns = _G.DF_NS or {} end

ns.Data._loaders["sources"] = function()
  return {
    drops = {
      [2318] = {
        {
          areaID = 40,
          avgStack = 1.26,
          dropRatePct = 0.184,
          isWorldDrop = false,
          itemID = 2318,
          maxLevel = 13,
          minLevel = 12,
          npcID = 454,
          sampleCount = 41880,
        },
        {
          areaID = 267,
          dropRatePct = 57.143,
          isWorldDrop = false,
          itemID = 2318,
          maxLevel = 24,
          minLevel = 23,
          npcID = 2274,
          sampleCount = 7,
        },
      },
      [252805] = {
        {
          areaID = 440,
          dropRatePct = 15,
          isWorldDrop = false,
          itemID = 252805,
          maxLevel = 26,
          minLevel = 24,
          npcID = 260326,
          sampleCount = 100,
        },
      },
    },
    extraSources = {
      [2318] = {
        {
          avgStack = 3.33,
          dropRatePct = 0.001,
          itemID = 2318,
          sampleCount = 290731,
          sourceKind = "fished",
          targetID = 17,
          targetType = "zone",
        },
        {
          dropRatePct = 96.553,
          itemID = 2318,
          sampleCount = 153678,
          sourceKind = "mined",
          targetID = 1731,
          targetType = "object",
        },
        {
          avgStack = 1.5,
          dropRatePct = 71.709,
          itemID = 2318,
          sampleCount = 35011,
          sourceKind = "skinned",
          targetID = 3256,
          targetType = "npc",
        },
      },
      [211780] = {
        {
          dropRatePct = 55,
          itemID = 211780,
          sampleCount = 100,
          sourceKind = "contained_in_item",
          targetID = 277651,
          targetType = "item",
        },
      },
    },
    learningRoutes = {
      [2657] = {
        coverage = "complete",
        missingReasons = {},
        profession = "mining",
        routes = {
          {
            conditions = {},
            conditionsKnown = true,
            kind = "autoGrant",
            minSkillRank = 1,
            questIDs = {},
            routeKey = "autoGrant",
            status = "confirmed",
            trainers = {},
          },
        },
        spellID = 2657,
      },
      [4508] = {
        coverage = "complete",
        missingReasons = {},
        profession = "alchemy",
        routes = {
          {
            conditions = {},
            conditionsKnown = true,
            kind = "trainer",
            questIDs = {},
            routeKey = "trainer",
            status = "confirmed",
            totalTrainerCount = 2,
            trainers = {
              {
                conditions = {
                  {
                    groups = {
                      { 91920 },
                    },
                    kind = "questGroup",
                  },
                },
                npcID = 1937,
              },
              { npcID = 9999 },
            },
            trainingCostCopper = 200,
          },
        },
        spellID = 4508,
      },
      [7751] = {
        coverage = "complete",
        missingReasons = {},
        profession = "cooking",
        routes = {
          {
            conditions = {},
            conditionsKnown = true,
            kind = "autoGrant",
            minSkillRank = 1,
            questIDs = {},
            routeKey = "autoGrant",
            status = "confirmed",
            trainers = {},
          },
        },
        spellID = 7751,
      },
      [1244645] = {
        coverage = "complete",
        missingReasons = {},
        profession = "alchemy",
        routes = {
          {
            conditions = {},
            conditionsKnown = true,
            kind = "trainer",
            questIDs = {},
            routeKey = "trainer",
            status = "confirmed",
            trainers = {
              {
                conditions = {
                  {
                    groups = {
                      { 91920 },
                    },
                    kind = "questGroup",
                  },
                },
                npcID = 1937,
              },
              {
                conditions = {
                  {
                    groups = {
                      { 92110 },
                    },
                    kind = "questGroup",
                  },
                },
                npcID = 249713,
              },
            },
          },
        },
        spellID = 1244645,
      },
      [1255102] = {
        coverage = "complete",
        missingReasons = {},
        profession = "leatherworking",
        routes = {
          {
            conditions = {},
            conditionsKnown = true,
            kind = "item",
            questIDs = {},
            routeKey = "item:252805",
            status = "confirmed",
            teachingItemID = 252805,
            trainers = {},
          },
          {
            conditions = {},
            conditionsKnown = true,
            kind = "trainer",
            questIDs = {},
            routeKey = "trainer",
            status = "confirmed",
            totalTrainerCount = 1,
            trainers = {
              { npcID = 5595 },
            },
            trainingCostCopper = 200,
          },
        },
        spellID = 1255102,
      },
    },
    vendorOffers = {
      [2318] = {
        commonVendorCount = 230,
        offers = {
          {
            bundleSize = 5,
            conditions = {},
            costItems = {
              { count = 2, itemID = 2447 },
            },
            currencies = {
              { amount = 5, currencyID = 3402 },
            },
            maxStock = -1,
            npcID = 151,
            optionIndex = 0,
            priceCopper = 25,
            priceVerified = true,
          },
        },
      },
      [8030] = {
        offers = {
          {
            bundleSize = 1,
            conditions = {},
            costItems = {},
            currencies = {},
            npcID = 11278,
            optionIndex = 0,
            priceCopper = 1000,
            priceVerified = false,
          },
        },
      },
      [248682] = {
        offers = {
          {
            bundleSize = 1,
            conditions = {
              { factionID = 529, kind = "reputation", minStanding = 6 },
              { kind = "unknown", textKey = "cond:24e844ab01dd" },
            },
            costItems = {
              { count = 2, itemID = 2318 },
            },
            currencies = {
              { amount = 12, currencyID = 3402 },
            },
            npcID = 248198,
            optionIndex = 0,
            priceCopper = 500,
            priceVerified = false,
          },
          {
            bundleSize = 1,
            conditions = {
              { factionID = 529, kind = "reputation", minStanding = 6 },
              { kind = "unknown", textKey = "cond:24e844ab01dd" },
            },
            costItems = {},
            currencies = {
              { amount = 25, currencyID = 3402 },
            },
            npcID = 248198,
            optionIndex = 1,
            priceCopper = 0,
            priceVerified = false,
          },
        },
      },
      [252805] = {
        offers = {
          {
            bundleSize = 1,
            conditions = {},
            costItems = {
              { count = 2, itemID = 2447 },
            },
            currencies = {
              { amount = 5, currencyID = 3402 },
            },
            maxStock = 1,
            npcID = 5594,
            optionIndex = 0,
            priceCopper = 1500,
            priceVerified = true,
          },
        },
      },
    },
  }
end
