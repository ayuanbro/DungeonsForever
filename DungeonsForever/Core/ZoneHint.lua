local _, ns = ...

local L = ns.L or function(k) return k end
local Z = {}
ns.ZoneHint = Z

local CITIES = {
    ["暴风城"] = true, ["铁炉堡"] = true, ["达纳苏斯"] = true, ["埃索达"] = true,
    ["奥格瑞玛"] = true, ["雷霆崖"] = true, ["幽暗城"] = true, ["银月城"] = true,
    ["沙塔斯"] = true, ["沙塔斯城"] = true, ["达拉然"] = true,
    ["Stormwind"] = true, ["Ironforge"] = true, ["Darnassus"] = true, ["Exodar"] = true,
    ["Orgrimmar"] = true, ["Thunder Bluff"] = true, ["Undercity"] = true,
    ["Silvermoon"] = true, ["Shattrath"] = true, ["Dalaran"] = true,
}

local DELAYS = { 0.5, 1.5, 3, 6 }

local QDISC = "Interface\\AddOns\\DungeonsForever\\Media\\Common\\CheckDisc"
local OV_LEGEND = {
    done   = { col = { 0.25, 0.85, 0.35, 1 }, sym = "Interface\\AddOns\\DungeonsForever\\Media\\Common\\CheckMark",        ink = { 0.043, 0.239, 0.102 } },
    ready  = { col = { 0.15, 0.82, 0.78, 1 }, sym = "Interface\\AddOns\\DungeonsForever\\Media\\icon\\QUEST\\QMarkTurnIn",  ink = { 0.020, 0.180, 0.172 } },
    active = { col = { 1, 0.82, 0, 1 },       sym = "Interface\\AddOns\\DungeonsForever\\Media\\icon\\QUEST\\QMarkAsk",     ink = { 0.227, 0.165, 0 } },
    todo   = { col = { 0.55, 0.55, 0.55, 1 }, sym = "Interface\\AddOns\\DungeonsForever\\Media\\icon\\QUEST\\QMarkExcl",    ink = { 0.102, 0.102, 0.102 } },
    rep    = { col = { 0.62, 0.50, 0.86, 1 }, sym = "Interface\\AddOns\\DungeonsForever\\Media\\icon\\QUEST\\QMarkAsk",     ink = { 0.18, 0.14, 0.26 } },
}
local OV_KEY = { done = "DONE", ready = "READY", active = "ACT", todo = "TODO", rep = "REP" }

local function OVDiscCol(DG, st)
    local k = OV_KEY[st]
    if DG and k and DG["Q_OV_" .. k] then
        local c = DG["Q_OV_" .. k]
        return { c[1], c[2], c[3] }
    end
    local e = OV_LEGEND[st] or OV_LEGEND.todo
    return { e.col[1], e.col[2], e.col[3] }
end

local function CFG()
    local db = ns.DB()
    db.ui.zoneHint = db.ui.zoneHint or {}
    local c = db.ui.zoneHint
    if c.on == nil then c.on = true end
    if c.book == nil then c.book = true end
    if c.bag == nil then c.bag = true end
    if c.torch == nil then c.torch = true end
    if c.banner == nil then c.banner = true end
    if c.quest == nil then c.quest = true end
    if c.qtDefault ~= 2 then
        c.qtDefault = 2
        c.questTaken = true
    end
    if c.questTaken == nil then c.questTaken = true end
    if c.questGrey == nil then c.questGrey = true end
    if c.spell == nil then c.spell = true end
    if c.talent == nil then c.talent = true end
    if c.food == nil then c.food = true end
    if tonumber(c.preferFood) == nil then c.preferFood = 0 end
    if c.rested == nil then c.rested = true end
    if c.camp == nil then c.camp = true end
    if c.renew == nil then c.renew = true end
    if c.tent == nil then c.tent = true end
    if c.tentOwn == nil then c.tentOwn = true end
    if tonumber(c.tentText) == nil then c.tentText = 1 end
    if c.carrot == nil then c.carrot = true end
    if c.carrot == false and c.carrotAuto == nil then c.carrotAuto = false; c.carrot = true end
    if c.carrotAuto == nil then c.carrotAuto = true end
    if c.voice == nil then c.voice = false end
    if c.voiceInit ~= 2 then
        c.voiceInit = 2
        c.voice = false
    end
    if c.foodVoice == nil then c.foodVoice = true end
    if c.restedVoice == nil then c.restedVoice = true end
    if c.turnin == nil then c.turnin = true end
    if c.keyitem == nil then c.keyitem = true end
    if c.profcd == nil then c.profcd = true end
    if c.onlyTodo == nil then c.onlyTodo = false end
    if c.noZonePopup == nil then c.noZonePopup = true end
    if c.mode == nil then c.mode = "auto" end
    if c.dur == nil then c.dur = 12 end
    if c.icon == nil then c.icon = 32 end
    if type(c.blacklist) ~= "table" then c.blacklist = {} end
    if type(c.asked) ~= "table" then c.asked = {} end
    if type(c.ignore) ~= "table" then c.ignore = {} end
    return c
end
Z.CFG = CFG

local function NextSeq()
    local c = CFG()
    c.seq = (tonumber(c.seq) or 0) + 1
    return c.seq
end

local function Trim(s)
    if type(s) ~= "string" then return "" end
    return (s:gsub("^%s+", ""):gsub("%s+$", ""))
end

local function SameName(a, b)
    a, b = Trim(a), Trim(b)
    if a == "" or b == "" then return false end
    if a == b then return true end
    a = a:gsub("[%s　]", "")
    b = b:gsub("[%s　]", "")
    return a == b
end
Z.SameName = SameName

local function ItemKey(kind, id)
    if not kind or id == nil then return nil end
    return kind .. ":" .. tostring(id)
end
Z.ItemKey = ItemKey

function Z.IsIgnored(key)
    if not key then return false end
    return CFG().ignore[key] ~= nil
end

local function NotifyList()
    local B = ns.ZoneHintList
    if type(B) == "table" and type(B.Notify) == "function" then
        pcall(B.Notify)
    end
end

function Z.IgnoreItem(kind, id, label)
    local key = ItemKey(kind, id)
    if not key then return nil end
    CFG().ignore[key] = {
        kind = kind,
        id = id,
        label = label or key,
        seq = NextSeq(),
    }
    Z.IgnoreRev = (Z.IgnoreRev or 0) + 1
    NotifyList()
    return key
end

function Z.UnignoreItem(key)
    if key then
        CFG().ignore[key] = nil
        Z.IgnoreRev = (Z.IgnoreRev or 0) + 1
        NotifyList()
    end
end

function Z.ItemList()
    local c = CFG()
    local out = {}
    for k, v in pairs(c.ignore) do
        out[#out + 1] = {
            key = k,
            kind = (type(v) == "table" and v.kind) or "item",
            id = (type(v) == "table" and v.id) or nil,
            label = (type(v) == "table" and v.label) or k,
            seq = (type(v) == "table" and tonumber(v.seq)) or 0,
        }
    end
    table.sort(out, function(a, b)
        if (a.seq or 0) ~= (b.seq or 0) then return (a.seq or 0) > (b.seq or 0) end
        return tostring(a.label) < tostring(b.label)
    end)
    return out
end

function Z.ItemCount()
    local n = 0
    for _ in pairs(CFG().ignore) do n = n + 1 end
    return n
end

function Z.ClearItems()
    local c = CFG()
    local n = 0
    for k in pairs(c.ignore) do c.ignore[k] = nil; n = n + 1 end
    if n > 0 then Z.IgnoreRev = (Z.IgnoreRev or 0) + 1 end
    NotifyList()
end

function Z.Context()
    local zone = Trim(GetZoneText and GetZoneText() or "")
    local sub = Trim(GetSubZoneText and GetSubZoneText() or "")
    local mapID
    if C_Map and C_Map.GetBestMapForUnit then
        local ok, v = pcall(C_Map.GetBestMapForUnit, "player")
        if ok then mapID = v end
    end
    return { zone = zone, sub = sub, mapID = mapID }
end

function Z.Key(ctx)
    ctx = ctx or Z.Context()
    if ctx.zone ~= "" then return ctx.zone end
    if ctx.mapID then return "map:" .. tostring(ctx.mapID) end
    return nil
end

local providers = {}
function Z.Register(kind, fn)
    if kind and type(fn) == "function" then providers[kind] = fn end
end

local function AreaName(areaID)
    local EG = ns.ExploreModule
    if EG and EG.ZoneName and areaID then
        local ok, v = pcall(EG.ZoneName, areaID)
        if ok and type(v) == "string" and v ~= "" then return v end
    end
    local mapID = areaID and (ns.AreaMap or {})[areaID]
    if mapID and C_Map and C_Map.GetMapInfo then
        local ok, mi = pcall(C_Map.GetMapInfo, mapID)
        if ok and mi and mi.name then return mi.name end
    end
    return nil
end

local function DGRef()
    return ns.DungeonDG or (ns.ProfHost and ns.ProfHost.DG)
end

local softQueued = false
local softForce = false
local tentShown = false
local tentPokeAt = nil
local TENT_GAP = 60

local function TentIn(res)
    local items = (type(res) == "table" and res.items) or {}
    for i = 1, #items do
        if items[i].kind == "tent" then return true end
    end
    return false
end

local softRes = { key = nil, t = 0 }

function Z.RefreshSoft(force)
    local ctx = Z.Context()
    local nowT = (GetTime and GetTime()) or 0
    local key = Z.Key(ctx)
    if not force and key and softRes.key == key and (nowT - softRes.t) < 1 then return end
    local res = Z.Collect(ctx)
    res.key = key
    softRes.key, softRes.t = key, nowT
    if ns.ZoneOrb and ns.ZoneOrb.Update then ns.ZoneOrb.Update(res) end
    if ns.ZoneHintList and ns.ZoneHintList.Refresh and ns.ZoneHintList.Count and ns.ZoneHintList.Count() > 0 then
        ns.ZoneHintList.Refresh()
    end
    local hasTent = TentIn(res)
    if not hasTent then
        tentShown = false
        tentPokeAt = nil
        return
    end
    if force then
        tentShown = false
        tentPokeAt = nil
    end
    if tentShown then return end
    local now = (GetTime and GetTime()) or 0
    local c = CFG()
    local busy = (type(InCombatLockdown) == "function") and InCombatLockdown()
    if busy or not c.on then return end
    if Z.IsBlocked(res.key) or Z.IsSessionSkipped(res.key) then return end
    if tentPokeAt and (now - tentPokeAt) < TENT_GAP then
        tentShown = true
        return
    end
    tentShown = true
    tentPokeAt = now
    if ns.ZoneOrb and ns.ZoneOrb.Reveal then ns.ZoneOrb.Reveal(res, "tent") end
end

function Z.ScheduleSoft(delay, force)
    if force then softForce = true end
    if softQueued then return end
    softQueued = true
    if type(C_Timer) == "table" and type(C_Timer.After) == "function" then
        C_Timer.After(delay or 1.5, function()
            softQueued = false
            local f = softForce
            softForce = false
            Z.RefreshSoft(f)
        end)
    end
end

local nameAsk = {}

local function AskName(id)
    if not id then return end
    local n = nameAsk[id] or 0
    if n >= 3 then return end
    nameAsk[id] = n + 1
    local DG = DGRef()
    if DG and DG.RequestItem then pcall(DG.RequestItem, id) end
    Z.ScheduleSoft()
end

local MISSING = nil

local function ItemName(id)
    if MISSING == nil then MISSING = L["暂时没有客户端数据"] end
    local DG = DGRef()
    if DG and DG.ItemName then
        local ok, nm = pcall(DG.ItemName, id)
        if ok and type(nm) == "string" and nm ~= "" and nm ~= MISSING then return nm, true end
    end
    AskName(id)
    return L["书籍"], false
end

local function ItemIcon(id)
    local DG = DGRef()
    if DG and DG.ItemIcon then
        local ok, ic = pcall(DG.ItemIcon, id)
        if ok then
            if type(ic) == "number" then return ic end
            if type(ic) == "string" and ic ~= "" then
                if ic:find("\\") then return ic end
                return "Interface\\Icons\\" .. ic
            end
        end
    end
    local f = C_Item and C_Item.GetItemIconByID
    if f then
        local ok, ic = pcall(f, id)
        if ok and type(ic) == "string" and ic ~= "" then return ic end
    end
    return "Interface\\Icons\\INV_Misc_Book_09"
end

local function QuestBadge(qid)
    local DG = DGRef()
    local st = "todo"
    if DG and DG.QuestBadgeState and qid then st = DG.QuestBadgeState(qid) or "todo" end
    return DG, st, OV_LEGEND[st] or OV_LEGEND.todo
end

local function QuestIconState(qid)
    local _, _, e = QuestBadge(qid)
    return e.sym
end

local function SplitLoc(s)
    if type(s) ~= "string" or s == "" then return nil end
    local x, y = s:match("([%d%.]+)%s*,%s*([%d%.]+)%s*$")
    local head = s:gsub("%s*[%d%.]+%s*,%s*[%d%.]+%s*$", "")
    local mapName, place = head:match("^(.-)%s*%-%s*(.+)$")
    if not mapName then mapName, place = head, nil end
    return Trim(mapName), Trim(place or ""), tonumber(x), tonumber(y)
end

local dgNames, dgOrder

local function LoadDungeons()
    if dgNames then return end
    dgNames, dgOrder = {}, {}
    local dd = ns.DungeonData and ns.DungeonData.dungeons
    if type(dd) ~= "table" then return end
    for i = 1, #dd do
        local d = dd[i]
        if d and d.id then
            dgNames[d.id] = d.name
            if dgOrder[d.id] == nil then dgOrder[d.id] = i end
        end
    end
end

local function DungeonName(slug)
    LoadDungeons()
    return slug and dgNames and dgNames[slug] or nil
end

local function DungeonOrder(slug)
    LoadDungeons()
    return (slug and dgOrder and dgOrder[slug]) or 9999
end

local BAG_TOY = 211527

local function HereArea(areaID, ctx)
    if not areaID then return false end
    local mid = (ns.AreaMap or {})[areaID]
    if mid and ctx.mapID and mid == ctx.mapID then return true end
    local nm = AreaName(areaID)
    if nm and SameName(nm, ctx.zone) then return true end
    return false
end

local function OwnItem(iid)
    if not iid then return false end
    local EG = ns.ExploreModule
    if EG and EG.CountInBags then
        local ok, n = pcall(EG.CountInBags, iid)
        if ok and (n or 0) > 0 then return true end
    end
    if type(GetItemCount) == "function" then
        local ok, n = pcall(GetItemCount, iid)
        if ok and (n or 0) > 0 then return true end
    end
    if type(C_Item) == "table" and type(C_Item.GetItemCount) == "function" then
        local ok, n = pcall(C_Item.GetItemCount, iid, true, false, true)
        if ok and (n or 0) > 0 then return true end
    end
    return false
end

local function BookLoc(rec, ctx)
    if type(rec[3]) == "number" and type(rec[4]) == "number" and HereArea(rec[2], ctx) then
        return { area = rec[2], x = rec[3], y = rec[4] }
    end
    local alt = rec[7]
    if type(alt) ~= "table" then return nil end
    for i = 1, #alt do
        local a = alt[i]
        if type(a) == "table" and type(a[2]) == "number" and type(a[3]) == "number"
           and HereArea(a[1], ctx) then
            return { area = a[1], x = a[2], y = a[3], alt = true }
        end
    end
    return nil
end

local function BookRows(ctx)
    local EG = ns.ExploreModule
    if not (EG and EG.IsBookFound) then return nil end
    local books = ns.ExploreBooks
    if type(books) ~= "table" then return nil end
    local keys, locs = {}, {}
    for bk, rec in pairs(books) do
        local loc = BookLoc(rec, ctx)
        if loc then
            local iid = (rec and rec[1]) or bk
            local found = false
            local ok, v = pcall(EG.IsBookFound, bk)
            if ok and v then found = true end
            if not found then
                local ok2, v2 = pcall(EG.IsBookFound, iid)
                if ok2 and v2 then found = true end
            end
            if not found and not Z.IsIgnored(ItemKey("book", iid)) then
                keys[#keys + 1] = bk
                locs[bk] = loc
            end
        end
    end
    local n = #keys
    if n == 0 then return nil end
    table.sort(keys)
    local list = {}
    for i = 1, n do
        local bk = keys[i]
        local rec = books[bk]
        local loc = locs[bk]
        local iid = rec[1] or bk
        local desc = rec[5]
        if type(desc) ~= "string" then desc = nil end
        local sub = string.format("%.1f, %.1f", loc.x, loc.y)
        if loc.alt then sub = sub .. " · " .. L["另一位置"] end
        list[i] = {
            id = iid, base = iid, ikey = ItemKey("book", iid), ikind = "book",
            name = ItemName(iid), icon = ItemIcon(iid),
            sub = sub, desc = desc,
            areaID = loc.area, x = loc.x, y = loc.y,
        }
    end
    return list
end

local TURNIN_AREA = 1497

local function TurnInSpot()
    local TI = ns.ExploreTurnIn
    if type(TI) ~= "table" then return nil end
    local side = (UnitFactionGroup and UnitFactionGroup("player")) or nil
    if type(side) == "string" then side = side:sub(1, 1) end
    local pick
    for i = 1, #TI do
        local o = TI[i]
        if type(o) == "table" and type(o.x) == "number" and type(o.y) == "number" then
            if side and o.side == side then return o end
            if not pick and o.area == TURNIN_AREA then pick = o end
        end
    end
    return pick
end

local function TurnInRows(ctx)
    local EG = ns.ExploreModule
    if not (EG and EG.CountInBags and EG.ScanAuto) then return nil end
    if not HereArea(TURNIN_AREA, ctx) then return nil end
    if not EG._auto then pcall(EG.ScanAuto) end
    local auto = EG._auto or {}
    local books = ns.ExploreBooks
    if type(books) ~= "table" then return nil end
    local spot = TurnInSpot()
    local subTxt, descTxt = L["可上交"], L["在幽暗城上交背包里的书"]
    if spot then
        subTxt = string.format("%s · %.1f, %.1f", L["可上交"], spot.x, spot.y)
        local nm, pl = tostring(spot.npc or ""), tostring(spot.place or "")
        if nm ~= "" and pl ~= "" then
            descTxt = string.format(L["%s（%s）"], nm, pl)
        elseif nm ~= "" then
            descTxt = nm
        end
    end
    local list = {}
    for bk, rec in pairs(books) do
        local iid = (rec and rec[1]) or bk
        if auto[iid] == "bag" and not Z.IsIgnored(ItemKey("turnin", iid)) then
            local row = {
                id = iid, base = iid, ikey = ItemKey("turnin", iid), ikind = "turnin",
                name = ItemName(iid), icon = ItemIcon(iid),
                sub = subTxt, desc = descTxt,
            }
            if spot then
                row.areaID, row.x, row.y = spot.area, spot.x, spot.y
            end
            list[#list + 1] = row
        end
    end
    local n = #list
    if n == 0 then return nil end
    table.sort(list, function(a, b) return tostring(a.name or "") < tostring(b.name or "") end)
    return {
        kind = "turnin", n = n, keys = {}, list = list,
        title = L["探索 · 书籍上交"],
        text = string.format(L["背包里有 %d 本可上交的书"], n),
    }
end

local function BagRows(ctx)
    local EG = ns.ExploreModule
    local chain = EG and EG.BagChain
    if type(chain) ~= "table" then return nil end
    if OwnItem(BAG_TOY) then return nil end
    if Z.IsIgnored(ItemKey("collect", BAG_TOY)) then return nil end
    local DG = DGRef()
    local side = (DG and DG.PlayerSide and DG.PlayerSide()) or "A"
    local step = 0
    for i = 1, #chain do
        local e = chain[i]
        if not e.optional then
            step = step + 1
            local q = e.q
            if type(q) == "table" then q = q[side] or q.A end
            if q then
                local done = DG and DG.QuestDone and DG.QuestDone(q)
                if not done then
                    local qs = DG and DG.QuestState and DG.QuestState(q)
                    if qs == "active" or qs == "ready" then return nil end
                    local loc = e.loc
                    if type(loc) == "table" and loc.area == nil then loc = loc[side] or loc.A end
                    if type(loc) == "table" and HereArea(loc.area, ctx) then
                        local qn, ok = nil, false
                        if DG and DG.QuestName then qn, ok = DG.QuestName(q) end
                        if not ok then Z.ScheduleSoft() end
                        local sub
                        if loc.x and loc.y then
                            sub = string.format(L["第 %d 步 · %.1f,%.1f"], step, loc.x, loc.y)
                        else
                            sub = string.format(L["第 %d 步"], step)
                        end
                        return { {
                            id = BAG_TOY, base = BAG_TOY, ikey = ItemKey("collect", BAG_TOY), ikind = "collect",
                            name = qn or L["睡袋"], icon = ItemIcon(BAG_TOY), sub = sub,
                            desc = loc.place, areaID = loc.area, x = loc.x, y = loc.y, qid = q,
                        } }
                    end
                    return nil
                end
            end
        end
    end
    return nil
end

local function TorchRows(ctx)
    local toys = ns.ExploreToys
    if type(toys) ~= "table" then return nil end
    local list = {}
    for i = 1, #toys do
        local t = toys[i]
        local iid, areaID = t[1], t[5]
        if iid and HereArea(areaID, ctx) and not OwnItem(iid) and not Z.IsIgnored(ItemKey("collect", iid)) then
            local pins = t[10]
            local x, y
            if type(pins) == "table" and type(pins[1]) == "table" then
                x, y = pins[1][3], pins[1][4]
            end
            local icon = t[2]
            if type(icon) == "string" and icon ~= "" then
                icon = "Interface\\Icons\\" .. icon
            else
                icon = ItemIcon(iid)
            end
            local sub = L["多点刷新"]
            if x and y then sub = string.format(L["多点刷新 · %.1f,%.1f"], x, y) end
            list[#list + 1] = {
                id = iid, base = iid, ikey = ItemKey("collect", iid), ikind = "collect",
                name = ItemName(iid) or L["守夜人火炬"], icon = icon, sub = sub,
                desc = t[8], areaID = areaID, x = x, y = y,
            }
        end
    end
    if #list == 0 then return nil end
    return list
end

local function FirstSeg(s)
    if type(s) ~= "string" then return nil end
    local i = string.find(s, " · ", 1, true)
    if i then return string.sub(s, 1, i - 1) end
    return s
end

local function InInstNow()
    if type(GetInstanceInfo) ~= "function" then return nil end
    local ok, nm, itype, _, _, _, _, _, iid = pcall(GetInstanceInfo)
    if not ok then return nil end
    local inside = (type(itype) == "string" and itype ~= "none") or (type(iid) == "number" and iid > 0)
    if not inside and type(IsInInstance) == "function" then
        local ok2, v = pcall(IsInInstance)
        if ok2 and v then inside = true end
    end
    if not inside then return nil end
    return nm
end

local function InstNamed(prefix)
    if type(prefix) ~= "string" or #prefix < 2 then return false end
    local nm = InInstNow()
    if not nm then return false end
    local cands = { nm, GetRealZoneText and GetRealZoneText() or nil, GetZoneText and GetZoneText() or nil }
    for i = 1, #cands do
        local s = cands[i]
        if type(s) == "string" and s ~= "" and (SameName(s, prefix) or string.find(s, prefix, 1, true)) then
            return true
        end
    end
    return false
end

local function BannerRows(ctx)
    local bs = ns.ExploreBanner
    if type(bs) ~= "table" then return nil end
    local list = {}
    for i = 1, #bs do
        local b = bs[i]
        local iid, areaID = b[1], b[5]
        local here = InstNamed(FirstSeg(b[8]) or "")
        if iid and here and not OwnItem(iid) and not Z.IsIgnored(ItemKey("collect", iid)) then
            local icon = b[2]
            if type(icon) == "string" and icon ~= "" then
                icon = "Interface\\Icons\\" .. icon
            else
                icon = ItemIcon(iid)
            end
            list[#list + 1] = {
                id = iid, base = iid, ikey = ItemKey("collect", iid), ikind = "collect",
                name = ItemName(iid) or L["血色旗帜"], icon = icon,
                sub = L["副本内"],
                desc = b[8], areaID = areaID,
                jump = function()
                    if ns.OpenPage then ns.OpenPage("Explore") end
                    local EG = ns.ExploreModule
                    if EG and EG.ShowSub then pcall(EG.ShowSub, "banner") end
                    return true
                end,
                jumpTip = L["点击查看获取步骤"],
            }
        end
    end
    if #list == 0 then return nil end
    return list
end

local function PCollect(ctx)
    local c = CFG()
    if not (c.book or c.bag or c.torch or c.banner) then return nil end
    local EG = ns.ExploreModule
    if not EG then return nil end
    if EG.ScanAuto and not EG._auto then pcall(EG.ScanAuto) end
    local list, keys = {}, {}
    local function Add(rows)
        if type(rows) ~= "table" then return end
        for i = 1, #rows do
            list[#list + 1] = rows[i]
            keys[#keys + 1] = rows[i].base
        end
    end
    if c.book then Add(BookRows(ctx)) end
    if c.bag then Add(BagRows(ctx)) end
    if c.torch then Add(TorchRows(ctx)) end
    if c.banner then Add(BannerRows(ctx)) end
    local n = #list
    if n == 0 then return nil end
    return {
        kind = "collect", n = n, keys = keys, list = list,
        title = L["探索 · 收集"],
        text = string.format(L["还有 %d 处未收集"], n),
    }
end

local function QuestClassOK(q)
    local raw = q[15]
    if not raw or raw == "" then return true end
    if type(UnitClass) ~= "function" then return true end
    local DG = DGRef()
    if not DG then return true end
    local list = DG.QClassList and DG.QClassList(raw)
    if not list then return true end
    local cn, tok = UnitClass("player")
    local map = DG.QCLASS_TOKEN
    for i = 1, #list do
        local s = list[i]
        if cn and s == cn then return true end
        local t = map and map[s]
        if t and tok and t == tok then return true end
    end
    return false
end

local dunLvCache
local function DunLvRange(slug)
    if not slug then return nil end
    if dunLvCache then return dunLvCache[slug] end
    local m = {}
    local dd = ns.DungeonData
    local list = dd and dd.dungeons
    if type(list) == "table" then
        for _, d in ipairs(list) do
            if type(d) == "table" and d.id then
                m[d.id] = { d.levelMin or 0, d.levelMax or 999 }
            end
        end
    end
    dunLvCache = m
    return m[slug]
end

local function QGreyLv(lv, qlv)
    if GetQuestDifficultyColor then
        local ok, c = pcall(GetQuestDifficultyColor, qlv)
        if ok and c and c.r then
            if math.abs(c.r - c.g) < 0.01 and math.abs(c.g - c.b) < 0.01 then return true end
            return false
        end
    end
    if lv <= 5 then return false end
    local g
    if lv <= 39 then
        g = lv - 5 - math.floor(lv / 10)
    elseif lv <= 59 then
        g = lv - 8 - math.floor((lv - 40) / 5)
    else
        g = lv - 12
    end
    return qlv <= g
end

local function HereSloc(pid, ctx)
    local sl = ns.DungeonQuestStartLoc
    local s = sl and sl[pid]
    if not s then return nil end
    if ctx.mapID and s[3] and s[3] == ctx.mapID then return s end
    if s[6] and SameName(s[6], ctx.zone) then return s end
    return nil
end

local function CurInstSlugs()
    local nm = InInstNow()
    if type(nm) ~= "string" or nm == "" then return nil end
    local dd = ns.DungeonData and ns.DungeonData.dungeons
    if type(dd) ~= "table" then return nil end
    local exact, pref = {}, {}
    for i = 1, #dd do
        local d = dd[i]
        if type(d) == "table" and d.id then
            if SameName(nm, d.name) or SameName(nm, d.nameEn) then
                exact[#exact + 1] = d.id
            elseif type(d.name) == "string" and #nm >= 2 and string.find(d.name, nm, 1, true) == 1 then
                pref[#pref + 1] = d.id
            end
        end
    end
    if #exact > 0 then return exact end
    if #pref > 0 then return pref end
    return nil
end

local questCache = { key = nil, t = 0, res = nil }

local questSlugs, qscan = nil, nil

local function ScanQOwn(sc, q)
    if ns.MapModule and ns.MapModule.QuestPinOK and not ns.MapModule.QuestPinOK(q[1]) then return false end
    if sc.side and q[2] and q[2] ~= sc.side then return false end
    if not QuestClassOK(q) then return false end
    if sc.DG.QuestRaceOK and not sc.DG.QuestRaceOK(q[1]) then return false end
    return true
end

local function ScanQHit(sc, q, slug)
    if not ScanQOwn(sc, q) then return false end
    local r = DunLvRange(slug)
    if sc.hideGrey then
        local gt
        if type(q[13]) == "table" then
            for k = 1, #q[13] do
                local dd = q[13][k]
                if type(dd) == "table" and dd[2] == 5 and type(dd[1]) == "number" then gt = dd[1] break end
            end
        end
        if gt then
            if sc.lv >= gt then return false end
        else
            local glv = sc.DG.QuestLevel and sc.DG.QuestLevel(q[1]) or nil
            if glv == nil then glv = q[4] end
            if glv == nil then glv = q[3] end
            if glv and QGreyLv(sc.lv, glv) then return false end
        end
    end
    if r and sc.lv >= r[1] and sc.lv <= r[2] then return true end
    return q[3] ~= nil and q[3] <= sc.lv
end

local function ScanRowDirect(sc, slug, q)
    local ctx = sc.ctx
    local loc = q[6]
    local sloc = HereSloc(q[1], ctx)
    local mapName = sloc and sloc[6] or (loc and sc.DG.QuestMapName and sc.DG.QuestMapName(loc))
    if not (mapName and not q[8] and SameName(mapName, ctx.zone)) then return end
    local DG = sc.DG
    local ok = ScanQHit(sc, q, slug)
    if ok and q[9] then
        for k = 1, #q[9] do
            if not DG.QuestDone(q[9][k]) and not DG.IsOptPre(q[1], q[9][k]) then ok = false break end
        end
    end
    if ok and DG.QuestState and DG.QuestState(q[1]) ~= "todo" then ok = false end
    if ok and Z.IsIgnored(ItemKey("quest", q[1])) then ok = false end
    if ok and sc.wantTodo then
        sc.n = sc.n + 1
        sc.hits[sc.n] = { q = q, slug = slug, loc = loc, sloc = sloc }
        sc.directSeen[q[1]] = true
    end
end

local function ScanRowPre(sc, slug, q)
    local pre = q[9]
    if not (type(pre) == "table" and not q[8] and not sc.directSeen[q[1]] and sc.wantTodo) then return end
    local DG = sc.DG
    if not (ScanQHit(sc, q, slug) and (not DG.QuestState or DG.QuestState(q[1]) == "todo")) then return end
    for k = 1, #pre do
        local pid = pre[k]
        local prow = DG.QuestRowByID and DG.QuestRowByID(pid) or nil
        local psd = (type(prow) == "table") and prow[2] or nil
        if not sc.preSeen[pid] and not sc.directSeen[pid] and not (DG.QuestDone and DG.QuestDone(pid))
           and not Z.IsIgnored(ItemKey("quest", pid))
           and not (sc.side and psd and psd ~= sc.side)
           and not (DG.QuestRaceOK and not DG.QuestRaceOK(pid))
           and not (ns.MapModule and ns.MapModule.QuestSideOK and not ns.MapModule.QuestSideOK(pid)) then
            local ps = HereSloc(pid, sc.ctx)
            if ps and (not DG.QuestState or DG.QuestState(pid) == "todo") then
                local pe = ns.DungeonQuestPreExtra and ns.DungeonQuestPreExtra[pid]
                local plv = (type(prow) == "table" and type(prow[3]) == "number") and prow[3] or nil
                if plv == nil and type(pe) == "table" and type(pe.lv) == "number" then plv = pe.lv end
                local chainOk = true
                if type(pe) == "table" then
                    for j = 1, #pe do
                        local pq = pe[j]
                        if type(pq) == "number" and not DG.QuestDone(pq) then chainOk = false break end
                    end
                end
                if chainOk and type(prow) == "table" and type(prow[9]) == "table" then
                    for j = 1, #prow[9] do
                        if not DG.QuestDone(prow[9][j]) then chainOk = false break end
                    end
                end
                if chainOk and (plv == nil or sc.lv >= plv) then
                    sc.preSeen[pid] = true
                    sc.n = sc.n + 1
                    sc.hits[sc.n] = { q = q, slug = slug, pre = pid, sloc = ps }
                end
            end
        end
    end
end

local function FinishQuestScan(sc)
    local DG = sc.DG
    local ctx = sc.ctx
    local lv = sc.lv
    local hits, n = sc.hits, sc.n
    local instSlugs = CurInstSlugs()
    if instSlugs then
        local seenQ = {}
        for k in pairs(sc.directSeen) do seenQ[k] = true end
        for si = 1, #instSlugs do
            local slug = instSlugs[si]
            local rows = sc.all[slug]
            if type(rows) == "table" then
                for i = 1, #rows do
                    local q = rows[i]
                    local st = DG.QuestState and DG.QuestState(q[1]) or "todo"
                    if st ~= "ready" and st ~= "done" then
                        local ok
                        if st == "active" then
                            ok = ScanQOwn(sc, q)
                        else
                            ok = ScanQHit(sc, q, slug)
                            if ok and type(q[9]) == "table" then
                                for k = 1, #q[9] do
                                    if not DG.QuestDone(q[9][k]) and not DG.IsOptPre(q[1], q[9][k]) then ok = false break end
                                end
                            end
                        end
                        if ok and Z.IsIgnored(ItemKey("quest", q[1])) then ok = false end
                        if ok and not seenQ[q[1]] and ((st == "active" and sc.wantTaken) or (st ~= "active" and sc.wantTodo)) then
                            seenQ[q[1]] = true
                            n = n + 1
                            hits[n] = { q = q, slug = slug, loc = q[6], inst = true }
                        end
                    end
                end
            end
        end
    end
    local nowT = (GetTime and GetTime()) or 0
    if n == 0 then
        questCache.key, questCache.t, questCache.res = sc.ck, nowT, nil
        Z.RefreshSoft(true)
        return
    end
    table.sort(hits, function(a, b)
        local oa, ob = DungeonOrder(a.slug), DungeonOrder(b.slug)
        if oa ~= ob then return oa < ob end
        return (a.q[1] or 0) < (b.q[1] or 0)
    end)
    local ids, list = {}, {}
    for i = 1, n do
        local h = hits[i]
        local q = h.q
        local dun = DungeonName(h.slug) or L["副本"]
        local ids2 = i
        if h.pre then
            local pid = h.pre
            local ps = h.sloc
            local pe = ns.DungeonQuestPreExtra and ns.DungeonQuestPreExtra[pid]
            local optPair = DG.IsOptPre(q[1], pid)
            local lvreq = pe and pe.lv or nil
            if lvreq and lvreq <= 0 then lvreq = nil end
            local st = DG.QuestState and DG.QuestState(pid)
            local can = (st ~= "done")
            if can and lvreq and lv < lvreq then can = false end
            local qname, qok = nil, false
            if DG.QuestName then qname, qok = DG.QuestName(pid) end
            if not qok then Z.ScheduleSoft() end
            local mainName = nil
            if DG.QuestName then mainName = DG.QuestName(q[1]) end
            local sub = dun
            local locdesc = dun
            if ps[2] and ps[2] ~= "" then
                locdesc = dun .. " · " .. ps[2]
                if ps[4] and ps[5] then locdesc = locdesc .. string.format(" %.1f, %.1f", ps[4], ps[5]) end
            end
            locdesc = locdesc .. " · " .. string.format(L["完成后解锁《%s》"], mainName or dun)
            ids2 = pid
            local _, bst, ovl = QuestBadge(pid)
            list[i] = {
                id = pid, base = pid, ikey = ItemKey("quest", pid),
                name = qname or tostring(pid),
                icon = ovl.sym,
                sub = sub, desc = locdesc, lvreq = lvreq, can = can,
                badge = { t = optPair and L["可选"] or L["前置"], col = optPair and (DG.Q_BADGE_OPT_BG or DG.Q_BADGE_PRE_BG) or DG.Q_BADGE_PRE_BG },
                discTex = QDISC, discCol = OVDiscCol(DG, bst),
                sym = ovl.sym, symCol = { ovl.ink[1], ovl.ink[2], ovl.ink[3] },
                qid = pid, mapName = ps[6], x = ps[4], y = ps[5], slug = h.slug,
            }
        else
            local mapName, place, x, y = SplitLoc(h.loc)
            local lvreq = q[3]
            if lvreq and lvreq <= 0 then lvreq = nil end
            local can = true
            if lvreq and lv < lvreq then can = false end
            if can and q[9] then
                for k = 1, #q[9] do
                    if not DG.QuestDone(q[9][k]) and not DG.IsOptPre(q[1], q[9][k]) then can = false break end
                end
            end
            local locdesc = dun
            if place and place ~= "" then
                locdesc = dun .. " · " .. place
                if x and y then locdesc = locdesc .. string.format(" %.0f,%.0f", x, y) end
            end
            if lvreq then
                locdesc = locdesc .. " · " .. L["可接等级"] .. " " .. lvreq
            end
            local qt = DG.QLCall and DG.QLCall("GetQuestType", q[1]) or nil
            local btext = (qt == 81) and L["地下城"] or L["副本内"]
            local progSub = nil
            local inDun = false
            if instSlugs then
                for _, s in ipairs(instSlugs) do
                    if s == h.slug then inDun = true break end
                end
            end
            if inDun and DG.QuestState and DG.QuestState(q[1]) == "active" then
                local objs = DG.QuestObjectiveList and DG.QuestObjectiveList(q[1]) or nil
                if objs then
                    local parts = {}
                    for oi = 1, #objs do
                        local ob = objs[oi]
                        if type(ob[1]) == "string" and ob[1] ~= "" then
                            if ob[3] > 0 and not ob[1]:find("%d+/%d+") then
                                parts[#parts + 1] = string.format("%d/%d %s", ob[2], ob[3], ob[1])
                            else
                                parts[#parts + 1] = ob[1]
                            end
                        end
                    end
                    if #parts > 0 then progSub = table.concat(parts, "\n") end
                end
            end
            ids2 = q[1]
            local qname, qok = nil, false
            if DG.QuestName then qname, qok = DG.QuestName(q[1]) end
            if not qok then Z.ScheduleSoft() end
            local _, bst, ovl = QuestBadge(q[1])
            list[i] = {
                id = q[1], base = q[1], ikey = ItemKey("quest", q[1]),
                name = qname or tostring(q[1]),
                icon = ovl.sym,
                sub = progSub or dun, desc = locdesc, lvreq = lvreq, can = can,
                badge = { t = btext, col = DG.Q_BADGE_IN_BG },
                discTex = QDISC, discCol = OVDiscCol(DG, bst),
                sym = ovl.sym, symCol = { ovl.ink[1], ovl.ink[2], ovl.ink[3] },
                qid = q[1], mapName = mapName, x = x, y = y, slug = h.slug,
            }
        end
        ids[i] = ids2
    end
    local anyInst = false
    for i = 1, n do
        if hits[i].inst then anyInst = true break end
    end
    local res = {
        kind = "quest", n = n, keys = ids, list = list,
        title = L["副本 · 任务"],
        text = string.format(anyInst and L["本副本待办 %d 个任务"] or L["本图可接 %d 个副本任务"], n),
    }
    questCache.key, questCache.t, questCache.res = sc.ck, nowT, res
    Z.RefreshSoft(true)
end

local function QuestScanTick(sc)
    if qscan ~= sc then return true end
    local all = sc.all
    if type(all) ~= "table" then qscan = nil return true end
    local over = debugprofilestop() + 3
    while true do
        if sc.phase <= 2 then
            local slugs = sc.slugs
            local si, ri = sc.si, sc.ri
            while si <= #slugs do
                local slug = slugs[si]
                local rows = all[slug]
                local cnt = type(rows) == "table" and #rows or 0
                local i = ri + 1
                while i <= cnt do
                    local q = rows[i]
                    if sc.phase == 1 then
                        ScanRowDirect(sc, slug, q)
                    else
                        ScanRowPre(sc, slug, q)
                    end
                    if debugprofilestop() > over then
                        sc.si, sc.ri = si, i
                        return
                    end
                    i = i + 1
                end
                si, ri = si + 1, 0
            end
            sc.phase = sc.phase + 1
            sc.si, sc.ri = 1, 0
        else
            FinishQuestScan(sc)
            qscan = nil
            return true
        end
    end
end

local function StartQuestScan(ck, ctx, DG, all, lv, side, hideGrey, wantTodo, wantTaken)
    local sc = qscan
    if sc and sc.ck == ck then return end
    if not questSlugs then
        questSlugs = {}
        for k in pairs(all) do questSlugs[#questSlugs + 1] = k end
    end
    sc = {
        ck = ck, ctx = ctx, DG = DG, all = all, lv = lv, side = side,
        hideGrey = hideGrey, wantTodo = wantTodo, wantTaken = wantTaken,
        slugs = questSlugs, hits = {}, n = 0, directSeen = {}, preSeen = {},
        phase = 1, si = 1, ri = 0,
    }
    qscan = sc
    if ns.IdleJobs and ns.IdleJobs.Add then
        ns.IdleJobs.Add(function() return QuestScanTick(sc) end)
    else
        while qscan == sc do
            QuestScanTick(sc)
        end
    end
end

local function PQuest(ctx)
    local c = CFG()
    local wantTodo = (c.quest ~= false)
    local wantTaken = (c.questTaken == true)
    if not wantTodo and not wantTaken then return nil end
    local DG = DGRef()
    local all = ns.DungeonQuests
    if not (DG and all) then return nil end
    local lv = (UnitLevel and UnitLevel("player")) or 60
    local side = DG.PlayerSide and DG.PlayerSide() or nil
    local hideGrey = (c.questGrey ~= false)
    local ck = tostring(ctx and ctx.zone) .. "|" .. tostring(ctx and ctx.sub) .. "|" .. tostring(lv) .. "|" .. tostring(side) .. "|" .. tostring(Z.IgnoreRev or 0) .. "|" .. tostring(wantTodo) .. tostring(wantTaken) .. "|" .. tostring(hideGrey)
    local nowT = (GetTime and GetTime()) or 0
    if questCache.key == ck and (nowT - questCache.t) < 30 then return questCache.res end
    StartQuestScan(ck, ctx, DG, all, lv, side, hideGrey, wantTodo, wantTaken)
    return nil
end

local function ZoneHasClassTrainer(ctx)
    local data = ns.ClassTrainerData
    if not (data and data.zones and data.classes) then return false end
    if not UnitClass then return false end
    local cls = select(2, UnitClass("player"))
    local fac = UnitFactionGroup and select(1, UnitFactionGroup("player")) or nil
    if not (cls and fac) then return false end
    local rows = data.classes[cls]
    if not rows then return false end
    local zid = nil
    for z, ui in pairs(data.zones) do
        if ui == ctx.mapID then zid = z break end
    end
    if not zid and ctx.mapID and C_Map and C_Map.GetMapInfo then
        local ok, mi = pcall(C_Map.GetMapInfo, ctx.mapID)
        if ok and mi and mi.parentMapID then
            for z, ui in pairs(data.zones) do
                if ui == mi.parentMapID then zid = z break end
            end
        end
    end
    if not zid then return false end
    for i = 1, #rows do
        local r = rows[i]
        if r.zoneId == zid and (r.faction == fac or r.faction == "Both") then return true end
    end
    return false
end

local function PSpell(ctx)
    local c = CFG()
    if not c.spell then return nil end
    local ST = ns.SpellTraining
    if not (ST and ST.Rows) then return nil end
    local ok, g, lv = pcall(ST.Rows)
    if not ok or type(g) ~= "table" or type(g.available) ~= "table" then return nil end
    local inCity = (CITIES[ctx.zone] or CITIES[ctx.sub]) and true or false
    local inTrainerZone = ZoneHasClassTrainer(ctx)
    local avail = (inCity and inTrainerZone) and g.available or {}
    local disc, discTip
    if ns.TrainerDiscount and ns.TrainerDiscount.Hint then
        local ok, r, t = pcall(ns.TrainerDiscount.Hint)
        if ok then disc, discTip = r, t end
    end
    local list, n = {}, 0
    for i = 1, #avail do
        local row = avail[i]
        if type(row) == "table" and row.id then
            local base = row.base or row.id
            local key = ItemKey("spell", base)
            if not Z.IsIgnored(key) then
                n = n + 1
                list[n] = {
                    id = row.id, base = base, ikey = key,
                    name = row.name or "", icon = row.icon,
                    learn = row.learn, rank = row.rank, tab = row.tab,
                    disc = disc, discTip = discTip,
                }
            end
        end
    end
    if n == 0 then return nil end
    local names, limit = {}, (n > 3 and 3 or n)
    for i = 1, limit do
        local nm = list[i].name
        if nm and nm ~= "" then names[#names + 1] = nm end
    end
    local text
    if #names > 0 then
        text = table.concat(names, " · ")
        if n > limit then text = text .. string.format(L[" 等 %d 个"], n) end
    else
        text = string.format(L["%d 个技能可学"], n)
    end
    return {
        kind = "spell", n = n, keys = {}, list = list,
        title = L["训练 · 技能"],
        text = text,
    }
end

local function PLearn(ctx)
    local c = CFG()
    if not c.spell then return nil end
    local ST = ns.SpellTraining
    if not (ST and ST.Rows) then return nil end
    local ok, g, lv = pcall(ST.Rows)
    if not ok or type(g) ~= "table" then return nil end
    local inTrainerZone = ZoneHasClassTrainer(ctx)
    local DG = ns.DungeonDG
    local list, n, nBook, nQuest = {}, 0, 0, 0
    local function put(row, src, q)
        local base = row.base or row.id
        local key = ItemKey("spell", base)
        if Z.IsIgnored(key) then return end
        n = n + 1
        local it = {
            id = row.id, base = base, ikey = key,
            name = row.name or "", icon = row.icon,
            learn = row.learn, rank = row.rank,
        }
        if src == "quest" then
            nQuest = nQuest + 1
            it.sub = L["任务获得"]
            if q and q.name and q.name ~= "" then it.sub = it.sub .. " · " .. q.name end
            it.badge = (DG and DG.Q_BADGE_PRE_BG) and { t = L["任务"], col = DG.Q_BADGE_PRE_BG } or nil
            it.mapID = q and q.uiMapId or nil
            it.x = q and q.x or nil
            it.y = q and q.y or nil
        elseif src == "misc" then
            it.sub = L["其他途径"]
            it.badge = (DG and DG.Q_BADGE_IN_BG) and { t = L["其他"], col = DG.Q_BADGE_IN_BG } or nil
        else
            nBook = nBook + 1
            local nm = row.book and ItemName(row.book) or nil
            it.sub = nm and nm or L["书"]
            it.badge = (DG and DG.Q_BADGE_IN_BG) and { t = L["书"], col = DG.Q_BADGE_IN_BG } or nil
        end
        list[n] = it
    end
    for i = 1, #(g.quest or {}) do
        local row = g.quest[i]
        if type(row) == "table" and row.id then
            local q = row.quest
            local nearSource = q and q.uiMapId and q.uiMapId == ctx.mapID
            if (inTrainerZone or nearSource) and not (lv and q and q.lv and q.lv > lv) then
                put(row, "quest", q)
            end
        end
    end
    if inTrainerZone then
        for i = 1, #(g.learn or {}) do
            local row = g.learn[i]
            if type(row) == "table" and row.id then put(row, row.src or "book", nil) end
        end
    end
    if n == 0 then return nil end
    local names, limit = {}, (n > 3 and 3 or n)
    for i = 1, limit do
        local nm = list[i].name
        if nm and nm ~= "" then names[#names + 1] = nm end
    end
    local text
    if #names > 0 then
        text = table.concat(names, " · ")
        if n > limit then text = text .. string.format(L[" 等 %d 个"], n) end
    else
        text = string.format(L["%d 个技能可学"], n)
    end
    local title
    if nBook > 0 and nQuest > 0 then
        title = L["学习 · 书 / 任务"]
    elseif nBook > 0 then
        title = L["学习 · 书"]
    elseif nQuest > 0 then
        title = L["学习 · 任务"]
    else
        title = L["学习 · 其他途径"]
    end
    return {
        kind = "learn", n = n, keys = {}, list = list,
        title = title,
        text = text,
    }
end

local KEY_ITEMS = {
    { "shadowfang_keep", { 276561, 275989 },
      L["达拉然隐藏 BOSS 激活物品"],
      L["阿鲁高书桌上拾取；带到银松森林 63.4, 64.3 换得召唤用书，用于召唤达拉然隐藏 BOSS"] },
}

local function OwnAny(ids)
    for i = 1, #ids do
        if OwnItem(ids[i]) then return true end
    end
    return false
end

local ARGENT_FACTION = 529
local ARGENT_TRINKET = 12846
local TRINKET_SLOTS = { 13, 14 }
local ARGENT_TTL = 2
local argentCache = { t = -1e9, need = false }
local argentEventAt = 0

local function ArgentExalted()
    if C_Reputation and C_Reputation.GetFactionDataByID then
        local ok, d = pcall(C_Reputation.GetFactionDataByID, ARGENT_FACTION)
        if ok and type(d) == "table" and type(d.reaction) == "number" then
            return d.reaction >= 8
        end
    end
    if type(GetFactionInfoByID) == "function" then
        local ok, _, _, standing = pcall(GetFactionInfoByID, ARGENT_FACTION)
        if ok and type(standing) == "number" then return standing >= 8 end
    end
    return false
end

local function TrinketEquipped()
    if type(GetInventoryItemID) ~= "function" then return false end
    for i = 1, #TRINKET_SLOTS do
        local ok, id = pcall(GetInventoryItemID, "player", TRINKET_SLOTS[i])
        if ok and id == ARGENT_TRINKET then return true end
    end
    return false
end

local function NeedArgentTrinket()
    if type(InCombatLockdown) == "function" and InCombatLockdown() then
        return argentCache.need
    end
    local now = (GetTime and GetTime()) or 0
    if now - argentCache.t < ARGENT_TTL then return argentCache.need end
    argentCache.t = now
    local need = false
    if not ArgentExalted() and not TrinketEquipped() then need = true end
    argentCache.need = need
    return need
end

local function InStratholme(slugs, ctx)
    if type(slugs) == "table" then
        for i = 1, #slugs do
            if slugs[i] == "stratholme_main" or slugs[i] == "stratholme_service" then return true end
        end
    end
    local cands = { ctx and ctx.zone, GetRealZoneText and GetRealZoneText() }
    for i = 1, #cands do
        local z = cands[i]
        if type(z) == "string" and (string.find(z, "斯坦索姆", 1, true) or string.find(z, "Stratholme", 1, true)) then
            return true
        end
    end
    return false
end

local argentName
local function ArgentTrinketName()
    if argentName then return argentName end
    local DG = DGRef()
    if DG and DG.ItemName then
        local ok, nm = pcall(DG.ItemName, ARGENT_TRINKET)
        if ok and type(nm) == "string" and nm ~= "" and nm ~= L["暂时没有客户端数据"] then
            argentName = nm
            return nm
        end
    end
    if C_Item and C_Item.GetItemNameByID then
        local ok, nm = pcall(C_Item.GetItemNameByID, ARGENT_TRINKET)
        if ok and type(nm) == "string" and nm ~= "" then
            argentName = nm
            return nm
        end
    end
    AskName(ARGENT_TRINKET)
    return L["银色黎明委任徽章"]
end

local function PKeyItem(ctx)
    local c = CFG()
    if c.keyitem == false then return nil end
    local slugs = CurInstSlugs()
    local here = {}
    if slugs then
        for i = 1, #slugs do here[slugs[i]] = true end
    end
    local list, n = {}, 0
    for i = 1, #KEY_ITEMS do
        local e = KEY_ITEMS[i]
        local ids = e[2]
        local iid = ids[1]
        if e[1] and here[e[1]] and not OwnAny(ids) and not Z.IsIgnored(ItemKey("collect", iid)) then
            n = n + 1
            list[n] = {
                id = iid, base = iid, ikey = ItemKey("collect", iid), ikind = "collect",
                name = ItemName(iid), icon = ItemIcon(iid),
                sub = e[3], desc = e[4],
                jump = function()
                    if ns.ShowDungeonDetail then
                        pcall(ns.ShowDungeonDetail, e[1])
                        return true
                    end
                    return false
                end,
                jumpTip = L["点击打开副本详情"],
            }
        end
    end
    if InStratholme(slugs, ctx) and NeedArgentTrinket()
       and not Z.IsIgnored(ItemKey("equip", ARGENT_TRINKET)) then
        n = n + 1
        list[n] = {
            id = ARGENT_TRINKET, base = ARGENT_TRINKET,
            ikey = ItemKey("equip", ARGENT_TRINKET), ikind = "equip",
            name = ArgentTrinketName(), icon = ItemIcon(ARGENT_TRINKET),
            sub = L["未装备 · 饰品栏"], desc = L["把「银色黎明委任徽章」放在饰品栏，刷亡灵才享受声望加成；崇拜后不再提醒"],
        }
    end
    if n == 0 then return nil end
    return {
        kind = "keyitem", n = n, keys = {}, list = list,
        title = L["副本 · 必备物品"],
        text = string.format(L["还差 %d 件必备物品"], n),
    }
end

Z.Register("collect", PCollect)
Z.Register("turnin", TurnInRows)
Z.Register("quest", PQuest)
Z.Register("keyitem", PKeyItem)
Z.Register("spell", PSpell)
Z.Register("learn", PLearn)

local function CDClassHex(cls)
    local c = cls and RAID_CLASS_COLORS and RAID_CLASS_COLORS[cls]
    if not c then return nil end
    return format("%02x%02x%02x",
        math.floor((c.r or 1) * 255 + 0.5),
        math.floor((c.g or 1) * 255 + 0.5),
        math.floor((c.b or 1) * 255 + 0.5))
end

local function CDReadyLine(nm, cls)
    local hex = CDClassHex(cls)
    if hex and nm and nm ~= "" then nm = "|cff" .. hex .. nm .. "|r" end
    return nm .. " " .. L["CD就绪了"]
end

local function PProfCD(ctx)
    local c = CFG()
    if c.profcd == false then return nil end
    local W = ns.ProfCDWatch
    if not (type(W) == "table" and type(W.TodoList) == "function") then return nil end
    local ok, list = pcall(W.TodoList)
    if not ok or type(list) ~= "table" or #list == 0 then return nil end
    local items, names = {}, {}
    for i = 1, #list do
        local e = list[i]
        local ign = Z.IsIgnored(ItemKey("profcd", e.spell))
        if not ign and e.item then ign = Z.IsIgnored(ItemKey("profcd", e.item)) end
        if not ign then
            local nm = e.name or L["冷却配方"]
            names[#names + 1] = nm
            local slug = e.slug
            local byc = e.byc
            local lines = {}
            if type(byc) == "table" and #byc > 0 then
                for j = 1, #byc do
                    local ch = byc[j]
                    lines[#lines + 1] = CDReadyLine(ch and ch.name or "", ch and ch.cls)
                end
            else
                local by = e.by
                if type(by) == "table" and #by > 0 then
                    for j = 1, #by do lines[#lines + 1] = CDReadyLine(by[j], nil) end
                else
                    lines[#lines + 1] = L["可再做"]
                end
            end
            items[#items + 1] = {
                id = e.item or e.spell, base = e.item or e.spell,
                ikey = ItemKey("profcd", e.spell), ikind = "profcd",
                name = nm,
                icon = e.item and ItemIcon(e.item) or nil,
                sub = table.concat(lines, "\n"),
                desc = L["专业冷却"],
                jump = function()
                    if ns.OpenPage then pcall(ns.OpenPage, "Professions") end
                    local pd = ns.ProfModule
                    if pd and slug and pd.Show then pcall(pd.Show, slug) end
                    return true
                end,
                jumpTip = L["点击打开专业页"],
            }
        end
    end
    if #items == 0 then return nil end
    return {
        kind = "profcd", n = #items, keys = {}, list = items,
        title = L["专业 · 冷却可做"],
        text = table.concat(names, " · "),
    }
end
Z.Register("profcd", PProfCD)

local WELL_FED_SPELL = 19705
local wellFedName = nil

local function ResolveWellFedName()
    if wellFedName then return wellFedName end
    local f = C_Spell and C_Spell.GetSpellInfo
    if f then
        local ok, si = pcall(f, WELL_FED_SPELL)
        if ok and type(si) == "table" and si.name and si.name ~= "" then
            wellFedName = si.name
        end
    end
    return wellFedName
end

local function WellFedIcon()
    local f = C_Spell and C_Spell.GetSpellInfo
    if f then
        local ok, si = pcall(f, WELL_FED_SPELL)
        if ok and type(si) == "table" and si.iconID then return si.iconID end
    end
    return "Interface\\Icons\\INV_Misc_Food_01"
end

local function Sealed(v)
    if type(issecretvalue) ~= "function" then return false end
    local ok, s = pcall(issecretvalue, v)
    return ok and s == true
end

local TALENT_ICON = "Interface\\Icons\\INV_Misc_QuestionMark"

local function TalentCount()
    local CT = _G.C_ClassTalents
    if type(CT) ~= "table" or type(CT.HasUnspentTalentPoints) ~= "function" then return nil end
    local ok, has, classPt, specPt = pcall(CT.HasUnspentTalentPoints)
    if not ok or Sealed(has) then return nil end
    local n = 0
    if not Sealed(classPt) and type(classPt) == "number" then n = n + classPt end
    if not Sealed(specPt) and type(specPt) == "number" then n = n + specPt end
    if type(CT.HasUnspentHeroTalentPoints) == "function" then
        local ok2, _, heroPt = pcall(CT.HasUnspentHeroTalentPoints)
        if ok2 and not Sealed(heroPt) and type(heroPt) == "number" then n = n + heroPt end
    end
    if n > 0 then return n end
    if has == true then return -1 end
    return nil
end

local function TalentIcon()
    local CSI = _G.C_SpecializationInfo
    if type(CSI) == "table"
        and type(CSI.GetSpecialization) == "function"
        and type(CSI.GetSpecializationInfo) == "function" then
        local ok, idx = pcall(CSI.GetSpecialization)
        if ok and not Sealed(idx) and type(idx) == "number" and idx > 0 then
            local ok2, _, _, _, icon = pcall(CSI.GetSpecializationInfo, idx)
            if ok2 and icon then return icon end
        end
    end
    return TALENT_ICON
end

local function PTalent()
    local c = CFG()
    if c.talent == false then return nil end
    local key = ItemKey("talent", "talent")
    if Z.IsIgnored(key) then return nil end
    local n = TalentCount()
    if not n then return nil end
    local sub
    if n > 0 then
        sub = string.format(L["有 %d 点还没有分配"], n)
    else
        sub = L["有天赋点还没有分配"]
    end
    return {
        kind = "talent", n = 1, keys = {}, title = L["天赋"],
        list = {
            {
                id = "talent", base = "talent", ikey = key, ikind = "talent",
                name = L["天赋点未分配"],
                sub = sub,
                desc = L["在天赋界面把点数用掉，角色会更强"],
                icon = TalentIcon(),
                jumpTip = L["点击打开天赋界面"],
            },
        },
    }
end

Z.Register("talent", PTalent)

local function HasWellFed()
    local name = ResolveWellFedName()
    if not (C_UnitAuras and C_UnitAuras.GetAuraDataByIndex) then return false end
    for i = 1, 40 do
        local ok, a = pcall(C_UnitAuras.GetAuraDataByIndex, "player", i, "HELPFUL")
        if not ok then return false end
        if not a then break end
        if not Sealed(a.spellId) and a.spellId == WELL_FED_SPELL then return true end
        if name and not Sealed(a.name) and a.name == name then return true end
    end
    return false
end

local foodList, foodListAt = nil, 0

local function ItemInfo(id)
    local f = (C_Item and C_Item.GetItemInfo) or GetItemInfo
    if type(f) ~= "function" then return nil end
    return f(id)
end

local function SlotInfo(bag, slot)
    local f = C_Container and C_Container.GetContainerItemInfo
    if type(f) == "function" then
        local ok, info = pcall(f, bag, slot)
        if ok and type(info) == "table" then
            return tonumber(info.stackCount) or 1, info.iconFileID or info.icon
        end
    end
    return 1, nil
end

local function FoodList()
    local now = (GetTime and GetTime()) or 0
    if foodList and (now - foodListAt) < 2 then return foodList end
    foodListAt = now
    foodList = {}
    if type(C_Container) ~= "table" or type(C_Container.GetContainerItemID) ~= "function" then return foodList end
    local drink, foodSpell
    if type(C_Spell) == "table" and type(C_Spell.GetSpellName) == "function" then
        local ok, n = pcall(C_Spell.GetSpellName, 430)
        if ok then drink = n end
        local ok2, n2 = pcall(C_Spell.GetSpellName, 433)
        if ok2 then foodSpell = n2 end
    end
    local seen = {}
    local bags = (type(NUM_BAG_SLOTS) == "number" and NUM_BAG_SLOTS) or 4
    for bag = 0, bags do
        local slots = C_Container.GetContainerNumSlots(bag) or 0
        for slot = 1, slots do
            local id = C_Container.GetContainerItemID(bag, slot)
            if id then
                local nm, _, _, ilvl, _, _, _, _, _, tex, _, cid, scid = ItemInfo(id)
                if cid == 0 and scid == 5 then
                    local ok2, sn = pcall(C_Item.GetItemSpell, id)
                    if not (ok2 and drink and sn == drink) then
                        local cnt, sic = SlotInfo(bag, slot)
                        local e = seen[id]
                        if e then
                            e.count = e.count + cnt
                        else
                            e = { id = id, name = nm or tostring(id), ilvl = tonumber(ilvl) or 0,
                                  count = cnt, icon = sic or tex, meal = (ok2 and foodSpell and sn == foodSpell) and true or false }
                            seen[id] = e
                            foodList[#foodList + 1] = e
                        end
                    end
                end
            end
        end
    end
    table.sort(foodList, function(a, b)
        if a.meal ~= b.meal then return a.meal end
        if a.ilvl ~= b.ilvl then return a.ilvl > b.ilvl end
        return a.id < b.id
    end)
    return foodList
end

Z.FoodList = FoodList

local DEFAULT_FOOD_ITEM = 6890

local function PreferredFood()
    local list = FoodList()
    local want = tonumber(CFG().preferFood) or 0
    if want > 0 then
        for i = 1, #list do if list[i].id == want then return list[i] end end
        return list[1]
    end
    for i = 1, #list do if list[i].id == DEFAULT_FOOD_ITEM then return list[i] end end
    return list[1]
end

local function FoodRow(c)
    if not c.food then return nil end
    if Z.IsIgnored(ItemKey("food", WELL_FED_SPELL)) then return nil end
    if type(IsResting) == "function" then
        local ok, rest = pcall(IsResting)
        if ok and rest == true then return nil end
    end
    if HasWellFed() then return nil end
    local f = PreferredFood()
    local sub = L["缺少进食充分"]
    local actTip, actLabel
    if f then
        sub = string.format(L["吃「%s」×%d"], f.name, f.count)
        actTip = string.format(L["左键吃「%s」，右键换一种"], f.name)
        actLabel = L["使用"]
    else
        actTip = L["背包里没有食物"]
    end
    return {
        id = WELL_FED_SPELL, base = WELL_FED_SPELL,
        ikey = ItemKey("food", WELL_FED_SPELL), ikind = "food",
        name = L["食物"],
        note = L["5%经验"],
        icon = WellFedIcon(),
        sub = sub,
        desc = L["吃任意食物获得进食充分效果，打怪经验 +5%"],
        foodID = f and f.id,
        actLabel = actLabel,
        actTip = actTip,
    }
end

local SLEEP_BAG_ITEM = 211527
local WELL_RESTED_SPELL = 429959
local wellRestedName = nil
local worldAt = nil

local function ResolveWellRestedName()
    if wellRestedName then return wellRestedName end
    local f = C_Spell and C_Spell.GetSpellInfo
    if f then
        local ok, si = pcall(f, WELL_RESTED_SPELL)
        if ok and type(si) == "table" and si.name and si.name ~= "" then
            wellRestedName = si.name
        end
    end
    return wellRestedName
end

local function WellRestedState()
    local name = ResolveWellRestedName()
    local now = (GetTime and GetTime()) or 0
    if worldAt == nil then return nil, nil end
    if now > 0 and now - worldAt < 6 then return nil, nil end
    local seen = false
    if not (C_UnitAuras and C_UnitAuras.GetAuraDataByIndex) then return nil, nil end
    for i = 1, 40 do
        local ok, a = pcall(C_UnitAuras.GetAuraDataByIndex, "player", i, "HELPFUL")
        if not ok then return nil, nil end
        if not a then break end
        seen = true
        if (not Sealed(a.spellId) and a.spellId == WELL_RESTED_SPELL)
            or (name and not Sealed(a.name) and a.name == name) then
            local rem = math.huge
            local exp = a.expirationTime
            if not Sealed(exp) and type(exp) == "number" and exp > 0 then
                rem = math.max(0, exp - now)
            end
            return true, rem
        end
    end
    if not seen then return false, nil end
    return false, nil
end

local function SleepBagCdLeft()
    local f = (C_Item and C_Item.GetItemCooldown) or GetItemCooldown
    if not f then return 0 end
    local ok, start, dur = pcall(f, SLEEP_BAG_ITEM)
    if not ok or type(start) ~= "number" or type(dur) ~= "number" or dur <= 0 then return 0 end
    local now = (GetTime and GetTime()) or 0
    return math.max(0, start + dur - now)
end

local function SleepBagCdReady()
    return SleepBagCdLeft() <= 0
end

local function SleepBagIcon()
    local f = GetItemIcon
    if f then
        local ok, ic = pcall(f, SLEEP_BAG_ITEM)
        if ok and ic then return ic end
    end
    return 133662
end

local RESTED_WARN = 1800
local restedGen = 0
local function ArmRestedTimer(rem)
    restedGen = restedGen + 1
    if not (rem and rem ~= math.huge and rem > RESTED_WARN) then return end
    if not (type(C_Timer) == "table" and type(C_Timer.After) == "function") then return end
    local my = restedGen
    C_Timer.After(rem - RESTED_WARN + 1, function()
        if my == restedGen then Z.ScheduleSoft(0.1, true) end
    end)
end

local function RestedRow(c)
    if not c.rested then return nil end
    if Z.IsIgnored(ItemKey("rested", SLEEP_BAG_ITEM)) then return nil end
    if not OwnItem(SLEEP_BAG_ITEM) then return nil end
    local buffed, rem = WellRestedState()
    if buffed == nil then return nil end
    ArmRestedTimer(buffed and rem or nil)
    local sub = L["缺少精神饱满"]
    if buffed then
        if rem == nil or rem >= RESTED_WARN then return nil end
        if not SleepBagCdReady() then
            local left = SleepBagCdLeft()
            restedGen = restedGen + 1
            if left < rem and type(C_Timer) == "table" and C_Timer.After then
                local my = restedGen
                C_Timer.After(left + 1, function()
                    if my == restedGen then Z.ScheduleSoft(0.1, true) end
                end)
            end
            return nil
        end
        sub = L["精神饱满即将到期"]
    end
    return {
        id = SLEEP_BAG_ITEM, base = SLEEP_BAG_ITEM,
        ikey = ItemKey("rested", SLEEP_BAG_ITEM), ikind = "rested",
        name = L["使用舒适的睡袋"], icon = SleepBagIcon(),
        sub = sub,
        desc = L["在睡袋中休息至少一分钟，获得的经验值提高 1%，最多叠加 3 次"],
        useItem = SLEEP_BAG_ITEM,
        actLabel = L["使用"],
        actTip = L["左键铺开睡袋"],
    }
end

local function PBuff(ctx)
    local c = CFG()
    local list = {}
    local fr = FoodRow(c)
    if fr then list[#list + 1] = fr end
    local rr = RestedRow(c)
    if rr then list[#list + 1] = rr end
    local CW = ns.CampWatch
    if CW and CW.Rows then
        local ok, rows = pcall(CW.Rows)
        if ok and type(rows) == "table" then
            for i = 1, #rows do list[#list + 1] = rows[i] end
        end
    end
    if #list == 0 then return nil end
    return { kind = "buff", n = #list, keys = {}, list = list, title = L["增益"] }
end

Z.Register("buff", PBuff)

local CARROT_ID = 11122
local CT = { slot = nil, orig = nil, id = nil, wait = nil, was = nil }
Z.MountSwap = CT

local function InvID(slot)
    if type(GetInventoryItemID) ~= "function" then return nil end
    local ok, v = pcall(GetInventoryItemID, "player", slot)
    if ok then return v end
    return nil
end

local function CarrotOn()
    return InvID(13) == CARROT_ID or InvID(14) == CARROT_ID
end

local function InInst()
    if type(IsInInstance) ~= "function" then return false end
    local ok, v = pcall(IsInInstance)
    return ok and v == true
end

local function BagFn(k)
    local C = rawget(_G, "C_Container")
    return (type(C) == "table" and C[k]) or rawget(_G, k)
end

local function FindInBags(id)
    local num, get = BagFn("GetContainerNumSlots"), BagFn("GetContainerItemID")
    if not (num and get) then return nil end
    for bag = 0, tonumber(NUM_BAG_SLOTS) or 4 do
        local okN, n = pcall(num, bag)
        if okN then
            for s = 1, tonumber(n) or 0 do
                local ok, v = pcall(get, bag, s)
                if ok and v == id then return bag, s end
            end
        end
    end
end

local function FreeBagSlot()
    local num, get, free = BagFn("GetContainerNumSlots"), BagFn("GetContainerItemID"), BagFn("GetContainerNumFreeSlots")
    if not (num and get and free) then return nil end
    for bag = 0, tonumber(NUM_BAG_SLOTS) or 4 do
        local okF, _, fam = pcall(free, bag)
        if okF and (tonumber(fam) or 0) == 0 then
            local okN, n = pcall(num, bag)
            if okN then
                for s = 1, tonumber(n) or 0 do
                    local ok, v = pcall(get, bag, s)
                    if ok and v == nil then return bag, s end
                end
            end
        end
    end
end

local function TrinketBusy()
    if type(InCombatLockdown) == "function" and InCombatLockdown() then return true end
    if type(UnitIsDeadOrGhost) == "function" and UnitIsDeadOrGhost("player") then return true end
    local casts = {}
    if type(UnitCastingInfo) == "function" then casts[#casts + 1] = UnitCastingInfo end
    if type(UnitChannelInfo) == "function" then casts[#casts + 1] = UnitChannelInfo end
    for i = 1, #casts do
        local ok, v = pcall(function() return casts[i]("player") ~= nil end)
        if ok and v then return true end
    end
    return false
end

local function TrinketName(id, fallback)
    local DG = DGRef()
    if DG and DG.ItemName then
        local ok, nm = pcall(DG.ItemName, id)
        if ok and type(nm) == "string" and nm ~= "" and nm ~= L["暂时没有客户端数据"] then return nm end
    end
    if C_Item and C_Item.GetItemNameByID then
        local ok, nm = pcall(C_Item.GetItemNameByID, id)
        if ok and type(nm) == "string" and nm ~= "" then return nm end
    end
    return fallback
end

local function EquipTo(name, slot)
    local C = rawget(_G, "C_Item")
    local f = (type(C) == "table" and C.EquipItemByName) or rawget(_G, "EquipItemByName")
    if f then pcall(f, name, slot) end
end

local function SwapSay()
    if ns.ZoneOrb and ns.ZoneOrb.SaySwap then pcall(ns.ZoneOrb.SaySwap) end
end

local function SaveSwap()
    local c = CFG()
    if CT.slot then
        c.carrotSwap = { CT.slot, CT.orig or false, CT.id }
    else
        c.carrotSwap = nil
    end
end

function CT.DoEquip()
    if TrinketBusy() then CT.wait = true; return false end
    if CarrotOn() then return false end
    if not FindInBags(CARROT_ID) then return false end
    local slot = (InvID(13) == nil and 13) or (InvID(14) == nil and 14) or 14
    CT.slot, CT.orig, CT.id = slot, InvID(slot), CARROT_ID
    SaveSwap()
    EquipTo(TrinketName(CARROT_ID, L["棍子上的胡萝卜"]), slot)
    SwapSay()
    Z.ScheduleSoft(0.3, true)
    return true
end

function CT.DoRestore()
    local slot, orig, id = CT.slot, CT.orig, CT.id
    if not slot then return false end
    if TrinketBusy() then CT.wait = true; return false end
    CT.slot, CT.orig, CT.id, CT.wait = nil, nil, nil, nil
    SaveSwap()
    if InvID(slot) ~= id then return false end
    if orig then
        if not FindInBags(orig) then return false end
        EquipTo(TrinketName(orig, L["原饰品"]), slot)
    else
        local bag, s = FreeBagSlot()
        local pick = BagFn("PickupContainerItem")
        if not (bag and pick and PickupInventoryItem) then return false end
        PickupInventoryItem(slot)
        pcall(pick, bag, s)
        if ClearCursor then pcall(ClearCursor) end
    end
    SwapSay()
    Z.ScheduleSoft(0.3, true)
    return true
end

function CT.Sync(force)
    local m = (IsMounted and IsMounted()) and true or false
    if not force and m == CT.was and not CT.wait then return end
    CT.was = m
    if TrinketBusy() then CT.wait = true; return end
    CT.wait = nil
    if CT.slot and InvID(CT.slot) ~= CT.id then
        CT.slot, CT.orig, CT.id = nil, nil, nil
        SaveSwap()
    end
    if m then
        if not InInst() and CFG().carrot ~= false and CFG().carrotAuto ~= false and not CT.slot and not CarrotOn() then CT.DoEquip() end
    else
        if CT.slot then CT.DoRestore() end
    end
end

function CT.ToggleAuto()
    local c = CFG()
    if c.carrotAuto == false then
        c.carrotAuto = true
        CT.Sync(true)
    else
        c.carrotAuto = false
        if CT.slot then CT.DoRestore() end
    end
    Z.ScheduleSoft(0.2, true)
end

function CT.ToggleMaster()
    local c = CFG()
    if c.carrot == false then
        c.carrot = true
        CT.Sync(true)
    else
        c.carrot = false
        if CT.slot then CT.DoRestore() end
    end
    Z.ScheduleSoft(0.2, true)
end

function CT.ManualEquip()
    return CT.DoEquip()
end

function CT.ManualRestore()
    local c = CFG()
    if c.carrotAuto ~= false then c.carrotAuto = false end
    return CT.DoRestore()
end

local ownT, ownV = -1e9, false
local function CarrotOwned()
    if CarrotOn() then return true end
    local nowT = (GetTime and GetTime()) or 0
    if nowT - ownT < 2 then return ownV end
    ownT = nowT
    ownV = FindInBags(CARROT_ID) ~= nil
    return ownV
end

function CT.Owned()
    return CarrotOwned()
end

local carrotName
local function CarrotNameCached()
    if carrotName then return carrotName end
    local DG = DGRef()
    if DG and DG.ItemName then
        local ok, nm = pcall(DG.ItemName, CARROT_ID)
        if ok and type(nm) == "string" and nm ~= "" and nm ~= L["暂时没有客户端数据"] then carrotName = nm end
    end
    return carrotName or L["棍子上的胡萝卜"]
end

local function PMount(ctx)
    if Z.IsIgnored(ItemKey("mount", CARROT_ID)) then return nil end
    if CFG().carrot == false then return nil end
    if InInst() then
        if not CarrotOn() then return nil end
        local swapped = (CT.slot and InvID(CT.slot) == CT.id) and true or false
        local row = {
            id = CARROT_ID, base = CARROT_ID,
            ikey = ItemKey("mount", CARROT_ID), ikind = "mount",
            name = CarrotNameCached(), icon = ItemIcon(CARROT_ID),
            desc = L["副本里坐骑饰品不起作用，换回正常装备再开打"],
            jumpTip = L["上马自动换上，下马自动换回"],
        }
        if swapped then
            row.sub = string.format(L["副本中 · 换回「%s」"], TrinketName(CT.orig, L["原饰品"]))
            row.mountAct = "restore"
            row.autoOn = CFG().carrotAuto ~= false
            row.autoKey = true
        else
            row.sub = L["副本中 · 建议换回正常饰品"]
        end
        return { kind = "mount", n = 1, keys = {}, list = { row }, title = L["坐骑"], text = "" }
    end
    if not CarrotOwned() then return nil end
    local on = CFG().carrotAuto ~= false
    local m = (IsMounted and IsMounted()) and true or false
    local swapped = (CT.slot and InvID(CT.slot) == CT.id) and true or false
    local sub, act
    if swapped then
        act = "restore"
        if m then
            if CT.orig then
                sub = string.format(L["下马将换回「%s」"], TrinketName(CT.orig, L["原饰品"]))
            else
                sub = L["下马将摘回背包"]
            end
        else
            sub = L["已换上 · 点换回摘下"]
        end
    elseif m then
        if CarrotOn() then
            sub = L["已装备 · 无需换装"]
        elseif not on then
            sub = L["自动换装已关"]
            act = "equip"
        elseif CT.wait then
            sub = L["战斗中 · 脱战后自动换上"]
            act = "equip"
        else
            sub = L["上马将自动换上"]
            act = "equip"
        end
    else
        if on then
            sub = L["上马将自动换上"]
        else
            sub = L["自动换装已关"]
        end
    end
    return {
        kind = "mount", n = 1, keys = {},
        list = {
            {
                id = CARROT_ID, base = CARROT_ID,
                ikey = ItemKey("mount", CARROT_ID), ikind = "mount",
                name = CarrotNameCached(),
                icon = ItemIcon(CARROT_ID),
                sub = sub,
                desc = L["上马自动换上「棍子上的胡萝卜」，下马自动换回原饰品"],
                mountAct = act, autoOn = on, autoKey = true,
                jumpTip = L["上马自动换上，下马自动换回"],
            },
        },
        title = L["坐骑"], text = "",
    }
end

Z.Register("mount", PMount)

local function PTent(ctx)
    local CW = ns.CampWatch
    if not (CW and CW.Card) then return nil end
    local ok, card = pcall(CW.Card)
    if not ok or type(card) ~= "table" then return nil end
    return card
end

Z.Register("tent", PTent)

local sessionSkip = {}
local shownPrint = {}
local pending = nil
local zoneTimer = false

local sim = nil
local SIM_ICON = "Interface\\Icons\\"
local SIM_SPELLS = {
    { "圣光闪现", "Spell_Holy_FlashHeal", 26, 2 },
    { "寒冰箭", "Spell_Frost_FrostBolt02", 28 },
    { "灼热之光", "Spell_Fire_FlameShock", 30, 3 },
    { "治疗祷言", "Spell_Holy_PrayerOfHealing", 34 },
    { "驱散魔法", "Spell_Holy_DispelMagic", 36, 1 },
    { "真言术：盾", "Spell_Holy_PowerWordShield", 40, 4 },
    { "次级治疗术", "Spell_Holy_LesserHeal", 42 },
    { "强化暗影箭", "Spell_Shadow_ShadowBolt", 46, 2 },
    { "变形术", "Spell_Magic_PolymorphPig", 50 },
    { "神圣新星", "Spell_Holy_HolyNova", 54, 5 },
}

local function SimSpells(n)
    local list = {}
    for i = 1, n do
        local t = SIM_SPELLS[(i - 1) % #SIM_SPELLS + 1]
        local lap = math.floor((i - 1) / #SIM_SPELLS)
        list[i] = {
            id = 900000 + i,
            base = 900000 + i,
            name = t[1],
            icon = SIM_ICON .. t[2],
            learn = t[3] + lap * 6,
            rank = t[4],
            tab = L["模拟"],
        }
    end
    return list
end

function Z.IsSim()
    return sim ~= nil
end

function Z.SimSet(book, quest, spell)
    local b = math.max(0, math.floor(tonumber(book) or 0))
    local q = math.max(0, math.floor(tonumber(quest) or 0))
    local s = math.max(0, math.floor(tonumber(spell) or 0))
    if b + q + s <= 0 then
        sim = nil
    else
        sim = { book = b, quest = q, spell = s }
    end
    return sim
end

local SIM_BOOKS = {
    { "《大法师安东尼达斯：未删节的自传》", 62.4, 45.1, "探险者大厅中央的圆桌上" },
    { "药剂师的超自然读本", 59.4, 52.3, "布瑞尔炼金店的货架上，药剂师旁边" },
    { "《阿塔瑞克：论奥术奇迹》", 43.4, 41.2, "银松森林墓穴内的桌上" },
}
local SIM_QUESTS = {
    { "影牙城堡的诅咒", "影牙城堡", "银松森林 - 焚木村", 46, 69, 26, true },
    { "被遗忘者的援军", "影牙城堡", "幽暗城 - 皇家区", 56, 92, 30, true },
    { "南海镇的委托", "影牙城堡", "希尔斯布莱德丘陵 - 南海镇", 51, 58, 56, false },
}

local function SimBooks(n)
    local list = {}
    for i = 1, n do
        local t = SIM_BOOKS[(i - 1) % #SIM_BOOKS + 1]
        local lap = math.floor((i - 1) / #SIM_BOOKS)
        list[i] = {
            id = 800000 + i, base = 800000 + i,
            name = t[1], icon = "Interface\\Icons\\INV_Misc_Book_09",
            sub = string.format("%.1f, %.1f", t[2] + lap, t[3]),
            desc = t[4],
            areaID = 130, x = t[2] + lap, y = t[3],
        }
    end
    return list
end

local function SimQuests(n)
    local list = {}
    for i = 1, n do
        local t = SIM_QUESTS[(i - 1) % #SIM_QUESTS + 1]
        local lap = math.floor((i - 1) / #SIM_QUESTS)
        local simOv = OV_LEGEND.todo
        list[i] = {
            id = 700000 + i, base = 700000 + i,
            name = t[1], icon = simOv.sym,
            sub = string.format(L["%s · 可接等级 %d"], t[2], t[6]),
            desc = string.format("%s · %s %.0f,%.0f", t[2], t[3], t[4] + lap, t[5]),
            lvreq = t[6], can = t[7],
            discTex = QDISC, discCol = OVDiscCol(nil, "todo"),
            sym = simOv.sym, symCol = { simOv.ink[1], simOv.ink[2], simOv.ink[3] },
            qid = 700000 + i, x = t[4] + lap, y = t[5],
        }
    end
    return list
end

local function SimCollect(ctx)
    local out = {
        ctx = { zone = L["模拟预览"], sub = "", mapID = ctx and ctx.mapID },
        items = {}, total = 0, sim = true,
    }
    if sim.book > 0 then
        local list = SimBooks(sim.book)
        out.items[#out.items + 1] = {
            kind = "book", n = #list, keys = {}, list = list,
            title = L["探索 · 书籍"], text = "",
        }
        out.total = out.total + #list
    end
    if sim.quest > 0 then
        local list = SimQuests(sim.quest)
        out.items[#out.items + 1] = {
            kind = "quest", n = #list, keys = {}, list = list,
            title = L["副本 · 任务"], text = "",
        }
        out.total = out.total + #list
    end
    if sim.spell > 0 then
        local list = SimSpells(sim.spell)
        out.items[#out.items + 1] = {
            kind = "spell", n = #list, keys = {}, list = list,
            title = L["训练 · 技能"], text = "",
        }
        out.total = out.total + #list
    end
    out.key = Z.Key(out.ctx)
    return out
end

function Z.Collect(ctx)
    ctx = ctx or Z.Context()
    if sim then return SimCollect(ctx) end
    local out = { ctx = ctx, items = {}, total = 0 }
    local c = CFG()
    local order = { "collect", "turnin", "quest", "keyitem", "spell", "learn", "profcd", "talent", "buff", "mount", "tent" }
    for i = 1, #order do
        local kind = order[i]
        local on = c[kind]
        if kind == "learn" then on = c.spell end
        if kind == "collect" then on = (c.book or c.bag or c.torch or c.banner) end
        if kind == "buff" then on = (c.food or c.rested or c.camp or c.renew) end
        if kind == "mount" then on = true end
        if on and providers[kind] then
            local ok, res = pcall(providers[kind], ctx)
            if ok and type(res) == "table" and (res.n or 0) > 0 then
                out.items[#out.items + 1] = res
                out.total = out.total + res.n
            end
        end
    end
    return out
end

local function Sig(res)
    local parts = {}
    for i = 1, #res.items do
        local it = res.items[i]
        parts[i] = tostring(it.kind) .. "=" .. tostring(it.n)
    end
    return table.concat(parts, ";")
end

function Z.IsBlocked(key)
    if not key then return false end
    return CFG().blacklist[key] ~= nil
end

function Z.IsSessionSkipped(key)
    return key ~= nil and sessionSkip[key] == true
end

function Z.SkipSession(key)
    if key then sessionSkip[key] = true end
end

function Z.Block(key, name, kinds)
    if not key then return end
    local c = CFG()
    c.blacklist[key] = {
        name = name or key,
        kinds = kinds or "all",
        seq = NextSeq(),
    }
    NotifyList()
end

function Z.Unblock(key)
    if not key then return end
    CFG().blacklist[key] = nil
    NotifyList()
end

function Z.ClearBlock()
    local c = CFG()
    for k in pairs(c.blacklist) do c.blacklist[k] = nil end
    NotifyList()
end

function Z.BlockList()
    local c = CFG()
    local out = {}
    for k, v in pairs(c.blacklist) do
        out[#out + 1] = { key = k, name = (type(v) == "table" and v.name) or k,
                          kinds = (type(v) == "table" and v.kinds) or "all",
                          seq = (type(v) == "table" and tonumber(v.seq)) or 0 }
    end
    table.sort(out, function(a, b)
        if (a.seq or 0) ~= (b.seq or 0) then return (a.seq or 0) > (b.seq or 0) end
        return tostring(a.name) < tostring(b.name)
    end)
    return out
end

function Z.BlockCount()
    local c = CFG()
    local n = 0
    for _ in pairs(c.blacklist) do n = n + 1 end
    return n
end

function Z.Schedule(reason, attempt)
    local d = DELAYS[attempt + 1]
    if not d then return false end
    if type(C_Timer) == "table" and type(C_Timer.After) == "function" then
        C_Timer.After(d, function() Z.Check(reason, attempt + 1) end)
    end
    return false
end

function Z.LoginCheck(spent)
    local DG = DGRef()
    if DG and DG.questDoneSet == nil and (spent or 0) < 2 then
        if type(C_Timer) == "table" and type(C_Timer.After) == "function" then
            C_Timer.After(0.1, function() Z.LoginCheck((spent or 0) + 0.1) end)
        else
            Z.Check("login", 0)
        end
        return
    end
    Z.Check("login", 0)
end

function Z.Check(reason, attempt)
    attempt = attempt or 0
    local c = CFG()
    if not c.on then
        if ns.ZoneOrb and ns.ZoneOrb.Hide then ns.ZoneOrb.Hide() end
        return false
    end
    local ctx = Z.Context()
    local key = Z.Key(ctx)
    if not key then return false end
    if Z.IsBlocked(key) then return false end
    if Z.IsSessionSkipped(key) then return false end

    local res = Z.Collect(ctx)
    res.key = key
    res.reason = reason

    if res.total == 0 and attempt < #DELAYS then
        return Z.Schedule(reason, attempt)
    end

    if ns.ZoneOrb and ns.ZoneOrb.Update then ns.ZoneOrb.Update(res) end

    if res.total == 0 then return false end

    if reason == "zone" and c.noZonePopup ~= false then return false end

    if type(InCombatLockdown) == "function" and InCombatLockdown() then
        pending = key
        return false
    end

    if ns.MainFrame and ns.MainFrame.IsShown and ns.MainFrame:IsShown() then
        return false
    end

    local fp = Sig(res)
    if shownPrint[key] == fp then return false end
    shownPrint[key] = fp

    if ns.ZoneOrb and ns.ZoneOrb.Reveal then ns.ZoneOrb.Reveal(res, reason) end
    return true
end

function Z.CheckNow(reason)
    return Z.Check(reason or "manual", 0)
end

local KIND_NAME = { collect = L["收集"], book = L["书籍"], turnin = L["书籍上交"], quest = L["任务"], keyitem = L["必备物品"], equip = L["饰品"], spell = L["技能"], learn = L["学习"], talent = L["天赋"], buff = L["增益"], camp = L["露营"], campren = L["到期"], tent = L["蹭帐篷"], food = L["食物"], profcd = L["冷却"], rested = L["睡袋"], bag = L["睡袋"], torch = L["火炬"], banner = L["旗帜"], mount = L["坐骑"], map = L["整张地图"] }
function Z.KindName(kind)
    return KIND_NAME[kind] or L["条目"]
end

function Z.IconFor(kind, id)
    if kind == "book" or kind == "collect" or kind == "turnin" or kind == "equip" or kind == "mount" then return ItemIcon(id) end
    if kind == "talent" then return TalentIcon() end
    if kind == "quest" then return QuestIconState(id) end
    if kind == "rested" then
        local f = GetItemIcon
        if f then
            local ok, ic = pcall(f, id)
            if ok and ic then return ic end
        end
        return 133662
    end
    if kind == "profcd" then
        local ic = ItemIcon(id)
        if ic then return ic end
        local f = C_Spell and C_Spell.GetSpellInfo
        if f then
            local ok, si = pcall(f, id)
            if ok and type(si) == "table" and si.iconID then return si.iconID end
        end
        return "Interface\\Icons\\INV_Misc_QuestionMark"
    end
    if kind == "spell" or kind == "learn" or kind == "food" or kind == "camp" or kind == "campren" then
        local f = C_Spell and C_Spell.GetSpellInfo
        if f then
            local ok, si = pcall(f, id)
            if ok and type(si) == "table" and si.iconID then return si.iconID end
        end
        return "Interface\\Icons\\INV_Misc_QuestionMark"
    end
    return "Interface\\Icons\\INV_Misc_QuestionMark"
end

function Z.Refresh()
    local ctx = Z.Context()
    local key = Z.Key(ctx)
    local res = Z.Collect(ctx)
    res.key = key
    if ns.ZoneOrb and ns.ZoneOrb.Update then ns.ZoneOrb.Update(res) end
    return res
end

function Z.OnZoneChanged()
    if zoneTimer then return end
    zoneTimer = true
    if type(C_Timer) == "table" and type(C_Timer.After) == "function" then
        C_Timer.After(0.8, function()
            zoneTimer = false
            Z.Check("zone", 0)
        end)
    else
        zoneTimer = false
        Z.Check("zone", 0)
    end
end

function Z.ResetSession()
    for k in pairs(sessionSkip) do sessionSkip[k] = nil end
    for k in pairs(shownPrint) do shownPrint[k] = nil end
    pending = nil
end

local frame = CreateFrame("Frame")

ns.Init(function()
    CFG()
    local savedSwap = CFG().carrotSwap
    if type(savedSwap) == "table" and savedSwap[1] then
        CT.slot = savedSwap[1]
        CT.orig = (savedSwap[2] ~= false and savedSwap[2]) or nil
        CT.id = savedSwap[3]
    end
    frame:RegisterEvent("PLAYER_ENTERING_WORLD")
    frame:RegisterEvent("ZONE_CHANGED_NEW_AREA")
    frame:RegisterEvent("ZONE_CHANGED")
    frame:RegisterEvent("PLAYER_REGEN_ENABLED")
    frame:RegisterEvent("BAG_UPDATE_DELAYED")
    frame:RegisterEvent("QUEST_LOG_UPDATE")
    if frame.RegisterUnitEvent then
        frame:RegisterUnitEvent("UNIT_AURA", "player")
    else
        frame:RegisterEvent("UNIT_AURA")
    end
    pcall(frame.RegisterEvent, frame, "ITEM_COOLDOWN_UPDATE")
    pcall(frame.RegisterEvent, frame, "SPELL_UPDATE_COOLDOWN")
    pcall(frame.RegisterEvent, frame, "CHARACTER_POINTS_CHANGED")
    pcall(frame.RegisterEvent, frame, "PLAYER_LEVEL_UP")
    pcall(frame.RegisterEvent, frame, "PLAYER_SPECIALIZATION_CHANGED")
    pcall(frame.RegisterEvent, frame, "TRAIT_CONFIG_UPDATED")
    pcall(frame.RegisterEvent, frame, "ACTIVE_TALENT_GROUP_CHANGED")
    pcall(frame.RegisterEvent, frame, "PLAYER_EQUIPMENT_CHANGED")
    pcall(frame.RegisterEvent, frame, "UPDATE_FACTION")
    frame:RegisterEvent("PLAYER_TARGET_CHANGED")
    pcall(frame.RegisterEvent, frame, "PLAYER_UPDATE_RESTING")
    pcall(frame.RegisterEvent, frame, "PLAYER_MOUNT_DISPLAY_CHANGED")
    pcall(frame.RegisterEvent, frame, "PLAYER_ALIVE")
    pcall(frame.RegisterEvent, frame, "PLAYER_UNGHOST")
    pcall(frame.RegisterUnitEvent, frame, "UNIT_SPELLCAST_STOP", "player")
    pcall(frame.RegisterUnitEvent, frame, "UNIT_SPELLCAST_CHANNEL_STOP", "player")
    pcall(frame.RegisterUnitEvent, frame, "UNIT_SPELLCAST_INTERRUPTED", "player")
    frame:SetScript("OnEvent", function(_, event)
        if event == "PLAYER_ENTERING_WORLD" then
            worldAt = (GetTime and GetTime()) or 0
            questCache.t = -1e9
            CT.Sync(true)
            Z.LoginCheck(0)
        elseif event == "UNIT_AURA" then
            CT.Sync()
            Z.ScheduleSoft(5)
        elseif event == "PLAYER_UPDATE_RESTING" then
            Z.ScheduleSoft(0.5, true)
        elseif event == "ITEM_COOLDOWN_UPDATE" or event == "SPELL_UPDATE_COOLDOWN" then
            Z.ScheduleSoft(1.2)
        elseif event == "PLAYER_TARGET_CHANGED" then
            local CW = ns.CampWatch
            if CW and CW.TentUnit and CW.TentUnit() then
                Z.ScheduleSoft(0.1, true)
            else
                Z.ScheduleSoft(0.4)
            end
        elseif event == "BAG_UPDATE_DELAYED" or event == "QUEST_LOG_UPDATE" then
            local EG = ns.ExploreModule
            if EG then EG._auto = nil end
            questCache.t = -1e9
            qscan = nil
            Z.ScheduleSoft(0.6, true)
        elseif event == "PLAYER_EQUIPMENT_CHANGED" or event == "UPDATE_FACTION" then
            local nowT = (GetTime and GetTime()) or 0
            if nowT - argentEventAt >= 1 then
                argentEventAt = nowT
                if type(InCombatLockdown) ~= "function" or not InCombatLockdown() then
                    argentCache.t = -1e9
                end
                CT.Sync(true)
                Z.ScheduleSoft(0.8)
            end
        elseif event == "PLAYER_REGEN_ENABLED" then
            CT.Sync(true)
            if pending then
                pending = nil
                Z.Check("regen", 0)
            end
            Z.ScheduleSoft(0.6)
        elseif event == "PLAYER_MOUNT_DISPLAY_CHANGED" then
            CT.Sync(true)
            Z.ScheduleSoft(0.3, true)
        elseif event == "PLAYER_ALIVE" or event == "PLAYER_UNGHOST" then
            CT.Sync(true)
        elseif event == "UNIT_SPELLCAST_STOP" or event == "UNIT_SPELLCAST_CHANNEL_STOP" or event == "UNIT_SPELLCAST_INTERRUPTED" then
            CT.Sync()
        elseif event == "CHARACTER_POINTS_CHANGED" or event == "PLAYER_LEVEL_UP"
            or event == "PLAYER_SPECIALIZATION_CHANGED" or event == "TRAIT_CONFIG_UPDATED"
            or event == "ACTIVE_TALENT_GROUP_CHANGED" then
            Z.ScheduleSoft(0.4, true)
        else
            Z.OnZoneChanged()
        end
    end)
    if ns.ZoneOrb and ns.ZoneOrb.Init then ns.ZoneOrb.Init() end
    Z.LoginCheck(0)
end)

local SIM_USAGE = "/dfhint 4 3 8 · /dfhint spells 8 · /dfhint off"

function Z.SimCommand(msg)
    local s = Trim(tostring(msg or "")):lower()
    local head = "|cff46bf72[" .. L["无限副本手册"] .. "·模拟]|r "
    if s == "" then
        local res = Z.Collect(Z.Context())
        res.key = Z.Key(res.ctx)
        if ns.ZoneOrb and ns.ZoneOrb.ForceOpen then ns.ZoneOrb.ForceOpen(res) end
        if sim then
            print(head .. string.format(L["模拟中：书 %d / 任务 %d / 技能 %d"], sim.book, sim.quest, sim.spell))
        else
            print(head .. L["当前为真实数据"])
        end
        print(head .. L["用法"] .. L["： "] .. SIM_USAGE)
        return
    end
    if s == "off" or s == "0" or s == "clear" or s == "关" then
        sim = nil
        Z.ResetSession()
        if ns.ZoneOrb then
            if ns.ZoneOrb.Hide then
                local res = Z.Refresh()
                if (res.total or 0) == 0 then ns.ZoneOrb.Hide() end
            end
        end
        print(head .. L["已关闭模拟，恢复真实待办"])
        return
    end
    local mode = s:match("^mode%s+(%a+)$")
    if mode then
        if mode ~= "auto" and mode ~= "badge" and mode ~= "silent" then
            print(head .. L["用法"] .. L["： /dfhint mode auto|badge|silent"])
            return
        end
        CFG().mode = mode
        print(head .. L["提醒方式"] .. " = " .. mode)
        return
    end
    local kind, num = s:match("^(%a+)%s+(%d+)$")
    if kind then
        local cur = sim or { book = 0, quest = 0, spell = 0 }
        local v = tonumber(num) or 0
        if kind == "book" or kind == "books" then
            cur.book = v
        elseif kind == "quest" or kind == "quests" then
            cur.quest = v
        elseif kind == "spell" or kind == "spells" or kind == "train" then
            cur.spell = v
        else
            print(head .. L["用法"] .. L["： "] .. SIM_USAGE)
            return
        end
        Z.SimSet(cur.book, cur.quest, cur.spell)
    else
        local a, b, c = s:match("^(%d+)%s*(%d*)%s*(%d*)$")
        if not a then
            print(head .. L["用法"] .. L["： "] .. SIM_USAGE)
            return
        end
        Z.SimSet(tonumber(a), tonumber(b), tonumber(c))
    end
    if not sim then
        print(head .. L["模拟条数为 0，已回到真实数据"])
        Z.Refresh()
        return
    end
    local res = Z.Collect(Z.Context())
    res.key = Z.Key(res.ctx)
    if ns.ZoneOrb then
        if ns.ZoneOrb.Update then ns.ZoneOrb.Update(res) end
        if ns.ZoneOrb.ForceOpen then ns.ZoneOrb.ForceOpen(res) end
    end
    print(head .. string.format(L["模拟中：书 %d / 任务 %d / 技能 %d"], sim.book, sim.quest, sim.spell))
    print(head .. L["关闭"] .. L["： /dfhint off"])
end

if type(SlashCmdList) == "table" then
    SLASH_DUNGEONSZONEHINT1 = "/dfhint"
    SLASH_DUNGEONSZONEHINT2 = L["/待办模拟"]
    SLASH_DUNGEONSZONEHINT3 = "/df模拟"
    SlashCmdList["DUNGEONSZONEHINT"] = function(msg)
        Z.SimCommand(msg)
    end
end
