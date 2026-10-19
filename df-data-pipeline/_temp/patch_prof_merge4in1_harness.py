# -*- coding: utf-8 -*-
"""四合一 harness 同步：df_dungeon_check.py 断言改写 + df_mut_check.py 锚点重锚。"""
import sys

def load(p):
    b = open(p, "rb").read()
    eol = "\r\n" if b"\r\n" in b else "\n"
    return b.decode("utf-8"), eol, b

def save(p, txt, eol):
    txt = txt.replace("\r\n", "\n").replace("\n", eol)
    open(p, "wb").write(txt.encode("utf-8"))

def apply(path, patches):
    txt, eol, _ = load(path)
    for old, new in patches:
        o = old.replace("\n", eol)
        n = new.replace("\n", eol)
        c = txt.count(o)
        if c != 1:
            print("FAIL[%s]: count=%d for: %s" % (path, c, old[:70].replace("\n", "\\n")))
            sys.exit(1)
        txt = txt.replace(o, n)
    save(path, txt, eol)
    print("OK:", path)

CHK = r"D:\workspace\DungeonsForever\_temp\df_dungeon_check.py"
MUT = r"D:\workspace\DungeonsForever\_temp\df_mut_check.py"

chk_patches = []

chk_patches.append((
'''    # ④ 第 6 颗子页签：Legacy → 传承
    ck('★★ 子页签第 6 颗与相关标题都改叫「传承」（界面上不留英文 Legacy）',
       'text = L["传承"]' in profui and 'Legacy 里程碑' not in profui
       and 'Legacy 点数' not in profui and 'L["Legacy 特权' not in profui)''',
'''    # ④ 四合一（2026-10-10 用户定）：页签 7 → 4，营地/传承/说明并入总览
    _sts = profui[profui.index('DG.PROF_SUBTABS = {'):]
    _sts = _sts[:_sts.index('}') + 1]
    ck('★★ 四合一：子页签恰好 4 项（总览/配方/采集/升级），营地/传承/说明退出页签',
       _sts.count('key = "') == 4
       and 'L["营地"]' not in _sts and 'L["传承"]' not in _sts and 'L["说明"]' not in _sts
       and 'PushHead(rows, L["传承"], 1)' in profui
       and 'PushHead(rows, L["开发备注"], 2)' in profui)'''))

chk_patches.append((
'''    # ★ 表格只属于营地页的加成视图：RowsOverview 里不再举手要表
    _ovslice = profui[profui.index('function PD.RowsOverview'):
                      profui.index('function PD.RowsCamp')]
    ck('★ 总览首页不再挂对照表（对照页挂「营地系统 → 职业加成」，总览只留指路一句）',
       'wantTable' not in _ovslice and '营地系统 → 职业加成' in profui)
    ck('★ 对照页挂在「营地」（camping）名下、首页不放行营地页签（2026-09-24 用户定）',
       'if slug == "__index" then return { "overview" } end' in profui
       and 'if slug == "camping" then out[#out + 1] = "camp" end' in profui)''',
'''    # ★★ 四合一：对照表改挂总览页（camping + bonus 视图），「营地」页签退役
    _ovslice = profui[profui.index('function PD.RowsOverview'):
                      profui.index('local CAMP_AREA_MAP')]
    ck('★★ 四合一：camping 在总览页直出对照表（Render 举手 wantBonusTable），营地页签退出',
       'wantTable' not in _ovslice
       and 'PD.cur == "camping" then' in profui
       and 'PD.campView = "bonus"' in profui
       and '"camp"' not in profui
       and '营地系统 → 职业加成' not in profui)'''))

chk_patches.append((
'''    # ⑱ 营地页卡片化（2026-09-24 用户定稿「三档合一卡」）：复用段落卡机制
    #    特权段已删（传承内容归 Legacy 页）→ RowsCamp 里只剩 1 处裸 OV_GUT（坐标段前）。
    ck('★★ 营地联盟/部落视图套段落卡（RowsCamp 打 sec 编号 + Render 举手 hasSecs；段间空档 = OV_GUT）',
       '    PushGap(rows, 6)\\n    PushHead(rows, L["三档营地物件' in profui
       and 'PD.hasSecs = true\\n            PD.RowsCamp(rows, PD.campView)' in profui
       and profui.count('PushGap(rows, PD.OV_GUT)') >= 1
       and '对营地系统的贡献' not in profui)''',
'''    # ⑱ 四合一：营地段并入 RowsOverview（col=1），联盟/部落坐标同列直出（联盟蓝/部落红）
    ck('★★ 营地段并入总览（物件带悬停明细 + 联盟/部落坐标同列、阵营字体色）',
       '    PushHead(rows, L["营地"], 1)' in profui
       and 'for _, side in ipairs({ "a", "h" })' in profui
       and 'local C_ALLIANCE' in profui and 'local C_HORDE' in profui
       and 'nameColor = fc' in profui
       and 'function PD.RowsCamp' not in profui
       and '对营地系统的贡献' not in profui)'''))

chk_patches.append((
'''    ck('★ 旧指路文案从 RowsOverview 挪进宫格尾注（__index 分支不再 PushText 那句）',
       '各专业营地物件的档位对照表在左列' not in profui
       and 'L["营地档位对照表 →「营地系统 → 职业加成」"]' in profui)''',
'''    ck('★ 宫格尾注指路文案随四合一改写（营地页签退役 → 直指「营地系统」）',
       '各专业营地物件的档位对照表在左列' not in profui
       and 'L["营地档位对照表 →「营地系统」"]' in profui)'''))

chk_patches.append((
'''    ck('★ 对照页签名是「职业加成」（用户 2026-09-23 晚措辞，不叫单字「加成」）',
       'bt:SetText(L["职业加成"])' in profui and 'L["加成"]' not in profui)''',
'''    ck('★ 页签签名统一 def.text（「职业加成」改名逻辑退役；宫格卡副题仍用该词）',
       'bt:SetText(def.text)' in profui and 'bt:SetText(L["职业加成"])' not in profui
       and '物件 %d · 职业加成' in profui)'''))

chk_patches.append((
'''    ck('★★ camping 页签改名「职业加成」、对照页不再套工具条一层（2026-09-24 用户定）',
       'bt:SetText(L["职业加成"])' in profui and 'bt:SetText(def.text)' in profui)''',
'''    ck('★★ 联盟/部落切换钮退役（阵营坐标同列直出，不再需要视图切换）',
       'text = L["联盟"]' not in profui and 'text = L["部落"]' not in profui
       and 'PD.campView = k' not in profui)'''))

chk_patches.append((
'''    _rl = profui[profui.index('function PD.RowsLeveling'):profui.index('function PD.RowsLegacy')]''',
'''    _rl = profui[profui.index('function PD.RowsLeveling'):profui.index('function PD.RowsSettings')]'''))

chk_patches.append((
'''          ck("★ 专业页子页签 = 7 个固定槽位（总览/营地/配方/采集/升级/Legacy/说明）",
             #allTabs == 7, #allTabs)''',
'''          ck("★ 专业页子页签 = 4 个固定槽位（总览/配方/采集/升级；营地/传承/说明已并入总览）",
             #allTabs == 4
             and allTabs[1] == "overview" and allTabs[2] == "recipe"
             and allTabs[3] == "gather" and allTabs[4] == "leveling",
             #allTabs)'''))

chk_patches.append((
'''          ck("★ 渲染覆盖面够（专业×子页签 组合 >= 40）", n1 >= 40, n1)''',
'''          ck("★ 渲染覆盖面够（专业×子页签 组合 >= 22）", n1 >= 22, n1)'''))

chk_patches.append((
'''            ck("★★ 总览每个内容块一张段落卡（炼金术 5 段：简介/认证/速览/里程碑/营地）",
               _ovSecs >= 5 and _ovSecs <= 6 and _ovSecRows >= 10,
               tostring(_ovSecs) .. " 卡 / " .. tostring(_ovSecRows) .. " 行入段")''',
'''            ck("★★ 总览每个内容块一张段落卡（简介/传承/营地/速览/备注，≤ 卡池上限）",
               _ovSecs >= 5 and _ovSecs <= (PD.SEC_CARD_MAX or 8) and _ovSecRows >= 10,
               tostring(_ovSecs) .. " 卡 / " .. tostring(_ovSecRows) .. " 行入段")'''))

chk_patches.append((
'''                ck("★★ 点营地卡 → 直达「职业加成」对照表（camping + bonus 视图）",
                   PD.cur == "camping" and PD.tab == "camp" and PD.campView == "bonus"''',
'''                ck("★★ 点营地卡 → 直达总览页对照表（camping + bonus 视图，四合一）",
                   PD.cur == "camping" and PD.tab == "overview" and PD.campView == "bonus"'''))

chk_patches.append((
'''            -- ② 营地页「加成」：对照表只在这里（2026-09-24 从首页搬到「营地」名下；
            --    二轮：页签直接改名「职业加成」，不再多套一层工具钮）
            PD.Show("camping")
            PD.SetTab("camp")
            ck("★★ 营地页只有「加成」一支、自动落在它上面（对照总表就绪）",
               PD.campView == "bonus" and PD.wantBonusTable == true
               and PD.bonusTable ~= nil and PD.bonusTable.__shown == true,
               tostring(PD.campView) .. "/" .. tostring(PD.wantBonusTable))
            ck("★ camping 的营地页签已改名「职业加成」（点页签直达对照表）",
               PD.subBtns.camp ~= nil and PD.subBtns.camp:GetText() == "职业加成",
               tostring(PD.subBtns.camp and PD.subBtns.camp:GetText()))''',
'''            -- ② 四合一（2026-10-10）：camping 总览页直出对照表（营地页签退役）
            PD.Show("camping")
            PD.SetTab("overview")
            ck("★★ camping 总览直出对照表（bonus 视图举手，对照总表就绪）",
               PD.campView == "bonus" and PD.wantBonusTable == true
               and PD.bonusTable ~= nil and PD.bonusTable.__shown == true,
               tostring(PD.campView) .. "/" .. tostring(PD.wantBonusTable))'''))

chk_patches.append((
'''            PD.Show("alchemy")
            PD.SetTab("camp")
            ck("★ 有营地数据的专业默认联盟视图（2 段、对照总表收起）",
               PD.campView == "a" and PD.hasSecs == true and PD.secCount == 2
               and PD.bonusTable.__shown == false)
            -- ②b 营地页卡片化（2026-09-24 用户定稿「三档合一卡」）：联盟/部落视图两段两卡
            --    （特权段已删：传承内容归 Legacy 页，与营地无关——用户 2026-09-24 定）
            ck("★★ 营地联盟视图套段落卡（物件/坐标 = 2 段，特权段不再出现在营地页）",
               PD.hasSecs == true and PD.secCount == 2, tostring(PD.secCount))
            local _sec1Rows, _campCards = 0, 0
            for _, sp in ipairs(PD.specs or {}) do
              if sp.sec == 1 and sp.kind == "row" then _sec1Rows = _sec1Rows + 1 end
            end
            for _, c in ipairs(PD.secCards or {}) do
              if c.__shown ~= false then _campCards = _campCards + 1 end
            end
            ck("★★ 三档合一卡：第 1 段 3 档行、可见卡数 = 段数",
               _sec1Rows == 3 and _campCards == PD.secCount,
               tostring(_sec1Rows) .. " 行 / " .. tostring(_campCards) .. " 卡")
            local _campZ = 0
            for _, r in ipairs(PD.rows or {}) do
              if r.__shown ~= false and r.__z then _campZ = _campZ + 1 end
            end
            ck("★★ 段落卡页不出斑马纹（与总览同口径）", _campZ == 0, _campZ)
            PD.onTool("h")
            ck("★ 切部落 → 物件视图切换（仍是 2 段段落卡）",
               PD.campView == "h" and PD.hasSecs == true and PD.secCount == 2,
               tostring(PD.campView))
            local _bonusBtn = false
            for _ti = 1, (PD.TOOL_MAX or 0) do
              local _tb = PD.toolBtns and PD.toolBtns[_ti]
              if _tb and _tb.__shown ~= false and _tb:GetText() == "职业加成" then
                _bonusBtn = true
              end
            end
            ck("★★ 「职业加成」钮只在营地系统名下（有物件专业的营地页不放它，2026-09-24 用户定）",
               _bonusBtn == false)
            PD.onTool("a")
            ck("★ 切回联盟 → 段落卡恢复", PD.hasSecs == true and PD.secCount == 2)
            PD.SetTab("overview")
            ck("★ 有营地数据的专业总览不落加成视图（对照页只在「营地」名下）",
               PD.campView ~= "bonus")
            PD.Show("camping")
            PD.SetTab("camp")
            ck("★ 切走再切回来 → 职业加成对照总表还在",
               PD.campView == "bonus" and PD.wantBonusTable == true
               and PD.bonusTable.__shown == true)
            PD.Show("alchemy")''',
'''            PD.Show("alchemy")
            PD.SetTab("overview")
            -- ②b 四合一：总览页段落卡（简介/传承/营地/速览/备注 ≤ SEC_CARD_MAX）
            ck("★★ 有营地数据的专业总览套段落卡（段数 ≥4 且 ≤ 卡池上限）",
               PD.hasSecs == true and PD.secCount >= 4
               and PD.secCount <= (PD.SEC_CARD_MAX or 8)
               and PD.bonusTable.__shown == false, tostring(PD.secCount))
            local _campCards = 0
            for _, c in ipairs(PD.secCards or {}) do
              if c.__shown ~= false then _campCards = _campCards + 1 end
            end
            ck("★★ 可见段落卡数 = 段数", _campCards == PD.secCount,
               tostring(_campCards) .. " 卡 / " .. tostring(PD.secCount) .. " 段")
            local _campZ = 0
            for _, r in ipairs(PD.rows or {}) do
              if r.__shown ~= false and r.__z then _campZ = _campZ + 1 end
            end
            ck("★★ 段落卡页不出斑马纹（与总览同口径）", _campZ == 0, _campZ)
            -- ★★ D1 去重：旧「营地三档」行（技能 N · 物件名）不再出现在总览
            local _dupCamp = 0
            for _, sp in ipairs(PD.specs or {}) do
              if type(sp.text) == "string"
                 and sp.text:find("^技能 %d+ · ", 1) then _dupCamp = _dupCamp + 1 end
            end
            ck("★★ D1 去重生效：总览无旧「营地三档」行", _dupCamp == 0, _dupCamp)
            -- ★★ 联盟/部落坐标同列直出（2 行、阵营字体色互异）
            local _campRows = {}
            for _, sp in ipairs(PD.specs or {}) do
              if type(sp.text) == "string" and sp.text:find("营地 · ", 1, true) then
                _campRows[#_campRows + 1] = sp
              end
            end
            ck("★★ 联盟/部落营地坐标同列（2 行、字体色互异）",
               #_campRows == 2 and _campRows[1].nameColor ~= nil
               and (_campRows[1].nameColor[1] ~= _campRows[2].nameColor[1]
                    or _campRows[1].nameColor[3] ~= _campRows[2].nameColor[3]),
               tostring(#_campRows))
            PD.Show("camping")
            PD.SetTab("overview")
            ck("★ 切走再切回来 → 对照总表还在总览页",
               PD.campView == "bonus" and PD.wantBonusTable == true
               and PD.bonusTable.__shown == true)
            PD.Show("alchemy")'''))

chk_patches.append((
'''              PD.Show("alchemy")
              PD.SetTab("camp")
              -- 上游钓鱼页断言块收尾会把**全局** C_Map = false（坑档案 #8 口径），''',
'''              PD.Show("alchemy")
              PD.SetTab("overview")
              -- 上游钓鱼页断言块收尾会把**全局** C_Map = false（坑档案 #8 口径），'''))

chk_patches.append((
'''              PD.SetTab("recipe")
              PD.SetTab("camp")''',
'''              PD.SetTab("recipe")
              PD.SetTab("overview")'''))

chk_patches.append((
'''            -- ④ 传承（原 Legacy）
            ck("★★ 子页签第 6 颗文案是「传承」",
               PDM.PROF_SUBTABS[6] ~= nil and PDM.PROF_SUBTABS[6].text == "传承",
               PDM.PROF_SUBTABS[6] and PDM.PROF_SUBTABS[6].text)''',
'''            -- ④ 四合一：传承/说明退出页签（内容并入总览合段）
            ck("★★ 子页签第 4 颗是「升级」、第 5/6 颗不存在（营地/传承/说明退役）",
               PDM.PROF_SUBTABS[4] ~= nil and PDM.PROF_SUBTABS[4].key == "leveling"
               and PDM.PROF_SUBTABS[5] == nil and PDM.PROF_SUBTABS[6] == nil,
               PDM.PROF_SUBTABS[5] and PDM.PROF_SUBTABS[5].key or "nil")'''))

apply(CHK, chk_patches)

mut_patches = []

mut_patches.append((
'''MUT_PROF_LEGACY_LABEL = ('Core/ProfessionUI.lua', (
    b'    { key = "legacy",   text = L["\\xe4\\xbc\\xa0\\xe6\\x89\\xbf"] },\\n',
    b'    { key = "legacy",   text = "Legacy" }, -- MUT: english label back\\n'))''',
'''MUT_PROF_TABS_REGROW = ('Core/ProfessionUI.lua', (
    b'    { key = "leveling", text = L["\\xe5\\x8d\\x87\\xe7\\xba\\xa7"] },\\n}\\n',
    b'    { key = "leveling", text = L["\\xe5\\x8d\\x87\\xe7\\xba\\xa7"] },\\n'
    b'    { key = "legacy",   text = "Legacy" }, -- MUT: merged tab regrows\\n}\\n'))'''))

mut_patches.append((
'''MUT_PROF_CAMPING_CAMP_GONE = ('Core/ProfessionUI.lua', (
    b'    if slug == "camping" then out[#out + 1] = "camp" end\\n',
    b'    -- MUT: camping camp tab gone\\n'))''',
'''MUT_PROF_MERGE_GONE = ('Core/ProfessionUI.lua', (
    b'        PushHead(rows, L["\\xe4\\xbc\\xa0\\xe6\\x89\\xbf"], 1)\\n',
    b'        -- MUT: legacy section dropped from overview\\n'))'''))

mut_patches.append((
'''MUT_PROF_CAMPVIEW_STICKY = ('Core/ProfessionUI.lua', (
    b'        PD.campView = "a"\\n',
    b'        -- MUT: camp view sticky across professions\\n'))''',
'''MUT_PROF_CAMP_BONUS_GONE = ('Core/ProfessionUI.lua', (
    b'            PD.campView = "bonus"\\n            PD.wantBonusTable = true\\n',
    b'            -- MUT: camping bonus table raise gone\\n'))'''))

mut_patches.append((
'''MUT_PROF_BONUS_LABEL = ('Core/ProfessionUI.lua', (
    b'                bt:SetText(L["\\xe8\\x81\\x8c\\xe4\\xb8\\x9a\\xe5\\x8a\\xa0\\xe6\\x88\\x90"])\\n',
    b'                bt:SetText(L["\\xe5\\x8a\\xa0\\xe6\\x88\\x90"]) -- MUT: label back\\n'))''',
'''MUT_PROF_DUP_CAMP = ('Core/ProfessionUI.lua', (
    b'                text = c[2] or "?",\\n',
    b'                text = format(L["\\xe6\\x8a\\x80\\xe8\\x83\\xbd %d \\xc2\\xb7 %s"], c[4] or 0, c[2] or "?"), -- MUT: old camp trio row back\\n'))'''))

mut_patches.append((
'''    ('专业页：第 6 颗子页签退回英文 Legacy', MUT_PROF_LEGACY_LABEL),''',
'''    ('专业页：并入总览的页签长回来（PROF_SUBTABS 回 5+ 项）', MUT_PROF_TABS_REGROW),'''))

mut_patches.append((
'''    ('专业页：营地页进不了对照（页签被摘）', MUT_PROF_CAMPING_CAMP_GONE),
    ('专业页：换专业不复位营地视图', MUT_PROF_CAMPVIEW_STICKY),''',
'''    ('专业页：总览传承段被摘（四合一内容丢失）', MUT_PROF_MERGE_GONE),
    ('专业页：camping 对照表举手被砍（总览不出总表）', MUT_PROF_CAMP_BONUS_GONE),'''))

mut_patches.append((
'''    ('专业页：营地第三视图退回单字加成', MUT_PROF_BONUS_LABEL),''',
'''    ('专业页：总览长回旧「营地三档」行（D1 去重失效）', MUT_PROF_DUP_CAMP),'''))

apply(MUT, mut_patches)
print("ALL DONE")
