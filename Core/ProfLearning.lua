-- Native recipe views consume immutable supplemental learning facts. Original
-- Data tuples remain owned by their existing loaders and are never rewritten.
local _, ns = ...
if not ns.LoadForeverPages or not ns.ProfEconomy then return end
local E = ns.ProfEconomy
local eligibility, sourceOf = E.LearningEligibility, E.LearningSource
local capture, findRecipe, formulaFor = E.Capture, E.FindRecipe, E.FormulaFor
local floor = math.floor
local firstAidTrainerDefault
-- Additive evidence for the shipped build, checked against the exact item
-- tooltip (not comments). See formula-policy-fixes-2026-10-30.json for hashes.
-- Future generated providers retain bindingType/bindingSource themselves.
local bindingSupplement={ [234271]=1,[234272]=1,[238782]=1,[238783]=1,[238784]=1,
    [238785]=1,[238786]=1,[238787]=1,[238788]=1,[274049]=1 }
local bindingViews=setmetatable({}, {__mode="kv"})
local specializationCache=setmetatable({}, {__mode="k"})
-- The four supplemental-only gates in the exact shipped provider. New
-- providers expose their compact index directly, avoiding history expansion
-- for already learned recipes. 13240 is supplemental-only, outside native rows.
local shippedFingerprint="c0b5dba91ed30145734fcce393ceaeb6d8e2966a5856a2a731a8616050f1f3b4"
local shippedSpecializations={engineering={ [12716]={{20222}},[13240]={{20222}},
    [15628]={{20222}},[15633]={{20219}} } }
local function specializationGroups(info)
    if not info then return end
    local cached=specializationCache[info]
    if cached~=nil then return cached or nil end
    local supported={};for _,id in ipairs(ns.ProfGates and ns.ProfGates.SpecAbilities or {})do supported[id]=true end
    local groups={}
    for _,route in ipairs(info.routes or {})do
        local group={}
        for _,condition in ipairs(route.conditions or {})do
            if condition.kind=="ability" and supported[condition.value] then group[#group+1]=condition.value end
        end
        -- Different learning routes are alternatives, not cumulative gates.
        if #group==0 then specializationCache[info]=false;return end
        groups[#groups+1]=group
    end
    specializationCache[info]=#groups>0 and groups or false
    return #groups>0 and groups or nil
end
local function spellOf(recipe) return recipe.spell or recipe.spellID or recipe[1] end
local function provider()
    local data=ns.IsForever and ns.ProfLearningSources
    if type(data)=="table" and type(data.meta)=="table" and data.meta.schema==1
        and data.meta.product=="wowf" and type(data.Get)=="function" then return data end
end
local function strict(recipe,snapshot)
    return recipe and
        (recipe.learningSourcesRequired==true or snapshot and snapshot.learningSourcesRequired==true or ns.IsForever==true)
end
function E.LearningPolicyFingerprint()
    if ns.IsForever then
        local data=provider()
        return "native-learning:17:first-aid-trainer-default:"..tostring(data and data.meta.fingerprint or "missing")
    end
    return "native-learning:8:poisons-class-policy"
end
function E.GetLearningInfo(slug,spell)
    local data=provider()
    if not data or type(spell)~="number" or spell<=0 then return end
    local ok,info=pcall(data.Get,slug,spell)
    if ok and type(info)=="table" and info.spell==spell and info.profession==slug
        and type(info.routes)=="table" then
        if data.meta.build~="1.60.1.70685" then return info end
        if bindingViews[info] then return bindingViews[info] end
        local view
        for i,route in ipairs(info.routes)do
            local binding=bindingSupplement[route.teachingItemID]
            local a=route.acquisition or {}
            if binding and a.nonAuctionable==nil and a.bindingType==nil then
                if not view then
                    view={spell=info.spell,profession=info.profession,coverage=info.coverage,
                        missingReasons=info.missingReasons}
                    view.routes={};for n,r in ipairs(info.routes)do view.routes[n]=r end
                end
                local r=E.Copy(route)
                local acquisition=r.acquisition or {}
                acquisition.bindingType=binding;acquisition.bindOnPickup=true
                acquisition.nonAuctionable=true;acquisition.bindingSource="wowhead:item-tooltip"
                r.acquisition=acquisition;view.routes[i]=r
            end
        end
        if view then bindingViews[info]=view end
        return view or info
    end
end
function E.AttachLearningInfo(recipe,known)
    if not strict(recipe) then return recipe end
    recipe.learningSourcesRequired=true
    recipe.learningDataFingerprint=E.LearningPolicyFingerprint()
    local data=provider()
    local rank=data and data.AutomaticSkillRank and data.AutomaticSkillRank(recipe.profession,spellOf(recipe))
    if type(rank)=="number" and rank>=1 and rank==floor(rank) and type(recipe.learn)=="number"
        and rank~=recipe.learn and recipe.skillSource~="client" then
        -- Verified skill rewards are usable from their grant rank. Keep the
        -- source tuple and yellow/green/grey curve intact; only this view changes.
        recipe.catalogueLearn=recipe.catalogueLearn or recipe.learn
        recipe.learn=rank;recipe.skillSource="automaticSkillGrant"
    end
    local slug,spell=recipe.profession,spellOf(recipe)
    local info,groups
    if known~=true then info=E.GetLearningInfo(slug,spell)
    elseif data and data.SpecializationGroups then groups=data.SpecializationGroups(slug,spell)
    elseif data and data.meta.fingerprint==shippedFingerprint then
        groups=shippedSpecializations[slug] and shippedSpecializations[slug][spell]
    else groups=specializationGroups(E.GetLearningInfo(slug,spell)) end
    recipe.learningSpecializations=groups
    -- Learned views retain only compact specialization alternatives, not the
    -- complete acquisition history. Frozen captures keep these static facts.
    if known~=true then recipe.learningInfo=info end
    return recipe
end
function E.LearningSource(recipe)
    if type(recipe)~="table" then return end
    if recipe.selectedLearningRoute then return recipe.selectedLearningRoute.kind end
    if recipe.learnSource=="trainer" or recipe.trainerObserved then return "trainer" end
    for _,route in ipairs(recipe.learningRoutes or {})do
        if route.kind=="trainer" and (route.trainerObserved or route.trainerTaught)then return "trainer" end
    end
    local source=sourceOf(recipe)
    if source and source~="unknown" then return source end
    if recipe.profession=="first-aid" and firstAidTrainerDefault(recipe,
        recipe.learningInfo or E.GetLearningInfo(recipe.profession,spellOf(recipe))) then return "trainer" end
    return source
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
local function professionClassEligibility(recipe,snapshot)
    -- Ordinary professions never depend on character class. Poisons is a
    -- Rogue skill, checked independently of recipe masks and learning source.
    if recipe.profession~="poisons" then return true end
    local id=identity(snapshot,"classID",UnitClass)
    if type(id)~="number" or id<1 then return false,"clientDataPending",{status="unknown"} end
    if id~=4 then return false,"poisonRogueRequired",{status="blocked"} end
    return true
end
local CLASS_CONDITIONS={classIDs=true,classMask=true,itemClassMask=true,abilityClassMask=true}
local function hasLearningConditions(conditions)
    for _,condition in ipairs(conditions or {})do
        if not CLASS_CONDITIONS[condition.kind] then return true end
    end
    return false
end
local function maskMatches(mask,id)
    if type(mask)~="number" or mask<0 or mask>9007199254740991 or mask~=floor(mask)then return nil end
    if mask==0 then return true end
    if type(id)~="number" or id<1 or id>53 or id~=floor(id)then return nil end
    return floor(mask/2^(id-1))%2==1
end
local function standing(factionID)
    local fn=C_Reputation and C_Reputation.GetFactionDataByID
    if type(fn)=="function" then
        local ok,data=pcall(fn,factionID)
        if ok and type(data)=="table" and type(data.reaction)=="number" then return data.reaction end
    end
    if type(GetFactionInfoByID)=="function" then
        local ok,_,_,rank=pcall(GetFactionInfoByID,factionID)
        if ok and type(rank)=="number" then return rank end
    end
end
local function conditionResult(condition,recipe,snapshot,state)
    local kind,value=condition.kind,condition.value
    -- Retain raw source fields for inspection, but never interpret class masks
    -- as profession admission conditions. Poisons has the explicit guard above.
    if CLASS_CONDITIONS[kind] then return true end
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
        if simulated[id]==true then return true end
        local actual
        if snapshot then actual=snapshot.learningAbilities or {} end
        if actual and actual[id]~=nil then return actual[id],actual[id]==false and id or nil end
        if snapshot then actual=snapshot.specializationAbilities or snapshot.abilities
            or snapshot.specializationContext and snapshot.specializationContext.abilities or {}
        else actual=ns.ProfGates and ns.ProfGates.Abilities() or {} end
        if simulated[id]==true or actual[id]==true then return true end
        -- Missing an explicit required ability is an unmet prerequisite of this
        -- route. A different acquisition route can still satisfy the recipe.
        if strict(recipe,snapshot) and actual[id]==nil and simulated[id]==nil then return nil end
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
    elseif kind=="reputation" then
        local id=tonumber(condition.factionID)
        local required=tonumber(value)
        if not id or id<=0 or not required then return nil end
        local rank
        if snapshot then
            local observed=snapshot.reputations and snapshot.reputations[id]
            rank=type(observed)=="table" and (observed.standingID or observed.rank or observed.reaction) or observed
        else rank=standing(id) end
        if type(rank)~="number" then return nil end
        return rank>=required
    elseif kind=="raceMask" then
        local mask=tonumber(value)
        return maskMatches(mask,identity(snapshot,"raceID",UnitRace))
    elseif kind=="abilityRaceMask0" or kind=="abilityRaceMask1" then
        -- Zero explicitly means no filter. The client acquisition masks are a
        -- separate schema; interpreting their nonzero 64-bit values is pending.
        if tonumber(value)==0 then return true end
        return nil
    end
    -- Account and other unsupported restrictions stay unknown.
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
local function legacyLearningEligibility(recipe,snapshot,state)
    if type(recipe)~="table"then return false,"clientDataPending",{status="unknown"}end
    snapshot=snapshot and (snapshot.snapshot or snapshot)
    local classOK,classReason,classDetail=professionClassEligibility(recipe,snapshot)
    if not classOK then return classOK,classReason,classDetail end
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
E.LearningEligibility=legacyLearningEligibility
E.RecipeSpecializationAllowed=legacyLearningEligibility

-- Unknown learning restrictions may be shown in the recipe catalogue, but
-- cannot become executable leveling or material-making steps.
function E.RouteRecipeEligibility(recipe,snapshot,state)
    local allowed,reason,detail=E.LearningEligibility(recipe,snapshot,state)
    -- Missing audit coverage is distinct from an unknown concrete condition.
    -- Keep the catalogue's audit status and use master's native recipe model.
    local native=recipe and (recipe.dataSource=="catalogue" or recipe.dataSource=="mixed")
    if allowed and native and detail and detail.status=="unknown" and not detail.requiredAbility
        and not recipe.availabilityUnknown and recipe.verified~=false
        and #(recipe.learningRoutes or {})==0 and not hasLearningConditions(recipe.learningConstraints)
        and type(recipe.learn)=="number" and recipe.learn>=1
        and type(recipe.mats)=="table" and not recipe.clientPending then
        return true,nil,{status="catalogue",source="native",hasPending=detail.hasPending}
    end
    if allowed and detail and (detail.status=="unknown" or detail.status=="conflict") then
        return false,"learningRequirementsUnknown",detail
    end
    return allowed,reason,detail
end

local legacyRouteEligibility=E.RouteRecipeEligibility
local function shallow(value)
    local out={};for key,v in pairs(value or {})do out[key]=v end;return out
end
local function known(recipe,snapshot,state)
    local spell,key=spellOf(recipe),recipe.key
    local learned=state and state.learned
    if learned and (learned[key]==true or learned[spell]==true)then return true end
    if snapshot then
        local observed=snapshot.known or {}
        return observed[key]==true or observed[spell]==true
    end
    return E.Known(spell)
end
local CONDITION_REASON={raceIDs="characterRaceRequired",raceMask="characterRaceRequired",
    reputation="reputationRequired",quest="questRequired",faction="learningFactionRequired",
    level="characterLevelRequired",skill="skillRequired",profession="professionMissing",ability="specializationRequired"}
local function sourceConditionUnknown(condition)
    local kind=condition.kind
    if CLASS_CONDITIONS[kind] then return false end
    if kind=="abilityRaceMask0" or kind=="abilityRaceMask1" then
        return tonumber(condition.value)~=0
    end
    if not CONDITION_REASON[kind] then return true end
    if kind=="raceIDs" then
        return type(condition.values)=="table" and #condition.values==0
            or type(condition.values)~="table" and type(condition.text)~="string"
    end
    if kind=="raceMask" then
        local n=tonumber(condition.value)
        return not n or n<0 or n>9007199254740991 or n~=floor(n)
    end
    return condition.value==nil or condition.value==false
end
local function check(conditions,recipe,snapshot,state,projectNative)
    if conditions~=nil and type(conditions)~="table" then return true,true,nil,{},{},true end
    local unresolved,reason,abilities,conflicts,sourceUnknown=false,nil,{},{},false
    for _,condition in ipairs(conditions or {})do
        local accepted,ability
        local p=condition.profession or (condition.professionID and E.ProfessionSlug and E.ProfessionSlug(condition.professionID)) or recipe.profession
        if projectNative and condition.kind=="skill" and p==recipe.profession and type(recipe.learn)=="number" then
            -- The source is retained for audit, but the existing solver owns
            -- this recipe's dev learning threshold and future skill planning.
            accepted=true
            if tonumber(condition.value)~=recipe.learn then
                conflicts[#conflicts+1]={kind="skill",sourceValue=condition.value,retainedValue=recipe.learn}
            end
        else accepted,ability=conditionResult(condition,recipe,snapshot,state) end
        if accepted==false then
            reason=reason or CONDITION_REASON[condition.kind] or "learningConditionFailed"
            if ability then abilities[#abilities+1]=ability end
        elseif accepted==nil then unresolved=true;sourceUnknown=sourceUnknown or sourceConditionUnknown(condition) end
    end
    return reason==nil,unresolved,reason,abilities,conflicts,sourceUnknown
end
local function infoFor(recipe,snapshot)
    if recipe.learningInfo then return recipe.learningInfo end
    -- An immutable capture may only use the facts it actually contains.
    if snapshot then return end
    return E.GetLearningInfo(recipe.profession,spellOf(recipe))
end
firstAidTrainerDefault=function(recipe,info)
    if recipe.profession~="first-aid" or recipe.formula or recipe.formulaID then return false end
    local source=sourceOf(recipe)
    if source and source~="unknown" then return false end
    for _,list in ipairs({recipe.learningRoutes or {},info and info.routes or {}})do
        for _,route in ipairs(list)do
            if route.kind=="trainer" or route.kind=="item" or route.kind=="quest" then return false end
        end
    end
    return true
end
local function routesFor(recipe,info)
    local out,seen={},{}
    for _,list in ipairs({recipe.learningRoutes or {},info and info.routes or {}})do
        for _,route in ipairs(list)do
            if type(route)=="table" and (route.kind=="trainer" or route.kind=="item" or route.kind=="quest") then
                local id=route.id or route.kind..":"..tostring(route.teachingItemID or route.itemID or spellOf(recipe))
                if not seen[id] then out[#out+1]={route=route,supplemental=info and list==info.routes};seen[id]=true end
            end
        end
    end
    local trainer,items=false,{}
    for _,entry in ipairs(out)do
        local r=entry.route
        if r.kind=="trainer" then trainer=true end
        if r.kind=="item" then items[r.teachingItemID or r.itemID]=true end
    end
    local G=ns.ProfGates
    local explicit=recipe.trainerAvailable==true or (recipe.learnSource=="trainer" and not recipe.trainerObserved)
        or G and G.LearningSource(spellOf(recipe))=="trainer"
    if not trainer and explicit then
        out[#out+1]={route={id="native:trainer:"..spellOf(recipe),kind="trainer",status="confirmed",
            conditionsKnown=true,conditions={},trainingCost=recipe.trainingCost}}
    end
    local item=recipe.formula or recipe.formulaID
    if item and not items[item] then
        out[#out+1]={route={id="native:item:"..spellOf(recipe)..":"..item,kind="item",teachingItemID=item,
            status="unknown",conditionsKnown=false,conditions={},acquisition={}}}
    end
    if #out==0 and firstAidTrainerDefault(recipe,info) then
        -- User policy: an unknown First Aid origin defaults to a trainer.
        -- This is not an observed NPC or a zero-price quote; keep source data
        -- intact and still enforce the recipe's known skill/character gates.
        local conditions={}
        if type(recipe.learn)=="number" and recipe.learn>0 then
            conditions[1]={kind="skill",professionID=129,value=recipe.learn}
        end
        out[1]={route={id="default:trainer:"..spellOf(recipe),kind="trainer",status="confirmed",
            conditionsKnown=true,conditions=conditions,defaultTrainer=true}}
    end
    return out
end
local function ownedItem(recipe,snapshot,id)
    if type(id)~="number" or id<=0 then return 0 end
    if snapshot then return (snapshot.ownedTeachingItems or {})[id] or 0 end
    local fn=C_Item and C_Item.GetItemCount or GetItemCount
    if type(fn)=="function" then local ok,n=pcall(fn,id,false,false);if ok and type(n)=="number" then return n end end
    return 0
end
local function routeQuote(recipe,route,snapshot,remaining,purchaseSource,state,pricingContext)
    local key=recipe.key or recipe.profession..":"..tostring(spellOf(recipe))
    local common={spell=spellOf(recipe),profession=recipe.profession,recipeKey=key,known=false,
        learningRouteId=route.id,learningRoute=route,count=1,need=1,
        recipes={{profession=recipe.profession,spell=spellOf(recipe),key=key}},sources={}}
    if route.kind=="trainer" then
        -- Current character observations and the existing dev value retain
        -- precedence over an auxiliary web quote for the selected path.
        local automatic=route.acquisition and route.acquisition.kind=="skillGrant"
        local cost=automatic and 0 or recipe.learningRequirements and tonumber(recipe.learningRequirements.trainingCost)
        if cost==nil then cost=tonumber(recipe.trainingCost) end
        if cost==nil then cost=tonumber(route.trainingCost) end
        common.source="trainer";common.sourceType="trainer";common.recipe=recipe
        common.cost=cost and cost>=0 and cost or nil;common.totalCost=common.cost
        common.usable=true;common.costComplete=common.cost~=nil;common.blocked=false
        common.unpriced=common.cost==nil or nil;common.reason=common.unpriced and "learningPriceUnknown" or nil
        common.trainerIDs=route.trainerIDs
        common.automatic=automatic or nil
        return common
    elseif route.kind~="item" then
        common.source=route.kind;common.usable=false;common.blocked=true;common.costComplete=false
        common.unpriced=true;common.reason="learningDataMissing";common.recipe=recipe
        return common
    end
    local id=tonumber(route.teachingItemID or route.itemID)
    if not id or id<=0 then common.usable=false;common.blocked=true;common.reason="learningDataMissing";return common end
    local prepaid=state and state.formulaPaid and state.formulaPaid[id]
    if prepaid or ownedItem(recipe,snapshot,id)>0 then
        common.id=id;common.source="owned";common.sourceType="owned";common.cost=0;common.totalCost=0
        common.usable=true;common.costComplete=true;common.owned=not prepaid or nil;common.prepaid=prepaid or nil;common.recipe=recipe
        return common
    end
    if type(remaining)=="table" then remaining=remaining[id] end
    if remaining==nil and snapshot and state then
        local supply=snapshot.auctionSupply and snapshot.auctionSupply[id]
        if supply and type(supply.quantity)=="number" then remaining=math.max(0,supply.quantity-((state.ahUsed or {})[id] or 0)) end
    end
    local view=shallow(recipe)
    view.formula,view.formulaID,view.selectedLearningRoute=id,id,route
    view.source=shallow(recipe.source)
    local acquisition=route.acquisition or {}
    local acquisitionOK,acquisitionPending,acquisitionReason,_,_,acquisitionUnknown=
        check(acquisition.conditions,recipe,snapshot,state,true)
    if acquisition.quests then view.source.quests=acquisition.quests end
    if acquisition.drops then view.source.drops=acquisition.drops end
    -- Partial world-source coverage cannot establish quest exclusivity.
    view.source.questOnly=nil
    local context=shallow(snapshot or pricingContext)
    if not snapshot and not context.faction and UnitFactionGroup then context.faction=faction(UnitFactionGroup("player")) end
    if snapshot then
        context.known=context.known or {};context.prices=context.prices or {}
        context.formulaOffers=context.formulaOffers or {};context.offers=context.offers or {}
        context.allowLimitedFormulas=context.allowLimitedFormulas==true
    end
    if acquisition.nonAuctionable==true then
        context.nonAuctionable=shallow(context.nonAuctionable);context.nonAuctionable[id]=true
    end
    local offers=context.formulaOffers and context.formulaOffers[id]
    if not offers and not snapshot and ns.VendorPriceDB and ns.VendorPriceDB.GetFormulaOffers then
        offers=ns.VendorPriceDB.GetFormulaOffers(id,context,view.source)
    end
    local added={}
    local supply=ns.ProfSupply
    local vendorFacts=supply and supply.FormulaFacts and supply.FormulaFacts(id) or {}
    for _,o in ipairs(offers or {})do added[#added+1]=o end
    if acquisitionOK and not acquisitionPending then
        local have={};for _,o in ipairs(added)do
            if o.npcID and o.source~="catalogue" then have[o.npcID]=true end
        end
        -- Static supplier facts supply faction metadata absent from a web
        -- quote. Current/native quotes for the same NPC retain precedence.
        for _,o in ipairs(acquisition.vendors or {})do
            local npc=tonumber(o.id or o.npcID)
            local quantity=tonumber(o.quantity or 1)
            local native=npc and vendorFacts[npc]
            local side=o.faction or native and native.faction
            local allowed,pending=check(o.conditions,recipe,snapshot,state,true)
            if allowed and not pending and o.available~=false and o.purchasable~=false and o.priceUsable~=false
                and (not native or native.available~=false and native.purchasable~=false)
                and npc and npc>0 and quantity and quantity>0 and quantity==floor(quantity)
                and not o.hasExtendedCost and not (o.currencyID and o.currencyID>0)
                and #(o.currencies or {})==0 and #(o.costItems or {})==0
                and not have[npc] and type(o.price)=="number" and o.price>=0 then
                added[#added+1]={npcID=npc,price=o.price,quantity=quantity,
                    stock=type(o.stock)=="number" and o.stock>=0 and o.stock or nil,
                    unlimited=o.stock==-1,stockUnknown=o.stock==nil,reference=true,
                    source="learning-sources",priceSource="learning-sources",available=true,
                    purchasable=true,priceUsable=true,faction=side and faction(side),conditions=o.conditions}
            end
        end
    end
    if #added>0 then
        context.formulaOffers=shallow(context.formulaOffers);context.formulaOffers[id]=added
    end
    local quote=formulaFor(view,context,remaining,purchaseSource)
    if quote then
        quote.learningRouteId,quote.learningRoute=route.id,route
        quote.recipeKey=key
    end
    if quote and quote.usable and (quote.source=="ah" or acquisitionOK and not acquisitionPending) then return quote end
    if not acquisitionOK or acquisitionPending then
        if quote then
            quote.usable=false;quote.blocked=true;quote.cost=nil;quote.totalCost=nil
            quote.costComplete=false;quote.unpriced=true
            quote.reason=acquisitionReason or (acquisitionUnknown and "learningDataMissing" or "clientDataPending")
        end
        return quote
    end
    local bound=acquisition.nonAuctionable==true or context.nonAuctionable and context.nonAuctionable[id]==true
        or recipe.bindOnPickup==true or quote and quote.bindOnPickup==true
    if acquisition.bindOnPickup~=nil then bound=acquisition.bindOnPickup
    elseif acquisition.bindingType~=nil then bound=acquisition.bindingType==1 end
    local canBound=E.AllowBindOnPickupFormulas and E.AllowBindOnPickupFormulas(context,recipe.profession)
    local canCurrency=E.AllowCurrencyFormulas and E.AllowCurrencyFormulas(context,recipe.profession)
    local kind,offer,currencyLimited
    local playerFaction=snapshot and snapshot.faction or not snapshot and UnitFactionGroup and UnitFactionGroup("player")
    local function sourceAllowed(source,native)
        local pass,pending=check(source.conditions,recipe,snapshot,state,true)
        local side=source.faction or native and native.faction
        side=side and faction(side)
        return pass and not pending and source.available~=false and source.purchasable~=false
            and (not native or native.available~=false and native.purchasable~=false)
            and (not side or side=="N" or side==faction(playerFaction))
    end
    if bound and canCurrency then
        for _,o in ipairs(acquisition.vendors or {})do
            local currency=o.hasExtendedCost or (tonumber(o.currencyID) or 0)>0
                or #(o.currencies or {})>0 or #(o.costItems or {})>0
            local npc=tonumber(o.id or o.npcID)
            local native=npc and vendorFacts[npc]
            local unlimited=o.unlimited==true or type(o.stock)=="number" and o.stock<0
            local stockOK=unlimited or E.AllowLimitedFormulas(context)
                and (o.stock==nil or type(o.stock)=="number" and o.stock>=1)
            if currency and npc and npc>0 and sourceAllowed(o,native) and not unlimited
                and not E.AllowLimitedFormulas(context) then currencyLimited=true end
            if currency and npc and npc>0 and sourceAllowed(o,native) and stockOK then
                kind,offer="currency",o
                if not o.faction and native and native.faction then
                    offer=shallow(o);offer.faction=native.faction
                end
                break
            end
        end
    end
    if bound and canBound and not kind then
        for _,q in ipairs(acquisition.quests or {})do
            if sourceAllowed(q) then kind="quest";break end
        end
        if not kind then
            for _,drop in ipairs(acquisition.drops or {})do
                if sourceAllowed(drop) then kind="drop";break end
            end
            if not kind and #(acquisition.drops or {})==0 and (acquisition.dropSourceCount or 0)>0 then kind="drop" end
        end
    end
    if kind then
        common.id=id;common.recipe=recipe;common.source="acquire";common.sourceType="acquire"
        common.usable=true;common.blocked=false;common.costComplete=false;common.unpriced=true
        common.acquisitionPending=true;common.acquisitionKind=kind;common.acquisition=acquisition
        common.acquisitionOffer=offer;common.acquisitionOffers=offer and {offer} or nil;common.sources=view.source
        if offer then
            common.cost=type(offer.price)=="number" and offer.price>=0 and offer.price or nil
            common.totalCost=common.cost;common.knownGoldCost=common.cost
            common.npcID=tonumber(offer.id or offer.npcID);common.stock=offer.stock
            common.unlimited=offer.unlimited==true or type(offer.stock)=="number" and offer.stock<0
            common.limited=not common.unlimited and E.LimitedFormulaOffer(offer) or nil
            common.stockUnknown=not common.unlimited and not common.limited or nil
            common.stockStatus=common.unlimited and "unlimited" or common.limited and "limited" or "unknown"
            common.availabilityUncertain=not common.unlimited or nil
        end
        return common
    end
    if quote and currencyLimited then quote.reason="limitedFormulaDisabled";quote.limitedVendorDisabled=true end
    if quote and bound and not canBound and (#(acquisition.quests or {})>0
        or #(acquisition.drops or {})>0 or (acquisition.dropSourceCount or 0)>0)
        and not quote.limitedVendorDisabled then
        quote.reason="bindOnPickupFormulaDisabled"
    end
    if quote and bound and (#(acquisition.vendors or {})>0) and not canCurrency then
        for _,o in ipairs(acquisition.vendors)do
            if o.hasExtendedCost or (tonumber(o.currencyID) or 0)>0 or #(o.currencies or {})>0 or #(o.costItems or {})>0 then
                quote.reason="currencyFormulaDisabled";break
            end
        end
    end
    return quote
end
local function decision(recipe,info,status,route)
    local detail={status=status,route=route,routeId=route and route.id,coverage=info and info.coverage or "none",
        missingReasons=info and info.missingReasons or {"sourceMissing"},
        learningDataFingerprint=recipe.learningDataFingerprint or E.LearningPolicyFingerprint()}
    local id=route and tonumber(route.teachingItemID or route.itemID)
    if id then detail.teachingItemID=id end
    if status=="unknown" then
        local seen,ids={},{}
        for _,entry in ipairs(info and info.routes or {})do
            local item=tonumber(entry.teachingItemID or entry.itemID)
            if item and item>0 and not seen[item] then seen[item]=true;ids[#ids+1]=item end
        end
        if #ids>0 then table.sort(ids);detail.missingItemIDs=ids;if #ids==1 then detail.teachingItemID=ids[1] end end
    end
    return detail
end

-- Admission follows actual learning/acquisition channels. Missing source audit
-- coverage never cancels a priced, stocked purchase; concrete restrictions do.
function E.SelectLearningRoute(recipe,snapshot,state,remaining,purchaseSource,pricingContext)
    if type(recipe)~="table" then return false,"clientDataPending",{status="unknown"} end
    snapshot=snapshot and (snapshot.snapshot or snapshot)
    if not strict(recipe,snapshot) then
        return legacyLearningEligibility(recipe,snapshot,state)
    end
    local classOK,classReason,classDetail=professionClassEligibility(recipe,snapshot)
    if not classOK then return classOK,classReason,classDetail end
    if recipe.craftingUnavailable or recipe.craftUnavailable or recipe.clientUnavailable then
        return false,"clientUnavailable",{status="blocked"}
    end
    local G=ns.ProfGates
    local function specializationAllowed(ability)
        local choice=snapshot and (snapshot.engineeringSpecialization
            or snapshot.specializationContext and snapshot.specializationContext.choice)
            or not snapshot and G and G.GetPlannedChoice and G.GetPlannedChoice()
        return not (ability==20219 and choice=="goblin" or ability==20222 and choice=="gnomish")
            and conditionResult({kind="ability",value=ability},recipe,snapshot,state)~=false
    end
    local ability=G and G.RequiredAbility(spellOf(recipe)) or 0
    if ability>0 then
        if not specializationAllowed(ability) then
            return false,"specializationRequired",{status="blocked",requiredAbility=ability,requiredAbilities={ability}}
        end
    end
    local isKnown=known(recipe,snapshot,state)
    local groups=isKnown and (recipe.learningSpecializations or specializationGroups(infoFor(recipe,snapshot)))
    if groups then
        local allowed,required=false,{}
        for _,group in ipairs(groups)do
            local pass=true
            for _,id in ipairs(group)do
                if not specializationAllowed(id) then pass=false;required[#required+1]=id end
            end
            if pass then allowed=true;break end
        end
        if not allowed then return false,"specializationRequired",{status="blocked",requiredAbilities=required,
            requiredAbility=#required==1 and required[1] or nil} end
    end
    if isKnown then return true,nil,{status="learned"} end
    local info=infoFor(recipe,snapshot)
    local input=snapshot
    if input and not input.known then input=shallow(input);input.known={} end
    local baseRecipe=recipe
    if recipe.trainerObserved and recipe.learningRequirements then
        baseRecipe=shallow(recipe);baseRecipe.learningRequirements=nil
    end
    local ok,reason,base=eligibility(baseRecipe,input,state)
    if not ok then return ok,reason,base end
    if base and base.requiredAbility then return false,"specializationRequired",base end
    local function requirements(conditions,supplemental)
        local pass,pending,why,abilities,conflicts,sourceUnknown=check(conditions,recipe,input,state,supplemental)
        if not pass then return false,why,abilities,conflicts end
        -- Unknown historical source fields do not invalidate a purchase, but a
        -- concrete specialization prerequisite still needs affirmative evidence.
        for _,condition in ipairs(type(conditions)=="table" and conditions or {})do
            if condition.kind=="ability" and (not specializationAllowed(tonumber(condition.value))
                or conditionResult(condition,recipe,input,state)~=true) then
                return false,"specializationRequired",{tonumber(condition.value)},conflicts
            end
        end
        if pending then return false,sourceUnknown and "learningDataMissing" or "clientDataPending",abilities,conflicts end
        return true,nil,abilities,conflicts
    end
    local pass,why,required=requirements(recipe._conditionsCheck or recipe.learningConstraints)
    if not pass then
        local detail=decision(recipe,info,"blocked");detail.requiredAbilities=required
        return false,why,detail
    end
    local best,bestCost,unpriced,failure,failureReason
    for _,entry in ipairs(routesFor(recipe,info))do
        local route=entry.route
        if route.kind=="item" or route.kind=="trainer" and route.status=="confirmed" and route.conditionsKnown==true then
            local allowed,blocked,abilities,conflicts=requirements(route.conditions,entry.supplemental)
            local detail=decision(recipe,info,allowed and "allowed" or "blocked",route)
            detail.numericConflicts=conflicts and #conflicts>0 and conflicts or nil
            detail.requiredAbilities=abilities
            if allowed then
                local quote=routeQuote(recipe,route,input,remaining,purchaseSource,state,pricingContext)
                detail.quote=quote
                if quote and quote.usable then
                    detail.missingReasons={}
                    if type(quote.cost)=="number" and not quote.acquisitionPending then
                        if not bestCost or quote.cost<bestCost then best,bestCost=detail,quote.cost end
                    elseif not unpriced then unpriced=detail end
                elseif not failure then failure,failureReason=detail,quote and quote.reason or "formulaUnavailable" end
            elseif not failure then failure,failureReason=detail,blocked end
        end
    end
    if best or unpriced then return true,nil,best or unpriced end
    return false,failureReason or "learningDataMissing",failure or decision(recipe,info,"unknown")
end
function E.LearningEligibility(recipe,snapshot,state)
    if strict(recipe,snapshot and (snapshot.snapshot or snapshot)) then return E.SelectLearningRoute(recipe,snapshot,state) end
    return legacyLearningEligibility(recipe,snapshot,state)
end
E.RecipeSpecializationAllowed=E.LearningEligibility
function E.RouteRecipeEligibility(recipe,snapshot,state)
    if strict(recipe,snapshot and (snapshot.snapshot or snapshot)) then return E.SelectLearningRoute(recipe,snapshot,state) end
    return legacyRouteEligibility(recipe,snapshot,state)
end
function E.FormulaFor(recipe,context,remaining,purchaseSource)
    -- Native fast routing passes pricing options, not an immutable capture.
    -- Options keep live character reads while a real snapshot remains isolated.
    local snapshot=context and (context.snapshot or
        (context.known~=nil or context.recipes~=nil or context.byKey~=nil or context.prices~=nil
            or context.learningSourcesRequired~=nil) and context)
    if not strict(recipe,snapshot) then
        local quote=formulaFor(recipe,context,remaining,purchaseSource)
        if type(recipe)=="table" then
            local allowed,reason,detail=professionClassEligibility(recipe,snapshot)
            if not allowed then
                quote=quote or {id=recipe.formula or recipe.formulaID,spell=spellOf(recipe),profession=recipe.profession}
                quote.usable,quote.blocked,quote.known,quote.costComplete=false,true,false,false
                quote.source,quote.sourceType="unknown","unknown"
                quote.vendor=false
                quote.cost,quote.totalCost,quote.offer,quote.npcID=nil,nil,nil,nil
                quote.reason,quote.learningStatus,quote.unpriced=reason,detail.status,true
            end
        end
        return quote
    end
    local ok,reason,detail=E.SelectLearningRoute(recipe,snapshot,nil,remaining,purchaseSource,context)
    if ok and detail.status=="learned" then return end
    if ok then return detail.quote end
    if detail and detail.quote then return detail.quote end
    -- Learning eligibility and purchase evidence are independent. Retain
    -- prices/stock for the reference UI even when learning is blocked, without
    -- selecting or charging for that purchase. Frozen captures stay isolated.
    local quote
    local item=recipe.formula or recipe.formulaID
    for _,entry in ipairs(routesFor(recipe,infoFor(recipe,snapshot))) do
        local route=entry.route
        if route.kind=="item" and (route.teachingItemID or route.itemID)==item then
            quote=routeQuote(recipe,route,snapshot,remaining,purchaseSource,nil,context);break
        end
    end
    quote=quote or formulaFor(recipe,context,remaining,purchaseSource) or {}
    quote.id,quote.spell,quote.profession=item,spellOf(recipe),recipe.profession
    quote.recipeKey,quote.recipe=recipe.key,recipe
    quote.count,quote.need,quote.known=1,1,false
    quote.source,quote.sourceType,quote.vendor="unknown","unknown",false
    quote.cost,quote.totalCost,quote.offer,quote.npcID=nil,nil,nil,nil
    quote.usable,quote.blocked,quote.costComplete,quote.unpriced=false,true,false,true
    quote.reason,quote.learningStatus,quote.missingReasons=reason,detail and detail.status,detail and detail.missingReasons
    quote.recipes={{profession=recipe.profession,spell=spellOf(recipe),key=recipe.key}}
    return quote
end
if findRecipe then
    function E.FindRecipe(slug,spell)
        local recipe=findRecipe(slug,spell)
        if strict(recipe) then E.AttachLearningInfo(recipe,E.Known(spell)) end
        return recipe
    end
end

local trackedQuests,trackedReputations={},{}
local questFacts,reputationFacts={},{}
local observationRevision=0
local pendingObservationEvents={}
local contextState
local function questDone(id)
    local probe=C_QuestLog and C_QuestLog.IsQuestFlaggedCompleted or IsQuestFlaggedCompleted
    if type(probe)=="function" then
        local ok,value=pcall(probe,id)
        if ok and type(value)=="boolean" then return value end
    end
end
local function fact(value)
    if value==nil then return "?" end
    if value==true then return "1" end
    if value==false then return "0" end
    return tostring(value)
end
function E.LearningObservationFingerprint()
    -- Initialize once for callers that validate a recipe before opening a route.
    -- Subsequent reads are revision-only; typed client tasks compare the values.
    if ns.IsForever and not contextState and E.UpdateLearningContext then
        E.UpdateLearningContext(UnitLevel and UnitLevel("player"),E.Professions())
    end
    return "learning-observations:"..tostring(observationRevision)
end
function E.QueueLearningObservationEvent(event)
    if event=="UPDATE_FACTION" or event=="PLAYER_LOGIN" or event=="QUEST_TURNED_IN"
        or event=="QUEST_LOG_UPDATE" or event=="QUEST_ACCEPTED" then pendingObservationEvents[event]=true end
end
local function observationChanged()
    observationRevision=observationRevision+1
    local d=E.ClientStore();d.clientInputRevision=(tonumber(d.clientInputRevision) or 0)+1
end
function E.UpdateLearningContext(level,professions)
    if not ns.IsForever then return false end
    local values={}
    for slug,entry in pairs(professions or {})do
        values[#values+1]=slug..":"..tostring(entry.cur)..":"..tostring(entry.max)
    end
    table.sort(values)
    local signature=tostring(level).."|"..table.concat(values,"|")
    local changed=contextState~=nil and contextState~=signature
    contextState=signature
    if changed then observationChanged() end
    return changed
end
function E.RefreshLearningObservations(event,tick)
    local changed=false
    local events=event and {[event]=true} or pendingObservationEvents
    pendingObservationEvents={}
    if events.UPDATE_FACTION or events.PLAYER_LOGIN then
        for id in pairs(trackedReputations)do
            local value=fact(standing(id))
            if reputationFacts[id] and reputationFacts[id]~=value then changed=true end
            reputationFacts[id]=value
            if tick then tick() end
        end
    end
    if events.QUEST_TURNED_IN or events.QUEST_LOG_UPDATE or events.QUEST_ACCEPTED or events.PLAYER_LOGIN then
        for id in pairs(trackedQuests)do
            local value=fact(questDone(id))
            if questFacts[id] and questFacts[id]~=value then changed=true end
            questFacts[id]=value
            if tick then tick() end
        end
    end
    if changed then
        observationChanged()
    end
    return changed
end

-- The capture caller names the profession and recipes before this hook runs.
-- Collect only referenced character facts and teaching items. Never expand a
-- directory-wide catalogue in response to a character event or recipe query.
function E.CaptureLearningFacts(snapshot,tick)
    local ids,reputations,abilities,items={},{},{},{}
    local changed=false
    local function collect(conditions)
        for _,condition in ipairs(conditions or {})do
            if condition.kind=="quest" and type(condition.value)=="number" and condition.value>0 then ids[condition.value]=true end
            if condition.kind=="reputation" and type(condition.factionID)=="number" and condition.factionID>0 then reputations[condition.factionID]=true end
            if condition.kind=="ability" and type(condition.value)=="number" and condition.value>0 then abilities[condition.value]=true end
        end
    end
    for _,recipe in ipairs(snapshot.recipes or {})do
        if not known(recipe,snapshot) then
            collect(recipe.learningConstraints)
            for _,entry in ipairs(routesFor(recipe,recipe.learningInfo))do
                local route=entry.route
                collect(route.conditions);collect(route.acquisition and route.acquisition.conditions)
                for _,offer in ipairs(route.acquisition and route.acquisition.vendors or {})do collect(offer.conditions) end
                for _,quest in ipairs(route.acquisition and route.acquisition.quests or {})do collect(quest.conditions) end
                if route.kind=="item" then
                    local id=tonumber(route.teachingItemID or route.itemID)
                    if id and id>0 then items[id]=true end
                end
            end
        end
        if tick then tick() end
    end
    snapshot.completedQuests=snapshot.completedQuests or {}
    snapshot.reputations=snapshot.reputations or {}
    snapshot.learningAbilities=snapshot.learningAbilities or {}
    snapshot.ownedTeachingItems=snapshot.ownedTeachingItems or {}
    for id in pairs(ids)do
        local value=questDone(id);snapshot.completedQuests[id]=value
        if questFacts[id] and questFacts[id]~=fact(value) then changed=true end
        trackedQuests[id],questFacts[id]=true,fact(value)
        if tick then tick()end
    end
    for id in pairs(reputations)do
        local value=standing(id);snapshot.reputations[id]=value
        if reputationFacts[id] and reputationFacts[id]~=fact(value) then changed=true end
        trackedReputations[id],reputationFacts[id]=true,fact(value)
        if tick then tick()end
    end
    for id in pairs(abilities)do
        snapshot.learningAbilities[id]=E.SpecializationKnown and E.SpecializationKnown(id)
        if tick then tick()end
    end
    for id in pairs(items)do
        local n=ownedItem(nil,nil,id)
        if n>0 then snapshot.ownedTeachingItems[id]=n end
        if tick then tick()end
    end
    if ns.IsForever then snapshot.learningSourcesRequired=true end
    if changed then observationChanged() end
    snapshot.learningDataFingerprint=E.LearningPolicyFingerprint()
    if ns.IsForever then E.UpdateLearningContext(snapshot.level,E.Professions()) end
    snapshot.learningObservationFingerprint=E.LearningObservationFingerprint()
    return snapshot
end
function E.Capture(slug,opts,tick)
    local snapshot=capture(slug,opts,tick)
    if not snapshot or opts and opts.snapshot then return snapshot end
    if not snapshot.learningDataFingerprint then E.CaptureLearningFacts(snapshot,tick) end
    return snapshot
end

-- Keep caches from an earlier learning algorithm separate. This version does
-- includes the supplemental content hash; volatile acquisition times do not
-- invalidate route caches.
local gates=ns.ProfGates
if gates and gates.SpecFingerprint then
    local fingerprint=gates.SpecFingerprint
    function gates.SpecFingerprint(choice)
        return fingerprint(choice)..":learning:"..E.LearningPolicyFingerprint()
    end
end
