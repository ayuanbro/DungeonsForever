# -*- coding: utf-8 -*-
"""采矿升级页：+熔炼模式（路线进度卡点击切换）+ 采集行上游样式（副行=大多在 X、Y…）"""
P = r"D:/workspace/DungeonsForever/Core/ProfessionUI.lua"
d = open(P, "rb").read()
e = b"\r\n"

def rep(old, new, tag):
    global d
    o = old.encode("utf-8").replace(b"\n", e)
    n = new.encode("utf-8").replace(b"\n", e)
    c = d.count(o)
    assert c == 1, (tag, c)
    d = d.replace(o, n)

# ── 1) SMELT_TBL + GatherMode：定义在所有使用点之前（local 顺序铁律）──
rep("""-- 采集四类（2026-10-11）：开放「升级」页签，走静态推荐路线（无价格/概率，无从自动计算）
PD.GATHER_SLUGS = { mining = true, herbalism = true, skinning = true, fishing = true }""",
"""-- 采集四类（2026-10-11）：开放「升级」页签，走静态推荐路线（无价格/概率，无从自动计算）
PD.GATHER_SLUGS = { mining = true, herbalism = true, skinning = true, fishing = true }
-- 熔炼路线表（2026-10-11 用户）：{ 锭物品ID, 训练师学习技能 }；区间 = [learn, 下一档 learn-1]。
--   名字/图标/品质由客户端 GetItemInfo 给出（查不到显示占位）；仅 mining 有采集/熔炼双模式。
local SMELT_TBL = {
    { 2840, 1 }, { 3576, 65 }, { 2841, 75 }, { 2842, 75 }, { 3575, 125 },
    { 3859, 155 }, { 3577, 155 }, { 3860, 175 }, { 6037, 210 },
    { 12359, 230 }, { 11371, 230 }, { 12360, 275 }, { 17771, 300 },
}
-- 采集页子模式（跨重载记忆，存 ProfDB.gatherMode）；非 mining 恒为采集
function PD.GatherMode(slug)
    if slug ~= "mining" then return "gather" end
        return (ProfDB().gatherMode == "smelt") and "smelt" or "gather"
end""", "tbl")

# ── 2) RowsGatherRoute：熔炼分支（插在 fishing 分支前）──
rep("""    if slug == "fishing" then
        -- 按门槛分档：{门槛, {区域...}}""",
"""    if PD.GatherMode(slug) == "smelt" then
        -- 熔炼路线：锭 → 可学区间（区间推进口径与采集一致）
        PushHead(rows, L["熔炼升级路线（全程）"])
        if curLv then
            PushText(rows, format(L["当前技能 %d，绿色为可练区间：练到下一档再换锭。"], curLv), 11, C_GREY)
        else
            PushText(rows, L["未学到该专业，先找训练师学习；学习后这里显示当前位置。"], 11, C_GREY)
        end
        PushGap(rows)
        for i, t in ipairs(SMELT_TBL) do
            local lo = t[2]
            local hi = (SMELT_TBL[i + 1] and SMELT_TBL[i + 1][2] or 301) - 1
            if hi < lo then hi = lo end
            local active = curLv and curLv >= lo and curLv <= hi
            local nm = DG.ItemName(t[1])
            if not (type(nm) == "string" and nm ~= "") then nm = format(L["物品 #%d"], t[1]) end
            rows[#rows + 1] = {
                kind = "row", h = PD.ROW_H1,
                it = { t[1] }, qItem = t[1],
                nameColor = active and { 0.4, 0.9, 0.45 } or nil,
                text = nm,
                right = (hi > lo) and format(L["%d - %d"], lo, hi) or tostring(lo),
            }
        end
        return
    end
    if slug == "fishing" then
        -- 按门槛分档：{门槛, {区域...}}""", "smelt")

# ── 3) 采集行上游样式：副行=大多在 X、Y…（区间移除 right2，副行改区域句）──
rep("""            sub = (#items > 0) and table.concat(items, "  ") or nil,
            right = (hi > lo) and format(L["%d - %d"], lo, hi) or tostring(lo),
            right2 = PD.ZoneText(zones, 3),
            lines = lines,""",
"""            sub = format(L["大多在 %s"], PD.ZoneText(zones, 3)),
            right = (hi > lo) and format(L["%d - %d"], lo, hi) or tostring(lo),
            lines = lines,""", "style")

# ── 4) PaintGatherTiles：进度按模式取值 + 路线进度卡点击切换（仅 mining）──
rep("""    tiles.scheme.label:SetText(L["路线进度"])
    tiles.scheme.val:SetText(prog)
    PD.TipTile(tiles.scheme, { { L["列表中绿色高亮行 = 推荐当前采集的区间"], 0.7, 0.7, 0.7 } })
    PD.PaintTileBorder(tiles.scheme, { 1, 1, 1, 0.10 })""",
"""    tiles.scheme.label:SetText(L["路线进度"])
    local smelt = PD.GatherMode(PD.cur) == "smelt"
    if smelt and curLv then
        -- 熔炼口径：落在哪个可学区间
        for i, t in ipairs(SMELT_TBL) do
            local lo = t[2]
            local hi = (SMELT_TBL[i + 1] and SMELT_TBL[i + 1][2] or 301) - 1
            if hi < lo then hi = lo end
            if curLv >= lo and curLv <= hi then
                prog = (hi > lo) and format(L["%d - %d"], lo, hi) or tostring(lo)
                break
            end
        end
    end
    tiles.scheme.val:SetText((PD.cur == "mining") and
        ((smelt and L["熔炼"] or L["采集"]) .. " " .. prog) or prog)
    if PD.cur == "mining" then
        tiles.scheme:SetScript("OnClick", function()
            ProfDB().gatherMode = smelt and "gather" or "smelt"
            PD.Render()
            ns.PlaySound(1)
        end)
    else
        tiles.scheme:SetScript("OnClick", nil)
    end
    PD.TipTile(tiles.scheme, (PD.cur == "mining") and {
        { L["点击切换：采集 ⇄ 熔炼"], 0.9, 0.78, 0.35 },
        { smelt and L["列表中绿色高亮行 = 当前技能可练的熔炼区间"]
            or L["列表中绿色高亮行 = 推荐当前采集的区间"], 0.7, 0.7, 0.7 },
    } or { { L["列表中绿色高亮行 = 推荐当前采集的区间"], 0.7, 0.7, 0.7 } })
    PD.PaintTileBorder(tiles.scheme, (PD.cur == "mining") and { 1, 0.82, 0, 0.55 } or { 1, 1, 1, 0.10 })""", "tiles")

open(P, "wb").write(d)
print("gather-smelt patch OK")
