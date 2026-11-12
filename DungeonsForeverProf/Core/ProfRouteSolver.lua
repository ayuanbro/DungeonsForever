local ns = _G.DF_NS or {}
if not ns.LoadForeverPages then return end
local E=ns.ProfEconomy
local R=ns.ProfRisk
local S={}; ns.ProfRouteSolver=S
S.ProcurementPolicyVersion=10
S.FailureDiagnosticVersion=1
local floor,ceil,min,max=math.floor,math.ceil,math.min,math.max
local stockFields={"unlimited","limited","stock","maxStock","stockUnknown","stockStatus"}
local function stampStock(entry,offer)
    if type(offer)=="table" then
        for _,key in ipairs(stockFields) do entry[key]=offer[key] end
    end
    return entry
end
local function clock() return debugprofilestop and debugprofilestop() or (os and os.clock and os.clock()*1000) or 0 end
local function available(s,id) return (s.inv[id] or 0)-(s.unusable[id] or 0) end
local function copyStateMap(source)
    local out={}
    for key,value in pairs(source or {}) do out[key]=value end
    return out
end
local function clone(s)
    return {inv=copyStateMap(s.inv),unusable=copyStateMap(s.unusable),unusableSeed=s.unusableSeed,
        produced=copyStateMap(s.produced),priorityProduced=copyStateMap(s.priorityProduced),profitMade=copyStateMap(s.profitMade),skill=copyStateMap(s.skill),progress=copyStateMap(s.progress),
        cap=copyStateMap(s.cap),learned=s.learned,formulaPaid=copyStateMap(s.formulaPaid),
        ahUsed=copyStateMap(s.ahUsed),specializationAbilities=copyStateMap(s.specializationAbilities),
        completedSpecializationGoals=copyStateMap(s.completedSpecializationGoals),
        completedToolGoals=copyStateMap(s.completedToolGoals),diagnostics=copyStateMap(s.diagnostics),
        risk=s.risk,plannedTarget=s.plannedTarget,greenLevelCrafts=s.greenLevelCrafts,rebatchGreenCrafts=s.rebatchGreenCrafts,money=s.money,log=s.log,switches=s.switches or 0,lastRecipe=s.lastRecipe,
        skeletonBought=s.skeletonBought and copyStateMap(s.skeletonBought)}
end
local function consume(s,id,n)
    local stock=s.inv[id] or 0
    assert(available(s,id)>=n,"reserved reagent became unavailable")
    local made=s.produced[id] or 0
    local purchased=max(0,stock-made-(s.unusableSeed and s.unusableSeed[id] or 0))
    s.produced[id]=max(0,made-max(0,n-purchased))
    s.priorityProduced[id]=max(0,(s.priorityProduced[id] or 0)-max(0,n-purchased))
    s.inv[id]=stock-n
end
local function log(s,a)
    if s.risk then s.risk=R.Apply(s.risk,a) end
    s.log={prev=s.log,action=a}
end
local function diagnostic(s,key,code,extra)
    if not s.diagnostics[key] then s.diagnostics[key]={code=code,detail=extra,item=type(extra)=="number" and extra or nil} end
end
local function uncertainty(s) local n=0; for _ in pairs(s.diagnostics) do n=n+1 end; return n end
local function objective(s,snapshot)
    local recovery=ns.ProfRecovery
    if snapshot and recovery and recovery.PriorityRevenue then return s.money-recovery.PriorityRevenue(s,snapshot) end
    return s.money
end
local function betterState(a,b,snapshot)
    if not b then return true end
    local ua,ub=uncertainty(a),uncertainty(b)
    if (ua==0)~=(ub==0) then return ua==0 end
    local ca,cb=objective(a,snapshot),objective(b,snapshot)
    if math.abs(ca-cb)>1e-7 then return ca<cb end
    if math.abs(a.money-b.money)>1e-7 then return a.money<b.money end
    if (a.switches or 0)~=(b.switches or 0) then return (a.switches or 0)<(b.switches or 0) end
    return uncertainty(a)<uncertainty(b)
end
local function initial(snap,slug,opts,tick)
    local s={inv={},unusable={},unusableSeed={},produced={},priorityProduced={},profitMade={},skill={},progress={},cap={},learned=E.Copy(snap.known,tick),formulaPaid={},ahUsed={},specializationAbilities=E.Copy(snap.specializationAbilities,tick),completedSpecializationGoals={},completedToolGoals={},diagnostics={},greenLevelCrafts=0,money=0,switches=0}
    for p,v in pairs(snap.professions) do s.skill[p]=v.cur or 1; s.cap[p]=v.max or 300 end
    s.skill[slug]=opts.start or s.skill[slug] or 1; s.cap[slug]=s.cap[slug] or 300
    if opts.scheme=="stable" then s.risk=R.New(snap,slug,opts,tick) end
    local inventory=opts.procurementDemands and opts.executionInventory or {}
    local ids={}; for id in pairs(inventory) do if type(id)=="number" then ids[#ids+1]=id end end
    table.sort(ids)
    for _,id in ipairs(ids) do
        local entry=inventory[id]
        local n=type(entry)=="table" and entry.count or entry
        if type(n)=="number" and n>0 and n==floor(n) then
            s.inv[id]=n
            if type(entry)=="table" and entry.usable==false then s.unusable[id]=n;s.unusableSeed[id]=n end
            log(s,{type="seed",item=id,count=n,usableOutput=not (type(entry)=="table" and entry.usable==false)})
        end
    end
    return s
end
local function actions(s,tick)
    local out={}; local node=s.log
    while node do out[#out+1]=node.action; node=node.prev;if tick and #out%64==0 then tick() end end
    local rev={}; for i=#out,1,-1 do rev[#rev+1]=out[i];if tick and i%64==0 then tick() end end
    return rev
end
local function stateKey(t,reusable,recovery,terminal)
    local parts={}
    for p,n in pairs(t.skill) do parts[#parts+1]="s"..p.."="..n..":"..(t.progress[p] or 0)..":"..(t.cap[p] or 300) end
    for id,n in pairs(t.inv) do if n>0 and not (terminal and terminal[id]) and (recovery or not reusable or reusable[id]) then
        parts[#parts+1]="i"..id.."="..n..":"..(t.unusable[id] or 0)..(recovery and (":"..(t.produced[id] or 0)..":"..(t.unusableSeed[id] or 0)..":"..(t.priorityProduced[id] or 0)) or "")
    end end
    if recovery then for key,n in pairs(t.profitMade) do parts[#parts+1]="profit:"..key.."="..n end end
    if t.risk then parts[#parts+1]="risk="..R.Key(t.risk) end
    for key in pairs(t.formulaPaid) do parts[#parts+1]="f"..tostring(key) end
    for id,n in pairs(t.ahUsed) do parts[#parts+1]="a"..id.."="..n end
    for id,value in pairs(t.specializationAbilities or {}) do parts[#parts+1]="spec"..id.."="..tostring(value) end
    for id in pairs(t.completedSpecializationGoals or {}) do parts[#parts+1]="quest"..id end
    for id in pairs(t.completedToolGoals or {}) do parts[#parts+1]="tool"..id end
    parts[#parts+1]="last="..tostring(t.lastRecipe or "")
    for k in pairs(t.diagnostics) do parts[#parts+1]="d"..k end
    table.sort(parts); return table.concat(parts,";")
end
local function goalsComplete(job,state)
    if not state or max(state.skill[job.slug] or 0,state.plannedTarget or 0)<job.target then return false end
    for _,goal in ipairs(job.snap and job.snap.specializationGoals or {}) do
        if not state.completedSpecializationGoals[goal.id] and not state.specializationAbilities[goal.abilityID] then return false end
    end
    for _,goal in ipairs(job.snap and job.snap.toolGoals or {}) do
        if not state.completedToolGoals[goal.id] then return false end
    end
    return not (job.slug=="engineering" and job.target>=200 and job.snap and job.snap.specializationContext and job.snap.specializationContext.selectionConflict)
end
local function completedGoals(state)
    local count=0
    for _ in pairs(state and state.completedSpecializationGoals or {}) do count=count+1 end
    for _ in pairs(state and state.completedToolGoals or {}) do count=count+1 end
    return count
end
local function stampFreshResult(result,snapshot,tick)
    local recovery=ns.ProfRecovery
    if recovery and recovery.Apply and snapshot then recovery.Apply(result,snapshot,tick) end
    local route=ns.ProfRouteAuto
    if route and route.StampVendorQuotes then route.StampVendorQuotes(result) end
    if route and route.StampToolPolicy then route.StampToolPolicy(result,snapshot and snapshot.targetProfession,nil,snapshot) end
    return result
end
local function stampLearningGaps(job,result)
    result.failureDiagnosticVersion=S.FailureDiagnosticVersion
    if result._learningGapRevision~=(job.learningGapRevision or 0) then
        result.learningGaps={}
        for _,gap in pairs(job.learningGaps or {}) do
            result.learningGaps[#result.learningGaps+1]=gap
            if job.tick and coroutine.running()==job.co then job.tick() end
        end
        table.sort(result.learningGaps,function(a,b)
            if a.profession~=b.profession then return tostring(a.profession)<tostring(b.profession) end
            return (a.spell or 0)<(b.spell or 0)
        end)
        result._learningGapRevision=job.learningGapRevision or 0
    end
    result.learningCoverageComplete=#(result.learningGaps or {})==0
    result.blockingLearningGaps={}
    if not result.targetReached then
        local blockers=job.blockedSkill==(result.plannedTo or result.start) and job.blockers or result.blockingDiagnostics
        local seen={}
        for _,d in ipairs(blockers or {}) do
            if d.code=="learningDataMissing" or d.code=="learningRequirementsUnknown"
                or type(d.missingReasons)=="table" and #d.missingReasons>0 then
                local key=tostring(d.code)..":"..tostring(d.recipe or d.spell)
                if not seen[key] then result.blockingLearningGaps[#result.blockingLearningGaps+1]=d;seen[key]=true end
            end
        end
    end
    result.learningBlocked=#result.blockingLearningGaps>0
    if result._learningPathComplete==nil then result._learningPathComplete=result.learningComplete~=false end
    result.learningComplete=result._learningPathComplete and not result.learningBlocked
    if result.learningBlocked then result.completeCost=false;result.optimal=false
    elseif result.costComplete~=nil then result.completeCost=result.costComplete end
end
function S.Progress(job,result)
    result=result or job.result
    local quoteComplete=result and result.costComplete and not result.essenceQuoteIncomplete and true or false
    if job.recovery and result and ((result.recoveryQuoteMissing or 0)>0 or result.recoveryFeeMissing) then quoteComplete=false end
    local inputOptimal=result and result.targetReached and job.exhausted and not job.restricted
        and not result.alreadyAtTarget and result.learningComplete~=false and result.formulaComplete~=false
        and result.specializationComplete~=false
        and result.supplyComplete~=false
        and not job.budgetLimited and job.status~="error" and job.status~="stopped" and quoteComplete or false
    local coverage=job.snap and job.snap.coverageComplete~=false or false
    return {status=job.status,expanded=job.expanded or 0,improvements=job.improvements or 0,
        searchCpuMs=job.cpuUsed or 0,searchCpuLimitMs=job.cpuLimitMs or 8000,
        searchComplete=job.exhausted or false,budgetLimited=job.budgetLimited or false,
        costSearchPerformed=(job.expanded or 0)>0,
        costSearchStatus=(job.expanded or 0)==0 and (job.seedDone and "seed_only" or "pending")
            or (job.exhausted and not job.budgetLimited and "exhausted" or "searched_unproven"),
        searchTermination=job.searchTermination,resultVersion=job.resultVersion or 0,
        progressVersion=job.progressVersion or 0,inputModelOptimal=inputOptimal,
        catalogueCoverageComplete=coverage,quoteComplete=quoteComplete,
        optimal=inputOptimal and coverage or false,restrictedReason=job.restrictedReason,
        frontierStates=job.frontierStates or 0,memoStates=job.memoStates or 0,
        searchFrontierLimit=job.frontierLimit,finalizing=job.finalizing and true or false,finalizeProgress=job.finalizeProgress or 0,
        searchExternalCpuMs=job.externalCpuUsed or 0,searchModel="fractional_skill_accumulation"}
end
function S.RefreshStatus(job,result,status)
    result=result or job.result
    if not result then return end
    for key,value in pairs(S.Progress(job,result)) do result[key]=value end
    result.status=status or job.status
    result.searchTermination=job.searchTermination
    result.restrictedReason=job.restricted and (job.restrictedReason or "restricted_search") or nil
    if result.partial then
        local blockers=job.blockedSkill==result.plannedTo and job.blockers or nil
        if job.resultBlockers~=blockers then
            result.blockingDiagnostics=E.Copy(blockers or {});job.resultBlockers=blockers
            E.SummarizeAuctionSupply(result,job.snap)
        end
    end
    stampLearningGaps(job,result)
    result.initialTotal=job.initialTotal
    result.savings=result.feasible and job.initialTotal and max(0,job.initialTotal-result.total) or 0
    if job.recovery then
        result.initialNetTotal=job.initialNetTotal
        result.bestNetTotal=result.feasible and result.netTotal or nil
        result.netSavings=result.bestNetTotal and job.initialNetTotal and max(0,job.initialNetTotal-result.bestNetTotal) or 0
    end
    return result
end
local function restrict(job,reason)
    job.restricted=true
    job.restrictedReason=job.restrictedReason or reason
end
local function resultTick(job)
    if job.tick and coroutine.running()==job.co then job.tick() end
end
local function finalizeProgress(job,value)
    if job.finalizing and coroutine.running()==job.co then job.finalizeProgress=max(job.finalizeProgress or 0,min(.99,value)) end
end
local function stampReserve(job,result,status)
    status=status or job.status
    if result.feasible and not result.reserve and ns.ProfReserve and not job.opts.procurementDemands
        and (status=="complete" or status=="incomplete") then
        result.slug=job.slug
        result.reserve=ns.ProfReserve.Build(result,job.snap,job.opts,
            coroutine.running()==job.co and job.tick or nil)
    end
end
local function finishResult(job,result,state,status)
    finalizeProgress(job,.96)
    stampReserve(job,result,status)
    finalizeProgress(job,.97)
    local tick=coroutine.running()==job.co and job.tick or nil
    if job.snap and job.snap.auctionPriceInputs then
        result.auctionPriceInputs=E.Copy(job.snap.auctionPriceInputs,tick)
    end
    stampFreshResult(result,job.snap,tick)
    E.SummarizeAuctionSupply(result,job.snap,tick)
    finalizeProgress(job,.98)
    local essence=ns.ProfEssences
    if job.snap and job.snap.essenceConversions and essence and essence.MissingQuotes then
        local bought={}
        for _,action in ipairs(result.actions or {}) do
            if action.type=="buy" and (action.count or 0)>0 then bought[action.item]=true end
        end
        result.essenceQuoteMissing=essence.MissingQuotes(job.snap,bought)
        result.essenceQuoteIncomplete=#result.essenceQuoteMissing>0 or nil
    end
    job.resultVersion=(job.resultVersion or 0)+1
    job.resultState=state;job.resultCache=result
    finalizeProgress(job,.99)
    return S.RefreshStatus(job,result,status)
end
function S.Result(job,state,status)
    local prefix=job.preview or (job.partial and job.partial.batched and job.partial)
    local partial=not state and prefix and (prefix.skill[job.slug]>(job.opts.start or 1) or completedGoals(prefix)>0)
    if partial then state=prefix; partial=not goalsComplete(job,state) end
    local finalStatus = status or job.status
    if finalStatus~="searching" and coroutine.running()==job.co then
        job.finalizing=true;job.finalizeProgress=job.finalizeProgress or 0
    end
    if state and (state == job.best or state == prefix) and not job.rebatchFinalized
        and (finalStatus == "complete" or finalStatus == "incomplete")
        and job.rebatchFinal and coroutine.running()==job.co then
        job.rebatchFinalized = true
        local previousPhase,finalizing=job.phase,job.finalizing
        job.phase="rebatch";job.finalizing=true
        local candidate = job.rebatchFinal(state)
        job.phase=previousPhase;job.finalizing=finalizing
        if candidate and candidate ~= state then
            local complete=goalsComplete(job,candidate)
            if state==job.best or complete then job.best=candidate end
            if state==prefix then job.preview=candidate end
            if complete and finalStatus=="incomplete" then
                status=uncertainty(candidate)==0 and "complete" or "incomplete";job.status=status;finalStatus=status
            end
            state = candidate
            if partial then partial=not goalsComplete(job,state) end
            job.resultState = nil
            job.resultCache = nil
        end
    end
    finalizeProgress(job,.8)
    if state and job.resultState==state and job.resultCache then
        stampReserve(job,job.resultCache,status)
        finalizeProgress(job,.99)
        return S.RefreshStatus(job,job.resultCache,status)
    end
    local out={planVersion=2,executionVersion=1,scheme="cheapest",steps={},executionSteps={},actions={},mats={},firstAt={},gaps={},total=0,matTotal=0,vendorTotal=0,ahTotal=0,crafts=0,productAH=0,productNPC=0,productPartial=false,start=job.opts.start or 1,target=job.target,status=status or "searching",feasible=state~=nil,priced=true,optimal=false,diagnostics={},stamp=(time and time()) or 0,expanded=job.expanded or 0,improvements=job.improvements or 0,initialTotal=job.initialTotal,searchComplete=job.exhausted or false,budgetLimited=job.budgetLimited or false}
    out.searchTermination=job.searchTermination
    out.procurementPolicyVersion=S.ProcurementPolicyVersion
    out.searchCpuMs=job.cpuUsed or 0
    out.searchCpuLimitMs=job.cpuLimitMs or 8000
    out.phaseCpuMs=E.Copy(job.phaseCpuMs or {})
    out.solverWork=E.Copy(job.workCounters or {})
    out.firstFeasibleCpuMs=job.firstFeasibleCpuMs
    out.seedInventory=E.Copy(job.opts.procurementDemands and job.opts.executionInventory or {})
    out.scheme=job.opts.scheme or "cheapest"
    out.greenLevelCrafts=state and state.greenLevelCrafts or 0
    out.stability=state and state.risk and E.Copy(R.Score(state.risk)) or nil
    out.toolGoals=E.Copy(job.snap and job.snap.toolGoals)
    out.toolGoalsPending=E.Copy(job.snap and job.snap.toolGoalsPending)
    out.retainedToolItems=E.Copy(job.snap and job.snap.retainedToolItems)
    out.toolFingerprint=job.snap and job.snap.toolFingerprint
    out.specializationGoals=E.Copy(job.snap and job.snap.specializationGoals)
    out.specializationContext=E.Copy(job.snap and job.snap.specializationContext)
    local specializationWarnings=out.specializationContext and out.specializationContext.warnings or {}
    out.specializationComplete=#specializationWarnings==0
    for _,warning in ipairs(specializationWarnings) do out.diagnostics[#out.diagnostics+1]=E.Copy(warning) end
    out.formulas={};out.formulasTotal=0;out.formulaAHTotal=0;out.formulaVendorTotal=0;out.formulaRevision=1;out.formulaComplete=true
    local context=job.snap and job.snap.routeContext
    out.professionPolicy=1
    if context then
        out.targetUnlearned=context.unlearned
        out.secondaryProfession=context.requiresPartner and context.partner or nil
    else
        out.targetUnlearned=job.opts.targetUnlearned
        out.secondaryProfession=job.opts.secondaryProfession
    end
    out.savings=state and job.initialTotal and max(0,job.initialTotal-state.money) or 0
    out.recoveryOptimized=job.recovery and true or false
    if job.recovery then
        out.initialNetTotal=job.initialNetTotal
        out.bestNetTotal=state and (state.money-ns.ProfRecovery.StateRevenue(state,job.snap)) or nil
        out.priorityTotal=state and objective(state,job.snap) or nil
        out.netSavings=out.bestNetTotal and job.initialNetTotal and max(0,job.initialNetTotal-out.bestNetTotal) or 0
    end
    out.partial=partial and true or false
    out.targetReached=goalsComplete(job,state)
    out.plannedTo=state and max(state.skill[job.slug] or 0,state.plannedTarget or 0) or out.start
    if not state then
        out.priced=false; out.costComplete=false; out.completeCost=false
        for _,d in pairs(job.failures or {}) do out.diagnostics[#out.diagnostics+1]=d end
        if job.blockedSkill==out.plannedTo then out.blockingDiagnostics=E.Copy(job.blockers or {}) end
        if job.opts.procurementDemands then out.procurement=true;out.demands=E.Copy(job.opts.procurementDemands);out.start=nil;out.target=nil;out.plannedTo=nil end
        return finishResult(job,out,state,status)
    end
    local purchases,purchaseLookup,vendorPurchases={},{},{}
    local crafted={}; local pendingCost=0; local pendingUnpriced=false
    local formulaEntries,formulaRecipes,formulaByOwner={},{},{}
    out.total=state.money; out.inventory=E.Copy(state.inv); out.finalSkills=E.Copy(state.skill)
    out.completedSpecializationGoals=E.Copy(state.completedSpecializationGoals)
    out.completedToolGoals=E.Copy(state.completedToolGoals)
    out.specializationAbilities=E.Copy(state.specializationAbilities)
    for _,d in pairs(state.diagnostics) do out.diagnostics[#out.diagnostics+1]=E.Copy(d) end
    local checkedLearning={}
    for _,d in ipairs(out.diagnostics) do
        if d.code=="learningRequirementsUnknown" then checkedLearning[d.detail]=true end
    end
    local entry=state.log
    while entry do
        resultTick(job)
        local action=entry.action
        if action.type=="craft" then
            local key=action.profession..":"..action.spell
            if not checkedLearning[key] then
                local recipe=job.snap.byKey and job.snap.byKey[key]
                local detail
                if recipe then local _,_,value=(E.RouteRecipeEligibility or E.RecipeSpecializationAllowed)(recipe,job.snap,state);detail=value end
                if detail and detail.status=="unknown" then
                    out.diagnostics[#out.diagnostics+1]={code="learningRequirementsUnknown",detail=key,spell=action.spell}
                end
                checkedLearning[key]=true
            end
        end
        entry=entry.prev
    end
    for _,d in ipairs(out.toolGoalsPending or {}) do out.diagnostics[#out.diagnostics+1]=E.Copy(d) end
    out.costComplete=true
    out.learningComplete=true
    for _,d in ipairs(out.diagnostics) do
        if d.code=="learningRequirementsUnknown" then out.learningComplete=false
        elseif d.code=="materialPriceUnknown" or d.code=="vendorPriceUnknown"
            or d.code=="vendorEstimate" or d.code=="formulaPriceUnknown" or d.code=="learningPriceUnknown" then out.costComplete=false end
    end
    out.completeCost=out.costComplete
    out.priced=out.costComplete
    out.actions=actions(state,coroutine.running()==job.co and job.tick or nil); out.dependencyGraph={}
    if partial then
        out.blockingDiagnostics=E.Copy(job.blockedSkill==out.plannedTo and job.blockers or {})
        out.remainingUnknown=true
    end
    local toolOrigins={}
    local provenance,provenanceHeads={},{}; local usedOutputs={}; local allocations={}; local cashByRecipe={}; local countByRecipe={}; local unpricedByRecipe={}
    for i,a in ipairs(out.actions) do
        finalizeProgress(job,.82+.02*(i-1)/max(1,#out.actions))
        resultTick(job)
        if (a.type=="buy" or a.type=="formula") and a.owner then
            cashByRecipe[a.owner]=(cashByRecipe[a.owner] or 0)+a.cost
            unpricedByRecipe[a.owner]=unpricedByRecipe[a.owner] or a.unpriced
        elseif a.type=="craft" then local key=a.profession..":"..a.spell; countByRecipe[key]=(countByRecipe[key] or 0)+a.count end
    end
    local function addOrigin(id,n,actionID,craftedOrigin)
        local pool=provenance[id] or {}; provenance[id]=pool
        pool[#pool+1]={count=n,id=actionID,crafted=craftedOrigin and true or false}
    end
    for i,a in ipairs(out.actions) do
        finalizeProgress(job,.84+.08*(i-1)/max(1,#out.actions))
        resultTick(job)
        a.id=tostring(i)..":"..tostring(a.profession or "")..":"..tostring(a.spell or a.item or 0)
        local dependencies={}; local dependencySet={}
        for _,input in ipairs(a.inputs or {}) do
            local need=input[2]
            local pool=provenance[input[1]] or {}
            local heads=provenanceHeads[input[1]] or {1,1};provenanceHeads[input[1]]=heads
            for pass=1,2 do
                local index=heads[pass]
                while need>0 and index<=#pool do
                    local origin=pool[index]
                    resultTick(job)
                    if origin.crafted==(pass==2) then
                        local n=min(need,origin.count); origin.count=origin.count-n; need=need-n
                        if n>0 and origin.id then
                            usedOutputs[origin.id]=true
                            local list=allocations[origin.id] or {}; allocations[origin.id]=list
                            list[#list+1]={consumerID=a.id,itemID=input[1],count=n}
                            if not dependencySet[origin.id] then dependencySet[origin.id]=true; dependencies[#dependencies+1]=origin.id end
                        end
                    end
                    if origin.crafted~=(pass==2) or origin.count<=0 then index=index+1 else break end
                end
                heads[pass]=index
                if need<=0 then break end
            end
        end
        a.dependencies=dependencies; out.dependencyGraph[a.id]=dependencies
        if a.type=="seed" then
            if a.usableOutput~=false then addOrigin(a.item,a.count,a.id) end
        elseif a.type=="formula" then
            local entry=E.Copy(a.formula);entry.recipes={};out.formulas[#out.formulas+1]=entry
            formulaEntries[entry.id or entry.recipeKey]=entry
            if a.owner then formulaByOwner[a.owner]=entry end
            out.formulaComplete=out.formulaComplete and entry.costComplete
            out.formulasTotal=out.formulasTotal+a.cost
            if a.source=="vendor" or a.source=="trainer" or a.source=="acquire" and entry.acquisitionKind=="currency" then
                out.vendorTotal=out.vendorTotal+a.cost;out.formulaVendorTotal=out.formulaVendorTotal+a.cost
            elseif a.source=="ah" then out.ahTotal=out.ahTotal+a.cost;out.formulaAHTotal=out.formulaAHTotal+a.cost end
            out.referencePrices=out.referencePrices or entry.offer and entry.offer.reference
        elseif a.type=="buy" then
            addOrigin(a.item,a.count,a.id)
            if not a.owner then pendingCost=pendingCost+a.cost;pendingUnpriced=pendingUnpriced or a.unpriced end
            local key=tostring(a.item)..":"..a.source..":"..tostring(a.npcID or 0)
            local map=purchaseLookup
            local bundlePrice=a.bundlePrice
            if a.source=="vendor" then
                local bundle=a.bundleSize or 1
                bundlePrice=bundlePrice or a.cost/(a.count/bundle)
                local identity={a.item,a.npcID or 0,bundle,bundlePrice,
                    a.priceSource or false,a.quoteSource or false,a.priceBasis or false}
                map=vendorPurchases
                for i=1,#identity-1 do
                    local part=identity[i];map[part]=map[part] or {};map=map[part]
                end
                key=identity[#identity]
            end
            local e=map[key]
            if not e then e=stampStock({a.item,0,id=a.item,count=0,need=0,cost=0,unit=0,vendor=a.source=="vendor",source=a.source,npcID=a.npcID,url=a.url,spell=a.spell,reason=a.reason,bundleSize=a.bundleSize,bundlePrice=bundlePrice,quoteSource=a.quoteSource,priceSource=a.priceSource,priceBasis=a.priceBasis,verifiedAt=a.verifiedAt},a); map[key]=e;purchases[#purchases+1]=e end

            e[2]=e[2]+a.count; e.count=e[2]; e.need=e.count; e.cost=e.cost+a.cost; e.unit=e.cost/e.count
            e.netDemand=true
            e.unpriced=e.unpriced or a.unpriced or nil

            out.pricePending=out.pricePending or a.unpriced or nil
            e.reference=e.reference or a.reference or nil; e.estimated=e.estimated or a.estimated or nil
            out.referencePrices=out.referencePrices or a.reference or nil
            out.matTotal=out.matTotal+a.cost
            if a.source=="vendor" then out.vendorTotal=out.vendorTotal+a.cost else out.ahTotal=out.ahTotal+a.cost end
        elseif a.type=="convert" then
            local c=a.conversion
            for _,output in ipairs(a.outputs or {}) do addOrigin(output[1],output[2],a.id) end
            out.executionSteps[#out.executionSteps+1]={a.from,a.to,0,a.count,kind="essence_conversion",
                profession=a.profession,reason="essence",manual=true,essence=true,conversion=E.Copy(c),
                actionID=a.id,actionIDs={a.id},item=a.item,cost=0,expectedGain=0,
                sourceItem=c.inputItemID,sourceCount=c.inputCount*a.count,sourcePerConversion=c.inputCount,
                targetItem=c.outputItemID,targetCount=c.outputCount*a.count,targetPerConversion=c.outputCount,
                inputs=E.Copy(a.inputs),outputs=E.Copy(a.outputs),attemptLimit=a.count,
                recipe={profession=a.profession,spell=0,item=c.outputItemID,count=c.outputCount,
                    mats={{c.inputItemID,c.inputCount}}}}
            if not out.firstAt[c.inputItemID] then out.firstAt[c.inputItemID]=a.from end
        elseif a.type=="tool_goal" then
            pendingCost=pendingCost+(cashByRecipe["tool:"..a.goalID] or 0)
            for _,origin in ipairs(provenance[a.item] or {}) do
                if origin.count>0 and origin.crafted then toolOrigins[origin.id]=a.item;break end
            end
        elseif a.type=="specialization_quest" then
            local goal=E.Copy(a.quest)
            local key="quest:"..goal.id
            out.executionSteps[#out.executionSteps+1]={a.from,a.to,0,0,kind="specialization_quest",
                profession=a.profession,quest=goal,goalID=goal.id,questID=goal.questID,abilityID=goal.abilityID,
                inputs=E.Copy(a.inputs),requiredItems=E.Copy(a.inputs),reason="specialization",
                actionID=a.id,actionIDs={a.id},cost=pendingCost+(cashByRecipe[key] or 0),
                unpriced=pendingUnpriced or unpricedByRecipe[key] or nil,expectedGain=0,
                recipe={profession=a.profession,spell=0,mats=E.Copy(a.inputs)}}
            pendingCost=0;pendingUnpriced=false
            for _,m in ipairs(a.inputs or {}) do if not out.firstAt[m[1]] then out.firstAt[m[1]]=a.from end end
        elseif a.type=="craft" or a.type=="gather" then
            local recipeKey=tostring(a.profession)..":"..tostring(a.spell)
            local f=job.formulaByRecipe and job.formulaByRecipe[recipeKey]
            local entry=formulaByOwner[recipeKey] or f and formulaEntries[f.id or recipeKey]
            if entry and not formulaRecipes[recipeKey] then
                entry.recipes[#entry.recipes+1]={profession=a.profession,spell=a.spell,key=recipeKey,source=f.sources}
                formulaRecipes[recipeKey]=true
            end
            if a.usableOutput~=false then for _,output in ipairs(a.outputs or {}) do addOrigin(output[1],output[2],a.id,true) end end
            local key=tostring(a.profession)..":"..tostring(a.spell)
            local stepCost=pendingCost+(cashByRecipe[key] or 0)*(a.count or 0)/max(1,countByRecipe[key] or 1)
            local stepUnpriced=pendingUnpriced or unpricedByRecipe[key] or nil
            local last=out.executionSteps[#out.executionSteps]
            if a.type=="craft" and last and not last.kind and not last.checkpoint and last[3]==a.spell and last.profession==a.profession then
                last[2]=a.to; last[4]=last[4]+a.count
                last.cost=last.cost+stepCost
                last.unpriced=last.unpriced or stepUnpriced
                last.actionIDs[#last.actionIDs+1]=a.id
                last.expectedGain=(last.expectedGain or 0)+(a.expectedGain or 0)
                last.toProgress=a.toProgress
            else
                local recipe=job.snap.byKey and job.snap.byKey[tostring(a.profession)..":"..tostring(a.spell)]
                out.executionSteps[#out.executionSteps+1]={a.from,a.to,a.spell or 0,a.count or 0,profession=a.profession,reason=a.reason,checkpoint=a.type=="gather",actionID=a.id,actionIDs={a.id},item=a.item,cost=stepCost,unpriced=stepUnpriced,recipe=recipe and E.Copy(recipe),tool=recipe and recipe.tool or nil,toolItem=recipe and recipe.toolItem or nil,expectedGain=a.expectedGain or (a.to-a.from),fromProgress=a.fromProgress or 0,toProgress=a.toProgress or 0}
            end
            pendingCost=0; pendingUnpriced=false
            if a.type=="gather" then out.gaps[#out.gaps+1]={a.from,a.to,manual=true,profession=a.profession}
            else
                out.crafts=out.crafts+a.count
                if a.item then crafted[a.item]=(crafted[a.item] or 0)+(a.outputCount or 0) end
                for _,m in ipairs(a.inputs or {}) do if not out.firstAt[m[1]] then out.firstAt[m[1]]=a.from end end
            end
        end
    end
    if pendingCost>0 and #out.executionSteps>0 then
        local last=out.executionSteps[#out.executionSteps];last.cost=last.cost+pendingCost
    end
    for _,e in ipairs(purchases) do out.mats[#out.mats+1]=e end
    out.referenceRoute=out.pricePending or nil
    table.sort(out.mats,function(a,b) return a.id<b.id or (a.id==b.id and a.source<b.source) end)
    local occurrences,actionSegments={},{}
    for i,step in ipairs(out.executionSteps) do
        finalizeProgress(job,.92+.01*(i-1)/max(1,#out.executionSteps))
        resultTick(job)
        local key=step.kind=="specialization_quest" and ("quest:"..step.goalID)
            or step.kind=="essence_conversion" and ("convert:"..step.sourceItem..":"..step.targetItem)
            or (step.profession..":"..step[3])
        occurrences[key]=(occurrences[key] or 0)+1
        step.segmentID="segment:"..key..":"..occurrences[key]
        step.expectedCrafts=step[4]
        step.outputMin=step.recipe and (step.recipe.outputMin or step.recipe.count) or 0
        step.outputMax=step.recipe and (step.recipe.outputMax or step.recipe.count) or step.outputMin
        step.requiredOutputs={};step.allocations={}
        if step.checkpoint then step.goalSkill=step[2]
        elseif (step.expectedGain or 0)>0 then
            step.goalSkill=step[2]>step[1] and step[2] or ceil(step[2]+(step.toProgress or 0)-1e-7)
            if step[2]==step[1] then step.attemptLimit=step[4];step.fractionalTransition=true end
        end
        for _,id in ipairs(step.actionIDs) do actionSegments[id]=step.segmentID end
    end
    for i,step in ipairs(out.executionSteps) do
        finalizeProgress(job,.93+.01*(i-1)/max(1,#out.executionSteps))
        resultTick(job)
        for _,id in ipairs(step.actionIDs) do for _,allocation in ipairs(allocations[id] or {}) do
            step.requiredOutputs[allocation.itemID]=(step.requiredOutputs[allocation.itemID] or 0)+allocation.count
            step.allocations[#step.allocations+1]={consumerID=actionSegments[allocation.consumerID] or allocation.consumerID,itemID=allocation.itemID,count=allocation.count}
        end end
        for _,id in ipairs(step.actionIDs) do
            local item=toolOrigins[id]
            if item then
                step.requiredOutputs[item]=max(1,step.requiredOutputs[item] or 0)
                step.tool=true;step.toolItem=item
                if #step.allocations==0 then step.allocations[#step.allocations+1]={consumerID="tool:"..item,itemID=item,count=1} end
            end
        end
        step.materialMinCrafts=0
        for _,n in pairs(step.requiredOutputs) do step.materialMinCrafts=max(step.materialMinCrafts,ceil(n/max(1,step.outputMin))) end
        step.leveling=(step.expectedGain or 0)>1e-9
        step.material=next(step.requiredOutputs)~=nil
        step.role=step.leveling and (step.material and "both" or "level") or (step.material and "material" or nil)
        if step.kind=="essence_conversion" then step.plannedSurplus=max(0,step.targetCount-(step.requiredOutputs[step.targetItem] or 0)) end
    end
    out.seedAllocations={}
    for _,a in ipairs(out.actions) do if a.type=="seed" then
        for _,allocation in ipairs(allocations[a.id] or {}) do
            out.seedAllocations[#out.seedAllocations+1]={itemID=a.item,count=allocation.count,consumerID=actionSegments[allocation.consumerID] or allocation.consumerID}
        end
    end end
    local grouped={}
    for i,step in ipairs(out.executionSteps) do
        finalizeProgress(job,.94+.02*(i-1)/max(1,#out.executionSteps))
        resultTick(job)
        local key=(step.checkpoint or step.kind=="specialization_quest" or step.kind=="essence_conversion") and step.actionID or (step.profession..":"..step[3])
        local prevRow=out.steps[#out.steps]
        local row=(prevRow and prevRow.__groupKey==key) and prevRow or nil
        if not row then
            row=E.Copy(step);row.requiredOutputs=E.Copy(step.requiredOutputs);row.allocations={}
            for _,allocation in ipairs(step.allocations) do row.allocations[#row.allocations+1]=E.Copy(allocation) end
            row.segments={};row.segmentIDs={};row.__groupKey=key;row.continued=true;out.steps[#out.steps+1]=row;row.stepIndex=#out.steps
        else
            row[2]=step[2];row[4]=row[4]+step[4];row.cost=row.cost+step.cost;row.unpriced=row.unpriced or step.unpriced
            row.expectedGain=(row.expectedGain or 0)+(step.expectedGain or 0)
            row.materialMinCrafts=(row.materialMinCrafts or 0)+(step.materialMinCrafts or 0)
            for id,n in pairs(step.requiredOutputs) do row.requiredOutputs[id]=(row.requiredOutputs[id] or 0)+n end
            for _,allocation in ipairs(step.allocations) do row.allocations[#row.allocations+1]=E.Copy(allocation) end
        end
        row.leveling=row.leveling or step.leveling
        row.material=row.material or step.material
        row.role=row.leveling and (row.material and "both" or "level") or (row.material and "material" or nil)
        step.stepIndex=row.stepIndex
        row.segmentIDs[#row.segmentIDs+1]=step.segmentID
        row.expectedCrafts=row[4]
        row.segments[#row.segments+1]={from=step[1],to=step[2],count=step[4],reason=step.reason}
    end
    local ra=ns.ProfRouteAuto
    for id,n in pairs(crafted) do
        local left=min(n,state.produced[id] or 0)
        local retained=job.snap.retainedToolItems and job.snap.retainedToolItems[id] or 0
        local purchased=max(0,(state.inv[id] or 0)-(state.produced[id] or 0))
        left=max(0,left-max(0,retained-purchased))
        if left>0 then
            local ah=job.snap.prices[id]; local npc=ra and ra.NPCSellPriceOf and ra.NPCSellPriceOf(id)
            if ah then out.productAH=out.productAH+left*ah else out.productPartial=true end
            if npc then out.productNPC=out.productNPC+left*npc end
        end
    end
    if job.opts.procurementDemands then
        out.procurement=true;out.demands=E.Copy(job.opts.procurementDemands)
        out.consumedDemands=E.Copy(job.opts.procurementDemands)
        out.start=nil;out.target=nil;out.plannedTo=nil
        local demandID
        for i=#out.executionSteps,1,-1 do local step=out.executionSteps[i]
            if step.profession=="__purchase" then
                demandID=step.segmentID;out.crafts=out.crafts-step[4];table.remove(out.executionSteps,i)
            end
        end
        for i=#out.steps,1,-1 do if out.steps[i].profession=="__purchase" then table.remove(out.steps,i) end end
        for _,step in ipairs(out.executionSteps) do for _,allocation in ipairs(step.allocations) do
            if allocation.consumerID==demandID then allocation.consumerID="demand:"..allocation.itemID end
        end end
        for _,allocation in ipairs(out.seedAllocations) do if allocation.consumerID==demandID then allocation.consumerID="demand:"..allocation.itemID end end
        for i=#out.actions,1,-1 do local a=out.actions[i]
            if a.type=="craft" and a.profession=="__purchase" then out.dependencyGraph[a.id]=nil;table.remove(out.actions,i) end
        end
    end
    out.alreadyAtTarget=out.targetReached and out.start~=nil and out.target~=nil
        and out.start>=out.target and #out.steps==0 and #out.executionSteps==0 or false
    return finishResult(job,out,state,status)
end
local function rebatchSameMap(a, b)
    a, b = a or {}, b or {}
    for k, v in pairs(a) do if b[k] ~= v then return false end end
    for k, v in pairs(b) do if a[k] ~= v then return false end end
    return true
end

local function rebatchSameKeys(a, b)
    a, b = a or {}, b or {}
    for k in pairs(a) do if b[k] == nil then return false end end
    for k in pairs(b) do if a[k] == nil then return false end end
    return true
end

local function rebatchEquivalent(a, b, progressGoals, preserveGreen, relaxCap)
    if not a or not b or math.abs((a.money or 0) - (b.money or 0)) > 1e-7 then return false end
    local risk=preserveGreen~=false and a.risk
    if risk and (not b.risk or R.Compare(b.risk,a.risk)>0) then return false end
    if not risk and preserveGreen~=false and ((b.greenLevelCrafts or 0)>(a.greenLevelCrafts or 0)
        or a.rebatchGreenCrafts~=nil and (b.rebatchGreenCrafts or 0)>a.rebatchGreenCrafts) then return false end
    for _, key in ipairs({"inv", "unusable", "unusableSeed", "produced", "priorityProduced", "profitMade",
            "cap", "ahUsed", "formulaPaid", "specializationAbilities",
            "completedSpecializationGoals", "completedToolGoals"}) do
        if (key~="cap" or not (relaxCap or risk)) and not rebatchSameMap(a[key], b[key]) then return false end
    end
    if not rebatchSameKeys(a.skill, b.skill) then return false end
    for profession, oldSkill in pairs(not risk and a.skill or {}) do
        local newSkill = b.skill[profession]
        local goal=progressGoals and progressGoals[profession] or 300
        if type(oldSkill) ~= "number" or type(newSkill) ~= "number"
            or newSkill < min(oldSkill,goal) then return false end
        if newSkill == oldSkill and oldSkill < goal
            and (b.progress and b.progress[profession] or 0) + 1e-7
            < (a.progress and a.progress[profession] or 0) then return false end
    end
    return rebatchSameKeys(a.diagnostics, b.diagnostics)
end

local function rebatchKey(a)
    if a and a.type == "craft" and a.spell and a.profession then
        return tostring(a.profession) .. ":" .. tostring(a.spell)
    end
end

local function rebatchSwitches(list)
    local switches, previous = 0, nil
    for _, action in ipairs(list) do
        local key = rebatchKey(action)
        if key then
            if previous and previous ~= key then switches = switches + 1 end
            previous = key
        end
    end
    return switches
end

local function rebatchStages(list, recipes, rebuild, caps, tools, reorderRanks)
    local stages, skill = {}, {}
    for _, a in ipairs(list) do
        if a.profession and skill[a.profession]==nil then skill[a.profession]=a.from end
    end
    caps=caps and copyStateMap(caps)
    local first, opening = 1, copyStateMap(skill)
    local function close(last)
        if last>=first then stages[#stages+1]={first,last} end
        first=last+1;opening=copyStateMap(skill)
    end
    for i,a in ipairs(list) do
        local key=rebatchKey(a)
        if key then
            local r=recipes and recipes[key]
            if not rebuild and r and r.learn>(opening[a.profession] or a.from or 0) then close(i-1) end
            skill[a.profession]=a.to or skill[a.profession]
            for _,cap in ipairs({75,150,225}) do
                if not reorderRanks and (a.from or 0)<cap and (a.to or 0)>=cap and (not caps or (caps[a.profession] or 300)<=cap) then
                    if caps then caps[a.profession]=min(300,cap+75) end
                    close(i);break
                end
            end
        elseif a.type~="buy" and not (rebuild and a.type=="formula")
            and not (a.type=="tool_goal" and tools and tools[a.goalID]) then
            close(i-1)
            if a.profession and a.to then skill[a.profession]=a.to end
            first=i+1;opening=copyStateMap(skill)
        end
    end
    close(#list)
    return stages
end

local function rebatchDependencies(list, checkpoint, reorderLeveling, reorderConsumers)
    local edges, pools, consumers, lastBuy, lastMade = {}, {}, {}, {}, {}
    local lastLevel
    local function edge(from,to)
        if from and from~=to then edges[from][to]=true end
    end
    local function add(id,n,index,crafted)
        if not id or not n or n<=0 then return end
        local pool=pools[id] or {{head=1},{head=1}};pools[id]=pool
        local lots=pool[crafted and 2 or 1]
        lots[#lots+1]={count=n,index=index}
        local previous=crafted and lastMade or lastBuy
        edge(previous[id],index);previous[id]=index
    end
    for i,a in ipairs(list) do
        if not checkpoint() then return end
        edges[i]={}
        for _,m in ipairs(a.inputs or {}) do
            local need, origins=m[2],{}
            local pool=pools[m[1]] or {}
            for pass=1,2 do
                local lots=pool[pass] or {head=1}
                while need>0 and lots.head<=#lots do
                    local lot=lots[lots.head];local n=min(need,lot.count)
                    if n>0 then edge(lot.index,i);origins[#origins+1]=lot.index end
                    lot.count=lot.count-n;need=need-n
                    if lot.count<=0 then lots.head=lots.head+1 end
                end
            end
            local single=#origins==1 and need==0 and origins[1] or nil
            local previous=consumers[m[1]]
            if not previous or not single or previous.single~=single then
                if not reorderConsumers then for _,index in ipairs(previous or {}) do edge(index,i) end end
                previous={single=single};consumers[m[1]]=previous
            end
            previous[#previous+1]=i
            edge(lastBuy[m[1]],i)
        end
        if a.type=="buy" or a.type=="seed" then
            if not reorderConsumers then for _,index in ipairs(consumers[a.item] or {}) do edge(index,i) end end
            consumers[a.item]=nil
            if a.usableOutput~=false then add(a.item,a.count,i,false) end
        elseif a.usableOutput~=false then
            for _,m in ipairs(a.outputs or {}) do add(m[1],m[2],i,a.type=="craft") end
        end
        if not reorderLeveling and rebatchKey(a) and a.reason and a.reason~="material" then
            edge(lastLevel,i);lastLevel=i
        end
    end
    return edges
end

local function rebatchStageOrder(list, edges, lo, hi, checkpoint, preferred)
    local remaining, done, ready, byKey = {}, {}, {}, {}
    local keys,external,seen={},{},{}
    local function push(heap,value)
        local i=#heap+1
        while i>1 do
            local parent=floor(i/2)
            if heap[parent]<value then break end
            heap[i]=heap[parent];i=parent
        end
        heap[i]=value
    end
    local function pop(heap)
        local first=heap[1];local value=table.remove(heap)
        if #heap>0 then
            local i=1
            while i*2<=#heap do
                local child=i*2
                if child<#heap and heap[child+1]<heap[child] then child=child+1 end
                if heap[child]>=value then break end
                heap[i]=heap[child];i=child
            end
            heap[i]=value
        end
        return first
    end
    local function peek(heap)
        if not heap then return end
        while heap[1] and done[heap[1]] do pop(heap) end
        return heap[1]
    end
    local function release(i)
        push(ready,i)
        local key=rebatchKey(list[i]) or "buy"
        byKey[key]=byKey[key] or {};push(byKey[key],i)
    end
    for i=lo,hi do
        remaining[i]=0
        local key=rebatchKey(list[i]) or "buy"
        if not seen[key] then seen[key]=true;keys[#keys+1]=key;external[key]=0 end
    end
    for i=lo,hi do
        if not checkpoint() then return end
        for to in pairs(edges[i]) do if to<=hi then
            remaining[to]=remaining[to]+1
            local key=rebatchKey(list[to]) or "buy"
            if key~="buy" and rebatchKey(list[i]) and key~=rebatchKey(list[i]) then external[key]=external[key]+1 end
        end end
    end
    for i=lo,hi do if remaining[i]==0 then release(i) end end
    local out, previous = {}, nil
    for _=lo,hi do
        if not checkpoint() then return end
        local index=peek(byKey.buy) or preferred and peek(byKey[preferred]) or previous and peek(byKey[previous])
        if not index then
            for _,key in ipairs(keys) do
                local candidate=external[key]==0 and peek(byKey[key])
                if candidate and (not index or candidate<index) then index=candidate end
            end
        end
        index=index or peek(ready)
        if not index then return end
        done[index]=true;out[#out+1]=list[index]
        previous=rebatchKey(list[index]) or previous
        for to in pairs(edges[index]) do if to<=hi then
            remaining[to]=remaining[to]-1
            local key=rebatchKey(list[to]) or "buy"
            if key~="buy" and rebatchKey(list[index]) and key~=rebatchKey(list[index]) then external[key]=external[key]-1 end
            if remaining[to]==0 then release(to) end
        end end
    end
    return out
end

local function rebatchGrayOrder(list,lo,hi,recipes,checkpoint)
    local batches,keys,out={},{},{}
    for i=lo,hi do
        if not checkpoint() then return end
        local a=list[i];local key=rebatchKey(a);local r=key and recipes and recipes[key]
        if r and a.reason=="material" and (a.from or 0)>=r.grey then
            keys[i]=key;batches[key]=batches[key] or {};batches[key][#batches[key]+1]=a
        end
        if a.type=="buy" then out[#out+1]=a end
    end
    local emitted={}
    for i=lo,hi do
        local a,key=list[i],keys[i]
        if key then
            if not emitted[key] then
                for _,entry in ipairs(batches[key]) do out[#out+1]=entry end
                emitted[key]=true
            end
        elseif a.type~="buy" then out[#out+1]=a end
    end
    return out
end

function S.RebatchChronological(original, replay, tick, cpuTime, recipes, grayMaterials, progressGoals, reorderLeveling, caps, preserveGreen, control)
    if not original or type(replay) ~= "function" then return original end
    local list = actions(original)
    if #list < 3 then return original end
    local occurrences, duplicate = {}, false
    for _, action in ipairs(list) do
        local key = rebatchKey(action)
        if key then
            if occurrences[key] then duplicate = true; break end
            occurrences[key] = true
        end
    end
    if not duplicate then return original end
    local best, attempts = original, 0
    local maxAttempts = #list > 600 and 3 or #list > 200 and 6 or 12
    local maxProbes = #list > 600 and 18 or #list > 200 and 36 or 96
    local probes = 0
    local useCPU = type(cpuTime)=="function"
    local started = useCPU and cpuTime()
        or (type(debugprofilestop)=="function" and debugprofilestop() or nil)
    local function timeExceeded()
        if control then
            if control.exhausted then return true end
            if control.remainingWork and control.remainingWork<=0 then control.exhausted=true;return true end
            local now=useCPU and cpuTime() or type(debugprofilestop)=="function" and debugprofilestop()
            if control.deadline and now and now>=control.deadline then control.exhausted=true;return true end
        end
        if reorderLeveling or grayMaterials or not started then return false end
        return (useCPU and cpuTime() or debugprofilestop()) - started
            >= (useCPU and 60 or 200)
    end
    local work=0
    local function checkpoint()
        if control and control.exhausted then return false end
        if control and control.remainingWork then
            if control.remainingWork<=0 then control.exhausted=true;return false end
            control.remainingWork=control.remainingWork-1
        end
        work=work+1
        if work%64==0 then
            if tick then tick() end
            return not timeExceeded()
        end
        return true
    end
    if timeExceeded() then return original end
    local stages=rebatchStages(list,recipes,grayMaterials,(reorderLeveling or grayMaterials) and (caps or original.cap))
    local edges=grayMaterials and {} or rebatchDependencies(list,checkpoint,reorderLeveling,reorderLeveling)
    if not edges then return original end
    local currentScore = rebatchSwitches(list)
    local order=list
    local function replayCandidate(candidateOrder)
        if tick then tick() end
        if timeExceeded() then return end
        if control and control.remainingReplays then
            if control.remainingReplays<=0 then control.exhausted=true;return end
            control.remainingReplays=control.remainingReplays-1
        end
        return replay(candidateOrder,control and checkpoint or nil)
    end
    if reorderLeveling or grayMaterials then
        local initialScore,minimumScore,completed,total=currentScore,0,0,1
        local failedPrefixes={}
        local function report(fraction)
            if control and control.onProgress then
                control.onProgress(fraction or (initialScore-currentScore+completed/max(1,total))/max(1,initialScore-minimumScore+1))
            end
        end
        local function accept(candidateOrder)
            if timeExceeded() then return false end
            completed=completed+1
            if not candidateOrder or rebatchSwitches(candidateOrder)>=currentScore then report();return false end
            local prefix=failedPrefixes
            for _,a in ipairs(candidateOrder) do
                prefix=prefix[a]
                if not prefix then break end
                if prefix.failed then report();return false end
                if not checkpoint() then return false end
            end
            local candidate,failedAt=replayCandidate(candidateOrder)
            if not candidate and type(failedAt)=="number" and failedAt%1==0 and failedAt>=1 and failedAt<=#candidateOrder then
                prefix=failedPrefixes
                for i=1,failedAt do
                    local a=candidateOrder[i];prefix[a]=prefix[a] or {};prefix=prefix[a]
                    if not checkpoint() then return false end
                end
                prefix.failed=true
            end
            if not rebatchEquivalent(original,candidate,progressGoals,preserveGreen) then report();return false end
            local score=rebatchSwitches(actions(candidate))
            if score>=currentScore then report();return false end
            best,currentScore=candidate,score
            completed=0;report()
            return true
        end
        local function replace(lo,hi,sorted)
            if not sorted then return accept(nil) end
            local candidate={}
            for i,a in ipairs(list) do candidate[i]=a;if not checkpoint() then return false end end
            for i,a in ipairs(sorted) do candidate[lo+i-1]=a;if not checkpoint() then return false end end
            return accept(candidate)
        end
        local function merge(lo,hi,selected)
            local marked,block,rest,positions={},{},{},{}
            for _,i in ipairs(selected) do marked[i]=true;block[#block+1]=list[i];if not checkpoint() then return false end end
            for i=lo,hi do if not marked[i] then rest[#rest+1]=list[i] end;positions[i]=#rest;if not checkpoint() then return false end end
            local first,last=0,#rest
            for i=lo,hi do
                for to in pairs(edges[i]) do if to<=hi then
                    if marked[i] and not marked[to] then last=min(last,positions[to]-1)
                    elseif not marked[i] and marked[to] then first=max(first,positions[i]) end
                end end
                if not checkpoint() then return false end
            end
            completed=completed+hi-lo+2-max(0,last-first+1);report()
            local slots,seen={},{}
            local function slotAt(slot)
                if slot>=first and slot<=last and not seen[slot] then seen[slot]=true;slots[#slots+1]=slot end
            end
            slotAt(first);slotAt(last)
            for _,i in ipairs(selected) do slotAt(positions[i]) end
            for slot=first,last do slotAt(slot);if not checkpoint() then return false end end
            for _,slot in ipairs(slots) do
                local sorted={}
                for i=1,slot do sorted[#sorted+1]=rest[i];if not checkpoint() then return false end end
                for _,a in ipairs(block) do sorted[#sorted+1]=a;if not checkpoint() then return false end end
                for i=slot+1,#rest do sorted[#sorted+1]=rest[i];if not checkpoint() then return false end end
                if replace(lo,hi,sorted) then return true end
                if not checkpoint() then return false end
            end
            return false
        end
        local changed=true
        while changed do
            if timeExceeded() then return best end
            changed=false;list=actions(best,tick)
            local distinct,n={},0
            for _,a in ipairs(list) do
                local key=rebatchKey(a)
                if key and not distinct[key] then distinct[key]=true;n=n+1 end
                if not checkpoint() then return best end
            end
            if currentScore<=n-1 then break end
            minimumScore=n-1;completed=0;failedPrefixes={}
            edges=rebatchDependencies(list,checkpoint,reorderLeveling,true)
            if not edges then return best end
            local plans={};total=grayMaterials and 1 or 2
            for pass=1,grayMaterials and 1 or 2 do
                stages=rebatchStages(list,recipes,grayMaterials or pass==2,caps or original.cap,nil,reorderLeveling and pass==2)
                plans[#plans+1]=stages
                for _,range in ipairs(stages) do
                local lo,hi=range[1],range[2];total=total+1
                local groups,keys,last={},{},nil
                for i=lo,hi do
                    local a=list[i];local key=rebatchKey(a);local r=key and recipes and recipes[key]
                    if key then
                        if not grayMaterials or r and a.reason=="material" and (a.from or 0)>=r.grey then
                            if not groups[key] then groups[key]={};keys[#keys+1]=key end
                            local runs=groups[key]
                            if last~=key or #runs==0 then runs[#runs+1]={} end
                            runs[#runs][#runs[#runs]+1]=i
                        end
                        last=key
                    end
                    if not checkpoint() then return best end
                end
                range.groups={}
                for _,key in ipairs(keys) do
                    local runs=groups[key]
                    if #runs>1 then
                        local selected={}
                        for _,run in ipairs(runs) do for _,i in ipairs(run) do selected[#selected+1]=i end end
                        range.groups[#range.groups+1]={key=key,runs=runs,selected=selected}
                        total=total+2+(hi-lo+2)*(1+(#runs>2 and #runs*(#runs-1)/2 or 0))
                    end
                    if not checkpoint() then return best end
                end
                end
            end
            report()
            for _,ranges in ipairs(plans) do
                local combined={}
                for i,a in ipairs(list) do combined[i]=a;if not checkpoint() then return best end end
                for _,range in ipairs(ranges) do
                    local sorted=grayMaterials and rebatchGrayOrder(list,range[1],range[2],recipes,checkpoint)
                        or rebatchStageOrder(list,edges,range[1],range[2],checkpoint)
                    if sorted then for i,a in ipairs(sorted) do combined[range[1]+i-1]=a end end
                    if not checkpoint() then return best end
                end
                changed=accept(combined)
                if changed then break end
                if timeExceeded() then return best end
            end
            if not changed then for _,ranges in ipairs(plans) do
            for _,range in ipairs(ranges) do
                local lo,hi=range[1],range[2]
                local sorted=grayMaterials and rebatchGrayOrder(list,lo,hi,recipes,checkpoint)
                    or rebatchStageOrder(list,edges,lo,hi,checkpoint)
                if replace(lo,hi,sorted) then changed=true;break end
                for _,group in ipairs(range.groups) do
                    local key,runs,selected=group.key,group.runs,group.selected
                    local first,last=selected[1],selected[#selected]
                    sorted=rebatchStageOrder(list,edges,first,last,checkpoint,key)
                    if replace(first,last,sorted) then changed=true;break end
                    if timeExceeded() then return best end
                    sorted=rebatchStageOrder(list,edges,lo,hi,checkpoint,key)
                    if replace(lo,hi,sorted) then changed=true;break end
                    if merge(lo,hi,selected) then changed=true;break end
                    if #runs>2 then for i=1,#runs-1 do
                        for k=i+1,#runs do
                            selected={}
                            for _,index in ipairs(runs[i]) do selected[#selected+1]=index end
                            for _,index in ipairs(runs[k]) do selected[#selected+1]=index end
                            if merge(lo,hi,selected) then changed=true;break end
                            if timeExceeded() then return best end
                        end
                        if changed then break end
                    end end
                    if changed then break end
                    if timeExceeded() then return best end
                end
                if changed then break end
            end
            if changed then break end
            end end
        end
        report(1)
        return best
    end
    local function improve(lo,hi)
        if hi-lo<2 or attempts>=maxAttempts or probes>=maxProbes or timeExceeded() then return end
        probes=probes+1
        local candidateOrder={};for i,a in ipairs(order) do candidateOrder[i]=a end
        for _,stage in ipairs(stages) do
            local first,last=max(lo,stage[1]),min(hi,stage[2])
            if last>first then
                local sorted=grayMaterials and rebatchGrayOrder(list,first,last,recipes,checkpoint)
                    or not grayMaterials and rebatchStageOrder(list,edges,first,last,checkpoint)
                if not sorted then return end
                for i,a in ipairs(sorted) do candidateOrder[first+i-1]=a end
            end
        end
        if rebatchSwitches(candidateOrder)>=currentScore or timeExceeded() then return end
        attempts=attempts+1
        local candidate=replayCandidate(candidateOrder)
        if rebatchEquivalent(best,candidate,progressGoals,preserveGreen) then
            local score=rebatchSwitches(actions(candidate))
            if score<currentScore then best,order,currentScore=candidate,candidateOrder,score;return end
        end
        local middle=floor((lo+hi)/2)
        improve(lo,middle);improve(middle+1,hi)
    end
    improve(1,#list)
    return best
end

function S.BatchFeasible(model,tick,report)
    local char,byte=string.char,string.byte
    local rows=model.rows or {}
    local stats={states=0,transitions=0,memoHits=0,skillStates=0,skillMemoHits=0,skillPruned=0,gatePruned=0,greenPruned=0,work=0,bestSegments=(model.limit or 0)+1,pending=1,progress=0}
    local function close(start,weight)
        stats.progress=max(stats.progress,min(1-1e-12,start+weight))
    end
    local function checkpoint()
        stats.work=stats.work+1
        if stats.work%128==0 and tick then tick() end
        if stats.work%4096==0 and report then report(stats) end
    end
    local function unknown(reason)
        stats.reason=reason
        return nil,nil,stats
    end
    local function integer(n) return type(n)=="number" and n==floor(n) and n>=0 and n<math.huge end
    local greenLimit=model.greenLimit
    if model.optimisticSkill then greenLimit=nil end
    if greenLimit~=nil and not integer(greenLimit) then return unknown("invalid_green_limit") end
    local greenTarget=model.greenTarget
    if greenTarget~=nil and (not integer(greenTarget) or greenTarget<1 or greenTarget>300) then return unknown("invalid_green_target") end
    if not integer(model.limit) or not integer(model.skill) or model.skill<1 or model.skill>300
        or not integer(model.cap) or model.cap<1 or model.cap>300
        or type(model.progress or 0)~="number" or (model.progress or 0)<0 or (model.progress or 0)>=1
        or not integer(model.target) or model.target<1 or model.target>300
        or type(model.targetProgress or 0)~="number" or (model.targetProgress or 0)<0 or (model.targetProgress or 0)>=1 then return unknown("invalid_state") end
    local cacheLimit=model.cacheEntries or 50000
    if not integer(cacheLimit) or cacheLimit<1 then return unknown("invalid_cache_size") end
    local function cache()
        local recent,older,entries={},{},0
        local function get(key)
            local value=recent[key]
            if value~=nil then return value end
            return older[key]
        end
        local function put(key,value)
            if recent[key]==nil then
                if entries>=cacheLimit then
                    older=recent;recent={};entries=0;stats.cacheRotations=(stats.cacheRotations or 0)+1
                end
                entries=entries+1
            end
            recent[key]=value
        end
        return get,put
    end
    local integerCodes={}
    local function code(n)
        local value=integerCodes[n]
        if value then return value end
        local parts={};local rest=n
        repeat
            local nextValue=floor(rest/128)
            parts[#parts+1]=char(rest%128+(nextValue>0 and 128 or 0));rest=nextValue
        until rest==0
        value=table.concat(parts);integerCodes[n]=value
        return value
    end
    local function pack(skill,progress,cap)
        return char(floor(skill/256),skill%256,floor(progress/65536),floor(progress/256)%256,progress%256,floor(cap/256),cap%256)
    end
    local function unpackState(sequence,count)
        local text=type(sequence)=="table" and sequence.states or sequence
        local index=min(count,#text/7);local offset=(index-1)*7+1
        local a,b,c,d,e,f,g=byte(text,offset,offset+6)
        return a*256+b,c*65536+d*256+e,f*256+g,type(sequence)=="table" and sequence.greens[index] or 0
    end
    local counts,mats,output,terminal,gain,seen,consumed={},{},{},{},{},{},{}
    local inventory={}
    for id,n in pairs(model.inventory or {}) do if not integer(n) then return unknown("fractional_inventory") end;inventory[id]=n end
    for i,r in ipairs(rows) do
        if not r.key or seen[r.key] or not integer(r.count) then return unknown("invalid_rows") end
        seen[r.key]=true;counts[i]=r.count;output[i]=r.output or 0
        if not integer(output[i]) or not integer(r.learn) or type(r.grey)~="number"
            or type(r.yellow)~="number" or type(r.green)~="number"
            or r.yellow>r.green or r.green>r.grey then return unknown("invalid_recipe") end
        mats[i]={};local byItem={}
        for _,m in ipairs(r.mats or {}) do
            if not integer(m[2]) or m[2]==0 or m[1]==r.item then return unknown("unsupported_reagent") end
            byItem[m[1]]=(byItem[m[1]] or 0)+m[2];consumed[m[1]]=true
        end
        for id,n in pairs(byItem) do mats[i][#mats[i]+1]={id,n} end
        gain[i]={}
        if not model.exactReasons then for skill=0,300 do
            local value=E.Gain(r,skill);gain[i][skill]=model.optimisticSkill and value>0 and 1 or value;checkpoint()
        end end
    end
    if model.exactReasons then return S.BatchTaskFeasible(model,tick,report) end
    for i,r in ipairs(rows) do terminal[i]=not r.item or not consumed[r.item] end
    local function candidateCounts(i,n,maximum,full,preferredFirst)
        local result,seen={},{}
        local function add(count)
            if integer(count) and count>0 and (count<=maximum or full and count==n) and not seen[count] then
                result[#result+1]=count;seen[count]=true
            end
        end
        if not preferredFirst and full then add(n) end
        for _,count in ipairs(rows[i].preferredCounts or {}) do
            add(count)
            checkpoint()
        end
        if full then add(n) end
        for count=maximum,1,-1 do
            if not seen[count] then result[#result+1]=count end
            checkpoint()
        end
        return result
    end
    local target,targetProgress=model.target,model.optimisticSkill and 0 or floor((model.targetProgress or 0)*1000000+.5)
    local function reached(skill,progress)
        return skill>target or skill==target and progress>=targetProgress
    end
    local function step(i,skill,progress,cap)
        local r=rows[i];local g=gain[i][skill]
        if g>0 and skill>=cap then
            if r.reason=="level" or r.reason=="secondary" then
                if cap<300 then cap=cap<=75 and 150 or cap<=150 and 225 or 300 end
            else g=0 end
        end
        local value=progress/1000000+g;local whole=floor(value+1e-7)
        local green=greenLimit and not r.ignoreGreen and g>0 and skill>=r.green
            and (not greenTarget or skill<greenTarget)
            and (r.reason=="level" or r.reason=="secondary") and 1 or 0
        stats.transitions=stats.transitions+1;checkpoint()
        return min(300,skill+whole),floor((value-whole)*1000000+.5),cap,green
    end
    local sequenceGet,sequencePut=cache()
    local function sequence(i,skill,progress,cap,n)
        local signature=code(i)..pack(skill,progress,cap)
        local saved=sequenceGet(signature)
        local length,green=0,0
        if saved then
            length=#(type(saved)=="table" and saved.states or saved)/7
            skill,progress,cap,green=unpackState(saved,length)
            if length>=n or skill>=rows[i].grey then stats.sequenceHits=(stats.sequenceHits or 0)+1;return saved end
        end
        local parts={saved and (type(saved)=="table" and saved.states or saved) or ""}
        local greens={}
        if greenLimit and saved then for i,value in ipairs(saved.greens) do greens[i]=value;checkpoint() end end
        for count=length+1,n do
            local delta
            skill,progress,cap,delta=step(i,skill,progress,cap);green=green+delta
            if greenLimit then greens[count]=green end
            parts[#parts+1]=pack(skill,progress,cap)
            if skill>=rows[i].grey then break end
        end
        saved=greenLimit and {states=table.concat(parts),greens=greens} or table.concat(parts);sequencePut(signature,saved)
        return saved
    end
    local function key(skill,progress,cap,last,green)
        local parts={}
        for i,n in ipairs(counts) do parts[i]=code(n) end
        parts[#parts+1]=pack(skill,progress,cap);parts[#parts+1]=code(last and counts[last]>0 and last or 0)
        if greenLimit then parts[#parts+1]=code(green or 0) end
        return table.concat(parts)
    end
    local function gate(skill,progress)
        local threshold=not reached(skill,progress) and target+targetProgress/1000000 or nil
        local upper=skill+progress/1000000
        for i,r in ipairs(rows) do
            local n=counts[i]
            if n>0 then
                if r.learn>skill then threshold=min(threshold or math.huge,r.learn)
                else upper=upper+n*(gain[i][skill]+.000001) end
            end
        end
        return not threshold or upper+1e-7>=threshold
    end
    local skillGet,skillPut=cache()
    local function rememberSkill(stateKey,budget,valid)
        local saved=skillGet(stateKey) or {}
        if valid then saved.minTrue=min(saved.minTrue or math.huge,budget)
        else saved.maxFalse=max(saved.maxFalse or -1,budget) end
        skillPut(stateKey,saved)
    end
    local function skillSearch(skill,progress,cap,budget,green,start,weight)
        stats.skillStates=stats.skillStates+1;checkpoint()
        if greenLimit and green>greenLimit then stats.greenPruned=stats.greenPruned+1;close(start,weight);return false end
        local gray,needed={},0
        for i,r in ipairs(rows) do
            if counts[i]>0 then
                if skill>=r.grey then gray[#gray+1]={i,counts[i]};counts[i]=0;budget=budget-1
                else needed=needed+1 end
            end
        end
        local function finish(value)
            for _,entry in ipairs(gray) do counts[entry[1]]=entry[2] end
            close(start,weight)
            return value
        end
        if needed>budget then return finish(false) end
        if reached(skill,progress) and (not greenLimit or needed==0) then return finish(true) end
        if needed==1 then
            for i,r in ipairs(rows) do if counts[i]>0 then
                if skill<r.learn then return finish(false) end
                local nextSkill,nextProgress,_,delta=unpackState(sequence(i,skill,progress,cap,counts[i]),counts[i])
                return finish((not greenLimit or green+delta<=greenLimit) and reached(nextSkill,nextProgress))
            end end
        end
        local stateKey=key(skill,progress,cap,nil,green)
        local cached=skillGet(stateKey)
        if cached and cached.minTrue and budget>=cached.minTrue then
            stats.skillMemoHits=stats.skillMemoHits+1
            if budget>cached.minTrue then stats.skillBudgetHits=(stats.skillBudgetHits or 0)+1 end
            return finish(true)
        elseif cached and cached.maxFalse and budget<=cached.maxFalse then
            stats.skillMemoHits=stats.skillMemoHits+1
            if budget<cached.maxFalse then stats.skillBudgetHits=(stats.skillBudgetHits or 0)+1 end
            return finish(false)
        end
        if not gate(skill,progress) then rememberSkill(stateKey,budget,false);return finish(false) end
        local choices=0
        for i,r in ipairs(rows) do if counts[i]>0 and skill>=r.learn then choices=choices+1 end end
        local share=choices>0 and weight/choices or 0
        local nextStart=start
        for i,r in ipairs(rows) do
            local n=counts[i]
            if n>0 and skill>=r.learn then
                local encoded=sequence(i,skill,progress,cap,n)
                local length=#(type(encoded)=="table" and encoded.states or encoded)/7
                local candidates=candidateCounts(i,n,budget>needed and min(n-1,length) or 0,true,budget>needed+3)
                local portion=#candidates>0 and share/#candidates or 0
                for index,count in ipairs(candidates) do
                    local nextSkill,nextProgress,nextCap,delta=unpackState(encoded,count)
                    local branchStart=nextStart+(index-1)*portion
                    if count==n or nextSkill<r.grey then
                        counts[i]=n-count
                        local valid=skillSearch(nextSkill,nextProgress,nextCap,budget-1,green+delta,branchStart,portion)
                        counts[i]=n
                        if valid then rememberSkill(stateKey,budget,true);return finish(true) end
                    else close(branchStart,portion) end
                end
                close(nextStart,share);nextStart=nextStart+share
            end
        end
        rememberSkill(stateKey,budget,false)
        return finish(false)
    end
    local memoGet,memoPut=cache()
    local function rememberFailure(stateKey,budget)
        local saved=memoGet(stateKey)
        if saved==nil or budget>saved then memoPut(stateKey,budget) end
    end
    local path,solution={},nil
    local function inventoryChange(i,n)
        for _,m in ipairs(mats[i]) do inventory[m[1]]=(inventory[m[1]] or 0)-m[2]*n end
        local r=rows[i]
        if r.item then inventory[r.item]=(inventory[r.item] or 0)+output[i]*n end
    end
    local function copyPath(extra)
        local out={}
        for _,entry in ipairs(path) do out[#out+1]={index=entry.index,key=entry.key,count=entry.count} end
        for _,i in ipairs(extra or {}) do out[#out+1]={index=i,key=rows[i].key,count=counts[i]} end
        return out
    end
    local function search(skill,progress,cap,budget,last,green,start,weight)
        stats.states=stats.states+1;checkpoint()
        local function finish(value) close(start,weight);return value end
        if greenLimit and green>greenLimit then stats.greenPruned=stats.greenPruned+1;return finish(false) end
        local needed,active,postponed,skip=0,0,{},{}
        for i,r in ipairs(rows) do if counts[i]>0 then
            needed=needed+1
            if skill<r.grey then active=active+1 end
            if terminal[i] and skill>=r.grey and skill>=r.learn then postponed[#postponed+1]=i;skip[i]=true end
        end end
        if needed>budget then return finish(false) end
        if needed==0 then if reached(skill,progress) then solution=copyPath();return finish(true) end;return finish(false) end
        if not gate(skill,progress) then stats.gatePruned=stats.gatePruned+1;return finish(false) end
        local stateKey=key(skill,progress,cap,last,green)
        local failedBudget=memoGet(stateKey)
        if failedBudget~=nil and budget<=failedBudget then
            stats.memoHits=stats.memoHits+1
            if budget<failedBudget then stats.budgetMemoHits=(stats.budgetMemoHits or 0)+1 end
            return finish(false)
        end
        local checkSkill=budget<=needed+1 or active<=1
        local availableByRow,choices={},checkSkill and 1 or 0
        for i,r in ipairs(rows) do
            local n=counts[i]
            if n>0 and i~=last and skill>=r.learn and not skip[i] then
                local available=n
                for _,m in ipairs(mats[i]) do available=min(available,floor((inventory[m[1]] or 0)/m[2])) end
                if available>0 and (available==n or budget>needed) then availableByRow[i]=available;choices=choices+1 end
            end
        end
        local share=choices>0 and weight/choices or 0
        local nextStart=start
        if checkSkill then
            local valid=skillSearch(skill,progress,cap,budget,green,nextStart,share)
            nextStart=nextStart+share
            if not valid then stats.skillPruned=stats.skillPruned+1;rememberFailure(stateKey,budget);return finish(false) end
        end
        if #postponed==needed then
            local required={}
            for _,i in ipairs(postponed) do for _,m in ipairs(mats[i]) do required[m[1]]=(required[m[1]] or 0)+counts[i]*m[2] end end
            for id,n in pairs(required) do if (inventory[id] or 0)<n then rememberFailure(stateKey,budget);return finish(false) end end
            if reached(skill,progress) then solution=copyPath(postponed);return finish(true) end
            rememberFailure(stateKey,budget);return finish(false)
        end
        for i,r in ipairs(rows) do
            local n=counts[i]
            local available=availableByRow[i]
            if available then
                    local encoded=sequence(i,skill,progress,cap,available)
                    local candidates=candidateCounts(i,n,budget>needed and min(available,n-1) or 0,available==n,budget>needed+3)
                    local portion=#candidates>0 and share/#candidates or 0
                    local function attempt(count,branchStart)
                        counts[i]=n-count;inventoryChange(i,count)
                        path[#path+1]={index=i,key=r.key,count=count}
                        local nextSkill,nextProgress,nextCap,delta=unpackState(encoded,count)
                        local valid=search(nextSkill,nextProgress,nextCap,budget-1,i,green+delta,branchStart,portion)
                        path[#path]=nil;inventoryChange(i,-count);counts[i]=n
                        return valid
                    end
                    for index,count in ipairs(candidates) do
                        if attempt(count,nextStart+(index-1)*portion) then return finish(true) end
                    end
                    close(nextStart,share);nextStart=nextStart+share
            end
        end
        rememberFailure(stateKey,budget)
        return finish(false)
    end
    if report then report(stats) end
    local feasible=search(model.skill,model.optimisticSkill and 0 or floor((model.progress or 0)*1000000+.5),model.cap,model.limit,nil,0,0,1)
    stats.finished=true;stats.feasible=feasible;stats.pending=0;stats.progress=1
    if report then report(stats) end
    return feasible,solution,stats
end

function S.BatchTaskFeasible(model,tick,report)
    local rows,byKey,totals,indexes=model.rows or {},{},{},{}
    local probabilityMode=model.probabilityMode
    local stats={states=0,skillStates=0,transitions=0,pending=1,bestSegments=(model.limit or 0)+1}
    local function unknown(reason) stats.reason=reason;return nil,nil,stats end
    if type(model.limit)~="number" or model.limit<0 or model.limit~=floor(model.limit)
        or model.limit==math.huge or type(model.actions)~="table" then return unknown("invalid_tasks") end
    local profession=model.profession or model.actions[1] and model.actions[1].profession
    if not profession then return unknown("missing_profession") end
    local function checkpoint() if tick then tick() end end
    for index,r in ipairs(rows) do byKey[r.key]=r;totals[r.key]=0;indexes[r.key]=index;checkpoint() end
    local greenLimit=model.greenLimit
    if model.optimisticSkill then greenLimit=nil end
    local targetProgress=model.optimisticSkill and 0 or floor((model.targetProgress or 0)*1000000+.5)/1000000
    local goal=max(model.goal or model.target,model.target+(targetProgress>0 and 1 or 0))
    local initialState={inv=copyStateMap(model.inventory),skill={[profession]=model.skill},
        progress={[profession]=model.optimisticSkill and 0 or floor((model.progress or 0)*1000000+.5)/1000000},cap={[profession]=model.cap},
        diagnostics={},money=0,greenLevelCrafts=0,rebatchGreenCrafts=0}
    local original={inv=copyStateMap(model.inventory),skill={[profession]=model.target},progress={[profession]=targetProgress},
        cap={[profession]=model.cap},diagnostics={},money=0,greenLevelCrafts=greenLimit or 0,rebatchGreenCrafts=greenLimit or 0}
    local equivalentReasons
    if probabilityMode then
        equivalentReasons={}
        local snapshot={recipes={},byKey={},known={},professions={[profession]={cur=model.skill,max=model.cap}}}
        for _,row in ipairs(rows) do
            local recipe={key=row.key,profession=profession,spell=tonumber(row.key:match(":(%d+)$")),learn=row.learn,
                yellow=row.yellow,green=row.green,grey=row.grey,item=row.item,count=row.output,mats=row.mats}
            if not recipe.spell then return unknown("invalid_recipe_key") end
            snapshot.recipes[#snapshot.recipes+1]=recipe;snapshot.byKey[row.key]=recipe;snapshot.known[row.key]=true;checkpoint()
            local cap=model.cap
            if model.skill<=cap then while cap<row.learn and cap<300 do cap=cap<=75 and 150 or cap<=150 and 225 or 300 end end
            equivalentReasons[row.key]=row.grey<=cap
        end
        initialState.risk=R.New(snapshot,profession,{start=model.skill,target=model.target,completionOnly=true},tick)
    end
    for _,a in ipairs(model.actions) do
        local key=rebatchKey(a);local r=key and byKey[key]
        if not r or a.profession~=profession or type(a.count)~="number" or a.count<1 or a.count~=floor(a.count) then
            return unknown("invalid_tasks")
        end
        totals[key]=totals[key]+a.count
        log(original,{type="craft",profession=profession,spell=a.spell,reason=a.reason,count=a.count})
        for _,m in ipairs(r.mats) do original.inv[m[1]]=(original.inv[m[1]] or 0)-m[2]*a.count;checkpoint() end
        if r.item then original.inv[r.item]=(original.inv[r.item] or 0)+(r.output or 0)*a.count end
        checkpoint()
    end
    for _,r in ipairs(rows) do if totals[r.key]~=r.count then return unknown("invalid_task_counts") end;checkpoint() end
    for _,n in pairs(original.inv) do if n<0 then stats.finished=true;stats.feasible=false;stats.progress=1;stats.pending=0;if report then report(stats) end;return false,nil,stats end end
    local function advance(state,a)
        local key=rebatchKey(a);local r=key and byKey[key]
        if not r or state.skill[profession]<r.learn then return end
        local count=a.count
        for _,m in ipairs(r.mats) do if (state.inv[m[1]] or 0)<m[2]*count then return end end
        local t={inv=copyStateMap(state.inv),skill=copyStateMap(state.skill),progress=copyStateMap(state.progress),
            cap=copyStateMap(state.cap),diagnostics=state.diagnostics,money=0,greenLevelCrafts=state.greenLevelCrafts,
            rebatchGreenCrafts=state.rebatchGreenCrafts,log=state.log,risk=state.risk}
        for _,m in ipairs(r.mats) do t.inv[m[1]]=t.inv[m[1]]-m[2]*count;checkpoint() end
        for _=1,probabilityMode and 0 or count do
            local skill=t.skill[profession];local gain=E.Gain(r,skill)
            if model.optimisticSkill and gain>0 then gain=1 end
            if gain>0 and skill>=t.cap[profession] then
                if a.reason=="level" or a.reason=="secondary" then
                    local cap=t.cap[profession]
                    if cap<300 then t.cap[profession]=cap<=75 and 150 or cap<=150 and 225 or 300 end
                else gain=0 end
            end
            if gain>0 and skill>=r.green and (not model.greenTarget or skill<model.greenTarget)
                and (a.reason=="level" or a.reason=="secondary") then
                t.greenLevelCrafts=t.greenLevelCrafts+1;t.rebatchGreenCrafts=t.rebatchGreenCrafts+1
            end
            local value=t.progress[profession]+gain;local whole=floor(value+1e-7)
            t.skill[profession]=min(300,skill+whole);t.progress[profession]=floor((value-whole)*1000000+.5)/1000000
            checkpoint()
        end
        if r.item then t.inv[r.item]=(t.inv[r.item] or 0)+(r.output or 0)*count end
        log(t,{type="craft",profession=profession,spell=a.spell,reason=a.reason,count=count})
        if probabilityMode then
            t.skill[profession]=R.SupportedSkill(t.risk,profession);t.progress[profession]=0;t.cap[profession]=300
        end
        return t
    end
    local suffixStates,suffixWork=0,0
    local function possible(state,left,tasks,budget,lastKey)
        local compact={rows={},inventory=copyStateMap(state.inv),skill=state.skill[profession],
            progress=state.progress[profession],cap=state.cap[profession],target=model.target,
            targetProgress=model.targetProgress,greenTarget=model.greenTarget,limit=budget,cacheEntries=model.cacheEntries,
            optimisticSkill=model.optimisticSkill}
        if greenLimit~=nil then
            compact.greenLimit=greenLimit-(state.greenLevelCrafts or 0)
            if compact.greenLimit<0 then return false end
        end
        local groups,kinds={},{}
        for i,task in ipairs(tasks) do
            local count=left[i]
            if count>0 then
                local r=task.key and byKey[task.key]
                if not r then return end
                local row=groups[task.key]
                if not row then
                    row={key=r.key,learn=r.learn,yellow=r.yellow,green=r.green,grey=r.grey,item=r.item,
                        output=r.output,mats=r.mats,count=0,reason=task.action.reason,preferredCounts=r.preferredCounts}
                    groups[task.key]=row;kinds[task.key]={};compact.rows[#compact.rows+1]=row
                end
                row.count=row.count+count
                kinds[task.key][(task.action.reason=="level" or task.action.reason=="secondary") and "level" or "material"]=true
            end
            checkpoint()
        end
        for _,row in ipairs(compact.rows) do
            local kind=kinds[row.key]
            if kind.level and kind.material then
                local cap=compact.cap
                if compact.skill<=cap then while cap<row.learn and cap<300 do cap=cap<=75 and 150 or cap<=150 and 225 or 300 end end
                if row.grey>cap then return end
                row.ignoreGreen=true
            end
            checkpoint()
        end
        if groups[lastKey] then compact.limit=compact.limit+1 end
        local feasible,_,counted=S.BatchFeasible(compact,tick,function(value)
            stats.skillStates=suffixStates+(value.states or 0)+(value.skillStates or 0)
            stats.suffixWork=suffixWork+(value.work or 0)
            if report then report(stats) end
        end)
        suffixStates=suffixStates+(counted and ((counted.states or 0)+(counted.skillStates or 0)) or 0)
        suffixWork=suffixWork+(counted and counted.work or 0)
        stats.skillStates=suffixStates;stats.suffixWork=suffixWork
        return feasible
    end
    local function accept(_,state)
        return rebatchSameMap(original.inv,state.inv) and R.Completion(state.risk)>=model.completionFloor*(1-1e-12)
    end
    local result=S.ScheduleBatches(original,initialState,advance,tick,{[profession]=goal},greenLimit~=nil,
        function(fraction,value)
            stats=value;stats.skillStates=suffixStates;stats.suffixWork=suffixWork;stats.progress=fraction
            if report then report(stats) end
        end,{segmentLimit=model.limit,firstFeasible=true,recipes=not model.optimisticSkill and byKey or nil,cacheEntries=model.cacheEntries,
            possible=possible,accept=probabilityMode and accept or nil,completionFloor=probabilityMode and model.completionFloor or nil,
            equivalentReasons=equivalentReasons})
    local feasible=result~=original;local path
    if feasible then
        path={}
        for _,a in ipairs(actions(result,tick)) do
            local key=rebatchKey(a);local previous=path[#path]
            if previous and previous.key==key and previous.reason==a.reason then previous.count=previous.count+a.count
            else path[#path+1]={index=indexes[key],key=key,reason=a.reason,count=a.count} end
            checkpoint()
        end
    end
    stats.finished=true;stats.feasible=feasible;stats.progress=1;stats.pending=0
    if report then report(stats) end
    return feasible,path,stats
end

function S.BatchRiskFeasible(model,tick,report)
    if not R or type(model.completionFloor)~="number" or model.completionFloor~=model.completionFloor
        or model.completionFloor<0 or model.completionFloor==math.huge then return nil,nil,{reason="invalid_completion_floor"} end
    local projection=copyStateMap(model)
    projection.probabilityMode=true;projection.optimisticSkill=true;projection.greenLimit=nil
    projection.progress=0;projection.targetProgress=0
    if model.relaxRanks then
        projection.rows={};projection.actions={}
        for _,row in ipairs(model.rows or {}) do
            local copy=copyStateMap(row);copy.reason="level";projection.rows[#projection.rows+1]=copy;if tick then tick() end
        end
        for _,action in ipairs(model.actions or {}) do
            local copy=copyStateMap(action);copy.reason="level";projection.actions[#projection.actions+1]=copy;if tick then tick() end
        end
    end
    local feasible,path,stats=S.BatchTaskFeasible(projection,tick,report)
    if model.relaxRanks then for _,entry in ipairs(path or {}) do entry.reason=nil;if tick then tick() end end end
    return feasible,path,stats
end

function S.BatchModel(original,initialState,recipes,progressGoals,tick,preserveGreen)
    local model={rows={},inventory={},actions={},optimisticSkill=preserveGreen and original.risk and true or nil}
    local byKey,profession,reasons={},nil,{}
    local lastKey
    for item,count in pairs(initialState.inv or {}) do model.inventory[item]=count-(initialState.unusable[item] or 0) end
    for _,a in ipairs(actions(original,tick)) do
        if a.type=="craft" then
            local key=rebatchKey(a);local r=recipes and recipes[key]
            if not r or not r.learn or not r.grey or type(r.mats)~="table"
                or profession and profession~=a.profession then return end
            profession=a.profession
            if type(a.count)~="number" or a.count<1 or a.count~=floor(a.count) then return end
            local row=byKey[key]
            if not row then
                row={key=key,learn=r.learn,yellow=r.yellow,green=r.green,grey=r.grey,item=r.item,
                    output=r.count or 0,mats=r.mats,count=0,reason=a.reason,preferredCounts={}}
                for _,m in ipairs(r.mats) do
                    if type(m[2])~="number" or m[2]<=0 or m[1]==r.item then return end
                end
                model.rows[#model.rows+1]=row;byKey[key]=row;reasons[key]={}
            end
            row.count=row.count+a.count
            model.actions[#model.actions+1]={type="craft",profession=a.profession,spell=a.spell,reason=a.reason,count=a.count}
            if lastKey==key then row.preferredCounts[#row.preferredCounts]=row.preferredCounts[#row.preferredCounts]+a.count
            else row.preferredCounts[#row.preferredCounts+1]=a.count;lastKey=key end
            reasons[key][(a.reason=="level" or a.reason=="secondary") and "level" or "material"]=true
        elseif a.type=="buy" then model.inventory[a.item]=(model.inventory[a.item] or 0)+a.count
        elseif a.type~="seed" and a.type~="formula" and a.type~="tool_goal" then return end
        if tick then tick() end
    end
    if not profession or not initialState.skill[profession] then return end
    model.skill=initialState.skill[profession];model.progress=initialState.progress[profession] or 0
    model.cap=initialState.cap[profession] or 300
    for _,row in ipairs(model.rows) do
        local kinds=reasons[row.key];local count=0;for _ in pairs(kinds) do count=count+1 end
        row.ignoreGreen=count>1
        if count>1 then
            local cap=model.cap
            if model.skill<=cap then while cap<row.learn and cap<300 do cap=cap<=75 and 150 or cap<=150 and 225 or 300 end end
            if row.grey>cap then model.exactReasons=true end
        end
        if tick then tick() end
    end
    local skill=original.skill[profession];local goal=progressGoals and progressGoals[profession] or 300
    model.profession=profession;model.goal=goal
    model.target=min(skill,goal);model.targetProgress=skill<goal and (original.progress[profession] or 0) or 0
    model.greenTarget=progressGoals and progressGoals[profession]
    if model.optimisticSkill then
        local risk=ns.ProfRisk and ns.ProfRisk.Score and ns.ProfRisk.Score(original.risk)
        model.target=risk and risk.completionProbability>0 and model.greenTarget or 1
        model.goal=model.target;model.progress=0;model.targetProgress=0
    elseif preserveGreen then model.greenLimit=min(original.greenLevelCrafts or 0,original.rebatchGreenCrafts or math.huge) end
    model.limit=rebatchSwitches(actions(original,tick))
    return model
end

function S.ReplayBatchHint(original,initialState,path,advance,tick,progressGoals,preserveGreen)
    local groups,events,done={},{},{}
    for _,a in ipairs(actions(original,tick)) do
        local key=rebatchKey(a)
        if key then
            groups[key]=groups[key] or {index=1}
            groups[key][#groups[key]+1]={action=a,left=a.count}
        elseif a.type~="seed" then events[#events+1]=a end
        if tick then tick() end
    end
    local current=initialState
    local function settle(owner)
        local changed=true
        while changed do
            changed=false
            for i,a in ipairs(events) do
                if not done[i] then
                    if a.type=="formula" and a.formula and current.formulaPaid[a.formula.id or a.owner] then
                        done[i]=true;changed=true
                    elseif (a.type~="formula" or a.owner==owner) and (a.type~="tool_goal" or not owner) then
                        local nextState=advance(current,a)
                        if nextState then current=nextState;done[i]=true;changed=true end
                    end
                end
                if tick then tick() end
            end
        end
    end
    for _,entry in ipairs(path or {}) do
        local group=groups[entry.key];local count=entry.count
        if not group or type(count)~="number" or count<1 or count~=floor(count) then return end
        settle(entry.key)
        while count>0 do
            local index=group.index
            if entry.reason~=nil then
                while group[index] and (group[index].left==0 or group[index].action.reason~=entry.reason) do index=index+1 end
            end
            local quota=group[index]
            if not quota then return end
            local n=min(count,quota.left);local action=E.Copy(quota.action);action.count=n
            current=advance(current,action);if not current then return end
            count=count-n;quota.left=quota.left-n
            while group[group.index] and group[group.index].left==0 do group.index=group.index+1 end
            if tick then tick() end
        end
    end
    settle()
    for i in ipairs(events) do if not done[i] then return end end
    for _,group in pairs(groups) do if group[group.index] then return end end
    if rebatchEquivalent(original,current,progressGoals,preserveGreen,true) then return current end
end

function S.ScheduleBatches(original,initialState,advance,tick,progressGoals,preserveGreen,onProgress,options)
    if not original or not initialState or type(advance)~="function" then return original end
    local requirements=options and options.requirements or original
    local function accepted(state)
        if options and options.accept then return options.accept(requirements,state) end
        return rebatchEquivalent(requirements,state,progressGoals,preserveGreen,true)
    end
    local completed,work=0,0
    local stats={states=0,transitions=0,pruned=0,skillPruned=0,greenPruned=0,cacheRotations=0,pending=1}
    local cacheLimit=options and tonumber(options.cacheEntries) or 50000
    if not cacheLimit or cacheLimit~=cacheLimit or cacheLimit==math.huge then cacheLimit=50000 end
    cacheLimit=max(1,floor(cacheLimit))
    local function report(value)
        if value then completed=max(completed,min(1,value)) end
        if onProgress then onProgress(completed,stats) end
    end
    local function checkpoint()
        work=work+1
        if tick then tick() end
        if work%64==0 then report() end
    end
    local encoded=setmetatable({},{__mode="k"})
    local interned,nextContent={},0
    local identities=setmetatable({},{__mode="k"});local nextIdentity=0
    local function encode(value,visiting)
        local kind=type(value)
        if kind=="nil" then return "z" end
        if kind=="number" then return "n"..string.format("%.17g",value)..";" end
        if kind=="string" then return "s"..#value..":"..value end
        if kind=="boolean" then return value and "t" or "f" end
        if kind~="table" then return kind..":"..tostring(value)..";" end
        if encoded[value] then return encoded[value] end
        visiting=visiting or {}
        if visiting[value] then
            if not identities[value] then nextIdentity=nextIdentity+1;identities[value]=nextIdentity end
            return "r"..identities[value]..";"
        end
        visiting[value]=true
        local entries={}
        for key,item in pairs(value) do
            entries[#entries+1]={encode(key,visiting),item};checkpoint()
        end
        table.sort(entries,function(a,b) return a[1]<b[1] end)
        local out={"{"}
        for _,entry in ipairs(entries) do out[#out+1]=entry[1];out[#out+1]=encode(entry[2],visiting);checkpoint() end
        out[#out+1]="}";visiting[value]=nil
        local content=table.concat(out);local id=interned[content]
        if not id then nextContent=nextContent+1;id=nextContent;interned[content]=id end
        local result="T"..id..";";encoded[value]=result
        return result
    end
    local list=actions(original,tick)
    local tasks,byTask,made,recipes={},{},{},{}
    local equivalentReasons=options and options.equivalentReasons or {}
    local distinct,previousTask=0,nil
    for actionIndex,a in ipairs(list) do
        for _,m in ipairs(a.outputs or {}) do made[m[1]]=true end
        if a.type=="craft" and a.item then made[a.item]=true end
        local key=rebatchKey(a)
        if key and not recipes[key] then recipes[key]=true;distinct=distinct+1 end
        if a.type~="seed" then
            local unit=E.Copy(a);local count,identity=1,nil
            if key then
                count=a.count
                unit.count=1;unit.from=nil;unit.to=nil;unit.fromProgress=nil;unit.toProgress=nil
                unit.expectedGain=nil;unit.outputCount=nil;unit.inputs=nil;unit.outputs=nil
                identity="craft"..encode(a.profession)..encode(a.spell)..encode(a.reason)
            elseif a.type=="buy" then
                local bundle=a.bundleSize or 1
                count=a.count/bundle
                unit.count=bundle;unit.cost=a.bundlePrice or a.cost/count
                unit.bundleSize=bundle;unit.bundlePrice=unit.cost
                identity="buy"..encode(unit)
            elseif a.type=="convert" then
                count=a.count;unit.count=1;unit.from=nil;unit.to=nil
                unit.outputCount=nil;unit.inputs=nil;unit.outputs=nil
                identity="convert"..encode(unit)
            end
            if type(count)~="number" or count<1 or count~=floor(count) then return original end
            local task=identity and byTask[identity]
            if task then task.count=task.count+count
            else
                task={action=unit,count=count,key=key,chunks={}};tasks[#tasks+1]=task
                if identity then byTask[identity]=task end
            end
            if previousTask==task then task.chunks[#task.chunks].cumulativeCount=task.count
            else task.chunks[#task.chunks+1]={cumulativeCount=task.count,actionIndex=actionIndex} end
            previousTask=task
        end
        checkpoint()
    end
    byTask=nil
    local best,bestScore=original,distinct>0 and rebatchSwitches(list)+1 or 0
    if options and options.incumbent and accepted(options.incumbent) then
        local score=distinct>0 and rebatchSwitches(actions(options.incumbent,tick))+1 or 0
        if score<bestScore then best,bestScore=options.incumbent,score end
    end
    if options and type(options.segmentLimit)=="number" and options.segmentLimit>=0
        and options.segmentLimit==floor(options.segmentLimit) and options.segmentLimit<math.huge then bestScore=options.segmentLimit+1 end
    stats.bestSegments=bestScore;stats.lowerBound=distinct
    if bestScore<=distinct then stats.pending=0;report(1);return best end
    local start=initialState
    local remaining={}
    for i,task in ipairs(tasks) do
        remaining[i]=task.count
        local a=task.action
        if options and options.prebuy and a.type=="buy" and (not made[a.item]
            or (original.inv[a.item] or 0)==0 and (original.unusable[a.item] or 0)==0) then
            local purchase=E.Copy(a);purchase.count=a.count*task.count;purchase.cost=a.cost*task.count
            local state=advance(start,purchase)
            stats.transitions=stats.transitions+1
            if state then start=state;remaining[i]=0 end
        end
        checkpoint()
    end
    local function stateKey(frame,keys)
        local lastTask=frame.lastTask
        if lastTask and frame.remaining[lastTask]==0 then lastTask=nil end
        local out={encode(keys[frame.lastKey] and frame.lastKey or nil),encode(lastTask),encode(frame.remaining)}
        local state={}
        for key,value in pairs(frame.state) do
            if key~="log" and key~="switches" and key~="batched"
                and not (options and options.ignoreStateFields and options.ignoreStateFields[key])
                and not ((frame.state.risk or preserveGreen==false) and (key=="greenLevelCrafts" or key=="rebatchGreenCrafts")) then
                state[key]=key=="risk" and R.Key(value) or value
            end
            checkpoint()
        end
        out[#out+1]=encode(state)
        return table.concat(out)
    end
    local function greenPossible(state)
        if options and options.completionFloor then
            return state.risk and R.Upper(state.risk)>=options.completionFloor*(1-1e-12)
        end
        if preserveGreen~=false and requirements.risk then
            return state.risk and R.Upper(state.risk)+1e-12>=R.Score(requirements.risk).completionProbability
        end
        return preserveGreen==false or (state.greenLevelCrafts or 0)<=(original.greenLevelCrafts or 0)
            and (original.rebatchGreenCrafts==nil or (state.rebatchGreenCrafts or 0)<=original.rebatchGreenCrafts)
    end
    local skillRecipes=options and options.recipes
    local skillTargets={}
    for profession,skill in pairs(requirements.skill or {}) do
        local goal=progressGoals and progressGoals[profession] or 300
        skillTargets[profession]=min(skill,goal)+(skill<goal and (requirements.progress and requirements.progress[profession] or 0) or 0)
    end
    local function skillPossible(state,left,changed,used)
        if not skillRecipes then return true end
        local upper,nextLearn,blocked={},{},{}
        for profession,skill in pairs(state.skill or {}) do
            upper[profession]=state.risk and R.SupportedSkill(state.risk,profession) or skill+(state.progress and state.progress[profession] or 0);checkpoint()
        end
        for i,task in ipairs(tasks) do
            local count=left[i]-(i==changed and used or 0)
            if count>0 then
                local a=task.action;local profession=a.profession
                if task.key then
                    local r=skillRecipes[task.key];local skill=state.risk and R.SupportedSkill(state.risk,profession) or state.skill and state.skill[profession]
                    if not r or type(r.learn)~="number" or type(r.grey)~="number" or not skill then blocked[profession]=true
                    elseif r.learn>skill then nextLearn[profession]=min(nextLearn[profession] or math.huge,r.learn)
                    else upper[profession]=upper[profession]+count*(state.risk and 1 or E.Gain(r,skill)+.000001) end
                elseif a.type=="gather" then
                    if not profession then return true end
                    blocked[profession]=true
                elseif a.type~="buy" and a.type~="formula" and a.type~="tool_goal"
                    and a.type~="specialization_quest" and a.type~="convert" then return true end
            end
            checkpoint()
        end
        for profession,maximum in pairs(upper) do
            if not blocked[profession] then
                local target=nextLearn[profession];local required
                if state.risk then required=progressGoals and progressGoals[profession] else required=skillTargets[profession] end
                if state.risk and (options and options.completionFloor or requirements.risk and R.Completion(requirements.risk) or 0)<=0 then required=nil end
                local current=state.risk and R.SupportedSkill(state.risk,profession) or state.skill[profession]+(state.progress and state.progress[profession] or 0)
                if required and required>current+1e-7 then target=min(target or math.huge,required) end
                if target and maximum+1e-7<target then return false end
            end
            checkpoint()
        end
        return true
    end
    local memo,memoEntries={},0
    local stack={{state=start,remaining=remaining,score=0,weight=1}}
    local function close(frame)
        table.remove(stack);report(completed+frame.weight)
    end
    while #stack>0 do
        checkpoint()
        if bestScore==distinct then stats.pending=0;report(1);return best end
        local frame=stack[#stack]
        if not frame.children then
            stats.states=stats.states+1;stats.pending=stats.pending-1
            if options and options.completed then
                for i,task in ipairs(tasks) do
                    if frame.remaining[i]>0 and options.completed(frame.state,task.action) then frame.remaining[i]=0 end
                    checkpoint()
                end
            end
            if options and options.eager then
                for i,task in ipairs(tasks) do
                    if frame.remaining[i]==1 then
                        local state=options.eager(frame.state,task.action)
                        if state then frame.state=state;frame.remaining[i]=0 end
                    end
                    checkpoint()
                end
            end
            local keys,n={},0
            local choices,activeReasons={},{}
            local left,events=0,0
            for i,count in ipairs(frame.remaining) do
                left=left+count
                local key=tasks[i].key
                if count>0 then
                    choices[i]=not key or not equivalentReasons[key] or not activeReasons[key]
                    if key then activeReasons[key]=true end
                end
                if count>0 and key then
                    if not keys[key] then keys[key]=0;n=n+1 end
                    keys[key]=keys[key]+count
                elseif count>0 then events=events+count end
                checkpoint()
            end
            local continuing=keys[frame.lastKey] and (events>0 or not frame.lastTask
                or tasks[frame.lastTask].key~=frame.lastKey or frame.remaining[frame.lastTask]==0
                or not equivalentReasons[frame.lastKey] and keys[frame.lastKey]>frame.remaining[frame.lastTask])
            local green=greenPossible(frame.state)
            if green and continuing and frame.score+n==bestScore then
                continuing=false;frame.first={}
                for i,task in ipairs(tasks) do
                    if choices[i] and i~=frame.lastTask and (not task.key or task.key==frame.lastKey) then
                        local state=advance(frame.state,task.action);stats.transitions=stats.transitions+1
                        if state and not greenPossible(state) then state=nil;stats.greenPruned=stats.greenPruned+1 end
                        frame.first[i]=state or false;checkpoint()
                        if state then continuing=true;break end
                    end
                    checkpoint()
                end
            end
            if not green or frame.score+n-(continuing and 1 or 0)>=bestScore then
                if not green then stats.greenPruned=stats.greenPruned+1 end
                stats.pruned=stats.pruned+1;close(frame)
            elseif left==0 then
                if accepted(frame.state) then
                    best,bestScore=frame.state,frame.score;stats.bestSegments=bestScore
                    if options and options.firstFeasible then stats.pending=0;report(1);return best end
                end
                close(frame)
            else
                if nextContent>=cacheLimit or memoEntries>=cacheLimit then
                    memo={};memoEntries=0;encoded=setmetatable({},{__mode="k"})
                    interned={};nextContent=0;identities=setmetatable({},{__mode="k"});nextIdentity=0
                    stats.cacheRotations=stats.cacheRotations+1
                end
                local key=stateKey(frame,keys)
                if memo[key] and memo[key]<=frame.score then stats.pruned=stats.pruned+1;close(frame)
                else
                    if memo[key]==nil then memoEntries=memoEntries+1 end
                    memo[key]=frame.score
                    local possible=not options or not options.possible or options.possible(frame.state,frame.remaining,tasks,bestScore-1-frame.score,frame.lastKey)
                    if possible==false then stats.pruned=stats.pruned+1;close(frame)
                    else
                    local children,taskOrder={},tasks
                    if options and options.firstFeasible then
                        local priority={};taskOrder={}
                        for i,task in ipairs(tasks) do
                            taskOrder[i]=i
                            local done=task.count-frame.remaining[i]
                            priority[i]=math.huge
                            for _,chunk in ipairs(task.chunks) do
                                if chunk.cumulativeCount>done then priority[i]=chunk.actionIndex;break end
                                checkpoint()
                            end
                            checkpoint()
                        end
                        table.sort(taskOrder,function(a,b) return priority[a]<priority[b] or priority[a]==priority[b] and a<b end)
                    end
                    for position,entry in ipairs(taskOrder) do
                        local i=options and options.firstFeasible and entry or position
                        local task=tasks[i]
                        local score=frame.score+(task.key and task.key~=frame.lastKey and 1 or 0)
                        if choices[i] and i~=frame.lastTask and (not task.key or score+n-1<bestScore) then
                            local state=frame.state;local batch,byCount={},options and options.firstFeasible and {} or nil
                            local lastKey=task.key or frame.lastKey
                            for count=1,frame.remaining[i] do
                                if count==1 and frame.first and frame.first[i]~=nil then state=frame.first[i] or nil
                                else state=advance(state,task.action);stats.transitions=stats.transitions+1 end
                                checkpoint()
                                if not state then break end
                                if not greenPossible(state) then
                                    stats.pruned=stats.pruned+1;stats.greenPruned=stats.greenPruned+1;break
                                end
                                local keyLeft=(keys[lastKey] or 0)-(task.key==lastKey and count or 0)
                                local continuing=keyLeft>0 and (not task.key or events>0
                                    or (not equivalentReasons[lastKey] or count==frame.remaining[i]) and keys[lastKey]>frame.remaining[i])
                                local lower=score+n-(task.key and keys[task.key]==count and 1 or 0)-(continuing and 1 or 0)
                                if lower<bestScore and skillPossible(state,frame.remaining,i,count) then
                                    local nextRemaining={}
                                    for index,value in ipairs(frame.remaining) do nextRemaining[index]=value;checkpoint() end
                                    nextRemaining[i]=nextRemaining[i]-count
                                    local child={state=state,remaining=nextRemaining,score=score,lastKey=lastKey,lastTask=i}
                                    batch[#batch+1]=child;if byCount then byCount[count]=child end
                                else
                                    stats.pruned=stats.pruned+1
                                    if lower<bestScore then stats.skillPruned=stats.skillPruned+1 end
                                end
                            end
                            if options and options.firstFeasible then
                                local emitted={}
                                local function emit(child)
                                    if child and not emitted[child] then emitted[child]=true;children[#children+1]=child end
                                end
                                local done=task.count-frame.remaining[i]
                                for _,chunk in ipairs(task.chunks) do
                                    if chunk.cumulativeCount>done then emit(byCount[chunk.cumulativeCount-done]);break end
                                    checkpoint()
                                end
                                local previous=0
                                for _,chunk in ipairs(task.chunks) do
                                    emit(byCount[chunk.cumulativeCount-previous]);previous=chunk.cumulativeCount;checkpoint()
                                end
                                for index=#batch,1,-1 do emit(batch[index]);checkpoint() end
                            else for index=#batch,1,-1 do children[#children+1]=batch[index];checkpoint() end end
                        elseif choices[i] and i~=frame.lastTask then stats.pruned=stats.pruned+frame.remaining[i] end
                        checkpoint()
                    end
                    if #children==0 then close(frame)
                    else
                        frame.children=children;frame.index=0;frame.childWeight=frame.weight/#children
                        stats.pending=stats.pending+#children
                    end
                    end
                end
            end
        elseif frame.index<#frame.children then
            frame.index=frame.index+1
            local child=frame.children[frame.index];child.weight=frame.childWeight
            frame.children[frame.index]=false
            stack[#stack+1]=child
        else table.remove(stack) end
    end
    stats.pending=0;report(1)
    return best
end

function S.NewJob(slug,opts)
    opts=opts or {}
    local j={slug=slug,opts=opts,target=min(300,max(1,floor(opts.target or (ns.ProfModule and ns.ProfModule.LV_DEF) or 300))),expanded=0,failures={},cpuUsed=0,cpuLimitMs=max(1,tonumber(opts.cpuLimitMs) or 8000),status="searching",generation=0,progressVersion=0,resultVersion=0,frontierLimit=max(1,floor(tonumber(opts.maxFrontier) or 20000))}
    j.phase, j.phaseCpuMs = "capture", {}
    j.seedLeafPrices = {}
    j.workCounters = {fastSeedPurchases=0,fastSeedCrafts=0,seedCraftComparisons=0,
        seedCandidateTrials=0,leafQuoteHits=0,seedQuoteCalls=0,
        batchedPlans=0,batchReuses=0,replayCalls=0}
    local stable=opts.scheme=="stable"
    local function better(a,b)
        if stable and b and a.risk and b.risk and (uncertainty(a)==0)==(uncertainty(b)==0) then
            local risk=R.Compare(a.risk,b.risk);if risk~=0 then return risk<0 end
        end
        return betterState(a,b,j.recovery and j.snap or nil)
    end
    local function countGreen(state,recipe,reason,gain)
        if stable and gain>0 and (reason=="level" or reason=="secondary")
            and state.skill[recipe.profession]>=recipe.green
            and (recipe.profession~=slug or state.skill[recipe.profession]<j.target) then
            state.greenLevelCrafts=state.greenLevelCrafts+1
        end
    end
    local ops=0
    local function cpuTime()
        return j.cpuUsed+(j.sliceStart and max(0,clock()-j.sliceStart) or 0)
    end
    local function tick()
        ops=ops+1
        if j.seedWorkRemaining then
            j.seedWorkRemaining=j.seedWorkRemaining-1
            if j.seedWorkRemaining<=0 then j.seedAborted=true end
        end
        if j.tickClockStride then
            j.tickClockCountdown=(j.tickClockCountdown or 0)-1
            if j.tickClockCountdown>0 and ops<1000 then return end
            j.tickClockCountdown=j.tickClockStride
            local now=clock()
            if j.seedDeadline and j.cpuUsed+max(0,now-(j.sliceStart or now))>=j.seedDeadline then j.seedAborted=true end
            if ops>=1000 or (j.deadline and now>=j.deadline) then ops=0;coroutine.yield("work") end
            return
        end
        if j.seedDeadline and cpuTime()>=j.seedDeadline then j.seedAborted=true end
        if ops>=1000 or (j.deadline and clock()>=j.deadline) then ops=0; coroutine.yield("work") end
    end
    j.tick=tick
    local levelIndex={}
    j.candidateIndex=levelIndex
    local function levelRecipes(profession,skill)
        local index=levelIndex[profession]
        if not index then
            local boundaries,seen={1},{[1]=true}
            for _,recipe in ipairs(j.snap.byProfession[profession] or {}) do
                for _,value in ipairs({ceil(recipe.learn),ceil(recipe.grey)}) do
                    if value>1 and value<=300 and not seen[value] then
                        seen[value]=true;boundaries[#boundaries+1]=value
                    end
                end
                tick()
            end
            table.sort(boundaries)
            index={boundaries=boundaries,lists={}};levelIndex[profession]=index
        end
        local low,high=1,#index.boundaries
        while low<high do
            local middle=floor((low+high+1)/2)
            if index.boundaries[middle]<=skill then low=middle else high=middle-1 end
        end
        if index.lists[low] then return index.lists[low] end
        local candidates={}
        for _,recipe in ipairs(j.snap.byProfession[profession] or {}) do
            if recipe.learn<=skill and skill<recipe.grey then candidates[#candidates+1]=recipe end
            tick()
        end
        index.lists[low]=candidates
        return candidates
    end
    local function fail(code,r,id,required,availableCount,learning)
        local key=code..":"..tostring(r and r.key or "")..":"..tostring(id or "")
        if code=="learningDataMissing" and j.failures[key] then
            if j.collectFailures then j.collectFailures[key]=j.failures[key] end
            return
        end
        j.failures[key]={code=code,recipe=r and r.key,item=id,spell=r and r.spell,profession=r and r.profession,
            required=required,available=availableCount}
        if learning then
            local route=ns.ProfRouteAuto
            local d=route and route.LearningDiagnostic and route.LearningDiagnostic(code,r,learning)
                or {code=code,recipe=r and r.key,spell=r and r.spell,profession=r and r.profession,
                    item=r and (r.formula or r.formulaID),coverage=learning.coverage,
                    routeId=learning.routeId,missingReasons=E.Copy(learning.missingReasons or {}),learningStatus=learning.status}
            for k,v in pairs(d) do j.failures[key][k]=v end
            if code=="learningDataMissing" or code=="learningRequirementsUnknown"
                or type(learning.missingReasons)=="table" and #learning.missingReasons>0 then
                j.learningGaps=j.learningGaps or {}
                local identity=r and r.key or key
                if not j.learningGaps[identity] then j.learningGapRevision=(j.learningGapRevision or 0)+1 end
                j.learningGaps[identity]=d
            end
        end
        if j.collectFailures then j.collectFailures[key]=j.failures[key] end
    end
    local acquire,craft,levelTo
    local function bound(s)
        if j.recovery then return objective(s,j.snap) end
        local credit=0
        for id,n in pairs(s.inv) do credit=credit+(j.values and j.values[id] or 0)*n end
        local remaining=max(0,j.target-(s.skill[slug] or 1)-(s.progress[slug] or 0))
        return s.money+max(0,(j.pointBound or 0)*remaining-credit)
    end
    local function pruned(s,complete)
        if j.batchRecipes then return false end
        if j.recovery then return false end
        if not j.best then return false end
        if uncertainty(j.best)>0 then return false end
        if uncertainty(s)>0 then return true end
        if stable and s.risk and j.best.risk then
            return R.Upper(s.risk)+1e-12<R.Score(j.best.risk).completionProbability
        end
        local lower=complete and bound(s) or s.money
        return lower>j.best.money+1e-7 or (math.abs(lower-j.best.money)<1e-7 and (s.switches or 0)>=(j.best.switches or 0))
    end
    local function supportedState(s)
        if not s.risk then return s end
        local t=clone(s)
        for p in pairs(t.skill) do t.skill[p]=R.SupportedSkill(s.risk,p) end
        return t
    end
    local function allowed(r,s,reason,probabilityGate)
        if probabilityGate then s=supportedState(s) end
        if slug~="__purchase" and r.profession~=slug and not opts.allowSecondaryLeveling then
            fail("secondaryDisabled",r);return false
        end
        local p=E.Policy(j.opts.exclusions,r)
        if p=="ban" or (p=="level" and reason~="material") then fail("excluded",r,r.item); return false end
        local skill=s.skill[r.profession]
        if not skill then fail("professionMissing",r);return false end
        if skill<r.learn and (r.profession==slug or not opts.allowSecondaryLeveling) then
            fail("skillRequired",r);return false
        end
        local eligibility=E.RouteRecipeEligibility or E.RecipeSpecializationAllowed
        local learning
        if eligibility then
            local ok,why,detail=eligibility(r,j.snap,s)
            if not ok then fail(why or "specializationRequired",r,nil,nil,nil,detail);return false end
            learning=detail
        end
        local formula=learning and learning.quote or j.formulaByRecipe and j.formulaByRecipe[r.key]
        if formula and not formula.usable then fail(formula.reason or "formulaUnavailable",r,formula.id);return false end
        if r.clientUnavailable then fail("clientUnavailable",r,r.item); return false end
        if r.clientPending then fail("clientDataPending",r,r.item); return false end
        if r.cooldown or r.cooldownUnknown then fail(r.cooldown and "cooldown" or "cooldownUnknown",r); return false end
        if r.outputConflict then fail("outputConflict",r,r.item); return false end
        if (r.availabilityUnknown or r.verified==false) and not r.clientAvailable then if not s.learned[r.key] and not s.learned[r.spell] then fail("availabilityUnknown",r); return false end end
        return true,learning
    end
    local function vendorQuote(o)
        return o.unlimited==true and type(o.price)=="number" and o.price>=0
            and o.available~=false and o.purchasable~=false and not o.hasExtendedCost
            and (not o.currencyID or o.currencyID==0)
            and (not o.faction or not j.snap.faction or o.faction==j.snap.faction or o.faction=="Neutral" or o.faction=="N")
    end
    local vendorChoices={}
    local function materialVendorOffers(id)
        if vendorChoices[id] then return vendorChoices[id] end
        local out,byPack={},{}
        for _,offer in ipairs(E.PreferredVendorOffers(j.snap.offers[id],vendorQuote)) do
            if vendorQuote(offer) then
                local size=offer.quantity or offer.bundleSize or 1
                local key=tostring(size)..":"..tostring(offer.estimated and not offer.reference or false)
                local index=byPack[key]
                if not index then out[#out+1]=offer;byPack[key]=#out
                elseif offer.price<out[index].price then out[index]=offer end
            end
            tick()
        end
        vendorChoices[id]=out
        return out
    end
    local function auctionQuote(id)
        local price=j.snap.prices[id]
        return not j.snap.nonAuctionable[id]
            and type(price)=="number" and price>0
    end
    local function auctionRemaining(s,id)
        local supply=j.auctionSupply[id]
        return supply and max(0,supply.quantity-(s.ahUsed[id] or 0)) or math.huge
    end
    local function essenceConversion(id)
        return j.snap.essenceConversions and ns.ProfEssences and ns.ProfEssences.ForItem(id)
    end
    local function convert(s,c,n,owner)
        if not c or n<1 or n~=floor(n) or available(s,c.inputItemID)<c.inputCount*n then return end
        local t=clone(s)
        consume(t,c.inputItemID,c.inputCount*n)
        t.inv[c.outputItemID]=(t.inv[c.outputItemID] or 0)+c.outputCount*n
        local skill=t.skill.enchanting or t.skill[slug] or 1
        log(t,{type="convert",profession="enchanting",count=n,from=skill,to=skill,
            item=c.outputItemID,outputCount=c.outputCount*n,inputs={{c.inputItemID,c.inputCount*n}},
            outputs={{c.outputItemID,c.outputCount*n}},conversion=E.Copy(c),manual=true,essence=true,
            reason="essence",owner=owner,usableOutput=true})
        return t
    end
    local function output(s,r,n)
        local eligible=n
        if j.recovery and j.profitRecipes[r.key] then
            local cap=ns.ProfRecovery.PROFIT_CAP
            local made=s.profitMade[r.key] or 0
            eligible=min(n,max(0,cap-made));s.profitMade[r.key]=min(cap,made+n)
        end
        if not r.item then return true end
        local count=r.count*n
        s.inv[r.item]=(s.inv[r.item] or 0)+count
        s.produced[r.item]=(s.produced[r.item] or 0)+count
        s.priorityProduced[r.item]=(s.priorityProduced[r.item] or 0)+r.count*eligible
        local materialProfession=opts.materialProfession or slug
        local usable=r.profession==materialProfession or materialProfession=="__purchase" or j.purchasePriced[r.item]
        if not usable then s.unusable[r.item]=(s.unusable[r.item] or 0)+count end
        return usable and true or false
    end
    local function buy(s,id,qty,source,price,bundle,npc,reason,url,estimated,owner,unpriced,offer)
        local t=clone(s); local count=ceil(qty/bundle)*bundle; local cost=ceil(qty/bundle)*price
        if source=="ah" and j.auctionSupply[id] then
            if count>auctionRemaining(s,id) then fail("auctionSupplyLimited",nil,id,count,auctionRemaining(s,id));return end
            t.ahUsed[id]=(t.ahUsed[id] or 0)+count
        end
        t.inv[id]=(t.inv[id] or 0)+count; t.money=t.money+cost
        log(t,stampStock({type="buy",item=id,count=count,cost=cost,source=source,npcID=npc,reason=reason,url=url,bundleSize=bundle,bundlePrice=price,owner=owner,unpriced=unpriced,estimated=estimated,reference=offer and offer.reference,quoteSource=offer and offer.source,priceSource=offer and offer.priceSource,priceBasis=offer and offer.priceBasis,verifiedAt=offer and offer.verifiedAt},offer))
        if estimated and not (offer and offer.reference) then diagnostic(t,"vendor:"..id..":"..tostring(npc),"vendorEstimate",id) end
        if unpriced then diagnostic(t,source..":"..id,source=="vendor" and "vendorPriceUnknown" or "materialPriceUnknown",id) end
        return t
    end
    local function fastSeedOffer(s, id, missing)
        local auctionPrice = auctionQuote(id) and j.snap.prices[id] or nil
        local ahRemaining = auctionPrice and auctionRemaining(s, id) or 0
        local best
        local function consider(cost, uncertain, ah, offer, vendorQty, waste)
            if not best or (best.uncertain and not uncertain)
                or (best.uncertain == uncertain and (cost < best.cost - 1e-7
                    or (math.abs(cost - best.cost) < 1e-7 and waste < best.waste))) then
                best = {cost=cost, uncertain=uncertain, ah=ah, offer=offer,
                    vendorQty=vendorQty, waste=waste}
            end
        end
        if auctionPrice and ahRemaining >= missing then
            consider(missing * auctionPrice, false, missing, nil, 0, 0)
        end
        for _, offer in ipairs(materialVendorOffers(id)) do
            if vendorQuote(offer) then
                local size = offer.quantity or offer.bundleSize or 1
                local price = offer.price
                local uncertain = offer.estimated and not offer.reference and true or false
                if type(size)=="number" and size>=1 and size==floor(size)
                    and type(price)=="number" and price>=0 then
                    local packs = ceil(missing / size)
                    consider(packs * price, uncertain, 0, offer,
                        packs * size, packs * size - missing)
                    if auctionPrice and ahRemaining > 0 then
                        local ah = min(missing, ahRemaining)
                        local remainder = missing - ah
                        if remainder > 0 then
                            local n = ceil(remainder / size) * size
                            consider(ah * auctionPrice + n / size * price,
                                uncertain, ah, offer, n, ah + n - missing)
                        end
                        local packs = ceil(max(0, missing - ahRemaining) / size)
                        if packs > 0 then
                            local n = packs * size
                            local onlyAH = max(0, missing - n)
                            if onlyAH > 0 and onlyAH <= ahRemaining then
                                consider(onlyAH * auctionPrice + packs * price,
                                    uncertain, onlyAH, offer, n, onlyAH + n - missing)
                            end
                        end
                        local partialPacks = ceil(missing / size) - 1
                        if partialPacks > 0 then
                            local n = partialPacks * size
                            local onlyAH = missing - n
                            if onlyAH <= ahRemaining then
                                consider(onlyAH * auctionPrice + partialPacks * price,
                                    uncertain, onlyAH, offer, n, 0)
                            end
                        end
                    end
                end
            end
        end
        return best, auctionPrice
    end
    local function fastSeedPurchase(s, id, missing, reason, path)
        if missing <= 0 then return s end
        local best, auctionPrice = fastSeedOffer(s, id, missing)
        if not best then return nil end
        local t = s
        if best.ah > 0 then
            t = buy(t, id, best.ah, "ah", auctionPrice, 1, nil,
                reason, nil, nil, path and path.owner)
            if not t then return nil end
        end
        if best.offer then
            local offer = best.offer
            local size = offer.quantity or offer.bundleSize or 1
            t = buy(t, id, best.vendorQty, "vendor", offer.price, size,
                offer.npcID, reason, offer.url, offer.estimated,
                path and path.owner, nil, offer)
        end
        if t and available(t, id) >= missing + available(s, id) then
            return t
        end
        return nil
    end
    local function seedMaterialQuote(s,id,need)
        local missing=max(0,need-available(s,id))
        if missing<=0 then return 0 end
        local potential=j.values and j.values[id]
        if potential and potential>0 then return potential*missing end
        local offer=fastSeedOffer(s,id,missing)
        return offer and offer.cost or math.huge
    end
    local function stateFormula(r,s,remaining,purchaseSource)
        if ns.IsForever and ns.ProfLearningSources and E.SelectLearningRoute then
            local ok,_,detail=E.SelectLearningRoute(r,j.snap,s,remaining,purchaseSource)
            return ok and detail and detail.quote or nil
        end
        return E.FormulaFor(r,j.snap,remaining,purchaseSource)
    end
    local function learnFormula(s,r,choice,selectedLearning)
        local ok,why,learning=true,nil,selectedLearning
        if not learning then ok,why,learning=(E.RouteRecipeEligibility or E.RecipeSpecializationAllowed)(r,j.snap,s) end
        if not ok then fail(why or "learningDataMissing",r,nil,nil,nil,learning);return end
        local f=learning and learning.quote or j.formulaByRecipe[r.key]
        if choice and (not f or not f.learningRouteId or choice.learningRouteId==f.learningRouteId) then f=choice end
        if not f or f.known then return s end
        if not f.usable then fail(f.reason or "formulaUnavailable",r,f.id);return end
        local key=f.id or r.key
        if s.formulaPaid[key] then return s end
        if f.source=="ah" and auctionRemaining(s,f.id)<1 then
            f=stateFormula(r,s,auctionRemaining(s,f.id))
            if not f or not f.usable then fail("auctionSupplyLimited",r,f and f.id);return end
        end
        local t=clone(s);t.formulaPaid[key]=true;t.money=t.money+(f.cost or 0)
        if f.automatic then return t end
        if f.source=="ah" and j.auctionSupply[f.id] then t.ahUsed[f.id]=(t.ahUsed[f.id] or 0)+1 end
        if f.unpriced then diagnostic(t,"formula:"..tostring(key),"formulaPriceUnknown",f.id or r.key) end
        if f.availabilityUncertain then diagnostic(t,"formulaStock:"..tostring(key),"formulaStockUnknown",f.id or r.key) end
        log(t,{type="formula",item=f.id,count=f.bundleSize or 1,cost=f.cost or 0,source=f.source,owner=r.key,unpriced=f.unpriced,formula=E.Copy(f)})
        return t
    end
    local function prepare(r,s,reason,path,emit,selectedLearning)
        local usable,learning=true,selectedLearning
        if not learning then usable,learning=allowed(r,s,reason) end
        if not usable then return end
        local skill=s.skill[r.profession]
        if not skill then fail("professionMissing",r); return end
        local learn=r.learn
        if skill<learn then
            if r.profession~=slug and opts.allowSecondaryLeveling and not path["level:"..r.profession] then
                local p=E.Copy(path); p["level:"..r.profession]=true
                levelTo(s,r.profession,learn,p,function(t) prepare(r,t,reason,p,emit) end)
            else fail("skillRequired",r) end
            return
        end
        if r.isNew and not (r.clientAvailable or r.catalogue or s.learned[r.key] or s.learned[r.spell] or r.formula or r.learnSource=="trainer" or (r.source and r.source.skill)) then
            fail("availabilityUnknown",r); return
        end
        local prepared=learnFormula(s,r,nil,learning)
        if prepared then emit(prepared,learning) end
        local f=learning and learning.quote or j.formulaByRecipe[r.key]
        if f and not f.known and f.source=="ah" and j.auctionSupply[f.id]
            and not s.formulaPaid[f.id or r.key] and auctionRemaining(s,f.id)>=1 then
            local alternative=stateFormula(r,s,0)
            if alternative and alternative.usable and alternative.source=="vendor" then
                local t=learnFormula(s,r,alternative,learning)
                if t then emit(t,learning) end
            end
        end
        if f and not f.known and f.source=="vendor" and f.availabilityUncertain
            and f.ahPrice and auctionRemaining(s,f.id)>=1 and not s.formulaPaid[f.id or r.key] then
            local alternative=stateFormula(r,s,auctionRemaining(s,f.id),"ah")
            if alternative and alternative.usable and alternative.source=="ah" then
                local t=learnFormula(s,r,alternative,learning)
                if t then emit(t,learning) end
            end
        end
    end
    local function rank(s,p)
        local cap=s.cap[p] or 300
        if (s.skill[p] or 1)<cap or cap>=300 then return s end
        local nextCap=cap<=75 and 150 or cap<=150 and 225 or 300
        local t=clone(s); t.cap[p]=nextCap
        return t
    end
    craft=function(s,r,n,reason,path,emit,learning)
        tick(); if j.seedAborted or pruned(s) then return end
        prepare(r,s,reason,path,function(base,selectedLearning)
            local function reagents(t,i)
                tick()
                if j.seedAborted then return end
                local m=r.mats[i]
                if m then
                    local inputPath=E.Copy(path); inputPath.owner=r.key
                    acquire(t,m[1],m[2]*n,"material",inputPath,function(u)
                        u=clone(u); consume(u,m[1],m[2]*n); reagents(u,i+1)
                    end)
                    return
                end
                t=clone(t)
                local p=r.profession; local from=t.skill[p]; local inputs={}
                local fromProgress=t.progress[p] or 0
                for _,mat in ipairs(r.mats) do inputs[#inputs+1]={mat[1],mat[2]*n} end
                for _=1,n do
                    local g=E.Gain(r,t.skill[p])
                    if g>0 and t.skill[p]>=(t.cap[p] or 300) then
                        if reason=="level" or reason=="secondary" then
                            t=rank(t,p); if not t then return end
                        else g=0 end
                    end
                    countGreen(t,r,reason,g)
                    local progress=(t.progress[p] or 0)+g
                    local gain=floor(progress+1e-7)
                    t.skill[p]=min(300,t.skill[p]+gain); t.progress[p]=floor((progress-gain)*1000000+.5)/1000000
                    tick()
                end
                local produced=r.item and r.count*n or 0
                local usableOutput=output(t,r,n)
                if p==slug and t.lastRecipe~=r.key then t.switches=t.switches+1; t.lastRecipe=r.key end
                log(t,{type="craft",profession=p,spell=r.spell,count=n,from=from,to=t.skill[p],item=r.item,outputCount=produced,outputs=r.item and {{r.item,produced}} or {},inputs=inputs,reason=reason,station=r.station,usableOutput=usableOutput,
                    fromProgress=fromProgress,toProgress=t.progress[p] or 0,
                    expectedGain=t.skill[p]-from+(t.progress[p] or 0)-fromProgress,learningRoute=selectedLearning and selectedLearning.route})
                if not pruned(t) then emit(t) end
            end
            reagents(base,1)
        end,learning)
    end
    acquire=function(s,id,need,reason,path,emit,used)
        tick()
        if j.seedAborted then return end
        if available(s,id)>=need then emit(s); return end
        if pruned(s) then return end
        path=path or {}; used=used or {}
        local missing=need-available(s,id)
        local producer=j.batchRecipes and j.batchRecipes[id]
        if producer and not path[id] then
            local pth=E.Copy(path);pth[id]=true
            craft(s,producer,ceil(missing/producer.count),"material",pth,function(t)
                if available(t,id)>=need then emit(t) end
            end)
            return
        end
        if opts.routeSkeleton then
            if path.forceCraftItem==id or j.snap.toolCraftOnlyItems[id] then
                fail("materialUnavailable",nil,id,missing);return
            end
            local demand=max(missing,(j.skeletonDemand[id] or 0)-(s.skeletonBought[id] or 0))
            local remaining=auctionRemaining(s,id)
            for key,item in pairs(j.skeletonFormulas) do
                if item==id and not s.formulaPaid[key] then remaining=max(0,remaining-1) end
            end
            local rows,_,complete=E.MaterialPurchases(id,demand,{offers=materialVendorOffers(id),
                auction=auctionQuote(id) and j.snap.prices[id] or nil,supply=j.auctionSupply[id],
                available=remaining,faction=j.snap.faction},tick)
            if not complete then
                fail(j.auctionSupply[id] and auctionRemaining(s,id)<demand and "auctionSupplyLimited"
                    or "materialUnavailable",nil,id,demand,auctionRemaining(s,id));return
            end
            local t=s
            for _,row in ipairs(rows) do
                t=buy(t,id,row.count,row.source,row.bundlePrice or row.unit,row.bundleSize or 1,
                    row.npcID,reason,row.url,row.estimated,path.owner,row.unpriced,
                    stampStock({reference=row.reference,source=row.quoteSource,priceSource=row.priceSource,
                        priceBasis=row.priceBasis,verifiedAt=row.verifiedAt},row))
                if not t then return end
            end
            t.skeletonBought[id]=(s.skeletonBought[id] or 0)+available(t,id)-available(s,id)
            emit(t);return
        end
        local finalEmit=emit; local localBest
        if j.seeding then emit=function(t) if better(t,localBest) then localBest=t end end end
        local price=j.snap.prices[id]
        local had=false
        local craftOnly=path.forceCraftItem==id or j.snap.toolCraftOnlyItems and j.snap.toolCraftOnlyItems[id]
        local auctionPriced=not craftOnly and auctionQuote(id)
        local remaining=auctionRemaining(s,id)
        if j.seeding and j.directSeed and not craftOnly then
            local warm=fastSeedPurchase(s,id,missing,reason,path)
            local selected=warm
            local ceiling=warm and warm.money-s.money or math.huge
            local uncertain=warm and uncertainty(warm)>uncertainty(s)
            if not path[id] then
                local pth=E.Copy(path);pth[id]=true
                local materialProfession=opts.materialProfession or slug
                local candidates={}
                for _,r in ipairs(j.snap.byItem[id] or {}) do
                    local own=path.ownProfessionOnly and r.profession==path.ownProfessionOnly
                        or not path.ownProfessionOnly and (j.purchasePriced[id]
                            or r.profession==materialProfession or materialProfession=="__purchase")
                    if own and not used[r.key] and type(r.count)=="number" and r.count>0 then
                        local n=ceil(missing/r.count)
                        local f=j.formulaByRecipe[r.key]
                        local estimate=f and not f.known and not s.formulaPaid[f.id or r.key] and (f.cost or 0) or 0
                        for _,m in ipairs(r.mats or {}) do
                            estimate=estimate+seedMaterialQuote(s,m[1],m[2]*n)
                            if estimate>=ceiling and not uncertain then break end
                        end
                        if estimate<ceiling-1e-7 or uncertain then
                            candidates[#candidates+1]={recipe=r,count=n,estimate=estimate}
                        end
                    end
                    tick()
                end
                table.sort(candidates,function(a,b)
                    if a.estimate~=b.estimate then return a.estimate<b.estimate end
                    return a.recipe.spell<b.recipe.spell
                end)
                local trials=0
                for _,candidate in ipairs(candidates) do
                    if j.seedAborted or trials>=3 then break end
                    if selected and not uncertain and candidate.estimate>=selected.money-s.money-1e-7 then break end
                    local r=candidate.recipe
                    local usable,learning=allowed(r,s,"material")
                    if usable then
                        local u=E.Copy(used);u[r.key]=true
                        trials=trials+1
                        j.workCounters.seedCraftComparisons=j.workCounters.seedCraftComparisons+1
                        craft(s,r,candidate.count,"material",pth,function(t)
                            if available(t,id)>=need and better(t,selected) then selected=t end
                        end,learning)
                    end
                    tick()
                end
            end
            if selected then
                if selected==warm then
                    j.workCounters.fastSeedPurchases=j.workCounters.fastSeedPurchases+1
                else
                    j.workCounters.fastSeedCrafts=j.workCounters.fastSeedCrafts+1
                end
                finalEmit(selected)
                return
            end
        end
        local conversion=not craftOnly and essenceConversion(id)
        if conversion and not path["essence:"..conversion.key] then
            local pth=E.Copy(path);pth["essence:"..conversion.key]=true
            local limit=ceil(missing/conversion.outputCount)
            for n=1,limit do
                if j.seedAborted then return end
                if not j.directSeed or n==1 or n==limit then
                    acquire(s,conversion.inputItemID,conversion.inputCount*n,reason,pth,function(t)
                        local u=convert(t,conversion,n,path.owner)
                        if u then acquire(u,id,need,reason,pth,emit,used) end
                    end)
                end
                tick()
            end
            had=true
        end
        if auctionPriced then
            if remaining>=missing then had=true;emit(buy(s,id,missing,"ah",price,1,nil,reason,nil,nil,path.owner))
            else
                fail("auctionSupplyLimited",nil,id,missing,remaining)
                if remaining>0 then
                    had=true
                    local t=buy(s,id,remaining,"ah",price,1,nil,reason,nil,nil,path.owner)
                    acquire(t,id,need,reason,path,emit,used)
                end
            end
        end
        for _,o in ipairs(materialVendorOffers(id)) do
            if not craftOnly and vendorQuote(o) then
                local qty=o.quantity or o.bundleSize or 1; local p=o.price
                if p and p>=0 then
                    had=true
                    local uk="vendor:"..tostring(o.npcID)..":"..qty..":"..p
                    if not used[uk] then
                        local u=E.Copy(used); u[uk]=true
                        local limit=ceil(missing/qty)
                        for k=1,limit do
                            if (not j.directSeed or k==limit) and (not j.seeding or k==1 or k==limit) then
                            local t=buy(s,id,k*qty,"vendor",p,qty,o.npcID,reason,o.url,o.estimated,path.owner,nil,o)
                            acquire(t,id,need,reason,path,emit,u); tick()
                            end
                        end
                    end
                end
            end
        end
        if j.directSeed and localBest then finalEmit(localBest); return end
        if not path[id] and (not j.directSeed or not auctionPriced or remaining<missing) then
            local pth=E.Copy(path); pth[id]=true
            for _,r in ipairs(j.snap.byItem[id] or {}) do
                if j.seedAborted then return end
                local materialProfession=opts.materialProfession or slug
                local own=path.ownProfessionOnly and r.profession==path.ownProfessionOnly
                    or not path.ownProfessionOnly and (j.purchasePriced[id] or r.profession==materialProfession or materialProfession=="__purchase")
                local usable,learning
                if own and not used[r.key] then usable,learning=allowed(r,s,"material") end
                if usable then
                    had=true; local u=E.Copy(used); u[r.key]=true
                    local limit=ceil(missing/r.count)
                    for n=1,limit do
                        if j.seedAborted then return end
                        if (not j.directSeed or n==limit) and (not j.seeding or n==1 or n==limit) then
                        craft(s,r,n,"material",pth,function(t) acquire(t,id,need,reason,path,emit,u) end,learning)
                        if j.directSeed and localBest then finalEmit(localBest); return end
                        tick()
                        end
                    end
                end
            end
        elseif path[id] and j.snap.byItem[id] then restrict(j,"material_cycle") end
        if not had then
            fail(j.auctionSupply[id] and remaining<missing and "auctionSupplyLimited"
                or "materialUnavailable",nil,id,missing,remaining)
        end
        if j.seeding and localBest then finalEmit(localBest) end
    end
    local function gather(s,p,target,emit)
        if p=="mining" then
                local t=clone(s); local to=min(target,t.skill[p]<155 and 155 or target)
                while t.skill[p]<to do
                    t=rank(t,p)
                    if not t then return end
                    local from=t.skill[p]; local nextLevel=min(to,t.cap[p] or 300)
                    t.skill[p]=nextLevel; t.progress[p]=0
                    log(t,{type="gather",profession=p,from=from,to=nextLevel,reason="level",count=0,spell=0})
                    tick()
                end
                emit(t)
        end
    end
    local function miningGap(s,p)
        if p~="mining" then return false end
        for _,r in ipairs(levelRecipes(p,s.skill[p])) do
            if r.learn<=s.skill[p] and s.skill[p]<r.grey then return false end
        end
        return true
    end
    local function goalBlocked(goal,s)
        local context=j.snap.specializationContext or {}
        local why=goal.blockedReason or (context.selectionConflict and "specializationChoiceConflict")
        if not why and (context.reason=="specializationUnknown" or context.actual=="unknown" or goal.abilityUnknown) then why="specializationUnknown" end
        local level=j.snap.playerLevel or j.snap.level or context.level
        if not why and goal.minLevel and (not level or level<goal.minLevel) then
            why=level and "specializationLevelRequired" or "specializationLevelUnknown"
        end
        if why then fail(why,{key=goal.id,profession=goal.profession,spell=goal.abilityID});return true end
        return false
    end
    local function finishGoal(s,goal)
        local t=clone(s)
        t.specializationAbilities[goal.abilityID]=true
        t.completedSpecializationGoals[goal.id]=true
        local skill=t.skill[goal.profession]
        log(t,{type="specialization_quest",profession=goal.profession,from=skill,to=skill,
            quest=E.Copy(goal),inputs=E.Copy(goal.inputs),goalID=goal.id,questID=goal.questID,abilityID=goal.abilityID})
        return t
    end
    local function quest(s,goal,emit)
        local wasSeeding,wasDirect,deadline=j.seeding,j.directSeed,j.seedDeadline
        if not j.directSeed or opts.specializationRecipeScore then
            j.seeding=false;j.directSeed=false
        end
        local function reagents(t,i)
            local m=goal.inputs[i]
            if not m then emit(finishGoal(t,goal));return end
            acquire(t,m[1],m[2],"specialization",{owner="quest:"..goal.id,ownProfessionOnly=goal.profession},function(u)
                u=clone(u);consume(u,m[1],m[2]);reagents(u,i+1)
            end)
        end
        reagents(s,1)
        j.seeding,j.directSeed,j.seedDeadline=wasSeeding,wasDirect,deadline
    end
    local function finishTool(s,goal)
        local t=clone(s);t.completedToolGoals[goal.id]=true
        log(t,{type="tool_goal",item=goal.item,count=1,goalID=goal.id,profession=goal.profession,minSkill=goal.minSkill})
        return t
    end
    local function procureTool(s,goal,emit)
        local path={owner="tool:"..goal.id,ownProfessionOnly=goal.profession}
        if goal.bindOnPickup then path.forceCraftItem=goal.item end
        acquire(s,goal.item,1,"tool",path,function(t) emit(finishTool(t,goal)) end)
    end
    local function executeSteps(steps,start,onPrefix)
        local current=start
        local function toolsDue()
            for _,goal in ipairs(j.snap.toolGoals or {}) do
                if not current.completedToolGoals[goal.id] and current.skill[slug]>=goal.minSkill then
                    local winner
                    procureTool(current,goal,function(t) if better(t,winner) then winner=t end end)
                    if not winner then return false end
                    current=winner
                end
            end
            return true
        end
        for _,step in ipairs(steps) do
            if not current or not toolsDue() then current=nil;break end
            local r=j.snap.byKey[(step.profession or slug)..":"..step[3]]
            if not r then fail("clientDataPending",{key=tostring(step[3]),spell=step[3]});current=nil;break end
            local n=ceil(step[4] or 0)
            local skillGoal=min(j.target,step[2] or 0)
            local leveling=skillGoal>(step[1] or 0)
            local attempts=0
            while current and (leveling and current.skill[r.profession]<skillGoal or not leveling and attempts<n) do
                if not toolsDue() then current=nil;break end
                if leveling and current.skill[r.profession]>=skillGoal then break end
                if leveling and E.Gain(r,current.skill[r.profession])<=0 then
                    fail("levelGap",r);current=nil;break
                end
                local winner
                craft(current,r,1,leveling and "level" or "material",{},function(t) if better(t,winner) then winner=t end end)
                current=winner
                attempts=attempts+1
                if not current then break end
            end
            if not current then break end
            if onPrefix then onPrefix(current) end
        end
        if current and not toolsDue() then current=nil end
        return current
    end
    local function expand(s,p,target,path,emit,greedy)
        if j.seedAborted then return end
        if p==slug then
            for _,goal in ipairs(j.snap.toolGoals or {}) do
                if not s.completedToolGoals[goal.id] and (s.skill[p] or 0)>=goal.minSkill then
                    procureTool(s,goal,emit)
                    return
                end
            end
            if j.specializationConflict and (s.skill[p] or 0)>=200 then
                fail("specializationChoiceConflict",{key=p,profession=p});return
            end
            for _,goal in ipairs(j.snap.specializationGoals or {}) do
                if not s.completedSpecializationGoals[goal.id] and not s.specializationAbilities[goal.abilityID]
                    and (s.skill[p] or 0)>=(goal.minSkill or 0) then
                    if goalBlocked(goal,s) then return end
                    quest(s,goal,emit)
                    if greedy or s.skill[p]>=target then return end
                end
            end
            if s.skill[p]>=target then return end
        end
        local any=false
        if greedy and j.seeding then
            local candidates={}
            local quoteCache={}
            local function quote(id,qty,path)
                j.workCounters.seedQuoteCalls=j.workCounters.seedQuoteCalls+1
                tick()
                if j.seedAborted then return math.huge end
                local missing=max(0,qty-available(s,id)); if missing==0 then return 0 end
                local key=id..":"..missing
                if quoteCache[key]~=nil then return quoteCache[key] end
                local price=j.snap.prices[id]
                local auctionPriced=auctionQuote(id)
                local enoughAuction=auctionPriced and auctionRemaining(s,id)>=missing
                local best=enoughAuction and price*missing or math.huge
                local producers = j.snap.byItem[id]
                local rawLeaf = (not producers or #producers==0)
                    and not j.auctionSupply[id] and not essenceConversion(id)
                if rawLeaf then
                    local bucket = j.seedLeafPrices[id]
                    local cached = bucket and bucket[missing]
                    if cached ~= nil then
                        j.workCounters.leafQuoteHits = j.workCounters.leafQuoteHits + 1
                        quoteCache[key] = cached
                        if cached==math.huge and j.collectFailures and not j.seedAborted then
                            fail("materialUnavailable", nil, id, missing, nil)
                        end
                        return cached
                    end
                    local raw = best
                    for _,offer in ipairs(materialVendorOffers(id)) do
                        if vendorQuote(offer) then
                            local size = offer.quantity or offer.bundleSize or 1
                            raw = min(raw, ceil(missing / size) * offer.price)
                        end
                    end
                    if (j.seedLeafPriceEntries or 0)<4096 then
                        if not bucket then bucket={}; j.seedLeafPrices[id]=bucket end
                        bucket[missing] = raw
                        j.seedLeafPriceEntries=(j.seedLeafPriceEntries or 0)+1
                    end
                    quoteCache[key] = raw
                    if raw==math.huge and j.collectFailures and not j.seedAborted then
                        fail("materialUnavailable", nil, id, missing, nil)
                    end
                    return raw
                end
                for _,o in ipairs(E.PreferredVendorOffers(j.snap.offers[id],vendorQuote)) do
                    if vendorQuote(o) then
                        local bundle=o.quantity or o.bundleSize or 1
                        best=min(best,ceil(missing/bundle)*o.price)
                    end
                end
                path=path or {}
                if path[id] then return best,true end
                local conversion=essenceConversion(id)
                if conversion and not path["essence:"..conversion.key] then
                    local pth=E.Copy(path);pth["essence:"..conversion.key]=true
                    for n=1,ceil(missing/conversion.outputCount) do
                        local sourceCost=quote(conversion.inputItemID,conversion.inputCount*n,pth)
                        local residual=max(0,missing-conversion.outputCount*n)
                        local targetCost=residual==0 and 0 or quote(id,available(s,id)+residual,pth)
                        best=min(best,sourceCost+targetCost)
                    end
                end
                if j.directSeed then
                    best=min(best,seedMaterialQuote(s,id,qty))
                    if best<math.huge then
                        quoteCache[key]=best
                        return best
                    end
                end
                local cyclic=false
                if not path[id] then
                    path[id]=true
                    for _,r in ipairs(j.snap.byItem[id] or {}) do
                        local materialProfession=opts.materialProfession or slug
                        if (r.profession==materialProfession or materialProfession=="__purchase") and allowed(r,s,"material") then
                            local count=ceil(missing/r.count); local cost=0
                            local f=j.formulaByRecipe[r.key]
                            if f and not f.known and not s.formulaPaid[f.id or r.key] then cost=f.cost or 0 end
                            for _,mat in ipairs(r.mats) do
                                local value,cycle=quote(mat[1],mat[2]*count,path)
                                cost=cost+value; cyclic=cyclic or cycle
                            end
                            best=min(best,cost)
                        end
                    end
                    path[id]=nil
                end
                if best<math.huge or not cyclic then quoteCache[key]=best end
                if best==math.huge and j.collectFailures and not j.seedAborted then
                    fail(j.auctionSupply[id] and auctionRemaining(s,id)<missing
                        and "auctionSupplyLimited" or "materialUnavailable",nil,id,missing,auctionRemaining(s,id))
                end
                return best,cyclic
            end
            for _,r in ipairs(levelRecipes(p,s.skill[p])) do
                local sk=s.skill[p]
                local usable,learning
                if r.learn<=sk and sk<r.grey then usable,learning=allowed(r,s,"level") end
                if usable
                    and (not j.referenceSeed or not j.referenceRecipes[r.key] or s.lastRecipe==r.key) then
                    any=true
                    local n=(opts.specializationRecipeScore or j.smoothSeed) and 1
                        or max(1,ceil((1-(s.progress[p] or 0))/max(.000001,E.Gain(r,sk))-1e-7))
                    local estimate=0
                    local f=j.formulaByRecipe[r.key]
                    if f and not f.known and not s.formulaPaid[f.id or r.key] then estimate=f.cost or 0 end
                    for _,m in ipairs(r.mats) do estimate=estimate+quote(m[1],m[2]*n) end
                    local rate
                    if j.smoothSeed then
                        local value=0
                        if f and not f.known and not s.formulaPaid[f.id or r.key] then value=f.cost or 0 end
                        for _,m in ipairs(r.mats) do value=value+(j.values[m[1]] or 0)*m[2] end
                        local sale=j.smoothSeed~="purchase" and j.recovery and j.snap.recovery.quotes[r.item]
                        if sale and (not j.profitRecipes[r.key] or (s.profitMade[r.key] or 0)<ns.ProfRecovery.PROFIT_CAP) then
                            local retained=j.snap.retainedToolItems and j.snap.retainedToolItems[r.item] or 0
                            local missingRetained=max(0,retained-available(s,r.item))
                            value=value-max(0,r.count-missingRetained)*(sale.unit or 0)
                        end
                        rate=value/max(.000001,E.Gain(r,sk))
                    end
                    candidates[#candidates+1]={recipe=r,count=n,estimate=estimate,rate=rate,learning=p==slug and learning or nil}
                    if j.hasFiniteSupply and n>1 then
                        local partialCost=0
                        if f and not f.known and not s.formulaPaid[f.id or r.key] then partialCost=f.cost or 0 end
                        for _,m in ipairs(r.mats) do partialCost=partialCost+quote(m[1],m[2]) end
                        candidates[#candidates+1]={recipe=r,count=1,estimate=partialCost*n,learning=p==slug and learning or nil}
                    end
                end
                tick()
            end
            if s.risk then
                for _,candidate in ipairs(candidates) do
                    candidate.risk=R.Apply(s.risk,{type="craft",profession=p,spell=candidate.recipe.spell,count=candidate.count,reason=p==slug and "level" or "secondary"})
                    R.Score(candidate.risk)
                    tick()
                end
            end
            table.sort(candidates,function(a,b)
                if a.risk and b.risk then local risk=R.Compare(a.risk,b.risk);if risk~=0 then return risk<0 end end
                if j.smoothSeed then
                    if a.rate~=b.rate then return a.rate<b.rate end
                    local sameA,sameB=a.recipe.key==s.lastRecipe,b.recipe.key==s.lastRecipe
                    if sameA~=sameB then return sameA end
                end
                return a.estimate<b.estimate or (a.estimate==b.estimate and a.recipe.spell<b.recipe.spell)
            end)
            local selected,selectedScore
            local directTrials=0
            for _,candidate in ipairs(candidates) do
                if j.seedAborted then return end
                if j.directSeed and selected and not opts.specializationRecipeScore
                    and (directTrials>=3 or not stable and candidate.estimate>=selected.money-s.money-1e-7) then break end
                if candidate.estimate<math.huge or not j.directSeed then
                    directTrials=directTrials+1
                    j.workCounters.seedCandidateTrials=j.workCounters.seedCandidateTrials+1
                    local winner
                    craft(s,candidate.recipe,candidate.count,p==slug and "level" or "secondary",path,function(t)
                        if (t.skill[p]>s.skill[p] or t.skill[p]==s.skill[p] and (t.progress[p] or 0)>(s.progress[p] or 0))
                            and better(t,winner) then winner=t end
                    end,candidate.learning)
                    local score=winner and opts.specializationRecipeScore and opts.specializationRecipeScore(candidate.recipe,s,j.snap,winner.money-s.money)
                    if winner and (score and (not selectedScore or score<selectedScore-1e-7
                        or math.abs(score-selectedScore)<1e-7 and better(winner,selected))
                        or not score and better(winner,selected)) then selected=winner;selectedScore=score end
                end
            end
            if selected then emit(selected); return end
            if not any and miningGap(s,p) then gather(s,p,target,emit)
            elseif not any then fail("levelGap",{key=p..":"..s.skill[p],profession=p}) end
            return
        end
        for _,r in ipairs(levelRecipes(p,s.skill[p])) do
            local sk=s.skill[p]
            local usable,learning
            if r.learn<=sk and sk<r.grey then usable,learning=allowed(r,s,"level") end
            if usable then
                any=true
                local g=E.Gain(r,sk)
                local n=greedy and max(1,ceil((1-(s.progress[p] or 0))/max(.000001,g)-1e-7)) or 1
                craft(s,r,n,p==slug and "level" or "secondary",path,emit,p==slug and learning or nil)
            end
            tick()
        end
        if not any and miningGap(s,p) then gather(s,p,target,emit)
        elseif not any then fail("levelGap",{key=p..":"..s.skill[p],profession=p}) end
    end
    levelTo=function(s,p,target,path,emit)
        local stack={s}; local visited={}
        while #stack>0 do
            if j.seedAborted then return end
            local t=table.remove(stack)
            if t.skill[p]>=target then emit(t)
            else
                local k=stateKey(t,j.reusable,j.recovery)
                if visited[k]==nil or t.money<visited[k] then visited[k]=t.money; expand(t,p,target,path,function(u) stack[#stack+1]=u end,true) end
            end
            tick()
        end
        restrict(j,"secondary_point_blocks")
    end
    local function batchPlan(raw,requireGoal)
        if raw and raw.batched and (not requireGoal or goalsComplete(j,raw)) then
            j.workCounters.batchReuses=j.workCounters.batchReuses+1
            return raw
        end
        j.workCounters.batchedPlans=j.workCounters.batchedPlans+1
        local original=actions(raw,tick)
        local function replay(list,start,checkpoint,activeRecipes)
            if checkpoint and not checkpoint() then return end
            j.workCounters.replayCalls=j.workCounters.replayCalls+1
            local t=start or initial(j.snap,slug,opts,tick)
            local greenCrafts=t.rebatchGreenCrafts or 0
            if not start then t.diagnostics={} end
            local active=activeRecipes or {}
            for _,a in ipairs(list) do
                if checkpoint and not checkpoint() then return end
                if a.type=="craft" then active[a.profession..":"..a.spell]=true end;tick()
            end
            local index=1
            while index<=#list do
                local a=list[index];index=index+1
                if checkpoint and not checkpoint() then return end
                if a.type=="buy" then
                    local bundle=a.bundleSize or 1
                    if a.count<=0 or a.count%bundle~=0 then return end
                    local price=a.bundlePrice or a.cost/(a.count/bundle)
                    t=buy(t,a.item,a.count,a.source,price,bundle,a.npcID,a.reason,a.url,a.estimated,a.owner,a.unpriced,
                        stampStock({reference=a.reference,source=a.quoteSource,priceSource=a.priceSource,priceBasis=a.priceBasis,verifiedAt=a.verifiedAt},a))
                    if not t then return end
                elseif a.type=="formula" and active[a.owner] then
                    local f=a.formula; local key=f and (f.id or a.owner)
                    if f and not t.formulaPaid[key] then
                        if ns.IsForever and ns.ProfLearningSources and E.RouteRecipeEligibility then
                            local rec=j.snap.byKey[a.owner]
                            local ok,detail
                            if rec then local accepted,_,value=E.RouteRecipeEligibility(rec,j.snap,supportedState(t));ok,detail=accepted,value end
                            local quote=detail and detail.quote
                            if not ok or not quote or quote.usable~=true
                                or quote.learningRouteId~=f.learningRouteId or (quote.cost or 0)~=a.cost then return end
                        end
                        if a.source=="ah" and auctionRemaining(t,a.item)<(a.count or 1) then return end
                        t=clone(t);t.formulaPaid[key]=true;t.money=t.money+a.cost
                        if a.source=="ah" and j.auctionSupply[a.item] then t.ahUsed[a.item]=(t.ahUsed[a.item] or 0)+(a.count or 1) end
                        log(t,E.Copy(a))
                        if f.unpriced then diagnostic(t,"formula:"..tostring(key),"formulaPriceUnknown",f.id or a.owner) end
                        if f.availabilityUncertain then diagnostic(t,"formulaStock:"..tostring(key),"formulaStockUnknown",f.id or a.owner) end
                    end
                elseif a.type=="gather" then
                    local event=E.Copy(a);event.from=t.skill[a.profession];event.to=max(event.from,a.to)
                    t.skill[a.profession]=event.to;t.progress[a.profession]=0;log(t,event)
                elseif a.type=="convert" then
                    local c=essenceConversion(a.item)
                    if not c then return end
                    t=convert(t,c,a.count,a.owner);if not t then return end
                elseif a.type=="tool_goal" then
                    local goal
                    for _,candidate in ipairs(j.snap.toolGoals or {}) do if candidate.id==a.goalID then goal=candidate;break end end
                    if not goal or available(t,goal.item)<1 or (supportedState(t).skill[goal.profession] or 0)<goal.minSkill then return end
                    t=finishTool(t,goal)
                elseif a.type=="specialization_quest" then
                    local goal=a.quest
                    if not goal or t.completedSpecializationGoals[goal.id] or (supportedState(t).skill[goal.profession] or 0)<(goal.minSkill or 0)
                        or goalBlocked(goal,t) then return end
                    for _,m in ipairs(goal.inputs) do if available(t,m[1])<m[2] then return end end
                    for _,m in ipairs(goal.inputs) do consume(t,m[1],m[2]) end
                    t=finishGoal(t,goal)
                elseif a.type=="craft" then
                    local r=j.snap.byKey[a.profession..":"..a.spell]
                    if not r then return end
                    local usable,learning=allowed(r,t,a.reason,true)
                    if (supportedState(t).skill[r.profession] or 0)<r.learn then return nil,index-1 end
                    if not usable then return end
                    local n=a.count;local from=t.skill[r.profession];local progressFrom=t.progress[r.profession] or 0
                    if checkpoint and (t.learned[r.key] or t.learned[r.spell]) then
                        local recursive=false
                        for _,m in ipairs(r.mats) do if m[1]==r.item then recursive=true;break end end
                        while not recursive and index<=#list do
                            local following=list[index]
                            if following.type~="craft" or following.profession~=a.profession or following.spell~=a.spell
                                or following.reason~=a.reason then break end
                            n=n+following.count;index=index+1
                            if not checkpoint() then return end
                        end
                    end
                    for _,m in ipairs(r.mats) do if available(t,m[1])<m[2]*n then return end end
                    t=learnFormula(t,r,nil,learning);if not t then return end
                    local inputs={}
                    for _,m in ipairs(r.mats) do inputs[#inputs+1]={m[1],m[2]*n};consume(t,m[1],m[2]*n) end
                    local gainSum=0
                    for _=1,n do
                        if checkpoint and not checkpoint() then return end
                        local gain=E.Gain(r,t.skill[r.profession])
                        if gain>0 and t.skill[r.profession]>=(t.cap[r.profession] or 300) then
                            if a.reason=="level" or a.reason=="secondary" then t=rank(t,r.profession) else gain=0 end
                        end
                        countGreen(t,r,a.reason,gain)
                        if gain>0 and (a.reason=="level" or a.reason=="secondary")
                            and t.skill[r.profession]>=r.green
                            and (r.profession~=slug or t.skill[r.profession]<j.target) then greenCrafts=greenCrafts+1 end
                        gainSum=gainSum+gain
                        local progress=(t.progress[r.profession] or 0)+gain;local whole=floor(progress+1e-7)
                        t.skill[r.profession]=min(300,t.skill[r.profession]+whole)
                        t.progress[r.profession]=floor((progress-whole)*1000000+.5)/1000000;tick()
                    end
                    local made=r.item and r.count*n or 0;local usable=output(t,r,n)
                    if r.profession==slug and t.lastRecipe~=r.key then t.switches=t.switches+1;t.lastRecipe=r.key end
                    log(t,{type="craft",profession=r.profession,spell=r.spell,count=n,from=from,to=t.skill[r.profession],
                        fromProgress=progressFrom,toProgress=t.progress[r.profession] or 0,expectedGain=gainSum,
                        item=r.item,outputCount=made,outputs=r.item and {{r.item,made}} or {},inputs=inputs,
                        reason=a.reason,usableOutput=usable,learningRoute=learning and learning.route})
                end
                tick()
            end
            t.rebatchGreenCrafts=greenCrafts
            return t
        end
        local function preservesProgress(candidate,t)
            if not t then return false end
            if candidate.risk and (not t.risk or R.Compare(t.risk,candidate.risk)>0) then return false end
            for p,skill in pairs(not candidate.risk and candidate.skill or {}) do
                local progressGoal=p==slug and j.target or 300
                if (t.skill[p] or 0)<min(skill,progressGoal) or skill<progressGoal and t.skill[p]==skill
                    and (t.progress[p] or 0)+1e-7<(candidate.progress[p] or 0) then return false end
            end
            for _,field in ipairs({"completedSpecializationGoals","completedToolGoals"}) do
                for id in pairs(candidate[field]) do if not t[field][id] then return false end end
            end
            return true
        end
        local function rebuildBatches(candidate,advance)
            local list=actions(candidate)
            local current=initial(j.snap,slug,opts,tick)
            if advance then
                local useful
                for _,a in ipairs(list) do
                    local key=rebatchKey(a);local r=key and j.snap.byKey[key]
                    if r and r.item and a.reason=="material" and a.usableOutput~=false
                        and (a.from or 0)>=r.grey and (current.skill[r.profession] or 0)<r.grey then useful=true;break end
                    tick()
                end
                if not useful then return end
            end
            local caps={};for p,v in pairs(j.snap.professions) do caps[p]=v.max or 300 end
            local made,tools={},{}
            for _,a in ipairs(list) do if a.type=="craft" and a.item then made[a.item]=true end end
            for _,goal in ipairs(j.snap.toolGoals or {}) do if not made[goal.item] then tools[goal.id]=goal end end
            local stages=rebatchStages(list,j.snap.byKey,nil,caps,tools)
            local ranges={};for _,range in ipairs(stages) do ranges[range[1]]=range[2] end
            local advanced={}
            local function advanceMaterials(first)
                local groups,byKey={},{}
                for i=first,#list do
                    local a=list[i];local key=rebatchKey(a);local r=key and j.snap.byKey[key]
                    if r and r.item and not advanced[key] and a.reason=="material" and a.usableOutput~=false
                        and (a.from or 0)>=r.grey and (current.skill[r.profession] or 0)>=r.learn
                        and (current.skill[r.profession] or 0)<min(r.grey,current.cap[r.profession] or 300) then
                        local g=byKey[key]
                        if not g then g={recipe=r,count=0};groups[#groups+1]=g;byKey[key]=g end
                        g.count=g.count+a.count
                    end
                    tick()
                end
                for _,g in ipairs(groups) do
                    local r=g.recipe;local skill=current.skill[r.profession]
                    local target=min(r.grey,current.cap[r.profession] or 300,r.profession==slug and j.target or 300)
                    local limit=min(advance[r.key] or g.count,max(0,g.count-floor(available(current,r.item)/r.count)))
                    local n,progress=0,current.progress[r.profession] or 0
                    while n<limit and skill<target do
                        local gain=E.Gain(r,skill);if gain<=0 then break end
                        progress=progress+gain;local whole=floor(progress+1e-7)
                        skill=skill+whole;progress=floor((progress-whole)*1000000+.5)/1000000
                        n=n+1;tick()
                    end
                    if n>0 then
                        local best
                        craft(current,r,n,"material",{[r.item]=true},function(t) if better(t,best) then best=t end end)
                        if best then current=best;advanced[r.key]=n end
                    end
                end
            end
            local function stage(first,last)
                local groups,byKey,byItem,used,goals,pending={},{},{},{},{},{}
                for i=first,last do
                    local a=list[i]
                    if a.type=="craft" then
                        local key=rebatchKey(a);local r=j.snap.byKey[key]
                        if not r then return end
                        local g=byKey[key]
                        if not g then
                            g={recipe=r,count=0,goal=0,reason=a.reason,produced=0}
                            groups[#groups+1]=g;byKey[key]=g
                            if r.item then
                                if byItem[r.item] and byItem[r.item]~=g then return end
                                byItem[r.item]=g
                            end
                        end
                        g.count=g.count+a.count;g.produced=g.produced+(a.outputCount or 0)
                        if a.reason=="level" or a.reason=="secondary" then
                            g.reason=a.reason
                            if (a.expectedGain or 0)>0 or a.to>a.from then g.goal=max(g.goal,a.to) end
                        end
                        goals[a.profession]=max(goals[a.profession] or 0,a.to)
                        for _,m in ipairs(a.inputs or {}) do used[m[1]]=(used[m[1]] or 0)+m[2] end
                    elseif a.type=="tool_goal" and tools[a.goalID] then
                        pending[#pending+1]=tools[a.goalID]
                    end
                end
                local function prepareTools()
                    for _,goal in ipairs(pending) do
                        if not current.completedToolGoals[goal.id] and (current.skill[goal.profession] or 0)>=goal.minSkill then
                            local best
                            procureTool(current,goal,function(t) if better(t,best) then best=t end end)
                            if not best then return false end
                            current=best
                        end
                    end
                    return true
                end
                if not prepareTools() then return end
                if #groups==0 then
                    for _,goal in ipairs(pending) do if not current.completedToolGoals[goal.id] then return end end
                    return current
                end
                local roots={}
                j.batchRecipes={}
                for _,g in ipairs(groups) do
                    local r=g.recipe
                    if r.item and used[r.item] then j.batchRecipes[r.item]=r end
                    if not r.item or not used[r.item] or g.produced>used[r.item] then roots[#roots+1]=g end
                end
                if #roots==0 then return end
                if advance then advanceMaterials(first) end
                local lastRoot={};for _,g in ipairs(roots) do lastRoot[g.recipe.profession]=g end
                for _,g in ipairs(roots) do
                    local r=g.recipe;local goal=g.goal
                    if lastRoot[r.profession]==g then goal=max(goal,goals[r.profession] or 0) end
                    local minimum=g.reason=="material" and g.count or 0
                    for i=last+1,#list do
                        local a=list[i]
                        if a.type=="tool_goal" and a.item==r.item then minimum=max(minimum,g.count) end
                        for _,m in ipairs(a.inputs or a.quest and a.quest.inputs or {}) do
                            if m[1]==r.item then minimum=max(minimum,g.count) end
                        end
                    end
                    local base=current
                    if advance and r.item then minimum=max(0,minimum-floor(available(base,r.item)/r.count)) end
                    local function trial(n)
                        if n==0 then return base end
                        local best
                        craft(base,r,n,g.reason or "level",{},function(t) if better(t,best) then best=t end end)
                        return best
                    end
                    local function reached(t) return t and (t.skill[r.profession] or 0)>=goal end
                    local low,high=minimum,max(minimum,g.count)
                    local chosen=trial(low)
                    if not reached(chosen) then
                        chosen=trial(high)
                        while chosen and not reached(chosen) and high<10000 do
                            low=high+1;high=min(10000,high*2);chosen=trial(high)
                        end
                        if not reached(chosen) then return end
                        while low<high do
                            local middle=floor((low+high)/2);local probe=trial(middle)
                            if reached(probe) then high=middle;chosen=probe else low=middle+1 end
                            tick()
                        end
                    end
                    if not chosen then return end
                    current=chosen
                    if not prepareTools() then return end
                end
                for p,goal in pairs(goals) do if (current.skill[p] or 0)<goal then return end end
                for _,goal in ipairs(pending) do if not current.completedToolGoals[goal.id] then return end end
                return current
            end
            local i=1
            while i<=#list do
                local last=ranges[i]
                if last then
                    if not stage(i,last) then return end
                    i=last+1
                else
                    local a=list[i]
                    if a.type=="tool_goal" then
                        local goal,best
                        for _,g in ipairs(j.snap.toolGoals or {}) do if g.id==a.goalID then goal=g;break end end
                        if not goal or (current.skill[goal.profession] or 0)<goal.minSkill then return end
                        procureTool(current,goal,function(t) if better(t,best) then best=t end end)
                        if not best then return end
                        current=best
                    elseif a.type~="formula" and a.type~="buy" then
                        current=replay({a},clone(current));if not current then return end
                    end
                    i=i+1
                end
                tick()
            end
            local verified=replay(actions(current))
            if not preservesProgress(candidate,verified) or uncertainty(verified)>uncertainty(candidate) then return end
            if advance and not next(advanced) then return end
            local retry
            for key,n in pairs(advanced) do
                local r=j.snap.byKey[key]
                local surplus=available(verified,r.item)-max(available(candidate,r.item),r.count-1)
                if surplus>0 then advance[key]=max(0,n-ceil(surplus/r.count));retry=true end
            end
            if retry then return nil,true end
            if not advance and rebatchSwitches(actions(verified))>=rebatchSwitches(list) then return end
            verified.batched=true
            return verified
        end
        local function reflowBatches(candidate)
            local deadline,work,aborted=j.seedDeadline,j.seedWorkRemaining,j.seedAborted
            j.seedDeadline=nil;j.seedWorkRemaining=nil;j.seedAborted=false
            local function calculate()
            local list=actions(candidate);local made,used,tools={},{},{}
            for _,a in ipairs(list) do
                if a.type=="craft" then
                    if a.profession~=slug then return end
                    if a.item then made[a.item]=true end
                    for _,m in ipairs(a.inputs or {}) do used[m[1]]=true end
                elseif a.type~="buy" and a.type~="formula" and a.type~="tool_goal" then return end
                tick()
            end
            for _,goal in ipairs(j.snap.toolGoals or {}) do
                used[goal.item]=true
                if not made[goal.item] then tools[goal.id]=goal end
            end
            local caps={};for p,v in pairs(j.snap.professions) do caps[p]=v.max or 300 end
            local function checkpoint() tick();return not j.seedAborted end
            local edges=rebatchDependencies(list,checkpoint,true,true)
            if not edges then return end
            local order,reordered={},{};for i,a in ipairs(list) do order[i]=a end
            for _,range in ipairs(rebatchStages(list,j.snap.byKey,nil,caps,tools)) do
                local sorted=rebatchStageOrder(list,edges,range[1],range[2],checkpoint)
                if j.seedAborted then return end
                local before={};for i=range[1],range[2] do before[#before+1]=list[i] end
                if sorted and rebatchSwitches(sorted)<rebatchSwitches(before) then
                    for i,a in ipairs(sorted) do order[range[1]+i-1]=a;reordered[a]=true end
                    break
                end
            end
            if rebatchSwitches(order)>=rebatchSwitches(list) then return end
            local steps,last={},nil
            for _,a in ipairs(order) do
                local key=rebatchKey(a)
                if key then
                    local step=steps[#steps]
                    if last~=key then
                        step={a.from,a.to,a.spell,0,profession=a.profession,material=true,item=a.item}
                        steps[#steps+1]=step;last=key
                    end
                    step[2]=max(step[2],a.to);step[4]=step[4]+a.count
                    if reordered[a] then step.reordered=true end
                    if a.reason=="level" or a.reason=="secondary" then step.material=false end
                elseif a.type=="tool_goal" and not tools[a.goalID] then last=nil end
            end
            for _,step in ipairs(steps) do if step.material or step.reordered and used[step.item] then step[2]=step[1] end end
            local best,remaining=nil,0
            for _,step in ipairs(steps) do if step.reordered and used[step.item] then remaining=remaining+step[4] end end
            local total=remaining
            while true do
                j.batchRecipes={}
                local state=executeSteps(steps,initial(j.snap,slug,opts,tick))
                j.batchRecipes=nil
                if not state or j.seedAborted then break end
                local prepared=batchPlan(state,goalsComplete(j,candidate))
                local verified=prepared and replay(actions(prepared),nil,function() return not j.seedAborted end)
                if not preservesProgress(candidate,verified) or uncertainty(verified)>uncertainty(candidate) then break end
                verified.batched=true
                if better(verified,best) then best=verified end
                local changed=false
                for _,step in ipairs(steps) do
                    if step.reordered and used[step.item] then
                        local r=j.snap.byKey[step.profession..":"..step[3]]
                        local surplus=available(verified,step.item)-max(available(candidate,step.item),r.count-1)
                        local n=max(0,step[4]-floor(surplus/r.count))
                        if n<step[4] then remaining=remaining-step[4]+n;step[4]=n;changed=true end
                    end
                end
                finalizeProgress(j,.3+.12*(total-remaining)/(total+1))
                if not changed or j.seedAborted then break end
            end
            return best
            end
            local best=calculate()
            j.seedDeadline,j.seedWorkRemaining,j.seedAborted=deadline,work,aborted
            return best
        end
        local first=replay(original)
        if not first then fail("executionInvalid");return end
        if not j.rebatchFinal then
            j.rebatchFinal = function(candidate)
                if opts.fixedSteps or opts.procurementDemands or opts.preserveRecipeOrder then
                    return candidate
                end
                local failures, collected = j.failures, j.collectFailures
                local restricted, restriction = j.restricted, j.restrictedReason
                j.failures, j.collectFailures = {}, nil
                local seeding,direct,aborted,deadline,work,smooth=j.seeding,j.directSeed,j.seedAborted,j.seedDeadline,j.seedWorkRemaining,j.smoothSeed
                j.seeding=true;j.directSeed=true;j.seedAborted=false;j.seedDeadline=nil;j.seedWorkRemaining=nil;j.smoothSeed=nil
                local function replayFinal(list,checkpoint)
                    local t,failedAt=replay(list,nil,checkpoint)
                    if not t then return nil,failedAt end
                    if preservesProgress(candidate,t) then return t end
                end
                local rebuilt=rebuildBatches(candidate)
                finalizeProgress(j,.12)
                if rebuilt and not better(rebuilt,candidate) then rebuilt=nil end
                local limits,quantities={},{}
                local remaining=0
                for _,a in ipairs(actions(candidate)) do
                    local key=rebatchKey(a);local r=key and j.snap.byKey[key]
                    if r and a.reason=="material" and (a.from or 0)>=r.grey then
                        quantities[key]=(quantities[key] or 0)+a.count;remaining=remaining+a.count
                    end
                end
                local total=remaining
                while true do
                    local advanced,retry=rebuildBatches(candidate,limits)
                    local nextRemaining=0
                    for key,n in pairs(quantities) do nextRemaining=nextRemaining+min(n,limits[key] or n) end
                    finalizeProgress(j,.12+.18*(total-nextRemaining)/(total+1))
                    if advanced and better(advanced,candidate) and (not rebuilt or better(advanced,rebuilt)) then rebuilt=advanced end
                    if not retry or nextRemaining>=remaining then break end
                    remaining=nextRemaining
                    tick()
                end
                finalizeProgress(j,.3)
                local reflow=reflowBatches(candidate)
                finalizeProgress(j,.42)
                if reflow and better(reflow,candidate) and (not rebuilt or better(reflow,rebuilt)) then rebuilt=reflow end
                j.batchRecipes=nil
                local baseline=candidate.rebatchGreenCrafts~=nil and candidate or replayFinal(actions(candidate))
                finalizeProgress(j,.45)
                local progressGoals={[slug]=j.target}
                local function schedule(state,from,to)
                    local active,kinds,gathered={},{},{}
                    for _,a in ipairs(actions(state)) do
                        local key=rebatchKey(a)
                        if key then
                            active[key]=true;kinds[key]=kinds[key] or {}
                            kinds[key][(a.reason=="level" or a.reason=="secondary") and "level" or "material"]=true
                        elseif a.type=="gather" then gathered[a.profession]=true end
                        tick()
                    end
                    local start=initial(j.snap,slug,opts,tick);local equivalentReasons={}
                    for key,group in pairs(kinds) do
                        local r=j.snap.byKey[key];local cap=start.cap[r.profession] or 300
                        if not gathered[r.profession] and start.skill[r.profession]<=cap then
                            while cap<r.learn and cap<300 do cap=cap<=75 and 150 or cap<=150 and 225 or 300 end
                        end
                        equivalentReasons[key]=not (group.level and group.material) or r.grey<=cap
                        tick()
                    end
                    local function advance(current,action)
                        return replay({action},clone(current),nil,active)
                    end
                    local inspected,best,requirements=0,state,clone(state)
                    local initialSegments=rebatchSwitches(actions(state,tick))+1
                    local distinct=0;for _ in pairs(active) do distinct=distinct+1 end
                    local progressSpan=max(1,initialSegments-distinct+1);local checked=0
                    local model=S.BatchModel(best,start,j.snap.byKey,progressGoals,tick,stable)
                    local upper=model and model.limit
                    for limit=distinct,upper or distinct-1 do
                        model.limit=limit
                        if requirements.risk and R.Score(requirements.risk).completionProbability<=0 then model.target=1;model.goal=1;model.targetProgress=0 end
                        local possible,path,stats=S.BatchFeasible(model,tick,function(value)
                            j.batchSearch={states=inspected+(value.states or 0)+(value.skillStates or 0),bestSegments=upper+1}
                            checked=max(checked,(limit-distinct+(value.progress or 0))/progressSpan)
                            finalizeProgress(j,from+(to-from)*checked)
                        end)
                        inspected=inspected+(stats and ((stats.states or 0)+(stats.skillStates or 0)) or 0)
                        if possible==nil or possible and not path then break end
                        local hint=possible and S.ReplayBatchHint(requirements,start,path,advance,tick,progressGoals,stable)
                        if possible and not hint and requirements.risk then
                            model.completionFloor=R.Completion(requirements.risk)
                            model.relaxRanks=true
                            possible,path,stats=S.BatchRiskFeasible(model,tick,function(value)
                                j.batchSearch={states=inspected+(value.states or 0)+(value.skillStates or 0),bestSegments=upper+1}
                                checked=max(checked,(limit-distinct+(value.progress or 0))/progressSpan)
                                finalizeProgress(j,from+(to-from)*checked)
                            end)
                            inspected=inspected+(stats and ((stats.states or 0)+(stats.skillStates or 0)) or 0)
                            if possible and path then hint=S.ReplayBatchHint(requirements,start,path,advance,tick,progressGoals,stable) end
                        end
                        if hint and rebatchSwitches(actions(hint,tick))+1<=limit then j.batchSearch=nil;finalizeProgress(j,to);return hint end
                        if possible~=false then break end
                        if limit==upper then j.batchSearch=nil;finalizeProgress(j,to);return best end
                        checked=max(checked,(limit-distinct+1)/progressSpan)
                        finalizeProgress(j,from+(to-from)*checked)
                    end
                    if state.risk then
                        local function warmReplay(list,checkpoint) return replay(list,nil,checkpoint) end
                        best=S.RebatchChronological(best,warmReplay,tick,nil,j.snap.byKey,false,progressGoals,true,start.cap,true)
                        best=S.RebatchChronological(best,warmReplay,tick,nil,j.snap.byKey,true,progressGoals,true,start.cap,true)
                        checked=max(checked,(initialSegments-rebatchSwitches(actions(best,tick))-1)/progressSpan)
                        finalizeProgress(j,from+(to-from)*checked)
                    end
                    return S.ScheduleBatches(state,start,advance,tick,progressGoals,stable,
                        function(fraction,stats)
                            finalizeProgress(j,from+(to-from)*(checked+(1-checked)*fraction))
                            j.batchSearch=fraction<1 and {states=inspected+stats.states,bestSegments=stats.bestSegments} or nil
                        end,{incumbent=best,requirements=requirements,prebuy=true,recipes=j.snap.byKey,equivalentReasons=equivalentReasons,ignoreStateFields={lastRecipe=true},eager=function(current,action)
                            if action.type=="tool_goal" and current.risk and R.Apply(current.risk,action)==current.risk then return advance(current,action) end
                        end,completed=function(current,action)
                            return action.type=="formula" and action.formula and current.formulaPaid[action.formula.id or action.owner]
                        end})
                end
                local result=baseline and rebatchEquivalent(candidate,baseline,progressGoals,stable) and baseline
                if stable and goalsComplete(j,candidate) and result and rebuilt then
                    if better(rebuilt,result) then result=nil else rebuilt=nil end
                elseif not stable and goalsComplete(j,candidate) and result and rebuilt then
                    local revenue=j.recovery and j.snap or nil
                    local a,b=objective(rebuilt,revenue),objective(result,revenue)
                    if (uncertainty(rebuilt)==0)~=(uncertainty(result)==0) or math.abs(a-b)>1e-7
                        or math.abs(rebuilt.money-result.money)>1e-7 then
                        if better(rebuilt,result) then result=nil else rebuilt=nil end
                    end
                end
                if rebuilt then rebuilt=schedule(rebuilt,.45,.6) end
                finalizeProgress(j,.6)
                if result then result=schedule(result,.6,.78) end
                if rebuilt then
                    if not result or not goalsComplete(j,candidate) and rebuilt.skill[slug]>result.skill[slug]
                        or (goalsComplete(j,candidate) or rebuilt.skill[slug]==result.skill[slug]) and better(rebuilt,result) then result=rebuilt end
                end
                finalizeProgress(j,.78)
                if result and candidate.risk and goalsComplete(j,candidate) and R.Compare(result.risk,candidate.risk)<=0 then result.plannedTarget=j.target end
                if result and result.skill[slug]~=candidate.skill[slug] and not goalsComplete(j,result) then
                    local advanced=false;j.failures={};j.collectFailures={};j.batchRecipes={}
                    expand(result,slug,j.target,{},function() advanced=true end,true)
                    j.blockedSkill=not advanced and result.skill[slug] or nil;j.blockers={}
                    if not advanced then for _,d in pairs(j.collectFailures) do j.blockers[#j.blockers+1]=d end end
                    j.batchRecipes=nil
                end
                j.seeding,j.directSeed,j.seedAborted,j.seedDeadline,j.seedWorkRemaining,j.smoothSeed=seeding,direct,aborted,deadline,work,smooth
                j.failures, j.collectFailures = failures, collected
                j.restricted, j.restrictedReason = restricted, restriction
                if rebuilt then restrict(j,"batch_execution") end
                finalizeProgress(j,.8)
                return result or candidate
            end
        end
        local trace=actions(first,tick);local need,keep,quantities,owners,needOwner={},{},{},{},{}
        local changed=false
        for i=#trace,1,-1 do
            local a=trace[i]
            if a.type=="craft" then
                local used=a.usableOutput~=false and a.item and (need[a.item] or 0)>0
                local useful=first.risk~=nil or (a.expectedGain or 0)>1e-9 or used or a.profession=="__purchase"
                if useful then
                    keep[i]=true
                    local r=j.snap.byKey[a.profession..":"..a.spell]
                    if E.Policy(opts.exclusions,r)=="level" and not used then
                        fail("excluded",r,r.item);return
                    end
                    if used then need[a.item]=max(0,(need[a.item] or 0)-(a.outputCount or 0)) end
                    for _,m in ipairs(a.inputs or {}) do need[m[1]]=(need[m[1]] or 0)+m[2];needOwner[m[1]]=a.profession..":"..a.spell end
                else changed=true end
            elseif a.type=="convert" then
                if (need[a.item] or 0)>0 then
                    keep[i]=true
                    need[a.item]=max(0,(need[a.item] or 0)-(a.outputCount or 0))
                    for _,m in ipairs(a.inputs or {}) do
                        need[m[1]]=(need[m[1]] or 0)+m[2];needOwner[m[1]]=a.owner
                    end
                else changed=true end
            elseif a.type=="tool_goal" then
                keep[i]=true
                need[a.item]=max(1,need[a.item] or 0);needOwner[a.item]="tool:"..a.goalID
            elseif a.type=="specialization_quest" then
                keep[i]=true
                for _,m in ipairs(a.inputs or {}) do
                    need[m[1]]=(need[m[1]] or 0)+m[2];needOwner[m[1]]="quest:"..a.goalID
                end
            elseif a.type=="buy" then
                local wanted=min(a.count,need[a.item] or 0)
                if wanted>0 then
                    local n=min(a.count,ceil(wanted/(a.bundleSize or 1))*(a.bundleSize or 1))
                    keep[i]=true;quantities[i]=n;need[a.item]=max(0,(need[a.item] or 0)-n)
                    owners[i]=needOwner[a.item]
                    if n~=a.count then changed=true end
                else changed=true end
            elseif a.type=="formula" or a.type=="gather" then keep[i]=true end
            tick()
        end
        local selected,identical={},true
        for i,a in ipairs(trace) do
            if keep[i] then
                local event=a
                if quantities[i] and quantities[i]~=a.count or owners[i] and owners[i]~=a.owner then
                    event=E.Copy(a,tick);identical=false
                    if quantities[i] then event.cost=event.cost*quantities[i]/event.count;event.count=quantities[i] end
                    if owners[i] then event.owner=owners[i] end
                end
                selected[#selected+1]=event
            else identical=false end
            tick()
        end
        local t=identical and first or replay(selected)
        if not t or (requireGoal and not goalsComplete(j,t)) then fail("executionInvalid");return end
        if changed then restrict(j,"chronological_replay_reduction") end
        local purchases,formulaStock={},{}
        for _,a in ipairs(selected) do
            if a.type=="buy" then
                local entry=purchases[a.item] or {cost=0,events=0}
                purchases[a.item]=entry
                entry.cost=entry.cost+a.cost;entry.events=entry.events+1
                if a.unpriced or a.source~="ah" and a.source~="vendor" then entry.skip=true end
            elseif a.type=="formula" and a.source=="ah" then
                formulaStock[a.item]=(formulaStock[a.item] or 0)+(a.count or 1)
            end
            tick()
        end
        for id,entry in pairs(purchases) do
            if entry.skip or entry.events<2 or #materialVendorOffers(id)==0 then purchases[id]=nil end
        end
        if not next(purchases) then t.batched=true;return t end
        local base=initial(j.snap,slug,opts,tick)
        local balance,demand={},{}
        for id in pairs(purchases) do balance[id]=available(base,id);demand[id]=0 end
        for _,a in ipairs(selected) do
            if a.type=="craft" or a.type=="convert" or a.type=="specialization_quest" then
                local inputs=a.type=="specialization_quest" and a.quest and a.quest.inputs or a.inputs
                for _,m in ipairs(inputs or {}) do if balance[m[1]] then
                    balance[m[1]]=balance[m[1]]-m[2]
                    demand[m[1]]=max(demand[m[1]],-balance[m[1]])
                end end
                if a.usableOutput~=false then
                    for _,m in ipairs(a.outputs or {}) do if balance[m[1]] then balance[m[1]]=balance[m[1]]+m[2] end end
                end
            elseif a.type=="tool_goal" and balance[a.item] then
                demand[a.item]=max(demand[a.item],1-balance[a.item])
            end
            tick()
        end
        local replacements={}
        for id,entry in pairs(purchases) do
            if demand[id]>0 then
                local supply=j.auctionSupply[id]
                local remaining=supply and max(0,supply.quantity-(formulaStock[id] or 0)) or nil
                local rows,cost,complete=E.MaterialPurchases(id,demand[id],{
                    offers=materialVendorOffers(id),auction=auctionQuote(id) and j.snap.prices[id] or nil,
                    supply=supply,available=remaining,faction=j.snap.faction},tick)
                if complete and cost<entry.cost-1e-7 then replacements[id]=rows end
            end
        end
        if next(replacements) then
            local revised,inserted={},{}
            for _,a in ipairs(selected) do
                local rows=a.type=="buy" and replacements[a.item]
                if rows then
                    if not inserted[a.item] then
                        for _,row in ipairs(rows) do
                            revised[#revised+1]=stampStock({type="buy",item=a.item,count=row.count,cost=row.cost,
                                source=row.source,npcID=row.npcID,reason=a.reason,owner=a.owner,url=row.url,
                                bundleSize=row.bundleSize or 1,bundlePrice=row.bundlePrice or row.unit,
                                estimated=row.estimated,reference=row.reference,quoteSource=row.quoteSource,
                                priceSource=row.priceSource,priceBasis=row.priceBasis,verifiedAt=row.verifiedAt},row)
                        end
                        inserted[a.item]=true
                    end
                else revised[#revised+1]=a end
                tick()
            end
            local candidate=replay(revised)
            if candidate and (not requireGoal or goalsComplete(j,candidate)) and better(candidate,t) then t=candidate end
        end
        t.batched=true
        return t
    end
    local function rebuildSkeleton(first)
        local skel=opts.routeSkeleton
        local blocked=E.StepsHaveNIP(skel.steps) and "catalogueFiltered" or nil
        if not opts.allowSecondaryLeveling then
            for _,step in ipairs(skel.steps) do
                if step.profession and step.profession~=slug then blocked="secondaryDisabled";break end
            end
        end
        if blocked then
            fail(blocked)
            j.status="recalculate_required";j.searchTermination="skeleton_rejected";j.exhausted=true
            j.result=S.Result(j,nil,j.status);j.finished=true
            return
        end
        local events,seen={},{}
        local balance,demand={},{}
        j.skeletonFormulas={}
        for id in pairs(first.inv) do balance[id]=available(first,id) end
        local function input(id,n)
            balance[id]=(balance[id] or 0)-n
            demand[id]=max(demand[id] or 0,-balance[id])
        end
        local valid=true
        for _,step in ipairs(skel.steps) do
            local p=step.profession or slug
            if not seen[p] then
                if first.skill[p]==nil then fail("professionMissing",{profession=p});valid=false end
                first.skill[p]=step[1];first.progress[p]=step.fromProgress or 0;seen[p]=true
            end
            local event={step=step,inputs={},outputs={}}
            if step.kind=="specialization_quest" then
                for _,goal in ipairs(j.snap.specializationGoals or {}) do
                    if goal.id==step.goalID and goal.questID==step.questID and goal.abilityID==step.abilityID then
                        event.goal=goal;event.inputs=goal.inputs;break
                    end
                end
                if not event.goal then fail("specializationChanged");valid=false end
            elseif step.kind=="essence_conversion" then
                local c=essenceConversion(step.targetItem)
                if c and c.inputItemID==step.sourceItem then
                    event.conversion=c;event.inputs={{c.inputItemID,c.inputCount*step[4]}}
                    event.outputs={{c.outputItemID,c.outputCount*step[4]}}
                else fail("executionInvalid");valid=false end
            elseif not step.checkpoint then
                local r=j.snap.byKey[p..":"..step[3]]
                event.recipe=r
                local f=r and j.formulaByRecipe[r.key]
                if f and not f.known and f.source=="ah" then j.skeletonFormulas[f.id or r.key]=f.id end
                if not r then fail("clientDataPending",{spell=step[3],profession=p});valid=false
                else
                    for _,m in ipairs(r.mats) do event.inputs[#event.inputs+1]={m[1],m[2]*step[4]} end
                    local usable=p==slug or j.purchasePriced[r.item]
                    if r.item and usable then event.outputs={{r.item,r.count*step[4]}} end
                end
            end
            for _,m in ipairs(event.inputs) do input(m[1],m[2]) end
            for _,m in ipairs(event.outputs) do balance[m[1]]=(balance[m[1]] or 0)+m[2] end
            events[#events+1]=event;tick()
        end
        for _,goal in ipairs(j.snap.toolGoals or {}) do
            demand[goal.item]=max(demand[goal.item] or 0,1-(balance[goal.item] or 0))
        end
        local bySegment,assigned={},{}
        for i,event in ipairs(events) do bySegment[event.step.segmentID]={index=i,event=event} end
        for i,event in ipairs(events) do
            local outputUse={}
            for _,edge in ipairs(event.step.allocations or {}) do
                local target=bySegment[edge.consumerID]
                local tool=type(edge.consumerID)=="string" and edge.consumerID=="tool:"..tostring(edge.itemID)
                local produced=0
                for _,m in ipairs(event.outputs) do if m[1]==edge.itemID then produced=produced+m[2] end end
                outputUse[edge.itemID]=(outputUse[edge.itemID] or 0)+edge.count
                if not tool and (not target or target.index<=i) or outputUse[edge.itemID]>produced then
                    fail("executionInvalid");valid=false
                elseif target then
                    local inputs=0
                    for _,m in ipairs(target.event.inputs) do if m[1]==edge.itemID then inputs=inputs+m[2] end end
                    local key=edge.consumerID..":"..edge.itemID
                    assigned[key]=(assigned[key] or 0)+edge.count
                    if assigned[key]>inputs then fail("executionInvalid");valid=false end
                end
            end
        end
        j.skeletonDemand=demand;first.skeletonBought={}
        local current=valid and first or nil
        for _,event in ipairs(events) do
            if not current then break end
            local step=event.step;local p=step.profession or slug
            if current.skill[p]~=step[1] or step.fromProgress~=nil and math.abs((current.progress[p] or 0)-step.fromProgress)>1e-6 then
                fail("executionInvalid");current=nil;break
            end
            if event.recipe then
                local r=event.recipe
                if (current.skill[p] or 0)<r.learn then fail("skillRequired",r);current=nil;break end
                local winner
                craft(current,r,step[4],step.reason or "level",{},function(t) if better(t,winner) then winner=t end end)
                current=winner
            elseif event.goal then
                local goal=event.goal
                if goalBlocked(goal,current) or (current.skill[p] or 0)<(goal.minSkill or 0) then
                    fail("specializationChanged");current=nil;break
                end
                local winner
                quest(current,goal,function(t) if better(t,winner) then winner=t end end)
                current=winner
            elseif event.conversion then
                local c=event.conversion;local winner
                acquire(current,c.inputItemID,c.inputCount*step[4],"essence",{},function(t)
                    winner=convert(t,c,step[4])
                end)
                current=winner
            elseif step.checkpoint then
                current=clone(current);current.skill[p]=step[2];current.progress[p]=0
                log(current,{type="gather",profession=p,from=step[1],to=step[2],count=0,spell=step[3],reason=step.reason})
            end
            if current and (current.skill[p]~=step[2]
                or step.toProgress~=nil and math.abs((current.progress[p] or 0)-step.toProgress)>1e-6) then
                fail("executionInvalid");current=nil
            end
            tick()
        end
        if current then
            for _,goal in ipairs(j.snap.toolGoals or {}) do
                local winner
                procureTool(current,goal,function(t) winner=t end)
                if not winner then current=nil;break end
                current=winner
            end
        end
        j.seedDone=true;j.searchTermination="skeleton_rebuilt";restrict(j,"saved_route")
        local status=skel.status=="complete" and "complete" or skel.status=="stopped" and "stopped" or "interrupted"
        if current and skel.status=="complete" and not goalsComplete(j,current) then
            fail("executionInvalid");current=nil
        end
        j.status=current and status or "recalculate_required"
        j.best=current and goalsComplete(j,current) and current or nil
        j.preview=current
        j.result=S.Result(j,j.best,j.status)
        if not current then
            j.result.steps=E.Copy(skel.steps);j.result.executionSteps=E.Copy(skel.steps)
            j.result.costComplete=false;j.result.completeCost=false;j.result.priced=false
        end
        j.finished=true
        return "done"
    end
    j.co=coroutine.create(function()
        j.snap=E.Capture(slug,opts,tick)
        j.auctionSupply=E.ConsiderAuctionSupply(j.snap) and j.snap.auctionSupply or {}
        if not E.ConsiderAuctionSupply(j.snap) and E.FormulaAuctionSupplyOf then
            for id in pairs(j.snap.formulaItems or {}) do
                local supply=E.FormulaAuctionSupplyOf(j.snap,id)
                if supply then j.auctionSupply[id]=supply end
            end
        end
        j.seedSkill=opts.start or (j.snap.professions[slug] or {}).cur or 1
        j.recovery=not opts.procurementDemands and (opts.scheme==nil or opts.scheme=="cheapest")
            and j.snap.recovery and j.snap.recovery.enabled and ns.ProfRecovery and ns.ProfRecovery.StateRevenue and true or false
        j.hasFiniteSupply=next(j.auctionSupply)~=nil
        if not opts.start then opts.start=(j.snap.professions[slug] or {}).cur or 1 end
        local context=j.snap.routeContext or E.RouteContext(slug,opts,j.snap.professions)
        j.specializationConflict=slug=="engineering" and j.target>=200 and
            j.snap.specializationContext and j.snap.specializationContext.selectionConflict
        if context.requiresPartner and not context.partnerValid then
            fail("secondaryRequired"); j.exhausted=true; j.searchTermination="exhausted"; j.status="infeasible"
            j.result=S.Result(j,nil,j.status)
            j.finished=true
            return "done"
        end
        j.formulaByRecipe={}
        for _,r in ipairs(j.snap.recipes) do j.formulaByRecipe[r.key]=E.FormulaFor(r,j.snap);tick() end
        j.purchasePriced={}
        for id in pairs(j.snap.prices) do if auctionQuote(id) then j.purchasePriced[id]=true end; tick() end
        for id,offers in pairs(j.snap.offers) do
            for _,o in ipairs(offers) do if vendorQuote(o) then j.purchasePriced[id]=true; break end end
            tick()
        end
        if j.snap.essenceConversions and ns.ProfEssences then
            for _,pair in ipairs(ns.ProfEssences.Pairs()) do
                if j.purchasePriced[pair.lesserID] or j.purchasePriced[pair.greaterID] then
                    j.purchasePriced[pair.lesserID]=true;j.purchasePriced[pair.greaterID]=true
                end
            end
        end
        opts.exclusions=opts.exclusions or E.GetPolicies(slug)
        local first=initial(j.snap,slug,opts,tick)
        if opts.routeSkeleton then return rebuildSkeleton(first) end
        j.reusable={}; j.values={}
        local reachable={}
        for id in pairs(first.inv) do if available(first,id)>0 then reachable[id]=true end end
        for id,available in pairs(j.snap.vendorItems or {}) do if available then reachable[id]=true end end
        for id,price in pairs(j.snap.prices) do if auctionQuote(id) then reachable[id]=true end end
        for id,offers in pairs(j.snap.offers) do for _,o in ipairs(offers) do
            if o.unlimited and o.price and not o.hasExtendedCost and o.purchasable~=false
                and (not o.currencyID or o.currencyID==0) then reachable[id]=true end
        end end
        local function ingredientsReachable(r)
            for _,m in ipairs(r.mats) do if not reachable[m[1]] then return false end end
            return true
        end
        for _=1,#j.snap.recipes+1 do
            local changed=false
            if j.snap.essenceConversions and ns.ProfEssences then
                for _,pair in ipairs(ns.ProfEssences.Pairs()) do
                    if reachable[pair.lesserID] or reachable[pair.greaterID] then
                        if not reachable[pair.lesserID] or not reachable[pair.greaterID] then changed=true end
                        reachable[pair.lesserID]=true;reachable[pair.greaterID]=true
                    end
                end
            end
            for _,r in ipairs(j.snap.recipes) do
                if r.item and not reachable[r.item] and ingredientsReachable(r) then reachable[r.item]=true; changed=true end
                tick()
            end
            if not changed then break end
        end
        local relevant={}; local levelRoots={}
        local function visit(r)
            if relevant[r.key] or not ingredientsReachable(r) then return end
            relevant[r.key]=true
            for _,m in ipairs(r.mats) do
                j.reusable[m[1]]=true
                for _,producer in ipairs(j.snap.byItem[m[1]] or {}) do visit(producer) end
                local c=essenceConversion(m[1])
                if c then
                    j.reusable[c.inputItemID]=true
                    for _,producer in ipairs(j.snap.byItem[c.inputItemID] or {}) do visit(producer) end
                end
            end
        end
        for _,r in ipairs(j.snap.recipes) do
            if r.profession==slug and r.grey>opts.start and r.learn<j.target and ingredientsReachable(r) then
                levelRoots[#levelRoots+1]=r; visit(r)
            elseif r.profession==slug and r.grey>opts.start and r.learn<j.target then
                for _,m in ipairs(r.mats) do
                    if not reachable[m[1]] then
                        local supply=j.auctionSupply[m[1]]
                        fail(supply and supply.quantity<m[2] and "auctionSupplyLimited"
                            or "materialUnavailable",r,m[1],m[2],supply and supply.quantity)
                    end
                end
            elseif opts.allowSecondaryLeveling and r.profession~=slug then visit(r) end
            tick()
        end
        for _,goal in ipairs(j.snap.toolGoals or {}) do
            j.reusable[goal.item]=true
            for _,r in ipairs(j.snap.byItem[goal.item] or {}) do if r.profession==goal.profession then visit(r) end end
        end
        for _,goal in ipairs(j.snap.specializationGoals or {}) do
            for _,m in ipairs(goal.inputs) do
                j.reusable[m[1]]=true
                for _,r in ipairs(j.snap.byItem[m[1]] or {}) do if r.profession==goal.profession then visit(r) end end
            end
        end
        if j.snap.essenceConversions and ns.ProfEssences then
            for _,pair in ipairs(ns.ProfEssences.Pairs()) do
                if j.reusable[pair.lesserID] or j.reusable[pair.greaterID] then
                    j.reusable[pair.lesserID]=true;j.reusable[pair.greaterID]=true
                end
            end
        end
        j.terminalItems={}
        if j.recovery then
            local consumed={}
            for _,r in ipairs(j.snap.recipes) do
                for _,m in ipairs(r.mats) do consumed[m[1]]=true end
                if r.toolItem then consumed[r.toolItem]=true end
                tick()
            end
            for id in pairs(j.snap.retainedToolItems or {}) do consumed[id]=true end
            for _,goal in ipairs(j.snap.toolGoals or {}) do consumed[goal.item]=true end
            for _,goal in ipairs(j.snap.specializationGoals or {}) do for _,m in ipairs(goal.inputs) do consumed[m[1]]=true end end
            if j.snap.essenceConversions and ns.ProfEssences then
                for _,pair in ipairs(ns.ProfEssences.Pairs()) do
                    if consumed[pair.lesserID] or consumed[pair.greaterID] then
                        consumed[pair.lesserID]=true;consumed[pair.greaterID]=true
                    end
                end
            end
            for id,q in pairs(j.snap.recovery.quotes or {}) do
                if not consumed[id] and not q.missing and type(q.unit)=="number" then j.terminalItems[id]=true end
            end
        end
        local ids={}; for id in pairs(j.reusable) do ids[#ids+1]=id; j.values[id]=0 end
        for _=1,24 do
            local changed=false
            for _,id in ipairs(ids) do
                local value=j.snap.prices[id] or math.huge
                if j.snap.nonAuctionable[id] then value=math.huge end
                for _,o in ipairs(j.snap.offers[id] or {}) do
                    if o.unlimited and o.price and not o.hasExtendedCost and o.purchasable~=false
                        and (not o.currencyID or o.currencyID==0) then
                        value=min(value,o.price/(o.quantity or o.bundleSize or 1))
                    end
                end
                for _,r in ipairs(j.snap.byItem[id] or {}) do
                    if relevant[r.key] then
                    local cost=0; for _,m in ipairs(r.mats) do cost=cost+(j.values[m[1]] or 0)*m[2] end
                    value=min(value,cost/r.count)
                    end
                end
                if essenceConversion(id) then value=0 end
                if value==math.huge then value=0 end
                if value>(j.values[id] or 0)+1e-9 then j.values[id]=value; changed=true end
                tick()
            end
            if not changed then break end
        end
        j.profitRecipes={}
        if j.recovery then
            for _,r in ipairs(j.snap.recipes) do
                local q=r.item and j.snap.recovery.quotes[r.item]
                local cost=0
                for _,m in ipairs(r.mats) do cost=cost+(j.values[m[1]] or 0)*m[2] end
                if q and (q.unit or 0)*(r.count or 1)>cost then j.profitRecipes[r.key]=true end
                tick()
            end
        end
        local point=math.huge
        for _,r in ipairs(levelRoots) do
            if r.grey>opts.start and r.learn<j.target then
                local net=-(r.item and (j.values[r.item] or 0)*r.count or 0)
                for _,m in ipairs(r.mats) do net=net+(j.values[m[1]] or 0)*m[2] end
                point=min(point,max(0,net))
            end
        end
        j.pointBound=(slug=="mining" or point==math.huge) and 0 or point*.99999
        local function rememberPrefix(t)
            local previous=j.partial
            if t and (not previous or t.skill[slug]>previous.skill[slug]
                or (t.skill[slug]==previous.skill[slug] and (completedGoals(t)>completedGoals(previous)
                    or completedGoals(t)==completedGoals(previous) and better(t,previous)))) then
                j.partial=t
            end
        end
        local function publishPrefix(t)
            if not t or t.skill[slug]<=first.skill[slug] and completedGoals(t)==0 then return end
            local failures,restricted,restriction=j.failures,j.restricted,j.restrictedReason
            j.failures={}
            local preview=batchPlan(t,false)
            j.failures,j.restricted,j.restrictedReason=failures,restricted,restriction
            if preview and (not j.preview or preview.skill[slug]>j.preview.skill[slug]
                or (preview.skill[slug]==j.preview.skill[slug] and (completedGoals(preview)>completedGoals(j.preview)
                    or completedGoals(preview)==completedGoals(j.preview) and better(preview,j.preview)))) then
                j.preview=preview;j.previewPublishCpu=cpuTime()
                j.result=S.Result(j,nil,"searching");coroutine.yield("publish")
            end
        end
        local function solveEssenceFixedSteps(fixedSteps,restriction)
            local pending,memo={},{}
            local sequence=0
            local function enqueue(state,index,attempts)
                if not state or pruned(state) or j.budgetLimited then return end
                local key=index..":"..attempts..":"..stateKey(state,j.reusable,j.recovery,j.terminalItems)
                local old=memo[key];local cost=objective(state,j.recovery and j.snap or nil)
                if old and (old.cost<cost-1e-7 or math.abs(old.cost-cost)<1e-7
                    and (old.money<state.money-1e-7 or math.abs(old.money-state.money)<1e-7
                        and old.switches<=(state.switches or 0))) then return end
                if #pending>=j.frontierLimit then j.budgetLimited=true;j.searchTermination="frontier_limit";return end
                sequence=sequence+1
                memo[key]={cost=cost,money=state.money,switches=state.switches or 0,token=sequence}
                pending[#pending+1]={state=state,index=index,attempts=attempts,key=key,token=sequence}
            end
            local function dueTools(state,emit)
                for _,goal in ipairs(j.snap.toolGoals or {}) do
                    if not state.completedToolGoals[goal.id] and state.skill[slug]>=goal.minSkill then
                        procureTool(state,goal,function(t) dueTools(t,emit) end)
                        return
                    end
                end
                emit(state)
            end
            enqueue(first,1,0)
            while #pending>0 and not j.budgetLimited do
                local node=table.remove(pending)
                if memo[node.key].token==node.token then
                    j.expanded=j.expanded+1
                    dueTools(node.state,function(state)
                        rememberPrefix(state)
                        local step=fixedSteps[node.index]
                        if not step then
                            local prepared=batchPlan(state,false)
                            if prepared then
                                if goalsComplete(j,prepared) and better(prepared,j.best) then j.best=prepared end
                                if not j.preview or better(prepared,j.preview) then j.preview=prepared end
                            end
                            return
                        end
                        local r=j.snap.byKey[(step.profession or slug)..":"..step[3]]
                        if not r then fail("clientDataPending",{key=tostring(step[3]),spell=step[3]});return end
                        local n=ceil(step[4] or 0)
                        local skillGoal=min(j.target,step[2] or 0)
                        local leveling=not step.preserveCount and skillGoal>(step[1] or 0)
                        if leveling and state.skill[r.profession]>=skillGoal or not leveling and node.attempts>=n then
                            enqueue(state,node.index+1,0);return
                        end
                        if node.attempts>=10000 or leveling and E.Gain(r,state.skill[r.profession])<=0 then fail("levelGap",r);return end
                        craft(state,r,1,step.reason or (leveling and "level" or "material"),{},function(t)
                            enqueue(t,node.index,node.attempts+1)
                        end)
                    end)
                end
                if opts.maxNodes and j.expanded>=opts.maxNodes and #pending>0 then
                    j.budgetLimited=true;j.searchTermination="node_limit"
                end
                tick()
            end
            if not j.best and j.partial then publishPrefix(j.partial) end
            j.exhausted=not j.budgetLimited;restrict(j,restriction or "fixed_route")
            j.searchTermination=j.searchTermination or (restriction=="strategy_route" and "strategy_complete" or "fixed")
            j.status=j.best and "complete" or j.preview and "incomplete" or "infeasible"
            j.result=S.Result(j,j.best,j.status);j.finished=true
            return "done"
        end
        if opts.fixedSteps and j.snap.essenceConversions then return solveEssenceFixedSteps(opts.fixedSteps,"fixed_route") end
        if opts.fixedSteps then
            local current=executeSteps(opts.fixedSteps,first,rememberPrefix)
            if current then
                local prepared=batchPlan(current,false)
                if prepared then j.preview=prepared;if goalsComplete(j,prepared) then j.best=prepared end end
            end
            j.exhausted=true;restrict(j,"fixed_route");j.searchTermination="fixed"
            j.status=j.best and "complete" or j.preview and "incomplete" or "infeasible"
            j.result=S.Result(j,j.best,j.status)
            j.finished=true
            return "done"
        end
        local function seed(direct,smooth)
            local current=first; j.seeding=true; j.directSeed=direct;j.smoothSeed=smooth
            j.seedAborted=false
            j.seedDeadline=smooth and cpuTime()+450
                or not direct and cpuTime()+300 or nil
            local checkpoint=first.skill[slug]
            while current and not goalsComplete(j,current) do
                local nextState
                j.collectFailures={}
                expand(current,slug,j.target,{},function(t)
                    if (t.skill[slug]>current.skill[slug] or t.skill[slug]==current.skill[slug]
                        and (t.progress[slug] or 0)>(current.progress[slug] or 0)
                        or completedGoals(t)>completedGoals(current))
                        and better(t,nextState) then nextState=t end
                end,true)
                if not nextState and not j.seedAborted
                    and (not j.blockedSkill or current.skill[slug]>=j.blockedSkill) then
                    j.blockers={}
                    j.blockedSkill=current.skill[slug]
                    for _,d in pairs(j.collectFailures) do j.blockers[#j.blockers+1]=d end
                end
                j.collectFailures=nil
                rememberPrefix(nextState)
                if j.referenceSeed and nextState and nextState.lastRecipe then j.referenceRecipes[nextState.lastRecipe]=true end
                if direct and not smooth and nextState and not goalsComplete(j,nextState)
                    and (not j.preview or nextState.skill[slug]>=checkpoint+15)
                    and (not j.previewPublishCpu or cpuTime()-j.previewPublishCpu>=200) then
                    publishPrefix(nextState); checkpoint=nextState.skill[slug]
                end
                if j.seedAborted then current=nil; break end
                current=nextState
                if current then j.seedSkill=max(j.seedSkill or 1,current.skill[slug] or 1) end
                tick()
            end
            j.seedDeadline=nil; j.seedAborted=false;j.smoothSeed=nil
            if direct and not smooth and (not current or not goalsComplete(j,current)) then publishPrefix(current or j.partial) end
            return current
        end
        j.phase="initial_seed"
        local current=seed(not opts.specializationRecipeScore)
        if current and goalsComplete(j,current) then current=batchPlan(current,true) end
        j.seedDone=true
        if current then
            j.initialTotal=current.money; j.initialObjective=objective(current,j.recovery and j.snap or nil)
            j.initialNetTotal=current.money-(j.recovery and ns.ProfRecovery.StateRevenue(current,j.snap) or 0)
            j.best=current
            if not opts.specializationRecipeScore and not opts.procurementDemands
                and current.skill[slug]>first.skill[slug] then
                local failures=j.failures
                j.failures={}
                for _,mode in ipairs(j.recovery and {"purchase","net"} or {"purchase"}) do
                    if cpuTime()>=j.cpuLimitMs*.72 then break end
                    local restricted,restriction=j.restricted,j.restrictedReason
                    j.phase="smooth_seed"
                    local smooth=seed(true,mode)
                    if smooth and goalsComplete(j,smooth) then smooth=batchPlan(smooth,true) end
                    if smooth and goalsComplete(j,smooth) and better(smooth,current) then
                        current=smooth;j.best=current;j.improvements=(j.improvements or 0)+1
                    else j.restricted,j.restrictedReason=restricted,restriction end
                end
                j.failures=failures
            end
            j.best=current
            j.result=S.Result(j,current,"searching"); coroutine.yield("publish")
        end
        if opts.specializationRecipeScore then
            if j.snap.essenceConversions and j.best then
                local selected={}
                for _,a in ipairs(actions(j.best)) do
                    if a.type=="craft" and a.profession==slug and a.reason=="level" then
                        selected[#selected+1]={a.from,a.to,a.spell,a.count,profession=a.profession,
                            preserveCount=true,reason=a.reason}
                    end
                end
                if #selected>0 then
                    j.seeding=false;j.directSeed=false
                    return solveEssenceFixedSteps(selected,"strategy_route")
                end
            end
            j.seeding=false;j.directSeed=false;restrict(j,"strategy_route");j.exhausted=true;j.searchTermination="strategy_complete"
            j.status=j.best and "complete" or (j.partial and "incomplete" or "infeasible")
            if not j.best and j.partial then publishPrefix(j.partial) end
            j.result=S.Result(j,j.best,j.status);j.finished=true;return "done"
        end
        if not current and opts.referenceFallback~=false then
            j.referenceSeed=true
            j.referenceRecipes={}
            local reference=seed(true)
            if reference then publishPrefix(reference) end
            j.referenceSeed=false
            if j.preview and goalsComplete(j,j.preview) and uncertainty(j.preview)==0 then
                current=j.preview;j.best=current; j.initialTotal=j.preview.money; j.initialObjective=objective(j.preview,j.recovery and j.snap or nil)
                j.initialNetTotal=j.preview.money-(j.recovery and ns.ProfRecovery.StateRevenue(j.preview,j.snap) or 0)
                j.result=S.Result(j,j.best,"searching"); coroutine.yield("publish")
            end
        end
        j.phase="refined_seed"
        local refined=cpuTime()<j.cpuLimitMs*.82 and seed(false) or nil
        if refined and goalsComplete(j,refined) then refined=batchPlan(refined,true) end
        if refined and goalsComplete(j,refined) and better(refined,j.best) then
            current=refined; j.best=refined; j.improvements=(j.improvements or 0)+1
        elseif not current then current=refined end
        j.seeding=false; j.directSeed=false
        if current and goalsComplete(j,current) then
            j.best=current; j.initialTotal=j.initialTotal or current.money
            j.initialObjective=j.initialObjective or objective(current,j.recovery and j.snap or nil)
            j.initialNetTotal=j.initialNetTotal or current.money-(j.recovery and ns.ProfRecovery.StateRevenue(current,j.snap) or 0)
            j.result=S.Result(j,current,"searching"); coroutine.yield("publish")
        end
        if not current and j.partial and (j.partial.skill[slug]>first.skill[slug] or completedGoals(j.partial)>0) then
            publishPrefix(j.partial)
            j.result=S.Result(j,nil,"searching"); coroutine.yield("publish")
        end
        if not stable and not j.recovery and not opts.procurementDemands
            and (opts.scheme==nil or opts.scheme=="cheapest") and cpuTime()<j.cpuLimitMs*.72 then
            local alternatives=false
            for _,r in ipairs(j.snap.recipes) do
                if r.green<r.grey and r.green<(r.profession==slug and j.target or 300)
                    and r.grey>(first.skill[r.profession] or 300) then alternatives=true;break end
            end
            if alternatives then
                local stableOpts=E.Copy(opts,nil,{snapshot=false})
                stableOpts.snapshot=j.snap;stableOpts.scheme="stable";stableOpts.anytime=false
                stableOpts.cpuLimitMs=max(1,(j.cpuLimitMs-cpuTime())*.5)
                local candidateJob=S.NewJob(slug,stableOpts)
                local previous,failures=nil,j.failures
                j.phase="stable_candidate";j.comparingStable=true
                repeat
                    candidateJob.tickClockStride=j.tickClockStride
                    local done=S.Run(candidateJob,max(.1,(j.deadline or clock()+2)-clock()),j.tickClockStride~=nil)
                    if candidateJob.best and candidateJob.best~=previous then
                        previous=candidateJob.best;j.failures={}
                        local restricted,restriction=j.restricted,j.restrictedReason
                        local candidate=batchPlan(clone(previous),true)
                        if candidate and j.rebatchFinal then candidate=j.rebatchFinal(candidate) end
                        j.failures=failures
                        if candidate and goalsComplete(j,candidate) and better(candidate,j.best) then
                            if candidateJob.restricted then restrict(j,candidateJob.restrictedReason) end
                            j.best=candidate;j.improvements=(j.improvements or 0)+1
                            j.initialTotal=j.initialTotal or candidate.money
                            j.initialObjective=j.initialObjective or candidate.money
                            j.result=S.Result(j,candidate,"searching");coroutine.yield("publish")
                        else j.restricted,j.restrictedReason=restricted,restriction end
                    end
                    if done then break end
                    tick()
                until candidateJob.error
                j.comparingStable=nil
            end
        end
        j.phase="frontier"
        local heap={}; local memo={}; local serial=0
        local function less(a,b)
            if stable and a.state.risk and b.state.risk then local risk=R.Compare(a.state.risk,b.state.risk);if risk~=0 then return risk<0 end end
            if math.abs(a.score-b.score)>1e-7 then return a.score<b.score end
            local sa,sb=a.state,b.state
            if sa.skill[slug]~=sb.skill[slug] then return sa.skill[slug]>sb.skill[slug] end
            if sa.switches~=sb.switches then return sa.switches<sb.switches end
            return a.serial<b.serial
        end
        local function push(t)
            if pruned(t,true) then return end
            if j.budgetLimited then return end
            local key=stateKey(t,j.reusable,j.recovery,j.terminalItems); local old=memo[key]
            local cost=objective(t,j.recovery and j.snap or nil)
            if old and (old.cost<cost-1e-7 or math.abs(old.cost-cost)<1e-7
                and (old.money<t.money-1e-7 or math.abs(old.money-t.money)<1e-7 and old.switches<=t.switches)) then return end
            if #heap>=j.frontierLimit then j.budgetLimited=true;j.searchTermination="frontier_limit";return end
            if not old then j.memoStates=(j.memoStates or 0)+1 end
            memo[key]={cost=cost,money=t.money,switches=t.switches,
                token=j.tickClockStride and (serial+1) or nil}
            serial=serial+1; local entry={state=t,score=bound(t),serial=serial,key=key}; local i=#heap+1
            if j.tickClockStride then entry.memoToken=serial end
            while i>1 do local parent=floor(i/2); if not less(entry,heap[parent]) then break end; heap[i]=heap[parent]; i=parent end
            heap[i]=entry;j.frontierStates=#heap
        end
        local function pop()
            local top=heap[1]; local tail=table.remove(heap)
            if #heap>0 then
                local i=1
                while i*2<=#heap do
                    local child=i*2; if child<#heap and less(heap[child+1],heap[child]) then child=child+1 end
                    if not less(heap[child],tail) then break end
                    heap[i]=heap[child]; i=child
                end
                heap[i]=tail
            end
            j.frontierStates=#heap
            return top
        end
        push(first)
        while #heap>0 do
            local entry=pop(); local t=entry.state; j.expanded=j.expanded+1
            if goalsComplete(j,t) then
                local batched=batchPlan(t,true)
                if batched and better(batched,j.best) then j.best=batched; j.improvements=(j.improvements or 0)+1; j.result=S.Result(j,batched,"searching"); coroutine.yield("publish") end
            elseif not pruned(t,true) then
                local known=memo[entry.key]
                local currentMemo
                if j.tickClockStride and entry.memoToken then
                    currentMemo=known and known.token==entry.memoToken
                else
                    local cost=objective(t,j.recovery and j.snap or nil)
                    currentMemo=known and math.abs(cost-known.cost)<1e-7
                        and math.abs(t.money-known.money)<1e-7 and t.switches==known.switches
                end
                if currentMemo then
                    local emitted=false
                    local collect=t.skill[slug]>=(j.blockedSkill or first.skill[slug])
                    if collect then j.collectFailures={} end
                    expand(t,slug,j.target,{},function(u) emitted=true;rememberPrefix(u);push(u) end,false)
                    if collect then
                        if not emitted then
                            j.blockedSkill=t.skill[slug];j.blockers={}
                            for _,failure in pairs(j.collectFailures) do j.blockers[#j.blockers+1]=failure end
                        end
                        j.collectFailures=nil
                    end
                end
            end
            if j.budgetLimited then break end
            if opts.maxNodes and j.expanded>=opts.maxNodes and #heap>0 then j.budgetLimited=true;j.searchTermination="node_limit";break end
            tick()
        end
        j.exhausted=not j.budgetLimited; j.searchTermination=j.budgetLimited and j.searchTermination or "exhausted"
        j.status=j.best and (uncertainty(j.best)==0 and "complete" or "incomplete") or (j.partial and (j.partial.skill[slug]>first.skill[slug] or completedGoals(j.partial)>0) and "incomplete" or "infeasible")
        if not j.best and j.partial then publishPrefix(j.partial) end
        if not j.best then for _,d in pairs(j.failures) do if d.code=="clientDataPending" or d.code=="materialUnavailable" or d.code=="outputConflict" or d.code=="availabilityUnknown" then j.status="incomplete"; break end end end
        j.result=S.Result(j,j.best,j.status)
        j.finished=true
        return "done"
    end)
    return j
end
function S.ChargeExternalWork(j,elapsed)
    elapsed=tonumber(elapsed)
    if not j or not elapsed or elapsed~=elapsed or elapsed<=0 or elapsed==math.huge then return end
    j.cpuUsed=(j.cpuUsed or 0)+elapsed
    j.externalCpuUsed=(j.externalCpuUsed or 0)+elapsed
    S.RefreshStatus(j)
end
local function qualityBudgetDue(j)
    local opts=j.opts or {}
    if j.finalizing or j.finished or not j.seedDone or j.comparingStable
        or opts.fixedSteps or opts.procurementDemands
        or opts.specializationRecipeScore or opts.anytime==false
        or (opts.snapshot and opts.anytime~=true) then return false end
    if j.best and goalsComplete(j,j.best) and not j.firstFeasibleCpuMs then
        j.firstFeasibleCpuMs=j.cpuUsed or 0
    end
    local extra=tonumber(opts.postFeasibleCpuMs) or max(1500,min(3500,(j.cpuLimitMs or 8000)*.35))
    extra=max(200,min(4000,extra))
    return j.firstFeasibleCpuMs
        and (j.cpuUsed or 0)-j.firstFeasibleCpuMs>=extra or false
end
local function finalize(j,status)
    j.comparingStable=nil
    j.status=status
    j.phase="finalize"
    j.finalizing=true
    j.finalizeProgress=j.finalizeProgress or 0
    j.co=coroutine.create(function()
        j.result=S.Result(j,j.best,status)
        j.finalizing=nil;j.finished=true
        return "done"
    end)
end
function S.Run(j,budget,deferStatus)
    if j.finished or j.cancelled or j.status=="stopped" and not j.finalizing or coroutine.status(j.co)=="dead" then
        S.RefreshStatus(j);return true
    end
    local start=clock();j.sliceStart=start;j.deadline=start+(budget or 2)
    j.tickClockCountdown=0
    local phase=j.phase or (j.finalizing and "finalize" or not j.snap and "capture" or "initial_seed")
    local before=j.cpuUsed
    if not j.finalizing and qualityBudgetDue(j) then
        j.budgetLimited=true;j.searchTermination="quality_budget"
        finalize(j,uncertainty(j.best)==0 and "complete" or "incomplete")
    end
    local function completingSeed() return j.phase=="initial_seed" and j.seeding and j.directSeed and not j.seedDone and not j.opts.procurementDemands end
    if not j.finalizing and not completingSeed() and j.cpuUsed>=j.cpuLimitMs then
        j.budgetLimited=true;j.searchTermination="cpu_limit"
        finalize(j,j.best and (uncertainty(j.best)==0 and "complete" or "incomplete") or "incomplete")
    end
    local ok,why=coroutine.resume(j.co)
    local elapsed=max(0,clock()-start)
    if ok and j.status~="searching" and coroutine.status(j.co)~="dead" then j.finalizing=true end
    if not ok then
        j.status="error";j.searchTermination="error";j.failures.error={code="solverError",detail=tostring(why)}
        j.error=why
        if j.finalizing then j.finished=true;j.finalizing=nil
        else finalize(j,"error") end
    elseif not j.finalizing and qualityBudgetDue(j)
        and coroutine.status(j.co)~="dead" then
        j.budgetLimited=true;j.searchTermination="quality_budget"
        finalize(j,uncertainty(j.best)==0 and "complete" or "incomplete")
    elseif not j.finalizing and not completingSeed() and max(before,j.cpuUsed)+elapsed>=j.cpuLimitMs and coroutine.status(j.co)~="dead" then
        j.budgetLimited=true;j.searchTermination="cpu_limit"
        finalize(j,j.best and (uncertainty(j.best)==0 and "complete" or "incomplete") or "incomplete")
    end
    local delta=max(0,clock()-start)
    j.phaseCpuMs[phase]=(j.phaseCpuMs[phase] or 0)+delta
    j.cpuUsed=max(before,j.cpuUsed)+delta;j.sliceStart=nil
    local done=j.finished or coroutine.status(j.co)=="dead"
    if done then j.finalizing=nil;j.finalizeProgress=1 end
    if done and j.result then j.result.phaseCpuMs=E.Copy(j.phaseCpuMs) end    if done or not j.progressAt or clock()-j.progressAt>=200 then
        j.progressAt=clock();j.progressVersion=(j.progressVersion or 0)+1
    end
    if done or not deferStatus then S.RefreshStatus(j) end
    return done
end
function S.Compute(slug,opts)
    local j=S.NewJob(slug,opts)
    while coroutine.status(j.co)~="dead" and not j.finished and (j.status~="error" or j.finalizing) do S.Run(j,1000) end
    return j.result or S.Result(j,j.best,j.status),j
end
function S.NewProcurementJob(snapshot,demands,opts)
    opts=E.Copy(opts or {},nil,{snapshot=false})
    opts.snapshot=E.Copy(snapshot,nil,{recipes={},specializationGoals={},toolGoals={},professions={},known={},byKey={},byItem={},byProfession={}})
    if opts.referenceFallback==nil then opts.referenceFallback=false end
    for _,r in ipairs(snapshot.recipes or {}) do opts.snapshot.recipes[#opts.snapshot.recipes+1]=r end
    local totals={}
    if type(demands)=="table" and type(demands[1])=="table" then
        for _,entry in ipairs(demands) do
            local id,n=entry.id or entry[1],entry.count or entry.need or entry[2]
            assert(type(id)=="number" and id>0 and id==floor(id) and type(n)=="number" and n>=0 and n==floor(n),"invalid procurement demand")
            totals[id]=(totals[id] or 0)+n
        end
    else for id,n in pairs(demands or {}) do
        assert(type(id)=="number" and id>0 and id==floor(id) and type(n)=="number" and n>=0 and n==floor(n),"invalid procurement demand")
        totals[id]=(totals[id] or 0)+n
    end end
    local ids={};for id,n in pairs(totals) do if n>0 then ids[#ids+1]=id end end;table.sort(ids)
    local mats={};for _,id in ipairs(ids) do mats[#mats+1]={id,totals[id]} end
    opts.procurementDemands=totals
    opts.snapshot.recipes[#opts.snapshot.recipes+1]={profession="__purchase",spell=2147483647,learn=1,yellow=2,green=2,grey=2,count=1,mats=mats,cooldown=false}
    opts.snapshot.professions=E.Copy(snapshot.professions); opts.snapshot.professions.__purchase={cur=1,max=300}
    opts.snapshot.known=E.Copy(snapshot.known); opts.snapshot.known["__purchase:2147483647"]=true
    opts.start=1; opts.target=2
    return S.NewJob("__purchase",opts)
end
function S.ProcureMany(snapshot,demands,opts)
    local j=S.NewProcurementJob(snapshot,demands,opts)
    if opts and opts.defer then return nil,j end
    while coroutine.status(j.co)~="dead" and not j.finished and (j.status~="error" or j.finalizing) do S.Run(j,1000) end
    return j.result or S.Result(j,j.best,j.status),j
end
function S.Procure(snapshot,id,count,opts)
    return S.ProcureMany(snapshot,{[id]=count},opts)
end
