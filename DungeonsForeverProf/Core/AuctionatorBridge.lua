local ns = _G.DF_NS or {}

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
local pendingImportHint = nil
function AB.ShowCopy(text, hint)
    pendingImportText = text or ""
    pendingImportHint = hint
    if not StaticPopupDialogs[POPUP] then
        StaticPopupDialogs[POPUP] = {
            text = L["未检测到可写入的购物清单插件，请复制以下导入串"],
            button1 = L["关闭"],
            timeout = 0,
            whileDead = true,
            hideOnEscape = true,
            preferredIndex = 3,
            hasEditBox = true,
            editBoxWidth = 320,
            OnShow = function(self)
                local label = self.text or _G[(self:GetName() or "") .. "Text"]
                if label and pendingImportHint then label:SetText(pendingImportHint) end
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

local function NativeAuctionator()
    return type(Auctionator) == "table"
        and Auctionator.EasyAuctionCompat == nil
        and type(Auctionator.API) == "table"
        and type(Auctionator.API.v1) == "table"
        and type(Auctionator.API.v1.CreateShoppingList) == "function"
end

function AB.DoImport(profName, items)
    if not (type(items) == "table" and #items > 0) then
        Say(L["购物清单为空，没有可导入的物品"])
        return
    end
    local listName = AB.ListName(profName)
    if NativeAuctionator() then
        local ok, err = AB.Import(listName, items)
        if ok then
            Say(format(L["已导入 Auctionator：%s（共 %d 种）"], listName, #items))
        else
            Say(L["导入失败："] .. tostring(err or "?"))
        end
        return
    end
    local eb = ns.EasyBridge
    if eb and eb.CanLists and eb.CanLists() then
        local ok, err, count = eb.ReplaceList(listName, items)
        if ok then
            Say(format(L["已导入 EasyAuction：%s（共 %d 种）"], listName, count or #items))
            return
        end
        local text = eb.ShareText and eb.ShareText(listName, items)
        if text then
            AB.ShowCopy(text, L["EasyAuction 清单写入失败，请复制以下分享码在 EasyAuction 中导入"])
            return
        end
        Say(L["导入失败："] .. tostring(err or "?"))
        return
    end
    if eb and eb.ShareText and type(_G.EasyAuction12) == "table" then
        local text = eb.ShareText(listName, items)
        if text then
            AB.ShowCopy(text, L["EasyAuction 清单写入失败，请复制以下分享码在 EasyAuction 中导入"])
            return
        end
    end
    AB.ShowCopy(AB.ExportString(listName, items), L["未检测到 EasyAuction 或 Auctionator，请复制以下导入串"])
end

local SUPPLY_MAX_AGE = (ns.ProfRouteAuto and ns.ProfRouteAuto.MaxAuctionSupplyAgeSeconds
    and ns.ProfRouteAuto.MaxAuctionSupplyAgeSeconds()) or 172800
local SNAPSHOT_VERSION = 3
local function WholeNumber(n)
    return type(n)=="number" and n>=0 and n<math.huge and n==math.floor(n)
end
local function ScanDB()
    return ns.ProfDB().prof
end

local supplyRevision = 0
local supplyListeners = {}
local forcedUntil = 0
function AB.ForceExpiredWindow(seconds)
    local now = time and time() or 0
    forcedUntil = now + math.max(30, tonumber(seconds) or 180)
    supplyRevision = supplyRevision + 1
    return forcedUntil
end
function AB.ForceExpiredActive()
    return forcedUntil > 0 and (time and time() or 0) <= forcedUntil
end
function AB.ForceExpiredLeft()
    if not AB.ForceExpiredActive() then return 0 end
    return math.max(0, forcedUntil - (time and time() or 0))
end
local function MarketKey()
    local rules=C_GameRules
    local ids=Enum and Enum.GameRule
    local faction=UnitFactionGroup and UnitFactionGroup("player")
    local region=GetCurrentRegion and GetCurrentRegion()
    if not (rules and type(rules.IsGameRuleActive)=="function" and ids
        and WholeNumber(region) and region>0 and (faction=="Alliance" or faction=="Horde")) then return end
    local bits={}
    for _,name in ipairs({"PvPRuleset","RPRuleset","HardcoreRuleset"}) do
        if ids[name]==nil then return end
        local ok,value=pcall(rules.IsGameRuleActive,ids[name])
        if not ok or type(value)~="boolean" then return end
        bits[#bits+1]=value and "1" or "0"
    end
    local product=ns.IsForever and "forever" or ns.IsRetail and "retail" or tostring(WOW_PROJECT_ID or "wow")
    return "rules:1:"..product..":"..region..":"..table.concat(bits)..":"..faction
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
local currentMarket=false
local SelectMarket
local function StoreBatch(batch)
    local key=batch.mk or currentMarket
    if type(key)~="string" or key=="" then return end
    batch.mk=key
    local db=ScanDB()
    if db.auctionFullScans~=nil and type(db.auctionFullScans)~="table" then return false end
    db.auctionFullScans=db.auctionFullScans or {}
    db.auctionFullScans[key]=batch
    return true
end
local function ReleaseFullBatch(reason,observation,snapshotStatus)
    if fullExpiryTimer then fullExpiryTimer:Cancel();fullExpiryTimer=nil end
    fullExpiryToken=nil
    local batch=observation or fullBatch or fullFailure
    fullFailure={v=SNAPSHOT_VERSION,failure=reason,snapshotStatus=snapshotStatus}
    if type(batch)=="table" then
        fullFailure.mk,fullFailure.ob,fullFailure.ox=batch.mk,batch.ob,batch.ox
        if WholeNumber(batch.t) and batch.t>0 then fullFailure.t=batch.t end
        if reason=="expired" and type(batch.items)=="table" then
            local keep={}
            for id,item in pairs(batch.items) do
                if WholeNumber(id) and id>0 and type(item)=="table" then
                    local q=tonumber(item.q)
                    if q and q>=0 and q==math.floor(q) then
                        local p=tonumber(item.p)
                        if p and p>0 and p<math.huge then keep[id]={q=q,p=p} else keep[id]={q=q} end
                        keep[id].d=item.d;keep[id].failure=item.failure
                    end
                end
            end
            fullFailure.items=keep
            fullFailure.dv=batch.dv
        end
    end
    fullBatch=nil
    StoreBatch(fullFailure)
end
local function FullBatchFailure(batch)
    local key=MarketKey()
    if not key or batch.mk~=key then return "unverified" end
    if batch.v~=SNAPSHOT_VERSION or batch.c~=true or type(batch.items)~="table" then return "incomplete" end
    local stamp=batch.t;local now=time and time() or 0
    if not WholeNumber(stamp) or stamp<=0 or stamp>now then return "incomplete" end
    if now-stamp>SUPPLY_MAX_AGE and not AB.ForceExpiredActive() then return "expired" end
end


local function BatchIds(items)
    local ids={}
    for id in pairs(items) do ids[#ids+1]=id end
    return ids
end

local function ValidBatchHead(batch)
    local now=time and time() or 0
    if type(batch)~="table" or batch.v~=SNAPSHOT_VERSION or batch.c~=true
        or batch.s~="client-auction-results" or type(batch.ox)~="boolean"
        or type(batch.mk)~="string" or batch.mk=="" or type(batch.ob)~="string" or batch.ob==""
        or not WholeNumber(batch.t) or batch.t<=0 or batch.t>now
        or not WholeNumber(batch.completedAt) or batch.completedAt<batch.t or batch.completedAt>now
        or not WholeNumber(batch.expected) or batch.received~=batch.expected or type(batch.items)~="table" then return false end
    if batch.dv~=nil and batch.dv~=1 then return false end
    return true
end

local function ValidItemEntry(id,item,dv)
    if not WholeNumber(id) or id==0 or type(item)~="table" or not WholeNumber(item.q)
        or item.failure~=nil and item.failure~="incomplete"
        or item.p~=nil and (type(item.p)~="number" or item.p~=item.p or item.p<=0 or item.p==math.huge)
        or item.q>0 and item.p==nil then return false end
    if dv~=1 then return true end
    if type(item.d)~="table" then return false end
    local total,last=0,0
    local entries=0
    for index in pairs(item.d) do
        if not WholeNumber(index) or index<1 or index>#item.d then return false end
        entries=entries+1
    end
    if entries~=#item.d then return false end
    for _,level in ipairs(item.d) do
        if type(level)~="table" or type(level[1])~="number" or level[1]~=level[1]
            or level[1]<=last or level[1]==math.huge or not WholeNumber(level[2]) or level[2]==0 then return false end
        last=level[1];total=total+level[2]
    end
    return total==item.q
end

local function ValidBatchStep(batch,ids,st,over)
    local dv=batch.dv
    while st.pos<=#ids do
        local id=ids[st.pos]
        if not ValidItemEntry(id,batch.items[id],dv) then return false end
        st.count=st.count+1
        st.pos=st.pos+1
        if over and debugprofilestop()>over then return nil end
    end
    return st.count<=batch.expected
end

local function ValidSavedBatch(batch)
    if not ValidBatchHead(batch) then return false end
    return ValidBatchStep(batch,BatchIds(batch.items),{pos=1,count=0},nil)
end

local function ClassifyFailedBatch(saved)
    if type(saved)=="table" and saved.v==SNAPSHOT_VERSION and saved.items==nil
        and saved.failure=="incomplete" and saved.snapshotStatus=="missing" then
        fullFailure=saved
    elseif type(saved)=="table" and saved.v==SNAPSHOT_VERSION
        and saved.failure=="expired" and WholeNumber(saved.t) and saved.t>0
        and (time and time() or 0)-saved.t>SUPPLY_MAX_AGE then
        fullFailure=saved
    else ReleaseFullBatch("incomplete",saved) end
end


local function PruneLegacyBatch(batch)
    if batch.dv~=1 or batch.mk~=MarketKey() then return end
    local db=ScanDB()
    local old=db.auctionFullScan
    if type(old)~="table" then return end
    local realm=GetRealmName and GetRealmName()
    local faction=UnitFactionGroup and UnitFactionGroup("player")
    local legacy=realm and faction and realm..":"..faction
    if old.mk~=batch.mk and old.mk~=legacy then return end
    if type(db.auctionFullScans)=="table" and old.mk~=batch.mk then db.auctionFullScans[old.mk]=nil end
    db.auctionFullScan=nil
end

local function OwnSnapshotStatus()
    if SelectMarket then SelectMarket() end
    local batch=fullBatch
    local failure=batch and FullBatchFailure(batch)
    if failure and failure~="unverified" then ReleaseFullBatch(failure);batch=nil end
    local meta=batch or fullFailure
    local forced=AB.ForceExpiredActive()
    local key=MarketKey()
    local matched=key and meta and meta.mk==key
    local staleUsable=forced and matched and meta.failure=="expired"
    local staleItems=type(meta)=="table" and meta.failure=="expired" and type(meta.items)=="table" and next(meta.items)~=nil
    local status=batch and (failure=="unverified" and "mismatch" or "available")
        or meta and not matched and "mismatch"
        or staleUsable and "available"
        or meta and (meta.failure=="expired" and "expired" or meta.snapshotStatus=="missing" and "missing" or "invalid") or "missing"
    return {status=status,observedAt=meta and meta.t,marketKey=meta and meta.mk,
        expiresAt=meta and meta.t and meta.t+SUPPLY_MAX_AGE,
        forced=(forced and (matched and batch~=nil or staleUsable)) or nil,
        canForce=(matched and not batch and meta.failure=="expired") or nil,
        staleIncomplete=(matched and meta.failure=="expired" and not staleItems) or nil,
        restored=restoredSnapshot,completedAt=batch and batch.completedAt}
end

function AB.FullScanSnapshotStatus()
    local own=OwnSnapshotStatus()
    if own.status~="available" then
        local eb=ns.EasyBridge
        local ea=eb and eb.Snapshot and eb.Snapshot()
        if type(ea)=="table" then
            if ea.status=="available" then return ea end
            if AB.ForceExpiredActive() then
                local forced={}
                for key,value in pairs(ea) do forced[key]=value end
                forced.status,forced.forced="available",true
                return forced
            end
            return ea
        end
    end
    return own
end

local function OwnRecord(id)
    if SelectMarket then SelectMarket() end
    local batch=fullBatch
    if batch then
        local failure=FullBatchFailure(batch)
        if failure=="unverified" then return {mk=batch.mk,ob=batch.ob,failure=failure} end
        if failure then ReleaseFullBatch(failure);batch=nil end
    end
    if not batch then
        if AB.ForceExpiredActive() and type(fullFailure)=="table" and fullFailure.mk==MarketKey() and fullFailure.failure=="expired"
            and type(fullFailure.items)=="table" and next(fullFailure.items)~=nil then
            local item=fullFailure.items[id]
            return {q=item and item.q or 0,p=item and item.p,t=fullFailure.t,
                mk=fullFailure.mk,ob=fullFailure.ob,c=not (item and item.failure),failure=item and item.failure,ox=fullFailure.ox~=false,
                s="client-auction-results",v=SNAPSHOT_VERSION,method="auctionator-full-scan"}
        end
        return fullFailure
    end
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
        c=batch.c==true and not (item and item.failure),ox=batch.ox,s="client-auction-results",v=SNAPSHOT_VERSION,
        failure=item and item.failure or batch.c~=true and "incomplete" or nil,
        method="auctionator-full-scan"}
end

local function SupplyRecord(id)
    local rec=OwnRecord(id)
    local eb=ns.EasyBridge
    local ea=eb and eb.Record and eb.Record(id)
    if type(rec)=="table" and not rec.failure then
        if (tonumber(rec.q) or 0)==0 and type(ea)=="table"
            and (tonumber(ea.q) or 0)>0
            and tonumber(ea.t) and tonumber(rec.t) and ea.t>rec.t then return ea end
        return rec
    end
    if type(ea)=="table" then return ea end
    return rec
end

function AB.SupplyRevision()
    local eb=ns.EasyBridge
    local info=eb and eb.Snapshot and eb.Snapshot()
    if type(info)=="table" and tonumber(info.observedAt) then
        return supplyRevision+tonumber(info.observedAt)
    end
    return supplyRevision
end

function AB.GetAuctionSupplyStatus(id)
    if type(id) ~= "number" or id <= 0 then return nil end
    local rec = SupplyRecord(id)
    if type(rec) ~= "table" then return "unknown" end
    local now = time and time() or 0
    if rec.ea then
        if rec.failure then return rec.failure end
        if rec.c ~= true then return "incomplete" end
        local stamp = tonumber(rec.t)
        if not stamp or stamp <= 0 or stamp > now then return "expired" end
        if now - stamp > SUPPLY_MAX_AGE and not AB.ForceExpiredActive() then return "expired" end
        return "verified"
    end
    local qty, stamp = tonumber(rec.q), tonumber(rec.t)
    if rec.failure then return rec.failure end
    if not MarketKey() or rec.mk ~= MarketKey() then return "unverified" end
    if rec.c ~= true or type(rec.ox) ~= "boolean" or rec.s ~= "client-auction-results" then return "incomplete" end
    if not qty or qty < 0 or qty == math.huge or qty ~= math.floor(qty) then return "incomplete" end
    if not stamp or stamp~=stamp or stamp <= 0 or stamp > now then return "expired" end
    if now-stamp > SUPPLY_MAX_AGE and not AB.ForceExpiredActive() then return "expired" end
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
        forced = AB.ForceExpiredActive() or nil,
        expiresAt = math.max(tonumber(rec.t) or 0, AB.ForceExpiredActive() and (time and time() or 0) or 0) + SUPPLY_MAX_AGE,
    }
end

function AB.SupplyFresh(id)
    return AB.GetAuctionSupply(id)
end

function AB.GetAuctionDepth(id)
    if AB.GetAuctionSupplyStatus(id)~="verified" then return end
    local rec=SupplyRecord(id)
    if type(rec)=="table" and rec.ea then return end
    local batch=fullBatch or AB.ForceExpiredActive() and fullFailure
    if not batch or batch.dv~=1 then return end
    local item=batch.items[id]
    local levels={}
    for i,row in ipairs(item and item.d or {}) do levels[i]={row[1],row[2]} end
    return {levels=levels,quantity=item and item.q or 0,observedAt=batch.t,
        marketKey=batch.mk,version=1}
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
    if type(rec) == "table" and (rec.ea or rec.mk==MarketKey()) and tonumber(rec.p) and rec.p>0
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
    if failure then
        if failure~="unverified" then ReleaseFullBatch(failure) end
        return
    end
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
        or buyout<0 or buyout==math.huge then item.failure="incomplete";return end
    if qty==0 or buyout==0 then return end
    local oldQty = item.q
    local newQty = oldQty + qty

    item.p = ((item.p or 0) * oldQty + buyout) / newQty
    item.q = newQty
    item.d=item.d or {}
    local unit=buyout/qty
    item.d[unit]=(item.d[unit] or 0)+qty
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
    fullState={status="processing",done=0,total=scan.expected,startedAt=time and time() or 0}
    local lastDecile=0
    local generation=fullGeneration
    local function Clock()
        if debugprofilestop then return debugprofilestop() end
        if GetTime then return GetTime()*1000 end
        return 0
    end
    local function step()
        if generation~=fullGeneration then return end
        fullTimer=nil
        if not scan.mk or scan.mk~=MarketKey() then
            ImportFailed("unverified");return
        end
        local startAt=Clock()
        local index=scan.index
        local counter=0
        while index<=scan.expected do
            FullRow(scan,rows[index])
            index=index+1
            counter=counter+1
            if counter>=3000 then break end
            if counter%64==0 and Clock()-startAt>=8 then break end
        end
        scan.index=index;fullState.done=index-1
        local decile=math.floor((index-1)/scan.expected*10)
        if decile~=lastDecile then lastDecile=decile;ScanStatusChanged() end
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
        if not scan.depthIDs then
            scan.depthIDs={};scan.depthIndex=1
            for id in pairs(scan.items) do scan.depthIDs[#scan.depthIDs+1]=id end
        end
        local depthLast=math.min(scan.depthIndex+799,#scan.depthIDs)
        for index=scan.depthIndex,depthLast do
            local item=scan.items[scan.depthIDs[index]]
            local prices,depth={},{}
            for price in pairs(item.d or {}) do prices[#prices+1]=price end
            table.sort(prices)
            for _,price in ipairs(prices) do depth[#depth+1]={price,item.d[price]} end
            item.d=depth
        end
        scan.depthIndex=depthLast+1
        if scan.depthIndex<=#scan.depthIDs then
            fullTimer=C_Timer.NewTimer(0,step);return
        end
        local candidate={items=scan.items,t=scan.observedAt,mk=scan.mk,ob=scan.ob,dv=1,
            c=true,v=SNAPSHOT_VERSION,s="client-auction-results",ox=false,
            completedAt=time and time() or scan.observedAt,expected=scan.expected,received=rowCount}
        if not ValidSavedBatch(candidate) or not StoreBatch(candidate) then ImportFailed("incomplete");return end
        PruneLegacyBatch(candidate)
        fullBatch=candidate
        fullFailure=nil
        restoredSnapshot=false
        ScheduleFullExpiry()
        fullState.status=scan.complete and "complete" or "incomplete"
        fullState.observedAt=scan.observedAt
        fullRead=nil
        Say(format(L["扫描数据已就绪（%d 种物品），可以重新计算路线了。"],#scan.depthIDs))
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
            SelectMarket()
            if not MarketKey() then ImportFailed("unverified");return end
            StopFullImport()
            mode.scanSerial=mode.scanSerial+1
            fullRead={startedAt=time and time() or 0,mk=MarketKey(),ob=ObserverKey(),
                modern=ev.ScanStart=="replicate_scan_start",
                modeGeneration=mode.generation,scanSerial=mode.scanSerial}
            local token=fullRead
            fullState={status="scanning",pct=0,startedAt=token.startedAt}
            ScanStatusChanged()
        elseif event==ev.ScanProgress and fullRead and type(data)=="number" then
            if fullState.status=="scanning" then
                local before=math.floor((tonumber(fullState.pct) or 0)*10)
                fullState.pct=data
                if math.floor(data*10)~=before then ScanStatusChanged() end
            end
            if data>=0.2 then ExpectedFullRows(fullRead) end
        elseif event==ev.ScanFailed then
            ImportFailed("failed")
        elseif event==ev.ScanComplete and fullRead and fullState.status=="scanning" then
            if fullRead.expected==nil then ExpectedFullRows(fullRead) end
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

SelectMarket=function()
    local key=MarketKey()
    if currentMarket==key then return end
    StopFullImport()
    if fullExpiryTimer then fullExpiryTimer:Cancel();fullExpiryTimer=nil end
    fullExpiryToken=nil;forcedUntil=0
    currentMarket=key;fullBatch=nil;fullFailure=nil;restoredSnapshot=false
    fullState={status=fullBus and "ready" or "unavailable"}
    local db=ScanDB()
    local saved=key and type(db.auctionFullScans)=="table" and db.auctionFullScans[key] or nil
    if saved==nil then saved=db.auctionFullScan end
    if saved==nil then return end
    restoredSnapshot=true
    if ValidSavedBatch(saved) then
        if key and type(db.auctionFullScans)=="table" and db.auctionFullScans[key]==saved then PruneLegacyBatch(saved) end
        fullBatch=saved;ScheduleFullExpiry()
    else ClassifyFailedBatch(saved) end
end

local function SlowSelectMarket()
    local key=MarketKey()
    if currentMarket==key then return end
    StopFullImport()
    if fullExpiryTimer then fullExpiryTimer:Cancel();fullExpiryTimer=nil end
    fullExpiryToken=nil;forcedUntil=0
    currentMarket=key;fullBatch=nil;fullFailure=nil;restoredSnapshot=false
    fullState={status=fullBus and "ready" or "unavailable"}
    local db=ScanDB()
    local saved=key and type(db.auctionFullScans)=="table" and db.auctionFullScans[key] or nil
    if saved==nil then saved=db.auctionFullScan end
    if saved==nil then return end
    restoredSnapshot=true
    if not ValidBatchHead(saved) then ClassifyFailedBatch(saved) return end
    if not (ns.IdleJobs and ns.IdleJobs.Add) then
        if ValidSavedBatch(saved) then
            if key and type(db.auctionFullScans)=="table" and db.auctionFullScans[key]==saved then PruneLegacyBatch(saved) end
            fullBatch=saved;ScheduleFullExpiry()
        else ClassifyFailedBatch(saved) end
        return
    end
    local ids=BatchIds(saved.items)
    local st={pos=1,count=0}
    local function step()
        if currentMarket~=key then return true end
        local ok=ValidBatchStep(saved,ids,st,debugprofilestop()+3)
        if ok==nil then return end
        if ok then
            if currentMarket~=key then return true end
            if key and type(ScanDB().auctionFullScans)=="table" and ScanDB().auctionFullScans[key]==saved then PruneLegacyBatch(saved) end
            fullBatch=saved;ScheduleFullExpiry()
        else ClassifyFailedBatch(saved) end
        return true
    end
    ns.IdleJobs.Add(step)
end
local function InitializeAuctionatorStock()
    local db=ScanDB()
    db.auctionReplicateGate=nil;db.replicateRequiredAfter=nil
    SlowSelectMarket()
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
    local eb=ns.EasyBridge
    if eb and eb.Available and eb.Available() then return false,"easyauctionStale" end
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

function AB.ClearSavedScans()
    StopFullImport()
    local db=ScanDB()
    db.auctionFullScan=nil
    db.auctionFullScans=nil
    if fullExpiryTimer then fullExpiryTimer:Cancel();fullExpiryTimer=nil end
    fullExpiryToken=nil;forcedUntil=0
    fullBatch=nil;fullFailure=nil;restoredSnapshot=false;currentMarket=false
    SelectMarket()
    supplyRevision=supplyRevision+1
    for _,fn in ipairs(supplyListeners) do pcall(fn,nil,"supply") end
    local RA=ns.ProfRouteAuto
    if RA and RA.NotifyPricesChanged then pcall(RA.NotifyPricesChanged) end
    return true
end

if ns.Init then
    ns.Init(function()
        C_Timer.After(2, function() pcall(InitializeAuctionatorStock) end)
    end)
else
    InitializeAuctionatorStock()
end
