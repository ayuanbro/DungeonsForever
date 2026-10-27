-- Evaluate the native recipe's explicit conditions and observed client facts.
-- Missing source restrictions remain data gaps; no reference table is injected.
local _, ns = ...
if not ns.LoadForeverPages or not ns.ProfEconomy then return end
local E = ns.ProfEconomy
local eligibility, sourceOf = E.LearningEligibility, E.LearningSource
local capture = E.Capture
local floor = math.floor
local function spellOf(recipe) return recipe.spell or recipe.spellID or recipe[1] end
function E.LearningPolicyFingerprint()
    -- An algorithm version invalidates older route caches without implying
    -- that any additional profession facts have been installed.
    return "native-learning:3:dev-data"
end
function E.LearningSource(recipe)
    if type(recipe)~="table" then return end
    if recipe.learnSource=="trainer" or recipe.trainerObserved then return "trainer" end
    for _,route in ipairs(recipe.learningRoutes or {})do
        if route.kind=="trainer" and (route.trainerObserved or route.trainerTaught)then return "trainer" end
    end
    return sourceOf(recipe)
end
local function faction(value)
    if value=="Alliance" or value=="a" then return "A" end
    if value=="Horde" or value=="h" then return "H" end
    if value=="Neutral" or value=="n" or value=="Both" then return "N" end
    return value
end
local function identity(snapshot,key,fn)
    if snapshot then return snapshot[key] end
    if type(fn)=="function" then local ok,_,_,id=pcall(fn,"player");if ok then return id end end
end
local function maskMatches(mask,id)
    if type(mask)~="number" or mask<0 or mask>9007199254740991 or mask~=floor(mask)then return nil end
    if mask==0 then return true end
    if type(id)~="number" or id<1 or id>53 or id~=floor(id)then return nil end
    return floor(mask/2^(id-1))%2==1
end
local function conditionResult(condition,recipe,snapshot,state)
    local kind,value=condition.kind,condition.value
    if kind=="raceIDs" then
        local ids=condition.values
        if not ids and type(condition.text)=="string" and condition.text:match("^%s*%[[%d,%s]*%]%s*$")then
            ids={};for id in condition.text:gmatch("%d+")do ids[#ids+1]=tonumber(id)end
        end
        local id=identity(snapshot,"raceID",UnitRace)
        if type(ids)~="table" or #ids==0 or type(id)~="number"then return nil end
        for _,candidate in ipairs(ids)do if id==candidate then return true end end
        return false
    end
    if value==nil or value==false then return nil end
    if kind=="ability" then
        local id=tonumber(value)
        if not id or id<0 then return nil end
        if id==0 then return true end
        local simulated=state and state.specializationAbilities or {}
        local actual=snapshot and (snapshot.specializationAbilities or snapshot.abilities
            or snapshot.specializationContext and snapshot.specializationContext.abilities)
            or ns.ProfGates and ns.ProfGates.Abilities() or {}
        if simulated[id]==true or actual[id]==true then return true end
        -- Missing an explicit required ability is an unmet prerequisite of this
        -- route. A different acquisition route can still satisfy the recipe.
        return false,id
    elseif kind=="level" then
        local required=tonumber(value)
        local level=snapshot and snapshot.level or (not snapshot and UnitLevel and UnitLevel("player"))
        if required==0 then return true end
        if not required or type(level)~="number"then return nil end
        return level>=required
    elseif kind=="skill" then
        local required=tonumber(value)
        if required==0 then return true end
        local profession=condition.profession or (condition.professionID and E.ProfessionSlug and E.ProfessionSlug(condition.professionID)) or recipe.profession
        if condition.professionID and not (E.ProfessionSlug and E.ProfessionSlug(condition.professionID))then return nil end
        local professions=snapshot and snapshot.professions or E.Professions()
        local current=state and state.skill and state.skill[profession] or professions[profession]and professions[profession].cur
        if not required or type(current)~="number"then return nil end
        return current>=required
    elseif kind=="profession" then
        local id=tonumber(value)
        if id==0 then return true end
        local profession=id and E.ProfessionSlug and E.ProfessionSlug(id)
        if not profession then return nil end
        if state and state.skill and type(state.skill[profession])=="number"then return true end
        local professions=snapshot and snapshot.professions or E.Professions()
        if not professions[profession]then return nil end
        return not professions[profession].unlearned
    elseif kind=="faction" then
        local actual=snapshot and snapshot.faction or (not snapshot and UnitFactionGroup and UnitFactionGroup("player"))
        if not actual then return nil end
        return faction(value)=="N" or faction(actual)==faction(value)
    elseif kind=="quest" then
        local completed=snapshot and snapshot.completedQuests
        local done=completed and completed[value]
        if not snapshot and C_QuestLog and C_QuestLog.IsQuestFlaggedCompleted then
            local ok,result=pcall(C_QuestLog.IsQuestFlaggedCompleted,value);if ok then done=result end
        end
        if type(done)~="boolean"then return nil end
        return done
    elseif kind=="classMask" or kind=="raceMask" or kind=="itemClassMask" then
        local mask=tonumber(value)
        if kind=="itemClassMask" and mask==0 then return nil end
        local class=kind=="classMask" or kind=="itemClassMask"
        local fn
        if class then fn=UnitClass else fn=UnitRace end
        return maskMatches(mask,identity(snapshot,class and "classID" or "raceID",fn))
    elseif kind=="abilityClassMask" or kind=="abilityRaceMask0" or kind=="abilityRaceMask1" then
        -- Zero explicitly means no filter. The client acquisition masks are a
        -- separate schema; interpreting their nonzero 64-bit values is pending.
        if tonumber(value)==0 then return true end
        return nil
    end
    -- Reputation, account and other unsupported restrictions stay unknown.
    return nil
end
local function evaluate(conditions,recipe,snapshot,state)
    local allowed,unknown=true,false
    local abilities={}
    for _,condition in ipairs(conditions or {})do
        local accepted,ability=conditionResult(condition,recipe,snapshot,state)
        if accepted==false then allowed=false;if ability then abilities[ability]=true end
        elseif accepted==nil then unknown=true end
    end
    return allowed,unknown,abilities
end
function E.LearningEligibility(recipe,snapshot,state)
    if type(recipe)~="table"then return false,"clientDataPending",{status="unknown"}end
    snapshot=snapshot and (snapshot.snapshot or snapshot)
    local spell=spellOf(recipe)
    local key=recipe.key or recipe.profession and recipe.profession..":"..tostring(spell)
    local known=state and state.learned or snapshot and snapshot.known
    -- A positively learned recipe is usable even if a stale reference/roster
    -- still carries a restriction. Frozen snapshots never query live spell APIs.
    if known and (known[key]==true or known[spell]==true) or not known and E.Known(spell)then
        return true,nil,{status="learned"}
    end
    if recipe.clientUnavailable then return false,"clientUnavailable",{status="blocked"}end
    if recipe.trainerAvailable==true then return true,nil,{status="observed"}end
    local ok,reason,base=eligibility(recipe,snapshot,state)
    -- An explicitly supplied alternative route must not erase a specialization
    -- prerequisite already present in dev's existing gate data.
    if not ok then return ok,reason,base end
    local constraints=recipe._conditionsCheck or recipe.learningConstraints
    if constraints and #constraints>0 then
        local allowed,unknown,required=evaluate(constraints,recipe,snapshot,state)
        if not allowed then
            local list={};for id in pairs(required)do list[#list+1]=id end;table.sort(list)
            return false,"specializationRequired",{status="blocked",requiredAbilities=list,requiredAbility=#list==1 and list[1]or nil}
        end
        if unknown then return false,"clientDataPending",{status="unknown",hasPending=true}end
        if recipe._conditionsCheck then return true,nil,{status="allowed"}end
    end
    local routes=recipe.learningRoutes or {}
    if #routes==0 then return ok,reason,base end
    local selectedKind=E.LearningSource(recipe)=="trainer" and "trainer" or recipe.learningRoute
        or (recipe.formula or recipe.formulaID)and "item"
    local item=recipe.formula or recipe.formulaID
    local selected,all,pending={},{},{}
    local conflict,hasPending=false,false
    for _,route in ipairs(routes)do
        local match=not selectedKind or route.kind==selectedKind and
            (selectedKind~="item" or not item or (route.teachingItemID or route.itemID)==item)
        if route.status=="confirmed"then all[#all+1]=route;if match then selected[#selected+1]=route end
        elseif route.status=="conflict"then conflict=true
        else hasPending=true;if match then pending[#pending+1]=route end end
    end
    if #selected==0 then selected=all end
    if #selected==0 then selected=pending end
    if #selected==0 then
        if conflict then return false,"specializationEvidenceConflict",{status="conflict"}end
        return true,nil,{status="unknown",hasPending=true}
    end
    local failed,unresolved,reference=false,false,false
    local required={}
    for _,route in ipairs(selected)do
        local allowed,unknown,abilities=evaluate(route.conditions,recipe,snapshot,state)
        for id in pairs(abilities)do required[id]=true end
        if allowed and not unknown then
            if route.conditionsKnown==true and route.status=="confirmed"then
                return true,nil,{status="allowed",route=route,hasPending=hasPending or nil}
            end
            reference=true
        end
        failed=failed or not allowed
        unresolved=unresolved or allowed and unknown
    end
    local list={};for id in pairs(required)do list[#list+1]=id end;table.sort(list)
    if not failed then
        if unresolved then return false,"clientDataPending",{status="unknown",hasPending=true}end
        if reference then return true,nil,{status="unknown",hasPending=true}end
    end
    return false,"specializationRequired",{status="blocked",requiredAbilities=list,
        requiredAbility=#list==1 and list[1]or nil,hasPending=hasPending or nil}
end
E.RecipeSpecializationAllowed=E.LearningEligibility

-- Freeze only quest flags referenced by this input. An injected snapshot must
-- carry its own observations and never acquires today's quest state.
function E.Capture(slug,opts,tick)
    local snapshot=capture(slug,opts,tick)
    if not snapshot or opts and opts.snapshot then return snapshot end
    local ids={}
    local function collect(conditions)
        for _,condition in ipairs(conditions or {})do
            if condition.kind=="quest" and type(condition.value)=="number" and condition.value>0 then ids[condition.value]=true end
        end
    end
    for _,recipe in ipairs(snapshot.recipes or {})do
        collect(recipe.learningConstraints)
        for _,route in ipairs(recipe.learningRoutes or {})do collect(route.conditions)end
    end
    snapshot.completedQuests=snapshot.completedQuests or {}
    local probe=C_QuestLog and C_QuestLog.IsQuestFlaggedCompleted
    if type(probe)=="function" then
        for id in pairs(ids)do
            local ok,done=pcall(probe,id)
            if ok and type(done)=="boolean"then snapshot.completedQuests[id]=done end
            if tick then tick()end
        end
    end
    return snapshot
end

-- Keep caches from an earlier learning algorithm separate. This version does
-- not fingerprint or load any extra source data.
local gates=ns.ProfGates
if gates and gates.SpecFingerprint then
    local fingerprint=gates.SpecFingerprint
    function gates.SpecFingerprint(choice)
        return fingerprint(choice)..":learning:"..E.LearningPolicyFingerprint()
    end
end
