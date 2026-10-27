-- Frozen sale estimates and a separate recursive cost ledger. Purchase quotes
-- remain in ProfEconomy; selling a future output never supplies buying money.
local _,ns=...
if not ns.LoadForeverPages then return end
local R={REVISION=1};ns.ProfRecovery=R
local floor,min,max,ceil=math.floor,math.min,math.max,math.ceil
local function copy(t,tick)
    if type(t)~="table" then return t end
    local o={};local n=0
    for k,v in pairs(t) do
        o[k]=copy(v,tick);n=n+1
        if tick and n%32==0 then tick() end
    end
    if tick then tick() end
    return o
end
local function amount(n) return type(n)=="number" and n==n and n>=0 and n<math.huge end
local function percent(n) return amount(n) and n<=100 end
local function now() return time and time() or 0 end
local requestedItems={}
local function requestMissingItem(id)
    local dg=ns.ProfHost and ns.ProfHost.DG
    if not requestedItems[id] and dg and type(dg.RequestItem)=="function" then
        requestedItems[id]=true;pcall(dg.RequestItem,id)
    end
end

-- Zero is a loaded, valid sell price. Nil remains retryable client data.
function R.NPCSellPriceOf(id)
    for _,fn in ipairs({C_Item and C_Item.GetItemInfo or false,GetItemInfo or false}) do
        if type(fn)=="function" then
            local values={pcall(fn,id)}
            if values[1] and amount(values[12]) then return floor(values[12]) end
        end
    end
    if C_Item and type(C_Item.GetItemSellPrice)=="function" then
        local ok,value=pcall(C_Item.GetItemSellPrice,id)
        if ok and amount(value) then return floor(value) end
    end
end
local function bound(id,s)
    if s.nonAuctionable and s.nonAuctionable[id] then return true end
    local fn=C_Item and C_Item.GetItemInfo or GetItemInfo
    if type(fn)=="function" then
        local v={pcall(fn,id)}
        if v[1] then return v[15]==1 or v[15]==4 end
    end
    return false
end
function R.Fee(snapshot,opts)
    opts=opts or {}
    if percent(opts.recoveryFeePercent) then return opts.recoveryFeePercent,"manual",false end
    -- The Forever C_AuctionHouse declarations expose deposits, but no cut
    -- getter. Accept an explicit reliable client observation if one is supplied;
    -- never mistake CalculateItemDeposit (which needs a real bag location) for it.
    local client=snapshot and snapshot.auctionFee
    if type(client)=="table" and client.reliable==true and percent(client.percent) then
        return client.percent,client.source or "client",false
    end
    local constants=type(Auctionator)=="table" and Auctionator.Constants
    local factor=type(constants)=="table" and constants.AfterAHCut
    if amount(factor) and factor<=1 then return (1-factor)*100,"auctionator-reference",true end
    return nil,"unknown",false
end
local function livePrice(id)
    local ra=ns.ProfRouteAuto
    return ra and ra.AHPriceOf and ra.AHPriceOf(id)
end
-- Retain the dev price-revaluation API while applying the same evidence
-- thresholds as freshly captured quotes.
local function rerate(q,fee)
    q.auctionNet=q.auctionGross and fee and floor(q.auctionGross*(100-fee)/100+1e-9) or nil
    q.assumedAllSold=nil;q.missing=nil;q.unsellable=q.bound and true or nil
    if q.npcUnit~=nil then
        q.unit=q.npcUnit;q.source="npc"
        if not q.bound and q.auctionNet and q.auctionNet-q.npcUnit>100
            and q.supplyReliable and (q.quantity or 0)>=40 then
            q.unit=q.auctionNet;q.source="ah";q.assumedAllSold=true
        end
    else q.unit=0;q.source="unknown";q.missing=true end
    return q
end
R.Rerate=rerate
local function quote(id,s,fee,stamp,live)
    local npc
    if not live and s.sellPrices then npc=s.sellPrices[id] else npc=R.NPCSellPriceOf(id) end
    if not amount(npc) then npc=nil else npc=floor(npc) end
    local auction=live and livePrice(id) or s.prices and s.prices[id]
    if not amount(auction) or auction==0 then auction=nil end
    local b=ns.AuctionBridge
    local supply=live and b and b.GetAuctionSupply and b.GetAuctionSupply(id,true) or s.auctionSupply and s.auctionSupply[id]
    local age=type(supply)=="table" and type(supply.observedAt)=="number" and stamp-supply.observedAt
    local reliable=type(supply)=="table" and amount(supply.quantity) and supply.quantity==floor(supply.quantity)
        and supply.complete==true and supply.ownerExcluded==true
        and supply.source=="client-auction-results"
        and age and age>=0 and age<=172800 or false
    local blocked=bound(id,live and {} or s)
    local net=auction and fee and floor(auction*(100-fee)/100+1e-9) or nil
    local q={id=id,npcUnit=npc,auctionGross=auction,auctionNet=net,bound=blocked,
        quantity=supply and supply.quantity,observedAt=supply and supply.observedAt,
        complete=supply and supply.complete,ownerExcluded=supply and supply.ownerExcluded,
        supplySource=supply and supply.source,supplyReliable=reliable,
        market=supply and supply.market,batch=supply and supply.batch}
    -- Without N the spread cannot be established. Missing is not a zero-price
    -- assumption even when a seemingly attractive auction quote is available.
    return rerate(q,fee)
end
local identityFields={"npcUnit","auctionGross","auctionNet","bound","quantity","observedAt","complete","ownerExcluded","supplySource","supplyReliable","market","batch","source","unit","missing"}
local function identity(q)
    local p={};for _,key in ipairs(identityFields) do p[#p+1]=key.."="..tostring(q[key]) end
    return table.concat(p,";")
end
function R.Options(opts)
    opts=opts or {}
    local db=DungeonsForeverDB and DungeonsForeverDB.prof
    if db then
        if opts.recoveryEnabled==nil and db.recoveryEnabled~=nil then opts.recoveryEnabled=db.recoveryEnabled end
        if opts.recoveryFeePercent==nil and type(db.recoveryFeePercent)=="number" then
            opts.recoveryFeePercent=db.recoveryFeePercent
        end
    end
    return opts
end
function R.Capture(snapshot,opts,tick)
    opts=R.Options(opts);snapshot=snapshot or {}
    -- A supplied route input is already immutable. In particular, a coroutine
    -- must not pick up a new quote half way through its search.
    if snapshot.recovery and snapshot.recovery.revision==R.REVISION and snapshot.recovery.quotes then
        local old=snapshot.recovery
        if opts.recoveryEnabled~=nil and opts.recoveryEnabled~=old.enabled
            or percent(opts.recoveryFeePercent) and opts.recoveryFeePercent~=old.feePercent then
            local r=copy(old,tick)
            if opts.recoveryEnabled~=nil then r.enabled=opts.recoveryEnabled~=false end
            if percent(opts.recoveryFeePercent) then
                r.feePercent=opts.recoveryFeePercent;r.feeSource="manual";r.feeReference=false;r.feeOverride=opts.recoveryFeePercent
                for _,q in pairs(r.quotes) do
                    q.auctionNet=q.auctionGross and floor(q.auctionGross*(100-r.feePercent)/100+1e-9) or nil
                    q.unit=q.npcUnit or 0;q.source=q.npcUnit~=nil and "npc" or "unknown";q.assumedAllSold=nil
                    if q.npcUnit~=nil and not q.bound and q.auctionNet and q.auctionNet-q.npcUnit>100
                        and q.supplyReliable and (q.quantity or 0)>=40 then q.unit=q.auctionNet;q.source="ah";q.assumedAllSold=true end
                    if tick then tick() end
                end
            end
            snapshot.recovery=r
        end
        return snapshot.recovery
    end
    local fee,source,reference=R.Fee(snapshot,opts)
    local r={revision=R.REVISION,enabled=opts.recoveryEnabled~=false,feePercent=fee,
        feeSource=source,feeReference=reference,feeOverride=opts.recoveryFeePercent,
        clientFee=copy(snapshot.auctionFee,tick),
        capturedAt=snapshot.stamp or now(),quotes={}}
    for _,recipe in ipairs(snapshot.recipes or {}) do
        if type(recipe.item)=="number" and recipe.item>0 and (recipe.count or 1)>0 then
            r.quotes[recipe.item]=quote(recipe.item,snapshot,fee,r.capturedAt,false)
            if r.quotes[recipe.item].missing then requestMissingItem(recipe.item) end
        end
        if tick then tick() end
    end
    snapshot.recovery=r
    return r
end
function R.StateRevenue(state,snapshot)
    local total=0
    for id,count in pairs(state and state.produced or {}) do
        local q=snapshot and snapshot.recovery and snapshot.recovery.quotes[id]
        local retained=snapshot and snapshot.retainedToolItems and snapshot.retainedToolItems[id] or 0
        local purchased=max(0,((state.inv or {})[id] or 0)-count)
        local sale=max(0,count-max(0,retained-purchased))
        if q and amount(count) then total=total+sale*(q.unit or 0) end
    end
    return total
end
function R.Objective(state,snapshot)
    local r=snapshot and snapshot.recovery
    return (state and state.money or 0)-(r and r.enabled and R.StateRevenue(state,snapshot) or 0)
end
local function changed(result,opts)
    local old=result and result.recoverySnapshot
    if not old or result.recoveryRevision~=R.REVISION then return true end
    opts=opts or {recoveryEnabled=old.enabled,recoveryFeePercent=old.feeOverride}
    if (opts.recoveryEnabled~=false)~=old.enabled then return true end
    local supplied=opts.snapshot
    if supplied and supplied.recovery and supplied.recovery.revision==R.REVISION then
        local current=supplied.recovery
        if current.enabled~=old.enabled or current.feePercent~=old.feePercent or current.feeSource~=old.feeSource then return true end
        for id,q in pairs(old.quotes or {}) do
            if not current.quotes[id] or identity(current.quotes[id])~=identity(q) then return true end
        end
        return false
    end
    local fee,source,reference=R.Fee(supplied or {auctionFee=old.clientFee},opts)
    if fee~=old.feePercent or source~=old.feeSource or reference~=old.feeReference then return true end
    for id,q in pairs(old.quotes or {}) do
        if identity(quote(id,supplied or {},fee,now(),not supplied))~=identity(q) then return true end
    end
    return false
end
local changedMemo=setmetatable({},{__mode="k"})
function R.Invalidate() changedMemo=setmetatable({},{__mode="k"}) end
function R.Changed(result,opts)
    -- HUD and page refreshes often read the same result in one frame. Bound the
    -- live reads to once per second; price/item notifications clear this memo.
    -- Injected snapshots remain deterministic and never use the live cache.
    if not result or opts and opts.snapshot or type(GetTime)~="function" then return changed(result,opts) end
    local stamp=GetTime();local bridge=ns.AuctionBridge
    local revision=bridge and bridge.SupplyRevision and bridge.SupplyRevision() or 0
    local signature=tostring(opts and opts.recoveryEnabled)..":"..tostring(opts and opts.recoveryFeePercent)..":"..tostring(revision)
    local previous=changedMemo[result]
    if previous and previous.signature==signature and stamp>=previous.at and stamp-previous.at<1 then return previous.value end
    local value=changed(result,opts)
    changedMemo[result]={signature=signature,at=stamp,value=value}
    return value
end

local function recipeFor(step,snapshot)
    if step.recipe then return step.recipe end
    local key=tostring(step.profession or snapshot.slug or "")..":"..tostring(step[3])
    if snapshot.byKey and snapshot.byKey[key] then return snapshot.byKey[key] end
    for _,r in ipairs(snapshot.recipes or {}) do if r.spell==step[3] and (not step.profession or r.profession==step.profession) then return r end end
end
local function trace(result,snapshot)
    local recorded=result.actions and #result.actions>0
    if recorded then
        for _,a in ipairs(result.actions) do
            if a.type=="buy" or a.type=="formula" then return result.actions end
        end
        -- Fishing records crafts but its purchases live only in mats/formulas.
        if #(result.mats or {})==0 and #(result.formulas or {})==0 then return result.actions end
    end
    -- Fixed guides, legacy scoring, and fishing do not have a solver action log.
    -- Their already selected purchases and recipe snapshots are sufficient for
    -- a read-only replay; this does not change their recipe choices.
    local out={}
    for _,m in ipairs(result.mats or {}) do
        local n=m.count or m[2] or m.need or 0
        out[#out+1]={type="buy",item=m.id or m[1],count=n,cost=m.cost or (m.unit or 0)*n,owner=m.owner}
    end
    for _,f in ipairs(result.formulas or {}) do
        local r=f.recipes and f.recipes[1]
        out[#out+1]={type="formula",cost=f.cost or 0,owner=f.recipeKey or r and (r.key or (tostring(r.profession)..":"..tostring(r.spell)))}
    end
    if recorded then
        for _,a in ipairs(result.actions) do out[#out+1]=a end
        return out
    end
    local rows=result.executionSteps and #result.executionSteps>0 and result.executionSteps or result.steps or {}
    for i,step in ipairs(rows) do
        local r=recipeFor(step,snapshot)
        if step.kind=="essence_conversion" or step.kind=="conversion" then
            local c=step.conversion or {};local n=step.expectedCrafts or step[4] or 0
            local source=c.inputItemID or step.sourceItem;local input=c.inputCount or step.sourcePerConversion
            local target=c.outputItemID or step.targetItem or step.item;local output=c.outputCount or step.targetPerConversion or step.outputMin
            if source and target and input and output then
                out[#out+1]={id="derived:"..i,type="convert",count=n,owner=step.owner,
                    inputs={{source,input*n}},outputs={{target,output*n}}}
            end
        elseif r and not step.checkpoint then
            local n=step[4] or step.count or 0;local inputs={}
            for _,m in ipairs(r.mats or {}) do inputs[#inputs+1]={m[1],m[2]*n} end
            -- Fish are gathered at zero purchase cost, never credited as sales.
            local id=r.item;local qty=(r.count or 1)*n
            out[#out+1]={id="derived:"..i,type="craft",profession=r.profession,spell=r.spell,count=n,
                inputs=inputs,outputs=id and {{id,qty}} or {},item=id,outputCount=qty,derivedStep=step,derivedIndex=i,derivedLength=#rows}
        end
    end
    return out
end
local sumFields={"productionCost","attributedCost","transferredCost","recoveryTotal","saleCount","producedCount","consumedCount","naturalRemainder","levelingRemainder","demandCount","demandCost"}
local function newAccounting()
    local a={recoveryOutputs={}};for _,key in ipairs(sumFields) do a[key]=0 end;return a
end
local function addAccounting(target,a,tick)
    for _,key in ipairs(sumFields) do target[key]=(target[key] or 0)+(a[key] or 0) end
    for _,output in ipairs(a.recoveryOutputs or {}) do target.recoveryOutputs[#target.recoveryOutputs+1]=copy(output,tick) end
end
-- Lots retain their original craft/cost ownership during replay. A displayed
-- step can combine many such crafts; summarize only equivalent frozen quotes.
-- This also accepts old saved steps without rewriting their accounting data.
function R.GroupOutputs(outputs,tick)
    local grouped,index={},{}
    for _,output in ipairs(outputs or {}) do
        local key=table.concat({tostring(output.id),tostring(output.source or ""),
            tostring(output.unit or 0),output.missing and "1" or "0"},"\031")
        local entry=index[key]
        if not entry then
            entry=copy(output);entry.count=0;entry.cost=0;entry.revenue=0
            index[key]=entry;grouped[#grouped+1]=entry
        end
        entry.count=entry.count+(output.count or 0)
        entry.cost=entry.cost+(output.cost or 0)
        entry.revenue=entry.revenue+(output.revenue or 0)
        if tick then tick() end
    end
    return grouped
end
function R.Apply(result,snapshot,tick)
    if not result then return end
    snapshot=snapshot or {};local frozen=R.Capture(snapshot,{recoveryEnabled=result.recoveryEnabled},tick)
    result.recoveryRevision=R.REVISION;result.recoveryEnabled=frozen.enabled
    result.recoveryOptimized=frozen.enabled and result.scheme=="cheapest" and not result.procurement or false
    result.recoverySnapshot=copy(frozen,tick)
    result.recoveryQuoteMissing=0
    for _,q in pairs(frozen.quotes or {}) do
        if q.missing then result.recoveryQuoteMissing=result.recoveryQuoteMissing+1 end
        if tick then tick() end
    end
    result.recoveryFeeMissing=frozen.feePercent==nil or nil
    if result.recoveryOptimized and (result.recoveryQuoteMissing>0 or result.recoveryFeeMissing) then result.optimal=false end
    result.purchaseTotal=result.total or 0;result.recoveryTotal=0;result.saleOutputs={}
    result.recoveryMissing=0;result.recoveryMissingItems={};result.purchaseRemainders={}
    result.demandAttribution={};result.demandCost=0;result.demandNonCraftCost=0
    result.recoveryAssumesAllSold=false
    local actions=trace(result,snapshot)
    local pools,poolHeads,accounts,byID,byStep,byRecipe,formulaCosts,recipeCounts={},{},{},{},{},{},{},{}
    local function key(a) return tostring(a.profession or "")..":"..tostring(a.spell or 0) end
    for i,a in ipairs(actions) do
        if a.type=="craft" or a.type=="specialization_quest" then
            local k=a.type=="specialization_quest" and ("quest:"..tostring(a.quest and a.quest.id or a.goalID)) or key(a)
            local ac=newAccounting();ac.key=k;ac.actionID=a.id;ac.item=a.item;ac.count=a.count or 0
            accounts[i]=ac;if a.id then byID[a.id]=ac end
            if a.derivedStep then
                byStep[a.derivedStep]=ac
                local equivalent=result.steps and result.steps[a.derivedIndex]
                if equivalent and #result.steps==a.derivedLength and equivalent[3]==a.spell and equivalent[4]==a.count then byStep[equivalent]=ac end
            end
            byRecipe[k]=byRecipe[k] or {};byRecipe[k][#byRecipe[k]+1]=ac
            recipeCounts[k]=(recipeCounts[k] or 0)+max(1,a.count or 0)
        elseif a.type=="formula" and a.owner then formulaCosts[a.owner]=(formulaCosts[a.owner] or 0)+(a.cost or 0) end
        if tick then tick() end
    end
    local function put(id,n,cost,origin,owner,usable)
        if not id or not n or n<=0 then return end
        local p=pools[id] or {};pools[id]=p;p[#p+1]={count=n,cost=cost,origin=origin,owner=owner,usable=usable~=false}
    end
    local function take(id,n,consumer,terminalDemand)
        local cost,remaining=0,n
        local pool=pools[id] or {}
        local heads=poolHeads[id] or {1,1};poolHeads[id]=heads
        -- Identical to the solver's state.produced rule: purchased stock first,
        -- then route-made stock. Purchased pack leftovers cannot become revenue.
        -- Exhausted lots never refill. Each provenance class advances its own
        -- cursor, including across later puts, instead of rescanning old lots.
        for pass=1,2 do
            local index=heads[pass]
            while n>0 and index<=#pool do
                local lot=pool[index]
                if tick then tick() end
                if lot.usable and (lot.origin==nil)==(pass==1) and n>0 and lot.count>0 then
                    if not lot.origin and not lot.owner and consumer then lot.owner=consumer.key;lot.ownerAccount=consumer end
                    local used=min(n,lot.count);local part=lot.cost*used/lot.count
                    lot.count=lot.count-used;lot.cost=lot.cost-part;n=n-used;cost=cost+part
                    if lot.origin then
                        if terminalDemand then
                            -- Top-up demands are retained final products. They
                            -- are neither sold nor an invisible downstream craft.
                            lot.origin.attributedCost=lot.origin.attributedCost+part
                            lot.origin.demandCost=lot.origin.demandCost+part
                            lot.origin.demandCount=lot.origin.demandCount+used
                        else
                            lot.origin.transferredCost=lot.origin.transferredCost+part
                            lot.origin.consumedCount=lot.origin.consumedCount+used
                        end
                    elseif terminalDemand then result.demandNonCraftCost=result.demandNonCraftCost+part end
                end
                if not lot.usable or (lot.origin==nil)~=(pass==1) or lot.count<=0 then index=index+1 else break end
            end
            heads[pass]=index
        end
        return cost,remaining-n
    end
    for i,a in ipairs(actions) do
        if a.type=="buy" then put(a.item,a.count,a.cost or 0,nil,a.owner)
        elseif a.type=="seed" then put(a.item,a.count,0,nil,nil,a.usableOutput)
        elseif a.type=="convert" then
            local cost=0;for _,input in ipairs(a.inputs or {}) do cost=cost+take(input[1],input[2]) end
            local outputN=0;for _,output in ipairs(a.outputs or {}) do outputN=outputN+(output[2] or 0) end
            -- A conversion transfers the paid cost into another denomination.
            -- Its remainder is still purchased material, never a fresh sale
            -- output (including when a crafted input was consumed here).
            if outputN>0 then for _,output in ipairs(a.outputs) do
                put(output[1],output[2],cost*output[2]/outputN,nil,a.owner,a.usableOutput)
            end end
        elseif accounts[i] then
            local ac=accounts[i];local cost=0
            for _,input in ipairs(a.inputs or {}) do cost=cost+take(input[1],input[2],ac) end
            cost=cost+(formulaCosts[ac.key] or 0)*max(1,a.count or 0)/max(1,recipeCounts[ac.key] or 1)
            ac.productionCost=cost
            local outputN=0;for _,o in ipairs(a.outputs or {}) do outputN=outputN+(o[2] or 0) end
            ac.producedCount=outputN
            if outputN>0 and a.type=="craft" then
                for _,o in ipairs(a.outputs) do put(o[1],o[2],cost*o[2]/outputN,ac,nil,a.usableOutput) end
            else ac.attributedCost=cost end
        end
        if tick then tick() end
    end
    -- ProcureMany removes its synthetic demand craft from player actions. Replay
    -- those already-satisfied obligations once so only natural surplus is sold.
    for id,n in pairs(result.consumedDemands or {}) do
        local cost,consumed=take(id,n,nil,true)
        result.demandAttribution[#result.demandAttribution+1]={id=id,count=consumed,cost=cost}
        result.demandCost=result.demandCost+cost
        if tick then tick() end
    end
    table.sort(result.demandAttribution,function(a,b)return a.id<b.id end)
    -- Permanent tools remain with the player. A lower tool used as a reagent
    -- has already left these pools and cannot be retained or sold twice.
    result.retainedTools={}
    local demandNonCraftCost=result.demandNonCraftCost
    for id,n in pairs(snapshot.retainedToolItems or result.retainedToolItems or {}) do
        local cost,retained=take(id,n,nil,true)
        if retained>0 then result.retainedTools[#result.retainedTools+1]={id=id,count=retained,cost=cost} end
        if tick then tick() end
    end
    result.demandNonCraftCost=demandNonCraftCost
    local sold,missing={},{ }
    for id,pool in pairs(pools) do for _,lot in ipairs(pool) do
    if tick then tick() end
    if lot.count>0 then
        if lot.origin then
            local ac=lot.origin;ac.attributedCost=ac.attributedCost+lot.cost;ac.saleCount=ac.saleCount+lot.count
            local q=frozen.quotes[id] or {unit=0,source="unknown",missing=true}
            local entry=sold[id]
            if not entry then entry=copy(q);entry.id=id;entry.count=0;entry.cost=0;entry.revenue=0;sold[id]=entry end
            local revenue=lot.count*(q.unit or 0)
            entry.count=entry.count+lot.count;entry.cost=entry.cost+lot.cost;entry.revenue=entry.revenue+revenue
            ac.recoveryTotal=ac.recoveryTotal+revenue
            ac.recoveryOutputs[#ac.recoveryOutputs+1]={id=id,count=lot.count,cost=lot.cost,unit=q.unit or 0,source=q.source,revenue=revenue,missing=q.missing}
            if q.missing then missing[id]=true end
        else
            result.purchaseRemainders[#result.purchaseRemainders+1]={id=id,count=lot.count,cost=lot.cost,owner=lot.owner}
            -- A pack remainder is still part of spending and belongs to its
            -- consumer's line, but is never a crafted sale output.
            local owner=lot.ownerAccount or lot.owner and byRecipe[lot.owner] and byRecipe[lot.owner][1]
            if owner then owner.attributedCost=owner.attributedCost+lot.cost end
        end
    end end end
    for _,ac in pairs(accounts) do
        local per=ac.count>0 and ac.producedCount/ac.count or 0
        local required=ac.consumedCount+ac.demandCount
        local material=per>0 and ceil(required/per) or 0
        ac.naturalRemainder=min(ac.saleCount,max(0,material*per-required))
        ac.levelingRemainder=ac.saleCount-ac.naturalRemainder
        if tick then tick() end
    end
    for id,entry in pairs(sold) do
        result.saleOutputs[#result.saleOutputs+1]=entry;result.recoveryTotal=result.recoveryTotal+entry.revenue
        if entry.source=="ah" then result.recoveryAssumesAllSold=true end
        if missing[id] then result.recoveryMissing=result.recoveryMissing+1;result.recoveryMissingItems[#result.recoveryMissingItems+1]=id end
        if tick then tick() end
    end
    table.sort(result.saleOutputs,function(a,b)return a.id<b.id end);table.sort(result.recoveryMissingItems)
    table.sort(result.purchaseRemainders,function(a,b)return a.id<b.id end)
    local function fill(step)
        local total=newAccounting();local found=false
        if byStep[step] then addAccounting(total,byStep[step],tick);found=true end
        if not found then for _,id in ipairs(step.actionIDs or {}) do if byID[id] then addAccounting(total,byID[id],tick);found=true end end end
        if not found and step.actionID and byID[step.actionID] then addAccounting(total,byID[step.actionID],tick);found=true end
        if not found then
            local r=recipeFor(step,snapshot)
            local k=step.kind=="specialization_quest" and ("quest:"..tostring(step.goalID)) or (r and (r.key or (tostring(r.profession)..":"..tostring(r.spell))) or key({profession=step.profession,spell=step[3]}))
            for _,a in ipairs(byRecipe[k] or {}) do addAccounting(total,a,tick) end
            -- Unsegmented legacy lists can repeat the same recipe. Their row
            -- count apportions its total without assigning the whole batch twice.
            local all=recipeCounts[k] or 0
            local count=step[4] or 0
            if all>0 and count>0 and count<all then
                local ratio=count/all
                for _,field in ipairs(sumFields) do total[field]=total[field]*ratio end
                for _,o in ipairs(total.recoveryOutputs) do
                    o.count=o.count*ratio;o.cost=o.cost*ratio;o.revenue=o.revenue*ratio
                end
            end
        end
        for _,field in ipairs(sumFields) do step[field]=total[field] end
        step.attributedCostExact=nil
        step.recoveryOutputs=R.GroupOutputs(total.recoveryOutputs,tick);step.netTotal=step.attributedCost-step.recoveryTotal
        step.costTransferred=step.saleCount==0 and step.transferredCost>0 or nil
        return step.attributedCost
    end
    local allocated=0
    for _,step in ipairs(result.steps or {}) do allocated=allocated+fill(step);if tick then tick() end end
    local executionAllocated=0
    for _,step in ipairs(result.executionSteps or {}) do executionAllocated=executionAllocated+fill(step);if tick then tick() end end
    -- Decimal splits are retained until the route boundary. Attribute the last
    -- copper residual (including legacy cost-only lines) once, never per edge.
    local delta=result.purchaseTotal-result.demandNonCraftCost-allocated
    result.recoveryUnallocatedCost=delta
    local last=result.steps and result.steps[#result.steps]
    if last and math.abs(delta)>1e-8 then last.attributedCost=last.attributedCost+delta;last.netTotal=last.attributedCost-last.recoveryTotal;result.recoveryUnallocatedCost=0 end
    local executionLast=result.executionSteps and result.executionSteps[#result.executionSteps]
    local executionDelta=result.purchaseTotal-result.demandNonCraftCost-executionAllocated
    if executionLast and executionLast~=last and math.abs(executionDelta)>1e-8 then
        executionLast.attributedCost=executionLast.attributedCost+executionDelta
        executionLast.netTotal=executionLast.attributedCost-executionLast.recoveryTotal
    end
    local function roundAttribution(list)
        local exact,rounded=0,0
        for _,step in ipairs(list or {}) do
            step.attributedCostExact=step.attributedCost
            exact=exact+step.attributedCostExact
            local nextRounded=floor(exact+.5+1e-8)
            step.attributedCost=nextRounded-rounded;rounded=nextRounded
            step.netTotal=step.attributedCost-(step.recoveryTotal or 0)
            if tick then tick() end
        end
    end
    roundAttribution(result.steps)
    -- Some old adapters share rows between the lists. Preserve exact values
    -- across the second independent rounding pass as well.
    for _,step in ipairs(result.executionSteps or {}) do
        if step.attributedCostExact~=nil then step.attributedCost=step.attributedCostExact end
    end
    roundAttribution(result.executionSteps)
    result.attributedTotal=result.purchaseTotal
    result.netTotal=result.purchaseTotal-result.recoveryTotal
    result.productPartial=result.recoveryMissing>0
    return result
end
