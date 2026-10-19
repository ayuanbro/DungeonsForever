# -*- coding: utf-8 -*-
"""HUD 第三轮反馈补丁：区间并入名字行 / 角标描边 / 倒圆角 / 标题图标修复 / 购物最早等级"""
import io

p = "Core/ProfFollow.lua"
s = io.open(p, encoding="utf-8", newline="").read()
orig = len(s)

def rep(old, new, n=1):
    global s
    c = s.count(old)
    assert c == n, "anchor %d (expect %d): %r" % (c, n, old[:70])
    s = s.replace(old, new)

# ---- R1 顶部：ProfIconTex（短名补 Interface\Icons\ 前缀，修标题图标不显示）+ RoundFrame 倒圆角助手 ----
rep("local SetOutline = Host.SetOutline\n",
"""local SetOutline = Host.SetOutline

-- 专业图标：数据里是短名（trade_leatherworking），SetTexture 直接喂短名会静默失败
local function ProfIconTex(name)
    if not name then return Host.FALLBACK_ICON end
    if type(name) == "string" and not name:find("\\\\", 1, true) then
        return "Interface\\\\Icons\\\\" .. name
    end
    return name
end

-- 倒圆角描边（HUI 主题走 BuildRoundBorder；非 HUI 返回 nil，保留原方角 backdrop 描边）
local function RoundFrame(fr, radius, col)
    if not (ns.hui and ns.hui.BuildRoundBorder) then return nil end
    local pieces = ns.hui.BuildRoundBorder(fr, radius, col, fr, "OVERLAY", "both", 1) or {}
    for _, tex in ipairs(pieces) do tex:SetShown(true) end
    return pieces
end
""")

# ---- R2 主窗 / 段卡 / 购物面板 倒圆角 ----
rep("""    f:SetBackdropColor(0, 0, 0, 0.62)
    f:SetBackdropBorderColor(1, 1, 1, 0.18)""",
"""    f:SetBackdropColor(0, 0, 0, 0.62)
    f:SetBackdropBorderColor(1, 1, 1, 0.18)
    f.__round = RoundFrame(f, 6, { 1, 1, 1, 0.25 })
    if f.__round then f:SetBackdropBorderColor(0, 0, 0, 0) end""")

rep("""    f.card:SetBackdropColor(1, 1, 1, 0.06)
    f.card:SetBackdropBorderColor(0, 0, 0, 0)""",
"""    f.card:SetBackdropColor(1, 1, 1, 0.06)
    f.card:SetBackdropBorderColor(0, 0, 0, 0)
    f.card.__round = RoundFrame(f.card, 6, { 0, 1, 0.4, 0.9 })""")

rep("""    f.shop:SetBackdropColor(1, 1, 1, 0.04)
    f.shop:SetBackdropBorderColor(1, 1, 1, 0.14)""",
"""    f.shop:SetBackdropColor(1, 1, 1, 0.04)
    f.shop:SetBackdropBorderColor(1, 1, 1, 0.14)
    f.shop.__round = RoundFrame(f.shop, 6, { 1, 1, 1, 0.14 })
    if f.shop.__round then f.shop:SetBackdropBorderColor(0, 0, 0, 0) end""")

# ---- R3 标题图标换 ProfIconTex ----
rep("    f.icon:SetTexture((p and p.icon) or Host.FALLBACK_ICON)",
    "    f.icon:SetTexture(ProfIconTex(p and p.icon))")

# ---- R4 数量角标加描边（对齐升级页 TBL_MAT_CNT 样式：THICKOUTLINE + 黑影） ----
rep("""        local bd = MakeFS(f.card, 14, C_GOLD, "RIGHT")
        bd:SetWordWrap(false)
        bd:Hide()
        rowsMatBadge[i] = bd""",
"""        local bd = MakeFS(f.card, 14, C_GOLD, "RIGHT")
        bd:SetFont(ns.FONT or "Fonts\\\\FRIZQT__.TTF", 14, "THICKOUTLINE")
        bd:SetShadowColor(0, 0, 0, 1)
        bd:SetShadowOffset(1, -1)
        bd:SetWordWrap(false)
        bd:Hide()
        rowsMatBadge[i] = bd""")

# ---- R5 段卡第二行 FS（crafts），range 改为名右侧内联 ----
rep("""    f.card.range = MakeFS(f.card, 14, C_GREY, "LEFT")
    f.card.range:SetWordWrap(false)
    f.card.range:SetPoint("TOPLEFT", f.card, "TOPLEFT", 42, -33)""",
"""    f.card.range = MakeFS(f.card, 14, C_GREY, "LEFT")
    f.card.range:SetWordWrap(false)
    f.card.range:SetPoint("TOPLEFT", f.card, "TOPLEFT", 42, -12)

    f.card.crafts = MakeFS(f.card, 14, C_GREY, "LEFT")
    f.card.crafts:SetWordWrap(false)
    f.card.crafts:SetPoint("TOPLEFT", f.card, "TOPLEFT", 42, -33)""")

# ---- R6 购物行「最早等级X使用」标签池 ----
rep("local rowsMatBadge = {}         -- 材料行数量角标池（挂图标右下角，显示单次用量）",
"""local rowsMatBadge = {}         -- 材料行数量角标池（挂图标右下角，显示单次用量）
local rowsShopTag = {}          -- 购物行「最早等级X使用」右缘标签池""")

rep("    for i = 1, SHOP_MAX + 1 do rowsShop[i] = MakeLine(f.shop, 14, C_TEXT) end",
"""    for i = 1, SHOP_MAX + 1 do rowsShop[i] = MakeLine(f.shop, 14, C_TEXT) end
    for i = 1, SHOP_MAX + 1 do
        rowsShopTag[i] = MakeFS(f.shop, 14, C_DIM, "RIGHT")
        rowsShopTag[i]:SetWordWrap(false)
        rowsShopTag[i]:Hide()
    end""")

# ---- R7 Paint：段卡边框改走圆角片段重着色 ----
rep("        card:SetBackdropBorderColor(accent[1], accent[2], accent[3], isCur and 0.9 or 0.35)",
"""        if card.__round then
            for _, tex in ipairs(card.__round) do
                tex:SetVertexColor(accent[1], accent[2], accent[3], isCur and 0.9 or 0.35)
            end
        else
            card:SetBackdropBorderColor(accent[1], accent[2], accent[3], isCur and 0.9 or 0.35)
        end""")

# ---- R8 Paint：名字+区间同行 / crafts 第二行 / 宽度分配 ----
rep("""        card.name:SetText(SpellName(seg[3]))

        -- 当前段剩余制作次数（浏览预览段用全量）
        local crafts = seg[4] or 0
        local remaining = crafts
        if vi == s.step then
            local span = math.max(1, seg[2] - seg[1])
            remaining = math.ceil(crafts * math.min(1, (seg[2] - math.max(s.skill or 0, seg[1])) / span))
        end
        local nMat, pend, canCraft = paintMats(seg, rm, sold, w - 8, remaining)
        pending = pending or pend

        -- 区间 · 总共约N次制作 · 材料还可制作N次
        local rangeText = format(L["%d – %d"], seg[1], seg[2]) .. " · " .. format(L["总共约%d次制作"], crafts)
        if canCraft then rangeText = rangeText .. " · " .. format(L["材料还可制作%d次"], canCraft) end
        card.range:SetText(rangeText)
        card.range:SetWidth(w - 42)

        -- 右上角：已学习（绿）/ 来源（灰）——替代原「当前」角标与底部来源行
        local PDm = ns.ProfModule
        local src, detail
        if PDm and PDm.LevelSrc then
            src, detail = PDm.LevelSrc(rec)
        end
        local learned = IsLearned(seg[3])
        local tagText = learned and L["已学习"] or (src or L["向训练师学习"])
        if detail and not learned then tagText = tagText .. " · " .. detail end
        card.srcTag:SetText(tagText)
        card.srcTag:SetTextColor(Unpack(learned and C_OK or C_GREY))
        local tagW = 90
        if PDm and PDm.TextW then
            local okW, tw = pcall(PDm.TextW, tagText, 14)
            if okW and type(tw) == "number" then tagW = math.ceil(tw) end
        end
        card.srcTag:SetWidth(tagW)
        card.name:SetWidth(math.max(60, w - 42 - tagW - 10))""",
"""        local PDm = ns.ProfModule
        local nmText = SpellName(seg[3])
        card.name:SetText(nmText)

        -- 当前段剩余制作次数（浏览预览段用全量）
        local crafts = seg[4] or 0
        local remaining = crafts
        if vi == s.step then
            local span = math.max(1, seg[2] - seg[1])
            remaining = math.ceil(crafts * math.min(1, (seg[2] - math.max(s.skill or 0, seg[1])) / span))
        end
        local nMat, pend, canCraft = paintMats(seg, rm, sold, w - 8, remaining)
        pending = pending or pend

        -- 右上角：已学习（绿）/ 来源（灰）——替代原「当前」角标与底部来源行
        local src, detail
        if PDm and PDm.LevelSrc then
            src, detail = PDm.LevelSrc(rec)
        end
        local learned = IsLearned(seg[3])
        local tagText = learned and L["已学习"] or (src or L["向训练师学习"])
        if detail and not learned then tagText = tagText .. " · " .. detail end
        card.srcTag:SetText(tagText)
        card.srcTag:SetTextColor(Unpack(learned and C_OK or C_GREY))
        local tagW = 90
        if PDm and PDm.TextW then
            local okW, tw = pcall(PDm.TextW, tagText, 14)
            if okW and type(tw) == "number" then tagW = math.ceil(tw) end
        end
        card.srcTag:SetWidth(tagW)

        -- 区间挪到配方名右侧（同行）；第二行只留次数信息
        local rangeText = format(L["%d – %d"], seg[1], seg[2])
        card.range:SetText(rangeText)
        local craftText = format(L["总共约%d次制作"], crafts)
        if canCraft then craftText = craftText .. " · " .. format(L["材料还可制作%d次"], canCraft) end
        card.crafts:SetText(craftText)

        local rangeW, nameW = 40, 90
        if PDm and PDm.TextW then
            local okW, tw = pcall(PDm.TextW, rangeText, 14)
            if okW and type(tw) == "number" then rangeW = math.ceil(tw) end
            local okW2, tw2 = pcall(PDm.TextW, nmText, 16)
            if okW2 and type(tw2) == "number" then nameW = math.ceil(tw2) end
        end
        local avail = math.max(60, w - 42 - tagW - 10 - rangeW - 10)
        local nameX = math.min(nameW, avail)
        card.name:SetWidth(avail)
        card.range:ClearAllPoints()
        card.range:SetPoint("TOPLEFT", f.card, "TOPLEFT", 42 + nameX + 10, -12)
        card.range:SetWidth(rangeW + 6)""")

# ---- R9 shopList：记录首次出现的段落等级 ----
rep("""                if not e then
                    e = { id = m[1], need = 0 }
                    totals[m[1]] = e
                    order[#order + 1] = m[1]
                end""",
"""                if not e then
                    e = { id = m[1], need = 0, at = seg[1] }
                    totals[m[1]] = e
                    order[#order + 1] = m[1]
                end""")

# ---- R10 购物绘制：行宽让位 + 右缘「最早等级X使用」 ----
rep("""            if soldSet(slug)[e.id] then txt = txt .. " · " .. L["商人直卖"] end
            line:SetText(txt)
            line:ClearAllPoints()
            line:SetPoint("TOPLEFT", f.shop, "TOPLEFT", 8, -(30 + n * 20))
            line:SetWidth(w)
            line:Show()
            n = n + 1""",
"""            if soldSet(slug)[e.id] then txt = txt .. " · " .. L["商人直卖"] end
            line:SetText(txt)
            line:ClearAllPoints()
            line:SetPoint("TOPLEFT", f.shop, "TOPLEFT", 8, -(30 + n * 20))
            line:SetWidth(w - 120)
            line:Show()
            local tag = rowsShopTag[n + 1]
            tag:SetText(L["最早等级%d使用"]:format(e.at or 0))
            tag:ClearAllPoints()
            tag:SetPoint("TOPRIGHT", f.shop, "TOPRIGHT", -8, -(32 + n * 20))
            tag:SetWidth(116)
            tag:Show()
            n = n + 1""")

rep("""            line:SetText(format(L["…还有 %d 种，进手册升级页看全部"], #list - n))
            line:ClearAllPoints()
            line:SetPoint("TOPLEFT", f.shop, "TOPLEFT", 8, -(30 + n * 20))
            line:SetWidth(w)
            line:Show()
            n = n + 1""",
"""            line:SetText(format(L["…还有 %d 种，进手册升级页看全部"], #list - n))
            line:ClearAllPoints()
            line:SetPoint("TOPLEFT", f.shop, "TOPLEFT", 8, -(30 + n * 20))
            line:SetWidth(w)
            line:Show()
            rowsShopTag[n + 1]:Hide()
            n = n + 1""")

rep("        for i = n + 1, #rowsShop do rowsShop[i]:Hide() end",
"""        for i = n + 1, #rowsShop do rowsShop[i]:Hide() end
        for i = n + 1, #rowsShopTag do rowsShopTag[i]:Hide() end""")

io.open(p, "w", encoding="utf-8", newline="").write(s)
print("patched OK, len %d -> %d" % (orig, len(s)))
