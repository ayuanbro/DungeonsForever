-- =============================================================================
-- DungeonsForever · 专业升级 HUD（冲专业 1~300 跟随弹窗）
-- 跟随专业页当前路线逐段提示制作与购物清单，实时跟随技能进度；只对无限服加载。
-- =============================================================================

local _, ns = ...

if not ns.LoadForeverPages then return end

local Host = ns.ProfHost
if not Host then return end

local L = ns.L
local DG = Host.DG
local MakeFS, NewButton = Host.MakeFS, Host.NewButton
local SetOutline = Host.SetOutline

-- 专业图标：数据里是短名（trade_leatherworking），SetTexture 直接喂短名会静默失败
local function ProfIconTex(name)
    if not name then return Host.FALLBACK_ICON end
    if type(name) == "string" and not name:find("\\", 1, true) then
        return "Interface\\Icons\\" .. name
    end
    return name
end

-- 倒圆角描边（HUI 主题走 BuildRoundBorder；非 HUI 返回 nil，保留原方角 backdrop 描边）
local function RoundFrame(fr, radius, col)
    if not (ns.hui and ns.hui.BuildRoundBorder) then return nil end
    local pieces = ns.hui.BuildRoundBorder(fr, radius, col, fr, "OVERLAY", "both", 1) or {}
    for _, tex in ipairs(pieces) do tex:SetShown(true) end
    return pieces
end
local Unpack = Host.Unpack
local C_GOLD, C_GREY, C_DIM, C_TEXT = Host.C_GOLD, Host.C_GREY, Host.C_DIM, Host.C_TEXT

local D  = ns.ProfData
local R
local function RGet(k)
    if not R then
        local fn = ns.EnsureProfRecipes
        R = type(fn) == "function" and fn() or nil
    end
    return R and R[k] or nil
end
local LV = ns.ProfLeveling
local RA = ns.ProfRouteAuto   -- 自动路线计算（Core/ProfRouteAuto.lua，先于本文件加载）

local format = string.format

local PF = {}
ns.ProfFollow = PF

-- 「跳转制造」入口开关（2026-10-10 用户：功能暂缓先隐藏）。true = 恢复显示按钮；
-- 引擎（jumpCraft/openProfPanel）完整保留，随时可重开。
PF.CRAFT_BTN = false

-- -------------------------------------------------------------------------
-- 常量与小工具
-- -------------------------------------------------------------------------
local W, W_BASE = 352, 352      -- W 为当前有效宽（购物列超宽时加宽），W_BASE 为基准（352 = 底部四按钮排 92+92+66+66+3*4+2*PAD）
local PAD = 12
local BTN_W = { 92, 66, 66 }
local BTN_GAP = 4
local MAT_MAX = 6          -- 当前段最多直列材料行，其余进购物清单
local SHOP_MAX = 16
local SWEEP_MAX = 5        -- 懒加载名称重扫上限
local IMPORT_TRIES = 5     -- 一键导入物品名懒加载重试上限

local C_OK   = { 0.27, 0.75, 0.45 }
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

-- 该制作法术是否已学会（段卡右上角显示「已学习」的依据）
local function IsLearned(spellID)
    if not spellID then return false end
    local E=ns.ProfEconomy
    if E and E.Known then return E.Known(spellID)==true end
    if C_SpellBook and C_SpellBook.IsSpellKnown then
        local ok,r=pcall(C_SpellBook.IsSpellKnown,spellID)
        if ok and type(r)=="boolean" then return r end
    end
    if C_Spell and C_Spell.IsSpellKnown then
        local ok, r = pcall(C_Spell.IsSpellKnown, spellID)
        if ok and r then return true end
    end
    for _, name in ipairs({ "IsSpellKnown", "IsPlayerSpell" }) do
        local fn=_G[name]
        if type(fn) == "function" then
            local ok, r = pcall(fn, spellID)
            if ok and r then return true end
        end
    end
    return false
end

-- Only the manual craft-button guard reads carried materials. Route and shopping
-- quantities deliberately ignore all pre-existing bag and bank items.
local function HaveForCraft(id)
    if C_Item and C_Item.GetItemCount then
        local ok, n = pcall(C_Item.GetItemCount, id, false)
        if ok and type(n) == "number" then return n end
    end
    if type(GetItemCount) == "function" then
        local ok, n = pcall(GetItemCount, id, false)
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
    return (UnitName("player") or "?") .. "-" .. (GetRealmName() or "?")
end

-- 当前角色的跟随状态（收窗只标记 hidden，进度保留）
local function st()
    local p = dbProf()
    p.follow = p.follow or {}
    return p.follow[charKey()]
end

-- 技能当前值（复用专业页 ProfLearned；取不到返回 nil）
local function skillOf(slug)
    local PD = ns.ProfModule
    if PD and PD.ProfLearned then
        local learned = PD.ProfLearned()
        local e = learned[slug]
        if e then return e.cur, e.max end
    end
    return nil, nil
end

-- -------------------------------------------------------------------------
-- HUD 通过统一门面取得剩余路线。最省钱方案允许仅靠商人完成；
-- 等待计算或无解时保留自动模式，不能回落到违反排除限制的固定攻略。
-- -------------------------------------------------------------------------
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

-- 固定路线按「目标等级」裁剪（2026-10-11 用户：HUD 固定路线也要按我设的等级显示）。
--   口径与专业页 ClipFixedSteps 逐字一致：跨目标的段把止点裁到目标，
--   制作数量按 (目标−起)/(止−起) 比例折算并 ceil（最少 1）。target 为 nil / >=300 时原样返回。
--   ★ 自动路线不受影响：它的 opts.target 已在 Core/ProfRouteAuto.lua 内部 clamp。
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
        out[#out + 1] = { a, nb, st[3], nq, _clip = isClip or nil }
    end
    return out
end

local function validatePlan(result,slug)
    if result and RA and RA.ValidateVendorQuotes then result=RA.ValidateVendorQuotes(result) end
    if result and RA and RA.ValidateSpecializationPlan then result=RA.ValidateSpecializationPlan(result,slug) end
    return result
end
local function questGoal(seg) return seg.quest or seg.specializationGoal or seg.goal or seg end
local function questName(seg)
    local ability=questGoal(seg).abilityID
    return format(L["%s入门任务"],ability==20222 and L["地精工程学"] or L["侏儒工程学"])
end
local function questSource(seg)
    local goal=questGoal(seg)
    local place=goal.zone and L[goal.zone] or ""
    if goal.x and goal.y then place=place..format(" (%.1f, %.1f)",goal.x,goal.y) end
    local npc=goal.npcName and L[goal.npcName] or ("NPC #"..tostring(goal.npcID or "?"))
    local quest=goal.questName and ("《"..L[goal.questName].."》 ") or ""
    return npc..(place~="" and (" · "..place) or "").." · "..quest.."#"..tostring(goal.questID or "?")
end

-- 返回 mode("auto"/"fixed")、段落表及自动结果快照。
local function routeFor(slug, skill)
    local PD = ns.ProfModule
    local scheme = PD and PD.SettingRaw and PD.SettingRaw("autoScheme") or "cheapest"
    local fishRoute=slug=="cooking" and ((PD and PD.CookingFishingMode and PD.CookingFishingMode(slug))
        or dbProf().cookingRoute=="fishing" or (PD and PD.SettingRaw and PD.SettingRaw("cookingRoute")=="fishing"))
    if fishRoute then scheme="fishing" end
    -- 最省钱与乐观计数均不强制依赖拍卖行插件。
    if PD and PD.Setting and (fishRoute or PD.Setting("autoRoute")) and RA
       and (fishRoute or scheme == "cheapest" or scheme == "optim" or RA.Available()) then
        local opts = RA.OptionsFor and RA.OptionsFor(slug, skill) or {
            start = (PD.Setting("autoFromCurrent") and skill) and math.max(1, skill) or 1,
            onlyAH = PD.Setting("autoOnlyAH"),
            learnedOnly = PD.Setting("autoLearnedOnly"),
            target = routeTarget(slug),
            scheme = scheme,
        }
        opts.target = routeTarget(slug)
        if scheme == "cheapest" or scheme=="fishing" then
            -- 执行中的重算使用实际技能；购物数量始终按剩余路线计算。
            opts.start = math.max(1, skill or skillOf(slug) or 1)
            opts.follow = true
        end
        local res = RA.Get(slug, opts)
        if res and (res.status == "selection_required" or res.status == "recalculate_required") then
            return "auto", {}, res
        end
        local xp, following = ns.ProfExecution, st()
        if xp and xp.GetPlan and following and following.slug == slug then
            res = xp.GetPlan(slug) or res
        end
        res=validatePlan(res,slug)
        if res and res.status=="recalculate_required" then return "auto",{},res end
        if scheme == "cheapest" or scheme=="fishing" then
            return "auto", (res and (res.executionSteps or res.steps)) or {}, res
        end
        if res and (res.priced or scheme == "optim") then return "auto", res.executionSteps or res.steps, res end
    end
    local lv = LV[slug]
    -- ★ 固定路线必须按「目标等级」裁剪后再交给 HUD（2026-10-11 用户）。
    --   原先直接返回 lv.steps（全量 1–300）⇒ 专业页设了目标、HUD 却一路画到 300，
    --   段标分母 / 购物清单 / 完成判定全和专业页对不上。
    local fixed=clipFixedSteps(lv and lv.steps or nil, routeTarget(slug))
    if RA and RA.FilterFixedSpecializations then
        local blocked,goalRequired
        fixed,blocked,goalRequired=RA.FilterFixedSpecializations(slug,fixed or {},{target=routeTarget(slug)})
        if goalRequired or (blocked and #blocked>0) then
            return "auto",{},{planVersion=2,status="recalculate_required",feasible=false,specializationBlocked=true,
                message=L["固定攻略存在专精缺口，请切换自动计算。"]}
        end
    end
    local xp=ns.ProfExecution
    if xp and xp.NormalizePlan then
        local frozen=xp.GetPlan(slug)
        if frozen and frozen.mode=="fixed" then
            frozen=validatePlan(frozen,slug)
            if frozen.status=="recalculate_required" then return "auto",{},frozen end
            return "fixed",frozen.executionSteps,frozen
        end
        local normalized=xp.NormalizePlan(slug,{mode="fixed",steps=fixed or {},target=routeTarget(slug),feasible=true,status="complete"})
        if normalized and RA and RA.StampSpecializations then RA.StampSpecializations(normalized,slug,{target=routeTarget(slug)}) end
        if normalized then return "fixed",normalized.executionSteps,normalized end
    end
    return "fixed",fixed
end

-- 路线指纹：模式 + 段数 + 首末段（自动路线随价格 / 设置重算时用它决定要不要重推指针）
local function routeKey(mode, steps, res)
    if res and res.planVersion == 2 then
        return tostring(mode) .. ":v2:" .. tostring(res.revision or res.stamp or "pending")
    end
    if not steps then return tostring(mode) .. ":0" end
    local a, b = steps[1], steps[#steps]
    return format("%s:%d:%s:%s:%s", tostring(mode), #steps,
                  tostring(a and a[1]), tostring(a and a[3]), tostring(b and b[2]))
end

-- 技能推导段落：第一段「上限 > 技能」的；全过则 #steps + 1
local function derivedStep(slug, skill)
    local _, steps, res = routeFor(slug, skill)
    if not steps then return nil end
    -- 制材可能完全不涨点，另一专业的等级也不能和主专业比较。
    if res and res.planVersion == 2 then return 1 end
    for i, s in ipairs(steps) do
        if skill < s[2] then return i end
    end
    return #steps + 1
end

-- spellID → 配方行（rec[2] = 产出物 ID / rec[12] = 材料 / rec[13]+rec[14] = 来源）
-- rinfo 行（升级路线里配方表没有的法术：附魔配方 / 魔棒）用命名字段 makes / mats / learn…grey
local function recMats(rec) return rec and (rec[12] or rec.mats) or nil end
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
        -- 自动 / 固定路线都可能引用 rinfo 里的法术（附魔配方游离在 enchants 之外、魔棒两头都不在）
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

local function stepRecipe(seg, res, slug)
    local base = recMap(seg.profession or slug)[seg[3]]
    if not (res and res.planVersion == 2) then return base end
    local rec = {}
    for key, value in pairs(base or {}) do rec[key] = value end
    if seg.recipe then
        rec[2], rec.makes = seg.recipe.item, seg.recipe.item
        rec[12], rec.mats = seg.recipe.mats, seg.recipe.mats
        rec.count, rec.dataSource = seg.recipe.count, seg.recipe.dataSource
        return rec
    end
    -- HUD 和制造按钮使用发布快照中的材料，不再从攻略二次推算。
    rec[2], rec.makes = seg.item, seg.item
    rec[12], rec.mats = nil, nil
    for _, action in ipairs(res.actions or {}) do
        if action.type == "craft" and action.profession == (seg.profession or slug)
            and action.spell == seg[3] and action.inputs then
            local mats = {}
            for _, mat in ipairs(action.inputs) do
                mats[#mats + 1] = { mat[1], mat[2] / math.max(1, action.count or 1) }
            end
            rec[12], rec.mats = mats, mats
            rec[2], rec.makes = action.item or seg.item, action.item or seg.item
            return rec
        end
    end
    local rt = ns.ProfRecipeRuntime and ns.ProfRecipeRuntime[seg[3]]
    if rt then rec[12], rec.mats = rt.mats, rt.mats; rec[2] = rt.item or seg.item end
    return rec
end

local function fmtTime(sec)
    local m = math.floor(sec / 60)
    local s = math.floor(sec % 60)
    return format(L["用时 %d 分 %d 秒"], m, s)
end

-- -------------------------------------------------------------------------
-- 跟随引擎
-- -------------------------------------------------------------------------
function PF.IsActive(slug)
    local s = st()
    return (s and s.slug == slug and not s.hidden) and true or false
end

function PF.Following(slug)
    local s = st()
    return (s and s.slug == slug) and true or false
end

local function actionKey(seg, i)
    return seg.segmentID or seg.actionID or format("%d:%s:%s", i or 0, seg.profession or "", tostring(seg[3]))
end

local function executionProgress(s, seg, i)
    local xp = ns.ProfExecution
    if xp and xp.Progress and xp.GetRun and xp.GetRun(s.slug) then
        return xp.Progress(s.slug, seg.segmentID or i)
    end
end

local function actionRemaining(s, seg, i)
    local progress = executionProgress(s, seg, i)
    if progress then return math.max(0, progress.remainingCrafts or 0) end
    return math.max(0, (seg[4] or 0) - ((s.actionDone and s.actionDone[actionKey(seg, i)]) or 0))
end

local function syncActions(s, steps, res)
    -- 计数只属于同一输入快照。重算已把实际技能写进新状态，不能再次扣计数。
    if PF.planRef ~= res or PF.planSlug ~= s.slug or PF.planRevision ~= res.revision then
        PF.planRef, PF.planSlug, PF.planRevision = res, s.slug, res.revision
        s.actionDone = {}
        s.step = 1
        PF.view = 0
    end
    while (s.step or 1) <= #steps do
        local i = s.step or 1
        local seg = steps[i]
        local complete
        if seg.checkpoint or seg[3] == 0 then
            local cur = skillOf(seg.profession or s.slug)
            complete = cur and cur >= seg[2]
        else
            complete = actionRemaining(s, seg, i) <= 0
        end
        if not complete then break end
        s.step = i + 1
    end
end

-- 一次成功施法对应一次制造，不按产物件数计算。castGUID 去重避免重复事件。
function PF.CraftSucceeded(unit, castGUID, spellID)
    if unit ~= "player" or type(spellID) ~= "number" then return end
    local s = st()
    local xp = ns.ProfExecution
    if s and xp and xp.GetRun and xp.GetRun(s.slug) then
        xp.RecordAttempt(s.slug, spellID, castGUID)
        PF.Sync()
        return
    end
    if xp then return end -- Unmigrated snapshots cannot safely accept execution facts.
    if not (s and s.slug and PF.planRef and PF.planRef.planVersion == 2) then return end
    if castGUID and castGUID == PF.lastCastGUID then return end
    if castGUID then PF.lastCastGUID = castGUID end
    local res = PF.planRef
    local steps = res.executionSteps or res.steps or {}
    local i = s.step or 1
    local seg = steps[i]
    if not seg or seg.checkpoint or seg[3] ~= spellID then return end
    s.actionDone = s.actionDone or {}
    local key = actionKey(seg, i)
    s.actionDone[key] = math.min(seg[4] or 0, (s.actionDone[key] or 0) + 1)
    syncActions(s, steps, res)
end

function PF.Sync()
    local s = st()
    if not (s and s.slug) then return end
    PF.executionNotice = nil
    local cur = skillOf(s.slug)
    if cur and cur ~= s.skill then
        s.skill = cur
        -- 技能涨了：若手册停在同一个专业的升级页，顺手重画高亮
        local PD = ns.ProfModule
        if PD and PD.built and PD.cur == s.slug and PD.page and PD.page:IsVisible() then
            pcall(PD.Render, PD)
        end
    end
    -- 路线模式 / 路线内容变了（自动路线随价格、设置重算）：段落表整块换掉，指针按技能重推
    local mode, steps, res = routeFor(s.slug, s.skill or 0)
    local xp = ns.ProfExecution
    if res and (res.planVersion == 2 or res.executionVersion==1) and xp and xp.Bind and xp.Sync then
        -- Bind freezes a durable execution snapshot. Search publication/revision
        -- changes never replace its segment counters or current position.
        local run, reason = xp.GetRun(s.slug)
        if run or res.feasible == true then run, reason = xp.Bind(s.slug, res) end
        if run then
            run = xp.Sync(s.slug) or run
            local plan = xp.GetPlan(s.slug) or res
            PF.planRef, PF.planSlug = plan, s.slug
            PF.planRevision = plan.planID
            s.planID = plan.planID or run.planID
            s.rkey = tostring(s.planID or "execution")
            s.step = run.currentIndex or run.step or 1
            return
        end
        if reason == "migration_required" then
            PF.executionNotice = L["旧路线缺少执行信息，请重新计算后继续跟随。"]
            return
        end
        if reason == "specializationChanged" then
            PF.executionNotice = L["专精选择或学习条件已更改，请重新计算。"]
            return
        end
    end
    local key = routeKey(mode, steps, res)
    if res and res.planVersion == 2 then
        s.rkey = key
        syncActions(s, steps, res)
        return
    end
    PF.planRef, PF.planSlug, PF.planRevision = nil, nil, nil
    if key ~= s.rkey then
        s.rkey = key
        s.step = derivedStep(s.slug, s.skill or 0) or 1
        PF.view = 0
    end
    local d = derivedStep(s.slug, s.skill or 0)
    if d and d > (s.step or 1) then s.step = d end
end

-- 目标等级变了 ⇒ 固定路线的段落表随之变短/变长，HUD 需要立刻按新目标重推指针并重画。
--   PF.Sync 里已有「设置变更 ⇒ 同步到专业页」的反向联动，这里补正向（专业页改完
--   只会 pcall(PD.Render) 重画专业页，HUD 的 rkey 不会自动刷新）。
function PF.RefreshRoute(slug)
    local s = st()
    if not (s and s.slug) then return end
    if slug and slug ~= s.slug then return end
    PF.Sync()
    if PF.f and PF.f:IsShown() then pcall(PF.Paint) end
end

function PF.Toggle(slug)
    if not (slug and LV[slug] and LV[slug].steps) then return end
    local p = dbProf()
    p.follow = p.follow or {}
    local k = charKey()
    local s = p.follow[k]
    if s and s.slug ~= slug then s = nil end      -- 执行记录由 ProfExecution 逐专业保留。
    -- 已在跟随该专业且窗口可见 → 收窗（进度保留）
    if s and not s.hidden and PF.f and PF.f:IsShown() then
        s.hidden = true
        PF.f:Hide()
        return
    end
    if not s then
        local cur = skillOf(slug) or 0
        s = { slug = slug, skill = cur, step = derivedStep(slug, cur) or 1, t0 = time() }
        local _mode, _steps, _res = routeFor(slug, cur)
        s.rkey = routeKey(_mode, _steps, _res)
        p.follow[k] = s
    end
    s.hidden = nil
    PF.Build()
    if not PF.f then return end       -- Build 未建窗（异常兜底），不往下走
    PF.Sync()
    PF.view = 0
    PF.f:Show()                       -- Paint 对隐藏窗口早退，必须先 Show 再画
    PF.Paint()
end

-- 上一步 / 跳过只动浏览偏移（与滚轮同轨，不碰真实指针）；技能一涨 Sync 仍自动推进（卡不死）
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

function PF.ReturnToCurrent()
    PF.Sync()
    PF.view = 0
    PF.Paint()
end

-- -------------------------------------------------------------------------
-- 剩余制作次数估算（按配方橙/黄/绿/灰断点的升点概率模型）
-- 经典概率口径：橙色必升（1次/点）；黄色段 1.0→0.5 线性；绿色段 0.5→0.05 线性；灰色不升
-- -------------------------------------------------------------------------
local function expPerPoint(sk, o, y, g, gr)
    if RA and RA.Gain then
        local gain = RA.Gain(sk, o, y, g, gr)
        return gain and gain > 0 and (1 / gain) or nil
    end
    if sk < y then return 1 end
    if sk < g then return 1 / (1 - 0.5 * (sk - y) / (g - y)) end
    if sk < gr then return 1 / (0.5 - 0.45 * (sk - g) / (gr - g)) end
    return nil -- 已灰，无法升点
end

-- 当前段还需制作次数：优先按难度断点逐点积分期望值；配方无断点数据或已灰时退回区间占比线性估算
local function craftsLeft(seg, skill, rec)
    if seg.segmentID or seg.actionID then
        local s = st()
        return s and actionRemaining(s, seg, s.step) or (seg[4] or 0)
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
        -- 循环没被灰色打断才采用概率口径（打断说明中途已灰，退回线性口径）
        if expPerPoint(seg[2] - 1, learn, y, g, gr) then return total end
    end
    local span = math.max(1, seg[2] - seg[1])
    return (seg[4] or 0) * math.min(1, (seg[2] - from) / span)
end

-- -------------------------------------------------------------------------
-- 购物清单（从当前段累计材料采购量，不扣除角色库存）
-- -------------------------------------------------------------------------
local function shopList(s, kind)
    local _, steps, res = routeFor(s.slug, s.skill)
    if kind == "supplement" then
        local xp = ns.ProfExecution
        res = xp and xp.GetSupplement and xp.GetSupplement(s.slug)
        if not res then return {} end
        res=validatePlan(res,s.slug)
        -- Supplemental procurement is a separate, shared snapshot. It never
        -- changes the original quantities or reuses its import list.
        steps = res.executionSteps or res.steps
    end
    local function purchaseSnapshot(entry, purchase)
        for _, key in ipairs({"availableCount", "supplyObserved", "supplyComplete", "supplyObservedAt",
                              "supplySource", "supplyOwnerExcluded", "supplyObservedPrice",
                              "supplyHistoryQuantity", "supplyHistoryObservedAt", "priceObservedAt", "ahPrice",
                              "cost", "unit", "bundleSize", "bundlePrice", "priceSource", "quoteSource",
                              "priceBasis", "reference", "estimated", "url", "unpriced"}) do
            purchase[key] = entry[key]
        end
        return purchase
    end
    local function addFormulas(list,formulas)
        for _,entry in ipairs(formulas or {}) do
            if entry.id and not entry.known and entry.usable~=false and not entry.blocked then
                list[#list+1]=purchaseSnapshot(entry,{id=entry.id,need=entry.count or 1,formula=true,
                    source=entry.source,vendor=entry.vendor or entry.source=="vendor" or entry.source=="npc",npcID=entry.npcID,
                    unpriced=entry.unpriced,remainingOnly=true})
            end
        end
        return list
    end
    local function purchases(snapshot)
        local list = {}
        for _, entry in ipairs(snapshot.mats or {}) do
            local id = entry.id or entry[1]
            local need = entry.count or entry.need or entry[2] or 0
            if id and need > 0 then
                list[#list + 1] = purchaseSnapshot(entry, {
                    id = id, need = need,
                    at = entry.at or (snapshot.firstAt and snapshot.firstAt[id]) or 0,
                    source = entry.source or (entry.vendor and "vendor" or "ah"),
                    vendor = entry.vendor, npcID = entry.npcID,
                    remainingOnly = true,
                })
            end
        end
        for _,entry in ipairs(snapshot.fishMaterials or {}) do
            list[#list+1]={id=entry.id,need=entry.count or entry.need,source="fishing",remainingOnly=true,
                areas=entry.areas,at=snapshot.firstAt and snapshot.firstAt[entry.id]}
        end
        return addFormulas(list,snapshot.formulas)
    end
    if res and (res.planVersion == 2 or kind == "supplement") then
        if res.feasible ~= true then return {} end
        return purchases(res)
    end
    if not steps then return {} end
    local rm = recMap(s.slug)
    local totals, order, remaining = {}, {}, {}
    for i = (s.step or 1), #steps do
        local seg = steps[i]
        local rec = rm[seg[3]]
        local mats = recMats(rec)
        local crafts = seg[4] or 0
        if i == s.step then
            crafts = math.ceil(craftsLeft(seg, s.skill, rec))
        end
        if mats and crafts > 0 then
            local step = {}
            for key,value in pairs(seg) do step[key]=value end
            step[4]=crafts
            remaining[#remaining+1]=step
            for _, m in ipairs(mats) do
                local e = totals[m[1]]
                if not e then
                    e = { id = m[1], need = 0, at = seg[1] }
                    totals[m[1]] = e
                    order[#order + 1] = m[1]
                end
                e.need = e.need + (m[2] or 1) * crafts
            end
        end
    end
    -- Fixed routes use the same selected procurement batches as the main
    -- shopping page, after reducing only the current segment's craft count.
    -- A known merchant does not make its quote preferable to an AH purchase.
    if RA and RA.SummarizeSteps then
        local summary=RA.SummarizeSteps(remaining,s.slug)
        if summary then return purchases(summary) end
    end
    -- 按攻略里材料的首次出现顺序输出（不按缺口大小排序）
    local list = {}
    for _, id in ipairs(order) do
        local e = totals[id]
        e.unpriced=true
        list[#list + 1] = e
    end
    local economy=ns.ProfEconomy
    local formulas=res and res.formulas
    if not formulas and economy and economy.CollectFormulas then
        formulas=economy.CollectFormulas(remaining,s.slug)
    end
    addFormulas(list,formulas)
    if economy and economy.SummarizeAuctionSupply then
        economy.SummarizeAuctionSupply({mats=list})
    end
    return list
end

-- 与主界面导出复用同一采购快照，便于诊断及离线验收。
PF.GetRoute = routeFor
PF.GetPurchases = shopList

local function routeNotice(res)
    if res and (res.message or res.blockedReason) then return res.message or res.blockedReason end
    if res and res.status == "selection_required" then return L["请选择搭配的主专业"] end
    if res and res.status == "recalculate_required" then
        for _,d in ipairs(res.diagnostics or {}) do
            if (d.code=="vendorQuoteChanged" or d.code=="specializationChanged")
               and ns.ProfEconomy and ns.ProfEconomy.DiagnosticText then
                return ns.ProfEconomy.DiagnosticText(d)
            end
        end
        return L["搭配专业已更改，点击重新计算应用。"]
    end
    if res and res.partial then return format(L["已计算至 %d；后续路线待补全"],res.plannedTo or res.start or 1) end
    for _, d in ipairs((res and res.diagnostics) or {}) do
        if d.code == "clientDataPending" then return L["客户端数据待读取"] end
    end
    if res and (res.status == "infeasible" or res.status == "blocked" or res.status == "error") then
        return L["当前限制下没有可行路线"]
    end
    return L["正在计算升级路线…"]
end

-- -------------------------------------------------------------------------
-- 一键导入拍卖行插件（主界面按钮 + HUD 购物清单按钮共用）
-- -------------------------------------------------------------------------
-- tooltip 双行（标题 + 说明）；两个导入按钮共用
local function TipOn(bt, title, body)
    bt:SetScript("OnEnter", function(self)
        GameTooltip:SetOwner(self, "ANCHOR_TOP")
        GameTooltip:ClearLines()
        GameTooltip:AddLine(title, 1, 0.82, 0, true)
        if body then GameTooltip:AddLine(body, 1, 1, 1, true) end
        GameTooltip:Show()
    end)
    bt:SetScript("OnLeave", function() GameTooltip:Hide() end)
end

-- -------------------------------------------------------------------------
-- 跳转制造（2026-10-10 用户定案）：定时器/事件上下文的自动制造被无限服硬拦
-- （4 通道轮换全 ADDON_ACTION_BLOCKED，非战斗也拦）——插件侧自动施法无解，
-- 合法方案 = 按钮点击（硬件事件）：打开专业面板 → 定位当前段配方 → 预填数量，
-- 玩家在面板内点一次「制造」即批量完成。
-- ★ 无限服 = 现代专业框架（ProfessionsFrame + C_TradeSkillUI + C_SpellBook）：
--   - C_TradeSkillUI.OpenTradeSkill 的参数是 skillLineID（GetProfessionInfo
--     第 7 个返回值），不是 GetProfessions() 的 index —— 传 index 会静默空转
--     （我们最初「面板打不开」的根因）
--   - 施法兜底走法术书扫描出的「制作入口法术」
-- -------------------------------------------------------------------------
local function craftNotify(msg)
    if DEFAULT_CHAT_FRAME then
        DEFAULT_CHAT_FRAME:AddMessage("|cff33ff99无限副本手册:|r " .. msg, 1, 1, 1)
    end
end

local jumpPending   -- { spellID, count, name } 待定位的配方（面板打开后消费）
local jumpEvt
local jumpApply     -- 前置声明：jumpEvtInit 闭包引用它（Lua5.1 前向引用坑）

local function jumpEvtInit()
    if jumpEvt or not CreateFrame then return end
    jumpEvt = CreateFrame("Frame")
    -- ★ 无限服没有 TRADE_SKILL_UPDATE 事件（实测 RegisterEvent 报 unknown），
    --   pcall 逐个注册，缺的静默跳过；定位另有 0.5s/1.5s 延时兜底
    pcall(function() jumpEvt:RegisterEvent("TRADE_SKILL_LIST_UPDATE") end)
    jumpEvt:SetScript("OnEvent", function()
        C_Timer.After(0, function()
            if jumpPending then jumpApply() end
        end)
    end)
end

-- 面板已开验证（现代帧名优先，兜底旧经典帧名）
local function panelShown()
    local pf = _G.ProfessionsFrame
    if pf and pf.IsShown and pf:IsShown() then return true end
    local tf = _G.TradeSkillFrame
    return (tf and tf.IsShown and tf:IsShown()) or false
end

-- 从法术书找专业的「制作入口法术」ID
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

-- 打开专业面板（点击上下文 = 硬件事件，合法）：
--   A) OpenTradeSkill(skillLineID)
--   B) 法术书入口法术施放（运行时施法版）
--   C) CastSpellByName(专业名) —— 最后兜底
local function openProfPanel(s)
    local profName = D.pro and D.pro[s.slug] and D.pro[s.slug].name
    local ids = (GetProfessions and { GetProfessions() }) or {}
    if C_TradeSkillUI and C_TradeSkillUI.OpenTradeSkill and type(GetProfessionInfo) == "function" then
        for _, idx in ipairs(ids) do                     -- 名字匹配的优先
            if idx then
                local nm, _, _, _, _, _, skillLine = GetProfessionInfo(idx)
                if profName and nm == profName and skillLine
                    and pcall(C_TradeSkillUI.OpenTradeSkill, skillLine) then
                    return true
                end
            end
        end
    end
    for _, idx in ipairs(ids) do                         -- B) 入口法术
        if idx then
            local nm = GetProfessionInfo and GetProfessionInfo(idx)
            local sid = (nm == profName) and CraftingEntrySpellID(idx) or nil
            local nm = sid and SpellName(sid)
            if nm and CastSpellByName and pcall(CastSpellByName, nm) then return true end
            if sid and C_Spell and C_Spell.CastSpell and pcall(C_Spell.CastSpell, sid) then return true end
        end
    end
    if profName and CastSpellByName then                 -- C) 专业名
        pcall(CastSpellByName, profName)
        return true
    end
    return false
end

function jumpApply()     -- 配合上方前置声明（function 不带 local，避免遮蔽）
    local p = jumpPending
    if not p then return end
    local selected, counted = false, false
    if C_TradeSkillUI then
        -- 现代通道：定位配方 → 预填重复次数 → 读回校验（防「pcall 成功但静默空转」）
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
    -- 经典通道兜底（按名字找行）
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
    -- 两者都没成：面板可能还在加载，等事件/下一轮兜底再试
end

local function jumpCraft()
    local s = st()
    if not (s and s.slug) then return end
    local _, steps, res = routeFor(s.slug, s.skill)
    local seg = steps and steps[(s.step or 1)]
    if not seg then return end
    if seg.checkpoint or seg[3] == 0 then return end
    local spellID = seg[3]
    if not IsLearned(spellID) then craftNotify(L["该配方还未学会，先找训练师学习"]) return end
    local stepSlug = seg.profession or s.slug
    local rec = stepRecipe(seg, res, stepSlug)
    local mats = recMats(rec)
    if mats then
        for _, m in ipairs(mats) do
            if (HaveForCraft(m[1]) or 0) < (m[2] or 1) then
                craftNotify(L["材料不足，先按购物清单备齐再制造"]) return
            end
        end
    end
    local count = math.max(1, math.ceil(craftsLeft(seg, skillOf(stepSlug) or s.skill, rec)))
    local name = SpellName(spellID)
    if not name then craftNotify(L["配方数据未就绪，稍后再试"]) return end
    jumpEvtInit()
    if openProfPanel({ slug = stepSlug }) then
        jumpPending = { spellID = spellID, count = count, name = name }
        craftNotify(format(L["正在打开专业面板并定位 %s（预填数量 %d）…"], name, count))
        if C_Timer and C_Timer.After then
            C_Timer.After(0.5, function() if jumpPending then jumpApply() end end)  -- 面板已开时无新事件，延时兜底
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

-- 推送当前专业的购物清单到拍卖行插件（经 ns.AuctionBridge）。
-- 跟随中用真实指针；没跟随用临时态推导，不落盘、不动进度。
-- 物品名没就绪（客户端物品库懒加载）先请求，1 秒后重试，最多 IMPORT_TRIES 次。
local importTries = 0
local function DoImport(slug, profName, kind)
    if not (LV[slug] and LV[slug].steps) then return end
    local baseName = profName
    local s0 = st()
    local tmp
    if s0 and s0.slug == slug then
        tmp = s0
    else
        local cur = skillOf(slug) or 0
        tmp = { slug = slug, skill = cur, step = derivedStep(slug, cur) or 1 }
    end
    local mode, _, result = routeFor(slug, tmp.skill)
    if kind == "supplement" then
        local xp = ns.ProfExecution
        result = xp and xp.GetSupplement and xp.GetSupplement(slug)
        result=validatePlan(result,slug)
        if not result or result.inFlight or result.stale or result.feasible ~= true then
            craftNotify(L["补料尚未计算完成"])
            return
        end
        profName = profName .. " · " .. L["补料清单"]
    end
    if mode == "auto" and (not result or (result.planVersion == 2 and result.feasible ~= true)) then
        craftNotify(routeNotice(result))
        return
    end
    local list = shopList(tmp, kind)
    local items, missing = {}, 0
    for _, e in ipairs(list) do
        local isAH = not e.unpriced and not e.vendor and (e.source == "ah" or e.source == "auction")
        local nm, got
        if isAH then nm, got = DG.ItemName(e.id) end
        if not isAH then
            -- 商人采购不进入拍卖行导入串。
        elseif not got then
            missing = missing + 1
            DG.RequestItem(e.id)
        else
            if e.need > 0 then
                items[#items + 1] = { name = nm, need = e.need }
            end
        end
    end
    if missing > 0 and importTries < IMPORT_TRIES then
        importTries = importTries + 1
        C_Timer.After(1, function() DoImport(slug, baseName, kind) end)
        return
    end
    importTries = 0
    if ns.AuctionBridge and ns.AuctionBridge.DoImport then
        ns.AuctionBridge.DoImport(profName, items)
    end
end

-- -------------------------------------------------------------------------
-- HUD 窗体（一次建好，之后只改内容）
-- -------------------------------------------------------------------------
local f

local rowsMat, rowsShop = {}, {}
local rowsMatIcon = {}          -- 材料行图标池（与 rowsMat 同索引）
local rowsMatBadge = {}         -- 材料行数量角标池（挂图标右下角，显示单次用量）
local rowsShopNum = {}          -- 采购数量列
local rowsShopSourcePill, rowsShopTagPill = {}, {}   -- 采购来源和首次使用等级

function PF.CalculateSupplement()
    local s, xp = st(), ns.ProfExecution
    if not (s and xp and xp.CalculateSupplement and xp.GetRun(s.slug)) then return end
    PF.shopKind, PF.showShop, PF.shopScroll = "supplement", true, 0
    xp.CalculateSupplement(s.slug, function()
        PF.Sync()
        if PF.f and PF.f:IsShown() then PF.Paint() end
    end)
    PF.Sync()
    PF.Paint()
end

function PF.VerifyCurrentOutput(total)
    local s, xp = st(), ns.ProfExecution
    if not (s and xp and xp.GetPlan and xp.VerifyOutput) then return false end
    local plan = xp.GetPlan(s.slug)
    local steps = plan and (plan.executionSteps or plan.steps)
    local seg = steps and steps[s.step or 1]
    if not seg then return false end
    local progress = executionProgress(s, seg, s.step)
    local item = progress and progress.outputItem or seg.item or (seg.recipe and seg.recipe.item)
    total = tonumber(total)
    if not item or not total or total < 0 or total ~= math.floor(total) then return false end
    local ok = xp.VerifyOutput(s.slug, seg.segmentID or s.step, item, total)
    PF.ReturnToCurrent()
    return ok ~= false
end

local function showOutputVerification()
    local s, xp = st(), ns.ProfExecution
    if not (s and xp and xp.GetPlan and StaticPopupDialogs and StaticPopup_Show) then return end
    local plan = xp.GetPlan(s.slug)
    local steps = plan and (plan.executionSteps or plan.steps)
    local seg = steps and steps[s.step or 1]
    if not seg then return end
    local progress = executionProgress(s, seg, s.step)
    local item = progress and progress.outputItem or seg.item or (seg.recipe and seg.recipe.item)
    if not item then return end
    -- Save identity in the dialog. A skill/event update while it is open must
    -- never apply the player's correction to a different segment.
    local data = {slug=s.slug, segmentID=seg.segmentID or s.step, item=item,
        actual=progress and progress.actualOutputs or 0}
    StaticPopupDialogs.DF_PROF_VERIFY_OUTPUT = {
        text=L["填写本步骤累计实际产出件数（不是当前背包数量）。"],
        button1=L["确认"], button2=L["取消"], hasEditBox=true,
        timeout=0, whileDead=true, hideOnEscape=true, preferredIndex=3,
        OnShow=function(self)
            local edit = self.editBox or (self.GetEditBox and self:GetEditBox())
            if edit then
                edit:SetText(tostring((self.data and self.data.actual) or 0))
                edit:SetFocus()
                edit:HighlightText()
            end
        end,
        OnAccept=function(self)
            local d = self.data
            local edit = self.editBox or (self.GetEditBox and self:GetEditBox())
            local n = edit and tonumber(edit:GetText())
            if not (d and n and n >= 0 and n == math.floor(n)) then return end
            xp.VerifyOutput(d.slug, d.segmentID, d.item, n)
            PF.ReturnToCurrent()
        end,
    }
    StaticPopup_Show("DF_PROF_VERIFY_OUTPUT", nil, nil, data)
end

local function MakeLine(parent, fs, color)
    local t = MakeFS(parent, fs, color, "LEFT")
    t:SetWordWrap(false)
    t:Hide()
    return t
end

function PF.Build()
    if f then return end

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
    f:SetScript("OnEvent", function(_, event, ...)
        if event == "UNIT_SPELLCAST_SUCCEEDED" and not ns.ProfExecution then
            PF.CraftSucceeded(...)
        end
        if f:IsShown() then
            C_Timer.After(0, function()
                PF.Sync()
                PF.Paint()
            end)
        end
    end)
    for _, event in ipairs({ "BAG_UPDATE_DELAYED", "CHAT_MSG_SKILL", "UNIT_SPELLCAST_SUCCEEDED",
                             "TRADE_SKILL_LIST_UPDATE", "SKILL_LINES_CHANGED", "PLAYERBANKSLOTS_CHANGED" }) do
        pcall(f.RegisterEvent, f, event)
    end

    f:SetBackdrop({
        bgFile = "Interface\\Buttons\\WHITE8x8",
        edgeFile = "Interface\\Buttons\\WHITE8x8",
        edgeSize = 1,
    })
    -- 背景与主界面同源（DG.RowPaint 口径）：HUI 走 L2 层色，非 HUI 黑底
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

    -- 头部（固定）：图标 / 标题 / 技能行 / 进度条
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

    f.seg = MakeFS(f, 16, C_GREY, "RIGHT")
    f.seg:SetPoint("TOPRIGHT", f, "TOPRIGHT", -10, -42)

    f.barBG = f:CreateTexture(nil, "BACKGROUND")
    f.barBG:SetColorTexture(1, 1, 1, 0.12)
    f.barBG:SetPoint("TOPLEFT", f, "TOPLEFT", 10, -66)
    f.barBG:SetSize(W - 20, 5)

    f.zone = f:CreateTexture(nil, "OVERLAY")   -- 当前段区间（黄色段，进度色压在其上）
    f.zone:SetColorTexture(1, 1, 1, 1)
    f.zone:SetPoint("TOPLEFT", f, "TOPLEFT", 10, -66)
    f.zone:SetSize(1, 5)

    f.bar = f:CreateTexture(nil, "OVERLAY")
    f.bar:SetColorTexture(1, 1, 1, 1)
    f.bar:SetPoint("TOPLEFT", f, "TOPLEFT", 10, -66)
    f.bar:SetSize(1, 5)

    -- 当前段卡（绿描边小面板）。卡中卡提亮：HUI 主题下主卡是 L2，内卡用 L3 实色；
    -- 非 HUI 沿用白 overlay。
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

    -- 段卡悬停 → 产物物品提示框 + 五行价格段（2026-10-10 用户：提示框三页通用）。
    --   __it/__mats 由 Paint 每拍刷新；价格段走 ns.ProfModule（PD）惰性取，避免加载环。
    f.card:EnableMouse(true)
    f.card:SetScript("OnEnter", function(self)
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
    f.card.progress = {}
    for i = 1, 6 do
        local line = MakeFS(f.card, 13, C_GREY, "LEFT")
        line:SetWordWrap(false)
        line:Hide()
        f.card.progress[i] = line
    end

    f.card.srcTag = MakeFS(f.card, 14, C_GREY, "RIGHT")
    f.card.srcTag:SetWordWrap(false)
    f.card.srcTag:SetPoint("TOPRIGHT", f.card, "TOPRIGHT", -8, -9)

    f.card.matHead = MakeFS(f.card, 14, C_GREY, "LEFT")
    f.card.matHead:SetPoint("TOPLEFT", f.card, "TOPLEFT", 8, -56)

    for i = 1, MAT_MAX + 1 do
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

    -- 购物清单（灰描边小面板，展开 / 收起）。同上：HUI 主题内卡提亮到 L3。
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
    f.shop.head = MakeFS(f.shop, 14, C_HEAD, "LEFT")
    f.shop.head:SetPoint("TOPLEFT", f.shop, "TOPLEFT", 8, -8)
    -- Material-only purchasing has no owned/missing toggle.
    f.shop.head:SetPoint("RIGHT", f.shop, "RIGHT", -86, 0)
    f.shop.head:SetWordWrap(false)
    f.shop.summary = MakeFS(f.shop, 13, C_GREY, "LEFT")
    f.shop.summary:SetWordWrap(false)
    f.shop.summary:SetPoint("TOPLEFT", f.shop, "TOPLEFT", 8, -28)
    f.shop.summary:Hide()
    f.shop.empty = MakeFS(f.shop, 14, C_GREY, "LEFT")
    f.shop.empty:SetPoint("TOPLEFT", f.shop, "TOPLEFT", 8, -30)
    f.shop.empty:Hide()
    -- 滚轮滚动购物清单（全部收录 + 右缘滚动条）
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
    for i = 1, SHOP_MAX + 1 do
        rowsShop[i] = MakeLine(f.shop, 14, C_TEXT)      -- 名字（白）
        rowsShopNum[i] = MakeLine(f.shop, 14, C_GOLD)   -- 采购数量（金）
        -- UI_RULES §4 胶囊小件（2026-10-11 用户重做）：旧「三段贴图压帽 + 0.99 预混」整体退役。
        --   新做法 = 专用宿主帧 + BuildCapsule（四角/边条**锚定帧角**，SetSize 改宽自动跟随，
        --   无缝无重叠 ⇒ 不再有预混/不透明批烦恼）；文字挂宿主帧自己的 FontString（ARTWORK
        --   画在胶囊之上，§5-2「父 FontString 永远画在子帧下」由此规避）。
        --   染色 = 每帧遍历 __cols SetVertexColor（语义色 C_BAD/C_OK 不变，§6）。
        local function MakePill(color)
            local p = CreateFrame("Frame", nil, f.shop)
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
            p.fs:SetAllPoints(p)
            p.fs:SetWordWrap(false)
            p:Hide()
            return p
        end
        rowsShopSourcePill[i] = MakePill(C_TEXT)   -- NPC/拍卖行采购来源
        rowsShopSourcePill[i]:EnableMouse(true)
        rowsShopSourcePill[i]:SetScript("OnEnter", function(self)
            local entry = self.__purchase
            if not entry then return end
            local PD = ns.ProfModule
            local extra = {{format(L["需要：%d"], entry.need or 0)}}
            if PD and PD.AuctionSupplyLines then
                for _, line in ipairs(PD.AuctionSupplyLines(entry)) do extra[#extra + 1] = line end
            end
            DG.ShowItemTip(self, {entry.id}, extra)
        end)
        rowsShopSourcePill[i]:SetScript("OnLeave", function() GameTooltip:Hide() end)
        rowsShopTagPill[i] = MakePill(C_DIM)     -- 等级丸 X+（灰字压淡灰底）
    end

    -- 一键导入：把当前购物清单推送到拍卖行插件（未装时降级为导入串弹窗）。
    -- 2026-10-08 晚改版：从购物面板页脚挪到底部按钮排（购物清单与上一步之间），
    -- 尺寸 / 字号与「购物清单」按钮完全一致（92×22 / 14 号）。
    -- 导入按钮位于购物清单表头右侧。
    f.shopImp = NewButton(f.shop, L["一键导入"], 66, 20, 13)
    f.shopImp.__huiKeepTextColor = true
    f.shopImp:SetScript("OnClick", function()
        local s0 = st()
        if not (s0 and s0.slug) then return end
        local nm = (D.pro and D.pro[s0.slug] and D.pro[s0.slug].name) or s0.slug
        DoImport(s0.slug, nm, PF.shopKind)
        ns.PlaySound(1)
    end)
    f.shopImp:SetPoint("TOPRIGHT", f.shop, "TOPRIGHT", -6, -4)
    TipOn(f.shopImp, L["一键导入到拍卖行"],
          L["将路线选定的拍卖行采购数量导入 Auctionator，同名清单将被覆盖。"])

    -- 「跳转制造」（2026-10-10 用户定案）：打开专业面板 + 定位当前段配方 + 预填数量；
    --   定时器自动制造被无限服硬拦（防脚本机制），按钮点击 = 硬件事件 = 合法通道。
    --   ★ 锚点在 Paint 里设（此时 f.btns 还没建）。
    --   ★ 2026-10-10 用户：功能暂缓 → 入口隐藏（引擎保留，PF.CRAFT_BTN 一开即回）。
    f.craftBtn = NewButton(f, L["跳转制造"], 66, 22, 14)
    f.craftBtn.__huiKeepTextColor = true
    f.craftBtn:Hide()
    f.craftBtn:SetScript("OnClick", function()
        jumpCraft()
        ns.PlaySound(1)
    end)
    TipOn(f.craftBtn, L["跳转制造"],
          L["打开专业面板并自动定位当前段配方、预填制造数量；在面板内点一次制造即可批量完成。"])

    f.finish = MakeFS(f, 14, C_OK, "LEFT")
    f.finish:SetWordWrap(false)

    -- Controls have their own higher frame, below the content cards. In the old
    -- layout the card's mouse-enabled surface could cover the return button.
    f.controls = CreateFrame("Frame", nil, f)
    f.controls:SetFrameLevel((f:GetFrameLevel() or 1) + 20)
    f.controls:EnableMouse(false)
    f.nowBtn = NewButton(f.controls, L["回到当前"], 84, 22, 14)
    f.nowBtn:Hide()
    f.nowBtn:SetScript("OnClick", function() PF.ReturnToCurrent() ns.PlaySound(1) end)
    f.suppBtn = NewButton(f.controls, L["计算补料"], 84, 22, 14)
    f.suppBtn:SetScript("OnClick", function() PF.CalculateSupplement() ns.PlaySound(1) end)
    TipOn(f.suppBtn, L["计算补料"], L["按当前实际进度展开追加材料的制作与采购需求。"])
    f.verifyBtn = NewButton(f.controls, L["产出核对"], 84, 22, 14)
    f.verifyBtn:SetScript("OnClick", function() showOutputVerification() ns.PlaySound(1) end)
    TipOn(f.verifyBtn, L["产出核对"], L["记录本步骤累计实际产出；请勿填写背包现存数量。"])

    local labels = { L["购物清单"], L["上一步"], L["下一步"] }
    local onclick = { function()
        PF.showShop = PF.shopKind == "supplement" or not PF.showShop
        PF.shopKind, PF.shopScroll = nil, 0
        PF.Paint()
    end, PF.Prev, PF.Skip }
    f.btns = {}
    for i = 1, 3 do
        local bt = NewButton(f.controls, labels[i], BTN_W[i], 22, 14)
        bt.__huiKeepTextColor = true
        bt:SetScript("OnClick", function() onclick[i]() ns.PlaySound(1) end)
        f.btns[i] = bt
    end
    -- （shopImp 已挪入购物清单卡表头、craftBtn 已挂 btns[1] 右侧，均相对锚自动跟随）

    -- 右上角关闭（收窗不删进度，再点入口按钮原地恢复）
    f.xBtn = NewButton(f, "×", 24, 22, 14)
    f.xBtn.__huiKeepTextColor = true
    f.xBtn:SetPoint("TOPRIGHT", f, "TOPRIGHT", -8, -8)
    f.xBtn:SetScript("OnClick", function()
        local s = st()
        if s then s.hidden = true end
        f:Hide()
    end)

    -- 初始位置：记忆点 或 屏幕右侧
    local pos = dbProf().followPos
    f:ClearAllPoints()
    if pos and pos[1] then
        f:SetPoint(pos[1], pos[2] or UIParent, pos[3], pos[4])
    else
        f:SetPoint("CENTER", UIParent, "CENTER", 340, 60)
    end

    -- 1 秒轮询（技能面板扫描兜底，兼带完成态计时刷新）
    if C_Timer.NewTicker then
        C_Timer.NewTicker(1, function()
            if f and f:IsShown() then
                PF.Sync()
                PF.Paint()
            end
        end)
    end

    PF.f = f            -- Toggle / 右上角×走 PF.f（f 是本函数局部，不挂回 PF 取不到）
end

-- 懒加载：物品名没就绪时挂几次重扫
local sweep = 0
local function sweepPaint(pending)
    if pending and sweep < SWEEP_MAX then
        sweep = sweep + 1
        C_Timer.After(2, function() if f and f:IsShown() then PF.Paint() end end)
    elseif not pending then
        sweep = 0
    end
end

-- -------------------------------------------------------------------------
-- 绘制（全部 SetText / 显隐 / 尺寸，零新建帧）
-- -------------------------------------------------------------------------
local function paintMats(seg, rm, w, remaining, extraCrafts)
    local rec = rm[seg[3]]
    local mats = recMats(rec)
    local n = 0
    local pending = false
    local offset = f.card.matOffset or 0
    if mats and #mats > 0 then
        f.card.matHead:Hide()
        for i, m in ipairs(mats) do
            if i > MAT_MAX then break end
            local per = (m[2] or 1)
            local need = per * math.max(0, remaining or 0)   -- 预计还需总量 = 单次用量 × 剩余制作次数
            local nm, got = DG.ItemName(m[1])
            if not got then DG.RequestItem(m[1]) pending = true end
            local line = rowsMat[i]
            line:SetTextColor(Unpack(C_TEXT))
            local txt = format("%s ×%d", nm, need)
            if extraCrafts and extraCrafts > 0 then
                txt = format(L["%s ×%d（追加%d）"], nm, need, per * extraCrafts)
            end
            line:SetText(txt)
            line:ClearAllPoints()
            line:SetPoint("TOPLEFT", f.card, "TOPLEFT", 36, -(61 + offset + (i - 1) * 26))
            line:SetWidth(w - 28)
            line:Show()
            local ic = rowsMatIcon[i]
            ic:SetTexture(DG.ItemIcon(m[1]) or Host.FALLBACK_ICON)
            ic:ClearAllPoints()
            ic:SetPoint("TOPLEFT", f.card, "TOPLEFT", 8, -(56 + offset + (i - 1) * 26))
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
            more:SetPoint("TOPLEFT", f.card, "TOPLEFT", 8, -(56 + offset + n * 26))
            more:SetWidth(w)
            more:Show()
            rowsMatIcon[MAT_MAX + 1]:Hide()
            rowsMatBadge[MAT_MAX + 1]:Hide()
            n = n + 1
        else
            rowsMat[MAT_MAX + 1]:Hide()
            rowsMatIcon[MAT_MAX + 1]:Hide()
            rowsMatBadge[MAT_MAX + 1]:Hide()
        end
    elseif rec then
        f.card.matHead:SetText(L["无材料"])
        f.card.matHead:Show()
    else
        f.card.matHead:SetText(L["材料未收录"])
        f.card.matHead:Show()
    end
    f.card.matHead:ClearAllPoints()
    f.card.matHead:SetPoint("TOPLEFT", f.card, "TOPLEFT", 8, -(56 + offset))
    for i = n + 1, MAT_MAX do
        rowsMat[i]:Hide()
        rowsMatIcon[i]:Hide()
        rowsMatBadge[i]:Hide()
    end
    if n < MAT_MAX + 1 then
        rowsMatIcon[MAT_MAX + 1]:Hide()
        rowsMatBadge[MAT_MAX + 1]:Hide()
    end
    return n, pending
end

function PF.Paint()
    if not (f and f:IsShown()) then return end
    -- 购物清单展开且列排不下时整体加宽 HUD（PF.wide 为额外宽，收起清单即回基准）
    W = W_BASE + ((PF.showShop and PF.wide) or 0)
    f:SetWidth(W)
    f.barBG:SetWidth(W - 20)
    local s = st()
    if not (s and s.slug) then f:Hide() return end
    local slug = s.slug
    local mode, steps, res = routeFor(slug, s.skill)
    if not steps then f:Hide() return end
    local p = D.pro and D.pro[slug]
    local accent = Accent()
    local name = (p and p.name) or slug

    f.icon:SetTexture(ProfIconTex(p and p.icon))
    f.title:SetText(format(L["%s升级HUD"], name))

    local cur, mx = skillOf(slug)
    f.skill:SetText(cur and format(L["技能 %d / %d"], cur, mx or 300) or L["未学过该专业，先找训练师学习"])
    local ratio = cur and math.min(1, cur / 300) or 0
    f.bar:SetWidth(math.max(2, math.floor((W - 20) * ratio + 0.5)))
    f.bar:SetVertexColor(accent[1], accent[2], accent[3], 0.95)

    local waiting = PF.executionNotice or mode == "auto" and (not res or (res.planVersion == 2 and
        (res.feasible ~= true or (res.partial and (s.step or 1)>#steps))))
    local finished = not waiting and (s.step or 1) > #steps
    local vi = math.max(1, math.min(#steps, (s.step or 1) + (PF.view or 0)))
    f.seg:SetText(((mode == "auto") and L["自动计算"] or L["固定路线"]) .. " · "
                  .. format(L["步骤 %d / %d"], vi, #steps))

    -- 黄色段 = 当前段落区间（真实指针段，与浏览偏移无关）
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

    f.finish:SetShown(finished or waiting)
    f.card:SetShown(not finished and not waiting)
    f.nowBtn:SetShown((PF.view or 0) ~= 0 and not finished and not waiting)
    f.craftBtn:SetShown(PF.CRAFT_BTN and not finished and not waiting)
    local xp = ns.ProfExecution
    local run = xp and xp.GetRun and xp.GetRun(slug)
    f.suppBtn:SetShown(run ~= nil and not finished and not waiting)
    f.verifyBtn:SetShown(run ~= nil and not finished and not waiting)

    local y = -82                      -- 头部固定高（「已过摘要」行已按用户要求移除）
    local pending = false

    if not finished and not waiting then
        local seg = steps[vi]
        local specializationQuest=seg.kind=="specialization_quest"
        if specializationQuest then f.craftBtn:Hide(); f.suppBtn:Hide(); f.verifyBtn:Hide() end
        local stepSlug = seg.profession or slug
        local rm = recMap(stepSlug)
        if res and res.planVersion == 2 then rm = { [seg[3]] = stepRecipe(seg, res, stepSlug) } end
        local rec = rm[seg[3]]
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
        -- 段卡悬停数据（OnEnter 用，见 Build）：产物 + 本段材料
        card.__it = prodItem and { prodItem } or nil
        card.__mats = recMats(rec)
        local PDm = ns.ProfModule
        local checkpoint = not specializationQuest and (seg.checkpoint or seg[3] == 0)
        local stepProf = D.pro and D.pro[stepSlug]
        local nmText = specializationQuest and questName(seg) or (checkpoint and L["实地采矿"] or SpellName(seg[3]))
        if stepSlug ~= slug then nmText = ((stepProf and stepProf.name) or stepSlug) .. " · " .. nmText end
        card.name:SetText(nmText)

        -- 当前段还需制作次数（按升点概率估算；浏览预览段显示攻略全量）
        local crafts = seg[4] or 0
        local remaining = crafts
        local progress = run and executionProgress(s, seg, vi)
        if progress and not progress.outputItem then f.verifyBtn:Hide() end
        if vi == s.step then
            remaining = math.ceil(craftsLeft(seg, skillOf(stepSlug) or s.skill, rec))
            crafts = remaining
        end
        if specializationQuest then remaining=progress and progress.complete and 0 or 1 end
        local progressLines = {}
        if specializationQuest then
            local goal=questGoal(seg)
            progressLines[#progressLines+1]=questSource(seg)
            progressLines[#progressLines+1]=format(L["需要工程学 %d、角色等级 %d"],goal.minSkill or 200,goal.minLevel or 30)
            local prerequisites={}
            for _,id in ipairs(goal.prerequisiteQuestIDs or {}) do prerequisites[#prerequisites+1]="#"..tostring(id) end
            if #prerequisites>0 then progressLines[#progressLines+1]=format(L["先完成前置任务并与导师对话：%s"],table.concat(prerequisites,", ")) end
            progressLines[#progressLines+1]=L["实际学会对应专精后才完成此步骤。"]
        elseif progress then
            if (progress.divertedOutputs or 0)>0 and (progress.remainingOutputs or 0)>0 then
                progressLines[#progressLines + 1] = L["材料被额外制作消耗，仍需补足。"]
            elseif progress.skillMet and (progress.remainingOutputs or 0) > 0 then
                progressLines[#progressLines + 1] = L["技能已达标，仍需为后续准备材料。"]
            end
            if (progress.requiredOutputs or 0) > 0 then
                progressLines[#progressLines + 1] = format(L["按最低产量需%d次，已制作%d次。"],
                    progress.minCrafts or 0, progress.casts or 0)
                progressLines[#progressLines + 1] = format(L["需%d份，已确认%d份，还需%d份。"],
                    progress.requiredOutputs, progress.confirmedOutputs or 0, progress.remainingOutputs or 0)
                if (progress.reusedOutputs or 0)>0 then
                    progressLines[#progressLines+1]=format(L["复用本路线余量%d份。"],progress.reusedOutputs)
                end
            elseif progress.outputItem then
                progressLines[#progressLines + 1] = format(L["已确认产出%d份。"], progress.confirmedOutputs or 0)
            end
            if (progress.pendingOutputs or 0) > 0 then
                progressLines[#progressLines + 1] = format(L["最低保证%d份；%d次制作的产出待确认。"],
                    progress.guaranteedOutputs or 0, progress.pendingOutputs)
            elseif run.newPlanAvailable and #progressLines < 4 then
                progressLines[#progressLines + 1] = L["有新方案，当前继续执行已保存计划。"]
            end
            if (progress.extraCrafts or 0) > 0 then
                progressLines[#progressLines + 1] = format(L["追加需求：预计再制作%d次。"], progress.extraCrafts)
            end
        end
        local progressCount = math.min(#f.card.progress, #progressLines)
        for i, line in ipairs(f.card.progress) do
            line:SetShown(i <= progressCount)
            if i <= progressCount then
                line:SetText(progressLines[i])
                line:ClearAllPoints()
                line:SetPoint("TOPLEFT", card, "TOPLEFT", 8, -(54 + (i - 1) * 18))
                line:SetWidth(W - 2 * PAD - 16)
            end
        end
        card.matOffset = progressCount * 18
        local nMat, pend = paintMats(seg, rm, w - 8, remaining, progress and progress.extraCrafts)
        pending = pending or pend

        -- 右上角：已学习（绿）/ 来源（灰）——替代原「当前」角标与底部来源行
        local src, detail
        if PDm and PDm.LevelSrc then
            src, detail = PDm.LevelSrc(rec)
        end
        local learned = IsLearned(seg[3])
        if specializationQuest then
            local E=ns.ProfEconomy
            learned=E and E.SpecializationKnown and E.SpecializationKnown(questGoal(seg).abilityID)==true
        end
        local tagText = learned and L["已学习"] or (src or L["向训练师学习"])
        if specializationQuest then tagText=learned and L["已学习"] or L["待完成"] end
        if checkpoint then tagText = L["实地采矿"] end
        local tags = seg.tags or {}
        local material = tags.material or seg.role == "material" or seg.role == "both" or seg.reason == "material"
        local leveling = tags.leveling or seg.role == "level" or seg.role == "both" or not material
        local role = material and (leveling and L["升级&中间产物"] or L["中间产物"]) or L["升级"]
        if specializationQuest then role=L["专精入门任务"] end
        if PDm and PDm.StepRole then role = PDm.StepRole(seg) end
        tagText = role .. " · " .. tagText
        if detail and not learned then tagText = tagText .. " · " .. detail end
        card.srcTag:SetText(tagText)
        card.srcTag:SetTextColor(Unpack(learned and C_OK or C_GREY))
        local tagW = 90
        if PDm and PDm.TextW then
            local okW, tw = pcall(PDm.TextW, tagText, 14)
            if okW and type(tw) == "number" then tagW = math.ceil(tw) end
        end
        card.srcTag:SetWidth(tagW)

        -- 区间挪到配方名右侧（同行）；第二行只留次数信息
        local rangeText = format(L["%d – %d"], seg[1], seg[2])
        card.range:SetText(rangeText)
        local craftText = format(L["大约还需制作%d次"], crafts)
        if progress then
            craftText = format(L["预计还需%d次 · 已制作%d次"], remaining, progress.casts or 0)
        end
        if checkpoint then craftText = L["达到目标技能后重新计算"] end
        if specializationQuest then
            craftText=L["交付任务物品"].." · #"..tostring(questGoal(seg).questID or "?")
            local E=ns.ProfEconomy
            local questProgress=E and E.SpecializationQuestProgress and E.SpecializationQuestProgress(questGoal(seg))
            if questProgress and questProgress.readyForTurnIn then craftText=craftText.." · "..L["任务可交付"]
            elseif questProgress and questProgress.inLog then craftText=craftText.." · "..L["任务已接取"] end
        end
        if seg.fishing and seg.fishing[1] then
            local areas={}
            for _,a in ipairs(seg.fishing[1].areas or {}) do
                if #areas<2 then areas[#areas+1]=a.name or (DG.ZoneName and DG.ZoneName(a.zoneID)) or tostring(a.zoneID) end
            end
            if #areas>0 then craftText=craftText.." · "..table.concat(areas," / ") end
        end
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

        local cardH = nMat * 26 + 60 + card.matOffset
        card:ClearAllPoints()
        card:SetPoint("TOPLEFT", f, "TOPLEFT", PAD, y)
        card:SetSize(W - 2 * PAD, cardH)
        y = y - cardH - 8
    end

    -- 购物清单（展开时）
    if PF.showShop and not finished and not waiting then
        local isSupplement = PF.shopKind == "supplement"
        local supplement = isSupplement and xp and xp.GetSupplement and xp.GetSupplement(slug)
        local list = shopList(s, PF.shopKind)
        local shown = list
        f.shop.head:SetText((isSupplement and L["补料清单"] or L["购物清单"]) .. format(L[" · 共%d种"], #shown))
        local rowTop = 30
        f.shop.summary:SetShown(isSupplement)
        if isSupplement then
            local summary = L["补料尚未计算完成"]
            if supplement then
                if supplement.inFlight then
                    summary = L["正在计算补料…"]
                elseif supplement.stale then
                    summary = L["进度已变化，请重新计算补料"]
                elseif supplement.feasible == false then
                    summary = L["当前限制下无法补齐材料"]
                else
                    local price = RA and RA.MoneyStr and RA.MoneyStr(supplement.total or 0, "copper") or tostring(supplement.total or 0)
                    summary = format(L["追加采购费用：%s"], price)
                    local count = #(supplement.executionSteps or supplement.steps or {})
                    if count > 0 then summary = summary .. format(L[" · 制材%d步"], count) end
                end
            end
            f.shop.summary:SetText(summary)
            f.shop.summary:SetWidth(W - 2 * PAD - 16)
            rowTop = 50
        end
        -- 先计算采购数量、来源、等级各列宽度，再统一对齐。
        local function tw(txt)
            local PDm = ns.ProfModule
            if PDm and PDm.TextW then
                local ok, wv = pcall(PDm.TextW, txt, 14)
                if ok and type(wv) == "number" then return wv end
            end
            return #txt * 5 + 16
        end
        local rows = {}
        local nameW, numW, tagW, sourceW = 0, 0, 0, 0
        for _, e in ipairs(shown) do
            local nm, got = DG.ItemName(e.id)
            if not got then DG.RequestItem(e.id) pending = true end
            if e.formula then nm=L["图纸"].." · "..nm end
            local row = {
                nm = nm,
                purchase = e,
                need = e.need,
                fishing=e.source=="fishing",
                sold = e.vendor or e.source == "vendor" or e.source == "npc",
                at = e.at or 0,
            }
            local w1 = tw(row.nm)
            if w1 > nameW then nameW = w1 end
            local w2 = tw(format("×%d", row.need))
            if w2 > numW then numW = w2 end
            local w5 = tw(format("%d+", row.at)) + 10
            if w5 > tagW then tagW = w5 end
            row.source = row.fishing and L["自行钓取"] or row.sold and L["NPC购买"] or L["拍卖行"]
            sourceW = math.max(sourceW, tw(row.source) + 10)
            rows[#rows + 1] = row
        end
        local soldW = sourceW
        -- 列位固定：名字 | 采购数量 | 采购来源 | 首次使用等级(贴右)
        local xName = 8
        local xNum = xName + nameW + 10
        local xSold = xNum + numW + 10
        -- 滚动窗口：全部收录（不再截断溢出行），SHOP_MAX 为可视行数
        local maxScroll = math.max(0, #rows - SHOP_MAX)
        PF.shopScroll = math.max(0, math.min(PF.shopScroll or 0, maxScroll))
        local scroll = PF.shopScroll
        local needInner = xSold + soldW + 10 + tagW + 14      -- 右缘留滚动条位
        local baseInner = W_BASE - 2 * PAD - 16
        local newWide = (needInner > baseInner) and (needInner - baseInner) or nil
        if (newWide or 0) ~= (PF.wide or 0) then
            PF.wide = newWide
            C_Timer.After(0, PF.Paint)      -- 下一帧按新宽整体重排（第二遍不再触发）
        end
        local n = 0
        for ri = scroll + 1, math.min(#rows, scroll + SHOP_MAX) do
            local row = rows[ri]
            local ry = -(rowTop + n * 20)
            -- 固定列：名字白 / 采购数量金 / 采购来源 / 等级丸(X+)贴右
            local nmFS = rowsShop[n + 1]
            local num = rowsShopNum[n + 1]
            local sp = rowsShopSourcePill[n + 1]
            sp.__purchase = row.purchase
            -- 胶囊染色：a 缺省 0.99（f.shop 是 0.04 白底半透明 backdrop，顶点 alpha=1 会被
            --   分进不透明批画到背板之下——见 2026-10-08 教训；胶囊件间无缝无重叠，0.99 无预混误差）
            local function paintPill(p, txt, x0, wpx, cr, cg, cb, ca)
                p:ClearAllPoints()
                p:SetPoint("TOPLEFT", f.shop, "TOPLEFT", x0, ry + 1)
                p:SetSize(math.max(wpx, 34), 17)
                local a2 = ca or 0.99
                for _, t in ipairs(p.__cols) do t:SetVertexColor(cr, cg, cb, a2) end
                p.fs:SetText(txt)
                p:Show()
            end
            nmFS:SetText(row.nm)
            num:SetText(format("×%d", row.need))
            nmFS:ClearAllPoints()
            nmFS:SetPoint("TOPLEFT", f.shop, "TOPLEFT", xName, ry)
            nmFS:Show()
            num:ClearAllPoints()
            num:SetPoint("TOPLEFT", f.shop, "TOPLEFT", xNum, ry)
            num:Show()
            paintPill(sp, row.source, xSold, soldW, Unpack(row.sold and C_OK or C_GREY))
            -- 等级药丸（X+）贴右：胶囊宿主帧右锚（右缘 -14 让开滚动条），淡灰底
            local tp = rowsShopTagPill[n + 1]
            tp:ClearAllPoints()
            tp:SetPoint("TOPRIGHT", f.shop, "TOPRIGHT", -14, ry + 1)
            tp:SetSize(math.max(tagW, 34), 17)
            for _, t in ipairs(tp.__cols) do t:SetVertexColor(0.55, 0.55, 0.55, 0.22) end
            tp.fs:SetText(format("%d+", row.at))
            tp:Show()
            n = n + 1
        end
        -- 右缘滚动条（全部收录、超出可视行数时出现；thumb 反映窗口位置）
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
            sb:SetPoint("TOPRIGHT", f.shop, "TOPRIGHT", -3, -(rowTop - 2 + thumbOff))
            sb:Show()
        else
            f.shop.sbarTrack:Hide()
            f.shop.sbarThumb:Hide()
        end
        for i = n + 1, #rowsShop do
            rowsShop[i]:Hide()
            rowsShopNum[i]:Hide()
            rowsShopSourcePill[i]:Hide()
            rowsShopSourcePill[i].__purchase = nil
        end
        for i = n + 1, #rowsShopTagPill do
            rowsShopTagPill[i]:Hide()
        end
        if n > 0 then
            local shopH = rowTop + n * 20 + 10
            f.shop.empty:Hide()
            f.shop:ClearAllPoints()
            f.shop:SetPoint("TOPLEFT", f, "TOPLEFT", PAD, y)
            f.shop:SetSize(W - 2 * PAD, shopH)
            f.shop:Show()
            y = y - shopH - 8
        else
            f.shop.empty:SetText(isSupplement and L["没有追加采购材料"] or L["无材料"])
            f.shop.empty:ClearAllPoints()
            f.shop.empty:SetPoint("TOPLEFT", f.shop, "TOPLEFT", 8, -rowTop)
            f.shop.empty:Show()
            local shopH = rowTop + 20 + 10
            f.shop:ClearAllPoints()
            f.shop:SetPoint("TOPLEFT", f, "TOPLEFT", PAD, y)
            f.shop:SetSize(W - 2 * PAD, shopH)
            f.shop:Show()
            y = y - shopH - 8
        end
    else
        f.shop:Hide()
        PF.wide = nil                    -- 收起购物清单即恢复基础宽度
        PF.shopScroll = nil
    end

    -- 完成态
    if finished or waiting then
        local msg = format(L["%s跟随完成 · %s"], name, fmtTime(time() - (s.t0 or time())))
        if waiting then
            msg = PF.executionNotice or routeNotice(res)
        end
        f.finish:SetText(msg)
        f.finish:ClearAllPoints()
        f.finish:SetPoint("TOPLEFT", f, "TOPLEFT", 10, y)
        f.finish:Show()
        y = y - 34
    end

    -- All footer buttons are children of a dedicated higher-level controls
    -- frame. Rows wrap by available width, so neither a card nor another
    -- button can intercept the return-to-current click.
    local by = y - 4
    f.controls:ClearAllPoints()
    f.controls:SetPoint("TOPLEFT", f, "TOPLEFT", PAD, by)
    f.controls:SetWidth(W - 2 * PAD)
    local x, row = 0, 0
    local controls = {
        {f.btns[1], 92}, {f.craftBtn, 66}, {f.btns[2], 66}, {f.btns[3], 66},
        {f.nowBtn, 84}, {f.suppBtn, 84}, {f.verifyBtn, 84},
    }
    for _, entry in ipairs(controls) do
        local bt, bw = entry[1], entry[2]
        if bt:IsShown() then
            local pd=ns.ProfModule
            if pd and pd.TextW and bt.GetText then
                bw=math.min(W-2*PAD,math.max(bw,math.ceil(pd.TextW(bt:GetText() or "",14))+16))
            end
            bt:SetWidth(bw)
            if x > 0 and x + bw > W - 2 * PAD then row, x = row + 1, 0 end
            bt:ClearAllPoints()
            bt:SetPoint("TOPLEFT", f.controls, "TOPLEFT", x, -row * 26)
            x = x + bw + BTN_GAP
        end
    end
    local controlsH = row * 26 + 22
    f.controls:SetHeight(controlsH)
    f:SetHeight(-by + controlsH + 8)
    sweepPaint(pending)
end

-- -------------------------------------------------------------------------
-- 入口按钮（由 ProfessionUI.PickTabs 调用；本文件不持有专业页任何帧）
-- -------------------------------------------------------------------------
function PF.PaintButton(bt, slug)
    if not bt then return end
    local ok = slug and slug ~= "__index" and LV[slug] and LV[slug].steps
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
    local accent = Accent()
    SetOutline(bt, PF.IsActive(slug), accent[1], accent[2], accent[3])
    bt:GetFontString():SetTextColor(Unpack(PF.Following(slug) and C_GOLD or C_GREY))
    bt:SetShown(true)
end

-- 主界面「一键导入购物清单」按钮（升级 HUD 入口左边；显隐与 hudBtn 同条件，
-- 由 ProfessionUI.PickTabs 调用；本文件不持有专业页任何帧，只刷状态与点击）
function PF.PaintImportBtn(bt, slug)
    if not bt then return end
    local ok = slug and slug ~= "__index" and LV[slug] and LV[slug].steps
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
    SetOutline(bt, false, 1, 0.82, 0)
    bt:GetFontString():SetTextColor(Unpack(C_GREY))
    bt:SetShown(true)
end

-- 价格/配方/设置触发新结果时更新当前 HUD，不等下一次技能提升。
if RA and RA.OnPlanChanged then
    RA.OnPlanChanged(function(slug, result)
        local s = st()
        if not (s and s.slug == slug) then return end
        local xp = ns.ProfExecution
        if xp and xp.GetRun and xp.GetRun(slug) and result and xp.Bind then
            xp.Bind(slug, result)
        end
        local function refresh()
            PF.Sync()
            if PF.f and PF.f:IsShown() then PF.Paint() end
        end
        if C_Timer and C_Timer.After then C_Timer.After(0, refresh) else refresh() end
    end)
end

if ns.ProfExecution and ns.ProfExecution.OnChanged then
    ns.ProfExecution.OnChanged(function(slug)
        local s = st()
        if not (s and s.slug == slug) then return end
        PF.Sync()
        if PF.f and PF.f:IsShown() then PF.Paint() end
    end)
end
