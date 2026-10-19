-- Shared profession inputs. Prices here are purchase prices, never resale values.
local _, ns = ...
if not ns.LoadForeverPages then return end
local E = {}
ns.ProfEconomy = E
local floor, max, min = math.floor, math.max, math.min
local function copy(t) local o = {}; for k,v in pairs(t or {}) do o[k]=v end; return o end
E.Copy = copy
function E.CharacterKey()
    return ((UnitName and UnitName("player")) or "?") .. "-" .. ((GetRealmName and GetRealmName()) or "?")
end
local function store()
    DungeonsForeverDB = DungeonsForeverDB or {}
    local d = DungeonsForeverDB
    d.prof = d.prof or {}; d.prof.economy = d.prof.economy or {}
    local all = d.prof.economy
    local k = E.CharacterKey(); all[k] = all[k] or { policies={} }
    all[k].policies=all[k].policies or {}
    if all[k].materialModel~=1 then
        all[k].trainerCosts=nil; all[k].rankCosts=nil; all[k].rankRequirements=nil
        for _,r in pairs(all[k].recipes or {}) do
            r.tools=nil; r.toolsKnown=nil; r.requirements=nil; r.stationReady=nil
        end
        d.prof.autoNoFormula=nil; d.prof.shopOnlyMiss=nil
        all[k].materialModel=1
    end
    return all[k]
end
local function runtime()
    local d=store()
    local version,number
    if GetBuildInfo then version,number=GetBuildInfo() end
    local build=tostring(version or "unknown")..":"..tostring(number or "unknown")
    if d.recipeBuild~=build then d.recipes={}; d.recipeRosters={}; d.recipeBuild=build end
    d.recipes=d.recipes or {}
    ns.ProfRecipeRuntime=d.recipes
    return d.recipes
end
local drafts = {}
function E.GetPolicies(slug, draft)
    if draft then
        if not drafts[slug] then drafts[slug] = copy(store().policies[slug]) end
        return drafts[slug]
    end
    return store().policies[slug] or {}
end
E.Policies = E.GetPolicies
function E.SetPolicy(slug, profession, spell, mode, draft)
    if mode ~= "ban" and mode ~= "level" then mode=nil end
    local key = tostring(profession) .. ":" .. tostring(spell)
    if draft ~= false then E.GetPolicies(slug,true)[key]=mode
    else
        local s=store(); s.policies[slug]=s.policies[slug] or {}; s.policies[slug][key]=mode
        drafts[slug]=nil
    end
end
function E.ApplyPolicies(slug)
    if drafts[slug] then store().policies[slug]=copy(drafts[slug]); drafts[slug]=nil end
    if ns.ProfRouteAuto then ns.ProfRouteAuto.Invalidate() end
end
function E.ResetPolicies(slug)
    drafts[slug]={}
end
function E.Policy(policies, r)
    return policies and (policies[r.key] or policies[r.spell])
end
function E.PolicyFingerprint(t)
    local keys={}; for k,v in pairs(t or {}) do keys[#keys+1]=tostring(k).."="..tostring(v) end
    table.sort(keys); return table.concat(keys,";")
end
local skillIDs = { [171]="alchemy",[164]="blacksmithing",[333]="enchanting",[202]="engineering",
    [165]="leatherworking",[197]="tailoring",[186]="mining",[182]="herbalism",[393]="skinning",
    [185]="cooking",[129]="first-aid",[356]="fishing" }
E.SkillIDs=skillIDs
-- Function presence is deliberately separate from successful data reads. Forever
-- backports parts of the modern profession UI, while an unopened/unlearned book
-- can still return nil. Neither case proves that a catalogue spell is absent.
local apiNames={"C_TradeSkillUI.GetRecipeInfo","C_TradeSkillUI.GetAllRecipeIDs","C_TradeSkillUI.GetRecipeSchematic",
    "C_TradeSkillUI.GetBaseProfessionInfo","C_TradeSkillUI.IsDataSourceChanging","C_TradeSkillUI.IsTradeSkillReady",
    "C_TradeSkillUI.GetRecipeOutputItemData","C_TradeSkillUI.GetRecipeNumItemsProduced","C_TradeSkillUI.GetRecipeNumReagents",
    "C_TradeSkillUI.GetRecipeReagentInfo",
    "GetNumTradeSkills","GetTradeSkillInfo","GetNumCrafts","GetCraftInfo","GetNumTrainerServices",
    "GetTrainerServiceInfo","GetTrainerServiceItemLink","GetTrainerServiceSpellID",
    "C_Trainer.GetServiceSpellID","GetProfessionInfo","GetProfessions"}
local reads={}
local function apiFunction(name)
    local parent,key=name:match("^([^.]+)%.(.+)$")
    return parent and _G[parent] and _G[parent][key] or (not parent and _G[name])
end
local function call(name,...)
    local fn=apiFunction(name)
    if type(fn)~="function" then return false end
    local results={pcall(fn,...)}
    local r=reads[name] or {calls=0,successes=0,empty=0,errors=0}; reads[name]=r; r.calls=r.calls+1
    if not results[1] then r.errors=r.errors+1
    elseif results[2]==nil then r.empty=r.empty+1
    else r.successes=r.successes+1 end
    return unpack(results)
end
function E.APICapabilities()
    local report={build=store().recipeBuild,functions={},reads=copy(reads),lastReadError=E.lastReadError}
    for _,name in ipairs(apiNames) do report.functions[name]=type(apiFunction(name))=="function" end
    for name,value in pairs(reads) do report.reads[name]=copy(value) end
    store().apiReport=report
    return report
end
function E.APIReport()
    runtime()
    local report=E.APICapabilities(); local lines={"DungeonsForever profession API: "..tostring(report.build)}
    for _,name in ipairs(apiNames) do
        local r=report.reads[name]; local status=report.functions[name] and "available" or "unavailable"
        if r then status=status.."; data="..r.successes..", empty="..r.empty..", errors="..r.errors end
        lines[#lines+1]=name..": "..status
    end
    if report.lastReadError then lines[#lines+1]="Last error: "..report.lastReadError end
    return table.concat(lines,"\n")
end
function E.Professions()
    local out={}
    if GetProfessions and GetProfessionInfo then
        local ok,a,b,c,d,e,f=call("GetProfessions")
        if not ok then return out end
        local values={a,b,c,d,e,f}
        for slot=1,6 do
            local index=values[slot]
            if index then
                local found,_,_,cur,cap,_,_,sid=call("GetProfessionInfo",index)
                local slug=skillIDs[sid]
                if found and slug then out[slug]={cur=cur or 1,max=cap or 75,primary=slot<=2,skillLineID=sid} end
            end
        end
    end
    return out
end
local primaryOrder={"alchemy","blacksmithing","enchanting","engineering","leatherworking","tailoring","mining","herbalism","skinning"}
function E.PartnerCandidates(slug)
    local out,seen={},{}
    local data=ns.ProfData
    local function add(p)
        if p~=slug and not seen[p] then seen[p]=true; out[#out+1]=p end
    end
    if data and type(data.pro)=="table" then
        for _,p in ipairs(data.order or primaryOrder) do
            if data.pro[p] and data.pro[p].kind=="primary" then add(p) end
        end
        local extra={}
        for p,info in pairs(data.pro) do
            if info.kind=="primary" and not seen[p] and p~=slug then extra[#extra+1]=p end
        end
        table.sort(extra); for _,p in ipairs(extra) do add(p) end
    else
        for _,p in ipairs(primaryOrder) do add(p) end
    end
    return out
end
local function validPartner(slug,partner)
    for _,p in ipairs(E.PartnerCandidates(slug)) do if p==partner then return true end end
    return false
end
function E.GetRoutePartner(slug)
    local saved=store().routePartners
    local partner=saved and saved[slug]
    if validPartner(slug,partner) then return partner end
end
function E.SetRoutePartner(slug,partner)
    if partner~=nil and not validPartner(slug,partner) then return false end
    local saved=store()
    if (saved.routePartners and saved.routePartners[slug])==partner then return true end
    saved.routePartners=saved.routePartners or {}; saved.routePartners[slug]=partner
    if ns.ProfRouteAuto and ns.ProfRouteAuto.Invalidate then ns.ProfRouteAuto.Invalidate() end
    return true
end
function E.RouteContext(slug,opts,professions)
    opts=opts or {}
    professions=professions or (opts.snapshot and (opts.snapshot.professions or {})) or E.Professions()
    local target=professions[slug]
    local unlearned=not target or target.unlearned==true
    local partner=opts.secondaryProfession
    if partner==nil then partner=E.GetRoutePartner(slug) end
    local valid=validPartner(slug,partner)
    return {unlearned=unlearned,requiresPartner=slug~="__purchase" and unlearned and opts.allowSecondaryLeveling==true,
        partner=valid and partner or nil,partnerValid=valid}
end
local function routeProfessions(slug,opts,professions)
    local context=E.RouteContext(slug,opts,professions)
    if slug=="__purchase" then return professions,context end
    local selected={}
    if context.unlearned then
        selected[slug]=copy(professions[slug] or {cur=opts.start or 1,max=75})
        selected[slug].unlearned=true
        if context.requiresPartner and context.partnerValid then
            local partner=professions[context.partner]
            selected[context.partner]=partner and not partner.unlearned and copy(partner) or {cur=1,max=75,primary=true,unlearned=true}
        end
    else
        for p,v in pairs(professions) do selected[p]=copy(v) end
    end
    return selected,context
end
function E.Known(spell)
    local rt=ns.ProfRecipeRuntime and ns.ProfRecipeRuntime[spell]
    if rt and rt.learned==true then return true end
    local fns={C_Spell and C_Spell.IsSpellKnown,IsSpellKnown,IsPlayerSpell}
    for _,fn in pairs(fns) do if type(fn)=="function" then local ok,v=pcall(fn,spell); if ok and v then return true end end end
    return false
end
function E.Gain(r, skill)
    if skill < r.learn or skill >= r.grey then return 0 end
    if skill < r.yellow then return 1 end
    if skill < r.green then
        return 1 - ((skill-r.yellow)/max(1,r.green-r.yellow))*.5
    end
    return max(.05,.5-((skill-r.green)/max(1,r.grey-r.green))*.45)
end
local function validMaterials(mats)
    if type(mats)~="table" then return false end
    for _,m in ipairs(mats) do
        if type(m)~="table" or type(m[1])~="number" or m[1]<=0 or type(m[2])~="number" or m[2]<=0 then return false end
    end
    return true
end
local function positiveInteger(value)
    return type(value)=="number" and value>0 and value==floor(value)
end
-- A genuine random range is usable: reserve only its guaranteed minimum.
-- Incomplete/zero sentinel results are not evidence against catalogue data.
local function readOutput(r,lo,hi)
    if not positiveInteger(lo) or (hi~=nil and (not positiveInteger(hi) or hi<lo)) then return false end
    r.count=lo; r.outputMin=lo; r.outputMax=hi or lo
    r.variableOutput=(hi and hi>lo) or nil
    return true
end
function E.ResolveRecipe(seed,slug)
    if type(seed)~="table" then return end
    local r=copy(seed); r.profession=slug or r.profession
    local meta=ns.ProfRecipeMeta and ns.ProfRecipeMeta[r.spell] or {}
    for k,v in pairs(meta) do r[k]=v end
    local rt=ns.ProfRecipeRuntime and ns.ProfRecipeRuntime[r.spell]
    local client,catalogue=false,false
    -- The existing leveling guide carries explicit skill thresholds, including
    -- starter recipes whose catalogue rows may list a later trainer rank.
    -- Use those reference fields until the client supplies the learning level.
    local leveling=ns.ProfLeveling and ns.ProfLeveling[r.profession]
    local guide=leveling and leveling.rinfo and leveling.rinfo[r.spell]
    if guide then
        for _,key in ipairs({"learn","yellow","green","grey"}) do
            if type(guide[key])=="number" then r[key]=guide[key]; r.skillSource="guide"; catalogue=true end
        end
    end
    local clientMaterials=rt and validMaterials(rt.mats) and
        (#rt.mats>0 or rt.learned==true or rt.trainerObserved or rt.validated)
    if clientMaterials then r.mats=rt.mats; r.materialSource="client"; client=true
    elseif validMaterials(r.mats) then r.materialSource="catalogue"; catalogue=true
    else r.mats=nil; r.materialSource="unknown" end
    if rt and type(rt.item)=="number" and rt.item>0 then r.item=rt.item; client=true end
    if rt and type(rt.count)=="number" and rt.count>0 then
        r.count=rt.count; r.outputConflict=nil; r.outputSource="client"; client=true
        r.outputMin,r.outputMax,r.variableOutput=rt.outputMin,rt.outputMax,rt.variableOutput
    elseif type(r.count)=="number" and (r.count>0 or not r.item) then r.outputSource="catalogue"; catalogue=true
    else r.outputSource="unknown" end
    -- Material-only planning does not collect or price tool prerequisites.
    r.tools=nil; r.toolsUnknown=nil; r.toolSource=nil; r.stationReady=nil
    if rt then
        if rt.cooldown~=nil and (rt.cooldown or r.cooldown~=true or rt.cooldownVerified) then
            r.cooldown=rt.cooldown; r.cooldownUnknown=nil
        end
        if rt.learn then r.learn=rt.learn; r.skillSource="client" end
        -- This flag requires positive client evidence. A nil recipe lookup or
        -- omission from a learned-only list must never hide an unlearned recipe.
        if rt.available==false or rt.unavailable==true then r.clientUnavailable=true; r.verified=false end
        if rt.available==true and not r.clientUnavailable then r.clientAvailable=true end
        if rt.variableOutput then
            r.variableOutput=true
            if positiveInteger(rt.outputMin) and positiveInteger(rt.outputMax) and rt.outputMax>=rt.outputMin then
                r.count=rt.outputMin; r.outputMin=rt.outputMin; r.outputMax=rt.outputMax
                r.outputConflict=nil; r.outputSource="client"; r.outputBasis="minimum"; client=true
            elseif r.outputSource=="catalogue" then
                -- Older captures retained only a boolean and discarded the
                -- range. Use the existing reference yield until re-read.
                r.outputConflict=nil; r.outputBasis="reference"
            else r.outputConflict=true end
        end
        if rt.trainerObserved then
            r.learnSource="trainer"; r.clientAvailable=true; r.clientUnavailable=nil
            r.availabilityUnknown=nil; r.verified=true
        end
    end
    local roster=store().recipeRosters and store().recipeRosters[r.profession]
    if roster and roster.complete and not roster.ids[r.spell] and not (rt and rt.trainerObserved) then
        r.clientUnavailable=true; r.clientAvailable=nil; r.verified=false
    end
    r.clientPending=not r.mats or (r.item and (type(r.count)~="number" or r.count<=0)) or nil
    r.dataSource=client and (catalogue and "mixed" or "client") or "catalogue"
    if r.profession and r.spell then r.key=r.profession..":"..r.spell end
    return r
end
local function normalized(row,slug,kind)
    local r={profession=slug,spell=row[1],item=row[2],count=row[3] or 1}
    if kind=="crafted" then
        r.learn=row[4]; r.yellow=row[5]; r.green=row[6]; r.grey=row[7]; r.mats=row[8]; r.source={}; r.isNew=row[10]
        r.formula=tonumber(row[9])
    elseif kind=="enchants" then
        r.spell=row[14]; r.item=tonumber(row[15]); r.count=r.item and 1 or 0
        r.learn=row[5]; r.yellow=row[6]; r.green=row[7]; r.grey=row[8]; r.mats=row[9]; r.source=row[10] or {}; r.isNew=row[11]
        -- Enchant field 15 is its output/scroll, never the learning formula.
        r.formula=tonumber(r.source.formulaID)
        -- A missing formula item ID is not evidence that a trainer recipe
        -- requires an item. Explicit formula sources are handled below.
        if #(r.source.drops or {})>0 or #(r.source.vendors or {})>0 then r.learnSource="catalogue" end
    else
        r.learn=row[7]; r.yellow=row[8]; r.green=row[9]; r.grey=row[10]; r.mats=row[12]; r.formula=row[13] and row[13][1]; r.source=row[14] or {}; r.isNew=row[11]; r.category=row[4]
    end
    if type(r.spell)~="number" or r.spell<=0 then return end
    r.key=slug..":"..r.spell
    r=E.ResolveRecipe(r,slug)
    if type(r.learn)~="number" or type(r.grey)~="number" or not validMaterials(r.mats) then return end
    r.catalogue=true
    r.yellow=r.yellow or r.learn; r.green=r.green or r.yellow
    local rt=ns.ProfRecipeRuntime and ns.ProfRecipeRuntime[r.spell]
    if r.cooldown==nil then
        -- Transmute classification is a request to verify, not proof of a cooldown.
        local fn=(C_Spell and C_Spell.GetSpellBaseCooldown) or GetSpellBaseCooldown
        local ok,ms=false,nil
        if fn then ok,ms=pcall(fn,r.spell) end
        if ok and type(ms)=="number" then r.cooldown=ms>0
        elseif r.category=="Transmutes" or r.spell==18560 then r.cooldownUnknown=true
        else r.cooldown=false end
    end
    if (r.category=="Transmutes" or r.spell==18560) and not r.cooldown
       and not (rt and rt.cooldownVerified) then r.cooldownUnknown=true end
    return r
end
E.Normalize=normalized
function E.FindRecipe(slug,spell)
    local tables=ns.EnsureProfRecipes and ns.EnsureProfRecipes({slug}) or ns.ProfRecipes or {}
    local data=tables[slug] or {}
    for _,kind in ipairs({"rows","crafted","enchants"}) do
        for _,row in ipairs(data[kind] or {}) do
            if (kind=="enchants" and row[14] or row[1])==spell then return normalized(row,slug,kind) end
        end
    end
    local guide=ns.ProfLeveling and ns.ProfLeveling[slug]
    local ri=guide and guide.rinfo and guide.rinfo[spell]
    if ri then
        local seed=copy(ri); seed.spell=spell; seed.item=seed.item or seed.makes; seed.count=seed.count or 1
        seed.profession=slug; seed.source=seed.source or {}; seed.cooldown=seed.cooldown or false
        return E.ResolveRecipe(seed,slug)
    end
end
local function formulaContext(context)
    context=context or {}
    return context.snapshot or context
end
local function recipeKnown(r,context)
    if context.professions and context.professions[r.profession] and context.professions[r.profession].unlearned then return false end
    if context.known then return context.known[r.key]==true or context.known[r.spell]==true end
    return E.Known(r.spell)
end
local function hasEntries(t) return type(t)=="table" and next(t)~=nil end
local function questSource(source)
    if source.questOnly or source.quest or hasEntries(source.quests) or source.type=="quest" or source.kind=="quest" then return true end
    -- `read=classic/wowhead` is scrape provenance, and numeric skill is the
    -- required profession level. Neither field identifies a quest reward.
    for _,key in ipairs({"skill","notes","description"}) do
        local value=source[key]
        if type(value)=="string" and (value:lower():find("quest",1,true) or value:find("任务",1,true) or value:find("任務",1,true)) then return true end
    end
    return false
end
-- The latest actual observation remains a finite purchase budget after reload.
-- Auctionator's daily maximum is reference-only; absent observations stay unknown.
local function validSupply(entry)
    return type(entry)=="table" and entry.source~="auctionator-daily-maximum"
        and type(entry.quantity)=="number" and entry.quantity>=0
        and entry.quantity<math.huge and entry.quantity==floor(entry.quantity)
end
function E.AuctionSupplyOf(context,id)
    local entry
    if context and context.auctionSupply then entry=context.auctionSupply[id]
    elseif not context or not context.prices then
        local bridge=ns.AuctionBridge
        if bridge and bridge.GetAuctionSupply then entry=bridge.GetAuctionSupply(id,true) end
    end
    if validSupply(entry) then return entry end
end
local function quoteMetadata(context,id,field,method)
    if context and context[field] then return context[field][id] end
    -- A captured input must not acquire new metadata while its search runs.
    if context and context.prices then return end
    local bridge=ns.AuctionBridge
    if bridge and type(bridge[method])=="function" then return bridge[method](id) end
end
local supplyIdentityFields={"quantity","observedAt","source","complete","ownerExcluded","market","batch","schemaVersion"}
local function supplyIdentity(supply)
    if not supply then return false end
    local out={}
    for _,key in ipairs(supplyIdentityFields) do out[key]=supply[key] end
    return out
end
function E.AuctionSupplyChanged(result)
    -- Prices/history have independent freshness. Only quantity evidence belongs
    -- to this comparison, and looking it up never starts a scan or a search.
    for id,previous in pairs(result.auctionSupplyInputs or {}) do
        local current=E.AuctionSupplyOf(nil,id)
        if (previous~=false)~=(current~=nil) then return true end
        if current then
            for _,key in ipairs(supplyIdentityFields) do if previous[key]~=current[key] then return true end end
        end
    end
    return false
end
function E.SummarizeAuctionSupply(result,context)
    local seen,needed={},{}
    result.auctionSupplyUnknown=0;result.auctionSupplyObserved=false;result.supplyComplete=true
    result.auctionSupplyInputs={}
    -- Include unused, priced candidates: a new quantity for a previously scarce
    -- cheaper recipe also changes the inputs to the saved minimum-cost result.
    for id in pairs(context and context.prices or {}) do
        result.auctionSupplyInputs[id]=supplyIdentity(E.AuctionSupplyOf(context,id))
    end
    for id in pairs(context and context.auctionSupply or {}) do
        result.auctionSupplyInputs[id]=supplyIdentity(E.AuctionSupplyOf(context,id))
    end
    for _,list in ipairs({result.mats or {},result.formulas or {}}) do
        for _,entry in ipairs(list) do
            local id=entry.id or entry[1]
            entry.priceObservedAt=quoteMetadata(context,id,"priceObservedAt","GetAuctionPriceObservedAt")
            if (entry.source=="ah" or entry.source=="auction") and not entry.known then
                local supply=E.AuctionSupplyOf(context,id)
                result.auctionSupplyInputs[id]=supplyIdentity(supply)
                entry.supplyObserved=supply~=nil
                entry.supplyLimited=nil;entry.supplyObservedAt=nil;entry.supplySource=nil
                entry.supplyOwnerExcluded=nil;entry.supplyObservedPrice=nil
                entry.supplyMarket=nil;entry.supplyBatch=nil;entry.supplySchemaVersion=nil
                entry.supplyHistoryQuantity=nil;entry.supplyHistoryObservedAt=nil
                local history=quoteMetadata(context,id,"auctionSupplyHistory","GetAuctionSupplyHistory")
                if type(history)=="table" and type(history.quantity)=="number" and history.quantity>=0
                    and history.quantity<math.huge and history.quantity==floor(history.quantity) then
                    entry.supplyHistoryQuantity=history.quantity;entry.supplyHistoryObservedAt=history.observedAt
                end
                if supply then
                    entry.availableCount=supply.quantity;entry.supplyComplete=supply.complete==true
                    entry.supplyObservedAt=supply.observedAt
                    entry.supplySource=supply.source;entry.supplyOwnerExcluded=supply.ownerExcluded
                    entry.supplyObservedPrice=supply.observedPrice;entry.supplyMarket=supply.market
                    entry.supplyBatch=supply.batch;entry.supplySchemaVersion=supply.schemaVersion
                    result.auctionSupplyObserved=true
                    needed[id]=(needed[id] or 0)+(entry.count or entry[2] or 1)
                    entry.supplyLimited=needed[id]>supply.quantity or nil
                    result.supplyComplete=result.supplyComplete and supply.complete==true
                        and supply.ownerExcluded~=false and not entry.supplyLimited
                else
                    entry.availableCount=nil;entry.supplyComplete=false;result.supplyComplete=false
                    if not seen[id] then result.auctionSupplyUnknown=result.auctionSupplyUnknown+1 end
                end
                seen[id]=true
            end
        end
    end
    result.auctionSupplyRevision=2
    return result
end
function E.FormulaFor(r,context,auctionRemaining)
    if type(r)~="table" then return end
    context=formulaContext(context)
    local id=tonumber(r.formula or r.formulaID)
    local known=recipeKnown(r,context)
    local sources=copy(r.source)
    local meta=id and ns.ProfFormulaMeta and ns.ProfFormulaMeta[id]
    if meta then
        for k,v in pairs(meta.source or {}) do sources[k]=v end
        for _,k in ipairs({"questOnly","quests","quest","url"}) do if meta[k]~=nil then sources[k]=meta[k] end end
    end
    local quest=questSource(sources)
    if not id or id<=0 then
        if not quest then return end
        id=nil
    end
    -- Positive trainer observation supersedes an old catalogue formula item.
    if r.learnSource=="trainer" then return end
    local entry={id=id,count=1,need=1,spell=r.spell,profession=r.profession,recipeKey=r.key,
        known=known,sources=sources,recipe=r,recipes={{profession=r.profession,spell=r.spell,key=r.key,source=sources}},
        questOnly=quest and not hasEntries(sources.vendors) and not hasEntries(sources.drops) or false,
        vendorOffers={},source="unknown",usable=true}
    local ah=id and context.prices and context.prices[id]
    if ah==nil and id and not context.prices then
        local ra=ns.ProfRouteAuto; if ra and ra.AHPriceOf then ah=ra.AHPriceOf(id) end
    end
    if type(ah)=="number" and ah>0 and not (context.nonAuctionable and context.nonAuctionable[id]) then entry.ahPrice=ah end
    local offers=id and context.formulaOffers and context.formulaOffers[id]
    if not offers and id and ns.VendorPriceDB and ns.VendorPriceDB.GetFormulaOffers then
        offers=ns.VendorPriceDB.GetFormulaOffers(id,context,sources)
    end
    if not offers and id and context.offers then offers=context.offers[id] end
    entry.vendorOffers=offers or {}
    local vendors,seen={},{}
    for _,v in ipairs(sources.vendors or {}) do vendors[#vendors+1]=v;if v.id then seen[v.id]=true end end
    for _,o in ipairs(entry.vendorOffers) do
        if o.npcID and not seen[o.npcID] then
            vendors[#vendors+1]={id=o.npcID,name=o.npcName or o.name or ("#"..o.npcID),zone=o.zone}
            seen[o.npcID]=true
        end
    end
    sources.vendors=vendors
    entry.questOnly=quest and not hasEntries(vendors) and not hasEntries(sources.drops) or false
    local supply=id and E.AuctionSupplyOf and E.AuctionSupplyOf(context,id)
    local ahAvailable=auctionRemaining or (supply and supply.quantity)
    local ahUsable=entry.ahPrice and (ahAvailable==nil or ahAvailable>=1)
    if supply then entry.availableCount=supply.quantity;entry.supplyObserved=true;entry.supplyComplete=supply.complete==true end
    local best,bestCost
    for _,o in ipairs(entry.vendorOffers) do
        if o.unlimited==true then entry.unlimited=true
        elseif o.unlimited==false or o.limited==true or o.stockStatus=="limited" or (type(o.stock)=="number" and o.stock>=0) then entry.limited=true
        else entry.stockUnknown=true end
        if type(o.price)=="number" and o.price>=0 and not o.hasExtendedCost and (not o.currencyID or o.currencyID==0) then
            local unit=o.price/(o.quantity or o.bundleSize or 1)
            if not entry.vendorPrice or unit<entry.vendorPrice then entry.vendorPrice=unit end
        end
        local factionOK=not o.faction or not context.faction or o.faction==context.faction or o.faction=="N" or o.faction=="Neutral" or o.faction=="AH" or o.faction=="Both"
        if o.available~=false and o.purchasable~=false and o.priceUsable~=false and factionOK
            and not o.hasExtendedCost and (not o.currencyID or o.currencyID==0)
            and type(o.price)=="number" and o.price>=0 and o.stock~=0 then
            local quantity=o.quantity or o.bundleSize or 1
            if not positiveInteger(quantity) then quantity=1 end
            local cost=o.price -- One indivisible purchase supplies the formula.
            if (type(o.stock)~="number" or o.stock<0 or o.stock>=quantity) and (not bestCost or cost<bestCost) then best,bestCost=o,cost end
        end
    end
    if bestCost~=nil and (not ahUsable or bestCost<=entry.ahPrice) then
        entry.source="vendor";entry.cost=bestCost;entry.offer=best;entry.npcID=best.npcID
        local quantity=best.quantity or best.bundleSize or 1
        entry.bundleSize=positiveInteger(quantity) and quantity or 1;entry.count=entry.bundleSize
        entry.availabilityUncertain=best.unlimited~=true and type(best.stock)~="number" or nil
    elseif ahUsable then entry.source="ah";entry.cost=entry.ahPrice
    elseif entry.questOnly then entry.source="quest";entry.usable=known
    end
    if known then entry.cost=0;entry.usable=true end
    if not known and entry.cost==nil then entry.usable=false end
    entry.unpriced=not known and entry.cost==nil or nil
    entry.costComplete=known or (entry.cost~=nil and not entry.availabilityUncertain) or false
    entry.sourceType=entry.source;entry.totalCost=entry.cost;entry.blocked=not entry.usable
    entry.vendor=entry.source=="vendor"
    if entry.blocked then
        entry.reason=entry.ahPrice and ahAvailable~=nil and ahAvailable<1 and "auctionSupplyLimited" or "formulaUnavailable"
    end
    return entry
end
function E.CollectFormulas(steps,slug,context)
    local snap=formulaContext(context);local list,byID={},{};local total,complete=0,true
    for _,step in ipairs(steps or {}) do
        if not step.checkpoint and (step[4] or step.count or 0)>0 then
            local profession=step.profession or slug
            local r=step.recipe or (snap.byKey and snap.byKey[profession..":"..tostring(step[3] or step.spell)]) or E.FindRecipe(profession,step[3] or step.spell)
            local entry=r and E.FormulaFor(r,snap)
            if entry and not entry.known then
                local key=entry.id or entry.recipeKey or profession..":"..tostring(entry.spell)
                local old=byID[key]
                if old then old.recipes[#old.recipes+1]=entry.recipes[1]
                else
                    byID[key]=entry;list[#list+1]=entry
                    total=total+(entry.cost or 0);complete=complete and entry.costComplete and entry.usable
                end
            end
        end
    end
    table.sort(list,function(a,b) return (a.id or 0)<(b.id or 0) end)
    return list,total,complete
end
function E.Index(s)
    s.byItem={}; s.byProfession={}; s.byKey={}; s.recipes=s.recipes or {}
    for _,r in ipairs(s.recipes) do
        r.key=r.key or (r.profession..":"..r.spell)
        r.count=r.count or 1; r.mats=r.mats or {}; r.yellow=r.yellow or r.learn; r.green=r.green or r.yellow
        s.byKey[r.key]=r
        local p=s.byProfession[r.profession] or {}; s.byProfession[r.profession]=p; p[#p+1]=r
        if type(r.item)=="number" and r.item>0 and r.count>0 then local a=s.byItem[r.item] or {}; s.byItem[r.item]=a; a[#a+1]=r end
    end
    -- All plans begin with an empty material ledger. Only materials produced by
    -- this route may be reused; legacy/injected stock and fee inputs are ignored.
    s.inventory={}; s.inventoryUnknown=nil
    s.trainingCosts=nil; s.rankCosts=nil; s.learningRequirements=nil; s.rankRequirements=nil
    s.stations=nil; s.stationRequirements=nil
    s.professions=s.professions or {}; s.known=s.known or {}
    s.prices=s.prices or {}; s.offers=s.offers or {}; s.formulaOffers=s.formulaOffers or {}
    s.auctionSupplyHistory=s.auctionSupplyHistory or {};s.priceObservedAt=s.priceObservedAt or {}
    s.nonAuctionable=s.nonAuctionable or {}
    local supply={}
    for id,entry in pairs(s.auctionSupply or {}) do
        if validSupply(entry) then supply[id]=entry end
    end
    s.auctionSupply=supply
    s.vendorItems=s.vendorItems or {}; s.vendorSuppliers=s.vendorSuppliers or {}
    return s
end
function E.Capture(slug,opts,tick)
    opts=opts or {}; tick=tick or function() end
    if opts.snapshot then
        local s=copy(opts.snapshot)
        s.professions,s.routeContext=routeProfessions(slug,opts,s.professions or {})
        if s.routeContext.unlearned and slug~="__purchase" then
            s.recipes={}
            for _,r in ipairs(opts.snapshot.recipes or {}) do
                if s.professions[r.profession] then s.recipes[#s.recipes+1]=r end
            end
        end
        return E.Index(s)
    end
    runtime()
    local s={recipes={},professions=E.Professions(),known={},prices={},offers={},auctionSupply={},auctionSupplyHistory={},priceObservedAt={},vendorItems={},vendorSuppliers={},diagnostics={},coverageComplete=false,stamp=(time and time()) or 0,character=E.CharacterKey()}
    s.level=UnitLevel and UnitLevel("player") or nil
    s.faction=UnitFactionGroup and UnitFactionGroup("player") or nil
    if s.faction=="Alliance" then s.faction="A" elseif s.faction=="Horde" then s.faction="H" end
    s.professions,s.routeContext=routeProfessions(slug,opts,s.professions)
    local relevant={[slug]=true}
    for p,v in pairs(s.professions) do if v.primary then relevant[p]=true end end
    local keys={}; for p in pairs(relevant) do keys[#keys+1]=p end
    local tables=ns.EnsureProfRecipes and ns.EnsureProfRecipes(keys) or ns.ProfRecipes or {}
    local seen={}
    for p in pairs(relevant) do
        local d=tables[p] or {}
        for _,kind in ipairs({"rows","crafted","enchants"}) do
            for _,row in ipairs(d[kind] or {}) do
                if E.ReadRecipe then pcall(E.ReadRecipe,kind=="enchants" and row[14] or row[1]) end
                local r=normalized(row,p,kind)
                if r and not seen[r.key] then
                    s.recipes[#s.recipes+1]=r; seen[r.key]=true
                    s.known[r.key]=not (s.professions[p] and s.professions[p].unlearned) and E.Known(r.spell) or false
                    local rt=ns.ProfRecipeRuntime and ns.ProfRecipeRuntime[r.spell]
                    local requirement=store().learningRequirements and store().learningRequirements[r.spell]
                    if requirement and type(requirement.skill)=="number" and not (rt and rt.learn) then r.learn=requirement.skill end
                    if s.known[r.key] and rt and rt.learned then r.learn=min(r.learn,(s.professions[p] or {}).cur or r.learn) end
                end
                tick()
            end
        end
        local lv=ns.ProfLeveling and ns.ProfLeveling[p]
        for spell,ri in pairs(lv and lv.rinfo or {}) do
            local key=p..":"..spell
            if not seen[key] and type(ri.learn)=="number" and type(ri.grey)=="number" then
                local row={spell,ri.makes,ri.count or 1,"","","",ri.learn,ri.yellow,ri.green,ri.grey,false,ri.mats or {},nil,{}}
                local r=normalized(row,p,"rows")
                if r then
                    s.recipes[#s.recipes+1]=r; seen[key]=true
                    s.known[key]=not (s.professions[p] and s.professions[p].unlearned) and E.Known(spell) or false
                end
            end
            tick()
        end
    end
    local items={}
    for _,r in ipairs(s.recipes) do
        if r.item then items[r.item]=true end
        if r.formula and not s.known[r.key] and not s.known[r.spell] then items[r.formula]=true end
        for _,m in ipairs(r.mats) do items[m[1]]=true end
    end
    local ra=ns.ProfRouteAuto
    local vendorContext={character=s.character,faction=s.faction,professions=s.professions,level=s.level,
        allowVendorCache=true,requireObservedPrice=false}
    for id in pairs(items) do
        local info=(C_Item and C_Item.GetItemInfo) or GetItemInfo
        if type(info)=="function" then
            local fields={pcall(info,id)}; local binding=fields[15]
            if fields[1] and (binding==1 or binding==4) then s.nonAuctionable=s.nonAuctionable or {}; s.nonAuctionable[id]=true end
        end
        if ra and ra.AHPriceOf then s.prices[id]=ra.AHPriceOf(id) end
        local supply=E.AuctionSupplyOf(nil,id)
        if supply then s.auctionSupply[id]=copy(supply) end
        local history=quoteMetadata(nil,id,"auctionSupplyHistory","GetAuctionSupplyHistory")
        if type(history)=="table" then s.auctionSupplyHistory[id]=copy(history) end
        s.priceObservedAt[id]=quoteMetadata(nil,id,"priceObservedAt","GetAuctionPriceObservedAt")
        local vendor=ns.VendorPriceDB
        if vendor then
            if vendor.GetSuppliers then
                local suppliers=vendor.GetSuppliers(id,vendorContext)
                local verified={}
                for _,supplier in ipairs(type(suppliers)=="table" and suppliers or {}) do
                    if supplier.unlimited==true and supplier.available~=false and supplier.verifiedAt and supplier.source
                        and not supplier.hasExtendedCost and (not supplier.currencyID or supplier.currencyID==0) then
                        verified[#verified+1]=supplier
                    end
                end
                if #verified>0 then s.vendorItems[id]=true; s.vendorSuppliers[id]=verified end
            end
            if vendor.GetOffers then s.offers[id]=vendor.GetOffers(id,vendorContext) end
        end
        tick()
    end
    s.formulaOffers={}
    if ns.VendorPriceDB and ns.VendorPriceDB.GetFormulaOffers then
        for _,r in ipairs(s.recipes) do if r.formula then
            local source=E.FormulaFor(r,s)
            s.formulaOffers[r.formula]=source and source.vendorOffers or {}
            tick()
        end end
    end
    return E.Index(s)
end
function E.ReadRecipe(spell)
    if not positiveInteger(spell) then return end
    local api=C_TradeSkillUI
    if not api then return end
    local linkedOk,linked=call("C_TradeSkillUI.IsTradeSkillLinked")
    local guildOk,guild=call("C_TradeSkillUI.IsTradeSkillGuild")
    if (linkedOk and linked) or (guildOk and guild) then return end
    local infoOk,info=call("C_TradeSkillUI.GetRecipeInfo",spell)
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
    local book=runtime(); local r=book[spell] or {}; book[spell]=r
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
            if spell then
                local r=book[spell] or {}; book[spell]=r; r.learned=true
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
            end
        end
        tick()
    end
end
-- Refresh only the currently open profession. Do not mistake another player's linked book for ours.
function E.ScanRecipes(tick)
    tick=tick or function() end
    if C_TradeSkillUI and C_TradeSkillUI.IsTradeSkillLinked and C_TradeSkillUI.IsTradeSkillLinked() then return end
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
            set[spell]=true
            local infoOk,info=call("C_TradeSkillUI.GetRecipeInfo",spell)
            if not infoOk or type(info)~="table" then complete=false
            elseif info.learned==false then unlearned=true end
            local readOk=pcall(E.ReadRecipe,spell); if not readOk then complete=false end
            tick()
        end
        local endBaseOk,endBase=call("C_TradeSkillUI.GetBaseProfessionInfo")
        local endChangingOk,endChanging=call("C_TradeSkillUI.IsDataSourceChanging")
        -- Require positive evidence that this is an all-recipes view. Legacy
        -- learned-only lists and a changing/foreign book cannot prove absence.
        if complete and unlearned and endBaseOk and type(endBase)=="table" and skillIDs[endBase.professionID]==slug and endChangingOk and endChanging==false then
            local d=store(); d.recipeRosters=d.recipeRosters or {}
            d.recipeRosters[slug]={complete=true,ids=set,observedAt=(time and time()) or 0}
        end
    elseif GetNumTradeSkills and GetTradeSkillInfo then
        for i=1,GetNumTradeSkills() do
            local _,kind=GetTradeSkillInfo(i)
            local link=GetTradeSkillRecipeLink and GetTradeSkillRecipeLink(i)
            local spell=link and tonumber(link:match("enchant:(%d+)") or link:match("spell:(%d+)"))
            if spell and kind~="header" then
                local r=book[spell] or {}; book[spell]=r; r.learned=true
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
            end
            tick()
        end
    end
end
function E.ScanTrainer(tick)
    tick=tick or function() end
    if not GetNumTrainerServices or not GetTrainerServiceInfo then return end
    local d=store(); local names={}
    d.learningRequirements=d.learningRequirements or {}
    local ranks={ [2259]={"alchemy",75},[3101]={"alchemy",150},[3464]={"alchemy",225},[11611]={"alchemy",300},
        [2018]={"blacksmithing",75},[3100]={"blacksmithing",150},[3538]={"blacksmithing",225},[9785]={"blacksmithing",300},
        [7411]={"enchanting",75},[7412]={"enchanting",150},[7413]={"enchanting",225},[13920]={"enchanting",300},
        [4036]={"engineering",75},[4037]={"engineering",150},[4038]={"engineering",225},[12656]={"engineering",300},
        [2108]={"leatherworking",75},[3104]={"leatherworking",150},[3811]={"leatherworking",225},[10662]={"leatherworking",300},
        [3908]={"tailoring",75},[3909]={"tailoring",150},[3910]={"tailoring",225},[12180]={"tailoring",300},
        [2575]={"mining",75},[2576]={"mining",150},[3564]={"mining",225},[10248]={"mining",300},
        [2550]={"cooking",75},[3102]={"cooking",150},[3413]={"cooking",225},[18260]={"cooking",300},
        [3273]={"first-aid",75},[3274]={"first-aid",150},[7924]={"first-aid",225},[10846]={"first-aid",300} }
    local all=ns.EnsureProfRecipes and ns.EnsureProfRecipes() or {}
    local spellName=(C_Spell and C_Spell.GetSpellName) or GetSpellInfo
    local function addName(spell)
        if type(spell)~="number" or not spellName then return end
        local ok,name,subtext=pcall(spellName,spell)
        if not ok or not name then return end
        if C_Spell and C_Spell.GetSpellSubtext then local subOk,sub=pcall(C_Spell.GetSpellSubtext,spell); if subOk then subtext=sub end end
        local key=name.."\031"..tostring(subtext or "")
        if names[key] and names[key]~=spell then names[key]=false elseif names[key]==nil then names[key]=spell end
        if names[name] and names[name]~=spell then names[name]=false elseif names[name]==nil then names[name]=spell end
    end
    for _,p in ipairs(ns.ProfRecipeKeys or {}) do
        for _,kind in ipairs({"rows","crafted","enchants"}) do for _,row in ipairs((all[p] or {})[kind] or {}) do
            addName(kind=="enchants" and row[14] or row[1]); tick()
        end end
    end
    for spell in pairs(ranks) do addName(spell) end
    local countOk,count=call("GetNumTrainerServices")
    if not countOk or type(count)~="number" then return end
    for i=1,count do
        local infoOk,name,subtext,status=call("GetTrainerServiceInfo",i)
        local spellOk,spell=call("C_Trainer.GetServiceSpellID",i)
        if not spellOk or type(spell)~="number" then spellOk,spell=call("GetTrainerServiceSpellID",i) end
        if type(spell)~="number" then
            local linkOk,link=call("GetTrainerServiceItemLink",i)
            spell=linkOk and type(link)=="string" and tonumber(link:match("enchant:(%d+)") or link:match("spell:(%d+)")) or nil
        end
        spell=spell or (infoOk and (names[tostring(name).."\031"..tostring(subtext or "")] or names[name]))
        local requirement={}
        if GetTrainerServiceLevelReq then local ok,level=pcall(GetTrainerServiceLevelReq,i); if ok and type(level)=="number" then requirement.level=level end end
        if GetTrainerServiceSkillReq then local ok,skillName,skill=pcall(GetTrainerServiceSkillReq,i); if ok and type(skill)=="number" then requirement.skill=skill; requirement.skillName=skillName end end
        if spell then
            d.learningRequirements[spell]=requirement
            local book=runtime(); book[spell]=book[spell] or {}; book[spell].available=true; book[spell].trainerObserved=true
        end
        tick()
    end
end
function E.RefreshClientData(readRecipes,readTrainer)
    local deadline,ops=0,0
    local function now() return debugprofilestop and debugprofilestop() or 0 end
    local function tick()
        ops=ops+1
        if ops>=1000 or (deadline>0 and now()>=deadline) then ops=0; coroutine.yield() end
    end
    local co=coroutine.create(function()
        runtime()
        if readRecipes then E.ScanRecipes(tick); E.ScanCrafts(tick) end
        if readTrainer then E.ScanTrainer(tick) end
    end)
    local function step()
        deadline=now()+2
        local ok,err=coroutine.resume(co)
        if not ok then E.lastReadError=tostring(err) end
        if not ok or coroutine.status(co)=="dead" then
            E.APICapabilities()
            if ns.ProfRouteAuto and ns.ProfRouteAuto.Invalidate then ns.ProfRouteAuto.Invalidate() end
            return true
        end
        return false
    end
    if ns.IdleJobs and ns.IdleJobs.Add then ns.IdleJobs.Add(step)
    else while not step() do end end
end
function E.DiagnosticText(d)
    if type(d)=="string" then return d end
    local messages={vendorEstimate="商人售价待读取，请打开对应商人窗口。",
        vendorQuoteChanged="已有可靠商人报价，点击重新计算更新路线。",
        cooldown="已排除有冷却的制作配方。",
        cooldownUnknown="制作冷却尚未核实，请打开对应专业面板。",outputConflict="制作产量待读取，请打开对应专业面板。",
        availabilityUnknown="配方学习条件尚未核实。",excluded="配方已按自定义规则排除。",notLearned="当前设置仅允许已学配方。",
        clientUnavailable="客户端已确认此配方不可用。",
        professionMissing="角色尚未学习所需专业。",skillRequired="另一专业技能不足，可开启联合升级或购买材料。",
        secondaryRequired="请先选择联合升级的另一个专业。",
        pairingChanged="搭配专业已更改，点击重新计算应用。",
        formulaUnavailable="未学配方的图纸没有可靠的购买报价；任务图纸需先学会或取得拍卖行报价。",
        formulaPriceUnknown="图纸购买价格尚未核实。",
        formulaStockUnknown="图纸为限量或未核实库存，不能保证商人现货。",
        auctionSupplyLimited="拍卖行可购数量不足，无法继续此配方；请查询更多货物或改用其他配方。",
        fishingRecipeGap="当前技能没有符合纯钓鱼条件的可用配方，请检查食谱、材料来源或排除设置。",
        materialUnavailable="材料没有可靠的购买或制作来源。",levelGap="当前技能区间没有可用升级配方。",
        clientDataPending="客户端数据待读取，请打开对应专业面板。",solverError="计算发生错误，请重新计算。",
        vendorPending="部分商人价格尚未读取，当前结果仅比较已知价格。",
        characterLevelRequired="角色等级不足，无法学习所需专业等级。",
        vendorPriceUnknown="商人材料价格待读取，请打开对应商人窗口后重新计算。",
        materialPriceUnknown="拍卖行价格未知，先按已有资料显示路线。",
        batchDependency="合并制作所需的材料或学习等级尚未满足。",
        batchSkillGap="合并制作后无法达到目标技能，请调整配方限制。"}
    local l=ns.L or {}; local text=l[messages[d.code] or "客户端数据待读取"] or messages[d.code] or d.code
    local spell=d.spell; local item=d.item
    if spell then
        local fn=(C_Spell and C_Spell.GetSpellName) or GetSpellInfo; local name=fn and fn(spell)
        text=text.." ("..tostring(name or ("#"..spell))..")"
    elseif item then
        local fn=(C_Item and C_Item.GetItemInfo) or GetItemInfo; local name=fn and fn(item)
        text=text.." ("..tostring(name or ("#"..item))..")"
    end
    return text
end
if CreateFrame then
    local f=CreateFrame("Frame")
    for _,ev in ipairs({"TRADE_SKILL_LIST_UPDATE","TRADE_SKILL_SHOW","TRADE_SKILL_DETAILS_UPDATE","CRAFT_SHOW","CRAFT_UPDATE","TRAINER_SHOW","TRAINER_UPDATE","CHAT_MSG_SKILL","SKILL_LINES_CHANGED","SPELLS_CHANGED"}) do pcall(f.RegisterEvent,f,ev) end
    local pending=false; local dirtyRecipe,dirtyTrainer=false,false
    f:SetScript("OnEvent",function(_,ev)
        if ev:find("TRADE_SKILL") or ev:find("CRAFT") then dirtyRecipe=true end
        if ev:find("TRAINER") then dirtyTrainer=true end
        if pending then return end; pending=true
        local function update()
            pending=false
            local recipes,trainer=dirtyRecipe,dirtyTrainer; dirtyRecipe,dirtyTrainer=false,false
            E.RefreshClientData(recipes,trainer)
        end
        if C_Timer and C_Timer.After then C_Timer.After(.1,update) else update() end
    end)
end
if ns.Init then ns.Init(function() E.RefreshClientData(true,false) end) end
if SlashCmdList then
    SLASH_DFPROFAPI1="/dfprofapi"
    SlashCmdList.DFPROFAPI=function()
        local report=E.APIReport()
        for line in report:gmatch("[^\n]+") do
            if DEFAULT_CHAT_FRAME and DEFAULT_CHAT_FRAME.AddMessage then DEFAULT_CHAT_FRAME:AddMessage(line) elseif print then print(line) end
        end
    end
end
