local _, ns = ...

local L = ns.L or function(k) return k end
local C = {}
ns.CampWatch = C

local NEARBY = 1283391
local BOOSTED = 1229451
local RENEW_SECS = 600
local TENT_ITEM = 288185
local TENT_ICON = 4624631

local TEXTS = {
    L["大佬，打扰一下，请问可以蹭下帐篷吗？"],
    L["请问帐篷方便蹭一下吗？"],
    L["求蹭帐篷，感谢大佬！"],
}

local function CFG()
    local Z = ns.ZoneHint
    if Z and Z.CFG then
        local ok, c = pcall(Z.CFG)
        if ok and type(c) == "table" then return c end
    end
    return {}
end

local function Now()
    if type(time) == "function" then
        local ok, t = pcall(time)
        if ok and type(t) == "number" then return t end
    end
    return (GetTime and GetTime()) or 0
end

local function Sealed(v)
    if type(issecretvalue) ~= "function" then return false end
    local ok, s = pcall(issecretvalue, v)
    return ok and s == true
end

local function SpellText(id)
    local f = C_Spell and C_Spell.GetSpellInfo
    if not f then return nil, nil end
    local ok, si = pcall(f, id)
    if ok and type(si) == "table" then return si.name, si.iconID end
    return nil, nil
end

local function TentIcon()
    local f = C_Item and C_Item.GetItemIconByID
    if f then
        local ok, tex = pcall(f, TENT_ITEM)
        if ok and tex then return tex end
    end
    return TENT_ICON
end

local function SpellIcon(id, fallback)
    local f = C_Spell and C_Spell.GetSpellTexture
    if f then
        local ok, tex = pcall(f, id)
        if ok and tex then return tex end
    end
    local _, ic = SpellText(id)
    return ic or fallback
end

local function Has(unit, id, name, bucket)
    if not (unit and C_UnitAuras and C_UnitAuras.GetAuraDataByIndex) then return false end
    for i = 1, 40 do
        local ok, a = pcall(C_UnitAuras.GetAuraDataByIndex, unit, i, bucket)
        if not ok or not a then break end
        if (not Sealed(a.spellId) and a.spellId == id)
            or (name and not Sealed(a.name) and a.name == name) then
            return true, a
        end
    end
    return false, nil
end

function C.Available()
    if not ns.IsForever then return false end
    local nm = SpellText(NEARBY)
    return nm ~= nil
end

function C.State()
    if not C.Available() then return nil end
    local nn = SpellText(NEARBY)
    local bn = SpellText(BOOSTED)
    local near = Has("player", NEARBY, nn, "HELPFUL")
    local boosted, aura = Has("player", BOOSTED, bn, "HARMFUL")
    if not boosted then boosted, aura = Has("player", BOOSTED, bn, "HELPFUL") end
    local rem
    if boosted and type(aura) == "table" then
        local exp = aura.expirationTime
        if not Sealed(exp) and type(exp) == "number" and exp > 0 then
            rem = math.max(0, exp - ((GetTime and GetTime()) or 0))
        end
    end
    return { near = near, boosted = boosted, rem = rem }
end

local function Dead()
    if type(UnitIsDeadOrGhost) ~= "function" then return false end
    local ok, v = pcall(UnitIsDeadOrGhost, "player")
    return ok and v == true
end

local ownToy = false

local function OwnTent()
    if ownToy then return true end
    if type(PlayerHasToy) == "function" then
        local ok, has = pcall(PlayerHasToy, TENT_ITEM)
        if ok and has == true then
            ownToy = true
            return true
        end
    end
    local cnt = C_Item and C_Item.GetItemCount
    if cnt then
        local ok2, n = pcall(cnt, TENT_ITEM)
        if ok2 and type(n) == "number" and n > 0 then return true end
    end
    return false
end

function C.Own()
    return OwnTent()
end

local function Left(cd)
    if type(cd) ~= "table" then return nil end
    local st, du = cd.startTime, cd.duration
    if type(st) ~= "number" or type(du) ~= "number" or du <= 0 then return nil end
    local now = (GetTime and GetTime()) or 0
    local v = st + du - now
    if v < 0 then v = 0 end
    return v
end

local function ToyCd()
    local f = C_Item and C_Item.GetItemCooldown
    if f then
        local ok, cd = pcall(f, TENT_ITEM)
        if ok then
            local v = Left(cd)
            if v then return v end
        end
    end
    local gs = C_Item and C_Item.GetItemSpell
    local sc = C_Spell and C_Spell.GetSpellCooldown
    if gs and sc then
        local ok1, _, sid = pcall(gs, TENT_ITEM)
        if ok1 and type(sid) == "number" then
            local ok2, cd2 = pcall(sc, sid)
            if ok2 then
                local v = Left(cd2)
                if v then return v end
            end
        end
    end
    return 0
end

function C.TentCd()
    return ToyCd()
end

local function CdText(rem)
    if not rem or rem <= 0 then return L["冷却已就绪"] end
    local m = math.ceil(rem / 60)
    if m < 1 then m = 1 end
    return string.format(L["冷却 %d 分钟"], m)
end

function C.Rows()
    local st = C.State()
    if not st or Dead() then return nil end
    local c = CFG()
    local out = {}
    if c.camp ~= false and st.near and not st.boosted then
        local own = OwnTent()
        local cd = own and (C.TentCd() or 0) or 0
        local row = {
            id = NEARBY, base = NEARBY, itipid = NEARBY,
            ikey = "camp:" .. NEARBY, ikind = "camp",
            name = own and L["帐篷"] or L["露营"],
            note = L["双倍经验"],
            icon = own and TentIcon() or SpellIcon(NEARBY, 7808147),
            sub = own and CdText(C.TentCd()) or L["营火在附近 · 缺少强化休息"],
            desc = L["在营火旁坐下或用帐篷休息，可获得强化休息：经验翻倍，一段时间内只有一次"],
        }
        if own and cd <= 0 then
            row.useMacro = "/use item:" .. TENT_ITEM
            row.actLabel = L["使用"]
            row.actTip = L["左键使用帐篷"]
        else
            row.useMacro = C.SitCmd()
            row.actLabel = L["坐下"]
            row.actTip = L["左键坐下（同 /sit）"]
        end
        out[#out + 1] = row
    end
    if c.renew ~= false and st.boosted and st.rem and st.rem <= RENEW_SECS then
        local mins = math.floor(st.rem / 60)
        if mins < 1 then mins = 1 end
        out[#out + 1] = {
            id = BOOSTED, base = BOOSTED, itipid = BOOSTED,
            ikey = "campren:" .. BOOSTED, ikind = "campren",
            name = L["强化休息即将到期"],
            icon = SpellIcon(BOOSTED, 1001982),
            sub = string.format(L["还剩 %d 分钟 · 回营地续一次"], mins),
            desc = L["强化休息到期后经验加成消失，回营火旁再休息一次即可续上"],
        }
    end
    if #out == 0 then return nil end
    return out
end

local TENT_IDS = { [277968] = true }
local TENT_NAMES = { ["资深冒险者的探险帐篷"] = true, ["資深冒險者的探險帳篷"] = true }

local function UnitCid(u)
    if type(UnitCreatureID) ~= "function" then return nil end
    local ok, id = pcall(UnitCreatureID, u)
    if ok and type(id) == "number" then return id end
    return nil
end

local function IsTent(u)
    if not (u and UnitExists(u)) then return false end
    local id = UnitCid(u)
    if id and TENT_IDS[id] then return true end
    local ok, hit = pcall(function()
        local nm = UnitName(u)
        return nm ~= nil and TENT_NAMES[nm] == true
    end)
    return ok and hit == true
end

function C.TentUnit()
    if type(IsInInstance) == "function" then
        local ok, v = pcall(IsInInstance)
        if ok and v then return nil end
    end
    if IsTent("target") then return "target" end
    return nil
end

local function Self(name)
    local me = UnitName("player")
    if not (me and name) then return false end
    if name == me then return true end
    local short = name:gsub("|c%x%x%x%x%x%x%x%x", ""):gsub("|r", "")
    short = short:gsub("%s*%-%s*.*$", ""):gsub("%s+.*$", ""):gsub("^%s+", "")
    if short == me then return true end
    if Ambiguate then
        local ok, s = pcall(Ambiguate, name, "short")
        if ok and s == me then return true end
        local ok2, s2 = pcall(Ambiguate, short, "short")
        if ok2 and s2 == me then return true end
    end
    return false
end

local function Plain(t)
    if type(t) ~= "string" then return nil end
    return (t:gsub("|c%x%x%x%x%x%x%x%x", ""):gsub("|r", ""))
end

local function OwnerOf(u)
    local f = C_TooltipInfo and C_TooltipInfo.GetUnit
    if not f then return nil end
    local ok, d = pcall(f, u)
    if not ok or type(d) ~= "table" or type(d.lines) ~= "table" then return nil end
    for i = 1, #d.lines do
        local t = Plain(d.lines[i].leftText)
        if t then
            local n = t:match("^由(.+)放置$") or t:match("^[Pp]laced by[: ]+(.+)$")
            if n then
                n = n:gsub("^%s+", ""):gsub("%s+$", "")
                if n ~= "" then return n end
            end
        end
    end
    return nil
end

function C.Owner()
    local u = C.TentUnit()
    if not u then return nil end
    return OwnerOf(u)
end

local sitCmd

function C.SitCmd()
    if sitCmd then return sitCmd end
    sitCmd = "/sit"
    for i = 1, 1000 do
        if _G["EMOTE" .. i .. "_TOKEN"] == "SIT" then
            sitCmd = _G["EMOTE" .. i .. "_CMD1"] or sitCmd
            break
        end
    end
    return sitCmd
end

function C.Card()
    local c = CFG()
    if c.tent == false then return nil end
    local st = C.State()
    if st and st.boosted then return nil end
    local tu = C.TentUnit()
    if not tu then return nil end
    if OwnTent() and c.tentOwn ~= false then return nil end
    local owner = OwnerOf(tu)
    if not owner or Self(owner) then return nil end
    local tname = UnitName(tu)
    return {
        kind = "tent", n = 1, noChip = true,
        icon = TentIcon(),
        title = L["蹭帐篷"],
        name = tname,
        text = string.format(L["由 %s 放置"], "|cffffffff" .. owner .. "|r"),
        btn = L["私聊"],
        onClick = function() C.Ask(owner) end,
        btn2 = L["附近喊话"],
        onClick2 = function() C.Say(owner) end,
        hint2 = L["左键用说频道喊一句"],
        btn3 = L["坐下"],
        hint3 = L["左键坐下（同 /sit）"],
        onCard = true,
        cardHint = L["点击卡片坐下或起身（同 /sit）"],
    }
end

function C.Texts()
    return TEXTS
end

function C.AskText()
    local i = tonumber(CFG().tentText) or 1
    return TEXTS[i] or TEXTS[1]
end

function C.Asked(name)
    if not name or name == "" then return nil, nil end
    local c = CFG()
    local t = type(c.asked) == "table" and c.asked[name]
    local stamp, ch
    if type(t) == "number" then
        stamp = t
    elseif type(t) == "table" then
        stamp = t.t
        ch = t.ch
    end
    if type(stamp) ~= "number" then return nil, nil end
    local d = Now() - stamp
    if d < 0 then d = 0 end
    return math.floor(d / 60), ch or "w"
end

function C.MarkAsked(name, ch)
    if not name or name == "" then return false end
    local c = CFG()
    if type(c.asked) ~= "table" then c.asked = {} end
    c.asked[name] = { t = Now(), ch = ch or "w" }
    return true
end

local armed

local function Arm(name, ch)
    armed = { name = name, ch = ch, text = C.AskText(), untilT = Now() + 300 }
end

local function Hits(msg, want)
    if msg == want then return true end
    if #msg >= 8 and msg:find(want, 1, true) then return true end
    if #want >= 8 and want:find(msg, 1, true) then return true end
    return false
end

local chatWatch = CreateFrame("Frame")
chatWatch:RegisterEvent("CHAT_MSG_SAY")
chatWatch:RegisterEvent("CHAT_MSG_WHISPER_INFORM")
chatWatch:SetScript("OnEvent", function(_, event, msg, who)
    C.OnChat(event, msg, who)
end)

function C.OnChat(event, msg, who)
    local a = armed
    if not a then return false end
    if Now() > a.untilT then
        armed = nil
        return false
    end
    if type(msg) ~= "string" or msg == "" then return false end
    if type(who) == "string" and who ~= "" and type(UnitName) == "function" then
        local me = UnitName("player")
        if me then
            local base = who
            local cut = base:find("-", 1, true)
            if cut then base = base:sub(1, cut - 1) end
            if base ~= me then return false end
        end
    end
    if not Hits(msg, a.text) then return false end
    C.MarkAsked(a.name, a.ch)
    armed = nil
    if ns.ZoneOrb and ns.ZoneOrb.Refresh then pcall(ns.ZoneOrb.Refresh) end
    return true
end

function C.AskTarget(name)
    local n = Plain(name)
    if type(n) ~= "string" then return nil end
    n = n:gsub("^%s+", ""):gsub("%s+$", "")
    if n == "" then return nil end
    return n
end

local function SendAsk(who)
    if type(SendChatMessage) ~= "function" then return false end
    local ok = pcall(SendChatMessage, C.AskText(), "WHISPER", nil, who)
    if not ok then return false end
    return true
end

function C.Ask(name)
    local who = C.AskTarget(name)
    if not who then return false end
    if not (ChatFrame_OpenChat and DEFAULT_CHAT_FRAME) then return false end
    if who:find("%s") then
        if not SendAsk(who) then return false end
        Arm(name, "w")
        return true
    end
    ChatFrame_OpenChat("/w " .. who .. " " .. C.AskText(), DEFAULT_CHAT_FRAME)
    Arm(name, "w")
    return true
end

function C.Say(name)
    if not (ChatFrame_OpenChat and DEFAULT_CHAT_FRAME) then return false end
    ChatFrame_OpenChat("/say " .. C.AskText(), DEFAULT_CHAT_FRAME)
    Arm(name, "s")
    return true
end
