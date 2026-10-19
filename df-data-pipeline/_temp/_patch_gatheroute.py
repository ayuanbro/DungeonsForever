# -*- coding: utf-8 -*-
"""采集专业升级路线页（2026-10-11 用户拍板）：
- TabsFor 给 mining/herbalism/skinning/fishing 开 leveling 页签（复用页签名分流）
- RowsGatherRoute：mining/herbalism 区间段 + skinning 原生区间 + fishing 门槛档，当前技能绿色定位
- PaintGatherTiles：复用 lvTiles 三卡（当前技能/路线进度/路线范围），制造页 OnClick 清除
- TipOn 提为 PD.TipTile 供两处复用
"""
P = r"D:/workspace/DungeonsForever/Core/ProfessionUI.lua"
d = open(P, "rb").read()
e = b"\r\n"  # 本文件 CRLF 基线

def rep(old, new, tag):
    global d
    o = old.encode("utf-8").replace(b"\n", e)
    n = new.encode("utf-8").replace(b"\n", e)
    c = d.count(o)
    assert c == 1, (tag, c)
    d = d.replace(o, n)

# ── 1) 常量：采集 slug 集合 ──
rep("""PD.SETTING_DEF.autoScheme = "cheapest"  -- 自动路线方案：最省钱/材料成本/次数最少/乐观计数""",
    """PD.SETTING_DEF.autoScheme = "cheapest"  -- 自动路线方案：最省钱/材料成本/次数最少/乐观计数

-- 采集四类（2026-10-11）：开放「升级」页签，走静态推荐路线（无价格/概率，无从自动计算）
PD.GATHER_SLUGS = { mining = true, herbalism = true, skinning = true, fishing = true }""",
    "const")

# ── 2) TabsFor：采集 slug 也开升级页签 ──
rep("""    if GA and (GA[slug] or (slug == "fishing" and GA.fishing)) then out[#out + 1] = "gather" end
    if LV and LV[slug] then out[#out + 1] = "leveling" end""",
    """    if GA and (GA[slug] or (slug == "fishing" and GA.fishing)) then out[#out + 1] = "gather" end
    if (LV and LV[slug]) or (PD.GATHER_SLUGS and PD.GATHER_SLUGS[slug]) then out[#out + 1] = "leveling" end""",
    "tabsfor")

# ── 3) TipOn 提为 PD.TipTile（PaintLvTiles 内保留 local 别名，调用点零改动）──
rep("""    local function TipOn(tf, lines)
        tf:SetScript("OnEnter", function(self)
            if tf.__hov then for _, t in ipairs(tf.__hov) do t:Show() end end
            GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
            GameTooltip:ClearLines()
            for _, ln in ipairs(lines) do
                if ln[1] and ln[1] ~= "" then
                    GameTooltip:AddLine(ln[1], ln[2] or 1, ln[3] or 1, ln[4] or 1, true)
                end
            end
            GameTooltip:Show()
        end)
        tf:SetScript("OnLeave", function()
            if tf.__hov then for _, t in ipairs(tf.__hov) do t:Hide() end end
            GameTooltip:Hide()
        end)
    end
    tiles.mode.label:SetText(L["模式 · 点击切换"])""",
    """    local TipOn = PD.TipTile
    tiles.mode.label:SetText(L["模式 · 点击切换"])""",
    "tipon-out")

rep("""function PD.PaintLvTiles()
    local tiles = PD.lvTiles
    if not (tiles and tiles.mode) then return 0 end
    if PD.tab ~= "leveling" or PD.setOpen then""",
    """-- 信息卡悬停提示（PaintLvTiles / PaintGatherTiles 共用；进出由 __hov 胶囊切换）
function PD.TipTile(tf, lines)
    tf:SetScript("OnEnter", function()
        if tf.__hov then for _, t in ipairs(tf.__hov) do t:Show() end end
        GameTooltip:SetOwner(tf, "ANCHOR_RIGHT")
        GameTooltip:ClearLines()
        for _, ln in ipairs(lines) do
            if ln[1] and ln[1] ~= "" then
                GameTooltip:AddLine(ln[1], ln[2] or 1, ln[3] or 1, ln[4] or 1, true)
            end
        end
        GameTooltip:Show()
    end)
    tf:SetScript("OnLeave", function()
        if tf.__hov then for _, t in ipairs(tf.__hov) do t:Hide() end end
        GameTooltip:Hide()
    end)
end

function PD.PaintLvTiles()
    local tiles = PD.lvTiles
    if not (tiles and tiles.mode) then return 0 end
    -- 采集专业升级页走独立三卡（当前技能/路线进度/路线范围）
    if PD.GATHER_SLUGS[PD.cur] then return PD.PaintGatherTiles() end
    if PD.tab ~= "leveling" or PD.setOpen then""",
    "paintlvtiles-head")

# ── 4) 渲染分发：leveling 分支分流 ──
rep("""    elseif PD.tab == "leveling" then
        tool, handler = PD.LevelTool()""",
    """    elseif PD.tab == "leveling" then
        if PD.GATHER_SLUGS[PD.cur] then
            PD.lvSplit = false
            PD.gridSplit = false
            PD.autoPage = nil   -- 制造页购物清单子页残留清掉
            PD.RowsGatherRoute(rows)
        else
        tool, handler = PD.LevelTool()""",
    "dispatch-a")

rep("""        if PD.autoPage == "shop" then
            PD.lvSplit = true
            PD.splitLW = math.floor((PD.RIGHT_W - 2 * PD.LIST_PAD - PD.OV_GUT) * PD.SHOP_SPLIT)
            PD.splitRW = PD.RIGHT_W - 2 * PD.LIST_PAD - PD.OV_GUT - PD.splitLW
        else
            PD.lvSplit = false
        end
        PD.RowsLeveling(rows)""",
    """        if PD.autoPage == "shop" then
            PD.lvSplit = true
            PD.splitLW = math.floor((PD.RIGHT_W - 2 * PD.LIST_PAD - PD.OV_GUT) * PD.SHOP_SPLIT)
            PD.splitRW = PD.RIGHT_W - 2 * PD.LIST_PAD - PD.OV_GUT - PD.splitLW
        else
            PD.lvSplit = false
        end
        PD.RowsLeveling(rows)
        end""",
    "dispatch-b")

# ── 5) PaintGatherTiles（挂在 PaintLvTiles 前、TipTile 后）+ RowsGatherRoute ──
rep("""function PD.PaintLvTiles()
    local tiles = PD.lvTiles
    if not (tiles and tiles.mode) then return 0 end
    -- 采集专业升级页走独立三卡（当前技能/路线进度/路线范围）""",
    """-- 采集升级页信息卡：复用 lvTiles 帧，三卡 = 当前技能 / 路线进度 / 路线范围
function PD.PaintGatherTiles()
    local tiles = PD.lvTiles
    if PD.tab ~= "leveling" or PD.setOpen then
        for _, k in ipairs({ "mode", "scheme", "cost", "target", "snap" }) do tiles[k]:Hide() end
        return 0
    end
    tiles.target:Hide()
    tiles.snap:Hide()
    -- 制造页点击行为（切模式/切方案）不得残留到采集页
    tiles.mode:SetScript("OnClick", nil)
    tiles.scheme:SetScript("OnClick", nil)
    tiles.cost:SetScript("OnClick", nil)
    local _learned = PD.ProfLearned()
    local curLv = _learned and _learned[PD.cur] and _learned[PD.cur].cur or nil
    -- 当前进度：落在哪个推荐段/门槛档
    local g = GA and (GA[PD.cur] or (PD.cur == "fishing" and GA.fishing))
    local prog = "-"
    if g and #g > 0 and curLv then
        for i, t in ipairs(g) do
            local lo, hi
            if PD.cur == "fishing" then
                lo = t[2]
                hi = (g[i + 1] and g[i + 1][2] or lo + 1) - 1
                if hi < lo then hi = lo end
            elseif PD.cur == "skinning" then
                lo, hi = t[1][1], t[1][2]
            else
                lo = t[2]
                hi = (g[i + 1] and g[i + 1][2] or 301) - 1
                if hi < lo then hi = lo end
            end
            if curLv >= lo and curLv <= hi then
                prog = (hi > lo) and format(L["%d - %d"], lo, hi) or tostring(lo)
                break
            end
        end
    end
    tiles.mode.label:SetText(L["当前技能"])
    tiles.mode.val:SetText(curLv and tostring(curLv) or L["未学"])
    PD.TipTile(tiles.mode, { { L["读取角色当前的专业技能值"], 0.7, 0.7, 0.7 } })
    PD.PaintTileBorder(tiles.mode, { 1, 1, 1, 0.10 })
    tiles.scheme.label:SetText(L["路线进度"])
    tiles.scheme.val:SetText(prog)
    PD.TipTile(tiles.scheme, { { L["列表中绿色高亮行 = 推荐当前采集的区间"], 0.7, 0.7, 0.7 } })
    PD.PaintTileBorder(tiles.scheme, { 1, 1, 1, 0.10 })
    tiles.cost.label:SetText(L["路线范围"])
    tiles.cost.val:SetText("1 - 300")
    PD.TipTile(tiles.cost, { { L["静态推荐路线（全程显示）：按资料整理的采集区间推进，不含价格与概率，无需价格插件"], 0.7, 0.7, 0.7 } })
    PD.PaintTileBorder(tiles.cost, { 1, 1, 1, 0.10 })
    -- 三卡均分（五卡槽位用三卡：等宽 tw，余数不用）
    local usable = PD.RIGHT_W - PD.LIST_PAD - 4 * PD.LV_TILE_GAP
    local tw = math.floor(usable / 5)
    tiles.mode:SetWidth(tw)
    tiles.scheme:SetWidth(tw)
    tiles.cost:SetWidth(tw)
    local x = PD.RIGHT_X
    for _, k in ipairs({ "mode", "scheme", "cost" }) do
        local tf = tiles[k]
        tf:ClearAllPoints()
        tf:SetPoint("TOPLEFT", PD.page, "TOPLEFT", x, -PD.BODY_TOP)
        x = x + tf:GetWidth() + PD.LV_TILE_GAP
        tf:Show()
    end
    return PD.LV_TILE_H + 8
end

function PD.PaintLvTiles()
    local tiles = PD.lvTiles
    if not (tiles and tiles.mode) then return 0 end
    -- 采集专业升级页走独立三卡（当前技能/路线进度/路线范围）""",
    "paintgathertiles")

# ── 6) RowsGatherRoute（插在 RowsGather 之后）──
rep("""-- ── 固定路线 · 目标裁剪 / 聚合（2026-10-09 v2）─────────────────────────────""",
    """-- ── 采集升级路线（2026-10-11）：mining/herbalism/skinning/fishing ──────────
-- 静态推荐路线（无价格/概率，无从自动计算）：按技能区间/门槛推进 + 当前技能绿色定位。
function PD.RowsGatherRoute(rows)
    local slug = PD.cur
    local g = GA and (GA[slug] or (slug == "fishing" and GA.fishing))
    if not g or #g == 0 then return end
    local _learned = PD.ProfLearned()
    local curLv = _learned and _learned[slug] and _learned[slug].cur or nil

    if slug == "fishing" then
        -- 按门槛分档：{门槛, {区域...}}
        PushHead(rows, format(L["钓鱼升级路线（%d 处水域）"], #g))
        PushText(rows, L["按技能门槛分档推进：下竿必涨，到下一档门槛就换区域。"], 11, C_GREY)
        PushGap(rows)
        local bands = {}
        for _, ed in ipairs(g) do
            local b = bands[#bands]
            if b and b[1] == ed[2] then b[2][#b[2] + 1] = ed[1]
            else bands[#bands + 1] = { ed[2], { ed[1] } } end
        end
        for bi, band in ipairs(bands) do
            local nxt = bands[bi + 1]
            local active = curLv and curLv >= band[1] and (not nxt or curLv < nxt[1])
            local names = {}
            for _, zid in ipairs(band[2]) do
                names[#names + 1] = DG.ZoneName(zid) or format("#%d", zid)
            end
            rows[#rows + 1] = {
                kind = "row", h = PD.ROW_H1,
                text = format(L["技能 %d 起"], band[1]),
                sub = table.concat(names, "、"),
                nameColor = active and { 0.4, 0.9, 0.45 } or nil,
                lines = { { active and L["◆ 推荐当前就练这一档"] or
                    (nxt and format(L["练到 %d 换下一档"], nxt[1]) or L["练满为止"]),
                    0.62, 0.62, 0.62 } },
            }
        end
        return
    end

    -- mining / herbalism / skinning：段 → 区间 → 产出 → 区域分布
    PushHead(rows, L["采集升级路线（全程）"])
    if curLv then
        PushText(rows, format(L["当前技能 %d，绿色为推荐段：采到区间上缘再换下一段。"], curLv), 11, C_GREY)
    else
        PushText(rows, L["未学到该专业，先找训练师学习；学习后这里显示当前位置。"], 11, C_GREY)
    end
    PushGap(rows)
    for i, t in ipairs(g) do
        local lo, hi, ids, zones
        if slug == "skinning" then
            lo, hi, ids, zones = t[1][1], t[1][2], t[2], t[3]
        else
            lo, ids, zones = t[2], t[1], t[3]
            hi = (g[i + 1] and g[i + 1][2] or 301) - 1
            if hi < lo then hi = lo end   -- 同起点双段（如采矿 230 两种矿）不再反转
        end
        local active = curLv and curLv >= lo and curLv <= hi
        local items, head, headName = {}, nil, nil
        for j, id in ipairs(ids) do
            local nm = DG.ItemName(id)
            if not (type(nm) == "string" and nm ~= "") then nm = format(L["物品 #%d"], id) end
            if j == 1 then head, headName = id, nm else items[#items + 1] = nm end
        end
        local lines = {}
        if #items > 0 then
            lines[#lines + 1] = { format(L["产出：%s"], table.concat(items, "  ")), 0.62, 0.62, 0.62 }
        end
        lines[#lines + 1] = { format(L["分布：%s"], PD.ZoneText(zones)), 0.62, 0.62, 0.62 }
        rows[#rows + 1] = {
            kind = "row", h = PD.ROW_H1,
            it = head and { head } or nil,
            qItem = head,
            nameColor = active and { 0.4, 0.9, 0.45 } or nil,
            text = headName or "?",
            sub = (#items > 0) and table.concat(items, "  ") or nil,
            right = (hi > lo) and format(L["%d - %d"], lo, hi) or tostring(lo),
            right2 = PD.ZoneText(zones, 3),
            lines = lines,
        }
    end
end

-- ── 固定路线 · 目标裁剪 / 聚合（2026-10-09 v2）─────────────────────────────""",
    "rowsgatherroute")

open(P, "wb").write(d)
print("main patch OK")
