local _, ns = ...

local L = ns.L

local TL = {}
ns.TipLines = TL

local C_SRC = { 1, 0.82, 0 }
local C_WISH = { 1, 0.82, 0.4 }
local C_BIS = { 0.47, 0.75, 0.45 }
local C_QUEST = { 0.75, 0.78, 0.82 }

local TIP_VER = 1
local TIP_KEYS = { "src", "bis", "wish", "quest" }

local function Cfg()
    local db = ns.DB and ns.DB()
    local ui = db and db.ui
    if not ui then return { ver = TIP_VER } end
    local t = ui.tip
    if type(t) ~= "table" or t.ver ~= TIP_VER then
        t = { ver = TIP_VER }
        ui.tip = t
    end
    for _, k in ipairs(TIP_KEYS) do
        if t[k] == nil then t[k] = false end
    end
    if t.global == nil then t.global = false end
    return t
end
ns.TipCfg = Cfg

local CLASS_FILE = {
    WARRIOR = "warrior", PALADIN = "paladin", HUNTER = "hunter",
    ROGUE = "rogue", PRIEST = "priest", MAGE = "mage",
    WARLOCK = "warlock", DRUID = "druid", SHAMAN = "shaman",
}

local srcIdx
local function BuildSrc()
    if srcIdx then return srcIdx end
    srcIdx = {}
    local nameOf = {}
    local dd = ns.DungeonData and ns.DungeonData.dungeons
    for _, d in ipairs(dd or {}) do
        if type(d) == "table" and type(d.id) == "string" and type(d.name) == "string" then
            nameOf[d.id] = d.name
        end
    end
    local loot = ns.DungeonLoot or {}
    for key, srcs in pairs(loot) do
        if type(srcs) == "table" then
            local dn = nameOf[key] or key
            for _, s in ipairs(srcs) do
                if type(s) == "table" then
                    local boss = s[2]
                    if type(boss) ~= "string" or boss == "" then boss = s[1] end
                    if type(boss) ~= "string" then boss = "" end
                    local its = s[5]
                    for _, it in ipairs(its or {}) do
                        local id = type(it) == "table" and it[1] or it
                        if type(id) == "number" then
                            local e = srcIdx[id]
                            if not e then e = {} srcIdx[id] = e end
                            if #e < 8 then e[#e + 1] = { dn, boss } end
                        end
                    end
                end
            end
        end
    end
    return srcIdx
end

local questIdx
local function BuildQuest()
    if questIdx then return questIdx end
    questIdx = {}
    local g = ns.GearSrcQ
    if type(g) == "table" then
        for item, qid in pairs(g) do
            if type(item) == "number" and type(qid) == "number" then
                local e = questIdx[item]
                if not e then e = {} questIdx[item] = e end
                e[qid] = true
            end
        end
    end
    local dq = ns.DungeonQuests or {}
    for _, rows in pairs(dq) do
        if type(rows) == "table" then
            for _, q in ipairs(rows) do
                if type(q) == "table" then
                    local qid = q[1]
                    local rewards = q[10]
                    for _, it in ipairs(rewards or {}) do
                        local iid = type(it) == "table" and it[1] or it
                        if type(iid) == "number" and type(qid) == "number" then
                            local e = questIdx[iid]
                            if not e then e = {} questIdx[iid] = e end
                            e[qid] = true
                        end
                    end
                end
            end
        end
    end
    return questIdx
end

local bisVols
local function Vols()
    if bisVols then return bisVols end
    bisVols = {}
    local B
    if ns.EnsureBISData then B = ns.EnsureBISData() end
    if not B then B = ns.BIS end
    if B and type(B.levels) == "table" then
        for lv, v in pairs(B.levels) do
            if type(v) == "table" and type(v.classes) == "table" then
                bisVols[#bisVols + 1] = { lv = tonumber(lv) or 0, classes = v.classes }
            end
        end
        table.sort(bisVols, function(a, b) return a.lv < b.lv end)
    end
    return bisVols
end

local function ClassSlug()
    local BG = ns.BisModule
    if BG and type(BG.cls) == "string" and BG.cls ~= "" then return BG.cls end
    if type(UnitClass) ~= "function" then return nil end
    local ok, _, file = pcall(UnitClass, "player")
    if ok and type(file) == "string" then return CLASS_FILE[file] end
    return nil
end

local function BisHit(id)
    local BG = ns.BisModule
    if BG and type(BG.cur) == "table" then
        for _, v in pairs(BG.cur) do
            if v == id then return nil, true end
        end
    end
    local vols = Vols()
    if #vols == 0 then return nil end
    local slug = ClassSlug()
    if not slug then return nil end
    local lv = 0
    if type(UnitLevel) == "function" then
        local ok, v = pcall(UnitLevel, "player")
        if ok and type(v) == "number" then lv = v end
    end
    local vol
    for _, v in ipairs(vols) do
        if v.lv <= lv then vol = v end
    end
    vol = vol or vols[1]
    local wantId = BG and BG.spec or nil
    local wantT = BG and BG.tspec or nil
    local labels = {}
    for _, c in ipairs(vol.classes) do
        if c.slug == slug then
            for _, sp in ipairs(c.specs or {}) do
                local hit = false
                for _, list in pairs(sp.slots or {}) do
                    if type(list) == "table" then
                        for _, row in ipairs(list) do
                            if type(row) == "table" and row[1] == id then
                                hit = true
                                break
                            end
                        end
                    end
                    if hit then break end
                end
                if hit then
                    if (wantId and sp.id == wantId) or (wantT and sp.tspec == wantT) then
                        return sp.label, true
                    end
                    labels[#labels + 1] = sp.label
                end
            end
        end
    end
    if #labels == 1 then return labels[1], true end
    if #labels > 1 then return nil, true end
    return nil
end

local function QuestOf(id)
    local e = BuildQuest()[id]
    if not e then return nil end
    local ids = {}
    for qid in pairs(e) do ids[#ids + 1] = qid end
    if #ids == 0 then return nil end
    table.sort(ids)
    local DG = ns.DungeonModule
    local nm
    for _, qid in ipairs(ids) do
        if DG and DG.QuestName then
            local t, ok = DG.QuestName(qid)
            if ok and type(t) == "string" and t ~= "" then
                nm = t
                break
            end
        end
    end
    return nm, #ids
end

function TL.Lines(id)
    if type(id) ~= "number" then return nil end
    local cfg = Cfg()
    local out
    local function add(text, col)
        if not out then out = {} end
        out[#out + 1] = { text, col[1], col[2], col[3] }
    end
    if cfg.src then
        local e = BuildSrc()[id]
        if e then
            local s = e[1]
            local text = s[1] .. " · " .. s[2]
            if #e > 1 then text = text .. format(L["等 %d 个来源"], #e) end
            add(text, C_SRC)
        end
    end
    if cfg.wish then
        local gm = ns.GearModule
        if gm and gm.WishIs and gm.WishIs(id) then
            add(L["★ 心愿清单"], C_WISH)
        end
    end
    if cfg.bis then
        local label, has = BisHit(id)
        if has then
            if type(label) == "string" and label ~= "" then
                add(format(L["BIS 推荐（%s）"], label), C_BIS)
            else
                add(L["BIS 推荐"], C_BIS)
            end
        end
    end
    if cfg.quest then
        local nm, n = QuestOf(id)
        if nm then
            if n > 1 then
                add(format(L["任务：%s 等 %d 个"], nm, n), C_QUEST)
            else
                add(format(L["任务：%s"], nm), C_QUEST)
            end
        end
    end
    return out
end

local function Append(tip, lines)
    if type(lines) ~= "table" or #lines == 0 then return end
    tip:AddLine(" ")
    for _, ln in ipairs(lines) do
        if type(ln) == "table" and type(ln[1]) == "string" then
            tip:AddLine(ln[1], ln[2] or 1, ln[3] or 1, ln[4] or 1, true)
        end
    end
end

local EXCLUDE = {
    ShoppingTooltip1 = true, ShoppingTooltip2 = true,
    ItemRefShoppingTooltip1 = true, ItemRefShoppingTooltip2 = true,
    TFItemScanTip = true,
}
local augStamp = {}

local function Augment(tt)
    if not tt then return end
    if tt.__dfOwn then return end
    local DG = ns.DungeonModule
    if DG and DG.__tipBusy then return end
    local nm = tt.GetName and tt:GetName()
    if nm and EXCLUDE[nm] then return end
    if not Cfg().global then return end
    local id
    if type(tt.GetItem) == "function" then
        local ok, _, link = pcall(tt.GetItem, tt)
        if ok and type(link) == "string" then id = tonumber(link:match("item:(%d+)")) end
    end
    if not id then return end
    if augStamp[tt] == id then return end
    augStamp[tt] = id
    Append(tt, TL.Lines(id))
end

local function HookTip(tt)
    if not tt or tt.__dfAugHooked then return end
    if not tt.HookScript then return end
    tt.__dfAugHooked = true
    pcall(tt.HookScript, tt, "OnTooltipCleared", function(self) augStamp[self] = nil end)
    pcall(tt.HookScript, tt, "OnTooltipSetItem", function() Augment(tt) end)
end

function TL.SampleItem()
    local idx = BuildSrc()
    local BG = ns.BisModule
    if BG and type(BG.cur) == "table" then
        local best
        for _, id in pairs(BG.cur) do
            if type(id) == "number" and id > 0 then
                if idx[id] then return id end
                if not best then best = id end
            end
        end
        if best then return best end
    end
    local loot = ns.DungeonLoot or {}
    local dd = ns.DungeonData and ns.DungeonData.dungeons or {}
    for _, d in ipairs(dd) do
        if type(d) == "table" and type(d.id) == "string" then
            local srcs = loot[d.id]
            local s = srcs and srcs[1]
            local its = s and s[5]
            local it = its and its[1]
            local id = type(it) == "table" and it[1] or it
            if type(id) == "number" then return id end
        end
    end
    return nil
end

local PREVIEW_W = 340
local previewTip
local previewCard

function TL.EnsurePreview(card)
    if previewTip then return previewTip end
    if not card then return nil end
    local ok, tip = pcall(CreateFrame, "GameTooltip", "DFTipPreview", card, "GameTooltipTemplate")
    if not ok or not tip then return nil end
    previewTip = tip
    previewCard = card
    tip.__dfOwn = true
    tip:EnableMouse(true)
    if card.GetFrameStrata and tip.SetFrameStrata then
        pcall(tip.SetFrameStrata, tip, card:GetFrameStrata())
    end
    tip:SetFrameLevel(card:GetFrameLevel() + 20)
    tip:Hide()
    return tip
end

function TL.RefreshPreview()
    local tip = previewTip
    if not tip or not tip:IsShown() then return end
    local card = previewCard
    if not card then return end
    tip:SetScale(1)
    pcall(tip.SetOwner, tip, card, "ANCHOR_NONE")
    tip:ClearAllPoints()
    tip:SetPoint("TOPRIGHT", card, "TOPLEFT", -8, 40)
    local id = TL.SampleItem()
    if not id then
        tip:ClearLines()
        tip:AddLine(L["没有可预览的物品"], 0.6, 0.6, 0.6, true)
        tip:Show()
        return
    end
    local okh = false
    if tip.SetHyperlink then
        okh = pcall(tip.SetHyperlink, tip, "item:" .. tostring(id))
    end
    local n = 0
    if tip.NumLines then
        local ok, v = pcall(tip.NumLines, tip)
        if ok and type(v) == "number" then n = v end
    end
    if not okh or n <= 1 then
        tip:ClearLines()
        local DG = ns.DungeonModule
        local nm, has
        if DG and DG.ItemName then nm, has = DG.ItemName(id) end
        if has then
            local r, g, b = DG.QColor(DG.QualOf(id))
            tip:AddLine(nm, r, g, b, true)
        else
            tip:AddLine(format(L["物品 #%d"], id), 0.6, 0.6, 0.6, true)
        end
    end
    Append(tip, TL.Lines(id))
    tip:Show()
    local w = 0
    local ok, v = pcall(tip.GetWidth, tip)
    if ok and type(v) == "number" then w = v end
    if w > PREVIEW_W then tip:SetScale(PREVIEW_W / w) end
end

function TL.HidePreview()
    if previewTip then previewTip:Hide() end
end

function TL.PreviewShown()
    return previewTip and previewTip:IsShown() and true or false
end

do
    HookTip(_G.GameTooltip)
    HookTip(_G.ItemRefTooltip)
    if TooltipDataProcessor and TooltipDataProcessor.AddTooltipPostCall then
        local td = Enum and Enum.TooltipDataType
        if td and td.Item ~= nil then
            pcall(TooltipDataProcessor.AddTooltipPostCall, td.Item, function(tt) Augment(tt) end)
        end
    end
end
