local _, ns = ...
if type(ns) ~= "table" then ns = _G.DF_NS or {} end
local gns = _G.DF_NS

local function readBudget()
    local cfg = ns.SolverConfig or (type(gns) == "table" and gns.SolverConfig) or nil
    return type(cfg) == "table" and cfg.COROUTINE_BUDGET or nil
end

local initialBudget = readBudget()
local CAP = (type(initialBudget) == "table" and type(initialBudget.paintCapMs) == "number" and initialBudget.paintCapMs > 0)
    and initialBudget.paintCapMs or 4

local function nowMs()
    if type(_G.debugprofilestop) == "function" then
        local ok, v = pcall(_G.debugprofilestop)
        if ok and type(v) == "number" then return v end
    end
    return 0
end

local qUrg, qNorm, qStep, qBg = {}, {}, {}, {}
local jobs = {}
local jobGen = {}
local deferredByKey = {}
local drv, armed, pumping = nil, false, false

local function inCombat()
    if type(_G.InCombatLockdown) == "function" then
        local ok, v = pcall(_G.InCombatLockdown)
        if ok then return v == true end
    end
    return false
end

local function stepJob(key, gen)
    local j = jobs[key]
    if not j or j.gen ~= gen or jobGen[key] ~= gen then return true end
    local cap = j.cap or CAP
    local t0 = nowMs()
    while true do
        if coroutine.status(j.co) == "dead" then break end
        local ok, err = coroutine.resume(j.co)
        if jobs[key] ~= j or j.gen ~= gen or jobGen[key] ~= gen then
            return true
        end
        if not ok then
            _G.DF_LAST_PAINT_ERR = tostring(err)
            pcall(print, "|cffff5040[无限副本手册] 页面渲染出错（已停止该次渲染）：|r" .. tostring(err))
            break
        end
        if coroutine.status(j.co) == "dead" then break end
        if nowMs() - t0 >= cap then return false end
    end
    if jobs[key] == j and j.gen == gen and jobGen[key] == gen then
        jobs[key] = nil
        if type(j.onDone) == "function" then pcall(j.onDone) end
    end
    return true
end

local function idleNow()
    return next(jobs) == nil and #qUrg == 0 and #qStep == 0 and #qNorm == 0 and #qBg == 0
end

local function runQueue(queue, allowYield, capMs)
    local t0 = nowMs()
    local keep = {}
    local ran = false
    while #queue > 0 do
        local fn = table.remove(queue, 1)
        ran = true
        local ok, done = pcall(fn)
        if allowYield and ok and done ~= true then
            keep[#keep + 1] = fn
        end
        if nowMs() - t0 >= capMs then break end
    end
    for i = 1, #keep do
        queue[#queue + 1] = keep[i]
    end
    return ran
end

local arm

local function pumpTick()
    local ran = false
    if not drv then
        armed = false
    end
    if next(jobs) ~= nil then
        local keys = {}
        for k in pairs(jobs) do keys[#keys + 1] = k end
        for i = 1, #keys do
            local k = keys[i]
            local j = jobs[k]
            if j then
                ran = true
                stepJob(k, j.gen)
            end
        end
    end
    if #qUrg > 0 then
        if runQueue(qUrg, true, CAP) then ran = true end
    end
    if #qStep > 0 then
        if runQueue(qStep, false, CAP) then ran = true end
    end
    if not inCombat() then
        if #qNorm > 0 then
            if runQueue(qNorm, true, CAP) then ran = true end
        end
        if #qBg > 0 and #qNorm == 0 then
            if runQueue(qBg, true, CAP) then ran = true end
        end
    end
    if idleNow() then
        armed = false
        if drv and type(drv.SetScript) == "function" then
            pcall(drv.SetScript, drv, "OnUpdate", nil)
        end
    elseif not drv and not pumping then
        arm()
    end
    return ran
end

if type(_G.CreateFrame) == "function" then
    local ok, f = pcall(_G.CreateFrame, "Frame", nil, _G.UIParent)
    if ok and type(f) == "table" and type(f.SetScript) == "function" then
        drv = f
        if type(drv.SetSize) == "function" then pcall(drv.SetSize, drv, 1, 1) end
        if type(drv.SetFrameStrata) == "function" then pcall(drv.SetFrameStrata, drv, "BACKGROUND") end
        if type(drv.Show) == "function" then pcall(drv.Show, drv) end
    end
end

arm = function()
    if armed then return end
    if drv then
        armed = true
        pcall(drv.SetScript, drv, "OnUpdate", pumpTick)
        return
    end
    if type(_G.C_Timer) == "table" and type(_G.C_Timer.After) == "function" then
        armed = true
        local ok = pcall(_G.C_Timer.After, 0, pumpTick)
        if ok then return end
        armed = false
    end
    if pumping then return end
    pumping = true
    local guard = 0
    while not idleNow() do
        guard = guard + 1
        local progressed = pumpTick()
        if not progressed or guard > 100000 then break end
    end
    pumping = false
end

local Idle = {}

function Idle.SliceCap(defaultMs)
    local budget = readBudget()
    local baseCap = (type(budget) == "table" and type(budget.paintCapMs) == "number" and budget.paintCapMs > 0)
        and budget.paintCapMs or CAP
    local def = (type(defaultMs) == "number" and defaultMs > 0) and defaultMs or baseCap
    if type(_G.GetFramerate) == "function" then
        local ok, fps = pcall(_G.GetFramerate)
        if ok and type(fps) == "number" and fps > 0 then
            local ad = type(budget) == "table" and type(budget.adaptiveSlice) == "table" and budget.adaptiveSlice or {}
            local lowThresh = ad.lowFpsThreshold or 25
            local lowMs = ad.lowFpsMs or 0.6
            local frac = ad.frameFraction or 0.09
            local minMs = ad.minMs or 0.8
            local maxMs = ad.maxMs or 2.25
            local adaptive
            if fps < lowThresh then
                adaptive = lowMs
            else
                adaptive = math.max(minMs, math.min(maxMs, (1000 / fps) * frac))
            end
            return math.min(def, adaptive)
        end
    end
    return def
end

function Idle.Add(fn)
    if type(fn) ~= "function" then return end
    qNorm[#qNorm + 1] = fn
    arm()
end

function Idle.Urgent(fn)
    if type(fn) ~= "function" then return end
    qUrg[#qUrg + 1] = fn
    arm()
end

function Idle.Background(fn)
    if type(fn) ~= "function" then return end
    qBg[#qBg + 1] = fn
    arm()
end

function Idle.Defer(key, fn, priority)
    if type(fn) ~= "function" then return end
    priority = priority or "normal"
    if key == nil then
        if priority == "urgent" then
            Idle.Urgent(fn)
        elseif priority == "background" then
            Idle.Background(fn)
        else
            Idle.Add(fn)
        end
        return
    end
    local existing = deferredByKey[key]
    if existing and not existing.cancelled then
        if existing.priority == priority and not existing.running then
            existing.fn = fn
            return
        end
        existing.cancelled = true
    end
    local entry = {
        key = key,
        fn = fn,
        priority = priority,
        cancelled = false,
        running = false,
    }
    deferredByKey[key] = entry
    local function wrapper()
        if entry.cancelled then return true end
        entry.running = true
        local ok, done = pcall(entry.fn)
        entry.running = false
        if not ok then
            if deferredByKey[key] == entry then
                deferredByKey[key] = nil
            end
            error(done, 0)
        end
        if entry.cancelled or done == true then
            if deferredByKey[key] == entry then
                deferredByKey[key] = nil
            end
            return true
        end
        return false
    end
    if priority == "urgent" then
        Idle.Urgent(wrapper)
    elseif priority == "background" then
        Idle.Background(wrapper)
    else
        Idle.Add(wrapper)
    end
end

function Idle.Cancel(key)
    if key == nil then return end
    local entry = deferredByKey[key]
    if entry then
        entry.cancelled = true
        deferredByKey[key] = nil
    end
end

function Idle.StepGC(frames, kb)
    local left = frames or 60
    Idle.Add(function()
        if left <= 0 then return true end
        left = left - 1
        if type(collectgarbage) == "function" then
            pcall(collectgarbage, "step", kb or 512)
        end
        return false
    end)
end

function Idle.Pump()
    return pumpTick()
end

function Idle.Flush()
    local guard = 0
    while not idleNow() do
        guard = guard + 1
        local progressed = pumpTick()
        if not progressed or guard > 100000 then break end
    end
end

local Paint = {}

function Paint.Run(key, body, onDone, cap)
    if type(body) ~= "function" and type(body) ~= "thread" then return end
    local gen = (jobGen[key] or 0) + 1
    jobGen[key] = gen
    jobs[key] = {
        co = type(body) == "thread" and body or coroutine.create(body),
        gen = gen,
        onDone = onDone,
        cap = cap or CAP,
    }
    arm()
    return gen
end

function Paint.Active(key)
    return jobs[key] ~= nil
end

function Paint.Cancel(key)
    jobGen[key] = (jobGen[key] or 0) + 1
    jobs[key] = nil
end

local Step = {}

function Step.Push(fn)
    if type(fn) ~= "function" then return end
    qStep[#qStep + 1] = fn
    arm()
end

function Step.Run()
    if not idleNow() then
        pumpTick()
    end
end

local function profGate()
    local h = ns.ProfHost or (type(gns) == "table" and gns.ProfHost) or nil
    if type(h) ~= "table" then return nil end
    local dg = h.DG
    if type(dg) ~= "table" then return nil end
    return dg.Gate
end

local function ProfPhased(total, body, onFail)
    if type(body) ~= "function" and type(body) ~= "thread" then return end
    local Gate = profGate()
    if type(collectgarbage) == "function" then
        pcall(collectgarbage, "setpause", 150)
        pcall(collectgarbage, "setstepmul", 300)
    end
    local co = type(body) == "thread" and body or coroutine.create(body)
    if Gate and type(Gate.Begin) == "function" then pcall(Gate.Begin, total) end
    local function restore()
        if type(collectgarbage) == "function" then
            pcall(collectgarbage, "restart")
            pcall(collectgarbage, "setpause", 200)
            pcall(collectgarbage, "setstepmul", 200)
        end
    end
    Idle.Urgent(function()
        local t0 = nowMs()
        while true do
            if coroutine.status(co) == "dead" then
                restore()
                if Gate and type(Gate.Finish) == "function" then pcall(Gate.Finish) end
                return true
            end
            local ok, err = coroutine.resume(co)
            if not ok then
                restore()
                _G.DF_LAST_BUILD_ERR = tostring(err)
                if Gate and type(Gate.Finish) == "function" then pcall(Gate.Finish) end
                if type(onFail) == "function" then pcall(onFail) end
                pcall(print, "|cffff5040[无限副本手册] 分帧构建出错（已跳过该块）：|r" .. tostring(err))
                return true
            end
            if Gate and type(Gate.Advance) == "function" then pcall(Gate.Advance, 1) end
            if nowMs() - t0 >= CAP then return false end
        end
    end)
end

ns.ProfIdle = Idle
ns.ProfPaint = Paint
ns.ProfStep = Step
ns.ProfPhased = ProfPhased
if type(gns) == "table" and gns ~= ns then
    gns.ProfIdle = Idle
    gns.ProfPaint = Paint
    gns.ProfStep = Step
    gns.ProfPhased = ProfPhased
end
