# -*- coding: utf-8 -*-
# 升级页操作区 B1 改版（2026-10-10）：
#   顶部信息卡（模式/总花费/目标等级/价格快照）+ 工具行瘦身为 视图切换+重算。
# 用法: python _temp/patch_lv_b1.py --check   # 只验锚点命中数
#       python _temp/patch_lv_b1.py           # 正式应用
import sys

P = 'Core/ProfessionUI.lua'

def n(s):
    return s.replace('\n', '\r\n').encode('utf-8')

EDITS = []

# ── 1. LevelTool：只剩 视图切换 + 重算 ──────────────────────────────
EDITS.append(('leveltool', n('''-- ── 升级页签工具行（2026-10-08）：固定/自动 + 路线/购物清单子页 + 重算 ──────
function PD.LevelTool()
    local autoOn = PD.Setting("autoRoute")
    local list = {
        { key = "fixed",      text = L["固定路线"], on = not autoOn },
        { key = "auto",       text = L["自动计算"], on = autoOn },
        -- 子页切换固定/自动共用（2026-10-09 v2：购物清单子页两种模式都可用）
        { key = "page_route", text = L["路线"],     on = PD.autoPage ~= "shop" },
        { key = "page_shop",  text = L["购物清单"], on = PD.autoPage == "shop" },
        { key = "recalc",     text = L["重新计算"] },
    }
    return list, function(k)
        if k == "fixed" then
            ProfDB().autoRoute = false
            if RA then RA.Invalidate() end
        elseif k == "auto" then
            ProfDB().autoRoute = true
        elseif k == "page_route" then
            PD.autoPage = "route"
        elseif k == "page_shop" then
            PD.autoPage = "shop"
        elseif k == "recalc" then
            if RA then RA.Invalidate() end
        end
        PD.Render()
    end
end
'''), n('''-- ── 升级页签工具行（2026-10-10 B1 改版）：模式 / 总花费 / 目标等级 / 价格快照
--    收进顶部信息卡（PD.PaintLvTiles）；工具行只剩 视图切换 + 重算。 ──────
function PD.LevelTool()
    local list = {
        { key = "page_route", text = L["路线"],     on = PD.autoPage ~= "shop", gap = 2 },
        { key = "page_shop",  text = L["购物清单"], on = PD.autoPage == "shop", gap = 14 },
        { key = "recalc",     text = L["重新计算"] },
    }
    return list, function(k)
        if k == "page_route" then
            PD.autoPage = "route"
        elseif k == "page_shop" then
            PD.autoPage = "shop"
        elseif k == "recalc" then
            if RA then RA.Invalidate() end
        end
        PD.Render()
    end
end
''')))

# ── 2. PaintTool：支持 yoff 上移偏移 + def.gap 自定义间距 ───────────
EDITS.append(('painttool_sig', n('''function PD.PaintTool(list, handler)
    PD.onTool = handler
    list = list or {}
    local n = math.min(#list, PD.TOOL_MAX)
'''), n('''function PD.PaintTool(list, handler, yoff)
    PD.onTool = handler
    list = list or {}
    yoff = yoff or 0
    local n = math.min(#list, PD.TOOL_MAX)
''')))

EDITS.append(('painttool_yoff', n('''            bt:SetPoint("TOPLEFT", PD.page, "TOPLEFT", PD.RIGHT_X + x,
                        -(PD.BODY_TOP + row * (PD.TOOL_H + PD.TOOL_GAP)))
'''), n('''            bt:SetPoint("TOPLEFT", PD.page, "TOPLEFT", PD.RIGHT_X + x,
                        -(PD.BODY_TOP + yoff + row * (PD.TOOL_H + PD.TOOL_GAP)))
''')))

EDITS.append(('painttool_gap', n('''            bt:Show()
            x = x + w + PD.TOOL_GAP
'''), n('''            bt:Show()
            x = x + w + (def.gap or PD.TOOL_GAP)
''')))

# ── 3. Build：tgtBox 整块退役 → 四张信息卡 + 卡内目标等级编辑 ───────
EDITS.append(('build_tiles', n('''    -- 目标等级输入框（2026-10-09 v2）：升级页工具行右端，回车 / 失焦生效
    local tgt = CreateFrame("Frame", nil, page)
    tgt:SetSize(180, PD.TOOL_H)
    tgt:Hide()
    tgt.label = MakeFS(tgt, 12, C_GREY, "LEFT")
    tgt.label:SetText(L["目标等级"])
    tgt.label:SetPoint("LEFT", tgt, "LEFT", 0, 0)
    local eb = CreateFrame("EditBox", nil, tgt, "BackdropTemplate")
    eb:SetBackdrop({
        bgFile = "Interface\\\\Buttons\\\\WHITE8x8",
        edgeFile = "Interface\\\\Buttons\\\\WHITE8x8",
        edgeSize = 1,
    })
    eb:SetBackdropColor(0, 0, 0, 0.55)
    eb:SetBackdropBorderColor(1, 0.82, 0, 0.9)
    eb:SetSize(58, PD.TOOL_H)
    eb:SetPoint("LEFT", tgt.label, "RIGHT", 8, 0)
    eb:SetFont(ns.FONT, 13, ns.hui and ns.hui.FontFlags and ns.hui.FontFlags("OUTLINE") or "OUTLINE")
    eb:SetTextColor(1, 0.82, 0)
    eb:SetJustifyH("CENTER")
    eb:SetAutoFocus(false)
    eb:SetTextInsets(4, 4, 0, 0)
    eb:SetNumeric(true)
    tgt.eb = eb
    tgt.hint = MakeFS(tgt, 12, C_GREY, "LEFT")
    tgt.hint:SetText(L["级（300 = 全程）"])
    tgt.hint:SetPoint("LEFT", eb, "RIGHT", 6, 0)
    local function ApplyTarget()
        if not PD.cur then return end
        local v = tonumber(eb:GetText()) or 300
        v = math.max(1, math.min(300, math.floor(v)))
        local db = ProfDB()
        db.lvTarget = db.lvTarget or {}
        local old = tonumber(db.lvTarget[PD.cur]) or 300
        if old == v then return end
        db.lvTarget[PD.cur] = (v >= 300) and nil or v
        if RA then RA.Invalidate() end
        PD.Render()
    end
    eb:SetScript("OnEnterPressed", function(self)
        self:ClearFocus()
        ApplyTarget()
        ns.PlaySound(1)
    end)
    eb:SetScript("OnEscapePressed", function(self) self:ClearFocus() end)
    eb:SetScript("OnEditFocusLost", ApplyTarget)
    PD.tgtBox = tgt
'''), n('''    -- 升级页信息卡（2026-10-10 B1）：模式 / 总花费 / 目标等级 / 价格快照。
    -- 帧数纪律：Build 一次建好；显隐与内容由 PD.PaintLvTiles 每次渲染刷新。
    -- 目标等级直接在卡内编辑（EditBox 常驻 target 卡，编辑态盖住数值文本）。
    PD.LV_TILE_H, PD.LV_TILE_GAP = 38, 8
    PD.lvTiles = {}
    for _, td in ipairs({
        { key = "mode",   w = 200 },
        { key = "cost",   w = 250 },
        { key = "target", w = 150 },
        { key = "snap",   w = 0 },
    }) do
        local tf = CreateFrame("Button", nil, page)
        tf:SetSize(td.w, PD.LV_TILE_H)
        tf:SetBackdrop({
            bgFile = "Interface\\\\Buttons\\\\WHITE8x8",
            edgeFile = "Interface\\\\Buttons\\\\WHITE8x8",
            edgeSize = 1,
        })
        tf:SetBackdropColor(0, 0, 0, 0.35)
        tf:SetBackdropBorderColor(0.45, 0.45, 0.45, 0.6)
        tf:Hide()
        tf.label = MakeFS(tf, 11, C_GREY, "LEFT")
        tf.label:SetPoint("TOPLEFT", tf, "TOPLEFT", 10, -6)
        tf.val = MakeFS(tf, 14, C_WHITE, "LEFT")
        tf.val:SetPoint("BOTTOMLEFT", tf, "BOTTOMLEFT", 10, 6)
        tf:EnableMouseWheel(true)
        tf:SetScript("OnMouseWheel", function(self, delta)
            DG.WheelScroll(PD.scroll, PD.child, delta)
        end)
        PD.lvTiles[td.key] = tf
    end
    PD.lvTiles.mode:SetScript("OnClick", function()
        local on = not PD.Setting("autoRoute")
        ProfDB().autoRoute = on
        if not on and RA then RA.Invalidate() end
        PD.Render()
        ns.PlaySound(1)
    end)
    do
        local tf = PD.lvTiles.target
        local eb = CreateFrame("EditBox", nil, tf, "BackdropTemplate")
        eb:SetBackdrop({
            bgFile = "Interface\\\\Buttons\\\\WHITE8x8",
            edgeFile = "Interface\\\\Buttons\\\\WHITE8x8",
            edgeSize = 1,
        })
        eb:SetBackdropColor(0, 0, 0, 0.55)
        eb:SetBackdropBorderColor(1, 0.82, 0, 0.9)
        eb:SetSize(64, 20)
        eb:SetPoint("BOTTOMLEFT", tf, "BOTTOMLEFT", 9, 5)
        eb:SetFont(ns.FONT, 13, ns.hui and ns.hui.FontFlags and ns.hui.FontFlags("OUTLINE") or "OUTLINE")
        eb:SetTextColor(1, 0.82, 0)
        eb:SetJustifyH("CENTER")
        eb:SetAutoFocus(false)
        eb:SetTextInsets(4, 4, 0, 0)
        eb:SetNumeric(true)
        eb:Hide()
        tf.eb = eb
        local function CloseTarget()
            PD.tgtEditing = nil
            eb:Hide()
            tf.val:Show()
        end
        local function ApplyTarget()
            if not PD.cur or not PD.tgtEditing then CloseTarget() return end
            local v = tonumber(eb:GetText()) or 300
            v = math.max(1, math.min(300, math.floor(v)))
            local db = ProfDB()
            db.lvTarget = db.lvTarget or {}
            local old = tonumber(db.lvTarget[PD.cur]) or 300
            CloseTarget()
            if old == v then return end
            db.lvTarget[PD.cur] = (v >= 300) and nil or v
            if RA then RA.Invalidate() end
            PD.Render()
        end
        local cancelled = nil
        eb:SetScript("OnEnterPressed", function(self) self:ClearFocus() end)
        eb:SetScript("OnEscapePressed", function(self)
            cancelled = true
            CloseTarget()
            self:ClearFocus()
        end)
        eb:SetScript("OnEditFocusLost", function()
            if cancelled then cancelled = nil return end
            ApplyTarget()
        end)
        tf:SetScript("OnClick", function()
            if PD.tgtEditing then return end
            local v = PD.LvTarget()
            eb:SetText(v >= 300 and "" or tostring(v))
            PD.tgtEditing = true
            tf.val:Hide()
            eb:Show()
            eb:SetFocus()
            ns.PlaySound(1)
        end)
    end
''')))

# ── 4. PaintLvTiles：插在 PaintTool 之后 ────────────────────────────
EDITS.append(('paint_lvtiles', n('''    local rows = (n > 0) and (row + 1) or 0
    PD.toolRows = rows
    return (rows > 0) and (rows * (PD.TOOL_H + PD.TOOL_GAP) + PD.TOOL_BODY_GAP) or 0
end
'''), n('''    local rows = (n > 0) and (row + 1) or 0
    PD.toolRows = rows
    return (rows > 0) and (rows * (PD.TOOL_H + PD.TOOL_GAP) + PD.TOOL_BODY_GAP) or 0
end

-- ── 升级页信息卡（2026-10-10 B1）：每次渲染按 PD.lvSummary 刷新内容 ──────
-- lvSummary 由 PD.RowsLeveling（路线 / 购物清单两个分支）在渲染期写入。
function PD.PaintLvTiles()
    local tiles = PD.lvTiles
    if not (tiles and tiles.mode) then return 0 end
    if PD.tab ~= "leveling" or PD.setOpen then
        for _, k in ipairs({ "mode", "cost", "target", "snap" }) do tiles[k]:Hide() end
        return 0
    end
    local s = PD.lvSummary or {}
    local v = PD.LvTarget()
    local auto = s.auto and true or false
    local warnAuto = s.autoSetting and not s.ahOK
    local ageMin = s.snapshotAge
    ageMin = (ageMin and math.floor(ageMin / 60 + 0.5)) or 0
    local function TipOn(tf, lines)
        tf:SetScript("OnEnter", function(self)
            GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
            GameTooltip:ClearLines()
            for _, ln in ipairs(lines) do
                if ln[1] and ln[1] ~= "" then
                    GameTooltip:AddLine(ln[1], ln[2] or 1, ln[3] or 1, ln[4] or 1, true)
                end
            end
            GameTooltip:Show()
        end)
        tf:SetScript("OnLeave", function() GameTooltip:Hide() end)
    end
    tiles.mode.label:SetText(L["模式 · 点击切换"])
    tiles.mode.val:SetText(auto and L["自动计算"] or L["固定路线"])
    tiles.mode.val:SetTextColor(Unpack(auto and C_GOLD or C_WHITE))
    if warnAuto then
        tiles.mode:SetBackdropBorderColor(0.95, 0.75, 0.4, 0.9)
    else
        tiles.mode:SetBackdropBorderColor(0.45, 0.45, 0.45, 0.6)
    end
    local modeLines = {
        { auto and L["自动计算：依据 Auctionator 价格算最省钱的制作路线"]
               or L["固定路线：按资料整理的分段练法逐段冲技能"], 1, 0.82, 0 },
        { L["点击在固定 / 自动之间切换"], 0.7, 0.7, 0.7 },
    }
    if warnAuto then
        modeLines[#modeLines + 1] = { L["自动路线需要 Auctionator 的价格数据：请安装 Auctionator 并完成一次拍卖行扫描；当前显示固定路线。"],
                                      0.95, 0.75, 0.4 }
    end
    TipOn(tiles.mode, modeLines)
    tiles.cost.label:SetText(format(L["1 → %d 预计总花费"], s.target or v))
    local costLines
    if s.priced and s.total then
        tiles.cost.val:SetText(RA.MoneyStr(s.total))
        tiles.cost.val:SetTextColor(Unpack(C_GOLD))
        costLines = {}
        if s.recipes then
            costLines[#costLines + 1] = { format(L["配方 %d 种 · %d 次制作"], s.recipes, s.crafts or 0) }
            costLines[#costLines + 1] = { format(L["商人直售 %s · 图纸 %s"],
                                                 RA.MoneyStr(s.vendorTotal or 0),
                                                 RA.MoneyStr(s.formulasTotal or 0)), 0.7, 0.7, 0.7 }
        else
            costLines[#costLines + 1] = { format(L["材料 %d 种"], s.matsN or 0) }
        end
    else
        tiles.cost.val:SetText(L["—"])
        tiles.cost.val:SetTextColor(Unpack(C_GREY))
        costLines = { { L["价格数据不可用（安装并扫描 Auctionator 后显示金币）"], 0.7, 0.7, 0.7 } }
    end
    if (s.np or 0) > 0 then
        costLines[#costLines + 1] = { format(L["含无价材料 %d 种：花费为估算下限"], s.np),
                                      0.95, 0.75, 0.4 }
    end
    TipOn(tiles.cost, costLines)
    tiles.target.label:SetText(L["目标等级 · 点击修改"])
    tiles.target.val:SetText(v >= 300 and L["全程"] or tostring(v))
    tiles.target.val:SetTextColor(Unpack(C_WHITE))
    TipOn(tiles.target, { { L["每专业独立记忆；300 = 全程。点击修改"], 0.7, 0.7, 0.7 } })
    tiles.snap.label:SetText(L["价格快照"])
    if s.priced then
        tiles.snap.val:SetText(format(L["%d 分钟前 · Auctionator"], ageMin))
        tiles.snap.val:SetTextColor(0.55, 0.85, 0.6, 1)
        TipOn(tiles.snap, { { format(L["价格快照 %d 分钟前（Auctionator）"], ageMin), 0.7, 0.7, 0.7 } })
    else
        tiles.snap.val:SetText(L["未接入 Auctionator"])
        tiles.snap.val:SetTextColor(0.95, 0.75, 0.4, 1)
        TipOn(tiles.snap, { { L["安装 Auctionator 并完成一次拍卖行扫描后，这里显示价格快照年龄。"],
                              0.7, 0.7, 0.7 } })
    end
    local w3 = tiles.mode:GetWidth() + tiles.cost:GetWidth() + tiles.target:GetWidth()
    tiles.snap:SetWidth(math.max(120, PD.RIGHT_W - w3 - 3 * PD.LV_TILE_GAP))
    local x = PD.RIGHT_X
    for _, k in ipairs({ "mode", "cost", "target", "snap" }) do
        local tf = tiles[k]
        tf:ClearAllPoints()
        tf:SetPoint("TOPLEFT", PD.page, "TOPLEFT", x, -PD.BODY_TOP)
        x = x + tf:GetWidth() + PD.LV_TILE_GAP
        tf:Show()
    end
    return PD.LV_TILE_H + 6
end
''')))

# ── 5. RowsLeveling：无数据早退时清 lvSummary ───────────────────────
EDITS.append(('earlyret', n('''function PD.RowsLeveling(rows)
    local lv = LV[PD.cur]
    if not lv then return end
'''), n('''function PD.RowsLeveling(rows)
    local lv = LV[PD.cur]
    if not lv then PD.lvSummary = nil return end
''')))

# ── 6. RowsLeveling：购物清单分支写 lvSummary ───────────────────────
EDITS.append(('shop_branch', n('''    -- ── 购物清单子页（2026-10-09 v2）：固定 / 自动共用 ──
    if PD.autoPage == "shop" then
        PD.RowsAutoShop(rows, auto and res or FixedShopData(target))
        return
    end
'''), n('''    -- ── 购物清单子页（2026-10-09 v2）：固定 / 自动共用 ──
    if PD.autoPage == "shop" then
        local data = auto and res or FixedShopData(target)
        PD.lvSummary = {
            target = target, auto = auto,
            autoSetting = PD.Setting("autoRoute"),
            ahOK = (RA and RA.Available()) and true or false,
            priced = (data.priced and true) or false,
            total = data.total, snapshotAge = data.snapshotAge,
            matsN = #(data.mats or {}), np = CountUnpriced(data),
        }
        PD.RowsAutoShop(rows, data)
        return
    end
''')))

# ── 7. RowsLeveling：路线分支写 lvSummary（fOf 之后）────────────────
EDITS.append(('route_summary', n('''    local fOf = {}
    local flist = auto and (res.formulas or {}) or (fixedSum and fixedSum.formulas or {})
    for _, f in ipairs(flist) do fOf[f.spell] = f end
'''), n('''    local fOf = {}
    local flist = auto and (res.formulas or {}) or (fixedSum and fixedSum.formulas or {})
    for _, f in ipairs(flist) do fOf[f.spell] = f end

    -- 顶部信息卡供数（2026-10-10 B1）：PaintLvTiles 读 PD.lvSummary
    PD.lvSummary = {
        target = target, auto = auto,
        autoSetting = PD.Setting("autoRoute"),
        ahOK = (RA and RA.Available()) and true or false,
        priced = auto or ((fixedSum and fixedSum.priced) and true or false),
        total = auto and res.total or (fixedSum and fixedSum.total),
        snapshotAge = auto and res.snapshotAge or (fixedSum and fixedSum.snapshotAge),
        recipes = auto and #res.steps or nil,
        crafts = auto and (res.crafts or 0) or nil,
        vendorTotal = auto and res.vendorTotal or (fixedSum and fixedSum.vendorTotal),
        formulasTotal = auto and res.formulasTotal or (fixedSum and fixedSum.formulasTotal),
        matsN = (not auto) and fixedSum and #(fixedSum.mats or {}) or nil,
        np = auto and CountUnpriced(res) or (fixedSum and CountUnpriced(fixedSum)) or 0,
    }
''')))

# ── 8. 路线正文：自动分支头部三行（花费/统计/快照）上移信息卡 ────────
EDITS.append(('auto_head', n('''        if auto then
            PushHead(rows, format(L["1 → %d 自动路线（按拍卖行价格）"], target))
            -- 汇总条（2026-10-08 定稿）：首行总花费，第二行合并明细（路线页底部不再放合计）
            PushText(rows, format(L["预计总花费 %s"], RA.MoneyStr(res.total)), 16, C_GOLD)
            local ageMin = res.snapshotAge
            ageMin = (ageMin and math.floor(ageMin / 60 + 0.5)) or 0
            PushText(rows, format(L["配方 %d 种 · %d 次制作 · 商人直售 %s · 图纸 %s · 价格快照 %d 分钟前（Auctionator）"],
                                  #res.steps, res.crafts or 0, RA.MoneyStr(res.vendorTotal),
                                  RA.MoneyStr(res.formulasTotal), ageMin), 12, C_GREY)
            -- 缺口先报「已按估价回填」（琥珀），残余真无解才报红（2026-10-09）
'''), n('''        if auto then
            PushHead(rows, format(L["1 → %d 自动路线（按拍卖行价格）"], target))
            -- 汇总（总花费 / 配方统计 / 快照年龄）2026-10-10 起移到顶部信息卡
            -- 缺口先报「已按估价回填」（琥珀），残余真无解才报红（2026-10-09）
''')))

# ── 9. 路线正文：固定分支头部两行上移，保留无价 / 无价材料提示 ───────
EDITS.append(('fixed_head', n('''        else
            PushHead(rows, format(L["1 → %d 分段路线"], target))
            -- 固定路线金币（2026-10-09 v2）：材料 + 图纸，与自动路线同一价格层
            if fixedSum and fixedSum.priced then
                PushText(rows, format(L["需要金币 %s"], RA.MoneyStr(fixedSum.total)), 16, C_GOLD)
                local ageMin = fixedSum.snapshotAge
                ageMin = (ageMin and math.floor(ageMin / 60 + 0.5)) or 0
                PushText(rows, format(L["材料 %d 种 · 其中图纸 %s · 价格快照 %d 分钟前（Auctionator）"],
                                      #(fixedSum.mats or {}), RA.MoneyStr(fixedSum.formulasTotal), ageMin),
                         12, C_GREY)
                local np = CountUnpriced(fixedSum)
                if np > 0 then
                    PushText(rows, format(L["含无价材料 %d 种：花费为估算下限"], np), 12, { 0.95, 0.75, 0.4 })
                end
            elseif fixedSum then
                PushText(rows, L["价格数据不可用（安装并扫描 Auctionator 后显示金币）"], 12, C_GREY)
            end
'''), n('''        else
            PushHead(rows, format(L["1 → %d 分段路线"], target))
            -- 金币 / 材料 / 快照 2026-10-10 起移到顶部信息卡；无价时信息卡给提示
            if fixedSum and not fixedSum.priced then
                PushText(rows, L["价格数据不可用（安装并扫描 Auctionator 后显示金币）"], 12, C_GREY)
            elseif fixedSum then
                local np = CountUnpriced(fixedSum)
                if np > 0 then
                    PushText(rows, format(L["含无价材料 %d 种：花费为估算下限"], np), 12, { 0.95, 0.75, 0.4 })
                end
            end
''')))

# ── 10. Render：工具行 + 信息卡高度，tgtBox 段整体退役 ──────────────
EDITS.append(('render_toolh', n('''    local toolH = PD.PaintTool(tool, handler)
    PD.Layout(toolH)

    -- 目标等级输入框：仅升级页显示（工具行右端，红框位置）
    if PD.tgtBox then
        if PD.tab == "leveling" and not PD.setOpen then
            local tg = PD.tgtBox
            tg:ClearAllPoints()
            tg:SetPoint("TOPRIGHT", PD.page, "TOPRIGHT", -PAGE_INSET, -(PD.BODY_TOP))
            tg:Show()
            if not tg.eb:HasFocus() then
                local v = PD.LvTarget()
                tg.eb:SetText(v >= 300 and "" or tostring(v))
            end
        else
            PD.tgtBox:Hide()
        end
    end
'''), n('''    local toolH
    if PD.tab == "leveling" and not PD.setOpen then
        toolH = PD.PaintLvTiles() + PD.PaintTool(tool, handler, PD.LV_TILE_H + 6)
    else
        toolH = PD.PaintTool(tool, handler)
    end
    PD.Layout(toolH)
''')))

# ── 11. PickTabs：一键导入只在购物清单子页出现 ──────────────────────
EDITS.append(('impbtn_gate', n('''    if pf and pf.PaintImportBtn and PD.impBtn then
        pcall(pf.PaintImportBtn, PD.impBtn, PD.cur)
    end
end
'''), n('''    if pf and pf.PaintImportBtn and PD.impBtn then
        pcall(pf.PaintImportBtn, PD.impBtn, PD.cur)
    end
    -- 2026-10-10 B1：一键导入只在购物清单子页出现（路线页 / 设置页不占位）
    if PD.impBtn then
        local wantImp = PD.tab == "leveling" and PD.autoPage == "shop"
                        and (not PD.setOpen) and PD.cur ~= nil and PD.cur ~= "__index"
                        and LV[PD.cur] ~= nil and LV[PD.cur].steps ~= nil
        PD.impBtn:SetShown(wantImp and true or false)
    end
end
''')))


def load():
    with open(P, 'rb') as f:
        return f.read()

def main():
    check_only = '--check' in sys.argv
    data = load()
    bad = 0
    for name, old, new in EDITS:
        cnt = data.count(old)
        if cnt != 1:
            print('锚点 %s 命中 %d 次（期望 1）' % (name, cnt))
            bad += 1
    if bad:
        print('共 %d 条锚点异常，中止' % bad)
        return 2
    print('锚点体检：全部 %d 条恰好命中 1 次' % len(EDITS))
    if check_only:
        return 0
    for name, old, new in EDITS:
        if data.count(new) > 0 and data.count(old) == 1:
            pass
        data = data.replace(old, new, 1)
        print('已应用:', name)
    if data.count(b'\n') != data.count(b'\r\n'):
        print('致命：产生裸 LF，中止落盘')
        return 3
    with open(P, 'wb') as f:
        f.write(data)
    print('落盘完成，裸 LF = 0')
    return 0

if __name__ == '__main__':
    sys.exit(main())
