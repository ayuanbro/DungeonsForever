# -*- coding: utf-8 -*-
"""2026-10-09 配方页提示框改版（用户）：

    「配方页面现在也这样修改 如果鼠标在材料上面，就显示材料的鼠标提示框
      如果鼠标在商人上面，就显示点击定位在地图上标记商人位置」

落地口径
 ① 材料列：从「一整条材料串」改成**锚点分段链**（第 1 段沿用 r.f，第 2 段起 r.mn[i]），
    每段配一格热区 r.mz[i]（PD.WireTipZone 接线 → 悬停出该材料的物品提示框，暴雪原皮）。
    段间那两格空格跟着**后一段**走 ⇒ 渲染结果与旧的 table.concat(out, "  ") 逐像素一致。
    ★ 为什么不用量宽：ns.hui.TextW 是估算器（图标按 fs+2、空格按步进表），拿它摆热区必然漂；
      锚点链把位置交给引擎算，零量宽、零漂移。
 ② 右下角那格：`PD.SourceText` 拆出 `PD.SourceParts`，把恒居末位的「商人：X」单独成段；
    BindRow 用 r.dv 承载它、r.d 只留前缀（锚点链，不量宽），热区只盖「商人」那一段。
    悬停出 PD.VendorLines（商人明细 + 「点击：在地图上标记该 NPC」），点击落图。
 ③ PD.WireTipZone 扩两个通道：__tipLines（文字提示框）/ __act（自定义点击）。

按 EOL 保真读写（本文件纯 CRLF）；每条锚点断言「恰好命中 1 次」；幂等短路。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEV = os.path.dirname(HERE)
FN = os.path.join(DEV, 'Core', 'ProfessionUI.lua')


def sub_once(txt, old, new, tag):
    n = txt.count(old)
    if n != 1:
        sys.exit('[FAIL] %s：锚点命中 %d 次（应恰好 1）\n--- 锚点 ---\n%s' % (tag, n, old))
    return txt.replace(old, new, 1)


raw = open(FN, 'rb').read()
assert raw.count(b'\r\n') and raw.count(b'\n') == raw.count(b'\r\n'), '不是纯 CRLF 文件'
txt = raw.decode('utf-8')

if 'PD.PaintMatSegs' in txt:
    print('[SKIP] ProfessionUI.lua：已是改版后形态')
    sys.exit(0)

# 统一按 \n 处理，最后统一换回 \r\n
txt = txt.replace('\r\n', '\n')

# ══════════════════════════════════════════════════════════════════════════
# ① PD.MatCol 回传分段
# ══════════════════════════════════════════════════════════════════════════
OLD = """function PD.MatCol(list, fs, budget)
    if not list or #list == 0 then return "", 0, 0 end
    local gap, px = 10, PD.MAT_ICON_PX
    local out, w, n = {}, 0, 0
    for i = 1, #list do
        local m = list[i]
        local cnt = format("%d×", m[2] or 1)
        local name = DG.ItemName(m[1])
        local cw = PD.TextW(cnt, fs) + px + PD.TextW(name, fs)
        if n > 0 and w + gap + cw > budget then
            out[#out + 1] = "…"
            break
        end
        if n == 0 and cw > budget then
            name = PD.Fit(name, fs, budget - PD.TextW(cnt, fs) - px)
            cw = PD.TextW(cnt, fs) + px + PD.TextW(name, fs)
        end
        out[#out + 1] = cnt .. PD.MatIconTex(m[1], px) .. name
        w = w + (n > 0 and gap or 0) + cw
        n = n + 1
    end
    return table.concat(out, "  "), w, n
end
"""
NEW = """-- 第 4 个返回值 segs = 分段表 {{ id = 物品ID|nil, text = 该段的完整串 }, ...}。
--   2026-10-09：配方页把材料列渲染成**锚点分段链**（每段一个字串 + 一格热区），
--   段间那两格空格跟着**后一段**走 ⇒ 与旧的 table.concat(out, "  ") 逐像素一致。
--   省略号那一段没有物品 id（不给热区）。
function PD.MatCol(list, fs, budget)
    if not list or #list == 0 then return "", 0, 0, nil end
    local gap, px = 10, PD.MAT_ICON_PX
    local out, w, n, segs = {}, 0, 0, {}
    for i = 1, #list do
        local m = list[i]
        local cnt = format("%d×", m[2] or 1)
        local name = DG.ItemName(m[1])
        local cw = PD.TextW(cnt, fs) + px + PD.TextW(name, fs)
        if n > 0 and w + gap + cw > budget then
            out[#out + 1] = "…"
            segs[#segs + 1] = { text = "  …" }
            break
        end
        if n == 0 and cw > budget then
            name = PD.Fit(name, fs, budget - PD.TextW(cnt, fs) - px)
            cw = PD.TextW(cnt, fs) + px + PD.TextW(name, fs)
        end
        local piece = cnt .. PD.MatIconTex(m[1], px) .. name
        out[#out + 1] = piece
        segs[#segs + 1] = { id = m[1], text = (n > 0 and "  " or "") .. piece }
        w = w + (n > 0 and gap or 0) + cw
        n = n + 1
    end
    return table.concat(out, "  "), w, n, segs
end
"""
txt = sub_once(txt, OLD, NEW, 'PD.MatCol')

# ══════════════════════════════════════════════════════════════════════════
# ② PD.SourceParts + PD.SourceText 改壳
# ══════════════════════════════════════════════════════════════════════════
OLD = """function PD.SourceText(s)
    if not s then return nil end
    local t = {}
    if s.skill then t[#t + 1] = format(L["技能 %s"], tostring(s.skill)) end
    if s.drops and #s.drops > 0 then t[#t + 1] = format(L["掉落 %d 处"], #s.drops) end
    if s.vendors and #s.vendors > 0 then
        local v = s.vendors[1]
        t[#t + 1] = format(L["商人：%s"], (v and v.name) or "?")
    end
    if #t == 0 then return nil end
    return table.concat(t, " · ")
end
"""
NEW = """-- 来源拆段：与 SourceText 同序、同「 · 」分隔，但把「商人：X」单独标出来（vendor = true）。
--   2026-10-09 配方页要给「商人」那一段单开热区（用户：「如果鼠标在商人上面，就显示
--   点击定位在地图上标记商人位置」）—— 量宽会漂，所以靠**锚点链**把商人那半拆到 r.dv，
--   热区直接盖 r.dv，位置由引擎算。
--   ★ 顺序铁律：skill → drops → vendors，商人**恒为最后一段**，拆段链就吃这一点。
function PD.SourceParts(s)
    local out = {}
    if not s then return out end
    if s.skill then out[#out + 1] = { text = format(L["技能 %s"], tostring(s.skill)) } end
    if s.drops and #s.drops > 0 then
        out[#out + 1] = { text = format(L["掉落 %d 处"], #s.drops) }
    end
    if s.vendors and #s.vendors > 0 then
        local v = s.vendors[1]
        out[#out + 1] = { text = format(L["商人：%s"], (v and v.name) or "?"), vendor = true }
    end
    return out
end

function PD.SourceText(s)
    local p = PD.SourceParts(s)
    if #p == 0 then return nil end
    local t = {}
    for i = 1, #p do t[i] = p[i].text end
    return table.concat(t, " · ")
end
"""
txt = sub_once(txt, OLD, NEW, 'PD.SourceText')

# ══════════════════════════════════════════════════════════════════════════
# ③ PD.Row：加 r.mn / r.mz / r.dv
# ══════════════════════════════════════════════════════════════════════════
OLD = """    r.f = MakeFS(r, PD.MAT_FS, C_TEXT, "LEFT")
"""
NEW = """    r.f = MakeFS(r, PD.MAT_FS, C_TEXT, "LEFT")
    -- 2026-10-09 配方页两处热区（用户）：
    --   ① 材料列改「锚点分段链」—— 第 1 段沿用 r.f（保住「材料列左锚 = PD.MAT_X」那条
    --      既有不变量），第 2 段起是 r.mn[i]；每段配一格热区 r.mz[i]，悬停出该材料的物品提示框；
    --   ② 右下角那格的「商人：X」半段搬到 r.dv（r.d 只留前缀），热区只盖 r.dv ——
    --      悬停出商人明细 + 「点击：在地图上标记该 NPC」，点击落图。
    r.mn = {}
    r.mz = {}
    r.dv = MakeFS(r, 11, C_GREY, "RIGHT")
    r.dv:SetText("")
    r.dv:SetWordWrap(false)
    r.dv:Hide()
"""
txt = sub_once(txt, OLD, NEW, 'PD.Row :: r.mn/mz/dv')

# ══════════════════════════════════════════════════════════════════════════
# ④ PD.WireTipZone：加 __tipLines / __act 两个通道
# ══════════════════════════════════════════════════════════════════════════
OLD = """    z:SetScript("OnEnter", function(self)
        PD.SetRowHover(r, true)
        if self.__it and DG.ShowItemTip then DG.ShowItemTip(self, self.__it) end
    end)
    z:SetScript("OnLeave", function(self)
        PD.SetRowHover(r, false)
        GameTooltip:Hide()
    end)
    z:SetScript("OnClick", function(self, button)
        DG.ItemShiftClick(self, button)
    end)
"""
NEW = """    z:SetScript("OnEnter", function(self)
        PD.SetRowHover(r, true)
        local lines = self.__tipLines
        if lines then
            -- 文字提示框通道（商人热区）：与行级提示框同一套写法（同样吃本插件主题）
            GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
            GameTooltip:ClearLines()
            for _, ln in ipairs(lines) do
                if ln[1] and ln[1] ~= "" then
                    GameTooltip:AddLine(ln[1], ln[2] or 1, ln[3] or 1, ln[4] or 1, true)
                end
            end
            GameTooltip:Show()
        elseif self.__it and DG.ShowItemTip then
            -- 物品通道：DG.ShowItemTip 走 SetItemByID ⇒ 带物品内容 ⇒ 暴雪原皮（不套本插件主题）
            DG.ShowItemTip(self, self.__it)
        end
    end)
    z:SetScript("OnLeave", function(self)
        PD.SetRowHover(r, false)
        GameTooltip:Hide()
    end)
    z:SetScript("OnClick", function(self, button)
        -- 自定义点击优先（商人热区 → 落图）；否则走物品的 Shift 点击发链接
        if self.__act then
            self.__act(self, button)
            return
        end
        DG.ItemShiftClick(self, button)
    end)
"""
txt = sub_once(txt, OLD, NEW, 'PD.WireTipZone')

# ══════════════════════════════════════════════════════════════════════════
# ⑤ 新增 PD.MatSeg / PD.MatZone / PD.ClearMatSegs / PD.PaintMatSegs
#    （紧挨 PD.RowBlk 之前插）
# ══════════════════════════════════════════════════════════════════════════
ANCHOR = "function PD.RowBlk(r, j)\n"
NEW_FUNCS = """-- ── 配方页「锚点分段链」：材料列各段 + 右下角商人半段 ──────────────────────────
-- 为什么是锚点链而不是量宽：hotspot 必须与文字**逐像素**对齐，而 ns.hui.TextW 是估算器
--   （图标按 fs + 2 算、空格走步进表），拿它摆热区必然漂；锚点链把位置交给引擎算。
function PD.MatSeg(r, i)
    if i == 1 then return r.f end
    local fs = r.mn[i]
    if not fs then
        fs = MakeFS(r, PD.MAT_FS, C_TEXT, "LEFT")
        fs:SetWordWrap(false)
        r.mn[i] = fs
    end
    return fs
end

function PD.MatZone(r, i)
    local z = r.mz[i]
    if not z then
        z = CreateFrame("Button", nil, r)
        PD.WireTipZone(z, r)
        r.mz[i] = z
    end
    return z
end

-- 收干净：行池跨专业/跨子页签复用 —— 不清就会留一串透明热区在旧位置吞鼠标（本相册老坑）。
function PD.ClearMatSegs(r)
    if r.f then r.f:SetText("") end
    if r.mn then
        for j = 2, #r.mn do
            r.mn[j]:SetText("")
            r.mn[j]:Hide()
        end
    end
    if r.mz then
        for j = 1, #r.mz do r.mz[j]:Hide() end
    end
    if r.dv then r.dv:Hide() end
end

-- 摆材料分段链：每段一个字串（第 1 段 = r.f，左锚 PD.MAT_X），每段一格热区压在字串上。
--   热区靠「锚到字串的 TOPLEFT / BOTTOMRIGHT」取尺寸 ⇒ 零量宽。没有物品 id 的段
--   （末尾省略号）不给热区。
function PD.PaintMatSegs(r, segs, color)
    local col = color or C_TEXT
    local prev
    for i = 1, #segs do
        local fs = PD.MatSeg(r, i)
        fs:SetTextColor(Unpack(col))
        fs:SetText(segs[i].text or "")
        fs:ClearAllPoints()
        if i == 1 then
            fs:SetPoint("LEFT", r, "LEFT", PD.MAT_X, 0)
        else
            fs:SetPoint("LEFT", prev, "RIGHT", 0, 0)
        end
        fs:Show()
        prev = fs
        local z = PD.MatZone(r, i)
        if segs[i].id then
            z.__it = { segs[i].id }
            z.__tipLines = nil
            z.__act = nil
            z:ClearAllPoints()
            z:SetPoint("TOPLEFT", fs, "TOPLEFT", 0, 1)
            z:SetPoint("BOTTOMRIGHT", fs, "BOTTOMRIGHT", 0, -1)
            z:Show()
        else
            z:Hide()
        end
    end
end

"""
txt = sub_once(txt, ANCHOR, NEW_FUNCS + ANCHOR, 'PD.RowBlk :: 前置新函数')

# ══════════════════════════════════════════════════════════════════════════
# ⑥ PD.BindRow：清分段链 + 摆材料链 + 商人半段
# ══════════════════════════════════════════════════════════════════════════
txt = sub_once(txt,
               "    PD.ClearMats(r)\n",
               "    PD.ClearMats(r)\n    PD.ClearMatSegs(r)\n",
               'PD.BindRow :: 清分段链')

OLD = """    r.f:SetTextColor(Unpack(spec.matColor or C_TEXT))
    r.f:SetText(spec.mats or "")
"""
NEW = """    r.f:SetTextColor(Unpack(spec.matColor or C_TEXT))
    -- 有分段数据（配方页）就让分段链自己写各段；没有（附魔/可制造/商人兑换）照旧走整串
    if not spec.matSegs then r.f:SetText(spec.mats or "") end
"""
txt = sub_once(txt, OLD, NEW, 'PD.BindRow :: matSegs 分支')

OLD = """        r.f:SetPoint("LEFT", r, "LEFT", PD.MAT_X, 0)
    end
"""
NEW = """        r.f:SetPoint("LEFT", r, "LEFT", PD.MAT_X, 0)
        -- 2026-10-09：配方页材料列摆分段链（第 1 段的 SetPoint 由 PaintMatSegs 重写，
        --   与上面这行同值，不冲突）
        if spec.matSegs then PD.PaintMatSegs(r, spec.matSegs, spec.matColor) end
    end
    -- 右下角那格拆两半：前缀留在 r.d，恒居末位的「商人：X」搬到 r.dv ——
    --   热区只盖「商人」半段（用户：「鼠标在商人上面」）；两半用锚点链相接，不量宽。
    if spec.dval and h > PD.ROW_H1 then
        r.d:SetText(spec.dpre or "")
        r.dv:SetText(spec.dval)
        r.dv:SetTextColor(Unpack(C_GREY))
        r.dv:ClearAllPoints()
        r.dv:SetPoint("BOTTOMRIGHT", r, "BOTTOMRIGHT", -6, 4)
        r.dv:Show()
        r.d:ClearAllPoints()
        r.d:SetPoint("RIGHT", r.dv, "LEFT", 0, 0)
        local vz = PD.IconZone(r)
        vz.__it = nil
        vz.__tipLines = PD.VendorLines(spec.src)
        vz.__act = PD.VendorAct(spec.src)
        vz:ClearAllPoints()
        vz:SetPoint("TOPLEFT", r.dv, "TOPLEFT", 0, 1)
        vz:SetPoint("BOTTOMRIGHT", r.dv, "BOTTOMRIGHT", 0, -1)
        vz:Show()
    end
"""
txt = sub_once(txt, OLD, NEW, 'PD.BindRow :: 材料链 + 商人半段')

# 升级行分支复用 r.__iconZone 时必须清掉商人通道（行池跨页复用）
txt = sub_once(txt,
               "        iz.__it = itemID and { itemID } or nil\n",
               "        iz.__it = itemID and { itemID } or nil\n"
               "        iz.__tipLines = nil\n"
               "        iz.__act = nil\n",
               'PD.BindRow :: 升级行清商人通道')

# ══════════════════════════════════════════════════════════════════════════
# ⑦ PD.RecipeSpec：回传 matSegs / src / dpre / dval
# ══════════════════════════════════════════════════════════════════════════
OLD = """    local hasVendor = r[14] and r[14].vendors and #r[14].vendors > 0
    if hasVendor then
        for _, ln in ipairs(PD.VendorLines(r[14])) do lines[#lines + 1] = ln end
    end
"""
NEW = """    local hasVendor = r[14] and r[14].vendors and #r[14].vendors > 0
    if hasVendor then
        for _, ln in ipairs(PD.VendorLines(r[14])) do lines[#lines + 1] = ln end
    end
    -- 右下角那格拆两半（见 PD.SourceParts）：商人**恒为最后一段**，单独搬到 r.dv 好挂热区。
    --   dval 带上「· 」分隔符，拆开渲染后与旧的一整串逐像素一致。
    local dpre, dval, vk
    local parts = PD.SourceParts(r[14])
    for i = 1, #parts do
        if parts[i].vendor then vk = i end
    end
    if vk then
        dval = (vk > 1 and "· " or "") .. parts[vk].text
        local t = {}
        for i = 1, vk - 1 do t[i] = parts[i].text end
        if #t > 0 then dpre = table.concat(t, " · ") end
    end
    local mcol, _, _, msegs = PD.MatCol(r[12], PD.MAT_FS, PD.MAT_W)
"""
txt = sub_once(txt, OLD, NEW, 'PD.RecipeSpec :: 拆段')

OLD = """        mats = PD.MatCol(r[12], PD.MAT_FS, PD.MAT_W),
"""
NEW = """        mats = mcol,
        matSegs = msegs,
        src = r[14],
        dpre = dpre,
        dval = dval,
"""
txt = sub_once(txt, OLD, NEW, 'PD.RecipeSpec :: spec 字段')

# ══════════════════════════════════════════════════════════════════════════
# ⑧ PD.FitRecipeCols：按最终列宽重算分段
# ══════════════════════════════════════════════════════════════════════════
OLD = """        if s._mats then s.mats = PD.MatCol(s._mats, PD.MAT_FS, PD.MAT_W) end
"""
NEW = """        if s._mats then
            local sg
            s.mats, sg = PD.MatCol(s._mats, PD.MAT_FS, PD.MAT_W)
            s.matSegs = sg
        end
"""
txt = sub_once(txt, OLD, NEW, 'PD.FitRecipeCols')

# ── 落盘前自检 ────────────────────────────────────────────────────────────
for must in ('function PD.PaintMatSegs', 'function PD.ClearMatSegs', 'function PD.MatSeg',
             'function PD.MatZone', 'function PD.SourceParts', 'matSegs = msegs',
             "local mcol, _, _, msegs = PD.MatCol(r[12], PD.MAT_FS, PD.MAT_W)\n",
             'PD.ClearMatSegs(r)\n', 'if self.__act then\n'):
    assert must in txt, '自检失败：缺 %s' % must
assert 'return table.concat(out, "  "), w, n, segs\n' in txt
assert txt.count('function PD.PaintMatSegs') == 1
assert '\r' not in txt, '混入裸 CR'

out = txt.replace('\n', '\r\n').encode('utf-8')
open(FN, 'wb').write(out)
print('[OK] ProfessionUI.lua：%d → %d 字节' % (len(raw), len(out)))
print('     CRLF=%d / 裸 LF=%d / 裸 CR=%d'
      % (out.count(b'\r\n'), out.count(b'\n') - out.count(b'\r\n'),
         out.count(b'\r') - out.count(b'\r\n')))
