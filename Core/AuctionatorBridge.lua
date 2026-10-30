local _, ns = ...

if not ns.LoadForeverPages then return end

local L = ns.L

local AB = {}
ns.AuctionBridge = AB

local CALLER = "DungeonsForever"

local format = string.format

local function Say(msg)
    local frame = DEFAULT_CHAT_FRAME
    if frame and frame.AddMessage then
        frame:AddMessage("|cffffd100" .. msg .. "|r")
    end
end

function AB.Available()
    return type(Auctionator) == "table"
        and type(Auctionator.API) == "table"
        and type(Auctionator.API.v1) == "table"
        and type(Auctionator.API.v1.CreateShoppingList) == "function"
end

function AB.ListName(profName)
    return format(L["[DF] %s购物清单"], profName or "?")
end

function AB.SearchString(name, need)
    local quoted = "\"" .. (name or "") .. "\""
    local hasNeed = (type(need) == "number" and need > 0) and true or false
    if AB.Available() and type(Auctionator.API.v1.ConvertToSearchString) == "function" then
        local term = { searchString = name, isExact = true }
        if hasNeed then term.quantity = need end
        local ok, s = pcall(Auctionator.API.v1.ConvertToSearchString, CALLER, term)
        if ok and type(s) == "string" and s ~= "" then return s end
    end
    if hasNeed then
        return strjoin(";", quoted, "", "", "", "", "", "", "", "", "", "", "#", "", tostring(need))
    end
    return quoted
end

function AB.Import(listName, items)
    if not AB.Available() then return false, "Auctionator not available" end
    local strings = {}
    for _, e in ipairs(items) do
        if type(e) == "table" and type(e.name) == "string" and e.name ~= "" then
            strings[#strings + 1] = AB.SearchString(e.name, e.need)
        end
    end
    local ok, err = pcall(Auctionator.API.v1.CreateShoppingList, CALLER, listName, strings)
    if ok then return true end
    return false, err
end

function AB.ExportString(listName, items)
    local parts = { listName }
    for _, e in ipairs(items) do
        if type(e) == "table" and type(e.name) == "string" and e.name ~= "" then
            parts[#parts + 1] = AB.SearchString(e.name, e.need)
        end
    end
    return table.concat(parts, "^")
end

local POPUP = "DungeonsForever_AuctionImport"
local pendingImportText = ""
function AB.ShowCopy(text)
    pendingImportText = text or ""
    if not StaticPopupDialogs[POPUP] then
        StaticPopupDialogs[POPUP] = {
            text = L["未检测到 Auctionator，请复制以下导入串"],
            button1 = L["关闭"],
            timeout = 0,
            whileDead = true,
            hideOnEscape = true,
            preferredIndex = 3,
            hasEditBox = true,
            editBoxWidth = 320,
            OnShow = function(self)
                local edit = self.EditBox or self.editBox
                edit:SetText(pendingImportText)
                edit:HighlightText()
                edit:SetFocus()
            end,
            EditBoxOnEnterPressed = function(self)
                self:GetParent():Hide()
            end,
            EditBoxOnEscapePressed = function(self)
                self:GetParent():Hide()
            end,
        }
    end
    StaticPopup_Show(POPUP)
end

function AB.DoImport(profName, items)
    if not (type(items) == "table" and #items > 0) then
        Say(L["购物清单为空，没有可导入的物品"])
        return
    end
    local listName = AB.ListName(profName)
    if AB.Available() then
        local ok, err = AB.Import(listName, items)
        if ok then
            Say(format(L["已导入 Auctionator：%s（共 %d 种）"], listName, #items))
        else
            Say(L["导入失败："] .. tostring(err or "?"))
        end
        return
    end
    AB.ShowCopy(AB.ExportString(listName, items))
    Say(L["未检测到 Auctionator，请在 Auctionator → 购物清单 → 导入 中粘贴"])
end

-- A quantity is a short-lived observation, never Auctionator's daily maximum.
local SUPPLY_MAX_AGE  = ns.ProfRouteAuto.MaxStaleSeconds()

local supplyRevision = 0
local supplyListeners = {}
local function MarketKey()
    return tostring(GetRealmName and GetRealmName() or "") .. ":"
        .. tostring(UnitFactionGroup and UnitFactionGroup("player") or "")
end
local function ObserverKey()
    return tostring(UnitGUID and UnitGUID("player") or UnitName and UnitName("player") or "")
end
function AB.OnChanged(fn)
    if type(fn)=="function" then supplyListeners[#supplyListeners+1]=fn end
end
local function SupplyChanged(id)
    supplyRevision=supplyRevision+1
    for _,fn in ipairs(supplyListeners) do pcall(fn,id,"supply") end
end

local function ProfDB()
    return DungeonsForeverDB and DungeonsForeverDB.prof
end

-- A complete market snapshot also proves zero for IDs absent from its rows.
-- Store one compact batch rather than duplicating its metadata on every item.
local function SupplyRecord(id)
    local db=ProfDB()
    local batch=db and db.auctionFullScan
    if type(batch)~="table" or batch.v~=1 or type(batch.items)~="table" then return nil end
    local item=batch.items[id]
    if item~=nil and type(item)~="table" then
        return {mk=batch.mk,ob=batch.ob,failure="incomplete"}
    end
    if not item and batch.c~=true then
        return {mk=batch.mk,ob=batch.ob,failure="incomplete"}
    end
    return {q=item and item.q or 0,p=item and item.p,t=batch.t,mk=batch.mk,ob=batch.ob,
        c=batch.c==true and not (item and item.failure),ox=true,s="client-auction-results",v=2,
        failure=item and item.failure or batch.c~=true and "incomplete" or nil,
        method="auctionator-full-scan"}
end

function AB.SupplyRevision()
    return supplyRevision
end

function AB.GetAuctionSupplyStatus(id)
    if type(id) ~= "number" or id <= 0 then return nil end
    local rec = SupplyRecord(id)
    if type(rec) ~= "table" then return "unknown" end
    local now = time and time() or 0
    local qty, stamp = tonumber(rec.q), tonumber(rec.t)
    if rec.mk ~= MarketKey() or rec.ob ~= ObserverKey() then return "unverified" end
    if rec.failure then return rec.failure end
    if rec.c ~= true or rec.ox ~= true or rec.s ~= "client-auction-results" then return "incomplete" end
    if not qty or qty < 0 or qty == math.huge or qty ~= math.floor(qty) then return "incomplete" end
    if not stamp or stamp~=stamp or stamp <= 0 or stamp > now or now-stamp > SUPPLY_MAX_AGE then return "expired" end
    return "verified"
end

function AB.GetAuctionSupply(id, live)
    if AB.GetAuctionSupplyStatus(id) ~= "verified" then return nil end
    local rec = SupplyRecord(id)
    return {
        quantity = tonumber(rec.q),
        observedAt = tonumber(rec.t) or 0,
        complete = rec.c == true,
        ownerExcluded = rec.ox == true,
        source = rec.s or "client-auction-results",
        market = tonumber(rec.p),
        marketKey = rec.mk,
        observer = rec.ob,
        method = rec.method,
        schemaVersion = rec.v,
        expiresAt = rec.t + SUPPLY_MAX_AGE,
    }
end

function AB.SupplyFresh(id)
    return AB.GetAuctionSupply(id)
end

function AB.SupplyEstimate(id)
    if type(id) ~= "number" or id <= 0 then return nil end
    local A = Auctionator
    if type(A) ~= "table" or type(A.Database) ~= "table" then return nil end
    local db = A.Database.db
    if type(db) ~= "table" then return nil end
    local entry = db[tostring(id)]
    if type(entry) ~= "table" then return nil end
    local scanDay = nil
    if type(A.Constants) == "table" and tonumber(A.Constants.SCAN_DAY_0) then
        scanDay = math.floor(((time and time() or 0) - A.Constants.SCAN_DAY_0) / 86400)
    end
    local qty, day = nil, nil
    if type(entry.a) == "table" then
        if scanDay and entry.a[tostring(scanDay)] then
            qty, day = tonumber(entry.a[tostring(scanDay)]), scanDay
        else
            for d, v in pairs(entry.a) do
                local dv = tonumber(d)
                if dv and (day == nil or dv > day) and tonumber(v) then
                    qty, day = tonumber(v), dv
                end
            end
        end
    end
    if qty == nil then return nil end
    local day0=A.Constants and A.Constants.SCAN_DAY_0
    local observedAt = (day and day0) and day * 86400 + day0 or nil
    return {
        quantity = qty,
        observedAt = observedAt or 0,
        complete = false,
        ownerExcluded = false,
        source = "auctionator-update",
        market = tonumber(entry.m),
    }
end

function AB.GetAuctionSupplyHistory(id)
    if type(id) ~= "number" or id <= 0 then return nil end
    local A = Auctionator
    if type(A) ~= "table" or type(A.Database) ~= "table" then return nil end
    local db = A.Database
    if type(db) ~= "table" or type(db.GetPriceHistory) ~= "function" then return nil end
    local ok, rows = pcall(db.GetPriceHistory, db, tostring(id))
    if not ok or type(rows) ~= "table" then return nil end
    local best, newest
    for _, row in ipairs(rows) do
        if type(row) == "table" then
            local day = tonumber(row.rawDay)
            local avail = tonumber(row.available)
            if avail and avail >= 0 and day and (newest == nil or day > newest) then
                best, newest = row, day
            end
        end
    end
    if not best or newest == nil then return nil end
    local day0 = type(A.Constants) == "table" and tonumber(A.Constants.SCAN_DAY_0) or nil
    return {
        quantity = tonumber(best.available),
        observedAt = day0 and (newest * 86400 + day0) or 0,
        complete = false,
        source = "auctionator-history",
    }
end

function AB.GetAuctionPriceObservedAt(id)
    if type(id) ~= "number" or id <= 0 then return nil end
    local rec = SupplyRecord(id)
    if type(rec) == "table" and rec.mk==MarketKey() and tonumber(rec.p) and rec.p>0
        and tonumber(rec.t) and rec.t>0 then return tonumber(rec.t) end
    local est = AB.SupplyEstimate(id)
    if type(est) == "table" and tonumber(est.observedAt) and est.observedAt > 0 then
        return tonumber(est.observedAt)
    end
    return nil
end

-- Auctionator 341 emits the raw get-all / replicate rows at ScanComplete.
-- Its saved Database.a field is a daily maximum, not the latest quantity.
-- Observe the scan that Auctionator already performs; never send a query here.
local fullBus,fullListener,fullEvents,fullRead,fullTimer
local fullGeneration=0
local fullState={status="unavailable"}
local function WholeNumber(n)
    return type(n)=="number" and n>=0 and n<math.huge and n==math.floor(n)
end
local function StopFullImport()
    fullGeneration=fullGeneration+1
    if fullTimer then fullTimer:Cancel();fullTimer=nil end
    fullRead=nil
end
function AB.FullScanStatus() return fullState end

local function ExpectedFullRows(scan)
    if scan.expected~=nil then return end
    local ok,count,total
    if scan.modern then
        local fn=C_AuctionHouse and C_AuctionHouse.GetNumReplicateItems
        if fn then ok,count=pcall(fn) end
    elseif GetNumAuctionItems then ok,count,total=pcall(GetNumAuctionItems,"list") end
    if ok and WholeNumber(count) and (total==nil or total==count) then
        scan.expected=count;scan.observedAt=time and time() or scan.startedAt
    end
end
local function FullRow(scan,row)
    if type(row)~="table" then scan.complete=false;return end
    local info=row.auctionInfo or row.replicateInfo
    if type(info)~="table" then scan.complete=false;return end
    local linkID=type(row.itemLink)=="string" and tonumber(row.itemLink:match("item:(%d+)"))
    local id=info[17]
    if not WholeNumber(id) or id==0 then id=linkID end
    if not WholeNumber(id) or id==0 or linkID and linkID~=id then scan.complete=false;return end
    local item=scan.items[id]
    if not item then item={q=0};scan.items[id]=item end
    local qty=info[3]
    local classic=info[17]~=nil or info[18]~=nil or row.replicateInfo~=nil
        or type(info[14])=="string" or type(info[15])=="string"
    local buyout=info[classic and 10 or 9]
    if not WholeNumber(qty) or type(buyout)~="number" or buyout~=buyout
        or buyout<0 or buyout==math.huge or info[18]==false then item.failure="incomplete";return end
    -- Bid-only and sold rows contribute no immediately purchasable stock.
    if qty==0 or buyout==0 then return end
    local owner=info[classic and 15 or 12]
    if classic and (type(owner)~="string" or owner=="") then owner=info[14] end
    if type(owner)~="string" or owner=="" then item.failure="incomplete";return end
    local player=UnitName and UnitName("player")
    if owner==player or owner:match("^[^-]+") == player then return end
    -- 按数量加权计算平均单价
    local oldQty = item.q
    local newQty = oldQty + qty

    item.p = ((item.p or 0) * oldQty + buyout) / newQty
    item.q = newQty
end

local function ImportFullRows(scan,rows)
    if type(rows)~="table" or scan.expected==nil then
        fullState={status="incomplete"};fullRead=nil;return
    end
    scan.items={};scan.complete=true;scan.index=1
    local rowCount=0
    for index in pairs(rows) do
        if not WholeNumber(index) or index<1 then scan.complete=false end
        rowCount=rowCount+1
    end
    if rowCount~=scan.expected then scan.complete=false end
    fullState={status="processing",done=0,total=scan.expected}
    local generation=fullGeneration
    local function step()
        fullTimer=nil
        if generation~=fullGeneration then return end
        if scan.mk~=MarketKey() or scan.ob~=ObserverKey() then
            fullState={status="unverified"};fullRead=nil;return
        end
        -- Missing raw rows are unknown. Never infer an empty market from them.
        local last=math.min(scan.index+249,scan.expected)
        for index=scan.index,last do FullRow(scan,rows[index]) end
        scan.index=last+1;fullState.done=last
        if scan.index<=scan.expected then
            if C_Timer and C_Timer.NewTimer then fullTimer=C_Timer.NewTimer(0,step)
            else fullState={status="unavailable"};fullRead=nil end
            return
        end
        local db=ProfDB()
        if db then
            db.auctionFullScan={items=scan.items,t=scan.observedAt,mk=scan.mk,ob=scan.ob,
                c=scan.complete,v=1}
            fullState.status=scan.complete and "complete" or "incomplete"
            fullState.observedAt=scan.observedAt
            fullRead=nil
            SupplyChanged(nil)
        else fullState={status="unavailable"};fullRead=nil end
    end
    if C_Timer and C_Timer.NewTimer then fullTimer=C_Timer.NewTimer(0,step)
    else fullState={status="unavailable"};fullRead=nil end
end

function AB.ConnectAuctionatorStock()
    local A=Auctionator
    local bus=type(A)=="table" and A.EventBus
    local ev=type(A)=="table" and A.FullScan and A.FullScan.Events
    if type(bus)~="table" or type(bus.Register)~="function" or type(ev)~="table"
        or type(ev.ScanStart)~="string" or type(ev.ScanComplete)~="string"
        or type(ev.ScanProgress)~="string" or type(ev.ScanFailed)~="string" then return false end
    if fullBus==bus then return true end
    if fullBus and fullBus.Unregister then pcall(fullBus.Unregister,fullBus,fullListener,fullEvents) end
    StopFullImport()
    local listener={}
    function listener:ReceiveEvent(event,data)
        if event==ev.ScanStart then
            StopFullImport()
            fullRead={startedAt=time and time() or 0,mk=MarketKey(),ob=ObserverKey(),
                modern=ev.ScanStart=="replicate_scan_start"}
            fullState={status="scanning"}
        elseif event==ev.ScanProgress and fullRead and type(data)=="number" and data>=0.2 then
            ExpectedFullRows(fullRead)
        elseif event==ev.ScanFailed then
            StopFullImport();fullState={status="failed"}
        elseif event==ev.ScanComplete and fullRead and fullState.status=="scanning" then
            -- Capture only this scan's raw payload, never the historical DB or
            -- the current query list (another search may already have started).
            ImportFullRows(fullRead,data)
        end
    end
    local events={ev.ScanStart,ev.ScanProgress,ev.ScanFailed,ev.ScanComplete}
    local ok=pcall(bus.Register,bus,listener,events)
    if not ok then return false end
    fullBus,fullListener,fullEvents=bus,listener,events
    fullState={status="ready"}
    return true
end

local function InitializeAuctionatorStock()
    AB.ConnectAuctionatorStock()
    local frame=CreateFrame and CreateFrame("Frame")
    if not frame then return end
    frame:RegisterEvent("ADDON_LOADED");frame:RegisterEvent("PLAYER_LOGIN")
    frame:SetScript("OnEvent",function(_,event,name)
        if event=="PLAYER_LOGIN" or name=="Auctionator" then AB.ConnectAuctionatorStock() end
    end)
end

function AB.ReplicateScanEnabled()
    local a = _G.Auctionator
    local cfg = type(a) == "table" and a.Config

    if type(cfg) ~= "table"
        or type(cfg.Get) ~= "function"
        or type(cfg.Options) ~= "table"
        or type(cfg.Options.REPLICATE_SCAN) ~= "string" then
        return nil
    end

    local ok, enabled = pcall(
        cfg.Get,
        cfg.Options.REPLICATE_SCAN
    )

    if ok and type(enabled) == "boolean" then
        return enabled
    end

    return nil
end

function AB.ReplicateScanReady()
    local enabled = AB.ReplicateScanEnabled()

    -- 无法判断设置：仅警告，不新增强制拦截
    if enabled == nil then
        return nil, "replicateModeUnknown"
    end

    local db = ProfDB()

    if enabled == false then
        if db and time then
            db.replicateRequiredAfter = math.max(
                db.replicateRequiredAfter or 0,
                time()
            )
        end
        return false, "replicateModeDisabled"
    end

    local batch = db and db.auctionFullScan
    local now = time and time()

    -- 必须存在本角色、本服务器的有效复制扫描结果
    if type(batch) ~= "table"
        or batch.v ~= 1
        or batch.c ~= true
        or type(batch.items) ~= "table"
        or batch.mk ~= MarketKey()
        or batch.ob ~= ObserverKey()
        or type(batch.t) ~= "number"
        or not now
        or batch.t > now
        or now - batch.t > SUPPLY_MAX_AGE then
        return false, "replicateScanRequired"
    end

    -- 摘要扫描不能替代复制扫描
    local a = _G.Auctionator
    local saved = a and a.SavedState
    local lastSummary = saved
        and saved.TimeOfLastBrowseScan or 0

    local requiredAfter = math.max(
        db.replicateRequiredAfter or 0,
        type(lastSummary) == "number" and lastSummary or 0
    )

    if batch.t <= requiredAfter then
        return false, "replicateScanRequired"
    end

    return true
end

if ns.Init then ns.Init(InitializeAuctionatorStock) else InitializeAuctionatorStock() end
