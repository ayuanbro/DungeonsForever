local _, ns = ...

if not ns.LoadForeverPages then return end

local S = ns.ProfRouteSolver
if not S then return end

local M = {}
ns.ProfSolverRun = M

local FRAME_MS = 2
-- Leave room for one condition evaluation, result publication and incremental
-- collection between cooperative yield points inside the two-ms job budget.
local SLICE_MS = 0.5
local NOTIFY_MS = 250
local GC_SOFT_KB = 24576
local GC_STEPS = 1
local GC_STEP_KB = 256
local GC_EVERY = 4

local live = nil
local serial = 0

local function stamp(j)
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

function M.Stamp(j)
    return stamp(j)
end

function M.State(j)
    local job = j
    if not job and live then job = live.job end
    local phase, fraction = stamp(job)
    local st = { phase = phase, fraction = fraction }
    if job then
        st.seedSkill = job.seedSkill
        st.target = job.target
        st.expanded = job.expanded
        st.cpuUsed = job.cpuUsed
        st.cpuLimitMs = job.cpuLimitMs
        st.status = job.status
        st.slug = job.slug
    end
    return st
end

function M.Active()
    return live
end

function M.Running(slug)
    if not live then return false end
    if slug and live.slug ~= slug then return false end
    return true
end

function M.Stop()
    local a = live
    if not a then return nil end
    live = nil
    local j = a.job
    if j and not j.finished then
        j.status = "stopped"
        j.finished = true
    end
    return a
end

function M.Start(slug, opts, hooks)
    M.Stop()
    if not ns.IdleJobs then return nil end
    local o = {}
    for k, v in pairs(opts or {}) do o[k] = v end
    if not o.professions then
        local E = ns.ProfEconomy
        local list = (E and E.Professions and E.Professions()) or {}
        if not list[slug] then
            list[slug] = { cur = 1, max = 300 }
            if o.allowSecondaryLeveling then list[slug].unlearned = true end
        end
        o.professions = list
    end
    serial = serial + 1
    local j = S.NewJob(slug, o)
    local a = { job = j, slug = slug, serial = serial, hooks = hooks or {}, notified = 0 }
    if type(collectgarbage) == "function" then a.gcBase = collectgarbage("count") or 0 end
    live = a
    local function notify(done)
        local h = a.hooks.onProgress
        if not h then return end
        local now = debugprofilestop()
        if not done and a.notified ~= 0 and now - a.notified < NOTIFY_MS then return end
        a.notified = now
        h(j, M.State(j), done)
    end
    local gcTick = 0
    local function keepGC()
        if not a.gcBase or a.gcBase <= 0 then return end
        gcTick = gcTick + 1
        if gcTick % GC_EVERY ~= 0 then return end
        if collectgarbage("count") <= a.gcBase + GC_SOFT_KB then return end
        for _ = 1, GC_STEPS do collectgarbage("step", GC_STEP_KB) end
    end
    -- Keep preparation and result construction yieldable, as on master. The
    -- ordinary route runner must not turn a source-data capture into one frame.
    local runnerDead = false
    local runner = coroutine.create(function()
        local budget = SLICE_MS
        while true do
            if S.Run(j, budget) then return true end
            budget = coroutine.yield(false)
            if type(budget) ~= "number" then budget = SLICE_MS end
        end
    end)
    local function advance(ms)
        if runnerDead then return true end
        local ok, result = coroutine.resume(runner, ms or SLICE_MS)
        if not ok then
            j.status = "error"
            j.searchTermination = "error"
            j.failures = j.failures or {}
            j.failures.error = {code="solverError",detail=tostring(result)}
            runnerDead = true
            return true
        end
        if coroutine.status(runner) == "dead" then runnerDead = true return true end
        return result == true
    end
    ns.IdleJobs.Add(function()
        if live ~= a then return true end
        -- One resume leaves headroom for publication and avoids accumulating
        -- two slightly oversized slices inside a nominal two-ms callback.
        local done = advance(math.min(SLICE_MS, FRAME_MS))
        if not done then keepGC() end
        notify(done)
        if done then
            live = nil
            local h = a.hooks.onDone
            if h then h(j) end
            return true
        end
        return false
    end)
    return a
end

function M.Result(j)
    local job = j
    if not job and live then job = live.job end
    if not job then return nil end
    if job.result then return job.result end
    if not job.best then return nil end
    return S.Result(job, job.best, "searching")
end
