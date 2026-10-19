# -*- coding: utf-8 -*-
"""升级路线页：退役「行级鼠标提示框」，改成「制作物 / 需求材料」各自的物品提示框。

口径（用户 2026-10-09）：
  · 每行那个整行提示框（GameTooltip:AddLine 拼的段落说明）不要了；
  · 鼠标移到「制作物」（配方图标 + 配方名）或「需求材料」（材料图标 + 数量角标）上时，
    出**该物品自己的**鼠标提示框；走 DG.ShowItemTip ⇒ 带物品内容 ⇒ 暴雪原皮，不套本插件主题。

做法：
  ① 行级提示框：升级行 spec 打 noTip 标记，PD.Row 的 OnEnter 命中即 return；
  ② 制作物热区：PD.IconZone(r)（惰性建一次，随行池复用）盖住「图标 + 名称列」；
  ③ 材料热区：PD.RowBlk 里给每个材料块加一格热区（只有升级行会建块 ⇒ 帧只服务升级页）；
  ④ 两个热区同一套四件事：悬停高亮 / 物品提示框 / 滚轮转发 / Shift 点击发链接。

幂等：第二次跑时锚点命中数会变成 0 → 直接跳过（打印 SKIP）。

用法：
  python _temp/patch_lv_item_tip.py --check     # 只看锚点命中数，不落盘
  python _temp/patch_lv_item_tip.py             # 正式改
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TARGET = os.path.join(ROOT, 'Core', 'ProfessionUI.lua')

CHECK = '--check' in sys.argv[1:]


def load(path):
    with open(path, 'rb') as f:
        raw = f.read()
    crlf = raw.count(b'\r\n') > 0
    txt = raw.decode('utf-8').replace('\r\n', '\n')
    return txt, crlf, raw


def save(path, txt, crlf):
    out = txt.replace('\n', '\r\n') if crlf else txt
    data = out.encode('utf-8')
    if crlf:
        assert data.count(b'\n') - data.count(b'\r\n') == 0, 'CRLF 文件里出现裸 LF'
    with open(path, 'wb') as f:
        f.write(data)


# ── 补丁表：(标签, old, new) ────────────────────────────────────────────────
PATCHES = []

# ① 行级提示框：升级行不弹（__noTip 由 BindRow 从 spec.noTip 落值）
PATCHES.append((
    'A1 行级提示框开关',
    '    r:SetScript("OnEnter", function(self)\n'
    '        PD.SetRowHover(self, true)\n'
    '        if self.__lines and (self.__linesFirst or not self.__it) then\n',
    '    r:SetScript("OnEnter", function(self)\n'
    '        PD.SetRowHover(self, true)\n'
    '        if self.__noTip then return end\n'
    '        if self.__lines and (self.__linesFirst or not self.__it) then\n',
))

# ② BindRow 落 __noTip
PATCHES.append((
    'A2 BindRow 落 __noTip',
    '    r.__it = spec.it\n'
    '    r.__lines = spec.lines\n'
    '    r.__linesFirst = spec.linesFirst\n',
    '    r.__it = spec.it\n'
    '    r.__noTip = spec.noTip\n'
    '    r.__lines = spec.lines\n'
    '    r.__linesFirst = spec.linesFirst\n',
))

# ③ 制作物热区（升级行）：盖住图标 + 名称列
PATCHES.append((
    'A3 制作物热区摆位',
    '        r.icon:SetSize(PD.TBL_ICON, PD.TBL_ICON)\n'
    '        r.icon:ClearAllPoints()\n'
    '        r.icon:SetPoint("LEFT", r, "LEFT", PD.LV_ICON_X, 0)\n'
    '        r.icon:SetDesaturated(spec.passed and true or false)\n',
    '        r.icon:SetSize(PD.TBL_ICON, PD.TBL_ICON)\n'
    '        r.icon:ClearAllPoints()\n'
    '        r.icon:SetPoint("LEFT", r, "LEFT", PD.LV_ICON_X, 0)\n'
    '        r.icon:SetDesaturated(spec.passed and true or false)\n'
    '        -- 2026-10-09：行级提示框退役 → 制作物自己出一格热区（图标 + 名称列），\n'
    '        -- 悬停出产物物品提示框。宽度取「图标 + 名称列」右缘，不压到次数列与材料块。\n'
    '        local iz = PD.IconZone(r)\n'
    '        iz.__it = itemID and { itemID } or nil\n'
    '        iz:ClearAllPoints()\n'
    '        iz:SetPoint("LEFT", r, "LEFT", PD.LV_ICON_X, 0)\n'
    '        iz:SetSize(PD.LV_NAME_X - PD.LV_ICON_X + PD.LV_NAME_W, h)\n'
    '        iz:SetShown(itemID and true or false)\n',
))

# ④ PD.IconZone：制作物热区构件（紧挨 PD.RowBlk 定义）
PATCHES.append((
    'A4 PD.IconZone 定义',
    'function PD.RowBlk(r, j)\n',
    '-- 制作物热区（升级行专用）：盖住「配方图标 + 配方名」，悬停出产物自己的物品提示框。\n'
    '-- 与材料块热区同款四件事：悬停高亮 / 物品提示框 / 滚轮转发 / Shift 点击发链接。\n'
    '-- ★ 提示框一律走 DG.ShowItemTip（带物品内容 ⇒ 暴雪原皮，不套本插件主题），\n'
    '--   且不自拼 AddLine 文案 —— 用户明确要求「这个提示框不使用我们的主题」。\n'
    'function PD.IconZone(r)\n'
    '    if r.iconZone then return r.iconZone end\n'
    '    local z = CreateFrame("Button", nil, r)\n'
    '    PD.WireTipZone(z, r)\n'
    '    r.iconZone = z\n'
    '    return z\n'
    'end\n'
    '\n'
    '-- 一格物品热区的统一接线（制作物 / 需求材料共用）。\n'
    '-- ★ 滚轮必须显式转发：热区是 EnableMouse 的，压在它上面时滚轮不保证冒泡到滚动容器\n'
    '--   （本相册老坑：满屏都是热区 = 整页滚不动）。\n'
    'function PD.WireTipZone(z, r)\n'
    '    z:EnableMouseWheel(true)\n'
    '    z:SetScript("OnEnter", function(self)\n'
    '        PD.SetRowHover(r, true)\n'
    '        if self.__it and DG.ShowItemTip then DG.ShowItemTip(self, self.__it) end\n'
    '    end)\n'
    '    z:SetScript("OnLeave", function(self)\n'
    '        PD.SetRowHover(r, false)\n'
    '        GameTooltip:Hide()\n'
    '    end)\n'
    '    z:SetScript("OnClick", function(self, button)\n'
    '        DG.ItemShiftClick(self, button)\n'
    '    end)\n'
    '    z:SetScript("OnMouseWheel", function(self, delta)\n'
    '        DG.WheelScroll(PD.scroll, PD.child, delta)\n'
    '    end)\n'
    'end\n'
    '\n'
    'function PD.RowBlk(r, j)\n',
))

# ⑤ 材料块热区
PATCHES.append((
    'A5 材料块热区',
    '    b.nm:SetWordWrap(false)\n'
    '    b.ct:SetWordWrap(false)\n'
    '    r.blk[j] = b\n',
    '    b.nm:SetWordWrap(false)\n'
    '    b.ct:SetWordWrap(false)\n'
    '    -- 2026-10-09：材料块自己出一格热区（图标 + 数量角标那一格），悬停出该材料的\n'
    '    -- 物品提示框。只有升级行会建块（配方页材料是文本列）⇒ 这些帧只服务升级页。\n'
    '    b.zone = CreateFrame("Button", nil, r)\n'
    '    b.zone:Hide()\n'
    '    PD.WireTipZone(b.zone, r)\n'
    '    r.blk[j] = b\n',
))

# ⑥ ClearMats 顺手收热区
PATCHES.append((
    'A6 ClearMats 收热区',
    '        b.ic:Hide()\n'
    '        b.nm:Hide()\n'
    '        b.ct:Hide()\n'
    '    end\n'
    'end\n'
    '\n'
    'function PD.PackMats(list, budget)\n',
    '        b.ic:Hide()\n'
    '        b.nm:Hide()\n'
    '        b.ct:Hide()\n'
    '        if b.zone then b.zone:Hide() end\n'
    '    end\n'
    'end\n'
    '\n'
    'function PD.PackMats(list, budget)\n',
))

# ⑦ PaintMats：材料块摆位时同步热区
PATCHES.append((
    'A7 PaintMats 摆材料热区',
    '        b.ct:SetPoint("RIGHT", r, "RIGHT", -(W - right), PD.TBL_MAT_CNT_DY)\n'
    '        b.ic:Show(); b.ct:Show()\n',
    '        b.ct:SetPoint("RIGHT", r, "RIGHT", -(W - right), PD.TBL_MAT_CNT_DY)\n'
    '        b.zone.__it = { blk.id }\n'
    '        b.zone:ClearAllPoints()\n'
    '        b.zone:SetPoint("RIGHT", r, "RIGHT", -(W - right), 0)\n'
    '        b.zone:SetSize(PD.TBL_ICON, PD.TBL_ICON)\n'
    '        b.ic:Show(); b.ct:Show(); b.zone:Show()\n',
))

# ⑧ PaintMats：省略号那格不带物品 → 热区收起
PATCHES.append((
    'A8 省略号格收热区',
    '        b.nm:SetPoint("RIGHT", r, "RIGHT", -(W - right), PD.TBL_NAME_DY)\n'
    '        b.nm:Show()\n',
    '        b.nm:SetPoint("RIGHT", r, "RIGHT", -(W - right), PD.TBL_NAME_DY)\n'
    '        b.nm:Show()\n'
    '        b.zone:Hide()\n',
))

# ⑨ PaintMats：多余块的热区一起收
PATCHES.append((
    'A9 多余块收热区',
    '    for k = n + (cut and 1 or 0) + 1, #r.blk do\n'
    '        local b = r.blk[k]\n'
    '        b.ic:Hide(); b.nm:Hide(); b.ct:Hide()\n'
    '    end\n',
    '    for k = n + (cut and 1 or 0) + 1, #r.blk do\n'
    '        local b = r.blk[k]\n'
    '        b.ic:Hide(); b.nm:Hide(); b.ct:Hide(); b.zone:Hide()\n'
    '    end\n',
))

# ⑩ RowsLeveling：段落数据不再需要（行级提示框退役）→ 整段摘掉
PATCHES.append((
    'A10 摘掉段落提示框数据',
    '            local tip = { { nm, 1, 0.82, 0 },\n'
    '                          { src or L["来源未收录"], 0.7, 0.7, 0.7 },\n'
    '                          { format(L["材料：%s"],\n'
    '                                   (#mats > 0 and PD.MatText(mats) or L["无"])), 0.7, 0.7, 0.7 } }\n'
    '            if detail then tip[#tip + 1] = { detail, 0.6, 0.9, 0.6 } end\n'
    '            local priced = auto or fixedSum\n'
    '            if priced then\n'
    '                tip[#tip + 1] = { format(L["段落花费：%s"], RA.MoneyStr(st.cost)), 1, 0.82, 0 }\n'
    '                if st.est then\n'
    '                    tip[#tip + 1] = { L["该段材料缺价格数据：花费按已估价材料估算（未知材料按 0 计）"], 0.95, 0.75, 0.4 }\n'
    '                elseif st.unpriced then\n'
    '                    tip[#tip + 1] = { L["含无价材料：花费为估算下限（可在设置放宽「只使用拍卖行可购材料」）"], 0.95, 0.55, 0.45 }\n'
    '                end\n'
    '            end\n'
    '            -- 图纸配方的图纸本身是一次性开销（已计入合计；价格见购物清单「图纸」区）\n'
    '            local f = fOf[st[3]]\n'
    '            if f then\n'
    '                local ps = (priced and not f.unpriced) and RA.MoneyStr(f.cost) or L["价格未知"]\n'
    '                tip[#tip + 1] = { format(L["图纸：%s · %s（一次性，已计入合计）"],\n'
    '                                         DG.ItemName(f.id) or L["未知图纸"], ps), 0.95, 0.75, 0.4 }\n'
    '            end\n'
    '            if st._clip then\n'
    '                tip[#tip + 1] = { format(L["按目标 %d 折算"], target), 0.7, 0.7, 0.7 }\n'
    '            end\n'
    '            local segHi = tonumber(st[2])\n',
    '            local segHi = tonumber(st[2])\n',
))

# ⑪ detail 只剩提示框一个消费方 → 不再取
PATCHES.append((
    'A11 不再取 detail',
    '            local src, detail = PD.LevelSrc(rec)\n',
    '            local src = PD.LevelSrc(rec)\n',
))

# ⑫ 升级行 spec：打 noTip、去掉 lines/linesFirst
PATCHES.append((
    'A12 升级行 spec 打 noTip',
    '                linesFirst = true,\n'
    '                rng = format(L["%s – %s"], tostring(st[1]), tostring(st[2])),\n',
    '                -- 2026-10-09：行级提示框退役（用户：「每行有个鼠标提示框，这个提示框不要了」）\n'
    '                -- → 由制作物 / 需求材料各自的物品提示框承担（PD.IconZone / PD.RowBlk）。\n'
    '                noTip = true,\n'
    '                rng = format(L["%s – %s"], tostring(st[1]), tostring(st[2])),\n',
))

PATCHES.append((
    'A13 升级行 spec 去 lines',
    '                blocks = blocks, matCut = cut,\n'
    '                _mats = mats,\n'
    '                lines = tip,\n'
    '            }\n',
    '                blocks = blocks, matCut = cut,\n'
    '                _mats = mats,\n'
    '            }\n',
))

# ⑭ 图纸索引表只服务提示框 → 摘掉
PATCHES.append((
    'A14 摘掉图纸索引表',
    '    -- 图纸条目索引（tooltip 用）：spell → { id, cost, unpriced }\n'
    '    local fOf = {}\n'
    '    local flist = auto and (res.formulas or {}) or (fixedSum and fixedSum.formulas or {})\n'
    '    for _, f in ipairs(flist) do fOf[f.spell] = f end\n'
    '\n',
    '',
))


def main():
    txt, crlf, raw = load(TARGET)
    print('[eol] CRLF=%s  bytes=%d' % (crlf, len(raw)))

    # 幂等短路：第一个锚点已经不存在 ⇒ 认为整批已落地
    if PATCHES[0][1] not in txt:
        # 但要确认是不是「已打过」而非「锚点抄错」
        if 'if self.__noTip then return end' in txt:
            print('[SKIP] 已打过（__noTip 守卫在）—— 不做任何修改')
            return 0
        print('[FAIL] 首个锚点缺失且没有已打标记 —— 锚点可能抄错，人工核对')
        return 2

    # 先全量校验命中数，全部通过才落盘（避免留下半成品）
    for tag, old, new in PATCHES:
        n = txt.count(old)
        print('[chk] %-26s 命中 %d' % (tag, n))
        if n != 1:
            print('[FAIL] %s 锚点命中 %d 次（要求恰好 1 次）—— 中止，未落盘' % (tag, n))
            return 2

    if CHECK:
        print('[check] 全部锚点各命中 1 次 —— 可以正式跑')
        return 0

    for tag, old, new in PATCHES:
        txt = txt.replace(old, new, 1)

    # 落盘前自检
    assert 'if self.__noTip then return end\n' in txt
    assert 'function PD.IconZone(r)\n' in txt
    assert 'function PD.WireTipZone(z, r)\n' in txt
    assert 'b.zone.__it = { blk.id }\n' in txt
    assert 'noTip = true,\n' in txt
    # ⚠️ 不能查裸 'lines = tip,' —— 购物清单（RowsAutoShop）里也有一处同形（12 空格缩进），
    #    拿裸串判会误红。收窄到「升级行 spec 的收尾」（16 空格缩进）。
    assert '                lines = tip,\n' not in txt
    assert '                _mats = mats,\n            }\n' in txt
    assert 'local fOf = {}\n' not in txt
    assert 'local src, detail = PD.LevelSrc(rec)\n' not in txt

    save(TARGET, txt, crlf)
    print('[done] 已写入 %s' % TARGET)
    return 0


if __name__ == '__main__':
    sys.exit(main())
