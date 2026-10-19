# -*- coding: utf-8 -*-
"""2026-10-09 配方页提示框改版 —— 收尾补丁（断言重锚 + 新断言 + 变异）。

一、harness（df_dungeon_check.py / mk_df_check.py）
    ① 我先前加的那条断言里引用了 WireTipZone 的旧 OnEnter 形态 → 改成新的 elseif 形态；
    ② 两条断言引用了被我改掉的 MatCol 调用行 → 重锚（`mats = mcol,` / `s.mats, sg = ...`）；
    ③ 新增「★★ 配方页：材料分段热区 + 商人半段热区」一条。

二、_temp/df_mut_check.py
    ① 修一条被我改断的旧变异锚点（MUT_PROF_MATCOL_BACK）；
    ② 新增 ㊿ 一节 7 条变异（材料热区/分段链/对齐/商人拆分/提示/落图/收起）。

三、_temp/mk_df_mut.py：同步修那条旧锚点（生成器该处文本，1 行）。
四、_temp/df_check_new_muts.py：DEFAULT_WANT 登记 7 条新变异。

全部按 EOL 保真读写；每条锚点断言「恰好命中 1 次」；幂等短路。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load(fn):
    p = os.path.join(HERE, fn)
    raw = open(p, 'rb').read()
    return p, raw, raw.decode('utf-8')


def save(p, raw):
    open(p, 'wb').write(raw)
    print('     落盘 %-24s %7d 字节（裸 LF=%d 裸 CR=%d）'
          % (os.path.basename(p), len(raw),
             raw.count(b'\n') - raw.count(b'\r\n'), raw.count(b'\r') - raw.count(b'\r\n')))


def sub_once(txt, old, new, tag):
    n = txt.count(old)
    if n != 1:
        sys.exit('[FAIL] %s：锚点命中 %d 次（应恰好 1）\n--- 锚点 ---\n%r' % (tag, n, old))
    return txt.replace(old, new, 1)


# ══════════════════════════════════════════════════════════════════════════
# 一、harness
# ══════════════════════════════════════════════════════════════════════════
OLD_TIPLINE = r"""       and '        if self.__it and DG.ShowItemTip then DG.ShowItemTip(self, self.__it) end\n' in profui
"""
NEW_TIPLINE = r"""       and '        elseif self.__it and DG.ShowItemTip then\n' in profui
       and '            DG.ShowItemTip(self, self.__it)\n' in profui
"""

OLD_MATS_ANCHOR = r"""       'sub = tostring(r[5] or "")' in profui and 'mats = PD.MatCol(r[12], PD.MAT_FS, PD.MAT_W)' in profui)
"""
NEW_MATS_ANCHOR = r"""       'sub = tostring(r[5] or "")' in profui and 'mats = mcol,\n' in profui
       and 'local mcol, _, _, msegs = PD.MatCol(r[12], PD.MAT_FS, PD.MAT_W)' in profui)
"""

OLD_FITCOLS = r"""       and 's.mats = PD.MatCol(s._mats, PD.MAT_FS, PD.MAT_W)' in profui
"""
NEW_FITCOLS = r"""       and 's.mats, sg = PD.MatCol(s._mats, PD.MAT_FS, PD.MAT_W)' in profui
"""

OLD_TAIL = "       and '                lines = tip,\\n' not in profui)\n"

NEW_RECIPE_CK = """       and '                lines = tip,\\n' not in profui)
    # ★★ 七轮（2026-10-09）：配方页的「材料列 / 右下角商人」也做成热区。用户原话：
    #   「配方页面现在也这样修改 如果鼠标在材料上面，就显示材料的鼠标提示框
    #     如果鼠标在商人上面，就显示点击定位在地图上标记商人位置」。
    #   ① 材料列改**锚点分段链**（第 1 段沿用 r.f、第 2 段起 r.mn[i]）：位置交给引擎算 ——
    #      ns.hui.TextW 是**估算器**（图标按 fs + 2、空格走步进表），拿它摆热区必然漂；
    #      段间那两格空格跟着后一段走 ⇒ 与旧的 table.concat(out, "  ") 逐像素一致。
    #   ② 每段配一格热区 r.mz[i]（PD.MatZone → PD.WireTipZone）挂 { 该材料 itemID }；
    #      热区尺寸靠「锚到字串的 TOPLEFT / BOTTOMRIGHT」取得，全程零量宽。
    #   ③ 右下角那格用 PD.SourceParts 把**恒居末位**的「商人：X」拆到 r.dv（r.d 只留前缀，
    #      两半锚点链相接），热区只盖 r.dv；悬停出 PD.VendorLines（商人明细 +
    #      「点击：在地图上标记该 NPC」），点击落图。
    #   ④ PD.WireTipZone 扩两个通道：__tipLines（文字提示框）/ __act（自定义点击）。
    #   ⑤ 行池跨页复用：ClearMatSegs 必须把分段字串与热区一起收干净（透明热区吞鼠标）。
    ck('★★ 配方页：材料分段热区（悬停出该材料的物品提示框）+ 商人半段热区（点击定位落图）',
       'function PD.MatCol' in profui
       and 'return table.concat(out, "  "), w, n, segs\\n' in profui
       and 'function PD.SourceParts(s)' in profui
       and 'out[#out + 1] = { text = format(L["商人：%s"], (v and v.name) or "?"), vendor = true }\\n' in profui
       and 'function PD.MatSeg(r, i)' in profui
       and 'function PD.MatZone(r, i)' in profui
       and 'function PD.PaintMatSegs(r, segs, color)' in profui
       and 'function PD.ClearMatSegs(r)' in profui
       # 热区尺寸靠区域互锚（不让估算器参与摆热区）
       and '            z:SetPoint("TOPLEFT", fs, "TOPLEFT", 0, 1)\\n' in profui
       and '            z:SetPoint("BOTTOMRIGHT", fs, "BOTTOMRIGHT", 0, -1)\\n' in profui
       and '        if spec.matSegs then PD.PaintMatSegs(r, spec.matSegs, spec.matColor) end\\n' in profui
       and '    r.mz = {}\\n' in profui
       and '    r.dv = MakeFS(r, 11, C_GREY, "RIGHT")\\n' in profui
       and '    if spec.dval and h > PD.ROW_H1 then\\n' in profui
       and '        r.d:SetPoint("RIGHT", r.dv, "LEFT", 0, 0)\\n' in profui
       and '        vz.__tipLines = PD.VendorLines(spec.src)\\n' in profui
       and '        vz.__act = PD.VendorAct(spec.src)\\n' in profui
       and '    PD.ClearMatSegs(r)\\n' in profui
       # 反例：材料列不许退回「只画一整串」（那样就没有分段热区可挂）
       and '    if not spec.matSegs then r.f:SetText(spec.mats or "") end\\n' in profui)
"""


def patch_harness(fn):
    p, raw, txt = load(fn)
    if '配方页：材料分段热区' in txt:
        print('[SKIP] %s：已含七轮断言' % fn)
        return
    txt = sub_once(txt, OLD_TIPLINE, NEW_TIPLINE, fn + ' :: tip-line')
    txt = sub_once(txt, OLD_MATS_ANCHOR, NEW_MATS_ANCHOR, fn + ' :: mats-anchor')
    txt = sub_once(txt, OLD_FITCOLS, NEW_FITCOLS, fn + ' :: fitcols')
    txt = sub_once(txt, OLD_TAIL, NEW_RECIPE_CK, fn + ' :: 七轮断言')
    assert txt.count('配方页：材料分段热区') == 1
    save(p, txt.encode('utf-8'))


# ══════════════════════════════════════════════════════════════════════════
# 二、df_mut_check.py：修旧锚点 + 新增 ㊿ 一节
# ══════════════════════════════════════════════════════════════════════════
OLD_MUT_OLD = r"""    b'        sub = tostring(r[5] or ""),\n        mats = PD.MatCol(r[12], PD.MAT_FS, PD.MAT_W),\n',
"""
NEW_MUT_OLD = r"""    b'        sub = tostring(r[5] or ""),\n        mats = mcol,\n        matSegs = msegs,\n',
"""
OLD_MUT_NEW = r"""    b'        sub = table.concat({ tostring(r[5] or ""), PD.MatText(r[12], 4) }, "   "), -- MUT: mats back into sub\n        mats = "",\n'))
"""
NEW_MUT_NEW = r"""    b'        sub = table.concat({ tostring(r[5] or ""), PD.MatText(r[12], 4) }, "   "), -- MUT: mats back into sub\n        mats = "",\n        matSegs = nil,\n'))
"""

RECIPE_DEFS = r"""# 2026-10-09 配方页提示框改版（用户）：「配方页面现在也这样修改 如果鼠标在材料上面，
#   就显示材料的鼠标提示框 如果鼠标在商人上面，就显示点击定位在地图上标记商人位置」）。
#   守护点：① 材料列必须是分段链（退回只画一整串 = 没有分段热区可挂）；
#   ② 材料热区必须挂该材料 itemID；③ 热区必须锚到字串（量宽会漂）；
#   ④ 商人半段必须拆到 r.dv；⑤ 商人热区要出提示框（含「点击：在地图上标记该 NPC」）
#   且点击落图；⑥ 行池跨页复用必须收起分段热区。
MUT_RECIPE_MATCHAIN_GONE = ('Core/ProfessionUI.lua', (
    b'        if spec.matSegs then PD.PaintMatSegs(r, spec.matSegs, spec.matColor) end\n',
    b'        do end -- MUT: material chain dropped (no per-material hotspot)\n'))
MUT_RECIPE_MATZONE_NOIT = ('Core/ProfessionUI.lua', (
    b'            z.__it = { segs[i].id }\n',
    b'            z.__it = nil -- MUT: material tooltip never fires\n'))
MUT_RECIPE_ZONE_ANCHOR_GONE = ('Core/ProfessionUI.lua', (
    b'            z:SetPoint("TOPLEFT", fs, "TOPLEFT", 0, 1)\n'
    b'            z:SetPoint("BOTTOMRIGHT", fs, "BOTTOMRIGHT", 0, -1)\n',
    b'            z:SetSize(20, 20) -- MUT: hotspot not aligned to the text run\n'))
MUT_RECIPE_VENDOR_SPLIT_GONE = ('Core/ProfessionUI.lua', (
    b'    if spec.dval and h > PD.ROW_H1 then\n',
    b'    if false then -- MUT: vendor half not split (no merchant hotspot)\n'))
MUT_RECIPE_VENDOR_NOHINT = ('Core/ProfessionUI.lua', (
    b'        vz.__tipLines = PD.VendorLines(spec.src)\n',
    b'        vz.__tipLines = nil -- MUT: merchant zone shows no hint\n'))
MUT_RECIPE_VENDOR_NOACT = ('Core/ProfessionUI.lua', (
    b'        vz.__act = PD.VendorAct(spec.src)\n',
    b'        vz.__act = nil -- MUT: merchant zone does not mark the map\n'))
MUT_RECIPE_SEGS_NOFREE = ('Core/ProfessionUI.lua', (
    b'    PD.ClearMatSegs(r)\n',
    b'    -- MUT: stale material hotspots not collapsed across pages\n'))

"""

MUT_ANCHOR = "MUTATIONS = [\n"

RECIPE_REGS = r"""    # 2026-10-09 配方页提示框改版（用户）
    ('配方页：材料列退回一整串（没有分段热区可挂）', MUT_RECIPE_MATCHAIN_GONE),
    ('配方页：材料热区不挂物品 id（悬停没提示框）', MUT_RECIPE_MATZONE_NOIT),
    ('配方页：材料热区不比着字串锚（量宽必漂）', MUT_RECIPE_ZONE_ANCHOR_GONE),
    ('配方页：商人半段不拆（没有商人热区）', MUT_RECIPE_VENDOR_SPLIT_GONE),
    ('配方页：商人热区不出提示框（看不到「点击定位」）', MUT_RECIPE_VENDOR_NOHINT),
    ('配方页：商人热区点击不落图', MUT_RECIPE_VENDOR_NOACT),
    ('配方页：行池复用不收起分段热区（透明热区吞鼠标）', MUT_RECIPE_SEGS_NOFREE),
"""


def patch_df_mut(fn):
    p, raw, txt = load(fn)
    if 'MUT_RECIPE_MATCHAIN_GONE' in txt:
        print('[SKIP] %s：已含 ㊿ 一节' % fn)
        return
    txt = sub_once(txt, OLD_MUT_OLD, NEW_MUT_OLD, fn + ' :: 旧变异 old 侧')
    txt = sub_once(txt, OLD_MUT_NEW, NEW_MUT_NEW, fn + ' :: 旧变异 new 侧')
    txt = sub_once(txt, MUT_ANCHOR, RECIPE_DEFS + MUT_ANCHOR, fn + ' :: ㊿ DEFS')
    txt = sub_once(txt, MUT_ANCHOR, MUT_ANCHOR + RECIPE_REGS, fn + ' :: ㊿ REGS')
    for n in ('MUT_RECIPE_MATCHAIN_GONE', 'MUT_RECIPE_SEGS_NOFREE'):
        assert txt.count(n) == 2, '%s 出现 %d 次（应 2）' % (n, txt.count(n))
    save(p, txt.encode('utf-8'))


# ══════════════════════════════════════════════════════════════════════════
# 三、mk_df_mut.py：同步修那条旧锚点（生成器该处文本）
# ══════════════════════════════════════════════════════════════════════════
MK_OLD_A = r'mats = PD.MatCol(r[12], PD.MAT_FS, PD.MAT_W),'
MK_NEW_A = r'mats = mcol,'
MK_OLD_B = r"""-- MUT: mats back into sub\\n        mats = \"\",\\n'))"""
MK_NEW_B = r"""-- MUT: mats back into sub\\n        mats = \"\",\\n        matSegs = nil,\\n'))"""


def patch_mk_mut(fn):
    p, raw, txt = load(fn)
    if MK_NEW_A in txt and MK_NEW_B in txt:
        print('[SKIP] %s：旧锚点已同步' % fn)
        return
    txt = sub_once(txt, MK_OLD_A, MK_NEW_A, fn + ' :: MUT_PROF_MATCOL_BACK old')
    txt = sub_once(txt, MK_OLD_B, MK_NEW_B, fn + ' :: MUT_PROF_MATCOL_BACK new')
    save(p, txt.encode('utf-8'))


# ══════════════════════════════════════════════════════════════════════════
# 四、df_check_new_muts.py：DEFAULT_WANT 登记
# ══════════════════════════════════════════════════════════════════════════
WANT_ANCHOR = """    '升级 HUD：配方查找表不并 rinfo（附魔段「材料未收录」）',
]
"""
WANT_NEW = """    '升级行：ClearMats 不收起材料热区（切页留透明热区）',
    # 2026-10-09 配方页提示框改版（用户）
    '配方页：材料列退回一整串（没有分段热区可挂）',
    '配方页：材料热区不挂物品 id（悬停没提示框）',
    '配方页：材料热区不比着字串锚（量宽必漂）',
    '配方页：商人半段不拆（没有商人热区）',
    '配方页：商人热区不出提示框（看不到「点击定位」）',
    '配方页：商人热区点击不落图',
    '配方页：行池复用不收起分段热区（透明热区吞鼠标）',
]
"""


def patch_prober(fn):
    p, raw, txt = load(fn)
    if '2026-10-09 配方页提示框改版' in txt:
        print('[SKIP] %s：已登记' % fn)
        return
    txt = sub_once(txt, WANT_ANCHOR, WANT_NEW, fn + ' :: DEFAULT_WANT')
    save(p, txt.encode('utf-8'))


if __name__ == '__main__':
    print('── 一、harness 断言 ──')
    patch_harness('df_dungeon_check.py')
    patch_harness('mk_df_check.py')
    print('── 二、df_mut_check.py 变异 ──')
    patch_df_mut('df_mut_check.py')
    print('── 三、mk_df_mut.py 旧锚点同步 ──')
    patch_mk_mut('mk_df_mut.py')
    print('── 四、df_check_new_muts.py 登记 ──')
    patch_prober('df_check_new_muts.py')
    print('[DONE]')
