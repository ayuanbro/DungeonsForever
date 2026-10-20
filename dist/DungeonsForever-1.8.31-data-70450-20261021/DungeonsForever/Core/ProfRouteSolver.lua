-- Integer procurement and chronological, resumable route search.
local _,ns=...
if not ns.LoadForeverPages then return end
local E=ns.ProfEconomy
local S={}; ns.ProfRouteSolver=S
local floor,ceil,min,max=math.floor,math.ceil,math.min,math.max
local function clock() return debugprofilestop and debugprofilestop() or (os and os.clock and os.clock()*1000) or 0 end
local function available(s,id) return (s.inv[id] or 0)-(s.unusable[id] or 0) end
local function clone(s)
    return {inv=E.Copy(s.inv),unusable=E.Copy(s.unusable),produced=E.Copy(s.produced),skill=E.Copy(s.skill),progress=E.Copy(s.progress),cap=E.Copy(s.cap),learned=E.Copy(s.learned),formulaPaid=E.Copy(s.formulaPaid),ahUsed=E.Copy(s.ahUsed),specializationAbilities=E.Copy(s.specializationAbilities),completedSpecializationGoals=E.Copy(s.completedSpecializationGoals),diagnostics=E.Copy(s.diagnostics),money=s.money,log=s.log,switches=s.switches or 0,lastRecipe=s.lastRecipe}
end
local function consume(s,id,n)
    local stock=s.inv[id] or 0
    assert(available(s,id)>=n,"reserved reagent became unavailable")
    local made=s.produced[id] or 0
    s.produced[id]=max(0,made-max(0,n-(stock-made)))
    s.inv[id]=stock-n
end
local function log(s,a) s.log={prev=s.log,action=a} end
local function diagnostic(s,key,code,extra)
    if not s.diagnostics[key] then s.diagnostics[key]={code=code,detail=extra,item=type(extra)=="number" and extra or nil} end
end
local function uncertainty(s) local n=0; for _ in pairs(s.diagnostics) do n=n+1 end; return n end
local function better(a,b)
    if not b then return true end
    local ua,ub=uncertainty(a),uncertainty(b)
    if (ua==0)~=(ub==0) then return ua==0 end
    if math.abs(a.money-b.money)>1e-7 then return a.money<b.money end
    if (a.switches or 0)~=(b.switches or 0) then return (a.switches or 0)<(b.switches or 0) end
    return uncertainty(a)<uncertainty(b)
end
local function initial(snap,slug,opts)
    local s={inv={},unusable={},produced={},skill={},progress={},cap={},learned=E.Copy(snap.known),formulaPaid={},ahUsed={},specializationAbilities=E.Copy(snap.specializationAbilities),completedSpecializationGoals={},diagnostics={},money=0,switches=0}
    for p,v in pairs(snap.professions) do s.skill[p]=v.cur or 1; s.cap[p]=v.max or 300 end
    s.skill[slug]=opts.start or s.skill[slug] or 1; s.cap[slug]=s.cap[slug] or 300
    -- Only the execution service may supply verified lots from this route.
    -- snapshot.inventory (bags/bank/legacy callers) remains deliberately ignored.
    local ids={}; for id in pairs(opts.executionInventory or {}) do if type(id)=="number" then ids[#ids+1]=id end end
    table.sort(ids)
    for _,id in ipairs(ids) do
        local entry=opts.executionInventory[id]
        local n=type(entry)=="table" and entry.count or entry
        if type(n)=="number" and n>0 and n==floor(n) then
            s.inv[id]=n
            if type(entry)=="table" and entry.usable==false then s.unusable[id]=n end
            log(s,{type="seed",item=id,count=n,usableOutput=not (type(entry)=="table" and entry.usable==false)})
        end
    end
    return s
end
local function actions(s)
    local out={}; local node=s.log
    while node do out[#out+1]=node.action; node=node.prev end
    local rev={}; for i=#out,1,-1 do rev[#rev+1]=out[i] end
    return rev
end
local function stateKey(t,reusable)
    local parts={}
    for p,n in pairs(t.skill) do parts[#parts+1]="s"..p.."="..n..":"..(t.progress[p] or 0)..":"..(t.cap[p] or 300) end
    for id,n in pairs(t.inv) do if n>0 and (not reusable or reusable[id]) then parts[#parts+1]="i"..id.."="..n..":"..(t.unusable[id] or 0) end end
    for key in pairs(t.formulaPaid) do parts[#parts+1]="f"..tostring(key) end
    for id,n in pairs(t.ahUsed) do parts[#parts+1]="a"..id.."="..n end
    for id,value in pairs(t.specializationAbilities or {}) do parts[#parts+1]="spec"..id.."="..tostring(value) end
    for id in pairs(t.completedSpecializationGoals or {}) do parts[#parts+1]="quest"..id end
    parts[#parts+1]="last="..tostring(t.lastRecipe or "")
    for k in pairs(t.diagnostics) do parts[#parts+1]="d"..k end
    table.sort(parts); return table.concat(parts,";")
end
local function goalsComplete(job,state)
    if not state or state.skill[job.slug]<job.target then return false end
    for _,goal in ipairs(job.snap and job.snap.specializationGoals or {}) do
        if not state.completedSpecializationGoals[goal.id] and not state.specializationAbilities[goal.abilityID] then return false end
    end
    return not (job.slug=="engineering" and job.target>=200 and job.snap and job.snap.specializationContext and job.snap.specializationContext.selectionConflict)
end
local function completedGoals(state)
    local count=0
    for _ in pairs(state and state.completedSpecializationGoals or {}) do count=count+1 end
    return count
end
local function stampFreshResult(result)
    local route=ns.ProfRouteAuto
    if route and route.StampVendorQuotes then route.StampVendorQuotes(result) end
    return result
end
function S.Result(job,state,status)
    -- A blocked future rank or missing quote must not hide the usable prefix.
    -- Keep the full-goal incumbent separate so it remains a valid pruning bound.
    local prefix=job.preview or (job.partial and job.partial.batched and job.partial)
    local partial=not state and prefix and (prefix.skill[job.slug]>(job.opts.start or 1) or completedGoals(prefix)>0)
    if partial then state=prefix; partial=not goalsComplete(job,state) end
    local out={planVersion=2,executionVersion=1,scheme="cheapest",steps={},executionSteps={},actions={},mats={},firstAt={},gaps={},total=0,matTotal=0,vendorTotal=0,ahTotal=0,crafts=0,productAH=0,productNPC=0,productPartial=false,start=job.opts.start or 1,target=job.target,status=status or "searching",feasible=state~=nil,priced=true,optimal=false,diagnostics={},stamp=(time and time()) or 0,expanded=job.expanded or 0,improvements=job.improvements or 0,initialTotal=job.initialTotal,searchComplete=job.exhausted or false,budgetLimited=job.budgetLimited or false}
    out.seedInventory=E.Copy(job.opts.executionInventory or {})
    out.scheme=job.opts.scheme or "cheapest"
    out.specializationGoals=E.Copy(job.snap and job.snap.specializationGoals)
    out.specializationContext=E.Copy(job.snap and job.snap.specializationContext)
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
    out.partial=partial and true or false
    out.targetReached=goalsComplete(job,state)
    out.plannedTo=state and state.skill[job.slug] or out.start
    if not state then
        out.priced=false; out.costComplete=false; out.completeCost=false
        for _,d in pairs(job.failures or {}) do out.diagnostics[#out.diagnostics+1]=d end
        if job.opts.procurementDemands then out.procurement=true;out.demands=E.Copy(job.opts.procurementDemands);out.start=nil;out.target=nil;out.plannedTo=nil end
        return stampFreshResult(out)
    end
    local purchases={}; local crafted={}; local pendingCost=0; local pendingUnpriced=false
    local formulaEntries,formulaRecipes={},{}
    out.total=state.money; out.inventory=E.Copy(state.inv); out.finalSkills=E.Copy(state.skill)
    out.completedSpecializationGoals=E.Copy(state.completedSpecializationGoals)
    out.specializationAbilities=E.Copy(state.specializationAbilities)
    for _,d in pairs(state.diagnostics) do out.diagnostics[#out.diagnostics+1]=d end
    out.costComplete=#out.diagnostics==0
    out.completeCost=out.costComplete
    out.priced=out.costComplete
    out.actions=actions(state); out.dependencyGraph={}
    if partial then
        out.blockingDiagnostics=E.Copy(job.blockedSkill==out.plannedTo and job.blockers or {})
        out.remainingUnknown=true
    end
    local provenance={}; local usedOutputs={}; local allocations={}; local cashByRecipe={}; local countByRecipe={}; local unpricedByRecipe={}
    for _,a in ipairs(actions(state)) do
        if (a.type=="buy" or a.type=="formula") and a.owner then
            cashByRecipe[a.owner]=(cashByRecipe[a.owner] or 0)+a.cost
            unpricedByRecipe[a.owner]=unpricedByRecipe[a.owner] or a.unpriced
        elseif a.type=="craft" then local key=a.profession..":"..a.spell; countByRecipe[key]=(countByRecipe[key] or 0)+a.count end
    end
    local function addOrigin(id,n,actionID)
        local pool=provenance[id] or {}; provenance[id]=pool
        pool[#pool+1]={count=n,id=actionID}
    end
    for i,a in ipairs(out.actions) do
        a.id=tostring(i)..":"..tostring(a.profession or "")..":"..tostring(a.spell or a.item or 0)
        local dependencies={}; local dependencySet={}
        for _,input in ipairs(a.inputs or {}) do
            local need=input[2]
            for _,origin in ipairs(provenance[input[1]] or {}) do
                local n=min(need,origin.count); origin.count=origin.count-n; need=need-n
                if n>0 and origin.id then
                    usedOutputs[origin.id]=true
                    local list=allocations[origin.id] or {}; allocations[origin.id]=list
                    list[#list+1]={consumerID=a.id,itemID=input[1],count=n}
                    if not dependencySet[origin.id] then dependencySet[origin.id]=true; dependencies[#dependencies+1]=origin.id end
                end
                if need<=0 then break end
            end
        end
        a.dependencies=dependencies; out.dependencyGraph[a.id]=dependencies
        if a.type=="seed" then
            if a.usableOutput~=false then addOrigin(a.item,a.count,a.id) end
        elseif a.type=="formula" then
            local entry=E.Copy(a.formula);entry.recipes={};out.formulas[#out.formulas+1]=entry
            formulaEntries[entry.id or entry.recipeKey]=entry
            out.formulaComplete=out.formulaComplete and entry.costComplete
            out.formulasTotal=out.formulasTotal+a.cost
            if a.source=="vendor" then
                out.vendorTotal=out.vendorTotal+a.cost;out.formulaVendorTotal=out.formulaVendorTotal+a.cost
            elseif a.source=="ah" then out.ahTotal=out.ahTotal+a.cost;out.formulaAHTotal=out.formulaAHTotal+a.cost end
            out.referencePrices=out.referencePrices or entry.offer and entry.offer.reference
        elseif a.type=="buy" then
            addOrigin(a.item,a.count,a.id)
            if not a.owner then pendingCost=pendingCost+a.cost;pendingUnpriced=pendingUnpriced or a.unpriced end
            local key=tostring(a.item)..":"..a.source..":"..tostring(a.npcID or 0)
            local map=purchases; local e=map[key]
            if not e then e={a.item,0,id=a.item,count=0,need=0,cost=0,unit=0,vendor=a.source=="vendor",source=a.source,npcID=a.npcID,url=a.url,spell=a.spell,reason=a.reason,bundleSize=a.bundleSize,quoteSource=a.quoteSource,priceSource=a.priceSource,priceBasis=a.priceBasis,verifiedAt=a.verifiedAt}; map[key]=e end
            e[2]=e[2]+a.count; e.count=e[2]; e.need=e.count; e.cost=e.cost+a.cost; e.unit=e.cost/e.count
            e.unpriced=e.unpriced or a.unpriced or nil
            out.pricePending=out.pricePending or a.unpriced or nil
            e.reference=e.reference or a.reference or nil; e.estimated=e.estimated or a.estimated or nil
            out.referencePrices=out.referencePrices or a.reference or nil
            out.matTotal=out.matTotal+a.cost
            if a.source=="vendor" then out.vendorTotal=out.vendorTotal+a.cost else out.ahTotal=out.ahTotal+a.cost end
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
            local entry=f and formulaEntries[f.id or recipeKey]
            if entry and not formulaRecipes[recipeKey] then
                entry.recipes[#entry.recipes+1]={profession=a.profession,spell=a.spell,key=recipeKey,source=f.sources}
                formulaRecipes[recipeKey]=true
            end
            if a.usableOutput~=false then for _,output in ipairs(a.outputs or {}) do addOrigin(output[1],output[2],a.id) end end
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
                out.executionSteps[#out.executionSteps+1]={a.from,a.to,a.spell or 0,a.count or 0,profession=a.profession,reason=a.reason,checkpoint=a.type=="gather",actionID=a.id,actionIDs={a.id},item=a.item,cost=stepCost,unpriced=stepUnpriced,recipe=recipe and E.Copy(recipe),expectedGain=a.expectedGain or (a.to-a.from),fromProgress=a.fromProgress or 0,toProgress=a.toProgress or 0}
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
    for _,e in pairs(purchases) do out.mats[#out.mats+1]=e end
    out.referenceRoute=out.pricePending or nil
    table.sort(out.mats,function(a,b) return a.id<b.id or (a.id==b.id and a.source<b.source) end)
    local occurrences,actionSegments={},{}
    for _,step in ipairs(out.executionSteps) do
        local key=step.kind=="specialization_quest" and ("quest:"..step.goalID) or (step.profession..":"..step[3])
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
        for _,id in ipairs(step.actionIDs) do for _,allocation in ipairs(allocations[id] or {}) do
            step.requiredOutputs[allocation.itemID]=(step.requiredOutputs[allocation.itemID] or 0)+allocation.count
            step.allocations[#step.allocations+1]={consumerID=actionSegments[allocation.consumerID] or allocation.consumerID,itemID=allocation.itemID,count=allocation.count}
        end end
        step.materialMinCrafts=0
        for _,n in pairs(step.requiredOutputs) do step.materialMinCrafts=max(step.materialMinCrafts,ceil(n/max(1,step.outputMin))) end
        step.leveling=(step.expectedGain or 0)>1e-9
        step.material=next(step.requiredOutputs)~=nil
        step.role=step.leveling and (step.material and "both" or "level") or (step.material and "material" or nil)
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
        local key=(step.checkpoint or step.kind=="specialization_quest") and step.actionID or (step.profession..":"..step[3])
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
        if left>0 then
            local ah=job.snap.prices[id]; local npc=ra and ra.NPCSellPriceOf and ra.NPCSellPriceOf(id)
            if ah then out.productAH=out.productAH+left*ah else out.productPartial=true end
            if npc then out.productNPC=out.productNPC+left*npc end
        end
    end
    E.SummarizeAuctionSupply(out,job.snap)
    out.optimal=not partial and job.exhausted and not job.restricted and out.costComplete and job.snap.coverageComplete~=false or false
    if job.opts.procurementDemands then
        out.procurement=true;out.demands=E.Copy(job.opts.procurementDemands)
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
    return stampFreshResult(out)
end
function S.NewJob(slug,opts)
    opts=opts or {}
    local j={slug=slug,opts=opts,target=min(300,max(1,floor(opts.target or 300))),expanded=0,failures={},cpuUsed=0,status="searching",generation=0}
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
    local function fail(code,r,id)
        local key=code..":"..tostring(r and r.key or "")..":"..tostring(id or "")
        j.failures[key]={code=code,recipe=r and r.key,item=id,spell=r and r.spell,profession=r and r.profession}
        if j.collectFailures then j.collectFailures[key]=j.failures[key] end
    end
    local acquire,craft,levelTo
    local function bound(s)
        local credit=0
        for id,n in pairs(s.inv) do credit=credit+(j.values and j.values[id] or 0)*n end
        local remaining=max(0,j.target-(s.skill[slug] or 1)-(s.progress[slug] or 0))
        return s.money+max(0,(j.pointBound or 0)*remaining-credit)
    end
    local function pruned(s,complete)
        if not j.best then return false end
        if uncertainty(j.best)>0 then return false end
        if uncertainty(s)>0 then return true end
        -- Inside reagent acquisition, inputs may already be reserved for an
        -- unfinished parent. Only complete frontier states admit this heuristic.
        local lower=complete and bound(s) or s.money
        return lower>j.best.money+1e-7 or (math.abs(lower-j.best.money)<1e-7 and (s.switches or 0)>=(j.best.switches or 0))
    end
    local function allowed(r,s,reason)
        if E.RecipeSpecializationAllowed then
            local ok,why=E.RecipeSpecializationAllowed(r,j.snap,s)
            if not ok then fail(why or "specializationRequired",r);return false end
        end
        local formula=j.formulaByRecipe and j.formulaByRecipe[r.key]
        if formula and not formula.usable then fail(formula.reason or "formulaUnavailable",r,formula.id);return false end
        if r.clientUnavailable then fail("clientUnavailable",r,r.item); return false end
        if r.clientPending then fail("clientDataPending",r,r.item); return false end
        if r.cooldown or r.cooldownUnknown then fail(r.cooldown and "cooldown" or "cooldownUnknown",r); return false end
        if r.outputConflict then fail("outputConflict",r,r.item); return false end
        if (r.availabilityUnknown or r.verified==false) and not r.clientAvailable then if not s.learned[r.key] and not s.learned[r.spell] then fail("availabilityUnknown",r); return false end end
        local p=E.Policy(j.opts.exclusions,r)
        if p=="ban" or (p=="level" and reason~="material") then fail("excluded",r,r.item); return false end
        local profession=j.snap.professions[r.profession]
        if opts.learnedOnly and not (profession and profession.unlearned)
            and not (s.learned[r.key] or s.learned[r.spell]) then fail("notLearned",r); return false end
        return true
    end
    local function vendorQuote(o)
        return o.unlimited==true and type(o.price)=="number" and o.price>=0
            and o.available~=false and o.purchasable~=false and not o.hasExtendedCost
            and (not o.currencyID or o.currencyID==0)
            and (not o.faction or not j.snap.faction or o.faction==j.snap.faction or o.faction=="Neutral" or o.faction=="N")
    end
    local function auctionQuote(id)
        local price=j.snap.prices[id]
        return not j.snap.nonAuctionable[id]
            and type(price)=="number" and price>0
    end
    local function auctionRemaining(s,id)
        local supply=j.snap.auctionSupply[id]
        return supply and max(0,supply.quantity-(s.ahUsed[id] or 0)) or math.huge
    end
    local function output(s,r,n)
        if not r.item then return true end
        local count=r.count*n
        s.inv[r.item]=(s.inv[r.item] or 0)+count
        s.produced[r.item]=(s.produced[r.item] or 0)+count
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
        if source=="ah" and j.snap.auctionSupply[id] then
            if count>auctionRemaining(s,id) then fail("auctionSupplyLimited",nil,id);return end
            t.ahUsed[id]=(t.ahUsed[id] or 0)+count
        end
        t.inv[id]=(t.inv[id] or 0)+count; t.money=t.money+cost
        log(t,{type="buy",item=id,count=count,cost=cost,source=source,npcID=npc,reason=reason,url=url,bundleSize=bundle,owner=owner,unpriced=unpriced,estimated=estimated,reference=offer and offer.reference,quoteSource=offer and offer.source,priceSource=offer and offer.priceSource,priceBasis=offer and offer.priceBasis,verifiedAt=offer and offer.verifiedAt})
        -- A verified reference price is a known quote in the reference-price
        -- model. Unqualified vendor caches still make the cost incomplete.
        if estimated and not (offer and offer.reference) then diagnostic(t,"vendor:"..id..":"..tostring(npc),"vendorEstimate",id) end
        if unpriced then diagnostic(t,source..":"..id,source=="vendor" and "vendorPriceUnknown" or "materialPriceUnknown",id) end
        return t
    end
    local function learnFormula(s,r,choice)
        local f=choice or j.formulaByRecipe[r.key]
        if not f or f.known then return s end
        if not f.usable then fail(f.reason or "formulaUnavailable",r,f.id);return end
        local key=f.id or r.key
        if s.formulaPaid[key] then return s end
        if f.source=="ah" and auctionRemaining(s,f.id)<1 then
            f=E.FormulaFor(r,j.snap,auctionRemaining(s,f.id))
            if not f or not f.usable then fail("auctionSupplyLimited",r,f and f.id);return end
        end
        local t=clone(s);t.formulaPaid[key]=true;t.money=t.money+(f.cost or 0)
        if f.source=="ah" and j.snap.auctionSupply[f.id] then t.ahUsed[f.id]=(t.ahUsed[f.id] or 0)+1 end
        if f.unpriced then diagnostic(t,"formula:"..tostring(key),"formulaPriceUnknown",f.id or r.key) end
        if f.availabilityUncertain then diagnostic(t,"formulaStock:"..tostring(key),"formulaStockUnknown",f.id or r.key) end
        log(t,{type="formula",item=f.id,count=f.bundleSize or 1,cost=f.cost or 0,source=f.source,owner=r.key,unpriced=f.unpriced,formula=E.Copy(f)})
        return t
    end
    local function prepare(r,s,reason,path,emit)
        if not allowed(r,s,reason) then return end
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
        local prepared=learnFormula(s,r)
        if prepared then emit(prepared) end
        local f=j.formulaByRecipe[r.key]
        if f and not f.known and f.source=="ah" and j.snap.auctionSupply[f.id]
            and not s.formulaPaid[f.id or r.key] and auctionRemaining(s,f.id)>=1 then
            -- Paying a little more at a vendor can reserve the last auction
            -- copy for a later reagent. It is a search branch, not a greedy
            -- decision made once for the whole recipe catalogue.
            local alternative=E.FormulaFor(r,j.snap,0)
            if alternative and alternative.usable and alternative.source=="vendor" then
                local t=learnFormula(s,r,alternative)
                if t then emit(t) end
            end
        end
        if f and not f.known and f.source=="vendor" and f.availabilityUncertain
            and f.ahPrice and auctionRemaining(s,f.id)>=1 and not s.formulaPaid[f.id or r.key] then
            -- A limited shelf is a reference, while a quoted auction copy can
            -- provide a complete route. Explore both before uncertainty pruning.
            local alternative=E.FormulaFor(r,j.snap,auctionRemaining(s,f.id),"ah")
            if alternative and alternative.usable and alternative.source=="ah" then
                local t=learnFormula(s,r,alternative)
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
                    local progress=(t.progress[p] or 0)+g
                    local gain=floor(progress+1e-7)
                    t.skill[p]=min(300,t.skill[p]+gain); t.progress[p]=floor((progress-gain)*1000000+.5)/1000000
                    tick()
                end
                local produced=r.item and r.count*n or 0
                local usableOutput=output(t,r,n)
                if p==slug and t.lastRecipe~=r.key then t.switches=t.switches+1; t.lastRecipe=r.key end
                log(t,{type="craft",profession=p,spell=r.spell,count=n,from=from,to=t.skill[p],item=r.item,outputCount=produced,outputs=r.item and {{r.item,produced}} or {},inputs=inputs,reason=reason,station=r.station,usableOutput=usableOutput})
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
        local finalEmit=emit; local localBest
        if j.seeding then emit=function(t) if better(t,localBest) then localBest=t end end end
        local price=j.snap.prices[id]
        local had=false
        local auctionPriced=auctionQuote(id)
        local remaining=auctionRemaining(s,id)
        if auctionPriced then
            if remaining>=missing then had=true;emit(buy(s,id,missing,"ah",price,1,nil,reason,nil,nil,path.owner))
            else
                fail("auctionSupplyLimited",nil,id)
                if remaining>0 then
                    had=true
                    local t=buy(s,id,remaining,"ah",price,1,nil,reason,nil,nil,path.owner)
                    acquire(t,id,need,reason,path,emit,used)
                end
            end
        end
        for _,o in ipairs(j.snap.offers[id] or {}) do
            if vendorQuote(o) then
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
        elseif path[id] and j.snap.byItem[id] then j.restricted=true end
        if not had then fail("materialUnavailable",nil,id) end
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
        for _,r in ipairs(j.snap.byProfession[p] or {}) do
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
        -- Search the whole material combination, including shared packs/leftovers,
        -- even during the quick route seed. Each reagent is reserved immediately.
        local wasSeeding,wasDirect,deadline=j.seeding,j.directSeed,j.seedDeadline
        j.seeding=false;j.directSeed=false;j.seedDeadline=nil
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
    local function expand(s,p,target,path,emit,greedy)
        if j.seedAborted then return end
        if p==slug then
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
                tick()
                if j.seedAborted then return math.huge end
                local missing=max(0,qty-available(s,id)); if missing==0 then return 0 end
                local key=id..":"..missing
                if quoteCache[key]~=nil then return quoteCache[key] end
                local price=j.snap.prices[id]
                local auctionPriced=auctionQuote(id)
                local enoughAuction=auctionPriced and auctionRemaining(s,id)>=missing
                local best=enoughAuction and price*missing or math.huge
                for _,o in ipairs(j.snap.offers[id] or {}) do
                    if vendorQuote(o) then
                        local bundle=o.quantity or o.bundleSize or 1
                        best=min(best,ceil(missing/bundle)*o.price)
                    end
                end
                path=path or {}
                if path[id] then return best,true end
                if j.directSeed and best<math.huge then quoteCache[key]=best; return best end
                local cyclic=false
                if not enoughAuction and not path[id] then
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
                            if j.directSeed and best<math.huge then break end
                        end
                    end
                    path[id]=nil
                end
                -- A failed lookup through a cycle is path-dependent. Do not
                -- memoize that failure and hide a valid alternative entry.
                if best<math.huge or not cyclic then quoteCache[key]=best end
                return best,cyclic
            end
            for _,r in ipairs(j.snap.byProfession[p] or {}) do
                local sk=s.skill[p]
                if r.learn<=sk and sk<r.grey and allowed(r,s,"level")
                    and (not j.referenceSeed or not j.referenceRecipes[r.key] or s.lastRecipe==r.key) then
                    any=true
                    local n=opts.specializationRecipeScore and 1
                        or max(1,ceil((1-(s.progress[p] or 0))/max(.000001,E.Gain(r,sk))-1e-7))
                    local estimate=0
                    local f=j.formulaByRecipe[r.key]
                    if f and not f.known and not s.formulaPaid[f.id or r.key] then estimate=f.cost or 0 end
                    for _,m in ipairs(r.mats) do estimate=estimate+quote(m[1],m[2]*n) end
                    candidates[#candidates+1]={recipe=r,count=n,estimate=estimate}
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
            table.sort(candidates,function(a,b) return a.estimate<b.estimate or (a.estimate==b.estimate and a.recipe.spell<b.recipe.spell) end)
            local selected,selectedScore
            for _,candidate in ipairs(candidates) do
                if j.seedAborted then return end
                if candidate.estimate<math.huge or not j.directSeed then
                    local winner
                    craft(s,candidate.recipe,candidate.count,p==slug and "level" or "secondary",path,function(t)
                        if (t.skill[p]>s.skill[p] or t.skill[p]==s.skill[p] and (t.progress[p] or 0)>(s.progress[p] or 0))
                            and better(t,winner) then winner=t end
                    end)
                    local score=winner and opts.specializationRecipeScore and opts.specializationRecipeScore(candidate.recipe,s,j.snap,winner.money-s.money)
                    if winner and (score and (not selectedScore or score<selectedScore-1e-7
                        or math.abs(score-selectedScore)<1e-7 and better(winner,selected))
                        or not score and better(winner,selected)) then selected=winner;selectedScore=score end
                    if winner and j.directSeed and not opts.specializationRecipeScore then emit(winner); return end
                end
            end
            if selected then emit(selected); return end
            if not any and miningGap(s,p) then gather(s,p,target,emit)
            elseif not any then fail("levelGap",{key=p..":"..s.skill[p],profession=p}) end
            return
        end
        for _,r in ipairs(j.snap.byProfession[p] or {}) do
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
                local k=stateKey(t,j.reusable)
                if visited[k]==nil or t.money<visited[k] then visited[k]=t.money; expand(t,p,target,path,function(u) stack[#stack+1]=u end,true) end
            end
            tick()
        end
        -- Secondary levelling groups attempts into an expected-point block.
        j.restricted=true
    end
    -- Keep the search's chronology. Moving every occurrence of a recipe to its
    -- first occurrence changes skill gains and can turn later leveling into waste.
    local function batchPlan(raw,requireGoal)
        local original=actions(raw)
        local function replay(list)
            local t=initial(j.snap,slug,opts)
            t.diagnostics={}
            local active={}
            for _,a in ipairs(list) do if a.type=="craft" then active[a.profession..":"..a.spell]=true end end
            for _,a in ipairs(list) do
                if a.type=="buy" then
                    local bundle=a.bundleSize or 1
                    if a.count<=0 or a.count%bundle~=0 then return end
                    local price=a.cost/(a.count/bundle)
                    t=buy(t,a.item,a.count,a.source,price,bundle,a.npcID,a.reason,a.url,a.estimated,a.owner,a.unpriced,
                        {reference=a.reference,source=a.quoteSource,priceBasis=a.priceBasis,verifiedAt=a.verifiedAt})
                    if not t then return end
                elseif a.type=="formula" and active[a.owner] then
                    local f=a.formula; local key=f and (f.id or a.owner)
                    if f and not t.formulaPaid[key] then
                        if a.source=="ah" and auctionRemaining(t,a.item)<(a.count or 1) then return end
                        t=clone(t);t.formulaPaid[key]=true;t.money=t.money+a.cost
                        if a.source=="ah" and j.snap.auctionSupply[a.item] then t.ahUsed[a.item]=(t.ahUsed[a.item] or 0)+(a.count or 1) end
                        log(t,E.Copy(a))
                        if f.unpriced then diagnostic(t,"formula:"..tostring(key),"formulaPriceUnknown",f.id or a.owner) end
                        if f.availabilityUncertain then diagnostic(t,"formulaStock:"..tostring(key),"formulaStockUnknown",f.id or a.owner) end
                    end
                elseif a.type=="gather" then
                    local event=E.Copy(a);event.from=t.skill[a.profession];event.to=max(event.from,a.to)
                    t.skill[a.profession]=event.to;t.progress[a.profession]=0;log(t,event)
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
            return t
        end
        local first=replay(original)
        if not first then fail("executionInvalid");return end
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
        if changed then j.restricted=true end
        t.batched=true
        return t
    end
    j.co=coroutine.create(function()
        j.snap=E.Capture(slug,opts,tick)
        j.hasFiniteSupply=next(j.snap.auctionSupply)~=nil
        if not opts.start then opts.start=(j.snap.professions[slug] or {}).cur or 1 end
        local context=j.snap.routeContext or E.RouteContext(slug,opts,j.snap.professions)
        j.specializationConflict=slug=="engineering" and j.target>=200 and
            j.snap.specializationContext and j.snap.specializationContext.selectionConflict
        if context.requiresPartner and not context.partnerValid then
            fail("secondaryRequired"); j.exhausted=true; j.status="infeasible"; j.finished=true
            j.result=S.Result(j,nil,j.status)
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
        opts.exclusions=opts.exclusions or E.GetPolicies(slug)
        local first=initial(j.snap,slug,opts)
        j.reusable={}; j.values={}
        -- Limit the state graph to recipes that can matter before this target.
        -- Reachability is a relaxation: it ignores learning/skill restrictions,
        -- but never assumes unquoted raw materials can appear from nothing.
        local reachable={}
        for id in pairs(first.inv) do if available(first,id)>0 then reachable[id]=true end end
        for id,available in pairs(j.snap.vendorItems or {}) do if available then reachable[id]=true end end
        for id,price in pairs(j.snap.prices) do if type(price)=="number" and price>0 then reachable[id]=true end end
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
            end
        end
        for _,r in ipairs(j.snap.recipes) do
            if r.profession==slug and r.grey>opts.start and r.learn<j.target and ingredientsReachable(r) then
                levelRoots[#levelRoots+1]=r; visit(r)
            elseif opts.allowSecondaryLeveling and r.profession~=slug then visit(r) end
            tick()
        end
        for _,goal in ipairs(j.snap.specializationGoals or {}) do
            for _,m in ipairs(goal.inputs) do
                j.reusable[m[1]]=true
                for _,r in ipairs(j.snap.byItem[m[1]] or {}) do if r.profession==goal.profession then visit(r) end end
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
                if value==math.huge then value=0 end
                if value>(j.values[id] or 0)+1e-9 then j.values[id]=value; changed=true end
                tick()
            end
            if not changed then break end
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
            local failures,restricted=j.failures,j.restricted
            j.failures={}
            local preview=batchPlan(t,false)
            j.failures,j.restricted=failures,restricted
            if preview and (not j.preview or preview.skill[slug]>j.preview.skill[slug]
                or (preview.skill[slug]==j.preview.skill[slug] and (completedGoals(preview)>completedGoals(j.preview)
                    or completedGoals(preview)==completedGoals(j.preview) and better(preview,j.preview)))) then
                j.preview=preview; j.result=S.Result(j,nil,"searching"); coroutine.yield("publish")
            end
        end
        -- A quick feasible incumbent uses a complete procurement ledger at every step.
        local function seed(direct)
            local current=first; j.seeding=true; j.directSeed=direct
            j.seedAborted=false
            -- Recursive material comparisons are a warm start. Reserve most
            -- of the shared CPU budget for actual frontier exploration.
            j.seedDeadline=not direct and not opts.specializationRecipeScore and cpuTime()+250 or nil
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
                if not nextState then
                    j.blockers={}
                    j.blockedSkill=current.skill[slug]
                    for _,d in pairs(j.collectFailures) do j.blockers[#j.blockers+1]=d end
                end
                j.collectFailures=nil
                rememberPrefix(nextState)
                if j.referenceSeed and nextState and nextState.lastRecipe then j.referenceRecipes[nextState.lastRecipe]=true end
                if direct and nextState and (not j.preview or nextState.skill[slug]>=checkpoint+15) then
                    publishPrefix(nextState); checkpoint=nextState.skill[slug]
                end
                if j.seedAborted then current=nil; break end
                current=nextState; tick()
            end
            j.seedDeadline=nil; j.seedAborted=false
            if direct then publishPrefix(current or j.partial) end
            return current
        end
        local current=seed(not opts.specializationRecipeScore)
        if current and goalsComplete(j,current) then current=batchPlan(current,true) end
        if current then
            j.best=current; j.initialTotal=current.money; j.result=S.Result(j,current,"searching"); coroutine.yield("publish")
        end
        if opts.specializationRecipeScore then
            j.seeding=false;j.directSeed=false;j.restricted=true;j.exhausted=true
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
                j.best=j.preview; j.initialTotal=j.preview.money
                j.result=S.Result(j,j.best,"searching"); coroutine.yield("publish")
            end
        end
        local refined=seed(false)
        if refined and goalsComplete(j,refined) then refined=batchPlan(refined,true) end
        if refined and goalsComplete(j,refined) and better(refined,j.best) then
            current=refined; j.best=refined; j.improvements=(j.improvements or 0)+1
        elseif not current then current=refined end
        j.seeding=false; j.directSeed=false
        if current and goalsComplete(j,current) then j.best=current; j.initialTotal=j.initialTotal or current.money; j.result=S.Result(j,current,"searching"); coroutine.yield("publish") end
        if not current and j.partial and (j.partial.skill[slug]>first.skill[slug] or completedGoals(j.partial)>0) then
            publishPrefix(j.partial)
            j.result=S.Result(j,nil,"searching"); coroutine.yield("publish")
        end
        -- Best-first search merges equivalent reusable-material states. Finished
        -- products remain in the output ledger but cannot multiply the frontier.
        local heap={}; local memo={}; local serial=0
        local function less(a,b)
            if math.abs(a.score-b.score)>1e-7 then return a.score<b.score end
            local sa,sb=a.state,b.state
            if sa.skill[slug]~=sb.skill[slug] then return sa.skill[slug]>sb.skill[slug] end
            if sa.switches~=sb.switches then return sa.switches<sb.switches end
            return a.serial<b.serial
        end
        local function push(t)
            if pruned(t,true) then return end
            local key=stateKey(t,j.reusable); local old=memo[key]
            if old and (old.money<t.money-1e-7 or (math.abs(old.money-t.money)<1e-7 and old.switches<=t.switches)) then return end
            memo[key]={money=t.money,switches=t.switches}
            serial=serial+1; local entry={state=t,score=bound(t),serial=serial,key=key}; local i=#heap+1
            while i>1 do local parent=floor(i/2); if not less(entry,heap[parent]) then break end; heap[i]=heap[parent]; i=parent end
            heap[i]=entry
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
                if known and t.money<=known.money+1e-7 and t.switches<=known.switches then
                    expand(t,slug,j.target,{},function(u) rememberPrefix(u); push(u) end,false)
                end
            end
            if opts.maxNodes and j.expanded>=opts.maxNodes then j.budgetLimited=true; break end
            tick()
        end
        j.exhausted=not j.budgetLimited; j.status=j.best and (uncertainty(j.best)==0 and "complete" or "incomplete") or (j.partial and (j.partial.skill[slug]>first.skill[slug] or completedGoals(j.partial)>0) and "incomplete" or "infeasible")
        if not j.best and j.partial then publishPrefix(j.partial) end
        if not j.best then for _,d in pairs(j.failures) do if d.code=="clientDataPending" or d.code=="materialUnavailable" or d.code=="outputConflict" or d.code=="availabilityUnknown" then j.status="incomplete"; break end end end
        j.result=S.Result(j,j.best,j.status)
        j.finished=true
        return "done"
    end)
    return j
end
function S.Run(j,budget)
    if j.finished or j.status=="stopped" or coroutine.status(j.co)=="dead" then return true end
    local start=clock(); j.sliceStart=start; j.deadline=start+(budget or 2)
    local ok,why=coroutine.resume(j.co)
    j.cpuUsed=j.cpuUsed+max(0,clock()-start)
    if not ok then
        j.status="error"; j.failures.error={code="solverError",detail=tostring(why)}
        j.result=S.Result(j,j.best,"error"); j.error=why; return true
    end
    if j.cpuUsed>=5000 and coroutine.status(j.co)~="dead" then
        j.budgetLimited=true; j.finished=true; j.status=j.best and "complete" or "incomplete"
        j.result=S.Result(j,j.best,j.status); return true
    end
    if j.expanded>0 and (not j.progressAt or clock()-j.progressAt>=200) and coroutine.status(j.co)~="dead" then
        j.progressAt=clock(); j.result=S.Result(j,j.best,"searching")
    end
    return coroutine.status(j.co)=="dead"
end
function S.Compute(slug,opts)
    local j=S.NewJob(slug,opts)
    while coroutine.status(j.co)~="dead" and not j.finished and j.status~="error" do S.Run(j,1000) end
    return j.result or S.Result(j,j.best,j.status),j
end
-- One demand recipe shares stock, supplier packs and finite AH budgets across
-- all requested items. executionInventory is explicit verified route stock only.
function S.NewProcurementJob(snapshot,demands,opts)
    opts=E.Copy(opts); opts.snapshot=E.Copy(snapshot); opts.snapshot.recipes={}
    -- A top-up purchases its explicit demand only. It must retain actual
    -- specialization gates, without trying to complete the parent route's quest.
    opts.snapshot.specializationGoals={}
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
    while coroutine.status(j.co)~="dead" and not j.finished and j.status~="error" do S.Run(j,1000) end
    return j.result or S.Result(j,j.best,j.status),j
end
function S.Procure(snapshot,id,count,opts)
    return S.ProcureMany(snapshot,{[id]=count},opts)
end
