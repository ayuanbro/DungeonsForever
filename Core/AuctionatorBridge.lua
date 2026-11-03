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
                ns.SkinPopupFont(self)
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

local SUPPLY_MAX_AGE = ns.ProfRouteAuto.MaxAuctionSupplyAgeSeconds()
local SNAPSHOT_VERSION = 3
local function WholeNumber(n)
    return type(n)=="number" and n>=0 and n<math.huge and n==math.floor(n)
end
local function ScanDB()
    if type(DungeonsForeverDB)~="table" then DungeonsForeverDB={} end
    if type(DungeonsForeverDB.prof)~="table" then DungeonsForeverDB.prof={} end
    return DungeonsForeverDB.prof
end

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

local fullBatch,fullFailure,fullExpiryTimer,fullExpiryToken,replicateState
local restoredSnapshot=false
local function ReleaseFullBatch(reason,observation,snapshotStatus)
    if fullExpiryTimer then fullExpiryTimer:Cancel();fullExpiryTimer=nil end
    fullExpiryToken=nil
    local batch=observation or fullBatch or fullFailure
    fullFailure={v=SNAPSHOT_VERSION,failure=reason,snapshotStatus=snapshotStatus}
    if type(batch)=="table" then
        fullFailure.mk,fullFailure.ob=batch.mk,batch.ob
        if WholeNumber(batch.t) and batch.t>0 then fullFailure.t=batch.t end
    end
    fullBatch=nil
    ScanDB().auctionFullScan=fullFailure
end
local function FullBatchFailure(batch)
    if batch.v~=SNAPSHOT_VERSION or batch.c~=true or type(batch.items)~="table" then return "incomplete" end
    local stamp=batch.t;local now=time and time() or 0
    if not WholeNumber(stamp) or stamp<=0 or stamp>now then return "incomplete" end
    if now-stamp>SUPPLY_MAX_AGE then return "expired" end
    if batch.mk~=MarketKey() or batch.ob~=ObserverKey() then return "unverified" end
end


local function ValidSavedBatch(batch)
    local now=time and time() or 0
    if type(batch)~="table" or batch.v~=SNAPSHOT_VERSION or batch.c~=true
        or batch.s~="client-auction-results" or batch.ox~=true
        or type(batch.mk)~="string" or batch.mk=="" or type(batch.ob)~="string" or batch.ob==""
        or not WholeNumber(batch.t) or batch.t<=0 or batch.t>now
        or not WholeNumber(batch.completedAt) or batch.completedAt<batch.t or batch.completedAt>now
        or not WholeNumber(batch.expected) or batch.received~=batch.expected or type(batch.items)~="table" then return false end
    local count=0
    for id,item in pairs(batch.items) do
        if not WholeNumber(id) or id==0 or type(item)~="table" or not WholeNumber(item.q)
            or item.failure~=nil and item.failure~="incomplete"
            or item.p~=nil and (type(item.p)~="number" or item.p~=item.p or item.p<=0 or item.p==math.huge)
            or item.q>0 and item.p==nil then return false end
        count=count+1
    end
    return count<=batch.expected
end


function AB.FullScanSnapshotStatus()
    local batch=fullBatch
    local failure=batch and FullBatchFailure(batch)
    if failure and failure~="unverified" then ReleaseFullBatch(failure);batch=nil end
    local meta=batch or fullFailure
    local status=batch and (failure=="unverified" and "mismatch" or "available")
        or meta and (meta.failure=="expired" and "expired" or meta.snapshotStatus=="missing" and "missing" or "invalid") or "missing"
    return {status=status,observedAt=meta and meta.t,
        expiresAt=meta and meta.t and meta.t+SUPPLY_MAX_AGE,
        restored=restoredSnapshot,completedAt=batch and batch.completedAt}
end

local function SupplyRecord(id)
    local batch=fullBatch
    if batch then
        local failure=FullBatchFailure(batch)
        if failure=="unverified" then return {mk=batch.mk,ob=batch.ob,failure=failure} end
        if failure then ReleaseFullBatch(failure);batch=nil end
    end
    if not batch then return fullFailure end
    if AB.ReplicateScanReady and AB.ReplicateScanReady()~=true then
        return fullFailure or {mk=batch.mk,ob=batch.ob,failure="unverified"}
    end
    local item=batch.items[id]
    if item~=nil and type(item)~="table" then
        return {mk=batch.mk,ob=batch.ob,failure="incomplete"}
    end
    if not item and batch.c~=true then
        return {mk=batch.mk,ob=batch.ob,failure="incomplete"}
    end
    return {q=item and item.q or 0,p=item and item.p,t=batch.t,mk=batch.mk,ob=batch.ob,
        c=batch.c==true and not (item and item.failure),ox=true,s="client-auction-results",v=SNAPSHOT_VERSION,
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
    if rec.failure then return rec.failure end
    if rec.mk ~= MarketKey() or rec.ob ~= ObserverKey() then return "unverified" end
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

local fullBus,fullListener,fullEvents,fullRead,fullTimer
local fullGeneration=0
local fullState={status="unavailable"}
local function StopFullImport()
    fullGeneration=fullGeneration+1
    if fullTimer then fullTimer:Cancel();fullTimer=nil end
    fullRead=nil
end
local function ScheduleFullExpiry()
    if fullExpiryTimer then fullExpiryTimer:Cancel();fullExpiryTimer=nil end
    if not fullBatch then return end
    local failure=FullBatchFailure(fullBatch)
    if failure and failure~="unverified" then ReleaseFullBatch(failure);return end
    if not (C_Timer and C_Timer.NewTimer) then return end
    local token={};fullExpiryToken=token
    fullExpiryTimer=C_Timer.NewTimer(math.max(1,fullBatch.t+SUPPLY_MAX_AGE+1-(time and time() or 0)),function()
        if fullExpiryToken~=token then return end
        fullExpiryTimer=nil
        if not fullBatch then return end
        local failure=FullBatchFailure(fullBatch)
        if failure and failure~="unverified" then ReleaseFullBatch(failure);SupplyChanged(nil)
        else ScheduleFullExpiry() end
    end)
end
function AB.FullScanStatus() return fullState end
local function ScanStatusChanged()
    for _,fn in ipairs(supplyListeners) do pcall(fn,nil,"scan-status") end
end
local function ImportFailed(status)
    StopFullImport();fullState={status=status}
    if not fullBatch and not fullFailure then ReleaseFullBatch("incomplete",nil,"missing") end
    ScanStatusChanged()
end

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
    if qty==0 or buyout==0 then return end
    local owner=info[classic and 15 or 12]
    if classic and (type(owner)~="string" or owner=="") then owner=info[14] end
    if type(owner)~="string" or owner=="" then item.failure="incomplete";return end
    local player=UnitName and UnitName("player")
    if owner==player or owner:match("^[^-]+") == player then return end
    local oldQty = item.q
    local newQty = oldQty + qty

    item.p = ((item.p or 0) * oldQty + buyout) / newQty
    item.q = newQty
end

local function ImportFullRows(scan,rows)
    if type(rows)~="table" or scan.expected==nil then
        ImportFailed("incomplete");return
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
        if generation~=fullGeneration then return end
        fullTimer=nil
        if scan.mk~=MarketKey() or scan.ob~=ObserverKey() then
            ImportFailed("unverified");return
        end
        local last=math.min(scan.index+249,scan.expected)
        for index=scan.index,last do FullRow(scan,rows[index]) end
        scan.index=last+1;fullState.done=last
        if scan.index<=scan.expected then
            if C_Timer and C_Timer.NewTimer then fullTimer=C_Timer.NewTimer(0,step)
            else ImportFailed("unavailable") end
            return
        end
        local enabled,mode=AB.ObserveReplicateMode()

        if enabled~=true or not mode then return end
        if mode.generation~=scan.modeGeneration or mode.scanSerial~=scan.scanSerial then
            ImportFailed("unverified");return
        end
        if not scan.complete then ImportFailed("incomplete");return end
        local candidate={items=scan.items,t=scan.observedAt,mk=scan.mk,ob=scan.ob,
            c=true,v=SNAPSHOT_VERSION,s="client-auction-results",ox=true,
            completedAt=time and time() or scan.observedAt,expected=scan.expected,received=rowCount}
        if not ValidSavedBatch(candidate) then ImportFailed("incomplete");return end
        fullBatch=candidate
        fullFailure=nil
        restoredSnapshot=false
        ScanDB().auctionFullScan=fullBatch
        ScheduleFullExpiry()
        fullState.status=scan.complete and "complete" or "incomplete"
        fullState.observedAt=scan.observedAt
        fullRead=nil
        SupplyChanged(nil)
    end
    if C_Timer and C_Timer.NewTimer then fullTimer=C_Timer.NewTimer(0,step)
    else ImportFailed("unavailable") end
end

local function DisconnectFullScan()
    if fullBus and fullBus.Unregister then pcall(fullBus.Unregister,fullBus,fullListener,fullEvents) end
    fullBus,fullListener,fullEvents=nil,nil,nil
    StopFullImport()
end

function AB.ConnectAuctionatorStock()
    local enabled=AB.ReplicateScanEnabled()
    if enabled~=true then
        if fullBus or fullRead or fullTimer then DisconnectFullScan() end
        fullState={status=enabled==false and "summary" or "unavailable"}
        return false
    end
    local A=Auctionator
    local bus=type(A)=="table" and A.EventBus
    local ev=type(A)=="table" and A.FullScan and A.FullScan.Events
    if type(bus)~="table" or type(bus.Register)~="function" or type(ev)~="table"
        or type(ev.ScanStart)~="string" or type(ev.ScanComplete)~="string"
        or type(ev.ScanProgress)~="string" or type(ev.ScanFailed)~="string" then return false end
    if fullBus==bus then return true end
    DisconnectFullScan()
    local listener={}
    function listener:ReceiveEvent(event,data)
        if self~=fullListener then return end
        local enabled,mode=AB.ObserveReplicateMode()
        if enabled~=true or self~=fullListener then return end
        if event==ev.ScanStart then
            StopFullImport()
            mode.scanSerial=mode.scanSerial+1
            fullRead={startedAt=time and time() or 0,mk=MarketKey(),ob=ObserverKey(),
                modern=ev.ScanStart=="replicate_scan_start",
                modeGeneration=mode.generation,scanSerial=mode.scanSerial}
            fullState={status="scanning"}
            ScanStatusChanged()
        elseif event==ev.ScanProgress and fullRead and type(data)=="number" and data>=0.2 then
            ExpectedFullRows(fullRead)
        elseif event==ev.ScanFailed then
            ImportFailed("failed")
        elseif event==ev.ScanComplete and fullRead and fullState.status=="scanning" then
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
    local db=ScanDB()
    db.auctionReplicateGate=nil;db.replicateRequiredAfter=nil
    local saved=db.auctionFullScan
    if saved~=nil then
        restoredSnapshot=true
        if ValidSavedBatch(saved) then
            fullBatch=saved;ScheduleFullExpiry()
        elseif type(saved)=="table" and saved.v==SNAPSHOT_VERSION and saved.items==nil
            and saved.failure=="incomplete" and saved.snapshotStatus=="missing" then
            fullFailure=saved
        elseif type(saved)=="table" and saved.v==SNAPSHOT_VERSION and saved.items==nil
            and saved.failure=="expired" and WholeNumber(saved.t) and saved.t>0
            and (time and time() or 0)-saved.t>SUPPLY_MAX_AGE then
            fullFailure=saved
        else ReleaseFullBatch("incomplete") end
    end
    AB.ConnectAuctionatorStock()
    AB.ObserveReplicateMode()
    AB.HookReplicateModeSetting()
    local frame=CreateFrame and CreateFrame("Frame")
    if not frame then return end
    frame:RegisterEvent("ADDON_LOADED");frame:RegisterEvent("PLAYER_LOGIN")
    frame:SetScript("OnEvent",function(_,event,name)
        if event=="PLAYER_LOGIN" or name=="Auctionator" then
            AB.ConnectAuctionatorStock()
            AB.ObserveReplicateMode()
            AB.HookReplicateModeSetting()
        end
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

local hookedModeConfig

function AB.ObserveReplicateMode()
    local enabled=AB.ReplicateScanEnabled()
    if enabled==nil then AB.ConnectAuctionatorStock();return nil,nil end
    local state=replicateState
    local changed=false
    if not state then
        state={enabled=enabled,generation=1,scanSerial=0}
        replicateState=state
    elseif state.enabled~=enabled then
        state.enabled=enabled
        state.generation=state.generation+1
        StopFullImport()
        fullState={status="mode-changed"}
        changed=true
    end
    AB.ConnectAuctionatorStock()
    if changed then
        ScanStatusChanged()
        for _,fn in ipairs(supplyListeners) do pcall(fn,nil,"replicate-mode") end
    end
    return enabled,state
end

function AB.ReplicateScanReady()
    if not ns.IsForever then return true end
    if AB.FullScanSnapshotStatus().status=="available" then return true end
    local enabled,state=AB.ObserveReplicateMode()
    if enabled==nil then return nil,"replicateModeUnknown" end
    if not enabled then return false,"replicateModeDisabled" end
    return false,"replicateScanRequired"
end

function AB.HookReplicateModeSetting()
    local a=_G.Auctionator
    local cfg=type(a)=="table" and a.Config
    if type(cfg)~="table" or type(cfg.Set)~="function" then return false end
    if cfg==hookedModeConfig then return true end
    if type(hooksecurefunc)~="function" then return false end
    local ok=pcall(hooksecurefunc,cfg,"Set",function(option)
        if cfg.Options and option==cfg.Options.REPLICATE_SCAN then
            AB.ObserveReplicateMode()
        end
    end)
    if ok then hookedModeConfig=cfg end
    return ok
end

if ns.Init then ns.Init(InitializeAuctionatorStock) else InitializeAuctionatorStock() end
