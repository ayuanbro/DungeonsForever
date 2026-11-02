-- Integer procurement and chronological, resumable route search.
local _,ns=...
if not ns.LoadForeverPages then return end
local E=ns.ProfEconomy
local S={}; ns.ProfRouteSolver=S
S.ProcurementPolicyVersion=8
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
-- learned and unusableSeed are initialized once and never mutated by a branch.
-- DF_REBATCH_SAFE_FINALIZE_AND_FLAT_STATE_V14
-- Solver state fields hold scalar leaves. Deep copying every diagnostic's
-- immutable nested record at each branch is unnecessary and costly.
-- Preserve independent outer maps, while keeping their immutable values.
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
        greenLevelCrafts=s.greenLevelCrafts,money=s.money,log=s.log,switches=s.switches or 0,lastRecipe=s.lastRecipe,
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
local function log(s,a) s.log={prev=s.log,action=a} end
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
    -- Explicit continuation supplies a current bag snapshot. Ordinary route
    -- previews do not silently discount their cost using character inventory.
    local ids={}; for id in pairs(opts.executionInventory or {}) do if type(id)=="number" then ids[#ids+1]=id end end
    table.sort(ids)
    for _,id in ipairs(ids) do
        local entry=opts.executionInventory[id]
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
    -- Sale value depends on every finished crafted remainder and its origin.
    -- Equal total inventory can contain different purchased/crafted quantities.
    for id,n in pairs(t.inv) do if n>0 and not (terminal and terminal[id]) and (recovery or not reusable or reusable[id]) then
        parts[#parts+1]="i"..id.."="..n..":"..(t.unusable[id] or 0)..(recovery and (":"..(t.produced[id] or 0)..":"..(t.unusableSeed[id] or 0)..":"..(t.priorityProduced[id] or 0)) or "")
    end end
    if recovery then for key,n in pairs(t.profitMade) do parts[#parts+1]="profit:"..key.."="..n end end
    parts[#parts+1]="green="..(t.greenLevelCrafts or 0)
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
    if not state or state.skill[job.slug]<job.target then return false end
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
    -- Coverage records every rejected candidate visited by the search. Only
    -- failures at the actual stopping frontier explain why this result stopped.
    -- A missing recipe that was bypassed, is now grey, or was excluded cannot
    -- turn a later stock/price failure into a learning-data failure.
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
-- Progress is deliberately scalar: callers need not rebuild or serialize a plan.
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
        searchFrontierLimit=job.frontierLimit,finalizing=job.finalizing and true or false,
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
    stampReserve(job,result,status)
    if job.snap and job.snap.auctionPriceInputs then
        result.auctionPriceInputs=E.Copy(job.snap.auctionPriceInputs)
    end
    stampFreshResult(result,job.snap,coroutine.running()==job.co and job.tick or nil)
    E.SummarizeAuctionSupply(result,job.snap)
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
    return S.RefreshStatus(job,result,status)
end
function S.Result(job,state,status)
    -- A blocked future rank or missing quote must not hide the usable prefix.
    -- Keep the full-goal incumbent separate so it remains a valid pruning bound.
    local prefix=job.preview or (job.partial and job.partial.batched and job.partial)
    local partial=not state and prefix and (prefix.skill[job.slug]>(job.opts.start or 1) or completedGoals(prefix)>0)
    if partial then state=prefix; partial=not goalsComplete(job,state) end
    -- BEGIN DF_REBATCH_FINAL_ONLY_V2
    -- Do not use replay optimization during quick seed, search, or preview.
    -- It may run ONCE, only for the final incumbent, after search termination.
    local finalStatus = status or job.status
    if state and state == job.best and not job.rebatchFinalized
        and (finalStatus == "complete" or finalStatus == "incomplete")
        and job.rebatchFinal and coroutine.running()==job.co then
        job.rebatchFinalized = true
        local previousPhase,finalizing=job.phase,job.finalizing
        job.phase="rebatch";job.finalizing=true
        local candidate = job.rebatchFinal(state)
        job.phase=previousPhase;job.finalizing=finalizing
        if candidate and candidate ~= state then
            state = candidate
            job.best = candidate
            job.resultState = nil
            job.resultCache = nil
        end
    end
    -- END DF_REBATCH_FINAL_ONLY_V2
    if state and job.resultState==state and job.resultCache then
        stampReserve(job,job.resultCache,status)
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
    out.seedInventory=E.Copy(job.opts.executionInventory or {})
    out.scheme=job.opts.scheme or "cheapest"
    out.greenLevelCrafts=state and state.greenLevelCrafts or 0
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
    out.plannedTo=state and state.skill[job.slug] or out.start
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
    -- Learning/availability warnings are independent of the quoted gold cost.
    -- Keep them in diagnostics without presenting known prices as missing.
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
    for _,a in ipairs(out.actions) do
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
        resultTick(job)
        a.id=tostring(i)..":"..tostring(a.profession or "")..":"..tostring(a.spell or a.item or 0)
        local dependencies={}; local dependencySet={}
        for _,input in ipairs(a.inputs or {}) do
            local need=input[2]
            local pool=provenance[input[1]] or {}
            local heads=provenanceHeads[input[1]] or {1,1};provenanceHeads[input[1]]=heads
            -- Match consume(): purchased/verified opening stock is spent first,
            -- preserving only genuinely crafted final leftovers for sale.
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
                -- Anonymous suppliers may sell different transaction sizes or
                -- prices. Only identical quotations share a receipt row.
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
            -- Conversion is a physical inventory operation, never a profession
            -- craft or a sale-producing byproduct. Its purchases belong to the
            -- eventual recipe; this row only records the required manual work.
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
            -- A tool is retained, not consumed. Its producer still has a real
            -- output obligation, including when its recipe is already grey.
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
    for _,step in ipairs(out.executionSteps) do
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
    for _,step in ipairs(out.executionSteps) do
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
    -- The page lists each recipe once; execution retains chronological segments.
    local grouped={}
    for _,step in ipairs(out.executionSteps) do
        resultTick(job)
        local key=(step.checkpoint or step.kind=="specialization_quest" or step.kind=="essence_conversion") and step.actionID or (step.profession..":"..step[3])
        local row=grouped[key]
        if not row then
            row=E.Copy(step);row.requiredOutputs=E.Copy(step.requiredOutputs);row.allocations={}
            for _,allocation in ipairs(step.allocations) do row.allocations[#row.allocations+1]=E.Copy(allocation) end
            row.segments={};row.segmentIDs={};grouped[key]=row;out.steps[#out.steps+1]=row;row.stepIndex=#out.steps
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
    -- Only the crafted quantity still in inventory may be sold; own stock isn't revenue.
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
        -- Keep the demand sink for the final economic replay after removing
        -- its synthetic craft from the player's execution/action lists.
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
-- BEGIN DF_REBATCH_CHRONOLOGICAL_V2
-- The solver still chooses the recipes and buys. This bounded, post-solve pass
-- only changes execution order after a full replay proves equivalent results.
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

local function rebatchEquivalent(a, b)
    if not a or not b or math.abs((a.money or 0) - (b.money or 0)) > 1e-7 then return false end
    if (b.greenLevelCrafts or 0)>(a.greenLevelCrafts or 0) then return false end
    if a.rebatchGreenCrafts~=nil and (b.rebatchGreenCrafts or 0)>a.rebatchGreenCrafts then return false end
    for _, key in ipairs({"inv", "unusable", "unusableSeed", "produced", "priorityProduced", "profitMade",
            "cap", "ahUsed", "formulaPaid", "specializationAbilities",
            "completedSpecializationGoals", "completedToolGoals"}) do
        if not rebatchSameMap(a[key], b[key]) then return false end
    end
    -- A reordered sequence may legitimately gain more skill earlier. Reject
    -- any loss of completed skill or fractional progress at the same skill.
    if not rebatchSameKeys(a.skill, b.skill) then return false end
    for profession, oldSkill in pairs(a.skill or {}) do
        local newSkill = b.skill[profession]
        if type(oldSkill) ~= "number" or type(newSkill) ~= "number"
            or newSkill < oldSkill then return false end
        if newSkill == oldSkill and (b.progress and b.progress[profession] or 0) + 1e-7
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

local function rebatchStages(list, recipes, rebuild)
    local stages, skill = {}, {}
    for _, a in ipairs(list) do
        if a.profession and skill[a.profession]==nil then skill[a.profession]=a.from end
    end
    local first, opening = 1, copyStateMap(skill)
    local function close(last)
        if last>=first then stages[#stages+1]={first,last} end
        first=last+1;opening=copyStateMap(skill)
    end
    for i,a in ipairs(list) do
        local key=rebatchKey(a)
        if key then
            local r=recipes and recipes[key]
            -- A known recipe can still require skill earned in this stage.
            if not rebuild and r and r.learn>(opening[a.profession] or a.from or 0) then close(i-1) end
            skill[a.profession]=a.to or skill[a.profession]
            -- Keep rank transitions separate even when no trainer action is logged.
            for _,cap in ipairs({75,150,225}) do
                if (a.from or 0)<cap and (a.to or 0)>=cap then close(i);break end
            end
        elseif a.type~="buy" and not (rebuild and a.type=="formula") then
            close(i-1)
            if a.profession and a.to then skill[a.profession]=a.to end
            first=i+1;opening=copyStateMap(skill)
        end
    end
    close(#list)
    return stages
end

local function rebatchDependencies(list, checkpoint)
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
            -- Same purchased-first allocation as consume() and S.Result.
            for pass=1,2 do
                local lots=pool[pass] or {head=1}
                while need>0 and lots.head<=#lots do
                    local lot=lots[lots.head];local n=min(need,lot.count)
                    if n>0 then edge(lot.index,i);origins[#origins+1]=lot.index end
                    lot.count=lot.count-n;need=need-n
                    if lot.count<=0 then lots.head=lots.head+1 end
                end
            end
            -- Consumers of one shared lot may trade places. Crossing a lot
            -- boundary must retain its original allocation, including seeds.
            local single=#origins==1 and need==0 and origins[1] or nil
            local previous=consumers[m[1]]
            if not previous or not single or previous.single~=single then
                for _,index in ipairs(previous or {}) do edge(index,i) end
                previous={single=single};consumers[m[1]]=previous
            end
            previous[#previous+1]=i
            edge(lastBuy[m[1]],i)
        end
        if a.type=="buy" or a.type=="seed" then
            -- A later purchase must not displace crafted stock already
            -- allocated to an earlier consumer.
            for _,index in ipairs(consumers[a.item] or {}) do edge(index,i) end
            consumers[a.item]=nil -- The purchase now orders all earlier consumers.
            if a.usableOutput~=false then add(a.item,a.count,i,false) end
        elseif a.usableOutput~=false then
            for _,m in ipairs(a.outputs or {}) do add(m[1],m[2],i,a.type=="craft") end
        end
        if rebatchKey(a) and a.reason and a.reason~="material" then
            edge(lastLevel,i);lastLevel=i
        end
    end
    return edges
end

local function rebatchStageOrder(list, edges, lo, hi, checkpoint)
    local remaining, done, ready, byKey = {}, {}, {}, {}
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
    for i=lo,hi do remaining[i]=0 end
    for i=lo,hi do
        if not checkpoint() then return end
        for to in pairs(edges[i]) do if to<=hi then remaining[to]=remaining[to]+1 end end
    end
    for i=lo,hi do if remaining[i]==0 then release(i) end end
    local out, previous = {}, nil
    for _=lo,hi do
        if not checkpoint() then return end
        local index=peek(byKey.buy) or (previous and peek(byKey[previous])) or peek(ready)
        if not index then return end
        done[index]=true;out[#out+1]=list[index]
        previous=rebatchKey(list[index]) or previous
        for to in pairs(edges[index]) do if to<=hi then
            remaining[to]=remaining[to]-1
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
        -- The shopping list acquires these inputs before crafting. Moving the
        -- purchases still requires the same complete stock/cost replay below.
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

function S.RebatchChronological(original, replay, tick, cpuTime, recipes, grayMaterials)
    if not original or type(replay) ~= "function" then return original end
    local list = actions(original)
    if #list < 3 or #list > 1600 then return original end
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
    -- Final-result only. Keep the optional improvement bounded regardless of
    -- route size and the number of non-improving rearrangements examined.
    local maxAttempts = #list > 600 and 3 or #list > 200 and 6 or 12
    local maxProbes = #list > 600 and 18 or #list > 200 and 36 or 96
    local probes = 0
    local useCPU = type(cpuTime)=="function"
    local started = useCPU and cpuTime()
        or (type(debugprofilestop)=="function" and debugprofilestop() or nil)
    local function timeExceeded()
        if not started then return false end
        return (useCPU and cpuTime() or debugprofilestop()) - started
            >= (useCPU and 60 or 200)
    end
    local work=0
    local function checkpoint()
        work=work+1
        if work%64==0 then if tick then tick() end;return not timeExceeded() end
        return true
    end
    local stages=rebatchStages(list,recipes,grayMaterials)
    local edges=grayMaterials and {} or rebatchDependencies(list,checkpoint)
    if not edges then return original end
    local currentScore = rebatchSwitches(list)
    local order=list
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
        if tick then tick() end
        local candidate=replay(candidateOrder)
        if rebatchEquivalent(best,candidate) then
            local score=rebatchSwitches(actions(candidate))
            if score<currentScore then best,order,currentScore=candidate,candidateOrder,score;return end
        end
        -- One unsafe skill interval must not prevent independent stages from
        -- batching. Refine only rejected ranges, within the existing budget.
        local middle=floor((lo+hi)/2)
        improve(lo,middle);improve(middle+1,hi)
    end
    improve(1,#list)
    return best
end
-- END DF_REBATCH_CHRONOLOGICAL_V2

function S.NewJob(slug,opts)
    opts=opts or {}
    local j={slug=slug,opts=opts,target=min(300,max(1,floor(opts.target or 300))),expanded=0,failures={},cpuUsed=0,cpuLimitMs=max(1,tonumber(opts.cpuLimitMs) or 8000),status="searching",generation=0,progressVersion=0,resultVersion=0,frontierLimit=max(1,floor(tonumber(opts.maxFrontier) or 20000))}
    j.phase, j.phaseCpuMs = "capture", {}
    j.seedLeafPrices = {}
    j.workCounters = {fastSeedPurchases=0,fastSeedCrafts=0,seedCraftComparisons=0,
        seedCandidateTrials=0,leafQuoteHits=0,seedQuoteCalls=0,
        batchedPlans=0,batchReuses=0,replayCalls=0}
    local stable=opts.scheme=="stable"
    local function better(a,b)
        if stable and b and (uncertainty(a)==0)==(uncertainty(b)==0)
            and a.greenLevelCrafts~=b.greenLevelCrafts then return a.greenLevelCrafts<b.greenLevelCrafts end
        return betterState(a,b,j.recovery and j.snap or nil)
    end
    local function countGreen(state,recipe,reason,gain)
        if stable and gain>0 and (reason=="level" or reason=="secondary")
            and state.skill[recipe.profession]>=recipe.green then
            state.greenLevelCrafts=state.greenLevelCrafts+1
        end
    end
    local ops=0
    local function cpuTime()
        return j.cpuUsed+(j.sliceStart and max(0,clock()-j.sliceStart) or 0)
    end
    local function tick()
        ops=ops+1
        if j.seedDeadline and cpuTime()>=j.seedDeadline then j.seedAborted=true end
        if ops>=1000 or (j.deadline and clock()>=j.deadline) then ops=0; coroutine.yield("work") end
    end
    j.tick=tick
    -- Eligibility changes only at learn/grey thresholds, not at every skill.
    -- Cache one ordered list per interval; dynamic policies/fees/specialization
    -- remain checked by allowed()/prepare() for every branch.
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
        -- Current net cost is useful for ordering, but future sales can lower
        -- it. It is deliberately never used as a pruning lower bound.
        if j.recovery then return objective(s,j.snap) end
        local credit=0
        for id,n in pairs(s.inv) do credit=credit+(j.values and j.values[id] or 0)*n end
        local remaining=max(0,j.target-(s.skill[slug] or 1)-(s.progress[slug] or 0))
        return s.money+max(0,(j.pointBound or 0)*remaining-credit)
    end
    local function pruned(s,complete)
        -- Batch scheduling has its own objective: fewer recipe switches. Its
        -- freshly quoted ledger may cost more than the search incumbent.
        if j.batchRecipes then return false end
        -- A more expensive prefix can produce a cheaper final net route. No
        -- safe bound on its eventual sale income has been established.
        if j.recovery then return false end
        if not j.best then return false end
        if uncertainty(j.best)>0 then return false end
        if uncertainty(s)>0 then return true end
        if stable and s.greenLevelCrafts~=j.best.greenLevelCrafts then
            return s.greenLevelCrafts>j.best.greenLevelCrafts
        end
        -- Inside reagent acquisition, inputs may already be reserved for an
        -- unfinished parent. Only complete frontier states admit this heuristic.
        local lower=complete and bound(s) or s.money
        return lower>j.best.money+1e-7 or (math.abs(lower-j.best.money)<1e-7 and (s.switches or 0)>=(j.best.switches or 0))
    end
    local function allowed(r,s,reason)
        local p=E.Policy(j.opts.exclusions,r)
        if p=="ban" or (p=="level" and reason~="material") then fail("excluded",r,r.item); return false end
        -- Material lookups may encounter a future producer that levelRecipes()
        -- would omit. Its learning data cannot block this skill when prepare()
        -- cannot reach its required level in the current acquisition branch.
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
                -- Suppliers with the same indivisible pack and quote certainty
                -- have identical future procurement effects. Keep the cheapest;
                -- retain different packs and reliable/estimated alternatives.
                -- The snapshot still exposes every supplier for display.
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
        -- Unquoted inputs must actually be made by the target profession.
        -- Secondary leveling byproducts remain surplus, never a shortcut past
        -- the own-profession recipe's availability and learning requirements.
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
        -- A verified reference price is a known quote in the reference-price
        -- model. Unqualified vendor caches still make the cost incomplete.
        if estimated and not (offer and offer.reference) then diagnostic(t,"vendor:"..id..":"..tostring(npc),"vendorEstimate",id) end
        if unpriced then diagnostic(t,source..":"..id,source=="vendor" and "vendorPriceUnknown" or "materialPriceUnknown",id) end
        return t
    end
    -- DF_ROUTE_ANYTIME_SEED_AND_FRAME_V15
    -- Warm-start procurement is permitted to use one executable, fully priced
    -- source combination. Exhaustive make/buy/split enumeration remains intact
    -- in the refined seed and frontier; this only accelerates the first route.
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
                    -- Finite AH stock can cover a non-integral pack remainder.
                    if auctionPrice and ahRemaining > 0 then
                        local ah = min(missing, ahRemaining)
                        local remainder = missing - ah
                        if remainder > 0 then
                            local n = ceil(remainder / size) * size
                            consider(ah * auctionPrice + n / size * price,
                                uncertain, ah, offer, n, ah + n - missing)
                        end
                        -- With one unlimited NPC pack and an AH unit price,
                        -- the minimum mixed cost lies at a pack-count endpoint.
                        -- The last required pack may reduce the AH need: e.g.
                        -- need=4, pack=3, AH cap=2 => vendor3 + AH1 (not AH2).
                        local packs = ceil(max(0, missing - ahRemaining) / size)
                        if packs > 0 then
                            local n = packs * size
                            local onlyAH = max(0, missing - n)
                            if onlyAH > 0 and onlyAH <= ahRemaining then
                                consider(onlyAH * auctionPrice + packs * price,
                                    uncertain, onlyAH, offer, n, onlyAH + n - missing)
                            end
                        end
                        -- The other endpoint is the last partial pack before
                        -- a full-vendor purchase. Necessary when AH alone is
                        -- sufficient but mixing one pack lowers the cost.
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
    -- Constant-time warm-seed cost envelope from relaxed material values.
    -- The executable route still validates every make/buy choice; this quote
    -- is only a ranking hint and never creates materials or learning rights.
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
        if f.automatic then return t end -- Granted by profession skill; no separate learning purchase/action.
        if f.source=="ah" and j.auctionSupply[f.id] then t.ahUsed[f.id]=(t.ahUsed[f.id] or 0)+1 end
        if f.unpriced then diagnostic(t,"formula:"..tostring(key),"formulaPriceUnknown",f.id or r.key) end
        if f.availabilityUncertain then diagnostic(t,"formulaStock:"..tostring(key),"formulaStockUnknown",f.id or r.key) end
        log(t,{type="formula",item=f.id,count=f.bundleSize or 1,cost=f.cost or 0,source=f.source,owner=r.key,unpriced=f.unpriced,formula=E.Copy(f)})
        return t
    end
    local function prepare(r,s,reason,path,emit)
        local usable,learning=allowed(r,s,reason)
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
        if prepared then emit(prepared) end
        local f=learning and learning.quote or j.formulaByRecipe[r.key]
        if f and not f.known and f.source=="ah" and j.auctionSupply[f.id]
            and not s.formulaPaid[f.id or r.key] and auctionRemaining(s,f.id)>=1 then
            -- Paying a little more at a vendor can reserve the last auction
            -- copy for a later reagent. It is a search branch, not a greedy
            -- decision made once for the whole recipe catalogue.
            local alternative=stateFormula(r,s,0)
            if alternative and alternative.usable and alternative.source=="vendor" then
                local t=learnFormula(s,r,alternative,learning)
                if t then emit(t) end
            end
        end
        if f and not f.known and f.source=="vendor" and f.availabilityUncertain
            and f.ahPrice and auctionRemaining(s,f.id)>=1 and not s.formulaPaid[f.id or r.key] then
            -- A limited shelf is a reference, while a quoted auction copy can
            -- provide a complete route. Explore both before uncertainty pruning.
            local alternative=stateFormula(r,s,auctionRemaining(s,f.id),"ah")
            if alternative and alternative.usable and alternative.source=="ah" then
                local t=learnFormula(s,r,alternative,learning)
                if t then emit(t) end
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
    craft=function(s,r,n,reason,path,emit)
        tick(); if j.seedAborted or pruned(s) then return end
        prepare(r,s,reason,path,function(base)
            local function reagents(t,i)
                tick()
                if j.seedAborted then return end
                local m=r.mats[i]
                if m then
                    local inputPath=E.Copy(path); inputPath.owner=r.key
                    acquire(t,m[1],m[2]*n,"material",inputPath,function(u)
                        -- Reserve immediately. A later nested producer must not consume
                        -- this parent's already allocated stock a second time.
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
                    -- Grey material crafting is allowed at the current rank.
                    -- Incidental gains do not justify buying a higher rank.
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
                    expectedGain=t.skill[p]-from+(t.progress[p] or 0)-fromProgress})
                if not pruned(t) then emit(t) end
            end
            reagents(base,1)
        end)
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
            -- Acquire the entire parent batch at once, using the producer
            -- selected for this stage. Never interleave one parent at a time.
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
        -- Compare direct purchase against a bounded set of executable
        -- processing chains; frontier exploration retains exact splits.
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
                    if allowed(r,s,"material") then
                        local u=E.Copy(used);u[r.key]=true
                        trials=trials+1
                        j.workCounters.seedCraftComparisons=j.workCounters.seedCraftComparisons+1
                        craft(s,r,candidate.count,"material",pth,function(t)
                            if available(t,id)>=need and better(t,selected) then selected=t end
                        end)
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
            -- Every integer split competes with buying the requested form.
            -- A pair lock prevents recursive split/combine cycles while the
            -- remaining target demand is filled; leftovers persist in inv.
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
                    -- Enumerate pack counts and fill the remainder using other sources.
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
        -- Missing quotes are not zero-price purchases. Resolve them through
        -- the target profession even in the first seed; every leaf must price.
        if not path[id] and (not j.directSeed or not auctionPriced or remaining<missing) then
            local pth=E.Copy(path); pth[id]=true
            for _,r in ipairs(j.snap.byItem[id] or {}) do
                if j.seedAborted then return end
                local materialProfession=opts.materialProfession or slug
                local own=path.ownProfessionOnly and r.profession==path.ownProfessionOnly
                    or not path.ownProfessionOnly and (j.purchasePriced[id] or r.profession==materialProfession or materialProfession=="__purchase")
                if own and not used[r.key] and allowed(r,s,"material") then
                    had=true; local u=E.Copy(used); u[r.key]=true
                    local limit=ceil(missing/r.count)
                    for n=1,limit do
                        if j.seedAborted then return end
                        if (not j.directSeed or n==limit) and (not j.seeding or n==1 or n==limit) then
                        craft(s,r,n,"material",pth,function(t) acquire(t,id,need,reason,path,emit,u) end)
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
        -- The first route needs one feasible ledger, just like ordinary leveling.
        -- Enumerating every buy/craft split here can consume the entire search
        -- budget before the first quest transition is ever emitted. The later
        -- frontier still compares complete combinations and shared leftovers.
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
                -- DF_ROUTE_LEAF_QUOTE_CACHE_V15
                -- Immutable, unconstrained raw-material quotes only. These
                -- depend on missing quantity, not the current route state.
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
                    -- A failed quote can be cycle-dependent. Only cache a
                    -- finite upper bound, never an infinite path-specific miss.
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
                -- A failed lookup through a cycle is path-dependent. Do not
                -- memoize that failure and hide a valid alternative entry.
                if best<math.huge or not cyclic then quoteCache[key]=best end
                if best==math.huge and j.collectFailures and not j.seedAborted then
                    fail(j.auctionSupply[id] and auctionRemaining(s,id)<missing
                        and "auctionSupplyLimited" or "materialUnavailable",nil,id,missing,auctionRemaining(s,id))
                end
                return best,cyclic
            end
            for _,r in ipairs(levelRecipes(p,s.skill[p])) do
                local sk=s.skill[p]
                if r.learn<=sk and sk<r.grey and allowed(r,s,"level")
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
                        -- Rank one attempt by continuous expected gain. Material
                        -- values amortize vendor packs instead of oscillating
                        -- between a new pack and its apparently free leftovers.
                        -- This is only a warm-start heuristic: craft/acquire and
                        -- the final replay still charge every actual purchase.
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
                    candidates[#candidates+1]={recipe=r,count=n,estimate=estimate,rate=rate}
                    -- A scarce green recipe may provide only part of an
                    -- expected skill point. Preserve that progress so another
                    -- recipe can complete it instead of discarding the stock.
                    if j.hasFiniteSupply and n>1 then
                        local partialCost=0
                        if f and not f.known and not s.formulaPaid[f.id or r.key] then partialCost=f.cost or 0 end
                        for _,m in ipairs(r.mats) do partialCost=partialCost+quote(m[1],m[2]) end
                        candidates[#candidates+1]={recipe=r,count=1,estimate=partialCost*n}
                    end
                end
                tick()
            end
            table.sort(candidates,function(a,b)
                if stable then
                    local ag=s.skill[p]>=a.recipe.green
                    local bg=s.skill[p]>=b.recipe.green
                    if ag~=bg then return not ag end
                end
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
                    and (directTrials>=3 or candidate.estimate>=selected.money-s.money-1e-7) then break end
                if candidate.estimate<math.huge or not j.directSeed then
                    directTrials=directTrials+1
                    j.workCounters.seedCandidateTrials=j.workCounters.seedCandidateTrials+1
                    local winner
                    craft(s,candidate.recipe,candidate.count,p==slug and "level" or "secondary",path,function(t)
                        if (t.skill[p]>s.skill[p] or t.skill[p]==s.skill[p] and (t.progress[p] or 0)>(s.progress[p] or 0))
                            and better(t,winner) then winner=t end
                    end)
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
            if r.learn<=sk and sk<r.grey and allowed(r,s,"level") then
                any=true
                local g=E.Gain(r,sk)
                local n=greedy and max(1,ceil((1-(s.progress[p] or 0))/max(.000001,g)-1e-7)) or 1
                craft(s,r,n,p==slug and "level" or "secondary",path,emit)
            end
            tick()
        end
        -- The guide's gathering checkpoints are not zero-price alternatives to smelting.
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
        -- Secondary levelling groups attempts into an expected-point block.
        restrict(j,"secondary_point_blocks")
    end
    -- Keep the search's chronology. Moving every occurrence of a recipe to its
    -- first occurrence changes skill gains and can turn later leveling into waste.
    local function batchPlan(raw,requireGoal)
        -- A validated replay already carries normalized acquisition lots.
        -- Reprocessing it cannot improve this fixed action ledger.
        if raw and raw.batched and (not requireGoal or goalsComplete(j,raw)) then
            j.workCounters.batchReuses=j.workCounters.batchReuses+1
            return raw
        end
        j.workCounters.batchedPlans=j.workCounters.batchedPlans+1
        local original=actions(raw)
        local function replay(list,start)
            j.workCounters.replayCalls=j.workCounters.replayCalls+1
            local t=start or initial(j.snap,slug,opts)
            local greenCrafts=t.rebatchGreenCrafts or 0
            t.diagnostics={}
            local active={}
            for _,a in ipairs(list) do if a.type=="craft" then active[a.profession..":"..a.spell]=true end end
            for _,a in ipairs(list) do
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
                            if rec then local accepted,_,value=E.RouteRecipeEligibility(rec,j.snap,t);ok,detail=accepted,value end
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
                    if not goal or available(t,goal.item)<1 or (t.skill[goal.profession] or 0)<goal.minSkill then return end
                    t=finishTool(t,goal)
                elseif a.type=="specialization_quest" then
                    local goal=a.quest
                    if not goal or t.completedSpecializationGoals[goal.id] or (t.skill[goal.profession] or 0)<(goal.minSkill or 0)
                        or goalBlocked(goal,t) then return end
                    for _,m in ipairs(goal.inputs) do if available(t,m[1])<m[2] then return end end
                    for _,m in ipairs(goal.inputs) do consume(t,m[1],m[2]) end
                    t=finishGoal(t,goal)
                elseif a.type=="craft" then
                    local r=j.snap.byKey[a.profession..":"..a.spell]
                    if not r or not allowed(r,t,a.reason) or (t.skill[r.profession] or 0)<r.learn then return end
                    local n=a.count;local from=t.skill[r.profession];local progressFrom=t.progress[r.profession] or 0
                    for _,m in ipairs(r.mats) do if available(t,m[1])<m[2]*n then return end end
                    t=learnFormula(t,r);if not t then return end
                    local inputs={}
                    for _,m in ipairs(r.mats) do inputs[#inputs+1]={m[1],m[2]*n};consume(t,m[1],m[2]*n) end
                    local gainSum=0
                    for _=1,n do
                        local gain=E.Gain(r,t.skill[r.profession])
                        if gain>0 and t.skill[r.profession]>=(t.cap[r.profession] or 300) then
                            if a.reason=="level" or a.reason=="secondary" then t=rank(t,r.profession) else gain=0 end
                        end
                        countGreen(t,r,a.reason,gain)
                        if gain>0 and (a.reason=="level" or a.reason=="secondary")
                            and t.skill[r.profession]>=r.green then greenCrafts=greenCrafts+1 end
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
                        reason=a.reason,usableOutput=usable})
                end
                tick()
            end
            t.rebatchGreenCrafts=greenCrafts
            return t
        end
        local function rebuildBatches(candidate)
            local list=actions(candidate)
            -- Recompute whole recipe batches, as in master's range plans, while
            -- retaining native skill, learning, rank and task boundaries.
            local stages=rebatchStages(list,j.snap.byKey)
            local ranges={};for _,range in ipairs(stages) do ranges[range[1]]=range[2] end
            local current=initial(j.snap,slug,opts)
            local function stage(first,last)
                local groups,byKey,byItem,used,goals={},{},{},{},{}
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
                    end
                end
                if #groups==0 then return current end
                local roots={}
                j.batchRecipes={}
                for _,g in ipairs(groups) do
                    local r=g.recipe
                    if r.item and used[r.item] then j.batchRecipes[r.item]=r end
                    -- An intermediate's incidental skill will be replayed by
                    -- its consumer. Keep independent leveling and leftover
                    -- outputs as explicit roots of the stage.
                    if not r.item or not used[r.item] or g.produced>used[r.item] then roots[#roots+1]=g end
                end
                if #roots==0 then return end -- Cyclic materials require chronology.
                local lastRoot={};for _,g in ipairs(roots) do lastRoot[g.recipe.profession]=g end
                for _,g in ipairs(roots) do
                    local r=g.recipe;local goal=g.goal
                    if lastRoot[r.profession]==g then goal=max(goal,goals[r.profession] or 0) end
                    local minimum=g.reason=="material" and g.count or 0
                    -- A later stage may depend on these outputs, including a
                    -- tool or quest. Do not trim its promised material batch.
                    for i=last+1,#list do
                        local a=list[i]
                        if a.type=="tool_goal" and a.item==r.item then minimum=max(minimum,g.count) end
                        for _,m in ipairs(a.inputs or a.quest and a.quest.inputs or {}) do
                            if m[1]==r.item then minimum=max(minimum,g.count) end
                        end
                    end
                    local base=current
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
                        -- The producer also raises skill before the consumer.
                        -- Recompute the required count against that actual order.
                        while low<high do
                            local middle=floor((low+high)/2);local probe=trial(middle)
                            if reached(probe) then high=middle;chosen=probe else low=middle+1 end
                            tick()
                        end
                    end
                    if not chosen then return end
                    current=chosen
                end
                for p,goal in pairs(goals) do if (current.skill[p] or 0)<goal then return end end
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
                    -- Recipes learn through craft/prepare with the current
                    -- quote. Other checkpoints retain their real dependencies.
                    if a.type~="formula" and a.type~="buy" then
                        current=replay({a},clone(current));if not current then return end
                    end
                    i=i+1
                end
                tick()
            end
            local verified=replay(actions(current))
            if not verified or not goalsComplete(j,verified) or uncertainty(verified)>uncertainty(candidate) then return end
            if stable and (verified.greenLevelCrafts or 0)>(candidate.greenLevelCrafts or 0) then return end
            if rebatchSwitches(actions(verified))>=rebatchSwitches(list) then return end
            verified.batched=true
            return verified
        end
        local first=replay(original)
        if not first then fail("executionInvalid");return end
        -- Cache the verified replay function, not a reordered candidate.
        -- Search seeds, previews and frontier nodes must NEVER pay for rebatching.
        if not j.rebatchFinal then
            j.rebatchFinal = function(candidate)
                if opts.fixedSteps or opts.procurementDemands or opts.preserveRecipeOrder then
                    return candidate
                end
                local failures, collected = j.failures, j.collectFailures
                local restricted, restriction = j.restricted, j.restrictedReason
                j.failures, j.collectFailures = {}, nil
                local seeding,direct,aborted=j.seeding,j.directSeed,j.seedAborted
                j.seeding=true;j.directSeed=true;j.seedAborted=false
                local rebuilt=rebuildBatches(candidate)
                j.batchRecipes=nil;j.seeding,j.directSeed,j.seedAborted=seeding,direct,aborted
                -- A cutoff may hand us a raw search state instead of a replay.
                -- Count green leveling attempts for every scheme, not only stable.
                local baseline=candidate.rebatchGreenCrafts~=nil and candidate or replay(actions(candidate))
                local result = rebuilt or baseline and rebatchEquivalent(candidate,baseline)
                    and S.RebatchChronological(baseline, replay, tick, cpuTime, j.snap.byKey)
                -- Already-gray intermediates can be prepared across later
                -- recipe unlocks without changing gains, counts or budgets.
                -- This also gathers small bolt batches for different products.
                if result then
                    local seen,last,split={},nil,false
                    for _,a in ipairs(actions(result)) do
                        local key=rebatchKey(a);local r=key and j.snap.byKey[key]
                        if key then
                            if r and a.reason=="material" and (a.from or 0)>=r.grey then
                                if seen[key] and last~=key then split=true;break end
                                seen[key]=true
                            end
                            last=key
                        end
                    end
                    if split then result=S.RebatchChronological(result,replay,tick,cpuTime,j.snap.byKey,true) end
                end
                j.failures, j.collectFailures = failures, collected
                j.restricted, j.restrictedReason = restricted, restriction
                if rebuilt then restrict(j,"batch_execution") end
                return result or candidate
            end
        end
        local trace=actions(first);local need,keep,quantities,owners,needOwner={},{},{},{},{}
        local changed=false
        -- Positive fractional skill is useful even when the integer range is 195–195.
        -- Other crafts survive only when a retained later consumer needs their output.
        for i=#trace,1,-1 do
            local a=trace[i]
            if a.type=="craft" then
                local used=a.usableOutput~=false and a.item and (need[a.item] or 0)>0
                local useful=(a.expectedGain or 0)>1e-9 or used or a.profession=="__purchase"
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
        end
        local selected={}
        for i,a in ipairs(trace) do if keep[i] then
            local event=E.Copy(a)
            if quantities[i] then event.cost=event.cost*quantities[i]/event.count;event.count=quantities[i] end
            if owners[i] then event.owner=owners[i] end
            selected[#selected+1]=event
        end end
        local t=replay(selected)
        if not t or (requireGoal and not goalsComplete(j,t)) then fail("executionInvalid");return end
        if changed then restrict(j,"chronological_replay_reduction") end
        -- A one-craft seed compares one AH item with an entire NPC pack and
        -- can repeat the more expensive unit purchase for hundreds of crafts.
        -- Requote the selected route's total external demand before publishing
        -- it, including when a strategy or search budget stops further search.
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
        -- Minimum cumulative external stock at each consumer preserves crafted
        -- intermediates, verified seed inventory, tool reservations and surplus.
        local base=initial(j.snap,slug,opts)
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
    -- Adapt master's RebuildFromSkel to native execution segments. This is a
    -- linear recipe replay with fresh procurement, not a route search. In
    -- particular, acquire() cannot invent replacement crafts or conversions.
    local function rebuildSkeleton(first)
        local skel=opts.routeSkeleton
        if E.StepsHaveNIP(skel.steps) then
            fail("catalogueFiltered")
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
        -- Allocation edges are part of the saved route choice. Validate them
        -- against today's recipe/quest inputs before admitting a reconstruction.
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
            -- Keep the entire chosen route reviewable. Never silently drop a
            -- missing recipe/quest and publish its shortened remainder as valid.
            j.result.steps=E.Copy(skel.steps);j.result.executionSteps=E.Copy(skel.steps)
            j.result.costComplete=false;j.result.completeCost=false;j.result.priced=false
        end
        -- Result construction can yield between frames. Keep the job runnable
        -- until its restored materials, prices and diagnostics are complete.
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
        -- Limit the state graph to recipes that can matter before this target.
        -- Reachability is a relaxation: it ignores learning/skill restrictions,
        -- but never assumes unquoted raw materials can appear from nothing.
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
        -- A terminal product cannot affect a future action. Its fixed income
        -- may be compared in memo dominance while the full stock/log survives.
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
        -- A feasible material-value potential gives an admissible remaining-cost
        -- bound. Unpriced leaves and cycles stay relaxed to zero, never guessed.
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
                -- Paired forms share a zero-cost edge. Keep their potential
                -- relaxed rather than use the expensive direct price as a
                -- lower bound and accidentally prune a cheaper conversion.
                if essenceConversion(id) then value=0 end
                if value==math.huge then value=0 end
                if value>(j.values[id] or 0)+1e-9 then j.values[id]=value; changed=true end
                tick()
            end
            if not changed then break end
        end
        -- Apply master's profitable-recipe preference to the native search,
        -- using this job's frozen recursive material values. It never caps work
        -- needed for skill, materials, quests or tools.
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
            -- Probe consolidation without turning an abandoned probe into a
            -- global failure or an optimality restriction on future routes.
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
            -- The fixed recipe order still needs a route-wide procurement
            -- frontier: paying for one Greater now can beat buying individual
            -- Lessers on several later steps. Keep each inventory/supply state
            -- instead of selecting the cheapest single craft at every step.
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
            -- Preserve the guide's recipe choices while procuring all inputs
            -- and tool goals through the same recursive, finite-supply ledger.
            local current=first
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
            for _,step in ipairs(opts.fixedSteps) do
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
                    if attempts>=10000 or leveling and E.Gain(r,current.skill[r.profession])<=0 then
                        fail("levelGap",r);current=nil;break
                    end
                    local winner
                    craft(current,r,1,leveling and "level" or "material",{},function(t) if better(t,winner) then winner=t end end)
                    current=winner
                    attempts=attempts+1
                    if not current then break end
                end
                if not current then break end
                rememberPrefix(current)
            end
            if current and not toolsDue() then current=nil end
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
        -- A quick feasible incumbent uses a complete procurement ledger at every step.
        local function seed(direct,smooth)
            local current=first; j.seeding=true; j.directSeed=direct;j.smoothSeed=smooth
            j.seedAborted=false
            -- Recursive material comparisons are a warm start. Reserve most
            -- of the shared CPU budget for actual frontier exploration.
            -- DF_ROUTE_SEED_BUDGET_V15
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
            -- tick() may yield or hit the global CPU budget inside the optional
            -- seed. Keep the complete baseline reachable by Run's cutoff path.
            j.best=current
            if not opts.specializationRecipeScore and not opts.procurementDemands
                and current.skill[slug]>first.skill[slug] then
                -- Keep the original feasible route as a cost guard. A smoother
                -- candidate may replace it only after full chronological replay
                -- and the same net-cost / purchase-cost / switches comparison.
                local failures=j.failures
                j.failures={}
                -- Both heuristics use the original frozen ledger and the same
                -- final objective. Neither may discard the complete incumbent.
                for _,mode in ipairs(j.recovery and {"purchase","net"} or {"purchase"}) do
                    if cpuTime()>=j.cpuLimitMs*.72 then break end
                    -- A later rejected probe must preserve restrictions carried
                    -- by an earlier accepted incumbent in this same portfolio.
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
                -- Preserve the strategy's chosen recipe order and attempt
                -- counts, then optimize its procurement across the complete
                -- sequence. A cheaper single attempt must not discard a
                -- Greater's reusable surplus needed by later attempts.
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
            -- Try a sequence that never returns to an earlier leveling recipe.
            -- It still requires real purchase quotes or fully priced own crafts;
            -- this repairs consolidation order without fabricating purchases.
            j.referenceSeed=true
            j.referenceRecipes={}
            local reference=seed(true)
            if reference then publishPrefix(reference) end
            j.referenceSeed=false
            if j.preview and goalsComplete(j,j.preview) and uncertainty(j.preview)==0 then
                j.best=j.preview; j.initialTotal=j.preview.money; j.initialObjective=objective(j.preview,j.recovery and j.snap or nil)
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
        -- Terminal products have fixed sale value and cannot affect a future
        -- action. Keep them in the ledger and compare net cost, cash and switches.
        -- All consumable stock, provenance, fees and limited supply stay keyed.
        j.phase="frontier"
        local heap={}; local memo={}; local serial=0
        local function less(a,b)
            if stable and a.state.greenLevelCrafts~=b.state.greenLevelCrafts then
                return a.state.greenLevelCrafts<b.state.greenLevelCrafts
            end
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
            memo[key]={cost=cost,money=t.money,switches=t.switches}
            serial=serial+1; local entry={state=t,score=bound(t),serial=serial,key=key}; local i=#heap+1
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
                local cost=objective(t,j.recovery and j.snap or nil)
                if known and math.abs(cost-known.cost)<1e-7 and math.abs(t.money-known.money)<1e-7 and t.switches==known.switches then
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
            -- Reaching the node count on the final frontier state still proves
            -- exhaustion. A limit only interrupts search when work remains.
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
-- Publication is outside the solver coroutine, but still consumes its budget.
-- Account for that work once; the next Run performs a cooperative finalization
-- instead of starting another search slice after the shared budget is spent.
function S.ChargeExternalWork(j,elapsed)
    elapsed=tonumber(elapsed)
    if not j or not elapsed or elapsed~=elapsed or elapsed<=0 or elapsed==math.huge then return end
    j.cpuUsed=(j.cpuUsed or 0)+elapsed
    j.externalCpuUsed=(j.externalCpuUsed or 0)+elapsed
    S.RefreshStatus(j)
end
-- DF_ROUTE_QUALITY_BUDGET_V15
local function qualityBudgetDue(j)
    local opts=j.opts or {}
    if j.finalizing or j.finished or not j.seedDone
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
    j.status=status
    j.phase="finalize"
    -- DF_REBATCH_FINALIZE_COROUTINE_FIX_V13
    -- A cached result may still trigger final-only rebatching. Its replay/tick
    -- can coroutine.yield(), so it MUST NOT run on the scheduler's main thread.
    -- Reuse the cached fast path only after that optional replay has completed.
    local rebatchPending = j.best and j.rebatchFinal and not j.rebatchFinalized
        and (status=="complete" or status=="incomplete")
    if j.best and j.resultState==j.best and j.resultCache and not rebatchPending then
        j.result=S.Result(j,j.best,status);j.finished=true
        return
    end
    -- The old search coroutine may be suspended halfway through result replay.
    -- Drop it and its frontier; build the retained incumbent in ordinary slices.
    -- No partially built ledger is published, including at the CPU cutoff.
    j.finalizing=true
    j.co=coroutine.create(function()
        j.result=S.Result(j,j.best,status)
        j.finalizing=nil;j.finished=true
        return "done"
    end)
end
function S.Run(j,budget)
    if j.finished or j.status=="stopped" or coroutine.status(j.co)=="dead" then
        S.RefreshStatus(j);return true
    end
    local start=clock();j.sliceStart=start;j.deadline=start+(budget or 2)
    local phase=j.phase or (j.finalizing and "finalize" or not j.snap and "capture" or "initial_seed")
    local before=j.cpuUsed
    if not j.finalizing and qualityBudgetDue(j) then
        j.budgetLimited=true;j.searchTermination="quality_budget"
        finalize(j,uncertainty(j.best)==0 and "complete" or "incomplete")
        -- A cached final result can mark the job finished immediately.
        -- Never resume the abandoned search coroutine after that point.
        if j.finished then
            local delta=max(0,clock()-start)
            j.phaseCpuMs[phase]=(j.phaseCpuMs[phase] or 0)+delta
            j.cpuUsed=max(before,j.cpuUsed)+delta;j.sliceStart=nil
            if j.result then j.result.phaseCpuMs=E.Copy(j.phaseCpuMs) end
            j.progressVersion=(j.progressVersion or 0)+1
            S.RefreshStatus(j)
            return true
        end
    end
    if not j.finalizing and j.cpuUsed>=j.cpuLimitMs then
        j.budgetLimited=true;j.searchTermination="cpu_limit"
        finalize(j,j.best and (uncertainty(j.best)==0 and "complete" or "incomplete") or "incomplete")
        -- Cached results need no replay. A new finalization coroutine continues
        -- below, using this call's still-unused frame budget.
        if j.finished then
            local delta=max(0,clock()-start)
            j.phaseCpuMs[phase]=(j.phaseCpuMs[phase] or 0)+delta
            j.cpuUsed=max(before,j.cpuUsed)+delta;j.sliceStart=nil
            if j.result then j.result.phaseCpuMs=E.Copy(j.phaseCpuMs) end
            j.progressVersion=(j.progressVersion or 0)+1;S.RefreshStatus(j);return true
        end
    end
    local ok,why=coroutine.resume(j.co)
    -- Include result construction and final status work in the same CPU ledger.
    local elapsed=max(0,clock()-start)
    if not ok then
        j.status="error";j.searchTermination="error";j.failures.error={code="solverError",detail=tostring(why)}
        j.error=why
        if j.finalizing then j.finished=true;j.finalizing=nil
        else finalize(j,"error") end
    elseif not j.finalizing and qualityBudgetDue(j)
        and coroutine.status(j.co)~="dead" then
        j.budgetLimited=true;j.searchTermination="quality_budget"
        finalize(j,uncertainty(j.best)==0 and "complete" or "incomplete")
    elseif not j.finalizing and max(before,j.cpuUsed)+elapsed>=j.cpuLimitMs and coroutine.status(j.co)~="dead" then
        j.budgetLimited=true;j.searchTermination="cpu_limit"
        finalize(j,j.best and (uncertainty(j.best)==0 and "complete" or "incomplete") or "incomplete")
    end
    local delta=max(0,clock()-start)
    j.phaseCpuMs[phase]=(j.phaseCpuMs[phase] or 0)+delta
    j.cpuUsed=max(before,j.cpuUsed)+delta;j.sliceStart=nil
    local done=j.finished or coroutine.status(j.co)=="dead"
    if done and j.result then j.result.phaseCpuMs=E.Copy(j.phaseCpuMs) end    if done or not j.progressAt or clock()-j.progressAt>=200 then
        j.progressAt=clock();j.progressVersion=(j.progressVersion or 0)+1
    end
    S.RefreshStatus(j)
    return done
end
function S.Compute(slug,opts)
    local j=S.NewJob(slug,opts)
    while coroutine.status(j.co)~="dead" and not j.finished and (j.status~="error" or j.finalizing) do S.Run(j,1000) end
    return j.result or S.Result(j,j.best,j.status),j
end
-- One demand recipe shares stock, supplier packs and finite AH budgets across
-- all requested items. executionInventory is the explicit continuation bag snapshot.
function S.NewProcurementJob(snapshot,demands,opts)
    opts=E.Copy(opts or {}); opts.snapshot=E.Copy(snapshot); opts.snapshot.recipes={}
    -- A top-up purchases its explicit demand only. It must retain actual
    -- specialization gates, without trying to complete the parent route's quest.
    opts.snapshot.specializationGoals={}
    opts.snapshot.toolGoals={}
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
