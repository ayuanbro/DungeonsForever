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

local format = string.format

local PF = {}
ns.ProfFollow = PF

PF.CRAFT_BTN = false

local W, W_BASE = 352, 352
local PAD = 12
local BTN_W = { 92, 66, 66 }
local BTN_GAP = 4
local MAT_MAX = 6
local SHOP_MAX = 16
local VENDOR_MAX = 6
local SWEEP_MAX = 5
local IMPORT_TRIES = 5

local C_OK   = { 0.27, 0.75, 0.45 }
local C_BAD  = { 0.85, 0.30, 0.30 }
local C_HEAD = { 0.95, 0.78, 0.35 }

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

local function Have(id)
    if C_Item and C_Item.GetItemCount then
        local ok, n = pcall(C_Item.GetItemCount, id, true)
        if ok and type(n) == "number" then return n end
    end
    if type(GetItemCount) == "function" then
        local ok, n = pcall(GetItemCount, id, true)
        if ok and type(n) == "number" then return n end
    end
    return 0
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

-- Rank reminders read the character's real cap through ProfRanks. They are
-- guidance beside the route and never become execution steps or craft facts.
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
        for _,probe in ipairs({{"inLog","IsOnQuest"},{"readyForTurnIn","ReadyForTurnIn"}}) do
            if type(api[probe[2]])=="function" then
                local ok,value=pcall(api[probe[2]],goal.questID)
                if ok and type(value)=="boolean" then progress[probe[1]]=value end
            end
        end
    end
    local status=progress.readyForTurnIn and L["任务可交付"] or progress.inLog and L["任务已接取"] or nil
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
    if isGathering(slug) then
        PF.pendingPlans=PF.pendingPlans or {};PF.pendingPlans[slug]=nil
        local steps=ns.ProfGatheringRoutes.Steps(slug,routeTarget(slug))
        if not steps then PF.pendingPlans[slug]={status="incomplete",diagnostics={{code="professionCapUnknown"}}} end
        return "gather",steps or {}
    end
    local XP = ns.ProfExecution
    local frozen = XP and XP.GetPlan and XP.GetPlan(slug)
    local economy=ns.ProfEconomy
    if frozen and frozen.learningPolicyFingerprint and economy and economy.LearningPolicyFingerprint
        and frozen.learningPolicyFingerprint~=economy.LearningPolicyFingerprint() then
        PF.pendingPlans=PF.pendingPlans or {}
        PF.pendingPlans[slug]={status="recalculate_required",feasible=false,diagnostics={{code="learningPolicyChanged"}}}
        return "auto",{}
    end
    local PD = ns.ProfModule
    local fixedOnly=slug=="poisons" or slug=="mining" and PD and PD.GatherMode and PD.GatherMode(slug)=="smelt"
    if frozen and fixedOnly and frozen.mode~="fixed" then
        PF.pendingPlans=PF.pendingPlans or {}
        PF.pendingPlans[slug]={status="recalculate_required",feasible=false,diagnostics={{code="fixedOnlyChanged"}}}
        return "fixed",{}
    end
    if frozen then return frozen.mode == "fixed" and "fixed" or "auto", frozen.executionSteps or frozen.steps end
    local ended = PF.endedPlan and PF.endedPlan[slug]
    if ended and PF.Following and PF.Following(slug) then return ended.mode == "fixed" and "fixed" or "auto", ended.executionSteps or ended.steps end
    local scheme = PD and PD.SettingRaw and PD.SettingRaw("autoScheme") or "cheapest"
    local smelt = slug == "mining" and PD and PD.GatherMode and PD.GatherMode(slug) == "smelt"
    local fish = PD and PD.CookingFishingMode and PD.CookingFishingMode(slug)
    local auto = slug ~= "poisons" and not smelt and PD and PD.Setting and (PD.Setting("autoRoute") or fish) and RA
        and (fish or scheme == "cheapest" or scheme == "optim" or RA.Available())
    PF.pendingPlans = PF.pendingPlans or {}
    if auto then
        local opts = RA.OptionsFor and RA.OptionsFor(slug, skill) or {
            start = (PD.Setting("autoFromCurrent") and skill) and math.max(1, skill) or 1,
            onlyAH = PD.Setting("autoOnlyAH"), noFormula = PD.Setting("autoNoFormula"),
            learnedOnly = PD.Setting("autoLearnedOnly"), target = routeTarget(slug), scheme = fish and "fishing" or scheme,
        }
        opts.target = routeTarget(slug)
        local res = RA.Get(slug, opts)
        local list = res and (res.executionSteps or res.steps)
        if res and res.status ~= "selection_required" and res.status ~= "recalculate_required" and res.feasible ~= false
            and list and #list > 0 then
            PF.pendingPlans[slug] = nil
            -- Following is an explicit request to execute; routine route reads
            -- never create a run. Wait for a settled candidate before freezing.
            if XP and XP.Bind and PF.Following(slug) and res.status ~= "searching" then
                XP.Bind(slug, res)
                frozen = XP.GetPlan(slug)
                if frozen then return "auto", frozen.executionSteps or frozen.steps end
            end
            return "auto", list
        end
        PF.pendingPlans[slug] = res or {status="searching"}
        return "auto", {}
    end
    PF.pendingPlans[slug] = nil
    local lv = LV[slug]
    local steps=clipFixedSteps(lv and lv.steps or nil,routeTarget(slug))
    if RA and RA.FilterFixedSpecializations then
        local filtered,blocked,goalRequired=RA.FilterFixedSpecializations(slug,steps,{target=routeTarget(slug)})
        if goalRequired or blocked and #blocked>0 then
            PF.pendingPlans[slug]={status="recalculate_required",specializationBlocked=true,
                diagnostics=blocked or {},steps={},feasible=false}
            return "fixed",{}
        end
        steps=filtered
    end
    if XP and PF.Following(slug) and steps and #steps>0 then
        local summary=RA and RA.SummarizeSteps and RA.SummarizeSteps(steps,slug,{target=routeTarget(slug),scheme="fixed"})
        summary=summary or {steps=steps,mats={},formulas={},total=0,scheme="fixed",target=routeTarget(slug)}
        summary.mode="fixed";summary.scheme="fixed"
        local normalized,reason=XP.NormalizePlan(slug,summary)
        if not normalized or summary.feasible==false then
            PF.pendingPlans[slug]={status="recalculate_required",feasible=false,diagnostics={{code=reason or "fixedUnavailable"}}}
            return "fixed",{}
        end
        local run=XP.Bind(slug,normalized)
        if run then return "fixed",run.plan.executionSteps or run.plan.steps end
    end
    return "fixed",steps
end

local rMemoSlug, rMemoSkill, rMemoMode, rMemoSteps, rMemoT
local ROUTE_MEMO_TTL = 10
local function routeFor(slug, skill)
    local now = GetTime and GetTime() or 0
    if slug and rMemoSlug == slug and rMemoSkill == skill
       and (now - (rMemoT or 0)) < ROUTE_MEMO_TTL then
        return rMemoMode, rMemoSteps
    end
    local mode, steps = routeForCalc(slug, skill)
    rMemoSlug, rMemoSkill, rMemoMode, rMemoSteps, rMemoT = slug, skill, mode, steps, now
    return mode, steps
end

function PF.InvalidateRoute()
    rMemoSlug, rMemoSkill, rMemoMode, rMemoSteps, rMemoT = nil, nil, nil, nil, nil
end

local function routeKey(mode, steps)
    if not steps then return tostring(mode) .. ":0" end
    local a, b = steps[1], steps[#steps]
    return format("%s:%d:%s:%s:%s", tostring(mode), #steps,
                  tostring(a and a[1]), tostring(a and a[3]), tostring(b and b[2]))
end

local function derivedStep(slug, skill)
    local XP = ns.ProfExecution
    local run = not isGathering(slug) and XP and XP.GetRun and XP.GetRun(slug)
    if run then XP.Sync(slug); return run.currentIndex or 1 end
    local ended = PF.endedPlan and PF.endedPlan[slug]
    if ended and PF.Following and PF.Following(slug) then return #(ended.executionSteps or ended.steps or {}) + 1 end
    local _, steps = routeFor(slug, skill)
    if not steps then return nil end
    for i, s in ipairs(steps) do
        if next(s.requiredOutputs or {}) or s.kind == "specialization_quest" or s.kind == "essence_conversion" or skill < s[2] then return i end
    end
    return #steps + 1
end

local function recMats(rec) return rec and (rec[12] or rec.mats) or nil end
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
local function recItem(rec) return rec and (rec[2] or rec.makes) or nil end
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

function PF.Sync()
    local s = st()
    if not (s and s.slug) then return false end
    local changed = false
    local cur = skillOf(s.slug)
    if cur and cur ~= s.skill then
        s.skill = cur
        changed = true
        local PD = ns.ProfModule
        if PD and PD.built and PD.cur == s.slug and PD.page and PD.page:IsVisible() then
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

function PF.RefreshRoute(slug)
    local s = st()
    if not (s and s.slug) then return end
    if slug and slug ~= s.slug then return end
    PF.InvalidateRoute()
    PF.Sync()
    if PF.f and PF.f:IsShown() then pcall(PF.Paint) end
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
        return
    end
    if s and not s.hidden and PF.f and PF.f:IsShown() then
        s.hidden = true
        PF.f:Hide()
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
    PF.InvalidateRoute()
    if PF.f then
        PF.Sync()
        PF.view = 0
        PF.f:Show()
        PF.Paint()
        return
    end
    if PF.building then return end
    PF.onBuilt = function()
        if not PF.f then return end
        PF.Sync()
        PF.view = 0
        PF.f:Show()
        PF.Paint()
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
    local T = ns.ProfTrack
    local s = st()
    if not (s and s.slug and T and T.VerifyOutput and T.Progress) then return false end
    local run = T.GetRun(s.slug)
    local prog = run and T.Progress(s.slug, nil, run)
    if not ref then ref = prog end
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
    local T = ns.ProfTrack
    local s = st()
    if not (s and s.slug and T and T.GetRun and T.Progress) then return end
    if not (StaticPopupDialogs and StaticPopup_Show) then return end
    local run = T.GetRun(s.slug)
    local prog = run and T.Progress(s.slug, nil, run)
    if not prog or not prog.item or prog.finished then return end
    local data = { slug = s.slug, index = prog.index, item = prog.item, total = prog.manualConversion and prog.remainingConversions or prog.outputs or 0, manualConversion = prog.manualConversion, planID = run.planID }
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

local function craftsLeft(seg, skill, rec)
    local XP = ns.ProfExecution
    if seg.segmentID and XP and XP.CurrentPlan then
        local slug = st() and st().slug
        local run = slug and XP.GetRun(slug)
        if run then
            local progress = XP.Progress(run.slug, seg.segmentID)
            if progress then
                if XP.IsSpecializationQuest(seg) then return progress.complete and 0 or 1 end
                return progress.remainingCrafts or 0
            end
        end
    end
    if XP and XP.IsSpecializationQuest(seg) then return 1 end
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

local function shopList(s, onlyStep)
    local _, steps = routeFor(s.slug, s.skill)
    if not steps then return {} end
    local rm = recMap(s.slug)
    local totals, order = {}, {}
    local curStep = s.step or 1
    for i = curStep, #steps do
        if onlyStep and i > curStep then break end
        local seg = steps[i]
        local rec = stepRecipe(seg, rm[seg[3]])
        local mats = recMats(rec)
        local crafts = seg[4] or 0
        if seg.segmentID or i == curStep then
            crafts = math.ceil(craftsLeft(seg, s.skill, rec))
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
    local active = ns.ProfExecution and ns.ProfExecution.GetPlan(s.slug)
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
    local list = {}
    for _, id in ipairs(order) do
        local e = totals[id]
        e.have = Have(e.id)
        list[#list + 1] = e
    end
    return list
end

-- The first HUD task uses the plan's actual leaf purchases. Intermediate
-- products, AH purchases and formula items must not become NPC material needs.
local TipOn
function PF.VendorPurchases(slug, plan)
    local xp=ns.ProfExecution
    plan=plan or (xp and xp.GetPlan and xp.GetPlan(slug)) or (RA and RA.Peek and RA.Peek(slug))
    if not plan or plan.feasible==false then return {} end
    local totals,order={},{}
    for _,entry in ipairs(plan.mats or {}) do
        local id=entry.id or entry[1]
        if id and (entry.source=="vendor" or entry.vendor and entry.source~="ah" and entry.source~="auction") then
            local row=totals[id]
            if not row then
                row={id=id,need=0,npcID=entry.npcID};totals[id]=row;order[#order+1]=id
            end
            row.need=row.need+(entry.count or entry[2] or entry.need or 0)
        end
    end
    local out={}
    for _,id in ipairs(order) do
        local row=totals[id];row.have=Have(id);row.missing=math.max(0,row.need-row.have)
        if row.missing>0 then out[#out+1]=row end
    end
    return out
end

function PF.PaintVendorPurchases(slug, y)
    local panel=PF.f and PF.f.vendorShop
    if not panel then return y,false end
    local state=st()
    local list=state and (state.step or 1)==1 and (PF.view or 0)==0 and PF.VendorPurchases(slug) or {}
    if #list==0 then panel:Hide();PF.vendorScroll=nil;return y,false end
    local offset=math.max(0,math.min(PF.vendorScroll or 0,math.max(0,#list-VENDOR_MAX)))
    PF.vendorScroll=offset
    panel.title:SetText(format(L["先购买 NPC 材料（%d 种）"],#list))
    panel.more:SetShown(#list>VENDOR_MAX)
    local pd=ns.ProfModule
    local pending=false
    for i,row in ipairs(panel.rows) do
        local entry=list[offset+i]
        row:Hide()
        if entry then
            local name,known=DG.ItemName(entry.id)
            if not known and DG.RequestItem then DG.RequestItem(entry.id);pending=true end
            local npc=entry.npcID and ns.ProfVendorNames and ns.ProfVendorNames[entry.npcID] or L["商人"]
            local loc=entry.npcID and ns.ProfVendors and ns.ProfVendors[entry.npcID]
            if not loc and entry.npcID and ns.EnsureProfNPCLocs then
                local locations=ns.EnsureProfNPCLocs()[entry.npcID];loc=locations and locations[1]
            end
            local where=npc
            local zone=loc and pd and pd.MapName and pd.MapName(loc[2])
            if zone and zone~="" then where=where.." · "..zone end
            if loc and loc[3] and loc[4] then where=where..format(" (%.1f, %.1f)",loc[3],loc[4]) end
            row.name:SetText(format("%s ×%d",name or ("#"..entry.id),entry.missing))
            row.source:SetText(where)
            row.__it={entry.id};row.__loc=loc
            TipOn(row,name or ("#"..entry.id),where)
            row:SetScript("OnClick",loc and pd and pd.MarkVendorLoc and function()pd.MarkVendorLoc(loc)end or nil)
            row:Show()
        end
    end
    local height=28+math.min(#list,VENDOR_MAX)*38
    panel:ClearAllPoints();panel:SetPoint("TOPLEFT",PF.f,"TOPLEFT",PAD,y)
    panel:SetSize(W-2*PAD,height);panel:Show()
    return y-height-8,pending
end

function PF.SupplementNeeds(slug)
    slug = slug or (st() and st().slug)
    if not slug then return nil end
    local s = st()
    if not (s and s.slug == slug and s.step) then
        local cur = skillOf(slug) or 0
        s = { slug = slug, skill = cur, step = derivedStep(slug, cur) or 1 }
    end
    local list = shopList(s, true)
    local items, kinds, qty = {}, 0, 0
    for _, e in ipairs(list) do
        local lack = (e.need or 0) - (e.have or 0)
        if lack > 0 then
            items[#items + 1] = { id = e.id, need = e.need, have = e.have, lack = lack }
            kinds = kinds + 1
            qty = qty + lack
        end
    end
    if kinds == 0 then return nil end
    return { items = items, kinds = kinds, qty = qty, step = s.step }
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
        C_Timer.After(0, function()
            if jumpPending then jumpApply() end
        end)
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

local function openProfPanel(s)
    local profName = D.pro and D.pro[s.slug] and D.pro[s.slug].name
    local ids = (GetProfessions and { GetProfessions() }) or {}
    if C_TradeSkillUI and C_TradeSkillUI.OpenTradeSkill and type(GetProfessionInfo) == "function" then
        for _, idx in ipairs(ids) do
            if idx then
                local nm, skillLine = GetProfessionInfo(idx)
                if profName and nm == profName and skillLine
                    and pcall(C_TradeSkillUI.OpenTradeSkill, skillLine) then
                    return true
                end
            end
        end
        for _, idx in ipairs(ids) do
            if idx then
                local skillLine = select(7, GetProfessionInfo(idx))
                if skillLine and pcall(C_TradeSkillUI.OpenTradeSkill, skillLine) then
                    return true
                end
            end
        end
    end
    for _, idx in ipairs(ids) do
        if idx then
            local sid = CraftingEntrySpellID(idx)
            local nm = sid and SpellName(sid)
            if nm and CastSpellByName and pcall(CastSpellByName, nm) then return true end
            if sid and C_Spell and C_Spell.CastSpell and pcall(C_Spell.CastSpell, sid) then return true end
        end
    end
    if profName and CastSpellByName then
        pcall(CastSpellByName, profName)
        return true
    end
    return false
end

function jumpApply()
    local p = jumpPending
    if not p then return end
    local selected, counted = false, false
    if C_TradeSkillUI then
        if C_TradeSkillUI.SetSelectedRecipe then
            pcall(C_TradeSkillUI.SetSelectedRecipe, p.spellID)
            if C_TradeSkillUI.GetSelectedRecipeID then
                local ok, rid = pcall(C_TradeSkillUI.GetSelectedRecipeID)
                selected = ok and rid == p.spellID
            else
                selected = true
            end
        end
        if C_TradeSkillUI.SetRecipeRepeatCount then
            if pcall(C_TradeSkillUI.SetRecipeRepeatCount, p.spellID, p.count) then counted = true end
        end
    end
    if not counted and type(GetNumTradeSkills) == "function" then
        for i = 1, GetNumTradeSkills() do
            local nm = GetTradeSkillInfo(i)
            if nm == p.name then
                if SelectTradeSkill then pcall(SelectTradeSkill, i) end
                if SetTradeSkillRepeatCount then pcall(SetTradeSkillRepeatCount, i, p.count) end
                selected, counted = true, true
                break
            end
        end
    end
    if counted then
        jumpPending = nil
        craftNotify(format(L["已定位配方 %s，预填制造数量 %d —— 在专业面板点一次制造即可"], p.name, p.count))
    elseif selected then
        jumpPending = nil
        craftNotify(format(L["已选中配方 %s，请在专业面板输入制造数量"], p.name))
    end
end

local function jumpCraft()
    local s = st()
    if not (s and s.slug) then return end
    local _, steps = routeFor(s.slug, s.skill)
    local seg = steps and steps[(s.step or 1)]
    if not seg then return end
    local spellID = seg[3]
    if not IsLearned(spellID) then craftNotify(L["该配方还未学会，先找训练师学习"]) return end
    local rec = stepRecipe(seg, recMap(s.slug)[spellID])
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
    local count = math.max(1, math.ceil(craftsLeft(seg, s.skill, rec)))
    local name = SpellName(spellID)
    if not name then craftNotify(L["配方数据未就绪，稍后再试"]) return end
    jumpEvtInit()
    if openProfPanel(s) then
        jumpPending = { spellID = spellID, count = count, name = name }
        craftNotify(format(L["正在打开专业面板并定位 %s（预填数量 %d）…"], name, count))
        if C_Timer and C_Timer.After then
            C_Timer.After(0.5, function() if jumpPending then jumpApply() end end)
            C_Timer.After(1.5, function()
                if jumpPending then
                    jumpApply()
                    if jumpPending then
                        jumpPending = nil
                        if panelShown() then
                            craftNotify(L["面板已打开但未能自动定位配方，请在列表中手动选择"])
                        else
                            craftNotify(L["无法自动打开专业面板，请手动打开后重试"])
                        end
                    end
                end
            end)
        end
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
    local items, missing = {}, 0
    for _, e in ipairs(list) do
        local nm, got = DG.ItemName(e.id)
        if not got then
            missing = missing + 1
            DG.RequestItem(e.id)
        else
            local lack = e.need - e.have
            if lack > 0 then
                items[#items + 1] = { name = nm, need = lack }
            end
        end
    end
    if missing > 0 and importTries < IMPORT_TRIES then
        importTries = importTries + 1
        C_Timer.After(1, function() DoImport(slug, profName) end)
        return
    end
    importTries = 0
    if ns.AuctionBridge and ns.AuctionBridge.DoImport then
        ns.AuctionBridge.DoImport(profName, items)
    end
end

local PROC_FRAME_MS, PROC_SLICE_MS = 10, 3

local function procureSig(slug, demands)
    local ids = {}
    for id in pairs(demands) do ids[#ids + 1] = id end
    table.sort(ids)
    local parts = {}
    for i = 1, #ids do parts[i] = ids[i] .. ":" .. demands[ids[i]] end
    return slug .. "|" .. table.concat(parts, ",")
end

function PF.ProcureBusy()
    return PF.procureJob ~= nil
end

local function procureNotify(res)
    if not res then
        craftNotify(L["优化买法：未找到可行买法，部分材料没有可靠货源。"])
        return
    end
    local RA = ns.ProfRouteAuto
    local byNPC, ahN, vendorN = {}, 0, 0
    for _, e in ipairs(res.mats or {}) do
        if e.vendor then
            vendorN = vendorN + 1
            if e.npcID then byNPC[e.npcID] = (byNPC[e.npcID] or 0) + 1 end
        else
            ahN = ahN + 1
        end
    end
    local VN = ns.ProfVendorNames
    local parts = {}
    for npcID, n in pairs(byNPC) do
        local nm = (VN and VN[npcID]) or format(L["商人 NPC #%d"], npcID)
        parts[#parts + 1] = format(L["%s（%d 种）"], nm, n)
    end
    local head = format(L["优化买法完成：%d 位商人 + 拍卖行 %d 种"], #parts, ahN)
    if RA and RA.MoneyStr and res.total then
        head = head .. " · " .. format(L["预计花费 %s"], RA.MoneyStr(res.total, "copper"))
    end
    if #parts > 0 then head = head .. "：" .. table.concat(parts, "、") end
    craftNotify(head)
end

function PF.ProcureStart()
    local s = st()
    if not (s and s.slug) then return end
    if PF.procureJob then return end
    local E = ns.ProfEconomy
    local S = ns.ProfRouteSolver
    local J = ns.IdleJobs
    if not (E and S and J and E.Capture and S.NewProcurementJob and S.Run) then
        craftNotify(L["优化买法不可用：求解器组件未加载。"])
        return
    end
    local list = shopList(s)
    local demands, n = {}, 0
    for _, e in ipairs(list) do
        local lack = (e.need or 0) - (e.have or 0)
        if lack > 0 and type(e.id) == "number" then
            demands[e.id] = (demands[e.id] or 0) + lack
            n = n + 1
        end
    end
    if n <= 0 then
        craftNotify(L["购物清单已全部备齐，无需采购。"])
        return
    end
    local slug = s.slug
    local opts = { target = 300 }
    opts.professions = (E.Professions and E.Professions()) or {}
    if not opts.professions[slug] then opts.professions[slug] = { cur = 1, max = 300 } end
    PF.procureRes = nil
    PF.procureSlug = slug
    PF.procureSig = procureSig(slug, demands)
    local job = { phase = "capture" }
    PF.procureJob = job
    job.co = coroutine.create(function()
        local snap = E.Capture(slug, opts, function()
            if debugprofilestop() > (job.deadline or 0) then coroutine.yield("work") end
        end)
        job.phase = "search"
        return S.NewProcurementJob(snap, demands, { cpuLimitMs = 2000 })
    end)
    J.Add(function()
        if PF.procureJob ~= job then return true end
        job.deadline = debugprofilestop() + PROC_FRAME_MS
        while true do
            if job.job then
                if S.Run(job.job, PROC_SLICE_MS) then
                    local res = job.job.result
                    if not res then res = S.Result(job.job, job.job.best, job.job.status) end
                    PF.procureJob = nil
                    PF.procureRes = (res and res.feasible and #(res.mats or {}) > 0) and res or nil
                    if f and f:IsShown() then PF.Paint() end
                    procureNotify(PF.procureRes)
                    return true
                end
            else
                local ok, out = coroutine.resume(job.co)
                if not ok then
                    PF.procureJob = nil
                    if f and f:IsShown() then PF.Paint() end
                    craftNotify(L["优化买法计算出错。"])
                    return true
                end
                if coroutine.status(job.co) == "dead" then job.job = out end
            end
            if debugprofilestop() >= job.deadline then break end
        end
        if f and f:IsShown() then PF.Paint() end
        return false
    end)
end

local f

local rowsMat, rowsShop = {}, {}
local rowsMatIcon = {}
local rowsMatBadge = {}
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
        if f:IsShown() then
            C_Timer.After(0, function()
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
    if ns.huiTheme == "hui" and ns.hui and ns.hui.layer and ns.hui.layer.L2 then
        local l2 = ns.hui.layer.L2
        f:SetBackdropColor(l2[1], l2[2], l2[3], 0.95)
        f:SetBackdropBorderColor(1, 1, 1, 0.10)
    else
        f:SetBackdropColor(0, 0, 0, 0.35)
        f:SetBackdropBorderColor(0.30, 0.30, 0.30, 1)
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

    f.skill = MakeFS(f, 16, C_GREY, "LEFT")
    f.skill:SetPoint("TOPLEFT", f, "TOPLEFT", 10, -42)

    f.rankHint = CreateFrame("Frame", nil, f)
    f.rankHint:SetPoint("TOPLEFT", f, "TOPLEFT", 8, -39)
    f.rankHint:SetSize(196, 24)
    f.rankHint:EnableMouse(true)
    f.rankHint:SetScript("OnEnter", function(self)
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

    f.vendorShop=CreateFrame("Frame",nil,f)
    local vendorPanel=f.vendorShop
    vendorPanel.title=MakeFS(vendorPanel,14,C_HEAD,"LEFT")
    vendorPanel.title:SetPoint("TOPLEFT",vendorPanel,"TOPLEFT",0,-2)
    vendorPanel.more=MakeFS(vendorPanel,11,C_GREY,"RIGHT")
    vendorPanel.more:SetPoint("TOPRIGHT",vendorPanel,"TOPRIGHT",0,-3)
    vendorPanel.more:SetText(L["滚轮查看更多"])
    vendorPanel.title:SetPoint("RIGHT",vendorPanel.more,"LEFT",-6,0)
    vendorPanel.title:SetWordWrap(false)
    vendorPanel.rows={}
    for i=1,VENDOR_MAX do
        local row=CreateFrame("Button",nil,vendorPanel)
        row:SetPoint("TOPLEFT",vendorPanel,"TOPLEFT",0,-24-(i-1)*38)
        row:SetPoint("RIGHT",vendorPanel,"RIGHT",0,0);row:SetHeight(36)
        row.name=MakeFS(row,14,C_TEXT,"LEFT")
        row.name:SetPoint("TOPLEFT",row,"TOPLEFT",0,0);row.name:SetPoint("RIGHT",row,"RIGHT",0,0)
        row.name:SetWordWrap(false)
        row.source=MakeFS(row,11,C_GREY,"LEFT")
        row.source:SetPoint("TOPLEFT",row,"TOPLEFT",0,-18);row.source:SetPoint("RIGHT",row,"RIGHT",0,0)
        row.source:SetWordWrap(false)
        vendorPanel.rows[i]=row
    end
    vendorPanel:EnableMouseWheel(true)
    vendorPanel:SetScript("OnMouseWheel",function(_,delta)
        PF.vendorScroll=math.max(0,(PF.vendorScroll or 0)-delta);PF.Paint()
    end)
    vendorPanel:Hide()

    f.seg = MakeFS(f, 16, C_GREY, "RIGHT")
    f.seg:SetPoint("TOPRIGHT", f, "TOPRIGHT", -10, -42)

    f.barBG = f:CreateTexture(nil, "BACKGROUND")
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

    f.card = CreateFrame("Frame", nil, f, BackdropTemplateMixin and "BackdropTemplate" or nil)
    f.card:SetBackdrop({
        bgFile = "Interface\\Buttons\\WHITE8x8",
        edgeFile = "Interface\\Buttons\\WHITE8x8",
        edgeSize = 1,
    })
    if ns.huiTheme == "hui" and ns.hui and ns.hui.layer and ns.hui.layer.L3 then
        local l3 = ns.hui.layer.L3
        f.card:SetBackdropColor(l3[1], l3[2], l3[3], 0.95)
    else
        f.card:SetBackdropColor(1, 1, 1, 0.06)
    end
    f.card:SetBackdropBorderColor(0, 0, 0, 0)
    f.card.__round = RoundFrame(f.card, 6, { 0, 1, 0.4, 0.9 })

    f.card:EnableMouse(true)
    f.card:SetScript("OnEnter", function(self)
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
    end)
    f.card:SetScript("OnLeave", function() GameTooltip:Hide() end)

    f.card.icon = f.card:CreateTexture(nil, "ARTWORK")
    f.card.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
    if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(f.card.icon) end
    f.card.icon:SetSize(26, 26)
    f.card.icon:SetPoint("TOPLEFT", f.card, "TOPLEFT", 8, -8)

    f.card.name = MakeFS(f.card, 16, C_TEXT, "LEFT")
    f.card.name:SetWordWrap(false)
    f.card.name:SetPoint("TOPLEFT", f.card, "TOPLEFT", 42, -9)

    f.card.range = MakeFS(f.card, 14, C_GREY, "LEFT")
    f.card.range:SetWordWrap(false)
    f.card.range:SetPoint("TOPLEFT", f.card, "TOPLEFT", 42, -12)

    f.card.crafts = MakeFS(f.card, 14, C_GREY, "LEFT")
    f.card.crafts:SetWordWrap(false)
    f.card.crafts:SetPoint("TOPLEFT", f.card, "TOPLEFT", 42, -33)

    f.card.srcTag = MakeFS(f.card, 14, C_GREY, "RIGHT")
    f.card.srcTag:SetWordWrap(false)
    f.card.srcTag:SetPoint("TOPRIGHT", f.card, "TOPRIGHT", -8, -9)

    f.card.matHead = MakeFS(f.card, 14, C_GREY, "LEFT")
    f.card.matHead:SetPoint("TOPLEFT", f.card, "TOPLEFT", 8, -56)
    BuildStep(3)

    for i = 1, MAT_MAX + 1 do
        BuildStep()
        rowsMat[i] = MakeLine(f.card, 14, C_TEXT)
        local ic = f.card:CreateTexture(nil, "ARTWORK")
        ic:SetTexCoord(0.07, 0.93, 0.07, 0.93)
        if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(ic) end
        ic:SetSize(22, 22)
        ic:Hide()
        rowsMatIcon[i] = ic
        local bd = MakeFS(f.card, 14, C_GOLD, "RIGHT")
        bd:SetFont(ns.FONT or "Fonts\\FRIZQT__.TTF", 14, "THICKOUTLINE")
        bd:SetShadowColor(0, 0, 0, 1)
        bd:SetShadowOffset(1, -1)
        bd:SetWordWrap(false)
        bd:Hide()
        rowsMatBadge[i] = bd
    end
    BuildStep(4)

    f.shop = CreateFrame("Frame", nil, f, BackdropTemplateMixin and "BackdropTemplate" or nil)
    f.shop:SetBackdrop({
        bgFile = "Interface\\Buttons\\WHITE8x8",
        edgeFile = "Interface\\Buttons\\WHITE8x8",
        edgeSize = 1,
    })
    if ns.huiTheme == "hui" and ns.hui and ns.hui.layer and ns.hui.layer.L3 then
        local l3 = ns.hui.layer.L3
        f.shop:SetBackdropColor(l3[1], l3[2], l3[3], 0.95)
    else
        f.shop:SetBackdropColor(1, 1, 1, 0.04)
    end
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
          L["将当前购物清单导入 Auctionator 的购物清单，只导入还缺的数量，同名清单将被覆盖。"])

    f.shopProc = NewButton(f.shop, L["优化买法"], 66, 20, 13)
    f.shopProc:SetScript("OnClick", function()
        PF.ProcureStart()
        ns.PlaySound(1)
    end)
    f.shopProc:SetPoint("RIGHT", f.shopImp, "LEFT", -10, 0)
    TipOn(f.shopProc, L["优化买法"],
          L["对清单里还缺的材料比较商人与拍卖行，找出总支出最低的买法；完成后聊天栏给出摘要，悬停商人名可在地图标记。"])

    f.shopStep = NewButton(f.shop, L["分步"], 48, 20, 13)
    f.shopStep:SetScript("OnClick", function()
        dbProf().shopStepView = not (dbProf().shopStepView and true or false)
        PF.shopScroll = 0
        PF.Paint()
        ns.PlaySound(1)
    end)
    f.shopStep:SetPoint("RIGHT", f.shopProc, "LEFT", -10, 0)
    TipOn(f.shopStep, L["分步 / 汇总"],
          L["汇总：所有步骤的材料合并成一行。分步：按首次需要的步骤分组列出，便于分段采购。"])

    f.craftBtn = NewButton(f, L["跳转制造"], 66, 22, 14)
    f.craftBtn:Hide()
    f.craftBtn:SetScript("OnClick", function()
        jumpCraft()
        ns.PlaySound(1)
    end)
    TipOn(f.craftBtn, L["跳转制造"],
          L["打开专业面板并自动定位当前段配方、预填制造数量；在面板内点一次制造即可批量完成。"])

    f.finish = MakeFS(f, 14, C_OK, "LEFT")
    f.finish:SetWordWrap(false)

    f.nowBtn = NewButton(f, L["回到当前"], 84, 22, 14)
    f.nowBtn:Hide()
    f.nowBtn:SetScript("OnClick", function() PF.view = 0 PF.Paint() ns.PlaySound(1) end)

    f.verifyBtn = NewButton(f, L["校正产出"], 84, 22, 14)
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
    end)
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

local function paintMats(seg, rm, sold, w, remaining)
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
        f.card.matHead:Hide()
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
            if sold[m[1]] then txt = txt .. " · " .. L["商人直卖"] end
            line:SetText(txt)
            line:ClearAllPoints()
            line:SetPoint("TOPLEFT", f.card, "TOPLEFT", 36, -(61 + (i - 1) * 26))
            line:SetWidth(w - 28)
            line:Show()
            local ic = rowsMatIcon[i]
            ic:SetTexture(DG.ItemIcon(m[1]) or Host.FALLBACK_ICON)
            if ns.hui and ns.hui.SetIconRing then
                local mq = DG.QualOf and DG.QualOf(m[1]) or nil
                ns.hui.SetIconRing(ic, mq and { ns.hui.QColor(mq) } or nil)
            end
            ic:ClearAllPoints()
            ic:SetPoint("TOPLEFT", f.card, "TOPLEFT", 8, -(56 + (i - 1) * 26))
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
            more:SetPoint("TOPLEFT", f.card, "TOPLEFT", 8, -(56 + n * 26))
            more:SetWidth(w)
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
        f.card.matHead:SetText(L["无材料"])
        f.card.matHead:Show()
    else
        f.card.matHead:SetText(L["材料未收录"])
        f.card.matHead:Show()
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

function PF.Paint()
    if not (f and f:IsShown()) then return end
    W = W_BASE + ((PF.showShop and PF.wide) or 0)
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
    f.rankHint.tasks = rankTasks
    f.rankHint:SetShown(#rankTasks > 0)
    local skillText = cur and format(L["技能 %d / %d"], cur, mx or 300) or L["未学过该专业，先找训练师学习"]
    if #rankTasks > 0 then skillText = skillText .. " · " .. L["晋级"] end
    f.skill:SetText(skillText)
    f.skill:SetTextColor(Unpack(#rankTasks > 0 and C_HEAD or C_GREY))
    local ratio = cur and math.min(1, cur / 300) or 0
    f.bar:SetWidth(math.max(2, math.floor((W - 20) * ratio + 0.5)))
    f.bar:SetVertexColor(accent[1], accent[2], accent[3], 0.95)

    local finished = (s.step or 1) > #steps
    local vi = math.max(1, math.min(#steps, (s.step or 1) + (PF.view or 0)))
    f.seg:SetText(((mode == "auto") and L["自动计算"] or mode == "gather" and L["采集路线"] or L["固定路线"]) .. " · "
                  .. format(L["段落 %d / %d"], vi, #steps))
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
    f.nowBtn:SetShown((PF.view or 0) ~= 0 and not finished)
    local TK = ns.ProfTrack
    local vRun = TK and TK.Active and TK.Active(slug)
    local vProg = vRun and TK.Progress and TK.Progress(slug, nil, vRun)
    f.verifyBtn:SetText(vProg and vProg.manualConversion and L["确认转换"] or L["校正产出"])
    f.verifyBtn:SetShown(not finished and vProg ~= nil and vProg.item ~= nil and not vProg.finished and not f.craftBtn:IsShown())
    f.craftBtn:SetShown(PF.CRAFT_BTN and not finished)

    local y = -82
    local pending = false
    if finished then f.vendorShop:Hide()
    else y,pending=PF.PaintVendorPurchases(slug,y) end

    if not finished then
        local seg = steps[vi]
        local rm = recMap(slug)
        local sold = soldSet(slug)
        local rec = stepRecipe(seg, rm[seg[3]])
        local card, w = f.card, W - 2 * PAD - 16
        local isCur = (vi == s.step)

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
        if vi == s.step then
            remaining = math.ceil(craftsLeft(seg, s.skill, rec))
            crafts = remaining
        end
        local nMat, pend, canCraft = paintMats(seg, rm, sold, w - 8, remaining)
        pending = pending or pend

        local src, detail
        if PDm and PDm.LevelSrc then
            src, detail = PDm.LevelSrc(rec)
        end
        local learned = IsLearned(seg[3])
        local manual = seg.navigationOnly or seg.checkpoint or XP and (XP.IsConversion(seg) or XP.IsSpecializationQuest(seg))
        local tagText = seg.navigationOnly and L["参考"] or manual and L["手动完成后继续"] or learned and L["已学习"] or (src or L["向训练师学习"])
        if detail and not learned then tagText = tagText .. " · " .. detail end
        card.srcTag:SetText(tagText)
        card.srcTag:SetTextColor(Unpack(learned and C_OK or C_GREY))
        local tagW = 90
        if PDm and PDm.TextW then
            local okW, tw = pcall(PDm.TextW, tagText, 14)
            if okW and type(tw) == "number" then tagW = math.ceil(tw) end
        end
        card.srcTag:SetWidth(tagW)

        local rangeText = format(L["%d – %d"], seg[1], seg[2])
        card.range:SetText(rangeText)
        local craftText = questInfo and questInfo.summary
            or seg.navigationOnly and L["按实际技能推进；不预计采集产出。"]
            or seg.checkpoint and L["不预先计入尚未采到的矿石"] or format(L["大约还需制作%d次"], crafts)
        if canCraft then craftText = craftText .. " · " .. format(L["材料还可制作%d次"], canCraft) end
        card.crafts:SetText(craftText)

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
        card.range:SetPoint("TOPLEFT", f.card, "TOPLEFT", 42 + nameX + 10, -12)
        card.range:SetWidth(rangeW + 6)

        local cardH = nMat * 26 + 60 + (((PF.view or 0) ~= 0) and 26 or 0)
        card:ClearAllPoints()
        card:SetPoint("TOPLEFT", f, "TOPLEFT", PAD, y)
        card:SetSize(W - 2 * PAD, cardH)
        y = y - cardH - 8
    end

    if PF.showShop and not finished then
        local list = shopList(s)
        local shown = {}
        for _, e in ipairs(list) do
            e.missing = e.need - e.have
            if (not onlyMissView()) or e.missing > 0 then shown[#shown + 1] = e end
        end
        f.shop.missTog:SetChecked(onlyMissView())
        if PF.ProcureBusy() then f.shopProc:SetText(L["优化中…"]) else f.shopProc:SetText(L["优化买法"]) end
        local procure
        if not PF.ProcureBusy() and PF.procureRes and PF.procureSlug == slug then
            local cur = {}
            for _, e in ipairs(list) do
                local lack = (e.need or 0) - (e.have or 0)
                if lack > 0 then cur[e.id] = (cur[e.id] or 0) + lack end
            end
            if procureSig(slug, cur) == PF.procureSig then procure = PF.procureRes end
        end
        local srcByID
        if procure then
            srcByID = {}
            for _, e in ipairs(procure.mats or {}) do
                local mid = e[1] or e.id
                if mid and srcByID[mid] == nil then
                    srcByID[mid] = e.vendor and { vendor = true, npcID = e.npcID } or { ah = true }
                end
            end
        end
        local function tw(txt)
            local PDm = ns.ProfModule
            if PDm and PDm.TextW then
                local ok, wv = pcall(PDm.TextW, txt, 14)
                if ok and type(wv) == "number" then return wv end
            end
            return #txt * 5 + 16
        end
        local rows = {}
        local nameW, numW, missW, tagW, srcW, anySold = 0, 0, 0, 0, 0, false
        local stepView = (dbProf().shopStepView) and true or false
        f.shopStep:SetText(stepView and L["汇总"] or L["分步"])
        local function pushRow(e)
            local nm, got = DG.ItemName(e.id)
            if not got then DG.RequestItem(e.id) pending = true end
            local row = {
                nm = nm,
                have = e.have,
                need = e.need,
                missing = e.need - e.have,
                sold = soldSet(slug)[e.id] and true or false,
                at = e.at or 0,
                src = srcByID and srcByID[e.id] or nil,
            }
            if row.at == math.huge then
                row.gate = true
                row.at = 0
            end
            local w1 = tw(row.nm)
            if w1 > nameW then nameW = w1 end
            local w2 = tw(format("%d/%d", math.min(row.have, row.need), row.need))
            if w2 > numW then numW = w2 end
            local w3 = tw(row.missing > 0 and format(L["缺%d"], row.missing) or L["已备齐"]) + 10
            if w3 > missW then missW = w3 end
            local w5 = tw(row.gate and L["全程"] or format("%d+", row.at)) + 10
            if w5 > tagW then tagW = w5 end
            if row.src then
                local stext = row.src.vendor and (ns.ProfVendorNames and ns.ProfVendorNames[row.src.npcID]
                    or L["商人"]) or L["拍卖行"]
                local w4 = tw(stext) + 10
                if w4 > srcW then srcW = w4 end
                row.srcText = stext
            end
            if row.sold then anySold = true end
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
        local soldW = anySold and (tw(L["直售"]) + 10) or 0
        local xName = 8
        local xNum = xName + nameW + 10
        local xMiss = xNum + numW + 10
        local xSold = xMiss + missW + 8
        local xSrc = xSold + soldW + 8
        local maxScroll = math.max(0, #rows - SHOP_MAX)
        PF.shopScroll = math.max(0, math.min(PF.shopScroll or 0, maxScroll))
        local scroll = PF.shopScroll
        local needInner = xSrc + srcW + 10 + tagW + 14
        local baseInner = W_BASE - 2 * PAD - 16
        local newWide = (needInner > baseInner) and (needInner - baseInner) or nil
        if (newWide or 0) ~= (PF.wide or 0) then
            PF.wide = newWide
            C_Timer.After(0, PF.Paint)
        end
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
                nmFS:SetText(row.nm)
                num:SetText(format("%d/%d", math.min(row.have, row.need), row.need))
                nmFS:ClearAllPoints()
                nmFS:SetPoint("TOPLEFT", f.shop, "TOPLEFT", xName, ry)
                nmFS:Show()
                num:ClearAllPoints()
                num:SetPoint("TOPLEFT", f.shop, "TOPLEFT", xNum, ry)
                num:Show()
                if row.missing > 0 then
                    paintPill(mp, format(L["缺%d"], row.missing), xMiss, missW, Unpack(C_BAD))
                else
                    local okr, okg, okb = Unpack(C_OK)
                    paintPill(mp, L["已备齐"], xMiss, missW, okr, okg, okb, 0.5)
                end
                if row.sold then
                    paintPill(sp, L["直售"], xSold, soldW, Unpack(C_OK))
                else
                    sp:Hide()
                end
                if row.src and row.srcText then
                    local kr, kg, kb = Unpack(C_HEAD)
                    paintPill(srcp, row.srcText, xSrc, srcW, kr, kg, kb, 0.22)
                else
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
        PF.wide = nil
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

    if (PF.view or 0) ~= 0 and not finished then
        f.nowBtn:ClearAllPoints()
        f.nowBtn:SetPoint("BOTTOMRIGHT", f.card, "BOTTOMRIGHT", -6, 4)
    end
    if f.verifyBtn:IsShown() then
        f.verifyBtn:ClearAllPoints()
        f.verifyBtn:SetPoint("TOPRIGHT", f.btns[2], "TOPLEFT", -BTN_GAP, 0)
    end

    local by = y - 4
    f.btns[1]:ClearAllPoints()
    f.btns[1]:SetPoint("TOPLEFT", f, "TOPLEFT", PAD, by)
    f.craftBtn:ClearAllPoints()
    f.craftBtn:SetPoint("TOPLEFT", f.btns[1], "TOPRIGHT", BTN_GAP, 0)
    f.btns[3]:ClearAllPoints()
    f.btns[3]:SetPoint("TOPRIGHT", f, "TOPRIGHT", -PAD, by)
    f.btns[2]:ClearAllPoints()
    f.btns[2]:SetPoint("TOPRIGHT", f.btns[3], "TOPLEFT", -BTN_GAP, 0)

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
    TipOn(bt, text, L["将当前购物清单导入 Auctionator 的购物清单，只导入还缺的数量，同名清单将被覆盖。"])
    local ifs = bt.GetFontString and bt:GetFontString()
    if ifs then
        ifs:ClearAllPoints()
        ifs:SetPoint("CENTER", 0, -1)
        ifs:SetJustifyH("CENTER")
        ifs:SetTextColor(Unpack(C_GREY))
    end
    bt:SetShown(true)
end


-- A saved execution, rather than live skill alone, advances the HUD. Publication
-- callbacks wake a visible waiting HUD without replacing any frozen execution.
local function connectExecution()
    local XP = ns.ProfExecution
    if XP and XP.OnChanged then XP.OnChanged(function(slug, run, reason)
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
