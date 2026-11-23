local _, ns = ...
if type(ns) ~= "table" then ns = _G.DF_NS or {} end

ns.Data._loaders["commerce"] = function()
  return {
    crates = {
      [280101] = {
        currencyID = 3402,
        itemID = 280101,
        minLevel = 10,
        options = {
          { count = 4, itemID = 2840 },
        },
        rewardAmount = 5,
        tier = 1,
      },
    },
    plunder = {
      [280201] = { category = "leather", itemID = 280201, levelBand = "1-20" },
    },
    writs = {
      [9195] = {
        qty = 20,
        questID = 9195,
        repReward = 0,
        targetItemID = 12643,
        writItemID = 22599,
      },
      [94004] = {
        minLevel = 10,
        qty = 4,
        questID = 94004,
        repReward = 150,
        targetItemID = 3371,
        writItemID = 264011,
      },
    },
  }
end
