local _, ns = ...

local L = ns.L

local TL = {}
ns.TipLines = TL

local C_SRC = { 1, 0.82, 0 }
local C_WISH = { 1, 0.82, 0.4 }
local C_BIS = { 0.47, 0.75, 0.45 }
local C_QUEST = { 0.75, 0.78, 0.82 }
local C_SC_UP = { 0.47, 0.85, 0.45 }
local C_SC_DOWN = { 0.92, 0.42, 0.38 }

local LOGO = "|TInterface\\AddOns\\DungeonsForever\\Media\\DF_Logo.tga:16:16:0:0:32:32:0:32:0:32|t "
local LOGO_GAP = "|TInterface\\AddOns\\DungeonsForever\\Media\\DF_Blank.tga:16:16:0:0:32:32:0:32:0:32|t "

local TIP_VER = 1
local TIP_KEYS = { "src", "bis", "bisScore", "wish", "quest" }

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
                            if #e < 24 then e[#e + 1] = { dn, boss } end
                        end
                    end
                end
            end
        end
    end
    return srcIdx
end

local craftIdx
local craftDone = false
local function BuildCraft()
    if craftDone then return craftIdx end
    craftDone = true
    if not ns.IsForever then return nil end
    local pro = ns.ProfData and ns.ProfData.pro
    if type(pro) ~= "table" or type(ns.ProfCraftSlugOf) ~= "function" then return nil end
    craftIdx = setmetatable({}, {
        __index = function(t, id)
            local slug = ns.ProfCraftSlugOf(id)
            if not slug then return nil end
            local pd = pro[slug]
            local nm = type(pd) == "table" and pd.name or nil
            if not nm then return nil end
            rawset(t, id, nm)
            return nm
        end,
    })
    return craftIdx
end

local function QuestQids(id)
    local ids = {}
    local gq = ns.GearSrcQ
    if type(gq) == "table" and type(gq[id]) == "number" then
        ids[#ids + 1] = gq[id]
    end
    local v = type(ns.GearRewardQ) == "table" and ns.GearRewardQ[id] or nil
    if type(v) == "number" then
        ids[#ids + 1] = v
    elseif type(v) == "table" then
        for _, qid in ipairs(v) do
            if type(qid) == "number" then ids[#ids + 1] = qid end
        end
    end
    return ids
end

local function QuestOf(id)
    local ids = QuestQids(id)
    if #ids > 1 then
        local seen = {}
        local out = {}
        for _, qid in ipairs(ids) do
            if not seen[qid] then
                seen[qid] = true
                out[#out + 1] = qid
            end
        end
        ids = out
    end
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

local function ScoreLineOf(id)
    local BG = ns.BisModule
    if not (BG and BG.ScoreVsBis) then return nil end
    local _, pct = BG.ScoreVsBis(id)
    if type(pct) ~= "number" or pct == 0 then return nil end
    if pct > 999 then pct = 999 elseif pct < -999 then pct = -999 end
    return format(L["BIS 评分 %+d%%"], pct), pct > 0
end

function TL.Lines(id)
    if type(id) ~= "number" then return nil end
    local cfg = Cfg()
    local out
    local function add(text, col, cont, mark)
        if not out then out = {} end
        out[#out + 1] = { text, col[1], col[2], col[3], cont, mark }
    end
    if cfg.src then
        local e = BuildSrc()[id]
        if e then
            for i, s in ipairs(e) do
                add(s[1] .. " · " .. s[2], C_SRC, i > 1)
            end
        else
            local cn = BuildCraft()
            local nm = cn and cn[id]
            if nm then
                add(format(L["专业制造（%s）"], nm), C_SRC)
            end
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
    if cfg.bisScore then
        local txt, up = ScoreLineOf(id)
        if txt then
            add(txt, up and C_SC_UP or C_SC_DOWN, nil, true)
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

local function Append(tip, lines, skipN)
    if type(lines) ~= "table" then return end
    local total = #lines
    local from = skipN or 0
    if from >= total then return end
    if from == 0 then tip:AddLine(" ") end
    local first = from == 0
    for i = from + 1, total do
        local ln = lines[i]
        if type(ln) == "table" and type(ln[1]) == "string" then
            tip:AddLine((first and LOGO or LOGO_GAP) .. ln[1], ln[2] or 1, ln[3] or 1, ln[4] or 1, true)
            first = false
        end
    end
end
TL.Append = Append

local EXCLUDE = {
    ShoppingTooltip1 = true, ShoppingTooltip2 = true,
    ItemRefShoppingTooltip1 = true, ItemRefShoppingTooltip2 = true,
    TFItemScanTip = true,
}
local augStamp = {}

local function TipItemID(tt)
    if type(tt.GetItem) ~= "function" then return nil end
    local ok, _, link = pcall(tt.GetItem, tt)
    if ok and type(link) == "string" then return tonumber(link:match("item:(%d+)")) end
    return nil
end

local function Augment(tt)
    if not tt then return end
    if tt.__dfOwn then return end
    local DG = ns.DungeonModule
    if DG and DG.__tipBusy then return end
    local nm = tt.GetName and tt:GetName()
    if nm and EXCLUDE[nm] then return end
    if not Cfg().global then return end
    local id = TipItemID(tt)
    if not id then return end
    if augStamp[tt] == id then return end
    augStamp[tt] = id
    local lines = TL.Lines(id)
    Append(tt, lines, 0)
    local n = type(lines) == "table" and #lines or 0
    tt.__dfAugN = n
    for i = 1, n do
        local ln = lines[i]
        if type(ln) == "table" and ln[6] then
            tt.__dfScoreShown = true
            break
        end
    end
    if Cfg().bisScore and C_Timer and C_Timer.After and not tt.__dfScoreShown then
        tt.__dfAugTries = 3
        local function Retry()
            local DG2 = ns.DungeonModule
            if tt.__dfOwn or augStamp[tt] ~= id then return end
            if DG2 and DG2.__tipBusy then return end
            if TipItemID(tt) ~= id then return end
            local txt, up = ScoreLineOf(id)
            if txt then
                if (tt.__dfAugN or 0) == 0 then
                    local ls = TL.Lines(id)
                    Append(tt, ls, 0)
                    tt.__dfAugN = type(ls) == "table" and #ls or 0
                else
                    tt:AddLine(LOGO_GAP .. txt,
                        up and C_SC_UP[1] or C_SC_DOWN[1],
                        up and C_SC_UP[2] or C_SC_DOWN[2],
                        up and C_SC_UP[3] or C_SC_DOWN[3], true)
                    tt.__dfAugN = (tt.__dfAugN or 0) + 1
                end
                tt.__dfScoreShown = true
            elseif tt.__dfAugTries > 0 then
                tt.__dfAugTries = tt.__dfAugTries - 1
                C_Timer.After(0.6, Retry)
            end
        end
        C_Timer.After(0.6, Retry)
    end
end

local function HookTip(tt)
    if not tt or tt.__dfAugHooked then return end
    if not tt.HookScript then return end
    tt.__dfAugHooked = true
    pcall(tt.HookScript, tt, "OnTooltipCleared", function(self)
        augStamp[self] = nil
        self.__dfAugN = nil
        self.__dfAugTries = nil
        self.__dfScoreShown = nil
    end)
    pcall(tt.HookScript, tt, "OnTooltipSetItem", function() Augment(tt) end)
end

local SAMPLE_CAP_WISH = 64
local SAMPLE_CAP_CUR = 64
local SAMPLE_CAP_QUEST = 128
local SAMPLE_CAP_SRC = 128

local function SampleFallback()
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

function TL.SampleItem()
    local cfg = Cfg()
    local GM = ns.GearModule
    local BG = ns.BisModule
    local srcIdx = BuildSrc()
    local pools = {}
    if GM and GM.WishIDs then
        local w = GM.WishIDs()
        for i = 1, math.min(#w, SAMPLE_CAP_WISH) do
            pools[#pools + 1] = w[i]
        end
    end
    if BG and type(BG.cur) == "table" then
        local cs = {}
        for _, v in pairs(BG.cur) do
            if type(v) == "number" and v > 0 then cs[#cs + 1] = v end
        end
        table.sort(cs)
        for i = 1, math.min(#cs, SAMPLE_CAP_CUR) do
            pools[#pools + 1] = cs[i]
        end
    end
    local qks = {}
    local seenQ = {}
    local gq = ns.GearSrcQ
    if type(gq) == "table" then
        for k in pairs(gq) do
            if type(k) == "number" and not seenQ[k] then
                seenQ[k] = true
                qks[#qks + 1] = k
            end
        end
    end
    local rq = ns.GearRewardQ
    if type(rq) == "table" then
        for k in pairs(rq) do
            if type(k) == "number" and not seenQ[k] then
                seenQ[k] = true
                qks[#qks + 1] = k
            end
        end
    end
    table.sort(qks)
    for i = 1, math.min(#qks, SAMPLE_CAP_QUEST) do
        pools[#pools + 1] = qks[i]
    end
    local sks = {}
    for k in pairs(srcIdx) do sks[#sks + 1] = k end
    table.sort(sks)
    for i = 1, math.min(#sks, SAMPLE_CAP_SRC) do
        pools[#pools + 1] = sks[i]
    end
    local bestId, bestScore
    for _, id in ipairs(pools) do
        local sc = 0
        if cfg.wish and GM and GM.WishIs and GM.WishIs(id) then sc = sc + 2 end
        if cfg.quest and QuestOf(id) then sc = sc + 2 end
        if cfg.src and srcIdx[id] then sc = sc + 1 end
        if cfg.src and not srcIdx[id] then
            local cn = BuildCraft()
            if cn and cn[id] then sc = sc + 2 end
        end
        if cfg.bis then
            local _, has = BisHit(id)
            if has then sc = sc + 2 end
        end
        if cfg.bisScore then
            local BG = ns.BisModule
            if BG and BG.ScoreVsBis and BG.ScoreVsBis(id) ~= nil then sc = sc + 2 end
        end
        if sc > 0 and sc > (bestScore or 0) then
            bestId = id
            bestScore = sc
        end
    end
    if bestId then return bestId end
    return SampleFallback()
end

local PREVIEW_W = 340
local previewTip
local previewCard
local previewOn = false
local previewId

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
    pcall(tip.HookScript, tip, "OnTooltipCleared", function(self) augStamp[self] = nil end)
    pcall(tip.HookScript, tip, "OnTooltipSetItem", function(self)
        if not previewOn then return end
        if augStamp[self] == previewId then return end
        local id = previewId
        if not id and type(self.GetItem) == "function" then
            local ok2, _, link = pcall(self.GetItem, self)
            if ok2 and type(link) == "string" then id = tonumber(link:match("item:(%d+)")) end
        end
        if not id then return end
        augStamp[self] = id
        Append(self, TL.Lines(id))
    end)
    tip:Hide()
    return tip
end

function TL.ShowPreview(card)
    local tip = TL.EnsurePreview(card)
    if not tip then return false end
    previewOn = true
    TL.RefreshPreview()
    return true
end

function TL.RefreshPreview()
    local tip = previewTip
    if not tip or not previewOn then return end
    local card = previewCard
    if not card then return end
    tip:SetScale(1)
    pcall(tip.SetOwner, tip, card, "ANCHOR_NONE")
    tip:ClearAllPoints()
    tip:SetPoint("TOPRIGHT", card, "TOPLEFT", -8, 40)
    local id = TL.SampleItem()
    previewId = id
    if not id then
        augStamp[tip] = nil
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
        augStamp[tip] = nil
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
    if augStamp[tip] ~= id then
        augStamp[tip] = id
        Append(tip, TL.Lines(id))
    end
    tip:Show()
    local w = 0
    local ok, v = pcall(tip.GetWidth, tip)
    if ok and type(v) == "number" then w = v end
    if w > PREVIEW_W then tip:SetScale(PREVIEW_W / w) end
end

function TL.HidePreview()
    previewOn = false
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
