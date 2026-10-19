# -*- coding: utf-8 -*-
"""五人本四子页（地图/任务/攻略/掉落）UI 规则审计可视化方案图。"""
import os
from PIL import Image, ImageDraw, ImageFont

S = 2
W = 1104
H = 736
PAD = 16

BG = (0x10, 0x13, 0x1A)
PANEL = (0x16, 0x1A, 0x23)
CARD = (0x20, 0x25, 0x32)
EDGE = (0x3A, 0x42, 0x50)
TXT = (0xE8, 0xEC, 0xF2)
DIM = (0x8A, 0x92, 0xA0)
RED = (0xE5, 0x48, 0x4D)
AMB = (0xF2, 0xB1, 0x2E)
GRN = (0x46, 0xA7, 0x5A)
GOLD = (0xE8, 0xC5, 0x57)

img = Image.new('RGB', (W * S, H * S), BG)
d = ImageDraw.Draw(img)

F = lambda px, bd=False: ImageFont.truetype(
    r'C:\Windows\Fonts\msyhbd.ttc' if bd else r'C:\Windows\Fonts\msyh.ttc', px * S)


def rrect(x0, y0, x1, y1, r, fill, outline=None, ow=1):
    d.rounded_rectangle([x0 * S, y0 * S, x1 * S, y1 * S], r * S, fill=fill,
                        outline=outline, width=ow * S)


def text(x, y, s, px, col, bd=False, anchor='la'):
    d.text((x * S, y * S), s, font=F(px, bd), fill=col, anchor=anchor)


def badge(x, y, n, col):
    rrect(x, y, x + 20, y + 15, 4, col)
    text(x + 10, y + 7.5, str(n), 11, (0xFF, 0xFF, 0xFF), True, 'mm')


def arrow(x, y, w, col):
    d.line([(x * S, y * S), ((x + w) * S, y * S)], fill=col, width=S)
    d.polygon([((x + w) * S, y * S), ((x + w - 5) * S, (y - 3.5) * S),
               ((x + w - 5) * S, (y + 3.5) * S)], fill=col)


# ── 标题 ────────────────────────────────────────────────────────────────
text(PAD, 12, '五人本四子页 · UI 规则审计与修改方案', 16, TXT, True)
text(W - PAD, 16, '对照 .workbuddy/UI_RULES.md（2026-10-13）', 11, DIM, anchor='ra')
badge(PAD, 40, '!', RED)
text(PAD + 26, 47, '红 = 违规（可直接改）', 11, RED)
badge(PAD + 190, 40, '?', AMB)
text(PAD + 216, 47, '黄 = 需用户拍板', 11, AMB)
text(PAD + 330, 47, '页面线框按源码常量等比缩放', 11, DIM)

# ── 四页线框 ────────────────────────────────────────────────────────────
PY0, PH, PW, PGAP = 66, 146, 258, 16


def frame(x0, title, sub):
    rrect(x0, PY0, x0 + PW, PY0 + PH, 6, PANEL, EDGE)
    text(x0 + 8, PY0 + 6, title, 12, TXT, True)
    text(x0 + PW - 8, PY0 + 8, sub, 10, DIM, anchor='ra')
    return x0 + 8, PY0 + 34


# ① 地图页：hdrCard 50 / 地图 663 / 缝 10 / 右栏 263（总 936×476）
x0, y0 = frame(PAD + 0 * (PW + PGAP), '地图页', '936×476')
k = (PW - 16) / 936.0
hc_h = 50 * k
rrect(x0, y0, x0 + 936 * k, y0 + hc_h, 3, CARD, EDGE)
badge(x0 + 936 * k - 24, y0 + 2, 1, RED)
map_w = 663 * k
my = y0 + hc_h + 8 * k
mh = PH - 24 - 24 - (my - y0)
rrect(x0, my, x0 + map_w, my + mh, 3, (0x0A, 0x0D, 0x12), EDGE)
sg = 10 * k
sx = x0 + map_w + sg
rrect(sx, my, x0 + 936 * k, my + mh, 3, CARD, EDGE)
badge(sx + 40, my + 4, 1, RED)
badge(sx + 4, my + mh - 40, 2, RED)
rrect(sx + 6, my + mh - 22, sx + 6 + 46, my + mh - 22 + 13, 3, (0x2B, 0x31, 0x40), EDGE)
badge(sx + 4, my + mh - 22 - 16, 3, RED)
gx = x0 + map_w
d.line([gx * S, my * S, gx * S, (my + mh) * S], fill=RED, width=S)
badge(gx - 11, my + 3, 4, RED)
text(x0 + 8, PY0 + PH - 16, 'hdrCard 底 / 右栏底 = 白α①· 小字②· 返回钮③· 缝④', 9, DIM)

# ② 任务页：左板 520 / 右详情 408（缝 8）
x0, y0 = frame(PAD + 1 * (PW + PGAP), '任务页', '板 520 + 详情 408')
lw = 520 * ((PW - 16) / 936.0)
rrect(x0, y0, x0 + lw, y0 + PH - 24, 3, CARD, EDGE)
rx = x0 + lw + 8 * ((PW - 16) / 936.0)
rrect(rx, y0, x0 + PW - 8, y0 + PH - 24, 3, CARD, EDGE)
for i in range(3):
    ry = y0 + 20 + i * 28
    rrect(x0 + 6, ry, x0 + lw - 6, ry + 22, 3, (0x1B, 0x20, 0x2B), None)
ov = y0 - 14
rrect(x0 + 20, ov, x0 + lw - 20, ov + 20, 3, (0x1B, 0x20, 0x2B), RED)
d.line([(x0 + 20) * S, (ov + 20) * S, (x0 + lw - 20) * S, (ov + 20) * S],
       fill=RED, width=S)
badge(x0 + lw / 2 - 10, ov + 2, 5, RED)
text(x0 + 8, PY0 + PH - 16, '滚动行画出板顶、盖住上方 hero 区', 9, DIM)

# ③ 攻略页：双列卡墙 464×2（缝 8）
x0, y0 = frame(PAD + 2 * (PW + PGAP), '攻略页', '卡墙 464 × 2 列')
cw = (PW - 16 - 2) / 2
for cx in (0, cw + 2):
    rrect(x0 + cx, y0 + 16, x0 + cx + cw, y0 + PH - 24, 3, CARD, EDGE)
    rrect(x0 + cx + 4, y0 + 15, x0 + cx + cw - 4, y0 + 27, 2, (0x2B, 0x31, 0x40), None)
    for i in range(3):
        d.line([(x0 + cx + 5) * S, (y0 + 36 + i * 8) * S,
                (x0 + cx + cw - 20) * S, (y0 + 36 + i * 8) * S],
               fill=(0x2A, 0x30, 0x3C), width=S)
ov = y0 - 14
rrect(x0 + 12, ov, x0 + 12 + cw - 8, ov + 20, 3, (0x1B, 0x20, 0x2B), RED)
badge(x0 + 12 + cw / 2 - 14, ov + 2, 6, RED)
text(x0 + 8, PY0 + PH - 16, '卡墙滚动区无遮罩：滚动卡画出 hero 区', 9, DIM)

# ④ 掉落页：工具行 + 三列卡墙
x0, y0 = frame(PAD + 3 * (PW + PGAP), '掉落页', '工具行 + 卡墙')
ty = y0 + 2
bx = x0 + 8 * ((PW - 16) / 936.0)
for bw in (52, 44, 26):
    rrect(bx, ty, bx + bw, ty + 13, 3, (0x2B, 0x31, 0x40), EDGE)
    bx += bw + 4
d.line([(x0) * S, (ty - 3) * S, x0 * S, (ty + 20) * S], fill=RED, width=S)
d.line([(x0 + 2) * S, (ty - 3) * S, (x0 + 2) * S, (ty + 20) * S],
       fill=(0x55, 0x5D, 0x6C), width=S)
badge(x0 - 2, ty - 6, 7, AMB)
ky = ty + 13 + 8 * ((PW - 16) / 936.0)
cw3 = (PW - 16 - 2 * 2) / 3
for c3 in range(3):
    rrect(x0 + c3 * (cw3 + 2), ky, x0 + c3 * (cw3 + 2) + cw3, y0 + PH - 24, 3,
          CARD, EDGE)
ov = ky - 10
rrect(x0 + 10, ov, x0 + 10 + cw3 - 6, ov + 18, 3, (0x1B, 0x20, 0x2B), RED)
badge(x0 + 10 + cw3 / 2 - 8, ov + 2, 8, RED)
text(x0 + 8, PY0 + PH - 16, '⑦ 工具行左缘 8 vs 卡墙 12 · ⑧ 滚动溢出', 9, DIM)

# ── 修改方案明细 ────────────────────────────────────────────────────────
sy = PY0 + PH + 14
rrect(PAD, sy, W - PAD, sy + 24, 4, CARD)
text(PAD + 10, sy + 12, '修改方案明细', 12, TXT, True)
text(W - PAD - 10, sy + 12, '现状（源码实测） → 目标（规则值）', 11, DIM, anchor='rm')

rows = [
    ('1', '地图页 · 顶部工具栏卡 + 右栏卡底色', '§1 禁白 α 叠加',
     'BuildRoundedBG(..., {1,1,1,0.03}) ×2 处（MapUI L887/L988）',
     '底色改 ns.hui.layer.L2（非 hui 白 3% 回退保留）', '直接改'),
    ('2', '地图页 · 4 处小字', '§7 只许 14/16',
     '件数注 12 / 空态注 13 / 技能描述 12 / 列表空态 13（L756/757/846/1017）',
     '全部 → 14 号（行内小卡 12 不涉及此四处）', '直接改'),
    ('3', '地图页 · 「‹ 全部首领」返回钮', '§7 按钮标准',
     '84×20 · 字号 12（L1035）',
     '高 24 / 字号 14 / 宽按 enUS「‹ All bosses」反算', '直接改'),
    ('4', '地图页 · 地图↔右栏缝', '§3 卡↔卡 = 8',
     'M.SIDE_GAP = 10', '改 8（SIDE_W 联动 +2，地图尺寸不变）', '直接改'),
    ('5', '任务页 · 左列表 / 右详情滚动区', 'TierUI 滚动定式',
     'qscroll/qdet 无裁剪、无上缘遮罩、无行级剔除 → 行画出板顶盖 hero',
     '上缘伪裁剪遮罩（板内 L2 / 板外 L0 双段）+ 行级视口剔除', '直接改'),
    ('6', '攻略页 · 卡墙滚动区', 'TierUI 滚动定式',
     'gscroll 同上：滚动卡画出 152 上沿、盖 hero',
     '同 5（卡级遮罩 + 视口剔除）', '直接改'),
    ('7', '掉落页 · 工具行（类型/BOSS 下拉 + 视图钮）', '§3 同侧边缘对齐',
     '工具行左缘 8（GUTTER），下方卡墙左缘 0（外缘 12）→ 错位 4px',
     '整条 x 链 GUTTER→0（LOOT_BOSS_X / LOOT_VIEW_X 联动）', '需拍板'),
    ('8', '掉落页 · 卡墙滚动区', 'TierUI 滚动定式',
     'dscroll 仅 SetClipsChildren（引擎不可依赖）、无遮罩 → 滚动卡盖工具行/hero',
     '同 5 兜底（遮罩 + 视口剔除）', '直接改'),
    ('9', '地图页 · 死常量', '§8 常量纪律',
     'M.CUSTOM_W = 663 零引用（注释自述 = M.MAP_W）', '删除', '直接改'),
]

ry = sy + 32
RH = 44
for n, where, rule, now, plan, act in rows:
    col = AMB if act == '需拍板' else RED
    rrect(PAD, ry, W - PAD, ry + RH - 6, 4, PANEL)
    badge(PAD + 8, ry + (RH - 6) / 2 - 7.5, n, col)
    text(PAD + 34, ry + 6, where, 12, TXT, True)
    text(PAD + 34, ry + 24, '§' + rule.split(' ')[0] + '  ' + rule.split(' ', 1)[1],
         10, GOLD if act == '需拍板' else DIM)
    text(PAD + 264, ry + 6, now, 10, DIM)
    text(PAD + 264, ry + 24, plan, 10, GRN)
    text(W - PAD - 10, ry + (RH - 6) / 2, act, 11, col, True, 'rm')
    ry += RH

text(PAD, ry + 6,
     '执行顺序建议：①→④⑨（地图页一次改齐）→ ⑤⑥⑧（滚动遮罩三页同款）→ ⑦ 单独拍板后再动；'
     '每步走 §9 验证链（lua51 → 行尾 → deploy → 串行全检）。',
     11, DIM)

img = img.resize((W * S, H * S), Image.LANCZOS) if S != 1 else img
out = r'_temp/_corner_view/ui_audit_4pages.png'
os.makedirs(os.path.dirname(out), exist_ok=True)
img.save(out)
print('wrote', os.path.abspath(out), img.size)
