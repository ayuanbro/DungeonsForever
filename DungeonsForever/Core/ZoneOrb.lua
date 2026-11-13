local _, ns = ...

local L = ns.L or function(k) return k end
local O = {}
ns.ZoneOrb = O

local ORB_SIZE = 48
local PANEL_W = 288
local PAD = 12
local CARD_H = 52
local HEAD_H = 20
local ROW_H = 44
local ROW_GAP = 6
local ROW_MAX = 8
local GAP = 8
local SLIDE = 26
local CLOSE_S = 36
local SIDE_S = 29

local FOOD_CUE = "Interface\\AddOns\\DungeonsForever\\Media\\Voice\\todo_food.ogg"
local RESTED_CUE = "Interface\\AddOns\\DungeonsForever\\Media\\Voice\\todo_rested.ogg"
local ON_CUE = "Interface\\AddOns\\DungeonsForever\\Media\\Voice\\prof_voice_on.ogg"
local OFF_CUE = "Interface\\AddOns\\DungeonsForever\\Media\\Voice\\todo_voice_off.ogg"
local MANAGE_S = 23
local GLYPH = 0xA0 / 255
local TOP_Y = -48
local TEXT = { 0.95, 0.96, 0.98 }
local DIM = { 0.63, 0.65, 0.68 }
local FAINT = { 0.50, 0.51, 0.53 }
local ACC = (ns.hui and ns.hui.ACCENT) or { 0x46 / 255, 0xbf / 255, 0x72 / 255 }
local GRAY = (ns.hui and ns.hui.TEXT and ns.hui.TEXT[3]) or DIM

local orb, panel, badge, badgeText, tweener, icon, disc, ring, voiceBtn
local cards, heads, subRows, row, btnOpen, btnSkip, btnBlock, manage, moreText
local Tip, HideTip
local closeBtn, gear, opts, optCbs
local foodMenu, foodRows, foodCatch, FoodMenuClose = nil, {}, nil, nil
local orbMenu, menuOpenedAt = nil, 0
local job = nil
local current = nil
local hovered = false
local lastFood, lastRested = false, false
local openedAt = 0
local hideToken = 0
local closePending = false
local lastN = -1
local pulseFrame, pulseT = nil, 0

local function Cfg()
    return ns.ZoneHint and ns.ZoneHint.CFG and ns.ZoneHint.CFG() or {}
end

local VOICE_SEC = {
    ["todo_food.ogg"] = 1.45,
    ["todo_rested.ogg"] = 1.45,
    ["prof_voice_on.ogg"] = 1.05,
    ["todo_voice_off.ogg"] = 0.95,
    ["prof_next_item.ogg"] = 1.35,
    ["prof_not_learned.ogg"] = 1.12,
    ["prof_skill_cap.ogg"] = 1.40,
}

local vq, vUntil, vTimer, vHandle = {}, 0, nil, nil

local function Now()
    return (GetTime and GetTime()) or 0
end

local vBootHold = Now() + 30
local VOICE_CD = 300
local vLast = {}

local function VoiceDrain()
    if #vq == 0 then return end
    local hold = (vUntil > vBootHold) and vUntil or vBootHold
    if Now() < hold then
        if not vTimer and type(C_Timer) == "table" and type(C_Timer.After) == "function" then
            vTimer = true
            C_Timer.After(hold - Now() + 0.04, function()
                vTimer = nil
                VoiceDrain()
            end)
        end
        return
    end
    local it = table.remove(vq, 1)
    if not it.force and Cfg().voice ~= true then
        vq = {}
        return
    end
    if type(PlaySoundFile) ~= "function" then
        vq = {}
        return
    end
    local ok, _, h = pcall(PlaySoundFile, it.path, "Master")
    vHandle = (ok and h) or nil
    vLast[it.path] = Now()
    local f = string.match(it.path, "([^\\]+)$") or ""
    vUntil = Now() + (VOICE_SEC[f] or 1.5) + 0.05
    if #vq > 0 then VoiceDrain() end
end

function O.SayVoice(path, urgent)
    if type(path) ~= "string" then return end
    if urgent == true then
        if vHandle and type(StopSound) == "function" then pcall(StopSound, vHandle) end
        vHandle, vUntil, vBootHold = nil, 0, 0
        vq = {}
    else
        if Cfg().voice ~= true then return end
        local last = vLast[path]
        if last and Now() - last < VOICE_CD then return end
        for i = 1, #vq do
            if vq[i].path == path then return end
        end
        if #vq >= 4 then return end
    end
    vq[#vq + 1] = { path = path, force = (urgent == true) }
    VoiceDrain()
end

local function ApplyOrbSize()
    if not orb then return end
    local sz = tonumber(Cfg().icon) or 32
    if sz < 20 then sz = 20 end
    if sz > 44 then sz = 44 end
    local orbSz = sz + 16
    orb:SetSize(orbSz, orbSz)
    local shown = sz * 1.25
    local ringSz = shown * 55 / 36
    if icon then icon:SetSize(shown, shown) end
    if disc then disc:SetSize(ringSz * 0.80, ringSz * 0.80) end
    if ring then ring:SetSize(ringSz, ringSz) end
end

local function PaintRing(n)
    if not ring then return end
    if hovered then
        ring:SetDesaturated(false)
        ring:SetVertexColor(1, 0.95, 0.65, 1)
    elseif (n or 0) > 0 then
        ring:SetDesaturated(false)
        ring:SetVertexColor(1, 0.85, 0.4, 1)
    else
        ring:SetDesaturated(true)
        ring:SetVertexColor(0.58, 0.58, 0.58, 1)
    end
end

local function PaintVoiceBtn()
    if not (voiceBtn and voiceBtn.tex) then return end
    local muted = Cfg().voice ~= true
    if muted then
        voiceBtn.tex:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\Prof\\prof_mute.tga")
        voiceBtn.tex:SetVertexColor(0.95, 0.32, 0.32, 0.98)
    else
        voiceBtn.tex:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\Prof\\prof_voice_on.tga")
        voiceBtn.tex:SetVertexColor(GLYPH, GLYPH, GLYPH, 1)
    end
end

local function TextW(fs, dflt)
    local w = fs and fs.GetStringWidth and fs:GetStringWidth()
    if type(w) == "number" then return w end
    local t = fs and fs.GetText and fs:GetText()
    if type(t) == "string" and #t > 0 then return #t * 7 end
    return dflt or 0
end

local function SavePos()
    if not orb then return end
    local c = Cfg()
    local p, _, rp, x, y = orb:GetPoint(1)
    if p then
        c.orb = { p = p, rp = rp or p, x = x or 0, y = y or 0 }
    end
end

local function ApplyPos()
    local c = Cfg()
    local o = c.orb
    orb:ClearAllPoints()
    if type(o) == "table" and o.p then
        orb:SetPoint(o.p, UIParent, o.rp or o.p, o.x or 0, o.y or 0)
    else
        orb:SetPoint("LEFT", UIParent, "LEFT", 12, 0)
    end
end

local function StartTween(dur, apply, done)
    job = { t = 0, dur = dur, apply = apply, done = done }
    if tweener then tweener:Show() end
end

function O.ArmGhost()
    if not orb or not orb:IsShown() or orb:GetAlpha() == 0 then return end
    if orb.ghostPending then return end
    orb.ghostPending = true
    orb.ghostTok = (orb.ghostTok or 0) + 1
    local my = orb.ghostTok
    if type(C_Timer) ~= "table" or type(C_Timer.After) ~= "function" then return end
    C_Timer.After(2.5, function()
        orb.ghostPending = false
        if my ~= orb.ghostTok then return end
        if orb:IsMouseOver() or (panel and panel:IsShown()) or (opts and opts:IsShown()) then return end
        local c = Cfg()
        if c.on == false or not c.onlyTodo then return end
        if current and (current.total or 0) > 0 then return end
        if orb:GetAlpha() ~= 0 then orb:SetAlpha(0) end
        orb.revealed = false
    end)
end

local function Close()
    if not panel or not panel:IsShown() then
        closePending = false
        return
    end
    if InCombatLockdown and InCombatLockdown() then
        closePending = true
        return
    end
    closePending = false
    if FoodMenuClose then FoodMenuClose() end
    hideToken = hideToken + 1
    StartTween(0.12, function(e)
        panel:SetAlpha(1 - e)
    end, function()
        panel:Hide()
        panel:SetAlpha(1)
    end)
end

local function FlushClose()
    if not closePending then return end
    if InCombatLockdown and InCombatLockdown() then
        if type(C_Timer) == "table" and type(C_Timer.After) == "function" then
            C_Timer.After(0.2, FlushClose)
        end
        return
    end
    Close()
end

local function StartHideTimer(keep)
    hideToken = hideToken + 1
    local my = hideToken
    local d = keep and 40 or (tonumber(Cfg().dur) or 12)
    if d <= 0 then return end
    if type(C_Timer) ~= "table" or type(C_Timer.After) ~= "function" then return end
    C_Timer.After(d, function()
        if my ~= hideToken then return end
        if foodMenu and foodMenu:IsShown() then return end
        if opts and opts:IsShown() then return end
        if panel and panel:IsShown() and not hovered then Close() end
    end)
end

local function SubText(s)
    local parts = {}
    if s.learn then parts[#parts + 1] = string.format(L["%d 级可学"], s.learn) end
    if s.rank then parts[#parts + 1] = string.format(L["第 %d 阶"], s.rank) end
    if #parts == 0 then
        if s.tab and s.tab ~= "" then return s.tab end
        return L["可学"]
    end
    return table.concat(parts, " · ")
end

local function FitBtn(bt, text, fixedW)
    if not (bt and text and text ~= "") then return end
    bt:SetText(text)
    if fixedW then
        bt:SetWidth(fixedW)
        return
    end
    local fs = bt:GetFontString()
    local w = 0
    if fs then
        fs:SetText(text)
        w = fs:GetStringWidth() or 0
    end
    w = math.floor(w + 24)
    if w < 60 then w = 60 end
    bt:SetWidth(w)
end

local function BtnTextW(bt, text)
    if not (bt and text and text ~= "") then return 0 end
    local fs = bt:GetFontString()
    if not fs then return 0 end
    fs:SetText(text)
    return fs:GetStringWidth() or 0
end

local function UniformW(bt, a, b, c)
    local m = BtnTextW(bt, a)
    local w = BtnTextW(bt, b)
    if w > m then m = w end
    w = BtnTextW(bt, c)
    if w > m then m = w end
    m = math.floor(m + 16)
    if m < 62 then m = 62 end
    if m > 78 then m = 78 end
    return m
end

local function MakeCard(i)
    local card = cards[i]
    if card then return card end
    card = CreateFrame("Frame", nil, panel, "BackdropTemplate")
    if ns.hui and ns.hui.SkinPopup and ns.hui.layer then
        ns.hui.SkinPopup(card, 8, "both", ns.hui.layer.L1)
    end
    card.icon = card:CreateTexture(nil, "ARTWORK")
    card.icon:SetSize(32, 32)
    card.icon:SetPoint("TOPLEFT", card, "TOPLEFT", 10, -10)
    card.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
    card.icon:Hide()
    card.title = card:CreateFontString(nil, "OVERLAY")
    card.title:SetFont(ns.FONT, 14, "")
    card.title:SetPoint("TOPLEFT", card, "TOPLEFT", 50, -9)
    card.title:SetJustifyH("LEFT")
    card.title:SetWidth(PANEL_W - PAD * 2 - 60)
    card.title:SetWordWrap(false)
    card.title:SetTextColor(TEXT[1], TEXT[2], TEXT[3])
    card.name = card:CreateFontString(nil, "OVERLAY")
    card.name:SetFont(ns.FONT, 12, "")
    card.name:SetPoint("LEFT", card.title, "RIGHT", 6, -1)
    card.name:SetJustifyH("LEFT")
    card.name:SetWordWrap(false)
    card.name:SetTextColor(GRAY[1], GRAY[2], GRAY[3])
    card.text = card:CreateFontString(nil, "OVERLAY")
    card.text:SetFont(ns.FONT, 12, "")
    card.text:SetPoint("TOPLEFT", card, "TOPLEFT", 50, -27)
    card.text:SetJustifyH("LEFT")
    card.text:SetTextColor(DIM[1], DIM[2], DIM[3])
    card.text:SetWidth(PANEL_W - PAD * 2 - 60)
    card.text:SetWordWrap(false)
    if ns.hui and ns.hui.MakeSolidChip then
        card.chip = ns.hui.MakeSolidChip(card, panel:GetFrameLevel() + 3)
        card.chip:SetPoint("TOPRIGHT", card, "TOPRIGHT", -8, -7)
    end
    card.act = ns.CreateButton(card)
    card.act:SetSize(74, 22)
    card.act:SetPoint("BOTTOMRIGHT", card, "BOTTOMRIGHT", -8, 8)
    card.act:SetScript("OnClick", function()
        ns.PlaySound(1)
        if card.onAct then card.onAct() end
        if O.Refresh then O.Refresh() end
    end)
    card.act:SetScript("OnEnter", function()
        if card.hint then Tip(card.act, card.hint, nil) end
    end)
    card.act:SetScript("OnLeave", HideTip)
    card.act:Hide()
    card.act2 = ns.CreateButton(card)
    card.act2:SetSize(74, 22)
    card.act2:SetPoint("BOTTOMRIGHT", card.act, "BOTTOMLEFT", -6, 0)
    card.act2:SetScript("OnClick", function()
        ns.PlaySound(1)
        if card.onAct2 then card.onAct2() end
        if O.Refresh then O.Refresh() end
    end)
    card.act2:SetScript("OnEnter", function()
        if card.hint2 then Tip(card.act2, card.hint2, nil) end
    end)
    card.act2:SetScript("OnLeave", HideTip)
    card.act2:Hide()
    card.act3 = ns.CreateButton(card)
    card.act3:SetSize(74, 22)
    card.act3:SetScript("OnEnter", function()
        if card.hint3 then Tip(card.act3, card.hint3, nil) end
    end)
    card.act3:SetScript("OnLeave", HideTip)
    card.act3:Hide()
    card.stat = card:CreateFontString(nil, "OVERLAY")
    card.stat:SetFont(ns.FONT, 12, "")
    card.stat:SetPoint("RIGHT", card.act, "LEFT", -8, 0)
    card.stat:SetJustifyH("RIGHT")
    card.stat:SetWordWrap(false)
    card.stat:SetWidth(150)
    card.stat:SetTextColor(FAINT[1], FAINT[2], FAINT[3])
    card.stat:Hide()
    cards[i] = card
    return card
end

local function MakeHead(i)
    local h = heads[i]
    if h then return h end
    h = CreateFrame("Frame", nil, panel)
    h.label = h:CreateFontString(nil, "OVERLAY")
    h.label:SetFont(ns.FONT, 14, "")
    h.label:SetPoint("LEFT", h, "LEFT", 2, 0)
    h.label:SetTextColor(TEXT[1], TEXT[2], TEXT[3])
    h.cnt = h:CreateFontString(nil, "OVERLAY")
    h.cnt:SetFont(ns.FONT, 14, "")
    h.cnt:SetPoint("RIGHT", h, "RIGHT", -2, 0)
    h.cnt:SetTextColor(FAINT[1], FAINT[2], FAINT[3])
    heads[i] = h
    return h
end

HideTip = function()
    if GameTooltip then GameTooltip:Hide() end
end

local function AddGray(text)
    if text and text ~= "" then
        GameTooltip:AddLine(text, 0.82, 0.86, 0.90, true)
    end
end

local function AddAccent(text)
    if text and text ~= "" then
        GameTooltip:AddLine(text, ACC[1], ACC[2], ACC[3], true)
    end
end

Tip = function(owner, title, desc, foot)
    if not (GameTooltip and owner) then return end
    GameTooltip:SetOwner(owner, "ANCHOR_RIGHT")
    GameTooltip:ClearLines()
    GameTooltip:AddLine(title or "", 1, 1, 1, true)
    AddGray(desc)
    AddAccent(foot)
    GameTooltip:Show()
end

local function ItemTip(owner, id, name, desc, foot)
    if not (GameTooltip and owner) then return end
    GameTooltip:SetOwner(owner, "ANCHOR_RIGHT")
    local ok = false
    if id and GameTooltip.SetItemByID then
        ok = pcall(GameTooltip.SetItemByID, GameTooltip, id)
        if ok then ok = (GameTooltip:NumLines() or 0) > 0 end
    end
    if not ok then
        GameTooltip:ClearLines()
        GameTooltip:AddLine(name or "", 1, 1, 1, true)
    end
    AddGray(desc)
    AddAccent(foot)
    GameTooltip:Show()
end

local function SpellTip(owner, id, name, sub, foot)
    if not (GameTooltip and owner) then return end
    GameTooltip:SetOwner(owner, "ANCHOR_RIGHT")
    local ok = false
    if id and GameTooltip.SetSpellByID then
        ok = pcall(GameTooltip.SetSpellByID, GameTooltip, id)
        if ok then ok = (GameTooltip:NumLines() or 0) > 0 end
    end
    if not ok then
        GameTooltip:ClearLines()
        GameTooltip:AddLine(name or "", 1, 1, 1, true)
    end
    AddGray(sub)
    AddAccent(foot)
    GameTooltip:Show()
end

local function OpenQuestPage(qid, slug)
    if not qid then return false end
    local U = ns.DungeonUI
    if not U then return false end
    if slug and ns.ShowDungeonDetail then
        if not pcall(ns.ShowDungeonDetail, slug) then return false end
    elseif ns.Open then
        pcall(ns.Open)
    end
    U.dungeonQView = "list"
    U.dungeonQFlow = nil
    U.dungeonQuestSel = qid
    U.dungeonQListKey = nil
    U.dungeonQDetKey = nil
    local DG = ns.DungeonDG or (ns.ProfHost and ns.ProfHost.DG)
    local row = (DG and DG.QuestRowByID) and DG.QuestRowByID(qid) or nil
    local qsd = (type(row) == "table") and row[2] or nil
    if (qsd == "A" or qsd == "H") and U.dungeonQSide ~= qsd then U.dungeonQSide = qsd end
    if U.SetDungeonTab then pcall(U.SetDungeonTab, U, "quest") end
    if ns.MapModule and ns.MapModule.QuestScrollTo then pcall(ns.MapModule.QuestScrollTo, qid) end
    return true
end

local function MarkOnMap(it)
    if not it then return false end
    local EG = ns.ExploreModule
    if it.areaID and it.x and it.y and EG and EG.MarkPoint then
        local ok = pcall(EG.MarkPoint, it.areaID, it.x, it.y)
        if ok then return true end
    end
    local mapID = it.mapID or (current and current.ctx and current.ctx.mapID)
    if mapID and it.x and it.y and UiMapPoint and UiMapPoint.CreateFromCoordinates
       and C_Map and C_Map.SetUserWaypoint then
        local ok, pt = pcall(UiMapPoint.CreateFromCoordinates, mapID, it.x / 100, it.y / 100)
        if ok and pt then
            pcall(C_Map.SetUserWaypoint, pt)
            if C_SuperTrack and C_SuperTrack.SetSuperTrackedUserWaypoint then
                pcall(C_SuperTrack.SetSuperTrackedUserWaypoint, false)
            end
            if C_Map.OpenWorldMap then pcall(C_Map.OpenWorldMap, mapID) end
            return true
        end
    end
    if it.qid and ns.MapUI and ns.MapUI.GotoQuest then
        pcall(ns.MapUI.GotoQuest, it.qid, false)
        return true
    end
    return false
end

local function MakeRow(i)
    local r = subRows[i]
    if r then return r end
    r = CreateFrame("Button", nil, panel, "BackdropTemplate")
    local fx = ns.hui and ns.hui.HuiCardFX and ns.hui.HuiCardFX(r, 6, 1)
    if not fx and ns.hui and ns.hui.SkinPopup and ns.hui.layer then
        ns.hui.SkinPopup(r, 8, "both", ns.hui.layer.L1)
    end
    r.icon = r:CreateTexture(nil, "ARTWORK")
    r.icon:SetSize(32, 32)
    r.icon:SetPoint("TOPLEFT", r, "TOPLEFT", 8, -6)
    r.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
    r.sym = r:CreateTexture(nil, "OVERLAY")
    r.sym:SetAllPoints(r.icon)
    r.sym:Hide()
    r.name = r:CreateFontString(nil, "OVERLAY")
    r.name:SetFont(ns.FONT, 14, "")
    r.name:SetPoint("TOPLEFT", r, "TOPLEFT", 48, -6)
    r.name:SetTextColor(TEXT[1], TEXT[2], TEXT[3])
    r.name:SetWidth(PANEL_W - PAD * 2 - 82)
    r.name:SetWordWrap(false)
    r.name:SetJustifyH("LEFT")
    r.sub = r:CreateFontString(nil, "OVERLAY")
    r.sub:SetFont(ns.FONT, 12, "")
    r.sub:SetPoint("TOPLEFT", r, "TOPLEFT", 48, -26)
    r.sub:SetTextColor(DIM[1], DIM[2], DIM[3])
    r.sub:SetWidth(PANEL_W - PAD * 2 - 82)
    r.sub:SetWordWrap(true)
    r.sub:SetJustifyH("LEFT")
    r.btn = CreateFrame("Button", nil, r)
    r.btn:SetSize(24, 24)
    r.btn:SetPoint("RIGHT", r, "RIGHT", -6, 0)
    r.btn:SetFrameLevel(r:GetFrameLevel() + 6)
    r.xt = r.btn:CreateFontString(nil, "OVERLAY")
    r.xt:SetFont(ns.FONT, 18, "")
    r.xt:SetPoint("CENTER", r.btn, "CENTER", 0, 0)
    r.xt:SetText("×")
    r.xt:SetTextColor(FAINT[1], FAINT[2], FAINT[3])
    r.btn:SetScript("OnEnter", function()
        r.xt:SetTextColor(0.89, 0.30, 0.29)
        Tip(r.btn, L["忽略此条"], L["以后不再提醒这一条"], L["可在管理忽略里恢复"])
    end)
    r.btn:SetScript("OnLeave", function()
        r.xt:SetTextColor(FAINT[1], FAINT[2], FAINT[3])
        HideTip()
    end)
    r.btn:SetScript("OnClick", function()
        ns.PlaySound(1)
        if r.ikey and ns.ZoneHint and ns.ZoneHint.IgnoreItem then
            ns.ZoneHint.IgnoreItem(r.ikind, r.iid, r.ilabel)
        end
        O.Refresh()
    end)
    r:RegisterForClicks("LeftButtonUp", "RightButtonUp")
    r:SetScript("OnClick", function(_, btn)
        if not r.jump then return end
        if ns.ZoneHint and ns.ZoneHint.IsSim and ns.ZoneHint.IsSim() then return end
        if btn == "RightButton" then
            if r.ikind ~= "quest" then return end
            if OpenQuestPage(r.qid or r.iid, r.slug) then Close() end
            return
        end
        ns.PlaySound(1)
        Close()
        r.jump()
    end)
    r:SetScript("OnEnter", function()
        if ns.hui and ns.hui.HuiCardState then ns.hui.HuiCardState(r, "hover") end
        r.name:SetTextColor(ACC[1], ACC[2], ACC[3])
        local sub = r.sub:GetText()
        if r.ikind == "turnin" then
            ItemTip(r, r.iid, r.ilabel, r.idesc or sub, L["点击在地图上定位上交 NPC"])
        elseif r.ikind == "book" or r.ikind == "collect" or r.ikind == "rested" then
            local desc = sub
            if r.idesc and r.idesc ~= "" then
                desc = (sub ~= "" and (sub .. " · " .. r.idesc)) or r.idesc
            end
            ItemTip(r, r.iid, r.ilabel, desc, r.jumpTip or L["点击在地图标出位置"])
        elseif r.ikind == "quest" then
            Tip(r, r.ilabel, r.idesc or sub, L["左键在地图上定位，右键查看任务详情"])
        elseif r.ikind == "talent" then
            Tip(r, r.ilabel, r.idesc or sub, r.jumpTip or L["点击打开天赋界面"])
        else
            SpellTip(r, r.itipid or r.iid, r.ilabel, sub)
        end
    end)
    r:SetScript("OnLeave", function()
        if ns.hui and ns.hui.HuiCardState then ns.hui.HuiCardState(r, "norm") end
        r.name:SetTextColor(TEXT[1], TEXT[2], TEXT[3])
        HideTip()
    end)
    subRows[i] = r
    return r
end

local function ActBtn(host, key)
    if not host.actBtns then host.actBtns = {} end
    local b = host.actBtns[key]
    if b then return b end
    if InCombatLockdown() then return nil end
    local okc, btn = pcall(CreateFrame, "Button", "DFZoneOrbAct_" .. key, host, "SecureActionButtonTemplate")
    if not okc or not btn then return nil end
    btn:RegisterForClicks("AnyUp", "AnyDown")
    btn:SetAttribute("useOnKeyDown", (GetCVarBool and GetCVarBool("ActionButtonUseKeyDown")) or false)
    btn:SetScript("PreClick", function(self, mouse)
        if mouse == "LeftButton" then
            if self.actKind == "item" then
                self:SetAttribute("type", "item")
                self:SetAttribute("macrotext", nil)
                self:SetAttribute("item", self.actValue)
            elseif self.actKind == "macro" then
                self:SetAttribute("type", "macro")
                self:SetAttribute("item", nil)
                self:SetAttribute("macrotext", self.actValue)
            end
        elseif self:GetAttribute("type") then
            self:SetAttribute("type", nil)
        end
    end)
    btn:SetScript("OnEnter", function(self)
        if self.tipText then Tip(self, self.tipText, nil) end
    end)
    btn:SetScript("OnLeave", function() HideTip() end)
    btn:HookScript("OnClick", function(self, mouse, down)
        if down then return end
        if mouse == "RightButton" and self.onRight then self.onRight() end
    end)
    host.actBtns[key] = btn
    return btn
end

local function ActPlace(btn, target, tipText, kind, value, h, inset, onRight)
    if not (btn and target) or InCombatLockdown() then return false end
    btn.tipText = tipText
    btn.onRight = onRight
    btn:SetAttribute("type1", nil)
    btn:SetAttribute("item1", nil)
    btn:SetAttribute("macrotext1", nil)
    if value then
        if kind == "item" then
            btn.actKind, btn.actValue = "item", value
            btn:SetAttribute("type", "item")
            btn:SetAttribute("macrotext", nil)
            btn:SetAttribute("item", value)
        else
            btn.actKind, btn.actValue = "macro", value
            btn:SetAttribute("type", "macro")
            btn:SetAttribute("item", nil)
            btn:SetAttribute("macrotext", value)
        end
    else
        btn.actKind, btn.actValue = nil, nil
        btn:SetAttribute("type", nil)
        btn:SetAttribute("item", nil)
        btn:SetAttribute("macrotext", nil)
    end
    local d = inset or 0
    btn:ClearAllPoints()
    btn:SetPoint("TOPLEFT", target, "TOPLEFT", d, -d)
    btn:SetPoint("TOPRIGHT", target, "TOPRIGHT", -d, -d)
    btn:SetHeight(h or (target:GetHeight() - d * 2))
    btn:SetFrameLevel(target:GetFrameLevel() + 3)
    btn:Show()
    btn.usedNow = true
    return true
end

FoodMenuClose = function()
    if foodMenu then foodMenu:Hide() end
    if foodCatch then foodCatch:Hide() end
    _G.DFFoodMenuUp = nil
end

local function PickFood(self)
    if not self or not self.foodID then return end
    if not foodMenu then return end
    _G.DFMenuLog = "pick:" .. tostring(self.foodID) .. ":" .. tostring(self.tok)
    if foodMenu.tok == nil or self.tok ~= foodMenu.tok then return end
    foodMenu.tok = -1
    local c = ns.ZoneHint and ns.ZoneHint.CFG and ns.ZoneHint.CFG()
    if c then c.preferFood = self.foodID end
    if ns.PlaySound then ns.PlaySound(1) end
    FoodMenuClose()
    local res = O.Refresh and O.Refresh()
    _G.DFMenuLog = _G.DFMenuLog .. "/pref=" .. tostring(c and c.preferFood) .. "/panel=" .. tostring(panel and panel:IsShown())
    if panel and not panel:IsShown() then
        if res then O.ForceOpen(res) elseif current then O.ForceOpen(current) end
    end
end

local function FoodMenuRow(i)
    local r = foodRows[i]
    if r then return r end
    r = CreateFrame("Button", nil, foodMenu, "BackdropTemplate")
    r:SetBackdrop({ edgeFile = "Interface/ChatFrame/ChatFrameBackground", edgeSize = 1 })
    r:SetBackdropBorderColor(0, 0, 0, 1)
    r.tex = r:CreateTexture(nil, "ARTWORK")
    r.tex:SetSize(16, 16)
    r.tex:SetPoint("LEFT", r, "LEFT", 6, 0)
    r.tex:SetTexCoord(0.07, 0.93, 0.07, 0.93)
    r.lab = r:CreateFontString(nil, "OVERLAY")
    r.lab:SetFont(ns.FONT, 12, "")
    r.lab:SetPoint("LEFT", r.tex, "RIGHT", 6, 0)
    r.lab:SetPoint("RIGHT", r, "RIGHT", -8, 0)
    r.lab:SetJustifyH("LEFT")
    r.lab:SetWordWrap(false)
    r.lab:SetTextColor(TEXT[1], TEXT[2], TEXT[3])
    r.hi = r:CreateTexture(nil, "HIGHLIGHT")
    r.hi:SetAllPoints()
    r.hi:SetColorTexture(ACC[1], ACC[2], ACC[3], 0.18)
    r:SetScript("OnEnter", function(self)
        if self.foodName then Tip(self, self.foodName, nil) end
    end)
    r:SetScript("OnLeave", function() HideTip() end)
    r:SetScript("OnMouseDown", function(self, mouse)
        if mouse == "LeftButton" then
            _G.DFMenuRowDown = "row:" .. tostring(self.foodID) .. ":" .. tostring(self.tok) .. ":" .. tostring(foodMenu.tok)
            PickFood(self)
        end
    end)
    r:SetScript("OnMouseUp", function(self, mouse)
        if mouse == "LeftButton" then PickFood(self) end
    end)
    r:SetScript("OnClick", function(self) PickFood(self) end)
    foodRows[i] = r
    return r
end

function O.FoodMenu()
    if foodMenu and foodMenu:IsShown() then FoodMenuClose() return end
    local list = (ns.ZoneHint and ns.ZoneHint.FoodList and ns.ZoneHint.FoodList()) or {}
    if #list == 0 then return end
    if not panel then return end
    if not foodCatch then
        foodCatch = CreateFrame("Frame", "DFZoneOrbFoodCatch", UIParent)
        foodCatch:SetAllPoints(UIParent)
        foodCatch:SetFrameStrata("FULLSCREEN_DIALOG")
        foodCatch:EnableMouse(true)
        foodCatch:SetScript("OnMouseDown", function()
            _G.DFMenuCatch = tostring((GetTime and GetTime()) or 0)
            FoodMenuClose()
        end)
        foodCatch:Hide()
    end
    if not foodMenu then
        foodMenu = CreateFrame("Frame", "DFZoneOrbFoodMenu", UIParent, "BackdropTemplate")
        foodMenu:SetFrameStrata("FULLSCREEN_DIALOG")
        foodMenu:SetFrameLevel(200)
        if ns.hui and ns.hui.SkinPopup and ns.hui.layer then
            ns.hui.SkinPopup(foodMenu, 8, "both", ns.hui.layer.L2)
        end
        foodMenu:EnableMouse(true)
        foodMenu:SetScript("OnMouseDown", function() end)
        foodMenu:SetScript("OnMouseUp", function() end)
        foodMenu.title = foodMenu:CreateFontString(nil, "OVERLAY")
        foodMenu.title:SetFont(ns.FONT, 12, "")
        foodMenu.title:SetPoint("TOPLEFT", foodMenu, "TOPLEFT", 10, -8)
        foodMenu.title:SetTextColor(GRAY[1], GRAY[2], GRAY[3])
        foodMenu.title:SetText(L["选择食物"])
    end
    local shown = #list > 8 and 8 or #list
    local tok = (tonumber(foodMenu.tok) or 0) + 1
    if tok < 1 then tok = 1 end
    foodMenu.tok = tok
    local y = -26
    for i = 1, shown do
        local e = list[i]
        local r = FoodMenuRow(i)
        r.foodID, r.foodName = e.id, e.name
        r.tok = tok
        r.tex:SetTexture(e.icon)
        r.lab:SetText(string.format("%s ×%d", e.name, e.count))
        r:ClearAllPoints()
        r:SetPoint("TOPLEFT", foodMenu, "TOPLEFT", 6, y)
        r:SetPoint("TOPRIGHT", foodMenu, "TOPRIGHT", -6, y)
        r:SetHeight(22)
        r:SetFrameLevel(foodMenu:GetFrameLevel() + 2)
        r:Show()
        y = y - 23
    end
    for i = shown + 1, #foodRows do foodRows[i]:Hide() end
    local w = 150
    if not foodMenu.meas then
        foodMenu.meas = foodMenu:CreateFontString(nil, "OVERLAY")
        foodMenu.meas:SetFont(ns.FONT, 12, "")
        foodMenu.meas:SetWordWrap(false)
        foodMenu.meas:Hide()
    end
    for i = 1, shown do
        foodMenu.meas:SetText(foodRows[i].lab:GetText() or "")
        local tw = TextW(foodMenu.meas, 100) + 52
        if tw > w then w = tw end
    end
    if w > 320 then w = 320 end
    foodMenu:SetSize(w, -y + 4)
    foodMenu:ClearAllPoints()
    local uiW = (UIParent and UIParent:GetWidth()) or 1920
    local rx = (panel:GetRight() or 0)
    if rx > 0 and rx + 8 + w > uiW - 10 then
        foodMenu:SetPoint("RIGHT", panel, "LEFT", -8, 0)
    else
        foodMenu:SetPoint("LEFT", panel, "RIGHT", 8, 0)
    end
    foodMenu.shownAt = (GetTime and GetTime()) or 0
    foodCatch:SetFrameLevel(foodMenu:GetFrameLevel() - 1)
    foodCatch:Show()
    foodMenu:Show()
    _G.DFFoodMenuUp = true
    _G.DFMenuOpen = string.format("%s/%.0f,%.0f %.0fx%.0f/lvl%s/rows%d",
        tostring(foodMenu:GetParent() and foodMenu:GetParent():GetName() or "?"),
        foodMenu:GetLeft() or -1, foodMenu:GetBottom() or -1,
        foodMenu:GetWidth() or -1, foodMenu:GetHeight() or -1,
        tostring(foodMenu:GetFrameLevel()), shown)
end

local function Layout(res)
    local list = (res and res.items) or {}
    local n = #list
    local ci, hi, ri = 0, 0, 0
    if moreText then moreText:Hide() end

    local want = {}
    for i = 1, n do
        local subs = list[i].list
        if type(subs) == "table" and #subs > 0 then want[i] = #subs end
    end

    local iconSz = tonumber(Cfg().icon) or 32
    if iconSz < 20 then iconSz = 20 end
    if iconSz > 44 then iconSz = 44 end
    local rowH = ROW_H
    if iconSz + 12 > rowH then rowH = iconSz + 12 end
    local textLeft = iconSz + 16
    local textW = PANEL_W - PAD * 2 - textLeft - 36

    local function SubExtraH(s)
        local t = s and s.sub
        if type(t) ~= "string" then return 0 end
        local nl = 0
        for _ in t:gmatch("\n") do nl = nl + 1 end
        return nl * 16
    end

    local function HeightFor(cap)
        local h = 0
        for i = 1, n do
            local c = want[i]
            if c and c > 0 then
                local shown = c > cap and cap or c
                local ex = 0
                local sl = list[i].list
                if sl then
                    for k = 1, math.min(shown, #sl) do ex = ex + SubExtraH(sl[k]) end
                end
                h = h + HEAD_H + 2 + shown * (rowH + ROW_GAP) + ex
                if c > shown then h = h + 18 end
            else
                local cardH = CARD_H
                if list[i] and list[i].btn then cardH = CARD_H + 26 end
                h = h + cardH + GAP
            end
        end
        return h
    end

    local maxH = ((UIParent and UIParent:GetHeight()) or 900) - 120
    local cap = ROW_MAX
    while cap > 1 and HeightFor(cap) > maxH do cap = cap - 1 end

    local y = TOP_Y
    local contentBottom = nil
    for i = 1, n do
        local it = list[i]
        local subs = it.list
        if type(subs) == "table" and #subs > 0 then
            hi = hi + 1
            local h = MakeHead(hi)
            h:ClearAllPoints()
            h:SetPoint("TOPLEFT", panel, "TOPLEFT", PAD, y)
            h:SetPoint("TOPRIGHT", panel, "TOPRIGHT", -PAD, y)
            h:SetHeight(HEAD_H)
            h.label:SetText(it.title or "")
            h.cnt:SetText(string.format(L["%d 个"], #subs))
            h:Show()
            y = y - (HEAD_H + 2)
            local shown = #subs > cap and cap or #subs
            for k = 1, shown do
                local s = subs[k]
                ri = ri + 1
                local r = MakeRow(ri)
                if s.disc then
                    r.icon:SetTexture(s.disc)
                    r.icon:SetTexCoord(0, 1, 0, 1)
                    local dc = s.discCol
                    if dc then
                        r.icon:SetVertexColor(dc[1], dc[2], dc[3])
                    else
                        r.icon:SetVertexColor(1, 1, 1)
                    end
                    r.sym:SetTexture(s.sym)
                    local sc = s.symCol
                    if sc then
                        r.sym:SetVertexColor(sc[1], sc[2], sc[3])
                    else
                        r.sym:SetVertexColor(1, 1, 1)
                    end
                    r.sym:Show()
                else
                    r.sym:Hide()
                    r.icon:SetVertexColor(1, 1, 1)
                    r.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
                    r.icon:SetTexture(s.icon or "Interface\\Icons\\INV_Misc_QuestionMark")
                end
                r.icon:SetSize(iconSz, iconSz)
                local actID = s.foodID or s.useItem
                local actMacro = (not actID) and s.useMacro or nil
                r.name:ClearAllPoints()
                r.name:SetPoint("TOPLEFT", r, "TOPLEFT", textLeft, -6)
                r.name:SetWidth(textW)
                r.sub:ClearAllPoints()
                r.sub:SetPoint("TOPLEFT", r, "TOPLEFT", textLeft, -26)
                r.sub:SetWidth(textW)
                r.name:SetText(s.name or "")
                r.sub:SetText(s.sub or SubText(s))
                local subH = r.sub:GetStringHeight() or 16
                local rowHi = rowH
                if 26 + subH + 4 > rowHi then rowHi = 26 + subH + 4 end
                local nameW = TextW(r.name, 14)
                if nameW > textW - 30 then nameW = textW - 30 end
                local tailX = textLeft + nameW
                if s.note then
                    if not r.note then
                        r.note = r:CreateFontString(nil, "OVERLAY")
                        r.note:SetFont(ns.FONT, 12, "")
                        r.note:SetTextColor(DIM[1], DIM[2], DIM[3])
                        r.note:SetWordWrap(false)
                        r.note:SetJustifyH("LEFT")
                    end
                    r.note:SetText(string.format(L["（%s）"], s.note))
                    r.note:ClearAllPoints()
                    r.note:SetPoint("LEFT", r.name, "LEFT", nameW + 3, 0)
                    r.note:Show()
                    tailX = tailX + 3 + TextW(r.note, 12)
                elseif r.note then
                    r.note:Hide()
                end
                r.btn:ClearAllPoints()
                r.btn:SetPoint("RIGHT", r, "RIGHT", -6, 0)
                r.btn:SetFrameLevel(r:GetFrameLevel() + 6)
                r.btn:Show()
                do
                    local DG = ns.DungeonDG or (ns.ProfHost and ns.ProfHost.DG)
                    if s.badge and DG and DG.MakeBadge and DG.BadgeTint then
                        if not r.badge then r.badge = DG.MakeBadge(r) end
                        DG.BadgeTint(r.badge, s.badge.col)
                        r.badge.lab:SetText(s.badge.t or "")
                        local bw = TextW(r.badge.lab, 20) + (DG.Q_BADGE_PAD or 5) * 2
                        if bw < (DG.Q_BADGE_MIN_W or 24) then bw = DG.Q_BADGE_MIN_W or 24 end
                        if ns.hui and ns.hui.PaintSolidChip then
                            ns.hui.PaintSolidChip(r.badge, s.badge.t or "", s.badge.col, bw)
                        else
                            r.badge:SetWidth(bw)
                        end
                        r.badge:ClearAllPoints()
                        if s.note then
                            r.badge:SetPoint("TOPLEFT", r.note, "TOPRIGHT", 6, -1)
                        else
                            r.badge:SetPoint("TOPLEFT", r.name, "TOPLEFT", nameW + 6, -1)
                        end
                        r.badge:Show()
                    elseif r.badge then
                        r.badge:Hide()
                    end
                end
                if (actID or actMacro) and ns.hui and ns.hui.MakeSolidChip and ns.hui.PaintSolidChip then
                    if not r.actChip then r.actChip = ns.hui.MakeSolidChip(r, r:GetFrameLevel() + 2, 20) end
                    ns.hui.PaintSolidChip(r.actChip, s.actLabel or L["使用"], ns.hui.ACCENT, nil, 12)
                    local cw = r.actChip:GetWidth() or 44
                    local chipX = tailX + 6
                    local chipMax = (PANEL_W - PAD * 2) - 40 - cw
                    if chipX > chipMax then chipX = chipMax end
                    if chipX < textLeft then chipX = textLeft end
                    r.actChip:ClearAllPoints()
                    r.actChip:SetPoint("LEFT", r, "TOPLEFT", chipX, -14)
                    r.actChip:Show()
                    if actID then
                        ActPlace(ActBtn(panel, "row" .. ri), r, s.actTip, "item", "item:" .. actID,
                            rowH, nil, s.foodID and function() O.FoodMenu() end or nil)
                    else
                        ActPlace(ActBtn(panel, "row" .. ri), r, s.actTip, "macro", actMacro, rowH, nil, nil)
                    end
                else
                    if r.actChip then r.actChip:Hide() end
                end
                r.ikey = s.ikey
                r.ikind = s.ikind or it.kind
                r.iid = s.base or s.id
                r.itipid = s.id
                r.qid = s.qid
                r.slug = s.slug
                r.idesc = s.desc
                r.ilabel = s.name
                r.jumpTip = s.jumpTip
                if s.jump then
                    r.jump = s.jump
                elseif s.areaID or s.qid or (s.mapID and s.x and s.y) then
                    r.jump = function() return MarkOnMap(s) end
                else
                    r.jump = nil
                end
                r:ClearAllPoints()
                r:SetPoint("TOPLEFT", panel, "TOPLEFT", PAD, y)
                r:SetPoint("TOPRIGHT", panel, "TOPRIGHT", -PAD, y)
                r:SetHeight(rowHi)
                r:Show()
                contentBottom = y - rowHi
                y = y - (rowHi + ROW_GAP)
            end
            if #subs > shown and moreText then
                moreText:SetText(string.format(L["还有 %d 个，打开手册查看"], #subs - shown))
                moreText:ClearAllPoints()
                moreText:SetPoint("TOPLEFT", panel, "TOPLEFT", PAD + 4, contentBottom - 4)
                moreText:Show()
                y = contentBottom - 20
                contentBottom = y + 2
            end
        else
            ci = ci + 1
            local card = MakeCard(ci)
            card.title:SetText(it.title or "")
            card.text:SetText(it.text or "")
            local textH = 14
            if it.btn then
                card.text:SetWordWrap(true)
                card.text:SetWidth(PANEL_W - PAD * 2 - 60)
                textH = card.text:GetStringHeight() or 14
                if textH < 14 then textH = 14 end
            else
                card.text:SetWordWrap(false)
                card.text:SetWidth(PANEL_W - PAD * 2 - 60)
            end
            if it.icon then
                card.icon:SetTexture(it.icon)
                card.icon:ClearAllPoints()
                card.icon:SetPoint("TOPLEFT", card, "TOPLEFT", 10, -(9 + (18 + textH) / 2 - 16))
                card.icon:Show()
            else
                card.icon:Hide()
            end
            if it.name and it.name ~= "" then
                card.name:SetText(it.name)
                local tw = (card.title:GetStringWidth() or 40) + 6
                local nx = 50 + tw
                local nw = PANEL_W - PAD * 2 - nx - 10
                if nw < 40 then nw = 40 end
                card.name:ClearAllPoints()
                card.name:SetPoint("TOPLEFT", card, "TOPLEFT", nx, -10)
                card.name:SetWidth(nw)
                card.name:Show()
            else
                card.name:SetText("")
                card.name:Hide()
            end
            if card.chip and ns.hui and ns.hui.PaintSolidChip then
                local chip = tostring(it.n or 0)
                if it.noChip then chip = "" end
                ns.hui.PaintSolidChip(card.chip, chip, ns.hui.ACCENT, 32)
            end
            local ch = CARD_H
            if it.btn then
                ch = 27 + textH + 6 + 22 + 8
                local has2 = it.btn2 and it.btn2 ~= ""
                local has3 = it.btn3 and it.btn3 ~= ""
                local bw
                if has2 or has3 then
                    bw = UniformW(card.act, it.btn, it.btn2, it.btn3)
                    FitBtn(card.act, it.btn, bw)
                else
                    FitBtn(card.act, it.btn)
                end
                card.onAct = it.onClick
                card.hint = it.hint
                card.act:Show()
                if has2 then
                    FitBtn(card.act2, it.btn2, bw)
                    card.onAct2 = it.onClick2
                    card.hint2 = it.hint2
                    card.act2:ClearAllPoints()
                    card.act2:SetPoint("BOTTOM", card, "BOTTOM", 0, 8)
                    card.act2:Show()
                else
                    card.onAct2 = nil
                    card.hint2 = nil
                    card.act2:Hide()
                end
                if has3 then
                    FitBtn(card.act3, it.btn3, bw)
                    card.hint3 = it.hint3
                    card.act3:ClearAllPoints()
                    card.act3:SetPoint("BOTTOMLEFT", card, "BOTTOMLEFT", 8, 8)
                    card.act3:Show()
                    local scc = (ns.CampWatch and ns.CampWatch.SitCmd and ns.CampWatch.SitCmd()) or "/sit"
                    local sb = ActBtn(panel, "card" .. ci .. "sit")
                    if sb then
                        sb.actKind, sb.actValue = "macro", scc
                        sb:SetAttribute("type", "macro")
                        sb:SetAttribute("macrotext", scc)
                        sb.tipText = it.hint3
                        sb:ClearAllPoints()
                        sb:SetPoint("BOTTOMLEFT", card.act3, "BOTTOMLEFT", 0, 0)
                        sb:SetPoint("TOPRIGHT", card.act3, "TOPRIGHT", 0, 0)
                        sb:SetHeight(22)
                        sb:SetFrameLevel(card:GetFrameLevel() + 6)
                        sb:Show()
                        sb.usedNow = true
                    end
                else
                    card.hint3 = nil
                    card.act3:Hide()
                end
                if it.stat and it.stat ~= "" then
                    local sc = it.statOn and ACC or DIM
                    card.stat:SetText(it.stat)
                    card.stat:SetTextColor(sc[1], sc[2], sc[3])
                    card.stat:ClearAllPoints()
                    card.stat:SetPoint("RIGHT", card.act, "LEFT", -8, 0)
                    card.stat:SetJustifyH("RIGHT")
                    card.stat:SetWidth(150)
                    card.stat:Show()
                else
                    card.stat:Hide()
                end
            else
                card.onAct = nil
                card.hint = nil
                card.onAct2 = nil
                card.hint2 = nil
                card.hint3 = nil
                card.act:Hide()
                card.act2:Hide()
                card.act3:Hide()
                card.stat:Hide()
            end
            local cardAct = it.onCard or it.useMacro or it.useItem
            card:SetScript("OnMouseUp", nil)
            if cardAct then
                card:EnableMouse(true)
                card.cardHint = it.cardHint
                card:SetScript("OnEnter", function()
                    if card.cardHint then Tip(card, card.cardHint, nil) end
                end)
                card:SetScript("OnLeave", function()
                    HideTip()
                end)
            else
                card:EnableMouse(false)
                card.cardHint = nil
                card:SetScript("OnEnter", nil)
                card:SetScript("OnLeave", nil)
            end
            if it.onCard then
                local cmd = (ns.CampWatch and ns.CampWatch.SitCmd and ns.CampWatch.SitCmd()) or "/sit"
                ActPlace(ActBtn(panel, "card" .. ci), card, it.cardHint, "macro", cmd,
                    ch - (it.btn and 30 or 0) - 1, 1)
            elseif cardAct then
                ActPlace(ActBtn(panel, "card" .. ci), card, it.cardHint,
                    it.useItem and "item" or "macro",
                    it.useItem and ("item:" .. it.useItem) or it.useMacro,
                    ch - (it.btn and 30 or 0) - 1, 1)
            end
            card:ClearAllPoints()
            card:SetPoint("TOPLEFT", panel, "TOPLEFT", PAD, y)
            card:SetPoint("TOPRIGHT", panel, "TOPRIGHT", -PAD, y)
            card:SetHeight(ch)
            card:Show()
            contentBottom = y - ch
            y = y - (ch + GAP)
        end
    end
    for i = ci + 1, #cards do cards[i]:Hide() end
    if panel.actBtns then
        for _, b in pairs(panel.actBtns) do
            if b.usedNow then
                b.usedNow = nil
            elseif not InCombatLockdown() then
                b:Hide()
            end
        end
    end
    for i = hi + 1, #heads do heads[i]:Hide() end
    if not InCombatLockdown() then
        for i = ri + 1, #subRows do subRows[i]:Hide() end
    end

    local btY = (contentBottom or (TOP_Y + 4)) - GAP
    row:ClearAllPoints()
    row:SetPoint("TOPLEFT", panel, "TOPLEFT", PAD, btY)
    row:SetPoint("TOPRIGHT", panel, "TOPRIGHT", -PAD, btY)
    row:SetHeight(24)
    row:Show()
    if not (InCombatLockdown and InCombatLockdown()) then
        panel:SetHeight(-btY + 24 + PAD)
    end
end

local function Open(keep)
    if not panel or panel:IsShown() then return end
    if InCombatLockdown and InCombatLockdown() then return end
    if opts then opts:Hide() end
    do
        local MWm = ns.MapWindowModule
        if MWm and MWm.MinioCardWanted and MWm.MinioCardWanted() then O.Refresh() end
    end
    Layout(current)
    panel:SetAlpha(0)
    local function apply(e)
        panel:ClearAllPoints()
        panel:SetPoint("LEFT", orb, "RIGHT", 8 - SLIDE * (1 - e), 0)
        panel:SetAlpha(e)
    end
    apply(0)
    panel:Show()
    openedAt = (GetTime and GetTime()) or 0
    StartTween(0.18, apply)
    StartHideTimer(keep)
end

local function CbTipBody()
    local parts = {}
    local items = current and current.items
    if type(items) == "table" then
        for _, it in ipairs(items) do
            if #parts >= 8 then break end
            local s = it.name
            if type(s) == "string" and s ~= "" then parts[#parts + 1] = "· " .. s end
        end
    end
    return table.concat(parts, "\n")
end

local function Toggle()
    if panel and panel:IsShown() then
        Close()
    elseif InCombatLockdown and InCombatLockdown() then
        O.CbPreviewToggle()
    else
        Open()
    end
end

local function Pulse()
    if not badge or not badge:IsShown() then return end
    pulseT = 0
    if pulseFrame then pulseFrame:Show() end
end

function O.Update(res)
    do
        local MWm = ns.MapWindowModule
        if MWm and MWm.MinioCardWanted and MWm.MinioCardWanted() and MWm.TodoCard then
            local g = MWm.TodoCard()
            if g and g.list then
                res = res or {}
                res.items = res.items or {}
                if not res.__dfMapCard then
                    table.insert(res.items, 1, g)
                    res.__dfMapCard = true
                end
            end
        end
    end
    current = res
    if not badge then return end
    local onc = Cfg()
    local n = (res and res.total) or 0
    local settingsOpen = opts and opts.IsShown and opts:IsShown() or false
    local wantOrb = onc.on ~= false
    if orb then
        local ghost = wantOrb and (onc.onlyTodo and not settingsOpen) and n == 0
        if wantOrb and not orb:IsShown() then orb:Show() end
        if not wantOrb and orb:IsShown() then orb:Hide() end
        if ghost then
            if orb:IsMouseOver() or (panel and panel:IsShown()) then
                if orb:GetAlpha() ~= 1 then orb:SetAlpha(1) end
            elseif orb.revealed then
                O.ArmGhost()
            else
                if orb:GetAlpha() ~= 0 then orb:SetAlpha(0) end
            end
        elseif orb:IsShown() then
            if orb:GetAlpha() ~= 1 then orb:SetAlpha(1) end
        end
    end
    PaintRing(n)
    if n > 0 then
        if badgeText then badgeText:SetText(n > 9 and "9+" or tostring(n)) end
        badge:Show()
        if lastN ~= n then Pulse() end
        lastN = n
    else
        badge:Hide()
        lastN = 0
    end
    local sawFood, sawRested = false, false
    for _, it in ipairs(res and res.items or {}) do
        if it.kind == "buff" and it.list then
            for _, r in ipairs(it.list) do
                if r.ikind == "food" then sawFood = true
                elseif r.ikind == "rested" then sawRested = true end
            end
        end
    end
    if onc.on ~= false then
        if sawFood and not lastFood and onc.voice == true and onc.foodVoice ~= false then
            O.SayVoice(FOOD_CUE)
        end
        if sawRested and not lastRested and onc.voice == true and onc.restedVoice ~= false then
            O.SayVoice(RESTED_CUE)
        end
    end
    lastFood, lastRested = sawFood, sawRested
    if panel and panel:IsShown() then Layout(res) end
end

function O.Reveal(res, reason)
    O.Update(res)
    local mode = Cfg().mode or "auto"
    if mode == "silent" or mode == "badge" then return end
    if reason == "tent" then
        if panel and panel:IsShown() then StartHideTimer(true) else Open(true) end
    elseif reason == "login" or reason == "zone" or reason == "manual" then
        Open()
    end
end

function O.IsShown()
    return panel ~= nil and panel:IsShown()
end

function O.Hide()
    Close()
    if orb then orb:Hide() end
end

local function InitVoiceBtn()
    voiceBtn = CreateFrame("Button", nil, panel)
    voiceBtn:SetSize(SIDE_S, SIDE_S)
    voiceBtn:SetPoint("CENTER", panel, "TOPRIGHT", -100, -22)
    voiceBtn:SetFrameLevel(panel:GetFrameLevel() + 4)
    voiceBtn.hover = false
    voiceBtn.tex = voiceBtn:CreateTexture(nil, "ARTWORK")
    voiceBtn.tex:SetSize(19, 19)
    voiceBtn.tex:SetPoint("CENTER", voiceBtn, "CENTER", 0, 0)
    voiceBtn.tex:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\Prof\\prof_mute.tga")
    voiceBtn:SetScript("OnClick", function()
        ns.PlaySound(1)
        local c = Cfg()
        c.voice = not (c.voice == true)
        PaintVoiceBtn()
        O.SayVoice((c.voice == true) and ON_CUE or OFF_CUE, true)
        if voiceBtn:IsMouseOver() then
            Tip(voiceBtn, L["语音"], (c.voice == true) and L["语音提示：开启（点击静音）"] or L["语音提示：已静音（点击恢复）"])
        end
    end)
    voiceBtn:SetScript("OnEnter", function()
        local c = Cfg()
        Tip(voiceBtn, L["语音"], (c.voice ~= true) and L["语音提示：已静音（点击恢复）"] or L["语音提示：开启（点击静音）"])
    end)
    voiceBtn:SetScript("OnLeave", function()
        HideTip()
    end)
    PaintVoiceBtn()
end

function O.Init()
    if orb then
        ApplyPos()
        return
    end

    orb = CreateFrame("Button", "DFZoneOrb", UIParent)
    orb:SetSize(ORB_SIZE, ORB_SIZE)
    orb:SetFrameStrata("MEDIUM")
    orb:SetFrameLevel(300)
    orb:SetClampedToScreen(true)
    orb:SetMovable(true)
    orb:RegisterForDrag("LeftButton")
    orb:EnableMouse(true)
    ApplyPos()

    disc = orb:CreateTexture(nil, "BACKGROUND")
    disc:SetPoint("CENTER", orb, "CENTER", 0, 0)
    disc:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\Common\\CheckDisc")
    disc:SetVertexColor(0x10 / 255, 0x13 / 255, 0x1A / 255, 1)

    ring = orb:CreateTexture(nil, "BORDER")
    ring:SetPoint("CENTER", orb, "CENTER", 0, 0)
    ring:SetAtlas("Talents-Main-Ring-c60")

    icon = orb:CreateTexture(nil, "ARTWORK")
    icon:SetSize(30, 30)
    icon:SetPoint("CENTER", orb, "CENTER", 0, 0)
    icon:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\Brand\\DungeonsForever")

    badge = CreateFrame("Frame", nil, orb)
    badge:SetSize(20, 20)
    badge:SetPoint("TOPRIGHT", orb, "TOPRIGHT", 4, 4)
    badge:SetFrameLevel(orb:GetFrameLevel() + 5)
    local disc2 = badge:CreateTexture(nil, "BACKGROUND")
    disc2:SetAllPoints(badge)
    disc2:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\Common\\CheckDisc")
    disc2:SetVertexColor(0x7F / 255, 0x1F / 255, 0x1F / 255, 1)
    badgeText = badge:CreateFontString(nil, "OVERLAY")
    badgeText:SetFont(ns.FONT, 11, "OUTLINE")
    badgeText:SetPoint("CENTER", badge, "CENTER", 0, 0)
    badgeText:SetTextColor(1, 1, 1)
    badge:Hide()

    pulseFrame = CreateFrame("Frame")
    pulseFrame:Hide()
    pulseFrame:SetScript("OnUpdate", function(_, dt)
        pulseT = pulseT + dt
        local k = pulseT / 0.32
        if k >= 1 then
            pulseFrame:Hide()
            if badge then badge:SetScale(1) end
            return
        end
        if badge then badge:SetScale(1 + 0.32 * math.sin(k * math.pi)) end
    end)

    tweener = CreateFrame("Frame")
    tweener:Hide()
    tweener:SetScript("OnUpdate", function(_, dt)
        if not job then
            tweener:Hide()
            return
        end
        job.t = job.t + dt
        local k = job.t / job.dur
        if k > 1 then k = 1 end
        local e = 1 - (1 - k) * (1 - k) * (1 - k)
        job.apply(e)
        if k >= 1 then
            local done = job.done
            job = nil
            tweener:Hide()
            if done then done() end
        end
    end)

    panel = CreateFrame("Frame", "DFZoneOrbPanel", UIParent, "BackdropTemplate")
    panel:SetSize(PANEL_W, 120)
    panel:SetPoint("LEFT", orb, "RIGHT", 8, 0)
    panel:SetFrameStrata("MEDIUM")
    panel:SetFrameLevel(400)
    panel:SetClampedToScreen(true)
    panel:EnableMouse(true)
    panel:Hide()
    if ns.hui and ns.hui.SkinPopup and ns.hui.layer then
        ns.hui.SkinPopup(panel, 10, "both", ns.hui.layer.L0)
    end

    panel.title = panel:CreateFontString(nil, "OVERLAY")
    panel.title:SetFont(ns.FONT, 16, "")
    panel.title:SetPoint("TOPLEFT", panel, "TOPLEFT", PAD, -12)
    panel.title:SetTextColor(TEXT[1], TEXT[2], TEXT[3])

    panel.count = panel:CreateFontString(nil, "OVERLAY")
    panel.count:SetFont(ns.FONT, 14, "")
    panel.count:SetPoint("LEFT", panel.title, "RIGHT", 8, 0)
    panel.count:SetTextColor(FAINT[1], FAINT[2], FAINT[3])

    moreText = panel:CreateFontString(nil, "OVERLAY")
    moreText:SetFont(ns.FONT, 14, "")
    moreText:SetTextColor(FAINT[1], FAINT[2], FAINT[3])
    moreText:Hide()

    closeBtn = CreateFrame("Button", nil, panel, "BackdropTemplate")
    closeBtn:SetSize(CLOSE_S, CLOSE_S)
    closeBtn:SetPoint("CENTER", panel, "TOPRIGHT", -22, -22)
    closeBtn:SetFrameLevel(panel:GetFrameLevel() + 4)
    if ns.hui and ns.hui.SkinButton then ns.hui.SkinButton(closeBtn, { noFrame = true }) end
    local ct = closeBtn:CreateTexture(nil, "ARTWORK")
    ct:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\textures\\YY_close")
    ct:SetSize(32, 32)
    ct:SetPoint("CENTER", closeBtn, "CENTER", 0, 0.4)
    ct:SetVertexColor(GLYPH, GLYPH, GLYPH)
    closeBtn:SetScript("OnClick", function()
        if InCombatLockdown and InCombatLockdown() then
            print("|cff46bf72[无限副本手册]|r " .. L["战斗中无法关闭，脱战后自动收起"])
        end
        Close()
    end)
    closeBtn:SetScript("OnEnter", function()
        ct:SetVertexColor(1, 1, 1)
        Tip(closeBtn, L["关闭"], L["收起抽屉，角标继续显示待办数"], nil)
    end)
    closeBtn:SetScript("OnLeave", function()
        ct:SetVertexColor(GLYPH, GLYPH, GLYPH)
        HideTip()
    end)

    row = CreateFrame("Frame", nil, panel)
    row:SetFrameLevel(panel:GetFrameLevel() + 2)

    local function MakeBtn(text)
        local b = ns.CreateButton(row)
        b:SetSize(82, 24)
        b:SetText(text)
        return b
    end

    btnOpen = MakeBtn(L["打开手册"])
    btnOpen:SetPoint("LEFT", row, "LEFT", 0, 0)
    btnSkip = MakeBtn(L["本次忽略"])
    btnSkip:SetPoint("CENTER", row, "CENTER", 0, 0)
    btnBlock = MakeBtn(L["永久忽略"])
    btnBlock:SetPoint("RIGHT", row, "RIGHT", 0, 0)

    btnOpen:HookScript("OnEnter", function()
        Tip(btnOpen, L["打开手册"], L["查看完整的地图待办、副本与探索清单"], nil)
    end)
    btnOpen:HookScript("OnLeave", HideTip)
    btnSkip:HookScript("OnEnter", function()
        Tip(btnSkip, L["本次忽略"], L["本次登录内不再提醒这张地图"], L["重新登录或重载后恢复"])
    end)
    btnSkip:HookScript("OnLeave", HideTip)
    btnBlock:HookScript("OnEnter", function()
        Tip(btnBlock, L["永久忽略"], L["加入黑名单，以后进入这张地图都不再提醒"], L["可在管理忽略里恢复"])
    end)
    btnBlock:HookScript("OnLeave", HideTip)

    manage = CreateFrame("Button", nil, panel)
    manage:SetSize(MANAGE_S, MANAGE_S)
    manage:SetPoint("CENTER", panel, "TOPRIGHT", -48, -22)
    manage:SetFrameLevel(panel:GetFrameLevel() + 4)
    manage.tex = {}
    local function paintManage(v)
        for i = 1, #manage.tex do manage.tex[i]:SetColorTexture(v, v, v, 1) end
    end
    do
        local g = GLYPH
        for i = 1, 3 do
            local yy = 6.3 - (i - 1) * 6.3
            local dot = manage:CreateTexture(nil, "ARTWORK")
            dot:SetColorTexture(g, g, g, 1)
            dot:SetSize(2.7, 2.7)
            dot:SetPoint("CENTER", manage, "CENTER", -6.3, yy)
            manage.tex[#manage.tex + 1] = dot
            local bar = manage:CreateTexture(nil, "ARTWORK")
            bar:SetColorTexture(g, g, g, 1)
            bar:SetSize(10, 1.8)
            bar:SetPoint("CENTER", manage, "CENTER", 0.9, yy)
            manage.tex[#manage.tex + 1] = bar
        end
    end
    manage:SetScript("OnEnter", function()
        paintManage(1)
        Tip(manage, L["管理忽略"], L["查看与恢复已忽略的地图和小项"])
    end)
    manage:SetScript("OnLeave", function()
        paintManage(GLYPH)
        HideTip()
    end)
    manage:SetScript("OnClick", function()
        ns.PlaySound(1)
        Close()
        if ns.ZoneHintList and ns.ZoneHintList.Open then ns.ZoneHintList.Open() end
    end)

    gear = CreateFrame("Button", "DFZoneOrbGear", panel)
    gear:SetSize(SIDE_S, SIDE_S)
    gear:SetPoint("CENTER", panel, "TOPRIGHT", -74, -22)
    gear:SetFrameLevel(panel:GetFrameLevel() + 4)
    local gt = gear:CreateTexture(nil, "ARTWORK")
    gt:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\textures\\DF_Settings")
    gt:SetSize(19, 19)
    gt:SetPoint("CENTER")
    gt:SetVertexColor(GLYPH, GLYPH, GLYPH, 1)

    InitVoiceBtn()
    opts = CreateFrame("Frame", nil, panel, "BackdropTemplate")
    opts:SetSize(184, 466)
    opts:SetPoint("TOPRIGHT", panel, "TOPRIGHT", -8, -40)
    opts:SetFrameLevel(panel:GetFrameLevel() + 8)
    if ns.hui and ns.hui.SkinPopup and ns.hui.layer then
        ns.hui.SkinPopup(opts, 8, "both", ns.hui.layer.L2)
        if ns.hui.SkinShadow then ns.hui.SkinShadow(opts, nil, nil, 8) end
    end
    opts:EnableMouse(true)
    opts:SetScript("OnEnter", function()
        hovered = true
        hideToken = hideToken + 1
    end)
    opts:SetScript("OnLeave", function()
        hovered = false
        StartHideTimer()
    end)
    opts:Hide()

    local oph = opts:CreateFontString(nil, "OVERLAY")
    oph:SetFont(ns.FONT, 14, "")
    oph:SetPoint("TOPLEFT", opts, "TOPLEFT", 10, -8)
    oph:SetText(L["提醒内容"])
    oph:SetTextColor(FAINT[1], FAINT[2], FAINT[3])

    optCbs = {}

    local function OptRow(y, label, key, tip, vkey)
        local t = opts:CreateFontString(nil, "OVERLAY")
        t:SetFont(ns.FONT, 14, "")
        t:SetPoint("TOPLEFT", opts, "TOPLEFT", 10, y - 4)
        t:SetText(label)
        t:SetTextColor(TEXT[1], TEXT[2], TEXT[3])
        if vkey then
            local vb = CreateFrame("Button", nil, opts)
            vb:SetSize(28, 22)
            vb:SetPoint("TOPRIGHT", opts, "TOPRIGHT", -56, y + 1)
            vb.tex = vb:CreateTexture(nil, "ARTWORK")
            vb.tex:SetSize(21, 21)
            vb.tex:SetPoint("CENTER", vb, "CENTER", 0, 0)
            vb.tex:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\Prof\\prof_mute.tga")
            local cue = (vkey == "foodVoice") and FOOD_CUE or RESTED_CUE
            local function paint()
                local c = ns.ZoneHint and ns.ZoneHint.CFG and ns.ZoneHint.CFG() or {}
                if c[vkey] == false then
                    vb.tex:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\Prof\\prof_mute.tga")
                    vb.tex:SetVertexColor(0xC6 / 255, 0xCB / 255, 0xD4 / 255, 1)
                else
                    vb.tex:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\Prof\\prof_voice_on.tga")
                    vb.tex:SetVertexColor(ACC[1], ACC[2], ACC[3], 1)
                end
            end
            vb.PaintVoice = paint
            vb:SetScript("OnClick", function()
                ns.PlaySound(1)
                local c = ns.ZoneHint and ns.ZoneHint.CFG and ns.ZoneHint.CFG()
                if c then c[vkey] = (c[vkey] == false) and true or false end
                paint()
                O.SayVoice(((c and c[vkey] ~= false) and cue) or OFF_CUE, true)
                if vb:IsMouseOver() then
                    Tip(vb, L["语音"], (c and c[vkey] == false) and L["语音提示：已静音（点击恢复）"] or L["语音提示：开启（点击静音）"])
                end
            end)
            vb:SetScript("OnEnter", function()
                local c = ns.ZoneHint and ns.ZoneHint.CFG and ns.ZoneHint.CFG() or {}
                Tip(vb, L["语音"], (c[vkey] == false) and L["语音提示：已静音（点击恢复）"] or L["语音提示：开启（点击静音）"])
            end)
            vb:SetScript("OnLeave", function()
                HideTip()
            end)
            paint()
            optCbs[vkey] = vb
        end
        local cb = CreateFrame("CheckButton", nil, opts)
        cb:SetSize(36, 20)
        cb:SetPoint("TOPRIGHT", opts, "TOPRIGHT", -8, y + 1)
        if ns.hui and ns.hui.ReskinToggle then ns.hui.ReskinToggle(cb) end
        cb:SetScript("OnClick", function(self)
            ns.PlaySound(1)
            local c = ns.ZoneHint and ns.ZoneHint.CFG and ns.ZoneHint.CFG()
            if not c then return end
            local nv = not (c[key] ~= false)
            c[key] = nv
            if self.SetChecked then self:SetChecked(nv) end
            if C_Timer and C_Timer.After then
                C_Timer.After(0, function()
                    local c2 = ns.ZoneHint and ns.ZoneHint.CFG and ns.ZoneHint.CFG()
                    if c2 and self.SetChecked then self:SetChecked(c2[key] ~= false) end
                end)
            end
            O.Refresh()
            if ns.MainFrame and ns.MainFrame.SyncZoneHintCard then ns.MainFrame.SyncZoneHintCard() end
        end)
        cb:SetScript("OnEnter", function()
            Tip(cb, label, tip)
        end)
        cb:SetScript("OnLeave", HideTip)
        optCbs[key] = cb
        return cb
    end

    OptRow(-32, L["探索-书籍提醒"], "book", L["本图还有未收集的书时提示"])
    OptRow(-54, L["探索-书籍上交提醒"], "turnin", L["在幽暗城且背包有可上交的书时提示"])
    OptRow(-76, L["探索-睡袋提醒"], "bag", L["本图有睡袋任务链的一步时提示"])
    OptRow(-98, L["探索-火炬提醒"], "torch", L["本图有守夜人火炬可拾取时提示"])
    OptRow(-120, L["探索-旗帜提醒"], "banner", L["进入血色修道院副本后，有未拾取的血色旗帜时提示"])
    OptRow(-142, L["副本-任务提醒"], "quest", L["本图有可接的副本任务时提示"])
    OptRow(-164, L["职业-技能提醒"], "spell", L["主城有训练师且技能可学时提示"])
    OptRow(-186, L["职业-天赋提醒"], "talent", L["有未分配的天赋点时提示，点击可直接打开天赋界面"])
    OptRow(-208, L["增益-食物提醒"], "food", L["没吃食物、缺少经验加成时提示"], "foodVoice")
    OptRow(-230, L["增益-睡袋提醒"], "rested", L["背包有睡袋且未休息或 buff 快到期时提示"], "restedVoice")
    OptRow(-252, L["增益-露营提醒"], "camp", L["在营火旁且没有强化休息时提示"])
    OptRow(-274, L["增益-到期提醒"], "renew", L["强化休息快到期时提示回营地续一次"])
    OptRow(-296, L["增益-蹭帐篷卡片"], "tent", L["找到营地玩家且自己还没有强化休息时，在待办里弹出卡片"])
    OptRow(-318, L["有帐篷时不提示"], "tentOwn", L["自己已有帐篷时，不再在待办里弹出蹭帐篷卡片"])

    local ttLabel = opts:CreateFontString(nil, "OVERLAY")
    ttLabel:SetFont(ns.FONT, 14, "")
    ttLabel:SetPoint("TOPLEFT", opts, "TOPLEFT", 10, -344)
    ttLabel:SetText(L["蹭帐篷密语"])
    ttLabel:SetTextColor(TEXT[1], TEXT[2], TEXT[3])

    local ttBtn = CreateFrame("Button", nil, opts, "BackdropTemplate")
    ttBtn:SetSize(56, 20)
    ttBtn:SetPoint("TOPRIGHT", opts, "TOPRIGHT", -8, -341)
    if ns.hui and ns.hui.BuildRoundedBG and ns.hui.layer then
        ns.hui.BuildRoundedBG(ttBtn, 6, ns.hui.layer.L2, "both", true, 1)
    end
    local ttText = ttBtn:CreateFontString(nil, "OVERLAY")
    ttText:SetFont(ns.FONT, 13, "")
    ttText:SetPoint("CENTER", ttBtn, "CENTER", 0, 0)
    ttText:SetTextColor(ACC[1], ACC[2], ACC[3])

    local function CampTexts()
        local CW = ns.CampWatch
        if CW and CW.Texts then
            local ok, v = pcall(CW.Texts)
            if ok and type(v) == "table" then return v end
        end
        return {}
    end

    local function SyncTentText()
        local c = ns.ZoneHint and ns.ZoneHint.CFG and ns.ZoneHint.CFG() or {}
        local i = tonumber(c.tentText) or 1
        ttText:SetText(string.format(L["第 %d 句"], i))
    end

    ttBtn:SetScript("OnClick", function()
        ns.PlaySound(1)
        local texts = CampTexts()
        if #texts == 0 then return end
        local c0 = ns.ZoneHint and ns.ZoneHint.CFG and ns.ZoneHint.CFG() or {}
        local cur = tonumber(c0.tentText) or 1
        local items = {}
        for i = 1, #texts do
            items[i] = {
                text = texts[i],
                checked = (i == cur),
                func = function()
                    local c2 = ns.ZoneHint and ns.ZoneHint.CFG and ns.ZoneHint.CFG()
                    if c2 then c2.tentText = i end
                    SyncTentText()
                    O.Refresh()
                    if ns.MainFrame and ns.MainFrame.SyncZoneHintCard then ns.MainFrame.SyncZoneHintCard() end
                end,
            }
        end
        if ns.hui and ns.hui.ShowMenu then ns.hui.ShowMenu(items, { anchor = ttBtn, up = true }) end
    end)
    ttBtn:SetScript("OnEnter", function()
        local texts = CampTexts()
        local c0 = ns.ZoneHint and ns.ZoneHint.CFG and ns.ZoneHint.CFG() or {}
        local i = tonumber(c0.tentText) or 1
        Tip(ttBtn, L["蹭帐篷密语"], (texts[i] or "") .. "\n" .. L["点击选择另外两句"])
    end)
    ttBtn:SetScript("OnLeave", HideTip)
    SyncTentText()

    local oph2 = opts:CreateFontString(nil, "OVERLAY")
    oph2:SetFont(ns.FONT, 14, "")
    oph2:SetPoint("TOPLEFT", opts, "TOPLEFT", 10, -368)
    oph2:SetText(L["窗口设置"])
    oph2:SetTextColor(FAINT[1], FAINT[2], FAINT[3])

    OptRow(-388, L["仅有待办时显示"], "onlyTodo", L["没有待办时隐藏圆形按钮"])
    OptRow(-410, L["进新场景不弹窗"], "noZonePopup", L["进入新的场景时不再自动弹出待办窗口，可点击圆球查看"])

    local SIZES = { 24, 28, 32, 36, 40 }

    local szLabel = opts:CreateFontString(nil, "OVERLAY")
    szLabel:SetFont(ns.FONT, 14, "")
    szLabel:SetPoint("TOPLEFT", opts, "TOPLEFT", 10, -438)
    szLabel:SetText(L["待办图标大小"])
    szLabel:SetTextColor(TEXT[1], TEXT[2], TEXT[3])

    local szBtn = CreateFrame("Button", nil, opts, "BackdropTemplate")
    szBtn:SetSize(36, 20)
    szBtn:SetPoint("TOPRIGHT", opts, "TOPRIGHT", -8, -433)
    if ns.hui and ns.hui.BuildRoundedBG and ns.hui.layer then
        ns.hui.BuildRoundedBG(szBtn, 6, ns.hui.layer.L2, "both", true, 1)
    end
    local szt = szBtn:CreateFontString(nil, "OVERLAY")
    szt:SetFont(ns.FONT, 14, "")
    szt:SetPoint("CENTER", szBtn, "CENTER", 0, 0)
    szt:SetTextColor(ACC[1], ACC[2], ACC[3])

    local function SyncSize()
        szt:SetText(tostring(tonumber(Cfg().icon) or 32))
    end

    szBtn:SetScript("OnClick", function()
        ns.PlaySound(1)
        local c = ns.ZoneHint and ns.ZoneHint.CFG and ns.ZoneHint.CFG()
        if not c then return end
        local cur = tonumber(c.icon) or 32
        local idx = 1
        for i = 1, #SIZES do
            if SIZES[i] == cur then idx = i end
        end
        c.icon = SIZES[idx % #SIZES + 1]
        SyncSize()
        ApplyOrbSize()
        if current then
            O.Update(current)
        else
            O.Refresh()
        end
    end)
    szBtn:SetScript("OnEnter", function()
        Tip(szBtn, L["待办图标大小"], L["点击切换待办圆球与条目的图标尺寸"])
    end)
    szBtn:SetScript("OnLeave", HideTip)

    gear:SetScript("OnClick", function()
        ns.PlaySound(1)
        if InCombatLockdown and InCombatLockdown() then return end
        if opts:IsShown() then
            opts:Hide()
            if current then O.Update(current) end
        else
            local c = ns.ZoneHint and ns.ZoneHint.CFG and ns.ZoneHint.CFG() or {}
            for k, cb in pairs(optCbs) do
                if cb.SetChecked then cb:SetChecked(c[k] and true or false)
                elseif cb.PaintVoice then cb:PaintVoice() end
            end
            SyncSize()
            SyncTentText()
            local rx = (panel.GetRight and panel:GetRight() or 0) - 8
            local ty = (panel.GetTop and panel:GetTop() or 0) - 40
            opts:ClearAllPoints()
            opts:SetPoint("TOPRIGHT", UIParent, "BOTTOMLEFT", rx, ty)
            opts:Show()
        end
    end)
    gear:SetScript("OnEnter", function()
        gt:SetVertexColor(1, 1, 1)
        Tip(gear, L["提醒设置"], L["选择要提醒的内容"])
    end)
    gear:SetScript("OnLeave", function()
        gt:SetVertexColor(GLYPH, GLYPH, GLYPH)
        HideTip()
    end)

    btnOpen:SetScript("OnClick", function()
        ns.PlaySound(1)
        Close()
        if ns.Open then ns.Open() end
    end)

    btnSkip:SetScript("OnClick", function()
        ns.PlaySound(1)
        if ns.ZoneHint and ns.ZoneHint.IsSim and ns.ZoneHint.IsSim() then Close() return end
        local key = current and current.key
        if key and ns.ZoneHint then ns.ZoneHint.SkipSession(key) end
        if badge then badge:Hide() end
        lastN = 0
        Close()
    end)

    btnBlock:SetScript("OnClick", function()
        ns.PlaySound(1)
        if ns.ZoneHint and ns.ZoneHint.IsSim and ns.ZoneHint.IsSim() then Close() return end
        local key = current and current.key
        if key and ns.ZoneHint then
            local name = current and current.ctx and current.ctx.zone or key
            ns.ZoneHint.Block(key, name, "all")
        end
        if badge then badge:Hide() end
        lastN = 0
        Close()
        if ns.MainFrame and ns.MainFrame.SyncZoneHintCard then ns.MainFrame.SyncZoneHintCard() end
    end)

    orbMenu = CreateFrame("Frame", nil, UIParent, "BackdropTemplate")
    orbMenu:SetHeight(64)
    orbMenu:SetFrameStrata("FULLSCREEN_DIALOG")
    if ns.hui and ns.hui.SkinPopup and ns.hui.layer then
        ns.hui.SkinPopup(orbMenu, 8, "both", ns.hui.layer.L2)
        if ns.hui.SkinShadow then ns.hui.SkinShadow(orbMenu, nil, nil, 8) end
    end
    local oml1 = orbMenu:CreateFontString(nil, "OVERLAY")
    oml1:SetFont(ns.FONT, 13, "")
    oml1:SetPoint("TOPLEFT", orbMenu, "TOPLEFT", 12, -11)
    oml1:SetTextColor(TEXT[1], TEXT[2], TEXT[3])
    local omb1 = CreateFrame("Button", nil, orbMenu)
    omb1:SetSize(10, 28)
    omb1:SetPoint("TOPLEFT", orbMenu, "TOPLEFT", 0, 0)
    omb1:SetPoint("TOPRIGHT", orbMenu, "TOPRIGHT", 0, 0)
    omb1:SetScript("OnEnter", function()
        oml1:SetTextColor(ACC[1], ACC[2], ACC[3])
        Tip(omb1, L["仅有待办时显示"], L["没有待办时隐藏圆形按钮"])
    end)
    omb1:SetScript("OnLeave", function()
        oml1:SetTextColor(TEXT[1], TEXT[2], TEXT[3])
        HideTip()
    end)
    local oml2 = orbMenu:CreateFontString(nil, "OVERLAY")
    oml2:SetFont(ns.FONT, 13, "")
    oml2:SetPoint("TOPLEFT", orbMenu, "TOPLEFT", 12, -39)
    oml2:SetText(L["永久关闭"])
    oml2:SetTextColor(TEXT[1], TEXT[2], TEXT[3])
    local omb2 = CreateFrame("Button", nil, orbMenu)
    omb2:SetSize(10, 28)
    omb2:SetPoint("TOPLEFT", orbMenu, "TOPLEFT", 0, -30)
    omb2:SetPoint("TOPRIGHT", orbMenu, "TOPRIGHT", 0, -30)
    omb2:SetScript("OnEnter", function()
        oml2:SetTextColor(ACC[1], ACC[2], ACC[3])
        Tip(omb2, L["永久关闭"], L["等同于设置里的地图待办开关，可随时重新开启"])
    end)
    omb2:SetScript("OnLeave", function()
        oml2:SetTextColor(TEXT[1], TEXT[2], TEXT[3])
        HideTip()
    end)
    local function SyncMenuLabels()
        local c = ns.ZoneHint and ns.ZoneHint.CFG and ns.ZoneHint.CFG() or {}
        oml1:SetText(L["仅有待办时显示"] .. "：" .. ((c.onlyTodo and L["开"]) or L["关"]))
    end
    omb1:SetScript("OnClick", function()
        ns.PlaySound(1)
        local c = ns.ZoneHint and ns.ZoneHint.CFG and ns.ZoneHint.CFG()
        if c then c.onlyTodo = not c.onlyTodo and true or false end
        SyncMenuLabels()
        if optCbs and optCbs.onlyTodo then optCbs.onlyTodo:SetChecked(c.onlyTodo and true or false) end
        if current then
            O.Update(current)
        else
            O.Refresh()
        end
    end)
    omb2:SetScript("OnClick", function()
        ns.PlaySound(1)
        local c = ns.ZoneHint and ns.ZoneHint.CFG and ns.ZoneHint.CFG()
        if c then c.on = false end
        orbMenu:Hide()
        Close()
        if orb then orb:Hide() end
        if ns.MainFrame and ns.MainFrame.SyncZoneHintCard then ns.MainFrame.SyncZoneHintCard() end
    end)
    orbMenu:Hide()

    local function ToggleOrbMenu()
        if orbMenu:IsShown() then
            orbMenu:Hide()
            return
        end
        SyncMenuLabels()
        local w = math.max(TextW(oml1, 60), TextW(oml2, 60)) + 24
        if w < 120 then w = 120 end
        orbMenu:SetWidth(w)
        orbMenu:ClearAllPoints()
        orbMenu:SetPoint("TOPLEFT", orb, "BOTTOMRIGHT", 4, -4)
        orbMenu:Show()
        menuOpenedAt = (GetTime and GetTime()) or 0
    end

    ApplyOrbSize()
    orb:RegisterForClicks("LeftButtonUp", "RightButtonUp")
    orb:SetScript("OnClick", function(_, btn)
        ns.PlaySound(1)
        if btn == "RightButton" then
            ToggleOrbMenu()
        else
            if orbMenu then orbMenu:Hide() end
            Toggle()
        end
    end)

    orb:SetScript("OnEnter", function()
        hovered = true
        hideToken = hideToken + 1
        orb.revealed = true
        orb.ghostPending = false
        orb.ghostTok = (orb.ghostTok or 0) + 1
        if orb:GetAlpha() ~= 1 then orb:SetAlpha(1) end
        PaintRing((current and current.total) or 0)
        if icon then icon:SetVertexColor(1, 1, 1, 1) end
        local zone = (current and current.ctx and current.ctx.zone) or ""
        local n = (current and current.total) or 0
        local desc
        if n > 0 then
            desc = string.format(L["本图待办 %d"], n)
        else
            desc = L["本图暂无待办"]
        end
        Tip(orb, zone ~= "" and zone or L["当前地图"], desc, L["左键展开 · 右键永久关闭 · 拖拽移动"])
    end)

    orb:SetScript("OnLeave", function()
        hovered = false
        PaintRing((current and current.total) or 0)
        local gc = Cfg()
        if gc.on ~= false and gc.onlyTodo and (current and (current.total or 0) == 0) and not (opts and opts:IsShown()) and not (panel and panel:IsShown()) then
            O.ArmGhost()
        end
        if icon then icon:SetVertexColor(0.92, 0.93, 0.95, 1) end
        if not O.CbTipHold() then HideTip() end
        if panel and panel:IsShown() then StartHideTimer() end
    end)
    orb:SetScript("OnDragStart", function()
        if type(InCombatLockdown) == "function" and InCombatLockdown() then return end
        orb:StartMoving()
    end)

    orb:SetScript("OnDragStop", function()
        orb:StopMovingOrSizing()
        SavePos()
        if panel and panel:IsShown() then
            panel:ClearAllPoints()
            panel:SetPoint("LEFT", orb, "RIGHT", 8, 0)
        end
    end)

    panel:SetScript("OnEnter", function()
        hovered = true
        hideToken = hideToken + 1
    end)

    panel:SetScript("OnLeave", function()
        hovered = false
        StartHideTimer()
    end)

    local watcher = CreateFrame("Frame")
    watcher:RegisterEvent("GLOBAL_MOUSE_DOWN")
    watcher:SetScript("OnEvent", function()
        local now = (GetTime and GetTime()) or 0
        if orbMenu and orbMenu:IsShown() then
            if now - menuOpenedAt >= 0.2 and not orbMenu:IsMouseOver() and not orb:IsMouseOver() then
                orbMenu:Hide()
            end
            return
        end
        if not panel or not panel:IsShown() then return end
        if now - openedAt < 0.2 then return end
        if _G.DFFoodMenuUp then return end
        if panel:IsMouseOver() then return end
        if opts and opts:IsShown() and opts:IsMouseOver() then return end
        if orb:IsMouseOver() then return end
        Close()
    end)

    if UISpecialFrames then
        local found = false
        for i = 1, #UISpecialFrames do
            if UISpecialFrames[i] == "DFZoneOrbPanel" then found = true break end
        end
        if not found then table.insert(UISpecialFrames, "DFZoneOrbPanel") end
    end
    panel:HookScript("OnHide", function()
        if FoodMenuClose then FoodMenuClose() end
        O.ArmGhost()
    end)

    if panel.title then panel.title:SetText("") end
    cards, heads, subRows = {}, {}, {}
end

function O.Refresh()
    if not (ns.ZoneHint and ns.ZoneHint.Collect) then return nil end
    local ctx = ns.ZoneHint.Context()
    local res = ns.ZoneHint.Collect(ctx)
    res.key = ns.ZoneHint.Key(ctx)
    O.Update(res)
    if (res.total or 0) == 0 then
        lastN = 0
        if badge then badge:Hide() end
        if not (opts and opts:IsShown()) then Close() end
    end
    return res
end

function O.ForceOpen(res)
    O.Update(res)
    Open()
end

function O.SetHeader(res)
    if not panel then return end
    local ctx = res and res.ctx
    local zone = ctx and ctx.zone or ""
    if zone == "" then zone = L["当前地图"] end
    if #zone > 12 then zone = zone:sub(1, 12) .. "..." end
    panel.title:SetText(zone)
    local n = (res and res.total) or 0
    if n > 0 then
        panel.count:SetText(string.format(L["本图待办 %d"], n))
    else
        panel.count:SetText(L["本图暂无待办"])
    end
end

local baseLayout = Layout
Layout = function(res)
    if InCombatLockdown and InCombatLockdown() then return end
    baseLayout(res)
    O.SetHeader(res)
end

local cbPanel = nil

function O.CbTipHold()
    return cbPanel ~= nil and cbPanel:IsShown()
end

function O.CbPreviewToggle()
    if not orb then return end
    if not cbPanel then
        local f = CreateFrame("Frame", nil, orb, "BackdropTemplate")
        f:SetWidth(248)
        f:SetBackdrop({
            bgFile = "Interface\\Tooltips\\TooltipBackground",
            edgeFile = "Interface\\Tooltips\\TooltipBorder",
            edgeSize = 12,
            insets = { left = 4, right = 4, top = 4, bottom = 4 },
        })
        f:SetBackdropColor(0.06, 0.07, 0.09, 0.96)
        f:SetBackdropBorderColor(0.25, 0.27, 0.31, 1)
        f:SetPoint("LEFT", orb, "RIGHT", 8, 0)
        f:SetFrameLevel(orb:GetFrameLevel() + 10)
        f.title = f:CreateFontString(nil, "OVERLAY")
        f.title:SetFont(ns.FONT, 14, "")
        f.title:SetPoint("TOPLEFT", f, "TOPLEFT", 12, -10)
        f.title:SetTextColor(1, 1, 1)
        f.title:SetJustifyH("LEFT")
        f.count = f:CreateFontString(nil, "OVERLAY")
        f.count:SetFont(ns.FONT, 12, "")
        f.count:SetPoint("TOPRIGHT", f, "TOPRIGHT", -12, -11)
        f.count:SetTextColor(ACC[1], ACC[2], ACC[3])
        f.count:SetJustifyH("RIGHT")
        f.body = f:CreateFontString(nil, "OVERLAY")
        f.body:SetFont(ns.FONT, 12, "")
        f.body:SetPoint("TOPLEFT", f, "TOPLEFT", 12, -32)
        f.body:SetTextColor(0.85, 0.88, 0.92)
        f.body:SetWidth(224)
        f.body:SetJustifyH("LEFT")
        f.body:SetJustifyV("TOP")
        cbPanel = f
    end
    if cbPanel:IsShown() then
        cbPanel:Hide()
        return
    end
    local ctx = current and current.ctx
    local zone = (ctx and ctx.zone) or ""
    if zone == "" then zone = L["当前地图"] end
    local n = (current and current.total) or 0
    cbPanel.title:SetText(zone)
    cbPanel.count:SetText(string.format(L["本图待办 %d"], n))
    local body = CbTipBody()
    if body == "" then body = L["本图暂无待办"] end
    cbPanel.body:SetText(body)
    local lines = select(2, body:gsub("\n", "")) + 1
    cbPanel:SetHeight(46 + lines * 17)
    cbPanel:Show()
end

local regenWatch = CreateFrame("Frame")
regenWatch:RegisterEvent("PLAYER_REGEN_ENABLED")
regenWatch:RegisterEvent("PLAYER_REGEN_DISABLED")
regenWatch:SetScript("OnEvent", function(_, event)
    if event == "PLAYER_REGEN_DISABLED" then
        if cbPanel and cbPanel:IsShown() then cbPanel:Hide() end
        if orbMenu and orbMenu:IsShown() then orbMenu:Hide() end
        if FoodMenuClose then FoodMenuClose() end
        if panel and panel:IsShown() then
            if InCombatLockdown and InCombatLockdown() then
                closePending = true
            else
                hideToken = hideToken + 1
                panel:SetAlpha(1)
                panel:Hide()
            end
        end
        return
    end
    if cbPanel and cbPanel:IsShown() then cbPanel:Hide() end
    if closePending then
        FlushClose()
    elseif panel and panel:IsShown() and current then
        Layout(current)
    end
end)
