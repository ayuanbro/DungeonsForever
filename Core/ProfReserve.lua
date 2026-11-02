local _,ns=...
if not ns.LoadForeverPages then return end
local E=ns.ProfEconomy
local R={};ns.ProfReserve=R
local ceil,floor,min,max=math.ceil,math.floor,math.min,math.max
local levels={off=0,standard=.90,ample=.95}
function R.Mode(value) return levels[value] and value or "ample" end
function R.Label(value)
    local L=ns.L
    return value=="off" and L["不准备余量"] or value=="standard" and L["适量备用"] or L["充足备用"]
end

function R.Attempts(recipe,start,goal,confidence,tick)
    start,goal=floor(start),ceil(goal)
    if start>=goal then return 0 end
    if start<(recipe.learn or 1) then return nil,"skill" end
    local rates,deterministic={},true
    for skill=start,goal-1 do
        local p=E.Gain(recipe,skill)
        if not p or p<=0 then return nil,"grey" end
        rates[skill-start]=p;deterministic=deterministic and p>=1
    end
    local points=goal-start
    if deterministic then return points end
    local distribution={[0]=1};local complete=0
    for attempt=1,8192 do
        if tick and tick()==false then return nil,"budget" end
        local nextState={}
        for k=0,min(points-1,attempt-1) do
            local mass=distribution[k] or 0;local p=rates[k]
            nextState[k]=(nextState[k] or 0)+mass*(1-p)
            if k+1==points then complete=complete+mass*p
            else nextState[k+1]=(nextState[k+1] or 0)+mass*p end
        end
        if complete+1e-12>=confidence then return attempt end
        distribution=nextState
    end
    return nil,"budget"
end

function R.Build(plan,snapshot,opts,tick)
    opts=opts or {};local mode=R.Mode(opts.reserveMode)
    local result={mode=mode,confidence=levels[mode],model="skill_colour_estimate",
        coverageComplete=true,priced=true,complete=true,total=0,steps={},materials={},mats={},diagnostics={}}
    if mode=="off" then
        for _,s in ipairs(plan.executionSteps or {}) do s.reserve=nil end
        return result
    end
    local steps=plan.executionSteps or {};local actionStep={}
    local work=0
    local function checkpoint()
        work=work+1
        if work%64==0 and tick then tick() end
        return work<=100000
    end
    local function issue(reason,item)
        result.complete=false
        result.diagnostics[#result.diagnostics+1]={code=reason,itemID=item}
    end
    local eligible,risks={},0
    for i,s in ipairs(steps) do
        for _,id in ipairs(s.actionIDs or {s.actionID}) do actionStep[id]=i end
        result.steps[i]={extraCrafts=0,requiredOutputs={},allocations={}}
        if not s.kind and not s.checkpoint and not s.tool and not s.fractionalTransition
            and (s.expectedGain or 0)>0 and s.recipe and s.goalSkill then
            eligible[i]=true
            if E.Gain(s.recipe,ceil(s.goalSkill)-1)<1 then risks=risks+1 end
        end
    end
    local lower={}
    for p,v in pairs(snapshot.professions or {}) do lower[p]=v.cur or 1 end
    lower[plan.slug or opts.profession]=plan.start or opts.start or 1
    local initial={}
    for i,s in ipairs(steps) do
        local row=result.steps[i];local recipe=s.recipe or {}
        local p=s.profession;local from=min(s[1] or 1,lower[p] or s[1] or 1)
        if eligible[i] then
            local count,reason=R.Attempts(recipe,from,s.goalSkill,1-(1-levels[mode])/max(1,risks),checkpoint)
            if count then
                row.extraCrafts=max(0,count-(s.expectedCrafts or s[4] or 0));lower[p]=s.goalSkill
            else
                result.coverageComplete=false;issue(reason,s.item)
                lower[p]=from
            end
        elseif s.checkpoint then lower[p]=s[2]
        elseif not s.kind then
            for _=1,(s.expectedCrafts or s[4] or 0) do
                if E.Gain(recipe,from)<1 then break end
                from=from+1
            end
            lower[p]=from
        end
        if recipe.outputMin and recipe.outputMax and recipe.outputMin~=recipe.outputMax then
            result.coverageComplete=false;issue("variable_output",s.item)
        end
        initial[i]=row.extraCrafts
    end

    local pools,sources,quotes,baseAH={},{},{},{}
    local position=0
    local function add(item,count,index,made,source)
        if not item or count<=0 then return end
        pools[item]=pools[item] or {}
        pools[item][#pools[item]+1]={left=count,index=index,made=made,source=source}
    end
    for _,a in ipairs(plan.actions or {}) do
        local index=actionStep[a.id]
        if index then position=index end
        for _,m in ipairs(a.inputs or {}) do
            local need=m[2]
            for pass=1,2 do for _,lot in ipairs(pools[m[1]] or {}) do
                if lot.made==(pass==2) and need>0 then
                    local n=min(need,lot.left);lot.left=lot.left-n;need=need-n
                    if n>0 and index then
                        sources[index]=sources[index] or {}
                        local previous=sources[index][m[1]]
                        if not previous or previous.source and previous.source.type=="seed" then sources[index][m[1]]=lot end
                    end
                end
            end end
            if need>0 then issue("provenance",m[1]);result.coverageComplete=false end
        end
        if a.type=="buy" then
            add(a.item,a.count,position+.5,false,a)
            quotes[a.item]=quotes[a.item] or {};quotes[a.item][#quotes[a.item]+1]=a
        elseif a.type=="seed" and a.usableOutput~=false then add(a.item,a.count,0,false,a)
        elseif a.usableOutput~=false then
            for _,m in ipairs(a.outputs or {}) do add(m[1],m[2],index or position,a.type=="craft",a) end
        end
        if (a.type=="buy" or a.type=="formula") and a.source=="ah" then baseAH[a.item]=(baseAH[a.item] or 0)+(a.count or 1) end
        checkpoint()
    end
    local retained=E.Copy(plan.retainedToolItems or {})
    for _,s in ipairs(steps) do if s.tool and (s.toolItem or s.item) then retained[s.toolItem or s.item]=max(1,retained[s.toolItem or s.item] or 0) end end
    for item,n in pairs(retained) do
        for _,lot in ipairs(pools[item] or {}) do local used=min(n,lot.left);lot.left=lot.left-used;n=n-used end
    end
    for i,s in ipairs(steps) do
        local per=s.outputMin or s.recipe and s.recipe.count or 0
        if initial[i]>0 and s.item and per>0 then add(s.item,initial[i]*per,i,true,{reserve=true}) end
    end
    local gross,spareUsed,requests={},{},{}
    local function allocation(index,consumer,item,n)
        if not index or not steps[index] or n<=0 then return end
        local row=result.steps[index]
        row.requiredOutputs[item]=(row.requiredOutputs[item] or 0)+n
        row.allocations[#row.allocations+1]={consumerID=steps[consumer].segmentID,itemID=item,count=n}
    end
    local demand,inputs
    inputs=function(index,count,depth)
        for _,m in ipairs((steps[index].recipe or {}).mats or {}) do demand(m[1],m[2]*count,index,depth+1) end
    end
    demand=function(item,n,consumer,depth)
        if n<=0 then return end
        if depth>#steps+1 or not checkpoint() then issue("dependency",item);return end
        for _,lot in ipairs(pools[item] or {}) do
            if lot.left>0 and lot.index<consumer and n>0 then
                local take=min(n,lot.left);lot.left=lot.left-take;n=n-take
                if steps[lot.index] then allocation(lot.index,consumer,item,take)
                else
                    gross[item]=(gross[item] or 0)+take;spareUsed[item]=(spareUsed[item] or 0)+take
                end
            end
        end
        if n<=0 then return end
        local origin=sources[consumer] and sources[consumer][item]
        local producer=origin and steps[origin.index]
        local per=producer and (producer.outputMin or producer.recipe and producer.recipe.count or 0)
        if producer and origin.index<consumer and per>0 and not producer.tool then
            local count=ceil(n/per);local row=result.steps[origin.index]
            row.extraCrafts=row.extraCrafts+count
            allocation(origin.index,consumer,item,n)
            add(item,count*per-n,origin.index,not producer.kind,{reserve=true})
            inputs(origin.index,count,depth)
        else
            gross[item]=(gross[item] or 0)+n;requests[item]=(requests[item] or 0)+n
        end
    end
    for i,n in ipairs(initial) do if n>0 then inputs(i,n,0) end end
    local ids={};for id in pairs(gross) do ids[#ids+1]=id end;table.sort(ids)
    for _,id in ipairs(ids) do
        local frozen={offers={},prices={},auctionSupply={},nonAuctionable=snapshot.nonAuctionable,
            considerAuctionSupply=snapshot.considerAuctionSupply,faction=snapshot.faction}
        local offers,seen={},{}
        for _,a in ipairs(quotes[id] or {}) do
            if a.source=="ah" then frozen.prices[id]=a.cost/a.count
            elseif a.source=="vendor" then
                local key=tostring(a.npcID)..":"..tostring(a.bundleSize)..":"..tostring(a.bundlePrice)
                if not seen[key] then
                    local offer=E.Copy(a);offer.price=a.bundlePrice;offer.quantity=a.bundleSize
                    offers[#offers+1]=offer;seen[key]=true
                end
            end
        end
        if not quotes[id] then
            offers=E.Copy(snapshot.offers and snapshot.offers[id] or {})
            frozen.prices[id]=snapshot.prices and snapshot.prices[id]
        end
        frozen.offers[id]=offers
        local supply=snapshot.auctionSupply and snapshot.auctionSupply[id]
        local remaining=snapshot.considerAuctionSupply~=false and supply and max(0,(supply.quantity or 0)-(baseAH[id] or 0)) or nil
        if supply then frozen.auctionSupply[id]=E.Copy(supply);frozen.auctionSupply[id].quantity=remaining end
        local need=requests[id] or 0
        local purchases,cost,complete=ns.ProfRouteAuto.MaterialPurchases(id,need,{snapshot=frozen,auctionRemaining={[id]=remaining}})
        if need==0 then
            local templates=ns.ProfRouteAuto.MaterialPurchases(id,1,{snapshot=frozen,auctionRemaining={[id]=remaining}})
            for _,entry in ipairs(templates or {}) do
                local quote=E.Copy(entry);quote[2]=0;quote.count=0;quote.need=0;quote.cost=0
                quote.reserve=true;quote.unavailable=nil;quote.unpriced=nil
                result.mats[#result.mats+1]=quote
            end
        end
        local priced,covered=true,0
        for _,entry in ipairs(purchases or {}) do
            local copy=E.Copy(entry);copy.reserve=true;result.mats[#result.mats+1]=copy
            if entry.unpriced or entry.cost==nil then priced=false end
            if not entry.unavailable and not entry.unpriced then covered=covered+(entry.count or entry[2] or 0)
            elseif entry.source=="ah" and not entry.unpriced and remaining then covered=covered+min(remaining,entry.count or entry[2] or 0) end
        end
        result.materials[#result.materials+1]={id=id,count=gross[id],spare=spareUsed[id] or 0,
            purchaseNeed=need,purchases=E.Copy(purchases or {}),cost=priced and cost or nil,
            uncovered=max(0,need-covered)}
        if not priced then result.priced=false;issue("quote",id) end
        if complete==false then issue("supply",id) end
        if covered<need then issue("supply",id) end
        result.total=result.total+(cost or 0)
    end
    result.knownTotal=result.total
    if not result.priced then result.total=nil end
    for i,s in ipairs(steps) do s.reserve=result.steps[i] end
    return result
end

function R.Remaining(plan,casts,disabled,completed)
    local need,byConsumer={},{}
    if disabled or not plan.reserve or plan.reserve.mode=="off" then return need end
    for i,s in ipairs(plan.executionSteps or {}) do
        local row=s.reserve or plan.reserve.steps[i] or {}
        local extra=max(0,(row.extraCrafts or 0)-max(0,(casts and casts[s.segmentID] or 0)-(s.expectedCrafts or s[4] or 0)))
        if completed and completed[s.segmentID] then extra=0 end
        local inputs={};byConsumer[s.segmentID]=inputs
        for _,m in ipairs((s.recipe or {}).mats or {}) do inputs[m[1]]=(inputs[m[1]] or 0)+extra*m[2] end
    end
    for _,s in ipairs(plan.executionSteps or {}) do for _,a in ipairs(s.reserve and s.reserve.allocations or {}) do
        local inputs=byConsumer[a.consumerID]
        if inputs then inputs[a.itemID]=max(0,(inputs[a.itemID] or 0)-a.count) end
    end end
    for _,inputs in pairs(byConsumer) do for item,n in pairs(inputs) do need[item]=(need[item] or 0)+n end end
    return need
end
