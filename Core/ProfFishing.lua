-- A self-fished cooking reference route. Gathered fish are requirements, never
-- free inventory injected into the general purchase-cost solver.
local _,ns=...
if not ns.LoadForeverPages then return end
local E=ns.ProfEconomy
local P={};ns.ProfFishing=P
local floor,ceil,min,max=math.floor,math.ceil,math.min,math.max
-- The reviewed modular route's authored cooking guide is a reference, not a
-- client observation. All recipes still pass the dev normalized eligibility.
local guide={
    {from=1,to=50,spell=7751},{from=50,to=100,spell=7753},
    {from=100,to=175,spell=7755},{from=175,to=225,spell=20916},
    {from=225,to=300,spell=18238},
}
local function fishingData(opts)
    local source=opts.fishingData or opts.snapshot and opts.snapshot.fishingRoutes or ns.ProfFishingRoutes or {}
    local out={fish={}}
    local authored={}
    for _,stage in ipairs(source.fishingSteps or {}) do
        for _,id in ipairs(stage.fishIDs or {}) do authored[id]=true end
    end
    for id,raw in pairs(source.fish or {}) do
        local f={};for key,value in pairs(raw) do f[key]=value end
        f.areas=raw.areas or raw.a or {};f.catchRate=raw.catchRate or raw.rate
        f.seasonal=raw.seasonal or raw.season;f.timeRestricted=raw.timeRestricted or raw.night
        f.requirementsKnown=raw.restrictionsVerified==true or authored[tonumber(id)]==true
        -- A known authored guide is marked as reference. It must never be
        -- promoted into a fabricated restrictionsVerified/client evidence bit.
        f.restrictionsReference=raw.restrictionsVerified~=true and authored[tonumber(id)]==true or nil
        out.fish[id]=f
    end
    return out
end
P.Data=fishingData
local function fishRecord(data,itemID)
    local fish=data.fish
    return fish and (fish[itemID]or fish[tostring(itemID)])
end
local function clone(value)
    if type(value)~="table" then return value end
    local meta=getmetatable(value)
    if type(meta)=="table" and type(meta.__profLearningMaterialize)=="function" then
        value=meta.__profLearningMaterialize(value)
    end
    local out={};for k,v in pairs(value) do out[k]=clone(v) end;return out
end
local function vendorOK(o,snap)
    return o.unlimited==true and o.available~=false and o.purchasable~=false
        and not o.hasExtendedCost and (not o.currencyID or o.currencyID==0)
        and (not o.faction or not snap.faction or o.faction==snap.faction or o.faction=="N" or o.faction=="Neutral" or o.faction=="Both")
        and type(o.price)=="number" and o.price>=0
        and o.price<math.huge
        and type(o.quantity or o.bundleSize or 1)=="number" and (o.quantity or o.bundleSize or 1)>=1
        and (o.quantity or o.bundleSize or 1)==floor(o.quantity or o.bundleSize or 1)
end
local function capture(opts)
    return E.Capture("cooking",opts or {})
end

P.Capture=capture
local function ease(fish)
    local skill,rate
    for _,area in ipairs(fish.areas or {}) do
        local required=area.minSkill or fish.minSkill
        local observed=fish.catchRate or area.catchRate
        if required and (not skill or required<skill) then skill=required;rate=observed
        elseif required and required==skill and observed then rate=max(rate or observed,observed) end
    end
    if not skill then skill=fish.minSkill end
    return skill,rate
end
function P.Compute(opts)
    opts=opts or {};local data=fishingData(opts);local snap=P.Capture(opts)
    local routes={cookingSteps=opts.cookingGuide or guide}
    local start=max(1,min(300,floor(opts.start or (snap.professions.cooking or {}).cur or 1)))
    local target=max(start,min(300,floor(opts.target or 300)))
    local out={planVersion=2,scheme="fishing",routeMode="fishing",start=start,target=target,steps={},executionSteps={},actions={},
        mats={},fishMaterials={},formulas={},diagnostics={},blockingDiagnostics={},firstAt={},gaps={},
        total=0,matTotal=0,vendorTotal=0,ahTotal=0,formulasTotal=0,formulaAHTotal=0,formulaVendorTotal=0,
        formulaRevision=1,formulaComplete=true,completeCost=true,costComplete=true,priced=true,crafts=0,
        productAH=0,productNPC=0,productPartial=false,optimal=false,searchComplete=true,status="complete",
        targetUnlearned=not snap.professions.cooking or snap.professions.cooking.unlearned==true,
        professionPolicy=1,stamp=time and time() or 0,fishingRouteRevision=2}
    local candidates,blocked={},{}
    local function fail(code,r,id)
        local key=code..":"..tostring(r and r.spell or "")..":"..tostring(id or "")
        blocked[key]={code=code,spell=r and r.spell,recipe=r and r.key,profession="cooking",item=id}
    end
    for _,r in ipairs(snap.recipes) do
        if r.profession=="cooking" then
            local valid=true;local fish={};local skill,rate=0,1
            local learningUnknown=false
            if E.LearningEligibility then
                local eligible,reason,detail=E.LearningEligibility(r,snap)
                if not eligible then valid=false;fail(reason or "learningRequirementsUnknown",r)
                elseif detail and detail.status=="unknown"then learningUnknown=true end
            end
            local policy=E.Policy(opts.exclusions,r)
            if policy then valid=false;fail("excluded",r) end
            if r.clientUnavailable or r.cooldown or r.cooldownUnknown or r.clientPending or r.outputConflict then valid=false end
            if (r.availabilityUnknown or r.verified==false) and not r.clientAvailable
                and not (snap.known[r.key] or snap.known[r.spell]) then valid=false end
            for _,m in ipairs(r.mats or {}) do
                local f=fishRecord(data,m[1])
                if f then
                    fish[#fish+1]=m[1];local sk,rt=ease(f)
                    if not sk or not f.requirementsKnown then
                        valid=false;fail("fishingRequirementsUnknown",r,m[1])
                    else skill=max(skill,sk) end
                    if rt then rate=min(rate,rt) end
                    if f.restrictionsReference then out.fishingReference=true end
                    if f.restricted or f.seasonal or f.timeRestricted or f.uncertain then valid=false end
                else
                    local found=false
                    for _,o in ipairs(snap.offers[m[1]] or {}) do if vendorOK(o,snap) then found=true;break end end
                    local price=snap.prices[m[1]]
                    local supply=E.AuctionSupplyOf(snap,m[1])
                    local auction=not (snap.nonAuctionable or {})[m[1]] and type(price)=="number"
                        and price>0 and price<math.huge and (not supply or supply.quantity~=0)
                    if not found and not auction then
                        valid=false
                        fail(type(price)=="number" and price>0 and supply and supply.quantity==0
                            and "auctionSupplyLimited" or "materialUnavailable",r,m[1])
                    end
                end
            end
            local formula
            if valid and #fish>0 then
                formula=E.FormulaFor(r,snap)
                if formula and not formula.usable then valid=false;fail(formula.reason or "formulaUnavailable",r,formula.id) end
            end
            if valid and #fish>0 and type(r.learn)=="number" and type(r.grey)=="number" then
                candidates[#candidates+1]={r=r,fish=fish,skill=skill,rate=rate,formula=formula,learningUnknown=learningUnknown}
            end
        end
    end
    local cur=start;local guide=routes.cookingSteps or {};local guard=0
    while cur<target and guard<1000 do
        guard=guard+1
        local preferred,stageTo
        for _,stage in ipairs(guide) do
            local a,b=stage.from or stage[1],stage.to or stage[2]
            if a<=cur and cur<b then preferred=stage.spell or stage.spellID or stage[3];stageTo=b;break end
        end
        local best
        for _,c in ipairs(candidates) do
            local r=c.r
            if r.learn<=cur and cur<r.grey then
                if r.spell==preferred then best=c;break end
                local g=E.Gain(r,cur)
                if not best or c.skill<best.skill or c.skill==best.skill and
                    (c.rate>best.rate or c.rate==best.rate and (g>E.Gain(best.r,cur) or g==E.Gain(best.r,cur) and r.spell<best.r.spell)) then best=c end
            end
        end
        if not best then break end
        local r=best.r;local to=min(target,stageTo or target,r.grey)
        if best.learningUnknown then
            out.learningRequirementsUnknown=true
            local seen=false;for _,diagnostic in ipairs(out.diagnostics)do if diagnostic.code=="learningRequirementsUnknown"and diagnostic.spell==r.spell then seen=true;break end end
            if not seen then out.diagnostics[#out.diagnostics+1]={code="learningRequirementsUnknown",spell=r.spell,detail=r.key}end
        end
        -- Stop at the next learning threshold so a lower-effort valid recipe
        -- can take over. Preferred guide stages are retained through 225.
        if not preferred or r.spell~=preferred then
            for _,c in ipairs(candidates) do if cur<c.r.learn and c.r.learn<to then to=c.r.learn end end
        end
        if to<=cur then break end
        local expected=0
        for skill=cur,to-1 do
            local gain=E.Gain(r,skill);if gain<=0 then to=skill;break end
            expected=expected+1/gain
        end
        local count=max(1,ceil(expected-1e-7))
        local step=out.steps[#out.steps]
        if not step or step[3]~=r.spell then
            step={cur,to,r.spell,count,profession="cooking",role="level",reason="level",recipe=clone(r),item=r.item,
                cost=0,leveling=true,stepIndex=#out.steps+1,fishing={},fishMaterials={},fishingAreas={},actionIDs={}}
            out.steps[#out.steps+1]=step
        else step[2]=to;step[4]=step[4]+count end
        out.crafts=out.crafts+count;cur=to
    end
    local fishOf,matOf={},{}
    for _,step in ipairs(out.steps) do
        local r=step.recipe
        for _,m in ipairs(r.mats) do
            local need=m[2]*step[4];local f=fishRecord(data,m[1])
            if f then
                local entry=fishOf[m[1]]
                if not entry then
                    entry={id=m[1],count=0,need=0,source="fishing",areas=clone(f.areas or {}),minSkill=f.minSkill,
                        noGetaway=f.noGetaway,catchRate=f.catchRate,name=f.name}
                    fishOf[m[1]]=entry;out.fishMaterials[#out.fishMaterials+1]=entry
                end
                entry.count=entry.count+need;entry.need=entry.count
                step.fishing[#step.fishing+1]={id=m[1],count=need,need=need,source="fishing",areas=clone(f.areas or {})}
                step.fishMaterials=step.fishing
                for _,area in ipairs(f.areas or {}) do step.fishingAreas[#step.fishingAreas+1]=clone(area) end
            else
                local entry=matOf[m[1]]
                if not entry then entry={id=m[1],need=0};matOf[m[1]]=entry end
                entry.need=entry.need+need
            end
            out.firstAt[m[1]]=out.firstAt[m[1]] or step[1]
        end
    end
    -- Reserve teaching items first: an item can also be a later reagent, and
    -- both purchases share the same observed auction quantity.
    out.formulas,out.formulasTotal,out.formulaComplete=E.CollectFormulas(out.steps,"cooking",snap)
    local remaining={}
    for id,supply in pairs(E.ConsiderAuctionSupply(snap) and snap.auctionSupply or {}) do
        if type(supply.quantity)=="number" then remaining[id]=max(0,supply.quantity) end
    end
    local ra=ns.ProfRouteAuto
    out.formulasTotal,out.formulaComplete=0,true
    for i,entry in ipairs(out.formulas) do
        local f=entry
        if matOf[f.id] and ra and ra.PreferSharedFormula then
            f=ra.PreferSharedFormula(f,matOf[f.id].need,{snapshot=snap,auctionRemaining=remaining}) or f
            out.formulas[i]=f
        end
        out.formulasTotal=out.formulasTotal+(f.cost or 0)
        out.formulaComplete=out.formulaComplete and f.costComplete==true and f.usable==true
        out.referencePrices=out.referencePrices or f.offer and f.offer.reference
        if f.availabilityUncertain then out.diagnostics[#out.diagnostics+1]={code="formulaStockUnknown",item=f.id} end
        if f.source=="vendor" or f.source=="trainer" or f.source=="acquire" and f.acquisitionKind=="currency" then
            out.formulaVendorTotal=out.formulaVendorTotal+(f.cost or 0)
        elseif f.source=="ah" then
            out.formulaAHTotal=out.formulaAHTotal+(f.cost or 0)
            if remaining[f.id]~=nil then remaining[f.id]=max(0,remaining[f.id]-(f.count or 1)) end
        end
        for _,step in ipairs(out.steps) do
            local owns=false;for _,ref in ipairs(f.recipes or {}) do if ref.spell==step[3] then owns=true end end
            if owns then step.cost=step.cost+(f.cost or 0);step.unpriced=step.unpriced or f.unpriced;break end
        end
    end
    -- Quote the entire non-fish demand once, preserving NPC pack leftovers and
    -- any cheaper auction/NPC combination. Gathered fish never enter this list.
    local materialComplete,materialAvailable=true,true
    for id,need in pairs(matOf) do
        local entries,total,complete,reason
        if ra and ra.MaterialPurchases then
            entries,total,complete,reason=ra.MaterialPurchases(id,need.need,{snapshot=snap,auctionRemaining=remaining})
        else entries,total,complete,reason={},0,false,"materialUnavailable" end
        entries=entries or {}
        materialComplete=materialComplete and complete==true
        if complete~=true then
            local code=reason=="auctionSupplyInsufficient" and "auctionSupplyLimited" or reason or "materialUnavailable"
            out.diagnostics[#out.diagnostics+1]={code=code,item=id,required=need.need,
                available=remaining[id],profession="cooking"}
            if code=="materialUnavailable" or code=="auctionSupplyLimited" then
                materialAvailable=false
                out.blockingDiagnostics[#out.blockingDiagnostics+1]={code=code,item=id,required=need.need,
                    available=remaining[id],profession="cooking"}
            end
        end
        local ledger={}
        for _,raw in ipairs(entries) do
            local entry=clone(raw)
            entry.id=entry.id or entry[1] or id;entry.count=entry.count or entry[2] or 0
            entry[1],entry[2]=entry.id,entry.count
            if entry.source=="ah" then
                if remaining[id]~=nil and not entry.unavailable then remaining[id]=max(0,remaining[id]-entry.count) end
                out.ahTotal=out.ahTotal+(entry.cost or 0)
            elseif entry.source=="vendor" then out.vendorTotal=out.vendorTotal+(entry.cost or 0) end
            out.referencePrices=out.referencePrices or entry.reference
            out.mats[#out.mats+1]=entry
            ledger[#ledger+1]={entry=entry,used=0}
        end
        out.matTotal=out.matTotal+(total or 0)
        -- Charge each actual purchase pack at its first use, then share its
        -- leftovers across later steps regardless of the chosen purchase source.
        local index=1
        for _,step in ipairs(out.steps) do
            for _,m in ipairs(step.recipe.mats) do if m[1]==id then
                if complete~=true then step.unpriced=true end
                local left=m[2]*step[4]
                while left>0 and ledger[index] do
                    local row=ledger[index];local entry=row.entry
                    local size=entry.source=="vendor" and (entry.bundleSize or 1) or 1
                    local quantity=min(left,max(0,entry.count-row.used))
                    local packPrice=entry.bundlePrice or (entry.cost or 0)/max(1,entry.count)*size
                    step.cost=step.cost+(ceil((row.used+quantity)/size)-ceil(row.used/size))*packPrice
                    row.used=row.used+quantity;left=left-quantity
                    if row.used>=entry.count then index=index+1 end
                end
            end end
        end
    end
    out.vendorTotal=out.vendorTotal+out.formulaVendorTotal;out.ahTotal=out.ahTotal+out.formulaAHTotal
    out.total=out.matTotal+out.formulasTotal
    out.costComplete=out.formulaComplete and materialComplete and not out.learningRequirementsUnknown;out.completeCost=out.costComplete;out.priced=out.costComplete
    out.plannedTo=cur;out.targetReached=cur>=target;out.partial=cur>start and cur<target
    out.feasible=(#out.steps>0 or out.targetReached) and materialAvailable
    if not out.costComplete then out.status="incomplete" end
    if not out.targetReached then
        out.status="incomplete";out.gaps={{cur,target}};out.remainingUnknown=true
        for _,d in pairs(blocked) do out.blockingDiagnostics[#out.blockingDiagnostics+1]=d end
        out.blockingDiagnostics[#out.blockingDiagnostics+1]={code="fishingRecipeGap",profession="cooking"}
        if not out.feasible then out.diagnostics=clone(out.blockingDiagnostics) end
    end
    for i,step in ipairs(out.steps) do
        local id="fishing-cook:"..i;step.actionID=id;step.actionIDs={id}
        local inputs={};for _,m in ipairs(step.recipe.mats) do inputs[#inputs+1]={m[1],m[2]*step[4]} end
        out.actions[#out.actions+1]={id=id,type="craft",profession="cooking",spell=step[3],count=step[4],from=step[1],to=step[2],
            reason="level",inputs=inputs,item=step.item,outputs=step.item and {{step.item,(step.recipe.count or 1)*step[4]}} or {}}
    end
    out.executionSteps=clone(out.steps)
    local xp=ns.ProfExecution
    if xp and xp.NormalizePlan then out=xp.NormalizePlan("cooking",out) or out end
    table.sort(out.mats,function(a,b)return a.id<b.id end)
    table.sort(out.fishMaterials,function(a,b)return (out.firstAt[a.id] or 0)<(out.firstAt[b.id] or 0) end)
    E.SummarizeAuctionSupply(out,snap)
    if ns.ProfRecovery then ns.ProfRecovery.Apply(out,snap) end
    return ra and ra.StampVendorQuotes and ra.StampVendorQuotes(out) or out
end

-- Replace only the special cooking route. The main TOC and default dev source
-- tables remain authoritative; no catalogue addon or loading gate is added.
if ns.ProfRouteAuto then
    ns.ProfRouteAuto.ComputeFishing=function(slug,opts)
        if slug~="cooking" then return nil end
        return P.Compute(opts)
    end
end
