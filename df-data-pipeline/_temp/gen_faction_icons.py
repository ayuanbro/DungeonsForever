# 从参考剪影图生成联盟/部落阵营图标 TGA（64x64，32 位，desc=0x28）
# 联盟=蓝色 狮头；部落=红色 符号。轮廓来自参考图的暗部剪影，重着色后轻扫上下明暗。
import struct, zlib, os
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = 64

ALLIANCE_BLUE = (102, 204, 240)
HORDE_RED = (255, 77, 64)

def load_mask(path):
    im = Image.open(path).convert('L')
    w, h = im.size
    px = im.load()
    # 用列/行投影找内容包围盒（暗部为形状）
    thr = 150
    xs = [x for x in range(w) if any(px[x, y] < thr for y in range(0, h, 2))]
    ys = [y for y in range(h) if any(px[x, y] < thr for x in range(0, w, 2))]
    if not xs or not ys:
        raise RuntimeError('no shape found in ' + path)
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    cw, ch = x1 - x0 + 1, y1 - y0 + 1
    side = max(cw, ch)
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    # 内容只占纹理 ~78%：行内图标统一走 7% 内缩裁切 + 圆角蒙版，留边防削尖
    half = int(side * 0.64) + 2
    box = (max(0, cx - half), max(0, cy - half), min(w, cx + half), min(h, cy + half))
    im = im.crop(box)
    # 补成正方形（白边填充=透明）
    w2, h2 = im.size
    side = max(w2, h2)
    sq = Image.new('L', (side, side), 255)
    sq.paste(im, ((side - w2) // 2, (side - h2) // 2))
    return sq.resize((S, S), Image.LANCZOS)

def build(path, color):
    mask = load_mask(path)
    src = mask.load()
    img = []
    cr, cg, cb = color
    for y in range(S):
        row = []
        # 上下明暗：顶部亮 1.12，底部暗 0.82
        k = 1.12 - (y / (S - 1)) * 0.30
        r, g, b = int(cr * k + 0.5), int(cg * k + 0.5), int(cb * k + 0.5)
        r = min(r, 255); g = min(g, 255); b = min(b, 255)
        for x in range(S):
            d = 255 - src[x, y]  # 越暗越实
            a = (d - 60) / (160 - 60)
            a = 0.0 if a < 0 else (1.0 if a > 1 else a)
            row.append((r, g, b, a))
        img.append(row)
    return img

def write_tga(path, img):
    raw = bytearray()
    for row in img:
        for (r, g, b, a) in row:
            raw += bytes([b, g, r, int(a * 255 + 0.5)])
    hdr = struct.pack('<BBBHHBHHHHBB', 0, 0, 2, 0, 0, 0, 0, 0, S, S, 32, 0x28)
    open(path, 'wb').write(hdr + bytes(raw))
    print('wrote', path)

def write_preview(path, imgs, scale=4):
    n = len(imgs)
    pad = 8
    W = (S * scale + pad) * n + pad
    H = S * scale + pad * 2
    raw = bytearray()
    bg = (0x16, 0x1A, 0x22)  # L2 卡底色
    for Y in range(H):
        raw.append(0)
        for X in range(W):
            i = (X - pad) // (S * scale + pad) if X >= pad else -1
            r, g, b = bg
            if 0 <= i < n:
                lx = (X - pad) % (S * scale + pad)
                ly = Y - pad
                if lx < S * scale and 0 <= ly < S * scale:
                    pr, pg, pb, pa = imgs[i][ly // scale][lx // scale]
                    r = int(bg[0] + (pr - bg[0]) * pa)
                    g = int(bg[1] + (pg - bg[1]) * pa)
                    b = int(bg[2] + (pb - bg[2]) * pa)
            raw += bytes([r, g, b])
    def chunk(t, data):
        c = t + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)
    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', W, H, 8, 2, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(bytes(raw), 6))
    png += chunk(b'IEND', b'')
    open(path, 'wb').write(png)
    print('preview', path)

out_dir = os.path.join(ROOT, 'Media', 'icon', 'FACTION')
os.makedirs(out_dir, exist_ok=True)
tmp = os.path.join(ROOT, '_temp')

a = build(os.path.join(tmp, '_fac_alliance_ref.jpg'), ALLIANCE_BLUE)
h = build(os.path.join(tmp, '_fac_horde_ref.jpg'), HORDE_RED)
write_tga(os.path.join(out_dir, 'FactionIcon_Alliance.tga'), a)
write_tga(os.path.join(out_dir, 'FactionIcon_Horde.tga'), h)
write_preview(os.path.join(tmp, '_fac_preview.png'), [a, h])
