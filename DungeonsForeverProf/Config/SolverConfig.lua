local _, ns = ...
if type(ns) ~= "table" then ns = _G.DF_NS or {} end

local C = {
  CAP = 300,
  DEFAULT_TARGET = 300,
  MAX_PER_RECIPE = 3,
  DIFFICULTY_RATES = {
    G_YELLOW = 0.5,
    G_GREEN = 0.05,
  },
  GREEN_BUDGET_MODES = {
    optimistic = {
      mode = "optimistic",
      greenRateFactor = 1.0,
      missLog = nil,
      expectedCraftsOnly = true,
    },
    balanced = {
      mode = "balanced",
      greenRateFactor = 1.0,
      missLog = math.log(0.20),
    },
    pessimistic = {
      mode = "pessimistic",
      greenRateFactor = 0.5,
      missLog = math.log(0.05),
    },
  },
  OBJECTIVES = {
    ORDER = { "cheapest", "matcost", "crafts", "optim" },
    LABELS = {
      cheapest = "最省钱",
      matcost = "材料成本",
      crafts = "次数最少",
      optim = "乐观计数",
    },
  },
  COROUTINE_BUDGET = {
    cpuLimitMs = 8000,
    maxFrontier = 20000,
    rebatchCpuLimitMs = 2000,
    rebatchWorkLimit = 400000,
    speedPresets = {
      fast = { budgetMs = 8 },
      turbo = { budgetMs = 60, tickClockStride = 16 },
    },
    adaptiveSlice = {
      lowFpsThreshold = 25,
      lowFpsMs = 0.6,
      frameFraction = 0.09,
      minMs = 0.8,
      maxMs = 2.25,
      defaultFps = 60,
    },
    paintCapMs = 4,
    routeTickMs = 1,
    yieldThresholdMs = 3,
  },
  FRESHNESS = {
    executionIdleLimitSec = 48 * 3600,
    resultCacheTTL = 600,
    resultCacheSlots = 4,
  },
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
ns.SolverConfig = C
if type(_G.DF_NS) == "table" and _G.DF_NS ~= ns then
  _G.DF_NS.SolverConfig = C
end
