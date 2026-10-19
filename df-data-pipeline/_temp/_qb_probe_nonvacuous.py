# -*- coding: utf-8 -*-
"""快捷按钮栏 / 全仓图标变异的**非恒真**逐条证明（29 条）。

为什么单独立这个：`df_mut_check.py` 是把全部变异**一次性**注入的，而其中
`MUT_QUAL_FALLBACK` 会让 `static_guard()` 早崩 → `main()` 里的动态断言（qb_guard）
在变异批次中**从不执行**。所以「总批变红」不能证明「这条断言真的抓住了这个变异」。
本脚本一次只注入一条，要求**指定的那条断言**出现 [FAIL]，并通过后立刻从源侧还原。

全程只动 beta 侧、跑完必还原；退出码 0 = 全部被对应断言抓住、漏网 0。
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from df_mut_check import to_file_style  # noqa: E402  （锚点行尾风格统一：本机 autocrlf=true）

PY = sys.executable or 'python'
TITAN = r'D:\workspace\DungeonsForever'
BETA = r'D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\DungeonsForever'

# (标签, 文件, old, new, 期望变红的断言名子串)
#   锚点一律「源代码行原文」（含缩进），与 df_mut_check.py 的变异条目保持一致。
CASES = [
    ('S01 吸附被架空（槽位写死第二槽）', 'Core/QuickBar.lua',
     '    local x = self:SlotX()',
     '    local x = self.SLOT2 -- MUT: never hug the main window\n',
     '吸附两档'),
    ('S02 不再让位给装备过滤面板', 'Core/QuickBar.lua',
     '    if LF and LF.ConfigPopup and PopShown(LF:ConfigPopup()) then return self.SLOT2 end',
     '    -- MUT: never yield to the loot-filter panel\n',
     '吸附两档'),
    ('S03 不再挂钩弹窗显隐', 'Core/QuickBar.lua',
     '    pop:HookScript("OnShow", function() if QB.built then QB:Reanchor() end end)',
     '    -- MUT: no onshow hook\n',
     '吸附两档'),
    ('S04 不再启动即建（等主窗首次 OnShow）', 'Core/QuickBar.lua',
     '    QB:Boot()',
     '    -- MUT: no eager boot\n',
     '启动即建'),
    ('S05 面板改挂 UIParent（不再是主窗子帧）', 'Core/QuickBar.lua',
     '    local f = CreateFrame("Frame", "DungeonsForever_QuickBar", host, "BackdropTemplate")',
     '    local f = CreateFrame("Frame", "DungeonsForever_QuickBar", UIParent, "BackdropTemplate")\n',
     '面板是主窗的子帧'),
    ('S06 条目 1px 圆角描边被摘', 'Core/QuickBar.lua',
     '    r.edgePieces = ns.hui.BuildRoundBorder(r, self.RADIUS, C_EDGE)',
     '    r.edgePieces = {} -- MUT: no rounded edge\n',
     '条目 = 圆角按钮'),
    ('S07 条目圆角底被摘', 'Core/QuickBar.lua',
     '    r.fillPieces = ns.hui.BuildRoundedBG(r, self.RADIUS, { 1, 1, 1, self.FILL }, "both", false, nil, true)',
     '    r.fillPieces = {} -- MUT: no rounded fill\n',
     '条目 = 圆角按钮'),
    ('S08 条目常态就画成金边', 'Core/QuickBar.lua',
     '    PaintEdge(r, C_EDGE)',
     '    PaintEdge(r, C_GOLD) -- MUT: idle already gold\n',
     '条目 = 圆角按钮'),
    ('S09 标题字号回到 16', 'Core/QuickBar.lua',
     'QB.FS_HEAD, QB.FS_NAME, QB.FS_AUX = 14, 14, 11',
     'QB.FS_HEAD, QB.FS_NAME, QB.FS_AUX = 16, 14, 11 -- MUT: title back to 16\n',
     '标题「5人本专业探索」'),
    ('S10 标题文字退回旧的「快捷」', 'Core/QuickBar.lua',
     '    head:SetText(L["5人本专业探索"])',
     '    head:SetText(L["快捷"]) -- MUT: old title\n',
     '标题「5人本专业探索」'),
    ('S11 副本等级副行回来', 'Core/QuickBar.lua',
     '    return {\n        text = d.name,',
     '    return {\n        text = d.name,\n'
     '        aux = format("%d-%d", d.levelMin or 0, d.levelMax or 0),',
     '条目恒单行'),
    ('S12 条目名退回换行', 'Core/QuickBar.lua',
     '    r.name:SetWordWrap(false)',
     '    r.name:SetWordWrap(true) -- MUT: wrap back\n',
     '条目恒单行'),
    ('S13 不再监听升级事件', 'Core/QuickBar.lua',
     '    ev:RegisterEvent("PLAYER_LEVEL_UP")',
     '    ev:RegisterEvent("PLAYER_INVENTORY_CHANGED") -- MUT: lost level up\n',
     '主窗显示时刷新快捷栏'),
    ('S14 副本分组开关被绕过', 'Core/QuickBar.lua',
     '    if cfg.groups.dungeon then\n'
     '        out[#out + 1] = { text = L["全部副本"], act = "page", key = "Dungeons", gold = true }',
     '    if true then\n'
     '        out[#out + 1] = { text = L["全部副本"], act = "page", key = "Dungeons", gold = true }',
     '关掉副本分组'),
    ('S15 内容帧不转发滚轮', 'Core/QuickBar.lua',
     '    content:SetScript("OnMouseWheel", function(_, delta) QB:Scroll(delta) end)',
     '    content:SetScript("OnMouseWheel", function(_, delta) end) -- MUT: no wheel\n',
     '滚轮转发三处齐备'),
    ('S16 专业口径默认变成「全部」', 'Core/Core.lua',
     '    if q.profMode ~= "all" then q.profMode = "learned" end',
     '    q.profMode = "all" -- MUT: all professions by default\n',
     '快捷栏默认配置'),
    ('S17 「全部副本」退回副本组尾条', 'Core/QuickBar.lua',
     '        out[#out + 1] = { text = L["全部副本"], act = "page", key = "Dungeons", gold = true }\n'
     '        out[#out + 1] = { grp = L["推荐五人本"] }',
     '        out[#out + 1] = { grp = L["推荐五人本"] }\n'
     '        out[#out + 1] = { text = L["全部副本"], act = "page", key = "Dungeons", gold = true }',
     '「全部副本」摆在'),
    ('S18 分组头字号回到 11', 'Core/QuickBar.lua',
     'QB.FS_GRP = 14',
     'QB.FS_GRP = 11 -- MUT: group header back to 11\n',
     '分组头（推荐五人本'),
    ('S19 专业条目不再画图标', 'Core/QuickBar.lua',
     '            if wantIcon then SetIcon(r.icon, sp.icon) end',
     '            -- MUT: icon not painted\n',
     '专业条目内嵌 16px 圆角图标'),
    ('S20 专业图标不再倒圆角', 'Core/QuickBar.lua',
     '    if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(r.icon) end',
     '    -- MUT: square icon\n',
     '专业条目内嵌 16px 圆角图标'),
    ('S21 图标贴图不再裁边（7% 内缩被摘）', 'Core/QuickBar.lua',
     '    r.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)',
     '    r.icon:SetTexCoord(0, 1, 0, 1) -- MUT: no crop\n',
     '图标贴图裁边'),
    ('S22 专业页设置齿轮不再裁边', 'Core/ProfessionUI.lua',
     '    gear.__icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)',
     '    gear.__icon:SetTexCoord(0, 1, 0, 1) -- MUT: no crop\n',
     '职业与专业页内所有图标裁边'),
    ('S23 BIS 配装部位卡片图标不再裁边', 'Core/BisUI.lua',
     '    c.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)',
     '    c.icon:SetTexCoord(0, 1, 0, 1) -- MUT: no crop\n',
     'BIS 配装两处装备图标裁边'),
    ('S24 探索页战斗法师导航图标不再裁边', 'Core/ExploreUI.lua',
     '        bt.__icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)\n'
     '        if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(bt.__icon) end\n'
     '        bt.__icon:SetTexture("Interface\\\\Icons\\\\inv_sword_05")',
     '        bt.__icon:SetTexCoord(0, 1, 0, 1) -- MUT: no crop\n'
     '        if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(bt.__icon) end\n'
     '        bt.__icon:SetTexture("Interface\\\\Icons\\\\inv_sword_05")',
     '探索页四个子页导航图标裁边'),
    # ---- ㊱c 图标倒圆角（2026-09-30 用户实机截图：「专业页面，你所有图标都没有倒圆角啊」+「BIS 配装里面也是啊」）----
    ('T01 RoundIcon 蒙版挂回父帧', 'Core/Hui.lua',
     '        mask:SetAllPoints(tex)',
     '        mask:SetAllPoints(f)   -- MUT: mask on parent frame',
     'RoundIcon 的蒙版按'),
    ('T02 专业页左列导航图标不挂蒙版', 'Core/ProfessionUI.lua',
     '        if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(bt.__icon) end\n',
     '        -- MUT: square icon\n',
     '24 处图标各自挂了 RoundIcon'),
    ('T03 BIS 部位卡片图标不挂蒙版', 'Core/BisUI.lua',
     '    if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(c.icon) end\n',
     '    -- MUT: square icon\n',
     '24 处图标各自挂了 RoundIcon'),
    ('T04 探索页清单行图标不挂蒙版', 'Core/ExploreUI.lua',
     '    if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(r.icon) end\n',
     '    -- MUT: square icon\n',
     '24 处图标各自挂了 RoundIcon'),
    ('T05 掉落过滤图标按钮不挂蒙版', 'Core/LootFilterUI.lua',
     '    if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(bt.tex) end\n',
     '    -- MUT: square icon button\n',
     '掉落过滤图标按钮倒圆角'),
    # ---- ㊸ 详细页「地图」页签 · 多层副本「楼层」按钮（2026-09-30 加，用户点名通灵学院）----
    ('M01 多层副本被压成单层', 'Core/MapUI.lua',
     '    scholomance           = { "ScholomanceOld",\n'
     '        { "ScholomanceOld1_", "ScholomanceOld2_", "ScholomanceOld3_", "ScholomanceOld4_" } },\n',
     '    scholomance           = { "ScholomanceOld", { "ScholomanceOld1_" } }, -- MUT: flat\n',
     '层数与客户端实测逐条一致'),
    ('M02 共用层被拆散（斯坦索姆两区各一套）', 'Core/MapUI.lua',
     '    stratholme_service    = ST,\n',
     '    stratholme_service    = { "Stratholme", { "Stratholme2_" } }, -- MUT: unshared\n',
     '斯坦索姆两区共用一套'),
    ('M03 取层忽略层号（永远第 1 层）', 'Core/MapUI.lua',
     '    return WM .. ART[id][1] .. "\\\\" .. layers[i]\n',
     '    return WM .. ART[id][1] .. "\\\\" .. layers[1] -- MUT: idx ignored\n',
     'PathAt 取第 i 层'),
    ('M04 取层不做越界判断', 'Core/MapUI.lua',
     '    if not (layers and layers[i]) then return nil end\n',
     '    if not layers then return nil end if not layers[i] then i = 1 end -- MUT: no bounds\n',
     'PathAt 取第 i 层'),
    ('M05 楼层按钮条永不出现', 'Core/MapUI.lua',
     '    frame.bar:SetShown(multi)\n',
     '    frame.bar:SetShown(false) -- MUT: bar off\n',
     '楼层按钮条显示'),
    ('M06 单层副本也铺楼层按钮条', 'Core/MapUI.lua',
     '    local multi = (n > 1)\n',
     '    local multi = true -- MUT: bar always\n',
     '楼层按钮条整条不出现'),
    ('M07 点楼层按钮只记状态不重画', 'Core/MapUI.lua',
     '    M.curLayer = i\n    M.Paint(M.curD)\n',
     '    M.curLayer = i -- MUT: no repaint\n',
     '切层真的生效'),
    ('M08 换副本复位到末层', 'Core/MapUI.lua',
     '        M.curId, M.curLayer, M.detailEn = id, 1, nil\n',
     '        M.curId, M.curLayer, M.detailEn = id, #layers, nil -- MUT: reset to last\n',
     '回到第 1 层'),
    ('M09 楼层条预留高度归零', 'Core/MapUI.lua',
     'M.BAR_H = 20',
     'M.BAR_H = 0',
     '楼层按钮池就绪'),
    ('M10 Paint 里又新建帧', 'Core/MapUI.lua',
     '    local lay = M.Layout(cw, ch)\n',
     '    local lay = M.Layout(cw, ch)\n    CreateFrame("Frame", nil, frame) -- MUT: frame in paint\n',
     '零新建帧'),
    # ---- ㊹ 首领钉点 + 右栏首领栏（2026-09-30 第三轮，用户「点 boss 出掉落 + 一句话攻略」）----
    ('U01 钉点坐标越界（left% 141.5）', 'Core/Data/Data_BossPos.lua',
     '        ["Bazzalan"] = { { 41.5, 86.2 } },\n',
     '        ["Bazzalan"] = { { 141.5, 86.2 } }, -- MUT: out of range\n',
     '钉点坐标全落在'),
    ('U02 同一点写两遍（钉点数膨胀）', 'Core/Data/Data_BossPos.lua',
     '        ["Kresh"] = { { 25.8, 44.6 } },',
     '        ["Kresh"] = { { 25.8, 44.6 }, { 25.8, 44.6 } }, -- MUT: duplicate\n',
     '首领坐标表规模'),
    ('U03 一整副本的坐标被摘掉', 'Core/Data/Data_BossPos.lua',
     '    ["gnomeregan"] = {\n        ["Crowd Pummeler 9-60"] = { { 43.8, 86.5, 3 } },\n'
     '        ["Dark Iron Ambassador"] = { { 29.5, 54, 4 } },\n'
     '        ["Electrocutioner 6000"] = { { 24.8, 67.9, 2 } },\n'
     '        ["Grubbis"] = { { 81.9, 65.1 } },\n'
     '        ["Mekgineer Thermaplugg"] = { { 31.3, 30, 4 } },\n'
     '        ["Viscous Fallout"] = { { 57.6, 56.6 } },\n    },\n',
     '    -- MUT: gnomeregan dropped\n',
     '首领坐标表规模'),
    ('U04 首领名改错（对不上掉落表）', 'Core/Data/Data_BossPos.lua',
     '        ["Oggleflint"] = { { 56.1, 38 } },\n',
     '        ["Oggleflint XX"] = { { 56.1, 38 } }, -- MUT: name mismatch\n',
     '逐条能在掉落表里对查'),
    ('U05 坐标查表失效（PosFor 恒 nil）', 'Core/MapUI.lua',
     '    local pts = all and en and all[en]\n',
     '    local pts = nil -- MUT: lookup dead\n',
     'PosFor：查得到回坐标数组'),
    ('U06 无攻略回空串而不是 nil', 'Core/MapUI.lua',
     '        if bs[i] and bs[i].en == en then return bs[i].text end\n    end\n    return nil\nend\n',
     '        if bs[i] and bs[i].en == en then return bs[i].text end\n    end\n'
     '    return "" -- MUT: empty string\nend\n',
     'GuideFor：洛丹伦废墟有真攻略'),
    ('U07 名单不再收「只有坐标/只有攻略」的来源（2026-09-30 晚洛丹伦 6 boss 补钉点后，'
     'guide 单项不再能单独翻行为，变异改为 pos+guide 一起摘）', 'Core/MapUI.lua',
     '           and ((s[4] and s[4] ~= "") or M.PosFor(id, s[1]) or M.GuideFor(id, s[1])) then\n',
     '           and (s[4] and s[4] ~= "") then -- MUT: pos/guide-only dropped\n',
     '洛丹伦废墟 7 条'),
    ('U08 钉点永远不画', 'Core/MapUI.lua',
     '    if list and #list > 0 then\n',
     '    if false then -- MUT: pins never drawn\n',
     '钉点层显示'),
    ('U09 SyncPins 不按当前层取（各层钉点全画在当前层）', 'Core/MapUI.lua',
     '        list = M.PinsFor(M.curId, M.FloorNumAt(M.curId, M.curLayer or 1))\n',
     '        list = M.PinsFor(M.curId) -- MUT: every floor\n',
     '只画本层钉点'),
    ('U10 百分比换算写错（/10 而不是 /100）', 'Core/MapUI.lua',
     '                        (p.left / 100) * cw, -(p.top / 100) * ch)\n',
     '                        (p.left / 10) * cw, -(p.top / 10) * ch) -- MUT: bad scale\n',
     '钉点按百分比换算到图上'),
    ('U11 钉点身份色被抹白', 'Core/MapUI.lua',
     '            local cr, cg, cb = M.BossColor(M.curId, p.en)\n'
     '            bt.dot:SetVertexColor(cr, cg, cb)\n            bt.nm:SetTextColor(cr, cg, cb)\n',
     '            local cr, cg, cb = 1, 1, 1 -- MUT: identity colors wiped\n'
     '            bt.dot:SetVertexColor(cr, cg, cb)\n            bt.nm:SetTextColor(cr, cg, cb)\n',
     '未选中钉点 = boss 身份色'),
    ('U12 再点同一点不能取消选中', 'Core/MapUI.lua',
     '    if M.detailEn == en then en = nil end',
     '    if false then en = nil end -- MUT: cannot deselect',
     '取消选中退回列表'),
    ('U13 点钉点只记状态不刷右栏', 'Core/MapUI.lua',
     '        bt:SetScript("OnClick", function(self) M.Select(self.__en) end)\n',
     '        bt:SetScript("OnClick", function(self) M.detailEn = self.__en end) -- MUT: no render\n',
     '点地图钉点 → 右栏切详情'),
    ('U14 详情永远显示「攻略待补充」（真攻略被无视）', 'Core/MapUI.lua',
     '            local guide = M.GuideFor(id, M.detailEn)\n',
     '            local guide = nil -- MUT: real guide ignored\n',
     '真攻略'),
    ('U15 掉落行永不显示', 'Core/MapUI.lua',
     '    r:Show()\nend\n',
     '    r:Hide() -- MUT: loot rows never shown\nend\n',
     '掉落卡片行数'),
    ('U16 「‹ 全部首领」不回列表', 'Core/MapUI.lua',
     'function M.ShowList()\n    M.detailEn = nil\n',
     'function M.ShowList()\n    -- MUT: no clear\n',
     '全部首领」→ 退回列表'),
    ('U17 楼层按钮条退回地图下方', 'Core/MapUI.lua',
     '    frame.bar:SetPoint("TOPRIGHT", frame, "TOPLEFT",\n'
     '                       cx + cw - M.FLOOR_INSET, -(cy + M.FLOOR_INSET))\n',
     '    frame.bar:SetPoint("BOTTOMLEFT", frame, "BOTTOMLEFT", cx, 0) -- MUT: bar under the map\n',
     '楼层按钮条锚在'),
    ('U18 多层副本又预留楼层条高度', 'Core/MapUI.lua',
     '    frame.pinW, frame.pinH = cw, ch\n',
     '    frame.pinW, frame.pinH = cw, ch - (layers and #layers > 1 and M.BAR_H or 0) -- MUT: reserve\n',
     '单层与多层副本地图区高度完全相同'),
    ('U19 钉点同步里又新建帧', 'Core/MapUI.lua',
     '    for i = n + 1, M.MAX_PINS do frame.pinBtns[i]:Hide() end\n',
     '    CreateFrame("Frame", nil, frame) -- MUT: frame in sync\n'
     '    for i = n + 1, M.MAX_PINS do frame.pinBtns[i]:Hide() end\n',
     '选中/渲染零新建帧'),
    ('U20 掉落行图标不裁边', 'Core/MapUI.lua',
     '        r.icon:SetPoint("LEFT", r, "LEFT", 6, 0)\n        r.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)\n',
     '        r.icon:SetPoint("LEFT", r, "LEFT", 6, 0)\n        -- MUT: no crop\n',
     '28 处图标纹理一律'),
    ('U21 掉落行名字着色套 Unpack（QColor 返三值）', 'Core/MapUI.lua',
     '        r.name:SetTextColor(DG.QColor(DG.QualOf(id)))\n',
     '        r.name:SetTextColor(Unpack(DG.QColor(DG.QualOf(id))))\n',
     '绝不套 Unpack'),
    ('U22 SkillsFor 恒回 nil（技能全丢）', 'Core/MapUI.lua',
     '    if type(sk) ~= "table" or #sk == 0 then return nil end\n',
     '    if true then return nil end -- MUT\n',
     '第 1 行名字 = 客户端 GetSpellInfo'),
    ('U23 技能查表键位错层', 'Core/MapUI.lua',
     '    local sk = row and en and row[en]\n',
     '    local sk = row and en and (ns.BossSkills or {})[en] -- MUT\n',
     '第 1 行名字 = 客户端 GetSpellInfo'),
    ('U24 技能行的法术 id 被丢弃（悬停不出法术提示框）', 'Core/MapUI.lua',
     '                r.__sid = sidN\n',
     '                r.__sid = nil -- MUT\n',
     '法术 id 15496'),
    ('U25 技能行永不渲染（技能与真攻略全被无视）', 'Core/MapUI.lua',
     '            for _i = 1, #(sk or {}) do\n',
     '            for _i = 1, 0 do -- MUT\n',
     '第 2 行 = 客户端法术描述'),
    ('U26 掉落行不再调 ShowItemTip', 'Core/MapUI.lua',
     '            if self.__it then DG.ShowItemTip(self, self.__it) end\n',
     '            -- MUT: tooltip gone\n',
     'DG.ShowItemTip 真被调'),
    ('U28 技能行数据兜底图标被摘', 'Core/MapUI.lua',
     '                local cn, ic, cd = M.SpellRowFor(sidN, nm, ds ~= "" and ds or nil, fbIcon)\n',
     '                local cn, ic, cd = M.SpellRowFor(sidN, nm, ds ~= "" and ds or nil) -- MUT\n',
     '图标仍用数据侧 slug'),
    ('U29 钉点层过滤失效（全层一起画）', 'Core/MapUI.lua',
     '        if (p[3] or 1) == floor then\n',
     '        if true then -- MUT\n',
     '只画本层钉点'),
    ('U30 钉点锁死第 1 层（切层没钉点）', 'Core/MapUI.lua',
     '        if (p[3] or 1) == floor then\n',
     '        if (p[3] or 1) == 1 then -- MUT\n',
     '钉点换成本层首领'),
    ('U31 层号映射固定为显示序号', 'Core/MapUI.lua',
     '    return tonumber(lay:match("(%d+)_")) or idx or 1\n',
     '    return idx or 1 -- MUT\n',
     '诺莫瑞根第 5 序号'),
    ('U32 boss技能 标题被摘', 'Core/MapUI.lua',
     '    ttl:SetPoint("TOPLEFT", blk, "TOPLEFT", M.BLK_TITLE_X, -M.BLK_TITLE_TOP)\n',
     '    ttl:ClearAllPoints() -- MUT: skill card title anchor dropped\n',
     '卡头标题有锚点'),
    ('U27 MapUI 不再显式取 U（裸 U 悬停崩）', 'Core/MapUI.lua',
     'local U = Host.U',
     'local U = {} -- MUT\n',
     'DG.ShowItemTip 真被调'),
    ('V01 自制副本图永不显示（领主大厅 / 洛丹伦废墟退回空态）', 'Core/MapUI.lua',
     '        local cpath, cv1 = M.CustomFor(id)\n',
     '        local cpath, cv1 = nil, nil -- MUT: custom map never shows\n',
     '用户手绘图顶上'),
    ('V02 自制贴图漏到有图副本上（上一本的图没收起）', 'Core/MapUI.lua',
     '    frame.empty:Hide()\n    frame.customTex:Hide()\n',
     '    frame.empty:Hide()\n    -- MUT: custom tex leaks onto tile maps\n',
     'customTex 收起'),
    ('V03 自制图副本的钉点不画（领主大厅 / 洛丹伦废墟一颗都不出，但自制贴图照显）', 'Core/MapUI.lua',
     '    elseif M.curId and M.CustomFor(M.curId) then\n',
     '    elseif false then -- MUT: custom map loses its pins\n',
     '自制手绘图同样画钉点'),
    # （2026-10-01 撤下 V04/V05：ns.SpellTips wowhead 兜底表整体退役，MapUI 消费代码已删，无锚可守）
]


def paths(rel):
    return (os.path.join(TITAN, *rel.split('/')), os.path.join(BETA, *rel.split('/')))


def restore(rel):
    src, dst = paths(rel)
    shutil.copyfile(src, dst)


def main():
    bad = 0
    for label, rel, old, new, want in CASES:
        src, dst = paths(rel)
        with open(src, 'rb') as f:
            data = f.read()
        ob = to_file_style(old.encode('utf-8'), data)
        nb = to_file_style(new.encode('utf-8'), data)
        if data.count(ob) != 1:
            print('!! 锚点不唯一（%d）: %s' % (data.count(ob), label))
            bad += 1
            continue
        with open(dst, 'wb') as f:
            f.write(data.replace(ob, nb, 1))
        try:
            r = subprocess.run([PY, os.path.join(HERE, 'df_dungeon_check.py')],
                               capture_output=True, text=True, encoding='utf-8',
                               errors='replace')
            out = (r.stdout or '') + (r.stderr or '')
            hit = any(('[FAIL]' in ln and want in ln) for ln in out.split('\n'))
            print('%-34s → %s   （目标断言「%s」）'
                  % (label, '抓住' if hit else '★漏网★', want))
            if not hit:
                bad += 1
                for ln in out.split('\n'):
                    if '[FAIL]' in ln:
                        print('      FAIL: %s' % ln.strip()[:160])
        finally:
            restore(rel)
            src_b = open(src, 'rb').read()
            dst_b = open(dst, 'rb').read()
            if src_b != dst_b:
                print('!! 还原失败: %s' % rel)
                bad += 1
    print('总计 %d 条，漏网 %d 条' % (len(CASES), bad))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
