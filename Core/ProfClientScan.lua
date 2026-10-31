-- Client observations enhance the existing dev data; loading remains owned
-- by the main addon TOC. Failed/unopened/foreign book reads never prove absence.
local _, ns = ...
if not ns.LoadForeverPages or not ns.ProfEconomy then return end
local E = ns.ProfEconomy
local activeScans = {}
local floor = math.floor
local function store() return E.ClientStore() end
local skillIDs = {[171]="alchemy",[164]="blacksmithing",[333]="enchanting",[202]="engineering",
    [165]="leatherworking",[197]="tailoring",[186]="mining",[182]="herbalism",[393]="skinning",
    [185]="cooking",[129]="first-aid",[356]="fishing",[40]="poisons"}
E.SkillIDs = skillIDs
function E.ProfessionSlug(id) return skillIDs[id] end
local function call(name, ...)
    local parent, key = name:match("^([^.]+)%.(.+)$")
    local fn = parent and _G[parent] and _G[parent][key] or (not parent and _G[name])
    if type(fn)~="function" then return false end
    return pcall(fn, ...)
end
local function positiveInteger(value) return type(value)=="number" and value>0 and value==floor(value) end
local function validMaterials(mats)
    if type(mats)~="table" then return false end
    for _, m in ipairs(mats) do if type(m)~="table" or not positiveInteger(m[1]) or not positiveInteger(m[2]) then return false end end
    return true
end
local function readOutput(r, lo, hi)
    if not positiveInteger(lo) or hi~=nil and (not positiveInteger(hi) or hi<lo) then return false end
    r.count=lo;r.outputMin=lo;r.outputMax=hi or lo;r.variableOutput=hi and hi>lo or nil
    return true
end
local function runtime()
    local d = store()
    local version, build
    if GetBuildInfo then version, build = GetBuildInfo() end
    local scope = tostring(version or "unknown") .. ":" .. tostring(build or "unknown")
    if d.recipeBuild ~= scope then
        d.recipes={}; d.recipeRosters={}; d.learningRequirements={}; d.recipeBuild=scope
        E.observedRankRequirements=nil
    end
    d.recipes=d.recipes or {}
    ns.ProfRecipeRuntime=d.recipes
    return d.recipes
end
E.EnsureClientRuntime = runtime
-- Only positive IDs from our static tables can participate in a route. This
-- index retains original records, not another copy of the profession catalog.
local recipeIDs = {}
local indexed = {}
local function indexProfession(slug)
    local group = ns.ProfRecipes and ns.ProfRecipes[slug]
    local lv = ns.ProfLeveling and ns.ProfLeveling[slug]
    if indexed[slug] == group and indexed[slug..":leveling"] == lv then return end
    indexed[slug], indexed[slug..":leveling"] = group, lv
    for _, kind in ipairs({"rows", "crafted", "enchants"}) do
        for _, row in ipairs(group and group[kind] or {}) do
            local id = kind=="enchants" and row[14] or row[1]
            if positiveInteger(id) then recipeIDs[id]=slug end
        end
    end
    for id in pairs(lv and lv.rinfo or {}) do if positiveInteger(id) then recipeIDs[id]=slug end end
end
local function hasRecipe(spell)
    if not positiveInteger(spell) then return false end
    if recipeIDs[spell] then return true end
    -- Build lazily for the currently open/learned professions first.
    for slug in pairs(E.Professions()) do indexProfession(slug) end
    local pd = ns.ProfModule
    if pd and pd.cur then indexProfession(pd.cur) end
    if recipeIDs[spell] then return true end
    -- A simulated unlearned target is also valid without opening its book.
    for slug, group in pairs(ns.ProfRecipes or {}) do if type(group)=="table" then indexProfession(slug) end end
    return recipeIDs[spell] ~= nil
end
function E.IndexClientProfession(slug) indexProfession(slug) end

local inputFields={"learned","available","unavailable","validated","trainerObserved","trainerAvailable","learn","item","count",
    "outputMin","outputMax","variableOutput","cooldown","cooldownVerified"}
local notified=setmetatable({}, {__mode="k"})
local function changedInput()
    local d=store();d.clientInputRevision=(tonumber(d.clientInputRevision) or 0)+1
end
local function recipeBefore(r)
    local before={mats=r and r.mats}
    for _,key in ipairs(inputFields) do before[key]=r and r[key] end
    return before
end
local function sameMaterials(a,b)
    if a==b then return true end
    if type(a)~="table" or type(b)~="table" or #a~=#b then return false end
    for i,row in ipairs(a) do
        local other=b[i]
        if type(row)~="table" or type(other)~="table" or row[1]~=other[1] or row[2]~=other[2] then return false end
    end
    return true
end
local function recipeObserved(before,r)
    local equal=sameMaterials(before.mats,r.mats)
    if equal then r.mats=before.mats end
    for _,key in ipairs(inputFields) do if before[key]~=r[key] then equal=false;break end end
    if not equal then changedInput() end
end
local function sameProfessions(a,b)
    if type(a)~="table" then return false end
    for slug,value in pairs(b) do
        local previous=a[slug]
        if not previous or previous.cur~=value.cur or previous.max~=value.max
            or previous.primary~=value.primary or previous.skillLineID~=value.skillLineID then return false end
    end
    for slug in pairs(a) do if not b[slug] then return false end end
    return true
end

function E.ReadRecipe(spell, observedInfo, infoAlreadyRead)
    if not positiveInteger(spell) or not hasRecipe(spell) then return end
    local api=C_TradeSkillUI
    if not api then return end
    local linkedOk,linked=call("C_TradeSkillUI.IsTradeSkillLinked")
    local guildOk,guild=call("C_TradeSkillUI.IsTradeSkillGuild")
    if (linkedOk and linked) or (guildOk and guild) then return end
    local infoOk,info=infoAlreadyRead,observedInfo
    if not infoAlreadyRead then infoOk,info=call("C_TradeSkillUI.GetRecipeInfo",spell) end
    local schematicOk,schematic=call("C_TradeSkillUI.GetRecipeSchematic",spell,false)
    info=infoOk and type(info)=="table" and info or nil
    if info and ((info.recipeID and info.recipeID~=spell) or (info.spellID and info.spellID~=spell)) then return end
    if info and not (type(info.learned)=="boolean" or type(info.recipeID)=="number" or
        type(info.spellID)=="number" or (type(info.name)=="string" and info.name~="")) then info=nil end
    schematic=schematicOk and type(schematic)=="table" and schematic or nil
    if schematic and schematic.recipeID and schematic.recipeID~=spell then return end
    if schematic and not (info or (type(schematic.name)=="string" and schematic.name~="") or
        (type(schematic.outputItemID)=="number" and schematic.outputItemID>0) or
        (type(schematic.quantityMin)=="number" and schematic.quantityMin>0) or
        (type(schematic.reagentSlotSchematics)=="table" and #schematic.reagentSlotSchematics>0)) then schematic=nil end
    -- Some builds expose a schematic for an arbitrary spell but no recipe-info
    -- lookup outside the active book. Read that useful data independently.
    if not info and not schematic and not (api.GetRecipeNumReagents and api.GetRecipeReagentInfo) then return end
    local book=runtime(); local r=book[spell] or {};local before=recipeBefore(r); book[spell]=r
    local positiveEvidence=info or schematic or r.learned==true or r.trainerObserved or r.validated or E.Known(spell)
    if positiveEvidence then r.validated=true end
    if info or schematic then r.available=true; r.validated=true end
    if info then
        if type(info.learned)=="boolean" then r.learned=info.learned end
        if type(info.hasCooldown)=="boolean" then r.cooldown=info.hasCooldown; r.cooldownVerified=true end
        local skill=info.requiredSkillRank or info.skillRequired
        if positiveInteger(skill) then r.learn=skill end
    end
    local outputRead,materialsRead=false,false
    if schematic then
            local lo,hi=schematic.quantityMin,schematic.quantityMax
            outputRead=readOutput(r,lo,hi)
            if type(schematic.outputItemID)=="number" and schematic.outputItemID>0 then r.item=schematic.outputItemID end
            if type(schematic.reagentSlotSchematics)=="table" then
                local mats={}; local complete=#schematic.reagentSlotSchematics>0 or r.learned==true
                local basic=Enum and Enum.CraftingReagentType and Enum.CraftingReagentType.Basic
                for _,slot in ipairs(schematic.reagentSlotSchematics) do
                    local required=not slot.optional and (basic==nil or slot.reagentType==nil or slot.reagentType==basic)
                    if required then
                        local choices=slot.reagents or {}
                        if positiveInteger(slot.quantityRequired) and #choices==1 and positiveInteger(choices[1].itemID) then mats[#mats+1]={choices[1].itemID,slot.quantityRequired}
                        else complete=false end
                    end
                end
                if complete then r.mats=mats; materialsRead=true end
            end
    end
    if not outputRead and api.GetRecipeNumItemsProduced then
        local ok,lo,hi=call("C_TradeSkillUI.GetRecipeNumItemsProduced",spell)
        if ok then readOutput(r,lo,hi) end
    end
    local linkOk,link=call("C_TradeSkillUI.GetRecipeItemLink",spell)
    if linkOk and type(link)=="string" then r.item=tonumber(link:match("item:(%d+)")) or r.item end
    if api.GetRecipeOutputItemData then
        local ok,out=call("C_TradeSkillUI.GetRecipeOutputItemData",spell)
        if ok and type(out)=="table" then
            r.item=out.itemID or (out.hyperlink and tonumber(out.hyperlink:match("item:(%d+)"))) or r.item
        end
    end
    local numOk,num=call("C_TradeSkillUI.GetRecipeNumReagents",spell)
    if not materialsRead and numOk and type(num)=="number" and num>=0 and api.GetRecipeReagentInfo then
        local mats={}; local complete=true
        for i=1,num do
            local ilOk,il=call("C_TradeSkillUI.GetRecipeReagentItemLink",spell,i)
            local id=ilOk and type(il)=="string" and tonumber(il:match("item:(%d+)"))
            local riOk,_,_,qty=call("C_TradeSkillUI.GetRecipeReagentInfo",spell,i)
            if riOk and positiveInteger(id) and positiveInteger(qty) then mats[#mats+1]={id,qty} else complete=false end
        end
        -- Some clients return 0 for an arbitrary inaccessible spell. Accept an
        -- empty input list only after the recipe itself was positively observed.
        if complete and (num>0 or r.learned==true) then r.mats=mats
        elseif num==0 and not positiveEvidence then
            if r.mats and #r.mats==0 then r.mats=nil end
            if r.available==true then r.available=nil end
        end
    end
    local baseFn=(C_Spell and C_Spell.GetSpellBaseCooldown) or GetSpellBaseCooldown
    if baseFn then local ok,ms=pcall(baseFn,spell); if ok and type(ms)=="number" then
        if ms>0 then r.cooldown=true elseif r.cooldown~=true then r.cooldown=false end
    end end
    if api.GetRecipeCooldown then
        local ok,seconds,daily,charges,maxCharges=call("C_TradeSkillUI.GetRecipeCooldown",spell)
        if ok and ((type(seconds)=="number" and seconds>0) or daily==true or (type(maxCharges)=="number" and maxCharges>0)) then r.cooldown=true; r.cooldownVerified=true end
    end
    if validMaterials(r.mats) then r.available=true end
    r.observedAt=(time and time()) or 0; r.source="client"
    recipeObserved(before,r)
    return r
end
function E.ScanCrafts(tick)
    tick=tick or function() end
    if not (GetNumCrafts and GetCraftInfo) then return end
    local book=runtime()
    for i=1,GetNumCrafts() do
        local name,_,kind=GetCraftInfo(i)
        if name and kind~="header" then
            local link=GetCraftRecipeLink and GetCraftRecipeLink(i)
            local spell=link and tonumber(link:match("enchant:(%d+)") or link:match("spell:(%d+)"))
            if not spell and C_Spell and C_Spell.GetSpellInfo then local info=C_Spell.GetSpellInfo(name); spell=info and info.spellID end
            if not spell and GetSpellInfo then spell=select(7,GetSpellInfo(name)) end
            if spell and hasRecipe(spell) then
                local r=book[spell] or {};local before=recipeBefore(r); book[spell]=r; r.learned=true
                local item=GetCraftItemLink and GetCraftItemLink(i); r.item=item and tonumber(item:match("item:(%d+)")) or r.item
                if GetCraftNumMade then local lo,hi=GetCraftNumMade(i); readOutput(r,lo,hi) end
                local mats={}; local complete=true
                if GetCraftNumReagents and GetCraftReagentInfo then
                    for n=1,GetCraftNumReagents(i) do
                        local il=GetCraftReagentItemLink and GetCraftReagentItemLink(i,n)
                        local id=il and tonumber(il:match("item:(%d+)")); local _,_,qty=GetCraftReagentInfo(i,n)
                        if id and qty then mats[#mats+1]={id,qty} else complete=false end
                    end
                    if complete then r.mats=mats end
                end
                if GetCraftCooldown then local seconds=GetCraftCooldown(i); if type(seconds)=="number" and seconds>0 then r.cooldown=true end end
                r.source="client"; r.observedAt=(time and time()) or 0
                recipeObserved(before,r)
            end
        end
        tick()
    end
end
-- Refresh only the currently open profession. Do not mistake another player's linked book for ours.
function E.ScanRecipes(tick)
    tick=tick or function() end
    if C_TradeSkillUI and C_TradeSkillUI.IsTradeSkillLinked and C_TradeSkillUI.IsTradeSkillLinked() then return end
    if C_TradeSkillUI and C_TradeSkillUI.IsTradeSkillGuild and C_TradeSkillUI.IsTradeSkillGuild() then return end
    local book=runtime()
    if C_TradeSkillUI and C_TradeSkillUI.GetAllRecipeIDs and C_TradeSkillUI.GetRecipeInfo then
        local ok,ids=call("C_TradeSkillUI.GetAllRecipeIDs")
        if not ok or type(ids)~="table" then return end
        local baseOk,base=call("C_TradeSkillUI.GetBaseProfessionInfo")
        local slug=baseOk and type(base)=="table" and skillIDs[base.professionID]
        local changingOk,changing=call("C_TradeSkillUI.IsDataSourceChanging")
        local readyOk,ready=call("C_TradeSkillUI.IsTradeSkillReady")
        local complete=slug and E.Professions()[slug] and changingOk and changing==false and (not readyOk or ready==true) and #ids>0
        local set={}; local unlearned=false
        for _,spell in ipairs(ids) do
            if hasRecipe(spell) then
            set[spell]=true
            local infoOk,info=call("C_TradeSkillUI.GetRecipeInfo",spell)
            if not infoOk or type(info)~="table" then complete=false
            elseif info.learned==false then unlearned=true end
            local readOk=pcall(E.ReadRecipe,spell,info,infoOk); if not readOk then complete=false end
            end
            tick()
        end
        local endBaseOk,endBase=call("C_TradeSkillUI.GetBaseProfessionInfo")
        local endChangingOk,endChanging=call("C_TradeSkillUI.IsDataSourceChanging")
        -- Require positive evidence that this is an all-recipes view. Legacy
        -- learned-only lists and a changing/foreign book cannot prove absence.
        if complete and unlearned and endBaseOk and type(endBase)=="table" and skillIDs[endBase.professionID]==slug and endChangingOk and endChanging==false then
            local d=store(); d.recipeRosters=d.recipeRosters or {}
            local previous=d.recipeRosters[slug]
            local same=previous and previous.complete and type(previous.ids)=="table"
            if same then
                for spell in pairs(set) do tick();if not previous.ids[spell] then same=false;break end end
                if same then for spell in pairs(previous.ids) do tick();if not set[spell] then same=false;break end end end
            end
            if same then previous.observedAt=(time and time()) or 0
            else d.recipeRosters[slug]={complete=true,ids=set,observedAt=(time and time()) or 0};changedInput() end
        end
    elseif GetNumTradeSkills and GetTradeSkillInfo then
        for i=1,GetNumTradeSkills() do
            local _,kind=GetTradeSkillInfo(i)
            local link=GetTradeSkillRecipeLink and GetTradeSkillRecipeLink(i)
            local spell=link and tonumber(link:match("enchant:(%d+)") or link:match("spell:(%d+)"))
            if spell and kind~="header" and hasRecipe(spell) then
                local r=book[spell] or {};local before=recipeBefore(r); book[spell]=r; r.learned=true
                if GetTradeSkillNumMade then local lo,hi=GetTradeSkillNumMade(i); readOutput(r,lo,hi) end
                local itemLink=GetTradeSkillItemLink and GetTradeSkillItemLink(i); r.item=itemLink and tonumber(itemLink:match("item:(%d+)")) or r.item
                local mats={}; local complete=true
                if GetTradeSkillNumReagents and GetTradeSkillReagentInfo then
                    for j=1,GetTradeSkillNumReagents(i) do
                        local il=GetTradeSkillReagentItemLink and GetTradeSkillReagentItemLink(i,j)
                        local id=il and tonumber(il:match("item:(%d+)")); local _,_,qty=GetTradeSkillReagentInfo(i,j)
                        if id and qty then mats[#mats+1]={id,qty} else complete=false end
                    end
                    if complete then r.mats=mats end
                end
                if GetTradeSkillCooldown then local seconds=GetTradeSkillCooldown(i); if type(seconds)=="number" and seconds>0 then r.cooldown=true end end
                local baseFn=(C_Spell and C_Spell.GetSpellBaseCooldown) or GetSpellBaseCooldown
                if baseFn then local ok,ms=pcall(baseFn,spell); if ok and type(ms)=="number" and ms>0 then r.cooldown=true end end
                r.observedAt=(time and time()) or 0; r.source="client"
                recipeObserved(before,r)
            end
            tick()
        end
    end
end
-- Capture only transient trainer API fields at the event boundary. Name
-- resolution and catalogue work may then wait safely until the scene allows it.
function E.CaptureTrainer(previous)
    if not GetNumTrainerServices or not GetTrainerServiceInfo then return previous end
    local countOk,count=call("GetNumTrainerServices")
    if not countOk or type(count)~="number" or count<=0 then return previous end
    local snapshot=type(previous)=="table" and previous or {services={}}
    for i=1,count do
        local infoOk,name,subtext,serviceType=call("GetTrainerServiceInfo",i)
        local spellOk,spell=call("C_Trainer.GetServiceSpellID",i)
        if not spellOk or not positiveInteger(spell) then spellOk,spell=call("GetTrainerServiceSpellID",i) end
        if not spellOk or not positiveInteger(spell) then
            local linkOk,link=call("GetTrainerServiceItemLink",i)
            spell=linkOk and type(link)=="string" and tonumber(link:match("enchant:(%d+)") or link:match("spell:(%d+)")) or nil
        end
        if not positiveInteger(spell) then spell=nil end
        local requirement={}
        if serviceType=="available" then requirement.available=true
        elseif serviceType=="unavailable" then requirement.available=false end
        if GetTrainerServiceLevelReq then local ok,level=pcall(GetTrainerServiceLevelReq,i);if ok and type(level)=="number" then requirement.level=level end end
        if GetTrainerServiceSkillReq then local ok,skillName,skill=pcall(GetTrainerServiceSkillReq,i);if ok and type(skill)=="number" then requirement.skill=skill;requirement.skillName=skillName end end
        if type(GetTrainerServiceCost)=="function" then
            local ok,cost,extra=pcall(GetTrainerServiceCost,i)
            if ok and type(cost)=="number" and cost>=0 and (extra==nil or extra==0) then requirement.trainingCost=cost end
        end
        if spell or infoOk and type(name)=="string" then
            local key=spell or tostring(name).."\031"..tostring(subtext or "")
            snapshot.services[key]={spell=spell,name=infoOk and name or nil,subtext=subtext,requirement=requirement}
        end
    end
    return snapshot
end
local trainerNames
function E.ScanTrainer(tick,snapshot)
    tick=tick or function() end
    snapshot=type(snapshot)=="table" and snapshot or E.CaptureTrainer()
    if not snapshot then return end
    runtime()
    local d=store()
    d.learningRequirements=d.learningRequirements or {}
    local spellName=(C_Spell and C_Spell.GetSpellName) or GetSpellInfo
    local subtextFn=C_Spell and C_Spell.GetSpellSubtext
    local function fallback(name,subtext)
        if type(name)~="string" or not spellName then return nil end
        -- Stable names are cached for this catalogue/API. Failed lazy client
        -- reads are retried on the next scan; ambiguity is never guessed away.
        if not trainerNames or trainerNames.spellName~=spellName or trainerNames.subtextFn~=subtextFn
             then
            trainerNames={spellName=spellName,subtextFn=subtextFn,names={},pending={}}
            -- Explicit all-profession iteration is reserved for ambiguous legacy
            -- trainer names; ordinary recipe queries always name a profession.
            for slug in pairs(E.Professions()) do indexProfession(slug) end
            for spell in pairs(recipeIDs) do trainerNames.pending[spell]=true; tick() end
        end
        if not trainerNames.scanned then
            local names=trainerNames.names
            for spell in pairs(trainerNames.pending) do
                local ok,spellText,sub=pcall(spellName,spell)
                local subOk=true
                if subtextFn then subOk,sub=pcall(subtextFn,spell) end
                if ok and type(spellText)=="string" and spellText~="" and subOk then
                    local key=spellText.."\031"..tostring(sub or "")
                    if names[key] and names[key]~=spell then names[key]=false elseif names[key]==nil then names[key]=spell end
                    if names[spellText] and names[spellText]~=spell then names[spellText]=false elseif names[spellText]==nil then names[spellText]=spell end
                    trainerNames.pending[spell]=nil
                end
                tick()
            end
            trainerNames.scanned=true
        end
        local match=trainerNames.names[name.."\031"..tostring(subtext or "")]
        if match==nil then match=trainerNames.names[name] end
        return match or nil
    end
    if trainerNames then trainerNames.scanned=nil end
    for _,service in pairs(snapshot.services) do
        local spell=service.spell or fallback(service.name,service.subtext)
        local requirement=service.requirement
        if spell and hasRecipe(spell) then
            local previous=d.learningRequirements[spell]
            if not previous or previous.level~=requirement.level or previous.skill~=requirement.skill
                or previous.skillName~=requirement.skillName or previous.trainingCost~=requirement.trainingCost then
                d.learningRequirements[spell]=requirement;changedInput()
            end
            local book=runtime();local r=book[spell] or {};local before=recipeBefore(r)
            book[spell]=r;r.available=true;r.trainerObserved=true;r.trainerAvailable=requirement.available
            recipeObserved(before,r)
        end
        tick()
    end
end
-- A details event with explicit recipe IDs can refresh those entries without
-- rereading the roster. Unknown/changing/foreign books retain the full scan.
function E.ScanRecipeDetails(ids,tick)
    tick=tick or function() end
    if type(ids)~="table" or not next(ids) then return false end
    local baseOk,base=call("C_TradeSkillUI.GetBaseProfessionInfo")
    local changingOk,changing=call("C_TradeSkillUI.IsDataSourceChanging")
    local readyOk,ready=call("C_TradeSkillUI.IsTradeSkillReady")
    local linkedOk,linked=call("C_TradeSkillUI.IsTradeSkillLinked")
    local guildOk,guild=call("C_TradeSkillUI.IsTradeSkillGuild")
    local slug=baseOk and type(base)=="table" and skillIDs[base.professionID]
    if not slug or not E.Professions()[slug] or not changingOk or changing~=false
        or not readyOk or ready~=true or (linkedOk and linked) or (guildOk and guild) then return false end
    for spell in pairs(ids) do
        if not positiveInteger(spell) then return false end
        local ok,r=pcall(E.ReadRecipe,spell)
        if not ok or not r then return false end
        tick()
    end
    local endBaseOk,endBase=call("C_TradeSkillUI.GetBaseProfessionInfo")
    local endChangingOk,endChanging=call("C_TradeSkillUI.IsDataSourceChanging")
    return endBaseOk and type(endBase)=="table" and endBase.professionID==base.professionID
        and endChangingOk and endChanging==false
end

function E.RefreshClientData(readRecipes,readTrainer,onComplete,recipeIDs,forceInputs,background)
    if ns.ProfessionTracking and not ns.ProfessionTracking.IsEnabled() then
        if onComplete then onComplete(false,"tracking_disabled") end
        return {done=true,cancelled=true,Cancel=function() end}
    end
    -- Older callers with no scan flags may represent an arbitrary spell/policy
    -- event. They retain conservative invalidation; typed skill events opt out.
    if forceInputs==nil then forceInputs=not readRecipes and not readTrainer and not recipeIDs end
    -- The first no-op refresh must compare with its starting input, rather
    -- than treating the lack of a previous notification as a data change.
    runtime()
    local initial=store()
    local initialLevel
    if UnitLevel then local ok,value=pcall(UnitLevel,"player");if ok then initialLevel=value end end
    local baseline={recipes=initial.recipes,build=initial.recipeBuild,revision=initial.clientInputRevision or 0,
        professions=E.Copy(E.Professions()),level=initialLevel,error=E.lastReadError}
    local deadline,ops=0,0
    local handle={}
    activeScans[handle]=true
    local function now() return debugprofilestop and debugprofilestop() or 0 end
    local function tick()
        ops=ops+1
        if ops>=1000 or (deadline>0 and now()>=deadline) then ops=0; coroutine.yield() end
    end
    local co=coroutine.create(function()
        runtime()
        if E.RefreshLearningObservations then E.RefreshLearningObservations(nil,tick) end
        if readRecipes or (recipeIDs and not E.ScanRecipeDetails(recipeIDs,tick)) then
            E.ScanRecipes(tick); E.ScanCrafts(tick)
        end
        if readTrainer then E.ScanTrainer(tick,type(readTrainer)=="table" and readTrainer or nil) end
    end)
    local function step()
        if handle.cancelled or ns.ProfessionTracking and not ns.ProfessionTracking.IsEnabled() then handle.done=true;activeScans[handle]=nil;return true end
        deadline=now()+(ns.IdleJobs and ns.IdleJobs.SliceCap and ns.IdleJobs.SliceCap(2) or 2)
        local ok,err=coroutine.resume(co)
        if not ok then E.lastReadError=tostring(err) end
        if not ok or coroutine.status(co)=="dead" then
            local d=store();local previous=notified[d] or baseline;local professions=E.Professions()
            local level
            if UnitLevel then local levelOK,value=pcall(UnitLevel,"player");if levelOK then level=value end end
            if E.UpdateLearningContext then E.UpdateLearningContext(level,professions) end
            local changed=forceInputs or not previous or previous.recipes~=d.recipes or previous.build~=d.recipeBuild
                or previous.revision~=(d.clientInputRevision or 0) or previous.level~=level
                or previous.error~=E.lastReadError or not sameProfessions(previous.professions,professions)
            notified[d]={recipes=d.recipes,build=d.recipeBuild,revision=d.clientInputRevision or 0,
                professions=professions,level=level,error=E.lastReadError}
            if changed and ns.ProfRouteAuto and ns.ProfRouteAuto.Invalidate then ns.ProfRouteAuto.Invalidate("client-inputs") end
            handle.done=true;activeScans[handle]=nil
            if onComplete then onComplete(ok, err) end
            return true
        end
        return false
    end
    function handle.Cancel()
        if handle.done then return end
        handle.cancelled=true;handle.done=true;co=nil;activeScans[handle]=nil
        if ns.IdleJobs and ns.IdleJobs.Cancel then ns.IdleJobs.Cancel(handle) end
        if onComplete then onComplete(false,"tracking_disabled") end
    end
    if ns.IdleJobs and ns.IdleJobs.Defer then
        function handle.Promote()
            if not handle.done then ns.IdleJobs.Defer(handle,step,"normal") end
        end
        ns.IdleJobs.Defer(handle,step,background and "background" or "normal")
    elseif background and ns.IdleJobs and ns.IdleJobs.Background then ns.IdleJobs.Background(step)
    elseif ns.IdleJobs and ns.IdleJobs.Add then ns.IdleJobs.Add(step)
    else while not step() do end end
    return handle
end

function E.CancelClientReads()
    local handles={};for handle in pairs(activeScans) do handles[#handles+1]=handle end
    for _,handle in ipairs(handles) do handle.Cancel() end
end

-- The dev addon owns this frame directly, just like ProfTrack and VendorPriceDB.
-- Coalesce event bursts before starting one cooperative client read.
if type(CreateFrame)=="function" then
    local frame = CreateFrame("Frame")
    local pendingRecipes, pendingTrainer, queued, scan, rescan = false, nil, false, nil, false
    local flush
    flush = function()
        queued = false
        if scan and not scan.done then rescan=true;return end
        local recipes, trainer = pendingRecipes, pendingTrainer
        pendingRecipes, pendingTrainer, rescan = false, nil, false
        local function complete()
            scan = nil
            if pendingRecipes or pendingTrainer or rescan then flush() end
        end
        local handle = E.RefreshClientData(recipes, trainer, complete, nil, false)
        if handle and not handle.done then scan=handle end
    end
    if frame and frame.RegisterEvent and frame.SetScript then
        for _, event in ipairs({"TRADE_SKILL_SHOW", "TRADE_SKILL_LIST_UPDATE", "TRADE_SKILL_DATA_SOURCE_CHANGED",
            "TRADE_SKILL_DETAILS_UPDATE", "CRAFT_SHOW", "CRAFT_UPDATE", "TRAINER_SHOW", "TRAINER_UPDATE",
            "SKILL_LINES_CHANGED", "SPELLS_CHANGED", "PLAYER_LEVEL_UP", "PLAYER_LOGIN", "UPDATE_FACTION",
            "QUEST_TURNED_IN", "QUEST_LOG_UPDATE", "QUEST_ACCEPTED"}) do pcall(frame.RegisterEvent, frame, event) end
        frame:SetScript("OnEvent", function(_, event)
            if E.QueueLearningObservationEvent then E.QueueLearningObservationEvent(event) end
            if ns.ProfGates then ns.ProfGates.Invalidate() end
            if event=="TRAINER_SHOW" or event=="TRAINER_UPDATE" then pendingTrainer=E.CaptureTrainer(pendingTrainer)
            elseif event:find("TRADE_SKILL",1,true) or event:find("CRAFT",1,true) then pendingRecipes=true end
            if queued then return end
            queued=true
            if C_Timer and C_Timer.After then C_Timer.After(0, flush) else flush() end
        end)
    end
    E.ClientInputFrame=frame
end
