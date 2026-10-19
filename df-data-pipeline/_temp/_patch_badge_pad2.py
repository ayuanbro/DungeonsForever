# -*- coding: utf-8 -*-
"""mut check 补丁（r-string 版，避免转义歧义）：NEW_TAG/NAME_FIT 重锚 + 两条新变异 + 注册。"""

def patch_file(path, pairs):
    data = open(path, 'rb').read()
    for label, old, new in pairs:
        o = old.encode('utf-8')
        n = new.encode('utf-8')
        c = data.count(o)
        assert c == 1, '%s: anchor count=%d' % (label, c)
        data = data.replace(o, n)
        print('ok  %s' % label)
    open(path, 'wb').write(data)

P = r'D:\workspace\DungeonsForever\_temp\df_mut_check.py'

old_new_tag = r"""MUT_PROF_NEW_TAG_GONE = ('Core/ProfessionUI.lua', (
    b'    r.a:SetText((spec.text or "") .. (spec.is_new and L[" |cff40d940\xe6\x96\xb0|r"] or ""))\n',
    b'    r.a:SetText(spec.text or "") -- MUT: NEW tag dropped\n'))"""

new_new_tag = r"""MUT_PROF_NEW_TAG_GONE = ('Core/ProfessionUI.lua', (
    '    r.b:SetText((spec.is_new and L[" |cff40d940新|r"] .. " " or "") .. (spec.sub or ""))\n'.encode('utf-8'),
    '    r.b:SetText(spec.sub or "") -- MUT: NEW tag dropped\n'.encode('utf-8')))"""

old_fit = r"""MUT_PROF_NAME_FIT_GONE = ('Core/ProfessionUI.lua', (
    '            s.text = PD.Fit(s.text, 13, PD.MAT_X - 8 - PD.RECIPE_PADL - (s.is_new and PD.RECIPE_BADGE_W or 0))\n'.encode('utf-8'),
    '            s.text = PD.Fit(s.text, 13, nameW - (s.is_new and PD.RECIPE_BADGE_W or 0)) -- MUT: truncate despite gap\n'.encode('utf-8')))"""

new_fit = r"""MUT_PROF_NAME_FIT_GONE = ('Core/ProfessionUI.lua', (
    '            s.text = PD.Fit(s.text, 13, math.max(PD.MAT_X - 8 - PD.RECIPE_PADL,\n                                                 (PD.RECIPE_NAME_W or 0) - 6))\n'.encode('utf-8'),
    '            s.text = PD.Fit(s.text, 13, nameW - (s.is_new and PD.RECIPE_BADGE_W or 0)) -- MUT: truncate despite gap\n'.encode('utf-8')))"""

old_shield = r"""MUT_PROF_PICKSHIELD_GONE = ('Core/ProfessionUI.lua', ("""

new_shield = r"""MUT_PROF_PAD_REGROWN = ('Core/ProfessionUI.lua', (
    'PD.RECIPE_NAME_PAD = 16'.encode('utf-8'),
    'PD.RECIPE_NAME_PAD = 44 -- MUT: column gap regrown'.encode('utf-8')))

MUT_PROF_SUBSCAN_GONE = ('Core/ProfessionUI.lua', (
    'local sw = PD.TextW(s.sub or "", 11) + (s.is_new and PD.RECIPE_BADGE_W or 0)'.encode('utf-8'),
    'local sw = PD.TextW(s.sub or "", 11) -- MUT: badge width dropped from sub scan'.encode('utf-8')))

MUT_PROF_PICKSHIELD_GONE = ('Core/ProfessionUI.lua', ("""

old_reg = """    ('专业页：弹窗点关盾断开（点别处不收窗）', MUT_PROF_PICKSHIELD_GONE),
"""
new_reg = """    ('专业页：弹窗点关盾断开（点别处不收窗）', MUT_PROF_PICKSHIELD_GONE),
    ('专业页：名称列间距回潮 44', MUT_PROF_PAD_REGROWN),
    ('专业页：副行扫描丢角标宽', MUT_PROF_SUBSCAN_GONE),
"""

patch_file(P, [
    ('NEW_TAG 重锚', old_new_tag, new_new_tag),
    ('NAME_FIT 重锚', old_fit, new_fit),
    ('新增 PAD/SUBSCAN 变异', old_shield, new_shield),
    ('注册', old_reg, new_reg),
])
print('ALL PATCHED')
