local ns = _G.DF_NS or {}
local L = ns.L
local Host = ns.ProfHost
if not Host then return end

local DG = Host.DG
local MakeFS = Host.MakeFS
local NewButton, SetButtonSelected = Host.NewButton, Host.SetButtonSelected
local AddBtnIcon = Host.AddBtnIcon
local C_GOLD, C_GREY, C_DIM, C_WHITE, C_TEXT = Host.C_GOLD, Host.C_GREY, Host.C_DIM, Host.C_WHITE, Host.C_TEXT

local H = ns.hui
local LV = (H and H.layer) or {}
local CL2 = LV.L2 or { 0.09, 0.10, 0.13, 1 }
local CDIV = LV.DIV or { 0.11, 0.13, 0.16, 1 }
local C_WARN = { 0.86, 0.72, 0.42 }
local C_OK = { 0.56, 0.85, 0.63 }

local DM = ns.Darkmoon

local PAD, GAP, HDR, BOT = 8, 8, 38, 8
local BAR_GUT = 8

local LC_H, LC_PAD, LC_ICON, LC_IGAP = 44, 6, 32, 5
local LC_TX = LC_PAD + LC_ICON + LC_IGAP
local HDR_ROW = 22
local BTN_H, TROW, ROW_PITCH, ROW_H = 24, 24, 24, 22

local RING = { "①", "②", "③", "④", "⑤" }
local BAND = { 0, 0, 0, 0, 3000, 9000, 21000, 42000 }

local function Gold(str)
    return "|cffffd100" .. tostring(str) .. "|r"
end

local function StrW(txt, size)
    local PM = ns.ProfModule
    if PM and PM.TextW then
        local ok, w = pcall(PM.TextW, txt, size or 14)
        if ok and type(w) == "number" and w > 0 then return w end
    end
    return #tostring(txt) * (size or 14) * 0.55
end

local function FH(fs, fb)
    local sz = fb or 14
    if type(fs) == "table" then
        if type(fs.GetFont) == "function" then
            local _, fsz = fs:GetFont()
            sz = tonumber(fsz) or sz
        end
        if type(fs.GetStringHeight) == "function" then
            local h = fs:GetStringHeight()
            if type(h) == "number" and h > 0 then return h end
        end
        if type(fs.GetText) == "function" and type(fs.GetWidth) == "function" then
            local txt = fs:GetText()
            local w = fs:GetWidth()
            if type(txt) == "string" and txt ~= "" and type(w) == "number" and w > 8 then
                local lines = math.max(1, math.ceil(StrW(txt, sz) / (w + 0.5)))
                return lines * (sz + 3)
            end
        end
    end
    return sz
end

local ACC_MAX = (type(MAX_ACCOUNT_MACROS) == "number" and MAX_ACCOUNT_MACROS) or 120

local function MacroByName(name)
    if type(GetMacroInfo) ~= "function" then return 0, 0 end
    for i = 1, ACC_MAX do
        if GetMacroInfo(i) == name then return i, 1 end
    end
    for i = ACC_MAX + 1, 190 do
        if GetMacroInfo(i) == name then return i, 2 end
    end
    return 0, 0
end

local function MakeMacro(name, body, icon)
    if type(CreateMacro) ~= "function" then return end
    if InCombatLockdown and InCombatLockdown() then
        if DEFAULT_CHAT_FRAME then DEFAULT_CHAT_FRAME:AddMessage(L["战斗中不能创建宏"]) end
        return
    end
    local idx, zone = MacroByName(name)
    if zone == 1 and type(EditMacro) == "function" then
        if not pcall(EditMacro, idx, name, icon, body) then idx = 0 end
    else
        idx = 0
    end
    if idx == 0 then
        if zone == 2 and type(DeleteMacro) == "function" then
            pcall(DeleteMacro, idx)
        end
        local ok, res = pcall(CreateMacro, name, icon, body, false)
        if ok and type(res) == "number" and res > 0 then idx = res end
    end
    if idx <= 0 then
        if DEFAULT_CHAT_FRAME then DEFAULT_CHAT_FRAME:AddMessage(L["创建失败：通用宏已达上限"]) end
        return
    end
    C_Timer.After(0, function()
        local live = MacroByName(name)
        if live > 0 then idx = live end
        if type(PickupMacro) == "function" then pcall(PickupMacro, idx) end
        if DEFAULT_CHAT_FRAME then
            DEFAULT_CHAT_FRAME:AddMessage(format(L["宏已就绪：%s · 拖到动作条"], name))
        end
    end)
end

local function MyTickets()
    local ci = C_CurrencyInfo and C_CurrencyInfo.GetCurrencyInfo and C_CurrencyInfo.GetCurrencyInfo(DM.CURRENCY)
    if ci then return ci.quantity or 0 end
    return 0
end

local function MyRep()
    if C_Reputation and C_Reputation.GetFactionDataByID then
        local d = C_Reputation.GetFactionDataByID(DM.FACTION)
        if d then
            local v = d.currentStanding or d.currentReputation or d.standing
            if type(v) == "number" then return v end
        end
    end
    local _, _, standing, bmin, bmax, bval = GetFactionInfoByID(DM.FACTION)
    if type(bval) ~= "number" then return 0 end
    if bval < bmin then return (BAND[standing] or 0) + (bval - bmin) end
    return bval
end

local function CalNow()
    local get = C_DateAndTime and C_DateAndTime.GetCurrentCalendarTime
    if not get then return nil end
    local ok, t = pcall(get)
    if ok and type(t) == "table" and type(t.monthDay) == "number" then return t end
    return nil
end

local function MonthDays(m)
    if C_Calendar and C_Calendar.GetMonthInfo then
        local ok, info = pcall(C_Calendar.GetMonthInfo, m)
        if ok and type(info) == "table" and type(info.numDays) == "number" then
            return info.numDays
        end
    end
    return 31
end

local function DmRange(m)
    if not (C_Calendar and C_Calendar.GetNumDayEvents and C_Calendar.GetDayEvent) then return nil end
    local needle = L["暗月马戏团"]
    local lo, hi
    for d = 1, MonthDays(m) do
        local ok, n = pcall(C_Calendar.GetNumDayEvents, m, d)
        if ok and type(n) == "number" and n > 0 then
            for i = 1, n do
                local ok2, ev = pcall(C_Calendar.GetDayEvent, m, d, i)
                if ok2 and type(ev) == "table" and type(ev.title) == "string"
                    and ev.title:find(needle, 1, true) then
                    if not lo then lo = d end
                    hi = d
                    break
                end
            end
        end
    end
    if lo then return lo, hi end
end

local function DmWhen()
    local now = CalNow()
    if not now then return nil end
    local lo, hi = DmRange(0)
    if lo and now.monthDay >= lo and now.monthDay <= hi then
        return "on", lo, hi, now.monthDay, 0, now.month
    end
    for m = 0, 3 do
        local a, b = DmRange(m)
        if a and (m > 0 or a > now.monthDay) then
            return "next", a, b, now.monthDay, m, ((now.month + m - 1) % 12) + 1
        end
    end
    return nil
end

local DmCalCache = {}

local function DmRounds()
    local out, seen = {}, {}
    if not (C_Calendar and C_Calendar.GetMonthInfo) then return out end
    for m = -3, 8 do
        local ok, mi = pcall(C_Calendar.GetMonthInfo, m)
        if ok and type(mi) == "table" and type(mi.month) == "number" then
            local a, b = DmRange(m)
            if a then
                local k = tostring(mi.year) .. "-" .. tostring(mi.month)
                if not seen[k] then
                    seen[k] = true
                    out[#out + 1] = { mo = mi.month, yr = mi.year, a = a, b = b,
                        zi = (mi.month % 2 == 1) and 1 or 2 }
                end
            end
        end
    end
    for k, r in pairs(DmCalCache) do
        if not seen[k] then
            seen[k] = true
            out[#out + 1] = { mo = r.mo, yr = r.yr, a = r.a, b = r.b, zi = r.zi }
        end
    end
    table.sort(out, function(x, y)
        local kx = (x.yr or 0) * 10000 + x.mo * 100 + x.a
        local ky = (y.yr or 0) * 10000 + y.mo * 100 + y.a
        return kx < ky
    end)
    return out
end

local function DmKey(yr, mo, d)
    return (yr or 0) * 10000 + mo * 100 + d
end

local function DmPick()
    local now = CalNow()
    local rs = DmRounds()
    if not now then return nil, nil, rs end
    local tk = DmKey(now.year, now.month, now.monthDay)
    local cur, nxt, nk
    for _, r in ipairs(rs) do
        local sk = DmKey(r.yr, r.mo, r.a)
        local ek = DmKey(r.yr, r.mo, r.b)
        if tk >= sk and tk <= ek then cur = r end
        if sk > tk and (not nk or sk < nk) then nxt = r; nk = sk end
    end
    return cur, nxt, rs
end

local function RepBand(rep)
    if rep >= 42000 then return L["崇拜"] end
    if rep >= 21000 then return L["崇敬"] end
    if rep >= 9000 then return L["尊敬"] end
    if rep >= 3000 then return L["友善"] end
    return L["中立"]
end

local function MatPrice(id)
    local RA = ns.ProfRouteAuto
    if not RA or not RA.AHPriceOf then return nil end
    local p = RA.AHPriceOf(id)
    if type(p) == "number" and p > 0 then return p end
    return nil
end

local function ShortMoney(c)
    if type(c) ~= "number" or c <= 0 then return "—" end
    if c >= 100000 then return format("%d" .. L["金"], math.floor(c / 10000 + 0.5)) end
    if c >= 10000 then return format("%.1f" .. L["金"], c / 10000) end
    if c >= 1000 then return format("%d" .. L["银"], math.floor(c / 100 + 0.5)) end
    if c >= 100 then return format("%.1f" .. L["银"], c / 100) end
    return format("%d" .. L["铜"], math.floor(c + 0.5))
end

local function MoneyStr(c)
    local RA = ns.ProfRouteAuto
    if RA and RA.MoneyStr then
        local ok, s = pcall(RA.MoneyStr, c)
        if ok and type(s) == "string" then return s end
    end
    local g = math.floor(c / 10000)
    local s = math.floor(c / 100) % 100
    if g > 0 then return format("%d金%d银", g, s) end
    return format("%d银", s)
end

local function BestOfTier(t)
    local best
    local function Try(id, q, ln)
        local p = id and q and MatPrice(id)
        if p then
            local c = p * q
            if not best or c < best.c then best = { id = id, q = q, p = p, c = c, line = ln } end
        end
    end
    for _, ln in ipairs(DM.LINES) do
        Try(ln.mats[t], ln.qty[t], ln)
        if ln.alt and ln.alt.t == t then Try(ln.alt.id, ln.alt.qty, ln) end
    end
    return best
end

local function AvailAt(rep, lvl)
    local out = {}
    for t = 1, 5 do
        local d = DM.TIERS[t]
        if lvl >= d.lvl and rep < d.cut then out[#out + 1] = t end
    end
    return out
end

local function MaxTickets(rep, lvl)
    local sum, r, guard = 0, rep, 0
    while r < 5999 and guard < 200 do
        guard = guard + 1
        local best = 0
        for _, t in ipairs(AvailAt(r, lvl)) do
            if DM.TIERS[t].tk > best then best = DM.TIERS[t].tk end
        end
        if best <= 0 then break end
        sum = sum + best
        r = r + 100
    end
    return sum
end

local function Solve(rep0, want, lvl)
    local cap = want + 20
    local layers = {}
    local base = {}
    base[0] = { c = 0 }
    layers[1] = base
    local best, maxStep = nil, 0
    if rep0 < 5999 then maxStep = math.floor((5998 - rep0) / 100) + 1 end
    local step = 0
    while step < maxStep do
        local rep = rep0 + 100 * step
        local avail = AvailAt(rep, lvl)
        if #avail == 0 then break end
        local prev = layers[#layers]
        local nextL, any = {}, false
        for tk, st in pairs(prev) do
            for _, t in ipairs(avail) do
                local o = BestOfTier(t)
                if o then
                    local nt = tk + DM.TIERS[t].tk
                    if nt > cap then nt = cap end
                    local nc = st.c + o.c
                    local cur = nextL[nt]
                    if not cur or nc < cur.c then
                        nextL[nt] = { c = nc, tier = t, prev = tk }
                        any = true
                    end
                end
            end
        end
        if not any then break end
        layers[#layers + 1] = nextL
        for tk = want, cap do
            local st = nextL[tk]
            if st and (not best or st.c < best.c) then
                best = { c = st.c, step = step + 1, tk = tk }
            end
        end
        step = step + 1
    end
    if not best then return nil end
    local cnt = { 0, 0, 0, 0, 0 }
    local s, tk = best.step, best.tk
    while s > 0 do
        local nd = layers[s + 1] and layers[s + 1][tk]
        if not nd or not nd.tier then break end
        cnt[nd.tier] = cnt[nd.tier] + 1
        tk = nd.prev
        s = s - 1
    end
    return { cnt = cnt, tickets = best.tk, cost = best.c, turns = best.step }
end

local function Build(EG, page)
    EG.dmLootRows = {}
    if EG.dmFrame or not DM then return end

    local GUT = (DG and DG.GUTTER) or 8
    local W = EG.RIGHT_W - GUT
    local CW = W - BAR_GUT

    local root = CreateFrame("Frame", nil, page)
    root:SetPoint("TOPLEFT", page, "TOPLEFT", EG.X0 + GUT, -(EG.TOP_EDGE + GUT))
    root:SetPoint("BOTTOMRIGHT", page, "BOTTOMRIGHT", -(EG.EDGE + GUT), EG.EDGE + GUT)
    root:Hide()
    EG.dmFrame = root

    local function SkinBox(f, base, rad)
        if H and H.SkinPopup then
            H.SkinPopup(f, rad or 6, nil, base)
        elseif f.SetBackdrop then
            f:SetBackdrop({
                bgFile = "Interface\\Buttons\\WHITE8x8",
                edgeFile = "Interface\\Buttons\\WHITE8x8",
                edgeSize = 1,
            })
            f:SetBackdropColor(base[1], base[2], base[3], base[4] or 1)
            f:SetBackdropBorderColor(1, 1, 1, 0.1)
        end
    end

    local function SplitCoord(str)
        if type(str) ~= "string" then return str end
        local a, b = str:match("(%d+%.?%d*)%s*,%s*(%d+%.?%d*)")
        local mx, my = tonumber(a), tonumber(b)
        if not (mx and my) then return str end
        if mx < 0 or mx > 100 or my < 0 or my > 100 then return str end
        local lab = str:gsub("%d+%.?%d*%s*,%s*%d+%.?%d*", "")
        lab = lab:gsub("^[%s·]+", ""):gsub("[%s·]+$", "")
        return lab, mx, my
    end

    local function ZoneIdx()
        local cur, nxt = DmPick()
        local r = cur or nxt
        if r then return r.zi end
        local now = CalNow()
        return (now and now.month % 2 == 0) and 2 or 1
    end
    EG.dmZoneIdx = ZoneIdx

    local function MapBtn(p, mx, my, map)
        local bt = NewButton(p, L["地图"], 68, BTN_H, 14)
        if AddBtnIcon then AddBtnIcon(bt, "EntryPin", 14, 5) end
        bt:SetScript("OnClick", function()
            if EG.RtGo then EG.RtGo(map or DM.ZONE.map, mx, my) end
        end)
        bt:SetScript("OnEnter", function(self)
            if not GameTooltip then return end
            GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
            GameTooltip:ClearLines()
            GameTooltip:AddLine(format("%.1f, %.1f", mx, my), 1, 0.82, 0.24, false)
            GameTooltip:AddLine(L["点击在世界地图上定位"], 0.8, 0.8, 0.8, true)
            GameTooltip:Show()
        end)
        bt:SetScript("OnLeave", function()
            if GameTooltip then GameTooltip:Hide() end
        end)
        return bt
    end

    local function BtnSide(p, btn, text)
        if type(text) ~= "string" or text == "" then return end
        local fs = MakeFS(p, 12, C_GREY, "RIGHT")
        fs:SetWordWrap(false)
        fs:SetPoint("RIGHT", btn, "LEFT", -GAP, 0)
        fs:SetText(text)
        return fs
    end

    local function NewCard(p, x, y, w, title, sub, mx, my, btn)
        local f = CreateFrame("Frame", nil, p)
        f:SetSize(w, 1)
        f:SetPoint("TOPLEFT", p, "TOPLEFT", x, y)
        SkinBox(f, CL2, 6)
        local hh = (mx or btn) and (PAD + BTN_H + 12) or HDR
        f.__hdr = hh
        f.__cur = -PAD
        f.__w = w
        if title then
            local rowH = (mx or btn) and BTN_H or (HDR - 2 * PAD)
            local row = CreateFrame("Frame", nil, f)
            row:SetPoint("TOPLEFT", f, "TOPLEFT", PAD, -PAD)
            row:SetPoint("BOTTOMRIGHT", f, "TOPRIGHT", -PAD, -PAD - rowH)
            local t = MakeFS(f, 16, C_GOLD, "LEFT")
            t:SetPoint("LEFT", row, "LEFT", 0, 0)
            t:SetText(title)
            local last
            if sub then
                local sm = MakeFS(f, 12, C_GREY, "LEFT")
                sm:SetPoint("LEFT", t, "RIGHT", GAP, 0)
                sm:SetText(sub)
                last = sm
            end
            if mx then
                local mb = MapBtn(f, mx, my)
                mb:SetPoint("LEFT", last or t, "RIGHT", GAP, 0)
            end
            local dv = f:CreateTexture(nil, "ARTWORK")
            dv:SetColorTexture(CDIV[1], CDIV[2], CDIV[3], 1)
            dv:SetSize(w - 2 * PAD, 1)
            dv:SetPoint("TOPLEFT", f, "TOPLEFT", PAD, -(hh - PAD))
            f.__cur = -hh
        end
        return f
    end

    local function CloseCard(f, minH)
        local h = -f.__cur + BOT
        if minH and minH > h then h = minH end
        f:SetHeight(h)
        return h
    end

    local function Put(p, x, y, text, size, color, w)
        local fs = MakeFS(p, size or 14, color or C_TEXT, "LEFT")
        fs:SetPoint("TOPLEFT", p, "TOPLEFT", x, y)
        if w then
            fs:SetWidth(w)
            fs:SetWordWrap(true)
        else
            fs:SetWordWrap(false)
        end
        fs:SetText(text)
        return fs
    end

    local function PutR(p, x, y, text, size, color)
        local fs = MakeFS(p, size or 12, color or C_GREY, "RIGHT")
        fs:SetPoint("TOPRIGHT", p, "TOPRIGHT", x, y)
        fs:SetWordWrap(false)
        fs:SetText(text)
        return fs
    end

    local function Para(f, text, size, color, gap, x, w)
        local fs = MakeFS(f, size or 14, color or C_TEXT, "LEFT")
        fs:SetPoint("TOPLEFT", f, "TOPLEFT", x or PAD, f.__cur)
        fs:SetWidth(w or (f.__w - 2 * PAD))
        fs:SetWordWrap(true)
        fs:SetText(text)
        f.__cur = f.__cur - FH(fs, size or 14) - (gap or 0)
        return fs
    end

    local function Bullets(f, list, size, gap)
        for i, s in ipairs(list) do
            Para(f, "· " .. s, size or 14, C_TEXT, i < #list and (gap or 6) or 0)
        end
    end

    local function Block(p, x, y, w, h)
        local f = CreateFrame("Frame", nil, p)
        f:SetSize(w, h)
        f:SetPoint("TOPLEFT", p, "TOPLEFT", x, y)
        SkinBox(f, CL2, 6)
        local row = CreateFrame("Frame", nil, f)
        row:SetPoint("TOPLEFT", f, "TOPLEFT", 0, -PAD)
        row:SetPoint("BOTTOMRIGHT", f, "TOPRIGHT", 0, -(PAD + BTN_H))
        f.__row = row
        return f
    end

    local function BlockTitle(b, text, size, color)
        local fs = MakeFS(b, size or 14, color or C_GOLD, "LEFT")
        fs:SetWordWrap(false)
        fs:SetPoint("LEFT", b.__row, "LEFT", PAD, 0)
        fs:SetText(text)
        return fs
    end

    local function RowSide(b, text, dx)
        if type(text) ~= "string" or text == "" then return end
        local fs = MakeFS(b, 12, C_GREY, "RIGHT")
        fs:SetWordWrap(false)
        fs:SetPoint("RIGHT", b.__row, "RIGHT", dx or -PAD, 0)
        fs:SetText(text)
        return fs
    end

    local refBuilders = {}
    local function RichPara(f, build, size, gap)
        local fs = Para(f, build(), size or 14, C_TEXT, gap)
        refBuilders[#refBuilders + 1] = { fs = fs, build = build }
        return fs
    end
    local function RichPut(f, x, y, build, size, color, w)
        local fs = Put(f, x, y, build(), size, color, w)
        refBuilders[#refBuilders + 1] = { fs = fs, build = build }
        return fs
    end

    local function ItemRef(id)
        local name = DG.ItemName(id)
        local r, g, b = DG.QColor(DG.QualOf(id))
        return format("|cff%02x%02x%02x|Hitem:%d:0:0:0:0:0:0:0:0|h[%s]|h|r",
            math.floor(r * 255 + 0.5), math.floor(g * 255 + 0.5), math.floor(b * 255 + 0.5), id, name)
    end
    local function QuestRef(id)
        return DG.QuestLink(id) or ("[quest:" .. tostring(id) .. "]")
    end

    local function ItemTex(id)
        local tex = DG.ItemIcon(id)
        if type(tex) == "number" then return tex end
        tex = tostring(tex)
        if tex:find("\\", 1, true) then return tex end
        return "Interface\\Icons\\" .. tex
    end

    local function PartOf(id)
        local loc = select(4, DG.ItemInfoInstant(id))
        local a = type(loc) == "string" and _G[loc] or loc
        if type(a) == "string" and a ~= "" then return a end
        return DG.ItemMeta(id)
    end

    local function Ring(tex, id)
        if H and H.SetIconRing then
            local ok, r, g, b = pcall(DG.QColor, DG.QualOf(id))
            if ok and type(r) == "number" then H.SetIconRing(tex, { r, g, b }) end
        end
    end

    local function MatIcon(p, x, y, id, qty)
        local bt = CreateFrame("Button", nil, p)
        bt:SetSize(18, 18)
        bt:SetPoint("TOPLEFT", p, "TOPLEFT", x, y)
        local tex = bt:CreateTexture(nil, "ARTWORK")
        tex:SetAllPoints()
        tex:SetTexture(ItemTex(id))
        tex:SetTexCoord(0.07, 0.93, 0.07, 0.93)
        Ring(tex, id)
        bt.__it = { id }
        bt:SetScript("OnClick", function(self2, button)
            if DG.ItemShiftClick then DG.ItemShiftClick(self2, button) end
        end)
        bt:SetScript("OnEnter", function(self2)
            DG.ShowItemTip(self2, self2.__it)
            if GameTooltip:IsShown() then
                GameTooltip:AddLine(L["需要"] .. " " .. tostring(qty), 0.85, 0.85, 0.85)
                GameTooltip:Show()
            end
        end)
        bt:SetScript("OnLeave", function() GameTooltip:Hide() end)
        return bt
    end

    local function TextW(txt, size)
        local PM = ns.ProfModule
        if PM and PM.TextW then
            local ok, w = pcall(PM.TextW, txt, size or 14)
            if ok and type(w) == "number" and w > 0 then return w end
        end
        return #tostring(txt) * (size or 14)
    end

    local function IconRef(p, x, y, id, sz)
        local bt = CreateFrame("Button", nil, p)
        bt:SetSize(sz or 18, sz or 18)
        bt:SetPoint("TOPLEFT", p, "TOPLEFT", x, y)
        local tex = bt:CreateTexture(nil, "ARTWORK")
        tex:SetAllPoints()
        tex:SetTexture(ItemTex(id))
        tex:SetTexCoord(0.07, 0.93, 0.07, 0.93)
        if H and H.RoundIcon then H.RoundIcon(tex) end
        Ring(tex, id)
        bt:SetScript("OnEnter", function(self) DG.ShowItemTip(self, { id }) end)
        bt:SetScript("OnLeave", function() GameTooltip:Hide() end)
        bt:SetScript("OnClick", function(self, button)
            if DG.ItemShiftClick then DG.ItemShiftClick(self, button) end
        end)
        return bt
    end

    local function TipBtn(fs, kind, id)
        local b = CreateFrame("Button", nil, fs:GetParent())
        b:SetAllPoints(fs)
        b:SetScript("OnEnter", function(self)
            if kind == "quest" then
                GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
                GameTooltip:ClearLines()
                local ok = pcall(GameTooltip.SetHyperlink, GameTooltip, "quest:" .. id .. ":0")
                if not ok then GameTooltip:AddLine("quest " .. tostring(id), 1, 1, 1) end
                GameTooltip:Show()
            else
                DG.ShowItemTip(self, { id })
            end
        end)
        b:SetScript("OnLeave", function() GameTooltip:Hide() end)
        if kind == "item" then
            b:SetScript("OnClick", function(self, button)
                if DG.ItemShiftClick then DG.ItemShiftClick(self, button) end
            end)
        end
        return b
    end

    local function LinkPut(p, x, y, id, size, w)
        local fs = Put(p, x, y, ItemRef(id), size or 14, C_TEXT, w)
        TipBtn(fs, "item", id)
        refBuilders[#refBuilders + 1] = { fs = fs, build = function() return ItemRef(id) end }
        return fs
    end

    local function QuestPut(p, x, y, qid, size, w)
        local fs = Put(p, x, y, QuestRef(qid), size or 14, C_TEXT, w)
        TipBtn(fs, "quest", qid)
        refBuilders[#refBuilders + 1] = { fs = fs, build = function() return QuestRef(qid) end }
        return fs
    end

    local function LootCard(p, x, y, w, id, sub, right, rcol, rightId)
        local bt = CreateFrame("Button", nil, p, "BackdropTemplate")
        bt:SetSize(w, LC_H)
        bt:SetPoint("TOPLEFT", p, "TOPLEFT", x, y)
        bt:SetBackdrop({
            bgFile = "Interface\\Buttons\\WHITE8x8",
            edgeFile = "Interface\\Buttons\\WHITE8x8",
            edgeSize = 1,
        })
        if H and H.HuiCardFX then H.HuiCardFX(bt, 12, 2) end

        local ic = bt:CreateTexture(nil, "ARTWORK")
        ic:SetSize(LC_ICON, LC_ICON)
        ic:SetPoint("LEFT", bt, "LEFT", LC_PAD, 0)
        ic:SetTexture(ItemTex(id))
        ic:SetTexCoord(0.07, 0.93, 0.07, 0.93)
        if H and H.RoundIcon then H.RoundIcon(ic) end
        Ring(ic, id)

        local rfs
        if right or rightId then
            rfs = MakeFS(bt, 14, rcol or C_GOLD, "RIGHT")
            rfs:SetPoint("TOPRIGHT", bt, "TOPRIGHT", -8, -6)
            rfs:SetWordWrap(false)
            if rightId then
                rfs:SetText(ItemRef(rightId))
                TipBtn(rfs, "item", rightId)
                refBuilders[#refBuilders + 1] = { fs = rfs, build = function() return ItemRef(rightId) end }
            else
                rfs:SetText(right)
            end
        end
        local rw = 0
        if rfs then rw = (rfs:GetStringWidth() or 0) + 8 end

        local nm, hasName = DG.ItemName(id)
        local nameW = w - LC_TX - 8 - rw
        local nfs = MakeFS(bt, 14, C_TEXT, "LEFT")
        nfs:SetPoint("TOPLEFT", bt, "TOPLEFT", LC_TX, -6)
        nfs:SetWordWrap(false)
        if TextW(nm, 14) > nameW - 2 then
            nfs:SetText(DG.FitText(nm, 14, nameW))
            if hasName then
                local r, g, b = DG.QColor(DG.QualOf(id))
                nfs:SetTextColor(r, g, b)
            else
                nfs:SetTextColor(C_GREY[1], C_GREY[2], C_GREY[3])
            end
        else
            nfs:SetText(ItemRef(id))
            TipBtn(nfs, "item", id)
            refBuilders[#refBuilders + 1] = { fs = nfs, build = function() return ItemRef(id) end }
        end

        if sub then
            local sw = w - LC_TX - 8
            local sfs = MakeFS(bt, 12, C_GREY, "LEFT")
            sfs:SetPoint("TOPLEFT", bt, "TOPLEFT", LC_TX, -26)
            sfs:SetWordWrap(false)
            sfs:SetWidth(sw)
            sfs:SetText(DG.FitText(sub, 12, sw))
        end

        bt.__it = { id }
        bt:SetScript("OnClick", function(self, button)
            if DG.ItemShiftClick then DG.ItemShiftClick(self, button) end
        end)
        bt:SetScript("OnEnter", function(self)
            if H and H.HuiCardState then H.HuiCardState(self, "hover") end
            DG.ShowItemTip(self, self.__it)
        end)
        bt:SetScript("OnLeave", function(self)
            if H and H.HuiCardState then H.HuiCardState(self, "norm") end
            GameTooltip:Hide()
        end)
        return bt
    end

    do
        local req = C_Item and C_Item.RequestLoadItemDataByID
        if req then
            local ids = {}
            for _, ln in ipairs(DM.LINES) do
                for _, id in ipairs(ln.mats) do ids[#ids + 1] = id end
            end
            for _, it in ipairs(DM.PRIZES) do ids[#ids + 1] = it.id end
            for _, d in ipairs(DM.DECKS) do
                ids[#ids + 1] = d.trinket
                ids[#ids + 1] = d.deck
            end
            ids[#ids + 1] = DM.FORTUNE_ITEM
            for _, c in ipairs(DM.FORTUNE_CARDS) do ids[#ids + 1] = c.item end
            for _, k in pairs(DM.PET_ITEMS) do ids[#ids + 1] = k end
            for _, id in ipairs(ids) do pcall(req, id) end
        end
    end

    local tabs = {
        { k = "overview", t = L["概览"] },
        { k = "ticket", t = L["奖券"] },
        { k = "prize", t = L["兑奖"] },
        { k = "fortune", t = L["占卜"] },
        { k = "deck", t = L["套牌"] },
        { k = "pet", t = L["宠物"] },
        { k = "game", t = L["小游戏"] },
    }

    EG.dmTabBtns = {}
    local tx = 0
    for _, it in ipairs(tabs) do
        local bt = NewButton(root, it.t, 56, BTN_H, 14)
        local fs = bt:GetFontString()
        local tw = fs and fs.GetStringWidth and fs:GetStringWidth() or 0
        if type(tw) ~= "number" then tw = 0 end
        local w = math.max(56, math.floor(tw + 20))
        bt:SetSize(w, BTN_H)
        bt:SetPoint("TOPLEFT", root, "TOPLEFT", tx, 0)
        local k = it.k
        bt:SetScript("OnClick", function()
            if EG.DarkmoonSetTab then EG.DarkmoonSetTab(k) end
        end)
        EG.dmTabBtns[k] = bt
        tx = tx + w + GAP
    end

    local sc = CreateFrame("ScrollFrame", nil, root)
    sc:SetPoint("TOPLEFT", root, "TOPLEFT", 0, -(BTN_H + GAP))
    sc:SetPoint("BOTTOMRIGHT", root, "BOTTOMRIGHT", 0, 0)
    if sc.SetClipsChildren then sc:SetClipsChildren(true) end
    sc:EnableMouseWheel(true)
    local child = CreateFrame("Frame", nil, sc)
    child:SetSize(CW, 10)
    sc:SetScrollChild(child)

    local track = CreateFrame("Frame", nil, root, "BackdropTemplate")
    if H and H.BuildCapsule then
        H.BuildCapsule(track, 3, CL2)
    else
        track:SetBackdrop({
            bgFile = "Interface\\Buttons\\WHITE8x8",
            edgeFile = "Interface\\Buttons\\WHITE8x8",
            edgeSize = 1,
        })
        track:SetBackdropColor(0, 0, 0, 0.25)
        track:SetBackdropBorderColor(1, 1, 1, 0.08)
    end
    track:SetWidth(7)
    track:SetPoint("TOPRIGHT", sc, "TOPRIGHT", 7, -2)
    track:SetPoint("BOTTOMRIGHT", sc, "BOTTOMRIGHT", 7, 2)
    track:SetFrameLevel((sc:GetFrameLevel() or 0) + 10)
    track:Hide()

    local thumb = CreateFrame("Button", nil, track)
    thumb:SetWidth(5)
    thumb:EnableMouse(true)
    local tp2 = nil
    if H and H.BuildCapsule then
        tp2 = H.BuildCapsule(thumb, 2, LV.L4)
    end
    thumb:SetScript("OnEnter", function()
        if tp2 then
            local c = LV.L5
            for _, t in ipairs(tp2) do t:SetVertexColor(c[1], c[2], c[3]) end
        end
    end)
    thumb:SetScript("OnLeave", function()
        if tp2 then
            local c = LV.L4
            for _, t in ipairs(tp2) do t:SetVertexColor(c[1], c[2], c[3]) end
        end
    end)
    thumb:SetPoint("TOP", track, "TOP", 0, -1)

    local function UpdateBar()
        if not sc:IsShown() then track:Hide() return end
        local viewH = sc:GetHeight()
        local contentH = child:GetHeight()
        if contentH <= viewH + 2 or viewH <= 0 then track:Hide() return end
        track:Show()
        local trackH = track:GetHeight() - 2
        local maxScroll = contentH - viewH
        local vpos = sc.GetVerticalScroll and sc:GetVerticalScroll() or 0
        if type(vpos) ~= "number" then vpos = 0 end
        if maxScroll <= 0 then maxScroll = 1 end
        local frac = math.min(1, math.max(0, vpos / maxScroll))
        local th = math.max(24, trackH * viewH / contentH)
        thumb:SetHeight(th)
        thumb:ClearAllPoints()
        thumb:SetPoint("TOP", track, "TOP", 0, -1 - frac * (trackH - th))
    end

    sc:SetScript("OnMouseWheel", function(_, delta)
        DG.WheelScroll(sc, child, delta)
        UpdateBar()
    end)

    thumb:SetScript("OnMouseDown", function(self, btn)
        if btn ~= "LeftButton" then return end
        local scale = UIParent and UIParent:GetEffectiveScale() or 1
        local cy0 = select(2, GetCursorPosition()) / scale
        local sc0 = sc:GetVerticalScroll()
        if type(sc0) ~= "number" then sc0 = 0 end
        self:SetScript("OnUpdate", function(self2)
            local cy = select(2, GetCursorPosition()) / scale
            local trackH = track:GetHeight() - 2
            local span = trackH - thumb:GetHeight()
            if span <= 0 then return end
            local maxScroll = child:GetHeight() - sc:GetHeight()
            if maxScroll <= 0 then return end
            local v = sc0 + (cy0 - cy) / span * maxScroll
            self2:SetHeight(thumb:GetHeight())
            sc:SetVerticalScroll(math.max(0, math.min(maxScroll, v)))
            UpdateBar()
        end)
    end)
    thumb:SetScript("OnMouseUp", function(self) self:SetScript("OnUpdate", nil) UpdateBar() end)
    thumb:SetScript("OnHide", function(self) self:SetScript("OnUpdate", nil) end)

    EG.dmScroll, EG.dmChild, EG.dmThumbUpdate = sc, child, UpdateBar

    EG.dmPanes = {}
    local function NewPane(key)
        local p = CreateFrame("Frame", nil, child)
        p:SetPoint("TOPLEFT", child, "TOPLEFT", 0, 0)
        p:SetSize(CW, 10)
        p.h = 10
        p:Hide()
        EG.dmPanes[key] = p
        return p
    end

    local function Section(p, x, y, title, sub)
        local f = CreateFrame("Frame", nil, p)
        f:SetSize(CW, 14)
        if x or y then f:SetPoint("TOPLEFT", p, "TOPLEFT", x or 0, y or 0) end
        local t = MakeFS(f, 14, C_WHITE, "LEFT")
        t:SetPoint("LEFT", f, "LEFT", 0, 0)
        t:SetText(title)
        if sub and sub ~= "" then
            local s = MakeFS(f, 12, C_GREY, "LEFT")
            s:SetPoint("LEFT", t, "RIGHT", GAP, 0)
            s:SetText(sub)
        end
        return f
    end

    local function GroupHeader(p, y, title, sub, count)
        local f = Section(p, 0, y, title, sub)
        if count then
            local c = MakeFS(f, 12, C_GREY, "RIGHT")
            c:SetPoint("RIGHT", f, "RIGHT", 0, 0)
            c:SetText(count)
        end
        return y - HDR_ROW
    end

    local ov = NewPane("overview")
    Section(ov, 0, 0, L["本轮"], L["每月一轮，联盟艾尔文森林 / 部落莫高雷"])
    local cw3 = math.floor((CW - 2 * GAP) / 3)
    local cellH = 76
    local VY = PAD + 14 + 12
    local SY = VY + 16 + 6
    local TW = function(txt, size)
        local PM = ns.ProfModule
        if PM and PM.TextW then
            local ok, w = pcall(PM.TextW, txt, size or 14)
            if ok and type(w) == "number" and w > 0 then return w end
        end
        return #tostring(txt) * (size or 14)
    end

    local function Cell(x, label, value, sub, tex, map, help)
        local c = Block(ov, x, -HDR_ROW, cw3, cellH)
        BlockTitle(c, label, 14, C_GREY)
        local lab, mx, my = SplitCoord(value)
        if mx then MapBtn(c, mx, my, map):SetPoint("TOPRIGHT", c, "TOPRIGHT", -PAD, -PAD) end
        if help then
            local hb = NewButton(c, "?", 24, BTN_H, 14)
            hb:SetPoint("TOPRIGHT", c, "TOPRIGHT", -PAD, -PAD)
            hb:SetScript("OnEnter", function(self)
                GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
                GameTooltip:ClearLines()
                GameTooltip:AddLine(L["赛程"], 1, 0.82, 0.24, false)
                for _, ln in ipairs(help()) do
                    GameTooltip:AddLine(ln, 0.8, 0.8, 0.8, false)
                end
                GameTooltip:AddLine(L["每月第一个周五搭台 · 周一开门 · 日历末日 04:00 收摊"], 0.72, 0.72, 0.72, true)
                GameTooltip:AddLine(L["数据读自游戏内日历，随日历实时更新"], 0.55, 0.55, 0.55, true)
                GameTooltip:Show()
            end)
            hb:SetScript("OnLeave", function() GameTooltip:Hide() end)
        end
        local vx = PAD
        if tex then
            local ic = c:CreateTexture(nil, "ARTWORK")
            ic:SetSize(16, 16)
            ic:SetPoint("TOPLEFT", c, "TOPLEFT", PAD, -VY)
            ic:SetTexture(tex)
            ic:SetTexCoord(0.07, 0.93, 0.07, 0.93)
            if H and H.RoundIcon then H.RoundIcon(ic) end
            vx = PAD + 16 + 6
        end
        local v = Put(c, vx, -VY, lab, 16, C_GOLD)
        v:SetWordWrap(false)
        local sfs = Put(c, PAD, -SY, sub or "", 12, C_GREY, cw3 - 2 * PAD)
        return v, sfs
    end

    local function CalRefresh()
        local now = CalNow()
        local cur, nxt, rs = DmPick()
        EG.dmCalLines = {}
        for _, r in ipairs(rs) do
            EG.dmCalLines[#EG.dmCalLines + 1] = format(L["%d月"], r.mo) .. "  " .. DM.ZONES[r.zi].name
                .. "  " .. format(L["%d日 – %d日"], r.a, r.b)
                .. ((cur == r) and ("   " .. L["进行中"]) or "")
        end
        if not EG.dmOpenVal then return end
        local dfmt = L["%d月%d日"]
        local mdfmt = L["%d/%d"]
        if cur and now then
            EG.dmOpenVal:SetText(L["开放中"] .. " · " .. L["还剩"] .. " "
                .. math.max(0, cur.b - now.monthDay) .. " " .. L["天"])
            local sub = format(mdfmt, cur.mo, cur.a) .. " – " .. format(mdfmt, cur.mo, cur.b) .. " 04:00"
            if nxt then sub = sub .. " · " .. L["下轮"] .. " " .. format(mdfmt, nxt.mo, nxt.a) end
            EG.dmOpenSub:SetText(sub)
        elseif nxt then
            EG.dmOpenVal:SetText(L["下轮"] .. " " .. format(dfmt, nxt.mo, nxt.a))
            EG.dmOpenSub:SetText(format(mdfmt, nxt.mo, nxt.a) .. " – " .. format(mdfmt, nxt.mo, nxt.b)
                .. " 04:00 · " .. L["开放"] .. " " .. (nxt.b - nxt.a + 1) .. " " .. L["天"])
        else
            EG.dmOpenVal:SetText(L["周五搭台 · 周一开门"])
            EG.dmOpenSub:SetText(L["下周日收摊，以游戏内日历为准"])
        end
        local r = cur or nxt
        if EG.dmZoneVal and r then
            local z = DM.ZONES[r.zi]
            EG.dmZoneVal:SetText(z.name)
            EG.dmZoneSub:SetText((z.sub or "") .. " · " .. (cur and L["本轮"] or L["下轮"]))
        end
    end
    EG.dmCalRefresh = CalRefresh

    local function ScanMonthAt(list, idx)
        if idx > #list then
            local now = CalNow()
            if now then pcall(C_Calendar.SetAbsMonth, now.month, now.year) end
            EG.dmCalBusy = false
            CalRefresh()
            return
        end
        local mm = list[idx]
        local ok = pcall(C_Calendar.SetAbsMonth, mm.mo, mm.yr)
        if not ok then
            ScanMonthAt(list, idx + 1)
            return
        end
        C_Timer.After(0.4, function()
            local nd = 31
            local oki, mi = pcall(C_Calendar.GetMonthInfo, 0)
            if oki and type(mi) == "table" and mi.numDays then nd = mi.numDays end
            local lo, hi
            for d = 1, nd do
                local ok2, n = pcall(C_Calendar.GetNumDayEvents, 0, d)
                if ok2 and type(n) == "number" and n > 0 then
                    for i = 1, n do
                        local ok3, ev = pcall(C_Calendar.GetDayEvent, 0, d, i)
                        if ok3 and type(ev) == "table" and type(ev.title) == "string"
                            and ev.title:find(L["暗月马戏团"], 1, true) then
                            if not lo then lo = d end
                            hi = d
                            break
                        end
                    end
                end
            end
            if lo then
                DmCalCache[tostring(mm.yr) .. "-" .. tostring(mm.mo)] = {
                    mo = mm.mo, yr = mm.yr, a = lo, b = hi,
                    zi = (mm.mo % 2 == 1) and 1 or 2,
                }
            end
            ScanMonthAt(list, idx + 1)
        end)
    end

    local function ScanCal()
        if EG.dmCalBusy then return end
        local now = CalNow()
        if not now or not (C_Calendar and C_Calendar.SetAbsMonth) then return end
        if _G.CalendarFrame and _G.CalendarFrame:IsShown() then return end
        local list = {}
        for i = -1, 3 do
            local mo, yr = now.month + i, now.year
            while mo > 12 do mo = mo - 12; yr = yr + 1 end
            while mo < 1 do mo = mo + 12; yr = yr - 1 end
            list[#list + 1] = { mo = mo, yr = yr }
        end
        EG.dmCalBusy = true
        ScanMonthAt(list, 1)
    end
    EG.dmCalScan = ScanCal

    local zi0 = ZoneIdx()
    local zn = DM.ZONES[zi0]
    local zv, zs = Cell(0, L["场地"], zn.name .. " " .. format("%.1f,%.0f", zn.x, zn.y),
        zn.sub or "", nil, zn.map)
    EG.dmZoneVal, EG.dmZoneSub = zv, zs
    local ov2, os2 = Cell(cw3 + GAP, L["开放"], "", "", nil, nil, function()
        return EG.dmCalLines or {}
    end)
    EG.dmOpenVal, EG.dmOpenSub = ov2, os2
    CalRefresh()
    C_Timer.After(1.5, function() pcall(ScanCal) end)
    local curIc = ItemTex(DM.CURRENCY)
    if C_CurrencyInfo and C_CurrencyInfo.GetCurrencyInfo then
        local ci = C_CurrencyInfo.GetCurrencyInfo(DM.CURRENCY)
        if ci and ci.iconFileID then curIc = ci.iconFileID end
    end
    EG.dmTicketVal = Cell((cw3 + GAP) * 2, L["我的暗月券"], "0 " .. L["张"], L["实时读取，交完马上变"], curIc)

    local py = -HDR_ROW - cellH - GAP

    local oc2 = NewCard(ov, 0, py, CW, L["怎么玩"])
    local stepH = -HDR
    local steps = {
        { n = "①", t = L["交材料"], d = L["营地四个 NPC 各收一类成品，采集、锻造、工程、制皮都能交"] },
        { n = "②", t = L["换暗月券"], d = L["交完直接给券，档次越高给得越多；同一档能反复交，声望过线才消失"] },
        { n = "③", t = L["兑奖"], d = L["吉瓦斯·格里加特 收券：50 张换 14 格包，1200 张换 60 级紫项链"] },
    }
    local stepMax = 0
    local descs = {}
    local stepW = math.floor((CW - 2 * PAD - 2 * GAP) / 3)
    for i, st in ipairs(steps) do
        local x = PAD + (i - 1) * (stepW + GAP)
        local num = Put(oc2, x, stepH, st.n, 16, C_GOLD)
        Put(oc2, x + (num:GetStringWidth() or 16) + 6, stepH + 2, st.t, 14, C_WHITE)
        local d = Put(oc2, x, stepH - 24, st.d, 14, C_GREY, stepW)
        local h = 24 + FH(d, 14)
        if h > stepMax then stepMax = h end
        descs[#descs + 1] = d
    end
    oc2.__cur = -HDR - stepMax - GAP
    Bullets(oc2, DM.PLAY_NOTES, 14, 6)
    CloseCard(oc2)

    py = py - oc2:GetHeight() - GAP
    local oc3 = NewCard(ov, 0, py, CW, L["时间与路线"])
    Bullets(oc3, DM.ROUTE_NOTES, 14, 6)
    local function AnnRow(y, pre, an, post)
        local prev
        local segs = {
            { t = pre, c = C_TEXT },
            { t = an.name, c = C_GOLD, go = an },
            { t = post, c = C_TEXT },
        }
        for _, seg in ipairs(segs) do
            local fs = MakeFS(oc3, 14, seg.c, "LEFT")
            fs:SetWordWrap(false)
            if prev then
                fs:SetPoint("LEFT", prev, "RIGHT", 0, 0)
            else
                fs:SetPoint("TOPLEFT", oc3, "TOPLEFT", PAD, y)
            end
            fs:SetText(seg.t)
            if seg.go then
                local b = CreateFrame("Button", nil, oc3)
                b:SetAllPoints(fs)
                b:SetScript("OnEnter", function(self)
                    GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
                    GameTooltip:ClearLines()
                    GameTooltip:AddLine(an.name, 1, 0.82, 0.24)
                    GameTooltip:AddLine(an.city .. " " .. format("%.1f, %.1f", an.x, an.y), 0.8, 0.8, 0.8, true)
                    GameTooltip:AddLine(L["点击在世界地图上定位"], 0.8, 0.8, 0.8, true)
                    GameTooltip:Show()
                end)
                b:SetScript("OnLeave", function() GameTooltip:Hide() end)
                b:SetScript("OnClick", function()
                    if EG.RtGo then EG.RtGo(an.map, an.x, an.y) end
                end)
            end
            prev = fs
        end
        return y - 18
    end
    local ay = oc3.__cur - 2
    ay = AnnRow(ay, L["报幕员在城里：铁炉堡「"], DM.ANNOUNCERS[1], L["」"]) + 6
    ay = AnnRow(ay, L["、奥格瑞玛「"], DM.ANNOUNCERS[2], L["」，见到他们就是这轮开了。"])
    oc3.__cur = ay
    CloseCard(oc3)
    py = py - oc3:GetHeight() - GAP
    local oc4 = NewCard(ov, 0, py, CW, L["声望与上限"])
    Bullets(oc4, DM.REP_NOTES, 14, 6)
    CloseCard(oc4)
    ov.h = -py + oc4:GetHeight() + BOT

    local tp = NewPane("ticket")
    local tcW1 = math.floor((CW - GAP) * 0.40)
    local tcW = CW - tcW1 - GAP

    local tc1 = NewCard(tp, 0, 0, tcW1, L["五个档次"], L["每交一次 +100 声望"], nil, nil, true)
    local tcol = math.floor((tcW1 - 2 * PAD) / 4)
    local tRows = {}
    local ty = -tc1.__hdr
    for i, d in ipairs(DM.TIERS) do
        tRows[i] = {
            Put(tc1, PAD, ty, RING[i], 16, C_GOLD),
            Put(tc1, PAD + tcol, ty + 2, L["等级"] .. " " .. d.lvl, 14, C_TEXT),
            Put(tc1, PAD + tcol * 2, ty + 2, d.tk .. " " .. L["张"], 14, C_GOLD),
            Put(tc1, PAD + tcol * 3, ty + 2, RepBand(d.cut) .. " " .. d.cut, 14, C_GREY),
        }
        ty = ty - TROW
    end
    tc1.__cur = ty + TROW - 16
    CloseCard(tc1)
    local help = NewButton(tc1, "?", 24, BTN_H, 14)
    help:SetPoint("TOPRIGHT", tc1, "TOPRIGHT", -PAD, -PAD)
    help:SetScript("OnEnter", function(self)
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
        GameTooltip:ClearLines()
        GameTooltip:AddLine(L["声望规则"], 1, 0.82, 0.24, false)
        GameTooltip:AddLine(L["过线该档任务整条消失，只能往上交 —— 低档趁早交完。"], 0.86, 0.72, 0.42, true)
        GameTooltip:AddLine(L["声望跨轮不清零，上一轮交过的会累积到这一轮。"], 0.75, 0.75, 0.75, true)
        GameTooltip:Show()
    end)
    help:SetScript("OnLeave", function() GameTooltip:Hide() end)
    local tNat = tc1:GetHeight()

    local tc3 = NewCard(tp, tcW1 + GAP, 0, tcW, L["算一算"], L["按拍卖行单价，声望算次数"], nil, nil, true)
    local impW = math.max(88, (ns.ProfModule and ns.ProfModule.TextW
        and select(2, pcall(ns.ProfModule.TextW, L["导入拍卖行"], 14)) or 84) + 20)
    local impBtn = NewButton(tc3, L["导入拍卖行"], impW, BTN_H, 14)
    impBtn:SetPoint("TOPRIGHT", tc3, "TOPRIGHT", -PAD, -PAD)
    impBtn:SetScript("OnEnter", function(self)
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
        GameTooltip:ClearLines()
        GameTooltip:AddLine(L["导入拍卖行"], 1, 0.82, 0.24, false)
        GameTooltip:AddLine(L["把当前方案要交的材料按数量导入拍卖行购物清单，清单名带上暗月马戏团。"], 0.8, 0.8, 0.8, true)
        GameTooltip:Show()
    end)
    impBtn:SetScript("OnLeave", function() GameTooltip:Hide() end)
    impBtn:SetScript("OnClick", function()
        local AB = ns.AuctionBridge
        local items = {}
        local tot = {}
        for _, e in ipairs(EG.dmPlan or {}) do
            tot[e.id] = (tot[e.id] or 0) + e.q * e.n
        end
        for id, need in pairs(tot) do
            items[#items + 1] = { name = DG.ItemName(id), need = need }
        end
        if AB and AB.DoImport then AB.DoImport(L["暗月马戏团"], items) end
        ns.PlaySound(1)
    end)
    local lab = MakeFS(tc3, 14, C_GREY, "RIGHT")
    lab:SetWordWrap(false)
    lab:SetText(L["目标"])
    local lw = lab:GetStringWidth() or 28
    local eb = ns.CreateEditBox(tc3, 52)
    eb:SetHeight(BTN_H)
    eb:SetPoint("TOPLEFT", tc3, "TOPLEFT", PAD + lw + GAP, -HDR)
    lab:SetPoint("RIGHT", eb, "LEFT", -GAP, 0)
    if eb.SetNumeric then eb:SetNumeric(true) end
    eb:SetMaxLetters(5)
    eb:SetTextInsets(5, 5, 0, 0)
    eb:SetJustifyH("RIGHT")
    eb:SetFont(ns.FONT or STANDARD_TEXT_FONT or "Fonts\\FRIZQT__.TTF", 14, "OUTLINE")
    eb:SetTextColor(1, 0.82, 0.24)
    eb:SetText("50")
    EG.dmWant = eb

    local CALC_ROW = -HDR
    local ROW_Y0 = -HDR - BTN_H - GAP
    local COST_W = 88
    local infoX = PAD + lw + GAP + 52 + GAP
    local calcRow = CreateFrame("Frame", nil, tc3)
    calcRow:SetPoint("TOPLEFT", tc3, "TOPLEFT", 0, CALC_ROW)
    calcRow:SetPoint("BOTTOMRIGHT", tc3, "TOPRIGHT", 0, CALC_ROW - BTN_H)
    local info = MakeFS(tc3, 12, C_GREY, "LEFT")
    info:SetPoint("LEFT", calcRow, "LEFT", infoX, 0)
    info:SetWordWrap(false)
    EG.dmInfo = info
    local budget = MakeFS(tc3, 12, C_WARN, "RIGHT")
    budget:SetWordWrap(false)
    budget:SetPoint("RIGHT", calcRow, "RIGHT", -PAD, 0)
    EG.dmBudget = budget

    EG.dmRows = {}
    for i = 1, 5 do
        local r = CreateFrame("Frame", nil, tc3)
        r:SetSize(tcW - 2 * PAD, ROW_H)
        r.icon = r:CreateTexture(nil, "ARTWORK")
        r.icon:SetSize(18, 18)
        r.icon:SetPoint("LEFT", r, "LEFT", 0, 0)
        r.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
        r.name = MakeFS(r, 14, C_TEXT, "LEFT")
        r.name:SetPoint("LEFT", r, "LEFT", 26, 0)
        r.name:SetWordWrap(false)
        r.cost = MakeFS(r, 14, C_GOLD, "RIGHT")
        r.cost:SetWidth(COST_W)
        r.cost:SetWordWrap(false)
        r.cost:SetPoint("RIGHT", r, "RIGHT", 0, 0)
        r.right = MakeFS(r, 14, C_GOLD, "RIGHT")
        r.right:SetPoint("RIGHT", r.cost, "LEFT", -GAP, 0)
        r:Hide()
        EG.dmRows[i] = r
    end

    local sum = MakeFS(tc3, 16, C_GOLD, "RIGHT")
    sum:SetPoint("BOTTOMRIGHT", tc3, "BOTTOMRIGHT", -PAD, BOT)
    EG.dmSum = sum
    local note = MakeFS(tc3, 12, C_GREY, "LEFT")
    note:SetWordWrap(true)
    note:SetPoint("BOTTOMLEFT", tc3, "BOTTOMLEFT", PAD, BOT + 2)
    note:SetWidth(tcW - 2 * PAD)
    EG.dmNote = note
    CloseCard(tc3, -ROW_Y0 + 48)

    local matW = math.floor((CW - GAP) / 2)
    local matBH = PAD + BTN_H + GAP + 6 * ROW_PITCH + PAD
    local PRICE_R, TK_R, QTY_R = 64, 116, 164
    local C_UP = { 0.86, 0.42, 0.42 }
    local C_DN = { 0.45, 0.86, 0.55 }
    local nameW = matW - QTY_R - 30 - GAP
    local function TierMins()
        local mins = {}
        local function Put2(t, id, q)
            local p2 = id and MatPrice(id)
            if p2 and q then
                local c2 = p2 * q
                if not mins[t] or c2 < mins[t] then mins[t] = c2 end
            end
        end
        for t = 1, 5 do
            for _, ln in ipairs(DM.LINES) do
                Put2(t, ln.mats[t], ln.qty[t])
                if ln.alt and ln.alt.t == t then Put2(t, ln.alt.id, ln.alt.qty) end
            end
        end
        return mins
    end
    EG.dmMatRows = {}
    local tmSec = Section(tp, nil, nil, L["四条材料线"], L["不用会专业，成品直接拍卖行买"])
    local tmBlocks = {}
    local zi = ZoneIdx()
    local zoneNow = DM.ZONES[zi]
    local tmH = {}
    local tmRows = {}
    for li, ln in ipairs(DM.LINES) do
        local nRows = 5 + (ln.alt and 1 or 0)
        local bh = PAD + BTN_H + GAP + nRows * ROW_PITCH + PAD
        local b = Block(tp, 0, 0, matW, bh)
        BlockTitle(b, ln.kind .. " · " .. ln.npcName, 14, C_GOLD)
        local posStr = (zi == 2 and ln.pos2) or ln.pos
        local lab, mx, my = SplitCoord(posStr)
        if mx then
            local mb = MapBtn(b, mx, my, zoneNow.map)
            mb:SetPoint("TOPRIGHT", b, "TOPRIGHT", -PAD, -PAD)
            BtnSide(b, mb, lab)
        elseif lab ~= "" then
            RowSide(b, lab, -PAD)
        end
        local rowAt = 0
        local rowRefs = {}
        local function MatRow(t, id, q)
            rowAt = rowAt + 1
            local y = -(PAD + BTN_H + GAP) - (rowAt - 1) * ROW_PITCH
            local ico = MatIcon(b, PAD, y + 2, id, q)
            local qty = PutR(b, -QTY_R, y + 2, "×" .. q, 12, C_GREY)
            local tkv = PutR(b, -TK_R, y, DM.TIERS[t].tk .. " " .. L["张"], 14, C_GOLD)
            local pfs = PutR(b, -PRICE_R, y + 1, "—", 12, C_DIM)
            local nfs
            if TextW(DG.ItemName(id), 14) > nameW - 2 then
                nfs = Put(b, PAD + 18 + 4, y, DG.FitText(DG.ItemName(id), 14, nameW), 14, C_TEXT)
            else
                nfs = LinkPut(b, PAD + 18 + 4, y, id, 14)
            end
            local chip
            if H and H.MakeSolidChip and H.PaintSolidChip then
                chip = H.MakeSolidChip(b, (b:GetFrameLevel() or 0) + 2, 14)
                chip.t:SetFont(ns.FONT, 12, "")
                chip.t.__chipFs = 12
                chip:SetPoint("TOPRIGHT", b, "TOPRIGHT", -PAD, y)
            end
            rowRefs[#rowRefs + 1] = { ico = ico, qty = qty, tkv = tkv, pfs = pfs, nfs = nfs, chip = chip }
            EG.dmMatRows[#EG.dmMatRows + 1] = { id = id, t = t, q = q, price = pfs, chip = chip }
        end
        for t = 1, 5 do MatRow(t, ln.mats[t], ln.qty[t]) end
        if ln.alt then MatRow(ln.alt.t, ln.alt.id, ln.alt.qty) end
        tmBlocks[li] = b
        tmH[li] = bh
        tmRows[li] = rowRefs
    end

    local tcNeed = 0
    local function PaintPrices()
        local mins = TierMins()
        for _, r in ipairs(EG.dmMatRows) do
            local price = MatPrice(r.id)
            if price then
                local cost = price * (r.q or 1)
                r.price:SetText(ShortMoney(cost))
                r.price:SetTextColor(C_GOLD[1], C_GOLD[2], C_GOLD[3])
                local mn = mins[r.t]
                if r.chip and mn and mn > 0 then
                    local pct = (cost / mn - 1) * 100
                    local cheap = pct < 0.5
                    local v = math.floor(pct + 0.5)
                    local txt = cheap and "0%" or (v > 999 and "999+%" or format("+%d%%", v))
                    H.PaintSolidChip(r.chip, txt, cheap and C_DN or C_UP, nil, 12)
                elseif r.chip then
                    r.chip:Hide()
                end
            else
                r.price:SetText("—")
                r.price:SetTextColor(C_DIM[1], C_DIM[2], C_DIM[3])
                if r.chip then r.chip:Hide() end
            end
        end
    end
    EG.dmPaintPrices = PaintPrices

    local scanStat = MakeFS(tmSec, 12, C_DIM, "RIGHT")
    scanStat:SetPoint("RIGHT", tmSec, "RIGHT", 0, 0)
    scanStat:SetWordWrap(false)

    local function AgeStr(sec)
        if sec < 3600 then return format(L["%d 分钟前"], math.max(1, math.floor(sec / 60))) end
        if sec < 86400 then return format(L["%d 小时前"], math.floor(sec / 3600)) end
        return format(L["%d 天前"], math.floor(sec / 86400))
    end

    local function UpdateScan()
        local AB = ns.AuctionBridge
        local priced, tot = 0, 0
        for _, r in ipairs(EG.dmMatRows) do
            tot = tot + 1
            if MatPrice(r.id) then priced = priced + 1 end
        end
        local snap = AB and AB.FullScanSnapshotStatus and AB.FullScanSnapshotStatus()
        if snap and snap.status == "available" and snap.observedAt then
            local age = math.max(0, (time() - snap.observedAt))
            scanStat:SetText(format(L["拍卖行 %d/%d 有价 · 扫描于 %s"], priced, tot, AgeStr(age)))
            scanStat:SetTextColor(C_GREY[1], C_GREY[2], C_GREY[3])
        elseif snap and snap.status == "expired" then
            scanStat:SetText(L["拍卖行数据已过期，重新扫描一次"])
            scanStat:SetTextColor(C_WARN[1], C_WARN[2], C_WARN[3])
        else
            scanStat:SetText(format(L["拍卖行 %d/%d 有价 · 未扫描完整数据"], priced, tot))
            scanStat:SetTextColor(C_DIM[1], C_DIM[2], C_DIM[3])
        end
    end
    EG.dmUpdateScan = UpdateScan

    local function LayoutTicket()
        local ch = math.max(tcNeed, tNat)
        tc1:SetHeight(ch)
        tc3:SetHeight(ch)
        local nTier = #DM.TIERS
        local pitch = (ch - tc1.__hdr - BOT - 16) / (nTier - 1)
        if pitch < TROW then pitch = TROW end
        if pitch > 40 then pitch = 40 end
        for i, rs in ipairs(tRows) do
            local y = -tc1.__hdr - (i - 1) * pitch
            rs[1]:ClearAllPoints()
            rs[1]:SetPoint("TOPLEFT", tc1, "TOPLEFT", PAD, y)
            for k = 2, 4 do
                rs[k]:ClearAllPoints()
                rs[k]:SetPoint("TOPLEFT", tc1, "TOPLEFT", PAD + tcol * (k - 1), y + 2)
            end
        end
        local hy = -(ch + GAP)
        tmSec:ClearAllPoints()
        tmSec:SetPoint("TOPLEFT", tp, "TOPLEFT", 0, hy)
        local nRowB = math.ceil(#tmBlocks / 2)
        local bh, rowTop, totalH = {}, {}, 0
        for r = 1, nRowB do
            rowTop[r] = totalH
            local rh = 0
            for c = 1, 2 do
                local idx = (r - 1) * 2 + c
                local h = tmH[idx]
                if h and h > rh then rh = h end
            end
            if rh <= 0 then rh = matBH end
            for c = 1, 2 do bh[(r - 1) * 2 + c] = rh end
            totalH = totalH + rh + GAP
        end
        for i, b in ipairs(tmBlocks) do
            local col = (i - 1) % 2
            local rIdx = math.floor((i - 1) / 2) + 1
            local rh = bh[i] or matBH
            b:SetHeight(rh)
            local refs = tmRows[i]
            local n = refs and #refs or 0
            if n > 1 then
                local pitch = (rh - (PAD + BTN_H + GAP) - 22 - PAD) / (n - 1)
                if pitch < ROW_PITCH then pitch = ROW_PITCH end
                for k, rr in ipairs(refs) do
                    local y = -(PAD + BTN_H + GAP) - (k - 1) * pitch
                    rr.ico:ClearAllPoints()
                    rr.ico:SetPoint("TOPLEFT", b, "TOPLEFT", PAD, y + 2)
                    rr.qty:ClearAllPoints()
                    rr.qty:SetPoint("TOPRIGHT", b, "TOPRIGHT", -QTY_R, y + 2)
                    rr.tkv:ClearAllPoints()
                    rr.tkv:SetPoint("TOPRIGHT", b, "TOPRIGHT", -TK_R, y)
                    rr.pfs:ClearAllPoints()
                    rr.pfs:SetPoint("TOPRIGHT", b, "TOPRIGHT", -PRICE_R, y + 1)
                    rr.nfs:ClearAllPoints()
                    rr.nfs:SetPoint("TOPLEFT", b, "TOPLEFT", PAD + 18 + 4, y)
                    if rr.chip then
                        rr.chip:ClearAllPoints()
                        rr.chip:SetPoint("TOPRIGHT", b, "TOPRIGHT", -PAD, y)
                    end
                end
            end
            b:ClearAllPoints()
            b:SetPoint("TOPLEFT", tp, "TOPLEFT", col * (matW + GAP), hy - HDR_ROW - rowTop[rIdx])
        end
        tp.h = -hy + HDR_ROW + totalH - GAP + BOT
        tp:SetHeight(tp.h)
        if tp:IsShown() then
            child:SetHeight(tp.h)
            UpdateBar()
        end
    end

    local pz = NewPane("prize")
    local cols = 4
    local pcw = math.floor((CW - (cols - 1) * GAP) / cols)
    local function CostOf(id)
        for _, it in ipairs(DM.PRIZES) do
            if it.id == id then return it.cost, it.lvl end
        end
    end
    local zy = 0
    for _, grp in ipairs(DM.PRIZE_GROUPS) do
        zy = GroupHeader(pz, zy, grp.title, grp.sub, format(L["%d 件"], #grp.ids))
        local rows = math.ceil(#grp.ids / cols)
        for i, id in ipairs(grp.ids) do
            local cost, lvl = CostOf(id)
            local rx = ((i - 1) % cols) * (pcw + GAP)
            local ry = zy - math.floor((i - 1) / cols) * (LC_H + GAP)
            local meta = PartOf(id)
            if cost and cost >= 1200 then
                meta = (meta ~= "" and (meta .. " · ") or "") .. L["购55/穿60"]
            elseif lvl then
                meta = (meta ~= "" and (meta .. " · ") or "") .. L["需"] .. " " .. lvl .. L["级"]
            end
            LootCard(pz, rx, ry, pcw, id, meta, (cost or "?") .. " " .. L["张"])
        end
        zy = zy - rows * LC_H - (rows - 1) * GAP - GAP
    end

    local ncY = zy
    local ncLab, ncx, ncy = SplitCoord(L["吉瓦斯·格里加特 41.5,68.9"])
    local nc = NewCard(pz, 0, ncY, CW, L["怎么选"], ncLab, ncx, ncy)
    Bullets(nc, DM.PRIZE_NOTES, 14, 6)
    CloseCard(nc)
    pz.h = -ncY + nc:GetHeight() + BOT

    local dk = NewPane("deck")
    local dcw = math.floor((CW - GAP) / 2)
    local dstat = Put(dk, 0, 0, DM.DECK_STATUS, 14, C_WARN, CW)
    local dy = GroupHeader(dk, -FH(dstat, 14) - GAP,
        L["四套牌换四个饰品"], L["八张牌（A–8）合成一套"], format(L["%d 件"], #DM.DECKS))
    for i, d in ipairs(DM.DECKS) do
        local rx = ((i - 1) % 2) * (dcw + GAP)
        local ry = dy - math.floor((i - 1) / 2) * (LC_H + GAP)
        LootCard(dk, rx, ry, dcw, d.trinket, d.eff, d.key, C_GREY, d.deck)
    end
    local drows = math.ceil(#DM.DECKS / 2)
    dy = dy - drows * LC_H - (drows - 1) * GAP

    local dnote = Put(dk, 0, dy - GAP,
        L["四件都是 60 级饰品；牌不绑定、可以拍卖行买卖，合出来的饰品拾取绑定。教授在艾尔文 41.3,70.0 / 莫高雷 36.5,38.0。"],
        14, C_GREY, CW)
    dy = dy - GAP - FH(dnote, 14) - GAP

    local ac = NewCard(dk, 0, dy, CW, L["A 牌在哪掉"], L["2–8 是 45–60 亡灵与人型随机掉"])
    local AX_CARD, AX_DECK, AX_BOSS = PAD + 24, PAD + 148, PAD + 264
    local acy = -HDR
    for _, a in ipairs(DM.ACES) do
        local drops = a.drops or {}
        for i, dr in ipairs(drops) do
            if i == 1 then
                IconRef(ac, PAD, acy - 2, a.item, 18)
                LinkPut(ac, AX_CARD, acy, a.item, 14)
                LinkPut(ac, AX_DECK, acy, a.deck, 14)
            end
            Put(ac, AX_BOSS, acy, dr[1], 14, C_TEXT)
            PutR(ac, -PAD, acy + 2, dr[2], 12, C_GREY)
            acy = acy - ROW_PITCH
        end
        acy = acy - 2
    end
    ac.__cur = acy
    CloseCard(ac)
    dy = dy - ac:GetHeight() - GAP

    local dn = NewCard(dk, 0, dy, CW, L["怎么凑"])
    Bullets(dn, DM.DECK_NOTES, 14, 6)
    CloseCard(dn)
    dk.h = -dy + dn:GetHeight() + BOT

    local ft = NewPane("fortune")
    local fcLab, fcx, fcy = SplitCoord(L["42.1,69.0 · 两小时增益"])
    local fc = NewCard(ft, 0, 0, CW, L["塞格的占卜"], fcLab, fcx, fcy)
    local fhalf = math.floor((CW - 2 * PAD - GAP) / 2)
    local qy = -HDR
    for i, q in ipairs(DM.FORTUNE_Q) do
        local col = (i - 1) % 2
        local row = math.floor((i - 1) / 2)
        local x = PAD + col * (fhalf + GAP)
        local y = qy - row * 24
        Put(fc, x, y, q.n, 16, C_GOLD)
        Put(fc, x + 24, y + 2, q.a, 14, C_TEXT)
    end
    local qdiv = fc:CreateTexture(nil, "ARTWORK")
    qdiv:SetColorTexture(CDIV[1], CDIV[2], CDIV[3], 1)
    qdiv:SetSize(CW - 2 * PAD, 1)
    qdiv:SetPoint("TOPLEFT", fc, "TOPLEFT", PAD, qy - 2 * 24 - 4)
    local fy = qy - 2 * 24 - 4 - GAP - 2
    for i, f in ipairs(DM.FORTUNE) do
        local col = (i - 1) % 2
        local row = math.floor((i - 1) / 2)
        local x = PAD + col * (fhalf + GAP)
        local y = fy - row * 24
        Put(fc, x, y, f.name, 14, C_TEXT)
        Put(fc, x + 96, y, f.a, 14, C_GOLD)
        if f.b then Put(fc, x + 154, y + 2, L["或 "] .. f.b, 12, C_GREY) end
    end
    fc.__cur = fy - 4 * 24 - GAP
    local fnote = Para(fc, L["数字是第几个选项：先答第一问，再答第二问。答错只能等下个周期，所以进队之前先看清要哪个。"], 14, C_GREY, 0)
    CloseCard(fc)

    local py2 = -fc:GetHeight() - GAP
    local fn2 = NewCard(ft, 0, py2, CW, L["规矩与塔罗牌"])
    RichPara(fn2, function()
        return "· " .. L["增益持续两小时，登录满四小时可以再来一次，一次只能带一个。"]
    end, 14, 6)
    RichPara(fn2, function()
        return "· " .. L["占卜完还会给一张"] .. ItemRef(DM.FORTUNE_ITEM)
            .. L["，多数只是句子；带任务的只有下面四张："]
    end, 14, 8)
    for _, c in ipairs(DM.FORTUNE_CARDS) do
        local y = fn2.__cur
        IconRef(fn2, PAD + 8, y - 3, c.item, 18)
        LinkPut(fn2, PAD + 32, y, c.item, 14)
        Put(fn2, PAD + 178, y, "→", 14, C_GREY)
        QuestPut(fn2, PAD + 202, y, c.quest, 14)
        PutR(fn2, -PAD, y + 2, c.where or "", 12, C_GREY)
        fn2.__cur = y - 26
    end
    fn2.__cur = fn2.__cur - 2
    RichPara(fn2, function()
        return "· " .. L["四条任务 10 级可接，奖励神秘锁箱，开出来的东西随等级。"]
    end, 14, 6)
    RichPara(fn2, function()
        return "· " .. L["四张卡本身不绑定，可以在拍卖行买到，也可以拿去卖。"]
    end, 14, 0)
    CloseCard(fn2)
    ft.h = -py2 + fn2:GetHeight() + BOT

    local pt = NewPane("pet")
    Section(pt, 0, 0, L["宠物与隐藏任务"], L["都在营地，不用声望"])
    local bw = math.floor((CW - GAP) / 2)
    local petBlocks = {
        { t = L["弗里克 · 青蛙商人"], pos = L["营地到处跑"],
          d = L["满营地追青蛙的小鬼，抓到他就能买下面三件。木蛙盒一次只卖一个，补货大约二十分钟；树蛙盒和皮球不限量。"],
          w = L["三件都不绑定，可以挂拍卖行；木蛙盒最值得蹲，蹲到就是白捡。"],
          macro = true,
          items = { { id = DM.PET_ITEMS.wood, note = L["限 1 个 · 约 20 分钟补货"] },
                    { id = DM.PET_ITEMS.tree, note = L["不限量"] },
                    { id = DM.PET_ITEMS.ball, note = L["20 铜 · 能扔着玩"] } } },
        { t = L["莫尔娅 · 加布林"], pos = "43.3,70.3",
          d = L["隐藏任务，要先备两个黑铁啤酒杯。别先点莫尔娅本人，会白丢一个杯子。"],
          qid = DM.PET_ITEMS.quest,
          items = { { id = DM.PET_ITEMS.mug, note = L["×2 · 放在她脚边"] },
                    { id = DM.PET_ITEMS.egg, note = L["交完第二个杯子给"] },
                    { id = DM.PET_ITEMS.home, note = L["七天后用它召唤"] } },
          steps = { { L["① 放杯子"], L["右键一个放在她旁边，等手发光再松手"] },
                    { L["② 等蛙"], L["朱布布会跳过来吃，耐心等"] },
                    { L["③ 接任务"], L["她给任务，接"] },
                    { L["④ 交杯子"], L["交第二个杯子，拿到蛙卵"] },
                    { L["⑤ 等七天"], L["七天后用加布林的小窝召唤"] } },
          w = nil },
    }
    local bh = 0
    local bframes = {}
    for i, b in ipairs(petBlocks) do
        local f = Block(pt, (i - 1) * (bw + GAP), -HDR_ROW, bw, 10)
        BlockTitle(f, b.t, 14, C_WHITE)
        local hdrR = 0
        if b.macro then
            local mname = L["找弗里克"]
            local mw = math.max(72, TextW(L["创建宏"], 14) + 20)
            local mb = NewButton(f, L["创建宏"], mw, BTN_H, 14)
            mb:SetPoint("TOPRIGHT", f, "TOPRIGHT", -PAD, -PAD)
            mb:SetScript("OnEnter", function(self)
                GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
                GameTooltip:ClearLines()
                GameTooltip:AddLine(mname, 1, 0.82, 0.24, false)
                GameTooltip:AddLine(L["一键选中营地里到处跑的青蛙商人，点完把图标拖到动作条。"], 0.85, 0.85, 0.85, true)
                GameTooltip:AddLine("#showtooltip", 0.55, 0.85, 0.55)
                GameTooltip:AddLine("/cleartarget", 0.55, 0.85, 0.55)
                GameTooltip:AddLine("/target " .. L["弗里克"], 0.55, 0.85, 0.55)
                GameTooltip:AddLine("/stopmacro [noexists][dead]", 0.55, 0.85, 0.55)
                GameTooltip:AddLine("/ping [@target] Attack", 0.55, 0.85, 0.55)
                GameTooltip:Show()
            end)
            mb:SetScript("OnLeave", function() GameTooltip:Hide() end)
            mb:SetScript("OnClick", function()
                local icon = select(10, C_Item.GetItemInfo(DM.PET_ITEMS.wood)) or 133352
                local body = "#showtooltip\n/cleartarget\n/target " .. L["弗里克"]
                    .. "\n/stopmacro [noexists][dead]\n/ping [@target] Attack"
                MakeMacro(mname, body, icon)
                ns.PlaySound(1)
            end)
            hdrR = mw + GAP
        end
        local plab, pmx, pmy = SplitCoord(b.pos)
        if pmx then
            local pmb = MapBtn(f, pmx, pmy)
            pmb:SetPoint("TOPRIGHT", f, "TOPRIGHT", -PAD - hdrR, -PAD)
            BtnSide(f, pmb, plab)
        elseif plab ~= "" then
            RowSide(f, plab, -PAD - hdrR)
        end
        local body = Put(f, PAD, -(PAD + BTN_H + GAP), b.d, 14, C_TEXT, bw - 2 * PAD)
        local cy = -(PAD + BTN_H + GAP) - FH(body, 14) - 4
        if b.qid then
            local lab = Put(f, PAD, cy, L["任务"], 14, C_GREY)
            QuestPut(f, PAD + (lab:GetStringWidth() or 28) + 6, cy, b.qid, 14)
            cy = cy - 22
        end
        for _, it in ipairs(b.items or {}) do
            IconRef(f, PAD, cy - 2, it.id, 18)
            LinkPut(f, PAD + 24, cy, it.id, 14)
            PutR(f, -PAD, cy + 2, it.note, 12, C_GREY)
            cy = cy - 24
        end
        for _, st in ipairs(b.steps or {}) do
            Put(f, PAD, cy, st[1], 14, C_GOLD)
            Put(f, PAD + 76, cy + 2, st[2], 12, C_GREY, bw - PAD - 76 - PAD)
            cy = cy - 22
        end
        cy = cy + 2
        if b.w then
            local wf = Put(f, PAD, cy - 4, b.w, 14, C_WARN, bw - 2 * PAD)
            cy = cy - 4 - FH(wf, 14)
        end
        local h = -cy + PAD
        if h > bh then bh = h end
        bframes[i] = f
    end
    for _, f in ipairs(bframes) do f:SetHeight(bh) end
    local pfoot = Put(pt, 0, -HDR_ROW - bh - GAP,
        L["弗里克卖的东西不绑定，可以挂拍卖行；他会跑到闪金镇卫兵附近，部落去抓的时候别顺手把卫兵惹了。"], 14, C_GREY, CW)
    pt.h = HDR_ROW + bh + GAP + FH(pfoot, 14) + BOT

    local gm = NewPane("game")
    Section(gm, 0, 0, L["小游戏"], L["经典版不给券，也不给声望"])
    local gameBlocks = {
        { t = L["人肉大炮"], pos = L["玛克希玛 44.6,70.3"],
          d = L["点炮台把人轰上天，飞向营地南边的水域靶子；空中右键点掉「魔力之翼」开始下落，落进水里才安全，打偏就是摔死。进炮台前先把装备脱了，省一笔修理费。落地要自己跑回来，没有传送。"],
          w = L["雷霆崖也有一台，在贸易区与补给区之间的主台阶上，插着暗月旗子。"],
          rows = { { L["艾尔文"], L["河上，营地对面的水域"] },
                   { L["莫高雷"], L["血蹄村外"] } } },
        { t = L["坦克大战"], pos = L["营地围栏边"],
          d = L["围栏边带金边的小铁箱就是控制台，点一下召唤遥控坦克，四个技能出现在动作条上方，跟别人的坦克对轰。100 血 100 蓝，五分钟一场。"],
          rows = { { L["加农炮"], L["18–22 伤害 · 4 秒"] },
                   { L["迫击炮"], L["35–45 · 落点 25 码 · 5 秒"] },
                   { L["护盾发生器"], L["吸收 50 点 · 15 秒"] },
                   { L["氮气加速"], L["移速 +50% · 每秒 10 法力"] } } },
    }
    local gh = 0
    local gframes = {}
    for i, b in ipairs(gameBlocks) do
        local f = Block(gm, (i - 1) * (bw + GAP), -HDR_ROW, bw, 10)
        BlockTitle(f, b.t, 14, C_WHITE)
        local glab, gmx, gmy = SplitCoord(b.pos)
        if gmx then
            local gmb = MapBtn(f, gmx, gmy)
            gmb:SetPoint("TOPRIGHT", f, "TOPRIGHT", -PAD, -PAD)
            BtnSide(f, gmb, glab)
        elseif glab ~= "" then
            RowSide(f, glab, -PAD)
        end
        local body = Put(f, PAD, -(PAD + BTN_H + GAP), b.d, 14, C_TEXT, bw - 2 * PAD)
        local cy = -(PAD + BTN_H + GAP) - FH(body, 14) - 6
        local rows = b.rows or {}
        if #rows > 0 then
            local lw = 0
            for _, r in ipairs(rows) do
                local w = TW(r[1], 14)
                if w > lw then lw = w end
            end
            local rx = PAD + lw + 20
            local rw = bw - rx - PAD
            for _, r in ipairs(rows) do
                local v1 = type(r[1]) == "function" and r[1]() or r[1]
                local v2 = type(r[2]) == "function" and r[2]() or r[2]
                if type(r[1]) == "function" then
                    RichPut(f, PAD, cy, r[1], 14, C_GOLD)
                else
                    Put(f, PAD, cy, v1, 14, C_GOLD)
                end
                if type(r[2]) == "function" then
                    RichPut(f, rx, cy + 2, r[2], 12, C_GREY, rw)
                else
                    Put(f, rx, cy + 2, v2, 12, C_GREY, rw)
                end
                cy = cy - 22
            end
            cy = cy + 4
        end
        if b.w then
            local wf = Put(f, PAD, cy - 4, b.w, 14, C_WARN, bw - 2 * PAD)
            cy = cy - 4 - FH(wf, 14)
        end
        local h = -cy + PAD
        if h > gh then gh = h end
        gframes[i] = f
    end
    for _, f in ipairs(gframes) do f:SetHeight(gh) end
    gm.h = HDR_ROW + gh + BOT

    local function Recalc()
        local want = tonumber(EG.dmWant:GetText()) or 50
        if want < 1 then want = 1 end
        if want > 5000 then want = 5000 end
        local lvl = UnitLevel("player") or 1
        local rep = MyRep()
        local avail = AvailAt(rep, lvl)
        local names = {}
        for _, t in ipairs(avail) do names[#names + 1] = RING[t] end

        local mt = MaxTickets(rep, lvl)
        EG.dmBudget:SetText(format(L["上限 %d 张"], mt))
        local infoW = tcW - PAD - infoX - (EG.dmBudget:GetStringWidth() or 90) - GAP
        DG.ClipTo(EG.dmInfo, L["等级"] .. " " .. lvl .. " · " .. L["声望"] .. " " .. rep
            .. "（" .. RepBand(rep) .. "）· " .. L["能交"] .. " "
            .. (#names > 0 and table.concat(names, " ") or L["已封顶"]), infoW)

        for i = 1, 5 do EG.dmRows[i]:Hide() end

        local rows, total, res, plan = 0, 0, nil, {}
        if mt > 0 then
            res = Solve(rep, math.min(want, mt), lvl)
        end
        if res then
            for t = 1, 5 do
                local n = res.cnt[t]
                if n > 0 then
                    local o = BestOfTier(t)
                    rows = rows + 1
                    local r = EG.dmRows[rows]
                    r:ClearAllPoints()
                    r:SetPoint("TOPLEFT", tc3, "TOPLEFT", PAD, ROW_Y0 - (rows - 1) * ROW_PITCH)
                    if o then
                        r.icon:SetTexture(ItemTex(o.id))
                        r.icon:Show()
                        Ring(r.icon, o.id)
                        DG.ClipTo(r.name, DG.ItemName(o.id) .. "  ×" .. o.q,
                            tcW - 2 * PAD - 26 - COST_W - GAP - 92)
                        r.right:SetText(n .. " " .. L["次"] .. " · "
                            .. Gold(n * DM.TIERS[t].tk) .. " " .. L["张"])
                        r.cost:SetText(MoneyStr(n * o.c))
                        r.cost:SetTextColor(C_GOLD[1], C_GOLD[2], C_GOLD[3])
                        total = total + n * o.c
                        plan[#plan + 1] = { id = o.id, q = o.q, n = n }
                    else
                        r.icon:Hide()
                        r.name:SetText(L["缺少价格"])
                        r.right:SetText(n .. " " .. L["次"])
                        r.cost:SetText("—")
                        r.cost:SetTextColor(C_DIM[1], C_DIM[2], C_DIM[3])
                    end
                    r:Show()
                end
            end
        end

        EG.dmPlan = plan
        local got = res and res.tickets or 0
        local short = want - got
        local rowsBottom = rows > 0 and (ROW_Y0 - (rows - 1) * ROW_PITCH - ROW_H) or ROW_Y0

        if mt <= 0 then
            EG.dmSum:SetText("")
            EG.dmNote:SetText(L["现在一档都交不了，先升级或等下一轮。"])
        elseif not res then
            EG.dmSum:SetText("")
            local priced = false
            for _, t in ipairs(avail) do
                if BestOfTier(t) then priced = true break end
            end
            EG.dmNote:SetText(priced and L["算不出方案。"] or L["这些档次在拍卖行都没有价格，先扫描一次拍卖行再来算。"])
        else
            EG.dmSum:SetText(L["合计"] .. " " .. MoneyStr(total))
            local head = got .. " " .. L["张"]
                .. (short > 0 and ("（" .. L["还差"] .. " " .. short .. " " .. L["张"] .. "）") or "")
            if short > 0 then
                EG.dmNote:SetText(head .. " · " .. L["交满只到"] .. " " .. mt .. " " .. L["张"]
                    .. "；" .. L["声望"] .. " " .. DM.MORE_AT
                    .. " " .. L["后可改交「更多…」任务（20 张/次，不涨声望）。"])
            else
                EG.dmNote:SetText(head .. " · " .. L["声望"] .. " " .. rep .. " → " .. (rep + 100 * res.turns)
                    .. "（" .. res.turns .. " " .. L["次"] .. "）")
            end
        end

        local sumW = EG.dmSum:GetStringWidth() or 0
        local noteW = tcW - 2 * PAD - (sumW > 0 and (sumW + GAP * 2) or 0)
        if noteW < 80 then noteW = 80 end
        EG.dmNote:SetWidth(noteW)

        local noteH = FH(EG.dmNote, 12)
        local lineH = noteH > 16 and noteH or 16
        local need = -rowsBottom + GAP + lineH + BOT
        tcNeed = need
        tc3:SetHeight(need)
        LayoutTicket()
    end

    eb:SetScript("OnTextChanged", function() Recalc() end)
    eb:SetScript("OnEnterPressed", function(self) self:ClearFocus() Recalc() end)
    eb:SetScript("OnEscapePressed", function(self) self:ClearFocus() end)
    EG.DarkmoonRecalc = Recalc

    local function RefreshNames()
        for _, r in ipairs(EG.dmRefBuilders or {}) do
            r.fs:SetText(r.build())
        end
        if EG.DarkmoonRecalc then pcall(EG.DarkmoonRecalc) end
    end
    EG.dmRefBuilders = refBuilders
    EG.dmRefreshNames = RefreshNames
    C_Timer.After(0.5, function() pcall(RefreshNames) end)

    if not EG.dmNameWatch then
        local w = CreateFrame("Frame")
        w:RegisterEvent("GET_ITEM_INFO_RECEIVED")
        w:SetScript("OnEvent", function()
            if EG.dmNameTimer then return end
            EG.dmNameTimer = true
            C_Timer.After(0.25, function()
                EG.dmNameTimer = nil
                if EG.dmRefreshNames then pcall(EG.dmRefreshNames) end
            end)
        end)
        EG.dmNameWatch = w
    end

    if not EG.dmCalWatch then
        local w = CreateFrame("Frame")
        w:RegisterEvent("CALENDAR_UPDATE_EVENT_LIST")
        w:RegisterEvent("CALENDAR_UPDATE_EVENT")
        w:RegisterEvent("PLAYER_ENTERING_WORLD")
        w:RegisterEvent("ZONE_CHANGED_NEW_AREA")
        w:SetScript("OnEvent", function()
            if EG.dmCalTimer then return end
            EG.dmCalTimer = true
            C_Timer.After(1, function()
                EG.dmCalTimer = nil
                if EG.dmCalScan then pcall(EG.dmCalScan) end
                if EG.dmCalRefresh then pcall(EG.dmCalRefresh) end
            end)
        end)
        EG.dmCalWatch = w
    end
    if not EG.dmCalTicker then
        EG.dmCalTicker = C_Timer.NewTicker(60, function()
            if EG.dmCalRefresh and EG.dmFrame and EG.dmFrame:IsShown() then
                pcall(EG.dmCalRefresh)
            end
        end)
    end

    PaintPrices()
    UpdateScan()
    LayoutTicket()

    if ns.AuctionBridge and ns.AuctionBridge.OnChanged then
        ns.AuctionBridge.OnChanged(function()
            if EG.dmScanTimer then return end
            EG.dmScanTimer = true
            C_Timer.After(0.4, function()
                EG.dmScanTimer = nil
                if EG.dmUpdateScan then pcall(EG.dmUpdateScan) end
                if EG.dmPaintPrices then pcall(EG.dmPaintPrices) end
                if EG.DarkmoonRecalc then pcall(EG.DarkmoonRecalc) end
            end)
        end)
    end

    if ns.ProfRouteAuto and ns.ProfRouteAuto.OnPricesChanged then
        ns.ProfRouteAuto.OnPricesChanged(function()
            if not EG.dmPaintPrices then return end
            pcall(EG.dmPaintPrices)
            if EG.DarkmoonRecalc then pcall(EG.DarkmoonRecalc) end
        end)
    end

    function EG.DarkmoonSetTab(k)
        local db = ns.ExploreDB()
        db.explore = db.explore or {}
        db.explore.dmTab = k
        for key, p in pairs(EG.dmPanes) do p:SetShown(key == k) end
        for key, bt in pairs(EG.dmTabBtns) do SetButtonSelected(bt, key == k) end
        local pane = EG.dmPanes[k]
        child:SetHeight(pane and pane.h or 10)
        sc:SetVerticalScroll(0)
        UpdateBar()
        if k == "ticket" then
            if EG.dmRefreshNames then pcall(EG.dmRefreshNames) end
            if EG.dmPaintPrices then pcall(EG.dmPaintPrices) end
            if EG.dmUpdateScan then pcall(EG.dmUpdateScan) end
            pcall(Recalc)
        elseif k == "overview" then
            if EG.dmCalScan then pcall(EG.dmCalScan) end
            if EG.dmCalRefresh then pcall(EG.dmCalRefresh) end
            if EG.dmTicketVal then
                EG.dmTicketVal:SetText(tostring(MyTickets()) .. " " .. L["张"])
            end
        end
    end

    local cur = (ns.ExploreDB().explore or {}).dmTab
    if cur ~= "overview" and cur ~= "ticket" and cur ~= "prize" and cur ~= "fortune"
        and cur ~= "deck" and cur ~= "pet" and cur ~= "game" then
        cur = "overview"
    end
    EG.DarkmoonSetTab(cur)
    root:SetFrameLevel(math.max(root:GetFrameLevel() or 0, (EG.cardLvl or 0) + 3))
end

ns.ExploreDarkmoonBuild = Build
