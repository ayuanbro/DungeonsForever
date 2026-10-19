# -*- coding: utf-8 -*-
"""详情页三张分组卡片：加「展开 / 折叠」（2026-10-01 用户：「这三张卡片呢，我希望都可以支持展开和折叠的」）。

用户拍板：
  ① 默认三张全展开；
  ② 折叠状态**存进配置**（跨会话记住）；
  ③ 卡头右侧只保留掉落现有的「N 件」，技能卡 / 攻略卡不加新计数。

做法（照 DungeonUI 掉落页分组头那套现成范式：整条热区 + 箭头两态 + 点击音）：
  · 每张卡一个卡头热区 Button（宽随卡、高 = 卡头高），点它收起 / 展开；
  · 箭头走 Media/textures/arrow.tga（原生朝上）—— ▾ 展开中 / ▴ 收起中，两态互斥；
  · 标题整体右让出箭头位（M.BLK_TITLE_X）；
  · 折叠状态真源 = DB().ui.mapCards（true = 收起，nil = 展开），读侧「非 true 即展开」。
用法：python patch_card_collapse.py --check   只体检锚点；不带参数 = 落盘。
"""
import sys

P = 'Core/MapUI.lua'
raw = open(P, 'rb').read().decode('utf-8')
assert raw.count('\r\n') == 0, 'MapUI.lua 应为 LF'
src = raw

PATCHES = []


def rep(name, old, new, count=1):
    PATCHES.append((name, old, new, count))


# ---- ① 常量区：折叠相关三个量 -------------------------------------------------
rep('常量',
    'M.ROW_GAP = 4                    -- 卡片内条目间距（掉落行 / 技能行共用同一值）\n',
    'M.ROW_GAP = 4                    -- 卡片内条目间距（掉落行 / 技能行共用同一值）\n'
    '\n'
    '-- ★★ 卡头可点折叠（用户 2026-10-01：「这三张卡片呢，我希望都可以支持展开和折叠的」）——\n'
    '--   热区 = 整条卡头（宽随卡、高 = 卡头高），点它收起 / 展开；箭头在最左（arrow.tga 原生朝上），\n'
    '--   标题整体右让出箭头位。折叠状态**存进配置**（用户点名「记住，存进配置」）：\n'
    '--   DB().ui.mapCards.<loot|skill|guide> —— true = 收起，缺省 / nil = 展开（老存档照样三张全展开）。\n'
    'M.BLK_MIN_H = M.BLK_HDR         -- 折叠后卡高 = 一行卡头（同一来源，不写第二个 26）\n'
    'M.BLK_TITLE_X = 24               -- 卡标题左缩 = BLK_PAD(8) + 箭头(10) + 间距(6)\n'
    'M.BLK_ARROW = 10                 -- 折叠箭头边长\n')

# ---- ② 折叠状态入口（真源 = 配置） -------------------------------------------
rep('CardClosed',
    'local function PiecesSetShown(t, on)\n'
    '    for i = 1, #(t or {}) do t[i]:SetShown(on) end\n'
    'end\n',
    'local function PiecesSetShown(t, on)\n'
    '    for i = 1, #(t or {}) do t[i]:SetShown(on) end\n'
    'end\n'
    '\n'
    '-- ★★ 卡片折叠状态：真源 = 配置（DB().ui.mapCards），缺档整档补齐（老存档没这个键 ⇒ 三张全展开）。\n'
    '--   收起写 true、展开写 nil —— 与「隐藏boss」同口径：存档里不留 false，读侧一律「非 true 即展开」。\n'
    'function M.CardClosed()\n'
    '    local ui = ns.DB().ui\n'
    '    local c = ui.mapCards\n'
    '    if type(c) ~= "table" then c = {} ui.mapCards = c end\n'
    '    return c\n'
    'end\n')

# ---- ③ 建卡头热区 + 两态箭头 --------------------------------------------------
rep('卡头热区',
    '        if ns.hui and ns.hui.BuildRoundedBG then\n'
    '            ns.hui.BuildRoundedBG(b, M.BLK_RADIUS, { 1, 1, 1, M.BLK_BG }, "both", true, 1)\n'
    '        end\n'
    '        b:Hide()\n',
    '        if ns.hui and ns.hui.BuildRoundedBG then\n'
    '            ns.hui.BuildRoundedBG(b, M.BLK_RADIUS, { 1, 1, 1, M.BLK_BG }, "both", true, 1)\n'
    '        end\n'
    '        -- ★ 卡头热区（整条卡头可点）+ 折叠箭头两态（▾ 展开中 / ▴ 收起中，arrow.tga 原生朝上）。\n'
    '        --   热区只盖卡头那一条 ⇒ 展开时不挡下面的条目；收起时卡只剩这一条，正好铺满。\n'
    '        b.hit = CreateFrame("Button", nil, b)\n'
    '        b.hit:RegisterForClicks("LeftButtonUp")\n'
    '        b.hit:SetHeight(M.BLK_MIN_H)\n'
    '        b.arrD = b:CreateTexture(nil, "ARTWORK")\n'
    '        b.arrD:SetSize(M.BLK_ARROW, M.BLK_ARROW)\n'
    '        b.arrD:SetTexture("Interface\\\\AddOns\\\\DungeonsForever\\\\Media\\\\textures\\\\arrow.tga")\n'
    '        b.arrD:SetRotation(math.pi)\n'
    '        b.arrU = b:CreateTexture(nil, "ARTWORK")\n'
    '        b.arrU:SetSize(M.BLK_ARROW, M.BLK_ARROW)\n'
    '        b.arrU:SetTexture("Interface\\\\AddOns\\\\DungeonsForever\\\\Media\\\\textures\\\\arrow.tga")\n'
    '        for _, at in ipairs({ b.arrD, b.arrU }) do\n'
    '            at:SetVertexColor(Unpack(C_GOLD))\n'
    '            at:SetPoint("TOPLEFT", b, "TOPLEFT", M.BLK_PAD, -(M.BLK_TITLE_TOP + 4))\n'
    '        end\n'
    '        b.hit:SetScript("OnClick", function(self)\n'
    '            local key = self.__key\n'
    '            if not key then return end\n'
    '            local c = M.CardClosed()\n'
    '            c[key] = not c[key] or nil      -- 收起 = true；展开 = nil（存档里不留 false）\n'
    '            ns.PlaySound(1)\n'
    '            M.SyncSide()\n'
    '        end)\n'
    '        b.hit:SetScript("OnEnter", function(self)\n'
    '            if not self.__key then return end\n'
    '            GameTooltip:SetOwner(self, "ANCHOR_TOP")\n'
    '            GameTooltip:ClearLines()\n'
    '            GameTooltip:AddLine(L["点击折叠 / 展开该组"], 1, 1, 1, true)\n'
    '            GameTooltip:Show()\n'
    '        end)\n'
    '        b.hit:SetScript("OnLeave", function() GameTooltip:Hide() end)\n'
    '        -- ★ 热区是 EnableMouse 的按钮（压在滚动容器里）⇒ 显式把滚轮转发给详情滚动条，\n'
    '        --   否则鼠标停在卡头上时整页滚不动（项目铁律：子控件一律显式转发滚轮）。\n'
    '        b.hit:EnableMouseWheel(true)\n'
    '        b.hit:SetScript("OnMouseWheel", function(self, delta)\n'
    '            M.WheelScroll(detScroll, detChild, delta)\n'
    '        end)\n'
    '        b:Hide()\n')

# ---- ④ 三张卡各自的折叠键 ----------------------------------------------------
rep('折叠键',
    '    local blkLoot, blkSkill, blkGuide = blocks[1], blocks[2], blocks[3]\n',
    '    local blkLoot, blkSkill, blkGuide = blocks[1], blocks[2], blocks[3]\n'
    '    blkLoot.__key, blkSkill.__key, blkGuide.__key = "loot", "skill", "guide"\n')

# ---- ⑤ 卡头统一摆法（热区宽 + 箭头两态 + 标题让位） ---------------------------
rep('LayoutCardHead',
    '    r:SetSize(rowW, M.CARD_H)\n'
    '    r:Show()\n'
    'end\n',
    '    r:SetSize(rowW, M.CARD_H)\n'
    '    r:Show()\n'
    'end\n'
    '\n'
    '-- 摆一张卡片的卡头：热区铺满卡宽（左 + 右两条锚点）+ 箭头两态互斥 + 标题让出箭头位。\n'
    '--   ★ 标题必须每轮重锚（清空后不锚定 ⇒ 落父容器中心、被卡内内容盖住 = 实机「标题消失」）。\n'
    'local function LayoutCardHead(blk, ttl, isClosed)\n'
    '    blk.hit:ClearAllPoints()\n'
    '    blk.hit:SetPoint("TOPLEFT", blk, "TOPLEFT", 0, 0)\n'
    '    blk.hit:SetPoint("RIGHT", blk, "RIGHT", 0, 0)\n'
    '    blk.hit:Show()\n'
    '    blk.arrD:SetShown(not isClosed)\n'
    '    blk.arrU:SetShown(isClosed)\n'
    '    ttl:ClearAllPoints()\n'
    '    ttl:SetPoint("TOPLEFT", blk, "TOPLEFT", M.BLK_TITLE_X, -M.BLK_TITLE_TOP)\n'
    'end\n')

# ---- ⑥ 详情页进入时取一次折叠状态 --------------------------------------------
rep('取折叠态',
    '            local rowW = frame.detChildW or (frame.innerW - M.BLK_PAD * 2)\n',
    '            local rowW = frame.detChildW or (frame.innerW - M.BLK_PAD * 2)\n'
    '            local closed = M.CardClosed()\n')

# ---- ⑦ 卡片高度：收起的卡只留一行卡头 ----------------------------------------
rep('卡片高度',
    '            local ltH = M.BLK_HDR + ltContentH + M.BLK_PAD\n'
    '            local skH = M.BLK_HDR + skContentH + M.BLK_PAD\n'
    '            local gdH = M.BLK_HDR + gdTextH + M.BLK_PAD\n',
    '            local ltH = closed.loot and M.BLK_MIN_H or (M.BLK_HDR + ltContentH + M.BLK_PAD)\n'
    '            local skH = closed.skill and M.BLK_MIN_H or (M.BLK_HDR + skContentH + M.BLK_PAD)\n'
    '            local gdH = closed.guide and M.BLK_MIN_H or (M.BLK_HDR + gdTextH + M.BLK_PAD)\n')

# ---- ⑧ 掉落卡：卡头 + 内容随折叠开关 -----------------------------------------
rep('掉落卡',
    '            frame.detLtTtl:ClearAllPoints()\n'
    '            frame.detLtTtl:SetPoint("TOPLEFT", blkLoot, "TOPLEFT", M.BLK_PAD, -M.BLK_TITLE_TOP)\n'
    '            frame.detLtCnt:ClearAllPoints()\n'
    '            frame.detLtCnt:SetPoint("TOPRIGHT", blkLoot, "TOPRIGHT", -M.BLK_PAD, -(M.BLK_TITLE_TOP + 1))\n'
    '            frame.detLtCnt:SetText((L["%d 件"] or "%d 件"):format(#(items or {})))\n'
    '            by = -M.BLK_HDR\n'
    '            for i = 1, nLoot do\n'
    '                layoutLootRow(frame.lootRows[i], items[i], by, rowW)\n'
    '                by = by - (M.CARD_H + M.ROW_GAP)\n'
    '            end\n'
    '            for i = nLoot + 1, M.MAX_LOOT do frame.lootRows[i]:Hide() end\n'
    '            frame.detLtNote:SetShown(nLoot == 0)\n'
    '            frame.detLtNote:ClearAllPoints()\n'
    '            frame.detLtNote:SetPoint("TOPLEFT", blkLoot, "TOPLEFT", M.BLK_PAD, by)\n',
    '            LayoutCardHead(blkLoot, frame.detLtTtl, closed.loot)\n'
    '            frame.detLtCnt:ClearAllPoints()\n'
    '            frame.detLtCnt:SetPoint("TOPRIGHT", blkLoot, "TOPRIGHT", -M.BLK_PAD, -(M.BLK_TITLE_TOP + 1))\n'
    '            frame.detLtCnt:SetText((L["%d 件"] or "%d 件"):format(#(items or {})))\n'
    '            by = -M.BLK_HDR\n'
    '            -- 收起 ⇒ 上界取 0（一条不摆），尾循环从 1 起把所有行收回池里（含上一轮显示过的）\n'
    '            for i = 1, (closed.loot and 0 or nLoot) do\n'
    '                layoutLootRow(frame.lootRows[i], items[i], by, rowW)\n'
    '                by = by - (M.CARD_H + M.ROW_GAP)\n'
    '            end\n'
    '            for i = (closed.loot and 1 or nLoot + 1), M.MAX_LOOT do frame.lootRows[i]:Hide() end\n'
    '            frame.detLtNote:SetShown(nLoot == 0 and not closed.loot)\n'
    '            frame.detLtNote:ClearAllPoints()\n'
    '            frame.detLtNote:SetPoint("TOPLEFT", blkLoot, "TOPLEFT", M.BLK_PAD, by)\n')

# ---- ⑨ 技能卡：卡头 + 行随折叠开关 -------------------------------------------
rep('技能卡头',
    '                frame.detSkTtl:ClearAllPoints()\n'
    '                frame.detSkTtl:SetPoint("TOPLEFT", blkSkill, "TOPLEFT", M.BLK_PAD, -M.BLK_TITLE_TOP)\n'
    '                by = -M.BLK_HDR\n'
    '                for i = 1, nSk do\n',
    '                LayoutCardHead(blkSkill, frame.detSkTtl, closed.skill)\n'
    '                by = -M.BLK_HDR\n'
    '                -- 收起 ⇒ 上界取 0（一条不摆）；下面的尾循环从 1 起收回池里\n'
    '                for i = 1, (closed.skill and 0 or nSk) do\n')

rep('技能卡尾',
    '            for i = nSk + 1, M.MAX_SKILL do\n'
    '                frame.skillRows[i].__sid = nil\n'
    '                frame.skillRows[i]:Hide()\n'
    '            end\n',
    '            for i = (closed.skill and 1 or nSk + 1), M.MAX_SKILL do\n'
    '                frame.skillRows[i].__sid = nil\n'
    '                frame.skillRows[i]:Hide()\n'
    '            end\n')

# ---- ⑩ 攻略卡：卡头 + 正文随折叠开关 -----------------------------------------
rep('攻略卡',
    '                frame.detGdTtl:ClearAllPoints()\n'
    '                frame.detGdTtl:SetPoint("TOPLEFT", blkGuide, "TOPLEFT", M.BLK_PAD, -M.BLK_TITLE_TOP)\n'
    '                frame.detGd:ClearAllPoints()\n'
    '                frame.detGd:SetPoint("TOPLEFT", blkGuide, "TOPLEFT", M.BLK_PAD, -M.BLK_HDR)\n'
    '                frame.detGd:Show()\n',
    '                LayoutCardHead(blkGuide, frame.detGdTtl, closed.guide)\n'
    '                if closed.guide then\n'
    '                    frame.detGd:Hide()\n'
    '                else\n'
    '                    frame.detGd:ClearAllPoints()\n'
    '                    frame.detGd:SetPoint("TOPLEFT", blkGuide, "TOPLEFT", M.BLK_PAD, -M.BLK_HDR)\n'
    '                    frame.detGd:Show()\n'
    '                end\n')


def main():
    out = src
    bad = 0
    for name, old, new, cnt in PATCHES:
        n = out.count(old)
        if n != cnt:
            print('[锚点失配] %s：命中 %d 次（期望 %d）' % (name, n, cnt))
            bad += 1
            continue
        out = out.replace(old, new, cnt)
        print('[OK] %s' % name)
    if bad:
        print('中止：%d 处锚点不匹配' % bad)
        return 2
    if len(sys.argv) > 1 and sys.argv[1] == '--check':
        print('体检通过（未落盘）')
        return 0
    open(P, 'wb').write(out.encode('utf-8'))
    print('已落盘 %s（%d 行 → %d 行）' % (P, src.count('\n'), out.count('\n')))
    return 0


if __name__ == '__main__':
    sys.exit(main())
