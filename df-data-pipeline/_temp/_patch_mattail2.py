# -*- coding: utf-8 -*-
"""补丁②：两个 check 脚本（自适应行尾）。"""
# -*- coding: utf-8 -*-

def patch_file(path, pairs):
    data = open(path, 'rb').read()
    crlf = b'\r\n' in data
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

patch_file(r'D:\workspace\DungeonsForever\_temp\df_dungeon_check.py', [
    ('harness 正向断言',
     """       and '{ text = "  …" }' not in profui and '{ text = "…" }' in profui
       and 'c:SetText("")' in profui)
""",
     """       and '{ text = "  …" }' not in profui and '{ text = "…" }' in profui
       and 'c:SetText("")' in profui)
    ck('★★ 材料末段「图标+截断名」不整段丢弃（2026-10-10 截图红框：右缘留白）',
       'local avail = budget - w - gap - px' in profui
       and 'local piece2 = PD.MatIconTex(m[1], px) .. PD.Fit(name, fs, avail)' in profui
       and 'segs[#segs + 1] = { id = m[1], cnt = m[2] or 1, text = piece2 }' in profui
       and 'PD.MAT_TAIL_MIN' in profui)
"""),
])

patch_file(r'D:\workspace\DungeonsForever\_temp\df_mut_check.py', [
    ('变异定义',
     """MUT_PROF_MATCNT_GONE = ('Core/ProfessionUI.lua', (
    b'        segs[#segs + 1] = { id = m[1], cnt = m[2] or 1, text = piece }\\n',
    b'        segs[#segs + 1] = { id = m[1], text = piece } -- MUT: count badge data gone\\n'))
""",
     """MUT_PROF_MATCNT_GONE = ('Core/ProfessionUI.lua', (
    b'        segs[#segs + 1] = { id = m[1], cnt = m[2] or 1, text = piece }\\n',
    b'        segs[#segs + 1] = { id = m[1], text = piece } -- MUT: count badge data gone\\n'))

MUT_PROF_MATTAIL_GONE = ('Core/ProfessionUI.lua', (
    '                local piece2 = PD.MatIconTex(m[1], px) .. PD.Fit(name, fs, avail)\\n'.encode('utf-8'),
    '                local piece2 = PD.MatIconTex(m[1], px) .. name -- MUT: tail refit gone\\n'.encode('utf-8')))
"""),
    ('变异注册',
     "    ('专业页：材料数量徽标回潮（N×前缀复活）', MUT_PROF_MATCNT_GONE),\n",
     "    ('专业页：材料数量徽标回潮（N×前缀复活）', MUT_PROF_MATCNT_GONE),\n"
     "    ('专业页：材料末段整段丢弃回潮（右缘留白）', MUT_PROF_MATTAIL_GONE),\n"),
])

print('ALL PATCHED')
