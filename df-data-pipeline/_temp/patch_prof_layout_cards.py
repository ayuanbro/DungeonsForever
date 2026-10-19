# 专业页容器卡版式 + 总览内容删改（锚定替换，全程 CRLF）
#  1) 常量：CARD_INSET(20)/NAV_PAD/CARD_NAV_R，RIGHT_X/BODY_* 重算
#  2) Build 顶部建 navCard/listCard 两张 L1 容器卡（先于所有按钮，垫底）
#  3) 旧 listCard 创建块删除；Layout/搜索框/HUD/齿轮锚点改 CARD_INSET
#  4) 总览：删简介状态行、删状态标签说明段；军需官行并入营地位置、图标换阵营 TGA
import io, sys

P = r"D:\workspace\DungeonsForever\Core\ProfessionUI.lua"
src = open(P, "rb").read().decode("utf-8")
crlf = src.count("\r\n")
assert src.count("\n") - crlf == 0, "unexpected bare LF"
t = src.replace("\r\n", "\n")

def rep(old, new, n=1):
    global t
    assert t.count(old) == n, "anchor x%d (want %d): %s" % (t.count(old), n, old[:80])
    t = t.replace(old, new)

# ── 1) 常量块 ──
rep("""PD.NAV_X, PD.NAV_TOP = PAGE_INSET, ROW_CLASS
PD.NAV_W = ((type(GetLocale) == "function") and GetLocale() == "enUS") and 184 or 148
PD.NAV_FS, PD.NAV_ICON = 16, 20
PD.NAV_ITEM_H, PD.NAV_GROUP_H, PD.NAV_GAP = 26, 22, 3
PD.NAV_LV_FS = 14
PD.RIGHT_X = PD.NAV_X + PD.NAV_W + 10
PD.RIGHT_W = CONTENT_W - PD.RIGHT_X - PAGE_INSET
PD.SUB_Y, PD.SUB_H, PD.SUB_W, PD.SUB_STEP = ROW_CLASS, 22, 70, 74
PD.BODY_TOP = PD.SUB_Y + PD.SUB_H + 10
PD.BODY_BOT = PAGE_INSET + 26
""",
"""PD.CARD_INSET = PAGE_INSET + (DG.GUTTER or 8)
PD.NAV_PAD = 8
PD.NAV_X, PD.NAV_TOP = PD.CARD_INSET + PD.NAV_PAD, PD.CARD_INSET + PD.NAV_PAD
PD.NAV_W = ((type(GetLocale) == "function") and GetLocale() == "enUS") and 184 or 148
PD.NAV_FS, PD.NAV_ICON = 16, 20
PD.NAV_ITEM_H, PD.NAV_GROUP_H, PD.NAV_GAP = 26, 22, 3
PD.NAV_LV_FS = 14
PD.CARD_NAV_R = PD.CARD_INSET + PD.NAV_W + 2 * PD.NAV_PAD
PD.RIGHT_X = PD.CARD_NAV_R + (DG.GUTTER or 8) + 8
PD.RIGHT_W = CONTENT_W - PD.RIGHT_X - PD.CARD_INSET
PD.SUB_Y, PD.SUB_H, PD.SUB_W, PD.SUB_STEP = PD.CARD_INSET + 8, 22, 70, 74
PD.BODY_TOP = PD.SUB_Y + PD.SUB_H + 10
PD.BODY_BOT = PD.CARD_INSET + 8
PD.FAC_ICON = {
    a = "Interface\\\\AddOns\\\\DungeonsForever\\\\Media\\\\icon\\\\FACTION\\\\FactionIcon_Alliance",
    h = "Interface\\\\AddOns\\\\DungeonsForever\\\\Media\\\\icon\\\\FACTION\\\\FactionIcon_Horde",
}
""")

# ── 2) MakeCard 助手 + Build 顶部建两卡 ──
rep("""function PD.Build(page)
    if PD.built then return end
    PD.built = true
    PD.page = page
    PD.navKey = {}
""",
"""function PD.MakeCard(f)
    local c = CreateFrame("Frame", nil, f, "BackdropTemplate")
    if ns.hui and ns.hui.layer and ns.hui.BuildRoundedBG then
        ns.hui.BuildRoundedBG(c, 6, ns.hui.layer.L1, "both", true, 1)
    else
        c:SetBackdrop({
            bgFile = "Interface\\\\Buttons\\\\WHITE8x8",
            edgeFile = "Interface\\\\Buttons\\\\WHITE8x8",
            edgeSize = 1,
        })
        c:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG)
        c:SetBackdropBorderColor(1, 1, 1, DG.LOOT_CARD_EDGE)
    end
    return c
end

function PD.Build(page)
    if PD.built then return end
    PD.built = true
    PD.page = page
    PD.navKey = {}

    PD.navCard = PD.MakeCard(page)
    PD.navCard:SetPoint("TOPLEFT", page, "TOPLEFT", PD.CARD_INSET, -PD.CARD_INSET)
    PD.navCard:SetPoint("BOTTOMRIGHT", page, "BOTTOMLEFT",
                        PD.CARD_NAV_R, PD.CARD_INSET)
    PD.listCard = PD.MakeCard(page)
""")

# ── 3a) 删旧 listCard 创建块 ──
rep("""    -- 列表容器卡（2026-10-11 色阶规整）：HUI 走 r6 圆角 + L1 实色 + 白 10% 细边，
    -- 确立页内「容器 L1 < 内卡 L2 < 悬停 L4」阶梯；非 HUI 回落旧半透明底。
    local listCard = CreateFrame("Frame", nil, page, "BackdropTemplate")
    if ns.hui and ns.hui.layer and ns.hui.BuildRoundedBG then
        ns.hui.BuildRoundedBG(listCard, 6, ns.hui.layer.L1, "both", true, 1)
    else
        listCard:SetBackdrop({
            bgFile = "Interface\\\\Buttons\\\\WHITE8x8",
            edgeFile = "Interface\\\\Buttons\\\\WHITE8x8",
            edgeSize = 1,
        })
        listCard:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG)
        listCard:SetBackdropBorderColor(1, 1, 1, DG.LOOT_CARD_EDGE)
    end
    PD.listCard = listCard

    local divider""",
"""    local divider""")

# ── 3b) 齿轮 / HUD / 搜索框 / Layout 锚点 ──
rep('gear:SetPoint("TOPRIGHT", page, "TOPLEFT", PD.RIGHT_X + PD.RIGHT_W, -PD.SUB_Y)',
    'gear:SetPoint("TOPRIGHT", page, "TOPLEFT", PD.RIGHT_X + PD.RIGHT_W - 8, -PD.SUB_Y)')
rep("""    hudBtn:SetPoint("TOPRIGHT", page, "TOPRIGHT",
                    -PAGE_INSET, -(PD.BODY_TOP + PD.LV_TILE_H + 8))""",
"""    hudBtn:SetPoint("TOPRIGHT", page, "TOPRIGHT",
                    -PD.CARD_INSET, -(PD.BODY_TOP + PD.LV_TILE_H + 8))""")
rep("""            PD.searchBox:SetPoint("TOPRIGHT", PD.page, "TOPRIGHT",
                                  -PAGE_INSET, -(PD.BODY_TOP))""",
"""            PD.searchBox:SetPoint("TOPRIGHT", PD.page, "TOPRIGHT",
                                  -PD.CARD_INSET, -(PD.BODY_TOP))""")
rep("""    PD.scroll:SetPoint("BOTTOMRIGHT", PD.page, "BOTTOMRIGHT", -PAGE_INSET, bot)
    PD.listCard:ClearAllPoints()
    PD.listCard:SetPoint("TOPLEFT", PD.page, "TOPLEFT",
                         PD.RIGHT_X - PD.LIST_PAD, -(top - PD.LIST_PAD))
    PD.listCard:SetPoint("BOTTOMRIGHT", PD.page, "BOTTOMRIGHT",
                         -PAGE_INSET, bot - PD.LIST_PAD)""",
"""    PD.scroll:SetPoint("BOTTOMRIGHT", PD.page, "BOTTOMRIGHT", -PD.CARD_INSET, bot)
    PD.listCard:ClearAllPoints()
    PD.listCard:SetPoint("TOPLEFT", PD.page, "TOPLEFT",
                         PD.RIGHT_X - PD.LIST_PAD, -PD.CARD_INSET)
    PD.listCard:SetPoint("BOTTOMRIGHT", PD.page, "BOTTOMRIGHT",
                         -PD.CARD_INSET, PD.CARD_INSET)""")

# ── 4a) 删简介状态行 ──
rep("""    PushHead(rows, L["简介"], 1)
    rows[#rows + 1] = {
        kind = "row", h = PD.ROW_H1, col = 1,
        text = p.status or L["未标注"], right = p.kind or "",
    }
    local lede""",
"""    PushHead(rows, L["简介"], 1)
    local lede""")

# ── 4b) 删「状态标签说明」段（状态行删除后已无指向）──
rep("""        PushGap(rows)
        PushHead(rows, L["状态标签说明"])
        local seen, list = {}, {}
        for _, slug in ipairs(D.order or {}) do
            local p = D.pro[slug]
            if p and p.status and not seen[p.status] then
                seen[p.status] = true
                list[#list + 1] = p.status
            end
        end
        for _, st in ipairs(list) do
            rows[#rows + 1] = { kind = "text", text = "· " .. st, color = C_GREY }
        end
        return
""",
"""        PushGap(rows)
        return
""")

# ── 4c) 军需官行：阵营图标 + 位置并入副行；营地行只在该侧无军需官时保留 ──
rep("""        for _, side in ipairs({ "a", "h" }) do
            local fc = (side == "a") and C_ALLIANCE or C_HORDE
            local camp = lv and lv.camps and lv.camps[side]
            if camp then
                rows[#rows + 1] = {
                    kind = "row", col = 1, nameColor = fc,
                    text = format(L["营地 · %s"], camp[3] or "?"),
                    sub = format("%s · %s", PD.CampZoneName(camp[6], tostring(camp[2] or "")), tostring(camp[1] or "")),
                    right = format("%.1f, %.1f", camp[4] or 0, camp[5] or 0),
                    lines = {
                        { L["点击：在地图上标记此位置"], 1, 0.82, 0 },
                        { format("%s %.1f, %.1f", tostring(camp[2] or ""), camp[4] or 0, camp[5] or 0), 0.75, 0.75, 0.75 },
                    },
                    act = function() PD.MarkCampPoint(camp[6], camp[4], camp[5]) end,
                }
            end
            local vd = lv and lv.vendor and lv.vendor[side]
            if vd then
                rows[#rows + 1] = {
                    kind = "row", col = 1, nameColor = fc, icon = vd[4],
                    text = format(L["军需官 · %s"], tostring(vd[1])),
                    sub = tostring(vd[3] or ""),
                    right = format("%.1f, %.1f", vd[5] or 0, vd[6] or 0),
                    lines = {
                        { L["点击：在地图上标记该 NPC"], 1, 0.82, 0 },
                        { format("%.1f, %.1f", vd[5] or 0, vd[6] or 0), 0.75, 0.75, 0.75 },
                    },
                    act = function() PD.MarkCampPoint(vd[7], vd[5], vd[6]) end,
                }
            end
        end""",
"""        for _, side in ipairs({ "a", "h" }) do
            local fc = (side == "a") and C_ALLIANCE or C_HORDE
            local camp = lv and lv.camps and lv.camps[side]
            local vd = lv and lv.vendor and lv.vendor[side]
            if vd then
                local loc = tostring(vd[3] or "")
                if camp then
                    loc = format("%s · %s · %s", tostring(camp[1] or ""),
                                 PD.CampZoneName(camp[6], tostring(camp[2] or "")),
                                 tostring(camp[3] or ""))
                end
                local lines = {
                    { L["点击：在地图上标记该 NPC"], 1, 0.82, 0 },
                    { format("%.1f, %.1f", vd[5] or 0, vd[6] or 0), 0.75, 0.75, 0.75 },
                }
                if camp then
                    lines[#lines + 1] = {
                        format(L["营地位置 %.1f, %.1f"], camp[4] or 0, camp[5] or 0),
                        0.75, 0.75, 0.75,
                    }
                end
                rows[#rows + 1] = {
                    kind = "row", col = 1, nameColor = fc, icon = PD.FAC_ICON[side],
                    text = format(L["军需官 · %s"], tostring(vd[1])),
                    sub = loc,
                    right = format("%.1f, %.1f", vd[5] or 0, vd[6] or 0),
                    lines = lines,
                    act = function() PD.MarkCampPoint(vd[7], vd[5], vd[6]) end,
                }
            elseif camp then
                rows[#rows + 1] = {
                    kind = "row", col = 1, nameColor = fc,
                    text = format(L["营地 · %s"], camp[3] or "?"),
                    sub = format("%s · %s", PD.CampZoneName(camp[6], tostring(camp[2] or "")), tostring(camp[1] or "")),
                    right = format("%.1f, %.1f", camp[4] or 0, camp[5] or 0),
                    lines = {
                        { L["点击：在地图上标记此位置"], 1, 0.82, 0 },
                        { format("%s %.1f, %.1f", tostring(camp[2] or ""), camp[4] or 0, camp[5] or 0), 0.75, 0.75, 0.75 },
                    },
                    act = function() PD.MarkCampPoint(camp[6], camp[4], camp[5]) end,
                }
            end
        end""")

open(P, "wb").write(t.replace("\n", "\r\n").encode("utf-8"))
print("patched OK")
