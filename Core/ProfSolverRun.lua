local _, ns = ...

if not ns.LoadForeverPages then return end

local S = ns.ProfRouteSolver
if not S then return end

local M = {}
ns.ProfSolverRun = M

local FRAME_MS = 6
local SLICE_MS = 2
local NOTIFY_MS = 250

local live = nil
local serial = 0

local function stamp(j)
    if not j then return "idle", 0 end
    if j.finished then return "done", 1 end
    if not j.seedDone then
        local target = j.target or 300
        local skill = j.seedSkill or 1
        local span = target - 1
        if span < 1 then span = 1 end
        local p = (skill - 1) / span
        if p < 0 then p = 0 elseif p > 1 then p = 1 end
        return "seed", 0.04 + 0.66 * p
    end
    local cap = j.cpuLimitMs or 5000
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
        if not list[slug] then list[slug] = { cur = 1, max = 300 } end
        o.professions = list
    end
    serial = serial + 1
    local j = S.NewJob(slug, o)
    local a = { job = j, slug = slug, serial = serial, hooks = hooks or {}, notified = 0 }
    live = a
    local function notify(done)
        local h = a.hooks.onProgress
        if not h then return end
        local now = debugprofilestop()
        if not done and a.notified ~= 0 and now - a.notified < NOTIFY_MS then return end
        a.notified = now
        h(j, M.State(j), done)
    end
    ns.IdleJobs.Add(function()
        if live ~= a then return true end
        local frameStart = debugprofilestop()
        local done = false
        while true do
            done = S.Run(j, SLICE_MS)
            if done then break end
            if debugprofilestop() - frameStart >= FRAME_MS then break end
        end
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
