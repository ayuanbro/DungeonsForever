-- Shared route lifecycle for the native, main-TOC profession implementation.
-- Calculations are replaceable candidates; an execution owns an immutable copy.
local _, ns = ...
if not ns.LoadForeverPages then return end
local RA, E, S = ns.ProfRouteAuto, ns.ProfEconomy, ns.ProfRouteSolver
if not (RA and E and S) then return end
local quickCompute, clearPrices, baseOptions = RA.Compute, RA.Invalidate, RA.OptionsFor
local jobs, results, active, listeners, progressListeners = {}, {}, {}, {}, {}
local serial, revision = 0, 0
local legacyRun
local MODEL, CACHE_LIMIT = 1, 4
local function learningPolicy()
    return E.LearningPolicyFingerprint and E.LearningPolicyFingerprint() or "native-learning:4:gold-procurement"
end
local function now() return time and time() or 0 end
local function copy(value, seen)
    if type(value) ~= "table" then return value end
    seen = seen or {}; if seen[value] then return seen[value] end
    local out = {}; seen[value] = out
    for k,v in pairs(value) do
        if type(k) == "string" or type(k) == "number" then
            local kind = type(v)
            if kind == "table" then out[k] = copy(v, seen)
            elseif kind == "string" or kind == "number" or kind == "boolean" then out[k] = v end
        end
    end
    return out
end
local function character()
    if E.CharacterKey then return E.CharacterKey() end
    return (UnitName and UnitName("player") or "Unknown") .. "-" .. (GetRealmName and GetRealmName() or "Realm")
end
local function saved()
    if DungeonsForeverDB~=nil and type(DungeonsForeverDB)~="table" then return nil,"historyUnreadable" end
    DungeonsForeverDB = DungeonsForeverDB or {}
    if DungeonsForeverDB.prof~=nil and type(DungeonsForeverDB.prof)~="table" then return nil,"historyUnreadable" end
    DungeonsForeverDB.prof = DungeonsForeverDB.prof or {}
    local prof = DungeonsForeverDB.prof
    -- Use a native cache subtree; do not reinterpret module-branch archives.
    if prof.routePlans~=nil and (type(prof.routePlans)~="table" or prof.routePlans.version~=MODEL) then return nil,"historyUnreadable" end
    prof.routePlans = prof.routePlans or {version=MODEL, characters={}}
    local all = prof.routePlans.characters
    if type(all) ~= "table" then return nil,"historyUnreadable" end
    local key = character()
    if all[key]~=nil and (type(all[key])~="table" or type(all[key].routes)~="table" or type(all[key].active)~="table"
        or type(all[key].nextID)~="number" or all[key].nextID<0 or all[key].nextID~=math.floor(all[key].nextID)) then return nil,"historyUnreadable" end
    all[key] = all[key] or {routes={}, active={}, nextID=0}
    return all[key]
end
local function setting(key, fallback)
    local pd = ns.ProfModule
    if pd and pd.SettingRaw then
        local value = pd.SettingRaw(key); if value ~= nil then return value end
    end
    return fallback
end
function RA.OptionsFor(slug, current)
    local opts = baseOptions and baseOptions(slug, current) or {}
    opts.fromCurrent = setting("autoFromCurrent", true)
    opts.cpuLimitMs = setting("solverRoute", false) and 8000 or 5000
    opts.autoCraftTools = setting("autoCraftTools", true)
    opts.recoveryEnabled = setting("recoveryEnabled", false)
    opts.recoveryFeePercent = setting("recoveryFeePercent", 5)
    opts.allowLimitedFormulas = setting("autoBuyLimitedFormulas", false)
    opts.skipUnpricedFormulas = setting("autoSkipUnpricedFormulas", true)
    opts.exclusions = copy(E.GetPolicies and E.GetPolicies(slug) or {})
    if E.GetRoutePartner then opts.secondaryProfession = E.GetRoutePartner(slug) end
    -- Only explicit continuation may introduce verified route-made stock.
    opts.executionInventory = nil
    return opts
end
local function options(slug, supplied)
    local opts = copy(supplied or RA.OptionsFor(slug))
    -- Identity of a synthetic immutable input is kept out of serialized copies.
    if supplied and supplied.snapshot then opts.snapshot = supplied.snapshot end
    opts.scheme = opts.scheme or "cheapest"
    opts.profession = slug
    opts.start = math.max(1, math.min(300, math.floor(tonumber(opts.start) or 1)))
    opts.target = math.max(1, math.min(300, math.floor(tonumber(opts.target) or 300)))
    if opts.recoveryEnabled == nil then opts.recoveryEnabled = setting("recoveryEnabled", false) end
    if opts.recoveryFeePercent == nil then opts.recoveryFeePercent = setting("recoveryFeePercent", 5) end
    if opts.autoCraftTools == nil then opts.autoCraftTools = setting("autoCraftTools", true) end
    if opts.allowLimitedFormulas == nil then opts.allowLimitedFormulas = setting("autoBuyLimitedFormulas", false) end
    opts.exclusions = opts.exclusions or copy(E.GetPolicies and E.GetPolicies(slug) or {})
    local profs = opts.snapshot and opts.snapshot.professions or opts.professions
    local context = E.RouteContext and E.RouteContext(slug, opts, profs)
    opts.targetUnlearned = context and context.unlearned or false
    opts.partnerRequired = context and context.requiresPartner and not context.partnerValid or false
    if context and context.requiresPartner then opts.secondaryProfession = context.partner end
    if opts.scheme == "fishing" then opts.allowSecondaryLeveling=false; opts.secondaryProfession=nil end
    local gates=ns.ProfGates
    local spec=gates and gates.SpecializationContext and gates.SpecializationContext(opts)
    local needsTools=E.HasToolGoals and E.HasToolGoals(slug,opts)
    local needsEssence=ns.ProfEssences and ns.ProfEssences.Enabled(slug,opts,opts.snapshot)
    if opts.scheme~="cheapest" and opts.scheme~="fishing" and
        (needsTools or needsEssence or spec and (#(spec.goals or {})>0 or spec.selectionConflict)) then
        opts.specializationRecipeScore=function(recipe,state,snapshot,incremental)
            local gain=E.Gain(recipe,(state.skill or {})[recipe.profession] or 1)
            if gain<=0 then return math.huge end
            if opts.scheme=="crafts" then return 1/gain end
            if opts.scheme=="optim" then
                local total=0
                for _,m in ipairs(recipe.mats or {}) do total=total+(RA.NPCSellPriceOf(m[1]) or 0)*m[2] end
                return total
            end
            return incremental/gain
        end
    end
    return opts
end
local function signature(slug, opts)
    local start = opts.fromCurrent == false and ("fixed:" .. opts.start) or "current"
    if opts.snapshot then start = tostring(opts.start) end
    local policy = E.PolicyFingerprint and E.PolicyFingerprint(opts.exclusions) or ""
    local sig=table.concat({opts.scheme, tostring(opts.target), start, tostring(opts.onlyAH),
        tostring(opts.noFormula), tostring(opts.learnedOnly), tostring(opts.allowSecondaryLeveling),
        tostring(opts.secondaryProfession), tostring(opts.autoCraftTools), tostring(opts.allowLimitedFormulas),
        tostring(opts.skipUnpricedFormulas), tostring(opts.recoveryEnabled), tostring(opts.recoveryFeePercent),
        tostring(opts.targetUnlearned), RA.SpecSig and RA.SpecSig(slug) or "", policy,learningPolicy()}, "|")
    if opts.snapshot then
        local stock={}
        for id,entry in pairs(opts.executionInventory or {}) do
            stock[#stock+1]=tostring(id)..":"..tostring(type(entry)=="table" and entry.count or entry)
                ..":"..tostring(type(entry)=="table" and entry.usable)
        end
        table.sort(stock)
        sig=sig.."|carry:"..tostring(opts.executionSourcePlanID or "")..":"..table.concat(stock,",")
    end
    return sig
end
local function identity(slug, opts)
    local scope = character() .. "|" .. slug
    if opts.snapshot then scope = scope .. "|" .. tostring(opts.snapshot) end
    return scope .. "|" .. signature(slug, opts), scope
end
local function gate(slug, opts, code)
    return {slug=slug, planVersion=2, executionVersion=1, scheme=opts.scheme, start=opts.start, target=opts.target,
        status=code=="secondaryRequired" and "selection_required" or "recalculate_required", feasible=false,
        steps={},executionSteps={},actions={},mats={},formulas={},gaps={},total=0,crafts=0,
        diagnostics={{code=code}},completeCost=false}
end
local function remember(job, result)
    if job.opts.snapshot or result.status == "searching" then return end
    local db = saved(); if not db then return end
    db.routes[job.signature] = {slug=job.slug, result=copy(result), savedAt=now(), model=MODEL}
    db.active[job.slug] = job.signature
    local entries={}
    for key, row in pairs(db.routes) do
        if type(row)=="table" and row.slug == job.slug then entries[#entries+1]={key=key, stamp=row.savedAt or 0} end
    end
    table.sort(entries, function(a,b) return a.stamp>b.stamp end)
    local kept=1
    for _,entry in ipairs(entries) do
        if entry.key ~= job.signature then
            kept=kept+1; if kept>CACHE_LIMIT then db.routes[entry.key]=nil end
        end
    end
end
local searchFields={"status","expanded","improvements","initialTotal","bestTotal","savings","budgetLimited",
    "searchComplete","searchTermination","searchCpuMs","searchCpuLimitMs","inputModelOptimal",
    "catalogueCoverageComplete","quoteComplete","restrictedReason","searchModel","frontierStates","memoStates",
    "searchFrontierLimit","initialNetTotal","bestNetTotal","netSavings","recoveryOptimized"}
local function updateExecution(job, result)
    local xp=ns.ProfExecution
    if job.opts.snapshot or not xp then return end
    if job.finished and xp.PlanRecalculated then xp.PlanRecalculated(job.slug,result) end
    local frozen=xp.GetPlan and xp.GetPlan(job.slug)
    if not frozen then return end
    if frozen.planID==result.planID or frozen.originPlanID==result.planID then
        local state={running=not job.finished and not job.cancelled}
        for _,key in ipairs(searchFields) do state[key]=result[key] end
        frozen.searchState=state
    else
        local run=xp.GetRun and xp.GetRun(job.slug)
        if run then run.newPlanAvailable=true;run.candidateRevision=result.revision end
    end
end
local function publish(job, result)
    if not result or job.invalid then return end
    local started=debugprofilestop and debugprofilestop()
    revision=revision+1
    result.slug=job.slug;result.revision=revision;result.planID=job.planID;result.routeModel=MODEL
    result.learningPolicyFingerprint=learningPolicy()
    result.executionOptions=copy(job.opts);result.executionOptions.snapshot=nil
    result.stale=job.stale or nil;result.staleReason=job.staleReason
    if RA.StampSpecializations then RA.StampSpecializations(result,job.slug,job.opts,job.snap) end
    result.quoteSignature=RA.QuoteSig and RA.QuoteSig() or ""
    result.cacheSignature=job.signature
    job.published=result;results[job.key]=result;active[job.scope]=job.key
    job.publishedProgressVersion=job.progressVersion
    remember(job,result);updateExecution(job,result)
    for _,fn in ipairs(listeners) do pcall(fn,job.slug,result) end
    if started and S.ChargeExternalWork and job.co then S.ChargeExternalWork(job,math.max(0,debugprofilestop()-started)) end
end
local function release(job)
    job.co=nil;job.snap=nil;job.best=nil;job.partial=nil;job.preview=nil
    job.candidateIndex=nil;job.pump=nil;job.invalid=true
end
local function pump(job)
    if job.invalid or job.cancelled or job.finished then return true end
    local done=S.Run(job,2)
    if job.result and (job.result~=job.published or done) then publish(job,job.result)
    elseif job.published and job.progressVersion~=job.publishedProgressVersion then
        if S.Progress then
            local state=S.Progress(job,job.published)
            for key,value in pairs(state or {}) do job.published[key]=value end
        end
        job.publishedProgressVersion=job.progressVersion
        updateExecution(job,job.published)
        for _,fn in ipairs(progressListeners) do pcall(fn,job.slug,job.published,S.Progress and S.Progress(job,job.published)) end
    end
    if job.hooks and job.hooks.onProgress then
        local api=ns.ProfSolverRun
        pcall(job.hooks.onProgress,job,api and api.State(job),done)
    end
    if done or job.finished then
        if job.hooks and job.hooks.onDone then pcall(job.hooks.onDone,job) end
        if jobs[job.key]==job then jobs[job.key]=nil end
        release(job);return true
    end
    return false
end
local function schedule(job)
    if job.scheduled then return end
    job.scheduled=true
    job.scheduleVersion=(job.scheduleVersion or 0)+1
    local generation=job.scheduleVersion
    local function step()
        if job.scheduleVersion~=generation then return true end
        local done=pump(job)
        if done then job.scheduled=false end
        return done
    end
    job.pump=step
    if ns.IdleJobs and ns.IdleJobs.Add then ns.IdleJobs.Add(step)
    elseif C_Timer and C_Timer.After then
        local function later() if not step() then C_Timer.After(0,later) end end
        C_Timer.After(0,later)
    end
end
local function start(slug, opts, sigOpts)
    local key, scope=identity(slug,sigOpts or opts)
    serial=serial+1
    local db=not opts.snapshot and saved()
    if db then db.nextID=(db.nextID or 0)+1 end
    local id=character()..":route:"..tostring(db and db.nextID or serial)
    if opts.scheme~="cheapest" and not opts.specializationRecipeScore then
        local result=quickCompute(slug,opts)
        if not result then return nil end
        result.status=result.status or "complete"
        local xp=ns.ProfExecution
        if xp and xp.NormalizePlan then result=xp.NormalizePlan(slug,result) or result end
        local job={key=key,scope=scope,slug=slug,signature=signature(slug,sigOpts or opts),opts=opts,planID=id,finished=true}
        publish(job,result);return result
    end
    local job=S.NewJob(slug,opts)
    job.key,job.scope,job.slug,job.planID=key,scope,slug,id
    job.signature=signature(slug,sigOpts or opts)
    jobs[key]=job;active[scope]=key
    local result=S.Result(job,nil,"searching")
    result.slug=slug;result.planID=id;result.cacheSignature=job.signature
    result.learningPolicyFingerprint=learningPolicy()
    job.published=result;results[key]=result
    schedule(job)
    return result
end
function RA.OnPlanChanged(fn) if type(fn)=="function" then listeners[#listeners+1]=fn end end
function RA.OnProgress(fn) if type(fn)=="function" then progressListeners[#progressListeners+1]=fn end end
function RA.Get(slug, supplied)
    local opts=options(slug,supplied)
    if opts.partnerRequired then return gate(slug,opts,"secondaryRequired") end
    local key,scope=identity(slug,opts)
    local xp=not opts.snapshot and ns.ProfExecution
    local frozen,reason
    if xp and xp.GetPlan then frozen,reason=xp.GetPlan(slug) end
    if reason=="historyUnreadable" then return gate(slug,opts,reason) end
    if frozen then
        if frozen.learningPolicyFingerprint~=learningPolicy() then return gate(slug,opts,"learningPolicyChanged") end
        if RA.SpecializationPlanChanged and RA.SpecializationPlanChanged(frozen,slug,opts) then return gate(slug,opts,"specializationChanged") end
        if frozen.cacheSignature and frozen.cacheSignature~=signature(slug,opts) then frozen.stale=true;frozen.settingsChanged=true end
        if frozen.quoteSignature~=(RA.QuoteSig and RA.QuoteSig() or "") then frozen.stale=true end
        if E.AuctionSupplyChanged and E.AuctionSupplyChanged(frozen) then frozen.stale=true end
        return frozen
    end
    local result=results[key]
    if result then
        if not opts.snapshot and result.quoteSignature and result.quoteSignature~=(RA.QuoteSig and RA.QuoteSig() or "") then result.stale=true end
        if not opts.snapshot and E.AuctionSupplyChanged and E.AuctionSupplyChanged(result) then result.stale=true end
        return result
    end
    local selected=active[scope] and results[active[scope]]
    if not opts.snapshot and selected then
        if selected.learningPolicyFingerprint~=learningPolicy() then return gate(slug,opts,"learningPolicyChanged") end
        selected.stale=true;selected.settingsChanged=true;return selected
    end
    local db,cacheError
    if not opts.snapshot then db,cacheError=saved() end
    if cacheError then return gate(slug,opts,cacheError) end
    local record=db and (db.routes[signature(slug,opts)] or db.routes[db.active[slug]])
    if record~=nil and (type(record)~="table" or record.model~=MODEL or type(record.result)~="table"
        or type(record.result.steps)~="table" or record.result.executionSteps~=nil and type(record.result.executionSteps)~="table") then
        return gate(slug,opts,"historyUnreadable")
    end
    if record and record.model==MODEL and type(record.result)=="table" then
        if record.result.learningPolicyFingerprint~=learningPolicy() then return gate(slug,opts,"learningPolicyChanged") end
        result=copy(record.result);result.cached=true
        if result.status=="searching" then result.status="interrupted";result.inFlight=false end
        if record.result.cacheSignature~=signature(slug,opts) then result.stale=true;result.settingsChanged=true end
        if result.quoteSignature~=(RA.QuoteSig and RA.QuoteSig() or "") then result.stale=true end
        results[key]=result;active[scope]=key
        return result
    end
    return start(slug,opts)
end
function RA.Compute(slug, supplied)
    local opts=options(slug,supplied)
    if opts.partnerRequired then return gate(slug,opts,"secondaryRequired") end
    if opts.scheme~="cheapest" and not opts.specializationRecipeScore then return quickCompute(slug,opts) end
    local result,job=S.Compute(slug,opts)
    if result then result.learningPolicyFingerprint=learningPolicy() end
    if RA.StampSpecializations then RA.StampSpecializations(result,slug,opts,job and job.snap) end
    return result,job
end
function RA.Recalculate(slug, supplied)
    local opts=options(slug,supplied);local sigOpts=copy(opts);sigOpts.snapshot=opts.snapshot
    if not opts.snapshot then local _,cacheError=saved();if cacheError then return gate(slug,opts,cacheError) end end
    local xp=not opts.snapshot and ns.ProfExecution
    if xp and xp.PrepareRecalculate then
        local inventory,source,errorCode=xp.PrepareRecalculate(slug)
        if errorCode then return gate(slug,opts,errorCode) end
        if source then
            opts.executionInventory=inventory or {};opts.executionSourcePlanID=source
            local professions=E.Professions and E.Professions() or {}
            opts.start=(professions[slug] or {}).cur or opts.start
        end
    end
    local _,scope=identity(slug,opts)
    for key,job in pairs(jobs) do if job.scope==scope then release(job);jobs[key]=nil end end
    for key in pairs(results) do if key:sub(1,#scope+1)==scope.."|" then results[key]=nil end end
    active[scope]=nil;clearPrices()
    if opts.partnerRequired then return gate(slug,opts,"secondaryRequired") end
    return start(slug,opts,sigOpts)
end
function RA.Invalidate(reason)
    clearPrices()
    reason=type(reason)=="string" and reason or "inputs"
    for _,job in pairs(jobs) do job.stale=true;job.staleReason=reason end
    for _,result in pairs(results) do result.stale=true;result.staleReason=reason end
    local db=saved()
    for _,record in pairs(db and db.routes or {}) do
        if type(record)=="table" and type(record.result)=="table" then record.result.stale=true;record.result.staleReason=reason end
    end
    local xp=ns.ProfExecution
    if xp and xp.GetHistory then
        -- Only current runs need the live stale marker. Archived facts stay frozen.
        for _,slug in ipairs(E.PrimaryOrder or {"alchemy","blacksmithing","cooking","enchanting","engineering","first-aid","leatherworking","mining","tailoring"}) do
            local plan=xp.GetPlan(slug);if plan then plan.stale=true;plan.staleReason=reason end
        end
    end
end
function RA.Pump(slug)
    for _,job in pairs(jobs) do if not slug or job.slug==slug then pump(job) end end
end
function RA.Peek(slug)
    if slug then
        local scope=character().."|"..slug
        return active[scope] and results[active[scope]]
    end
    for _,job in pairs(jobs) do if not job.invalid then return job.published end end
end
function RA.HasWork(slug)
    for _,job in pairs(jobs) do if (not slug or job.slug==slug) and not job.cancelled and not job.finished and not job.invalid then return true end end
    return false
end
function RA.Cancel(slug)
    local changed=false
    for _,job in pairs(jobs) do
        if (not slug or job.slug==slug) and not job.finished and not job.invalid then
            job.cancelled=true;job.status="stopped";job.searchTermination="user_stopped";job.scheduled=false;job.scheduleVersion=(job.scheduleVersion or 0)+1
            local result=job.published
            if result then result.status="stopped";result.inFlight=false;result.searchTermination="user_stopped";publish(job,result) end
            changed=true
        end
    end
    return changed
end
function RA.Continue(slug)
    for _,job in pairs(jobs) do
        if (not slug or job.slug==slug) and job.cancelled and not job.finished and not job.invalid then
            job.cancelled=false;job.status="searching";job.searchTermination=nil
            if job.published then job.published.status="searching";job.published.searchTermination=nil end
            schedule(job)
        end
    end
end
function RA.ReleaseExecution(slug)
    for key,job in pairs(jobs) do if job.slug==slug then
        job.status="stopped";job.cancelled=true;job.searchTermination="execution_ended"
        local result=job.published
        if result then result.status="stopped";result.inFlight=false;result.searchTermination="execution_ended";publish(job,result) end
        release(job);jobs[key]=nil
    end end
end
function RA.EndExecution(slug)
    local xp=ns.ProfExecution
    local run,reason
    if xp and xp.End then run,reason=xp.End(slug,"ended") end
    RA.ReleaseExecution(slug)
    return run,reason
end
function RA.PlanSig(slug, opts) return signature(slug,options(slug,opts)) end
RA.Start=RA.Get
-- Preserve the dev precision API while sharing the route facade's jobs.
local run=ns.ProfSolverRun
if run then
    run.Running=RA.HasWork
    run.Stop=RA.Cancel
    run.Result=function(job)
        job=job or legacyRun and legacyRun.job
        if job then return job.result or job.published end
        return RA.Peek(ns.ProfModule and ns.ProfModule.cur)
    end
    run.Active=function()
        for _,job in pairs(jobs) do if not job.finished and not job.invalid and not job.cancelled then return {job=job,slug=job.slug} end end
    end
    run.State=function(job)
        if not job then local entry=run.Active();job=entry and entry.job end
        local phase,fraction=run.Stamp(job)
        return {phase=phase,fraction=fraction,seedSkill=job and job.seedSkill,target=job and job.target,
            expanded=job and job.expanded,cpuUsed=job and job.cpuUsed,cpuLimitMs=job and job.cpuLimitMs,status=job and job.status}
    end
    run.Start=function(slug,opts,hooks)
        local supplied=opts
        opts=copy(opts or RA.OptionsFor(slug));opts.cpuLimitMs=opts.cpuLimitMs or 8000
        if supplied and supplied.snapshot then opts.snapshot=supplied.snapshot end
        local result=RA.Recalculate(slug,opts)
        local key=identity(slug,options(slug,opts))
        local job=jobs[key] or {slug=slug,result=result,published=result,finished=true}
        job.hooks=hooks
        legacyRun={job=job,slug=slug,hooks=hooks}
        if job.finished and hooks and hooks.onDone then pcall(hooks.onDone,job) end
        return legacyRun
    end
end
local function initialize()
    local bridge=ns.AuctionBridge
    if bridge and bridge.OnChanged then bridge.OnChanged(function(_,reason)
        if reason=="prices" or reason=="supply" then RA.Invalidate(reason) end
    end) end
    local frame=CreateFrame and CreateFrame("Frame")
    if frame then
        frame:RegisterEvent("PLAYER_LOGOUT")
        frame:SetScript("OnEvent",function()
            for _,job in pairs(jobs) do
                local result=job.published
                if result and #(result.steps or {})>0 then
                    local stored=copy(result);stored.status="interrupted";stored.inFlight=false
                    remember(job,stored)
                end
            end
        end)
    end
end
if ns.Init then ns.Init(initialize) else initialize() end
