local ns=_G.DF_NS or {}
if not ns.LoadForeverPages then return end
local E=ns.ProfEconomy
local R={};ns.ProfRisk=R
local floor,min,max=math.floor,math.min,math.max
local contexts=setmetatable({},{__mode="k"})
local nextContext=0
local function copy(source)
    local out={};for k,v in pairs(source or {}) do out[k]=v end;return out
end
local function keys(source)
    local out={};for k in pairs(source or {}) do out[#out+1]=k end
    table.sort(out,function(a,b) if tostring(a)==tostring(b) then return type(a)<type(b) end;return tostring(a)<tostring(b) end);return out
end
local function number(n) return string.format("%.17g",n) end
local function atom(value) local text=tostring(value);return type(value)..":"..#text..":"..text end
local function check(risk) if risk.tick then risk.tick() end end
local function code(skill,cap) return cap*512+skill end
local function decode(value) local cap=floor(value/512);return value-cap*512,cap end
local function mass(dist)
    local value=0;for _,n in pairs(dist or {}) do value=value+n end;return value
end
local function product(risk,except)
    local value=1
    for p,dist in pairs(risk.distributions) do if p~=except then value=value*mass(dist) end end
    return value
end
local function recipeKey(r) return r.key or tostring(r.profession)..":"..tostring(r.spell) end
local function clone(risk)
    return {ctx=risk.ctx,tick=risk.tick,distributions=copy(risk.distributions),prepared=risk.prepared,
        learned=risk.learned,failedProbability=risk.failedProbability,unrepairableProbability=risk.unrepairableProbability,
        expectedExtraCrafts=risk.expectedExtraCrafts,expectedShortfall=risk.expectedShortfall}
end
local function probability(risk,r,skill)
    local cache=risk.ctx.gains[r]
    if not cache then cache={};risk.ctx.gains[r]=cache end
    local p=cache[skill]
    if p==nil then p=max(0,min(1,E.Gain(r,skill)));cache[skill]=p end
    return p
end
local function poolKey(pool)
    local out={};for _,key in ipairs(keys(pool)) do out[#out+1]=atom(key) end;return table.concat(out)
end
local function repair(risk,p,skill,cap,target)
    if skill>=target then return 0 end
    if target>300 then return math.huge end
    local pool=risk.prepared[p] or {}
    local signature=atom(p)..atom(poolKey(pool))..":"..skill..":"..cap..":"..target
    local cached=risk.ctx.repairs[signature]
    if cached~=nil then return cached end
    local expected=0
    for current=skill,target-1 do
        local best=0
        for _,r in pairs(pool) do
            if current>=(r.learn or 1) then best=max(best,probability(risk,r,current)) end
            check(risk)
        end
        if best<=0 then expected=math.huge;break end
        if current>=cap and cap<300 then cap=cap<=75 and 150 or cap<=150 and 225 or 300 end
        if current>=cap then expected=math.huge;break end
        expected=expected+1/best;check(risk)
    end
    if risk.ctx.repairEntries>=8192 then risk.ctx.repairs={};risk.ctx.repairEntries=0 end
    risk.ctx.repairs[signature]=expected;risk.ctx.repairEntries=risk.ctx.repairEntries+1
    return expected
end
local function eligible(risk,r)
    local policy=E.Policy and E.Policy(risk.ctx.exclusions,r)
    return not r.cooldown and not r.cooldownUnknown and r.levelingEligible~=false and not r.levelingDisabled
        and not r.clientUnavailable and not r.craftingUnavailable and not r.craftUnavailable
        and policy~="level" and policy~="ban"
end
local function prepare(risk,r,used)
    local key=recipeKey(r);local p=r.profession
    local repairable=not risk.ctx.completionOnly and used and eligible(risk,r)
    local changed=not risk.learned[key] or repairable and not (risk.prepared[p] and risk.prepared[p][key])
    if not changed then return risk end
    local out=clone(risk);out.learned=copy(risk.learned);out.learned[key]=true
    if repairable then
        out.prepared=copy(risk.prepared);out.prepared[p]=copy(risk.prepared[p]);out.prepared[p][key]=r
    end
    return out
end
local function gate(risk,p,target)
    if not p or type(target)~="number" or target<=0 then return risk end
    target=math.ceil(target)
    local dist=risk.distributions[p]
    if not dist then dist={[code(0,300)]=1} end
    local lost=0
    for index,n in pairs(dist) do local skill=decode(index);if skill<target then lost=lost+n end end
    if lost==0 then return risk end
    local out=clone(risk);local kept={};out.distributions[p]=kept
    local other=not risk.ctx.completionOnly and product(risk,p)
    for index,n in pairs(dist) do
        local skill,cap=decode(index)
        if skill>=target then kept[index]=n
        elseif not risk.ctx.completionOnly then
            local weight=n*other;local extra=repair(risk,p,skill,cap,target)
            out.failedProbability=out.failedProbability+weight
            out.expectedShortfall=out.expectedShortfall+weight*(target-skill)
            if extra==math.huge then out.unrepairableProbability=out.unrepairableProbability+weight
            else out.expectedExtraCrafts=out.expectedExtraCrafts+weight*extra end
        end
        check(risk)
    end
    return out
end
local function known(risk,r)
    return risk.learned[recipeKey(r)] or risk.learned[r.spell]
end
local function profession(condition,r)
    return condition.profession or condition.professionID and E.ProfessionSlug and E.ProfessionSlug(condition.professionID) or r.profession
end
local function conditions(gates,list,r,projectNative)
    for _,condition in ipairs(type(list)=="table" and list or {}) do
        if condition.kind=="skill" then
            local p=profession(condition,r);local value=tonumber(condition.value)
            if projectNative and p==r.profession then value=r.learn end
            if p and value then gates[p]=max(gates[p] or 0,value) end
        end
    end
end
local function applyGates(risk,gates)
    for _,p in ipairs(keys(gates)) do risk=gate(risk,p,gates[p]) end
    return risk
end
local function selectedRoute(risk,r,a)
    local detail=a.learning or a.selectedLearning
    local quote=a.formula or detail and detail.quote
    local route=a.learningRoute or quote and quote.learningRoute or detail and detail.route
    if route then return route,quote end
    if E.SelectLearningRoute then
        local state={skill={},learned=risk.learned,formulaPaid={},specializationAbilities=risk.ctx.snapshot.specializationAbilities or {}}
        for p in pairs(risk.distributions) do state.skill[p]=R.SupportedSkill(risk,p) end
        local ok,_,value=E.SelectLearningRoute(r,risk.ctx.snapshot,state)
        if ok and value then return value.route or value.quote and value.quote.learningRoute,value.quote end
    end
end
local function learningGates(risk,r,a)
    if known(risk,r) then return risk end
    local gates={}
    local requirement=r.learningRequirements
    if requirement and type(requirement.skill)=="number" and not r.trainerObserved then gates[r.profession]=requirement.skill end
    conditions(gates,r._conditionsCheck or r.learningConstraints,r,false)
    local route,quote=selectedRoute(risk,r,a)
    if route then
        local supplemental=false
        for _,entry in ipairs(r.learningInfo and r.learningInfo.routes or {}) do if entry==route or entry.id and entry.id==route.id then supplemental=true;break end end
        conditions(gates,route.conditions,r,supplemental)
        if quote and quote.source~="ah" then
            conditions(gates,route.acquisition and route.acquisition.conditions,r,true)
            conditions(gates,quote.conditions,r,true)
        end
    end
    return applyGates(risk,gates)
end
function R.New(snapshot,slug,opts,tick)
    snapshot=snapshot or {};opts=opts or {}
    local target=min(300,max(1,floor(opts.target or 300)))
    local policy={}
    for _,key in ipairs(keys(opts.exclusions)) do policy[#policy+1]=atom(key)..atom(opts.exclusions[key]) end
    local completionOnly=opts.riskCompletionOnly==true or opts.completionOnly==true
    local contextKey=atom(slug)..":"..target..":"..tostring(completionOnly)..":"..table.concat(policy)
    local byOption=contexts[snapshot]
    if not byOption then byOption=setmetatable({},{__mode="v"});contexts[snapshot]=byOption end
    local ctx=byOption[contextKey]
    if not ctx then
        nextContext=nextContext+1
        ctx={id=nextContext,snapshot=snapshot,slug=slug,target=target,completionOnly=completionOnly,known=copy(snapshot.known),
            exclusions=copy(opts.exclusions),recipes={},goals={},gains=setmetatable({},{__mode="k"}),repairs={},repairEntries=0}
        for key,r in pairs(snapshot.byKey or {}) do ctx.recipes[key]=r;if tick then tick() end end
        for _,r in ipairs(snapshot.recipes or {}) do ctx.recipes[recipeKey(r)]=r;if tick then tick() end end
        for _,list in ipairs({snapshot.toolGoals or {},snapshot.specializationGoals or {}}) do
            for _,goal in ipairs(list) do ctx.goals[goal.id]=goal;if tick then tick() end end
        end
        byOption[contextKey]=ctx
    end
    local out={ctx=ctx,tick=tick,distributions={},prepared={},learned=copy(ctx.known),failedProbability=0,
        unrepairableProbability=0,expectedExtraCrafts=0,expectedShortfall=0}
    for p,v in pairs(snapshot.professions or {}) do
        local skill=min(300,max(0,floor(v.cur or 1)));local cap=min(300,max(1,floor(v.max or 300)))
        out.distributions[p]={[code(skill,cap)]=1};if tick then tick() end
    end
    local initial=snapshot.professions and snapshot.professions[slug] or {}
    out.distributions[slug]={[code(min(300,max(1,floor(opts.start or initial.cur or 1))),min(300,max(1,floor(initial.max or 300))))]=1}
    return out
end
function R.SupportedSkill(risk,p)
    local best=0
    for index,n in pairs(risk and risk.distributions[p] or {}) do if n>0 then local skill=decode(index);best=max(best,skill) end end
    return best
end
R.MaxSkill=R.SupportedSkill
function R.CanGate(risk,p,threshold) return R.SupportedSkill(risk,p)>=(threshold or 0) and R.Upper(risk)>0 end
function R.Upper(risk) return risk and product(risk) or 0 end
function R.Completion(risk)
    if risk._completion~=nil then return risk._completion end
    local ctx=risk.ctx;local other=product(risk,ctx.slug);local value=0
    for index,n in pairs(risk.distributions[ctx.slug] or {}) do
        local skill=decode(index)
        if skill>=ctx.target then value=value+n*other end
        check(risk)
    end
    risk._completion=value;return value
end
function R.Apply(risk,a)
    if not risk or type(a)~="table" then return risk end
    local ctx=risk.ctx;local kind=a.type
    if kind=="craft" then
        local key=a.owner or a.profession and a.spell and (a.profession..":"..a.spell)
        local r=a.recipe or ctx.recipes[key]
        assert(r,"risk recipe missing")
        local count=a.count or 1
        assert(type(count)=="number" and count>=0 and count==floor(count) and count<math.huge,"invalid risk craft count")
        if count==0 then return risk end
        local current=learningGates(risk,r,a);current=gate(current,r.profession,r.learn or 1)
        current=prepare(current,r,true)
        local out=clone(current);local dist=current.distributions[r.profession] or {}
        local leveling=a.reason=="level" or a.reason=="secondary"
        for _=1,count do
            local nextDist={}
            for index,n in pairs(dist) do
                local skill,cap=decode(index);local p=probability(current,r,skill)
                if p>0 and skill>=cap then
                    if leveling then if cap<300 then cap=cap<=75 and 150 or cap<=150 and 225 or 300 end
                    else p=0 end
                end
                if skill>=300 then p=0 end
                local stay=code(skill,cap)
                if p<1 then nextDist[stay]=(nextDist[stay] or 0)+n*(1-p) end
                if p>0 then local up=code(skill+1,cap);nextDist[up]=(nextDist[up] or 0)+n*p end
                check(current)
            end
            dist=nextDist
        end
        out.distributions[r.profession]=dist;return out
    elseif kind=="formula" then
        local f=a.formula or {};local key=a.owner or f.recipeKey
        local r=a.recipe or f.recipe or ctx.recipes[key]
        if not r then return risk end
        local current=learningGates(risk,r,a)
        current=gate(current,r.profession,a.minSkill or f.minSkill)
        return prepare(current,r,false)
    elseif kind=="tool_goal" or kind=="specialization_quest" then
        local goal=a.quest or a.goal or ctx.goals[a.goalID] or a
        local p=a.profession or goal.profession
        return gate(risk,p,a.minSkill or goal.minSkill or goal.skillRequired or goal.requiredSkill)
    elseif kind=="gather" then
        local p=a.profession;local target=tonumber(a.to)
        if not p or not target then return risk end
        target=min(300,max(0,floor(target)))
        local current=gate(risk,p,a.minSkill)
        local out=clone(current);local dist={}
        for index,n in pairs(current.distributions[p] or {}) do
            local skill,cap=decode(index)
            while cap<target and cap<300 do cap=cap<=75 and 150 or cap<=150 and 225 or 300;check(current) end
            local nextIndex=code(max(skill,target),cap);dist[nextIndex]=(dist[nextIndex] or 0)+n;check(current)
        end
        out.distributions[p]=dist;return out
    end
    return risk
end
function R.Score(risk)
    if risk._score then return risk._score end
    local ctx=risk.ctx;local other=product(risk,ctx.slug)
    local out={completionProbability=R.Completion(risk),unlockProbability=product(risk),unrepairableProbability=risk.unrepairableProbability,
        expectedExtraCrafts=risk.expectedExtraCrafts,expectedShortfall=risk.expectedShortfall,
        failedGateProbability=risk.failedProbability,estimated=true,probabilityModel="independent_skill_bernoulli",
        repairModel=ctx.completionOnly and "not_evaluated" or "first_blocking_gate_or_terminal",extraCraftsAssumeMaterials=false,
        completionOnly=ctx.completionOnly or nil}
    if ctx.completionOnly then risk._score=out;return out end
    for index,n in pairs(risk.distributions[ctx.slug] or {}) do
        local skill,cap=decode(index);local weight=n*other
        if skill<ctx.target then
            local extra=repair(risk,ctx.slug,skill,cap,ctx.target)
            out.expectedShortfall=out.expectedShortfall+weight*(ctx.target-skill)
            if extra==math.huge then out.unrepairableProbability=out.unrepairableProbability+weight
            else out.expectedExtraCrafts=out.expectedExtraCrafts+weight*extra end
        end
        check(risk)
    end
    risk._score=out;return out
end
local function compare(a,b,descending)
    if a~=b and (a==math.huge or b==math.huge or math.abs(a-b)>1e-12*max(math.abs(a),math.abs(b))) then
        return (descending and a>b or not descending and a<b) and -1 or 1
    end
    return 0
end
function R.Compare(a,b)
    if a==b then return 0 end
    if not a then return 1 end;if not b then return -1 end
    local order=compare(R.Completion(a),R.Completion(b),true)
    if order~=0 then return order end
    order=compare(R.Upper(a),R.Upper(b),true)
    if order~=0 then return order end
    local x,y=R.Score(a),R.Score(b)
    for _,field in ipairs({"unrepairableProbability","expectedExtraCrafts","expectedShortfall"}) do
        order=compare(x[field],y[field],false);if order~=0 then return order end
    end
    return 0
end
function R.Key(risk)
    if risk._key then return risk._key end
    local out={"risk:"..risk.ctx.id}
    for _,p in ipairs(keys(risk.distributions)) do
        out[#out+1]=atom(p)
        for _,index in ipairs(keys(risk.distributions[p])) do out[#out+1]=index.."="..number(risk.distributions[p][index]);check(risk) end
    end
    if not risk.ctx.completionOnly then
        for _,p in ipairs(keys(risk.prepared)) do out[#out+1]="pool"..atom(p)..atom(poolKey(risk.prepared[p]));check(risk) end
    end
    for _,key in ipairs(keys(risk.learned)) do
        if risk.learned[key]~=risk.ctx.known[key] then out[#out+1]="known"..atom(key)..atom(risk.learned[key]);check(risk) end
    end
    if not risk.ctx.completionOnly then
        for _,field in ipairs({"failedProbability","unrepairableProbability","expectedExtraCrafts","expectedShortfall"}) do out[#out+1]=field.."="..number(risk[field]) end
    end
    risk._key=table.concat(out,";");return risk._key
end
