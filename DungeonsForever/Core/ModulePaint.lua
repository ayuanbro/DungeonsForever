local _, ns = ...

local CAP = 4

local function nowMs()
    if type(debugprofilestop) == "function" then
        local ok, v = pcall(debugprofilestop)
        if ok and type(v) == "number" then return v end
    end
    return 0
end

local function inCombat()
    return InCombatLockdown and InCombatLockdown() or false
end

local function gateOf()
    local h = ns.ProfHost
    if type(h) ~= "table" then return nil end
    local dg = h.DG
    if type(dg) ~= "table" then return nil end
    return dg.Gate
end

function ns.ModulePaint(prefix)
    if type(prefix) ~= "string" then return nil end
    local qUrg, qNorm, qStep = {}, {}, {}
    local jobs, jobGen = {}, {}
    local paintBusy = false

    local function stepJob(key, gen)
        local j = jobs[key]
        if not j or j.gen ~= gen then return true end
        local cap = j.cap or CAP
        local t0 = nowMs()
        while true do
            if coroutine.status(j.co) == "dead" then break end
            local ok, err = coroutine.resume(j.co)
            if not ok then
                _G.DF_LAST_PAINT_ERR = tostring(err)
                print("|cffff5040[无限副本手册] 页面渲染出错（已停止该次渲染）：|r" .. tostring(err))
                break
            end
            if coroutine.status(j.co) == "dead" then break end
            if nowMs() - t0 >= cap then return false end
        end
        jobs[key] = nil
        if type(j.onDone) == "function" then pcall(j.onDone) end
        return true
    end

    local function pumpTick()
        if next(jobs) ~= nil then
            local keys = {}
            for k in pairs(jobs) do keys[#keys + 1] = k end
            for i = 1, #keys do
                local k = keys[i]
                local j = jobs[k]
                if j then stepJob(k, j.gen) end
            end
        end
        if #qUrg > 0 then
            local t0 = nowMs()
            local keep = {}
            while #qUrg > 0 do
                local fn = table.remove(qUrg, 1)
                local ok, done = pcall(fn)
                if ok and done ~= true then keep[#keep + 1] = fn end
                if nowMs() - t0 >= CAP then break end
            end
            for i = 1, #keep do qUrg[#qUrg + 1] = keep[i] end
        end
        if #qStep > 0 then
            local t0 = nowMs()
            while #qStep > 0 do
                local fn = table.remove(qStep, 1)
                pcall(fn)
                if nowMs() - t0 >= CAP then break end
            end
        end
        if #qNorm > 0 and not inCombat() then
            local t0 = nowMs()
            local keep = {}
            while #qNorm > 0 do
                local fn = table.remove(qNorm, 1)
                local ok, done = pcall(fn)
                if ok and done ~= true then keep[#keep + 1] = fn end
                if nowMs() - t0 >= CAP then break end
            end
            for i = 1, #keep do qNorm[#qNorm + 1] = keep[i] end
        end
    end

    local drv = CreateFrame("Frame", nil, UIParent)
    drv:SetSize(1, 1)
    drv:SetFrameStrata("BACKGROUND")
    drv:Show()
    drv:SetScript("OnUpdate", pumpTick)

    local Idle = {}
    local Paint = {}
    local Step = {}
    local M = { Idle = Idle, Paint = Paint, Step = Step }

    function Idle.Add(fn)
        if type(fn) ~= "function" then return end
        qNorm[#qNorm + 1] = fn
    end

    function Idle.Urgent(fn)
        if type(fn) ~= "function" then return end
        qUrg[#qUrg + 1] = fn
    end

    function Idle.StepGC(frames, kb)
        local left = frames or 60
        Idle.Add(function()
            if left <= 0 then return true end
            left = left - 1
            collectgarbage("step", kb or 512)
            return false
        end)
    end

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
        if not paintBusy then
            paintBusy = true
            pcall(stepJob, key, gen)
            paintBusy = false
        end
        return gen
    end

    function Paint.Active(key)
        return jobs[key] ~= nil
    end

    function Paint.Cancel(key)
        jobGen[key] = (jobGen[key] or 0) + 1
        jobs[key] = nil
    end

    function Step.Push(fn)
        if type(fn) ~= "function" then return end
        qStep[#qStep + 1] = fn
    end

    function Step.Run()
    end

    function M.Phased(total, body, onFail)
        local Gate = gateOf()
        if type(collectgarbage) == "function" then
            pcall(collectgarbage, "setpause", 150)
            pcall(collectgarbage, "setstepmul", 300)
        end
        local co = type(body) == "thread" and body or coroutine.create(body)
        if Gate and Gate.Begin then pcall(Gate.Begin, total) end
        local function restore()
            if type(collectgarbage) == "function" then
                pcall(collectgarbage, "restart")
                pcall(collectgarbage, "setpause", 200)
                pcall(collectgarbage, "setstepmul", 200)
            end
        end
        local function slice()
            local t0 = nowMs()
            while true do
                if coroutine.status(co) == "dead" then
                    restore()
                    if Gate and Gate.Finish then pcall(Gate.Finish) end
                    return true
                end
                local ok, err = coroutine.resume(co)
                if not ok then
                    restore()
                    _G.DF_LAST_BUILD_ERR = tostring(err)
                    if Gate and Gate.Finish then pcall(Gate.Finish) end
                    if type(onFail) == "function" then pcall(onFail) end
                    print("|cffff5040[无限副本手册] 分帧构建出错（已跳过该块）：|r" .. tostring(err))
                    return true
                end
                if Gate and Gate.Advance then pcall(Gate.Advance, 1) end
                if nowMs() - t0 >= CAP then return false end
            end
        end
        if not slice() then Idle.Urgent(slice) end
    end

    return M
end
