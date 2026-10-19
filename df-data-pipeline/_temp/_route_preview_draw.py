import io
import math
import os
import re

from PIL import Image, ImageDraw, ImageFont

ROOT = 'D:/workspace/DungeonsForever'
SRC = ROOT + '/_temp/_route_preview_png'
AST = ROOT + '/_temp/_route_assets'
FR = 'D:/Game/World of Warcraft/_cn_beta_/Interface/AddOns/ForeverDungeonRoutes/Data/DefaultRoutes.lua'
W, H = 1002, 668
SS = 2


def parse_route(key):
    s = io.open(FR, encoding='utf-8').read()
    m = re.search(r'DR\.DefaultRoutes\["%s"\] = \{(.*?)\n\}\n' % key, s, re.S)
    body = m.group(1)
    paths = []
    for pm in re.finditer(r'\{kind="(main|side)", floor=(\d+),(.*?)pts=\{([^}]*)\}\}', body):
        nums = [float(x) for x in pm.group(4).split(',') if x.strip()]
        pts = [(nums[i] * W, nums[i + 1] * H) for i in range(0, len(nums) - 1, 2)]
        paths.append((pm.group(1), int(pm.group(2)), pts))
    stops = []
    for sm in re.finditer(r'\{kind="(\w+)", floor=(\d+), x=([\d.]+), y=([\d.]+), name="([^"]*)"', body):
        stops.append((sm.group(1), int(sm.group(2)), float(sm.group(3)) * W,
                      float(sm.group(4)) * H, sm.group(5)))
    notes = []
    for nm in re.finditer(r'\{floor=(\d+), x=([\d.]+), y=([\d.]+), text="([^"]*)"', body):
        notes.append((int(nm.group(1)), float(nm.group(2)) * W, float(nm.group(3)) * H, nm.group(4)))
    return paths, stops, notes


def grad(t):
    G = [(0.00, 0.37, 0.84, 0.82), (0.55, 1.00, 0.84, 0.36), (1.00, 1.00, 0.50, 0.25)]
    for i in range(len(G) - 1):
        a, b = G[i], G[i + 1]
        if t <= b[0]:
            u = (t - a[0]) / (b[0] - a[0]) if b[0] > a[0] else 0
            return tuple(int(255 * (a[k] + (b[k] - a[k]) * u)) for k in (1, 2, 3))
    return tuple(int(255 * v) for v in G[-1][1:])


def cumps(pts):
    cum = [0.0]
    for i in range(1, len(pts)):
        cum.append(cum[-1] + math.dist(pts[i - 1], pts[i]))
    return cum


def draw_main(d, pts, t0, t1):
    cum = cumps(pts)
    total = cum[-1] or 1
    for i in range(1, len(pts)):
        d.line([pts[i - 1], pts[i]], fill=(13, 10, 8, 200), width=int(7 * SS))
    for i in range(1, len(pts)):
        t = t0 + (t1 - t0) * ((cum[i - 1] + cum[i]) * 0.5 / total)
        d.line([pts[i - 1], pts[i]], fill=grad(t), width=int(4 * SS))
    spacing, size = 64.0, 5.0
    s = spacing * 0.6
    i = 1
    while s < total - 8:
        while i < len(cum) - 1 and cum[i] < s:
            i += 1
        seg = cum[i] - cum[i - 1]
        u = (s - cum[i - 1]) / seg if seg > 0 else 0
        mx = pts[i - 1][0] + (pts[i][0] - pts[i - 1][0]) * u
        my = pts[i - 1][1] + (pts[i][1] - pts[i - 1][1]) * u
        ang = math.atan2(pts[i][1] - pts[i - 1][1], pts[i][0] - pts[i - 1][0])
        a1 = (mx - size * math.cos(ang - 0.75), my - size * math.sin(ang - 0.75))
        a2 = (mx - size * math.cos(ang + 0.75), my - size * math.sin(ang + 0.75))
        d.line([a1, (mx, my)], fill=(15, 13, 8, 235), width=int(2 * SS))
        d.line([a2, (mx, my)], fill=(15, 13, 8, 235), width=int(2 * SS))
        s += spacing


def draw_side(d, pts):
    for i in range(1, len(pts)):
        d.line([pts[i - 1], pts[i]], fill=(13, 10, 8, 140), width=int(6 * SS))
    dash, gap = 7.0, 5.0
    phase, drawing = dash, True
    for i in range(1, len(pts)):
        x1, y1 = pts[i - 1]
        x2, y2 = pts[i]
        ln = math.dist((x1, y1), (x2, y2))
        pos = 0.0
        while pos < ln:
            step = min(phase, ln - pos)
            if drawing:
                a, b = pos / ln, (pos + step) / ln
                d.line([(x1 + (x2 - x1) * a, y1 + (y2 - y1) * a),
                        (x1 + (x2 - x1) * b, y1 + (y2 - y1) * b)],
                       fill=(227, 222, 209, 255), width=int(3 * SS))
            pos += step
            phase -= step
            if phase <= 0:
                drawing = not drawing
                phase = dash if drawing else gap


def tint(im, rgb):
    from PIL import ImageChops
    layer = Image.new('RGBA', im.size, (int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255), 255))
    out = ImageChops.multiply(im, layer)
    out.putalpha(im.getchannel('A'))
    return out


def size(im, d):
    return im.resize((max(1, int(d * SS)), max(1, int(d * SS))), Image.LANCZOS)


def paste_c(base, im, cx, cy):
    base.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))


def main():
    CIRCLE = Image.open(AST + '/circle.png').convert('RGBA')
    RING = Image.open(AST + '/ring.png').convert('RGBA')
    DIA = Image.open(AST + '/diamond.png').convert('RGBA')
    DIAR = Image.open(AST + '/diamondring.png').convert('RGBA')
    CHECK = Image.open(AST + '/check.png').convert('RGBA')
    FILL = tint(CIRCLE, (0.06, 0.05, 0.04))
    KIND = {'boss': (242, 194, 79), 'rare': (227, 222, 209), 'optional': (158, 199, 242)}
    try:
        font = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', int(12 * SS))
    except Exception:
        font = ImageFont.load_default()

    key = 'blackfathom'
    paths, stops, notes = parse_route(key)
    order = {}
    for floor, lay in ((221, 1), (222, 2), (223, 3)):
        base = Image.open('%s/bfd_L%d_crop.png' % (SRC, lay)).convert('RGBA')
        big = base.resize((W * SS, H * SS), Image.LANCZOS)
        ov = Image.new('RGBA', big.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        for kind, pf, pts in paths:
            if pf != floor:
                continue
            sp = [(x * SS, y * SS) for x, y in pts]
            draw_side(d, sp) if kind == 'side' else draw_main(d, sp, 0, 1)
        for pf, x, y, txt in notes:
            if pf != floor:
                continue
            cx, cy = x * SS, y * SS
            paste_c(ov, size(tint(DIA, (0.55, 0.16, 0.14)), 20), cx, cy)
            paste_c(ov, size(tint(DIAR, (1, 0.78, 0.7)), 20), cx, cy)
            d.text((cx, cy - 1 * SS), '!', font=font, fill=(255, 244, 236), anchor='mm')
        idx = 0
        for kind, pf, x, y, name in stops:
            if pf != floor:
                continue
            idx += 1
            cx, cy = x * SS, y * SS
            paste_c(ov, size(FILL, 26), cx, cy)
            paste_c(ov, size(tint(RING, [v / 255 for v in KIND[kind]]), 26), cx, cy)
            d.text((cx, cy + 0.5 * SS), str(idx), font=font, fill=KIND[kind], anchor='mm')
        out = Image.alpha_composite(big, ov)
        p = '%s/bfd_L%d_pin.png' % (SRC, lay)
        out.convert('RGB').save(p)
        print(p)


if __name__ == '__main__':
    main()
