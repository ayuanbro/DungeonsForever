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

local format = string.format

local PF = {}
ns.ProfFollow = PF

local f

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

local function routeForCalc(slug, skill)
    local PD = ns.ProfModule
    local live = skillOf(slug)
    if PD and PD.lastStepsSlug == slug and type(PD.lastSteps) == "table" and #PD.lastSteps > 0
       and (PD.lastStepsSkill == nil or live == nil or PD.lastStepsSkill == live) then
        return PD.lastStepsAuto and "auto" or "fixed", PD.lastSteps
    end
    if PD and PD.autoSnapshot and PD.autoSnapshotSlug == slug then
        local snapSteps = PD.autoSnapshot.steps
        if type(snapSteps) == "table" and #snapSteps > 0 then return "auto", snapSteps end
    end
    if PD and PD.RestorePlanSkel and PD.autoSnapshotSlug ~= slug then
        local okR, saved = pcall(PD.RestorePlanSkel, slug, live or skill)
        if okR and type(saved) == "table" and type(saved.steps) == "table" and #saved.steps > 0 then
            return "auto", saved.steps
        end
    end
    local scheme = PD and PD.SettingRaw and PD.SettingRaw("autoScheme") or "cheapest"
    if PD and PD.Setting and PD.Setting("autoRoute") and RA
       and (scheme == "optim" or RA.Available()) then
        local opts = {
            start = (PD.Setting("autoFromCurrent") and skill) and math.max(1, skill) or 1,
            onlyAH = PD.Setting("autoOnlyAH"),
            noFormula = PD.Setting("autoNoFormula"),
            learnedOnly = PD.Setting("autoLearnedOnly"),
            target = routeTarget(slug),
            scheme = scheme,
        }
        local res = RA.Get(slug, opts)
        if res and (res.priced or scheme == "optim") then return "auto", res.steps end
    end
    local lv = LV[slug]
    return "fixed", clipFixedSteps(lv and lv.steps or nil, routeTarget(slug))
end

local rMemoSlug, rMemoSkill, rMemoMode, rMemoSteps, rMemoT, rMemoSnap
local ROUTE_MEMO_TTL = 10
local function routeFor(slug, skill)
    local now = GetTime and GetTime() or 0
    local PD = ns.ProfModule
    local snap = (PD and PD.autoSnapshotSlug == slug) and PD.autoSnapshot or nil
    if slug and rMemoSlug == slug and rMemoSkill == skill and rMemoSnap == snap
       and (now - (rMemoT or 0)) < ROUTE_MEMO_TTL then
        return rMemoMode, rMemoSteps
    end
    local mode, steps = routeForCalc(slug, skill)
    rMemoSlug, rMemoSkill, rMemoMode, rMemoSteps, rMemoT, rMemoSnap =
        slug, skill, mode, steps, now, snap
    return mode, steps
end

function PF.InvalidateRoute()
    rMemoSlug, rMemoSkill, rMemoMode, rMemoSteps, rMemoT, rMemoSnap = nil, nil, nil, nil, nil, nil
end

local function routeKey(mode, steps)
    if not steps then return tostring(mode) .. ":0" end
    local a, b = steps[1], steps[#steps]
    return format("%s:%d:%s:%s:%s", tostring(mode), #steps,
                  tostring(a and a[1]), tostring(a and a[3]), tostring(b and b[2]))
end

local function derivedStep(slug, skill)
    local _, steps = routeFor(slug, skill)
    if not steps then return nil end
    local T = ns.ProfTrack
    local run = T and T.GetRun and T.GetRun(slug)
    local casts = {}
    if run and type(run.steps) == "table" then
        for i = 1, #steps do
            local rs = run.steps[i]
            local p = (run.progress or {})[i]
            if rs and rs.spell == steps[i][3] and p then casts[i] = tonumber(p.casts) or 0 end
        end
    end
    if T and T.PickIndex then return T.PickIndex(steps, skill or 0, casts) end
    for i, s in ipairs(steps) do
        if skill < s[2] then return i end
    end
    return #steps + 1
end

local function recMats(rec) return rec and (rec[12] or rec.mats) or nil end
local function recItem(rec) return rec and (rec[2] or rec.makes) or nil end

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
    if cur and cur ~= (s.skill or 0) then
        local dropped = cur < (s.skill or 0)
        s.skill = cur
        changed = true
        if dropped then
            local TK = ns.ProfTrack
            if TK and TK.Archive then pcall(TK.Archive, s.slug, "skill_dropped") end
            PF.InvalidateRoute()
            s.step = nil
            s.rkey = nil
            PF.view = 0
            PF.shopScroll = nil
            s.t0 = time()
        end
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
    if not s.step then
        s.step = d or 1
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

function PF.RefreshMainUI()
    local PD = ns.ProfModule
    if PD and PD.built and PD.page and PD.page.IsVisible and PD.page:IsVisible() then
        if PD.RequestRender then PD.RequestRender() end
    end
end

function PF.Toggle(slug)
    if not (slug and LV[slug] and LV[slug].steps) then return end
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
    local T = ns.ProfTrack
    local s = st()
    if not (s and s.slug and T and T.VerifyOutput and T.Progress) then return false end
    local run = T.GetRun(s.slug)
    local prog = run and T.Progress(s.slug, nil, run)
    if not ref then ref = prog end
    if not ref or not ref.item or ref.finished then return false end
    total = tonumber(total)
    if not total or total < 0 or total ~= math.floor(total) then return false end
    local ok = T.VerifyOutput(s.slug, ref.index, ref.item, total)
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
    local data = { slug = s.slug, index = prog.index, item = prog.item, total = prog.outputs or 0 }
    StaticPopupDialogs.DF_PROF_VERIFY_OUTPUT = {
        text = L["填写本步骤累计实际产出件数（不是当前背包数量）。"],
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

local function craftsLeft(seg, skill)
    local from = math.max(skill or 0, seg[1])
    if from >= seg[2] then return 0 end
    local plan = tonumber(seg[4]) or 0
    if plan <= 0 then return 0 end
    local span = math.max(1, seg[2] - seg[1])
    return plan * math.min(1, (seg[2] - from) / span)
end

local function currentCands(steps, skill, curStep)
    local out = {}
    for i = 1, #steps do
        local sg = steps[i]
        local a = tonumber(sg[1]) or 0
        local b = tonumber(sg[2]) or 0
        if a <= skill and skill < b then out[#out + 1] = i end
    end
    if #out == 0 then out[1] = math.max(1, math.min(#steps, curStep or 1)) end
    return out
end

local function canCraftOf(seg, rm)
    local rec = rm[seg[3]]
    local mats = recMats(rec)
    local can
    if mats and #mats > 0 then
        for _, m in ipairs(mats) do
            local per = (m[2] or 1)
            if per > 0 then
                local c = math.floor(Have(m[1]) / per)
                can = (can == nil) and c or math.min(can, c)
            end
        end
    end
    return can
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
        local rec = rm[seg[3]]
        local mats = recMats(rec)
        local crafts = seg[4] or 0
        if i == curStep then
            crafts = math.ceil(craftsLeft(seg, s.skill))
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
    local goal = (not onlyStep) and G and G.SpecGoal and G.SpecGoal(s.slug, routeTarget(s.slug))
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

local function craftPageShown()
    local pf = _G.ProfessionsFrame
    local cp = pf and pf.CraftingPage
    if cp and cp.IsShown and cp:IsShown() then return true end
    local tf = _G.TradeSkillFrame
    return (tf and tf.IsShown and tf:IsShown()) or false
end

local function baseProfID()
    local CUI = _G.C_TradeSkillUI
    if not (CUI and CUI.GetBaseProfessionInfo) then return nil end
    local ok, info = pcall(CUI.GetBaseProfessionInfo)
    if ok and type(info) == "table" then return tonumber(info.professionID) end
    return nil
end

local function activeProfID()
    local CUI = _G.C_TradeSkillUI
    if not CUI then return nil end
    local ok, info = pcall(CUI.GetChildProfessionInfo)
    if ok and type(info) == "table" then
        local id = tonumber(info.professionID)
        if id and id ~= 0 then return id end
    end
    return baseProfID()
end

local function profSkillLine(slug)
    local profName = D.pro and D.pro[slug] and D.pro[slug].name
    if not profName or not GetProfessions or not GetProfessionInfo then return nil end
    for _, i in ipairs({ GetProfessions() }) do
        if i then
            local ok, n, _, _, _, _, _, sl = pcall(GetProfessionInfo, i)
            if ok and type(sl) == "number" then
                if n == profName or (type(n) == "string" and n ~= "" and profName:find(n, 1, true)) then
                    return sl
                end
            end
        end
    end
    return nil
end

local function showCraftingPage()
    local f = _G.ProfessionsFrame
    if not (f and f.CraftingPage) then return false end
    if f.IsShown and not f:IsShown() then return false end
    local book = f.BookPage
    if book and book.IsShown and book:IsShown() and _G.EventRegistry then
        pcall(_G.EventRegistry.TriggerEvent, _G.EventRegistry, "Professions.ShowSelectedCraftingPage")
    end
    if not (f.CraftingPage.IsShown and f.CraftingPage:IsShown()) then
        if book and book.Hide then pcall(book.Hide, book) end
        pcall(f.CraftingPage.Show, f.CraftingPage)
        if f.RefreshRightTabs then pcall(f.RefreshRightTabs, f) end
    end
    return craftPageShown()
end

local function ensureProfFrame()
    local f = _G.ProfessionsFrame
    if f then return f end
    local C = _G.C_AddOns
    if C and C.LoadAddOn then pcall(C.LoadAddOn, "Blizzard_Professions") end
    return _G.ProfessionsFrame
end

local function refreshProfInfo(f)
    local P = _G.Professions
    if not (P and P.GetProfessionInfo and f.SetProfessionInfo) then return end
    local ok, info = pcall(P.GetProfessionInfo)
    if not (ok and type(info) == "table") then return end
    if tonumber(info.professionID) == 0 then return end
    pcall(f.SetProfessionInfo, f, info, false)
end

local function boundProfOK(skillLine)
    local CUI = C_TradeSkillUI
    if not (CUI and CUI.GetBaseProfessionInfo) then return false end
    local ok, info = pcall(CUI.GetBaseProfessionInfo)
    if ok and type(info) == "table" then
        return (tonumber(info.professionID) or 0) == skillLine
    end
    return false
end

local function openProfPanel(skillLine)
    if craftPageShown() and boundProfOK(skillLine) then return true end
    local CUI = C_TradeSkillUI
    if CUI and CUI.OpenTradeSkill and type(skillLine) == "number" then
        if pcall(CUI.OpenTradeSkill, skillLine) then return true end
    end
    local f = ensureProfFrame()
    if not (f and f.Show) then return false end
    if not (f.IsShown and f:IsShown()) then
        if not pcall(f.Show, f) then return false end
        refreshProfInfo(f)
    end
    showCraftingPage()
    if C_Timer and C_Timer.After then
        C_Timer.After(0.2, function() if not craftPageShown() then showCraftingPage() end end)
    end
    return true
end

local function watchSelection(p)
    if not (C_Timer and C_Timer.After) then return end
    local po = p.opts or {}
    local tries = 0
    local function tick()
        if p.done then return end
        tries = tries + 1
        if tries > 120 then return end
        local cp = _G.ProfessionsFrame and _G.ProfessionsFrame.CraftingPage
        if not (cp and cp.SchematicForm) then
            C_Timer.After(0.5, tick)
            return
        end
        if not po.noSelect and tries <= 6 then
            local srch = cp.RecipeList and cp.RecipeList.SearchBox
            if srch and srch.SetText and srch.GetText and srch:GetText() == "" then
                pcall(srch.SetText, srch, p.name)
            end
        end
        local t = cp.SchematicForm.transaction
        local rid = t and tonumber(t.recipeID) or 0
        local cri = cp.SchematicForm.currentRecipeInfo
        local nm = cri and cri.name or nil
        local box = cp.CreateMultipleInputBox
        local mx = box and box.GetMaxValue and tonumber(box:GetMaxValue()) or 0
        _G.__DFJumpWatch = { tries = tries, done = p.done, rid = rid, spell = p.spellID }
        local log = _G.__DFJumpLog
        if log == nil then log = {} _G.__DFJumpLog = log end
        log[#log + 1] = format("t%d rid=%s nm=%s mx=%s", tries, tostring(rid), tostring(nm), tostring(mx))
        if #log > 30 then table.remove(log, 1) end
        if rid == p.spellID or (nm ~= nil and nm == p.name) then
            if po.noFill or mx > 0 then
                p.done = true
                if not po.noFill and box and box.SetValue and box.GetValue then
                    local okS = pcall(box.SetValue, box, p.count)
                    log[#log + 1] = format("FILL ok=%s val=%s", tostring(okS), tostring(box.GetValue and box:GetValue()))
                end
                craftNotify(format(L["已选中 %s —— 数量已预填 %d，点一次制造即可"], p.name, p.count))
                return
            end
        end
        if rid ~= p.spellID and nm ~= p.name and not po.noSelect and tries <= 10 then
            local CUI = C_TradeSkillUI
            local sb = cp.RecipeList and cp.RecipeList.ScrollBox
            local nodeReady = false
            if sb and sb.FindElementDataByPredicate then
                local okN, node = pcall(function()
                    return sb:FindElementDataByPredicate(function(n)
                        if type(n) ~= "table" or not n.GetData then return false end
                        local okD, d = pcall(n.GetData, n)
                        if not (okD and type(d) == "table") then return false end
                        return d.recipeID == p.spellID or (d.recipeInfo and d.recipeInfo.recipeID == p.spellID)
                    end)
                end)
                nodeReady = okN and node ~= nil
            end
            if nodeReady and cp.SelectRecipe and CUI and CUI.GetRecipeInfo then
                local okR, ri = pcall(CUI.GetRecipeInfo, p.spellID)
                if okR and type(ri) == "table" then
                    local okS = pcall(cp.SelectRecipe, cp, ri)
                    log[#log + 1] = format("SEL ok=%s", tostring(okS))
                end
            end
        end
        C_Timer.After(0.5, tick)
    end
    C_Timer.After(0.5, tick)
end

function jumpApply()
    local p = jumpPending
    if not p then return end
    if not craftPageShown() then return end
    jumpPending = nil
    craftNotify(format(L["已打开 %s 并定位配方 %s —— 请在列表中点击该配方，数量会自动填好"], p.prof or "", p.name))
    watchSelection(p)
end

local function jumpPoll()
    if not (C_Timer and C_Timer.After) then return end
    local tries = 0
    local function tick()
        if not jumpPending then return end
        local pf = _G.ProfessionsFrame
        _G.__DFJumpPoll = {
            tries = tries,
            pf = pf and pf.IsShown and pf:IsShown() or false,
            cp = pf and pf.CraftingPage and pf.CraftingPage.IsShown and pf.CraftingPage:IsShown() or false,
        }
        if craftPageShown() then
            jumpApply()
            return
        end
        if pf and pf.IsShown and pf:IsShown() then
            showCraftingPage()
        end
        tries = tries + 1
        if tries < 600 then C_Timer.After(0.3, tick) end
    end
    C_Timer.After(0.3, tick)
end

local function jumpCraft(stepIdx, opts)
    local s = st()
    if not (s and s.slug) then return end
    local _, steps = routeFor(s.slug, s.skill)
    local seg = steps and steps[stepIdx or (s.step or 1)]
    if not seg then return end
    local spellID = seg[3]
    if not IsLearned(spellID) then
        playCue("nol")
        craftNotify(L["该配方还未学会，先找训练师学习"])
        return
    end
    local rec = recMap(s.slug)[spellID]
    local mats = recMats(rec)
    local short = false
    if mats then
        for _, m in ipairs(mats) do
            if (Have(m[1]) or 0) < (m[2] or 1) then short = true break end
        end
    end
    if short then
        local sup = PF.SupplementNeeds(s.slug)
        if sup then
            craftNotify(format(L["本步材料不足：缺 %d 种共 %d 件，先按购物清单补齐"], sup.kinds, sup.qty))
        else
            craftNotify(L["材料不足，先按购物清单备齐再制造"])
        end
    end
    local count = math.max(1, math.ceil(craftsLeft(seg, s.skill)))
    local name = SpellName(spellID)
    if not name then craftNotify(L["配方数据未就绪，稍后再试"]) return end
    opts = opts or {}
    if not opts.noEvt then jumpEvtInit() end
    if openProfPanel(profSkillLine(s.slug)) then
        jumpPending = { spellID = spellID, count = count, name = name, opts = opts,
                        prof = (D.pro and D.pro[s.slug] and D.pro[s.slug].name) or "" }
        if C_Timer and C_Timer.After and not opts.noTimer then
            jumpPoll()
            C_Timer.After(0.4, function() if jumpPending then jumpApply() end end)
        else
            jumpApply()
        end
    else
        craftNotify(L["无法自动打开专业面板，请手动打开后重试"])
    end
end

PF.DebugJumpFull = function(opts) jumpCraft(nil, opts) end

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
                    if f then PF.Paint() end
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
    pcall(f.RegisterEvent, f, "SPELLS_CHANGED")
    pcall(f.RegisterEvent, f, "LEARNED_SPELL_IN_TAB")

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
            if not self.__it then return end
            local PD = ns.ProfModule
            local extra
            if PD and PD.PriceTipLines then
                extra = PD.PriceTipLines(self.__it[1], self.__mats)
            end
            DG.ShowItemTip(self, self.__it, extra)
            if self.__spell then
                DG.TipAppendLines({ { L["点击卡片：打开专业面板、定位本步配方并填好制作次数"], 0.62, 0.86, 1 } })
            end
        end)
        card:SetScript("OnLeave", function() GameTooltip:Hide() end)
        card:SetScript("OnMouseUp", function(self, button)
            if button == "LeftButton" and self.__spell then
                jumpCraft(self.__step)
                ns.PlaySound(1)
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
        for i = 1, MAT_MAX + 1 do
            BuildStep()
            card.__rowsMat[i] = MakeLine(card, 14, C_TEXT)
            local ic = card:CreateTexture(nil, "ARTWORK")
            ic:SetTexCoord(0.07, 0.93, 0.07, 0.93)
            if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(ic) end
            ic:SetSize(22, 22)
            ic:Hide()
            card.__rowsIcon[i] = ic
            local bd = MakeFS(card, 14, C_GOLD, "RIGHT")
            bd:SetFont(ns.FONT or "Fonts\\FRIZQT__.TTF", 14, "THICKOUTLINE")
            bd:SetShadowColor(0, 0, 0, 1)
            bd:SetShadowOffset(1, -1)
            bd:SetWordWrap(false)
            bd:Hide()
            card.__rowsBadge[i] = bd
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
            elseif r.srcKind == 3 then
                GameTooltip:AddLine(L["商人处直接出售"], 0.75, 0.75, 0.75, true)
            else
                GameTooltip:AddLine(L["拍卖行购买"], 0.75, 0.75, 0.75, true)
            end
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

    f.finish = MakeFS(f, 14, C_OK, "LEFT")
    f.finish:SetWordWrap(false)

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
            if DEFAULT_CHAT_FRAME and err then
                pcall(DEFAULT_CHAT_FRAME.AddMessage, DEFAULT_CHAT_FRAME,
                    "|cffff5555无限副本手册：HUD 构建失败|r " .. tostring(err), 1, 1, 1)
            end
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
    local rec = rm[seg[3]]
    local mats = recMats(rec)
    local rowsMat, rowsMatIcon, rowsMatBadge = card.__rowsMat, card.__rowsIcon, card.__rowsBadge
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
            if sold[m[1]] then txt = txt .. " · " .. L["商人直卖"] end
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

function PF.Paint()
    if not (f and f:IsShown()) then return end
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
    local atCap = (cur ~= nil and mx ~= nil and mx > 0 and cur >= mx)
    if atCap then
        if not PF.__capSaid then
            PF.__capSaid = true
            playCue("cap")
        end
    else
        PF.__capSaid = nil
    end
    local curStep = s.step or 1
    if PF.__lastSlug ~= slug then
        PF.__lastSlug = slug
        PF.__lastStep = curStep
    elseif PF.__lastStep ~= curStep then
        PF.__lastStep = curStep
        playCue("item")
    end
    if cur then
        f.skill:SetText(format(L["技能 %d / %d"], cur, mx or 300))
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
    f.seg:SetText(((mode == "auto") and L["自动计算"] or L["固定路线"]) .. " · "
                  .. format(L["段落 %d / %d"], vi, #steps))

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
    local TK = ns.ProfTrack
    local vRun = TK and TK.Active and TK.Active(slug)
    local vProg = vRun and TK.Progress and TK.Progress(slug, nil, vRun)
    local verShown = (not finished) and vProg ~= nil and vProg.item ~= nil and not vProg.finished

    local y = -82
    local pending = false

    if not finished then
        local rm = recMap(slug)
        local sold = soldSet(slug)
        local cands
        if viewing then
            cands = { vi }
        else
            cands = currentCands(steps, cur or s.skill or 0, s.step or 1)
            if #cands > 2 then
                cands = { cands[1], cands[2] }
            end
            if #cands >= 2 then
                local anyPos = false
                local cans = {}
                for k2, ci in ipairs(cands) do
                    local cc = canCraftOf(steps[ci], rm) or 0
                    cans[k2] = cc
                    if cc > 0 then anyPos = true end
                end
                if anyPos then
                    local kept = {}
                    for k2, ci in ipairs(cands) do
                        if cans[k2] > 0 then kept[#kept + 1] = ci end
                    end
                    if #kept > 0 then cands = kept end
                end
            end
        end
        local cards = { f.card, f.card2 }
        local painted = 0
        for _, ci in ipairs(cands) do
            painted = painted + 1
            local seg = steps[ci]
            local rec = rm[seg[3]]
            local card = cards[painted]
            local w = W - 2 * PAD - 16
            local isCur = (not viewing) or (ci == s.step)
            card.__step = ci
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
            local nmText = SpellName(seg[3])
            card.name:SetText(nmText)
            card.__nm = nmText
            card.__spell = seg[3]

            local crafts = seg[4] or 0
            local remaining = crafts
            if isCur then
                remaining = math.ceil(craftsLeft(seg, s.skill))
                crafts = remaining
            end
            local nMat, pend, canCraft = paintMats(card, seg, rm, sold, w - 8, remaining,
                                                   viewing and ((f.cardBtnW or 68) + 6) or 0)
            pending = pending or pend

            local learned = IsLearned(seg[3])
            local isTrainer = not (type(rec) == "table" and type(rec[13]) == "table"
                and type(rec[13][1]) == "number")
            local srcLabel, srcColor
            local CARD_COL = PDm and PDm.CARD_COL or {}
            if isTrainer then
                srcLabel, srcColor = L["训练师"], CARD_COL.trainer
            elseif PDm and PDm.LevelSrc then
                local _, _, kind = PDm.LevelSrc(rec)
                if kind == "vendor" then
                    srcLabel, srcColor = L["商人"], CARD_COL.vendor
                elseif kind == "drop" then
                    srcLabel, srcColor = L["掉落"], CARD_COL.drop
                elseif kind == "currency" then
                    srcLabel, srcColor = L["兑换"], CARD_COL.vendor
                elseif kind == "quest" then
                    srcLabel, srcColor = L["任务"], CARD_COL.both
                else
                    srcLabel, srcColor = L["图纸"], CARD_COL.both
                end
            end
            local chL, chS = card.chipLearn, card.chipSrc
            chL.lab:SetText(learned and L["已学"] or L["未学"])
            DG.BadgeTint(chL, learned and DG.Q_BADGE_SHARE_BG or DG.Q_BADGE_RACE_BG)
            local w1 = math.max(DG.Q_BADGE_MIN_W, (chL.lab:GetStringWidth() or 18) + DG.Q_BADGE_PAD * 2)
            chL:SetSize(w1, DG.Q_BADGE_H)
            local tagW = w1
            chL:ClearAllPoints()
            if srcLabel then
                chS.lab:SetText(srcLabel)
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
                local pv = TK.Progress(slug, ci, vRun)
                if pv and pv.item then
                    craftText = craftText .. "/" .. format(L["已生产%s"], numCol .. (pv.outputs or 0) .. "|r")
                end
            end
            card.crafts:SetText(craftText)
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

            local cardH = nMat * 26 + 60
            card:ClearAllPoints()
            card:SetPoint("TOPLEFT", f, "TOPLEFT", PAD, y)
            card:SetSize(W - 2 * PAD, cardH)
            y = y - cardH - 8
        end
        for k2 = painted + 1, #cards do
            cards[k2]:Hide()
        end
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
            local src = srcByID and srcByID[e.id] or nil
            local row = {
                nm = nm,
                have = e.have,
                need = e.need,
                missing = e.need - e.have,
                at = e.at or 0,
            }
            if row.at == math.huge then
                row.gate = true
                row.at = 0
            end
            if src and src.vendor and src.npcID then
                row.srcKind = 1
                row.npcID = src.npcID
                local full = (ns.ProfVendorNames and ns.ProfVendorNames[src.npcID]) or L["商人"]
                row.srcFull = full
                row.srcText = clipText(full, SRC_TEXT_W)
            elseif src and src.ah then
                row.srcKind = 2
                row.srcText = L["拍卖行"]
            elseif soldSet(slug)[e.id] then
                row.srcKind = 3
                row.srcText = L["直售"]
            end
            if row.srcText then row.srcW = math.min(SRC_COL_W, tw(row.srcText) + 12) end
            local w1 = tw(row.nm)
            if w1 > nameW then nameW = w1 end
            local w2 = tw(format("%d/%d", math.min(row.have, row.need), row.need))
            if w2 > numW then numW = w2 end
            local w3 = math.max(tw(L["已备齐"]), tw(format(L["缺%d"], row.need or 0))) + 10
            if w3 > missW then missW = w3 end
            local w5 = tw(row.gate and L["全程"] or format("%d+", row.at)) + 10
            if w5 > tagW then tagW = w5 end
            rows[#rows + 1] = row
        end
        if stepView then
            local lastAt = nil
            for _, e in ipairs(shown) do
                local at = e.at or 0
                if at == math.huge then at = 0 end
                if at ~= lastAt then
                    local htext = at > 0 and format(L["第 %d 步起"], at) or L["路线起点"]
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
                if row.srcText then
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
                else
                    srcp.__row = nil
                    srcp:Hide()
                end
                sp:Hide()
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
        f.finish:SetText(format(L["%s跟随完成 · %s"], name, fmtTime(time() - (s.t0 or time()))))
        f.finish:ClearAllPoints()
        f.finish:SetPoint("TOPLEFT", f, "TOPLEFT", 10, y)
        f.finish:Show()
        y = y - 34
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

function PF.ImportList(slug)
    local name = (D.pro and D.pro[slug] and D.pro[slug].name) or slug
    DoImport(slug, name)
end

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
        PF.ImportList(slug)
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
