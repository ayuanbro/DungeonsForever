# -*- coding: utf-8 -*-
"""材料末段「图标+截断名」补丁（2026-10-10 截图红框：整段丢弃 = 材料列右缘留白）。
锚定替换 + 唯一性 assert，二进制读写保 CRLF。"""
import sys

def to_crlf(b):
    return b.replace(b'\n', b'\r\n')

def patch_file(path, pairs):
    data = open(path, 'rb').read()
    for label, old, new in pairs:
        o, n = to_crlf(old.encode('utf-8')), to_crlf(new.encode('utf-8'))
        c = data.count(o)
        assert c == 1, '%s: anchor count=%d' % (label, c)
        data = data.replace(o, n)
        print('ok  %s' % label)
    open(path, 'wb').write(data)

# ── ① Core/ProfessionUI.lua ──────────────────────────────────────────
patch_file(r'D:\workspace\DungeonsForever\Core\ProfessionUI.lua', [
    ('常量 MAT_TAIL_MIN',
     "PD.MAT_RIGHT_RESERVE = 132\n",
     "PD.MAT_RIGHT_RESERVE = 132\n"
     "PD.MAT_TAIL_MIN = 14       -- 末段「图标+截断名」至少再留给名称的宽（< 此值才退回纯 … 段）\n"),

    ('MatCol 头注释同步',
     "--   省略号那一段没有物品 id（不给热区）。\n",
     "--   纯 … 段没有物品 id（不给热区）；末段「图标+截断名」仍带 id 出热区（2026-10-10）。\n"),

    ('MatCol 末段不再整段丢弃',
     '''        if n > 0 and w + gap + cw > budget then
            out[#out + 1] = "…"
            segs[#segs + 1] = { text = "…" }
            break
        end
''',
     '''        if n > 0 and w + gap + cw > budget then
            -- 2026-10-10 用户（截图红框）：末段整段丢弃 = 材料列右缘留一截白 ——
            --   改画「图标 + 名称按剩余宽截断」（PD.Fit 自带 …，热区/徽标照挂）；
            --   只剩连图标都放不下的零头才退回纯 … 段（无 id 不给热区）。
            local avail = budget - w - gap - px
            if avail >= PD.MAT_TAIL_MIN then
                local piece2 = PD.MatIconTex(m[1], px) .. PD.Fit(name, fs, avail)
                out[#out + 1] = piece2
                segs[#segs + 1] = { id = m[1], cnt = m[2] or 1, text = piece2 }
            else
                out[#out + 1] = "…"
                segs[#segs + 1] = { text = "…" }
            end
            break
        end
'''),
])

# ── ② _temp/df_dungeon_check.py：正向断言 ────────────────────────────
patch_file(r'D:\workspace\DungeonsForever\_temp\df_dungeon_check.py', [
    ('harness 正向断言',
     '''       and '{ text = "  …" }' not in profui and '{ text = "…" }' in profui
       and 'c:SetText("")' in profui)
''',
     '''       and '{ text = "  …" }' not in profui and '{ text = "…" }' in profui
       and 'c:SetText("")' in profui)
    ck('★★ 材料末段「图标+截断名」不整段丢弃（2026-10-10 截图红框：右缘留白）',
       'local avail = budget - w - gap - px' in profui
       and 'local piece2 = PD.MatIconTex(m[1], px) .. PD.Fit(name, fs, avail)' in profui
       and 'segs[#segs + 1] = { id = m[1], cnt = m[2] or 1, text = piece2 }' in profui
       and 'PD.MAT_TAIL_MIN' in profui)
'''),
])

# ── ③ _temp/df_mut_check.py：变异 + 注册 ─────────────────────────────
patch_file(r'D:\workspace\DungeonsForever\_temp\df_mut_check.py', [
    ('变异定义',
     '''MUT_PROF_MATCNT_GONE = ('Core/ProfessionUI.lua', (
    b'        segs[#segs + 1] = { id = m[1], cnt = m[2] or 1, text = piece }\\n',
    b'        segs[#segs + 1] = { id = m[1], text = piece } -- MUT: count badge data gone\\n'))
''',
     '''MUT_PROF_MATCNT_GONE = ('Core/ProfessionUI.lua', (
    b'        segs[#segs + 1] = { id = m[1], cnt = m[2] or 1, text = piece }\\n',
    b'        segs[#segs + 1] = { id = m[1], text = piece } -- MUT: count badge data gone\\n'))

MUT_PROF_MATTAIL_GONE = ('Core/ProfessionUI.lua', (
    '                local piece2 = PD.MatIconTex(m[1], px) .. PD.Fit(name, fs, avail)\\n'.encode('utf-8'),
    '                local piece2 = PD.MatIconTex(m[1], px) .. name -- MUT: tail refit gone\\n'.encode('utf-8')))
'''),

    ('变异注册',
     "    ('专业页：材料数量徽标回潮（N×前缀复活）', MUT_PROF_MATCNT_GONE),\n",
     "    ('专业页：材料数量徽标回潮（N×前缀复活）', MUT_PROF_MATCNT_GONE),\n"
     "    ('专业页：材料末段整段丢弃回潮（右缘留白）', MUT_PROF_MATTAIL_GONE),\n"),
])

print('ALL PATCHED')
