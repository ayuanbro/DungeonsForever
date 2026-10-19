# -*- coding: utf-8 -*-
"""MapUI 加四类新钉点（入口/任务/物品/稀有）：渲染分派 + 点击/悬停 + 开关改名。"""
import sys

P = 'Core/MapUI.lua'
src = open(P, encoding='utf-8').read()


def rep(old, new, tag):
    n = src.count(old)
    assert n == 1, '%s: 锚点命中 %d 次' % (tag, n)
    return src.replace(old, new)


# ── R1 常量区：MAX_PINS 16 → 24 + 新钉点贴图常量 ─────────────────────────────
src = rep(
    'M.MAX_PINS = 16                  -- 钉点池（实测最多 11：暴风城监狱）',
    'M.MAX_PINS = 24                  -- 钉点池（实测最多 14：影牙 12 boss + 2 任务物品）\n'
    '-- 四类钉点的贴图：boss / 稀有共用骷髅（金 / 银染色）；任务 = 黄色「!」；\n'
    '-- 入口 = 自制石门（客户端 POIIcons 图集的格子坐标未实测，等数据 pin 刷新后\n'
    '--      可换 Interface\\Minimap\\POIIcons 子矩形，只改本常量）；物品 = 客户端图标。\n'
    'M.PIN_BOSS_TEX = "Interface\\\\AddOns\\\\DungeonsForever\\\\Media\\\\BossSkull"\n'
    'M.PIN_QUEST_TEX = "Interface\\\\GossipFrame\\\\AvailableQuestIcon"\n'
    'M.PIN_DOOR_TEX = "Interface\\\\AddOns\\\\DungeonsForever\\\\Media\\\\MapDoor"',
    'R1-MAXPINS')

# ── R2 ExtraPinsFor 插在 HasPins 之前 ────────────────────────────────────────
src = rep(
    '-- 本副本**有没有钉点可画**（任意层）——「隐藏 boss」开关的显隐判据。',
    '''-- 「入口 / 任务 / 物品 / 稀有」钉点（ns.MapPins，_temp/fc_pins.py 产物）：
-- 返回扁平列表 { { kind=, left=, top=, id=, name= }, … }（boss 钉之外的其余类型）。
-- floor = 客户端层号：数据未写层号的一律按第 1 层（与 ns.BossPos 同口径）；
-- nil = 不分层（HasPins 判据用）。
function M.ExtraPinsFor(id, floor)
    local row = id and ns.MapPins and ns.MapPins[id]
    if type(row) ~= "table" then return nil end
    local out
    for _, kind in ipairs({ "entrance", "quest", "object", "rare" }) do
        local arr = row[kind]
        if type(arr) == "table" then
            for i = 1, #arr do
                local p = arr[i]
                if type(p) == "table" and p[1] and p[2] then
                    if floor == nil or floor == 1 then
                        out = out or {}
                        out[#out + 1] = {
                            kind = kind, left = p[1], top = p[2], id = p[3],
                            name = (kind == "rare") and p[4] or nil,
                        }
                    end
                end
            end
        end
    end
    return out
end

-- 本副本**有没有钉点可画**（任意层）——「隐藏图钉」开关的显隐判据。''',
    'R2-EXTRAPINS')

# ── R3 HasPins 计入新钉点 ────────────────────────────────────────────────────
src = rep(
    '''    local list = M.PinsFor(id, nil)
    return (list and #list > 0) and true or false
end''',
    '''    local list = M.PinsFor(id, nil)
    local n = list and #list or 0
    local ex = M.ExtraPinsFor(id, nil)
    if ex then n = n + #ex end
    return (n > 0) and true or false
end''',
    'R3-HASPINS')

# ── R4 SyncPins 列表合并 ─────────────────────────────────────────────────────
src = rep(
    '''    local list, n = nil, 0
    if M.curId and M.LayersFor(M.curId) then
        list = M.PinsFor(M.curId, M.FloorNumAt(M.curId, M.curLayer or 1))
    elseif M.curId and M.CustomFor(M.curId) then
        list = M.PinsFor(M.curId, 1)
    end''',
    '''    local list, n = nil, 0
    local floor
    if M.curId and M.LayersFor(M.curId) then
        floor = M.FloorNumAt(M.curId, M.curLayer or 1)
    elseif M.curId and M.CustomFor(M.curId) then
        floor = 1
    end
    if M.curId and floor then
        list = M.PinsFor(M.curId, floor)
        local ex = M.ExtraPinsFor(M.curId, floor)
        if ex then
            for i = 1, #ex do
                list = list or {}
                list[#list + 1] = ex[i]
            end
        end
    end''',
    'R4-LIST')

# ── R5 渲染循环按 kind 分派 ──────────────────────────────────────────────────
src = rep(
    '''    if list and #list > 0 then
        local cw, ch = frame.pinW, frame.pinH
        for i = 1, #list do
            if i > M.MAX_PINS then break end
            n = n + 1
            local p = list[i]
            local bt = frame.pinBtns[n]
            bt.__en = p.en
            bt.__zh = p.zh
            bt:ClearAllPoints()
            bt:SetPoint("CENTER", frame.pins, "TOPLEFT",
                        (p.left / 100) * cw, -(p.top / 100) * ch)
            bt.nm:SetText(p.zh or p.en or "")
            -- 名字常驻显示在钉点正下方；选中 16 / 未选 14
            local sel = (M.detailEn == p.en)
            local fpath, _, fflags = bt.nm:GetFont()
            bt.nm:SetFont(fpath, sel and 16 or 14, fflags)
            -- 颜色即身份：钉点与名字都用 boss 专属色（选中只放大、不变色）
            local cr, cg, cb = M.BossColor(M.curId, p.en)
            bt.dot:SetVertexColor(cr, cg, cb)
            bt.nm:SetTextColor(cr, cg, cb)
            bt.dot:ClearAllPoints()
            bt.dot:SetPoint("CENTER", bt, "CENTER", 0, 0)
            bt.dot:SetSize(sel and M.PIN_SIZE or M.PIN_MIN, sel and M.PIN_SIZE or M.PIN_MIN)
            bt:Show()
        end
    end''',
    '''    if list and #list > 0 then
        local cw, ch = frame.pinW, frame.pinH
        for i = 1, #list do
            if i > M.MAX_PINS then break end
            n = n + 1
            local p = list[i]
            local bt = frame.pinBtns[n]
            local kind = p.kind or "boss"
            bt.__kind, bt.__p = kind, p
            bt.__en, bt.__zh = p.en, p.zh
            bt:ClearAllPoints()
            bt:SetPoint("CENTER", frame.pins, "TOPLEFT",
                        (p.left / 100) * cw, -(p.top / 100) * ch)
            -- 贴图按类型走：boss / 稀有 = 骷髅（金 / 银染色）；任务 = 黄「!」；
            -- 入口 = 自制石门；物品 = 客户端物品图标（铁律：外观运行期问客户端）。
            if kind == "quest" then
                bt.dot:SetTexture(M.PIN_QUEST_TEX)
                bt.dot:SetVertexColor(1, 1, 1)
            elseif kind == "entrance" then
                bt.dot:SetTexture(M.PIN_DOOR_TEX)
                bt.dot:SetVertexColor(1, 1, 1)
            elseif kind == "object" then
                bt.dot:SetTexture(DG.ItemIcon(p.id))
                bt.dot:SetVertexColor(1, 1, 1)
            else
                bt.dot:SetTexture(M.PIN_BOSS_TEX)
                if kind == "rare" then
                    bt.dot:SetVertexColor(0.72, 0.76, 0.85)
                else
                    bt.dot:SetVertexColor(1, 0.82, 0)
                end
            end
            -- 名字 / 颜色：boss 专属色即身份；其余类型按类别固定色
            local nm, cr, cg, cb
            if kind == "boss" then
                nm = p.zh or p.en or ""
                cr, cg, cb = M.BossColor(M.curId, p.en)
            elseif kind == "quest" then
                nm = DG.QuestName(p.id)
                cr, cg, cb = Unpack(C_GOLD)
            elseif kind == "object" then
                nm = DG.ItemName(p.id)
                cr, cg, cb = Unpack(C_TEXT)
            elseif kind == "entrance" then
                nm = L["副本入口"]
                cr, cg, cb = Unpack(C_GOLD)
            else
                nm = p.name or ""
                cr, cg, cb = 0.72, 0.76, 0.85
            end
            bt.nm:SetText(nm or "")
            -- 名字常驻显示在钉点正下方；选中（仅 boss）16 / 未选 14
            local sel = (kind == "boss") and (M.detailEn == p.en) or false
            local fpath, _, fflags = bt.nm:GetFont()
            bt.nm:SetFont(fpath, sel and 16 or 14, fflags)
            bt.nm:SetTextColor(cr, cg, cb)
            bt.dot:ClearAllPoints()
            bt.dot:SetPoint("CENTER", bt, "CENTER", 0, 0)
            bt.dot:SetSize(sel and M.PIN_SIZE or M.PIN_MIN, sel and M.PIN_SIZE or M.PIN_MIN)
            bt:SetScript("OnClick", M.PinOnClick)
            bt:SetScript("OnEnter", M.PinOnEnter)
            bt:SetScript("OnLeave", M.PinOnLeave)
            bt:Show()
        end
    end''',
    'R5-LOOP')

# ── R6 开关文案：隐藏boss/显示boss → 隐藏图钉/显示图钉 ────────────────────────
src = rep(
    'bt:SetText(off and L["显示boss"] or L["隐藏boss"])',
    'bt:SetText(off and L["显示图钉"] or L["隐藏图钉"])',
    'R6-LABEL')

# ── R7 点击/悬停分派函数 + 段头注释改名 ──────────────────────────────────────
src = rep(
    '-- ── 左上角「隐藏 boss」开关 ────────────────────────────────────────────────',
    '''-- ── 钉点点击 / 悬停（按 __kind 分派）─────────────────────────────────────────
-- boss = 右栏选中；任务 = 切到详情任务区并选中该任务（SetDungeonTab 内部先
-- EnsureQuestLane 再渲染，「先补建再切显隐」顺序由它负责）；物品 = 物品提示框
-- （走 DG.ShowItemTip，自带重入守卫）；入口 / 稀有 = 一行说明。
function M.PinOnClick(self)
    local kind, p = self.__kind, self.__p
    if kind == "boss" and p and p.en then
        M.Select(p.en)
    elseif kind == "quest" and p and p.id then
        U.dungeonQuestSel = p.id
        U:SetDungeonTab("quest")
    end
end

function M.PinOnEnter(self)
    local p = self.__p
    if not p or self.__kind == "boss" then return end
    if self.__kind == "object" then
        DG.ShowItemTip(self, { p.id })
        return
    end
    GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
    GameTooltip:ClearLines()
    if self.__kind == "quest" then
        GameTooltip:AddLine(DG.QuestName(p.id) or L["任务"], 1, 0.82, 0, true)
        GameTooltip:AddLine(L["点击查看任务详情"], 0.7, 0.7, 0.7, true)
    elseif self.__kind == "entrance" then
        GameTooltip:AddLine(L["副本入口"], 1, 0.82, 0, true)
    elseif self.__kind == "rare" then
        GameTooltip:AddLine(L["稀有"] .. "：" .. (p.name or ""), 0.72, 0.76, 0.85, true)
    end
    GameTooltip:Show()
end

function M.PinOnLeave()
    GameTooltip:Hide()
end

-- ── 左上角「隐藏图钉」开关 ────────────────────────────────────────────────''',
    'R7-DISPATCH')

open(P, 'w', encoding='utf-8', newline='\n').write(src)
print('MapUI 补丁落盘 OK')
