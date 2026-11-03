local _, ns = ...

if not ns.LoadForeverPages then return end

local Host = ns.ProfHost
if not Host then return end

local L = ns.L
local DG = Host.DG
local MakeFS, NewButton = Host.MakeFS, Host.NewButton
local SetButtonSelected = Host.SetButtonSelected

local function ProfIconTex(name)
    if not name then return Host.FALLBACK_ICON end
    if type(name) == "string" and not name:find("\\", 1, true) then
        return "Interface\\Icons\\" .. name
    end
    return name
end

local function RoundFrame(fr, radius, col)
    if not (ns.hui and ns.hui.BuildRoundBorder) then return nil end
    local pieces = ns.hui.BuildRoundBorder(fr, radius, col, fr, "OVERLAY", "both", 1) or {}
    for _, tex in ipairs(pieces) do tex:SetShown(true) end
    return pieces
end
local function RoundBG(fr, radius, col)
    if not (ns.hui and ns.hui.BuildRoundedBG) then
        fr:SetBackdropColor(col[1], col[2], col[3], col[4])
        return nil
    end
    fr:SetBackdropColor(0, 0, 0, 0)
    fr.__rbg = ns.hui.BuildRoundedBG(fr, radius, col, "both", false)
    return fr.__rbg
end
local Unpack = Host.Unpack
local C_GOLD, C_GREY, C_DIM, C_TEXT = Host.C_GOLD, Host.C_GREY, Host.C_DIM, Host.C_TEXT
local C_WHITE = Host.C_WHITE

local D  = ns.ProfData
local R
local function RGet(k)
    if not R then
        R = ns.ProfRecipes
    end
    return R and R[k] or nil
end
local LV = ns.ProfLeveling
local RA = ns.ProfRouteAuto
local function trackingPaused()
    local xp=ns.ProfExecution
    return xp and xp.IsCombatPaused and xp.IsCombatPaused()
end

local format = string.format

local PF = {}
ns.ProfFollow = PF

local f
local cueState = {}

local W, W_BASE = 375, 375
local PAD = 12
local SRC_COL_W = 68
local SRC_TEXT_W = 56
local NUM_CAP = 56
local TAG_CAP = 46
local BTN_W = { 92, 66, 66 }
local BTN_GAP = 4
local MAT_MAX = 6
local SHOP_MAX = 16
local SWEEP_MAX = 5
local IMPORT_TRIES = 5

local C_OK   = { 0.27, 0.75, 0.45 }
local C_BAD  = { 0.85, 0.30, 0.30 }
local C_HEAD = { 0.95, 0.78, 0.35 }

local CUE_FILES = {
    cap = "Interface\\AddOns\\DungeonsForever\\Media\\Voice\\prof_skill_cap.ogg",
    item = "Interface\\AddOns\\DungeonsForever\\Media\\Voice\\prof_next_item.ogg",
    on = "Interface\\AddOns\\DungeonsForever\\Media\\Voice\\prof_voice_on.ogg",
    nol = "Interface\\AddOns\\DungeonsForever\\Media\\Voice\\prof_not_learned.ogg",
}

local function cueMuted()
    local db = DungeonsForeverDB
    local p = db and db.prof
    return (p and p.muteCue) and true or false
end

local function playCue(kind)
    if cueMuted() then return end
    if type(PlaySoundFile) ~= "function" then return end
    local path = CUE_FILES[kind]
    if path then pcall(PlaySoundFile, path, "Master") end
end

local function cueMsg(msg)
    if DEFAULT_CHAT_FRAME then
        DEFAULT_CHAT_FRAME:AddMessage("|cff33ff99无限副本手册:|r " .. msg, 1, 1, 1)
    end
end

if type(SlashCmdList) == "table" then
    SLASH_DUNGEONSFOREVERVOICE1 = "/dfvoice"
    SLASH_DUNGEONSFOREVERVOICE2 = "/df语音"
    SlashCmdList["DUNGEONSFOREVERVOICE"] = function(msg)
        local k = type(msg) == "string" and msg:match("^%s*(.-)%s*$") or ""
        k = k:lower()
        if k == "cap" or k == "上限" or k == "1" then
            playCue("cap")
            cueMsg(L["播放：专业技能点上限了"])
        elseif k == "item" or k == "下一件" or k == "2" then
            playCue("item")
            cueMsg(L["播放：做下一件物品啦"])
        elseif k == "on" or k == "开启" or k == "3" then
            playCue("on")
            cueMsg(L["播放：语音开启"])
        elseif k == "nol" or k == "未学" or k == "4" then
            playCue("nol")
            cueMsg(L["播放：该配方还未学会，先找训练师学习"])
        else
            playCue("cap")
            cueMsg(L["播放：专业技能点上限了"])
            if C_Timer and C_Timer.After then
                C_Timer.After(1.8, function()
                    playCue("item")
                    cueMsg(L["播放：做下一件物品啦"])
                end)
            end
        end
    end
end

local function Accent()
    local PD = ns.ProfModule
    if PD and PD.NavAccent then return { PD.NavAccent() } end
    if ns.hui and ns.hui.ACCENT then return { ns.hui.ACCENT[1], ns.hui.ACCENT[2], ns.hui.ACCENT[3] } end
    return { 0x46 / 255, 0xbf / 255, 0x72 / 255 }
end

local function SpellName(id)
    if not id then return "?" end
    local nm
    if C_Spell and C_Spell.GetSpellInfo then
        local info = C_Spell.GetSpellInfo(id)
        nm = info and info.name
    end
    if (type(nm) ~= "string" or nm == "") and type(GetSpellInfo) == "function" then
        nm = GetSpellInfo(id)
    end
    if type(nm) == "string" and nm ~= "" then return nm end
    return format(L["法术 #%d"], id)
end

local function IsLearned(spellID)
    if not spellID then return false end
    if C_Spell and C_Spell.IsSpellKnown then
        local ok, r = pcall(C_Spell.IsSpellKnown, spellID)
        if ok and r then return true end
    end
    for _, fn in ipairs({ IsSpellKnown, IsPlayerSpell }) do
        if type(fn) == "function" then
            local ok, r = pcall(fn, spellID)
            if ok and r then return true end
        end
    end
    return false
end

local function Have(id, includeBank)
    local bank=includeBank~=false
    if C_Item and C_Item.GetItemCount then
        local ok, n = pcall(C_Item.GetItemCount, id, bank, false, false)
        if ok and type(n) == "number" and n>=0 and n<math.huge and n==math.floor(n) then return n,true end
    end
    if type(GetItemCount) == "function" then
        local ok, n = pcall(GetItemCount, id, bank)
        if ok and type(n) == "number" and n>=0 and n<math.huge and n==math.floor(n) then return n,true end
    end
    return 0,false
end

local function dbProf()
    DungeonsForeverDB = DungeonsForeverDB or {}
    DungeonsForeverDB.prof = DungeonsForeverDB.prof or {}
    return DungeonsForeverDB.prof
end

local function charKey()
    local name = type(UnitName) == "function" and UnitName("player") or nil
    local realm = type(GetRealmName) == "function" and GetRealmName() or nil
    return (name or "?") .. "-" .. (realm or "?")
end

local function onlyMissView()
    return dbProf().shopOnlyMiss and true or false
end

local function st()
    local p = dbProf()
    p.follow = p.follow or {}
    return p.follow[charKey()]
end

local function skillOf(slug)
    local PD = ns.ProfModule
    if PD and PD.ProfLearned then
        local learned = PD.ProfLearned(true)
        local e = learned[slug]
        if e then return e.cur, e.max end
    end
    return nil, nil
end

local function routeTarget(slug)
    local PD = ns.ProfModule
    local v
    if PD and PD.cur == slug and PD.LvTarget then
        v = PD.LvTarget()
    else
        local db = dbProf()
        v = tonumber(db.lvTarget and db.lvTarget[slug])
    end
    if not v then return 300 end
    return math.max(1, math.min(300, math.floor(v)))
end

function PF.RankTasks(slug, target, steps, currentIndex)
    local ranks = ns.ProfRanks
    if not (ranks and ranks.NextStep) then return {} end
    local targets, order = {[slug] = target or routeTarget(slug)}, {slug}
    local current = steps and steps[currentIndex or 1]
    local partner = current and current.profession
    if partner and partner ~= slug then
        local recipe = current.recipe or {}
        targets[partner] = math.max(tonumber(current.goalSkill or current[2]) or 0, tonumber(recipe.learn) or 0)
        order[#order + 1] = partner
    end
    local tasks = {}
    for _, profession in ipairs(order) do
        local step = ranks.NextStep(profession, targets[profession])
        if step and step.due then tasks[#tasks + 1] = step end
    end
    return tasks
end

local function updateCues(slug, rankTasks)
    if cueState.slug ~= slug then cueState = { slug = slug } end
    local caps, newCap = {}, false
    for _, task in ipairs(rankTasks) do
        local state = task.state or {}
        if task.due and state.known and state.maxSkill and state.maxSkill > 0
            and state.skill and state.skill >= state.maxSkill then
            local key = tostring(task.profession) .. ":" .. tostring(state.maxSkill)
            caps[key] = true
            if not (cueState.caps and cueState.caps[key]) then newCap = true end
        end
    end
    cueState.caps = caps
    local XP = ns.ProfExecution
    local run = XP and XP.GetActive and XP.GetActive(slug)
    local index = run and run.currentIndex or 1
    local plan = run and XP.GetPlan(slug)
    local steps = plan and (plan.executionSteps or plan.steps)
    local seg = steps and steps[index]
    local step = seg and (seg.segmentID or seg)
    local advanced = run and cueState.run == run and cueState.step and step ~= cueState.step
        and index > (cueState.index or 0)
    cueState.run, cueState.step, cueState.index = run, step, index
    local craft = seg and not seg.navigationOnly and not seg.checkpoint and (tonumber(seg[3]) or 0) > 0
        and not XP.IsConversion(seg) and not XP.IsSpecializationQuest(seg)
    if newCap then playCue("cap")
    elseif advanced and craft and not next(caps) then playCue("item") end
end

function PF.SpecializationQuestInfo(seg)
    local xp=ns.ProfExecution
    if not (xp and xp.IsSpecializationQuest(seg)) then return end
    local goal=xp.SpecializationQuest(seg)
    local function label(value)
        if type(value)~="table" then return value end
        local locale=GetLocale and GetLocale() or "zhCN"
        return value[locale] or value.zhCN or value.enUS
    end
    local name=label(goal.questName or goal.name) or L["专业专精任务"]
    local lines={}
    local identity=goal.questID and format(L["任务 #%d"],goal.questID) or L["任务身份尚未确认"]
    lines[#lines+1]=identity
    local requirements={}
    if type(goal.minSkill)=="number" then requirements[#requirements+1]=format(L["需要专业技能 %d"],goal.minSkill) end
    if type(goal.minLevel)=="number" then requirements[#requirements+1]=format(L["需要角色等级 %d"],goal.minLevel) end
    if #requirements>0 then lines[#lines+1]=table.concat(requirements," · ") end
    if type(goal.inputs) == "table" and #goal.inputs > 0 then
        local materials = {}

        for _, pair in ipairs(goal.inputs) do
            local itemID = tonumber(pair[1])
            local quantity = tonumber(pair[2])

            if itemID and quantity and quantity > 0 then
                local name = DG.ItemName(itemID)

                if not name or name == "" then
                    name = "#" .. itemID
                    if DG.RequestItem then
                        DG.RequestItem(itemID)
                    end
                end

                materials[#materials + 1] =
                    format("%s ×%d", name, quantity)
            end
        end

        if #materials > 0 then
            lines[#lines + 1] = format(L["任务材料：%s"],table.concat(materials, L["、"]))
        end
    end
    local place={}
    if label(goal.npcName) then place[#place+1]=label(goal.npcName)
    elseif goal.npcID then place[#place+1]="#"..goal.npcID end
    if label(goal.zone) then place[#place+1]=label(goal.zone) end
    if #place>0 then lines[#lines+1]=table.concat(place," · ") end
    if type(goal.x)=="number" and type(goal.y)=="number" then
        lines[#lines+1]=format(L["参考坐标 %.2f, %.2f"],goal.x,goal.y)
    end
    local prerequisites={}
    for _,id in ipairs(goal.prerequisiteQuestIDs or {}) do prerequisites[#prerequisites+1]="#"..id end
    if #prerequisites>0 then
        lines[#lines+1]=format(L["先完成前置任务并与导师对话：%s"],table.concat(prerequisites,", "))
    end
    local progress={}
    for key,value in pairs(goal.questProgress or {}) do progress[key]=value end
    local api=C_QuestLog
    if goal.questID and api then
        for _, probe in ipairs({
            {"inLog", "IsOnQuest"},
            {"readyForTurnIn", "ReadyForTurnIn"},
            {"completed", "IsQuestFlaggedCompleted"},
        }) do
            if type(api[probe[2]])=="function" then
                local ok,value=pcall(api[probe[2]],goal.questID)
                if ok and type(value)=="boolean" then progress[probe[1]]=value end
            end
        end
    end
    local status =
        progress.completed and L["任务已完成"]
        or progress.readyForTurnIn and L["任务可交付"]
        or progress.inLog and L["任务已接取"]
        or nil
    if status then lines[#lines+1]=status end
    lines[#lines+1]=L["实际学会对应专精后才完成此步骤。"]
    return {name=name,lines=lines,summary=identity..(status and " · "..status or ""),goal=goal}
end

local function clipFixedSteps(steps, target)
    if not target or target >= 300 then return steps end
    local out = {}
    for _, st in ipairs(steps or {}) do
        local a, b = st[1], st[2]
        if a > target then break end
        local nb, nq = math.min(b, target), st[4] or 0
        local isClip = b > target
        if isClip then
            nq = math.max(1, math.ceil(nq * (target - a) / (b - a) - 1e-9))
        end
        local clipped={}
        for key,value in pairs(st) do clipped[key]=value end
        clipped[2],clipped[4],clipped._clip=nb,st.checkpoint and 0 or nq,isClip or nil
        out[#out + 1] = clipped
    end
    return out
end

local function isGathering(slug)
    local gathering=ns.ProfGatheringRoutes
    if not (gathering and gathering.HasRoute(slug)) then return false end
    local view=ns.ProfModule
    return not (slug=="mining" and view and view.GatherMode and view.GatherMode(slug)=="smelt")
end
local function hasRoute(slug)
    return slug and ((LV[slug] and LV[slug].steps) or (ns.ProfGatheringRoutes and ns.ProfGatheringRoutes.HasRoute(slug)))
end
local function routeForCalc(slug, skill)
    if slug=="poisons" then
        PF.pendingPlans=PF.pendingPlans or {};PF.pendingPlans[slug]=nil
        local guide=LV[slug]
        return "fixed",clipFixedSteps(guide and guide.steps,routeTarget(slug))
    end
    if isGathering(slug) then
        PF.pendingPlans=PF.pendingPlans or {};PF.pendingPlans[slug]=nil
        local steps=ns.ProfGatheringRoutes.Steps(slug,routeTarget(slug))
        if not steps then PF.pendingPlans[slug]={status="incomplete",diagnostics={{code="professionCapUnknown"}}} end
        return "gather",steps or {}
    end
    local XP = ns.ProfExecution
    local frozen, planError
    if XP and XP.GetPlan then frozen, planError = XP.GetPlan(slug) end
    if planError then
        PF.pendingPlans=PF.pendingPlans or {}
        PF.pendingPlans[slug]={status="recalculate_required",slug=slug,feasible=false,diagnostics={{code=planError}}}
        return "auto",{}
    end
    local economy=ns.ProfEconomy
    if frozen and frozen.learningPolicyFingerprint and economy and economy.LearningPolicyFingerprint
        and frozen.learningPolicyFingerprint~=economy.LearningPolicyFingerprint() then
        PF.pendingPlans=PF.pendingPlans or {}
        PF.pendingPlans[slug]={status="recalculate_required",feasible=false,diagnostics={{code="learningPolicyChanged"}}}
        return "auto",{}
    end
    local PD = ns.ProfModule
    local fixedOnly=slug=="first-aid" or slug=="poisons" or slug=="mining" and PD and PD.GatherMode and PD.GatherMode(slug)=="smelt"
    if frozen and fixedOnly and frozen.mode~="fixed" then
        PF.pendingPlans=PF.pendingPlans or {}
        PF.pendingPlans[slug]={status="recalculate_required",feasible=false,diagnostics={{code="fixedOnlyChanged"}}}
        return "fixed",{}
    end
    if frozen then return frozen.mode == "fixed" and "fixed" or "auto", frozen.executionSteps or frozen.steps,frozen end
    local ended = PF.endedPlan and PF.endedPlan[slug]
    if ended and PF.Following and PF.Following(slug) then return ended.mode == "fixed" and "fixed" or "auto", ended.executionSteps or ended.steps,ended end
    local scheme = PD and PD.SettingRaw and PD.SettingRaw("autoScheme",slug) or "cheapest"
    local smelt = slug == "mining" and PD and PD.GatherMode and PD.GatherMode(slug) == "smelt"
    local fish = PD and PD.CookingFishingMode and PD.CookingFishingMode(slug)
    local auto = not fixedOnly and not smelt and PD and PD.Setting and (PD.Setting("autoRoute",slug) or fish) and RA
    PF.pendingPlans = PF.pendingPlans or {}
    if auto then
        local opts = RA.OptionsFor and RA.OptionsFor(slug, skill) or {
            start = (PD.Setting("autoFromCurrent",slug) and skill) and math.max(1, skill) or 1,
            onlyAH = PD.Setting("autoOnlyAH",slug),
            allowLimitedFormulas=PD.Setting("autoBuyLimitedFormulas",slug),
            allowBindOnPickupFormulas=PD.Setting("autoAllowBindOnPickupFormulas",slug),
            allowCurrencyFormulas=PD.Setting("autoAllowCurrencyFormulas",slug), target = routeTarget(slug), scheme = fish and "fishing" or scheme,
        }
        opts.target = routeTarget(slug)
        local res = RA.Get(slug, opts)
        local list = res and (res.executionSteps or res.steps)
        if res and res.status ~= "selection_required" and res.status ~= "recalculate_required" and res.feasible ~= false
            and list and #list > 0 then
            PF.pendingPlans[slug] = nil
            local hudState = st()
            if XP and XP.Bind
                and hudState
                and hudState.slug == slug
                and not hudState.hidden
                and not hudState.autoTrackSuspended
                and res.status ~= "searching" then
                XP.Bind(slug, res)
                frozen = XP.GetPlan(slug)
                if frozen then return "auto", frozen.executionSteps or frozen.steps,frozen end
            end
            return "auto", list,res
        end
        PF.pendingPlans[slug] = res or {status="searching"}
        return "auto", {}
    end
    PF.pendingPlans[slug] = nil
    local lv = LV[slug]
    local steps=clipFixedSteps(lv and lv.steps or nil,routeTarget(slug))
    local opts=RA and RA.OptionsFor and RA.OptionsFor(slug,skill) or {}
    opts.target,opts.scheme=routeTarget(slug),"fixed"
    local summary=RA and RA.FixedPlan and RA.FixedPlan(slug,opts)
    if summary and summary.status=="recalculate_required" then
        PF.pendingPlans[slug]=summary
        return "fixed",{}
    end
    if summary then steps=summary.steps end
    if RA and RA.FilterFixedSpecializations then
        local filtered,blocked,goalRequired=RA.FilterFixedSpecializations(slug,steps,opts)
        if goalRequired or blocked and #blocked>0 then
            PF.pendingPlans[slug]={status="recalculate_required",specializationBlocked=true,
                diagnostics=blocked or {},steps={},feasible=false}
            return "fixed",{}
        end
        steps=filtered
    end
    local hudState = st()
    if XP and hudState
        and hudState.slug == slug
        and not hudState.hidden
        and not hudState.autoTrackSuspended
        and steps and #steps > 0 then
        summary=summary or RA and RA.SummarizeSteps and RA.SummarizeSteps(steps,slug,opts)
        summary=summary or {steps=steps,mats={},formulas={},total=0,scheme="fixed",target=routeTarget(slug)}
        summary.mode="fixed";summary.scheme="fixed"
        local normalized,reason=XP.NormalizePlan(slug,summary)
        if not normalized or summary.feasible==false then
            PF.pendingPlans[slug]={status="recalculate_required",feasible=false,diagnostics={{code=reason or "fixedUnavailable"}}}
            return "fixed",{}
        end
        local run=XP.Bind(slug,normalized)
        if run then return "fixed",run.plan.executionSteps or run.plan.steps,run.plan end
    end
    return "fixed",steps,summary
end

local rMemoSlug, rMemoSkill, rMemoMode, rMemoSteps, rMemoPlan, rMemoT
local ROUTE_MEMO_TTL = 10
local function routeFor(slug, skill)
    local now = GetTime and GetTime() or 0
    if slug and rMemoSlug == slug and rMemoSkill == skill
       and (now - (rMemoT or 0)) < ROUTE_MEMO_TTL then
        return rMemoMode, rMemoSteps,rMemoPlan
    end
    local mode, steps,plan = routeForCalc(slug, skill)
    rMemoSlug, rMemoSkill, rMemoMode, rMemoSteps, rMemoT = slug, skill, mode, steps, now
    rMemoPlan=plan
    return mode, steps,plan
end

function PF.InvalidateRoute()
    rMemoSlug, rMemoSkill, rMemoMode, rMemoSteps, rMemoPlan, rMemoT = nil, nil, nil, nil, nil,nil
end

local function routeKey(mode, steps)
    if not steps then return tostring(mode) .. ":0" end
    local a, b = steps[1], steps[#steps]
    return format("%s:%d:%s:%s:%s", tostring(mode), #steps,
                  tostring(a and a[1]), tostring(a and a[3]), tostring(b and b[2]))
end

local function derivedStep(slug, skill)
    local XP = ns.ProfExecution
    local run = slug~="poisons" and not isGathering(slug) and XP and XP.GetRun and XP.GetRun(slug)
    if run then XP.Sync(slug); return run.currentIndex or 1 end
    local ended = slug~="poisons" and PF.endedPlan and PF.endedPlan[slug]
    if ended and PF.Following and PF.Following(slug) then return #(ended.executionSteps or ended.steps or {}) + 1 end
    local _, steps = routeFor(slug, skill)
    if not steps then return nil end
    for i, s in ipairs(steps) do
        if next(s.requiredOutputs or {}) or s.kind == "specialization_quest" or s.kind == "essence_conversion" or skill < s[2] then return i end
    end
    return #steps + 1
end

local function recMats(rec) return rec and (rec[12] or rec.mats) or nil end
function PF.LearningWarning(slug, progress)
    if slug=="poisons" then return end
    local XP=ns.ProfExecution
    progress=progress or (XP and XP.Progress and XP.Progress(slug))
    if not (progress and progress.learningBlocked) then return end
    local E=ns.ProfEconomy
    return E and E.DiagnosticText and E.DiagnosticText(progress.reason or "learningDataMissing")
        or L["学习来源尚未确认"]
end
local function stepRecipe(seg, fallback)
    if seg and seg.recipe then return seg.recipe end
    local XP = ns.ProfExecution
    if seg and XP and XP.IsConversion(seg) then
        local conversion = XP.Conversion(seg)
        if conversion then return {mats={{conversion.inputItemID,conversion.inputCount}},item=conversion.outputItemID,count=conversion.outputCount} end
    end
    if seg and XP and XP.IsSpecializationQuest(seg) then return {mats=XP.SpecializationQuest(seg).inputs or {}} end
    return fallback
end
local function recItem(rec) return rec and (rec[2] or rec.item or rec.makes) or nil end
local function recBreaks(rec)
    if not rec then return nil end
    return rec[7] or rec.learn, rec[8] or rec.yellow, rec[9] or rec.green, rec[10] or rec.grey
end

local recCache = {}
local function recMap(slug)
    local c = recCache[slug]
    if not c then
        c = {}
        local rr = RGet(slug)
        if rr and rr.rows then
            for _, r in ipairs(rr.rows) do c[r[1]] = r end
        end
        local lv = LV[slug]
        if lv and type(lv.rinfo) == "table" then
            for spell, ri in pairs(lv.rinfo) do
                if not c[spell] then c[spell] = ri end
            end
        end
        recCache[slug] = c
    end
    return c
end

local soldCache = {}
local function soldSet(slug)
    local s = soldCache[slug]
    if not s then
        s = {}
        local lv = LV[slug]
        if lv and lv.sold then
            for _, id in ipairs(lv.sold) do s[id] = true end
        end
        soldCache[slug] = s
    end
    return s
end

local function purchaseSource(entry)
    local source=entry.source or entry.sourceType
    if source~=nil then return source end
    return entry.vendor and "vendor" or nil
end

local function copyPurchase(entry)
    local out={}
    for key,value in pairs(entry) do out[key]=value end
    out.id=entry.id or entry[1]
    out.count=tonumber(entry.count or entry[2]) or 0
    out.source=purchaseSource(entry)
    return out
end

local function allocatePurchases(row)
    row.purchases={};row.purchaseCount=0;row.purchaseCost=0
    row.ahCount,row.vendorCount=0,0
    row.materialNeed=math.max(0,(row.need or 0)-(row.formulaNeed or 0))
    row.materialMissing=row.haveKnown and math.max(0,row.materialNeed-math.max(0,row.have-(row.formulaNeed or 0))) or nil
    if not row.haveKnown then
        row.purchaseCount,row.purchaseCost=nil,nil
        row.purchaseUnknown=true;row.inventoryUnknown=true
        return
    end
    local left=math.max(0,row.need-row.have)
    row.missing=left
    row.baseMissing=math.max(0,(row.baseNeed or row.need)-row.have)
    row.reserveMissing=math.max(0,left-row.baseMissing)
    local bridge=ns.AuctionBridge
    local useSupply=row.considerAuctionSupply~=false
    local available=useSupply and row.availableCount or nil
    if useSupply and row.planAHCount>0 and bridge and bridge.GetAuctionSupply then
        local observed=bridge.GetAuctionSupply(row.id)
        available=observed and observed.quantity or nil
        row.availableCount=available;row.supplyObserved=available~=nil
        row.supplyStatus=bridge.GetAuctionSupplyStatus and bridge.GetAuctionSupplyStatus(row.id) or (available==nil and "unknown" or "verified")
    end
    row.supplyChanged=available~=nil and available<row.planAHCount
    local function add(entry,count,cost)
        if count<=0 then return end
        local item=copyPurchase(entry);item.count=count;item[2]=count;item.cost=cost
        row.purchases[#row.purchases+1]=item
        row.purchaseCount=row.purchaseCount+count
        if type(cost)=="number" and not item.unpriced then row.purchaseCost=row.purchaseCost and row.purchaseCost+cost
        else row.purchaseCost=nil;row.costUnknown=true end
        if item.source=="ah" or item.source=="auction" then row.ahCount=row.ahCount+count
        elseif item.source=="vendor" or item.source=="npc" then row.vendorCount=row.vendorCount+count end
    end
    local formulaLeft=math.max(0,(row.formulaNeed or 0)-row.have)
    local formulaAH=0
    for _,entry in ipairs(row.planPurchases or {}) do
        if entry.formula and formulaLeft>0 then
            local count=math.min(formulaLeft,entry.count)
            add(entry,count,entry.cost)
            formulaLeft=formulaLeft-count;left=math.max(0,left-count)
            if entry.source=="ah" or entry.source=="auction" then formulaAH=formulaAH+count end
            if entry.usable==false or entry.unavailable or entry.available==false or entry.purchasable==false then row.purchaseUncovered=(row.purchaseUncovered or 0)+count end
        end
    end
    local offers,auction,ahLimit={},nil,0
    local hasMaterials=false;local quotesComplete=true
    for _,entry in ipairs(row.planPurchases or {}) do
        if not entry.formula then
            hasMaterials=true
            local source=entry.source
            if source=="ah" or source=="auction" then
                ahLimit=ahLimit+entry.count
                local unit=entry.unit or (type(entry.cost)=="number" and entry.count>0 and entry.cost/entry.count)
                if type(unit)=="number" and unit>0 and (not auction or auction==unit) and not entry.unpriced then auction=unit
                else quotesComplete=false end
            elseif source=="vendor" or source=="npc" then
                local offer=copyPurchase(entry)
                local size=entry.bundleSize or 1
                local price=entry.bundlePrice or (type(entry.cost)=="number" and entry.count>0 and entry.cost*size/entry.count)
                if type(price)=="number" and price>=0 and not entry.unpriced and entry.unlimited==true then
                    offer.quantity,offer.price=size,price;offers[#offers+1]=offer
                else quotesComplete=false end
            else quotesComplete=false end
        end
    end
    if available~=nil then ahLimit=math.min(ahLimit,math.max(0,available-formulaAH)) end
    if left>0 and hasMaterials then
        local entries,complete
        if quotesComplete and RA and RA.MaterialPurchases then
            local snap={prices={[row.id]=auction},offers={[row.id]=offers},auctionSupply={},considerAuctionSupply=useSupply}
            if available~=nil then snap.auctionSupply[row.id]={quantity=ahLimit} end
            local total
            entries,total,complete=RA.MaterialPurchases(row.id,left,{snapshot=snap,auctionRemaining={[row.id]=ahLimit}})
        elseif row.have==0 and row.need==row.planDemand then
            entries={};complete=true
            for _,entry in ipairs(row.planPurchases or {}) do if not entry.formula then entries[#entries+1]=entry end end
        elseif row.planVendorCount==0 and row.planAHCount>=left+formulaAH then
            entries={{id=row.id,count=left,source="ah",unit=auction,cost=auction and auction*left}}
            complete=available==nil or available>=left+formulaAH
        else
            row.purchaseUnknown=true;row.purchaseCount,row.purchaseCost=nil,nil
        end
        if entries then
            local covered=0
            local remainingAH=ahLimit
            for _,entry in ipairs(entries) do
                local count=tonumber(entry.count or entry[2]) or 0
                local cost=entry.cost
                if purchaseSource(entry)=="ah" or purchaseSource(entry)=="auction" then
                    local requested=count
                    count=math.min(count,remainingAH);remainingAH=math.max(0,remainingAH-count)
                    if count~=requested then cost=entry.unit and entry.unit*count or (type(entry.cost)=="number" and requested>0 and entry.cost*count/requested) or nil end
                end
                add(entry,count,cost)
                if purchaseSource(entry)~=nil then covered=covered+count end
            end
            if complete==false or covered<left then row.purchaseUncovered=(row.purchaseUncovered or 0)+math.max(0,left-covered) end
        end
    elseif left>0 then row.purchaseUncovered=(row.purchaseUncovered or 0)+left end
    if row.purchaseCount then row.packSurplus=math.max(0,row.purchaseCount-row.missing) end
    if useSupply and row.ahCount>0 then
        row.auctionUnknown=available==nil
        if available~=nil and available<row.ahCount then row.auctionShortage=row.ahCount-available end
    end
    row.purchaseChanged=row.purchaseCount~=row.planPurchaseCount or row.purchaseCost~=row.planPurchaseCost
end

local function fmtTime(sec)
    local m = math.floor(sec / 60)
    local s = math.floor(sec % 60)
    return format(L["用时 %d 分 %d 秒"], m, s)
end

function PF.IsActive(slug)
    local s = st()
    if not (s and s.slug == slug and not s.hidden) then return false end
    return (PF.f and PF.f:IsShown()) and true or false
end

function PF.Following(slug)
    local s = st()
    return (s and s.slug == slug) and true or false
end

function PF.SuspendAutoTrack(slug, reason)
    if reason == "recalculate" and PF.endedPlan then PF.endedPlan[slug] = nil end
    local s = st()
    if s and s.slug == slug then
        s.autoTrackSuspended = reason or true
        PF.InvalidateRoute()
    end
end

function PF.Sync()
    if trackingPaused() then PF.combatPaused=true;return false end
    local s = st()
    if not (s and s.slug) then return false end
    if s.autoTrackSuspended=="inactive" then
        local xp=ns.ProfExecution
        if not (xp and xp.GetActive(s.slug)) then return false end
        s.autoTrackSuspended=nil
    end
    local changed = PF.combatPaused or false
    PF.combatPaused=nil
    local cur, maxSkill = skillOf(s.slug)

    local skillChanged = cur ~= nil and cur ~= s.skill
    local capChanged = maxSkill ~= nil and maxSkill ~= s.maxSkill

    if skillChanged or capChanged then
        if cur ~= nil then s.skill = cur end
        if maxSkill ~= nil then s.maxSkill = maxSkill end

        changed = true

        local PD = ns.ProfModule
        if PD and PD.built and PD.cur == s.slug
            and PD.page and PD.page:IsVisible() then
            pcall(PD.Render, PD)
        end
    end
    local mode, steps = routeFor(s.slug, s.skill or 0)
    local key = routeKey(mode, steps)
    if key ~= s.rkey then
        s.rkey = key
        s.step = derivedStep(s.slug, s.skill or 0) or 1
        PF.view = 0
        changed = true
    end
    local d = derivedStep(s.slug, s.skill or 0)
    if d and d > (s.step or 1) then
        s.step = d
        changed = true
    end
    return changed
end

function PF.PaintMute(btn)
    local bt = btn or (PF.f and PF.f.muteBtn)
    if not (bt and bt.tex) then return end
    local muted = cueMuted()
    SetButtonSelected(bt, muted)
    if bt.__hover then
        bt.tex:SetVertexColor(1, 1, 1, 1)
    elseif muted then
        bt.tex:SetVertexColor(0.95, 0.32, 0.32, 0.98)
    else
        local r, g, b = 0.78, 0.78, 0.78
        local xb = PF.f and PF.f.xBtn
        if xb and xb.GetFontString then
            local fs = xb:GetFontString()
            if fs and fs.GetTextColor then
                local tr, tg, tb = fs:GetTextColor()
                if tr then r, g, b = tr, tg, tb end
            end
        end
        bt.tex:SetVertexColor(r, g, b, 0.95)
    end
end

function PF.RefreshRoute(slug)
    local s = st()
    if not (s and s.slug) then return end
    if slug and slug ~= s.slug then return end
    PF.InvalidateRoute()
    PF.Sync()
    if PF.f and PF.f:IsShown() then pcall(PF.Paint) end
end

function PF.RefreshMainUI()
    local PD = ns.ProfModule
    if PD and PD.built and PD.page and PD.page.IsVisible and PD.page:IsVisible() then
        if PD.RequestRender then PD.RequestRender() end
    end
end

function PF.Toggle(slug)
    if not hasRoute(slug) then return end
    local p = dbProf()
    p.follow = p.follow or {}
    local k = charKey()
    local s = p.follow[k]
    if s and s.slug ~= slug then s = nil end
    if s and not s.hidden and PF.building then
        s.hidden = true
        PF.onBuilt = nil
        PF.RefreshMainUI()
        return
    end
    if s and not s.hidden and PF.f and PF.f:IsShown() then
        s.hidden = true
        PF.f:Hide()
        PF.RefreshMainUI()
        return
    end
    if not s then
        if PF.endedPlan then PF.endedPlan[slug] = nil end
        local cur = skillOf(slug) or 0
        s = { slug = slug, skill = cur, step = derivedStep(slug, cur) or 1, t0 = time() }
        local _mode, _steps = routeFor(slug, cur)
        s.rkey = routeKey(_mode, _steps)
        p.follow[k] = s
    end
    s.hidden = nil
    s.autoTrackSuspended = nil
    PF.InvalidateRoute()
    if PF.f then
        PF.Sync()
        PF.view = 0
        PF.f:Show()
        PF.Paint()
        PF.RefreshMainUI()
        return
    end
    if PF.building then return end
    PF.onBuilt = function()
        if not PF.f then return end
        PF.Sync()
        PF.view = 0
        PF.f:Show()
        PF.Paint()
        PF.RefreshMainUI()
    end
    PF.Build()
end

function PF.Prev()
    local s = st()
    if not (s and s.slug) then return end
    local _, steps = routeFor(s.slug, s.skill)
    if not steps then return end
    PF.view = math.max(-((s.step or 1) - 1), (PF.view or 0) - 1)
    PF.Paint()
end

function PF.Skip()
    local s = st()
    if not (s and s.slug) then return end
    local _, steps = routeFor(s.slug, s.skill)
    if not steps then return end
    PF.view = math.min(#steps - (s.step or 1) + 1, (PF.view or 0) + 1)
    PF.Paint()
end

function PF.VerifyCurrentOutput(total, ref)
    local T = ns.ProfExecution
    local s = st()
    if not (s and s.slug and T and T.VerifyOutput and T.Progress) then return false end
    local run = T.GetRun(s.slug)
    local prog = run and T.Progress(s.slug, nil, nil, run.planID)
    if not ref and prog then ref = {index=prog.index,item=prog.outputItem,planID=run.planID} end
    if not ref or not ref.item or ref.finished then return false end
    if ref.planID and (not run or ref.planID ~= run.planID) then return false end
    total = tonumber(total)
    if not total or total < 0 or total ~= math.floor(total) then return false end
    local ok
    if ref.manualConversion or prog and prog.manualConversion then
        ok = T.ConfirmConversion and T.ConfirmConversion(s.slug, ref.index, total, run and run.planID)
    else ok = T.VerifyOutput(s.slug, ref.index, ref.item, total) end
    PF.InvalidateRoute(); PF.Sync()
    PF.view = 0
    PF.Paint()
    return ok ~= false
end

local function verifyOutputDialog()
    local T = ns.ProfExecution
    local s = st()
    if not (s and s.slug and T and T.GetRun and T.Progress) then return end
    if not (StaticPopupDialogs and StaticPopup_Show) then return end
    local run = T.GetRun(s.slug)
    local prog = run and T.Progress(s.slug, nil, nil, run.planID)
    if not prog or not prog.outputItem or prog.finished then return end
    local data = { slug = s.slug, index = prog.index, item = prog.outputItem, total = prog.manualConversion and prog.remainingConversions or prog.actualOutputs or 0, manualConversion = prog.manualConversion, planID = run.planID }
    StaticPopupDialogs.DF_PROF_VERIFY_OUTPUT = {
        text = prog.manualConversion and L["填写本次已完成的精华转换次数。"] or L["填写本步骤累计实际产出件数（不是当前背包数量）。"],
        button1 = L["确认"], button2 = L["取消"], hasEditBox = true,
        timeout = 0, whileDead = true, hideOnEscape = true, preferredIndex = 3,
        OnShow = function(self)
            local edit = self.editBox or (self.GetEditBox and self:GetEditBox())
            if edit then
                edit:SetText(tostring((self.data and self.data.total) or 0))
                edit:SetFocus()
                edit:HighlightText()
            end
            ns.SkinPopupFont(self)
        end,
        OnAccept = function(self)
            local d = self.data
            local edit = self.editBox or (self.GetEditBox and self:GetEditBox())
            local n = edit and tonumber(edit:GetText())
            if not (d and n and n >= 0 and n == math.floor(n)) then return end
            PF.VerifyCurrentOutput(n, d)
        end,
    }
    StaticPopup_Show("DF_PROF_VERIFY_OUTPUT", nil, nil, data)
end

local function expPerPoint(sk, o, y, g, gr)
    if sk < y then return 1 end
    if sk < g then return 1 / (1 - 0.5 * (sk - y) / (g - y)) end
    if sk < gr then return 1 / (0.5 - 0.45 * (sk - g) / (gr - g)) end
    return nil
end

local function craftsLeft(seg, skill, rec,routeSlug,future)
    local XP = ns.ProfExecution
    if seg.segmentID and XP and XP.CurrentPlan then
        local slug = routeSlug or (st() and st().slug)
        local run = slug and XP.GetRun(slug)
        if run then
            local progress = XP.Progress(run.slug, seg.segmentID)
            if progress and (progress.segmentID==seg.segmentID or progress.complete~=true) then
                if XP.IsSpecializationQuest(seg) then return progress.complete and 0 or 1 end
                local untouched=(progress.attemptsDone or 0)==0 and type(progress.currentSkill)=="number"
                    and progress.currentSkill<=(seg[1] or 0)
                if (future or untouched) and not progress.skillDone and not (XP.IsConversion and XP.IsConversion(seg)) then
                    if seg.reason~="material" and seg.role~="material" then
                        local planned=math.max(0,(seg.expectedCrafts or seg[4] or 0)-(progress.attemptsDone or 0))
                        local output=seg.outputMin or rec and (rec.outputMin or rec.count or rec[3]) or 1
                        local required=output>0 and math.ceil((progress.remainingOutputs or 0)/output) or 0
                        return math.max(planned,required)
                    end
                end
                return progress.remainingCrafts or 0
            end
        end
    end
    if XP and XP.IsSpecializationQuest(seg) then return 1 end
    if seg.segmentID and (future or (skill or 0)<=(seg[1] or 0)) then
        return seg.expectedCrafts or seg[4] or 0
    end
    local from = math.max(skill or 0, seg[1])
    if from >= seg[2] then return 0 end
    local learn, y, g, gr = recBreaks(rec)
    if y and g and gr and g > y and gr > g then
        local total = 0
        for sk = from, seg[2] - 1 do
            local e = expPerPoint(sk, learn, y, g, gr)
            if not e then break end
            total = total + e
        end
        if expPerPoint(seg[2] - 1, learn, y, g, gr) then return total end
    end
    local span = math.max(1, seg[2] - seg[1])
    return (seg[4] or 0) * math.min(1, (seg[2] - from) / span)
end

local function currentCands(steps, skill, curStep, slug, rm, run)
    local out = { math.max(1, math.min(#steps, curStep or 1)) }
    local XP = ns.ProfExecution
    local first = steps[out[1]]
    local profession = first and (first.profession or slug)
    if profession ~= slug then skill = skillOf(profession) or 0 end
    local reserved, produced, consumers = {}, {}, {}
    for i = out[1], #steps do
        local sg = steps[i]
        if (sg.profession or slug) ~= profession or sg.navigationOnly or sg.checkpoint or sg.tool
            or (tonumber(sg[3]) or 0) <= 0
            or XP and (XP.IsConversion(sg) or XP.IsSpecializationQuest(sg)) then break end
        local a, b = tonumber(sg[1]) or 0, tonumber(sg[2]) or 0
        if i > out[1] and a > skill then break end
        local rec = stepRecipe(sg, rm[sg[3]])
        local progress = run and XP.Progress(slug, sg.segmentID or i, nil, run.planID)
        if progress and progress.blocked then break end
        local remaining = math.ceil(craftsLeft(sg, skill, rec, slug, i ~= out[1]))
        if i > out[1] and a <= skill and skill < b and sg[3] ~= first[3]
            and remaining > 0 and not (progress and progress.complete)
            and not consumers[sg.segmentID or i] and IsLearned(sg[3]) then
            local safe = rec ~= nil
            if run and XP.ValidateLearning then safe = safe and XP.ValidateLearning(run.plan, slug, sg) end
            for _, m in ipairs(recMats(rec) or {}) do
                local have, known = Have(m[1], false)
                if not known or produced[m[1]] or have < (reserved[m[1]] or 0) + (m[2] or 1) * remaining then
                    safe = false; break
                end
            end
            if safe then out[2] = i; break end
        end
        if remaining > 0 then
            for _, m in ipairs(recMats(rec) or {}) do
                reserved[m[1]] = (reserved[m[1]] or 0) + (m[2] or 1) * remaining
            end
            local item = recItem(rec)
            if item then produced[item] = true end
            for _, allocation in ipairs(sg.allocations or {}) do
                if (allocation.count or 0) > 0 and allocation.consumerID then consumers[allocation.consumerID] = true end
            end
            for _, allocation in ipairs(sg.reserve and sg.reserve.allocations or {}) do
                if (allocation.count or 0) > 0 and allocation.consumerID then consumers[allocation.consumerID] = true end
            end
        end
    end
    return out
end

local function shopList(s, onlyStep, bagsOnly, suppliedPlan)
    local _, steps,plan
    if suppliedPlan then plan=suppliedPlan;steps=plan.executionSteps or plan.steps
    else _,steps,plan=routeFor(s.slug,s.skill) end
    if not steps then return {} end
    local rm = recMap(s.slug)
    local totals, order = {}, {}
    local futureOutputs,futureSpells={},{}
    local reserve=not onlyStep and plan and plan.reserve and plan.reserve.mode~="off" and ns.ProfReserve
    local xp=ns.ProfExecution
    local run=xp and xp.GetRun(s.slug)
    local matching=run and plan and (run.plan==plan or plan.planID and run.originPlanID==plan.planID)
    local casts,completed,baseRemaining={},{},{}
    if reserve and matching then for _,seg in ipairs(steps) do
        local progress=xp.Progress(s.slug,seg.segmentID)
        if progress and progress.segmentID==seg.segmentID then
            casts[seg.segmentID]=progress.casts;completed[seg.segmentID]=progress.complete
            baseRemaining[seg.segmentID]=progress.baseRemaining or 0
        end
    end end
    local reserveNeeds=reserve and reserve.Remaining(plan,casts,matching and run.reserveDisabled,completed) or {}
    local curStep = s.step or 1
    for i = curStep, #steps do
        if onlyStep and i > curStep then break end
        local seg = steps[i]
        local rec = stepRecipe(seg, rm[seg[3]])
        local mats = recMats(rec)
        local crafts = seg[4] or 0
        if seg.segmentID or i == curStep then
            crafts = math.ceil(craftsLeft(seg, s.skill, rec,s.slug,i>curStep))
        end
        if reserve and matching then
            crafts=math.min(crafts,baseRemaining[seg.segmentID] or 0)
        end
        if crafts>0 then
            futureSpells[(seg.profession or s.slug)..":"..tostring(seg[3])]=true
            local item=recItem(rec)
            local output=seg.outputMin or rec and (rec.outputMin or rec[3] or rec.count)
            if item and type(output)=="number" and output>0 then
                futureOutputs[item]=(futureOutputs[item] or 0)+crafts*output
            end
        end
        if mats and crafts > 0 then
            for _, m in ipairs(mats) do
                local e = totals[m[1]]
                if not e then
                    e = { id = m[1], need = 0, at = seg[1] }
                    totals[m[1]] = e
                    order[#order + 1] = m[1]
                end
                local qty = (m[2] or 1) * crafts
                e.need = e.need + qty
                if i == curStep then e.atStep = (e.atStep or 0) + qty end
            end
        end
    end
    local G = ns.ProfGates
    local active = s.slug~="poisons" and ns.ProfExecution and ns.ProfExecution.GetPlan(s.slug)
    local goal = (not active and not onlyStep) and G and G.SpecGoal and G.SpecGoal(s.slug, routeTarget(s.slug))
    if goal and type(goal.inputs) == "table" then
        for _, pair in ipairs(goal.inputs) do
            local sid, sn = pair[1], tonumber(pair[2]) or 0
            if type(sid) == "number" and sn > 0 then
                local e = totals[sid]
                if not e then
                    e = { id = sid, need = 0, at = math.huge }
                    totals[sid] = e
                    order[#order + 1] = sid
                end
                e.spec = true
                e.need = e.need + sn
            end
        end
    end
    if not onlyStep and plan then
        local leaves={}
        local originalNeeds,originalOutputs={},{}
        for _,segment in ipairs(steps) do
            local recipe=stepRecipe(segment,rm[segment[3]])
            local count=math.ceil(segment.expectedCrafts or segment[4] or 0)
            for _,material in ipairs(recMats(recipe) or {}) do originalNeeds[material[1]]=(originalNeeds[material[1]] or 0)+(material[2] or 1)*count end
            local item=recItem(recipe)
            local output=segment.outputMin or recipe and (recipe.outputMin or recipe[3] or recipe.count)
            if item and type(output)=="number" and output>0 then originalOutputs[item]=(originalOutputs[item] or 0)+output*count end
        end
        local function purchase(entry,formula)
            local id=entry.id or entry[1]
            if not id then return end
            local leaf=leaves[id]
            if not leaf then leaf={planPurchaseCount=0,planPurchaseCost=0,planAHCount=0,planVendorCount=0,planPurchases={}};leaves[id]=leaf end
            local count=tonumber(entry.count or entry[2]) or (formula and 1 or 0)
            local source=purchaseSource(entry)
            if leaf.source and leaf.source~=source then leaf.source="mixed"
            elseif not leaf.source then leaf.source=source end
            leaf.planPurchaseCount=leaf.planPurchaseCount+count
            if type(entry.cost)=="number" and not entry.unpriced then leaf.planPurchaseCost=leaf.planPurchaseCost and leaf.planPurchaseCost+entry.cost
            else leaf.planPurchaseCost=nil end
            leaf.considerAuctionSupply=plan.considerAuctionSupply
            local receipt=copyPurchase(entry);receipt.formula=formula and true or false;receipt.count=count
            receipt.considerAuctionSupply=plan.considerAuctionSupply
            leaf.planPurchases[#leaf.planPurchases+1]=receipt
            if source=="ah" or source=="auction" then leaf.planAHCount=leaf.planAHCount+count
            elseif source=="vendor" or source=="npc" then leaf.planVendorCount=leaf.planVendorCount+count end
            for _,key in ipairs({"npcID","unlimited","limited","stockUnknown","availableCount",
                "supplyObserved","supplyStatus","supplyRequired","supplyComplete","supplyObservedAt",
                "supplySource","supplyMethod","unit","bundleSize"}) do
                if leaf[key]==nil then leaf[key]=entry[key] end
            end
            if formula then leaf.formulaCost=(leaf.formulaCost or 0)+(entry.cost or 0) end
        end
        for _,entry in ipairs(plan.mats or {}) do purchase(entry) end
        if reserve then for _,entry in ipairs(plan.reserve.mats or {}) do purchase(entry) end end
        for id,quantity in pairs(plan.retainedToolItems or {}) do
            if leaves[id] then
                if not totals[id] then totals[id]={id=id,need=0,at=math.huge};order[#order+1]=id end
                totals[id].need=totals[id].need+(tonumber(quantity) or 0)
            end
        end
        for _,id in ipairs(plan.toolItems or {}) do
            if leaves[id] and not (plan.retainedToolItems and plan.retainedToolItems[id]) then
                if not totals[id] then totals[id]={id=id,need=0,at=math.huge};order[#order+1]=id end
                totals[id].need=totals[id].need+1
            end
        end
        for _,id in ipairs(order) do
            local row=totals[id]
            row.need=math.max(0,row.need-(futureOutputs[id] or 0))
            if type(plan.mats)=="table" and not leaves[id] then row.need=0 end
        end
        local economy=ns.ProfEconomy
        for _,entry in ipairs(plan.formulas or {}) do
            local spell=entry.spell
            local needed=not spell or futureSpells[(entry.profession or s.slug)..":"..spell]
            local known=entry.known or spell and economy and economy.Known and economy.Known(spell)
            local id=entry.id or entry[1]
            if id and needed and not known and entry.usable~=false then
                local row=totals[id]
                if not row then row={id=id,need=0,at=math.huge};totals[id]=row;order[#order+1]=id end
                local count=tonumber(entry.count or entry[2]) or 1
                if count>(row.formulaNeed or 0) then
                    purchase(entry,true)
                    row.need=row.need+count-(row.formulaNeed or 0)
                end
                row.formulaNeed=math.max(row.formulaNeed or 0,count)
                row.formula=true
            end
        end
        for _,id in ipairs(order) do
            local row,leaf=totals[id],leaves[id]
            if leaf then
                for key,value in pairs(leaf) do row[key]=value end
                local tools=tonumber((plan.retainedToolItems or {})[id]) or 0
                if tools==0 then for _,tool in ipairs(plan.toolItems or {}) do if tool==id then tools=1;break end end end
                row.planDemand=math.max(0,(originalNeeds[id] or 0)-(originalOutputs[id] or 0))+tools+(row.formulaNeed or 0)
            end
        end
        if reserve then
            for _,entry in ipairs(plan.reserve.materials or {}) do
                local id=entry.id;local amount=reserveNeeds[id] or 0
                if amount>0 then
                    if not totals[id] then totals[id]={id=id,need=0,at=math.huge};order[#order+1]=id end
                    local row=totals[id];row.baseNeed=row.need;row.reserveNeed=amount;row.need=row.need+amount
                    if not row.planPurchases and leaves[id] then for key,value in pairs(leaves[id]) do row[key]=value end end
                    row.planDemand=(row.planDemand or row.baseNeed)+entry.count
                end
            end
        end
    end
    local list = {}
    for _, id in ipairs(order) do
        local e = totals[id]
        if onlyStep or e.need>0 then
            e.have,e.haveKnown = Have(e.id,not (bagsOnly or reserve))
            if s.slug=="poisons" then
                e.vendor=soldSet(s.slug)[e.id] or false
                e.source=e.vendor and "vendor" or "ah"
            end
            if not onlyStep and e.planPurchases then allocatePurchases(e) end
            list[#list + 1] = e
        end
    end
    return list
end

function PF.ShoppingForPlan(slug,plan)
    local xp=ns.ProfExecution;local run=xp and xp.GetRun(slug)
    local matching=run and (run.plan==plan or plan.planID and run.originPlanID==plan.planID)
    return shopList({slug=slug,skill=skillOf(slug) or plan.start or 1,step=matching and run.currentIndex or 1},false,true,plan)
end

function PF.ShoppingList(slug,onlyStep)
    local state=st()
    if not state or state.slug~=slug then
        local skill=skillOf(slug) or 0
        state={slug=slug,skill=skill,step=derivedStep(slug,skill) or 1}
    end
    return shopList(state,onlyStep)
end

function PF.ShoppingSourceText(entry)
    if entry.planPurchases then
        if entry.inventoryUnknown then return L["请打开背包和银行，再查看需要购买的数量。"] end
        if entry.purchaseUnknown then return L["请核对价格"] end
        local parts={}
        if (entry.reserveNeed or 0)>0 then
            parts[#parts+1]=format(L["基础缺 %d · 备用缺 %d"],entry.baseMissing or 0,entry.reserveMissing or 0)
        end
        for _,purchase in ipairs(entry.purchases or {}) do
            local source=purchaseSource(purchase)
            local name=(source=="ah" or source=="auction") and L["拍卖行"]
                or (source=="vendor" or source=="npc") and (ns.ProfVendorNames and ns.ProfVendorNames[purchase.npcID] or L["商人"])
                or L["尚无购买来源"]
            local cost=type(purchase.cost)=="number" and not purchase.unpriced and RA and RA.MoneyStr and RA.MoneyStr(purchase.cost,"copper") or L["请核对价格"]
            local text=format("%s ×%d · %s",name,purchase.count or 0,cost)
            if (source=="ah" or source=="auction") and entry.considerAuctionSupply~=false then
                text=text.." · "..(entry.availableCount~=nil and format(L["可购 %d"],entry.availableCount) or L["请扫描拍卖行"])
            elseif purchase.unlimited then text=text.." · "..L["不限量"]
            elseif purchase.limited then text=text.." · "..L["限量"]
            elseif purchase.stockUnknown then text=text.." · "..L["请向商人确认现货"] end
            parts[#parts+1]=text
        end
        if (entry.packSurplus or 0)>0 then parts[#parts+1]=format(L["整包余量 %d"],entry.packSurplus) end
        if (entry.purchaseUncovered or 0)>0 then parts[#parts+1]=format(L["原计划货源还缺 %d 件，请重新计算。"],entry.purchaseUncovered) end
        if (entry.auctionShortage or 0)>0 then parts[#parts+1]=L["库存不足"] end
        return #parts>0 and format(L["待购：%s"],table.concat(parts," / ")) or L["已备齐"]
    end
    local source=purchaseSource(entry)
    local text
    if source=="mixed" then text=L["商人"].." / "..L["拍卖行"]
    elseif source=="vendor" or source=="npc" then
        text=ns.ProfVendorNames and ns.ProfVendorNames[entry.npcID] or L["商人"]
        if entry.unlimited then text=text.." · "..L["不限量"]
        elseif entry.limited then text=text.." · "..L["限量"]
        elseif entry.stockUnknown then text=text.." · "..L["请向商人确认现货"] end
    elseif source=="ah" or source=="auction" then
        text=L["拍卖行"]
        if entry.considerAuctionSupply~=false then text=text.." · "..(entry.availableCount and tostring(entry.availableCount) or L["请扫描拍卖行"]) end
    end
    if text and entry.formula and entry.formulaCost and RA and RA.MoneyStr then
        text=text.." · "..RA.MoneyStr(entry.formulaCost,"copper")
    end
    return text
end

function PF.ShoppingSourceDetail(entry)
    if not entry.planPurchases then return PF.ShoppingSourceText(entry) end
    local cost=type(entry.planPurchaseCost)=="number" and RA and RA.MoneyStr and RA.MoneyStr(entry.planPurchaseCost,"copper") or L["请核对价格"]
    local parts={PF.ShoppingSourceText(entry) or "",
        format(L["原料需 %d；原计划购入 %d，费用 %s"],entry.need or 0,entry.planPurchaseCount or 0,cost)}
    if entry.haveKnown and (entry.have or 0)>0 then parts[#parts+1]=L["已有材料已抵扣；按原计划货源和报价计算待购费用。"] end
    if entry.purchaseChanged and entry.supplyChanged then parts[#parts+1]=L["拍卖行可购数量已变化；待购数量按原计划货源和报价重新分配。"] end
    for _,purchase in ipairs(entry.planPurchases) do
        local item=copyPurchase(purchase)
        item.need=item.count;item.have=0
        parts[#parts+1]=format("%s ×%d · %s",PF.ShoppingSourceText(item) or L["尚无购买来源"],item.count,
            type(item.cost)=="number" and RA and RA.MoneyStr and RA.MoneyStr(item.cost,"copper") or L["请核对价格"])
    end
    if entry.auctionUnknown then parts[#parts+1]=L["请使用 Auctionator 完整扫描一次拍卖行，再重新计算路线。"] end
    if (entry.auctionShortage or 0)>0 then parts[#parts+1]=L["本次扫描的材料数量不够；请用 Auctionator 完整扫描后重新计算，或更换货源。"] end
    if entry.purchaseUncovered and entry.purchaseUncovered>0 then parts[#parts+1]=format(L["原计划货源还缺 %d 件，请重新计算。"],entry.purchaseUncovered) end
    if entry.inventoryUnknown then parts[#parts+1]=L["请打开背包和银行，再查看需要购买的数量。"] end
    return table.concat(parts,"\n")
end

local TipOn
function PF.VendorPurchases(slug, plan)
    if slug=="poisons" then return {} end
    local xp=ns.ProfExecution
    plan=plan or (xp and xp.GetPlan and xp.GetPlan(slug)) or (RA and RA.Peek and RA.Peek(slug))
    if not plan or plan.feasible==false then return {} end
    local state=st()
    if not state or state.slug~=slug then local skill=skillOf(slug) or 0;state={slug=slug,skill=skill,step=1} end
    local list=shopList(state,false,false,plan)
    local out,byKey={},{}
    for _,entry in ipairs(list) do
        for _,purchase in ipairs(entry.purchases or {}) do
            local source=purchaseSource(purchase)
            if not purchase.formula and (source=="vendor" or source=="npc") and purchase.count>0 then
                local key=tostring(entry.id)..":"..tostring(purchase.npcID or 0)
                local row=byKey[key]
                if not row then row={id=entry.id,need=0,missing=0,cost=0,npcID=purchase.npcID,have=entry.have};byKey[key]=row;out[#out+1]=row end
                row.need=row.need+purchase.count;row.missing=row.need
                row.cost=type(purchase.cost)=="number" and row.cost and row.cost+purchase.cost or nil
            end
        end
    end
    return out
end

function PF.SupplementNeeds(slug)
    slug = slug or (st() and st().slug)
    if not slug then return nil end
    local s = st()
    if not (s and s.slug == slug and s.step) then
        local cur = skillOf(slug) or 0
        s = { slug = slug, skill = cur, step = derivedStep(slug, cur) or 1 }
    end
    local list = shopList(s, true, true)
    local items, kinds, qty = {}, 0, 0
    for _, e in ipairs(list) do
        local lack = (e.need or 0) - (e.have or 0)
        if e.haveKnown and lack > 0 then
            items[#items + 1] = { id = e.id, need = e.need, have = e.have, lack = lack }
            kinds = kinds + 1
            qty = qty + lack
        end
    end
    if kinds == 0 then return nil end
    return { items = items, kinds = kinds, qty = qty, step = s.step, basis="bags" }
end

TipOn = function(bt, title, body)
    bt:SetScript("OnEnter", function(self)
        GameTooltip:SetOwner(self, "ANCHOR_TOP")
        GameTooltip:ClearLines()
        GameTooltip:AddLine(title, 1, 0.82, 0, true)
        if body then GameTooltip:AddLine(body, 1, 1, 1, true) end
        GameTooltip:Show()
    end)
    bt:SetScript("OnLeave", function() GameTooltip:Hide() end)
end

local function craftNotify(msg)
    if DEFAULT_CHAT_FRAME then
        DEFAULT_CHAT_FRAME:AddMessage("|cff33ff99无限副本手册:|r " .. msg, 1, 1, 1)
    end
end

local jumpPending
local jumpEvt
local jumpApply

local function jumpEvtInit()
    if jumpEvt or not CreateFrame then return end
    jumpEvt = CreateFrame("Frame")
    pcall(function() jumpEvt:RegisterEvent("TRADE_SKILL_LIST_UPDATE") end)
    jumpEvt:SetScript("OnEvent", function()
        local p = jumpPending
        if not p or p.eventQueued or p.applying or p.scheduled then return end
        if C_Timer and C_Timer.After then
            p.eventQueued = true
            C_Timer.After(0, function()
                p.eventQueued = nil
                if jumpPending == p then jumpApply() end
            end)
        elseif not p.applying then
            jumpApply()
        end
    end)
end

local function panelShown()
    local pf = _G.ProfessionsFrame
    if pf and pf.IsShown and pf:IsShown() then return true end
    local tf = _G.TradeSkillFrame
    return (tf and tf.IsShown and tf:IsShown()) or false
end

local function CraftingEntrySpellID(index)
    if not C_SpellBook or not C_SpellBook.GetSpellBookItemInfo or not Enum
        or not Enum.SpellBookSpellBank or not GetProfessionInfo then return nil end
    local _, _, _, _, count, offset = GetProfessionInfo(index)
    if type(count) ~= "number" or type(offset) ~= "number" then return nil end
    local fallback
    for slot = offset + 1, offset + count do
        local info = C_SpellBook.GetSpellBookItemInfo(slot, Enum.SpellBookSpellBank.Player)
        local spellID = info and info.spellID
        if type(spellID) == "number"
            and (not Enum.SpellBookItemType or info.itemType == Enum.SpellBookItemType.Spell) then
            fallback = fallback or spellID
            if C_TradeSkillUI and C_TradeSkillUI.CanTradeSkillShowCraftingUI
                and C_TradeSkillUI.CanTradeSkillShowCraftingUI(spellID) then
                return spellID
            end
        end
    end
    return fallback
end

local function openProfPanel(slug)
    local profName = D.pro and D.pro[slug] and D.pro[slug].name
    local ids = (GetProfessions and { GetProfessions() }) or {}
    local targetLine
    if type(GetProfessionInfo) == "function" then
        for _, idx in ipairs(ids) do
            if idx then
                local nm, _, _, _, _, _, skillLine = GetProfessionInfo(idx)
                if profName and nm == profName and skillLine then
                    targetLine = skillLine
                    if C_TradeSkillUI and C_TradeSkillUI.OpenTradeSkill
                        and pcall(C_TradeSkillUI.OpenTradeSkill, skillLine) then
                        return true, skillLine
                    end
                end
            end
        end
    end
    for _, idx in ipairs(ids) do
        if idx and GetProfessionInfo and GetProfessionInfo(idx) == profName then
            local sid = CraftingEntrySpellID(idx)
            local nm = sid and SpellName(sid)
            if nm and CastSpellByName and pcall(CastSpellByName, nm) then return true, targetLine end
            if sid and C_Spell and C_Spell.CastSpell and pcall(C_Spell.CastSpell, sid) then return true, targetLine end
        end
    end
    if profName and CastSpellByName then
        if pcall(CastSpellByName, profName) then return true, targetLine end
    end
    return false
end

local function modernJump(p)
    local frame = _G.ProfessionsFrame
    local cp = frame and frame.CraftingPage
    if not (frame and frame.IsShown and frame:IsShown() and cp) then return false end
    local CUI = C_TradeSkillUI
    if p.skillLine and CUI and CUI.GetBaseProfessionInfo then
        local ok, info = pcall(CUI.GetBaseProfessionInfo)
        if not ok or type(info) ~= "table" or tonumber(info.professionID) ~= p.skillLine then return false end
    end
    if cp.IsShown and not cp:IsShown() then
        if _G.EventRegistry and _G.EventRegistry.TriggerEvent then
            pcall(_G.EventRegistry.TriggerEvent, _G.EventRegistry, "Professions.ShowSelectedCraftingPage")
        end
        if cp.IsShown and not cp:IsShown() then return false end
    end
    local form = cp.SchematicForm
    if not form then return false end
    local transaction = form.transaction
    local recipeInfo = form.currentRecipeInfo
    local selected = transaction and tonumber(transaction.recipeID)
        or recipeInfo and tonumber(recipeInfo.recipeID)
    if selected ~= p.spellID then
        local search = cp.RecipeList and cp.RecipeList.SearchBox
        if search and search.GetText and search.SetText and search:GetText() ~= "" then
            pcall(search.SetText, search, "")
        end
        if cp.SelectRecipe and CUI and CUI.GetRecipeInfo then
            local ok, info = pcall(CUI.GetRecipeInfo, p.spellID)
            if ok and type(info) == "table" then pcall(cp.SelectRecipe, cp, info) end
        end
        return false
    end
    local box = cp.CreateMultipleInputBox
    if not (box and box.SetValue and box.GetValue) then return false end
    local count = p.count
    if box.GetMaxValue then
        local maxCount = tonumber(box:GetMaxValue())
        if not maxCount or maxCount <= 0 then return false end
        count = math.min(count, maxCount)
    end
    local ok = pcall(box.SetValue, box, count)
    if ok and tonumber(box:GetValue()) == count then
        p.filledCount = count
        return true
    end
    return false
end

function jumpApply()
    local p = jumpPending
    if not p or p.applying then return end
    p.applying = true
    local selected, counted = false, modernJump(p)
    local frame = _G.ProfessionsFrame
    local modern = frame and frame.CraftingPage and frame.IsShown and frame:IsShown()
    local matches = true
    if p.skillLine and C_TradeSkillUI and C_TradeSkillUI.GetBaseProfessionInfo then
        local ok, info = pcall(C_TradeSkillUI.GetBaseProfessionInfo)
        matches = ok and type(info) == "table" and tonumber(info.professionID) == p.skillLine
    end
    if not counted and not modern and matches and C_TradeSkillUI then
        local verified = false
        if C_TradeSkillUI.SetSelectedRecipe then
            local ok, accepted = pcall(C_TradeSkillUI.SetSelectedRecipe, p.spellID)
            selected = ok and accepted ~= false
            if selected and C_TradeSkillUI.GetSelectedRecipeID then
                local ok, rid = pcall(C_TradeSkillUI.GetSelectedRecipeID)
                verified = ok and tonumber(rid) == p.spellID
            end
        end
        if verified and C_TradeSkillUI.SetRecipeRepeatCount then
            local ok, accepted = pcall(C_TradeSkillUI.SetRecipeRepeatCount, p.spellID, p.count)
            counted = ok and accepted ~= false
        end
    end
    if not counted and not modern and matches and type(GetNumTradeSkills) == "function" then
        for i = 1, GetNumTradeSkills() do
            local nm = GetTradeSkillInfo(i)
            if nm == p.name then
                if SelectTradeSkill then
                    local ok, accepted = pcall(SelectTradeSkill, i)
                    selected = ok and accepted ~= false
                end
                if selected and GetTradeSkillSelectionIndex then
                    local ok, index = pcall(GetTradeSkillSelectionIndex)
                    selected = ok and index == i
                end
                if selected and SetTradeSkillRepeatCount then
                    local ok, accepted = pcall(SetTradeSkillRepeatCount, i, p.count)
                    counted = ok and accepted ~= false
                end
                break
            end
        end
    end
    p.applying = nil
    if jumpPending ~= p then return end
    if counted then
        jumpPending = nil
        craftNotify(format(L["已定位配方 %s，预填制造数量 %d —— 在专业面板点一次制造即可"], p.name, p.filledCount or p.count))
    elseif not p.scheduled then
        if (p.retries or 0) < 12 and C_Timer and C_Timer.After then
            p.scheduled = true
            C_Timer.After(0.2, function()
                p.scheduled = nil
                if jumpPending ~= p then return end
                p.retries = (p.retries or 0) + 1
                jumpApply()
            end)
        else
            jumpPending = nil
            craftNotify(selected and format(L["已选中配方 %s，请在专业面板输入制造数量"], p.name)
                or panelShown() and L["面板已打开但未能自动定位配方，请在列表中手动选择"]
                or L["无法自动打开专业面板，请手动打开后重试"])
        end
    end
end

local function jumpCraft(stepIdx)
    jumpPending = nil
    local s = st()
    if not (s and s.slug) then return end
    local _, steps = routeFor(s.slug, s.skill)
    local index = stepIdx or (s.step or 1)
    local seg = steps and steps[index]
    if not seg then return end
    local XP = ns.ProfExecution
    if seg.navigationOnly or seg.checkpoint or seg[3] == 0
        or XP and (XP.IsConversion(seg) or XP.IsSpecializationQuest(seg)) then return end
    local progress = XP and XP.Progress and XP.Progress(s.slug, seg.segmentID or index)
    local spellID = seg[3]
    local rec = stepRecipe(seg, recMap(s.slug)[spellID])
    local learned = IsLearned(spellID)
    local E = ns.ProfEconomy
    if not learned and E and E.LearningSource and E.LearningSource(rec) == "trainer" then playCue("nol") end
    local learningWarning=PF.LearningWarning(s.slug, progress)
    if learningWarning then craftNotify(learningWarning) return end
    if not learned then craftNotify(L["该配方还未学会，先找训练师学习"]) return end
    local mats = recMats(rec)
    if mats then
        for _, m in ipairs(mats) do
            if (Have(m[1]) or 0) < (m[2] or 1) then
                local sup = PF.SupplementNeeds(s.slug)
                if sup then
                    craftNotify(format(L["本步材料不足：缺 %d 种共 %d 件，先按购物清单补齐"], sup.kinds, sup.qty))
                else
                    craftNotify(L["材料不足，先按购物清单备齐再制造"])
                end
                return
            end
        end
    end
    local count = math.max(1, math.ceil(craftsLeft(seg, s.skill, rec, s.slug, index ~= s.step)))
    if XP and XP.SafeCraftCount then
        count=XP.SafeCraftCount(s.slug,seg.segmentID or index,count)
        if count<=0 then craftNotify(L["本步备用不足，或材料需留给后续步骤；请检查采购清单或续算。"]);return end
    end
    local name = SpellName(spellID)
    if not name then craftNotify(L["配方数据未就绪，稍后再试"]) return end
    jumpEvtInit()
    local opened, skillLine = openProfPanel(seg.profession or s.slug)
    if opened then
        jumpPending = { spellID = spellID, count = count, name = name, skillLine = skillLine }
        craftNotify(format(L["正在打开专业面板并定位 %s（预填数量 %d）…"], name, count))
        jumpApply()
    else
        craftNotify(L["无法自动打开专业面板，请手动打开后重试"])
    end
end

local importTries = 0
local function DoImport(slug, profName)
    if not (LV[slug] and LV[slug].steps) then return end
    local s0 = st()
    local tmp
    if s0 and s0.slug == slug then
        tmp = s0
    else
        local cur = skillOf(slug) or 0
        tmp = { slug = slug, skill = cur, step = derivedStep(slug, cur) or 1 }
    end
    local list = shopList(tmp)
    local items, missing, inventoryUnknown = {}, 0, false
    for _, e in ipairs(list) do
        local auction=slug=="poisons" or e.source=="ah" or e.source=="auction" or e.source=="mixed"
        if auction and e.haveKnown==false then inventoryUnknown=true
        elseif auction then
            local nm, got = DG.ItemName(e.id)
            if not got then
                missing = missing + 1
                DG.RequestItem(e.id)
            else
                local lack = e.planPurchases and not e.purchaseUnknown and (e.ahCount or 0) or math.max(0,e.need-e.have)
                if e.purchaseUnknown then lack=0 end
                if not e.planPurchases and e.source=="mixed" then lack=math.min(lack,e.ahCount or 0) end
                if lack > 0 then
                    items[#items + 1] = { name = nm, need = lack }
                end
            end
        end
    end
    if missing > 0 and importTries < IMPORT_TRIES then
        importTries = importTries + 1
        C_Timer.After(1, function() DoImport(slug, profName) end)
        return
    end
    importTries = 0
    if inventoryUnknown then craftNotify(L["请打开背包和银行，再查看需要购买的数量。"]) end
    if ns.AuctionBridge and ns.AuctionBridge.DoImport then
        ns.AuctionBridge.DoImport(profName, items)
    end
end
PF.ImportShoppingList=DoImport

local f

local rowsShop = {}
local rowsShopNum = {}
local rowsShopMissPill, rowsShopSoldPill, rowsShopTagPill, rowsShopSrcPill = {}, {}, {}, {}

local function MakeLine(parent, fs, color)
    local t = MakeFS(parent, fs, color, "LEFT")
    t:SetWordWrap(false)
    t:Hide()
    return t
end

local buildSec = 0
local buildSecTotal = 8
local bgGate = 0
local function BuildStep(n)
    if n then
        buildSec = n
        if f and f.barBG and f.zone then
            local frac = n / buildSecTotal
            if frac > 1 then frac = 1 end
            f.zone:ClearAllPoints()
            f.zone:SetPoint("TOPLEFT", f.barBG, "TOPLEFT", 0, 0)
            f.zone:SetWidth(math.max(1, math.floor((W - 20) * frac + 0.5)))
            local ac = Accent()
            f.zone:SetVertexColor(ac[1], ac[2], ac[3], 0.9)
            f.zone:Show()
        end
    end
    if not coroutine.running() then return end
    if not debugprofilestop then return end
    local now = debugprofilestop()
    if now - bgGate >= 3 then
        bgGate = now
        coroutine.yield()
    end
end

local function BuildBody()
    if f then return end
    buildSec = 0
    bgGate = 0

    f = CreateFrame("Frame", "DFProfFollowHUD", UIParent, BackdropTemplateMixin and "BackdropTemplate" or nil)
    f:SetSize(W, 10)
    f:SetFrameStrata("FULLSCREEN_DIALOG")
    f:SetClampedToScreen(true)
    f:SetMovable(true)
    f:EnableMouse(true)
    f:RegisterForDrag("LeftButton")
    f:SetScript("OnHide", function() cueState = {} end)
    f:SetScript("OnDragStart", function(self) self:StartMoving() end)
    f:SetScript("OnDragStop", function(self)
        self:StopMovingOrSizing()
        local pt, _, _, x, y = self:GetPoint(1)
        dbProf().followPos = { pt, "UIParent", x, y }
    end)
    f:SetScript("OnMouseWheel", function(_, delta)
        local s = st()
        if not (s and s.slug) then return end
        local _, steps = routeFor(s.slug, s.skill)
        if not steps then return end
        PF.view = math.max(-(s.step - 1), math.min(#steps - s.step + 1, (PF.view or 0) - delta))
        PF.Paint()
    end)
    f:SetScript("OnEvent", function()
        if f:IsShown() and not trackingPaused() then
            C_Timer.After(0, function()
                if trackingPaused() then return end
                PF.Sync()
                PF.Paint()
            end)
        end
    end)
    f:RegisterEvent("BAG_UPDATE_DELAYED")
    f:RegisterEvent("CHAT_MSG_SKILL")

    f:SetBackdrop({
        bgFile = "Interface\\Buttons\\WHITE8x8",
        edgeFile = "Interface\\Buttons\\WHITE8x8",
        edgeSize = 1,
    })
    local bgCol = { 0, 0, 0, 0.35 }
    if ns.huiTheme == "hui" and ns.hui and ns.hui.layer and ns.hui.layer.L0 then
        local l0 = ns.hui.layer.L0
        bgCol = { l0[1], l0[2], l0[3], 0.95 }
        f:SetBackdropBorderColor(1, 1, 1, 0.10)
    else
        f:SetBackdropBorderColor(0.30, 0.30, 0.30, 1)
    end
    RoundBG(f, 6, bgCol)
    if ns.hui and ns.hui.SkinShadow then
        f:SetHeight(200)
        ns.hui.SkinShadow(f, 16, 0.55, 6)
        f:SetHeight(10)
    end
    f.__round = RoundFrame(f, 6, { 1, 1, 1, 0.25 })
    if f.__round then f:SetBackdropBorderColor(0, 0, 0, 0) end
    BuildStep(1)

    f.icon = f:CreateTexture(nil, "ARTWORK")
    f.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
    if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(f.icon) end
    f.icon:SetSize(24, 24)
    f.icon:SetPoint("TOPLEFT", f, "TOPLEFT", 10, -10)

    f.title = MakeFS(f, 16, C_TEXT, "LEFT")
    f.title:SetWordWrap(false)
    f.title:SetPoint("TOPLEFT", f, "TOPLEFT", 42, -14)

    f.capWarn = MakeFS(f, 12, { 0.95, 0.32, 0.32 }, "LEFT")
    f.capWarn:SetWordWrap(false)
    f.capWarn:SetPoint("LEFT", f.title, "RIGHT", 8, 0)
    f.capWarn:Hide()

    f.skill = MakeFS(f, 16, C_TEXT, "LEFT")
    f.skill:SetPoint("TOPLEFT", f, "TOPLEFT", 10, -42)

    f.noLearn = CreateFrame("Frame", nil, f, BackdropTemplateMixin and "BackdropTemplate" or nil)
    f.noLearn:SetPoint("TOPLEFT", f, "TOPLEFT", 10, -40)
    f.noLearn:SetHeight(22)
    f.noLearn:SetBackdrop({ bgFile = "Interface\\ChatFrame\\ChatFrameBackground" })
    RoundBG(f.noLearn, 5, { 0.42, 0.09, 0.09, 0.92 })
    f.noLearn:SetBackdropBorderColor(0.93, 0.32, 0.32, 1)
    f.noLearn.__round = RoundFrame(f.noLearn, 5, { 0.93, 0.32, 0.32, 1 })
    if f.noLearn.__round then f.noLearn:SetBackdropBorderColor(0, 0, 0, 0) end
    f.noLearnTxt = MakeFS(f.noLearn, 12, { 1, 0.86, 0.86 }, "CENTER")
    f.noLearnTxt:SetWordWrap(false)
    f.noLearnTxt:SetPoint("CENTER", f.noLearn, "CENTER", 0, 0)
    f.noLearnTxt:SetText(L["未学习该专业"])
    do
        local cw = 72
        local PDm = ns.ProfModule
        if PDm and PDm.TextW then
            local okw, wv = pcall(PDm.TextW, L["未学习该专业"], 12)
            if okw and type(wv) == "number" then cw = math.ceil(wv) end
        end
        f.noLearn:SetWidth(cw + 20)
    end
    f.noLearn:Hide()

    f.rankHint = CreateFrame("Frame", nil, f)
    f.rankHint:SetPoint("TOPLEFT", f, "TOPLEFT", 8, -39)
    f.rankHint:SetSize(196, 24)
    f.rankHint:EnableMouse(true)
    f.rankHint:SetScript("OnEnter", function(self)
        if self.statusTitle and GameTooltip then
            GameTooltip:SetOwner(self, "ANCHOR_TOP")
            GameTooltip:ClearLines()
            GameTooltip:AddLine(self.statusTitle, 1, 0.82, 0, true)
            GameTooltip:AddLine(self.statusDetail, 1, 1, 1, true)
            GameTooltip:Show()
            return
        end
        local ranks = ns.ProfRanks
        if not (ranks and GameTooltip and self.tasks and #self.tasks > 0) then return end
        GameTooltip:SetOwner(self, "ANCHOR_TOP")
        GameTooltip:ClearLines()
        GameTooltip:AddLine(L["专业晋级"], 1, 0.82, 0, true)
        for _, step in ipairs(self.tasks) do
            GameTooltip:AddLine(ranks.Title(step), 0.95, 0.78, 0.35, true)
            for _, text in ipairs(ranks.Lines(step)) do GameTooltip:AddLine(text, 1, 1, 1, true) end
        end
        GameTooltip:Show()
    end)
    f.rankHint:SetScript("OnLeave", function() if GameTooltip then GameTooltip:Hide() end end)
    f.rankHint:Hide()

    f.seg = MakeFS(f, 16, C_GREY, "RIGHT")
    f.seg:SetPoint("TOPRIGHT", f, "TOPRIGHT", -10, -42)

    f.barBG = f:CreateTexture(nil, "BACKGROUND", nil, 2)
    f.barBG:SetColorTexture(1, 1, 1, 0.12)
    f.barBG:SetPoint("TOPLEFT", f, "TOPLEFT", 10, -66)
    f.barBG:SetSize(W - 20, 5)

    f.zone = f:CreateTexture(nil, "OVERLAY")
    f.zone:SetColorTexture(1, 1, 1, 1)
    f.zone:SetPoint("TOPLEFT", f, "TOPLEFT", 10, -66)
    f.zone:SetSize(1, 5)

    f.bar = f:CreateTexture(nil, "OVERLAY")
    f.bar:SetColorTexture(1, 1, 1, 1)
    f.bar:SetPoint("TOPLEFT", f, "TOPLEFT", 10, -66)
    f.bar:SetSize(1, 5)
    f:SetHeight(90)
    f:Show()
    BuildStep(2)

    local function CreateCard()
        local card = CreateFrame("Frame", nil, f, BackdropTemplateMixin and "BackdropTemplate" or nil)
        card:SetBackdrop({
            bgFile = "Interface\\Buttons\\WHITE8x8",
            edgeFile = "Interface\\Buttons\\WHITE8x8",
            edgeSize = 1,
        })
        local cardCol = { 1, 1, 1, 0.06 }
        if ns.huiTheme == "hui" and ns.hui and ns.hui.layer and ns.hui.layer.L1 then
            local l1 = ns.hui.layer.L1
            cardCol = { l1[1], l1[2], l1[3], 0.95 }
        end
        RoundBG(card, 6, cardCol)
        card:SetBackdropBorderColor(0, 0, 0, 0)
        card.__round = RoundFrame(card, 6, { 0, 1, 0.4, 0.9 })

        card:EnableMouse(true)
        card:SetScript("OnEnter", function(self)
            if self.__guide and GameTooltip then
                GameTooltip:SetOwner(self,"ANCHOR_TOP")
                GameTooltip:ClearLines()
                GameTooltip:AddLine(self.__guide.name,1,0.82,0,true)
                for _,line in ipairs(self.__guide.lines or {}) do GameTooltip:AddLine(line,1,1,1,true) end
                GameTooltip:Show()
                return
            end
            if not self.__it then return end
            local PD = ns.ProfModule
            local extra
            if PD and PD.PriceTipLines then
                extra = PD.PriceTipLines(self.__it[1], self.__mats)
            end
            DG.ShowItemTip(self, self.__it, extra)
            if self.__spell and DG.TipAppendLines then
                DG.TipAppendLines({ { L["点击卡片：打开专业面板、定位本步配方并填好制作次数"], 0.62, 0.86, 1 } })
            end
        end)
        card:SetScript("OnLeave", function() GameTooltip:Hide() end)
        card:SetScript("OnMouseUp", function(self, button)
            if button == "LeftButton" then
                jumpPending = nil
                if self.__spell then
                    jumpCraft(self.__step)
                    ns.PlaySound(1)
                end
            end
        end)

        card.icon = card:CreateTexture(nil, "ARTWORK")
        card.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
        if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(card.icon) end
        card.icon:SetSize(26, 26)
        card.icon:SetPoint("TOPLEFT", card, "TOPLEFT", 8, -8)

        card.name = MakeFS(card, 16, C_TEXT, "LEFT")
        card.name:SetWordWrap(false)
        card.name:SetPoint("TOPLEFT", card, "TOPLEFT", 42, -9)

        card.range = MakeFS(card, 14, C_GREY, "LEFT")
        card.range:SetWordWrap(false)
        card.range:SetPoint("TOPLEFT", card, "TOPLEFT", 42, -12)

        card.crafts = MakeFS(card, 14, C_GREY, "LEFT")
        card.crafts:SetWordWrap(false)
        card.crafts:SetPoint("TOPLEFT", card, "TOPLEFT", 42, -33)

        card.chipLearn = DG.MakeBadge(card, DG.Q_BADGE_SHARE_BG)
        card.chipSrc = DG.MakeBadge(card,
            (ns.ProfModule and ns.ProfModule.CARD_COL and ns.ProfModule.CARD_COL.trainer) or { 0.29, 0.33, 0.40 })
        for _, ch in ipairs({ card.chipLearn, card.chipSrc }) do
            ch.lab:SetFont(ns.FONT, DG.Q_BADGE_FS,
                (ns.hui and ns.hui.FontFlags and ns.hui.FontFlags("OUTLINE")) or "OUTLINE")
            ch:Hide()
        end

        card.matHead = MakeFS(card, 14, C_GREY, "LEFT")
        card.matHead:SetPoint("TOPLEFT", card, "TOPLEFT", 8, -56)
        BuildStep(3)

        card.__rowsMat, card.__rowsIcon, card.__rowsBadge = {}, {}, {}
        local rowsMat, rowsMatIcon, rowsMatBadge = card.__rowsMat, card.__rowsIcon, card.__rowsBadge
        for i = 1, MAT_MAX + 1 do
            BuildStep()
            rowsMat[i] = MakeLine(card, 14, C_TEXT)
            local ic = card:CreateTexture(nil, "ARTWORK")
            ic:SetTexCoord(0.07, 0.93, 0.07, 0.93)
            if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(ic) end
            ic:SetSize(22, 22)
            ic:Hide()
            rowsMatIcon[i] = ic
            local bd = MakeFS(card, 14, C_GOLD, "RIGHT")
            bd:SetFont(ns.FONT or "Fonts\\FRIZQT__.TTF", 14, "THICKOUTLINE")
            bd:SetShadowColor(0, 0, 0, 1)
            bd:SetShadowOffset(1, -1)
            bd:SetWordWrap(false)
            bd:Hide()
            rowsMatBadge[i] = bd
        end
        return card
    end
    f.card = CreateCard()
    f.card2 = CreateCard()
    f.card2:Hide()
    BuildStep(4)

    f.shop = CreateFrame("Frame", nil, f, BackdropTemplateMixin and "BackdropTemplate" or nil)
    f.shop:SetBackdrop({
        bgFile = "Interface\\Buttons\\WHITE8x8",
        edgeFile = "Interface\\Buttons\\WHITE8x8",
        edgeSize = 1,
    })
    local shopCol = { 1, 1, 1, 0.04 }
    if ns.huiTheme == "hui" and ns.hui and ns.hui.layer and ns.hui.layer.L1 then
        local l1s = ns.hui.layer.L1
        shopCol = { l1s[1], l1s[2], l1s[3], 0.95 }
    end
    RoundBG(f.shop, 6, shopCol)
    f.shop:SetBackdropBorderColor(1, 1, 1, 0.14)
    f.shop.__round = RoundFrame(f.shop, 6, { 1, 1, 1, 0.14 })
    if f.shop.__round then f.shop:SetBackdropBorderColor(0, 0, 0, 0) end
    local labW = 70
    do
        local PDw = ns.ProfModule
        if PDw and PDw.TextW then
            local okw, wv = pcall(PDw.TextW, L["仅显示缺失"], 14)
            if okw and type(wv) == "number" then labW = math.ceil(wv) end
        end
    end
    f.shop.missTog = CreateFrame("CheckButton", nil, f.shop)
    f.shop.missTog:SetSize(36, 20)
    f.shop.missTog:EnableMouse(true)
    if ns.hui and ns.hui.ReskinToggle then ns.hui.ReskinToggle(f.shop.missTog) end
    f.shop.missTog:SetPoint("TOPRIGHT", f.shop, "TOPRIGHT", -6, -4)
    f.shop.missLab = MakeFS(f.shop, 14, C_TEXT, "RIGHT")
    f.shop.missLab:SetWordWrap(false)
    f.shop.missLab:SetPoint("RIGHT", f.shop.missTog, "LEFT", -4, 0)
    f.shop.missLab:SetText(L["仅显示缺失"])
    f.shop.missTog:SetScript("OnClick", function(self)
        dbProf().shopOnlyMiss = not onlyMissView()
        self:SetChecked(onlyMissView())
        PF.Paint()
        ns.PlaySound(1)
    end)
    f.shop.missTog:SetChecked(onlyMissView())
    TipOn(f.shop.missTog, L["仅显示缺失"],
          L["开启：购物清单只列出还缺的材料，已备齐的自动隐藏。"])
    f.shop.empty = MakeFS(f.shop, 14, C_GREY, "LEFT")
    f.shop.empty:SetPoint("TOPLEFT", f.shop, "TOPLEFT", 8, -30)
    f.shop.empty:Hide()
    f.shop:EnableMouse(true)
    f.shop:EnableMouseWheel(true)
    f.shop:SetScript("OnMouseWheel", function(_, delta)
        PF.shopScroll = math.max(0, (PF.shopScroll or 0) - delta)
        PF.Paint()
    end)
    f.shop.sbarTrack = f.shop:CreateTexture(nil, "OVERLAY")
    f.shop.sbarTrack:SetColorTexture(1, 1, 1, 0.10)
    f.shop.sbarTrack:SetPoint("TOPRIGHT", f.shop, "TOPRIGHT", -4, -28)
    f.shop.sbarTrack:Hide()
    f.shop.sbarThumb = f.shop:CreateTexture(nil, "OVERLAY")
    f.shop.sbarThumb:SetColorTexture(1, 1, 1, 0.35)
    f.shop.sbarThumb:Hide()
    BuildStep(5)
    for i = 1, SHOP_MAX + 1 do
        BuildStep()
        rowsShop[i] = MakeLine(f.shop, 14, C_TEXT)
        rowsShopNum[i] = MakeLine(f.shop, 14, C_GOLD)
        local function MakePill(color)
            local p = CreateFrame("Frame", nil, f.shop, "BackdropTemplate")
            local solid = ns.hui and ns.hui.BuildSolidFill and true
            if solid then
                p:SetHeight((ns.hui.ChipH and ns.hui.ChipH(14)) or 13.7)
                p.__chipFill = ns.hui.BuildSolidFill(p, ns.hui.CHIP_S_R, ns.hui.layer.L2)
                p.__border = ns.hui.BuildRoundBorder(p, ns.hui.CHIP_S_R, { 1, 1, 1, 1 }, nil, "BORDER", "both", 1)
                p.fs = MakeFS(p, ns.hui.CHIP_S_FS, C_WHITE, "CENTER")
            else
                p:SetHeight(17)
                local cols
                if ns.hui and ns.hui.BuildCapsule then
                    cols = ns.hui.BuildCapsule(p, 8, ns.hui.layer.L2)
                else
                    local tx = p:CreateTexture(nil, "BACKGROUND")
                    tx:SetAllPoints()
                    tx:SetColorTexture(1, 1, 1, 1)
                    cols = { tx }
                end
                p.__cols = cols
                p.fs = MakeFS(p, 14, color, "CENTER")
            end
            if solid then
                p.fs:SetPoint("CENTER", p, "CENTER", 0, (ns.hui.ChipLabelDY and ns.hui.ChipLabelDY(ns.hui.CHIP_S_FS)) or 0.5)
            else
                p.fs:SetAllPoints(p)
            end
            p.fs:SetWordWrap(false)
            p:Hide()
            return p
        end
        rowsShopMissPill[i] = MakePill(C_TEXT)
        rowsShopSoldPill[i] = MakePill(C_TEXT)
        rowsShopTagPill[i] = MakePill(C_DIM)
        rowsShopSrcPill[i] = MakePill(C_HEAD)
        local src0 = rowsShopSrcPill[i]
        src0:EnableMouse(true)
        src0:SetScript("OnEnter", function(self)
            local r = self.__row
            if not r or not r.srcText then return end
            GameTooltip:SetOwner(self, "ANCHOR_TOP")
            GameTooltip:ClearLines()
            if r.srcKind == 1 then
                GameTooltip:AddLine(r.srcFull or r.srcText, 1, 0.82, 0, true)
                local loc = r.npcID and ns.ProfVendors and ns.ProfVendors[r.npcID]
                GameTooltip:AddLine(loc and L["点击在地图上标出该商人"] or L["该商人的位置暂未收录"],
                                    0.75, 0.75, 0.75, true)
            else
                GameTooltip:AddLine(r.nm, 1, 0.82, 0, true)
            end
            local detail = PF.ShoppingSourceDetail(r.src)
            if detail then GameTooltip:AddLine(detail, 1, 1, 1, true) end
            GameTooltip:Show()
        end)
        src0:SetScript("OnLeave", function() GameTooltip:Hide() end)
        if src0.SetHitRectInsets then src0:SetHitRectInsets(-2, -3, -3, -2) end
        src0:SetScript("OnMouseUp", function(self, btn)
            if btn ~= "LeftButton" then return end
            local r = self.__row
            if not r or r.srcKind ~= 1 or not r.npcID then return end
            local PDm = ns.ProfModule
            local loc = ns.ProfVendors and ns.ProfVendors[r.npcID]
            if PDm and PDm.MarkVendorLoc then PDm.MarkVendorLoc(loc) end
            if not loc then
                craftNotify(format(L["%s 的位置暂未收录"], r.srcFull or r.srcText or "?"))
            end
            ns.PlaySound(1)
        end)
    end
    BuildStep(6)

    f.shopImp = NewButton(f.shop, L["一键导入"], 66, 20, 13)
    f.shopImp:SetScript("OnClick", function()
        local s0 = st()
        if not (s0 and s0.slug) then return end
        local nm = (D.pro and D.pro[s0.slug] and D.pro[s0.slug].name) or s0.slug
        DoImport(s0.slug, nm)
        ns.PlaySound(1)
    end)
    f.shopImp:SetPoint("RIGHT", f.shop.missTog, "LEFT", -(labW + 10), 0)
    TipOn(f.shopImp, L["一键导入到拍卖行"],
          L["将拍卖行采购的缺口导入 Auctionator；NPC 货物和自制材料不导入，同名清单将被覆盖。"])

    f.shopStep = NewButton(f.shop, L["分步"], 48, 20, 13)
    f.shopStep:SetScript("OnClick", function()
        dbProf().shopStepView = not (dbProf().shopStepView and true or false)
        PF.shopScroll = 0
        PF.Paint()
        ns.PlaySound(1)
    end)
    f.shopStep:SetPoint("RIGHT", f.shopImp, "LEFT", -10, 0)
    TipOn(f.shopStep, L["分步 / 汇总"],
          L["汇总：所有步骤的材料合并成一行。分步：按首次需要的步骤分组列出，便于分段采购。"])

    f.finish = MakeFS(f, 14, C_OK, "LEFT")
    f.finish:SetWordWrap(false)
    f.scanStatus = MakeFS(f, 11, C_DIM, "LEFT")
    f.scanStatus:SetWordWrap(true)

    local nowW = 68
    do
        local PDm = ns.ProfModule
        if PDm and PDm.TextW then
            local ok, wv = pcall(PDm.TextW, L["回到当前"], 13)
            if ok and type(wv) == "number" then nowW = math.max(nowW, math.ceil(wv) + 14) end
            ok, wv = pcall(PDm.TextW, L["校正产出"], 13)
            if ok and type(wv) == "number" then nowW = math.max(nowW, math.ceil(wv) + 14) end
        end
    end
    f.cardBtnW = nowW

    f.nowBtn = NewButton(f.card, L["回到当前"], nowW, 20, 13)
    f.nowBtn:SetFrameLevel((f.card:GetFrameLevel() or 0) + 6)
    f.nowBtn:Hide()
    f.nowBtn:SetScript("OnClick", function() PF.view = 0 PF.Paint() ns.PlaySound(1) end)

    f.verifyBtn = NewButton(f.card, L["校正产出"], nowW, 20, 13)
    f.verifyBtn:SetFrameLevel((f.card:GetFrameLevel() or 0) + 6)
    f.verifyBtn:Hide()
    f.verifyBtn:SetScript("OnClick", function() verifyOutputDialog() ns.PlaySound(1) end)

    local labels = { L["购物清单"], L["上一步"], L["下一步"] }
    local onclick = { function() PF.showShop = not PF.showShop PF.Paint() end, PF.Prev, PF.Skip }
    f.btns = {}
    for i = 1, 3 do
        local bt = NewButton(f, labels[i], BTN_W[i], 22, 14)
        bt:SetScript("OnClick", function() onclick[i]() ns.PlaySound(1) end)
        f.btns[i] = bt
    end

    f.xBtn = NewButton(f, "×", 24, 22, 14)
    f.xBtn:SetPoint("TOPRIGHT", f, "TOPRIGHT", -8, -8)
    f.xBtn:SetScript("OnClick", function()
        local s = st()
        if s then s.hidden = true end
        f:Hide()
        if PF.RefreshMainUI then PF.RefreshMainUI() end
    end)
    TipOn(f.xBtn, L["隐藏 HUD"], L["关闭 HUD 只隐藏窗口，不会结束追踪。"] .. "\n"
        .. L["不再升级时，请在升级页点击追踪进度按钮结束追踪。"])

    f.muteBtn = NewButton(f, "", 24, 22, 14)
    f.muteBtn:SetPoint("TOPRIGHT", f.xBtn, "TOPLEFT", -4, 0)
    f.muteBtn.tex = f.muteBtn:CreateTexture(nil, "ARTWORK")
    f.muteBtn.tex:SetSize(12, 12)
    f.muteBtn.tex:SetPoint("CENTER", f.muteBtn, "CENTER", 0, 0)
    f.muteBtn.tex:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\Prof\\prof_mute.tga")
    f.muteBtn:SetScript("OnClick", function()
        local p = dbProf()
        p.muteCue = (not p.muteCue) and true or nil
        PF.PaintMute()
        cueMsg(p.muteCue and L["已静音：不再播放升级语音"] or L["已恢复语音提示"])
        if not p.muteCue then playCue("on") end
        ns.PlaySound(1)
    end)
    f.muteBtn:SetScript("OnEnter", function(self)
        self.__hover = true
        PF.PaintMute(self)
        GameTooltip:SetOwner(self, "ANCHOR_TOP")
        GameTooltip:SetText(cueMuted() and L["语音提示：已静音（点击恢复）"] or L["语音提示：开启（点击静音）"], 1, 1, 1)
        GameTooltip:Show()
    end)
    f.muteBtn:SetScript("OnLeave", function(self)
        self.__hover = false
        PF.PaintMute(self)
        GameTooltip:Hide()
    end)
    PF.PaintMute(f.muteBtn)
    BuildStep(7)

    local pos = dbProf().followPos
    f:ClearAllPoints()
    if pos and pos[1] then
        f:SetPoint(pos[1], pos[2] or UIParent, pos[3], pos[4])
    else
        f:SetPoint("CENTER", UIParent, "CENTER", 340, 60)
    end

    if C_Timer.NewTicker then
        C_Timer.NewTicker(1, function()
            if f and f:IsShown() and PF.Sync() then PF.Paint() end
        end)
    end

    BuildStep(8)
    PF.f = f
end

function PF.Build()
    if f or PF.building then return end
    PF.building = true
    local co = coroutine.create(BuildBody)
    local function pump()
        local ok, err = coroutine.resume(co)
        if not ok then
            PF.building = false
            PF.onBuilt = nil
            if f then
                f:Hide()
                f = nil
            end
            PF.f = nil
            return
        end
        if coroutine.status(co) ~= "dead" then
            C_Timer.After(0, pump)
        else
            PF.building = false
            if PF.onBuilt then
                local cb = PF.onBuilt
                PF.onBuilt = nil
                cb()
            end
        end
    end
    pump()
end

local sweep = 0
local function sweepPaint(pending)
    if pending and sweep < SWEEP_MAX then
        sweep = sweep + 1
        C_Timer.After(2, function() if f and f:IsShown() then PF.Paint() end end)
    elseif not pending then
        sweep = 0
    end
end

local function paintMats(card, seg, rm, sold, w, remaining, resR)
    local rowsMat, rowsMatIcon, rowsMatBadge = card.__rowsMat, card.__rowsIcon, card.__rowsBadge
    local rec = stepRecipe(seg, rm[seg[3]])
    local mats = recMats(rec)
    local n = 0
    local pending = false
    local canCraft
    if mats and #mats > 0 then
        for _, m in ipairs(mats) do
            local per = (m[2] or 1)
            if per > 0 then
                local c = math.floor(Have(m[1]) / per)
                canCraft = (canCraft == nil) and c or math.min(canCraft, c)
            end
        end
        card.matHead:Hide()
        for i, m in ipairs(mats) do
            if i > MAT_MAX then break end
            local have = Have(m[1])
            local per = (m[2] or 1)
            local need = per * math.max(0, remaining or 0)
            local ok = have >= need
            local nm, got = DG.ItemName(m[1])
            if not got then DG.RequestItem(m[1]) pending = true end
            local line = rowsMat[i]
            line:SetTextColor(Unpack(ok and C_OK or C_BAD))
            local txt = format("%s %d/%d", nm, have, need)
            if sold[m[1]] then txt = txt .. " · " .. L[(st() and st().slug=="poisons") and "商人直卖" or "NPC也有出售"] end
            line:SetText(txt)
            line:ClearAllPoints()
            line:SetPoint("TOPLEFT", card, "TOPLEFT", 36, -(61 + (i - 1) * 26))
            line:SetWidth(math.max(60, w - 28 - (resR or 0)))
            line:Show()
            local ic = rowsMatIcon[i]
            ic:SetTexture(DG.ItemIcon(m[1]) or Host.FALLBACK_ICON)
            if ns.hui and ns.hui.SetIconRing then
                local mq = DG.QualOf and DG.QualOf(m[1]) or nil
                ns.hui.SetIconRing(ic, mq and { ns.hui.QColor(mq) } or nil)
            end
            ic:ClearAllPoints()
            ic:SetPoint("TOPLEFT", card, "TOPLEFT", 8, -(56 + (i - 1) * 26))
            ic:Show()
            local bd = rowsMatBadge[i]
            bd:ClearAllPoints()
            bd:SetPoint("BOTTOMRIGHT", ic, "BOTTOMRIGHT", 2, 0)
            bd:SetText(per)
            bd:Show()
            n = i
        end
        if #mats > MAT_MAX then
            local more = rowsMat[MAT_MAX + 1]
            more:SetTextColor(Unpack(C_DIM))
            more:SetText(format(L["…共 %d 种材料，进购物清单看合计"], #mats))
            more:ClearAllPoints()
            more:SetPoint("TOPLEFT", card, "TOPLEFT", 8, -(56 + n * 26))
            more:SetWidth(math.max(60, w - (resR or 0)))
            more:Show()
            rowsMatIcon[MAT_MAX + 1]:Hide()
            if ns.hui and ns.hui.SetIconRing then ns.hui.SetIconRing(rowsMatIcon[MAT_MAX + 1], nil) end
            rowsMatBadge[MAT_MAX + 1]:Hide()
            n = n + 1
        else
            rowsMat[MAT_MAX + 1]:Hide()
            rowsMatIcon[MAT_MAX + 1]:Hide()
            if ns.hui and ns.hui.SetIconRing then ns.hui.SetIconRing(rowsMatIcon[MAT_MAX + 1], nil) end
            rowsMatBadge[MAT_MAX + 1]:Hide()
        end
    elseif rec then
        card.matHead:SetText(L["无材料"])
        card.matHead:Show()
    else
        card.matHead:SetText(L["材料未收录"])
        card.matHead:Show()
    end
    for i = n + 1, MAT_MAX do
        rowsMat[i]:Hide()
        rowsMatIcon[i]:Hide()
        if ns.hui and ns.hui.SetIconRing then ns.hui.SetIconRing(rowsMatIcon[i], nil) end
        rowsMatBadge[i]:Hide()
    end
    if n < MAT_MAX + 1 then
        rowsMatIcon[MAT_MAX + 1]:Hide()
        if ns.hui and ns.hui.SetIconRing then ns.hui.SetIconRing(rowsMatIcon[MAT_MAX + 1], nil) end
        rowsMatBadge[MAT_MAX + 1]:Hide()
    end
    return n, pending, canCraft
end

local function paintTrackingStatus(title, detail)
    f.skill:SetText(title)
    f.skill:SetWidth(W_BASE - 20)
    f.skill:SetTextColor(C_TEXT[1], C_TEXT[2], C_TEXT[3])
    f.skill:SetWordWrap(false)
    f.skill:Show()
    f.noLearn:Hide()
    f.seg:Hide()
    f.capWarn:Hide()
    f.rankHint.tasks = nil
    f.rankHint.statusTitle, f.rankHint.statusDetail = title, detail
    f.rankHint:SetWidth(W_BASE - 16)
    f.rankHint:Show()
end

function PF.Paint()
    if not (f and f:IsShown()) then return end
    f.scanStatus:Hide()
    if trackingPaused() then
        PF.combatPaused=true
        paintTrackingStatus(L["战斗中暂停追踪"], L["战斗中暂停追踪，脱战后自动恢复。"])
        return
    end
    local state=st()
    if state and state.autoTrackSuspended=="inactive" then
        paintTrackingStatus(L["追踪已自动结束"], L["48 小时无制作，追踪已自动结束。"])
        return
    end
    W = W_BASE
    f:SetWidth(W)
    f.barBG:SetWidth(W - 20)
    local s = st()
    if not (s and s.slug) then f:Hide() return end
    local slug = s.slug
    local mode, steps = routeFor(slug, s.skill)
    if not steps then f:Hide() return end
    local p = D.pro and D.pro[slug]
    local accent = Accent()
    local name = (p and p.name) or slug

    f.icon:SetTexture(ProfIconTex(p and p.icon))
    f.title:SetText(format(L["%s升级HUD"], name))

    local cur, mx = skillOf(slug)
    local rankTasks = PF.RankTasks(slug, routeTarget(slug), steps, s.step)
    updateCues(slug, rankTasks)
    f.rankHint.tasks = rankTasks
    f.rankHint.statusTitle, f.rankHint.statusDetail = nil, nil
    f.rankHint:SetShown(#rankTasks > 0)
    local atCap = false
    for _, task in ipairs(rankTasks) do
        local state = task.state or {}
        if task.due and state.known and state.maxSkill and state.maxSkill > 0
            and state.skill and state.skill >= state.maxSkill then atCap = true; break end
    end
    if cur then
        local _, stp = routeFor(s.slug, s.skill)
        local seg = stp and stp[s.step or 1]
        local toPts = seg and tonumber(seg[2]) or nil
        if toPts and toPts > cur then
            f.skill:SetText(format(L["技能 %d（%d）/ %d"], cur, toPts, mx or 300))
        else
            f.skill:SetText(format(L["技能 %d / %d"], cur, mx or 300))
        end
        f.skill:Show()
        if f.noLearn then f.noLearn:Hide() end
    else
        f.skill:SetText("")
        f.skill:Hide()
        if f.noLearn then f.noLearn:Show() end
    end
    if atCap then
        f.skill:SetTextColor(0.95, 0.32, 0.32)
    else
        f.skill:SetTextColor(C_TEXT[1], C_TEXT[2], C_TEXT[3])
    end
    if f.capWarn then
        if atCap then
            f.capWarn:SetText(L["找训练师提高技能上限"])
            f.capWarn:Show()
        else
            f.capWarn:Hide()
        end
    end
    if f.__round then
        local br, bgc, bb, ba = 1, 1, 1, 0.25
        if atCap then br, bgc, bb, ba = 0.93, 0.32, 0.32, 0.95 end
        for _, tex in ipairs(f.__round) do tex:SetVertexColor(br, bgc, bb, ba) end
    elseif atCap then
        f:SetBackdropBorderColor(0.93, 0.32, 0.32, 0.95)
    elseif ns.huiTheme == "hui" then
        f:SetBackdropBorderColor(1, 1, 1, 0.10)
    else
        f:SetBackdropBorderColor(0.30, 0.30, 0.30, 1)
    end
    local ratio = cur and math.min(1, cur / 300) or 0
    f.bar:SetWidth(math.max(2, math.floor((W - 20) * ratio + 0.5)))
    f.bar:SetVertexColor(accent[1], accent[2], accent[3], 0.95)

    local finished = (s.step or 1) > #steps
    local vi = math.max(1, math.min(#steps, (s.step or 1) + (PF.view or 0)))
    f.seg:SetText(((mode == "auto") and L["自动计算"] or mode == "gather" and L["采集路线"] or L["固定路线"]) .. " · "
                  .. format(L["段落 %d / %d"], vi, #steps))
    f.seg:Show()
    local segmentWidth = f.seg.GetStringWidth and f.seg:GetStringWidth() or 140
    local skillWidth = math.max(90, W - 28 - segmentWidth)
    f.skill:SetWidth(skillWidth)
    f.skill:SetWordWrap(false)
    f.rankHint:SetWidth(skillWidth + 4)

    local segCur = (not finished) and steps[math.min((s.step or 1), #steps)] or nil
    if segCur then
        local x0 = math.floor((W - 20) * math.min(1, segCur[1] / 300) + 0.5)
        local x1 = math.floor((W - 20) * math.min(1, segCur[2] / 300) + 0.5)
        f.zone:ClearAllPoints()
        f.zone:SetPoint("TOPLEFT", f.barBG, "TOPLEFT", x0, 0)
        f.zone:SetWidth(math.max(1, x1 - x0))
        f.zone:SetVertexColor(C_HEAD[1], C_HEAD[2], C_HEAD[3], 0.9)
        f.zone:Show()
    else
        f.zone:Hide()
    end

    f.finish:SetShown(finished)
    f.card:SetShown(not finished)
    f.card2:Hide()
    local viewing = (PF.view or 0) ~= 0 and not finished
    f.nowBtn:SetShown(viewing)
    local TK = ns.ProfExecution
    local vRun = slug~="poisons" and TK and TK.GetActive and TK.GetActive(slug)
    local vProg = vRun and TK.Progress and TK.Progress(slug, nil, nil, vRun.planID)
    f.verifyBtn:SetText(vProg and vProg.manualConversion and L["确认转换"] or L["校正产出"])
    local verShown = not finished and vProg ~= nil and vProg.outputItem ~= nil and not vProg.finished
    f.verifyBtn:SetShown(verShown)

    local y = -82
    local pending = false

    if not finished then
        local rm = recMap(slug)
        local cands = viewing and {vi} or currentCands(steps, cur or s.skill or 0, s.step or 1, slug, rm, vRun)
        local cards = {f.card, f.card2}
        for painted, ci in ipairs(cands) do
        local seg = steps[ci]
        local sold = soldSet(slug)
        local rec = stepRecipe(seg, rm[seg[3]])
        local card, w = cards[painted], W - 2 * PAD - 16
        local isCur = (ci == s.step)
        card:Show()

        if card.__round then
            for _, tex in ipairs(card.__round) do
                tex:SetVertexColor(accent[1], accent[2], accent[3], isCur and 0.9 or 0.35)
            end
        else
            card:SetBackdropBorderColor(accent[1], accent[2], accent[3], isCur and 0.9 or 0.35)
        end

        local prodItem = recItem(rec)
        if prodItem then
            card.icon:SetTexture(DG.ItemIcon(prodItem))
        else
            card.icon:SetTexture(Host.FALLBACK_ICON)
        end
        if ns.hui and ns.hui.SetIconRing then
            local pq = (prodItem and DG.QualOf) and DG.QualOf(prodItem) or nil
            ns.hui.SetIconRing(card.icon, pq and { ns.hui.QColor(pq) } or nil)
        end
        card.__it = prodItem and { prodItem } or nil
        card.__mats = recMats(rec)
        local PDm = ns.ProfModule
        local nmText = seg.name or SpellName(seg[3])
        local XP = ns.ProfExecution
        local questInfo=PF.SpecializationQuestInfo(seg)
        card.__guide=questInfo or seg.navigationOnly and {name=seg.name,lines={seg.detail or ""}} or nil
        if XP and XP.IsConversion(seg) then nmText = L["精华转换"]
        elseif questInfo then nmText=questInfo.name end
        card.name:SetText(nmText)

        local crafts = seg[4] or 0
        local remaining = crafts
        if seg.segmentID or ci == s.step then
            remaining = math.ceil(craftsLeft(seg, s.skill, rec, slug, ci ~= s.step))
            crafts = remaining
        end
        local nMat, pend, canCraft = paintMats(card, seg, rm, sold, w - 8, remaining,
            viewing and ((f.cardBtnW or 68) + 6) or 0)
        pending = pending or pend

        local src, detail, kind
        if PDm and PDm.LevelSrc then
            src, detail, kind = PDm.LevelSrc(rec, seg.profession or slug, seg.recipe, true)
        end
        local learned = IsLearned(seg[3])
        local learningWarning=isCur and PF.LearningWarning(slug,vProg)
        if learningWarning then card.__guide={name=nmText,lines={learningWarning}} end
        local manual = seg.navigationOnly or seg.checkpoint or XP and (XP.IsConversion(seg) or XP.IsSpecializationQuest(seg))
        card.__step = ci
        card.__spell = not manual and seg[3] ~= 0 and seg[3] or nil
        local srcLabel, srcColor
        local CARD_COL = PDm and PDm.CARD_COL or {}
        if manual then
            srcLabel = seg.navigationOnly and L["参考"] or questInfo and L["任务"]
                or XP and XP.IsConversion(seg) and L["精华转换"] or L["采集"]
            srcColor = CARD_COL.both
        elseif kind == "vendor" then srcLabel, srcColor = L["商人"], CARD_COL.vendor
        elseif kind == "drop" then srcLabel, srcColor = L["掉落"], CARD_COL.drop
        elseif kind == "currency" then srcLabel, srcColor = L["兑换"], CARD_COL.vendor
        elseif kind == "quest" then srcLabel, srcColor = L["任务"], CARD_COL.both
        elseif kind == "trainer" or src == L["向训练师学习"] then srcLabel, srcColor = L["训练师"], CARD_COL.trainer
        else srcLabel, srcColor = L["图纸"], CARD_COL.both end
        local chL, chS = card.chipLearn, card.chipSrc
            chL.lab:SetText(learned and L["已学"] or L["未学"])
            DG.BadgeTint(chL, learned and DG.Q_BADGE_SHARE_BG or DG.Q_BADGE_RACE_BG)
            local w1 = math.max(DG.Q_BADGE_MIN_W, (chL.lab:GetStringWidth() or 18) + DG.Q_BADGE_PAD * 2)
            chL:SetSize(w1, DG.Q_BADGE_H)
            local tagW = w1
            chL:ClearAllPoints()
            if srcLabel then
                chS.lab:SetText(srcLabel)
                chS:EnableMouse(true)
                if manual then TipOn(chS, srcLabel, questInfo and questInfo.summary or seg.detail)
                else TipOn(chS, src or srcLabel, detail) end
                DG.BadgeTint(chS, srcColor or { 0.29, 0.33, 0.40 })
                local w2 = math.max(DG.Q_BADGE_MIN_W, (chS.lab:GetStringWidth() or 18) + DG.Q_BADGE_PAD * 2)
                chS:SetSize(w2, DG.Q_BADGE_H)
                chS:ClearAllPoints()
                chS:SetPoint("TOPRIGHT", card, "TOPRIGHT", -8, -9)
                chS:Show()
                chL:SetPoint("TOPRIGHT", chS, "TOPLEFT", -DG.Q_BADGE_GAP, 0)
                tagW = tagW + DG.Q_BADGE_GAP + w2
            else
                chS:Hide()
                chL:SetPoint("TOPRIGHT", card, "TOPRIGHT", -8, -9)
            end
            chL:Show()

        if manual then chL:Hide();tagW = srcLabel and (chS:GetWidth() or 0) or 0 end
        local rangeText = format(L["%d – %d"], seg[1], seg[2])
        card.range:SetText(rangeText)
            local numCol = format("|cff%02x%02x%02x", math.floor(accent[1] * 255 + 0.5),
                math.floor(accent[2] * 255 + 0.5), math.floor(accent[3] * 255 + 0.5))
            local exactQty = (tonumber(seg[4]) or 0) <= math.max(1, seg[2] - seg[1])
            if exactQty and C_TradeSkillUI and C_TradeSkillUI.GetRecipeInfo then
                local okInfo, ri = pcall(C_TradeSkillUI.GetRecipeInfo, seg[3])
                if okInfo and type(ri) == "table" then
                    local rd = ri.relativeDifficulty
                    if rd == nil then rd = ri.difficulty end
                    if rd ~= nil and rd >= 1 then exactQty = false end
                end
            end
            local needKey = L["还需%s次"]
            if not exactQty then needKey = L["还需约%s次"] end
            local craftText = format(needKey, numCol .. crafts .. "|r")
            if canCraft then
                craftText = craftText .. "/" .. format(L["可制造%s次"], numCol .. canCraft .. "|r")
            end
            if vRun and TK.Progress then
                local pv = TK.Progress(slug, ci, nil, vRun.planID)
                if pv and pv.outputItem then
                    craftText = craftText .. "/" .. format(L["已生产%s"], numCol .. (pv.actualOutputs or 0) .. "|r")
                end
            end
        if questInfo then craftText = questInfo.summary
        elseif seg.navigationOnly then craftText = L["按实际技能推进；不预计采集产出。"]
        elseif seg.checkpoint then craftText = L["不预先计入尚未采到的矿石"] end
        card.crafts:SetText(learningWarning or craftText)
        local craftW = w - 54
        if verShown and painted == 1 then craftW = craftW - (f.cardBtnW or 68) - 2 end
        card.crafts:SetWidth(math.max(60, craftW))

        local rangeW, nameW = 40, 90
        if PDm and PDm.TextW then
            local okW, tw = pcall(PDm.TextW, rangeText, 14)
            if okW and type(tw) == "number" then rangeW = math.ceil(tw) end
            local okW2, tw2 = pcall(PDm.TextW, nmText, 16)
            if okW2 and type(tw2) == "number" then nameW = math.ceil(tw2) end
        end
        local avail = math.max(60, w - 42 - tagW - 10 - rangeW - 10)
        local nameX = math.min(nameW, avail)
        card.name:SetWidth(avail)
        card.range:ClearAllPoints()
        card.range:SetPoint("TOPLEFT", card, "TOPLEFT", 42 + nameX + 10, -12)
        card.range:SetWidth(rangeW + 6)

        local cardH = math.max(nMat * 26 + 60, viewing and 86 or 60)
        card:ClearAllPoints()
        card:SetPoint("TOPLEFT", f, "TOPLEFT", PAD, y)
        card:SetSize(W - 2 * PAD, cardH)
        y = y - cardH - 8
        end
    end

    if PF.showShop and not finished then
        local list = shopList(s)
        local shown = {}
        for _, e in ipairs(list) do
            e.missing = e.haveKnown and math.max(0,e.need-e.have) or nil
            if (not onlyMissView()) or e.missing==nil or e.missing > 0 then shown[#shown + 1] = e end
        end
        f.shop.missTog:SetChecked(onlyMissView())
        local srcByID={}
        for _,entry in ipairs(list) do srcByID[entry.id]=entry end
        local function tw(txt)
            local PDm = ns.ProfModule
            if PDm and PDm.TextW then
                local ok, wv = pcall(PDm.TextW, txt, 14)
                if ok and type(wv) == "number" then return wv end
            end
            return #txt * 5 + 16
        end
        local function clipText(txt, maxW)
            if type(txt) ~= "string" or txt == "" then return txt end
            local PDm = ns.ProfModule
            local CS = ns.hui and ns.hui.CharStep
            if not (PDm and PDm.TextW and CS) then return txt end
            local ok, wv = pcall(PDm.TextW, txt, 14)
            if not ok or type(wv) ~= "number" or wv <= maxW then return txt end
            local out, w = "", 0
            local i, n = 1, #txt
            while i <= n do
                local ch, step, k = CS(txt, i)
                local cw = (k or 1) * 14
                if w + cw > maxW - 14 then break end
                out = out .. ch
                w = w + cw
                i = i + (step or 1)
            end
            if out == "" then return txt end
            return out .. "…"
        end
        local rows = {}
        local nameW, numW, missW, tagW = 0, 0, 0, 0
        local stepView = (dbProf().shopStepView) and true or false
        f.shopStep:SetText(stepView and L["汇总"] or L["分步"])
        local function pushRow(e)
            local nm, got = DG.ItemName(e.id)
            if not got then DG.RequestItem(e.id) pending = true end
            local row = {
                nm = e.formula and (L["图纸"].." · "..nm) or nm,
                have = e.have,
                need = e.need,
                missing = e.missing,
                inventoryUnknown = not e.haveKnown,
                at = e.at or 0,
                src = srcByID and srcByID[e.id] or nil,
            }
            if row.at == math.huge then
                row.gate = true
                row.at = 0
            end
            local w1 = tw(row.nm)
            if w1 > nameW then nameW = w1 end
            local w2 = tw(row.inventoryUnknown and ("? / "..row.need) or format("%d/%d", math.min(row.have, row.need), row.need))
            if w2 > numW then numW = w2 end
            local w3 = tw(row.inventoryUnknown and L["请检查背包"] or row.missing > 0 and format(L["缺%d"], row.missing) or L["已备齐"]) + 10
            if w3 > missW then missW = w3 end
            local w5 = tw(row.gate and L["全程"] or format("%d+", row.at)) + 10
            if w5 > tagW then tagW = w5 end
            if row.src then
                local entry = row.src
                local vendor = (entry.vendorCount or 0) > 0 or purchaseSource(entry) == "vendor"
                local auction = (entry.ahCount or 0) > 0 or purchaseSource(entry) == "ah"
                if vendor and auction then row.srcText, row.srcKind = L["商人"] .. "/" .. L["拍卖行"], 4
                elseif vendor then row.srcText, row.srcKind = L["商人"], 1
                elseif auction then row.srcText, row.srcKind = L["拍卖行"], 2
                elseif entry.selfCraft then row.srcText, row.srcKind = L["自制"], 3 end
                if row.srcKind == 1 then
                    row.npcID = entry.npcID
                    for _, purchase in ipairs(entry.purchases or {}) do
                        if purchase.npcID then row.npcID = purchase.npcID; break end
                    end
                    row.srcFull = row.npcID and ns.ProfVendorNames and ns.ProfVendorNames[row.npcID]
                    row.srcText = row.srcFull or row.srcText
                end
                row.srcText = clipText(row.srcText, SRC_TEXT_W)
            end
            rows[#rows + 1] = row
        end
        if stepView then
            local lastAt = nil
            for _, e in ipairs(shown) do
                local at = e.at or 0
                if at == math.huge then at = 0 end
                if at ~= lastAt then
                    local htext = at > 0 and format(L["第 %d 步起"], at) or L["路线起点"]
                    local w0 = tw(htext) + 10
                    if w0 > nameW then nameW = w0 end
                    rows[#rows + 1] = { head = true, nm = htext }
                    lastAt = at
                end
                pushRow(e)
            end
        else
            for _, e in ipairs(shown) do pushRow(e) end
        end
        if numW < 34 then numW = 34 end
        if numW > NUM_CAP then numW = NUM_CAP end
        if tagW > TAG_CAP then tagW = TAG_CAP end
        if tagW < 34 then tagW = 34 end
        local srcW = SRC_COL_W
        local innerW = W - 2 * PAD
        local xName = 8
        local xSrc = innerW - 14 - tagW - 8 - srcW
        local xMiss = xSrc - 8 - missW
        local xNum = xMiss - 10 - numW
        nameW = xNum - 10 - xName
        if nameW < 40 then nameW = 40 end
        local maxScroll = math.max(0, #rows - SHOP_MAX)
        PF.shopScroll = math.max(0, math.min(PF.shopScroll or 0, maxScroll))
        local scroll = PF.shopScroll
        local n = 0
        for ri = scroll + 1, math.min(#rows, scroll + SHOP_MAX) do
            local row = rows[ri]
            local ry = -(30 + n * 20)
            local nmFS = rowsShop[n + 1]
            local num = rowsShopNum[n + 1]
            local mp = rowsShopMissPill[n + 1]
            local sp = rowsShopSoldPill[n + 1]
            local srcp = rowsShopSrcPill[n + 1]
            local tp = rowsShopTagPill[n + 1]
            local function paintPill(p, txt, x0, wpx, cr, cg, cb, ca)
                p:ClearAllPoints()
                p:SetPoint("TOPLEFT", f.shop, "TOPLEFT", x0, ry + ((ns.hui and ns.hui.ChipDY and ns.hui.ChipDY(14)) or -0.8))
                p:SetWidth(math.max(wpx, 34))
                if p.__chipFill and ns.hui and ns.hui.PaintSolidFill then
                    ns.hui.PaintSolidFill(p.__chipFill, ns.hui.ChipSolidBase({ cr, cg, cb }))
                    if p.__border then
                        for _, t in ipairs(p.__border) do t:SetVertexColor(cr, cg, cb, 1) end
                    end
                    p.fs:SetTextColor(1, 1, 1)
                else
                    local a2 = ca or 0.99
                    for _, t in ipairs(p.__cols) do t:SetVertexColor(cr, cg, cb, a2) end
                end
                p.fs:SetText(txt)
                p:Show()
            end
            if row.head then
                nmFS:SetText(row.nm)
                nmFS:SetWidth(innerW - 2 * xName)
                nmFS:SetTextColor(Unpack(C_HEAD))
                nmFS:ClearAllPoints()
                nmFS:SetPoint("TOPLEFT", f.shop, "TOPLEFT", xName, ry)
                nmFS:Show()
                num:Hide()
                mp:Hide()
                sp:Hide()
                srcp:Hide()
                tp:Hide()
                n = n + 1
            else
                nmFS:SetTextColor(Unpack(C_TEXT))
                nmFS:SetText((tw(row.nm) > nameW) and clipText(row.nm, nameW) or row.nm)
                nmFS:SetWidth(nameW)
                num:SetWidth(numW)
                num:SetText(row.inventoryUnknown and ("? / "..row.need) or format("%d/%d", math.min(row.have, row.need), row.need))
                nmFS:ClearAllPoints()
                nmFS:SetPoint("TOPLEFT", f.shop, "TOPLEFT", xName, ry)
                nmFS:Show()
                num:ClearAllPoints()
                num:SetPoint("TOPLEFT", f.shop, "TOPLEFT", xNum, ry)
                num:Show()
                if row.inventoryUnknown then
                    paintPill(mp,L["请检查背包"],xMiss,missW,Unpack(C_BAD))
                elseif row.missing > 0 then
                    paintPill(mp, format(L["缺%d"], row.missing), xMiss, missW, Unpack(C_BAD))
                else
                    local okr, okg, okb = Unpack(C_OK)
                    paintPill(mp, L["已备齐"], xMiss, missW, okr, okg, okb, 0.5)
                end
                sp:Hide()
                if row.src and row.srcText then
                    if row.srcKind == 1 then
                        local kr, kg, kb = Unpack(C_HEAD)
                        paintPill(srcp, row.srcText, xSrc, srcW, kr, kg, kb)
                    elseif row.srcKind == 3 then
                        local okr, okg, okb = Unpack(C_OK)
                        paintPill(srcp, row.srcText, xSrc, srcW, okr, okg, okb, 0.5)
                    else
                        paintPill(srcp, row.srcText, xSrc, srcW, 0.58, 0.58, 0.58, 0.45)
                    end
                    srcp.__row = row
                    srcp.fs:SetWidth(srcW - 10)
                    srcp.fs:SetWordWrap(false)
                    srcp:EnableMouse(true)
                else
                    srcp.__row = nil
                    srcp:Hide()
                end
                tp:ClearAllPoints()
                tp:SetPoint("TOPRIGHT", f.shop, "TOPRIGHT", -14, ry + ((ns.hui and ns.hui.ChipDY and ns.hui.ChipDY(14)) or -0.8))
                tp:SetWidth(math.max(tagW, 34))
                if tp.__chipFill and ns.hui and ns.hui.PaintSolidFill then
                    ns.hui.PaintSolidFill(tp.__chipFill, ns.hui.ChipSolidBase({ 0.55, 0.55, 0.55 }))
                    if tp.__border then
                        for _, t in ipairs(tp.__border) do t:SetVertexColor(0.55, 0.55, 0.55, 1) end
                    end
                    tp.fs:SetTextColor(1, 1, 1)
                else
                    for _, t in ipairs(tp.__cols) do t:SetVertexColor(0.55, 0.55, 0.55, 0.22) end
                end
                tp.fs:SetText(row.gate and L["全程"] or format("%d+", row.at))
                tp:Show()
                n = n + 1
            end
        end
        local total = #rows
        if total > SHOP_MAX then
            local visH = SHOP_MAX * 20
            f.shop.sbarTrack:SetSize(3, visH)
            f.shop.sbarTrack:Show()
            local thumbH = math.max(14, math.floor(visH * SHOP_MAX / total + 0.5))
            local thumbOff = math.floor((visH - thumbH) * scroll / (total - SHOP_MAX) + 0.5)
            local sb = f.shop.sbarThumb
            sb:SetHeight(thumbH)
            sb:ClearAllPoints()
            sb:SetPoint("TOPRIGHT", f.shop, "TOPRIGHT", -3, -(28 + thumbOff))
            sb:Show()
        else
            f.shop.sbarTrack:Hide()
            f.shop.sbarThumb:Hide()
        end
        for i = n + 1, #rowsShop do
            rowsShop[i]:Hide()
            rowsShopNum[i]:Hide()
            rowsShopMissPill[i]:Hide()
            rowsShopSoldPill[i]:Hide()
            rowsShopSrcPill[i]:Hide()
        end
        for i = n + 1, #rowsShopTagPill do
            rowsShopTagPill[i]:Hide()
        end
        if n > 0 then
            local shopH = 30 + n * 20 + 10
            f.shop.empty:Hide()
            f.shop:ClearAllPoints()
            f.shop:SetPoint("TOPLEFT", f, "TOPLEFT", PAD, y)
            f.shop:SetSize(W - 2 * PAD, shopH)
            f.shop:Show()
            y = y - shopH - 8
        else
            f.shop.empty:SetText(#list > 0 and L["所有物品已备齐"] or L["无材料"])
            f.shop.empty:Show()
            local shopH = 30 + 20 + 10
            f.shop:ClearAllPoints()
            f.shop:SetPoint("TOPLEFT", f, "TOPLEFT", PAD, y)
            f.shop:SetSize(W - 2 * PAD, shopH)
            f.shop:Show()
            y = y - shopH - 8
        end
    else
        f.shop:Hide()
        PF.shopScroll = nil
    end

    if finished then
        local waiting = PF.pendingPlans and PF.pendingPlans[slug]
        local PD = ns.ProfModule
        f.finish:SetText(waiting and (PD and PD.PlanStatusText and PD.PlanStatusText(waiting) or L["正在计算升级路线…"])
            or format(L["%s跟随完成 · %s"], name, fmtTime(time() - (s.t0 or time()))))
        f.finish:ClearAllPoints()
        f.finish:SetPoint("TOPLEFT", f, "TOPLEFT", 10, y)
        f.finish:Show()
        y = y - 34
    end

    local PD=ns.ProfModule
    local scanText=PD and PD.ScanSnapshotText and PD.ScanSnapshotText()
    local scanWarning,scanBlocked
    if PD and PD.ReplicateScanWarning then scanWarning,scanBlocked=PD.ReplicateScanWarning() end
    scanText=scanText or scanWarning
    if scanText and not (finished and f.finish:GetText()==scanText) then
        f.scanStatus:SetText(scanText)
        f.scanStatus:SetTextColor(scanBlocked and 0.98 or 0.55,scanBlocked and 0.55 or 0.85,scanBlocked and 0.4 or 0.6)
        f.scanStatus:SetWidth(W-20)
        f.scanStatus:ClearAllPoints()
        f.scanStatus:SetPoint("TOPLEFT",f,"TOPLEFT",10,y)
        f.scanStatus:Show()
        y=y-math.max(16,f.scanStatus:GetStringHeight())-8
    end

    if viewing then
        f.nowBtn:ClearAllPoints()
        f.nowBtn:SetPoint("TOPRIGHT", f.card, "TOPRIGHT", -8, -59)
    end
    local by = y - 4
    f.btns[1]:ClearAllPoints()
    f.btns[1]:SetPoint("TOPLEFT", f, "TOPLEFT", PAD, by)
    f.btns[3]:ClearAllPoints()
    f.btns[3]:SetPoint("TOPRIGHT", f, "TOPRIGHT", -PAD, by)
    f.btns[2]:ClearAllPoints()
    f.btns[2]:SetPoint("TOPRIGHT", f.btns[3], "TOPLEFT", -BTN_GAP, 0)
    f.verifyBtn:SetShown(verShown)
    if verShown then
        f.verifyBtn:ClearAllPoints()
        f.verifyBtn:SetPoint("TOPRIGHT", f.card, "TOPRIGHT", -8, -30)
    end

    f:SetHeight(-by + 30)
    sweepPaint(pending)
end

function PF.PaintButton(bt, slug)
    if not bt then return end
    local ok = slug and slug ~= "__index" and hasRoute(slug)
    if not ok then
        bt:SetShown(false)
        return
    end
    local name = (D.pro and D.pro[slug] and D.pro[slug].name) or slug
    local text = format(L["%s升级HUD"], name)
    bt:SetText(text)
    local PD = ns.ProfModule
    if PD and PD.TextW then bt:SetWidth(math.ceil(PD.TextW(text, 13)) + 22) end
    bt:SetScript("OnClick", function() PF.Toggle(slug) end)
    TipOn(bt, text, L["打开 HUD 后，路线就绪时会自动开始执行并追踪制作进度。"] .. "\n"
        .. L["连续 48 小时无制作（含离线）自动结束；战斗中暂停，脱战后恢复。"] .. "\n"
        .. L["关闭 HUD 只隐藏窗口，不会结束追踪。"] .. "\n"
        .. L["不再升级时，请在升级页点击追踪进度按钮结束追踪。"])
    local active = PF.IsActive(slug)
    SetButtonSelected(bt, active)
    local fs = bt.GetFontString and bt:GetFontString()
    if fs then
        fs:ClearAllPoints()
        fs:SetPoint("CENTER", 0, -1)
        fs:SetJustifyH("CENTER")
        fs:SetTextColor(Unpack(active and C_WHITE or C_GREY))
    end
    bt:SetShown(true)
end

function PF.PaintImportBtn(bt, slug)
    if not bt then return end
    local ok = slug and slug ~= "__index" and hasRoute(slug)
    if not ok then
        bt:SetShown(false)
        return
    end
    local text = L["一键导入购物清单"]
    bt:SetText(text)
    local PDm = ns.ProfModule
    if PDm and PDm.TextW then bt:SetWidth(math.ceil(PDm.TextW(text, 13)) + 22) end
    bt:SetScript("OnClick", function()
        local name = (D.pro and D.pro[slug] and D.pro[slug].name) or slug
        DoImport(slug, name)
        ns.PlaySound(1)
    end)
    TipOn(bt, text, L["将拍卖行采购的缺口导入 Auctionator；NPC 货物和自制材料不导入，同名清单将被覆盖。"])
    local ifs = bt.GetFontString and bt:GetFontString()
    if ifs then
        ifs:ClearAllPoints()
        ifs:SetPoint("CENTER", 0, -1)
        ifs:SetJustifyH("CENTER")
        ifs:SetTextColor(Unpack(C_GREY))
    end
    bt:SetShown(true)
end

local function connectExecution()
    local bridge=ns.AuctionBridge
    if bridge and bridge.OnChanged then bridge.OnChanged(function(_,reason)
        if reason=="supply" or reason=="scan-status" then
            PF.InvalidateRoute()
            if PF.f and PF.f:IsShown() then PF.Sync();PF.Paint() end
        end
    end) end
    local XP = ns.ProfExecution
    if XP and XP.OnObservationChanged then XP.OnObservationChanged(function()
        if PF.f and PF.f:IsShown() then
            PF.Sync();PF.Paint()
        end
    end) end
    if XP and XP.OnChanged then XP.OnChanged(function(slug, run, reason)
        if slug=="poisons" then return end
        local state = st()
        if not state or state.slug ~= slug then return end
        if reason == "ended" and run.archiveReason == "completed" then
            PF.endedPlan = PF.endedPlan or {}; PF.endedPlan[slug] = run.plan
        end
        PF.InvalidateRoute()
        PF.Sync()
        if PF.f and PF.f:IsShown() then PF.Paint() end
    end) end
    if RA and RA.OnPlanChanged then RA.OnPlanChanged(function(slug)
        local state = st()
        if not state or state.slug ~= slug then return end
        PF.InvalidateRoute(); PF.Sync()
        if PF.f and not state.hidden then PF.f:Show(); PF.Paint() end
    end) end
end
if ns.Init then ns.Init(connectExecution) else connectExecution() end
