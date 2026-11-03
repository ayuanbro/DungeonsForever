local ns = _G.DF_NS or {}

if not ns.ProfessionDB then
    function ns.ProfessionDB(create)
        if ns.ProfessionStorage then return ns.ProfessionStorage.Get(create) end
        if create==false and type(_G.DungeonsForeverProfDB)~="table" then return nil end
        return ns.ProfDB().prof
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
local listeners, observationListeners, jobs = {}, {}, {}
local seenMem, seenOrder = {}, {}
local pendCast, pendOrder, pendLast = {}, {}, nil
local receiptMem, receiptOrder = {}, {}
local creditCaches = setmetatable({}, {__mode="k"})
local learningChecks = setmetatable({}, {__mode="k"})
local performance = {creditBuilds=0,historyScans=0}
local completionTimer, observationGeneration = false, 0
local idleTimer, checkingIdle, combatPaused
local IDLE_LIMIT = 48 * 60 * 60
local observedActive, observedReceipts
local floor, ceil, max, min = math.floor, math.ceil, math.max, math.min
local function now() return time and time() or 0 end
function XP.IsCombatPaused()
    return combatPaused or (InCombatLockdown and InCombatLockdown())
        or (UnitAffectingCombat and UnitAffectingCombat("player")) or false
end
local function integer(n) return type(n)=="number" and n>=0 and n==floor(n) and n<math.huge end
local function copy(v, seen)
    if type(v)~="table" then if type(v)~="function" and type(v)~="userdata" then return v end; return end
    local view=getmetatable(v)
    if type(view)=="table" and type(view.__profLearningMaterialize)=="function" then v=view.__profLearningMaterialize(v) end
    seen=seen or {}; if seen[v] then return end
    seen[v]=true; local out={}
    for k,x in pairs(v) do if type(k)=="string" or type(k)=="number" then out[k]=copy(x,seen) end end
    seen[v]=nil; return out
end
local function character() return E and E.CharacterKey and E.CharacterKey() or ((UnitName and UnitName("player") or "?").."-"..(GetRealmName and GetRealmName() or "?")) end
local function db()
    local prof=ns.ProfessionDB();prof.track=prof.track or {}
    local key=character(); local c=prof.track[key]
    if type(c)~="table" or c.version~=1 then c={version=1,nextID=0,active={},runs={},preparing={}}; prof.track[key]=c end
    c.active=c.active or {}; c.runs=c.runs or {}; c.preparing=c.preparing or {}
    c.continuation=c.continuation or {};c.endedContracts=c.endedContracts or {}
    return c
end
local function remember(set,order,key,limit)
    if not key then return false end
    if set[key] then return true end
    set[key]=true; order[#order+1]=key
    while #order>limit do set[table.remove(order,1)]=nil end
    return false
end
local function clearPending()
    pendCast,pendOrder,pendLast={},{},nil
end
local function cachePending(entry)
    pendLast=entry
    if entry.castGUID or entry.receiptKey then
        local pk=tostring(entry.castGUID or entry.receiptKey)
        if not pendCast[pk] then pendOrder[#pendOrder+1]=pk end
        pendCast[pk]=pendLast
        while #pendOrder>32 do pendCast[table.remove(pendOrder,1)]=nil end
    end
end
local function outputTotal(p,item)
    if not item then return end
    p.outputs=p.outputs or {}
    local total=p.outputs[item]
    if not total then total={actual=0,guaranteed=0,pending=0};p.outputs[item]=total end
    return total
end
local function steps(plan)
    local list=type(plan)=="table" and (plan.executionSteps or plan.steps)
    return type(list)=="table" and list or {}
end
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
    if E and E.StepsHaveNIP and E.StepsHaveNIP(steps(plan)) then return false end
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
local function requiredOutputs(seg,run)
    local required=quotaMap(seg.requiredOutputs)
    if run and not run.reserveDisabled then
        for item,n in pairs(seg.reserve and seg.reserve.requiredOutputs or {}) do required[item]=(required[item] or 0)+n end
    end
    local c=XP.Conversion(seg)
    if c and next(required)==nil then required[c.outputItemID]=c.outputCount*ceil(seg.expectedCrafts or seg[4] or 0) end
    return required
end
local function reserveAllowance(run,seg)
    if run.reserveDisabled then return run.reserveUsed and run.reserveUsed[seg.segmentID] or 0 end
    return seg.reserve and seg.reserve.extraCrafts or 0
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
function XP.ValidateLearning(plan,slug,seg)
    if seg and E and E.StepsHaveNIP and E.StepsHaveNIP({seg}) then return false,"catalogueFiltered" end
    if not (ns.IsForever and E and E.RouteRecipeEligibility) then return true end
    local current=E.LearningPolicyFingerprint and E.LearningPolicyFingerprint()
    if current and plan.learningPolicyFingerprint~=current then return false,"learningPolicyChanged" end
    if not seg or seg.checkpoint or XP.IsConversion(seg) or XP.IsSpecializationQuest(seg) then return true end
    local spell=seg.spell or seg[3]
    if type(spell)~="number" or spell<=0 then return true end
    local observation=E.LearningObservationFingerprint and E.LearningObservationFingerprint() or ""
    local store=E.ClientStore and E.ClientStore()
    local professions=E.Professions and E.Professions() or {}
    local profession=seg.profession or slug
    local pd=ns.ProfModule
    local pricing={allowBindOnPickupFormulas=pd and pd.Setting and pd.Setting("autoAllowBindOnPickupFormulas",slug) or false,
        allowCurrencyFormulas=pd and pd.Setting and pd.Setting("autoAllowCurrencyFormulas",slug) or false,
        allowLimitedFormulas=pd and pd.Setting and pd.Setting("autoBuyLimitedFormulas",slug) or false}
    local key=table.concat({tostring(current),tostring(observation),tostring(store and store.clientInputRevision or 0),
        tostring(seg.segmentID or spell),tostring(professions[profession] and professions[profession].cur),
        tostring(pricing.allowBindOnPickupFormulas),tostring(pricing.allowCurrencyFormulas),tostring(pricing.allowLimitedFormulas)},":")
    local cached=learningChecks[plan]
    if cached and cached.key==key and not cached.inventoryDependent then
        return cached.allowed,cached.reason,cached.detail
    end
    local rec=E.FindRecipe and E.FindRecipe(profession,spell) or seg.recipe
    local allowed,reason,detail
    if rec and E.SelectLearningRoute then
        allowed,reason,detail=E.SelectLearningRoute(rec,nil,nil,nil,nil,pricing)
    elseif rec then allowed,reason,detail=E.RouteRecipeEligibility(rec)
    else allowed,reason=false,"clientDataPending" end
    if allowed and detail and detail.quote and detail.quote.acquisitionPending then
        allowed,reason=false,"formulaAcquisitionPending"
    end
    local ra=ns.ProfRouteAuto
    local diagnostic=ra and ra.LearningDiagnostic and ra.LearningDiagnostic(reason,rec,detail)
        or {code=reason,spell=spell,profession=profession,missingReasons=detail and detail.missingReasons}
    local quote=detail and detail.quote
    learningChecks[plan]={key=key,allowed=allowed,reason=reason,detail=diagnostic,
        inventoryDependent=quote and (quote.id or quote.acquisitionPending or quote.source=="owned") and true or false}
    return allowed,reason,diagnostic
end
local function progressRecord(run,seg)
    local id=seg.segmentID; local p=run.progress[id]
    if not p then p={casts=0,outputs={}};run.progress[id]=p end
    p.outputs=p.outputs or {}
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
    run.progressVersion=(run.progressVersion or 0)+1;run.updatedAt=now()
    referencesChanged()
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
            if XP.IsConversion(seg) then for item,total in pairs(record.outputs) do
                ledger.confirmed[item]=(ledger.confirmed[item] or 0)+total.actual
                ledger.guaranteed[item]=(ledger.guaranteed[item] or 0)+total.guaranteed
            end end
            for item,n in pairs(requiredOutputs(seg)) do ledger.allocated[item]=(ledger.allocated[item] or 0)+n end
        end
        run.materialLedger=ledger
    end
    for _,fn in ipairs(listeners) do pcall(fn,run.slug,run,lifecycleReason) end
end
function XP.PerformanceCounters()
    return {creditBuilds=performance.creditBuilds,historyScans=performance.historyScans}
end
function XP.GetRun(slug) local c=db();return c.runs[c.active[slug]] end
function XP.Get(slug,planID)
    local run=planID and db().runs[planID]
    return run and run.slug==slug and run or nil
end
function XP.GetActive(slug)
    local run=XP.GetRun(slug);return run and run.status=="active" and run or nil
end
function XP.HasActive(slug)
    local c=db()
    if slug then local run=c.runs[c.active[slug]];return run~=nil and run.status=="active" end
    for _,id in pairs(c.active) do local run=c.runs[id];if run and run.status=="active" then return true end end
    return false
end
function XP.IsPreparing(slug) return db().preparing[slug]~=nil end
function XP.CanRevertCandidate(slug)
    local c=db();local preparing=c.preparing[slug];local source=c.continuation[slug]
    return not c.active[slug]
        and not (preparing and (preparing.hadActive or preparing.sourcePlanID))
        and not (source and source.sourcePlanID)
end
function XP.GetPlan(slug,planID)
    local run=planID and XP.Get(slug,planID) or not planID and XP.GetRun(slug)
    if run then return readablePlan(run) end
end
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
function XP.CanRemove(slug,planID)
    local c=db();local run=c.runs[planID]
    if not run or run.slug~=slug then return false end
    if run.status=="active" then return false end
    for _,id in pairs(c.active) do if id==planID then return false end end
    for _,sources in ipairs({c.preparing,c.continuation}) do
        for _,source in pairs(sources) do if source.sourcePlanID==planID then return false end end
    end
    for id,other in pairs(c.runs) do if id~=planID then
        local plan=type(other.plan)=="table" and other.plan or {}
        local opts=type(plan.executionOptions)=="table" and plan.executionOptions or {}
        if other.inheritedFrom==planID or other.originPlanID==planID
            or plan.executionSourcePlanID==planID or opts.executionSourcePlanID==planID then return false end
    end end
    return true
end
function XP.Remove(slug,planID)
    if not XP.CanRemove(slug,planID) then return false end
    local c=db();local run=c.runs[planID]
    c.runs[planID]=nil
    for _,contracts in pairs(c.endedContracts) do
        for signature,id in pairs(contracts) do if id==planID then contracts[signature]=true end end
    end
    local job=jobs[planID]
    if job then job.cancelled=true;jobs[planID]=nil end
    for i=#pendOrder,1,-1 do
        local key=pendOrder[i];local entry=pendCast[key]
        if entry and entry.run==run then pendCast[key]=nil;table.remove(pendOrder,i) end
    end
    if pendLast and pendLast.run==run then pendLast=nil end
    creditCaches[run]=nil;if run.plan then learningChecks[run.plan]=nil end
    referencesChanged()
    for _,fn in ipairs(listeners) do pcall(fn,slug,run,"removed") end
    if XP.RefreshObservation then XP.RefreshObservation() end
    return true
end
local function recorded(run)
    if type(run)~="table" then return false end
    if (run.attemptsDone or 0)>0 or (run.conversionsDone or 0)>0 then return true end
    for _,p in pairs(run.progress or {}) do
        if (p.casts or 0)>0 or p.questCompleted then return true end
        for _,total in pairs(p.outputs or {}) do
            if (total.actual or 0)>0 or (total.guaranteed or 0)>0 then return true end
        end
    end
    return false
end
local function pruneArchived(slug)
    local c=db()
    local removed
    repeat
        local list={}
        for id,r in pairs(c.runs) do
            if r.slug==slug and r.status~="active" and readablePlan(r) then
                list[#list+1]={id=id,run=r,at=tonumber(r.archivedAt or r.updatedAt) or 0}
            end
        end
        table.sort(list,function(a,b)
            if a.at~=b.at then return a.at>b.at end
            return tostring(a.id)>tostring(b.id)
        end)
        local kept=0;removed=false
        for _,entry in ipairs(list) do
            local hasFacts=recorded(entry.run)
            if hasFacts then kept=kept+1 end
            if (not hasFacts or kept>3) and XP.Remove(slug,entry.id) then removed=true end
        end
    until not removed
end
function XP.GetSummary(slug,planID)
    local run
    if planID then run=XP.Get(slug,planID) else run=XP.GetRun(slug) end
    if not run and not planID then run=XP.GetHistory(slug)[1] end
    if not run then return end
    local plan=readablePlan(run)
    if not plan then return nil,"historyUnreadable" end
    local list=steps(plan);local planned=0
    for _,seg in ipairs(list) do planned=planned+(seg[4] or 0) end
    return {planID=run.planID,status=run.status,archiveReason=run.archiveReason,
        current=run.currentIndex or 1,total=#list,done=min(#list,(run.currentIndex or 1)-1),
        planned=planned,casts=run.attemptsDone or 0,skill=skill(slug),
        target=plan.target or plan.targetSkill,startSkill=run.startSkill or plan.startSkill or plan.start,
        finished=run.finished or run.archiveReason=="completed" or run.status=="done",
        stale=plan.stale or run.status=="stale",staleReason=plan.staleReason or run.staleReason,
        learningBlocked=run.learningBlocked,learningBlockReason=run.learningBlockReason}
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
    return result
        and result.feasible ~= false
        and result.status ~= "searching"
        and result.status ~= "selection_required"
        and result.status ~= "recalculate_required"
        and #steps(result) > 0
end
local function originSignature(plan)
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
local function releaseSourceReferences(run)
    run.inheritedFrom=nil
    local plan=readablePlan(run)
    if plan then
        plan.executionSourcePlanID=nil
        if plan.executionOptions then plan.executionOptions.executionSourcePlanID=nil end
    end
end
local function archive(c,slug,reason)
    local run=c.runs[c.active[slug]]
    if run then
        run.status="archived";run.archivedAt=now();run.archiveReason=reason or "recalculate"
        releaseSourceReferences(run)
    end
    c.active[slug]=nil
    if c.trackingSlug==slug then c.trackingSlug=nil end
    return run
end
function XP.End(slug,reason)
    local c=db();local run=XP.GetRun(slug)
    local preparing=c.preparing[slug]
    if not run and preparing and preparing.sourcePlanID then run=c.runs[preparing.sourcePlanID] end
    c.preparing[slug]=nil
    if not run then
        c.active[slug]=nil;if c.trackingSlug==slug then c.trackingSlug=nil end
        if preparing and (preparing.sourcePlanID or type(preparing.inventory)=="table" and next(preparing.inventory)) then
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
    c.continuation[slug]=readablePlan(run) and {sourcePlanID=run.planID} or nil
    if run.originSignature then
        c.endedContracts[slug]=c.endedContracts[slug] or {};c.endedContracts[slug][run.originSignature]=run.planID
    end
    if c.trackingSlug==slug then c.trackingSlug=nil end
    changed(run,"ended")
    pruneArchived(slug)
    if XP.RefreshObservation then XP.RefreshObservation() end
    return run
end
local function idleOwners()
    local c=db();local owners={}
    for slug,id in pairs(c.active) do
        local run=c.runs[id];if run and run.status=="active" then owners[slug]=run end
    end
    for slug,pending in pairs(c.preparing) do
        if pending.hadActive then owners[slug]=owners[slug] or c.runs[pending.sourcePlanID] end
    end
    return owners
end
local function idleDeadline(run)
    return (run.lastCraftAt or run.createdAt)+IDLE_LIMIT
end
function XP.ExpireIdle()
    if checkingIdle then return end
    checkingIdle=true
    local at=now()
    for slug,run in pairs(idleOwners()) do if at>=idleDeadline(run) then
        local follow=ns.ProfFollow
        if follow and follow.SuspendAutoTrack then follow.SuspendAutoTrack(slug,"inactive") end
        XP.End(slug,"inactive")
    end end
    checkingIdle=nil
end
local function scheduleIdleCheck()
    local due
    for _,run in pairs(idleOwners()) do due=min(due or idleDeadline(run),idleDeadline(run)) end
    if idleTimer and due and idleTimer.due<=due then return end
    if idleTimer then idleTimer.handle:Cancel();idleTimer=nil end
    if due and C_Timer and C_Timer.NewTimer then
        local token={due=due};idleTimer=token
        token.handle=C_Timer.NewTimer(max(0.1,due-now()),function()
            if idleTimer~=token then return end
            idleTimer=nil;XP.ExpireIdle();XP.RefreshObservation()
        end)
    end
end
local function replicateScanReason()
    if not ns.IsForever then return end
    local bridge=ns.AuctionBridge
    if not (bridge and bridge.ReplicateScanReady) then return "replicateModeUnknown" end
    local ready,reason=bridge.ReplicateScanReady()
    if ready~=true then return reason or "replicateScanRequired" end
end
function XP.Bind(slug,result,opts)
    if XP.IsCombatPaused() then return nil,"combatPaused" end
    local scanReason=replicateScanReason()
    if scanReason then return nil,scanReason end
    XP.ExpireIdle()
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
        local learnable,learningReason=XP.ValidateLearning(existing.plan,slug,segment(existing))
        if not learnable then return nil,learningReason end
        c.trackingSlug=slug
        if XP.RefreshObservation then XP.RefreshObservation() end
        if ready(result) and result~=existing.plan and result.revision~=existing.plan.revision then existing.newPlanAvailable=true;existing.candidateRevision=result.revision end
        return existing
    end
    local normalized,reason=XP.NormalizePlan(slug,result)
    if not normalized then return nil,reason end
    if not catalogueAllowed(normalized) then return nil,"catalogueFiltered" end
    if not ready(normalized) then return nil,"pending" end
    local learnable,learningReason=XP.ValidateLearning(normalized,slug,steps(normalized)[1])
    if not learnable then return nil,learningReason end
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
    for _,seg in ipairs(steps(plan)) do for _,a in ipairs(seg.reserve and seg.reserve.allocations or {}) do
        if ids[a.consumerID] then a.consumerID=ids[a.consumerID] end
    end end
    for _,row in ipairs(plan.steps or {}) do for i,id in ipairs(row.segmentIDs or {}) do row.segmentIDs[i]=ids[id] or id end end
    local run={planID=planID,id=planID,originPlanID=normalized.planID or normalized.executionPlanID,
        originSignature=not (normalized.planID or normalized.executionPlanID) and originSignature(result) or nil,
        slug=slug,plan=plan,status="active",createdAt=now(),updatedAt=now(),progressVersion=0,startSkill=skill(slug),
        currentIndex=1,step=1,attemptsDone=0,progress={},supplements={},
        inheritedFrom=plan.executionSourcePlanID or plan.executionOptions and plan.executionOptions.executionSourcePlanID
            or opts.executionSourcePlanID or c.preparing[slug] and c.preparing[slug].sourcePlanID}
    local source=run.inheritedFrom and c.runs[run.inheritedFrom]
    if source and not opts.force then
        run.lastCraftAt=source.lastCraftAt or source.createdAt
        if now()>=idleDeadline(run) then return nil,"executionEnded" end
    end
    if source and not recorded(source) then releaseSourceReferences(run) end
    c.runs[planID]=run;c.active[slug]=planID;c.trackingSlug=slug;c.preparing[slug]=nil;c.continuation[slug]=nil
    XP.Sync(slug);changed(run);pruneArchived(slug)
    if XP.RefreshObservation then XP.RefreshObservation() end;return run
end
XP.Start=XP.Bind
function XP.StartNew(slug,result,opts)
    opts=copy(opts or {});opts.force=true
    return XP.Bind(slug,result,opts)
end
local function outputFacts(run,seg)
    local p=progressRecord(run,seg);local rec=recipe(seg,run.slug)
    local confirmed,guaranteed={},{};local pending=0
    for item,total in pairs(p.outputs) do
        confirmed[item]=total.actual;guaranteed[item]=total.guaranteed
        pending=pending+total.pending
    end
    return confirmed,guaranteed,pending,seg.item or rec.item or rec.makes
end
local function bagCount(item)
    if C_Item and C_Item.GetItemCount then
        local ok,n=pcall(C_Item.GetItemCount,item,false,false,false)
        if ok and integer(n) then return n end
    end
    if type(GetItemCount)=="function" then
        local ok,n=pcall(GetItemCount,item,false,false,false)
        if ok and integer(n) then return n end
    end
end
XP.BagCount=bagCount
local function skillComplete(run,seg,index,record,skillSnapshot)
    local cur=skill(seg.profession or run.slug,skillSnapshot);local goal=seg.goalSkill or seg[2]
    local skillDone=not goal or (cur~=nil and cur>=goal) or (seg.expectedGain or 0)<=0 and not seg.checkpoint
    if XP.Conversion(seg) then skillDone=true
    elseif seg.checkpoint or seg[3]==0 then skillDone=cur~=nil and goal~=nil and cur>=goal end
    local fractional=seg.fractionalTransition or (seg.expectedGain or 0)>0 and seg[2]==seg[1] and seg.attemptLimit~=nil
    if not skillDone and fractional and (record.casts or 0)>=ceil(seg.attemptLimit-1e-9) then
        local following=steps(run.plan)[index+1]
        if following then
            local nextRecipe=recipe(following,run.slug);local nextSkill=skill(following.profession or run.slug,skillSnapshot)
            if following.checkpoint or (nextSkill and type(nextRecipe.learn)=="number" and nextSkill>=nextRecipe.learn) then skillDone=true end
        end
    end
    return skillDone,cur,goal
end
local function creditsFor(run,target,skillSnapshot)
    local inventory,skillState={},{}
    skillSnapshot=skillSnapshot or E and E.Professions and E.Professions()
    for _,seg in ipairs(steps(run.plan)) do
        local profession=seg.profession or run.slug
        if not skillState[profession] then skillState[profession]={cur=skill(profession,skillSnapshot)} end
        for item in pairs(requiredOutputs(seg,run)) do
            if inventory[item]==nil then inventory[item]=bagCount(item) or false end
        end
    end
    local cached=creditCaches[run];local same=cached and cached._version==(run.creditVersion or 0)
    if same then for item,n in pairs(inventory) do if cached._inventory[item]~=n then same=false;break end end end
    if same then for profession,state in pairs(skillState) do
        if not cached._skills[profession] or cached._skills[profession].cur~=state.cur then same=false;break end
    end end
    if same and cached[target.segmentID] then return cached[target.segmentID] end
    performance.creditBuilds=performance.creditBuilds+1
    local list,bySegment,used={},{},{}
    for index,seg in ipairs(steps(run.plan)) do
        local record=progressRecord(run,seg)
        local funded=ceil((seg.expectedCrafts or seg[4] or 0)+(record.supplementAllowance or 0)+reserveAllowance(run,seg)-1e-9)
        local casts=min(record.casts or 0,funded)
        if XP.IsSpecializationQuest(seg) then funded=1;casts=record.questCompleted and 1 or 0 end
        local o={seg=seg,index=index,record=record,funded=funded,required=requiredOutputs(seg,run),
            consumed={},waived={},destinations={},released={}}
        list[#list+1]=o;bySegment[seg.segmentID]=o;used[seg.segmentID]={}
        for _,m in ipairs(recipe(seg,run.slug).mats or {}) do
            used[seg.segmentID][m[1]]=(used[seg.segmentID][m[1]] or 0)+m[2]*casts
        end
    end
    for _,o in ipairs(list) do
        local allocations=copy(o.seg.allocations or {})
        if not run.reserveDisabled then for _,a in ipairs(o.seg.reserve and o.seg.reserve.allocations or {}) do allocations[#allocations+1]=a end end
        for _,a in ipairs(allocations) do
            if a.itemID and a.consumerID and (a.count or 0)>0 then
                local dest=o.destinations[a.itemID] or {};o.destinations[a.itemID]=dest
                dest[a.consumerID]=(dest[a.consumerID] or 0)+a.count
            end
        end
        for item,required in pairs(o.required) do
            local dest=o.destinations[item]
            if not dest then
                dest={};o.destinations[item]=dest;local left=required
                for index=o.index+1,#list do
                    local consumer=list[index]
                    for _,m in ipairs(recipe(consumer.seg,run.slug).mats or {}) do if m[1]==item then
                        local n=min(left,m[2]*consumer.funded)
                        dest[consumer.seg.segmentID]=(dest[consumer.seg.segmentID] or 0)+n;left=left-n
                    end end
                    if left<=0 then break end
                end
            end
            for _,consumer in ipairs(list) do
                local id=consumer.seg.segmentID;local n=min(dest[id] or 0,used[id][item] or 0)
                n=min(n,max(0,required-(o.consumed[item] or 0)-(o.waived[item] or 0)))
                if n>0 then
                    local totals=XP.IsSpecializationQuest(consumer.seg) and o.waived or o.consumed
                    totals[item]=(totals[item] or 0)+n;dest[id]=dest[id]-n;used[id][item]=used[id][item]-n
                end
            end
        end
    end
    local function allocateBags()
        local stock=copy(inventory)
        for _,o in ipairs(list) do
            o.credited={};o.available={};o.unknown=false
            for item,required in pairs(o.required) do
                local missing=max(0,required-(o.consumed[item] or 0)-(o.waived[item] or 0))
                local available=stock[item];local n=min(missing,available or 0)
                if available==false and missing>0 then o.unknown=true end
                o.available[item]=n;o.credited[item]=(o.consumed[item] or 0)+n
                if available then stock[item]=available-n end
            end
        end
    end
    for pass=1,#list+1 do
        allocateBags();local changed=false
        for index=#list,1,-1 do
            local consumer=list[index];local seg=consumer.seg
            if not consumer.unknown and not seg.checkpoint and not XP.IsSpecializationQuest(seg)
                and skillComplete(run,seg,index,consumer.record,skillState) then
                local rec=recipe(seg,run.slug);local needed=0;local output=seg.item or rec.item
                local per=seg.outputMin or rec.outputMin or rec.count or 1
                for item,n in pairs(consumer.required) do
                    local remaining=max(0,n-(consumer.credited[item] or 0)-(consumer.waived[item] or 0))
                    if remaining>0 then needed=max(needed,item==output and per>0 and ceil(remaining/per) or math.huge) end
                end
                local unused=max(0,consumer.funded-(consumer.record.casts or 0)-needed)
                for _,m in ipairs(rec.mats or {}) do
                    local item=m[1];local desired=unused*m[2];local delta=max(0,desired-(consumer.released[item] or 0))
                    consumer.released[item]=max(consumer.released[item] or 0,desired)
                    for _,o in ipairs(list) do
                        local dest=o.destinations[item];local id=seg.segmentID
                        local n=min(delta,dest and dest[id] or 0,max(0,(o.required[item] or 0)-(o.consumed[item] or 0)-(o.waived[item] or 0)))
                        if n>0 then o.waived[item]=(o.waived[item] or 0)+n;dest[id]=dest[id]-n;delta=delta-n;changed=true end
                        if delta<=0 then break end
                    end
                end
            end
        end
        if not changed then break end
    end
    allocateBags()
    bySegment._version=run.creditVersion or 0;bySegment._inventory=inventory;bySegment._skills=skillState;creditCaches[run]=bySegment
    return bySegment[target.segmentID]
end
function XP.GetRecipeTotals(slug,planID,fresh)
    local run=planID and db().runs[planID] or XP.GetRun(slug)
    if not run or run.slug~=slug then return {} end
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
local function progressFor(run,slug,id,skillSnapshot,baseOnly)
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
    local credit=run.previewCredits and run.previewCredits[seg.segmentID] or creditsFor(run,seg,skillSnapshot)
    local reused,reusedActual,fulfilled,waived=credit.available,credit.available,credit.credited,credit.waived
    local required=baseOnly and quotaMap(seg.requiredOutputs) or requiredOutputs(seg,run);local remaining={};local materialDone=true
    for item,n in pairs(required) do remaining[item]=max(0,n-(fulfilled[item] or 0)-(waived[item] or 0));if remaining[item]>0 then materialDone=false end end
    local skillDone,cur,goal=skillComplete(run,seg,index,p,skillSnapshot)
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
    local baseLimit=ceil((seg.attemptLimit or seg.expectedCrafts or seg[4] or 0)-1e-9)
    local allowance=reserveAllowance(run,seg)
    local limit=baseLimit+allowance+(p.supplementAllowance or 0)
    local reserveRemaining=not run.reserveDisabled and max(0,allowance-max(0,(p.casts or 0)-baseLimit)) or 0
    local direct={};for _,m in ipairs(rec.mats or {}) do direct[#direct+1]={id=m[1],count=m[2]*remainingCrafts,perCraft=m[2]} end
    local result={segmentID=seg.segmentID,index=index,kind=seg.kind,complete=skillDone and materialDone,skillDone=skillDone,skillMet=skillDone,materialDone=materialDone,
        currentSkill=cur,goalSkill=goal,attemptsDone=p.casts or 0,casts=p.casts or 0,minimumCrafts=seg.materialMinCrafts or 0,minCrafts=seg.materialMinCrafts or 0,
        outputItem=output,requiredOutputs=required[output] or 0,actualOutputs=confirmed[output] or 0,confirmedOutputs=confirmed[output] or 0,
        guaranteedOutputs=guaranteed[output] or 0,pendingOutputs=pending,remainingOutputs=remaining[output] or 0,
        reusedOutputs=reused[output] or 0,reusedConfirmedOutputs=reusedActual[output] or 0,
        resolvedByQuestOutputs=waived[output] or 0,resolvedByQuestByItem=waived,
        fulfilledOutputs=fulfilled[output] or 0,divertedOutputs=max(0,min(required[output] or 0,(guaranteed[output] or 0)+(reused[output] or 0))-(fulfilled[output] or 0)),
        requiredByItem=required,confirmedByItem=confirmed,guaranteedByItem=guaranteed,remainingByItem=remaining,
        remainingCrafts=remainingCrafts,expectedRemaining=levelCrafts,attemptLimit=limit,extraCrafts=max(0,(p.casts or 0)+remainingCrafts-limit),
        reserveAllowance=allowance,reserveRemaining=reserveRemaining,
        baseRemaining=max(0,limit-(p.casts or 0)-reserveRemaining),
        exhausted=(p.casts or 0)>=limit and not (skillDone and materialDone),blocked=grey or credit.unknown,inventoryUnknown=credit.unknown or nil,reason=credit.unknown and "inventoryUnknown" or nil,directMaterials=direct,outputConflict=p.outputConflict}
    if conversion then
        result.manualConversion=true
        result.plannedConversions=ceil(seg.expectedCrafts or seg[4] or 0)
        result.confirmedConversions=p.casts or 0;result.remainingConversions=remainingCrafts
        result.sourceItem=conversion.inputItemID;result.sourcePerConversion=conversion.inputCount
        result.targetItem=conversion.outputItemID;result.targetPerConversion=conversion.outputCount
        result.remainingInput=remainingCrafts*conversion.inputCount;result.remainingOutput=remainingCrafts*conversion.outputCount
    end
    if not result.complete and index==(run.currentIndex or 1) and run.status~="archived" then
        local allowed,reason,detail=XP.ValidateLearning(run.plan,slug,seg)
        if not allowed then
            result.blocked=true;result.learningBlocked=true;result.reason=reason;result.learningDetail=detail
        end
    end
    return result
end
function XP.Progress(slug,id,skillSnapshot,planID)
    local run=planID and db().runs[planID] or XP.GetRun(slug);if not run or run.slug~=slug then return nil end
    return progressFor(run,slug,id,skillSnapshot)
end
function XP.PreviewProgress(slug,plan)
    if type(plan)~="table" or plan.executionVersion~=1 then return {} end
    local run={slug=slug,plan=plan,progress={},status="archived",currentIndex=1,creditVersion=0}
    local snapshot=E and E.Professions and E.Professions()
    local out={}
    for _,seg in ipairs(steps(plan)) do
        if seg.segmentID then
            local progress=progressFor(run,slug,seg.segmentID,snapshot)
            run.previewCredits=creditCaches[run]
            local base=progressFor(run,slug,seg.segmentID,snapshot,true)
            progress.baseCrafts=max(base.remainingCrafts or 0,(progress.remainingCrafts or 0)-(seg.reserve and seg.reserve.extraCrafts or 0))
            out[seg.segmentID]=progress
        end
    end
    return out
end
function XP.GetProgressAll(slug)
    local run=XP.GetRun(slug);if not run then return end
    local plan=readablePlan(run);if not plan then return nil,"historyUnreadable" end
    local out={run=run,current=run.currentIndex or 1,finished=run.finished,steps={}}
    local snapshot=E and E.Professions and E.Professions()
    for i=1,#steps(plan) do out.steps[i]=XP.Progress(slug,i,snapshot,run.planID) end
    return out
end
function XP.SkipReserve(slug)
    local run=XP.GetRun(slug);if not run then return false end
    if run.reserveDisabled then return true end
    run.reserveUsed={}
    for _,seg in ipairs(steps(run.plan)) do
        local used=min(reserveAllowance(run,seg),max(0,(progressRecord(run,seg).casts or 0)-(seg.expectedCrafts or seg[4] or 0)))
        if used>0 then run.reserveUsed[seg.segmentID]=used end
    end
    run.reserveDisabled=true;invalidateCredits(run);XP.Sync(slug);changed(run);return true
end
function XP.SafeCraftCount(slug,id,requested)
    local run=XP.GetRun(slug);local seg,index
    if run then seg,index=segment(run,id) end
    if not seg or not run.plan.reserve or run.plan.reserve.mode=="off" or run.reserveDisabled then return requested end
    local p=XP.Progress(slug,id)
    if not p or p.complete then return 0 end
    local base=p.baseRemaining or 0
    local count=min(requested,base+(p.reserveRemaining or 0))
    local baseOther,extraOther,earlierBase={},{},{}
    for i=1,#steps(run.plan) do
        local future=steps(run.plan)[i];local progress=XP.Progress(slug,future.segmentID)
        if i~=index and progress and not progress.complete then
            local n=min(progress.remainingCrafts or 0,progress.baseRemaining or 0)
            if XP.IsSpecializationQuest(future) then n=1 end
            for _,m in ipairs(recipe(future,slug).mats or {}) do
                baseOther[m[1]]=(baseOther[m[1]] or 0)+m[2]*n
                extraOther[m[1]]=(extraOther[m[1]] or 0)+m[2]*(progress.reserveRemaining or 0)
                if i<index then earlierBase[m[1]]=(earlierBase[m[1]] or 0)+m[2]*n end
            end
        end
    end
    for _,m in ipairs(recipe(seg,slug).mats or {}) do
        local stock=bagCount(m[1]);if stock==nil then return 0,"inventoryUnknown" end
        local basic=min(base,count,floor(max(0,stock-(earlierBase[m[1]] or 0))/m[2]))
        local extra=max(0,floor((stock-basic*m[2]-(baseOther[m[1]] or 0)-(extraOther[m[1]] or 0))/m[2]))
        count=min(count,basic+extra)
    end
    return max(0,count)
end
function XP.Sync(slug,result)
    if ns.ProfessionTracking and not ns.ProfessionTracking.IsEnabled() then return end
    XP.ExpireIdle()
    if XP.IsCombatPaused() then return XP.GetRun(slug) end
    local run=XP.GetRun(slug)
    if not run and result then run=XP.Bind(slug,result) end
    if not run then return end
    if not readablePlan(run) then return nil,"historyUnreadable" end
    local observed=false
    for _,seg in ipairs(steps(run.plan)) do
        if XP.IsSpecializationQuest(seg) then
            local goal=XP.SpecializationQuest(seg);local p=progressRecord(run,seg)
            if not p.questCompleted and E and E.SpecializationKnown and E.SpecializationKnown(goal.abilityID)==true then
                p.questCompleted=true;p.questCompletedAt=now()
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
    local currentProgress=not run.finished and XP.Progress(slug,index,skillSnapshot)
    run.learningBlocked=currentProgress and currentProgress.learningBlocked or nil
    run.learningBlockReason=currentProgress and currentProgress.learningBlocked and currentProgress.reason or nil
    if run.finished then
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
local function matchingReceipt(a,receipt)
    return a and a.item==receipt.itemID and (not receipt.slug or a.run.slug==receipt.slug)
        and (not receipt.spellID or a.spell==receipt.spellID)
        and db().runs[a.run.planID]==a.run
end
local function receiptFallback(receipt)
    local c=db();local slugs={}
    if receipt.slug then slugs[1]=receipt.slug
    else
        if c.trackingSlug then slugs[1]=c.trackingSlug end
        for slug in pairs(c.active) do if slug~=c.trackingSlug then slugs[#slugs+1]=slug end end
    end
    for _,slug in ipairs(slugs) do
        local run=XP.GetRun(slug)
        if run and readablePlan(run) then
            local list=steps(run.plan)
            for i=#list,1,-1 do
                local seg=list[i];local p=run.progress[seg.segmentID]
                if not seg.checkpoint and not XP.IsConversion(seg) and not XP.IsSpecializationQuest(seg)
                    and seg.item==receipt.itemID and (not receipt.spellID or seg[3]==receipt.spellID)
                    and p and (p.casts or 0)>0 then
                    local total=outputTotal(p,receipt.itemID);local pending=total.pending>0
                    return {run=run,progress=p,step=seg.segmentID,item=seg.item,spell=seg[3],
                        minimum=pending and (seg.outputMin or recipe(seg,slug).count or 0) or 0,
                        pending=pending,sources={},castGUID=receipt.castGUID}
                end
            end
        end
    end
end
local function acceptReceipt(receipt,matched)
    local hit=matched or receipt.castGUID and pendCast[tostring(receipt.castGUID)]
    if hit and not matchingReceipt(hit,receipt) then return false end
    if not hit and matchingReceipt(pendLast,receipt)
        and (not receipt.castGUID or not pendLast.castGUID or receipt.castGUID==pendLast.castGUID)
        and not pendLast.sources[receipt.source] then hit=pendLast end
    if not hit and not receipt.castGUID then
        for _,a in pairs(pendCast) do
            if matchingReceipt(a,receipt) and not a.sources[receipt.source] then hit=a;break end
        end
    end
    if not hit then
        hit=receiptFallback(receipt)
        if not hit then return false end
        cachePending(hit)
    end
    if hit.sources[receipt.source] then return true end
    local p,run=hit.progress,hit.run
    local previous=hit.actual
    hit.sources[receipt.source]={quantity=receipt.quantity}
    local preferred=hit.sources.structured or hit.sources.manual or hit.sources.chat
    hit.actual=preferred and preferred.quantity or hit.actual
    if not hit.verified and hit.actual~=previous then
        local total=outputTotal(p,hit.item)
        total.actual=total.actual+(hit.actual or 0)-(previous or 0)
        total.guaranteed=total.guaranteed+(hit.actual or hit.minimum)-(previous or hit.minimum)
        if hit.pending and previous==nil and hit.actual~=nil then total.pending=max(0,total.pending-(hit.pendingCrafts or 1)) end
    end
    if hit.actual and hit.actual<hit.minimum then p.outputConflict=true end
    if hit.sources.structured and hit.sources.chat and hit.sources.structured.quantity~=hit.sources.chat.quantity then p.outputConflict=true end
    invalidateCredits(run)
    if XP.IsCombatPaused() then
        run.progressVersion=(run.progressVersion or 0)+1;run.updatedAt=now()
        return true
    end
    if run.status=="active" then XP.Sync(run.slug) end
    changed(run);return true
end
function XP.RecordOutput(data,source,crafted)
    if ns.ProfessionTracking and not ns.ProfessionTracking.IsEnabled() then return end
    XP.ExpireIdle()
    if type(data)~="table" then return false,"invalid_receipt" end
    local receipt={itemID=tonumber(data.itemID or data.id),quantity=tonumber(data.quantity or data.count),
        source=source or data.source or "structured",castGUID=data.castGUID and tostring(data.castGUID),
        spellID=tonumber(data.spellID or data.recipeID),slug=data.slug}
    if not integer(receipt.itemID) or receipt.itemID<=0 or not integer(receipt.quantity) or receipt.quantity<=0 then return false,"invalid_receipt" end
    local id=data.receiptID or data.eventID
    local key=id and receipt.source..":"..tostring(id)
    if key and receiptMem[key] then return true,"duplicate" end
    receipt.eventKey=key
    local matched
    if XP.IsCombatPaused() then
        matched=receipt.castGUID and pendCast[receipt.castGUID]
            or not receipt.castGUID and matchingReceipt(pendLast,receipt) and pendLast
        if not matchingReceipt(matched,receipt) then return false,"combatPaused" end
        crafted=false
    end
    if crafted then
        local reason
        matched,reason=XP.CraftFallback(receipt)
        if not matched then return reason=="duplicate",reason end
        if receipt.castGUID then
            matched.castGUID=receipt.castGUID;remember(seenMem,seenOrder,receipt.castGUID,512)
        end
        matched.at=matched.at or now();cachePending(matched)
    end
    if not acceptReceipt(receipt,matched) then return false,"unmatched" end
    remember(receiptMem,receiptOrder,key,256)
    return true
end
function XP.RecordAttempt(slug,spellID,castGUID,id,inferred)
    if ns.ProfessionTracking and not ns.ProfessionTracking.IsEnabled() then return end
    XP.ExpireIdle()
    if XP.IsCombatPaused() then return false,"combatPaused" end
    if castGUID then
        castGUID=tostring(castGUID)
        if seenMem[castGUID] then return false,"duplicate" end
    end
    if not inferred then
        local function late(a)
            return a and a.run.slug==slug and a.spell==spellID and db().runs[a.run.planID]==a.run
                and (a.inferredRemaining or 0)>0 and now()-(a.at or 0)<2
        end
        local hit=late(pendLast) and pendLast
        if not hit then for _,a in pairs(pendCast) do if late(a) then hit=a;break end end end
        if hit then
            hit.inferredRemaining=hit.inferredRemaining-1
            if castGUID then
                remember(seenMem,seenOrder,castGUID,512);hit.castGUID=castGUID;cachePending(hit)
            end
            return false,"duplicate"
        end
    end
    local run=XP.GetRun(slug);if not run or run.status~="active" or type(spellID)~="number" then return false end
    if not readablePlan(run) then return false,"historyUnreadable" end
    local seg=matchingSegment(run,spellID,id);if not seg or XP.IsSpecializationQuest(seg) or XP.IsConversion(seg) then return false end
    remember(seenMem,seenOrder,castGUID,512)
    local rec=recipe(seg,slug);local p=progressRecord(run,seg)
    local a={run=run,progress=p,step=seg.segmentID,castGUID=castGUID,spell=spellID,
        item=seg.item or rec.item or rec.makes,minimum=seg.outputMin or rec.outputMin or rec.count or 0,
        pending=true,sources={},at=now()}
    local total=outputTotal(p,a.item)
    if total then total.guaranteed=total.guaranteed+a.minimum;total.pending=total.pending+1 end
    p.casts=(p.casts or 0)+1;run.attemptsDone=(run.attemptsDone or 0)+1
    run.lastCraftAt=now()
    cachePending(a)
    if run.completionDue then run.completionDue=now()+2 end
    invalidateCredits(run)
    XP.Sync(slug);changed(run);if XP.RefreshObservation then XP.RefreshObservation() end;return true,a
end
function XP.CraftFallback(receipt)
    local guid=receipt.castGUID
    local hit=guid and pendCast[guid]
    if hit then
        if matchingReceipt(hit,receipt) then return hit end
        return nil,"wrong_receipt"
    end
    if guid and seenMem[guid] then return nil,"unmatched" end
    local function pending(a)
        return matchingReceipt(a,receipt) and not a.sources.structured
            and (not guid or not a.castGUID)
    end
    if pending(pendLast) then return pendLast end
    for _,a in pairs(pendCast) do if pending(a) then return a end end
    if not guid and not receipt.eventKey and matchingReceipt(pendLast,receipt)
        and pendLast.sources.structured and now()-(pendLast.at or 0)<3 then
        return nil,pendLast.sources.structured.quantity==receipt.quantity and "duplicate" or "ambiguous_receipt"
    end
    hit=receiptFallback(receipt)
    if hit and hit.pending then
        local known,visited=0,{}
        local function countKnown(a)
            if a and not visited[a] and a.run==hit.run and a.progress==hit.progress
                and a.item==hit.item and a.pending and a.actual==nil then
                visited[a]=true;known=known+(a.pendingCrafts or 1)
            end
        end
        countKnown(pendLast);for _,a in pairs(pendCast) do countKnown(a) end
        if outputTotal(hit.progress,hit.item).pending>known then return hit end
    end

    local found,chosen
    for slug,id in pairs(db().active) do
        local run=db().runs[id]
        if (not receipt.slug or receipt.slug==slug) and run and run.status=="active" and readablePlan(run) then
            local list=steps(run.plan);local cur=run.currentIndex or 1
            for offset=0,#list-1 do
                local index=(cur-1+offset)%#list+1;local seg=list[index]
                if not seg.checkpoint and not seg.navigationOnly and not XP.IsConversion(seg) and not XP.IsSpecializationQuest(seg)
                    and seg.item==receipt.itemID and (not receipt.spellID or seg[3]==receipt.spellID) then
                    if found and (found~=run or chosen[3]~=seg[3] or chosen.profession~=seg.profession) then
                        return nil,"ambiguous_recipe"
                    end
                    if not found then found,chosen=run,seg end
                end
            end
        end
    end
    if not found then return nil,"no_step" end
    local count=1
    if not guid then
        local rec=recipe(chosen,found.slug)
        local lo=chosen.outputMin or rec.outputMin or rec.count
        local hi=chosen.outputMax or rec.outputMax or lo
        if not integer(lo) or lo<=0 or not integer(hi) or hi<lo then return nil,"unknown_output" end
        local least,most=ceil(receipt.quantity/hi),floor(receipt.quantity/lo)
        if least~=most or least<1 or least>5 then return nil,"ambiguous_quantity" end
        count=least
    end
    local entry
    for _=1,count do
        local ok,a=XP.RecordAttempt(found.slug,chosen[3],guid,chosen.segmentID,true)
        if not ok then return nil,a or "inactive" end
        entry=a
    end
    entry.minimum=entry.minimum*count;entry.pendingCrafts=count
    entry.inferredRemaining=not guid and count or 0
    entry.receiptKey=receipt.eventKey and "receipt:"..receipt.eventKey
    cachePending(entry)
    return entry
end
function XP.RecordCraftedResult(data,quantity)
    if type(data)~="table" then data={itemID=data,quantity=quantity} end
    return XP.RecordOutput(data,"structured",true)
end
function XP.ConfirmConversion(slug,id,count,planID)
    if ns.ProfessionTracking and not ns.ProfessionTracking.IsEnabled() then return end
    XP.ExpireIdle()
    if XP.IsCombatPaused() then return false,"combatPaused" end
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
    local record=progressRecord(run,seg);local total=outputTotal(record,conversion.outputItemID)
    total.actual=total.actual+count*conversion.outputCount
    total.guaranteed=total.guaranteed+count*conversion.outputCount
    record.casts=(record.casts or 0)+count;record.verifiedAt=now()
    run.conversionsDone=(run.conversionsDone or 0)+count
    run.lastCraftAt=now()
    invalidateCredits(run)
    XP.Sync(slug);changed(run);if XP.RefreshObservation then XP.RefreshObservation() end
    return true,count
end
function XP.VerifyOutput(slug,id,item,total)
    XP.ExpireIdle()
    if XP.IsCombatPaused() then return false,"combatPaused" end
    if not integer(item) or item<=0 or not integer(total) then return false,"invalid_quantity" end
    local run=XP.GetRun(slug);if not run then return false,"no_execution" end
    if not readablePlan(run) then return false,"historyUnreadable" end
    local seg=segment(run,id);if not seg then return false,"unknown_segment" end
    if XP.IsConversion(seg) then return false,"manual_conversion_required" end
    local rec=recipe(seg,slug)
    if item~=(seg.item or rec.item or rec.makes) then return false,"wrong_item" end
    local p=progressRecord(run,seg);local value=outputTotal(p,item)
    value.actual=total;value.guaranteed=total;value.pending=0;p.verifiedAt=now()
    if pendLast and pendLast.progress==p and pendLast.item==item then pendLast.verified=true end
    for _,a in pairs(pendCast) do if a.progress==p and a.item==item then a.verified=true end end
    invalidateCredits(run)
    XP.Sync(slug);changed(run);return true
end
function XP.GetContinuation(slug)
    local c=db();local run=XP.GetRun(slug)
    if not run then
        local source=c.preparing[slug] or c.continuation[slug];run=source and c.runs[source.sourcePlanID]
        if not run and source and source.sourcePlanID then return nil,"historyUnreadable" end
    end
    if not run then return {} end
    if not readablePlan(run) then return nil,"historyUnreadable" end
    local items={}
    for _,seg in ipairs(steps(run.plan)) do
        local rec=recipe(seg,slug)
        for _,m in ipairs(rec.mats or {}) do items[m[1]]=true end
        local output=seg.item or rec.item or rec.makes
        if output then items[output]=true end
    end
    for _,purchase in ipairs(run.plan.mats or {}) do
        local item=purchase.id or purchase[1];if item then items[item]=true end
    end
    local inventory={}
    for item in pairs(items) do
        local n=bagCount(item)
        if n==nil then return nil,"inventoryUnknown" end
        if n>0 then inventory[item]=n end
    end
    return inventory
end
function XP.PrepareRecalculate(slug)
    local c=db();local run=XP.GetRun(slug);local seed,reason=XP.GetContinuation(slug)
    if not seed then return nil,nil,reason or "historyUnreadable" end
    local previous=c.preparing[slug]
    local source=c.continuation[slug]
    local preparing={hadActive=run~=nil and run.status=="active" or previous and previous.hadActive or false,
        sourcePlanID=run and run.planID or previous and previous.sourcePlanID or source and source.sourcePlanID,inventory=copy(seed)}
    if run then archive(c,slug,"recalculate");changed(run) end
    c.preparing[slug]=preparing;referencesChanged();pruneArchived(slug)
    if XP.RefreshObservation then XP.RefreshObservation() end;return seed,preparing.sourcePlanID
end
function XP.PlanRecalculated(slug,result)
    local c=db();local p=c.preparing[slug]
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
    local plan=readablePlan(run)
    if not plan then return false,"historyUnreadable" end
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
    local scanReason=replicateScanReason()
    if scanReason then return nil,scanReason end
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
    if p.learningBlocked then return nil,p.reason or "learningDataMissing" end
    if p.extraCrafts<=0 then return nil,"planned_attempts_remaining" end
    if p.blocked and not p.skillDone then return nil,"skill_gap" end
    local extra=max(1,p.extraCrafts);local demands={};local rec=recipe(seg,slug)
    for _,m in ipairs(rec.mats or {}) do demands[m[1]]=(demands[m[1]] or 0)+m[2]*extra end
    local inventory,reason=XP.GetContinuation(slug);if not inventory then return nil,reason end
    local version=run.progressVersion;local state={status="searching",inFlight=true,feasible=false,segmentID=seg.segmentID,extraCrafts=extra,mats={},formulas={},total=0,revision=#run.supplements+1}
    run.supplement=state
    local task={run=run,version=version,state=state};jobs[run.planID]=task
    local co=coroutine.create(function()
        local opts=copy(run.plan.executionOptions or {});opts.snapshot=nil
        opts.materialProfession=slug;opts.executionInventory=copy(inventory);opts.defer=true
        local snap=E.Capture(slug,opts,function() coroutine.yield() end)
        snap.known=snap.known or {}
        for _,step in ipairs(steps(run.plan)) do
            if (progressRecord(run,step).casts or 0)>0 then snap.known[(step.profession or slug)..":"..step[3]]=true end
        end
        local reserved={}
        for _,future in ipairs(steps(run.plan)) do
            local record=progressRecord(run,future)
            local allowance=(future.attemptLimit or future.expectedCrafts or future[4] or 0)+(record.supplementAllowance or 0)+reserveAllowance(run,future)
            local remaining=max(0,allowance-(record.casts or 0))
            if XP.IsSpecializationQuest(future) then remaining=record.questCompleted and 0 or 1
            else
                local progress=XP.Progress(slug,future.segmentID)
                remaining=min(remaining,progress and progress.remainingCrafts or remaining)
            end
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
        if j then while coroutine.status(j.co)~="dead" and not j.finished and (j.status~="error" or j.finalizing) do S.Run(j,ns.ProfIdle and ns.ProfIdle.SliceCap and ns.ProfIdle.SliceCap(2) or 2);coroutine.yield() end;result=j.result or S.Result(j,j.best,j.status) end
        return result
    end)
    local function pump()
        if task.cancelled then return true end
        local scanReason=replicateScanReason()
        if scanReason then
            state.status="recalculate_required";state.error=scanReason;state.feasible=false;state.inFlight=false
            state.diagnostics={{code=scanReason}};jobs[run.planID]=nil
            if callback then pcall(callback,state) end
            return true
        end
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
    if ns.ProfIdle and ns.ProfIdle.Defer then ns.ProfIdle.Defer(task,pump,"normal")
    elseif ns.ProfIdle and ns.ProfIdle.Add then ns.ProfIdle.Add(pump)
    elseif C_Timer and C_Timer.After then local function later() if not pump() then C_Timer.After(0,later) end end;C_Timer.After(0,later)
    else while not pump() do end end
    return state
end
function XP.Pump(slug) local run=XP.GetRun(slug);local j=run and jobs[run.planID];if j then return j.pump() end end
local executionEvents={"BAG_UPDATE_DELAYED","UNIT_SPELLCAST_SUCCEEDED","SKILL_LINES_CHANGED","CHAT_MSG_SKILL","SPELLS_CHANGED","LEARNED_SPELL_IN_TAB","QUEST_TURNED_IN"}
local receiptEvents={"TRADE_SKILL_ITEM_CRAFTED_RESULT","CHAT_MSG_LOOT"}
local observedEvents={}
function XP.RefreshObservation()
    if ns.ProfessionTracking and not ns.ProfessionTracking.IsEnabled() then if XP.DisableTracking then XP.DisableTracking() end;return false,false end
    XP.ExpireIdle()
    local c=db();local at=now()
    local tracking=false
    for _,id in pairs(c.active) do
        local run=c.runs[id]
        if run and run.status=="active" and readablePlan(run) then tracking=true;break end
    end
    local paused=XP.IsCombatPaused()
    local active=tracking and not paused;local receipts=active or tracking and pendLast~=nil
    local f=XP.eventFrame
    if f then
        local wanted={}
        if tracking then wanted.PLAYER_REGEN_DISABLED=true;wanted.PLAYER_REGEN_ENABLED=true end
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
    if not tracking then clearPending();combatPaused=nil end
    scheduleIdleCheck()
    local due
    for _,id in pairs(c.active) do local run=c.runs[id];if run and run.completionDue and readablePlan(run) then due=min(due or run.completionDue,run.completionDue) end end
    if due and not paused and not completionTimer and C_Timer and C_Timer.After then
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
    XP.ExpireIdle()
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
    if ns.ProfessionTracking and not ns.ProfessionTracking.IsEnabled() then return end
    observationGeneration=observationGeneration+1;completionTimer=false
    combatPaused=nil
    local c=db();c.observerSession=(c.observerSession or 0)+1;XP.eventSession=tostring(c.observerSession)
    for _,id in pairs(c.active) do local run=c.runs[id]
        if run and run.supplement and run.supplement.inFlight then run.supplement.inFlight=false;run.supplement.status="stale";run.supplement.stale=true;run.supplement.feasible=false end
    end
    if type(CreateFrame)~="function" then return end
    local f=XP.eventFrame or CreateFrame("Frame");XP.eventFrame=f;XP.capabilities=XP.capabilities or {}
    f:SetScript("OnEvent",function(_,event,...)
        if event=="PLAYER_REGEN_DISABLED" then
            combatPaused=true;XP.RefreshObservation();return
        elseif event=="PLAYER_REGEN_ENABLED" then
            combatPaused=nil;XP.ReconcileLifecycle()
            local slugs={};for slug in pairs(db().active) do slugs[#slugs+1]=slug end
            for _,slug in ipairs(slugs) do local run=XP.GetRun(slug);if run then changed(run) end end
            return
        end
        XP.ExpireIdle()
        if XP.IsCombatPaused() and event~="TRADE_SKILL_ITEM_CRAFTED_RESULT" and event~="CHAT_MSG_LOOT" then return end
        if event=="UNIT_SPELLCAST_SUCCEEDED" then
            local unit,guid,spell=...;if unit~="player" then return end
            local c=db();local selected=c.trackingSlug
            if not (selected and XP.RecordAttempt(selected,spell,guid)) then
                local slugs={};for slug in pairs(c.active) do if slug~=selected then slugs[#slugs+1]=slug end end
                table.sort(slugs)
                for _,slug in ipairs(slugs) do if XP.RecordAttempt(slug,spell,guid) then break end end
            end
        elseif event=="TRADE_SKILL_ITEM_CRAFTED_RESULT" then XP.RecordCraftedResult(...)
        elseif event=="CHAT_MSG_LOOT" then local args={...};XP.RecordCreatedMessage(args[1],args[11])
        elseif event=="SPELLS_CHANGED" or event=="LEARNED_SPELL_IN_TAB" or event=="QUEST_TURNED_IN" then
            local slugs={};for slug in pairs(db().active) do slugs[#slugs+1]=slug end
            for _,slug in ipairs(slugs) do XP.Sync(slug) end
        elseif event=="SKILL_LINES_CHANGED" or event=="CHAT_MSG_SKILL" or event=="BAG_UPDATE_DELAYED" then
            local slugs={};for slug in pairs(db().active) do slugs[#slugs+1]=slug end
            for _,slug in ipairs(slugs) do
                local run=XP.GetRun(slug);if run then XP.Sync(slug);if run.status=="active" then changed(run) end end
            end
        end
    end)
    XP.ReconcileLifecycle()
end

function XP.DisableTracking()
    observationGeneration=observationGeneration+1
    completionTimer=false;combatPaused=nil
    if idleTimer then idleTimer.handle:Cancel();idleTimer=nil end
    for _,job in pairs(jobs) do
        if ns.ProfIdle and ns.ProfIdle.Cancel then ns.ProfIdle.Cancel(job) end
        job.cancelled=true
        if job.state then job.state.inFlight=false;job.state.status="cancelled" end
    end
    jobs={};clearPending()
    seenMem,seenOrder={},{};receiptMem,receiptOrder={},{}
    creditCaches=setmetatable({}, {__mode="k"})
    local frame=XP.eventFrame
    for event in pairs(observedEvents) do
        if frame and frame.UnregisterEvent then frame:UnregisterEvent(event) end
    end
    observedEvents={};observedActive=false;observedReceipts=false
end

local T={};ns.ProfTrack=T
T.Get=XP.Get;T.GetRun=XP.GetRun;T.Active=XP.GetActive;T.History=XP.GetHistory
T.CanRemove=XP.CanRemove;T.Remove=XP.Remove
T.Bind=XP.Bind;T.Restart=XP.StartNew;T.Sync=XP.Sync;T.OnChanged=XP.OnChanged
T.RecordAttempt=XP.RecordAttempt;T.VerifyOutput=XP.VerifyOutput
T.RecordCreatedText=XP.RecordCreatedMessage;T.ContinueInventory=XP.GetContinuation
T.Summary=XP.GetSummary;T.GetPlan=XP.GetPlan
T.PrepareRecalculate=XP.PrepareRecalculate;T.PlanRecalculated=XP.PlanRecalculated
T.GetSupplement=XP.GetSupplement;T.CalculateSupplement=XP.CalculateSupplement
T.ConfirmConversion=XP.ConfirmConversion
function T.Archive(slug,reason) return XP.End(slug,reason or "archived") end
function T.Drop(slug) return XP.End(slug,"dropped") end
function T.RecordOutput(slug,item,quantity,guid)
    return XP.RecordOutput({slug=slug,itemID=item,quantity=quantity or 1,castGUID=guid},"structured")
end
local function trackProgress(slug,run,i,p)
    if not p then return end
    local seg=segment(run,i);local rec=seg and recipe(seg,slug) or {}
    p.index=i;p.from=seg and seg[1];p.to=seg and seg[2];p.spell=seg and seg[3]
    p.item=p.outputItem;p.mats=rec.mats or {};p.planned=seg and (seg[4] or 0) or 0
    p.outputs=p.actualOutputs or 0;p.remaining=p.remainingCrafts or 0;p.current=p.currentSkill
    p.started=(p.casts or 0)>0;p.over=p.extraCrafts and p.extraCrafts>0 or nil
    p.finished=not p.historyUnreadable and seg==nil or nil
    return p
end
function T.Progress(slug,index,run)
    run=run or XP.GetRun(slug);if not run then return end
    local i=index or run.currentIndex or 1
    return trackProgress(slug,run,i,XP.Progress(slug,i,nil,run.planID))
end
function T.ProgressAll(slug)
    local out=XP.GetProgressAll(slug);if not out then return end
    for i=1,#out.steps do out.steps[i]=trackProgress(slug,out.run,i,out.steps[i]) end
    return out
end
function T.RecipeTotals(slug)
    local out={}
    for _,entry in ipairs(XP.GetRecipeTotals(slug)) do
        if (entry.casts or 0)>0 then
            local quantity=0
            for item,n in pairs(entry.confirmedOutputs) do entry.item=entry.item or item;quantity=quantity+n end
            entry.out=quantity;out[#out+1]=entry
        end
    end
    return out
end
if ns.Init then ns.Init(XP.Initialize) else XP.Initialize() end
