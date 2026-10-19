# -*- coding: utf-8 -*-
"""配方页二轮补丁：①名称↔材料列间距 44→16；②「新」角标迁副行（类型左边）。"""

def patch_file(path, pairs, force_crlf=None):
    data = open(path, 'rb').read()
    crlf = (b'\r\n' in data) if force_crlf is None else force_crlf
    def conv(s):
        b = s.encode('utf-8')
        return b.replace(b'\n', b'\r\n') if crlf else b
    for label, old, new in pairs:
        o, n = conv(old), conv(new)
        c = data.count(o)
        assert c == 1, '%s: anchor count=%d (crlf=%s)' % (label, c, crlf)
        data = data.replace(o, n)
        print('ok  %s (crlf=%s)' % (label, crlf))
    open(path, 'wb').write(data)

# ── ① Core/ProfessionUI.lua（CRLF）────────────────────────────────────
patch_file(r'D:\workspace\DungeonsForever\Core\ProfessionUI.lua', [
    ('常量 PAD 44→16 + 角标注释',
     '''PD.RECIPE_NAME_PAD = 44     -- 名称列右界→材料列起点（= 名称起点 32 的回让 + 12 列间距）
PD.RECIPE_BADGE_W = 26      -- 「新」角标占宽（实画 " 新" ≈ 20；旧 34 虚胖会把新行名称白白截短）
''',
     '''PD.RECIPE_NAME_PAD = 16     -- 名称列右界→材料列起点（2026-10-10 二轮 44→16：角标迁副行、32 回让作废；16 = 保住 6 字截断档的最低间距）
PD.RECIPE_BADGE_W = 26      -- 「新」角标占宽（副行「 新 」≈ 26；随副行参与列宽扫描，不再压名称行）
'''),

    ('角标迁副行（渲染处）',
     '''    r.a:SetText((spec.text or "") .. (spec.is_new and L[" |cff40d940新|r"] or ""))
    r.b:SetText(spec.sub or "")
''',
     '''    r.a:SetText(spec.text or "")
    -- 2026-10-10 用户：「新」角标从名称行尾移到副行（类型左边）；行尾版退役
    r.b:SetText((spec.is_new and L[" |cff40d940新|r"] .. " " or "") .. (spec.sub or ""))
'''),

    ('FitRecipeCols 自扫：角标宽归副行',
     '''            local w = PD.TextW(s.text or "", 13)
            if s.is_new then w = w + PD.RECIPE_BADGE_W end
            local sw = PD.TextW(s.sub or "", 11)
            if sw > w then w = sw end
''',
     '''            local w = PD.TextW(s.text or "", 13)
            -- 2026-10-10 用户：角标迁副行 ⇒ 角标宽记到副行一侧（名称行不再背 26px）
            local sw = PD.TextW(s.sub or "", 11) + (s.is_new and PD.RECIPE_BADGE_W or 0)
            if sw > w then w = sw end
'''),

    ('ScanRecipe 轻扫：角标宽归副行',
     '''                    local nm = PD.ItemName(r[2])
                    local w = (nm and nm ~= "" and PD.TextW(nm, 13)) or 0
                    if r[11] then w = w + PD.RECIPE_BADGE_W end
                    local sw = PD.TextW(tostring(r[5] or ""), 11)
                    if sw > w then w = sw end
''',
     '''                    local nm = PD.ItemName(r[2])
                    local w = (nm and nm ~= "" and PD.TextW(nm, 13)) or 0
                    -- 2026-10-10 用户：角标迁副行 ⇒ 角标宽记到副行一侧（与 FitRecipeCols 同口径）
                    local sw = PD.TextW(tostring(r[5] or ""), 11) + (r[11] and PD.RECIPE_BADGE_W or 0)
                    if sw > w then w = sw end
'''),

    ('名称截断预算双口径',
     '''        -- 2026-10-10 用户：名称截断按**真实可用宽**（MAT_X-8 右界反推），不按 nameW ——
        --   否则 nameW(≤115) 再扣角标 ⇒ 右边留着 44 间距、名字却被截成 …（截图实锤）
        if s.text and s.text ~= "" then
            s.text = PD.Fit(s.text, 13, PD.MAT_X - 8 - PD.RECIPE_PADL - (s.is_new and PD.RECIPE_BADGE_W or 0))
        end
''',
     '''        -- 2026-10-10 用户（二轮）：PAD 44→16 后预算改双口径 —— 通常随列宽（MAT_X-8-32）；
        --   名称列被 MIN/MAX 钳住的页退回 nameW-6，短名页不因压缩新增截断。
        --   角标已迁副行 ⇒ 不再扣 BADGE_W（实机字宽 ≈ 估宽 0.85，留有余量不压材料列）。
        if s.text and s.text ~= "" then
            s.text = PD.Fit(s.text, 13, math.max(PD.MAT_X - 8 - PD.RECIPE_PADL,
                                                 (PD.RECIPE_NAME_W or 0) - 6))
        end
'''),
], force_crlf=True)

# ── ② _temp/df_dungeon_check.py ───────────────────────────────────────
patch_file(r'D:\workspace\DungeonsForever\_temp\df_dungeon_check.py', [
    ('新字断言改副行 + 间距压缩断言',
     """    ck('★★ 新配方在名称右边补绿色「新」字（左缘竖条之外再加字）',
       '|cff40d940新|r' in profui and 'spec.is_new and L[\" |cff40d940新|r\"]' in profui)
""",
     """    ck('★★ 新配方副行「类型」左边带绿色「新」字（2026-10-10 用户：从名称行尾移来）',
       '|cff40d940新|r' in profui
       and 'spec.is_new and L[\" |cff40d940新|r\"] .. \" \"' in profui
       and '(spec.text or \"\") .. (spec.is_new and L[\" |cff40d940新|r\"] or \"\")' not in profui)
    ck('★★ 名称↔材料列间距压缩：PAD 44→16 + 角标迁副行（名称/副行扫描各归各）',
       'PD.RECIPE_NAME_PAD = 16' in profui
       and 'local sw = PD.TextW(s.sub or \"\", 11) + (s.is_new and PD.RECIPE_BADGE_W or 0)' in profui
       and 'local sw = PD.TextW(tostring(r[5] or \"\"), 11) + (r[11] and PD.RECIPE_BADGE_W or 0)' in profui
       and 'if s.is_new then w = w + PD.RECIPE_BADGE_W end' not in profui
       and 'if r[11] then w = w + PD.RECIPE_BADGE_W end' not in profui)
"""),
    ('截断预算断言改双口径',
     """    ck('★ 名称截断按真实可用宽（MAT_X-8-名称起点 反推；按 nameW 截会「右留间距、左出 …」）',
       'PD.RECIPE_PADL = 32' in profui
       and 'PD.Fit(s.text, 13, PD.MAT_X - 8 - PD.RECIPE_PADL' in profui
       and 'nameW - (s.is_new and PD.RECIPE_BADGE_W or 0)' not in profui)
""",
     """    ck('★ 名称截断预算双口径（随列宽 MAT_X-8-32；列宽被钳住的短名页退回 nameW-6 防新增截断）',
       'PD.RECIPE_PADL = 32' in profui
       and 'PD.Fit(s.text, 13, math.max(PD.MAT_X - 8 - PD.RECIPE_PADL,' in profui
       and '(PD.RECIPE_NAME_W or 0) - 6))' in profui
       and 'nameW - (s.is_new and PD.RECIPE_BADGE_W or 0)' not in profui)
"""),
])

# ── ③ _temp/df_mut_check.py ───────────────────────────────────────────
patch_file(r'D:\workspace\DungeonsForever\_temp\df_mut_check.py', [
    ('NEW_TAG 变异重锚到副行',
     """MUT_PROF_NEW_TAG_GONE = ('Core/ProfessionUI.lua', (
    b'    r.a:SetText((spec.text or "") .. (spec.is_new and L[" |cff40d940\\xe6\\x96\\xb0|r"] or "")\\n',
    b'    r.a:SetText(spec.text or "") -- MUT: NEW tag dropped\\n'))
""",
     """MUT_PROF_NEW_TAG_GONE = ('Core/ProfessionUI.lua', (
    '    r.b:SetText((spec.is_new and L[" |cff40d940新|r"] .. " " or "") .. (spec.sub or ""))\\n'.encode('utf-8'),
    '    r.b:SetText(spec.sub or "") -- MUT: NEW tag dropped\\n'.encode('utf-8')))
"""),
    ('NAME_FIT 变异重锚到双口径',
     """MUT_PROF_NAME_FIT_GONE = ('Core/ProfessionUI.lua', (
    '            s.text = PD.Fit(s.text, 13, PD.MAT_X - 8 - PD.RECIPE_PADL - (s.is_new and PD.RECIPE_BADGE_W or 0))\\n'.encode('utf-8'),
    '            s.text = PD.Fit(s.text, 13, nameW - (s.is_new and PD.RECIPE_BADGE_W or 0)) -- MUT: truncate despite gap\\n'.encode('utf-8')))
""",
     """MUT_PROF_NAME_FIT_GONE = ('Core/ProfessionUI.lua', (
    '            s.text = PD.Fit(s.text, 13, math.max(PD.MAT_X - 8 - PD.RECIPE_PADL,\\n                                                 (PD.RECIPE_NAME_W or 0) - 6))\\n'.encode('utf-8'),
    '            s.text = PD.Fit(s.text, 13, nameW - (s.is_new and PD.RECIPE_BADGE_W or 0)) -- MUT: truncate despite gap\\n'.encode('utf-8')))
"""),
    ('新增 PAD 回潮变异',
     """MUT_PROF_PICKSHIELD_GONE = ('Core/ProfessionUI.lua', (
""",
     """MUT_PROF_PAD_REGROWN = ('Core/ProfessionUI.lua', (
    'PD.RECIPE_NAME_PAD = 16'.encode('utf-8'),
    'PD.RECIPE_NAME_PAD = 44 -- MUT: column gap regrown'.encode('utf-8')))

MUT_PROF_SUBSCAN_GONE = ('Core/ProfessionUI.lua', (
    'local sw = PD.TextW(s.sub or "", 11) + (s.is_new and PD.RECIPE_BADGE_W or 0)'.encode('utf-8'),
    'local sw = PD.TextW(s.sub or "", 11) -- MUT: badge width dropped from sub scan'.encode('utf-8')))

MUT_PROF_PICKSHIELD_GONE = ('Core/ProfessionUI.lua', (
"""),
    ('注册两条新变异',
     "    ('专业页：弹窗点关盾断开（点别处不收窗）', MUT_PROF_PICKSHIELD_GONE),\n",
     "    ('专业页：弹窗点关盾断开（点别处不收窗）', MUT_PROF_PICKSHIELD_GONE),\n"
     "    ('专业页：名称列间距回潮 44', MUT_PROF_PAD_REGROWN),\n"
     "    ('专业页：副行扫描丢角标宽', MUT_PROF_SUBSCAN_GONE),\n"),
])

print('ALL PATCHED')
