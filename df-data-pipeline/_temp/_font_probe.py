from PIL import Image, ImageDraw, ImageFont

FONTS = [
    ('msyhbd', 'C:/Windows/Fonts/msyhbd.ttc'),
    ('msyh', 'C:/Windows/Fonts/msyh.ttc'),
    ('segoeuib', 'C:/Windows/Fonts/segoeuib.ttf'),
    ('segoeui', 'C:/Windows/Fonts/segoeui.ttf'),
    ('arialbd', 'C:/Windows/Fonts/arialbd.ttf'),
    ('arial', 'C:/Windows/Fonts/arial.ttf'),
    ('tahomabd', 'C:/Windows/Fonts/tahomabd.ttf'),
    ('calibrib', 'C:/Windows/Fonts/calibrib.ttf'),
    ('verdanab', 'C:/Windows/Fonts/verdanab.ttf'),
    ('trebucbd', 'C:/Windows/Fonts/trebucbd.ttf'),
]

TARGET_H = 288
S = 512


def render(path, stroke):
    try:
        f = ImageFont.truetype(path, 400)
    except Exception as e:
        return None
    tmp = Image.new('L', (1000, 1000), 0)
    d = ImageDraw.Draw(tmp)
    if stroke:
        d.text((500, 500), '?', font=f, fill=255, anchor='mm', stroke_width=stroke, stroke_fill=255)
    else:
        d.text((500, 500), '?', font=f, fill=255, anchor='mm')
    bb = tmp.getbbox()
    if not bb:
        return None
    tmp = tmp.crop(bb)
    w, h = tmp.size
    nh = TARGET_H
    nw = max(1, int(round(w * nh / h)))
    tmp = tmp.resize((nw, nh), Image.LANCZOS)
    return tmp


def gap_rows(img64):
    a = img64.split()[3]
    px = a.load()
    rows = []
    for j in range(64):
        rows.append(sum(px[i, j] for i in range(64)))
    bbox = a.getbbox()
    if not bbox:
        return 0, bbox
    y0, y1 = bbox[1], bbox[3] - 1
    gaps = []
    run = 0
    for j in range(y0, y1 + 1):
        if rows[j] < 40:
            run += 1
        else:
            if run:
                gaps.append((j - run, run))
            run = 0
    if run:
        gaps.append((y1 - run + 1, run))
    inner = [g for g in gaps if g[0] > y0 + 1]
    best = max([g[1] for g in inner], default=0)
    return best, bbox


for name, path in FONTS:
    for stroke in (0, 14, 26):
        t = render(path, stroke)
        if t is None:
            print(name, stroke, 'MISS')
            continue
        canvas = Image.new('RGBA', (S, S), (0, 0, 0, 0))
        a = Image.new('RGBA', t.size, (255, 255, 255, 255))
        canvas.paste(a, ((S - t.size[0]) // 2, (S - t.size[1]) // 2), t)
        small = canvas.resize((64, 64), Image.LANCZOS)
        g, bbox = gap_rows(small)
        print('%-9s stroke=%-3d gap=%dpx(64)  bbox=%s' % (name, stroke, g, bbox))
