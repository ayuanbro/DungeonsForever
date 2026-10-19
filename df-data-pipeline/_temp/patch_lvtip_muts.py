# -*- coding: utf-8 -*-
"""2026-10-09 升级行提示框改版 —— 收尾补丁（断言加强 + 变异 + 登记 + 生成器追平）。

一、加强 harness 断言（df_dungeon_check.py / mk_df_check.py）：
    原来的新断言只钉了「OnMouseWheel 那一行的头」，没钉转发体 ⇒ 把
    `DG.WheelScroll(...)` 掏空也抓不到。改成三行整块锚点，并把「行池复用收起
    制作物热区」「ClearMats 收起材料热区」两条也钉上（都是真实踩过的坑：
    透明热区跨页残留会吞鼠标、切页后满屏不可滚）。

二、df_mut_check.py 加 7 条变异（每条都是「真实错误写法」）。
三、mk_df_mut.py 追加同名一节（生成器追平；照 _GUIDE_* 那套 _DEFS + _REGS 模式）。
四、df_check_new_muts.py 的 DEFAULT_WANT 登记这 7 条名字。

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
    eol = 'CRLF' if raw.count(b'\r\n') else 'LF'
    print('     落盘 %s：%d 字节 / %s（裸 LF=%d 裸 CR=%d）'
          % (os.path.basename(p), len(raw), eol,
             raw.count(b'\n') - raw.count(b'\r\n'), raw.count(b'\r') - raw.count(b'\r\n')))


def sub_once(txt, old, new, tag):
    n = txt.count(old)
    if n != 1:
        sys.exit('[FAIL] %s：锚点命中 %d 次（应恰好 1）' % (tag, n))
    return txt.replace(old, new, 1)


# ══════════════════════════════════════════════════════════════════════════
# ① harness 断言加强（两份同源）
# ══════════════════════════════════════════════════════════════════════════
OLD_WHEEL = r"""       and '    z:SetScript("OnMouseWheel", function(self, delta)\n' in profui
"""
NEW_WHEEL = r"""       # 滚轮转发钉**整块**（只钉函数头的话，把 DG.WheelScroll 掏空也抓不到）
       and '    z:SetScript("OnMouseWheel", function(self, delta)\n        DG.WheelScroll(PD.scroll, PD.child, delta)\n    end)\n' in profui
       # 行池跨页复用必须收起热区：不收起就留一个透明热区在旧位置吞鼠标（实机踩过）
       and '    if r.__iconZone then r.__iconZone:Hide() end\n' in profui
       and '        if b.zone then b.zone:Hide() end\n' in profui
"""


def patch_harness(fn):
    p, raw, txt = load(fn)
    if "滚轮转发钉**整块**" in txt:
        print('[SKIP] %s：断言已是加强版' % fn)
        return
    txt = sub_once(txt, OLD_WHEEL, NEW_WHEEL, fn + ' :: wheel-anchor')
    assert txt.count('滚轮转发钉**整块**') == 1
    assert txt.count(r'    if r.__iconZone then r.__iconZone:Hide() end\n') == 1
    assert txt.count(r'        if b.zone then b.zone:Hide() end\n') == 1
    save(p, txt.encode('utf-8'))


# ══════════════════════════════════════════════════════════════════════════
# ② df_mut_check.py：7 条变异定义 + 登记
# ══════════════════════════════════════════════════════════════════════════
LVTIP_DEFS = r"""# ㊾ 升级行提示框改版（2026-10-09 用户）：「每行有个鼠标提示框，这个提示框不要了，
#   改成当我们移动到制作物或需求材料的上方时，显示该物品的鼠标提示框。注意，这个
#   提示框不使用我们的主题」。守护点：① 行级 noTip 短路不许退回；② 制作物热区必须
#   挂产物 itemID 且盖住「图标 + 名称列」；③ 材料热区必须挂该材料 id；④ 两处热区都
#   要转发滚轮（否则压在热区上整页滚不动）；⑤ 行池跨页复用时热区必须收起。
MUT_LVTIP_ROW_TIP_BACK = ('Core/ProfessionUI.lua', (
    b'                noTip = true,\n',
    b'                -- MUT: row-level segment tooltip back\n'))
MUT_LVTIP_ICONZONE_NOIT = ('Core/ProfessionUI.lua', (
    b'        iz.__it = itemID and { itemID } or nil\n',
    b'        iz.__it = nil -- MUT: craft-product tooltip never fires\n'))
MUT_LVTIP_ICONZONE_NARROW = ('Core/ProfessionUI.lua', (
    b'        iz:SetSize(PD.LV_NAME_X - PD.LV_ICON_X + PD.LV_NAME_W, h)\n',
    b'        iz:SetSize(PD.TBL_ICON, h) -- MUT: hotspot covers the icon only\n'))
MUT_LVTIP_MATZONE_NOIT = ('Core/ProfessionUI.lua', (
    b'    b.zone.__it = { blk.id }\n',
    b'    b.zone.__it = nil -- MUT: material tooltip never fires\n'))
MUT_LVTIP_ZONE_NOWHEEL = ('Core/ProfessionUI.lua', (
    b'    z:SetScript("OnMouseWheel", function(self, delta)\n'
    b'        DG.WheelScroll(PD.scroll, PD.child, delta)\n'
    b'    end)\n',
    b'    z:SetScript("OnMouseWheel", function(self, delta)\n'
    b'        do end -- MUT: wheel swallowed (page unscrollable over hotspots)\n'
    b'    end)\n'))
MUT_LVTIP_ICONZONE_KEEPSHOWN = ('Core/ProfessionUI.lua', (
    b'    if r.__iconZone then r.__iconZone:Hide() end\n',
    b'    -- MUT: hotspot not collapsed on rebind (invisible zone eats the mouse)\n'))
MUT_LVTIP_MATZONE_KEEPSHOWN = ('Core/ProfessionUI.lua', (
    b'        if b.zone then b.zone:Hide() end\n',
    b'        do end -- MUT: material hotspot not collapsed in ClearMats\n'))

"""

LVTIP_REGS = r"""    # ㊾ 升级行提示框改版（2026-10-09 用户）
    ('升级行：行级提示框又长回来（整段说明复辟）', MUT_LVTIP_ROW_TIP_BACK),
    ('升级行：制作物热区不挂产物 id（悬停没提示框）', MUT_LVTIP_ICONZONE_NOIT),
    ('升级行：制作物热区只盖图标（名称列悬停不了）', MUT_LVTIP_ICONZONE_NARROW),
    ('升级行：材料热区不挂材料 id（悬停没提示框）', MUT_LVTIP_MATZONE_NOIT),
    ('升级行：热区吞滚轮（压在热区上整页滚不动）', MUT_LVTIP_ZONE_NOWHEEL),
    ('升级行：行池复用不收起制作物热区（透明热区吞鼠标）', MUT_LVTIP_ICONZONE_KEEPSHOWN),
    ('升级行：ClearMats 不收起材料热区（切页留透明热区）', MUT_LVTIP_MATZONE_KEEPSHOWN),
"""

MUT_DEF_ANCHOR = "MUTATIONS = [\n"


def patch_df_mut(fn):
    p, raw, txt = load(fn)
    if 'MUT_LVTIP_ROW_TIP_BACK' in txt:
        print('[SKIP] %s：已含 ㊾ 一节' % fn)
        return
    txt = sub_once(txt, MUT_DEF_ANCHOR, LVTIP_DEFS + MUT_DEF_ANCHOR, fn + ' :: DEFS')
    txt = sub_once(txt, MUT_DEF_ANCHOR, MUT_DEF_ANCHOR + LVTIP_REGS, fn + ' :: REGS')
    for n in ('MUT_LVTIP_ROW_TIP_BACK', 'MUT_LVTIP_MATZONE_KEEPSHOWN'):
        assert txt.count(n) == 2, '%s 出现 %d 次（应 2：定义 + 登记）' % (n, txt.count(n))
    save(p, txt.encode('utf-8'))


# ══════════════════════════════════════════════════════════════════════════
# ③ mk_df_mut.py：生成器追平 —— 追加同名一节（照 _GUIDE_* 那套模式）
# ══════════════════════════════════════════════════════════════════════════
def mk_mut_section():
    """把 ㊾ 一节包成生成器代码（DEFS 插在 MUTATIONS 前、REGS 插在其后）。"""

    def lit(block):
        # 把一整段多行文本变成生成器里那种一行一个 Python 字符串字面量的形式
        out = []
        for line in block.split('\n')[:-1]:
            s = line.replace('\\', '\\\\').replace('"', '\\"')
            out.append('    "%s\\n"\n' % s)
        return ''.join(out)

    return (
        '\n'
        '# ── ㊾ 升级行提示框改版（2026-10-09 用户）────────────────────────────\n'
        '_LVTIP_MUT_DEFS = (\n'
        + lit(LVTIP_DEFS) +
        ')\n'
        '\n'
        '\n'
        '_LVTIP_REGS = (\n'
        + lit(LVTIP_REGS) +
        ')\n'
        '\n'
        '\n'
        '_LVTIP_DEF_ANCHOR = "MUTATIONS = [\\n"\n'
        "if _LVTIP_DEF_ANCHOR not in text:\n"
        "    sys.exit('未找到 MUTATIONS 列表头，上游可能已改动')\n"
        "if 'MUT_LVTIP_ROW_TIP_BACK' in text:\n"
        "    print('  %-40s -> 已存在，跳过' % ('㊾ 升级行提示框改版'))\n"
        "else:\n"
        "    text = text.replace(_LVTIP_DEF_ANCHOR, _LVTIP_MUT_DEFS + _LVTIP_DEF_ANCHOR, 1)\n"
        "    text = text.replace(_LVTIP_DEF_ANCHOR, _LVTIP_DEF_ANCHOR + _LVTIP_REGS, 1)\n"
        "    print('  %-40s -> 定义 + 登记各 %d 处' % ('㊾ 升级行提示框改版', 1))\n"
    )


def patch_mk_mut(fn):
    p, raw, txt = load(fn)
    if '_LVTIP_MUT_DEFS' in txt:
        print('[SKIP] %s：已含 ㊾ 一节' % fn)
        return
    anchor = '_HELPER_ANCHOR = "def split_spec(spec):"\n'
    txt = sub_once(txt, anchor, mk_mut_section() + anchor, fn + ' :: ㊾ 节')
    assert txt.count('_LVTIP_MUT_DEFS') == 2, txt.count('_LVTIP_MUT_DEFS')
    assert txt.count('_LVTIP_REGS') == 2, txt.count('_LVTIP_REGS')
    save(p, txt.encode('utf-8'))
    # 语法体检由调用方 py_compile 负责


# ══════════════════════════════════════════════════════════════════════════
# ④ df_check_new_muts.py：DEFAULT_WANT 登记
# ══════════════════════════════════════════════════════════════════════════
WANT_ANCHOR = r"""    '搜索：输入后不重渲染（要按回车才滤）',
]
"""
WANT_NEW = r"""    '搜索：输入后不重渲染（要按回车才滤）',
    # ㊾ 升级行提示框改版（2026-10-09 用户）
    '升级行：行级提示框又长回来（整段说明复辟）',
    '升级行：制作物热区不挂产物 id（悬停没提示框）',
    '升级行：制作物热区只盖图标（名称列悬停不了）',
    '升级行：材料热区不挂材料 id（悬停没提示框）',
    '升级行：热区吞滚轮（压在热区上整页滚不动）',
    '升级行：行池复用不收起制作物热区（透明热区吞鼠标）',
    '升级行：ClearMats 不收起材料热区（切页留透明热区）',
]
"""


def patch_prober(fn):
    p, raw, txt = load(fn)
    if '㊾ 升级行提示框改版' in txt:
        print('[SKIP] %s：已登记' % fn)
        return
    txt = sub_once(txt, WANT_ANCHOR, WANT_NEW, fn + ' :: DEFAULT_WANT')
    save(p, txt.encode('utf-8'))


if __name__ == '__main__':
    print('── ① harness 断言加强 ──')
    patch_harness('df_dungeon_check.py')
    patch_harness('mk_df_check.py')
    print('── ② df_mut_check.py 加变异 ──')
    patch_df_mut('df_mut_check.py')
    print('── ③ mk_df_mut.py 生成器追平 ──')
    patch_mk_mut('mk_df_mut.py')
    print('── ④ df_check_new_muts.py 登记 ──')
    patch_prober('df_check_new_muts.py')
    print('[DONE]')
