# -*- coding: utf-8 -*-
"""离线预览图（v3）：左列「按钮皮 + 职业色文字 + 圆角裁剪图标 + 4px 间距」+ 14 号板块页签。

对应本轮（2026-09-30 第二轮）改动：
  · 左列 9 职业条目的**文字取职业色**（RAID_CLASS_COLORS；未选中 alpha 0.82，
    选中 alpha 1 + 金色描边）——「职业排行」不是职业，仍走中性色；
  · 左列条目之间加 4px 纵向间距（TT.NAV_ITEM_GAP，步进 26+4=30），按钮不再贴在一起；
  · 「指南」/「专精指南」分组标题 16，右上子页签 + 板块页签统一 14。

纯预览用，不参与打包、不进 AddOns。用法：python _gen_tier_preview.py
输出：_temp/_tier_ui_preview.png
"""
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ICONS = os.path.join(ROOT, 'Media', 'icon', 'CLASS')
MASK = os.path.join(ROOT, 'Media', 'LibHUI', 'HUIRoundRectMask.tga')

Z = 3                               # 放大倍数
NAV_W, ITEM_H, ICON = 148, 26, 20
ITEM_GAP = 4                        # TT.NAV_ITEM_GAP
PITCH = ITEM_H + ITEM_GAP           # TT.NAV_ITEM_STEP
ICON_X = 5                          # 游戏里图标瓦片 SetPoint("LEFT", bt, "LEFT", 5, 0)
TXT_DX = ICON_X + ICON + 5          # 游戏里 fs:SetPoint("LEFT", bt, "LEFT", 30, 0)
BTN_R = 6                           # SkinButton 里 BuildRoundBorder 的 cr
NAV_FS, NAV_HEAD_FS, TAB_FS = 16, 16, 14

# 左列纵向节奏（与源码常量同值）
NAV_HEAD_Y, NAV_RANK_Y, NAV_GROUP_Y, NAV_FIRST_Y = 2, 22, 58, 84

ORDER = ['WARRIOR', 'PALADIN', 'HUNTER', 'ROGUE', 'PRIEST',
         'SHAMAN', 'MAGE', 'WARLOCK', 'DRUID']
CN = {'WARRIOR': '战士', 'PALADIN': '圣骑士', 'HUNTER': '猎人', 'ROGUE': '潜行者',
      'PRIEST': '牧师', 'SHAMAN': '萨满祭司', 'MAGE': '法师', 'WARLOCK': '术士',
      'DRUID': '德鲁伊'}
# 客户端 RAID_CLASS_COLORS（经典旧世口径）
CLS_COLOR = {
    'WARRIOR': (0.78, 0.61, 0.43), 'PALADIN': (0.96, 0.55, 0.73),
    'HUNTER': (0.67, 0.83, 0.45), 'ROGUE': (1.00, 0.96, 0.41),
    'PRIEST': (1.00, 1.00, 1.00), 'SHAMAN': (0.00, 0.44, 0.87),
    'MAGE': (0.41, 0.80, 0.94), 'WARLOCK': (0.58, 0.51, 0.79),
    'DRUID': (1.00, 0.49, 0.04),
}
SEL = 'DRUID'

# 「职业排行」用的书本图标（inv_misc_book_11）只在客户端侧，预览从用户参考截图里裁一份。
BOOK_REF = (r'C:\Users\Administrator\.workbuddy\clipboard-images'
            r'\clipboard-2026-09-29T22-48-49-681Z-f40dbd34.png')
BOOK = os.path.join(HERE, '_book_icon.png')

TABS = ['改动速览', '定位评估', '优缺点', '新手上手', '职业系统', '种族推荐']
TAB_ON = 4
RIGHT_W, TAB_STEP, TAB_PAD = 778, 5, 24

PAGE_BG = (26, 26, 26, 255)
C_BG = (0x2a, 0x2d, 0x31)
C_BORDER = (0x55, 0x58, 0x5e)
C_GREY = (140, 140, 140)
C_DIM = (161, 161, 161)
C_WHITE = (255, 255, 255)
C_GOLD = (255, 209, 0)

FONT = None
for cand in (r'C:\Windows\Fonts\msyhbd.ttc', r'C:\Windows\Fonts\msyh.ttc',
             r'C:\Windows\Fonts\simhei.ttf'):
    if os.path.isfile(cand):
        FONT = cand
        break


def font(px):
    return ImageFont.truetype(FONT, px) if FONT else ImageFont.load_default()


def rounded_tile(art, size, mask_path):
    """按蒙版 alpha 做圆角裁剪（= 游戏里 RoundIcon 的效果）。"""
    a = art.convert('RGBA').resize((size, size), Image.LANCZOS)
    m = Image.open(mask_path).convert('RGBA').resize((size, size), Image.LANCZOS)
    ma = m.getchannel('A')
    out = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    for yy in range(size):
        for xx in range(size):
            r, g, b, al = a.getpixel((xx, yy))
            out.putpixel((xx, yy), (r, g, b, al * ma.getpixel((xx, yy)) // 255))
    return out


def main():
    x0, y0 = 10, 8
    navw, ih = NAV_W * Z, ITEM_H * Z
    pad, lw = 10, max(1, Z)
    nav_bottom = NAV_FIRST_Y + len(ORDER) * PITCH - ITEM_GAP
    W = x0 * 2 + navw + pad + 620
    H = y0 * 2 + (max(nav_bottom, NAV_RANK_Y + ITEM_H) + 20) * Z
    im = Image.new('RGBA', (W, H), PAGE_BG)
    d = ImageDraw.Draw(im)

    # 手算底色（ImageDraw 不做 alpha 混合）：按钮体 = 页面底 + 50% C_BG；
    # 选中行再叠 4% 白（对应代码里 cb.bg 的 SetColorTexture(1,1,1,0.04)）。
    def mix(a, b, k):
        return tuple(round(a[i] * (1 - k) + b[i] * k) for i in range(3))

    body = mix(PAGE_BG[:3], C_BG, 0.5)
    body_sel = mix(body, (255, 255, 255), 0.04)

    def skin(box, sel=False):
        """SkinButton 皮：1px 圆角描边（C_BORDER；选中改金色）+ 按钮体底色。"""
        d.rounded_rectangle(box, radius=BTN_R * Z, fill=(body_sel if sel else body) + (255,))
        d.rounded_rectangle(box, radius=BTN_R * Z,
                            outline=(C_GOLD if sel else C_BORDER) + (255,), width=lw)

    def tile(path, cx, cy):
        ic = rounded_tile(Image.open(path), ICON, MASK).resize(
            (ICON * Z, ICON * Z), Image.LANCZOS)
        im.alpha_composite(ic, (int(cx), int(cy)))

    f16, fn, ft = font(NAV_HEAD_FS * Z), font(NAV_FS * Z), font(TAB_FS * Z)
    iy_off = (ITEM_H - ICON) // 2 * Z

    book = BOOK
    if not os.path.isfile(book):
        if os.path.isfile(BOOK_REF):
            Image.open(BOOK_REF).convert('RGBA').crop((17, 13, 53, 49)).save(book)
        else:
            book = os.path.join(ICONS, 'ClassIcon_Warrior.blp')   # 兜底占位

    # ── 「指南」分组标题（16 号）
    d.text((x0 + 5 * Z, y0 + NAV_HEAD_Y * Z), '指南', font=f16, fill=C_GREY)

    # ── 「职业排行」按钮（不是职业 ⇒ 中性文字色）
    by = y0 + NAV_RANK_Y * Z
    skin((x0, by, x0 + navw, by + ih))
    tile(book, x0 + ICON_X * Z, by + iy_off)
    d.text((x0 + TXT_DX * Z, by + ih // 2), '职业排行', font=fn, fill=C_DIM, anchor='lm')

    # ── 「专精指南」分组标题（16 号）
    d.text((x0 + 5 * Z, y0 + NAV_GROUP_Y * Z), '专精指南', font=f16, fill=C_GREY)

    # ── 9 职业条目：文字 = 职业色（未选中 alpha 0.82 / 选中 alpha 1 + 金描边），条目间留 4px
    y = y0 + NAV_FIRST_Y * Z
    for cls in ORDER:
        sel = (cls == SEL)
        skin((x0, y, x0 + navw, y + ih), sel)
        tile(os.path.join(ICONS, 'ClassIcon_%s.blp' % (cls[0] + cls[1:].lower())),
             x0 + ICON_X * Z, y + iy_off)
        c = CLS_COLOR[cls]
        txt = c if sel else mix(body, c, 0.82)      # 未选中 0.82 不透明度
        d.text((x0 + TXT_DX * Z, y + ih // 2), CN[cls], font=fn,
               fill=tuple(round(v * 255) for v in txt), anchor='lm')
        y += PITCH * Z

    # ── 板块页签行（14 号，高 24；无底部强调条，选中只靠金描边 + 白字）
    tx, ty = x0 + navw + pad, y0 + 30 * Z
    maxw = (RIGHT_W - (len(TABS) - 1) * TAB_STEP) // len(TABS)
    for i, t in enumerate(TABS):
        w = min(len(t) * TAB_FS + TAB_PAD, maxw) * Z
        on = (i == TAB_ON)
        d.rounded_rectangle((tx, ty, tx + w, ty + 24 * Z), radius=6 * Z, fill=body + (255,))
        d.rounded_rectangle((tx, ty, tx + w, ty + 24 * Z), radius=6 * Z,
                            outline=(C_GOLD if on else C_BORDER) + (255,), width=lw)
        d.text((tx + w // 2, ty + 12 * Z), t, font=ft,
               fill=C_WHITE if on else C_DIM, anchor='mm')
        tx += w + TAB_STEP * Z

    out = os.path.join(HERE, '_tier_ui_preview.png')
    im.convert('RGB').save(out)
    print('saved', out, im.size)


if __name__ == '__main__':
    main()
