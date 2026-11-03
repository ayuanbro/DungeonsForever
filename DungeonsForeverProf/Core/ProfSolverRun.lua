local ns = _G.DF_NS or {}

if not ns.LoadForeverPages then return end

local S = ns.ProfRouteSolver
if not S then return end

local M = {}
ns.ProfSolverRun = M

function M.Stamp(j)
    if not j then return "idle", 0 end
    if j.finished then return "done", 1 end
    if j.finalizing then return "finalizing", 1 end
    if not j.snap then return "prepare", 0.01 end
    if not j.seedDone then
        local target = j.target or 300
        local skill = j.seedSkill or 1
        local span = target - 1
        if span < 1 then span = 1 end
        local p = (skill - 1) / span
        if p < 0 then p = 0 elseif p > 1 then p = 1 end
        return "seed", 0.04 + 0.66 * p
    end
    local cap = j.cpuLimitMs or 8000
    if cap < 1 then cap = 1 end
    local used = (j.cpuUsed or 0) / cap
    if used < 0 then used = 0 elseif used > 1 then used = 1 end
    return "search", 0.70 + 0.30 * used
end
