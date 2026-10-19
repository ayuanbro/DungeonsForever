# -*- coding: utf-8 -*-
"""升级路线行：四档技能色阶条（占用原来源行）+ 名字右侧来源卡片。

一次原子操作：读全文 → 逐条断言锚点唯一 → 写回 → 回读校验。
（同一批文件另有并发会话在改，必须避免「读-改-写」被夹断。）

改动面：
  Core/ProfessionUI.lua
    1) PD.Row          : 建 4 段色底 + 4 个数字 + 落点竖线 + 卡片热区/底/文字
    2) PD.RowBlk 之前   : 常量 + PD.LvTier / PD.PaintSkillBar / PD.HideSkillBar /
                         PD.PaintCard / PD.CardOf
    3) PD.BindRow      : lvstep 分支——来源行让位给色阶条，名字右侧摆卡片
    4) PD.RowsLeveling : 循环里量卡片宽 → avail 扣掉；spec 带 sbVals/sbTier/card
    5) PD.WipeRow      : 切页时收干净色阶条与卡片
  Locales/zhTW.lua, Locales/enUS.lua : 补「训练师」「图纸」两个短标签
"""
import sys

ROOT = r'D:\workspace\DungeonsForever'


def load(p):
    with open(p, 'rb') as f:
        return f.read().decode('utf-8')


def save(p, s):
    with open(p, 'wb') as f:
        f.write(s.encode('utf-8'))


def rep(t, old, new, tag, count=1):
    n = t.count(old)
    if n != count:
        print('!! [%s] 锚点命中 %d 次，要求 %d 次' % (tag, n, count))
        print('   old = %r' % (old[:160],))
        sys.exit(1)
    print('OK [%s] 锚点唯一 (%d)' % (tag, count))
    return t.replace(old, new)


# ══════════════════════════════════════════════════════════════════════
# Core/ProfessionUI.lua
# ══════════════════════════════════════════════════════════════════════
P = ROOT + r'\Core\ProfessionUI.lua'
raw = load(P)
before_bytes = len(raw.encode('utf-8'))
assert raw.count('\r\n') > 0, '源文件不是 CRLF？'
assert (raw.count('\n') - raw.count('\r\n')) == 0, '源文件混有裸 LF'
t = raw.replace('\r\n', '\n')

# ── 1. PD.Row：色阶条 + 卡片骨架 ────────────────────────────────────────
A1 = '''    r.dv = MakeFS(r, 11, C_GREY, "RIGHT")
    r.dv:SetText("")
    r.dv:SetWordWrap(false)
    r.dv:Hide()
'''
N1 = A1 + '''    -- 2026-10-09 四轮（用户）：「升级路线」每行要显示该配方的四档技能阈值
    --   （学 / 黄 / 绿 / 灰），并给出「当前技能等级落在哪一档」的位置。
    --   布局：色阶条占用**原来的来源行**（名字正下方），来源压成名字右侧的小卡片。
    --   ★ 全部在 Row 里一次建好，渲染期只摆位 / 改文本。
    --   ★ 帧上的自定义字段一律 __ 前缀（桩铁律：非 __ 字段未赋值就索引会现造 function）。
    r.__sbBg, r.__sbTx = {}, {}
    for k = 1, 4 do
        local bg = r:CreateTexture(nil, "ARTWORK")
        bg:SetColorTexture(1, 1, 1, 1)
        bg:Hide()
        r.__sbBg[k] = bg
        local tx = MakeFS(r, PD.SB_FS, C_WHITE, "CENTER")
        tx:SetText("")
        tx:SetWordWrap(false)
        tx:Hide()
        r.__sbTx[k] = tx
    end
    r.__sbPin = r:CreateTexture(nil, "OVERLAY")
    r.__sbPin:SetWidth(2)
    r.__sbPin:SetColorTexture(1, 1, 1, 0.9)
    r.__sbPin:Hide()
    r.__cardZone = CreateFrame("Button", nil, r)
    r.__cardZone:Hide()
    PD.WireTipZone(r.__cardZone, r)
    r.__cardBg = r:CreateTexture(nil, "BORDER")
    r.__cardBg:SetColorTexture(1, 1, 1, 0.18)
    r.__cardBg:Hide()
    r.__cardTx = MakeFS(r, 11, C_TEXT, "LEFT")
    r.__cardTx:SetText("")
    r.__cardTx:SetWordWrap(false)
    r.__cardTx:Hide()
'''
t = rep(t, A1, N1, 'A1 PD.Row 骨架')

# ── 2. 常量 + 五个函数（插在 PD.RowBlk 定义之前）────────────────────────
A2 = 'function PD.RowBlk(r, j)\n'
N2 = '''-- ── 升级路线行：四档技能色阶条 + 来源卡片（2026-10-09 四轮，用户）────────────
-- 四档语义（WoW 专业惯例）：学得(橙/必升) → 黄(大概率) → 绿(小概率) → 灰(不再提升)。
--   ★ 四档**等分**而不是按等级跨度：数据里 learn == yellow 极常见（如 150/150/162/175），
--     按真实跨度画「必升」那档宽度就是 0 —— 会缺一块。等分 + 落点竖线更稳。
PD.SB_H  = 12            -- 色阶条高
PD.SB_DY = -8            -- 色阶条 y（= 原来源行的位置）
PD.SB_FS = 11            -- 段内数字字号
PD.CARD_PAD, PD.CARD_GAP = 6, 6
PD.SB_COL = {
    { 1.00, 0.50, 0.25 },   -- 1 橙：学得 / 必升
    { 1.00, 0.82, 0.00 },   -- 2 黄：大概率提升
    { 0.25, 0.75, 0.25 },   -- 3 绿：小概率提升
    { 0.55, 0.58, 0.64 },   -- 4 灰：不再提升
}
PD.SB_INK = {
    { 0.10, 0.06, 0.02 },
    { 0.12, 0.09, 0.00 },
    { 0.04, 0.12, 0.03 },
    { 1.00, 1.00, 1.00 },
}
PD.CARD_COL = {
    trainer = { 0.29, 0.33, 0.40 },
    drop    = { 0.42, 0.27, 0.66 },
    vendor  = { 0.54, 0.42, 0.12 },
}
PD.CARD_INK = {
    trainer = { 0.81, 0.85, 0.89 },
    drop    = { 0.91, 0.86, 1.00 },
    vendor  = { 1.00, 0.91, 0.66 },
}

-- 当前技能等级落在第几档（1 橙 / 2 黄 / 3 绿 / 4 灰）；没阈值数据返回 nil。
function PD.LvTier(skill, learn, yellow, green, grey)
    if not skill then return nil end
    if not (learn or yellow or green or grey) then return nil end
    if grey and skill >= grey then return 4 end
    if green and skill >= green then return 3 end
    if yellow and skill >= yellow then return 2 end
    return 1
end

-- 摆四档色阶条：条宽 = 名字列宽（PD.LV_NAME_W），四段等分，段内写该档阈值。
--   vals = { learn, yellow, green, grey }；tier = PD.LvTier(...)；dim = 已过段落灰显。
function PD.PaintSkillBar(r, vals, tier, dim)
    local seg = PD.LV_NAME_W / 4
    local a1, a2 = dim and 0.35 or 1, dim and 0.55 or 1
    for k = 1, 4 do
        local bg, tx = r.__sbBg[k], r.__sbTx[k]
        bg:ClearAllPoints()
        bg:SetPoint("LEFT", r, "LEFT", PD.LV_NAME_X + (k - 1) * seg, PD.SB_DY)
        bg:SetSize(seg, PD.SB_H)
        bg:SetColorTexture(Unpack(PD.SB_COL[k]))
        bg:SetAlpha(a1)
        bg:Show()
        tx:ClearAllPoints()
        tx:SetPoint("CENTER", bg, "CENTER", 0, 0)
        tx:SetTextColor(Unpack(PD.SB_INK[k]))
        tx:SetAlpha(a2)
        tx:SetText(vals[k] and tostring(vals[k]) or "")
        tx:Show()
    end
    if tier then
        r.__sbPin:ClearAllPoints()
        r.__sbPin:SetPoint("CENTER", r, "LEFT", PD.LV_NAME_X + (tier - 0.5) * seg, PD.SB_DY)
        r.__sbPin:SetSize(2, PD.SB_H + 6)
        r.__sbPin:SetAlpha(dim and 0.35 or 1)
        r.__sbPin:Show()
    else
        r.__sbPin:Hide()
    end
end

function PD.HideSkillBar(r)
    for k = 1, 4 do
        r.__sbBg[k]:Hide()
        r.__sbTx[k]:SetText("")
        r.__sbTx[k]:Hide()
    end
    r.__sbPin:Hide()
end

-- 来源卡片（名字右侧）。悬停走 __tipLines 出明细；点击：商人 → 落图，
--   图纸 → 走 Shift 点击发物品链接（__it）。
function PD.PaintCard(r, card)
    local z, bg, tx = r.__cardZone, r.__cardBg, r.__cardTx
    if not card then
        z:Hide()
        bg:Hide()
        tx:SetText("")
        tx:Hide()
        z.__tipLines, z.__act, z.__it = nil, nil, nil
        return
    end
    local x = PD.LV_NAME_X + PD.LV_NAME_W + PD.CARD_GAP + PD.CARD_PAD
    tx:ClearAllPoints()
    tx:SetPoint("LEFT", r, "LEFT", x, PD.TBL_NAME_DY)
    tx:SetTextColor(Unpack(PD.CARD_INK[card.kind] or PD.CARD_INK.trainer))
    tx:SetText(card.text or "")
    tx:Show()
    bg:ClearAllPoints()
    bg:SetPoint("TOPLEFT", tx, "TOPLEFT", -PD.CARD_PAD, 3)
    bg:SetPoint("BOTTOMRIGHT", tx, "BOTTOMRIGHT", PD.CARD_PAD, -3)
    bg:SetColorTexture(Unpack(PD.CARD_COL[card.kind] or PD.CARD_COL.trainer))
    bg:Show()
    z.__tipLines = card.lines
    z.__act = card.act
    z.__it = card.fid and { card.fid } or nil
    z:ClearAllPoints()
    z:SetPoint("TOPLEFT", tx, "TOPLEFT", -PD.CARD_PAD, 3)
    z:SetPoint("BOTTOMRIGHT", tx, "BOTTOMRIGHT", PD.CARD_PAD, -3)
    z:Show()
end

-- 卡片数据：来源只有两条主路径 —— 训练师直教 / 需图纸；图纸再分掉落 / 商人。
function PD.CardOf(rec, ri)
    if not rec then
        return (ri and ri.trainer) and { kind = "trainer", text = L["训练师"] } or nil
    end
    local fid = rec[13] and rec[13][1]
    if not fid then return { kind = "trainer", text = L["训练师"] } end
    local src = rec[14]
    local hasDrop = src and src.drops and #src.drops > 0
    local hasVendor = src and src.vendors and #src.vendors > 0
    local lines = { { format(L["图纸：%s"], DG.ItemName(fid)), 1, 0.82, 0.35 } }
    if hasDrop then lines[#lines + 1] = { format(L["掉落 %d 处"], #src.drops), 0.75, 0.75, 0.75 } end
    local vl = PD.VendorLines(src)
    for i = 1, #vl do lines[#lines + 1] = vl[i] end
    return {
        kind = hasDrop and "drop" or (hasVendor and "vendor" or "drop"),
        text = L["图纸"], fid = fid, lines = lines,
        act = hasVendor and PD.VendorAct(src) or nil,
    }
end

'''
t = rep(t, A2, N2, 'A2 色阶条/卡片函数')

# ── 3. PD.BindRow：来源行让位 ──────────────────────────────────────────
A3 = '''        r.a:SetText(spec.rng or "")
        r.e:SetText(spec.text or "")
        r.b:SetText(spec.src or "")
        r.c:SetText(spec.cnt or "")
'''
N3 = '''        r.a:SetText(spec.rng or "")
        r.e:SetText(spec.text or "")
        -- 2026-10-09 四轮（用户）：这一行原来写来源文字 —— 现在让给四档技能色阶条，
        --   来源压成名字右侧的卡片（PD.PaintCard）。
        r.b:SetText("")
        r.c:SetText(spec.cnt or "")
'''
t = rep(t, A3, N3, 'A3 BindRow 来源行让位')

# ── 4. PD.BindRow：摆色阶条 + 卡片 ─────────────────────────────────────
A4 = '''        r.icon:SetDesaturated(spec.passed and true or false)
        -- 2026-10-09：行级提示框退役 → 制作物自己出一格热区（图标 + 名称列），
'''
N4 = '''        r.icon:SetDesaturated(spec.passed and true or false)
        -- 2026-10-09 四轮（用户）：名字正下方那条（原来源行）改成四档技能色阶条，
        --   名字右侧补一张来源卡片。「已过段落灰显」时整条一并压暗，不抢视线。
        if spec.sbVals then
            PD.PaintSkillBar(r, spec.sbVals, spec.sbTier, spec.passed)
        else
            PD.HideSkillBar(r)
        end
        PD.PaintCard(r, spec.card)
        -- 2026-10-09：行级提示框退役 → 制作物自己出一格热区（图标 + 名称列），
'''
t = rep(t, A4, N4, 'A4 BindRow 摆条+卡片')

# ── 5. PD.RowsLeveling：宽度初值 + 卡片表 ──────────────────────────────
A5 = '''    local cntOf = {}
    local rngW, nameW, cntW, matNeed = 0, 0, 0, 0
'''
N5 = '''    local cntOf = {}
    local cardOf = {}
    local rngW, nameW, cntW, matNeed, cardNeed = 0, 0, 0, 0, 0
'''
t = rep(t, A5, N5, 'A5 宽度初值')

# ── 6. PD.RowsLeveling：循环里量卡片宽 ─────────────────────────────────
A6 = '''        local rec = recOf[st[3]]
        if not rec and rin then rec = rin[st[3]] end
        local _, mw = PD.PackMats((rec and (rec[12] or rec.mats)) or {}, 1e9)
        if mw + PD.TBL_MARK_W > matNeed then matNeed = mw + PD.TBL_MARK_W end
'''
N6 = '''        local rec = recOf[st[3]]
        if not rec and rin then rec = rin[st[3]] end
        local _, mw = PD.PackMats((rec and (rec[12] or rec.mats)) or {}, 1e9)
        if mw + PD.TBL_MARK_W > matNeed then matNeed = mw + PD.TBL_MARK_W end
        -- 2026-10-09 四轮：来源卡片贴在名字列右缘 → 材料区，宽度先在这里量出来，
        --   下面从 avail 里扣掉（卡片全页统一宽 = 本页最长的那张）。
        local cd = PD.CardOf(rec, rin and rin[st[3]] or nil)
        cardOf[st] = cd
        if cd then
            local cwd = PD.TextW(cd.text, 11) + 2 * PD.CARD_PAD + PD.CARD_GAP
            if cwd > cardNeed then cardNeed = cwd end
        end
'''
t = rep(t, A6, N6, 'A6 量卡片宽')

# ── 7. PD.RowsLeveling：avail 扣掉卡片 ────────────────────────────────
A7 = '''    local avail = rowW - PD.TBL_MAT_RPAD - PD.LV_NAME_X - PD.TBL_NAME_GAP
                  - PD.LV_CNT_W - PD.TBL_CNT_GAP
'''
N7 = '''    -- 2026-10-09 四轮：名字列右缘要塞来源卡片 → 材料区预算里扣掉那一格。
    PD.LV_CARD_W = math.ceil(cardNeed)
    local avail = rowW - PD.TBL_MAT_RPAD - PD.LV_NAME_X - PD.TBL_NAME_GAP
                  - PD.LV_CNT_W - PD.TBL_CNT_GAP - PD.LV_CARD_W
'''
t = rep(t, A7, N7, 'A7 avail 扣卡片')

# ── 8. PD.RowsLeveling：spec 带阈值与卡片 ──────────────────────────────
A8 = '''                blocks = blocks, matCut = cut,
                _mats = mats,
            }
'''
N8 = '''                blocks = blocks, matCut = cut,
                _mats = mats,
                -- 2026-10-09 四轮：四档技能阈值（学 / 黄 / 绿 / 灰）+ 当前落点档次 +
                --   来源卡片。阈值取配方行 7..10；rinfo 兜底配方没有阈值 ⇒ 不画条。
                sbVals = (rec and (rec[7] or rec[8] or rec[9] or rec[10]))
                         and { rec[7], rec[8], rec[9], rec[10] } or nil,
                sbTier = rec and PD.LvTier(curLv, rec[7], rec[8], rec[9], rec[10]) or nil,
                card = cardOf[st],
            }
'''
t = rep(t, A8, N8, 'A8 spec 字段')

# ── 9. PD.WipeRow：切页收干净 ──────────────────────────────────────────
A9 = '''    if r.tagFs then r.tagFs:Hide() end
    if r.tagBg then r.tagBg:Hide() end
'''
N9 = '''    if r.tagFs then r.tagFs:Hide() end
    if r.tagBg then r.tagBg:Hide() end
    -- 2026-10-09 四轮：四档色阶条与来源卡片也要一起收（行池跨页复用）。
    if r.__sbBg then PD.HideSkillBar(r) end
    if r.__cardZone then PD.PaintCard(r, nil) end
'''
t = rep(t, A9, N9, 'A9 WipeRow 清理')

out = t.replace('\n', '\r\n')
assert out.count('\r\n') == len(t.split('\n')) - 1, 'CRLF 还原异常'
assert (out.count('\n') - out.count('\r\n')) == 0, '写回后出现裸 LF'
save(P, out)
back = load(P)
assert back == out, '回读不一致'
print('== ProfessionUI.lua 写入 OK：%d -> %d 字节，CRLF %d'
      % (before_bytes, len(out.encode('utf-8')), out.count('\r\n')))

# ══════════════════════════════════════════════════════════════════════
# Locales：补「训练师」「图纸」两个短标签（zhCN 靠键名回退，不用登记）
# ══════════════════════════════════════════════════════════════════════
for path, anchor, add in (
    (ROOT + r'\Locales\zhTW.lua',
     'L["向训练师学习"] = "向訓練師學習"\n',
     'L["训练师"] = "訓練師"\nL["图纸"] = "圖紙"\n'),
    (ROOT + r'\Locales\enUS.lua',
     'L["向训练师学习"] = "Learn from a trainer"\n',
     'L["训练师"] = "Trainer"\nL["图纸"] = "Pattern"\n'),
):
    src = load(path)
    crlf = src.count('\r\n') > 0
    s = src.replace('\r\n', '\n')
    n0 = len(s.encode('utf-8'))
    s = rep(s, anchor, anchor + add, path.split('\\')[-1])
    if crlf:
        s = s.replace('\n', '\r\n')
    save(path, s)
    print('== %s 写入 OK：%d -> %d 字节'
          % (path.split('\\')[-1], n0, len(s.encode('utf-8'))))

print('\n全部补丁落地。')
