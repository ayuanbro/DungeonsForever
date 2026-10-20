-- Persistent execution facts are separate from route search and price estimates.
local _, ns = ...
if not ns.LoadForeverPages then return end
local E, S = ns.ProfEconomy, ns.ProfRouteSolver
local XP = {}; ns.ProfExecution = XP
local listeners, jobs, early = {}, {}, {}
local creditCaches = setmetatable({}, {__mode="k"})
local floor, ceil, max, min = math.floor, math.ceil, math.max, math.min
local function now() return time and time() or 0 end
local function integer(n) return type(n)=="number" and n>=0 and n==floor(n) and n<math.huge end
local function copy(v, seen)
    if type(v)~="table" then if type(v)~="function" and type(v)~="userdata" then return v end; return end
    seen=seen or {}; if seen[v] then return end
    seen[v]=true; local out={}
    for k,x in pairs(v) do if type(k)=="string" or type(k)=="number" then out[k]=copy(x,seen) end end
    seen[v]=nil; return out
end
local function character() return E and E.CharacterKey and E.CharacterKey() or ((UnitName and UnitName("player") or "?").."-"..(GetRealmName and GetRealmName() or "?")) end
local function db()
    DungeonsForeverDB=DungeonsForeverDB or {}; local d=DungeonsForeverDB
    d.prof=d.prof or {}; d.prof.execution=d.prof.execution or {}
    local key=character(); local c=d.prof.execution[key]
    if type(c)~="table" or c.version~=1 then c={version=1,nextID=0,nextAttempt=0,active={},runs={},preparing={}}; d.prof.execution[key]=c end
    c.active=c.active or {}; c.runs=c.runs or {}; c.preparing=c.preparing or {}; c.seenCasts=c.seenCasts or {}; c.castOrder=c.castOrder or {}
    c.seenReceipts=c.seenReceipts or {}; c.receiptOrder=c.receiptOrder or {}
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
function XP.IsSpecializationQuest(seg) return seg and seg.kind=="specialization_quest" end
function XP.SpecializationQuest(seg) return seg and (seg.quest or seg.specializationGoal or seg.goal or seg) or {} end
local function specializationChanged(plan,slug)
    local ra=ns.ProfRouteAuto
    return ra and ra.SpecializationPlanChanged and ra.SpecializationPlanChanged(plan,slug)
end
local function validatedPlan(plan,slug)
    local ra=ns.ProfRouteAuto
    if ra and ra.ValidateVendorQuotes then plan=ra.ValidateVendorQuotes(plan) end
    if ra and ra.ValidateSpecializationPlan then plan=ra.ValidateSpecializationPlan(plan,slug) end
    return plan
end
local function skill(slug)
    local all=E and E.Professions and E.Professions()
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
local function recipe(seg,slug)
    if XP.IsSpecializationQuest(seg) then return {mats=XP.SpecializationQuest(seg).inputs or {}} end
    return seg.recipe or (E and E.FindRecipe and E.FindRecipe(seg.profession or slug,seg[3])) or {}
end
local function segment(run,id)
    if type(id)=="number" then return steps(run.plan)[id],id end
    if not id then local i=run.currentIndex or 1;return steps(run.plan)[i],i end
    for i,x in ipairs(steps(run.plan)) do if x.segmentID==id or x.actionID==id then return x,i end end
end
local function progressRecord(run,seg)
    local id=seg.segmentID; local p=run.progress[id]
    if not p then p={casts=0,attempts={},manualOutputs={}};run.progress[id]=p end
    p.attempts=p.attempts or {};p.manualOutputs=p.manualOutputs or {}
    return p
end
function XP.OnChanged(fn) if type(fn)=="function" then listeners[#listeners+1]=fn end end
local function changed(run)
    creditCaches[run]=nil
    run.progressVersion=(run.progressVersion or 0)+1;run.updatedAt=now()
    if XP.GetRecipeTotals then
        run.byRecipe=XP.GetRecipeTotals(run.slug,run.planID)
        local ledger={confirmed={},guaranteed={},consumed={},allocated={}}
        for _,entry in ipairs(run.byRecipe) do
            for item,n in pairs(entry.confirmedOutputs) do ledger.confirmed[item]=(ledger.confirmed[item] or 0)+n end
            for item,n in pairs(entry.guaranteedOutputs) do ledger.guaranteed[item]=(ledger.guaranteed[item] or 0)+n end
        end
        for _,seg in ipairs(steps(run.plan)) do
            local record=progressRecord(run,seg)
            local casts=XP.IsSpecializationQuest(seg) and (record.questCompleted and 1 or 0) or record.casts or 0
            for _,m in ipairs(recipe(seg,run.slug).mats or {}) do ledger.consumed[m[1]]=(ledger.consumed[m[1]] or 0)+m[2]*casts end
            for item,n in pairs(quotaMap(seg.requiredOutputs)) do ledger.allocated[item]=(ledger.allocated[item] or 0)+n end
        end
        run.materialLedger=ledger
    end
    for _,fn in ipairs(listeners) do pcall(fn,run.slug,run) end
end
function XP.GetRun(slug) local c=db();return c.runs[c.active[slug]] end
XP.GetActive=XP.GetRun
function XP.GetPlan(slug) local run=XP.GetRun(slug);return run and run.plan end
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
    if type(result)~="table" then return nil,"pending" end
    if result.executionVersion==1 then return result end
    if result.planVersion==2 then return nil,"migration_required" end
    local out=copy(result);out.executionVersion=1;out.executionSteps={}
    for i,raw in ipairs(result.executionSteps or result.steps or {}) do
        local seg=copy(raw);local rec=recipe(seg,slug)
        if seg[3]~=0 and not rec.spell then return nil,"migration_required" end
        if (seg[2] or 0)<=(seg[1] or 0) and (seg[4] or 0)>0 then return nil,"migration_required" end
        seg.profession=seg.profession or slug;seg.recipe=copy(rec)
        seg.segmentID=seg.segmentID or ("legacy:"..seg.profession..":"..tostring(seg[3])..":"..i)
        seg.goalSkill=seg[2];seg.expectedGain=max(0,(seg[2] or 0)-(seg[1] or 0))
        seg.expectedCrafts=seg[4] or 0;seg.attemptLimit=seg.expectedCrafts
        seg.requiredOutputs={};seg.materialMinCrafts=0;seg.allocations={}
        seg.outputMin=rec.outputMin or rec.count or 1;seg.outputMax=rec.outputMax or seg.outputMin
        out.executionSteps[#out.executionSteps+1]=seg
    end
    if not out.steps then out.steps=out.executionSteps end
    return out
end
local function ready(result)
    return result and result.feasible~=false and result.status~="selection_required" and result.status~="recalculate_required" and #steps(result)>0
end
local function archive(c,slug,reason)
    local run=c.runs[c.active[slug]]
    if run then run.status="archived";run.archivedAt=now();run.archiveReason=reason or "recalculate" end
    c.active[slug]=nil
    return run
end
function XP.Bind(slug,result,opts)
    local ra=ns.ProfRouteAuto
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
    if existing and not opts.force then
        if specializationChanged(existing.plan,slug) then return nil,"specializationChanged" end
        c.trackingSlug=slug
        if ready(result) and result~=existing.plan and result.revision~=existing.plan.revision then existing.newPlanAvailable=true;existing.candidateRevision=result.revision end
        return existing
    end
    local normalized,reason=XP.NormalizePlan(slug,result)
    if not normalized then return nil,reason end
    if not ready(normalized) then return nil,"pending" end
    if existing then archive(c,slug,"replace") end
    c.nextID=(c.nextID or 0)+1
    local planID=normalized.planID or normalized.executionPlanID or (character()..":execution:"..c.nextID)
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
    local run={planID=planID,id=planID,slug=slug,plan=plan,status="active",createdAt=now(),updatedAt=now(),progressVersion=0,
        currentIndex=1,step=1,attemptsDone=0,progress={},supplements={},inheritedInventory=copy(plan.seedInventory or opts.executionInventory or {})}
    c.runs[planID]=run;c.active[slug]=planID;c.trackingSlug=slug;c.preparing[slug]=nil
    XP.Sync(slug);changed(run);return run
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
    if cached and cached[target.segmentID] then
        local o=cached[target.segmentID];return o.borrowed,o.borrowedActual,o.credited,o.actual,o.diverted,o.waived
    end
    local obligations,bySegment,events,stock={},{},{},{}
    for index,seg in ipairs(steps(run.plan)) do
        local o={seg=seg,index=index,required=quotaMap(seg.requiredOutputs),credited={},actual={},borrowed={},borrowedActual={},destinations={},explicit={},diverted={},waived={}}
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
    creditCaches[run]=bySegment
    local o=bySegment[target.segmentID]
    return o.borrowed,o.borrowedActual,o.credited,o.actual,o.diverted,o.waived
end
function XP.GetRecipeTotals(slug,planID)
    local run=planID and db().runs[planID] or XP.GetRun(slug)
    if not run or run.slug~=slug then return {} end
    local list,byKey={},{ }
    for _,seg in ipairs(steps(run.plan)) do
        if seg[3]~=0 and not XP.IsSpecializationQuest(seg) then
            local key=(seg.profession or slug)..":"..seg[3];local entry=byKey[key]
            if not entry then entry={profession=seg.profession or slug,spell=seg[3],casts=0,confirmedOutputs={},guaranteedOutputs={},pendingOutputs=0};byKey[key]=entry;list[#list+1]=entry end
            local confirmed,guaranteed,pending=outputFacts(run,seg)
            entry.casts=entry.casts+(progressRecord(run,seg).casts or 0);entry.pendingOutputs=entry.pendingOutputs+pending
            for item,n in pairs(confirmed) do entry.confirmedOutputs[item]=(entry.confirmedOutputs[item] or 0)+n end
            for item,n in pairs(guaranteed) do entry.guaranteedOutputs[item]=(entry.guaranteedOutputs[item] or 0)+n end
        end
    end
    return list
end
function XP.Progress(slug,id)
    local run=XP.GetRun(slug);if not run then return nil end
    local seg,index=segment(run,id);if not seg then return {complete=true,skillDone=true,skillMet=true,materialDone=true,attemptsDone=0,casts=0,remainingCrafts=0,remainingOutputs=0,pendingOutputs=0} end
    local p=progressRecord(run,seg);local rec=recipe(seg,slug)
    if XP.IsSpecializationQuest(seg) then
        local goal=XP.SpecializationQuest(seg)
        local done=p.questCompleted==true
        local current=skill(seg.profession or slug)
        local direct={}
        for _,m in ipairs(goal.inputs or {}) do direct[#direct+1]={id=m[1],count=done and 0 or m[2],perCraft=m[2]} end
        return {segmentID=seg.segmentID,index=index,kind=seg.kind,questID=goal.questID,abilityID=goal.abilityID,
            complete=done,skillDone=done,skillMet=current and current>=(goal.minSkill or 200) or false,
            materialDone=done,attemptsDone=0,casts=0,remainingCrafts=0,remainingOutputs=0,pendingOutputs=0,
            extraCrafts=0,blocked=not done,directMaterials=direct}
    end
    local confirmed,guaranteed,pending,output=outputFacts(run,seg)
    local reused,reusedActual,fulfilled,_,diverted,waived=creditsFor(run,seg)
    local required=quotaMap(seg.requiredOutputs);local remaining={};local materialDone=true
    for item,n in pairs(required) do remaining[item]=max(0,n-(fulfilled[item] or 0)-(waived[item] or 0));if remaining[item]>0 then materialDone=false end end
    local cur=skill(seg.profession or slug);local goal=seg.goalSkill or seg[2]
    local skillDone=not goal or (cur~=nil and cur>=goal) or (seg.expectedGain or 0)<=0 and not seg.checkpoint
    if seg.checkpoint or seg[3]==0 then skillDone=cur~=nil and goal~=nil and cur>=goal end
    local fractional=seg.fractionalTransition or (seg.expectedGain or 0)>0 and seg[2]==seg[1] and seg.attemptLimit~=nil
    if not skillDone and fractional and (p.casts or 0)>=ceil(seg.attemptLimit-1e-9) then
        local following=steps(run.plan)[index+1]
        if following then
            local nextRecipe=recipe(following,slug);local nextSkill=skill(following.profession or slug)
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
    return {segmentID=seg.segmentID,index=index,complete=skillDone and materialDone,skillDone=skillDone,skillMet=skillDone,materialDone=materialDone,
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
end
function XP.Sync(slug,result)
    local run=XP.GetRun(slug)
    if not run and result then run=XP.Bind(slug,result) end
    if not run then return end
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
                observed=true;creditCaches[run]=nil
            end
        end
    end
    local index=1
    while index<=#steps(run.plan) do local p=XP.Progress(slug,index);if not p.complete then break end;index=index+1 end
    run.currentIndex=index;run.step=index;run.finished=index>#steps(run.plan)
    if observed then changed(run) end
    return run
end
local function matchingSegment(run,spell,id)
    if id then local seg=segment(run,id);if seg and seg[3]==spell then return seg end end
    local current=segment(run);if current and current[3]==spell then return current end
    local fallback
    for i,seg in ipairs(steps(run.plan)) do if seg[3]==spell and not seg.checkpoint then
        fallback=seg;local p=XP.Progress(run.slug,i);if not p.complete then return seg end
    end end
    return fallback
end
local function allAttempts(c)
    local list={}
    for _,run in pairs(c.runs) do for _,p in pairs(run.progress or {}) do for _,a in ipairs(p.attempts or {}) do list[#list+1]={run=run,progress=p,attempt=a} end end end
    table.sort(list,function(a,b) return a.attempt.sequence<b.attempt.sequence end);return list
end
local function acceptReceipt(receipt)
    local c=db();local selected
    for _,entry in ipairs(allAttempts(c)) do
        local a=entry.attempt
        if a.item==receipt.itemID and (not receipt.castGUID or receipt.castGUID==a.castGUID)
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
    creditCaches[run]=nil
    if run.status=="active" then XP.Sync(run.slug) end
    changed(run);return true
end
function XP.RecordOutput(data,source)
    if type(data)~="table" then return false,"invalid_receipt" end
    local receipt={itemID=tonumber(data.itemID or data.id),quantity=tonumber(data.quantity or data.count),source=source or data.source or "structured",
        operationID=data.operationID,itemGUID=data.itemGUID,castGUID=data.castGUID,spellID=data.spellID,at=data.at or now()}
    if not integer(receipt.itemID) or receipt.itemID<=0 or not integer(receipt.quantity) or receipt.quantity<=0 then return false,"invalid_receipt" end
    local c=db();local receiptID=data.receiptID or data.eventID
    if receiptID and remember(c.seenReceipts,c.receiptOrder,receipt.source..":"..tostring(receiptID),256) then return true,"duplicate" end
    if acceptReceipt(receipt) then return true end
    early[#early+1]=receipt;while #early>64 do table.remove(early,1) end
    return false,"unmatched"
end
function XP.RecordAttempt(slug,spellID,castGUID,id)
    local run=XP.GetRun(slug);if not run or type(spellID)~="number" then return false end
    local seg=matchingSegment(run,spellID,id);if not seg or XP.IsSpecializationQuest(seg) then return false end
    local c=db()
    if castGUID and remember(c.seenCasts,c.castOrder,tostring(castGUID),512) then return false,"duplicate" end
    c.nextAttempt=(c.nextAttempt or 0)+1
    local rec=recipe(seg,slug);local p=progressRecord(run,seg)
    local a={sequence=c.nextAttempt,castGUID=castGUID,spellID=spellID,segmentID=seg.segmentID,at=now(),
        item=seg.item or rec.item or rec.makes,minimum=seg.outputMin or rec.outputMin or rec.count or 0,sources={}}
    p.casts=(p.casts or 0)+1;p.attempts[#p.attempts+1]=a;run.attemptsDone=(run.attemptsDone or 0)+1
    creditCaches[run]=nil
    for i=#early,1,-1 do local r=early[i];if now()-r.at>15 then table.remove(early,i) end end
    local waiting=early;early={}
    for _,r in ipairs(waiting) do if not acceptReceipt(r) then early[#early+1]=r end end
    XP.Sync(slug);changed(run);return true,a
end
function XP.VerifyOutput(slug,id,item,total)
    if not integer(item) or item<=0 or not integer(total) then return false,"invalid_quantity" end
    local run=XP.GetRun(slug);if not run then return false,"no_execution" end
    local seg=segment(run,id);if not seg then return false,"unknown_segment" end
    local rec=recipe(seg,slug)
    if item~=(seg.item or rec.item or rec.makes) then return false,"wrong_item" end
    local p=progressRecord(run,seg);local sequence=0;for _,a in ipairs(p.attempts) do sequence=max(sequence,a.sequence) end
    p.manualOutputs[item]={total=total,throughSequence=sequence};p.verifiedAt=now()
    creditCaches[run]=nil
    XP.Sync(slug);changed(run);return true
end
local function bagCount(item)
    local fn=C_Item and C_Item.GetItemCount or GetItemCount
    if type(fn)~="function" then return 0 end
    local ok,n=pcall(fn,item,false);if ok and integer(n) then return n end;return 0
end
function XP.GetContinuation(slug)
    local run=XP.GetRun(slug);if not run then return {} end
    XP.Sync(slug)
    local stock,intermediate,events,unconfirmed,unconfirmedUsed={},{},{},{},{}
    for item,value in pairs(run.inheritedInventory or {}) do
        local n=type(value)=="table" and value.count or value
        if integer(n) then stock[item]=n;intermediate[item]=true end
    end
    for _,seg in ipairs(steps(run.plan)) do
        local rec=recipe(seg,slug);local record=progressRecord(run,seg)
        for _,m in ipairs(rec.mats or {}) do intermediate[m[1]]=true end
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
    local c=db();local run=XP.GetRun(slug);local seed=XP.GetContinuation(slug)
    local previous=c.preparing[slug]
    if not run and previous and previous.hadActive then
        seed=copy(previous.inventory or {})
        for item,n in pairs(seed) do seed[item]=min(n,bagCount(item)) end
    end
    local preparing={hadActive=run~=nil or previous and previous.hadActive,
        sourcePlanID=run and run.planID or previous and previous.sourcePlanID,inventory=copy(seed)}
    if run then archive(c,slug,"recalculate");changed(run) end
    c.preparing[slug]=preparing;return seed,preparing.sourcePlanID
end
function XP.PlanRecalculated(slug,result)
    local c=db();local p=c.preparing[slug]
    if p and p.hadActive and ready(result) then return XP.Bind(slug,result,{executionInventory=p.inventory}) end
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
    local ra=ns.ProfRouteAuto
    if run and ra and ra.VendorQuotesChanged and ra.VendorQuotesChanged(run.plan) then
        return ra.ValidateVendorQuotes(run.plan)
    end
    if run and specializationChanged(run.plan,slug) then return validatedPlan(run.plan,slug) end
    return validatedPlan(result,slug)
end
local function appendSupplement(run,result,seg,extra)
    local plan=run.plan;local index
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
    creditCaches[run]=nil
    XP.Sync(run.slug);changed(run);return true
end
function XP.CalculateSupplement(slug,callback)
    local run=XP.GetRun(slug);if not run then return nil,"no_execution" end
    local ra=ns.ProfRouteAuto
    if ra and ra.VendorQuotesChanged and ra.VendorQuotesChanged(run.plan) then return nil,"vendorQuoteChanged" end
    if specializationChanged(run.plan,slug) then return nil,"specializationChanged" end
    if jobs[run.planID] then return run.supplement end
    XP.Sync(slug);local seg=segment(run);local p=seg and XP.Progress(slug,seg.segmentID)
    if XP.IsSpecializationQuest(seg) then return nil,"specialization_quest_pending" end
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
        if j then while coroutine.status(j.co)~="dead" and not j.finished and j.status~="error" do S.Run(j,2);coroutine.yield() end;result=j.result or S.Result(j,j.best,j.status) end
        return result
    end)
    local function pump()
        if XP.GetRun(slug)~=run or run.progressVersion~=version or specializationChanged(run.plan,slug) then
            state.status="stale";state.stale=true;state.feasible=false;state.inFlight=false;jobs[run.planID]=nil;if callback then pcall(callback,state) end;return true
        end
        local ok,result=coroutine.resume(co)
        if not ok then state.status="error";state.error=tostring(result);state.inFlight=false;jobs[run.planID]=nil;changed(run);if callback then pcall(callback,state) end;return true end
        if coroutine.status(co)~="dead" then return false end
        jobs[run.planID]=nil
        result=result or {status="infeasible",feasible=false,mats={},formulas={},total=0};result.inFlight=false
        if ra and ra.StampVendorQuotes then ra.StampVendorQuotes(result) end
        if ra and ra.StampSpecializations then ra.StampSpecializations(result,slug,run.plan.executionOptions) end
        if result.feasible and result.targetReached~=false then appendSupplement(run,result,seg,extra)
        else run.supplement=result;changed(run) end
        if callback then pcall(callback,result) end
        return true
    end
    task.pump=pump
    if ns.IdleJobs and ns.IdleJobs.Add then ns.IdleJobs.Add(pump)
    elseif C_Timer and C_Timer.After then local function later() if not pump() then C_Timer.After(0,later) end end;C_Timer.After(0,later)
    else while not pump() do end end
    return state
end
function XP.Pump(slug) local run=XP.GetRun(slug);local j=run and jobs[run.planID];if j then return j.pump() end end
-- One observer exists independently of HUD construction or visibility.
local function initialize()
    local c=db();c.observerSession=(c.observerSession or 0)+1;XP.eventSession=tostring(c.observerSession)
    for _,run in pairs(c.runs) do
        if run.supplement and run.supplement.inFlight then run.supplement.inFlight=false;run.supplement.status="stale";run.supplement.stale=true;run.supplement.feasible=false end
    end
    if type(CreateFrame)~="function" then return end
    local f=CreateFrame("Frame");XP.eventFrame=f;XP.capabilities={}
    f:SetScript("OnEvent",function(_,event,...)
        if event=="UNIT_SPELLCAST_SUCCEEDED" then
            local unit,guid,spell=...;if unit~="player" then return end
            local slug=db().trackingSlug;if slug then XP.RecordAttempt(slug,spell,guid) end
        elseif event=="TRADE_SKILL_ITEM_CRAFTED_RESULT" then XP.RecordOutput((...),"structured")
        elseif event=="CHAT_MSG_LOOT" then local args={...};XP.RecordCreatedMessage(args[1],args[11])
        elseif event=="SPELLS_CHANGED" or event=="LEARNED_SPELL_IN_TAB" or event=="QUEST_TURNED_IN" then
            for slug in pairs(db().active) do XP.Sync(slug) end
        elseif event=="SKILL_LINES_CHANGED" or event=="CHAT_MSG_SKILL" then
            local slug=db().trackingSlug;local run=slug and XP.GetRun(slug);if run then XP.Sync(slug);changed(run) end
        end
    end)
    for _,event in ipairs({"UNIT_SPELLCAST_SUCCEEDED","TRADE_SKILL_ITEM_CRAFTED_RESULT","CHAT_MSG_LOOT","SKILL_LINES_CHANGED","CHAT_MSG_SKILL","SPELLS_CHANGED","LEARNED_SPELL_IN_TAB","QUEST_TURNED_IN"}) do XP.capabilities[event]=pcall(f.RegisterEvent,f,event) end
end
if ns.Init then ns.Init(initialize) else initialize() end
