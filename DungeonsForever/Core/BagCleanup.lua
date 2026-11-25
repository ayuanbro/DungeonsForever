local _, ns = ...

local L = ns.L or function(k) return k end

local BC = ns.BagCleanup or {}
ns.BagCleanup = BC

local function DB()
    local db = ns.DB and ns.DB()
    if type(db) ~= "table" then return { on = true, minFree = 10, confirm = true, keep = {} } end
    db.ui = db.ui or {}
    local b = db.ui.bagCleanup
    if type(b) ~= "table" then
        b = {}
        db.ui.bagCleanup = b
    end
    if b.on == nil then b.on = true end
    if tonumber(b.minFree) == nil then b.minFree = 10 end
    if b.confirm == nil then b.confirm = true end
    if type(b.keep) ~= "table" then b.keep = {} end
    if type(b.pos) ~= "table" then b.pos = {} end
    return b
end
BC.DB = DB

local function Con()
    return rawget(_G, "C_Container")
end

local function BagFn(k)
    local c = Con()
    if type(c) == "table" and type(c[k]) == "function" then return c[k] end
    return rawget(_G, k)
end

local function ItemInfoFn()
    return (type(C_Item) == "table" and C_Item.GetItemInfo) or rawget(_G, "GetItemInfo")
end

local function ItemUnitPrice(id)
    local f = ItemInfoFn()
    if type(f) ~= "function" then return nil end
    local ok, _, _, _, _, _, _, _, _, _, _, sell = pcall(f, id)
    if not ok then return nil end
    return tonumber(sell)
end

local function ItemMeta(id)
    local f = ItemInfoFn()
    if type(f) == "function" then
        local ok, nm, _, _, _, _, _, _, _, tex = pcall(f, id)
        if ok then return nm, tex end
    end
    return nil, nil
end

function BC.MoneyText(c)
    c = math.floor(tonumber(c) or 0)
    if c < 0 then c = 0 end
    local g = math.floor(c / 10000)
    local s = math.floor((c % 10000) / 100)
    local co = c % 100
    if g > 0 then return string.format("%d金%d银%02d铜", g, s, co) end
    if s > 0 then return string.format("%d银%02d铜", s, co) end
    return string.format("%d铜", co)
end

local cache = { t = 0, data = nil }
local TTL = 0.5

function BC.Scan()
    local b = DB()
    local free = 0
    local calc = BagFn("CalculateTotalNumberOfFreeBagSlots")
    if type(calc) == "function" then
        local ok, v = pcall(calc)
        if ok and tonumber(v) then free = math.floor(tonumber(v)) end
    end
    local numSlots = BagFn("GetContainerNumSlots")
    local getInfo = Con() and Con().GetContainerItemInfo
    local getQuest = Con() and Con().GetContainerItemQuestInfo
    local keep = b.keep
    local items = {}
    local totalSlots = 0
    local totalValue = 0
    local nb = tonumber(NUM_BAG_SLOTS) or 4
    if type(numSlots) == "function" and type(getInfo) == "function" then
        for bag = 0, nb do
            local okN, n = pcall(numSlots, bag)
            n = (okN and tonumber(n)) or 0
            totalSlots = totalSlots + n
            for slot = 1, n do
                local okI, info = pcall(getInfo, bag, slot)
                if okI and type(info) == "table" and info.itemID then
                    local id = info.itemID
                    if info.quality == 0 and not keep[id] and not info.isLocked then
                        local isQuest = false
                        if type(getQuest) == "function" then
                            local okQ, q = pcall(getQuest, bag, slot)
                            if okQ and type(q) == "table" and q.isQuestItem then isQuest = true end
                        end
                        if not isQuest then
                            local unit = ItemUnitPrice(id)
                            if unit ~= nil then
                                local cnt = tonumber(info.stackCount) or 1
                                local value = unit * cnt
                                items[#items + 1] = {
                                    bag = bag, slot = slot, id = id,
                                    name = info.itemName or tostring(id),
                                    count = cnt, unit = unit, value = value,
                                    icon = info.iconFileID or info.icon or 134400,
                                }
                                totalValue = totalValue + value
                            end
                        end
                    end
                end
            end
        end
    end
    table.sort(items, function(x, y)
        if x.value ~= y.value then return x.value < y.value end
        return tostring(x.name) < tostring(y.name)
    end)
    local data = { free = free, totalSlots = totalSlots, items = items, count = #items, totalValue = totalValue }
    cache.data = data
    cache.t = (GetTime and GetTime()) or 0
    return data
end

function BC.Get(force)
    local now = (GetTime and GetTime()) or 0
    if force or not cache.data or (now - cache.t) > TTL then return BC.Scan() end
    return cache.data
end

function BC.On()
    return DB().on ~= false
end

function BC.MinFree()
    return tonumber(DB().minFree) or 10
end

function BC.Active()
    if not BC.On() then return false end
    local d = BC.Get()
    return d.free <= BC.MinFree()
end

function BC.NextItem()
    local d = BC.Get()
    return d.items and d.items[1]
end

function BC.AllItems()
    return BC.Get().items or {}
end

function BC.WhiteList()
    local b = DB()
    local out = {}
    for id, v in pairs(b.keep) do
        if v then
            local nm, tex = ItemMeta(id)
            out[#out + 1] = { id = id, name = nm or string.format(L["物品 #%d"], id), icon = tex }
        end
    end
    table.sort(out, function(x, y) return tostring(x.name) < tostring(y.name) end)
    return out
end

local function RefreshBag()
    local O = ns.ZoneOrb
    if O and type(O.RefreshBag) == "function" then pcall(O.RefreshBag) end
end
BC.RefreshOrb = RefreshBag

local function RefreshUI()
    local UI = ns.BagCleanupUI
    if UI and type(UI.Refresh) == "function" then pcall(UI.Refresh) end
end

local function TooltipFor(row, it)
    if not (GameTooltip and row) then return end
    GameTooltip:SetOwner(row, "ANCHOR_RIGHT")
    local ok = false
    if GameTooltip.SetItemByID then
        local pok = pcall(GameTooltip.SetItemByID, GameTooltip, it.id)
        if pok then ok = (GameTooltip:NumLines() or 0) > 0 end
    end
    if not ok then
        GameTooltip:ClearLines()
        GameTooltip:AddLine(it.name, 1, 1, 1, true)
    end
    GameTooltip:AddLine(" ")
    GameTooltip:AddLine(string.format(L["按住 Shift 点击摧毁：%d %s，价值 %s"], it.count, it.name, BC.MoneyText(it.value)), 0.62, 0.62, 0.62, true)
    GameTooltip:AddLine(L["右键点击跳过此物品"], 0.62, 0.62, 0.62, true)
    GameTooltip:Show()
end

function BC.Card()
    if not BC.On() then return nil end
    local d = BC.Get()
    if d.free > BC.MinFree() then return nil end
    local card = {
        kind = "bagcleanup", bagcleanup = true,
        title = L["背包清理"],
        name = string.format(L["合计 %s"], BC.MoneyText(d.totalValue)),
        chipText = string.format(L["余%d"], d.free),
    }
    local it = d.items[1]
    if it then
        card.icon = it.icon
        card.text = string.format(L["%s ×%d · %s"], it.name, it.count, BC.MoneyText(it.value))
        card.btn = L["摧毁这一件"]
        card.onClick = function() BC.DestroyCheapest() end
        card.btn2 = L["跳过"]
        card.onClick2 = function() BC.SkipCheapest() end
        card.btn3 = L["名单管理"]
        card.onClick3 = function() BC.OpenManage("destroy") end
        card.tipFn = function(row) TooltipFor(row, it) end
    else
        card.text = L["没有可摧毁的灰色物品"]
        card.btn3 = L["名单管理"]
        card.onClick3 = function() BC.OpenManage("white") end
    end
    return { card }
end

local function DeleteSlot(bag, slot, wantId)
    local getInfo = Con() and Con().GetContainerItemInfo
    if type(getInfo) ~= "function" then return false end
    local okI, info = pcall(getInfo, bag, slot)
    if not (okI and type(info) == "table" and info.itemID) then return false end
    if wantId and info.itemID ~= wantId then return false end
    if CursorHasItem and CursorHasItem() and ClearCursor then pcall(ClearCursor) end
    local pick = BagFn("PickupContainerItem")
    if type(pick) ~= "function" then return false end
    pcall(pick, bag, slot)
    if DeleteCursorItem then pcall(DeleteCursorItem) end
    if CursorHasItem and CursorHasItem() and ClearCursor then pcall(ClearCursor) end
    return true
end

function BC.DestroyOne(bag, slot, wantId)
    if type(InCombatLockdown) == "function" and InCombatLockdown() then return false end
    local ok = DeleteSlot(bag, slot, wantId)
    BC.Get(true)
    RefreshBag()
    return ok
end

function BC.DestroyCheapest()
    local it = BC.NextItem()
    if not it then return false end
    return BC.DestroyOne(it.bag, it.slot, it.id)
end

function BC.DestroyAll(done)
    if type(InCombatLockdown) == "function" and InCombatLockdown() then
        if done then pcall(done) end
        return
    end
    local d = BC.Get(true)
    local list = {}
    for _, it in ipairs(d.items) do
        list[#list + 1] = { bag = it.bag, slot = it.slot, id = it.id }
    end
    local i = 0
    local function finish()
        BC.Get(true)
        RefreshBag()
        RefreshUI()
        if done then pcall(done) end
    end
    local function step()
        i = i + 1
        local e = list[i]
        if not e then finish() return end
        if type(InCombatLockdown) == "function" and InCombatLockdown() then finish() return end
        DeleteSlot(e.bag, e.slot, e.id)
        if type(C_Timer) == "table" and type(C_Timer.After) == "function" then
            C_Timer.After(0.08, step)
        else
            step()
        end
    end
    step()
end

function BC.SkipCheapest()
    local it = BC.NextItem()
    if not it then return false end
    BC.Keep(it.id)
    return true
end

function BC.Keep(id)
    if not id then return end
    DB().keep[id] = true
    BC.Get(true)
    RefreshBag()
    RefreshUI()
end

function BC.RemoveKeep(id)
    if not id then return end
    DB().keep[id] = nil
    BC.Get(true)
    RefreshBag()
    RefreshUI()
end

function BC.ClearKeep()
    local b = DB()
    b.keep = {}
    BC.Get(true)
    RefreshBag()
    RefreshUI()
end

function BC.KeepCount()
    local n = 0
    for _ in pairs(DB().keep) do n = n + 1 end
    return n
end

function BC.OpenManage(page)
    local UI = ns.BagCleanupUI
    if UI and type(UI.Open) == "function" then UI.Open(page) end
end

function BC.SetOn(v)
    DB().on = v and true or false
    BC.Get(true)
    RefreshBag()
end

function BC.SetMinFree(v)
    local n = tonumber(v)
    if not n or n < 0 then n = 10 end
    DB().minFree = n
    BC.Get(true)
    RefreshBag()
end

function BC.ToggleOn()
    BC.SetOn(not BC.On())
    return BC.On()
end

local bagQueued = false
local function DoBagScan()
    BC.Get(true)
    RefreshBag()
    RefreshUI()
end
local function ScheduleBagScan()
    if bagQueued then return end
    bagQueued = true
    if type(C_Timer) == "table" and type(C_Timer.After) == "function" then
        C_Timer.After(0.3, function() bagQueued = false; DoBagScan() end)
    else
        bagQueued = false
        DoBagScan()
    end
end

if not BC.__drv then
    local drv = CreateFrame("Frame")
    drv:RegisterEvent("BAG_UPDATE_DELAYED")
    drv:RegisterEvent("PLAYER_ENTERING_WORLD")
    drv:RegisterEvent("GET_ITEM_INFO_RECEIVED")
    drv:SetScript("OnEvent", function() ScheduleBagScan() end)
    BC.__drv = drv
end
