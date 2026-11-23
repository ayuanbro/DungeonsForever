local _, ns = ...
if type(ns) ~= "table" then ns = _G.DF_NS or {} end
local gns = _G.DF_NS

local M = ns.ProfSolverRun or (type(gns) == "table" and gns.ProfSolverRun) or {}
ns.ProfSolverRun = M
if type(gns) == "table" and gns ~= ns then
    gns.ProfSolverRun = M
end

local function getSolverCfg()
    return ns.SolverConfig or (type(gns) == "table" and gns.SolverConfig) or nil
end

function M.Stamp(j)
    if not j then return "idle", 0 end
    if j.finished then return "done", 1 end
    if j.finalizing then return "finalizing", 0.90 + 0.10 * math.max(0, math.min(0.99, tonumber(j.finalizeProgress) or 0)) end
    if not j.snap then return "prepare", 0.01 end
    local cfg = getSolverCfg()
    if not j.seedDone then
        local defTarget = type(cfg) == "table" and type(cfg.DEFAULT_TARGET) == "number" and cfg.DEFAULT_TARGET or 300
        local target = j.target or defTarget
        local skill = j.seedSkill or 1
        local span = target - 1
        if span < 1 then span = 1 end
        local p = (skill - 1) / span
        if p < 0 then p = 0 elseif p > 1 then p = 1 end
        return "seed", 0.04 + 0.66 * p
    end
    local budget = type(cfg) == "table" and type(cfg.COROUTINE_BUDGET) == "table" and cfg.COROUTINE_BUDGET or nil
    local defCap = budget and type(budget.cpuLimitMs) == "number" and budget.cpuLimitMs or 8000
    local cap = j.cpuLimitMs or defCap
    if cap < 1 then cap = 1 end
    local used = (j.cpuUsed or 0) / cap
    if used < 0 then used = 0 elseif used > 1 then used = 1 end
    return "search", 0.70 + 0.20 * used
end
