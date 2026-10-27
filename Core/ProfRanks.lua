-- Rank guidance is a live view over the reference data. It never changes a
-- frozen crafting plan, the purchase ledger, or recorded execution facts.
local _, ns = ...
if not ns.LoadForeverPages then return end
local R = {}
ns.ProfRanks = R

local ids = { [171]="alchemy", [164]="blacksmithing", [333]="enchanting", [202]="engineering",
    [165]="leatherworking", [197]="tailoring", [186]="mining", [182]="herbalism", [393]="skinning",
    [185]="cooking", [129]="first-aid", [356]="fishing" }
local names = {
    alchemy={"炼金术","鍊金術","Alchemy"}, blacksmithing={"锻造","鍛造","Blacksmithing"},
    enchanting={"附魔","附魔","Enchanting"}, engineering={"工程学","工程學","Engineering"},
    leatherworking={"制皮","製皮","Leatherworking"}, tailoring={"裁缝","裁縫","Tailoring"},
    mining={"采矿","採礦","Mining"}, herbalism={"采药","草藥學","Herbalism"},
    skinning={"剥皮","剝皮","Skinning"}, cooking={"烹饪","烹飪","Cooking"},
    ["first-aid"]={"急救","急救","First Aid"}, fishing={"钓鱼","釣魚","Fishing"},
}
local ranks = {{"初级","初級","Apprentice"}, {"中级","中級","Journeyman"},
    {"高级","高級","Expert"}, {"专家级","專家級","Artisan"}}
local function locale()
    return GetLocale and GetLocale() or "zhCN"
end
local function tr(zh, tw, en)
    local loc=locale()
    return loc=="enUS" and en or (loc=="zhTW" and tw or zh)
end
local function label(value)
    if type(value)~="table" then return value end
    return value[locale()] or value.zhCN or value.enUS or value[locale()=="enUS" and 3 or (locale()=="zhTW" and 2 or 1)]
end
local function number(value, minimum)
    value=tonumber(value)
    if value and value==value and value<math.huge and value>=(minimum or 0) then return value end
end
local function safe(fn,...)
    if type(fn)~="function" then return false end
    return pcall(fn,...)
end
local function copy(value)
    if type(value)~="table" then return value end
    local out={}
    for key,item in pairs(value) do out[key]=copy(item) end
    return out
end

local function trainerData(slug)
    if ns.EnsureProfTrainers then ns.EnsureProfTrainers() end
    return ns.ProfTrainers and ns.ProfTrainers[slug]
end
local function professionData(slug)
    local data=trainerData(slug)
    if not data then return end
    local info=ns.ProfData and ns.ProfData.pro and ns.ProfData.pro[slug]
    local out={name=info and info.name,ranks={}}
    local prior=1
    for index, raw in ipairs(data.ranks or {}) do
        local method="trainer"
        if (slug=="cooking" or slug=="first-aid" or slug=="fishing") and index==3 then method="book"
        elseif (slug=="cooking" or slug=="first-aid" or slug=="fishing") and index==4 then method="quest" end
        local note,book
        for _,row in ipairs(info and info.ranks or {}) do
            if tonumber(row[2])==raw.cap and type(row[3])=="string" then note=row[3];book=row[4];break end
        end
        out.ranks[#out.ranks+1]={rank=index,cap=raw.cap,skillRequired=raw.sk,levelRequired=raw.lv,
            method=method,name={zhCN=raw.zh,zhTW=raw.tw,enUS=raw.en},trainerRange=prior.."-"..tostring(raw.cap),
            status="reference",conditionsKnown=raw.sk~=nil and raw.lv~=nil,note=note,bookItemID=book,
            referenceNote=tr("晋级门槛和获取方式为现有资料参考；缺失条件保持未知，实际开放以游戏为准。",
                "晉級門檻和取得方式為現有資料參考；缺失條件保持未知，實際開放以遊戲為準。",
                "Rank thresholds and acquisition are references; missing requirements stay unknown. Verify availability in game.")}
        prior=raw.cap
    end
    return out
end
local function sourcesFor(slug,entry,state)
    local out={}
    local data=trainerData(slug)
    -- A reference book/task keeps its own acquisition method. Trainer locations
    -- are useful directions, not evidence that a trainer bypasses that method.
    for _,raw in ipairs(data and data.list or {}) do
        if raw.rng==entry.trainerRange and (not state.faction or not raw.fac or raw.fac=="N" or raw.fac==state.faction) then
            out[#out+1]={kind=entry.method=="book" and "vendor" or entry.method,
                name={zhCN=raw.zh,zhTW=raw.tw,enUS=raw.en},
                zone={zhCN=raw.loc_zh,zhTW=raw.loc_tw,enUS=raw.loc_en},
                faction=raw.fac,map=raw.map,x=raw.x,y=raw.y,npcID=raw.npcID,itemID=entry.bookItemID}
        end
    end
    return out
end

-- Unknown API state stays unknown. In particular, do not use Economy's
-- solver defaults (1/75), a saved plan's cap, or skill points as rank evidence.
function R.Status(slug, opts)
    opts=opts or {}
    local state={known=false}
    local loginOK, loggedIn=safe(IsLoggedIn)
    if not loginOK or loggedIn~=false then
        local ok,a,b,c,d,e,f=safe(GetProfessions)
        if ok and type(GetProfessionInfo)=="function" then
            local slots, valid, found={a,b,c,d,e,f},true,false
            for i=1,6 do
                if slots[i] then
                    local success,name,_,cur,cap,_,_,skillID=safe(GetProfessionInfo,slots[i])
                    if not success or not name or not ids[skillID] then valid=false end
                    if success and ids[skillID]==slug then
                        found=true
                        state.skill, state.maxSkill=number(cur),number(cap,1)
                        state.learned=true
                        state.known=state.skill~=nil and state.maxSkill~=nil
                    end
                end
            end
            if valid and not found then
                state.known,state.learned,state.skill,state.maxSkill=true,false,0,0
            end
        end
    end
    local ok,level=safe(UnitLevel,"player")
    if ok then state.level=number(level,1) end
    local factionOK,faction=safe(UnitFactionGroup,"player")
    if factionOK then state.faction=faction=="Alliance" and "A" or (faction=="Horde" and "H" or nil) end
    if opts.skill~=nil then state.skill=number(opts.skill) end
    if opts.maxSkill~=nil then state.maxSkill=number(opts.maxSkill) end
    if opts.skill~=nil or opts.maxSkill~=nil then
        state.known=state.skill~=nil and state.maxSkill~=nil
        state.learned=state.maxSkill and state.maxSkill>0 or false
    end
    if opts.level~=nil then state.level=number(opts.level,1) end
    if opts.faction~=nil then
        state.faction=opts.faction=="Alliance" and "A" or (opts.faction=="Horde" and "H" or opts.faction)
    end
    return state
end

local function rankChoices(profession)
    local groups,order={},{}
    for _,entry in ipairs(profession.ranks or {}) do
        local key=entry.rank or ("spell:"..tostring(entry.spell))
        if not groups[key] then groups[key]={};order[#order+1]=key end
        groups[key][#groups[key]+1]=entry
    end
    local function score(entry)
        local observed=ns.ProfEconomy and ns.ProfEconomy.observedRankRequirements
            and entry.spell and ns.ProfEconomy.observedRankRequirements[entry.spell]
        return (observed and observed.available==true and 1000000 or 0)
            +(type(entry.cap)=="number" and 100000 or 0)
            +(entry.status=="confirmed" and 10000 or 0)
            +(entry.conditionsKnown==true and 1000 or 0)
            +math.min(99,#(entry.conditions or {}))*10+math.min(9,#(entry.sources or {}))
    end
    local out={}
    for _,key in ipairs(order) do
        local candidates=groups[key]
        table.sort(candidates,function(a,b)
            local sa,sb=score(a),score(b)
            if sa~=sb then return sa>sb end
            return (tonumber(a.spell) or 0)<(tonumber(b.spell) or 0)
        end)
        local selected=copy(candidates[1])
        -- Several real spells may confer the same profession rank. Guidance
        -- represents that rank once; its alternative spell facts stay intact.
        if #candidates>1 then selected.candidates=copy(candidates) end
        out[#out+1]=selected
    end
    table.sort(out,function(a,b)return (a.rank or 0)<(b.rank or 0) end)
    return out
end

function R.RouteSteps(slug, target, opts)
    local profession=professionData(slug)
    local out={}
    if not profession then return out end
    local state=R.Status(slug,opts)
    target=number(target) or 300
    local priorCap=0
    for _,entry in ipairs(rankChoices(profession)) do
        entry=copy(entry)
        local observed=ns.ProfEconomy and ns.ProfEconomy.observedRankRequirements
            and entry.spell and ns.ProfEconomy.observedRankRequirements[entry.spell]
        if observed and type(observed.level)=="number" and type(observed.skill)=="number" then
            if observed.available==true then
                entry.levelRequired,entry.skillRequired=observed.level,observed.skill
                entry.conditionsKnown,entry.status,entry.method=true,"confirmed","trainer"
            else
                entry.levelRequired=entry.levelRequired or observed.level
                entry.skillRequired=entry.skillRequired or observed.skill
            end
        end
        local preferences={rankReminders={cooking={[4]=200},["first-aid"]={[4]=200},fishing={[4]=200}},rankReminderWindow=25}
        local reminders=preferences.rankReminders or {}
        reminders=reminders[slug] or {}
        local reminder=reminders[entry.spell] or reminders[tostring(entry.spell)] or reminders[entry.rank]
            or entry.skillRequired or math.max(0,priorCap-(preferences.rankReminderWindow or 25))
        if reminder<=target then
            local step={}
            for key,value in pairs(entry) do step[key]=value end
            step.id="rank:"..slug..":"..tostring(entry.rank)
            step.profession,step.reminderSkill=slug,reminder
            step.name=label(entry.name) or label(ranks[entry.rank]) or tostring(entry.rank)
            step.professionName=label(profession.name) or label(names[slug]) or slug
            step.state=state
            step.sources=sourcesFor(slug,entry,state)
            local factsKnown=entry.conditionsKnown==true
                and type(entry.cap)=="number" and type(entry.skillRequired)=="number" and type(entry.levelRequired)=="number"
            local qualificationAllowed=true
            if entry.conditions and ns.ProfEconomy and ns.ProfEconomy.LearningEligibility then
                local snapshot={known={},level=state.level,faction=state.faction,professions={[slug]={cur=state.skill}},specializationAbilities={}}
                if type(UnitClass)=="function" then local ok,_,_,id=pcall(UnitClass,"player");if ok then snapshot.classID=id end end
                if type(UnitRace)=="function" then local ok,_,_,id=pcall(UnitRace,"player");if ok then snapshot.raceID=id end end
                local _,_,detail
                qualificationAllowed,_,detail=ns.ProfEconomy.LearningEligibility({spell=entry.spell,profession=slug,_conditionsCheck=entry.conditions},snapshot)
                if detail and detail.status=="unknown" then factsKnown=false end
            end
            step.complete=state.known and type(entry.cap)=="number" and state.maxSkill>=entry.cap or false
            step.available=not step.complete and factsKnown and qualificationAllowed and state.known and state.skill>=entry.skillRequired
                and (entry.levelRequired==0 or state.level~=nil and state.level>=entry.levelRequired) or false
            if observed and observed.available==true and not step.complete then step.available=true end
            step.due=not step.complete and state.skill~=nil and state.skill>=reminder
            if step.complete then step.status="complete"
            elseif step.available then step.status="available"
            elseif not state.known then step.status="unknown"
            elseif type(entry.levelRequired)=="number" and state.level and state.level<entry.levelRequired then step.status="level_locked"
            elseif type(entry.skillRequired)=="number" and state.skill<entry.skillRequired then step.status="skill_locked"
            elseif not qualificationAllowed and entry.conditions and #entry.conditions>0 and factsKnown then step.status="requirements_locked"
            elseif not factsKnown or ((entry.levelRequired or 0)>0 and not state.level) then step.status="unknown"
            elseif not qualificationAllowed then step.status="requirements_locked"
            else step.status="available" end
            out[#out+1]=step
        end
        if type(entry.cap)=="number" then priorCap=entry.cap end
    end
    return out
end

function R.NextStep(slug, target, opts)
    local steps=R.RouteSteps(slug,target,opts)
    local state=steps[1] and steps[1].state
    -- A guide may show a rank early, but a route that ends inside the current
    -- cap does not require another rank and must be allowed to finish.
    if state and state.known and (number(target) or 300)<=state.maxSkill then return nil end
    for _,step in ipairs(steps) do if not step.complete then return step end end
end

function R.Title(step)
    return string.format(tr("%s · %s（上限 %s）","%s · %s（上限 %s）","%s · %s (cap %s)"),
        step.professionName,step.name,tostring(step.cap or "?"))
end

function R.Lines(step)
    local out={}
    if step.complete then
        out[#out+1]=tr("已学习：当前技能上限已达到此阶。","已學習：目前技能上限已達到此階。","Learned: the current skill cap confirms this rank.")
    elseif step.status=="unknown" then
        out[#out+1]=tr("晋级资料或角色资格尚未确认；请在游戏中核对。","晉級資料或角色資格尚未確認；請在遊戲中核對。","Rank facts or character eligibility are unknown; check in game.")
    elseif step.available then
        out[#out+1]=tr("已达到参考条件；提升技能上限后继续路线。","已達到參考條件；提升技能上限後繼續路線。","Reference requirements met; raise the skill cap to continue.")
    else
        out[#out+1]=tr("尚未达到学习条件。","尚未達到學習條件。","Learning requirements are not yet met.")
    end
    if type(step.levelRequired)=="number" and step.levelRequired>0 then
        out[#out+1]=string.format(tr("需要技能 %d · 角色等级 %d","需要技能 %d · 角色等級 %d","Requires skill %d · character level %d"),
            step.skillRequired or 0,step.levelRequired)
    elseif step.skillRequired~=nil then
        out[#out+1]=string.format(tr("需要技能 %d","需要技能 %d","Requires skill %d"),step.skillRequired or 0)
    end
    if step.reminderSkill<(step.skillRequired or 0) then
        out[#out+1]=string.format(tr("%d 点开始准备；达到 %d 点后办理任务晋级。","%d 點開始準備；達到 %d 點後辦理任務晉級。","Prepare at skill %d; complete the rank quest at skill %d."),
            step.reminderSkill,step.skillRequired)
    end
    local methods={
        trainer={"向对应阶级的专业训练师学习。","向對應階級的專業訓練師學習。","Learn from a trainer for this rank."},
        book={"购买并阅读教材。","購買並閱讀教材。","Buy and read the skill book."},
        quest={"完成专业晋级任务。","完成專業晉級任務。","Complete the profession rank quest."},
    }
    if methods[step.method] then out[#out+1]=label(methods[step.method]) end
    local function add(value) value=label(value); if value and value~="" then out[#out+1]=value end end
    add(step.note)
    if step.bookItemID then out[#out+1]=tr("教材：#","教材：#","Book: #")..step.bookItemID end
    for _,source in ipairs(step.sources or {}) do
        local prefix=source.faction=="A" and tr("联盟 · ","聯盟 · ","Alliance · ")
            or (source.faction=="H" and tr("部落 · ","部落 · ","Horde · ") or "")
        local text=prefix..(label(source.name) or (source.npcID and ("NPC "..source.npcID)) or "")
        local zone=label(source.zone)
        if zone then text=text.." · "..zone end
        if number(source.x) and number(source.y) then text=text..string.format(" (%.1f, %.1f)",source.x,source.y) end
        if text~="" then out[#out+1]=text end
        if source.itemName or source.itemID then
            out[#out+1]=tr("教材：","教材：","Book: ")..(label(source.itemName) or ("#"..source.itemID))
        end
        if source.questName or source.questID then
            out[#out+1]=tr("任务：","任務：","Quest: ")..(label(source.questName) or ("#"..source.questID))
        end
        add(source.note)
    end
    add(step.referenceNote)
    return out
end
