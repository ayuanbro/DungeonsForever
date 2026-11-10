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
local QSYM_CAN = "Interface\\AddOns\\DungeonsForever\\Media\\icon\\QUEST\\QMarkExcl"
local QSYM_CANT = "Interface\\AddOns\\DungeonsForever\\Media\\Pins\\QuestSymLock"
local QDISC_CAN = { 1, 0.82, 0 }
local QDISC_CANT = { 0.45, 0.47, 0.50 }
local QSYM_CANCOL = { 0.227, 0.165, 0 }
local QSYM_CANTCOL = { 0.08, 0.08, 0.09 }

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
    if c.spell == nil then c.spell = true end
    if c.food == nil then c.food = true end
    if c.rested == nil then c.rested = true end
    if c.voice == nil then c.voice = false end
    if c.voiceInit ~= 2 then
        c.voiceInit = 2
        c.voice = false
    end
    if c.foodVoice == nil then c.foodVoice = true end
    if c.restedVoice == nil then c.restedVoice = true end
    if c.turnin == nil then c.turnin = true end
    if c.onlyTodo == nil then c.onlyTodo = false end
    if c.mode == nil then c.mode = "auto" end
    if c.dur == nil then c.dur = 12 end
    if c.icon == nil then c.icon = 32 end
    if type(c.blacklist) ~= "table" then c.blacklist = {} end
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

function Z.IgnoreItem(kind, id, label)
    local key = ItemKey(kind, id)
    if not key then return nil end
    CFG().ignore[key] = {
        kind = kind,
        id = id,
        label = label or key,
        seq = NextSeq(),
    }
    return key
end

function Z.UnignoreItem(key)
    if key then CFG().ignore[key] = nil end
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
    for k in pairs(c.ignore) do c.ignore[k] = nil end
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

function Z.RefreshSoft()
    local ctx = Z.Context()
    local res = Z.Collect(ctx)
    res.key = Z.Key(ctx)
    if ns.ZoneOrb and ns.ZoneOrb.Update then ns.ZoneOrb.Update(res) end
    if ns.ZoneHintList and ns.ZoneHintList.Refresh and ns.ZoneHintList.Count and ns.ZoneHintList.Count() > 0 then
        ns.ZoneHintList.Refresh()
    end
end

function Z.ScheduleSoft()
    if softQueued then return end
    softQueued = true
    if type(C_Timer) == "table" and type(C_Timer.After) == "function" then
        C_Timer.After(1.5, function()
            softQueued = false
            Z.RefreshSoft()
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

local function BookRows(ctx)
    local EG = ns.ExploreModule
    if not (EG and EG.IsBookFound) then return nil end
    local books = ns.ExploreBooks
    if type(books) ~= "table" then return nil end
    local keys = {}
    for bk, rec in pairs(books) do
        if HereArea(rec and rec[2], ctx) then
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
        local iid = rec[1] or bk
        local desc = rec[5]
        if type(desc) ~= "string" then desc = nil end
        list[i] = {
            id = iid, base = iid, ikey = ItemKey("book", iid), ikind = "book",
            name = ItemName(iid), icon = ItemIcon(iid),
            sub = string.format("%.1f, %.1f", rec[3] or 0, rec[4] or 0), desc = desc,
            areaID = rec[2], x = rec[3], y = rec[4],
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
    pcall(EG.ScanAuto)
    local auto = EG._auto or {}
    local books = ns.ExploreBooks
    if type(books) ~= "table" then return nil end
    local spot = TurnInSpot()
    local subTxt, descTxt = L["可上交"], L["在幽暗城上交背包里的书"]
    if spot then
        subTxt = string.format("%s · %.1f, %.1f", L["可上交"], spot.x, spot.y)
        local nm, pl = tostring(spot.npc or ""), tostring(spot.place or "")
        if nm ~= "" and pl ~= "" then
            descTxt = string.format("%s（%s）", nm, pl)
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

local function PQuest(ctx)
    local c = CFG()
    if not c.quest then return nil end
    local DG = DGRef()
    local all = ns.DungeonQuests
    if not (DG and all) then return nil end
    local lv = (UnitLevel and UnitLevel("player")) or 60
    local side = DG.PlayerSide and DG.PlayerSide() or nil
    local function QHitPin(q, slug)
        if ns.MapModule and ns.MapModule.QuestPinOK and not ns.MapModule.QuestPinOK(q[1]) then return false end
        if side and q[2] and q[2] ~= side then return false end
        if not QuestClassOK(q) then return false end
        if DG.QuestRaceOK and not DG.QuestRaceOK(q[1]) then return false end
        local r = DunLvRange(slug)
        local gt
        if type(q[13]) == "table" then
            for k = 1, #q[13] do
                local dd = q[13][k]
                if type(dd) == "table" and dd[2] == 5 and type(dd[1]) == "number" then gt = dd[1] break end
            end
        end
        if gt then
            if lv >= gt then return false end
        else
            local glv = DG.QuestLevel and DG.QuestLevel(q[1]) or nil
            if glv == nil then glv = q[4] end
            if glv == nil then glv = q[3] end
            if glv and QGreyLv(lv, glv) then return false end
        end
        if r and lv >= r[1] and lv <= r[2] then return true end
        return q[3] ~= nil and q[3] <= lv
    end
    local hits, n = {}, 0
    local directSeen = {}
    for slug, rows in pairs(all) do
        for i = 1, #rows do
            local q = rows[i]
            local loc = q[6]
            local sloc = HereSloc(q[1], ctx)
            local mapName = sloc and sloc[6] or (loc and DG.QuestMapName and DG.QuestMapName(loc))
            if mapName and not q[8] and SameName(mapName, ctx.zone) then
                local ok = QHitPin(q, slug)
                if ok and q[9] then
                    for k = 1, #q[9] do
                        if not DG.QuestDone(q[9][k]) and not DG.IsOptPre(q[1], q[9][k]) then ok = false break end
                    end
                end
                if ok and DG.QuestState and DG.QuestState(q[1]) ~= "todo" then ok = false end
                if ok and Z.IsIgnored(ItemKey("quest", q[1])) then ok = false end
                if ok then
                    n = n + 1
                    hits[n] = { q = q, slug = slug, loc = loc, sloc = sloc }
                    directSeen[q[1]] = true
                end
            end
        end
    end
    local preSeen = {}
    for slug, rows in pairs(all) do
        for i = 1, #rows do
            local q = rows[i]
            local pre = q[9]
            if type(pre) == "table" and not q[8] and not directSeen[q[1]] then
                if QHitPin(q, slug) and (not DG.QuestState or DG.QuestState(q[1]) == "todo") then
                    for k = 1, #pre do
                        local pid = pre[k]
                        local prow = DG.QuestRowByID and DG.QuestRowByID(pid) or nil
                        local psd = (type(prow) == "table") and prow[2] or nil
                        if not preSeen[pid] and not directSeen[pid] and not (DG.QuestDone and DG.QuestDone(pid))
                           and not (side and psd and psd ~= side)
                           and not (DG.QuestRaceOK and not DG.QuestRaceOK(pid))
                           and not (ns.MapModule and ns.MapModule.QuestSideOK and not ns.MapModule.QuestSideOK(pid)) then
                            local ps = HereSloc(pid, ctx)
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
                                if chainOk and (plv == nil or lv >= plv) then
                                    preSeen[pid] = true
                                    n = n + 1
                                    hits[n] = { q = q, slug = slug, pre = pid, sloc = ps }
                                end
                            end
                        end
                    end
                end
            end
        end
    end
    if n == 0 then return nil end
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
            list[i] = {
                id = pid, base = pid, ikey = ItemKey("quest", pid),
                name = qname or tostring(pid),
                icon = "Interface\\GossipFrame\\AvailableQuestIcon",
                sub = sub, desc = locdesc, lvreq = lvreq, can = can,
                badge = { t = optPair and L["可选"] or L["前置"], col = optPair and (DG.Q_BADGE_OPT_BG or DG.Q_BADGE_PRE_BG) or DG.Q_BADGE_PRE_BG },
                disc = QDISC, discCol = can and QDISC_CAN or QDISC_CANT,
                sym = can and QSYM_CAN or QSYM_CANT,
                symCol = can and QSYM_CANCOL or QSYM_CANTCOL,
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
            ids2 = q[1]
            local qname, qok = nil, false
            if DG.QuestName then qname, qok = DG.QuestName(q[1]) end
            if not qok then Z.ScheduleSoft() end
            list[i] = {
                id = q[1], base = q[1], ikey = ItemKey("quest", q[1]),
                name = qname or tostring(q[1]),
                icon = "Interface\\GossipFrame\\AvailableQuestIcon",
                sub = dun, desc = locdesc, lvreq = lvreq, can = can,
                badge = { t = btext, col = DG.Q_BADGE_IN_BG },
                disc = QDISC, discCol = can and QDISC_CAN or QDISC_CANT,
                sym = can and QSYM_CAN or QSYM_CANT,
                symCol = can and QSYM_CANCOL or QSYM_CANTCOL,
                qid = q[1], mapName = mapName, x = x, y = y, slug = h.slug,
            }
        end
        ids[i] = ids2
    end
    return {
        kind = "quest", n = n, keys = ids, list = list,
        title = L["副本 · 任务"],
        text = string.format(L["本图可接 %d 个副本任务"], n),
    }
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
                }
            end
        end
    end
    local DG = ns.DungeonDG
    for i = 1, #(g.quest or {}) do
        local row = g.quest[i]
        if type(row) == "table" and row.id then
            local q = row.quest
            local nearSource = q and q.uiMapId and q.uiMapId == ctx.mapID
            if (inTrainerZone or nearSource) and not (lv and q and q.lv and q.lv > lv) then
                local base = row.base or row.id
                local key = ItemKey("spell", base)
                if not Z.IsIgnored(key) then
                    n = n + 1
                    local sub = L["任务获得"]
                    if q and q.name and q.name ~= "" then sub = sub .. " · " .. q.name end
                    list[n] = {
                        id = row.id, base = base, ikey = key,
                        name = row.name or "", icon = row.icon,
                        sub = sub,
                        badge = (DG and DG.Q_BADGE_PRE_BG) and { t = L["任务"], col = DG.Q_BADGE_PRE_BG } or nil,
                        mapID = q and q.uiMapId or nil,
                        x = q and q.x or nil,
                        y = q and q.y or nil,
                    }
                end
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

Z.Register("collect", PCollect)
Z.Register("turnin", TurnInRows)
Z.Register("quest", PQuest)
Z.Register("spell", PSpell)

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

local function HasWellFed()
    local name = ResolveWellFedName()
    local seen = false
    if C_UnitAuras and C_UnitAuras.GetAuraDataByIndex then
        for i = 1, 40 do
            local ok, a = pcall(C_UnitAuras.GetAuraDataByIndex, "player", i, "HELPFUL")
            if not ok then return true end
            if not a then break end
            seen = true
            if not Sealed(a.spellId) and a.spellId == WELL_FED_SPELL then return true end
            if name and not Sealed(a.name) and a.name == name then return true end
        end
    end
    if not seen then return true end
    return false
end

local function FoodRow(c)
    if not c.food then return nil end
    if type(IsResting) == "function" then
        local ok, rest = pcall(IsResting)
        if ok and rest == true then return nil end
    end
    if HasWellFed() then return nil end
    local lv = (UnitLevel and UnitLevel("player")) or 0
    return {
        id = WELL_FED_SPELL, base = WELL_FED_SPELL,
        ikey = ItemKey("food", WELL_FED_SPELL), ikind = "food",
        name = (lv >= 60) and L["食物"] or L["食物（推荐5%经验食物）"],
        icon = WellFedIcon(),
        sub = L["缺少进食充分"],
        desc = L["吃任意食物获得进食充分效果，打怪经验 +5%"],
    }
end

local SLEEP_BAG_ITEM = 211527
local WELL_RESTED_SPELL = 429959
local wellRestedName = nil

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
    local seen = false
    if C_UnitAuras and C_UnitAuras.GetAuraDataByIndex then
        for i = 1, 40 do
            local ok, a = pcall(C_UnitAuras.GetAuraDataByIndex, "player", i, "HELPFUL")
            if not ok then return true, nil end
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
    end
    if not seen then return false, nil end
    return false, nil
end

local function SleepBagCdReady()
    local f = (C_Item and C_Item.GetItemCooldown) or GetItemCooldown
    if not f then return true end
    local ok, start, dur = pcall(f, SLEEP_BAG_ITEM)
    if not ok or type(start) ~= "number" or type(dur) ~= "number" then return true end
    if dur <= 0 then return true end
    local now = (GetTime and GetTime()) or 0
    return (start + dur - now) <= 0
end

local function SleepBagIcon()
    local f = GetItemIcon
    if f then
        local ok, ic = pcall(f, SLEEP_BAG_ITEM)
        if ok and ic then return ic end
    end
    return 133662
end

local function RestedRow(c)
    if not c.rested then return nil end
    if not OwnItem(SLEEP_BAG_ITEM) then return nil end
    local buffed, rem = WellRestedState()
    local sub = L["缺少精神饱满"]
    if buffed then
        if rem == nil or rem >= 1800 then return nil end
        if not SleepBagCdReady() then return nil end
        sub = L["精神饱满即将到期"]
    end
    return {
        id = SLEEP_BAG_ITEM, base = SLEEP_BAG_ITEM,
        ikey = ItemKey("rested", SLEEP_BAG_ITEM), ikind = "rested",
        name = L["使用舒适的睡袋"], icon = SleepBagIcon(),
        sub = sub,
        desc = L["在睡袋中休息至少一分钟，获得的经验值提高 1%，最多叠加 3 次"],
    }
end

local function PBuff(ctx)
    local c = CFG()
    local list = {}
    local fr = FoodRow(c)
    if fr then list[#list + 1] = fr end
    local rr = RestedRow(c)
    if rr then list[#list + 1] = rr end
    if #list == 0 then return nil end
    return { kind = "buff", n = #list, keys = {}, list = list, title = L["增益"] }
end

Z.Register("buff", PBuff)

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
        list[i] = {
            id = 700000 + i, base = 700000 + i,
            name = t[1], icon = "Interface\\GossipFrame\\AvailableQuestIcon",
            sub = string.format(L["%s · 可接等级 %d"], t[2], t[6]),
            desc = string.format("%s · %s %.0f,%.0f", t[2], t[3], t[4] + lap, t[5]),
            lvreq = t[6], can = t[7],
            disc = QDISC, discCol = t[7] and QDISC_CAN or QDISC_CANT,
            sym = t[7] and QSYM_CAN or QSYM_CANT,
            symCol = t[7] and QSYM_CANCOL or QSYM_CANTCOL,
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
    local order = { "collect", "turnin", "quest", "spell", "buff" }
    for i = 1, #order do
        local kind = order[i]
        local on = c[kind]
        if kind == "collect" then on = (c.book or c.bag or c.torch or c.banner) end
        if kind == "buff" then on = (c.food or c.rested) end
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
end

function Z.Unblock(key)
    if not key then return end
    CFG().blacklist[key] = nil
end

function Z.ClearBlock()
    local c = CFG()
    for k in pairs(c.blacklist) do c.blacklist[k] = nil end
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

local KIND_NAME = { collect = L["收集"], book = L["书籍"], turnin = L["书籍上交"], quest = L["任务"], spell = L["技能"], buff = L["增益"] }
function Z.KindName(kind)
    return KIND_NAME[kind] or L["条目"]
end

function Z.IconFor(kind, id)
    if kind == "book" or kind == "collect" or kind == "turnin" then return ItemIcon(id) end
    if kind == "quest" then return "Interface\\GossipFrame\\AvailableQuestIcon" end
    if kind == "rested" then
        local f = GetItemIcon
        if f then
            local ok, ic = pcall(f, id)
            if ok and ic then return ic end
        end
        return 133662
    end
    if kind == "spell" or kind == "food" then
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
    frame:SetScript("OnEvent", function(_, event)
        if event == "PLAYER_ENTERING_WORLD" then
            Z.Check("login", 0)
        elseif event == "UNIT_AURA" or event == "ITEM_COOLDOWN_UPDATE" then
            Z.ScheduleSoft()
        elseif event == "BAG_UPDATE_DELAYED" or event == "QUEST_LOG_UPDATE" then
            local EG = ns.ExploreModule
            if EG then EG._auto = nil end
            Z.RefreshSoft()
        elseif event == "PLAYER_REGEN_ENABLED" then
            if pending then
                pending = nil
                Z.Check("regen", 0)
            end
        else
            Z.OnZoneChanged()
        end
    end)
    if ns.ZoneOrb and ns.ZoneOrb.Init then ns.ZoneOrb.Init() end
    Z.Check("login", 0)
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
        print(head .. L["用法"] .. "： " .. SIM_USAGE)
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
            print(head .. L["用法"] .. "： /dfhint mode auto|badge|silent")
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
            print(head .. L["用法"] .. "： " .. SIM_USAGE)
            return
        end
        Z.SimSet(cur.book, cur.quest, cur.spell)
    else
        local a, b, c = s:match("^(%d+)%s*(%d*)%s*(%d*)$")
        if not a then
            print(head .. L["用法"] .. "： " .. SIM_USAGE)
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
    print(head .. L["关闭"] .. "： /dfhint off")
end

if type(SlashCmdList) == "table" then
    SLASH_DUNGEONSZONEHINT1 = "/dfhint"
    SLASH_DUNGEONSZONEHINT2 = L["/待办模拟"]
    SLASH_DUNGEONSZONEHINT3 = "/df模拟"
    SlashCmdList["DUNGEONSZONEHINT"] = function(msg)
        Z.SimCommand(msg)
    end
end
