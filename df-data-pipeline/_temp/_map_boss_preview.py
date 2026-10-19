# -*- coding: utf-8 -*-
"""「地图页 · 首领钉点 + 右栏掉落/攻略 + 楼层按钮右上角悬浮」——实装版版式图（三版）。

几何完全按 Core/MapUI.lua 的真实常量算，不估：
  detail 内区 936×570（960 面板 − 12 内缩 ×2 宽；648 高 − ROW_CLASS 30 − 36 二级行）
  地图帧顶 = DETAIL 顶 + GUIDE_TOP_Y(128) ⇒ 帧高 = 570 − 128 = 442（M.FRAME_H）
  ★ 三版（2026-09-30 用户）：地图**满高** —— 图高 = FRAME_H 442 ⇒ 图宽 = 442×1002/668 = 663
    （M.MAP_W）；右栏宽反推 = 936 − 663 − 10 = 263（M.SIDE_W）。
  ★ 右栏详情：**掉落在上、攻略在下**；两块标题同款（14 金）；攻略正文 = 首领技能表
    + 一句话攻略（都没有才「攻略待补充」）。
  楼层按钮 = 46×20、间距 4、贴**地图右上角内侧 6px**、右起排（M.LAYER_W/GAP/FLOOR_INSET）
  钉点 = 未选 9px 暗金 / 选中 16px 亮金 + 右侧名字（M.PIN_MIN / M.PIN_SIZE）

数据全部来自插件本体（用真 Lua 5.1 读 Data_DungeonLoot / Data_DungeonGuide /
Data_BossPos / Data_BossSkills），不是手抄。
出图：MAP_BOSS_PREVIEW.png
"""
import os

from lupa import lua51
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(HERE)
RF_TILES = os.path.join(HERE, "_mapprobe_png", "ragefire")
MAPCHECK = os.path.join(HERE, "_mapcheck")
REF = os.path.join(HERE, "_ref")
OUT = os.path.join(HERE, "MAP_BOSS_PREVIEW.png")
FONT = "C:/Windows/Fonts/msyh.ttc"

ART_W, ART_H = 1002, 668
DETAIL_W, DETAIL_H = 936, 570
HERO_H = 120
GUIDE_TOP_Y = 128
FRAME_H = DETAIL_H - GUIDE_TOP_Y              # 442
SIDE_GAP = 10
MAP_W = int(FRAME_H * ART_W / ART_H)          # 663（满高）
SIDE_W = DETAIL_W - MAP_W - SIDE_GAP          # 263

LAYER_W, LAYER_H, LAYER_GAP, FLOOR_INSET = 46, 20, 4, 6
PIN_MIN, PIN_SIZE = 9, 16
LIST_H, CARD_H, CARD_ICON = 22, 38, 20
SIDE_PAD = 8
INNER_W = SIDE_W - SIDE_PAD * 2               # 247

BG = (14, 17, 21)
PANEL = (34, 34, 37)
PANEL2 = (26, 27, 31)
HERO = (56, 60, 68)
TAB_OFF = (44, 46, 52)
TAB_ON = (96, 78, 22)
GOLD = (255, 209, 0)
GOLD_D = (184, 148, 31)
GREY = (172, 172, 172)
DIM = (130, 132, 140)
FAINT = (96, 98, 106)
WHITE = (238, 238, 238)
GREEN = (107, 240, 158)
EDGE = (92, 94, 102)
CARD_EDGE = (74, 76, 84)


def fnt(sz):
    return ImageFont.truetype(FONT, sz)


def wrap(d, text, font, maxw):
    lines, cur = [], ""
    for ch in text:
        if ch == "\n":
            lines.append(cur)
            cur = ""
            continue
        if d.textlength(cur + ch, font=font) > maxw and cur:
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines


# ---------------------------------------------------------------- 读插件真数据
def load_ns():
    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    lua.execute("ns = {}")
    run = lua.eval('function(code) local f = loadstring(code); return f("DungeonsForever", ns) end')

    def read(rel):
        return open(os.path.join(DF, *rel.split('/')), 'rb').read().decode('utf-8')

    for rel in ('Core/Data/Data_DungeonLoot.lua', 'Core/Data/Data_DungeonGuide.lua',
                'Core/Data/Data_BossPos.lua', 'Core/Data/Data_BossSkills.lua'):
        run(read(rel))
    return lua.eval('ns')


NS = load_ns()
LOOT, GUIDE, BOSSPOS, BOSSSKILLS = NS.DungeonLoot, NS.DungeonGuide, NS.BossPos, NS.BossSkills


def _arr(t):
    """Lua 数组（1-based）→ Python list。"""
    if t is None:
        return []
    return [t[i] for i in range(1, len(t) + 1)]


def _keys(t):
    return set(t.keys()) if t is not None else set()


def bosses_for(did):
    """与 Core/MapUI.lua 的 M.BossesFor 同口径：有 npcid ∪ 有坐标 ∪ 有攻略。"""
    rows, out = LOOT[did], []
    guides = set()
    g = GUIDE[did]
    if g is not None:
        for b in _arr(g['bosses']):
            guides.add(b['en'])
    pins = _keys(BOSSPOS[did])
    for s in _arr(rows):
        if (s[4] and s[4] != '') or (s[1] in pins) or (s[1] in guides):
            items = [(it[1], it[2], it[3]) for it in _arr(s[5])]
            out.append({'en': s[1], 'zh': s[2], 'items': items})
    return out


def pins_for(did):
    out = []
    row = BOSSPOS[did]
    for b in bosses_for(did):
        pts = row[b['en']] if row is not None else None
        for p in _arr(pts):
            out.append({'en': b['en'], 'zh': b['zh'], 'left': p[1], 'top': p[2]})
    return out


def guide_for(did, en):
    g = GUIDE[did]
    if g is None:
        return None
    for b in _arr(g['bosses']):
        if b['en'] == en:
            return b['text']
    return None


def skills_for(did, en):
    row = BOSSSKILLS[did]
    if row is None or en not in row:
        return None
    return [_arr(row[en][i]) for i in range(1, len(row[en]) + 1)]


def guide_text_for(did, en):
    """攻略正文 = wowhead 攻略（GuideFor）；与 MapUI.SyncSide 新版式同口径。"""
    return guide_for(did, en)


# ---------------------------------------------------------------- 地图素材
def map_custom(name):
    """用户手绘 TGA（与 M.CustomFor 同口径：1024×1024、画面占顶部 683 行，UV 裁顶）。"""
    p = os.path.join(DF, "Media", "Maps", name)
    im = Image.open(p).convert("RGB")
    w, h = im.size
    return im.crop((0, 0, w, int(h * 683 / 1024)))


def map_ragefire():
    c = Image.new("RGB", (4 * 256, 3 * 256), (0, 0, 0))
    for n in range(1, 13):
        f = os.path.join(RF_TILES, "ragefire_%02d.png" % n)
        if os.path.exists(f):
            c.paste(Image.open(f).convert("RGB"), (((n - 1) % 4) * 256, ((n - 1) // 4) * 256))
    return c.crop((0, 0, ART_W, ART_H))


def map_layer(name):
    f = os.path.join(MAPCHECK, name)
    im = Image.open(f).convert("RGB")
    return im.crop((0, 0, min(im.width, ART_W), min(im.height, ART_H)))


def fit(art, aw, ah):
    s = min(aw / art.width, ah / art.height)
    return art.resize((int(art.width * s), int(art.height * s)), Image.LANCZOS)


# ---------------------------------------------------------------- 画零件
ICONS = [os.path.join(REF, n) for n in ("i_crossbow.jpg", "i_bone.jpg", "i_whirl.jpg")]


def draw_pin(im, d, cx, cy, sel, name=None):
    r = PIN_SIZE / 2.0 if sel else PIN_MIN / 2.0
    x0, y0, x1, y1 = cx - r, cy - r, cx + r, cy + r
    if sel:
        for k in range(5, 0, -1):
            d.ellipse([x0 - k, y0 - k, x1 + k, y1 + k], outline=(120, 92, 16))
        d.ellipse([x0, y0, x1, y1], fill=GOLD, outline=(255, 240, 180))
    else:
        d.ellipse([x0, y0, x1, y1], fill=GOLD_D, outline=(88, 70, 12))
    if sel and name:
        f = fnt(11)
        tw = d.textlength(name, font=f)
        bx = cx + r + 3
        d.rectangle([bx - 1, cy - 8, bx + tw + 4, cy + 8], fill=(28, 22, 8), outline=(120, 92, 16))
        d.text((bx + 1, cy - 6), name, font=f, fill=GOLD)


def floor_bar(d, mx, my, mw, n, cur):
    """贴地图右上角内侧 FLOOR_INSET，右起排 —— 实装 B 方案。"""
    x1 = mx + mw - FLOOR_INSET
    y0 = my + FLOOR_INSET
    for i in range(n, 0, -1):
        bx1 = x1 - (n - i) * (LAYER_W + LAYER_GAP)
        bx0 = bx1 - LAYER_W
        sel = (i == cur)
        d.rectangle([bx0, y0, bx1, y0 + LAYER_H],
                    fill=(78, 62, 16) if sel else (40, 42, 48),
                    outline=GOLD if sel else (110, 112, 120))
        t = "第 %d 层" % i
        tw = d.textlength(t, font=fnt(12))
        d.text((bx0 + (LAYER_W - tw) / 2, y0 + 1), t, font=fnt(12), fill=GOLD if sel else GREY)


def draw_shell(d, dx, dy, title, meta, tab="地图"):
    d.rectangle([dx, dy, dx + DETAIL_W, dy + DETAIL_H], fill=PANEL, outline=EDGE)
    d.rectangle([dx + 1, dy + 1, dx + DETAIL_W - 1, dy + HERO_H], fill=HERO)
    d.text((dx + 10, dy + 6), "‹ 副本", font=fnt(14), fill=GREY)
    d.text((dx + 12, dy + 44), title, font=fnt(17), fill=WHITE)
    d.text((dx + 12, dy + 70), meta, font=fnt(13), fill=GREY)
    ty = dy + 92
    for i, name in enumerate(["掉落", "任务", "攻略", "地图"], start=1):
        rx = dx + DETAIL_W - 8 - (i - 1) * (70 + 6)
        lx = rx - 70
        on = (name == tab)
        d.rectangle([lx, ty, rx, ty + 24], fill=TAB_ON if on else TAB_OFF,
                    outline=GOLD if on else (110, 112, 120))
        tw = d.textlength(name, font=fnt(14))
        d.text((lx + (70 - tw) / 2, ty + 3), name, font=fnt(14), fill=GOLD if on else GREY)


def draw_map_panel(im, d, dx, dy, art, pins, sel_en, floors=0, floor_cur=1, empty=None):
    """左半区：地图 + 钉点 + 楼层按钮（或空态）。"""
    mx, my, mw, mh = dx, dy + GUIDE_TOP_Y, MAP_W, FRAME_H
    if art is None:
        d.rectangle([mx, my, mx + mw, my + mh], outline=(60, 62, 70))
        lab = empty or "这个副本没有客户端自带的地图。"
        f = fnt(14)
        lines = wrap(d, lab, f, mw - 80)
        yy = my + mh / 2 - len(lines) * 11
        for ln in lines:
            tw = d.textlength(ln, font=f)
            d.text((mx + (mw - tw) / 2, yy), ln, font=f, fill=DIM)
            yy += 22
        return None
    mp = fit(art, mw, mh)
    ox = mx + (mw - mp.width) // 2
    oy = my + (mh - mp.height) // 2
    im.paste(mp, (ox, oy))
    d.rectangle([ox - 1, oy - 1, ox + mp.width, oy + mp.height], outline=(118, 120, 128))
    for p in pins:
        cx = ox + p['left'] / 100.0 * mp.width
        cy = oy + p['top'] / 100.0 * mp.height
        sel = (p['en'] == sel_en)
        draw_pin(im, d, cx, cy, sel, p['zh'] if sel else None)
    if floors > 1:
        floor_bar(d, ox, oy, mp.width, floors, floor_cur)
    return (ox, oy, mp.width, mp.height)


def side_rect(dx, dy):
    """右栏（与 M.SIDE_W / M.SIDE_GAP 同版式）。"""
    return dx + MAP_W + SIDE_GAP, dy + GUIDE_TOP_Y, SIDE_W, FRAME_H


def draw_side_detail(im, d, px, py, zh, gdtext, items, idn, did=None, en=None):
    """详情态：返回键 + 名 + **掉落（上）+ 攻略（下）** —— 与 MapUI.SyncSide 三版版式一致。

    纵向偏移（MapUI.SyncSide 的 y 递推，TOPLEFT 锚、负 y 向下）：
      名字 −1（与右上角返回键同排）/「掉落」−28（计数同行）/ 卡片 −52 起每张 42 /「攻略」= 卡片底 + 8 / 正文再 −20。
    """
    iw = INNER_W
    d.rectangle([px, py, px + SIDE_W, py + FRAME_H], fill=PANEL2, outline=(84, 86, 94))
    ax, ay = px + SIDE_PAD, py + SIDE_PAD

    # 返回键：右上角（2026-09-30 用户点名；此前无锚点被内容盖住 = 实机「消失」）
    d.rectangle([ax + iw - 84, ay, ax + iw, ay + 20], fill=(40, 42, 48), outline=(110, 112, 120))
    d.text((ax + iw - 84 + 8, ay + 2), "‹ 全部首领", font=fnt(12), fill=GREY)

    d.text((ax, ay + 1), zh, font=fnt(16), fill=GOLD)

    # 掉落（上；整体上移约 22px —— 内容从按钮行下 8px 起）
    d.text((ax, ay + 28), "掉落", font=fnt(14), fill=GOLD)
    cnt = "%d 件" % len(items)
    d.text((ax + iw - d.textlength(cnt, font=fnt(12)), ay + 27), cnt, font=fnt(12), fill=GREY)

    y = 52
    for n, (iid, pct, isnew) in enumerate(items):
        ry = ay + y
        d.rectangle([ax, ry, ax + iw, ry + CARD_H], fill=(30, 31, 36), outline=CARD_EDGE)
        ic = Image.open(ICONS[n % len(ICONS)]).convert("RGB").resize((CARD_ICON, CARD_ICON),
                                                                    Image.LANCZOS)
        mask = Image.new("L", (CARD_ICON, CARD_ICON), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, CARD_ICON - 1, CARD_ICON - 1], fill=255)
        im.paste(ic, (ax + 6, ry + (CARD_H - CARD_ICON) // 2), mask)
        d.text((ax + 6 + CARD_ICON + 5, ry + 4), "物品 #%d" % iid, font=fnt(13), fill=WHITE)
        d.text((ax + 6 + CARD_ICON + 5, ry + 21), "客户端本地化", font=fnt(11), fill=DIM)
        if pct:
            pt = "%s%%" % (int(pct) if float(pct) == int(pct) else pct)
            d.text((ax + iw - 6 - d.textlength(pt, font=fnt(11)), ry + 4), pt,
                   font=fnt(11), fill=DIM)
        if isnew:
            tw = d.textlength("新", font=fnt(11))
            d.text((ax + iw - 6 - tw, ry + 21), "新", font=fnt(11), fill=GREEN)
        y += CARD_H + 4

    # 攻略（下；两块标题同款 14 金）：技能行在前（左图标占名/文两行高 + 右两行，2026-09-30 用户定版）
    #   第 1 行 = 技能名、第 2 行 = 客户端提示框内容；名字与正文同色（不单独染蓝）。
    gy = y + 8
    # 2026-09-30 二拆：技能行上方「boss技能」标题（有技能才画）、技能行下方再出「攻略」标题
    sk = skills_for(did, en) if did else None
    if sk:
        d.text((ax, ay + gy), "boss技能", font=fnt(14), fill=GOLD)
        yy = ay + gy + 22
    else:
        yy = ay + gy
    for row in (sk or []):
        nm, ds = row[0], (row[1] if len(row) > 1 else "")
        sid = row[2] if len(row) > 2 else None
        tx = ax
        if sid:
            # 技能图标 32×32 占两行高（左上角钉住，圆角裁边同全仓口径）
            ic = Image.open(ICONS[1 % len(ICONS)]).convert("RGB").resize((32, 32), Image.LANCZOS)
            mask = Image.new("L", (32, 32), 0)
            ImageDraw.Draw(mask).ellipse([0, 0, 31, 31], fill=255)
            im.paste(ic, (ax, yy), mask)
            tx = ax + 32 + 6
        d.text((tx, yy), nm, font=fnt(14), fill=WHITE)
        if ds:
            for ln in wrap(d, ds, fnt(12), iw - (38 if sid else 0)):
                d.text((tx, yy + 20), ln, font=fnt(12), fill=WHITE)
                yy += 18
            yy += 20
        else:
            yy += 24
        yy += 4
    guide = guide_for(did, en) if did else None
    if guide or not sk:
        d.text((ax, yy), "攻略", font=fnt(14), fill=GOLD)
        yy += 22
        if guide:
            for ln in wrap(d, guide, fnt(12), iw):
                d.text((ax, yy), ln, font=fnt(12), fill=WHITE)
                yy += 18
        else:
            for ln in wrap(d, "攻略待补充", fnt(12), iw):
                d.text((ax, yy), ln, font=fnt(12), fill=FAINT)
                yy += 18


def draw_side_list(im, d, px, py, rows, mark=None):
    """列表态：表头「首领」+ 行（与 MapUI.SyncSide 列表模式同版式）。"""
    d.rectangle([px, py, px + SIDE_W, py + FRAME_H], fill=PANEL2, outline=(84, 86, 94))
    d.text((px + SIDE_PAD + 2, py + SIDE_PAD), "首领", font=fnt(14), fill=GOLD)
    y = -26
    for zh in rows:
        ry = py + SIDE_PAD - y
        d.rectangle([px + SIDE_PAD, ry, px + SIDE_PAD + INNER_W, ry + LIST_H],
                    fill=(44, 46, 52) if zh == mark else None)
        d.text((px + SIDE_PAD + 8, ry + 2), zh, font=fnt(14),
               fill=GOLD if zh == mark else WHITE)
        y -= LIST_H
    return y


# ---------------------------------------------------------------- 三块版式
def build():
    PAD = 40
    TITLE_H, GAPY, CAP_H = 112, 76, 96
    W = PAD * 2 + DETAIL_W
    H = TITLE_H + 3 * (DETAIL_H + CAP_H + GAPY) + 20
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)

    d.text((PAD, 26), "实装版式：「地图」页签 · 地图满高 + 首领钉点 · 右栏掉落在上/攻略在下 · 楼层按钮右上角悬浮",
           font=fnt(20), fill=GOLD)
    d.text((PAD, 58), "① 怒焰裂谷（单层·有坐标）：4 颗钉点，点奥格弗林特 → 右栏切该首领详情（掉落卡片 + 技能攻略）；"
                      "悬停掉落行出物品提示框。", font=fnt(13), fill=GREY)
    d.text((PAD, 80), "② 死亡矿井（2 层·有坐标）：地图满高 663×442 ⇒ 右栏联动收窄到 263；"
                      "楼层按钮贴地图右上角内侧 ⇒ 单层/多层面板同高。", font=fnt(13), fill=GREY)

    # ---- ① 怒焰裂谷：单层 + 详情态 ----
    rf = map_ragefire()
    rf_pins = pins_for("ragefire_chasm")
    rf_bosses = bosses_for("ragefire_chasm")
    og = next((b for b in rf_bosses if b['en'] == 'Oggleflint'), rf_bosses[0])
    y = TITLE_H
    draw_shell(d, PAD, y, "怒焰裂谷", "13-18 级 · 奥格瑞玛 / 贫瘠之地 · BOSS %d · 掉落 %d"
               % (len(rf_bosses), sum(len(b['items']) for b in rf_bosses)))
    draw_map_panel(im, d, PAD, y, rf, rf_pins, 'Oggleflint')
    px, py, _, _ = side_rect(PAD, y)
    draw_side_detail(im, d, px, py, og['zh'], guide_text_for("ragefire_chasm", 'Oggleflint'),
                     og['items'], og['en'], did="ragefire_chasm", en='Oggleflint')
    cap(d, PAD, y, [
        ("钉点按采集坐标画在客户端原图上（ns.BossPos，9 个副本 / 59 首领 / 71 钉点）；"
         "未选 9px 暗金、选中 16px 亮金 + 右侧名字。", WHITE),
        ("【地图满高】图 = 442×1002/668 = 663 宽，与右栏卡片同高（右栏 263 = 936 − 663 − 10 联动）。"
         "单层没有楼层按钮条。", GREEN),
        ("【掉落在上·攻略在下】攻略正文 = 上游采集的首领技能（「技能名：说明」逐条）；"
         "悬停掉落行出物品提示。", GREEN)])

    # ---- ② 死亡矿井：2 层 + 楼层按钮 + 列表态 ----
    dm = map_layer("thedeadmines__thedeadmines1_.png")
    dm_pins = pins_for("the_deadmines")
    dm_bosses = bosses_for("the_deadmines")
    y += DETAIL_H + CAP_H + GAPY
    draw_shell(d, PAD, y, "死亡矿井", "17-26 级 · 西部荒野 · BOSS %d · 客户端内地图 2 层"
               % len(dm_bosses))
    draw_map_panel(im, d, PAD, y, dm, dm_pins, None, floors=2, floor_cur=1)
    px, py, _, _ = side_rect(PAD, y)
    van = next((b['zh'] for b in dm_bosses if b['en'] == 'Edwin VanCleef'), None)
    draw_side_list(im, d, px, py, [b['zh'] for b in dm_bosses], mark=van)
    cap(d, PAD, y, [
        ("【楼层按钮换位置 · B 方案】贴地图右上角内侧 6px、右起排（46×20 / 间距 4），"
         "不再往地图下方要 30px。", GOLD),
        ("切到第 2 层 → 钉点全撤（坐标只对第 1 层有效，不替玩家猜位置）；右栏为默认的「首领」列表态，"
         "点任一行同样进详情。", GREY)])

    # ---- ③ 洛丹伦废墟：用户手绘 TGA 自制图 + 首领钉点 + 真攻略 ----
    lor_bosses = bosses_for("ruins_of_lordaeron")
    lor = next((b for b in lor_bosses if b['en'] == "Rath'mael"), lor_bosses[0])
    lor_map = map_custom("RuinsOfLordaeron.tga")
    lor_pins = pins_for("ruins_of_lordaeron")
    y += DETAIL_H + CAP_H + GAPY
    draw_shell(d, PAD, y, "洛丹伦废墟", "提瑞斯法林地 · BOSS %d · 自制手绘图 + 首领钉点"
               % len(lor_bosses))
    draw_map_panel(im, d, PAD, y, lor_map, lor_pins, lor['en'])
    px, py, _, _ = side_rect(PAD, y)
    draw_side_detail(im, d, px, py, lor['zh'], guide_text_for("ruins_of_lordaeron", lor['en']),
                     lor['items'], lor['en'], did="ruins_of_lordaeron", en=lor['en'])
    cap(d, PAD, y, [
        ("【自制图 CUSTOM】Media/RuinsOfLordaeron.tga（1024×1024，画面占顶部 683 行）UV 裁顶满铺画布；"
         "钉点 = 窝窝头/站点第 1 层坐标（6 枚，选中拉斯玛尔）。", WHITE),
        ("右栏详情 = 掉落在上 + boss技能（slug 图标）+ 攻略在下 —— 攻略条目取窝窝头内容汉化"
         "（三语：zhCN 手写 / enUS 对照层 / zhTW opencc）。", GREEN)])

    im.save(OUT)
    print("ok", OUT, im.size)


def cap(d, dx, y, pairs):
    yy = y + DETAIL_H + 12
    for txt, col in pairs:
        d.text((dx, yy), txt, font=fnt(12), fill=col)
        yy += 20


if __name__ == "__main__":
    build()
