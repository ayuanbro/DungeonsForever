local _, ns = ...
if type(ns) ~= "table" then ns = _G.DF_NS or {} end

ns.Data._loaders["guides"] = function()
  return {
    fishingGuides = {
      cookingSteps = {
        {
          fishReagentIDs = { 6291 },
          green = 45,
          grey = 50,
          learnedAt = 1,
          orange = 1,
          outputItemID = 6290,
          reagents = {
            { count = 1, itemID = 6291 },
          },
          spellID = 7751,
          yellow = 30,
        },
      },
      fish = {
        [2318] = {
          areas = {
            { areaID = 17, dropRatePct = 0.001, sampleCount = 290731 },
          },
        },
        [6291] = {
          areas = {
            { areaID = 12, minSkill = 1, noGetaway = 75 },
          },
        },
        [13755] = {
          areas = {
            { areaID = 440, minSkill = 205, noGetaway = 300 },
          },
          note = "Winter only",
          pool = true,
          season = true,
        },
        [13759] = {
          areas = {
            { areaID = 440, minSkill = 205, noGetaway = 300 },
          },
          night = true,
        },
      },
      fishingSteps = {
        {
          areas = {
            { areaID = 12, minSkill = 1, noGetaway = 75 },
          },
          fishIDs = { 6291 },
          from = 1,
          to = 75,
        },
        {
          areas = {
            { areaID = 440, minSkill = 205, noGetaway = 300 },
          },
          fishIDs = { 13759, 13755 },
          from = 205,
          to = 300,
        },
      },
    },
    gatheringGuides = {
      mining = {
        bands = {
          {
            itemIDs = { 2770 },
            maxSkill = 65,
            minSkill = 1,
            zones = {
              { areaID = 12, nodeCount = 48 },
            },
          },
        },
        profession = "mining",
      },
    },
  }
end
