# -*- coding: utf-8 -*-
"""弹窗「点关盾」补丁：点别处/滚轮自动收窗（2026-10-10 用户）。"""

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
    ('头注释补盾说明',
     "--   父 = PD.page（不进滚动子帧：滚轮 / 换页 / 收窗统一 Hide 兜位）；\n",
     "--   父 = PD.page（不进滚动子帧：滚轮 / 换页 / 收窗统一 Hide 兜位）；\n"
     "--   点关盾 = 弹窗开着时全页挡一层（层级钉弹窗下 1），点它收窗 / 滚轮收窗+滚页（2026-10-10 用户）；\n"),

    ('懒建块加盾',
     '''        pick = CreateFrame("Button", nil, PD.page, "BackdropTemplate")
        pick:EnableMouse(true)
        pick:SetFrameLevel(515)
''',
     '''        pick = CreateFrame("Button", nil, PD.page, "BackdropTemplate")
        pick:EnableMouse(true)
        pick:SetFrameLevel(515)
        -- 点关盾（2026-10-10 用户：点别处 / 滚轮自动收窗）：弹窗开着时全页挡一层，
        --   点它 = 收窗；滚轮 = 收窗 + 照常滚页。层级在 Show 时钉到弹窗正下方
        --   （forever 引擎同层次序不可靠 ⇒ 显式 SetFrameLevel，不赌创建次序）。
        --   收窗时随弹窗一起 Hide ⇒ 平时不挡任何交互（行热区/页签照常）。
        local shield = CreateFrame("Frame", nil, PD.page)
        shield:EnableMouse(true)
        shield:EnableMouseWheel(true)
        shield:SetAllPoints(PD.page)
        shield:SetScript("OnMouseDown", function() PD.HideVendorPick() end)
        shield:SetScript("OnMouseWheel", function(self, delta)
            PD.HideVendorPick()
            DG.WheelScroll(PD.scroll, PD.child, delta)
        end)
        pick.__shield = shield
'''),

    ('HideVendorPick 连盾收',
     '''function PD.HideVendorPick()
    if PD.vendorPick and PD.vendorPick:IsShown() then
        PD.vendorPick:Hide()
    end
end
''',
     '''function PD.HideVendorPick()
    local pick = PD.vendorPick
    if not pick then return end
    if pick:IsShown() then pick:Hide() end
    if pick.__shield then pick.__shield:Hide() end
end
'''),

    ('Show 时亮盾并钉层级',
     '''    pick:ClearAllPoints()
    pick:SetPoint("TOPRIGHT", zone, "BOTTOMRIGHT", 0, -4)
    pick:Show()
end
''',
     '''    pick:ClearAllPoints()
    pick:SetPoint("TOPRIGHT", zone, "BOTTOMRIGHT", 0, -4)
    if pick.__shield then
        pick.__shield:SetFrameLevel(pick:GetFrameLevel() - 1)
        pick.__shield:Show()
    end
    pick:Show()
end
'''),
], force_crlf=True)

# ── ② _temp/df_dungeon_check.py ───────────────────────────────────────
patch_file(r'D:\workspace\DungeonsForever\_temp\df_dungeon_check.py', [
    ('harness 点关盾断言',
     """       # 反例：材料列不许退回「只画一整串」（那样就没有分段热区可挂）
       and '    if not spec.matSegs then r.f:SetText(spec.mats or "") end\\n' in profui)
""",
     """       # 反例：材料列不许退回「只画一整串」（那样就没有分段热区可挂）
       and '    if not spec.matSegs then r.f:SetText(spec.mats or "") end\\n' in profui)
    ck('★★ 商人弹窗点关盾：点别处收窗 + 滚轮收窗照常滚页（2026-10-10 用户）',
       'pick.__shield = shield' in profui
       and 'shield:SetScript("OnMouseDown", function() PD.HideVendorPick() end)' in profui
       and 'shield:EnableMouseWheel(true)' in profui
       and 'pick.__shield:Hide()' in profui
       and 'pick.__shield:SetFrameLevel(pick:GetFrameLevel() - 1)' in profui)
"""),
])

# ── ③ _temp/df_mut_check.py ───────────────────────────────────────────
patch_file(r'D:\workspace\DungeonsForever\_temp\df_mut_check.py', [
    ('变异定义',
     """MUT_PROF_MATTAIL_GONE = ('Core/ProfessionUI.lua', (
""",
     """MUT_PROF_PICKSHIELD_GONE = ('Core/ProfessionUI.lua', (
    '        shield:SetScript("OnMouseDown", function() PD.HideVendorPick() end)\\n'.encode('utf-8'),
    '        shield:SetScript("OnMouseDown", nil) -- MUT: click-away close gone\\n'.encode('utf-8')))

MUT_PROF_MATTAIL_GONE = ('Core/ProfessionUI.lua', (
"""),
    ('变异注册',
     "    ('专业页：材料末段整段丢弃回潮（右缘留白）', MUT_PROF_MATTAIL_GONE),\n",
     "    ('专业页：材料末段整段丢弃回潮（右缘留白）', MUT_PROF_MATTAIL_GONE),\n"
     "    ('专业页：弹窗点关盾断开（点别处不收窗）', MUT_PROF_PICKSHIELD_GONE),\n"),
])

print('ALL PATCHED')
