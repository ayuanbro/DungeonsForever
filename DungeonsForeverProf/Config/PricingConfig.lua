local _, ns = ...
if type(ns) ~= "table" then ns = _G.DF_NS or {} end

local C = {
  AH_CUT = 0.05,
  NET_MULTIPLIER = 0.95,
  DEFAULT_RECOVERY_FEE_PCT = 5,
  MIN_RECOVERY_FEE_PCT = 0,
  MAX_RECOVERY_FEE_PCT = 25,
  RESIDUAL_MASS = 0.7,
  PROFIT_CAP = 20,
  RERATE_MIN_AH_GAIN_COPPER = 100,
  RERATE_MIN_SUPPLY = 40,
  FISHING_FILTER = {
    enabled = true,
    headMaxQtyShare = 0.05,
    headMaxLotCount = 3,
    cliffPriceRatio = 0.60,
    minTotalSupplyForTrim = 5,
  },
  ROBUST_FLOOR = {
    percentileLow = 0.10,
    percentileHigh = 0.15,
    defaultPercentile = 0.125,
    maxHighSpikeRatio = 3.0,
    minConfidenceSupply = 1,
  },
  SUPPLY_MAX_AGE_SEC = 172800,
  MAX_STALE_DAYS = 2,
  SCAN_SILENT_SEC = 45,
  SNAPSHOT_VERSION = 3,
  EASY_AUCTION = {
    dbName = "EasyAuctionDB12",
    cacheTTL = 2,
    indexTTL = 30,
    listLimit = 200,
  },
  CACHE = {
    quoteTTL = 600,
    negTTL = 60,
    slotsPerSlug = 4,
    quietDebounceMs = 300,
  },
  MATERIAL_SOURCE_PRECEDENCE = {
    "min_vendor_and_denoised_ah",
    "vendor",
    "denoised_ah",
    "raw_ah",
    "unknown",
  },
  UNAVAILABLE_ON_UNKNOWN_CONDITION = true,
}

local function freezeTable(tbl)
  if type(ns.Data) == "table" and type(ns.Data._freeze) == "function" then
    return ns.Data._freeze(tbl)
  end
  local frozen = {}
  local roMt = {
    __newindex = function() error("DungeonsForeverProf: static data table is read-only", 2) end,
    __metatable = false,
  }
  local function walk(t)
    if type(t) ~= "table" or frozen[t] then return t end
    frozen[t] = true
    for _, v in pairs(t) do
      if type(v) == "table" then walk(v) end
    end
    return setmetatable(t, roMt)
  end
  return walk(tbl)
end

C = freezeTable(C)
ns.PricingConfig = C
if type(_G.DF_NS) == "table" and _G.DF_NS ~= ns then
  _G.DF_NS.PricingConfig = C
end
