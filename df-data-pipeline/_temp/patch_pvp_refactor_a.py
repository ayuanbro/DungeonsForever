# -*- coding: utf-8 -*-
"""方案 A 四页签重构：军衔 / 本周(周上限+冲刺+战场轮换) / 声望(二级阵营) / 套装。
全部锚点断言 count==1，幂等可重跑。"""
import io, os, sys

SRC = r'D:/workspace/DungeonsForever/Core/PvPUI.lua'
ZH = r'D:/workspace/DungeonsForever/Locales/zhTW.lua'
EN = r'D:/workspace/DungeonsForever/Locales/enUS.lua'
HK = r'D:/workspace/DungeonsForever/_temp/df_dungeon_check.py'

def patch(path, pairs, label):
    s = io.open(path, encoding='utf-8', newline='').read()
    changed = 0
    for old, new in pairs:
        n = s.count(old)
        assert n == 1, '%s: 锚点命中 %d 次（应为 1）：%r' % (label, n, old[:90])
        if new != old:
            s = s.replace(old, new)
            changed += 1
    io.open(path, 'w', encoding='utf-8', newline='').write(s)
    print('%s: %d 处替换落盘' % (label, changed))

# ────────────────────────── PvPUI.lua ──────────────────────────
pv = []

# P1 头注释
pv.append((
"""-- ★ 六个二级子页签：军衔 / 周上限 / 套装 / 战场 / 暗矛群岛 / 冲刺。页签在标题下方，
--   与团本页的时间线 / 列表 / 套装同层同规格（76×24、14 号字、金描边选中态）。""",
"""-- ★ 四个二级子页签（方案 A 重构）：军衔 / 本周 / 声望 / 套装。页签在标题下方，
--   与团本页的时间线 / 列表 / 套装同层同规格（76×24、14 号字、金描边选中态）。
--   「本周」= 周上限 + 冲刺 + 战场轮换合并页；「声望」= 二级阵营注册表
--   （REP_DEFS：暗矛群岛 / 荣誉之地，后续阵营即插即用）。"""))

# P2 TAB_DEFS + REP_DEFS
pv.append((
"""local TAB_DEFS = {
    { key = "ranks",  text = L["军衔"] },
    { key = "caps",   text = L["周上限"] },
    { key = "sets",   text = L["套装"] },
    { key = "fields", text = L["战场"] },
    { key = "spear",  text = L["暗矛群岛"] },
    { key = "sprint", text = L["冲刺"] },
}""",
"""local TAB_DEFS = {
    { key = "ranks", text = L["军衔"] },
    { key = "week",  text = L["本周"] },
    { key = "rep",   text = L["声望"] },
    { key = "sets",  text = L["套装"] },
}

-- ★ 声望页二级阵营注册表：新阵营只需插一条 + 在 RenderRep 加一个渲染分支，
--   页签自动多一枚切换钮（数据层零改动）。
local REP_DEFS = {
    { key = "spear", text = L["暗矛群岛"] },
    { key = "honor", text = L["荣誉之地"] },
}"""))

# P3 池初始化：bfRows → weekBf；加 repBtns / selRep
pv.append((
"""    PV.setRows = {}
    PV.bfRows = {}
    PV.taskRows = {}""",
"""    PV.setRows = {}
    PV.weekBf = {}
    PV.taskRows = {}"""))
pv.append((
"""    PV.markChips = {}
    PV.spRows = {}""",
"""    PV.markChips = {}
    PV.repBtns = {}
    PV.spRows = {}"""))
pv.append((
"""    PV.selSet = 1
    PV.goal = 14""",
"""    PV.selSet = 1
    PV.selRep = "spear"
    PV.goal = 14"""))

# P4 capRows 紧凑双列几何
pv.append((
"""    for i = 1, 10 do
        local r = CreateFrame("Frame", nil, child)
        r:SetSize(PV.W, 34)
        r.week = MakeFS(r, 14, C_TEXT, "LEFT")
        r.week:SetPoint("TOPLEFT", r, "TOPLEFT", 6, -8)
        r.rank = MakeFS(r, 14, C_GOLD, "LEFT")
        r.rank:SetPoint("TOPLEFT", r, "TOPLEFT", 96, -8)
        r.barBG = r:CreateTexture(nil, "BACKGROUND")
        r.barBG:SetPoint("TOPLEFT", r, "TOPLEFT", 160, -11)
        r.barBG:SetSize(300, 12)
        r.barBG:SetColorTexture(1, 1, 1, 0.08)
        r.bar = r:CreateTexture(nil, "ARTWORK")
        r.bar:SetPoint("TOPLEFT", r.barBG, "TOPLEFT", 0, 0)
        r.bar:SetHeight(12)
        r.bar:SetColorTexture(0.27, 0.75, 0.45, 0.85)
        r.cum = MakeFS(r, 14, C_TEXT, "RIGHT")
        r.cum:SetPoint("TOPRIGHT", r, "TOPLEFT", 620, -8)
        r.inc = MakeFS(r, 14, C_GREY, "RIGHT")
        r.inc:SetPoint("TOPRIGHT", r, "TOPLEFT", 720, -8)
        r.sep = r:CreateTexture(nil, "BACKGROUND")
        r.sep:SetPoint("BOTTOMLEFT", r, "BOTTOMLEFT", 4, 0)
        r.sep:SetPoint("BOTTOMRIGHT", r, "BOTTOMRIGHT", -4, 0)
        r.sep:SetHeight(1)
        r.sep:SetColorTexture(1, 1, 1, 0.06)
        PV.capRows[i] = r
    end""",
"""    -- ★★ 周上限行：并入本周页后改双列网格，行内列随之紧凑（行高 30、条宽 120）。
    local capColW = floor(PV.W / 2) - 16
    for i = 1, 10 do
        local r = CreateFrame("Frame", nil, child)
        r:SetSize(capColW, 30)
        r.week = MakeFS(r, 12, C_TEXT, "LEFT")
        r.week:SetPoint("TOPLEFT", r, "TOPLEFT", 4, -7)
        r.rank = MakeFS(r, 12, C_GOLD, "LEFT")
        r.rank:SetPoint("TOPLEFT", r, "TOPLEFT", 64, -7)
        r.barBG = r:CreateTexture(nil, "BACKGROUND")
        r.barBG:SetPoint("TOPLEFT", r, "TOPLEFT", 106, -9)
        r.barBG:SetSize(120, 10)
        r.bar = r:CreateTexture(nil, "ARTWORK")
        r.bar:SetPoint("TOPLEFT", r.barBG, "TOPLEFT", 0, 0)
        r.bar:SetHeight(10)
        r.bar:SetColorTexture(0.27, 0.75, 0.45, 0.85)
        r.cum = MakeFS(r, 12, C_TEXT, "RIGHT")
        r.cum:SetPoint("TOPRIGHT", r, "TOPLEFT", capColW - 36, -7)
        r.inc = MakeFS(r, 12, C_GREY, "RIGHT")
        r.inc:SetPoint("TOPRIGHT", r, "TOPLEFT", capColW - 4, -7)
        r.sep = r:CreateTexture(nil, "BACKGROUND")
        r.sep:SetPoint("BOTTOMLEFT", r, "BOTTOMLEFT", 2, 0)
        r.sep:SetPoint("BOTTOMRIGHT", r, "BOTTOMRIGHT", -2, 0)
        r.sep:SetHeight(1)
        r.sep:SetColorTexture(1, 1, 1, 0.06)
        PV.capRows[i] = r
    end"""))

# P5 bfRows 行 → 本周轮换芯片 + 声望二级按钮
pv.append((
"""    for i = 1, 4 do
        local r = CreateFrame("Frame", nil, child)
        r:SetSize(PV.W, PV.ROW_H)
        r.name = MakeFS(r, 14, C_TEXT, "LEFT")
        r.name:SetPoint("TOPLEFT", r, "TOPLEFT", 6, -6)
        r.band = MakeFS(r, 14, C_GREY, "LEFT")
        r.band:SetPoint("TOPLEFT", r, "TOPLEFT", 196, -6)
        r.size = MakeFS(r, 14, C_GREY, "LEFT")
        r.size:SetPoint("TOPLEFT", r, "TOPLEFT", 356, -6)
        r.cta = MakeFS(r, 14, C_GOLD, "LEFT")
        r.cta:SetPoint("TOPLEFT", r, "TOPLEFT", 486, -6)
        r.sep = r:CreateTexture(nil, "BACKGROUND")
        r.sep:SetPoint("BOTTOMLEFT", r, "BOTTOMLEFT", 4, 0)
        r.sep:SetPoint("BOTTOMRIGHT", r, "BOTTOMRIGHT", -4, 0)
        r.sep:SetHeight(1)
        r.sep:SetColorTexture(1, 1, 1, 0.06)
        PV.bfRows[i] = r
    end""",
"""    -- ★★ 本周页战场轮换芯片：悬浮提示 等级段 / 人数 / 召唤轮换 全量信息。
    for i, rec in ipairs(RD.battlefields) do
        local bt = NewButton(child, FIELD_LABEL[rec.key] or rec.key, 148, 24, 12)
        MakeOutline(bt, 1, 0.82, 0)
        bt.__huiKeepTextColor = true
        bt.__bf = rec
        bt:SetScript("OnEnter", function(self)
            local d = self.__bf
            local cta = (d.cta > 0) and format(L["召唤轮换 %d"], d.cta) or L["不在轮换"]
            if SetTip then
                SetTip(self, format("%s · %s · %s",
                    format(L["%d–%d 级"], d.minLevel, d.maxLevel),
                    format(L["%d 对 %d"], d.size, d.size), cta))
            end
        end)
        bt:SetScript("OnLeave", function() GameTooltip:Hide() end)
        ForwardWheel(bt)
        PV.weekBf[i] = bt
    end

    -- ★★ 声望页二级阵营按钮：按 REP_DEFS 注册表生成，新阵营插一条即多一枚。
    for i, def in ipairs(REP_DEFS) do
        local bt = NewButton(child, def.text, 120, 24, 12)
        MakeOutline(bt, 1, 0.82, 0)
        bt.__huiKeepTextColor = true
        bt.__rep = def.key
        bt:SetScript("OnClick", function(self)
            PV.selRep = self.__rep
            PV.Render()
        end)
        PV.repBtns[i] = bt
    end"""))

# P6 secSpecs 加 weekCaps 分区标题
pv.append((
"""        { key = "capsFoot",  fs = 11, col = C_GREY },""",
"""        { key = "capsFoot",  fs = 11, col = C_GREY },
        { key = "weekCaps",  fs = 14, col = C_GOLD },"""))

# P7 HideAll
pv.append((
"""    for i = 1, 4 do PV.bfRows[i]:Hide() end
""",
"""    for i = 1, #RD.battlefields do PV.weekBf[i]:Hide() end
    for i = 1, #REP_DEFS do PV.repBtns[i]:Hide() end
"""))

# P8 Render 分流
pv.append((
"""    if PV.cur == "caps" then
        PV.RenderCaps()
    elseif PV.cur == "sets" then
        PV.RenderSets()
    elseif PV.cur == "fields" then
        PV.RenderFields()
    elseif PV.cur == "spear" then
        PV.RenderSpear()
    elseif PV.cur == "sprint" then
        PV.RenderSprint()
    else
        PV.RenderRanks()
    end""",
"""    if PV.cur == "week" then
        PV.RenderWeek()
    elseif PV.cur == "rep" then
        PV.RenderRep()
    elseif PV.cur == "sets" then
        PV.RenderSets()
    else
        PV.RenderRanks()
    end"""))

# P9 SetTab 键名校验（存档/旧键回退军衔页）
pv.append((
"""function PV.SetTab(key)
    if not PV.built then return end
    PV.cur = key""",
"""function PV.SetTab(key)
    if not PV.built then return end
    local ok
    for _, def in ipairs(TAB_DEFS) do
        if def.key == key then ok = true end
    end
    if not ok then key = "ranks" end
    PV.cur = key"""))

# P10 删除 RenderCaps
pv.append((
"""function PV.RenderCaps()
    local y = 0
    local maxCum = RD.caps[10].cum
    for i = 1, 10 do
        local rec = RD.caps[i]
        local row = PV.capRows[i]
        row.week:SetText(format(L["第 %d 周"], rec.week))
        row.rank:SetText(format("R%d", rec.rank))
        row.bar:SetWidth(floor(300 * rec.cum / maxCum))
        row.cum:SetText(format("%d", rec.cum))
        row.inc:SetText(format("+%d", rec.inc))
        row:SetPoint("TOPLEFT", PV.child, "TOPLEFT", 0, -y)
        row:Show()
        y = y + 34
    end
    local foot = PV.labels.capsFoot
    foot:SetPoint("TOPLEFT", PV.child, "TOPLEFT", 4, -(y + 8))
    foot:SetText(L["等级 4 和 10 永远不是某周的上限；第 7 周一次跳两级（等级 11 与黑色战争坐骑）；上限按赛季累计点数计算，晚开始可直接冲级"])
    foot:Show()
    PV.child:SetHeight(y + 40)
end

""",
""))

# P11 RenderFields → RenderHonorBody（任务 + 传承，供声望页荣誉之地条目调用）
pv.append((
"""function PV.RenderFields()
    local y = 0
    local head = PV.labels.bfHead
    head:SetPoint("TOPLEFT", PV.child, "TOPLEFT", 4, -y)
    head:SetText(format("%s · %s · %s · %s", L["战场"], L["等级"], L["人数"], L["战斗的召唤"]))
    head:Show()
    y = y + 26
    for i, rec in ipairs(RD.battlefields) do
        local row = PV.bfRows[i]
        row.name:SetText(FIELD_LABEL[rec.key] or rec.key)
        row.band:SetText(format(L["%d–%d 级"], rec.minLevel, rec.maxLevel))
        row.size:SetText(format(L["%d 对 %d"], rec.size, rec.size))
        if rec.cta > 0 then
            row.cta:SetText(format(L["召唤轮换 %d"], rec.cta))
        else
            row.cta:SetText(L["不在轮换"])
        end
        row:SetPoint("TOPLEFT", PV.child, "TOPLEFT", 0, -y)
        row:Show()
        y = y + PV.ROW_H
    end
    local foot = PV.labels.bfFoot
    foot:SetPoint("TOPLEFT", PV.child, "TOPLEFT", 4, -(y + 6))
    foot:SetText(L["每周前三个战场轮流当“战斗的召唤”：暗矛群岛 → 阿拉希盆地 → 战歌峡谷，当周给更多荣誉与等级点数；各战场荣誉已拉平"])
    foot:Show()
    y = y + 34
    local taskHead = PV.labels.taskHead""",
"""function PV.RenderHonorBody(y)
    local taskHead = PV.labels.taskHead"""))
pv.append((
"""    for i = 1, #LEGACY_TEXTS do
        PV.legacyRows[i]:SetPoint("TOPLEFT", PV.child, "TOPLEFT", 0, -y)
        PV.legacyRows[i]:Show()
        y = y + 24
    end
    PV.child:SetHeight(y + 16)
end

function PV.RenderSpear()
    local y = 0
""",
"""    for i = 1, #LEGACY_TEXTS do
        PV.legacyRows[i]:SetPoint("TOPLEFT", PV.child, "TOPLEFT", 0, -y)
        PV.legacyRows[i]:Show()
        y = y + 24
    end
    return y + 4
end

function PV.RenderRep()
    local y = 0
    for i, def in ipairs(REP_DEFS) do
        local bt = PV.repBtns[i]
        bt:SetPoint("TOPLEFT", PV.child, "TOPLEFT", 4 + (i - 1) * 126, -y)
        SetOutline(bt, PV.selRep == def.key, 1, 0.82, 0)
        bt:Show()
    end
    y = y + 30
    if PV.selRep == "honor" then
        y = PV.RenderHonorBody(y)
    else
        y = PV.RenderSpearBody(y)
    end
    PV.child:SetHeight(y + 8)
end

function PV.RenderSpearBody(y)
"""))

# P12 RenderSpear 尾部：只 return y（高度由 RenderRep 统一收口）
pv.append((
"""    PV.child:SetHeight(y + 8)
end

LiveState = function()""",
"""    return y
end

LiveState = function()"""))

# P13 RenderSprint → RenderWeek；标题并入本周口径
pv.append((
"""function PV.RenderSprint()""", """function PV.RenderWeek()"""))
pv.append((
"""    head:SetText(L["荣誉冲刺 · 每周结算模型"])""",
"""    head:SetText(format("%s · %s", L["本周荣誉"], L["每周结算模型"]))"""))

# P14 RenderWeek 尾部追加：周上限双列 + 战场轮换条
pv.append((
"""    note:SetText(L["CP 结算存在 ±10 点的已知浮动 bug，实际结果可能相差一档；起点模拟按 0% 进度、0 荣誉计算，仅供参考"])
    note:Show()
    PV.child:SetHeight(y + 34)
end""",
"""    note:SetText(L["CP 结算存在 ±10 点的已知浮动 bug，实际结果可能相差一档；起点模拟按 0% 进度、0 荣誉计算，仅供参考"])
    note:Show()
    y = y + FSHeight(note, 14) + 22

    local capsHead = PV.labels.weekCaps
    capsHead:SetPoint("TOPLEFT", PV.child, "TOPLEFT", 4, -y)
    capsHead:SetText(L["周上限 · 按赛季累计点数"])
    capsHead:Show()
    y = y + 26
    local maxCum = RD.caps[10].cum
    local halfW = floor(PV.W / 2) - 16
    for i = 1, 10 do
        local rec = RD.caps[i]
        local row = PV.capRows[i]
        local col = (i - 1) % 2
        local rowi = floor((i - 1) / 2)
        row.week:SetText(format(L["第 %d 周"], rec.week))
        row.rank:SetText(format("R%d", rec.rank))
        row.bar:SetWidth(floor(120 * rec.cum / maxCum))
        row.cum:SetText(format("%d", rec.cum))
        row.inc:SetText(format("+%d", rec.inc))
        row:SetPoint("TOPLEFT", PV.child, "TOPLEFT", col * (halfW + 32), -(y + rowi * 30))
        row:Show()
    end
    y = y + 5 * 30
    local cfoot = PV.labels.capsFoot
    cfoot:SetPoint("TOPLEFT", PV.child, "TOPLEFT", 4, -(y + 6))
    cfoot:SetText(L["等级 4 和 10 永远不是某周的上限；第 7 周一次跳两级（等级 11 与黑色战争坐骑）；上限按赛季累计点数计算，晚开始可直接冲级"])
    cfoot:Show()
    y = y + FSHeight(cfoot, 14) + 22

    local bfHead = PV.labels.bfHead
    bfHead:SetPoint("TOPLEFT", PV.child, "TOPLEFT", 4, -y)
    bfHead:SetText(format("%s · %s", L["战场轮换"], L["战斗的召唤"]))
    bfHead:Show()
    y = y + 26
    for i, rec in ipairs(RD.battlefields) do
        local bt = PV.weekBf[i]
        bt:SetPoint("TOPLEFT", PV.child, "TOPLEFT", 4 + (i - 1) * 156, -y)
        bt:Show()
    end
    y = y + 30
    local bfoot = PV.labels.bfFoot
    bfoot:SetPoint("TOPLEFT", PV.child, "TOPLEFT", 4, -(y + 4))
    bfoot:SetText(L["每周前三个战场轮流当“战斗的召唤”：暗矛群岛 → 阿拉希盆地 → 战歌峡谷，当周给更多荣誉与等级点数；各战场荣誉已拉平"])
    bfoot:Show()
    y = y + FSHeight(bfoot, 14) + 10
    PV.child:SetHeight(y + 8)
end"""))

patch(SRC, pv, 'PvPUI.lua')

# ────────────────────────── 三语 ──────────────────────────
zh_add = '''
L["本周"] = "本週"
L["声望"] = "聲望"
L["荣誉之地"] = "榮譽之地"
L["本周荣誉"] = "本週榮譽"
L["战场轮换"] = "戰場輪換"
L["周上限 · 按赛季累计点数"] = "週上限 · 按賽季累計點數"
'''
en_add = '''
L["本周"] = "This Week"
L["声望"] = "Reputation"
L["荣誉之地"] = "Honor Grounds"
L["本周荣誉"] = "This Week's Honor"
L["战场轮换"] = "Battleground Rotation"
L["周上限 · 按赛季累计点数"] = "Weekly Cap · by season-cumulative points"
'''
for path, add, tag in ((ZH, zh_add, 'zhTW'), (EN, en_add, 'enUS')):
    s = io.open(path, encoding='utf-8', newline='').read()
    if 'L["本周"]' in s:
        print('%s: 已有键，跳过' % tag)
        continue
    io.open(path, 'a', encoding='utf-8', newline='').write(add)
    print('%s: +6 键' % tag)

# ────────────────────────── harness ──────────────────────────
hk = []
hk.append((
"""    _pvp_hd = open(os.path.join(ADDON, 'Core', 'Data', 'Data_PvPHonor.lua'), encoding='utf-8',""",
"""    ck('★ PvPUI 方案 A 四页签 + 声望二级注册表（week/rep 合并、bfRows 移除）',
       'key = "week"' in _pv and 'key = "rep"' in _pv and 'local REP_DEFS' in _pv
       and 'PV.selRep = "spear"' in _pv and 'PV.RenderWeek' in _pv
       and 'PV.RenderRep' in _pv and 'PV.bfRows' not in _pv)
    _pvp_hd = open(os.path.join(ADDON, 'Core', 'Data', 'Data_PvPHonor.lua'), encoding='utf-8',"""))
hk.append((
"""        TF_NS.PvPModule.SetTab("sprint")
        ck("★ 冲刺子页切换成功（cur=sprint、场景行池 5、目标钮 13、模拟钮 14）",
           TF_NS.PvPModule.cur == "sprint"
""",
"""        TF_NS.PvPModule.SetTab("week")
        ck("★ 本周子页切换成功（cur=week、场景行 5、目标钮 13、模拟钮 14、上限行 10、轮换芯片 4）",
           TF_NS.PvPModule.cur == "week"
           and #TF_NS.PvPModule.weekBf == 4
           and #TF_NS.PvPModule.capRows == 10
"""))
hk.append((
"""        U:SwitchSub("Dungeons")
        ck("★ 切回 5人本后 pvpPage 隐藏（互斥）",""",
"""        TF_NS.PvPModule.SetTab("rep")
        ck("★ 声望页二级阵营：repBtns 2 枚、默认暗矛",
           TF_NS.PvPModule.cur == "rep"
           and #TF_NS.PvPModule.repBtns == 2
           and TF_NS.PvPModule.selRep == "spear")
        TF_NS.PvPModule.selRep = "honor"
        TF_NS.PvPModule.Render()
        ck("★ 荣誉之地条目渲染（任务行/传承行文本就位）",
           TF_NS.PvPModule.taskRows[1].txt.__text ~= nil
           and TF_NS.PvPModule.legacyRows[3].txt.__text ~= nil)
        TF_NS.PvPModule.selRep = "spear"
        TF_NS.PvPModule.Render()
        U:SwitchSub("Dungeons")
        ck("★ 切回 5人本后 pvpPage 隐藏（互斥）","""))
patch(HK, hk, 'harness')

print('ALL-OK')
