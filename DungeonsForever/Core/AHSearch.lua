local ns = _G.DF_NS or {}
local DG = ns.DungeonDG
if type(DG) ~= "table" then return end

local type, pcall = type, pcall

local function WindowShown()
    local f = _G.AuctionHouseFrame
    if f and type(f.IsShown) == "function" and f:IsShown() then return true end
    local b = _G.AuctionFrame
    if b and type(b.IsShown) == "function" and b:IsShown() then return true end
    return false
end

function DG.AHWindowShown()
    return WindowShown()
end

local function NativeBox()
    local f = _G.AuctionHouseFrame
    local bar = f and f.SearchBar
    if bar and bar.EditBox then return bar.EditBox, bar end
    local b = _G.AuctionFrameBrowse
    if b then
        if b.SearchBar and b.SearchBar.EditBox then return b.SearchBar.EditBox, b.SearchBar end
        if b.SearchBox then
            if b.SearchBox.EditBox then return b.SearchBox.EditBox, b.SearchBox end
            if b.SearchBox.editBox then return b.SearchBox.editBox, b.SearchBox end
        end
    end
    return nil
end

local function ApplyNative(term, box, bar)
    box:SetText(term)
    if type(box.ClearFocus) == "function" then pcall(box.ClearFocus, box) end
    if type(bar.OnSearchTextChanged) == "function" then pcall(bar.OnSearchTextChanged, bar) end
    if type(bar.OnEnterPressed) == "function" then pcall(bar.OnEnterPressed, bar) end
    if type(_G.SearchBoxTemplate_OnTextChanged) == "function" then pcall(_G.SearchBoxTemplate_OnTextChanged, bar) end
    return true
end

local function SearchNative(term)
    local box, bar = NativeBox()
    if not box or not bar then return false end
    local ok = pcall(ApplyNative, term, box, bar)
    return ok
end

local function SearchAuctionator(term)
    local addon = _G.Auctionator
    local api = addon and addon.API and addon.API.v1
    local fn = api and api.MultiSearchExact
    if type(fn) ~= "function" then return false end
    local ok = pcall(fn, "DungeonsForever", { term })
    return ok
end

local function EasyFrame()
    local api = _G.EasyAuctionAPI
    if type(api) ~= "table" or type(api.IsReady) ~= "function" then return nil end
    local ok, ready = pcall(api.IsReady)
    if not ok or ready ~= true then return nil end
    local auction = _G.AuctionHouseFrame
    if not auction or type(auction.IsShown) ~= "function" or not auction:IsShown() then return nil end
    local slash = _G.SlashCmdList and _G.SlashCmdList.EASYAUCTION12
    if type(slash) ~= "function" then return nil end
    pcall(slash, "")
    local frame = _G.EasyAuctionWorkbench
    if not frame or type(frame.GetParent) ~= "function" then return nil end
    if frame:GetParent() ~= auction or not frame:IsShown() then return nil end
    return frame
end

local function EasyBox(frame)
    local box, best = nil, 0
    local children = { frame:GetChildren() }
    for index = 1, #children do
        local child = children[index]
        if child and type(child.GetObjectType) == "function" and child:GetObjectType() == "EditBox" then
            local width = type(child.GetWidth) == "function" and child:GetWidth() or 0
            local handler = type(child.GetScript) == "function" and child:GetScript("OnEnterPressed") or nil
            if width >= 240 and width > best and type(handler) == "function" then
                box, best = child, width
            end
        end
    end
    return box
end

local function SearchEasyAuction(term)
    local frame = EasyFrame()
    if not frame then return false end
    local box = EasyBox(frame)
    if not box then return false end
    box:SetText(term)
    if type(box.SetFocus) == "function" then pcall(box.SetFocus, box) end
    if type(box.HighlightText) == "function" then pcall(box.HighlightText, box) end
    local handler = type(box.GetScript) == "function" and box:GetScript("OnEnterPressed") or nil
    if type(handler) == "function" then
        local ok = pcall(handler, box)
        if not ok then return false end
    end
    return true
end

DG.__AHSearchBuild = 2

function DG.AHSearchName(name)
    if type(name) ~= "string" or name == "" then return false end
    if not WindowShown() then return false end
    if SearchEasyAuction(name) then return true end
    if SearchAuctionator(name) then return true end
    return SearchNative(name)
end

function DG.AHSearchItem(id)
    if type(id) ~= "number" or id <= 0 then return false end
    if not WindowShown() then return false end
    local name, known
    if type(DG.ItemName) == "function" then name, known = DG.ItemName(id) end
    if known == true and type(name) == "string" and name ~= "" then
        if DG.AHSearchName(name) then return true end
    end
    return SearchEasyAuction("item:" .. id)
end

local BaseShiftClick = DG.ItemShiftClick
if type(BaseShiftClick) == "function" then
    function DG.ItemShiftClick(row, button)
        if button == "LeftButton" and type(IsShiftKeyDown) == "function" and IsShiftKeyDown() then
            local it = row and row.__it
            if type(it) == "table" then it = it[1] end
            if type(it) == "number" and DG.AHSearchItem(it) then return true end
        end
        return BaseShiftClick(row, button)
    end
end
