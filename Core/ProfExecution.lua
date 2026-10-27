-- Persistent execution facts, adapted to the dev Core data and ProfTrack APIs.
-- The main addon owns loading and DungeonsForeverDB.prof remains the sole store.
local _, ns = ...

-- Use the shared storage facade; standalone domain fixtures may supply
-- the same profession subtree without loading the native core.
if not ns.ProfessionDB then
    function ns.ProfessionDB(create)
        if ns.ProfessionStorage then return ns.ProfessionStorage.Get(create) end
        local db=DungeonsForeverDB
        if type(db)~="table" then
            if create==false then return nil end
            db={};DungeonsForeverDB=db
        end
        if type(db.prof)~="table" then
            if create==false then return nil end
            db.prof={}
        end
        return db.prof
    end
end
if not ns.ProfessionTrackingEnabled then
    function ns.ProfessionTrackingEnabled()
        return not ns.ProfessionTracking or ns.ProfessionTracking.IsEnabled()
    end
end
if not ns.LoadForeverPages then return end
local E, S = ns.ProfEconomy, ns.ProfRouteSolver
local XP = {}; ns.ProfExecution = XP
local listeners, observationListeners, jobs, early = {}, {}, {}, {}
local creditCaches = setmetatable({}, {__mode="k"})
local recentCaches = setmetatable({}, {__mode="k"})
local registeredHistory = setmetatable({}, {__mode="k"})
local performance = {creditBuilds=0,historyScans=0,recentBuilds=0}
local observationTimer, completionTimer, observationGeneration = false, false, 0
local observedActive, observedReceipts
local upgradeLegacy
local floor, ceil, max, min = math.floor, math.ceil, math.max, math.min
local function now() return time and time() or 0 end
local function integer(n) return type(n)=="number" and n>=0 and n==floor(n) and n<math.huge end
local function copy(v, seen)
    if type(v)~="table" then if type(v)~="function" and type(v)~="userdata" then return v end; return end
    if ns.ProfPlanStore then ns.ProfPlanStore.Materialize(v) end
    seen=seen or {}; if seen[v] then return end
    seen[v]=true; local out={}
    for k,x in pairs(v) do if type(k)=="string" or type(k)=="number" then out[k]=copy(x,seen) end end
    seen[v]=nil; return out
end
local function character() return E and E.CharacterKey and E.CharacterKey() or ((UnitName and UnitName("player") or "?").."-"..(GetRealmName and GetRealmName() or "?")) end
local function db()
    local prof=ns.ProfessionDB();prof.track=prof.track or {}
    local key=character(); local c=prof.track[key]
    if type(c)~="table" or c.version~=1 then c={version=1,nextID=0,nextAttempt=0,active={},runs={},seen={},order={},preparing={}}; prof.track[key]=c end
    if upgradeLegacy and not c.devExecutionMigration then
        for _,run in pairs(c.runs or {}) do if not run.plan and type(run.steps)=="table" then upgradeLegacy(run,c) end end
        c.devExecutionMigration=1
    end
    c.seen=c.seen or {};c.order=c.order or {}
    c.active=c.active or {}; c.runs=c.runs or {}; c.preparing=c.preparing or {}; c.seenCasts=c.seenCasts or {}; c.castOrder=c.castOrder or {}
    c.seenReceipts=c.seenReceipts or {}; c.receiptOrder=c.receiptOrder or {}
    c.continuation=c.continuation or {};c.recentRunIDs=c.recentRunIDs or {};c.endedContracts=c.endedContracts or {}
    if c.receiptWindowVersion~=1 then
        -- Upgrade once without opening any historical plan. Persisting this
        -- tiny index lets reloads resume only the finite late-receipt window.
        local at=now();c.receiptUntil=0
        for id,run in pairs(c.runs) do
            for _,p in pairs(run.progress or {}) do for _,a in ipairs(p.attempts or {}) do
                if type(a.at)=="number" and a.at<=at+2 and a.at+15>=at then
                    c.recentRunIDs[id]=max(c.recentRunIDs[id] or 0,a.at+15)
                    c.receiptUntil=max(c.receiptUntil,a.at+15)
                end
            end end
        end
        c.receiptWindowVersion=1
    end
    if ns.ProfHistory and not registeredHistory[c] then
        registeredHistory[c]=true
        for _,run in pairs(c.runs) do ns.ProfHistory.RegisterRun(run) end
    end
    return c
end
local function remember(set,order,key,limit)
    if not key then return false end
    if set[key] then return true end
    set[key]=true; order[#order+1]=key
    while #order>limit do set[table.remove(order,1)]=nil end
    return false
end
local function steps(plan) return plan and (plan.executionSteps or plan.steps) or {} end
local function readablePlan(run)
    local plan=run and run.plan
    if type(plan)=="table" and rawget(plan,"__dfHistory")==nil and rawget(plan,"__dfPlan")==nil
        and (plan.executionVersion==nil or plan.executionVersion==1)
        and type(plan.executionSteps or plan.steps)=="table" then return plan end
    if run and not run.historyError then run.historyError="history:unreadable_plan" end
    return nil,"historyUnreadable"
end
function XP.IsSpecializationQuest(seg) return seg and seg.kind=="specialization_quest" end
function XP.SpecializationQuest(seg) return seg and (seg.quest or seg.specializationGoal or seg.goal or seg) or {} end
function XP.IsConversion(seg) return seg and (seg.kind=="essence_conversion" or seg.kind=="conversion") end
local function catalogueAllowed(plan)
    for _,segment in ipairs(steps(plan)) do
        local spell=segment.spell or segment[3]
        if type(spell)=="number"and spell>0 and not XP.IsConversion(segment) and not XP.IsSpecializationQuest(segment)
            and not (segment.recipe and segment.recipe.spell==spell)
            and not (E and E.FindRecipe and E.FindRecipe(segment.profession or plan.slug,spell)) then return false end
    end
    return true
end
function XP.Conversion(seg)
    if not XP.IsConversion(seg) then return end
    local c=seg.conversion or {}
    local input=c.inputItemID or seg.sourceItem
    local output=c.outputItemID or seg.targetItem or seg.item
    local inputCount=c.inputCount or seg.sourcePerConversion
    local outputCount=c.outputCount or seg.targetPerConversion or seg.outputMin
    if not integer(input) or input<=0 or not integer(output) or output<=0 or input==output
        or not integer(inputCount) or inputCount<=0 or not integer(outputCount) or outputCount<=0 then return end
    local current=ns.ProfEssences and ns.ProfEssences.ForItem(output)
    if current and current.status=="confirmed" and (current.outputItemID~=output
        or current.inputCount~=inputCount or current.outputCount~=outputCount) then return end
    return {inputItemID=input,inputCount=inputCount,outputItemID=output,outputCount=outputCount}
end
local function specializationChanged(plan,slug)
    local ra=ns.ProfRouteAuto
    return ra and (ra.SpecializationPlanChanged and ra.SpecializationPlanChanged(plan,slug)
        or ra.ToolPolicyChanged and ra.ToolPolicyChanged(plan,slug))
end
local function validatedPlan(plan,slug)
    local ra=ns.ProfRouteAuto
    if ra and ra.ValidateVendorQuotes then plan=ra.ValidateVendorQuotes(plan) end
    if ra and ra.ValidateSpecializationPlan then plan=ra.ValidateSpecializationPlan(plan,slug) end
    return plan
end
local function skill(slug,snapshot)
    local all=snapshot or E and E.Professions and E.Professions()
    if all and all[slug] then return all[slug].cur end
    local pd=ns.ProfModule; all=pd and pd.ProfLearned and pd.ProfLearned()
    return all and all[slug] and all[slug].cur
end
local function quotaMap(value)
    local out={}
    for k,v in pairs(type(value)=="table" and value or {}) do
        if type(v)=="table" then local id=v.id or v.itemID or v[1];local n=v.count or v.quantity or v[2];if integer(id) and id>0 and integer(n) then out[id]=(out[id] or 0)+n end
        elseif integer(tonumber(k)) and tonumber(k)>0 and integer(v) then out[tonumber(k)]=v end
    end
    return out
end
local function requiredOutputs(seg)
    local required=quotaMap(seg.requiredOutputs)
    local c=XP.Conversion(seg)
    if c and next(required)==nil then required[c.outputItemID]=c.outputCount*ceil(seg.expectedCrafts or seg[4] or 0) end
    return required
end
local function recipe(seg,slug)
    if XP.IsSpecializationQuest(seg) then return {mats=XP.SpecializationQuest(seg).inputs or {}} end
    if XP.IsConversion(seg) then
        local c=XP.Conversion(seg)
        return c and {mats={{c.inputItemID,c.inputCount}},item=c.outputItemID,count=c.outputCount,
            outputMin=c.outputCount,outputMax=c.outputCount,spell=0,profession=seg.profession or slug} or {}
    end
    return seg.recipe or (E and E.FindRecipe and E.FindRecipe(seg.profession or slug,seg[3])) or {}
end
local function segment(run,id)
    local plan=readablePlan(run);if not plan then return end
    if type(id)=="number" then return steps(plan)[id],id end
    if not id then local i=run.currentIndex or 1;return steps(plan)[i],i end
    for i,x in ipairs(steps(plan)) do if x.segmentID==id or x.actionID==id then return x,i end end
end
local function progressRecord(run,seg)
    local id=seg.segmentID; local p=run.progress[id]
    if not p then p={casts=0,attempts={},manualOutputs={}};run.progress[id]=p end
    p.attempts=p.attempts or {};p.manualOutputs=p.manualOutputs or {}
    return p
end
function XP.OnChanged(fn) if type(fn)=="function" then listeners[#listeners+1]=fn end end
function XP.OnObservationChanged(fn) if type(fn)=="function" then observationListeners[#observationListeners+1]=fn end end
local function invalidateCredits(run)
    creditCaches[run]=nil
    run.creditVersion=(run.creditVersion or 0)+1
end
local function referencesChanged()
    local ra=ns.ProfRouteAuto
    if ra and ra.CacheReferencesChanged then ra.CacheReferencesChanged(character()) end
end
local function changed(run,lifecycleReason)
    -- Fact writers invalidate before Sync. Notifying views must not discard the
    -- allocation ledger that Sync just built for those same facts.
    run.progressVersion=(run.progressVersion or 0)+1;run.updatedAt=now()
    if ns.ProfHistory then
        if ns.ProfHistory.FactsChanged then ns.ProfHistory.FactsChanged(run)
        else ns.ProfHistory.Touch(run) end
    end
    referencesChanged()
    -- A late receipt remains an execution fact even if its archived plan can
    -- no longer be decoded. Keep the last derived ledger until it can be rebuilt.
    if XP.GetRecipeTotals and readablePlan(run) then
        run.byRecipe=XP.GetRecipeTotals(run.slug,run.planID,true)
        run.byRecipeVersion=run.progressVersion
        local ledger={confirmed={},guaranteed={},consumed={},allocated={}}
        for _,entry in ipairs(run.byRecipe) do
            for item,n in pairs(entry.confirmedOutputs) do ledger.confirmed[item]=(ledger.confirmed[item] or 0)+n end
            for item,n in pairs(entry.guaranteedOutputs) do ledger.guaranteed[item]=(ledger.guaranteed[item] or 0)+n end
        end
        for _,seg in ipairs(steps(run.plan)) do
            local record=progressRecord(run,seg)
            local casts=XP.IsSpecializationQuest(seg) and (record.questCompleted and 1 or 0) or record.casts or 0
            for _,m in ipairs(recipe(seg,run.slug).mats or {}) do ledger.consumed[m[1]]=(ledger.consumed[m[1]] or 0)+m[2]*casts end
            -- Manual conversions are material facts, never recipe casts. They
            -- are omitted from byRecipe but still belong to this same ledger.
            if XP.IsConversion(seg) then for _,a in ipairs(record.attempts) do
                if a.item and integer(a.actual) then
                    ledger.confirmed[a.item]=(ledger.confirmed[a.item] or 0)+a.actual
                    ledger.guaranteed[a.item]=(ledger.guaranteed[a.item] or 0)+a.actual
                end
            end end
            for item,n in pairs(requiredOutputs(seg)) do ledger.allocated[item]=(ledger.allocated[item] or 0)+n end
        end
        run.materialLedger=ledger
    end
    for _,fn in ipairs(listeners) do pcall(fn,run.slug,run,lifecycleReason) end
end
function XP.PerformanceCounters()
    return {creditBuilds=performance.creditBuilds,historyScans=performance.historyScans,recentBuilds=performance.recentBuilds}
end
function XP.GetRun(slug) local c=db();return c.runs[c.active[slug]] end
XP.GetActive=XP.GetRun
function XP.HasActive(slug)
    local c=db()
    if slug then local run=c.runs[c.active[slug]];return run~=nil and run.status=="active" end
    for _,id in pairs(c.active) do local run=c.runs[id];if run and run.status=="active" then return true end end
    return false
end
function XP.IsPreparing(slug) return db().preparing[slug]~=nil end
function XP.GetPlan(slug) local run=XP.GetRun(slug);if run then return readablePlan(run) end end
function XP.CurrentPlan()
    local slug = db().trackingSlug
    return slug and XP.GetPlan(slug) or nil
end
function XP.GetHistory(slug)
    local c=db();local list={}
    for _,run in pairs(c.runs) do if run.slug==slug then list[#list+1]=run end end
    table.sort(list,function(a,b)
        if (a.status=="active")~=(b.status=="active") then return a.status=="active" end
        if a.createdAt~=b.createdAt then return (a.createdAt or 0)>(b.createdAt or 0) end
        return a.planID>b.planID
    end)
    return list
end
function XP.NormalizePlan(slug,result)
    if type(result)=="table" and (rawget(result,"__dfHistory")~=nil or rawget(result,"__dfPlan")~=nil) then return nil,"historyUnreadable" end
    if type(result)~="table" then return nil,"pending" end
    if (result.executionVersion~=nil and result.executionVersion~=1)
        or (result.executionSteps~=nil and type(result.executionSteps)~="table")
        or (result.steps~=nil and type(result.steps)~="table") then return nil,"historyUnreadable" end
    if result.executionVersion==1 then return result end
    local out=copy(result);out.executionVersion=1;out.executionSteps={}
    for i,raw in ipairs(result.executionSteps or result.steps or {}) do
        local seg=copy(raw);local rec=recipe(seg,slug)
        if seg[3]~=0 and not rec.spell then return nil,"migration_required" end
        seg.profession=seg.profession or slug;seg.recipe=copy(rec)
        seg.segmentID=seg.segmentID or ("legacy:"..seg.profession..":"..tostring(seg[3])..":"..i)
        seg.goalSkill=seg[2];seg.expectedGain=max(0,(seg[2] or 0)-(seg[1] or 0))
        seg.expectedCrafts=seg[4] or 0;seg.attemptLimit=seg.expectedCrafts
        seg.requiredOutputs=quotaMap(raw.requiredOutputs);seg.materialMinCrafts=raw.materialMinCrafts or 0;seg.allocations=copy(raw.allocations or {})
        if seg.expectedGain<=0 and not seg.checkpoint and next(seg.requiredOutputs)==nil and rec.item then
            seg.requiredOutputs[rec.item]=(rec.count or 1)*seg.expectedCrafts;seg.materialMinCrafts=seg.expectedCrafts
        end
        if XP.IsConversion(seg) and next(seg.requiredOutputs)==nil and rec.item then seg.requiredOutputs[rec.item]=(rec.count or 0)*seg.expectedCrafts end
        seg.outputMin=rec.outputMin or rec.count or 1;seg.outputMax=rec.outputMax or seg.outputMin
        out.executionSteps[#out.executionSteps+1]=seg
    end
    if not out.steps then out.steps=out.executionSteps end
    return out
end
local function ready(result)
    return result and result.feasible~=false and result.status~="selection_required" and result.status~="recalculate_required" and #steps(result)>0
end
local function originSignature(plan)
    -- Legacy/fixed candidates have no persisted plan ID. Compare their small
    -- execution contract so merely redisplaying that same cache cannot restart
    -- a terminal run. New solver plans use their explicit ID instead.
    local parts={}
    local function field(value) local text=type(value)..":"..tostring(value);parts[#parts+1]=#text..":"..text end
    for _,key in ipairs({"mode","revision","total","targetSkill","startSkill"}) do field(plan and plan[key]) end
    for _,seg in ipairs(steps(plan)) do
        for i=1,4 do field(seg[i]) end
        for _,key in ipairs({"segmentID","actionID","profession","kind","goalSkill","expectedCrafts","attemptLimit"}) do field(seg[key]) end
        if XP.IsConversion(seg) then
            local c=XP.Conversion(seg) or {}
            for _,key in ipairs({"inputItemID","inputCount","outputItemID","outputCount"}) do field(c[key]) end
        end
        local quotas=quotaMap(seg.requiredOutputs);local ids={};for id in pairs(quotas) do ids[#ids+1]=id end;table.sort(ids)
        field(#ids);for _,id in ipairs(ids) do field(id);field(quotas[id]) end
    end
    return table.concat(parts)
end
local function archive(c,slug,reason)
    local run=c.runs[c.active[slug]]
    if run then
        run.status="archived";run.archivedAt=now();run.archiveReason=reason or "recalculate"
        if ns.ProfHistory then ns.ProfHistory.RegisterRun(run) end
    end
    c.active[slug]=nil
    if c.trackingSlug==slug then c.trackingSlug=nil end
    return run
end
function XP.End(slug,reason)
    local c=db();local run=XP.GetRun(slug)
    -- Cancelling a replacement must not let its eventual solver publication
    -- turn the archived source back into an active execution.
    local preparing=c.preparing[slug]
    if not run and preparing and preparing.sourcePlanID then run=c.runs[preparing.sourcePlanID] end
    c.preparing[slug]=nil
    if not run then
        c.active[slug]=nil;if c.trackingSlug==slug then c.trackingSlug=nil end
        if preparing and (preparing.sourcePlanID or type(preparing.inventory)=="table" and next(preparing.inventory)) then
            -- Keep the entire carry evidence when an old/corrupt save lost its
            -- source run. Ending observation must never silently discard it.
            c.continuation[slug]=copy(preparing);c.continuation[slug].missingSource=true
            c.continuation[slug].endedAt=c.continuation[slug].endedAt or now()
        end
        referencesChanged()
        if XP.RefreshObservation then XP.RefreshObservation() end
        local source=c.continuation[slug];return source and c.runs[source.sourcePlanID] or true
    end
    local job=jobs[run.planID]
    if job then
        job.cancelled=true;job.state.inFlight=false;job.state.status="cancelled";jobs[run.planID]=nil
    end
    archive(c,slug,reason or "ended")
    run.status="archived";run.archivedAt=run.archivedAt or now();run.archiveReason=reason or "ended"
    run.endedAt=run.endedAt or now();run.completionDue=nil
    c.continuation[slug]={sourcePlanID=run.planID}
    if run.originSignature then
        c.endedContracts[slug]=c.endedContracts[slug] or {};c.endedContracts[slug][run.originSignature]=run.planID
    end
    if c.trackingSlug==slug then c.trackingSlug=nil end
    changed(run,"ended")
    if XP.RefreshObservation then XP.RefreshObservation() end
    return run
end
function XP.Bind(slug,result,opts)
    if ns.ProfessionTracking and not ns.ProfessionTracking.IsEnabled() then ns.ProfessionTracking.SetEnabled(true) end
    local ra=ns.ProfRouteAuto
    local active=XP.GetRun(slug)
    if active and not readablePlan(active) then return nil,"historyUnreadable" end
    if type(result)=="table" and (rawget(result,"__dfHistory")~=nil or rawget(result,"__dfPlan")~=nil) then return nil,"historyUnreadable" end
    if ra and ra.ToolPolicyChanged and (ra.ToolPolicyChanged(result,slug) or active and ra.ToolPolicyChanged(active.plan,slug)) then return nil,"toolPolicyChanged" end
    if ra and ra.VendorQuotesChanged and ra.VendorQuotesChanged(result) then return nil,"vendorQuoteChanged" end
    if result and result.status=="recalculate_required" then
        for _,diagnostic in ipairs(result.diagnostics or {}) do
            if diagnostic.code=="specializationChanged" or diagnostic.code=="specializationFixed" then return nil,"specializationChanged" end
        end
        return nil,"pending"
    end
    if specializationChanged(result,slug) or (result and (result.specializationBlocked==true
        or result.specializationGoalRequired or (type(result.specializationBlocked)=="table" and #result.specializationBlocked>0))) then
        return nil,"specializationChanged"
    end
    opts=opts or {};local c=db();local existing=XP.GetRun(slug)
    if not existing and not opts.force then
        local id=result and (result.planID or result.executionPlanID)
        if not id and c.endedContracts[slug] and c.endedContracts[slug][originSignature(result)] then return nil,"executionEnded" end
        local terminal=id and c.runs[id]
        if terminal and terminal.endedAt then return nil,"executionEnded" end
        local source=c.continuation[slug];terminal=source and c.runs[source.sourcePlanID]
        if terminal and terminal.endedAt and ((id and (id==terminal.originPlanID or id==terminal.planID))
            or not id and terminal.originSignature and terminal.originSignature==originSignature(result)) then return nil,"executionEnded" end
    end
    if existing and not opts.force then
        if not catalogueAllowed(existing.plan) then return nil,"catalogueFiltered" end
        if specializationChanged(existing.plan,slug) then return nil,"specializationChanged" end
        c.trackingSlug=slug
        if XP.RefreshObservation then XP.RefreshObservation() end
        if ready(result) and result~=existing.plan and result.revision~=existing.plan.revision then existing.newPlanAvailable=true;existing.candidateRevision=result.revision end
        return existing
    end
    local normalized,reason=XP.NormalizePlan(slug,result)
    if not normalized then return nil,reason end
    if not catalogueAllowed(normalized) then return nil,"catalogueFiltered" end
    if not ready(normalized) then return nil,"pending" end
    if existing then archive(c,slug,"replace") end
    c.nextID=(c.nextID or 0)+1
    local planID=normalized.planID or normalized.executionPlanID or (character()..":track:"..c.nextID)
    if c.runs[planID] then planID=planID..":"..c.nextID end
    local plan=copy(normalized);plan.planID=planID;plan.executionPlanID=planID
    local ids={}
    for i,seg in ipairs(steps(plan)) do
        local old=seg.segmentID or seg.actionID or ("segment:"..i)
        local id=old:sub(1,#planID+1)==planID..":" and old or planID..":"..old
        ids[old]=id;seg.segmentID=id;seg.actionID=id
    end
    for _,seg in ipairs(steps(plan)) do for _,a in ipairs(seg.allocations or {}) do if ids[a.consumerID] then a.consumerID=ids[a.consumerID] end end end
    for _,row in ipairs(plan.steps or {}) do for i,id in ipairs(row.segmentIDs or {}) do row.segmentIDs[i]=ids[id] or id end end
    local run={planID=planID,id=planID,originPlanID=normalized.planID or normalized.executionPlanID,
        originSignature=not (normalized.planID or normalized.executionPlanID) and originSignature(result) or nil,
        slug=slug,plan=plan,status="active",createdAt=now(),updatedAt=now(),progressVersion=0,
        currentIndex=1,step=1,attemptsDone=0,progress={},supplements={},inheritedInventory=copy(plan.seedInventory or opts.executionInventory
            or c.preparing[slug] and c.preparing[slug].inventory or {}),
        inheritedFrom=plan.executionSourcePlanID or plan.executionOptions and plan.executionOptions.executionSourcePlanID
            or opts.executionSourcePlanID or c.preparing[slug] and c.preparing[slug].sourcePlanID}
    c.runs[planID]=run;c.active[slug]=planID;c.trackingSlug=slug;c.preparing[slug]=nil
    XP.Sync(slug);changed(run);if XP.RefreshObservation then XP.RefreshObservation() end;return run
end
XP.Start=XP.Bind
function XP.StartNew(slug,result,opts)
    opts=copy(opts or {});opts.force=true
    return XP.Bind(slug,result,opts)
end
local function outputFacts(run,seg)
    local p=progressRecord(run,seg);local rec=recipe(seg,run.slug)
    local confirmed,guaranteed={},{};local pending=0
    local output=seg.item or rec.item or rec.makes
    for _,a in ipairs(p.attempts) do
        local item=a.item or output
        if item then
            local n=a.actual
            if integer(n) then confirmed[item]=(confirmed[item] or 0)+n;guaranteed[item]=(guaranteed[item] or 0)+n
            else guaranteed[item]=(guaranteed[item] or 0)+(a.minimum or 0);pending=pending+1 end
        end
    end
    for item,value in pairs(p.manualOutputs) do
        local n=type(value)=="table" and value.total or value
        if type(value)=="table" then
            local actual,lower=0,0
            for _,a in ipairs(p.attempts) do if a.item==item and a.sequence>(value.throughSequence or 0) then actual=actual+(a.actual or 0);lower=lower+(a.actual or a.minimum or 0) end end
            confirmed[item]=n+actual;guaranteed[item]=n+lower
        else confirmed[item]=n;guaranteed[item]=n end
    end
    pending=0
    for _,a in ipairs(p.attempts) do
        local item=a.item or output;local manual=item and p.manualOutputs[item]
        if item and a.actual==nil and not (type(manual)=="table" and a.sequence<=(manual.throughSequence or 0)) then pending=pending+1 end
    end
    return confirmed,guaranteed,pending,output
end
-- A quota stays fulfilled when its assigned consumer uses the output. If an
-- earlier or extra craft spends output reserved for another obligation, that
-- obligation must be replenished instead of counting the gross output again.
local function creditsFor(run,target)
    local cached=creditCaches[run]
    if cached and cached._version==(run.creditVersion or 0) and cached[target.segmentID] then
        local o=cached[target.segmentID];return o.borrowed,o.borrowedActual,o.credited,o.actual,o.diverted,o.waived
    end
    performance.creditBuilds=performance.creditBuilds+1
    local obligations,bySegment,events,stock={},{},{},{}
    for index,seg in ipairs(steps(run.plan)) do
        local o={seg=seg,index=index,required=requiredOutputs(seg),credited={},actual={},borrowed={},borrowedActual={},destinations={},explicit={},diverted={},waived={}}
        obligations[#obligations+1]=o;bySegment[seg.segmentID]=o
        for _,a in ipairs(seg.allocations or {}) do
            local item=a.itemID;local n=a.count or 0
            if item and n>0 then
                o.explicit[item]=true;o.destinations[item]=o.destinations[item] or {}
                o.destinations[item][a.consumerID]=(o.destinations[item][a.consumerID] or 0)+n
            end
        end
        local record=progressRecord(run,seg);local covered={}
        if XP.IsSpecializationQuest(seg) and record.questCompleted and record.questSequence then
            events[#events+1]={sequence=record.questSequence,owner=o,ordinal=1,quest=true}
        end
        for item,value in pairs(record.manualOutputs) do
            if type(value)=="table" then
                local entries={};for _,a in ipairs(record.attempts) do if a.item==item and a.sequence<=(value.throughSequence or 0) then entries[#entries+1]=a end end
                local remaining=value.total
                for i,a in ipairs(entries) do
                    local n=i==#entries and remaining or min(remaining,a.actual or a.minimum or 0)
                    covered[a.sequence]=max(0,n);remaining=max(0,remaining-n)
                end
            end
        end
        for ordinal,a in ipairs(record.attempts) do
            local confirmed=covered[a.sequence]
            if confirmed==nil then confirmed=a.actual end
            events[#events+1]={sequence=a.sequence,attempt=a,owner=o,ordinal=ordinal,quantity=confirmed or a.minimum or 0,confirmed=confirmed~=nil}
        end
    end
    table.sort(events,function(a,b) return a.sequence<b.sequence end)
    local function produce(event)
        local a,o=event.attempt,event.owner;local item=a.item;if not item then return end
        local remaining=event.quantity;stock[item]=stock[item] or {}
        for _,candidate in ipairs(obligations) do
            if candidate.index>=o.index and (candidate.seg.profession or run.slug)==(o.seg.profession or run.slug) then
                local n=min(remaining,max(0,(candidate.required[item] or 0)-(candidate.credited[item] or 0)-(candidate.waived[item] or 0)))
                if n>0 then
                    local actual=event.confirmed and n or 0;local borrowed=candidate~=o
                    candidate.credited[item]=(candidate.credited[item] or 0)+n;candidate.actual[item]=(candidate.actual[item] or 0)+actual
                    if borrowed then candidate.borrowed[item]=(candidate.borrowed[item] or 0)+n;candidate.borrowedActual[item]=(candidate.borrowedActual[item] or 0)+actual end
                    stock[item][#stock[item]+1]={owner=candidate,count=n,actual=actual,borrowed=borrowed};remaining=remaining-n
                end
                if remaining<=0 then break end
            end
        end
        if remaining>0 then stock[item][#stock[item]+1]={count=remaining,actual=event.confirmed and remaining or 0} end
    end
    local function consume(event,item,quantity)
        local lots=stock[item] or {};local consumer=event.owner
        local function take(lot,n,legitimate)
            local actual=min(n,lot.actual or 0);lot.count=lot.count-n;lot.actual=max(0,(lot.actual or 0)-actual)
            local o=lot.owner
            if o and not legitimate then
                o.credited[item]=(o.credited[item] or 0)-n;o.actual[item]=max(0,(o.actual[item] or 0)-actual)
                o.diverted[item]=(o.diverted[item] or 0)+n
                if lot.borrowed then o.borrowed[item]=(o.borrowed[item] or 0)-n;o.borrowedActual[item]=max(0,(o.borrowedActual[item] or 0)-actual) end
            end
            quantity=quantity-n
        end
        -- Prefer the exact allocation. Legacy/simple contracts can infer only
        -- ordinary forward consumption within the originally funded allowance.
        for _,lot in ipairs(lots) do
            local o=lot.owner;local allowed=0
            if o and o.explicit[item] then allowed=o.destinations[item][consumer.seg.segmentID] or 0
            elseif o and o.index<consumer.index then
                local record=progressRecord(run,consumer.seg)
                if event.quest or event.ordinal<=ceil((consumer.seg.expectedCrafts or consumer.seg[4] or 0)+(record.supplementAllowance or 0)-1e-9) then allowed=quantity end
            end
            local n=min(quantity,lot.count,allowed)
            if n>0 then
                take(lot,n,true)
                if o.explicit[item] then o.destinations[item][consumer.seg.segmentID]=allowed-n end
            end
            if quantity<=0 then return end
        end
        for _,lot in ipairs(lots) do if not lot.owner then local n=min(quantity,lot.count);if n>0 then take(lot,n,true) end;if quantity<=0 then return end end end
        for _,lot in ipairs(lots) do local n=min(quantity,lot.count);if n>0 then take(lot,n,false) end;if quantity<=0 then return end end
    end
    local function releaseAllocation(consumer,item,quantity)
        for _,o in ipairs(obligations) do
            local destinations=o.destinations[item]
            if destinations and destinations[consumer.seg.segmentID]~=nil then o.taskResolved=true end
            local allocated=destinations and destinations[consumer.seg.segmentID] or 0
            local released=min(quantity,allocated)
            if released>0 then
                destinations[consumer.seg.segmentID]=allocated-released
                local unmet=max(0,(o.required[item] or 0)-(o.credited[item] or 0)-(o.waived[item] or 0))
                o.waived[item]=(o.waived[item] or 0)+min(released,unmet)
                quantity=quantity-released
            end
            if quantity<=0 then break end
        end
    end
    for _,event in ipairs(events) do
        for _,m in ipairs(recipe(event.owner.seg,run.slug).mats or {}) do consume(event,m[1],m[2]) end
        if event.quest then
            -- The player may have handed in items obtained outside this route.
            -- Resolve only that task's remaining allocations, never fabricate
            -- production receipts or consume future output.
            for _,m in ipairs(recipe(event.owner.seg,run.slug).mats or {}) do releaseAllocation(event.owner,m[1],m[2]) end
        else produce(event) end
    end
    -- Release unused input allocations of material-only producers whose demand
    -- was removed by the task. Walk backwards through the production DAG so
    -- task-only upstream materials are not crafted again either.
    for index=#obligations,1,-1 do
        local o=obligations[index];local seg=o.seg
        if o.taskResolved and not XP.IsSpecializationQuest(seg) and not seg.checkpoint and (seg.expectedGain or 0)<=0 then
            local rec=recipe(seg,run.slug);local record=progressRecord(run,seg)
            local output=seg.item or rec.item;local per=seg.outputMin or rec.outputMin or rec.count or 1
            local needed=0
            for item,n in pairs(o.required) do
                local left=max(0,n-(o.credited[item] or 0)-(o.waived[item] or 0))
                if left>0 then needed=max(needed,item==output and per>0 and ceil(left/per) or math.huge) end
            end
            local funded=max(0,ceil((seg.expectedCrafts or seg[4] or 0)+(record.supplementAllowance or 0))-(record.casts or 0))
            local unused=max(0,funded-needed)
            if unused>0 then for _,m in ipairs(rec.mats or {}) do releaseAllocation(o,m[1],m[2]*unused) end end
        end
    end
    bySegment._version=run.creditVersion or 0
    creditCaches[run]=bySegment
    local o=bySegment[target.segmentID]
    return o.borrowed,o.borrowedActual,o.credited,o.actual,o.diverted,o.waived
end
function XP.GetRecipeTotals(slug,planID,fresh)
    local run=planID and db().runs[planID] or XP.GetRun(slug)
    if not run or run.slug~=slug then return {} end
    -- Saved summaries describe the same execution facts; history browsing must
    -- not inflate every archived plan just to display its recipe totals.
    if not fresh and run.status=="archived" and type(run.byRecipe)=="table"
        and (run.byRecipeVersion==nil or run.byRecipeVersion==run.progressVersion) then
        return copy(run.byRecipe)
    end
    local plan=readablePlan(run)
    if not plan then return copy(run.byRecipe or {}),"historyUnreadable" end
    local list,byKey={},{ }
    for _,seg in ipairs(steps(plan)) do
        if seg[3]~=0 and not XP.IsSpecializationQuest(seg) and not XP.IsConversion(seg) then
            local key=(seg.profession or slug)..":"..seg[3];local entry=byKey[key]
            if not entry then entry={profession=seg.profession or slug,spell=seg[3],casts=0,confirmedOutputs={},guaranteedOutputs={},pendingOutputs=0};byKey[key]=entry;list[#list+1]=entry end
            local confirmed,guaranteed,pending=outputFacts(run,seg)
            entry.casts=entry.casts+(progressRecord(run,seg).casts or 0);entry.pendingOutputs=entry.pendingOutputs+pending
            for item,n in pairs(confirmed) do entry.confirmedOutputs[item]=(entry.confirmedOutputs[item] or 0)+n end
            for item,n in pairs(guaranteed) do entry.guaranteedOutputs[item]=(entry.guaranteedOutputs[item] or 0)+n end
        end
    end
    if run.status=="archived" then run.byRecipe=copy(list);run.byRecipeVersion=run.progressVersion end
    return list
end
function XP.Progress(slug,id,skillSnapshot,planID)
    local run=planID and db().runs[planID] or XP.GetRun(slug);if not run or run.slug~=slug then return nil end
    if not readablePlan(run) then
        return {complete=false,skillDone=false,skillMet=false,materialDone=false,blocked=true,
            historyUnreadable=true,reason="historyUnreadable",attemptsDone=0,casts=0,
            remainingCrafts=0,remainingOutputs=0,pendingOutputs=0,directMaterials={}}
    end
    local seg,index=segment(run,id);if not seg then return {complete=true,skillDone=true,skillMet=true,materialDone=true,attemptsDone=0,casts=0,remainingCrafts=0,remainingOutputs=0,pendingOutputs=0} end
    local p=progressRecord(run,seg);local rec=recipe(seg,slug)
    local conversion=XP.Conversion(seg)
    if XP.IsConversion(seg) and not conversion then
        return {segmentID=seg.segmentID,index=index,kind=seg.kind,manualConversion=true,
            complete=false,skillDone=true,skillMet=true,materialDone=false,blocked=true,reason="invalid_conversion",
            attemptsDone=0,casts=0,remainingCrafts=0,remainingConversions=0,remainingOutputs=0,pendingOutputs=0,directMaterials={}}
    end
    if XP.IsSpecializationQuest(seg) then
        local goal=XP.SpecializationQuest(seg)
        local done=p.questCompleted==true
        local current=skill(seg.profession or slug,skillSnapshot)
        local direct={}
        for _,m in ipairs(goal.inputs or {}) do direct[#direct+1]={id=m[1],count=done and 0 or m[2],perCraft=m[2]} end
        return {segmentID=seg.segmentID,index=index,kind=seg.kind,questID=goal.questID,abilityID=goal.abilityID,
            complete=done,skillDone=done,skillMet=current and current>=(goal.minSkill or 200) or false,
            materialDone=done,attemptsDone=0,casts=0,remainingCrafts=0,remainingOutputs=0,pendingOutputs=0,
            extraCrafts=0,blocked=not done,directMaterials=direct}
    end
    local confirmed,guaranteed,pending,output=outputFacts(run,seg)
    local reused,reusedActual,fulfilled,_,diverted,waived=creditsFor(run,seg)
    local required=requiredOutputs(seg);local remaining={};local materialDone=true
    for item,n in pairs(required) do remaining[item]=max(0,n-(fulfilled[item] or 0)-(waived[item] or 0));if remaining[item]>0 then materialDone=false end end
    local cur=skill(seg.profession or slug,skillSnapshot);local goal=seg.goalSkill or seg[2]
    local skillDone=not goal or (cur~=nil and cur>=goal) or (seg.expectedGain or 0)<=0 and not seg.checkpoint
    if conversion then skillDone=true
    elseif seg.checkpoint or seg[3]==0 then skillDone=cur~=nil and goal~=nil and cur>=goal end
    local fractional=seg.fractionalTransition or (seg.expectedGain or 0)>0 and seg[2]==seg[1] and seg.attemptLimit~=nil
    if not skillDone and fractional and (p.casts or 0)>=ceil(seg.attemptLimit-1e-9) then
        local following=steps(run.plan)[index+1]
        if following then
            local nextRecipe=recipe(following,slug);local nextSkill=skill(following.profession or slug,skillSnapshot)
            if following.checkpoint or (nextSkill and type(nextRecipe.learn)=="number" and nextSkill>=nextRecipe.learn) then skillDone=true end
        end
    end
    local levelCrafts=0;local grey=false
    if not skillDone and cur and goal then
        for sk=cur,goal-1 do
            local gain=E and E.Gain and E.Gain(rec,sk)
            if not gain or gain<=0 then grey=true;break end
            levelCrafts=levelCrafts+1/gain
        end
    end
    local outputMin=seg.outputMin or rec.outputMin or rec.count or 1
    local materialCrafts=0
    for item,n in pairs(remaining) do
        local per=item==output and outputMin or 0
        if per>0 then materialCrafts=max(materialCrafts,ceil(n/per)) elseif n>0 then materialCrafts=math.huge end
    end
    local remainingCrafts=max(materialCrafts,ceil(levelCrafts-1e-9))
    if not skillDone and (grey or not cur) then remainingCrafts=max(1,materialCrafts) end
    local limit=ceil((seg.attemptLimit or seg.expectedCrafts or seg[4] or 0)+(p.supplementAllowance or 0)-1e-9)
    local direct={};for _,m in ipairs(rec.mats or {}) do direct[#direct+1]={id=m[1],count=m[2]*remainingCrafts,perCraft=m[2]} end
    local result={segmentID=seg.segmentID,index=index,kind=seg.kind,complete=skillDone and materialDone,skillDone=skillDone,skillMet=skillDone,materialDone=materialDone,
        currentSkill=cur,goalSkill=goal,attemptsDone=p.casts or 0,casts=p.casts or 0,minimumCrafts=seg.materialMinCrafts or 0,minCrafts=seg.materialMinCrafts or 0,
        outputItem=output,requiredOutputs=required[output] or 0,actualOutputs=confirmed[output] or 0,confirmedOutputs=confirmed[output] or 0,
        guaranteedOutputs=guaranteed[output] or 0,pendingOutputs=pending,remainingOutputs=remaining[output] or 0,
        reusedOutputs=reused[output] or 0,reusedConfirmedOutputs=reusedActual[output] or 0,
        resolvedByQuestOutputs=waived[output] or 0,resolvedByQuestByItem=waived,
        divertedOutputs=diverted[output] or 0,
        fulfilledOutputs=fulfilled[output] or 0,divertedOutputs=max(0,min(required[output] or 0,(guaranteed[output] or 0)+(reused[output] or 0))-(fulfilled[output] or 0)),
        requiredByItem=required,confirmedByItem=confirmed,guaranteedByItem=guaranteed,remainingByItem=remaining,
        remainingCrafts=remainingCrafts,expectedRemaining=levelCrafts,attemptLimit=limit,extraCrafts=max(0,(p.casts or 0)+remainingCrafts-limit),
        exhausted=(p.casts or 0)>=limit and not (skillDone and materialDone),blocked=grey,directMaterials=direct,outputConflict=p.outputConflict}
    if conversion then
        result.manualConversion=true
        result.plannedConversions=ceil(seg.expectedCrafts or seg[4] or 0)
        result.confirmedConversions=p.casts or 0;result.remainingConversions=remainingCrafts
        result.sourceItem=conversion.inputItemID;result.sourcePerConversion=conversion.inputCount
        result.targetItem=conversion.outputItemID;result.targetPerConversion=conversion.outputCount
        result.remainingInput=remainingCrafts*conversion.inputCount;result.remainingOutput=remainingCrafts*conversion.outputCount
    end
    return result
end
function XP.Sync(slug,result)
    if ns.ProfessionTracking and not ns.ProfessionTracking.IsEnabled() then return end
    local run=XP.GetRun(slug)
    if not run and result then run=XP.Bind(slug,result) end
    if not run then return end
    if not readablePlan(run) then return nil,"historyUnreadable" end
    local observed=false
    for _,seg in ipairs(steps(run.plan)) do
        if XP.IsSpecializationQuest(seg) then
            local goal=XP.SpecializationQuest(seg);local p=progressRecord(run,seg)
            if not p.questCompleted and E and E.SpecializationKnown and E.SpecializationKnown(goal.abilityID)==true then
                local c=db();c.nextAttempt=(c.nextAttempt or 0)+1
                p.questCompleted=true;p.questSequence=c.nextAttempt;p.questCompletedAt=now()
                local policy=run.plan.specializationPolicy
                if policy then
                    policy.actualAbilities=policy.actualAbilities or {}
                    policy.actualAbilities[goal.abilityID]=true
                end
                observed=true;invalidateCredits(run)
            end
        end
    end
    local index=1
    local skillSnapshot=E and E.Professions and E.Professions()
    while index<=#steps(run.plan) do local p=XP.Progress(slug,index,skillSnapshot);if not p.complete then break end;index=index+1 end
    run.currentIndex=index;run.step=index;run.finished=index>#steps(run.plan)
    if run.finished then
        -- Skill events may precede the final spell-success event. Give that
        -- last cast a bounded settling interval before detaching the run.
        run.completionDue=run.completionDue or now()+2
        if now()>=run.completionDue then XP.End(slug,"completed")
        elseif XP.RefreshObservation then XP.RefreshObservation() end
    else run.completionDue=nil end
    if observed and run.status=="active" then changed(run) end
    return run
end
local function matchingSegment(run,spell,id)
    if id then local seg=segment(run,id);if seg and not XP.IsConversion(seg) and seg[3]==spell then return seg end end
    local current=segment(run);if current and not XP.IsConversion(current) and current[3]==spell then return current end
    local fallback
    for i,seg in ipairs(steps(run.plan)) do if seg[3]==spell and not seg.checkpoint and not XP.IsConversion(seg) then
        fallback=seg;local p=XP.Progress(run.slug,i);if not p.complete then return seg end
    end end
    return fallback
end
local function allAttempts(c,minimum,maximum)
    local list={}
    performance.historyScans=performance.historyScans+1
    for _,run in pairs(c.runs) do for _,p in pairs(run.progress or {}) do for _,a in ipairs(p.attempts or {}) do
        if type(a.at)=="number" and (not minimum or a.at>=minimum) and (not maximum or a.at<=maximum) then
            list[#list+1]={run=run,progress=p,attempt=a}
        end
    end end end
    table.sort(list,function(a,b) return a.attempt.sequence<b.attempt.sequence end);return list
end
local function recentRunAttempts(c,at)
    local list={}
    for id,untilAt in pairs(c.recentRunIDs) do
        if untilAt<at then c.recentRunIDs[id]=nil
        else
            local run=c.runs[id]
            for _,p in pairs(run and run.progress or {}) do for _,a in ipairs(p.attempts or {}) do
                if type(a.at)=="number" and a.at>=at-17 and a.at<=at+2 then list[#list+1]={run=run,progress=p,attempt=a} end
            end end
        end
    end
    table.sort(list,function(a,b) return a.attempt.sequence<b.attempt.sequence end);return list
end
local function indexRecent(cache,entry)
    local a=entry.attempt
    if a.item then local list=cache.items[a.item] or {};cache.items[a.item]=list;list[#list+1]=entry end
    if a.castGUID then local list=cache.guids[a.castGUID] or {};cache.guids[a.castGUID]=list;list[#list+1]=entry end
end
local function trimRecent(cache,at)
    local list={};cache.items={};cache.guids={}
    for _,entry in ipairs(cache.list) do
        if entry.attempt.at>=at-17 and entry.attempt.at<=at+2 then list[#list+1]=entry;indexRecent(cache,entry) end
    end
    cache.list=list;cache.at=at
end
local function recentAttempts(c,receipt)
    local at=now()
    -- Explicit historical receipts retain their original association semantics.
    -- Ordinary live events only inspect the short matching window.
    if receipt.historicalAt and (receipt.at<at-2 or receipt.at>at+2) then return allAttempts(c,receipt.at-15,receipt.at+2) end
    local cache=recentCaches[c]
    if not cache or cache.sequence~=(c.nextAttempt or 0) or at<cache.at then
        cache={at=at,sequence=c.nextAttempt or 0,list=recentRunAttempts(c,at),items={},guids={}}
        for _,entry in ipairs(cache.list) do indexRecent(cache,entry) end
        recentCaches[c]=cache;performance.recentBuilds=performance.recentBuilds+1
    elseif at~=cache.at then
        trimRecent(cache,at)
    end
    return receipt.castGUID and (cache.guids[receipt.castGUID] or {}) or cache.items[receipt.itemID] or {}
end
local function addRecent(c,run,p,a)
    local cache=recentCaches[c]
    if not cache then return end
    if cache.sequence+1~=a.sequence then recentCaches[c]=nil;return end
    if a.at<cache.at then recentCaches[c]=nil;return end
    if a.at~=cache.at then trimRecent(cache,a.at) end
    cache.sequence=a.sequence
    local entry={run=run,progress=p,attempt=a}
    cache.list[#cache.list+1]=entry;indexRecent(cache,entry)
end
local function acceptReceipt(receipt)
    local c=db();local selected
    for _,entry in ipairs(recentAttempts(c,receipt)) do
        local a=entry.attempt
        if not a.conversion and a.item==receipt.itemID and (not receipt.castGUID or receipt.castGUID==a.castGUID)
            and (not receipt.spellID or receipt.spellID==a.spellID)
            and (receipt.at or now())-a.at>=-2 and (receipt.at or now())-a.at<=15 then
            a.sources=a.sources or {}
            if receipt.castGUID and a.sources[receipt.source] then return true end
            if not a.sources[receipt.source] then selected=entry;break end
        end
    end
    if not selected then return false end
    local a,p,run=selected.attempt,selected.progress,selected.run
    a.sources[receipt.source]={quantity=receipt.quantity,operationID=receipt.operationID,itemGUID=receipt.itemGUID}
    local preferred=a.sources.structured or a.sources.manual or a.sources.chat
    a.actual=preferred and preferred.quantity or a.actual
    if a.actual and a.actual<(a.minimum or 0) then p.outputConflict=true end
    if a.sources.structured and a.sources.chat and a.sources.structured.quantity~=a.sources.chat.quantity then p.outputConflict=true end
    invalidateCredits(run)
    if run.status=="active" then XP.Sync(run.slug) end
    changed(run);return true
end
function XP.RecordOutput(data,source)
    if ns.ProfessionTracking and not ns.ProfessionTracking.IsEnabled() then return end
    if type(data)~="table" then return false,"invalid_receipt" end
    local receipt={itemID=tonumber(data.itemID or data.id),quantity=tonumber(data.quantity or data.count),source=source or data.source or "structured",
        operationID=data.operationID,itemGUID=data.itemGUID,castGUID=data.castGUID,spellID=data.spellID,at=data.at or now(),historicalAt=data.at~=nil}
    if not integer(receipt.itemID) or receipt.itemID<=0 or not integer(receipt.quantity) or receipt.quantity<=0 then return false,"invalid_receipt" end
    local c=db();local receiptID=data.receiptID or data.eventID
    if receiptID and remember(c.seenReceipts,c.receiptOrder,receipt.source..":"..tostring(receiptID),256) then return true,"duplicate" end
    if acceptReceipt(receipt) then return true end
    early[#early+1]=receipt;while #early>64 do table.remove(early,1) end
    return false,"unmatched"
end
function XP.RecordAttempt(slug,spellID,castGUID,id)
    if ns.ProfessionTracking and not ns.ProfessionTracking.IsEnabled() then return end
    local run=XP.GetRun(slug);if not run or type(spellID)~="number" then return false end
    if not readablePlan(run) then return false,"historyUnreadable" end
    local seg=matchingSegment(run,spellID,id);if not seg or XP.IsSpecializationQuest(seg) or XP.IsConversion(seg) then return false end
    local c=db()
    if castGUID and remember(c.seenCasts,c.castOrder,tostring(castGUID),512) then return false,"duplicate" end
    c.nextAttempt=(c.nextAttempt or 0)+1
    local rec=recipe(seg,slug);local p=progressRecord(run,seg)
    local a={sequence=c.nextAttempt,castGUID=castGUID,spellID=spellID,segmentID=seg.segmentID,at=now(),
        item=seg.item or rec.item or rec.makes,minimum=seg.outputMin or rec.outputMin or rec.count or 0,sources={}}
    p.casts=(p.casts or 0)+1;p.attempts[#p.attempts+1]=a;run.attemptsDone=(run.attemptsDone or 0)+1
    c.recentRunIDs[run.planID]=a.at+15;c.receiptUntil=max(c.receiptUntil or 0,a.at+15)
    if run.completionDue then run.completionDue=now()+2 end
    addRecent(c,run,p,a)
    invalidateCredits(run)
    for i=#early,1,-1 do local r=early[i];if now()-r.at>15 then table.remove(early,i) end end
    local waiting=early;early={}
    for _,r in ipairs(waiting) do if not acceptReceipt(r) then early[#early+1]=r end end
    XP.Sync(slug);changed(run);if XP.RefreshObservation then XP.RefreshObservation() end;return true,a
end
function XP.ConfirmConversion(slug,id,count,planID)
    if ns.ProfessionTracking and not ns.ProfessionTracking.IsEnabled() then return end
    local run=XP.GetRun(slug);if not run then return false,"no_execution" end
    if planID and planID~=run.planID then return false,"stale_plan" end
    if not readablePlan(run) then return false,"historyUnreadable" end
    local seg,index=segment(run,id);if not seg then return false,"unknown_segment" end
    local conversion=XP.Conversion(seg);if not conversion then return false,"invalid_conversion" end
    local current=ns.ProfEssences and ns.ProfEssences.ForItem(conversion.outputItemID)
    if not current or current.status~="confirmed" or current.noSkillGain~=true
        or current.outputItemID~=conversion.outputItemID or current.inputItemID~=conversion.inputItemID or current.inputCount~=conversion.inputCount
        or current.outputCount~=conversion.outputCount then return false,"conversionFactsUnknown" end
    XP.Sync(slug)
    if run.status~="active" then return false,"complete" end
    local p=XP.Progress(slug,seg.segmentID)
    if p.complete then return false,"complete" end
    if index~=run.currentIndex then return false,"not_current_step" end
    count=count or p.remainingConversions
    if not integer(count) or count<=0 or count>p.remainingConversions then return false,"invalid_quantity" end
    -- This explicit user attestation is the only conversion receipt. Purchases,
    -- loot, skill changes and spell success must never invent a conversion.
    -- Each operation is replayed with the same input/output chronology as a
    -- craft, but it is not a profession cast and owns no late-receipt window.
    local c=db();local record=progressRecord(run,seg)
    for _=1,count do
        c.nextAttempt=(c.nextAttempt or 0)+1
        local a={sequence=c.nextAttempt,segmentID=seg.segmentID,at=now(),conversion=true,
            item=conversion.outputItemID,minimum=conversion.outputCount,actual=conversion.outputCount,
            sources={manualConversion={quantity=conversion.outputCount,inputItemID=conversion.inputItemID,inputCount=conversion.inputCount}}}
        record.attempts[#record.attempts+1]=a
    end
    record.casts=(record.casts or 0)+count;record.verifiedAt=now()
    run.conversionsDone=(run.conversionsDone or 0)+count
    invalidateCredits(run)
    XP.Sync(slug);changed(run);if XP.RefreshObservation then XP.RefreshObservation() end
    return true,count
end
function XP.VerifyOutput(slug,id,item,total)
    if not integer(item) or item<=0 or not integer(total) then return false,"invalid_quantity" end
    local run=XP.GetRun(slug);if not run then return false,"no_execution" end
    if not readablePlan(run) then return false,"historyUnreadable" end
    local seg=segment(run,id);if not seg then return false,"unknown_segment" end
    if XP.IsConversion(seg) then return false,"manual_conversion_required" end
    local rec=recipe(seg,slug)
    if item~=(seg.item or rec.item or rec.makes) then return false,"wrong_item" end
    local p=progressRecord(run,seg);local sequence=0;for _,a in ipairs(p.attempts) do sequence=max(sequence,a.sequence) end
    p.manualOutputs[item]={total=total,throughSequence=sequence};p.verifiedAt=now()
    invalidateCredits(run)
    XP.Sync(slug);changed(run);return true
end
local function bagCount(item)
    local fn=C_Item and C_Item.GetItemCount or GetItemCount
    if type(fn)~="function" then return 0 end
    local ok,n=pcall(fn,item,false);if ok and integer(n) then return n end;return 0
end
function XP.GetContinuation(slug)
    local c=db();local run=XP.GetRun(slug)
    if not run then
        local source=c.preparing[slug] or c.continuation[slug];run=source and c.runs[source.sourcePlanID]
        if not run and source and (source.sourcePlanID or type(source.inventory)=="table" and next(source.inventory)) then return nil,"historyUnreadable" end
    end
    if not run then return {} end
    if not readablePlan(run) then return nil,"historyUnreadable" end
    if run.status=="active" then XP.Sync(slug) end
    local stock,intermediate,events,unconfirmed,unconfirmedUsed={},{},{},{},{}
    for item,value in pairs(run.inheritedInventory or {}) do
        local n=type(value)=="table" and value.count or value
        if integer(n) then stock[item]=n;intermediate[item]=true end
    end
    for _,seg in ipairs(steps(run.plan)) do
        local rec=recipe(seg,slug);local record=progressRecord(run,seg)
        for _,m in ipairs(rec.mats or {}) do intermediate[m[1]]=true end
        if XP.IsConversion(seg) and rec.item then intermediate[rec.item]=true end
        for _,a in ipairs(record.attempts) do events[#events+1]={sequence=a.sequence,attempt=a,recipe=rec} end
        if XP.IsSpecializationQuest(seg) and record.questCompleted and record.questSequence then
            events[#events+1]={sequence=record.questSequence,attempt={},recipe=rec}
        end
        for item,manual in pairs(record.manualOutputs) do
            local through=type(manual)=="table" and manual.throughSequence or 0
            local total=type(manual)=="table" and manual.total or manual;local counted=0
            for _,a in ipairs(record.attempts) do if a.item==item and a.sequence<=through then counted=counted+(a.actual or 0) end end
            events[#events+1]={sequence=through,manual=true,item=item,adjust=total-counted}
        end
    end
    table.sort(events,function(a,b) if a.sequence==b.sequence then return not a.manual and b.manual or false end;return a.sequence<b.sequence end)
    -- Actual event chronology matters after inserted top-up steps: casts which
    -- happened before a producer cannot consume items that did not yet exist.
    for _,event in ipairs(events) do
        if event.manual then
            -- A cumulative correction may cover unknown output made before a
            -- consumer. Do not recreate the units already used in that gap.
            local consumed=min(max(0,event.adjust),unconfirmedUsed[event.item] or 0)
            stock[event.item]=max(0,(stock[event.item] or 0)+event.adjust-consumed)
            unconfirmedUsed[event.item]=max(0,(unconfirmedUsed[event.item] or 0)-consumed)
        else
            for _,m in ipairs(event.recipe.mats or {}) do
                local available=stock[m[1]] or 0
                if unconfirmed[m[1]] then unconfirmedUsed[m[1]]=(unconfirmedUsed[m[1]] or 0)+max(0,m[2]-available) end
                stock[m[1]]=max(0,available-m[2])
            end
            local a=event.attempt
            if a.item and integer(a.actual) then stock[a.item]=(stock[a.item] or 0)+a.actual end
            if a.item and not integer(a.actual) then unconfirmed[a.item]=true end
        end
    end
    local out={}
    for item,n in pairs(stock) do if intermediate[item] then local left=min(n,bagCount(item));if left>0 then out[item]=left end end end
    return out
end
function XP.PrepareRecalculate(slug)
    local c=db();local run=XP.GetRun(slug);local seed,reason=XP.GetContinuation(slug)
    if not seed then return nil,nil,reason or "historyUnreadable" end
    local previous=c.preparing[slug]
    if not run and previous and previous.hadActive and not c.runs[previous.sourcePlanID] then
        seed=copy(previous.inventory or {})
        for item,n in pairs(seed) do seed[item]=min(n,bagCount(item)) end
    end
    local source=c.continuation[slug]
    local preparing={hadActive=run~=nil and run.status=="active" or previous and previous.hadActive or false,
        sourcePlanID=run and run.planID or previous and previous.sourcePlanID or source and source.sourcePlanID,inventory=copy(seed)}
    if run then archive(c,slug,"recalculate");changed(run) end
    c.preparing[slug]=preparing;referencesChanged();if XP.RefreshObservation then XP.RefreshObservation() end;return seed,preparing.sourcePlanID
end
function XP.PlanRecalculated(slug,result)
    local c=db();local p=c.preparing[slug]
    -- The first published prefix is a preview, not the completed replacement.
    -- Freezing it here hid every later extension of the same calculation.
    if p and p.hadActive and ready(result) and result.status~="searching" then
        return XP.Bind(slug,result,{executionInventory=p.inventory})
    end
    return XP.GetRun(slug)
end
local function formatPattern(fmt)
    if type(fmt)~="string" or fmt=="" then return end
    local out,types={},{};local i=1
    while i<=#fmt do
        local token=fmt:sub(i):match("^%%(%d+)%$([sd])")
        local position,kind,advance
        if token then position,kind=fmt:sub(i):match("^%%(%d+)%$([sd])");advance=#position+3
        else kind=fmt:sub(i):match("^%%([sd])");advance=2 end
        if kind then out[#out+1]=kind=="d" and "(%d+)" or "(.-)";types[#types+1]={kind=kind,position=tonumber(position)};i=i+advance
        elseif fmt:sub(i,i+1)=="%%" then out[#out+1]="%%";i=i+2
        else out[#out+1]=fmt:sub(i,i):gsub("([%^%$%(%)%%%.%[%]%*%+%-%?])","%%%1");i=i+1 end
    end
    return "^"..table.concat(out).."$",types
end
function XP.RecordCreatedMessage(text,lineID)
    if ns.ProfessionTracking and not ns.ProfessionTracking.IsEnabled() then return end
    if type(text)~="string" then return false end
    for _,name in ipairs({"LOOT_ITEM_CREATED_SELF_MULTIPLE","LOOT_ITEM_CREATED_SELF"}) do
        local pat,types=formatPattern(_G[name])
        if pat then
            local captures={text:match(pat)}
            if #captures>0 then
                local item,quantity
                for i,v in ipairs(captures) do if types[i].kind=="d" then quantity=tonumber(v) else item=tonumber(v:match("item:(%d+)")) or item end end
                if item then return XP.RecordOutput({itemID=item,quantity=quantity or 1,receiptID=lineID and lineID~=0 and (XP.eventSession..":"..lineID) or nil},"chat") end
            end
        end
    end
    return false
end
function XP.GetSupplement(slug)
    local run=XP.GetRun(slug);local result=run and run.supplement
    if run and not readablePlan(run) then return nil,"historyUnreadable" end
    local ra=ns.ProfRouteAuto
    if run and ra and ra.VendorQuotesChanged and ra.VendorQuotesChanged(run.plan) then
        return ra.ValidateVendorQuotes(run.plan)
    end
    if run and specializationChanged(run.plan,slug) then return validatedPlan(run.plan,slug) end
    return validatedPlan(result,slug)
end
local function appendSupplement(run,result,seg,extra)
    local history=ns.ProfHistory
    local plan=history and history.Touch and history.Touch(run)
    -- The legacy manager's Touch has no return value. The repository manager
    -- returns the private pending revision that remains durable until commit.
    if not plan and history and history.FactsChanged then return false,"historyUnreadable" end
    plan=plan or run.plan
    if not plan then return false end
    local index
    for i,x in ipairs(steps(plan)) do if x.segmentID==seg.segmentID then index=i;break end end
    if not index then return false end
    local ordinal=#run.supplements+1;local prefix=run.planID..":supplement:"..ordinal..":"
    local insertions,ids={},{ }
    for i,raw in ipairs(steps(result)) do if raw.profession~="__purchase" then
        local x=copy(raw);local old=x.segmentID or x.actionID or tostring(i);x.segmentID=prefix..old;x.actionID=x.segmentID;ids[old]=x.segmentID;insertions[#insertions+1]=x
    end end
    for _,x in ipairs(insertions) do for _,a in ipairs(x.allocations or {}) do a.consumerID=ids[a.consumerID] or seg.segmentID end end
    for i=#insertions,1,-1 do table.insert(plan.executionSteps,index,insertions[i]) end
    local p=progressRecord(run,seg);p.supplementAllowance=(p.supplementAllowance or 0)+extra
    result.appended=true;result.segmentID=seg.segmentID;result.extraCrafts=extra;result.revision=ordinal
    run.supplements[#run.supplements+1]=result;run.supplement=result
    invalidateCredits(run)
    XP.Sync(run.slug);changed(run);return true
end
function XP.CalculateSupplement(slug,callback)
    if ns.ProfessionTracking and not ns.ProfessionTracking.IsEnabled() then return end
    local run=XP.GetRun(slug);if not run then return nil,"no_execution" end
    if not readablePlan(run) then return nil,"historyUnreadable" end
    local ra=ns.ProfRouteAuto
    if ra and ra.VendorQuotesChanged and ra.VendorQuotesChanged(run.plan) then return nil,"vendorQuoteChanged" end
    if specializationChanged(run.plan,slug) then return nil,"specializationChanged" end
    if jobs[run.planID] then return run.supplement end
    XP.Sync(slug);local seg=segment(run);local p=seg and XP.Progress(slug,seg.segmentID)
    if XP.IsSpecializationQuest(seg) then return nil,"specialization_quest_pending" end
    if XP.IsConversion(seg) then return nil,"manual_conversion_required" end
    if not p or p.complete then return nil,"complete" end
    if p.extraCrafts<=0 then return nil,"planned_attempts_remaining" end
    if p.blocked and not p.skillDone then return nil,"skill_gap" end
    local extra=max(1,p.extraCrafts);local demands={};local rec=recipe(seg,slug)
    for _,m in ipairs(rec.mats or {}) do demands[m[1]]=(demands[m[1]] or 0)+m[2]*extra end
    local version=run.progressVersion;local state={status="searching",inFlight=true,feasible=false,segmentID=seg.segmentID,extraCrafts=extra,mats={},formulas={},total=0,revision=#run.supplements+1}
    run.supplement=state
    local task={run=run,version=version,state=state};jobs[run.planID]=task
    local co=coroutine.create(function()
        local opts=copy(run.plan.executionOptions or {});opts.snapshot=nil
        opts.materialProfession=slug;opts.executionInventory=XP.GetContinuation(slug);opts.defer=true
        local snap=E.Capture(slug,opts,function() coroutine.yield() end)
        snap.known=snap.known or {}
        for _,step in ipairs(steps(run.plan)) do
            if (progressRecord(run,step).casts or 0)>0 then snap.known[(step.profession or slug)..":"..step[3]]=true end
        end
        -- Production already promised to later base steps is not free top-up
        -- stock. Keep their still-planned reagent demand reserved as well.
        local reserved={}
        for _,future in ipairs(steps(run.plan)) do
            local record=progressRecord(run,future)
            local allowance=(future.attemptLimit or future.expectedCrafts or future[4] or 0)+(record.supplementAllowance or 0)
            local remaining=max(0,allowance-(record.casts or 0))
            if XP.IsSpecializationQuest(future) then remaining=record.questCompleted and 0 or 1 end
            for _,m in ipairs(recipe(future,slug).mats or {}) do reserved[m[1]]=(reserved[m[1]] or 0)+remaining*m[2] end
        end
        for item,n in pairs(opts.executionInventory) do opts.executionInventory[item]=max(0,n-(reserved[item] or 0)) end
        for _,purchase in ipairs(run.plan.mats or {}) do
            local item=purchase.id or purchase[1];local supply=snap.auctionSupply and snap.auctionSupply[item]
            if supply and not purchase.vendor and (purchase.source=="ah" or purchase.source=="auction") then
                supply.quantity=max(0,supply.quantity-min(reserved[item] or 0,purchase.count or purchase[2] or 0))
            end
        end
        local result,j=S.ProcureMany(snap,demands,opts)
        if j then while coroutine.status(j.co)~="dead" and not j.finished and (j.status~="error" or j.finalizing) do S.Run(j,ns.IdleJobs and ns.IdleJobs.SliceCap and ns.IdleJobs.SliceCap(2) or 2);coroutine.yield() end;result=j.result or S.Result(j,j.best,j.status) end
        return result
    end)
    local function pump()
        if task.cancelled then return true end
        if not readablePlan(run) then
            state.status="blocked";state.error="historyUnreadable";state.feasible=false;state.inFlight=false
            state.diagnostics={{code="historyUnreadable"}};jobs[run.planID]=nil
            if callback then pcall(callback,state) end
            return true
        end
        if XP.GetRun(slug)~=run or run.progressVersion~=version or specializationChanged(run.plan,slug) then
            state.status="stale";state.stale=true;state.feasible=false;state.inFlight=false;jobs[run.planID]=nil;if callback then pcall(callback,state) end;return true
        end
        local ok,result=coroutine.resume(co)
        if not ok then state.status="error";state.error=tostring(result);state.inFlight=false;jobs[run.planID]=nil;changed(run);if callback then pcall(callback,state) end;return true end
        if coroutine.status(co)~="dead" then return false end
        jobs[run.planID]=nil
        result=result or {status="infeasible",feasible=false,mats={},formulas={},total=0};result.inFlight=false
        -- The caller may retain the object returned by CalculateSupplement.
        -- Publish the terminal result into that same object so it cannot remain
        -- permanently marked as searching after the ledger has accepted it.
        if result~=state then
            for key in pairs(state) do state[key]=nil end
            for key,value in pairs(result) do state[key]=value end
            result=state
        end
        if ra and ra.StampVendorQuotes then ra.StampVendorQuotes(result) end
        if ra and ra.StampSpecializations then ra.StampSpecializations(result,slug,run.plan.executionOptions) end
        if result.feasible and result.targetReached~=false then
            local appended,reason=appendSupplement(run,result,seg,extra)
            if not appended and reason=="historyUnreadable" then
                state.status="blocked";state.error=reason;state.feasible=false;state.inFlight=false
                state.diagnostics={{code=reason}};run.supplement=state;result=state
            end
        else run.supplement=result;changed(run) end
        if callback then pcall(callback,result) end
        return true
    end
    task.pump=pump
    if ns.IdleJobs and ns.IdleJobs.Defer then ns.IdleJobs.Defer(task,pump,"normal")
    elseif ns.IdleJobs and ns.IdleJobs.Add then ns.IdleJobs.Add(pump)
    elseif C_Timer and C_Timer.After then local function later() if not pump() then C_Timer.After(0,later) end end;C_Timer.After(0,later)
    else while not pump() do end end
    return state
end
function XP.Pump(slug) local run=XP.GetRun(slug);local j=run and jobs[run.planID];if j then return j.pump() end end
-- Observation follows execution activity, never HUD visibility. At rest the
-- frame has no subscriptions, timers or historical-plan traversal.
local executionEvents={"UNIT_SPELLCAST_SUCCEEDED","SKILL_LINES_CHANGED","CHAT_MSG_SKILL","SPELLS_CHANGED","LEARNED_SPELL_IN_TAB","QUEST_TURNED_IN"}
local receiptEvents={"TRADE_SKILL_ITEM_CRAFTED_RESULT","CHAT_MSG_LOOT"}
local observedEvents={}
function XP.RefreshObservation()
    if ns.ProfessionTracking and not ns.ProfessionTracking.IsEnabled() then if XP.DisableTracking then XP.DisableTracking() end;return false,false end
    local c=db();local active=XP.HasActive();local at=now();local receipts=active or (c.receiptUntil or 0)>=at and (c.receiptUntil or 0)>0
    local f=XP.eventFrame
    if f then
        local wanted={}
        if active then for _,event in ipairs(executionEvents) do wanted[event]=true end end
        if receipts then for _,event in ipairs(receiptEvents) do wanted[event]=true end end
        for event in pairs(observedEvents) do if not wanted[event] then
            if type(f.UnregisterEvent)=="function" then f:UnregisterEvent(event) end
            observedEvents[event]=nil
        end end
        for event in pairs(wanted) do if not observedEvents[event] then
            local ok=pcall(f.RegisterEvent,f,event);XP.capabilities[event]=ok;observedEvents[event]=ok or nil
        end end
    end
    if not active and not receipts then recentCaches[c]=nil;early={} end
    if not observationTimer and (c.receiptUntil or 0)>=at and (c.receiptUntil or 0)>0 and C_Timer and C_Timer.After then
        observationTimer=true;local generation=observationGeneration;local scheduling=true
        C_Timer.After(max(1,c.receiptUntil-at+1),function()
            if generation~=observationGeneration then return end
            observationTimer=false;if scheduling then return end;XP.RefreshObservation()
        end)
        scheduling=false
    end
    local due
    for _,id in pairs(c.active) do local run=c.runs[id];if run and run.completionDue then due=min(due or run.completionDue,run.completionDue) end end
    if due and not completionTimer and C_Timer and C_Timer.After then
        completionTimer=true;local generation=observationGeneration;local scheduling=true
        C_Timer.After(max(0.1,due-at),function()
            if generation~=observationGeneration then return end
            completionTimer=false;if scheduling then return end
            local slugs={};for slug in pairs(db().active) do slugs[#slugs+1]=slug end
            for _,slug in ipairs(slugs) do XP.Sync(slug) end
            XP.RefreshObservation()
        end)
        scheduling=false
    end
    if observedActive~=active or observedReceipts~=receipts then
        observedActive=active;observedReceipts=receipts
        for _,fn in ipairs(observationListeners) do pcall(fn,active,receipts) end
    end
    return active,receipts
end
function XP.ReconcileLifecycle()
    if ns.ProfessionTracking and not ns.ProfessionTracking.IsEnabled() then return end
    local c=db();local slugs={};for slug in pairs(c.active) do slugs[#slugs+1]=slug end
    for _,slug in ipairs(slugs) do
        local run=c.runs[c.active[slug]]
        if not run then c.active[slug]=nil;if c.trackingSlug==slug then c.trackingSlug=nil end
        elseif run.status=="archived" then XP.End(slug,run.archiveReason or "ended")
        elseif not catalogueAllowed(run.plan) then XP.End(slug,"catalogueFiltered")
        else XP.Sync(slug) end
    end
    if c.trackingSlug and not c.active[c.trackingSlug] then c.trackingSlug=nil end
    return XP.RefreshObservation()
end
function XP.Initialize()
    local old=ns.ProfTrack and ns.ProfTrack.frame
    if old and old.UnregisterAllEvents then old:UnregisterAllEvents() end
    if ns.ProfessionTracking and not ns.ProfessionTracking.IsEnabled() then return end
    observationGeneration=observationGeneration+1;observationTimer=false;completionTimer=false
    local c=db();c.observerSession=(c.observerSession or 0)+1;XP.eventSession=tostring(c.observerSession)
    -- Only active executions can own an in-flight supplement; archived plans
    -- and their compressed payloads are irrelevant to observation startup.
    for _,id in pairs(c.active) do local run=c.runs[id]
        if run and run.supplement and run.supplement.inFlight then run.supplement.inFlight=false;run.supplement.status="stale";run.supplement.stale=true;run.supplement.feasible=false end
    end
    if type(CreateFrame)~="function" then return end
    local f=XP.eventFrame or CreateFrame("Frame");XP.eventFrame=f;XP.capabilities=XP.capabilities or {}
    f:SetScript("OnEvent",function(_,event,...)
        if event=="UNIT_SPELLCAST_SUCCEEDED" then
            local unit,guid,spell=...;if unit~="player" then return end
            local c=db();local selected=c.trackingSlug
            if not (selected and XP.RecordAttempt(selected,spell,guid)) then
                -- Keep dev's ability to observe another active profession.
                -- One cast belongs to one execution, even if plans overlap.
                local slugs={};for slug in pairs(c.active) do if slug~=selected then slugs[#slugs+1]=slug end end
                table.sort(slugs)
                for _,slug in ipairs(slugs) do if XP.RecordAttempt(slug,spell,guid) then break end end
            end
        elseif event=="TRADE_SKILL_ITEM_CRAFTED_RESULT" then XP.RecordOutput((...),"structured")
        elseif event=="CHAT_MSG_LOOT" then local args={...};XP.RecordCreatedMessage(args[1],args[11])
        elseif event=="SPELLS_CHANGED" or event=="LEARNED_SPELL_IN_TAB" or event=="QUEST_TURNED_IN" then
            local slugs={};for slug in pairs(db().active) do slugs[#slugs+1]=slug end
            for _,slug in ipairs(slugs) do XP.Sync(slug) end
        elseif event=="SKILL_LINES_CHANGED" or event=="CHAT_MSG_SKILL" then
            local slugs={};for slug in pairs(db().active) do slugs[#slugs+1]=slug end
            for _,slug in ipairs(slugs) do
                local run=XP.GetRun(slug);if run then XP.Sync(slug);if run.status=="active" then changed(run) end end
            end
        end
    end)
    XP.ReconcileLifecycle()
end
-- Compatibility facade and legacy migration are installed below before startup.

function XP.DisableTracking()
    observationGeneration=observationGeneration+1
    observationTimer,completionTimer=false,false
    for _,job in pairs(jobs) do
        if ns.IdleJobs and ns.IdleJobs.Cancel then ns.IdleJobs.Cancel(job) end
        job.cancelled=true
        if job.state then job.state.inFlight=false;job.state.status="cancelled" end
    end
    jobs={};early={}
    creditCaches=setmetatable({}, {__mode="k"})
    recentCaches=setmetatable({}, {__mode="k"})
    local frame=XP.eventFrame
    for event in pairs(observedEvents) do
        if frame and frame.UnregisterEvent then frame:UnregisterEvent(event) end
    end
    observedEvents={};observedActive=false;observedReceipts=false
end

-- Upgrade the old index-based dev recorder without discarding its evidence.
-- Only casts/receipts that were recorded are migrated; bag contents are never
-- promoted into production receipts. Unknown historical fields survive in the
-- original backup so a newer reader can still recover them.
upgradeLegacy=function(run,c)
    if type(run)~="table" or run.plan or type(run.steps)~="table" then return end
    local legacySteps,legacyProgress=run.steps,run.progress or {}
    local plan={executionVersion=1,planVersion=2,slug=run.slug,planID=run.planID,
        mode=run.scheme=="fixed" and "fixed" or "auto",scheme=run.scheme,
        start=run.start,target=run.target,total=run.totalCost,priced=run.priced,
        status="complete",feasible=true,executionSteps={},steps={},mats={},formulas={}}
    local migrated={};local total=0
    run.legacyTrack={steps=copy(legacySteps),progress=copy(legacyProgress),outputs=copy(run.outputs or {}),
        planSig=run.planSig,migratedAt=now()}
    for i,old in ipairs(legacySteps) do
        local spell=old.spell or old[3];local profession=old.profession or run.slug
        local rec=E and E.FindRecipe and E.FindRecipe(profession,spell)
        rec=copy(rec or {spell=spell,profession=profession,item=old.item,count=old.out or 1,mats=old.mats or {},
            learn=old.from or old[1] or 1,yellow=old.from or old[1] or 1,
            green=old.to or old[2] or 300,grey=max((old.to or old[2] or 300)+1,2)})
        local a,b=old.from or old[1] or 0,old.to or old[2] or 0
        local count=old.crafts or old[4] or 0
        local id=run.planID..":legacy:"..i
        local seg={a,b,spell,count,segmentID=id,actionID=id,profession=profession,recipe=rec,
            item=old.item or rec.item,goalSkill=b,expectedGain=max(0,b-a),expectedCrafts=count,attemptLimit=count,
            outputMin=rec.outputMin or rec.count or 1,outputMax=rec.outputMax or rec.count or 1,
            requiredOutputs={},materialMinCrafts=0,allocations={},cost=old.cost,est=old.est}
        if b<=a and count>0 and seg.item then
            seg.requiredOutputs[seg.item]=seg.outputMin*count;seg.materialMinCrafts=count
        end
        plan.executionSteps[i]=seg;plan.steps[i]=seg
        local source=legacyProgress[i] or {};local progress={casts=source.casts or 0,attempts={},manualOutputs={}}
        total=total+progress.casts
        for _,oldAttempt in ipairs(source.attempts or {}) do
            local attempt=copy(oldAttempt)
            attempt.sequence=attempt.sequence or attempt.seq or ((c.nextAttempt or 0)+1)
            c.nextAttempt=max(c.nextAttempt or 0,attempt.sequence)
            attempt.spellID=attempt.spellID or attempt.spell or spell;attempt.segmentID=id
            attempt.item=attempt.item or seg.item;attempt.actual=attempt.actual or attempt.out
            attempt.minimum=attempt.minimum or seg.outputMin;attempt.sources=attempt.sources or {}
            if attempt.actual~=nil then attempt.sources.legacy={quantity=attempt.actual} end
            progress.attempts[#progress.attempts+1]=attempt
        end
        if type(source.manual)=="table" and source.manual.item then
            progress.manualOutputs[source.manual.item]={total=source.manual.total or 0,throughSequence=c.nextAttempt or 0}
        end
        migrated[id]=progress
    end
    run.plan=plan;run.progress=migrated;run.attemptsDone=total;run.supplements=run.supplements or {}
    run.inheritedInventory=run.inheritedInventory or {};run.executionMigration=1
    if run.status=="active" and not c.trackingSlug then c.trackingSlug=run.slug end
end

-- Keep the public dev ProfTrack surface used by ProfessionUI and ProfFollow.
-- The execution ledger owns facts; these views expose the former field names.
local T=ns.ProfTrack
if T then
    local legacyExtract=T.Extract
    local function compat(run)
        if not run or not readablePlan(run) then return run end
        run.steps={}
        for i,seg in ipairs(steps(run.plan)) do
            local rec=recipe(seg,run.slug)
            run.steps[i]={from=seg[1] or 0,to=seg[2] or 0,spell=seg[3],crafts=seg[4] or 0,
                item=seg.item or rec.item,out=rec.count,mats=rec.mats or {},cost=seg.cost,est=seg.est,
                profession=seg.profession,segmentID=seg.segmentID,kind=seg.kind}
        end
        run.start=run.plan.start;run.target=run.plan.target;run.scheme=run.plan.scheme
        run.totalCost=run.plan.total;run.priced=run.plan.priced;run.casts=run.attemptsDone or 0
        run.currentSkill=skill(run.slug);run.finished=(run.currentIndex or 1)>#run.steps or nil
        run.outputs={}
        for _,entry in ipairs(XP.GetRecipeTotals(run.slug,run.planID)) do
            for item,n in pairs(entry.confirmedOutputs or {}) do run.outputs[item]=(run.outputs[item] or 0)+n end
        end
        return run
    end
    function T.Get(slug,planID) return compat(planID and db().runs[planID]) end
    function T.GetRun(slug) return compat(XP.GetRun(slug)) end
    function T.Active(slug) local run=T.GetRun(slug);return run and run.status=="active" and run or nil end
    function T.History(slug)
        local all=XP.GetHistory(slug);for _,run in ipairs(all) do compat(run) end;return all
    end
    function T.Bind(slug,result,opts) local run,reason=XP.Bind(slug,result,opts);return compat(run),reason end
    function T.Restart(slug,result) return T.Bind(slug,result,{force=true}) end
    function T.Archive(slug,reason) return compat(XP.End(slug,reason or "archived")) end
    function T.Drop(slug) return T.Archive(slug,"dropped") end
    function T.Sync(slug) return compat(XP.Sync(slug)) end
    function T.Extract(result)
        if result and result.executionVersion==1 then
            local out={}
            for _,seg in ipairs(steps(result)) do
                local rec=recipe(seg,result.slug)
                out[#out+1]={from=seg[1],to=seg[2],spell=seg[3],crafts=seg[4] or 0,item=seg.item or rec.item,
                    out=rec.count,mats=rec.mats or {},cost=seg.cost,profession=seg.profession,segmentID=seg.segmentID}
            end
            return #out>0 and out or nil
        end
        return legacyExtract(result)
    end
    function T.SamePlan(run,result)
        if not run or not result then return false end
        if result==run.plan or result.planID and result.planID==run.planID then return true end
        return originSignature(run.plan)==originSignature(result)
    end
    function T.Rebase(run,list)
        -- Repainting a candidate is never authorization to rewrite a frozen run.
        return run and run.plan and originSignature(run.plan)==originSignature({executionSteps=list}) or false
    end
    function T.Progress(slug,index,run)
        run=run or XP.GetRun(slug);if not run then return end
        local i=index or run.currentIndex or 1;local p=XP.Progress(slug,i,nil,run.planID)
        if not p then return end
        local seg=steps(run.plan)[i];local rec=seg and recipe(seg,slug) or {}
        p.index=i;p.from=seg and seg[1];p.to=seg and seg[2];p.spell=seg and seg[3]
        p.item=seg and (seg.item or rec.item);p.mats=rec.mats or {};p.planned=seg and (seg[4] or 0) or 0
        p.outputs=p.actualOutputs or 0;p.remaining=p.remainingCrafts or 0;p.current=p.currentSkill
        p.started=(p.casts or 0)>0;p.over=p.extraCrafts and p.extraCrafts>0 or nil;p.finished=seg==nil or nil
        return p
    end
    function T.ProgressAll(slug)
        local run=T.GetRun(slug);if not run then return end
        local out={run=run,current=run.currentIndex or 1,finished=run.finished,steps={}}
        for i=1,#run.steps do out.steps[i]=T.Progress(slug,i,run) end;return out
    end
    T.RecordAttempt=XP.RecordAttempt
    function T.RecordOutput(slug,item,quantity,guid)
        return XP.RecordOutput({itemID=item,quantity=quantity or 1,castGUID=guid},"structured")
    end
    T.VerifyOutput=XP.VerifyOutput
    T.RecordCreatedText=XP.RecordCreatedMessage
    T.ContinueInventory=XP.GetContinuation
    function T.RecipeTotals(slug)
        local out={}
        for _,entry in ipairs(XP.GetRecipeTotals(slug)) do
            local item,quantity
            for id,n in pairs(entry.confirmedOutputs or {}) do item=item or id;quantity=(quantity or 0)+n end
            if (entry.casts or 0)>0 then
                local row=copy(entry);row.item=item;row.out=quantity or 0;out[#out+1]=row
            end
        end
        return out
    end
    function T.Summary(slug)
        local run=T.GetRun(slug) or T.History(slug)[1];if not run then return end
        local planned=0;for _,seg in ipairs(steps(run.plan)) do planned=planned+(seg[4] or 0) end
        return {planID=run.planID,status=run.status,current=run.currentIndex or 1,total=#steps(run.plan),
            done=min(#steps(run.plan),(run.currentIndex or 1)-1),planned=planned,casts=run.attemptsDone or 0,
            skill=skill(slug),target=run.plan.target,startSkill=run.startSkill,finished=run.finished,
            stale=run.plan.stale,staleReason=run.plan.staleReason}
    end
    T.GetPlan=XP.GetPlan;T.PrepareRecalculate=XP.PrepareRecalculate;T.PlanRecalculated=XP.PlanRecalculated
    T.GetSupplement=XP.GetSupplement;T.CalculateSupplement=XP.CalculateSupplement
    T.ConfirmConversion=XP.ConfirmConversion
    XP.OnChanged(function(slug,run,reason)
        compat(run)
        if T._Notify then T._Notify(slug,run,reason) end
    end)
end
if ns.Init then ns.Init(XP.Initialize) else XP.Initialize() end
