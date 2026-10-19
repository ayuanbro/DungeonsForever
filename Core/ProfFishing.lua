-- A self-fished cooking reference route. Gathered fish are requirements, never
-- free inventory injected into the general purchase-cost solver.
local _,ns=...
if not ns.LoadForeverPages then return end
local E=ns.ProfEconomy
local P={};ns.ProfFishing=P
local floor,ceil,min,max=math.floor,math.ceil,math.min,math.max
local function clone(value)
    if type(value)~="table" then return value end
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
    if opts.snapshot then return E.Index(clone(opts.snapshot)) end
    local snap={recipes={},known={},prices={},offers={},formulaOffers={},professions=E.Professions(),auctionSupply={}}
    local faction=UnitFactionGroup and UnitFactionGroup("player")
    snap.faction=faction=="Alliance" and "A" or faction=="Horde" and "H" or faction
    local all=ns.EnsureProfRecipes and ns.EnsureProfRecipes({"cooking"}) or ns.ProfRecipes or {}
    local seen={}
    for _,row in ipairs(all.cooking and all.cooking.rows or {}) do
        if E.ReadRecipe then pcall(E.ReadRecipe,row[1]) end
        local r=E.Normalize(row,"cooking","rows")
        if r then snap.recipes[#snap.recipes+1]=r;seen[r.spell]=true;snap.known[r.key]=E.Known(r.spell) end
    end
    for _,spell in ipairs(ns.ProfFishingRoutes and ns.ProfFishingRoutes.recipeSpells or {}) do
        if not seen[spell] then
            local r=E.FindRecipe("cooking",spell)
            if r then snap.recipes[#snap.recipes+1]=r;snap.known[r.key]=E.Known(r.spell) end
        end
    end
    if not snap.professions.cooking then snap.professions.cooking={cur=opts.start or 1,max=75,unlearned=true} end
    local ids={}
    for _,r in ipairs(snap.recipes) do
        for _,m in ipairs(r.mats or {}) do ids[m[1]]=true end
        if r.formula then ids[r.formula]=true end
    end
    local db,ra=ns.VendorPriceDB,ns.ProfRouteAuto
    for id in pairs(ids) do
        if ra and ra.AHPriceOf then snap.prices[id]=ra.AHPriceOf(id) end
        if db and db.GetOffers then snap.offers[id]=db.GetOffers(id,snap) end
        if db and db.GetFormulaOffers then snap.formulaOffers[id]=db.GetFormulaOffers(id,snap) end
        local supply=E.AuctionSupplyOf(nil,id);if supply then snap.auctionSupply[id]=supply end
    end
    return E.Index(snap)
end
P.Capture=capture
local function ease(fish)
    local skill,rate=math.huge,0
    for _,area in ipairs(fish.areas or {}) do
        local required=area.minSkill or fish.minSkill
        if required and required<skill then skill=required;rate=fish.catchRate or area.catchRate or 0
        elseif required==skill then rate=max(rate,fish.catchRate or area.catchRate or 0) end
    end
    if skill==math.huge then skill=fish.minSkill or 10000 end
    return skill,rate
end
function P.Compute(opts)
    opts=opts or {};local data=ns.ProfFishingRoutes or {};local snap=P.Capture(opts)
    local start=max(1,min(300,floor(opts.start or (snap.professions.cooking or {}).cur or 1)))
    local target=max(start,min(300,floor(opts.target or 300)))
    local out={planVersion=2,scheme="fishing",routeMode="fishing",start=start,target=target,steps={},executionSteps={},actions={},
        mats={},fishMaterials={},formulas={},diagnostics={},blockingDiagnostics={},firstAt={},gaps={},
        total=0,matTotal=0,vendorTotal=0,ahTotal=0,formulasTotal=0,formulaAHTotal=0,formulaVendorTotal=0,
        formulaRevision=1,formulaComplete=true,completeCost=true,costComplete=true,priced=true,crafts=0,
        productAH=0,productNPC=0,productPartial=false,optimal=false,searchComplete=true,status="complete",
        targetUnlearned=not snap.professions.cooking or snap.professions.cooking.unlearned==true,
        professionPolicy=1,stamp=time and time() or 0,fishingRouteRevision=1}
    local candidates,blocked={},{}
    local function fail(code,r,id)
        local key=code..":"..tostring(r and r.spell or "")..":"..tostring(id or "")
        blocked[key]={code=code,spell=r and r.spell,recipe=r and r.key,profession="cooking",item=id}
    end
    for _,r in ipairs(snap.recipes) do
        if r.profession=="cooking" then
            local valid=true;local fish={};local skill,rate=0,1
            local policy=E.Policy(opts.exclusions,r)
            if policy then valid=false;fail("excluded",r) end
            if r.clientUnavailable or r.cooldown or r.cooldownUnknown or r.clientPending or r.outputConflict then valid=false end
            if (r.availabilityUnknown or r.verified==false) and not r.clientAvailable
                and not (snap.known[r.key] or snap.known[r.spell]) then valid=false end
            if opts.learnedOnly and not out.targetUnlearned and not (snap.known[r.key] or snap.known[r.spell]) then valid=false end
            for _,m in ipairs(r.mats or {}) do
                local f=data.fish and data.fish[m[1]]
                if f then
                    fish[#fish+1]=m[1];local sk,rt=ease(f);skill=max(skill,sk);rate=min(rate,rt)
                    if f.restricted or f.seasonal or f.timeRestricted or f.uncertain then valid=false end
                else
                    local found=false
                    for _,o in ipairs(snap.offers[m[1]] or {}) do if vendorOK(o,snap) then found=true;break end end
                    if not found then valid=false end
                end
            end
            local formula
            if valid and #fish>0 then
                formula=E.FormulaFor(r,snap)
                if formula and not formula.usable then valid=false;fail(formula.reason or "formulaUnavailable",r,formula.id) end
            end
            if valid and #fish>0 and type(r.learn)=="number" and type(r.grey)=="number" then
                candidates[#candidates+1]={r=r,fish=fish,skill=skill,rate=rate,formula=formula}
            end
        end
    end
    local cur=start;local groups={};local guide=data.cookingSteps or {};local guard=0
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
        local step=groups[r.key]
        if not step then
            step={cur,to,r.spell,count,profession="cooking",role="level",reason="level",recipe=clone(r),item=r.item,
                cost=0,leveling=true,stepIndex=#out.steps+1,fishing={},fishMaterials={},fishingAreas={},actionIDs={}}
            out.steps[#out.steps+1]=step;groups[r.key]=step
        else step[2]=to;step[4]=step[4]+count end
        out.crafts=out.crafts+count;cur=to
    end
    local fishOf,matOf={},{}
    for _,step in ipairs(out.steps) do
        local r=step.recipe
        for _,m in ipairs(r.mats) do
            local need=m[2]*step[4];local f=data.fish and data.fish[m[1]]
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
                if not entry then entry={id=m[1],need=0,count=0,source="vendor",vendor=true};matOf[m[1]]=entry end
                entry.need=entry.need+need
            end
            out.firstAt[m[1]]=out.firstAt[m[1]] or step[1]
        end
    end
    -- Share merchant pack leftovers across all steps, and charge each new pack
    -- only at the step that first needs it.
    local materialComplete=true
    for id,entry in pairs(matOf) do
        local best,bestCost
        for _,offer in ipairs(snap.offers[id] or {}) do
            if vendorOK(offer,snap) then
                local size=offer.quantity or offer.bundleSize or 1;local cost=ceil(entry.need/size)*offer.price
                if not best or cost<bestCost then best,bestCost=offer,cost end
            end
        end
        if best then
            local size=best.quantity or best.bundleSize or 1
            entry.count=ceil(entry.need/size)*size;entry[1],entry[2]=id,entry.count
            entry.cost=bestCost;entry.unit=best.price/size;entry.bundleSize=size;entry.bundlePrice=best.price
            entry.npcID=best.npcID;entry.url=best.url;entry.reference=best.reference;entry.estimated=best.estimated
            entry.quoteSource=best.source;entry.priceBasis=best.priceBasis;entry.verifiedAt=best.verifiedAt
            if best.estimated and not best.reference then
                materialComplete=false;out.diagnostics[#out.diagnostics+1]={code="vendorEstimate",item=id}
            end
            out.referencePrices=out.referencePrices or best.reference
            local used=0
            for _,step in ipairs(out.steps) do
                for _,m in ipairs(step.recipe.mats) do if m[1]==id then
                    local nextUsed=used+m[2]*step[4]
                    step.cost=step.cost+(ceil(nextUsed/size)-ceil(used/size))*best.price;used=nextUsed
                end end
            end
            out.mats[#out.mats+1]=entry;out.matTotal=out.matTotal+bestCost
        end
    end
    out.formulas,out.formulasTotal,out.formulaComplete=E.CollectFormulas(out.steps,"cooking",snap)
    for _,f in ipairs(out.formulas) do
        out.referencePrices=out.referencePrices or f.offer and f.offer.reference
        if f.availabilityUncertain then out.diagnostics[#out.diagnostics+1]={code="formulaStockUnknown",item=f.id} end
        if f.source=="vendor" then out.formulaVendorTotal=out.formulaVendorTotal+(f.cost or 0)
        elseif f.source=="ah" then out.formulaAHTotal=out.formulaAHTotal+(f.cost or 0) end
        for _,step in ipairs(out.steps) do
            local owns=false;for _,ref in ipairs(f.recipes or {}) do if ref.spell==step[3] then owns=true end end
            if owns then step.cost=step.cost+(f.cost or 0);step.unpriced=step.unpriced or f.unpriced;break end
        end
    end
    out.vendorTotal=out.matTotal+out.formulaVendorTotal;out.ahTotal=out.formulaAHTotal
    out.total=out.matTotal+out.formulasTotal
    out.costComplete=out.formulaComplete and materialComplete;out.completeCost=out.costComplete;out.priced=out.costComplete
    out.plannedTo=cur;out.targetReached=cur>=target;out.partial=cur>start and cur<target
    out.feasible=#out.steps>0 or out.targetReached
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
    table.sort(out.mats,function(a,b)return a.id<b.id end)
    table.sort(out.fishMaterials,function(a,b)return (out.firstAt[a.id] or 0)<(out.firstAt[b.id] or 0) end)
    E.SummarizeAuctionSupply(out,snap)
    return out
end
